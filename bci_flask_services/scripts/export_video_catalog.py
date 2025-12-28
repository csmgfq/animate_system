"""Export video catalog from static/video/report.xlsx to JSON.

This keeps the "video tags + link" data in the backend and makes it easy for
/api/video-rec endpoints to load without hardcoding local absolute paths.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in row.items():
        k = str(key).strip()
        if not k or k.lower().startswith("unnamed"):
            continue
        if pd.isna(value):
            continue
        if isinstance(value, str):
            v = value.strip()
            if not v:
                continue
            cleaned[k] = v
        else:
            cleaned[k] = value

    # Best-effort field normalization to stable names.
    # report.xlsx currently uses columns like: tag_names, bilibili_video_urls
    url_keys = [
        "url",
        "link",
        "视频链接",
        "链接",
        "videoUrl",
        "video_url",
        "bilibili_video_urls",
    ]
    tag_keys = [
        "tags",
        "tag",
        "标签",
        "tag_names",
        "text",
        "desc",
        "description",
        "文本",
        "描述",
    ]

    url: str | None = None
    for k in url_keys:
        if k in cleaned:
            url = str(cleaned[k]).strip()
            break

    tags_raw: str | None = None
    for k in tag_keys:
        if k in cleaned:
            tags_raw = str(cleaned[k]).strip()
            break

    tags: list[str] = []
    if tags_raw:
        tags = [t.strip() for t in tags_raw.replace("，", ",").split(",") if t.strip()]

    return {
        "url": url,
        "tags": tags,
        "raw": cleaned,
    }


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    xlsx_path = repo_root / "static" / "video" / "report.xlsx"
    out_path = repo_root / "static" / "video" / "catalog.json"

    if not xlsx_path.exists():
        raise FileNotFoundError(f"Missing: {xlsx_path}")

    df = pd.read_excel(xlsx_path)
    rows = df.to_dict(orient="records")

    catalog = []
    for row in rows:
        normalized = _normalize_row(row)
        # Skip rows with no meaningful content
        if normalized.get("url") is None and normalized.get("text") is None and not normalized["raw"]:
            continue
        catalog.append(normalized)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"items": catalog}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Exported {len(catalog)} items -> {out_path}")


if __name__ == "__main__":
    main()
