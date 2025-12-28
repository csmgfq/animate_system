"""视频推荐服务 Blueprint

将历史的本地 Flask 脚本（animate/src/文本情感匹配模型.py）能力迁移到后端：
- 从 static/video/catalog.json 加载“标签 + 链接”视频库
- 根据 /api/question 保存的问卷偏好给出一个匹配视频链接
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Any
from collections import Counter
import math
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from flask import Blueprint, jsonify, request

from bci_flask_services.models import Question

video_rec_bp = Blueprint('video_rec_service', __name__)


@video_rec_bp.route("/health", methods=["GET"])
def health():
    """健康检查"""
    return jsonify({"status": "ok", "service": "video_rec_service", "message": "预留接口"})


def _extract_bili_id_from_url(url: str) -> dict[str, str]:
    """从各种 B 站链接中尽量提取 bvid/aid。

    支持：
    - https://www.bilibili.com/video/BVxxxx
    - https://www.bilibili.com/video/av123
    - https://player.bilibili.com/player.html?bvid=... 或 aid=...
    - https://b23.tv/xxxx（需要上游先做一次重定向解析）
    """

    u = (url or "").strip()
    if not u:
        return {}

    # query params (player 形式)
    try:
        parsed = urlparse(u)
        q = parse_qs(parsed.query or "")
        bvid = (q.get("bvid") or [""])[0].strip()
        aid = (q.get("aid") or [""])[0].strip()
        if bvid:
            return {"bvid": bvid}
        if aid.isdigit():
            return {"aid": aid}
    except Exception:
        pass

    # path 形式 /video/BVxxxx 或 /video/av123
    lower = u.lower()
    if "/video/" in lower:
        tail = u.split("/video/", 1)[1]
        seg = tail.split("?", 1)[0].split("#", 1)[0].strip("/")
        # BV...
        if seg.upper().startswith("BV"):
            return {"bvid": seg[:12] if len(seg) >= 12 else seg}
        # av123
        if seg.lower().startswith("av") and seg[2:].isdigit():
            return {"aid": seg[2:]}

    # 兜底：任意位置包含 av123
    for part in u.replace("/", " ").replace("?", " ").replace("#", " ").split():
        if part.lower().startswith("av") and part[2:].isdigit():
            return {"aid": part[2:]}

    return {}


def _resolve_redirect_url(url: str, timeout_sec: float = 6.0) -> str:
    """尝试解析短链最终跳转的 URL。失败则返回原 URL。"""

    u = (url or "").strip()
    if not u:
        return u

    # HEAD 更轻量；若失败再 GET
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        req = Request(u, headers=headers, method="HEAD")
        with urlopen(req, timeout=timeout_sec) as resp:
            return resp.geturl() or u
    except Exception:
        pass

    try:
        req = Request(u, headers=headers, method="GET")
        with urlopen(req, timeout=timeout_sec) as resp:
            return resp.geturl() or u
    except Exception:
        return u


def _fetch_bili_view(bvid: str | None = None, aid: str | None = None, timeout_sec: float = 6.0) -> dict[str, Any] | None:
    """调用 B 站公开 view API 获取视频信息。"""

    if not bvid and not aid:
        return None

    if bvid:
        api = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    else:
        api = f"https://api.bilibili.com/x/web-interface/view?aid={aid}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
        "Accept": "application/json",
    }

    try:
        req = Request(api, headers=headers, method="GET")
        with urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        if int(data.get("code", -1)) != 0:
            return None
        view = data.get("data")
        return view if isinstance(view, dict) else None
    except Exception:
        return None


def _build_bili_embed_url(bvid: str | None = None, aid: str | None = None, cid: str | None = None) -> str:
    if bvid:
        if cid:
            return f"https://player.bilibili.com/player.html?bvid={bvid}&cid={cid}&page=1"
        return f"https://player.bilibili.com/player.html?bvid={bvid}&page=1"
    if aid:
        if cid:
            return f"https://player.bilibili.com/player.html?aid={aid}&cid={cid}&page=1"
        return f"https://player.bilibili.com/player.html?aid={aid}&page=1"
    return ""


@video_rec_bp.route("/bili-meta", methods=["GET"])
def bili_meta():
    """根据 url/bvid/aid 返回 B 站视频宽高信息与推荐 aspectRatio。

    返回：
    - width/height
    - aspectRatioCss: "w / h" 形式（给 CSS aspect-ratio 用）
    - embedUrl: 可直接 iframe 的 player 链接
    """

    raw_url = (request.args.get("url") or "").strip()
    bvid = (request.args.get("bvid") or "").strip()
    aid = (request.args.get("aid") or "").strip()

    final_url = raw_url
    # 对 b23.tv 之类短链尽量解析
    if raw_url and ("b23.tv" in raw_url or "bili2233.cn" in raw_url):
        final_url = _resolve_redirect_url(raw_url)

    if not (bvid or aid) and final_url:
        ids = _extract_bili_id_from_url(final_url)
        bvid = ids.get("bvid", "")
        aid = ids.get("aid", "")

    if not bvid and not aid:
        return jsonify({"code": 0, "msg": "missing bvid/aid", "data": None}), 400

    view = _fetch_bili_view(bvid=bvid or None, aid=aid or None)
    if not view:
        return jsonify({"code": 0, "msg": "bilibili view api failed", "data": None}), 502

    dim = view.get("dimension") if isinstance(view.get("dimension"), dict) else {}
    width = int(dim.get("width") or 0)
    height = int(dim.get("height") or 0)
    cid = str(view.get("cid") or "").strip() or None

    # 有些情况下 cid 在 pages[0]
    if not cid:
        pages = view.get("pages")
        if isinstance(pages, list) and pages:
            p0 = pages[0] if isinstance(pages[0], dict) else {}
            c0 = str(p0.get("cid") or "").strip()
            if c0:
                cid = c0

    if width <= 0 or height <= 0:
        return jsonify({"code": 0, "msg": "missing dimension", "data": None}), 502

    aspect_css = f"{width} / {height}"
    embed_url = _build_bili_embed_url(bvid=bvid or None, aid=aid or None, cid=cid)
    title = str(view.get("title") or "")

    return jsonify({
        "code": 1,
        "msg": "success",
        "data": {
            "width": width,
            "height": height,
            "aspectRatioCss": aspect_css,
            "embedUrl": embed_url,
            "title": title,
            "sourceUrl": final_url or raw_url,
        },
    })


def _catalog_path() -> Path:
    return Path(__file__).resolve().parents[1] / "static" / "video" / "catalog.json"


def _load_catalog() -> list[dict[str, Any]]:
    p = _catalog_path()
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    items = data.get("items") or []
    if not isinstance(items, list):
        return []
    return [i for i in items if isinstance(i, dict) and i.get("url")]


def _split_tokens(value: str | None) -> list[str]:
    if not value:
        return []
    # 前端可能传 "春天, 夏天" 这样的字符串
    norm = value.replace("，", ",")
    parts = [p.strip() for p in norm.split(",") if p.strip()]
    return parts


def _score_item(item: dict[str, Any], tokens: list[str]) -> int:
    tags = item.get("tags") or []
    if not isinstance(tags, list):
        tags = []
    tag_set = {str(t).strip() for t in tags if str(t).strip()}
    # 简单重合计分
    return sum(1 for t in tokens if t in tag_set)


def _score_item_semantic(item: dict[str, Any], tokens: list[str]) -> float:
    """更“语义化”的轻量打分：基于 tags 的词袋余弦相似度。

    说明：
    - 当前视频库给的是离散 tag（已天然分词），用词袋余弦比“重合计数”更平滑。
    - 不依赖外部大模型/下载，适合在线服务。
    """

    tags = item.get("tags") or []
    if not isinstance(tags, list):
        tags = []
    tag_tokens = [str(t).strip() for t in tags if str(t).strip()]

    q = Counter(tokens)
    d = Counter(tag_tokens)
    if not q or not d:
        return 0.0

    # dot(q, d)
    dot = 0.0
    for k, v in q.items():
        dot += float(v) * float(d.get(k, 0))

    q_norm = math.sqrt(sum(float(v) * float(v) for v in q.values()))
    d_norm = math.sqrt(sum(float(v) * float(v) for v in d.values()))
    if q_norm == 0.0 or d_norm == 0.0:
        return 0.0
    return dot / (q_norm * d_norm)


def _parse_k(value: str | None, default: int = 1) -> int:
    try:
        k = int(value) if value is not None else default
    except Exception:
        k = default
    return max(1, min(10, k))


def _safe_tags(item: dict[str, Any]) -> list[str]:
    tags = item.get("tags") or []
    if not isinstance(tags, list):
        return []
    out: list[str] = []
    for t in tags:
        s = str(t).strip()
        if s:
            out.append(s)
    return out


@video_rec_bp.route("/match", methods=["GET"])
def match_video():
    """返回一个匹配的推荐视频链接

    默认读取 question 表 id=1 的问卷结果（与前端流程一致：先 POST /api/question，再 GET /api/video-rec/match）。
    也支持通过 query params 直接传 season/movie/music。
    """

    season = request.args.get("season")
    movie = request.args.get("movie")
    music = request.args.get("music")
    custom = request.args.get("custom") or request.args.get("musicInstrument")

    if not (season or movie or music or custom):
        q = Question.query.get(1)
        if q:
            season = getattr(q, "season", None)
            movie = q.movie
            music = q.music
            custom = getattr(q, "musicInstrument", None)

    tokens = _split_tokens(season) + _split_tokens(movie) + _split_tokens(music) + _split_tokens(custom)
    catalog = _load_catalog()
    if not catalog:
        return jsonify({"code": 0, "msg": "video catalog missing", "data": None}), 500

    k = _parse_k(request.args.get("k"), default=1)

    # 选择匹配策略：
    # - VIDEO_REC_MATCH_MODE=overlap：标签重合计数（最快）
    # - VIDEO_REC_MATCH_MODE=semantic：词袋余弦（更平滑）
    mode = os.getenv("VIDEO_REC_MATCH_MODE", "semantic").strip().lower()

    scored: list[tuple[float, dict[str, Any]]] = []
    if mode == "overlap":
        for item in catalog:
            scored.append((float(_score_item(item, tokens)), item))
    else:
        for item in catalog:
            scored.append((float(_score_item_semantic(item, tokens)), item))

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score = scored[0][0] if scored else -1.0

    # k=1 保持兼容：仍返回 data.url
    if k == 1:
        chosen = scored[0][1] if scored else random.choice(catalog)
        return jsonify({
            "code": 1,
            "msg": "success",
            "data": {
                "url": chosen.get("url"),
                "tags": _safe_tags(chosen),
                "score": best_score,
                "mode": mode,
                "tokens": tokens,
            },
        })

    # k>1：返回多个可选项。
    # 逻辑：如果有有效分数（>0），从 Top 池中抽样；否则随机给 k 个。
    pool: list[tuple[float, dict[str, Any]]]
    if best_score > 0:
        pool = scored[: min(len(scored), max(20, k * 5))]
    else:
        pool = scored

    # 去重 URL，保证给到 k 个不同链接（尽力而为）
    options: list[dict[str, Any]] = []
    seen: set[str] = set()
    candidates = pool[:]
    random.shuffle(candidates)
    for s, item in candidates:
        url = item.get("url")
        if not url or not isinstance(url, str):
            continue
        if url in seen:
            continue
        seen.add(url)
        options.append({"url": url, "score": s, "tags": _safe_tags(item)})
        if len(options) >= k:
            break

    # 兜底：数量不足就从全量里补
    if len(options) < k:
        for s, item in scored:
            url = item.get("url")
            if not url or not isinstance(url, str) or url in seen:
                continue
            seen.add(url)
            options.append({"url": url, "score": s, "tags": _safe_tags(item)})
            if len(options) >= k:
                break

    return jsonify({
        "code": 1,
        "msg": "success",
        "data": {
            "options": options,
            "score": best_score,
            "mode": mode,
            "tokens": tokens,
        },
    })


@video_rec_bp.route("/open-app", methods=["GET"])
def open_app():
    """打开 EEG 采集设备（可选）

    出于安全与可移植性考虑，默认只返回提示信息。
    如需在 Windows 服务器上实际打开程序：设置环境变量 EEG_APP_PATH 指向 .exe/.lnk。
    """

    path = os.getenv("EEG_APP_PATH", "").strip()
    if not path:
        return jsonify({"code": 1, "msg": "success", "data": {"message": "EEG_APP_PATH 未配置，已跳过打开程序"}})

    try:
        os.startfile(path)  # type: ignore[attr-defined]
        return jsonify({"code": 1, "msg": "success", "data": {"message": "已发送打开EEG采集设备指令"}})
    except Exception as e:
        return jsonify({"code": 0, "msg": f"open app failed: {str(e)}", "data": None}), 500


# TODO: 实现视频推荐接口
# @video_rec_bp.route("/recommend", methods=["GET"])
# def recommend_videos():
#     pass

# TODO: 实现用户行为记录接口
# @video_rec_bp.route("/behavior", methods=["POST"])
# def record_behavior():
#     pass
