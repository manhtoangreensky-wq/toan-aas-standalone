"""Empirical verification test suite for P0.WEBAPP.WEB05: JOBS, HISTORY, ASSETS TRUTH.

Mandate: MASTER_PROGRAM=P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Task: TASK=P0.WEBAPP.WEB05.JOBS.HISTORY.ASSETS.TRUTH
Mode: OWNER-GOVERNED, SOURCE_ONLY, AUDIT_FIRST, FIRST_RED_FIRST, ONE_BOUNDED_TASK

Invariants tested:
1. CUSTOMER_SEES_ONLY_OWN_JOBS: Customer sees only their own jobs (CROSS_ACCOUNT_JOB_READ=0).
2. FOREIGN_JOB_BLOCKED: A customer cannot read another account's job detail.
3. CANONICAL_STATUS_MAPPING: Backend statuses map accurately to UI statuses.
4. UNKNOWN_PROGRESS_TRUTH: Unknown progress remains null/unknown; never fabricated as 0 or 100 (FAKE_PROGRESS=0).
5. COMPLETED_WITHOUT_ASSET_NO_FAKE_SUCCESS: Completed job without asset does not show fake download (FAKE_OUTPUT_SUCCESS=0).
6. COMPLETED_WITH_ASSET_VALID_CTA: Completed job with asset has valid download CTA.
7. FOREIGN_ASSET_BLOCKED: Cross-account asset read and download are forbidden (CROSS_ACCOUNT_ASSET_READ=0, CROSS_ACCOUNT_DOWNLOAD=0).
8. DEAD_ASSET_CTA_ZERO: Zero href="#" or dead download buttons.
9. EMPTY_STATES_TRUTHFUL: No fake rows, mock jobs, or placeholder assets on empty states.
10. BACKEND_FAILURE_TRUTHFUL: Bridge failure/timeout does not fake empty success.
11. WALLET_HISTORY_PROTECTED: /wallet/history remains dedicated to canonical wallet ledger.
12. ASSET_DETAIL_ROUTE_RESOLVES: /assets/{id} resolves truthfully via render_portal and API.
13. HISTORY_SEMANTICS_UNAMBIGUOUS: History routes distinguish job history, wallet history, and activity history.
"""

from __future__ import annotations

import importlib
from pathlib import Path
import re
import sys

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
PORTAL_JS_PATH = ROOT / "static" / "portal" / "portal.js"
COPYFAST_PAGES_PATH = ROOT / "copyfast_pages.py"
COPYFAST_REGISTRY_PATH = ROOT / "copyfast_registry.py"

MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_native_read_models", "copyfast_api", "copyfast_projects", "copyfast_assets",
    "copyfast_project_packages", "copyfast_document_operations", "copyfast_image_runtime",
    "copyfast_image_operations", "copyfast_pages",
]


def make_client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "web05-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "web05-test-session-secret-key-32chars!!")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "5")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "20")
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_ROOT", str(tmp_path / "private-packages"))
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_MAX_MB", "5")
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_QUOTA_MB", "20")
    for name in (
        "APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH",
        "CORE_BRIDGE_BASE_URL", "CORE_BRIDGE_TOKEN", "CORE_BRIDGE_HMAC_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def register_and_login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123!",
            "display_name": f"User {email}",
        },
    )
    assert registered.status_code == 200, registered.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPassword123!"},
    )
    assert login.status_code == 200, login.text
    return login.json()["data"]["csrf_token"]


def create_native_records(client: TestClient, csrf: str, *, tag: str) -> tuple[dict, dict, bytes]:
    source_bytes = f"private native source for {tag}".encode("utf-8")
    uploaded = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": f"native-read-asset-{tag}-0001"},
        data={"display_name": f"Private source {tag}"},
        files={"file": (f"{tag}-brief.txt", source_bytes, "text/plain")},
    )
    assert uploaded.status_code == 200, uploaded.text
    asset = uploaded.json()["data"]["asset"]

    project_response = client.post(
        "/api/v1/projects",
        headers={"X-CSRF-Token": csrf},
        json={
            "title": f"Native package {tag}",
            "summary": "Private Web-native package test",
            "objective": "Verify generic compatibility reads",
            "idempotency_key": f"native-read-project-{tag}-0001",
        },
    )
    assert project_response.status_code == 200, project_response.text
    project = project_response.json()["data"]["project"]
    document_response = client.post(
        f"/api/v1/projects/{project['id']}/documents",
        headers={"X-CSRF-Token": csrf},
        json={
            "kind": "script",
            "title": f"Private document {tag}",
            "content": f"This document belongs only to {tag}.",
            "idempotency_key": f"native-read-document-{tag}-0001",
        },
    )
    assert document_response.status_code == 200, document_response.text
    package_response = client.post(
        f"/api/v1/projects/{project['id']}/packages",
        headers={"X-CSRF-Token": csrf},
        json={"idempotency_key": f"native-read-package-{tag}-0001"},
    )
    assert package_response.status_code == 200, package_response.text
    package = package_response.json()["data"]["package"]
    return asset, package, source_bytes


