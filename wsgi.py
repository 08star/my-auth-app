# /home/deploy/my-auth-app/wsgi.py
import os, sys
# 确保项目根目录在 path 里
sys.path.insert(0, os.path.dirname(__file__))

from app import app

if __name__ == "__main__":
    # 仅作本地调试用
    app.run(host="127.0.0.1", port=8000)
