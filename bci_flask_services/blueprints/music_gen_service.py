"""音乐生成服务 Blueprint"""
import os
import sys
from pathlib import Path
from flask import Blueprint, request, jsonify, send_from_directory
import random
import re
import threading

from bci_flask_services import config

# 兜底：确保能导入仓库内的 audiocraft（不依赖 app.py 的 sys.path 注入）
try:
    _audiocraft_repo_dir = Path(getattr(config, "AUDIOCRAFT_REPO_DIR", "")).resolve()
    if str(_audiocraft_repo_dir) and _audiocraft_repo_dir.exists():
        sys.path.insert(0, str(_audiocraft_repo_dir))
except Exception:
    pass

# 设置离线模式
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_DATASETS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

music_gen_bp = Blueprint('music_gen_service', __name__)

# 全局变量存储模型
_musicgen_model = None
_model_loading = False
_model_lock = threading.Lock()
_model_ready = threading.Event()


def _get_model_local_path() -> Path:
    return Path(config.MUSICGEN_MODEL_PATH).resolve()


def _configure_hf_caches() -> None:
    """配置 HuggingFace/Transformers 缓存目录。

    目的：离线模式下，transformers 会从本地缓存读取 t5-base 等依赖模型。
    """
    hf_home = Path(config.HF_HOME).resolve()
    hf_home.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(hf_home))
    # transformers 旧/新版本都会读取这些变量之一
    os.environ.setdefault("HF_HUB_CACHE", str(hf_home / "hub"))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(hf_home / "hub"))
    os.environ.setdefault("HF_DATASETS_CACHE", str(hf_home / "datasets"))


def _select_device(prefer_cuda: bool = True) -> str:
    """选择推理设备。

    - 优先 CUDA，但会检查当前 PyTorch 是否包含该 GPU 架构的内核。
    - 对于像 RTX 5090（sm_120）这类新架构，如果 torch 版本较老，
      会出现 `no kernel image is available`，这里提前回退到 CPU。
    """
    override = os.getenv("MUSICGEN_DEVICE", "").strip().lower()
    if override in {"cpu", "cuda"}:
        prefer_cuda = (override == "cuda")
    if not prefer_cuda:
        return "cpu"
    try:
        import torch

        if not torch.cuda.is_available():
            return "cpu"

        major, minor = torch.cuda.get_device_capability(0)
        target = f"sm_{major}{minor}"

        # torch.cuda.get_arch_list() 在多数 CUDA 构建中可用
        try:
            supported = set(torch.cuda.get_arch_list())
        except Exception:
            supported = set()

        # 如果能拿到支持列表且不包含当前设备架构，则直接回退 CPU
        if supported and target not in supported:
            print(
                f"⚠️  CUDA 架构不匹配：设备 {target} 不在当前 PyTorch 支持列表中：{sorted(supported)}。将回退到 CPU。"
            )
            print("   建议：升级/重装支持该显卡架构的 PyTorch（通常需要更新到较新的版本与 CUDA 构建）。")
            return "cpu"

        try:
            torch.backends.cuda.matmul.allow_tf32 = True
        except Exception:
            pass
        try:
            torch.set_float32_matmul_precision("high")
        except Exception:
            pass

        return "cuda"
    except Exception:
        return "cpu"


def _load_musicgen_model():
    _configure_hf_caches()
    from audiocraft.models import musicgen

    model_local_path = _get_model_local_path()
    if not model_local_path.exists():
        raise FileNotFoundError(f"本地模型路径不存在: {model_local_path}")

    os.environ.setdefault("AUDIOCRAFT_CACHE_DIR", str(model_local_path))

    device = _select_device(prefer_cuda=True)
    print(f"🎛️ MusicGen 使用设备: {device}")
    if device == "cpu":
        print("⚠️  当前在 CPU 上推理会明显偏慢；如需 GPU，请确保 PyTorch 与显卡架构匹配。")

    model = musicgen.MusicGen.get_pretrained(
        'facebook/musicgen-small', device=device, local_path=str(model_local_path)
    )
    model.set_generation_params(duration=16)
    return model

