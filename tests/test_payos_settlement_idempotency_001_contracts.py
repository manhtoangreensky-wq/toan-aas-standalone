"""Focused contracts for PAYOS-SETTLEMENT-IDEMPOTENCY-001."""
from __future__ import annotations
import hashlib, json, random, sqlite3, sys, types
from pathlib import Path

import anyio
import pytest
from fastapi import HTTPException
from starlette.requests import Request

import copyfast_api as api
from copyfast_api import PaymentRequest

ROOT = Path(__file__).resolve().parents[1]
API_SOURCE = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static/portal/integration.js").read_text(encoding="utf-8")
ACCOUNT_A, ACCOUNT_B = ({"id": "web-account-A", "canonical_user_id": "telegram-1"}, {"id": "web-account-B", "canonical_user_id": "telegram-2"})
UNLINKED_ACCOUNT = {"id": "web-account-U"}
# Mirrors the canonical Bot schema: 19 base columns plus 25 additive columns.
CANONICAL_PAYOS_SCHEMA = """
CREATE TABLE payos_orders (
 order_code TEXT PRIMARY KEY, user_id TEXT, amount INTEGER, xu INTEGER,
 package_amount_vnd INTEGER DEFAULT 0, base_xu INTEGER DEFAULT 0,
 launch_bonus_xu INTEGER DEFAULT 0, order_type TEXT DEFAULT 'topup',
 plan_id TEXT DEFAULT '', plan_name TEXT DEFAULT '', duration_days INTEGER DEFAULT 0,
 plan_xu INTEGER DEFAULT 0, metadata_json TEXT DEFAULT '', status TEXT DEFAULT 'PENDING',
 created_at DATETIME, expires_at DATETIME, paid_at DATETIME, checkout_url TEXT,
 payment_link_id TEXT, payment_type TEXT DEFAULT 'topup_xu', package_id TEXT DEFAULT '',
 apply_status TEXT DEFAULT '', apply_error TEXT DEFAULT '', invoice_type TEXT DEFAULT '',
 payment_channel TEXT DEFAULT '', currency TEXT DEFAULT 'VND',
 subtotal_amount_vnd INTEGER DEFAULT 0, vat_rate REAL DEFAULT 0,
 vat_amount_vnd INTEGER DEFAULT 0, total_amount_vnd INTEGER DEFAULT 0,
 fx_rate REAL DEFAULT 1, original_amount REAL DEFAULT 0,
 original_currency TEXT DEFAULT 'VND', vat_mode TEXT DEFAULT '', tax_category TEXT DEFAULT '',
 anomaly_reason TEXT DEFAULT '', approved_by_admin_id TEXT DEFAULT '', granted_at TEXT DEFAULT '',
 user_market_snapshot TEXT DEFAULT '', payment_market TEXT DEFAULT '',
 payment_transaction_id TEXT DEFAULT '', domestic_eligibility INTEGER DEFAULT 0,
 successful_topup_ordinal INTEGER DEFAULT 0, base_credit_applied INTEGER DEFAULT 0
);
"""

def _request(path: str = "/api/v1/payments/create") -> Request:
    return Request({"type": "http", "method": "POST", "path": path, "headers": []})

def _enable_direct_checkout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api, "_flags", lambda: {"payment_enabled": True})
    monkeypatch.setattr(api, "_payment_topup_packages", lambda: [{
        "code": "topup_10k", "label": "10.000 đ", "amount_vnd": 10_000,
        "xu": 100, "available": True,
    }])
    monkeypatch.setattr(api, "_payos_config", lambda: {
        "client_id": "stub-client", "api_key": "stub-api", "checksum": "stub-checksum",
    })


def _canonical_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, list[sqlite3.Connection]]:
    path = tmp_path / "canonical-payments.db"
    with sqlite3.connect(path) as conn:
        conn.executescript(CANONICAL_PAYOS_SCHEMA)
        assert len(conn.execute("PRAGMA table_info(payos_orders)").fetchall()) == 44
    opened: list[sqlite3.Connection] = []

    def connect() -> sqlite3.Connection:
        conn = sqlite3.connect(path, timeout=1)
        opened.append(conn)
        return conn

    module = types.ModuleType("db")
    module.db_connect = connect
    module.now_text = lambda: "2026-08-26 00:00:00"
    monkeypatch.setitem(sys.modules, "db", module)
    return path, opened

