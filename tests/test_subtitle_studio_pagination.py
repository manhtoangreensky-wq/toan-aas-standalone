"""Focused list and hydration contracts for the Web-native Subtitle Studio.

The subtitle project library is private account data.  These checks pin only
the pagination, privacy and stale-read behavior needed to browse that library
safely; they deliberately do not exercise providers, Bot workflows, media,
payments, or visual redesign work.
"""

from __future__ import annotations

import importlib
from pathlib import Path
import re
import sqlite3
import sys

from fastapi.testclient import TestClient


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "copyfast_subtitle_workspace.py").read_text(encoding="utf-8")


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_api", "copyfast_pages", "copyfast_projects", "copyfast_assets",
    "copyfast_project_packages", "copyfast_document_operations", "copyfast_image_runtime",
    "copyfast_image_operations", "copyfast_memory", "copyfast_prompt_library",
    "copyfast_music_media", "copyfast_content_studio", "copyfast_voice_studio",
    "copyfast_video_studio", "copyfast_subtitle_workspace", "copyfast_support",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "subtitle-studio-pagination.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "subtitle-studio-pagination-session-secret")
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
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Subtitle Pagination Owner"},
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def project_payload(key: str, title: str, *, private_tail: str = "") -> dict:
    return {
        "title": title,
        "source_language": "vi",
        "target_language": "en",
        "caption_format": "srt",
        # The query must be able to locate a private context server-side, but
        # the library response is deliberately an excerpt-only projection.
        "context": ("Bối cảnh nội bộ dùng để kiểm tra subtitle project riêng tư. " * 12) + private_tail,
        "tags": ["pagination", "subtitle"],
        "project_id": "",
        "intent": "translation",
        "idempotency_key": key,
    }


