"""RED contracts for revision-pinned Web Support Desk resolution feedback.

The feature belongs exclusively to the standalone Web Support Desk.  These
tests deliberately use the full FastAPI application and its SQLite store so
they can prove signed ownership, lifecycle, idempotency, redaction and
Customer Care role boundaries without touching a Bot, payment, wallet or
provider path.
"""

from __future__ import annotations

import importlib
import json
import sqlite3
import sys
import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


MODULES = [
    "app",
    "copyfast_db",
    "copyfast_auth",
    "copyfast_auth_throttle",
    "copyfast_support",
]
DATABASE_NAME = "support-resolution-feedback.db"
PASSWORD = "correct-horse-battery-staple"


def database_path(tmp_path):
    return tmp_path / DATABASE_NAME


def make_client(tmp_path, monkeypatch, *, support_enabled: bool = True) -> TestClient:
    """Create a full isolated app with the Support Desk flag set explicitly."""

    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(database_path(tmp_path)))
    monkeypatch.setenv("WEB_SESSION_SECRET", "support-resolution-feedback-test-secret")
    monkeypatch.setenv("WEBAPP_SUPPORT_DESK_ENABLED", "true" if support_enabled else "false")
    monkeypatch.delenv("WEBAPP_SUPPORT_MANAGER_EMAILS", raising=False)
    monkeypatch.delenv("WEBAPP_SUPPORT_STAFF_EMAILS", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    # Match the focused Support fixture: only modules that own the test
    # database/session/router configuration must reload between app clients.
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def register_and_login(client: TestClient, email: str, *, display_name: str = "Support Feedback Owner") -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": display_name},
    )
    assert registered.status_code == 200
    assert registered.json()["ok"] is True
    return login(client, email)


