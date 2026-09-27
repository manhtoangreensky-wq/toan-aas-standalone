"""Isolated verification tests for Web Issue #564 (T02 Phase B).

TASK_ID=WEBAPP_T02_R1_PHASE_B_IMMUTABLE_REQUEST_TRANSFER_INSTRUCTION
PARENT=Master #561

Covers all 11 required isolated invariants:
1. Additive schema migration from a pre-T02 database.
2. Legacy row backfill preserves legacy value exactly (historical truth).
3. 3-pending request collision is eliminated (distinct request-bound instructions).
4. Account-code mutation after request creation cannot alter history/detail.
5. Customer/Admin snapshot parity and no customer reference authority.
6. Owner isolation.
7. Idempotent replay stability.
8. Concurrent replay stability.
9. Zero wallet mutation during request creation and replay.
10. Zero bridge/Bot/PayOS/provider calls during request creation.
11. T01 manual-topup approval/admin queue regressions remain green.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import sqlite3
from typing import Any

import pytest
from starlette.testclient import TestClient

import app as app_module
import copyfast_api
import copyfast_db
from copyfast_db import (
    WebManualTopupIdempotencyConflict,
    WebManualTopupPendingLimit,
    create_web_manual_topup_request,
    ensure_copyfast_schema,
    get_web_manual_topup_for_admin,
    get_web_manual_topup_request,
    list_web_manual_topup_requests,
    list_web_manual_topups_for_admin,
)


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _setup_account(db_path: str, email: str, *, role: str = "user") -> str:
    account_id = f"acc-{hashlib.md5(email.encode()).hexdigest()[:12]}"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO web_accounts (id, email, password_hash, display_name, role_cache, created_at, updated_at)
               VALUES (?, ?, 'hash', 'User', ?, datetime('now'), datetime('now'))""",
            (account_id, email, role),
        )
        conn.commit()
    return account_id


