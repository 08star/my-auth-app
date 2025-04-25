import os
import jwt
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, abort
from models import db, User, Device

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://db_user:db_pass@50.6.201.184/db_name?charset=utf8mb4"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "replace-with-a-secure-random-string")

db.init_app(app)

def make_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=8)
    }
    return jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")

@app.route("/api/authenticate", methods=["POST"])
def authenticate():
    data = request.get_json() or {}
    u = data.get("username")
    p = data.get("password")
    d = data.get("device_id")
    if not (u and p and d):
        return jsonify({"error": "missing fields"}), 400

    user = User.query.filter_by(username=u).first()
    if not user or not user.check_password(p):
        return jsonify({"error": "invalid credentials"}), 401

    allowed = Device.query.filter_by(user_id=user.id, device_id=d).first()
    if not allowed:
        return jsonify({"error": "device not authorized"}), 403

    token = make_token(user.id)
    return jsonify({"token": token}), 200

# （可選）一個用來測試 token 的端點
@app.route("/api/ping", methods=["GET"])
def ping():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        t = auth.split(None,1)[1]
        try:
            payload = jwt.decode(t, app.config["SECRET_KEY"], algorithms=["HS256"])
            return jsonify({"user_id": payload["user_id"], "status": "ok"})
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "invalid token"}), 401
    return jsonify({"error": "missing token"}), 401

if __name__ == "__main__":
    # 本機測試用
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=8000)
