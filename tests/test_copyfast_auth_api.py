import importlib
import base64
import asyncio
import hashlib
import hmac
from io import BytesIO
import json
from pathlib import Path
import sqlite3
import sys
import time
import types
import uuid
from zipfile import ZipFile
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient


MODULES = [
    "app", "config", "db", "copyfast_db", "copyfast_auth", "copyfast_bridge",
    "copyfast_registry", "copyfast_api", "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations", "copyfast_pages",
]


def make_client(tmp_path, monkeypatch, *, base_url="http://testserver", session_database_path=None):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(session_database_path or (tmp_path / "copyfast-test.db")))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("CORE_BRIDGE_CALLBACK_TOKEN", "bridge-test-token")
    monkeypatch.setenv("CORE_BRIDGE_CALLBACK_HMAC_SECRET", "bridge-test-hmac")
    # The Telegram Bot bridge has an independent callback credential.  Keep
    # the old core callback variables present to prove the Web layer does not
    # silently fall back to them.
    monkeypatch.setenv("WEBAPP_LINK_CALLBACK_TOKEN", "bridge-test-token")
    monkeypatch.setenv("WEBAPP_LINK_CALLBACK_HMAC_SECRET", "bridge-test-hmac")
    # Tests exercising a callback use the separately reviewed Bot adapter.
    # Production defaults to false until that adapter is deliberately deployed.
    monkeypatch.setenv("WEBAPP_TELEGRAM_BOT_LINK_ENABLED", "true")
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    application = importlib.import_module("app").app
    return TestClient(application, base_url=base_url)


def link_callback_headers(body, *, request_id=None, timestamp=None, path="/api/v1/auth/internal/telegram-link/confirm"):
    request_id = request_id or f"link-callback-{uuid.uuid4()}"
    timestamp = str(timestamp or int(time.time()))
    digest = hashlib.sha256(body).hexdigest()
    material = f"{timestamp}.{request_id}.POST.{path}.{digest}".encode("utf-8")
    signature = hmac.new(b"bridge-test-hmac", material, hashlib.sha256).hexdigest()
    return {
        "X-TOAN-AAS-BRIDGE-TOKEN": "bridge-test-token",
        "X-TOAN-AAS-Timestamp": timestamp,
        "X-TOAN-AAS-Request-ID": request_id,
        "X-TOAN-AAS-Signature": signature,
        "Content-Type": "application/json",
    }


def confirm_link(client, code, *, role="user", canonical_user_id="telegram-123", request_id=None, timestamp=None, callback_path="/api/v1/auth/internal/telegram-link/confirm", extra_headers=None):
    body = json.dumps(
        {"code": code, "canonical_user_id": canonical_user_id, "role": role},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    headers = link_callback_headers(body, request_id=request_id, timestamp=timestamp, path=callback_path)
    headers.update(extra_headers or {})
    return client.post(
        callback_path,
        headers=headers,
        content=body,
    )


def complete_link(client, csrf=None):
    if not csrf:
        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        csrf = me.json()["data"]["csrf_token"]
    return client.post("/api/v1/auth/telegram/link/complete", headers={"X-CSRF-Token": csrf})


def register_and_link(client, *, role="user"):
    response = client.post("/api/v1/auth/register", json={"email": "user@example.com", "password": "correct-horse-battery-staple", "display_name": "User"})
    assert response.status_code == 200
    assert response.json()["ok"] is True
    # Register never creates a session; login is the one indistinguishable
    # password flow that issues the signed cookie and CSRF credential.
    login = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "correct-horse-battery-staple"})
    assert login.status_code == 200
    csrf = login.json()["data"]["csrf_token"]
    link = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf})
    assert link.status_code == 200
    code = link.json()["data"]["code"]
    confirmed = confirm_link(client, code, role=role)
    assert confirmed.json()["ok"] is True
    completed = complete_link(client, csrf)
    assert completed.status_code == 200
    assert completed.json()["ok"] is True
    return csrf


def enable_oauth_provider(monkeypatch, provider):
    monkeypatch.setenv(f"WEBAPP_{provider.upper()}_OAUTH_ENABLED", "true")
    monkeypatch.setenv(f"{provider.upper()}_OAUTH_CLIENT_ID", f"{provider}-client-id")
    monkeypatch.setenv(f"{provider.upper()}_OAUTH_CLIENT_SECRET", f"{provider}-client-secret")
    monkeypatch.setenv("WEBAPP_PUBLIC_BASE_URL", "http://localhost")
    monkeypatch.setenv("WEB_OAUTH_IDENTITY_HMAC_SECRET", "oauth-test-hmac-secret")


def enable_apple_oauth(monkeypatch):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    private_key = ec.generate_private_key(ec.SECP256R1())
    pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    monkeypatch.setenv("WEBAPP_APPLE_OAUTH_ENABLED", "true")
    monkeypatch.setenv("APPLE_OAUTH_CLIENT_ID", "com.toanaas.web")
    monkeypatch.setenv("APPLE_OAUTH_TEAM_ID", "APPLETEAM1")
    monkeypatch.setenv("APPLE_OAUTH_KEY_ID", "APPLEKEY01")
    monkeypatch.setenv("APPLE_OAUTH_PRIVATE_KEY_BASE64", base64.b64encode(pem).decode("ascii"))
    monkeypatch.setenv("WEBAPP_PUBLIC_BASE_URL", "https://app.toanaas.vn")
    monkeypatch.setenv("WEB_OAUTH_IDENTITY_HMAC_SECRET", "oauth-test-hmac-secret")
    monkeypatch.setenv("WEB_COOKIE_SECURE", "true")


def oauth_state_from_redirect(response):
    assert response.status_code == 303
    query = parse_qs(urlparse(response.headers["location"]).query)
    state = query.get("state", [""])[0]
    assert state
    return state, query


def test_signed_session_csrf_and_telegram_link(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_link(client)
        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        browser_account = me.json()["data"]["account"]
        assert browser_account["telegram_linked"] is True
        assert "canonical_user_id" not in browser_account
        assert "telegram-123" not in me.text
        link_status = client.get("/api/v1/auth/telegram/link/status")
        assert link_status.json()["data"] == {"linked": True}
        assert "telegram-123" not in link_status.text
        core_me = client.get("/api/v1/core/me")
        assert core_me.status_code == 200
        assert core_me.json()["error_code"] == "BROWSER_IDENTITY_NOT_EXPOSED"
        assert "telegram-123" not in core_me.text
        invalid = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": "wrong"})
        assert invalid.status_code == 403
        guarded = client.get("/api/v1/wallet")
        assert guarded.status_code == 200
        assert guarded.json()["status"] == "guarded"
        confirmed = client.post(
            "/api/v1/features/video_single/confirm",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "feature-confirm-0001"},
            json={"input": {"prompt": "test"}, "idempotency_key": "feature-confirm-0001"},
        )
        assert confirmed.status_code == 200
        assert confirmed.json()["error_code"] == "WEBAPP_PROVIDER_CALLS_DISABLED"

        monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "true")
        still_guarded = client.post(
            "/api/v1/features/video_single/confirm",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "feature-confirm-adapter-0001"},
            json={"input": {"prompt": "test"}, "idempotency_key": "feature-confirm-adapter-0001"},
        )
        assert still_guarded.status_code == 200
        assert still_guarded.json()["error_code"] == "WEBAPP_FEATURE_JOB_ADAPTER_REQUIRED"
        # Provider calls alone can never make a Web confirm executable.  The
        # dedicated, default-off adapter flag and an actual private bridge are
        # both required before the portal exposes a confirm button.
        status = client.get("/api/v1/core/status")
        assert status.status_code == 200
        assert status.json()["data"]["flags"]["feature_job_adapter_enabled"] is False
        assert status.json()["data"]["web_feature_execution_available"] is False
        assert status.json()["data"]["web_feature_execution_features"] == []


