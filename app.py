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
from wtforms import PasswordField, StringField, BooleanField, Form
from wtforms.validators import DataRequired
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import (
    LoginManager, UserMixin,
    login_user, logout_user,
    login_required, current_user
)
from flask_wtf import FlaskForm

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '開發用_請換成更長的隨機字串')
# 把 SQLite 存到 /tmp，Cloud Run 這裡可寫
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/auth_devices.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['BABEL_DEFAULT_LOCALE'] = 'zh_TW'
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'

db    = SQLAlchemy(app)
jwt   = JWTManager(app)
babel = Babel(app)

login_manager = LoginManager(app)
login_manager.login_view = 'admin_login'


# ─── 資料模型 ─────────────────────────────────────────────
class User(db.Model):
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

class AdminUser(UserMixin, db.Model):
    __tablename__ = 'admin_users'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_active     = db.Column(db.Boolean, default=True)
    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)


# ─── Admin 介面安全設定 ─────────────────────────────────
class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated
    def inaccessible_callback(self, name, **kw):
        return redirect(url_for('admin_login'))
    def get_actions(self):
        return {}

class SecureAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated
    def inaccessible_callback(self, name, **kw):
        return redirect(url_for('admin_login'))


# ─── Flask-Admin View ────────────────────────────────────
class UserForm(Form):
    username  = StringField(_l('使用者名稱'), validators=[DataRequired()])
    is_active = BooleanField(_l('啟用狀態'))
    password  = PasswordField(_l('新密碼（留空不變更）'))

class UserAdmin(SecureModelView):
    form = UserForm
    column_list          = ['id','username','is_active']
    column_editable_list = ['is_active']
    can_create = can_edit = can_delete = True
    def on_model_change(self, form, model, created):
        pw = getattr(form, 'password', None)
        if created and (not pw or not pw.data):
            raise ValueError(_l('建立使用者需要密碼'))
        if pw and pw.data:
            model.password_hash = generate_password_hash(pw.data)
        return super().on_model_change(form, model, created)

class DeviceAdmin(SecureModelView):
    column_list  = ['id','user.username','device_id','verified']
    form_columns = ['user','device_id','verified']
    column_editable_list = ['verified']
    can_create = False
    can_edit = can_delete = True

class AdminUserForm(FlaskForm):
    username  = StringField(_l('帳號'), validators=[DataRequired()])
    is_active = BooleanField(_l('啟用狀態'))
    password  = PasswordField(_l('新密碼（留空不變更）'))

class AdminUserAdmin(SecureModelView):
    form = AdminUserForm
    column_list          = ['id','username','is_active']
    column_editable_list = ['is_active']
    can_create = can_edit = can_delete = True
    def on_model_change(self, form, model, created):
        pw = getattr(form, 'password', None)
        if created and (not pw or not pw.data):
            raise ValueError(_l('建立管理員需要密碼'))
        if pw and pw.data:
            model.password_hash = generate_password_hash(pw.data)
        return super().on_model_change(form, model, created)


# ─── 登記 Admin ───────────────────────────────────────────
admin = Admin(
    app,
    name=_l('管理後臺'),
    index_view=SecureAdminIndexView(),
    template_mode='bootstrap3',
    translations_path='translations'
)
admin.add_view(UserAdmin(User, db.session,      name=_l('使用者')))
admin.add_view(DeviceAdmin(Device, db.session,  name=_l('裝置')))
admin.add_view(AdminUserAdmin(AdminUser, db.session, name=_l('後臺帳號')))


# ─── Admin 登入/登出 ─────────────────────────────────────
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method=='POST':
        u=request.form['username']; p=request.form['password']
        adm=AdminUser.query.filter_by(username=u).first()
        if adm and adm.is_active and adm.check_password(p):
            login_user(adm)
            return redirect(url_for('admin.index'))
        flash(_l('帳號或密碼錯誤'),'danger')
    return render_template('admin_login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_login'))


