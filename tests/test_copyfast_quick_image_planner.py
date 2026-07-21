"""Focused contracts for the frozen-Bot-derived Quick Image Planner."""

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
    "copyfast_content_studio", "copyfast_trend_research", "copyfast_media_factory",
    "copyfast_quick_image_planner", "copyfast_voice_studio", "copyfast_video_studio",
    "copyfast_subtitle_workspace", "copyfast_support",
]

BOUNDARY_FIELDS = (
    "execution", "input_persisted", "live_search_called", "search_provider_called", "social_platform_called",
    "source_content_fetched", "source_content_stored", "provider_called", "bot_called", "job_created",
    "wallet_mutated", "payment_started", "asset_saved", "media_output_created", "publish_action_created",
    "fact_checked", "trend_claim_verified", "rights_verified",
)


def make_client(tmp_path, monkeypatch, *, enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "quick-image-planner-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "quick-image-planner-test-session-secret")
    monkeypatch.setenv("WEBAPP_QUICK_IMAGE_PLANNER_ENABLED", "true" if enabled else "false")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Quick Planner"},
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
        "idea_source": "curated",
        "suggestion_key": "desk_organizer",
        "custom_prompt": "",
        "aspect_ratio": "9:16",
        "variation": 1,
        "brand_direction": "TOAN AAS · phong cách tinh tế",
        "brand_position": "bottom_right",
        "language": "vi",
    }
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
    assert data["execution"] == "web_native_deterministic_quick_image_planner_only"
    assert all(data[field] is False for field in BOUNDARY_FIELDS if field != "execution")


def test_quick_image_planner_is_signed_csrf_deterministic_and_non_persistent(tmp_path, monkeypatch):
    path = "/api/v1/quick-image-planner/plan"
    db_path = tmp_path / "quick-image-planner-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(path, json=payload()).status_code == 401
        csrf = login(client, "quick-image@example.com")
        before = storage_counts(db_path)
        assert client.post(path, json=payload()).status_code == 403

        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload())
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store, private"
        body = response.json()
        assert body["ok"] is True and body["status"] == "draft"
        assert_boundary(body["data"])
        plan = body["data"]["plan"]
        assert set(plan) == {
            "title", "language", "idea_source", "suggestion_key", "topic", "variation", "variation_label", "aspect_ratio",
            "brand_direction", "brand_position", "brand_position_label", "short_prompt", "detailed_prompt", "negative_prompt",
            "composition", "output_status", "summary", "review_checklist", "unavailable_capabilities", "next_workflows",
        }
        assert plan["idea_source"] == "curated"
        assert plan["suggestion_key"] == "desk_organizer"
        assert plan["variation"] == 1
        assert plan["aspect_ratio"] == "9:16"
        assert plan["brand_position"] == "bottom_right"
        assert plan["output_status"] == "prompt_plan_only_no_real_image"
        assert len(plan["review_checklist"]) == 4
        assert len(plan["unavailable_capabilities"]) == 4
        assert [(item["label"], item["route"]) for item in plan["next_workflows"]] == [
            ("Image Prompt Composer", "/image/prompt-composer"),
            ("Image Creative Studio", "/image-studio"),
            ("Content Prompt Pack", "/content/prompt-pack"),
        ]
        # The public explanation may name a boundary (for example ShopAI or
        # wallet) to say it was not called. Assert that no transport handle,
        # provider token, price or balance is leaked instead.
        for forbidden in ("job_id", "output_url", "confirm_token", "shopai|", "tier_price", "wallet_balance", "provider_id", "payos_"):
            assert forbidden not in response.text.lower()
        assert storage_counts(db_path) == before

        replay = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload())
        assert replay.status_code == 200 and replay.json()["data"] == body["data"]


def test_quick_image_planner_custom_brief_maps_full_draft_without_a_watermark_claim(tmp_path, monkeypatch):
    path = "/api/v1/quick-image-planner/plan"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "quick-image-custom@example.com")
        response = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json=payload(
                idea_source="custom",
                suggestion_key="",
                custom_prompt="Một chiếc balo nhẹ cho người đi làm bằng xe đạp, buổi sáng thành phố nhiều nắng",
                aspect_ratio="4:5",
                variation=2,
                brand_direction="",
                brand_position="none",
            ),
        )
        assert response.status_code == 200
        plan = response.json()["data"]["plan"]
        assert plan["idea_source"] == "custom"
        assert plan["suggestion_key"] == ""
        assert plan["brand_direction"] == ""
        assert plan["brand_position"] == "none"
        assert "balo nhẹ" in plan["detailed_prompt"]
        assert "watermark render" not in plan["summary"].lower()


def test_quick_image_planner_rejects_unsafe_or_invalid_input_and_has_raw_body_cap(tmp_path, monkeypatch):
    path = "/api/v1/quick-image-planner/plan"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "quick-image-safety@example.com")
        invalid_values = (
            payload(idea_source="unexpected"),
            payload(suggestion_key="qi_pick_1"),
            payload(variation="1"),
            payload(aspect_ratio="2:1"),
            payload(brand_direction="TOAN AAS", brand_position="none"),
            payload(brand_direction="", brand_position="bottom_right"),
            payload(language="fr"),
            payload(extra_provider_url="https://provider.invalid"),
            payload(idea_source="custom", suggestion_key="", custom_prompt="https://untrusted.invalid/image"),
            payload(idea_source="custom", suggestion_key="", custom_prompt="x"),
        )
        for invalid in invalid_values:
            rejected = client.post(path, headers={"X-CSRF-Token": csrf}, json=invalid)
            assert rejected.status_code == 422
            assert rejected.json()["data"]["execution"] == "web_native_deterministic_quick_image_planner_only"

        oversized = client.post(
            path,
            headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
            content=b'{"idea_source":"custom","suggestion_key":"","custom_prompt":"' + (b"x" * (17 * 1024)) + b'"}',
        )
        assert oversized.status_code == 413
        assert oversized.json()["error_code"] == "WEB_QUICK_IMAGE_PLANNER_BODY_TOO_LARGE"

        guarded = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json=payload(idea_source="custom", suggestion_key="", custom_prompt="tạo deepfake của người thật", brand_direction="", brand_position="none"),
        )
        assert guarded.status_code == 200
        body = guarded.json()
        assert body["ok"] is False and body["status"] == "guarded"
        assert body["error_code"] == "WEB_QUICK_IMAGE_PLANNER_POLICY_GUARD"
        assert "plan" not in body["data"]


def test_quick_image_planner_flag_and_engine_descriptor_fail_closed(tmp_path, monkeypatch):
    from copyfast_web_engine import ENGINE_MODE_WEB_NATIVE, engine_descriptor, engine_spec

    assert engine_descriptor("quick_image_planner", {}) == {"mode": ENGINE_MODE_WEB_NATIVE, "execution_state": "guarded"}
    assert engine_descriptor("quick_image_planner", {"quick_image_planner_enabled": True}) == {
        "mode": ENGINE_MODE_WEB_NATIVE,
        "execution_state": "ready",
    }
    assert engine_spec("quick_image_planner").required_flags == ("quick_image_planner_enabled",)

    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        csrf = login(client, "quick-image-disabled@example.com")
        response = client.post("/api/v1/quick-image-planner/plan", headers={"X-CSRF-Token": csrf}, json=payload())
        assert response.status_code == 503
        assert "WEBAPP_QUICK_IMAGE_PLANNER_ENABLED" in response.json()["message"]
