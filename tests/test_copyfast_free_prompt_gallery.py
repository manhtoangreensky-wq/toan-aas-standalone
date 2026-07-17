"""Focused contract tests for the isolated Web Free Prompt Gallery snapshot."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest


MODULES = ["copyfast_db", "copyfast_auth", "copyfast_free_prompt_gallery"]
WEB_ROOT = Path(__file__).resolve().parents[1]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "free-prompt-gallery.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-free-prompt-gallery-session-secret")
    for name in MODULES:
        sys.modules.pop(name, None)

    auth = importlib.import_module("copyfast_auth")
    gallery = importlib.import_module("copyfast_free_prompt_gallery")
    app = FastAPI()
    app.include_router(auth.router, prefix="/api/v1/auth")
    # Intentionally mount only in this temporary test application.  The
    # production app/router remains untouched by this data-module task.
    app.include_router(gallery.router)
    return TestClient(app)


def login(client: TestClient) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": "gallery-owner@example.com",
            "password": "correct-horse-battery-staple",
            "display_name": "Gallery Owner",
        },
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": "gallery-owner@example.com", "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return str(signed_in.json()["data"]["csrf_token"])


def assert_boundaries(data: dict) -> None:
    boundaries = data["boundaries"]
    assert boundaries == {
        "execution": "web_native_static_prompt_gallery",
        "snapshot_read_only": True,
        "gallery_request_persisted": False,
        "provider_called": False,
        "bot_called": False,
        "bridge_called": False,
        "job_created": False,
        "wallet_mutated": False,
        "payment_started": False,
        "asset_saved": False,
        "publish_action_created": False,
        "delivery_created": False,
    }


def test_gallery_requires_signed_session_and_exposes_full_deterministic_catalog(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        assert client.get("/api/v1/free-prompt-gallery/catalog").status_code == 401
        csrf = login(client)
        # Read-only endpoints require a signed session but deliberately do not
        # demand CSRF.  A CSRF token exists only because login created it.
        assert csrf

        catalog = client.get("/api/v1/free-prompt-gallery/catalog")
        assert catalog.status_code == 200
        assert catalog.headers["cache-control"] == "private, no-store"
        assert catalog.headers["pragma"] == "no-cache"
        assert catalog.headers["vary"] == "Cookie"
        catalog_data = catalog.json()["data"]
        assert catalog.json()["ok"] is True
        assert catalog_data["snapshot_version"] == "2026-07-15.1"
        assert catalog_data["total_items"] == 140
        assert [item["id"] for item in catalog_data["categories"]] == [
            "meta_ai_video",
            "image_prompt",
            "video_prompt",
            "caption_cta",
            "hook_script",
            "document_checklist",
            "music_sfx",
        ]
        assert len(catalog_data["industries"]) == 20
        assert catalog_data["industries"][0] == {"id": "shop_online", "title": "Shop online", "item_count": 7}
        assert catalog_data["industries"][-1] == {"id": "education", "title": "Giáo dục / kỹ năng", "item_count": 7}
        assert all(category["item_count"] == 20 for category in catalog_data["categories"])
        assert_boundaries(catalog_data)

        first_page = client.get(
            "/api/v1/free-prompt-gallery/items",
            params={"category_id": "caption_cta", "page": 1, "page_size": 3},
        )
        assert first_page.status_code == 200
        first_data = first_page.json()["data"]
        assert first_data["filters"] == {
            "category_id": "caption_cta",
            "industry_id": "",
            "goal": "",
            "platform": "",
            "q": "",
        }
        assert first_data["pagination"] == {
            "page": 1,
            "page_size": 3,
            "total_items": 20,
            "total_pages": 7,
            "has_next": True,
            "has_previous": False,
        }
        assert [item["id"] for item in first_data["items"]] == [
            "caption_cta_shop_online_1",
            "caption_cta_affiliate_1",
            "caption_cta_cosmetics_1",
        ]
        assert_boundaries(first_data)

        next_page = client.get(
            "/api/v1/free-prompt-gallery/items",
            params={"category_id": "caption_cta", "page": 2, "page_size": 3},
        )
        assert [item["id"] for item in next_page.json()["data"]["items"]] == [
            "caption_cta_fragrance_1",
            "caption_cta_spa_1",
            "caption_cta_fashion_1",
        ]

        combined = client.get(
            "/api/v1/free-prompt-gallery/items",
            params={"industry_id": "food_cafe", "goal": "sell", "platform": "tiktok", "q": "caption bán hàng"},
        )
        assert combined.status_code == 200
        combined_data = combined.json()["data"]
        assert [item["id"] for item in combined_data["items"]] == ["caption_cta_food_cafe_1"]
        assert combined_data["items"][0]["title"] == "Caption bán hàng - Đồ ăn / quán cafe"
        assert "món ăn hoặc đồ uống nổi bật" in combined_data["items"][0]["prompt"]

        detail = client.get("/api/v1/free-prompt-gallery/items/caption_cta_food_cafe_1")
        assert detail.status_code == 200
        detail_data = detail.json()["data"]
        assert detail_data["item"] == combined_data["items"][0]
        assert "tự rà soát" in detail_data["copy_instruction"]
        assert_boundaries(detail_data)


def test_gallery_filters_and_detail_fail_closed_without_persisting_gallery_state(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        login(client)
        invalid_category = client.get("/api/v1/free-prompt-gallery/items", params={"category_id": "not-a-real-category"})
        assert invalid_category.status_code == 422
        invalid_goal = client.get("/api/v1/free-prompt-gallery/items", params={"goal": "trade"})
        assert invalid_goal.status_code == 422
        secret_query = client.get("/api/v1/free-prompt-gallery/items", params={"q": "api_key=do-not-echo-this"})
        assert secret_query.status_code == 422
        too_long_query = client.get("/api/v1/free-prompt-gallery/items", params={"q": "x" * 161})
        assert too_long_query.status_code == 422
        malformed_id = client.get("/api/v1/free-prompt-gallery/items/not-valid-id!")
        assert malformed_id.status_code == 422
        missing = client.get("/api/v1/free-prompt-gallery/items/caption_cta_notreal_1")
        assert missing.status_code == 404
        assert missing.json() == {
            "ok": False,
            "status": "guarded",
            "message": "Không tìm thấy prompt trong snapshot hiện tại.",
            "data": {},
            "error_code": "WEB_FREE_PROMPT_NOT_FOUND",
        }
        assert missing.headers["cache-control"] == "private, no-store"

        # The gallery has no write route and its own source has no database,
        # Bot, bridge, provider or file-load dependency.  Session persistence
        # remains solely the responsibility of the shared auth middleware.
        source = (WEB_ROOT / "copyfast_free_prompt_gallery.py").read_text(encoding="utf-8")
        for forbidden in (
            "free_tools_hub",
            "bot.py",
            "copyfast_db",
            "copyfast_bridge",
            "transaction(",
            "open(",
            "json.load",
            "requests.",
            "httpx.",
        ):
            assert forbidden not in source.lower()


def test_pure_snapshot_expansion_filter_and_pagination_are_stable():
    gallery = importlib.import_module("copyfast_free_prompt_gallery")
    first = gallery.expand_free_prompt_snapshot()
    second = gallery.expand_free_prompt_snapshot()
    assert len(first) == len(second) == 140
    assert [item["id"] for item in first] == [item["id"] for item in second]
    assert first[0]["id"] == "meta_ai_video_shop_online_1"
    assert first[-1]["id"] == "music_sfx_education_1"
    assert isinstance(first[0]["goals"], tuple)
    with pytest.raises(TypeError):
        first[0]["title"] = "cannot mutate snapshot"
    assert gallery.free_prompt_item("meta_ai_video_shop_online_1") is not None
    assert gallery.free_prompt_item("unknown") is None

    filtered = gallery.filter_free_prompt_items(first, industry_id="fitness", goal="sell")
    assert [item["id"] for item in filtered] == [
        "meta_ai_video_fitness_1",
        "image_prompt_fitness_1",
        "video_prompt_fitness_1",
        "caption_cta_fitness_1",
        "hook_script_fitness_1",
    ]
    page, metadata = gallery.paginate_free_prompt_items(filtered, page=2, page_size=2)
    assert [item["id"] for item in page] == ["video_prompt_fitness_1", "caption_cta_fitness_1"]
    assert metadata == {
        "page": 2,
        "page_size": 2,
        "total_items": 5,
        "total_pages": 3,
        "has_next": True,
        "has_previous": True,
    }