def preload_model():
    """预加载模型（在应用启动时调用）"""
    global _musicgen_model, _model_loading
    
    with _model_lock:
        if _musicgen_model is not None or _model_loading:
            return
        _model_loading = True
        _model_ready.clear()
    
    try:
        print('🎵 MusicGen 模型预加载中...')
        _musicgen_model = _load_musicgen_model()
        print('✅ MusicGen 模型预加载完成')
    except Exception as e:
        msg = str(e)
        print(f'❌ 模型预加载失败: {msg}')
        if "Can't load tokenizer for 't5-base'" in msg or "Can't load tokenizer for \"t5-base\"" in msg:
            print("⚠️  检测到缺少 t5-base，本地离线缓存未准备好。")
            print("   解决：先把 t5-base 下载到本地缓存目录后再启动服务。")
            print("   参考脚本：bci_flask_services/aitest/download_hf_assets.py")
        print('⚠️  模型将在首次请求时加载')
        _musicgen_model = None
    finally:
        with _model_lock:
            _model_loading = False
            _model_ready.set()

def get_model():
    """获取模型（如果未加载则加载）"""
    global _musicgen_model
    with _model_lock:
        if _musicgen_model is not None:
            return _musicgen_model
        if _model_loading:
            waiter = _model_ready
        else:
            _model_loading = True
            _model_ready.clear()
            waiter = None

    if waiter is not None:
        waiter.wait(timeout=600)
        with _model_lock:
            if _musicgen_model is not None:
                return _musicgen_model
        raise RuntimeError("MusicGen 模型加载失败或超时，请查看启动日志。")

    try:
        print('🎵 MusicGen 模型加载中...')
        model = _load_musicgen_model()
        print('✅ MusicGen 模型加载完成')
        with _model_lock:
            _musicgen_model = model
        return model
    finally:
        with _model_lock:
            _model_loading = False
            _model_ready.set()

def init_translator():
    """翻译已停用，占位以保持接口兼容。"""
    return

def offline_translate(text, from_lang="zh", to_lang="en"):
    """
    离线翻译（使用 transformers，本地缓存）
    完全本地运行，无需联网
    """
    return text


def _sanitize_tag(value: str, fallback: str = "guest") -> str:
    v = (value or "").strip()
    if not v:
        return fallback
    v = re.sub(r"[^a-zA-Z0-9_-]+", "_", v)
    v = re.sub(r"_+", "_", v).strip("_")
    return v or fallback


def _parse_music_filename(filename: str) -> dict:
    """从文件名解析音乐信息。

    支持的文件名格式：
    - {genre}_{timbre}_{user}_{timestamp}.mp3/wav
    - 例如：pop_piano_admin_20250101_120000.mp3

    Returns:
        dict: {genre, timbre, user_account, created_at} 或空字段
    """
    from datetime import datetime

    result = {"genre": None, "timbre": None, "user_account": None, "created_at": None}

    # 去掉扩展名
    name = Path(filename).stem
    parts = name.split("_")

    if len(parts) >= 4:
        result["genre"] = parts[0]
        result["timbre"] = parts[1]
        result["user_account"] = parts[2]
        # 尝试解析时间戳 (格式: YYYYMMDD_HHMMSS)
        try:
            ts_str = "_".join(parts[3:5]) if len(parts) >= 5 else parts[3]
            result["created_at"] = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
        except ValueError:
            pass
    elif len(parts) >= 2:
        result["genre"] = parts[0]
        result["timbre"] = parts[1] if len(parts) > 1 else None

    return result


def _check_music_exists(file_path: str) -> bool:
    """检查音乐文件是否已存在于数据库中"""
    from bci_flask_services.models import Music
    return Music.query.filter_by(file_path=file_path).first() is not None


@music_gen_bp.route("/health", methods=["GET"])
def health():
    """健康检查"""
    return jsonify({
        "status": "ok", 
        "service": "music_gen_service",
        "model_loaded": _musicgen_model is not None
    })


@music_gen_bp.route("/test", methods=["GET"])
def test():
    """测试端点"""
    return jsonify({"message": "Music Gen Service is working!"})


