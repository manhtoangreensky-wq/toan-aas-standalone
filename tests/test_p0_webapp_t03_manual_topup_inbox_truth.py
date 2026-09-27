"""Isolated verification tests for Web Issue #566 (T03 Phase B).

TASK_ID=WEBAPP_T03_R1_PHASE_B_TRANSACTIONAL_IN_APP_EVENTS
PARENT=Master #561

Covers all 16 mandatory invariants:
1. create -> exactly 1 pending Inbox item (owner = customer, kind = manual_topup_pending, source_revision = 1)
2. create replay -> no duplicate
3. approve -> exactly 1 approved item (owner = customer, kind = manual_topup_approved, source_revision = 2)
4. approve replay -> no duplicate
5. reject -> exactly 1 rejected item (owner = customer, kind = manual_topup_rejected, source_revision = 3)
6. reject replay -> no duplicate
7. approve vs reject terminal exclusivity (one request cannot have both approved & rejected notifications)
8. ambiguous credit / failure path -> request remains pending, zero terminal notification
9. owner is customer, never admin
10. cross-account isolation (Customer B cannot query/read/dismiss Customer A's inbox item)
11. Inbox API list, read, and dismiss contract (read/dismiss transitions work as expected)
12. scheduler independence (WEBAPP_NOTIFICATION_AUTOMATION_ENABLED=false does not prevent materialization)
13. no scheduler tick called (web_notification_runs count == 0)
14. privacy boundary (zero sensitive fields persisted in notification tables)
15. historical terminal rows -> no backfill
16. historical pending -> terminal-only notification upon transition
"""

from __future__ import annotations

import hashlib
import sqlite3
import uuid

import pytest
from starlette.testclient import TestClient

import app as app_module
import copyfast_api
from copyfast_auth import SESSION_COOKIE, _cookie_name, _session_cookie_value
import copyfast_db
from copyfast_db import (
    WebManualTopupAdminGuard,
    claim_web_credit_operation_for_dispatch,
    claim_web_manual_topup_approve_decision,
    confirm_web_manual_topup_reject,
    create_web_manual_topup_approve_receipt,
    create_web_manual_topup_reject_receipt,
    create_web_manual_topup_request,
    ensure_copyfast_schema,
    finalize_web_manual_topup_approval_with_operation,
    update_web_manual_topup_credit_operation_status,
    utc_now,
)


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _setup_account(db_path: str, email: str, *, role: str = "user", canon_id: str | None = None) -> str:
    account_id = f"acc-{hashlib.md5(email.encode()).hexdigest()[:12]}"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO web_accounts (id, email, password_hash, display_name, role_cache, canonical_user_id, created_at, updated_at)
               VALUES (?, ?, 'hash', 'User', ?, ?, datetime('now'), datetime('now'))""",
            (account_id, email, role, canon_id or f"canon-{account_id}"),
        )
        conn.commit()
    return account_id


def _setup_session(db_path: str, account_id: str) -> tuple[str, str]:
    session_id = str(uuid.uuid4())
    csrf_token = f"csrf-{session_id}"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO web_sessions (id, account_id, csrf_token, created_at, expires_at, last_seen_at)
               VALUES (?, ?, ?, datetime('now'), datetime('now', '+1 hour'), datetime('now'))""",
            (session_id, account_id, csrf_token),
        )
        conn.commit()
    return session_id, csrf_token


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "t03_isolated.db")
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", db_path)
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-secret-12345678901234567890")
    monkeypatch.setenv("WEBAPP_NOTIFICATION_CENTER_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_NOTIFICATION_AUTOMATION_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ADMIN_WRITES_ENABLED", "true")
    ensure_copyfast_schema()
    return db_path