def login(client: TestClient, email: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    assert response.json()["ok"] is True
    return str(response.json()["data"]["csrf_token"])


def set_role(database, email: str, role: str) -> None:
    with sqlite3.connect(database) as conn:
        conn.execute("UPDATE web_accounts SET role_cache=? WHERE email=?", (role, email))
        conn.commit()


def account_id(database, email: str) -> str:
    with sqlite3.connect(database) as conn:
        row = conn.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()
    assert row
    return str(row[0])


def create_case(client: TestClient, csrf: str, *, key: str = "support-feedback-case-0001") -> dict:
    response = client.post(
        "/api/v1/support/cases",
        headers={"X-CSRF-Token": csrf},
        json={
            "category": "image_error",
            "priority": "high",
            "subject": "Cần xác nhận trạng thái ảnh trong Web",
            "detail": "Ảnh đã hoàn tất nhưng chưa hiện trong khu vực tài sản của Web account hiện tại.",
            "idempotency_key": key,
        },
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    return response.json()["data"]["case"]


def close_case(client: TestClient, csrf: str, case: dict, *, key: str = "support-feedback-close-0001") -> dict:
    response = client.post(
        f"/api/v1/support/cases/{case['id']}/close",
        headers={"X-CSRF-Token": csrf},
        json={
            "expected_revision": case["revision"],
            "idempotency_key": key,
            "confirm": True,
        },
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    closed = response.json()["data"]["case"]
    assert closed["state"] == "closed"
    return closed


def reopen_case(client: TestClient, csrf: str, case: dict, *, key: str = "support-feedback-reopen-0001") -> dict:
    response = client.post(
        f"/api/v1/support/cases/{case['id']}/reopen",
        headers={"X-CSRF-Token": csrf},
        json={
            "expected_revision": case["revision"],
            "idempotency_key": key,
            "confirm": True,
        },
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    reopened = response.json()["data"]["case"]
    assert reopened["state"] == "reviewing"
    return reopened


def resolve_case_as_manager(client: TestClient, database, case: dict) -> dict:
    """Use the existing staff lifecycle route rather than a test-only state edit."""

    manager_email = "resolution-feedback-manager@example.com"
    manager_csrf = register_and_login(client, manager_email, display_name="Quản lý Customer Care")
    set_role(database, manager_email, "support_manager")
    response = client.post(
        f"/api/v1/support/admin/cases/{case['id']}/update",
        headers={"X-CSRF-Token": manager_csrf},
        json={
            "state": "resolved",
            "priority": case["priority"],
            "operation_note": "Đã hoàn tất kiểm tra trạng thái hiển thị trong Web.",
            "expected_revision": case["revision"],
            "idempotency_key": "support-feedback-resolve-0001",
            "confirm": True,
        },
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    resolved = response.json()["data"]["case"]
    assert resolved["state"] == "resolved"
    return resolved


def feedback_payload(case: dict, *, key: str, **overrides) -> dict:
    payload = {
        "rating": 5,
        "comment": "Hướng dẫn rõ ràng, dễ thực hiện.",
        "expected_revision": case["revision"],
        "confirm": True,
        "idempotency_key": key,
    }
    payload.update(overrides)
    return payload


def submit_feedback(client: TestClient, csrf: str | None, case: dict, *, key: str, **overrides):
    headers = {"X-CSRF-Token": csrf} if csrf is not None else {}
    return client.post(
        f"/api/v1/support/cases/{case['id']}/resolution-feedback",
        headers=headers,
        json=feedback_payload(case, key=key, **overrides),
    )


def feedback_count(database) -> int:
    """Treat the not-yet-added table as zero so RED stays an assertion failure."""

    with sqlite3.connect(database) as conn:
        try:
            row = conn.execute("SELECT COUNT(*) FROM web_support_case_resolution_feedback").fetchone()
        except sqlite3.OperationalError as exc:
            if "no such table" not in str(exc).lower():
                raise
            return 0
    assert row
    return int(row[0])


def support_event_count(database, case_id: str) -> int:
    with sqlite3.connect(database) as conn:
        row = conn.execute("SELECT COUNT(*) FROM web_support_events WHERE case_id=?", (case_id,)).fetchone()
    assert row
    return int(row[0])


def assert_safe_receipt(receipt: dict, terminal_case: dict) -> None:
    required = {"id", "rating", "terminal_revision", "terminal_state", "submitted_at"}
    assert required <= set(receipt)
    assert set(receipt) <= {"id", "rating", "terminal_revision", "terminal_state", "submitted_at"}
    assert isinstance(receipt["id"], str) and receipt["id"]
    assert receipt["rating"] == 5
    assert receipt["terminal_revision"] == terminal_case["revision"]
    assert receipt["terminal_state"] == terminal_case["state"]
    assert isinstance(receipt["submitted_at"], str) and receipt["submitted_at"]
    assert "comment" not in receipt


def assert_guarded(response, error_code: str) -> None:
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["status"] == "guarded"
    assert body["error_code"] == error_code


def test_owner_can_submit_one_feedback_for_the_current_terminal_revision(tmp_path, monkeypatch):
    database = database_path(tmp_path)
    comment = "Hướng dẫn rõ ràng, dễ thực hiện."
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "owner-feedback@example.com")
        terminal_case = close_case(client, csrf, create_case(client, csrf))
        events_before = support_event_count(database, terminal_case["id"])

        response = submit_feedback(
            client,
            csrf,
            terminal_case,
            key="support-feedback-owner-0001",
        )

        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["status"] == "completed"
        assert body["data"]["delivery"] == "web_view_only"
        receipt = body["data"]["resolution_feedback"]
        assert_safe_receipt(receipt, terminal_case)
        assert comment not in response.text
        assert feedback_count(database) == 1

        detail = client.get(f"/api/v1/support/cases/{terminal_case['id']}")
        assert detail.status_code == 200
        assert detail.json()["data"]["case"]["state"] == "closed"
        assert detail.json()["data"]["case"]["revision"] == terminal_case["revision"]
        assert detail.json()["data"]["resolution_feedback"] == receipt
        assert comment not in detail.text
        assert support_event_count(database, terminal_case["id"]) == events_before

        with sqlite3.connect(database) as conn:
            audit_rows = conn.execute(
                "SELECT detail FROM web_audit_events WHERE action='web.support.case.resolution_feedback'"
            ).fetchall()
        assert len(audit_rows) == 1
        assert comment not in str(audit_rows[0][0])


def test_owner_can_submit_feedback_for_a_resolved_terminal_revision(tmp_path, monkeypatch):
    database = database_path(tmp_path)
    owner_email = "owner-resolved-feedback@example.com"
    with make_client(tmp_path, monkeypatch) as client:
        owner_csrf = register_and_login(client, owner_email)
        created = create_case(client, owner_csrf)
        terminal_case = resolve_case_as_manager(client, database, created)
        owner_csrf = login(client, owner_email)

        response = submit_feedback(
            client,
            owner_csrf,
            terminal_case,
            key="support-feedback-resolved-0001",
            rating=4,
        )

        assert response.status_code == 200
        receipt = response.json()["data"]["resolution_feedback"]
        assert receipt["rating"] == 4
        assert receipt["terminal_revision"] == terminal_case["revision"]
        assert receipt["terminal_state"] == "resolved"
        assert feedback_count(database) == 1


def test_resolution_feedback_requires_signed_owner_and_valid_csrf(tmp_path, monkeypatch):
    database = database_path(tmp_path)
    case_id = ""
    case_subject = ""
    with make_client(tmp_path, monkeypatch) as owner:
        owner_csrf = register_and_login(owner, "owner-feedback-boundary@example.com")
        terminal_case = close_case(owner, owner_csrf, create_case(owner, owner_csrf))
        case_id = terminal_case["id"]
        case_subject = terminal_case["subject"]

        missing_csrf = submit_feedback(
            owner,
            None,
            terminal_case,
            key="support-feedback-no-csrf-0001",
        )
        assert missing_csrf.status_code == 403
        assert missing_csrf.json()["error_code"] == "REQUEST_DENIED"
        assert feedback_count(database) == 0

        invalid_csrf = submit_feedback(
            owner,
            "not-the-signed-csrf-token",
            terminal_case,
            key="support-feedback-invalid-csrf-0001",
        )
        assert invalid_csrf.status_code == 403
        assert invalid_csrf.json()["error_code"] == "REQUEST_DENIED"
        assert feedback_count(database) == 0

    with make_client(tmp_path, monkeypatch) as anonymous:
        unsigned = anonymous.post(
            f"/api/v1/support/cases/{case_id}/resolution-feedback",
            json={
                "rating": 5,
                "comment": "Không có signed session.",
                "expected_revision": 2,
                "confirm": True,
                "idempotency_key": "support-feedback-unsigned-0001",
            },
        )
        assert unsigned.status_code == 401
        assert feedback_count(database) == 0

    with make_client(tmp_path, monkeypatch) as other:
        other_csrf = register_and_login(other, "other-feedback-owner@example.com")
        foreign = other.post(
            f"/api/v1/support/cases/{case_id}/resolution-feedback",
            headers={"X-CSRF-Token": other_csrf},
            json={
                "rating": 5,
                "comment": "Không phải chủ sở hữu case này.",
                "expected_revision": 2,
                "confirm": True,
                "idempotency_key": "support-feedback-foreign-0001",
            },
        )
        assert_guarded(foreign, "WEB_SUPPORT_CASE_NOT_FOUND")
        assert case_subject not in foreign.text
        assert "owner-feedback-boundary@example.com" not in foreign.text
        assert feedback_count(database) == 0


def test_resolution_feedback_rejects_nonterminal_and_stale_revision_without_a_row(tmp_path, monkeypatch):
    database = database_path(tmp_path)
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "feedback-lifecycle@example.com")
        active_case = create_case(client, csrf, key="support-feedback-active-case-0001")
        nonterminal = submit_feedback(
            client,
            csrf,
            active_case,
            key="support-feedback-nonterminal-0001",
        )
        assert_guarded(nonterminal, "WEB_SUPPORT_FEEDBACK_NOT_TERMINAL")
        assert feedback_count(database) == 0

        terminal_case = close_case(
            client,
            csrf,
            active_case,
            key="support-feedback-stale-close-0001",
        )
        stale = submit_feedback(
            client,
            csrf,
            terminal_case,
            key="support-feedback-stale-0001",
            expected_revision=terminal_case["revision"] - 1,
        )
        assert_guarded(stale, "WEB_SUPPORT_CASE_CONFLICT")
        assert feedback_count(database) == 0


@pytest.mark.parametrize(
    ("name", "overrides"),
    [
        ("missing_confirm", {"confirm": False}),
        ("rating_below_range", {"rating": 0}),
        ("rating_above_range", {"rating": 6}),
        ("rating_string_is_not_strict", {"rating": "5"}),
        ("revision_string_is_not_strict", {"expected_revision": "2"}),
        ("sensitive_comment", {"comment": "api_key=super-secret-token-value"}),
        ("control_character_comment", {"comment": "Dịch vụ tốt\x1b[31m"}),
        ("browser_account_id", {"account_id": "browser-must-not-select-owner"}),
    ],
)
def test_resolution_feedback_rejects_invalid_or_untrusted_input(tmp_path, monkeypatch, name, overrides):
    database = database_path(tmp_path)
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, f"feedback-invalid-{name}@example.com")
        terminal_case = close_case(client, csrf, create_case(client, csrf))
        response = submit_feedback(
            client,
            csrf,
            terminal_case,
            key=f"support-feedback-{name}-0001",
            **overrides,
        )
        assert response.status_code == 422
        assert feedback_count(database) == 0


def test_resolution_feedback_model_rejects_a_malformed_idempotency_key_before_route_work(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch):
        support_module = sys.modules["copyfast_support"]
        with pytest.raises(HTTPException) as exc_info:
            support_module.ResolutionFeedbackRequest.model_validate({
                "rating": 5,
                "comment": "",
                "expected_revision": 2,
                "confirm": True,
                "idempotency_key": "spaces are not a valid feedback key",
            })
    assert exc_info.value.status_code == 422


def test_resolution_feedback_idempotency_replays_exactly_and_rejects_conflicts(tmp_path, monkeypatch):
    database = database_path(tmp_path)
    comment = "Nhân viên giải thích rõ bước cần thực hiện tiếp theo."
    key = "support-feedback-idempotent-0001"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "feedback-idempotent@example.com")
        terminal_case = close_case(client, csrf, create_case(client, csrf))
        first = submit_feedback(client, csrf, terminal_case, key=key, comment=comment)
        assert first.status_code == 200
        first_body = first.json()
        assert first_body["ok"] is True
        assert feedback_count(database) == 1

        replay = submit_feedback(client, csrf, terminal_case, key=key, comment=comment)
        assert replay.status_code == 200
        assert replay.json()["data"]["resolution_feedback"] == first_body["data"]["resolution_feedback"]
        assert feedback_count(database) == 1

        duplicate_terminal = submit_feedback(
            client,
            csrf,
            terminal_case,
            key="support-feedback-distinct-key-0001",
            comment=comment,
        )
        assert_guarded(duplicate_terminal, "WEB_SUPPORT_FEEDBACK_EXISTS")
        assert feedback_count(database) == 1

        collision = submit_feedback(
            client,
            csrf,
            terminal_case,
            key=key,
            rating=4,
            comment="Nội dung khác không được tái sử dụng cùng idempotency key.",
        )
        assert collision.status_code == 409
        assert feedback_count(database) == 1

        with sqlite3.connect(database) as conn:
            stored = conn.execute(
                "SELECT response_json FROM web_idempotency WHERE key=?", (key,)
            ).fetchone()
        assert stored
        assert comment not in str(stored[0])


def test_resolution_feedback_storage_rejects_duplicate_terminal_revision(tmp_path, monkeypatch):
    database = database_path(tmp_path)
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "feedback-unique@example.com")
        terminal_case = close_case(client, csrf, create_case(client, csrf))
        first = submit_feedback(
            client,
            csrf,
            terminal_case,
            key="support-feedback-unique-first-0001",
        )
        assert first.status_code == 200

        with sqlite3.connect(database) as conn:
            row = conn.execute(
                """SELECT case_id, account_id, terminal_revision, terminal_state, rating, comment, created_at
                     FROM web_support_case_resolution_feedback
                     WHERE case_id=? AND terminal_revision=?""",
                (terminal_case["id"], terminal_case["revision"]),
            ).fetchone()
            assert row
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    """INSERT INTO web_support_case_resolution_feedback
                       (id, case_id, account_id, terminal_revision, terminal_state, rating, comment, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (str(uuid.uuid4()), *row),
                )
            assert conn.execute(
                "SELECT COUNT(*) FROM web_support_case_resolution_feedback WHERE case_id=?",
                (terminal_case["id"],),
            ).fetchone()[0] == 1


def test_resolution_feedback_handles_a_preexisting_terminal_unique_collision_without_500(tmp_path, monkeypatch):
    database = database_path(tmp_path)
    with make_client(tmp_path, monkeypatch) as client:
        owner_csrf = register_and_login(client, "feedback-collision-owner@example.com")
        terminal_case = close_case(client, owner_csrf, create_case(client, owner_csrf))
        register_and_login(client, "feedback-collision-other@example.com")
        other_account = account_id(database, "feedback-collision-other@example.com")
        owner_csrf = login(client, "feedback-collision-owner@example.com")

        with sqlite3.connect(database) as conn:
            conn.execute(
                """INSERT INTO web_support_case_resolution_feedback
                   (id, case_id, account_id, terminal_revision, terminal_state, rating, comment, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4()),
                    terminal_case["id"],
                    other_account,
                    terminal_case["revision"],
                    terminal_case["state"],
                    3,
                    "Dữ liệu collision đã có trước khi owner gửi đánh giá.",
                    "2026-07-29T00:00:00+00:00",
                ),
            )
            conn.commit()

        response = submit_feedback(
            client,
            owner_csrf,
            terminal_case,
            key="support-feedback-unique-collision-0001",
        )
        assert_guarded(response, "WEB_SUPPORT_FEEDBACK_EXISTS")
        assert feedback_count(database) == 1


