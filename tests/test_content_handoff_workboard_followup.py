"""Owner-safe Content Handoff to Workboard follow-up contracts.

Most tests mount only the two Web-native routers with dependency overrides;
the signed-session case mounts the real local app. They never call the bridge,
contact a provider, mutate a wallet/payment ledger, or create a
delivery/publish action.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import importlib
import json
import sqlite3
import sys
from threading import Barrier
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest


MODULES = [
    "copyfast_db",
    "copyfast_auth",
    "copyfast_support",
    "copyfast_native_read_models",
    "copyfast_content_handoff",
    "copyfast_workboard",
]

FULL_APP_MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry", "copyfast_api",
    "copyfast_pages", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations", "copyfast_image_studio",
    "copyfast_document_workspace", "copyfast_chat_workspace", "copyfast_analytics_workspace", "copyfast_workboard",
    "copyfast_memory", "copyfast_prompt_library", "copyfast_music_media", "copyfast_content_studio",
    "copyfast_voice_studio", "copyfast_video_studio", "copyfast_subtitle_workspace", "copyfast_support",
]


def _account(email: str, role: str = "user") -> dict[str, str | None]:
    return {"id": str(uuid.uuid4()), "email": email, "role": role, "canonical_user_id": None}


def _insert_account(db, account: dict[str, str | None]) -> None:
    now = db.utc_now()
    with db.transaction() as conn:
        conn.execute(
            """INSERT INTO web_accounts
               (id, email, password_hash, display_name, canonical_user_id, role_cache, is_active, password_login_enabled, created_at, updated_at)
               VALUES (?, ?, 'test-password-hash', 'Test account', NULL, ?, 1, 1, ?, ?)""",
            (str(account["id"]), str(account["email"]), str(account["role"]), now, now),
        )


def _seed_project(db, account_id: str) -> dict[str, object]:
    project_id = str(uuid.uuid4())
    now = db.utc_now()
    with db.transaction() as conn:
        conn.execute(
            """INSERT INTO web_projects (id, account_id, title, summary, objective, state, created_at, updated_at)
               VALUES (?, ?, 'Project follow-up riêng tư', 'Nguồn Web-owned', 'Rà soát', 'active', ?, ?)""",
            (project_id, account_id, now, now),
        )
    return {"project_id": project_id, "asset_ids": [], "campaign_id": None, "native_refs": []}


def make_client(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "handoff-followup-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "handoff-followup-test-secret")
    monkeypatch.setenv("WEBAPP_CONTENT_HANDOFF_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_WORKBOARD_ENABLED", "true")
    for name in ("APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH"):
        monkeypatch.delenv(name, raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    handoff = importlib.import_module("copyfast_content_handoff")
    workboard = importlib.import_module("copyfast_workboard")
    db = importlib.import_module("copyfast_db")
    handoff._ensure_schema()
    owner = _account("owner-handoff-followup@example.com")
    manager = _account("manager-handoff-followup@example.com", "support_manager")
    for account in (owner, manager):
        _insert_account(db, account)
    context = {"account": owner}
    app = FastAPI()
    app.include_router(handoff.router)
    app.include_router(workboard.router)
    app.dependency_overrides[handoff.require_account] = lambda: context["account"]
    app.dependency_overrides[handoff.require_csrf] = lambda: context["account"]
    app.dependency_overrides[workboard.require_account] = lambda: context["account"]
    app.dependency_overrides[workboard.require_csrf] = lambda: context["account"]
    return TestClient(app), handoff, workboard, db, context, owner, manager


def make_full_app_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "handoff-followup-full-app-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "handoff-followup-full-app-test-secret")
    monkeypatch.setenv("WEBAPP_CONTENT_HANDOFF_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_WORKBOARD_ENABLED", "true")
    for name in ("APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH"):
        monkeypatch.delenv(name, raising=False)
    for name in ("CORE_BRIDGE_BASE_URL", "CORE_BRIDGE_TOKEN", "CORE_BRIDGE_HMAC_SECRET"):
        monkeypatch.delenv(name, raising=False)
    for name in FULL_APP_MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def _create_and_approve_handoff(client: TestClient, context: dict, owner: dict, manager: dict, references: dict[str, object]) -> dict:
    created = client.post(
        "/api/v1/content-handoffs/records",
        json={
            "title": "Bộ nội dung đã sẵn sàng follow-up",
            "purpose": "Owner cần theo dõi bước phối hợp nội bộ sau khi Customer Care đã approve.",
            "references": references,
            "idempotency_key": "handoff-followup-record-create-0001",
        },
    )
    assert created.status_code == 200 and created.json()["ok"] is True
    record = created.json()["data"]["record"]
    submitted = client.post(
        f"/api/v1/content-handoffs/records/{record['id']}/submit-review",
        json={
            "expected_revision": record["revision"],
            "confirm": True,
            "idempotency_key": "handoff-followup-submit-review-0001",
        },
    )
    assert submitted.status_code == 200 and submitted.json()["ok"] is True
    record = submitted.json()["data"]["record"]
    context["account"] = manager
    approved = client.post(
        f"/api/v1/content-handoffs/admin/records/{record['id']}/review",
        json={
            "decision": "approved_for_handoff",
            "review_note": "Đã kiểm tra nội bộ.",
            "expected_revision": record["revision"],
            "confirm": True,
            "confirm_manual_handoff": False,
            "idempotency_key": "handoff-followup-manager-approve-0001",
        },
    )
    assert approved.status_code == 200 and approved.json()["ok"] is True
    context["account"] = owner
    return approved.json()["data"]["record"]


def _followup_payload(record: dict, *, idempotency_key: str) -> dict:
    return {
        "handoff_id": record["id"],
        "expected_handoff_revision": record["revision"],
        "title": "Theo dõi bước bàn giao nội bộ",
        "checklist": [{"body": "Rà soát tiến độ follow-up", "is_done": False}],
        "priority": "high",
        "due_at": "2026-08-01T09:00",
        "confirm": True,
        "idempotency_key": idempotency_key,
    }


def _workboard_item_count(db, account_id: str) -> int:
    with db.read_transaction() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM web_workboard_items WHERE account_id=?",
            (account_id,),
        ).fetchone()
    return int(row[0])


def _assert_followup_public_shape(value: dict) -> None:
    assert set(value) == {"handoff_id", "handoff_revision", "link_state"}


def test_followup_request_is_closed_and_strict_without_creating_a_card(tmp_path, monkeypatch):
    client, _handoff, _workboard, db, context, owner, manager = make_client(tmp_path, monkeypatch)
    try:
        record = _create_and_approve_handoff(client, context, owner, manager, _seed_project(db, str(owner["id"])))
        payload = _followup_payload(record, idempotency_key="handoff-followup-strict-valid-0001")
        invalid_payloads = [
            {**payload, "expected_handoff_revision": str(record["revision"])},
            {**payload, "confirm": 1},
            {**payload, "checklist": [{"body": "Không được ép kiểu", "is_done": 1}]},
            {key: value for key, value in payload.items() if key != "confirm"},
        ]
        for index, invalid in enumerate(invalid_payloads, start=1):
            response = client.post(
                "/api/v1/workboard/content-handoff-followups",
                json={**invalid, "idempotency_key": f"handoff-followup-strict-{index:04d}"},
            )
            assert response.status_code == 422
            assert _workboard_item_count(db, str(owner["id"])) == 0
    finally:
        client.close()


def test_followup_requires_content_handoff_to_be_enabled(tmp_path, monkeypatch):
    client, _handoff, _workboard, db, context, owner, manager = make_client(tmp_path, monkeypatch)
    try:
        record = _create_and_approve_handoff(client, context, owner, manager, _seed_project(db, str(owner["id"])))
        monkeypatch.setenv("WEBAPP_CONTENT_HANDOFF_ENABLED", "false")
        response = client.post(
            "/api/v1/workboard/content-handoff-followups",
            json=_followup_payload(record, idempotency_key="handoff-followup-feature-disabled-0001"),
        )
        assert response.status_code == 503
        assert _workboard_item_count(db, str(owner["id"])) == 0
    finally:
        client.close()


def test_full_app_followup_requires_signed_session_and_csrf(tmp_path, monkeypatch):
    client = make_full_app_client(tmp_path, monkeypatch)
    try:
        payload = {
            "handoff_id": str(uuid.uuid4()), "expected_handoff_revision": 1,
            "title": "Follow-up signed session", "checklist": [], "priority": "normal",
            "due_at": None, "confirm": True, "idempotency_key": "handoff-followup-full-app-0001",
        }
        anonymous = TestClient(client.app)
        try:
            assert anonymous.post("/api/v1/workboard/content-handoff-followups", json=payload).status_code == 401
        finally:
            anonymous.close()
        registered = client.post(
            "/api/v1/auth/register",
            json={"email": "signed-followup@example.com", "password": "correct-horse-battery-staple", "display_name": "Signed owner"},
        )
        assert registered.status_code == 200 and registered.json()["ok"] is True
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "signed-followup@example.com", "password": "correct-horse-battery-staple"},
        )
        assert login.status_code == 200 and login.json()["ok"] is True
        csrf = login.json()["data"]["csrf_token"]
        importlib.import_module("copyfast_content_handoff")._ensure_schema()
        db_path = tmp_path / "handoff-followup-full-app-test.db"
        account_id = sqlite3.connect(db_path).execute(
            "SELECT id FROM web_accounts WHERE email=?", ("signed-followup@example.com",)
        ).fetchone()[0]
        record_id = str(uuid.uuid4())
        now = "2026-07-29T00:00:00+00:00"
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """INSERT INTO web_content_handoff_records
                   (id, account_id, title, purpose, references_json, handoff_status, record_state, staff_note,
                    reviewer_account_id, revision, created_at, updated_at, reviewed_at, handed_off_at, archived_at)
                   VALUES (?, ?, 'Signed source', 'Local seeded record only', '{}', 'approved_for_handoff', 'active', '', NULL, 1, ?, ?, NULL, NULL, NULL)""",
                (record_id, account_id, now, now),
            )
        payload["handoff_id"] = record_id
        assert client.post("/api/v1/workboard/content-handoff-followups", json=payload).status_code == 403
        assert client.post(
            "/api/v1/workboard/content-handoff-followups", headers={"X-CSRF-Token": "wrong"}, json=payload,
        ).status_code == 403
        created = client.post(
            "/api/v1/workboard/content-handoff-followups", headers={"X-CSRF-Token": csrf}, json=payload,
        )
        assert created.status_code == 200 and created.json()["ok"] is True
    finally:
        client.close()


def test_followup_guards_draft_review_blocked_and_archived_without_creating_a_card(tmp_path, monkeypatch):
    client, _handoff, _workboard, db, context, owner, manager = make_client(tmp_path, monkeypatch)
    try:
        created = client.post(
            "/api/v1/content-handoffs/records",
            json={
                "title": "Handoff lifecycle guard",
                "purpose": "Kiểm tra các trạng thái không đủ điều kiện tạo follow-up.",
                "references": _seed_project(db, str(owner["id"])),
                "idempotency_key": "handoff-followup-lifecycle-create-0001",
            },
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        record = created.json()["data"]["record"]

        for status, expected_code in (("draft", "WEB_WORKBOARD_HANDOFF_NOT_ELIGIBLE"),):
            response = client.post(
                "/api/v1/workboard/content-handoff-followups",
                json=_followup_payload(record, idempotency_key=f"handoff-followup-lifecycle-{status}-0001"),
            )
            assert response.status_code == 200
            assert response.json()["error_code"] == expected_code
            assert _workboard_item_count(db, str(owner["id"])) == 0

        submitted = client.post(
            f"/api/v1/content-handoffs/records/{record['id']}/submit-review",
            json={
                "expected_revision": record["revision"],
                "confirm": True,
                "idempotency_key": "handoff-followup-lifecycle-review-0001",
            },
        )
        assert submitted.status_code == 200 and submitted.json()["ok"] is True
        record = submitted.json()["data"]["record"]
        response = client.post(
            "/api/v1/workboard/content-handoff-followups",
            json=_followup_payload(record, idempotency_key="handoff-followup-lifecycle-review-0002"),
        )
        assert response.status_code == 200
        assert response.json()["error_code"] == "WEB_WORKBOARD_HANDOFF_NOT_ELIGIBLE"
        assert _workboard_item_count(db, str(owner["id"])) == 0

        context["account"] = manager
        blocked = client.post(
            f"/api/v1/content-handoffs/admin/records/{record['id']}/review",
            json={
                "decision": "blocked",
                "review_note": "Thiếu xác nhận nội bộ.",
                "expected_revision": record["revision"],
                "confirm": True,
                "confirm_manual_handoff": False,
                "idempotency_key": "handoff-followup-lifecycle-blocked-0001",
            },
        )
        assert blocked.status_code == 200 and blocked.json()["ok"] is True
        record = blocked.json()["data"]["record"]
        context["account"] = owner
        response = client.post(
            "/api/v1/workboard/content-handoff-followups",
            json=_followup_payload(record, idempotency_key="handoff-followup-lifecycle-blocked-0002"),
        )
        assert response.status_code == 200
        assert response.json()["error_code"] == "WEB_WORKBOARD_HANDOFF_NOT_ELIGIBLE"
        assert _workboard_item_count(db, str(owner["id"])) == 0

        archived = client.post(
            f"/api/v1/content-handoffs/records/{record['id']}/archive",
            json={
                "expected_revision": record["revision"],
                "confirm": True,
                "idempotency_key": "handoff-followup-lifecycle-archived-0001",
            },
        )
        assert archived.status_code == 200 and archived.json()["ok"] is True
        record = archived.json()["data"]["record"]
        response = client.post(
            "/api/v1/workboard/content-handoff-followups",
            json=_followup_payload(record, idempotency_key="handoff-followup-lifecycle-archived-0002"),
        )
        assert response.status_code == 200
        assert response.json()["error_code"] == "WEB_WORKBOARD_HANDOFF_ARCHIVED"
        assert _workboard_item_count(db, str(owner["id"])) == 0
    finally:
        client.close()


def test_relation_collision_after_card_creation_returns_guarded_without_an_orphan(tmp_path, monkeypatch):
    client, _handoff, workboard, db, context, owner, manager = make_client(tmp_path, monkeypatch)
    try:
        record = _create_and_approve_handoff(client, context, owner, manager, _seed_project(db, str(owner["id"])))
        original_create = workboard._create_item_in_transaction

        def create_with_competing_relation(conn, **kwargs):
            created = original_create(conn, **kwargs)
            if created.get("ok") is False:
                return created
            now = db.utc_now()
            conn.execute(
                """INSERT INTO web_content_handoff_workboard_followups
                   (id, account_id, handoff_id, handoff_revision, workboard_item_id, link_state, created_at, updated_at, superseded_at)
                   VALUES (?, ?, ?, ?, ?, 'active', ?, ?, NULL)""",
                (str(uuid.uuid4()), owner["id"], record["id"], record["revision"], created["item_id"], now, now),
            )
            return created

        monkeypatch.setattr(workboard, "_create_item_in_transaction", create_with_competing_relation)
        response = client.post(
            "/api/v1/workboard/content-handoff-followups",
            json=_followup_payload(record, idempotency_key="handoff-followup-relation-race-0001"),
        )
        assert response.status_code == 200
        assert response.json()["ok"] is False
        assert response.json()["error_code"] == "WEB_WORKBOARD_HANDOFF_FOLLOWUP_EXISTS"
        assert _workboard_item_count(db, str(owner["id"])) == 0
        with db.read_transaction() as conn:
            relation_count = conn.execute(
                "SELECT COUNT(*) FROM web_content_handoff_workboard_followups WHERE handoff_id=? AND handoff_revision=?",
                (record["id"], record["revision"]),
            ).fetchone()
        assert int(relation_count[0]) == 0
    finally:
        client.close()


def test_concurrent_followup_requests_create_exactly_one_card_and_relation(tmp_path, monkeypatch):
    client, _handoff, _workboard, db, context, owner, manager = make_client(tmp_path, monkeypatch)
    first_client = TestClient(client.app)
    second_client = TestClient(client.app)
    try:
        record = _create_and_approve_handoff(client, context, owner, manager, _seed_project(db, str(owner["id"])))
        start = Barrier(3)

        def create_followup(request_client: TestClient, idempotency_key: str):
            start.wait(timeout=10)
            return request_client.post(
                "/api/v1/workboard/content-handoff-followups",
                json=_followup_payload(record, idempotency_key=idempotency_key),
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(create_followup, first_client, "handoff-followup-concurrent-first-0001"),
                executor.submit(create_followup, second_client, "handoff-followup-concurrent-second-0001"),
            ]
            start.wait(timeout=10)
            responses = [future.result(timeout=15) for future in futures]

        assert [response.status_code for response in responses] == [200, 200]
        bodies = [response.json() for response in responses]
        assert sum(body["ok"] is True for body in bodies) == 1
        guarded = [body for body in bodies if body["ok"] is False]
        assert len(guarded) == 1
        assert guarded[0]["error_code"] == "WEB_WORKBOARD_HANDOFF_FOLLOWUP_EXISTS"
        assert "locked" not in str(bodies).lower()
        assert _workboard_item_count(db, str(owner["id"])) == 1
        with db.read_transaction() as conn:
            relation_count = conn.execute(
                "SELECT COUNT(*) FROM web_content_handoff_workboard_followups WHERE account_id=? AND handoff_id=? AND handoff_revision=?",
                (owner["id"], record["id"], record["revision"]),
            ).fetchone()
        assert int(relation_count[0]) == 1
    finally:
        first_client.close()
        second_client.close()
        client.close()


def test_stale_handoff_revision_creates_no_followup_card(tmp_path, monkeypatch):
    client, _handoff, _workboard, db, context, owner, manager = make_client(tmp_path, monkeypatch)
    try:
        record = _create_and_approve_handoff(client, context, owner, manager, _seed_project(db, str(owner["id"])))
        response = client.post(
            "/api/v1/workboard/content-handoff-followups",
            json=_followup_payload(
                {**record, "revision": record["revision"] - 1},
                idempotency_key="handoff-followup-stale-revision-0001",
            ),
        )
        assert response.status_code == 200
        assert response.json()["error_code"] == "WEB_WORKBOARD_HANDOFF_REVISION_CONFLICT"
        assert _workboard_item_count(db, str(owner["id"])) == 0
    finally:
        client.close()


def test_handed_off_handoff_can_create_one_followup(tmp_path, monkeypatch):
    client, _handoff, _workboard, db, context, owner, manager = make_client(tmp_path, monkeypatch)
    try:
        record = _create_and_approve_handoff(client, context, owner, manager, _seed_project(db, str(owner["id"])))
        context["account"] = manager
        handed_off = client.post(
            f"/api/v1/content-handoffs/admin/records/{record['id']}/review",
            json={
                "decision": "handed_off", "review_note": "Đã ghi nhận bàn giao nội bộ.",
                "expected_revision": record["revision"], "confirm": True, "confirm_manual_handoff": True,
                "idempotency_key": "handoff-followup-handed-off-0001",
            },
        )
        assert handed_off.status_code == 200 and handed_off.json()["ok"] is True
        context["account"] = owner
        record = handed_off.json()["data"]["record"]
        created = client.post(
            "/api/v1/workboard/content-handoff-followups",
            json=_followup_payload(record, idempotency_key="handoff-followup-handed-off-0002"),
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        assert _workboard_item_count(db, str(owner["id"])) == 1
    finally:
        client.close()


def test_second_owner_cannot_create_followup_for_another_owner_handoff(tmp_path, monkeypatch):
    client, _handoff, _workboard, db, context, owner, manager = make_client(tmp_path, monkeypatch)
    try:
        record = _create_and_approve_handoff(client, context, owner, manager, _seed_project(db, str(owner["id"])))
        other_owner = _account("other-owner-handoff-followup@example.com")
        _insert_account(db, other_owner)
        context["account"] = other_owner
        response = client.post(
            "/api/v1/workboard/content-handoff-followups",
            json=_followup_payload(record, idempotency_key="handoff-followup-other-owner-0001"),
        )
        assert response.status_code == 200
        assert response.json()["error_code"] == "WEB_WORKBOARD_HANDOFF_NOT_FOUND"
        assert _workboard_item_count(db, str(owner["id"])) == 0
        assert _workboard_item_count(db, str(other_owner["id"])) == 0
    finally:
        client.close()


@pytest.mark.parametrize("source_change", ("archive", "revision"))
def test_list_reconciliation_only_supersedes_relation_for_archive_or_revision_change(tmp_path, monkeypatch, source_change):
    client, _handoff, _workboard, db, context, owner, manager = make_client(tmp_path, monkeypatch)
    try:
        record = _create_and_approve_handoff(client, context, owner, manager, _seed_project(db, str(owner["id"])))
        created = client.post(
            "/api/v1/workboard/content-handoff-followups",
            json=_followup_payload(record, idempotency_key=f"handoff-followup-list-{source_change}-0001"),
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        item = created.json()["data"]["item"]
        with db.transaction() as conn:
            if source_change == "archive":
                conn.execute(
                    "UPDATE web_content_handoff_records SET record_state='archived', updated_at=? WHERE id=? AND account_id=?",
                    (db.utc_now(), record["id"], owner["id"]),
                )
            else:
                conn.execute(
                    "UPDATE web_content_handoff_records SET revision=revision+1, updated_at=? WHERE id=? AND account_id=?",
                    (db.utc_now(), record["id"], owner["id"]),
                )
        listing = client.get("/api/v1/workboard/items")
        assert listing.status_code == 200 and listing.json()["ok"] is True
        listed = next(value for value in listing.json()["data"]["items"] if value["id"] == item["id"])
        assert listed["state"] == "backlog"
        _assert_followup_public_shape(listed["content_handoff_followup"])
        assert listed["content_handoff_followup"]["link_state"] == "superseded"
        detail = client.get(f"/api/v1/workboard/items/{item['id']}")
        assert detail.status_code == 200 and detail.json()["data"]["item"]["state"] == "backlog"
        assert detail.json()["data"]["checklist"][0]["is_done"] is False
    finally:
        client.close()


def test_active_followup_list_and_detail_use_only_deferred_read_transactions(tmp_path, monkeypatch):
    client, _handoff, workboard, db, context, owner, manager = make_client(tmp_path, monkeypatch)
    try:
        record = _create_and_approve_handoff(client, context, owner, manager, _seed_project(db, str(owner["id"])))
        created = client.post(
            "/api/v1/workboard/content-handoff-followups",
            json=_followup_payload(record, idempotency_key="handoff-followup-read-path-0001"),
        )
        assert created.status_code == 200 and created.json()["ok"] is True

        events: list[str] = []
        original_read_transaction = workboard.read_transaction
        original_transaction = workboard.transaction

        @contextmanager
        def tracked_read_transaction():
            events.append("read_enter")
            with original_read_transaction() as conn:
                yield conn
            events.append("read_exit")

        @contextmanager
        def tracked_transaction():
            events.append("write_enter")
            with original_transaction() as conn:
                yield conn
            events.append("write_exit")

        monkeypatch.setattr(workboard, "read_transaction", tracked_read_transaction)
        monkeypatch.setattr(workboard, "transaction", tracked_transaction)

        listing = client.get("/api/v1/workboard/items")
        assert listing.status_code == 200 and listing.json()["ok"] is True
        assert events == ["read_enter", "read_exit"]
        listed = next(item for item in listing.json()["data"]["items"] if item["id"] == created.json()["data"]["item"]["id"])
        _assert_followup_public_shape(listed["content_handoff_followup"])
        assert listed["content_handoff_followup"]["link_state"] == "active"

        detail = client.get(f"/api/v1/workboard/items/{listed['id']}")
        assert detail.status_code == 200 and detail.json()["ok"] is True
        assert events == ["read_enter", "read_exit", "read_enter", "read_exit"]
        _assert_followup_public_shape(detail.json()["data"]["content_handoff_followup"])
        assert detail.json()["data"]["content_handoff_followup"]["link_state"] == "active"
    finally:
        client.close()


def test_owner_creates_one_followup_from_an_approved_handoff(tmp_path, monkeypatch):
    client, _handoff, _workboard, db, context, owner, manager = make_client(tmp_path, monkeypatch)
    try:
        record = _create_and_approve_handoff(client, context, owner, manager, _seed_project(db, str(owner["id"])))
        response = client.post(
            "/api/v1/workboard/content-handoff-followups",
            json={
                "handoff_id": record["id"],
                "expected_handoff_revision": record["revision"],
                "title": "Theo dõi bước bàn giao nội bộ",
                "checklist": [{"body": "Rà soát tiến độ follow-up", "is_done": False}],
                "priority": "high",
                "due_at": "2026-08-01T09:00",
                "confirm": True,
                "idempotency_key": "handoff-followup-owner-create-0001",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["data"]["content_handoff_followup"]["link_state"] == "active"
        _assert_followup_public_shape(body["data"]["content_handoff_followup"])
    finally:
        client.close()


def test_superseded_handoff_link_never_mutates_the_owner_workboard_card(tmp_path, monkeypatch):
    client, _handoff, _workboard, db, context, owner, manager = make_client(tmp_path, monkeypatch)
    try:
        record = _create_and_approve_handoff(client, context, owner, manager, _seed_project(db, str(owner["id"])))
        created = client.post(
            "/api/v1/workboard/content-handoff-followups",
            json={
                "handoff_id": record["id"],
                "expected_handoff_revision": record["revision"],
                "title": "Theo dõi Handoff không tự đóng",
                "checklist": [{"body": "Owner tự quyết định tiến độ", "is_done": False}],
                "priority": "normal",
                "due_at": None,
                "confirm": True,
                "idempotency_key": "handoff-followup-supersede-create-0001",
            },
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        item = created.json()["data"]["item"]
        with db.transaction() as conn:
            conn.execute(
                """UPDATE web_content_handoff_records
                   SET handoff_status='blocked', revision=revision+1, updated_at=?
                   WHERE id=? AND account_id=?""",
                (db.utc_now(), record["id"], owner["id"]),
            )
        detail = client.get(f"/api/v1/workboard/items/{item['id']}")
        assert detail.status_code == 200 and detail.json()["ok"] is True
        data = detail.json()["data"]
        assert data["content_handoff_followup"]["link_state"] == "superseded"
        _assert_followup_public_shape(data["content_handoff_followup"])
        assert data["item"]["state"] == "backlog"
        assert data["checklist"][0]["is_done"] is False
    finally:
        client.close()


def test_followup_is_owner_scoped_confirmed_idempotent_and_never_copies_handoff_detail(tmp_path, monkeypatch):
    client, _handoff, workboard, db, context, owner, manager = make_client(tmp_path, monkeypatch)
    try:
        references = _seed_project(db, str(owner["id"]))
        record = _create_and_approve_handoff(client, context, owner, manager, references)
        payload = {
            "handoff_id": record["id"],
            "expected_handoff_revision": record["revision"],
            "title": "Owner tự theo dõi follow-up",
            "checklist": [{"body": "Xác nhận việc nội bộ", "is_done": False}],
            "priority": "high",
            "due_at": "2026-08-02T10:00",
            "confirm": True,
            "idempotency_key": "handoff-followup-owner-boundary-0001",
        }
        route_calls = {
            (route.path, next(iter(route.methods or set()))): [dependency.call for dependency in route.dependant.dependencies]
            for route in workboard.router.routes
        }
        assert workboard.require_csrf in route_calls[("/api/v1/workboard/content-handoff-followups", "POST")]

        rejected_confirm = client.post(
            "/api/v1/workboard/content-handoff-followups",
            json={**payload, "confirm": False, "idempotency_key": "handoff-followup-confirm-0001"},
        )
        assert rejected_confirm.status_code == 422
        rejected_sensitive = client.post(
            "/api/v1/workboard/content-handoff-followups",
            json={**payload, "staff_note": "không được sao chép", "idempotency_key": "handoff-followup-sensitive-0001"},
        )
        assert rejected_sensitive.status_code == 422

        context["account"] = manager
        foreign = client.post(
            "/api/v1/workboard/content-handoff-followups",
            json={**payload, "idempotency_key": "handoff-followup-manager-foreign-0001"},
        )
        assert foreign.status_code == 200
        assert foreign.json()["error_code"] == "WEB_WORKBOARD_HANDOFF_NOT_FOUND"
        context["account"] = owner

        first = client.post("/api/v1/workboard/content-handoff-followups", json=payload)
        assert first.status_code == 200 and first.json()["ok"] is True
        replay = client.post("/api/v1/workboard/content-handoff-followups", json=payload)
        assert replay.status_code == 200 and replay.json()["ok"] is True
        assert replay.json()["data"]["item"]["id"] == first.json()["data"]["item"]["id"]
        _assert_followup_public_shape(replay.json()["data"]["content_handoff_followup"])
        duplicate = client.post(
            "/api/v1/workboard/content-handoff-followups",
            json={**payload, "idempotency_key": "handoff-followup-owner-second-key-0001"},
        )
        assert duplicate.status_code == 200
        assert duplicate.json()["error_code"] == "WEB_WORKBOARD_HANDOFF_FOLLOWUP_EXISTS"
        assert _workboard_item_count(db, str(owner["id"])) == 1
        collision = client.post(
            "/api/v1/workboard/content-handoff-followups",
            json={**payload, "title": "Một card khác", "idempotency_key": payload["idempotency_key"]},
        )
        assert collision.status_code == 409

        detail = client.get(f"/api/v1/workboard/items/{first.json()['data']['item']['id']}")
        assert detail.status_code == 200 and detail.json()["ok"] is True
        serialized_detail = str(detail.json())
        assert "Owner cần theo dõi bước phối hợp" not in serialized_detail
        assert "Đã kiểm tra nội bộ." not in serialized_detail
        assert references["project_id"] not in serialized_detail
    finally:
        client.close()

    with sqlite3.connect(tmp_path / "handoff-followup-test.db") as conn:
        receipts = conn.execute(
            "SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-workboard:%:content-handoff:%'"
        ).fetchall()
        relations = conn.execute(
            "SELECT handoff_id, handoff_revision, workboard_item_id, link_state FROM web_content_handoff_workboard_followups"
        ).fetchall()
    assert len(relations) == 1
    assert relations[0][0] == record["id"]
    assert relations[0][3] == "active"
    for (receipt,) in receipts:
        assert "Owner cần theo dõi bước phối hợp" not in str(receipt)
        assert "Đã kiểm tra nội bộ." not in str(receipt)
        assert references["project_id"] not in str(receipt)
        parsed = json.loads(receipt)
        followup = parsed.get("data", {}).get("content_handoff_followup")
        if followup:
            _assert_followup_public_shape(followup)
