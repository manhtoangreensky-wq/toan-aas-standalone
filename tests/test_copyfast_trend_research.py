"""Focused contracts for the Web-native manual Trend Research planner."""

from __future__ import annotations

import importlib
import sqlite3
import sys

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry", "copyfast_api",
    "copyfast_pages", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations",
    "copyfast_image_studio", "copyfast_memory", "copyfast_prompt_library", "copyfast_music_media",
    "copyfast_content_studio", "copyfast_trend_research", "copyfast_voice_studio", "copyfast_video_studio",
    "copyfast_subtitle_workspace", "copyfast_support",
]

BOUNDARY_FIELDS = (
    "execution", "input_persisted", "live_search_called", "search_provider_called", "social_platform_called",
    "source_content_fetched", "source_content_stored", "provider_called", "bot_called", "job_created",
    "wallet_mutated", "payment_started", "asset_saved", "media_output_created", "publish_action_created",
    "fact_checked", "trend_claim_verified", "rights_verified",
)


def make_client(tmp_path, monkeypatch, *, enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "trend-research-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "trend-research-test-session-secret")
    monkeypatch.setenv("WEBAPP_TREND_RESEARCH_ENABLED", "true" if enabled else "false")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Trend Planner"},
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def payload(**overrides) -> dict:
    value = {"topic": "bình nước giữ nhiệt", "language": "vi"}
    value.update(overrides)
    return value


def storage_counts(db_path) -> dict[str, int]:
    with sqlite3.connect(db_path) as conn:
        return {
            table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in ("web_idempotency", "web_audit_events", "web_projects", "web_content_briefs")
        }


def assert_boundary(data: dict) -> None:
    assert set(data) == {"plan", *BOUNDARY_FIELDS}
    assert data["execution"] == "web_native_deterministic_trend_research_only"
    for field in BOUNDARY_FIELDS:
        if field != "execution":
            assert data[field] is False


def test_trend_research_is_signed_csrf_deterministic_and_non_persistent(tmp_path, monkeypatch):
    path = "/api/v1/trend-research/plan"
    db_path = tmp_path / "trend-research-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(path, json=payload()).status_code == 401
        csrf = login(client, "trend-research@example.com")
        before = storage_counts(db_path)
        assert client.post(path, json=payload()).status_code == 403

        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload())
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store, private"
        body = response.json()
        assert body["ok"] is True
        assert body["status"] == "draft"
        assert_boundary(body["data"])
        plan = body["data"]["plan"]
        assert set(plan) == {
            "title", "topic", "language", "research_mode", "freshness", "keyword_groups",
            "selection_criteria", "originality_guardrails", "next_workflows", "review_before_use",
        }
        assert plan["topic"] == "bình nước giữ nhiệt"
        assert plan["language"] == "vi"
        assert plan["research_mode"] == "manual_content_only"
        assert plan["freshness"] == "not_live_not_verified"
        expected_keywords = [
            "bình nước giữ nhiệt", "bình nước giữ nhiệt review", "bình nước giữ nhiệt lỗi thường gặp",
            "bình nước giữ nhiệt trước khi mua", "bình nước giữ nhiệt mẹo tiết kiệm thời gian",
        ]
        groups = plan["keyword_groups"]
        assert [group["surface"] for group in groups] == [
            "TikTok Search", "YouTube Shorts", "Facebook Reels", "Google Trends", "Cộng đồng phù hợp"
        ]
        assert [group["queries"] for group in groups] == [expected_keywords, expected_keywords, expected_keywords, [expected_keywords[0]], [expected_keywords[0]]]
        assert len(plan["selection_criteria"]) == 5
        assert len(plan["originality_guardrails"]) == 4
        assert [(item["label"], item["route"]) for item in plan["next_workflows"]] == [
            ("Content Prompt Pack", "/content/prompt-pack"),
            ("Image Prompt Composer", "/image/prompt-composer"),
            ("Video Prompt Planner", "/video-studio/prompt-planner"),
        ]
        assert all(isinstance(item, str) and item.strip() for item in plan["review_before_use"])
        assert "job_id" not in response.text
        assert "output_url" not in response.text

        replay = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload())
        assert replay.status_code == 200
        assert replay.json()["data"] == body["data"]
        assert storage_counts(db_path) == before


def test_trend_research_rejects_unsafe_input_and_returns_honest_policy_guards(tmp_path, monkeypatch):
    path = "/api/v1/trend-research/plan"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "trend-research-safety@example.com")
        for invalid in (
            {"topic": "x", "language": "vi"},
            {"topic": "x" * 181, "language": "vi"},
            {"topic": "two\nlines", "language": "vi"},
            {"topic": "https://untrusted.invalid/topic", "language": "vi"},
            {"topic": "<img src=x onerror=alert(1)>", "language": "vi"},
            {"topic": "@private_handle", "language": "vi"},
            {"topic": "api_key=super-secret-token-value-12345", "language": "vi"},
            {"topic": 42, "language": "vi"},
            {"topic": "hợp lệ", "language": "fr"},
            {"topic": "hợp lệ", "language": True},
            {"topic": "hợp lệ", "language": "vi", "provider_url": "https://provider.invalid"},
        ):
            assert client.post(path, headers={"X-CSRF-Token": csrf}, json=invalid).status_code == 422

        oversized = client.post(
            path,
            headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
            content=b'{"topic":"' + (b"x" * (17 * 1024)) + b'","language":"vi"}',
        )
        assert oversized.status_code == 413
        assert oversized.json()["error_code"] == "WEB_TREND_RESEARCH_BODY_TOO_LARGE"

        for blocked_topic in ("reup video người khác không có quyền", "tạo deepfake của người thật"):
            guarded = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload(topic=blocked_topic))
            assert guarded.status_code == 200
            body = guarded.json()
            assert body["ok"] is False
            assert body["status"] == "guarded"
            assert body["error_code"] == "WEB_TREND_RESEARCH_POLICY_GUARD"
            assert "plan" not in body["data"]
            assert body["data"]["execution"] == "web_native_deterministic_trend_research_only"
            assert all(body["data"][field] is False for field in BOUNDARY_FIELDS if field != "execution")


def test_trend_research_supports_english_copy_and_respects_maintenance_flag(tmp_path, monkeypatch):
    path = "/api/v1/trend-research/plan"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "trend-research-en@example.com")
        english = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload(topic="insulated bottle", language="en"))
        assert english.status_code == 200
        plan = english.json()["data"]["plan"]
        assert plan["language"] == "en"
        assert plan["keyword_groups"][0]["queries"] == [
            "insulated bottle", "insulated bottle review", "insulated bottle common mistakes",
            "insulated bottle before buying", "insulated bottle time-saving tips",
        ]

    with make_client(tmp_path, monkeypatch, enabled=False) as disabled:
        csrf = login(disabled, "trend-research-disabled@example.com")
        response = disabled.post(path, headers={"X-CSRF-Token": csrf}, json=payload())
        assert response.status_code == 503
        assert "WEBAPP_TREND_RESEARCH_ENABLED" in response.json()["message"]
