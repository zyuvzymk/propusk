# Шаг 1: Берем официальный легкий образ Python
FROM python:3.11-slim

# Шаг 2: Устанавливаем рабочую папку внутри контейнера
WORKDIR /app

# Шаг 3: Запрещаем Python писать файлы кэша .pyc на диск и включаем моментальный вывод логов
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Шаг 4: Устанавливаем системные зависимости для компиляции пакетов (базы данных и PDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Шаг 5: Копируем список зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Шаг 6: Копируем весь остальной код бэкенда в контейнер
COPY . .
