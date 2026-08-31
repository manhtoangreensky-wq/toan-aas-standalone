from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from dataclasses import dataclass
import hashlib
import hmac
import importlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
import uuid

import httpx
import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

import bot


OWNER_ID = "123456789"
ADMIN_ID = "9001"
FOREIGN_OWNER_ID = "223456789"
OWNER_TOKEN = "p005-owner-fixture-token"
ADMIN_TOKEN = "p005-admin-fixture-token"
BRIDGE_HMAC = "p005-fixture-hmac-secret"
PASSWORD = "correct-horse-battery-staple"
BOT_ROOT = Path(bot.__file__).resolve().parent
WEB_MODULES = [
    "app", "config", "db", "copyfast_db", "copyfast_auth", "copyfast_bridge",
    "copyfast_registry", "copyfast_api", "copyfast_document_operations",
    "copyfast_image_runtime", "copyfast_image_operations", "copyfast_pages",
]


class CapturingASGITransport(httpx.AsyncBaseTransport):
    def __init__(self, app, calls: list[dict]):
        self._inner = httpx.ASGITransport(app=app)
        self._calls = calls

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        body = await request.aread()
        self._calls.append({
            "method": request.method,
            "path": request.url.path,
            "query": request.url.query.decode() if isinstance(request.url.query, bytes) else str(request.url.query),
            "headers": {key.lower(): value for key, value in request.headers.items()},
            "body": json.loads(body or b"{}"),
        })
        return await self._inner.handle_async_request(request)

    async def aclose(self) -> None:
        await self._inner.aclose()


@dataclass
class Harness:
    tmp_path: Path
    bot_db: Path
    web_db: Path
    app: object
    api: object
    auth: object
    bridge: object
    owner: TestClient
    admin: TestClient
    foreign: TestClient
    admin_peer: TestClient
    owner_csrf: str
    admin_csrf: str
    foreign_csrf: str
    admin_peer_csrf: str
    bridge_calls: list[dict]
    external_http_calls: list[str]


def callback_headers(body: bytes, path: str) -> dict[str, str]:
    request_id = f"p005-link-{uuid.uuid4()}"
    timestamp = str(int(time.time()))
    digest = hashlib.sha256(body).hexdigest()
    material = f"{timestamp}.{request_id}.POST.{path}.{digest}".encode()
    signature = hmac.new(b"bridge-test-hmac", material, hashlib.sha256).hexdigest()
    return {
        "X-TOAN-AAS-BRIDGE-TOKEN": "bridge-test-token",
        "X-TOAN-AAS-Timestamp": timestamp,
        "X-TOAN-AAS-Request-ID": request_id,
        "X-TOAN-AAS-Signature": signature,
        "Content-Type": "application/json",
    }


