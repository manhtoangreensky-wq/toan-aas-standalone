"""Contract tests for the private, Web-native Prompt Library."""

from __future__ import annotations

import asyncio
import importlib
import json
import sqlite3
import sys

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_api", "copyfast_pages", "copyfast_projects", "copyfast_assets",
    "copyfast_project_packages", "copyfast_document_operations", "copyfast_image_runtime",
    "copyfast_image_operations", "copyfast_memory", "copyfast_support", "copyfast_free_prompt_gallery",
    "copyfast_prompt_library",
]


def make_client(tmp_path, monkeypatch, *, prompt_library_enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "copyfast-prompt-library-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-prompt-library-session-secret")
    monkeypatch.setenv("WEBAPP_PROMPT_LIBRARY_ENABLED", "true" if prompt_library_enabled else "false")
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def register_and_login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Prompt Owner"},
    )
    assert registered.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    return login.json()["data"]["csrf_token"]


def template_payload(key: str, **overrides) -> dict:
    payload = {
        "title": "Video ra mắt sản phẩm",
        "category": "Video product",
        "product_context": "video",
        "platform": "TikTok",
        "style": "Rõ ràng, giàu nhịp điệu",
        "language": "vi",
        "prompt_text": "Viết hook 3 giây cho {{product}} với lợi ích {{benefit}}.",
        "negative_prompt": "Không dùng cam kết tuyệt đối.",
        "variables": ["product", "benefit"],
        "tags": ["launch", "video"],
        "source": "Tự soạn trong TOAN AAS Web",
        "license_note": "Tôi có quyền sử dụng nội dung này.",
        "quality_score": 72,
        "idempotency_key": key,
    }
    payload.update(overrides)
    return payload


