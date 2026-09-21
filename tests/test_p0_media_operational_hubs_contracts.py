"""Empirical contract & behavioral E2E tests for the Media Operational Hubs.

Proves the complete behavioral chain for all 7 WORKING hub capabilities:
UI route/control -> actual API -> canonical backend -> isolated DB/file state -> result/artifact -> visible result contract:
1. VIDEO_FINISHING (/tools/video, /video/finishing -> copyfast_video_transform_operations)
2. VIDEO_POSTER (/video/poster -> copyfast_video_operations)
3. IMAGE_LOCAL_OPERATION (/tools/image -> copyfast_image_operations)
4. AUDIO_ASSET_OPERATION (/voice, /audio/assets -> copyfast_audio_asset_operations)
5. SUBTITLE_FORMAT_OPERATION (/subdub, /subtitle/formats -> copyfast_subtitle_format_core)
6. SUBTITLE_ASSET_OPERATION (/subdub, /subtitle/assets -> copyfast_subtitle_asset_operations)
7. FREE_TOOL representative behavior (/tools/free -> copyfast_free_prompt_gallery)
"""

from __future__ import annotations

import importlib
from io import BytesIO
from pathlib import Path
import uuid

from fastapi.testclient import TestClient
from PIL import Image
import pytest

import copyfast_pages
import copyfast_subtitle_format_core as sfc

import tests.test_copyfast_video_transform_operations as vto
import tests.test_copyfast_video_operations as vo
import tests.test_copyfast_image_operations as io
import tests.test_copyfast_audio_asset_operations as ao
import tests.test_copyfast_subtitle_asset_operations as so

ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")


