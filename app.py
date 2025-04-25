import os
from flask import Flask, request, jsonify, redirect, url_for, render_template, flash
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity
)
from flask_babel import Babel, lazy_gettext as _l, gettext, ngettext
import flask_admin as admin_ext
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import (
    LoginManager, UserMixin,
    login_user, logout_user,
    current_user, login_required
)
from wtforms import PasswordField
from werkzeug.security import generate_password_hash, check_password_hash
from flask import redirect, url_for, request
from flask_login import current_user

# ── 1. 建立 Flask 應用與設定 ───────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY', 
    '開發用_請換成更長的隨機字串'
)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///auth_devices.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['BABEL_DEFAULT_LOCALE'] = 'zh_TW'
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'

# ── 2. 初始化 Extension ────────────────────────────────────────────────────
db    = SQLAlchemy(app)
jwt   = JWTManager(app)
babel = Babel(app)

# Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'admin_login'

# 啟用 Jinja2 i18n extension，並 Monkey-patch Flask-Admin 的翻譯函式
app.jinja_env.add_extension('jinja2.ext.i18n')
admin_ext.babel.gettext  = gettext
admin_ext.babel.ngettext = ngettext

# ── 3. 定義資料模型 ──────────────────────────────────────────────────────
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_active     = db.Column(db.Boolean, default=True)
    devices       = db.relationship('Device', back_populates='user', lazy=True)

class Device(db.Model):
    __tablename__ = 'devices'
    id        = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(128), unique=True, nullable=False)
    verified  = db.Column(db.Boolean, default=False)
    user_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user      = db.relationship('User', back_populates='devices')

# User Loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ── 4. 自訂 AdminIndexView 與 SecureModelView ─────────────────────────────
class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not current_user.is_authenticated:
            return redirect(url_for('admin_login', next=request.url))
        return super().index()

class SecureModelView(ModelView):
    """所有後台 View 都要繼承這個，才能強制登入檢查"""
    def is_accessible(self):
        # 只有已登入的使用者才能存取
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        # 未登入時，導到 /admin/login
        return redirect(url_for('admin_login', next=request.url))

class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        # 若還沒登入，就跳去 /admin/login
        if not current_user.is_authenticated:
            return redirect(url_for('admin_login', next=request.url))
        return super().index()
# ── 5. 建立 Admin 並掛上 View ────────────────────────────────────────────
admin = Admin(
    app,
    name=_l('管理後臺'),
    index_view=MyAdminIndexView(),
    template_mode='bootstrap3',
    base_template='admin/custom_master.html',
    translations_path='translations'
)

class UserAdmin(SecureModelView):
    column_list  = ['id', 'username', 'is_active']
    column_labels = {
        'id':        _l('編號'),
        'username':  _l('使用者名稱'),
        'is_active': _l('啟用狀態'),
    }
    form_columns = ['username', 'password', 'is_active']
    form_args = {
        'username': {'label': _l('使用者名稱')},
        'password': {'label': _l('密碼')},
        'is_active': {'label': _l('啟用狀態')},
    }
    form_extra_fields = {
        'password': PasswordField(_l('密碼'))
    }
    form_excluded_columns = ['password_hash', 'devices']
    column_editable_list  = ['is_active']
    can_create            = True
    can_edit              = True
    can_delete            = False

    def on_model_change(self, form, model, is_created):
        if hasattr(form, 'password') and form.password.data:
            model.password_hash = generate_password_hash(form.password.data)
        elif is_created:
            raise ValueError(_l("建立用戶需要密碼"))
        return super().on_model_change(form, model, is_created)
        
class DeviceAdmin(SecureModelView):
    column_list  = ['id', 'user.username', 'device_id', 'verified']
    column_labels = {
        'id':            _l('編號'),
        'user.username': _l('使用者'),
        'device_id':     _l('裝置 ID'),
        'verified':      _l('已驗證'),
    }
    form_columns = ['user', 'device_id', 'verified']
    form_args = {
        'user':      {'label': _l('使用者')},
        'device_id': {'label': _l('裝置 ID')},
        'verified':  {'label': _l('已驗證')},
    }
    column_editable_list = ['verified']
    can_create           = False
    can_edit             = True
    can_delete           = False

admin.add_view(UserAdmin(User, db.session, name=_l('使用者'), endpoint='user_admin'))
admin.add_view(DeviceAdmin(Device, db.session, name=_l('裝置'), endpoint='device_admin'))

# ── 6. 登入／登出 Route ────────────────────────────────────────────────────
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
        flash(_l('帳號或密碼錯誤'), 'danger')
    return render_template('admin_login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_login'))

# ── 7. REST API 路由 ─────────────────────────────────────────────────────
@app.route('/health', methods=['GET'])
def health():
    return jsonify(status='ok')

@app.route('/auth/register', methods=['POST'])
def auth_register():
    data = request.get_json() or {}
    u, p = data.get('username'), data.get('password')
    if not u or not p:
        return jsonify(error=_l('需要使用者名稱和密碼')), 400
    if User.query.filter_by(username=u).first():
        return jsonify(error=_l('使用者名稱已存在')), 409
    user = User(username=u, password_hash=generate_password_hash(p))
    db.session.add(user); db.session.commit()
    return jsonify(msg=_l('使用者創建')), 201

@app.route('/auth/login', methods=['POST'])
def auth_login():
    data = request.get_json() or {}
    u, p = data.get('username'), data.get('password')
    if not u or not p:
        return jsonify(error=_l('需要使用者名稱和密碼')), 400

    user = User.query.filter_by(username=u).first()
    if not user or not check_password_hash(user.password_hash, p):
        return jsonify(error=_l('無效憑證')), 401
    if not user.is_active:
        return jsonify(error=_l('用戶已停用')), 403

    token = create_access_token(identity=user.username)
    return jsonify(access_token=token), 200

@app.route('/devices', methods=['GET'])
@jwt_required()
def list_devices():
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify(error=_l('未找到用戶')), 404
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
        return jsonify(error=_l('未找到用戶')), 404

    data = request.get_json() or {}
    dev_id = data.get('device_id')
    if not dev_id:
        return jsonify(error=_l('需要裝置 ID')), 400

    dev = Device.query.filter_by(user=user, device_id=dev_id).first()
    if not dev:
        dev = Device(user=user, device_id=dev_id, verified=False)
        db.session.add(dev); db.session.commit()
    return jsonify(device_id=dev.device_id, verified=dev.verified), 200

@app.route('/devices/status', methods=['GET'])
@jwt_required()
def device_status():
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify(error=_l('未找到用戶')), 404

    dev_id = request.args.get('device_id')
    if not dev_id:
        return jsonify(error=_l('需要裝置 ID')), 400

    dev = Device.query.filter_by(user=user, device_id=dev_id).first()
    if not dev:
        return jsonify(error=_l('設備未綁定')), 404

    return jsonify(device_id=dev.device_id, verified=dev.verified), 200

# ── 8. 啟動 ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=8000)
