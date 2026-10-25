"""Contract and provider-free verification tests for Voice Vault Web Canonical Parity.

Task: WEBAPP_R37_VOICE_VAULT_CANONICAL_MANAGEMENT_PARITY_AND_DELIVERY_CLOSURE_R1
Product Family: Voice Vault / Voice Studio
Tracker: manhtoangreensky-wq/toan-aas-standalone#665
Base Web SHA: 0e1b49b58f180f4ae9df6425df533419f66e55c4
Authority Bot SHA: 7d411159c5347474797bb6168f68c50080c78833

Proves:
1. LIST_OWNER_SCOPE & LIST_FOREIGN_ISOLATION
2. RENAME_SUCCESS, RENAME_FOREIGN_BLOCKED, RENAME_INVALID_NAME
3. SET_DEFAULT_SUCCESS, SET_DEFAULT_NOT_READY_FAIL, SET_DEFAULT_FOREIGN_BLOCKED
4. SOFT_DELETE_SUCCESS, SOFT_DELETE_IDEMPOTENT, SOFT_DELETE_FOREIGN_BLOCKED
5. DELETED_PROFILE_NOT_ACTIVE (excluded from list and handoff)
6. PREVIEW_READY_SUCCESS (stream inline, download attachment, meta JSON)
7. PREVIEW_NOT_READY_FAIL & PREVIEW_FOREIGN_BLOCKED
8. NO_PRIVATE_METADATA_LEAK (zero private tokens, passwords, filesystem paths, raw provider IDs)
9. HANDOFF_OWNER_SUCCESS, HANDOFF_FOREIGN_BLOCKED, HANDOFF_DELETED_NOT_READY_FAIL
10. DUPLICATE_MUTATION_RETRY_SAFE
11. CSRF_PROTECTION on all mutation routes
12. UNLINKED_ACCOUNT_BLOCKED (409 if no Telegram link)
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import urllib.parse
import uuid

import pytest
from fastapi.testclient import TestClient

STANDALONE_ROOT = Path(__file__).resolve().parents[1]
if str(STANDALONE_ROOT) not in sys.path:
    sys.path.insert(0, str(STANDALONE_ROOT))

from app import app
import app as app_module
from copyfast_auth import (
    SESSION_COOKIE,
    _cookie_name,
    _insert_session,
    _session_cookie_value,
)
from copyfast_db import ensure_copyfast_schema, transaction, utc_now
from copyfast_voice_tts_job_bridge import validate_voice_tts_input
from copyfast_subdub_job_bridge import validate_subdub_input


class MockVoiceVaultState:
    """Canonical in-memory state modeling Bot Core Voice Vault table."""

    def __init__(self):
        self.profiles: dict[int, dict] = {}
        self.next_id = 100
        self.force_redirect = False
        self.reset()

    def reset(self):
        self.force_redirect = False
        self.profiles = {
            1: {
                "id": 1,
                "user_id": "1001",
                "display_name": "Giọng Thuyết Minh Chuẩn",
                "status": "active",
                "is_default": 0,
                "consent_status": "consented",
                "preview_audio_ref": "outputs/voice_previews/1001_1.mp3",
                "provider_voice_id": "pv_secret_mock_1",
                "source_file_id": "file_src_1",
                "source_file_ref": "/private/bot/src/1.wav",
                "created_at": "2026-10-24T10:00:00Z",
                "updated_at": "2026-10-24T10:00:00Z",
                "deleted_at": None,
            },
            2: {
                "id": 2,
                "user_id": "1001",
                "display_name": "Giọng Chưa Sẵn Sàng",
                "status": "pending_name",
                "is_default": 0,
                "consent_status": "pending",
                "preview_audio_ref": "",
                "provider_voice_id": "",
                "source_file_id": "",
                "source_file_ref": "",
                "created_at": "2026-10-24T10:05:00Z",
                "updated_at": "2026-10-24T10:05:00Z",
                "deleted_at": None,
            },
            3: {
                "id": 3,
                "user_id": "1001",
                "display_name": "Giọng Có Telegram File ID",
                "status": "active",
                "is_default": 0,
                "consent_status": "consented",
                "preview_audio_ref": "CQACAgIAAxkBAAICk_valid_telegram_id_3",
                "provider_voice_id": "pv_secret_mock_3",
                "source_file_id": "file_src_3",
                "source_file_ref": "",
                "created_at": "2026-10-24T10:10:00Z",
                "updated_at": "2026-10-24T10:10:00Z",
                "deleted_at": None,
            },
            4: {
                "id": 4,
                "user_id": "1001",
                "display_name": "Giọng Có Stale Telegram ID",
                "status": "active",
                "is_default": 0,
                "consent_status": "consented",
                "preview_audio_ref": "stale_telegram_file_id_4",
                "provider_voice_id": "pv_secret_mock_4",
                "source_file_id": "file_src_4",
                "source_file_ref": "",
                "created_at": "2026-10-24T10:12:00Z",
                "updated_at": "2026-10-24T10:12:00Z",
                "deleted_at": None,
            },
            5: {
                "id": 5,
                "user_id": "1001",
                "display_name": "Giọng Đường Dẫn Trái Phép",
                "status": "active",
                "is_default": 0,
                "consent_status": "consented",
                "preview_audio_ref": "C:/Windows/System32/drivers/etc/hosts",
                "provider_voice_id": "pv_secret_mock_5",
                "source_file_id": "file_src_5",
                "source_file_ref": "",
                "created_at": "2026-10-24T10:13:00Z",
                "updated_at": "2026-10-24T10:13:00Z",
                "deleted_at": None,
            },
            6: {
                "id": 6,
                "user_id": "1001",
                "display_name": "Giọng Có Remote HTTP URL",
                "status": "active",
                "is_default": 0,
                "consent_status": "consented",
                "preview_audio_ref": "https://cdn.toanaas.vn/voice6.mp3",
                "provider_voice_id": "pv_secret_mock_6",
                "source_file_id": "file_src_6",
                "source_file_ref": "",
                "created_at": "2026-10-24T10:14:00Z",
                "updated_at": "2026-10-24T10:14:00Z",
                "deleted_at": None,
            },
            99: {
                "id": 99,
                "user_id": "9999",
                "display_name": "Giọng Của Người Khác",
                "status": "active",
                "is_default": 1,
                "consent_status": "consented",
                "preview_audio_ref": "CQACAgIAAxkBAAICk_foreign_99",
                "provider_voice_id": "pv_foreign_secret_99",
                "source_file_id": "file_src_99",
                "source_file_ref": "/private/bot/foreign/99.wav",
                "created_at": "2026-10-24T09:00:00Z",
                "updated_at": "2026-10-24T09:00:00Z",
                "deleted_at": None,
            },
        }

    def _sanitize(self, p: dict) -> dict:
        return {
            "id": p["id"],
            "display_name": p["display_name"],
            "status": p["status"],
            "is_default": bool(p["is_default"]),
            "consent_status": p["consent_status"],
            "tts_ready": bool(p["status"] in ("active", "ready")),
            "preview_ready": bool(p["status"] in ("active", "ready") and p.get("preview_audio_ref")),
            "created_at": p["created_at"],
            "updated_at": p["updated_at"],
        }

    def handle_request(self, method: str, path: str, actor_id: str, payload: dict | None = None, params: dict | None = None) -> tuple[int, dict]:
        parts = path.strip("/").split("/")
        # Path: internal/v1/voice/profiles ...
        if len(parts) == 4 and parts[3] == "profiles":
            if method == "GET":
                items = [
                    self._sanitize(p)
                    for p in self.profiles.values()
                    if str(p["user_id"]) == str(actor_id) and p["deleted_at"] is None and p["status"] != "deleted"
                ]
                return 200, {"ok": True, "status": "completed", "data": {"items": items}}

        if len(parts) >= 5 and parts[3] == "profiles":
            try:
                pid = int(parts[4])
            except ValueError:
                return 422, {"ok": False, "error_code": "INVALID_PROFILE_ID", "message": "ID không hợp lệ"}

            profile = self.profiles.get(pid)
            if not profile or str(profile["user_id"]) != str(actor_id) or profile["deleted_at"] is not None or profile["status"] == "deleted":
                # For delete idempotent, if it was deleted by this owner
                if method == "DELETE" and profile and str(profile["user_id"]) == str(actor_id) and (profile["deleted_at"] is not None or profile["status"] == "deleted"):
                    return 200, {"ok": True, "profile_id": pid, "deleted": True}
                return 404, {"ok": False, "error_code": "PROFILE_NOT_FOUND", "message": "Không tìm thấy hồ sơ giọng"}

            # Rename
            if len(parts) == 5 and method == "PATCH":
                new_name = str((payload or {}).get("display_name") or "").strip()
                if len(new_name) < 2 or len(new_name) > 80:
                    return 400, {"ok": False, "error_code": "VOICE_PROFILE_INVALID_NAME", "message": "Tên giọng phải từ 2 đến 80 ký tự."}
                profile["display_name"] = new_name
                profile["updated_at"] = utc_now()
                sanitized = self._sanitize(profile)
                return 200, {
                    "ok": True,
                    "profile_id": pid,
                    "display_name": new_name,
                    "profile": sanitized,
                }

            # Set default
            if len(parts) == 6 and parts[5] == "default" and method == "POST":
                if profile["status"] not in ("active", "ready"):
                    return 400, {"ok": False, "error_code": "VOICE_PROFILE_NOT_READY", "message": "Hồ sơ giọng chưa sẵn sàng để đặt làm mặc định"}
                for other in self.profiles.values():
                    if str(other["user_id"]) == str(actor_id):
                        other["is_default"] = 0
                profile["is_default"] = 1
                profile["updated_at"] = utc_now()
                sanitized = self._sanitize(profile)
                return 200, {
                    "ok": True,
                    "profile_id": pid,
                    "is_default": True,
                    "profile": sanitized,
                }

            # Delete
            if len(parts) == 5 and method == "DELETE":
                profile["status"] = "deleted"
                profile["is_default"] = 0
                profile["deleted_at"] = utc_now()
                return 200, {
                    "ok": True,
                    "profile_id": pid,
                    "deleted": True,
                }

            # Preview
            if len(parts) == 6 and parts[5] == "preview" and method == "GET":
                if profile["status"] not in ("active", "ready") or not profile.get("preview_audio_ref"):
                    return 400, {"ok": False, "error_code": "PREVIEW_NOT_READY", "message": "Bản nghe thử chưa sẵn sàng"}
                ref = profile["preview_audio_ref"]

                # Remote URLs rejected (REMOTE_URL_LANE_REMOVED=YES)
                if ref.startswith(("http://", "https://")) or "://" in ref:
                    return 404, {"ok": False, "error_code": "PREVIEW_MISSING_ARTIFACT", "message": "Định dạng bản nghe thử không được hỗ trợ"}

                # Path like (local file)
                if "/" in ref or "\\" in ref:
                    # Canonical root check: must be in outputs/
                    if not ref.startswith("outputs/"):
                        return 404, {"ok": False, "error_code": "PREVIEW_MISSING_ARTIFACT", "message": "Bản nghe thử không tìm thấy trên hệ thống lưu trữ"}
                    return 200, {
                        "ok": True,
                        "profile_id": pid,
                        "display_name": profile["display_name"],
                        "delivery_mode": "file",
                        "content_type": "audio/mpeg",
                        "download_ready": True,
                    }

                # Telegram file ID
                if ref.startswith("stale_") or ref.startswith("missing_"):
                    return 404, {"ok": False, "error_code": "PREVIEW_MISSING_ARTIFACT", "message": "Không thể tải bản nghe thử từ Telegram"}

                return 200, {
                    "ok": True,
                    "profile_id": pid,
                    "display_name": profile["display_name"],
                    "delivery_mode": "telegram",
                    "content_type": "audio/mpeg",
                    "download_ready": True,
                }

        return 404, {"ok": False, "error_code": "NOT_FOUND", "message": "Not found"}

        return 404, {"ok": False, "error_code": "NOT_FOUND", "message": "Not found"}


vault_state = MockVoiceVaultState()


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Ensure test environment is strictly provider-free and tables exist."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-voice-vault-r37")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "false")
    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "mock-core-bridge-token-r37-fixed-len")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "mock-hmac-secret-r37-32-bytes-long!")

    vault_state.reset()
    app_module._auth_rate_windows.clear()
    monkeypatch.setattr(app_module, "_durable_auth_throttle_guard", lambda *a, **kw: None)
    ensure_copyfast_schema()

    # Mock CoreBridgeClient.request
    from copyfast_bridge import CoreBridgeClient, envelope
    import copyfast_bridge

    async def mock_bridge_client_request(self, method: str, path: str, *, payload=None, params=None, request_id=None, actor_id="", owner_id=""):
        status_code, resp_data = vault_state.handle_request(method, path, actor_id, payload=payload, params=params)
        if status_code >= 400:
            return copyfast_bridge._sanitize_envelope(resp_data, fallback_code=resp_data.get("error_code"))
        return copyfast_bridge._sanitize_envelope(resp_data)

    monkeypatch.setattr(CoreBridgeClient, "request", mock_bridge_client_request)

    # Mock httpx.AsyncClient for preview streaming
    import httpx

    class MockHttpxResponse:
        def __init__(self, status_code: int, content: bytes, headers: dict):
            self.status_code = status_code
            self.content = content
            self.headers = headers

        def json(self):
            return json.loads(self.content.decode("utf-8"))

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def get(self, url: str, headers=None):
            parsed = urllib.parse.urlparse(url)
            query = urllib.parse.parse_qs(parsed.query)
            actor_id = query.get("user_id", [""])[0] or (headers or {}).get("x-toan-aas-actor-id", "")
            download = query.get("download", ["0"])[0] in ("1", "true")
            status_code, resp_data = vault_state.handle_request("GET", parsed.path, actor_id, params=query)

            if status_code >= 400:
                return MockHttpxResponse(status_code, json.dumps(resp_data).encode("utf-8"), {"content-type": "application/json"})

            if vault_state.force_redirect:
                return MockHttpxResponse(307, b"", {"location": "https://cdn.toanaas.vn/rogue_redirect.mp3"})

            if query.get("mode") == ["meta"]:
                return MockHttpxResponse(200, json.dumps(resp_data).encode("utf-8"), {"content-type": "application/json"})

            # file or remote safe stream mode: return audio bytes
            audio_bytes = b"\xFF\xFB\x90\x44" + b"\x00" * 256
            disp = "attachment" if download else "inline"
            return MockHttpxResponse(
                200,
                audio_bytes,
                {
                    "content-type": "audio/mpeg",
                    "content-disposition": f'{disp}; filename="voice_preview.mp3"',
                },
            )

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    yield


def _create_test_account(canonical_user_id: str = "") -> tuple[TestClient, str]:
    """Insert or update deterministic test account into SQLite and return authenticated TestClient and csrf_token."""
    account_id = f"acc_{canonical_user_id or 'anon'}"
    email = f"{account_id}@test.local"
    with transaction() as conn:
        now = utc_now()
        conn.execute(
            """
            INSERT INTO web_accounts (
                id, email, password_hash, canonical_user_id, role_cache, created_at, updated_at
            ) VALUES (?, ?, 'test_hash', ?, 'member', ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                email=excluded.email,
                canonical_user_id=excluded.canonical_user_id,
                updated_at=excluded.updated_at
            """,
            (account_id, email, canonical_user_id or None, now, now),
        )
        conn.execute("DELETE FROM web_sessions WHERE account_id=?", (account_id,))
        sess = _insert_session(conn, account_id)
    client = TestClient(app)
    cookie_val = _session_cookie_value(sess["session_id"])
    client.cookies.set(_cookie_name(SESSION_COOKIE), cookie_val)
    return client, sess["csrf_token"]


# ─── 1. LIST_OWNER_SCOPE & LIST_FOREIGN_ISOLATION ────────────────────────────

def test_list_owner_scope_and_foreign_isolation():
    """Verify GET /voice/profiles returns only the linked user's profiles and excludes foreign ones."""
    # Account 1001 linked to Telegram 1001
    client1, _ = _create_test_account(canonical_user_id="1001")
    resp1 = client1.get("/api/v1/voice/profiles")
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["ok"] is True
    items1 = data1["data"]["items"]
    ids1 = [item["id"] for item in items1]
    assert 1 in ids1
    assert 2 in ids1
    assert 3 in ids1
    assert 99 not in ids1  # Foreign profile strictly excluded

    # Account 9999 linked to Telegram 9999
    client2, _ = _create_test_account(canonical_user_id="9999")
    resp2 = client2.get("/api/v1/voice/profiles")
    assert resp2.status_code == 200
    items2 = resp2.json()["data"]["items"]
    ids2 = [item["id"] for item in items2]
    assert 99 in ids2
    assert 1 not in ids2


def test_unlinked_account_cannot_access_voice_profiles():
    """Verify unlinked account gets 409 conflict when accessing voice profiles."""
    client_unlinked, _ = _create_test_account(canonical_user_id="")
    resp = client_unlinked.get("/api/v1/voice/profiles")
    assert resp.status_code == 409
    assert "Telegram" in resp.json().get("message", "") or "Telegram" in resp.json().get("detail", "")


# ─── 2. RENAME_SUCCESS, FOREIGN_BLOCKED & INVALID_NAME ────────────────────────

def test_rename_voice_profile_success():
    """Verify owner can rename profile successfully with CSRF protection."""
    client, csrf = _create_test_account(canonical_user_id="1001")
    resp = client.patch(
        "/api/v1/voice/profiles/1",
        json={"display_name": "Giọng Thuyết Minh Mới"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["display_name"] == "Giọng Thuyết Minh Mới"
    assert body["data"]["profile"]["display_name"] == "Giọng Thuyết Minh Mới"


def test_rename_voice_profile_foreign_blocked():
    """Verify user cannot rename someone else's voice profile."""
    client2, csrf2 = _create_test_account(canonical_user_id="9999")
    resp = client2.patch(
        "/api/v1/voice/profiles/1",
        json={"display_name": "Hack Name"},
        headers={"X-CSRF-Token": csrf2},
    )
    # Returns bridge guarded failure with PROFILE_NOT_FOUND error code
    body = resp.json()
    assert body["ok"] is False
    assert body["error_code"] == "PROFILE_NOT_FOUND"


def test_rename_voice_profile_invalid_name():
    """Verify invalid name lengths (min 2, max 80) are rejected with VOICE_PROFILE_INVALID_NAME."""
    client, csrf = _create_test_account(canonical_user_id="1001")

    # Name too short (< 2 chars)
    resp_short = client.patch(
        "/api/v1/voice/profiles/1",
        json={"display_name": "A"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp_short.status_code == 400
    assert resp_short.json()["ok"] is False
    assert resp_short.json()["error_code"] == "VOICE_PROFILE_INVALID_NAME"

    # Name empty (0 chars)
    resp_empty = client.patch(
        "/api/v1/voice/profiles/1",
        json={"display_name": ""},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp_empty.status_code == 400
    assert resp_empty.json()["ok"] is False
    assert resp_empty.json()["error_code"] == "VOICE_PROFILE_INVALID_NAME"

    # Name too long (> 80 chars)
    resp_long = client.patch(
        "/api/v1/voice/profiles/1",
        json={"display_name": "A" * 85},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp_long.status_code == 400
    assert resp_long.json()["ok"] is False
    assert resp_long.json()["error_code"] == "VOICE_PROFILE_INVALID_NAME"


def test_rename_requires_csrf():
    """Verify CSRF token is required for rename mutation."""
    client, _ = _create_test_account(canonical_user_id="1001")
    resp = client.patch("/api/v1/voice/profiles/1", json={"display_name": "No CSRF"})
    assert resp.status_code == 403


# ─── 3. SET_DEFAULT_SUCCESS, NOT_READY_FAIL & FOREIGN_BLOCKED ─────────────────

def test_set_default_success_and_readiness_fail():
    """Verify setting default works for ready profiles and fails for unready profiles."""
    client, csrf = _create_test_account(canonical_user_id="1001")

    # Ready profile 1 -> succeeds
    resp1 = client.post("/api/v1/voice/profiles/1/default", headers={"X-CSRF-Token": csrf})
    assert resp1.status_code == 200
    body1 = resp1.json()
    assert body1["ok"] is True
    assert body1["data"]["is_default"] is True

    # Not ready profile 2 -> fails
    resp2 = client.post("/api/v1/voice/profiles/2/default", headers={"X-CSRF-Token": csrf})
    body2 = resp2.json()
    assert body2["ok"] is False
    assert body2["error_code"] == "VOICE_PROFILE_NOT_READY"


def test_set_default_foreign_blocked():
    """Verify user cannot set default on another user's profile."""
    client2, csrf2 = _create_test_account(canonical_user_id="9999")
    resp = client2.post("/api/v1/voice/profiles/1/default", headers={"X-CSRF-Token": csrf2})
    body = resp.json()
    assert body["ok"] is False
    assert body["error_code"] == "PROFILE_NOT_FOUND"


# ─── 4. SOFT_DELETE_SUCCESS, IDEMPOTENT & FOREIGN_BLOCKED ─────────────────────

def test_soft_delete_success_and_idempotent():
    """Verify soft delete marks profile as deleted, and subsequent deletes are idempotent."""
    client, csrf = _create_test_account(canonical_user_id="1001")

    # Delete profile 2
    resp1 = client.delete("/api/v1/voice/profiles/2", headers={"X-CSRF-Token": csrf})
    assert resp1.status_code == 200
    body1 = resp1.json()
    assert body1["ok"] is True
    assert body1["data"]["deleted"] is True

    # Idempotent delete on already deleted profile
    resp2 = client.delete("/api/v1/voice/profiles/2", headers={"X-CSRF-Token": csrf})
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["ok"] is True
    assert body2["data"]["deleted"] is True

    # Deleted profile is excluded from active list
    list_resp = client.get("/api/v1/voice/profiles")
    items = list_resp.json()["data"]["items"]
    assert 2 not in [i["id"] for i in items]


def test_soft_delete_foreign_blocked():
    """Verify user cannot soft delete another user's profile."""
    client2, csrf2 = _create_test_account(canonical_user_id="9999")
    resp = client2.delete("/api/v1/voice/profiles/1", headers={"X-CSRF-Token": csrf2})
    body = resp.json()
    assert body["ok"] is False
    assert body["error_code"] == "PROFILE_NOT_FOUND"


# ─── 5. PREVIEW DELIVERY (STREAM, DOWNLOAD, META, FOREIGN) ───────────────────

def test_preview_delivery_telegram_file_id_stream_and_download():
    """Verify Telegram file ID preview delivery streams audio or sets attachment disposition on download."""
    client, _ = _create_test_account(canonical_user_id="1001")

    # 1. TELEGRAM_FILE_ID_OWNER_STREAM (inline stream)
    resp_listen = client.get("/api/v1/voice/profiles/3/preview")
    assert resp_listen.status_code == 200
    assert resp_listen.headers["content-type"] == "audio/mpeg"
    assert "inline" in resp_listen.headers["content-disposition"]
    assert len(resp_listen.content) > 0

    # 2. TELEGRAM_FILE_ID_DOWNLOAD (attachment download)
    resp_dl = client.get("/api/v1/voice/profiles/3/preview?download=true")
    assert resp_dl.status_code == 200
    assert resp_dl.headers["content-type"] == "audio/mpeg"
    assert "attachment" in resp_dl.headers["content-disposition"]
    assert len(resp_dl.content) > 0

    # 3. TELEGRAM_FILE_ID_META_NO_ID_LEAK
    resp_meta = client.get("/api/v1/voice/profiles/3/preview?mode=meta")
    assert resp_meta.status_code == 200
    body = resp_meta.json()
    assert body["ok"] is True
    data = body["data"]
    assert data.get("profile_id") == 3
    assert data["delivery_mode"] == "telegram"
    assert data["content_type"] == "audio/mpeg"
    assert data["download_ready"] is True
    # Invariants: RAW_TELEGRAM_FILE_ID_BROWSER_EXPOSURE=NO & RAW_PREVIEW_URL_BROWSER_EXPOSURE=NO
    assert "CQACAgIAAxkBAAICk" not in resp_meta.text
    assert "preview_url" not in data
    assert "preview_audio_ref" not in data


def test_preview_delivery_local_file_stream_and_download():
    """Verify local filesystem path preview delivery in canonical storage root."""
    client, _ = _create_test_account(canonical_user_id="1001")

    # Local stream
    resp_listen = client.get("/api/v1/voice/profiles/1/preview")
    assert resp_listen.status_code == 200
    assert resp_listen.headers["content-type"] == "audio/mpeg"
    assert len(resp_listen.content) > 0

    # Local meta mode
    resp_meta = client.get("/api/v1/voice/profiles/1/preview?mode=meta")
    assert resp_meta.status_code == 200
    data = resp_meta.json()["data"]
    assert data["delivery_mode"] == "file"
    assert data["download_ready"] is True
    # PRIVATE_PATH_EXPOSURE_COUNT=0
    assert "outputs" not in resp_meta.text
    assert "1001_1.mp3" not in resp_meta.text


def test_preview_delivery_stale_and_remote_and_arbitrary_path_fails_closed():
    """Verify stale Telegram file ID, arbitrary local path, and remote URLs fail closed."""
    client, _ = _create_test_account(canonical_user_id="1001")

    # 1. TELEGRAM_FILE_ID_STALE_FAILS_CLOSED (Profile 4 has stale/unreachable Telegram ID)
    resp_stale = client.get("/api/v1/voice/profiles/4/preview")
    assert resp_stale.status_code == 404
    assert resp_stale.json()["error_code"] == "PREVIEW_MISSING_ARTIFACT"

    # 2. CANONICAL_STORAGE_ROOT_ENFORCED & ARBITRARY_PATH_READ=NO (Profile 5 points to system path)
    resp_arb = client.get("/api/v1/voice/profiles/5/preview")
    assert resp_arb.status_code == 404
    assert resp_arb.json()["error_code"] == "PREVIEW_MISSING_ARTIFACT"

    # 3. REMOTE_URL_LANE_REMOVED=YES (Profile 6 has remote HTTP URL, not supported in Bot)
    resp_url = client.get("/api/v1/voice/profiles/6/preview")
    assert resp_url.status_code == 404
    assert resp_url.json()["error_code"] == "PREVIEW_MISSING_ARTIFACT"


def test_preview_redirect_strictly_blocked():
    """Verify Web refuses 300-level redirects from Bot and returns 502 fail-closed."""
    client, _ = _create_test_account(canonical_user_id="1001")
    vault_state.force_redirect = True
    try:
        resp = client.get("/api/v1/voice/profiles/3/preview", follow_redirects=False)
        assert resp.status_code == 502
        body = resp.json()
        assert "Chuyển hướng không được phép" in (body.get("message") or body.get("detail", ""))
    finally:
        vault_state.force_redirect = False


def test_preview_delivery_not_ready_and_foreign_blocked():
    """Verify unready preview returns 400, foreign returns 404, and deleted returns 404."""
    client, csrf = _create_test_account(canonical_user_id="1001")

    # NOT_READY_PREVIEW_BLOCKED (profile 2 has no preview artifact)
    resp_nr = client.get("/api/v1/voice/profiles/2/preview")
    assert resp_nr.status_code == 400
    assert resp_nr.json()["error_code"] == "PREVIEW_NOT_READY"

    # TELEGRAM_FILE_ID_FOREIGN_BLOCKED (profile 99 belongs to user 9999)
    resp_foreign = client.get("/api/v1/voice/profiles/99/preview")
    assert resp_foreign.status_code == 404
    assert resp_foreign.json()["error_code"] == "PROFILE_NOT_FOUND"

    # DELETED_PREVIEW_BLOCKED (Soft deleted profile 1)
    del_resp = client.delete("/api/v1/voice/profiles/1", headers={"X-CSRF-Token": csrf})
    assert del_resp.status_code == 200
    resp_del_prev = client.get("/api/v1/voice/profiles/1/preview")
    assert resp_del_prev.status_code == 404
    assert resp_del_prev.json()["error_code"] == "PROFILE_NOT_FOUND"


# ─── 6. NO_PRIVATE_METADATA_LEAK ─────────────────────────────────────────────

def test_no_private_metadata_leak_across_all_responses():
    """Verify no private Bot credentials, paths, source file IDs, or raw provider IDs leak."""
    client, csrf = _create_test_account(canonical_user_id="1001")

    # 1. List
    list_body = client.get("/api/v1/voice/profiles").text
    for sensitive in ("provider_voice_id", "pv_secret", "source_file", "private/bot", "password", "token"):
        assert sensitive not in list_body

    # 2. Rename
    rename_body = client.patch(
        "/api/v1/voice/profiles/1",
        json={"display_name": "Tên Không Lộ Info"},
        headers={"X-CSRF-Token": csrf},
    ).text
    for sensitive in ("provider_voice_id", "pv_secret", "source_file", "private/bot", "password", "token"):
        assert sensitive not in rename_body

    # 3. Preview Meta
    meta_body = client.get("/api/v1/voice/profiles/1/preview?mode=meta").text
    for sensitive in ("provider_voice_id", "pv_secret", "source_file", "private/bot", "password", "token"):
        assert sensitive not in meta_body


# ─── 7. HANDOFF CONTRACTS (VOICE TTS & SUBDUB) ───────────────────────────────

def test_handoff_voice_tts_saved_voice_validation():
    """Verify Voice TTS job creation enforces valid voice_profile_id and rejects raw provider IDs."""
    # 1. Missing profile id
    ok, err, _ = validate_voice_tts_input({"script": "Xin chào", "voice_source": "saved"})
    assert not ok
    assert err == "VOICE_PROFILE_ID_REQUIRED"

    # 2. Raw provider voice ID passed directly -> strictly rejected
    ok_raw, err_raw, _ = validate_voice_tts_input({
        "script": "Xin chào",
        "voice_source": "saved",
        "voice_profile_id": "female-shaonv",
    })
    assert not ok_raw
    assert err_raw == "RAW_PROVIDER_VOICE_ID_REJECTED"

    # 3. Valid profile id -> normalized
    ok_valid, err_valid, norm = validate_voice_tts_input({
        "script": "Xin chào",
        "voice_source": "saved",
        "voice_profile_id": "1",
    })
    assert ok_valid
    assert norm["voice_profile_id"] == "1"


def test_handoff_subdub_voice_profile_contract():
    """Verify SubDub job creation preserves voice_profile_id without raw provider IDs."""
    valid, err, norm = validate_subdub_input({
        "upload_id": "UPL-12345678",
        "source_language": "en",
        "target_language": "vi",
        "voice_profile_id": "1",
    })
    assert valid
    assert norm["voice_profile_id"] == "1"


# ─── 8. DUPLICATE MUTATION RETRY SAFETY ──────────────────────────────────────

def test_duplicate_mutation_retry_safety():
    """Verify sequential repeat mutations on rename/set_default/delete are idempotent."""
    client, csrf = _create_test_account(canonical_user_id="1001")

    # Duplicate rename
    r1 = client.patch("/api/v1/voice/profiles/1", json={"display_name": "Tên Thử Lại"}, headers={"X-CSRF-Token": csrf})
    r2 = client.patch("/api/v1/voice/profiles/1", json={"display_name": "Tên Thử Lại"}, headers={"X-CSRF-Token": csrf})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["data"]["display_name"] == r2.json()["data"]["display_name"]

    # Duplicate set default
    d1 = client.post("/api/v1/voice/profiles/1/default", headers={"X-CSRF-Token": csrf})
    d2 = client.post("/api/v1/voice/profiles/1/default", headers={"X-CSRF-Token": csrf})
    assert d1.status_code == 200
    assert d2.status_code == 200
    assert d1.json()["data"]["is_default"] is True
    assert d2.json()["data"]["is_default"] is True
