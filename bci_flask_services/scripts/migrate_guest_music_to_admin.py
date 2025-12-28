"""Migrate legacy guest music records to a target user (default: admin).

Why:
- Old records were created with file names like *_guest_*.mp3 and had no ownership fields.
- After adding access control, those records become inaccessible unless we backfill ownership.

Usage:
  # Default target is account/username 'admin'
  conda run -n BCIGame --no-capture-output python bci_flask_services/scripts/migrate_guest_music_to_admin.py

  # Override target user
  set TARGET_ACCOUNT=admin
  set TARGET_USERNAME=admin
  python bci_flask_services/scripts/migrate_guest_music_to_admin.py

Optional:
    set DRY_RUN=1          # only prints affected rows count
    set MIGRATE_MODE=...   # guest_only (default) | unowned_all
    set FILE_PATH_LIKE=... # optional SQL LIKE filter (e.g. %_guest_% or %.mp3)

Migration rule:
- Base condition: (user_id IS NULL OR user_id=0)
- Additional conditions depend on MIGRATE_MODE:
    - guest_only: requires file_path LIKE FILE_PATH_LIKE (default: %_guest_%)
    - unowned_all: migrates all unowned rows; FILE_PATH_LIKE can further narrow it
- Sets user_id/user_account/created_at

Note:
- This script does NOT rename files on disk; it only fixes DB ownership.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import or_, and_

# Ensure repo root is on sys.path when executed as a script
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))

from bci_flask_services.app import create_app
from bci_flask_services.db import db
from bci_flask_services.models import User, Music


def main() -> None:
    target_account = (os.getenv("TARGET_ACCOUNT") or "admin").strip()
    target_username = (os.getenv("TARGET_USERNAME") or "admin").strip()
    dry_run = (os.getenv("DRY_RUN") or "").strip() == "1"
    migrate_mode = (os.getenv("MIGRATE_MODE") or "guest_only").strip().lower()
    file_path_like = (os.getenv("FILE_PATH_LIKE") or "").strip()

    app = create_app()
    with app.app_context():
        target = (
            User.query.filter((User.account == target_account) | (User.username == target_username))
            .first()
        )
        if not target:
            raise SystemExit(
                f"Target user not found (TARGET_ACCOUNT={target_account}, TARGET_USERNAME={target_username}). "
                "Please create the user first."
            )

        # Build filter
        base = or_(Music.user_id.is_(None), Music.user_id == 0)

        if migrate_mode not in {"guest_only", "unowned_all"}:
            raise SystemExit("MIGRATE_MODE must be 'guest_only' or 'unowned_all'")

        conditions = [base]

        # Default pattern for legacy guest naming
        if not file_path_like and migrate_mode == "guest_only":
            file_path_like = "%_guest_%"

        if file_path_like:
            conditions.append(Music.file_path.like(file_path_like))
        elif migrate_mode == "guest_only":
            # Safety net: guest_only requires a LIKE condition
            conditions.append(Music.file_path.like("%_guest_%"))

        filt = and_(*conditions)

        count = Music.query.filter(filt).count()
        print(f"Mode={migrate_mode}, FILE_PATH_LIKE={file_path_like or '(none)'}")
        print(f"Found {count} matching unowned music rows.")
        if count == 0:
            return

        if dry_run:
            print("DRY_RUN=1, no changes applied.")
            return

        now = datetime.now()
        # Bulk update
        Music.query.filter(filt).update(
            {
                Music.user_id: target.id,
                Music.user_account: (target.account or target.username or "admin"),
                Music.created_at: now,
            },
            synchronize_session=False,
        )
        db.session.commit()
        print(f"Migrated {count} rows to user_id={target.id}.")


if __name__ == "__main__":
    main()
