from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import sys
import os
import re

# Добавляем корневой каталог backend в пути поиска, чтобы избежать ошибок импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db
from models import PassRequest, PassVisitor, RequestStatus
from schemas import PassRequestCreate, PassRequestOut
from utils.email import send_email

router = APIRouter(prefix="/api/public", tags=["Public Form"])

@router.post("/request", response_model=PassRequestOut, status_code=status.HTTP_201_CREATED)
def create_public_request(payload: PassRequestCreate, db: Session = Depends(get_db)):
    """
    Эндпоинт для публичной подачи заявки на временный пропуск.
    Принимает заголовок заявки и вложенный список посетителей.
    """
    if payload.honeypot:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Automated submission detected."
        )

    db_request = PassRequest(
        company_name=payload.company_name,
        purpose=payload.purpose,
        car_info=payload.car_info,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=RequestStatus.PENDING,
        # Новые поля для отслеживания изменений дат
        original_start_date=payload.start_date,
        original_end_date=payload.end_date,
        current_start_date=payload.start_date,
        current_end_date=payload.end_date,
        dates_changed=False
    )
    db.add(db_request)

    try:
        db.flush()

        for visitor_data in payload.visitors:
            db_visitor = PassVisitor(
                request_id=db_request.id,
                **visitor_data.model_dump()
            )
            db.add(db_visitor)

        db.commit()
        db.refresh(db_request)

        # === УВЕДОМЛЕНИЕ ОПЕРАТОРУ ===
        send_email(
            to=["operator@zymk.ru"],
            subject=f"Новая заявка на пропуск №{db_request.id}",
            body=f"Поступила новая заявка №{db_request.id}\n\nСсылка: https://propusk.shipyard29.ru/view/{db_request.id}"
        )

        # === УВЕДОМЛЕНИЕ ОТПРАВИТЕЛЮ ===
        email_match = re.search(r'Email:\s*([^\s,|]+)', payload.purpose)
        if email_match:
            client_email = email_match.group(1)
            send_email(
                to=[client_email],
                subject="Ваша заявка на пропуск принята на рассмотрение",
                body=f"Ваша заявка №{db_request.id} на рассмотрении."
            )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка транзакции СУБД при сохранении данных: {str(e)}"
        )

    return db_request
