"""Security and real-output contracts for Web-native Resize & Aspect Studio."""

from __future__ import annotations

from io import BytesIO
import importlib
from pathlib import Path
import sqlite3
import sys

from fastapi.testclient import TestClient
from PIL import Image


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_api", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations", "copyfast_pages",
]


def make_client(tmp_path, monkeypatch, *, image_resize_enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "copyfast-image-operations-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-image-operations-session-secret")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-web-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "20")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "100")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ROOT", str(tmp_path / "private-image-outputs"))
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_MAX_OUTPUT_MB", "20")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_QUOTA_MB", "100")
    monkeypatch.setenv("WEBAPP_IMAGE_RESIZE_ENABLED", "true" if image_resize_enabled else "false")
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
    assert client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Resize Owner"},
    ).status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    return login.json()["data"]["csrf_token"]


def image_bytes(
    image_format: str,
    *,
    size: tuple[int, int] = (160, 100),
    with_exif: bool = False,
    orientation: int | None = None,
) -> bytes:
    """Make a non-uniform source so crop/pad/blur behavior is observable."""
    image = Image.new("RGB", size, (16, 80, 196))
    pixels = image.load()
    for y in range(size[1]):
        for x in range(size[0]):
            if x < size[0] // 2:
                pixels[x, y] = (240, 72 + (y % 32), 64)
            else:
                pixels[x, y] = (32, 136, 232 - (y % 32))
    stream = BytesIO()
    try:
        if (with_exif or orientation is not None) and image_format.upper() == "JPEG":
            exif = Image.Exif()
            if with_exif:
                exif[0x010E] = "private-secret-metadata"
            if orientation is not None:
                exif[0x0112] = orientation
            image.save(stream, format=image_format, quality=95, exif=exif)
        else:
            image.save(stream, format=image_format, quality=95)
        return stream.getvalue()
    finally:
        image.close()


def animated_webp_bytes() -> bytes:
    first = Image.new("RGB", (96, 64), (240, 96, 64))
    second = Image.new("RGB", (96, 64), (64, 160, 240))
    stream = BytesIO()
    try:
        first.save(stream, format="WEBP", save_all=True, append_images=[second], duration=100, loop=0, quality=95)
        return stream.getvalue()
    finally:
        first.close()
        second.close()


def upload_image(
    client: TestClient,
    csrf: str,
    *,
    key: str,
    body: bytes,
    name: str = "source.jpg",
    content_type: str = "image/jpeg",
) -> dict:
    response = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data={"display_name": "Ảnh nguồn riêng tư"},
        files={"file": (name, body, content_type)},
    )
    assert response.status_code == 200
    return response.json()["data"]["asset"]


def resize(
    client: TestClient,
    csrf: str,
    *,
    asset_id: str,
    key: str,
    width: int | None = 128,
    height: int | None = 128,
    preset: str = "custom",
    fit_mode: str = "crop",
):
    return client.post(
        "/api/v1/image-operations/resize",
        headers={"X-CSRF-Token": csrf},
        json={
            "source_asset_id": asset_id,
            "preset": preset,
            "target_width": width,
            "target_height": height,
            "fit_mode": fit_mode,
            "idempotency_key": key,
        },
    )


def output_image(client: TestClient, operation_id: str) -> Image.Image:
    downloaded = client.get(f"/api/v1/image-operations/{operation_id}/download")
    assert downloaded.status_code == 200
    loaded = Image.open(BytesIO(downloaded.content))
    loaded.load()
    return loaded