def test_web_owned_profile_defaults_are_csrf_protected_and_cannot_change_canonical_authority(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_link(client)
        initial = client.get("/api/v1/auth/me").json()["data"]["account"]
        assert initial["profile"] == {"locale": "vi", "timezone": "Asia/Ho_Chi_Minh", "avatar_style": "gradient"}

        updated = client.post(
            "/api/v1/auth/profile",
            headers={"X-CSRF-Token": csrf},
            json={
                "display_name": "Hồ sơ Web",
                "locale": "en",
                "timezone": "UTC",
                "role": "admin",
                "canonical_user_id": "browser-forged",
            },
        )
        assert updated.status_code == 200
        payload = updated.json()
        assert payload["ok"] is True
        assert payload["data"]["account"]["display_name"] == "Hồ sơ Web"
        assert payload["data"]["account"]["profile"] == {"locale": "en", "timezone": "UTC", "avatar_style": "gradient"}
        assert payload["data"]["account"]["role"] == "user"
        assert "canonical_user_id" not in updated.text

        persisted = client.get("/api/v1/auth/me").json()["data"]["account"]
        assert persisted["display_name"] == "Hồ sơ Web"
        assert persisted["profile"]["timezone"] == "UTC"
        invalid_timezone = client.post(
            "/api/v1/auth/profile",
            headers={"X-CSRF-Token": csrf},
            json={"display_name": "Hồ sơ Web", "locale": "vi", "timezone": "Browser/forged"},
        )
        assert invalid_timezone.json()["error_code"] == "PROFILE_TIMEZONE_INVALID"
        forbidden = client.post(
            "/api/v1/auth/profile",
            headers={"X-CSRF-Token": "invalid"},
            json={"display_name": "Không được lưu"},
        )
        assert forbidden.status_code == 403


def test_account_activity_is_web_owned_owner_scoped_and_sanitized(tmp_path, monkeypatch):
    """Account history must not become a browser view of the raw audit table."""
    with make_client(tmp_path, monkeypatch) as first:
        registration = first.post(
            "/api/v1/auth/register",
            json={"email": "activity-owner@example.com", "password": "correct-horse-battery-staple", "display_name": "Activity owner"},
        )
        assert registration.json()["ok"] is True
        login = first.post("/api/v1/auth/login", json={"email": "activity-owner@example.com", "password": "correct-horse-battery-staple"})
        assert login.json()["ok"] is True
        # This is a Web-only account history, so signed-but-unlinked users may
        # use it without opening any canonical Bot/bridge data.
        assert first.get("/account/activity").status_code == 200
        with sqlite3.connect(tmp_path / "copyfast-test.db") as conn:
            account_id = conn.execute(
                "SELECT id FROM web_accounts WHERE email=?",
                ("activity-owner@example.com",),
            ).fetchone()[0]
            conn.execute(
                """INSERT INTO web_audit_events
                   (id, account_id, canonical_user_id, action, request_id, target, outcome, detail, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4()), account_id, "telegram-hidden-owner", "campaign.plan.create",
                    "request-id-must-not-reach-browser", "opaque-plan-target", "ok",
                    "https://private.example/brief password=must-not-reach-browser", "2026-07-12T08:00:00+00:00",
                ),
            )
            conn.commit()

        activity = first.get("/api/v1/account/activity")
        assert activity.status_code == 200
        body = activity.json()
        assert body["ok"] is True
        assert body["status"] == "read_only"
        items = body["data"]["items"]
        assert any(item["label"] == "Tạo kế hoạch Web" for item in items)
        assert all(set(item) == {"label", "category", "status", "created_at"} for item in items)
        assert all(item["status"] in {"completed", "guarded", "read_only"} for item in items)
        for forbidden in ("telegram-hidden-owner", "request-id-must-not-reach-browser", "opaque-plan-target", "private.example", "must-not-reach-browser", "detail"):
            assert forbidden not in activity.text

        application = importlib.import_module("app").app
        with TestClient(application) as second:
            assert second.post(
                "/api/v1/auth/register",
                json={"email": "activity-other@example.com", "password": "correct-horse-battery-staple"},
            ).json()["ok"] is True
            assert second.post(
                "/api/v1/auth/login",
                json={"email": "activity-other@example.com", "password": "correct-horse-battery-staple"},
            ).json()["ok"] is True
            other = second.get("/api/v1/account/activity")
            assert other.status_code == 200
            assert "Tạo kế hoạch Web" not in other.text
            assert "activity-owner@example.com" not in other.text


def test_workspace_drafts_are_safe_idempotent_and_owner_scoped(tmp_path, monkeypatch):
    """Web drafts persist only safe scalar brief fields, never Bot state."""
    with make_client(tmp_path, monkeypatch) as first:
        assert first.post(
            "/api/v1/auth/register",
            json={"email": "draft-owner@example.com", "password": "correct-horse-battery-staple"},
        ).json()["ok"] is True
        login = first.post("/api/v1/auth/login", json={"email": "draft-owner@example.com", "password": "correct-horse-battery-staple"})
        csrf = login.json()["data"]["csrf_token"]
        # A draft library is Web-owned and intentionally usable before the
        # one-time Telegram link has been completed.
        assert first.get("/workspace").status_code == 200
        payload = {
            "feature_key": "video_product",
            "title": "Video ra mắt an toàn",
            "input": {"brief": "Video giới thiệu sản phẩm mới", "platform": "TikTok", "format": "9:16", "tier": "video-standard"},
            "idempotency_key": "workspace-draft-create-0001",
        }
        assert first.post("/api/v1/workspace/drafts", json=payload).status_code == 403
        created = first.post("/api/v1/workspace/drafts", headers={"X-CSRF-Token": csrf}, json=payload)
        assert created.status_code == 200
        body = created.json()
        assert body["ok"] is True
        assert body["status"] == "draft"
        item = body["data"]["item"]
        assert item["feature_key"] == "video_product"
        assert item["route"] == "/video/product"
        assert "input" not in item
        replay = first.post("/api/v1/workspace/drafts", headers={"X-CSRF-Token": csrf}, json=payload)
        assert replay.json()["data"]["item"]["id"] == item["id"]

        listing = first.get("/api/v1/workspace/drafts")
        assert listing.json()["data"]["items"][0]["id"] == item["id"]
        assert "brief" not in listing.text
        detail = first.get(f"/api/v1/workspace/drafts/{item['id']}")
        assert detail.status_code == 200
        detail_item = detail.json()["data"]["item"]
        assert detail_item["input"] == payload["input"]
        for forbidden in ("canonical_user_id", "telegram_id", "upload_ids", "voice_profile_id", "web_quote_receipt", "provider", "payment", "output"):
            assert forbidden not in detail.text.lower()

        edited = first.patch(
            f"/api/v1/workspace/drafts/{item['id']}",
            headers={"X-CSRF-Token": csrf},
            json={
                "title": "Video ra mắt đã cập nhật",
                "input": {"brief": "Brief đã rà soát", "scene_count": "3", "duration_seconds": "20"},
                "idempotency_key": "workspace-draft-update-0001",
            },
        )
        assert edited.json()["ok"] is True
        assert edited.json()["data"]["item"]["title"] == "Video ra mắt đã cập nhật"
        assert first.get(f"/api/v1/workspace/drafts/{item['id']}").json()["data"]["item"]["input"] == {"brief": "Brief đã rà soát", "scene_count": "3", "duration_seconds": "20"}

        for unsafe in (
            {"upload_ids": "forged-upload"},
            {"voice_profile_id": "forged-profile"},
            {"brief": {"nested": "not-scalar"}},
            {"brief": "api_key=secretvalue123456"},
            {"brief": "TXID 1234 for manual payment"},
        ):
            rejected = first.post(
                "/api/v1/workspace/drafts",
                headers={"X-CSRF-Token": csrf},
                json={"feature_key": "video_product", "title": "Unsafe draft", "input": unsafe, "idempotency_key": f"workspace-draft-reject-{uuid.uuid4()}"},
            )
            assert rejected.status_code == 422
        wrong_feature = first.post(
            "/api/v1/workspace/drafts",
            headers={"X-CSRF-Token": csrf},
            json={"feature_key": "account", "title": "Wrong feature", "input": {"brief": "No"}, "idempotency_key": "workspace-draft-wrong-feature"},
        )
        assert wrong_feature.status_code == 422

        archived = first.post(
            f"/api/v1/workspace/drafts/{item['id']}/archive",
            headers={"X-CSRF-Token": csrf},
            json={"idempotency_key": "workspace-draft-archive-0001"},
        )
        assert archived.json()["status"] == "archived"
        assert first.get("/api/v1/workspace/drafts").json()["data"]["items"] == []
        all_drafts = first.get("/api/v1/workspace/drafts?include_archived=true").json()["data"]["items"]
        assert all_drafts[0]["state"] == "archived"
        archived_update = first.patch(
            f"/api/v1/workspace/drafts/{item['id']}",
            headers={"X-CSRF-Token": csrf},
            json={"title": "Không sửa archived", "input": {"brief": "No"}, "idempotency_key": "workspace-draft-update-archived"},
        )
        assert archived_update.json()["error_code"] == "WORKSPACE_DRAFT_ARCHIVED"

        with sqlite3.connect(tmp_path / "copyfast-test.db") as conn:
            audits = conn.execute(
                "SELECT target, detail FROM web_audit_events WHERE action LIKE 'workspace.draft.%' ORDER BY rowid"
            ).fetchall()
        assert audits
        assert all(row[0] == item["id"] for row in audits)
        assert all("Video ra mắt" not in row[1] and "Brief đã rà soát" not in row[1] for row in audits)

        application = importlib.import_module("app").app
        with TestClient(application) as second:
            assert second.post(
                "/api/v1/auth/register",
                json={"email": "draft-other@example.com", "password": "correct-horse-battery-staple"},
            ).json()["ok"] is True
            assert second.post("/api/v1/auth/login", json={"email": "draft-other@example.com", "password": "correct-horse-battery-staple"}).json()["ok"] is True
            hidden = second.get(f"/api/v1/workspace/drafts/{item['id']}")
            assert hidden.status_code == 200
            assert hidden.json()["error_code"] == "WORKSPACE_DRAFT_NOT_FOUND"
            assert "Video ra mắt" not in hidden.text


def test_workspace_draft_list_filters_pages_and_never_searches_brief_bodies(tmp_path, monkeypatch):
    """The mature Web library stays owner-scoped, bounded and metadata-only."""
    with make_client(tmp_path, monkeypatch) as first:
        assert first.post(
            "/api/v1/auth/register",
            json={"email": "draft-library-owner@example.com", "password": "correct-horse-battery-staple"},
        ).json()["ok"] is True
        csrf = first.post(
            "/api/v1/auth/login",
            json={"email": "draft-library-owner@example.com", "password": "correct-horse-battery-staple"},
        ).json()["data"]["csrf_token"]

        def create_draft(feature_key: str, title: str, brief: str) -> dict:
            response = first.post(
                "/api/v1/workspace/drafts",
                headers={"X-CSRF-Token": csrf},
                json={
                    "feature_key": feature_key,
                    "title": title,
                    "input": {"brief": brief},
                    "idempotency_key": f"workspace-library-create-{uuid.uuid4()}",
                },
            )
            assert response.status_code == 200
            return response.json()["data"]["item"]

        first_active = create_draft("video_product", "Launch library alpha", "PRIVATE_BRIEF_NEVER_LIST alpha")
        archived = create_draft("voice_tts", "Voice library beta", "PRIVATE_BRIEF_NEVER_LIST beta")
        second_active = create_draft("video_product", "Launch library gamma", "PRIVATE_BRIEF_NEVER_LIST gamma")
        archived_response = first.post(
            f"/api/v1/workspace/drafts/{archived['id']}/archive",
            headers={"X-CSRF-Token": csrf},
            json={"idempotency_key": "workspace-library-archive-0001"},
        )
        assert archived_response.json()["status"] == "archived"

        with sqlite3.connect(tmp_path / "copyfast-test.db") as conn:
            audit_count_before_reads = conn.execute(
                "SELECT COUNT(*) FROM web_audit_events WHERE action LIKE 'workspace.draft.%'"
            ).fetchone()[0]

        default_listing = first.get("/api/v1/workspace/drafts")
        assert default_listing.status_code == 200
        assert {item["id"] for item in default_listing.json()["data"]["items"]} == {first_active["id"], second_active["id"]}
        legacy_all = first.get("/api/v1/workspace/drafts?include_archived=true")
        assert {item["id"] for item in legacy_all.json()["data"]["items"]} == {first_active["id"], archived["id"], second_active["id"]}
        explicit_active = first.get("/api/v1/workspace/drafts?state=active&include_archived=true")
        assert {item["id"] for item in explicit_active.json()["data"]["items"]} == {first_active["id"], second_active["id"]}

        page_one = first.get("/api/v1/workspace/drafts?state=all&limit=2&offset=0")
        assert page_one.status_code == 200
        page_one_data = page_one.json()["data"]
        assert page_one.json()["status"] == "read_only"
        assert page_one_data["pagination"] == {"limit": 2, "offset": 0, "returned": 2}
        assert page_one_data["has_more"] is True
        assert page_one_data["next_offset"] == 2
        assert page_one_data["filters"] == {"state": "all", "feature_key": "", "q": ""}
        assert page_one_data["summary"] == {"active": 2, "archived": 1}
        public_fields = {"id", "feature_key", "feature_title", "route", "title", "state", "created_at", "updated_at"}
        assert all(set(item) == public_fields for item in page_one_data["items"])
        assert "input" not in page_one.text.lower()
        assert "private_brief_never_list" not in page_one.text.lower()

        page_two = first.get("/api/v1/workspace/drafts?state=all&limit=2&offset=2")
        page_two_data = page_two.json()["data"]
        assert page_two_data["pagination"] == {"limit": 2, "offset": 2, "returned": 1}
        assert page_two_data["has_more"] is False
        assert page_two_data["next_offset"] is None
        page_one_ids = {item["id"] for item in page_one_data["items"]}
        page_two_ids = {item["id"] for item in page_two_data["items"]}
        assert page_one_ids.isdisjoint(page_two_ids)
        assert page_one_ids | page_two_ids == {first_active["id"], archived["id"], second_active["id"]}

        archived_only = first.get("/api/v1/workspace/drafts?state=archived")
        assert [item["id"] for item in archived_only.json()["data"]["items"]] == [archived["id"]]
        feature_only = first.get("/api/v1/workspace/drafts?state=all&feature_key=voice_tts")
        assert [item["id"] for item in feature_only.json()["data"]["items"]] == [archived["id"]]
        title_search = first.get("/api/v1/workspace/drafts?state=all&q=Voice")
        assert [item["id"] for item in title_search.json()["data"]["items"]] == [archived["id"]]
        body_search = first.get("/api/v1/workspace/drafts?state=all&q=PRIVATE_BRIEF_NEVER_LIST")
        assert body_search.json()["data"]["items"] == []
        assert first.get("/api/v1/workspace/drafts?state=queued").status_code == 422
        assert first.get("/api/v1/workspace/drafts?feature_key=account").status_code == 422

        with sqlite3.connect(tmp_path / "copyfast-test.db") as conn:
            audit_count_after_reads = conn.execute(
                "SELECT COUNT(*) FROM web_audit_events WHERE action LIKE 'workspace.draft.%'"
            ).fetchone()[0]
        assert audit_count_after_reads == audit_count_before_reads

        application = importlib.import_module("app").app
        with TestClient(application) as second:
            assert second.post(
                "/api/v1/auth/register",
                json={"email": "draft-library-other@example.com", "password": "correct-horse-battery-staple"},
            ).json()["ok"] is True
            assert second.post(
                "/api/v1/auth/login",
                json={"email": "draft-library-other@example.com", "password": "correct-horse-battery-staple"},
            ).json()["ok"] is True
            hidden = second.get("/api/v1/workspace/drafts?state=all&limit=2&offset=0")
            assert hidden.status_code == 200
            assert hidden.json()["data"]["items"] == []
            assert "Launch library" not in hidden.text
            assert "PRIVATE_BRIEF_NEVER_LIST" not in hidden.text


def test_catalog_declares_exact_web_workspace_draft_support(tmp_path, monkeypatch):
    """The UI must not offer a local draft on a read-only/history surface."""
    with make_client(tmp_path, monkeypatch) as client:
        response = client.get("/api/v1/catalog")
        assert response.status_code == 200
        features = response.json()["data"]["features"]
        support = {item["key"]: item["web_workspace_draft_supported"] for item in features}
        assert all(isinstance(item["web_workspace_draft_supported"], bool) for item in features)
        assert support["video_product"] is True
        assert support["voice_tts"] is True
        assert support["image_history"] is False
        assert support["workspace_drafts"] is False


def test_catalog_exposes_a_closed_browser_safe_menu_capability_catalog(tmp_path, monkeypatch):
    """Menu metadata may navigate, but it must never replay Bot callbacks."""
    with make_client(tmp_path, monkeypatch) as client:
        response = client.get("/api/v1/catalog")
        assert response.status_code == 200
        menu = response.json()["data"]["menu_capabilities"]

    by_key = {item["key"]: item for item in menu}
    assert {
        "workspace_home", "guided_start", "account", "memory_center", "reminder_center", "campaign_planner", "chat_workspace", "prompt_studio", "wallet",
        "wallet_topup", "membership", "packages", "documents", "subtitle_studio", "documents_pdf_to_word", "documents_image_to_pdf",
        "documents_compress", "documents_split", "documents_merge", "asset_vault",
        "image_studio", "image_prompt_composer", "image_edit", "image_upscale",
        "video_studio", "media_workspace", "guides", "pricing", "support",
        "media_factory", "video_factory_workflow",
    } == set(by_key)
    assert by_key["account"] == {
        "key": "account",
        "feature_key": "account",
        "title": "Tài khoản",
        "group": "account",
        "route": "/account",
        "authority": "SIGNED_CUSTOMER",
        "launch_mode": "WEB_NAVIGATION",
        "availability": "NAVIGATION_ONLY",
        "execution": "NO_EXECUTION_CLAIM",
        "description": "Hồ sơ và bảo mật Web theo signed session, tách khỏi callback Bot.",
    }
    assert by_key["wallet_topup"]["route"] == "/wallet/topup"
    assert by_key["wallet_topup"]["authority"] == "CORE_CANONICAL_PAYMENT"
    assert by_key["wallet_topup"]["launch_mode"] == "BRIDGE_GUARDED_PROXY"
    assert by_key["wallet_topup"]["availability"] == "GUARDED"
    assert by_key["wallet"]["authority"] == "CORE_CANONICAL_READ"
    assert by_key["wallet"]["launch_mode"] == "READ_ONLY_CANONICAL"
    assert by_key["wallet"]["availability"] == "GUARDED"
    assert by_key["guided_start"] == {
        "key": "guided_start",
        "feature_key": "feature_catalog",
        "title": "Tất cả công cụ",
        "group": "content",
        "route": "/features",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
        "availability": "NAVIGATION_ONLY",
        "execution": "NO_EXECUTION_CLAIM",
        "description": "Mở catalog Web theo mục tiêu để bắt đầu workflow mới; không phát lại guide, callback, state hoặc child action của Telegram.",
    }
    assert by_key["memory_center"] == {
        "key": "memory_center",
        "feature_key": "notes",
        "title": "Ghi chú & Memory",
        "group": "account",
        "route": "/notes",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
        "availability": "NAVIGATION_ONLY",
        "execution": "NO_EXECUTION_CLAIM",
        "description": "Mở Memory Center Web-owned với tổng quan, ghi chú, tag, archive và version history; không đọc quota, add-on hay dữ liệu Memory của Bot.",
    }
    assert by_key["reminder_center"]["feature_key"] == "reminders"
    assert by_key["reminder_center"]["route"] == "/reminders"
    assert by_key["reminder_center"]["authority"] == "SIGNED_CUSTOMER_WEB_NATIVE"
    assert by_key["campaign_planner"] == {
        "key": "campaign_planner",
        "feature_key": "campaign_planner",
        "title": "Campaign Planner",
        "group": "content",
        "route": "/campaigns",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
        "availability": "NAVIGATION_ONLY",
        "execution": "NO_EXECUTION_CLAIM",
        "description": "Mở Campaign Planner Web-owned với brief, mục tiêu, calendar marker và self-review riêng; không nhập suggestion, pending state, save/schedule hay publishing state của Telegram.",
    }
    assert by_key["membership"]["route"] == "/membership"
    assert by_key["membership"]["authority"] == "CORE_CANONICAL_READ"
    assert by_key["membership"]["launch_mode"] == "READ_ONLY_CANONICAL"
    assert by_key["membership"]["availability"] == "GUARDED"
    assert by_key["packages"]["route"] == "/packages"
    assert by_key["packages"]["authority"] == "CORE_CANONICAL_READ"
    assert by_key["packages"]["launch_mode"] == "READ_ONLY_CANONICAL"
    assert by_key["packages"]["availability"] == "GUARDED"
    assert by_key["subtitle_studio"]["route"] == "/subtitle-studio"
    assert by_key["subtitle_studio"]["authority"] == "SIGNED_CUSTOMER_WEB_NATIVE"
    assert by_key["subtitle_studio"]["launch_mode"] == "WEB_NAVIGATION"
    assert by_key["subtitle_studio"]["availability"] == "NAVIGATION_ONLY"
    assert by_key["asset_vault"]["route"] == "/asset-vault"
    assert by_key["documents_split"]["route"] == "/documents/split"
    assert all(item["execution"] == "NO_EXECUTION_CLAIM" for item in menu)
    allowed_fields = {
        "key", "feature_key", "title", "group", "route", "authority",
        "launch_mode", "availability", "execution", "description",
    }
    assert all(set(item) == allowed_fields for item in menu)
    serialized = json.dumps(menu, ensure_ascii=False)
    forbidden_fields = {"callback_data", "bot_action", "telegram_action", "raw_callback"}
    assert all(not (forbidden_fields & set(item)) for item in menu)
    assert "|" not in serialized


def test_login_runs_password_verification_for_missing_and_existing_accounts(tmp_path, monkeypatch):
    """Avoid an account-enumeration timing oracle on the login endpoint."""
    with make_client(tmp_path, monkeypatch) as client:
        registration = client.post(
            "/api/v1/auth/register",
            json={"email": "timing@example.com", "password": "correct-horse-battery-staple"},
        )
        assert registration.json()["ok"] is True

        import copyfast_auth

        original_verify = copyfast_auth._verify_password
        hashes_checked = []

        def observing_verify(password, encoded):
            hashes_checked.append(encoded)
            return original_verify(password, encoded)

        monkeypatch.setattr(copyfast_auth, "_verify_password", observing_verify)
        missing = client.post(
            "/api/v1/auth/login",
            json={"email": "missing@example.com", "password": "wrong-password"},
        )
        wrong = client.post(
            "/api/v1/auth/login",
            json={"email": "timing@example.com", "password": "wrong-password"},
        )
        assert missing.json()["error_code"] == wrong.json()["error_code"] == "LOGIN_DENIED"
        assert len(hashes_checked) == 2
        assert hashes_checked[0] == copyfast_auth._DUMMY_PASSWORD_HASH
        assert hashes_checked[1] != copyfast_auth._DUMMY_PASSWORD_HASH


def test_oauth_disabled_by_default_exposes_no_live_provider_path(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        providers = client.get("/api/v1/auth/providers")
        assert providers.status_code == 200
        assert providers.json()["data"]["providers"] == {"apple": {"enabled": False}, "github": {"enabled": False}, "google": {"enabled": False}, "telegram": {"enabled": False}}
        start = client.get("/api/v1/auth/oauth/google/start", follow_redirects=False)
        assert start.status_code == 303
        assert start.headers["location"] == "/login?oauth=unavailable"


def test_google_oauth_uses_signed_state_pkce_and_creates_an_oauth_only_account(tmp_path, monkeypatch):
    enable_oauth_provider(monkeypatch, "google")
    with make_client(tmp_path, monkeypatch) as client:
        import copyfast_auth

        seen = []

        async def fake_identity(provider, code, state_value):
            seen.append((provider, code, state_value))
            return {
                "provider": "google",
                "subject": "google-immutable-subject-001",
                "email": "new-google@example.com",
                "email_verified": True,
                "display_name": "Google User",
            }

        monkeypatch.setattr(copyfast_auth, "_fetch_oauth_identity", fake_identity)
        started = client.get("/api/v1/auth/oauth/google/start?next=/video/product", follow_redirects=False)
        state_value, query = oauth_state_from_redirect(started)
        assert started.headers["location"].startswith("https://accounts.google.com/o/oauth2/v2/auth?")
        assert query["response_type"] == ["code"]
        assert query["code_challenge_method"] == ["S256"]
        assert query["nonce"]
        assert "google-client-secret" not in started.headers["location"]
        assert "toan_aas_oauth_state" in started.headers["set-cookie"]

        callback = client.get(f"/api/v1/auth/oauth/google/callback?code=opaque-code&state={state_value}", follow_redirects=False)
        assert callback.status_code == 303
        assert callback.headers["location"] == "/video/product"
        assert seen == [("google", "opaque-code", state_value)]
        me = client.get("/api/v1/auth/me")
        account = me.json()["data"]["account"]
        assert account["email"] == "new-google@example.com"
        assert account["login_methods"] == {"email": False, "telegram_oidc": False, "telegram": False, "google": True, "github": False, "apple": False}
        assert "google-immutable-subject-001" not in me.text

        from copyfast_db import transaction

        with transaction() as conn:
            stored_subject = conn.execute("SELECT subject_hash FROM web_external_identities WHERE provider='google'").fetchone()[0]
            assert stored_subject != "google-immutable-subject-001"
            assert len(stored_subject) == 64
        replay = client.get(f"/api/v1/auth/oauth/google/callback?code=opaque-code&state={state_value}", follow_redirects=False)
        assert replay.status_code == 303
        assert replay.headers["location"] == "/login?oauth=state"


def test_oauth_state_cookies_isolate_parallel_provider_tabs_and_preserve_provider_policy(tmp_path, monkeypatch):
    """One provider callback must not consume or erase another tab's proof."""
    enable_oauth_provider(monkeypatch, "google")
    enable_oauth_provider(monkeypatch, "github")
    enable_apple_oauth(monkeypatch)
    # This route-level state test stubs every identity exchange.  A tiny JWT
    # stand-in lets the app's startup validation mint Apple's local client
    # assertion without adding a network/provider dependency to this test.
    monkeypatch.setitem(sys.modules, "jwt", types.SimpleNamespace(encode=lambda *_args, **_kwargs: "test-apple-client-assertion"))
    with make_client(tmp_path, monkeypatch, base_url="https://testserver") as client:
        import copyfast_auth

        seen = []

        async def fake_identity(provider, code, state_value):
            seen.append((provider, code, state_value))
            return {
                "provider": provider,
                "subject": f"{provider}-parallel-subject",
                "email": f"{provider}-parallel@example.com",
                "email_verified": True,
                "display_name": f"{provider.title()} Parallel",
            }

        async def fake_apple_identity(code, state_value, *, display_name=""):
            seen.append(("apple", code, state_value))
            return {
                "provider": "apple",
                "subject": "apple-parallel-subject",
                "email": "apple-parallel@example.com",
                "email_verified": True,
                "display_name": display_name,
            }

        monkeypatch.setattr(copyfast_auth, "_fetch_oauth_identity", fake_identity)
        monkeypatch.setattr(copyfast_auth, "_fetch_apple_identity", fake_apple_identity)

        google_start = client.get("/api/v1/auth/oauth/google/start?next=/video/product", follow_redirects=False)
        google_state, _ = oauth_state_from_redirect(google_start)
        github_start = client.get("/api/v1/auth/oauth/github/start?next=/assets", follow_redirects=False)
        github_state, _ = oauth_state_from_redirect(github_start)
        apple_start = client.get("/api/v1/auth/oauth/apple/start?next=/documents", follow_redirects=False)
        apple_state, _ = oauth_state_from_redirect(apple_start)

        cookie_names = {
            provider: copyfast_auth._oauth_state_cookie_name(provider, state_value)
            for provider, state_value in (
                ("google", google_state),
                ("github", github_state),
                ("apple", apple_state),
            )
        }
        assert len(set(cookie_names.values())) == 3
        assert all(name.startswith("__Host-toan_aas_oauth_state_v1_") for name in cookie_names.values())
        assert all(state_value not in cookie_names[provider] for provider, state_value in (
            ("google", google_state),
            ("github", github_state),
            ("apple", apple_state),
        ))
        assert all(client.cookies.get(cookie_name) for cookie_name in cookie_names.values())
        assert "SameSite=lax" in google_start.headers["set-cookie"]
        assert "SameSite=lax" in github_start.headers["set-cookie"]
        assert "SameSite=none" in apple_start.headers["set-cookie"]

        # A provider/state mismatch cannot touch a valid state cookie owned by
        # another flow.  The real Google callback still succeeds afterwards.
        mismatch = client.get(
            f"/api/v1/auth/oauth/github/callback?code=wrong-provider-code&state={google_state}",
            follow_redirects=False,
        )
        assert mismatch.headers["location"] == "/login?oauth=state"
        assert client.cookies.get(cookie_names["google"])
        assert client.cookies.get(cookie_names["github"])
        assert client.cookies.get(cookie_names["apple"])

        github_callback = client.get(
            f"/api/v1/auth/oauth/github/callback?code=github-parallel-code&state={github_state}",
            follow_redirects=False,
        )
        assert github_callback.headers["location"] == "/assets"
        assert client.cookies.get(cookie_names["github"]) is None
        assert client.cookies.get(cookie_names["google"])
        assert client.cookies.get(cookie_names["apple"])

        google_callback = client.get(
            f"/api/v1/auth/oauth/google/callback?code=google-parallel-code&state={google_state}",
            follow_redirects=False,
        )
        assert google_callback.headers["location"] == "/video/product"
        assert client.cookies.get(cookie_names["google"]) is None
        assert client.cookies.get(cookie_names["apple"])

        apple_callback = client.post(
            "/api/v1/auth/oauth/apple/callback",
            data={"code": "apple-parallel-code", "state": apple_state},
            follow_redirects=False,
        )
        assert apple_callback.headers["location"] == "/documents"
        assert client.cookies.get(cookie_names["apple"]) is None
        assert seen == [
            ("github", "github-parallel-code", github_state),
            ("google", "google-parallel-code", google_state),
            ("apple", "apple-parallel-code", apple_state),
        ]


def test_telegram_oidc_creates_a_web_session_but_requires_the_same_bot_identity(tmp_path, monkeypatch):
    """Telegram Login makes browser sign-in real without trusting a raw ID.

    The signed OIDC profile can create the Web identity shell.  It cannot,
    however, open Bot-owned wallet/job data until the Bot callback proves the
    same numeric Telegram identity for the one-time account-link code.
    """
    enable_oauth_provider(monkeypatch, "telegram")
    with make_client(tmp_path, monkeypatch) as client:
        import copyfast_auth

        calls = []

        async def fake_identity(provider, code, state_value):
            calls.append((provider, code, state_value))
            return {
                "provider": "telegram",
                "subject": "987654321",
                "email": "",
                "display_name": "Telegram OIDC User",
            }

        monkeypatch.setattr(copyfast_auth, "_fetch_oauth_identity", fake_identity)
        started = client.get("/api/v1/auth/oauth/telegram/start?next=/video/product", follow_redirects=False)
        state_value, query = oauth_state_from_redirect(started)
        assert started.headers["location"].startswith("https://oauth.telegram.org/auth?")
        assert query["response_type"] == ["code"]
        assert query["scope"] == ["openid profile"]
        assert query["code_challenge_method"] == ["S256"]
        assert query["nonce"]
        assert "telegram-client-secret" not in started.headers["location"]

        callback = client.get(f"/api/v1/auth/oauth/telegram/callback?code=opaque-code&state={state_value}", follow_redirects=False)
        assert callback.status_code == 303
        assert callback.headers["location"] == "/video/product"
        assert calls == [("telegram", "opaque-code", state_value)]
        me = client.get("/api/v1/auth/me")
        account = me.json()["data"]["account"]
        assert account["email"] == ""
        assert account["account_type"] == "telegram"
        assert account["telegram_linked"] is False
        assert account["login_methods"] == {"email": False, "telegram_oidc": True, "telegram": False, "google": False, "github": False, "apple": False}
        assert "987654321" not in me.text

        csrf = me.json()["data"]["csrf_token"]
        link = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf})
        code = link.json()["data"]["code"]
        mismatch = confirm_link(client, code, canonical_user_id="987654322")
        assert mismatch.status_code == 409
        assert mismatch.json()["error_code"] == "TELEGRAM_OIDC_MISMATCH"
        pending_status = client.get("/api/v1/auth/telegram/link/status").json()["data"]
        assert pending_status["linked"] is False
        assert pending_status["pending"] is True
        assert pending_status["ready_to_complete"] is False

        matched = confirm_link(client, code, canonical_user_id="987654321")
        assert matched.status_code == 200
        assert matched.json()["ok"] is True
        pending_completion = client.get("/api/v1/auth/telegram/link/status").json()["data"]
        assert pending_completion["ready_to_complete"] is True
        assert "987654321" not in json.dumps(pending_completion)
        assert complete_link(client, csrf).json()["ok"] is True
        completed = client.get("/api/v1/auth/me")
        assert completed.json()["data"]["account"]["telegram_linked"] is True
        assert "987654321" not in completed.text


