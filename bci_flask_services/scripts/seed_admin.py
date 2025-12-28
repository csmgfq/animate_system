"""Seed an initial admin user into the MySQL database.

Usage:
  conda run -n BCIGame --no-capture-output python bci_flask_services/scripts/seed_admin.py

Env overrides:
  ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_ACCOUNT
"""

from __future__ import annotations

import os

import sys
from pathlib import Path

# Ensure repo root is on sys.path when executed as a script
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))

from bci_flask_services.app import create_app
from bci_flask_services.db import db
from bci_flask_services.models import User


def main() -> None:
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "123456")
    account = os.getenv("ADMIN_ACCOUNT", username)

    app = create_app()
    with app.app_context():
        exists = User.query.filter((User.username == username) | (User.account == account)).first()
        if exists:
            print("Admin already exists")
            return

        user = User(username=username, account=account, password=password, is_admin=1)
        db.session.add(user)
        db.session.commit()
        print(f"Seeded admin user: {username}")


if __name__ == "__main__":
    main()