def test_resize_is_private_idempotent_and_generates_verified_png(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "resize-owner@example.com")
        assert client.get("/image/resize").status_code == 200
        source = upload_image(client, csrf, key="resize-source-0001", body=image_bytes("JPEG"))

        denied = client.post(
            "/api/v1/image-operations/resize",
            json={"source_asset_id": source["id"], "preset": "custom", "target_width": 100, "target_height": 100, "fit_mode": "crop", "idempotency_key": "resize-denied-0001"},
        )
        assert denied.status_code == 403

        created = resize(client, csrf, asset_id=source["id"], key="resize-create-0001")
        assert created.status_code == 200
        payload = created.json()
        assert payload["ok"] is True
        assert payload["status"] == "completed"
        operation = payload["data"]["operation"]
        assert operation["kind"] == "image_resize"
        assert operation["state"] == "completed"
        assert operation["target_width"] == 128
        assert operation["target_height"] == 128
        assert operation["fit_mode"] == "crop"
        assert operation["download_ready"] is True
        for forbidden in ("storage_key", "sha256", "source_sha", "filesystem", "provider", "payment", "payos", "xu"):
            assert forbidden not in created.text.lower()

        replay = resize(client, csrf, asset_id=source["id"], key="resize-create-0001")
        assert replay.status_code == 200
        assert replay.json()["data"]["operation"]["id"] == operation["id"]
        conflict = resize(client, csrf, asset_id=source["id"], key="resize-create-0001", fit_mode="pad")
        assert conflict.status_code == 409

        history = client.get("/api/v1/image-operations?kind=image_resize&limit=100")
        assert history.status_code == 200
        assert [item["id"] for item in history.json()["data"]["items"]] == [operation["id"]]
        assert client.get("/api/v1/image-operations?kind=untrusted").status_code == 422

        downloaded = client.get(f"/api/v1/image-operations/{operation['id']}/download")
        assert downloaded.status_code == 200
        assert downloaded.headers["content-type"].startswith("image/png")
        assert downloaded.headers["cache-control"] == "no-store, private"
        assert downloaded.headers["x-content-type-options"] == "nosniff"
        assert downloaded.headers["referrer-policy"] == "no-referrer"
        assert downloaded.headers["content-security-policy"] == "sandbox"
        assert "attachment" in downloaded.headers["content-disposition"]
        with Image.open(BytesIO(downloaded.content)) as verifier:
            verifier.verify()
        with Image.open(BytesIO(downloaded.content)) as rendered:
            rendered.load()
            assert rendered.format == "PNG"
            assert rendered.size == (128, 128)
            assert int(getattr(rendered, "n_frames", 1) or 1) == 1

        detail = client.get(f"/api/v1/image-operations/{operation['id']}")
        assert detail.status_code == 200
        assert [event["state"] for event in detail.json()["data"]["events"]] == ["queued", "processing", "completed"]
        db_path = tmp_path / "copyfast-image-operations-test.db"
        with sqlite3.connect(db_path) as conn:
            storage_key = conn.execute("SELECT storage_key FROM web_image_operations WHERE id=?", (operation["id"],)).fetchone()[0]
            owner_id = conn.execute("SELECT account_id FROM web_image_operations WHERE id=?", (operation["id"],)).fetchone()[0]
            audit = conn.execute("SELECT detail FROM web_audit_events WHERE action='web.image_operation.image_resize'").fetchone()
        assert audit and audit[0].startswith("preset=custom;fit=crop;source=160x100;output=128x128;bytes=")
        assert source["id"] not in audit[0]
        # Pillow receives duplicated parser descriptors. It must never close
        # the descriptor that will later deliver this private attachment.
        operations_module = importlib.import_module("copyfast_image_operations")
        with (tmp_path / "private-image-outputs" / storage_key).open("rb") as owned_stream:
            operations_module._verify_png_stream(owned_stream, expected_width=128, expected_height=128)
            assert owned_stream.closed is False
            assert owned_stream.read(8) == b"\x89PNG\r\n\x1a\n"

        with make_client(tmp_path, monkeypatch) as other:
            csrf_other = register_and_login(other, "resize-other@example.com")
            hidden = other.get(f"/api/v1/image-operations/{operation['id']}")
            assert hidden.json()["error_code"] == "WEB_IMAGE_OPERATION_NOT_FOUND"
            hidden_download = other.get(f"/api/v1/image-operations/{operation['id']}/download")
            assert hidden_download.json()["error_code"] == "WEB_IMAGE_OPERATION_NOT_FOUND"
            rejected = resize(other, csrf_other, asset_id=source["id"], key="resize-other-0001")
            assert rejected.json()["error_code"] == "WEB_IMAGE_RESIZE_SOURCE_NOT_FOUND"

        (tmp_path / "private-image-outputs" / storage_key).write_bytes(b"tampered-png")
        unavailable = client.get(f"/api/v1/image-operations/{operation['id']}/download")
        assert unavailable.json()["error_code"] == "WEB_IMAGE_OPERATION_UNAVAILABLE"
        assert client.get(f"/api/v1/image-operations/{operation['id']}").json()["data"]["operation"]["state"] == "unavailable"
        # A corrupt/missing artifact is no longer retained output and cannot
        # exhaust the account's private image quota forever.
        monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_QUOTA_MB", "1")
        operations_module = importlib.import_module("copyfast_image_operations")
        database_module = importlib.import_module("copyfast_db")
        with database_module.transaction() as conn:
            assert operations_module._quota_available(conn, account_id=owner_id, additional_bytes=1024 * 1024)