def _insert_order(path: Path, *, order_code: str, owner: str, status: str = "PENDING",
                  checkout_url: str = "https://pay.payos.vn/checkout/order", metadata: str = "") -> None:
    with sqlite3.connect(path) as conn:
        conn.execute(
            "INSERT INTO payos_orders (order_code,user_id,amount,xu,status,checkout_url,metadata_json,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (order_code, owner, 10_000, 100, status, checkout_url, metadata, "2026-08-26"),
        )

def _direct_idempotency(monkeypatch: pytest.MonkeyPatch) -> None:
    async def run_once(scope: str, key: str, operation):
        return await operation()
    monkeypatch.setattr(api, "_run_transient_idempotent", run_once)

def _single_flight(monkeypatch: pytest.MonkeyPatch) -> None:
    pending: set[tuple[str, str]] = set()

    def reserve(scope: str, key: str) -> tuple[str, str]:
        identity = (scope, key)
        if identity in pending:
            return "pending", ""
        pending.add(identity)
        return "owner", "marker"

    monkeypatch.setattr(api, "_reserve_transient_idempotency", reserve)
    monkeypatch.setattr(api, "_release_idempotency", lambda scope, key, marker: pending.discard((scope, key)))


@pytest.mark.anyio
async def test_unlinked_account_is_blocked_before_db_or_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable_direct_checkout(monkeypatch)
    provider_calls = []
    monkeypatch.setattr(api, "_create_payos_checkout", lambda *args, **kwargs: provider_calls.append(True))
    module = types.ModuleType("db")
    module.db_connect = lambda: pytest.fail("DB must not open for an unlinked account")
    monkeypatch.setitem(sys.modules, "db", module)
    with pytest.raises(HTTPException) as exc_info:
        await api.create_payment(
            PaymentRequest(package_id="topup_10k", payment_type="topup_xu", idempotency_key="unlinked-key-01"),
            _request(), UNLINKED_ACCOUNT,
        )
    assert exc_info.value.status_code == 409
    assert provider_calls == []


@pytest.mark.anyio
async def test_sequential_retry_uses_one_provider_order_and_hashed_metadata(monkeypatch, tmp_path) -> None:
    _enable_direct_checkout(monkeypatch)
    path, _ = _canonical_db(monkeypatch, tmp_path)
    _direct_idempotency(monkeypatch)
    provider_calls = 0
    order_calls = 0

    async def provider_stub(*args, **kwargs):
        nonlocal provider_calls
        provider_calls += 1
        return {"code": "00", "data": {"checkoutUrl": "https://pay.payos.vn/checkout/order?source=web", "paymentLinkId": "link-1"}}

    def order_stub(start: int, end: int) -> int:
        nonlocal order_calls
        order_calls += 1
        return 12345678

    monkeypatch.setattr(api, "_create_payos_checkout", provider_stub)
    monkeypatch.setattr(random, "randint", order_stub)
    payload = PaymentRequest(package_id="topup_10k", payment_type="topup_xu", idempotency_key="retry-key-0123")
    first = await api.create_payment(payload, _request(), ACCOUNT_A)
    second = await api.create_payment(payload, _request(), ACCOUNT_A)
    assert first["data"]["order_code"] == second["data"]["order_code"] == 12345678
    assert first["data"]["checkout_url"] == second["data"]["checkout_url"]
    assert provider_calls == order_calls == 1
    with sqlite3.connect(path) as conn:
        rows = conn.execute("SELECT order_code,user_id,amount,xu,order_type,status,checkout_url,payment_link_id,currency,metadata_json FROM payos_orders").fetchall()
    assert len(rows) == 1
    metadata = json.loads(rows[0][-1])
    assert metadata == {"source": "web", "web_idempotency_hash": hashlib.sha256(b"telegram-1:retry-key-0123").hexdigest()}
    assert "retry-key-0123" not in rows[0][-1]