def create_template(client: TestClient, csrf: str, key: str = "prompt-template-create-0001", **overrides) -> dict:
    response = client.post(
        "/api/v1/prompt-library/templates",
        headers={"X-CSRF-Token": csrf},
        json=template_payload(key, **overrides),
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    return response.json()["data"]["template"]


def save_gallery_prompt(client: TestClient, csrf: str, prompt_id: str, key: str) -> dict:
    response = client.post(
        f"/api/v1/prompt-library/gallery-items/{prompt_id}/save",
        headers={"X-CSRF-Token": csrf},
        json={"idempotency_key": key},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    return response.json()["data"]


def test_gallery_seed_save_is_csrf_owned_server_resolved_deduplicated_and_audited(tmp_path, monkeypatch):
    prompt_id = "caption_cta_food_cafe_1"
    initial_key = "gallery-save-initial-0001"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(
            f"/api/v1/prompt-library/gallery-items/{prompt_id}/save",
            json={"idempotency_key": initial_key},
        ).status_code == 401
        csrf = register_and_login(client, "gallery-save-owner@example.com")
        no_csrf = client.post(
            f"/api/v1/prompt-library/gallery-items/{prompt_id}/save",
            json={"idempotency_key": initial_key},
        )
        assert no_csrf.status_code == 403
        assert client.post(
            "/api/v1/prompt-library/gallery-items/not-valid-id!/save",
            headers={"X-CSRF-Token": csrf},
            json={"idempotency_key": "gallery-save-invalid-id-0001"},
        ).status_code == 422
        assert client.post(
            "/api/v1/prompt-library/gallery-items/caption_cta_notreal_1/save",
            headers={"X-CSRF-Token": csrf},
            json={"idempotency_key": "gallery-save-missing-id-0001"},
        ).status_code == 404
        assert client.post(
            f"/api/v1/prompt-library/gallery-items/{prompt_id}/save",
            headers={"X-CSRF-Token": csrf},
            json={"idempotency_key": "gallery-save-extra-field-0001", "prompt_text": "browser must not control this"},
        ).status_code == 422

        saved = save_gallery_prompt(client, csrf, prompt_id, initial_key)
        template = saved["template"]
        assert saved["created"] is True
        assert saved["deduplicated"] is False
        assert saved["gallery"] == {"prompt_id": prompt_id, "snapshot_version": "2026-07-15.1"}
        assert "prompt_text" not in template
        assert saved["boundaries"] == {
            "execution": "web_native_prompt_library_gallery_save",
            "source_snapshot_read_only": True,
            "template_persisted": True,
            "gallery_state_persisted": False,
            "pending_bot_save_created": False,
            "telegram_state_changed": False,
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
        detail = client.get(f"/api/v1/prompt-library/templates/{template['id']}")
        assert detail.status_code == 200
        source = detail.json()["data"]["template"]
        assert source["prompt_text"].startswith("Viết caption ngắn cho món ăn hoặc đồ uống nổi bật")
        assert source["source"] == "TOAN AAS Web Free Prompt Gallery | snapshot 2026-07-15.1 | caption_cta_food_cafe_1"
        assert source["tags"] == ["free-prompt-gallery", "caption_cta", "food_cafe"]

        # The same retry returns the durable receipt. A fresh idempotency key
        # still reaches the owner-scoped Gallery map and cannot create a copy.
        replay = save_gallery_prompt(client, csrf, prompt_id, initial_key)
        assert replay["template"]["id"] == template["id"]
        assert replay["created"] is True
        deduplicated = save_gallery_prompt(client, csrf, prompt_id, "gallery-save-deduplicate-0001")
        assert deduplicated["template"]["id"] == template["id"]
        assert deduplicated["created"] is False
        assert deduplicated["deduplicated"] is True
        collision = client.post(
            "/api/v1/prompt-library/gallery-items/hook_script_food_cafe_1/save",
            headers={"X-CSRF-Token": csrf},
            json={"idempotency_key": initial_key},
        )
        assert collision.status_code == 409

        db_path = tmp_path / "copyfast-prompt-library-test.db"
        with sqlite3.connect(db_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_prompt_templates").fetchone()[0] == 1
            assert conn.execute(
                "SELECT gallery_prompt_id, snapshot_version, template_id FROM web_prompt_gallery_saves"
            ).fetchone() == (prompt_id, "2026-07-15.1", template["id"])
            assert conn.execute(
                "SELECT COUNT(*) FROM web_prompt_template_events WHERE template_id=? AND action='gallery_prompt_saved'",
                (template["id"],),
            ).fetchone()[0] == 1
            assert conn.execute(
                "SELECT COUNT(*) FROM web_audit_events WHERE target=? AND action='web.prompt_library.gallery_save'",
                (template["id"],),
            ).fetchone()[0] == 1

        # A normal archive/purge is still owner-controlled. Cascade removes
        # the provenance row so a later explicit save can intentionally start
        # a fresh private template rather than retaining a dangling map.
        archived = client.post(
            f"/api/v1/prompt-library/templates/{template['id']}/archive",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 1, "idempotency_key": "gallery-save-archive-0001"},
        )
        assert archived.json()["ok"] is True
        purged = client.post(
            f"/api/v1/prompt-library/templates/{template['id']}/purge",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 2, "confirm": True, "idempotency_key": "gallery-save-purge-0001"},
        )
        assert purged.json()["ok"] is True
        with sqlite3.connect(db_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_prompt_gallery_saves").fetchone()[0] == 0
        resaved = save_gallery_prompt(client, csrf, prompt_id, "gallery-save-after-purge-0001")
        assert resaved["created"] is True
        assert resaved["template"]["id"] != template["id"]

    # The mapping is account-scoped: a second signed account may save its own
    # private copy but cannot read the first account's template or map.
    with make_client(tmp_path, monkeypatch) as second:
        second_csrf = register_and_login(second, "gallery-save-other@example.com")
        other = save_gallery_prompt(second, second_csrf, prompt_id, "gallery-save-other-account-0001")
        assert other["template"]["id"] != resaved["template"]["id"]
        hidden = second.get(f"/api/v1/prompt-library/templates/{resaved['template']['id']}")
        assert hidden.json()["error_code"] == "WEB_PROMPT_TEMPLATE_NOT_FOUND"


def test_prompt_library_is_csrf_owned_versioned_and_private(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as first:
        csrf = register_and_login(first, "prompt-owner@example.com")
        raw = template_payload("prompt-template-create-0001")
        denied = first.post("/api/v1/prompt-library/templates", json=raw)
        assert denied.status_code == 403

        created = create_template(first, csrf)
        assert created["revision"] == 1
        assert "prompt_text" not in created
        replay = first.post("/api/v1/prompt-library/templates", headers={"X-CSRF-Token": csrf}, json=raw)
        assert replay.json()["data"]["template"]["id"] == created["id"]
        collision = first.post(
            "/api/v1/prompt-library/templates",
            headers={"X-CSRF-Token": csrf},
            json=template_payload("prompt-template-create-0001", title="Một template khác"),
        )
        assert collision.status_code == 409

        detail = first.get(f"/api/v1/prompt-library/templates/{created['id']}")
        assert detail.status_code == 200
        assert detail.json()["data"]["template"]["prompt_text"] == raw["prompt_text"]
        assert detail.json()["data"]["versions"][0]["revision"] == 1

        updated_payload = template_payload(
            "prompt-template-update-0001",
            title="Video ra mắt đã rà soát",
            prompt_text="Viết hook 3 giây cho {{product}} và nêu {{benefit}} rõ ràng.",
            expected_revision=1,
        )
        updated = first.patch(
            f"/api/v1/prompt-library/templates/{created['id']}",
            headers={"X-CSRF-Token": csrf},
            json=updated_payload,
        )
        assert updated.status_code == 200
        assert updated.json()["data"]["template"]["revision"] == 2
        conflict = first.patch(
            f"/api/v1/prompt-library/templates/{created['id']}",
            headers={"X-CSRF-Token": csrf},
            json=template_payload("prompt-template-conflict-0001", expected_revision=1),
        )
        assert conflict.json()["error_code"] == "WEB_PROMPT_TEMPLATE_CONFLICT"

        restored_version = first.post(
            f"/api/v1/prompt-library/templates/{created['id']}/restore-version",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 2, "revision": 1, "idempotency_key": "prompt-template-restore-v1-0001"},
        )
        assert restored_version.json()["data"]["template"]["revision"] == 3
        assert restored_version.json()["data"]["template"]["title"] == raw["title"]

        archived = first.post(
            f"/api/v1/prompt-library/templates/{created['id']}/archive",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 3, "idempotency_key": "prompt-template-archive-0001"},
        )
        assert archived.json()["data"]["template"]["state"] == "archived"
        restored = first.post(
            f"/api/v1/prompt-library/templates/{created['id']}/restore",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 4, "idempotency_key": "prompt-template-unarchive-0001"},
        )
        assert restored.json()["data"]["template"]["state"] == "active"

        duplicate = first.post(
            f"/api/v1/prompt-library/templates/{created['id']}/duplicate",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 5, "idempotency_key": "prompt-template-duplicate-0001"},
        )
        duplicate_template = duplicate.json()["data"]["template"]
        assert duplicate_template["id"] != created["id"]
        assert duplicate_template["revision"] == 1

        preview = first.post(
            f"/api/v1/prompt-library/templates/{duplicate_template['id']}/preview",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 1, "values": {"product": "Bình giữ nhiệt", "benefit": "giữ lạnh lâu"}},
        )
        assert preview.status_code == 200
        assert "Bình giữ nhiệt" in preview.json()["data"]["prompt_text"]
        assert preview.json()["data"]["execution"] == "local_preview_only"

        listing = first.get("/api/v1/prompt-library/templates", params={"state": "all", "q": "ra mắt"})
        assert listing.status_code == 200
        assert len(listing.json()["data"]["items"]) == 2
        events = first.get("/api/v1/prompt-library/events")
        assert events.status_code == 200
        assert all("prompt_text" not in item for item in events.json()["data"]["items"])

        with make_client(tmp_path, monkeypatch) as second:
            csrf_second = register_and_login(second, "prompt-other@example.com")
            hidden = second.get(f"/api/v1/prompt-library/templates/{created['id']}")
            assert hidden.status_code == 200
            assert hidden.json()["error_code"] == "WEB_PROMPT_TEMPLATE_NOT_FOUND"
            assert raw["prompt_text"] not in hidden.text
            denied_mutation = second.post(
                f"/api/v1/prompt-library/templates/{created['id']}/archive",
                headers={"X-CSRF-Token": csrf_second},
                json={"expected_revision": 5, "idempotency_key": "prompt-template-other-archive-0001"},
            )
            assert denied_mutation.json()["error_code"] == "WEB_PROMPT_TEMPLATE_NOT_FOUND"


