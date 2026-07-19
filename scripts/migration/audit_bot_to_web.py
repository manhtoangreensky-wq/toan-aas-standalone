#!/usr/bin/env python3
"""Static-only TOAN AAS bot-to-web parity inventory.

This tool deliberately parses source files as text/AST only.  It never imports,
executes, or starts the Telegram bot, FastAPI application, provider adapters, or
environment files.  Generated output is designed for migration planning rather
than for declaring feature parity.

Example:
    python scripts/migration/audit_bot_to_web.py \
      --bot-root "D:\\TOANAAS\\bot telegram" \
      --web-root . \
      --bot-baseline-sha b29d0d474974075f4cba963d2c510f49d2d1b3e4
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "1.4"
SOURCE_SUFFIXES = {".py", ".js", ".html", ".htm", ".json", ".sql", ".md"}
EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    "__pycache__",
    "archive",
    "backups",
    "data",
    "files",
    "node_modules",
    "tests",
    "venv",
    ".venv",
}
NON_CANONICAL_BOT_SOURCE_MARKERS = (
    "nháp",
    "draft",
    "backup",
    "code hoàn chỉnh",
    "code cao nhất",
)
MAX_AST_PARSE_BYTES = 1_000_000
HTTP_VERBS = {"get", "post", "put", "patch", "delete", "options", "head"}
ADMIN_TERMS = (
    "admin",
    "operator",
    "runtime",
    "provider",
    "maintenance",
    "freeze",
    "unfreeze",
    "emergency",
    "backup",
    "security",
    "risk",
    "audit",
    "debug",
    "test_",
    "smoke",
    "pricing",
    "finance",
    "revenue",
    "refund",
)
TELEGRAM_ONLY_TERMS = (
    "ping",
    "takeover",
    "webhook",
    "test_",
    "smoke",
    "debug",
    "backup",
    "emergency",
    "freeze",
    "unfreeze",
    "worker",
    "provider_spend",
)
PROVIDER_MARKERS = {
    "PayOS": r"\bpayos\b",
    "Key4U": r"\bkey4u\b",
    "ShopAIKey": r"\bshopaikey\b",
    "MiniMax": r"\bminimax\b",
    "Deepgram": r"\bdeepgram\b",
    "DeepL": r"\bdeepl\b",
    "Gemini": r"\bgemini\b",
    "OpenAI": r"\bopenai\b",
    "ElevenLabs": r"\belevenlabs\b",
    "Fish Audio": r"\bfish(?:[_ -]?audio)?\b",
    "Suno": r"\bsuno\b",
    "Kling": r"\bkling\b",
    "Runway": r"\brunway\b",
    "Replicate": r"\breplicate\b",
    "Cloudinary": r"\bcloudinary\b",
    "Telegram": r"\btelegram\b",
}
FEATURE_TARGETS = {
    "chat_prompt": ("chat", "prompt", "caption", "hashtag", "hook", "script", "storyboard", "content_pack"),
    "image": ("image", "upscale", "remove_background", "background_remove"),
    "video": ("video", "multiscene", "text_to_video", "image_to_video", "trend", "quick_video"),
    "voice": ("voice", "tts", "clone"),
    "music": ("music", "song", "sfx", "audio"),
    "subtitle_dub": ("subtitle", "translate", "dub", "asr", "srt", "vtt"),
    "documents": ("pdf", "ocr", "document", "merge", "compress"),
    "wallet_billing": ("wallet", "credit", "xu", "payment", "payos", "topup"),
    "support": ("support", "ticket", "feedback"),
    "admin_erp": ("admin", "operator", "finance", "report", "audit"),
}
COMMAND_ROUTE_OVERRIDES = {
    "start": "/dashboard",
    "menu": "/dashboard",
    "quick": "/dashboard",
    "quickstart": "/dashboard",
    "truycapnhanh": "/dashboard",
    "profile": "/account",
    "account": "/account",
    "myid": "/account",
    "profile_user": "/account",
    "lang": "/account",
    "language": "/account",
    "en_vi": "/account",
    "vi_en": "/account",
    "ja_vi": "/account",
    "ko_vi": "/account",
    "zh_vi": "/account",
    "adjust_package": "/membership",
    "buy_plan": "/membership",
    "goi_beta": "/membership",
    "grant_combo": "/membership",
    "grant_monthly": "/membership",
    "grant_storage": "/membership",
    "member": "/membership",
    "member_policy": "/membership",
    "member_user": "/membership",
    "package_catalog": "/membership",
    "rank": "/membership",
    "trial_bonus_status": "/membership",
    "trial_status": "/membership",
    "user_packages": "/membership",
    "vip": "/membership",
    "vip_policy": "/membership",
    "vip_services": "/membership",
    "tools": "/tools",
    "tool_catalog": "/tools",
    "models": "/tools",
    "ai_models": "/tools",
    "api_recommend": "/tools",
    "feature_set": "/tools",
    "status": "/status",
    "ai_status": "/status",
    "data_status": "/status",
    "feature_status": "/status",
    "free_hub_status": "/status",
    "key4u_status": "/status",
    "local_status": "/status",
    "minimax_status": "/status",
    "orchestrator_status": "/status",
    "queue_status": "/status",
    "shopaikey_status": "/status",
    "storage_status": "/status",
    "system_public_status": "/status",
    "telegram_status": "/status",
    "toanaas_ai_status": "/status",
    "tool_public_status": "/status",
    "tool_status": "/status",
    "create_media": "/studio",
    "creative_flow": "/creative-flow",
    "film": "/studio",
    "media_factory": "/media-factory",
    "trend_research": "/trend-research",
    "video_factory_flow": "/video-studio/workflow",
    "story_video_factory": "/video-studio/story-video-plan",
    "story_motion_prompt": "/video-studio/story-video-plan",
    "pipeline": "/studio",
    "produce": "/studio",
    "quick": "/studio",
    "quickstart": "/studio",
    "render_center": "/studio",
    "shot_variations": "/studio",
    "truycapnhanh": "/studio",
    "media_library": "/assets",
    "play_media": "/assets",
    "select_media": "/assets",
    "memory": "/notes",
    "memory_plan": "/notes",
    "memory_set_plan": "/notes",
    "memory_status": "/notes",
    "note": "/notes",
    "notes": "/notes",
    "search_note": "/notes",
    "notes_category": "/notes",
    "notes_important": "/notes",
    "note_ai": "/notes",
    "note_archive": "/notes",
    "note_category": "/notes",
    "note_delete": "/notes",
    "note_priority": "/notes",
    "note_remind": "/notes",
    "note_tags": "/notes",
    "note_view": "/notes",
    "remind": "/reminders",
    "reminders": "/reminders",
    "reminder_cancel": "/reminders",
    "reminder_done": "/reminders",
    "reminder_pause": "/reminders",
    "reminder_resume": "/reminders",
    "repeat_daily": "/reminders",
    "repeat_weekly": "/reminders",
    "repeat_monthly": "/reminders",
    "repeat_yearly": "/reminders",
    "ref": "/referrals",
    "referral": "/referrals",
    "ref_link": "/referrals",
    "ref_stats": "/referrals",
    "invite": "/referrals",
    "gift": "/rewards",
    "nhanqua": "/rewards",
    "birthday": "/rewards",
    "birthday_gift_check": "/rewards",
    "my_promos": "/rewards",
    "promo": "/rewards",
    "promos": "/rewards",
    "magiamgia": "/rewards",
    "khuyenmai": "/rewards",
    "community": "/community",
    "hub": "/community",
    "toanaas_hub": "/community",
    "official_channels": "/community",
    "kenh_chinh_thuc": "/community",
    "wallet": "/wallet",
    "naptien": "/wallet/topup",
    "topup": "/wallet/topup",
    "thucong": "/wallet/topup",
    "support": "/support",
    "gopy": "/support",
    "tickets": "/tickets",
    "ticket_status": "/tickets",
    "support_status": "/tickets",
    "legal": "/legal",
    "terms": "/legal",
    "ads_policy": "/legal",
    "affiliate_policy": "/legal",
    "content_policy": "/legal",
    "dieukhoan": "/legal",
    "dieukhoan_xu": "/legal",
    "phaply": "/legal",
    "terms_xu": "/legal",
    "xu_terms": "/legal",
    "privacy": "/privacy",
    "data_delete": "/account",
    "mydata": "/account",
    "assets": "/assets",
    "asset_add": "/assets",
    "asset_send": "/assets",
    "job_status": "/jobs",
    "job_report": "/jobs",
    "job_ready": "/jobs",
    "job_context": "/jobs",
    "transcribe": "/asr",
    "remove_bg": "/image/remove-background",
    "image_to_pdf": "/documents/pdf",
    "pdf_to_images": "/documents/pdf-to-images",
    "ocr_image": "/documents/ocr",
    "ocr_pdf": "/api/v1/document-operations/ocr-pdf",
    "add_voice_to_video": "/video/add-ons",
    "video_music": "/video/add-ons",
    "help": "/guides",
    "source_help": "/guides/source-rights",
    "dubbing_help": "/guides/source-rights",
    "commands": "/guides",
    "huongdan": "/guides",
    "guide": "/guides",
    "hdsd": "/guides",
    "affiliate": "/affiliate-app",
    "campaign": "/campaign-app",
    "video": "/video-app",
    "media": "/media-app",
    "assistant": "/assistant-app",
    "linkweb": "/onboarding",
    "growth_ai": "/growth/ai",
    "campaign_report": "/campaign/report",
    "export_report": "/campaign/report",
    "mode": "/account",
    "beta_offer": "/membership",
    "goi_beta": "/membership",
    "uudai": "/rewards",
    "cancel": "/jobs",
}

# Dynamic Bot callbacks are intentionally inventory-only by default: the
# auditor must never evaluate their formatted values.  A small number of
# namespaces have nevertheless been manually reviewed against real signed Web
# surfaces.  These entries therefore mean only "this callback family has a
# guarded Web counterpart"; they do not prove a particular dynamic identifier,
# provider action, payment, job, delivery or admin permission works at runtime.
#
# Keep the routes at a workflow boundary rather than inventing a query-string
# deep link from a Telegram object ID.  The Web must obtain any record through
# its own signed, owner/role-checked API after navigation.
DYNAMIC_CALLBACK_TEMPLATE_ROUTE_OVERRIDES = (
    ("memory|", "/notes", "customer"),
    ("ticket|", "/support", "customer"),
    ("support|", "/support", "customer"),
    ("pipe|", "/workboard", "customer"),
    ("task|", "/workboard", "customer"),
    ("storyboard|", "/video-studio/storyboard-composer", "customer"),
    ("videodub|", "/dubbing", "customer"),
    ("tr_target|", "/dubbing", "customer"),
    ("tr_pick|", "/dubbing", "customer"),
    ("tr_more|", "/dubbing", "customer"),
    ("adconcept|", "/video-studio/cinematic-concept", "customer"),
    ("creative|", "/content-studio", "customer"),
    ("vproduct|", "/video/product", "customer"),
    ("videoaddon|", "/video/add-ons", "customer"),
    ("framevideo|", "/video-studio", "customer"),
    ("videoedit|", "/video-studio", "customer"),
    ("vfinal|", "/video/export", "customer"),
    ("license_music|", "/media-workspace", "customer"),
    ("select_media|", "/media-workspace", "customer"),
    ("play_media|", "/media-workspace", "customer"),
    ("create_media|", "/media-factory", "customer"),
    ("imgtool|", "/image", "customer"),
    ("prov|", "/image", "customer"),
    # Payment namespaces stay at a canonical, explicitly guarded entry point.
    # This does not turn the Web into a second PayOS/manual-payment writer.
    ("manual|", "/wallet/topup", "customer"),
    ("shopai|", "/wallet/topup", "customer"),
    ("shopai_video_job|", "/wallet/topup", "customer"),
    ("pkgbuy|", "/wallet/topup", "customer"),
    ("storage|", "/wallet/topup", "customer"),
    ("job|", "/jobs", "customer"),
    ("archive|", "/admin", "admin"),
    ("opmenu|", "/admin", "admin"),
)

# Exact, source-reviewed menu entries that can safely become a fresh signed Web
# navigation.  The keys stay in this *static auditor* only: raw Telegram
# callback tokens must never be sent to the browser.  The product-facing
# catalog in ``copyfast_registry.py`` exposes equivalent Web capability keys
# and routes without these Bot identifiers.
#
# This is intentionally a small finite allow-list.  A menu button often clears
# or creates Bot pending state, changes product context, mutates a canonical
# payment/storage/referral record, or opens an admin/provider control.  Those
# actions remain visible as guarded, Telegram-only, bridge-required, or
# unresolved until a dedicated Web contract exists; they must not inherit a
# route from a label or namespace prefix.
MENU_ACTION_REGISTRY: dict[str, dict[str, str]] = {
    "menu|main": {
        "capability_key": "workspace_home",
        "target": "/dashboard",
        "feature_key": "dashboard",
        "authority": "SIGNED_CUSTOMER",
        "launch_mode": "NAVIGATION_SHELL",
    },
    "menu|back": {
        "capability_key": "workspace_home",
        "target": "/dashboard",
        "feature_key": "dashboard",
        "authority": "SIGNED_CUSTOMER",
        "launch_mode": "NAVIGATION_SHELL",
    },
    "freehub|main": {
        "capability_key": "workspace_home",
        "target": "/dashboard",
        "feature_key": "dashboard",
        "authority": "SIGNED_CUSTOMER",
        "launch_mode": "NAVIGATION_SHELL",
    },
    "menu|main_profile": {
        "capability_key": "account",
        "target": "/account",
        "feature_key": "account",
        "authority": "SIGNED_CUSTOMER",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|main_topup": {
        "capability_key": "wallet_topup",
        "target": "/wallet/topup",
        "feature_key": "wallet_topup",
        "authority": "CORE_CANONICAL_PAYMENT",
        "launch_mode": "BRIDGE_GUARDED_PROXY",
    },
    "menu|main_docs": {
        "capability_key": "documents",
        "target": "/documents",
        "feature_key": "documents",
        "authority": "SIGNED_CUSTOMER",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|doc_tools": {
        "capability_key": "documents",
        "target": "/documents",
        "feature_key": "documents",
        "authority": "SIGNED_CUSTOMER",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|main_image": {
        "capability_key": "image_studio",
        "target": "/image-studio",
        "feature_key": "image_studio",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|main_video": {
        "capability_key": "video_studio",
        "target": "/video-studio",
        "feature_key": "video_studio",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|main_music": {
        "capability_key": "media_workspace",
        "target": "/media-workspace",
        "feature_key": "media_workspace",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|main_audio": {
        "capability_key": "media_workspace",
        "target": "/media-workspace",
        "feature_key": "media_workspace",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|main_guide": {
        "capability_key": "guides",
        "target": "/guides",
        "feature_key": "guides",
        "authority": "SIGNED_CUSTOMER",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|guide": {
        "capability_key": "guides",
        "target": "/guides",
        "feature_key": "guides",
        "authority": "SIGNED_CUSTOMER",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|support": {
        "capability_key": "support",
        "target": "/support",
        "feature_key": "support",
        "authority": "SIGNED_CUSTOMER",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|create_media": {
        "capability_key": "media_factory",
        "target": "/media-factory",
        "feature_key": "media_factory",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|video_workflow": {
        "capability_key": "video_factory_workflow",
        "target": "/video-studio/workflow",
        "feature_key": "video_factory_workflow",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|video_factory_flow": {
        "capability_key": "video_factory_workflow",
        "target": "/video-studio/workflow",
        "feature_key": "video_factory_workflow",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
}

# A dashboard is an intentional signed entry point for a person starting the
# Web App. It is not evidence that an arbitrary Bot callback has an equivalent
# Web workflow. Keep this distinction in the static report so a catch-all
# route cannot silently turn unreviewed callbacks into a parity claim.
DASHBOARD_ENTRYPOINT_COMMANDS = frozenset({"start", "menu"})
DASHBOARD_NAVIGATION_TEMPLATE_PREFIXES = ("menu|",)

# These are backlog dispositions, not route mappings.  They keep every
# dashboard fallback visible with an authority boundary and a concrete next
# contract, without pretending that a candidate route implements the Bot
# action.  A family moves out of this list only after its finite Bot actions
# have a reviewed Web-native or canonical-bridge contract and focused tests.
FALLBACK_FEATURE_DISPOSITIONS: dict[str, dict[str, Any]] = {
    "menu": {
        "priority": "P0",
        "candidate_boundary": "/features",
        "authority": "Web capability catalog",
        "next_contract": "Create an explicit menu-action catalog; never infer a destination from a button label or generic keyword.",
    },
    "vfinal": {
        "priority": "P0",
        "candidate_boundary": "/video/finishing",
        "authority": "Web-native private finishing or canonical Bot job bridge",
        "next_contract": "Split safe editing choices from render/export/payment actions; require a verified source, idempotency, validated output and owner-scoped delivery before any runtime action.",
    },
    "pkgbuy": {
        "priority": "P0",
        "candidate_boundary": "/wallet/topup",
        "authority": "Canonical Bot wallet/PayOS bridge",
        "next_contract": "Expose only verified package/read/confirm contracts. The Web must not price, credit Xu, finalize PayOS or create a second webhook.",
    },
    "storage": {
        "priority": "P0",
        "candidate_boundary": "/wallet/topup",
        "authority": "Canonical Bot wallet/PayOS bridge",
        "next_contract": "Keep storage purchase/credit changes canonical to the Bot until an owner-scoped bridge contract exists.",
    },
    "payosalert": {
        "priority": "P0",
        "candidate_boundary": "TELEGRAM_ONLY",
        "authority": "Canonical Bot PayOS/admin alert flow",
        "next_contract": "Classify each alert action by source evidence; do not convert Telegram dismissal, test or renewal buttons into Web payment actions.",
    },
    "job": {
        "priority": "P0",
        "candidate_boundary": "/jobs",
        "authority": "Canonical Bot job bridge",
        "next_contract": "Add only owner-scoped read/status projections first; retry/refund/charge/delivery require separate canonical action contracts.",
    },
    "vproduct": {
        "priority": "P1",
        "candidate_boundary": "/video-studio/script-to-screen-planner",
        "authority": "Web-native planning; runtime separately guarded",
        "next_contract": "Map finite Script-to-Screen planning choices to a recomputed Web Video Plan; render/export stays a distinct runtime boundary.",
    },
    "adconcept": {
        "priority": "P1",
        "candidate_boundary": "/video-studio/cinematic-concept",
        "authority": "Web-native planning; runtime separately guarded",
        "next_contract": "Map text concept choices to the cinematic planner; finalization/lock/runtime actions require an explicit capability contract.",
    },
    "storypack": {
        "priority": "P1",
        "candidate_boundary": "/video-studio/storyboard-composer",
        "authority": "Web-native planning",
        "next_contract": "Map finite brief/concept/template choices to the signed storyboard composer and keep copy/export effects locally reviewable.",
    },
    "create_media": {
        "priority": "P1",
        "candidate_boundary": "/media-factory",
        "authority": "Web-native planning",
        "next_contract": "Map Quick Idea choices to an explicit Media Factory blueprint; media generation and provider calls remain unavailable until a separate runtime exists.",
    },
    "marketing": {
        "priority": "P1",
        "candidate_boundary": "/campaign-app",
        "authority": "Web campaign planning and controlled operations",
        "next_contract": "Map brief/KPI/schedule choices to account-owned campaign plans; publishing and canonical analytics remain separately authorized.",
    },
    "docflow": {
        "priority": "P1",
        "candidate_boundary": "/documents",
        "authority": "Web-native private document operations",
        "next_contract": "Map document selection/confirmation only to validated Asset Vault-backed operations; preserve output validation and private delivery constraints.",
    },
    "archive": {
        "priority": "P1",
        "candidate_boundary": "/admin",
        "authority": "Canonical Bot admin or separate Web admin archive",
        "next_contract": "Separate Bot archive state from the isolated Web admin document archive; every write needs canonical role, CSRF, confirmation and audit evidence.",
    },
    "opmenu": {
        "priority": "P1",
        "candidate_boundary": "/admin",
        "authority": "Server-authorized Admin ERP",
        "next_contract": "Map every operations category to a role-checked ERP module; browser navigation must never grant Bot/admin authority.",
    },
    "motion": {
        "priority": "P1",
        "candidate_boundary": "/video-studio/image-motion-planner",
        "authority": "Web-native planning",
        "next_contract": "Map finite motion suggestions to the owner-scoped Image Motion planner; source inspection/rendering remains a separate capability.",
    },
    "tvflow": {
        "priority": "P1",
        "candidate_boundary": "/video-studio",
        "authority": "Source review required",
        "next_contract": "Recover the exact Bot handler state machine before mapping cancel/rewrite/confirm actions; do not infer a render or content mutation contract.",
        "source_evidence": "Bot handler `handle_trend_video_flow_callback` reads and clears pending workflow/confirmation state; confirmation can inspect package/Xu state, record billing events, and enter provider/job guards.",
        "source_dispositions": ("SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
    },
    "tr_pick": {
        "priority": "P1",
        "candidate_boundary": "/dubbing",
        "authority": "Web-native subtitle/dubbing boundary",
        "next_contract": "Require an explicit owner-scoped source selection contract before mapping Telegram file-pick actions.",
    },
    "freehub": {
        "priority": "P2",
        "candidate_boundary": "/features",
        "authority": "Web capability catalog",
        "next_contract": "Map remaining hub/root navigation to a named Web catalog entry; do not import Bot pending text or hidden Telegram state.",
    },
    "lang": {
        "priority": "P2",
        "candidate_boundary": "/account",
        "authority": "Signed Web profile locale",
        "next_contract": "Map supported UI locales through the signed account preference. Bot-only languages need a reviewed locale bundle before being advertised.",
    },
    "aspect_ratio_orphan": {
        "priority": "P2",
        "candidate_boundary": "parent_workflow_required",
        "authority": "Parent Web workflow",
        "next_contract": "Resolve orphan ratio tokens from their source keyboard/handler before mapping; a ratio alone must not become a global browser action.",
        "source_evidence": "Bare ratio tokens are reused by image/video selection keyboards and can feed provider/package flows; static source does not prove a single safe parent workflow.",
        "source_dispositions": ("PARENT_WORKFLOW_REQUIRED", "NO_RUNTIME_CLAIM"),
    },
    "affiliate": {
        "priority": "P1",
        "candidate_boundary": "separate_affiliate_domain_required",
        "authority": "Separate affiliate/referral business domain",
        "next_contract": "Do not map Bot affiliate navigation into Partner CRM. Define attribution, commission, payout, promotion and membership authority before exposing a Web affiliate action.",
        "source_dispositions": ("SEPARATE_BUSINESS_DOMAIN_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "Bot affiliate menu/actions are not evidence that the Web Partner CRM owns referral attribution, commission, payout, promotion or membership behavior.",
    },
    "freelance": {
        "priority": "P1",
        "candidate_boundary": "separate_freelance_domain_required",
        "authority": "Separate marketplace/freelance business domain",
        "next_contract": "Define an account-owned freelance workflow and moderation/data policy before exposing a Web action; do not repurpose Support or CRM navigation as parity.",
        "source_dispositions": ("SEPARATE_BUSINESS_DOMAIN_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "The Bot's freelance choices are informational/navigation state and have no reviewed Web marketplace, lead-routing or service-delivery contract.",
    },
    "social_navigation": {
        "priority": "P2",
        "candidate_boundary": "separate_social_domain_required",
        "authority": "Separate social publishing/integration domain",
        "next_contract": "Do not turn a Bot social shortcut into a publish/account integration. Define linked-account ownership, permissions and publish controls first.",
        "source_dispositions": ("SEPARATE_BUSINESS_DOMAIN_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "Social shortcut callbacks do not contain a signed Web social account, publishing permission or provider contract.",
    },
    "locale_navigation": {
        "priority": "P2",
        "candidate_boundary": "/account",
        "authority": "Signed Web profile locale",
        "next_contract": "Map a locale action only after the signed Web account preference, supported bundle and fallback behavior are explicitly reviewed; do not replay Bot language/menu state.",
        "source_dispositions": ("SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "Bot language callbacks write Bot user preference and redraw a localized Telegram menu. They are not a browser locale mutation contract.",
    },
    "root_navigation": {
        "priority": "P2",
        "candidate_boundary": "/features",
        "authority": "Web capability catalog",
        "next_contract": "Review the exact Bot screen/state before adding a named Web catalog entry; a legacy back button must not reset or import Telegram state.",
        "source_dispositions": ("SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "A Bot back/root callback can depend on the previous Telegram screen and pending state, which the Web catalog intentionally does not receive.",
    },
    "tr_transcribe": {
        "priority": "P1",
        "candidate_boundary": "/asr",
        "authority": "Owner-scoped Web ASR runtime boundary",
        "next_contract": "Require a verified owner-scoped source asset plus a dedicated ASR execution/delivery contract; do not infer it from the Bot's recent-audio Telegram slot.",
        "source_dispositions": ("SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "Bot `tr_transcribe` requires recent Telegram audio/video input and delegates to Bot transcription logic; it is not an existing Web ASR execution claim.",
    },
    "unstructured": {
        "priority": "P0",
        "candidate_boundary": "source_review_required",
        "authority": "Source review required",
        "next_contract": "Classify delimiter-free concrete callbacks with handler-level evidence before assigning any Web route or authority; dispatcher registrations are tracked separately and do not become product actions.",
        "source_evidence": "The backlog contains concrete callback values only. Broad `CallbackQueryHandler` registrations are dispatch evidence, not end-user callback actions or Web parity claims.",
        "source_dispositions": ("SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
    },
}
DEFAULT_FALLBACK_FEATURE_DISPOSITION: dict[str, Any] = {
    "priority": "P1",
    "candidate_boundary": "source_review_required",
    "authority": "Source review required",
    "next_contract": "Review the finite Bot handler branch and assign a Web-native workflow, guarded runtime boundary, canonical bridge contract, admin-only surface or TELEGRAM_ONLY.",
    "source_evidence": "Static source evidence requires a finite handler/route decision before any Web mapping.",
    "source_dispositions": ("SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
}

# These public Bot commands can contain words such as ``factory`` or mention
# an admin review in their handler, which the generic static heuristic sees as
# an admin signal.  Their command registrations and customer-facing handlers
# are nevertheless public.  Keep this narrow, explicit list next to the
# route overrides so the audit does not incorrectly point a customer command
# at a non-existent ``/admin/<command>`` page.
PUBLIC_CUSTOMER_COMMAND_OVERRIDES = frozenset(
    {
        "creative_flow",
        "media_factory",
        "trend_research",
        "video_factory_flow",
        "story_video_factory",
        "story_motion_prompt",
        "source_help",
        "dubbing_help",
    }
)
SECRET_VALUE_PATTERNS = (
    re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{20,}\b"),  # Telegram-style token
    re.compile(r"(?i)\b(?:sk|pk|rk|ghp|xox[baprs]|eyJ)[-_A-Za-z0-9]{12,}\b"),
    re.compile(
        r"(?i)((?:api[_ -]?key|access[_ -]?token|refresh[_ -]?token|secret|password)\s*[=:]\s*)"
        r"([^\s,'\";]{6,})"
    ),
)
SQL_TABLE_RE = re.compile(
    r"\b(?P<operation>CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?|INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+"
    r"[`\"\[]?(?P<table>[A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)
SQL_NOISE_WORDS = {
    "and", "c", "failed", "from", "mode", "ownership", "performance", "profile",
    "railway", "skipped", "the", "v", "with", "after", "before", "current", "event",
}
ENV_LITERAL_RE = re.compile(r"\b([A-Z][A-Z0-9_]{2,})\b")
COMMAND_HANDLER_RE = re.compile(
    r"\bCommandHandler\s*\(\s*(['\"])(?P<command>[^'\"\r\n]+)\1\s*,\s*(?P<handler>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)"
)
CALLBACK_HANDLER_RE = re.compile(r"\bCallbackQueryHandler\s*\(\s*(?P<handler>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)")
CALLBACK_PATTERN_RE = re.compile(
    # The canonical Bot keeps this multi-megabyte registration block in raw
    # strings (``pattern=r\"^flow\\|\"``).  The AST path already handles raw
    # strings, but its bounded large-file parser must preserve the same
    # handler/pattern evidence instead of incorrectly calling them catch-all.
    r"\bCallbackQueryHandler\s*\(\s*(?P<handler>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)(?:(?!\bCallbackQueryHandler\s*\()[\s\S]){0,360}?\bpattern\s*=\s*(?:[rR])?(?P<quote>['\"])(?P<pattern>[^'\"\r\n]+)(?P=quote)"
)
CALLBACK_DATA_RE = re.compile(r"\bcallback_data\s*=\s*(['\"])(?P<token>[^'\"\r\n]+)\1")
# Keep f-string callbacks separate from literal callback data.  A template such
# as ``f\"{prefix}|save\"`` is useful audit evidence, but it is not proof of a
# concrete browser action and must never be evaluated by this static tool.
CALLBACK_DYNAMIC_DATA_RE = re.compile(
    r"\bcallback_data\s*=\s*f(?P<quote>['\"])(?P<body>[^'\"\r\n]+)(?P=quote)"
)
# The Bot's keyboard builders also accept ``(label, callback_token)`` rows.
# Its canonical monolithic source is deliberately handled by the bounded regex
# extractor below, so inventorying only ``callback_data=...`` would omit most
# of those buttons.  Keep this intentionally narrow: a two-value tuple must
# have a callback-shaped second literal (``namespace|action`` or
# ``namespace:action``), never an arbitrary display/data pair.
CALLBACK_TUPLE_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_])\((?:[^()\r\n]|\\.)*?,\s*(?P<quote>['\"])(?P<token>"
    r"[A-Za-z0-9][A-Za-z0-9_.-]*(?:[|:][A-Za-z0-9_.:-]+)+)(?P=quote)\s*\)"
)
CALLBACK_LITERAL_TOKEN_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_.-]*(?:[|:][A-Za-z0-9_.:-]+)+$"
)
BARE_NUMERIC_ASPECT_RATIO_RE = re.compile(r"^\d{1,3}:\d{1,3}$")
CALLBACK_DYNAMIC_TUPLE_RE = re.compile(
    r"(?<![A-Za-z0-9_])\((?:[^()\r\n]|\\.)*?,\s*f(?P<quote>['\"])(?P<body>[^'\"\r\n]+)(?P=quote)\s*\)"
)
CALLBACK_TEMPLATE_SEGMENT_RE = r"(?:[A-Za-z0-9][A-Za-z0-9_.-]*|\{\*\})"
CALLBACK_TEMPLATE_TOKEN_RE = re.compile(
    rf"^{CALLBACK_TEMPLATE_SEGMENT_RE}(?:[|:]{CALLBACK_TEMPLATE_SEGMENT_RE})+$"
)
CALLBACK_TEMPLATE_FORMATTED_VALUE_RE = re.compile(r"\{[^{}]*\}")
# The three helpers below deliberately share the same reviewed, literal Web
# planner prefixes.  Their raw f-string callback templates remain in the
# inventory, but a source-only pass may derive the two concrete callback
# families only when it sees a direct literal caller.  It must never follow a
# variable ``flow``/``prefix`` value or turn ``{*}|...`` into a generic browser
# callback namespace.
GUIDED_VIDEO_KEYBOARD_HELPER_RE = re.compile(
    r"(?ms)^\s*def\s+(?P<helper>guided_video_(?:motion|music|result)_keyboard)\s*\(\s*prefix\b"
    r"(?P<body>.*?)(?=^\s*(?:async\s+)?def\s|\Z)"
)
GUIDED_VIDEO_LITERAL_PREFIX_CALL_RE = re.compile(
    r"\b(?P<helper>guided_video_(?:motion|music|result)_keyboard)\s*\(\s*"
    r"(?P<quote>['\"])(?P<prefix>promptvideo|imagevideo)(?P=quote)"
)
GUIDED_VIDEO_BACK_TEMPLATE_EXPANSIONS = {
    # ``back_action`` is selected locally in this one reviewed helper.  Do not
    # try to evaluate arbitrary formatted callback segments elsewhere.
    ("guided_video_motion_keyboard", "{*}|{*}"): {
        "promptvideo": "promptvideo|back_choices",
        "imagevideo": "imagevideo|back_style",
    },
}
CONVERSATION_RE = re.compile(r"\bConversationHandler\s*\(")
DECORATOR_ROUTE_RE = re.compile(
    r"@(?P<app>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\.(?P<verb>get|post|put|patch|delete|options|head)\s*\(\s*(['\"])(?P<path>/[^'\"\r\n]*)\3",
    re.IGNORECASE,
)
ADD_ROUTE_RE = re.compile(
    r"\badd_api_route\s*\(\s*(['\"])(?P<path>/[^'\"\r\n]*)\1\s*,\s*(?P<endpoint>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)"
)
ENV_CALL_RE = re.compile(r"\b(?:os\.getenv|os\.environ\.get|_env|env)\s*\(\s*(['\"])(?P<name>[A-Z][A-Z0-9_]{2,})\1")
ENV_SUBSCRIPT_RE = re.compile(r"\bos\.environ\s*\[\s*(['\"])(?P<name>[A-Z][A-Z0-9_]{2,})\1\s*\]")
TASK_CALL_RE = re.compile(r"\b(?P<kind>create_task|add_task|submit|delay|enqueue)\s*\(\s*(?P<target>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)")
JOB_FUNCTION_RE = re.compile(
    r"^(?:async\s+)?def\s+(?P<target>[A-Za-z_]\w*(?:worker|job|queue|background|scheduler)\w*)\s*\(",
    re.IGNORECASE | re.MULTILINE,
)
CORE_BRIDGE_FILE = "webapp_core_bridge.py"
CORE_BRIDGE_DEFAULT_PREFIX = "/internal/v1"
CORE_BRIDGE_CALL_NAMES = frozenset({"_bridge", "bridge_request"})
TELEGRAM_LINK_CALLBACK_HEADERS = (
    "X-TOAN-AAS-BRIDGE-TOKEN",
    "X-TOAN-AAS-Timestamp",
    "X-TOAN-AAS-Request-ID",
    "X-TOAN-AAS-Signature",
)
TELEGRAM_LINK_CALLBACK_ENV = (
    "WEBAPP_LINK_CALLBACK_URL",
    "WEBAPP_LINK_CALLBACK_TOKEN",
    "WEBAPP_LINK_CALLBACK_HMAC_SECRET",
)


def _callback_signature_shape_observed(text: str, *, side: str) -> bool:
    """Check the static body/timestamp/request-id/path HMAC shape.

    This remains a text-only release guard: it does not execute either
    service, read a secret, or make a network request.  It catches the most
    dangerous integration drift where both sides still mention the same
    headers but no longer sign the same canonical material.
    """
    compact = re.sub(r"\s+", "", text or "")
    shared = "hashlib.sha256(body).hexdigest()" in compact
    if side == "bot":
        return all(
            (
                shared,
                'f"{timestamp}.{request_id}.POST.{callback_path}.{digest}".encode("utf-8")' in compact,
                'hmac.new(callback_secret.encode("utf-8"),material,hashlib.sha256).hexdigest()' in compact,
            )
        )
    if side == "web":
        return all(
            (
                shared,
                'f"{timestamp}.{request_id}.{request.method.upper()}.{request.url.path}.{digest}".encode("utf-8")' in compact,
                'hmac.new(secret.encode("utf-8"),material,hashlib.sha256).hexdigest()' in compact,
            )
        )
    raise ValueError("callback signature side must be bot or web")


def _literal_template(node: ast.AST | None) -> str | None:
    """Return a static route template without evaluating source code.

    The Web compatibility layer deliberately builds a few route values with
    f-strings (for example ``/jobs/{job_id}``).  A generic source inventory
    cannot execute those expressions, but it can still keep their path shape
    and compare it to the Bot router.  A ``{*}`` segment means "dynamic
    source value", never a value observed at runtime.
    """

    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return _redact_text(node.value)
    if isinstance(node, ast.JoinedStr):
        values: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                values.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                values.append("{*}")
            else:
                return None
        return _redact_text("".join(values))
    return None


def _normalise_route_template(value: str) -> str:
    """Normalise a route only for static method/path comparison."""

    route = "/" + str(value or "").strip().lstrip("/")
    route = re.sub(r"/{2,}", "/", route)
    if route != "/" and route.endswith("/"):
        route = route.rstrip("/")
    return route


def _route_segment_is_dynamic(value: str) -> bool:
    return value == "{*}" or bool(re.fullmatch(r"\{[^/{}]+\}", value))


def _route_template_matches(web_path: str, bot_path: str) -> bool:
    """Compare route shapes while respecting dynamic path segments.

    This is intentionally a narrow static assertion: the method must still
    match and literal segments must still agree.  It does *not* prove that a
    dynamic feature/action allowlist is safe at runtime; the API tests remain
    responsible for that validation.
    """

    web_segments = [segment for segment in _normalise_route_template(web_path).split("/") if segment]
    bot_segments = [segment for segment in _normalise_route_template(bot_path).split("/") if segment]
    if len(web_segments) != len(bot_segments):
        return False
    return all(
        left == right or _route_segment_is_dynamic(left) or _route_segment_is_dynamic(right)
        for left, right in zip(web_segments, bot_segments)
    )


def _redact_text(value: str) -> str:
    """Mask secret-shaped literals before they can reach a report or document."""

    text = str(value)
    for pattern in SECRET_VALUE_PATTERNS:
        if pattern.groups >= 2:
            text = pattern.sub(lambda match: f"{match.group(1)}***REDACTED***", text)
        else:
            text = pattern.sub("***REDACTED***", text)
    # A large static numeric identifier is usually a chat/user/order identifier.
    return re.sub(r"\b\d{12,}\b", "***REDACTED_ID***", text)


def _sanitize(value: Any) -> Any:
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_sanitize(item) for item in value]
    return value


def _is_excluded_source_dir(name: str) -> bool:
    """Return whether a directory is outside the canonical static inventory.

    Pytest creates temporary copied project trees such as ``_pytest_*`` in a
    checkout.  Those copies can contain valid-looking FastAPI routes and would
    otherwise inflate the Web inventory.  Prune them before walking so an
    audit only describes source-of-truth files and does not need permission to
    inspect a stale test artifact.
    """

    return name in EXCLUDED_DIRS or name.startswith("_pytest_")


def _source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    # ``Path.rglob`` cannot prune child directories.  ``os.walk`` lets this
    # static-only audit skip generated snapshots before attempting to read
    # them, which also keeps inaccessible temporary test directories harmless.
    for directory, child_dirs, filenames in os.walk(root, topdown=True, onerror=lambda _error: None):
        child_dirs[:] = [name for name in child_dirs if not _is_excluded_source_dir(name)]
        base = Path(directory)
        for filename in filenames:
            path = base / filename
            if path.suffix.lower() not in SOURCE_SUFFIXES:
                continue
            try:
                if path.is_file():
                    files.append(path)
            except OSError:
                # The source audit is read-only and must not fail merely
                # because an unrelated generated artifact disappeared.
                continue
    return sorted(files)


def _active_inventory_files(project_kind: str, root: Path, files: list[Path]) -> tuple[list[Path], list[str]]:
    """Exclude clearly named Bot drafts from the source-of-truth inventory.

    The local bot worktree keeps several human-named historical snippets next
    to ``bot.py``. They are useful reference material but are not imported by
    the deployed entrypoint, so counting their duplicate command registrations
    would overstate parity and can contradict the canonical Bot implementation.
    Web App files are never filtered by this rule.
    """

    if project_kind != "telegram_bot":
        return files, []
    active: list[Path] = []
    excluded: list[str] = []
    for path in files:
        candidate = _relative(path, root).casefold()
        if any(marker in candidate for marker in NON_CANONICAL_BOT_SOURCE_MARKERS):
            excluded.append(_relative(path, root))
            continue
        active.append(path)
    return active, excluded


STATIC_FROM_IMPORT_RE = re.compile(
    r"(?m)^\s*from\s+(?P<module>\.*[A-Za-z_][A-Za-z0-9_.]*)\s+import\b"
)
STATIC_IMPORT_RE = re.compile(
    r"(?m)^\s*import\s+(?P<modules>[A-Za-z_][A-Za-z0-9_.]*(?:\s+as\s+[A-Za-z_]\w*)?(?:\s*,\s*[A-Za-z_][A-Za-z0-9_.]*(?:\s+as\s+[A-Za-z_]\w*)?)*)"
)
DYNAMIC_HANDLER_IMPORT_RE = re.compile(
    r"\b(?:importlib\.)?import_module\s*\(\s*['\"]handlers(?:[.'\"]|$)|\b__import__\s*\(\s*['\"]handlers(?:[.'\"]|$)"
)


def _local_python_module_index(root: Path) -> dict[str, Path]:
    """Return local module names without importing or executing any source."""

    modules: dict[str, Path] = {}
    for path in _source_files(root):
        if path.suffix.lower() != ".py":
            continue
        relative_parts = list(path.relative_to(root).with_suffix("").parts)
        if not relative_parts:
            continue
        if relative_parts[-1] == "__init__":
            relative_parts.pop()
        if relative_parts:
            modules[".".join(relative_parts)] = path
    return modules


def _static_import_modules(text: str) -> set[str]:
    """Collect literal import roots from source text without resolving code."""

    modules = {match.group("module").lstrip(".") for match in STATIC_FROM_IMPORT_RE.finditer(text)}
    for match in STATIC_IMPORT_RE.finditer(text):
        for value in str(match.group("modules") or "").split(","):
            module = value.strip().split(" as ", 1)[0].strip()
            if module:
                modules.add(module)
    return {module for module in modules if module}


def _unreferenced_handler_module_observation(root: Path) -> dict[str, Any]:
    """Keep legacy ``handlers/`` source visible without claiming Bot runtime.

    The observed Bot entrypoint is the local ``bot.py`` module.  Its static
    import closure is enough to answer one narrow audit question: does the
    entrypoint reference the legacy ``handlers`` package at all?  If it does
    not, records in that directory remain source evidence but are excluded
    from the *observed runtime* parity denominator.  A dynamic literal import
    is treated conservatively as reachable rather than being silently pruned.
    """

    module_index = _local_python_module_index(root)
    handler_files = sorted(
        relative
        for module, path in module_index.items()
        if module == "handlers" or module.startswith("handlers.")
        for relative in [_relative(path, root)]
    )
    entrypoint = root / "bot.py"
    if not handler_files:
        return {
            "status": "NO_HANDLER_MODULES_DISCOVERED",
            "observed_entrypoint": "bot.py",
            "unreferenced_module_files": [],
            "reachable_local_modules": [],
            "note": "No local handlers package was discovered in the static source tree.",
        }
    if not entrypoint.is_file():
        return {
            "status": "ENTRYPOINT_NOT_OBSERVED",
            "observed_entrypoint": "bot.py",
            "unreferenced_module_files": [],
            "reachable_local_modules": [],
            "note": "No bot.py entrypoint was available, so handler-module runtime reachability was not inferred.",
        }

    reachable_paths: set[Path] = set()
    pending = [entrypoint]
    dynamic_handler_import_seen = False
    while pending:
        path = pending.pop()
        if path in reachable_paths:
            continue
        reachable_paths.add(path)
        try:
            text = _read_source(path)
        except OSError:
            continue
        if DYNAMIC_HANDLER_IMPORT_RE.search(text):
            dynamic_handler_import_seen = True
            break
        for module in _static_import_modules(text):
            if module == "handlers" or module.startswith("handlers."):
                return {
                    "status": "HANDLERS_REACHABLE_FROM_OBSERVED_ENTRYPOINT",
                    "observed_entrypoint": "bot.py",
                    "unreferenced_module_files": [],
                    "reachable_local_modules": sorted(_relative(item, root) for item in reachable_paths),
                    "note": "A literal handlers import is reachable from bot.py, so no handler source is excluded from the observed runtime denominator.",
                }
            candidate = module_index.get(module)
            if candidate is not None and candidate not in reachable_paths:
                pending.append(candidate)

    reachable = sorted(_relative(item, root) for item in reachable_paths)
    if dynamic_handler_import_seen:
        return {
            "status": "DYNAMIC_HANDLER_IMPORT_POSSIBLE",
            "observed_entrypoint": "bot.py",
            "unreferenced_module_files": [],
            "reachable_local_modules": reachable,
            "note": "A literal dynamic handlers import is reachable from bot.py, so the audit keeps all handler sources in the observed runtime denominator.",
        }
    return {
        "status": "HANDLERS_UNREFERENCED_BY_OBSERVED_ENTRYPOINT",
        "observed_entrypoint": "bot.py",
        "unreferenced_module_files": handler_files,
        "reachable_local_modules": reachable,
        "note": "No static handlers import is reachable from bot.py. These files remain static source evidence but do not prove active Bot runtime behavior.",
    }


def _read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _line_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _literal_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return _redact_text(node.value)
    if isinstance(node, ast.JoinedStr):
        return "<dynamic-fstring>"
    if isinstance(node, ast.Name):
        return f"<dynamic:{node.id}>"
    return None


def _callback_template_from_text(value: str) -> str | None:
    """Canonicalise a callback f-string without evaluating any expression.

    The inventory only retains callback-shaped literal segments and replaces
    every formatted expression with ``{*}``.  This is deliberately weaker than
    constant propagation: a template is an unresolved source marker, not a
    list of values that could be sent by a browser.
    """

    template = CALLBACK_TEMPLATE_FORMATTED_VALUE_RE.sub("{*}", str(value or ""))
    if not CALLBACK_TEMPLATE_TOKEN_RE.fullmatch(template):
        return None
    return _redact_text(template)


def _callback_template_from_ast(node: ast.AST | None) -> str | None:
    """Return a callback f-string template from AST without evaluating it."""

    if not isinstance(node, ast.JoinedStr):
        return None
    values: list[str] = []
    for value in node.values:
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            values.append(value.value)
        elif isinstance(value, ast.FormattedValue):
            values.append("{*}")
        else:
            return None
    return _callback_template_from_text("".join(values))


def _is_bare_numeric_aspect_ratio(value: str) -> bool:
    """Return whether a tuple literal is data such as ``16:9``, not an action.

    A numeric-leading namespace can be a valid callback (for example
    ``2fa|enable``), so this is intentionally narrower than a first-character
    grammar change.  Only a standalone numeric ratio is excluded from the
    keyboard-row callback heuristic; direct ``callback_data=...`` literals
    continue to be inventoried as source evidence.
    """

    return bool(BARE_NUMERIC_ASPECT_RATIO_RE.fullmatch(str(value or "")))


def _tuple_callback_token(node: ast.AST) -> str | None:
    """Return a static keyboard-row callback token without evaluating source.

    The Bot keeps many keyboards as literal ``(label, callback_token)`` rows
    for helper functions such as ``build_2col_keyboard``.  A tuple is only
    treated as a callback row when it has exactly two values and the second is
    a conservative callback-shaped literal.  This avoids inventing callback
    inventory entries from arbitrary application tuples while keeping this
    audit text/AST-only.
    """

    if not isinstance(node, ast.Tuple) or len(node.elts) != 2:
        return None
    token = _literal_string(node.elts[1])
    if token and CALLBACK_LITERAL_TOKEN_RE.fullmatch(token) and not _is_bare_numeric_aspect_ratio(token):
        return token
    return None


def _tuple_callback_template(node: ast.AST) -> str | None:
    """Return a dynamic keyboard-row callback template, never a concrete token."""

    if not isinstance(node, ast.Tuple) or len(node.elts) != 2:
        return None
    return _callback_template_from_ast(node.elts[1])


def _kwarg(call: ast.Call, name: str) -> ast.AST | None:
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _handler_name(node: ast.AST | None) -> str:
    if node is None:
        return "<missing>"
    name = _call_name(node)
    return name or "<dynamic>"


FUNCTION_DEFINITION_RE = re.compile(
    r"(?m)^(?:async\s+)?def\s+(?P<name>[A-Za-z_]\w*)\s*\(",
)
ADMIN_GUARD_RE = re.compile(
    r"\bif\s+not\s+(?:is_admin_user|is_admin_or_owner|is_owner_user)\s*\("
    r"|\b(?:await\s+)?(?:require_admin|require_canonical_admin)\s*\("
    r"|\bif\s+str\([^\n]{0,200}?\)\s*!=\s*ADMIN_ID\b",
)
ADMIN_HANDLER_DELEGATE_RE = re.compile(
    r"\breturn\s+await\s+((?:cmd_[A-Za-z_]\w*|send_admin_[A-Za-z_]\w*|send_ai_admin_report|send_report_chart))\s*\(",
)


def _static_admin_guarded_handlers(text: str) -> set[str]:
    """Find handlers whose own function body has a static admin guard.

    The frozen Bot has many command names that do not contain ``admin`` but
    immediately reject callers through ``is_admin_user``.  This scans source
    text only (including the large monolithic ``bot.py`` path that is not AST
    parsed) so the parity matrix does not advertise a sensitive operation as a
    customer surface merely because its command name is neutral.
    """

    definitions = list(FUNCTION_DEFINITION_RE.finditer(text))
    guarded: set[str] = set()
    body_heads: dict[str, str] = {}
    for index, match in enumerate(definitions):
        body_end = definitions[index + 1].start() if index + 1 < len(definitions) else len(text)
        # Admin checks in this Bot occur near the top of a command handler.
        # Bound the scan to keep the static audit predictable for monolithic
        # generated source while avoiding a cross-function false positive.
        body_head = text[match.end():min(body_end, match.end() + 8_000)]
        body_heads[match.group("name")] = body_head
        if ADMIN_GUARD_RE.search(body_head):
            guarded.add(match.group("name"))
    # A few Bot compatibility commands are thin aliases which delegate to a
    # separately guarded handler. Propagate only direct aliases to a command
    # handler or explicitly named admin-report helper; this stays static,
    # bounded and avoids treating ordinary shared UI helpers as an
    # authorization guarantee.
    changed = True
    while changed:
        changed = False
        for name, body_head in body_heads.items():
            if name in guarded:
                continue
            if any(target in guarded for target in ADMIN_HANDLER_DELEGATE_RE.findall(body_head)):
                guarded.add(name)
                changed = True
    return guarded


def _record_location(root: Path, path: Path, node: ast.AST) -> dict[str, Any]:
    return {"file": _relative(path, root), "line": int(getattr(node, "lineno", 0) or 0)}


def _append_unique(records: list[dict[str, Any]], seen: set[tuple[Any, ...]], record: dict[str, Any], keys: Iterable[str]) -> None:
    def freeze(value: Any) -> Any:
        if isinstance(value, list):
            return tuple(freeze(item) for item in value)
        if isinstance(value, dict):
            return tuple(sorted((str(key), freeze(item)) for key, item in value.items()))
        if isinstance(value, set):
            return tuple(sorted(freeze(item) for item in value))
        return value

    signature = tuple(freeze(record.get(key)) for key in keys)
    if signature not in seen:
        seen.add(signature)
        records.append(record)


def _extract_env_from_ast(tree: ast.AST, root: Path, path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_name = _call_name(node.func)
            captures_env = call_name in {"os.getenv", "os.environ.get", "_env", "env"}
            if captures_env and node.args:
                name = _literal_string(node.args[0])
                if name and ENV_LITERAL_RE.fullmatch(name):
                    record = {"name": name, **_record_location(root, path, node)}
                    _append_unique(records, seen, record, ("name", "file", "line"))
        elif isinstance(node, ast.Subscript) and _call_name(node.value) == "os.environ":
            name = _literal_string(node.slice)
            if name and ENV_LITERAL_RE.fullmatch(name):
                record = {"name": name, **_record_location(root, path, node)}
                _append_unique(records, seen, record, ("name", "file", "line"))
    return records


def _extract_large_python_file(
    text: str,
    root: Path,
    path: Path,
    commands: list[dict[str, Any]],
    callback_handlers: list[dict[str, Any]],
    callback_data: list[dict[str, Any]],
    callback_templates: list[dict[str, Any]],
    conversations: list[dict[str, Any]],
    routes: list[dict[str, Any]],
    background_jobs: list[dict[str, Any]],
    env_references: list[dict[str, Any]],
    seen: dict[str, set[tuple[Any, ...]]],
) -> None:
    """Fast, bounded regex extraction for monolithic generated Python files.

    Full AST construction for a multi-megabyte bot module can be prohibitively
    expensive. These expressions deliberately cover registration/configuration
    patterns and retain source locations without executing the file.
    """

    def location(match: re.Match[str]) -> dict[str, Any]:
        return {"file": _relative(path, root), "line": _line_for_offset(text, match.start())}

    admin_guarded_handlers = _static_admin_guarded_handlers(text)
    for match in COMMAND_HANDLER_RE.finditer(text):
        handler = match.group("handler")
        record = {
            "command": _redact_text(match.group("command")).lstrip("/"),
            "handler": handler,
            "admin_guarded": handler.rsplit(".", 1)[-1] in admin_guarded_handlers,
            **location(match),
        }
        _append_unique(commands, seen["command"], record, ("command", "handler", "file", "line"))
    patterned_handler_locations: set[tuple[str, int]] = set()
    for match in CALLBACK_PATTERN_RE.finditer(text):
        record = {"pattern": _redact_text(match.group("pattern")), "handler": match.group("handler"), **location(match)}
        _append_unique(callback_handlers, seen["callback_handler"], record, ("pattern", "handler", "file", "line"))
        patterned_handler_locations.add((match.group("handler"), record["line"]))
    for match in CALLBACK_HANDLER_RE.finditer(text):
        record = {"pattern": "<catch-all>", "handler": match.group("handler"), **location(match)}
        if (record["handler"], record["line"]) not in patterned_handler_locations:
            _append_unique(callback_handlers, seen["callback_handler"], record, ("pattern", "handler", "file", "line"))
    for match in CALLBACK_DATA_RE.finditer(text):
        record = {"token": _redact_text(match.group("token")), **location(match)}
        _append_unique(callback_data, seen["callback_data"], record, ("token", "file", "line"))
    for match in CALLBACK_TUPLE_TOKEN_RE.finditer(text):
        token = _redact_text(match.group("token"))
        if _is_bare_numeric_aspect_ratio(token):
            # A tuple such as ("9:16", "16:9") is configuration data, not
            # a callback. Keep direct callback_data literals untouched; this
            # narrow rule only protects the broad keyboard-row heuristic.
            continue
        record = {"token": token, **location(match)}
        _append_unique(callback_data, seen["callback_data"], record, ("token", "file", "line"))
    for expression in (CALLBACK_DYNAMIC_DATA_RE, CALLBACK_DYNAMIC_TUPLE_RE):
        for match in expression.finditer(text):
            template = _callback_template_from_text(match.group("body"))
            if not template:
                continue
            record = {
                "template": template,
                "resolution": "unresolved_dynamic_template",
                **location(match),
            }
            _append_unique(callback_templates, seen["callback_template"], record, ("template", "file", "line"))
    for match in CONVERSATION_RE.finditer(text):
        record = {"handler": "ConversationHandler", **location(match)}
        _append_unique(conversations, seen["conversation"], record, ("file", "line"))
    for match in DECORATOR_ROUTE_RE.finditer(text):
        record = {
            "path": _redact_text(match.group("path")),
            "methods": [match.group("verb").upper()],
            "endpoint": "<static-decorator>",
            **location(match),
        }
        _append_unique(routes, seen["route"], record, ("path", "methods", "file", "line"))
    for match in ADD_ROUTE_RE.finditer(text):
        record = {
            "path": _redact_text(match.group("path")),
            "methods": ["<unspecified>"],
            "endpoint": match.group("endpoint"),
            **location(match),
        }
        _append_unique(routes, seen["route"], record, ("path", "methods", "file", "line"))
    for expression in (ENV_CALL_RE, ENV_SUBSCRIPT_RE):
        for match in expression.finditer(text):
            record = {"name": match.group("name"), **location(match)}
            _append_unique(env_references, seen["env"], record, ("name", "file", "line"))
    for match in TASK_CALL_RE.finditer(text):
        record = {"kind": match.group("kind"), "target": match.group("target"), **location(match)}
        _append_unique(background_jobs, seen["job"], record, ("kind", "target", "file", "line"))
    for match in JOB_FUNCTION_RE.finditer(text):
        record = {"kind": "function", "target": match.group("target"), **location(match)}
        _append_unique(background_jobs, seen["job"], record, ("kind", "target", "file", "line"))


def _guided_video_helper_tokens(helper: str, template: str, prefixes: set[str]) -> list[tuple[str, str]]:
    """Expand one reviewed helper template from direct literal callers only.

    The caller set is deliberately supplied by the source scanner and contains
    only ``promptvideo`` and ``imagevideo``.  A variable prefix, a future
    namespace, or a second formatted segment therefore cannot enter this
    function as a browser callback.
    """

    special = GUIDED_VIDEO_BACK_TEMPLATE_EXPANSIONS.get((helper, template))
    if special is not None:
        return [(prefix, special[prefix]) for prefix in sorted(prefixes) if prefix in special]
    if not template.startswith("{*}|") or template.count("{*}") != 1:
        return []
    return [(prefix, template.replace("{*}", prefix, 1)) for prefix in sorted(prefixes)]


def _resolve_reviewed_guided_video_helper_callbacks(
    *,
    text: str,
    root: Path,
    path: Path,
    callback_templates: list[dict[str, Any]],
    callback_data: list[dict[str, Any]],
    seen: dict[str, set[tuple[Any, ...]]],
) -> None:
    """Annotate reviewed helper templates and derive direct literal callbacks.

    This is a deliberately bounded static transformation, not symbolic
    execution.  It only considers f-string templates physically inside the
    three inspected helpers and the literal ``promptvideo``/``imagevideo``
    call sites.  The raw template record, its source line and its unresolved
    source marker are retained in inventory with the derivation evidence.
    """

    relative_path = _relative(path, root)
    records = [record for record in callback_templates if record.get("file") == relative_path]
    if not records:
        return

    for helper_match in GUIDED_VIDEO_KEYBOARD_HELPER_RE.finditer(text):
        helper = str(helper_match.group("helper") or "")
        start_line = _line_for_offset(text, helper_match.start())
        end_line = _line_for_offset(text, helper_match.end())
        calls = [
            {
                "prefix": str(call.group("prefix")),
                "file": relative_path,
                "line": _line_for_offset(text, call.start()),
            }
            for call in GUIDED_VIDEO_LITERAL_PREFIX_CALL_RE.finditer(text)
            if call.group("helper") == helper
        ]
        prefixes = {str(call["prefix"]) for call in calls}
        if not prefixes:
            continue

        for template_record in records:
            template_line = int(template_record.get("line") or 0)
            if template_line < start_line or template_line > end_line:
                continue
            template = str(template_record.get("template") or "")
            derived = _guided_video_helper_tokens(helper, template, prefixes)
            if not derived:
                continue

            derived_tokens = [token for _, token in derived]
            literal_calls = [call for call in calls if call["prefix"] in {prefix for prefix, _ in derived}]
            template_record.update(
                {
                    "resolution": "reviewed_literal_prefix_helper_calls",
                    "helper": helper,
                    "derived_callback_tokens": sorted(set(derived_tokens)),
                    "literal_prefix_call_evidence": literal_calls,
                }
            )
            for prefix, token in derived:
                for call in literal_calls:
                    if call["prefix"] != prefix:
                        continue
                    record = {
                        "token": token,
                        "resolution": "reviewed_literal_prefix_helper_call",
                        "template": template,
                        "template_file": relative_path,
                        "template_line": template_line,
                        "helper": helper,
                        "file": relative_path,
                        "line": int(call["line"]),
                    }
                    _append_unique(callback_data, seen["callback_data"], record, ("token", "file", "line"))


def _extract_python_inventory(root: Path, files: list[Path]) -> dict[str, Any]:
    commands: list[dict[str, Any]] = []
    callback_handlers: list[dict[str, Any]] = []
    callback_data: list[dict[str, Any]] = []
    callback_templates: list[dict[str, Any]] = []
    conversations: list[dict[str, Any]] = []
    routes: list[dict[str, Any]] = []
    background_jobs: list[dict[str, Any]] = []
    env_references: list[dict[str, Any]] = []
    parse_errors: list[dict[str, str]] = []
    seen: dict[str, set[tuple[Any, ...]]] = defaultdict(set)

    for path in files:
        if path.suffix.lower() != ".py":
            continue
        text = _read_source(path)
        if len(text.encode("utf-8", errors="replace")) > MAX_AST_PARSE_BYTES:
            _extract_large_python_file(
                text,
                root,
                path,
                commands,
                callback_handlers,
                callback_data,
                callback_templates,
                conversations,
                routes,
                background_jobs,
                env_references,
                seen,
            )
            continue
        try:
            tree = ast.parse(text, filename=str(path))
        except (SyntaxError, ValueError) as exc:
            parse_errors.append({"file": _relative(path, root), "error": _redact_text(str(exc))})
            continue

        admin_guarded_handlers = _static_admin_guarded_handlers(text)
        for record in _extract_env_from_ast(tree, root, path):
            _append_unique(env_references, seen["env"], record, ("name", "file", "line"))

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_name = _call_name(node.func)
                simple_name = call_name.rsplit(".", 1)[-1]
                location = _record_location(root, path, node)

                if simple_name == "CommandHandler":
                    command = _literal_string(node.args[0] if node.args else None) or "<dynamic-command>"
                    handler = _handler_name(node.args[1] if len(node.args) > 1 else _kwarg(node, "callback"))
                    record = {
                        "command": command.lstrip("/"),
                        "handler": handler,
                        "admin_guarded": handler.rsplit(".", 1)[-1] in admin_guarded_handlers,
                        **location,
                    }
                    _append_unique(commands, seen["command"], record, ("command", "handler", "file", "line"))

                if simple_name == "CallbackQueryHandler":
                    pattern = _literal_string(_kwarg(node, "pattern")) or "<catch-all>"
                    handler = _handler_name(node.args[0] if node.args else _kwarg(node, "callback"))
                    record = {"pattern": pattern, "handler": handler, **location}
                    _append_unique(callback_handlers, seen["callback_handler"], record, ("pattern", "handler", "file", "line"))

                if simple_name == "ConversationHandler":
                    record = {"handler": _handler_name(node), **location}
                    _append_unique(conversations, seen["conversation"], record, ("file", "line"))

                if simple_name == "add_api_route":
                    route = _literal_string(node.args[0] if node.args else None)
                    methods_node = _kwarg(node, "methods")
                    methods: list[str] = []
                    if isinstance(methods_node, (ast.List, ast.Tuple, ast.Set)):
                        methods = [item for item in (_literal_string(element) for element in methods_node.elts) if item]
                    record = {
                        "path": route or "<dynamic-route>",
                        "methods": methods or ["<unspecified>"],
                        "endpoint": _handler_name(node.args[1] if len(node.args) > 1 else None),
                        **location,
                    }
                    _append_unique(routes, seen["route"], record, ("path", "methods", "file", "line"))

                if simple_name in {"create_task", "add_task", "submit", "delay", "enqueue"}:
                    target = _handler_name(node.args[0] if node.args else None)
                    record = {"kind": simple_name, "target": target, **location}
                    _append_unique(background_jobs, seen["job"], record, ("kind", "target", "file", "line"))

                for keyword in node.keywords:
                    if keyword.arg == "callback_data":
                        template = _callback_template_from_ast(keyword.value)
                        if template:
                            record = {
                                "template": template,
                                "resolution": "unresolved_dynamic_template",
                                **location,
                            }
                            _append_unique(callback_templates, seen["callback_template"], record, ("template", "file", "line"))
                        else:
                            token = _literal_string(keyword.value) or "<dynamic-callback-data>"
                            record = {"token": token, **location}
                            _append_unique(callback_data, seen["callback_data"], record, ("token", "file", "line"))

            if isinstance(node, ast.Tuple):
                token = _tuple_callback_token(node)
                if token:
                    record = {"token": token, **_record_location(root, path, node)}
                    _append_unique(callback_data, seen["callback_data"], record, ("token", "file", "line"))
                else:
                    template = _tuple_callback_template(node)
                    if template:
                        record = {
                            "template": template,
                            "resolution": "unresolved_dynamic_template",
                            **_record_location(root, path, node),
                        }
                        _append_unique(callback_templates, seen["callback_template"], record, ("template", "file", "line"))

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                lowered = node.name.lower()
                if any(term in lowered for term in ("worker", "job", "queue", "background", "scheduler")):
                    record = {"kind": "function", "target": node.name, **_record_location(root, path, node)}
                    _append_unique(background_jobs, seen["job"], record, ("kind", "target", "file", "line"))

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    if not isinstance(decorator, ast.Call):
                        continue
                    decorator_name = _call_name(decorator.func)
                    verb = decorator_name.rsplit(".", 1)[-1].lower()
                    if verb in HTTP_VERBS:
                        route = _literal_string(decorator.args[0] if decorator.args else None) or "<dynamic-route>"
                        record = {"path": route, "methods": [verb.upper()], "endpoint": node.name, **_record_location(root, path, node)}
                        _append_unique(routes, seen["route"], record, ("path", "methods", "file", "line"))

    # This pass stays source-only and is deliberately scoped to the reviewed
    # helpers plus their literal callers.  It runs for both AST and large-file
    # paths, never follows a variable flow/prefix and keeps raw templates in
    # the inventory as source evidence.
    for path in files:
        if path.suffix.lower() != ".py":
            continue
        _resolve_reviewed_guided_video_helper_callbacks(
            text=_read_source(path),
            root=root,
            path=path,
            callback_templates=callback_templates,
            callback_data=callback_data,
            seen=seen,
        )

    return {
        "commands": sorted(commands, key=lambda item: (item["command"], item["file"], item["line"])),
        "callback_handlers": sorted(callback_handlers, key=lambda item: (item["pattern"], item["file"], item["line"])),
        "callback_data": sorted(callback_data, key=lambda item: (item["token"], item["file"], item["line"])),
        "callback_templates": sorted(callback_templates, key=lambda item: (item["template"], item["file"], item["line"])),
        "conversations": sorted(conversations, key=lambda item: (item["file"], item["line"])),
        "routes": sorted(routes, key=lambda item: (item["path"], item["file"], item["line"])),
        "background_jobs": sorted(background_jobs, key=lambda item: (item["target"], item["file"], item["line"])),
        "env_references": sorted(env_references, key=lambda item: (item["name"], item["file"], item["line"])),
        "parse_errors": parse_errors,
    }


def _extract_database_references(root: Path, files: list[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int]] = set()
    for path in files:
        if path.suffix.lower() not in {".py", ".sql"}:
            continue
        text = _read_source(path)
        for match in SQL_TABLE_RE.finditer(text):
            table = match.group("table").lower()
            if table in {"if", "select", "where", "set", "on", "table", "into"} | SQL_NOISE_WORDS:
                continue
            record = {
                "table": table,
                "operation": re.sub(r"\s+", " ", match.group("operation").upper()),
                "file": _relative(path, root),
                "line": _line_for_offset(text, match.start()),
            }
            signature = (record["table"], record["file"], record["line"])
            if signature not in seen:
                seen.add(signature)
                records.append(record)
    return sorted(records, key=lambda item: (item["table"], item["file"], item["line"]))


def _extract_provider_references(root: Path, files: list[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for provider, pattern in PROVIDER_MARKERS.items():
        files_with_marker: list[str] = []
        occurrences = 0
        matcher = re.compile(pattern, re.IGNORECASE)
        for path in files:
            text = _read_source(path)
            count = len(matcher.findall(text))
            if count:
                files_with_marker.append(_relative(path, root))
                occurrences += count
        if occurrences:
            records.append({"provider": provider, "occurrences": occurrences, "files": files_with_marker[:40]})
    return records


def _extract_web_ui_paths(root: Path, files: list[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int]] = set()
    pattern = re.compile(r"(?:fetch|axios\.(?:get|post|put|delete)|href)\s*\(?\s*[\"'](/[^\"'?#\s<]+)", re.IGNORECASE)
    for path in files:
        if path.suffix.lower() not in {".js", ".html", ".htm"}:
            continue
        text = _read_source(path)
        for match in pattern.finditer(text):
            route = _redact_text(match.group(1))
            record = {"path": route, "file": _relative(path, root), "line": _line_for_offset(text, match.start())}
            signature = (route, record["file"], record["line"])
            if signature not in seen:
                seen.add(signature)
                records.append(record)
    return sorted(records, key=lambda item: (item["path"], item["file"], item["line"]))


def _feature_presence(files: list[Path]) -> dict[str, list[str]]:
    lower_text = "\n".join(_read_source(path).casefold() for path in files)
    return {
        feature: [term for term in terms if term.casefold() in lower_text]
        for feature, terms in FEATURE_TARGETS.items()
    }


def _fingerprint(files: list[Path], root: Path) -> str:
    digest = hashlib.sha256()
    for path in files:
        relative = _relative(path, root).encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _summarize_inventory(project_kind: str, root: Path) -> dict[str, Any]:
    discovered_files = _source_files(root)
    files, excluded_noncanonical_source_files = _active_inventory_files(project_kind, root, discovered_files)
    python_inventory = _extract_python_inventory(root, files)
    tables = _extract_database_references(root, files)
    providers = _extract_provider_references(root, files)
    inventory: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "project_kind": project_kind,
        "audit_mode": "static-only",
        "source_root": str(root),
        "source_files_discovered": len(discovered_files),
        "source_files_scanned": len(files),
        "excluded_noncanonical_source_files": excluded_noncanonical_source_files,
        "source_fingerprint_sha256": _fingerprint(files, root),
        **python_inventory,
        "database_references": tables,
        "database_tables": sorted({record["table"] for record in tables}),
        "providers": providers,
        "provider_names": [record["provider"] for record in providers],
        "feature_presence": _feature_presence(files),
        "private_core_bridge_present": (root / "webapp_core_bridge.py").is_file(),
        "counts": {
            "commands": len(python_inventory["commands"]),
            "callback_handlers": len(python_inventory["callback_handlers"]),
            "callback_data": len(python_inventory["callback_data"]),
            "callback_templates": len(python_inventory["callback_templates"]),
            "conversations": len(python_inventory["conversations"]),
            "routes": len(python_inventory["routes"]),
            "background_jobs": len(python_inventory["background_jobs"]),
            "env_references": len(python_inventory["env_references"]),
            "database_tables": len({record["table"] for record in tables}),
            "providers": len(providers),
        },
    }
    if project_kind == "telegram_bot":
        inventory["handler_module_observation"] = _unreferenced_handler_module_observation(root)
    if project_kind == "webapp":
        inventory["ui_path_references"] = _extract_web_ui_paths(root, files)
        inventory["counts"]["ui_path_references"] = len(inventory["ui_path_references"])
    return _sanitize(inventory)


def _core_bridge_prefix(tree: ast.AST) -> str:
    """Read the private router prefix from AST, never by importing the Bot."""

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)) or not isinstance(node.value, ast.Call):
            continue
        if _call_name(node.value.func).rsplit(".", 1)[-1] != "APIRouter":
            continue
        candidate = _literal_string(_kwarg(node.value, "prefix"))
        if candidate and candidate.startswith("/"):
            return _normalise_route_template(candidate)
    return CORE_BRIDGE_DEFAULT_PREFIX


def _extract_bot_core_bridge_routes(bot_root: Path) -> tuple[list[dict[str, Any]], bool]:
    """Statically collect mounted-contract candidates from the Bot bridge file."""

    bridge_file = bot_root / CORE_BRIDGE_FILE
    if not bridge_file.is_file():
        return [], False
    try:
        source = _read_source(bridge_file)
        tree = ast.parse(source, filename=str(bridge_file))
    except (OSError, SyntaxError, ValueError):
        return [], False
    prefix = _core_bridge_prefix(tree)
    routes: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            if not isinstance(decorator.func.value, ast.Name) or decorator.func.value.id != "router":
                continue
            method = decorator.func.attr.lower()
            if method not in HTTP_VERBS:
                continue
            suffix = _literal_template(decorator.args[0] if decorator.args else None)
            if not suffix or not suffix.startswith("/"):
                continue
            route = _normalise_route_template(f"{prefix}/{suffix.lstrip('/')}")
            signature = (method.upper(), route, int(getattr(node, "lineno", 0) or 0))
            if signature in seen:
                continue
            seen.add(signature)
            routes.append(
                {
                    "method": method.upper(),
                    "path": route,
                    "endpoint": node.name,
                    "file": CORE_BRIDGE_FILE,
                    "line": int(getattr(node, "lineno", 0) or 0),
                }
            )
    entrypoint = bot_root / "bot.py"
    mounted = False
    if entrypoint.is_file():
        try:
            entrypoint_source = _read_source(entrypoint)
            mounted = bool(
                re.search(r"\binclude_router\s*\(\s*build_core_bridge_router\s*\(", entrypoint_source)
            )
        except OSError:
            mounted = False
    return sorted(routes, key=lambda item: (item["path"], item["method"], item["line"])), mounted


def _call_argument(call: ast.Call, index: int, keyword: str) -> ast.AST | None:
    if len(call.args) > index:
        return call.args[index]
    return _kwarg(call, keyword)


def _extract_web_bridge_requests(web_root: Path) -> list[dict[str, Any]]:
    """Collect only static Web-to-Bot bridge calls, preserving f-string shape."""

    requests: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, int]] = set()
    for path in _source_files(web_root):
        if path.suffix.lower() != ".py":
            continue
        try:
            source = _read_source(path)
            if len(source.encode("utf-8", errors="replace")) > MAX_AST_PARSE_BYTES:
                continue
            tree = ast.parse(source, filename=str(path))
        except (OSError, SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _call_name(node.func).rsplit(".", 1)[-1]
            if name not in CORE_BRIDGE_CALL_NAMES:
                continue
            raw_method = _literal_string(_call_argument(node, 0, "method"))
            raw_path = _literal_template(_call_argument(node, 1, "path"))
            # The public application can have other helper functions with a
            # similar name. Only private-core paths belong in this contract.
            if not raw_path or not raw_path.startswith(CORE_BRIDGE_DEFAULT_PREFIX):
                continue
            method = (
                raw_method.upper()
                if raw_method and not raw_method.startswith("<dynamic")
                else "<dynamic-method>"
            )
            route = _normalise_route_template(raw_path)
            line = int(getattr(node, "lineno", 0) or 0)
            signature = (method, route, _relative(path, web_root), line)
            if signature in seen:
                continue
            seen.add(signature)
            requests.append(
                {
                    "method": method,
                    "path": route,
                    "file": _relative(path, web_root),
                    "line": line,
                    "call": name,
                    "static": raw_method is not None,
                }
            )
    return sorted(requests, key=lambda item: (item["path"], item["method"], item["file"], item["line"]))


def _bridge_contract_inventory(bot_root: Path, web_root: Path) -> dict[str, Any]:
    """Compare Web outbound private-core calls against Bot bridge routes.

    This is a source-level compatibility check, not a network health check.
    It intentionally cannot claim that a separate Bot deployment is running,
    configured, or reachable from Railway.
    """

    bot_routes, router_mount_observed = _extract_bot_core_bridge_routes(bot_root)
    web_requests = _extract_web_bridge_requests(web_root)
    matches: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for request in web_requests:
        if request["method"] == "<DYNAMIC-METHOD>":
            unresolved.append(request)
            continue
        candidates = [
            route
            for route in bot_routes
            if route["method"] == request["method"] and _route_template_matches(request["path"], route["path"])
        ]
        if not candidates:
            unmatched.append(request)
            continue
        matches.append(
            {
                "request": request,
                "bot_routes": [
                    {"method": route["method"], "path": route["path"], "endpoint": route["endpoint"], "file": route["file"], "line": route["line"]}
                    for route in candidates
                ],
            }
        )
    if not bot_routes:
        status_name = "BOT_BRIDGE_SOURCE_MISSING"
    elif not router_mount_observed:
        status_name = "BOT_BRIDGE_ROUTER_NOT_MOUNTED"
    elif unmatched or unresolved:
        status_name = "CONTRACT_GAPS_FOUND"
    else:
        status_name = "STATIC_CONTRACT_MATCHED"
    return _sanitize(
        {
            "audit_mode": "static-only",
            "status": status_name,
            "bot_bridge_source_present": bool(bot_routes),
            "bot_router_mount_observed": router_mount_observed,
            "bot_route_count": len(bot_routes),
            "web_request_count": len(web_requests),
            "matched_request_count": len(matches),
            "unmatched_request_count": len(unmatched),
            "unresolved_request_count": len(unresolved),
            "bot_routes": bot_routes,
            "matched_requests": matches,
            "unmatched_requests": unmatched,
            "unresolved_requests": unresolved,
            "note": "Method/path shapes only. This does not prove Bot deployment, ENV, bearer/HMAC credentials, runtime authorization, schema, payment, provider, job, or delivery readiness.",
        }
    )


def _telegram_link_callback_contract(bot_root: Path, web_root: Path) -> dict[str, Any]:
    """Inspect the direction-specific Bot→Web identity callback statically.

    The private-core route comparison deliberately excludes this callback: it
    travels in the opposite direction and uses its own bearer/HMAC pair. Keep
    a separate inventory so raw Telegram-ID UI can never be mistaken for a
    real Bot identity proof.
    """

    def read(path: Path) -> str:
        try:
            return _read_source(path)
        except OSError:
            return ""

    bot_bridge = read(bot_root / CORE_BRIDGE_FILE)
    bot_entrypoint = read(bot_root / "bot.py")
    web_auth = read(web_root / "copyfast_auth.py")
    web_entrypoint = read(web_root / "app.py")
    bot_headers = {header: header in bot_bridge for header in TELEGRAM_LINK_CALLBACK_HEADERS}
    web_headers = {header: header in web_auth for header in TELEGRAM_LINK_CALLBACK_HEADERS}
    bot_env = {name: name in bot_bridge for name in TELEGRAM_LINK_CALLBACK_ENV}
    bot = {
        "bridge_source_present": bool(bot_bridge),
        "callback_sender_observed": "confirm_web_link_from_telegram" in bot_bridge,
        "deep_link_handler_observed": bool(re.search(r"startswith\(\s*['\"]web_['\"]\s*\)", bot_entrypoint)),
        "fallback_link_command_observed": bool(re.search(r"CommandHandler\s*\(\s*['\"]linkweb['\"]", bot_entrypoint)),
        "callback_environment_names_observed": bot_env,
        "callback_headers_observed": bot_headers,
        "callback_signature_shape_observed": _callback_signature_shape_observed(bot_bridge, side="bot"),
    }
    web = {
        "receiver_route_observed": "@router.post(\"/internal/telegram-link/confirm\")" in web_auth or "@router.post('/internal/telegram-link/confirm')" in web_auth,
        "receiver_hmac_authorizer_observed": "def _bridge_callback_authorized" in web_auth,
        "callback_headers_observed": web_headers,
        "mounted_under_auth_prefix_observed": bool(re.search(r"include_router\s*\(\s*copyfast_auth\.router\s*,\s*prefix\s*=\s*['\"]/api/v1/auth['\"]", web_entrypoint)),
        "raw_browser_id_rejection_observed": "TELEGRAM_BROWSER_INPUT_NOT_ACCEPTED" in web_auth,
        "callback_signature_shape_observed": _callback_signature_shape_observed(web_auth, side="web"),
    }
    bot_complete = (
        bot["bridge_source_present"]
        and bot["callback_sender_observed"]
        and bot["deep_link_handler_observed"]
        and bot["fallback_link_command_observed"]
        and all(bot_env.values())
        and all(bot_headers.values())
        and bot["callback_signature_shape_observed"]
    )
    web_complete = (
        web["receiver_route_observed"]
        and web["receiver_hmac_authorizer_observed"]
        and web["mounted_under_auth_prefix_observed"]
        and web["raw_browser_id_rejection_observed"]
        and all(web_headers.values())
        and web["callback_signature_shape_observed"]
    )
    status_name = "STATIC_CALLBACK_CONTRACT_PRESENT" if bot_complete and web_complete else "CALLBACK_CONTRACT_GAPS_FOUND"
    return _sanitize(
        {
            "audit_mode": "static-only",
            "status": status_name,
            "bot": bot,
            "web": web,
            "expected_web_callback_path": "/api/v1/auth/internal/telegram-link/confirm",
            "operator_configuration_required": True,
            "note": "This verifies source markers and a static callback HMAC material shape only. It does not prove Bot deployment, Railway environment equality, actual secret equality, DNS/TLS reachability, Telegram delivery, or a successful customer callback.",
        }
    )


def _is_admin_command(command: str, handler: str, *, admin_guarded: bool = False) -> bool:
    if str(command or "").casefold() in PUBLIC_CUSTOMER_COMMAND_OVERRIDES:
        return False
    if admin_guarded:
        return True
    haystack = f"{command} {handler}".casefold()
    return any(term in haystack for term in ADMIN_TERMS)


def _is_telegram_only(identifier: str) -> bool:
    lowered = identifier.casefold()
    return any(term in lowered for term in TELEGRAM_ONLY_TERMS)


def _feature_route(identifier: str) -> str:
    lowered = identifier.casefold().replace("-", "_")
    if any(term in lowered for term in ("growth_ai", "growth_report", "campaign_report", "export_report")):
        return "/growth/ai" if "growth" in lowered else "/campaign/report"
    if any(term in lowered for term in ("member", "vip", "trial", "package", "tier", "rank")):
        return "/membership"
    if any(term in lowered for term in ("manual", "thucong", "topup", "naptien", "payment")):
        return "/wallet/topup"
    if any(term in lowered for term in ("policy", "terms", "legal", "phaply", "dieukhoan")):
        return "/legal"
    if any(term in lowered for term in ("support", "ticket", "feedback", "gopy")):
        return "/tickets"
    if any(term in lowered for term in ("community", "official_channel", "kenh_chinh_thuc", "toanaas_hub")):
        return "/community"
    if any(term in lowered for term in ("linkweb", "telegram_link")):
        return "/onboarding"
    if any(term in lowered for term in ("mode", "language", "locale")):
        return "/account"
    if any(term in lowered for term in ("tool_status", "system_public_status", "telegram_status", "ai_status", "feature_status", "queue_status", "runtime_status")):
        return "/status"
    if any(term in lowered for term in ("tool", "model", "api_recommend")):
        return "/tools"
    if any(term in lowered for term in ("media_factory", "creative_flow", "film", "pipeline", "produce", "render_center", "shot_variation")):
        return "/studio"
    if any(term in lowered for term in ("remind", "repeat_")):
        return "/reminders"
    if any(term in lowered for term in ("memory", "note")):
        return "/notes"
    if any(term in lowered for term in ("referral", "ref_link", "ref_stats", "invite")):
        return "/referrals"
    if any(term in lowered for term in ("birthday", "gift", "promo", "magiamgia", "khuyenmai")):
        return "/rewards"
    if any(term in lowered for term in ("guide", "huongdan", "hdsd", "commands")):
        return "/guides"
    if any(term in lowered for term in ("image", "upscale", "background")):
        return "/features/image"
    if any(term in lowered for term in ("video", "multiscene", "trend", "storyboard")):
        return "/features/video"
    if any(term in lowered for term in ("voice", "tts", "clone")):
        return "/features/voice"
    if any(term in lowered for term in ("music", "song", "sfx", "audio")):
        return "/features/music"
    if any(term in lowered for term in ("subtitle", "translate", "dub", "asr", "srt", "vtt")):
        return "/features/subtitle"
    if any(term in lowered for term in ("pdf", "ocr", "document", "merge", "compress")):
        return "/features/documents"
    if any(term in lowered for term in ("caption", "hashtag", "hook", "script", "prompt", "chat")):
        return "/features/content"
    return "/dashboard"


def _route_exists(candidate: str, routes: set[str]) -> bool:
    return candidate in routes or candidate.rstrip("/") in {route.rstrip("/") for route in routes}


def _compatibility_surface_exists(candidate: str, routes: set[str]) -> bool:
    """Recognise the signed, guarded portal catch-all route statically.

    The renderer keeps its path allow-list in Python rather than a huge set of
    generated FastAPI decorators.  This is a real safe UI surface, but it is
    deliberately *not* evidence that a provider, wallet action or job works.
    """
    if "/{page_path:path}" not in routes:
        return False
    normalized = candidate.rstrip("/") or "/"
    prefixes = (
        "/dashboard", "/account", "/onboarding", "/wallet", "/packages", "/jobs", "/assets", "/asset-vault", "/support", "/tickets", "/analytics",
        "/membership", "/status", "/studio", "/workboard", "/trend-research", "/media-factory", "/media-workspace", "/creative-flow", "/video-studio",
        "/notes", "/reminders", "/referrals", "/rewards", "/community", "/guides", "/growth", "/campaign", "/calendar", "/approvals",
        "/pricing", "/legal", "/privacy", "/prompt-library", "/free-prompt-gallery", "/content", "/image", "/video", "/voice", "/music", "/subtitle",
        "/translate", "/dubbing", "/asr", "/documents", "/features", "/admin", "/tools", "/prompts",
        "/caption", "/hashtag", "/hook", "/script", "/storyboard",
    )
    return normalized == "/" or normalized.startswith(prefixes)


def _mapping_status(
    target: str,
    existing_routes: set[str],
    telegram_only: bool,
    *,
    dashboard_fallback: bool = False,
    navigation_entrypoint: bool = False,
    navigation_only: bool = False,
) -> str:
    if telegram_only:
        return "TELEGRAM_ONLY"
    if dashboard_fallback:
        return "NEEDS_FEATURE_DISPOSITION"
    if navigation_entrypoint and (
        _route_exists(target, existing_routes) or _compatibility_surface_exists(target, existing_routes)
    ):
        return "NAVIGATION_ENTRYPOINT"
    if navigation_only and (
        _route_exists(target, existing_routes) or _compatibility_surface_exists(target, existing_routes)
    ):
        # An exact Bot menu item may open a fresh signed Web workspace, but
        # that is not evidence that the Bot callback's pending state, engine,
        # wallet, job, provider or delivery side effect was reproduced.
        return "NAVIGATION_ONLY"
    if _route_exists(target, existing_routes):
        return "MAPPED_TO_EXISTING_ROUTE"
    if _compatibility_surface_exists(target, existing_routes):
        return "COPIED_GUARDED"
    return "NEEDS_WEB_IMPLEMENTATION"


def _map_command(command: dict[str, Any], existing_routes: set[str]) -> dict[str, Any]:
    name = command["command"].casefold()
    admin = _is_admin_command(name, command["handler"], admin_guarded=bool(command.get("admin_guarded")))
    telegram_only = _is_telegram_only(name)
    route_override = COMMAND_ROUTE_OVERRIDES.get(name)
    if admin and not telegram_only:
        target = f"/admin/{name}"
    else:
        target = route_override or _feature_route(name)
    navigation_entrypoint = not telegram_only and not admin and name in DASHBOARD_ENTRYPOINT_COMMANDS and target == "/dashboard"
    dashboard_fallback = not telegram_only and not navigation_entrypoint and route_override is None and target == "/dashboard"
    status = _mapping_status(
        target,
        existing_routes,
        telegram_only,
        dashboard_fallback=dashboard_fallback,
        navigation_entrypoint=navigation_entrypoint,
    )
    if telegram_only:
        resolution = "telegram_only"
    elif navigation_entrypoint:
        resolution = "reviewed_dashboard_navigation_entrypoint"
    elif dashboard_fallback:
        resolution = "unreviewed_dashboard_fallback_requires_feature_disposition"
    else:
        resolution = "explicit_static_route_mapping"
    return {
        "source_kind": "command",
        "source": f"/{command['command']}",
        "handler": command["handler"],
        "target": target if not telegram_only else "TELEGRAM_ONLY",
        "classification": "admin" if admin else "customer",
        "status": status,
        "resolution": resolution,
        "evidence": {"file": command["file"], "line": command["line"]},
    }


def _map_callback_handler_registration(record: dict[str, Any]) -> dict[str, Any]:
    """Keep a Bot callback dispatcher visible without pretending it is an action.

    ``CallbackQueryHandler`` registrations are routing mechanics.  A broad
    handler can receive many unrelated Telegram buttons and can also contain
    state, wallet, provider, admin or delivery branches.  Treating its
    ``<catch-all>`` pattern as a customer callback used to collapse dozens of
    independent dispatchers into one fake dashboard fallback.  The audit now
    preserves the actual handler identity and line while deliberately making
    no Web route or runtime claim.  This is transport metadata, not a
    ``NEEDS_FEATURE_DISPOSITION`` product action.
    """

    handler = str(record.get("handler") or "<unknown-handler>")
    pattern = str(record.get("pattern") or "<catch-all>")
    return {
        "source_kind": "callback_handler_registration",
        "source": f"CallbackQueryHandler:{handler}",
        "handler": handler,
        "pattern": pattern,
        "target": "NOT_BROWSER_ACTION",
        "classification": "telegram_transport",
        "status": "TELEGRAM_TRANSPORT_HANDLER",
        "resolution": "registered_telegram_dispatch_not_browser_action",
        "source_dispositions": ["NOT_BROWSER_ACTION", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"],
        "source_evidence": "Registration metadata routes Telegram callback traffic to a Bot handler. It does not identify a finite browser action or prove a Web runtime contract.",
        "evidence": {"file": record["file"], "line": record["line"]},
    }


def _map_unreferenced_static_record(record: dict[str, Any], source_kind: str) -> dict[str, Any]:
    """Preserve a legacy static record without treating it as live Bot parity."""

    field_by_kind = {
        "command": "command",
        "callback_data": "token",
        "callback_template": "template",
        "conversation": "handler",
        "callback_handler_registration": "handler",
    }
    source = str(record.get(field_by_kind.get(source_kind, "token")) or "<unknown-source>")
    if source_kind == "command" and not source.startswith("/"):
        source = f"/{source}"
    return {
        "source_kind": source_kind,
        "source": source,
        "target": "UNREFERENCED_BY_OBSERVED_ENTRYPOINT",
        "classification": "static_module_evidence",
        "status": "UNREFERENCED_BY_OBSERVED_ENTRYPOINT",
        "resolution": "not_imported_by_observed_bot_entrypoint",
        "source_dispositions": ["UNREFERENCED_BY_OBSERVED_ENTRYPOINT", "NO_RUNTIME_CLAIM"],
        "source_evidence": "The source file is not statically reachable from the observed bot.py entrypoint. Retained for migration evidence, excluded from runtime parity metrics.",
        "evidence": {"file": str(record.get("file") or ""), "line": int(record.get("line") or 0)},
    }


def _partition_unreferenced_module_records(
    records: Iterable[dict[str, Any]],
    unreferenced_files: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Separate observed-runtime source from static legacy-module evidence."""

    active: list[dict[str, Any]] = []
    unreferenced: list[dict[str, Any]] = []
    for record in records:
        if str(record.get("file") or "") in unreferenced_files:
            unreferenced.append(record)
        else:
            active.append(record)
    return active, unreferenced


