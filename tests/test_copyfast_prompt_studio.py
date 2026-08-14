"""Focused safety and API contracts for the Web-native Prompt Studio."""

from __future__ import annotations

import importlib
import json
import sqlite3
import sys

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry", "copyfast_api",
    "copyfast_pages", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations",
    "copyfast_image_studio", "copyfast_memory", "copyfast_prompt_library", "copyfast_prompt_studio",
    "copyfast_music_media", "copyfast_content_studio", "copyfast_trend_research", "copyfast_voice_studio",
    "copyfast_video_studio", "copyfast_subtitle_workspace", "copyfast_support",
]

BOUNDARY_FIELDS = (
    "execution", "input_persisted", "template_persisted", "bot_called", "bridge_called",
    "provider_called", "job_created", "wallet_mutated", "payment_started", "asset_saved",
    "media_output_created", "publish_action_created", "delivery_created", "fact_checked", "rights_verified",
)


def make_client(tmp_path, monkeypatch, *, enabled: bool = True, prompt_library_enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "prompt-studio-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "prompt-studio-test-session-secret")
    monkeypatch.setenv("WEBAPP_PROMPT_STUDIO_ENABLED", "true" if enabled else "false")
    monkeypatch.setenv("WEBAPP_PROMPT_LIBRARY_ENABLED", "true" if prompt_library_enabled else "false")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Prompt Editor"},
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
        "goal": "Giải thích lợi ích của bình nước giữ nhiệt cho người mới đi làm",
        "audience": "Người đi làm mới cần giữ đồ uống nóng hoặc lạnh",
        "platform": "social",
        "tone": "professional",
        "language": "vi",
        "output_format": "caption",
        "constraints": "Không nêu giá hoặc claim chưa kiểm tra",
    }
    value.update(overrides)
    return value


def save_payload(key: str, **overrides) -> dict:
    value = {**payload(), "confirmed": True, "idempotency_key": key}
    value.update(overrides)
    return value


def storage_counts(db_path) -> dict[str, int]:
    with sqlite3.connect(db_path) as conn:
        return {
            table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in ("web_idempotency", "web_audit_events", "web_prompt_templates", "web_prompt_template_versions")
        }


def assert_boundary(data: dict) -> None:
    assert data["execution"] == "web_native_deterministic_prompt_blueprint_only"
    for field in BOUNDARY_FIELDS:
        if field != "execution":
            assert data[field] is False


def test_policy_is_signed_no_store_and_exposes_only_static_allowlists(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        assert client.get("/api/v1/prompt-studio/policy").status_code == 401
        login(client, "prompt-policy@example.com")
        response = client.get("/api/v1/prompt-studio/policy")
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store, private"
        body = response.json()
        assert body["ok"] is True
        assert body["status"] == "ready"
        data = body["data"]
        assert set(data) == {"feature", "platforms", "tones", "languages", "output_formats", *BOUNDARY_FIELDS}
        assert data["feature"] == "prompt_blueprint_composer"
        assert data["platforms"] == ["chat", "document", "email", "general", "image", "social", "video", "voice", "website"]
        assert data["tones"] == ["clear", "creative", "educational", "friendly", "neutral", "persuasive", "professional"]
        assert data["languages"] == ["en", "vi"]
        assert data["output_formats"] == ["caption", "content", "document_outline", "general", "image_prompt", "script", "video_prompt", "voice_script"]
        assert_boundary(data)


def test_compose_requires_csrf_is_deterministic_and_never_persists(tmp_path, monkeypatch):
    path = "/api/v1/prompt-studio/compose"
    db_path = tmp_path / "prompt-studio-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(path, json=payload()).status_code == 401
        csrf = login(client, "prompt-compose@example.com")
        before = storage_counts(db_path)
        assert client.post(path, json=payload()).status_code == 403

        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload())
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store, private"
        body = response.json()
        assert body["ok"] is True
        assert body["status"] == "draft"
        data = body["data"]
        assert set(data) == {"brief", "blueprint", *BOUNDARY_FIELDS}
        assert_boundary(data)
        assert data["brief"] == payload()
        blueprint = data["blueprint"]
        assert set(blueprint) == {
            "title", "goal", "audience", "platform", "tone", "language", "output_format",
            "prompt_text", "negative_prompt", "variables", "review_checklist",
        }
        assert blueprint["goal"] == payload()["goal"]
        assert blueprint["audience"] == payload()["audience"]
        assert blueprint["platform"] == "social"
        assert blueprint["tone"] == "professional"
        assert blueprint["language"] == "vi"
        assert blueprint["output_format"] == "caption"
        assert payload()["goal"] in blueprint["prompt_text"]
        assert payload()["constraints"] in blueprint["prompt_text"]
        assert [item["name"] for item in blueprint["variables"]] == ["goal", "audience", "constraints", "facts_to_verify"]
        assert len(blueprint["review_checklist"]) == 4
        assert "job_id" not in response.text
        assert "output_url" not in response.text
        assert "provider" not in blueprint["prompt_text"].lower()
        assert storage_counts(db_path) == before

        replay = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload())
        assert replay.status_code == 200
        assert replay.json()["data"] == data
        assert storage_counts(db_path) == before