def test_prompt_library_listing_is_paginated_filtered_and_owner_scoped(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as owner:
        csrf = register_and_login(owner, "prompt-library-pages@example.com")
        created = [
            create_template(
                owner,
                csrf,
                f"prompt-template-page-{index:04d}",
                title=f"Pagination template {index}",
                category="Library pagination",
                tags=["pages", "private"],
            )
            for index in range(3)
        ]

        first = owner.get("/api/v1/prompt-library/templates", params={"q": "Pagination template", "limit": 1})
        assert first.status_code == 200
        first_data = first.json()["data"]
        assert first_data["filters"] == {
            "q": "Pagination template",
            "category": "",
            "platform": "",
            "product_context": "",
            "tag": "",
            "state": "active",
        }
        assert first_data["pagination"] == {"limit": 1, "offset": 0, "returned": 1}
        assert first_data["has_more"] is True
        assert first_data["next_offset"] == 1

        second = owner.get("/api/v1/prompt-library/templates", params={"q": "Pagination template", "limit": 1, "offset": 1})
        assert second.status_code == 200
        second_data = second.json()["data"]
        assert second_data["pagination"] == {"limit": 1, "offset": 1, "returned": 1}
        assert second_data["has_more"] is True
        assert second_data["next_offset"] == 2
        assert first_data["items"][0]["id"] != second_data["items"][0]["id"]

        all_ids = {item["id"] for item in first_data["items"] + second_data["items"]}
        third = owner.get("/api/v1/prompt-library/templates", params={"q": "Pagination template", "limit": 1, "offset": 2})
        third_data = third.json()["data"]
        assert third_data["pagination"] == {"limit": 1, "offset": 2, "returned": 1}
        assert third_data["has_more"] is False
        assert third_data["next_offset"] is None
        all_ids.update(item["id"] for item in third_data["items"])
        assert all_ids == {item["id"] for item in created}

        filtered = owner.get("/api/v1/prompt-library/templates", params={"category": "Library pagination", "tag": "pages"})
        assert {item["id"] for item in filtered.json()["data"]["items"]} == {item["id"] for item in created}

        with make_client(tmp_path, monkeypatch) as other:
            other_csrf = register_and_login(other, "prompt-library-pages-other@example.com")
            foreign = create_template(
                other,
                other_csrf,
                "prompt-template-page-other-0001",
                title="Pagination template foreign",
                category="Library pagination",
                tags=["pages"],
            )
            visible_to_owner = owner.get("/api/v1/prompt-library/templates", params={"q": "Pagination template", "state": "all"})
            assert foreign["id"] not in {item["id"] for item in visible_to_owner.json()["data"]["items"]}


def test_prompt_library_rejects_sensitive_content_and_unknown_preview_values(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "prompt-sensitive@example.com")
        rejected_secret = client.post(
            "/api/v1/prompt-library/templates",
            headers={"X-CSRF-Token": csrf},
            json=template_payload("prompt-template-secret-0001", prompt_text="api_key=super-secret-token-value-12345"),
        )
        assert rejected_secret.status_code == 422
        rejected_quoted_secret = client.post(
            "/api/v1/prompt-library/templates",
            headers={"X-CSRF-Token": csrf},
            json=template_payload("prompt-template-secret-quoted-0001", prompt_text="token = 'arbitrary-secret-value-123'"),
        )
        assert rejected_quoted_secret.status_code == 422
        rejected_json_secret = client.post(
            "/api/v1/prompt-library/templates",
            headers={"X-CSRF-Token": csrf},
            json=template_payload("prompt-template-secret-json-0001", prompt_text='{"api_key":"arbitrary-secret-value-123"}'),
        )
        assert rejected_json_secret.status_code == 422
        rejected_aws_secret = client.post(
            "/api/v1/prompt-library/templates",
            headers={"X-CSRF-Token": csrf},
            json=template_payload("prompt-template-secret-aws-0001", prompt_text="AWS_SECRET_ACCESS_KEY=arbitrary-secret-value-123"),
        )
        assert rejected_aws_secret.status_code == 422
        rejected_basic_auth = client.post(
            "/api/v1/prompt-library/templates",
            headers={"X-CSRF-Token": csrf},
            json=template_payload("prompt-template-secret-basic-0001", prompt_text="Authorization: Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ=="),
        )
        assert rejected_basic_auth.status_code == 422
        rejected_private_key = client.post(
            "/api/v1/prompt-library/templates",
            headers={"X-CSRF-Token": csrf},
            json=template_payload(
                "prompt-template-secret-private-key-0001",
                prompt_text="-----BEGIN PRIVATE KEY-----\nnot-a-real-key-material\n-----END PRIVATE KEY-----",
            ),
        )
        assert rejected_private_key.status_code == 422
        rejected_control_character = client.post(
            "/api/v1/prompt-library/templates",
            headers={"X-CSRF-Token": csrf},
            json=template_payload(
                "prompt-template-control-character-0001",
                prompt_text="Nội dung không hợp lệ\x01",
            ),
        )
        assert rejected_control_character.status_code == 422
        rejected_payment = client.post(
            "/api/v1/prompt-library/templates",
            headers={"X-CSRF-Token": csrf},
            json=template_payload("prompt-template-payment-0001", license_note="Mã giao dịch: 123456"),
        )
        assert rejected_payment.status_code == 422
        created = create_template(client, csrf, "prompt-template-safe-0001")
        unknown_value = client.post(
            f"/api/v1/prompt-library/templates/{created['id']}/preview",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 1, "values": {"not_declared": "x"}},
        )
        assert unknown_value.status_code == 422
        wrong_account_shape = client.post(
            "/api/v1/prompt-library/templates",
            headers={"X-CSRF-Token": csrf},
            json={**template_payload("prompt-template-account-0001"), "account_id": "attacker"},
        )
        assert wrong_account_shape.status_code == 422
        reserved_variable = client.post(
            "/api/v1/prompt-library/templates",
            headers={"X-CSRF-Token": csrf},
            json=template_payload("prompt-template-reserved-variable-0001", variables=["__proto__"]),
        )
        assert reserved_variable.status_code == 422