def _map_callback(identifier: str, source_kind: str, evidence: dict[str, Any], existing_routes: set[str]) -> dict[str, Any]:
    token = identifier.casefold()
    admin = _is_admin_command(token, "")
    telegram_only = _is_telegram_only(token)
    dashboard_fallback = False
    menu_entry = MENU_ACTION_REGISTRY.get(token)
    navigation_only = menu_entry is not None
    if token == "payosalert|remind_later":
        # This is not a customer reminder.  The Bot emits it only in its
        # owner/admin PayOS-expiry alert keyboard and
        # ``handle_payos_alert_callback`` first enforces ``is_admin_user``.
        # Its only effect is dismissing that Telegram message; there is no
        # account reminder or Web-owned payment state to recreate.
        admin = True
        telegram_only = True
        target = "TELEGRAM_ONLY"
    elif menu_entry is not None:
        # Only this finite catalog may become a fresh signed Web navigation.
        # It cannot carry hidden Bot state, a message id, a file id or a
        # canonical action into the browser.
        target = menu_entry["target"]
    elif admin and not telegram_only:
        target = "/admin/callbacks"
    elif token.startswith(DASHBOARD_NAVIGATION_TEMPLATE_PREFIXES):
        # A Bot menu namespace often embeds a label such as ``video`` or
        # ``assets``.  That label alone is not a reviewed Web workflow and
        # must not be promoted to feature parity by the generic keyword
        # router below. Keep the safe dashboard target visible but actionable.
        target = "/dashboard"
        dashboard_fallback = True
    elif token == "adconcept|message|memory":
        # ``memory`` is one selectable *creative message theme* in the Bot's
        # cinematic-ad wizard (alongside success, confidence and luxury), not
        # a request to create or open a Memory Center note.
        target = "/video-studio/cinematic-concept"
    elif token == "freehub|meta":
        # The main Free Hub Meta button starts the Bot's small, deterministic
        # three-prompt pack.  Keep it separate from the later wizard steps so
        # the audit does not incorrectly erase that useful route mapping.
        target = "/content/prompt-pack"
    elif token in {"freehub|caption", "freehub|ideas", "freehub|prompts", "freehub|hook"}:
        # These are pure Free Hub text recipes: caption/hashtag, ideas,
        # image/video prompt guidance and Hook & Script.  The signed Web
        # Content Prompt Pack now owns their Web-native equivalents.
        target = "/content/prompt-pack"
    elif token == "freehub|publish_package":
        # The frozen Bot formatted its most recent Telegram pending result as
        # a review package.  The Web never imports that hidden state: its
        # explicit, signed input form returns a bounded text-only review
        # receipt and cannot schedule or publish any social content.
        target = "/content/publish-review"
    elif token == "freehub|library" or token.startswith("freehub|lib_"):
        # The Free Hub global seed is intentionally not copied into the
        # account-owned Prompt Library.  The dedicated signed Gallery exposes
        # the reviewed static snapshot with filter/detail/copy only.
        target = "/free-prompt-gallery"
    elif token == "freehub|upload":
        # The Bot's temporary Telegram-media slot has no safe Web equivalent.
        # Route the customer to the independently owned, validated Asset Vault
        # instead; it does not recreate a hidden Bot pending chain.
        target = "/asset-vault"
    elif token in {"freehub|docs", "freehub|notes"}:
        # Bot opens its memory/doc menu.  Web Notes is the direct Web-owned
        # counterpart; document transforms retain separate private routes.
        target = "/notes"
    elif token in {"freehub|docs_split_merge", "freehub|docs_summary_guard"}:
        # Summary stays guarded and split/merge remains separately scoped;
        # this parent menu maps only to the Web document hub.
        target = "/documents"
    elif token in {
        "freehub|suggest_pick1", "freehub|suggest_pick2", "freehub|suggest_pick3",
        "freehub|suggest_more", "freehub|suggest_custom", "freehub|copy",
        "freehub|edit", "freehub|variant", "freehub|prompt_back", "freehub|use_prompt1",
        "freehub|use_prompt2", "freehub|use_prompt3", "freehub|to_caption", "freehub|to_ideas",
        "freehub|to_prompts",
    }:
        # These are local Free Hub text-selection transitions.  The Web
        # Prompt Pack provides explicit topic suggestions and an ephemeral
        # deterministic receipt, without importing Telegram pending state.
        target = "/content/prompt-pack"
    elif token == "freehub|to_cinematic":
        target = "/video-studio/cinematic-concept"
    elif token == "freehub|image_prompt":
        target = "/image/prompt-composer"
    elif token == "freehub|video_prompt":
        target = "/video-studio/prompt-planner"
    elif token == "freehub|use_video":
        # This route is a planner, not a claim that a video render is ready.
        target = "/video-studio/prompt-planner"
    elif token.startswith("promptvideo|"):
        # The Bot's prompt-to-video wizard is a finite deterministic planning
        # sequence (topic, prompt, motion, music, strength and optional save).
        # Web presents those selections together in the signed Video Prompt
        # Planner; saving there recomputes a private Video Plan rather than
        # accepting Telegram pending state or triggering a render/provider.
        target = "/video-studio/prompt-planner"
    elif token in {"imagevideo|await_image", "imagevideo|back_image", "imagevideo|back_style"}:
        # The Web cannot reuse the Bot's transient Telegram upload slot.
        # Image Studio owns the explicit art direction and Image Vault image
        # reference that must exist before motion planning can begin.
        target = "/image-studio"
    elif token == "imagevideo|start" or token == "imagevideo|back_motion" or token.startswith("imagevideo|style_"):
        # These Bot wizard steps are represented by the one explicit Web
        # Image Motion Planner form. It never imports the Bot pending image;
        # the customer selects an owner-scoped Image Studio direction instead.
        target = "/video-studio/image-motion-planner"
    elif token == "imagevideo|save":
        # The sibling Bot callback retained a plan after a Telegram image
        # choice.  The Web equivalent deliberately does not accept that Bot
        # file slot: Image Motion Planner rechecks an owner-scoped Image
        # Studio direction with an active Image Vault image and only creates
        # an explicit, server-recomputed Video Plan draft.
        target = "/video-studio/image-motion-planner"
    elif token.startswith("imagevideo|"):
        # Remaining Image → Video choices (motion/music/strength/edit and
        # finalization guards) belong to the same explicit Image Motion
        # Planner. It works from a signed, owner-scoped Web asset/direction
        # rather than a Telegram file slot and never implies media execution.
        target = "/video-studio/image-motion-planner"
    elif token in {
        "selfscene|await_video",
        "selfscene|use_recent_video",
        "selfscene|input|video",
        "selfscene|back_upload",
        "selfscene|video_guard",
        "selfscene|frame_hint",
        "selfscene|finalization",
    }:
        # The frozen Bot implementation uses a Telegram video/file id or
        # recent-media slot for these transitions. ``frame_hint`` can also
        # enter the Bot's image-slideshow route, while ``video_guard`` and
        # ``finalization`` leave planning for its package/invoice/runtime
        # flow. A browser route must not imply source ingestion, media
        # inspection, rendering, payment, preview, output or delivery.
        telegram_only = True
        target = "TELEGRAM_ONLY"
    elif token in {
        "selfscene|start",
        "selfscene|plan_without_video",
        "selfscene|direction|context",
        "selfscene|direction|cinematic",
        "selfscene|direction|ad",
        "selfscene|direction_choice|1",
        "selfscene|direction_choice|2",
        "selfscene|direction_choice|3",
        "selfscene|direction_refresh",
        "selfscene|direction_custom",
        "selfscene|object|person",
        "selfscene|object|product",
        "selfscene|object|pet",
        "selfscene|object|custom",
        "selfscene|input|person",
        "selfscene|input|product",
        "selfscene|input|pet",
        "selfscene|input|custom",
        "selfscene|back_direction",
        "selfscene|back_object",
        "selfscene|back_context",
        "selfscene|back_style",
        "selfscene|back_music",
        "selfscene|context|1",
        "selfscene|context|2",
        "selfscene|context|3",
        "selfscene|context_refresh",
        "selfscene|context_custom",
        "selfscene|style_choice|1",
        "selfscene|style_choice|2",
        "selfscene|style_choice|3",
        "selfscene|style_refresh",
        "selfscene|style_custom",
        "selfscene|music|none",
        "selfscene|music_refresh",
        "selfscene|music_custom",
        "selfscene|plan",
        "selfscene|image_guard",
        "selfscene|music_guard",
        "selfscene|save",
    }:
        # These are the reviewed, finite text-direction choices in Bot
        # ``selfscene``: a subject to preserve, new scene, camera motion and
        # prompt/music guidance. The designated Web planner deliberately
        # starts from fresh text plus an explicit consent/right-to-use
        # acknowledgement. It does not receive a Telegram file id, inspect
        # media, read Bot state, invoke a provider or persist a plan merely
        # because Bot's transient ``save`` label was pressed.
        #
        # Keep the list literal. Any new ``selfscene`` action needs source
        # evidence and an independently reviewed Web contract; it cannot
        # inherit this route through a namespace wildcard.
        target = "/video-studio/self-shot-planner"
    elif token in {"videoref|link", "videoref|catalog", "videoref|save_catalog"}:
        # The Bot's private reference catalog/link flow cannot be copied as a
        # Telegram file-id or an external fetch.  Web starts from a validated
        # account-owned Asset Vault upload instead.
        target = "/asset-vault"
    elif token == "videoref|manual":
        # The Bot allowed a manual written reference description.  The
        # Storyboard Composer is the explicit Web text-only counterpart; it
        # does not pretend that a video was uploaded or analyzed.
        target = "/video-studio/storyboard-composer"
    elif token == "videoref|image_prompts":
        target = "/image/prompt-composer"
    elif token == "videoref|video_prompts":
        target = "/video-studio/prompt-planner"
    elif token in {"videoref|finalization", "videoref|frame_plan", "videoref|generate"}:
        # No Web provider/render adapter is being claimed.  The durable Video
        # Studio plan editor is the appropriate guarded next surface.
        target = "/video-studio"
    elif token in {
        "videoref|hub", "videoref|start", "videoref|await_video", "videoref|back_upload",
        "videoref|back_direction", "videoref|direction_custom", "videoref|back_topics",
        "videoref|topic_custom", "videoref|topic_refresh", "videoref|topic_choice", "videoref|sample_segments",
        "videoref|plan", "videoref|save", "videoref|version_refresh", "videoref|format",
        "videoref|profile", "videoref|profile_create", "videoref|profile_platform",
        "videoref|profile_affiliate", "videoref|profile_goal",
    } or token.startswith("videoref|direction|") or token.startswith("videoref|topic_choice|") or token.startswith("videoref|profile_platform|") or token.startswith("videoref|profile_affiliate|") or token.startswith("videoref|profile_goal|"):
        # Bot ``videoref`` retained a Telegram upload/file id plus temporary
        # channel choices, then emitted a text plan.  Web replaces the core
        # planning grammar with one explicit signed form: an active
        # owner-scoped Asset Vault video selector, a newly supplied topic,
        # audience/platform/goal/tone and server-recomputed three-scene plan.
        # It does not import Bot pending state, fetch a link or analyze a
        # source video, so the route spells that boundary out in the UI.
        target = "/video-studio/reference-format-planner"
    elif token in {"videoref|publish_package", "videoref|auto_publish"}:
        # Bot's package is text formatting and its auto-publish button is
        # guarded.  Web's explicit review package remains manual-only and
        # does not connect social accounts or publish content.
        target = "/content/publish-review"
    elif token == "videoref|performance":
        # Performance data must be entered and owned in the Web analytics
        # workspace; Web never reads the Bot's pending/video state.
        target = "/analytics"
    elif token in {
        "longvideo|finalization",
        "longvideo|frame_video",
        "longvideo|render_segments",
    }:
        # These buttons leave the Bot's finite editorial planning flow.
        # ``finalization`` opens the Bot invoice/finalization path,
        # ``frame_video`` may use Bot-held image file ids, and
        # ``render_segments`` observes/starts the Bot provider job flow.
        # A standalone Web planner has no canonical bridge/runtime contract
        # for those effects, so navigation must not imply render, payment,
        # preview, output or delivery.
        telegram_only = True
        target = "TELEGRAM_ONLY"
    elif token in {
        "longvideo|start",
        "longvideo|topic|sales",
        "longvideo|topic|education",
        "longvideo|topic|story",
        "longvideo|topic_custom",
        "longvideo|topic_choice|1",
        "longvideo|topic_choice|2",
        "longvideo|topic_choice|3",
        "longvideo|topic_refresh",
        "longvideo|back_topic_suggestions",
        "longvideo|duration|3 phút",
        "longvideo|duration|5 phút",
        "longvideo|duration|10 phút",
        "longvideo|duration|30 phút",
        "longvideo|duration|60 phút",
        "longvideo|duration_custom",
        "longvideo|back_duration",
        "longvideo|style|professional",
        "longvideo|style|viral",
        "longvideo|style|cinematic",
        "longvideo|style_custom",
        "longvideo|back_style",
        "longvideo|structure|1",
        "longvideo|structure|2",
        "longvideo|structure|3",
        "longvideo|structure_custom",
        "longvideo|back_structure",
        "longvideo|storyboard",
        "longvideo|image_prompts",
        "longvideo|video_prompts",
        "longvideo|music",
        "longvideo|save",
    }:
        # These are the reviewed, literal editorial transitions in the Bot's
        # long-video roadmap: topic → duration → style → structure, followed
        # by deterministic storyboard/prompt/audio text and the plan-save
        # intent.  The proposed signed Web surface must use fresh Web form
        # fields and its own owner-scoped persistence; it must never import
        # Bot pending state, project rows or scene rows.
        #
        # Keep this finite list deliberately literal.  A new ``longvideo``
        # action needs source evidence and an explicit Web contract instead
        # of being swallowed by a namespace wildcard.
        target = "/video-studio/long-form-planner"
    elif token in {
        "videoidea|finalization",
        "videoidea|frame_video",
        "videoidea|render_ai",
        "videoidea|platform|tiktok",
        "videoidea|platform|youtube",
        "videoidea|platform|facebook",
        "videoidea|platform_custom",
        "videoidea|trend_type|before_after",
        "videoidea|trend_type|problem_solution",
        "videoidea|trend_type|pov",
    }:
        # ``finalization`` opens the Bot's paid/runtime path, ``frame_video``
        # can assemble Bot-held scene images, and ``render_ai`` queries the
        # Bot job/provider flow.  The standalone planner deliberately has no
        # such execution adapter.  The platform/trend callbacks are legacy
        # keyboard literals with no matching branch in
        # ``handle_video_idea_callback``; mapping them to a Web form would
        # incorrectly claim that their Bot state transition exists.
        telegram_only = True
        target = "TELEGRAM_ONLY"
    elif token in {
        "videoidea|start",
        "videoidea|kind|ad",
        "videoidea|kind|cinema",
        "videoidea|kind|custom",
        "videoidea|cinema_refresh",
        "videoidea|cinema_custom",
        "videoidea|cinema_choice|1",
        "videoidea|cinema_choice|2",
        "videoidea|cinema_choice|3",
        "videoidea|product_type|physical",
        "videoidea|product_type|service",
        "videoidea|product_type|affiliate",
        "videoidea|product_type|custom",
        "videoidea|product_refresh",
        "videoidea|product_custom",
        "videoidea|product_choice|1",
        "videoidea|product_choice|2",
        "videoidea|product_choice|3",
        "videoidea|back_product_type",
        "videoidea|back_description",
        "videoidea|back_goal",
        "videoidea|back_context",
        "videoidea|back_choices",
        "videoidea|idea_refresh",
        "videoidea|goal_custom",
        "videoidea|goal|sales",
        "videoidea|goal|brand",
        "videoidea|goal|viral",
        "videoidea|context_custom",
        "videoidea|context|1",
        "videoidea|context|2",
        "videoidea|context|3",
        "videoidea|genre|scifi",
        "videoidea|genre|fantasy",
        "videoidea|genre|drama",
        "videoidea|choose|1",
        "videoidea|choose|2",
        "videoidea|choose|3",
        "videoidea|choice_custom",
        "videoidea|storyboard",
        "videoidea|image_prompts",
        "videoidea|video_prompts",
        "videoidea|music",
        "videoidea|save",
    }:
        # These are the finite text-planning choices handled by the frozen
        # Bot ``videoidea`` conversation: idea kind, product/topic, goal,
        # context, concept choice and its text-only storyboard/prompt/audio
        # follow-ups.  The signed Web Idea Planner replaces their temporary
        # Telegram state with original bounded form values and can explicitly
        # save a server-recomputed private Video Plan draft.  No Bot state,
        # provider, media, job, wallet, payment, publish or delivery path is
        # implied by this navigation mapping.
        target = "/video-studio/idea-planner"
    elif token == "freehub|save":
        # ``freehub|save`` is the terminal action for the five deterministic
        # Free Hub text packs (Meta prompt, caption/hashtag, ideas, hook/script
        # and image/video direction).  The Web counterpart keeps that useful
        # intent without importing the Bot's transient pending state: Prompt
        # Pack submits only its bounded original selection, recomputes the
        # reviewed text inside the server transaction, then writes an
        # owner-scoped Memory note with CSRF and idempotency.  It never accepts
        # a browser-supplied rendered result or calls Bot/provider/payment code.
        target = "/content/prompt-pack"
    elif token.startswith("freehub|meta_"):
        # The frozen Bot's contextual Meta wizard is a callback-only pending
        # flow.  Web replaces those transient buttons with one signed form at
        # the explicit contextual prompt surface, never an admin/dashboard
        # fallback or a claim of a Meta provider call.
        target = "/content/contextual-prompt"
    else:
        target = _feature_route(token)
        dashboard_fallback = target == "/dashboard"
    status = _mapping_status(
        target,
        existing_routes,
        telegram_only,
        dashboard_fallback=dashboard_fallback,
        navigation_only=navigation_only,
    )
    if telegram_only:
        resolution = "telegram_only"
    elif navigation_only:
        resolution = "reviewed_exact_menu_navigation"
    elif dashboard_fallback:
        resolution = (
            "menu_callback_requires_explicit_feature_disposition"
            if token.startswith(DASHBOARD_NAVIGATION_TEMPLATE_PREFIXES)
            else "unreviewed_dashboard_fallback_requires_feature_disposition"
        )
    else:
        resolution = "explicit_static_route_mapping"
    result = {
        "source_kind": source_kind,
        "source": identifier,
        "target": target if not telegram_only else "TELEGRAM_ONLY",
        "classification": "admin" if admin else "customer",
        "status": status,
        "resolution": resolution,
        "evidence": evidence,
    }
    if menu_entry is not None:
        # These are audit-only descriptors.  The public API returns the
        # matching Web capability catalog without raw Bot action identifiers.
        result["menu_capability_key"] = menu_entry["capability_key"]
        result["menu_feature_key"] = menu_entry["feature_key"]
        result["menu_authority"] = menu_entry["authority"]
        result["menu_launch_mode"] = menu_entry["launch_mode"]
    return result


