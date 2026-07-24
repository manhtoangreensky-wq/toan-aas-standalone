"""Focused safety contracts for the isolated Partner & Lead CRM router.

The router is intentionally mounted only in this test app until a separate
application/UI integration is approved.  These tests exercise the signed Web
account database alone: no Bot, bridge, provider, notification, wallet,
payment, referral or publishing runtime is loaded.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient


MODULES = ["copyfast_db", "copyfast_auth", "copyfast_partner_crm"]


def make_client(tmp_path, monkeypatch, *, enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "partner-crm-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "partner-crm-test-session-secret")
    monkeypatch.setenv("WEBAPP_PARTNER_CRM_ENABLED", "true" if enabled else "false")
    for name in ("APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    auth = importlib.import_module("copyfast_auth")
    crm = importlib.import_module("copyfast_partner_crm")
    app = FastAPI()
    app.include_router(auth.router, prefix="/api/v1/auth")
    app.include_router(crm.router)
    return TestClient(app)


def login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "CRM Owner"},
    )
    assert registered.status_code == 200
    return sign_in(client, email)


def sign_in(client: TestClient, email: str) -> str:
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def lead_payload(key: str = "partner-crm-lead-create-0001", **overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "lead_name": "Nguyễn Minh An",
        "organization": "Studio Nền Tảng",
        "contact_email": "minh.an@example.com",
        "lead_kind": "partner",
        "opportunity_summary": "Cần trao đổi riêng về một gói nội dung và workflow phù hợp cho đội marketing nhỏ.",
        "source_kind": "inbound",
        "source_label": "Biểu mẫu Web tự nguyện",
        "tags": ["B2B", "Nội dung", "Ưu tiên"],
        "consent_status": "documented",
        "consent_note": "Đồng ý được lưu để đội ngũ tự review nội bộ.",
        "idempotency_key": key,
    }
    value.update(overrides)
    return value


def consultation_preview_payload(**overrides: Any) -> dict[str, Any]:
    """The narrow customer intake is intentionally not a generic CRM form."""

    value: dict[str, Any] = {
        "service_id": "web-service-video",
        "request_title": "Tư vấn quy trình video cho đội nhỏ",
        "need_summary": "Đội nhỏ cần chuẩn hóa brief, review và theo dõi đầu ra video trong Web.",
    }
    value.update(overrides)
    return value


def consultation_confirm_payload(
    key: str = "consultation-crm-confirm-0001",
    **overrides: Any,
) -> dict[str, Any]:
    value = {
        **consultation_preview_payload(),
        "consent_to_store": True,
        "confirm_create": True,
        "idempotency_key": key,
    }
    value.update(overrides)
    return value


def storage_counts(db_path: Path) -> dict[str, int]:
    tables = (
        "web_partner_crm_leads",
        "web_partner_crm_notes",
        "web_partner_crm_events",
        "web_idempotency",
        "web_audit_events",
    )
    with sqlite3.connect(db_path) as conn:
        return {
            table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in tables
        }


def account_id_for_email(db_path: Path, email: str) -> str:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()
    assert row is not None
    return str(row[0])


def seed_leads(
    db_path: Path,
    *,
    account_id: str,
    count: int,
    id_start: int,
    stage: str = "qualified",
) -> list[str]:
    """Seed local records only so the list API is tested at page boundaries.

    Creation validation is covered elsewhere.  Keeping this deterministic
    avoids 100+ mutation/audit requests in a focused read-pagination test.
    """

    lead_ids = [f"00000000-0000-4000-8000-{id_start + index:012d}" for index in range(count)]
    rows = []
    for index, lead_id in enumerate(lead_ids, start=1):
        timestamp = f"2026-07-16T12:00:00.{index:03d}+00:00"
        rows.append(
            (
                lead_id,
                account_id,
                f"Lead pagination {index}",
                f"Tổ chức {index}",
                f"lead-{index}@example.com",
                "partner" if index % 2 else "agency",
                f"Nhu cầu nội bộ có thứ tự {index} để kiểm tra phân trang.",
                "manual",
                "Seed kiểm thử",
                "[]",
                "documented",
                "Đã ghi nhận consent nội bộ.",
                stage,
                index,
                timestamp,
                timestamp,
                None,
            )
        )
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            """INSERT INTO web_partner_crm_leads
               (id, account_id, lead_name, organization, contact_email, lead_kind, opportunity_summary,
                source_kind, source_label, tags_json, consent_status, consent_note, stage, revision,
                created_at, updated_at, archived_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        conn.commit()
    return lead_ids


def assert_boundary(data: dict[str, Any], *, persisted: bool) -> None:
    assert data["execution"] == "web_native_partner_lead_crm_only"
    assert data["lead_persisted"] is persisted
    for key in (
        "telegram_state_changed",
        "bot_called",
        "bridge_called",
        "provider_called",
        "remote_lookup_called",
        "social_platform_called",
        "contacted",
        "notification_sent",
        "job_created",
        "wallet_mutated",
        "payment_started",
        "payout_created",
        "referral_ledger_changed",
        "promo_or_membership_changed",
        "publish_action_created",
    ):
        assert data[key] is False


def create_lead(client: TestClient, csrf: str, key: str = "partner-crm-lead-create-0001", **overrides: Any) -> dict[str, Any]:
    response = client.post(
        "/api/v1/partner-crm/leads",
        headers={"X-CSRF-Token": csrf},
        json=lead_payload(key, **overrides),
    )
    assert response.status_code == 200 and response.json()["ok"] is True
    assert_boundary(response.json()["data"], persisted=True)
    return response.json()["data"]["lead"]


def test_partner_crm_requires_signed_session_csrf_idempotency_and_redacts_receipts(tmp_path, monkeypatch):
    db_path = tmp_path / "partner-crm-test.db"
    raw = lead_payload()
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post("/api/v1/partner-crm/leads", json=raw).status_code == 401
        csrf = login(client, "partner-crm-auth@example.com")
        assert client.post("/api/v1/partner-crm/leads", json=raw).status_code == 403

        created = client.post("/api/v1/partner-crm/leads", headers={"X-CSRF-Token": csrf}, json=raw)
        assert created.status_code == 200 and created.json()["ok"] is True
        body = created.json()
        assert body["status"] == "draft"
        assert_boundary(body["data"], persisted=True)
        lead = body["data"]["lead"]
        assert set(lead) == {"id", "revision", "stage"}
        assert lead["revision"] == 1 and lead["stage"] == "draft"

        replay = client.post("/api/v1/partner-crm/leads", headers={"X-CSRF-Token": csrf}, json=raw)
        assert replay.status_code == 200 and replay.json() == body
        collision = client.post(
            "/api/v1/partner-crm/leads",
            headers={"X-CSRF-Token": csrf},
            json=lead_payload(raw["idempotency_key"], organization="Một tổ chức khác hoàn toàn"),
        )
        assert collision.status_code == 409

    with sqlite3.connect(db_path) as conn:
        receipt = conn.execute(
            "SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-partner-crm:%:lead:create'"
        ).fetchone()
        audit = conn.execute(
            "SELECT detail FROM web_audit_events WHERE action='web.partner_crm.lead.create'"
        ).fetchone()
    assert receipt is not None and audit is not None
    assert raw["lead_name"] not in str(receipt[0])
    assert raw["contact_email"] not in str(receipt[0])
    assert raw["opportunity_summary"] not in str(receipt[0])
    assert raw["lead_name"] not in str(audit[0])
    assert raw["contact_email"] not in str(audit[0])


def test_partner_crm_owner_scoped_crud_notes_stage_tags_and_consent(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        first_csrf = login(client, "partner-crm-owner@example.com")
        created = create_lead(client, first_csrf, "partner-crm-owner-create-0001")
        lead_id = created["id"]

        detail = client.get(f"/api/v1/partner-crm/leads/{lead_id}")
        assert detail.status_code == 200 and detail.json()["ok"] is True
        first = detail.json()["data"]["lead"]
        assert first["contact_email"] == "minh.an@example.com"
        assert first["tags"] == ["B2B", "Nội dung", "Ưu tiên"]

        updated_payload = lead_payload(
            "partner-crm-owner-update-0001",
            organization="Studio Nền Tảng Mới",
            tags=["B2B", "b2b", "Đã review"],
        )
        updated_payload["expected_revision"] = first["revision"]
        updated = client.patch(
            f"/api/v1/partner-crm/leads/{lead_id}",
            headers={"X-CSRF-Token": first_csrf},
            json=updated_payload,
        )
        assert updated.status_code == 200 and updated.json()["ok"] is True
        assert updated.json()["data"]["lead"]["revision"] == 2

        qualified = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/stage",
            headers={"X-CSRF-Token": first_csrf},
            json={"stage": "qualified", "expected_revision": 2, "idempotency_key": "partner-crm-owner-stage-0001"},
        )
        assert qualified.status_code == 200 and qualified.json()["data"]["lead"] == {"id": lead_id, "revision": 3, "stage": "qualified"}

        consent = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/consent",
            headers={"X-CSRF-Token": first_csrf},
            json={
                "consent_status": "withdrawn",
                "consent_note": "Lead yêu cầu chỉ lưu lịch sử nội bộ, không được chủ động liên hệ.",
                "expected_revision": 3,
                "idempotency_key": "partner-crm-owner-consent-0001",
            },
        )
        assert consent.status_code == 200 and consent.json()["data"]["lead"]["revision"] == 4

        note = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/notes",
            headers={"X-CSRF-Token": first_csrf},
            json={
                "body": "Đã kiểm tra nội bộ: cần chờ lead tự chủ động trao đổi tiếp.",
                "expected_revision": 4,
                "idempotency_key": "partner-crm-owner-note-0001",
            },
        )
        assert note.status_code == 200 and note.json()["ok"] is True
        assert note.json()["data"]["lead"]["revision"] == 5
        assert set(note.json()["data"]["note"]) == {"id", "created_at"}

        after = client.get(f"/api/v1/partner-crm/leads/{lead_id}").json()["data"]
        assert after["lead"]["organization"] == "Studio Nền Tảng Mới"
        assert after["lead"]["tags"] == ["B2B", "Đã review"]
        assert after["lead"]["consent_status"] == "withdrawn"
        assert len(after["notes"]) == 1
        assert {event["action"] for event in after["events"]} >= {
            "lead_created", "lead_updated", "stage_changed", "consent_recorded", "note_added",
        }

        second_csrf = login(client, "partner-crm-other@example.com")
        hidden = client.get(f"/api/v1/partner-crm/leads/{lead_id}")
        assert hidden.status_code == 200
        assert hidden.json()["error_code"] == "WEB_PARTNER_CRM_LEAD_NOT_FOUND"
        foreign_update = client.patch(
            f"/api/v1/partner-crm/leads/{lead_id}",
            headers={"X-CSRF-Token": second_csrf},
            json={**lead_payload("partner-crm-foreign-update-0001"), "expected_revision": 5},
        )
        assert foreign_update.status_code == 200
        assert foreign_update.json()["error_code"] == "WEB_PARTNER_CRM_LEAD_NOT_FOUND"
        own_list = client.get("/api/v1/partner-crm/leads")
        assert own_list.status_code == 200 and own_list.json()["data"]["items"] == []

        # A local Web manager can see only a redacted read-only directory.
        # Promote this separate test account in the signed-session database;
        # its existing session reloads role_cache on the next request.
        with sqlite3.connect(tmp_path / "partner-crm-test.db") as conn:
            conn.execute("UPDATE web_accounts SET role_cache='admin' WHERE email=?", ("partner-crm-other@example.com",))
            conn.commit()
        directory = client.get("/api/v1/partner-crm/manager/leads")
        assert directory.status_code == 200 and directory.json()["ok"] is True
        directory_data = directory.json()["data"]
        assert directory_data["cross_account_write_available"] is False
        assert directory_data["contact_detail_available"] is False
        assert directory_data["notes_available"] is False
        assert_boundary(directory_data, persisted=False)
        item = next(value for value in directory_data["items"] if value["stage"] == "qualified")
        assert item["stage"] == "qualified" and item["consent_status"] == "withdrawn"
        for private_key in ("lead_id", "owner_account_id", "owner_display_name", "lead_name", "organization", "contact_email", "opportunity_summary", "source_label", "tags", "consent_note", "notes"):
            assert private_key not in item
        # Manager visibility never bypasses the normal owner-scoped detail API.
        assert client.get(f"/api/v1/partner-crm/leads/{lead_id}").json()["error_code"] == "WEB_PARTNER_CRM_LEAD_NOT_FOUND"


