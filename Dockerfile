FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run 一定要監聽 $PORT（預設 8080）
ENV PORT 8080
EXPOSE 8080

# 啟動時 Gunicorn 會 import app.py -> 執行 before_first_request
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app", "--workers", "2"]