def test_prompt_library_preview_has_a_bounded_rendered_output(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "prompt-preview-limit@example.com")
        created = create_template(
            client,
            csrf,
            "prompt-template-preview-limit-create-0001",
            variables=["item"],
            prompt_text="{{item}}" * 2000,
            negative_prompt="",
        )
        limited = client.post(
            f"/api/v1/prompt-library/templates/{created['id']}/preview",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 1, "values": {"item": "x" * 600}},
        )
        assert limited.status_code == 200
        assert limited.json()["ok"] is False
        assert limited.json()["error_code"] == "WEB_PROMPT_TEMPLATE_PREVIEW_LIMIT"


def test_prompt_library_preview_is_single_pass_and_never_reparses_a_variable_value(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "prompt-preview-single-pass@example.com")
        created = create_template(
            client,
            csrf,
            "prompt-template-preview-single-pass-create-0001",
            variables=["alpha", "beta"],
            prompt_text="A={{alpha}}; B={{beta}}",
            negative_prompt="",
        )
        preview = client.post(
            f"/api/v1/prompt-library/templates/{created['id']}/preview",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 1, "values": {"alpha": "{{beta}}", "beta": "resolved"}},
        )
        assert preview.json()["ok"] is True
        assert preview.json()["data"]["prompt_text"] == "A={{beta}}; B=resolved"