def _map_reviewed_guided_video_helper_template(
    record: dict[str, Any],
    existing_routes: set[str],
) -> dict[str, Any] | None:
    """Map a raw helper marker through its reviewed literal callback evidence.

    A raw marker can fan out to the Prompt and Image Motion planners, so it
    deliberately carries ``target_routes`` and per-token evidence instead of
    pretending that one broad ``{*}|`` namespace has a single Web endpoint.
    """

    if record.get("resolution") != "reviewed_literal_prefix_helper_calls":
        return None
    template = str(record.get("template") or "")
    tokens = [str(token) for token in record.get("derived_callback_tokens", []) if str(token)]
    if not template or not tokens:
        return None
    evidence = {"file": str(record.get("file") or ""), "line": int(record.get("line") or 0)}
    derived = [
        _map_callback(token, "callback_data", evidence, existing_routes)
        for token in tokens
    ]
    safe_statuses = {"MAPPED_TO_EXISTING_ROUTE", "COPIED_GUARDED"}
    if not derived or any(item["status"] not in safe_statuses for item in derived):
        return None
    target_routes = sorted({str(item["target"]) for item in derived})
    status = "MAPPED_TO_EXISTING_ROUTE" if all(item["status"] == "MAPPED_TO_EXISTING_ROUTE" for item in derived) else "COPIED_GUARDED"
    return {
        "source_kind": "callback_template",
        "source": template,
        "target": target_routes[0] if len(target_routes) == 1 else "DERIVED_LITERAL_PREFIX_CALLBACKS",
        "target_routes": target_routes,
        "derived_callbacks": [
            {
                "source": item["source"],
                "target": item["target"],
                "status": item["status"],
                "classification": item["classification"],
            }
            for item in derived
        ],
        "classification": "customer",
        "status": status,
        "resolution": "reviewed_literal_prefix_helper_calls",
        "helper": str(record.get("helper") or ""),
        "literal_prefix_call_evidence": list(record.get("literal_prefix_call_evidence") or []),
        "evidence": evidence,
    }


