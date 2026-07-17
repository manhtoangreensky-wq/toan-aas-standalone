"""Risk-focused contracts for the Web-native Voice Studio & Consent Vault.

The Voice Studio must remain a signed-account authoring surface.  These tests
focus on boundaries that would be costly or unsafe to regress: request limits,
consent/anti-imitation policy, private ownership, idempotency, and the promise
that its local writing aids never create provider audio or jobs.
"""

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
    "copyfast_music_media", "copyfast_content_studio", "copyfast_voice_studio",
    "copyfast_support",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "voice-studio-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "voice-studio-test-session-secret")
    monkeypatch.setenv("WEBAPP_VOICE_STUDIO_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_CONTENT_STUDIO_ENABLED", "true")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Voice Owner"},
    )
    assert registered.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    return login.json()["data"]["csrf_token"]


def vault_payload(key: str, **overrides) -> dict:
    payload = {
        "title": "Giọng đọc rõ ràng cho video hướng dẫn",
        "vault_kind": "delivery_style",
        "language": "vi",
        "style_notes": "Nói chậm rãi, câu ngắn và ưu tiên những chỉ dẫn có thể kiểm tra.",
        "use_context": "Video hướng dẫn khách hàng sử dụng sản phẩm an toàn.",
        "consent_status": "not_required",
        "consent_note": "",
        "is_default": True,
        "tags": ["how-to", "clear"],
        "project_id": "",
        "content_brief_id": "",
        "idempotency_key": key,
    }
    payload.update(overrides)
    return payload


def script_payload(key: str, revision: int, **overrides) -> dict:
    payload = {
        "title": "Lời mở đầu video hướng dẫn",
        "script_kind": "explainer",
        "language": "vi",
        "audience": "Khách hàng mới",
        "pace_wpm": 130,
        "script_text": "Chào bạn. Hôm nay chúng tôi hướng dẫn từng bước một cách rõ ràng và an toàn.",
        "delivery_notes": "Ngắt nhẹ sau mỗi câu, không tuyên bố hiệu quả không có bằng chứng.",
        "pronunciation_notes": "",
        "tags": ["intro"],
        "expected_revision": revision,
        "idempotency_key": key,
    }
    payload.update(overrides)
    return payload


