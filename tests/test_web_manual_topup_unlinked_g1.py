"""Web-native manual top-up G1: account code and pending request only."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import importlib
import json
from pathlib import Path
import sqlite3
import sys
import uuid

import pytest
from fastapi.testclient import TestClient

from tests.test_copyfast_auth_api import make_client


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(
    encoding="utf-8"
)

ROUTE_CONTRACTS = {
    ("GET", "/api/v1/payments/options"): "payment_options",
    ("POST", "/api/v1/payments/manual"): "manual_topup_create",
    ("GET", "/api/v1/payments/manual"): "manual_topup_history",
    ("GET", "/api/v1/payments/manual/{request_id}"): "manual_topup_detail",
    ("GET", "/api/v1/payments/manual/{request_id}/status"): "manual_topup_status",
}
PUBLIC_REQUEST_KEYS = {
    "request_id",
    "amount_vnd",
    "currency",
    "method",
    "reference",
    "transfer_content",
    "status",
    "submitted_at",
    "updated_at",
}
FORBIDDEN_PUBLIC_KEYS = {
    "id",
    "account_id",
    "idempotency_key",
    "idempotency_key_hash",
    "request_fingerprint",
    "expected_xu",
    "approved_xu",
    "admin_id",
    "decided_by_account_id",
    "ledger_event_id",
}


@pytest.fixture(autouse=True)
def _configured_bank_transfer(monkeypatch):
    monkeypatch.setenv("MANUAL_BANK_CODE", "ACB")
    monkeypatch.setenv("MANUAL_BANK_NAME", "Asia Commercial Bank")
    monkeypatch.setenv("MANUAL_BANK_ACCOUNT", "0387532320")
    monkeypatch.setenv("MANUAL_BANK_OWNER", "TOAN AAS")


def _register_and_login(client: TestClient, email: str) -> str:
    assert client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "correct-horse-battery-staple",
            "display_name": "Manual top-up QA",
        },
    ).json()["ok"] is True
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    assert login.json()["ok"] is True
    return str(login.json()["data"]["csrf_token"])


def _database_modules() -> tuple[object, object]:
    return importlib.import_module("copyfast_db"), importlib.import_module("copyfast_api")


def _account_id(database_path: Path, email: str) -> str:
    with sqlite3.connect(database_path) as conn:
        row = conn.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()
    assert row is not None
    return str(row[0])


def _manual_routes(application) -> dict[tuple[str, str], list[object]]:
    result: dict[tuple[str, str], list[object]] = {}
    for route in application.routes:
        path = str(getattr(route, "path", ""))
        for method in set(getattr(route, "methods", set()) or set()):
            key = (str(method), path)
            if key in ROUTE_CONTRACTS:
                result.setdefault(key, []).append(route)
    return result


def test_routes_are_unique_and_bound_to_exported_web_local_handlers(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        _, api = _database_modules()
        routes = _manual_routes(client.app)
        assert set(routes) == set(ROUTE_CONTRACTS)
        for key, endpoint_name in ROUTE_CONTRACTS.items():
            assert len(routes[key]) == 1, key
            assert routes[key][0].endpoint is getattr(api, endpoint_name)


def test_signed_wallet_topup_hydrates_manual_metadata_without_telegram_link():
    marker = 'if (account && currentPath === "/wallet/topup") {'
    assert marker in INTEGRATION
    assert 'if (account && telegramLinked && currentPath === "/wallet/topup") {' not in INTEGRATION
    section = INTEGRATION[
        INTEGRATION.index(marker) : INTEGRATION.index(marker) + 220
    ]
    assert "await hydratePaymentOptions();" in section
    assert "await hydrateManualTopupHistory();" in section


def test_unlinked_options_publish_one_stable_web_code_and_vnd_methods(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBAPP_PAYMENT_ENABLED", "true")
    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "https://bridge.test")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "bridge-token-not-called")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "bridge-hmac-not-called")
    with make_client(tmp_path, monkeypatch) as client:
        csrf = _register_and_login(client, "manual-unlinked@example.com")
        assert csrf

        first = client.get("/api/v1/payments/options")
        second = client.get("/api/v1/payments/options")
        assert first.status_code == second.status_code == 200
        manual = first.json()["data"]["manual"]
        assert manual == second.json()["data"]["manual"]
        assert manual["available"] is True
        assert manual["history_in_web"] is True
        assert manual["support_hotline"] == "0898360858"
        assert manual["payment_code"].isascii()
        assert manual["payment_code"].isdigit()
        assert len(manual["payment_code"]) == 8
        assert [item["id"] for item in manual["methods"]] == [
            "bank_acb",
            "bank_acb_vietqr",
            "zalopay_personal",
            "zalopay_merchant",
            "momo_tuithantai",
        ]
        assert {item["currency"] for item in manual["methods"]} == {"VND"}
        for forbidden in ("telegram_url", "command", "receipt_channel", "history_command"):
            assert forbidden not in manual

        payos = first.json()["data"]["payos"]
        assert payos["request_enabled"] is False
        assert payos["checkout_owner"] == "canonical_bot"

        rejected_usd = client.post(
            "/api/v1/payments/manual",
            headers={"X-CSRF-Token": csrf},
            json={
                "amount_vnd": 100_000,
                "method": "usdt_trc20",
                "reference": "USD-MUST-BE-SEPARATE",
                "idempotency_key": "manual-usd-rejected-0001",
            },
        )
        assert rejected_usd.status_code == 422
        with sqlite3.connect(tmp_path / "copyfast-test.db") as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_manual_topup_requests").fetchone()[0] == 0


def test_code_allocation_is_persistent_ascii_and_serialized(tmp_path, monkeypatch):
    database_path = tmp_path / "manual-code.db"
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(database_path))
    db = importlib.import_module("copyfast_db")
    db.ensure_copyfast_schema()
    account_id = str(uuid.uuid4())
    now = db.utc_now()
    with db.transaction() as conn:
        conn.execute(
            """INSERT INTO web_accounts
               (id, email, password_hash, display_name, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (account_id, "code-owner@example.com", "hash", "Code owner", now, now),
        )

    allocator = getattr(db, "get_or_create_web_topup_code")
    with ThreadPoolExecutor(max_workers=8) as pool:
        codes = list(pool.map(lambda _: allocator(account_id), range(16)))
    assert len(set(codes)) == 1
    code = codes[0]
    assert code == "10000000"
    assert allocator(account_id) == code
    with sqlite3.connect(database_path) as conn:
        rows = conn.execute(
            "SELECT account_id, payment_code FROM web_account_topup_codes"
        ).fetchall()
    assert rows == [(account_id, code)]