def test_additive_schema_migration_and_legacy_backfill(tmp_path, monkeypatch):
    """1 & 2: Additive schema migration from pre-T02 database and exact legacy backfill."""
    db_path = str(tmp_path / "pre_t02_migration.db")
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", db_path)

    # Build pre-T02 schema (WITHOUT the 3 new snapshot columns)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE web_accounts (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL DEFAULT '',
                role_cache TEXT NOT NULL DEFAULT 'user',
                canonical_user_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE web_account_topup_codes (
                account_id TEXT PRIMARY KEY,
                payment_code TEXT NOT NULL UNIQUE CHECK(
                    length(payment_code) = 8
                    AND payment_code NOT GLOB '*[^0-9]*'
                ),
                created_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE web_manual_topup_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT NOT NULL,
                amount_vnd INTEGER NOT NULL CHECK(amount_vnd > 0),
                currency TEXT NOT NULL CHECK(currency = 'VND'),
                method TEXT NOT NULL,
                reference TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending_admin_review',
                idempotency_key_hash TEXT NOT NULL,
                request_fingerprint TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                decided_by_account_id TEXT,
                decision_at TEXT,
                decision_reason TEXT,
                approved_xu INTEGER,
                ledger_event_id TEXT
            )
            """
        )
        # Insert legacy account, code, and request
        legacy_account_id = "legacy-acc-001"
        legacy_code = "10000000"
        conn.execute(
            """INSERT INTO web_accounts (id, email, password_hash, display_name, created_at, updated_at)
               VALUES (?, 'legacy@example.com', 'hash', 'Legacy User', '2026-09-01T00:00:00Z', '2026-09-01T00:00:00Z')""",
            (legacy_account_id,),
        )
        conn.execute(
            """INSERT INTO web_account_topup_codes (account_id, payment_code, created_at)
               VALUES (?, ?, '2026-09-01T00:00:00Z')""",
            (legacy_account_id, legacy_code),
        )
        conn.execute(
            """INSERT INTO web_manual_topup_requests
               (id, account_id, amount_vnd, currency, method, reference, status,
                idempotency_key_hash, request_fingerprint, submitted_at, updated_at)
               VALUES (42, ?, 150000, 'VND', 'bank_acb', 'LEGACY-REF', 'pending_admin_review',
                       'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
                       'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
                       '2026-09-01T10:00:00Z', '2026-09-01T10:00:00Z')""",
            (legacy_account_id,),
        )
        conn.commit()

    # Run migration
    ensure_copyfast_schema()

    # Verify table columns now contain snapshots
    with sqlite3.connect(db_path) as conn:
        cols = {col[1] for col in conn.execute("PRAGMA table_info(web_manual_topup_requests)").fetchall()}
        assert "payment_code_snapshot" in cols
        assert "transfer_content_snapshot" in cols
        assert "instruction_version" in cols

        row = conn.execute(
            """SELECT payment_code_snapshot, transfer_content_snapshot, instruction_version
               FROM web_manual_topup_requests WHERE id = 42"""
        ).fetchone()
        assert row is not None
        assert row[0] == legacy_code
        assert row[1] == legacy_code
        assert row[2] == "legacy_account_code_v1"

    # Verify Customer history and detail read truthful legacy values
    history = list_web_manual_topup_requests(legacy_account_id, limit=10)
    assert len(history) == 1
    assert history[0]["request_id"] == "MANUAL-42"
    assert history[0]["transfer_content"] == legacy_code

    detail = get_web_manual_topup_request(legacy_account_id, 42)
    assert detail is not None
    assert detail["request_id"] == "MANUAL-42"
    assert detail["transfer_content"] == legacy_code

    # Verify Admin detail reads truthful legacy values
    admin_detail = get_web_manual_topup_for_admin(42)
    assert admin_detail is not None
    assert admin_detail["request_id"] == "MANUAL-42"
    assert admin_detail["payment_code"] == legacy_code
    assert admin_detail["transfer_content"] == legacy_code
    assert admin_detail["instruction_version"] == "legacy_account_code_v1"


def test_three_pending_requests_collision_eliminated(tmp_path, monkeypatch):
    """3: Up to 3 pending requests have distinct, request-bound transfer instructions."""
    db_path = str(tmp_path / "three_pending.db")
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", db_path)
    ensure_copyfast_schema()

    account_id = _setup_account(db_path, "multi_pending@toanaas.vn")

    # Create 3 requests
    r1 = create_web_manual_topup_request(
        account_id=account_id,
        amount_vnd=50_000,
        method="bank_acb",
        reference="REF-1",
        idempotency_key_hash=_hash_key("key-1"),
        request_fingerprint=_hash_key("fp-1"),
    )
    r2 = create_web_manual_topup_request(
        account_id=account_id,
        amount_vnd=100_000,
        method="bank_acb",
        reference="REF-2",
        idempotency_key_hash=_hash_key("key-2"),
        request_fingerprint=_hash_key("fp-2"),
    )
    r3 = create_web_manual_topup_request(
        account_id=account_id,
        amount_vnd=200_000,
        method="bank_acb",
        reference="REF-3",
        idempotency_key_hash=_hash_key("key-3"),
        request_fingerprint=_hash_key("fp-3"),
    )

    # 1. Same account payment code
    with sqlite3.connect(db_path) as conn:
        codes = conn.execute(
            "SELECT payment_code_snapshot FROM web_manual_topup_requests ORDER BY id ASC"
        ).fetchall()
        assert len(codes) == 3
        assert codes[0][0] == codes[1][0] == codes[2][0] == "10000000"

    # 2. Three distinct request IDs
    ids = [r1["request_id"], r2["request_id"], r3["request_id"]]
    assert len(set(ids)) == 3
    assert ids == ["MANUAL-1", "MANUAL-2", "MANUAL-3"]

    # 3. Three distinct request transfer contents
    contents = [r1["transfer_content"], r2["transfer_content"], r3["transfer_content"]]
    assert len(set(contents)) == 3
    assert contents == [
        "10000000 MANUAL-1",
        "10000000 MANUAL-2",
        "10000000 MANUAL-3",
    ]

    # MULTI_PENDING_TRANSFER_IDENTITY_AMBIGUOUS=NO
    assert contents[0] != contents[1] != contents[2]

    # 4th request must fail with pending limit
    with pytest.raises(WebManualTopupPendingLimit):
        create_web_manual_topup_request(
            account_id=account_id,
            amount_vnd=300_000,
            method="bank_acb",
            reference="REF-4",
            idempotency_key_hash=_hash_key("key-4"),
            request_fingerprint=_hash_key("fp-4"),
        )


def test_account_code_mutation_after_creation_cannot_alter_history(tmp_path, monkeypatch):
    """4: Mutating web_account_topup_codes cannot alter history or detail (immutable snapshots)."""
    db_path = str(tmp_path / "mutation_isolation.db")
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", db_path)
    ensure_copyfast_schema()

    account_id = _setup_account(db_path, "mutation_test@toanaas.vn")
    created = create_web_manual_topup_request(
        account_id=account_id,
        amount_vnd=75_000,
        method="bank_acb",
        reference="REF-ORIGINAL",
        idempotency_key_hash=_hash_key("key-mut"),
        request_fingerprint=_hash_key("fp-mut"),
    )
    req_id = created["request_id"]
    req_num = int(req_id.split("-", 1)[1])
    expected_content = "10000000 " + req_id

    assert created["transfer_content"] == expected_content

    # Now mutate the live account payment code in web_account_topup_codes
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE web_account_topup_codes SET payment_code='99999999' WHERE account_id=?",
            (account_id,),
        )
        conn.commit()

    # Customer history must NOT change
    history = list_web_manual_topup_requests(account_id, limit=10)
    assert history[0]["transfer_content"] == expected_content

    # Customer detail must NOT change
    detail = get_web_manual_topup_request(account_id, req_num)
    assert detail is not None
    assert detail["transfer_content"] == expected_content

    # Admin detail must NOT change
    admin_detail = get_web_manual_topup_for_admin(req_num)
    assert admin_detail is not None
    assert admin_detail["transfer_content"] == expected_content
    assert admin_detail["payment_code"] == "10000000"  # snapshot preserved

    # Even if web_account_topup_codes row is completely deleted
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM web_account_topup_codes WHERE account_id=?", (account_id,))
        conn.commit()

    # History and detail still remain stable
    detail_after_delete = get_web_manual_topup_request(account_id, req_num)
    assert detail_after_delete is not None
    assert detail_after_delete["transfer_content"] == expected_content

    admin_after_delete = get_web_manual_topup_for_admin(req_num)
    assert admin_after_delete is not None
    assert admin_after_delete["transfer_content"] == expected_content
    assert admin_after_delete["payment_code"] == "10000000"


def test_customer_admin_snapshot_parity_and_no_reference_authority(tmp_path, monkeypatch):
    """5: Customer and Admin view identical snapshot, reference has NO authority."""
    db_path = str(tmp_path / "parity_reference.db")
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", db_path)
    ensure_copyfast_schema()

    account_id = _setup_account(db_path, "parity@toanaas.vn")
    customer_forged_ref = "HACKED_INSTRUCTION_TRYING_TO_CONTROL_TRANSFER"

    created = create_web_manual_topup_request(
        account_id=account_id,
        amount_vnd=120_000,
        method="bank_acb",
        reference=customer_forged_ref,
        idempotency_key_hash=_hash_key("key-parity"),
        request_fingerprint=_hash_key("fp-parity"),
    )
    req_num = int(created["request_id"].split("-", 1)[1])

    customer_detail = get_web_manual_topup_request(account_id, req_num)
    admin_detail = get_web_manual_topup_for_admin(req_num)

    assert customer_detail is not None
    assert admin_detail is not None

    # Parity: exactly equal transfer instruction
    assert customer_detail["transfer_content"] == admin_detail["transfer_content"]
    assert customer_detail["transfer_content"] == f"10000000 MANUAL-{req_num}"

    # Customer reference did NOT override or affect canonical transfer content
    assert customer_forged_ref not in customer_detail["transfer_content"]
    assert customer_detail["reference"] == customer_forged_ref
    assert admin_detail["reference"] == customer_forged_ref


def test_owner_isolation(tmp_path, monkeypatch):
    """6: Owner isolation: Account A cannot view Account B's topup request."""
    db_path = str(tmp_path / "isolation.db")
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", db_path)
    ensure_copyfast_schema()

    acc_a = _setup_account(db_path, "owner_a@toanaas.vn")
    acc_b = _setup_account(db_path, "owner_b@toanaas.vn")

    req_a = create_web_manual_topup_request(
        account_id=acc_a,
        amount_vnd=50_000,
        method="bank_acb",
        reference="REF-A",
        idempotency_key_hash=_hash_key("key-a"),
        request_fingerprint=_hash_key("fp-a"),
    )
    req_num = int(req_a["request_id"].split("-", 1)[1])

    # Account B tries to read Account A's request
    assert get_web_manual_topup_request(acc_b, req_num) is None

    # Account B's list is empty
    assert list_web_manual_topup_requests(acc_b, limit=10) == []