def test_telegram_oidc_can_sign_into_the_existing_same_canonical_bot_account(tmp_path, monkeypatch):
    """Two cryptographic proofs for one Telegram user may safely converge."""
    enable_oauth_provider(monkeypatch, "telegram")
    with make_client(tmp_path, monkeypatch) as client:
        registration = client.post(
            "/api/v1/auth/register",
            json={"email": "canonical@example.com", "password": "correct-horse-battery-staple", "display_name": "Canonical"},
        )
        assert registration.json()["ok"] is True
        login = client.post("/api/v1/auth/login", json={"email": "canonical@example.com", "password": "correct-horse-battery-staple"})
        csrf = login.json()["data"]["csrf_token"]
        code = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf}).json()["data"]["code"]
        assert confirm_link(client, code, canonical_user_id="246802468").json()["ok"] is True
        assert complete_link(client, csrf).json()["ok"] is True
        assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).json()["ok"] is True

        import copyfast_auth

        async def fake_identity(provider, _code, _state_value):
            assert provider == "telegram"
            return {
                "provider": "telegram",
                "subject": "246802468",
                "email": "",
                "display_name": "Should not replace the Web profile",
            }

        monkeypatch.setattr(copyfast_auth, "_fetch_oauth_identity", fake_identity)
        started = client.get("/api/v1/auth/oauth/telegram/start", follow_redirects=False)
        state_value, _query = oauth_state_from_redirect(started)
        callback = client.get(f"/api/v1/auth/oauth/telegram/callback?code=existing-user-code&state={state_value}", follow_redirects=False)
        assert callback.status_code == 303
        assert callback.headers["location"] == "/dashboard"
        account = client.get("/api/v1/auth/me").json()["data"]["account"]
        assert account["email"] == "canonical@example.com"
        assert account["display_name"] == "Canonical"
        assert account["login_methods"]["telegram"] is True
        assert account["login_methods"]["telegram_oidc"] is True
        assert "246802468" not in client.get("/api/v1/auth/me").text