def register_link(client: TestClient, email: str, canonical_id: str, role: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": email.split("@")[0]},
    )
    assert registered.status_code == 200, registered.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    csrf = login.json()["data"]["csrf_token"]
    started = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf})
    assert started.status_code == 200, started.text
    code = started.json()["data"]["code"]
    path = "/api/v1/auth/internal/telegram-link/confirm"
    body = json.dumps(
        {"code": code, "canonical_user_id": canonical_id, "role": role},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    confirmed = client.post(path, headers=callback_headers(body, path), content=body)
    assert confirmed.status_code == 200 and confirmed.json()["ok"] is True, confirmed.text
    completed = client.post("/api/v1/auth/telegram/link/complete", headers={"X-CSRF-Token": csrf})
    assert completed.status_code == 200 and completed.json()["ok"] is True, completed.text
    return csrf


def login(client: TestClient, email: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()["data"]["csrf_token"]


@pytest.fixture(scope="session")
def bot_db_template(tmp_path_factory):
    root = tmp_path_factory.mktemp("p005_bot_template")
    path = root / "template.db"
    values = {
        "DB_FILE": str(path),
        "DB_BACKUP_DIR": str(root / "backups"),
        "DB_STARTUP_BACKUP_ENABLED": False,
        "DB_MIGRATION_DRY_RUN": False,
        "DB_STARTUP_BACKUP_PATHS": set(),
        "DB_STARTUP_PREP_RESULT": {"status": "not_run", "path": "", "created_at": "", "reason": ""},
    }
    originals = {name: getattr(bot, name) for name in values}
    try:
        for name, value in values.items():
            setattr(bot, name, value)
        bot.init_db()
    finally:
        for name, value in originals.items():
            setattr(bot, name, value)
    return path


@pytest.fixture
def harness(monkeypatch, tmp_path, bot_db_template):
    bot_db = tmp_path / "bot.db"
    source = sqlite3.connect(bot_db_template)
    destination = sqlite3.connect(bot_db)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()

    monkeypatch.setattr(bot, "DB_FILE", str(bot_db))
    monkeypatch.setattr(bot, "DB_BACKUP_DIR", str(tmp_path / "bot-backups"))
    monkeypatch.setattr(bot, "DB_STARTUP_BACKUP_ENABLED", False)
    monkeypatch.setattr(bot, "INTERNAL_BILLING_TOKEN", OWNER_TOKEN)
    monkeypatch.setattr(bot, "INTERNAL_MANUAL_ADMIN_TOKEN", ADMIN_TOKEN)
    monkeypatch.setattr(bot, "OWNER_IDS", set())
    monkeypatch.setattr(bot, "ADMIN_IDS", {ADMIN_ID})
    assert bot.is_admin_user(ADMIN_ID) is True
    assert bot.is_admin_user("7777") is False
    monkeypatch.setattr(
        bot,
        "calculate_package_credit_for_user",
        lambda _owner, amount: {"base_xu": int(amount), "launch_bonus_xu": 0, "total_xu": int(amount)},
    )
    monkeypatch.setattr(
        bot,
        "apply_automatic_topup_promotion_conn",
        lambda *_args, **_kwargs: {
            "bonus_xu": 0, "promotion_id": "", "label": "",
            "successful_topup_ordinal": 0, "domestic_eligibility": False, "status": "not_eligible",
        },
    )
    monkeypatch.setattr(
        bot,
        "award_referral_bonus_if_needed",
        lambda *_args, **_kwargs: {"reward_xu": 0, "status": "none", "referrer_user_id": ""},
    )
    bot.init_db()
    with sqlite3.connect(bot_db) as conn:
        for user_id, username, credits in (
            (OWNER_ID, "P005 Owner", 777),
            (FOREIGN_OWNER_ID, "P005 Foreign", 0),
            (ADMIN_ID, "P005 Admin", 0),
        ):
            conn.execute(
                """INSERT OR REPLACE INTO users
                   (user_id,username,credits,is_vip,join_date,total_spent,total_paid_vnd)
                   VALUES (?,?,?,?,?,?,?)""",
                (user_id, username, credits, 0, "2026-08-29 00:00:00", 0, 0),
            )
        conn.commit()

    web_db = tmp_path / "web.db"
    legacy_web_db = tmp_path / "legacy-web.db"
    env = {
        "WEBAPP_SESSION_DB_PATH": str(web_db),
        "DB_PATH": str(legacy_web_db),
        "DB_FILE": str(legacy_web_db),
        "DB_BACKUP_DIR": str(tmp_path / "legacy-web-backups"),
        "DB_STARTUP_BACKUP_ENABLED": "false",
        "WEB_SESSION_SECRET": "p005-web-fixture-session-secret",
        "BOT_USERNAME": "ToanAasSupportBot",
        "CORE_BRIDGE_BASE_URL": "https://bot.test",
        "CORE_BRIDGE_TOKEN": OWNER_TOKEN,
        "CORE_BRIDGE_HMAC_SECRET": BRIDGE_HMAC,
        "INTERNAL_MANUAL_ADMIN_TOKEN": ADMIN_TOKEN,
        "WEBAPP_COPYFAST_ENABLED": "true",
        "WEBAPP_ADMIN_ERP_ENABLED": "true",
        "WEBAPP_ADMIN_WRITES_ENABLED": "true",
        "WEBAPP_TELEGRAM_BOT_LINK_ENABLED": "true",
        "CORE_BRIDGE_CALLBACK_TOKEN": "bridge-test-token",
        "CORE_BRIDGE_CALLBACK_HMAC_SECRET": "bridge-test-hmac",
        "WEBAPP_LINK_CALLBACK_TOKEN": "bridge-test-token",
        "WEBAPP_LINK_CALLBACK_HMAC_SECRET": "bridge-test-hmac",
    }
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("WEB_COOKIE_SECURE", raising=False)
    for name in WEB_MODULES:
        sys.modules.pop(name, None)

    application = importlib.import_module("app").app
    api = sys.modules["copyfast_api"]
    auth = sys.modules["copyfast_auth"]
    bridge = sys.modules["copyfast_bridge"]
    calls: list[dict] = []
    external_calls: list[str] = []
    transport = CapturingASGITransport(bot.fastapi_app, calls)
    original_async_client = httpx.AsyncClient

    def async_client_factory(*args, **kwargs):
        base_url = str(kwargs.get("base_url") or "").rstrip("/")
        if base_url == "https://bot.test":
            kwargs["transport"] = transport
            return original_async_client(*args, **kwargs)
        external_calls.append(base_url or "<none>")
        raise AssertionError(f"external HTTP forbidden: {base_url or '<none>'}")

    monkeypatch.setattr(httpx, "AsyncClient", async_client_factory)

    async def canonical_admin(request: Request):
        account = auth.require_admin(request)
        if not bot.is_admin_user(str(account.get("canonical_user_id") or "")):
            raise HTTPException(status_code=403, detail="canonical admin denied")
        return account

    async def canonical_admin_csrf(request: Request):
        account = auth.require_admin_csrf(request)
        if not bot.is_admin_user(str(account.get("canonical_user_id") or "")):
            raise HTTPException(status_code=403, detail="canonical admin denied")
        return account

    application.dependency_overrides[api.require_canonical_admin] = canonical_admin
    application.dependency_overrides[api.require_canonical_admin_csrf] = canonical_admin_csrf

    with ExitStack() as stack:
        owner = stack.enter_context(TestClient(application))
        admin = stack.enter_context(TestClient(application))
        foreign = stack.enter_context(TestClient(application))
        admin_peer = stack.enter_context(TestClient(application))
        owner_csrf = register_link(owner, "owner@p005.invalid", OWNER_ID, "user")
        admin_csrf = register_link(admin, "admin@p005.invalid", ADMIN_ID, "admin")
        foreign_csrf = register_link(foreign, "foreign@p005.invalid", FOREIGN_OWNER_ID, "user")
        admin_peer_csrf = login(admin_peer, "admin@p005.invalid")
        yield Harness(
            tmp_path, bot_db, web_db, application, api, auth, bridge,
            owner, admin, foreign, admin_peer,
            owner_csrf, admin_csrf, foreign_csrf, admin_peer_csrf,
            calls, external_calls,
        )
    application.dependency_overrides.clear()


def create_pending(h: Harness, amount: int, key: str, reference: str) -> tuple[str, int]:
    response = h.owner.post(
        "/api/v1/payments/manual",
        headers={"X-CSRF-Token": h.owner_csrf},
        json={"amount_vnd": amount, "method": "bank_acb", "reference": reference, "idempotency_key": key},
    )
    assert response.status_code == 200 and response.json()["ok"] is True, response.text
    request_id = response.json()["data"]["request_id"]
    return request_id, int(request_id.split("-", 1)[1])


def admin_draft(h: Harness, request_id: str, payload: dict) -> str:
    response = h.admin.post(
        f"/api/v1/admin/payments/manual/{request_id}/draft",
        headers={"X-CSRF-Token": h.admin_csrf},
        json=payload,
    )
    assert response.status_code == 200 and response.json()["status"] == "awaiting_confirm", response.text
    data = response.json()["data"]
    assert "confirmation_token" not in json.dumps(data)
    receipt = data["confirmation_receipt"]
    assert 32 <= len(receipt) <= 160
    return receipt


def admin_confirm(client: TestClient, csrf: str, request_id: str, receipt: str, key: str):
    return client.post(
        f"/api/v1/admin/payments/manual/{request_id}/confirm",
        headers={"X-CSRF-Token": csrf},
        json={"confirmation_receipt": receipt, "idempotency_key": key},
    )


def bot_counts(h: Harness, deposit_id: int | None = None) -> dict:
    with sqlite3.connect(h.bot_db) as conn:
        credits = conn.execute("SELECT credits FROM users WHERE user_id=?", (OWNER_ID,)).fetchone()[0]
        result = {
            "credits": credits,
            "deposits": conn.execute("SELECT COUNT(*) FROM pending_deposits").fetchone()[0],
            "invoices": conn.execute("SELECT COUNT(*) FROM finance_invoices WHERE order_id LIKE 'MANUAL-WEB-%'").fetchone()[0],
            "positive_credit": 0,
            "usage": 0,
            "revenue": 0,
            "audit": 0,
            "deposit": (),
            "invoice": (),
        }
        if deposit_id is None:
            return result
        ref = str(deposit_id)
        result.update({
            "positive_credit": conn.execute(
                """SELECT COUNT(*) FROM credit_events
                   WHERE user_id=? AND event_type='manual_deposit' AND ref_id=? AND delta>0""",
                (OWNER_ID, ref),
            ).fetchone()[0],
            "usage": conn.execute(
                """SELECT COUNT(*) FROM usage_events
                   WHERE user_id=? AND event_type='payment_manual_approved'""",
                (OWNER_ID,),
            ).fetchone()[0],
            "revenue": conn.execute(
                """SELECT COUNT(*) FROM finance_revenue_events
                   WHERE source_type='manual_revenue' AND source_id=?""",
                (f"manual_deposit:{deposit_id}",),
            ).fetchone()[0],
            "audit": conn.execute(
                """SELECT COUNT(*) FROM audit_logs
                   WHERE object_type='pending_deposit' AND object_id=?
                     AND action IN ('bill.approved','bill.rejected')""",
                (ref,),
            ).fetchone()[0],
            "deposit": tuple(conn.execute(
                """SELECT status,approved_xu,admin_note,approved_by,approved_at,updated_at
                   FROM pending_deposits WHERE id=?""",
                (deposit_id,),
            ).fetchone() or ()),
            "invoice": tuple(conn.execute(
                """SELECT status,approved_by_admin_id FROM finance_invoices
                   WHERE order_id=(SELECT order_code FROM pending_deposits WHERE id=?)""",
                (deposit_id,),
            ).fetchone() or ()),
        })
        return result


def assert_owner_projection_safe(payload) -> None:
    text = json.dumps(payload, ensure_ascii=False)
    for forbidden in (
        "confirmation_token", "decided_by_admin_id", "approved_by",
        "file_id", "raw_response", OWNER_TOKEN, ADMIN_TOKEN,
    ):
        assert forbidden not in text


def test_web_owner_create_pending_then_admin_approve_expected_exactly_once(harness):
    h = harness
    request_id, deposit_id = create_pending(h, 10_000, "p005-create-approve-0001", "p005-tx-approve")
    pending = bot_counts(h, deposit_id)
    assert pending["deposits"] == pending["invoices"] == 1
    assert pending["credits"] == 777
    assert pending["positive_credit"] == pending["usage"] == pending["revenue"] == pending["audit"] == 0

    history = h.owner.get("/api/v1/payments/manual")
    detail = h.owner.get(f"/api/v1/payments/manual/{request_id}")
    assert history.status_code == detail.status_code == 200
    assert history.json()["data"]["items"][0]["status"] == "pending_admin_review"
    assert detail.json()["data"]["status"] == "pending_admin_review"
    assert_owner_projection_safe(history.json())
    assert_owner_projection_safe(detail.json())

    listed = h.admin.get("/api/v1/admin/payments/manual")
    admin_detail = h.admin.get(f"/api/v1/admin/payments/manual/{request_id}")
    assert listed.status_code == admin_detail.status_code == 200
    assert listed.json()["data"]["items"][0]["request_id"] == request_id
    assert admin_detail.json()["data"]["telegram_user_id"] == OWNER_ID

    receipt = admin_draft(h, request_id, {"action": "approve_expected"})
    still_pending = bot_counts(h, deposit_id)
    assert still_pending["credits"] == 777 and still_pending["audit"] == 0
    confirmed = admin_confirm(h.admin, h.admin_csrf, request_id, receipt, "p005-confirm-approve-0001")
    assert confirmed.status_code == 200 and confirmed.json()["status"] == "approved", confirmed.text
    approved_xu = confirmed.json()["data"]["approved_xu"]
    final = bot_counts(h, deposit_id)
    assert final["credits"] == 777 + approved_xu
    assert final["positive_credit"] == final["usage"] == final["revenue"] == final["audit"] == 1
    assert final["deposit"][0] == "approved"
    assert final["invoice"][0] == "paid"

    owner_history = h.owner.get("/api/v1/payments/manual")
    owner_status = h.owner.get(f"/api/v1/payments/manual/{request_id}/status")
    assert owner_history.json()["data"]["items"][0]["status"] == "approved"
    assert owner_status.json()["data"]["status"] == "approved"
    assert_owner_projection_safe(owner_history.json())
    assert_owner_projection_safe(owner_status.json())

    custom_request, custom_deposit = create_pending(
        h, 15_000, "p005-create-custom-0001", "p005-tx-custom"
    )
    custom_receipt = admin_draft(
        h,
        custom_request,
        {
            "action": "approve_custom",
            "approved_xu": 123,
            "reason": "Đối soát thực nhận theo chứng từ",
        },
    )
    custom_confirm = admin_confirm(
        h.admin,
        h.admin_csrf,
        custom_request,
        custom_receipt,
        "p005-confirm-custom-0001",
    )
    assert custom_confirm.status_code == 200
    assert custom_confirm.json()["status"] == "approved"
    assert custom_confirm.json()["data"]["approved_xu"] == 123
    custom_final = bot_counts(h, custom_deposit)
    assert custom_final["credits"] == final["credits"] + 123
    assert custom_final["positive_credit"] == 1
    assert custom_final["usage"] == 2
    assert custom_final["revenue"] == custom_final["audit"] == 1
    assert custom_final["deposit"][0] == "approved"
    assert custom_final["deposit"][1] == 123
    assert custom_final["invoice"][0] == "paid"


def test_web_admin_reject_credits_zero_and_owner_history_is_rejected(harness):
    h = harness
    request_id, deposit_id = create_pending(h, 20_000, "p005-create-reject-0001", "p005-tx-reject")
    before = bot_counts(h, deposit_id)
    receipt = admin_draft(h, request_id, {"action": "reject", "reason": "Không tìm thấy giao dịch"})
    rejected = admin_confirm(h.admin, h.admin_csrf, request_id, receipt, "p005-confirm-reject-0001")
    assert rejected.status_code == 200 and rejected.json()["status"] == "rejected", rejected.text
    after = bot_counts(h, deposit_id)
    assert after["credits"] == before["credits"] == 777
    assert after["positive_credit"] == after["usage"] == after["revenue"] == 0
    assert after["audit"] == 1
    assert after["deposit"][0] == after["invoice"][0] == "rejected"
    replay = admin_confirm(h.admin, h.admin_csrf, request_id, receipt, "p005-confirm-reject-0001")
    assert replay.status_code == 200
    assert replay.json()["status"] == "rejected"
    conflict = admin_confirm(h.admin, h.admin_csrf, request_id, receipt, "p005-confirm-reject-other")
    assert conflict.status_code == 200
    assert conflict.json()["error_code"] == "MANUAL_ADMIN_CONFIRMATION_ALREADY_USED"
    after_replay = bot_counts(h, deposit_id)
    for key in ("credits", "positive_credit", "usage", "revenue", "audit"):
        assert after_replay[key] == after[key]
    owner_history = h.owner.get("/api/v1/payments/manual")
    owner_status = h.owner.get(f"/api/v1/payments/manual/{request_id}/status")
    assert owner_history.json()["data"]["items"][0]["status"] == "rejected"
    assert owner_status.json()["data"]["status"] == "rejected"
    assert_owner_projection_safe(owner_history.json())
    assert_owner_projection_safe(owner_status.json())


def test_replay_and_concurrent_confirm_do_not_double_credit(harness):
    h = harness
    request_id, deposit_id = create_pending(h, 30_000, "p005-create-concurrent-0001", "p005-tx-concurrent")
    receipt = admin_draft(h, request_id, {"action": "approve_expected"})
    clone = TestClient(h.app)
    clone.cookies.update(h.admin.cookies)
    try:
        def confirm(client):
            return admin_confirm(client, h.admin_csrf, request_id, receipt, "p005-confirm-concurrent-0001")

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = [future.result() for future in (pool.submit(confirm, h.admin), pool.submit(confirm, clone))]
        bodies = [response.json() for response in responses]
        assert all(response.status_code == 200 for response in responses)
        assert any(body["status"] == "approved" and body["ok"] is True for body in bodies)
        assert all(body["status"] == "approved" or body["error_code"] == "MANUAL_ADMIN_CONFIRMATION_IN_PROGRESS" for body in bodies)

        replay = admin_confirm(h.admin, h.admin_csrf, request_id, receipt, "p005-confirm-concurrent-0001")
        assert replay.status_code == 200 and replay.json()["status"] == "approved"
        conflict = admin_confirm(h.admin, h.admin_csrf, request_id, receipt, "p005-confirm-concurrent-other")
        assert conflict.status_code == 200 and conflict.json()["ok"] is False
        assert conflict.json()["error_code"] == "MANUAL_ADMIN_CONFIRMATION_ALREADY_USED"
    finally:
        clone.close()
    final = bot_counts(h, deposit_id)
    assert final["credits"] == 777 + 30_000
    assert final["positive_credit"] == final["usage"] == final["revenue"] == final["audit"] == 1


def test_wrong_owner_role_csrf_admin_identity_and_cross_session_receipt_are_denied(harness):
    h = harness
    with TestClient(h.app) as anonymous:
        assert anonymous.get("/api/v1/payments/manual").status_code == 401
        assert anonymous.get("/api/v1/admin/payments/manual").status_code == 401
    missing_csrf = h.owner.post(
        "/api/v1/payments/manual",
        json={"amount_vnd": 40_000, "method": "bank_acb", "reference": "x", "idempotency_key": "p005-missing-csrf"},
    )
    wrong_csrf = h.owner.post(
        "/api/v1/payments/manual",
        headers={"X-CSRF-Token": "wrong"},
        json={"amount_vnd": 40_000, "method": "bank_acb", "reference": "x", "idempotency_key": "p005-wrong-csrf"},
    )
    assert missing_csrf.status_code == wrong_csrf.status_code == 403

    request_id, deposit_id = create_pending(h, 40_000, "p005-create-denial-0001", "p005-tx-denial")
    baseline = bot_counts(h, deposit_id)
    for response in (
        h.foreign.get(f"/api/v1/payments/manual/{request_id}"),
        h.foreign.get(f"/api/v1/payments/manual/{request_id}/status"),
    ):
        assert response.status_code == 404
        assert_owner_projection_safe(response.json())
    assert request_id not in json.dumps(h.foreign.get("/api/v1/payments/manual").json())
    assert h.owner.get("/api/v1/admin/payments/manual").status_code == 403
    assert h.owner.post(
        f"/api/v1/admin/payments/manual/{request_id}/draft",
        headers={"X-CSRF-Token": h.owner_csrf},
        json={"action": "approve_expected"},
    ).status_code == 403
    assert h.admin.post(f"/api/v1/admin/payments/manual/{request_id}/draft", json={"action": "approve_expected"}).status_code == 403
    assert h.admin.post(
        f"/api/v1/admin/payments/manual/{request_id}/draft",
        headers={"X-CSRF-Token": "wrong"},
        json={"action": "approve_expected"},
    ).status_code == 403

    calls_before = len(h.bridge_calls)
    forged_query = h.admin.get("/api/v1/admin/payments/manual?admin_id=7777")
    forged_body = h.admin.post(
        f"/api/v1/admin/payments/manual/{request_id}/draft",
        headers={"X-CSRF-Token": h.admin_csrf},
        json={"action": "approve_expected", "admin_id": "7777"},
    )
    assert forged_query.status_code == forged_body.status_code == 422
    assert len(h.bridge_calls) == calls_before
    forged_header = h.admin.get(
        "/api/v1/admin/payments/manual",
        headers={"X-TOAN-AAS-Admin-ID": "7777"},
    )
    assert forged_header.status_code == 200
    admin_call = [call for call in h.bridge_calls if call["path"] == "/internal/v1/admin/payments/manual"][-1]
    assert admin_call["headers"]["x-toan-aas-admin-id"] == ADMIN_ID

    receipt = admin_draft(h, request_id, {"action": "approve_expected"})
    assert h.owner.post(
        f"/api/v1/admin/payments/manual/{request_id}/confirm",
        headers={"X-CSRF-Token": h.owner_csrf},
        json={"confirmation_receipt": receipt, "idempotency_key": "p005-customer-confirm-denied"},
    ).status_code == 403
    cross_session = admin_confirm(h.admin_peer, h.admin_peer_csrf, request_id, receipt, "p005-cross-session-0001")
    tampered = admin_confirm(h.admin, h.admin_csrf, request_id, receipt[:-1] + "x", "p005-tampered-0001")
    no_csrf = h.admin.post(
        f"/api/v1/admin/payments/manual/{request_id}/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "p005-no-csrf-0001"},
    )
    wrong_csrf_confirm = h.admin.post(
        f"/api/v1/admin/payments/manual/{request_id}/confirm",
        headers={"X-CSRF-Token": "wrong"},
        json={"confirmation_receipt": receipt, "idempotency_key": "p005-wrong-csrf-confirm"},
    )
    assert cross_session.json()["error_code"] == "MANUAL_ADMIN_CONFIRMATION_REQUIRED"
    assert tampered.json()["error_code"] == "MANUAL_ADMIN_CONFIRMATION_REQUIRED"
    assert no_csrf.status_code == 403
    assert wrong_csrf_confirm.status_code == 403

    receipt_hash = hashlib.sha256(receipt.encode()).hexdigest()
    with h.api._manual_admin_receipt_lock:
        h.api._manual_admin_receipt_vault[receipt_hash].expires_at = 0
    expired = admin_confirm(h.admin, h.admin_csrf, request_id, receipt, "p005-expired-0001")
    assert expired.json()["error_code"] == "MANUAL_ADMIN_CONFIRMATION_EXPIRED"
    after = bot_counts(h, deposit_id)
    for key in ("credits", "positive_credit", "usage", "revenue", "audit"):
        assert after[key] == baseline[key]


def test_owner_and_admin_tokens_are_distinct_and_direct_admin_bridge_is_scoped(harness, monkeypatch, caplog):
    h = harness
    direct = TestClient(bot.fastapi_app)
    try:
        owner_admin_headers = {
            "Authorization": f"Bearer {OWNER_TOKEN}",
            "X-TOAN-AAS-Admin-ID": ADMIN_ID,
        }
        owner_on_admin = [
            direct.get("/internal/v1/admin/payments/manual", headers=owner_admin_headers),
            direct.get("/internal/v1/admin/payments/manual/MANUAL-1", headers=owner_admin_headers),
            direct.post(
                "/internal/v1/admin/payments/manual/MANUAL-1/draft",
                headers=owner_admin_headers,
                json={"action": "approve_expected"},
            ),
            direct.post(
                "/internal/v1/admin/payments/manual/MANUAL-1/confirm",
                headers=owner_admin_headers,
                json={"confirmation_token": ("a" * 40) + "." + ("b" * 64)},
            ),
        ]
        admin_on_owner = direct.get(
            "/internal/v1/payments/manual",
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}", "X-TOAN-AAS-Telegram-User-ID": OWNER_ID},
        )
        assert [response.status_code for response in owner_on_admin] == [401, 401, 401, 401]
        assert admin_on_owner.status_code == 401
        before = bot_counts(h)
        monkeypatch.setattr(bot, "INTERNAL_MANUAL_ADMIN_TOKEN", "")
        missing = direct.get(
            "/internal/v1/admin/payments/manual",
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}", "X-TOAN-AAS-Admin-ID": ADMIN_ID},
        )
        assert missing.status_code == 503
        monkeypatch.setattr(bot, "INTERNAL_MANUAL_ADMIN_TOKEN", OWNER_TOKEN)
        same = direct.get(
            "/internal/v1/admin/payments/manual",
            headers={"Authorization": f"Bearer {OWNER_TOKEN}", "X-TOAN-AAS-Admin-ID": ADMIN_ID},
        )
        assert same.status_code == 503
        monkeypatch.setattr(bot, "INTERNAL_MANUAL_ADMIN_TOKEN", ADMIN_TOKEN)
        non_admin = direct.get(
            "/internal/v1/admin/payments/manual",
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}", "X-TOAN-AAS-Admin-ID": "7777"},
        )
        assert non_admin.status_code == 403
        after = bot_counts(h)
        assert after["deposits"] == before["deposits"] and after["credits"] == before["credits"]

        web = h.admin.get(
            "/api/v1/admin/payments/manual",
            headers={"X-TOAN-AAS-Admin-ID": "7777"},
        )
        assert web.status_code == 200
        admin_call = [call for call in h.bridge_calls if call["path"] == "/internal/v1/admin/payments/manual"][-1]
        assert admin_call["headers"]["x-toan-aas-admin-id"] == ADMIN_ID
        evidence = web.text + caplog.text
        assert OWNER_TOKEN not in evidence and ADMIN_TOKEN not in evidence
        browser = (
            (Path(__file__).parents[1] / "static/portal/portal.js").read_text(encoding="utf-8")
            + (Path(__file__).parents[1] / "static/portal/integration.js").read_text(encoding="utf-8")
        )
        assert OWNER_TOKEN not in browser and ADMIN_TOKEN not in browser
    finally:
        direct.close()


