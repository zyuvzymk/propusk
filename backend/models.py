import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from database import Base

class RequestStatus(str, enum.Enum):
    PENDING = "На рассмотрении"
    APPROVED = "Одобрен"
    REJECTED = "Отклонен"
    EXPIRED = "Истек"

class UserRole(str, enum.Enum):
    ADMIN = "Администратор"
    OPERATOR_1 = "Оператор 1"
    OPERATOR_2 = "Оператор 2"
    SECURITY = "Охрана"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    # Используем String для стабильной записи строковых значений Enum в СУБД
    role = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class PassRequest(Base):
    __tablename__ = "pass_requests"
    dates_changed = Column(Boolean, default=False)
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(255), nullable=False, index=True)
    purpose = Column(Text, nullable=False)
    car_info = Column(String(255), nullable=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(String(50), default=RequestStatus.PENDING.value, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    visitors = relationship("PassVisitor", back_populates="request", cascade="all, delete-orphan")

class PassVisitor(Base):
    is_excluded = Column(Boolean, default=False)
    is_pedestrian = Column(Boolean, default=False)
    __tablename__ = "pass_visitors"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("pass_requests.id", ondelete="CASCADE"), nullable=False)
    full_name = Column(String(255), nullable=False, index=True)
    passport_series = Column(String(10), nullable=False)
    passport_number = Column(String(10), nullable=False)
    passport_issued_by = Column(Text, nullable=False)
    passport_issued_at = Column(DateTime, nullable=False)

    request = relationship("PassRequest", back_populates="visitors")