def test_resize_crop_pad_blur_are_real_png_modes_and_strip_source_metadata(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "resize-modes@example.com")
        source = upload_image(
            client,
            csrf,
            key="resize-modes-source-0001",
            body=image_bytes("JPEG", with_exif=True),
        )
        operations = {}
        for mode in ("crop", "pad", "blur"):
            response = resize(client, csrf, asset_id=source["id"], key=f"resize-mode-{mode}-0001", fit_mode=mode)
            assert response.status_code == 200
            operations[mode] = response.json()["data"]["operation"]

        rendered = {}
        for mode, operation in operations.items():
            image = output_image(client, operation["id"])
            try:
                assert image.format == "PNG"
                assert image.mode == "RGB"
                assert image.size == (128, 128)
                assert not image.getexif()
                rendered[mode] = image.copy()
            finally:
                image.close()
        try:
            # A 160×100 source in a 128×128 canvas exposes the modes without
            # assuming an exact Gaussian implementation across Pillow builds.
            assert rendered["pad"].getpixel((0, 0)) == (255, 255, 255)
            assert rendered["crop"].getpixel((0, 0)) != (255, 255, 255)
            assert rendered["blur"].getpixel((0, 0)) != (255, 255, 255)
            assert rendered["blur"].tobytes() != rendered["pad"].tobytes()
            assert b"private-secret-metadata" not in client.get(
                f"/api/v1/image-operations/{operations['blur']['id']}/download"
            ).content
        finally:
            for image in rendered.values():
                image.close()


def test_resize_normalizes_orientation_flattens_alpha_and_accepts_static_webp(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "resize-normalize@example.com")
        oriented = upload_image(
            client,
            csrf,
            key="resize-orientation-source-0001",
            body=image_bytes("JPEG", size=(128, 160), orientation=6),
        )
        oriented_result = resize(
            client,
            csrf,
            asset_id=oriented["id"],
            key="resize-orientation-create-0001",
            width=160,
            height=128,
            fit_mode="pad",
        )
        assert oriented_result.status_code == 200, oriented_result.text
        oriented_output = output_image(client, oriented_result.json()["data"]["operation"]["id"])
        try:
            # EXIF orientation 6 turns the raw 128x160 JPEG into a 160x128
            # canvas before pad placement, so no white side bars remain.
            assert oriented_output.getpixel((0, 0)) != (255, 255, 255)
        finally:
            oriented_output.close()

        transparent = Image.new("RGBA", (160, 128), (255, 0, 0, 0))
        stream = BytesIO()
        try:
            transparent.save(stream, format="PNG")
            alpha = upload_image(
                client,
                csrf,
                key="resize-alpha-source-0001",
                body=stream.getvalue(),
                name="transparent.png",
                content_type="image/png",
            )
        finally:
            transparent.close()
        alpha_result = resize(client, csrf, asset_id=alpha["id"], key="resize-alpha-create-0001", width=160, height=128, fit_mode="crop")
        assert alpha_result.status_code == 200
        alpha_output = output_image(client, alpha_result.json()["data"]["operation"]["id"])
        try:
            assert alpha_output.mode == "RGB"
            assert alpha_output.getpixel((0, 0)) == (255, 255, 255)
        finally:
            alpha_output.close()

        webp = upload_image(
            client,
            csrf,
            key="resize-webp-source-0001",
            body=image_bytes("WEBP"),
            name="static.webp",
            content_type="image/webp",
        )
        webp_result = resize(client, csrf, asset_id=webp["id"], key="resize-webp-create-0001", fit_mode="blur")
        assert webp_result.status_code == 200
        static_webp_output = output_image(client, webp_result.json()["data"]["operation"]["id"])
        try:
            assert static_webp_output.format == "PNG"
            assert static_webp_output.mode == "RGB"
        finally:
            static_webp_output.close()


