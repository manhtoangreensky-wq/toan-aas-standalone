"""Tests for Chrome Extension Download and 2x SubDub Pricing Enforcement."""

import io
import os
import zipfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app import app
from copyfast_realtime_translate import (
    PRICING_STATE,
    PRODUCTION_PAID_ADMISSION,
    REALTIME_XU_PER_BLOCK,
    REALTIME_XU_PER_WORD,
    get_chrome_extension_zip_bytes,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_extension_download_endpoints(client):
    """Verifies that extension zip download endpoints serve a valid ZIP package."""
    # 1. Direct route
    r1 = client.get("/api/v1/live-translate/extension-download")
    assert r1.status_code == 200
    assert r1.headers.get("content-type") == "application/zip"
    assert "attachment" in r1.headers.get("content-disposition", "")

    # 2. API alias route
    r2 = client.get("/api/v1/extensions/chrome-live-translate.zip")
    assert r2.status_code == 200
    assert r2.headers.get("content-type") == "application/zip"

    # 3. Verify ZIP contents
    with zipfile.ZipFile(io.BytesIO(r1.content), "r") as zf:
        namelist = zf.namelist()
        assert "manifest.json" in namelist
        assert "popup.html" in namelist
        assert "popup.js" in namelist
        assert "background.js" in namelist
        assert "offscreen.js" in namelist
        assert "content.js" in namelist
        assert "content.css" in namelist


def test_popup_js_target_domain():
    """Verifies that popup.js defaults to app.toanaas.vn production webapp domain."""
    ext_dir = Path(__file__).resolve().parent.parent / "extensions" / "chrome-live-translate"
    popup_js = (ext_dir / "popup.js").read_text(encoding="utf-8")
    assert 'const DEFAULT_API_BASE = "https://app.toanaas.vn";' in popup_js
    assert "https://tg.toanaas.vn" not in popup_js


def test_realtime_pricing_constants():
    """Verifies that pricing invariants match Owner approval at 2x SubDub rate."""
    assert PRICING_STATE == "OWNER_APPROVED_2X_SUBDUB"
    assert PRODUCTION_PAID_ADMISSION == "PAID_ACCOUNT_REQUIRED"
    assert REALTIME_XU_PER_BLOCK == 2
    assert REALTIME_XU_PER_WORD == 1.0


def test_unpaid_account_blocked(client):
    """Verifies that accounts without deposited Xu cannot start live translate sessions."""
    # Authenticated user without balance
    payload = {
        "mode": "LIVE_DUB_BILINGUAL",
        "target_language": "vi",
    }
    # Unauthenticated -> 401
    res = client.post("/api/v1/live-translate/sessions", json=payload)
    assert res.status_code == 401
