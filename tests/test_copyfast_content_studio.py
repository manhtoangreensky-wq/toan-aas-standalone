"""Risk-focused contracts for the Web-native Creative Content Studio."""

from __future__ import annotations

import importlib
import sqlite3
import sys

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_api", "copyfast_pages", "copyfast_projects", "copyfast_assets",
    "copyfast_project_packages", "copyfast_document_operations", "copyfast_image_runtime",
    "copyfast_image_operations", "copyfast_memory", "copyfast_prompt_library",
    "copyfast_music_media", "copyfast_content_studio", "copyfast_support",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "content-studio-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "content-studio-test-session-secret")
    monkeypatch.setenv("WEBAPP_CONTENT_STUDIO_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_MEMORY_CENTER_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROMPT_LIBRARY_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_MUSIC_MEDIA_WORKSPACE_ENABLED", "true")
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.delenv("RAILWAY_VOLUME_MOUNT_PATH", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def register_and_login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Content Owner"},
    )
    assert registered.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    return login.json()["data"]["csrf_token"]


def brief_payload(key: str, **overrides) -> dict:
    payload = {
        "title": "Ra mắt bộ sưu tập mùa hè",
        "content_kind": "caption_hashtag",
        "subject": "Bộ sưu tập chăm sóc da mùa hè cho người bận rộn",
        "objective": "Giải thích lợi ích có thể kiểm chứng",
        "audience": "Người đi làm 22 đến 35 tuổi",
        "platform": "Instagram",
        "tone": "Rõ ràng và gần gũi",
        "language": "vi",
        "call_to_action": "Xem hướng dẫn sử dụng trước khi chọn sản phẩm.",
        "brief_text": "Nêu lợi ích thực tế, cách dùng an toàn và chỗ cần đội ngũ kiểm tra trước khi đăng.",
        "constraints": "Không nêu số liệu không có nguồn và không giả kết quả điều trị.",
        "tags": ["summer", "skincare"],
        "rights_note": "Tôi sẽ xác nhận quyền sử dụng tài sản và claim trước khi publish.",
        "project_id": "",
        "campaign_plan_id": "",
        "prompt_template_id": "",
        "media_collection_id": "",
        "idempotency_key": key,
    }
    payload.update(overrides)
    return payload


def prompt_pack_payload(kind: str = "meta_ai_prompt", topic: str = "Bộ dụng cụ pha cà phê cho người mới", variant_seed: int = 0, **overrides) -> dict:
    payload = {
        "kind": kind,
        "topic": topic,
        "variant_seed": variant_seed,
    }
    payload.update(overrides)
    return payload


def prompt_pack_storage_counts(db_path) -> dict[str, int]:
    """Return only tables that the stateless Prompt Pack must never touch."""

    tables = (
        "web_content_briefs",
        "web_content_brief_versions",
        "web_content_variants",
        "web_content_variant_versions",
        "web_content_studio_events",
        "web_idempotency",
        "web_audit_events",
    )
    with sqlite3.connect(db_path) as conn:
        return {
            table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in tables
        }


def prompt_pack_memory_storage_counts(db_path) -> dict[str, int]:
    """Count only durable records relevant to the explicit Memory handoff."""

    tables = (
        "web_memory_notes",
        "web_memory_note_versions",
        "web_memory_events",
        "web_content_briefs",
        "web_content_brief_versions",
        "web_content_variants",
        "web_content_variant_versions",
        "web_content_studio_events",
        "web_idempotency",
        "web_audit_events",
    )
    with sqlite3.connect(db_path) as conn:
        return {
            table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in tables
        }


def create_brief(client: TestClient, csrf: str, key: str = "content-studio-create-0001", **overrides) -> dict:
    response = client.post("/api/v1/content-studio/briefs", headers={"X-CSRF-Token": csrf}, json=brief_payload(key, **overrides))
    assert response.status_code == 200
    assert response.json()["ok"] is True
    receipt = response.json()["data"]["brief"]
    detail = client.get(f"/api/v1/content-studio/briefs/{receipt['id']}")
    assert detail.status_code == 200
    return detail.json()["data"]["brief"]


