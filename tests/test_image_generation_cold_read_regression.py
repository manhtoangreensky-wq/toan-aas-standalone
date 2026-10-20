"""Focused regression tests for Image Generation cold-read schema presence.

Verifies that get_image_generation_job, list_image_generation_jobs, and
is_image_generation_job_other_account are completely safe on cold/new SQLite
databases where web_image_generation_jobs does not yet exist.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
import pytest

from copyfast_db import read_transaction
from copyfast_image_generation_job_bridge import (
    create_or_replay_image_generation_job,
    ensure_image_generation_schema,
    get_image_generation_job,
    is_image_generation_job_other_account,
    list_image_generation_jobs,
)


@pytest.fixture
def cold_db_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide a fresh, empty SQLite database with zero tables."""
    db_file = tmp_path / "cold_test_session.db"
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(db_file))
    return db_file


def test_reproduce_before_fix_raw_cold_read_raises_operational_error(cold_db_env: Path) -> None:
    """Re-prove BEFORE_FIX_REPRODUCED: querying uninitialized cold DB raises OperationalError."""
    with read_transaction() as conn:
        with pytest.raises(sqlite3.OperationalError) as exc_info:
            conn.execute(
                "SELECT * FROM web_image_generation_jobs WHERE id = ?",
                ("img_nonexistent",),
            )
        assert "no such table: web_image_generation_jobs" in str(exc_info.value).lower()


def test_case_a_cold_db_get_image_generation_job_returns_none(cold_db_env: Path) -> None:
    """Case A: cold DB + get_image_generation_job -> no OperationalError, returns None."""
    result = get_image_generation_job("account_test_a", "img_absent_123")
    assert result is None


def test_case_b_cold_db_list_image_generation_jobs_returns_empty_list(cold_db_env: Path) -> None:
    """Case B: cold DB + list_image_generation_jobs -> no OperationalError, returns []."""
    result = list_image_generation_jobs("account_test_b")
    assert result == []


def test_case_c_cold_db_is_image_generation_job_other_account_returns_false(cold_db_env: Path) -> None:
    """Case C: cold DB + is_image_generation_job_other_account -> no OperationalError, returns False."""
    result = is_image_generation_job_other_account("img_absent_123", "account_test_c")
    assert result is False


def test_case_d_existing_schema_owner_job_preserved(cold_db_env: Path) -> None:
    """Case D: existing schema + owner job retrieval and listing preserved."""
    from copyfast_db import ensure_copyfast_schema, transaction
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO web_accounts (id, email, password_hash, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("account_owner_d", "owner_d@test.local", "hash", "2026-10-19T00:00:00", "2026-10-19T00:00:00"),
        )

    created = create_or_replay_image_generation_job(
        account_id="account_owner_d",
        payload={"prompt": "A cinematic shot of a mountain peak at dawn", "tier": "standard"},
        idempotency_key="idemp_case_d",
    )
    job_id = created["id"]
    assert job_id.startswith("img_")

    retrieved = get_image_generation_job("account_owner_d", job_id)
    assert retrieved is not None
    assert retrieved["id"] == job_id
    assert retrieved["account_id"] == "account_owner_d"
    assert retrieved["prompt"] == "A cinematic shot of a mountain peak at dawn"
    assert retrieved["tier_key"] == "standard"
    assert retrieved["status"] == "queued"

    job_list = list_image_generation_jobs("account_owner_d")
    assert len(job_list) == 1
    assert job_list[0]["id"] == job_id


def test_case_e_existing_schema_cross_account_isolation_preserved(cold_db_env: Path) -> None:
    """Case E: existing schema + cross-account isolation and ownership check preserved."""
    from copyfast_db import ensure_copyfast_schema, transaction
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO web_accounts (id, email, password_hash, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("account_real_owner", "real_owner@test.local", "hash", "2026-10-19T00:00:00", "2026-10-19T00:00:00"),
        )
        conn.execute(
            "INSERT OR REPLACE INTO web_accounts (id, email, password_hash, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("account_intruder", "intruder@test.local", "hash", "2026-10-19T00:00:00", "2026-10-19T00:00:00"),
        )

    created = create_or_replay_image_generation_job(
        account_id="account_real_owner",
        payload={"prompt": "A modern architectural villa in autumn foliage", "tier": "standard"},
        idempotency_key="idemp_case_e",
    )
    job_id = created["id"]

    # Cross-account reader sees None
    intruder_read = get_image_generation_job("account_intruder", job_id)
    assert intruder_read is None

    # is_image_generation_job_other_account returns True for other account
    assert is_image_generation_job_other_account(job_id, "account_intruder") is True

    # is_image_generation_job_other_account returns False for real owner
    assert is_image_generation_job_other_account(job_id, "account_real_owner") is False


def test_case_f_repeated_reads_schema_bootstrap_remains_idempotent(cold_db_env: Path) -> None:
    """Case F: repeated cold and subsequent reads execute without DDL/idempotency failure."""
    for i in range(10):
        assert get_image_generation_job("account_loop", f"img_loop_{i}") is None
        assert list_image_generation_jobs("account_loop") == []
        assert is_image_generation_job_other_account(f"img_loop_{i}", "account_loop") is False

    # Verify table and indexes exist exactly once and are intact
    with read_transaction() as conn:
        tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        assert "web_image_generation_jobs" in tables
        indexes = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()]
        assert "idx_web_image_generation_jobs_account_created" in indexes
        assert "idx_web_image_generation_jobs_request" in indexes
        assert "idx_web_image_generation_jobs_account_idempotency" in indexes
        assert "idx_web_image_generation_jobs_status_created" in indexes
