"""Unit contracts for Smart App Install Banner and High FPS Motion.
"""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PORTAL_JS = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
MOTION_JS = (ROOT / "static" / "portal" / "portal-motion.js").read_text(encoding="utf-8")
PORTAL_CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")


def test_motion_js_has_raf_pointer_throttling_for_60fps() -> None:
    assert "pointerFrame = window.requestAnimationFrame" in MOTION_JS
    assert "if (pointerFrame) return;" in MOTION_JS


def test_portal_js_has_smart_app_install_banner() -> None:
    assert "syncSmartInstallBanner" in PORTAL_JS
    assert "isIosDevice" in PORTAL_JS
    assert "isStandaloneApp" in PORTAL_JS
    assert "portal-smart-install-banner" in PORTAL_JS
    assert "data-portal-smart-install-banner" in PORTAL_JS
    assert "openIosInstallGuideModal" in PORTAL_JS
    assert "pwa-install-ios-guide" in PORTAL_JS
    assert "pwa-install-prompt" in PORTAL_JS
    assert "pwa-install-dismiss" in PORTAL_JS


def test_portal_css_has_smart_install_banner_and_modal_styling() -> None:
    assert ".portal-smart-install-banner" in PORTAL_CSS
    assert ".portal-ios-guide-modal" in PORTAL_CSS
    assert ".portal-modal-backdrop" in PORTAL_CSS
    assert "contain: layout paint;" in PORTAL_CSS
    assert "will-change: transform, opacity;" in PORTAL_CSS
