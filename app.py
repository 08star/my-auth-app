# app.py
import os
from datetime import datetime, timedelta

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash
import jwt

# ---- 初始化 ----
app = Flask(__name__)
# 从 .env 或环境变量里读取
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SECRET_KEY']            = os.getenv('SECRET_KEY')
db = SQLAlchemy(app)

# ---- Models (示例) ----
class User(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def verify_password(self, pwd):
        return check_password_hash(self.password_hash, pwd)

class Device(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    device_id = db.Column(db.String(128), nullable=False)

# ---- 健康检查 ----
@app.route('/health')
def health():
    return 'OK', 200

# ---- 认证接口 ----
@app.route('/api/authenticate', methods=['POST'])
def authenticate():
    data = request.get_json() or {}
    u = User.query.filter_by(username=data.get('username')).first()
    if not u or not u.verify_password(data.get('password', '')):
        return jsonify({'message': 'Invalid credentials'}), 401

    d = Device.query.filter_by(user_id=u.id, device_id=data.get('device_id')).first()
    if not d:
        return jsonify({'message': 'Device not authorized'}), 403

    token = jwt.encode({
        'sub': u.id,
        'exp': datetime.utcnow() + timedelta(hours=2)
    }, app.config['SECRET_KEY'], algorithm='HS256')
    return jsonify({'token': token})

# 你还可以在这里加更多 API 路由…

if __name__ == '__main__':
    # 方便本地调试
    app.run(host='127.0.0.1', port=8000)
