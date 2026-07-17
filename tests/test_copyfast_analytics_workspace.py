"""High-risk contracts for the private, Web-native Analytics Workspace.

The suite deliberately exercises only durable security and accounting-adjacent
behaviour: signed ownership, CSRF/idempotency, bounded input, deterministic
manual calculations and lifecycle locks.  It never calls a Bot, provider,
social platform, wallet, PayOS, job, publishing or import surface.  The one
CSV check below covers a bounded, signed Web-only attachment rather than an
external export, canonical Campaign report or stored delivery artifact.
"""

from __future__ import annotations

import importlib
import csv
import io
import sqlite3
import sys
from contextlib import contextmanager

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry", "copyfast_api",
    "copyfast_pages", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations", "copyfast_image_studio",
    "copyfast_document_workspace", "copyfast_chat_workspace", "copyfast_analytics_workspace", "copyfast_memory",
    "copyfast_prompt_library", "copyfast_music_media", "copyfast_content_studio", "copyfast_voice_studio",
    "copyfast_video_studio", "copyfast_subtitle_workspace", "copyfast_support",
]


def make_client(tmp_path, monkeypatch, *, enabled: bool = True, export_enabled: bool = False) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "analytics-workspace-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "analytics-workspace-test-session-secret")
    monkeypatch.setenv("WEBAPP_ANALYTICS_WORKSPACE_ENABLED", "true" if enabled else "false")
    monkeypatch.setenv("WEBAPP_ANALYTICS_WORKSPACE_EXPORT_ENABLED", "true" if export_enabled else "false")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Analytics Owner"},
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def report_payload(key: str, **overrides) -> dict:
    value = {
        "title": "Báo cáo chỉ số tăng trưởng tháng bảy",
        "objective": "Ghi nhận các quan sát thủ công để đội ngũ rà soát giả định và quyết định nội bộ.",
        "context_label": "Nội bộ Web-owned",
        "period_start": "2026-07-01",
        "period_end": "2026-07-31",
        "tags": ["growth", "july"],
        "summary_note": "Không kết nối nền tảng, Bot, provider hay số liệu doanh thu canonical.",
        "idempotency_key": key,
    }
    value.update(overrides)
    return value


def create_report(client: TestClient, csrf: str, key: str = "analytics-report-create-0001", **overrides) -> dict:
    response = client.post(
        "/api/v1/analytics-workspace/reports",
        headers={"X-CSRF-Token": csrf},
        json=report_payload(key, **overrides),
    )
    assert response.status_code == 200 and response.json()["ok"] is True
    return response.json()["data"]["report"]


def metric_payload(key: str, report_revision: int, **overrides) -> dict:
    value = {
        "name": "Lượt xem đủ điều kiện",
        "unit": "count",
        "direction": "up",
        "description": "Metric do account tự định nghĩa, không đồng bộ nền tảng.",
        "expected_report_revision": report_revision,
        "idempotency_key": key,
    }
    value.update(overrides)
    return value


def create_metric(client: TestClient, csrf: str, report: dict, key: str = "analytics-metric-create-0001", **overrides) -> tuple[dict, dict]:
    response = client.post(
        f"/api/v1/analytics-workspace/reports/{report['id']}/metrics",
        headers={"X-CSRF-Token": csrf},
        json=metric_payload(key, report["revision"], **overrides),
    )
    assert response.status_code == 200 and response.json()["ok"] is True
    data = response.json()["data"]
    return data["report"], data["metric"]


def transition_report(client: TestClient, csrf: str, report: dict, state: str, key: str) -> dict:
    response = client.post(
        f"/api/v1/analytics-workspace/reports/{report['id']}/lifecycle",
        headers={"X-CSRF-Token": csrf},
        json={"state": state, "expected_revision": report["revision"], "idempotency_key": key},
    )
    assert response.status_code == 200 and response.json()["ok"] is True
    return response.json()["data"]["report"]


def finalize_report(client: TestClient, csrf: str, report: dict, *, prefix: str) -> dict:
    reviewed = transition_report(client, csrf, report, "review", f"{prefix}-review-0001")
    return transition_report(client, csrf, reviewed, "finalized", f"{prefix}-finalized-0001")


def snapshot_payload(key: str, report_revision: int, **overrides) -> dict:
    value = {
        "observed_on": "2026-07-01",
        "value": "10.00",
        "source_label": "Nhập tay trong cuộc họp",
        "note": "Quan sát nội bộ chưa được nền tảng xác minh.",
        "expected_report_revision": report_revision,
        "idempotency_key": key,
    }
    value.update(overrides)
    return value


