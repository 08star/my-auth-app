
"""
後端伺服器：帳號與裝置雙重授權管理
- /auth/register  註冊帳號
- /auth/login     登入並回傳 JWT
- /devices        列出已註冊裝置狀態
- /devices/register 申請註冊裝置
- /devices/verify   管理員核准後前端呼叫標記已核准
"""
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///auth_devices.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'your-very-secret-key'  # 建議改環境變數
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=1)

db = SQLAlchemy(app)
jwt = JWTManager(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    device_id = db.Column(db.String(128), nullable=False)
    verified = db.Column(db.Boolean, default=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'device_id', name='uix_user_device'),)

@app.before_first_request
def create_tables():
    db.create_all()

# 註冊帳號
@app.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    u = data.get('username')
    p = data.get('password')
    if not u or not p:
        return jsonify({'error': 'username and password required'}), 400
    if User.query.filter_by(username=u).first():
        return jsonify({'error': 'username exists'}), 409
    user = User(username=u, password_hash=generate_password_hash(p))
    db.session.add(user)
    db.session.commit()
    return jsonify({'msg': 'user created'}), 201

# 登入取得 JWT
@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    u = data.get('username')
    p = data.get('password')
    if not u or not p:
        return jsonify({'error': 'username and password required'}), 400
    user = User.query.filter_by(username=u).first()
    if not user or not check_password_hash(user.password_hash, p):
        return jsonify({'error': 'invalid credentials'}), 401
    token = create_access_token(identity=user.id)
    return jsonify({'access_token': token}), 200

# 列出所有已註冊裝置及狀態
@app.route('/devices', methods=['GET'])
@jwt_required()
def list_devices():
    user_id = get_jwt_identity()
    devs = Device.query.filter_by(user_id=user_id).all()
    return jsonify([{'device_id': d.device_id, 'verified': d.verified} for d in devs]), 200

# 申請註冊裝置
@app.route('/devices/register', methods=['POST'])
@jwt_required()
def register_device():
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    did = data.get('device_id')
    if not did:
        return jsonify({'error': 'device_id required'}), 400
    dev = Device.query.filter_by(user_id=user_id, device_id=did).first()
    if dev:
        return jsonify({'msg': 'device already registered', 'verified': dev.verified}), 200
    dev = Device(user_id=user_id, device_id=did, verified=False)
    db.session.add(dev)
    db.session.commit()
    return jsonify({'msg': 'device registration requested', 'verified': False}), 201

# 前端呼叫核准（管理員網頁介面亦可呼）
@app.route('/devices/verify', methods=['POST'])
@jwt_required()
def verify_device():
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    did = data.get('device_id')
    if not did:
        return jsonify({'error': 'device_id required'}), 400
    dev = Device.query.filter_by(user_id=user_id, device_id=did).first()
    if not dev:
        return jsonify({'error': 'device not found'}), 404
    dev.verified = True
    db.session.commit()
    return jsonify({'msg': 'device verified'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)

