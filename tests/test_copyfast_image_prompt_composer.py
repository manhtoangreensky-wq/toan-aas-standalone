"""Focused contracts for the Web-native Image Prompt Composer.

The Composer is deliberately a short-lived deterministic prompt planning
surface derived from the Telegram Bot's pure prompt helpers.  It must retain
the useful goal/style/ratio/variant behaviour without becoming an implicit
image operation, provider call, payment flow, asset write, job, or durable
Image Studio record.
"""

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
    "copyfast_content_studio", "copyfast_voice_studio", "copyfast_video_studio", "copyfast_subtitle_workspace",
    "copyfast_support",
]


def make_client(tmp_path, monkeypatch, *, enabled: bool = True, memory_enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "image-prompt-composer-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "image-prompt-composer-test-session-secret")
    monkeypatch.setenv("WEBAPP_IMAGE_STUDIO_ENABLED", "true" if enabled else "false")
    monkeypatch.setenv("WEBAPP_MEMORY_CENTER_ENABLED", "true" if memory_enabled else "false")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Prompt Planner"},
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def composer_payload(**overrides) -> dict:
    payload = {
        "goal_code": "product",
        "custom_goal": "",
        "subject": "Bình nước giữ nhiệt cho người đi làm",
        "style": "Studio sạch đẹp, ánh sáng mềm",
        "ratio": "9x16",
        "language": "vi",
    }
    payload.update(overrides)
    return payload


def composer_storage_counts(db_path) -> dict[str, int]:
    """Tables that a request-only composer must never mutate."""

    tables = (
        "web_image_artboards",
        "web_image_artboard_versions",
        "web_image_directions",
        "web_image_direction_versions",
        "web_image_studio_events",
        "web_image_operations",
        "web_image_operation_events",
        "web_memory_notes",
        "web_memory_note_versions",
        "web_memory_events",
        "web_idempotency",
        "web_audit_events",
    )
    with sqlite3.connect(db_path) as conn:
        return {
            table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in tables
        }


def test_image_prompt_composer_is_session_csrf_bounded_and_non_persistent(tmp_path, monkeypatch):
    """A Bot-like prompt draft must not secretly create an image workflow."""

    db_path = tmp_path / "image-prompt-composer-test.db"
    path = "/api/v1/image-studio/tools/prompt-composer"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(path, json=composer_payload()).status_code == 401
        csrf = login(client, "image-prompt-composer@example.com")
        before = composer_storage_counts(db_path)

        denied = client.post(path, json=composer_payload())
        assert denied.status_code == 403

        response = client.post(path, headers={"X-CSRF-Token": csrf}, json=composer_payload())
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store, private"
        body = response.json()
        assert body["ok"] is True
        assert body["status"] == "draft"
        data = body["data"]
        assert set(data) == {
            "composer",
            "execution",
            "input_persisted",
            "source_image_inspected",
            "provider_called",
            "image_created",
            "output_created",
            "job_created",
            "payment_started",
            "wallet_mutated",
            "asset_saved",
            "publish_action_created",
            "fact_checked",
            "rights_verified",
        }
        assert data["execution"] == "web_native_deterministic_prompt_only"
        for key in (
            "input_persisted",
            "source_image_inspected",
            "provider_called",
            "image_created",
            "output_created",
            "job_created",
            "payment_started",
            "wallet_mutated",
            "asset_saved",
            "publish_action_created",
            "fact_checked",
            "rights_verified",
        ):
            assert data[key] is False

        composer = data["composer"]
        assert set(composer) == {
            "title",
            "goal_code",
            "goal_label",
            "custom_goal",
            "subject",
            "style",
            "ratio",
            "language",
            "short_prompt",
            "detailed_prompt",
            "negative_prompt",
            "variants",
            "review_before_use",
        }
        assert composer["goal_code"] == "product"
        assert composer["subject"] == "Bình nước giữ nhiệt cho người đi làm"
        assert composer["style"] == "Studio sạch đẹp, ánh sáng mềm"
        assert composer["ratio"] == "9:16"
        assert composer["language"] == "vi"
        assert all(isinstance(composer[key], str) and composer[key].strip() for key in ("title", "goal_label", "short_prompt", "detailed_prompt", "negative_prompt"))
        assert isinstance(composer["variants"], list) and len(composer["variants"]) == 3
        assert all(isinstance(item, str) and item.strip() for item in composer["variants"])
        assert isinstance(composer["review_before_use"], list) and composer["review_before_use"]
        assert "job_id" not in response.text
        assert "output_url" not in response.text

        # The deterministic tool accepts Bot-compatible aliases but always
        # returns a canonical ratio.  It has no silent fallback for unknown
        # ratio input in the Web contract.
        aliases = {
            "vuông": "1:1",
            "reels": "9:16",
            "youtube": "16:9",
            "4 × 5": "4:5",
            "portrait": "3:4",
            "slide": "4:3",
            "landscape": "3:2",
            "21x9": "21:9",
        }
        for supplied, expected in aliases.items():
            generated = client.post(path, headers={"X-CSRF-Token": csrf}, json=composer_payload(ratio=supplied))
            assert generated.status_code == 200
            assert generated.json()["data"]["composer"]["ratio"] == expected

        custom = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json=composer_payload(goal_code="custom", custom_goal="Key visual ra mắt sản phẩm", ratio="1:1"),
        )
        assert custom.status_code == 200
        assert custom.json()["data"]["composer"]["goal_code"] == "custom"
        assert custom.json()["data"]["composer"]["custom_goal"] == "Key visual ra mắt sản phẩm"

        # No artboard, direction, Image Operations record, receipt or audit
        # detail may be created by a read-only composition request.
        assert composer_storage_counts(db_path) == before