def test_content_prompt_pack_is_session_csrf_bounded_and_non_persistent(tmp_path, monkeypatch):
    """The Bot-derived recipes remain a request-only Web-native text tool."""

    db_path = tmp_path / "content-studio-test.db"
    path = "/api/v1/content-studio/tools/prompt-pack"
    topic = "Bộ dụng cụ pha cà phê cho người mới"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(path, json=prompt_pack_payload(topic=topic)).status_code == 401
        csrf = register_and_login(client, "content-prompt-pack@example.com")
        before = prompt_pack_storage_counts(db_path)

        denied = client.post(path, json=prompt_pack_payload(topic=topic))
        assert denied.status_code == 403

        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=prompt_pack_payload(topic=topic))
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store, private"
        body = response.json()
        assert body["ok"] is True
        assert body["status"] == "draft"
        data = body["data"]
        assert set(data) == {
            "pack",
            "execution",
            "input_persisted",
            "provider_called",
            "job_created",
            "payment_started",
            "publish_action_created",
            "fact_checked",
            "rights_verified",
        }
        assert data["execution"] == "local_deterministic_text_only"
        for key in (
            "input_persisted",
            "provider_called",
            "job_created",
            "payment_started",
            "publish_action_created",
            "fact_checked",
            "rights_verified",
        ):
            assert data[key] is False
        pack = data["pack"]
        assert pack["kind"] == "meta_ai_prompt"
        assert pack["topic"] == topic
        assert 1 <= len(pack["sections"]) <= 6
        assert all(section["label"] and 1 <= len(section["items"]) <= 6 for section in pack["sections"])
        assert pack["verify_before_publish"]
        assert "job_id" not in response.text
        assert "output_url" not in response.text

        # Repeating a stateless request returns the same deterministic draft;
        # changing the bounded seed selects another fixed template variation.
        repeated = client.post(path, headers={"X-CSRF-Token": csrf}, json=prompt_pack_payload(topic=topic))
        changed = client.post(path, headers={"X-CSRF-Token": csrf}, json=prompt_pack_payload(topic=topic, variant_seed=1))
        assert repeated.status_code == changed.status_code == 200
        assert repeated.json()["data"]["pack"] == pack
        assert changed.json()["data"]["pack"] != pack

        # All five Bot-derived recipe groups are exposed through the same safe
        # Web contract instead of a Bot callback/provider workflow.
        for kind in ("caption_hashtag", "content_ideas", "hook_script", "image_video_prompt"):
            generated = client.post(path, headers={"X-CSRF-Token": csrf}, json=prompt_pack_payload(kind=kind, topic=topic, variant_seed=7))
            assert generated.status_code == 200
            generated_data = generated.json()["data"]
            assert generated_data["pack"]["kind"] == kind
            assert generated_data["execution"] == "local_deterministic_text_only"
            assert generated_data["provider_called"] is False
            assert generated_data["job_created"] is False
            assert generated_data["payment_started"] is False
            if kind == "hook_script":
                sections = generated_data["pack"]["sections"]
                assert [section["label"] for section in sections] == [
                    "3 hook mở đầu", "Kịch bản 15 giây", "Kịch bản 30 giây", "CTA"
                ]
                assert topic in sections[0]["items"][0]
                assert "0–3s" in sections[1]["items"][0]
                assert "0–4s" in sections[2]["items"][0]

        # The endpoint must not create a brief, revision, variant, event,
        # idempotency receipt, or audit detail containing the private topic.
        assert prompt_pack_storage_counts(db_path) == before

        malformed = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json=prompt_pack_payload(kind="not-a-prompt-pack", topic="x", provider_url="https://invalid.example"),
        )
        assert malformed.status_code == 422
        secret = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json=prompt_pack_payload(topic="api_key=super-secret-token-value-12345"),
        )
        assert secret.status_code == 422
        bad_seed = client.post(path, headers={"X-CSRF-Token": csrf}, json=prompt_pack_payload(topic=topic, variant_seed=-1))
        assert bad_seed.status_code == 422

        guarded = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json=prompt_pack_payload(topic="Viết nội dung theo phong cách của một ca sĩ cụ thể"),
        )
        assert guarded.status_code == 200
        assert guarded.json()["ok"] is False
        assert guarded.json()["status"] == "guarded"
        assert guarded.json()["error_code"] == "WEB_CONTENT_ORIGINALITY_GUARD"
        assert "pack" not in guarded.json().get("data", {})

        oversized = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json=prompt_pack_payload(topic="x" * (129 * 1024)),
        )
        assert oversized.status_code == 413
        assert oversized.json()["error_code"] == "WEB_CONTENT_STUDIO_BODY_TOO_LARGE"
        assert oversized.headers["Cache-Control"] == "no-store, private"
        assert prompt_pack_storage_counts(db_path) == before