def test_partner_crm_owner_list_paginates_101_records_without_cross_account_cursor_leakage(tmp_path, monkeypatch):
    """Owner pages remain scoped to the signed account at every offset."""

    db_path = tmp_path / "partner-crm-test.db"
    owner_email = "partner-crm-page-owner@example.com"
    other_email = "partner-crm-page-other@example.com"
    with make_client(tmp_path, monkeypatch) as client:
        login(client, owner_email)
        assert client.get("/api/v1/partner-crm/summary").status_code == 200
        owner_ids = set(
            seed_leads(
                db_path,
                account_id=account_id_for_email(db_path, owner_email),
                count=101,
                id_start=100_000,
            )
        )

        login(client, other_email)
        other_ids = set(
            seed_leads(
                db_path,
                account_id=account_id_for_email(db_path, other_email),
                count=2,
                id_start=200_000,
            )
        )
        other_page = client.get("/api/v1/partner-crm/leads?stage=all&limit=50&offset=0")
        assert other_page.status_code == 200 and other_page.json()["ok"] is True
        assert {item["id"] for item in other_page.json()["data"]["items"]} == other_ids
        assert other_page.json()["data"]["has_more"] is False
        assert other_page.json()["data"]["next_offset"] is None

        sign_in(client, owner_email)
        pages = []
        for offset, expected_count, has_more, next_offset in ((0, 50, True, 50), (50, 50, True, 100), (100, 1, False, None)):
            response = client.get(f"/api/v1/partner-crm/leads?stage=all&limit=50&offset={offset}")
            assert response.status_code == 200 and response.json()["ok"] is True
            data = response.json()["data"]
            assert len(data["items"]) == expected_count
            assert data["has_more"] is has_more
            assert data["next_offset"] == next_offset
            pages.append({item["id"] for item in data["items"]})

    assert all(page.isdisjoint(other_ids) for page in pages)
    assert pages[0].isdisjoint(pages[1]) and pages[0].isdisjoint(pages[2]) and pages[1].isdisjoint(pages[2])
    assert set().union(*pages) == owner_ids