def test_prompt_library_archived_template_cannot_preview_until_restored(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "prompt-archived-preview@example.com")
        created = create_template(client, csrf, "prompt-template-archived-preview-create-0001")
        archived = client.post(
            f"/api/v1/prompt-library/templates/{created['id']}/archive",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 1, "idempotency_key": "prompt-template-archived-preview-archive-0001"},
        )
        assert archived.json()["data"]["template"]["state"] == "archived"
        preview = client.post(
            f"/api/v1/prompt-library/templates/{created['id']}/preview",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 2, "values": {"product": "Bình nước", "benefit": "giữ lạnh"}},
        )
        assert preview.status_code == 200
        assert preview.json()["ok"] is False
        assert preview.json()["error_code"] == "WEB_PROMPT_TEMPLATE_ARCHIVED"


def test_prompt_library_body_limiter_rejects_declared_and_chunked_bodies_before_router(tmp_path, monkeypatch):
    """Both Content-Length and chunked streams must yield the same envelope."""

    with make_client(tmp_path, monkeypatch) as client:
        app_module = sys.modules["app"]
        too_large = client.post(
            "/api/v1/prompt-library/templates",
            headers={
                "Content-Type": "application/json",
                "Origin": "https://app.toanaas.vn",
                "X-Request-ID": "prompt-body-limit-request",
            },
            content=b"x" * (app_module.PROMPT_LIBRARY_BODY_MAX_BYTES + 1),
        )
        assert too_large.status_code == 413
        assert too_large.json()["error_code"] == "WEB_PROMPT_LIBRARY_BODY_TOO_LARGE"
        assert too_large.headers["x-request-id"] == "prompt-body-limit-request"
        assert too_large.headers["access-control-allow-origin"] == "https://app.toanaas.vn"
        assert too_large.headers["access-control-allow-credentials"] == "true"

        async def invoke(scope, messages, *, limit=3):
            sent: list[dict] = []
            pending = list(messages)

            async def receive():
                return pending.pop(0) if pending else {"type": "http.disconnect"}

            async def send(message):
                sent.append(message)

            async def downstream(_scope, replay_receive, downstream_send):
                received = b""
                while True:
                    message = await replay_receive()
                    if message["type"] != "http.request":
                        break
                    received += message.get("body", b"")
                    if not message.get("more_body", False):
                        break
                await downstream_send({"type": "http.response.start", "status": 200, "headers": []})
                await downstream_send({"type": "http.response.body", "body": received})

            middleware = app_module.PromptLibraryBodyLimitMiddleware(downstream, max_bytes=limit, import_max_bytes=10)
            await middleware(scope, receive, send)
            return sent

        chunked_scope = {
            "type": "http", "method": "POST", "path": "/api/v1/prompt-library/templates", "headers": [],
        }
        chunked = asyncio.run(
            invoke(
                chunked_scope,
                [
                    {"type": "http.request", "body": b"ab", "more_body": True},
                    {"type": "http.request", "body": b"cd", "more_body": False},
                ],
            )
        )
        assert chunked[0]["status"] == 413
        assert b"WEB_PROMPT_LIBRARY_BODY_TOO_LARGE" in chunked[1]["body"]

        exact_boundary = asyncio.run(
            invoke(
                chunked_scope,
                [
                    {"type": "http.request", "body": b"ab", "more_body": True},
                    {"type": "http.request", "body": b"c", "more_body": False},
                ],
            )
        )
        assert exact_boundary[0]["status"] == 200
        assert exact_boundary[1]["body"] == b"abc"


