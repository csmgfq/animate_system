"""脑电信号深度推理服务 Blueprint（预留）"""
from flask import Blueprint, jsonify

inference_bp = Blueprint('inference_service', __name__)


@inference_bp.route("/health", methods=["GET"])
def health():
    """健康检查"""
    return jsonify({"status": "ok", "service": "inference_service", "message": "预留接口"})


# TODO: 实现脑电信号推理接口
# @inference_bp.route("/predict", methods=["POST"])
# def predict():
#     pass

# TODO: 实现模型加载接口
# @inference_bp.route("/model/load", methods=["POST"])
# def load_model():
#     pass