def test_partner_crm_manager_directory_is_role_guarded_paginated_and_redacted(tmp_path, monkeypatch):
    """The directory pages only after the server confirms an admin role."""

    db_path = tmp_path / "partner-crm-test.db"
    owner_email = "partner-crm-directory-owner@example.com"
    manager_email = "partner-crm-directory-manager@example.com"
    with make_client(tmp_path, monkeypatch) as client:
        login(client, owner_email)
        assert client.get("/api/v1/partner-crm/summary").status_code == 200
        seed_leads(
            db_path,
            account_id=account_id_for_email(db_path, owner_email),
            count=101,
            id_start=300_000,
        )

        login(client, manager_email)
        denied = client.get("/api/v1/partner-crm/manager/leads?stage=all&limit=50&offset=0")
        assert denied.status_code == 403

        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_accounts SET role_cache='admin' WHERE email=?", (manager_email,))
            conn.commit()

        pages = []
        for offset, expected_count, has_more, next_offset in ((0, 50, True, 50), (50, 50, True, 100), (100, 1, False, None)):
            response = client.get(f"/api/v1/partner-crm/manager/leads?stage=all&limit=50&offset={offset}")
            assert response.status_code == 200 and response.json()["ok"] is True
            data = response.json()["data"]
            assert len(data["items"]) == expected_count
            assert data["has_more"] is has_more
            assert data["next_offset"] == next_offset
            assert data["cross_account_write_available"] is False
            assert data["contact_detail_available"] is False
            assert data["notes_available"] is False
            assert_boundary(data, persisted=False)
            pages.append(data["items"])

    seen_revisions = {int(item["revision"]) for page in pages for item in page}
    assert seen_revisions == set(range(1, 102))
    for item in (value for page in pages for value in page):
        for private_key in (
            "id", "lead_id", "account_id", "owner_account_id", "owner_display_name", "lead_name",
            "organization", "contact_email", "opportunity_summary", "source_label", "tags", "consent_note", "notes",
        ):
            assert private_key not in item


