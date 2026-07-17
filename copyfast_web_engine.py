"""Fail-closed execution taxonomy for the standalone Web App catalog.

This is not an executor.  It imports no Bot, Core Bridge, provider, wallet,
PayOS, database, storage, environment, network or subprocess code.  Callers
pass already-public feature flags and receive a two-field browser descriptor.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


ENGINE_MODE_WEB_NATIVE = "web_native"
ENGINE_MODE_BOT_COMPANION = "bot_companion"
ENGINE_MODE_GUARDED = "guarded"
ENGINE_MODES = frozenset({ENGINE_MODE_WEB_NATIVE, ENGINE_MODE_BOT_COMPANION, ENGINE_MODE_GUARDED})
ENGINE_STATES = frozenset({"ready", "guarded"})


@dataclass(frozen=True)
class EngineSpec:
    """Internal classification for one registry feature key.

    ``handler_name`` and ``required_flags`` are deliberately internal.  They
    do not leave ``engine_descriptor`` and cannot become browser authority.
    """

    feature_key: str
    mode: str
    required_flags: tuple[str, ...] = ()
    handler_name: str = ""
    requires_asset_vault: bool = False
    payment_mode: str = "none"


def _many(
    keys: tuple[str, ...],
    *,
    mode: str,
    flags: tuple[str, ...] = (),
    handler: str = "",
    asset_vault: bool = False,
    payment_mode: str = "none",
) -> dict[str, EngineSpec]:
    return {
        key: EngineSpec(
            feature_key=key,
            mode=mode,
            required_flags=flags,
            handler_name=handler,
            requires_asset_vault=asset_vault,
            payment_mode=payment_mode,
        )
        for key in keys
    }


# A Web-native classification means this repository owns a signed workspace or
# deterministic private operation.  It does not mean a provider job, payment,
# output or delivery is available.
ENGINE_SPECS: dict[str, EngineSpec] = {}
ENGINE_SPECS.update(_many(
    (
        "dashboard", "feature_catalog", "projects", "workspace_drafts",
        "account", "account_activity", "tool_directory",
        "media_studio",
    ),
    mode=ENGINE_MODE_WEB_NATIVE,
    flags=("copyfast_enabled",),
    handler="web_workspace",
))
ENGINE_SPECS.update(_many(("notes", "reminders"), mode=ENGINE_MODE_WEB_NATIVE, flags=("memory_center_enabled",), handler="memory_center"))
ENGINE_SPECS.update(_many(("inbox",), mode=ENGINE_MODE_WEB_NATIVE, flags=("notification_center_enabled",), handler="notification_center"))
ENGINE_SPECS.update(_many(("automation", "operations"), mode=ENGINE_MODE_WEB_NATIVE, flags=("autopilot_enabled",), handler="operations_autopilot"))
ENGINE_SPECS.update(_many(("asset_vault",), mode=ENGINE_MODE_WEB_NATIVE, flags=("asset_vault_enabled",), handler="asset_vault", asset_vault=True))
ENGINE_SPECS.update(_many(("project_packages",), mode=ENGINE_MODE_WEB_NATIVE, flags=("project_package_enabled",), handler="project_packages"))
ENGINE_SPECS.update(_many(("prompt_library",), mode=ENGINE_MODE_WEB_NATIVE, flags=("prompt_library_enabled",), handler="prompt_library"))
ENGINE_SPECS.update(_many(("prompt_studio",), mode=ENGINE_MODE_WEB_NATIVE, flags=("prompt_studio_enabled",), handler="prompt_studio"))
# Free Prompt Gallery is a signed, immutable catalog snapshot rather than the
# private Prompt Library or a Bot/global-seed runtime. Its own router stays
# read-only and shares only the Content Studio availability gate; an explicit
# save handoff is separately owned and guarded by Prompt Library.
ENGINE_SPECS.update(_many(("free_prompt_gallery",), mode=ENGINE_MODE_WEB_NATIVE, flags=("content_studio_enabled",), handler="free_prompt_gallery"))
ENGINE_SPECS.update(_many(("content_studio",), mode=ENGINE_MODE_WEB_NATIVE, flags=("content_studio_enabled",), handler="content_studio"))
# Prompt Pack is a bounded, stateless text planner derived from pure template
# logic. It is not a model/provider call, Bot handoff, job, output, payment,
# publish action or durable Content Studio variant.
ENGINE_SPECS.update(_many(("content_prompt_pack",), mode=ENGINE_MODE_WEB_NATIVE, flags=("content_studio_enabled",), handler="content_prompt_pack"))
# The Bot's Free Hub `publish_package` only formats a previous text result.
# Web makes that source explicit and returns a transient human-review package;
# it never connects a social account, schedules, publishes or delivers a post.
ENGINE_SPECS.update(_many(("publish_review_pack",), mode=ENGINE_MODE_WEB_NATIVE, flags=("content_studio_enabled",), handler="publish_review_pack"))
# Contextual Ad Prompt Wizard is the Web conversion of the Bot's local,
# five-choice Meta prompt conversation.  It returns only a bounded text plan;
# no Meta/provider/Bot request, media output/job, wallet/payment mutation or
# publishing action exists behind this descriptor.
ENGINE_SPECS.update(_many(("contextual_ad_prompt",), mode=ENGINE_MODE_WEB_NATIVE, flags=("content_studio_enabled",), handler="contextual_ad_prompt"))
# `/trend_research` in the frozen Bot is a static manual-research checklist.
# The Web conversion keeps that deterministic text guidance only: no live
# search, social scrape, Bot/bridge/provider execution, job, wallet/payment,
# asset, media output or publishing capability is implied by this route.
ENGINE_SPECS.update(_many(("trend_research",), mode=ENGINE_MODE_WEB_NATIVE, flags=("trend_research_enabled",), handler="trend_research"))
# `/media_factory` is a static content/video-pack checklist in the frozen Bot.
# Its Web conversion coordinates only transient planning text and next routes;
# no live search, provider/Bot bridge, job, wallet/payment, media output or
# publishing execution is implied by this descriptor.
ENGINE_SPECS.update(_many(("media_factory",), mode=ENGINE_MODE_WEB_NATIVE, flags=("media_factory_enabled",), handler="media_factory"))
# `/creative_flow` is a second deterministic template in the same frozen Bot
# media-planning family. It creates only a transient script/brief direction,
# never a provider/Bot call, job, wallet/payment mutation, media output or
# publish action.
ENGINE_SPECS.update(_many(("creative_flow",), mode=ENGINE_MODE_WEB_NATIVE, flags=("media_factory_enabled",), handler="creative_flow"))
ENGINE_SPECS.update(_many(("media_workspace",), mode=ENGINE_MODE_WEB_NATIVE, flags=("music_media_workspace_enabled",), handler="music_media_workspace"))
ENGINE_SPECS.update(_many(("music_prompt_composer",), mode=ENGINE_MODE_WEB_NATIVE, flags=("music_media_workspace_enabled",), handler="music_prompt_composer"))
ENGINE_SPECS.update(_many(("voice_studio",), mode=ENGINE_MODE_WEB_NATIVE, flags=("voice_studio_enabled",), handler="voice_studio"))
# Voice Direction Composer is a bounded, transient adaptation of the Bot's
# static voice-style suggestions.  It only returns editorial text; it has no
# consent, TTS/clone/preview, provider, job, wallet, payment, asset or
# Telegram execution path.
ENGINE_SPECS.update(_many(("voice_direction_composer",), mode=ENGINE_MODE_WEB_NATIVE, flags=("voice_studio_enabled",), handler="voice_direction_composer"))
ENGINE_SPECS.update(_many(("video_studio",), mode=ENGINE_MODE_WEB_NATIVE, flags=("video_studio_enabled",), handler="video_studio"))
# The Bot's video-factory flow is a read-only seven-step guide. This route is
# navigational only; it does not carry data into linked tools or enable a
# renderer, provider/Bot call, job, wallet/payment, media output or publish.
ENGINE_SPECS.update(_many(("video_factory_workflow",), mode=ENGINE_MODE_WEB_NATIVE, flags=("video_studio_enabled",), handler="video_factory_workflow"))
# Story Video Planner combines the frozen Bot's static story workflow and
# motion-prompt helper as a transient text receipt. It never invokes a video
# engine/provider/Bot, creates an output/job, mutates wallet/payment or
# publishes.
ENGINE_SPECS.update(_many(("story_video_plan",), mode=ENGINE_MODE_WEB_NATIVE, flags=("media_factory_enabled",), handler="story_video_plan"))
# Source-rights and dubbing help in the frozen Bot are static public guidance.
# The private Web guide remains navigation/read-only only; it does not verify
# license/consent, call a provider/Bot, create an asset/job, mutate payment or
# publish.
ENGINE_SPECS.update(_many(("source_rights_guide",), mode=ENGINE_MODE_WEB_NATIVE, flags=("content_studio_enabled",), handler="source_rights_guide"))
# Video Prompt Planner translates only static prompt-direction semantics into a
# bounded, transient text plan. It never accepts source media or calls an
# engine/provider, creates a preview/output/job, mutates a wallet/payment or
# publishes.
ENGINE_SPECS.update(_many(("video_prompt_planner",), mode=ENGINE_MODE_WEB_NATIVE, flags=("video_studio_enabled",), handler="video_prompt_planner"))
# Cinematic Ad Concept Composer reuses only the Bot's static ad-concept
# planning vocabulary.  It is request/response text only: no media/provider,
# preview/output/job, wallet/payment, asset save or publish authority exists.
ENGINE_SPECS.update(_many(("cinematic_ad_concept",), mode=ENGINE_MODE_WEB_NATIVE, flags=("video_studio_enabled",), handler="cinematic_ad_concept"))
# Image Motion Planner replaces the Bot's short-lived image-video save state
# with a signed Image Studio metadata selector and a durable Video Plan draft.
# It requires both authoring stores but never opens source media, calls a
# provider/Bot, renders, creates a job/output, mutates wallet/payment or
# publishes.
ENGINE_SPECS.update(_many(("image_motion_planner",), mode=ENGINE_MODE_WEB_NATIVE, flags=("video_studio_enabled", "image_studio_enabled"), handler="image_motion_planner"))
# Reference Format Planner ports the Bot's `videoref` planning grammar to a
# signed, Asset-Vault-selected Web flow.  The selected video remains metadata
# only: it is never opened, downloaded, decoded, analyzed or sent to a model.
# The engine descriptor grants only deterministic planning and a private Video
# Plan handoff, never a provider/Bot call, render, job, wallet/payment or
# publishing action.
ENGINE_SPECS.update(_many(("reference_format_planner",), mode=ENGINE_MODE_WEB_NATIVE, flags=("video_studio_enabled",), handler="reference_format_planner"))
# Storyboard Prompt Pack Composer reimplements only the Bot's static storypack
# vocabulary as a bounded request/response text plan. It does not accept source
# media or execute anything: no external service, generated media/output/job,
# wallet/payment, saved asset or publish action is available here.
ENGINE_SPECS.update(_many(("storyboard_composer",), mode=ENGINE_MODE_WEB_NATIVE, flags=("video_studio_enabled",), handler="storyboard_composer"))
ENGINE_SPECS.update(_many(("subtitle_studio",), mode=ENGINE_MODE_WEB_NATIVE, flags=("subtitle_studio_enabled",), handler="subtitle_studio"))
# Format Lab is a bounded, stateless text transform that shares Subtitle
# Studio's maintenance flag.  It is not ASR, translation, TTS, dubbing, a
# file/media output, provider call, Bot companion, job, wallet or payment.
ENGINE_SPECS.update(_many(("subtitle_formats",), mode=ENGINE_MODE_WEB_NATIVE, flags=("subtitle_studio_enabled",), handler="subtitle_format_lab"))
ENGINE_SPECS.update(_many(("image_studio",), mode=ENGINE_MODE_WEB_NATIVE, flags=("image_studio_enabled",), handler="image_studio"))
# Prompt Composer adapts only the Bot's deterministic prompt templates.  It
# never inspects an image or calls a model/provider, creates media/output,
# saves an asset, creates a job, mutates a wallet/payment or publishes.
ENGINE_SPECS.update(_many(("image_prompt_composer",), mode=ENGINE_MODE_WEB_NATIVE, flags=("image_studio_enabled",), handler="image_prompt_composer"))
ENGINE_SPECS.update(_many(("documents", "documents_pdf"), mode=ENGINE_MODE_WEB_NATIVE, flags=("document_workspace_enabled",), handler="document_workspace"))
ENGINE_SPECS.update(_many(("chat",), mode=ENGINE_MODE_WEB_NATIVE, flags=("chat_workspace_enabled",), handler="chat_workspace"))
ENGINE_SPECS.update(_many(("analytics_workspace",), mode=ENGINE_MODE_WEB_NATIVE, flags=("analytics_workspace_enabled",), handler="analytics_workspace"))
ENGINE_SPECS.update(_many(("workboard",), mode=ENGINE_MODE_WEB_NATIVE, flags=("workboard_enabled",), handler="workboard"))
ENGINE_SPECS.update(_many(("support", "tickets"), mode=ENGINE_MODE_WEB_NATIVE, flags=("support_desk_enabled",), handler="support_desk"))

# Initial verified artifact scope. It includes only opt-in local image OCR;
# PDF OCR, AI edit/upscale, provider generation, translation, TTS, music and
# video rendering remain outside this direct Web-native execution boundary.
ENGINE_SPECS.update(_many(("documents_merge", "documents_split", "documents_compress"), mode=ENGINE_MODE_WEB_NATIVE, flags=("asset_vault_enabled", "document_operations_enabled"), handler="document_operations", asset_vault=True))
ENGINE_SPECS.update(_many(("documents_ocr",), mode=ENGINE_MODE_WEB_NATIVE, flags=("asset_vault_enabled", "document_operations_enabled", "image_ocr_enabled"), handler="image_ocr", asset_vault=True))
ENGINE_SPECS.update(_many(("documents_image_to_pdf",), mode=ENGINE_MODE_WEB_NATIVE, flags=("asset_vault_enabled", "document_operations_enabled", "image_to_pdf_enabled"), handler="image_to_pdf", asset_vault=True))
ENGINE_SPECS.update(_many(("documents_pdf_to_images",), mode=ENGINE_MODE_WEB_NATIVE, flags=("asset_vault_enabled", "document_operations_enabled", "pdf_to_images_enabled"), handler="pdf_to_images", asset_vault=True))
ENGINE_SPECS.update(_many(("documents_pdf_to_word",), mode=ENGINE_MODE_WEB_NATIVE, flags=("asset_vault_enabled", "document_operations_enabled", "pdf_to_word_enabled"), handler="pdf_to_word", asset_vault=True))
ENGINE_SPECS.update(_many(("image_resize",), mode=ENGINE_MODE_WEB_NATIVE, flags=("asset_vault_enabled", "image_operations_enabled", "image_resize_enabled"), handler="image_resize", asset_vault=True))
ENGINE_SPECS.update(_many(("image_edit",), mode=ENGINE_MODE_WEB_NATIVE, flags=("asset_vault_enabled", "image_operations_enabled", "image_enhance_enabled"), handler="image_enhance", asset_vault=True))

# Bot companion applies only to canonical/read-only product domains.  The
# public descriptor remains guarded even if an account happens to be linked:
# it must not leak integration state or promise canonical execution.
ENGINE_SPECS.update(_many(
    (
        "wallet", "wallet_topup", "packages", "membership", "jobs", "assets",
        "referrals", "rewards", "community", "guides", "growth_ai",
        "campaign_report", "image_history", "video_progress", "video_preview",
        "video_export", "voice_vault", "voice_preview", "voice_outputs",
        "music_library", "sfx_library", "music_upload", "service_status",
    ),
    mode=ENGINE_MODE_BOT_COMPANION,
    flags=("copyfast_enabled",),
    handler="canonical_companion",
    payment_mode="canonical_only",
))

_DEFAULT_GUARDED_SPEC = EngineSpec(
    feature_key="",
    mode=ENGINE_MODE_GUARDED,
    handler_name="adapter_pending",
    payment_mode="canonical_only",
)


def engine_spec(feature_key: str) -> EngineSpec:
    """Return the immutable classification; unknown work fails closed."""

    return ENGINE_SPECS.get(str(feature_key or "").strip(), _DEFAULT_GUARDED_SPEC)


def _flags_allow(spec: EngineSpec, flags: Mapping[str, object]) -> bool:
    return all(flags.get(name) is True for name in spec.required_flags)


def engine_descriptor(feature_key: str, flags: Mapping[str, object]) -> dict[str, str]:
    """Return display metadata only, never an execution capability grant.

    The public descriptor contains no internal handler, endpoint, maintenance
    flag, account/link state, price, payment, provider, output or path.  Each
    existing route remains its own authority for session, CSRF, ownership,
    idempotency and artifact validation.
    """

    spec = engine_spec(feature_key)
    mode = spec.mode if spec.mode in ENGINE_MODES else ENGINE_MODE_GUARDED
    state = "ready" if mode == ENGINE_MODE_WEB_NATIVE and _flags_allow(spec, flags) else "guarded"
    return {"mode": mode, "execution_state": state}
