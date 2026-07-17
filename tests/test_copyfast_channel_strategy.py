"""Focused security and lifecycle contracts for Web-native Channel Strategy."""

from __future__ import annotations

import importlib
import sqlite3
import sys

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry", "copyfast_api",
    "copyfast_pages", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations", "copyfast_image_studio",
    "copyfast_document_workspace", "copyfast_chat_workspace", "copyfast_analytics_workspace", "copyfast_workboard",
    "copyfast_memory", "copyfast_prompt_library", "copyfast_music_media", "copyfast_content_studio",
    "copyfast_channel_strategy", "copyfast_trend_research", "copyfast_media_factory", "copyfast_voice_studio",
    "copyfast_video_studio", "copyfast_subtitle_workspace", "copyfast_support", "copyfast_autopilot",
    "copyfast_reliability", "copyfast_notification_center",
]

BOUNDARY_FIELDS = {
    "telegram_state_changed", "bot_called", "bridge_called", "channel_url_fetched", "social_platform_called",
    "provider_called", "job_created", "wallet_mutated", "payment_started", "asset_saved",
    "publish_action_created", "delivery_created", "analytics_claim_verified",
}


def make_client(tmp_path, monkeypatch, *, enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "channel-strategy-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "channel-strategy-test-session-secret")
    monkeypatch.setenv("WEBAPP_CHANNEL_STRATEGY_ENABLED", "true" if enabled else "false")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Channel Strategy Owner"},
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def profile_payload(key: str, **overrides) -> dict:
    value = {
        "channel_name": "Bếp nhỏ mỗi ngày",
        "platform": "tiktok",
        "channel_url": "https://example.com/channel/be-nho",
        "niche": "Món ăn đơn giản cho người bận rộn",
        "target_audience": "Người đi làm muốn tự nấu ăn nhanh và rõ nguyên liệu",
        "content_style": "Hướng dẫn thực tế, dễ làm và có kiểm tra claim",
        "tone": "Ấm áp, ngắn gọn",
        "language": "vi",
        "allowed_topics": ["bữa sáng nhanh", "meal prep"],
        "blocked_topics": ["claim chữa bệnh"],
        "brand_keywords": ["Bếp nhỏ"],
        "cta_default": "Lưu lại để nấu thử vào cuối tuần.",
        "affiliate_allowed": False,
        "product_categories": ["dụng cụ bếp"],
        "posting_frequency": "2 video mỗi tuần, tự review trước khi đăng",
        "preferred_aspect_ratio": "9:16",
        "preferred_duration_seconds": 30,
        "primary_goal": "community",
        "notes": "Ưu tiên nguyên liệu dễ mua, không cam kết hiệu quả sức khỏe.",
        "idempotency_key": key,
    }
    value.update(overrides)
    return value


def create_profile(client: TestClient, csrf: str, key: str = "channel-strategy-create-0001", **overrides) -> dict:
    response = client.post("/api/v1/channel-strategy/profiles", headers={"X-CSRF-Token": csrf}, json=profile_payload(key, **overrides))
    assert response.status_code == 200 and response.json()["ok"] is True
    return response.json()["data"]["profile"]


def counts(db_path) -> dict[str, int]:
    with sqlite3.connect(db_path) as conn:
        return {
            table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in (
                "web_channel_strategy_profiles", "web_channel_strategy_profile_versions",
                "web_channel_strategy_events", "web_idempotency", "web_audit_events",
            )
        }


def test_channel_strategy_requires_signed_csrf_bounded_body_and_content_free_replay(tmp_path, monkeypatch):
    db_path = tmp_path / "channel-strategy-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        assert client.get("/api/v1/channel-strategy/summary").status_code == 401
        csrf = login(client, "channel-auth@example.com")
        raw = profile_payload("channel-strategy-create-0001")
        assert client.post("/api/v1/channel-strategy/profiles", json=raw).status_code == 403
        oversized = client.post(
            "/api/v1/channel-strategy/profiles",
            headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
            content=b'{"channel_name":"' + (b"x" * (33 * 1024)) + b'"}',
        )
        assert oversized.status_code == 413
        assert oversized.json()["error_code"] == "WEB_CHANNEL_STRATEGY_BODY_TOO_LARGE"
        assert oversized.headers["Cache-Control"] == "no-store, private"

        created = client.post("/api/v1/channel-strategy/profiles", headers={"X-CSRF-Token": csrf}, json=raw)
        assert created.status_code == 200 and created.json()["ok"] is True
        created_data = created.json()["data"]
        profile_id = created_data["profile"]["id"]
        assert set(created_data["profile"]) == {"id", "revision", "state"}
        assert "Bếp nhỏ" not in created.text
        assert created_data["execution"] == "web_native_channel_strategy_profile_only"
        assert created_data["profile_persisted"] is True
        assert all(created_data[field] is False for field in BOUNDARY_FIELDS)

        replay = client.post("/api/v1/channel-strategy/profiles", headers={"X-CSRF-Token": csrf}, json=raw)
        assert replay.status_code == 200
        assert replay.json()["data"] == created_data
        collision = client.post(
            "/api/v1/channel-strategy/profiles",
            headers={"X-CSRF-Token": csrf},
            json=profile_payload("channel-strategy-create-0001", channel_name="Kênh khác"),
        )
        assert collision.status_code == 409
        assert counts(db_path)["web_channel_strategy_profiles"] == 1
        assert profile_id


def test_channel_strategy_is_owner_scoped_revisioned_and_archivable(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf_owner = login(client, "channel-owner@example.com")
        created = create_profile(client, csrf_owner)
        profile_id = created["id"]
        detail = client.get(f"/api/v1/channel-strategy/profiles/{profile_id}")
        assert detail.status_code == 200 and detail.json()["ok"] is True
        profile = detail.json()["data"]["profile"]
        assert profile["channel_name"] == "Bếp nhỏ mỗi ngày"
        assert profile["allowed_topics"] == ["bữa sáng nhanh", "meal prep"]
        assert len(detail.json()["data"]["versions"]) == 1

        csrf_other = login(client, "channel-other@example.com")
        invisible = client.get(f"/api/v1/channel-strategy/profiles/{profile_id}")
        assert invisible.status_code == 200 and invisible.json()["ok"] is False
        assert invisible.json()["error_code"] == "WEB_CHANNEL_STRATEGY_PROFILE_NOT_FOUND"
        other_preview = client.post(
            f"/api/v1/channel-strategy/profiles/{profile_id}/strategy-preview",
            headers={"X-CSRF-Token": csrf_other}, json={"expected_revision": 1},
        )
        assert other_preview.status_code == 200 and other_preview.json()["ok"] is False

        owner_login = client.post("/api/v1/auth/login", json={"email": "channel-owner@example.com", "password": "correct-horse-battery-staple"})
        csrf_owner = owner_login.json()["data"]["csrf_token"]
        update = client.patch(
            f"/api/v1/channel-strategy/profiles/{profile_id}",
            headers={"X-CSRF-Token": csrf_owner},
            json=profile_payload("channel-strategy-update-0001", expected_revision=1, primary_goal="sales", affiliate_allowed=True),
        )
        assert update.status_code == 200 and update.json()["ok"] is True
        assert update.json()["data"]["profile"]["revision"] == 2
        stale = client.patch(
            f"/api/v1/channel-strategy/profiles/{profile_id}",
            headers={"X-CSRF-Token": csrf_owner},
            json=profile_payload("channel-strategy-update-stale-0001", expected_revision=1),
        )
        assert stale.status_code == 200 and stale.json()["error_code"] == "WEB_CHANNEL_STRATEGY_REVISION_CONFLICT"

        archived = client.post(
            f"/api/v1/channel-strategy/profiles/{profile_id}/archive",
            headers={"X-CSRF-Token": csrf_owner},
            json={"expected_revision": 2, "idempotency_key": "channel-strategy-archive-0001"},
        )
        assert archived.status_code == 200 and archived.json()["data"]["profile"]["state"] == "archived"
        restored = client.post(
            f"/api/v1/channel-strategy/profiles/{profile_id}/restore",
            headers={"X-CSRF-Token": csrf_owner},
            json={"expected_revision": 3, "idempotency_key": "channel-strategy-restore-0001"},
        )
        assert restored.status_code == 200 and restored.json()["data"]["profile"]["state"] == "active"


def test_channel_strategy_preview_is_deterministic_profile_scoped_and_non_execution(tmp_path, monkeypatch):
    db_path = tmp_path / "channel-strategy-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "channel-preview@example.com")
        profile = create_profile(client, csrf)
        before = counts(db_path)
        path = f"/api/v1/channel-strategy/profiles/{profile['id']}/strategy-preview"
        first = client.post(path, headers={"X-CSRF-Token": csrf}, json={"expected_revision": 1})
        second = client.post(path, headers={"X-CSRF-Token": csrf}, json={"expected_revision": 1})
        assert first.status_code == 200 and second.status_code == 200
        assert first.json()["data"]["strategy"] == second.json()["data"]["strategy"]
        data = first.json()["data"]
        assert data["execution"] == "web_native_deterministic_channel_strategy_preview_only"
        assert data["profile_persisted"] is False
        assert data["strategy_persisted"] is False
        assert all(data[field] is False for field in BOUNDARY_FIELDS)
        assert data["strategy"]["profile_id"] == profile["id"]
        assert len(data["strategy"]["content_pillars"]) == 3
        after = counts(db_path)
        assert after["web_channel_strategy_profiles"] == before["web_channel_strategy_profiles"]
        assert after["web_channel_strategy_profile_versions"] == before["web_channel_strategy_profile_versions"]
        assert after["web_idempotency"] == before["web_idempotency"]
        assert after["web_channel_strategy_events"] == before["web_channel_strategy_events"] + 2


def test_channel_strategy_rejects_unsafe_or_extra_input_and_respects_maintenance(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "channel-guard@example.com")
        for invalid in (
            profile_payload("channel-strategy-invalid-0001", content_style="phong cách của nghệ sĩ nổi tiếng"),
            profile_payload("channel-strategy-invalid-0002", cta_default="cam kết 100% tăng follow"),
            profile_payload("channel-strategy-invalid-0003", channel_url="http://example.com/not-https"),
            profile_payload("channel-strategy-invalid-0004", allowed_topics="không phải danh sách"),
            profile_payload("channel-strategy-invalid-0005", unexpected_provider="x"),
        ):
            assert client.post("/api/v1/channel-strategy/profiles", headers={"X-CSRF-Token": csrf}, json=invalid).status_code == 422

    with make_client(tmp_path, monkeypatch, enabled=False) as disabled:
        csrf = login(disabled, "channel-disabled@example.com")
        response = disabled.post("/api/v1/channel-strategy/profiles", headers={"X-CSRF-Token": csrf}, json=profile_payload("channel-strategy-disabled-0001"))
        assert response.status_code == 503
        assert "WEBAPP_CHANNEL_STRATEGY_ENABLED" in response.json()["message"]


def test_channel_strategy_profile_library_paginates_stably_and_keeps_filters_owner_scoped(tmp_path, monkeypatch):
    """Offset pages must be a stable partition of one signed account's filter.

    The profile library is private positioning metadata.  This pins bounded
    offset pagination so a browser cannot repeat page zero when it asks for a
    next page, and so a transient query cannot pull records from another
    account.
    """
    with make_client(tmp_path, monkeypatch) as owner:
        csrf = login(owner, "channel-pages-owner@example.com")
        created = [
            create_profile(
                owner,
                csrf,
                f"channel-pages-create-{index:04d}",
                channel_name=f"Pagination channel profile {index}",
                niche="Pagination niche private",
            )
            for index in range(1, 4)
        ]
        create_profile(
            owner,
            csrf,
            "channel-pages-create-nomatch-0001",
            channel_name="Private strategy unrelated to page query",
            niche="Unrelated private niche",
        )

        first = owner.get(
            "/api/v1/channel-strategy/profiles",
            params={"state": "all", "q": "Pagination channel", "limit": 1, "offset": 0},
        )
        assert first.status_code == 200 and first.json()["ok"] is True
        first_data = first.json()["data"]
        assert first_data["filters"]["state"] == "all"
        assert first_data["pagination"] == {"limit": 1, "offset": 0, "returned": 1}
        assert first_data["has_more"] is True and first_data["next_offset"] == 1

        second = owner.get(
            "/api/v1/channel-strategy/profiles",
            params={"state": "all", "q": "Pagination channel", "limit": 1, "offset": first_data["next_offset"]},
        )
        assert second.status_code == 200 and second.json()["ok"] is True
        second_data = second.json()["data"]
        assert second_data["filters"]["state"] == "all"
        assert second_data["pagination"] == {"limit": 1, "offset": 1, "returned": 1}
        assert second_data["has_more"] is True and second_data["next_offset"] == 2
        assert first_data["items"][0]["id"] != second_data["items"][0]["id"]

        third = owner.get(
            "/api/v1/channel-strategy/profiles",
            params={"state": "all", "q": "Pagination channel", "limit": 1, "offset": second_data["next_offset"]},
        )
        assert third.status_code == 200 and third.json()["ok"] is True
        third_data = third.json()["data"]
        assert third_data["pagination"] == {"limit": 1, "offset": 2, "returned": 1}
        assert third_data["has_more"] is False and third_data["next_offset"] is None
        assert {item["id"] for item in first_data["items"] + second_data["items"] + third_data["items"]} == {
            profile["id"] for profile in created
        }

        # A repeated first-page request must retain the same deterministic
        # updated_at/id ordering rather than moving records between pages.
        repeat = owner.get(
            "/api/v1/channel-strategy/profiles",
            params={"state": "all", "q": "Pagination channel", "limit": 1, "offset": 0},
        )
        assert repeat.status_code == 200
        assert repeat.json()["data"]["items"] == first_data["items"]

        with make_client(tmp_path, monkeypatch) as other:
            csrf_other = login(other, "channel-pages-other@example.com")
            foreign = create_profile(
                other,
                csrf_other,
                "channel-pages-other-create-0001",
                channel_name="Pagination channel profile foreign",
                niche="Pagination niche foreign",
            )
            owner_ids = {
                item["id"]
                for item in owner.get(
                    "/api/v1/channel-strategy/profiles",
                    params={"state": "all", "q": "Pagination channel", "limit": 100, "offset": 0},
                ).json()["data"]["items"]
            }
            assert foreign["id"] not in owner_ids