def test_reopened_case_can_receive_feedback_only_after_a_new_terminal_revision(tmp_path, monkeypatch):
    database = database_path(tmp_path)
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "feedback-cycle@example.com")
        first_terminal = close_case(client, csrf, create_case(client, csrf))
        first = submit_feedback(
            client,
            csrf,
            first_terminal,
            key="support-feedback-cycle-first-0001",
            rating=3,
        )
        assert first.status_code == 200
        assert feedback_count(database) == 1

        reopened = reopen_case(client, csrf, first_terminal)
        blocked = submit_feedback(
            client,
            csrf,
            reopened,
            key="support-feedback-cycle-active-0001",
        )
        assert_guarded(blocked, "WEB_SUPPORT_FEEDBACK_NOT_TERMINAL")
        assert feedback_count(database) == 1

        second_terminal = close_case(
            client,
            csrf,
            reopened,
            key="support-feedback-cycle-close-second-0001",
        )
        second = submit_feedback(
            client,
            csrf,
            second_terminal,
            key="support-feedback-cycle-second-0001",
            rating=5,
        )
        assert second.status_code == 200
        receipt = second.json()["data"]["resolution_feedback"]
        assert receipt["terminal_revision"] == second_terminal["revision"]
        assert receipt["terminal_revision"] != first_terminal["revision"]
        assert feedback_count(database) == 2