def test_partner_crm_manager_directory_filters_stage_server_side_and_stays_redacted(tmp_path, monkeypatch):
    """Stage filtering remains an admin-only, redacted server query."""

    db_path = tmp_path / "partner-crm-test.db"
    owner_email = "partner-crm-filter-owner@example.com"
    manager_email = "partner-crm-filter-manager@example.com"
    with make_client(tmp_path, monkeypatch) as client:
        login(client, owner_email)
        assert client.get("/api/v1/partner-crm/summary").status_code == 200
        owner_id = account_id_for_email(db_path, owner_email)
        seed_leads(db_path, account_id=owner_id, count=2, id_start=510_000, stage="qualified")
        seed_leads(db_path, account_id=owner_id, count=3, id_start=520_000, stage="draft")

        login(client, manager_email)
        assert client.get("/api/v1/partner-crm/manager/leads?stage=qualified&limit=50&offset=0").status_code == 403
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_accounts SET role_cache='admin' WHERE email=?", (manager_email,))
            conn.commit()

        qualified = client.get("/api/v1/partner-crm/manager/leads?stage=qualified&limit=50&offset=0")
        assert qualified.status_code == 200 and qualified.json()["ok"] is True
        qualified_items = qualified.json()["data"]["items"]
        assert len(qualified_items) == 2
        assert {item["stage"] for item in qualified_items} == {"qualified"}

        draft = client.get("/api/v1/partner-crm/manager/leads?stage=draft&limit=50&offset=0")
        assert draft.status_code == 200 and draft.json()["ok"] is True
        draft_items = draft.json()["data"]["items"]
        assert len(draft_items) == 3
        assert {item["stage"] for item in draft_items} == {"draft"}

        combined = client.get("/api/v1/partner-crm/manager/leads?stage=all&limit=50&offset=0")
        assert combined.status_code == 200 and len(combined.json()["data"]["items"]) == 5
        for item in combined.json()["data"]["items"]:
            for private_key in ("id", "lead_id", "account_id", "lead_name", "organization", "contact_email", "notes"):
                assert private_key not in item

        invalid = client.get("/api/v1/partner-crm/manager/leads?stage=not-a-stage&limit=50&offset=0")
        assert invalid.status_code == 422


