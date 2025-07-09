# wsgi.py －－讓 Gunicorn 找到 Flask 應用實體
from app import app   # ← 這一行就夠了，請確定 app.py 裡有 app = Flask(...)
