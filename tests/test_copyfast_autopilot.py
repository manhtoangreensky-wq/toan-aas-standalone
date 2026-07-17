"""Critical contracts for controlled Web Operations Autopilot.

The suite uses only the signed Web app database and deterministic policy.  It
does not call any external service or claim a provider/payment/job result.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib
import sqlite3
import sys
import uuid

from fastapi.testclient import TestClient

from copyfast_autopilot_protocol import PROTOCOL_VERSION, canonical_json, sign_tick


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry", "copyfast_api",
    "copyfast_projects", "copyfast_assets", "copyfast_project_packages", "copyfast_document_operations",
    "copyfast_image_runtime", "copyfast_image_operations", "copyfast_image_studio", "copyfast_document_workspace",
    "copyfast_chat_workspace", "copyfast_analytics_workspace", "copyfast_workboard", "copyfast_memory",
    "copyfast_prompt_library", "copyfast_music_media", "copyfast_content_studio", "copyfast_voice_studio",
    "copyfast_video_studio", "copyfast_subtitle_workspace", "copyfast_support", "copyfast_autopilot",
]

TICK_SECRET = "t" * 32
INCIDENT_SECRET = "i" * 32


def make_client(tmp_path, monkeypatch, *, enabled: bool = True, remediation: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "operations-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "operations-test-session-secret")
    monkeypatch.setenv("WEBAPP_AUTOPILOT_ENABLED", "true" if enabled else "false")
    monkeypatch.setenv("WEBAPP_AUTOPILOT_SAFE_REMEDIATION_ENABLED", "true" if remediation else "false")
    monkeypatch.setenv("WEBAPP_AUTOPILOT_TICK_SECRET", TICK_SECRET)
    monkeypatch.setenv("WEBAPP_AUTOPILOT_INCIDENT_SECRET", INCIDENT_SECRET)
    monkeypatch.setenv("WEBAPP_AUTOPILOT_TICK_KEY_ID", "primary")
    monkeypatch.setenv("WEBAPP_AUTOPILOT_TOPOLOGY", "sqlite_single_replica")
    for name in ("APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Operations Owner"},
    )
    assert registered.status_code == 200
    return sign_in(client, email)


def sign_in(client: TestClient, email: str) -> str:
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def account_id_for_email(db_path, email: str) -> str:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()
    assert row is not None
    return str(row[0])


def fixture_uuid(kind: str, index: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"https://toanaas.vn/tests/operations-pagination/{kind}/{index}"))


def fixture_timestamp(index: int) -> str:
    return (datetime(2030, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=index)).isoformat(timespec="seconds")


def seed_operation_incidents(db_path, *, account_id: str, count: int, prefix: str) -> list[str]:
    """Seed only local table rows so list-page boundaries stay focused."""

    incident_ids = [fixture_uuid(f"incident-{prefix}", index) for index in range(1, count + 1)]
    rows = []
    for index, incident_id in enumerate(incident_ids, start=1):
        timestamp = fixture_timestamp(index)
        rows.append(
            (
                incident_id,
                f"incident-fingerprint-{prefix}-{index}",
                "support_case_triage",
                "web_support",
                account_id,
                None,
                "open",
                "medium",
                0,
                0,
                index,
                None,
                timestamp,
                timestamp,
                None,
                None,
                index,
            )
        )
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            """INSERT INTO web_ops_incidents
               (id, fingerprint, kind, scope_kind, account_id, support_case_id, state, severity,
                auto_close_eligible, healthy_streak, observation_count, last_failure_at,
                first_observed_at, last_observed_at, resolved_at, closed_at, revision)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        conn.commit()
    return incident_ids