@pytest.mark.anyio
async def test_retry_revalidates_stored_checkout_url_without_provider_call(monkeypatch, tmp_path) -> None:
    _enable_direct_checkout(monkeypatch)
    path, _ = _canonical_db(monkeypatch, tmp_path)
    _direct_idempotency(monkeypatch)
    key = "unsafe-retry-key-01"
    digest = hashlib.sha256(f"telegram-1:{key}".encode()).hexdigest()
    stored_metadata = json.dumps({"source": "web", "web_idempotency_hash": digest}, separators=(",", ":"), sort_keys=True)
    _insert_order(path, order_code="900001", owner="telegram-1", checkout_url="https://evil.example/checkout", metadata=stored_metadata)
    provider_calls = []
    monkeypatch.setattr(api, "_create_payos_checkout", lambda *args, **kwargs: provider_calls.append(True))
    result = await api.create_payment(
        PaymentRequest(package_id="topup_10k", payment_type="topup_xu", idempotency_key=key),
        _request(), ACCOUNT_A,
    )
    assert result["ok"] is False
    assert result["error_code"] == "PAYOS_CHECKOUT_URL_INVALID"
    assert "checkout_url" not in result.get("data", {})
    assert provider_calls == []


@pytest.mark.anyio
async def test_lookup_db_failure_is_stable_closes_connection_and_leaks_nothing(
    monkeypatch, tmp_path, caplog, capsys,
) -> None:
    _enable_direct_checkout(monkeypatch)
    _, opened = _canonical_db(monkeypatch, tmp_path)
    module = sys.modules["db"]
    original_connect = module.db_connect

    def denied_connect() -> sqlite3.Connection:
        conn = original_connect()
        conn.set_authorizer(lambda action, arg1, *args: sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_READ and arg1 == "payos_orders" else sqlite3.SQLITE_OK)
        return conn

    module.db_connect = denied_connect
    result = await api.create_payment(
        PaymentRequest(package_id="topup_10k", payment_type="topup_xu", idempotency_key="db-lookup-fail-01"),
        _request(), ACCOUNT_A,
    )
    assert result["ok"] is False
    assert result["error_code"] == "PAYMENT_ORDER_PERSISTENCE_FAILED"
    leaked = f"{result} {caplog.text} {capsys.readouterr()}".lower()
    assert "prohibited" not in leaked and "not authorized" not in leaked
    with pytest.raises(sqlite3.ProgrammingError):
        opened[-1].execute("SELECT 1")


@pytest.mark.anyio
async def test_provider_exception_is_stable_and_lookup_connection_is_closed(monkeypatch, tmp_path) -> None:
    _enable_direct_checkout(monkeypatch)
    path, opened = _canonical_db(monkeypatch, tmp_path)
    provider_error = True

    async def provider_stub(*args, **kwargs):
        if provider_error:
            raise RuntimeError("private-provider-detail")
        return {"code": "00", "data": {"checkoutUrl": "https://pay.payos.vn/checkout/insert-fail"}}

    monkeypatch.setattr(api, "_create_payos_checkout", provider_stub)
    result = await api.create_payment(
        PaymentRequest(package_id="topup_10k", payment_type="topup_xu", idempotency_key="provider-fail-001"),
        _request(), ACCOUNT_A,
    )
    assert result["error_code"] == "PAYOS_EXCEPTION"
    assert "private-provider-detail" not in str(result)
    with pytest.raises(sqlite3.ProgrammingError):
        opened[0].execute("SELECT 1")
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TRIGGER reject_order BEFORE INSERT ON payos_orders BEGIN SELECT RAISE(ABORT, 'private-db-detail'); END")
    provider_error = False
    failed_insert = await api.create_payment(
        PaymentRequest(package_id="topup_10k", payment_type="topup_xu", idempotency_key="insert-fail-key-01"), _request(), ACCOUNT_A,
    )
    assert failed_insert["error_code"] == "PAYMENT_ORDER_PERSISTENCE_FAILED"
    assert "private-db-detail" not in str(failed_insert) and "checkout_url" not in failed_insert.get("data", {})


