"""Focused contracts for the static Gallery-to-Web-Memory save handoff."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib
import inspect
import sqlite3
import sys
from pathlib import Path

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_api", "copyfast_pages", "copyfast_projects", "copyfast_assets",
    "copyfast_project_packages", "copyfast_document_operations", "copyfast_image_runtime",
    "copyfast_image_operations", "copyfast_free_prompt_gallery", "copyfast_memory",
]
WEB_ROOT = Path(__file__).resolve().parents[1]


def make_client(tmp_path, monkeypatch, *, memory_enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "free-prompt-gallery-memory-save.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-free-prompt-gallery-memory-save-secret")
    monkeypatch.setenv("WEBAPP_MEMORY_CENTER_ENABLED", "true" if memory_enabled else "false")
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def register_and_login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "correct-horse-battery-staple",
            "display_name": "Gallery Memory Owner",
        },
    )
    assert registered.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    return str(login.json()["data"]["csrf_token"])


def save_item(client: TestClient, csrf: str, prompt_id: str, key: str):
    return client.post(
        f"/api/v1/memory/gallery-items/{prompt_id}/save",
        headers={"X-CSRF-Token": csrf},
        json={"idempotency_key": key},
    )


def test_static_gallery_save_creates_one_private_memory_note_with_safe_receipt(tmp_path, monkeypatch):
    prompt_id = "caption_cta_food_cafe_1"
    key = "gallery-memory-save-0001"
    gallery = importlib.import_module("copyfast_free_prompt_gallery")
    item = gallery.free_prompt_item(prompt_id)
    assert item is not None
    raw_prompt = str(item["prompt"])

    with make_client(tmp_path, monkeypatch) as client:
        endpoint = f"/api/v1/memory/gallery-items/{prompt_id}/save"
        assert client.post(endpoint, json={"idempotency_key": key}).status_code == 401
        csrf = register_and_login(client, "gallery-memory-owner@example.com")
        assert client.post(endpoint, json={"idempotency_key": key}).status_code == 403
        assert client.post(
            endpoint,
            headers={"X-CSRF-Token": csrf},
            json={"idempotency_key": "gallery-memory-extra-0001", "prompt": "browser must not control this"},
        ).status_code == 422
        assert client.post(
            "/api/v1/memory/gallery-items/not-valid-id!/save",
            headers={"X-CSRF-Token": csrf},
            json={"idempotency_key": "gallery-memory-invalid-0001"},
        ).status_code == 422
        missing = client.post(
            "/api/v1/memory/gallery-items/caption_cta_notreal_1/save",
            headers={"X-CSRF-Token": csrf},
            json={"idempotency_key": "gallery-memory-missing-0001"},
        )
        assert missing.status_code == 404
        assert missing.json()["error_code"] == "WEB_FREE_PROMPT_NOT_FOUND"
        assert missing.headers["cache-control"] == "no-store, private"

        created = save_item(client, csrf, prompt_id, key)
        assert created.status_code == 200
        assert created.headers["cache-control"] == "no-store, private"
        assert raw_prompt not in created.text
        data = created.json()["data"]
        note = data["note"]
        assert set(note) == {"id", "category", "priority", "state", "revision"}
        assert note["category"] == "Free Prompt Gallery"
        assert note["priority"] == "normal"
        assert note["state"] == "active"
        assert note["revision"] == 1
        assert data["gallery"] == {"prompt_id": prompt_id, "snapshot_version": "2026-07-15.1"}
        assert data["boundaries"] == {
            "execution": "web_native_memory_gallery_save",
            "source_snapshot_read_only": True,
            "memory_note_persisted": True,
            "gallery_state_persisted": False,
            "pending_bot_save_created": False,
            "telegram_state_changed": False,
            "provider_called": False,
            "bot_called": False,
            "bridge_called": False,
            "job_created": False,
            "wallet_mutated": False,
            "payment_started": False,
            "asset_saved": False,
            "publish_action_created": False,
            "delivery_created": False,
        }

        # Only the normal owner-scoped detail surface exposes the persisted
        # source seed. The mutation receipt never echoes it.
        detail = client.get(f"/api/v1/memory/notes/{note['id']}")
        assert detail.status_code == 200
        assert detail.json()["data"]["note"]["title"] == "Free Prompt Gallery — Caption bán hàng - Đồ ăn / quán cafe"
        assert raw_prompt in detail.json()["data"]["note"]["content"]
        assert "Snapshot: 2026-07-15.1" in detail.json()["data"]["note"]["content"]

        replay = save_item(client, csrf, prompt_id, key)
        assert replay.status_code == 200
        assert raw_prompt not in replay.text
        assert replay.json()["data"]["note"]["id"] == note["id"]
        collision = save_item(client, csrf, "hook_script_food_cafe_1", key)
        assert collision.status_code == 409

    db_path = tmp_path / "free-prompt-gallery-memory-save.db"
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM web_memory_notes").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM web_memory_note_versions").fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM web_memory_events WHERE note_id=? AND action='note_created'",
            (note["id"],),
        ).fetchone()[0] == 1
        audit_rows = conn.execute(
            "SELECT target, detail FROM web_audit_events WHERE action='web.memory.gallery_item.save'"
        ).fetchall()
        assert audit_rows == [(note["id"], "web-owned static Gallery item saved to Memory Center")]
        assert all(raw_prompt not in str(detail) for _, detail in audit_rows)
        idempotency_rows = conn.execute(
            "SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-memory:%:gallery-item:save'"
        ).fetchall()
        assert len(idempotency_rows) == 1
        assert raw_prompt not in str(idempotency_rows[0][0])

    # A different signed account cannot read the first account's note and
    # receives its own Web-owned copy only after its own explicit save.
    with make_client(tmp_path, monkeypatch) as other:
        other_csrf = register_and_login(other, "gallery-memory-other@example.com")
        hidden = other.get(f"/api/v1/memory/notes/{note['id']}")
        assert hidden.status_code == 200
        assert hidden.json()["error_code"] == "WEB_MEMORY_NOTE_NOT_FOUND"
        assert raw_prompt not in hidden.text
        other_saved = save_item(other, other_csrf, prompt_id, "gallery-memory-other-0001")
        assert other_saved.status_code == 200
        assert other_saved.json()["data"]["note"]["id"] != note["id"]


def test_gallery_memory_save_fails_closed_with_memory_flag_and_has_no_runtime_bridge_or_provider(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch, memory_enabled=False) as client:
        csrf = register_and_login(client, "gallery-memory-disabled@example.com")
        response = save_item(client, csrf, "caption_cta_food_cafe_1", "gallery-memory-disabled-0001")
        assert response.status_code == 503
        assert response.json()["ok"] is False

    memory = importlib.import_module("copyfast_memory")
    handler_source = inspect.getsource(memory.save_gallery_item_to_memory).lower()
    for forbidden in ("copyfast_bridge", "requests.", "httpx.", "provider_request(", "payos"):
        assert forbidden not in handler_source
    module_source = (WEB_ROOT / "copyfast_memory.py").read_text(encoding="utf-8").lower()
    for forbidden_import in ("import copyfast_bridge", "from copyfast_bridge", "import requests", "import httpx"):
        assert forbidden_import not in module_source


def test_gallery_memory_save_quota_guard_never_claims_a_note_was_persisted(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        memory = importlib.import_module("copyfast_memory")
        monkeypatch.setattr(memory, "MAX_NOTES_PER_ACCOUNT", 0)
        csrf = register_and_login(client, "gallery-memory-quota@example.com")
        response = save_item(client, csrf, "caption_cta_food_cafe_1", "gallery-memory-quota-0001")
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is False
        assert body["status"] == "guarded"
        assert body["error_code"] == "WEB_MEMORY_NOTE_LIMIT"
        assert "note" not in body["data"]
        assert body["data"]["boundaries"]["memory_note_persisted"] is False
        assert body["data"]["boundaries"]["bot_called"] is False
        assert body["data"]["boundaries"]["provider_called"] is False
        assert response.headers["cache-control"] == "no-store, private"

    with sqlite3.connect(tmp_path / "free-prompt-gallery-memory-save.db") as conn:
        assert conn.execute("SELECT COUNT(*) FROM web_memory_notes").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM web_memory_note_versions").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM web_memory_events").fetchone()[0] == 0
        assert conn.execute(
            "SELECT COUNT(*) FROM web_audit_events WHERE action='web.memory.gallery_item.save'"
        ).fetchone()[0] == 0


def test_gallery_memory_idempotency_expires_after_ttl_then_executes_a_fresh_save(tmp_path, monkeypatch):
    """An expired Gallery receipt must not pin a customer to stale output."""

    db_path = tmp_path / "free-prompt-gallery-memory-save.db"
    key = "gallery-memory-expired-0001"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "gallery-memory-expired@example.com")
        initial = save_item(client, csrf, "caption_cta_food_cafe_1", key)
        assert initial.status_code == 200
        initial_note_id = initial.json()["data"]["note"]["id"]

        with sqlite3.connect(db_path) as conn:
            scope = conn.execute(
                "SELECT scope FROM web_idempotency WHERE key=?", (key,)
            ).fetchone()[0]
            expired_at = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat(timespec="seconds")
            conn.execute(
                "UPDATE web_idempotency SET created_at=? WHERE scope=? AND key=?",
                (expired_at, scope, key),
            )
            conn.commit()

        fresh = save_item(client, csrf, "hook_script_food_cafe_1", key)
        assert fresh.status_code == 200
        fresh_note_id = fresh.json()["data"]["note"]["id"]
        assert fresh_note_id != initial_note_id

        # Once freshly executed, the same active key retains the usual
        # collision protection rather than accepting a different Gallery item.
        active_collision = save_item(client, csrf, "document_checklist_food_cafe_1", key)
        assert active_collision.status_code == 409

    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM web_memory_notes").fetchone()[0] == 2
        receipts = conn.execute(
            "SELECT key, created_at FROM web_idempotency WHERE scope=?", (scope,)
        ).fetchall()
        assert len(receipts) == 1
        assert receipts[0][0] == key
        assert datetime.fromisoformat(receipts[0][1]) > datetime.now(timezone.utc) - timedelta(hours=24)


def test_gallery_memory_idempotency_cap_prunes_only_current_account_gallery_scope(tmp_path, monkeypatch):
    """Gallery retry cleanup cannot delete another Web feature or account."""

    db_path = tmp_path / "free-prompt-gallery-memory-save.db"
    key_old = "gallery-memory-cap-old-0001"
    key_kept = "gallery-memory-cap-kept-0001"
    key_new = "gallery-memory-cap-new-0001"
    with make_client(tmp_path, monkeypatch) as client:
        memory = importlib.import_module("copyfast_memory")
        monkeypatch.setattr(memory, "MAX_GALLERY_MEMORY_IDEMPOTENCY_RECORDS_PER_ACCOUNT", 2)
        csrf = register_and_login(client, "gallery-memory-cap@example.com")
        old = save_item(client, csrf, "caption_cta_food_cafe_1", key_old)
        kept = save_item(client, csrf, "hook_script_food_cafe_1", key_kept)
        assert old.status_code == 200 and kept.status_code == 200
        kept_note_id = kept.json()["data"]["note"]["id"]

        with sqlite3.connect(db_path) as conn:
            gallery_scope = conn.execute(
                "SELECT scope FROM web_idempotency WHERE key=?", (key_old,)
            ).fetchone()[0]
            account_id = gallery_scope.removeprefix("web-memory:").removesuffix(":gallery-item:save")
            now = datetime.now(timezone.utc)
            conn.execute(
                "UPDATE web_idempotency SET created_at=? WHERE scope=? AND key=?",
                ((now - timedelta(hours=3)).isoformat(timespec="seconds"), gallery_scope, key_old),
            )
            conn.execute(
                "UPDATE web_idempotency SET created_at=? WHERE scope=? AND key=?",
                ((now - timedelta(hours=2)).isoformat(timespec="seconds"), gallery_scope, key_kept),
            )
            # These rows are deliberately old enough to be tempting cleanup
            # targets, but are outside this account's Gallery scope.
            same_account_other_flow = f"web-memory:{account_id}:note:create"
            other_account_gallery = "web-memory:another-account:gallery-item:save"
            preserved_at = (now - timedelta(hours=6)).isoformat(timespec="seconds")
            conn.execute(
                """INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (same_account_other_flow, "memory-note-flow-keep-0001", "{}", "fixture", preserved_at),
            )
            conn.execute(
                """INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (other_account_gallery, "other-account-gallery-0001", "{}", "fixture", preserved_at),
            )
            conn.commit()

        added = save_item(client, csrf, "document_checklist_food_cafe_1", key_new)
        assert added.status_code == 200
        replay = save_item(client, csrf, "hook_script_food_cafe_1", key_kept)
        assert replay.status_code == 200
        assert replay.json()["data"]["note"]["id"] == kept_note_id

    with sqlite3.connect(db_path) as conn:
        gallery_keys = {
            row[0]
            for row in conn.execute(
                "SELECT key FROM web_idempotency WHERE scope=?", (gallery_scope,)
            ).fetchall()
        }
        assert gallery_keys == {key_kept, key_new}
        assert conn.execute(
            "SELECT COUNT(*) FROM web_idempotency WHERE scope=? AND key=?",
            (same_account_other_flow, "memory-note-flow-keep-0001"),
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM web_idempotency WHERE scope=? AND key=?",
            (other_account_gallery, "other-account-gallery-0001"),
        ).fetchone()[0] == 1