def test_partner_crm_pipeline_revision_and_archive_boundary(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "partner-crm-stage@example.com")
        lead = create_lead(client, csrf, "partner-crm-stage-create-0001")
        lead_id = lead["id"]

        invalid = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/stage",
            headers={"X-CSRF-Token": csrf},
            json={"stage": "proposal", "expected_revision": 1, "idempotency_key": "partner-crm-stage-invalid-0001"},
        )
        assert invalid.status_code == 200
        assert invalid.json()["error_code"] == "WEB_PARTNER_CRM_STAGE_TRANSITION"

        qualified = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/stage",
            headers={"X-CSRF-Token": csrf},
            json={"stage": "qualified", "expected_revision": 1, "idempotency_key": "partner-crm-stage-qualified-0001"},
        )
        assert qualified.status_code == 200 and qualified.json()["data"]["lead"]["revision"] == 2
        archived = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/stage",
            headers={"X-CSRF-Token": csrf},
            json={"stage": "archived", "expected_revision": 2, "idempotency_key": "partner-crm-stage-archive-0001"},
        )
        assert archived.status_code == 200 and archived.json()["data"]["lead"] == {"id": lead_id, "revision": 3, "stage": "archived"}

        denied_note = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/notes",
            headers={"X-CSRF-Token": csrf},
            json={"body": "Không được ghi vào lead archived.", "expected_revision": 3, "idempotency_key": "partner-crm-archived-note-0001"},
        )
        assert denied_note.status_code == 200
        assert denied_note.json()["error_code"] == "WEB_PARTNER_CRM_ARCHIVED"
        restored = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/stage",
            headers={"X-CSRF-Token": csrf},
            json={"stage": "draft", "expected_revision": 3, "idempotency_key": "partner-crm-stage-restore-0001"},
        )
        assert restored.status_code == 200 and restored.json()["data"]["lead"] == {"id": lead_id, "revision": 4, "stage": "draft"}
        stale = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/stage",
            headers={"X-CSRF-Token": csrf},
            json={"stage": "qualified", "expected_revision": 1, "idempotency_key": "partner-crm-stage-stale-0001"},
        )
        assert stale.status_code == 200
        assert stale.json()["error_code"] == "WEB_PARTNER_CRM_REVISION_CONFLICT"


