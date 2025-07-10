# 使用官方 Python Slim 映像
FROM python:3.9-slim

# 建立工作目錄
WORKDIR /app

# 複製需求檔並安裝
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式原始碼
COPY . .

# 設定 Cloud Run 監聽的埠
# Cloud Run 會把 $PORT 設成 8080
ENV PORT 8080
EXPOSE 8080

# 啟動前先做 db.create_all() 並啟動 Gunicorn
# 確保 init_app() 在這行 import 時就跑到
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app", "--workers", "2"]
