"""Critical contracts for the Web-native, text-only Subtitle Studio."""

from __future__ import annotations

import importlib
import sqlite3
import sys

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry", "copyfast_api",
    "copyfast_pages", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations", "copyfast_memory",
    "copyfast_prompt_library", "copyfast_music_media", "copyfast_content_studio", "copyfast_voice_studio",
    "copyfast_video_studio", "copyfast_subtitle_workspace", "copyfast_support",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "subtitle-studio-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "subtitle-studio-test-session-secret")
    monkeypatch.setenv("WEBAPP_SUBTITLE_STUDIO_ENABLED", "true")
    for name in ("APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def login(client: TestClient, email: str) -> str:
    registered = client.post("/api/v1/auth/register", json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Subtitle Owner"})
    assert registered.status_code == 200
    signed_in = client.post("/api/v1/auth/login", json={"email": email, "password": "correct-horse-battery-staple"})
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def project_payload(key: str, **overrides) -> dict:
    value = {
        "title": "Phụ đề hướng dẫn sử dụng sản phẩm", "source_language": "vi", "target_language": "en",
        "caption_format": "srt", "context": "Dùng cho bản hướng dẫn nội bộ với giọng điệu rõ ràng.",
        "tags": ["how-to", "manual"], "project_id": "", "intent": "translation", "idempotency_key": key,
    }
    value.update(overrides)
    return value


def cue_payload(key: str, revision: int, *, start: int = 0, end: int = 1000, **overrides) -> dict:
    value = {
        "start_ms": start, "end_ms": end, "speaker": "Người dẫn", "source_text": "Chào mừng bạn đến với phần hướng dẫn.",
        "translated_text": "Welcome to the guide.", "notes": "Đọc chậm, rõ từng bước.",
        "expected_revision": revision, "idempotency_key": key,
    }
    value.update(overrides)
    return value


def create_project(client: TestClient, csrf: str, key: str = "subtitle-project-create-0001", **overrides) -> dict:
    created = client.post("/api/v1/subtitle-studio/projects", headers={"X-CSRF-Token": csrf}, json=project_payload(key, **overrides))
    assert created.status_code == 200
    assert created.json()["ok"] is True
    project_id = created.json()["data"]["project"]["id"]
    detail = client.get(f"/api/v1/subtitle-studio/projects/{project_id}")
    assert detail.status_code == 200 and detail.json()["ok"] is True
    return detail.json()["data"]["project"]


def test_subtitle_requires_session_csrf_and_scrubs_idempotency_receipts(tmp_path, monkeypatch):
    db_path = tmp_path / "subtitle-studio-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.get("/api/v1/subtitle-studio/summary").status_code == 401
        csrf = login(client, "subtitle-auth@example.com")
        raw = project_payload("subtitle-project-idempotency-0001")
        assert client.post("/api/v1/subtitle-studio/projects", json=raw).status_code == 403
        too_large = client.post(
            "/api/v1/subtitle-studio/projects", headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
            content=b'{"title":"' + (b"x" * (129 * 1024)) + b'"}',
        )
        assert too_large.status_code == 413
        assert too_large.json()["error_code"] == "WEB_SUBTITLE_STUDIO_BODY_TOO_LARGE"
        assert too_large.headers["Cache-Control"] == "no-store, private"
        created = client.post("/api/v1/subtitle-studio/projects", headers={"X-CSRF-Token": csrf}, json=raw)
        assert created.status_code == 200 and created.json()["ok"] is True
        assert raw["context"] not in created.text
        assert created.json()["data"]["execution"] == "authoring_only"
        assert created.json()["data"]["output_created"] is False
        replay = client.post("/api/v1/subtitle-studio/projects", headers={"X-CSRF-Token": csrf}, json=raw)
        assert replay.status_code == 200 and replay.json() == created.json()
        collision = client.post("/api/v1/subtitle-studio/projects", headers={"X-CSRF-Token": csrf}, json=project_payload("subtitle-project-idempotency-0001", context="Nội dung thay đổi."))
        assert collision.status_code == 409
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-subtitle-studio:%'").fetchall()
    assert rows and all(raw["title"] not in str(row[0]) and raw["context"] not in str(row[0]) for row in rows)


def test_subtitle_owner_scope_and_metadata_boundary(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as first:
        csrf = login(first, "subtitle-first@example.com")
        project = create_project(first, csrf, "subtitle-first-project-0001")
        accepted = first.post(
            f"/api/v1/subtitle-studio/projects/{project['id']}/cues", headers={"X-CSRF-Token": csrf},
            json=cue_payload("subtitle-url-spoken-0001", project["revision"], source_text="Đọc địa chỉ https://example.test/help như nội dung hiển thị."),
        )
        assert accepted.status_code == 200 and accepted.json()["ok"] is True
        blocked_note = first.post(
            f"/api/v1/subtitle-studio/projects/{project['id']}/cues", headers={"X-CSRF-Token": csrf},
            json=cue_payload("subtitle-note-url-0001", accepted.json()["data"]["project"]["revision"], start=1200, end=2200, notes="Tham chiếu https://provider.example/private"),
        )
        assert blocked_note.status_code == 422
        with make_client(tmp_path, monkeypatch) as second:
            csrf_second = login(second, "subtitle-second@example.com")
            hidden = second.get(f"/api/v1/subtitle-studio/projects/{project['id']}")
            assert hidden.status_code == 200 and hidden.json()["ok"] is False
            assert hidden.json()["error_code"] == "WEB_SUBTITLE_PROJECT_NOT_FOUND"
            assert project["title"] not in hidden.text
            denied = second.post(f"/api/v1/subtitle-studio/projects/{project['id']}/cues", headers={"X-CSRF-Token": csrf_second}, json=cue_payload("subtitle-cross-owner-0001", project["revision"], start=1500, end=2500))
            assert denied.status_code == 200 and denied.json()["error_code"] == "WEB_SUBTITLE_PROJECT_NOT_FOUND"


def test_subtitle_import_replaces_active_cues_and_vtt_metadata_is_safe(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "subtitle-import@example.com")
        project = create_project(client, csrf, "subtitle-import-project-0001")
        original = client.post(f"/api/v1/subtitle-studio/projects/{project['id']}/cues", headers={"X-CSRF-Token": csrf}, json=cue_payload("subtitle-original-cue-0001", project["revision"]))
        assert original.status_code == 200 and original.json()["ok"] is True
        revision = original.json()["data"]["project"]["revision"]
        imported = client.post(
            f"/api/v1/subtitle-studio/projects/{project['id']}/import", headers={"X-CSRF-Token": csrf},
            json={"format": "vtt", "content": "WEBVTT\nKind: captions\nLanguage: vi\nX-TIMESTAMP-MAP=MPEGTS:900000,LOCAL:00:00:00.000\n\nNOTE ignored safely\nno metadata persists\n\n00:01.000 --> 00:02.000\nCâu đầu tiên\n\n00:02.000 --> 00:03.000\nCâu thứ hai", "expected_revision": revision, "idempotency_key": "subtitle-vtt-replace-0001"},
        )
        assert imported.status_code == 200 and imported.json()["ok"] is True
        assert imported.json()["data"]["imported_count"] == 2
        assert imported.json()["data"]["replaced_count"] == 1
        detail = client.get(f"/api/v1/subtitle-studio/projects/{project['id']}").json()["data"]
        active = [cue for cue in detail["cues"] if cue["state"] == "active"]
        archived = [cue for cue in detail["cues"] if cue["state"] == "archived"]
        assert [cue["source_text"] for cue in active] == ["Câu đầu tiên", "Câu thứ hai"]
        assert len(archived) == 1
        exported = client.get(f"/api/v1/subtitle-studio/projects/{project['id']}/export?format=vtt")
        assert exported.status_code == 200 and exported.json()["ok"] is True
        assert exported.headers["Cache-Control"] == "no-store, private"
        assert "WEBVTT" in exported.json()["data"]["text"]
        assert exported.json()["data"]["output_created"] is False
        assert exported.json()["data"]["asr_called"] is False
        assert exported.json()["data"]["translation_called"] is False
        assert exported.json()["data"]["tts_called"] is False
        assert exported.json()["data"]["dubbing_called"] is False


def test_subtitle_review_approved_archive_freezes_and_estimate_never_completes(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "subtitle-lifecycle@example.com")
        project = create_project(client, csrf, "subtitle-lifecycle-project-0001")
        reviewed = client.post(f"/api/v1/subtitle-studio/projects/{project['id']}/lifecycle", headers={"X-CSRF-Token": csrf}, json={"state": "review", "expected_revision": project["revision"], "idempotency_key": "subtitle-review-0001"})
        assert reviewed.status_code == 200 and reviewed.json()["data"]["project"]["state"] == "review"
        locked = client.post(f"/api/v1/subtitle-studio/projects/{project['id']}/cues", headers={"X-CSRF-Token": csrf}, json=cue_payload("subtitle-review-locked-0001", reviewed.json()["data"]["project"]["revision"]))
        assert locked.status_code == 200 and locked.json()["error_code"] == "WEB_SUBTITLE_PROJECT_REVIEW_LOCKED"
        draft = client.post(f"/api/v1/subtitle-studio/projects/{project['id']}/lifecycle", headers={"X-CSRF-Token": csrf}, json={"state": "draft", "expected_revision": reviewed.json()["data"]["project"]["revision"], "idempotency_key": "subtitle-reopen-0001"})
        cue = client.post(f"/api/v1/subtitle-studio/projects/{project['id']}/cues", headers={"X-CSRF-Token": csrf}, json=cue_payload("subtitle-draft-cue-0001", draft.json()["data"]["project"]["revision"]))
        assert cue.status_code == 200 and cue.json()["ok"] is True
        review_again = client.post(f"/api/v1/subtitle-studio/projects/{project['id']}/lifecycle", headers={"X-CSRF-Token": csrf}, json={"state": "review", "expected_revision": cue.json()["data"]["project"]["revision"], "idempotency_key": "subtitle-review-two-0001"})
        approved = client.post(f"/api/v1/subtitle-studio/projects/{project['id']}/lifecycle", headers={"X-CSRF-Token": csrf}, json={"state": "approved", "expected_revision": review_again.json()["data"]["project"]["revision"], "idempotency_key": "subtitle-approved-0001"})
        assert approved.status_code == 200 and approved.json()["data"]["project"]["state"] == "approved"
        frozen = client.post(f"/api/v1/subtitle-studio/projects/{project['id']}/cues", headers={"X-CSRF-Token": csrf}, json=cue_payload("subtitle-approved-locked-0001", approved.json()["data"]["project"]["revision"], start=1200, end=2200))
        assert frozen.status_code == 200 and frozen.json()["error_code"] == "WEB_SUBTITLE_PROJECT_APPROVED"
        reopened = client.post(f"/api/v1/subtitle-studio/projects/{project['id']}/lifecycle", headers={"X-CSRF-Token": csrf}, json={"state": "draft", "expected_revision": approved.json()["data"]["project"]["revision"], "idempotency_key": "subtitle-reopen-two-0001"})
        archived = client.post(f"/api/v1/subtitle-studio/projects/{project['id']}/lifecycle", headers={"X-CSRF-Token": csrf}, json={"state": "archived", "expected_revision": reopened.json()["data"]["project"]["revision"], "idempotency_key": "subtitle-archive-0001"})
        assert archived.status_code == 200 and archived.json()["data"]["project"]["state"] == "archived"
        estimate = client.get(f"/api/v1/subtitle-studio/projects/{project['id']}/estimate")
        assert estimate.status_code == 200 and estimate.json()["ok"] is False
        assert estimate.json()["error_code"] == "WEB_SUBTITLE_PROJECT_ARCHIVED"
        assert "completed" not in estimate.text
        export = client.get(f"/api/v1/subtitle-studio/projects/{project['id']}/export?format=srt")
        assert export.status_code == 200 and export.json()["error_code"] == "WEB_SUBTITLE_PROJECT_ARCHIVED"


def test_subtitle_reorder_exact_active_set_survives_archives_and_restore(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "subtitle-order@example.com")
        project = create_project(client, csrf, "subtitle-order-project-0001")
        first = client.post(f"/api/v1/subtitle-studio/projects/{project['id']}/cues", headers={"X-CSRF-Token": csrf}, json=cue_payload("subtitle-order-first-0001", project["revision"], start=0, end=1000, source_text="Cue một"))
        second = client.post(f"/api/v1/subtitle-studio/projects/{project['id']}/cues", headers={"X-CSRF-Token": csrf}, json=cue_payload("subtitle-order-second-0001", first.json()["data"]["project"]["revision"], start=1000, end=2000, source_text="Cue hai"))
        third = client.post(f"/api/v1/subtitle-studio/projects/{project['id']}/cues", headers={"X-CSRF-Token": csrf}, json=cue_payload("subtitle-order-third-0001", second.json()["data"]["project"]["revision"], start=2000, end=3000, source_text="Cue ba"))
        one, two, three = first.json()["data"]["cue"], second.json()["data"]["cue"], third.json()["data"]["cue"]
        archived_one = client.post(f"/api/v1/subtitle-studio/projects/{project['id']}/cues/{one['id']}/archive", headers={"X-CSRF-Token": csrf}, json={"expected_revision": one["revision"], "idempotency_key": "subtitle-archive-one-0001"})
        archived_two = client.post(f"/api/v1/subtitle-studio/projects/{project['id']}/cues/{two['id']}/archive", headers={"X-CSRF-Token": csrf}, json={"expected_revision": two["revision"], "idempotency_key": "subtitle-archive-two-0001"})
        current_project = archived_two.json()["data"]["project"]
        invalid = client.post(f"/api/v1/subtitle-studio/projects/{project['id']}/cues/reorder", headers={"X-CSRF-Token": csrf}, json={"cue_ids": [three["id"], three["id"]], "expected_revision": current_project["revision"], "idempotency_key": "subtitle-reorder-duplicate-0001"})
        assert invalid.status_code == 200 and invalid.json()["error_code"] == "WEB_SUBTITLE_REORDER_INVALID"
        reordered = client.post(f"/api/v1/subtitle-studio/projects/{project['id']}/cues/reorder", headers={"X-CSRF-Token": csrf}, json={"cue_ids": [three["id"]], "expected_revision": current_project["revision"], "idempotency_key": "subtitle-reorder-valid-0001"})
        assert reordered.status_code == 200 and reordered.json()["ok"] is True
        restored = client.post(f"/api/v1/subtitle-studio/projects/{project['id']}/cues/{one['id']}/restore", headers={"X-CSRF-Token": csrf}, json={"expected_revision": archived_one.json()["data"]["cue"]["revision"], "idempotency_key": "subtitle-restore-one-0001"})
        assert restored.status_code == 200 and restored.json()["ok"] is True
        detail = client.get(f"/api/v1/subtitle-studio/projects/{project['id']}").json()["data"]
        active = [cue for cue in detail["cues"] if cue["state"] == "active"]
        assert [cue["id"] for cue in active] == [three["id"], one["id"]]
        assert [cue["ordinal"] for cue in active] == [1, 2]