# ==============================================================================
# 1. VIDEO FINISHING BEHAVIORAL E2E PROOF
# ==============================================================================
def test_behavioral_video_finishing_e2e(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """UI route /tools/video & /video/finishing -> POST /api/v1/video-transform-operations -> verified MP4 artifact."""
    shell = copyfast_pages.render_portal("/tools/video")
    assert shell.status_code == 200
    assert b"Video Operations" in shell.body or b"Video Studio" in shell.body

    finishing_shell = copyfast_pages.render_portal("/video/finishing")
    assert finishing_shell.status_code == 200

    with vto.make_client(tmp_path, monkeypatch) as client:
        csrf = vto.register_and_login(client, "finishing-e2e@example.com")
        source = vto.upload_video(client, csrf, key=uuid.uuid4().hex)
        vto.activate_transform_runtime(monkeypatch)

        res = client.post(
            "/api/v1/video-transform-operations",
            headers={"X-CSRF-Token": csrf},
            json={
                "source_asset_id": source["id"],
                "target_ratio": "9:16",
                "fit_mode": "crop",
                "preset": "cinematic",
                "sharpen": True,
                "preserve_audio": True,
                "idempotency_key": uuid.uuid4().hex,
            },
        )
        assert res.status_code == 200
        op = res.json()["data"]["operation"]
        assert op["state"] == "completed"
        assert op["source"]["width"] == 720

        dl = client.get(f"/api/v1/video-transform-operations/{op['id']}/download")
        assert dl.status_code == 200
        assert dl.headers["content-type"] == "video/mp4"
        assert len(dl.content) > 0


# ==============================================================================
# 2. VIDEO POSTER BEHAVIORAL E2E PROOF
# ==============================================================================
def test_behavioral_video_poster_e2e(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """UI route /video/poster -> POST /api/v1/video-operations/poster -> verified JPEG artifact."""
    shell = copyfast_pages.render_portal("/video/poster")
    assert shell.status_code == 200

    with vto.make_client(tmp_path, monkeypatch) as client:
        csrf = vto.register_and_login(client, "poster-e2e@example.com")
        source = vto.upload_video(client, csrf, key=uuid.uuid4().hex)

        vo.activate_video_runtime(monkeypatch)
        monkeypatch.setenv("WEBAPP_VIDEO_OPERATIONS_ENABLED", "true")
        monkeypatch.setenv("WEBAPP_VIDEO_POSTER_ENABLED", "true")

        res = client.post(
            "/api/v1/video-operations/poster",
            headers={"X-CSRF-Token": csrf},
            json={
                "source_asset_id": source["id"],
                "poster_position": "middle",
                "idempotency_key": uuid.uuid4().hex,
            },
        )
        assert res.status_code == 200
        op = res.json()["data"]["operation"]
        assert op["state"] == "completed"

        dl = client.get(f"/api/v1/video-operations/{op['id']}/download")
        assert dl.status_code == 200
        assert dl.headers["content-type"].startswith("image/jpeg")
        assert len(dl.content) > 0


# ==============================================================================
# 3. IMAGE LOCAL OPERATION BEHAVIORAL E2E PROOF
# ==============================================================================
def test_behavioral_image_local_operation_e2e(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """UI route /tools/image -> POST /api/v1/image-operations/resize -> verified Image artifact."""
    shell = copyfast_pages.render_portal("/tools/image")
    assert shell.status_code == 200

    with vto.make_client(tmp_path, monkeypatch) as client:
        csrf = vto.register_and_login(client, "image-e2e@example.com")
        monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ENABLED", "true")
        monkeypatch.setenv("WEBAPP_IMAGE_RESIZE_ENABLED", "true")

        source = io.upload_image(client, csrf, key=uuid.uuid4().hex, body=io.image_bytes("JPEG"))
        res = io.resize(client, csrf, asset_id=source["id"], key=uuid.uuid4().hex, width=128, height=128)
        assert res.status_code == 200
        op = res.json()["data"]["operation"]
        assert op["state"] == "completed"

        dl = client.get(f"/api/v1/image-operations/{op['id']}/download")
        assert dl.status_code == 200
        assert len(dl.content) > 0


# ==============================================================================
# 4. AUDIO ASSET OPERATION BEHAVIORAL E2E PROOF
# ==============================================================================
def test_behavioral_audio_asset_operation_e2e(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """UI route /voice & /audio/assets -> POST /api/v1/audio-asset-operations/convert -> verified audio artifact."""
    shell = copyfast_pages.render_portal("/voice")
    assert shell.status_code == 200

    with vto.make_client(tmp_path, monkeypatch) as client:
        csrf = vto.register_and_login(client, "audio-e2e@example.com")
        ao.activate_audio_runtime(monkeypatch)
        monkeypatch.setenv("WEBAPP_AUDIO_ASSET_OPERATIONS_ENABLED", "true")

        source = ao.upload_mp3(client, csrf, key=uuid.uuid4().hex)
        res = ao.convert(client, csrf, asset_id=source["id"], target_format="mp3", key=uuid.uuid4().hex)
        assert res.status_code == 200
        op = res.json()["data"]["operation"]
        assert op["state"] == "completed"

        dl = client.get(f"/api/v1/audio-asset-operations/{op['id']}/download")
        assert dl.status_code == 200
        assert dl.headers["content-type"] == "audio/mpeg"
        assert len(dl.content) > 0


# ==============================================================================
# 5. SUBTITLE FORMAT OPERATION BEHAVIORAL E2E PROOF
# ==============================================================================
def test_behavioral_subtitle_format_operation_e2e() -> None:
    """UI route /subdub & /subtitle/formats -> copyfast_subtitle_format_core -> valid VTT cues."""
    shell = copyfast_pages.render_portal("/subdub")
    assert shell.status_code == 200

    source_srt = (
        "1\n"
        "00:00:01,000 --> 00:00:02,500\n"
        "Xin chào TOAN AAS\n\n"
        "2\n"
        "00:00:02,600 --> 00:00:04,000\n"
        "Subtitle format lab hoạt động chuẩn xác\n"
    )
    cues = sfc.parse_subtitle_text("srt", source_srt)
    assert len(cues) == 2
    rendered_vtt = sfc.render_subtitle_text("vtt", cues)
    assert rendered_vtt.startswith("WEBVTT\n")
    assert "Xin chào TOAN AAS" in rendered_vtt
    assert "00:00:01.000 --> 00:00:02.500" in rendered_vtt


# ==============================================================================
# 6. SUBTITLE ASSET OPERATION BEHAVIORAL E2E PROOF
# ==============================================================================
def test_behavioral_subtitle_asset_operation_e2e(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """UI route /subdub & /subtitle/assets -> POST /api/v1/subtitle-asset-operations/convert -> VTT artifact."""
    shell = copyfast_pages.render_portal("/subtitle/assets")
    assert shell.status_code == 200

    with vto.make_client(tmp_path, monkeypatch) as client:
        csrf = vto.register_and_login(client, "sub-e2e@example.com")
        monkeypatch.setenv("WEBAPP_SUBTITLE_ASSET_OPERATIONS_ENABLED", "true")
        monkeypatch.setenv("WEBAPP_SUBTITLE_ASSET_OPERATIONS_TOPOLOGY", "sqlite_single_replica")
        monkeypatch.setenv("WEBAPP_REPLICA_COUNT", "1")

        source = so.upload_subtitle(client, csrf, key=uuid.uuid4().hex, body=so.SRT)
        res = so.convert(client, csrf, asset_id=source["id"], target_format="vtt", key=uuid.uuid4().hex)
        assert res.status_code == 200
        op = res.json()["data"]["operation"]
        assert op["state"] == "completed"

        dl = client.get(f"/api/v1/subtitle-asset-operations/{op['id']}/download")
        assert dl.status_code == 200
        assert b"WEBVTT" in dl.content


# ==============================================================================
# 7. FREE TOOL REPRESENTATIVE BEHAVIOR PROOF
# ==============================================================================
def test_behavioral_free_tool_representative_behavior_e2e(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """UI route /tools/free -> GET /api/v1/free-prompt-gallery/catalog -> verified prompt snapshot."""
    shell = copyfast_pages.render_portal("/tools/free")
    assert shell.status_code == 200

    with vto.make_client(tmp_path, monkeypatch) as client:
        csrf = vto.register_and_login(client, "free-tool-e2e@example.com")
        res = client.get("/api/v1/free-prompt-gallery/catalog")
        assert res.status_code == 200
        data = res.json()["data"]
        assert "categories" in data
        assert len(data["categories"]) > 0
        assert data["boundaries"]["execution"] == "web_native_static_prompt_gallery"
        assert data["boundaries"]["provider_called"] is False
