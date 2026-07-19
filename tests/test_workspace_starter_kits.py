"""Focused security and transaction contracts for Web-native Starter Kits.

Starter Kits are deliberately a local Project + Studio Documents + Workboard
seed.  These tests exercise the narrow, high-risk boundaries only: signed
ownership and CSRF, raw body limits and rate lanes, no-partial-write guards,
idempotent receipts, and maintenance flags.  They must never start a Bot,
bridge, provider, job, wallet or payment flow.
"""

from __future__ import annotations

import importlib
import sqlite3
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient


MODULES = [
    "app",
    "copyfast_db",
    "copyfast_auth",
    "copyfast_bridge",
    "copyfast_registry",
    "copyfast_api",
    "copyfast_pages",
    "copyfast_projects",
    "copyfast_assets",
    "copyfast_project_packages",
    "copyfast_document_operations",
    "copyfast_image_runtime",
    "copyfast_image_operations",
    "copyfast_memory",
    "copyfast_workboard",
    "copyfast_workspace_setup",
    "copyfast_starter_kits",
]


def make_client(
    tmp_path,
    monkeypatch,
    *,
    starter_kits_enabled: bool = True,
    workboard_enabled: bool = True,
) -> TestClient:
    """Load a fresh app whose flags and SQLite volume belong to this test."""

    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "starter-kits-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "starter-kits-test-session-secret")
    monkeypatch.setenv("WEBAPP_STARTER_KITS_ENABLED", "true" if starter_kits_enabled else "false")
    monkeypatch.setenv("WEBAPP_WORKBOARD_ENABLED", "true" if workboard_enabled else "false")
    for name in ("APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "correct-horse-battery-staple",
            "display_name": "Starter Kit Owner",
        },
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def complete_setup(client: TestClient, csrf: str, key: str = "starter-kits-setup-complete-0001") -> dict:
    response = client.post(
        "/api/v1/workspace/setup",
        headers={"X-CSRF-Token": csrf},
        json={
            "intent": "complete",
            "role": "solo_creator",
            "goal": "create_content",
            "experience": "growing",
            "focus_areas": ["projects", "content"],
            "expected_revision": 0,
            "idempotency_key": key,
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["profile"]["setup_state"] == "completed"
    return response.json()["data"]["profile"]


def apply_payload(
    key: str,
    *,
    kit_version: int = 1,
    expected_setup_revision: int = 1,
    confirmed: bool = True,
) -> dict:
    return {
        "kit_version": kit_version,
        "expected_setup_revision": expected_setup_revision,
        "confirmed": confirmed,
        "idempotency_key": key,
    }


def boundary_from(response: dict) -> dict:
    data = response.get("data") if isinstance(response.get("data"), dict) else {}
    return data.get("boundary") if isinstance(data.get("boundary"), dict) else data


def assert_web_only_boundary(
    response: dict,
    *,
    installed: bool = False,
    catalog_loaded: bool | None = None,
) -> None:
    boundary = boundary_from(response)
    assert boundary["execution"] == "web_native_starter_kit_install"
    assert isinstance(boundary["catalog_loaded"], bool)
    if catalog_loaded is not None:
        assert boundary["catalog_loaded"] is catalog_loaded
    for key in (
        "bot_called",
        "bridge_called",
        "provider_called",
        "job_created",
        "wallet_mutated",
        "payment_started",
        "publish_action_created",
        "notification_sent",
        "asset_created",
        "delivery_created",
    ):
        assert boundary[key] is False
    for key in ("installation_created", "project_created", "studio_documents_created", "workboard_items_created"):
        assert boundary[key] is installed


def row_count(db_path, table: str) -> int:
    with sqlite3.connect(db_path) as conn:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def test_starter_kits_require_signed_session_csrf_bounded_body_and_fixed_rate_lanes(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        unsigned = client.get("/api/v1/workspace/starter-kits")
        assert unsigned.status_code == 401
        assert_web_only_boundary(unsigned.json())

        csrf = login(client, "starter-auth@example.com")
        catalog = client.get("/api/v1/workspace/starter-kits")
        assert catalog.status_code == 200
        assert catalog.json()["status"] == "read_only"
        assert len(catalog.json()["data"]["kits"]) == 8
        assert {kit["state"] for kit in catalog.json()["data"]["kits"]} == {"setup_required"}
        assert_web_only_boundary(catalog.json(), catalog_loaded=True)

        denied = client.post(
            "/api/v1/workspace/starter-kits/project-foundation/apply",
            json=apply_payload("starter-kits-csrf-required-0001"),
        )
        assert denied.status_code == 403
        assert_web_only_boundary(denied.json())

        too_large = client.post(
            "/api/v1/workspace/starter-kits/project-foundation/apply",
            headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
            content=b'{"kit_version":1,"padding":"' + (b"x" * (9 * 1024)) + b'"}',
        )
        assert too_large.status_code == 413
        assert too_large.json()["error_code"] == "WEB_STARTER_KITS_BODY_TOO_LARGE"
        assert too_large.headers["Cache-Control"] == "no-store, private"
        assert_web_only_boundary(too_large.json())

        app_module = sys.modules["app"]
        client_ip = "testclient"
        app_module._auth_rate_windows.clear()
        app_module._auth_rate_windows[f"starter-kits-read:{client_ip}"] = [time.monotonic()] * 120
        read_limited = client.get("/api/v1/workspace/starter-kits")
        assert read_limited.status_code == 429
        assert read_limited.json()["error_code"] == "AUTH_RATE_LIMITED"
        assert_web_only_boundary(read_limited.json())

        app_module._auth_rate_windows.clear()
        app_module._auth_rate_windows[f"starter-kits-write:{client_ip}"] = [time.monotonic()] * 20
        write_limited = client.post(
            "/api/v1/workspace/starter-kits/project-foundation/apply",
            headers={"X-CSRF-Token": csrf},
            json=apply_payload("starter-kits-rate-write-0001"),
        )
        assert write_limited.status_code == 429
        assert write_limited.json()["error_code"] == "AUTH_RATE_LIMITED"
        assert_web_only_boundary(write_limited.json())


def test_starter_kit_setup_and_capacity_guards_leave_no_partial_records(tmp_path, monkeypatch):
    db_path = tmp_path / "starter-kits-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "starter-guarded@example.com")
        setup_required = client.post(
            "/api/v1/workspace/starter-kits/project-foundation/apply",
            headers={"X-CSRF-Token": csrf},
            json=apply_payload("starter-kits-setup-required-0001"),
        )
        assert setup_required.status_code == 200
        assert setup_required.json()["ok"] is False
        assert setup_required.json()["status"] == "guarded"
        assert setup_required.json()["error_code"] == "WEB_STARTER_KITS_SETUP_REQUIRED"
        assert_web_only_boundary(setup_required.json(), catalog_loaded=True)
        assert row_count(db_path, "web_projects") == 0
        assert row_count(db_path, "web_studio_documents") == 0
        assert row_count(db_path, "web_workboard_items") == 0
        assert row_count(db_path, "web_workspace_starter_kit_installs") == 0

        complete_setup(client, csrf)
        workboard_module = sys.modules["copyfast_workboard"]
        monkeypatch.setattr(workboard_module, "MAX_ITEMS_PER_ACCOUNT", 0)
        capacity_guard = client.post(
            "/api/v1/workspace/starter-kits/project-foundation/apply",
            headers={"X-CSRF-Token": csrf},
            json=apply_payload("starter-kits-capacity-guard-0001"),
        )
        assert capacity_guard.status_code == 200
        assert capacity_guard.json()["ok"] is False
        assert capacity_guard.json()["status"] == "guarded"
        assert capacity_guard.json()["error_code"] == "WEB_STARTER_KITS_WORKBOARD_LIMIT"
        assert_web_only_boundary(capacity_guard.json(), catalog_loaded=True)

    # The capacity guard runs before the Project/Documents/Workboard bundle,
    # so a declined install cannot leave a partially-created workspace.
    assert row_count(db_path, "web_projects") == 0
    assert row_count(db_path, "web_studio_documents") == 0
    assert row_count(db_path, "web_studio_document_versions") == 0
    assert row_count(db_path, "web_workboard_items") == 0
    assert row_count(db_path, "web_workspace_starter_kit_installs") == 0


def test_starter_kit_install_is_atomic_idempotent_owner_scoped_and_audited(tmp_path, monkeypatch):
    db_path = tmp_path / "starter-kits-test.db"
    owner_email = "starter-owner@example.com"
    with make_client(tmp_path, monkeypatch) as client:
        owner_csrf = login(client, owner_email)
        profile = complete_setup(client, owner_csrf)
        request = apply_payload("starter-kits-install-owner-0001", expected_setup_revision=profile["revision"])
        created = client.post(
            "/api/v1/workspace/starter-kits/project-foundation/apply",
            headers={"X-CSRF-Token": owner_csrf},
            json=request,
        )
        assert created.status_code == 200
        assert created.json()["ok"] is True
        assert created.json()["status"] == "draft"
        assert_web_only_boundary(created.json(), installed=True, catalog_loaded=True)
        installation = created.json()["data"]["installation"]
        assert installation["kit_key"] == "project-foundation"
        assert installation["kit_version"] == 1
        assert installation["work_item_count"] == 1
        assert installation["document_count"] >= 2
        assert installation["setup_profile_revision"] == profile["revision"]

        replay = client.post(
            "/api/v1/workspace/starter-kits/project-foundation/apply",
            headers={"X-CSRF-Token": owner_csrf},
            json=request,
        )
        assert replay.status_code == 200
        assert replay.json() == created.json()
        collision = client.post(
            "/api/v1/workspace/starter-kits/project-foundation/apply",
            headers={"X-CSRF-Token": owner_csrf},
            json=apply_payload(
                "starter-kits-install-owner-0001",
                expected_setup_revision=profile["revision"] + 1,
            ),
        )
        assert collision.status_code == 409

        duplicate = client.post(
            "/api/v1/workspace/starter-kits/project-foundation/apply",
            headers={"X-CSRF-Token": owner_csrf},
            json=apply_payload("starter-kits-install-duplicate-0001", expected_setup_revision=profile["revision"]),
        )
        assert duplicate.status_code == 200
        assert duplicate.json()["ok"] is False
        assert duplicate.json()["status"] == "guarded"
        assert duplicate.json()["error_code"] == "WEB_STARTER_KITS_ALREADY_INSTALLED"
        assert_web_only_boundary(duplicate.json(), catalog_loaded=True)

        # The next signed account receives no installation projection from the
        # first account, even though it uses the same shared SQLite volume.
        other_csrf = login(client, "starter-other@example.com")
        other_catalog = client.get("/api/v1/workspace/starter-kits")
        assert other_catalog.status_code == 200
        other_project = next(kit for kit in other_catalog.json()["data"]["kits"] if kit["key"] == "project-foundation")
        assert other_project["installation"] is None
        assert other_project["state"] == "setup_required"
        assert other_csrf

    with sqlite3.connect(db_path) as conn:
        owner = conn.execute("SELECT id FROM web_accounts WHERE email=?", (owner_email,)).fetchone()
        assert owner
        owner_id = str(owner[0])
        install = conn.execute(
            """SELECT id, project_id, document_count, work_item_count, kit_digest, setup_profile_revision
               FROM web_workspace_starter_kit_installs WHERE account_id=? AND kit_key=?""",
            (owner_id, "project-foundation"),
        ).fetchone()
        assert install
        install_id, project_id, document_count, work_item_count, digest, stored_revision = install
        assert str(project_id) == installation["project_id"]
        assert int(document_count) == installation["document_count"]
        assert int(work_item_count) == 1
        assert len(str(digest)) == 64
        assert int(stored_revision) == profile["revision"]
        assert conn.execute("SELECT COUNT(*) FROM web_projects WHERE id=? AND account_id=?", (project_id, owner_id)).fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM web_studio_documents WHERE project_id=? AND account_id=?", (project_id, owner_id)).fetchone()[0] == document_count
        assert conn.execute(
            """SELECT COUNT(*) FROM web_studio_document_versions v
               JOIN web_studio_documents d ON d.id=v.document_id
               WHERE d.project_id=? AND v.account_id=?""",
            (project_id, owner_id),
        ).fetchone()[0] == document_count
        item = conn.execute(
            """SELECT i.id FROM web_workboard_items i
               JOIN web_workboard_item_references r ON r.item_id=i.id
               WHERE i.account_id=? AND r.ref_type='project' AND r.ref_id=?""",
            (owner_id, project_id),
        ).fetchone()
        assert item
        item_id = str(item[0])
        checklist_count = conn.execute(
            "SELECT COUNT(*) FROM web_workboard_checklist_items WHERE item_id=? AND account_id=?",
            (item_id, owner_id),
        ).fetchone()[0]
        assert checklist_count >= 1
        assert conn.execute("SELECT COUNT(*) FROM web_workboard_item_versions WHERE item_id=?", (item_id,)).fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM web_workboard_checklist_versions WHERE item_id=?", (item_id,)).fetchone()[0] == checklist_count
        assert conn.execute(
            "SELECT COUNT(*) FROM web_workboard_events WHERE item_id=? AND action='starter_kit_seeded'",
            (item_id,),
        ).fetchone()[0] == 1
        audit = conn.execute(
            "SELECT action, detail FROM web_audit_events WHERE target=?",
            (install_id,),
        ).fetchone()
        assert audit == ("web.starter_kit.apply", "web-native starter kit installed")
        receipt = conn.execute(
            "SELECT response_json FROM web_idempotency WHERE scope=? AND key=?",
            (f"web-starter-kits:{owner_id}:apply", request["idempotency_key"]),
        ).fetchone()
        assert receipt
        # Receipt/audit retain opaque IDs and counts, not authored document
        # content, account identity, storage locations or provider data.
        assert owner_email not in str(receipt[0])
        assert "Khung Project Web" not in str(receipt[0])
        assert "Brief khởi đầu" not in str(receipt[0])

    module_source = (Path(__file__).resolve().parents[1] / "copyfast_starter_kits.py").read_text(encoding="utf-8").lower()
    for forbidden in (
        "import bot",
        "from bot",
        "copyfast_bridge",
        "payos",
        "import requests",
        "import httpx",
        "telegram_send",
    ):
        assert forbidden not in module_source


def test_starter_kit_flags_fail_closed_without_records(tmp_path, monkeypatch):
    db_path = tmp_path / "starter-kits-test.db"
    with make_client(tmp_path, monkeypatch, starter_kits_enabled=False) as client:
        csrf = login(client, "starter-disabled@example.com")
        disabled = client.get("/api/v1/workspace/starter-kits")
        assert disabled.status_code == 503
        assert "WEBAPP_STARTER_KITS_ENABLED" in disabled.text
        assert_web_only_boundary(disabled.json())
        assert csrf

    with make_client(tmp_path, monkeypatch, workboard_enabled=False) as client:
        csrf = login(client, "starter-workboard-disabled@example.com")
        profile = complete_setup(client, csrf, "starter-kits-workboard-disabled-setup-0001")
        catalog = client.get("/api/v1/workspace/starter-kits")
        assert catalog.status_code == 200
        assert catalog.json()["data"]["workboard_ready"] is False
        assert {kit["state"] for kit in catalog.json()["data"]["kits"]} == {"maintenance"}
        paused = client.post(
            "/api/v1/workspace/starter-kits/project-foundation/apply",
            headers={"X-CSRF-Token": csrf},
            json=apply_payload("starter-kits-workboard-disabled-0001", expected_setup_revision=profile["revision"]),
        )
        assert paused.status_code == 503
        assert_web_only_boundary(paused.json())

    assert row_count(db_path, "web_projects") == 0
    assert row_count(db_path, "web_studio_documents") == 0
    assert row_count(db_path, "web_workboard_items") == 0
    assert row_count(db_path, "web_workspace_starter_kit_installs") == 0
