FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости + msmtp для отправки писем
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    python3-dev \
    msmtp \
    && rm -rf /var/lib/apt/lists/*

# Копируем конфиг msmtp
COPY msmtprc /etc/msmtprc

# Копируем requirements и устанавливаем зависимости Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код
COPY . .

# Открываем порт для FastAPI
EXPOSE 8000

# Запускаем Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
