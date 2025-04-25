# create_test_user.py
# This script will create a test User in the database for login testing.

from app import app
from extensions import db
from models import User
from werkzeug.security import generate_password_hash

username = "testuser"
password = "testpass"

with app.app_context():
    # create tables if not exist
    db.create_all()
    # check if user exists
    if User.query.filter_by(username=username).first():
        print(f"User '{username}' already exists.")
    else:
        u = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(u)
        db.session.commit()
        print(f"Created test user: {username}/{password}")
