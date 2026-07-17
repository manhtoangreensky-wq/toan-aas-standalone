"""Focused safety tests for the Web-owned Admin Audit Explorer."""

from __future__ import annotations

from contextlib import contextmanager
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import copyfast_admin_audit as audit


def _db() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.execute(
        """CREATE TABLE web_audit_events (
            id TEXT PRIMARY KEY, account_id TEXT, canonical_user_id TEXT,
            action TEXT NOT NULL, request_id TEXT NOT NULL, target TEXT,
            outcome TEXT NOT NULL, detail TEXT, created_at TEXT NOT NULL
        )"""
    )
    connection.executemany(
        """INSERT INTO web_audit_events
           (id, account_id, canonical_user_id, action, request_id, target, outcome, detail, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            ("1", "customer-private", "telegram-private", "web.support.case.create", "request-private", "case-private", "ok", "customer text and secret sk_live_private", "2026-07-15T10:00:00Z"),
            ("2", "admin-private", "telegram-admin", "web.admin.refund", "request-admin", "job-private", "denied", "payment reference private", "2026-07-15T09:00:00Z"),
            ("3", "customer-private", "telegram-private", "unreviewed.internal.workflow", "request-other", "target-other", "ok", "unreviewed detail", "2026-07-15T08:00:00Z"),
        ],
    )
    return connection


def _client(monkeypatch, connection: sqlite3.Connection, *, canonical: bool = True) -> TestClient:
    app = FastAPI()
    app.include_router(audit.router)

    @contextmanager
    def transaction():
        yield connection

    async def canonical_admin(_request):
        if not canonical:
            raise HTTPException(status_code=403, detail="denied")
        return {"id": "admin", "role": "admin"}

    monkeypatch.setattr(audit, "ensure_copyfast_schema", lambda: None)
    monkeypatch.setattr(audit, "transaction", transaction)
    monkeypatch.setattr(audit, "require_canonical_admin", canonical_admin)
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
    return TestClient(app)


def test_audit_explorer_requires_live_canonical_admin(monkeypatch) -> None:
    connection = _db()
    with _client(monkeypatch, connection, canonical=False) as client:
        response = client.get("/api/v1/admin/audit-events")
    assert response.status_code == 403


def test_audit_explorer_redacts_all_sensitive_audit_columns(monkeypatch) -> None:
    connection = _db()
    with _client(monkeypatch, connection) as client:
        response = client.get("/api/v1/admin/audit-events?limit=10")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["status"] == "read_only"
    events = body["data"]["events"]
    assert len(events) == 3
    assert events[0] == {
        "category": "support",
        "category_label": "CSKH",
        "event_label": "Tạo case CSKH",
        "state": "completed",
        "outcome_label": "Đã ghi nhận",
        "created_at": "2026-07-15T10:00:00Z",
        "source": "web_audit_events_redacted",
    }
    rendered = str(body["data"])
    for secret in ("customer-private", "telegram-private", "request-private", "case-private", "sk_live_private", "payment reference private", "unreviewed.internal.workflow"):
        assert secret not in rendered
    assert events[1]["category"] == "admin"
    assert events[1]["state"] == "guarded"
    assert events[2]["event_label"] == "Sự kiện Web · sự kiện đã redaction"


def test_audit_explorer_category_is_allowlisted_and_uses_no_raw_search(monkeypatch) -> None:
    connection = _db()
    with _client(monkeypatch, connection) as client:
        response = client.get("/api/v1/admin/audit-events?category=support&limit=1")
        invalid = client.get("/api/v1/admin/audit-events?category=admin%27%20OR%201%3D1--")

    assert response.status_code == 200
    assert response.json()["data"]["summary"] == {
        "returned": 1,
        "completed": 1,
        "guarded": 0,
        "read_only": 0,
        "category": "support",
    }
    assert invalid.status_code == 422


def test_audit_explorer_category_pages_are_bounded_and_redacted(monkeypatch) -> None:
    """Category paging cannot expose a raw owner or audit record at any offset."""

    connection = _db()
    connection.executemany(
        """INSERT INTO web_audit_events
           (id, account_id, canonical_user_id, action, request_id, target, outcome, detail, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                f"security-{index:03d}",
                f"owner-private-{index}",
                f"telegram-private-{index}",
                "web.security.reviewed",
                f"request-private-{index}",
                f"target-private-{index}",
                "ok" if index % 2 else "guarded",
                f"secret-detail-{index}",
                f"2026-07-16T{index // 60:02d}:{index % 60:02d}:00Z",
            )
            for index in range(101)
        ],
    )

    with _client(monkeypatch, connection) as client:
        pages = []
        for offset, expected_count, has_more, next_offset in ((0, 50, True, 50), (50, 50, True, 100), (100, 1, False, None)):
            response = client.get(f"/api/v1/admin/audit-events?category=security&limit=50&offset={offset}")
            assert response.status_code == 200
            body = response.json()
            data = body["data"]
            assert data["has_more"] is has_more
            assert data["next_offset"] == next_offset
            assert data["summary"]["category"] == "security"
            assert data["summary"]["returned"] == expected_count
            assert len(data["events"]) == expected_count
            assert all(event["category"] == "security" for event in data["events"])
            assert all(event["source"] == "web_audit_events_redacted" for event in data["events"])
            rendered = str(data)
            for private in ("owner-private-", "telegram-private-", "request-private-", "target-private-", "secret-detail-"):
                assert private not in rendered
            pages.append(data["events"])

    # Created timestamps are safe, reviewed presentation metadata; the three
    # pages must still represent all 101 filtered records without repeats.
    timestamps = [event["created_at"] for page in pages for event in page]
    assert len(timestamps) == 101
    assert len(set(timestamps)) == 101


def test_audit_explorer_rejects_invalid_offsets_and_guarded_reads_have_no_cursor(monkeypatch) -> None:
    connection = _db()
    with _client(monkeypatch, connection) as client:
        negative = client.get("/api/v1/admin/audit-events?offset=-1")
        too_large = client.get("/api/v1/admin/audit-events?offset=10001")
        invalid_category = client.get("/api/v1/admin/audit-events?category=other")
    assert negative.status_code == 422
    assert too_large.status_code == 422
    assert invalid_category.status_code == 422

    with _client(monkeypatch, connection) as client:
        monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "false")
        guarded = client.get("/api/v1/admin/audit-events?category=asset&offset=50")
    assert guarded.status_code == 200
    data = guarded.json()["data"]
    assert guarded.json()["status"] == "guarded"
    assert data["events"] == []
    assert data["has_more"] is False
    assert data["next_offset"] is None
    assert data["summary"] == {
        "returned": 0,
        "completed": 0,
        "guarded": 0,
        "read_only": 0,
        "category": "asset",
    }
