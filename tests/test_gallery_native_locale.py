"""Native Gallery reads and saves share one server-owned locale projection."""

from __future__ import annotations

import importlib
import sqlite3
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest


ITEM = "caption_cta_food_cafe_1"
NATIVE = {
    "vi": ("Chú thích bán hàng - Đồ ăn / quán cà phê", "Câu lệnh video Meta AI", "Chú thích bán hàng"),
    "en": ("Sales caption - Food / cafe", "Meta AI Video Prompt", "Sales caption"),
    "zh": ("销售配文 - 美食 / 咖啡馆", "Meta AI 视频提示词", "销售配文"),
}
ITEM_KEYS = {"id", "category_id", "category_title", "industry_id", "industry", "title", "prompt", "goals", "platforms"}


def make_client(tmp_path, monkeypatch):
    # Only this pytest child gets fake settings; no dotenv or OS configuration is written.
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "gallery-native.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "isolated-gallery-native-session-secret")
    monkeypatch.setenv("WEBAPP_MEMORY_CENTER_ENABLED", "true")
    for name in ("copyfast_db", "copyfast_auth", "copyfast_free_prompt_gallery", "copyfast_memory"):
        sys.modules.pop(name, None)
    auth = importlib.import_module("copyfast_auth")
    gallery = importlib.import_module("copyfast_free_prompt_gallery")
    memory = importlib.import_module("copyfast_memory")
    app = FastAPI()
    app.include_router(auth.router, prefix="/api/v1/auth")
    app.include_router(gallery.router)
    app.include_router(memory.router)
    return TestClient(app)


def sign_in(client):
    body = {"email": "native-gallery@example.com", "password": "isolated-gallery-password", "display_name": "Native Gallery"}
    assert client.post("/api/v1/auth/register", json=body).status_code == 200
    result = client.post("/api/v1/auth/login", json={key: body[key] for key in ("email", "password")})
    assert result.status_code == 200
    return {"X-CSRF-Token": result.json()["data"]["csrf_token"]}


@pytest.mark.parametrize("lang", ["vi", "en", "zh"])
def test_native_catalogue_list_detail_and_search_keep_exact_contract(tmp_path, monkeypatch, lang):
    with make_client(tmp_path, monkeypatch) as client:
        sign_in(client)
        catalogue = client.get("/api/v1/free-prompt-gallery/catalog", params={"lang": lang})
        assert catalogue.status_code == 200
        assert catalogue.headers["cache-control"] == "private, no-store"
        data = catalogue.json()["data"]
        assert set(data) == {"snapshot_version", "description", "total_items", "categories", "industries", "boundaries"}
        assert data["total_items"] == 140
        assert data["categories"][0]["title"] == NATIVE[lang][1]
        listing = client.get("/api/v1/free-prompt-gallery/items", params={
            "lang": lang, "q": NATIVE[lang][2], "industry_id": "food_cafe",
        }).json()["data"]
        assert listing["pagination"]["total_items"] == 1
        item = listing["items"][0]
        assert set(item) == ITEM_KEYS
        assert item["id"] == ITEM
        assert item["title"] == NATIVE[lang][0]
        assert item["goals"] == ["sell", "engagement"]
        assert item["platforms"] == ["facebook", "instagram", "tiktok"]
        detail = client.get(f"/api/v1/free-prompt-gallery/items/{ITEM}", params={"lang": lang}).json()["data"]
        assert detail["item"] == item
        assert detail["snapshot_version"] == "2026-07-15.1"
        assert set(detail) == {"snapshot_version", "item", "copy_instruction", "boundaries"}


@pytest.mark.parametrize("lang,label", [("vi", "Xây dựng thương hiệu"), ("en", "Brand building"), ("zh", "品牌建设")])
def test_native_taxonomy_terms_are_searchable_without_changing_filter_ids(tmp_path, monkeypatch, lang, label):
    with make_client(tmp_path, monkeypatch) as client:
        sign_in(client)
        response = client.get("/api/v1/free-prompt-gallery/items", params={"lang": lang, "q": label, "goal": "branding"})
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["pagination"]["total_items"] == 20
        assert {item["category_id"] for item in data["items"]} == {"image_prompt"}
        assert data["filters"]["goal"] == "branding"