def test_content_prompt_pack_memory_save_is_signed_recomputed_and_owner_scoped(tmp_path, monkeypatch):
    """A reviewed pack becomes one private Web note, never a Bot/pipeline write."""

    db_path = tmp_path / "content-studio-test.db"
    path = "/api/v1/content-studio/tools/prompt-pack/save"
    topic = "Máy xay cà phê mini cho căn hộ nhỏ"
    payload = prompt_pack_payload(
        topic=topic,
        variant_seed=17,
        destination="memory_note",
        idempotency_key="content-prompt-pack-save-memory-0001",
    )
    boundary_keys = (
        "draft_recomputed_on_server",
        "web_note_persisted",
        "browser_result_persisted",
        "pending_bot_save_created",
        "telegram_state_changed",
        "bot_called",
        "bridge_called",
        "provider_called",
        "job_created",
        "wallet_mutated",
        "payment_started",
        "asset_saved",
        "publish_action_created",
        "delivery_created",
        "fact_checked",
        "rights_verified",
    )
    with make_client(tmp_path, monkeypatch) as client:
        # A cookie session and a matching CSRF token are both mandatory before
        # parsing an otherwise valid durable-write request.
        assert client.post(path, json=payload).status_code == 401
        csrf = register_and_login(client, "content-prompt-pack-memory-owner@example.com")
        assert client.post(path, json=payload).status_code == 403
        before = prompt_pack_memory_storage_counts(db_path)

        # Only the narrow deterministic inputs are accepted.  In particular,
        # a browser cannot inject a generated body, choose an account, or
        # redirect this save to another store.
        invalid_requests = (
            {key: value for key, value in payload.items() if key != "destination"},
            {**payload, "destination": "prompt_library"},
            {key: value for key, value in payload.items() if key != "idempotency_key"},
            {**payload, "content": "browser-authored text must never be stored"},
            {**payload, "account_id": "browser-selected-account"},
        )
        for invalid in invalid_requests:
            rejected = client.post(path, headers={"X-CSRF-Token": csrf}, json=invalid)
            assert rejected.status_code == 422
        assert prompt_pack_memory_storage_counts(db_path) == before

        # Compare against the request-only preview without making it part of
        # the save request: the saved material must be recomputed server-side.
        preview = client.post(
            "/api/v1/content-studio/tools/prompt-pack",
            headers={"X-CSRF-Token": csrf},
            json=prompt_pack_payload(topic=topic, variant_seed=17),
        )
        assert preview.status_code == 200
        expected_pack = preview.json()["data"]["pack"]

        created = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload)
        assert created.status_code == 200
        assert created.headers["Cache-Control"] == "no-store, private"
        body = created.json()
        assert body["ok"] is True
        assert body["status"] == "completed"
        assert topic not in created.text
        data = body["data"]
        assert data["destination"] == "memory_note"
        assert data["execution"] == "web_native_memory_note_server_recomputed"
        assert data["note"] == {
            "id": data["note"]["id"],
            "revision": 1,
            "state": "active",
            "category": "Content Prompt Pack",
            "priority": "normal",
        }
        assert all(data[key] is (key in {"draft_recomputed_on_server", "web_note_persisted"}) for key in boundary_keys)
        assert "job_id" not in created.text
        assert "output_url" not in created.text

        note_id = data["note"]["id"]
        detail = client.get(f"/api/v1/memory/notes/{note_id}")
        assert detail.status_code == 200
        saved_note = detail.json()["data"]["note"]
        assert saved_note["title"] == "Content Prompt Pack · Prompt Meta AI"
        assert saved_note["category"] == "Content Prompt Pack"
        assert saved_note["content"].startswith("Content Prompt Pack — bản nháp Web đã được dựng lại trên máy chủ.")
        assert f"Chủ đề: {topic}" in saved_note["content"]
        for section in expected_pack["sections"]:
            assert f"## {section['label']}" in saved_note["content"]
            assert all(item in saved_note["content"] for item in section["items"])

        after_create = prompt_pack_memory_storage_counts(db_path)
        assert after_create["web_memory_notes"] == before["web_memory_notes"] + 1
        assert after_create["web_memory_note_versions"] == before["web_memory_note_versions"] + 1
        assert after_create["web_memory_events"] == before["web_memory_events"] + 1
        assert after_create["web_idempotency"] == before["web_idempotency"] + 1
        assert after_create["web_audit_events"] == before["web_audit_events"] + 1
        for table in (
            "web_content_briefs",
            "web_content_brief_versions",
            "web_content_variants",
            "web_content_variant_versions",
            "web_content_studio_events",
        ):
            assert after_create[table] == before[table]

        # The replay receipt and audit stay content-free.  The one-way request
        # fingerprint may bind the topic, but it must never retain it verbatim.
        with sqlite3.connect(db_path) as conn:
            receipt = conn.execute(
                "SELECT response_json, request_fingerprint FROM web_idempotency WHERE key=?",
                (payload["idempotency_key"],),
            ).fetchone()
            audit_rows = conn.execute(
                "SELECT action, target, detail FROM web_audit_events WHERE action=?",
                ("web.content_studio.prompt_pack.save_memory",),
            ).fetchall()
        assert receipt is not None
        assert topic not in str(receipt[0])
        assert topic not in str(receipt[1])
        assert audit_rows
        assert all(topic not in "\n".join(str(value or "") for value in row) for row in audit_rows)

        replay = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload)
        assert replay.status_code == 200
        assert replay.json() == body
        assert prompt_pack_memory_storage_counts(db_path) == after_create

        # A reused key may not silently attach a second note to altered input.
        changed = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json={**payload, "topic": "Máy pha cà phê tự động cho văn phòng"},
        )
        assert changed.status_code == 409
        assert prompt_pack_memory_storage_counts(db_path) == after_create

        # Memory reads retain the account-scoped ownership rule even though
        # this note was created by a Content Studio route.
        with make_client(tmp_path, monkeypatch) as other:
            other_csrf = register_and_login(other, "content-prompt-pack-memory-other@example.com")
            assert other_csrf
            hidden = other.get(f"/api/v1/memory/notes/{note_id}")
            assert hidden.status_code == 200
            assert hidden.json()["ok"] is False
            assert hidden.json()["error_code"] == "WEB_MEMORY_NOTE_NOT_FOUND"
            assert topic not in hidden.text


