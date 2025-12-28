"""音乐管理服务 Blueprint"""
from pathlib import Path
from flask import Blueprint, request, jsonify
from bci_flask_services.db import db
from bci_flask_services.models import Music
from bci_flask_services.core.auth import get_current_user, is_admin
from bci_flask_services import config


music_bp = Blueprint('music_service', __name__)


def json_response(code=1, msg="success", data=None):
    return jsonify({"code": code, "msg": msg, "data": data})


@music_bp.route("", methods=["GET"])
def list_music():
    """查询音乐（默认仅返回当前用户；管理员可返回全部）"""
    current = get_current_user()
    if not current:
        return json_response(code=0, msg="unauthorized"), 401

    query = Music.query
    if not is_admin(current):
        # 同时支持 user_id 和 user_account 匹配（兼容旧数据）
        user_account = getattr(current, 'account', None) or getattr(current, 'username', None)
        if user_account:
            query = query.filter(
                (Music.user_id == current.id) | (Music.user_account == user_account)
            )
        else:
            query = query.filter(Music.user_id == current.id)
    items = query.order_by(Music.id.desc()).all()
    return json_response(data=[m.to_dict() for m in items])


@music_bp.route("", methods=["POST"])
def update_music():
    """更新音乐信息"""
    current = get_current_user()
    if not current:
        return json_response(code=0, msg="unauthorized"), 401
    payload = request.get_json(force=True, silent=True) or {}
    mid = payload.get("id") or 1
    m = Music.query.get(mid)
    if not m:
        return json_response(code=0, msg="music not found"), 404
    if (not is_admin(current)) and (m.user_id != current.id):
        return json_response(code=0, msg="forbidden"), 403
    m.genre = payload.get("genre", m.genre)
    m.timbre = payload.get("timbre", m.timbre)
    m.description = payload.get("description", m.description)
    m.file_path = payload.get("filePath", payload.get("file_path", m.file_path))
    db.session.commit()
    return json_response(data=m.to_dict())


@music_bp.route("/<int:mid>", methods=["DELETE"])
def delete_music(mid: int):
    """删除音乐：删除数据库记录 + 删除本地静态文件（仅允许本人或管理员）。"""
    current = get_current_user()
    if not current:
        return json_response(code=0, msg="unauthorized"), 401

    m = Music.query.get(mid)
    if not m:
        return json_response(code=0, msg="music not found"), 404

    if (not is_admin(current)) and (getattr(m, "user_id", None) != current.id):
        return json_response(code=0, msg="forbidden"), 403

    deleted_file = False
    file_error = None
    try:
        rel = (m.file_path or "").strip()
        if rel:
            rel = rel.lstrip("/\\")
            rel_path = Path(rel)
            if rel_path.is_absolute() or ".." in rel_path.parts:
                file_error = "unsafe_path"
            else:
                static_root = Path(config.STATIC_FOLDER).resolve()
                abs_path = (static_root / rel_path).resolve()
                # 确保在 static_root 下
                abs_path.relative_to(static_root)
                if abs_path.exists() and abs_path.is_file():
                    abs_path.unlink()
                    deleted_file = True
    except Exception as e:
        file_error = str(e)

    db.session.delete(m)
    db.session.commit()
    return json_response(data={"id": mid, "deleted_file": deleted_file, "file_error": file_error})
