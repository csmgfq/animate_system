"""问卷管理服务 Blueprint"""
from flask import Blueprint, request, jsonify
from bci_flask_services.db import db
from bci_flask_services.models import Question


question_bp = Blueprint('question_service', __name__)


def json_response(code=1, msg="success", data=None):
    return jsonify({"code": code, "msg": msg, "data": data})


@question_bp.route("", methods=["GET"])
def list_questions():
    """查询所有问卷"""
    questions = Question.query.all()
    return json_response(data=[q.to_dict() for q in questions])


@question_bp.route("", methods=["POST"])
def update_question():
    """保存问卷信息（兼容旧/新前端字段，默认 upsert id=1）"""
    payload = request.get_json(force=True, silent=True) or {}
    qid = payload.get("id") or 1

    q = Question.query.get(qid)
    if not q:
        q = Question(id=qid)
        db.session.add(q)

    # 新前端（video.vue）字段：season/movie/music
    # 旧字段：musicInstrument
    season = payload.get("season")
    movie = payload.get("movie")
    music = payload.get("music")
    music_instrument = payload.get("musicInstrument")

    # season 字段可能在历史表结构中不存在；若迁移失败则回退存入 musicInstrument
    if season is not None:
        if hasattr(q, "season"):
            q.season = season
        else:
            q.musicInstrument = season

    if movie is not None:
        q.movie = movie

    if music is not None:
        q.music = music

    if music_instrument is not None:
        q.musicInstrument = music_instrument

    db.session.commit()
    return json_response(data=q.to_dict())
