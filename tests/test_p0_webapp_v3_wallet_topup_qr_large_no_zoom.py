"""Contract-First Tests for P0.WEBAPP.V3.WALLET.TOPUP.QR.DEFAULT.LARGE.NO.ZOOM.R1

Validates:
01. openQrLightboxModal does not exist in static/portal/portal.js
02. closeQrLightboxModal does not exist in static/portal/portal.js
03. No data-portal-action="open-qr-lightbox"
04. No data-portal-action="close-qr-lightbox"
05. No portal-qr-lightbox-modal class in portal.css or portal.js
06. No cursor: pointer or cursor: zoom-in on QR figure
07. No hover scale/zoom on QR image
08. No copy "phóng to", "Bấm để phóng to", "Xem lớn" in figure/caption
09. QR desktop size >= 360px
10. QR mobile size >= 300px (at viewport 390px)
11. QR visible directly in payment card without extra click/zoom
12. Payment info adjacent to QR in the same card
13. Aspect ratio 1, object-fit contain, zero crop
"""

from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PORTAL_JS = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
PORTAL_CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")


def test_01_and_02_no_lightbox_functions_in_portal_js() -> None:
    """01 & 02: openQrLightboxModal and closeQrLightboxModal must NOT exist in portal.js."""
    assert "openQrLightboxModal" not in PORTAL_JS
    assert "closeQrLightboxModal" not in PORTAL_JS


def test_03_and_04_no_lightbox_actions_in_portal_js() -> None:
    """03 & 04: Neither open-qr-lightbox nor close-qr-lightbox actions exist."""
    assert "open-qr-lightbox" not in PORTAL_JS
    assert "close-qr-lightbox" not in PORTAL_JS


def test_05_no_lightbox_modal_in_css_or_js() -> None:
    """05: portal-qr-lightbox-modal class does not exist in portal.css or portal.js."""
    assert "portal-qr-lightbox" not in PORTAL_CSS
    assert "portal-qr-lightbox" not in PORTAL_JS


def test_06_no_zoom_cursor_on_qr_figure() -> None:
    """06: No cursor: pointer or cursor: zoom-in on QR figure."""
    assert "cursor:zoom-in" not in PORTAL_JS
    assert "cursor: zoom-in" not in PORTAL_JS
    # In portal.css, .portal-manual-payment-method figure must not have cursor: pointer
    figure_rule = re.search(r"\.portal-manual-payment-method\s+figure\s*\{(?P<body>[^}]+)\}", PORTAL_CSS)
    assert figure_rule, "Expected .portal-manual-payment-method figure rule in CSS"
    assert "cursor" not in figure_rule.group("body")


def test_07_no_hover_scale_zoom_on_qr() -> None:
    """07: No hover scale/zoom on QR figure/image."""
    assert ".portal-manual-payment-method figure:hover" not in PORTAL_CSS
    assert ".portal-manual-payment-qr-figure" not in PORTAL_CSS
    assert ".portal-manual-payment-qr-figure" not in PORTAL_JS


def test_08_no_zoom_copy_in_figure_or_caption() -> None:
    """08: No copy 'phóng to', 'Bấm để phóng to', 'Xem lớn' in topup guide or payment card."""
    guide = PORTAL_JS[PORTAL_JS.index("function renderManualTopupGuide(context)"):PORTAL_JS.index("function renderPaymentRequestForm(page, context)")]
    assert "phóng to" not in guide.lower()
    assert "bấm để phóng to" not in guide.lower()
    assert "xem lớn" not in guide.lower()


def test_09_desktop_qr_size_contract() -> None:
    """09: Desktop QR size contract (markup specifies 380x380, CSS supports >= 360px up to 420px)."""
    assert 'width="380" height="380"' in PORTAL_JS
    img_rule = re.search(r"\.portal-manual-payment-method\s+img\s*\{(?P<body>[^}]+)\}", PORTAL_CSS)
    assert img_rule, "Expected .portal-manual-payment-method img rule in CSS"
    body = img_rule.group("body")
    assert "width: min(380px, 100%)" in body or "width: 380px" in body
    assert "max-width: 420px" in body
    assert "aspect-ratio: 1" in body
    assert "object-fit: contain" in body


def test_10_mobile_qr_size_contract() -> None:
    """10: Mobile QR size contract (at 390px viewport, min-width >= 300px)."""
    manual_css = PORTAL_CSS[PORTAL_CSS.index("/* Manual top-up"):]
    assert "min-width: 300px" in manual_css
    assert ".portal-manual-payment-method img" in manual_css


def test_11_qr_visible_in_payment_card_without_zoom_interaction() -> None:
    """11: QR renders directly inside singleMethodCard HTML without extra click."""
    assert '<figure><img src="${safeText(safeQrUrl)}"' in PORTAL_JS
    assert 'alt="${safeText(`${manualTopupText("scanQr", "Quét mã QR")} · ${methodLabel}`)}"' in PORTAL_JS


def test_12_payment_info_adjacent_to_qr_in_same_card() -> None:
    """12: Payment info (methodLabel, facts, statusText) is adjacent to QR figure in same article."""
    card_marker = 'class="portal-manual-payment-method"'
    assert card_marker in PORTAL_JS
    card_idx = PORTAL_JS.index(card_marker)
    snippet = PORTAL_JS[card_idx : card_idx + 800]
    assert "<figure><img src=" in snippet
    assert 'class="portal-manual-payment-method-copy"' in snippet


def test_13_no_escape_listener_for_lightbox() -> None:
    """13: Keydown Escape listener for lightbox is removed."""
    assert 'closeQrLightboxModal' not in PORTAL_JS