def test_create_and_replay_materializes_exactly_one_pending_item(isolated_db):
    """1 & 2: Create materializes exactly 1 pending item; replay does not duplicate."""
    customer_id = _setup_account(isolated_db, "customer1@toanaas.vn")
    idem_hash = _hash_key("create-req-1")
    fp = _hash_key("fp-req-1")

    req = create_web_manual_topup_request(
        account_id=customer_id,
        amount_vnd=100_000,
        method="bank_acb_vietqr",
        reference="REF001",
        idempotency_key_hash=idem_hash,
        request_fingerprint=fp,
    )
    req_num = int(req["request_id"].split("-")[1])
    submitted_at = req["submitted_at"]

    with sqlite3.connect(isolated_db) as conn:
        items = conn.execute("SELECT id, account_id, kind, source_kind, source_id, source_revision, occurrence_at, severity, state, revision, dedupe_fingerprint, created_by_run_id FROM web_notification_items").fetchall()
        dedupes = conn.execute("SELECT dedupe_fingerprint, account_id, source_kind, source_id, source_revision, occurrence_at FROM web_notification_dedupes").fetchall()
        events = conn.execute("SELECT id, notification_id, account_id, actor_account_id, action, state, revision FROM web_notification_events").fetchall()

    assert len(items) == 1
    assert len(dedupes) == 1
    assert len(events) == 1

    item = items[0]
    assert item[1] == customer_id
    assert item[2] == "manual_topup_pending"
    assert item[3] == "manual_topup"
    assert item[4] == f"MANUAL-{req_num}"
    assert item[5] == 1  # source_revision
    assert item[6] == submitted_at
    assert item[7] == "warning"
    assert item[8] == "unread"
    assert item[9] == 1  # revision
    assert item[11] is None  # created_by_run_id

    dedupe = dedupes[0]
    assert dedupe[0] == item[10]  # dedupe_fingerprint
    assert dedupe[1] == customer_id
    assert dedupe[2] == "manual_topup"
    assert dedupe[3] == f"MANUAL-{req_num}"
    assert dedupe[4] == 1
    assert dedupe[5] == submitted_at

    event = events[0]
    assert event[1] == item[0]
    assert event[2] == customer_id
    assert event[3] is None  # actor_account_id
    assert event[4] == "materialized"
    assert event[5] == "unread"
    assert event[6] == 1

    # Replay creation
    replay_req = create_web_manual_topup_request(
        account_id=customer_id,
        amount_vnd=100_000,
        method="bank_acb_vietqr",
        reference="REF001",
        idempotency_key_hash=idem_hash,
        request_fingerprint=fp,
    )
    assert replay_req.get("idempotent_replay") is True

    with sqlite3.connect(isolated_db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM web_notification_items").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM web_notification_dedupes").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM web_notification_events").fetchone()[0] == 1