def create_vault(client: TestClient, csrf: str, key: str = "voice-studio-create-0001", **overrides) -> dict:
    response = client.post(
        "/api/v1/voice-studio/vaults",
        headers={"X-CSRF-Token": csrf},
        json=vault_payload(key, **overrides),
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    vault_id = response.json()["data"]["vault"]["id"]
    detail = client.get(f"/api/v1/voice-studio/vaults/{vault_id}")
    assert detail.status_code == 200
    assert detail.json()["ok"] is True
    return detail.json()["data"]["vault"]


def test_voice_vaults_are_paginated_and_owner_scoped(tmp_path, monkeypatch):
    """Old Voice Vault metadata stays reachable through signed pages."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "voice-list-owner@example.com")
        created = [
            create_vault(
                client,
                csrf,
                f"voice-list-pagination-{index:04d}",
                title=f"Voice pagination {index}",
                tags=["pagination"],
                is_default=False,
            )
            for index in range(1, 4)
        ]
        pages = [
            client.get(
                "/api/v1/voice-studio/vaults",
                params={"state": "all", "q": "Voice pagination", "tag": "pagination", "limit": 1, "offset": offset},
            )
            for offset in range(3)
        ]
        assert all(page.status_code == 200 for page in pages)
        page_data = [page.json()["data"] for page in pages]
        seen_ids = {item["id"] for data in page_data for item in data["items"]}
        assert seen_ids == {item["id"] for item in created}
        assert page_data[0]["has_more"] is True
        assert page_data[0]["next_offset"] == 1
        assert page_data[1]["next_offset"] == 2
        assert page_data[2]["has_more"] is False
        assert page_data[2]["next_offset"] is None
        assert page_data[0]["filters"] == {"q": "Voice pagination", "tag": "pagination", "state": "all"}
        assert page_data[0]["pagination"] == {"limit": 1, "offset": 0, "returned": 1}

        with make_client(tmp_path, monkeypatch) as other:
            register_and_login(other, "voice-list-other@example.com")
            hidden = other.get("/api/v1/voice-studio/vaults", params={"state": "all", "q": "Voice pagination", "limit": 1})
            assert hidden.status_code == 200
            assert hidden.json()["data"]["items"] == []


def test_voice_studio_requires_session_csrf_and_keeps_receipts_free_of_authoring_text(tmp_path, monkeypatch):
    db_path = tmp_path / "voice-studio-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.get("/api/v1/voice-studio/summary").status_code == 401
        csrf = register_and_login(client, "voice-owner@example.com")
        raw = vault_payload("voice-studio-create-0001")

        denied = client.post("/api/v1/voice-studio/vaults", json=raw)
        assert denied.status_code == 403

        oversized = client.post(
            "/api/v1/voice-studio/vaults",
            headers={"X-CSRF-Token": csrf},
            json={"title": "x" * (129 * 1024)},
        )
        assert oversized.status_code == 413
        assert oversized.json()["error_code"] == "WEB_VOICE_STUDIO_BODY_TOO_LARGE"
        assert oversized.headers["cache-control"] == "no-store, private"
        assert client.get("/api/v1/voice-studio/summary").json()["data"]["vaults"]["total"] == 0

        created = client.post("/api/v1/voice-studio/vaults", headers={"X-CSRF-Token": csrf}, json=raw)
        assert created.status_code == 200
        assert created.json()["status"] == "draft"
        vault_id = created.json()["data"]["vault"]["id"]
        assert raw["title"] not in created.text
        assert raw["style_notes"] not in created.text

        replay = client.post("/api/v1/voice-studio/vaults", headers={"X-CSRF-Token": csrf}, json=raw)
        assert replay.status_code == 200
        assert replay.json() == created.json()
        collision = client.post(
            "/api/v1/voice-studio/vaults",
            headers={"X-CSRF-Token": csrf},
            json=vault_payload("voice-studio-create-0001", title="Voice direction khác"),
        )
        assert collision.status_code == 409

        detail = client.get(f"/api/v1/voice-studio/vaults/{vault_id}")
        assert detail.status_code == 200
        assert detail.json()["data"]["vault"]["style_notes"] == raw["style_notes"]
        with sqlite3.connect(db_path) as conn:
            receipts = conn.execute(
                "SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-voice-studio:%'"
            ).fetchall()
        assert receipts
        assert all(raw["title"] not in str(row[0]) for row in receipts)
        assert all(raw["style_notes"] not in str(row[0]) for row in receipts)


def test_voice_studio_enforces_consent_and_refuses_imitation_or_sensitive_authoring(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "voice-boundary@example.com")

        no_attestation = client.post(
            "/api/v1/voice-studio/vaults",
            headers={"X-CSRF-Token": csrf},
            json=vault_payload(
                "voice-consent-missing-0001",
                vault_kind="consented_reference",
                consent_status="not_required",
                consent_note="",
            ),
        )
        assert no_attestation.status_code == 422

        imitation = client.post(
            "/api/v1/voice-studio/vaults",
            headers={"X-CSRF-Token": csrf},
            json=vault_payload(
                "voice-imitation-rejected-0001",
                style_notes="Hãy clone giọng của một ca sĩ nổi tiếng cho toàn bộ video.",
            ),
        )
        assert imitation.status_code == 422

        vault = create_vault(client, csrf, "voice-policy-vault-0001")
        unsafe_script = client.post(
            f"/api/v1/voice-studio/vaults/{vault['id']}/scripts",
            headers={"X-CSRF-Token": csrf},
            json=script_payload(
                "voice-script-secret-rejected-0001",
                vault["revision"],
                script_text="api_key=super-secret-token-value-12345. Không lưu nội dung này.",
            ),
        )
        assert unsafe_script.status_code == 422

        custom_reference = create_vault(
            client,
            csrf,
            "voice-consent-valid-0001",
            title="Reference đã tự xác nhận quyền sử dụng",
            vault_kind="consented_reference",
            consent_status="self_attested",
            consent_note="Tôi tự xác nhận có quyền sử dụng định hướng này cho tài khoản hiện tại.",
            is_default=False,
        )
        assert custom_reference["consent_status"] == "self_attested"
        assert custom_reference["execution"] == "metadata_only"
        assert custom_reference["provider_status"] == "not_connected"
        assert custom_reference["preview_available"] is False

        revoked_default = client.post(
            "/api/v1/voice-studio/vaults",
            headers={"X-CSRF-Token": csrf},
            json=vault_payload(
                "voice-consent-revoked-default-0001",
                vault_kind="consented_reference",
                consent_status="revoked",
                consent_note="Tôi ghi nhận quyền sử dụng direction này đã được thu hồi cho account hiện tại.",
                is_default=True,
            ),
        )
        assert revoked_default.status_code == 422

        revoked_reference = create_vault(
            client,
            csrf,
            "voice-consent-revoked-valid-0001",
            title="Reference đã thu hồi consent",
            vault_kind="consented_reference",
            consent_status="revoked",
            consent_note="Tôi ghi nhận quyền sử dụng direction này đã được thu hồi cho account hiện tại.",
            is_default=False,
        )
        assert revoked_reference["consent_status"] == "revoked"
        assert revoked_reference["is_default"] is False
        assert revoked_reference["authoring_status"] == "guarded"
        blocked_authoring = client.post(
            f"/api/v1/voice-studio/vaults/{revoked_reference['id']}/scripts",
            headers={"X-CSRF-Token": csrf},
            json=script_payload("voice-revoked-script-blocked-0001", revoked_reference["revision"]),
        )
        assert blocked_authoring.status_code == 200
        assert blocked_authoring.json()["error_code"] == "WEB_VOICE_CONSENT_REVOKED"


def test_voice_studio_keeps_vaults_and_scripts_owner_scoped(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as first:
        csrf = register_and_login(first, "voice-first@example.com")
        vault = create_vault(first, csrf, "voice-first-create-0001")
        script = first.post(
            f"/api/v1/voice-studio/vaults/{vault['id']}/scripts",
            headers={"X-CSRF-Token": csrf},
            json=script_payload("voice-first-script-0001", vault["revision"]),
        )
        assert script.status_code == 200
        script_id = script.json()["data"]["script"]["id"]

        with make_client(tmp_path, monkeypatch) as second:
            csrf_second = register_and_login(second, "voice-second@example.com")
            hidden = second.get(f"/api/v1/voice-studio/vaults/{vault['id']}")
            assert hidden.status_code == 200
            assert hidden.json()["error_code"] == "WEB_VOICE_VAULT_NOT_FOUND"
            assert vault["title"] not in hidden.text
            assert vault["style_notes"] not in hidden.text

            script_hidden = second.get(f"/api/v1/voice-studio/vaults/{vault['id']}/scripts/{script_id}")
            assert script_hidden.status_code == 200
            assert script_hidden.json()["error_code"] == "WEB_VOICE_SCRIPT_NOT_FOUND"

            blocked = second.post(
                f"/api/v1/voice-studio/vaults/{vault['id']}/compose",
                headers={"X-CSRF-Token": csrf_second},
                json={"expected_revision": vault["revision"], "idempotency_key": "voice-cross-owner-compose-0001"},
            )
            assert blocked.status_code == 200
            assert blocked.json()["error_code"] == "WEB_VOICE_VAULT_NOT_FOUND"


def test_voice_studio_composer_and_cue_sheet_are_local_writing_aids_not_audio(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "voice-writing-aid@example.com")
        vault = create_vault(client, csrf, "voice-compose-vault-0001")

        composed = client.post(
            f"/api/v1/voice-studio/vaults/{vault['id']}/compose",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": vault["revision"], "idempotency_key": "voice-compose-local-0001"},
        )
        assert composed.status_code == 200
        data = composed.json()["data"]
        assert data["execution"] == "local_deterministic_draft_only"
        assert data["provider_called"] is False
        assert data["audio_created"] is False
        assert len(data["script_ids"]) == 3
        assert "job_id" not in composed.text
        assert "output_url" not in composed.text
        assert "audio_url" not in composed.text

        detail = client.get(f"/api/v1/voice-studio/vaults/{vault['id']}")
        scripts = detail.json()["data"]["scripts"]
        assert len(scripts) == 3
        assert all(item["source_kind"] == "local_deterministic_draft_only" for item in scripts)
        assert all(item["provider_called"] is False and item["audio_created"] is False for item in scripts)

        cue = client.get(f"/api/v1/voice-studio/vaults/{vault['id']}/scripts/{scripts[0]['id']}/cue-sheet")
        assert cue.status_code == 200
        cue_data = cue.json()["data"]
        assert cue_data["execution"] == "local_deterministic_writing_aid"
        assert cue_data["provider_called"] is False
        assert cue_data["audio_created"] is False
        assert cue_data["metrics"]["words"] > 0
        assert cue_data["items"]
        assert all(item["end_seconds"] >= item["start_seconds"] for item in cue_data["items"])
        assert "preview" not in cue_data
        assert "download" not in cue_data


def test_voice_studio_archived_vault_freezes_child_mutations_and_cue_sheets(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "voice-parent-freeze@example.com")
        vault = create_vault(client, csrf, "voice-parent-freeze-vault-0001")
        created = client.post(
            f"/api/v1/voice-studio/vaults/{vault['id']}/scripts",
            headers={"X-CSRF-Token": csrf},
            json=script_payload("voice-parent-freeze-script-0001", vault["revision"]),
        )
        assert created.status_code == 200
        script = created.json()["data"]["script"]

        archived = client.post(
            f"/api/v1/voice-studio/vaults/{vault['id']}/archive",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": vault["revision"], "idempotency_key": "voice-parent-freeze-archive-0001"},
        )
        assert archived.status_code == 200
        assert archived.json()["ok"] is True
        assert archived.json()["data"]["vault"]["state"] == "archived"

        script_archive = client.post(
            f"/api/v1/voice-studio/vaults/{vault['id']}/scripts/{script['id']}/archive",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": script["revision"], "idempotency_key": "voice-parent-freeze-script-archive-0001"},
        )
        assert script_archive.status_code == 200
        assert script_archive.json()["error_code"] == "WEB_VOICE_VAULT_ARCHIVED"

        cue = client.get(f"/api/v1/voice-studio/vaults/{vault['id']}/scripts/{script['id']}/cue-sheet")
        assert cue.status_code == 200
        assert cue.json()["error_code"] == "WEB_VOICE_VAULT_ARCHIVED"
