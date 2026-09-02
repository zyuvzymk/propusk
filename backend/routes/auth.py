from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import hashlib
import hmac
import base64
import json
import sys
import os

# Гарантируем корректный импорт модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db
from models import User, UserRole
from config import settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

def hash_password(password: str) -> str:
    """Хеширование пароля (используется для сверки)"""
    salt = b"PomorShipyardSalt2026_Secure!"
    iterations = 100000
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hashed.hex()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка совпадения сырого пароля с хэшем из БД"""
    return hash_password(plain_password) == hashed_password

def base64url_encode(payload: bytes) -> str:
    """Кодирование в формат base64url по стандарту RFC 7519"""
    return base64.urlsafe_b64encode(payload).decode('utf-8').replace('=', '')

def base64url_decode(payload_str: str) -> bytes:
    """Декодирование формата base64url с восстановлением паддинга"""
    rem = len(payload_str) % 4
    if rem > 0:
        payload_str += '=' * (4 - rem)
    return base64.urlsafe_b64decode(payload_str.encode('utf-8'))

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Автономная генерация подписанного JWT-токена (HS256)"""
    header = {"alg": "HS256", "typ": "JWT"}
    header_json = json.dumps(header, separators=(',', ':')).encode('utf-8')
    header_b64 = base64url_encode(header_json)
    
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": int(expire.timestamp())})
    payload_json = json.dumps(to_encode, separators=(',', ':')).encode('utf-8')
    payload_b64 = base64url_encode(payload_json)
    
    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    signature = hmac.new(settings.SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
    signature_b64 = base64url_encode(signature)
    
    return f"{header_b64}.{payload_b64}.{signature_b64}"

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Зависимость для извлечения и полной валидации текущего пользователя из Cookie.
    """
    token_cookie = request.cookies.get("access_token")
    if not token_cookie or not token_cookie.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Вы не авторизованы в системе"
        )
    
    token = token_cookie.split(" ")[1]
    
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверная структура сессии")
            
        header_b64, payload_b64, signature_b64 = parts
        
        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
        expected_sig = hmac.new(settings.SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
        expected_sig_b64 = base64url_encode(expected_sig)
        
        if not hmac.compare_digest(signature_b64, expected_sig_b64):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Токен сессии скомпрометирован")
            
        payload_bytes = base64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode('utf-8'))
        
        username: str = payload.get("sub")
        exp: int = payload.get("exp")
        
        if username is None or exp is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неполные данные сессии")
            
        if datetime.utcnow().timestamp() > exp:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Время сессии истекло, войдите заново")
            
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ошибка валидации сессии пропусков"
        )
        
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь системы не найден")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ваш аккаунт заблокирован")
        
    return user

class RoleChecker:
    """Класс-зависимость для разграничения ролевой модели"""
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)):
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для выполнения операции на Поморской Судоверфи"
            )
        return current_user

@router.post("/login")
def login_for_access_token(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Эндпоинт авторизации. Токен пишется в Cookie сессии."""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Учетная запись деактивирована")

    # Внимание: убираем .value, так как user.role теперь является чистой строкой 'str' из базы
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "role": user.role,
        "username": user.username
    }

@router.post("/logout")
def logout(response: Response):
    """Сброс сессии авторизации и очистка Cookie"""
    response.delete_cookie("access_token")
    return {"status": "session cleared"}

@router.get("/me")
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Возвращает информацию о текущем пользователе (роль, логин)"""
    return {"username": current_user.username, "role": current_user.role}