def assert_manual_only(data: dict) -> None:
    assert data["execution"] == "manual_measurement_only"
    assert data["data_origin"] == "user_supplied_only"
    for key in (
        "bot_called", "provider_called", "social_api_called", "platform_data_connected", "platform_data_verified",
        "ai_recommendation_created", "canonical_revenue", "wallet_mutated", "payment_started", "payment_processed",
        "job_created", "publish_action_created", "browser_file_upload", "external_url_import", "report_file_created",
    ):
        assert data[key] is False
    assert data["local_calculation"] is True
    assert data["output_delivery"] == "not_applicable"


def test_analytics_workspace_requires_signed_session_csrf_bounded_body_and_redacted_idempotency(tmp_path, monkeypatch):
    db_path = tmp_path / "analytics-workspace-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.get("/api/v1/analytics-workspace/summary").status_code == 401
        csrf = login(client, "analytics-auth@example.com")
        raw = report_payload("analytics-report-idempotency-0001")
        assert client.post("/api/v1/analytics-workspace/reports", json=raw).status_code == 403
        too_large = client.post(
            "/api/v1/analytics-workspace/reports",
            headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
            content=b'{"title":"' + (b"x" * (129 * 1024)) + b'"}',
        )
        assert too_large.status_code == 413
        assert too_large.json()["error_code"] == "WEB_ANALYTICS_WORKSPACE_BODY_TOO_LARGE"
        assert too_large.headers["Cache-Control"] == "no-store, private"
        assert_manual_only(too_large.json()["data"])
        created = client.post("/api/v1/analytics-workspace/reports", headers={"X-CSRF-Token": csrf}, json=raw)
        assert created.status_code == 200 and created.json()["ok"] is True
        assert_manual_only(created.json()["data"])
        report = created.json()["data"]["report"]
        replay = client.post("/api/v1/analytics-workspace/reports", headers={"X-CSRF-Token": csrf}, json=raw)
        assert replay.status_code == 200 and replay.json()["ok"] is True
        assert replay.json()["data"]["report"]["id"] == report["id"]
        assert replay.json()["data"]["report"]["revision"] == report["revision"]
        collision = client.post(
            "/api/v1/analytics-workspace/reports",
            headers={"X-CSRF-Token": csrf},
            json=report_payload("analytics-report-idempotency-0001", title="Một báo cáo khác hẳn"),
        )
        assert collision.status_code == 409
    with sqlite3.connect(db_path) as conn:
        receipts = conn.execute(
            "SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-analytics-workspace:%'"
        ).fetchall()
    assert receipts
    for row in receipts:
        stored = str(row[0])
        assert raw["title"] not in stored
        assert raw["objective"] not in stored
        assert raw["summary_note"] not in stored


