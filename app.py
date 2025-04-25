"""
app.py - 帶管理介面的後端程式：帳號與裝置雙重授權管理

Endpoints:
  GET  /health               健康檢查
  POST /auth/register        註冊帳號
  POST /auth/login           登入並取得 JWT
  GET  /devices              列出該帳號所有裝置及狀態
  POST /devices/register     申請註冊新裝置
  POST /devices/verify       標記裝置為已核准

Admin UI:
  使用 Flask-Admin，自動生成 /admin 頁面，可管理 User 和 Device
"""
import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

# --- App & Config ---
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///auth_devices.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'CHANGE_THIS_TO_A_SECURE_RANDOM_VALUE'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=1)

db = SQLAlchemy(app)
jwt = JWTManager(app)

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    devices = db.relationship('Device', back_populates='user', lazy=True)

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    device_id = db.Column(db.String(128), nullable=False)
    verified = db.Column(db.Boolean, default=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'device_id', name='uix_user_device'),)
    # 明確定義 relationship 屬性，讓 Flask-Admin 可見
    user = db.relationship('User', back_populates='devices')

# 建表
with app.app_context():
    db.create_all()

# --- Flask-Admin Setup ---
admin = Admin(app, name='AdminPanel', template_mode='bootstrap3')

class UserAdmin(ModelView):
    column_exclude_list = ['password_hash']
    form_excluded_columns = ['password_hash', 'devices']

class DeviceAdmin(ModelView):
    column_list = ('id', 'user.username', 'device_id', 'verified')
    column_labels = {'user.username': 'Username'}
    form_columns = ['user', 'device_id', 'verified']

admin.add_view(UserAdmin(User, db.session))
admin.add_view(DeviceAdmin(Device, db.session))

# --- API Routes ---
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200

@app.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    u = data.get('username'); p = data.get('password')
    if not u or not p: return jsonify({'error':'username and password required'}),400
    if User.query.filter_by(username=u).first(): return jsonify({'error':'username exists'}),409
    user=User(username=u,password_hash=generate_password_hash(p))
    db.session.add(user); db.session.commit()
    return jsonify({'msg':'user created'}),201

@app.route('/auth/login', methods=['POST'])
def login():
    data=request.get_json() or {}; u=data.get('username'); p=data.get('password')
    if not u or not p: return jsonify({'error':'username and password required'}),400
    user=User.query.filter_by(username=u).first()
    if not user or not check_password_hash(user.password_hash,p): return jsonify({'error':'invalid credentials'}),401
    token=create_access_token(identity=str(user.id))
    return jsonify({'access_token':token}),200

@app.route('/devices', methods=['GET'])
@jwt_required()
def list_devices():
    user_id=int(get_jwt_identity())
    devs=Device.query.filter_by(user_id=user_id).all()
    return jsonify([{'device_id':d.device_id,'verified':d.verified} for d in devs]),200

@app.route('/devices/register', methods=['POST'])
@jwt_required()
def register_device():
    user_id=int(get_jwt_identity()); data=request.get_json() or {}
    did=data.get('device_id')
    if not did: return jsonify({'error':'device_id required'}),400
    exist=Device.query.filter_by(user_id=user_id,device_id=did).first()
    if exist: return jsonify({'msg':'already registered','verified':exist.verified}),200
    d=Device(user_id=user_id,device_id=did,verified=False)
    db.session.add(d); db.session.commit()
    return jsonify({'msg':'registration requested','verified':False}),201

@app.route('/devices/verify', methods=['POST'])
@jwt_required()
def verify_device():
    user_id=int(get_jwt_identity()); data=request.get_json() or {}
    did=data.get('device_id')
    d=Device.query.filter_by(user_id=user_id,device_id=did).first()
    if not d: return jsonify({'error':'device not found'}),404
    d.verified=True; db.session.commit()
    return jsonify({'msg':'device verified'}),200

# --- Run server ---
if __name__=='__main__':
    app.run(host='0.0.0.0', port=8000)