def test_telegram_oidc_id_token_uses_fixed_jwks_and_bot_compatible_profile_id(tmp_path, monkeypatch):
    enable_oauth_provider(monkeypatch, "telegram")
    with make_client(tmp_path, monkeypatch):
        import copyfast_auth
        import jwt
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec, rsa

        config = copyfast_auth._oauth_client_configuration("telegram")
        state_value = "telegram-rsa-verification-state"
        nonce = copyfast_auth._oauth_derived_token("nonce", state_value)
        rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_pem = rsa_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        public_numbers = rsa_key.public_key().public_numbers()

        def jwk_number(value):
            return base64.urlsafe_b64encode(value.to_bytes((value.bit_length() + 7) // 8, "big")).rstrip(b"=").decode("ascii")

        jwks = {
            "keys": [{
                "kty": "RSA", "kid": "telegram-rsa-kid", "use": "sig", "alg": "RS256",
                "n": jwk_number(public_numbers.n), "e": jwk_number(public_numbers.e),
            }],
        }

        async def fake_jwks(method, url, **_kwargs):
            assert method == "GET"
            assert url == copyfast_auth.TELEGRAM_OAUTH_JWKS_URL
            return jwks

        monkeypatch.setattr(copyfast_auth, "_oauth_json_request", fake_jwks)
        payload = {
            "iss": "https://oauth.telegram.org",
            "aud": config["client_id"],
            "sub": "telegram-oidc-app-subject",
            "nonce": nonce,
            "iat": int(time.time()) - 1,
            "exp": int(time.time()) + 60,
            "id": 246802468,
            "name": "Telegram Signed User",
        }
        token = jwt.encode(payload, private_pem, algorithm="RS256", headers={"kid": "telegram-rsa-kid"})
        identity = asyncio.run(copyfast_auth._verify_telegram_id_token(token, client_id=config["client_id"], expected_nonce=nonce))
        assert identity == {"provider": "telegram", "subject": "246802468", "email": "", "email_verified": False, "display_name": "Telegram Signed User"}

        bad_id_payload = {**payload, "id": "not-a-telegram-id"}
        bad_id_token = jwt.encode(bad_id_payload, private_pem, algorithm="RS256", headers={"kid": "telegram-rsa-kid"})
        with pytest.raises(copyfast_auth.OAuthIdentityError):
            asyncio.run(copyfast_auth._verify_telegram_id_token(bad_id_token, client_id=config["client_id"], expected_nonce=nonce))

        ec_key = ec.generate_private_key(ec.SECP256R1())
        es256_token = jwt.encode(payload, ec_key, algorithm="ES256", headers={"kid": "telegram-es256-kid"})
        with pytest.raises(copyfast_auth.OAuthIdentityError):
            asyncio.run(copyfast_auth._verify_telegram_id_token(es256_token, client_id=config["client_id"], expected_nonce=nonce))


def test_verified_oauth_email_collision_creates_an_isolated_oauth_only_account(tmp_path, monkeypatch):
    """A verified OAuth mailbox must never take over a pre-registered account."""
    enable_oauth_provider(monkeypatch, "github")
    with make_client(tmp_path, monkeypatch) as owner_client:
        import copyfast_auth
        from copyfast_db import transaction

        contact_email = "existing@example.com"
        raw_subject = "github-immutable-subject-001"

        async def matching_email_identity(provider, code, state_value):
            return {
                "provider": provider,
                "subject": raw_subject,
                "email": contact_email,
                "email_verified": True,
                "display_name": "GitHub User",
            }

        monkeypatch.setattr(copyfast_auth, "_fetch_oauth_identity", matching_email_identity)
        assert owner_client.post(
            "/api/v1/auth/register",
            json={"email": contact_email, "password": "correct-horse-battery-staple", "display_name": "Original Owner"},
        ).json()["ok"] is True
        owner_login = owner_client.post(
            "/api/v1/auth/login",
            json={"email": contact_email, "password": "correct-horse-battery-staple"},
        )
        owner_before = owner_client.get("/api/v1/auth/me").json()["data"]
        owner_cookie_name = copyfast_auth._cookie_name(copyfast_auth.SESSION_COOKIE)
        owner_cookie = owner_client.cookies.get(owner_cookie_name)
        assert owner_cookie

        # A separate browser completes OAuth. The original signed session is
        # intentionally neither read into the callback nor replaced/revoked.
        with TestClient(owner_client.app) as oauth_client:
            started = oauth_client.get("/api/v1/auth/oauth/github/start", follow_redirects=False)
            state_value, query = oauth_state_from_redirect(started)
            assert query["scope"] == ["read:user user:email"]
            callback = oauth_client.get(
                f"/api/v1/auth/oauth/github/callback?code=opaque-code&state={state_value}",
                follow_redirects=False,
            )
            assert callback.status_code == 303
            assert callback.headers["location"] == "/dashboard"
            isolated = oauth_client.get("/api/v1/auth/me").json()["data"]["account"]
            assert isolated["email"] == contact_email
            assert isolated["account_type"] == "oauth_only"
            assert isolated["oauth_only"] is True
            assert isolated["login_methods"] == {
                "email": False,
                "telegram_oidc": False,
                "telegram": False,
                "google": False,
                "github": True,
                "apple": False,
            }
            assert raw_subject not in json.dumps(isolated)

        # The first account and its session/data stay exactly where they were.
        owner_after = owner_client.get("/api/v1/auth/me").json()["data"]
        assert owner_after["csrf_token"] == owner_before["csrf_token"] == owner_login.json()["data"]["csrf_token"]
        assert owner_after["account"]["display_name"] == "Original Owner"
        assert owner_client.cookies.get(owner_cookie_name) == owner_cookie

        with transaction() as conn:
            rows = conn.execute(
                "SELECT id, email, password_login_enabled, display_name FROM web_accounts ORDER BY created_at, id"
            ).fetchall()
            assert len(rows) == 2
            original = next(row for row in rows if row[1] == contact_email)
            isolated_row = next(row for row in rows if row[0] != original[0])
            assert original[2:] == (1, "Original Owner")
            assert isolated_row[2] == 0
            assert copyfast_auth._is_oauth_only_email(isolated_row[1])
            assert contact_email not in isolated_row[1]
            assert raw_subject not in isolated_row[1]
            contact = conn.execute(
                "SELECT account_id, provider, email FROM web_account_oauth_contacts"
            ).fetchall()
            assert contact == [(isolated_row[0], "github", contact_email)]
            mapped_account = conn.execute(
                "SELECT account_id FROM web_external_identities WHERE provider='github'"
            ).fetchone()[0]
            assert mapped_account == isolated_row[0]
            audit_text = "\n".join(str(row[0] or "") for row in conn.execute("SELECT detail FROM web_audit_events").fetchall())
            assert contact_email not in audit_text
            assert raw_subject not in audit_text
            internal_alias = isolated_row[1]
        assert internal_alias not in json.dumps(isolated)

        # Neither the public contact nor the internal alias can become a
        # password path for the isolated OAuth account.
        with TestClient(owner_client.app) as password_client:
            assert password_client.post(
                "/api/v1/auth/login",
                json={"email": contact_email, "password": "not-the-original-password"},
            ).json()["error_code"] == "LOGIN_DENIED"
            assert password_client.post(
                "/api/v1/auth/login",
                json={"email": internal_alias, "password": "not-a-real-password"},
            ).json()["error_code"] == "LOGIN_DENIED"
            assert password_client.get("/api/v1/auth/me").status_code == 401

        # Replaying the same verified immutable subject signs into the
        # isolated account; it never creates a third account or touches the
        # original account.
        with TestClient(owner_client.app) as repeat_client:
            started = repeat_client.get("/api/v1/auth/oauth/github/start", follow_redirects=False)
            state_value, _ = oauth_state_from_redirect(started)
            assert repeat_client.get(
                f"/api/v1/auth/oauth/github/callback?code=repeat-code&state={state_value}",
                follow_redirects=False,
            ).headers["location"] == "/dashboard"
            repeated = repeat_client.get("/api/v1/auth/me").json()["data"]["account"]
            assert repeated["email"] == contact_email
            assert repeated["oauth_only"] is True
        with transaction() as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_accounts").fetchone()[0] == 2
            assert conn.execute("SELECT COUNT(*) FROM web_account_oauth_contacts").fetchone()[0] == 1


def test_explicit_oauth_link_records_only_an_exact_verified_contact(tmp_path, monkeypatch):
    """Linking stays opt-in and a mismatched provider email cannot take over UI contact."""
    enable_oauth_provider(monkeypatch, "github")
    enable_oauth_provider(monkeypatch, "google")
    # This route test stubs the provider exchange completely; a minimal JWT
    # module lets startup validate the enabled Google capability without
    # requiring crypto extras in this focused local test environment.
    monkeypatch.setitem(sys.modules, "jwt", types.SimpleNamespace())
    with make_client(tmp_path, monkeypatch) as client:
        import copyfast_auth
        from copyfast_db import transaction

        account_email = "link-owner@example.com"

        async def linked_identity(provider, code, state_value):
            if provider == "github":
                return {
                    "provider": "github",
                    "subject": "github-link-subject",
                    "email": account_email,
                    "email_verified": True,
                    "display_name": "GitHub Link",
                }
            return {
                "provider": "google",
                "subject": "google-mismatched-subject",
                "email": "different-owner@example.com",
                "email_verified": True,
                "display_name": "Google Different Contact",
            }

        monkeypatch.setattr(copyfast_auth, "_fetch_oauth_identity", linked_identity)
        assert client.post(
            "/api/v1/auth/register",
            json={"email": account_email, "password": "correct-horse-battery-staple"},
        ).json()["ok"] is True
        login = client.post(
            "/api/v1/auth/login",
            json={"email": account_email, "password": "correct-horse-battery-staple"},
        )
        csrf = login.json()["data"]["csrf_token"]
        assert client.post("/api/v1/auth/oauth/github/link/start", headers={"X-CSRF-Token": "wrong"}, json={}).status_code == 403

        with TestClient(client.app) as second_browser:
            second_login = second_browser.post(
                "/api/v1/auth/login",
                json={"email": account_email, "password": "correct-horse-battery-staple"},
            )
            assert second_login.json()["ok"] is True
            github_start = client.post("/api/v1/auth/oauth/github/link/start", headers={"X-CSRF-Token": csrf}, json={})
            github_state, _ = oauth_state_from_redirect(client.get(github_start.json()["data"]["start_path"], follow_redirects=False))
            assert client.get(
                f"/api/v1/auth/oauth/github/callback?code=github-link-code&state={github_state}",
                follow_redirects=False,
            ).headers["location"] == "/account?oauth=linked"
            assert second_browser.get("/api/v1/auth/me").status_code == 401

        csrf = client.get("/api/v1/auth/me").json()["data"]["csrf_token"]
        google_start = client.post("/api/v1/auth/oauth/google/link/start", headers={"X-CSRF-Token": csrf}, json={})
        google_state, _ = oauth_state_from_redirect(client.get(google_start.json()["data"]["start_path"], follow_redirects=False))
        assert client.get(
            f"/api/v1/auth/oauth/google/callback?code=google-link-code&state={google_state}",
            follow_redirects=False,
        ).headers["location"] == "/account?oauth=linked"
        csrf = client.get("/api/v1/auth/me").json()["data"]["csrf_token"]

        account = client.get("/api/v1/auth/me").json()["data"]["account"]
        assert account["email"] == account_email
        assert account["account_type"] == "standard"
        assert account["oauth_only"] is False
        assert account["login_methods"] == {
            "email": True,
            "telegram_oidc": False,
            "telegram": False,
            "google": True,
            "github": True,
            "apple": False,
        }
        with transaction() as conn:
            verified_contact = conn.execute(
                "SELECT provider, email FROM web_account_oauth_contacts"
            ).fetchall()
            assert verified_contact == [("github", account_email)]
            assert conn.execute("SELECT COUNT(*) FROM web_accounts").fetchone()[0] == 1

        # A later sign-in with the already linked GitHub subject returns to
        # the existing account instead of using matching email to create or
        # take over another account.
        assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).json()["ok"] is True
        started = client.get("/api/v1/auth/oauth/github/start", follow_redirects=False)
        state_value, _ = oauth_state_from_redirect(started)
        assert client.get(
            f"/api/v1/auth/oauth/github/callback?code=github-repeat-code&state={state_value}",
            follow_redirects=False,
        ).headers["location"] == "/dashboard"
        assert client.get("/api/v1/auth/me").json()["data"]["account"]["email"] == account_email


def test_apple_oauth_uses_form_post_and_can_link_without_relaxing_session_cookie(tmp_path, monkeypatch):
    enable_apple_oauth(monkeypatch)
    with make_client(tmp_path, monkeypatch, base_url="https://testserver") as client:
        import copyfast_auth
        import jwt

        seen = []

        async def fake_apple_identity(code, state_value, *, display_name=""):
            seen.append((code, state_value, display_name))
            return {
                "provider": "apple",
                "subject": "apple-immutable-subject-001",
                "email": "apple-user@example.com",
                "email_verified": True,
                "display_name": display_name,
            }

        monkeypatch.setattr(copyfast_auth, "_fetch_apple_identity", fake_apple_identity)
        config = copyfast_auth._oauth_client_configuration("apple")
        client_secret = copyfast_auth._apple_client_secret(config)
        claims = jwt.decode(client_secret, options={"verify_signature": False})
        assert claims["iss"] == "APPLETEAM1"
        assert claims["aud"] == "https://appleid.apple.com"
        assert claims["sub"] == "com.toanaas.web"

        started = client.get("/api/v1/auth/oauth/apple/start?next=/documents", follow_redirects=False)
        state_value, query = oauth_state_from_redirect(started)
        assert started.headers["location"].startswith("https://appleid.apple.com/auth/authorize?")
        assert query["response_mode"] == ["form_post"]
        assert query["response_type"] == ["code id_token"]
        assert query["scope"] == ["name email"]
        assert "code_challenge" not in query
        assert "SameSite=none" in started.headers["set-cookie"]
        signed_in = client.post(
            "/api/v1/auth/oauth/apple/callback",
            data={"code": "apple-code", "state": state_value, "user": json.dumps({"name": {"firstName": "Apple", "lastName": "User"}, "email": "untrusted@example.com"})},
            follow_redirects=False,
        )
        assert signed_in.status_code == 303
        assert signed_in.headers["location"] == "/documents"
        assert seen == [("apple-code", state_value, "Apple User")]
        account = client.get("/api/v1/auth/me").json()["data"]["account"]
        assert account["login_methods"] == {"email": False, "telegram_oidc": False, "telegram": False, "google": False, "github": False, "apple": True}
        assert "apple-immutable-subject-001" not in client.get("/api/v1/auth/me").text

    # Apple link callback is cross-site form POST: transfer only its temporary
    # state cookie to a separate HTTPS client, deliberately omitting the Lax
    # signed-session cookie. The active session binding in the DB still
    # protects and completes the explicit link.
    with make_client(tmp_path, monkeypatch, base_url="https://testserver") as client:
        import copyfast_auth

        async def fake_link_identity(code, state_value, *, display_name=""):
            return {"provider": "apple", "subject": "apple-immutable-subject-002", "email": "", "display_name": display_name}

        monkeypatch.setattr(copyfast_auth, "_fetch_apple_identity", fake_link_identity)
        registration = client.post("/api/v1/auth/register", json={"email": "apple-link@example.com", "password": "correct-horse-battery-staple"})
        assert registration.json()["ok"] is True
        login = client.post("/api/v1/auth/login", json={"email": "apple-link@example.com", "password": "correct-horse-battery-staple"})
        csrf = login.json()["data"]["csrf_token"]
        link_start = client.post("/api/v1/auth/oauth/apple/link/start", headers={"X-CSRF-Token": csrf}, json={})
        provider_redirect = client.get(link_start.json()["data"]["start_path"], follow_redirects=False)
        link_state, _ = oauth_state_from_redirect(provider_redirect)
        state_cookie_name = copyfast_auth._oauth_state_cookie_name("apple", link_state)
        state_cookie = client.cookies.get(state_cookie_name)
        assert state_cookie
        with TestClient(client.app, base_url="https://testserver") as form_post_client:
            form_post_client.cookies.set(state_cookie_name, state_cookie)
            linked = form_post_client.post(
                "/api/v1/auth/oauth/apple/callback",
                data={"code": "apple-link-code", "state": link_state},
                follow_redirects=False,
            )
            replacement_cookie = form_post_client.cookies.get(copyfast_auth._cookie_name(copyfast_auth.SESSION_COOKIE))
        assert linked.status_code == 303
        assert linked.headers["location"] == "/account?oauth=linked"
        # A real browser owns both the pre-redirect tab and Apple's form-post
        # callback, so it receives the replacement cookie even though the Lax
        # session cookie was not sent on the cross-site POST. This separate
        # TestClient models only the missing request cookie, then transfers
        # the response cookie back to that shared browser jar.
        assert replacement_cookie
        client.cookies.set(copyfast_auth._cookie_name(copyfast_auth.SESSION_COOKIE), replacement_cookie)
        linked_methods = client.get("/api/v1/auth/me").json()["data"]["account"]["login_methods"]
        assert linked_methods["email"] is True
        assert linked_methods["apple"] is True


def test_secure_deployments_use_host_prefixed_cookie_names_and_reject_legacy_session_cookie(tmp_path, monkeypatch):
    volume = tmp_path / "host-cookie-volume"
    volume.mkdir()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("WEB_COOKIE_SECURE", "true")
    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", str(volume))
    with make_client(
        tmp_path,
        monkeypatch,
        base_url="https://testserver",
        session_database_path=volume / "copyfast-test.db",
    ) as client:
        import copyfast_auth

        registration = client.post("/api/v1/auth/register", json={"email": "host-cookie@example.com", "password": "correct-horse-battery-staple"})
        assert registration.json()["ok"] is True
        login = client.post("/api/v1/auth/login", json={"email": "host-cookie@example.com", "password": "correct-horse-battery-staple"})
        host_cookie_name = copyfast_auth._cookie_name(copyfast_auth.SESSION_COOKIE)
        assert host_cookie_name == "__Host-toan_aas_session"
        assert f"{host_cookie_name}=" in login.headers["set-cookie"]
        assert client.get("/api/v1/auth/me").status_code == 200

        # A copied signed value under the legacy parent-domain-capable name
        # must not authenticate a production request.
        host_cookie_value = client.cookies.get(host_cookie_name)
        with TestClient(client.app, base_url="https://testserver") as legacy_client:
            legacy_client.cookies.set("toan_aas_session", host_cookie_value)
            assert legacy_client.get("/api/v1/auth/me").status_code == 401


def test_apple_new_identity_without_a_verified_email_fails_closed(tmp_path, monkeypatch):
    enable_apple_oauth(monkeypatch)
    with make_client(tmp_path, monkeypatch, base_url="https://testserver") as client:
        import copyfast_auth

        calls = []

        async def no_email_identity(code, state_value, *, display_name=""):
            calls.append((code, state_value))
            return {"provider": "apple", "subject": "apple-no-email-subject", "email": "", "display_name": display_name}

        monkeypatch.setattr(copyfast_auth, "_fetch_apple_identity", no_email_identity)
        started = client.get("/api/v1/auth/oauth/apple/start", follow_redirects=False)
        state_value, _ = oauth_state_from_redirect(started)
        failed = client.post("/api/v1/auth/oauth/apple/callback", data={"code": "apple-no-email-code", "state": state_value}, follow_redirects=False)
        assert failed.headers["location"] == "/login?oauth=failed"
        assert calls == [("apple-no-email-code", state_value)]
        from copyfast_db import transaction

        with transaction() as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_external_identities WHERE provider='apple'").fetchone()[0] == 0


def test_apple_id_token_verification_uses_apple_rsa_jwks_not_the_es256_client_secret(tmp_path, monkeypatch):
    enable_apple_oauth(monkeypatch)
    with make_client(tmp_path, monkeypatch, base_url="https://testserver"):
        import copyfast_auth
        import jwt
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec, rsa

        config = copyfast_auth._oauth_client_configuration("apple")
        state_value = "apple-rsa-verification-state"
        nonce = copyfast_auth._oauth_derived_token("nonce", state_value)
        rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_pem = rsa_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        public_numbers = rsa_key.public_key().public_numbers()

        def jwk_number(value):
            return base64.urlsafe_b64encode(value.to_bytes((value.bit_length() + 7) // 8, "big")).rstrip(b"=").decode("ascii")

        jwks = {"keys": [{"kty": "RSA", "kid": "apple-rsa-kid", "use": "sig", "alg": "RS256", "n": jwk_number(public_numbers.n), "e": jwk_number(public_numbers.e)}]}

        async def fake_jwks(method, url, **_kwargs):
            assert method == "GET"
            assert url == copyfast_auth.APPLE_JWKS_URL
            return jwks

        monkeypatch.setattr(copyfast_auth, "_oauth_json_request", fake_jwks)
        payload = {
            "iss": "https://appleid.apple.com",
            "aud": config["client_id"],
            "sub": "apple-rsa-subject",
            "nonce": nonce,
            "iat": int(time.time()) - 1,
            "exp": int(time.time()) + 60,
            "email": "apple-rsa@example.com",
            "email_verified": True,
        }
        token = jwt.encode(payload, private_pem, algorithm="RS256", headers={"kid": "apple-rsa-kid"})
        identity = asyncio.run(copyfast_auth._verify_apple_id_token(token, client_id=config["client_id"], expected_nonce=nonce))
        assert identity == {"provider": "apple", "subject": "apple-rsa-subject", "email": "apple-rsa@example.com", "email_verified": True}

        ec_key = ec.generate_private_key(ec.SECP256R1())
        es256_token = jwt.encode(payload, ec_key, algorithm="ES256", headers={"kid": "apple-es256-kid"})
        with pytest.raises(copyfast_auth.OAuthIdentityError):
            asyncio.run(copyfast_auth._verify_apple_id_token(es256_token, client_id=config["client_id"], expected_nonce=nonce))


def test_https_oauth_configuration_requires_secure_cookies(tmp_path, monkeypatch):
    enable_oauth_provider(monkeypatch, "google")
    monkeypatch.setenv("WEBAPP_PUBLIC_BASE_URL", "https://app.toanaas.vn")
    monkeypatch.delenv("WEB_COOKIE_SECURE", raising=False)
    with pytest.raises(RuntimeError, match="WEB_COOKIE_SECURE"):
        with make_client(tmp_path, monkeypatch):
            pass


def test_support_ticket_refuses_sensitive_data_before_it_can_reach_the_bridge(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_link(client)
        rejected = client.post(
            "/api/v1/support/tickets",
            headers={"X-CSRF-Token": csrf},
            json={
                "subject": "Không thể gọi provider",
                "detail": "api_key=sk_1234567890abcdefghi",
                "idempotency_key": "ticket-secret-guard-0001",
            },
        )
        assert rejected.status_code == 422
        assert rejected.json()["error_code"] == "REQUEST_INVALID"
        assert "dữ liệu nhạy cảm" in rejected.json()["message"]


def test_login_response_uses_link_boolean_not_raw_telegram_identity(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_link(client)
        assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 200
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": "correct-horse-battery-staple"},
        )
        assert login.status_code == 200
        account = login.json()["data"]["account"]
        assert account["telegram_linked"] is True
        assert "canonical_user_id" not in account
        assert "telegram-123" not in login.text


def test_payment_entry_options_are_linked_session_only_and_do_not_expose_manual_bank_data(tmp_path, monkeypatch):
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("MANUAL_BANK_ACCOUNT", "private-bank-account-must-not-leak")
    monkeypatch.setenv("WEBAPP_PAYMENT_ENABLED", "false")
    with make_client(tmp_path, monkeypatch) as client:
        denied = client.get("/api/v1/payments/options")
        assert denied.status_code == 401

        registration = client.post(
            "/api/v1/auth/register",
            json={"email": "payment-options@example.com", "password": "correct-horse-battery-staple"},
        )
        assert registration.json()["ok"] is True
        login = client.post("/api/v1/auth/login", json={"email": "payment-options@example.com", "password": "correct-horse-battery-staple"})
        csrf = login.json()["data"]["csrf_token"]
        unlinked = client.get("/api/v1/payments/options")
        assert unlinked.status_code == 409

        code = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf}).json()["data"]["code"]
        assert confirm_link(client, code).json()["ok"] is True
        assert complete_link(client, csrf).json()["ok"] is True
        options = client.get("/api/v1/payments/options")
        assert options.status_code == 200
        payload = options.json()
        assert payload["status"] == "read_only"
        assert payload["data"]["payos"]["request_enabled"] is False
        assert payload["data"]["payos"]["topup_catalog_available"] is False
        assert payload["data"]["payos"]["topup_packages"] == []
        assert payload["data"]["payos"]["telegram_url"] == "https://t.me/ToanAasSupportBot"
        assert payload["data"]["payos"]["command"] == "/naptien"
        assert payload["data"]["manual"] == {
            "available": True,
            "telegram_url": "https://t.me/ToanAasSupportBot",
            "command": "/thucong",
            "receipt_channel": "telegram_bot",
            "payment_lookup_available": False,
            "wallet_history_signal_available": True,
            "history_in_web": False,
            "history_channel": "telegram_bot",
            "history_command": "/thucong",
            "history_menu_label": "Lịch sử nạp thủ công",
        }
        assert "private-bank-account-must-not-leak" not in options.text

        # An enabled Web-payment flag and configured bridge are not enough:
        # until the dedicated top-up SKU catalog exists, the browser must keep
        # the request path guarded and hand the customer back to the Bot.
        monkeypatch.setenv("WEBAPP_PAYMENT_ENABLED", "true")
        monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "http://bridge.test")
        monkeypatch.setenv("CORE_BRIDGE_TOKEN", "test-token")
        monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "test-hmac")
        blocked_catalog = client.get("/api/v1/payments/options").json()["data"]["payos"]
        assert blocked_catalog["request_enabled"] is False
        assert blocked_catalog["status"] == "guarded"

        monkeypatch.setenv("BOT_USERNAME", "not/a-valid-telegram-username")
        invalid_name = client.get("/api/v1/payments/options").json()["data"]["manual"]
        assert invalid_name["available"] is False
        assert invalid_name["telegram_url"] == ""
        invalid_deep_link = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf})
        assert invalid_deep_link.status_code == 200
        # A linked account cannot mint another code just to probe a deep link:
        # canonical Telegram identity is intentionally non-replaceable here.
        assert invalid_deep_link.json()["error_code"] == "TELEGRAM_RELINK_NOT_ALLOWED"


