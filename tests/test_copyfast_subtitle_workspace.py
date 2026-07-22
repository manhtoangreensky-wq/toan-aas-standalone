"""Critical contracts for the Web-native, text-only Subtitle Studio."""

from __future__ import annotations

import importlib
import sqlite3
import sys
import uuid

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


def seed_language_source_asset(
    db_path,
    email: str,
    *,
    asset_id: str | None = None,
    display_name: str = "Launch demo source",
    original_filename: str = "private-original-source.mp4",
    extension: str = ".mp4",
    content_type: str = "video/mp4",
    byte_size: int = 4_096,
    state: str = "active",
    lifecycle_revision: int = 1,
) -> tuple[str, dict[str, str]]:
    """Seed only Asset Vault metadata for the Subtitle Studio boundary tests.

    The fixture intentionally leaves no physical file behind.  The language
    source API must prove that it never needs to open bytes, expose a storage
    key, hash or original filename, or create an external job.
    """
    asset_id = asset_id or str(uuid.uuid4())
    private = {
        "original_filename": original_filename,
        "storage_key": f"private-test-storage/{asset_id}/source.bin",
        "sha256": "a" * 64,
    }
    now = "2026-07-22T00:00:00+00:00"
    with sqlite3.connect(db_path) as conn:
        account = conn.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()
        assert account, "login fixture must create the Web account before seeding an Asset Vault record"
        conn.execute(
            """INSERT INTO web_asset_files
               (id, account_id, project_id, display_name, original_filename, extension, content_type, byte_size,
                sha256, storage_key, state, lifecycle_revision, created_at, updated_at, archived_at)
               VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                asset_id,
                str(account[0]),
                display_name,
                private["original_filename"],
                extension,
                content_type,
                byte_size,
                private["sha256"],
                private["storage_key"],
                state,
                lifecycle_revision,
                now,
                now,
                now if state == "archived" else None,
            ),
        )
    return asset_id, private


def assert_language_source_boundary(data: dict) -> None:
    for key in (
        "source_bytes_read",
        "provider_called",
        "bot_called",
        "bridge_called",
        "asr_called",
        "tts_called",
        "dubbing_called",
        "translation_called",
        "job_created",
        "output_created",
        "download_created",
        "payment_started",
        "payment_processed",
        "wallet_mutated",
    ):
        assert data[key] is False


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
        # Idempotency deliberately returns a small receipt rather than a full
        # project document.  The browser must accept this immutable identity
        # receipt, then hydrate the complete language-source contract before
        # it renders the detail route.
        assert set(created.json()["data"]["project"]) == {"id", "revision", "state"}
        assert created.json()["data"]["project"]["state"] == "draft"
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
        # The text-only surface also has an explicit response budget.  Lower
        # it in this isolated process to cover the guard without constructing
        # an unnecessarily huge subtitle fixture.
        workspace = importlib.import_module("copyfast_subtitle_workspace")
        monkeypatch.setattr(workspace, "MAX_EXPORT_UTF8_BYTES", 1)
        oversized = client.get(f"/api/v1/subtitle-studio/projects/{project['id']}/export?format=vtt")
        assert oversized.status_code == 200 and oversized.json()["ok"] is False
        assert oversized.json()["error_code"] == "WEB_SUBTITLE_EXPORT_TOO_LARGE"
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


def test_subtitle_format_lab_is_csrf_protected_and_text_only(tmp_path, monkeypatch):
    path = "/api/v1/subtitle-studio/format-tools/convert"
    srt = "1\n00:00:01,000 --> 00:00:02,400\nCâu đầu tiên\n\n2\n00:00:02,400 --> 00:00:04,000\nCâu thứ hai"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post(path, json={"mode": "srt_to_vtt", "content": srt}).status_code == 401
        csrf = login(client, "subtitle-format@example.com")
        assert client.post(path, json={"mode": "srt_to_vtt", "content": srt}).status_code == 403
        converted = client.post(path, headers={"X-CSRF-Token": csrf}, json={"mode": "srt_to_vtt", "content": srt})
        assert converted.status_code == 200 and converted.json()["ok"] is True
        payload = converted.json()
        data = payload["data"]
        assert payload["status"] == "completed"
        assert data["mode"] == "srt_to_vtt"
        assert data["format"] == "vtt"
        assert data["cue_count"] == 2
        assert data["text"].startswith("WEBVTT\n\n00:00:01.000 --> 00:00:02.400")
        for key in ("provider_called", "asr_called", "translation_called", "tts_called", "dubbing_called", "media_uploads", "output_created", "job_created", "payment_charged"):
            assert data[key] is False
        assert data["execution"] == "web_native_text_transform"
        assert data["output_delivery"] == "none"
        assert converted.headers["Cache-Control"] == "no-store, private"


def test_subtitle_format_lab_normalizes_vtt_and_creates_deterministic_text_srt(tmp_path, monkeypatch):
    path = "/api/v1/subtitle-studio/format-tools/convert"
    vtt = "WEBVTT\nKind: captions\n\nNOTE excluded\nmetadata is not returned\n\n00:00:01.000 --> 00:00:02.000\nHello\n\n00:00:02.000 --> 00:00:03.000\nWorld"
    words = "một hai ba bốn năm sáu bảy tám chín mười mười một mười hai mười ba"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "subtitle-format-normalize@example.com")
        normalized = client.post(path, headers={"X-CSRF-Token": csrf}, json={"mode": "vtt_to_srt", "content": vtt})
        assert normalized.status_code == 200 and normalized.json()["ok"] is True
        text = normalized.json()["data"]["text"]
        assert text.startswith("1\n00:00:01,000 --> 00:00:02,000\nHello")
        assert "Kind: captions" not in text and "NOTE excluded" not in text
        generated = client.post(path, headers={"X-CSRF-Token": csrf}, json={"mode": "text_to_srt", "content": words, "duration_seconds": 5})
        assert generated.status_code == 200 and generated.json()["ok"] is True
        generated_data = generated.json()["data"]
        assert generated_data["cue_count"] == 2
        assert "00:00:00,000 --> 00:00:02,500" in generated_data["text"]
        assert "00:00:02,500 --> 00:00:05,000" in generated_data["text"]
        rejected_extra = client.post(path, headers={"X-CSRF-Token": csrf}, json={"mode": "text_to_srt", "content": "nội dung hợp lệ", "file_url": "https://invalid.example"})
        assert rejected_extra.status_code == 422
        malformed = client.post(path, headers={"X-CSRF-Token": csrf}, json={"mode": "srt_to_vtt", "content": "1\ninvalid timing\nCaption"})
        assert malformed.status_code == 422
        workspace = importlib.import_module("copyfast_subtitle_workspace")
        monkeypatch.setattr(workspace, "MAX_EXPORT_UTF8_BYTES", 1)
        oversized = client.post(path, headers={"X-CSRF-Token": csrf}, json={"mode": "text_to_srt", "content": "nội dung hợp lệ"})
        assert oversized.status_code == 200 and oversized.json()["ok"] is False
        assert oversized.json()["error_code"] == "WEB_SUBTITLE_FORMAT_OUTPUT_TOO_LARGE"
        assert "text" not in oversized.json()["data"]


def test_subtitle_language_source_listing_is_owner_scoped_exact_and_metadata_only(tmp_path, monkeypatch):
    db_path = tmp_path / "subtitle-studio-test.db"
    path = "/api/v1/subtitle-studio/references/language-sources?limit=30&offset=0"
    owner_email = "subtitle-language-owner@example.com"
    with make_client(tmp_path, monkeypatch) as owner:
        # This is a private account read; it neither accepts an anonymous
        # caller nor enables any mutation/upload capability.
        assert owner.get(path).status_code == 401
        csrf = login(owner, owner_email)
        valid_id, private = seed_language_source_asset(db_path, owner_email, display_name="Launch demo source")
        seed_language_source_asset(
            db_path,
            owner_email,
            display_name="MIME mismatch must stay hidden",
            original_filename="private-mismatch.mp4",
            extension=".mp4",
            content_type="application/octet-stream",
        )
        seed_language_source_asset(
            db_path,
            owner_email,
            display_name="Archived source must stay hidden",
            original_filename="private-archived.mp3",
            extension=".mp3",
            content_type="audio/mpeg",
            state="archived",
            lifecycle_revision=2,
        )

        # A source reference is create-only and still needs normal CSRF.
        csrf_guard = owner.post(
            "/api/v1/subtitle-studio/projects",
            json=project_payload(
                "subtitle-language-list-csrf-0001",
                source_mode="asset_reference",
                source_asset_id=valid_id,
                source_rights_confirmed=True,
            ),
        )
        assert csrf_guard.status_code == 403

        listed = owner.get(path)
        assert listed.status_code == 200 and listed.json()["ok"] is True
        assert listed.headers["Cache-Control"] == "no-store, private"
        data = listed.json()["data"]
        assert data["execution"] == "asset_reference_metadata_only"
        assert data["output_delivery"] == "none"
        assert_language_source_boundary(data)
        assert data["pagination"] == {"limit": 30, "offset": 0, "returned": 1}
        assert [item["id"] for item in data["items"]] == [valid_id]
        item = data["items"][0]
        assert set(item) == {"id", "display_name", "extension", "content_type", "byte_size", "state", "lifecycle_revision", "updated_at"}
        assert item["display_name"] == "Launch demo source"
        assert item["extension"] == ".mp4" and item["content_type"] == "video/mp4"
        for secret in private.values():
            assert secret not in listed.text
        for forbidden in ("original_filename", "storage_key", "sha256", "path", "url", "download", "preview"):
            assert forbidden not in item

    # A second signed Web account sees neither the first account's reference
    # nor an existence distinction between a foreign and archived UUID.
    second_email = "subtitle-language-other@example.com"
    with make_client(tmp_path, monkeypatch) as other:
        csrf_other = login(other, second_email)
        archived_id, _ = seed_language_source_asset(
            db_path,
            second_email,
            display_name="Other archived source",
            original_filename="other-private-archived.mp3",
            extension=".mp3",
            content_type="audio/mpeg",
            state="archived",
            lifecycle_revision=2,
        )
        hidden = other.get(path)
        assert hidden.status_code == 200 and hidden.json()["data"]["items"] == []
        foreign = other.post(
            "/api/v1/subtitle-studio/projects",
            headers={"X-CSRF-Token": csrf_other},
            json=project_payload(
                "subtitle-language-foreign-0001",
                source_mode="asset_reference",
                source_asset_id=valid_id,
                source_rights_confirmed=True,
            ),
        )
        archived = other.post(
            "/api/v1/subtitle-studio/projects",
            headers={"X-CSRF-Token": csrf_other},
            json=project_payload(
                "subtitle-language-archived-0001",
                source_mode="asset_reference",
                source_asset_id=archived_id,
                source_rights_confirmed=True,
            ),
        )
        assert foreign.status_code == archived.status_code == 422
        foreign_body, archived_body = foreign.json(), archived.json()
        for body in (foreign_body, archived_body):
            assert body["ok"] is False
            assert body["status"] == "failed"
            assert body["error_code"] == "REQUEST_INVALID"
            assert body["data"] == {}
        assert foreign_body["message"] == archived_body["message"]
        assert valid_id not in foreign.text and archived_id not in archived.text

        # Lookup scope is enforced in SQL as well as through the generic
        # 422 create result: an archived record and a record owned by a
        # different Web account do not produce a candidate row at all.
        workspace = importlib.import_module("copyfast_subtitle_workspace")
        with sqlite3.connect(db_path) as conn:
            owner_account = conn.execute("SELECT id FROM web_accounts WHERE email=?", (owner_email,)).fetchone()
            other_account = conn.execute("SELECT id FROM web_accounts WHERE email=?", (second_email,)).fetchone()
            assert owner_account and other_account
            assert workspace._language_source_asset_row(
                conn, asset_id=valid_id, account_id=str(owner_account[0])
            ) is not None
            assert workspace._language_source_asset_row(
                conn, asset_id=valid_id, account_id=str(other_account[0])
            ) is None
            assert workspace._language_source_asset_row(
                conn, asset_id=archived_id, account_id=str(other_account[0])
            ) is None


def test_subtitle_language_source_listing_paginates_only_fully_eligible_assets(tmp_path, monkeypatch):
    """Ineligible legacy rows cannot consume the picker offset.

    All three malformed rows sort before the eligible records.  A raw SQL
    page followed by Python filtering would return an empty first page and
    skip/double results on the next request; the endpoint must page only over
    rows already meeting the whole source contract.
    """
    db_path = tmp_path / "subtitle-studio-test.db"
    email = "subtitle-language-pagination@example.com"
    path = "/api/v1/subtitle-studio/references/language-sources?limit=2&offset="
    with make_client(tmp_path, monkeypatch) as client:
        login(client, email)
        first_id, _ = seed_language_source_asset(db_path, email, display_name="Eligible one")
        second_id, _ = seed_language_source_asset(db_path, email, display_name="Eligible two")
        third_id, _ = seed_language_source_asset(db_path, email, display_name="Eligible three")
        blank_id, _ = seed_language_source_asset(db_path, email, display_name="\u2003\u00a0")
        oversized_id, _ = seed_language_source_asset(
            db_path,
            email,
            display_name="Oversized metadata record",
            byte_size=100 * 1024 * 1024 + 1,
        )
        stale_revision_id, _ = seed_language_source_asset(
            db_path,
            email,
            display_name="Zero revision metadata record",
            lifecycle_revision=0,
        )
        with sqlite3.connect(db_path) as conn:
            # Invalid rows sort first.  Eligible rows are deterministic and
            # distinct so the test also proves the stable next offset.
            for asset_id, updated_at in (
                (blank_id, "2026-07-22T00:10:00+00:00"),
                (oversized_id, "2026-07-22T00:09:00+00:00"),
                (stale_revision_id, "2026-07-22T00:08:00+00:00"),
                (first_id, "2026-07-22T00:07:00+00:00"),
                (second_id, "2026-07-22T00:06:00+00:00"),
                (third_id, "2026-07-22T00:05:00+00:00"),
            ):
                conn.execute("UPDATE web_asset_files SET updated_at=? WHERE id=?", (updated_at, asset_id))

        first_page = client.get(path + "0")
        assert first_page.status_code == 200 and first_page.json()["ok"] is True
        first_data = first_page.json()["data"]
        assert [item["id"] for item in first_data["items"]] == [first_id, second_id]
        assert first_data["pagination"] == {"limit": 2, "offset": 0, "returned": 2}
        assert first_data["has_more"] is True and first_data["next_offset"] == 2

        second_page = client.get(path + str(first_data["next_offset"]))
        assert second_page.status_code == 200 and second_page.json()["ok"] is True
        second_data = second_page.json()["data"]
        assert [item["id"] for item in second_data["items"]] == [third_id]
        assert second_data["pagination"] == {"limit": 2, "offset": 2, "returned": 1}
        assert second_data["has_more"] is False and second_data["next_offset"] is None
        assert second_data["previous_offset"] == 0
        returned = [item["id"] for item in first_data["items"] + second_data["items"]]
        assert returned == [first_id, second_id, third_id]
        assert not set(returned) & {blank_id, oversized_id, stale_revision_id}


def test_subtitle_language_source_create_is_immutable_and_never_reads_asset_bytes(tmp_path, monkeypatch):
    db_path = tmp_path / "subtitle-studio-test.db"
    email = "subtitle-language-create@example.com"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, email)
        asset_id, private = seed_language_source_asset(
            db_path,
            email,
            display_name="Owned audio source",
            original_filename="private-owned-audio.mp3",
            extension=".mp3",
            content_type="audio/mpeg",
        )
        alternate_id, _ = seed_language_source_asset(
            db_path,
            email,
            display_name="Alternate audio source",
            original_filename="private-alternate-audio.mp3",
            extension=".mp3",
            content_type="audio/mpeg",
        )
        created = client.post(
            "/api/v1/subtitle-studio/projects",
            headers={"X-CSRF-Token": csrf},
            json=project_payload(
                "subtitle-language-source-create-0001",
                source_mode="asset_reference",
                source_asset_id=asset_id,
                source_rights_confirmed=True,
            ),
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        assert created.headers["Cache-Control"] == "no-store, private"
        assert_language_source_boundary(created.json()["data"])
        project_id = created.json()["data"]["project"]["id"]

        detail_response = client.get(f"/api/v1/subtitle-studio/projects/{project_id}")
        assert detail_response.status_code == 200 and detail_response.json()["ok"] is True
        detail = detail_response.json()["data"]
        assert_language_source_boundary(detail)
        project = detail["project"]
        source = project["language_source"]
        assert source["mode"] == "asset_reference"
        assert source["asset_available"] is True and source["rights_confirmed"] is True
        assert source["attested_at"]
        assert set(source["asset"]) == {"id", "display_name", "extension", "content_type", "byte_size", "state", "lifecycle_revision", "updated_at"}
        assert source["asset"]["id"] == asset_id
        assert source["asset"]["display_name"] == "Owned audio source"
        for secret in private.values():
            assert secret not in detail_response.text

        with sqlite3.connect(db_path) as conn:
            source_row = conn.execute(
                """SELECT source_mode, source_asset_id, source_asset_lifecycle_revision,
                          source_rights_confirmed, source_attested_at
                   FROM web_subtitle_projects WHERE id=?""",
                (project_id,),
            ).fetchone()
            snapshots = conn.execute(
                "SELECT snapshot_json FROM web_subtitle_project_versions WHERE subtitle_project_id=? ORDER BY revision",
                (project_id,),
            ).fetchall()
        assert source_row[0:4] == ("asset_reference", asset_id, 1, 1)
        assert source_row[4]
        stored = "\n".join(str(value) for row in snapshots for value in row)
        assert asset_id in stored
        for secret in private.values():
            assert secret not in stored

        # Update DTOs have extra=forbid and cannot retarget a source after
        # creation, even if the caller owns another otherwise valid asset.
        retarget = project_payload(
            "subtitle-language-source-retarget-0001",
            title="Attempt retarget must fail",
            source_mode="asset_reference",
            source_asset_id=alternate_id,
            source_rights_confirmed=True,
            expected_revision=project["revision"],
        )
        rejected = client.patch(
            f"/api/v1/subtitle-studio/projects/{project_id}",
            headers={"X-CSRF-Token": csrf},
            json=retarget,
        )
        assert rejected.status_code == 422

        updated = client.patch(
            f"/api/v1/subtitle-studio/projects/{project_id}",
            headers={"X-CSRF-Token": csrf},
            json=project_payload(
                "subtitle-language-source-update-0001",
                title="Metadata-only source stays attached",
                expected_revision=project["revision"],
            ),
        )
        assert updated.status_code == 200 and updated.json()["ok"] is True
        current_revision = updated.json()["data"]["project"]["revision"]

        # When an asset lifecycle changes later, the project keeps its opaque
        # historical UUID but no longer exposes any asset metadata or treats
        # it as a usable source.  Restoring revision 1 must not revive it.
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE web_asset_files SET state='archived', lifecycle_revision=2, archived_at=? WHERE id=?",
                ("2026-07-22T00:01:00+00:00", asset_id),
            )
        unavailable = client.get(f"/api/v1/subtitle-studio/projects/{project_id}").json()["data"]["project"]["language_source"]
        assert unavailable == {
            "mode": "asset_reference",
            "asset": None,
            "asset_available": False,
            "rights_confirmed": True,
            "attested_at": source["attested_at"],
        }
        restored = client.post(
            f"/api/v1/subtitle-studio/projects/{project_id}/restore-version",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": current_revision, "target_revision": 1, "idempotency_key": "subtitle-language-source-restore-0001"},
        )
        assert restored.status_code == 200 and restored.json()["ok"] is True
        final_source = client.get(f"/api/v1/subtitle-studio/projects/{project_id}").json()["data"]["project"]["language_source"]
        assert final_source["mode"] == "asset_reference"
        assert final_source["asset"] is None and final_source["asset_available"] is False
        with sqlite3.connect(db_path) as conn:
            persisted = conn.execute(
                "SELECT source_asset_id, source_asset_lifecycle_revision, source_rights_confirmed FROM web_subtitle_projects WHERE id=?",
                (project_id,),
            ).fetchone()
        assert persisted == (asset_id, 1, 1)


def test_subtitle_language_source_malformed_persisted_shape_is_guarded_and_never_normalized(tmp_path, monkeypatch):
    """A legacy/direct DB source mismatch must never become a manual source.

    The public response redacts the malformed record as guarded, and all
    project-row writers reject it so an update/lifecycle action cannot erase
    provenance by rewriting the source columns to their manual defaults.
    """
    db_path = tmp_path / "subtitle-studio-test.db"
    email = "subtitle-language-legacy-guard@example.com"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, email)
        project = create_project(client, csrf, "subtitle-language-legacy-create-0001")
        project_id, revision = project["id"], project["revision"]
        malformed_asset_id = str(uuid.uuid4())
        persisted = (
            # `rights=2` is truthy if coerced with bool(int(...)), but it is
            # not the one canonical asset-reference attestation value (`1`).
            "asset_reference", malformed_asset_id, 7, 2,
            "2026-07-22T00:00:00+00:00",
        )
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """UPDATE web_subtitle_projects
                   SET source_mode=?, source_asset_id=?, source_asset_lifecycle_revision=?,
                       source_rights_confirmed=?, source_attested_at=? WHERE id=?""",
                (*persisted, project_id),
            )

        detail = client.get(f"/api/v1/subtitle-studio/projects/{project_id}")
        assert detail.status_code == 200 and detail.json()["ok"] is True
        assert detail.json()["data"]["project"]["language_source"] == {
            "mode": "guarded", "asset": None, "asset_available": False,
            "rights_confirmed": False, "attested_at": None,
        }
        update = client.patch(
            f"/api/v1/subtitle-studio/projects/{project_id}",
            headers={"X-CSRF-Token": csrf},
            json=project_payload(
                "subtitle-language-legacy-update-0001",
                expected_revision=revision,
                title="Must not normalize source",
            ),
        )
        lifecycle = client.post(
            f"/api/v1/subtitle-studio/projects/{project_id}/lifecycle",
            headers={"X-CSRF-Token": csrf},
            json={"state": "review", "expected_revision": revision, "idempotency_key": "subtitle-language-legacy-state-0001"},
        )
        for response in (update, lifecycle):
            assert response.status_code == 200 and response.json()["ok"] is False
            assert response.json()["status"] == "guarded"
            assert response.json()["error_code"] == "WEB_SUBTITLE_LANGUAGE_SOURCE_GUARDED"
        with sqlite3.connect(db_path) as conn:
            final = conn.execute(
                """SELECT source_mode, source_asset_id, source_asset_lifecycle_revision,
                          source_rights_confirmed, source_attested_at
                   FROM web_subtitle_projects WHERE id=?""",
                (project_id,),
            ).fetchone()
        assert final == persisted
