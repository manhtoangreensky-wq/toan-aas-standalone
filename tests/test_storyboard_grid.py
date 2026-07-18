"""Focused security and real-output contracts for Storyboard Grid Splitter.

The Web module intentionally retains only the deterministic crop maths from
the Bot's local ``crop_storyboard_grid_to_assets`` helper.  These tests keep
that useful parity while proving that Web output is private, verified and not
an operator/Bot shortcut.
"""

from __future__ import annotations

from io import BytesIO
import importlib
import json
from pathlib import Path
import sqlite3
import sys
from zipfile import ZipFile

from fastapi.testclient import TestClient
from PIL import Image


MODULES = [
    "app",
    "copyfast_db",
    "copyfast_auth",
    "copyfast_bridge",
    "copyfast_registry",
    "copyfast_api",
    "copyfast_projects",
    "copyfast_assets",
    "copyfast_project_packages",
    "copyfast_document_operations",
    "copyfast_image_runtime",
    "copyfast_image_operations",
    "copyfast_storyboard_grid",
    "copyfast_pages",
]


def make_client(tmp_path, monkeypatch, *, storyboard_grid_enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "copyfast-storyboard-grid-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-storyboard-grid-session-secret")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-web-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "20")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "100")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ROOT", str(tmp_path / "private-image-outputs"))
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_MAX_OUTPUT_MB", "30")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_QUOTA_MB", "100")
    monkeypatch.setenv("WEBAPP_STORYBOARD_GRID_ENABLED", "true" if storyboard_grid_enabled else "false")
    monkeypatch.setenv("WEBAPP_STORYBOARD_GRID_MAX_OUTPUT_MB", "30")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_IMAGE_TO_PDF_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_PDF_TO_WORD_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_ENABLED", "false")
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
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "correct-horse-battery-staple",
            "display_name": "Storyboard Grid Owner",
        },
    )
    assert registered.status_code == 200, registered.text
    return login(client, email)


