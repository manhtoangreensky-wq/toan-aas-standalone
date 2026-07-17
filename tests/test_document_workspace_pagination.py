"""Focused privacy and pagination contracts for Document Workspace briefs.

The Document Workspace library is a Web-native, signed-account authoring
surface.  Its list can grow independently of Document Operations, so this
test pins the small public contract required to browse it safely: server-side
state/search filtering, bounded offset pagination, owner isolation and list
redaction.  It deliberately does not exercise file execution, providers, Bot
state, wallets or payments.
"""

from __future__ import annotations

import importlib
from pathlib import Path
import sqlite3
import sys

from fastapi.testclient import TestClient


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")

MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_api", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations", "copyfast_image_studio",
    "copyfast_document_workspace", "copyfast_memory", "copyfast_prompt_library", "copyfast_music_media",
    "copyfast_content_studio", "copyfast_voice_studio", "copyfast_video_studio", "copyfast_subtitle_workspace",
    "copyfast_support",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "document-workspace-pagination.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "document-workspace-pagination-session-secret")
    monkeypatch.setenv("WEBAPP_DOCUMENT_WORKSPACE_ENABLED", "true")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Document Pagination Owner"},
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def workspace_payload(key: str, title: str, *, private_tail: str = "") -> dict:
    return {
        "title": title,
        "document_type": "pdf",
        # The tail is intentionally beyond the list excerpt boundary.  A list
        # can find it server-side, but must not return the full brief body.
        "source_summary": ("Nguồn nội bộ để kiểm tra phân trang an toàn. " * 20) + private_tail,
        "objective": "Self-review document brief có metadata rõ ràng, không tạo file hay output.",
        "language": "vi",
        "target_language": "",
        "tags": ["pagination", "document"],
        "project_id": "",
        "idempotency_key": key,
    }


