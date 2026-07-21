"""Focused safety tests for the display-only Web Engine Registry."""

from __future__ import annotations

from copyfast_web_engine import (
    ENGINE_MODES,
    ENGINE_SPECS,
    ENGINE_MODE_BOT_COMPANION,
    ENGINE_MODE_GUARDED,
    ENGINE_MODE_WEB_NATIVE,
    engine_descriptor,
    engine_spec,
)
from copyfast_api import _flags
from copyfast_registry import FEATURE_BY_KEY


def test_every_explicit_engine_spec_references_a_real_catalog_feature() -> None:
    assert set(ENGINE_SPECS).issubset(FEATURE_BY_KEY)
    assert {spec.mode for spec in ENGINE_SPECS.values()}.issubset(ENGINE_MODES)


def test_native_document_operation_needs_its_explicit_private_gates() -> None:
    disabled = engine_descriptor("documents_merge", {})
    enabled = engine_descriptor(
        "documents_merge",
        {"asset_vault_enabled": True, "document_operations_enabled": True},
    )

    assert disabled == {"mode": ENGINE_MODE_WEB_NATIVE, "execution_state": "guarded"}
    assert enabled == {"mode": ENGINE_MODE_WEB_NATIVE, "execution_state": "ready"}
    assert engine_spec("documents_merge").requires_asset_vault is True


def test_native_image_enhance_cannot_be_enabled_by_a_provider_flag() -> None:
    descriptor = engine_descriptor(
        "image_edit",
        {
            "provider_calls_enabled": True,
            "asset_vault_enabled": True,
            "image_operations_enabled": True,
        },
    )

    assert descriptor == {"mode": ENGINE_MODE_WEB_NATIVE, "execution_state": "guarded"}


def test_native_image_history_remains_readable_when_new_image_writes_are_paused() -> None:
    disabled = engine_descriptor("image_history", {})
    enabled = engine_descriptor(
        "image_history",
        {"asset_vault_enabled": True, "image_operations_enabled": True},
    )

    assert disabled == {"mode": ENGINE_MODE_WEB_NATIVE, "execution_state": "guarded"}
    assert enabled == {"mode": ENGINE_MODE_WEB_NATIVE, "execution_state": "ready"}
    assert engine_spec("image_history").requires_asset_vault is True


def test_subtitle_asset_operations_catalog_is_fail_closed_and_private(monkeypatch) -> None:
    monkeypatch.delenv("WEBAPP_SUBTITLE_ASSET_OPERATIONS_ENABLED", raising=False)
    assert _flags()["subtitle_asset_operations_enabled"] is False

    monkeypatch.setenv("WEBAPP_SUBTITLE_ASSET_OPERATIONS_ENABLED", "true")
    assert _flags()["subtitle_asset_operations_enabled"] is True
    assert FEATURE_BY_KEY["subtitle_asset_operations"].route == "/subtitle/assets"

    missing_vault = engine_descriptor(
        "subtitle_asset_operations",
        {"subtitle_asset_operations_enabled": True, "provider_calls_enabled": True},
    )
    ready = engine_descriptor(
        "subtitle_asset_operations",
        {"asset_vault_enabled": True, "subtitle_asset_operations_enabled": True},
    )

    assert missing_vault == {"mode": ENGINE_MODE_WEB_NATIVE, "execution_state": "guarded"}
    assert ready == {"mode": ENGINE_MODE_WEB_NATIVE, "execution_state": "ready"}
    assert engine_spec("subtitle_asset_operations").required_flags == (
        "asset_vault_enabled",
        "subtitle_asset_operations_enabled",
    )
    assert engine_spec("subtitle_asset_operations").requires_asset_vault is True


def test_audio_asset_operations_catalog_is_fail_closed_and_private(monkeypatch) -> None:
    monkeypatch.delenv("WEBAPP_AUDIO_ASSET_OPERATIONS_ENABLED", raising=False)
    assert _flags()["audio_asset_operations_enabled"] is False

    monkeypatch.setenv("WEBAPP_AUDIO_ASSET_OPERATIONS_ENABLED", "true")
    assert _flags()["audio_asset_operations_enabled"] is True
    assert FEATURE_BY_KEY["audio_asset_operations"].route == "/audio/assets"

    missing_vault = engine_descriptor(
        "audio_asset_operations",
        {"audio_asset_operations_enabled": True, "provider_calls_enabled": True},
    )
    ready = engine_descriptor(
        "audio_asset_operations",
        {"asset_vault_enabled": True, "audio_asset_operations_enabled": True},
    )

    assert missing_vault == {"mode": ENGINE_MODE_WEB_NATIVE, "execution_state": "guarded"}
    assert ready == {"mode": ENGINE_MODE_WEB_NATIVE, "execution_state": "ready"}
    assert engine_spec("audio_asset_operations").required_flags == (
        "asset_vault_enabled",
        "audio_asset_operations_enabled",
    )
    assert engine_spec("audio_asset_operations").requires_asset_vault is True


def test_video_preview_is_a_fail_closed_web_native_asset_vault_read(monkeypatch) -> None:
    monkeypatch.delenv("WEBAPP_ASSET_VAULT_ENABLED", raising=False)
    monkeypatch.delenv("WEBAPP_VIDEO_PREVIEW_ENABLED", raising=False)
    assert _flags()["video_preview_enabled"] is False

    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_VIDEO_PREVIEW_ENABLED", "true")
    assert _flags()["video_preview_enabled"] is True
    assert FEATURE_BY_KEY["video_preview"].route == "/video/preview"

    missing_vault = engine_descriptor("video_preview", {"video_preview_enabled": True, "provider_calls_enabled": True})
    ready = engine_descriptor("video_preview", {"asset_vault_enabled": True, "video_preview_enabled": True})

    assert missing_vault == {"mode": ENGINE_MODE_WEB_NATIVE, "execution_state": "guarded"}
    assert ready == {"mode": ENGINE_MODE_WEB_NATIVE, "execution_state": "ready"}
    assert engine_spec("video_preview").required_flags == ("asset_vault_enabled", "video_preview_enabled")
    assert engine_spec("video_preview").requires_asset_vault is True


def test_bot_companion_and_future_adapters_never_claim_public_execution() -> None:
    companion = engine_descriptor("wallet", {"copyfast_enabled": True})
    future_adapter = engine_descriptor("music_song", {"provider_calls_enabled": True, "copyfast_enabled": True})
    unknown = engine_descriptor("unregistered_feature", {"copyfast_enabled": True})

    assert companion == {"mode": ENGINE_MODE_BOT_COMPANION, "execution_state": "guarded"}
    assert future_adapter == {"mode": ENGINE_MODE_GUARDED, "execution_state": "guarded"}
    assert unknown == {"mode": ENGINE_MODE_GUARDED, "execution_state": "guarded"}


def test_public_descriptor_does_not_leak_internal_execution_details() -> None:
    descriptor = engine_descriptor(
        "documents_pdf_to_word",
        {"asset_vault_enabled": True, "document_operations_enabled": True, "pdf_to_word_enabled": True},
    )

    assert set(descriptor) == {"mode", "execution_state"}
    assert "handler_name" not in descriptor
    assert "required_flags" not in descriptor
    assert "payment_mode" not in descriptor