def _map_callback_template(template: str, evidence: dict[str, Any], existing_routes: set[str]) -> dict[str, Any] | None:
    """Map only reviewed *namespace* templates to a guarded Web workflow.

    ``{*}`` deliberately stays opaque.  This helper never derives a resource
    id, looks up a Bot state value or turns a template into a browser action.
    It merely records that a fixed callback family has a signed Web surface
    where the account can continue in a matching workflow.  Unlisted templates
    remain ``NEEDS_WEB_IMPLEMENTATION`` in the generated parity report.
    """

    token = str(template or "").casefold()
    if "{*}" not in token:
        return _map_callback(token, "callback_template", evidence, existing_routes)
    if token.startswith("menu|"):
        # Dynamic menu templates can encode a Bot-only back route, translation
        # session, locale/product context or other pending state.  A finite
        # exact action catalog is required before any one value can be treated
        # as navigation; never route this namespace through a dashboard
        # fallback or expose the formatted value to the browser.
        return {
            "source_kind": "callback_template",
            "source": template,
            "target": "UNRESOLVED_DYNAMIC_MENU_ACTION",
            "classification": "customer",
            "status": "NEEDS_FEATURE_DISPOSITION",
            "resolution": "dynamic_menu_action_requires_finite_catalog",
            "evidence": evidence,
        }
    if token == "longvideo|structure|{*}":
        # The only dynamic value is a bounded position (1–3) emitted by the
        # reviewed long-video structure keyboard.  Web's Long-form Roadmap
        # owns an equivalent bounded structure selection; this does not copy
        # Bot project rows, finalization, rendering or provider behavior.
        target = "/video-studio/long-form-planner"
        return {
            "source_kind": "callback_template",
            "source": template,
            "target": target,
            "classification": "customer",
            "status": _mapping_status(target, existing_routes, telegram_only=False),
            "resolution": "reviewed_bounded_longvideo_structure_template",
            "evidence": evidence,
        }
    if token.startswith("trend|video|"):
        # This dynamic button belongs to the Bot's admin-only live trend
        # search → calendar → production-job pipeline. A local Web research
        # checklist is not an equivalent executor, so do not claim a route
        # mapping until a role-checked read/write contract exists.
        return {
            "source_kind": "callback_template",
            "source": template,
            "target": "TELEGRAM_ONLY",
            "classification": "admin",
            "status": "TELEGRAM_ONLY",
            "resolution": "bot_admin_only_dynamic_flow",
            "evidence": evidence,
        }
    if token.startswith("adconcept|admin_") or token.startswith("manual|approve") or token.startswith("manual|reject"):
        # Provider smoke/video execution and manual-payment approval mutate
        # canonical Bot/provider/wallet state. They stay out of the browser
        # and cannot be represented by a navigation-only compatibility route.
        return {
            "source_kind": "callback_template",
            "source": template,
            "target": "TELEGRAM_ONLY",
            "classification": "admin",
            "status": "TELEGRAM_ONLY",
            "resolution": "bot_canonical_admin_dynamic_flow",
            "evidence": evidence,
        }
    for prefix, target, classification in DYNAMIC_CALLBACK_TEMPLATE_ROUTE_OVERRIDES:
        if not token.startswith(prefix):
            continue
        dashboard_fallback = target == "/dashboard" and prefix in DASHBOARD_NAVIGATION_TEMPLATE_PREFIXES
        return {
            "source_kind": "callback_template",
            "source": template,
            "target": target,
            "classification": classification,
            "status": _mapping_status(
                target,
                existing_routes,
                telegram_only=False,
                dashboard_fallback=dashboard_fallback,
            ),
            "resolution": (
                "menu_namespace_requires_explicit_feature_disposition"
                if dashboard_fallback
                else "reviewed_namespace_compatibility_route"
            ),
            "evidence": evidence,
        }
    return None


