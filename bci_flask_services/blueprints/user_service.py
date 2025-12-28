"""用户管理服务 Blueprint"""
from flask import Blueprint, request, jsonify
from bci_flask_services.db import db
from bci_flask_services.models import User
from bci_flask_services.core.auth import get_current_user, is_admin


user_bp = Blueprint('user_service', __name__)


def json_response(code=1, msg="success", data=None):
    return jsonify({"code": code, "msg": msg, "data": data})


def _norm(value):
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _username_account_conflict(*, username: str | None, account: str | None, exclude_user_id: int | None = None) -> bool:
    """Return True if username/account conflicts with existing users."""
    username = _norm(username)
    account = _norm(account)
    if not username and not account:
        return False

    q = User.query
    if exclude_user_id is not None:
        q = q.filter(User.id != exclude_user_id)

    if username and account:
        return q.filter((User.username == username) | (User.account == account)).first() is not None
    if username:
        return q.filter(User.username == username).first() is not None
    return q.filter(User.account == account).first() is not None


@user_bp.route("/login", methods=["POST"])
def login():
    """用户登录（最小实现）

    兼容前端字段：username/password。
    - username 可匹配 users.username 或 users.account
    - password 明文比对（如需更安全可改为哈希存储）
    """
    payload = request.get_json(force=True, silent=True) or {}
    username = (payload.get("username") or payload.get("account") or "").strip()
    password = (payload.get("password") or "").strip()

    if not username or not password:
        return json_response(code=0, msg="missing username/password"), 400

    user = (
        User.query.filter((User.username == username) | (User.account == username))
        .first()
    )
    if not user:
        return json_response(code=0, msg="user not found"), 404

    if (user.password or "") != password:
        return json_response(code=0, msg="invalid password"), 401

    # 不实现复杂鉴权，返回用户信息供前端保存
    return json_response(data={"user": user.to_dict()})


@user_bp.route("/register", methods=["POST"])
def register():
    """用户注册（最小实现）

    允许传入 username/account/password 等字段。
    """
    payload = request.get_json(force=True, silent=True) or {}
    username = (payload.get("username") or "").strip()
    account = (payload.get("account") or username).strip()
    password = (payload.get("password") or "").strip()

    if not username or not password:
        return json_response(code=0, msg="missing username/password"), 400

    if User.query.filter((User.username == username) | (User.account == account)).first():
        return json_response(code=0, msg="user already exists"), 409

    user = User(
        username=username,
        account=account,
        password=password,
        gender=payload.get("gender"),
        occupation=payload.get("occupation"),
        birthday=payload.get("birthday"),
        phone=payload.get("phone"),
        email=payload.get("email"),
    )
    db.session.add(user)
    db.session.commit()
    return json_response(data={"user": user.to_dict()})


@user_bp.route("/info", methods=["GET"])
def list_users():
    """查询用户基本信息"""
    current = get_current_user()
    if not is_admin(current):
        return json_response(code=0, msg="forbidden"), 403
    users = User.query.all()
    return json_response(data=[u.to_dict() for u in users])


@user_bp.route("/me", methods=["GET"])
def get_me():
    """获取当前登录用户信息（普通用户仅能查看自己）"""
    current = get_current_user()
    if not current:
        return json_response(code=0, msg="unauthorized"), 401
    return json_response(data={"user": current.to_dict()})


@user_bp.route("/me", methods=["PUT"])
def update_me():
    """更新当前登录用户信息（普通用户仅能修改自己）"""
    current = get_current_user()
    if not current:
        return json_response(code=0, msg="unauthorized"), 401

    payload = request.get_json(force=True, silent=True) or {}
    next_username = payload.get("username", current.username)
    next_account = payload.get("account", current.account)
    if _username_account_conflict(username=next_username, account=next_account, exclude_user_id=current.id):
        return json_response(code=0, msg="username/account already exists"), 409
    # 仅允许更新个人资料字段
    current.username = payload.get("username", current.username)
    current.gender = payload.get("gender", current.gender)
    current.occupation = payload.get("occupation", current.occupation)
    current.birthday = payload.get("birthday", current.birthday)
    current.phone = payload.get("phone", current.phone)
    current.email = payload.get("email", current.email)
    # account 允许自改会影响登录名，这里默认允许（如需禁止可删掉这一行）
    current.account = payload.get("account", current.account)
    if payload.get("password"):
        current.password = payload.get("password")

    db.session.commit()
    return json_response(data={"user": current.to_dict()})


@user_bp.route("", methods=["GET"])
def list_all_users():
    """查询所有用户（支持分页和筛选）"""
    current = get_current_user()
    if not is_admin(current):
        return json_response(code=0, msg="forbidden"), 403
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("pageSize", 10))
    username = request.args.get("username")
    gender = request.args.get("gender")
    occupation = request.args.get("occupation")

    query = User.query
    if username:
        query = query.filter(User.username.like(f"%{username}%"))
    if gender:
        query = query.filter(User.gender == gender)
    if occupation:
        query = query.filter(User.occupation.like(f"%{occupation}%"))

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return json_response(data={"total": total, "rows": [u.to_dict() for u in items]})


@user_bp.route("/<ids>", methods=["DELETE"])
def delete_users(ids: str):
    """批量删除用户"""
    current = get_current_user()
    if not is_admin(current):
        return json_response(code=0, msg="forbidden"), 403
    id_list = [int(i) for i in ids.split(",") if i.strip().isdigit()]
    if not id_list:
        return json_response(code=0, msg="no ids provided"), 400
    User.query.filter(User.id.in_(id_list)).delete(synchronize_session=False)
    db.session.commit()
    return json_response()


@user_bp.route("", methods=["POST"])
def add_user():
    """新增用户"""
    current = get_current_user()
    if not is_admin(current):
        return json_response(code=0, msg="forbidden"), 403
    payload = request.get_json(force=True, silent=True) or {}
    if _username_account_conflict(username=payload.get("username"), account=payload.get("account"), exclude_user_id=None):
        return json_response(code=0, msg="username/account already exists"), 409
    user = User(
        username=payload.get("username"),
        gender=payload.get("gender"),
        occupation=payload.get("occupation"),
        birthday=payload.get("birthday"),
        phone=payload.get("phone"),
        email=payload.get("email"),
        account=payload.get("account"),
        password=payload.get("password"),
    )
    db.session.add(user)
    db.session.commit()
    return json_response(data=user.to_dict())


@user_bp.route("/<int:user_id>", methods=["PUT"])
def update_user(user_id: int):
    """更新用户信息"""
    current = get_current_user()
    if not current:
        return json_response(code=0, msg="unauthorized"), 401
    if (not is_admin(current)) and (current.id != user_id):
        return json_response(code=0, msg="forbidden"), 403
    user = User.query.get(user_id)
    if not user:
        return json_response(code=0, msg="user not found"), 404
    payload = request.get_json(force=True, silent=True) or {}
    next_username = payload.get("username", user.username)
    next_account = payload.get("account", user.account)
    if _username_account_conflict(username=next_username, account=next_account, exclude_user_id=user.id):
        return json_response(code=0, msg="username/account already exists"), 409
    user.username = payload.get("username", user.username)
    user.gender = payload.get("gender", user.gender)
    user.occupation = payload.get("occupation", user.occupation)
    user.birthday = payload.get("birthday", user.birthday)
    user.phone = payload.get("phone", user.phone)
    user.email = payload.get("email", user.email)
    user.account = payload.get("account", user.account)
    if payload.get("password"):
        user.password = payload.get("password")
    db.session.commit()
    return json_response(data=user.to_dict())
