"""Focused security and lifecycle tests for Web-native Content Handoff.

The test application mounts only the new router.  Its signed-account and CSRF
dependencies are overridden after asserting the real route dependency shape;
this keeps the suite focused on the bounded handoff contract and never starts
the full app, Bot, bridge, provider, payment, wallet, job or publish stack.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import sqlite3
import sys
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient


MODULES = ["copyfast_db", "copyfast_auth", "copyfast_support", "copyfast_native_read_models", "copyfast_content_handoff"]


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


def _seed_references(db, account_id: str, *, suffix: str) -> dict[str, object]:
    project_id = str(uuid.uuid4())
    asset_id = str(uuid.uuid4())
    campaign_id = str(uuid.uuid4())
    now = db.utc_now()
    with db.transaction() as conn:
        conn.execute(
            """INSERT INTO web_projects (id, account_id, title, summary, objective, state, created_at, updated_at)
               VALUES (?, ?, ?, 'Nguồn Web-owned', 'Rà soát handoff', 'active', ?, ?)""",
            (project_id, account_id, f"Project handoff {suffix}", now, now),
        )
        conn.execute(
            """INSERT INTO web_asset_files
               (id, account_id, project_id, display_name, original_filename, extension, content_type, byte_size, sha256, storage_key, state, created_at, updated_at, archived_at)
               VALUES (?, ?, ?, 'asset-handoff.txt', 'asset-handoff.txt', 'txt', 'text/plain', 1, ?, ?, 'active', ?, ?, NULL)""",
            (asset_id, account_id, project_id, "a" * 64, f"test/{suffix}/{asset_id}", now, now),
        )
        conn.execute(
            """INSERT INTO web_campaign_plans
               (id, account_id, title, destination_url, platform, objective, scheduled_for, approval_status, review_note, created_at, updated_at)
               VALUES (?, ?, ?, 'https://example.invalid/never-used', 'website', 'review', NULL, 'draft', '', ?, ?)""",
            (campaign_id, account_id, f"Campaign handoff {suffix}", now, now),
        )
    return {"project_id": project_id, "asset_ids": [asset_id], "campaign_id": campaign_id}


def _seed_native_lineage(db, account_id: str, *, suffix: str) -> dict[str, str]:
    """Seed a real-shaped local output and asset without invoking a provider."""

    source_asset_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    now = db.utc_now()
    with db.transaction() as conn:
        conn.execute(
            """INSERT INTO web_asset_files
               (id, account_id, project_id, display_name, original_filename,
                extension, content_type, byte_size, sha256, storage_key,
                state, created_at, updated_at, archived_at)
               VALUES (?, ?, NULL, 'native-lineage.png', 'native-lineage.png',
                       '.png', 'image/png', 1024, ?, ?, 'active', ?, ?, NULL)""",
            (source_asset_id, account_id, "a" * 64, f"test-native/{suffix}/{source_asset_id}.blob", now, now),
        )
        conn.execute(
            """INSERT INTO web_image_operations
               (id, account_id, source_asset_id, project_id, kind, state,
                idempotency_key, request_fingerprint, source_sha256,
                source_byte_size, source_width, source_height, target_width,
                target_height, preset, fit_mode, storage_key,
                original_filename, content_type, byte_size, sha256,
                failure_code, created_at, queued_at, started_at, completed_at,
                updated_at, settings_json)
               VALUES (?, ?, ?, NULL, 'image_resize', 'completed', ?, ?, ?,
                       1024, 1600, 1200, 1024, 1024, '1:1', 'crop', ?,
                       'untrusted-private-name.png', 'image/png', 2048, ?,
                       NULL, ?, ?, ?, ?, ?, '{}')""",
            (
                job_id,
                account_id,
                source_asset_id,
                f"content-handoff-native-{suffix}",
                f"fingerprint-{suffix}",
                "a" * 64,
                "outputs/" + ("b" * 32) + ".png",
                "c" * 64,
                now,
                now,
                now,
                now,
                now,
            ),
        )
    models = importlib.import_module("copyfast_native_read_models")
    return {
        "native_output": models.encode_native_job_id("image-operation", job_id),
        "native_asset": models.encode_native_asset_id(source_asset_id),
        "source_asset_id": source_asset_id,
        "job_id": job_id,
    }


def make_client(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "content-handoff-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "content-handoff-test-secret")
    monkeypatch.setenv("WEBAPP_CONTENT_HANDOFF_ENABLED", "true")
    for name in ("APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH"):
        monkeypatch.delenv(name, raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    module = importlib.import_module("copyfast_content_handoff")
    db = importlib.import_module("copyfast_db")
    module._ensure_schema()
    owner = _account("owner-content-handoff@example.com")
    other = _account("other-content-handoff@example.com")
    operator = _account("operator-content-handoff@example.com", "support_operator")
    manager = _account("manager-content-handoff@example.com", "support_manager")
    for account in (owner, other, operator, manager):
        _insert_account(db, account)
    context = {"account": owner}
    app = FastAPI()
    app.include_router(module.router)
    app.dependency_overrides[module.require_account] = lambda: context["account"]
    app.dependency_overrides[module.require_csrf] = lambda: context["account"]
    return TestClient(app), module, db, context, owner, other, operator, manager


def _payload(key: str, references: dict[str, object], **overrides) -> dict[str, object]:
    value: dict[str, object] = {
        "title": "Bộ nội dung cần bàn giao nội bộ",
        "purpose": "Đội ngũ cần rà soát nguồn Web-owned và xác nhận bước bàn giao nội bộ tiếp theo.",
        "references": references,
        "idempotency_key": key,
    }
    value.update(overrides)
    return value


def _create(client: TestClient, references: dict[str, object], key: str = "content-handoff-create-0001") -> dict:
    response = client.post("/api/v1/content-handoffs/records", json=_payload(key, references))
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    return body["data"]["record"]


def _seed_handoff_records(
    db,
    account_id: str,
    *,
    count: int,
    prefix: str,
    handoff_status: str = "review",
) -> list[str]:
    """Create deterministic private records without exercising 100+ writes.

    The pagination contract itself is read-only.  Direct inserts keep this
    focused test fast while still using the module's real SQLite schema and
    public record serializer.  The reference is an opaque UUID because list
    reads only decode it; no provider, bot, wallet or external record is
    involved.
    """

    reference_id = str(uuid.uuid4())
    references = json.dumps(
        {"project_id": reference_id, "asset_ids": [], "campaign_id": None},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    rows: list[tuple[object, ...]] = []
    record_ids: list[str] = []
    for index in range(count):
        record_id = str(uuid.uuid4())
        record_ids.append(record_id)
        # Stable values make each multi-page query deterministic while being
        # independent from the local wall clock.
        timestamp = f"2026-07-16T00:{index // 60:02d}:{index % 60:02d}.000000+00:00"
        rows.append(
            (
                record_id,
                account_id,
                f"{prefix} handoff {index:03d}",
                f"Mục đích Web-owned cho {prefix} record {index:03d}, chỉ dùng để kiểm thử phân trang riêng tư.",
                references,
                handoff_status,
                timestamp,
                timestamp,
            )
        )
    with db.transaction() as conn:
        conn.executemany(
            """INSERT INTO web_content_handoff_records
               (id, account_id, title, purpose, references_json, handoff_status, record_state, staff_note,
                reviewer_account_id, revision, created_at, updated_at, reviewed_at, handed_off_at, archived_at)
               VALUES (?, ?, ?, ?, ?, ?, 'active', '', NULL, 1, ?, ?, NULL, NULL, NULL)""",
            rows,
        )
    return record_ids


def test_handoff_routes_are_signed_csrf_writes_and_idempotency_receipts_are_redacted(tmp_path, monkeypatch):
    client, module, db, context, owner, *_ = make_client(tmp_path, monkeypatch)
    try:
        route_calls = {
            (route.path, next(iter(route.methods or set()))) if getattr(route, "methods", None) else ("", ""):
            [dependency.call for dependency in route.dependant.dependencies]
            for route in module.router.routes
        }
        for path in (
            "/api/v1/content-handoffs/records",
            "/api/v1/content-handoffs/records/{record_id}/submit-review",
            "/api/v1/content-handoffs/records/{record_id}/archive",
            "/api/v1/content-handoffs/records/{record_id}/restore",
            "/api/v1/content-handoffs/admin/records/{record_id}/review",
        ):
            assert module.require_csrf in route_calls[(path, "POST")]

        references = _seed_references(db, str(owner["id"]), suffix="owner")
        raw = _payload("content-handoff-idempotency-0001", references)
        first = client.post("/api/v1/content-handoffs/records", json=raw)
        assert first.status_code == 200 and first.json()["ok"] is True
        record = first.json()["data"]["record"]
        replay = client.post("/api/v1/content-handoffs/records", json=raw)
        assert replay.status_code == 200 and replay.json()["ok"] is True
        assert replay.json()["data"]["record"]["id"] == record["id"]
        assert "purpose" not in replay.json()["data"]["record"]
        collision = client.post(
            "/api/v1/content-handoffs/records",
            json=_payload("content-handoff-idempotency-0001", references, title="Một handoff khác hoàn toàn"),
        )
        assert collision.status_code == 409
    finally:
        client.close()

    db_path = tmp_path / "content-handoff-test.db"
    with sqlite3.connect(db_path) as conn:
        receipts = conn.execute("SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-content-handoff:%'").fetchall()
    assert receipts
    for (receipt,) in receipts:
        assert raw["purpose"] not in str(receipt)
        assert raw["title"] not in str(receipt)


def test_handoff_owner_scopes_opaque_web_references_and_rejects_external_or_foreign_input(tmp_path, monkeypatch):
    client, module, db, context, owner, other, *_ = make_client(tmp_path, monkeypatch)
    try:
        owner_refs = _seed_references(db, str(owner["id"]), suffix="owner")
        record = _create(client, owner_refs, "content-handoff-owner-create-0001")
        context["account"] = other
        hidden = client.get(f"/api/v1/content-handoffs/records/{record['id']}")
        assert hidden.status_code == 200
        assert hidden.json()["error_code"] == "WEB_CONTENT_HANDOFF_NOT_FOUND"
        foreign = client.post(
            "/api/v1/content-handoffs/records",
            json=_payload("content-handoff-foreign-reference-0001", owner_refs),
        )
        assert foreign.status_code == 200
        assert foreign.json()["error_code"] == "WEB_CONTENT_HANDOFF_REFERENCE_INVALID"
        bad_text = client.post(
            "/api/v1/content-handoffs/records",
            json=_payload(
                "content-handoff-external-target-0001",
                _seed_references(db, str(other["id"]), suffix="other"),
                purpose="Bàn giao tới https://example.invalid/destination?token=not-allowed",
            ),
        )
        assert bad_text.status_code == 422
        policy = client.get("/api/v1/content-handoffs/policy")
        assert policy.status_code == 200 and policy.json()["ok"] is True
        boundary = policy.json()["data"]
        for key in (
            "bot_called", "provider_called", "social_oauth_connected", "social_api_called", "publish_action_created",
            "external_notification_sent", "job_created", "wallet_mutated", "payment_processed", "external_delivery_verified",
        ):
            assert boundary[key] is False
    finally:
        client.close()


def test_handoff_native_lineage_requires_sealed_owner_output_and_never_fakes_delivery(tmp_path, monkeypatch):
    client, module, db, context, owner, other, *_ = make_client(tmp_path, monkeypatch)
    try:
        native = _seed_native_lineage(db, str(owner["id"]), suffix="owner")
        references = {
            "project_id": None,
            "asset_ids": [],
            "campaign_id": None,
            "native_refs": [
                {"ref_type": "native_output", "ref_id": native["native_output"]},
                {"ref_type": "native_asset", "ref_id": native["native_asset"]},
            ],
        }
        record = _create(client, references, "content-handoff-native-create-0001")
        detail = client.get(f"/api/v1/content-handoffs/records/{record['id']}")
        assert detail.status_code == 200 and detail.json()["ok"] is True
        assert detail.json()["data"]["record"]["references"]["native_refs"] == references["native_refs"]

        lineage = client.get(f"/api/v1/content-handoffs/records/{record['id']}/lineage")
        assert lineage.status_code == 200 and lineage.json()["ok"] is True
        items = {entry["ref_type"]: entry for entry in lineage.json()["data"]["lineage"]}
        output = items["native_output"]
        assert output == {
            "ref_type": "native_output",
            "ref_id": native["native_output"],
            "state": "completed",
            "status": "completed",
            "availability": "available",
            "output": {
                "filename": "toan-aas-image-resized.png",
                "content_type": "image/png",
                "byte_size": 2048,
            },
        }
        assert items["native_asset"] == {
            "ref_type": "native_asset",
            "ref_id": native["native_asset"],
            "state": "active",
            "status": "active",
            "availability": "available",
            "output": None,
        }
        assert module._safe_lineage_output(
            {"filename": "toan-aas-image-ocr.txt", "content_type": "text/plain; charset=utf-8", "byte_size": 1}
        ) == {"filename": "toan-aas-image-ocr.txt", "content_type": "text/plain; charset=utf-8", "byte_size": 1}
        assert module._safe_lineage_output(
            {"filename": "empty.txt", "content_type": "text/plain", "byte_size": 0}
        ) is None
        serialized = json.dumps(lineage.json(), ensure_ascii=False)
        assert str(native["job_id"]) not in serialized
        assert str(native["source_asset_id"]) not in serialized
        assert "outputs/" not in serialized
        assert '"sha256"' not in serialized
        for key in ("provider_called", "job_created", "wallet_mutated", "payment_processed", "external_delivery_verified"):
            assert lineage.json()["data"][key] is False

        # Native refs are included in the same revisioned document as other
        # Handoff references, and raw/foreign opaque IDs stay rejected.
        updated = client.patch(
            f"/api/v1/content-handoffs/records/{record['id']}",
            json={
                "title": "Bộ nội dung native đã ghi nhận revision",
                "purpose": "Rà soát lineage Web-native an toàn trước khi nhóm nội bộ xem xét bước tiếp theo.",
                "references": references,
                "expected_revision": record["revision"],
                "idempotency_key": "content-handoff-native-update-0001",
            },
        )
        assert updated.status_code == 200 and updated.json()["ok"] is True
        current = client.get(f"/api/v1/content-handoffs/records/{record['id']}").json()["data"]
        assert current["record"]["references"]["native_refs"] == references["native_refs"]
        assert {entry["revision"] for entry in current["versions"]} >= {1, 2}

        malformed = client.post(
            "/api/v1/content-handoffs/records",
            json=_payload(
                "content-handoff-native-malformed-0001",
                {"project_id": None, "asset_ids": [], "campaign_id": None, "native_refs": [{"ref_type": "native_output", "ref_id": "not-an-opaque-id"}]},
            ),
        )
        assert malformed.status_code == 422
        context["account"] = other
        hidden = client.get(f"/api/v1/content-handoffs/records/{record['id']}/lineage")
        assert hidden.status_code == 200 and hidden.json()["error_code"] == "WEB_CONTENT_HANDOFF_NOT_FOUND"
        foreign = client.post(
            "/api/v1/content-handoffs/records",
            json=_payload("content-handoff-native-foreign-0001", references),
        )
        assert foreign.status_code == 200
        assert foreign.json()["error_code"] == "WEB_CONTENT_HANDOFF_REFERENCE_INVALID"

        # The record keeps honest history if its output later loses the sealed
        # contract: no recreated file, URL, or success claim is returned.
        context["account"] = owner
        with db.transaction() as conn:
            conn.execute("UPDATE web_image_operations SET storage_key=NULL WHERE id=?", (native["job_id"],))
        unavailable = client.get(f"/api/v1/content-handoffs/records/{record['id']}/lineage")
        assert unavailable.status_code == 200 and unavailable.json()["ok"] is True
        invalid_output = {entry["ref_type"]: entry for entry in unavailable.json()["data"]["lineage"]}["native_output"]
        assert invalid_output["state"] == "completed"
        assert invalid_output["status"] == "unavailable"
        assert invalid_output["availability"] == "unavailable"
        assert invalid_output["output"] is None
    finally:
        client.close()


def test_handoff_owner_listing_paginates_without_duplicates_or_cross_account_records(tmp_path, monkeypatch):
    """The customer list is offset-paged and remains owner-scoped at every page."""

    client, module, db, context, owner, other, *_ = make_client(tmp_path, monkeypatch)
    try:
        owner_ids = _seed_handoff_records(db, str(owner["id"]), count=101, prefix="owner")
        other_ids = _seed_handoff_records(db, str(other["id"]), count=3, prefix="other", handoff_status="draft")

        pages = [
            client.get(f"/api/v1/content-handoffs/records?status=all&include_archived=true&limit=50&offset={offset}")
            for offset in (0, 50, 100)
        ]
        assert [response.status_code for response in pages] == [200, 200, 200]
        payloads = [response.json()["data"] for response in pages]
        assert [len(payload["items"]) for payload in payloads] == [50, 50, 1]
        assert [payload["has_more"] for payload in payloads] == [True, True, False]
        assert [payload["next_offset"] for payload in payloads] == [50, 100, None]
        seen = [item["id"] for payload in payloads for item in payload["items"]]
        assert len(seen) == len(set(seen)) == 101
        assert set(seen) == set(owner_ids)
        assert not set(seen).intersection(other_ids)

        # Changing the signed account must start a distinct owner-scoped list;
        # it must never reveal page data previously queried by the first user.
        context["account"] = other
        other_page = client.get("/api/v1/content-handoffs/records?status=all&include_archived=true&limit=50&offset=0")
        assert other_page.status_code == 200
        other_payload = other_page.json()["data"]
        assert other_payload["has_more"] is False
        assert other_payload["next_offset"] is None
        assert {item["id"] for item in other_payload["items"]} == set(other_ids)
        assert not {item["id"] for item in other_payload["items"]}.intersection(owner_ids)
    finally:
        client.close()


def test_handoff_staff_queue_paginates_and_rejects_non_staff_session(tmp_path, monkeypatch):
    """The staff queue has its own role guard and bounded page receipt."""

    client, module, db, context, owner, _other, operator, _manager = make_client(tmp_path, monkeypatch)
    try:
        record_ids = _seed_handoff_records(db, str(owner["id"]), count=101, prefix="review", handoff_status="review")

        denied = client.get("/api/v1/content-handoffs/admin/records?status=all&limit=50&offset=0")
        assert denied.status_code == 403

        context["account"] = operator
        pages = [
            client.get(f"/api/v1/content-handoffs/admin/records?status=all&limit=50&offset={offset}")
            for offset in (0, 50, 100)
        ]
        assert [response.status_code for response in pages] == [200, 200, 200]
        payloads = [response.json()["data"] for response in pages]
        assert [payload["operator_role"] for payload in payloads] == ["operator", "operator", "operator"]
        assert [len(payload["items"]) for payload in payloads] == [50, 50, 1]
        assert [payload["has_more"] for payload in payloads] == [True, True, False]
        assert [payload["next_offset"] for payload in payloads] == [50, 100, None]
        seen = [item["id"] for payload in payloads for item in payload["items"]]
        assert len(seen) == len(set(seen)) == 101
        assert set(seen) == set(record_ids)
        # Queue records are detailed enough for authorised review, but the
        # record serializer must not disclose the owner account ID.
        assert all({"title", "purpose", "staff_note"}.issubset(item) for payload in payloads for item in payload["items"])
        assert all("account_id" not in item for payload in payloads for item in payload["items"])
    finally:
        client.close()


def test_handoff_staff_queue_filters_status_server_side_and_rejects_invalid_values(tmp_path, monkeypatch):
    """Customer Care can filter only its authorised internal queue."""

    client, _module, db, context, owner, _other, operator, _manager = make_client(tmp_path, monkeypatch)
    try:
        review_ids = _seed_handoff_records(db, str(owner["id"]), count=2, prefix="filter-review", handoff_status="review")
        blocked_ids = _seed_handoff_records(db, str(owner["id"]), count=3, prefix="filter-blocked", handoff_status="blocked")

        assert client.get("/api/v1/content-handoffs/admin/records?status=review&limit=50&offset=0").status_code == 403

        context["account"] = operator
        review = client.get("/api/v1/content-handoffs/admin/records?status=review&limit=50&offset=0")
        assert review.status_code == 200 and review.json()["ok"] is True
        review_items = review.json()["data"]["items"]
        assert {item["id"] for item in review_items} == set(review_ids)
        assert {item["handoff_status"] for item in review_items} == {"review"}

        blocked = client.get("/api/v1/content-handoffs/admin/records?status=blocked&limit=50&offset=0")
        assert blocked.status_code == 200 and blocked.json()["ok"] is True
        blocked_items = blocked.json()["data"]["items"]
        assert {item["id"] for item in blocked_items} == set(blocked_ids)
        assert {item["handoff_status"] for item in blocked_items} == {"blocked"}

        combined = client.get("/api/v1/content-handoffs/admin/records?status=all&limit=50&offset=0")
        assert combined.status_code == 200
        assert {item["id"] for item in combined.json()["data"]["items"]} == set(review_ids + blocked_ids)
        assert client.get("/api/v1/content-handoffs/admin/records?status=not-a-status&limit=50&offset=0").status_code == 422
    finally:
        client.close()


def test_handoff_lifecycle_uses_revisioned_customer_review_and_server_side_staff_authority(tmp_path, monkeypatch):
    client, module, db, context, owner, other, operator, manager = make_client(tmp_path, monkeypatch)
    try:
        references = _seed_references(db, str(owner["id"]), suffix="lifecycle")
        created = _create(client, references, "content-handoff-lifecycle-create-0001")
        stale = client.post(
            f"/api/v1/content-handoffs/records/{created['id']}/submit-review",
            json={"expected_revision": 999, "confirm": True, "idempotency_key": "content-handoff-stale-review-0001"},
        )
        assert stale.status_code == 200
        assert stale.json()["error_code"] == "WEB_CONTENT_HANDOFF_REVISION_CONFLICT"
        updated = client.patch(
            f"/api/v1/content-handoffs/records/{created['id']}",
            json=_payload(
                "content-handoff-lifecycle-update-0001",
                references,
                purpose="Đội ngũ cần rà soát revision Web-owned đã cập nhật trước khi xác nhận bước bàn giao nội bộ.",
                expected_revision=created["revision"],
            ),
        )
        assert updated.status_code == 200 and updated.json()["ok"] is True
        record = updated.json()["data"]["record"]
        assert record["handoff_status"] == "draft"
        review = client.post(
            f"/api/v1/content-handoffs/records/{created['id']}/submit-review",
            json={"expected_revision": record["revision"], "confirm": True, "idempotency_key": "content-handoff-review-0001"},
        )
        assert review.status_code == 200 and review.json()["ok"] is True
        review_record = review.json()["data"]["record"]
        assert review_record["handoff_status"] == "review"

        context["account"] = operator
        denied = client.post(
            f"/api/v1/content-handoffs/admin/records/{created['id']}/review",
            json={
                "decision": "approved_for_handoff", "review_note": "Đủ điều kiện để chuyển tiếp nội bộ.",
                "expected_revision": review_record["revision"], "confirm": True,
                "idempotency_key": "content-handoff-operator-approve-0001",
            },
        )
        assert denied.status_code == 200
        assert denied.json()["error_code"] == "WEB_CONTENT_HANDOFF_STAFF_MANAGER_REQUIRED"

        context["account"] = manager
        approved = client.post(
            f"/api/v1/content-handoffs/admin/records/{created['id']}/review",
            json={
                "decision": "approved_for_handoff", "review_note": "Đủ điều kiện để chuyển tiếp nội bộ.",
                "expected_revision": review_record["revision"], "confirm": True,
                "idempotency_key": "content-handoff-manager-approve-0001",
            },
        )
        assert approved.status_code == 200 and approved.json()["ok"] is True
        approved_record = approved.json()["data"]["record"]
        assert approved_record["handoff_status"] == "approved_for_handoff"
        handed = client.post(
            f"/api/v1/content-handoffs/admin/records/{created['id']}/review",
            json={
                "decision": "handed_off", "review_note": "Đã ghi nhận nhân sự nội bộ tiếp nhận gói Web-owned.",
                "expected_revision": approved_record["revision"], "confirm": True, "confirm_manual_handoff": True,
                "idempotency_key": "content-handoff-manager-handoff-0001",
            },
        )
        assert handed.status_code == 200 and handed.json()["ok"] is True
        handed_record = handed.json()["data"]["record"]
        assert handed_record["handoff_status"] == "handed_off"
        assert handed.json()["data"]["external_delivery_verified"] is False

        context["account"] = owner
        archive = client.post(
            f"/api/v1/content-handoffs/records/{created['id']}/archive",
            json={"expected_revision": handed_record["revision"], "confirm": True, "idempotency_key": "content-handoff-archive-0001"},
        )
        assert archive.status_code == 200 and archive.json()["ok"] is True
        archived_record = archive.json()["data"]["record"]
        assert archived_record["record_state"] == "archived"
        restore = client.post(
            f"/api/v1/content-handoffs/records/{created['id']}/restore",
            json={"expected_revision": archived_record["revision"], "confirm": True, "idempotency_key": "content-handoff-restore-0001"},
        )
        assert restore.status_code == 200 and restore.json()["ok"] is True
        assert restore.json()["data"]["record"]["record_state"] == "active"
        detail = client.get(f"/api/v1/content-handoffs/records/{created['id']}")
        assert detail.status_code == 200 and detail.json()["ok"] is True
        assert any(event["action"] == "staff_manual_handoff_recorded" for event in detail.json()["data"]["events"])
    finally:
        client.close()

    db_path = tmp_path / "content-handoff-test.db"
    with sqlite3.connect(db_path) as conn:
        audit_actions = conn.execute("SELECT action FROM web_audit_events WHERE action LIKE 'web.content_handoff.%'").fetchall()
    assert {row[0] for row in audit_actions} >= {
        "web.content_handoff.create",
        "web.content_handoff.update",
        "web.content_handoff.submit_review",
        "web.content_handoff.staff_review",
        "web.content_handoff.record_archived",
        "web.content_handoff.record_restored",
    }


def test_content_handoff_stays_independent_of_bot_provider_wallet_job_and_publish_code():
    source = (Path(__file__).parents[1] / "copyfast_content_handoff.py").read_text(encoding="utf-8")
    for forbidden in (
        "import bot", "from bot", "import copyfast_bridge", "from copyfast_bridge", "import PayOS", "from PayOS",
        "import wallet", "from wallet", "import requests", "import httpx", "import urllib",
    ):
        assert forbidden not in source