def test_contextual_ad_prompt_is_session_csrf_bounded_and_non_persistent(tmp_path, monkeypatch):
    """Bot's pending wizard becomes one signed, stateless Web request."""

    db_path = tmp_path / "content-studio-test.db"
    path = "/api/v1/content-studio/tools/contextual-ad-prompt"
    payload = {
        "topic": "Bình nước giữ nhiệt cho dân văn phòng",
        "goal": "sell",
        "platform": "tiktok",
        "aspect_ratio": "9:16",
        "style": "real",
    }
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(path, json=payload).status_code == 401
        csrf = register_and_login(client, "contextual-ad-prompt@example.com")
        before = prompt_pack_storage_counts(db_path)

        assert client.post(path, json=payload).status_code == 403
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload)
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store, private"
        body = response.json()
        assert body["ok"] is True
        assert body["status"] == "draft"
        data = body["data"]
        assert set(data) == {
            "plan", "execution", "input_persisted", "provider_called", "bot_called", "job_created",
            "wallet_mutated", "payment_started", "asset_saved", "media_output_created", "publish_action_created",
            "fact_checked", "rights_verified",
        }
        assert data["execution"] == "web_native_deterministic_contextual_ad_prompt_only"
        for key in set(data) - {"plan", "execution"}:
            assert data[key] is False
        plan = data["plan"]
        assert set(plan) == {
            "title", "topic", "industry_id", "industry", "audience", "goal", "platform", "aspect_ratio", "style",
            "duration_seconds", "primary_prompt", "variants", "caption", "hashtags", "cta", "shot_list", "negative_prompt",
            "music_sfx", "copy_instruction", "review_before_use",
        }
        assert plan["topic"] == payload["topic"]
        assert plan["platform"] == "TikTok"
        assert plan["aspect_ratio"] == "9:16"
        assert plan["duration_seconds"] == 12
        assert len(plan["variants"]) == 3
        assert len(plan["shot_list"]) == 3
        assert 3 <= len(plan["hashtags"]) <= 6
        assert len(plan["review_before_use"]) == 3
        assert "job_id" not in response.text
        assert "output_url" not in response.text

        repeated = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload)
        assert repeated.status_code == 200
        assert repeated.json()["data"]["plan"] == plan
        changed = client.post(path, headers={"X-CSRF-Token": csrf}, json={**payload, "style": "cinematic"})
        assert changed.status_code == 200
        assert changed.json()["data"]["plan"]["primary_prompt"] != plan["primary_prompt"]

        malformed = client.post(path, headers={"X-CSRF-Token": csrf}, json={**payload, "platform": "unknown", "provider_url": "https://invalid.example"})
        assert malformed.status_code == 422
        secret = client.post(path, headers={"X-CSRF-Token": csrf}, json={**payload, "topic": "api_key=super-secret-token-value-12345"})
        assert secret.status_code == 422
        guarded = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json={**payload, "topic": "Làm video theo phong cách của một ca sĩ cụ thể"},
        )
        assert guarded.status_code == 200
        assert guarded.json()["ok"] is False
        assert guarded.json()["status"] == "guarded"
        assert guarded.json()["error_code"] == "WEB_CONTEXTUAL_AD_PROMPT_ORIGINALITY_GUARD"
        assert "plan" not in guarded.json().get("data", {})
        for key in (
            "input_persisted", "provider_called", "bot_called", "job_created", "wallet_mutated", "payment_started",
            "asset_saved", "media_output_created", "publish_action_created", "fact_checked", "rights_verified",
        ):
            assert guarded.json()["data"][key] is False

        oversized = client.post(path, headers={"X-CSRF-Token": csrf}, json={**payload, "topic": "x" * (129 * 1024)})
        assert oversized.status_code == 413
        assert oversized.json()["error_code"] == "WEB_CONTENT_STUDIO_BODY_TOO_LARGE"
        assert oversized.headers["Cache-Control"] == "no-store, private"
        assert prompt_pack_storage_counts(db_path) == before