def test_prompt_library_import_export_is_bounded_private_round_trippable_and_has_no_storage_artifact(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "prompt-import@example.com")
        import_payload = template_payload("ignored-import-item-key")
        import_payload.pop("idempotency_key")
        imported = client.post(
            "/api/v1/prompt-library/import",
            headers={"X-CSRF-Token": csrf},
            json={"templates": [import_payload], "idempotency_key": "prompt-template-import-0001"},
        )
        assert imported.status_code == 200
        assert imported.json()["data"]["imported"] == 1
        replay = client.post(
            "/api/v1/prompt-library/import",
            headers={"X-CSRF-Token": csrf},
            json={"templates": [import_payload], "idempotency_key": "prompt-template-import-0001"},
        )
        assert replay.json()["data"]["items"][0]["id"] == imported.json()["data"]["items"][0]["id"]
        too_many = client.post(
            "/api/v1/prompt-library/import",
            headers={"X-CSRF-Token": csrf},
            json={"templates": [import_payload] * 51, "idempotency_key": "prompt-template-import-too-many-0001"},
        )
        assert too_many.status_code == 422

        imported_id = imported.json()["data"]["items"][0]["id"]
        archived = client.post(
            f"/api/v1/prompt-library/templates/{imported_id}/archive",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 1, "idempotency_key": "prompt-template-export-archive-0001"},
        )
        assert archived.json()["data"]["template"]["state"] == "archived"

        assert client.get("/api/v1/prompt-library/export").status_code == 404
        exported = client.post("/api/v1/prompt-library/export", headers={"X-CSRF-Token": csrf})
        assert exported.status_code == 200
        assert exported.headers["content-type"].startswith("application/json")
        assert "attachment" in exported.headers["content-disposition"]
        assert exported.headers["cache-control"] == "no-store, private"
        assert exported.headers["referrer-policy"] == "no-referrer"
        assert exported.headers["content-security-policy"] == "sandbox"
        body = json.loads(exported.content.decode("utf-8"))
        assert body["schema"] == "toan-aas-web-prompt-library-v1"
        assert body["templates"][0]["prompt_text"] == import_payload["prompt_text"]
        assert "account_id" not in body["templates"][0]
        assert "id" not in body["templates"][0]
        assert "revision" not in body["templates"][0]
        assert body["templates"][0]["state"] == "archived"

        with make_client(tmp_path, monkeypatch) as other:
            csrf_other = register_and_login(other, "prompt-export-other@example.com")
            round_trip = other.post(
                "/api/v1/prompt-library/import",
                headers={"X-CSRF-Token": csrf_other},
                json={"templates": body["templates"], "idempotency_key": "prompt-template-roundtrip-import-0001"},
            )
            assert round_trip.status_code == 200
            assert round_trip.json()["data"]["items"][0]["state"] == "archived"
            other_export = json.loads(other.post("/api/v1/prompt-library/export", headers={"X-CSRF-Token": csrf_other}).content.decode("utf-8"))
            assert other_export["templates"][0]["title"] == import_payload["title"]
            assert other_export["templates"][0]["state"] == "archived"

        db_path = tmp_path / "copyfast-prompt-library-test.db"
        with sqlite3.connect(db_path) as conn:
            idempotency_rows = conn.execute("SELECT response_json FROM web_idempotency").fetchall()
        assert idempotency_rows
        assert all(import_payload["prompt_text"] not in str(row[0]) for row in idempotency_rows)


def test_prompt_library_restore_respects_active_limit(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        module = sys.modules["copyfast_prompt_library"]
        monkeypatch.setattr(module, "MAX_TEMPLATES_PER_ACCOUNT", 1)
        csrf = register_and_login(client, "prompt-limit@example.com")
        archived = create_template(client, csrf, "prompt-template-limit-archived-0001")
        archive_response = client.post(
            f"/api/v1/prompt-library/templates/{archived['id']}/archive",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 1, "idempotency_key": "prompt-template-limit-archive-0001"},
        )
        assert archive_response.json()["ok"] is True
        create_template(client, csrf, "prompt-template-limit-active-0001", title="Template đang active")
        restore_response = client.post(
            f"/api/v1/prompt-library/templates/{archived['id']}/restore",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 2, "idempotency_key": "prompt-template-limit-restore-0001"},
        )
        assert restore_response.json()["ok"] is False
        assert restore_response.json()["error_code"] == "WEB_PROMPT_TEMPLATE_LIMIT"