def test_compose_rejects_unsafe_inputs_and_returns_honest_policy_guard(tmp_path, monkeypatch):
    path = "/api/v1/prompt-studio/compose"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "prompt-safety@example.com")
        for invalid in (
            payload(goal="x"),
            payload(goal="x" * 301),
            payload(goal="two\nlines"),
            payload(goal="https://untrusted.invalid/brief"),
            payload(goal="<img src=x onerror=alert(1)>"),
            payload(goal="api_key=super-secret-token-value-12345"),
            payload(goal=42),
            payload(platform="metaverse"),
            payload(tone="aggressive"),
            payload(language="fr"),
            payload(output_format="podcast"),
            {**payload(), "provider_url": "https://provider.invalid"},
        ):
            assert client.post(path, headers={"X-CSRF-Token": csrf}, json=invalid).status_code == 422

        guarded = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload(goal="tạo deepfake của người thật"))
        assert guarded.status_code == 200
        body = guarded.json()
        assert body["ok"] is False
        assert body["status"] == "guarded"
        assert body["error_code"] == "WEB_PROMPT_STUDIO_POLICY_GUARD"
        assert "blueprint" not in body["data"]
        assert_boundary(body["data"])


def test_compose_supports_english_and_feature_flag_fails_closed(tmp_path, monkeypatch):
    path = "/api/v1/prompt-studio/compose"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "prompt-en@example.com")
        response = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json=payload(goal="Explain the benefits of an insulated bottle", audience="busy office workers", language="en", output_format="script"),
        )
        assert response.status_code == 200
        blueprint = response.json()["data"]["blueprint"]
        assert blueprint["language"] == "en"
        assert "Act as an editorial assistant." in blueprint["prompt_text"]
        assert "Do not invent prices" in blueprint["negative_prompt"]

    with make_client(tmp_path, monkeypatch, enabled=False) as disabled:
        csrf = login(disabled, "prompt-disabled@example.com")
        response = disabled.post(path, headers={"X-CSRF-Token": csrf}, json=payload())
        assert response.status_code == 503
        assert "WEBAPP_PROMPT_STUDIO_ENABLED" in response.json()["message"]


def test_compose_raw_body_cap_is_no_store_and_keeps_prompt_boundary(tmp_path, monkeypatch):
    path = "/api/v1/prompt-studio/compose"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "prompt-body-cap@example.com")
        oversized = payload(constraints="x" * (17 * 1024))
        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=oversized)
        assert response.status_code == 413
        assert response.headers["Cache-Control"] == "no-store, private"
        body = response.json()
        assert body["status"] == "guarded"
        assert body["error_code"] == "WEB_PROMPT_STUDIO_BODY_TOO_LARGE"
        assert_boundary(body["data"])


def test_prompt_studio_engine_descriptor_needs_its_own_maintenance_flag():
    from copyfast_web_engine import ENGINE_MODE_WEB_NATIVE, engine_descriptor

    assert engine_descriptor("prompt_studio", {}) == {
        "mode": ENGINE_MODE_WEB_NATIVE,
        "execution_state": "guarded",
    }
    assert engine_descriptor("prompt_studio", {"prompt_studio_enabled": True}) == {
        "mode": ENGINE_MODE_WEB_NATIVE,
        "execution_state": "ready",
    }