@music_gen_bp.route("/submit", methods=["POST"])
def submit_music():
    """生成音乐并保存到数据库"""
    from bci_flask_services.db import db
    from bci_flask_services.models import Music
    from bci_flask_services.core.auth import get_current_user, is_admin
    import torch
    import torchaudio
    
    data = request.get_json()
    if not data or not all(key in data for key in ['genre', 'timbre', 'description']):
        return jsonify({'error': 'Missing required fields: genre, timbre, description'}), 400

    try:
        from datetime import datetime
        from bci_flask_services import config
        
        # 提取参数
        genre = data['genre']
        timbre = data['timbre']
        description = data['description']
        current = get_current_user()
        # 兼容旧字段 userId，但优先使用登录用户
        legacy_user_id = data.get('userId')
        user_tag = "guest"
        owner_user_id = None
        owner_account = "guest"
        if current:
            owner_user_id = current.id
            if is_admin(current):
                owner_account = "admin"
                user_tag = "admin"
            else:
                owner_account = (current.account or current.username or "guest")
                user_tag = _sanitize_tag(str(current.account or current.username or current.id), fallback="guest")
        elif legacy_user_id:
            user_tag = _sanitize_tag(str(legacy_user_id), fallback="guest")

        # 生成参数字符串，直接使用原始描述（不翻译）
        translated_description = description
        params_str = f"{genre}, {timbre}, {translated_description}"
        print(f"生成音乐参数: {params_str}")
        
        # 加载模型并生成音乐
        model = get_model()
        res = model.generate([params_str], progress=True)
        
        # 转换音频张量
        audio = res[0].cpu().detach().numpy()

        def _to_audio_tensor(x):
            t = torch.as_tensor(x)
            if t.ndim == 1:
                t = t.unsqueeze(0)
            # torchaudio.save 更偏好 float32/float16 或 int16
            if t.dtype not in (torch.float16, torch.float32, torch.int16, torch.int32):
                t = t.float()
            return t

        def _save_audio_with_fallback(base_path_no_ext, waveform, sample_rate: int):
            """优先保存 mp3，失败时自动回退 wav。返回 (file_path, file_name)。"""
            # 先尝试 mp3
            mp3_path = Path(str(base_path_no_ext) + ".mp3")
            try:
                torchaudio.save(str(mp3_path), waveform, sample_rate)
                # 某些 Windows 环境下 mp3 编码可能“无报错但产出空壳文件”（只有 ID3 头，无法播放）。
                # 这里做一个最小健壮性检查：太小就回退 wav。
                try:
                    if mp3_path.exists() and mp3_path.stat().st_size < 4096:
                        raise RuntimeError(f"mp3 too small: {mp3_path.stat().st_size} bytes")
                except Exception as _size_err:
                    try:
                        mp3_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    wav_path = Path(str(base_path_no_ext) + ".wav")
                    torchaudio.save(str(wav_path), waveform, sample_rate)
                    return wav_path, wav_path.name
                return mp3_path, mp3_path.name
            except Exception as e:
                msg = str(e)
                # torchaudio 在缺失 torchcodec/torchcodec backend 不可用时，常见报错会提到 TorchCodec
                if "TorchCodec" not in msg and "torchcodec" not in msg.lower():
                    raise
                wav_path = Path(str(base_path_no_ext) + ".wav")
                torchaudio.save(str(wav_path), waveform, sample_rate)
                return wav_path, wav_path.name

        # 构建文件路径（使用配置文件中的路径）
        output_folder = config.MUSIC_OUTPUT_FOLDER
        output_folder.mkdir(parents=True, exist_ok=True)
        
        # 优化文件命名：标签_用户_时间戳.mp3
        # 优化文件命名：标签_用户_时间戳（扩展名由保存逻辑决定）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = f'{genre}_{timbre}_{user_tag}_{timestamp}'
        base_path_no_ext = output_folder / base_name
        
        # 保存音频文件
        # 保存音频文件（mp3 优先，必要时回退 wav）
        waveform = _to_audio_tensor(audio)
        file_path, file_name = _save_audio_with_fallback(base_path_no_ext, waveform, 32000)
        print(f'✅ 音频已保存到: {file_path}')

        # 保存到数据库（使用相对路径）
        relative_path = f'music/{file_name}'

        # 查重：检查文件是否已存在于数据库
        if _check_music_exists(relative_path):
            print(f'⚠️ 文件已存在于数据库: {relative_path}')
            existing = Music.query.filter_by(file_path=relative_path).first()
            return jsonify({
                'message': 'Music already exists',
                'data': existing.to_dict() if existing else {'filePath': relative_path}
            }), 200

        music_entry = Music(
            genre=genre,
            timbre=timbre,
            description=translated_description,
            file_path=relative_path,
            user_id=owner_user_id,
            user_account=owner_account,
            created_at=datetime.now(),
        )
        db.session.add(music_entry)
        db.session.commit()
        
        return jsonify({
            'message': 'Music generated successfully',
            'data': {
                'id': music_entry.id,
                'genre': genre,
                'timbre': timbre,
                'description': translated_description,
                'filePath': relative_path,
                'fileName': file_name,
                'fileUrl': f'/static/music/{file_name}'
            }
        }), 200
        
    except Exception as e:
        print(f"❌ 生成音乐时出错: {str(e)}")
        return jsonify({'error': f'Failed to generate music: {str(e)}'}), 500


