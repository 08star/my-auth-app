# 使用官方 Python Slim 映像
FROM python:3.9-slim

# 設定工作目錄
WORKDIR /app

# 複製並安裝相依
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式碼
COPY . .

# Cloud Run 會以 $PORT 環境變數為監聽埠
ENV PORT 8080
EXPOSE 8080

# 啟動指令：app.py 裡有 Flask 實例 app
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