def seed_operation_admin_queues(db_path, *, account_id: str, count: int) -> tuple[list[str], list[str], list[str]]:
    """Build deterministic, redacted-safe local rows for independent queues."""

    run_ids = [fixture_uuid("run", index) for index in range(1, count + 1)]
    incident_ids = [fixture_uuid("admin-incident", index) for index in range(1, count + 1)]
    approval_ids = [fixture_uuid("approval", index) for index in range(1, count + 1)]
    run_rows = []
    incident_rows = []
    approval_rows = []
    for index in range(1, count + 1):
        timestamp = fixture_timestamp(index)
        expires_at = fixture_timestamp(10_000 + index)
        run_rows.append(
            (
                run_ids[index - 1],
                f"operations-pagination-request-{index}",
                "railway_cron",
                f"2026-07-16T00:{index % 60:02d}:00+00:00",
                "completed",
                index,
                1,
                f"input-hash-{index}",
                0,
                0,
                0,
                expires_at,
                timestamp,
                timestamp,
                None,
                "{}",
            )
        )
        incident_rows.append(
            (
                incident_ids[index - 1],
                f"admin-incident-fingerprint-{index}",
                "support_case_triage",
                "web_support",
                account_id,
                None,
                "open",
                "medium",
                0,
                0,
                index,
                None,
                timestamp,
                timestamp,
                None,
                None,
                index,
            )
        )
        approval_rows.append(
            (
                approval_ids[index - 1],
                f"approval-proposal-fingerprint-{index}",
                "payment_refund",
                account_id,
                None,
                None,
                "financial",
                "manager",
                "awaiting_approval",
                index,
                f"approval-payload-hash-{index}",
                None,
                timestamp,
                expires_at,
                None,
                None,
                "",
            )
        )
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            """INSERT INTO web_ops_runs
               (id, request_id, trigger, schedule_slot, state, fence_token, policy_version, input_hash,
                action_count, triaged_case_count, incident_count, deadline_at, started_at, finished_at,
                error_code, receipt_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            run_rows,
        )
        conn.executemany(
            """INSERT INTO web_ops_incidents
               (id, fingerprint, kind, scope_kind, account_id, support_case_id, state, severity,
                auto_close_eligible, healthy_streak, observation_count, last_failure_at,
                first_observed_at, last_observed_at, resolved_at, closed_at, revision)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            incident_rows,
        )
        conn.executemany(
            """INSERT INTO web_ops_approvals
               (id, proposal_fingerprint, action_type, account_id, support_case_id, incident_id, risk,
                required_role, state, revision, payload_hash, proposed_by_run_id, proposed_at, expires_at,
                decided_at, decided_by_account_id, decision_code)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            approval_rows,
        )
        conn.commit()
    return run_ids, incident_ids, approval_ids


def assert_paged_ids(client: TestClient, path: str, expected_ids: set[str], *, limit: int) -> None:
    pages: list[set[str]] = []
    total = len(expected_ids)
    for offset in range(0, total, limit):
        expected_count = min(limit, total - offset)
        has_more = offset + expected_count < total
        next_offset = offset + limit if has_more else None
        response = client.get(f"{path}?limit={limit}&offset={offset}")
        assert response.status_code == 200 and response.json()["ok"] is True
        data = response.json()["data"]
        assert len(data["items"]) == expected_count
        assert data["has_more"] is has_more
        assert data["next_offset"] == next_offset
        pages.append({str(item["id"]) for item in data["items"]})
    assert all(first.isdisjoint(second) for index, first in enumerate(pages) for second in pages[index + 1:])
    assert set().union(*pages) == expected_ids


def tick_headers(*, body: bytes, timestamp: str | None = None, nonce: str | None = None, request_id: str | None = None) -> dict[str, str]:
    timestamp = timestamp or datetime.now(timezone.utc).replace(microsecond=0).isoformat(timespec="seconds")
    nonce = nonce or ("N" * 24)
    request_id = request_id or str(uuid.uuid4())
    return {
        "Content-Type": "application/json",
        "X-Ops-Timestamp": timestamp,
        "X-Ops-Nonce": nonce,
        "X-Ops-Request-Id": request_id,
        "X-Ops-Key-Id": "primary",
        "X-Ops-Signature": sign_tick(
            secret=TICK_SECRET, timestamp=timestamp, nonce=nonce, request_id=request_id, key_id="primary", body=body,
        ),
    }


def tick_body(timestamp: str | None = None) -> tuple[bytes, str]:
    timestamp = timestamp or datetime.now(timezone.utc).replace(microsecond=0).isoformat(timespec="seconds")
    return canonical_json({"protocol_version": PROTOCOL_VERSION, "trigger": "railway_cron", "requested_at": timestamp}), timestamp


def test_autopilot_fail_closed_and_rejects_oversized_or_bad_hmac_before_persistence(tmp_path, monkeypatch):
    db_path = tmp_path / "operations-test.db"
    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        assert client.get("/api/v1/operations/status").status_code == 401
        csrf = login(client, "operations-disabled@example.com")
        assert client.get("/api/v1/operations/status").status_code == 503
        body, timestamp = tick_body()
        paused = client.post(
            "/internal/v1/operations/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="D" * 24),
            content=body,
        )
        assert paused.status_code == 200 and paused.json()["status"] == "guarded"
        assert paused.json()["data"]["guarded_code"] == "OPS_AUTOPILOT_DISABLED"
        assert csrf
    with make_client(tmp_path, monkeypatch, enabled=True) as client:
        huge = client.post(
            "/internal/v1/operations/tick",
            headers={"Content-Type": "application/json"},
            content=b"{" + (b"x" * (9 * 1024)) + b"}",
        )
        assert huge.status_code == 413
        assert huge.json()["error_code"] == "WEB_AUTOPILOT_TICK_BODY_TOO_LARGE"
        approval_huge = client.post(
            f"/api/v1/operations/admin/approvals/{uuid.uuid4()}/approve",
            headers={"Content-Type": "application/json"},
            content=b"{" + (b"x" * (9 * 1024)) + b"}",
        )
        assert approval_huge.status_code == 413
        assert approval_huge.json()["error_code"] == "WEB_AUTOPILOT_APPROVAL_BODY_TOO_LARGE"
        body, timestamp = tick_body()
        bad = client.post(
            "/internal/v1/operations/tick",
            headers={**tick_headers(body=body, timestamp=timestamp), "X-Ops-Signature": "0" * 64},
            content=body,
        )
        assert bad.status_code == 401
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM web_ops_nonces").fetchone()[0] == 1
        assert conn.execute("SELECT state, error_code FROM web_ops_runs").fetchall() == [
            ("guarded", "OPS_AUTOPILOT_DISABLED"),
        ]


def test_tick_replay_safe_triage_owner_scope_and_approval_record_only(tmp_path, monkeypatch):
    db_path = tmp_path / "operations-test.db"
    with make_client(tmp_path, monkeypatch, enabled=True, remediation=True) as client:
        csrf = login(client, "operations-owner@example.com")
        created = client.post(
            "/api/v1/support/cases",
            headers={"X-CSRF-Token": csrf},
            json={
                "category": "refund", "priority": "urgent", "subject": "Cần tra xét giao dịch dịch vụ",
                "detail": "Tôi cần nhân sự kiểm tra yêu cầu hoàn tiền theo quy trình an toàn.",
                "idempotency_key": "operations-support-case-0001",
            },
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        case_id = created.json()["data"]["case"]["id"]
        body, timestamp = tick_body()
        request_id = str(uuid.uuid4())
        headers = tick_headers(body=body, timestamp=timestamp, nonce="R" * 24, request_id=request_id)
        first = client.post("/internal/v1/operations/tick", headers=headers, content=body)
        assert first.status_code == 200 and first.json()["ok"] is True
        assert first.json()["status"] == "completed"
        boundary = first.json()["data"]
        for key in ("bot_called", "provider_called", "wallet_mutated", "payment_mutated", "customer_reply_sent", "deployment_changed", "self_modifying_code"):
            assert boundary[key] is False
        replay = client.post("/internal/v1/operations/tick", headers=headers, content=body)
        assert replay.status_code == 200 and replay.json()["status"] == "guarded"
        assert replay.json()["data"]["guarded_code"] == "OPS_TICK_REPLAYED"
        triage = client.get(f"/api/v1/support/cases/{case_id}/triage")
        assert triage.status_code == 200 and triage.json()["ok"] is True
        triage_data = triage.json()["data"]["triage"]
        assert triage_data["risk"] == "financial"
        assert triage_data["disposition"] == "awaiting_operator"
        assert triage_data["sla_status"] == "within_target"
        approval_list = client.get("/api/v1/operations/admin/approvals")
        assert approval_list.status_code == 403
        other_csrf = login(client, "operations-other@example.com")
        hidden = client.get(f"/api/v1/support/cases/{case_id}/triage")
        assert hidden.status_code == 200
        assert hidden.json()["error_code"] == "WEB_SUPPORT_CASE_NOT_FOUND"
        assert other_csrf
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM web_ops_runs").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM web_ops_nonces").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM web_support_triage").fetchone()[0] == 1
        approval = conn.execute("SELECT id, state, action_type FROM web_ops_approvals").fetchone()
        assert approval and approval[1] == "awaiting_approval" and approval[2] == "payment_refund"
        triage_columns = {row[1] for row in conn.execute("PRAGMA table_info(web_support_triage)").fetchall()}
        assert "detail" not in triage_columns and "subject" not in triage_columns

    with make_client(tmp_path, monkeypatch, enabled=True, remediation=True) as client:
        csrf = client.post(
            "/api/v1/auth/login",
            json={"email": "operations-owner@example.com", "password": "correct-horse-battery-staple"},
        ).json()["data"]["csrf_token"]
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_accounts SET role_cache='support_manager' WHERE email=?", ("operations-owner@example.com",))
            conn.commit()
            approval_id, _state, _action = conn.execute("SELECT id, state, action_type FROM web_ops_approvals").fetchone()
        approvals = client.get("/api/v1/operations/admin/approvals")
        assert approvals.status_code == 200 and approvals.json()["ok"] is True
        decision = client.post(
            f"/api/v1/operations/admin/approvals/{approval_id}/approve",
            headers={"X-CSRF-Token": csrf},
            json={
                "expected_revision": 1, "confirm": True, "decision_code": "review-verified",
                "idempotency_key": "operations-approval-wrong-code-0001",
            },
        )
        assert decision.status_code == 422
        decision = client.post(
            f"/api/v1/operations/admin/approvals/{approval_id}/approve",
            headers={"X-CSRF-Token": csrf},
            json={
                "expected_revision": 1, "confirm": True, "decision_code": "manager_approved",
                "idempotency_key": "operations-approval-approve-0001",
            },
        )
        assert decision.status_code == 200 and decision.json()["ok"] is True
        decided = decision.json()["data"]
        assert decided["approval"]["state"] == "approved"
        assert decided["dangerous_action_executed"] is False
        assert decided["provider_called"] is False
        assert decided["payment_mutated"] is False


def test_tick_observes_only_when_safe_remediation_is_off(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch, enabled=True, remediation=False) as client:
        body, timestamp = tick_body()
        response = client.post("/internal/v1/operations/tick", headers=tick_headers(body=body, timestamp=timestamp), content=body)
        assert response.status_code == 200 and response.json()["ok"] is True
        assert response.json()["status"] == "guarded"
        assert response.json()["data"]["guarded_code"] == "OPS_SAFE_REMEDIATION_DISABLED"


def test_autopilot_uses_customer_waiting_clock_not_generic_case_update_time(tmp_path, monkeypatch):
    """Internal record churn must never make an overdue customer wait healthy."""

    db_path = tmp_path / "operations-test.db"
    with make_client(tmp_path, monkeypatch, enabled=True, remediation=True) as client:
        csrf = login(client, "operations-sla-clock@example.com")
        created = client.post(
            "/api/v1/support/cases",
            headers={"X-CSRF-Token": csrf},
            json={
                "category": "general_support", "priority": "urgent", "subject": "Cần Customer Care phản hồi",
                "detail": "Yêu cầu Web Support đang chờ phản hồi để kiểm tra SLA nội bộ.",
                "idempotency_key": "operations-sla-clock-case-0001",
            },
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        case_id = str(created.json()["data"]["case"]["id"])
        old_wait = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(timespec="seconds")
        fresh_internal_update = datetime.now(timezone.utc).replace(microsecond=0).isoformat(timespec="seconds")
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE web_support_cases SET customer_waiting_since=?, updated_at=? WHERE id=?",
                (old_wait, fresh_internal_update, case_id),
            )
            conn.commit()
        body, timestamp = tick_body()
        tick = client.post(
            "/internal/v1/operations/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="S" * 24),
            content=body,
        )
        assert tick.status_code == 200 and tick.json()["status"] == "completed"
    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT sla_status FROM web_support_triage WHERE case_id=?", (case_id,)
        ).fetchone() == ("breached",)
        assert conn.execute(
            "SELECT COUNT(*) FROM web_ops_incidents WHERE support_case_id=?", (case_id,)
        ).fetchone() == (1,)


def test_autopilot_fails_closed_when_semantic_sla_clock_is_absent(tmp_path, monkeypatch):
    """A legacy/malformed record cannot become a false SLA breach or recovery."""

    db_path = tmp_path / "operations-test.db"
    with make_client(tmp_path, monkeypatch, enabled=True, remediation=True) as client:
        csrf = login(client, "operations-sla-clock-legacy@example.com")
        created = client.post(
            "/api/v1/support/cases",
            headers={"X-CSRF-Token": csrf},
            json={
                "category": "general_support", "priority": "urgent", "subject": "Legacy SLA marker",
                "detail": "Bản ghi kiểm tra thiếu đồng hồ chờ phản hồi ngữ nghĩa.",
                "idempotency_key": "operations-sla-clock-legacy-0001",
            },
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        case_id = str(created.json()["data"]["case"]["id"])
        old_generic_update = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(timespec="seconds")
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE web_support_cases SET customer_waiting_since=NULL, updated_at=? WHERE id=?",
                (old_generic_update, case_id),
            )
            conn.commit()
        body, timestamp = tick_body()
        tick = client.post(
            "/internal/v1/operations/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="U" * 24),
            content=body,
        )
        assert tick.status_code == 200 and tick.json()["status"] == "completed"
    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT sla_status FROM web_support_triage WHERE case_id=?", (case_id,)
        ).fetchone() == ("unverified",)
        assert conn.execute(
            "SELECT COUNT(*) FROM web_ops_incidents WHERE support_case_id=?", (case_id,)
        ).fetchone() == (0,)


def test_tick_guards_missing_incident_key_and_unverified_replica_topology_without_starting_a_run(tmp_path, monkeypatch):
    db_path = tmp_path / "operations-test.db"
    with make_client(tmp_path, monkeypatch, enabled=True, remediation=True) as client:
        monkeypatch.delenv("WEBAPP_AUTOPILOT_INCIDENT_SECRET", raising=False)
        body, timestamp = tick_body()
        missing_key = client.post(
            "/internal/v1/operations/tick", headers=tick_headers(body=body, timestamp=timestamp, nonce="I" * 24), content=body,
        )
        assert missing_key.status_code == 200
        assert missing_key.json()["status"] == "guarded"
        assert missing_key.json()["data"]["guarded_code"] == "OPS_INCIDENT_SECRET_UNAVAILABLE"
        monkeypatch.setenv("WEBAPP_AUTOPILOT_INCIDENT_SECRET", INCIDENT_SECRET)
        monkeypatch.setenv("RAILWAY_REPLICA_COUNT", "2")
        body, timestamp = tick_body()
        replica_headers = tick_headers(body=body, timestamp=timestamp, nonce="M" * 24)
        multiple_replicas = client.post(
            "/internal/v1/operations/tick", headers=replica_headers, content=body,
        )
        assert multiple_replicas.status_code == 200
        assert multiple_replicas.json()["data"]["guarded_code"] == "OPS_MULTI_REPLICA_BLOCKED"
        monkeypatch.delenv("RAILWAY_REPLICA_COUNT", raising=False)
        replay_after_guard = client.post(
            "/internal/v1/operations/tick",
            headers=replica_headers,
            content=body,
        )
        assert replay_after_guard.status_code == 200
        assert replay_after_guard.json()["data"]["guarded_code"] == "OPS_TICK_REPLAYED"
    with sqlite3.connect(db_path) as conn:
        assert set(conn.execute("SELECT state, error_code FROM web_ops_runs").fetchall()) == {
            ("guarded", "OPS_INCIDENT_SECRET_UNAVAILABLE"),
            ("guarded", "OPS_MULTI_REPLICA_BLOCKED"),
        }


def test_invalid_scheduler_limits_are_guarded_and_consume_the_signed_nonce(tmp_path, monkeypatch):
    """A malformed Cron limit must not trigger Railway retry/failure mail loops."""
    db_path = tmp_path / "operations-test.db"
    monkeypatch.setenv("WEBAPP_AUTOPILOT_MAX_RUN_SECONDS", "not-an-integer")
    with make_client(tmp_path, monkeypatch, enabled=True, remediation=True) as client:
        body, timestamp = tick_body()
        headers = tick_headers(body=body, timestamp=timestamp, nonce="B" * 24, request_id=str(uuid.uuid4()))
        guarded = client.post("/internal/v1/operations/tick", headers=headers, content=body)
        assert guarded.status_code == 200 and guarded.json()["status"] == "guarded"
        assert guarded.json()["data"]["guarded_code"] == "OPS_MAX_RUN_SECONDS_UNVERIFIED"
        # A repaired environment never turns the exact same signed request
        # into an execution; its nonce/request identity was retained.
        monkeypatch.setenv("WEBAPP_AUTOPILOT_MAX_RUN_SECONDS", "20")
        replay = client.post("/internal/v1/operations/tick", headers=headers, content=body)
        assert replay.status_code == 200 and replay.json()["status"] == "guarded"
        assert replay.json()["data"]["guarded_code"] == "OPS_TICK_REPLAYED"

        monkeypatch.setenv("WEBAPP_AUTOPILOT_MAX_ACTIONS_PER_RUN", "0")
        body_two, timestamp_two = tick_body()
        second = client.post(
            "/internal/v1/operations/tick",
            headers=tick_headers(body=body_two, timestamp=timestamp_two, nonce="C" * 24, request_id=str(uuid.uuid4())),
            content=body_two,
        )
        assert second.status_code == 200 and second.json()["status"] == "guarded"
        assert second.json()["data"]["guarded_code"] == "OPS_MAX_ACTIONS_UNVERIFIED"
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM web_ops_nonces").fetchone()[0] == 2
        assert set(conn.execute("SELECT state, error_code FROM web_ops_runs").fetchall()) == {
            ("guarded", "OPS_MAX_RUN_SECONDS_UNVERIFIED"),
            ("guarded", "OPS_MAX_ACTIONS_UNVERIFIED"),
        }


def test_terminal_case_reconciliation_closes_only_local_incident_and_supersedes_proposal(tmp_path, monkeypatch):
    db_path = tmp_path / "operations-test.db"
    with make_client(tmp_path, monkeypatch, enabled=True, remediation=True) as client:
        csrf = login(client, "operations-terminal@example.com")
        created = client.post(
            "/api/v1/support/cases",
            headers={"X-CSRF-Token": csrf},
            json={
                "category": "refund", "priority": "urgent", "subject": "Cần tra xét giao dịch cũ",
                "detail": "Yêu cầu Web này cần được nhân sự xem lại theo quy trình an toàn.",
                "idempotency_key": "operations-terminal-case-0001",
            },
        )
        assert created.status_code == 200
        case_id = created.json()["data"]["case"]["id"]
        with sqlite3.connect(db_path) as conn:
            old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(timespec="seconds")
            conn.execute("UPDATE web_support_cases SET customer_waiting_since=? WHERE id=?", (old, case_id))
            conn.commit()
        body, timestamp = tick_body()
        first = client.post(
            "/internal/v1/operations/tick", headers=tick_headers(body=body, timestamp=timestamp, nonce="T" * 24), content=body,
        )
        assert first.status_code == 200 and first.json()["status"] == "completed"
        detail = client.get(f"/api/v1/support/cases/{case_id}")
        assert detail.status_code == 200
        revision = detail.json()["data"]["case"]["revision"]
        closed = client.post(
            f"/api/v1/support/cases/{case_id}/close",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": revision, "confirm": True, "idempotency_key": "operations-terminal-close-0001"},
        )
        assert closed.status_code == 200
        body, timestamp = tick_body()
        reconciled = client.post(
            "/internal/v1/operations/tick", headers=tick_headers(body=body, timestamp=timestamp, nonce="U" * 24), content=body,
        )
        assert reconciled.status_code == 200 and reconciled.json()["ok"] is True
        assert reconciled.json()["data"]["terminal_reconciled_count"] >= 2
    with sqlite3.connect(db_path) as conn:
        triage = conn.execute("SELECT case_state, sla_status FROM web_support_triage WHERE case_id=?", (case_id,)).fetchone()
        incident = conn.execute("SELECT state, closed_at FROM web_ops_incidents WHERE support_case_id=?", (case_id,)).fetchone()
        approval = conn.execute("SELECT state, decision_code FROM web_ops_approvals WHERE support_case_id=?", (case_id,)).fetchone()
        assert triage == ("closed", "terminal")
        assert incident and incident[0] == "closed" and incident[1]
        assert approval == ("superseded", "case_terminal")


def test_action_budget_reconciles_missing_incident_and_approval_on_later_ticks(tmp_path, monkeypatch):
    """A capped triage must not lose its financial/support escalation forever."""
    db_path = tmp_path / "operations-test.db"
    monkeypatch.setenv("WEBAPP_AUTOPILOT_MAX_ACTIONS_PER_RUN", "1")
    with make_client(tmp_path, monkeypatch, enabled=True, remediation=True) as client:
        csrf = login(client, "operations-budget@example.com")
        created = client.post(
            "/api/v1/support/cases",
            headers={"X-CSRF-Token": csrf},
            json={
                "category": "refund", "priority": "urgent", "subject": "Case cần kiểm tra theo SLA",
                "detail": "Nội dung chỉ dùng để tạo support case Web trong test an toàn.",
                "idempotency_key": "operations-budget-case-0001",
            },
        )
        assert created.status_code == 200
        case_id = created.json()["data"]["case"]["id"]
        with sqlite3.connect(db_path) as conn:
            old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(timespec="seconds")
            conn.execute("UPDATE web_support_cases SET customer_waiting_since=? WHERE id=?", (old, case_id))
            conn.commit()
        for nonce in ("B" * 24, "C" * 24, "E" * 24):
            body, timestamp = tick_body()
            response = client.post(
                "/internal/v1/operations/tick",
                headers=tick_headers(body=body, timestamp=timestamp, nonce=nonce),
                content=body,
            )
            assert response.status_code == 200 and response.json()["status"] == "guarded"
            assert response.json()["data"]["guarded_code"] == "OPS_ACTION_BUDGET_REACHED"
            assert response.json()["data"]["payment_mutated"] is False
            assert response.json()["data"]["provider_called"] is False
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM web_support_triage WHERE case_id=?", (case_id,)).fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM web_ops_incidents WHERE support_case_id=?", (case_id,)).fetchone()[0] == 1
        assert conn.execute("SELECT state, action_type FROM web_ops_approvals WHERE support_case_id=?", (case_id,)).fetchone() == (
            "awaiting_approval", "payment_refund",
        )


def test_incident_recovery_needs_consecutive_fresh_web_support_ticks_and_resets_on_rebreach(tmp_path, monkeypatch):
    """Only the local incident converges after repeated healthy Web SLA reads."""

    db_path = tmp_path / "operations-test.db"
    email = "operations-recovery@example.com"
    with make_client(tmp_path, monkeypatch, enabled=True, remediation=True) as client:
        csrf = login(client, email)
        created = client.post(
            "/api/v1/support/cases",
            headers={"X-CSRF-Token": csrf},
            json={
                "category": "general_support", "priority": "normal", "subject": "Cần hỗ trợ thao tác Web",
                "detail": "Chi tiết chỉ dùng để tạo case Web-native trong kiểm thử an toàn.",
                "idempotency_key": "operations-recovery-case-0001",
            },
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        case_id = str(created.json()["data"]["case"]["id"])
        with sqlite3.connect(db_path) as conn:
            source_before = conn.execute(
                "SELECT state, revision, subject, initial_detail FROM web_support_cases WHERE id=?", (case_id,)
            ).fetchone()
            old = (datetime.now(timezone.utc) - timedelta(hours=9)).isoformat(timespec="seconds")
            conn.execute("UPDATE web_support_cases SET customer_waiting_since=? WHERE id=?", (old, case_id))
            conn.commit()

        body, timestamp = tick_body()
        breached = client.post(
            "/internal/v1/operations/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="H" * 24),
            content=body,
        )
        assert breached.status_code == 200 and breached.json()["status"] == "completed"
        with sqlite3.connect(db_path) as conn:
            incident_id = str(conn.execute(
                "SELECT id FROM web_ops_incidents WHERE support_case_id=?", (case_id,)
            ).fetchone()[0])
            assert conn.execute(
                "SELECT state, auto_close_eligible, healthy_streak FROM web_ops_incidents WHERE id=?", (incident_id,)
            ).fetchone() == ("open", 0, 0)
            fresh = datetime.now(timezone.utc).replace(microsecond=0).isoformat(timespec="seconds")
            conn.execute("UPDATE web_support_cases SET customer_waiting_since=? WHERE id=?", (fresh, case_id))
            conn.commit()

        body, timestamp = tick_body()
        first_healthy = client.post(
            "/internal/v1/operations/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="I" * 24),
            content=body,
        )
        assert first_healthy.status_code == 200
        assert first_healthy.json()["data"]["incident_recovery_healthy_observation_count"] == 1
        with sqlite3.connect(db_path) as conn:
            assert conn.execute(
                "SELECT state, auto_close_eligible, healthy_streak FROM web_ops_incidents WHERE id=?", (incident_id,)
            ).fetchone() == ("open", 0, 1)
            old = (datetime.now(timezone.utc) - timedelta(hours=9)).isoformat(timespec="seconds")
            conn.execute("UPDATE web_support_cases SET customer_waiting_since=? WHERE id=?", (old, case_id))
            conn.commit()

        body, timestamp = tick_body()
        rebreached = client.post(
            "/internal/v1/operations/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="J" * 24),
            content=body,
        )
        assert rebreached.status_code == 200 and rebreached.json()["status"] == "completed"
        with sqlite3.connect(db_path) as conn:
            assert conn.execute(
                "SELECT state, auto_close_eligible, healthy_streak FROM web_ops_incidents WHERE id=?", (incident_id,)
            ).fetchone() == ("investigating", 0, 0)
            fresh = datetime.now(timezone.utc).replace(microsecond=0).isoformat(timespec="seconds")
            conn.execute("UPDATE web_support_cases SET customer_waiting_since=? WHERE id=?", (fresh, case_id))
            conn.commit()

        final_payload = None
        for nonce in ("K" * 24, "L" * 24, "M" * 24):
            body, timestamp = tick_body()
            response = client.post(
                "/internal/v1/operations/tick",
                headers=tick_headers(body=body, timestamp=timestamp, nonce=nonce),
                content=body,
            )
            assert response.status_code == 200 and response.json()["status"] == "completed"
            final_payload = response.json()["data"]
        assert final_payload is not None
        assert final_payload["incident_recovery_reconciled_count"] == 1
        assert final_payload["incident_recovery_required_streak"] == 3
        for key in (
            "bot_called", "provider_called", "wallet_mutated", "payment_mutated", "customer_reply_sent",
            "external_notification_sent", "job_retried", "asset_delivery_changed", "deployment_changed",
        ):
            assert final_payload[key] is False

        status = client.get("/api/v1/operations/status")
        assert status.status_code == 200
        assert status.json()["data"]["incident_recovery_policy"] == "incident_recovery_reconciliation"
        assert status.json()["data"]["incident_recovery_reconciled_count"] == 1

    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT state, auto_close_eligible, healthy_streak, closed_at FROM web_ops_incidents WHERE id=?", (incident_id,)
        ).fetchone()[0:3] == ("closed", 1, 3)
        assert conn.execute("SELECT closed_at FROM web_ops_incidents WHERE id=?", (incident_id,)).fetchone()[0]
        assert conn.execute(
            "SELECT state, revision, subject, initial_detail FROM web_support_cases WHERE id=?", (case_id,)
        ).fetchone() == source_before
        observations = {str(row[0]) for row in conn.execute(
            "SELECT observation FROM web_ops_incident_observations WHERE incident_id=?", (incident_id,)
        ).fetchall()}
        assert {"recovery_healthy_tick", "recovery_reconciled"}.issubset(observations)
        assert conn.execute(
            "SELECT COUNT(*) FROM web_ops_playbook_runs WHERE playbook='incident_recovery_reconciliation'"
        ).fetchone()[0] >= 1


def test_incident_recovery_never_closes_when_a_web_support_case_has_pending_approval(tmp_path, monkeypatch):
    """A pending local approval blocks incident closure even after healthy ticks."""

    db_path = tmp_path / "operations-test.db"
    with make_client(tmp_path, monkeypatch, enabled=True, remediation=True) as client:
        csrf = login(client, "operations-recovery-approval@example.com")
        created = client.post(
            "/api/v1/support/cases",
            headers={"X-CSRF-Token": csrf},
            json={
                "category": "general_support", "priority": "normal", "subject": "Case cần staff xem lại",
                "detail": "Nội dung case Web; approval test không gọi hành động ngoài Web.",
                "idempotency_key": "operations-recovery-approval-case-0001",
            },
        )
        assert created.status_code == 200
        case_id = str(created.json()["data"]["case"]["id"])
        with sqlite3.connect(db_path) as conn:
            account_id = str(conn.execute("SELECT account_id FROM web_support_cases WHERE id=?", (case_id,)).fetchone()[0])
            old = (datetime.now(timezone.utc) - timedelta(hours=9)).isoformat(timespec="seconds")
            conn.execute("UPDATE web_support_cases SET customer_waiting_since=? WHERE id=?", (old, case_id))
            conn.commit()
        body, timestamp = tick_body()
        first = client.post(
            "/internal/v1/operations/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="N" * 24),
            content=body,
        )
        assert first.status_code == 200 and first.json()["status"] == "completed"
        with sqlite3.connect(db_path) as conn:
            incident_id = str(conn.execute(
                "SELECT id FROM web_ops_incidents WHERE support_case_id=?", (case_id,)
            ).fetchone()[0])
            now = datetime.now(timezone.utc).replace(microsecond=0).isoformat(timespec="seconds")
            expires = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0).isoformat(timespec="seconds")
            conn.execute(
                """INSERT INTO web_ops_approvals
                   (id, proposal_fingerprint, action_type, account_id, support_case_id, incident_id, risk,
                    required_role, state, revision, payload_hash, proposed_by_run_id, proposed_at, expires_at)
                   VALUES (?, ?, 'provider_retry', ?, ?, ?, 'web_support', 'support_operator',
                           'awaiting_approval', 1, ?, NULL, ?, ?)""",
                (str(uuid.uuid4()), f"recovery-pending-{uuid.uuid4()}", account_id, case_id, incident_id,
                 f"recovery-payload-{uuid.uuid4()}", now, expires),
            )
            conn.execute("UPDATE web_support_cases SET customer_waiting_since=? WHERE id=?", (now, case_id))
            conn.commit()

        for nonce in ("O" * 24, "P" * 24, "Q" * 24):
            body, timestamp = tick_body()
            response = client.post(
                "/internal/v1/operations/tick",
                headers=tick_headers(body=body, timestamp=timestamp, nonce=nonce),
                content=body,
            )
            assert response.status_code == 200 and response.json()["status"] == "completed"
            assert response.json()["data"]["incident_recovery_reconciled_count"] == 0
            assert response.json()["data"]["payment_mutated"] is False
            assert response.json()["data"]["provider_called"] is False
            assert response.json()["data"]["customer_reply_sent"] is False

    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT state, auto_close_eligible, healthy_streak FROM web_ops_incidents WHERE id=?", (incident_id,)
        ).fetchone() == ("open", 0, 0)
        assert conn.execute(
            "SELECT state FROM web_ops_approvals WHERE support_case_id=?", (case_id,)
        ).fetchone() == ("awaiting_approval",)
        assert conn.execute(
            "SELECT state FROM web_support_cases WHERE id=?", (case_id,)
        ).fetchone() == ("new",)


def test_incident_recovery_invalid_streak_is_a_nonce_consuming_guarded_tick(tmp_path, monkeypatch):
    """One healthy tick can never become a close through a malformed setting."""

    monkeypatch.setenv("WEBAPP_AUTOPILOT_INCIDENT_RECOVERY_STREAK", "1")
    with make_client(tmp_path, monkeypatch, enabled=True, remediation=True) as client:
        body, timestamp = tick_body()
        response = client.post(
            "/internal/v1/operations/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="R" * 24),
            content=body,
        )
        assert response.status_code == 200 and response.json()["status"] == "guarded"
        assert response.json()["data"]["guarded_code"] == "OPS_INCIDENT_RECOVERY_STREAK_UNVERIFIED"


def test_expired_approval_is_materialized_only_as_local_record(tmp_path, monkeypatch):
    db_path = tmp_path / "operations-test.db"
    with make_client(tmp_path, monkeypatch, enabled=True, remediation=True) as client:
        csrf = login(client, "operations-expiry@example.com")
        created = client.post(
            "/api/v1/support/cases",
            headers={"X-CSRF-Token": csrf},
            json={
                "category": "refund", "priority": "normal", "subject": "Case có approval hết hạn",
                "detail": "Nội dung test không được sao chép vào telemetry Operations.",
                "idempotency_key": "operations-expiry-case-0001",
            },
        )
        assert created.status_code == 200
        case_id = created.json()["data"]["case"]["id"]
        body, timestamp = tick_body()
        first = client.post(
            "/internal/v1/operations/tick", headers=tick_headers(body=body, timestamp=timestamp, nonce="X" * 24), content=body,
        )
        assert first.status_code == 200 and first.json()["status"] == "completed"
        with sqlite3.connect(db_path) as conn:
            approval_id = conn.execute("SELECT id FROM web_ops_approvals WHERE support_case_id=?", (case_id,)).fetchone()[0]
            past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(timespec="seconds")
            conn.execute("UPDATE web_ops_approvals SET expires_at=? WHERE id=?", (past, approval_id))
            conn.commit()
        body, timestamp = tick_body()
        reconciled = client.post(
            "/internal/v1/operations/tick", headers=tick_headers(body=body, timestamp=timestamp, nonce="Y" * 24), content=body,
        )
        assert reconciled.status_code == 200 and reconciled.json()["status"] == "completed"
        receipt = reconciled.json()["data"]
        assert receipt["approval_expired_count"] == 1
        for key in ("payment_mutated", "provider_called", "job_retried", "customer_reply_sent", "deployment_changed"):
            assert receipt[key] is False
    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT state, decision_code, decided_by_account_id FROM web_ops_approvals WHERE id=?", (approval_id,)
        ).fetchone() == ("expired", "approval_expired", None)
        assert conn.execute(
            "SELECT action, state FROM web_ops_approval_events WHERE approval_id=? AND action='approval_expired'", (approval_id,)
        ).fetchone() == ("approval_expired", "expired")


def test_concurrent_lease_consumes_the_signed_nonce_and_never_runs_it_later(tmp_path, monkeypatch):
    db_path = tmp_path / "operations-test.db"
    with make_client(tmp_path, monkeypatch, enabled=True, remediation=True) as client:
        now_dt = datetime.now(timezone.utc).replace(microsecond=0)
        future = (now_dt + timedelta(days=365)).isoformat(timespec="seconds")
        now = now_dt.isoformat(timespec="seconds")
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """INSERT INTO web_ops_leases (name, owner_run_id, fence_token, acquired_at, expires_at, updated_at)
                   VALUES ('operations_autopilot_tick', 'other-active-run', 9, ?, ?, ?)""",
                (now, future, now),
            )
            conn.commit()
        body, timestamp = tick_body()
        headers = tick_headers(body=body, timestamp=timestamp, nonce="L" * 24, request_id=str(uuid.uuid4()))
        guarded = client.post("/internal/v1/operations/tick", headers=headers, content=body)
        assert guarded.status_code == 200 and guarded.json()["status"] == "guarded"
        assert guarded.json()["data"]["guarded_code"] == "OPS_TICK_LEASE_HELD"
        replay = client.post("/internal/v1/operations/tick", headers=headers, content=body)
        assert replay.status_code == 200 and replay.json()["data"]["guarded_code"] == "OPS_TICK_REPLAYED"
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM web_ops_nonces").fetchone()[0] == 1
        runs = conn.execute("SELECT state, error_code FROM web_ops_runs").fetchall()
        assert runs == [("guarded", "OPS_TICK_LEASE_HELD")]


def test_expired_lease_fences_only_the_abandoned_run_before_takeover(tmp_path, monkeypatch):
    """A later tick may close an old local receipt, never run its work again."""

    db_path = tmp_path / "operations-test.db"
    old_run_id = str(uuid.uuid4())
    old_request_id = str(uuid.uuid4())
    with make_client(tmp_path, monkeypatch, enabled=True, remediation=True) as client:
        now_dt = datetime.now(timezone.utc).replace(microsecond=0)
        past = (now_dt - timedelta(minutes=5)).isoformat(timespec="seconds")
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """INSERT INTO web_ops_runs
                   (id, request_id, trigger, schedule_slot, state, fence_token, policy_version, input_hash,
                    action_count, triaged_case_count, incident_count, deadline_at, started_at, receipt_json)
                   VALUES (?, ?, 'railway_cron', '2026-07-16T00:00', 'started', 7, 1, 'old-input',
                           0, 0, 0, ?, ?, '{}')""",
                (old_run_id, old_request_id, past, past),
            )
            conn.execute(
                """INSERT INTO web_ops_leases (name, owner_run_id, fence_token, acquired_at, expires_at, updated_at)
                   VALUES ('operations_autopilot_tick', ?, 7, ?, ?, ?)""",
                (old_run_id, past, past, past),
            )
            conn.commit()
        body, timestamp = tick_body()
        takeover = client.post(
            "/internal/v1/operations/tick",
            headers=tick_headers(body=body, timestamp=timestamp, nonce="E" * 24),
            content=body,
        )
        assert takeover.status_code == 200 and takeover.json()["status"] == "completed"
    with sqlite3.connect(db_path) as conn:
        old = conn.execute(
            "SELECT state, error_code, finished_at, receipt_json FROM web_ops_runs WHERE id=?", (old_run_id,)
        ).fetchone()
        assert old is not None
        assert old[0] == "guarded"
        assert old[1] == "OPS_TICK_LEASE_EXPIRED"
        assert old[2]
        assert "OPS_TICK_LEASE_EXPIRED" in str(old[3])
        assert conn.execute("SELECT COUNT(*) FROM web_ops_runs WHERE state='started'").fetchone() == (0,)


def test_operations_portal_routes_require_signed_session_and_server_side_staff_role(tmp_path, monkeypatch):
    db_path = tmp_path / "operations-test.db"
    with make_client(tmp_path, monkeypatch, enabled=True, remediation=False) as client:
        unsigned = client.get("/operations", follow_redirects=False)
        assert unsigned.status_code == 307
        assert unsigned.headers["location"].startswith("/login?next=/operations")
        login(client, "operations-portal@example.com")
        customer = client.get("/operations")
        assert customer.status_code == 200
        assert "<title>Operations Autopilot</title>" in customer.text
        forbidden = client.get("/admin/operations")
        assert forbidden.status_code == 403
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_accounts SET role_cache='support_manager' WHERE email=?", ("operations-portal@example.com",))
            conn.commit()
        staff = client.get("/admin/operations")
        assert staff.status_code == 200
        assert "Operations Autopilot" in staff.text
        alias = client.get("/admin/autopilot", follow_redirects=False)
        assert alias.status_code == 307
        assert alias.headers["location"] == "/admin/operations"


def test_operations_customer_incidents_page_101_records_without_cross_account_leakage(tmp_path, monkeypatch):
    """Every customer incident page remains tied to the signed account."""

    db_path = tmp_path / "operations-test.db"
    owner_email = "operations-pagination-owner@example.com"
    other_email = "operations-pagination-other@example.com"
    with make_client(tmp_path, monkeypatch, enabled=True, remediation=False) as client:
        login(client, owner_email)
        assert client.get("/api/v1/operations/status").status_code == 200
        owner_ids = set(
            seed_operation_incidents(
                db_path,
                account_id=account_id_for_email(db_path, owner_email),
                count=101,
                prefix="owner",
            )
        )

        login(client, other_email)
        other_ids = set(
            seed_operation_incidents(
                db_path,
                account_id=account_id_for_email(db_path, other_email),
                count=2,
                prefix="other",
            )
        )
        other = client.get("/api/v1/operations/incidents?limit=30&offset=0")
        assert other.status_code == 200 and other.json()["ok"] is True
        assert {str(item["id"]) for item in other.json()["data"]["items"]} == other_ids
        assert other.json()["data"]["has_more"] is False
        assert other.json()["data"]["next_offset"] is None

        sign_in(client, owner_email)
        assert_paged_ids(client, "/api/v1/operations/incidents", owner_ids, limit=30)
        for invalid_offset in (-1, 10_001):
            assert client.get(f"/api/v1/operations/incidents?limit=30&offset={invalid_offset}").status_code == 422


def test_operations_admin_queues_page_independently_and_reject_non_staff(tmp_path, monkeypatch):
    """Runs, incidents and approval receipts keep independent server cursors."""

    db_path = tmp_path / "operations-test.db"
    staff_email = "operations-pagination-staff@example.com"
    customer_email = "operations-pagination-customer@example.com"
    admin_paths = (
        "/api/v1/operations/admin/runs",
        "/api/v1/operations/admin/incidents",
        "/api/v1/operations/admin/approvals",
    )
    with make_client(tmp_path, monkeypatch, enabled=True, remediation=False) as client:
        login(client, staff_email)
        assert client.get("/api/v1/operations/status").status_code == 200
        staff_id = account_id_for_email(db_path, staff_email)
        run_ids, incident_ids, approval_ids = seed_operation_admin_queues(db_path, account_id=staff_id, count=101)
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_accounts SET role_cache='support_manager' WHERE email=?", (staff_email,))
            conn.commit()

        login(client, customer_email)
        for path in admin_paths:
            assert client.get(f"{path}?limit=50&offset=0").status_code == 403

        sign_in(client, staff_email)
        for path, ids, limit in zip(admin_paths, (set(run_ids), set(incident_ids), set(approval_ids)), (40, 50, 50), strict=True):
            assert_paged_ids(client, path, ids, limit=limit)
            for invalid_offset in (-1, 10_001):
                assert client.get(f"{path}?limit={limit}&offset={invalid_offset}").status_code == 422


def test_operations_approval_queue_and_summary_are_manager_only_without_operator_metadata_or_lookup_oracle(tmp_path, monkeypatch):
    """Approval records are more sensitive than the ordinary staff queue.

    A Support Operator may use the read-only Operations surface, but must not
    learn that an approval exists from an aggregate, a list page, a record ID
    returned to a manager, or a direct guessed decision URL.  The Manager is
    checked first to prove the fixture is real and independently paginated.
    """

    db_path = tmp_path / "operations-test.db"
    manager_email = "operations-approval-manager@example.com"
    operator_email = "operations-approval-operator@example.com"
    with make_client(tmp_path, monkeypatch, enabled=True, remediation=False) as client:
        login(client, manager_email)
        login(client, operator_email)
        assert client.get("/api/v1/operations/status").status_code == 200
        manager_id = account_id_for_email(db_path, manager_email)
        _run_ids, _incident_ids, approval_ids = seed_operation_admin_queues(
            db_path,
            account_id=manager_id,
            count=3,
        )
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_accounts SET role_cache='support_manager' WHERE email=?", (manager_email,))
            conn.execute("UPDATE web_accounts SET role_cache='support_operator' WHERE email=?", (operator_email,))
            conn.commit()

        sign_in(client, manager_email)
        manager_summary = client.get("/api/v1/operations/admin/summary")
        manager_first = client.get("/api/v1/operations/admin/approvals?limit=2&offset=0")
        manager_second = client.get("/api/v1/operations/admin/approvals?limit=2&offset=2")

        operator_csrf = sign_in(client, operator_email)
        operator_summary = client.get("/api/v1/operations/admin/summary")
        operator_list = client.get("/api/v1/operations/admin/approvals?limit=50&offset=0")
        operator_direct = client.post(
            f"/api/v1/operations/admin/approvals/{approval_ids[0]}/approve",
            headers={"X-CSRF-Token": operator_csrf},
            json={
                "expected_revision": 1,
                "confirm": True,
                "decision_code": "manager_approved",
                "idempotency_key": "operations-hidden-approval-0001",
            },
        )

    assert manager_summary.status_code == 200 and manager_summary.json()["ok"] is True
    assert manager_summary.json()["data"]["pending_approvals"] == 3
    manager_page_ids = set()
    for response, expected_count, has_more, next_offset in (
        (manager_first, 2, True, 2),
        (manager_second, 1, False, None),
    ):
        assert response.status_code == 200 and response.json()["ok"] is True
        data = response.json()["data"]
        assert len(data["items"]) == expected_count
        assert data["has_more"] is has_more
        assert data["next_offset"] == next_offset
        manager_page_ids.update(str(item["id"]) for item in data["items"])
        assert all(item["execution"] == "approval_record_only" for item in data["items"])
    assert manager_page_ids == set(approval_ids)

    assert operator_summary.status_code == 200 and operator_summary.json()["ok"] is True
    operator_data = operator_summary.json()["data"]
    assert operator_data["operator_role"] == "operator"
    assert operator_data["approvals_access"] == "manager_only"
    assert operator_data["pending_approvals"] is None

    # Authorization happens before a list query or an approval-id lookup.
    # The response must therefore contain no existence/metadata oracle.
    assert operator_list.status_code == 403
    assert operator_direct.status_code == 403
    rendered = str(operator_list.json()) + str(operator_direct.json()) + str(operator_summary.json())
    for forbidden in (*approval_ids, "payment_refund", "approval-payload-hash", "financial"):
        assert forbidden not in rendered


def test_autopilot_source_stays_outside_external_authorities():
    root = importlib.import_module("pathlib").Path(__file__).parents[1]
    source = (root / "copyfast_autopilot.py").read_text(encoding="utf-8")
    for forbidden in (
        "import bot", "from bot", "import copyfast_bridge", "from copyfast_bridge", "import PayOS", "from PayOS",
        "import wallet", "from wallet", "import requests", "import httpx", "import urllib",
    ):
        assert forbidden not in source