def test_manual_flow_calls_no_payos_provider_telegram_or_production_endpoint(harness, monkeypatch):
    h = harness
    counters = {"payos": 0, "provider": 0, "telegram": 0}

    def sentinel(kind):
        def blocked(*_args, **_kwargs):
            counters[kind] += 1
            raise AssertionError(f"{kind} call forbidden")
        return blocked

    for name, kind in (
        ("process_payos_paid_order", "payos"),
        ("call_image_edit_provider", "provider"),
        ("shopaikey_chat_completion", "provider"),
        ("send_manual_payment", "telegram"),
        ("send_manual_payment_qr", "telegram"),
    ):
        if hasattr(bot, name):
            monkeypatch.setattr(bot, name, sentinel(kind))

    request_id, deposit_id = create_pending(h, 60_000, "p005-create-isolated-0001", "p005-tx-isolated")
    receipt = admin_draft(h, request_id, {"action": "approve_expected"})
    confirmed = admin_confirm(h.admin, h.admin_csrf, request_id, receipt, "p005-confirm-isolated-0001")
    assert confirmed.status_code == 200 and confirmed.json()["status"] == "approved"
    history = h.owner.get("/api/v1/payments/manual")
    assert history.status_code == 200 and history.json()["data"]["items"][0]["status"] == "approved"
    assert bot_counts(h, deposit_id)["positive_credit"] == 1
    assert counters == {"payos": 0, "provider": 0, "telegram": 0}
    assert h.external_http_calls == []
    assert h.bridge_calls
    assert all(call["path"].startswith("/internal/v1/") for call in h.bridge_calls)
    assert h.bot_db.resolve().is_relative_to(h.tmp_path.resolve())
    assert h.web_db.resolve().is_relative_to(h.tmp_path.resolve())
    assert not str(h.bot_db).startswith("/opt/") and not str(h.web_db).startswith("/opt/")
