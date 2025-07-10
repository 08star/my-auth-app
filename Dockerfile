# 1. 以官方 Python image 為 base
FROM python:3.9-slim

# 2. 建立 app 目錄並切進去
WORKDIR /app

# 3. 拷貝 requirements 並安裝
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 拷貝整個專案
COPY . .

# 5. 建表＆塞預設管理員（在 container build 時就執行一次）
RUN python - <<EOF
from app import init_app
init_app()
EOF

# 6. Cloud Run 會用 $PORT 環境變數
ENV PORT 8080
EXPOSE 8080

# 7. 啟動指令
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