# ─── 公開 API ─────────────────────────────────────────────
@app.route('/health')
def health():
    return jsonify(status='ok')

@app.route('/auth/register', methods=['POST'])
def auth_register():
    data = request.get_json() or {}
    u,p = data.get('username'), data.get('password')
    if not u or not p:
        return jsonify(error=_l('需要使用者名稱和密碼')),400
    if User.query.filter_by(username=u).first():
        return jsonify(error=_l('使用者名稱已存在')),409
    usr=User(username=u,password_hash=generate_password_hash(p))
    db.session.add(usr); db.session.commit()
    return jsonify(msg=_l('使用者創建')),201

@app.route('/auth/login', methods=['POST'])
def auth_login():
    data=request.get_json() or {}
    u,p=data.get('username'),data.get('password')
    if not u or not p:
        return jsonify(error=_l('需要使用者名稱和密碼')),400
    usr=User.query.filter_by(username=u).first()
    if not usr or not check_password_hash(usr.password_hash,p):
        return jsonify(error=_l('無效憑證')),401
    if not usr.is_active:
        return jsonify(error=_l('用戶已停用')),403
    tok=create_access_token(identity=usr.username)
    return jsonify(access_token=tok),200

@app.route('/devices', methods=['GET'])
@jwt_required()
def list_devices():
    usr=User.query.filter_by(username=get_jwt_identity()).first()
    if not usr:
        return jsonify(error=_l('未找到用戶')),404
    return jsonify([{'device_id':d.device_id,'verified':d.verified} for d in usr.devices]),200

@app.route('/devices/register', methods=['POST'])
@jwt_required()
def device_bind():
    usr=User.query.filter_by(username=get_jwt_identity()).first_or_404()
    dev_id=(request.get_json() or {}).get('device_id')
    if not dev_id:
        return jsonify(error=_l('需要裝置 ID')),400
    d=Device.query.filter_by(user_id=usr.id,device_id=dev_id).first()
    if not d:
        d=Device(user_id=usr.id,device_id=dev_id,verified=False)
        db.session.add(d); db.session.commit()
    return jsonify(device_id=d.device_id,verified=d.verified),200

@app.route('/devices/verify', methods=['POST'])
@jwt_required()
def device_verify():
    usr=User.query.filter_by(username=get_jwt_identity()).first_or_404()
    dev_id=(request.get_json() or {}).get('device_id')
    if not dev_id:
        return jsonify(error=_l('需要裝置 ID')),400
    Device.query.filter_by(user_id=usr.id,verified=True).delete(synchronize_session=False)
    d=Device.query.filter_by(user_id=usr.id,device_id=dev_id).first()
    if d:
        d.verified=True
    else:
        d=Device(user=usr,device_id=dev_id,verified=True)
        db.session.add(d)
    db.session.commit()
    return jsonify(device_id=d.device_id,verified=d.verified),200

@app.route('/devices/status')
@jwt_required()
def device_status():
    usr=User.query.filter_by(username=get_jwt_identity()).first()
    if not usr:
        return jsonify(error=_l('未找到用戶')),404
    dev_id=request.args.get('device_id')
    if not dev_id:
        return jsonify(error=_l('需要裝置 ID')),400
    d=Device.query.filter_by(user=usr,device_id=dev_id).first()
    if not d:
        return jsonify(error=_l('設備未綁定')),404
    return jsonify(device_id=d.device_id,verified=d.verified),200


# ─── 啟動前務必建表＆塞預設管理員 ────────────────────────
def init_app():
    with app.app_context():
        db.create_all()
        if AdminUser.query.count()==0:
            adm=AdminUser(username='admin',
                          password_hash=generate_password_hash('0905'),
                          is_active=True)
            db.session.add(adm)
            db.session.commit()
            print('已自動建立預設管理員：admin / 0905')

init_app()

if __name__=='__main__':
    # Cloud Run 會用 PORT env
    port=int(os.environ.get('PORT',8000))
    app.run(host='0.0.0.0',port=port)