def test_schema_is_hash_only_and_financial_delivery_remains_absent(tmp_path, monkeypatch):
    database_path = tmp_path / "manual-schema.db"
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(database_path))
    db = importlib.import_module("copyfast_db")
    db.ensure_copyfast_schema()
    with sqlite3.connect(database_path) as conn:
        code_sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='web_account_topup_codes'"
        ).fetchone()[0]
        request_sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='web_manual_topup_requests'"
        ).fetchone()[0]
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(web_manual_topup_requests)")
        }
        table_names = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }

    normalized_code = " ".join(str(code_sql).split())
    normalized_request = " ".join(str(request_sql).split())
    assert "length(payment_code) = 8" in normalized_code
    assert "payment_code NOT GLOB '*[^0-9]*'" in normalized_code
    assert "length(idempotency_key_hash) = 64" in normalized_request
    assert "idempotency_key_hash NOT GLOB '*[^0-9a-f]*'" in normalized_request
    assert "length(request_fingerprint) = 64" in normalized_request
    assert "request_fingerprint NOT GLOB '*[^0-9a-f]*'" in normalized_request
    assert "idempotency_key" not in columns
    assert {"idempotency_key_hash", "request_fingerprint"} <= columns
    assert not any(name.startswith("web_wallet") for name in table_names)
    assert "web_wallet_ledger_events" not in table_names


