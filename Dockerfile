# 基礎映像
FROM python:3.9-slim

# 工作目錄
WORKDIR /app

# 複製依賴並安裝
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製程式碼
COPY . .

# Cloud Run 會用 $PORT 環境變數
ENV PORT 8080
EXPOSE 8080

# 啟動指令，綁定到 0.0.0.0:$PORT
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
