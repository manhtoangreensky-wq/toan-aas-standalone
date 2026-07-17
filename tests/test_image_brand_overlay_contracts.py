"""Focused contracts for the Web-native Brand Overlay Studio boundary."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_brand_overlay_registry_and_engine_are_explicitly_web_native() -> None:
    registry = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")
    engine = (ROOT / "copyfast_web_engine.py").read_text(encoding="utf-8")
    api = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")

    assert 'WebFeature("image_brand_overlay", "Brand Overlay Studio", "image", "/image/brand-overlay"' in registry
    assert 'ENGINE_SPECS.update(_many(("image_brand_overlay",), mode=ENGINE_MODE_WEB_NATIVE' in engine
    assert 'flags=("asset_vault_enabled", "image_operations_enabled", "image_brand_overlay_enabled")' in engine
    assert '"image_brand_overlay_enabled": enabled("WEBAPP_IMAGE_BRAND_OVERLAY_ENABLED", False)' in api
    assert '"web_native_image_brand_overlay_required"' in api


def test_brand_overlay_portal_is_separate_from_generic_image_history() -> None:
    portal = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
    integration = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
    operations = (ROOT / "copyfast_image_operations.py").read_text(encoding="utf-8")

    assert 'customerPage("/image/brand-overlay", "Brand Overlay Studio"' in portal
    assert 'layout: "image-brand-overlay"' in portal
    assert 'data-portal-action="image-brand-overlay"' in portal
    assert 'data-portal-no-transient data-portal-action="image-brand-overlay"' in portal
    assert 'maxLength: 260' in portal
    assert 'transientFormValues("/image/brand-overlay")' not in portal
    assert '["chat-run-submit", "image-brand-overlay"].includes(action)' in portal
    assert 'logo_opacity_percent: "78"' in portal
    for position in (
        "top_left", "top_center", "top_right", "center_left", "center", "center_right",
        "bottom_left", "bottom_center", "bottom_right",
    ):
        assert f'value: "{position}"' in portal
    assert "imageBrandOverlayOperations" in portal
    assert "imageBrandOverlayOperationListing" in portal
    assert 'const kind = "image_brand_overlay"' in integration
    assert 'api("/image-operations/brand-overlay"' in integration
    assert "imageBrandOverlayOperationsReadState" in integration
    # Raw watermark text belongs only in the signed request body.  The
    # in-memory retry map receives a bounded fingerprint, never the text.
    assert 'const scope = `image-operation:brand-overlay:${sourceAssetId}:${logoAssetId}`;' in integration
    assert "const requestFingerprint = `${textFingerprint.toString(36)}:" in integration
    assert "acquireSubmission(scope, requestFingerprint)" in integration
    assert "${logoAssetId}:${overlayText}:${textPosition}" not in integration
    assert 'const opacityText = String(fields.logo_opacity_percent || "78").trim();' in integration
    # The server, rather than a browser list projection, owns the deliberate
    # generic-history exclusion. The client has its own dedicated route/list.
    assert "IMAGE_HISTORY_KINDS = frozenset({IMAGE_RESIZE_KIND, IMAGE_ENHANCE_KIND})" in operations
    assert '"/image/history": account && assetVaultEnabled && imageOperationsEnabled' in integration


def test_brand_overlay_public_settings_never_expose_text_logo_identity_or_hash() -> None:
    import copyfast_image_operations as operations

    stored = {
        "renderer_version": operations.BRAND_OVERLAY_RENDERER_VERSION,
        "text_present": True,
        "text_digest": "a" * 64,
        "text_position": "top_left",
        "logo_present": True,
        "logo_asset_id": "123e4567-e89b-42d3-a456-426614174000",
        "logo_sha256": "b" * 64,
        "logo_byte_size": 321,
        "logo_position": "bottom_right",
        "logo_scale_percent": 18,
        "logo_opacity_percent": 78,
    }
    public = operations._operation_settings(operations.IMAGE_BRAND_OVERLAY_KIND, json.dumps(stored))

    assert public == {
        "text_present": True,
        "text_position": "top_left",
        "logo_present": True,
        "logo_position": "bottom_right",
        "logo_scale_percent": 18,
        "logo_opacity_percent": 78,
    }
    rendered = json.dumps(public)
    for forbidden in ("digest", "asset_id", "sha256", "logo_byte_size"):
        assert forbidden not in rendered


def test_brand_overlay_positions_match_local_editor_coordinate_contract() -> None:
    import copyfast_image_operations as operations

    dimensions = {"canvas_width": 1000, "canvas_height": 800, "overlay_width": 100, "overlay_height": 50, "margin": 20}
    assert operations._overlay_xy(position="top_left", **dimensions) == (20, 20)
    assert operations._overlay_xy(position="center", **dimensions) == (450, 375)
    assert operations._overlay_xy(position="bottom_right", **dimensions) == (880, 730)