@pytest.mark.parametrize("lang", ["vi", "en", "zh"])
def test_native_save_matches_displayed_prompt_and_retry_is_locale_bound(tmp_path, monkeypatch, lang):
    with make_client(tmp_path, monkeypatch) as client:
        headers = sign_in(client)
        item = client.get(f"/api/v1/free-prompt-gallery/items/{ITEM}", params={"lang": lang}).json()["data"]["item"]
        assert item["title"] == NATIVE[lang][0]
        endpoint = f"/api/v1/memory/gallery-items/{ITEM}/save"
        payload = {"idempotency_key": "gallery-native-retry-0001"}
        saved = client.post(endpoint, params={"lang": lang}, headers=headers, json=payload)
        assert saved.status_code == 200
        receipt = saved.json()["data"]
        assert set(receipt["note"]) == {"id", "category", "priority", "state", "revision"}
        assert item["prompt"] not in saved.text
        note = client.get(f"/api/v1/memory/notes/{receipt['note']['id']}").json()["data"]["note"]
        assert item["title"] in note["title"]
        assert f"\n\n{item['prompt']}\n\n" in note["content"]
        replay = client.post(endpoint, params={"lang": lang}, headers=headers, json=payload)
        assert replay.json()["data"]["note"]["id"] == receipt["note"]["id"]
        different = "en" if lang != "en" else "zh"
        collision = client.post(endpoint, params={"lang": different}, headers=headers, json=payload)
        assert collision.status_code == 409
    with sqlite3.connect(tmp_path / "gallery-native.db") as conn:
        assert conn.execute("SELECT COUNT(*) FROM web_memory_notes").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM web_memory_note_versions").fetchone()[0] == 1


@pytest.mark.parametrize("bad", ["", "VI", "fr", "en-US"])
def test_explicit_invalid_locale_fails_closed_for_all_four_endpoints(tmp_path, monkeypatch, bad):
    with make_client(tmp_path, monkeypatch) as client:
        headers = sign_in(client)
        for suffix in ("catalog", "items", f"items/{ITEM}"):
            result = client.get(f"/api/v1/free-prompt-gallery/{suffix}", params={"lang": bad})
            assert result.status_code == 422
        result = client.post(f"/api/v1/memory/gallery-items/{ITEM}/save", params={"lang": bad},
                             headers=headers, json={"idempotency_key": "gallery-invalid-lang-0001"})
        assert result.status_code == 422


def test_legacy_default_and_vi_replay_preserve_existing_note_bytes(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        headers = sign_in(client)
        legacy = client.get(f"/api/v1/free-prompt-gallery/items/{ITEM}").json()["data"]["item"]
        assert legacy["title"] == "Caption bán hàng - Đồ ăn / quán cafe"
        endpoint = f"/api/v1/memory/gallery-items/{ITEM}/save"
        payload = {"idempotency_key": "gallery-legacy-replay-0001"}
        first = client.post(endpoint, headers=headers, json=payload)
        note_id = first.json()["data"]["note"]["id"]
        before = client.get(f"/api/v1/memory/notes/{note_id}").json()["data"]["note"]
        retry = client.post(endpoint, params={"lang": "vi"}, headers=headers, json=payload)
        assert retry.json()["data"]["note"]["id"] == note_id
        after = client.get(f"/api/v1/memory/notes/{note_id}").json()["data"]["note"]
        assert after == before
        assert legacy["prompt"] in after["content"]
        for extra in ("lang", "prompt", "title"):
            bad = client.post(endpoint, params={"lang": "en"}, headers=headers,
                              json={"idempotency_key": "gallery-body-allowlist-0001", extra: "untrusted"})
            assert bad.status_code == 422
