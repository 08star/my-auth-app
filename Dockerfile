# 從官方 Python Slim
FROM python:3.9-slim

# 設好工作資料夾
WORKDIR /app

# 先複製 requirements 安裝，加快 rebuild
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 把整個程式碼（包含 templates）複製進去
COPY . .

# Cloud Run 會用 $PORT
ENV PORT 8080
EXPOSE 8080

# 啟動指令：用 wsgi.application，確保 init_app() 執行
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "wsgi:application"]
