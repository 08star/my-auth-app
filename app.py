import os
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_mapping(
    SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL"),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SECRET_KEY=os.getenv("SECRET_KEY"),
)

db = SQLAlchemy(app)

@app.route("/health")
def health():
    return "OK", 200

@app.route("/api/authenticate", methods=["POST"])
def authenticate():
    data = request.get_json()
    # 这里写你自己的验证逻辑
    return jsonify(token="fake-jwt-token"), 200
