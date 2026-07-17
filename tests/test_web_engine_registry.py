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
