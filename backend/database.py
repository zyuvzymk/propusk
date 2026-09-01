from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config import settings

# Создаем движок подключения к PostgreSQL
# pool_pre_ping=True проверяет "живучесть" коннекта перед выдачей сессии приложению
engine = create_engine(
    settings.POSTGRES_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Фабрика сессий для взаимодействия с БД внутри запросов
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Декларативный класс-родитель для будущих ORM моделей таблиц
Base = declarative_base()

def get_db():
    """
    Зависимость (Dependency Injection) для эндпоинтов FastAPI.
    Гарантирует автоматическое закрытие сессии после выполнения HTTP-запроса.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