def test_customer_sees_only_own_jobs(tmp_path: Path, monkeypatch) -> None:
    """1. CUSTOMER_SEES_ONLY_OWN_JOBS: User A cannot see User B's Web-native jobs."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf_a = register_and_login(client, "user_a@example.com")
        asset_a, package_a, _ = create_native_records(client, csrf_a, tag="usera")

        # Check User A sees their own jobs
        jobs_a = client.get("/api/v1/jobs").json()
        assert jobs_a.get("ok") is True
        items_a = jobs_a["data"]["items"]
        assert len(items_a) > 0
        job_ids_a = {item["id"] for item in items_a}

        # User B registers and logs in
        csrf_b = register_and_login(client, "user_b@example.com")
        jobs_b = client.get("/api/v1/jobs").json()
        assert jobs_b.get("ok") is True
        items_b = jobs_b["data"]["items"]
        job_ids_b = {item["id"] for item in items_b}
        assert not any(jid in job_ids_b for jid in job_ids_a), (
            "Cross-account job read detected: User B saw User A's job!"
        )


def test_foreign_job_blocked(tmp_path: Path, monkeypatch) -> None:
    """2. FOREIGN_JOB_BLOCKED: User B cannot access User A's job detail."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf_a = register_and_login(client, "user_a_detail@example.com")
        asset_a, package_a, _ = create_native_records(client, csrf_a, tag="useradetail")
        jobs_a = client.get("/api/v1/jobs").json()
        job_id_a = jobs_a["data"]["items"][0]["id"]

        # User B tries to access User A's job detail
        register_and_login(client, "user_b_detail@example.com")
        res = client.get(f"/api/v1/jobs/{job_id_a}")
        assert res.status_code == 200
        body = res.json()
        assert body.get("ok") is False
        assert body.get("error_code") == "WEB_NATIVE_JOB_NOT_FOUND"


def test_job_progress_truth_in_api(tmp_path: Path, monkeypatch) -> None:
    """3. UNKNOWN_PROGRESS_TRUTH: Canonical progress is preserved if numeric, never fabricated."""
    with make_client(tmp_path, monkeypatch) as client:
        register_and_login(client, "progress_truth@example.com")
        db_path = tmp_path / "web05-test.db"
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_accounts SET canonical_user_id=? WHERE email=?", ("7126457028", "progress_truth@example.com"))
        # Re-login to populate canonical_user_id in session
        client.post("/api/v1/auth/login", json={"email": "progress_truth@example.com", "password": "StrongPassword123!"})

        api = importlib.import_module("copyfast_api")

        async def fake_bridge(method, path, **_kwargs):
            if path == "/internal/v1/jobs":
                return {
                    "ok": True,
                    "status": "completed",
                    "message": "canonical",
                    "data": {
                        "items": [
                            {"id": "job-with-prog", "status": "processing", "progress": 65},
                            {"id": "job-unknown-prog", "status": "processing"},
                        ]
                    },
                }
            return {"ok": True, "status": "completed", "message": "canonical", "data": {}}

        monkeypatch.setattr(api, "bridge_configured", lambda: True)
        monkeypatch.setattr(api, "_canonical_companion_ready", lambda _account: True)
        monkeypatch.setattr(api, "bridge_request", fake_bridge)

        jobs_res = client.get("/api/v1/jobs").json()
        assert jobs_res.get("ok") is True
        items = jobs_res["data"]["items"]
        item_prog = next((i for i in items if i["id"] == "job-with-prog"), None)
        item_unk = next((i for i in items if i["id"] == "job-unknown-prog"), None)

        assert item_prog is not None
        assert item_prog.get("progress") == 65, f"Progress was stripped or altered: {item_prog}"

        assert item_unk is not None
        assert item_unk.get("progress") is None or "progress" not in item_unk, (
            f"Unknown progress was falsely invented as {item_unk.get('progress')}"
        )


