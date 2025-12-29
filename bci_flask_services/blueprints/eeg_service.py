"""
脑电读写服务 Blueprint
提供 EEG 设备连接、录制控制和状态查询的 REST API
"""
from flask import Blueprint, jsonify, request, current_app
from pathlib import Path
from datetime import datetime
from bci_flask_services.core.auth import get_current_user

eeg_bp = Blueprint('eeg_service', __name__)

# 全局引用（在 app.py 中初始化）
_eeg_server = None
_session_manager = None


def init_eeg_service(eeg_server, session_manager):
    """初始化 EEG 服务（由 app.py 调用）"""
    global _eeg_server, _session_manager
    _eeg_server = eeg_server
    _session_manager = session_manager


@eeg_bp.route("/health", methods=["GET"])
def health():
    """健康检查 - 即使服务未初始化也返回正常"""
    try:
        from bci_flask_services.core.eeg import realtime_stats
        stats = realtime_stats.get_stats()
        return jsonify({
            "status": "ok",
            "service": "eeg_service",
            "initialized": _session_manager is not None,
            "eeg_connected": stats["eeg"]["connected"],
            "trigger_connected": stats["trigger"]["connected"],
            "recording": stats["recording"]
        })
    except Exception:
        return jsonify({
            "status": "ok",
            "service": "eeg_service",
            "initialized": False,
            "eeg_connected": False,
            "trigger_connected": False,
            "recording": False
        })


@eeg_bp.route("/status", methods=["GET"])
def get_status():
    """获取详细状态 - 服务未初始化时返回默认状态"""
    try:
        from bci_flask_services.core.eeg import realtime_stats
        realtime = realtime_stats.get_stats()
    except Exception:
        realtime = {
            "eeg": {"connected": False, "received": 0, "loss_rate": 0, "dropped": 0, "padded": 0},
            "trigger": {"connected": False, "received": 0, "loss_rate": 0, "dropped": 0, "padded": 0, "last_value": 0},
            "recording": False,
            "session_id": "",
            "duration": 0
        }

    if _session_manager is None:
        return jsonify({
            "code": 1,
            "data": {
                "session": {
                    "is_recording": False,
                    "current_session": None,
                    "eeg_connected": False,
                    "trigger_connected": False,
                    "total_samples": 0
                },
                "realtime": realtime,
                "server_running": False,
                "initialized": False
            }
        })

    session_status = _session_manager.get_status()

    return jsonify({
        "code": 1,
        "data": {
            "session": session_status,
            "realtime": realtime,
            "server_running": _eeg_server.running if _eeg_server else False,
            "initialized": True
        }
    })


@eeg_bp.route("/server/start", methods=["POST"])
def start_server():
    """启动 TCP 服务器"""
    if _eeg_server is None:
        return jsonify({"code": 0, "msg": "EEG 服务未初始化，请检查配置"})

    success, msg = _eeg_server.start()
    return jsonify({"code": 1 if success else 0, "msg": msg})


@eeg_bp.route("/server/stop", methods=["POST"])
def stop_server():
    """停止 TCP 服务器"""
    if _eeg_server is None:
        return jsonify({"code": 0, "msg": "EEG 服务未初始化"})

    success, msg = _eeg_server.stop()
    return jsonify({"code": 1 if success else 0, "msg": msg})


@eeg_bp.route("/server/send-start-cmd", methods=["POST"])
def send_start_cmd():
    """发送启动指令到设备"""
    if _eeg_server is None:
        return jsonify({"code": 0, "msg": "EEG service not initialized"}), 503

    _eeg_server.send_start_cmd()
    return jsonify({"code": 1, "msg": "Start command sent"})


@eeg_bp.route("/recording/start", methods=["POST"])
def start_recording():
    """开始录制（支持用户关联）"""
    if _session_manager is None:
        return jsonify({"code": 0, "msg": "EEG service not initialized"}), 503

    # 获取用户信息：优先使用 core.auth.get_current_user()（与 user_service 一致）
    # 建议前端统一在请求头带 X-User-Id / X-User-Account；保留 body 兼容字段作为兜底。
    current = get_current_user()
    user_id = current.id
    user_account = current.account
    if user_id is None and user_account is None:
        return jsonify({"code": 0, "msg": "unauthorized: missing user identity"}), 401

    # 调用带用户信息的录制
    success, result = _session_manager.start_new_session(
        user_id=user_id,
        user_account=user_account
    )
    if success:
        return jsonify({
            "code": 1,
            "msg": "Recording started",
            "session_id": result
        })
    else:
        return jsonify({"code": 0, "msg": result})


@eeg_bp.route("/recording/stop", methods=["POST"])
def stop_recording():
    """停止录制并保存到数据库"""
    if _session_manager is None:
        return jsonify({"code": 0, "msg": "EEG service not initialized"}), 503

    success, result = _session_manager.stop_session()
    if success:
        # 保存到数据库
        try:
            _save_session_to_db(result)
        except Exception as e:
            print(f"⚠️ 保存 EEG 会话到数据库失败: {e}")

        return jsonify({
            "code": 1,
            "msg": "Recording stopped",
            "session_id": result
        })
    else:
        return jsonify({"code": 0, "msg": result})


@eeg_bp.route("/sessions", methods=["GET"])
def get_sessions():
    """获取所有录制会话列表"""
    if _session_manager is None:
        return jsonify({"code": 0, "msg": "EEG service not initialized"}), 503

    sessions = _session_manager.get_sessions()
    sessions_data = []
    for s in sessions:
        sessions_data.append({
            "id": s.get("id"),
            "dir": str(s.get("dir", "")),
            "start_time": s.get("start_time"),
            "end_time": s.get("end_time"),
            "samples": s.get("samples", 0),
            "duration": s.get("duration", 0)
        })

    return jsonify({"code": 1, "data": sessions_data})


@eeg_bp.route("/realtime", methods=["GET"])
def get_realtime_stats():
    """获取实时统计数据"""
    from bci_flask_services.core.eeg import realtime_stats
    return jsonify({"code": 1, "data": realtime_stats.get_stats()})


def _save_session_to_db(session_id: str):
    """保存会话记录到数据库"""
    from bci_flask_services.db import db
    from bci_flask_services.models import EegSession

    if _session_manager is None:
        return

    # 从 sessions 列表中找到对应会话
    session_data = None
    for s in _session_manager.sessions:
        if s.get("id") == session_id:
            session_data = s
            break

    if session_data is None:
        return

    # 查找 EEG 和 Trigger 文件
    session_dir = Path(session_data.get("dir", ""))
    eeg_file = None
    trigger_file = None

    if session_dir.exists():
        for f in session_dir.glob("*_eeg_*.h5"):
            eeg_file = str(f)
            break
        for f in session_dir.glob("*_trigger_*.h5"):
            trigger_file = str(f)
            break

    # 解析时间
    start_time = None
    end_time = None
    try:
        if session_data.get("start_time"):
            start_time = datetime.fromisoformat(session_data["start_time"])
        if session_data.get("end_time"):
            end_time = datetime.fromisoformat(session_data["end_time"])
    except Exception:
        pass

    # 创建数据库记录
    record = EegSession(
        session_id=session_id,
        user_id=session_data.get("user_id"),
        user_account=session_data.get("user_account"),
        session_dir=str(session_dir),
        eeg_file=eeg_file,
        trigger_file=trigger_file,
        duration=session_data.get("duration", 0),
        samples=session_data.get("samples", 0),
        start_time=start_time,
        end_time=end_time
    )

    db.session.add(record)
    db.session.commit()