def test_approve_and_replay_materializes_exactly_one_approved_item(isolated_db):
    """3 & 4: Approve materializes exactly 1 approved item for customer; replay does not duplicate."""
    customer_id = _setup_account(isolated_db, "customer2@toanaas.vn")
    admin_id = _setup_account(isolated_db, "admin2@toanaas.vn", role="admin")
    session_id, _ = _setup_session(isolated_db, admin_id)

    req = create_web_manual_topup_request(
        account_id=customer_id,
        amount_vnd=50_000,
        method="bank_acb_vietqr",
        reference="REF002",
        idempotency_key_hash=_hash_key("create-req-2"),
        request_fingerprint=_hash_key("fp-req-2"),
    )
    req_num = int(req["request_id"].split("-")[1])

    receipt_hash = _hash_key("receipt-approve-2")
    now = utc_now()
    expires_at = "2099-01-01T00:00:00Z"
    create_web_manual_topup_approve_receipt(
        request_number=req_num,
        admin_account_id=admin_id,
        session_id=session_id,
        receipt_hash=receipt_hash,
        approved_xu=50,
        reason="Verified deposit",
        now=now,
        expires_at=expires_at,
    )
    claim_idem_hash = _hash_key("claim-approve-2")
    claim_web_manual_topup_approve_decision(
        request_number=req_num,
        admin_account_id=admin_id,
        session_id=session_id,
        receipt_hash=receipt_hash,
        idempotency_key_hash=claim_idem_hash,
        now=now,
    )
    finalize_web_manual_topup_approval_with_operation(
        request_number=req_num,
        admin_account_id=admin_id,
        approved_xu=50,
        ledger_event_id="ledger-tx-222",
        reason="Verified deposit",
        session_id=session_id,
        idempotency_key_hash=claim_idem_hash,
        audit_request_id="audit-app-2",
        now=now,
    )

    with sqlite3.connect(isolated_db) as conn:
        items = conn.execute("SELECT account_id, kind, source_id, source_revision, occurrence_at FROM web_notification_items ORDER BY id ASC").fetchall()
        assert len(items) == 2  # 1 pending + 1 approved
        approved_item = [it for it in items if it[1] == "manual_topup_approved"][0]
        assert approved_item[0] == customer_id  # customer is owner, not admin!
        assert approved_item[1] == "manual_topup_approved"
        assert approved_item[2] == f"MANUAL-{req_num}"
        assert approved_item[3] == 2  # source_revision = 2
        assert approved_item[4] == now

    # Replay approval
    replay_res = finalize_web_manual_topup_approval_with_operation(
        request_number=req_num,
        admin_account_id=admin_id,
        approved_xu=50,
        ledger_event_id="ledger-tx-222",
        reason="Verified deposit",
        session_id=session_id,
        idempotency_key_hash=claim_idem_hash,
        audit_request_id="audit-app-2",
        now=now,
    )
    assert replay_res.get("idempotent_replay") is True

    with sqlite3.connect(isolated_db) as conn:
        items = conn.execute("SELECT account_id, kind, source_id FROM web_notification_items").fetchall()
        assert len(items) == 2  # no duplicate created


def test_reject_and_replay_materializes_exactly_one_rejected_item(isolated_db):
    """5 & 6: Reject materializes exactly 1 rejected item for customer; replay does not duplicate."""
    customer_id = _setup_account(isolated_db, "customer3@toanaas.vn")
    admin_id = _setup_account(isolated_db, "admin3@toanaas.vn", role="admin")
    session_id, _ = _setup_session(isolated_db, admin_id)

    req = create_web_manual_topup_request(
        account_id=customer_id,
        amount_vnd=200_000,
        method="bank_acb_vietqr",
        reference="REF003",
        idempotency_key_hash=_hash_key("create-req-3"),
        request_fingerprint=_hash_key("fp-req-3"),
    )
    req_num = int(req["request_id"].split("-")[1])

    receipt_hash = _hash_key("receipt-reject-3")
    now = utc_now()
    expires_at = "2099-01-01T00:00:00Z"
    create_web_manual_topup_reject_receipt(
        request_number=req_num,
        admin_account_id=admin_id,
        session_id=session_id,
        receipt_hash=receipt_hash,
        reason="Invalid transfer slip",
        now=now,
        expires_at=expires_at,
    )
    claim_idem_hash = _hash_key("claim-reject-3")
    confirm_web_manual_topup_reject(
        request_number=req_num,
        admin_account_id=admin_id,
        session_id=session_id,
        receipt_hash=receipt_hash,
        idempotency_key_hash=claim_idem_hash,
        audit_request_id="audit-rej-3",
        now=now,
    )

    with sqlite3.connect(isolated_db) as conn:
        items = conn.execute("SELECT account_id, kind, source_id, source_revision, occurrence_at FROM web_notification_items ORDER BY id ASC").fetchall()
        assert len(items) == 2  # 1 pending + 1 rejected
        rejected_item = [it for it in items if it[1] == "manual_topup_rejected"][0]
        assert rejected_item[0] == customer_id  # customer is owner, not admin!
        assert rejected_item[1] == "manual_topup_rejected"
        assert rejected_item[2] == f"MANUAL-{req_num}"
        assert rejected_item[3] == 3  # source_revision = 3
        assert rejected_item[4] == now

    # Replay reject
    replay_res = confirm_web_manual_topup_reject(
        request_number=req_num,
        admin_account_id=admin_id,
        session_id=session_id,
        receipt_hash=receipt_hash,
        idempotency_key_hash=claim_idem_hash,
        audit_request_id="audit-rej-3",
        now=now,
    )
    assert replay_res.get("idempotent_replay") is True

    with sqlite3.connect(isolated_db) as conn:
        items = conn.execute("SELECT account_id, kind, source_id FROM web_notification_items").fetchall()
        assert len(items) == 2  # no duplicate created