def create_workspace(client: TestClient, csrf: str, key: str, title: str, *, private_tail: str = "") -> dict:
    response = client.post(
        "/api/v1/document-workspace/workspaces",
        headers={"X-CSRF-Token": csrf},
        json=workspace_payload(key, title, private_tail=private_tail),
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    return response.json()["data"]["workspace"]


def transition_workspace(client: TestClient, csrf: str, workspace: dict, state: str, key: str) -> dict:
    response = client.post(
        f"/api/v1/document-workspace/workspaces/{workspace['id']}/lifecycle",
        headers={"X-CSRF-Token": csrf},
        json={"state": state, "expected_revision": workspace["revision"], "idempotency_key": key},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    changed = response.json()["data"]["workspace"]
    assert changed["state"] == state
    return changed


def set_listing_order(db_path: Path, workspaces: list[dict]) -> None:
    """Set known public sort keys without reading private rows from SQLite."""
    with sqlite3.connect(db_path) as connection:
        for index, workspace in enumerate(workspaces, start=1):
            connection.execute(
                "UPDATE web_document_workspaces SET updated_at=? WHERE id=?",
                (f"2026-07-16T00:00:0{index}+00:00", workspace["id"]),
            )


def assert_public_listing_item(item: dict, private_tail: str) -> None:
    forbidden = {
        "account_id", "canonical_user_id", "source_summary", "objective", "tags_json",
        "storage_key", "sha256", "request_fingerprint", "idempotency_key", "path",
        "filesystem", "provider", "wallet", "payment", "payos", "job",
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
        assert_public_listing_item(item, private_tail)
    return data


def test_document_workspace_library_paginates_current_filters_without_owner_or_brief_leaks(tmp_path, monkeypatch) -> None:
    private_tail = "PRIVATE_DOCUMENT_WORKSPACE_BODY_MUST_NOT_APPEAR_IN_LIST"
    database = tmp_path / "document-workspace-pagination.db"
    with make_client(tmp_path, monkeypatch) as owner:
        csrf = login(owner, "document-workspace-pagination-owner@example.com")
        draft_oldest = create_workspace(
            owner, csrf, "document-workspace-page-draft-0001", "Needle Document Draft oldest", private_tail=private_tail,
        )
        review_middle = create_workspace(
            owner, csrf, "document-workspace-page-review-0001", "Needle Document Review middle",
        )
        review_middle = transition_workspace(
            owner, csrf, review_middle, "review", "document-workspace-page-review-state-0001",
        )
        approved_newest = create_workspace(
            owner, csrf, "document-workspace-page-approved-0001", "Needle Document Approved newest",
        )
        approved_newest = transition_workspace(
            owner, csrf, approved_newest, "review", "document-workspace-page-approved-review-0001",
        )
        approved_newest = transition_workspace(
            owner, csrf, approved_newest, "approved", "document-workspace-page-approved-state-0001",
        )
        archived = create_workspace(
            owner, csrf, "document-workspace-page-archived-0001", "Needle Document Archived",
        )
        archived = transition_workspace(
            owner, csrf, archived, "archived", "document-workspace-page-archived-state-0001",
        )
        set_listing_order(database, [draft_oldest, review_middle, approved_newest, archived])

        # The existing `active` state continues to mean all non-archived
        # briefs.  Search occurs on the server before offset pagination.
        first = owner.get(
            "/api/v1/document-workspace/workspaces",
            params={"state": "active", "q": "Needle Document", "limit": 2, "offset": 0},
        )
        assert_page(
            first,
            [approved_newest["id"], review_middle["id"]],
            has_more=True,
            next_offset=2,
            private_tail=private_tail,
        )
        second = owner.get(
            "/api/v1/document-workspace/workspaces",
            params={"state": "active", "q": "Needle Document", "limit": 2, "offset": 2},
        )
        assert_page(second, [draft_oldest["id"]], has_more=False, next_offset=None, private_tail=private_tail)

        # A lifecycle filter must stay server-side and compose with search.
        review = owner.get(
            "/api/v1/document-workspace/workspaces",
            params={"state": "review", "q": "Needle Document", "limit": 2, "offset": 0},
        )
        assert_page(review, [review_middle["id"]], has_more=False, next_offset=None, private_tail=private_tail)
        archived_page = owner.get(
            "/api/v1/document-workspace/workspaces",
            params={"state": "archived", "q": "Needle Document", "limit": 2, "offset": 0},
        )
        assert_page(archived_page, [archived["id"]], has_more=False, next_offset=None, private_tail=private_tail)

        # A server-side search can locate a long private body, but a public
        # library row remains an excerpt-only projection.
        private_search = owner.get(
            "/api/v1/document-workspace/workspaces",
            params={"state": "active", "q": private_tail, "limit": 2, "offset": 0},
        )
        assert_page(private_search, [draft_oldest["id"]], has_more=False, next_offset=None, private_tail=private_tail)

        for offset in ("-1", "10001", "not-an-offset"):
            invalid = owner.get(
                "/api/v1/document-workspace/workspaces",
                params={"state": "active", "q": "Needle Document", "limit": 2, "offset": offset},
            )
            assert invalid.status_code == 422
            assert private_tail not in invalid.text

    with make_client(tmp_path, monkeypatch) as other:
        login(other, "document-workspace-pagination-other@example.com")
        hidden_active = other.get(
            "/api/v1/document-workspace/workspaces",
            params={"state": "active", "q": "Needle Document", "limit": 2, "offset": 0},
        )
        assert_page(hidden_active, [], has_more=False, next_offset=None, private_tail=private_tail)
        hidden_archived = other.get(
            "/api/v1/document-workspace/workspaces",
            params={"state": "archived", "q": "Needle Document", "limit": 2, "offset": 0},
        )
        assert_page(hidden_archived, [], has_more=False, next_offset=None, private_tail=private_tail)


def test_document_workspace_portal_keeps_filter_and_page_state_in_memory() -> None:
    """The library must never recover a prior account's page from browser storage."""
    for token in (
        "DOCUMENT_WORKSPACE_LIST_LIMIT = 50",
        "DOCUMENT_WORKSPACE_MAX_LIST_OFFSET = 10000",
        "function documentWorkspaceFilterPayload",
        "function documentWorkspaceListOffset",
        "function documentWorkspaceListPath",
        "function documentWorkspaceListingProjection",
        "documentWorkspaceFilter",
        "documentWorkspaceListing",
        'action === "document-workspace-filter"',
        'action === "document-workspace-filter-clear"',
        'action === "document-workspace-page"',
        "fields.__documentWorkspaceFilter",
        "fields.__documentWorkspaceOffset",
    ):
        assert token in INTEGRATION

    for token in (
        "documentWorkspaceFilter",
        "documentWorkspaceListing",
        "document-workspace-filter",
        "document-workspace-filter-clear",
        "document-workspace-page",
        "data-document-workspace-filter",
        "data-document-workspace-offset",
    ):
        assert token in PORTAL

    hydration = INTEGRATION[
        INTEGRATION.index("function documentWorkspaceFilterPayload"):INTEGRATION.index("async function hydrateDocumentWorkspaceDetail")
    ]
    assert "api(documentWorkspaceListPath(filter, offset))" in hydration
    assert "localStorage" not in hydration
    assert "bridge_request" not in hydration
    assert "CORE_BRIDGE" not in hydration