def test_create_replay_conflict_owner_scope_redaction_and_zero_external_calls(tmp_path, monkeypatch):
    database_path = tmp_path / "copyfast-test.db"
    with make_client(tmp_path, monkeypatch, session_database_path=database_path) as owner:
        csrf = _register_and_login(owner, "manual-owner@example.com")
        db, api = _database_modules()

        def forbidden_call(*_args, **_kwargs):
            raise AssertionError("G1 must not call bridge, PayOS, provider, Telegram, or wallet")

        monkeypatch.setattr(api, "_manual_topup_bridge", forbidden_call)
        monkeypatch.setattr(api, "bridge_request", forbidden_call)
        monkeypatch.setattr(api, "manual_admin_bridge_request", forbidden_call)
        monkeypatch.setattr(api, "_create_payos_checkout", forbidden_call)

        options = owner.get("/api/v1/payments/options")
        payment_code = options.json()["data"]["manual"]["payment_code"]
        raw_key = "manual-web-local-key-0001"
        payload = {
            "amount_vnd": 125_000,
            "method": "bank_acb",
            "reference": "TX-125",
            "idempotency_key": raw_key,
        }
        created = owner.post(
            "/api/v1/payments/manual",
            headers={"X-CSRF-Token": csrf},
            json=payload,
        )
        assert created.status_code == 200
        record = created.json()["data"]
        assert set(record) == PUBLIC_REQUEST_KEYS
        assert not (set(record) & FORBIDDEN_PUBLIC_KEYS)
        assert record["request_id"].startswith("MANUAL-")
        assert record["status"] == "pending_admin_review"
        assert record["currency"] == "VND"
        assert record["transfer_content"] == payment_code
        datetime.fromisoformat(record["submitted_at"])
        datetime.fromisoformat(record["updated_at"])

        replay = owner.post(
            "/api/v1/payments/manual",
            headers={"X-CSRF-Token": csrf},
            json=payload,
        )
        assert replay.status_code == 200
        assert replay.json()["data"]["request_id"] == record["request_id"]
        assert replay.json()["data"]["idempotent_replay"] is True

        conflict = owner.post(
            "/api/v1/payments/manual",
            headers={"X-CSRF-Token": csrf},
            json={**payload, "amount_vnd": 126_000},
        )
        assert conflict.status_code == 409
        assert conflict.json()["error_code"] == "MANUAL_TOPUP_IDEMPOTENCY_CONFLICT"

        history = owner.get("/api/v1/payments/manual?limit=20")
        assert history.status_code == 200
        assert history.json()["data"]["items"] == [record]
        detail = owner.get(f"/api/v1/payments/manual/{record['request_id']}")
        assert detail.status_code == 200
        assert detail.json()["data"] == record
        status = owner.get(
            f"/api/v1/payments/manual/{record['request_id']}/status"
        )
        assert status.status_code == 200
        assert status.json()["data"] == {
            "request_id": record["request_id"],
            "status": "pending_admin_review",
        }

        with sqlite3.connect(database_path) as conn:
            stored = conn.execute(
                """SELECT idempotency_key_hash, request_fingerprint, COUNT(*)
                   FROM web_manual_topup_requests GROUP BY idempotency_key_hash, request_fingerprint"""
            ).fetchone()
        assert stored is not None
        assert stored[0] == hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        assert len(stored[0]) == len(stored[1]) == 64
        assert stored[2] == 1
        assert raw_key.encode("utf-8") not in database_path.read_bytes()

        with TestClient(owner.app) as foreign:
            foreign_csrf = _register_and_login(foreign, "manual-foreign@example.com")
            assert foreign_csrf
            hidden = foreign.get(
                f"/api/v1/payments/manual/{record['request_id']}"
            )
            assert hidden.status_code == 404
            assert hidden.json()["error_code"] == "MANUAL_TOPUP_NOT_FOUND"

        for invalid in (
            "1",
            "MANUAL-0",
            "MANUAL--1",
            "MANUAL-abc",
            "MANUAL-9999999999999999999",
            "MANUAL-" + "1" * 20,
        ):
            response = owner.get(f"/api/v1/payments/manual/{invalid}")
            assert response.status_code == 404
            assert response.json()["error_code"] == "MANUAL_TOPUP_NOT_FOUND"