def test_prompt_library_purge_requires_archive_confirmation_and_removes_private_history(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "prompt-purge@example.com")
        created = create_template(client, csrf, "prompt-template-purge-create-0001")
        guarded = client.post(
            f"/api/v1/prompt-library/templates/{created['id']}/purge",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 1, "confirm": True, "idempotency_key": "prompt-template-purge-active-0001"},
        )
        assert guarded.json()["error_code"] == "WEB_PROMPT_TEMPLATE_PURGE_REQUIRES_ARCHIVE"
        archived = client.post(
            f"/api/v1/prompt-library/templates/{created['id']}/archive",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 1, "idempotency_key": "prompt-template-purge-archive-0001"},
        )
        assert archived.json()["data"]["template"]["revision"] == 2
        denied_confirmation = client.post(
            f"/api/v1/prompt-library/templates/{created['id']}/purge",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 2, "confirm": False, "idempotency_key": "prompt-template-purge-denied-0001"},
        )
        assert denied_confirmation.status_code == 422
        missing_confirmation = client.post(
            f"/api/v1/prompt-library/templates/{created['id']}/purge",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 2, "idempotency_key": "prompt-template-purge-missing-0001"},
        )
        assert missing_confirmation.status_code == 422
        with make_client(tmp_path, monkeypatch) as other:
            csrf_other = register_and_login(other, "prompt-purge-other@example.com")
            cross_account = other.post(
                f"/api/v1/prompt-library/templates/{created['id']}/purge",
                headers={"X-CSRF-Token": csrf_other},
                json={"expected_revision": 2, "confirm": True, "idempotency_key": "prompt-template-purge-other-0001"},
            )
            assert cross_account.json()["error_code"] == "WEB_PROMPT_TEMPLATE_NOT_FOUND"
        purged = client.post(
            f"/api/v1/prompt-library/templates/{created['id']}/purge",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 2, "confirm": True, "idempotency_key": "prompt-template-purge-confirmed-0001"},
        )
        assert purged.json()["data"] == {"template_id": created["id"], "purged": True}
        assert client.get(f"/api/v1/prompt-library/templates/{created['id']}").json()["error_code"] == "WEB_PROMPT_TEMPLATE_NOT_FOUND"
        db_path = tmp_path / "copyfast-prompt-library-test.db"
        with sqlite3.connect(db_path) as conn:
            version_count = conn.execute("SELECT COUNT(*) FROM web_prompt_template_versions WHERE template_id=?", (created["id"],)).fetchone()[0]
            event_count = conn.execute("SELECT COUNT(*) FROM web_prompt_template_events WHERE template_id=?", (created["id"],)).fetchone()[0]
            audit_actions = [row[0] for row in conn.execute("SELECT action FROM web_audit_events WHERE target=?", (created["id"],)).fetchall()]
        assert version_count == 0
        assert event_count == 0
        assert "web.prompt_library.purge" in audit_actions


def test_prompt_library_versions_are_bounded_before_another_snapshot_is_written(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        module = sys.modules["copyfast_prompt_library"]
        monkeypatch.setattr(module, "MAX_VERSIONS_PER_TEMPLATE", 2)
        csrf = register_and_login(client, "prompt-version-limit@example.com")
        created = create_template(client, csrf, "prompt-template-version-create-0001")
        first_update = client.patch(
            f"/api/v1/prompt-library/templates/{created['id']}",
            headers={"X-CSRF-Token": csrf},
            json=template_payload(
                "prompt-template-version-update-0001",
                title="Template revision hai",
                expected_revision=1,
            ),
        )
        assert first_update.json()["data"]["template"]["revision"] == 2
        blocked = client.patch(
            f"/api/v1/prompt-library/templates/{created['id']}",
            headers={"X-CSRF-Token": csrf},
            json=template_payload(
                "prompt-template-version-update-0002",
                title="Template revision ba",
                expected_revision=2,
            ),
        )
        assert blocked.json()["ok"] is False
        assert blocked.json()["error_code"] == "WEB_PROMPT_TEMPLATE_VERSION_LIMIT"
        detail = client.get(f"/api/v1/prompt-library/templates/{created['id']}").json()["data"]
        assert detail["template"]["revision"] == 2
        assert len(detail["versions"]) == 2


def test_prompt_library_storage_quota_keeps_archive_cleanup_and_export_bounded(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        module = sys.modules["copyfast_prompt_library"]
        csrf = register_and_login(client, "prompt-storage-quota@example.com")
        created = create_template(client, csrf, "prompt-template-storage-create-0001")
        used_bytes = client.get("/api/v1/prompt-library/summary").json()["data"]["storage"]["used_bytes"]
        assert used_bytes > 0
        monkeypatch.setattr(module, "MAX_TEMPLATE_STORAGE_BYTES", used_bytes)

        blocked_update = client.patch(
            f"/api/v1/prompt-library/templates/{created['id']}",
            headers={"X-CSRF-Token": csrf},
            json=template_payload(
                "prompt-template-storage-update-0001",
                title="Template vượt quota",
                expected_revision=1,
            ),
        )
        assert blocked_update.json()["error_code"] == "WEB_PROMPT_TEMPLATE_STORAGE_LIMIT"

        # Archive remains available to let the owner purge data even when a
        # new immutable snapshot would exceed the strict byte budget.
        archived = client.post(
            f"/api/v1/prompt-library/templates/{created['id']}/archive",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 1, "idempotency_key": "prompt-template-storage-archive-0001"},
        )
        assert archived.json()["ok"] is True
        assert archived.json()["data"]["history_snapshot_recorded"] is False
        db_path = tmp_path / "copyfast-prompt-library-test.db"
        with sqlite3.connect(db_path) as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM web_prompt_template_versions WHERE template_id=?", (created["id"],)
            ).fetchone()[0] == 1

        monkeypatch.setattr(module, "MAX_EXPORT_BYTES", 1)
        export = client.post("/api/v1/prompt-library/export", headers={"X-CSRF-Token": csrf})
        assert export.status_code == 413
        assert export.json()["error_code"] == "WEB_PROMPT_LIBRARY_EXPORT_LIMIT"
        assert "content-disposition" not in export.headers


