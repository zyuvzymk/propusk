import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Привязываем Pydantic к реальным именам переменных из вашего .env
    DB_USER: str = Field(default="postgres")
    DB_PASSWORD: str = Field(default="postgres")
    DB_NAME: str = Field(default="postgres")
    DB_HOST: str = Field(default="db")
    DB_PORT: str = Field(default="5432")
    
    # Настройки безопасности и JWT-сессий
    SECRET_KEY: str = Field(default="POMOR_SHIPYARD_SECRET_KEY_2026_SECURE")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    @property
    def POSTGRES_URL(self) -> str:
        """Сборка DSN-строки на основе корректных переменных .env"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Конфигурация парсинга файла .env (на уровень выше папки backend)
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
