"""Focused contracts for private Document/Image Operation history pagination.

These tests deliberately exercise the public list endpoints with tiny real
artifacts.  They do not know storage-table shapes beyond setting deterministic
timestamps/failure codes after a verified operation has been created.  That
keeps the assertions focused on the browser-facing owner/pagination/redaction
contract rather than implementation details.
"""

from __future__ import annotations

from io import BytesIO
import importlib
from pathlib import Path
import sqlite3
import sys

from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")

MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_api", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations", "copyfast_pages",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "operation-history-pagination.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "operation-history-pagination-session-secret")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-web-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "20")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "100")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ROOT", str(tmp_path / "private-document-outputs"))
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_MAX_OUTPUT_MB", "20")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_QUOTA_MB", "100")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ROOT", str(tmp_path / "private-image-outputs"))
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_MAX_OUTPUT_MB", "20")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_QUOTA_MB", "100")
    monkeypatch.setenv("WEBAPP_IMAGE_RESIZE_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_IMAGE_ENHANCE_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_IMAGE_TO_PDF_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_PDF_TO_IMAGES_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_PDF_TO_WORD_ENABLED", "false")
    monkeypatch.delenv("WEBAPP_PROJECT_PACKAGE_ENABLED", raising=False)
    monkeypatch.delenv("WEBAPP_PROJECT_PACKAGE_ROOT", raising=False)
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
    assert client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Pagination Owner"},
    ).status_code == 200
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200
    return response.json()["data"]["csrf_token"]


def pdf_bytes(page_count: int = 3) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=144, height=144)
    stream = BytesIO()
    writer.write(stream)
    return stream.getvalue()


def image_bytes() -> bytes:
    image = Image.new("RGB", (160, 100), (16, 96, 212))
    stream = BytesIO()
    try:
        image.save(stream, format="JPEG", quality=95)
        return stream.getvalue()
    finally:
        image.close()


def upload_pdf(client: TestClient, csrf: str) -> dict:
    response = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "history-pdf-source-0001"},
        data={"display_name": "PDF pagination private"},
        files={"file": ("source.pdf", pdf_bytes(), "application/pdf")},
    )
    assert response.status_code == 200
    return response.json()["data"]["asset"]


def upload_image(client: TestClient, csrf: str) -> dict:
    response = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "history-image-source-0001"},
        data={"display_name": "Image pagination private"},
        files={"file": ("source.jpg", image_bytes(), "image/jpeg")},
    )
    assert response.status_code == 200
    return response.json()["data"]["asset"]


def split_pdf(client: TestClient, csrf: str, asset_id: str, page: int) -> dict:
    response = client.post(
        "/api/v1/document-operations/pdf-split",
        headers={"X-CSRF-Token": csrf},
        json={"source_asset_id": asset_id, "page_range": str(page), "idempotency_key": f"history-pdf-split-{page:04d}"},
    )
    assert response.status_code == 200
    return response.json()["data"]["operation"]


def resize_image(client: TestClient, csrf: str, asset_id: str, index: int) -> dict:
    response = client.post(
        "/api/v1/image-operations/resize",
        headers={"X-CSRF-Token": csrf},
        json={
            "source_asset_id": asset_id,
            "preset": "custom",
            "target_width": 128 + index,
            "target_height": 128 + index,
            "fit_mode": "crop",
            "idempotency_key": f"history-image-resize-{index:04d}",
        },
    )
    assert response.status_code == 200
    return response.json()["data"]["operation"]


def enhance_image(client: TestClient, csrf: str, asset_id: str, index: int) -> dict:
    preset = ("photo_clear_detail", "product_clean", "fresh_blue")[index - 1]
    response = client.post(
        "/api/v1/image-operations/enhance",
        headers={"X-CSRF-Token": csrf},
        json={
            "source_asset_id": asset_id,
            "preset": preset,
            "basic_upscale": False,
            "idempotency_key": f"history-image-enhance-{index:04d}",
        },
    )
    assert response.status_code == 200
    return response.json()["data"]["operation"]


def make_listing_order(db_path: Path, table: str, operations: list[dict], secret: str) -> None:
    assert table in {"web_document_operations", "web_image_operations"}
    with sqlite3.connect(db_path) as conn:
        for index, operation in enumerate(operations, start=1):
            conn.execute(
                f"UPDATE {table} SET updated_at=?, failure_code=? WHERE id=?",
                (f"2026-07-16T00:00:0{index}+00:00", secret, operation["id"]),
            )


