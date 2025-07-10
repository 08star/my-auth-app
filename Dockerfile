# 1. 使用官方 Python Slim 镜像
FROM python:3.9-slim

# 2. 设置工作目录
WORKDIR /app

# 3. 复制并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 复制应用代码
COPY . .

# 5. Cloud Run 会以 PORT 环境变量监听
ENV PORT 8080
EXPOSE 8080

# 6. 启动命令：用 Gunicorn 运行你的 app.py
#    假设你的 Flask 实例在 app.py 中叫做 "app"
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:8080", "app:app"]