def create_project(client: TestClient, csrf: str, key: str, title: str, *, private_tail: str = "") -> dict:
    response = client.post(
        "/api/v1/subtitle-studio/projects",
        headers={"X-CSRF-Token": csrf},
        json=project_payload(key, title, private_tail=private_tail),
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    return response.json()["data"]["project"]


def transition_project(client: TestClient, csrf: str, project: dict, state: str, key: str) -> dict:
    response = client.post(
        f"/api/v1/subtitle-studio/projects/{project['id']}/lifecycle",
        headers={"X-CSRF-Token": csrf},
        json={"state": state, "expected_revision": project["revision"], "idempotency_key": key},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    changed = response.json()["data"]["project"]
    assert changed["state"] == state
    return changed


def set_listing_order(database: Path, projects: list[dict]) -> None:
    """Pin deterministic sort keys without inspecting private stored content."""
    with sqlite3.connect(database) as connection:
        for index, project in enumerate(projects, start=1):
            connection.execute(
                "UPDATE web_subtitle_projects SET updated_at=? WHERE id=?",
                (f"2026-07-16T00:00:0{index}+00:00", project["id"]),
            )


def assert_public_project(item: dict, private_tail: str) -> None:
    forbidden = {
        "account_id", "context", "tags_json", "request_fingerprint", "idempotency_key",
        "storage_key", "path", "filesystem", "provider", "wallet", "payment", "payos", "job",
    }
    assert not (forbidden & set(item))
    assert private_tail not in repr(item)


def assert_page(response, expected_ids: list[str], *, has_more: bool, next_offset: int | None, private_tail: str) -> dict:
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert [item["id"] for item in data["items"]] == expected_ids
    assert data["has_more"] is has_more
    assert data["next_offset"] == next_offset
    assert private_tail not in response.text
    for item in data["items"]:
        assert_public_project(item, private_tail)
    return data


def test_subtitle_project_library_paginates_current_filters_without_owner_or_context_leaks(tmp_path, monkeypatch) -> None:
    """List filtering happens before a bounded, stable owner-only page read."""
    private_tail = "PRIVATE_SUBTITLE_CONTEXT_MUST_NOT_APPEAR_IN_LIBRARY"
    database = tmp_path / "subtitle-studio-pagination.db"
    with make_client(tmp_path, monkeypatch) as owner:
        csrf = login(owner, "subtitle-pagination-owner@example.com")
        draft_oldest = create_project(
            owner, csrf, "subtitle-pagination-draft-0001", "Needle Subtitle Draft oldest", private_tail=private_tail,
        )
        review_middle = create_project(
            owner, csrf, "subtitle-pagination-review-0001", "Needle Subtitle Review middle",
        )
        review_middle = transition_project(
            owner, csrf, review_middle, "review", "subtitle-pagination-review-state-0001",
        )
        approved_newest = create_project(
            owner, csrf, "subtitle-pagination-approved-0001", "Needle Subtitle Approved newest",
        )
        approved_newest = transition_project(
            owner, csrf, approved_newest, "review", "subtitle-pagination-approved-review-0001",
        )
        approved_newest = transition_project(
            owner, csrf, approved_newest, "approved", "subtitle-pagination-approved-state-0001",
        )
        archived = create_project(
            owner, csrf, "subtitle-pagination-archived-0001", "Needle Subtitle Archived",
        )
        archived = transition_project(
            owner, csrf, archived, "archived", "subtitle-pagination-archived-state-0001",
        )
        set_listing_order(database, [draft_oldest, review_middle, approved_newest, archived])

        # `active` stays the existing all-non-archived view.  A stable
        # `updated_at DESC, id DESC` order is required before offset slicing.
        first = owner.get(
            "/api/v1/subtitle-studio/projects",
            params={"state": "active", "q": "Needle Subtitle", "limit": 2, "offset": 0},
        )
        assert_page(
            first,
            [approved_newest["id"], review_middle["id"]],
            has_more=True,
            next_offset=2,
            private_tail=private_tail,
        )
        second = owner.get(
            "/api/v1/subtitle-studio/projects",
            params={"state": "active", "q": "Needle Subtitle", "limit": 2, "offset": 2},
        )
        assert_page(second, [draft_oldest["id"]], has_more=False, next_offset=None, private_tail=private_tail)

        review = owner.get(
            "/api/v1/subtitle-studio/projects",
            params={"state": "review", "q": "Needle Subtitle", "limit": 2, "offset": 0},
        )
        assert_page(review, [review_middle["id"]], has_more=False, next_offset=None, private_tail=private_tail)
        archived_page = owner.get(
            "/api/v1/subtitle-studio/projects",
            params={"state": "archived", "q": "Needle Subtitle", "limit": 2, "offset": 0},
        )
        assert_page(archived_page, [archived["id"]], has_more=False, next_offset=None, private_tail=private_tail)

        # The server may search private context, but it must never echo the
        # searched text or full context in a list projection.
        private_search = owner.get(
            "/api/v1/subtitle-studio/projects",
            params={"state": "active", "q": private_tail, "limit": 2, "offset": 0},
        )
        assert_page(private_search, [draft_oldest["id"]], has_more=False, next_offset=None, private_tail=private_tail)

        for offset in ("-1", "10001", "not-an-offset"):
            invalid = owner.get(
                "/api/v1/subtitle-studio/projects",
                params={"state": "active", "q": "Needle Subtitle", "limit": 2, "offset": offset},
            )
            assert invalid.status_code == 422
            assert private_tail not in invalid.text

    with make_client(tmp_path, monkeypatch) as other:
        login(other, "subtitle-pagination-other@example.com")
        hidden_active = other.get(
            "/api/v1/subtitle-studio/projects",
            params={"state": "active", "q": "Needle Subtitle", "limit": 2, "offset": 0},
        )
        assert_page(hidden_active, [], has_more=False, next_offset=None, private_tail=private_tail)
        hidden_archived = other.get(
            "/api/v1/subtitle-studio/projects",
            params={"state": "archived", "q": "Needle Subtitle", "limit": 2, "offset": 0},
        )
        assert_page(hidden_archived, [], has_more=False, next_offset=None, private_tail=private_tail)


def _subtitle_hydration() -> str:
    start = INTEGRATION.index("async function hydrateSubtitleStudio(overrides)")
    return INTEGRATION[start:INTEGRATION.index("async function hydrateSupportDesk", start)]


def test_subtitle_project_library_client_keeps_filtered_page_in_memory() -> None:
    """The list may never resurrect a prior account's default/old page."""
    for token in (
        "SUBTITLE_STUDIO_LIST_LIMIT = 50",
        "SUBTITLE_STUDIO_MAX_LIST_OFFSET = 10_000",
        "function subtitleStudioListOptions(overrides)",
        "function subtitleStudioProjectsPath(options)",
        "function subtitleStudioPagination(data, requested)",
        "subtitleStudioListing",
    ):
        assert token in INTEGRATION

    hydration = _subtitle_hydration()
    assert "api(subtitleStudioProjectsPath(requested))" in hydration
    assert "localStorage" not in hydration
    assert "bridge_request" not in hydration
    assert "CORE_BRIDGE" not in hydration

    # State normalization is not visual state: it keeps the signed list
    # projection (including its server pagination) through a render.
    start = PORTAL.index("// Subtitle Studio and Format Lab are a separate")
    end = PORTAL.index("// Image Creative Studio is a distinct", start)
    normalizer = PORTAL[start:end]
    assert "subtitleStudioListing:" in normalizer
    assert "source.subtitleStudioListing" in normalizer


def test_subtitle_hydration_fences_session_list_detail_and_current_signed_path() -> None:
    """Late private reads cannot cross a logout, account switch, or route change."""
    for name in (
        "subtitleStudioSessionEpoch",
        "subtitleStudioListHydrationEpoch",
        "subtitleStudioDetailHydrationEpoch",
    ):
        assert re.search(r"(?:\+\+|\+=\s*1)" + re.escape(name), INTEGRATION), name
    assert INTEGRATION.count("subtitleStudioRequestIsCurrent(") >= 3
    assert "const sessionEpoch = subtitleStudioSessionEpoch;" in INTEGRATION
    assert "const requestEpoch = ++subtitleStudioListHydrationEpoch;" in INTEGRATION
    assert "const requestEpoch = ++subtitleStudioDetailHydrationEpoch;" in INTEGRATION
    assert "if (!subtitleStudioRequestIsCurrent(" in INTEGRATION
    assert "currentPortalPath()" in INTEGRATION

    helpers_start = INTEGRATION.index("function subtitleStudioRequestIsCurrent(")
    helpers = INTEGRATION[helpers_start:INTEGRATION.index("async function hydrateSubtitleStudio", helpers_start)]
    assert "sessionEpoch === subtitleStudioSessionEpoch" in helpers
    assert "currentPortalPath() === expectedPath" in helpers
    assert "base().subtitleStudioEnabled === true" in helpers
    assert "base().session" in helpers and "authenticated === true" in helpers


def test_subtitle_client_keeps_all_server_supported_cues_for_exact_reorder() -> None:
    """A 500-cue project must not be silently truncated to 250 in the browser."""
    assert "MAX_CUES_PER_PROJECT = 500" in WORKSPACE
    assert "max_length=MAX_CUES_PER_PROJECT" in WORKSPACE
    detail_start = WORKSPACE.index("def _project_detail(")
    detail_source = WORKSPACE[detail_start:WORKSPACE.index("def _estimate(", detail_start)]
    assert "MAX_CUES_PER_PROJECT" in detail_source

    hydration = _subtitle_hydration()
    assert "const SUBTITLE_STUDIO_CUE_LIMIT = 500;" in INTEGRATION
    assert ".slice(0, SUBTITLE_STUDIO_CUE_LIMIT)" in hydration
    assert ".slice(0, 250)" not in hydration

    assert "const SUBTITLE_STUDIO_CUE_LIMIT = 500;" in PORTAL
    detail_start = PORTAL.index("function renderSubtitleStudioDetail(")
    detail_surface = PORTAL[detail_start:PORTAL.index("function renderStudioDocumentEditor", detail_start)]
    assert ".slice(0, SUBTITLE_STUDIO_CUE_LIMIT)" in detail_surface
    assert ".slice(0, 250)" not in detail_surface

    reorder_start = INTEGRATION.index('if (action === "subtitle-cue-reorder")')
    reorder_end = INTEGRATION.index('if (action === "voice-direction-compose")', reorder_start)
    reorder = INTEGRATION[reorder_start:reorder_end]
    assert "projectDetail.cues" in reorder
    assert "const cueIds = activeCues.map" in reorder
    assert "cue_ids: cueIds" in reorder