def login(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["csrf_token"]


def grid_source_bytes(*, size: tuple[int, int] = (503, 205)) -> bytes:
    """A real non-uniform JPEG whose crop bounds are deliberately uneven."""
    image = Image.new("RGB", size, (16, 80, 196))
    pixels = image.load()
    try:
        for y in range(size[1]):
            for x in range(size[0]):
                pixels[x, y] = (
                    (x * 17 + y * 3) % 256,
                    (x * 5 + y * 11) % 256,
                    (x * 7 + y * 13) % 256,
                )
        stream = BytesIO()
        image.save(stream, format="JPEG", quality=95)
        return stream.getvalue()
    finally:
        image.close()


def upload_image(client: TestClient, csrf: str, *, key: str, body: bytes) -> dict:
    response = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data={"display_name": "Storyboard nguồn riêng tư"},
        files={"file": ("storyboard-source.jpg", body, "image/jpeg")},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["asset"]


def create_grid(
    client: TestClient,
    csrf: str,
    *,
    asset_id: str,
    key: str,
    episode: int = 3,
    rows: int = 2,
    cols: int = 5,
    start_scene: int = 10,
    trim_percent: float = 0.1,
):
    return client.post(
        "/api/v1/storyboard-grid",
        headers={"X-CSRF-Token": csrf},
        json={
            "source_asset_id": asset_id,
            "episode": episode,
            "rows": rows,
            "cols": cols,
            "start_scene": start_scene,
            "trim_percent": trim_percent,
            "idempotency_key": key,
        },
    )


def test_grid_math_matches_bot_rounding_trim_and_row_major_scene_order():
    grid = importlib.import_module("copyfast_storyboard_grid")
    layout = grid._grid_cells_for_geometry(
        source_width=501,
        source_height=251,
        spec={
            "episode": 4,
            "rows": 2,
            "cols": 5,
            "start_scene": 7,
            "trim_percent": 0.1,
            "scene_count": 10,
        },
    )

    # This specifically locks Bot-compatible Python ``round`` behavior while
    # retaining the production 32 px minimum cell floor: 501 / 5 yields the
    # unequal x boundary round(300.6) = 301, and 251 / 2 gives the
    # bankers-rounding boundary round(125.5) = 126.
    assert [
        (cell["scene_no"], cell["row_index"], cell["column_index"], cell["crop_x"], cell["crop_y"], cell["width"], cell["height"])
        for cell in layout
    ] == [
        (7, 1, 1, 10, 12, 80, 102),
        (8, 1, 2, 110, 12, 80, 102),
        (9, 1, 3, 210, 12, 81, 102),
        (10, 1, 4, 311, 12, 80, 102),
        (11, 1, 5, 411, 12, 80, 102),
        (12, 2, 1, 10, 138, 80, 101),
        (13, 2, 2, 110, 138, 80, 101),
        (14, 2, 3, 210, 138, 81, 101),
        (15, 2, 4, 311, 138, 80, 101),
        (16, 2, 5, 411, 138, 80, 101),
    ]


def test_storyboard_grid_is_csrf_protected_private_verified_and_idempotent(tmp_path, monkeypatch):
    db_path = tmp_path / "copyfast-storyboard-grid-test.db"
    owner_email = "storyboard-owner@example.com"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, owner_email)
        source = upload_image(client, csrf, key="storyboard-source-0001", body=grid_source_bytes())

        denied = client.post(
            "/api/v1/storyboard-grid",
            json={
                "source_asset_id": source["id"],
                "idempotency_key": "storyboard-denied-0001",
            },
        )
        assert denied.status_code == 403

        created = create_grid(client, csrf, asset_id=source["id"], key="storyboard-create-0001")
        assert created.status_code == 200, created.text
        payload = created.json()
        assert payload["ok"] is True
        assert payload["status"] == "completed"
        operation = payload["data"]["operation"]
        assert operation["kind"] == "storyboard_grid_split"
        assert operation["state"] == "completed"
        assert (operation["source_width"], operation["source_height"]) == (503, 205)
        assert (operation["episode"], operation["rows"], operation["cols"], operation["start_scene"]) == (3, 2, 5, 10)
        assert operation["trim_percent"] == 0.1
        assert operation["scene_count"] == 10
        assert operation["download_ready"] is True
        assert [cell["scene_no"] for cell in operation["cells"]] == list(range(10, 20))
        assert [cell["original_filename"] for cell in operation["cells"]] == [
            f"ep03_scene{scene:02d}.jpg" for scene in range(10, 20)
        ]
        for forbidden in ("storage_key", "sha256", "source_sha", "filesystem", "provider", "payment", "payos", "xu", "telegram"):
            assert forbidden not in created.text.lower()

        replay = create_grid(client, csrf, asset_id=source["id"], key="storyboard-create-0001")
        assert replay.status_code == 200, replay.text
        assert replay.json()["data"]["operation"]["id"] == operation["id"]
        conflict = create_grid(
            client,
            csrf,
            asset_id=source["id"],
            key="storyboard-create-0001",
            rows=1,
        )
        assert conflict.status_code == 409

        history = client.get("/api/v1/storyboard-grid?limit=100")
        assert history.status_code == 200
        assert [item["id"] for item in history.json()["data"]["items"]] == [operation["id"]]
        detail = client.get(f"/api/v1/storyboard-grid/{operation['id']}")
        assert detail.status_code == 200
        assert [event["state"] for event in detail.json()["data"]["events"]] == ["queued", "processing", "completed"]

        archive = client.get(f"/api/v1/storyboard-grid/{operation['id']}/download")
        assert archive.status_code == 200
        assert archive.headers["content-type"].startswith("application/zip")
        assert archive.headers["cache-control"] == "no-store, private"
        assert archive.headers["x-content-type-options"] == "nosniff"
        assert archive.headers["referrer-policy"] == "no-referrer"
        assert archive.headers["content-security-policy"] == "sandbox"
        assert source["id"].encode("utf-8") not in archive.content
        with ZipFile(BytesIO(archive.content), "r") as zip_file:
            assert zip_file.namelist() == [
                "manifest.json",
                *[f"ep03_scene{scene:02d}.jpg" for scene in range(10, 20)],
            ]
            manifest = json.loads(zip_file.read("manifest.json"))
            assert manifest == {
                "format": "toan-aas-storyboard-grid-v1",
                "source": {"width": 503, "height": 205},
                "grid": {
                    "episode": 3,
                    "rows": 2,
                    "cols": 5,
                    "start_scene": 10,
                    "trim_percent": 0.1,
                    "scene_count": 10,
                },
                "cells": [
                    {
                        "filename": f"ep03_scene{scene:02d}.jpg",
                        "scene_no": scene,
                        "row": 1 if scene < 15 else 2,
                        "column": ((scene - 10) % 5) + 1,
                        "x": (10, 111, 211, 312, 412)[(scene - 10) % 5],
                        "y": 10 if scene < 15 else 112,
                        "width": (81, 80, 81, 80, 81)[(scene - 10) % 5],
                        "height": 82 if scene < 15 else 83,
                    }
                    for scene in range(10, 20)
                ],
            }
            with Image.open(BytesIO(zip_file.read("ep03_scene10.jpg"))) as first_cell:
                first_cell.load()
                assert first_cell.format == "JPEG"
                assert first_cell.mode == "RGB"
                assert first_cell.size == (81, 82)
                assert first_cell.getexif() == {}

        first_cell = operation["cells"][0]
        cell_download = client.get(
            f"/api/v1/storyboard-grid/{operation['id']}/cells/{first_cell['id']}/download"
        )
        assert cell_download.status_code == 200
        assert cell_download.headers["content-type"].startswith("image/jpeg")
        assert cell_download.headers["cache-control"] == "no-store, private"
        with Image.open(BytesIO(cell_download.content)) as rendered_cell:
            rendered_cell.load()
            assert rendered_cell.size == (81, 82)

        with sqlite3.connect(db_path) as conn:
            storage_key = conn.execute(
                "SELECT storage_key FROM web_storyboard_grid_operations WHERE id=?", (operation["id"],)
            ).fetchone()[0]
            audit = conn.execute(
                "SELECT detail FROM web_audit_events WHERE action='web.storyboard_grid.created'"
            ).fetchone()
        assert audit and audit[0].startswith("source=503x205;grid=2x5;episode=3;start_scene=10;trim=0.100000;cells=10;bytes=")

    # A separate signed account cannot inspect an operation, download output,
    # or use another account's private source Asset Vault object.
    with make_client(tmp_path, monkeypatch) as other:
        csrf_other = register_and_login(other, "storyboard-other@example.com")
        hidden = other.get(f"/api/v1/storyboard-grid/{operation['id']}")
        assert hidden.json()["error_code"] == "WEB_STORYBOARD_GRID_NOT_FOUND"
        hidden_archive = other.get(f"/api/v1/storyboard-grid/{operation['id']}/download")
        assert hidden_archive.json()["error_code"] == "WEB_STORYBOARD_GRID_NOT_FOUND"
        hidden_cell = other.get(
            f"/api/v1/storyboard-grid/{operation['id']}/cells/{first_cell['id']}/download"
        )
        assert hidden_cell.json()["error_code"] == "WEB_STORYBOARD_GRID_NOT_FOUND"
        rejected_source = create_grid(
            other,
            csrf_other,
            asset_id=source["id"],
            key="storyboard-other-source-0001",
        )
        assert rejected_source.json()["error_code"] == "WEB_STORYBOARD_GRID_SOURCE_NOT_FOUND"

    # Even a valid owner must never receive a ZIP whose path or bytes were
    # tampered with after completion.  Delivery revokes it fail-closed.
    private_archive = tmp_path / "private-image-outputs" / "storyboard-grid" / str(storage_key)
    private_archive.write_bytes(b"tampered-storyboard-zip")
    with make_client(tmp_path, monkeypatch) as owner_again:
        login(owner_again, owner_email)
        unavailable = owner_again.get(f"/api/v1/storyboard-grid/{operation['id']}/download")
        assert unavailable.json()["error_code"] == "WEB_STORYBOARD_GRID_UNAVAILABLE"
        unavailable_detail = owner_again.get(f"/api/v1/storyboard-grid/{operation['id']}")
        assert unavailable_detail.json()["data"]["operation"]["state"] == "unavailable"


def test_storyboard_grid_feature_gate_creates_no_operation(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch, storyboard_grid_enabled=False) as client:
        csrf = register_and_login(client, "storyboard-disabled@example.com")
        source = upload_image(client, csrf, key="storyboard-disabled-source-0001", body=grid_source_bytes())
        blocked = create_grid(client, csrf, asset_id=source["id"], key="storyboard-disabled-create-0001")
        assert blocked.status_code == 503
        assert "WEBAPP_STORYBOARD_GRID_ENABLED" in blocked.text
        with sqlite3.connect(tmp_path / "copyfast-storyboard-grid-test.db") as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_storyboard_grid_operations").fetchone()[0] == 0