def test_prompt_library_idempotency_prunes_expired_rows_and_never_persists_noop_guards(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        module = sys.modules["copyfast_prompt_library"]
        csrf = register_and_login(client, "prompt-idempotency-bounds@example.com")
        db_path = tmp_path / "copyfast-prompt-library-test.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    "web-prompt-library:retired-account:template:create",
                    "prompt-expired-idempotency-0001",
                    '{"ok":true}',
                    "fingerprint",
                    "2000-01-01T00:00:00+00:00",
                ),
            )
            conn.commit()
        created = create_template(client, csrf, "prompt-live-idempotency-0001")
        assert created["id"]
        with sqlite3.connect(db_path) as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM web_idempotency WHERE key='prompt-expired-idempotency-0001'"
            ).fetchone()[0] == 0

        monkeypatch.setattr(module, "MAX_TEMPLATE_STORAGE_BYTES", 1)
        guarded = client.post(
            "/api/v1/prompt-library/templates",
            headers={"X-CSRF-Token": csrf},
            json=template_payload("prompt-noop-idempotency-0001", title="Không có side effect"),
        )
        assert guarded.json()["error_code"] == "WEB_PROMPT_TEMPLATE_STORAGE_LIMIT"
        with sqlite3.connect(db_path) as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM web_idempotency WHERE key='prompt-noop-idempotency-0001'"
            ).fetchone()[0] == 0


def test_prompt_library_write_rate_limit_uses_one_fixed_family_bucket(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        register_and_login(client, "prompt-rate@example.com")
        app_module = sys.modules["app"]
        app_module._auth_rate_windows.clear()
        assert client.post("/api/v1/prompt-library/random-first").status_code == 405
        assert client.post("/api/v1/prompt-library/random-second").status_code == 405
        keys = [key for key in app_module._auth_rate_windows if key.startswith("prompt-library-write:")]
        assert len(keys) == 1
        assert len(app_module._auth_rate_windows[keys[0]]) == 2


def test_prompt_library_read_rate_limit_uses_one_fixed_family_bucket(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        register_and_login(client, "prompt-read-rate@example.com")
        app_module = sys.modules["app"]
        app_module._auth_rate_windows.clear()
        assert client.get("/api/v1/prompt-library/random-first").status_code == 404
        assert client.get("/api/v1/prompt-library/random-second").status_code == 404
        keys = [key for key in app_module._auth_rate_windows if key.startswith("prompt-library-read:")]
        assert len(keys) == 1
        assert len(app_module._auth_rate_windows[keys[0]]) == 2


def test_prompt_library_fails_closed_when_maintenance_flag_is_off(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch, prompt_library_enabled=False) as client:
        register_and_login(client, "prompt-disabled@example.com")
        response = client.get("/api/v1/prompt-library/summary")
        assert response.status_code == 503
        assert response.json()["ok"] is False


def test_prompt_library_avoids_bridge_provider_payment_and_legacy_feedback_mounts():
    source = open("copyfast_prompt_library.py", encoding="utf-8").read().lower()
    app_source = open("app.py", encoding="utf-8").read()
    assert "copyfast_bridge" not in source
    assert "import requests" not in source
    assert "import httpx" not in source
    assert "import copyfast_api" not in source
    assert "customer_api.router" not in app_source
    assert "app.include_router(copyfast_prompt_library.router)" in app_source