def _runtime_web_route_paths(web: dict[str, Any], web_root: Path) -> set[str]:
    """Return only routes reachable from the deployed Web entrypoint.

    The Web repository intentionally retains legacy prototype modules for
    reference.  Static inventory must still record them, but a decorator in an
    unmounted module is not proof that the signed ``app.py`` entrypoint exposes
    that endpoint.  Follow direct ``include_router(module.router)`` references
    from ``app.py`` without importing any code, then fall back to the full
    inventory only when there is no identifiable app entrypoint.
    """

    records = [route for route in web.get("routes", []) if not str(route.get("path") or "").startswith("<")]
    entrypoint = web_root / "app.py"
    if not entrypoint.is_file():
        return {str(route["path"]) for route in records}
    try:
        source = _read_source(entrypoint)
    except OSError:
        return {str(route["path"]) for route in records}
    route_files = {"app.py"}
    for module in re.findall(r"\binclude_router\s*\(\s*([A-Za-z_]\w*)\.router\b", source):
        candidate = f"{module}.py"
        if (web_root / candidate).is_file():
            route_files.add(candidate)

    router_prefixes: dict[str, str] = {}
    for route_file in route_files - {"app.py"}:
        try:
            module_source = _read_source(web_root / route_file)
        except OSError:
            continue
        router_declaration = re.search(
            r"\brouter\s*=\s*APIRouter\s*\((?P<arguments>.*?)\)",
            module_source,
            flags=re.DOTALL,
        )
        if router_declaration is None:
            continue
        prefix_match = re.search(
            r"\bprefix\s*=\s*(['\"])(?P<prefix>[^'\"]+)\1",
            router_declaration.group("arguments"),
        )
        if prefix_match is not None:
            router_prefixes[route_file] = "/" + prefix_match.group("prefix").strip("/")

    reachable: set[str] = set()
    for route in records:
        route_file = str(route.get("file") or "")
        if route_file not in route_files:
            continue
        path = str(route["path"])
        prefix = router_prefixes.get(route_file)
        if prefix and path.startswith("/") and not path.startswith(prefix + "/"):
            path = prefix.rstrip("/") + path
        reachable.add(path)
    return reachable


def _fallback_feature_family(item: dict[str, Any]) -> str:
    """Return a stable non-executing family key for a dashboard fallback."""

    source = str(item.get("source") or "").strip()
    if not source or source.startswith("<"):
        return "unstructured"
    lowered = source.casefold()
    if lowered == "menu_affiliate" or lowered.startswith("affiliate_"):
        return "affiliate"
    if lowered == "menu_freelance" or lowered.startswith("freelance_"):
        return "freelance"
    if lowered == "menu_mxh" or lowered.startswith("mxh_"):
        return "social_navigation"
    if lowered in {"back_lang", "lang_more"}:
        return "locale_navigation"
    if lowered == "back_main":
        return "root_navigation"
    if lowered == "tr_transcribe":
        return "tr_transcribe"
    if re.fullmatch(r"\d{1,3}:\d{1,3}", source):
        return "aspect_ratio_orphan"
    if source.startswith("/"):
        return f"command:{source[1:].casefold() or 'unknown'}"
    match = re.match(r"(?P<family>[A-Za-z0-9_.-]+)[|:]", source)
    if match is None:
        return "unstructured"
    return str(match.group("family") or "unstructured").casefold()