def test_publish_review_pack_is_session_csrf_bounded_and_non_persistent(tmp_path, monkeypatch):
    """The Bot's last-result formatter is a signed, explicit Web-only review draft."""

    db_path = tmp_path / "content-studio-test.db"
    path = "/api/v1/content-studio/tools/publish-review-pack"
    payload = {
        "title": "Bộ dụng cụ pha cà phê cho người mới",
        "caption": "Bắt đầu pha cà phê tại nhà bằng một quy trình gọn, sau đó tự kiểm tra thông tin phù hợp trước khi đăng.",
        "hashtags": ["#CaPheMoi", "CreatorTips"],
        "cta": "",
        "source_prompt": "Nêu ngữ cảnh sử dụng thật, lợi ích cần kiểm chứng và CTA nhẹ.",
    }
    boundary_keys = (
        "input_persisted", "provider_called", "bot_called", "job_created", "wallet_mutated", "payment_started",
        "asset_saved", "media_output_created", "publish_action_created", "delivery_created", "fact_checked",
        "rights_verified",
    )
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(path, json=payload).status_code == 401
        csrf = register_and_login(client, "publish-review-pack@example.com")
        before = prompt_pack_storage_counts(db_path)

        assert client.post(path, json=payload).status_code == 403
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload)
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store, private"
        body = response.json()
        assert body["ok"] is True
        assert body["status"] == "draft"
        data = body["data"]
        assert set(data) == {"package", "execution", *boundary_keys}
        assert data["execution"] == "web_native_publish_review_text_only"
        for key in boundary_keys:
            assert data[key] is False
        package = data["package"]
        assert set(package) == {
            "title", "caption", "hashtags", "cta", "source_prompt", "review_checklist", "copy_instruction",
        }
        assert package["title"] == payload["title"]
        assert package["caption"] == payload["caption"]
        assert package["hashtags"] == ["#CaPheMoi", "#CreatorTips"]
        assert package["cta"] == "Xem thêm thông tin phù hợp trước khi quyết định."
        assert package["source_prompt"] == payload["source_prompt"]
        assert len(package["review_checklist"]) == 4
        assert "không kết nối tài khoản social" in package["copy_instruction"].lower()
        assert "job_id" not in response.text
        assert "output_url" not in response.text

        # The formatter is deterministic and never creates an authored record,
        # receipt, audit detail, job, asset, payment or publish action.
        repeated = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload)
        assert repeated.status_code == 200
        assert repeated.json()["data"]["package"] == package
        assert prompt_pack_storage_counts(db_path) == before

        malformed = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json={**payload, "provider_url": "https://invalid.example"},
        )
        assert malformed.status_code == 422
        invalid_hashtag = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json={**payload, "hashtags": ["not valid!"]},
        )
        assert invalid_hashtag.status_code == 422
        secret = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json={**payload, "caption": "api_key=super-secret-token-value-12345"},
        )
        assert secret.status_code == 422

        guarded = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json={**payload, "caption": "Viết caption theo phong cách của một ca sĩ cụ thể"},
        )
        assert guarded.status_code == 200
        guarded_body = guarded.json()
        assert guarded_body["ok"] is False
        assert guarded_body["status"] == "guarded"
        assert guarded_body["error_code"] == "WEB_PUBLISH_REVIEW_ORIGINALITY_GUARD"
        assert "package" not in guarded_body.get("data", {})
        assert guarded_body["data"]["execution"] == "web_native_publish_review_text_only"
        for key in boundary_keys:
            assert guarded_body["data"][key] is False

        oversized = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json={**payload, "caption": "x" * (129 * 1024)},
        )
        assert oversized.status_code == 413
        assert oversized.json()["error_code"] == "WEB_CONTENT_STUDIO_BODY_TOO_LARGE"
        assert oversized.headers["Cache-Control"] == "no-store, private"
        assert prompt_pack_storage_counts(db_path) == before


