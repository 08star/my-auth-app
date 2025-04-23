import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from app import app

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