def test_legacy_billing_router_is_not_mounted_as_a_second_payos_or_wallet_writer(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        # A mistaken `uvicorn main:app` command must resolve to the same safe
        # signed-session application, not the abandoned billing/webhook app.
        sys.modules.pop("main", None)
        compatibility_main = importlib.import_module("main").app
        assert compatibility_main is client.app
        paths = {getattr(route, "path", "") for route in client.app.routes}
        assert "/api/v1/billing/create-payment-link" not in paths
        assert "/api/v1/billing/webhook/payos" not in paths
        assert "/api/v1/webhook/payos" not in paths
        assert "/payos/create-link" not in paths
        assert "/manual-topup" not in paths
        assert "/admin/manual-orders" not in paths
        assert "/admin/approve-topup" not in paths
        for path in (
            "/api/v1/billing/create-payment-link",
            "/api/v1/billing/webhook/payos",
            "/payos/create-link",
            "/manual-topup",
            "/admin/approve-topup",
        ):
            response = client.post(path, json={})
            assert response.status_code in {404, 405}, path


def test_telegram_link_callback_requires_hmac_timestamp_and_one_time_nonce(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        registration = client.post("/api/v1/auth/register", json={"email": "link@example.com", "password": "correct-horse-battery-staple"})
        assert registration.json()["ok"] is True
        login = client.post("/api/v1/auth/login", json={"email": "link@example.com", "password": "correct-horse-battery-staple"})
        csrf = login.json()["data"]["csrf_token"]
        code = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf}).json()["data"]["code"]
        unsigned = client.post(
            "/api/v1/auth/internal/telegram-link/confirm",
            headers={"X-TOAN-AAS-BRIDGE-TOKEN": "bridge-test-token"},
            json={"code": code, "canonical_user_id": "telegram-123"},
        )
        assert unsigned.status_code == 401
        request_id = "link-callback-replay-0001"
        confirmed = confirm_link(client, code, request_id=request_id)
        assert confirmed.status_code == 200
        replay = confirm_link(client, code, request_id=request_id)
        assert replay.status_code == 401
        assert replay.json()["error_code"] == "REQUEST_DENIED"


def test_telegram_identity_callback_never_falls_back_to_core_bridge_credentials(tmp_path, monkeypatch):
    """A general core callback credential must not establish Web identity."""
    with make_client(tmp_path, monkeypatch) as client:
        registration = client.post("/api/v1/auth/register", json={"email": "no-fallback@example.com", "password": "correct-horse-battery-staple"})
        assert registration.json()["ok"] is True
        login = client.post("/api/v1/auth/login", json={"email": "no-fallback@example.com", "password": "correct-horse-battery-staple"})
        csrf = login.json()["data"]["csrf_token"]
        code = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf}).json()["data"]["code"]

        # The Web callback endpoint must reject the legacy/general pair even
        # though the test service still has those core variables configured.
        monkeypatch.delenv("WEBAPP_LINK_CALLBACK_TOKEN")
        monkeypatch.delenv("WEBAPP_LINK_CALLBACK_HMAC_SECRET")
        rejected = confirm_link(client, code)
        assert rejected.status_code == 401
        assert rejected.json()["ok"] is False
        assert rejected.json()["error_code"] == "REQUEST_DENIED"


def test_telegram_link_start_rejects_a_raw_browser_identity(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        registered = client.post("/api/v1/auth/register", json={"email": "no-raw-link@example.com", "password": "correct-horse-battery-staple"})
        assert registered.json()["ok"] is True
        login = client.post("/api/v1/auth/login", json={"email": "no-raw-link@example.com", "password": "correct-horse-battery-staple"})
        rejected = client.post(
            "/api/v1/auth/telegram/link/start",
            headers={"X-CSRF-Token": login.json()["data"]["csrf_token"]},
            json={"telegram_id": "browser-forged"},
        )
        assert rejected.status_code == 422
        assert rejected.json()["error_code"] == "TELEGRAM_BROWSER_INPUT_NOT_ACCEPTED"
        assert "browser-forged" not in rejected.text


def test_telegram_callback_accepts_the_explicit_trailing_slash_alias(tmp_path, monkeypatch):
    """A Bot callback URL with one harmless trailing slash must not hit a 307."""
    with make_client(tmp_path, monkeypatch) as client:
        registration = client.post("/api/v1/auth/register", json={"email": "slash-link@example.com", "password": "correct-horse-battery-staple"})
        assert registration.json()["ok"] is True
        login = client.post("/api/v1/auth/login", json={"email": "slash-link@example.com", "password": "correct-horse-battery-staple"})
        csrf = login.json()["data"]["csrf_token"]
        code = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf}).json()["data"]["code"]
        confirmed = confirm_link(client, code, callback_path="/api/v1/auth/internal/telegram-link/confirm/")
        assert confirmed.status_code == 200
        assert confirmed.json()["ok"] is True


def test_telegram_callback_rejects_invalid_codes_and_auto_provisions_a_telegram_first_account(tmp_path, monkeypatch):
    """The Bot treats 2xx as completion, so rejected callbacks must not use it."""
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    with make_client(tmp_path, monkeypatch) as client:
        missing = confirm_link(client, "missing-telegram-link-code")
        assert missing.status_code == 410
        assert missing.json()["error_code"] == "LINK_CODE_INVALID"

        started = client.post("/api/v1/auth/telegram/login/start")
        login_code = started.json()["data"]["code"]
        first_login = confirm_link(client, login_code, canonical_user_id="telegram-without-web-account")
        assert first_login.status_code == 200
        assert first_login.json()["data"] == {"mode": "login"}
        status = client.get("/api/v1/auth/telegram/login/status")
        assert status.json()["data"] == {"ready": True}
        completed = client.post("/api/v1/auth/telegram/login/complete", json={})
        assert completed.status_code == 200
        account = completed.json()["data"]["account"]
        assert account["account_type"] == "telegram"
        assert account["email"] == ""
        assert account["display_name"] == "Người dùng Telegram"
        assert account["telegram_linked"] is True
        assert account["profile"] == {"locale": "vi", "timezone": "Asia/Ho_Chi_Minh", "avatar_style": "gradient"}
        assert account["login_methods"] == {"email": False, "telegram_oidc": False, "telegram": True, "google": False, "github": False, "apple": False}
        assert "canonical_user_id" not in completed.text
        assert "telegram-without-web-account" not in completed.text

        with sqlite3.connect(tmp_path / "copyfast-test.db") as conn:
            persisted = conn.execute(
                "SELECT email, display_name, password_login_enabled FROM web_accounts WHERE canonical_user_id=?",
                ("telegram-without-web-account",),
            ).fetchone()
        assert persisted is not None
        assert persisted[0].startswith("telegram-")
        assert persisted[0].endswith("@telegram.toanaas.invalid")
        assert "telegram-without-web-account" not in persisted[0]
        assert persisted[1] == "Người dùng Telegram"
        assert persisted[2] == 0
        # The internal placeholder cannot be used as a customer email/password
        # login path even if it is discovered from server-only storage.
        denied = client.post("/api/v1/auth/login", json={"email": persisted[0], "password": "not-a-real-password"})
        # Password authentication deliberately uses a generic HTTP 200
        # envelope to avoid account enumeration, but the session is denied.
        assert denied.status_code == 200
        assert denied.json()["ok"] is False
        assert denied.json()["error_code"] == "LOGIN_DENIED"


def test_telegram_auto_provisioning_can_be_disabled_without_turning_a_rejection_into_success(tmp_path, monkeypatch):
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("WEBAPP_TELEGRAM_AUTO_REGISTER_ENABLED", "false")
    with make_client(tmp_path, monkeypatch) as client:
        started = client.post("/api/v1/auth/telegram/login/start")
        login_code = started.json()["data"]["code"]
        no_account = confirm_link(client, login_code, canonical_user_id="telegram-without-web-account")
        assert no_account.status_code == 409
        assert no_account.json()["error_code"] == "TELEGRAM_LOGIN_ACCOUNT_REQUIRED"
        status = client.get("/api/v1/auth/telegram/login/status")
        assert status.json()["status"] == "guarded"
        assert status.json()["error_code"] == "TELEGRAM_LOGIN_ACCOUNT_REQUIRED"
        assert status.json()["data"] == {"ready": False, "restart_required": True}
        completed = client.post("/api/v1/auth/telegram/login/complete", json={})
        assert completed.json()["error_code"] == "TELEGRAM_LOGIN_ACCOUNT_REQUIRED"


def test_telegram_first_account_can_add_email_password_without_relinking_identity(tmp_path, monkeypatch):
    """Telegram-first customers must not need to create a second Web account."""
    with make_client(tmp_path, monkeypatch) as client:
        started = client.post("/api/v1/auth/telegram/login/start", json={})
        code = started.json()["data"]["code"]
        assert confirm_link(client, code, canonical_user_id="telegram-upgrade-user").status_code == 200
        completed = client.post("/api/v1/auth/telegram/login/complete", json={})
        assert completed.status_code == 200
        assert completed.json()["data"]["account"]["account_type"] == "telegram"
        csrf = completed.json()["data"]["csrf_token"]

        with TestClient(client.app) as second_browser:
            second_started = second_browser.post("/api/v1/auth/telegram/login/start", json={})
            second_code = second_started.json()["data"]["code"]
            assert confirm_link(second_browser, second_code, canonical_user_id="telegram-upgrade-user").status_code == 200
            second_completed = second_browser.post("/api/v1/auth/telegram/login/complete", json={})
            assert second_completed.status_code == 200

            upgraded = client.post(
                "/api/v1/auth/telegram-account/upgrade",
                headers={"X-CSRF-Token": csrf},
                json={"email": "telegram-upgrade@example.com", "password": "correct-horse-battery-staple"},
            )
            assert upgraded.status_code == 200
            assert upgraded.json()["ok"] is True
            account = upgraded.json()["data"]["account"]
            assert account["email"] == "telegram-upgrade@example.com"
            assert account["telegram_linked"] is True
            assert account["login_methods"]["email"] is True
            assert account["login_methods"]["telegram"] is True
            fresh_csrf = upgraded.json()["data"]["csrf_token"]
            assert upgraded.json()["data"]["expires_at"]
            assert client.get("/api/v1/auth/me").json()["data"]["csrf_token"] == fresh_csrf
            assert fresh_csrf != csrf
            assert second_browser.get("/api/v1/auth/me").status_code == 401

        assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": fresh_csrf}).status_code == 200
        password_login = client.post(
            "/api/v1/auth/login",
            json={"email": "telegram-upgrade@example.com", "password": "correct-horse-battery-staple"},
        )
        assert password_login.status_code == 200
        assert password_login.json()["ok"] is True
        assert password_login.json()["data"]["account"]["telegram_linked"] is True


def test_telegram_start_is_configuration_gated_and_never_reuses_core_callback_credentials(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        monkeypatch.delenv("BOT_USERNAME")
        no_bot_name = client.get("/api/v1/auth/telegram/connection/status")
        assert no_bot_name.status_code == 200
        assert no_bot_name.json()["status"] == "guarded"
        assert no_bot_name.json()["data"]["missing_configuration"] == ["BOT_USERNAME"]
        assert no_bot_name.json()["data"]["bot_chat_url"] == ""
        blocked = client.post("/api/v1/auth/telegram/login/start")
        assert blocked.status_code == 200
        assert blocked.json()["error_code"] == "TELEGRAM_LINK_CONFIGURATION_REQUIRED"
        assert "code" not in blocked.json()["data"]

        monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
        ready = client.get("/api/v1/auth/telegram/connection/status")
        assert ready.json()["ok"] is True
        assert ready.json()["data"]["bot_deep_link_ready"] is True
        assert ready.json()["data"]["web_callback_ready"] is True
        assert ready.json()["data"]["oidc_web_login_enabled"] is False
        assert ready.json()["data"]["bot_username"] == "ToanAasSupportBot"
        assert ready.json()["data"]["bot_chat_url"] == "https://t.me/ToanAasSupportBot"
        assert ready.json()["data"]["bot_callback_observed"] is False
        assert ready.json()["data"]["bot_callback_configuration_unverified"] is True

        # CORE_BRIDGE_CALLBACK_* remains configured by make_client, but it is
        # not a permitted identity-callback fallback.
        monkeypatch.delenv("WEBAPP_LINK_CALLBACK_TOKEN")
        monkeypatch.delenv("WEBAPP_LINK_CALLBACK_HMAC_SECRET")
        dedicated_missing = client.get("/api/v1/auth/telegram/connection/status")
        assert dedicated_missing.json()["status"] == "guarded"
        assert dedicated_missing.json()["data"]["web_callback_ready"] is False
        assert dedicated_missing.json()["data"]["missing_configuration"] == ["WEBAPP_LINK_CALLBACK_TOKEN", "WEBAPP_LINK_CALLBACK_HMAC_SECRET"]
        assert "bridge-test-token" not in dedicated_missing.text
        assert client.post("/api/v1/auth/telegram/login/start").json()["error_code"] == "TELEGRAM_LINK_CONFIGURATION_REQUIRED"


def test_telegram_start_requires_explicit_paired_bot_adapter_release_gate(tmp_path, monkeypatch):
    """Web credentials alone must not expose a deep link the Bot cannot consume."""
    with make_client(tmp_path, monkeypatch) as client:
        monkeypatch.setenv("WEBAPP_TELEGRAM_BOT_LINK_ENABLED", "false")
        status_payload = client.get("/api/v1/auth/telegram/connection/status").json()
        assert status_payload["status"] == "guarded"
        assert status_payload["data"]["bot_deep_link_ready"] is True
        assert status_payload["data"]["web_callback_ready"] is True
        assert status_payload["data"]["bot_callback_adapter_enabled"] is False
        assert status_payload["data"]["missing_configuration"] == ["WEBAPP_TELEGRAM_BOT_LINK_ENABLED"]
        blocked = client.post("/api/v1/auth/telegram/login/start", json={}).json()
        assert blocked["error_code"] == "TELEGRAM_LINK_CONFIGURATION_REQUIRED"
        assert blocked["data"]["reason"] == "bot_adapter_not_enabled"
        assert "code" not in blocked["data"]

        monkeypatch.setenv("WEBAPP_TELEGRAM_BOT_LINK_ENABLED", "true")
        enabled = client.get("/api/v1/auth/telegram/connection/status").json()
        assert enabled["status"] == "completed"
        assert enabled["data"]["ready"] is True
        assert enabled["data"]["bot_callback_adapter_enabled"] is True


def test_telegram_release_gate_also_rejects_an_inflight_signed_callback_without_consuming_code(tmp_path, monkeypatch):
    """Turning the gate off must stop old codes as well as new code issuance."""
    with make_client(tmp_path, monkeypatch) as client:
        client.post("/api/v1/auth/register", json={"email": "release-gate@example.com", "password": "correct-horse-battery-staple"})
        login = client.post("/api/v1/auth/login", json={"email": "release-gate@example.com", "password": "correct-horse-battery-staple"})
        csrf = login.json()["data"]["csrf_token"]
        started = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf})
        code = started.json()["data"]["code"]

        monkeypatch.setenv("WEBAPP_TELEGRAM_BOT_LINK_ENABLED", "false")
        paused = confirm_link(client, code, request_id="link-release-gate-paused")
        assert paused.status_code == 503
        assert paused.json()["error_code"] == "TELEGRAM_LINK_ADAPTER_DISABLED"
        paused_status = client.get("/api/v1/auth/telegram/link/status").json()["data"]
        assert paused_status["linked"] is False
        assert paused_status["pending"] is True

        # The paused callback did not consume the one-time code. Once the
        # operator restores the release gate, the same user can complete it
        # only through a fresh signed callback with a distinct replay nonce.
        monkeypatch.setenv("WEBAPP_TELEGRAM_BOT_LINK_ENABLED", "true")
        resumed = confirm_link(client, code, request_id="link-release-gate-resumed")
        assert resumed.status_code == 200
        assert resumed.json()["ok"] is True
        assert complete_link(client, csrf).json()["ok"] is True