@music_gen_bp.route("/music", methods=["POST"])
def get_music():
    """根据文件路径获取音乐URL"""
    data = request.get_json()
    if not data or 'filePath' not in data:
        return jsonify({'error': 'No filePath provided'}), 400

    file_path = data['filePath']

    # 确保文件路径安全
    if not file_path.endswith(('.mp3', '.wav')):
        return jsonify({'error': 'Invalid file format'}), 400

    try:
        # 从数据库查询音乐
        from bci_flask_services.models import Music
        from bci_flask_services.core.auth import get_current_user, is_admin
        current = get_current_user()
        if not current:
            return jsonify({'error': 'unauthorized'}), 401
        music = Music.query.filter_by(file_path=file_path).first()
        
        if music:
            if (not is_admin(current)) and (getattr(music, 'user_id', None) != current.id):
                return jsonify({'error': 'forbidden'}), 403
            # 转换为可访问的 URL
            file_name = os.path.basename(music.file_path)
            file_url = f'/static/music/{file_name}'
            
            return jsonify({
                'fileUrl': file_url,
                'data': [music.to_dict()]
            }), 200
        else:
            return jsonify({'error': 'Music not found in database'}), 404
            
    except Exception as e:
        print(f"❌ 获取音乐时出错: {str(e)}")
        return jsonify({'error': f'Failed to get music: {str(e)}'}), 500


@music_gen_bp.route("/emotion", methods=["POST"])
def emotion_process():
    """情感分析处理（简化版）"""
    data = request.get_json()
    file_path = data.get('filePath') if data else None
    
    # 简单随机返回情感（可以扩展为真实的情感识别）
    emotion_text = random.choice(["Happy", "Sad", "Calm", "Angry"])
    
    return jsonify({
        "emotionText": emotion_text,
        "filePath": file_path
    })


@music_gen_bp.route("/sync", methods=["POST"])
def sync_music_files():
    """扫描音乐目录，将未入库的文件同步到数据库。

    - 自动解析文件名填充 genre、timbre、user_account、created_at
    - 跳过已存在的文件（基于 file_path 查重）
    - 仅管理员可调用
    """
    from datetime import datetime
    from bci_flask_services.db import db
    from bci_flask_services.models import Music
    from bci_flask_services.core.auth import get_current_user, is_admin

    current = get_current_user()
    if not current or not is_admin(current):
        return jsonify({"code": 0, "msg": "仅管理员可执行同步操作"}), 403

    output_folder = config.MUSIC_OUTPUT_FOLDER
    if not output_folder.exists():
        return jsonify({"code": 0, "msg": f"音乐目录不存在: {output_folder}"}), 404

    added = []
    skipped = []
    errors = []

    for ext in ("*.mp3", "*.wav"):
        for file_path in output_folder.glob(ext):
            file_name = file_path.name
            relative_path = f"music/{file_name}"

            # 查重
            if _check_music_exists(relative_path):
                skipped.append(file_name)
                continue

            # 解析文件名
            parsed = _parse_music_filename(file_name)

            try:
                music_entry = Music(
                    genre=parsed.get("genre") or "unknown",
                    timbre=parsed.get("timbre") or "unknown",
                    description="从文件同步导入",
                    file_path=relative_path,
                    user_id=None,
                    user_account=parsed.get("user_account") or "unknown",
                    created_at=parsed.get("created_at") or datetime.now(),
                )
                db.session.add(music_entry)
                added.append(file_name)
            except Exception as e:
                errors.append({"file": file_name, "error": str(e)})

    if added:
        db.session.commit()

    return jsonify({
        "code": 1,
        "msg": f"同步完成: 新增 {len(added)}, 跳过 {len(skipped)}, 失败 {len(errors)}",
        "data": {"added": added, "skipped": skipped, "errors": errors}
    })
