FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости (для playwright, aiohttp и т.д.)
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем Playwright браузеры (нужно для будущих парсеров Tier 1+)
RUN playwright install --with-deps chromium

# Копируем весь код
COPY . .

# Порт FastAPI
EXPOSE 8000

# Запуск (будет переопределён в docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