def test_content_studio_requires_session_csrf_and_keeps_idempotency_receipts_content_free(tmp_path, monkeypatch):
    db_path = tmp_path / "content-studio-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.get("/api/v1/content-studio/summary").status_code == 401
        csrf = register_and_login(client, "content-owner@example.com")
        raw = brief_payload("content-studio-create-0001")

        denied = client.post("/api/v1/content-studio/briefs", json=raw)
        assert denied.status_code == 403

        oversized = client.post(
            "/api/v1/content-studio/briefs",
            headers={"X-CSRF-Token": csrf},
            json={"title": "x" * (129 * 1024)},
        )
        assert oversized.status_code == 413
        assert oversized.json()["error_code"] == "WEB_CONTENT_STUDIO_BODY_TOO_LARGE"
        assert oversized.headers["cache-control"] == "no-store, private"
        assert client.get("/api/v1/content-studio/summary").json()["data"]["briefs"]["total"] == 0

        created = client.post("/api/v1/content-studio/briefs", headers={"X-CSRF-Token": csrf}, json=raw)
        assert created.status_code == 200
        assert created.json()["status"] == "draft"
        brief_id = created.json()["data"]["brief"]["id"]
        assert raw["brief_text"] not in created.text
        assert raw["title"] not in created.text

        replay = client.post("/api/v1/content-studio/briefs", headers={"X-CSRF-Token": csrf}, json=raw)
        assert replay.status_code == 200
        assert replay.json() == created.json()
        collision = client.post(
            "/api/v1/content-studio/briefs",
            headers={"X-CSRF-Token": csrf},
            json=brief_payload("content-studio-create-0001", title="Brief khác"),
        )
        assert collision.status_code == 409

        detail = client.get(f"/api/v1/content-studio/briefs/{brief_id}")
        assert detail.status_code == 200
        assert detail.json()["data"]["brief"]["brief_text"] == raw["brief_text"]
        with sqlite3.connect(db_path) as conn:
            receipts = conn.execute("SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-content-studio:%'").fetchall()
        assert receipts
        assert all(raw["brief_text"] not in str(row[0]) for row in receipts)
        assert all(raw["title"] not in str(row[0]) for row in receipts)


