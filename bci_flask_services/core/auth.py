from __future__ import annotations

from typing import Optional

from flask import request

from bci_flask_services.models import User


USER_ID_HEADER = "X-User-Id"
USER_ACCOUNT_HEADER = "X-User-Account"


def _safe_int(value: object) -> Optional[int]:
    try:
        if value is None:
            return None
        s = str(value).strip()
        if not s:
            return None
        return int(s)
    except Exception:
        return None


def get_current_user() -> Optional[User]:
    """Best-effort current user resolver.

    Priority:
    1) Header X-User-Id
    2) Header X-User-Account
    3) JSON body field userId/user_id (for backward compatibility)

    This is intentionally minimal (no JWT/session). Frontend should attach X-User-Id.
    """

    uid = _safe_int(request.headers.get(USER_ID_HEADER))
    if uid is None:
        payload = request.get_json(silent=True) or {}
        uid = _safe_int(payload.get("userId") or payload.get("user_id"))

    if uid is not None:
        return User.query.get(uid)

    account = (request.headers.get(USER_ACCOUNT_HEADER) or "").strip()
    if account:
        return User.query.filter((User.account == account) | (User.username == account)).first()

    return None


def is_admin(user: Optional[User]) -> bool:
    if not user:
        return False
    return bool(getattr(user, "is_admin", 0))
