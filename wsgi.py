# wsgi.py
from app import app, db, AdminUser, generate_password_hash

def init_db():
    """啟動時建表並插入預設管理員"""
    with app.app_context():
        db.create_all()
        if not AdminUser.query.filter_by(username='admin').first():
            adm = AdminUser(username='admin',
                            password_hash=generate_password_hash('0905'),
                            is_active=True)
            db.session.add(adm)
            db.session.commit()
            print('✅ 已建立預設管理員：admin / 0905')

# Gunicorn import wsgi:application 時先執行
init_db()

# Gunicorn 會尋找這個應用物件
application = app
