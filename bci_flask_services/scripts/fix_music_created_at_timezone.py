"""Fix music_data.created_at timezone mismatch.

Background
- Earlier versions wrote created_at using datetime.utcnow() (UTC) into a MySQL DATETIME column.
- When viewing in DB or UI as local time (e.g. Asia/Shanghai), it looks "wrong" (typically -8 hours).

This script shifts existing timestamps by an offset.

Usage (Windows cmd)
- Dry run:
  set DRY_RUN=1
  set OFFSET_HOURS=8
  python -m bci_flask_services.scripts.fix_music_created_at_timezone

- Apply:
  set DRY_RUN=0
  set OFFSET_HOURS=8
  python -m bci_flask_services.scripts.fix_music_created_at_timezone

Notes
- OFFSET_HOURS should match your local timezone offset from UTC.
- This updates ONLY rows where created_at is NOT NULL.
"""

from __future__ import annotations

import os
from datetime import timedelta

from bci_flask_services.app import create_app
from bci_flask_services.db import db
from bci_flask_services.models import Music


def main() -> None:
    app = create_app()
    with app.app_context():
        dry_run = os.getenv("DRY_RUN", "1").strip() != "0"
        offset_hours = int(os.getenv("OFFSET_HOURS", "8").strip() or "8")

        if offset_hours == 0:
            print("OFFSET_HOURS=0, nothing to do")
            return

        q = Music.query.filter(Music.created_at.isnot(None))
        total = q.count()
        print(f"Found {total} music rows with created_at")

        delta = timedelta(hours=offset_hours)
        updated = 0

        for m in q.yield_per(200):
            m.created_at = m.created_at + delta  # type: ignore[operator]
            updated += 1

        if dry_run:
            db.session.rollback()
            print(f"DRY_RUN=1: would update {updated} rows, rolled back")
        else:
            db.session.commit()
            print(f"Updated {updated} rows, committed")


if __name__ == "__main__":
    main()