def test_approve_reject_terminal_exclusivity(isolated_db):
    """7: One request cannot materialize both approved and rejected terminal items."""
    customer_id = _setup_account(isolated_db, "customer4@toanaas.vn")
    admin_id = _setup_account(isolated_db, "admin4@toanaas.vn", role="admin")
    session_id, _ = _setup_session(isolated_db, admin_id)

    req = create_web_manual_topup_request(
        account_id=customer_id,
        amount_vnd=100_000,
        method="bank_acb_vietqr",
        reference="REF004",
        idempotency_key_hash=_hash_key("create-req-4"),
        request_fingerprint=_hash_key("fp-req-4"),
    )
    req_num = int(req["request_id"].split("-")[1])
    now = utc_now()

    # First approve it
    receipt_hash = _hash_key("receipt-approve-4")
    create_web_manual_topup_approve_receipt(
        request_number=req_num,
        admin_account_id=admin_id,
        session_id=session_id,
        receipt_hash=receipt_hash,
        approved_xu=100,
        reason="Good",
        now=now,
        expires_at="2099-01-01T00:00:00Z",
    )
    finalize_web_manual_topup_approval_with_operation(
        request_number=req_num,
        admin_account_id=admin_id,
        approved_xu=100,
        ledger_event_id="ledger-tx-444",
        reason="Good",
        session_id=session_id,
        idempotency_key_hash=_hash_key("claim-app-4"),
        audit_request_id="audit-app-4",
        now=now,
    )

    # Attempt to reject the already-approved request -> must fail closed
    with pytest.raises(WebManualTopupAdminGuard) as exc_info:
        create_web_manual_topup_reject_receipt(
            request_number=req_num,
            admin_account_id=admin_id,
            session_id=session_id,
            receipt_hash=_hash_key("receipt-rej-4"),
            reason="Trying to reject approved",
            now=now,
            expires_at="2099-01-01T00:00:00Z",
        )
    assert exc_info.value.args[0] == "MANUAL_ADMIN_NOT_PENDING"

    with sqlite3.connect(isolated_db) as conn:
        kinds = [r[0] for r in conn.execute("SELECT kind FROM web_notification_items WHERE source_id=?", (f"MANUAL-{req_num}",)).fetchall()]
        assert "manual_topup_approved" in kinds
        assert "manual_topup_rejected" not in kinds


def test_ambiguous_credit_does_not_create_terminal_notification(isolated_db):
    """8: Ambiguous credit / failure leaves request pending, creating zero terminal notification."""
    customer_id = _setup_account(isolated_db, "customer5@toanaas.vn")
    admin_id = _setup_account(isolated_db, "admin5@toanaas.vn", role="admin")

    req = create_web_manual_topup_request(
        account_id=customer_id,
        amount_vnd=75_000,
        method="bank_acb_vietqr",
        reference="REF005",
        idempotency_key_hash=_hash_key("create-req-5"),
        request_fingerprint=_hash_key("fp-req-5"),
    )
    req_num = int(req["request_id"].split("-")[1])

    # Claim credit operation for dispatch
    op, status = claim_web_credit_operation_for_dispatch(
        request_number=req_num,
        admin_account_id=admin_id,
        canonical_user_id="canon-customer5",
        amount_xu=75,
        reference="REF005",
    )
    assert status == "dispatch"

    # Simulate timeout / ambiguous bridge failure -> update status to reconcile_required
    update_web_manual_topup_credit_operation_status(
        request_number=req_num,
        status="reconcile_required",
        error_detail="WALLET_CREDIT_TIMEOUT",
    )

    # Check request status remains pending
    with sqlite3.connect(isolated_db) as conn:
        req_status = conn.execute("SELECT status FROM web_manual_topup_requests WHERE id=?", (req_num,)).fetchone()[0]
        assert req_status == "pending_admin_review"
        # Only pending notification exists, zero terminal notification
        items = conn.execute("SELECT kind FROM web_notification_items WHERE source_id=?", (f"MANUAL-{req_num}",)).fetchall()
        assert len(items) == 1
        assert items[0][0] == "manual_topup_pending"


