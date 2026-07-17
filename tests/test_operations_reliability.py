"""Focused P0.AUTO2 contracts for safe Reliability Follow-up automation.

These checks deliberately exercise only Web-native, local records.  A runtime
failure is reduced to a route-family/count bucket; it must never turn into a
provider call, payment action, customer reply, external notification, or a
record containing request-sensitive data.  Follow-up lifecycle writes remain
staff-only and require the same session/CSRF/revision/idempotency controls as
the existing Operations approval record.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import importlib
import importlib.util
import inspect
import sqlite3
import sys
import uuid

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from copyfast_autopilot_protocol import PROTOCOL_VERSION, canonical_json, sign_tick


# The implementation is being added in the same P0.AUTO2 change.  Keeping the
# conditional at collection time prevents an unrelated intermediate checkout
# from becoming red; once the module is present these are ordinary, mandatory
# contract tests (there are no per-test skips or xfails).
pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("copyfast_reliability") is None,
    reason="P0.AUTO2 Reliability Follow-up module has not been added yet",
)


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry", "copyfast_api",
    "copyfast_projects", "copyfast_assets", "copyfast_project_packages", "copyfast_document_operations",
    "copyfast_image_runtime", "copyfast_image_operations", "copyfast_image_studio", "copyfast_document_workspace",
    "copyfast_chat_workspace", "copyfast_analytics_workspace", "copyfast_workboard", "copyfast_memory",
    "copyfast_prompt_library", "copyfast_music_media", "copyfast_content_studio", "copyfast_voice_studio",
    "copyfast_video_studio", "copyfast_subtitle_workspace", "copyfast_support", "copyfast_autopilot",
    "copyfast_reliability",
]

TICK_SECRET = "t" * 32
INCIDENT_SECRET = "i" * 32


def make_client(tmp_path, monkeypatch) -> TestClient:
    """Load a fresh app with every local-only Operations gate enabled."""
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "reliability-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "reliability-test-session-secret")
    monkeypatch.setenv("WEBAPP_AUTOPILOT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_AUTOPILOT_SAFE_REMEDIATION_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_RELIABILITY_FOLLOWUP_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_AUTOPILOT_TICK_SECRET", TICK_SECRET)
    monkeypatch.setenv("WEBAPP_AUTOPILOT_INCIDENT_SECRET", INCIDENT_SECRET)
    monkeypatch.setenv("WEBAPP_AUTOPILOT_TICK_KEY_ID", "primary")
    monkeypatch.setenv("WEBAPP_AUTOPILOT_TOPOLOGY", "sqlite_single_replica")
    # Tests intentionally disable only the process-local capture throttle so
    # six deterministic calls can exercise bucket aggregation. Production
    # keeps the bounded default limiter to protect a failing response path.
    monkeypatch.setenv("WEBAPP_RELIABILITY_CAPTURE_MIN_INTERVAL_MS", "0")
    # Six repetitions is intentionally above the P0 default threshold while
    # remaining well below the bounded scheduler action budget.
    monkeypatch.setenv("WEBAPP_RELIABILITY_SIGNAL_THRESHOLD", "3")
    for name in (
        "APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH",
        "CORE_BRIDGE_BASE_URL", "CORE_BRIDGE_TOKEN", "CORE_BRIDGE_HMAC_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Reliability Tester"},
    )
    assert registered.status_code == 200
    return sign_in(client, email)


def sign_in(client: TestClient, email: str) -> str:
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return str(signed_in.json()["data"]["csrf_token"])


def promote_staff(db_path, email: str, *, role: str = "support_manager") -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE web_accounts SET role_cache=? WHERE email=?", (role, email))
        conn.commit()


def account_id_for_email(db_path, email: str) -> str:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()
    assert row is not None
    return str(row[0])


def seed_reliability_followups(
    db_path,
    *,
    account_id: str,
    count: int,
    required_role: str = "operator",
    fixture_scope: str = "reliability-pagination",
) -> list[str]:
    """Seed isolated local metadata to exercise only list-page boundaries."""

    followup_ids = [
        str(uuid.uuid5(uuid.NAMESPACE_URL, f"https://toanaas.vn/tests/{fixture_scope}/{index}"))
        for index in range(1, count + 1)
    ]
    rows = []
    for index, followup_id in enumerate(followup_ids, start=1):
        timestamp = (datetime(2026, 7, 16, tzinfo=timezone.utc) + timedelta(seconds=index)).isoformat(timespec="seconds")
        rows.append(
            (
                followup_id,
                f"{fixture_scope}-fingerprint-{index}",
                "runtime_signal",
                f"{fixture_scope}-opaque-source-{index}",
                account_id,
                required_role,
                "medium",
                "open",
                index,
                index,
                None,
                timestamp,
                timestamp,
                None,
                None,
            )
        )
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            """INSERT INTO web_ops_followups
               (id, fingerprint, source_kind, source_id, account_id, required_role, severity, state,
                source_revision, revision, created_by_run_id, opened_at, updated_at, acknowledged_at, resolved_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        conn.commit()
    return followup_ids


def assert_reliability_pages(client: TestClient, expected_ids: set[str]) -> None:
    pages: list[set[str]] = []
    for offset, expected_count, has_more, next_offset in ((0, 50, True, 50), (50, 50, True, 100), (100, 1, False, None)):
        response = client.get(f"/api/v1/operations/admin/followups?state=all&severity=all&limit=50&offset={offset}")
        assert response.status_code == 200 and response.json()["ok"] is True
        data = response.json()["data"]
        assert len(data["items"]) == expected_count
        assert data["has_more"] is has_more
        assert data["next_offset"] == next_offset
        pages.append({str(item["id"]) for item in data["items"]})
    assert pages[0].isdisjoint(pages[1])
    assert pages[0].isdisjoint(pages[2])
    assert pages[1].isdisjoint(pages[2])
    assert set().union(*pages) == expected_ids


def tick_body(timestamp: str | None = None) -> tuple[bytes, str]:
    timestamp = timestamp or datetime.now(timezone.utc).replace(microsecond=0).isoformat(timespec="seconds")
    return canonical_json({"protocol_version": PROTOCOL_VERSION, "trigger": "railway_cron", "requested_at": timestamp}), timestamp


def tick_headers(*, body: bytes, timestamp: str, nonce: str) -> dict[str, str]:
    request_id = str(uuid.uuid4())
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


def run_tick(client: TestClient, nonce: str) -> dict:
    body, timestamp = tick_body()
    response = client.post("/internal/v1/operations/tick", headers=tick_headers(body=body, timestamp=timestamp, nonce=nonce), content=body)
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    # The existing scheduler may return completed or a bounded guarded receipt;
    # neither outcome is allowed to invoke an external authority.
    assert payload["status"] in {"completed", "guarded"}
    for key in (
        "bot_called", "provider_called", "wallet_mutated", "payment_mutated", "customer_reply_sent",
        "external_notification_sent", "job_retried", "asset_delivery_changed", "deployment_changed",
        "self_modifying_code", "dangerous_action_executed",
    ):
        assert payload["data"][key] is False
    return payload


def runtime_request(path: str, *, body: bytes, query: bytes, client_ip: str) -> Request:
    """Build a request carrying values that must never reach reliability DB rows."""

    async def receive() -> dict:
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "https",
            "path": path,
            "raw_path": path.encode("utf-8"),
            "query_string": query,
            "headers": [
                (b"host", b"app.toanaas.vn"),
                (b"authorization", b"Bearer sentinel-auth-token-should-never-persist"),
                (b"cookie", b"session=sentinel-session-cookie-should-never-persist"),
                (b"content-type", b"application/json"),
            ],
            "client": (client_ip, 43123),
            "server": ("app.toanaas.vn", 443),
        },
        receive,
    )