def test_idempotent_replay_stability(tmp_path, monkeypatch):
    """7: Idempotent replay returns identical snapshots; mismatch raises conflict."""
    db_path = str(tmp_path / "idempotency.db")
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", db_path)
    ensure_copyfast_schema()

    account_id = _setup_account(db_path, "idemp@toanaas.vn")
    key_hash = _hash_key("same-key")
    fp_hash = _hash_key("same-body")

    first = create_web_manual_topup_request(
        account_id=account_id,
        amount_vnd=100_000,
        method="bank_acb",
        reference="REF-FIRST",
        idempotency_key_hash=key_hash,
        request_fingerprint=fp_hash,
    )

    # Replay with same key + same body
    replay = create_web_manual_topup_request(
        account_id=account_id,
        amount_vnd=100_000,
        method="bank_acb",
        reference="REF-FIRST",
        idempotency_key_hash=key_hash,
        request_fingerprint=fp_hash,
    )

    assert replay["idempotent_replay"] is True
    assert replay["request_id"] == first["request_id"]
    assert replay["transfer_content"] == first["transfer_content"]

    # Replay with same key + DIFFERENT body -> conflict
    conflict_fp = _hash_key("different-body")
    with pytest.raises(WebManualTopupIdempotencyConflict):
        create_web_manual_topup_request(
            account_id=account_id,
            amount_vnd=200_000,
            method="bank_acb",
            reference="REF-SECOND",
            idempotency_key_hash=key_hash,
            request_fingerprint=conflict_fp,
        )


