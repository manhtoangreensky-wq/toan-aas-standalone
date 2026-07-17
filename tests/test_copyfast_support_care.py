"""Focused contract coverage for Web-native Customer Care controls.

The test deliberately exercises only Support Desk metadata.  It proves that
queue/assignment/SLA/escalation changes stay server-authorized, revisioned,
idempotent and invisible to the customer projection.
"""

from __future__ import annotations

import importlib
import sqlite3
import sys

from fastapi.testclient import TestClient


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "copyfast-support-care.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-support-care-session-secret")
    monkeypatch.setenv("WEBAPP_SUPPORT_DESK_ENABLED", "true")
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in tuple(sys.modules):
        if name == "app" or name.startswith("copyfast_"):
            sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def register_and_login(client: TestClient, email: str, display_name: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "correct-horse-battery-staple",
            "display_name": display_name,
        },
    )
    assert registered.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    return str(login.json()["data"]["csrf_token"])


def account_id(database, email: str) -> str:
    with sqlite3.connect(database) as conn:
        row = conn.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()
    assert row
    return str(row[0])


def set_role(database, email: str, role: str) -> None:
    with sqlite3.connect(database) as conn:
        conn.execute("UPDATE web_accounts SET role_cache=? WHERE email=?", (role, email))
        conn.commit()