def test_manager_sees_only_redacted_aggregate_and_operator_is_forbidden(tmp_path, monkeypatch):
    database = database_path(tmp_path)
    owner_email = "feedback-summary-owner@example.com"
    raw_comment = "Khách cần nhận xét này chỉ trong luồng riêng của Web Support Desk."
    with make_client(tmp_path, monkeypatch) as client:
        owner_csrf = register_and_login(client, owner_email, display_name="Khách đánh giá riêng")
        terminal_case = close_case(client, owner_csrf, create_case(client, owner_csrf))
        created = submit_feedback(
            client,
            owner_csrf,
            terminal_case,
            key="support-feedback-summary-owner-0001",
            rating=4,
            comment=raw_comment,
        )
        assert created.status_code == 200

        manager_email = "feedback-summary-manager@example.com"
        register_and_login(client, manager_email, display_name="Quản lý chất lượng")
        set_role(database, manager_email, "support_manager")
        manager = client.get("/api/v1/support/admin/care/resolution-feedback-summary?days=30")
        assert manager.status_code == 200
        body = manager.json()
        assert body["ok"] is True
        assert body["status"] == "read_only"
        data = body["data"]
        assert set(data) == {
            "window_days", "total_responses", "rating_counts", "average_rating", "comments_count", "delivery",
        }
        assert data == {
            "window_days": 30,
            "total_responses": 1,
            "rating_counts": {"1": 0, "2": 0, "3": 0, "4": 1, "5": 0},
            "average_rating": 4.0,
            "comments_count": 1,
            "delivery": "internal_metadata_only",
        }
        serialized = json.dumps(data, ensure_ascii=False)
        owner_id = account_id(database, owner_email)
        assert raw_comment not in serialized
        assert terminal_case["id"] not in serialized
        assert owner_id not in serialized
        assert owner_email not in serialized
        assert "Khách đánh giá riêng" not in serialized

        manager_detail = client.get(f"/api/v1/support/admin/cases/{terminal_case['id']}")
        assert manager_detail.status_code == 200
        assert "resolution_feedback" not in manager_detail.json()["data"]
        assert raw_comment not in manager_detail.text

        operator_email = "feedback-summary-operator@example.com"
        register_and_login(client, operator_email, display_name="Điều phối viên")
        set_role(database, operator_email, "support_operator")
        operator = client.get("/api/v1/support/admin/care/resolution-feedback-summary?days=30")
        assert operator.status_code == 403
        assert raw_comment not in operator.text
        assert terminal_case["id"] not in operator.text