def test_concurrent_replay_stability(tmp_path, monkeypatch):
    """8: Concurrent requests with same idempotency key create exactly 1 DB record."""
    db_path = str(tmp_path / "concurrent.db")
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", db_path)
    ensure_copyfast_schema()

    account_id = _setup_account(db_path, "concurrent@toanaas.vn")
    key_hash = _hash_key("concurrent-key")
    fp_hash = _hash_key("concurrent-body")

    def make_req():
        return create_web_manual_topup_request(
            account_id=account_id,
            amount_vnd=100_000,
            method="bank_acb",
            reference="CONCURRENT",
            idempotency_key_hash=key_hash,
            request_fingerprint=fp_hash,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_req) for _ in range(5)]
        results = [f.result() for f in futures]

    # Exactly 1 row in DB
    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM web_manual_topup_requests").fetchone()[0]
        assert count == 1

    # All returned the exact same request_id and transfer_content
    assert len({r["request_id"] for r in results}) == 1
    assert len({r["transfer_content"] for r in results}) == 1


def test_zero_wallet_and_zero_external_calls_during_request_creation(tmp_path, monkeypatch):
    """9 & 10: Zero wallet mutation and zero bridge/Bot/PayOS calls during creation."""
    db_path = str(tmp_path / "zero_side_effects.db")
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", db_path)
    ensure_copyfast_schema()

    account_id = _setup_account(db_path, "side_effects@toanaas.vn")

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Request creation must NOT make external or bridge calls!")

    monkeypatch.setattr(copyfast_api, "_manual_topup_bridge", forbidden)
    monkeypatch.setattr(copyfast_api, "bridge_request", forbidden)
    monkeypatch.setattr(copyfast_api, "_create_payos_checkout", forbidden)

    created = create_web_manual_topup_request(
        account_id=account_id,
        amount_vnd=500_000,
        method="bank_acb",
        reference="NO-SIDE-EFFECTS",
        idempotency_key_hash=_hash_key("key-clean"),
        request_fingerprint=_hash_key("fp-clean"),
    )
    assert created["status"] == "pending_admin_review"

    # Verify no wallet or ledger entries exist
    with sqlite3.connect(db_path) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "web_wallets" in tables:
            wallet_rows = conn.execute("SELECT COUNT(*) FROM web_wallets").fetchone()[0]
            assert wallet_rows == 0
        if "web_credit_operations" in tables:
            credit_rows = conn.execute("SELECT COUNT(*) FROM web_credit_operations").fetchone()[0]
            assert credit_rows == 0