def test_image_prompt_composer_rejects_schema_sensitive_input_and_guards_imitation(tmp_path, monkeypatch):
    path = "/api/v1/image-studio/tools/prompt-composer"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "image-prompt-policy@example.com")

        invalid_ratio = client.post(path, headers={"X-CSRF-Token": csrf}, json=composer_payload(ratio="5:7"))
        assert invalid_ratio.status_code == 422
        invalid_goal = client.post(path, headers={"X-CSRF-Token": csrf}, json=composer_payload(goal_code="not-a-goal"))
        assert invalid_goal.status_code == 422
        missing_custom_goal = client.post(path, headers={"X-CSRF-Token": csrf}, json=composer_payload(goal_code="custom", custom_goal=""))
        assert missing_custom_goal.status_code == 422
        short_custom_goal = client.post(path, headers={"X-CSRF-Token": csrf}, json=composer_payload(goal_code="custom", custom_goal="x"))
        assert short_custom_goal.status_code == 422
        short_style = client.post(path, headers={"X-CSRF-Token": csrf}, json=composer_payload(style="x"))
        assert short_style.status_code == 422
        extra = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json=composer_payload(provider_url="https://provider.invalid/private"),
        )
        assert extra.status_code == 422
        secret = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json=composer_payload(subject="api_key=super-secret-token-value-12345"),
        )
        assert secret.status_code == 422
        markup = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json=composer_payload(style="<img src=x onerror=alert(1)>"),
        )
        assert markup.status_code == 422

        guarded = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json=composer_payload(style="phong cách của một nghệ sĩ đương đại"),
        )
        assert guarded.status_code == 200
        assert guarded.json()["ok"] is False
        assert guarded.json()["status"] == "guarded"
        guarded_data = guarded.json().get("data", {})
        assert "composer" not in guarded_data
        assert guarded_data["execution"] == "web_native_deterministic_prompt_only"
        assert all(
            guarded_data[key] is False
            for key in (
                "input_persisted",
                "source_image_inspected",
                "provider_called",
                "image_created",
                "output_created",
                "job_created",
                "payment_started",
                "wallet_mutated",
                "asset_saved",
                "publish_action_created",
                "fact_checked",
                "rights_verified",
            )
        )

        oversized = client.post(
            path,
            headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
            content=b'{"subject":"' + (b"x" * (129 * 1024)) + b'"}',
        )
        assert oversized.status_code == 413
        assert oversized.json()["error_code"] == "WEB_IMAGE_STUDIO_BODY_TOO_LARGE"
        assert oversized.headers["Cache-Control"] == "no-store, private"