def test_read_helpers_never_open_a_write_transaction(tmp_path, monkeypatch):
    database_path = tmp_path / "manual-readonly.db"
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(database_path))
    db = importlib.import_module("copyfast_db")
    db.ensure_copyfast_schema()
    account_id = str(uuid.uuid4())
    now = db.utc_now()
    with db.transaction() as conn:
        conn.execute(
            """INSERT INTO web_accounts
               (id, email, password_hash, display_name, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (account_id, "read-owner@example.com", "hash", "Read owner", now, now),
        )
    code = db.get_or_create_web_topup_code(account_id)
    key_hash = hashlib.sha256(b"manual-read-key-0001").hexdigest()
    fingerprint = hashlib.sha256(b"manual-read-fingerprint").hexdigest()
    created = db.create_web_manual_topup_request(
        account_id=account_id,
        amount_vnd=50_000,
        method="bank_acb",
        reference="READ-ONLY",
        idempotency_key_hash=key_hash,
        request_fingerprint=fingerprint,
    )
    assert created["transfer_content"] == code

    def forbidden_write():
        raise AssertionError("read helper opened a write transaction")

    monkeypatch.setattr(db, "transaction", forbidden_write)
    rows = db.list_web_manual_topup_requests(account_id, limit=20)
    detail = db.get_web_manual_topup_request(
        account_id, int(created["request_id"].split("-", 1)[1])
    )
    assert rows == [{key: value for key, value in created.items() if key != "idempotent_replay"}]
    assert detail == rows[0]


def test_concurrent_manual_create_is_one_request_and_one_terminal_replay(tmp_path, monkeypatch):
    database_path = tmp_path / "manual-concurrent.db"
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(database_path))
    db = importlib.import_module("copyfast_db")
    db.ensure_copyfast_schema()
    account_id = str(uuid.uuid4())
    now = db.utc_now()
    with db.transaction() as conn:
        conn.execute(
            """INSERT INTO web_accounts
               (id, email, password_hash, display_name, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (account_id, "concurrent@example.com", "hash", "Concurrent", now, now),
        )
    key_hash = hashlib.sha256(b"manual-concurrent-key").hexdigest()
    fingerprint = hashlib.sha256(b"manual-concurrent-fingerprint").hexdigest()

    def create_once(_index: int) -> dict:
        return db.create_web_manual_topup_request(
            account_id=account_id,
            amount_vnd=88_000,
            method="bank_acb_vietqr",
            reference="CONCURRENT",
            idempotency_key_hash=key_hash,
            request_fingerprint=fingerprint,
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(create_once, range(16)))
    assert len({item["request_id"] for item in results}) == 1
    assert sum(item.get("idempotent_replay") is not True for item in results) == 1
    with sqlite3.connect(database_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM web_manual_topup_requests").fetchone()[0] == 1


def test_manual_create_enforces_three_pending_requests_but_preserves_replay(
    tmp_path, monkeypatch
):
    database_path = tmp_path / "manual-pending-limit.db"
    with make_client(tmp_path, monkeypatch, session_database_path=database_path) as client:
        csrf = _register_and_login(client, "pending-limit@example.com")
        payloads = [
            {
                "amount_vnd": 100_000 + index,
                "method": "bank_acb",
                "reference": f"LIMIT-{index}",
                "idempotency_key": f"manual-pending-limit-key-{index:04d}",
            }
            for index in range(4)
        ]
        created = [
            client.post(
                "/api/v1/payments/manual",
                headers={"X-CSRF-Token": csrf},
                json=payload,
            )
            for payload in payloads[:3]
        ]
        assert [response.status_code for response in created] == [200, 200, 200]

        replay = client.post(
            "/api/v1/payments/manual",
            headers={"X-CSRF-Token": csrf},
            json=payloads[0],
        )
        assert replay.status_code == 200
        assert replay.json()["data"]["idempotent_replay"] is True

        blocked = client.post(
            "/api/v1/payments/manual",
            headers={"X-CSRF-Token": csrf},
            json=payloads[3],
        )
        assert blocked.status_code == 429
        assert blocked.json()["status"] == "guarded"
        assert blocked.json()["error_code"] == "MANUAL_TOPUP_PENDING_LIMIT"

        account_id = _account_id(database_path, "pending-limit@example.com")
        with sqlite3.connect(database_path) as conn:
            rows = conn.execute(
                """SELECT id, status FROM web_manual_topup_requests
                   WHERE account_id=? ORDER BY id""",
                (account_id,),
            ).fetchall()
            assert len(rows) == 3
            assert {status for _request_id, status in rows} == {"pending_admin_review"}
            conn.execute(
                "UPDATE web_manual_topup_requests SET status='rejected' WHERE id=?",
                (rows[0][0],),
            )

        admitted = client.post(
            "/api/v1/payments/manual",
            headers={"X-CSRF-Token": csrf},
            json=payloads[3],
        )
        assert admitted.status_code == 200
        assert admitted.json()["data"]["status"] == "pending_admin_review"

    with sqlite3.connect(database_path) as conn:
        assert conn.execute(
            """SELECT COUNT(*) FROM web_manual_topup_requests
               WHERE account_id=? AND status='pending_admin_review'""",
            (account_id,),
        ).fetchone()[0] == 3


def test_manual_create_has_one_fixed_twelve_request_rate_bucket(tmp_path, monkeypatch):
    database_path = tmp_path / "manual-route-rate.db"
    with make_client(tmp_path, monkeypatch, session_database_path=database_path) as client:
        csrf = _register_and_login(client, "route-rate@example.com")
        payload = {
            "amount_vnd": 150_000,
            "method": "bank_acb",
            "reference": "ROUTE-RATE",
            "idempotency_key": "manual-route-rate-key-0001",
        }
        responses = [
            client.post(
                "/api/v1/payments/manual",
                headers={"X-CSRF-Token": csrf},
                json=payload,
            )
            for _index in range(12)
        ]
        assert [response.status_code for response in responses] == [200] * 12
        assert responses[0].json()["data"].get("idempotent_replay") is not True
        assert all(
            response.json()["data"].get("idempotent_replay") is True
            for response in responses[1:]
        )

        blocked = client.post(
            "/api/v1/payments/manual/",
            headers={"X-CSRF-Token": csrf},
            json=payload,
        )
        assert blocked.status_code == 429
        assert blocked.json()["status"] == "guarded"
        assert blocked.json()["error_code"] == "MANUAL_TOPUP_RATE_LIMITED"

    with sqlite3.connect(database_path) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM web_manual_topup_requests"
        ).fetchone()[0] == 1


def test_manual_pending_limit_serializes_concurrent_distinct_requests(tmp_path, monkeypatch):
    database_path = tmp_path / "manual-pending-concurrent.db"
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(database_path))
    db = importlib.import_module("copyfast_db")
    db.ensure_copyfast_schema()
    account_id = str(uuid.uuid4())
    now = db.utc_now()
    with db.transaction() as conn:
        conn.execute(
            """INSERT INTO web_accounts
               (id, email, password_hash, display_name, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (account_id, "pending-concurrent@example.com", "hash", "Concurrent", now, now),
        )

    def request_values(index: int) -> tuple[str, str, str]:
        key = f"pending-concurrent-key-{index:04d}"
        reference = f"CONCURRENT-{index}"
        canonical = json.dumps(
            {"amount_vnd": 200_000 + index, "method": "bank_acb", "reference": reference},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return key, reference, hashlib.sha256(canonical).hexdigest()

    for index in range(2):
        key, reference, fingerprint = request_values(index)
        db.create_web_manual_topup_request(
            account_id=account_id,
            amount_vnd=200_000 + index,
            method="bank_acb",
            reference=reference,
            idempotency_key_hash=hashlib.sha256(key.encode()).hexdigest(),
            request_fingerprint=fingerprint,
        )

    def create_distinct(index: int) -> str:
        key, reference, fingerprint = request_values(index)
        try:
            db.create_web_manual_topup_request(
                account_id=account_id,
                amount_vnd=200_000 + index,
                method="bank_acb",
                reference=reference,
                idempotency_key_hash=hashlib.sha256(key.encode()).hexdigest(),
                request_fingerprint=fingerprint,
            )
            return "created"
        except db.WebManualTopupPendingLimit:
            return "limited"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = sorted(pool.map(create_distinct, (2, 3)))
    assert outcomes == ["created", "limited"]
    with sqlite3.connect(database_path) as conn:
        assert conn.execute(
            """SELECT COUNT(*) FROM web_manual_topup_requests
               WHERE account_id=? AND status='pending_admin_review'""",
            (account_id,),
        ).fetchone()[0] == 3