def test_owner_is_customer_never_admin(isolated_db):
    """9: Inbox account_id MUST equal customer request owner; admin never receives customer inbox item."""
    customer_id = _setup_account(isolated_db, "customer6@toanaas.vn")
    admin_id = _setup_account(isolated_db, "admin6@toanaas.vn", role="admin")
    session_id, _ = _setup_session(isolated_db, admin_id)

    req = create_web_manual_topup_request(
        account_id=customer_id,
        amount_vnd=120_000,
        method="bank_acb_vietqr",
        reference="REF006",
        idempotency_key_hash=_hash_key("create-req-6"),
        request_fingerprint=_hash_key("fp-req-6"),
    )
    req_num = int(req["request_id"].split("-")[1])

    # Approve
    now = utc_now()
    receipt_hash = _hash_key("receipt-approve-6")
    create_web_manual_topup_approve_receipt(
        request_number=req_num,
        admin_account_id=admin_id,
        session_id=session_id,
        receipt_hash=receipt_hash,
        approved_xu=120,
        reason="Approved",
        now=now,
        expires_at="2099-01-01T00:00:00Z",
    )
    finalize_web_manual_topup_approval_with_operation(
        request_number=req_num,
        admin_account_id=admin_id,
        approved_xu=120,
        ledger_event_id="ledger-tx-666",
        reason="Approved",
        session_id=session_id,
        idempotency_key_hash=_hash_key("claim-app-6"),
        audit_request_id="audit-app-6",
        now=now,
    )

    with sqlite3.connect(isolated_db) as conn:
        customer_items = conn.execute("SELECT COUNT(*) FROM web_notification_items WHERE account_id=?", (customer_id,)).fetchone()[0]
        admin_items = conn.execute("SELECT COUNT(*) FROM web_notification_items WHERE account_id=?", (admin_id,)).fetchone()[0]
        assert customer_items == 2  # pending + approved
        assert admin_items == 0    # zero items for admin


def test_cross_account_isolation(isolated_db):
    """10: Customer B cannot list, read, or dismiss Customer A's inbox item."""
    customer_a = _setup_account(isolated_db, "customerA@toanaas.vn")
    customer_b = _setup_account(isolated_db, "customerB@toanaas.vn")
    sess_b, csrf_b = _setup_session(isolated_db, customer_b)

    req = create_web_manual_topup_request(
        account_id=customer_a,
        amount_vnd=100_000,
        method="bank_acb_vietqr",
        reference="REFA",
        idempotency_key_hash=_hash_key("create-req-A"),
        request_fingerprint=_hash_key("fp-req-A"),
    )

    with sqlite3.connect(isolated_db) as conn:
        item_a = conn.execute("SELECT id FROM web_notification_items WHERE account_id=?", (customer_a,)).fetchone()
        assert item_a is not None
        item_a_id = item_a[0]

    client = TestClient(app_module.app)
    client.cookies.set(_cookie_name(SESSION_COOKIE), _session_cookie_value(sess_b))
    client.headers["X-CSRF-Token"] = csrf_b

    # Customer B lists items -> must see 0 items
    list_res = client.get("/api/v1/inbox/items")
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]["items"]) == 0

    # Customer B attempts to read Customer A's item -> must fail closed (404/not found)
    read_res = client.post(
        f"/api/v1/inbox/items/{item_a_id}/read",
        json={"expected_revision": 1, "idempotency_key": "read-attempt-by-b-12345"},
    )
    assert read_res.status_code == 200
    body = read_res.json()
    assert body["ok"] is False
    assert body["error_code"] == "WEB_INBOX_ITEM_NOT_FOUND"

    # Customer B attempts to dismiss Customer A's item -> must fail closed
    dismiss_res = client.post(
        f"/api/v1/inbox/items/{item_a_id}/dismiss",
        json={"expected_revision": 1, "confirm": True, "idempotency_key": "dismiss-attempt-b-12345"},
    )
    assert dismiss_res.status_code == 200
    body = dismiss_res.json()
    assert body["ok"] is False
    assert body["error_code"] == "WEB_INBOX_ITEM_NOT_FOUND"


