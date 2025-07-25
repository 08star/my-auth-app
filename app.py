import os
from flask import Flask, request, jsonify, redirect, url_for, flash, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_babel import Babel, lazy_gettext as _l
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from wtforms import PasswordField, StringField, BooleanField, Form
from wtforms.validators import DataRequired
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm

app = Flask(__name__)
app.config.update({
    'SECRET_KEY': os.environ.get('SECRET_KEY', 'development-only'),
    'SQLALCHEMY_DATABASE_URI': 'sqlite:////tmp/auth_devices.db',
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'BABEL_DEFAULT_LOCALE': 'zh_TW',
})

db    = SQLAlchemy(app)    # ← 只这一处！
jwt   = JWTManager(app)
babel = Babel(app)
login_manager = LoginManager(app)
login_manager.login_view = 'admin_login'

# ─── Models ───────────────────────
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    devices = db.relationship('Device', back_populates='user')

class Device(db.Model):
    __tablename__ = 'devices'
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(128), unique=True, nullable=False)
    verified = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', back_populates='devices')

class AdminUser(UserMixin, db.Model):
    __tablename__ = 'admin_users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

# ─── Admin views ──────────────────
class SecureModelView(ModelView):
    def is_accessible(self): return current_user.is_authenticated
    def inaccessible_callback(self, name, **kw): return redirect(url_for('admin_login'))

class SecureAdminIndexView(AdminIndexView):
    def is_accessible(self): return current_user.is_authenticated
    def inaccessible_callback(self, name, **kw): return redirect(url_for('admin_login'))

# UserAdmin / DeviceAdmin / AdminUserAdmin 略，同你之前的

admin = Admin(app, index_view=SecureAdminIndexView(), template_mode='bootstrap3')
# … add_view(UserAdmin …), add_view(DeviceAdmin …), add_view(AdminUserAdmin …)

# ─── Admin login/logout ───────────
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        adm = AdminUser.query.filter_by(username=request.form['username']).first()
        if adm and adm.is_active and adm.check_password(request.form['password']):
            login_user(adm)
            return redirect(url_for('admin.index'))
        flash(_l('帳號或密碼錯誤'),'danger')
    return render_template('admin_login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_login'))

# ─── 初始化 DB ─────────────────────
@app.before_first_request
def init_db():
    db.create_all()
    if not AdminUser.query.filter_by(username='admin').first():
        adm = AdminUser(username='admin',
                        password_hash=generate_password_hash('0905'),
                        is_active=True)
        db.session.add(adm)
        db.session.commit()

# ─── 其余 前台API … ────────────────────
@app.route('/', methods=['GET'])
def index():
    """
    網站首頁——之後可放通用導覽、介紹或跳轉登入連結
    """
    return render_template('search_follow.html')



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',8000)))
