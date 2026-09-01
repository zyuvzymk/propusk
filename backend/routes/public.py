from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import sys
import os

# Добавляем корневой каталог backend в пути поиска, чтобы избежать ошибок импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db
from models import PassRequest, PassVisitor, RequestStatus
from schemas import PassRequestCreate, PassRequestOut

router = APIRouter(prefix="/api/public", tags=["Public Form"])

@router.post("/request", response_model=PassRequestOut, status_code=status.HTTP_201_CREATED)
def create_public_request(payload: PassRequestCreate, db: Session = Depends(get_db)):
    """
    Эндпоинт для публичной подачи заявки на временный пропуск.
    Принимает заголовок заявки и вложенный список посетителей.
    """
    # Защита от ботов: если скрытое поле honeypot заполнено — сбрасываем запрос
    if payload.honeypot:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Automated submission detected."
        )
    
    # 1. Формируем основную запись заявки
    db_request = PassRequest(
        company_name=payload.company_name,
        purpose=payload.purpose,
        car_info=payload.car_info,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=RequestStatus.PENDING
    )
    db.add(db_request)
    
    try:
        # Извлекаем сгенерированный базой ID без фиксации транзакции на диске
        db.flush()  

        # 2. Привязываем каждого посетителя к полученному ID заявки
        for visitor_data in payload.visitors:
            db_visitor = PassVisitor(
                request_id=db_request.id,
                **visitor_data.model_dump()
            )
            db.add(db_visitor)
        
        # Фиксируем атомарную транзакцию целиком
        db.commit()
        db.refresh(db_request)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка транзакции СУБД при сохранении данных Поморской Судоверфи: {str(e)}"
        )
        
    return db_request