def test_telegram_connection_status_only_marks_bot_verified_after_signed_callback(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        before = client.get("/api/v1/auth/telegram/connection/status").json()["data"]
        assert before["bot_callback_observed"] is False
        assert before["last_valid_callback_at"] == ""
        assert before["last_valid_callback_kind"] == ""

        register_and_link(client)

        after = client.get("/api/v1/auth/telegram/connection/status").json()["data"]
        assert after["bot_callback_observed"] is True
        assert after["bot_callback_configuration_unverified"] is False
        assert after["last_valid_callback_kind"] == "account_link"
        assert after["last_valid_callback_at"]


def test_telegram_connection_status_exposes_only_the_safe_oidc_feature_flag(tmp_path, monkeypatch):
    enable_oauth_provider(monkeypatch, "telegram")
    with make_client(tmp_path, monkeypatch) as client:
        status_payload = client.get("/api/v1/auth/telegram/connection/status").json()
        assert status_payload["data"]["oidc_web_login_enabled"] is True
        assert "telegram-client-id" not in json.dumps(status_payload)
        assert "telegram-client-secret" not in json.dumps(status_payload)


def test_bot_companion_routes_need_a_signed_session_but_telegram_link_is_optional(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        anonymous = client.get("/notes", follow_redirects=False)
        assert anonymous.status_code == 307
        assert anonymous.headers["location"].endswith("/login?next=/notes")

        client.post("/api/v1/auth/register", json={"email": "companion@example.com", "password": "correct-horse-battery-staple"})
        login = client.post("/api/v1/auth/login", json={"email": "companion@example.com", "password": "correct-horse-battery-staple"})
        assert login.status_code == 200
        unlinked = client.get("/notes", follow_redirects=False)
        assert unlinked.status_code == 200
        assert '"path": "/notes"' in unlinked.text

        client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": login.json()["data"]["csrf_token"]})
        csrf = register_and_link(client)
        assert csrf
        linked = client.get("/notes")
        assert linked.status_code == 200
        assert '"path": "/notes"' in linked.text


def test_telegram_passwordless_login_is_browser_bound_and_never_accepts_a_raw_id(tmp_path, monkeypatch):
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_link(client)
        profile_update = client.post(
            "/api/v1/auth/profile",
            headers={"X-CSRF-Token": csrf},
            json={"display_name": "Telegram profile", "locale": "en", "timezone": "UTC"},
        )
        assert profile_update.json()["ok"] is True
        assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 200
        assert client.get("/api/v1/auth/me").status_code == 401

        rejected_raw_id = client.post("/api/v1/auth/telegram/login/start", json={"telegram_id": "browser-forged"})
        assert rejected_raw_id.status_code == 422
        assert rejected_raw_id.json()["error_code"] == "TELEGRAM_BROWSER_INPUT_NOT_ACCEPTED"
        assert "browser-forged" not in rejected_raw_id.text

        started = client.post("/api/v1/auth/telegram/login/start", json={})
        assert started.status_code == 200
        payload = started.json()
        assert payload["status"] == "awaiting_confirm"
        assert payload["data"]["raw_telegram_id_accepted"] is False
        assert payload["data"]["deep_link"].startswith("https://t.me/ToanAasSupportBot?start=web_")
        code = payload["data"]["code"]

        with TestClient(client.app) as other_client:
            other_status = other_client.get("/api/v1/auth/telegram/login/status")
            assert other_status.json()["error_code"] == "TELEGRAM_LOGIN_CHALLENGE_REQUIRED"
            assert confirm_link(client, code).json()["data"] == {"mode": "login"}
            assert other_client.post("/api/v1/auth/telegram/login/complete", json={}).json()["error_code"] == "TELEGRAM_LOGIN_CHALLENGE_REQUIRED"

        status = client.get("/api/v1/auth/telegram/login/status")
        assert status.json()["data"] == {"ready": True}
        completed = client.post("/api/v1/auth/telegram/login/complete", json={})
        assert completed.status_code == 200
        account = completed.json()["data"]["account"]
        assert account["telegram_linked"] is True
        assert "canonical_user_id" not in completed.text
        assert account["profile"] == {"locale": "en", "timezone": "UTC", "avatar_style": "gradient"}
        assert account["login_methods"] == {"email": True, "telegram_oidc": False, "telegram": True, "google": False, "github": False, "apple": False}
        assert client.get("/api/v1/auth/me").status_code == 200
        replay = client.post("/api/v1/auth/telegram/login/complete", json={})
        assert replay.json()["error_code"] == "TELEGRAM_LOGIN_CHALLENGE_REQUIRED"


def test_upload_rejects_path_traversal_and_never_falls_back_to_web_storage(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_link(client)
        headers = {"X-CSRF-Token": csrf, "Idempotency-Key": "upload-traversal-0001"}
        traversal = client.post(
            "/api/v1/uploads",
            headers=headers,
            files={"file": ("../unsafe.pdf", b"%PDF-1.4\nunsafe", "application/pdf")},
        )
        assert traversal.status_code == 422
        assert traversal.json()["error_code"] == "REQUEST_INVALID"

        guarded = client.post(
            "/api/v1/uploads",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "upload-guarded-0001"},
            files={"file": ("safe.pdf", b"%PDF-1.4\nsafe", "application/pdf")},
        )
        assert guarded.status_code == 200
        assert guarded.json()["status"] == "guarded"
        assert guarded.json()["error_code"] == "CORE_BRIDGE_NOT_CONFIGURED"


def test_upload_rejects_mime_spoofed_media_and_non_docx_zip_before_bridge(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_link(client)
        headers = {"X-CSRF-Token": csrf, "Idempotency-Key": "upload-media-spoof-0001"}
        fake_video = client.post(
            "/api/v1/uploads",
            headers=headers,
            files={"file": ("clip.mp4", b"not-a-video-container", "video/mp4")},
        )
        assert fake_video.status_code == 422
        assert fake_video.json()["error_code"] == "REQUEST_INVALID"

        mime_mismatch = client.post(
            "/api/v1/uploads",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "upload-mime-mismatch-0001"},
            files={"file": ("image.png", b"\x89PNG\r\n\x1a\nvalid", "application/pdf")},
        )
        assert mime_mismatch.status_code == 415
        assert mime_mismatch.json()["error_code"] == "REQUEST_INVALID"

        raw_zip = client.post(
            "/api/v1/uploads",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "upload-docx-zip-guard-0001"},
            files={"file": ("report.docx", b"PK\x03\x04not-a-docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert raw_zip.status_code == 422
        assert raw_zip.json()["error_code"] == "REQUEST_INVALID"

        docx_buffer = BytesIO()
        with ZipFile(docx_buffer, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types/>")
            archive.writestr("word/document.xml", "<w:document/>")
        valid_docx = client.post(
            "/api/v1/uploads",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "upload-docx-valid-0001"},
            files={"file": ("report.docx", docx_buffer.getvalue(), "application/octet-stream")},
        )
        assert valid_docx.status_code == 200
        assert valid_docx.json()["error_code"] == "CORE_BRIDGE_NOT_CONFIGURED"


def test_copyfast_flag_blocks_feature_and_upload_requests_before_bridge_work(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "false")
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_link(client)
        feature = client.post(
            "/api/v1/features/image_create/draft",
            headers={"X-CSRF-Token": csrf},
            json={"input": {"prompt": "an image"}},
        )
        assert feature.status_code == 200
        assert feature.json()["status"] == "guarded"
        assert feature.json()["error_code"] == "WEBAPP_COPYFAST_DISABLED"

        upload = client.post(
            "/api/v1/uploads",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "flag-upload-0001"},
            files={"file": ("ignored.invalid", b"not-read", "application/octet-stream")},
        )
        assert upload.status_code == 200
        assert upload.json()["status"] == "guarded"
        assert upload.json()["error_code"] == "WEBAPP_COPYFAST_DISABLED"


def test_catalog_and_portal_routes_are_available(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        catalog = client.get("/api/v1/catalog")
        assert catalog.status_code == 200
        keys = {item["key"] for item in catalog.json()["data"]["features"]}
        assert {
            "video_multiscene", "voice_tts", "subtitle_asr", "admin_jobs",
            "caption", "image_remove_background", "music_song", "documents_ocr", "feature_catalog",
            "membership", "service_status", "tool_directory", "media_studio", "growth_ai", "campaign_report",
        }.issubset(keys)
        register_and_link(client)
        page = client.get("/video/multiscene")
        assert page.status_code == 200
        assert "TOAN AAS" in page.text
        feature_catalog = client.get("/features")
        assert feature_catalog.status_code == 200
        assert "Tất cả công cụ" in feature_catalog.text
        for hub_path, hub_title in {
            "/membership": "Gói thành viên",
            "/status": "Trạng thái dịch vụ",
            "/tools": "Công cụ &amp; models",
            "/studio": "Media Studio",
            "/growth/ai": "Growth Review",
            "/campaign/report": "Báo cáo campaign",
        }.items():
            hub = client.get(hub_path)
            assert hub.status_code == 200
            assert hub_title in hub.text
        for family_path, family_title in {
            "/features/content": "Content & Chat",
            "/features/image": "Image Studio",
            "/features/video": "Video Studio",
            "/features/voice": "Voice Studio",
            "/features/music": "Music & SFX",
            "/features/subtitle": "Phụ đề & ngôn ngữ",
            "/features/documents": "Documents & PDF",
        }.items():
            family = client.get(family_path)
            assert family.status_code == 200
            assert family_title in family.text
        legacy_sfx_library = client.get("/music/library?type=sfx", follow_redirects=False)
        assert legacy_sfx_library.status_code == 307
        assert legacy_sfx_library.headers["location"] == "/music/sfx-library"
        sfx_library = client.get("/music/sfx-library")
        assert sfx_library.status_code == 200
        assert "Thư viện SFX" in sfx_library.text
        compatibility = client.get("/features/image")
        assert compatibility.status_code == 200
        legacy = client.get("/campaign-app", follow_redirects=False)
        assert legacy.status_code == 307
        assert legacy.headers["location"] == "/campaigns"
        for legacy_path, target in {
            "/login.html": "/login",
            "/auth.html": "/login",
            "/wallet.html": "/wallet",
            "/admin.html": "/admin",
            "/customer_app.html": "/dashboard",
        }.items():
            redirected = client.get(legacy_path, follow_redirects=False)
            assert redirected.status_code == 307
            assert redirected.headers["location"] == target


def test_customer_portal_keeps_web_workspace_independent_from_telegram_link_state(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        unauthenticated = client.get("/dashboard", follow_redirects=False)
        assert unauthenticated.status_code == 307
        assert unauthenticated.headers["location"] == "/login?next=/dashboard"
        assert client.get("/legal").status_code == 200

        registration = client.post("/api/v1/auth/register", json={"email": "redirect@example.com", "password": "correct-horse-battery-staple"})
        assert registration.json()["ok"] is True
        login = client.post("/api/v1/auth/login", json={"email": "redirect@example.com", "password": "correct-horse-battery-staple"})
        csrf = login.json()["data"]["csrf_token"]
        unlinked_dashboard = client.get("/dashboard", follow_redirects=False)
        assert unlinked_dashboard.status_code == 200
        assert '"path": "/dashboard"' in unlinked_dashboard.text
        unlinked_workflow = client.get("/video/product", follow_redirects=False)
        assert unlinked_workflow.status_code == 200
        assert '"path": "/video/product"' in unlinked_workflow.text
        assert client.get("/account").status_code == 200
        signed_login = client.get("/login", follow_redirects=False)
        assert signed_login.headers["location"] == "/dashboard"

        code = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf}).json()["data"]["code"]
        assert confirm_link(client, code).json()["ok"] is True
        assert complete_link(client, csrf).json()["ok"] is True
        linked_onboarding = client.get("/onboarding", follow_redirects=False)
        assert linked_onboarding.status_code == 307
        assert linked_onboarding.headers["location"] == "/dashboard"
        resumed_workflow = client.get("/onboarding?next=/video/product", follow_redirects=False)
        assert resumed_workflow.status_code == 307
        assert resumed_workflow.headers["location"] == "/video/product"
        unsafe_next = client.get("/onboarding?next=https://attacker.invalid", follow_redirects=False)
        assert unsafe_next.status_code == 307
        assert unsafe_next.headers["location"] == "/dashboard"


def test_app_root_redirects_to_secure_access_and_welcome_is_explicit(tmp_path, monkeypatch):
    """The application origin must never present a marketing shell as home."""
    with make_client(tmp_path, monkeypatch) as client:
        root = client.get("/", follow_redirects=False)
        app_alias = client.get("/app", follow_redirects=False)
        assert root.status_code == app_alias.status_code == 307
        assert root.headers["location"] == app_alias.headers["location"] == "/login"

        welcome = client.get("/welcome", follow_redirects=False)
        assert welcome.status_code == 200
        assert 'id="portal-bootstrap" type="application/json"' in welcome.text
        assert '"path": "/welcome"' in welcome.text

        registration = client.post(
            "/api/v1/auth/register",
            json={"email": "landing@example.com", "password": "correct-horse-battery-staple"},
        )
        assert registration.json()["ok"] is True
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "landing@example.com", "password": "correct-horse-battery-staple"},
        )
        assert login.json()["ok"] is True
        unlinked_home = client.get("/", follow_redirects=False)
        assert unlinked_home.status_code == 307
        assert unlinked_home.headers["location"] == "/dashboard"
        assert client.get("/app", follow_redirects=False).headers["location"] == "/dashboard"

        csrf = login.json()["data"]["csrf_token"]
        code = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf}).json()["data"]["code"]
        assert confirm_link(client, code).json()["ok"] is True
        assert complete_link(client, csrf).json()["ok"] is True
        linked_home = client.get("/", follow_redirects=False)
        assert linked_home.status_code == 307
        assert linked_home.headers["location"] == "/dashboard"
        assert client.get("/app", follow_redirects=False).headers["location"] == "/dashboard"


def test_portal_documents_and_auth_redirects_are_never_http_cached(tmp_path, monkeypatch):
    """A stale portal shell must not survive logout or an expired session."""
    with make_client(tmp_path, monkeypatch) as client:
        public_portal = client.get("/welcome", follow_redirects=False)
        signed_out_redirect = client.get("/dashboard", follow_redirects=False)
        assert public_portal.status_code == 200
        assert signed_out_redirect.status_code == 307
        assert public_portal.headers["cache-control"] == "no-store, private"
        assert signed_out_redirect.headers["cache-control"] == "no-store, private"

        registered = client.post(
            "/api/v1/auth/register",
            json={"email": "cache-boundary@example.com", "password": "correct-horse-battery-staple"},
        )
        assert registered.status_code == 200
        signed_in = client.post(
            "/api/v1/auth/login",
            json={"email": "cache-boundary@example.com", "password": "correct-horse-battery-staple"},
        )
        assert signed_in.status_code == 200
        signed_in_dashboard = client.get("/dashboard", follow_redirects=False)
        assert signed_in_dashboard.status_code == 200
        assert signed_in_dashboard.headers["cache-control"] == "no-store, private"


def test_admin_portal_requires_signed_session_and_current_canonical_role(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        for path in ("/admin", "/admin/finance/tax-readiness"):
            unauthenticated = client.get(path, follow_redirects=False)
            assert unauthenticated.status_code == 401
            assert unauthenticated.json()["error_code"] == "REQUEST_DENIED"

        # A callback may populate the display cache, but the HTML page itself
        # refuses access when the bot core cannot currently prove admin role.
        register_and_link(client, role="admin")
        for path in ("/admin/users", "/admin/finance/tax-readiness"):
            stale_cached_role = client.get(path, follow_redirects=False)
            assert stale_cached_role.status_code == 403
            assert stale_cached_role.json()["error_code"] == "REQUEST_DENIED"

        # The static Tax Readiness shell is still a canonical-admin route.
        # Proving this gate must not require a finance-data bridge request.
        application_module = sys.modules["app"]
        canonical_checks: list[str] = []

        async def canonical_ok(_request):
            canonical_checks.append("checked")
            return {"id": "canonical-admin", "role": "admin", "canonical_user_id": "canonical-admin"}

        monkeypatch.setattr(application_module, "require_canonical_admin", canonical_ok)
        allowed = client.get("/admin/finance/tax-readiness", follow_redirects=False)
        assert allowed.status_code == 200
        assert canonical_checks == ["checked"]


def test_web_local_admin_crm_page_is_signed_role_only_and_never_queries_bot_bridge(tmp_path, monkeypatch):
    """The one redacted CRM page is not a hidden canonical-admin route."""
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
    with make_client(tmp_path, monkeypatch) as client:
        registered = client.post(
            "/api/v1/auth/register",
            json={"email": "local-crm-admin@example.com", "password": "correct-horse-battery-staple"},
        )
        assert registered.status_code == 200
        signed_in = client.post(
            "/api/v1/auth/login",
            json={"email": "local-crm-admin@example.com", "password": "correct-horse-battery-staple"},
        )
        assert signed_in.status_code == 200
        # Browser input does not grant this role; the test changes only the
        # server-side account row, matching the route's production authority.
        with sqlite3.connect(tmp_path / "copyfast-test.db") as conn:
            conn.execute("UPDATE web_accounts SET role_cache='admin' WHERE email=?", ("local-crm-admin@example.com",))
            conn.commit()

        application_module = sys.modules["app"]
        bridge_calls: list[str] = []

        async def unexpected_canonical_check(_request):
            bridge_calls.append("called")
            raise AssertionError("The local CRM manager page must not query the Bot bridge")

        monkeypatch.setattr(application_module, "require_canonical_admin", unexpected_canonical_check)
        page = client.get("/admin/crm/leads", follow_redirects=False)
        assert page.status_code == 200
        assert bridge_calls == []

        # A signed customer remains unable to use the exact local-admin page.
        other = TestClient(application_module.app)
        assert other.post(
            "/api/v1/auth/register",
            json={"email": "local-crm-customer@example.com", "password": "correct-horse-battery-staple"},
        ).status_code == 200
        assert other.post(
            "/api/v1/auth/login",
            json={"email": "local-crm-customer@example.com", "password": "correct-horse-battery-staple"},
        ).status_code == 200
        denied = other.get("/admin/crm/leads", follow_redirects=False)
        assert denied.status_code == 403
        assert denied.json()["error_code"] == "REQUEST_DENIED"


def test_web_local_admin_security_access_pages_and_retired_bridge_paths_never_query_bot(tmp_path, monkeypatch):
    """Security posture is Web-owned and rejects historic bridge URLs early."""

    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
    with make_client(tmp_path, monkeypatch) as client:
        registered = client.post(
            "/api/v1/auth/register",
            json={"email": "security-posture-admin@example.com", "password": "correct-horse-battery-staple"},
        )
        assert registered.status_code == 200
        signed_in = client.post(
            "/api/v1/auth/login",
            json={"email": "security-posture-admin@example.com", "password": "correct-horse-battery-staple"},
        )
        assert signed_in.status_code == 200
        with sqlite3.connect(tmp_path / "copyfast-test.db") as conn:
            conn.execute(
                "UPDATE web_accounts SET role_cache='admin' WHERE email=?",
                ("security-posture-admin@example.com",),
            )
            conn.commit()

        application_module = sys.modules["app"]
        bridge_calls: list[str] = []

        async def unexpected_canonical_check(_request):
            bridge_calls.append("called")
            raise AssertionError("Web Security & Access posture must not query the Bot bridge")

        monkeypatch.setattr(application_module, "require_canonical_admin", unexpected_canonical_check)
        for path in ("/admin/security", "/admin/access"):
            page = client.get(path, follow_redirects=False)
            assert page.status_code == 200
        assert bridge_calls == []

        # Fixed retired routes are registered before the generic dynamic
        # module bridge, so they return 404 instead of resolving its
        # canonical-admin/bridge dependency.
        for path in ("/api/v1/admin/modules/security", "/api/v1/admin/modules/access"):
            retired = client.get(path, follow_redirects=False)
            assert retired.status_code == 404
        assert bridge_calls == []


def test_web_support_content_handoff_queue_uses_its_own_server_role_not_bot_admin(tmp_path, monkeypatch):
    """The staff queue advertised by Admin ERP must not require Bot authority.

    Content Handoff is a Web-owned internal review ledger.  Its queue API
    already uses ``require_support_staff``; the protected Portal document must
    use the same narrow authority so a support operator can open the route
    without accidentally invoking the canonical Bot-admin bridge.
    """
    with make_client(tmp_path, monkeypatch) as client:
        registered = client.post(
            "/api/v1/auth/register",
            json={"email": "handoff-support-operator@example.com", "password": "correct-horse-battery-staple"},
        )
        assert registered.status_code == 200
        signed_in = client.post(
            "/api/v1/auth/login",
            json={"email": "handoff-support-operator@example.com", "password": "correct-horse-battery-staple"},
        )
        assert signed_in.status_code == 200

        denied = client.get("/admin/content-handoffs", follow_redirects=False)
        assert denied.status_code == 403
        assert denied.json()["error_code"] == "REQUEST_DENIED"

        # The role is changed only in the server-side account store.  Nothing
        # supplied by this browser request grants the staff authority.
        with sqlite3.connect(tmp_path / "copyfast-test.db") as conn:
            conn.execute(
                "UPDATE web_accounts SET role_cache='support_operator' WHERE email=?",
                ("handoff-support-operator@example.com",),
            )
            conn.commit()

        application_module = sys.modules["app"]
        bridge_calls: list[str] = []

        async def unexpected_canonical_check(_request):
            bridge_calls.append("called")
            raise AssertionError("Web Support Content Handoff queue must not query the Bot admin bridge")

        monkeypatch.setattr(application_module, "require_canonical_admin", unexpected_canonical_check)
        queue = client.get("/admin/content-handoffs", follow_redirects=False)
        assert queue.status_code == 200
        assert bridge_calls == []


def test_every_admin_api_rechecks_canonical_role_for_reads_and_writes(tmp_path, monkeypatch):
    """A stale role cache must never unlock JSON Admin ERP endpoints.

    The test bridge is intentionally unconfigured even with the Web write
    flag on, so a callback that only claims ``role=admin`` proves neither the
    reads nor the CSRF-protected mutations can reach their bridge action
    without live canonical confirmation.
    """
    monkeypatch.setenv("WEBAPP_ADMIN_WRITES_ENABLED", "true")
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_link(client, role="admin")
        api_module = sys.modules["copyfast_api"]
        mutation_calls = []

        async def unexpected_mutation(*args, **kwargs):
            mutation_calls.append((args, kwargs))
            return {"ok": True, "status": "completed", "message": "unexpected", "data": {}, "error_code": None}

        monkeypatch.setattr(api_module, "_bridge", unexpected_mutation)
        for path in (
            "/api/v1/admin/summary",
            "/api/v1/admin/users",
            "/api/v1/admin/jobs",
            "/api/v1/admin/payments",
            "/api/v1/admin/providers",
            "/api/v1/admin/tickets",
        ):
            response = client.get(path)
            assert response.status_code == 403, path
            assert response.json()["error_code"] == "REQUEST_DENIED"

        writes = (
            ("/api/v1/admin/jobs/job-1/retry", {"input": {}, "idempotency_key": "admin-retry-0001"}),
            ("/api/v1/admin/jobs/job-1/refund", {"input": {}, "idempotency_key": "admin-refund-0001"}),
            ("/api/v1/admin/features/video_single/freeze", {"frozen": True, "note": "Test canonical role", "idempotency_key": "admin-freeze-0001"}),
        )
        for path, payload in writes:
            response = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload)
            assert response.status_code == 403, path
            assert response.json()["error_code"] == "REQUEST_DENIED"
        assert mutation_calls == []


