from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Request

from config import settings
from db import db_connect
from security import admin_guard_response

router = APIRouter()


def _bool_env(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _path_state(path_value: str) -> dict:
    path = Path(path_value)
    parent = path.parent if path.parent != Path("") else Path(".")
    exists = path.exists()
    parent_exists = parent.exists()
    writable = False
    try:
        parent.mkdir(parents=True, exist_ok=True)
        probe = parent / ".toanaas_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        writable = True
    except Exception:
        writable = False
    return {
        "path": str(path),
        "exists": exists,
        "parent_exists": parent_exists,
        "parent_writable": writable,
        "persistent_candidate": str(path).replace("\\", "/").startswith("/data/"),
    }


def _table_count(table_name: str) -> int | None:
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cur.fetchone():
            return None
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        return int(cur.fetchone()[0] or 0)
    finally:
        conn.close()


@router.get("/status")
async def control_status(request: Request, admin_id: str = ""):
    requested_admin = request.headers.get("x-toan-aas-user-id") or admin_id
    denied = admin_guard_response(requested_admin)
    if denied:
        return denied

    db_state = _path_state(settings.DB_FILE)
    payos_configured = all(
        [
            bool(settings.PAYOS_CLIENT_ID),
            bool(settings.PAYOS_API_KEY),
            bool(settings.PAYOS_CHECKSUM_KEY),
        ]
    )
    admin_configured = bool(
        os.environ.get("ADMIN_IDS")
        or os.environ.get("ADMIN_ID")
        or os.environ.get("OWNER_TELEGRAM_ID")
        or os.environ.get("ADMIN_TELEGRAM_IDS")
    )

    risk = "LOW" if db_state["persistent_candidate"] and db_state["parent_writable"] else "YES"
    if settings.REQUIRE_PERSISTENT_DB and risk != "LOW":
        risk = "ERROR"

    return {
        "success": True,
        "app": "TOAN AAS Control Center",
        "domain": os.environ.get("PUBLIC_BASE_URL", "https://app.toanaas.vn"),
        "db": {
            **db_state,
            "backup_dir": settings.DB_BACKUP_DIR,
            "require_persistent": settings.REQUIRE_PERSISTENT_DB,
            "data_loss_risk": risk,
            "tables": {
                "users": _table_count("users"),
                "payos_orders": _table_count("payos_orders"),
                "credit_events": _table_count("credit_events"),
                "storage_entitlements": _table_count("storage_entitlements"),
            },
        },
        "billing": {
            "payos_configured": payos_configured,
            "single_source": "/api/v1/billing/create-payment-link",
            "webhook": "/api/v1/billing/webhook/payos",
        },
        "storage": {
            "base_free_mb": 50,
            "block_amount_vnd": 10000,
            "block_mb": 50,
            "packages": ["storage_10k", "storage_20k", "storage_50k", "storage_100k", "storage_custom"],
        },
        "guards": {
            "admin_configured": admin_configured,
            "web_tool_process_enabled": _bool_env("WEB_TOOL_PROCESS_ENABLED"),
            "provider_jobs_default": "guarded_until_smoke_pass",
        },
    }