def record_runtime_failure(request: Request, *, status_code: int, occurred_at: datetime | None = None) -> None:
    reliability = importlib.import_module("copyfast_reliability")
    recorded = reliability.record_runtime_failure(request, status_code=status_code, occurred_at=occurred_at)
    if inspect.isawaitable(recorded):
        asyncio.run(recorded)


def rows_as_text(db_path, table: str) -> tuple[list[str], list[tuple]]:
    with sqlite3.connect(db_path) as conn:
        columns = [str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
    return columns, rows


def response_items(response) -> list[dict]:
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert isinstance(data, dict)
    items = data.get("items", [])
    assert isinstance(items, list)
    return items


def test_runtime_5xx_capture_is_allowlisted_and_never_persists_request_sensitive_values(tmp_path, monkeypatch):
    """Dynamic request data must not survive the Web-native reliability boundary."""
    db_path = tmp_path / "reliability-test.db"
    with make_client(tmp_path, monkeypatch):
        dynamic_case_id = str(uuid.uuid4())
        raw_path = f"/api/v1/support/cases/{dynamic_case_id}"
        sentinels = (
            dynamic_case_id,
            "sentinel-query-token-should-never-persist",
            "sentinel-body-secret-should-never-persist",
            "203.0.113.77",
            "sentinel-auth-token-should-never-persist",
            "sentinel-session-cookie-should-never-persist",
        )
        request = runtime_request(
            raw_path,
            query=b"token=sentinel-query-token-should-never-persist&retry=1",
            body=b'{"secret":"sentinel-body-secret-should-never-persist"}',
            client_ip="203.0.113.77",
        )
        # Repeated allowlisted 5xx values become one aggregate bucket.
        for _ in range(6):
            record_runtime_failure(request, status_code=500)
        # Non-5xx and non-Web-native/internal/financial paths are deliberately
        # invisible to this module even if a caller tries to feed them in.
        record_runtime_failure(request, status_code=404)
        record_runtime_failure(
            runtime_request(
                "/internal/v1/operations/tick",
                query=b"nonce=sentinel-query-token-should-never-persist",
                body=b'{"session":"sentinel-session-cookie-should-never-persist"}',
                client_ip="203.0.113.77",
            ),
            status_code=500,
        )
        record_runtime_failure(
            runtime_request(
                "/api/v1/wallet/history",
                query=b"token=sentinel-query-token-should-never-persist",
                body=b'{"secret":"sentinel-body-secret-should-never-persist"}',
                client_ip="203.0.113.77",
            ),
            status_code=500,
        )

    columns, rows = rows_as_text(db_path, "web_ops_runtime_signal_buckets")
    assert len(rows) == 1
    assert {"route_family", "signal_code", "count", "first_seen_at", "last_seen_at"}.issubset(columns)
    row = dict(zip(columns, rows[0], strict=True))
    assert int(row["count"]) == 6
    # The route family is a policy-owned fixed label, not a raw URL.  It
    # cannot preserve the dynamic instance id or a query string.
    assert str(row["route_family"]) == "support_desk"
    assert dynamic_case_id not in str(row["route_family"])
    assert "/" not in str(row["route_family"])
    persisted = "\n".join("" if value is None else str(value) for db_row in rows for value in db_row)
    for sentinel in sentinels:
        assert sentinel not in persisted


def test_scheduler_dedupes_runtime_and_operator_complaint_followups_then_terminal_source_supersedes_metadata_only(tmp_path, monkeypatch):
    """A repeated signal and an operator-needed complaint each create one local follow-up."""
    db_path = tmp_path / "reliability-test.db"
    owner_email = "reliability-manager@example.com"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, owner_email)
        promote_staff(db_path, owner_email)
        created = client.post(
            "/api/v1/support/cases",
            headers={"X-CSRF-Token": csrf},
            json={
                "category": "refund",
                "priority": "urgent",
                "subject": "Cần nhân sự tra xét yêu cầu Web",
                "detail": "Case test dùng để tạo metadata operator an toàn, không tạo thao tác tài chính.",
                "idempotency_key": "reliability-followup-case-0001",
            },
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        case_id = str(created.json()["data"]["case"]["id"])

        for _ in range(6):
            record_runtime_failure(
                runtime_request(
                    f"/api/v1/support/cases/{uuid.uuid4()}",
                    query=b"query=dynamic-value-never-persisted",
                    body=b'{"body":"never-persisted"}',
                    client_ip="198.51.100.18",
                ),
                status_code=500,
            )
        first_tick = run_tick(client, "R" * 24)
        assert int(first_tick["data"].get("runtime_followup_count", 0)) >= 1
        assert int(first_tick["data"].get("complaint_followup_count", 0)) >= 1

        first_items = response_items(client.get("/api/v1/operations/admin/followups?limit=50"))
        runtime_items = [item for item in first_items if item.get("source_kind") == "runtime_signal"]
        complaint_items = [item for item in first_items if item.get("source_kind") == "support_triage"]
        assert len(runtime_items) == 1
        assert len(complaint_items) == 1
        for item in first_items:
            assert item["state"] == "open"
            assert isinstance(item["revision"], int) and item["revision"] >= 1
            # Public admin records identify a safe source class only; raw
            # route/case identifiers, fingerprints and account ownership stay
            # in the private DB model.
            for forbidden in ("source_id", "fingerprint", "account_id", "route_family"):
                assert forbidden not in item

        second_tick = run_tick(client, "S" * 24)
        assert int(second_tick["data"].get("runtime_followup_count", 0)) == 0
        assert int(second_tick["data"].get("complaint_followup_count", 0)) == 0
        assert len([item for item in response_items(client.get("/api/v1/operations/admin/followups?limit=50")) if item.get("source_kind") == "runtime_signal"]) == 1
        assert len([item for item in response_items(client.get("/api/v1/operations/admin/followups?limit=50")) if item.get("source_kind") == "support_triage"]) == 1

        detail = client.get(f"/api/v1/support/cases/{case_id}")
        assert detail.status_code == 200
        close = client.post(
            f"/api/v1/support/cases/{case_id}/close",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": detail.json()["data"]["case"]["revision"], "confirm": True, "idempotency_key": "reliability-terminal-close-0001"},
        )
        assert close.status_code == 200 and close.json()["ok"] is True
        with sqlite3.connect(db_path) as conn:
            source_before = conn.execute("SELECT state, revision FROM web_support_cases WHERE id=?", (case_id,)).fetchone()
            messages_before = conn.execute("SELECT COUNT(*) FROM web_support_messages WHERE case_id=?", (case_id,)).fetchone()[0]

        terminal_tick = run_tick(client, "T" * 24)
        assert terminal_tick["data"].get("complaint_followup_count", 0) == 0
        refreshed = response_items(client.get("/api/v1/operations/admin/followups?limit=50"))
        complaint = next(item for item in refreshed if item.get("source_kind") == "support_triage")
        assert complaint["state"] == "superseded"
        with sqlite3.connect(db_path) as conn:
            source_after = conn.execute("SELECT state, revision FROM web_support_cases WHERE id=?", (case_id,)).fetchone()
            messages_after = conn.execute("SELECT COUNT(*) FROM web_support_messages WHERE case_id=?", (case_id,)).fetchone()[0]
        assert source_before and source_before[0] == "closed"
        assert source_after == source_before
        assert messages_after == messages_before


def test_unverified_ordinary_support_clock_creates_one_medium_followup_not_a_breach_or_source_mutation(tmp_path, monkeypatch):
    """A missing semantic clock needs human review, never a fabricated SLA failure."""

    db_path = tmp_path / "reliability-test.db"
    manager_email = "reliability-unverified-manager@example.com"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, manager_email)
        promote_staff(db_path, manager_email)
        created = client.post(
            "/api/v1/support/cases",
            headers={"X-CSRF-Token": csrf},
            json={
                "category": "general_support",
                "priority": "normal",
                "subject": "Rà soát mốc chờ phản hồi Web",
                "detail": "Fixture nội bộ kiểm tra metadata Reliability không chạm nội dung hay trạng thái case.",
                "idempotency_key": "reliability-unverified-clock-0001",
            },
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        case_id = str(created.json()["data"]["case"]["id"])
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_support_cases SET customer_waiting_since=NULL WHERE id=?", (case_id,))
            conn.commit()
            source_before = conn.execute(
                "SELECT state, revision, customer_waiting_since FROM web_support_cases WHERE id=?", (case_id,)
            ).fetchone()
            messages_before = conn.execute("SELECT COUNT(*) FROM web_support_messages WHERE case_id=?", (case_id,)).fetchone()[0]
            controls_before = conn.execute("SELECT COUNT(*) FROM web_support_case_controls WHERE case_id=?", (case_id,)).fetchone()[0]

        first_tick = run_tick(client, "U" * 24)
        assert int(first_tick["data"].get("complaint_followup_count", 0)) == 1
        with sqlite3.connect(db_path) as conn:
            triage = conn.execute(
                "SELECT risk, disposition, required_role, sla_status, source_revision FROM web_support_triage WHERE case_id=?",
                (case_id,),
            ).fetchone()
            stored = conn.execute(
                """SELECT severity, required_role, state, source_revision
                   FROM web_ops_followups
                   WHERE source_kind='support_triage' AND source_id=?""",
                (case_id,),
            ).fetchone()
            incident_count = conn.execute("SELECT COUNT(*) FROM web_ops_incidents WHERE support_case_id=?", (case_id,)).fetchone()[0]
            source_after = conn.execute(
                "SELECT state, revision, customer_waiting_since FROM web_support_cases WHERE id=?", (case_id,)
            ).fetchone()
            messages_after = conn.execute("SELECT COUNT(*) FROM web_support_messages WHERE case_id=?", (case_id,)).fetchone()[0]
            controls_after = conn.execute("SELECT COUNT(*) FROM web_support_case_controls WHERE case_id=?", (case_id,)).fetchone()[0]
        assert triage is not None
        assert tuple(triage[:4]) == ("web_support", "monitored", "support_operator", "unverified")
        assert stored == ("medium", "operator", "open", int(triage[4]))
        assert incident_count == 0
        assert source_after == source_before
        assert messages_after == messages_before
        assert controls_after == controls_before

        items = response_items(client.get("/api/v1/operations/admin/followups?limit=50"))
        followup = next(item for item in items if item.get("source_kind") == "support_triage")
        assert followup["severity"] == "medium"
        assert followup["required_role"] == "operator"
        for forbidden in ("source_id", "case_id", "account_id", "fingerprint", "sla_status"):
            assert forbidden not in followup
        handoff = client.get(f"/api/v1/operations/admin/followups/{followup['id']}/handoff")
        assert handoff.status_code == 200 and handoff.json()["ok"] is True
        assert handoff.json()["data"]["handoff"]["target_route"] == f"/admin/support/{case_id}"

        # Repeating the tick cannot fan the same unverified case out into a
        # second local row, incident, notification or source mutation.
        second_tick = run_tick(client, "V" * 24)
        assert int(second_tick["data"].get("complaint_followup_count", 0)) == 0
        with sqlite3.connect(db_path) as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM web_ops_followups WHERE source_kind='support_triage' AND source_id=?", (case_id,)
            ).fetchone()[0] == 1
            assert conn.execute("SELECT COUNT(*) FROM web_ops_incidents WHERE support_case_id=?", (case_id,)).fetchone()[0] == 0

        # A genuine customer event creates a new semantic clock. The fresh
        # within-target triage makes the old local reminder stale; it cannot
        # auto-close the case, contact the customer or claim a repair.
        reply = client.post(
            f"/api/v1/support/cases/{case_id}/reply",
            headers={"X-CSRF-Token": csrf},
            json={
                "body": "Khách đã bổ sung thông tin để tạo mốc chờ phản hồi mới.",
                "expected_revision": int(source_before[1]),
                "idempotency_key": "reliability-unverified-customer-reply-0001",
            },
        )
        assert reply.status_code == 200 and reply.json()["ok"] is True
        third_tick = run_tick(client, "W" * 24)
        assert int(third_tick["data"].get("complaint_followup_count", 0)) == 0
        with sqlite3.connect(db_path) as conn:
            fresh_triage = conn.execute(
                "SELECT sla_status FROM web_support_triage WHERE case_id=?", (case_id,)
            ).fetchone()
            source_final = conn.execute("SELECT state FROM web_support_cases WHERE id=?", (case_id,)).fetchone()
        assert fresh_triage == ("within_target",)
        assert source_final is not None and source_final[0] not in {"resolved", "closed"}
        refreshed = next(
            item for item in response_items(client.get("/api/v1/operations/admin/followups?limit=50"))
            if item["id"] == followup["id"]
        )
        assert refreshed["state"] == "superseded"


