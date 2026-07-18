"""Focused contracts for the Web-native manual Growth Review."""

from __future__ import annotations

import importlib
import sqlite3
import sys

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry", "copyfast_api",
    "copyfast_pages", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations", "copyfast_storyboard_grid",
    "copyfast_image_studio", "copyfast_memory", "copyfast_prompt_library", "copyfast_music_media",
    "copyfast_content_studio", "copyfast_trend_research", "copyfast_growth_review", "copyfast_voice_studio",
    "copyfast_video_studio", "copyfast_subtitle_workspace", "copyfast_support",
]

BOUNDARY_FALSE_FIELDS = (
    "input_persisted", "platform_connected", "platform_data_verified", "canonical_revenue_read",
    "canonical_revenue_written", "ai_model_called", "provider_called", "bot_called", "bridge_called",
    "job_created", "wallet_mutated", "payment_started", "asset_saved", "publish_action_created",
    "delivery_created",
)


def make_client(tmp_path, monkeypatch, *, enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "growth-review-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "growth-review-test-session-secret")
    monkeypatch.setenv("WEBAPP_GROWTH_REVIEW_ENABLED", "true" if enabled else "false")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Growth Reviewer"},
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def payload(**overrides) -> dict:
    value = {
        "content_label": "Video bình giữ nhiệt tuần 1",
        "platform": "tiktok",
        "views": 10_000,
        "likes": 70,
        "comments": 20,
        "shares": 20,
        "clicks": 51,
        "manual_attributed_value_vnd": 100_001,
    }
    value.update(overrides)
    return value


def storage_counts(db_path) -> dict[str, int]:
    with sqlite3.connect(db_path) as conn:
        return {
            table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in ("web_idempotency", "web_audit_events", "web_projects", "web_analytics_reports")
        }


def assert_boundary(data: dict) -> None:
    assert data["execution"] == "web_native_manual_rule_review_only"
    assert data["manual_metrics_only"] is True
    for field in BOUNDARY_FALSE_FIELDS:
        assert data[field] is False


def test_growth_review_is_signed_csrf_rule_based_and_non_persistent(tmp_path, monkeypatch):
    path = "/api/v1/growth-review/evaluate"
    db_path = tmp_path / "growth-review-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        no_session = client.post(path, json=payload())
        assert no_session.status_code == 401
        assert_boundary(no_session.json()["data"])
        csrf = login(client, "growth-review@example.com")
        before = storage_counts(db_path)
        no_csrf = client.post(path, json=payload())
        assert no_csrf.status_code == 403
        assert_boundary(no_csrf.json()["data"])

        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload())
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store, private"
        body = response.json()
        assert body["ok"] is True
        assert body["status"] == "draft"
        assert_boundary(body["data"])
        review = body["data"]["review"]
        assert set(review) == {
            "content_label", "platform", "platform_label", "manual_inputs", "engagement_total", "score",
            "score_band", "score_breakdown", "recommendation", "rule_version", "provenance", "next_workflows",
        }
        assert review["score"] == 100
        assert review["recommendation"]["type"] == "scale"
        assert review["recommendation"]["score"] == 100
        assert review["manual_inputs"]["manual_attributed_value_vnd"] == 100_001
        assert review["provenance"] == {
            "kind": "manual_account_input", "platform_data_verified": False,
            "canonical_revenue": False, "input_persisted": False,
            "evaluated_at": review["provenance"]["evaluated_at"],
        }
        assert [(item["label"], item["route"]) for item in review["next_workflows"]] == [
            ("Content Prompt Pack", "/content/prompt-pack"),
            ("Gói review trước khi đăng", "/content/publish-review"),
            ("Analytics Workspace", "/analytics"),
        ]
        assert "job_id" not in response.text
        assert "checkout_url" not in response.text
        assert storage_counts(db_path) == before


def test_growth_review_preserves_bot_rule_priority_and_score_thresholds(tmp_path, monkeypatch):
    path = "/api/v1/growth-review/evaluate"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "growth-rules@example.com")
        scenarios = [
            (payload(views=1_000, likes=0, comments=0, shares=0, clicks=3, manual_attributed_value_vnd=0), "fix_cta", 20),
            (payload(views=299, likes=100, comments=0, shares=1, clicks=51, manual_attributed_value_vnd=0), "fix_hook", 40),
            (payload(views=300, likes=20, comments=10, shares=0, clicks=0, manual_attributed_value_vnd=0), "add_offer", 8),
            (payload(views=300, likes=0, comments=0, shares=0, clicks=0, manual_attributed_value_vnd=0), "pause_or_rewrite", 8),
        ]
        for data, expected_type, expected_score in scenarios:
            response = client.post(path, headers={"X-CSRF-Token": csrf}, json=data)
            assert response.status_code == 200
            review = response.json()["data"]["review"]
            assert review["recommendation"]["type"] == expected_type
            assert review["score"] == expected_score


def test_growth_review_rejects_unsafe_or_ambiguous_input_and_respects_flag(tmp_path, monkeypatch):
    path = "/api/v1/growth-review/evaluate"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "growth-review-safety@example.com")
        for invalid in (
            payload(content_label="x"),
            payload(content_label="two\nlines"),
            payload(content_label="https://untrusted.invalid/review"),
            payload(content_label="api_key=super-secret-token-value-12345"),
            payload(platform="linkedin"),
            payload(views=-1),
            payload(clicks="4"),
            payload(manual_attributed_value_vnd=9_000_000_000_001),
            {**payload(), "provider_url": "https://provider.invalid"},
        ):
            invalid_response = client.post(path, headers={"X-CSRF-Token": csrf}, json=invalid)
            assert invalid_response.status_code == 422
            assert_boundary(invalid_response.json()["data"])

        oversized = client.post(
            path,
            headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
            content=b'{"content_label":"' + (b"x" * (17 * 1024)) + b'"}',
        )
        assert oversized.status_code == 413
        assert oversized.json()["error_code"] == "WEB_GROWTH_REVIEW_BODY_TOO_LARGE"

    with make_client(tmp_path, monkeypatch, enabled=False) as disabled:
        csrf = login(disabled, "growth-review-disabled@example.com")
        response = disabled.post(path, headers={"X-CSRF-Token": csrf}, json=payload())
        assert response.status_code == 503
        assert "WEBAPP_GROWTH_REVIEW_ENABLED" in response.json()["message"]
        assert_boundary(response.json()["data"])


def test_growth_review_source_cannot_reach_bot_provider_or_financial_authority():
    from pathlib import Path

    source = (Path(__file__).parents[1] / "copyfast_growth_review.py").read_text(encoding="utf-8")
    for forbidden in (
        "import bot", "from bot", "import copyfast_bridge", "from copyfast_bridge", "import requests", "import httpx",
        "import urllib", "import PayOS", "from PayOS", "import subprocess", "import sqlite3",
    ):
        assert forbidden not in source


def test_growth_review_is_explicitly_excluded_from_pwa_cache_paths():
    from pathlib import Path

    worker = (Path(__file__).parents[1] / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
    shell = worker.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    public_navigation = worker.split("const PUBLIC_NAVIGATION_PATHS = Object.freeze([", 1)[1].split("]);", 1)[0]
    private_paths = worker.split("const PRIVATE_PATH_PREFIXES = Object.freeze([", 1)[1].split("]);", 1)[0]

    assert "api/v1/growth-review" not in shell
    assert '"/growth/ai"' not in public_navigation
    assert '"/" + "api/v1/growth-review"' in private_paths
    assert '"/growth/ai"' in private_paths
