from flask import Flask, request, jsonify
from main import app  # 如果主程式叫 main.py，就這樣寫

# Gunicorn 會從這裡找 app

app = Flask(__name__)
# …其他初始化比如 db …

@app.route("/api/health", methods=["GET"])
def health():
    return "OK", 200

@app.route("/api/authenticate", methods=["POST"])
def authenticate():
    data = request.get_json() or {}
    username  = data.get("username")
    password  = data.get("password")
    device_id = data.get("device_id")
    # —— 下面自己加：在数据库里查 username/password，验证 device_id 是否已经授权
    if username == "admin" and password == "123456" and device_id == "TEST-DEVICE-001":
        return jsonify({"status":"ok"}), 200
    return jsonify({"error":"invalid credentials"}), 401