def test_support_triage_handoff_is_role_scoped_and_only_returns_a_protected_local_route(tmp_path, monkeypatch):
    """A hidden Reliability source can be opened only through a fresh staff handoff."""
    db_path = tmp_path / "reliability-test.db"
    manager_email = "reliability-handoff-manager@example.com"
    operator_email = "reliability-handoff-operator@example.com"
    with make_client(tmp_path, monkeypatch) as client:
        reliability = importlib.import_module("copyfast_reliability")
        assert reliability._can_change(staff_role="manager", required_role="unexpected") is False
        manager_csrf = login(client, manager_email)
        promote_staff(db_path, manager_email)
        created = client.post(
            "/api/v1/support/cases",
            headers={"X-CSRF-Token": manager_csrf},
            json={
                "category": "refund",
                "priority": "urgent",
                "subject": "Yêu cầu manager kiểm tra an toàn",
                "detail": "Dữ liệu fixture nội bộ; không tạo thao tác tiền hoặc liên hệ khách.",
                "idempotency_key": "reliability-handoff-case-0001",
            },
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        case_id = str(created.json()["data"]["case"]["id"])
        run_tick(client, "H" * 24)
        complaint = next(
            item for item in response_items(client.get("/api/v1/operations/admin/followups?limit=50"))
            if item.get("source_kind") == "support_triage"
        )
        assert complaint["required_role"] == "manager"
        for forbidden in ("source_id", "case_id", "account_id", "fingerprint"):
            assert forbidden not in complaint

        with sqlite3.connect(db_path) as conn:
            source_before = conn.execute(
                "SELECT state, revision FROM web_support_cases WHERE id=?", (case_id,)
            ).fetchone()
            messages_before = conn.execute(
                "SELECT COUNT(*) FROM web_support_messages WHERE case_id=?", (case_id,)
            ).fetchone()[0]
        handoff = client.get(f"/api/v1/operations/admin/followups/{complaint['id']}/handoff")
        assert handoff.status_code == 200 and handoff.json()["ok"] is True
        handoff_data = handoff.json()["data"]
        assert handoff_data["execution"] == "web_native_reliability_metadata_only"
        assert handoff_data["bot_called"] is False
        assert handoff_data["provider_called"] is False
        assert handoff_data["customer_reply_sent"] is False
        assert handoff_data["external_notification_sent"] is False
        assert handoff_data["handoff"] == {
            "execution": "protected_support_case_navigation_only",
            "target_route": f"/admin/support/{case_id}",
            "source_content_copied": False,
            "support_case_mutated": False,
        }
        assert "source_id" not in handoff_data["handoff"]
        assert "case_id" not in handoff_data["handoff"]
        with sqlite3.connect(db_path) as conn:
            source_after = conn.execute(
                "SELECT state, revision FROM web_support_cases WHERE id=?", (case_id,)
            ).fetchone()
            messages_after = conn.execute(
                "SELECT COUNT(*) FROM web_support_messages WHERE case_id=?", (case_id,)
            ).fetchone()[0]
            audit = conn.execute(
                "SELECT target, detail FROM web_audit_events WHERE action='web.operations.reliability_followup.handoff_read'"
            ).fetchone()
        assert source_after == source_before
        assert messages_after == messages_before
        assert audit and audit[0] == complaint["id"]
        assert case_id not in str(audit[1])

        login(client, operator_email)
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_accounts SET role_cache='support_operator' WHERE email=?", (operator_email,))
            conn.commit()
        denied = client.get(f"/api/v1/operations/admin/followups/{complaint['id']}/handoff")
        assert denied.status_code == 200 and denied.json()["ok"] is False
        # A manager-only record must be indistinguishable from a missing
        # record to an operator who guesses its opaque UUID.
        assert denied.json()["error_code"] == "OPS_RELIABILITY_FOLLOWUP_NOT_FOUND"
        assert "handoff" not in denied.json()["data"]
        assert "followup" not in denied.json()["data"]


def test_stale_support_triage_followup_is_superseded_then_only_newer_fresh_triage_reopens(tmp_path, monkeypatch):
    """Revision drift must close a handoff until a newer authoritative triage exists."""
    db_path = tmp_path / "reliability-test.db"
    manager_email = "reliability-freshness-manager@example.com"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, manager_email)
        promote_staff(db_path, manager_email)
        created = client.post(
            "/api/v1/support/cases",
            headers={"X-CSRF-Token": csrf},
            json={
                "category": "refund",
                "priority": "urgent",
                "subject": "Kiểm tra freshness triage",
                "detail": "Fixture chỉ kiểm tra revision Web-native.",
                "idempotency_key": "reliability-freshness-case-0001",
            },
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        case_id = str(created.json()["data"]["case"]["id"])
        run_tick(client, "F" * 24)
        initial = next(
            item for item in response_items(client.get("/api/v1/operations/admin/followups?limit=50"))
            if item.get("source_kind") == "support_triage"
        )

        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_support_cases SET revision=revision+1 WHERE id=?", (case_id,))
            current_case_revision = conn.execute(
                "SELECT revision FROM web_support_cases WHERE id=?", (case_id,)
            ).fetchone()[0]
            conn.commit()
        reliability = importlib.import_module("copyfast_reliability")
        stale = reliability.reconcile_followups(
            run_id=str(uuid.uuid4()),
            deadline=datetime.now(timezone.utc) + timedelta(seconds=5),
            action_budget=10,
            secret=INCIDENT_SECRET,
            lease_current=lambda _conn: True,
        )
        assert stale["superseded_count"] == 1
        superseded = next(
            item for item in response_items(client.get("/api/v1/operations/admin/followups?limit=50"))
            if item["id"] == initial["id"]
        )
        assert superseded["state"] == "superseded"
        unavailable = client.get(f"/api/v1/operations/admin/followups/{initial['id']}/handoff")
        assert unavailable.status_code == 200 and unavailable.json()["ok"] is False
        assert unavailable.json()["error_code"] == "OPS_RELIABILITY_HANDOFF_UNAVAILABLE"

        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE web_support_triage SET source_revision=? WHERE case_id=?",
                (current_case_revision, case_id),
            )
            conn.commit()
        fresh = reliability.reconcile_followups(
            run_id=str(uuid.uuid4()),
            deadline=datetime.now(timezone.utc) + timedelta(seconds=5),
            action_budget=10,
            secret=INCIDENT_SECRET,
            lease_current=lambda _conn: True,
        )
        assert fresh["complaint_followup_count"] == 1
        reopened = next(
            item for item in response_items(client.get("/api/v1/operations/admin/followups?limit=50"))
            if item["id"] == initial["id"]
        )
        assert reopened["state"] == "open"
        assert reopened["source_revision"] == current_case_revision
        assert reopened["revision"] > superseded["revision"]
        refreshed_handoff = client.get(f"/api/v1/operations/admin/followups/{initial['id']}/handoff")
        assert refreshed_handoff.status_code == 200 and refreshed_handoff.json()["ok"] is True
        assert refreshed_handoff.json()["data"]["handoff"]["target_route"] == f"/admin/support/{case_id}"


