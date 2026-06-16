import os


def _split_admin_ids(raw: str = "") -> set[str]:
    ids: set[str] = set()
    for item in str(raw or "").replace(";", ",").split(","):
        value = item.strip()
        if value:
            ids.add(value)
    return ids


def configured_admin_ids() -> set[str]:
    ids: set[str] = set()
    for key in ("ADMIN_IDS", "ADMIN_ID", "OWNER_TELEGRAM_ID", "ADMIN_TELEGRAM_IDS"):
        ids.update(_split_admin_ids(os.environ.get(key, "")))
    return ids


def is_admin_user(user_id: str = "") -> bool:
    uid = str(user_id or "").strip()
    if not uid:
        return False
    return uid in configured_admin_ids()


def admin_guard_response(user_id: str = "") -> dict | None:
    if is_admin_user(user_id):
        return None
    return {"success": False, "message": "Truy cập bị từ chối"}