def test_admin_freeze_requires_a_meaningful_server_validated_operation_note(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBAPP_ADMIN_WRITES_ENABLED", "true")
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_link(client, role="admin")
        response = client.post(
            "/api/v1/admin/features/video_single/freeze",
            headers={"X-CSRF-Token": csrf},
            json={"frozen": True, "note": "   ", "idempotency_key": "admin-freeze-note-0001"},
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "REQUEST_INVALID"


def test_portal_template_uses_inert_bootstrap_for_strict_csp(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        register_and_link(client)
        page = client.get("/dashboard")
        assert page.status_code == 200
        assert 'id="portal-bootstrap" type="application/json"' in page.text
        assert "window.__TOAN_AAS_PORTAL__=" not in page.text
        assert "__PORTAL_ASSET_VERSION__" not in page.text
        assert "/static/portal/portal.js?v=" in page.text


def test_api_validation_errors_keep_the_standard_envelope(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        response = client.post("/api/v1/auth/register", json={"email": "not-an-email"})
        assert response.status_code == 422
        assert response.json() == {
            "ok": False,
            "status": "failed",
            "message": "Dữ liệu yêu cầu không hợp lệ",
            "data": {},
            "error_code": "REQUEST_INVALID",
        }


def test_auth_rate_limit_is_server_side_and_separates_login_from_registration(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        for _ in range(8):
            denied = client.post("/api/v1/auth/login", json={"email": "missing@example.com", "password": "not-the-right-password"})
            assert denied.status_code == 200
        login_limited = client.post("/api/v1/auth/login", json={"email": "missing@example.com", "password": "not-the-right-password"})
        assert login_limited.status_code == 429
        assert login_limited.json()["error_code"] == "AUTH_RATE_LIMITED"

        for index in range(4):
            registered = client.post(
                "/api/v1/auth/register",
                json={"email": f"rate-{index}@example.com", "password": "correct-horse-battery-staple"},
            )
            assert registered.status_code == 200
        registration_limited = client.post(
            "/api/v1/auth/register",
            json={"email": "rate-final@example.com", "password": "correct-horse-battery-staple"},
        )
        assert registration_limited.status_code == 429
        assert registration_limited.json()["error_code"] == "AUTH_RATE_LIMITED"


def test_registration_does_not_disclose_that_an_email_already_exists(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        first = client.post(
            "/api/v1/auth/register",
            json={"email": "existing@example.com", "password": "correct-horse-battery-staple"},
        )
        assert first.status_code == 200
        duplicate = client.post(
            "/api/v1/auth/register",
            json={"email": "existing@example.com", "password": "different-correct-horse-battery"},
        )
        assert duplicate.status_code == 200
        # Public wording may evolve with the account-verification flow, but
        # an existing email must remain indistinguishable from a new one.
        assert first.json() == duplicate.json()
        response = first.json()
        assert set(response) == {"ok", "status", "message", "data", "error_code"}
        assert response["ok"] is True
        assert response["status"] == "awaiting_confirm"
        assert response["data"] == {}
        assert response["error_code"] is None
        assert "email" in response["message"].lower()
        assert "set-cookie" not in first.headers
        assert "set-cookie" not in duplicate.headers


def test_telegram_link_revokes_other_sessions_but_keeps_the_initiating_session(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        registration = client.post(
            "/api/v1/auth/register",
            json={"email": "two-sessions@example.com", "password": "correct-horse-battery-staple"},
        )
        assert registration.json()["ok"] is True
        first_login = client.post("/api/v1/auth/login", json={"email": "two-sessions@example.com", "password": "correct-horse-battery-staple"})
        csrf = first_login.json()["data"]["csrf_token"]
        with TestClient(client.app) as other_client:
            second_login = other_client.post(
                "/api/v1/auth/login",
                json={"email": "two-sessions@example.com", "password": "correct-horse-battery-staple"},
            )
            assert second_login.status_code == 200
            assert other_client.get("/api/v1/auth/me").status_code == 200

            code = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf}).json()["data"]["code"]
            assert confirm_link(client, code).json()["ok"] is True
            assert complete_link(client, csrf).json()["ok"] is True
            assert client.get("/api/v1/auth/me").status_code == 200
            revoked = other_client.get("/api/v1/auth/me")
            assert revoked.status_code == 401
            assert revoked.json()["error_code"] == "REQUEST_DENIED"


def test_a_canonical_telegram_identity_cannot_link_two_web_accounts(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        first = client.post(
            "/api/v1/auth/register",
            json={"email": "first-link@example.com", "password": "correct-horse-battery-staple"},
        )
        assert first.json()["ok"] is True
        first_login = client.post("/api/v1/auth/login", json={"email": "first-link@example.com", "password": "correct-horse-battery-staple"})
        first_code = client.post(
            "/api/v1/auth/telegram/link/start",
            headers={"X-CSRF-Token": first_login.json()["data"]["csrf_token"]},
        ).json()["data"]["code"]
        assert confirm_link(client, first_code).json()["ok"] is True

        with TestClient(client.app) as other_client:
            second = other_client.post(
                "/api/v1/auth/register",
                json={"email": "second-link@example.com", "password": "correct-horse-battery-staple"},
            )
            assert second.json()["ok"] is True
            second_login = other_client.post("/api/v1/auth/login", json={"email": "second-link@example.com", "password": "correct-horse-battery-staple"})
            second_code = other_client.post(
                "/api/v1/auth/telegram/link/start",
                headers={"X-CSRF-Token": second_login.json()["data"]["csrf_token"]},
            ).json()["data"]["code"]
            collision = confirm_link(other_client, second_code)
            assert collision.status_code == 409
            assert collision.json()["ok"] is False
            assert collision.json()["error_code"] == "TELEGRAM_ALREADY_LINKED"


def test_linked_account_cannot_issue_or_use_a_code_to_replace_telegram_identity(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_link(client)
        blocked_start = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf})
        assert blocked_start.status_code == 200
        assert blocked_start.json()["error_code"] == "TELEGRAM_RELINK_NOT_ALLOWED"

        import copyfast_auth
        from copyfast_db import transaction

        forged_code = "defensive-relink-code-0001"
        with transaction() as conn:
            account_id = conn.execute("SELECT id FROM web_accounts WHERE email=?", ("user@example.com",)).fetchone()[0]
            conn.execute(
                """INSERT INTO telegram_link_codes (code_hash, account_id, expires_at, initiating_session_id, created_at)
                VALUES (?, ?, ?, ?, ?)""",
                (
                    hashlib.sha256(forged_code.encode("utf-8")).hexdigest(),
                    account_id,
                    copyfast_auth._link_expiry(),
                    "test-defensive-relink-session",
                    copyfast_auth.utc_now(),
                ),
            )
        blocked_callback = confirm_link(client, forged_code, canonical_user_id="telegram-456")
        assert blocked_callback.status_code == 410
        assert blocked_callback.json()["error_code"] == "LINK_SESSION_INVALID"
        me = client.get("/api/v1/auth/me")
        assert "telegram-456" not in me.text


def test_bot_callback_requires_the_initiating_browser_to_complete_the_account_link(tmp_path, monkeypatch):
    """A Bot proof is pending until the same CSRF session explicitly commits it."""
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post("/api/v1/auth/register", json={"email": "two-step-link@example.com", "password": "correct-horse-battery-staple"}).json()["ok"] is True
        login = client.post("/api/v1/auth/login", json={"email": "two-step-link@example.com", "password": "correct-horse-battery-staple"})
        csrf = login.json()["data"]["csrf_token"]
        code = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf}).json()["data"]["code"]

        confirmed = confirm_link(client, code, canonical_user_id="telegram-two-step")
        assert confirmed.status_code == 200
        assert confirmed.json()["status"] == "awaiting_confirm"
        assert confirmed.json()["data"] == {"mode": "link", "browser_confirmation_required": True}
        assert client.get("/api/v1/auth/me").json()["data"]["account"]["telegram_linked"] is False

        pending = client.get("/api/v1/auth/telegram/link/status").json()["data"]
        assert pending["linked"] is False
        assert pending["ready_to_complete"] is True
        assert "code" not in pending
        assert "telegram-two-step" not in json.dumps(pending)

        completed = complete_link(client, csrf)
        assert completed.status_code == 200
        assert completed.json()["data"] == {"linked": True}
        assert client.get("/api/v1/auth/me").json()["data"]["account"]["telegram_linked"] is True


def test_telegram_callback_rejects_a_code_after_its_initiating_session_logs_out(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post("/api/v1/auth/register", json={"email": "logout-link@example.com", "password": "correct-horse-battery-staple"}).json()["ok"] is True
        login = client.post("/api/v1/auth/login", json={"email": "logout-link@example.com", "password": "correct-horse-battery-staple"})
        csrf = login.json()["data"]["csrf_token"]
        code = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf}).json()["data"]["code"]
        assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).json()["ok"] is True

        denied = confirm_link(client, code, canonical_user_id="telegram-after-logout")
        assert denied.status_code == 410
        assert denied.json()["error_code"] == "LINK_SESSION_INVALID"
        with sqlite3.connect(tmp_path / "copyfast-test.db") as conn:
            canonical = conn.execute("SELECT canonical_user_id FROM web_accounts WHERE email=?", ("logout-link@example.com",)).fetchone()[0]
        assert canonical is None


def test_pending_link_status_and_completion_are_bound_to_the_initiating_browser_session(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post("/api/v1/auth/register", json={"email": "session-bound-link@example.com", "password": "correct-horse-battery-staple"}).json()["ok"] is True
        first_login = client.post("/api/v1/auth/login", json={"email": "session-bound-link@example.com", "password": "correct-horse-battery-staple"})
        first_csrf = first_login.json()["data"]["csrf_token"]
        code = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": first_csrf}).json()["data"]["code"]

        with TestClient(client.app) as other_client:
            second_login = other_client.post("/api/v1/auth/login", json={"email": "session-bound-link@example.com", "password": "correct-horse-battery-staple"})
            second_csrf = second_login.json()["data"]["csrf_token"]
            other_status = other_client.get("/api/v1/auth/telegram/link/status").json()["data"]
            assert other_status == {"linked": False}
            denied = complete_link(other_client, second_csrf)
            assert denied.json()["error_code"] == "LINK_CODE_INVALID"

            assert confirm_link(client, code, canonical_user_id="telegram-session-bound").status_code == 200
            first_status = client.get("/api/v1/auth/telegram/link/status").json()["data"]
            assert first_status["ready_to_complete"] is True
            assert other_client.get("/api/v1/auth/telegram/link/status").json()["data"] == {"linked": False}
            assert complete_link(client, first_csrf).json()["ok"] is True
            assert other_client.get("/api/v1/auth/me").status_code == 401


def test_telegram_callback_caps_body_validates_after_hmac_and_binds_audit_to_signed_request_id(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post("/api/v1/auth/register", json={"email": "callback-hardening@example.com", "password": "correct-horse-battery-staple"}).json()["ok"] is True
        login = client.post("/api/v1/auth/login", json={"email": "callback-hardening@example.com", "password": "correct-horse-battery-staple"})
        csrf = login.json()["data"]["csrf_token"]
        code = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf}).json()["data"]["code"]

        oversized = b'{"code":"' + (b"x" * 2_100) + b'"}'
        blocked = client.post(
            "/api/v1/auth/internal/telegram-link/confirm",
            headers=link_callback_headers(oversized, request_id="oversized-callback-0001"),
            content=oversized,
        )
        assert blocked.status_code == 413
        assert blocked.json()["error_code"] == "BRIDGE_CALLBACK_BODY_TOO_LARGE"

        malformed = b"{"
        invalid = client.post(
            "/api/v1/auth/internal/telegram-link/confirm",
            headers=link_callback_headers(malformed, request_id="malformed-callback-0001"),
            content=malformed,
        )
        assert invalid.status_code == 422
        assert invalid.json()["error_code"] == "LINK_CALLBACK_INVALID"
        assert client.get("/api/v1/auth/telegram/link/status").json()["data"]["pending"] is True

        future = confirm_link(
            client,
            code,
            canonical_user_id="telegram-future-clock",
            request_id="future-callback-0001",
            # Leave a deliberate margin beyond the 30-second allowed skew.
            # A slow CI request must not turn this security assertion into a
            # race with the wall clock.
            timestamp=int(time.time()) + 120,
        )
        assert future.status_code == 401
        assert client.get("/api/v1/auth/me").json()["data"]["account"]["telegram_linked"] is False

        authenticated_request_id = "bridge-audit-authenticated-0001"
        accepted = confirm_link(
            client,
            code,
            canonical_user_id="telegram-audit-bound",
            request_id=authenticated_request_id,
            extra_headers={"X-Request-ID": "browser-spoofed-request-id"},
        )
        assert accepted.status_code == 200
        with sqlite3.connect(tmp_path / "copyfast-test.db") as conn:
            audit_request_id = conn.execute(
                """SELECT request_id FROM web_audit_events
                   WHERE action='auth.telegram_link_confirm'
                   ORDER BY rowid DESC LIMIT 1"""
            ).fetchone()[0]
        assert audit_request_id == authenticated_request_id
        assert complete_link(client, csrf).json()["ok"] is True


def test_production_environment_requires_a_real_secret_and_sets_secure_session_cookie(tmp_path, monkeypatch):
    volume = tmp_path / "production-cookie-volume"
    volume.mkdir()
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", str(volume))
    with make_client(tmp_path, monkeypatch, session_database_path=volume / "copyfast-test.db") as client:
        registration = client.post(
            "/api/v1/auth/register",
            json={"email": "production-cookie@example.com", "password": "correct-horse-battery-staple"},
        )
        assert registration.status_code == 200
        assert "set-cookie" not in registration.headers
        login = client.post("/api/v1/auth/login", json={"email": "production-cookie@example.com", "password": "correct-horse-battery-staple"})
        assert "Secure" in login.headers["set-cookie"]
        assert login.headers["cache-control"] == "no-store, private"

    import copyfast_auth

    monkeypatch.delenv("WEB_SESSION_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="WEB_SESSION_SECRET"):
        copyfast_auth.ensure_auth_configuration()


def test_auth_never_falls_back_to_a_source_secret_and_railway_preview_forces_secure_cookies(monkeypatch):
    import copyfast_auth

    for name in (
        "WEB_SESSION_SECRET", "APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT",
        "RAILWAY_ENVIRONMENT_ID", "RAILWAY_PROJECT_ID", "RAILWAY_SERVICE_ID",
        "RAILWAY_DEPLOYMENT_ID", "RAILWAY_PUBLIC_DOMAIN", "WEB_COOKIE_SECURE",
    ):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(RuntimeError, match="WEB_SESSION_SECRET"):
        copyfast_auth.ensure_auth_configuration()

    monkeypatch.setenv("WEB_SESSION_SECRET", "railway-preview-test-session-secret")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "staging")
    monkeypatch.setenv("WEB_COOKIE_SECURE", "false")
    assert copyfast_auth._cookie_secure() is True
    assert copyfast_auth._cookie_name(copyfast_auth.SESSION_COOKIE).startswith("__Host-")


def test_production_requires_persistent_session_database_configuration(tmp_path, monkeypatch):
    import copyfast_db

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("WEBAPP_SESSION_DB_PATH", raising=False)
    monkeypatch.delenv("RAILWAY_VOLUME_MOUNT_PATH", raising=False)
    monkeypatch.setattr(copyfast_db.os.path, "isdir", lambda _value: False)
    with pytest.raises(RuntimeError, match="WEBAPP_SESSION_DB_PATH"):
        copyfast_db.ensure_copyfast_persistence()

    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", "relative.db")
    with pytest.raises(RuntimeError, match="đường dẫn tuyệt đối"):
        copyfast_db.ensure_copyfast_persistence()

    # An arbitrary absolute container path is not evidence of persistence.
    # The file must live under this Web service's verified volume.
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "toanaas-session.db"))
    with pytest.raises(RuntimeError, match="persistent volume"):
        copyfast_db.ensure_copyfast_persistence()


