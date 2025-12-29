"""
Flask 模块化单体应用
采用 Blueprint 架构，支持渐进式演进到微服务
"""

import sys
import os
from pathlib import Path
import threading
import time
import importlib
import importlib.util
import importlib.util
import urllib.request

# 如果依赖缺失（常见于未安装 requirements 或双击脚本启动），给出更清晰的错误提示，避免“啥也没出现”。
def _exit_with_missing_dependency(e: ModuleNotFoundError) -> None:
    missing = getattr(e, "name", None) or "unknown"
    print("\n" + "=" * 60)
    print("❌ 依赖缺失，程序未能启动")
    print("=" * 60)
    print(f"Missing module: {missing}")
    print("解决方式：在当前 Python 环境安装依赖：")
    print("  python -m pip install -r requirements.txt")
    print("=" * 60 + "\n")
    try:
        if os.name == "nt" and hasattr(sys, "stdin") and sys.stdin and sys.stdin.isatty():
            input("按 Enter 退出...")
    except Exception:
        pass
    raise SystemExit(1)

# Windows 默认控制台编码可能为 gbk，打印 emoji 会触发 UnicodeEncodeError。
# 这里将输出流切到 utf-8 并用 replace，保证启动日志不因编码问题中断。
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    from flask import Flask, jsonify, request, send_from_directory
    from flask_cors import CORS
    from sqlalchemy import inspect
    from sqlalchemy import text
    from sqlalchemy import create_engine
    from sqlalchemy.engine.url import make_url
    from sqlalchemy.exc import OperationalError
except ModuleNotFoundError as e:
    _exit_with_missing_dependency(e)

from bci_flask_services import config

# 将本地 audiocraft 源码仓库加入导入路径（避免依赖工作目录或外部安装包）
try:
    audiocraft_repo_dir = Path(getattr(config, "AUDIOCRAFT_REPO_DIR", "")).resolve()
    if str(audiocraft_repo_dir) and audiocraft_repo_dir.exists():
        sys.path.insert(0, str(audiocraft_repo_dir))
except Exception:
    # 保持启动健壮性：即使路径异常也不阻断服务启动
    pass
from bci_flask_services.db import db
from bci_flask_services.models import User, Question, Music

# 核心业务蓝图：保持静态导入，确保 PyInstaller 能正确收集这些模块
from bci_flask_services.blueprints.user_service import user_bp
from bci_flask_services.blueprints.question_service import question_bp
from bci_flask_services.blueprints.music_service import music_bp
from bci_flask_services.blueprints.eeg_service import eeg_bp
from bci_flask_services.blueprints.inference_service import inference_bp
from bci_flask_services.blueprints.video_rec_service import video_rec_bp