def test_save_to_library_requires_session_csrf_explicit_confirmation_and_only_a_brief(tmp_path, monkeypatch):
    path = "/api/v1/prompt-studio/save-to-library"
    with make_client(tmp_path, monkeypatch) as client:
        first = save_payload("prompt-studio-save-schema-0001")
        assert client.post(path, json=first).status_code == 401

        csrf = login(client, "prompt-save-schema@example.com")
        assert client.post(path, json=first).status_code == 403
        assert client.post(path, headers={"X-CSRF-Token": csrf}, json=save_payload("prompt-studio-save-confirm-0001", confirmed=False)).status_code == 422

        for field, value in (
            ("blueprint", {"prompt_text": "browser-controlled body"}),
            ("template_id", "00000000-0000-4000-8000-000000000001"),
            ("url", "https://untrusted.invalid/template"),
            ("asset_id", "00000000-0000-4000-8000-000000000002"),
            ("provider", "external"),
            ("job_id", "job-browser-controlled"),
            ("wallet", "browser"),
            ("payment", "browser"),
            ("result", {"state": "completed"}),
            ("state", "completed"),
        ):
            rejected = client.post(
                path,
                headers={"X-CSRF-Token": csrf},
                json=save_payload(f"prompt-studio-save-extra-{field}-0001", **{field: value}),
            )
            assert rejected.status_code == 422, field

    with make_client(tmp_path, monkeypatch, enabled=False) as disabled_studio:
        csrf = login(disabled_studio, "prompt-save-studio-disabled@example.com")
        assert disabled_studio.post(path, headers={"X-CSRF-Token": csrf}, json=save_payload("prompt-studio-save-studio-disabled-0001")).status_code == 503

    with make_client(tmp_path, monkeypatch, prompt_library_enabled=False) as disabled_library:
        csrf = login(disabled_library, "prompt-save-library-disabled@example.com")
        assert disabled_library.post(path, headers={"X-CSRF-Token": csrf}, json=save_payload("prompt-studio-save-library-disabled-0001")).status_code == 503
        assert disabled_library.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json=save_payload("prompt-studio-save-library-disabled-guarded-0001", goal="tạo deepfake của người thật"),
        ).status_code == 503


def test_save_to_library_recomputes_the_brief_and_never_persists_a_guarded_blueprint(tmp_path, monkeypatch):
    path = "/api/v1/prompt-studio/save-to-library"
    db_path = tmp_path / "prompt-studio-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "prompt-save-recompute@example.com")
        before = storage_counts(db_path)
        guarded = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json=save_payload("prompt-studio-save-guarded-0001", goal="tạo deepfake của người thật"),
        )
        assert guarded.status_code == 200
        assert guarded.json()["error_code"] == "WEB_PROMPT_STUDIO_POLICY_GUARD"
        assert guarded.json()["data"]["template_persisted"] is False
        assert storage_counts(db_path) == before

        saved = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json=save_payload("prompt-studio-save-recompute-0001"),
        )
        assert saved.status_code == 200
        body = saved.json()
        assert body["ok"] is True
        assert body["status"] == "completed"
        receipt = body["data"]
        assert receipt["destination"] == "prompt_library"
        assert receipt["execution"] == "web_native_prompt_studio_library_save"
        assert receipt["blueprint_recomputed_on_server"] is True
        assert receipt["template_persisted"] is True
        assert set(receipt["template"]) == {"id", "category", "state", "revision"}
        receipt_json = json.dumps(receipt, ensure_ascii=False)
        for raw_brief_field in (
            "title", "goal", "audience", "platform", "tone", "language", "output_format", "constraints",
        ):
            assert raw_brief_field not in receipt["template"]
            assert f'"{raw_brief_field}"' not in receipt_json
        assert payload()["goal"] not in json.dumps(receipt, ensure_ascii=False)
        assert "prompt_text" not in receipt
        assert "negative_prompt" not in receipt
        assert "audit" not in receipt
        assert "actor" not in receipt
        assert "email" not in receipt
        for field in (
            "browser_blueprint_persisted", "bot_called", "bridge_called", "provider_called", "job_created",
            "wallet_mutated", "payment_started", "asset_saved", "media_output_created", "publish_action_created",
            "delivery_created",
        ):
            assert receipt[field] is False

        template_id = receipt["template"]["id"]
        detail = client.get(f"/api/v1/prompt-library/templates/{template_id}")
        assert detail.status_code == 200
        template = detail.json()["data"]["template"]
        assert template["title"] == f"Prompt Studio: {payload()['goal']}"
        assert template["platform"] == payload()["platform"]
        assert template["language"] == payload()["language"]
        assert template["prompt_text"] == client.post(
            "/api/v1/prompt-studio/compose", headers={"X-CSRF-Token": csrf}, json=payload()
        ).json()["data"]["blueprint"]["prompt_text"]
        assert template["negative_prompt"] == client.post(
            "/api/v1/prompt-studio/compose", headers={"X-CSRF-Token": csrf}, json=payload()
        ).json()["data"]["blueprint"]["negative_prompt"]

        with sqlite3.connect(db_path) as conn:
            action, detail_text = conn.execute(
                "SELECT action, detail FROM web_audit_events WHERE target=?", (template_id,)
            ).fetchone()
            assert action == "web.prompt_library.prompt_studio_save"
            assert payload()["goal"] not in detail_text
            assert "prompt_text" not in detail_text