def test_cover_resize_matches_bot_crop_order_without_giant_intermediate_canvas(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch):
        operations = importlib.import_module("copyfast_image_operations")
        seen: dict[str, object] = {}

        class Cropped:
            def resize(self, size, *, resample):
                seen["resize"] = size
                seen["resample"] = resample
                return "rendered"

            def close(self):
                seen["closed"] = True

        class ThinSource:
            size = (1, 12)

            def crop(self, box):
                seen["crop"] = box
                return Cropped()

        result = operations._cover_resize(ThinSource(), width=4096, height=4096, resample="lanczos")
        assert result == "rendered"
        assert seen == {
            "crop": (0, 5, 1, 6),
            "resize": (4096, 4096),
            "resample": "lanczos",
            "closed": True,
        }


def test_resize_replay_survives_archived_source_and_restart_reconciliation(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "resize-reconcile@example.com")
        source = upload_image(client, csrf, key="resize-reconcile-source-0001", body=image_bytes("JPEG"))
        created = resize(client, csrf, asset_id=source["id"], key="resize-reconcile-create-0001", fit_mode="crop")
        assert created.status_code == 200
        operation = created.json()["data"]["operation"]
        db_path = tmp_path / "copyfast-image-operations-test.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_asset_files SET state='archived' WHERE id=?", (source["id"],))
            conn.commit()
        replay_after_archive = resize(client, csrf, asset_id=source["id"], key="resize-reconcile-create-0001", fit_mode="crop")
        assert replay_after_archive.status_code == 200
        assert replay_after_archive.json()["data"]["operation"]["id"] == operation["id"]

        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE web_image_operations SET state='processing', failure_code=NULL WHERE id=?",
                (operation["id"],),
            )
            conn.commit()
        operations = importlib.import_module("copyfast_image_operations")
        operations.reconcile_image_operation_storage()
        reconciled = client.get(f"/api/v1/image-operations/{operation['id']}")
        assert reconciled.status_code == 200
        assert reconciled.json()["data"]["operation"]["state"] == "failed"
        assert reconciled.json()["data"]["operation"]["download_ready"] is False
        assert reconciled.json()["data"]["events"][-1]["state"] == "failed"
        retry = resize(client, csrf, asset_id=source["id"], key="resize-reconcile-create-0001", fit_mode="crop")
        assert retry.status_code == 200
        assert retry.json()["data"]["operation"]["state"] == "failed"


def test_startup_reconcile_revokes_tampered_completed_output_and_releases_quota(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "resize-corrupt-reconcile@example.com")
        source = upload_image(client, csrf, key="resize-corrupt-source-0001", body=image_bytes("JPEG"))
        created = resize(client, csrf, asset_id=source["id"], key="resize-corrupt-create-0001", fit_mode="pad")
        assert created.status_code == 200
        operation = created.json()["data"]["operation"]
        db_path = tmp_path / "copyfast-image-operations-test.db"
        with sqlite3.connect(db_path) as conn:
            storage_key, account_id = conn.execute(
                "SELECT storage_key, account_id FROM web_image_operations WHERE id=?",
                (operation["id"],),
            ).fetchone()
        output_path = tmp_path / "private-image-outputs" / storage_key
        output_path.write_bytes(b"not-a-verified-png")
        operations = importlib.import_module("copyfast_image_operations")
        operations.reconcile_image_operation_storage()
        assert output_path.exists() is False
        detail = client.get(f"/api/v1/image-operations/{operation['id']}")
        assert detail.status_code == 200
        assert detail.json()["data"]["operation"]["state"] == "unavailable"
        monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_QUOTA_MB", "1")
        database_module = importlib.import_module("copyfast_db")
        with database_module.transaction() as conn:
            assert operations._quota_available(conn, account_id=account_id, additional_bytes=1024 * 1024)


