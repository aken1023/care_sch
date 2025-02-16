FROM python:3.8-slim

WORKDIR /app

COPY requirements.txt .
COPY .env.example .env
COPY . .

RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt

# 設定預設 PORT
ENV PORT=5000
ENV PYTHONUNBUFFERED=1
ENV FLASK_DEBUG=0

EXPOSE ${PORT}

# 使用環境變數中的 PORT
CMD gunicorn --bind 0.0.0.0:${PORT} app:app
