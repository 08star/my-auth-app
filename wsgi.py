from app import app, init_app

# 在 container 啟動、gunicorn import 這個 wsgi.py 時就先跑一次
init_app()

# gunicorn 會找的 WSGI 物件名稱
application = app