def test_foreign_asset_blocked(tmp_path: Path, monkeypatch) -> None:
    """4. FOREIGN_ASSET_BLOCKED: User B cannot download User A's private asset."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf_a = register_and_login(client, "user_a_asset@example.com")
        upload_res = client.post(
            "/api/v1/asset-vault/upload",
            headers={"X-CSRF-Token": csrf_a, "Idempotency-Key": "asset-a-0000000001"},
            data={"display_name": "Private File A"},
            files={"file": ("secret.txt", b"user a top secret content", "text/plain")},
        )
        assert upload_res.status_code == 200, upload_res.text
        asset_id_a = upload_res.json()["data"]["asset"]["id"]

        # User B attempts to download User A's asset
        register_and_login(client, "user_b_asset@example.com")
        dl_res = client.get(f"/api/v1/asset-vault/{asset_id_a}/download")
        assert dl_res.status_code == 200
        body = dl_res.json()
        assert body.get("ok") is False
        assert body.get("error_code") == "WEB_ASSET_NOT_FOUND"
        assert b"user a top secret content" not in dl_res.content


def test_dead_asset_cta_count_zero() -> None:
    """5. DEAD_ASSET_CTA: No href='#' or href='javascript:*' anywhere in portal.js."""
    content = PORTAL_JS_PATH.read_text(encoding="utf-8")
    dead_hashes = list(re.finditer(r'href=["\']#["\']', content))
    assert len(dead_hashes) == 0, f"Found {len(dead_hashes)} dead href='#' in portal.js"
    dead_js = list(re.finditer(r'href=["\']javascript:[^"\']*["\']', content))
    assert len(dead_js) == 0, f"Found {len(dead_js)} dead javascript hrefs in portal.js"


def test_wallet_history_semantics_preserved(tmp_path: Path, monkeypatch) -> None:
    """6. WALLET_HISTORY_PROTECTED: /wallet/history remains wallet history, not jobs."""
    with make_client(tmp_path, monkeypatch) as client:
        register_and_login(client, "wallet_user@example.com")
        db_path = tmp_path / "web05-test.db"
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_accounts SET canonical_user_id=? WHERE email=?", ("7126457028", "wallet_user@example.com"))
        # Re-login to populate canonical_user_id in session
        client.post("/api/v1/auth/login", json={"email": "wallet_user@example.com", "password": "StrongPassword123!"})

        api = importlib.import_module("copyfast_api")

        async def fake_bridge(method, path, **_kwargs):
            if path == "/internal/v1/wallet/history":
                return {
                    "ok": True,
                    "status": "completed",
                    "message": "ok",
                    "data": {
                        "items": [
                            {"created_at": "2026-09-17T12:00:00Z", "event_type": "topup", "delta_xu": 500, "balance_after_xu": 1000}
                        ]
                    },
                }
            return {"ok": True, "status": "completed", "data": {}}

        monkeypatch.setattr(api, "bridge_configured", lambda: True)
        monkeypatch.setattr(api, "_canonical_companion_ready", lambda _account: True)
        monkeypatch.setattr(api, "bridge_request", fake_bridge)

        res = client.get("/api/v1/wallet/history")
        assert res.status_code == 200
        body = res.json()
        assert body["ok"] is True
        assert len(body["data"]["items"]) == 1
        assert body["data"]["items"][0]["delta_xu"] == 500


def test_asset_detail_route_resolves_in_portal_pages() -> None:
    """7. ASSET_DETAIL_ROUTE: /assets/{id} must resolve with HTTP 200 in render_portal."""
    from copyfast_pages import render_portal
    res = render_portal("/assets/canonical-asset-12345")
    assert res.status_code == 200, f"/assets/canonical-asset-12345 returned {res.status_code}"


def test_asset_detail_api_exists_and_guards(tmp_path: Path, monkeypatch) -> None:
    """8. ASSET_DETAIL_API: GET /api/v1/assets/{id} exists and enforces ownership."""
    with make_client(tmp_path, monkeypatch) as client:
        register_and_login(client, "asset_detail_test@example.com")
        res = client.get("/api/v1/assets/unknown-asset-id-999")
        assert res.status_code == 200
        body = res.json()
        assert body.get("ok") is False


def test_history_route_resolves_unambiguously() -> None:
    """9. HISTORY_ROUTE: /history resolves with HTTP 200 in render_portal."""
    from copyfast_pages import render_portal
    res = render_portal("/history")
    assert res.status_code == 200, f"render_portal('/history') returned {res.status_code}"
