from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import List, Optional
from models import RequestStatus, UserRole

# --- Схемы Посетителей ---
class PassVisitorBase(BaseModel):
    position: Optional[str] = Field(None, max_length=255, description="Должность сотрудника")
    full_name: str = Field(..., min_length=2, max_length=255, description="ФИО посетителя")
    passport_series: str = Field(..., min_length=4, max_length=10, description="Серия паспорта")
    passport_number: str = Field(..., min_length=6, max_length=10, description="Номер паспорта")
    passport_issued_by: str = Field(..., min_length=1, description="Кем выдан паспорт")
    passport_issued_at: datetime = Field(..., description="Дата выдачи паспорта")

class PassVisitorCreate(PassVisitorBase):
    pass

class PassVisitorOut(PassVisitorBase):
    id: int
    request_id: int

    class Config:
        from_attributes = True


# --- Схемы Заявок на Пропуск ---
class PassRequestBase(BaseModel):
    contractor: Optional[str] = Field(None, max_length=255, description="Подрядчик/субподрядчик")
    company_name: str = Field(..., min_length=2, max_length=255, description="Название организации")
    purpose: str = Field(..., min_length=5, description="Цель визита")
    car_info: Optional[str] = Field(None, max_length=255, description="Данные автотранспорта (NULL если пешком)")
    start_date: datetime = Field(..., description="Дата начала действия пропуска")
    end_date: datetime = Field(..., description="Дата окончания действия пропуска")
    original_start_date: Optional[datetime] = Field(None, description="Исходная дата начала из заявки")
    original_end_date: Optional[datetime] = Field(None, description="Исходная дата окончания из заявки")
    current_start_date: Optional[datetime] = Field(None, description="Текущая дата начала (после правок)")
    current_end_date: Optional[datetime] = Field(None, description="Текущая дата окончания (после правок)")

    @field_validator('end_date')
    @classmethod
    def validate_dates(cls, v: datetime, info):
        if 'start_date' in info.data and v < info.data['start_date']:
            raise ValueError('Дата окончания действия пропуска не может быть раньше даты начала')
        return v

class PassRequestCreate(PassRequestBase):
    visitors: List[PassVisitorCreate] = Field(..., min_length=1, description="Список посетителей (минимум 1)")
    honeypot: Optional[str] = Field(None, description="Скрытое поле-ловушка для спам-ботов")

class PassRequestOut(PassRequestBase):
    id: int
    status: RequestStatus
    created_at: datetime
    updated_at: datetime
    visitors: List[PassVisitorOut]
    dates_changed: bool = False

    class Config:
        from_attributes = True


# --- Схемы Пользователей ---
class UserOut(BaseModel):
    id: int
    username: str
    role: UserRole
    is_active: bool

    class Config:
        from_attributes = True

# --- Схема Обновления Заявки (PUT) ---
class PassRequestUpdate(BaseModel):
    status: RequestStatus = Field(..., description="Новый статус заявки")
    start_date: datetime = Field(..., description="Дата начала действия пропуска")
    end_date: datetime = Field(..., description="Дата окончания действия пропуска")
    car_info: Optional[str] = Field(None, max_length=255, description="Данные автотранспорта")
    comment: Optional[str] = Field(None, description="Комментарий оператора или причина отказа")
    pedestrian_ids: Optional[List[int]] = Field(None, description="Список ID посетителей, идущих пешком")
    excluded_ids: Optional[List[int]] = Field(None, description="Список ID исключённых посетителей")
    contractor: Optional[str] = Field(None, max_length=255, description="Подрядчик/субподрядчик")

    @field_validator('end_date')
    @classmethod
    def validate_dates(cls, v: datetime, info):
        if 'start_date' in info.data and v < info.data['start_date']:
            raise ValueError('Дата окончания действия пропуска не может быть раньше даты начала')
        return v