def create_case(client: TestClient, csrf: str) -> dict:
    response = client.post(
        "/api/v1/support/cases",
        headers={"X-CSRF-Token": csrf},
        json={
            "category": "image_error",
            "priority": "high",
            "subject": "Ảnh chưa xuất hiện trong kho tài sản",
            "detail": "Yêu cầu chỉ cần Customer Care rà soát trạng thái hiển thị trong Web.",
            "idempotency_key": "care-case-create-0001",
        },
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    return response.json()["data"]["case"]


def test_customer_care_triage_and_escalation_are_private_revisioned_and_server_authorized(tmp_path, monkeypatch):
    database = tmp_path / "copyfast-support-care.db"
    with make_client(tmp_path, monkeypatch) as customer:
        customer_csrf = register_and_login(customer, "care-customer@example.com", "Khách Customer Care")
        case = create_case(customer, customer_csrf)
    with sqlite3.connect(database) as conn:
        waiting_since_before = conn.execute(
            "SELECT customer_waiting_since FROM web_support_cases WHERE id=?", (case["id"],)
        ).fetchone()
    assert waiting_since_before and waiting_since_before[0]

    with make_client(tmp_path, monkeypatch) as operator:
        operator_csrf = register_and_login(operator, "care-operator@example.com", "Điều phối viên")
        set_role(database, "care-operator@example.com", "support_operator")
        operator_id = account_id(database, "care-operator@example.com")

        # A signed operator can work existing cases but cannot view a roster
        # or route a case to another member merely by sending an account id.
        roster_denied = operator.get("/api/v1/support/admin/care/staff")
        assert roster_denied.status_code == 403
        triage_denied = operator.post(
            f"/api/v1/support/admin/cases/{case['id']}/care/triage",
            headers={"X-CSRF-Token": operator_csrf},
            json={
                "team_queue": "technical",
                "assigned_account_id": operator_id,
                "sla_class": "priority",
                "operation_note": "Không được phép tự điều phối hàng đợi.",
                "expected_revision": 1,
                "idempotency_key": "care-operator-triage-0001",
                "confirm": True,
            },
        )
        assert triage_denied.status_code == 403

        # Operators may raise an internal escalation, but cannot acknowledge
        # or resolve one.  No customer message is created by this operation.
        escalation_reason = "Cần quản lý Customer Care rà soát nguyên nhân nội bộ."
        escalation_requested = operator.post(
            f"/api/v1/support/admin/cases/{case['id']}/care/escalation",
            headers={"X-CSRF-Token": operator_csrf},
            json={
                "escalation_state": "requested",
                "reason": escalation_reason,
                "expected_revision": 1,
                "idempotency_key": "care-escalation-request-0001",
                "confirm": True,
            },
        )
        assert escalation_requested.status_code == 200
        assert escalation_requested.json()["data"]["case"]["revision"] == 2
        assert escalation_requested.json()["data"]["case"]["care"]["escalation"]["state"] == "requested"
        acknowledgement_denied = operator.post(
            f"/api/v1/support/admin/cases/{case['id']}/care/escalation",
            headers={"X-CSRF-Token": operator_csrf},
            json={
                "escalation_state": "acknowledged",
                "reason": "Không được phép tự xác nhận escalation.",
                "expected_revision": 2,
                "idempotency_key": "care-escalation-ack-denied-0001",
                "confirm": True,
            },
        )
        assert acknowledgement_denied.status_code == 403

    with make_client(tmp_path, monkeypatch) as manager:
        manager_csrf = register_and_login(manager, "care-manager@example.com", "Quản lý Customer Care")
        set_role(database, "care-manager@example.com", "support_manager")

        roster = manager.get("/api/v1/support/admin/care/staff")
        assert roster.status_code == 200
        roster_items = roster.json()["data"]["items"]
        assert any(item["id"] == operator_id and item["role"] == "operator" for item in roster_items)
        assert "@example.com" not in str(roster_items)

        missing_csrf = manager.post(
            f"/api/v1/support/admin/cases/{case['id']}/care/triage",
            json={
                "team_queue": "technical",
                "assigned_account_id": operator_id,
                "sla_class": "priority",
                "operation_note": "Không có CSRF.",
                "expected_revision": 2,
                "idempotency_key": "care-triage-no-csrf-0001",
                "confirm": True,
            },
        )
        assert missing_csrf.status_code == 403
        missing_confirm = manager.post(
            f"/api/v1/support/admin/cases/{case['id']}/care/triage",
            headers={"X-CSRF-Token": manager_csrf},
            json={
                "team_queue": "technical",
                "assigned_account_id": operator_id,
                "sla_class": "priority",
                "operation_note": "Chưa xác nhận thao tác.",
                "expected_revision": 2,
                "idempotency_key": "care-triage-no-confirm-0001",
                "confirm": False,
            },
        )
        assert missing_confirm.status_code == 422

        triage_payload = {
            "team_queue": "technical",
            "assigned_account_id": operator_id,
            "sla_class": "priority",
            "operation_note": "Điều phối vào hàng đợi kỹ thuật để xử lý nội bộ.",
            "expected_revision": 2,
            "idempotency_key": "care-triage-manager-0001",
            "confirm": True,
        }
        triage = manager.post(
            f"/api/v1/support/admin/cases/{case['id']}/care/triage",
            headers={"X-CSRF-Token": manager_csrf},
            json=triage_payload,
        )
        assert triage.status_code == 200
        triaged_case = triage.json()["data"]["case"]
        assert triaged_case["revision"] == 3
        assert triaged_case["care"]["team_queue"] == "technical"
        assert triaged_case["care"]["assignee"]["id"] == operator_id
        assert triaged_case["care"]["sla"]["class"] == "priority"
        assert triaged_case["care"]["sla"]["scope"] == "internal_triage_only"

        # Same key and fingerprint is safe to replay; a changed request with
        # the key fails before creating a second staff-side assignment event.
        replay = manager.post(
            f"/api/v1/support/admin/cases/{case['id']}/care/triage",
            headers={"X-CSRF-Token": manager_csrf},
            json=triage_payload,
        )
        assert replay.status_code == 200
        assert replay.json()["data"]["case"]["revision"] == 3
        collision = manager.post(
            f"/api/v1/support/admin/cases/{case['id']}/care/triage",
            headers={"X-CSRF-Token": manager_csrf},
            json={**triage_payload, "team_queue": "product"},
        )
        assert collision.status_code == 409

        queues = manager.get("/api/v1/support/admin/care/queues")
        assert queues.status_code == 200
        technical = next(item for item in queues.json()["data"]["items"] if item["team_queue"] == "technical")
        assert technical["total"] == 1
        assert technical["escalated"] == 1
        assert queues.json()["data"]["delivery"] == "internal_metadata_only"

        acknowledged = manager.post(
            f"/api/v1/support/admin/cases/{case['id']}/care/escalation",
            headers={"X-CSRF-Token": manager_csrf},
            json={
                "escalation_state": "acknowledged",
                "reason": "Quản lý đã tiếp nhận escalation nội bộ.",
                "expected_revision": 3,
                "idempotency_key": "care-escalation-ack-0001",
                "confirm": True,
            },
        )
        assert acknowledged.status_code == 200
        assert acknowledged.json()["data"]["case"]["revision"] == 4
        resolved = manager.post(
            f"/api/v1/support/admin/cases/{case['id']}/care/escalation",
            headers={"X-CSRF-Token": manager_csrf},
            json={
                "escalation_state": "resolved",
                "reason": "Đã hoàn tất rà soát metadata nội bộ.",
                "expected_revision": 4,
                "idempotency_key": "care-escalation-resolve-0001",
                "confirm": True,
            },
        )
        assert resolved.status_code == 200
        assert resolved.json()["data"]["case"]["care"]["escalation"]["state"] == "resolved"

        detail = manager.get(f"/api/v1/support/admin/cases/{case['id']}")
        assert detail.status_code == 200
        detail_data = detail.json()["data"]
        assert detail_data["case"]["care"]["escalation"]["reason"] == "Đã hoàn tất rà soát metadata nội bộ."
        assert [item["action"] for item in detail_data["care_history"]] == ["requested", "updated", "acknowledged", "resolved"]

    with make_client(tmp_path, monkeypatch) as customer_again:
        customer_login = customer_again.post(
            "/api/v1/auth/login",
            json={"email": "care-customer@example.com", "password": "correct-horse-battery-staple"},
        )
        assert customer_login.status_code == 200
        owner_detail = customer_again.get(f"/api/v1/support/cases/{case['id']}")
        assert owner_detail.status_code == 200
        owner_data = owner_detail.json()["data"]
        assert "care" not in owner_data["case"]
        assert "care_history" not in owner_data
        assert escalation_reason not in owner_detail.text
        assert all(message["author_role"] == "customer" for message in owner_data["messages"])

    with sqlite3.connect(database) as conn:
        audit_rows = conn.execute(
            "SELECT detail FROM web_audit_events WHERE action LIKE 'web.support.admin.care.%'"
        ).fetchall()
        waiting_since_after_internal_care = conn.execute(
            "SELECT customer_waiting_since FROM web_support_cases WHERE id=?", (case["id"],)
        ).fetchone()
    assert audit_rows
    assert all(escalation_reason not in str(row[0]) for row in audit_rows)
    # Assignment and internal escalation must not look like a customer-facing
    # response or reset the semantic SLA clock.
    assert waiting_since_after_internal_care == waiting_since_before


def test_customer_waiting_clock_changes_only_for_public_service_turns(tmp_path, monkeypatch):
    """A public operator response clears the wait; a customer reply starts it again."""

    database = tmp_path / "copyfast-support-care.db"
    customer_email = "care-sla-clock-customer@example.com"
    with make_client(tmp_path, monkeypatch) as customer:
        customer_csrf = register_and_login(customer, customer_email, "Khách SLA Clock")
        case = create_case(customer, customer_csrf)
    with sqlite3.connect(database) as conn:
        initial_clock = conn.execute(
            "SELECT customer_waiting_since FROM web_support_cases WHERE id=?", (case["id"],)
        ).fetchone()
    assert initial_clock and initial_clock[0]

    with make_client(tmp_path, monkeypatch) as manager:
        manager_csrf = register_and_login(manager, "care-sla-clock-manager@example.com", "Quản lý SLA Clock")
        set_role(database, "care-sla-clock-manager@example.com", "support_manager")
        reply = manager.post(
            f"/api/v1/support/admin/cases/{case['id']}/reply",
            headers={"X-CSRF-Token": manager_csrf},
            json={
                "body": "Đã xem yêu cầu trên Web và cần bạn xác nhận thêm một chi tiết.",
                "visibility": "public",
                "next_state": "waiting_user",
                "expected_revision": 1,
                "idempotency_key": "care-sla-clock-public-reply-0001",
                "confirm": True,
            },
        )
        assert reply.status_code == 200 and reply.json()["data"]["case"]["revision"] == 2
    with sqlite3.connect(database) as conn:
        assert conn.execute(
            "SELECT customer_waiting_since FROM web_support_cases WHERE id=?", (case["id"],)
        ).fetchone() == (None,)

    with make_client(tmp_path, monkeypatch) as customer_again:
        customer_csrf = customer_again.post(
            "/api/v1/auth/login",
            json={"email": customer_email, "password": "correct-horse-battery-staple"},
        ).json()["data"]["csrf_token"]
        response = customer_again.post(
            f"/api/v1/support/cases/{case['id']}/reply",
            headers={"X-CSRF-Token": customer_csrf},
            json={
                "body": "Tôi đã bổ sung chi tiết để Customer Care tiếp tục xử lý trên Web.",
                "expected_revision": 2,
                "idempotency_key": "care-sla-clock-customer-reply-0001",
            },
        )
        assert response.status_code == 200 and response.json()["data"]["case"]["revision"] == 3
    with sqlite3.connect(database) as conn:
        restarted_clock = conn.execute(
            "SELECT customer_waiting_since FROM web_support_cases WHERE id=?", (case["id"],)
        ).fetchone()
    assert restarted_clock and restarted_clock[0]