def test_image_prompt_composer_memory_save_is_signed_recomputed_and_owner_scoped(tmp_path, monkeypatch):
    """A reviewed draft becomes one private Web note, never Bot/image state."""

    db_path = tmp_path / "image-prompt-composer-test.db"
    path = "/api/v1/image-studio/tools/prompt-composer/save"
    subject = "Đèn bàn chống chói cho góc làm việc tại nhà"
    payload = composer_payload(
        subject=subject,
        ratio="16:9",
        destination="memory_note",
        idempotency_key="image-prompt-composer-save-memory-0001",
    )
    boundary_keys = (
        "draft_recomputed_on_server",
        "web_note_persisted",
        "browser_result_persisted",
        "pending_bot_save_created",
        "telegram_state_changed",
        "bot_called",
        "bridge_called",
        "source_image_inspected",
        "provider_called",
        "image_created",
        "output_created",
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
        # Signed cookie and matching CSRF are both required before the durable
        # write parses an otherwise valid save request.
        assert client.post(path, json=payload).status_code == 401
        csrf = login(client, "image-prompt-composer-memory-owner@example.com")
        assert client.post(path, json=payload).status_code == 403
        before = composer_storage_counts(db_path)

        # The browser cannot inject a generated result, arbitrary memory body,
        # destination, or account into a deterministic server-side handoff.
        invalid_requests = (
            {key: value for key, value in payload.items() if key != "destination"},
            {**payload, "destination": "prompt_library"},
            {key: value for key, value in payload.items() if key != "idempotency_key"},
            {**payload, "content": "browser-authored text must never be stored"},
            {**payload, "title": "browser-authored note title must never be stored"},
            {**payload, "composer": {"detailed_prompt": "browser result must never be stored"}},
            {**payload, "account_id": "browser-selected-account"},
        )
        for invalid in invalid_requests:
            rejected = client.post(path, headers={"X-CSRF-Token": csrf}, json=invalid)
            assert rejected.status_code == 422
        assert composer_storage_counts(db_path) == before

        guarded = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json={**payload, "style": "phong cách của một nghệ sĩ đương đại"},
        )
        assert guarded.status_code == 200
        assert guarded.json()["ok"] is False
        assert guarded.json()["status"] == "guarded"
        assert guarded.json()["error_code"] == "WEB_IMAGE_PROMPT_ORIGINALITY_GUARD"
        assert guarded.json()["data"]["web_note_persisted"] is False
        assert composer_storage_counts(db_path) == before

        # The persisted content must equal a fresh server computation, but the
        # browser does not submit preview text as part of the save payload.
        preview = client.post(
            "/api/v1/image-studio/tools/prompt-composer",
            headers={"X-CSRF-Token": csrf},
            json=composer_payload(subject=subject, ratio="16:9"),
        )
        assert preview.status_code == 200
        expected = preview.json()["data"]["composer"]

        created = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload)
        assert created.status_code == 200
        assert created.headers["Cache-Control"] == "no-store, private"
        body = created.json()
        assert body["ok"] is True
        assert body["status"] == "completed"
        assert subject not in created.text
        data = body["data"]
        assert data["destination"] == "memory_note"
        assert data["execution"] == "web_native_memory_note_server_recomputed"
        assert data["note"] == {
            "id": data["note"]["id"],
            "revision": 1,
            "state": "active",
            "category": "Image Prompt Composer",
            "priority": "normal",
        }
        assert all(
            data[key] is (key in {"draft_recomputed_on_server", "web_note_persisted"})
            for key in boundary_keys
        )
        assert "job_id" not in created.text
        assert "output_url" not in created.text

        note_id = data["note"]["id"]
        detail = client.get(f"/api/v1/memory/notes/{note_id}")
        assert detail.status_code == 200
        saved_note = detail.json()["data"]["note"]
        assert saved_note["title"] == "Image Prompt Composer"
        assert saved_note["category"] == "Image Prompt Composer"
        assert saved_note["content"].startswith("Image Prompt Composer — bản nháp Web đã được dựng lại trên máy chủ.")
        assert f"Chủ thể: {subject}" in saved_note["content"]
        assert expected["short_prompt"] in saved_note["content"]
        assert expected["detailed_prompt"] in saved_note["content"]
        assert expected["negative_prompt"] in saved_note["content"]
        assert all(variant in saved_note["content"] for variant in expected["variants"])
        assert all(item in saved_note["content"] for item in expected["review_before_use"])

        after_create = composer_storage_counts(db_path)
        assert after_create["web_memory_notes"] == before["web_memory_notes"] + 1
        assert after_create["web_memory_note_versions"] == before["web_memory_note_versions"] + 1
        assert after_create["web_memory_events"] == before["web_memory_events"] + 1
        assert after_create["web_idempotency"] == before["web_idempotency"] + 1
        assert after_create["web_audit_events"] == before["web_audit_events"] + 1
        for table in (
            "web_image_artboards",
            "web_image_artboard_versions",
            "web_image_directions",
            "web_image_direction_versions",
            "web_image_studio_events",
            "web_image_operations",
            "web_image_operation_events",
        ):
            assert after_create[table] == before[table]

        # An idempotency replay and its audit projection must not retain the
        # private subject or a duplicate deterministic result outside Memory.
        with sqlite3.connect(db_path) as conn:
            receipt = conn.execute(
                "SELECT response_json, request_fingerprint FROM web_idempotency WHERE key=?",
                (payload["idempotency_key"],),
            ).fetchone()
            audit_rows = conn.execute(
                "SELECT action, target, detail FROM web_audit_events WHERE action=?",
                ("web.image_studio.prompt_composer.save_memory",),
            ).fetchall()
        assert receipt is not None
        assert subject not in str(receipt[0])
        assert subject not in str(receipt[1])
        assert audit_rows
        assert all(subject not in "\n".join(str(value or "") for value in row) for row in audit_rows)

        replay = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload)
        assert replay.status_code == 200
        assert replay.json() == body
        assert composer_storage_counts(db_path) == after_create

        # A reused key must not attach a second note to changed inputs.
        altered = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json={**payload, "subject": "Đèn cây đọc sách cho phòng khách"},
        )
        assert altered.status_code == 409
        assert composer_storage_counts(db_path) == after_create

        # A Memory note created from Image Studio retains owner-only reads.
        with make_client(tmp_path, monkeypatch) as other:
            other_csrf = login(other, "image-prompt-composer-memory-other@example.com")
            assert other_csrf
            hidden = other.get(f"/api/v1/memory/notes/{note_id}")
            assert hidden.status_code == 200
            assert hidden.json()["ok"] is False
            assert hidden.json()["error_code"] == "WEB_MEMORY_NOTE_NOT_FOUND"
            assert subject not in hidden.text


def test_image_prompt_composer_respects_the_existing_image_studio_maintenance_flag(tmp_path, monkeypatch):
    path = "/api/v1/image-studio/tools/prompt-composer"
    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        csrf = login(client, "image-prompt-disabled@example.com")
        guarded = client.post(path, headers={"X-CSRF-Token": csrf}, json=composer_payload())
        assert guarded.status_code == 503
        assert "WEBAPP_IMAGE_STUDIO_ENABLED" in guarded.text


def test_image_prompt_composer_memory_save_respects_memory_center_maintenance_flag(tmp_path, monkeypatch):
    path = "/api/v1/image-studio/tools/prompt-composer/save"
    with make_client(tmp_path, monkeypatch, memory_enabled=False) as client:
        csrf = login(client, "image-prompt-composer-memory-disabled@example.com")
        response = client.post(
            path,
            headers={"X-CSRF-Token": csrf},
            json=composer_payload(destination="memory_note", idempotency_key="image-prompt-memory-disabled-0001"),
        )
        assert response.status_code == 503
        assert "WEBAPP_MEMORY_CENTER_ENABLED" in response.text
