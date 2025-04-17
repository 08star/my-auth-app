# wsgi.py
import os, sys
# （可选）确保能找到同目录下的 app.py
sys.path.insert(0, os.path.dirname(__file__))

from app import app   # 你的 Flask 实例写在 app.py 里

if __name__ == "__main__":
    app.run()