def assert_private_listing(item: dict, secret: str) -> None:
    forbidden = {
        "_failure_code", "failure_code", "storage_key", "sha256", "source_sha256", "source_sha",
        "source_byte_size", "request_fingerprint", "path", "filesystem", "provider", "payment",
    }
    assert not (forbidden & set(item))
    assert secret not in repr(item)


def assert_paged_response(response, expected_ids: list[str], *, has_more: bool, next_offset: int | None, secret: str) -> dict:
    assert response.status_code == 200
    payload = response.json()
    data = payload["data"]
    assert [item["id"] for item in data["items"]] == expected_ids
    assert data["has_more"] is has_more
    assert data["next_offset"] == next_offset
    assert secret not in response.text
    for item in data["items"]:
        assert_private_listing(item, secret)
    return data


def test_document_operation_history_paginates_owner_scoped_redacted_rows(tmp_path, monkeypatch) -> None:
    secret = "PRIVATE_DOCUMENT_FAILURE_CODE_MUST_NOT_LEAK"
    db_path = tmp_path / "operation-history-pagination.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "document-history-owner@example.com")
        source = upload_pdf(client, csrf)
        operations = [split_pdf(client, csrf, source["id"], page) for page in (1, 2, 3)]
        make_listing_order(db_path, "web_document_operations", operations, secret)

        # The one-operation status endpoint shares the same public projection
        # shape.  Injected internal failure metadata must not reappear here
        # merely because the owner opens a history row.
        detail = client.get(f"/api/v1/document-operations/{operations[0]['id']}")
        assert detail.status_code == 200
        assert secret not in detail.text
        assert_private_listing(detail.json()["data"]["operation"], secret)

        first_page = client.get("/api/v1/document-operations?kind=pdf_split&limit=2&offset=0")
        assert_paged_response(
            first_page,
            [operations[2]["id"], operations[1]["id"]],
            has_more=True,
            next_offset=2,
            secret=secret,
        )
        second_page = client.get("/api/v1/document-operations?kind=pdf_split&limit=2&offset=2")
        assert_paged_response(second_page, [operations[0]["id"]], has_more=False, next_offset=None, secret=secret)

        # `limit` remains backward-compatible: old callers may pass 0 and
        # receive the legacy one-item clamp rather than an unbounded list.
        clamped = client.get("/api/v1/document-operations?kind=pdf_split&limit=0&offset=0")
        assert_paged_response(clamped, [operations[2]["id"]], has_more=True, next_offset=1, secret=secret)
        assert client.get("/api/v1/document-operations?kind=untrusted_operation&offset=0").status_code == 422
        for offset in ("-1", "10001", "not-an-offset"):
            assert client.get(f"/api/v1/document-operations?kind=pdf_split&limit=2&offset={offset}").status_code == 422

    with make_client(tmp_path, monkeypatch) as other:
        register_and_login(other, "document-history-other@example.com")
        hidden = other.get("/api/v1/document-operations?kind=pdf_split&limit=2&offset=0")
        assert_paged_response(hidden, [], has_more=False, next_offset=None, secret=secret)


