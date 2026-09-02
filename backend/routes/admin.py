from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import sys
import os

# Гарантируем корректный импорт модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db
from models import PassRequest, PassVisitor, User, UserRole, RequestStatus
from schemas import PassRequestOut, PassRequestUpdate
from routes.auth import get_current_user, RoleChecker

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
    """
    Получение реестра заявок.
    Доступно абсолютно всем авторизованным пользователям Поморской Судоверфи (включая Охрану).
    """
    requests = db.query(PassRequest).order_by(PassRequest.created_at.desc()).all()
    return requests

@router.get("/requests/{request_id}", response_model=PassRequestOut)
def get_request_by_id(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(any_authenticated_user)
):
    """
    Детальный просмотр заявки по ID для интерактивного макета сравнения данных.
    Доступно любой роли, включая Охрану для сверки документов на КПП.
    """
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
        # TASK-BA-1.2: Привилегии Администратора для возврата на рассмотрение
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

    db_request.status = payload.status.value
    db_request.start_date = payload.start_date
    db_request.end_date = payload.end_date
    db_request.car_info = payload.car_info

    if payload.comment and payload.comment.strip():
        if " | Комментарий:" not in db_request.purpose:
            db_request.purpose = f"{db_request.purpose} | Комментарий: {payload.comment.strip()}"

    try:
        db.commit()
        db.refresh(db_request)
        
        # TASK-BA-1.3: Аудит-лог операторов с добавлением метки в purpose
        audit_mark = f" [Обработал: {current_user.username} ({current_user.role})]"
        if db_request.purpose:
            if audit_mark not in db_request.purpose:
                db_request.purpose = db_request.purpose + audit_mark
        else:
            db_request.purpose = audit_mark
        
        db.commit()
        db.refresh(db_request)
        
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
    """
    Изменение статуса заявки (Одобрен / Отклонен).
    ДОСТУПНО: Администратору, Оператору 1, Оператору 2.
    СТРОГО ЗАПРЕЩЕНО: Сотрудникам Охраны КПП (возвращает 403 Forbidden).
    """
    db_request = db.query(PassRequest).filter(PassRequest.id == request_id).first()
    if not db_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Заявка №{request_id} не найдена"
        )

    # Проверка на возможность изменения статуса для обработанных заявок
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
    
    # Добавляем аудит-метку при изменении статуса
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
    """
    Полное удаление заявки из системы.
    СТРОГО ОГРАНИЧЕНО: Доступно исключительно Администратору.
    Сотрудники Охраны и Операторы получат отказ в доступе.
    """
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