def _annotate_feature_disposition(item: dict[str, Any]) -> dict[str, Any]:
    """Attach source-state evidence without changing a route/parity result.

    The metadata makes unresolved records reviewable by product/security
    boundary while retaining their existing ``NEEDS_FEATURE_DISPOSITION``
    status.  In particular, it must never turn a dispatcher, Bot pending
    state, provider action or canonical payment action into a browser route.
    """

    if item.get("status") != "NEEDS_FEATURE_DISPOSITION":
        return item
    family = _fallback_feature_family(item)
    policy = FALLBACK_FEATURE_DISPOSITIONS.get(family, DEFAULT_FALLBACK_FEATURE_DISPOSITION)
    item["fallback_family"] = family
    source_dispositions = [str(value) for value in policy.get("source_dispositions", ())]
    source_evidence = str(policy.get("source_evidence") or "")
    if source_dispositions:
        item["source_dispositions"] = source_dispositions
    if source_evidence:
        item["source_evidence"] = source_evidence
    return item


def _feature_disposition_backlog(mappings: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group unresolved dashboard fallbacks into a reviewable contract backlog.

    This does not resolve or reroute a callback. It keeps the migration plan
    finite and auditable while preserving the source evidence that still needs
    a product/security decision.
    """

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in mappings:
        if item.get("status") != "NEEDS_FEATURE_DISPOSITION":
            continue
        family = str(item.get("fallback_family") or _fallback_feature_family(item))
        grouped[family].append(item)

    priority_rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    backlog: list[dict[str, Any]] = []
    for family, items in grouped.items():
        policy = FALLBACK_FEATURE_DISPOSITIONS.get(family, DEFAULT_FALLBACK_FEATURE_DISPOSITION)
        entry = {
            "family": family,
            "priority": str(policy["priority"]),
            "candidate_boundary": str(policy["candidate_boundary"]),
            "authority": str(policy["authority"]),
            "next_contract": str(policy["next_contract"]),
            "count": len(items),
            "source_kinds": sorted({str(item.get("source_kind") or "unknown") for item in items}),
            "sample_sources": sorted({str(item.get("source") or "") for item in items})[:12],
        }
        source_dispositions = [str(value) for value in policy.get("source_dispositions", ())]
        source_evidence = str(policy.get("source_evidence") or "")
        if source_dispositions:
            entry["source_dispositions"] = source_dispositions
        if source_evidence:
            entry["source_evidence"] = source_evidence
        backlog.append(entry)
    return sorted(
        backlog,
        key=lambda item: (
            priority_rank.get(str(item["priority"]), 99),
            -int(item["count"]),
            str(item["family"]),
        ),
    )


def _build_parity_gap(bot: dict[str, Any], web: dict[str, Any], bot_root: Path, web_root: Path) -> dict[str, Any]:
    existing_routes = _runtime_web_route_paths(web, web_root)
    bridge_contract = _bridge_contract_inventory(bot_root, web_root)
    telegram_link_contract = _telegram_link_callback_contract(bot_root, web_root)
    handler_module_observation = (
        bot.get("handler_module_observation")
        if isinstance(bot.get("handler_module_observation"), dict)
        else {}
    )
    unreferenced_module_files = {
        str(path)
        for path in handler_module_observation.get("unreferenced_module_files", [])
        if isinstance(path, str)
    }
    active_commands, unreferenced_commands = _partition_unreferenced_module_records(
        bot["commands"], unreferenced_module_files
    )
    active_callback_handlers, unreferenced_callback_handlers = _partition_unreferenced_module_records(
        bot["callback_handlers"], unreferenced_module_files
    )
    active_callback_data, unreferenced_callback_data = _partition_unreferenced_module_records(
        bot["callback_data"], unreferenced_module_files
    )
    active_callback_templates, unreferenced_callback_templates = _partition_unreferenced_module_records(
        bot.get("callback_templates", []), unreferenced_module_files
    )
    active_conversations, unreferenced_conversations = _partition_unreferenced_module_records(
        bot["conversations"], unreferenced_module_files
    )

    # The runtime-parity denominator contains only concrete source actions
    # statically reachable from the observed entrypoint. Dispatcher
    # registrations and unreferenced handler-package modules stay in separate
    # evidence collections. This corrects the audit scope, but changes the
    # denominator and must never be described as feature-progress coverage.
    command_mappings = [_map_command(command, existing_routes) for command in active_commands]
    callback_handler_mappings = [
        _map_callback_handler_registration(record)
        for record in active_callback_handlers
    ]
    callback_mappings = [
        _map_callback(record["token"], "callback_data", {"file": record["file"], "line": record["line"]}, existing_routes)
        for record in active_callback_data
    ]
    callback_template_mappings = []
    for record in active_callback_templates:
        evidence = {"file": record["file"], "line": record["line"]}
        mapped = _map_reviewed_guided_video_helper_template(record, existing_routes)
        if mapped is None:
            mapped = _map_callback_template(str(record["template"]), evidence, existing_routes)
        if mapped is None:
            mapped = {
                "source_kind": "callback_template",
                "source": str(record["template"]),
                "target": "UNRESOLVED_DYNAMIC_CALLBACK_TEMPLATE",
                "classification": "unknown",
                "status": "NEEDS_WEB_IMPLEMENTATION",
                "resolution": str(record.get("resolution") or "unresolved_dynamic_template"),
                "evidence": evidence,
            }
        elif "resolution" not in mapped:
            mapped["resolution"] = "reviewed_namespace_compatibility_route"
        callback_template_mappings.append(mapped)
    conversation_mappings = [
        {
            "source_kind": "conversation",
            "source": f"ConversationHandler at {record['file']}:{record['line']}",
            "target": "/workflow",
            "classification": "customer",
            "status": "NEEDS_WEB_IMPLEMENTATION",
            "evidence": {"file": record["file"], "line": record["line"]},
        }
        for record in active_conversations
    ]
    mappings = command_mappings + callback_mappings + callback_template_mappings + conversation_mappings
    for item in mappings:
        _annotate_feature_disposition(item)

    unreferenced_static_module_mappings = [
        _map_unreferenced_static_record(record, source_kind)
        for source_kind, records in (
            ("command", unreferenced_commands),
            ("callback_handler_registration", unreferenced_callback_handlers),
            ("callback_data", unreferenced_callback_data),
            ("callback_template", unreferenced_callback_templates),
            ("conversation", unreferenced_conversations),
        )
        for record in records
    ]
    status_counts = Counter(item["status"] for item in mappings)
    feature_disposition_backlog = _feature_disposition_backlog(mappings)
    callback_handler_summary = {
        "total": len(bot["callback_handlers"]),
        "observed_runtime_registrations": len(callback_handler_mappings),
        "unreferenced_static_module_registrations": len(unreferenced_callback_handlers),
        "catch_all": sum(1 for item in bot["callback_handlers"] if item.get("pattern") == "<catch-all>"),
        "patterned": sum(1 for item in bot["callback_handlers"] if item.get("pattern") != "<catch-all>"),
        "product_action_claims": 0,
        "note": "CallbackQueryHandler registrations are Telegram transport evidence only. They are excluded from product-action coverage and never prove a browser route or Web runtime parity.",
    }
    static_web_surfaces = status_counts["MAPPED_TO_EXISTING_ROUTE"] + status_counts["COPIED_GUARDED"]
    source_total = len(mappings)
    unresolved_callback_templates = sum(
        1
        for item in callback_template_mappings
        if item["status"] in {"NEEDS_WEB_IMPLEMENTATION", "NEEDS_FEATURE_DISPOSITION"}
    )
    unresolved_feature_dispositions = status_counts["NEEDS_FEATURE_DISPOSITION"]
    dashboard_fallback_count = sum(1 for item in mappings if item.get("status") == "NEEDS_FEATURE_DISPOSITION")
    unresolved_source_count = status_counts["NEEDS_WEB_IMPLEMENTATION"] + unresolved_feature_dispositions
    resolved_static_source_count = source_total - unresolved_source_count
    bot_tables = set(bot["database_tables"])
    web_tables = set(web["database_tables"])
    observed_private_route = bool(bot.get("private_core_bridge_present")) or any(
        str(route["path"]).startswith("/internal/v1/") for route in bot["routes"]
    )
    bridge_contract_count = (
        int(bridge_contract["unmatched_request_count"])
        + int(bridge_contract["unresolved_request_count"])
        if bridge_contract.get("bot_bridge_source_present")
        else (0 if observed_private_route else 1)
    )
    gaps = [
        {
            "area": "customer_and_admin_routes",
            "severity": "high",
            "detail": "Bot source mappings that do not have an observed Web App route or guarded compatibility surface.",
            "count": status_counts["NEEDS_WEB_IMPLEMENTATION"],
        },
        {
            "area": "dashboard_navigation_fallbacks",
            "severity": "high",
            "detail": "Concrete Bot actions with no reviewed feature-family disposition are deliberately excluded from static Web-surface coverage and must be mapped to a Web-native workflow, a guarded runtime boundary, an admin-only contract, or TELEGRAM_ONLY. Callback dispatcher registrations are counted separately as source evidence.",
            "count": dashboard_fallback_count,
            "families": [
                {"family": item["family"], "priority": item["priority"], "count": item["count"]}
                for item in feature_disposition_backlog
            ],
        },
        {
            "area": "callback_handler_dispatchers",
            "severity": "high",
            "detail": "CallbackQueryHandler registrations are recorded with their real handler identity and source line. They are Telegram transport evidence, not end-user browser actions, and are excluded from product-action coverage.",
            "count": callback_handler_summary["observed_runtime_registrations"],
            "static_inventory_count": callback_handler_summary["total"],
            "catch_all": callback_handler_summary["catch_all"],
            "patterned": callback_handler_summary["patterned"],
        },
        {
            "area": "unreferenced_static_modules",
            "severity": "high",
            "detail": "Legacy handler-module records are retained as source evidence but excluded from the observed bot.py runtime parity denominator when the static import closure does not reach their module files.",
            "count": len(unreferenced_static_module_mappings),
            "module_files": sorted(unreferenced_module_files),
            "observation_status": str(handler_module_observation.get("status") or "NOT_AUDITED"),
        },
        {
            "area": "dynamic_callback_templates",
            "severity": "high",
            "detail": "Only templates without a manually reviewed namespace-to-workflow route remain unresolved. A resolved template proves a guarded route family, never a dynamic value or runtime execution.",
            "count": unresolved_callback_templates,
        },
        {
            "area": "private_core_bridge",
            "severity": "high",
            "detail": "Private bridge routes are owned by the separate bot bridge branch, never the browser-facing Web App. Current checkout contract status: " + str(bridge_contract["status"]),
            "count": bridge_contract_count,
        },
        {
            "area": "telegram_bot_to_web_identity_callback",
            "severity": "high",
            "detail": "Direction-specific one-time Telegram callback contract. Current checkout status: " + str(telegram_link_contract["status"]),
            "count": 0 if telegram_link_contract.get("status") == "STATIC_CALLBACK_CONTRACT_PRESENT" else 1,
        },
        {
            "area": "database_authority",
            "severity": "high",
            "detail": "Bot-only tables need read/proxy contracts; the Web App must not duplicate wallet or PayOS writers.",
            "count": len(bot_tables - web_tables),
            "tables": sorted(bot_tables - web_tables),
        },
        {
            "area": "feature_surface",
            "severity": "medium",
            "detail": "Static feature-token presence differs between bot and Web App; inspect feature-specific routes before enabling a surface.",
            "count": sum(1 for key in FEATURE_TARGETS if bool(bot["feature_presence"].get(key)) != bool(web["feature_presence"].get(key))),
        },
    ]
    return _sanitize(
        {
            "schema_version": SCHEMA_VERSION,
            "audit_mode": "static-only",
            "source_counts": {
                "commands": len(bot["commands"]),
                "callback_handlers": len(bot["callback_handlers"]),
                "callback_handler_dispatchers": len(callback_handler_mappings),
                "callback_data": len(bot["callback_data"]),
                "callback_templates": len(bot.get("callback_templates", [])),
                "unresolved_callback_templates": unresolved_callback_templates,
                "conversations": len(bot["conversations"]),
                "observed_runtime_product_action_mappings": source_total,
                "unreferenced_static_module_records": len(unreferenced_static_module_mappings),
                "telegram_transport_handler_records": len(callback_handler_mappings),
                "total_audited_source_records": source_total + len(callback_handler_mappings) + len(unreferenced_static_module_mappings),
                "total_mappings": source_total,
                "resolved_static_source_count": resolved_static_source_count,
                "unresolved_source_count": unresolved_source_count,
            },
            "mapping_status_counts": dict(sorted(status_counts.items())),
            "static_web_surface_coverage_percent": round((static_web_surfaces / source_total * 100), 2) if source_total else 0.0,
            "safe_disposition_coverage_percent": round((resolved_static_source_count / source_total * 100), 2) if source_total else 100.0,
            "mapping_coverage_percent": round((resolved_static_source_count / source_total * 100), 2) if source_total else 100.0,
            "metric_scope": {
                "product_action_denominator": source_total,
                "excluded_telegram_transport_handlers": len(callback_handler_mappings),
                "excluded_unreferenced_handler_package_records": len(unreferenced_static_module_mappings),
                "numeric_tuple_non_action_rule": "Bare N:N aspect-ratio tuple values are configuration data, not callback actions; numeric-leading structured callbacks remain inventoried.",
                "note": "Coverage is calculated only from concrete source actions reachable from the observed bot.py entrypoint. CallbackQueryHandler registrations are transport metadata, and unreferenced handlers-package records remain evidence only. This changes the denominator; it does not add a Web feature or runtime-parity claim.",
            },
            "coverage_comparability": {
                "status": "NOT_COMPARABLE_TO_PREVIOUS_AUDIT_PERCENTAGES",
                "feature_progress_claim": False,
                "reason": "Schema 1.4 corrects raw-string callback-handler extraction, keeps the handlers/ package outside the observed bot.py runtime denominator when no static import path exists, and rejects only bare numeric aspect-ratio tuples from the keyboard callback heuristic.",
                "scope_changes": [
                    "CallbackQueryHandler registrations are Telegram transport evidence, not product actions.",
                    "Records from unreferenced handlers/ package files remain evidence-only instead of mapped/guarded runtime parity.",
                    "Bare N:N tuple values are treated as aspect-ratio configuration, while numeric-leading structured callbacks remain supported.",
                ],
                "note": "Any percentage delta caused by these inventory corrections is not feature progress. Compare absolute routes/contracts and separately verified runtime evidence instead.",
            },
            "workflow_equivalence": {
                "status": "NOT_STATICALLY_VERIFIABLE",
                "verified_mapping_count": 0,
                "coverage_percent": 0.0,
                "note": "This source-only audit can verify route and disposition evidence, not signed runtime behavior, provider execution, billing, job delivery, or owner-scoped output access.",
            },
            "feature_disposition_backlog": feature_disposition_backlog,
            "callback_handler_summary": callback_handler_summary,
            "bridge_contract": bridge_contract,
            "telegram_link_callback_contract": telegram_link_contract,
            "command_mappings": command_mappings,
            "callback_mappings": callback_mappings,
            "callback_handler_mappings": callback_handler_mappings,
            "callback_template_mappings": callback_template_mappings,
            "conversation_mappings": conversation_mappings,
            "handler_module_observation": handler_module_observation,
            "unreferenced_static_module_mappings": unreferenced_static_module_mappings,
            "gaps": gaps,
            "notes": [
                "Every statically discovered source record remains represented: reachable concrete product actions in the parity denominator, Telegram handler registrations in transport evidence, and unreferenced legacy-module records in a separate evidence collection.",
                "CallbackQueryHandler registrations are Telegram transport evidence, not browser actions. They have status TELEGRAM_TRANSPORT_HANDLER and do not contribute a route, runtime, payment, provider, job or delivery claim.",
                "A handlers/ package source file not statically reachable from the observed bot.py entrypoint is retained as UNREFERENCED_BY_OBSERVED_ENTRYPOINT evidence and excluded from runtime parity metrics. This is not a deletion, a general module-closure audit, or a claim that the file can never be loaded by an unobserved deployment path.",
                "Schema 1.4 coverage percentages are NOT_COMPARABLE_TO_PREVIOUS_AUDIT_PERCENTAGES because audit source scope was corrected; a percentage delta is not feature progress.",
                "Unresolved callback templates and dashboard fallbacks are source markers only. They are not browser actions and lower mapping coverage until a typed disposition exists.",
                "COPIED_GUARDED is a real signed/guarded Web compatibility surface, not a provider, wallet, job, or output success claim.",
                "MAPPED_TO_EXISTING_ROUTE only confirms a static Web route was found; it does not prove auth, wallet, provider, job, or output parity.",
                "NAVIGATION_ENTRYPOINT and NAVIGATION_ONLY are reviewed launch/navigation records, not feature parity. NEEDS_FEATURE_DISPOSITION records were previously absorbed by a dashboard fallback and now remain actionable.",
                "Workflow-equivalence coverage is intentionally zero in a static-only audit until a separate runtime evidence suite verifies each claimed flow.",
                "TELEGRAM_ONLY records are intentionally not made browser actions without a separate product/security decision.",
            ],
        }
    )


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(value.replace("|", "\\|").replace("\n", " ") for value in row) + " |")
    return "\n".join(lines)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _render_docs(docs_dir: Path, preflight: dict[str, Any], bot: dict[str, Any], web: dict[str, Any], gap: dict[str, Any]) -> list[Path]:
    docs_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    revision = preflight.get("bot", {}).get("revision", {})
    checkout_sha = str(revision.get("checkout_sha") or "unavailable")
    relation = str(revision.get("baseline_relation") or "comparison_unavailable")
    ahead = revision.get("ahead_commits")
    behind = revision.get("behind_commits")
    baseline_bridge = preflight.get("bot", {}).get("baseline_bridge_source", {})
    baseline_bridge_state = str(baseline_bridge.get("state") or "not_checked")
    baseline_bridge_present = baseline_bridge.get("present")
    bridge_contract = gap.get("bridge_contract") if isinstance(gap.get("bridge_contract"), dict) else {}
    telegram_callback_contract = gap.get("telegram_link_callback_contract") if isinstance(gap.get("telegram_link_callback_contract"), dict) else {}
    feature_disposition_backlog = gap.get("feature_disposition_backlog") if isinstance(gap.get("feature_disposition_backlog"), list) else []
    callback_handler_mappings = gap.get("callback_handler_mappings") if isinstance(gap.get("callback_handler_mappings"), list) else []
    callback_handler_summary = gap.get("callback_handler_summary") if isinstance(gap.get("callback_handler_summary"), dict) else {}
    handler_module_observation = gap.get("handler_module_observation") if isinstance(gap.get("handler_module_observation"), dict) else {}
    unreferenced_static_module_mappings = gap.get("unreferenced_static_module_mappings") if isinstance(gap.get("unreferenced_static_module_mappings"), list) else []
    metric_scope = gap.get("metric_scope") if isinstance(gap.get("metric_scope"), dict) else {}
    coverage_comparability = gap.get("coverage_comparability") if isinstance(gap.get("coverage_comparability"), dict) else {}
    telegram_callback_status = str(telegram_callback_contract.get("status") or "NOT_AUDITED")
    bridge_status = str(bridge_contract.get("status") or "NOT_AUDITED")
    bridge_matched = int(bridge_contract.get("matched_request_count") or 0)
    bridge_requests = int(bridge_contract.get("web_request_count") or 0)
    revision_summary = f"- Bot checkout audited: `{checkout_sha}` (`{relation}`)\n"
    if ahead is not None or behind is not None:
        revision_summary += f"- Bot drift versus requested baseline: ahead `{ahead if ahead is not None else 'unknown'}`, behind `{behind if behind is not None else 'unknown'}` commits\n"

    def write(name: str, content: str) -> None:
        path = docs_dir / name
        _write_text(path, _sanitize(content))
        generated.append(path)

    write(
        "README.md",
        "# P0 WebApp CopyFast1 migration inventory\n\n"
        "This directory is generated by `scripts/migration/audit_bot_to_web.py`. The audit parses source files only; it does not import or run the Telegram bot, FastAPI app, database, providers, payment service, or environment files.\n\n"
        f"- Bot baseline requested: `{preflight['bot']['baseline_sha_requested']}`\n"
        + revision_summary
        + f"- Bot source fingerprint: `{bot['source_fingerprint_sha256']}`\n"
        + f"- Web source fingerprint: `{web['source_fingerprint_sha256']}`\n"
        + f"- Noncanonical Bot draft files excluded from inventory: `{len(bot.get('excluded_noncanonical_source_files', []))}`\n"
        + "- Canonical authority remains the bot for Telegram identity, Xu ledger, PayOS, jobs, and provider state.\n\n"
        + f"- Requested baseline private bridge source (`{CORE_BRIDGE_FILE}`): `{baseline_bridge_state}` (`present={baseline_bridge_present}`).\n"
        + f"- Static Web-to-Bot bridge contract: `{bridge_status}` (`{bridge_matched}/{bridge_requests}` outbound calls have a current-checkout route match). This is not a deployment/reachability claim.\n\n"
        + f"- Static Bot-to-Web Telegram identity callback: `{telegram_callback_status}`. This is not a Railway/Telegram live-flow claim.\n\n"
        + "The generated parity matrix is an implementation backlog, not a claim that surfaces are live or safe to enable.\n\n"
        + "## Web implementation contracts\n\n"
        + "- [`FEATURE_FAMILY_NAVIGATION.md`](FEATURE_FAMILY_NAVIGATION.md) — navigation-only feature families.\n"
        + "- [`CALLBACK_HANDLER_DISPATCH_MAP.md`](CALLBACK_HANDLER_DISPATCH_MAP.md) — Bot callback dispatcher registrations, their source provenance and why they are not browser actions.\n"
        + "- [`UNREFERENCED_STATIC_MODULES.md`](UNREFERENCED_STATIC_MODULES.md) — scoped legacy Bot `handlers/` package evidence outside the observed `bot.py` import closure; it is not silently counted as live parity.\n"
        + "- [`FALLBACK_FEATURE_DISPOSITION.md`](FALLBACK_FEATURE_DISPOSITION.md) — every dashboard/catch-all fallback grouped by its required authority boundary; a candidate boundary is not an implementation claim.\n"
        + "- [`CAPABILITY_HUB_CONTRACT.md`](CAPABILITY_HUB_CONTRACT.md) — aggregate static Bot-to-Web coverage for the product catalog; no raw commands, callbacks or engine-success claim.\n"
        + "- [`WEB_ENGINE_REGISTRY_CONTRACT.md`](WEB_ENGINE_REGISTRY_CONTRACT.md) — display-only classification of Web-native, Bot companion and guarded execution boundaries.\n"
        + "- [`SUBTITLE_FORMAT_LAB_CONTRACT.md`](SUBTITLE_FORMAT_LAB_CONTRACT.md) — signed, stateless SRT↔VTT and text→SRT transform with no Bot/provider/job/payment/file-delivery claim.\n"
        + "- [`SUBTITLE_ASSET_OPERATIONS_CONTRACT.md`](SUBTITLE_ASSET_OPERATIONS_CONTRACT.md) — bounded owner-scoped Asset Vault SRT/VTT validation and verified private conversion attachment; no ASR/translation/dubbing/provider/Bot/payment claim.\n"
        + "- [`CONTENT_PROMPT_PACK_CONTRACT.md`](CONTENT_PROMPT_PACK_CONTRACT.md) — signed, stateless deterministic content-planning drafts adapted from Bot text recipes without Bot/provider/job/payment/publish claims.\n"
        + "- [`PUBLISH_REVIEW_PACK_CONTRACT.md`](PUBLISH_REVIEW_PACK_CONTRACT.md) — signed, stateless text-only review package adapted from the Bot’s pending-result formatter, with no social account/scheduler/provider/Bot/job/payment/asset/publish/delivery claim.\n"
        + "- [`CONTEXTUAL_AD_PROMPT_WIZARD_CONTRACT.md`](CONTEXTUAL_AD_PROMPT_WIZARD_CONTRACT.md) — signed, stateless contextual ad-prompt wizard adapted from Bot goal/platform/ratio/style choices, with no Meta/provider/Bot/job/payment/media-output/publish claim.\n"
        + "- [`TREND_RESEARCH_CONTRACT.md`](TREND_RESEARCH_CONTRACT.md) — signed, stateless manual trend-research checklist adapted from Bot keyword/selection/originality guidance, with no live search/scraping/provider/Bot/job/payment claim.\n"
        + "- [`MEDIA_FACTORY_BLUEPRINT_CONTRACT.md`](MEDIA_FACTORY_BLUEPRINT_CONTRACT.md) — signed, stateless Media Factory blueprint adapted from the Bot's content/video-pack plan, with no live search/provider/Bot/job/payment/media-output/publish claim.\n"
        + "- [`CREATIVE_FLOW_COMPOSER_CONTRACT.md`](CREATIVE_FLOW_COMPOSER_CONTRACT.md) — signed, stateless Creative Flow template adapted from the Bot's hook/script/image/music/SFX/caption guidance, with no provider/Bot/job/payment/media-output/publish claim.\n"
        + "- [`VIDEO_FACTORY_WORKFLOW_CONTRACT.md`](VIDEO_FACTORY_WORKFLOW_CONTRACT.md) — signed, read-only seven-step Video Factory workflow map adapted from the Bot, with no input transfer/provider/Bot/job/payment/media-output/publish claim.\n"
        + "- [`STORY_VIDEO_PLANNER_CONTRACT.md`](STORY_VIDEO_PLANNER_CONTRACT.md) — signed, stateless story workflow/motion-direction plan adapted from Bot prompt-only commands, with no provider/Bot/job/payment/video-output/publish claim.\n"
        + "- [`SOURCE_RIGHTS_GUIDE_CONTRACT.md`](SOURCE_RIGHTS_GUIDE_CONTRACT.md) — signed, read-only source/license/dubbing guidance adapted from Bot public safety commands, with no rights-verification/provider/Bot/job/payment/output/publish claim.\n"
        + "- [`IMAGE_PROMPT_COMPOSER_CONTRACT.md`](IMAGE_PROMPT_COMPOSER_CONTRACT.md) — signed, stateless image-prompt drafting adapted from Bot templates without image/vision/provider/job/payment/asset/publish claims.\n"
        + "- [`VIDEO_PROMPT_PLANNER_CONTRACT.md`](VIDEO_PROMPT_PLANNER_CONTRACT.md) — signed, stateless deterministic video planning adapted from Bot prompt/shot rules without source-media/provider/preview/job/payment/asset/publish claims.\n"
        + "- [`CINEMATIC_AD_CONCEPT_CONTRACT.md`](CINEMATIC_AD_CONCEPT_CONTRACT.md) — signed, stateless Bot-derived cinematic ad concept, storyboard and prompt direction with no media/provider/job/payment/asset/publish claim.\n"
        + "- [`STORYBOARD_PROMPT_PACK_COMPOSER_CONTRACT.md`](STORYBOARD_PROMPT_PACK_COMPOSER_CONTRACT.md) — signed, stateless Bot-derived storyboard prompt-pack planning with a visual canon and no render/provider/job/payment/asset/publish claim.\n"
        + "- [`VOICE_DIRECTION_COMPOSER_CONTRACT.md`](VOICE_DIRECTION_COMPOSER_CONTRACT.md) — signed, stateless Bot-derived voice delivery directions with no clone/TTS/provider/audio/job/payment/asset/Telegram action.\n"
        + "- [`MUSIC_PROMPT_COMPOSER_CONTRACT.md`](MUSIC_PROMPT_COMPOSER_CONTRACT.md) — signed, stateless Bot-derived music prompt directions with no Suno/provider/audio/job/payment/asset/collection/Telegram action.\n"
        + "- [`JOB_SUPPORT_RECOVERY.md`](JOB_SUPPORT_RECOVERY.md) — safe job-to-ticket recovery handoff.\n"
        + "- [`CONTENT_OPERATIONS_ADMIN.md`](CONTENT_OPERATIONS_ADMIN.md) — guarded Campaign/Calendar/Publishing/Admin navigation.\n"
        + "- [`ADMIN_DOMAIN_CENTERS_CONTRACT.md`](ADMIN_DOMAIN_CENTERS_CONTRACT.md) — safe first-class Admin navigation for Publishing, Growth, Finance and Trends.\n"
        + "- [`ASSET_VAULT_CONTRACT.md`](ASSET_VAULT_CONTRACT.md) — private Web-owned source storage and owner-scoped delivery.\n"
        + "- [`PROJECT_PACKAGE_CONTRACT.md`](PROJECT_PACKAGE_CONTRACT.md) — private immutable Project ZIP exports.\n"
        + "- [`PDF_SPLIT_CONTRACT.md`](PDF_SPLIT_CONTRACT.md), [`PDF_MERGE_CONTRACT.md`](PDF_MERGE_CONTRACT.md) and [`PDF_OPTIMIZE_CONTRACT.md`](PDF_OPTIMIZE_CONTRACT.md) — bounded private PDF structure operations.\n"
        + "- [`IMAGE_TO_PDF_CONTRACT.md`](IMAGE_TO_PDF_CONTRACT.md) — ordered private image-to-PDF delivery.\n"
        + "- [`PDF_TO_IMAGES_CONTRACT.md`](PDF_TO_IMAGES_CONTRACT.md) — Bot-compatible 2× PDF raster delivery as verified private PNG or deterministic PNG ZIP.\n"
        + "- [`PDF_TO_WORD_CONTRACT.md`](PDF_TO_WORD_CONTRACT.md) — real text-only private PDF-to-DOCX extraction.\n"
        + "- [`IMAGE_OCR_CONTRACT.md`](IMAGE_OCR_CONTRACT.md) — opt-in local private image OCR with verified TXT delivery; no browser OCR, provider, Bot, job, wallet or payment execution.\n"
        + "- [`PDF_OCR_CONTRACT.md`](PDF_OCR_CONTRACT.md) — opt-in bounded private PDF OCR through local PDFium/Tesseract with verified TXT delivery; no browser OCR, provider, Bot, job, wallet or payment execution.\n"
        + "- [`PDF_OCR_WORD_CONTRACT.md`](PDF_OCR_WORD_CONTRACT.md) — opt-in bounded local scanned-PDF OCR to verified private DOCX; no browser OCR, provider, Bot, job, wallet or payment execution.\n"
        + "- [`IMAGE_RESIZE_ASPECT_CONTRACT.md`](IMAGE_RESIZE_ASPECT_CONTRACT.md) and [`IMAGE_ENHANCE_CONTRACT.md`](IMAGE_ENHANCE_CONTRACT.md) — bounded local private image artifacts.\n"
        + "- [`VIDEO_POSTER_OPERATION_CONTRACT.md`](VIDEO_POSTER_OPERATION_CONTRACT.md) — disabled-by-default, bounded private JPEG poster extraction from an owner-scoped Asset Vault video; it is not Video Studio rendering, a Bot job, provider call, wallet/Xu or PayOS flow.\n"
        + "- [`MEMORY_CENTER_CONTRACT.md`](MEMORY_CENTER_CONTRACT.md) — signed Web-owned notes, version history and view-only reminders.\n"
        + "- [`TELEGRAM_WEB_CONNECTION.md`](TELEGRAM_WEB_CONNECTION.md) — browser-bound Telegram one-time link/login.\n"
        + "- [`BRIDGE_CONTRACT_INVENTORY.md`](BRIDGE_CONTRACT_INVENTORY.md) — static Web-to-Bot method/path compatibility, not live health.\n"
        + "- [`BOT_COMPANION_HANDOFF.md`](BOT_COMPANION_HANDOFF.md) — remaining Bot-first referral/rewards, community and help handoffs.\n"
        + "- [`FEATURE_CONFIRM_CONTRACT.md`](FEATURE_CONFIRM_CONTRACT.md) — explicit job tracking/confirm contract.\n"
        + "- [`ENGINE_DELIVERY_ADAPTER_BACKLOG.md`](ENGINE_DELIVERY_ADAPTER_BACKLOG.md) — canonical job/output/delivery prerequisites.\n"
        + "- [`ADMIN_FAILED_JOB_INCIDENTS.md`](ADMIN_FAILED_JOB_INCIDENTS.md) and [`ADMIN_WRITE_CONTRACT.md`](ADMIN_WRITE_CONTRACT.md) — guarded Admin incident/write boundaries.\n"
        + "- [`ADMIN_INTERNAL_DOCUMENT_ARCHIVE_CONTRACT.md`](ADMIN_INTERNAL_DOCUMENT_ARCHIVE_CONTRACT.md) — opt-in local-admin private document archive with isolated immutable versions; it does not migrate or call Bot internal-document state.\n",
    )
    write(
        "inventory.md",
        "# Static inventory\n\n"
        + _markdown_table(
            ["Area", "Bot", "Web App"],
            [
                ["Source files scanned", str(bot["source_files_scanned"]), str(web["source_files_scanned"])],
                ["Noncanonical Bot drafts excluded", str(len(bot.get("excluded_noncanonical_source_files", []))), "n/a"],
                ["Commands", str(bot["counts"]["commands"]), "n/a"],
                ["Callback handler registrations", str(bot["counts"]["callback_handlers"]), "Dispatcher evidence only; not a user-action parity claim"],
                ["Callback-data values", str(bot["counts"]["callback_data"]), "n/a"],
                ["Legacy handlers/ package records outside observed runtime", str(len(unreferenced_static_module_mappings)), "Evidence only; excluded from product-action coverage"],
                ["Unresolved callback templates", str(bot["counts"].get("callback_templates", 0)), "n/a"],
                ["Conversation handlers", str(bot["counts"]["conversations"]), "n/a"],
                ["FastAPI routes", str(bot["counts"]["routes"]), str(web["counts"]["routes"])],
                ["Background/job signals", str(bot["counts"]["background_jobs"]), str(web["counts"]["background_jobs"])],
                ["Database tables", str(bot["counts"]["database_tables"]), str(web["counts"]["database_tables"])],
                ["Environment names", str(bot["counts"]["env_references"]), str(web["counts"]["env_references"])],
                ["Provider names", str(bot["counts"]["providers"]), str(web["counts"]["providers"])],
            ],
        )
        + "\n\nReports contain the complete machine-readable records. Values matching secret formats are redacted.\n",
    )
    sampled_commands = [[f"/{item['command']}", item["handler"], item["file"]] for item in bot["commands"][:100]]
    write(
        "bot-inventory.md",
        "# Telegram bot inventory\n\n"
        f"Discovered `{bot['counts']['commands']}` registered commands, `{bot['counts']['callback_handlers']}` callback-handler registrations, `{bot['counts']['callback_data']}` concrete callback-data values, and `{bot['counts'].get('callback_templates', 0)}` unresolved callback templates from static source. A handler registration is dispatcher evidence, not one customer action. `{len(unreferenced_static_module_mappings)}` records belong to the legacy `handlers/` package outside the observed `bot.py` import closure and stay evidence-only.\n\n"
        + ("Excluded clearly named Bot drafts: `" + "`, `".join(bot.get("excluded_noncanonical_source_files", [])) + "`.\n\n" if bot.get("excluded_noncanonical_source_files") else "")
        + _markdown_table(["Command", "Handler", "Source"], sampled_commands or [["None discovered", "", ""]])
        + "\n\nThe full command/callback inventory is in `reports/migration/bot_inventory.json`.\n",
    )
    callback_handler_rows = [
        [
            str(item.get("handler") or ""),
            str(item.get("pattern") or ""),
            str(item.get("classification") or ""),
            str(item.get("target") or ""),
            ", ".join(str(value) for value in item.get("source_dispositions", [])),
            str(item.get("resolution") or ""),
            str(item.get("evidence", {}).get("file") or ""),
            str(item.get("evidence", {}).get("line") or ""),
        ]
        for item in callback_handler_mappings[:200]
        if isinstance(item, dict)
    ]
    write(
        "CALLBACK_HANDLER_DISPATCH_MAP.md",
        "# Callback handler dispatch map\n\n"
        + f"Static registrations: `{int(callback_handler_summary.get('total') or 0)}`; observed-runtime registrations: `{int(callback_handler_summary.get('observed_runtime_registrations') or 0)}`; unreferenced-module registrations: `{int(callback_handler_summary.get('unreferenced_static_module_registrations') or 0)}`; catch-all: `{int(callback_handler_summary.get('catch_all') or 0)}`; patterned: `{int(callback_handler_summary.get('patterned') or 0)}`. "
        + "A `CallbackQueryHandler` registration routes Telegram traffic to Bot code. It is **not** a browser action, Web route, provider call, payment action, job claim or output-delivery claim, and it is excluded from product-action coverage.\n\n"
        + _markdown_table(
            ["Bot handler", "Pattern", "Classification", "Web target", "Source disposition", "Resolution", "File", "Line"],
            callback_handler_rows or [["None discovered", "", "", "", "", "", "", ""]],
        )
        + "\n\nBefore any callback family is marked as Web parity, recover the finite handler branch and separately prove signed authorization, CSRF for writes, canonical ownership, provider/job/payment boundaries and private output delivery.\n",
    )
    unreferenced_static_rows = [
        [
            str(item.get("source_kind") or ""),
            str(item.get("source") or ""),
            str(item.get("status") or ""),
            str(item.get("evidence", {}).get("file") or ""),
            str(item.get("evidence", {}).get("line") or ""),
        ]
        for item in unreferenced_static_module_mappings[:200]
        if isinstance(item, dict)
    ]
    write(
        "UNREFERENCED_STATIC_MODULES.md",
        "# Unreferenced static Bot handler-package modules\n\n"
        + f"Observation status: `{handler_module_observation.get('status') or 'NOT_AUDITED'}`. Observed entrypoint: `{handler_module_observation.get('observed_entrypoint') or 'unavailable'}`. "
        + f"Records preserved outside the observed-runtime denominator: `{len(unreferenced_static_module_mappings)}`. "
        + "This scoped source-only observation evaluates the local `handlers/` package, not every Python module in the repository. It does not delete a file or prove that an arbitrary deployment can never load it. It only prevents a handler-package module with no static path from the observed entrypoint from becoming a false Web parity claim.\n\n"
        + "## Handler-package files outside the observed import closure\n\n"
        + ("\n".join(f"- `{path}`" for path in handler_module_observation.get("unreferenced_module_files", [])) or "- None")
        + "\n\n## Preserved source evidence\n\n"
        + _markdown_table(
            ["Source type", "Bot entry", "Disposition", "File", "Line"],
            unreferenced_static_rows or [["None", "", "", "", ""]],
        )
        + "\n\nA module moves back into the runtime parity denominator only after a static import path from the observed entrypoint is present and its finite behavior is reviewed.\n",
    )
    write(
        "web-inventory.md",
        "# Web App inventory\n\n"
        + _markdown_table(
            ["Route", "Methods", "Endpoint"],
            [[item["path"], ", ".join(item["methods"]), item["endpoint"]] for item in web["routes"][:160]] or [["None discovered", "", ""]],
        )
        + "\n\nStatic route presence is not proof of session protection, ownership checks, or functional feature parity.\n",
    )
    bridge_rows = [
        [
            str(item.get("request", {}).get("method") or ""),
            str(item.get("request", {}).get("path") or ""),
            ", ".join(str(route.get("path") or "") for route in item.get("bot_routes", [])[:3]),
            str(item.get("request", {}).get("file") or ""),
        ]
        for item in bridge_contract.get("matched_requests", [])[:200]
        if isinstance(item, dict)
    ]
    missing_bridge_rows = [
        [str(item.get("method") or ""), str(item.get("path") or ""), str(item.get("file") or ""), str(item.get("line") or "")]
        for item in (bridge_contract.get("unmatched_requests", []) + bridge_contract.get("unresolved_requests", []))[:200]
        if isinstance(item, dict)
    ]
    write(
        "BRIDGE_CONTRACT_INVENTORY.md",
        "# Private Core Bridge static contract\n\n"
        + f"Status: **{bridge_status}**. Web outbound calls matched: `{bridge_matched}/{bridge_requests}`. "
        + "The comparison parses source only; it does not contact the Bot, Railway, Telegram, PayOS, a provider, or read an environment value.\n\n"
        + f"- Bot bridge source present: `{bool(bridge_contract.get('bot_bridge_source_present'))}`\n"
        + f"- Bot router mount observed in current checkout: `{bool(bridge_contract.get('bot_router_mount_observed'))}`\n"
        + f"- Requested baseline bridge source: `{baseline_bridge_state}` (`present={baseline_bridge_present}`)\n"
        + f"- Unmatched Web calls: `{int(bridge_contract.get('unmatched_request_count') or 0)}`\n"
        + f"- Unresolved dynamic Web calls: `{int(bridge_contract.get('unresolved_request_count') or 0)}`\n\n"
        + "## Matched method/path shapes\n\n"
        + _markdown_table(["Method", "Web request", "Bot route candidate", "Web source"], bridge_rows or [["None", "", "", ""]])
        + "\n\n## Gaps requiring a contract change\n\n"
        + _markdown_table(["Method", "Web request", "Web source", "Line"], missing_bridge_rows or [["None", "", "", ""]])
        + "\n\n## Telegram one-time identity callback\n\n"
        + f"Static status: **{telegram_callback_status}**. Expected Web receiver: `{telegram_callback_contract.get('expected_web_callback_path') or 'unavailable'}`. "
        + "The Bot→Web callback uses separate bearer/HMAC credentials and is not part of the Web→Bot core bridge credential.\n\n"
        + _markdown_table(
            ["Check", "Bot", "Web"],
            [
                ["Deep link / fallback", str(telegram_callback_contract.get("bot", {}).get("deep_link_handler_observed")), str(telegram_callback_contract.get("bot", {}).get("fallback_link_command_observed"))],
                ["Callback sender / receiver", str(telegram_callback_contract.get("bot", {}).get("callback_sender_observed")), str(telegram_callback_contract.get("web", {}).get("receiver_route_observed"))],
                ["HMAC authorization", str(all(telegram_callback_contract.get("bot", {}).get("callback_headers_observed", {}).values())), str(telegram_callback_contract.get("web", {}).get("receiver_hmac_authorizer_observed"))],
                ["HMAC material shape", str(telegram_callback_contract.get("bot", {}).get("callback_signature_shape_observed")), str(telegram_callback_contract.get("web", {}).get("callback_signature_shape_observed"))],
                ["Raw browser ID rejected", "n/a", str(telegram_callback_contract.get("web", {}).get("raw_browser_id_rejection_observed"))],
            ],
        )
        + "\n\nA matched path does not authorize a feature. Bearer/HMAC, session ownership, schema, idempotency, provider readiness, payment policy, job validation and delivery safety must pass independently.\n",
    )
    parity_rows = [
        [item["source_kind"], item["source"], item["target"], item["status"]]
        for item in (gap["command_mappings"] + gap["callback_mappings"] + gap.get("callback_template_mappings", []) + gap["conversation_mappings"])[:200]
    ]
    write(
        "parity-matrix.md",
        "# Parity matrix\n\n"
        f"Observed-runtime static Web-surface coverage: **{gap['static_web_surface_coverage_percent']}%** (`MAPPED_TO_EXISTING_ROUTE` + `COPIED_GUARDED`). "
        f"Observed-runtime typed source-disposition coverage: **{gap['mapping_coverage_percent']}%**; unresolved callback templates and dashboard fallbacks lower this value until they have a typed disposition. "
        f"Runtime workflow-equivalence verification: **{gap['workflow_equivalence']['coverage_percent']}%** (`{gap['workflow_equivalence']['status']}`). "
        f"Product-action denominator: `{int(metric_scope.get('product_action_denominator') or 0)}`; excluded Telegram transport registrations: `{int(metric_scope.get('excluded_telegram_transport_handlers') or 0)}`; excluded unreferenced `handlers/` package records: `{int(metric_scope.get('excluded_unreferenced_handler_package_records') or 0)}`. **Comparability: `{coverage_comparability.get('status') or 'NOT_AUDITED'}` — this percentage is not feature progress and must not be compared with earlier audit percentages after the denominator correction.** All source items remain represented in JSON evidence; this page shows the first 200 reachable product records.\n\n"
        + _markdown_table(["Source type", "Bot entry", "Web target", "Status"], parity_rows or [["None discovered", "", "", ""]])
        + "\n\n`COPIED_GUARDED` means a signed/guarded compatibility page exists; it never claims an engine, payment, or output completed. `NAVIGATION_ENTRYPOINT` and `NAVIGATION_ONLY` are reviewed launches only. `NEEDS_FEATURE_DISPOSITION` remains actionable until it is mapped to a real Web workflow, a guarded runtime boundary, admin-only, or `TELEGRAM_ONLY`. `TELEGRAM_TRANSPORT_HANDLER` and `UNREFERENCED_BY_OBSERVED_ENTRYPOINT` are evidence-only statuses outside the product-action denominator.\n",
    )
    fallback_rows = [
        [
            str(item.get("priority") or ""),
            str(item.get("family") or ""),
            str(item.get("count") or 0),
            str(item.get("candidate_boundary") or ""),
            str(item.get("authority") or ""),
            ", ".join(str(value) for value in item.get("source_dispositions", [])),
            str(item.get("source_evidence") or ""),
            str(item.get("next_contract") or ""),
        ]
        for item in feature_disposition_backlog
    ]
    write(
        "FALLBACK_FEATURE_DISPOSITION.md",
        "# Dashboard fallback feature-disposition backlog\n\n"
        "Concrete callbacks below were previously able to fall through to dashboard/catch-all navigation. Callback-handler registrations and unreferenced `handlers/` package records are retained in separate evidence documents, never browser actions. Every row is a required migration decision. `Candidate boundary` names the first contract to design; it does **not** claim that the route, runtime, provider, payment, job or output is already implemented.\n\n"
        + _markdown_table(
            ["Priority", "Bot family", "Entries", "Candidate boundary", "Authority", "Source disposition", "Source evidence", "Required next contract"],
            fallback_rows or [["None", "", "0", "", "", "", "", ""]],
        )
        + "\n\nBefore a row leaves this backlog, preserve the source evidence and add focused tests for signed authorization, CSRF where a Web write exists, canonical ownership, idempotency where relevant, safe guarded state, and validated private delivery for any output.\n",
    )
    route_rows = [[item["source"], item["target"], item["status"]] for item in gap["command_mappings"][:200]]
    write(
        "route-map.md",
        "# Route and action map\n\n"
        "This maps Telegram entry points to the intended Web route family. Existing-route status uses the signed `app.py` entrypoint plus its directly included routers; unmounted legacy decorators are not treated as production routes. A dashboard navigation fallback is never counted as feature parity and remains `NEEDS_FEATURE_DISPOSITION`.\n\n"
        "## Additive Web-native route (not a Telegram command mapping)\n\n"
        "| Web route/action | Authority | Status |\n"
        "| --- | --- | --- |\n"
        "| `/api/v1/video-operations/*` (not yet a public catalogue route) | Signed Web account + private Asset Vault source | `WEB_NATIVE_DISABLED_BY_DEFAULT` — bounded JPEG poster utility; no Bot/provider/PayOS/wallet delegation and no claim that existing `/video/*` Bot companion routes render media. It stays outside the public registry until the dedicated signed workbench is implemented in the broader video navigation/UI phase. |\n\n"
        + _markdown_table(["Telegram command", "Web route/action", "Status"], route_rows or [["None discovered", "", ""]])
        + "\n",
    )
    bot_tables = set(bot["database_tables"])
    web_tables = set(web["database_tables"])
    write(
        "state-database-map.md",
        "# State and database authority map\n\n"
        "The bot remains the canonical writer for identity, wallet, PayOS, jobs, and provider state. The Web App consumes typed bridge contracts and must not duplicate those writes.\n\n"
        + _markdown_table(
            ["Table set", "Count", "Examples"],
            [
                ["Bot discovered", str(len(bot_tables)), ", ".join(sorted(bot_tables)[:30]) or "None"],
                ["Web discovered", str(len(web_tables)), ", ".join(sorted(web_tables)[:30]) or "None"],
                ["Bot-only (bridge/read contract required)", str(len(bot_tables - web_tables)), ", ".join(sorted(bot_tables - web_tables)[:30]) or "None"],
            ],
        )
        + "\n\n## Additive Web-native Video Poster state\n\n"
        + "| Table | Owner | Purpose | Explicitly not authoritative for |\n"
        + "| --- | --- | --- | --- |\n"
        + "| `web_video_operations` | Signed Web account | One bounded private poster request, sealed output metadata and exact lifecycle | Bot jobs, provider execution, wallet/Xu, PayOS, Telegram identity or Asset Vault source ownership |\n"
        + "| `web_video_operation_attempts` | Web operation | In-request execution attempt/fence audit; future worker seam only | Durable worker lease, automatic retry, provider job or billing attempt |\n"
        + "| `web_video_operation_events` | Web operation | Ordered lifecycle evidence | Bot audit log, payment ledger, webhook, notification or delivery receipt |\n\n"
        + "These are additive schema records. They do not migrate, synchronize, infer or\n"
        + "overwrite any Bot table. The Bot remains the canonical writer for its own\n"
        + "identity, wallet, PayOS, jobs and provider state.\n\n"
        + "No destructive migration or schema synchronization is authorized by this inventory.\n",
    )
    wallet_tables = [table for table in sorted(bot_tables) if any(term in table for term in ("payos", "credit", "transaction", "payment", "job", "wallet"))]
    write(
        "payos-wallet-jobs.md",
        "# PayOS, wallet, and jobs boundary\n\n"
        "- Canonical writer: Telegram bot.\n"
        "- Web App role: signed-session caller of the private bridge; it must never credit Xu, finalize PayOS, or add a second payment webhook.\n"
        "- Manual top-up is a Telegram Bot-only handoff until a separate read-only, owner-scoped and redacted `pending_deposits` bridge contract exists. Web must not receive bills/TXIDs, create requests, run review actions or infer approval from a browser event.\n"
        "- Provider/payments remain disabled in local/test unless an explicit feature flag and approved integration are present.\n\n"
        "## Related bot tables detected statically\n\n"
        + ("\n".join(f"- `{table}`" for table in wallet_tables) or "- None detected")
        + "\n\nCompletion must remain conditional on validated output, not a pending/provider acknowledgement.\n",
    )
    admin_commands = [
        item for item in bot["commands"]
        if _is_admin_command(item["command"], item["handler"], admin_guarded=bool(item.get("admin_guarded")))
    ]
    write(
        "admin-map.md",
        "# Admin ERP map\n\n"
        "Admin entries must resolve authority from a canonical signed session and server-side role, never from a browser-supplied ID. Write actions need CSRF, confirmation, permission checks, idempotency where applicable, and audit logging.\n\n"
        + _markdown_table(
            ["Bot command", "Handler", "Planned Web target"],
            [[f"/{item['command']}", item["handler"], f"/admin/{item['command']}"] for item in admin_commands[:200]] or [["None discovered", "", ""]],
        ),
    )
    provider_rows = [[item["provider"], str(item["occurrences"]), ", ".join(item["files"][:5])] for item in bot["providers"]]
    write(
        "env-provider-map.md",
        "# Environment and provider map\n\n"
        "Only environment variable names are recorded. Values are never read and secret-shaped static literals are redacted.\n\n"
        "## Bot environment names\n\n"
        + "\n".join(f"- `{record['name']}`" for record in bot["env_references"])[:20000]
        + "\n\n## Bot provider markers\n\n"
        + _markdown_table(["Provider", "Occurrences", "Sample files"], provider_rows or [["None detected", "", ""]])
        + "\n\n## Web-native Video Poster environment names\n\n"
        + "These are Web-local configuration names, not Bot/provider credentials. They\n"
        + "remain unset/false unless an operator deliberately enables the reviewed local\n"
        + "runtime:\n\n"
        + "- `WEBAPP_VIDEO_OPERATIONS_ENABLED` (default `false`)\n"
        + "- `WEBAPP_VIDEO_POSTER_ENABLED` (default `false`)\n"
        + "- `WEBAPP_VIDEO_OPERATIONS_ROOT`\n"
        + "- `WEBAPP_VIDEO_OPERATIONS_MAX_OUTPUT_MB` (default `4`)\n"
        + "- `WEBAPP_VIDEO_OPERATIONS_QUOTA_MB` (default `50`)\n"
        + "- `WEBAPP_VIDEO_OPERATIONS_TOPOLOGY` (must be `sqlite_single_replica` when the poster runtime is enabled)\n"
        + "- one of `RAILWAY_REPLICA_COUNT`, `RAILWAY_REPLICAS` or `WEBAPP_REPLICA_COUNT` (must attest exactly `1` for every enabled runtime)\n"
        + "- `WEBAPP_VIDEO_FFMPEG_BIN`\n"
        + "- `WEBAPP_VIDEO_FFPROBE_BIN`\n\n"
        + "They do not contain an API key and must not be used as a provider, Bot,\n"
        + "PayOS, wallet, webhook or production-deployment toggle. Enabling the feature\n"
        + "also requires the existing private Asset Vault gate and a separately supplied\n"
        + "FFmpeg/ffprobe runtime.\n",
    )
    key4u_features = [
        ("Video", "video_single, video_multiscene, video_long"),
        ("Voice / audio", "voice_tts, voice_clone, voice_saved_tts"),
        ("Music", "music_background, music_song, music_library, sfx_library"),
        ("Caption / dub", "subtitle_asr, subtitle_translate, video_dub"),
    ]
    key4u_seen = "Key4U" in bot["provider_names"]
    write(
        "key4u-map.md",
        "# Key4U mapping\n\n"
        f"Key4U static marker observed in bot source: **{'yes' if key4u_seen else 'no'}**. This audit makes no network call and does not verify a key, balance, model availability, or paid endpoint.\n\n"
        + _markdown_table(["Capability family", "Feature keys to validate"], [[family, keys] for family, keys in key4u_features])
        + "\n\nBefore enabling each feature, verify provider adapter, required ENV name, quote/confirm policy, job polling, output validation, and public-safe failure copy through the private bridge.\n",
    )
    gap_rows = [[item["area"], item["severity"], str(item["count"]), item["detail"]] for item in gap["gaps"]]
    write(
        "known-gaps.md",
        "# Known gaps from static audit\n\n"
        + _markdown_table(["Area", "Severity", "Count", "Finding"], gap_rows)
        + "\n\nThese are static findings. Resolve each through contracts and tests before marking a Web App flow complete.\n\n"
        + "## Additive Web-native guard: Video Poster Lab\n\n"
        + "Video Poster Lab is intentionally outside the static Telegram mapping counts: it\n"
        + "is a Web-owned utility, not a replacement for a Telegram command. Its code and\n"
        + "schema may exist while the operation stays disabled by default. It must remain\n"
        + "guarded until all of the following are true in the target environment:\n\n"
        + "- Asset Vault and both Video Poster execution flags are explicitly enabled;\n"
        + "- the isolated private Video Operations root and trusted `ffmpeg`/`ffprobe`\n"
        + "  runtime are available; and\n"
        + "- the deployment explicitly attests `WEBAPP_VIDEO_OPERATIONS_TOPOLOGY=sqlite_single_replica`\n"
        + "  and an available replica-count variable equals exactly `1`; and\n"
        + "- the operator accepts the current bounded request-time model. It has no\n"
        + "  durable queue, retry worker, cross-replica lease or long-form/video-series\n"
        + "  renderer.\n\n"
        + "This does not change the Bot authority for Telegram identity, Bot jobs,\n"
        + "provider state, Xu/wallet or PayOS. See\n"
        + "[`VIDEO_POSTER_OPERATION_CONTRACT.md`](VIDEO_POSTER_OPERATION_CONTRACT.md).\n",
    )
    # Stable, task-specified document names.  The lower-case documents above
    # are convenient working views; these are the deliverable entry points.
    write(
        "BOT_TO_WEB_INVENTORY.md",
        "# Bot-to-Web inventory\n\n"
        + _markdown_table(
            ["Area", "Bot", "Web App"],
            [
                ["Commands", str(bot["counts"]["commands"]), "Mapped through feature/route registry"],
                ["Callback dispatcher registrations", str(bot["counts"]["callback_handlers"]), "Source provenance only; not a feature/action mapping"],
                ["Concrete callback values", str(bot["counts"]["callback_data"]), "Mapped, guarded, actionable backlog or TELEGRAM_ONLY"],
                ["Conversations", str(bot["counts"]["conversations"]), "Draft/estimate/confirm contract"],
                ["FastAPI routes", str(bot["counts"]["routes"]), str(web["counts"]["routes"])],
                ["DB tables", str(bot["counts"]["database_tables"]), str(web["counts"]["database_tables"])],
            ],
        )
        + "\n\nCanonical business state remains in the bot; this inventory never imports runtime code.\n",
    )
    write(
        "FEATURE_PARITY_MATRIX.md",
        "# Feature parity matrix\n\n"
        f"Observed-runtime static Web-surface coverage: **{gap['static_web_surface_coverage_percent']}%**. Observed-runtime typed source-disposition coverage: **{gap['mapping_coverage_percent']}%**. Runtime workflow-equivalence verification: **{gap['workflow_equivalence']['coverage_percent']}%** (`{gap['workflow_equivalence']['status']}`). Product-action denominator: `{int(metric_scope.get('product_action_denominator') or 0)}`. **Comparability: `{coverage_comparability.get('status') or 'NOT_AUDITED'}` — the denominator correction is not feature progress.** This is an actionable migration baseline, not a LIVE or engine-success claim.\n\n"
        + _markdown_table(["Source type", "Bot entry", "Web target", "Status"], parity_rows)
        + "\n\nAudit statuses: `MAPPED_TO_EXISTING_ROUTE`, `COPIED_GUARDED`, `NAVIGATION_ENTRYPOINT`, `NAVIGATION_ONLY`, `NEEDS_FEATURE_DISPOSITION`, `NEEDS_WEB_IMPLEMENTATION`, `TELEGRAM_ONLY`, `TELEGRAM_TRANSPORT_HANDLER`, `UNREFERENCED_BY_OBSERVED_ENTRYPOINT`. Handler registrations are documented in `CALLBACK_HANDLER_DISPATCH_MAP.md`, and legacy unreferenced-module evidence in `UNREFERENCED_STATIC_MODULES.md`; neither is a browser action. A static route is not a runtime workflow-equivalence claim.\n",
    )
    write(
        "TELEGRAM_TO_WEB_ROUTE_MAP.md",
        "# Telegram command and callback to Web route map\n\n"
        + _markdown_table(["Telegram command", "Web route/action", "Status"], route_rows)
        + "\n\n`TELEGRAM_ONLY` entries stay documented rather than becoming unsafe browser actions.\n",
    )
    write(
        "STATE_AND_DATABASE_MAP.md",
        "# State and database authority map\n\n"
        "| State | Canonical authority | Web role |\n| --- | --- | --- |\n"
        "| Telegram identity / role | Bot | Read via private bridge after account link |\n"
        "| Xu ledger / refunds | Bot | Read-only; no direct credit/debit |\n"
        "| PayOS order / webhook | Bot | Create/status only through canonical bridge when verified |\n"
        "| Jobs / outputs | Bot + workers | Read/status via bridge, signed delivery only |\n"
        "| Web session / CSRF | Web App | Local additive session database only |\n\n"
        + _markdown_table(["Table set", "Count", "Examples"], [["Bot", str(len(bot_tables)), ", ".join(sorted(bot_tables)[:30]) or "None"], ["Web", str(len(web_tables)), ", ".join(sorted(web_tables)[:30]) or "None"]])
        + "\n",
    )
    write(
        "PAYOS_WALLET_JOB_MAP.md",
        "# PayOS, wallet and job safety map\n\n"
        "- One canonical PayOS webhook and wallet writer: Telegram bot.\n"
        "- Web never calculates credit, finalizes redirect, stores a second order ledger, or exposes payment secrets.\n"
        "- Manual top-up stays a Bot handoff: the P0 bridge has no owner-scoped, redacted `pending_deposits` history adapter. Web must not accept bills/TXIDs, create a manual request, approve/reject it or claim a result before canonical wallet history reflects an approved Bot transaction.\n"
        "- Job completion means validated output bytes or a canonical queued task with a polling route; HTTP success alone is insufficient.\n"
        "- Retry/refund/freeze remain guarded until their existing canonical bot action has a tested adapter.\n",
    )
    write(
        "ADMIN_ERP_MAP.md",
        "# Admin ERP map\n\n"
        "## Authority model\n\n"
        "Admin navigation is an ERP information architecture, not a browser-issued permission. "
        "All server write actions require a signed session, CSRF, confirmation, permission check, "
        "idempotency where applicable, optimistic revision where applicable, and an audit event.\n\n"
        + _markdown_table(
            ["Authority domain", "Server authorizes", "May do", "Must not do"],
            [
                ["Canonical Bot admin", "Core Bridge canonical role", "Read canonical users/jobs/payments/providers and request the existing guarded Bot actions.", "Accept a browser `admin_id`, duplicate wallet/PayOS state, call a provider from the browser, or create a second webhook/ledger."],
                ["Web Support Desk", "Signed server-side staff role", "Operate owner-scoped Web support cases, triage and review handoffs.", "Become canonical Bot admin or perform wallet/payment/provider actions without a canonical bridge contract."],
                ["Web CRM manager", "Signed server-side local admin role", "Read redacted, Web-owned Partner & Lead CRM pipeline records.", "Read another account's private content, impersonate a canonical admin, or mutate Bot canonical data."],
            ],
        )
        + "\n\n`WEBAPP_ADMIN_ERP_ENABLED` is the umbrella navigation gate. `WEBAPP_CONTENT_HANDOFF_ENABLED` and "
        "`WEBAPP_PARTNER_CRM_ENABLED` gate their Web-native modules. These flags do not create authority; "
        "the server still checks the signed role on every request.\n\n"
        + "The following is a Bot command compatibility map. A target is a signed guarded Web surface or a "
        "canonical bridge projection; it is never proof that a browser may execute the Bot command directly.\n\n"
        + _markdown_table(["Bot command", "Handler", "Compatibility target"], [[f"/{item['command']}", item["handler"], f"/admin/{item['command']}"] for item in admin_commands[:200]] or [["None discovered", "", ""]]),
    )
    write(
        "ENV_AND_PROVIDER_MAP.md",
        "# Environment and provider map\n\n"
        "Only variable names are inventoried; values, tokens and keys are never read or copied.\n\n"
        + "\n".join(f"- `{record['name']}`" for record in bot["env_references"][:500])
        + "\n\n"
        + _markdown_table(["Provider", "Occurrences", "Sample files"], provider_rows or [["None detected", "", ""]]),
    )
    write(
        "KEY4U_CURRENT_DOCS_MAP.md",
        "# Key4U current documentation map\n\n"
        "Source of documentation: `https://docs.key4u.shop`. This static audit does not call a paid endpoint. Before enabling a capability, compare bot adapter fields against the current official request, submit-id, polling/status, result URL and error schema.\n\n"
        + _markdown_table(["Capability family", "Feature keys to validate"], [[family, keys] for family, keys in key4u_features]),
    )
    write(
        "KNOWN_GAPS_AND_GUARDS.md",
        "# Known gaps and guards\n\n"
        + _markdown_table(["Area", "Severity", "Count", "Finding"], gap_rows)
        + "\n\nA guarded feature remains visible with safe Vietnamese copy and must not call a provider or claim an output.\n\n"
        + "## Additive Web-native guard: Video Poster Lab\n\n"
        + "Video Poster Lab is a Web-owned, bounded private JPEG extraction utility, not\n"
        + "a Telegram command mapping. Its route, schema and read-model integration do\n"
        + "not make it live: it remains disabled until Asset Vault, the Video Operations\n"
        + "and Video Poster flags, an isolated private root, and trusted `ffmpeg` and\n"
        + "`ffprobe` are deliberately available together.\n\n"
        + "The request-time SQLite executor additionally requires an explicit\n"
        + "`WEBAPP_VIDEO_OPERATIONS_TOPOLOGY=sqlite_single_replica` acknowledgement. A\n"
        + "runtime with the feature enabled must attest a replica count of exactly `1`; a\n"
        + "missing, malformed or multi-replica deployment remains blocked.\n\n"
        + "The present executor is request-time only. It has no durable queue, retry\n"
        + "daemon, cross-replica coordination, long-form/video-series renderer or\n"
        + "provider/Bot fallback. On a missing runtime or interrupted attempt it must\n"
        + "fail closed instead of claiming an output. It does not change Bot authority\n"
        + "for Telegram identity, Bot jobs, provider state, Xu/wallet or PayOS. See\n"
        + "[`VIDEO_POSTER_OPERATION_CONTRACT.md`](VIDEO_POSTER_OPERATION_CONTRACT.md).\n",
    )
    return generated


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_sanitize(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git_read(root: Path, *args: str) -> tuple[int, str]:
    """Read local Git metadata without touching remotes or source runtime.

    The migration task locks an expected Bot SHA.  A source fingerprint alone
    cannot tell a reviewer whether the audited worktree is that baseline or a
    separate bridge branch.  This helper invokes only local, read-only Git
    revision commands; it never fetches, checks out, changes config, imports
    Python, or starts any application/provider.
    """
    # Do not let `git -C` walk upward into an unrelated parent checkout.  The
    # audited Bot root must itself be a worktree (directory or worktree-file
    # `.git`) before we attach revision metadata to the report.
    if not (root / ".git").exists():
        return 1, ""
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return 1, ""
    return completed.returncode, completed.stdout.strip()


def _git_revision_context(root: Path, baseline_sha: str) -> dict[str, Any]:
    """Return a small, secret-free local revision comparison for preflight."""
    requested = str(baseline_sha or "").strip()
    context: dict[str, Any] = {
        "checkout_sha": "",
        "baseline_relation": "not_a_git_worktree",
        "ahead_commits": None,
        "behind_commits": None,
    }
    head_status, head = _git_read(root, "rev-parse", "--verify", "HEAD")
    if head_status != 0 or not re.fullmatch(r"[0-9a-f]{40}", head):
        return context
    context["checkout_sha"] = head
    if not re.fullmatch(r"[0-9a-f]{7,64}", requested):
        context["baseline_relation"] = "baseline_sha_invalid"
        return context
    baseline_status, baseline = _git_read(root, "rev-parse", "--verify", f"{requested}^{{commit}}")
    if baseline_status != 0 or not re.fullmatch(r"[0-9a-f]{40}", baseline):
        context["baseline_relation"] = "requested_baseline_unavailable"
        return context
    if head == baseline:
        context.update({"baseline_relation": "exact", "ahead_commits": 0, "behind_commits": 0})
        return context
    ahead_status, ahead = _git_read(root, "rev-list", "--count", f"{baseline}..{head}")
    behind_status, behind = _git_read(root, "rev-list", "--count", f"{head}..{baseline}")
    context["ahead_commits"] = int(ahead) if ahead_status == 0 and ahead.isdigit() else None
    context["behind_commits"] = int(behind) if behind_status == 0 and behind.isdigit() else None
    if context["ahead_commits"] is not None and context["behind_commits"] is not None:
        if context["ahead_commits"] > 0 and context["behind_commits"] == 0:
            context["baseline_relation"] = "ahead_of_requested_baseline"
        elif context["ahead_commits"] == 0 and context["behind_commits"] > 0:
            context["baseline_relation"] = "behind_requested_baseline"
        else:
            context["baseline_relation"] = "diverged_from_requested_baseline"
    else:
        context["baseline_relation"] = "comparison_unavailable"
    return context


def _baseline_bridge_source_context(root: Path, baseline_sha: str) -> dict[str, Any]:
    """Report whether the requested Bot baseline contains bridge source.

    This is a local Git object check, not a checkout, merge or runtime import.
    A method/path match against a newer bridge branch must never be mistaken
    for proof that the frozen requested baseline can serve the Web App bridge.
    """

    requested = str(baseline_sha or "").strip()
    context: dict[str, Any] = {"path": CORE_BRIDGE_FILE, "state": "baseline_sha_invalid", "present": None}
    if not re.fullmatch(r"[0-9a-f]{7,64}", requested):
        return context
    revision_status, _revision = _git_read(root, "rev-parse", "--verify", f"{requested}^{{commit}}")
    if revision_status != 0:
        context.update({"state": "baseline_unavailable", "present": None})
        return context
    file_status, _ = _git_read(root, "cat-file", "-e", f"{requested}:{CORE_BRIDGE_FILE}")
    context.update({"state": "present" if file_status == 0 else "missing", "present": file_status == 0})
    return context


def run_audit(bot_root: Path, web_root: Path, bot_baseline_sha: str, report_dir: Path, docs_dir: Path) -> dict[str, Any]:
    """Run the static audit and write reports/docs.  Safe to call from tests."""

    bot_root = bot_root.resolve()
    web_root = web_root.resolve()
    if not bot_root.is_dir():
        raise ValueError(f"Bot root does not exist: {bot_root}")
    if not web_root.is_dir():
        raise ValueError(f"Web root does not exist: {web_root}")
    bot_entrypoint = bot_root / "bot.py"
    preflight = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "audit_mode": "static-only",
        "guarantees": [
            "No bot, web app, provider, database, payment service, environment file, or webhook is imported or executed.",
            "Only source text, Python AST, and local read-only Git revision metadata are read.",
            "Report/document text is sanitized for secret-shaped literals.",
        ],
        "bot": {
            "root": str(bot_root),
            "entrypoint_present": bot_entrypoint.is_file(),
            "baseline_sha_requested": bot_baseline_sha,
            "revision": _git_revision_context(bot_root, bot_baseline_sha),
            "baseline_bridge_source": _baseline_bridge_source_context(bot_root, bot_baseline_sha),
        },
        "webapp": {"root": str(web_root), "entrypoint_present": (web_root / "app.py").is_file()},
    }
    bot = _summarize_inventory("telegram_bot", bot_root)
    web = _summarize_inventory("webapp", web_root)
    gap = _build_parity_gap(bot, web, bot_root, web_root)
    report_dir = report_dir.resolve()
    docs_dir = docs_dir.resolve()
    _write_json(report_dir / "preflight.json", preflight)
    _write_json(report_dir / "bot_inventory.json", bot)
    _write_json(report_dir / "web_inventory.json", web)
    _write_json(report_dir / "parity_gap.json", gap)
    generated_docs = _render_docs(docs_dir, preflight, bot, web, gap)
    return {
        "preflight": preflight,
        "bot_inventory": bot,
        "web_inventory": web,
        "parity_gap": gap,
        "report_paths": [str(report_dir / name) for name in ("preflight.json", "bot_inventory.json", "web_inventory.json", "parity_gap.json")],
        "doc_paths": [str(path) for path in generated_docs],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Static-only TOAN AAS Telegram bot to Web App inventory")
    parser.add_argument("--bot-root", required=True, type=Path, help="Telegram bot source root; read-only")
    parser.add_argument("--web-root", required=True, type=Path, help="Web App source root; read-only")
    parser.add_argument("--bot-baseline-sha", required=True, help="Already verified bot baseline SHA to record")
    parser.add_argument("--report-dir", type=Path, default=Path("reports/migration"), help="JSON report output directory")
    parser.add_argument("--docs-dir", type=Path, default=Path("docs/migration"), help="Markdown output directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = run_audit(args.bot_root, args.web_root, args.bot_baseline_sha, args.report_dir, args.docs_dir)
    except (OSError, ValueError) as exc:
        print(f"audit failed: {_redact_text(str(exc))}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "ok": True,
                "reports": result["report_paths"],
                "docs": result["doc_paths"],
                "bot_commands": result["bot_inventory"]["counts"]["commands"],
                "web_routes": result["web_inventory"]["counts"]["routes"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