def _env_flag(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    v = raw.strip().lower()
    return v in {"1", "true", "yes", "on"}


def _register_optional_blueprint(app: Flask, module_path: str, symbol: str, url_prefix: str) -> bool:
    """动态导入并注册可选 Blueprint（用于控制打包体积）。"""
    try:
        module = importlib.import_module(module_path)
        bp = getattr(module, symbol)
        app.register_blueprint(bp, url_prefix=url_prefix)
        return True
    except Exception as e:
        print(f"⚠️  Blueprint 注册失败：{module_path}.{symbol} -> {url_prefix}，原因：{e}")
        return False


def _sync_local_files_to_db(inspector):
    """扫描本地文件同步到数据库"""
    from bci_flask_services.models import EegSession, Music
    import json

    print("\n📂 本地文件同步：")

    # 同步 EEG 会话
    _sync_eeg_sessions(inspector)

    # 同步音乐文件
    _sync_music_files(inspector)


def _sync_eeg_sessions(inspector):
    """同步 EEG 会话到数据库"""
    from bci_flask_services.models import EegSession
    import json

    if 'eeg_session' not in inspector.get_table_names():
        return

    eeg_data_dir = getattr(config, "EEG_DATA_DIR", None)
    if not eeg_data_dir or not Path(eeg_data_dir).exists():
        return

    synced = 0
    for session_dir in Path(eeg_data_dir).rglob("session_*"):
        if not session_dir.is_dir():
            continue

        session_id = session_dir.name
        # 检查是否已存在
        existing = EegSession.query.filter_by(session_id=session_id).first()
        if existing:
            continue

        # 读取 metadata.json
        meta_file = session_dir / "metadata.json"
        meta = {}
        if meta_file.exists():
            try:
                with open(meta_file, "r") as f:
                    meta = json.load(f)
            except Exception:
                pass

        # 查找文件
        eeg_file = None
        trigger_file = None
        for f in session_dir.glob("*_eeg_*.h5"):
            eeg_file = str(f)
            break
        for f in session_dir.glob("*_trigger_*.h5"):
            trigger_file = str(f)
            break

        # 从目录路径推断用户
        user_account = None
        parent = session_dir.parent
        if parent.name != Path(eeg_data_dir).name:
            user_account = parent.name

        # 创建记录
        record = EegSession(
            session_id=session_id,
            user_account=user_account,
            session_dir=str(session_dir),
            eeg_file=eeg_file,
            trigger_file=trigger_file,
            duration=meta.get("duration", 0),
            samples=meta.get("samples", 0)
        )
        db.session.add(record)
        synced += 1

    if synced > 0:
        db.session.commit()
        print(f"   ✅ 同步 {synced} 个 EEG 会话")
    else:
        print(f"   ✅ EEG 会话已是最新")


def _sync_music_files(inspector):
    """同步音乐文件到数据库（解析文件名填充字段）"""
    from datetime import datetime
    from bci_flask_services.models import Music

    if 'music_data' not in inspector.get_table_names():
        return

    music_dir = getattr(config, "MUSIC_OUTPUT_FOLDER", None)
    if not music_dir or not Path(music_dir).exists():
        return

    def _parse_filename(filename: str) -> dict:
        """从文件名解析音乐信息"""
        result = {"genre": None, "timbre": None, "user_account": None, "created_at": None}
        name = Path(filename).stem
        parts = name.split("_")
        if len(parts) >= 4:
            result["genre"] = parts[0]
            result["timbre"] = parts[1]
            result["user_account"] = parts[2]
            try:
                ts_str = "_".join(parts[3:5]) if len(parts) >= 5 else parts[3]
                result["created_at"] = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
            except ValueError:
                pass
        elif len(parts) >= 2:
            result["genre"] = parts[0]
            result["timbre"] = parts[1] if len(parts) > 1 else None
        return result

    synced = 0
    for ext in ("*.mp3", "*.wav"):
        for music_file in Path(music_dir).glob(ext):
            # 使用正确的相对路径格式
            file_path = f"music/{music_file.name}"
            existing = Music.query.filter_by(file_path=file_path).first()
            if existing:
                continue

            parsed = _parse_filename(music_file.name)
            record = Music(
                file_path=file_path,
                genre=parsed.get("genre") or "unknown",
                timbre=parsed.get("timbre") or "unknown",
                description="启动时自动同步",
                user_account=parsed.get("user_account") or "unknown",
                created_at=parsed.get("created_at") or datetime.now(),
            )
            db.session.add(record)
            synced += 1

    if synced > 0:
        db.session.commit()
        print(f"   ✅ 同步 {synced} 个音乐文件")
    else:
        print(f"   ✅ 音乐文件已是最新")


def create_app():
    """Flask 应用工厂函数"""
    # 配置静态文件夹
    static_folder = str(config.STATIC_FOLDER) if hasattr(config, 'STATIC_FOLDER') else None
    app = Flask(__name__, static_folder=static_folder)
    app.config.from_object(config)
    db.init_app(app)
    
    # 启用 CORS
    # Enable cookies for session-based minimal auth.
    CORS(app, supports_credentials=True)

    # Flask session requires a secret key (signed cookie).
    app.config.setdefault("SECRET_KEY", os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-me"))
    
    print("\n" + "="*60)
    print("🚀 Flask 模块化单体应用启动中...")
    print("="*60)

    # 注册 Blueprints（模块化架构）
    # MusicGen 默认启用策略：
    # - 源码运行：默认启用
    # - PyInstaller 打包运行：仅当能导入 audiocraft 时才默认启用（轻量包通常不包含它）
    if getattr(sys, "frozen", False):
        default_enable_musicgen = importlib.util.find_spec("audiocraft") is not None
    else:
        default_enable_musicgen = True
    enable_musicgen = _env_flag("BCI_ENABLE_MUSICGEN", default=default_enable_musicgen)

    # 核心业务服务
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(question_bp, url_prefix='/api/question')
    app.register_blueprint(music_bp, url_prefix='/api/music')

    # 预留的微服务接口
    app.register_blueprint(eeg_bp, url_prefix='/api/eeg')

    # 初始化 EEG 服务（后台线程，不阻塞主线程）
    eeg_initialized = False
    try:
        from bci_flask_services.core.eeg import SessionManager, EEGDeviceServer
        from bci_flask_services.blueprints.eeg_service import init_eeg_service

        eeg_data_dir = getattr(config, "EEG_DATA_DIR", "./data")
        eeg_session_manager = SessionManager(save_dir=eeg_data_dir)

        eeg_server = EEGDeviceServer(
            host_ip=getattr(config, "EEG_HOST_IP", "192.168.1.101"),
            port=getattr(config, "EEG_SERVER_PORT", 5001),
            eeg_ip=getattr(config, "EEG_DEVICE_IP", "192.168.1.102"),
            trigger_ip=getattr(config, "EEG_TRIGGER_IP", "192.168.1.103"),
            session_manager=eeg_session_manager
        )

        init_eeg_service(eeg_server, eeg_session_manager)
        eeg_initialized = True

        # 可选：自动启动 TCP 服务器
        if getattr(config, "EEG_AUTO_START", False):
            eeg_server.start()
            print("   🧠 EEG TCP 服务器已自动启动")
    except Exception as e:
        print(f"⚠️  EEG 服务初始化失败：{e}")

    app.register_blueprint(inference_bp, url_prefix='/api/inference')
    # MusicGen（可选模块）：启用时用常规导入，确保 PyInstaller 能收集该模块
    musicgen_registered = False
    if enable_musicgen:
        try:
            from bci_flask_services.blueprints.music_gen_service import music_gen_bp

            app.register_blueprint(music_gen_bp, url_prefix='/api/music-gen')
            musicgen_registered = True
        except Exception as e:
            print(f"⚠️  music_gen_service 启用失败，将禁用：{e}")
            enable_musicgen = False

    if not enable_musicgen:
        print("⏭️  已禁用 music_gen_service（BCI_ENABLE_MUSICGEN=0 或依赖缺失）")

    app.register_blueprint(video_rec_bp, url_prefix='/api/video-rec')

    print(f"📦 已注册服务模块：")
    print(f"   ✅ 用户管理服务: /api/users")
    print(f"   ✅ 问卷管理服务: /api/question")
    print(f"   ✅ 音乐管理服务: /api/music")
    if eeg_initialized:
        print(f"   ✅ 脑电读写服务: /api/eeg")
    else:
        print(f"   ⚠️  脑电读写服务: /api/eeg (初始化失败)")
    print(f"   ⏸️  脑电推理服务: /api/inference (预留)")
    if enable_musicgen and musicgen_registered:
        print(f"   ✅ 音乐生成服务: /api/music-gen")
    else:
        print(f"   ⏭️  音乐生成服务: /api/music-gen (已禁用)")
    print(f"   ⏸️  视频推荐服务: /api/video-rec (预留)")

    # 健康检查端点
    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "architecture": "modular-monolith"})

    # 前端静态资源（Vue build 输出）
    def _resolve_frontend_dist_dir() -> Path | None:
        candidates: list[Path] = []

        # 1) 显式配置优先
        try:
            raw = getattr(config, "FRONTEND_DIST_DIR", "")
            if raw:
                candidates.append(Path(raw))
        except Exception:
            pass

        # 2) 打包/源码常见相对路径兜底
        try:
            runtime_base = getattr(config, "RUNTIME_BASE_DIR", None)
            if runtime_base:
                rb = Path(runtime_base)
                candidates += [
                    rb / "bci_flask_services" / "frontend_dist",
                    rb / "frontend_dist",
                ]
        except Exception:
            pass

        candidates.append(Path(__file__).resolve().parent / "frontend_dist")

        for c in candidates:
            try:
                p = c.resolve()
                if p.exists() and (p / "index.html").is_file():
                    return p
            except Exception:
                continue
        return None

    frontend_dist_dir = _resolve_frontend_dist_dir()
    if frontend_dist_dir is None:
        print("⚠️  未找到前端 dist（frontend_dist）。访问 / 将返回 404。")
    else:
        print(f"🌐 前端 dist 已启用：{frontend_dist_dir}")
    
    # 静态文件路由（用于访问音乐文件）
    @app.route("/static/<path:filename>", methods=["GET"])
    def serve_static(filename):
        """提供静态文件访问"""
        static_dir = config.STATIC_FOLDER if hasattr(config, 'STATIC_FOLDER') else 'static'
        return send_from_directory(static_dir, filename)

    # 托管 Vue SPA（history 模式兜底）
    # - 真实存在的 dist 文件：直接返回文件
    # - 非文件路由（不含扩展名）：返回 index.html
    # - /api 与 /static 等保留前缀：不在这里接管
    if frontend_dist_dir is not None:
        @app.route("/", defaults={"path": ""})
        @app.route("/<path:path>")
        def serve_frontend(path: str):
            reserved_prefixes = (
                "api/",
                "static/",
            )
            reserved_exact = {
                "api",
                "static",
                "health",
            }

            if path in reserved_exact or any(path.startswith(p) for p in reserved_prefixes):
                # 交给已有路由/错误处理（API 未命中应返回 JSON 404）
                from flask import abort
                abort(404)

            if path:
                candidate = frontend_dist_dir / path
                if candidate.is_file():
                    resp = send_from_directory(frontend_dist_dir, path)
                    # 资产文件（通常带 hash）允许长缓存；index.html 不做长缓存
                    if not path.endswith(".html"):
                        resp.cache_control.public = True
                        resp.cache_control.max_age = 31536000
                    return resp

                # 带扩展名但文件不存在：应返回 404（避免把缺失静态资源误导到 index.html）
                if "." in Path(path).name:
                    from flask import abort
                    abort(404)

            # SPA 路由兜底
            resp = send_from_directory(frontend_dist_dir, "index.html")
            resp.cache_control.no_cache = True
            resp.cache_control.max_age = 0
            return resp
    
    # 服务发现端点
    @app.route("/api/services", methods=["GET"])
    def list_services():
        """列出所有已注册的服务模块"""
        services = [
            {"name": "用户管理", "prefix": "/api/users", "status": "active"},
            {"name": "问卷管理", "prefix": "/api/question", "status": "active"},
            {"name": "音乐管理", "prefix": "/api/music", "status": "active"},
            {"name": "脑电读写", "prefix": "/api/eeg", "status": "reserved"},
            {"name": "脑电推理", "prefix": "/api/inference", "status": "reserved"},
            {"name": "音乐生成", "prefix": "/api/music-gen", "status": "active" if enable_musicgen else "disabled"},
            {"name": "视频推荐", "prefix": "/api/video-rec", "status": "reserved"},
        ]
        return jsonify({"services": services})

    # 错误处理
    @app.errorhandler(404)
    def not_found(e):
        # API/静态资源仍返回 JSON 404
        path = (request.path or "").lstrip("/")
        if path.startswith("api/") or path == "api" or path.startswith("static/") or path == "static":
            {"name": "音乐生成", "prefix": "/api/music-gen", "status": "active" if (enable_musicgen and musicgen_registered) else "disabled"},

        # 非 API：若前端 dist 存在且是 SPA 路由（不含扩展名），返回 index.html
        if frontend_dist_dir is not None:
            if path == "" or "." not in Path(path).name:
                resp = send_from_directory(frontend_dist_dir, "index.html")
                resp.cache_control.no_cache = True
                resp.cache_control.max_age = 0
                return resp

        return jsonify({"code": 0, "msg": "resource not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"code": 0, "msg": "internal server error"}), 500

    # 数据库初始化（智能表检测）
    with app.app_context():
        # 新机器常见：数据库还不存在（MySQL 1049 Unknown database）。
        # 这里仅在“库不存在”时自动创建库；库/表已存在则不做破坏性操作。
        try:
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
        except OperationalError as e:
            # e.orig 通常是 pymysql.err.OperationalError，args[0] 是 MySQL errno。
            mysql_errno = None
            try:
                mysql_errno = getattr(getattr(e, 'orig', None), 'args', [None])[0]
            except Exception:
                mysql_errno = None

            if mysql_errno != 1049:
                raise

            db_url = make_url(app.config["SQLALCHEMY_DATABASE_URI"])
            db_name = db_url.database
            if not db_name:
                raise

            print(f"\n💾 检测到数据库不存在: {db_name}")
            print("   🔧 正在创建数据库（如果不存在）...")

            # 连接到系统库 mysql 来执行 CREATE DATABASE。
            admin_url = db_url.set(database="mysql")
            admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
            try:
                with admin_engine.connect() as conn:
                    conn.execute(
                        text(
                            f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                        )
                    )
            finally:
                admin_engine.dispose()

            print("   ✅ 数据库创建/确认完成，继续初始化表...")

            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
        
        print(f"\n💾 数据库初始化：")
        print(f"   数据库: {config.DB_NAME}")
        print(f"   已存在表: {existing_tables}")
        
        required_tables = {'users', 'question', 'music_data', 'eeg_session'}
        missing_tables = required_tables - set(existing_tables)
        
        if missing_tables:
            print(f"   ⚠️  缺失表: {missing_tables}")
            print(f"   🔧 创建缺失的表...")
            db.create_all()
            print(f"   ✅ 表创建完成")
        else:
            print(f"   ✅ 所有必需的表已存在，跳过创建")

        # 轻量级字段迁移：为 question 表补齐 season 字段（旧版本可能没有）
        try:
            cols = {c.get('name') for c in inspector.get_columns('question')}
            if 'season' not in cols:
                print("   🔧 为 question 表新增 season 字段...")
                db.session.execute(text("ALTER TABLE question ADD COLUMN season VARCHAR(255)"))
                db.session.commit()
                print("   ✅ question.season 字段已添加")
        except Exception as e:
            # 不阻塞应用启动，但会影响视频问卷保存
            print(f"   ⚠️  question 表字段检查/迁移失败: {str(e)}")

        # 轻量级字段迁移：为 users 表补齐 is_admin 字段
        try:
            cols = {c.get('name') for c in inspector.get_columns('users')}
            if 'is_admin' not in cols:
                print("   🔧 为 users 表新增 is_admin 字段...")
                db.session.execute(text("ALTER TABLE users ADD COLUMN is_admin TINYINT(1) DEFAULT 0"))
                db.session.commit()
                print("   ✅ users.is_admin 字段已添加")
        except Exception as e:
            print(f"   ⚠️  users 表字段检查/迁移失败: {str(e)}")

        # 轻量级字段迁移：为 music_data 表补齐 user_id/user_account/created_at 字段
        try:
            cols = {c.get('name') for c in inspector.get_columns('music_data')}
            altered = False
            if 'user_id' not in cols:
                print("   🔧 为 music_data 表新增 user_id 字段...")
                db.session.execute(text("ALTER TABLE music_data ADD COLUMN user_id INT NULL"))
                altered = True
            if 'user_account' not in cols:
                print("   🔧 为 music_data 表新增 user_account 字段...")
                db.session.execute(text("ALTER TABLE music_data ADD COLUMN user_account VARCHAR(255) NULL"))
                altered = True
            if 'created_at' not in cols:
                print("   🔧 为 music_data 表新增 created_at 字段...")
                db.session.execute(text("ALTER TABLE music_data ADD COLUMN created_at DATETIME NULL"))
                altered = True
            if altered:
                db.session.commit()
                print("   ✅ music_data 归属字段已添加")
        except Exception as e:
            print(f"   ⚠️  music_data 表字段检查/迁移失败: {str(e)}")

        # 本地文件同步到数据库
        _sync_local_files_to_db(inspector)

    # 列出核心路由
    print("\n📋 核心 API 端点：")
    core_endpoints = [
        "GET  /health",
        "GET  /api/services",
        "GET  /api/users/info",
        "GET  /api/users",
        "POST /api/users",
        "PUT  /api/users/<id>",
        "DEL  /api/users/<ids>",
        "GET  /api/question",
        "POST /api/question",
        "GET  /api/music",
        "POST /api/music",
    ]
    if enable_musicgen:
        core_endpoints += [
            "GET  /api/music-gen/health",
            "GET  /api/music-gen/test",
            "POST /api/music-gen/submit",
            "POST /api/music-gen/music",
            "POST /api/music-gen/emotion",
        ]
    core_endpoints += [
        "GET  /api/eeg/health",
        "GET  /api/eeg/status",
        "POST /api/eeg/server/start",
        "POST /api/eeg/server/stop",
        "POST /api/eeg/recording/start",
        "POST /api/eeg/recording/stop",
        "GET  /api/eeg/sessions",
        "GET  /api/eeg/realtime",
        "GET  /api/inference/health",
        "GET  /api/video-rec/health",
    ]
    for endpoint in core_endpoints:
        print(f"   • {endpoint}")

    print("\n" + "="*60)
    print(f"✨ Flask 应用就绪，访问 http://localhost:{config.APP_PORT}")
    print(f"💡 架构: 模块化单体 → 支持渐进式演进到微服务")
    print("="*60 + "\n")

    # MusicGen 模型异步预热（启动后不阻塞）
    # 可通过环境变量跳过：SKIP_MUSICGEN_PRELOAD=1
    skip_preload_env = os.getenv("SKIP_MUSICGEN_PRELOAD", "").strip()
    skip_preload_default = True if getattr(sys, "frozen", False) else False
    skip_preload = (skip_preload_env == "1") or (skip_preload_env == "" and skip_preload_default)

    if (not enable_musicgen) or skip_preload:
        print("⏭️  已跳过 MusicGen 模型异步预热（已禁用或默认跳过）")
    else:
        def _async_preload_musicgen() -> None:
            # 稍作延迟，让启动日志先输出、服务先就绪
            time.sleep(0.5)
            print("🔧 MusicGen 模型后台预热开始...")
            try:
                module = importlib.import_module("bci_flask_services.blueprints.music_gen_service")
                getattr(module, "preload_model")()
                print("✅ MusicGen 模型后台预热完成")
            except Exception as e:
                print(f"⚠️  MusicGen 模型后台预热失败: {str(e)}")
                print("⚠️  模型将在首次请求时加载\n")

        threading.Thread(target=_async_preload_musicgen, daemon=True).start()
        print("🧵 已启动 MusicGen 模型后台预热线程")

    return app



if __name__ == "__main__":
    # CLI flags:
    # - --desktop: 打开内嵌桌面窗口（pywebview）
    # - --no-desktop: 强制仅服务模式
    # - --dual: 桌面窗口 + 局域网绑定（0.0.0.0）
    try:
        import argparse

        parser = argparse.ArgumentParser(add_help=True)
        parser.add_argument("--desktop", action="store_true")
        parser.add_argument("--no-desktop", action="store_true")
        parser.add_argument("--dual", action="store_true")
        args, _unknown = parser.parse_known_args()

        if args.dual:
            os.environ["BCI_DESKTOP"] = "1"
            os.environ["BCI_DESKTOP_BIND_ALL"] = "1"
            os.environ["APP_HOST"] = "0.0.0.0"
        elif args.desktop:
            os.environ["BCI_DESKTOP"] = "1"
        elif args.no_desktop:
            os.environ["BCI_DESKTOP"] = "0"
    except Exception:
        # 向后兼容旧参数
        if "--dual" in sys.argv:
            os.environ["BCI_DESKTOP"] = "1"
            os.environ["BCI_DESKTOP_BIND_ALL"] = "1"
            os.environ["APP_HOST"] = "0.0.0.0"

    app = create_app()
    debug_env = os.getenv("FLASK_DEBUG", os.getenv("APP_DEBUG", "")).strip().lower()
    debug = debug_env in {"1", "true", "yes", "on"}

    host_cfg = getattr(config, "APP_HOST", "0.0.0.0")
    port_cfg = getattr(config, "APP_PORT", 8088)

    # Windows 桌面端模式（pywebview）：
    # - 默认关闭（推荐使用 Electron 作为前端）
    # - 可用 --desktop 或 BCI_DESKTOP=1 手动开启
    desktop_default = False
    desktop_mode = _env_flag("BCI_DESKTOP", default=desktop_default)

    # 默认同时支持“桌面窗口 + 局域网访问”：桌面窗口仍使用 127.0.0.1 打开，但后端绑定 0.0.0.0 供同网段访问。
    # 如需仅本机访问，可设置 BCI_DESKTOP_BIND_ALL=0 或使用 --no-desktop。
    desktop_bind_all = _env_flag("BCI_DESKTOP_BIND_ALL", default=True)

    def _wait_http_ready(url: str, timeout_sec: float = 12.0) -> bool:
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=1.2) as resp:
                    if 200 <= int(getattr(resp, "status", 200)) < 500:
                        return True
            except Exception:
                time.sleep(0.2)
        return False


    def _run_server() -> None:
        # 桌面模式默认只监听本机；如需“桌面 + 局域网共存”，设置 BCI_DESKTOP_BIND_ALL=1
        if desktop_mode:
            bind_host = "0.0.0.0" if desktop_bind_all else "127.0.0.1"
        else:
            bind_host = host_cfg
        app.run(
            host=bind_host,
            port=port_cfg,
            debug=debug,
            use_reloader=False,  # 禁用热重载，避免重复启动
            threaded=True,
        )


    if desktop_mode:
        # 桌面端：主线程跑 pywebview，Flask 服务在子线程
        base_url = f"http://127.0.0.1:{port_cfg}/"

        def _run_server_bg():
            _run_server()

        flask_thread = threading.Thread(target=_run_server_bg, daemon=True)
        flask_thread.start()

        # 等待服务可用
        ready = _wait_http_ready(f"http://127.0.0.1:{port_cfg}/health") or _wait_http_ready(base_url)
        if not ready:
            print("⚠️  桌面窗口启动前等待服务超时，将尝试继续打开窗口")

        try:
            webview = importlib.import_module("webview")  # pywebview
            webview.create_window("BCI App", base_url, width=1200, height=800)
            webview.start()
        except Exception as e:
            print(f"⚠️  桌面窗口启动失败，将回退到浏览器：{e}")
            try:
                import webbrowser
                webbrowser.open(base_url, new=1)
            except Exception:
                pass

        # 桌面窗口关闭即退出进程
        raise SystemExit(0)

    # 非桌面模式：直接运行 Flask 服务，默认绑定 0.0.0.0（局域网可访问）
    auto_open_default = True if getattr(sys, "frozen", False) else False
    auto_open = _env_flag("BCI_AUTO_OPEN_BROWSER", default=auto_open_default)
    if auto_open:
        def _open_browser() -> None:
            try:
                import webbrowser
                time.sleep(1.0)
                host = host_cfg or "127.0.0.1"
                # APP_HOST 可能是 0.0.0.0，浏览器应使用 127.0.0.1
                if host in {"0.0.0.0", "::"}:
                    host = "127.0.0.1"
                webbrowser.open(f"http://{host}:{port_cfg}/", new=1)
            except Exception:
                pass

        threading.Thread(target=_open_browser, daemon=True).start()

    _run_server()
