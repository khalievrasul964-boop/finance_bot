FROM python:3.11-slim
WORKDIR /app

# Установим зависимости
COPY requirements.txt ./
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY . /app

# Рекомендуется использовать .env на хостинге для BOT_TOKEN
CMD ["python", "main.py"]
