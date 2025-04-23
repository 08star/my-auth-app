# wsgi.py
import os, sys
# 确保当前目录在 Python 路径里
sys.path.insert(0, os.path.dirname(__file__))

from app import app

# Gunicorn 会导入这个 app
if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8000)
