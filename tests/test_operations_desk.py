"""Focused safety tests for the Web-native read-only ERP Operations Desk."""

from __future__ import annotations

from contextlib import contextmanager
import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient

import copyfast_operations_desk as desk


def _db() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.execute(
        """CREATE TABLE web_support_cases (
            id TEXT PRIMARY KEY, account_id TEXT, subject TEXT, initial_detail TEXT,
            state TEXT NOT NULL, priority TEXT NOT NULL, updated_at TEXT NOT NULL
        )"""
    )
    connection.execute(
        """CREATE TABLE web_ops_incidents (
            id TEXT PRIMARY KEY, support_case_id TEXT, state TEXT NOT NULL,
            severity TEXT NOT NULL, last_observed_at TEXT NOT NULL
        )"""
    )
    connection.execute(
        """CREATE TABLE web_ops_approvals (
            id TEXT PRIMARY KEY, account_id TEXT, action_type TEXT, payload_hash TEXT,
            state TEXT NOT NULL, risk TEXT NOT NULL, proposed_at TEXT NOT NULL, decided_at TEXT
        )"""
    )
    connection.execute(
        """CREATE TABLE web_ops_followups (
            id TEXT PRIMARY KEY, source_id TEXT, state TEXT NOT NULL,
            required_role TEXT NOT NULL, severity TEXT NOT NULL, updated_at TEXT NOT NULL
        )"""
    )
    connection.execute(
        """CREATE TABLE web_content_handoff_records (
            id TEXT PRIMARY KEY, account_id TEXT, title TEXT, purpose TEXT,
            handoff_status TEXT NOT NULL, record_state TEXT NOT NULL, updated_at TEXT NOT NULL
        )"""
    )
    connection.executemany(
        """INSERT INTO web_support_cases
           (id, account_id, subject, initial_detail, state, priority, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [
            ("support-private-new", "account-private", "private subject", "private detail sk_live_secret", "new", "normal", "2026-07-16T10:05:00Z"),
            ("support-private-old", "account-private", "private old", "private old detail", "resolved", "normal", "2026-07-16T10:01:00Z"),
        ],
    )
    connection.execute(
        """INSERT INTO web_ops_incidents (id, support_case_id, state, severity, last_observed_at)
           VALUES (?, ?, ?, ?, ?)""",
        ("incident-private", "support-private-new", "open", "critical", "2026-07-16T10:04:00Z"),
    )
    connection.execute(
        """INSERT INTO web_ops_approvals
           (id, account_id, action_type, payload_hash, state, risk, proposed_at, decided_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("approval-private", "account-private", "payment_finalize", "provider/payment private payload", "awaiting_approval", "financial", "2026-07-16T10:03:00Z", None),
    )
    connection.execute(
        """INSERT INTO web_ops_followups (id, source_id, state, required_role, severity, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("followup-private", "support-private-new", "open", "operator", "medium", "2026-07-16T10:02:00Z"),
    )
    connection.execute(
        """INSERT INTO web_content_handoff_records
           (id, account_id, title, purpose, handoff_status, record_state, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("handoff-private", "account-private", "private handoff title", "private handoff purpose", "review", "active", "2026-07-16T10:06:00Z"),
    )
    return connection


def _client(monkeypatch, connection: sqlite3.Connection, *, role: str = "support_operator") -> TestClient:
    app = FastAPI()
    app.include_router(desk.router)

    @contextmanager
    def read_transaction():
        yield connection

    app.dependency_overrides[desk.require_account] = lambda: {"id": "staff-private", "role": role}
    monkeypatch.setattr(desk, "read_transaction", read_transaction)
    monkeypatch.setattr(desk, "reliability_preflight_code", lambda: None)
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_SUPPORT_DESK_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_AUTOPILOT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_RELIABILITY_FOLLOWUP_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_CONTENT_HANDOFF_ENABLED", "true")
    return TestClient(app)


def test_operations_desk_requires_signed_support_staff(monkeypatch) -> None:
    connection = _db()
    with _client(monkeypatch, connection, role="customer") as client:
        response = client.get("/api/v1/admin/operations-desk/summary")
    assert response.status_code == 403


def test_operations_desk_counts_pages_and_filters_deterministically(monkeypatch) -> None:
    connection = _db()
    # Operations approvals are an explicit manager-only source.  Keep this
    # baseline aggregation test on a Manager rather than accidentally making
    # the old broad operator projection the contract.
    with _client(monkeypatch, connection, role="support_manager") as client:
        summary = client.get("/api/v1/admin/operations-desk/summary")
        first = client.get("/api/v1/admin/operations-desk/work-items?limit=2")
        second = client.get("/api/v1/admin/operations-desk/work-items?limit=2&offset=2")
        open_items = client.get("/api/v1/admin/operations-desk/work-items?state=open&limit=10")
        critical_items = client.get("/api/v1/admin/operations-desk/work-items?severity=critical&limit=10")

    assert summary.status_code == 200
    assert summary.json()["status"] == "read_only"
    assert summary.json()["data"]["summary"] == {
        "total": 6,
        "available_total": 6,
        "counts_by_kind": {
            "support_case": 2,
            "operations_incident": 1,
            "operations_approval": 1,
            "reliability_followup": 1,
            "content_handoff": 1,
        },
    }

    assert first.status_code == 200
    first_data = first.json()["data"]
    assert [item["kind"] for item in first_data["items"]] == ["content_handoff", "support_case"]
    assert first_data["total"] == 6
    assert first_data["has_more"] is True
    assert first_data["next_offset"] == 2

    second_data = second.json()["data"]
    assert [item["kind"] for item in second_data["items"]] == ["operations_incident", "operations_approval"]
    assert second_data["next_offset"] == 4

    assert [item["kind"] for item in open_items.json()["data"]["items"]] == [
        "operations_incident", "reliability_followup"
    ]
    assert [item["kind"] for item in critical_items.json()["data"]["items"]] == [
        "operations_incident", "operations_approval"
    ]


def test_operations_desk_attention_view_is_server_side_and_paginates_after_policy(monkeypatch) -> None:
    connection = _db()
    # A terminal high incident must stay outside the attention lane. This
    # proves that the fixed server policy is more precise than a browser-side
    # severity-only filter and that it runs before source count/pagination.
    connection.execute(
        """INSERT INTO web_ops_incidents (id, support_case_id, state, severity, last_observed_at)
           VALUES (?, ?, ?, ?, ?)""",
        ("incident-private-terminal", "support-private-old", "resolved", "critical", "2026-07-16T10:07:00Z"),
    )
    with _client(monkeypatch, connection, role="support_manager") as client:
        first = client.get("/api/v1/admin/operations-desk/work-items?view=attention&limit=2")
        second = client.get("/api/v1/admin/operations-desk/work-items?view=attention&limit=2&offset=2")
        support_only = client.get(
            "/api/v1/admin/operations-desk/work-items?view=attention&kind=support_case&limit=10"
        )
        terminal_intersection = client.get(
            "/api/v1/admin/operations-desk/work-items?view=attention&state=resolved&limit=10"
        )
        critical_intersection = client.get(
            "/api/v1/admin/operations-desk/work-items?view=attention&severity=critical&limit=10"
        )

    assert first.status_code == 200
    first_data = first.json()["data"]
    assert first.json()["status"] == "read_only"
    assert first.json()["message"] == "Đã nạp hàng cần xử lý Operations Desk đã redaction."
    assert [item["kind"] for item in first_data["items"]] == ["content_handoff", "support_case"]
    assert first_data["total"] == 5
    assert first_data["next_offset"] == 2

    second_data = second.json()["data"]
    assert [item["kind"] for item in second_data["items"]] == ["operations_incident", "operations_approval"]
    assert second_data["next_offset"] == 4
    assert second_data["total"] == 5

    support_items = support_only.json()["data"]["items"]
    assert [item["kind"] for item in support_items] == ["support_case"]
    assert support_items[0]["state"] == "new"
    assert terminal_intersection.json()["data"]["items"] == []
    assert [item["kind"] for item in critical_intersection.json()["data"]["items"]] == [
        "operations_incident", "operations_approval"
    ]


def test_operations_desk_operator_hides_manager_approval_source_before_counts_and_pagination(monkeypatch) -> None:
    """An operator must not infer manager approvals from a Desk total or page gap.

    The manager view proves that the source exists and pages normally.  The
    operator receives the same non-approval work, but the approval source is
    explicitly guarded with a null count and is excluded before the global
    count and pagination are calculated.  This blocks both passive dashboard
    disclosure and a direct ``kind=operations_approval`` lookup.
    """

    connection = _db()
    connection.executemany(
        """INSERT INTO web_ops_approvals
           (id, account_id, action_type, payload_hash, state, risk, proposed_at, decided_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                f"approval-manager-private-{index}",
                "account-private",
                "payment_finalize",
                f"provider/payment private payload {index}",
                "awaiting_approval",
                "financial",
                f"2026-07-16T10:0{6 + index}:00Z",
                None,
            )
            for index in range(1, 4)
        ],
    )
    connection.commit()

    with _client(monkeypatch, connection, role="support_manager") as manager:
        manager_summary = manager.get("/api/v1/admin/operations-desk/summary")
        manager_approvals = manager.get(
            "/api/v1/admin/operations-desk/work-items?kind=operations_approval&limit=10"
        )
        manager_first = manager.get("/api/v1/admin/operations-desk/work-items?limit=2&offset=0")
        manager_second = manager.get("/api/v1/admin/operations-desk/work-items?limit=2&offset=2")

    manager_sources = {source["kind"]: source for source in manager_summary.json()["data"]["sources"]}
    assert manager_summary.status_code == 200
    assert manager_summary.json()["data"]["summary"]["total"] == 9
    assert manager_sources["operations_approval"] == {
        "kind": "operations_approval", "availability": "available", "count": 4
    }
    assert manager_approvals.status_code == 200
    assert manager_approvals.json()["data"]["total"] == 4
    assert [item["kind"] for item in manager_approvals.json()["data"]["items"]] == [
        "operations_approval",
        "operations_approval",
        "operations_approval",
        "operations_approval",
    ]
    assert manager_first.json()["data"]["total"] == 9
    assert manager_first.json()["data"]["has_more"] is True
    assert manager_first.json()["data"]["next_offset"] == 2
    assert manager_second.json()["data"]["offset"] == 2

    with _client(monkeypatch, connection, role="support_operator") as operator:
        operator_summary = operator.get("/api/v1/admin/operations-desk/summary")
        operator_first = operator.get("/api/v1/admin/operations-desk/work-items?limit=2&offset=0")
        operator_second = operator.get("/api/v1/admin/operations-desk/work-items?limit=2&offset=2")
        operator_direct = operator.get(
            "/api/v1/admin/operations-desk/work-items?kind=operations_approval&limit=10"
        )

    assert operator_summary.status_code == 200
    operator_summary_data = operator_summary.json()["data"]
    operator_sources = {source["kind"]: source for source in operator_summary_data["sources"]}
    assert operator_summary.json()["status"] == "guarded"
    assert operator_summary_data["partial"] is True
    # A partial response deliberately refuses to publish a deceptively
    # complete total.  ``available_total`` is only the operator-visible work.
    assert operator_summary_data["summary"] == {
        "total": None,
        "available_total": 5,
        "counts_by_kind": {
            "support_case": 2,
            "operations_incident": 1,
            "operations_approval": None,
            "reliability_followup": 1,
            "content_handoff": 1,
        },
    }
    assert operator_sources["operations_approval"] == {
        "kind": "operations_approval", "availability": "guarded", "count": None
    }

    first_items = operator_first.json()["data"]["items"]
    second_items = operator_second.json()["data"]["items"]
    assert operator_first.status_code == 200
    assert operator_first.json()["status"] == "guarded"
    assert [item["kind"] for item in first_items] == ["content_handoff", "support_case"]
    assert [item["kind"] for item in second_items] == ["operations_incident", "reliability_followup"]
    assert operator_first.json()["data"]["total"] is None
    assert operator_first.json()["data"]["available_total"] == 5
    assert operator_first.json()["data"]["has_more"] is None
    assert operator_first.json()["data"]["next_offset"] is None
    assert all(item["kind"] != "operations_approval" for item in first_items + second_items)

    # An explicit safe enum filter is still not a lookup oracle for the
    # manager-only source: no count, item, action label or metadata survives.
    direct_data = operator_direct.json()["data"]
    assert operator_direct.status_code == 200
    assert operator_direct.json()["status"] == "guarded"
    assert direct_data["items"] == []
    assert direct_data["total"] is None
    assert direct_data["available_total"] is None
    assert direct_data["sources"] == [
        {"kind": "operations_approval", "availability": "guarded", "count": None}
    ]
    rendered = str(operator_summary.json()) + str(operator_first.json()) + str(operator_direct.json())
    for private in (
        "approval-private",
        "approval-manager-private-1",
        "payment_finalize",
        "provider/payment private payload",
    ):
        assert private not in rendered


def test_operations_desk_redacts_rows_and_uses_only_allowlisted_targets(monkeypatch) -> None:
    connection = _db()
    with _client(monkeypatch, connection, role="support_manager") as client:
        response = client.get("/api/v1/admin/operations-desk/work-items?limit=10")

    assert response.status_code == 200
    body = response.json()
    items = body["data"]["items"]
    assert {item["target_route"] for item in items} <= {
        "/admin/support", "/admin/operations", "/admin/reliability", "/admin/content-handoffs"
    }
    assert all(set(item) <= {"kind", "target_route", "state", "priority", "severity", "updated_at", "available_actions"} for item in items)
    rendered = str(body)
    for private in (
        "support-private", "incident-private", "approval-private", "followup-private", "handoff-private",
        "account-private", "private subject", "private detail", "sk_live_secret", "payment_finalize",
        "provider/payment private payload", "private handoff title", "private handoff purpose",
    ):
        assert private not in rendered
    approval = next(item for item in items if item["kind"] == "operations_approval")
    assert approval["available_actions"] == ["Xem bản ghi phê duyệt Operations"]


def test_operations_desk_never_presents_disabled_or_missing_sources_as_zero(monkeypatch) -> None:
    connection = _db()
    with _client(monkeypatch, connection) as client:
        monkeypatch.setenv("WEBAPP_AUTOPILOT_ENABLED", "false")
        disabled = client.get("/api/v1/admin/operations-desk/summary")
        monkeypatch.setenv("WEBAPP_AUTOPILOT_ENABLED", "true")
        connection.execute("DROP TABLE web_content_handoff_records")
        missing = client.get("/api/v1/admin/operations-desk/summary")
        monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "false")
        erp_disabled = client.get("/api/v1/admin/operations-desk/work-items?limit=5")

    disabled_sources = {source["kind"]: source for source in disabled.json()["data"]["sources"]}
    assert disabled.json()["status"] == "guarded"
    assert disabled_sources["operations_incident"] == {
        "kind": "operations_incident", "availability": "guarded", "count": None
    }
    assert disabled_sources["operations_approval"]["count"] is None
    assert disabled.json()["data"]["summary"]["total"] is None

    missing_sources = {source["kind"]: source for source in missing.json()["data"]["sources"]}
    assert missing.json()["status"] == "guarded"
    assert missing_sources["content_handoff"] == {
        "kind": "content_handoff", "availability": "unavailable", "count": None
    }
    assert missing.json()["data"]["summary"]["total"] is None

    erp_data = erp_disabled.json()["data"]
    assert erp_disabled.json()["status"] == "guarded"
    assert erp_data["items"] == []
    assert erp_data["total"] is None
    assert all(source["availability"] == "guarded" and source["count"] is None for source in erp_data["sources"])


def test_operations_desk_rejects_non_allowlisted_filters(monkeypatch) -> None:
    connection = _db()
    with _client(monkeypatch, connection) as client:
        invalid_kind = client.get("/api/v1/admin/operations-desk/work-items?kind=approval%27%20OR%201%3D1--")
        invalid_view = client.get("/api/v1/admin/operations-desk/work-items?view=private")
        invalid_state = client.get("/api/v1/admin/operations-desk/work-items?state=private_state")
        invalid_severity = client.get("/api/v1/admin/operations-desk/work-items?severity=secret")
        invalid_offset = client.get("/api/v1/admin/operations-desk/work-items?offset=10001")
    assert invalid_kind.status_code == 422
    assert invalid_view.status_code == 422
    assert invalid_state.status_code == 422
    assert invalid_severity.status_code == 422
    assert invalid_offset.status_code == 422