def test_partner_crm_rejects_unsafe_schema_and_has_no_remote_or_money_surface(tmp_path, monkeypatch):
    db_path = tmp_path / "partner-crm-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "partner-crm-safety@example.com")
        headers = {"X-CSRF-Token": csrf}
        assert client.get("/api/v1/partner-crm/manager/leads").status_code == 403
        for index, overrides in enumerate((
            {"lead_name": "<script>alert(1)</script>"},
            {"opportunity_summary": "api_key=not-a-real-secret-value"},
            {"opportunity_summary": "Mã OTP 123456 không được lưu trong CRM"},
            {"contact_email": "not-an-email"},
            {"consent_status": "documented", "consent_note": ""},
            {"payout_amount": 100000},
            {"referral_code": "should-not-exist"},
        ), start=1):
            response = client.post(
                "/api/v1/partner-crm/leads",
                headers=headers,
                json=lead_payload(f"partner-crm-safety-{index:04d}", **overrides),
            )
            assert response.status_code == 422

        policy = client.get("/api/v1/partner-crm/policy")
        assert policy.status_code == 200 and policy.json()["ok"] is True
        policy_data = policy.json()["data"]
        assert policy_data["canonical_admin_directory_available"] is False
        assert_boundary(policy_data, persisted=False)

        create_lead(client, csrf, "partner-crm-safety-create-0001")

    with sqlite3.connect(db_path) as conn:
        tables = {str(row[0]) for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        counts = storage_counts(db_path)
    assert {"web_partner_crm_leads", "web_partner_crm_notes", "web_partner_crm_events"}.issubset(tables)
    assert counts["web_partner_crm_leads"] == 1
    assert counts["web_partner_crm_notes"] == 0
    assert not any("payos" in table.lower() or "wallet" in table.lower() or "payout" in table.lower() for table in tables)

    source = (Path(__file__).resolve().parents[1] / "copyfast_partner_crm.py").read_text(encoding="utf-8")
    for forbidden_import in (
        "import bot", "from bot", "import copyfast_bridge", "from copyfast_bridge",
        "import requests", "import httpx", "import urllib", "from urllib",
        "import affiliate_ops", "from affiliate_ops", "import erp_core", "from erp_core",
        "import PayOS", "from PayOS",
    ):
        assert forbidden_import not in source


def test_partner_crm_can_be_disabled_without_creating_a_canonical_admin_backdoor(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        csrf = login(client, "partner-crm-disabled@example.com")
        assert csrf
        guarded = client.get("/api/v1/partner-crm/policy")
        assert guarded.status_code == 503
        assert "WEBAPP_PARTNER_CRM_ENABLED" in guarded.text


def test_customer_consultation_crm_is_signed_previewed_then_persisted_only_after_storage_consent(tmp_path, monkeypatch):
    """A customer intake is a closed, two-step CRM contract, never generic lead input."""

    db_path = tmp_path / "partner-crm-test.db"
    preview_payload = consultation_preview_payload()
    confirm_payload = consultation_confirm_payload()
    with make_client(tmp_path, monkeypatch) as client:
        # Every route is account-bound; the persistent stages are CSRF-bound too.
        assert client.get("/api/v1/partner-crm/consultations/catalog").status_code == 401
        assert client.post("/api/v1/partner-crm/consultations/preview", json=preview_payload).status_code == 401
        assert client.post("/api/v1/partner-crm/consultations", json=confirm_payload).status_code == 401

        owner_email = "consultation-owner@example.com"
        csrf = login(client, owner_email)
        catalog = client.get("/api/v1/partner-crm/consultations/catalog")
        assert catalog.status_code == 200 and catalog.json()["ok"] is True
        catalog_data = catalog.json()["data"]
        assert catalog.json()["status"] == "read_only"
        assert catalog_data["persistence"] == "none"
        assert catalog_data["automation"] == "none"
        assert catalog_data["contact_collection"] is False
        assert catalog_data["outbound_contact_authorized"] is False
        assert_boundary(catalog_data, persisted=False)
        assert_boundary(catalog_data["boundaries"], persisted=False)
        services = [service for group in catalog_data["groups"] for service in group["services"]]
        assert len(services) == 15
        assert len({service["id"] for service in services}) == 15
        assert preview_payload["service_id"] in {service["id"] for service in services}
        for service in services:
            assert set(service) == {"id", "group_id", "category", "title", "summary", "prompt"}
            assert not {"price", "payment", "contact_email", "telegram_id", "phone"}.intersection(service)

        assert client.post("/api/v1/partner-crm/consultations/preview", json=preview_payload).status_code == 403
        assert client.post("/api/v1/partner-crm/consultations", json=confirm_payload).status_code == 403

        # Initialise only the existing local CRM schema, then prove preview has
        # no write, audit, event or replay receipt side effect.
        assert client.get("/api/v1/partner-crm/summary").status_code == 200
        before_preview = storage_counts(db_path)
        with sqlite3.connect(db_path) as conn:
            tables_before = {str(row[0]) for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        preview = client.post(
            "/api/v1/partner-crm/consultations/preview",
            headers={"X-CSRF-Token": csrf},
            json=preview_payload,
        )
        assert preview.status_code == 200 and preview.json()["ok"] is True
        preview_body = preview.json()
        preview_data = preview_body["data"]
        assert preview_body["status"] == "awaiting_confirm"
        assert preview_data["selection"]["id"] == preview_payload["service_id"]
        assert preview_data["request"] == preview_payload
        assert preview_data["stage"] == "draft"
        assert preview_data["record_created"] is False
        assert preview_data["input_persisted"] is False
        assert preview_data["intake_consent_scope"] == "crm_draft_storage_only"
        assert preview_data["outbound_contact_authorized"] is False
        assert "lead" not in preview_data
        assert_boundary(preview_data, persisted=False)
        assert_boundary(preview_data["boundaries"], persisted=False)
        assert storage_counts(db_path) == before_preview

        # A review is not consent.  Both explicit booleans are required even
        # when the customer has already sent a valid preview payload.
        for rejected_payload in (
            consultation_confirm_payload("consultation-consent-false-0001", consent_to_store=False),
            consultation_confirm_payload("consultation-confirm-false-0001", confirm_create=False),
        ):
            rejected = client.post(
                "/api/v1/partner-crm/consultations",
                headers={"X-CSRF-Token": csrf},
                json=rejected_payload,
            )
            assert rejected.status_code == 422
        assert storage_counts(db_path) == before_preview

        created = client.post(
            "/api/v1/partner-crm/consultations",
            headers={"X-CSRF-Token": csrf},
            json=confirm_payload,
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        created_body = created.json()
        created_data = created_body["data"]
        assert created_body["status"] == "draft"
        assert created_data["lead"]["stage"] == "draft"
        assert created_data["lead"]["revision"] == 1
        assert created_data["consultation"] == {
            "service_id": preview_payload["service_id"],
            "catalog_version": catalog_data["catalog_version"],
        }
        assert created_data["intake_consent_scope"] == "crm_draft_storage_only"
        assert created_data["outbound_contact_authorized"] is False
        assert_boundary(created_data, persisted=True)
        # The replay receipt is deliberately content-free: safe metadata and
        # opaque lead state may be returned, customer narrative may not.
        assert preview_payload["request_title"] not in created.text
        assert preview_payload["need_summary"] not in created.text

        replay = client.post(
            "/api/v1/partner-crm/consultations",
            headers={"X-CSRF-Token": csrf},
            json=confirm_payload,
        )
        assert replay.status_code == 200 and replay.json() == created_body
        collision = client.post(
            "/api/v1/partner-crm/consultations",
            headers={"X-CSRF-Token": csrf},
            json=consultation_confirm_payload(
                confirm_payload["idempotency_key"],
                need_summary="Một nhu cầu video khác hẳn không thể dùng lại receipt cũ.",
            ),
        )
        assert collision.status_code == 409

        lead_id = created_data["lead"]["id"]
        # Switching to another signed account must not disclose the title,
        # summary or even distinguish the private lead from a missing one.
        login(client, "consultation-other@example.com")
        hidden = client.get(f"/api/v1/partner-crm/leads/{lead_id}")
        assert hidden.status_code == 200
        assert hidden.json()["error_code"] == "WEB_PARTNER_CRM_LEAD_NOT_FOUND"
        assert preview_payload["request_title"] not in hidden.text
        assert preview_payload["need_summary"] not in hidden.text
        assert_boundary(hidden.json()["data"], persisted=False)

    with sqlite3.connect(db_path) as conn:
        stored = conn.execute(
            """SELECT account_id, lead_name, organization, contact_email, lead_kind, opportunity_summary,
                      source_kind, source_label, tags_json, consent_status, consent_note, stage, revision
                 FROM web_partner_crm_leads"""
        ).fetchall()
        events = conn.execute(
            "SELECT action, stage, revision FROM web_partner_crm_events"
        ).fetchall()
        audit = conn.execute(
            "SELECT detail FROM web_audit_events WHERE action='web.partner_crm.consultation.create'"
        ).fetchone()
        receipt = conn.execute(
            "SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-partner-crm:%:consultation:create'"
        ).fetchone()
        tables = {str(row[0]) for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

    assert stored == [(
        account_id_for_email(db_path, "consultation-owner@example.com"),
        preview_payload["request_title"],
        "",
        "",
        "customer",
        preview_payload["need_summary"],
        "inbound",
        "Yêu cầu tư vấn Web · Video",
        json.dumps(["web-consultation", preview_payload["service_id"]], ensure_ascii=False),
        "documented",
        "Khách đã xác nhận chỉ lưu lead draft CRM trong Web; không phải consent liên hệ.",
        "draft",
        1,
    )]
    assert events == [("consultation_lead_confirmed", "draft", 1)]
    assert audit is not None
    assert "service=web-service-video;scope=crm_draft_storage_only;stage=draft" in str(audit[0])
    assert preview_payload["request_title"] not in str(audit[0])
    assert preview_payload["need_summary"] not in str(audit[0])
    assert receipt is not None
    assert preview_payload["request_title"] not in str(receipt[0])
    assert preview_payload["need_summary"] not in str(receipt[0])
    # The confirmed intake writes only to the existing CRM lead/event/audit
    # tables.  Account authentication may own unrelated tables (for example
    # Telegram link codes), so compare schema before/after instead of treating
    # an unrelated table name as an execution signal.
    assert tables == tables_before


def test_customer_consultation_crm_rejects_contact_secret_and_generic_crm_fields_without_writes(tmp_path, monkeypatch):
    """The signed account is the owner, so free text cannot become a contact channel."""

    db_path = tmp_path / "partner-crm-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "consultation-safety@example.com")
        headers = {"X-CSRF-Token": csrf}
        assert client.get("/api/v1/partner-crm/summary").status_code == 200
        before = storage_counts(db_path)

        invalid_previews = (
            consultation_preview_payload(service_id="web-unknown"),
            consultation_preview_payload(request_title="Email: customer@example.com"),
            consultation_preview_payload(need_summary="Hãy gọi số 0912345678 để cùng xem quy trình video hiện tại."),
            consultation_preview_payload(need_summary="Telegram: @consultation_team để trao đổi về video và asset."),
            consultation_preview_payload(need_summary="TXID 7f2b9a9013c4 là thông tin thanh toán không thuộc yêu cầu tư vấn."),
            consultation_preview_payload(need_summary="api_key=super-secret-value-should-not-ever-be-stored-here"),
            consultation_preview_payload(need_summary="Mã OTP 123456 chỉ để kiểm tra một cách không an toàn."),
            consultation_preview_payload(need_summary="Số thẻ 4111 1111 1111 1111 không thuộc nội dung tư vấn."),
            consultation_preview_payload(request_title="<script>alert(1)</script>"),
            consultation_preview_payload(contact_email="browser@example.com"),
            consultation_preview_payload(lead_kind="partner"),
            consultation_preview_payload(source_kind="manual"),
            consultation_preview_payload(tags=["browser-controlled"]),
            # Preview is intentionally non-persistent: accepting an
            # idempotency key here would encourage client code to route it
            # through a durable mutation helper and blur the two steps.
            consultation_preview_payload(idempotency_key="preview-must-not-have-receipt-0001"),
            consultation_preview_payload(bot_callback="menu:consultation"),
            consultation_preview_payload(telegram_state="awaiting_contact"),
        )
        for payload in invalid_previews:
            rejected = client.post(
                "/api/v1/partner-crm/consultations/preview",
                headers=headers,
                json=payload,
            )
            assert rejected.status_code == 422

        # Confirmation has the same strict intake schema plus two explicit
        # booleans.  Browser-provided CRM metadata or fake external actions
        # must fail before any idempotency/audit/lead write.
        invalid_confirms = (
            consultation_confirm_payload("consultation-extra-001", contact_email="browser@example.com"),
            consultation_confirm_payload("consultation-extra-002", stage="qualified"),
            consultation_confirm_payload("consultation-extra-003", consent_status="documented"),
            consultation_confirm_payload("consultation-extra-004", provider="fake"),
            consultation_confirm_payload("consultation-extra-005", payment_amount=100_000),
            consultation_confirm_payload("consultation-extra-006", bot_callback="callback"),
            consultation_confirm_payload("consultation-extra-007", telegram_state="pending"),
        )
        for payload in invalid_confirms:
            rejected = client.post(
                "/api/v1/partner-crm/consultations",
                headers=headers,
                json=payload,
            )
            assert rejected.status_code == 422

        assert storage_counts(db_path) == before

    with make_client(tmp_path, monkeypatch, enabled=False) as disabled:
        csrf = login(disabled, "consultation-disabled@example.com")
        headers = {"X-CSRF-Token": csrf}
        assert disabled.get("/api/v1/partner-crm/consultations/catalog").status_code == 503
        assert disabled.post(
            "/api/v1/partner-crm/consultations/preview",
            headers=headers,
            json=consultation_preview_payload(),
        ).status_code == 503
        assert disabled.post(
            "/api/v1/partner-crm/consultations",
            headers=headers,
            json=consultation_confirm_payload("consultation-disabled-0001"),
        ).status_code == 503
