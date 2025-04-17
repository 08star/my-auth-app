from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///auth.db'
db = SQLAlchemy(app)

# --------- Models ---------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    devices = db.relationship('Device', backref='user', lazy=True)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# --------- API Endpoints ---------
@app.route('/api/authenticate', methods=['POST'])
def authenticate():
    """
    请求 JSON: { "username": "...", "password": "...", "device_id": "..." }
    返回 200 OK 表示通过，否则 401/403
    """
    data = request.get_json()
    u = data.get('username', '')
    p = data.get('password', '')
    d = data.get('device_id', '')

    user = User.query.filter_by(username=u).first()
    if not user or not user.check_password(p):
        return jsonify({ 'error': 'Invalid username or password' }), 401

    # 检查设备是否已经绑定到这个用户
    if not any(dev.device_id == d for dev in user.devices):
        return jsonify({ 'error': 'Device not authorized' }), 403

    return jsonify({ 'message': 'Authenticated' }), 200

if __name__ == '__main__':
    db.create_all()  # 第一次运行用
    app.run(host='0.0.0.0', port=8000)