def test_image_operation_history_paginates_resize_and_enhance_rows_without_cross_owner_leaks(tmp_path, monkeypatch) -> None:
    secret = "PRIVATE_IMAGE_FAILURE_CODE_MUST_NOT_LEAK"
    db_path = tmp_path / "operation-history-pagination.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "image-history-owner@example.com")
        source = upload_image(client, csrf)
        resize_operations = [resize_image(client, csrf, source["id"], index) for index in (1, 2, 3)]
        enhance_operations = [enhance_image(client, csrf, source["id"], index) for index in (1, 2, 3)]
        make_listing_order(db_path, "web_image_operations", resize_operations, secret)
        make_listing_order(db_path, "web_image_operations", enhance_operations, secret)

        resize_first = client.get("/api/v1/image-operations?kind=image_resize&limit=2&offset=0")
        assert_paged_response(
            resize_first,
            [resize_operations[2]["id"], resize_operations[1]["id"]],
            has_more=True,
            next_offset=2,
            secret=secret,
        )
        resize_second = client.get("/api/v1/image-operations?kind=image_resize&limit=2&offset=2")
        assert_paged_response(resize_second, [resize_operations[0]["id"]], has_more=False, next_offset=None, secret=secret)

        enhance_first = client.get("/api/v1/image-operations?kind=image_enhance&limit=2&offset=0")
        assert_paged_response(
            enhance_first,
            [enhance_operations[2]["id"], enhance_operations[1]["id"]],
            has_more=True,
            next_offset=2,
            secret=secret,
        )
        enhance_second = client.get("/api/v1/image-operations?kind=image_enhance&limit=2&offset=2")
        assert_paged_response(enhance_second, [enhance_operations[0]["id"]], has_more=False, next_offset=None, secret=secret)

        clamped = client.get("/api/v1/image-operations?kind=image_resize&limit=0&offset=0")
        assert_paged_response(clamped, [resize_operations[2]["id"]], has_more=True, next_offset=1, secret=secret)
        assert client.get("/api/v1/image-operations?kind=untrusted_operation&offset=0").status_code == 422
        for offset in ("-1", "10001", "not-an-offset"):
            assert client.get(f"/api/v1/image-operations?kind=image_resize&limit=2&offset={offset}").status_code == 422

        # The combined `/image/history` reader intentionally omits `kind`.
        # A future/untrusted DB value must not leak into that projection or
        # consume a pagination slot merely because this test can insert it
        # directly into SQLite.
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE web_image_operations SET kind=?, updated_at=? WHERE id=?",
                ("future_image_internal", "2026-07-16T00:00:09+00:00", resize_operations[2]["id"]),
            )
        expected_history_ids = {operation["id"] for operation in resize_operations[:2] + enhance_operations}
        combined_ids: list[str] = []
        for offset, expected_count, has_more, next_offset in ((0, 2, True, 2), (2, 2, True, 4), (4, 1, False, None)):
            response = client.get(f"/api/v1/image-operations?limit=2&offset={offset}")
            assert response.status_code == 200
            data = response.json()["data"]
            assert len(data["items"]) == expected_count
            assert data["has_more"] is has_more
            assert data["next_offset"] == next_offset
            assert secret not in response.text
            for item in data["items"]:
                assert item["kind"] in {"image_resize", "image_enhance"}
                assert_private_listing(item, secret)
                combined_ids.append(item["id"])
        assert set(combined_ids) == expected_history_ids
        assert resize_operations[2]["id"] not in combined_ids

    with make_client(tmp_path, monkeypatch) as other:
        register_and_login(other, "image-history-other@example.com")
        for kind in ("image_resize", "image_enhance"):
            hidden = other.get(f"/api/v1/image-operations?kind={kind}&limit=2&offset=0")
            assert_paged_response(hidden, [], has_more=False, next_offset=None, secret=secret)
        combined_hidden = other.get("/api/v1/image-operations?limit=2&offset=0")
        assert_paged_response(combined_hidden, [], has_more=False, next_offset=None, secret=secret)


def test_operation_history_portal_has_independent_in_memory_pagers_for_each_private_surface() -> None:
    for token in (
        "OPERATION_HISTORY_LIST_LIMIT = 50",
        "OPERATION_HISTORY_MAX_LIST_OFFSET = 10000",
        "function operationHistoryListOffset",
        "function operationHistoryListingProjection",
        "documentOperationListing",
        "imageOperationListing",
        "imageEnhanceOperationListing",
        "imageHistoryListing",
        'action === "document-operation-page"',
        'action === "image-operation-page"',
        'action === "image-enhance-operation-page"',
        'action === "image-history-operation-page"',
    ):
        assert token in INTEGRATION
    for token in (
        "documentOperationListing",
        "imageOperationListing",
        "imageEnhanceOperationListing",
        "document-operation-page",
        "image-operation-page",
        "image-enhance-operation-page",
        "data-document-operation-offset",
        "data-image-operation-offset",
        "data-image-enhance-operation-offset",
    ):
        assert token in PORTAL

    history_hydration = INTEGRATION[
        INTEGRATION.index("function operationHistoryListOffset"):INTEGRATION.index("async function hydrateProjectDetail")
    ]
    assert "localStorage" not in history_hydration
    assert "bridge_request" not in history_hydration
    assert "CORE_BRIDGE" not in history_hydration
