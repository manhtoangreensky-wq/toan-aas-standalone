"""Closed, display-only readiness taxonomy for the standalone Web catalog.

This registry is deliberately not a capability grant.  It has no network,
storage, environment, provider, payment or bridge access; callers supply the
already-public flags and bridge-configuration boolean that they are allowed to
project.  Route handlers remain authoritative for authentication, CSRF,
ownership, idempotency, jobs, output verification and delivery.
"""

from __future__ import annotations

from typing import Mapping

from copyfast_web_engine import ENGINE_MODE_BOT_COMPANION, ENGINE_MODE_WEB_NATIVE, engine_spec


READINESS_AVAILABLE = "available"
READINESS_PLANNING_ONLY = "planning_only"
READINESS_LOCAL_EXECUTION = "local_execution"
READINESS_CANONICAL_READ = "canonical_read"
READINESS_GUARDED = "guarded"
READINESS_DISABLED = "disabled"
READINESS_STATES = frozenset({
    READINESS_AVAILABLE,
    READINESS_PLANNING_ONLY,
    READINESS_LOCAL_EXECUTION,
    READINESS_CANONICAL_READ,
    READINESS_GUARDED,
    READINESS_DISABLED,
})


# These Web routes are useful product surfaces in their own right: signed
# account workspaces, local organisation, verified local history or support.
# They do not thereby claim an AI/provider/media execution result.
_AVAILABLE_FEATURES = frozenset({
    "dashboard",
    "feature_catalog",
    "projects",
    "workspace_drafts",
    "workspace_menu",
    "account",
    "interface_locale_navigator",
    "account_activity",
    "account_security",
    "workspace_care",
    "partner_readiness",
    "notes",
    "reminders",
    "inbox",
    "automation",
    "community",
    "guides",
    "asset_vault",
    "chat",
    "analytics_workspace",
    "workboard",
    "prompt_library",
    "free_prompt_gallery",
    "support",
    "tickets",
    "operations",
    "tool_directory",
    "media_studio",
    "legal",
    "privacy",
    "image_history",
    "video_preview",
})

# Only these reviewable local artifact/transform boundaries may use the
# ``local_execution`` label.  Every other Web-native engine defaults to
# planning-only until it earns its own output-validation contract.
_LOCAL_EXECUTION_FEATURES = frozenset({
    "project_packages",
    "subtitle_formats",
    "subtitle_asset_operations",
    "audio_asset_operations",
    "documents_merge",
    "documents_split",
    "documents_compress",
    "documents_ocr",
    "documents_pdf_ocr",
    "documents_pdf_ocr_word",
    "documents_image_to_pdf",
    "documents_pdf_to_images",
    "documents_pdf_to_word",
    "image_resize",
    "image_edit",
    "image_brand_overlay",
    "image_storyboard_grid",
})

# Canonical writes and provider-mediated execution must stay guarded even
# when a companion read surface is configured.  In particular, this prevents
# a catalog label from presenting payment as a readable/ready integration.
_ALWAYS_GUARDED_FEATURES = frozenset({"wallet_topup"})


def _web_native_flags_are_enabled(feature_key: str, flags: Mapping[str, object]) -> bool:
    spec = engine_spec(feature_key)
    return spec.mode == ENGINE_MODE_WEB_NATIVE and all(flags.get(name) is True for name in spec.required_flags)


def _base_readiness(feature_key: str) -> str:
    if feature_key in _ALWAYS_GUARDED_FEATURES:
        return READINESS_GUARDED
    if feature_key in _LOCAL_EXECUTION_FEATURES:
        return READINESS_LOCAL_EXECUTION
    if feature_key in _AVAILABLE_FEATURES:
        return READINESS_AVAILABLE
    mode = engine_spec(feature_key).mode
    if mode == ENGINE_MODE_WEB_NATIVE:
        return READINESS_PLANNING_ONLY
    if mode == ENGINE_MODE_BOT_COMPANION:
        return READINESS_CANONICAL_READ
    return READINESS_GUARDED


def readiness_descriptor(
    feature_key: str,
    flags: Mapping[str, object],
    *,
    bridge_ready: bool,
) -> dict[str, str]:
    """Return one conservative product label for a known registry feature.

    The descriptor describes the kind of product surface a route represents;
    it never indicates a user is linked, a provider/job/payment is possible,
    or an output is valid.  Missing keys, paused Web-native switches and a
    missing canonical bridge all fail closed.
    """

    key = str(feature_key or "").strip()
    status = _base_readiness(key)
    if status in {READINESS_AVAILABLE, READINESS_PLANNING_ONLY, READINESS_LOCAL_EXECUTION}:
        spec = engine_spec(key)
        if spec.mode == ENGINE_MODE_WEB_NATIVE and not _web_native_flags_are_enabled(key, flags):
            status = READINESS_DISABLED
    elif status == READINESS_CANONICAL_READ:
        if flags.get("copyfast_enabled") is not True or bridge_ready is not True:
            status = READINESS_GUARDED
    return {"status": status if status in READINESS_STATES else READINESS_GUARDED}
