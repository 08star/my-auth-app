import os
import uuid
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity
)
from flask_babel import Babel, lazy_gettext as _l, gettext, ngettext
import flask_admin as admin_ext
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from wtforms import PasswordField
from werkzeug.security import generate_password_hash, check_password_hash

# ── 1. 建立 Flask 應用與設定 ───────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY',
    '開發用_請換成更長的隨機字串'
)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///auth_devices.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Babel 設定
app.config['BABEL_DEFAULT_LOCALE'] = 'zh_TW'
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'

# ── 2. 初始化擴充套件 ────────────────────────────────────────────────────
db    = SQLAlchemy(app)
jwt   = JWTManager(app)
babel = Babel(app)

# 告訴 Jinja2 啟用 i18n
app.jinja_env.add_extension('jinja2.ext.i18n')
# Monkey‐patch Flask-Admin 的翻譯函式
admin_ext.babel.gettext  = gettext
admin_ext.babel.ngettext = ngettext

# 建立 Admin
admin = Admin(
  app,
  name=_l('管理後臺'),
  template_mode='bootstrap3',
  base_template='admin/custom_master.html',   # ← 這行要有
  translations_path='translations'
)


from flask_babel import gettext as _

class UserAdmin(ModelView):
    # 原本的設定…
    column_list  = ['id', 'username', 'is_active']
    form_columns = ['username', 'password', 'is_active']
    # 加上這段，告訴它要怎麼顯示欄位名稱
    column_labels = {
        'id':        _('編號'),
        'username':  _('使用者名稱'),
        'is_active': _('啟用狀態'),
    }
    # 同理，表單欄位也可以自訂 label
    form_args = {
        'username': {'label': _('使用者名稱')},
        'password': {'label': _('密碼')},
        'is_active': {'label': _('啟用狀態')},
    }
    form_extra_fields = {
        'password': PasswordField(_('密碼'))
    }
    # …其餘不變

class DeviceAdmin(ModelView):
    column_list = ['id', 'user.username', 'device_id', 'verified']
    column_labels = {
        'id':            _('編號'),
        'user.username': _('使用者'),
        'device_id':     _('裝置 ID'),
        'verified':      _('已驗證'),
    }
    form_args = {
        'user':      {'label': _('使用者')},
        'device_id': {'label': _('裝置 ID')},
        'verified':  {'label': _('已驗證')},
    }
    # …其餘不變



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


