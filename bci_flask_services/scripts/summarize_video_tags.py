from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def main() -> None:
    catalog_path = Path(__file__).resolve().parents[1] / "static" / "video" / "catalog.json"
    obj = json.loads(catalog_path.read_text(encoding="utf-8"))
    items = obj.get("items", [])

    counter: Counter[str] = Counter()
    for it in items:
        for t in (it.get("tags") or []):
            if not isinstance(t, str):
                continue
            tag = t.strip()
            if tag:
                counter[tag] += 1

    print(f"items={len(items)}")
    print(f"unique_tags={len(counter)}")
    print("\nTop 80 tags:")
    for tag, n in counter.most_common(80):
        print(f"{n:>4}  {tag}")

    out_path = Path(__file__).resolve().parents[1] / "static" / "video" / "tags_summary.json"
    out = {
        "items": len(items),
        "unique_tags": len(counter),
        "top": [{"tag": t, "count": c} for t, c in counter.most_common(200)],
        "all_tags_sorted": sorted(counter.keys()),
    }
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote: {out_path}")


if __name__ == "__main__":
    main()
