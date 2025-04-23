# /home/deploy/my-auth-app/app.py
import os
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

# 初始化 Flask
app = Flask(__name__)
# 从环境变量里读配置
app.config.update(
    SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL"),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SECRET_KEY=os.getenv("SECRET_KEY"),
)

# 初始化数据库扩展
db = SQLAlchemy(app)

# 健康检查
@app.route("/health")
def health():
    return "OK", 200

# 简单示例：认证接口
@app.route("/api/authenticate", methods=["POST"])
def authenticate():
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")
    device_id = data.get("device_id")
    # TODO: 换成你的真实验证逻辑
    if username == "admin" and password == "123456" and device_id:
        return jsonify(token="fake-jwt-token"), 200
    return jsonify(error="invalid credentials"), 401