def test_resize_rejects_animated_tampered_and_invalid_private_sources(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "resize-unsafe@example.com")
        animated = upload_image(
            client,
            csrf,
            key="resize-animated-source-0001",
            body=animated_webp_bytes(),
            name="animated.webp",
            content_type="image/webp",
        )
        rejected_animated = resize(client, csrf, asset_id=animated["id"], key="resize-animated-create-0001")
        assert rejected_animated.status_code == 422
        animated_history = client.get("/api/v1/image-operations?kind=image_resize&limit=100").json()["data"]["items"]
        assert animated_history[0]["state"] == "failed"
        assert animated_history[0]["download_ready"] is False

        source = upload_image(client, csrf, key="resize-tamper-source-0001", body=image_bytes("JPEG"))
        db_path = tmp_path / "copyfast-image-operations-test.db"
        with sqlite3.connect(db_path) as conn:
            storage_key = conn.execute("SELECT storage_key FROM web_asset_files WHERE id=?", (source["id"],)).fetchone()[0]
        (tmp_path / "private-web-assets" / storage_key).write_bytes(b"tampered-source")
        tampered = resize(client, csrf, asset_id=source["id"], key="resize-tamper-create-0001")
        assert tampered.status_code == 422
        with sqlite3.connect(db_path) as conn:
            asset_state = conn.execute("SELECT state FROM web_asset_files WHERE id=?", (source["id"],)).fetchone()[0]
            operation_state = conn.execute(
                "SELECT state, storage_key FROM web_image_operations WHERE source_asset_id=? ORDER BY created_at DESC LIMIT 1",
                (source["id"],),
            ).fetchone()
        assert asset_state == "unavailable"
        assert operation_state == ("failed", None)

        invalid = client.post(
            "/api/v1/image-operations/resize",
            headers={"X-CSRF-Token": csrf},
            json={"source_asset_id": animated["id"], "preset": "not-a-preset", "target_width": 100, "target_height": 100, "fit_mode": "magic", "idempotency_key": "resize-invalid-0001"},
        )
        assert invalid.status_code == 422


def test_resize_capacity_and_disabled_feature_fail_closed_without_new_work(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "resize-capacity@example.com")
        source = upload_image(client, csrf, key="resize-capacity-source-0001", body=image_bytes("JPEG"))
        completed = resize(client, csrf, asset_id=source["id"], key="resize-capacity-completed-0001")
        assert completed.status_code == 200
        operations = importlib.import_module("copyfast_image_operations")
        capacity = operations.image_decoder_capacity()
        assert capacity.acquire(blocking=False)
        try:
            # A replay remains available before the busy gate, while a genuinely
            # new request is rejected without creating a lifecycle row.
            replay = resize(client, csrf, asset_id=source["id"], key="resize-capacity-completed-0001")
            assert replay.status_code == 200
            busy = resize(client, csrf, asset_id=source["id"], key="resize-capacity-busy-0001", fit_mode="blur")
            assert busy.status_code == 429
        finally:
            capacity.release()
        with sqlite3.connect(tmp_path / "copyfast-image-operations-test.db") as conn:
            count = conn.execute("SELECT COUNT(*) FROM web_image_operations").fetchone()[0]
        assert count == 1

    disabled_root = tmp_path / "disabled"
    disabled_root.mkdir()
    with make_client(disabled_root, monkeypatch, image_resize_enabled=False) as disabled:
        csrf = register_and_login(disabled, "resize-disabled@example.com")
        source = upload_image(disabled, csrf, key="resize-disabled-source-0001", body=image_bytes("JPEG"))
        blocked = resize(disabled, csrf, asset_id=source["id"], key="resize-disabled-create-0001")
        assert blocked.status_code == 503
        with sqlite3.connect(disabled_root / "copyfast-image-operations-test.db") as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_image_operations").fetchone()[0] == 0


def test_generic_image_resize_intent_is_rejected_before_any_bridge_path(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "resize-generic-block@example.com")
        rejected = client.post(
            "/api/v1/features/image_edit/draft",
            headers={"X-CSRF-Token": csrf},
            json={
                "input": {"operation": "resize", "instructions": "Không đưa request này qua bridge"},
                "idempotency_key": "resize-generic-block-0001",
            },
        )
        assert rejected.status_code == 200
        payload = rejected.json()
        assert payload["ok"] is False
        assert payload["error_code"] == "FEATURE_INPUT_CONTRACT_REQUIRED"
        assert "/image/resize" in payload["message"]