def test_inbox_api_list_read_dismiss_lifecycle(isolated_db):
    """11: Inbox existing API contract works for manual-topup kinds with read and dismiss."""
    customer_id = _setup_account(isolated_db, "customer_lifecycle@toanaas.vn")
    session_id, csrf_token = _setup_session(isolated_db, customer_id)

    req = create_web_manual_topup_request(
        account_id=customer_id,
        amount_vnd=300_000,
        method="bank_acb_vietqr",
        reference="REFLC",
        idempotency_key_hash=_hash_key("create-req-lc"),
        request_fingerprint=_hash_key("fp-req-lc"),
    )

    client = TestClient(app_module.app)
    client.cookies.set(_cookie_name(SESSION_COOKIE), _session_cookie_value(session_id))
    client.headers["X-CSRF-Token"] = csrf_token

    # 1. Summary
    sum_res = client.get("/api/v1/inbox/summary")
    assert sum_res.status_code == 200
    sum_data = sum_res.json()["data"]
    assert sum_data["unread_count"] == 1
    assert sum_data["counts"]["unread"] == 1

    # 2. List items
    items_res = client.get("/api/v1/inbox/items")
    assert items_res.status_code == 200
    items = items_res.json()["data"]["items"]
    assert len(items) == 1
    item = items[0]
    assert item["kind"] == "manual_topup_pending"
    assert item["source_kind"] == "manual_topup"
    assert item["state"] == "unread"
    assert item["revision"] == 1
    assert item["delivery"] == "in_app_record_only"
    item_id = item["id"]

    # 3. Mark as read
    read_res = client.post(
        f"/api/v1/inbox/items/{item_id}/read",
        json={"expected_revision": 1, "idempotency_key": "read-key-valid-12345"},
    )
    assert read_res.status_code == 200
    read_data = read_res.json()["data"]["item"]
    assert read_data["state"] == "read"
    assert read_data["revision"] == 2
    assert read_data["read_at"] is not None

    # 4. Dismiss
    dismiss_res = client.post(
        f"/api/v1/inbox/items/{item_id}/dismiss",
        json={"expected_revision": 2, "confirm": True, "idempotency_key": "dismiss-key-valid-12345"},
    )
    assert dismiss_res.status_code == 200
    dismiss_data = dismiss_res.json()["data"]["item"]
    assert dismiss_data["state"] == "dismissed"
    assert dismiss_data["revision"] == 3
    assert dismiss_data["dismissed_at"] is not None