@pytest.mark.anyio
async def test_foreign_owner_never_falls_through_to_canonical_bridge(monkeypatch, tmp_path) -> None:
    path, _ = _canonical_db(monkeypatch, tmp_path)
    _insert_order(path, order_code="ORD123", owner="telegram-1")
    bridge_calls = []

    async def bridge_stub(*args, **kwargs):
        bridge_calls.append((args, kwargs))
        return {"ok": True, "data": {"order_code": "ORD123", "amount_vnd": 10_000}}

    monkeypatch.setattr(api, "_canonical_companion_ready", lambda account: True)
    monkeypatch.setattr(api, "_bridge", bridge_stub)
    result = await api.payment_status("ORD123", _request(), ACCOUNT_B)
    assert result["error_code"] == "PAYMENT_NOT_FOUND"
    assert result.get("data") == {}
    assert bridge_calls == []


@pytest.mark.anyio
async def test_real_canonical_sqlite_statuses_are_owner_bound_and_normalized(monkeypatch, tmp_path) -> None:
    path, _ = _canonical_db(monkeypatch, tmp_path)
    cases = {"PENDING": "PENDING", "PENDING_ADMIN_REVIEW": "PENDING", "paid": "PAID", "SUCCESS": "PAID", "FAILED": "FAILED", "CANCELLED": "CANCELLED", "EXPIRED": "CANCELLED", "UNKNOWN_STATE": "FAILED"}
    for index, status in enumerate(cases):
        _insert_order(path, order_code=f"ORD{index}", owner="telegram-1", status=status)
    for index, expected in enumerate(cases.values()):
        result = await api.payment_status(f"ORD{index}", _request(), ACCOUNT_A)
        assert result["data"]["status"] == expected
        assert result["data"]["status"] in {"PENDING", "PAID", "FAILED", "CANCELLED"}
        assert "user_id" not in result["data"]


@pytest.mark.anyio
async def test_concurrent_same_key_writes_one_real_order_and_calls_provider_once(monkeypatch, tmp_path) -> None:
    _enable_direct_checkout(monkeypatch)
    path, _ = _canonical_db(monkeypatch, tmp_path)
    _single_flight(monkeypatch)
    provider_calls = 0

    async def provider_stub(*args, **kwargs):
        nonlocal provider_calls
        provider_calls += 1
        await anyio.sleep(0.03)
        return {"code": "00", "data": {"checkoutUrl": "https://pay.payos.vn/checkout/one"}}

    monkeypatch.setattr(api, "_create_payos_checkout", provider_stub)
    monkeypatch.setattr(random, "randint", lambda start, end: 700001)
    payload = PaymentRequest(package_id="topup_10k", payment_type="topup_xu", idempotency_key="concurrent-key-001")
    results = []

    async def submit() -> None:
        results.append(await api.create_payment(payload, _request(), ACCOUNT_A))

    async with anyio.create_task_group() as group:
        group.start_soon(submit)
        group.start_soon(submit)
    assert provider_calls == 1
    assert {item["error_code"] for item in results} == {None, "IDEMPOTENCY_IN_PROGRESS"}
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM payos_orders").fetchone()[0] == 1


def test_source_and_frontend_contracts_remain_fail_closed() -> None:
    create_block = API_SOURCE.split("async def create_payment", 1)[1].split('@router.get("/payments/{payment_id}")', 1)[0]
    status_block = API_SOURCE.split("async def payment_status", 1)[1].split('@router.get("/jobs")', 1)[0]
    polling = INTEGRATION.split("function schedulePaymentPolling", 1)[1].split("function hydratePaymentOptions", 1)[0]
    assert "str(exc)" not in create_block and "INSERT OR REPLACE" not in create_block and "_run_transient_idempotent(scope, web_idempotency_hash" in create_block
    assert "except Exception:\n        pass" not in status_block
    assert "base().bridge.available" not in polling
    assert 'currentRoute !== "/wallet/topup"' in polling
    assert "paymentNeedsPolling(flow)" in polling
    assert len(Path(__file__).read_text(encoding="utf-8").splitlines()) <= 300