def test_production_accepts_only_an_existing_absolute_railway_volume_mount(tmp_path, monkeypatch):
    import copyfast_db

    mount = tmp_path / "railway-volume"
    mount.mkdir()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("WEBAPP_SESSION_DB_PATH", raising=False)
    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", str(mount))
    monkeypatch.setattr(
        copyfast_db.os.path,
        "isdir",
        lambda value: Path(value).resolve() == mount.resolve(),
    )

    assert copyfast_db.session_database_path() == str(mount / "toanaas_webapp_session.db")
    copyfast_db.ensure_copyfast_persistence()

    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", "relative-volume")
    with pytest.raises(RuntimeError, match="RAILWAY_VOLUME_MOUNT_PATH"):
        copyfast_db.ensure_copyfast_persistence()


def test_production_app_starts_on_an_existing_railway_volume_mount(tmp_path, monkeypatch):
    """Exercise the real lifespan path that otherwise becomes a Railway 502."""
    mount = tmp_path / "railway-web-volume"
    mount.mkdir()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.delenv("WEBAPP_SESSION_DB_PATH", raising=False)
    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", str(mount))
    monkeypatch.setenv("WEB_SESSION_SECRET", "production-test-session-secret")
    for provider in ("TELEGRAM", "GOOGLE", "GITHUB", "APPLE"):
        monkeypatch.delenv(f"WEBAPP_{provider}_OAUTH_ENABLED", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)

    application = importlib.import_module("app").app
    with TestClient(application) as client:
        response = client.get("/api/v1/catalog")
        assert response.status_code == 200
        assert response.json()["ok"] is True
    assert (mount / "toanaas_webapp_session.db").is_file()


def test_credentialed_cors_rejects_wildcards_and_non_https_remote_origins(monkeypatch):
    application = importlib.import_module("app")
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    assert application._origins() == ["https://app.toanaas.vn"]
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "*")
    with pytest.raises(RuntimeError, match="tường minh"):
        application._origins()
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "http://example.invalid")
    with pytest.raises(RuntimeError, match="HTTPS"):
        application._origins()
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "http://localhost:8877,https://app.toanaas.vn")
    assert application._origins() == ["http://localhost:8877", "https://app.toanaas.vn"]


def test_portal_uses_a_single_delegated_listener_after_hydration():
    source = (Path(__file__).parents[1] / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
    assert "let interactionsBound = false;" in source
    assert "if (interactionsBound) return;" in source
    assert "dispatchAction(action, getBootstrap())" in source
    assert "bindInteractions(context)" not in source


def test_web_campaign_planner_is_csrf_owned_idempotent_and_never_calls_canonical_state(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_link(client)
        empty = client.get("/api/v1/campaigns")
        assert empty.status_code == 200
        assert empty.json()["status"] == "read_only"
        assert empty.json()["data"]["items"] == []

        payload = {
            "title": "Video giới thiệu tháng 7",
            "destination_url": "https://example.com/product?ref=toanaas",
            "platform": "tiktok",
            "objective": "affiliate",
            "scheduled_for": "2026-07-20T09:30",
            "idempotency_key": "campaign-create-0001",
        }
        denied = client.post("/api/v1/campaigns", json=payload)
        assert denied.status_code == 403

        created = client.post("/api/v1/campaigns", headers={"X-CSRF-Token": csrf}, json=payload)
        assert created.status_code == 200
        body = created.json()
        assert body["ok"] is True
        assert body["status"] == "draft"
        item = body["data"]["item"]
        assert item["approval_status"] == "draft"
        assert item["scheduled_for"] == "2026-07-20T09:30"
        assert "account_id" not in item
        assert "canonical_user_id" not in created.text
        assert "provider" not in created.text.lower()

        repeated = client.post("/api/v1/campaigns", headers={"X-CSRF-Token": csrf}, json=payload)
        assert repeated.status_code == 200
        assert repeated.json()["data"]["item"]["id"] == item["id"]
        assert len(client.get("/api/v1/campaigns").json()["data"]["items"]) == 1
        detail = client.get(f"/api/v1/campaigns/{item['id']}")
        assert detail.status_code == 200
        assert detail.json()["ok"] is True
        assert detail.json()["status"] == "draft"
        assert detail.json()["data"]["item"]["id"] == item["id"]
        assert detail.json()["data"]["item"]["destination_url"] == payload["destination_url"]
        assert "account_id" not in detail.text
        invalid_detail = client.get("/api/v1/campaigns/not-a-plan-id")
        assert invalid_detail.status_code == 422
        assert invalid_detail.json()["error_code"] == "REQUEST_INVALID"

        edited = client.patch(
            f"/api/v1/campaigns/{item['id']}",
            headers={"X-CSRF-Token": csrf},
            json={
                **payload,
                "title": "Video giới thiệu tháng 7 · đã rà soát",
                "scheduled_for": "2026-07-21T10:15",
                "idempotency_key": "campaign-edit-0001",
            },
        )
        assert edited.status_code == 200
        assert edited.json()["status"] == "draft"
        assert edited.json()["data"]["item"]["title"] == "Video giới thiệu tháng 7 · đã rà soát"
        assert edited.json()["data"]["item"]["scheduled_for"] == "2026-07-21T10:15"
        repeated_edit = client.patch(
            f"/api/v1/campaigns/{item['id']}",
            headers={"X-CSRF-Token": csrf},
            json={
                **payload,
                "title": "Video giới thiệu tháng 7 · đã rà soát",
                "scheduled_for": "2026-07-21T10:15",
                "idempotency_key": "campaign-edit-0001",
            },
        )
        assert repeated_edit.json()["data"]["item"]["id"] == item["id"]

        invalid_url = client.post(
            "/api/v1/campaigns",
            headers={"X-CSRF-Token": csrf},
            json={**payload, "destination_url": "https://user:pass@localhost/private", "idempotency_key": "campaign-create-0002"},
        )
        assert invalid_url.status_code == 422
        assert invalid_url.json()["error_code"] == "REQUEST_INVALID"

        review = client.post(
            f"/api/v1/campaigns/{item['id']}/status",
            headers={"X-CSRF-Token": csrf},
            json={"approval_status": "review", "review_note": "Kiểm tra CTA và quyền dùng asset.", "idempotency_key": "campaign-review-0001"},
        )
        assert review.status_code == 200
        assert review.json()["status"] == "review"
        assert review.json()["data"]["item"]["approval_status"] == "review"

        denied_transition = client.post(
            f"/api/v1/campaigns/{item['id']}/status",
            headers={"X-CSRF-Token": csrf},
            json={"approval_status": "scheduled", "review_note": "", "idempotency_key": "campaign-review-0002"},
        )
        assert denied_transition.status_code == 200
        assert denied_transition.json()["error_code"] == "CAMPAIGN_STATUS_TRANSITION_DENIED"

        approved = client.post(
            f"/api/v1/campaigns/{item['id']}/status",
            headers={"X-CSRF-Token": csrf},
            json={"approval_status": "approved", "review_note": "Đã rà soát nội bộ.", "idempotency_key": "campaign-review-0003"},
        )
        assert approved.json()["status"] == "approved"
        scheduled = client.post(
            f"/api/v1/campaigns/{item['id']}/status",
            headers={"X-CSRF-Token": csrf},
            json={"approval_status": "scheduled", "review_note": "Mốc nội bộ, chưa publish.", "idempotency_key": "campaign-review-0004"},
        )
        assert scheduled.json()["status"] == "scheduled"

        with sqlite3.connect(tmp_path / "copyfast-test.db") as conn:
            audits = conn.execute(
                "SELECT target, detail FROM web_audit_events WHERE action LIKE 'campaign.plan.%' ORDER BY rowid"
            ).fetchall()
        assert audits
        assert all(row[0] == item["id"] for row in audits)
        assert all("example.com" not in row[1] and "Video giới thiệu" not in row[1] for row in audits)


def test_web_campaign_calendar_window_is_month_bounded_redacted_and_owner_scoped(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_link(client)

        def create_plan(key, title, scheduled_for, platform):
            response = client.post(
                "/api/v1/campaigns",
                headers={"X-CSRF-Token": csrf},
                json={
                    "title": title,
                    "destination_url": f"https://example.com/{key}?private=1",
                    "platform": platform,
                    "objective": "traffic",
                    "scheduled_for": scheduled_for,
                    "idempotency_key": key,
                },
            )
            assert response.status_code == 200
            return response.json()["data"]["item"]

        july_tiktok = create_plan("calendar-window-0001", "Lịch TikTok tháng bảy", "2026-07-16T09:30", "tiktok")
        july_facebook = create_plan("calendar-window-0002", "Lịch Facebook tháng bảy", "2026-07-20T14:00", "facebook")
        create_plan("calendar-window-0003", "Lịch tháng tám", "2026-08-01T08:00", "website")

        window = client.get("/api/v1/campaign-calendar/window", params={"month": "2026-07", "status": "all", "platform": "all"})
        assert window.status_code == 200
        assert window.headers["cache-control"] == "no-store, private"
        body = window.json()
        assert body["ok"] is True
        assert body["status"] == "read_only"
        assert body["data"]["month"] == "2026-07"
        assert body["data"]["filters"] == {"status": "all", "platform": "all"}
        assert body["data"]["summary"] == {"total": 2, "returned": 2, "has_more": False, "limit": 200}
        assert [item["id"] for item in body["data"]["items"]] == [july_tiktok["id"], july_facebook["id"]]
        for item in body["data"]["items"]:
            assert set(item) == {"id", "title", "platform", "objective", "scheduled_for", "approval_status", "updated_at"}
            assert item["scheduled_for"].startswith("2026-07-")
            assert "destination_url" not in item
            assert "review_note" not in item
            assert "account_id" not in item
            assert "canonical" not in item

        filtered = client.get("/api/v1/campaign-calendar/window", params={"month": "2026-07", "status": "draft", "platform": "tiktok"})
        assert filtered.status_code == 200
        assert [item["id"] for item in filtered.json()["data"]["items"]] == [july_tiktok["id"]]

        for invalid in (
            {"month": "2026-13", "status": "all", "platform": "all"},
            {"month": "2026-07", "status": "published", "platform": "all"},
            {"month": "2026-07", "status": "all", "platform": "external"},
        ):
            rejected = client.get("/api/v1/campaign-calendar/window", params=invalid)
            assert rejected.status_code == 422
            assert rejected.json()["error_code"] == "REQUEST_INVALID"

        logout = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
        assert logout.status_code == 200
        registration = client.post(
            "/api/v1/auth/register",
            json={"email": "calendar-other@example.com", "password": "correct-horse-battery-staple", "display_name": "Calendar Other"},
        )
        assert registration.json()["ok"] is True
        assert client.post(
            "/api/v1/auth/login",
            json={"email": "calendar-other@example.com", "password": "correct-horse-battery-staple"},
        ).json()["ok"] is True
        other_window = client.get("/api/v1/campaign-calendar/window", params={"month": "2026-07", "status": "all", "platform": "all"})
        assert other_window.status_code == 200
        assert other_window.json()["data"]["items"] == []
        assert other_window.json()["data"]["summary"]["total"] == 0


def test_web_campaign_planner_enforces_account_ownership_without_a_telegram_gate(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as first:
        # A signed Web account owns planning even without a Telegram companion
        # link; API writes still need their own ownership/CSRF checks below.
        registration = first.post(
            "/api/v1/auth/register",
            json={"email": "unlinked-campaign@example.com", "password": "correct-horse-battery-staple"},
        )
        assert registration.json()["ok"] is True
        unlinked_login = first.post("/api/v1/auth/login", json={"email": "unlinked-campaign@example.com", "password": "correct-horse-battery-staple"})
        gate = first.get("/campaigns", follow_redirects=False)
        assert gate.status_code == 200
        assert '"path": "/campaigns"' in gate.text
        for path in ("/calendar", "/approvals"):
            gate = first.get(path, follow_redirects=False)
            assert gate.status_code == 200
            assert f'"path": "{path}"' in gate.text
        independent_plan = first.post(
            "/api/v1/campaigns",
            headers={"X-CSRF-Token": unlinked_login.json()["data"]["csrf_token"]},
            json={
                "title": "Kế hoạch Web độc lập",
                "destination_url": "https://example.com/independent-web",
                "platform": "website",
                "objective": "traffic",
                "scheduled_for": "",
                "idempotency_key": "campaign-unlinked-web-0001",
            },
        )
        assert independent_plan.status_code == 200
        assert independent_plan.json()["ok"] is True
        first.post("/api/v1/auth/logout", headers={"X-CSRF-Token": first.get("/api/v1/auth/me").json()["data"]["csrf_token"]})

        csrf_first = register_and_link(first)
        created = first.post(
            "/api/v1/campaigns",
            headers={"X-CSRF-Token": csrf_first},
            json={
                "title": "Kế hoạch riêng tư",
                "destination_url": "https://example.com/private-plan",
                "platform": "website",
                "objective": "traffic",
                "scheduled_for": "",
                "idempotency_key": "campaign-owner-0001",
            },
        ).json()["data"]["item"]
        assert first.get("/campaigns").status_code == 200
        detail_page = first.get(f"/campaigns/{created['id']}")
        assert detail_page.status_code == 200
        assert "Chi tiết kế hoạch" in detail_page.text
        for path, title in {"/calendar": "Content Calendar", "/approvals": "Self-review Queue"}.items():
            response = first.get(path)
            assert response.status_code == 200
            assert title in response.text

        application = importlib.import_module("app").app
        with TestClient(application) as second:
            registration = second.post(
                "/api/v1/auth/register",
                json={"email": "other-campaign@example.com", "password": "correct-horse-battery-staple"},
            )
            assert registration.json()["ok"] is True
            login = second.post("/api/v1/auth/login", json={"email": "other-campaign@example.com", "password": "correct-horse-battery-staple"})
            csrf_second = login.json()["data"]["csrf_token"]
            link = second.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf_second})
            code = link.json()["data"]["code"]
            assert confirm_link(second, code, canonical_user_id="telegram-campaign-second").json()["ok"] is True
            assert complete_link(second, csrf_second).json()["ok"] is True
            detail_denied = second.get(f"/api/v1/campaigns/{created['id']}")
            assert detail_denied.status_code == 200
            assert detail_denied.json()["ok"] is False
            assert detail_denied.json()["status"] == "guarded"
            assert detail_denied.json()["error_code"] == "CAMPAIGN_PLAN_NOT_FOUND"
            assert "Kế hoạch riêng tư" not in detail_denied.text
            denied = second.post(
                f"/api/v1/campaigns/{created['id']}/status",
                headers={"X-CSRF-Token": csrf_second},
                json={"approval_status": "review", "review_note": "", "idempotency_key": "campaign-owner-0002"},
            )
            assert denied.status_code == 200
            assert denied.json()["error_code"] == "CAMPAIGN_PLAN_NOT_FOUND"
            assert second.get("/api/v1/campaigns").json()["data"]["items"] == []