def test_resolution_feedback_maintenance_flag_fails_closed_without_a_write(tmp_path, monkeypatch):
    database = database_path(tmp_path)
    owner_email = "feedback-maintenance@example.com"
    terminal_case = None
    with make_client(tmp_path, monkeypatch) as enabled:
        csrf = register_and_login(enabled, owner_email)
        terminal_case = close_case(enabled, csrf, create_case(enabled, csrf))

    assert terminal_case is not None
    with make_client(tmp_path, monkeypatch, support_enabled=False) as disabled:
        csrf = login(disabled, owner_email)
        response = submit_feedback(
            disabled,
            csrf,
            terminal_case,
            key="support-feedback-maintenance-0001",
        )
        assert response.status_code == 503
        assert response.json()["ok"] is False
        assert feedback_count(database) == 0


def test_resolution_feedback_body_cap_and_fixed_rate_scope_happen_before_router_work(tmp_path, monkeypatch):
    database = database_path(tmp_path)
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "feedback-rate-owner@example.com")
        terminal_case = close_case(client, csrf, create_case(client, csrf))
        path = f"/api/v1/support/cases/{terminal_case['id']}/resolution-feedback"
        oversized = (
            b'{"rating":5,"comment":"' + b"x" * 9000
            + b'","expected_revision":2,"confirm":true,"idempotency_key":"support-feedback-body-cap-0001"}'
        )
        too_large = client.post(
            path,
            headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
            content=oversized,
        )
        assert too_large.status_code == 413
        assert too_large.json()["error_code"] == "WEB_SUPPORT_RESOLUTION_FEEDBACK_BODY_TOO_LARGE"
        assert feedback_count(database) == 0

        malformed_path = "/api/v1/support/cases/not-a-uuid/resolution-feedback"
        for _ in range(12):
            rejected = client.post(malformed_path, content=b"{}", headers={"Content-Type": "application/json"})
            assert rejected.status_code in {401, 403, 422, 404, 405}
        limited = client.post(malformed_path, content=b"{}", headers={"Content-Type": "application/json"})
        assert limited.status_code == 429
        app_module = sys.modules["app"]
        scopes = [key for key in app_module._auth_rate_windows if key.startswith("support-resolution-feedback-write:")]
        assert len(scopes) == 1
        assert feedback_count(database) == 0