def test_analytics_workspace_is_owner_scoped_and_lifecycle_prevents_writes(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        first_csrf = login(client, "analytics-owner@example.com")
        report = create_report(client, first_csrf, "analytics-owner-report-0001")
        reviewed = client.post(
            f"/api/v1/analytics-workspace/reports/{report['id']}/lifecycle",
            headers={"X-CSRF-Token": first_csrf},
            json={"state": "review", "expected_revision": report["revision"], "idempotency_key": "analytics-review-0001"},
        )
        assert reviewed.status_code == 200 and reviewed.json()["ok"] is True
        reviewed_report = reviewed.json()["data"]["report"]
        assert reviewed_report["state"] == "review"
        blocked = client.post(
            f"/api/v1/analytics-workspace/reports/{report['id']}/metrics",
            headers={"X-CSRF-Token": first_csrf},
            json=metric_payload("analytics-locked-metric-0001", reviewed_report["revision"]),
        )
        assert blocked.status_code == 200
        assert blocked.json()["error_code"] == "WEB_ANALYTICS_REVIEW_LOCKED"
        assert_manual_only(blocked.json()["data"])
        second_csrf = login(client, "analytics-other@example.com")
        hidden = client.get(f"/api/v1/analytics-workspace/reports/{report['id']}")
        assert hidden.status_code == 200
        assert hidden.json()["error_code"] == "WEB_ANALYTICS_REPORT_NOT_FOUND"
        denied = client.post(
            f"/api/v1/analytics-workspace/reports/{report['id']}/lifecycle",
            headers={"X-CSRF-Token": second_csrf},
            json={"state": "draft", "expected_revision": reviewed_report["revision"], "idempotency_key": "analytics-cross-owner-0001"},
        )
        assert denied.status_code == 200
        assert denied.json()["error_code"] == "WEB_ANALYTICS_REPORT_NOT_FOUND"


def test_analytics_manual_csv_export_is_fail_closed_until_separately_enabled(tmp_path, monkeypatch):
    """The attachment feature has its own default-off switch, after session + CSRF."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "analytics-csv-flag@example.com")
        guarded = client.post(
            "/api/v1/analytics-workspace/reports/00000000-0000-4000-8000-000000000001/export.csv",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 1},
        )
        assert guarded.status_code == 503
        assert "WEBAPP_ANALYTICS_WORKSPACE_EXPORT_ENABLED" in guarded.text
        assert "Content-Disposition" not in guarded.headers


def test_analytics_manual_csv_export_requires_finalized_owner_current_revision_and_csrf(tmp_path, monkeypatch):
    """Only one signed owner can receive a complete, formula-safe CSV attachment."""
    db_path = tmp_path / "analytics-workspace-test.db"
    with make_client(tmp_path, monkeypatch, export_enabled=True) as client:
        csrf = login(client, "analytics-csv-owner@example.com")
        report_title = "Báo cáo chỉ số tăng trưởng tháng bảy"
        report = create_report(
            client,
            csrf,
            "analytics-csv-report-create-0001",
            summary_note="-Ghi chú nội bộ bắt đầu bằng dấu trừ phải không thành công thức bảng tính.",
        )
        report, metric = create_metric(client, csrf, report, "analytics-csv-metric-create-0001")
        snapshot = client.post(
            f"/api/v1/analytics-workspace/reports/{report['id']}/metrics/{metric['id']}/snapshots",
            headers={"X-CSRF-Token": csrf},
            json=snapshot_payload(
                "analytics-csv-snapshot-create-0001",
                report["revision"],
                note="=SUM(1,1)",
            ),
        )
        assert snapshot.status_code == 200 and snapshot.json()["ok"] is True
        finding = client.post(
            f"/api/v1/analytics-workspace/reports/{report['id']}/findings",
            headers={"X-CSRF-Token": csrf},
            json={
                "kind": "finding", "body": "@SUM(1,1)",
                "expected_report_revision": report["revision"], "idempotency_key": "analytics-csv-finding-create-0001",
            },
        )
        assert finding.status_code == 200 and finding.json()["ok"] is True
        endpoint = f"/api/v1/analytics-workspace/reports/{report['id']}/export.csv"

        missing_csrf = client.post(endpoint, json={"expected_revision": report["revision"]})
        assert missing_csrf.status_code == 403
        before_finalized = client.post(endpoint, headers={"X-CSRF-Token": csrf}, json={"expected_revision": report["revision"]})
        assert before_finalized.status_code == 409
        assert before_finalized.json()["error_code"] == "WEB_ANALYTICS_MANUAL_CSV_FINALIZED_REQUIRED"
        assert before_finalized.headers["Cache-Control"] == "no-store, private"

        finalized = finalize_report(client, csrf, report, prefix="analytics-csv-report")
        assert finalized["state"] == "finalized"
        stale = client.post(
            endpoint,
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": finalized["revision"] - 1},
        )
        assert stale.status_code == 409
        assert stale.json()["error_code"] == "WEB_ANALYTICS_REVISION_CONFLICT"

        exported = client.post(
            endpoint,
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": finalized["revision"]},
        )
        assert exported.status_code == 200
        assert exported.headers["Content-Type"].startswith("text/csv")
        assert exported.headers["Content-Disposition"] == 'attachment; filename="toan-aas-manual-analytics.csv"'
        assert exported.headers["Content-Length"] == str(len(exported.content))
        assert exported.headers["Cache-Control"] == "no-store, private"
        assert exported.headers["X-Content-Type-Options"] == "nosniff"
        assert exported.headers["Referrer-Policy"] == "no-referrer"
        assert exported.headers["Content-Security-Policy"] == "sandbox"
        assert exported.headers["Cross-Origin-Resource-Policy"] == "same-origin"
        assert exported.content.startswith(b"\xef\xbb\xbf")
        csv_text = exported.content.decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(csv_text, newline="")))
        assert {row["record_type"] for row in rows} == {"report", "metric", "snapshot", "finding"}
        assert any(row["summary_note"] == "'-Ghi chú nội bộ bắt đầu bằng dấu trừ phải không thành công thức bảng tính." for row in rows)
        assert any(row["snapshot_note"] == "'=SUM(1,1)" for row in rows)
        assert any(row["finding_body"] == "'@SUM(1,1)" for row in rows)
        assert report["id"] not in csv_text
        assert "analytics-csv-owner@example.com" not in csv_text

        second_csrf = login(client, "analytics-csv-other@example.com")
        foreign = client.post(
            endpoint,
            headers={"X-CSRF-Token": second_csrf},
            json={"expected_revision": finalized["revision"]},
        )
        assert foreign.status_code == 404
        assert foreign.json()["error_code"] == "WEB_ANALYTICS_REPORT_NOT_FOUND"
        assert report_title not in foreign.text

    with sqlite3.connect(db_path) as conn:
        audit = conn.execute(
            "SELECT target, detail FROM web_audit_events WHERE action='analytics_report_manual_csv_exported'"
        ).fetchone()
    assert audit is not None
    assert audit[0] == report["id"]
    assert f"revision={finalized['revision']}" in audit[1]
    assert report_title not in audit[1]
    assert "=SUM(1,1)" not in audit[1]


def test_analytics_manual_csv_export_refuses_oversized_complete_attachment_without_partial_file(tmp_path, monkeypatch):
    """A hard cap must fail atomically: no attachment and no export audit record."""
    db_path = tmp_path / "analytics-workspace-test.db"
    with make_client(tmp_path, monkeypatch, export_enabled=True) as client:
        csrf = login(client, "analytics-csv-limit@example.com")
        report = create_report(client, csrf, "analytics-csv-limit-report-create-0001")
        finalized = finalize_report(client, csrf, report, prefix="analytics-csv-limit-report")
        workspace = importlib.import_module("copyfast_analytics_workspace")
        monkeypatch.setattr(workspace, "MAX_MANUAL_CSV_EXPORT_BYTES", 1)
        refused = client.post(
            f"/api/v1/analytics-workspace/reports/{report['id']}/export.csv",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": finalized["revision"]},
        )
        assert refused.status_code == 413
        assert refused.json()["ok"] is False
        assert refused.json()["error_code"] == "WEB_ANALYTICS_MANUAL_CSV_EXPORT_LIMIT"
        assert refused.headers["Cache-Control"] == "no-store, private"
        assert "Content-Disposition" not in refused.headers
        assert b"toan-aas-manual-analytics.csv" not in refused.content

    with sqlite3.connect(db_path) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM web_audit_events WHERE action='analytics_report_manual_csv_exported'"
        ).fetchone()[0]
    assert count == 0


def test_analytics_manual_csv_export_fails_closed_when_audit_recheck_is_write_locked(tmp_path, monkeypatch):
    """A concurrent SQLite writer must not delay or release an unaudited CSV."""
    with make_client(tmp_path, monkeypatch, export_enabled=True) as client:
        csrf = login(client, "analytics-csv-lock@example.com")
        report = create_report(client, csrf, "analytics-csv-lock-report-create-0001")
        finalized = finalize_report(client, csrf, report, prefix="analytics-csv-lock-report")
        workspace = importlib.import_module("copyfast_analytics_workspace")

        @contextmanager
        def locked_audit_transaction(*, timeout_seconds):
            assert timeout_seconds <= 0.25
            raise sqlite3.OperationalError("database is locked")
            yield None  # pragma: no cover - required to make this a generator context manager

        monkeypatch.setattr(workspace, "best_effort_transaction", locked_audit_transaction)
        refused = client.post(
            f"/api/v1/analytics-workspace/reports/{report['id']}/export.csv",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": finalized["revision"]},
        )
        assert refused.status_code == 503
        assert refused.json()["error_code"] == "WEB_ANALYTICS_MANUAL_CSV_RETRY_LATER"
        assert "Content-Disposition" not in refused.headers
        assert refused.headers["Cache-Control"] == "no-store, private"
        assert refused.headers["Referrer-Policy"] == "no-referrer"
        assert refused.headers["Content-Security-Policy"] == "sandbox"
        assert refused.headers["Cross-Origin-Resource-Policy"] == "same-origin"


def test_analytics_report_library_paginates_owner_scoped_metadata_only(tmp_path, monkeypatch):
    """The report library must page deterministically without widening its boundary."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "analytics-pagination@example.com")
        created = [
            create_report(client, csrf, f"analytics-pagination-report-{index:04d}", title=f"Báo cáo phân trang {index}")
            for index in range(1, 4)
        ]
        owned_ids = {item["id"] for item in created}

        first = client.get("/api/v1/analytics-workspace/reports", params={"state": "all", "limit": 1, "offset": 0})
        second = client.get("/api/v1/analytics-workspace/reports", params={"state": "all", "limit": 1, "offset": 1})
        last = client.get("/api/v1/analytics-workspace/reports", params={"state": "all", "limit": 1, "offset": 10_000})
        for response in (first, second, last):
            assert response.status_code == 200 and response.json()["ok"] is True
            assert_manual_only(response.json()["data"])

        first_data = first.json()["data"]
        second_data = second.json()["data"]
        last_data = last.json()["data"]
        assert first_data["filter"] == {"state": "all", "q": ""}
        assert first_data["pagination"] == {
            "total": 3, "limit": 1, "offset": 0, "returned": 1,
            "has_more": True, "next_offset": 1, "previous_offset": None,
        }
        assert second_data["pagination"]["offset"] == 1
        assert second_data["pagination"]["previous_offset"] == 0
        assert second_data["pagination"]["has_more"] is True
        assert last_data["pagination"]["offset"] == 2
        assert last_data["pagination"]["has_more"] is False
        assert last_data["pagination"]["next_offset"] is None
        listed_ids = {
            first_data["items"][0]["id"],
            second_data["items"][0]["id"],
            last_data["items"][0]["id"],
        }
        assert listed_ids == owned_ids


def test_analytics_workspace_rejects_sensitive_transport_values_and_invalid_decimal(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "analytics-validation@example.com")
        unsafe_values = (
            "https://example.invalid/private?token=abc",
            "file:///C:/private/source.txt",
            "<img src=x onerror=alert(1)>",
            "api_key=not-a-real-secret-value",
            "Mã giao dịch: 123456789",
        )
        for index, unsafe in enumerate(unsafe_values, start=1):
            response = client.post(
                "/api/v1/analytics-workspace/reports",
                headers={"X-CSRF-Token": csrf},
                json=report_payload(f"analytics-unsafe-report-{index:04d}", objective=unsafe),
            )
            assert response.status_code == 422
            assert_manual_only(response.json()["data"])
        report = create_report(client, csrf, "analytics-validation-report-0001")
        report, metric = create_metric(client, csrf, report, "analytics-validation-metric-0001")
        for index, unsafe in enumerate(("=100", "10e2", "-1", "NaN"), start=1):
            response = client.post(
                f"/api/v1/analytics-workspace/reports/{report['id']}/metrics/{metric['id']}/snapshots",
                headers={"X-CSRF-Token": csrf},
                json=snapshot_payload(
                    f"analytics-invalid-decimal-{index:04d}",
                    report["revision"],
                    value=unsafe,
                ),
            )
            assert response.status_code == 422
            assert_manual_only(response.json()["data"])
        query = client.get("/api/v1/analytics-workspace/reports", params={"q": "https://example.invalid/secret"})
        assert query.status_code == 422
        assert query.headers["Cache-Control"] == "no-store, private"
        assert_manual_only(query.json()["data"])


def test_analytics_workspace_snapshot_decimal_comparison_and_duplicate_guard(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "analytics-decimal@example.com")
        report = create_report(client, csrf, "analytics-decimal-report-0001")
        report, metric = create_metric(client, csrf, report, "analytics-decimal-metric-0001")
        first = client.post(
            f"/api/v1/analytics-workspace/reports/{report['id']}/metrics/{metric['id']}/snapshots",
            headers={"X-CSRF-Token": csrf},
            json=snapshot_payload("analytics-snapshot-first-0001", report["revision"], observed_on="2026-07-01", value="10.00"),
        )
        assert first.status_code == 200 and first.json()["ok"] is True
        first_snapshot = first.json()["data"]["snapshot"]
        # Mutations return an opaque receipt. Full private values are fetched
        # only through the signed owner-scoped detail route.
        assert "value" not in first_snapshot
        assert first.json()["data"]["report"]["revision"] == report["revision"]
        second = client.post(
            f"/api/v1/analytics-workspace/reports/{report['id']}/metrics/{metric['id']}/snapshots",
            headers={"X-CSRF-Token": csrf},
            json=snapshot_payload("analytics-snapshot-second-0001", report["revision"], observed_on="2026-07-02", value="12.50"),
        )
        assert second.status_code == 200 and second.json()["ok"] is True
        assert "value" not in second.json()["data"]["snapshot"]
        detail = client.get(f"/api/v1/analytics-workspace/reports/{report['id']}")
        assert detail.status_code == 200 and detail.json()["ok"] is True
        detail_data = detail.json()["data"]
        snapshots = {item["id"]: item for item in detail_data["snapshots"]}
        assert snapshots[first_snapshot["id"]]["value"] == "10"
        assert snapshots[second.json()["data"]["snapshot"]["id"]]["value"] == "12.5"
        comparison = detail_data["comparisons"][metric["id"]]
        assert comparison == {
            "latest_value": "12.5", "previous_value": "10", "delta": "2.5", "change_percent": "25", "sample_count": 2,
        }
        duplicate = client.post(
            f"/api/v1/analytics-workspace/reports/{report['id']}/metrics/{metric['id']}/snapshots",
            headers={"X-CSRF-Token": csrf},
            json=snapshot_payload("analytics-snapshot-duplicate-0001", report["revision"], observed_on="2026-07-01", value="11"),
        )
        assert duplicate.status_code == 200
        assert duplicate.json()["error_code"] == "WEB_ANALYTICS_SNAPSHOT_DUPLICATE"
        archived = client.post(
            f"/api/v1/analytics-workspace/reports/{report['id']}/metrics/{metric['id']}/snapshots/{first_snapshot['id']}/state",
            headers={"X-CSRF-Token": csrf},
            json={
                "state": "archived", "expected_report_revision": report["revision"],
                "expected_revision": first_snapshot["revision"], "idempotency_key": "analytics-snapshot-archive-0001",
            },
        )
        assert archived.status_code == 200 and archived.json()["ok"] is True
        replacement = client.post(
            f"/api/v1/analytics-workspace/reports/{report['id']}/metrics/{metric['id']}/snapshots",
            headers={"X-CSRF-Token": csrf},
            json=snapshot_payload("analytics-snapshot-replacement-0001", report["revision"], observed_on="2026-07-01", value="11"),
        )
        assert replacement.status_code == 200 and replacement.json()["ok"] is True
        assert "value" not in replacement.json()["data"]["snapshot"]


def test_analytics_workspace_human_findings_have_no_ai_claim_and_are_audited(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "analytics-findings@example.com")
        report = create_report(client, csrf, "analytics-findings-report-0001")
        created = client.post(
            f"/api/v1/analytics-workspace/reports/{report['id']}/findings",
            headers={"X-CSRF-Token": csrf},
            json={
                "kind": "decision", "body": "Con người quyết định kiểm chứng thêm trước khi thay đổi kế hoạch.",
                "expected_report_revision": report["revision"], "idempotency_key": "analytics-finding-create-0001",
            },
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        finding = created.json()["data"]["finding"]
        assert "kind" not in finding
        assert_manual_only(created.json()["data"])
        detail = client.get(f"/api/v1/analytics-workspace/reports/{report['id']}")
        assert detail.status_code == 200 and detail.json()["ok"] is True
        detail_data = detail.json()["data"]
        persisted = next(item for item in detail_data["findings"] if item["id"] == finding["id"])
        assert persisted["kind"] == "decision"
        assert persisted["ai_recommendation_created"] is False
        assert any(item["action"] == "finding_created" for item in detail_data["events"])
        assert_manual_only(detail_data)
        events = client.get(f"/api/v1/analytics-workspace/reports/{report['id']}/events")
        assert events.status_code == 200 and events.json()["ok"] is True
        assert any(item["action"] == "finding_created" for item in events.json()["data"]["events"])
        assert_manual_only(events.json()["data"])


def test_analytics_workspace_can_be_disabled_without_importing_bot_or_payment_code(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        csrf = login(client, "analytics-disabled@example.com")
        guarded = client.get("/api/v1/analytics-workspace/summary")
        assert guarded.status_code == 503
        assert "WEBAPP_ANALYTICS_WORKSPACE_ENABLED" in guarded.text
        assert csrf
    source = (importlib.import_module("pathlib").Path(__file__).parents[1] / "copyfast_analytics_workspace.py").read_text(encoding="utf-8")
    for forbidden in (
        "import bot", "from bot", "import copyfast_bridge", "from copyfast_bridge", "import PayOS", "from PayOS",
        "import wallet", "from wallet", "import requests", "import httpx", "import urllib",
    ):
        assert forbidden not in source
