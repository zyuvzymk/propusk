from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import sys
import os
import re

# Гарантируем корректный импорт модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db
from models import PassRequest, User, UserRole, RequestStatus
from schemas import PassRequestOut, PassRequestUpdate
from routes.auth import get_current_user, RoleChecker
from utils.email import send_email

router = APIRouter(prefix="/api/admin", tags=["Admin Registry & Management"])

# Настраиваем боевые политики разграничения прав доступа
admin_only = RoleChecker(allowed_roles=[UserRole.ADMIN.value])
operators_and_admin = RoleChecker(allowed_roles=[UserRole.ADMIN.value, UserRole.OPERATOR_1.value, UserRole.OPERATOR_2.value])
any_authenticated_user = RoleChecker(allowed_roles=[UserRole.ADMIN.value, UserRole.OPERATOR_1.value, UserRole.OPERATOR_2.value, UserRole.SECURITY.value])

@router.get("/requests", response_model=List[PassRequestOut])
def get_all_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(any_authenticated_user)
):
    requests = db.query(PassRequest).order_by(PassRequest.created_at.desc()).all()
    return requests

@router.get("/requests/{request_id}", response_model=PassRequestOut)
def get_request_by_id(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(any_authenticated_user)
):
    db_request = db.query(PassRequest).filter(PassRequest.id == request_id).first()
    if not db_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Заявка №{request_id} на Поморской Судоверфи не найдена"
        )
    return db_request

@router.put("/requests/{request_id}", response_model=PassRequestOut)
def update_and_approve_request(
    request_id: int,
    payload: PassRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(operators_and_admin)
):
    db_request = db.query(PassRequest).filter(PassRequest.id == request_id).first()
    if not db_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Заявка №{request_id} на Поморской Судоверфи не найдена"
        )

    # TASK-BA-1.1: Защита Read-Only для обработанных заявок
    if db_request.status in [RequestStatus.APPROVED.value, RequestStatus.REJECTED.value]:
        if payload.status == RequestStatus.PENDING:
            if current_user.role != UserRole.ADMIN.value:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Только администратор может возвращать заявку на рассмотрение"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Заявка обработана, изменение запрещено"
            )

    days_limit = (payload.end_date - payload.start_date).days
    if days_limit > 31:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Период действия временного пропуска не может превышать 31 день по регламенту СБ"
        )

    # === НОВАЯ ЛОГИКА ДАТ (сравнение только по датам) ===
    old_start = db_request.original_start_date
    old_end = db_request.original_end_date

    # Обновляем текущие даты
    db_request.current_start_date = payload.start_date
    db_request.current_end_date = payload.end_date

    # Сравниваем только даты (без времени)
    db_request.dates_changed = (
        old_start.date() != payload.start_date.date() or
        old_end.date() != payload.end_date.date()
    )

    # Основные поля
    db_request.start_date = payload.start_date
    db_request.end_date = payload.end_date
    db_request.status = payload.status.value
    db_request.car_info = payload.car_info

    if payload.comment and payload.comment.strip():
        if " | Комментарий:" not in db_request.purpose:
            db_request.purpose = f"{db_request.purpose} | Комментарий: {payload.comment.strip()}"

    # Обновление флагов посетителей
    if payload.pedestrian_ids is not None:
        for visitor in db_request.visitors:
            visitor.is_pedestrian = visitor.id in payload.pedestrian_ids

    if payload.excluded_ids is not None:
        for visitor in db_request.visitors:
            visitor.is_excluded = visitor.id in payload.excluded_ids

    try:
        db.commit()
        db.refresh(db_request)

        # TASK-BA-1.3: Аудит-лог операторов
        audit_mark = f" [Обработал: {current_user.username} ({current_user.role})]"
        if db_request.purpose:
            if audit_mark not in db_request.purpose:
                db_request.purpose = db_request.purpose + audit_mark
        else:
            db_request.purpose = audit_mark

        db.commit()
        db.refresh(db_request)

        # === УВЕДОМЛЕНИЯ ===
        email_match = re.search(r'Email:\s*([^\s,|]+)', db_request.purpose)
        client_email = email_match.group(1) if email_match else None

        if payload.status == RequestStatus.APPROVED:
            send_email(
                to=["security@zymk.ru"],
                subject=f"Заявка №{db_request.id} одобрена",
                body=f"Заявка №{db_request.id} одобрена.\n\nСсылка: https://propusk.shipyard29.ru/view/{db_request.id}"
            )
            if client_email:
                send_email(
                    to=[client_email],
                    subject=f"Заявка №{db_request.id} одобрена",
                    body=f"Ваша заявка №{db_request.id} одобрена."
                )

        if payload.status == RequestStatus.REJECTED:
            if client_email:
                reason = payload.comment or "Без указания причины"
                send_email(
                    to=[client_email],
                    subject=f"Заявка №{db_request.id} отклонена",
                    body=f"Ваша заявка №{db_request.id} отклонена.\n\nПричина: {reason}"
                )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка транзакции СУБД при сохранении параметров: {str(e)}"
        )
    return db_request

@router.patch("/requests/{request_id}/status", response_model=PassRequestOut)
def update_request_status(
    request_id: int,
    new_status: RequestStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(operators_and_admin)
):
    db_request = db.query(PassRequest).filter(PassRequest.id == request_id).first()
    if not db_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Заявка №{request_id} не найдена"
        )

    if db_request.status in [RequestStatus.APPROVED.value, RequestStatus.REJECTED.value]:
        if new_status == RequestStatus.PENDING:
            if current_user.role != UserRole.ADMIN.value:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Только администратор может возвращать заявку на рассмотрение"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Заявка обработана, изменение статуса запрещено"
            )

    db_request.status = new_status.value

    audit_mark = f" [Обработал: {current_user.username} ({current_user.role})]"
    if db_request.purpose:
        if audit_mark not in db_request.purpose:
            db_request.purpose = db_request.purpose + audit_mark
    else:
        db_request.purpose = audit_mark

    try:
        db.commit()
        db.refresh(db_request)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обновлении статуса заявки: {str(e)}"
        )
    return db_request

@router.delete("/requests/{request_id}", status_code=status.HTTP_200_OK)
def delete_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    db_request = db.query(PassRequest).filter(PassRequest.id == request_id).first()
    if not db_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Заявка №{request_id} не найдена"
        )

    try:
        db.delete(db_request)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка транзакции СУБД при удалении записи: {str(e)}"
        )
    return {"detail": f"Заявка №{request_id} и все связанные посетители успешно удалены"}