def test_save_to_library_idempotency_receipt_drops_raw_brief_content(tmp_path, monkeypatch):
    path = "/api/v1/prompt-studio/save-to-library"
    db_path = tmp_path / "prompt-studio-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "prompt-save-private-receipt@example.com")
        request = save_payload(
            "prompt-studio-save-private-receipt-0001",
            goal="Mục tiêu riêng tư không được lưu trong receipt",
            audience="Đối tượng riêng tư không được lưu trong receipt",
            platform="image",
            tone="creative",
            language="en",
            output_format="image_prompt",
            constraints="Ràng buộc riêng tư không được lưu trong receipt",
        )
        saved = client.post(path, headers={"X-CSRF-Token": csrf}, json=request)
        assert saved.status_code == 200
        receipt = saved.json()["data"]
        assert set(receipt["template"]) == {"id", "category", "state", "revision"}
        receipt_json = json.dumps(receipt, ensure_ascii=False)
        for raw_brief_field in (
            "title", "goal", "audience", "platform", "tone", "language", "output_format", "constraints",
        ):
            assert raw_brief_field not in receipt["template"]
            assert f'"{raw_brief_field}"' not in receipt_json

        with sqlite3.connect(db_path) as conn:
            stored_response = conn.execute(
                "SELECT response_json FROM web_idempotency WHERE key=?", (request["idempotency_key"],)
            ).fetchone()[0]
        stored_receipt = json.loads(stored_response)["data"]
        assert stored_receipt == receipt
        assert set(stored_receipt["template"]) == {"id", "category", "state", "revision"}
        for raw_brief_field in (
            "title", "goal", "audience", "platform", "tone", "language", "output_format", "constraints",
        ):
            assert raw_brief_field not in stored_receipt["template"]
            assert f'"{raw_brief_field}"' not in stored_response
        for raw_brief_content in (
            request["goal"], request["audience"], request["constraints"], f"Prompt Studio: {request['goal']}",
        ):
            assert raw_brief_content not in receipt_json
            assert raw_brief_content not in stored_response


def test_save_to_library_has_a_fixed_pre_db_write_rate_bucket(tmp_path, monkeypatch):
    path = "/api/v1/prompt-studio/save-to-library"
    with make_client(tmp_path, monkeypatch) as client:
        app_module = sys.modules["app"]
        app_module._auth_rate_windows.clear()
        request = save_payload("prompt-studio-save-rate-0001")
        for _ in range(40):
            assert client.post(path, json=request).status_code == 401
        assert client.post(path, json=request).status_code == 429
        keys = [key for key in app_module._auth_rate_windows if key.startswith("prompt-studio-save:")]
        assert len(keys) == 1
        assert len(app_module._auth_rate_windows[keys[0]]) == 40
        assert not [key for key in app_module._auth_rate_windows if key.startswith("prompt-library-write:")]
