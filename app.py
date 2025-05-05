import os
from flask import (
    Flask, request, jsonify,
    redirect, url_for, flash, render_template
)
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity
)
from flask_babel import Babel, lazy_gettext as _l
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from wtforms import PasswordField
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import (
    LoginManager, UserMixin,
    login_user, logout_user,
    login_required, current_user
)
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, PasswordField
from wtforms.validators import DataRequired
from wtforms import Form, StringField, BooleanField
# ── 1. 建立 Flask 應用與設定 ───────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY',
    '開發用_請換成更長的隨機字串'
)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///auth_devices.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['BABEL_DEFAULT_LOCALE'] = 'zh_TW'
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'

# ── 2. 初始化擴充套件 ───────────────────────────────────
db    = SQLAlchemy(app)
jwt   = JWTManager(app)
babel = Babel(app)

login_manager = LoginManager(app)
login_manager.login_view = 'admin_login'

# ── 3. 定義資料模型 ───────────────────────────────────────
class User(db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_active     = db.Column(db.Boolean, default=True)
    devices       = db.relationship('Device', back_populates='user', lazy=True)
    def __str__(self):
        return self.username

class Device(db.Model):
    __tablename__ = 'devices'
    id        = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(128), unique=True, nullable=False)
    verified  = db.Column(db.Boolean, default=False)
    user_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user      = db.relationship('User', back_populates='devices')

class AdminUser(UserMixin, db.Model):
    __tablename__ = 'admin_users'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_active     = db.Column(db.Boolean, default=True)

    # 這兩行讓表單能對應到 password 欄位
    _password = None
    @property
    def password(self):
        return self._password
    @password.setter
    def password(self, value):
        self._password = value

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)


@login_manager.user_loader
def load_admin(uid):
    return AdminUser.query.get(int(uid))


# ── 4. 自訂保護用的 ModelView & IndexView ─────────────────────
class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('admin_login'))

class SecureAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('admin_login'))


class UserForm(Form):
    username  = StringField(_l('使用者名稱'), validators=[DataRequired()])
    is_active = BooleanField(_l('啟用狀態'))
    # 新增可編輯密碼欄位
    password  = PasswordField(_l('新密碼（留空不變更）'))

class UserAdmin(SecureModelView):
    form = UserForm

    column_list          = ['id', 'username', 'is_active']
    column_editable_list = ['is_active']
    column_labels = {
        'id':        _l('編號'),
        'username':  _l('使用者名稱'),
        'is_active': _l('啟用狀態'),
    }

    can_create = True
    can_edit   = True
    can_delete = False

    def on_model_change(self, form, model, is_created):
        # 只有當 form 有 password 屬性（完整表單）時才處理密碼邏輯
        if hasattr(form, 'password'):
            # 建立時必填密碼
            if is_created and not form.password.data:
                raise ValueError(_l('建立使用者需要密碼'))
            # 若填了密碼，就更新 hash
            if form.password.data:
                model.password_hash = generate_password_hash(form.password.data)
        return super().on_model_change(form, model, is_created)





# 定義一張自訂的 WTForms 表單，直接拿給 ModelView 用
class AdminUserForm(FlaskForm):
    username  = StringField(_l('帳號'),     validators=[DataRequired()])
    is_active = BooleanField(_l('啟用狀態'))
    password  = PasswordField(_l('新密碼（留空不變更）'))

# 把 AdminUserAdmin 改成這樣：
class AdminUserAdmin(SecureModelView):
    # 直接指定自訂表單，Flask-Admin 就不會再去合併任何 form_* 屬性
    form = AdminUserForm

    # 列表視圖設定維持不變
    column_list          = ['id', 'username', 'is_active']
    column_editable_list = ['is_active']
    column_labels = {
        'id':        _l('編號'),
        'username':  _l('帳號'),
        'is_active': _l('啟用狀態'),
    }

    can_create = True
    can_edit   = True
    can_delete = False

    # 只有 on_model_change 需要保留：處理密碼欄邏輯
    def on_model_change(self, form, model, is_created):
        if is_created and not form.password.data:
            raise ValueError(_l("建立管理員需要密碼"))
        if form.password.data:
            model.password_hash = generate_password_hash(form.password.data)
        return super().on_model_change(form, model, is_created)



# ── 6. 建立並註冊 Admin ─────────────────────────────────────
admin = Admin(
    app,
    name=_l('管理後臺'),
    index_view=SecureAdminIndexView(),
    template_mode='bootstrap3',
    base_template='admin/custom_master.html',
    translations_path='translations'
)
admin.add_view(UserAdmin(User,           db.session, name=_l('使用者'),   endpoint='user_admin'))
admin.add_view(DeviceAdmin(Device,       db.session, name=_l('裝置'),     endpoint='device_admin'))
admin.add_view(AdminUserAdmin(AdminUser, db.session, name=_l('後臺帳號'), endpoint='admin_user'))


# ── 7. 管理員登入／登出路由 ───────────────────────────────────
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        adm = AdminUser.query.filter_by(username=u).first()
        if adm and adm.is_active and adm.check_password(p):
            login_user(adm)
            return redirect(url_for('admin.index'))
        flash(_l('帳號或密碼錯誤'), 'danger')
    return render_template('admin_login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_login'))


# ── 8. 公開 API 路由 ─────────────────────────────────────
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
    db.session.add(user)
    db.session.commit()
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
        db.session.add(dev)
        db.session.commit()
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


# ── 9. 啟動 & 自動建立預設管理員 ───────────────────────────────
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # 如果尚無任何管理員，則自動建立一組
        if AdminUser.query.count() == 0:
            admin = AdminUser(
                username='admin',
                password_hash=generate_password_hash('0905'),
                is_active=True
            )
            db.session.add(admin)
            db.session.commit()
            print('已自動建立預設管理員：admin / 0905')
    app.run(host='0.0.0.0', port=8000)