def test_scheduler_independence_and_no_tick_called(isolated_db):
    """12 & 13: WEBAPP_NOTIFICATION_AUTOMATION_ENABLED=false does not prevent materialization, zero scheduler runs."""
    customer_id = _setup_account(isolated_db, "customer_sched@toanaas.vn")

    req = create_web_manual_topup_request(
        account_id=customer_id,
        amount_vnd=50_000,
        method="bank_acb_vietqr",
        reference="REFSCHED",
        idempotency_key_hash=_hash_key("create-req-sched"),
        request_fingerprint=_hash_key("fp-req-sched"),
    )

    with sqlite3.connect(isolated_db) as conn:
        # Item exists
        items = conn.execute("SELECT COUNT(*) FROM web_notification_items").fetchone()[0]
        assert items == 1
        # Scheduler runs table is empty
        runs = conn.execute("SELECT COUNT(*) FROM web_notification_runs").fetchone()[0]
        assert runs == 0
        run_steps = conn.execute("SELECT COUNT(*) FROM web_notification_run_steps").fetchone()[0]
        assert run_steps == 0
        leases = conn.execute("SELECT COUNT(*) FROM web_notification_leases").fetchone()[0]
        assert leases == 0


def test_privacy_boundary_zero_sensitive_data(isolated_db):
    """14: Notification tables contain only opaque event coordinates, zero sensitive fields."""
    customer_id = _setup_account(isolated_db, "customer_priv@toanaas.vn")
    admin_id = _setup_account(isolated_db, "admin_priv@toanaas.vn", role="admin")
    session_id, _ = _setup_session(isolated_db, admin_id)

    req = create_web_manual_topup_request(
        account_id=customer_id,
        amount_vnd=500_000,
        method="bank_acb_vietqr",
        reference="SECRET_REF_12345",
        idempotency_key_hash=_hash_key("create-req-priv"),
        request_fingerprint=_hash_key("fp-req-priv"),
    )
    req_num = int(req["request_id"].split("-")[1])
    now = utc_now()
    receipt_hash = _hash_key("receipt-approve-priv")
    create_web_manual_topup_approve_receipt(
        request_number=req_num,
        admin_account_id=admin_id,
        session_id=session_id,
        receipt_hash=receipt_hash,
        approved_xu=500,
        reason="SECRET_ADMIN_REASON_XYZ",
        now=now,
        expires_at="2099-01-01T00:00:00Z",
    )
    finalize_web_manual_topup_approval_with_operation(
        request_number=req_num,
        admin_account_id=admin_id,
        approved_xu=500,
        ledger_event_id="SECRET_LEDGER_RECEIPT_999",
        reason="SECRET_ADMIN_REASON_XYZ",
        session_id=session_id,
        idempotency_key_hash=_hash_key("claim-app-priv"),
        audit_request_id="audit-priv-1",
        now=now,
    )

    sensitive_tokens = [
        "SECRET_REF_12345",
        "SECRET_ADMIN_REASON_XYZ",
        "SECRET_LEDGER_RECEIPT_999",
        "500000",
        "500_000",
        "customer_priv@toanaas.vn",
        "bank_acb_vietqr",
    ]

    with sqlite3.connect(isolated_db) as conn:
        for table in ("web_notification_items", "web_notification_dedupes", "web_notification_events"):
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            for row in rows:
                for col in row:
                    col_str = str(col or "")
                    assert col != 500, f"Found numeric amount 500 in {table}"
                    assert col != 500_000, f"Found numeric amount 500000 in {table}"
                    for token in sensitive_tokens:
                        assert token not in col_str, f"Found sensitive token '{token}' in {table} column: {col_str}"


