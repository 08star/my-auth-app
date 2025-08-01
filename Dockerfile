FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT 8080
EXPOSE 8080
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:8080", "app:app"]