def test_content_brief_listing_is_paginated_filtered_and_owner_scoped(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as owner:
        csrf = register_and_login(owner, "content-pages-owner@example.com")
        created = [
            create_brief(
                owner,
                csrf,
                f"content-pages-create-{index:04d}",
                title=f"Pagination content brief {index}",
                content_kind="hook_script",
                tags=["pages", "private"],
            )
            for index in range(3)
        ]

        first = owner.get("/api/v1/content-studio/briefs", params={"q": "Pagination content brief", "limit": 1})
        assert first.status_code == 200
        first_data = first.json()["data"]
        assert first_data["filters"] == {"q": "Pagination content brief", "tag": "", "content_kind": "", "state": "active"}
        assert first_data["pagination"] == {"limit": 1, "offset": 0, "returned": 1}
        assert first_data["has_more"] is True
        assert first_data["next_offset"] == 1

        second = owner.get("/api/v1/content-studio/briefs", params={"q": "Pagination content brief", "limit": 1, "offset": 1})
        second_data = second.json()["data"]
        assert second_data["pagination"] == {"limit": 1, "offset": 1, "returned": 1}
        assert second_data["has_more"] is True
        assert second_data["next_offset"] == 2
        assert first_data["items"][0]["id"] != second_data["items"][0]["id"]

        third = owner.get("/api/v1/content-studio/briefs", params={"q": "Pagination content brief", "limit": 1, "offset": 2})
        third_data = third.json()["data"]
        assert third_data["pagination"] == {"limit": 1, "offset": 2, "returned": 1}
        assert third_data["has_more"] is False
        assert third_data["next_offset"] is None
        assert {item["id"] for item in first_data["items"] + second_data["items"] + third_data["items"]} == {item["id"] for item in created}

        filtered = owner.get("/api/v1/content-studio/briefs", params={"content_kind": "hook_script", "tag": "pages"})
        assert {item["id"] for item in filtered.json()["data"]["items"]} == {item["id"] for item in created}

        with make_client(tmp_path, monkeypatch) as other:
            csrf_other = register_and_login(other, "content-pages-other@example.com")
            foreign = create_brief(
                other,
                csrf_other,
                "content-pages-other-create-0001",
                title="Pagination content brief foreign",
                content_kind="hook_script",
                tags=["pages"],
            )
            visible_to_owner = owner.get("/api/v1/content-studio/briefs", params={"q": "Pagination content brief", "state": "all"})
            assert foreign["id"] not in {item["id"] for item in visible_to_owner.json()["data"]["items"]}


def test_content_studio_keeps_references_and_content_pieces_owner_scoped(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as first:
        csrf = register_and_login(first, "content-first@example.com")
        brief = create_brief(first, csrf, "content-first-create-0001")

        invalid_ref = first.post(
            "/api/v1/content-studio/briefs",
            headers={"X-CSRF-Token": csrf},
            json=brief_payload("content-invalid-reference-0001", project_id="1dcca218-d5a0-4c6a-9a62-3dd630db6a67"),
        )
        assert invalid_ref.status_code == 422

        secret = first.post(
            "/api/v1/content-studio/briefs",
            headers={"X-CSRF-Token": csrf},
            json=brief_payload("content-secret-brief-0001", brief_text="api_key=super-secret-token-value-12345"),
        )
        assert secret.status_code == 422

        composed = first.post(
            f"/api/v1/content-studio/briefs/{brief['id']}/compose",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": brief["revision"], "idempotency_key": "content-compose-local-0001"},
        )
        assert composed.status_code == 200
        data = composed.json()["data"]
        assert data["execution"] == "local_deterministic_draft_only"
        assert data["provider_called"] is False
        assert data["charge_started"] is False
        assert len(data["variant_ids"]) == 3
        assert "job_id" not in composed.text
        assert "output_url" not in composed.text

        detail = first.get(f"/api/v1/content-studio/briefs/{brief['id']}")
        variants = detail.json()["data"]["variants"]
        assert len(variants) == 3
        assert all(item["source_kind"] == "local_deterministic_draft_only" for item in variants)

        with make_client(tmp_path, monkeypatch) as second:
            csrf_second = register_and_login(second, "content-second@example.com")
            hidden = second.get(f"/api/v1/content-studio/briefs/{brief['id']}")
            assert hidden.status_code == 200
            assert hidden.json()["error_code"] == "WEB_CONTENT_BRIEF_NOT_FOUND"
            assert brief["brief_text"] not in hidden.text
            blocked = second.post(
                f"/api/v1/content-studio/briefs/{brief['id']}/compose",
                headers={"X-CSRF-Token": csrf_second},
                json={"expected_revision": brief["revision"], "idempotency_key": "content-cross-owner-compose-0001"},
            )
            assert blocked.status_code == 200
            assert blocked.json()["error_code"] == "WEB_CONTENT_BRIEF_NOT_FOUND"


def test_content_studio_variant_revision_selection_and_archive_are_safe(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "content-variant@example.com")
        brief = create_brief(client, csrf, "content-variant-brief-0001", content_kind="hook_script")
        created = client.post(
            f"/api/v1/content-studio/briefs/{brief['id']}/variants",
            headers={"X-CSRF-Token": csrf},
            json={
                "kind": "hook",
                "title": "Hook có kiểm tra",
                "content_text": "Một câu mở đầu được người dùng tự viết và sẽ được kiểm tra trước khi dùng.",
                "note": "",
                "tags": ["review"],
                "expected_revision": brief["revision"],
                "idempotency_key": "content-variant-create-0001",
            },
        )
        assert created.status_code == 200
        variant_id = created.json()["data"]["variant"]["id"]
        detail = client.get(f"/api/v1/content-studio/briefs/{brief['id']}")
        variant = next(item for item in detail.json()["data"]["variants"] if item["id"] == variant_id)
        selected = client.post(
            f"/api/v1/content-studio/briefs/{brief['id']}/select-variant",
            headers={"X-CSRF-Token": csrf},
            json={"variant_id": variant_id, "expected_revision": brief["revision"], "idempotency_key": "content-select-variant-0001"},
        )
        assert selected.status_code == 200
        current_revision = selected.json()["data"]["brief"]["revision"]
        archived = client.post(
            f"/api/v1/content-studio/briefs/{brief['id']}/variants/{variant_id}/archive",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": variant["revision"], "idempotency_key": "content-archive-variant-0001"},
        )
        assert archived.status_code == 200
        current = client.get(f"/api/v1/content-studio/briefs/{brief['id']}").json()["data"]["brief"]
        assert current["selected_variant_id"] is None
        stale = client.post(
            f"/api/v1/content-studio/briefs/{brief['id']}/select-variant",
            headers={"X-CSRF-Token": csrf},
            json={"variant_id": variant_id, "expected_revision": current_revision, "idempotency_key": "content-select-archived-0001"},
        )
        assert stale.status_code == 200
        assert stale.json()["error_code"] in {"WEB_CONTENT_REVISION_CONFLICT", "WEB_CONTENT_VARIANT_NOT_FOUND"}
