from werkzeug.security import generate_password_hash
from app import db, User, app

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username="testuser").first():
        u = User(username="testuser", password_hash=generate_password_hash("testpass"))
        db.session.add(u)
        db.session.commit()
        print("Created testuser/testpass")
    else:
        print("User already exists")
