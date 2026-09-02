"""Web-local Admin G2 for manual top-up: durable two-step reject only."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib
from pathlib import Path
import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from tests.test_copyfast_auth_api import make_client
from tests.test_web_manual_topup_unlinked_g1 import (
    _account_id,
    _register_and_login,
)


@pytest.fixture(autouse=True)
def _configured_bank_transfer(monkeypatch):
    monkeypatch.setenv("MANUAL_BANK_CODE", "ACB")
    monkeypatch.setenv("MANUAL_BANK_NAME", "Asia Commercial Bank")
    monkeypatch.setenv("MANUAL_BANK_ACCOUNT", "0387532320")
    monkeypatch.setenv("MANUAL_BANK_OWNER", "TOAN AAS")


PUBLIC_ADMIN_FIELDS = {
    "request_id",
    "display_name",
    "email",
    "amount_vnd",
    "currency",
    "method",
    "reference",
    "payment_code",
    "status",
    "submitted_at",
    "updated_at",
    "decision_at",
    "decision_reason",
}
FORBIDDEN_ADMIN_FIELDS = {
    "id",
    "account_id",
    "admin_account_id",
    "session_id",
    "canonical_user_id",
    "telegram_user_id",
    "receipt_hash",
    "claimed_idempotency_hash",
    "idempotency_key",
    "request_fingerprint",
    "expected_xu",
    "approved_xu",
    "ledger_event_id",
}


def _promote(database_path: Path, email: str) -> str:
    account_id = _account_id(database_path, email)
    with sqlite3.connect(database_path) as conn:
        conn.execute(
            "UPDATE web_accounts SET role_cache='admin', canonical_user_id=NULL WHERE id=?",
            (account_id,),
        )
    return account_id


def _create_request(client: TestClient, email: str, *, amount: int, suffix: str) -> dict:
    csrf = _register_and_login(client, email)
    response = client.post(
        "/api/v1/payments/manual",
        headers={"X-CSRF-Token": csrf},
        json={
            "amount_vnd": amount,
            "method": "bank_acb",
            "reference": f"REF-{suffix}",
            "idempotency_key": f"manual-g2-customer-{suffix}-0001",
        },
    )
    assert response.status_code == 200
    return response.json()["data"]


def _admin(client: TestClient, database_path: Path, email: str) -> tuple[str, str]:
    csrf = _register_and_login(client, email)
    return csrf, _promote(database_path, email)


def _draft(client: TestClient, request_id: str, csrf: str, reason: str) -> dict:
    response = client.post(
        f"/api/v1/admin/payments/manual/{request_id}/draft",
        headers={"X-CSRF-Token": csrf},
        json={"action": "reject", "reason": reason},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["status"] == "awaiting_confirm"
    return body["data"]


def test_web_local_admin_routes_page_list_detail_and_zero_bridge(tmp_path, monkeypatch):
    database_path = tmp_path / "g2-routes.db"
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ADMIN_WRITES_ENABLED", "true")
    with make_client(tmp_path, monkeypatch, session_database_path=database_path) as customer:
        record = _create_request(customer, "g2-customer@example.com", amount=125_000, suffix="route")
        api = importlib.import_module("copyfast_api")

        def forbidden(*_args, **_kwargs):
            raise AssertionError("G2 must not call Bot, bridge, PayOS, provider, Telegram or wallet")

        monkeypatch.setattr(api, "manual_admin_bridge_request", forbidden)
        monkeypatch.setattr(api, "bridge_request", forbidden)
        monkeypatch.setattr(api, "manual_admin_bridge_configured", forbidden)

        with TestClient(customer.app) as unsigned:
            assert unsigned.get("/admin/topups", follow_redirects=False).status_code in {307, 401}
            assert unsigned.get("/api/v1/admin/payments/manual").status_code == 401

        with TestClient(customer.app) as ordinary:
            _register_and_login(ordinary, "g2-ordinary@example.com")
            assert ordinary.get("/admin/topups").status_code == 403
            assert ordinary.get("/api/v1/admin/payments/manual").status_code == 403

        with TestClient(customer.app) as admin:
            _admin(admin, database_path, "g2-admin@example.com")
            assert admin.get("/admin/topups").status_code == 200
            listed = admin.get("/api/v1/admin/payments/manual?status=pending&limit=20")
            assert listed.status_code == 200
            assert listed.json()["data"]["items"][0]["request_id"] == record["request_id"]
            detail = admin.get(f"/api/v1/admin/payments/manual/{record['request_id']}")
            assert detail.status_code == 200
            item = detail.json()["data"]
            assert set(item) <= PUBLIC_ADMIN_FIELDS
            assert not set(item) & FORBIDDEN_ADMIN_FIELDS
            assert item["payment_code"] == record["transfer_content"]
            assert item["email"] == "g2-customer@example.com"

            for invalid in ("1", "MANUAL-0", "MANUAL-abc", "MANUAL-9999999999999999999"):
                hidden = admin.get(f"/api/v1/admin/payments/manual/{invalid}")
                assert hidden.status_code == 404
                assert hidden.json()["error_code"] == "MANUAL_ADMIN_NOT_FOUND"
            assert admin.get("/api/v1/admin/payments/manual?status=pending&status=rejected").status_code == 422
            assert admin.get("/api/v1/admin/payments/manual?unknown=1").status_code == 422

        routes = [
            (method, route.path, route.endpoint, tuple(dep.call for dep in route.dependant.dependencies))
            for route in customer.app.routes
            if getattr(route, "path", "").startswith("/api/v1/admin/payments/manual")
            for method in sorted(getattr(route, "methods", set()) or set())
        ]
        assert [(method, path) for method, path, _endpoint, _deps in routes] == [
            ("GET", "/api/v1/admin/payments/manual"),
            ("GET", "/api/v1/admin/payments/manual/{request_id}"),
            ("POST", "/api/v1/admin/payments/manual/{request_id}/draft"),
            ("POST", "/api/v1/admin/payments/manual/{request_id}/confirm"),
        ]
        assert [endpoint for _method, _path, endpoint, _deps in routes] == [
            api.manual_admin_list,
            api.manual_admin_detail,
            api.manual_admin_draft,
            api.manual_admin_confirm,
        ]


def test_reject_models_and_draft_are_closed_durable_and_no_request_mutation(tmp_path, monkeypatch):
    database_path = tmp_path / "g2-draft.db"
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ADMIN_WRITES_ENABLED", "true")
    with make_client(tmp_path, monkeypatch, session_database_path=database_path) as customer:
        record = _create_request(customer, "g2-draft-customer@example.com", amount=225_000, suffix="draft")
        api = importlib.import_module("copyfast_api")
        for payload in (
            {"action": "approve_expected"},
            {"action": "approve_custom", "approved_xu": 100, "reason": "forged"},
            {"action": "reject", "reason": "ok", "approved_xu": 100},
            {"action": "reject", "reason": "bad\nreason"},
        ):
            with pytest.raises(ValidationError):
                api.ManualAdminDraftRequest(**payload)

        with TestClient(customer.app) as admin:
            csrf, admin_id = _admin(admin, database_path, "g2-draft-admin@example.com")
            draft = _draft(admin, record["request_id"], csrf, "Không tìm thấy giao dịch khớp")
            receipt = draft["confirmation_receipt"]
            assert draft["action"] == "reject"
            assert draft["request_id"] == record["request_id"]
            assert draft["amount_vnd"] == 225_000
            assert "approved_xu" not in draft
            assert "telegram_user_id" not in draft

            with sqlite3.connect(database_path) as conn:
                status = conn.execute(
                    "SELECT status FROM web_manual_topup_requests WHERE id=?",
                    (int(record["request_id"].split("-", 1)[1]),),
                ).fetchone()[0]
                row = conn.execute(
                    """SELECT receipt_hash, admin_account_id, session_id, action, reason,
                              claimed_idempotency_hash, consumed_at
                       FROM web_manual_topup_decision_receipts"""
                ).fetchone()
                assert status == "pending_admin_review"
                assert row is not None
                assert row[0] == hashlib.sha256(receipt.encode()).hexdigest()
                assert row[1] == admin_id
                assert row[3:] == ("reject", "Không tìm thấy giao dịch khớp", None, None)
                assert receipt.encode() not in database_path.read_bytes()

            replacement = _draft(admin, record["request_id"], csrf, "Mở lại xác nhận sau khi hủy")
            assert replacement["confirmation_receipt"] != receipt
            stale = admin.post(
                f"/api/v1/admin/payments/manual/{record['request_id']}/confirm",
                headers={"X-CSRF-Token": csrf},
                json={
                    "confirmation_receipt": receipt,
                    "idempotency_key": "g2-stale-receipt-key-0001",
                },
            )
            assert stale.status_code == 404
            with sqlite3.connect(database_path) as conn:
                receipt_rows = conn.execute(
                    "SELECT receipt_hash, consumed_at FROM web_manual_topup_decision_receipts"
                ).fetchall()
                assert receipt_rows == [(
                    hashlib.sha256(replacement["confirmation_receipt"].encode()).hexdigest(),
                    None,
                )]


def test_confirm_reject_replay_binding_expiry_and_atomic_rollback(tmp_path, monkeypatch):
    database_path = tmp_path / "g2-confirm.db"
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ADMIN_WRITES_ENABLED", "true")
    with make_client(tmp_path, monkeypatch, session_database_path=database_path) as customer:
        first = _create_request(customer, "g2-confirm-customer@example.com", amount=325_000, suffix="confirm")
        second = _create_request(customer, "g2-confirm-customer@example.com", amount=425_000, suffix="second")
        with TestClient(customer.app) as admin:
            csrf, _admin_id = _admin(admin, database_path, "g2-confirm-admin@example.com")
            draft = _draft(admin, first["request_id"], csrf, "Số tiền thực nhận không khớp")
            receipt = draft["confirmation_receipt"]

            with TestClient(customer.app) as other_admin:
                other_csrf, _ = _admin(other_admin, database_path, "g2-other-admin@example.com")
                wrong_session = other_admin.post(
                    f"/api/v1/admin/payments/manual/{first['request_id']}/confirm",
                    headers={"X-CSRF-Token": other_csrf},
                    json={"confirmation_receipt": receipt, "idempotency_key": "g2-other-session-key-0001"},
                )
                assert wrong_session.status_code == 404

            wrong_request = admin.post(
                f"/api/v1/admin/payments/manual/{second['request_id']}/confirm",
                headers={"X-CSRF-Token": csrf},
                json={"confirmation_receipt": receipt, "idempotency_key": "g2-wrong-request-key-0001"},
            )
            assert wrong_request.status_code == 404

            payload = {"confirmation_receipt": receipt, "idempotency_key": "g2-confirm-key-0001"}
            confirmed = admin.post(
                f"/api/v1/admin/payments/manual/{first['request_id']}/confirm",
                headers={"X-CSRF-Token": csrf},
                json=payload,
            )
            assert confirmed.status_code == 200
            assert confirmed.json()["status"] == "rejected"
            assert confirmed.json()["data"]["status"] == "rejected"
            replay = admin.post(
                f"/api/v1/admin/payments/manual/{first['request_id']}/confirm",
                headers={"X-CSRF-Token": csrf},
                json=payload,
            )
            assert replay.status_code == 200
            assert replay.json()["data"]["idempotent_replay"] is True
            conflict = admin.post(
                f"/api/v1/admin/payments/manual/{first['request_id']}/confirm",
                headers={"X-CSRF-Token": csrf},
                json={**payload, "idempotency_key": "g2-conflicting-key-0002"},
            )
            assert conflict.status_code == 409
            assert conflict.json()["error_code"] == "MANUAL_ADMIN_IDEMPOTENCY_CONFLICT"

            rollback_draft = _draft(admin, second["request_id"], csrf, "Lỗi đối soát cần rollback")
            with sqlite3.connect(database_path) as conn:
                conn.execute(
                    """CREATE TRIGGER fail_manual_reject_audit BEFORE INSERT ON web_audit_events
                       WHEN NEW.action='admin.manual_topup.reject'
                       BEGIN SELECT RAISE(ABORT, 'forced audit failure'); END"""
                )
            failed = admin.post(
                f"/api/v1/admin/payments/manual/{second['request_id']}/confirm",
                headers={"X-CSRF-Token": csrf},
                json={
                    "confirmation_receipt": rollback_draft["confirmation_receipt"],
                    "idempotency_key": "g2-rollback-key-0001",
                },
            )
            assert failed.status_code == 503
            with sqlite3.connect(database_path) as conn:
                second_number = int(second["request_id"].split("-", 1)[1])
                assert conn.execute(
                    "SELECT status FROM web_manual_topup_requests WHERE id=?", (second_number,)
                ).fetchone()[0] == "pending_admin_review"
                assert conn.execute(
                    "SELECT consumed_at FROM web_manual_topup_decision_receipts WHERE manual_topup_id=?",
                    (second_number,),
                ).fetchone()[0] is None
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                assert not any(name.startswith("web_wallet") for name in tables)
                conn.execute("DROP TRIGGER fail_manual_reject_audit")

        db = importlib.import_module("copyfast_db")
        helper = getattr(db, "confirm_web_manual_topup_reject")
        customer_csrf = customer.get("/api/v1/auth/me").json()["data"]["csrf_token"]
        third_response = customer.post(
            "/api/v1/payments/manual",
            headers={"X-CSRF-Token": customer_csrf},
            json={
                "amount_vnd": 525_000,
                "method": "bank_acb",
                "reference": "REF-concurrent",
                "idempotency_key": "manual-g2-customer-concurrent-0001",
            },
        )
        assert third_response.status_code == 200
        third = third_response.json()["data"]
        with TestClient(customer.app) as admin_again:
            login = admin_again.post(
                "/api/v1/auth/login",
                json={
                    "email": "g2-confirm-admin@example.com",
                    "password": "correct-horse-battery-staple",
                },
            )
            assert login.status_code == 200 and login.json()["ok"] is True
            csrf = str(login.json()["data"]["csrf_token"])
            admin_id = _account_id(database_path, "g2-confirm-admin@example.com")
            draft = _draft(admin_again, third["request_id"], csrf, "Từ chối đồng thời")
            receipt_hash = hashlib.sha256(draft["confirmation_receipt"].encode()).hexdigest()
            key_hash = hashlib.sha256(b"g2-concurrent-key-0001").hexdigest()
            with sqlite3.connect(database_path) as conn:
                session_id = conn.execute(
                    "SELECT id FROM web_sessions WHERE account_id=? AND revoked_at IS NULL ORDER BY created_at DESC LIMIT 1",
                    (admin_id,),
                ).fetchone()[0]
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(
                    lambda _index: helper(
                        request_number=int(third["request_id"].split("-", 1)[1]),
                        admin_account_id=admin_id,
                        session_id=session_id,
                        receipt_hash=receipt_hash,
                        idempotency_key_hash=key_hash,
                        audit_request_id="g2-concurrency-audit",
                    ),
                    range(2),
                ))
            assert {item["status"] for item in results} == {"rejected"}
            assert sum(item.get("idempotent_replay") is True for item in results) == 1

            expired_response = customer.post(
                "/api/v1/payments/manual",
                headers={"X-CSRF-Token": customer_csrf},
                json={
                    "amount_vnd": 625_000,
                    "method": "bank_acb",
                    "reference": "REF-expired",
                    "idempotency_key": "manual-g2-customer-expired-0001",
                },
            )
            assert expired_response.status_code == 200
            expired_record = expired_response.json()["data"]
            expired_draft = _draft(admin_again, expired_record["request_id"], csrf, "Biên nhận hết hạn")
            expired_number = int(expired_record["request_id"].split("-", 1)[1])
            with sqlite3.connect(database_path) as conn:
                conn.execute(
                    "UPDATE web_manual_topup_decision_receipts SET expires_at='2000-01-01T00:00:00+00:00' WHERE manual_topup_id=?",
                    (expired_number,),
                )
            expired = admin_again.post(
                f"/api/v1/admin/payments/manual/{expired_record['request_id']}/confirm",
                headers={"X-CSRF-Token": csrf},
                json={
                    "confirmation_receipt": expired_draft["confirmation_receipt"],
                    "idempotency_key": "g2-expired-key-0001",
                },
            )
            assert expired.status_code == 409
            assert expired.json()["error_code"] == "MANUAL_ADMIN_CONFIRMATION_EXPIRED"
            with sqlite3.connect(database_path) as conn:
                assert conn.execute(
                    "SELECT status FROM web_manual_topup_requests WHERE id=?", (expired_number,)
                ).fetchone()[0] == "pending_admin_review"
                assert conn.execute(
                    "SELECT consumed_at FROM web_manual_topup_decision_receipts WHERE manual_topup_id=?",
                    (expired_number,),
                ).fetchone()[0] is None


def test_confirm_sanitizes_browser_request_id_and_persists_no_raw_secret(tmp_path, monkeypatch):
    database_path = tmp_path / "g2-audit-sanitized.db"
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ADMIN_WRITES_ENABLED", "true")
    unsafe_request_id = "RAW_SECRET_MARKER_APIKEY_20260901"
    raw_idempotency_key = "g2-audit-idempotency-secret-0001"

    with make_client(tmp_path, monkeypatch, session_database_path=database_path) as customer:
        record = _create_request(
            customer,
            "g2-audit-customer@example.com",
            amount=725_000,
            suffix="audit-sanitized",
        )
        with TestClient(customer.app) as admin:
            csrf, _ = _admin(admin, database_path, "g2-audit-admin@example.com")
            draft = _draft(admin, record["request_id"], csrf, "Không tìm thấy giao dịch")
            response = admin.post(
                f"/api/v1/admin/payments/manual/{record['request_id']}/confirm",
                headers={
                    "X-CSRF-Token": csrf,
                    "X-Request-ID": unsafe_request_id,
                },
                json={
                    "confirmation_receipt": draft["confirmation_receipt"],
                    "idempotency_key": raw_idempotency_key,
                },
            )
            assert response.status_code == 200
            assert response.json()["status"] == "rejected"

    with sqlite3.connect(database_path) as conn:
        audit_rows = conn.execute(
            """SELECT request_id, action, target, outcome, detail
               FROM web_audit_events
               WHERE action='admin.manual_topup.reject'"""
        ).fetchall()
    assert len(audit_rows) == 1
    audit_request_id, action, target, outcome, detail = audit_rows[0]
    assert str(uuid.UUID(audit_request_id)) == audit_request_id
    assert (action, target, outcome, detail) == (
        "admin.manual_topup.reject",
        record["request_id"],
        "rejected",
        "web_local_reject_only",
    )
    database_bytes = database_path.read_bytes()
    assert unsafe_request_id.encode() not in database_bytes
    assert raw_idempotency_key.encode() not in database_bytes
    assert draft["confirmation_receipt"].encode() not in database_bytes


@pytest.mark.parametrize("session_state", ["revoked", "expired"])
def test_confirm_fails_closed_when_current_admin_session_is_invalid(
    tmp_path, monkeypatch, session_state
):
    database_path = tmp_path / f"g2-session-{session_state}.db"
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ADMIN_WRITES_ENABLED", "true")

    with make_client(tmp_path, monkeypatch, session_database_path=database_path) as customer:
        record = _create_request(
            customer,
            f"g2-{session_state}-customer@example.com",
            amount=825_000,
            suffix=session_state,
        )
        request_number = int(record["request_id"].split("-", 1)[1])
        with TestClient(customer.app) as admin:
            csrf, admin_id = _admin(
                admin,
                database_path,
                f"g2-{session_state}-admin@example.com",
            )
            draft = _draft(admin, record["request_id"], csrf, "Phiên phải còn hiệu lực")
            with sqlite3.connect(database_path) as conn:
                session_id = conn.execute(
                    """SELECT id FROM web_sessions
                       WHERE account_id=? AND revoked_at IS NULL
                       ORDER BY created_at DESC LIMIT 1""",
                    (admin_id,),
                ).fetchone()[0]
                if session_state == "revoked":
                    conn.execute(
                        "UPDATE web_sessions SET revoked_at='2026-09-01T00:00:00+00:00' WHERE id=?",
                        (session_id,),
                    )
                else:
                    conn.execute(
                        "UPDATE web_sessions SET expires_at='2000-01-01T00:00:00+00:00' WHERE id=?",
                        (session_id,),
                    )

            response = admin.post(
                f"/api/v1/admin/payments/manual/{record['request_id']}/confirm",
                headers={"X-CSRF-Token": csrf},
                json={
                    "confirmation_receipt": draft["confirmation_receipt"],
                    "idempotency_key": f"g2-{session_state}-confirm-key-0001",
                },
            )
            assert response.status_code == 401

    with sqlite3.connect(database_path) as conn:
        assert conn.execute(
            "SELECT status FROM web_manual_topup_requests WHERE id=?",
            (request_number,),
        ).fetchone()[0] == "pending_admin_review"
        assert conn.execute(
            "SELECT consumed_at FROM web_manual_topup_decision_receipts WHERE manual_topup_id=?",
            (request_number,),
        ).fetchone()[0] is None
        assert conn.execute(
            "SELECT COUNT(*) FROM web_audit_events WHERE action='admin.manual_topup.reject'"
        ).fetchone()[0] == 0


def test_web_local_admin_navigation_publishes_one_reject_only_topup_module(
    tmp_path, monkeypatch
):
    database_path = tmp_path / "g2-navigation.db"
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
    with make_client(tmp_path, monkeypatch, session_database_path=database_path) as admin:
        _admin(admin, database_path, "g2-navigation-admin@example.com")
        response = admin.get("/api/v1/admin/navigation")
        assert response.status_code == 200
        payload = response.json()
        assert payload["data"]["access"]["web_local_admin"] is True
        assert payload["data"]["access"]["canonical_admin"] is False
        modules = [
            module
            for group in payload["data"]["groups"]
            for module in group["modules"]
            if module["route"] == "/admin/topups"
        ]
    assert len(modules) == 1
    assert {key: modules[0][key] for key in (
        "id", "title", "route", "authority", "source", "availability", "capability"
    )} == {
        "id": "manual_topups",
        "title": "Đối soát nạp thủ công",
        "route": "/admin/topups",
        "authority": "web_local_admin",
        "source": "web_native",
        "availability": "web_native",
        "capability": "manual_topup_reject_only",
    }

    navigation = importlib.import_module("copyfast_admin_erp_navigation")
    assert all(
        module["route"] != "/admin/topups"
        for group in navigation.canonical_groups()
        for module in group["modules"]
    )