def test_historical_terminal_rows_no_backfill(isolated_db):
    """15: Legacy approved and rejected rows do NOT get fabricated notifications on schema start."""
    customer_id = _setup_account(isolated_db, "customer_hist@toanaas.vn")

    # Manually seed pre-existing approved and rejected rows (simulating historical data before T03)
    with sqlite3.connect(isolated_db) as conn:
        conn.execute(
            """INSERT INTO web_manual_topup_requests
               (account_id, amount_vnd, currency, method, reference, status,
                idempotency_key_hash, request_fingerprint, submitted_at, updated_at,
                decision_at, decision_reason, approved_xu, ledger_event_id)
               VALUES (?, 100000, 'VND', 'bank_acb_vietqr', 'OLD_REF1', 'approved',
                       ?, ?, '2026-01-01T00:00:00Z', '2026-01-01T01:00:00Z',
                       '2026-01-01T01:00:00Z', 'Old Approval', 100, 'old-ledger-1')""",
            (customer_id, _hash_key("hist-key-1"), _hash_key("hist-fp-1")),
        )
        conn.execute(
            """INSERT INTO web_manual_topup_requests
               (account_id, amount_vnd, currency, method, reference, status,
                idempotency_key_hash, request_fingerprint, submitted_at, updated_at,
                decision_at, decision_reason)
               VALUES (?, 200000, 'VND', 'bank_acb_vietqr', 'OLD_REF2', 'rejected',
                       ?, ?, '2026-01-02T00:00:00Z', '2026-01-02T01:00:00Z',
                       '2026-01-02T01:00:00Z', 'Old Rejection')""",
            (customer_id, _hash_key("hist-key-2"), _hash_key("hist-fp-2")),
        )
        conn.commit()

    # Re-run schema ensure (simulating restart / deployment)
    ensure_copyfast_schema()

    with sqlite3.connect(isolated_db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM web_notification_items WHERE account_id=?", (customer_id,)).fetchone()[0]
        assert count == 0  # Zero notifications fabricated for historical rows!


def test_historical_pending_gets_terminal_only_notification(isolated_db):
    """16: Pre-existing pending row gets terminal-only notification upon approval; no fake pending event."""
    customer_id = _setup_account(isolated_db, "customer_hist_pending@toanaas.vn")
    admin_id = _setup_account(isolated_db, "admin_hist@toanaas.vn", role="admin")
    session_id, _ = _setup_session(isolated_db, admin_id)

    # Manually seed pre-existing pending row (created before T03, so no pending notification exists)
    with sqlite3.connect(isolated_db) as conn:
        cursor = conn.execute(
            """INSERT INTO web_manual_topup_requests
               (account_id, amount_vnd, currency, method, reference, status,
                idempotency_key_hash, request_fingerprint, submitted_at, updated_at,
                payment_code_snapshot, transfer_content_snapshot, instruction_version)
               VALUES (?, 150000, 'VND', 'bank_acb_vietqr', 'OLD_PENDING_REF', 'pending_admin_review',
                       ?, ?, '2026-01-03T00:00:00Z', '2026-01-03T00:00:00Z',
                       '10000001', '10000001 MANUAL-99', 'request_bound_v2')""",
            (customer_id, _hash_key("hist-pending-key"), _hash_key("hist-pending-fp")),
        )
        req_num = cursor.lastrowid
        conn.commit()

    with sqlite3.connect(isolated_db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM web_notification_items WHERE account_id=?", (customer_id,)).fetchone()[0] == 0

    # Now approve this request after T03
    now = utc_now()
    receipt_hash = _hash_key("receipt-approve-hist")
    create_web_manual_topup_approve_receipt(
        request_number=req_num,
        admin_account_id=admin_id,
        session_id=session_id,
        receipt_hash=receipt_hash,
        approved_xu=150,
        reason="Approved legacy pending",
        now=now,
        expires_at="2099-01-01T00:00:00Z",
    )
    finalize_web_manual_topup_approval_with_operation(
        request_number=req_num,
        admin_account_id=admin_id,
        approved_xu=150,
        ledger_event_id="ledger-tx-hist-99",
        reason="Approved legacy pending",
        session_id=session_id,
        idempotency_key_hash=_hash_key("claim-app-hist"),
        audit_request_id="audit-app-hist",
        now=now,
    )

    with sqlite3.connect(isolated_db) as conn:
        items = conn.execute("SELECT kind, source_revision FROM web_notification_items WHERE account_id=?", (customer_id,)).fetchall()
        assert len(items) == 1
        assert items[0][0] == "manual_topup_approved"
        assert items[0][1] == 2  # source_revision = 2
        # NO manual_topup_pending item was ever created!
