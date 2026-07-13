"""Critical contracts for the Web-native Video Production Studio.

The module deliberately stores authoring plans only.  These tests focus on
the boundaries where a regression would be expensive: signed-account/CSRF
ownership, idempotent writes, lifecycle freezes, exact scene sequencing and
the promise that an estimate never turns into an execution or delivery.
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
    "copyfast_video_studio", "copyfast_support",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "video-studio-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "video-studio-test-session-secret")
    monkeypatch.setenv("WEBAPP_VIDEO_STUDIO_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_VOICE_STUDIO_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_CONTENT_STUDIO_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROMPT_LIBRARY_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_MUSIC_MEDIA_WORKSPACE_ENABLED", "true")
    for name in ("APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def register_and_login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Video Owner"},
    )
    assert registered.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    return login.json()["data"]["csrf_token"]


def plan_payload(key: str, **overrides) -> dict:
    payload = {
        "title": "Video hướng dẫn sử dụng sản phẩm mới",
        "format": "explainer",
        "language": "vi",
        "aspect_ratio": "9:16",
        "target_duration_seconds": 45,
        "objective": "Giải thích đúng các bước an toàn cho khách hàng mới.",
        "audience": "Khách hàng đang bắt đầu sử dụng sản phẩm.",
        "brief": "Mở đầu ngắn, đi theo từng bước đã được kiểm tra và kết lại bằng hành động rõ ràng.",
        "tags": ["how-to", "safe"],
        "project_id": "",
        "idempotency_key": key,
    }
    payload.update(overrides)
    return payload


def scene_payload(key: str, revision: int, **overrides) -> dict:
    payload = {
        "title": "Mở đầu xác định vấn đề",
        "scene_type": "hook",
        "duration_seconds": 8,
        "visual_direction": "Cận cảnh sản phẩm trên nền sáng, bố cục rõ ràng.",
        "narration": "Hôm nay chúng ta cùng đi qua từng bước đơn giản.",
        "on_screen_text": "Bắt đầu đúng cách",
        "shot_notes": "Giữ nhịp chậm, không dùng claim chưa được kiểm tra.",
        "transition": "cut",
        "tags": ["intro"],
        "expected_revision": revision,
        "idempotency_key": key,
    }
    payload.update(overrides)
    return payload


def create_plan(client: TestClient, csrf: str, key: str = "video-plan-create-0001", **overrides) -> dict:
    created = client.post(
        "/api/v1/video-studio/plans",
        headers={"X-CSRF-Token": csrf},
        json=plan_payload(key, **overrides),
    )
    assert created.status_code == 200
    assert created.json()["ok"] is True
    plan_id = created.json()["data"]["plan"]["id"]
    detail = client.get(f"/api/v1/video-studio/plans/{plan_id}")
    assert detail.status_code == 200
    assert detail.json()["ok"] is True
    return detail.json()["data"]["plan"]


def test_video_studio_requires_session_csrf_and_scrubs_idempotency_receipts(tmp_path, monkeypatch):
    db_path = tmp_path / "video-studio-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.get("/api/v1/video-studio/summary").status_code == 401
        csrf = register_and_login(client, "video-auth@example.com")
        raw = plan_payload("video-plan-idempotency-0001")

        denied = client.post("/api/v1/video-studio/plans", json=raw)
        assert denied.status_code == 403

        created = client.post("/api/v1/video-studio/plans", headers={"X-CSRF-Token": csrf}, json=raw)
        assert created.status_code == 200
        assert created.json()["ok"] is True
        assert raw["brief"] not in created.text
        assert created.json()["data"]["provider_called"] is False
        assert created.json()["data"]["video_created"] is False

        replay = client.post("/api/v1/video-studio/plans", headers={"X-CSRF-Token": csrf}, json=raw)
        assert replay.status_code == 200
        assert replay.json() == created.json()

        collision = client.post(
            "/api/v1/video-studio/plans",
            headers={"X-CSRF-Token": csrf},
            json=plan_payload("video-plan-idempotency-0001", brief="Nội dung đã thay đổi nhưng dùng lại receipt cũ."),
        )
        assert collision.status_code == 409

    with sqlite3.connect(db_path) as conn:
        receipts = conn.execute(
            "SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-video-studio:%'"
        ).fetchall()
    assert receipts
    assert all(raw["title"] not in str(row[0]) for row in receipts)
    assert all(raw["brief"] not in str(row[0]) for row in receipts)


def test_video_studio_owner_scope_and_rejects_raw_urls(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as first:
        csrf = register_and_login(first, "video-first@example.com")
        plan = create_plan(first, csrf, "video-first-plan-0001")
        scene = first.post(
            f"/api/v1/video-studio/plans/{plan['id']}/scenes",
            headers={"X-CSRF-Token": csrf},
            json=scene_payload("video-first-scene-0001", plan["revision"]),
        )
        assert scene.status_code == 200
        assert scene.json()["ok"] is True

        bad_url = first.post(
            "/api/v1/video-studio/plans",
            headers={"X-CSRF-Token": csrf},
            json=plan_payload("video-url-blocked-0001", brief="Nguồn cũ được ghi chú ở (https://untrusted.example/private-video.mp4)."),
        )
        assert bad_url.status_code == 422

        bad_external_reference = first.post(
            "/api/v1/video-studio/plans",
            headers={"X-CSRF-Token": csrf},
            json=plan_payload("video-provider-ref-blocked-0001", brief="Ghi chú legacy: provider_id=opaque-render-12345"),
        )
        assert bad_external_reference.status_code == 422

        with make_client(tmp_path, monkeypatch) as second:
            csrf_second = register_and_login(second, "video-second@example.com")
            hidden = second.get(f"/api/v1/video-studio/plans/{plan['id']}")
            assert hidden.status_code == 200
            assert hidden.json()["ok"] is False
            assert hidden.json()["error_code"] == "WEB_VIDEO_PLAN_NOT_FOUND"
            assert plan["title"] not in hidden.text

            blocked = second.post(
                f"/api/v1/video-studio/plans/{plan['id']}/scenes",
                headers={"X-CSRF-Token": csrf_second},
                json=scene_payload("video-cross-owner-scene-0001", plan["revision"]),
            )
            assert blocked.status_code == 200
            assert blocked.json()["ok"] is False
            assert blocked.json()["error_code"] == "WEB_VIDEO_PLAN_NOT_FOUND"


def test_video_studio_approved_and_archived_plans_freeze_authoring_and_estimate(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "video-lifecycle@example.com")
        plan = create_plan(client, csrf, "video-lifecycle-plan-0001")

        review = client.post(
            f"/api/v1/video-studio/plans/{plan['id']}/lifecycle",
            headers={"X-CSRF-Token": csrf},
            json={"state": "review", "expected_revision": plan["revision"], "idempotency_key": "video-lifecycle-review-0001"},
        )
        assert review.status_code == 200
        reviewed = review.json()["data"]["plan"]
        assert reviewed["state"] == "review"

        approved = client.post(
            f"/api/v1/video-studio/plans/{plan['id']}/lifecycle",
            headers={"X-CSRF-Token": csrf},
            json={"state": "approved", "expected_revision": reviewed["revision"], "idempotency_key": "video-lifecycle-approved-0001"},
        )
        assert approved.status_code == 200
        approved_plan = approved.json()["data"]["plan"]
        assert approved_plan["state"] == "approved"
        assert approved.json()["data"]["provider_called"] is False
        assert approved.json()["data"]["video_created"] is False

        write_after_approval = client.post(
            f"/api/v1/video-studio/plans/{plan['id']}/scenes",
            headers={"X-CSRF-Token": csrf},
            json=scene_payload("video-approved-scene-0001", approved_plan["revision"]),
        )
        assert write_after_approval.status_code == 200
        assert write_after_approval.json()["error_code"] == "WEB_VIDEO_PLAN_APPROVED"

        reopen = client.post(
            f"/api/v1/video-studio/plans/{plan['id']}/lifecycle",
            headers={"X-CSRF-Token": csrf},
            json={"state": "draft", "expected_revision": approved_plan["revision"], "idempotency_key": "video-lifecycle-reopen-0001"},
        )
        assert reopen.status_code == 200
        reopened = reopen.json()["data"]["plan"]

        archived = client.post(
            f"/api/v1/video-studio/plans/{plan['id']}/lifecycle",
            headers={"X-CSRF-Token": csrf},
            json={"state": "archived", "expected_revision": reopened["revision"], "idempotency_key": "video-lifecycle-archive-0001"},
        )
        assert archived.status_code == 200
        archived_plan = archived.json()["data"]["plan"]
        assert archived_plan["state"] == "archived"

        scene_after_archive = client.post(
            f"/api/v1/video-studio/plans/{plan['id']}/scenes",
            headers={"X-CSRF-Token": csrf},
            json=scene_payload("video-archive-scene-0001", archived_plan["revision"]),
        )
        assert scene_after_archive.status_code == 200
        assert scene_after_archive.json()["error_code"] == "WEB_VIDEO_PLAN_ARCHIVED"

        estimate = client.get(f"/api/v1/video-studio/plans/{plan['id']}/estimate")
        assert estimate.status_code == 200
        assert estimate.json()["ok"] is False
        assert estimate.json()["error_code"] == "WEB_VIDEO_PLAN_ARCHIVED"


def test_video_studio_reorders_exact_active_scene_set_and_exposes_local_estimate(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "video-order@example.com")
        plan = create_plan(client, csrf, "video-order-plan-0001")

        one = client.post(
            f"/api/v1/video-studio/plans/{plan['id']}/scenes",
            headers={"X-CSRF-Token": csrf},
            json=scene_payload("video-order-scene-one-0001", plan["revision"], title="Scene thứ nhất", duration_seconds=9),
        )
        assert one.status_code == 200
        plan_after_one = one.json()["data"]["plan"]
        scene_one = one.json()["data"]["scene"]

        two = client.post(
            f"/api/v1/video-studio/plans/{plan['id']}/scenes",
            headers={"X-CSRF-Token": csrf},
            json=scene_payload("video-order-scene-two-0001", plan_after_one["revision"], title="Scene thứ hai", duration_seconds=14),
        )
        assert two.status_code == 200
        plan_after_two = two.json()["data"]["plan"]
        scene_two = two.json()["data"]["scene"]

        invalid = client.post(
            f"/api/v1/video-studio/plans/{plan['id']}/scenes/reorder",
            headers={"X-CSRF-Token": csrf},
            json={
                "scene_ids": [scene_one["id"]],
                "expected_revision": plan_after_two["revision"],
                "idempotency_key": "video-order-invalid-0001",
            },
        )
        assert invalid.status_code == 200
        assert invalid.json()["ok"] is False
        assert invalid.json()["error_code"] == "WEB_VIDEO_REORDER_INVALID"

        reordered = client.post(
            f"/api/v1/video-studio/plans/{plan['id']}/scenes/reorder",
            headers={"X-CSRF-Token": csrf},
            json={
                "scene_ids": [scene_two["id"], scene_one["id"]],
                "expected_revision": plan_after_two["revision"],
                "idempotency_key": "video-order-valid-0001",
            },
        )
        assert reordered.status_code == 200
        assert reordered.json()["ok"] is True
        assert reordered.json()["data"]["reordered"] is True
        assert reordered.json()["data"]["provider_called"] is False
        assert reordered.json()["data"]["video_created"] is False

        estimate = client.get(f"/api/v1/video-studio/plans/{plan['id']}/estimate")
        assert estimate.status_code == 200
        data = estimate.json()["data"]
        assert estimate.json()["ok"] is True
        assert [item["scene_id"] for item in data["items"]] == [scene_two["id"], scene_one["id"]]
        assert data["scene_duration_seconds"] == 23
        assert data["execution"] == "authoring_only"
        assert data["provider_called"] is False
        assert data["video_created"] is False
        assert "job_id" not in estimate.text
        assert "output_url" not in estimate.text


def test_video_studio_reorder_remains_safe_with_multiple_archives_and_restore(tmp_path, monkeypatch):
    """Archived scene ordinals must not make a valid active reorder crash.

    The request deliberately contains the exact active set.  This protects
    the temporary-ordinal implementation from a subtle unique-constraint
    regression after an earlier scene has been archived.
    """

    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "video-archive-order@example.com")
        plan = create_plan(client, csrf, "video-archive-order-plan-0001")
        first = client.post(
            f"/api/v1/video-studio/plans/{plan['id']}/scenes",
            headers={"X-CSRF-Token": csrf},
            json=scene_payload("video-archive-order-first-0001", plan["revision"], title="Scene archive trước"),
        )
        assert first.status_code == 200
        plan_one = first.json()["data"]["plan"]
        first_scene = first.json()["data"]["scene"]
        second = client.post(
            f"/api/v1/video-studio/plans/{plan['id']}/scenes",
            headers={"X-CSRF-Token": csrf},
            json=scene_payload("video-archive-order-second-0001", plan_one["revision"], title="Scene còn hoạt động"),
        )
        assert second.status_code == 200
        plan_two = second.json()["data"]["plan"]
        second_scene = second.json()["data"]["scene"]

        third = client.post(
            f"/api/v1/video-studio/plans/{plan['id']}/scenes",
            headers={"X-CSRF-Token": csrf},
            json=scene_payload("video-archive-order-third-0001", plan_two["revision"], title="Scene giữ thứ tự active"),
        )
        assert third.status_code == 200
        third_scene = third.json()["data"]["scene"]

        archived = client.post(
            f"/api/v1/video-studio/plans/{plan['id']}/scenes/{first_scene['id']}/archive",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": first_scene["revision"], "idempotency_key": "video-archive-order-scene-0001"},
        )
        assert archived.status_code == 200
        assert archived.json()["ok"] is True
        archived_first = archived.json()["data"]["scene"]
        plan_after_first_archive = archived.json()["data"]["plan"]

        archived_second = client.post(
            f"/api/v1/video-studio/plans/{plan['id']}/scenes/{second_scene['id']}/archive",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": second_scene["revision"], "idempotency_key": "video-archive-order-scene-two-0001"},
        )
        assert archived_second.status_code == 200
        assert archived_second.json()["ok"] is True
        plan_after_second_archive = archived_second.json()["data"]["plan"]

        reordered = client.post(
            f"/api/v1/video-studio/plans/{plan['id']}/scenes/reorder",
            headers={"X-CSRF-Token": csrf},
            json={
                "scene_ids": [third_scene["id"]],
                "expected_revision": plan_after_second_archive["revision"],
                "idempotency_key": "video-archive-order-reorder-0001",
            },
        )
        assert reordered.status_code == 200
        assert reordered.json()["ok"] is True

        restored = client.post(
            f"/api/v1/video-studio/plans/{plan['id']}/scenes/{first_scene['id']}/restore",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": archived_first["revision"], "idempotency_key": "video-archive-order-restore-0001"},
        )
        assert restored.status_code == 200
        assert restored.json()["ok"] is True

        detail = client.get(f"/api/v1/video-studio/plans/{plan['id']}")
        assert detail.status_code == 200
        active = [scene for scene in detail.json()["data"]["scenes"] if scene["state"] == "active"]
        assert [scene["id"] for scene in active] == [third_scene["id"], first_scene["id"]]
        assert [scene["ordinal"] for scene in active] == [1, 2]