def test_resolved_runtime_followup_reopens_when_a_later_bucket_has_new_occurrences(tmp_path, monkeypatch):
    """A five-minute bucket rollover must not hide a renewed Web failure."""
    db_path = tmp_path / "reliability-test.db"
    manager_email = "reliability-reopen@example.com"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, manager_email)
        promote_staff(db_path, manager_email)
        current = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        first_moment = current.replace(minute=(current.minute // 5) * 5)
        later_moment = first_moment + timedelta(minutes=5)

        request = runtime_request(
            "/api/v1/support/cases/" + str(uuid.uuid4()), query=b"x=no-store", body=b"{}", client_ip="203.0.113.19",
        )
        for _ in range(3):
            record_runtime_failure(request, status_code=500, occurred_at=first_moment)
        run_tick(client, "V" * 24)
        first = next(item for item in response_items(client.get("/api/v1/operations/admin/followups?limit=50")) if item["source_kind"] == "runtime_signal")
        resolved = client.post(
            f"/api/v1/operations/admin/followups/{first['id']}/resolve",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": first["revision"], "confirm": True, "idempotency_key": "reliability-resolve-bucket-0001"},
        )
        assert resolved.status_code == 200 and resolved.json()["ok"] is True

        for _ in range(3):
            record_runtime_failure(request, status_code=500, occurred_at=later_moment)
        run_tick(client, "W" * 24)
        reopened = next(item for item in response_items(client.get("/api/v1/operations/admin/followups?limit=50")) if item["id"] == first["id"])
        assert reopened["state"] == "open"
        assert reopened["source_revision"] > first["source_revision"]
        assert reopened["occurrence_count"] == reopened["source_revision"]
    with sqlite3.connect(db_path) as conn:
        totals = conn.execute(
            "SELECT occurrence_count, revision FROM web_ops_runtime_signal_totals WHERE route_family='support_desk'"
        ).fetchone()
    assert totals == (6, 6)


def test_reliability_followup_queue_pages_101_records_with_staff_guard_and_no_duplicates(tmp_path, monkeypatch):
    """The staff-only queue must not truncate, share cursors or accept invalid offsets."""

    db_path = tmp_path / "reliability-test.db"
    manager_email = "reliability-pagination-manager@example.com"
    customer_email = "reliability-pagination-customer@example.com"
    with make_client(tmp_path, monkeypatch) as client:
        login(client, manager_email)
        # Status initialization creates the additive Operations tables before
        # deterministic local-only fixture rows are inserted.
        assert client.get("/api/v1/operations/status").status_code == 200
        followup_ids = set(
            seed_reliability_followups(
                db_path,
                account_id=account_id_for_email(db_path, manager_email),
                count=101,
            )
        )

        login(client, customer_email)
        assert client.get("/api/v1/operations/admin/followups?state=all&severity=all&limit=50&offset=0").status_code == 403

        promote_staff(db_path, manager_email)
        sign_in(client, manager_email)
        assert_reliability_pages(client, followup_ids)
        for invalid_offset in (-1, 10_001):
            assert client.get(
                f"/api/v1/operations/admin/followups?state=all&severity=all&limit=50&offset={invalid_offset}"
            ).status_code == 422


def test_reliability_followup_role_scope_hides_manager_rows_before_summary_count_pagination_and_direct_mutation(tmp_path, monkeypatch):
    """Manager sees all follow-ups; operator gets only the operator queue.

    Role filtering must happen in the database predicate before a summary
    count or pagination window is produced.  Otherwise an operator could
    infer manager work from a count, an empty final page, or a guessed UUID.
    The fixture intentionally attaches both role classes to the manager's
    account: Reliability permissions are based on the persisted required role,
    not an account-id correlation shortcut.
    """

    db_path = tmp_path / "reliability-test.db"
    manager_email = "reliability-role-manager@example.com"
    operator_email = "reliability-role-operator@example.com"
    with make_client(tmp_path, monkeypatch) as client:
        login(client, manager_email)
        login(client, operator_email)
        # Status initialization creates the additive Operations tables before
        # deterministic local-only metadata is inserted.
        assert client.get("/api/v1/operations/status").status_code == 200
        manager_id = account_id_for_email(db_path, manager_email)
        operator_ids = set(
            seed_reliability_followups(
                db_path,
                account_id=manager_id,
                count=3,
                required_role="operator",
                fixture_scope="reliability-role-operator",
            )
        )
        manager_ids = set(
            seed_reliability_followups(
                db_path,
                account_id=manager_id,
                count=4,
                required_role="manager",
                fixture_scope="reliability-role-manager",
            )
        )
        promote_staff(db_path, manager_email)
        promote_staff(db_path, operator_email, role="support_operator")

        sign_in(client, manager_email)
        manager_summary = client.get("/api/v1/operations/admin/reliability/summary")
        manager_pages = [
            client.get(
                "/api/v1/operations/admin/followups",
                params={"state": "all", "severity": "all", "limit": 3, "offset": offset},
            )
            for offset in (0, 3, 6)
        ]

        operator_csrf = sign_in(client, operator_email)
        operator_summary = client.get("/api/v1/operations/admin/reliability/summary")
        operator_pages = [
            client.get(
                "/api/v1/operations/admin/followups",
                params={"state": "all", "severity": "all", "limit": 2, "offset": offset},
            )
            for offset in (0, 2)
        ]
        hidden_mutation = client.post(
            f"/api/v1/operations/admin/followups/{next(iter(manager_ids))}/acknowledge",
            headers={"X-CSRF-Token": operator_csrf},
            json={
                "expected_revision": 1,
                "confirm": True,
                "idempotency_key": "reliability-hidden-manager-row-0001",
            },
        )

    assert manager_summary.status_code == 200 and manager_summary.json()["ok"] is True
    manager_data = manager_summary.json()["data"]
    assert manager_data["operator_role"] == "manager"
    assert manager_data["counts"] == {
        "open": 7,
        "acknowledged": 0,
        "resolved": 0,
        "superseded": 0,
    }
    manager_page_ids: set[str] = set()
    for response, expected_count, has_more, next_offset in zip(
        manager_pages,
        (3, 3, 1),
        (True, True, False),
        (3, 6, None),
        strict=True,
    ):
        assert response.status_code == 200 and response.json()["ok"] is True
        data = response.json()["data"]
        assert len(data["items"]) == expected_count
        assert data["has_more"] is has_more
        assert data["next_offset"] == next_offset
        manager_page_ids.update(str(item["id"]) for item in data["items"])
    assert manager_page_ids == operator_ids | manager_ids

    assert operator_summary.status_code == 200 and operator_summary.json()["ok"] is True
    operator_data = operator_summary.json()["data"]
    assert operator_data["operator_role"] == "operator"
    assert operator_data["counts"] == {
        "open": 3,
        "acknowledged": 0,
        "resolved": 0,
        "superseded": 0,
    }
    operator_page_ids: set[str] = set()
    for response, expected_count, has_more, next_offset in zip(
        operator_pages,
        (2, 1),
        (True, False),
        (2, None),
        strict=True,
    ):
        assert response.status_code == 200 and response.json()["ok"] is True
        data = response.json()["data"]
        assert len(data["items"]) == expected_count
        assert data["has_more"] is has_more
        assert data["next_offset"] == next_offset
        operator_page_ids.update(str(item["id"]) for item in data["items"])
        assert {str(item["required_role"]) for item in data["items"]} <= {"operator"}
    assert operator_page_ids == operator_ids
    assert operator_page_ids.isdisjoint(manager_ids)

    # A guessed manager-only UUID is indistinguishable from a missing record:
    # no row body/revision/role is returned that could become a lookup oracle.
    assert hidden_mutation.status_code == 200
    hidden_data = hidden_mutation.json()["data"]
    assert hidden_mutation.json()["ok"] is False
    assert hidden_mutation.json()["error_code"] == "OPS_RELIABILITY_FOLLOWUP_NOT_FOUND"
    assert "followup" not in hidden_data
    assert "handoff" not in hidden_data
    rendered_hidden = str(hidden_mutation.json())
    for forbidden in (*manager_ids, "manager", "reliability-role-manager"):
        assert forbidden not in rendered_hidden


def test_reliability_followup_filters_intersect_fixed_metadata_only(tmp_path, monkeypatch):
    """The staff queue accepts only state/severity and preserves filtered paging."""

    db_path = tmp_path / "reliability-test.db"
    manager_email = "reliability-filter-manager@example.com"
    with make_client(tmp_path, monkeypatch) as client:
        login(client, manager_email)
        assert client.get("/api/v1/operations/status").status_code == 200
        manager_id = account_id_for_email(db_path, manager_email)
        followup_ids = seed_reliability_followups(db_path, account_id=manager_id, count=4)
        with sqlite3.connect(db_path) as conn:
            conn.executemany(
                "UPDATE web_ops_followups SET state=?, severity=? WHERE id=?",
                [
                    ("acknowledged", "high", followup_ids[0]),
                    ("acknowledged", "high", followup_ids[1]),
                    ("open", "critical", followup_ids[2]),
                    ("resolved", "low", followup_ids[3]),
                ],
            )
            conn.commit()
        promote_staff(db_path, manager_email)
        sign_in(client, manager_email)

        first_page = client.get(
            "/api/v1/operations/admin/followups",
            params={"state": "acknowledged", "severity": "high", "limit": 1, "offset": 0},
        )
        assert first_page.status_code == 200
        first_data = first_page.json()["data"]
        assert first_data["has_more"] is True
        assert first_data["next_offset"] == 1
        assert len(first_data["items"]) == 1
        assert first_data["items"][0]["state"] == "acknowledged"
        assert first_data["items"][0]["severity"] == "high"

        second_page = client.get(
            "/api/v1/operations/admin/followups",
            params={"state": "acknowledged", "severity": "high", "limit": 1, "offset": 1},
        )
        assert second_page.status_code == 200
        second_data = second_page.json()["data"]
        assert second_data["has_more"] is False
        assert second_data["next_offset"] is None
        assert len(second_data["items"]) == 1
        assert second_data["items"][0]["state"] == "acknowledged"
        assert second_data["items"][0]["severity"] == "high"
        assert {item["id"] for item in first_data["items"] + second_data["items"]} == set(followup_ids[:2])
        for item in first_data["items"] + second_data["items"]:
            assert {"source_id", "account_id", "fingerprint", "created_by_run_id"}.isdisjoint(item)

        for params in (
            {"state": "unknown"},
            {"severity": "urgent"},
            {"state": "open", "severity": "anything"},
        ):
            assert client.get("/api/v1/operations/admin/followups", params=params).status_code == 422


def test_reliability_admin_api_requires_staff_csrf_confirmation_revision_and_idempotency(tmp_path, monkeypatch):
    """The follow-up lifecycle is a human staff record, never a browser-side shortcut."""
    db_path = tmp_path / "reliability-test.db"
    manager_email = "reliability-lifecycle@example.com"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.get("/api/v1/operations/admin/reliability/summary").status_code == 401
        customer_csrf = login(client, "reliability-customer@example.com")
        assert customer_csrf
        assert client.get("/api/v1/operations/admin/reliability/summary").status_code == 403
        assert client.get("/api/v1/operations/admin/followups").status_code == 403

        manager_csrf = login(client, manager_email)
        promote_staff(db_path, manager_email)
        for _ in range(6):
            record_runtime_failure(
                runtime_request(
                    f"/api/v1/support/cases/{uuid.uuid4()}", query=b"x=sensitive", body=b'{"x":"sensitive"}', client_ip="203.0.113.88",
                ),
                status_code=500,
            )
        run_tick(client, "U" * 24)

        summary_response = client.get("/api/v1/operations/admin/reliability/summary")
        assert summary_response.status_code == 200 and summary_response.json()["ok"] is True
        summary_data = summary_response.json()["data"]
        counts = summary_data.get("counts", {})
        assert isinstance(counts, dict)
        for state in ("open", "acknowledged", "resolved", "superseded"):
            assert isinstance(counts.get(state), int)
        assert isinstance(summary_data.get("signal_groups"), int)
        for key in (
            "bot_called", "provider_called", "wallet_mutated", "payment_mutated", "customer_reply_sent",
            "external_notification_sent", "deployment_changed", "self_modifying_code", "dangerous_action_executed",
        ):
            assert summary_data[key] is False

        items = response_items(client.get("/api/v1/operations/admin/followups?state=open&limit=50"))
        assert items
        followup = next(item for item in items if item.get("source_kind") == "runtime_signal")
        followup_id = str(followup["id"])
        revision = int(followup["revision"])

        no_csrf = client.post(
            f"/api/v1/operations/admin/followups/{followup_id}/acknowledge",
            json={"expected_revision": revision, "confirm": True, "idempotency_key": "reliability-no-csrf-0001"},
        )
        assert no_csrf.status_code == 403
        missing_confirmation = client.post(
            f"/api/v1/operations/admin/followups/{followup_id}/acknowledge",
            headers={"X-CSRF-Token": manager_csrf},
            json={"expected_revision": revision, "idempotency_key": "reliability-no-confirm-0001"},
        )
        assert missing_confirmation.status_code == 422
        missing_key = client.post(
            f"/api/v1/operations/admin/followups/{followup_id}/acknowledge",
            headers={"X-CSRF-Token": manager_csrf},
            json={"expected_revision": revision, "confirm": True},
        )
        assert missing_key.status_code == 422
        conflict = client.post(
            f"/api/v1/operations/admin/followups/{followup_id}/acknowledge",
            headers={"X-CSRF-Token": manager_csrf},
            json={"expected_revision": revision + 9, "confirm": True, "idempotency_key": "reliability-conflict-0001"},
        )
        assert conflict.status_code in {200, 409, 422}
        assert conflict.json().get("ok") is not True

        acknowledge_payload = {"expected_revision": revision, "confirm": True, "idempotency_key": "reliability-acknowledge-0001"}
        acknowledged = client.post(
            f"/api/v1/operations/admin/followups/{followup_id}/acknowledge",
            headers={"X-CSRF-Token": manager_csrf}, json=acknowledge_payload,
        )
        assert acknowledged.status_code == 200 and acknowledged.json()["ok"] is True
        acknowledged_item = acknowledged.json()["data"]["followup"]
        assert acknowledged_item["state"] == "acknowledged"
        assert int(acknowledged_item["revision"]) == revision + 1
        replay = client.post(
            f"/api/v1/operations/admin/followups/{followup_id}/acknowledge",
            headers={"X-CSRF-Token": manager_csrf}, json=acknowledge_payload,
        )
        assert replay.status_code == 200 and replay.json()["ok"] is True
        assert replay.json()["data"]["followup"] == acknowledged_item

        resolved = client.post(
            f"/api/v1/operations/admin/followups/{followup_id}/resolve",
            headers={"X-CSRF-Token": manager_csrf},
            json={"expected_revision": revision + 1, "confirm": True, "idempotency_key": "reliability-resolve-0001"},
        )
        assert resolved.status_code == 200 and resolved.json()["ok"] is True
        assert resolved.json()["data"]["followup"]["state"] == "resolved"
        reopened = client.post(
            f"/api/v1/operations/admin/followups/{followup_id}/reopen",
            headers={"X-CSRF-Token": manager_csrf},
            json={"expected_revision": revision + 2, "confirm": True, "idempotency_key": "reliability-reopen-0001"},
        )
        assert reopened.status_code == 200 and reopened.json()["ok"] is True
        assert reopened.json()["data"]["followup"]["state"] == "open"

    with sqlite3.connect(db_path) as conn:
        events = conn.execute(
            "SELECT action, state, revision FROM web_ops_followup_events WHERE followup_id=? ORDER BY revision",
            (followup_id,),
        ).fetchall()
    assert [(row[0], row[1], row[2]) for row in events] == [
        ("opened", "open", 1),
        ("acknowledge", "acknowledged", 2),
        ("resolve", "resolved", 3),
        ("reopen", "open", 4),
    ]
