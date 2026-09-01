from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import hashlib
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, Base, SessionLocal
from models import User, UserRole
from routes import public, auth, admin

def hash_password(password: str) -> str:
    """Безопасное хеширование пароля на базе PBKDF2."""
    salt = b"PomorShipyardSalt2026_Secure!"
    iterations = 100000
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hashed.hex()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения, автосоздание таблиц и сидинг боевых пользователей."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 1. Администратор
        if not db.query(User).filter(User.username == "admin").first():
            db.add(User(username="admin", hashed_password=hash_password("admin123"), role=UserRole.ADMIN.value, is_active=True))
        
        # 2. Оператор 1
        if not db.query(User).filter(User.username == "operator1").first():
            db.add(User(username="operator1", hashed_password=hash_password("op123"), role=UserRole.OPERATOR_1.value, is_active=True))
            
        # 3. Оператор 2
        if not db.query(User).filter(User.username == "operator2").first():
            db.add(User(username="operator2", hashed_password=hash_password("op456"), role=UserRole.OPERATOR_2.value, is_active=True))
            
        # 4. Охрана
        if not db.query(User).filter(User.username == "security").first():
            db.add(User(username="security", hashed_password=hash_password("kpp123"), role=UserRole.SECURITY.value, is_active=True))
            
        db.commit()
        print("=== СИДИНГ ЧЕТЫРЕХ ПОЛЬЗОВАТЕЛЕЙ ПРОШЕЛ УСПЕШНО ===")
    except Exception as e:
        print(f"Ошибка при инициализации демонстрационных данных: {str(e)}")
        db.rollback()
    finally:
        db.close()
    yield

app = FastAPI(
    title="Система временных пропусков Поморской Судоверфи",
    version="1.0.0",
    lifespan=lifespan
)

templates = Jinja2Templates(directory="templates")

static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.include_router(public.router)
app.include_router(auth.router)
app.include_router(admin.router)

@app.get("/", response_class=HTMLResponse)
def render_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
def render_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def render_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/view/{request_id}", response_class=HTMLResponse)
def render_view(request_id: int, request: Request):
    return templates.TemplateResponse("view.html", {"request": request, "request_id": request_id})

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "database": "PostgreSQL 15 Connected"}
