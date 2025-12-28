import os
import sys
from pathlib import Path

# Basic configuration for the Flask app and database connection.
# Adjust the environment variables below to match your local MySQL setup.

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "music_db")

SQLALCHEMY_DATABASE_URI = os.getenv(
    "DATABASE_URL",
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4",
)
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Flask settings
JSON_SORT_KEYS = False
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8088"))

BCI_SERVICE_DIR = Path(__file__).resolve().parent

# 打包后（PyInstaller）运行时，资源通常放在可执行文件同目录（onedir）
if getattr(sys, "frozen", False):
    RUNTIME_BASE_DIR = Path(sys.executable).resolve().parent
else:
    RUNTIME_BASE_DIR = BCI_SERVICE_DIR

# 本地 audiocraft 源码仓库位置（用于 sys.path 注入，让 `import audiocraft` 指向该源码）
# 允许通过环境变量覆盖：AUDIOCRAFT_REPO_DIR
AUDIOCRAFT_REPO_DIR = Path(os.getenv(
    "AUDIOCRAFT_REPO_DIR",
    str(RUNTIME_BASE_DIR / "bci_flask_services" / "audiocraft") if getattr(sys, "frozen", False) else str(BCI_SERVICE_DIR / "audiocraft")
))


def _pick_first_snapshot_dir(snapshots_dir: Path) -> Path | None:
    if not snapshots_dir.exists() or not snapshots_dir.is_dir():
        return None
    subdirs = [p for p in snapshots_dir.iterdir() if p.is_dir()]
    if not subdirs:
        return None
    # snapshot 目录名通常是 hash，排序可保证确定性
    return sorted(subdirs, key=lambda p: p.name)[0]


# MusicGen 本地模型路径（默认指向仓库内 musicgenmodel 的 snapshot；也可用环境变量覆盖）
_DEFAULT_MUSICGEN_SNAPSHOTS_DIR = (
    (RUNTIME_BASE_DIR / "musicgenmodel") if getattr(sys, "frozen", False) else (BCI_SERVICE_DIR / "musicgenmodel")
    / "models--facebook--musicgen-small"
    / "snapshots"
)
_DEFAULT_MUSICGEN_MODEL_PATH = _pick_first_snapshot_dir(_DEFAULT_MUSICGEN_SNAPSHOTS_DIR) or (
    (RUNTIME_BASE_DIR / "musicgenmodel") if getattr(sys, "frozen", False) else (BCI_SERVICE_DIR / "musicgenmodel")
    / "models--facebook--musicgen-small"
)

MUSICGEN_MODEL_PATH = Path(os.getenv(
    "MUSICGEN_MODEL_PATH",
    str(_DEFAULT_MUSICGEN_MODEL_PATH)
))

# HuggingFace / Transformers 本地缓存目录（离线运行需要提前把模型与 tokenizer 下载到这里）
HF_HOME = Path(os.getenv(
    "HF_HOME",
    str(RUNTIME_BASE_DIR / "hf_cache") if getattr(sys, "frozen", False) else str(BCI_SERVICE_DIR / "hf_cache")
))

# 静态文件配置
STATIC_FOLDER = Path(os.getenv(
    "STATIC_FOLDER",
    str(RUNTIME_BASE_DIR / "bci_flask_services" / "static") if getattr(sys, "frozen", False) else str(Path(__file__).parent / "static")
))

# 音乐生成输出目录（务必落在 STATIC_FOLDER 下，前端通过 /static/music/* 访问）
MUSIC_OUTPUT_FOLDER = Path(os.getenv(
    "MUSIC_OUTPUT_FOLDER",
    str(STATIC_FOLDER / "music")
))

# 前端静态资源（Vue build 输出 dist）目录
# 打包/部署时建议将 animate/dist 拷贝到 bci_flask_services/frontend_dist
FRONTEND_DIST_DIR = Path(os.getenv(
    "FRONTEND_DIST_DIR",
    str(RUNTIME_BASE_DIR / "bci_flask_services" / "frontend_dist") if getattr(sys, "frozen", False) else str(BCI_SERVICE_DIR / "frontend_dist")
))

# ============================================
# EEG 设备配置
# ============================================
# 主机 IP（TCP 服务器绑定地址）
EEG_HOST_IP = os.getenv("EEG_HOST_IP", "192.168.1.101")
# TCP 服务器端口
EEG_SERVER_PORT = int(os.getenv("EEG_SERVER_PORT", "5001"))
# EEG 设备 IP
EEG_DEVICE_IP = os.getenv("EEG_DEVICE_IP", "192.168.1.102")
# Trigger 设备 IP
EEG_TRIGGER_IP = os.getenv("EEG_TRIGGER_IP", "192.168.1.103")
# EEG 数据保存目录
EEG_DATA_DIR = Path(os.getenv(
    "EEG_DATA_DIR",
    str(RUNTIME_BASE_DIR / "data") if getattr(sys, "frozen", False) else str(Path(__file__).parent.parent / "data")
))
# 是否自动启动 EEG 服务器（默认关闭，需要手动启动）
EEG_AUTO_START = os.getenv("EEG_AUTO_START", "0").strip().lower() in {"1", "true", "yes", "on"}

