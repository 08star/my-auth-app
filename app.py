import os
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
# 从 .env 或环境变量读取
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
db = SQLAlchemy(app)

@app.route('/health')
def health():
    return 'OK', 200

@app.route('/api/authenticate', methods=['POST'])
def authenticate():
    data = request.get_json() or {}
    # 这里放你登录验证逻辑，示例：
    username = data.get('username')
    password = data.get('password')
    device_id = data.get('device_id')
    # TODO: 校验用户名/密码/设备
    if username == 'admin' and password == '123456' and device_id == 'TEST-DEVICE-001':
        return jsonify(token='fake-jwt-token'), 200
    return jsonify(error='Unauthorized'), 401
