from flask import (
    Flask, request, redirect,
    url_for, render_template, flash
)
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_babel import Babel, lazy_gettext as _l, gettext, ngettext
import flask_admin as admin_ext
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import (
    LoginManager, UserMixin,
    login_user, logout_user,
    current_user, login_required
)
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import PasswordField

app = Flask(__name__)
# …（前面原本的設定略）…

# ── 1. 初始化擴充套件 ───────────────────
db    = SQLAlchemy(app)
jwt   = JWTManager(app)
babel = Babel(app)

# Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'admin_login'

from models import User, Device   # 假設你把模型放在 models.py

class AuthUser(UserMixin, User):
    pass

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ── 2. 自訂 AdminIndexView ─────────────────
class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not current_user.is_authenticated:
            return redirect(url_for('admin_login', next=request.url))
        return super().index()

# ── 3. 自訂 ModelView 要求登入 ───────────────
class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('admin_login', next=request.url))

# ── 4. 建立 Admin 並掛上 SecureModelView ────
admin = Admin(
    app,
    name=_l('管理後臺'),
    template_mode='bootstrap3',
    index_view=MyAdminIndexView(),
    base_template='admin/custom_master.html',
    translations_path='translations'
)
admin.add_view(SecureModelView(User,   db.session, name=_l('使用者'), endpoint='user_admin'))
admin.add_view(SecureModelView(Device, db.session, name=_l('裝置'),   endpoint='device_admin'))

# ── 5. 登入登出路由 ─────────────────────────
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        user = User.query.filter_by(username=u).first()
        if user and check_password_hash(user.password_hash, p):
            login_user(user)
            next_url = request.args.get('next') or url_for('admin.index')
            return redirect(next_url)
        flash('帳號或密碼錯誤', 'danger')
    return render_template('admin_login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_login'))


# ── 3. 定義資料模型 ──────────────────────────────────────────────────────
class User(db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_active     = db.Column(db.Boolean, default=True)

    # 雙向關聯：User.devices <-> Device.user
    devices       = db.relationship(
        'Device',
        back_populates='user',
        lazy=True
    )

class Device(db.Model):
    __tablename__ = 'devices'
    id        = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(128), unique=True, nullable=False)
    verified  = db.Column(db.Boolean, default=False)
    user_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user_id   = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False
    )
    # 明確定義雙向關聯
    user      = db.relationship(
        'User',
        back_populates='devices'
    )

# ── 4. 自訂 Admin View ───────────────────────────────────────────────────
class UserAdmin(ModelView):
    column_list           = ['id', 'username', 'is_active']
    form_columns          = ['username', 'password', 'is_active']
    form_excluded_columns = ['password_hash', 'devices']
    column_exclude_list   = ['password_hash']
    column_editable_list  = ['is_active']
    can_create            = True
    can_edit              = True
    can_delete            = False

    form_extra_fields = {
        'password': PasswordField('Password')
    }

    def on_model_change(self, form, model, is_created):
        if hasattr(form, 'password') and form.password.data:
            model.password_hash = generate_password_hash(form.password.data)
        elif is_created:
            raise ValueError("建立用戶需要密碼")
        return super().on_model_change(form, model, is_created)

class DeviceAdmin(ModelView):
    column_list          = ['id', 'user.username', 'device_id', 'verified']
    form_columns         = ['user', 'device_id', 'verified']
    column_labels        = {'user.username': 'Username'}
    column_editable_list = ['verified']
    can_create           = False
    can_edit             = True
    can_delete           = False

# 掛載到 Admin
admin.add_view(UserAdmin(User, db.session,   name=_l('使用者'), endpoint='user_admin'))
admin.add_view(DeviceAdmin(Device, db.session, name=_l('裝置'),   endpoint='device_admin'))

# ── 5. REST API 路由 ─────────────────────────────────────────────────────
@app.route('/health', methods=['GET'])
def health():
    return jsonify(status='ok')

@app.route('/auth/register', methods=['POST'])
def auth_register():
    data = request.get_json() or {}
    u, p = data.get('username'), data.get('password')
    if not u or not p:
        return jsonify(error='需要使用者名稱和密碼'), 400
    if User.query.filter_by(username=u).first():
        return jsonify(error='使用者名稱已存在'), 409
    user = User(username=u, password_hash=generate_password_hash(p))
    db.session.add(user)
    db.session.commit()
    return jsonify(msg='使用者創建'), 201

@app.route('/auth/login', methods=['POST'])
def auth_login():
    data = request.get_json() or {}
    u, p = data.get('username'), data.get('password')
    if not u or not p:
        return jsonify(error='需要使用者名稱和密碼'), 400

    user = User.query.filter_by(username=u).first()
    if not user or not check_password_hash(user.password_hash, p):
        return jsonify(error='無效憑證'), 401
    if not user.is_active:
        return jsonify(error='用戶已停用'), 403

    token = create_access_token(identity=user.username)
    return jsonify(access_token=token), 200

@app.route('/devices', methods=['GET'])
@jwt_required()
def list_devices():
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify(error='未找到用戶'), 404
    return jsonify([
        {"device_id": d.device_id, "verified": d.verified}
        for d in user.devices
    ]), 200

@app.route('/devices/register', methods=['POST'])
@jwt_required()
def device_bind():
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify(error='未找到用戶'), 404

    data = request.get_json() or {}
    dev_id = data.get('device_id')
    if not dev_id:
        return jsonify(error='需要 device_id'), 400

    dev = Device.query.filter_by(user=user, device_id=dev_id).first()
    if not dev:
        dev = Device(user=user, device_id=dev_id, verified=False)
        db.session.add(dev)
        db.session.commit()
    return jsonify(device_id=dev.device_id, verified=dev.verified), 200

@app.route('/devices/status', methods=['GET'])
@jwt_required()
def device_status():
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify(error='未找到用戶'), 404

    dev_id = request.args.get('device_id')
    if not dev_id:
        return jsonify(error='需要 device_id'), 400

    dev = Device.query.filter_by(user=user, device_id=dev_id).first()
    if not dev:
        return jsonify(error='設備未綁定'), 404

    return jsonify(device_id=dev.device_id, verified=dev.verified), 200

# ── 啟動 ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    # 啟動前建表
    with app.app_context():
        db.create_all()

    # 啟動服務
    app.run(host='0.0.0.0', port=8000)


