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
from bisect import bisect_right
from contextlib import contextmanager
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SCHEMA_VERSION = "1.7"
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
# The locked Bot baseline is materialized only into a temporary static source
# snapshot. Keep its archive bounded so a malformed local Git object cannot
# turn a read-only audit into unbounded disk/memory work.
MAX_BASELINE_ARCHIVE_BYTES = 64 * 1024 * 1024
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
    # The frozen Bot's menu dispatcher treats the complete ``tax_`` family
    # as admin-only before it reaches any estimate, profile or export branch.
    # This is an audit classification signal only; it must never grant a Web
    # route or turn an unknown tax action into a resolved feature.
    "tax_",
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
    "pdf_to_images": "/documents/pdf-to-images",
    "ocr_image": "/documents/ocr",
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

# The signed Web interface preference is deliberately closed to these three
# reviewed catalogs.  Bot language callbacks can set Bot-owned user/menu
# state, so only the finite values below may open the fresh Web Account
# settings surface.  They never apply a locale automatically or transfer Bot
# language/menu state into the browser.
INTERFACE_LOCALE_FRESH_WEB_NAVIGATION_COMMANDS = frozenset({"lang", "language"})
INTERFACE_LOCALE_FRESH_WEB_NAVIGATION_ACTIONS = frozenset({"lang|vi", "lang|en", "lang|zh"})
INTERFACE_LOCALE_SOURCE_REVIEW_ACTIONS = frozenset(
    {"lang|ar", "lang|ja", "lang|ko", "lang|th", "lang_more", "back_lang"}
)
INTERFACE_LOCALE_FRESH_WEB_NAVIGATION_DISPOSITIONS = (
    "FRESH_SIGNED_WEB_INTERFACE_LOCALE_NAVIGATION",
    "BOT_INTERFACE_LOCALE_STATE_NOT_REPLAYED",
    "EXPLICIT_WEB_PROFILE_SAVE_REQUIRED",
    "NO_RUNTIME_CLAIM",
)

# These finite customer commands can open a **fresh**, signed Web Document
# Operations surface.  They intentionally do not turn a Bot command into a
# browser execution request: the Web must obtain its own owner-scoped Asset
# Vault source, validate input, require CSRF/idempotency for writes and verify
# any private delivery independently.  Keep this catalog separate from the
# generic route overrides so a convenient-looking route cannot silently claim
# that the Bot pending file, page range, compression profile, confirmation,
# charge or delivery state was transferred.
DOCUMENT_FRESH_WEB_NAVIGATION_COMMANDS: dict[str, dict[str, str]] = {
    "doc_tools": {
        "target": "/documents",
        "capability_key": "documents",
        "feature_key": "documents",
        "surface": "document_directory",
    },
    "pdf_to_word": {
        "target": "/documents/pdf-to-word",
        "capability_key": "documents_pdf_to_word",
        "feature_key": "documents_pdf_to_word",
        "surface": "pdf_to_word",
    },
    "compress_pdf": {
        "target": "/documents/compress",
        "capability_key": "documents_compress",
        "feature_key": "documents_compress",
        "surface": "pdf_optimize",
    },
    "split_pdf": {
        "target": "/documents/split",
        "capability_key": "documents_split",
        "feature_key": "documents_split",
        "surface": "pdf_split",
    },
    "merge_pdf": {
        "target": "/documents/merge",
        "capability_key": "documents_merge",
        "feature_key": "documents_merge",
        "surface": "pdf_merge",
    },
    "image_to_pdf": {
        "target": "/documents/image-to-pdf",
        "capability_key": "documents_image_to_pdf",
        "feature_key": "documents_image_to_pdf",
        "surface": "image_to_pdf",
    },
    "ocr_pdf": {
        "target": "/documents/pdf-ocr",
        "capability_key": "documents_pdf_ocr",
        "feature_key": "documents_pdf_ocr",
        "surface": "pdf_ocr",
    },
}

DOCUMENT_FRESH_WEB_NAVIGATION_DISPOSITIONS = (
    "FRESH_SIGNED_WEB_DOCUMENT_NAVIGATION",
    "BOT_PENDING_DOCUMENT_STATE_NOT_REPLAYED",
    "BOT_EXECUTION_DELIVERY_NOT_REPLAYED",
    "NO_RUNTIME_CLAIM",
)

# The internal-document Archive callback family is admin-only and carries Bot
# department/type selections, pending upload/edit state and Telegram delivery
# controls.  Only these finite, source-reviewed literals may open a fresh
# signed Admin Archive directory.  They never forward the selector, search
# text, file identifier, pending record or mutation into the browser.
ARCHIVE_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS = frozenset(
    {
        "archive|root",
        "archive|help",
        "archive|quick",
        "archive|recent",
        "archive|search",
        "archive|search_dept",
        "archive|types",
        "archive|dept|tax_invoice",
        "archive|type|general",
    }
)
ARCHIVE_SOURCE_REVIEW_ACTIONS = frozenset(
    {
        "archive|back_department",
        "archive|change_dept",
        "archive|discard_to_dept",
        "archive|edit",
    }
)
ARCHIVE_TELEGRAM_ONLY_ACTIONS = frozenset({"archive|preview", "archive|save"})

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
    ("opmenu|", "/admin", "admin"),
)

# Frozen baseline b29d0d4: the Bot Quick Image conversation has a useful
# non-executing draft grammar (catalog/custom brief, deterministic rewrite,
# text-only logo direction and ratio) followed by a canonical tier/ShopAI/Xu
# confirmation branch.  Only the finite draft literals below can point at a
# fresh signed Web-native Planner.  No Telegram state, selected topic, raw
# callback, watermark text, provider choice, tier, token, quote, job or wallet
# state crosses that boundary.
QUICK_IMAGE_PLANNER_FRESH_WEB_CALLBACKS = frozenset({
    "create_media|quick_image",
    "create_media|qi_entry",
    "create_media|qi_suggest",
    "create_media|qi_refresh",
    "create_media|qi_pick_1",
    "create_media|qi_pick_2",
    "create_media|qi_pick_3",
    "create_media|qi_custom",
    "create_media|qi_rewrite",
    "create_media|qi_topics",
    "create_media|qi_back_suggestions",
    "create_media|qi_choose_ratio",
    "create_media|qi_logo_choice",
    "create_media|qi_logo_add",
    "create_media|qi_logo_skip",
    "create_media|qi_logo_confirm",
    "create_media|qi_back_prompt",
    "create_media|qi_back_ratio",
})
QUICK_IMAGE_PLANNER_FRESH_WEB_CALLBACK_TEMPLATES = frozenset({
    "create_media|qi_ratio_{*}",
    # This source-only template is derived from a literal ``qi_logo_pos``
    # helper call; it is retained here for direct unit-level review as well.
    "create_media|qi_logo_pos|{*}",
})
QUICK_IMAGE_PLANNER_TELEGRAM_ONLY_CALLBACKS = frozenset({"create_media|qi_back_tier"})
QUICK_IMAGE_PLANNER_TELEGRAM_ONLY_CALLBACK_TEMPLATES = frozenset({
    "create_media|qi_tier_{*}",
    # These opaque confirmation/package tokens are shared canonical Bot
    # checkout transitions.  They must never inherit the generic top-up route.
    "shopai|confirm|{*}",
    "shopai|package|{*}",
})

# The Bot emits only this reviewed Free Hub library category template.  Its
# formatted suffix chooses a Bot-side suggestion set and short-lived Telegram
# pending state; it is not a safe Web query parameter, prompt identifier or
# browser action.  The standalone Web can only open its own fresh signed
# Gallery surface without carrying that value forward.
FREE_HUB_LIBRARY_CATEGORY_CALLBACK_TEMPLATE = "freehub|lib_{*}"

# These are the only literal values emitted by the Bot's internal PayOS alert
# keyboards at the frozen baseline. They are intentionally not a namespace
# route override: the Bot handler is admin-gated and a future value might
# mutate canonical payment, alert, or deployment state. Every value below was
# reviewed against ``handle_payos_alert_callback``; unknown values remain
# unresolved instead of inheriting a convenient-looking Web route.
PAYOS_ALERT_TELEGRAM_ONLY_CALLBACKS: dict[str, dict[str, Any]] = {
    "payosalert|test": {
        "source_dispositions": ("BOT_ADMIN_ONLY", "TELEGRAM_COMMAND_GUIDANCE", "NO_RUNTIME_CLAIM"),
        "source_evidence": "After the Bot's admin guard, this callback only displays masked Bot-command guidance for PayOS diagnostics; it does not perform a provider or payment test.",
    },
    "payosalert|mute": {
        "source_dispositions": ("BOT_ADMIN_ONLY", "BOT_PROCESS_LOCAL_ALERT_STATE", "NO_RUNTIME_CLAIM"),
        "source_evidence": "After the Bot's admin guard, this callback changes only the Bot process-local one-hour PayOS alert mute window. It is not persistent Web notification state.",
    },
    "payosalert|renewed": {
        "source_dispositions": ("BOT_ADMIN_ONLY", "DEPLOYMENT_ENV_GUIDANCE", "NO_RUNTIME_CLAIM"),
        "source_evidence": "After the Bot's admin guard, this callback only tells an operator that the PayOS registration-expiry deployment setting must be changed and redeployed; it does not change an environment value or PayOS state.",
    },
    "payosalert|remind_later": {
        "source_dispositions": ("BOT_ADMIN_ONLY", "TELEGRAM_MESSAGE_DISMISSAL", "NO_RUNTIME_CLAIM"),
        "source_evidence": "After the Bot's admin guard, this callback only replaces the current Telegram expiry-reminder message. It does not persist a customer or Web reminder state.",
    },
}

# The frozen Bot has nine finite package catalog selectors. They only validate
# a package catalog and redraw a Telegram detail/confirmation screen. The raw
# package type/code is not safe Web input: the standalone catalog must load
# its own current data after a signed Web session. The f-string confirmation
# is deliberately separate below because it creates a canonical Bot order and
# PayOS checkout.
PACKAGE_PURCHASE_SELECTOR_CALLBACKS = frozenset({
    "pkgbuy|combo|tiktok_99k",
    "pkgbuy|combo|basic_199k",
    "pkgbuy|combo|standard_299k",
    "pkgbuy|combo|posting_499k",
    "pkgbuy|combo|product_ads_699k",
    "pkgbuy|monthly|starter_monthly",
    "pkgbuy|monthly|creator_monthly",
    "pkgbuy|monthly|shop_monthly",
    "pkgbuy|monthly|pro_monthly",
})
PACKAGE_PURCHASE_CONFIRM_CALLBACK_TEMPLATE = "pkgbuy|confirm|{*}|{*}"

# The observed Bot `job|*` namespace belongs to the admin-only video-job
# workflow.  Stats only reads Bot-owned campaign/video-job rows, while approve
# and cancel write the canonical Bot state machine.  None of these values are
# customer `/jobs` shortcuts or browser mutation inputs.
VIDEO_JOB_STATS_CALLBACK = "job|stats|0"
VIDEO_JOB_MUTATION_CALLBACK_TEMPLATES = frozenset({
    "job|approve|{*}",
    "job|cancel|{*}",
})

# Storage add-ons are distinct from Xu top-ups.  The frozen Bot renders the
# catalog and custom-input prompt in Telegram, then its confirm branch creates
# a canonical storage order/PayOS checkout and grants quota only after the
# canonical settlement path.  A callback can never become a browser amount,
# a wallet top-up, or a second storage ledger.
STORAGE_ADDON_TELEGRAM_ONLY_CALLBACKS: dict[str, dict[str, Any]] = {
    "storage|menu": {
        "source_dispositions": (
            "CANONICAL_BOT_STORAGE_ADDON_CATALOG",
            "TELEGRAM_PAYMENT_CONTEXT",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot storage menu redraws its Telegram storage-add-on catalog. It is the entry to a "
            "canonical Bot purchase flow, not a Web storage catalog, Xu top-up, or browser checkout."
        ),
    },
    "storage|custom": {
        "source_dispositions": (
            "TELEGRAM_IDENTITY_CONTEXT",
            "BOT_PENDING_STORAGE_INPUT",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot custom-storage branch writes a short-lived pending action for the Telegram user and "
            "expects the next Telegram text message. It does not transfer an amount or storage request to Web."
        ),
    },
}
STORAGE_ADDON_CONFIRM_CALLBACK_TEMPLATE = "storage|confirm|{*}"

# The frozen Bot's vfinal namespace is a Telegram-only state machine.  Every
# reviewed literal below reads or writes its per-Telegram-user finalization
# session and several branches can hand off to selected media, TTS/ASR,
# rendering, package selection, wallet and delivery guards.  The standalone
# Web owns a separate signed Video Finishing workflow; a raw Bot callback can
# never become a browser command, source asset, quote, export, or payment.
VIDEO_FINALIZATION_TELEGRAM_ONLY_CALLBACKS = frozenset({
    "vfinal|addon", "vfinal|addon_none", "vfinal|ai_guard", "vfinal|aspect|16x9",
    "vfinal|aspect|1x1", "vfinal|aspect|4x5", "vfinal|aspect|9x16", "vfinal|back",
    "vfinal|combo", "vfinal|combo_asr", "vfinal|combo_input", "vfinal|combo_lang_custom",
    "vfinal|combo_lang|en", "vfinal|combo_lang|vi", "vfinal|combo_lang|zh", "vfinal|combo_script",
    "vfinal|copy_prompt", "vfinal|export_ai", "vfinal|export_local", "vfinal|logo",
    "vfinal|logo_confirm", "vfinal|logo_pos|bottom_center", "vfinal|logo_pos|bottom_left",
    "vfinal|logo_pos|bottom_right", "vfinal|logo_pos|center", "vfinal|logo_pos|center_left",
    "vfinal|logo_pos|center_right", "vfinal|logo_pos|top_center", "vfinal|logo_pos|top_left",
    "vfinal|logo_pos|top_right", "vfinal|main", "vfinal|menu", "vfinal|music",
    "vfinal|music_ai", "vfinal|music_library", "vfinal|music_none", "vfinal|music_sfx",
    "vfinal|music_upload", "vfinal|music_use", "vfinal|my_media", "vfinal|review",
    "vfinal|save", "vfinal|scene_count_screen", "vfinal|scene_count|1", "vfinal|scene_count|10",
    "vfinal|scene_count|20", "vfinal|scene_count|3", "vfinal|scene_count|5", "vfinal|scene_custom",
    "vfinal|skip", "vfinal|strip_addons", "vfinal|subtitle_asr", "vfinal|subtitle_manual",
    "vfinal|subtitle_none", "vfinal|subtitle_script", "vfinal|tier", "vfinal|tier|basic",
    "vfinal|tier|common", "vfinal|translate_lang_custom", "vfinal|translate_lang|en",
    "vfinal|translate_lang|vi", "vfinal|translate_lang|zh", "vfinal|translate_sub",
    "vfinal|upgrade_300", "vfinal|voice", "vfinal|voice_create", "vfinal|voice_default|female",
    "vfinal|voice_default|male", "vfinal|voice_default|neutral", "vfinal|voice_lang|auto",
    "vfinal|voice_lang|en", "vfinal|voice_lang|vi", "vfinal|voice_lang|zh", "vfinal|voice_none",
    "vfinal|voice_preview", "vfinal|voice_vault",
})
VIDEO_FINALIZATION_TELEGRAM_ONLY_CALLBACK_TEMPLATES = frozenset({
    "vfinal|tier|{*}",
})

# The Bot's Memory Center has two sharply different kinds of source action.
# A few buttons merely open a parent/help surface or ask for a new note/search
# input; those may open an independently signed Web Memory Center without
# carrying the Telegram context, note/query text or Bot records.  Record-ID
# callbacks, storage status and purchase actions are deliberately separated
# below because they read or mutate canonical Bot state.
MEMORY_FRESH_WEB_NAVIGATION_ACTIONS: dict[str, dict[str, Any]] = {
    "menu|main_memory": {
        "capability_key": "memory_center",
        "feature_key": "notes",
        "target": "/notes",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
        "source_dispositions": (
            "FRESH_SIGNED_WEB_MEMORY_NAVIGATION",
            "BOT_MEMORY_MENU_CONTEXT_NOT_REPLAYED",
            "BOT_STORAGE_QUOTA_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot callback only renders its Memory/Document parent menu. The Web opens a fresh signed "
            "Memory Center and never receives Bot note rows, reminder rows, storage quota, add-ons, "
            "Telegram identity, pending context or a payment action."
        ),
    },
    "menu|hint_note": {
        "capability_key": "memory_center",
        "feature_key": "notes",
        "target": "/notes",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
        "source_dispositions": (
            "FRESH_SIGNED_WEB_MEMORY_NAVIGATION",
            "BOT_PENDING_NOTE_INPUT_NOT_REPLAYED",
            "BOT_MEMORY_RECORDS_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot note hint can enter a Telegram pending-text flow. The Web starts a blank, owner-scoped "
            "note workflow and never accepts the Bot input, note ID, message or pending state."
        ),
    },
    "menu|hint_search_note": {
        "capability_key": "memory_center",
        "feature_key": "notes",
        "target": "/notes",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
        "source_dispositions": (
            "FRESH_SIGNED_WEB_MEMORY_NAVIGATION",
            "BOT_PENDING_SEARCH_QUERY_NOT_REPLAYED",
            "BOT_MEMORY_RECORDS_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot search hint can wait for a Telegram query. The Web opens its independently authorized "
            "search form and never receives the Bot query, result list, note ID or Telegram state."
        ),
    },
    "freehub|docs": {
        "capability_key": "memory_center",
        "feature_key": "notes",
        "target": "/notes",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
        "source_dispositions": (
            "FRESH_SIGNED_WEB_MEMORY_NAVIGATION",
            "BOT_FREEHUB_CONTEXT_NOT_REPLAYED",
            "BOT_MEMORY_AND_STORAGE_STATE_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot Free Hub action clears its local context then renders the same Memory/Document menu. "
            "The Web starts its own signed Memory Center and does not import the Free Hub or Bot storage state."
        ),
    },
    "freehub|notes": {
        "capability_key": "memory_center",
        "feature_key": "notes",
        "target": "/notes",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
        "source_dispositions": (
            "FRESH_SIGNED_WEB_MEMORY_NAVIGATION",
            "BOT_FREEHUB_CONTEXT_NOT_REPLAYED",
            "BOT_MEMORY_AND_STORAGE_STATE_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot Free Hub action clears its local context then renders the same Memory/Document menu. "
            "The Web starts its own signed Memory Center and does not import the Free Hub or Bot storage state."
        ),
    },
    "menu|hint_remind": {
        "capability_key": "reminder_center",
        "feature_key": "reminders",
        "target": "/reminders",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
        "source_dispositions": (
            "FRESH_SIGNED_WEB_REMINDER_NAVIGATION",
            "BOT_COMMAND_GUIDANCE_NOT_REPLAYED",
            "TELEGRAM_REMINDER_DELIVERY_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot reminder hint only renders command guidance. The Web starts an independent reminder "
            "workspace and does not receive a Bot reminder, Telegram identity or notification-delivery state."
        ),
    },
    "memory|create": {
        "capability_key": "memory_center",
        "feature_key": "notes",
        "target": "/notes",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
        "source_dispositions": (
            "FRESH_SIGNED_WEB_MEMORY_NAVIGATION",
            "BOT_PENDING_NOTE_INPUT_NOT_REPLAYED",
            "BOT_MEMORY_RECORDS_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot action starts a Telegram note-input state. The Web opens a new signed note form and "
            "does not accept any pending Bot text, note ID or message context."
        ),
    },
    "memory|list": {
        "capability_key": "memory_center",
        "feature_key": "notes",
        "target": "/notes",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
        "source_dispositions": (
            "FRESH_SIGNED_WEB_MEMORY_NAVIGATION",
            "BOT_MEMORY_RECORDS_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot list reads its own note rows. The Web opens an independent signed account list and "
            "never reads the Bot table or accepts a Bot note identifier."
        ),
    },
    "memory|search": {
        "capability_key": "memory_center",
        "feature_key": "notes",
        "target": "/notes",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
        "source_dispositions": (
            "FRESH_SIGNED_WEB_MEMORY_NAVIGATION",
            "BOT_PENDING_SEARCH_QUERY_NOT_REPLAYED",
            "BOT_MEMORY_RECORDS_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot action starts a Telegram search-query state. The Web opens an independent signed search "
            "form and never receives the Bot query, result list, note ID or Telegram state."
        ),
    },
    "memory|delete_start": {
        "capability_key": "memory_center",
        "feature_key": "notes",
        "target": "/notes",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
        "source_dispositions": (
            "FRESH_SIGNED_WEB_MEMORY_NAVIGATION",
            "BOT_NOTE_DELETE_SELECTION_NOT_REPLAYED",
            "BOT_MEMORY_RECORDS_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot action starts a Telegram note-delete selection. The Web opens its own archive-oriented "
            "notes surface and cannot receive a Bot record ID, deletion choice or mutation state."
        ),
    },
}

MEMORY_STORAGE_TELEGRAM_ONLY_ACTIONS: dict[str, dict[str, Any]] = {
    "menu|memory_storage_status": {
        "source_dispositions": (
            "TELEGRAM_IDENTITY_CONTEXT",
            "BOT_CANONICAL_MEMORY_STORAGE_QUOTA",
            "BOT_STORAGE_ADDON_ENTITLEMENTS",
            "NO_WEB_STORAGE_STATUS_ADAPTER",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot status surface reads its canonical storage plan, usage and active add-on entitlement. "
            "The Web Memory summary is intentionally separate and has no reviewed storage-status bridge."
        ),
    },
    "menu|memory_storage_addon": {
        "source_dispositions": (
            "TELEGRAM_IDENTITY_CONTEXT",
            "CANONICAL_BOT_STORAGE_ADDON_CATALOG",
            "CANONICAL_BOT_PAYOS_CHECKOUT",
            "CANONICAL_STORAGE_ENTITLEMENT_SETTLEMENT",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot menu enters the canonical storage add-on catalog and payment flow. It must not become "
            "a Web amount, wallet top-up, checkout, storage order, quota grant or second PayOS ledger."
        ),
    },
}

# ``menu|memory_storage_cleanup`` used to remain in this generic gap list. It
# now has the finite, navigation-only Workspace Care disposition below in
# ``SYSTEM_DATA_STEWARDSHIP_FRESH_WEB_NAVIGATION_ACTIONS``. Keep this map for
# any future guidance-only source that needs a dedicated Web contract rather
# than a name-based fallback.
MEMORY_STORAGE_GUIDANCE_ACTIONS: dict[str, dict[str, Any]] = {}

MEMORY_RECORD_TELEGRAM_ONLY_CALLBACK_TEMPLATES = frozenset({
    "memory|view|{*}",
    "memory|delete|{*}",
    "memory|delete_yes|{*}",
})

# The frozen Bot marketing namespace is a short-lived Telegram conversation:
# it contains suggestion indexes, product/kind choices, pending custom text,
# a Bot save/schedule transition and an optional video handoff.  The standalone
# Web now owns a richer Campaign Planner, but a raw Bot action must only ever
# open a **fresh** signed Web workspace.  It never receives the selection,
# brief, KPI, destination, pending context, Bot campaign identifier, save or
# schedule state that the Telegram conversation held.
#
# Keep this finite allow-list separate from the generic menu registry.  The
# browser-safe product catalog exposes only the ``campaign_planner`` concept;
# these raw Bot tokens remain inside the static audit and cannot become a
# browser payload or API parameter.  Caption and video handoffs retain their
# existing dedicated dispositions below instead of being relabelled as a
# Campaign action.
MARKETING_FRESH_WEB_NAVIGATION_ACTIONS: dict[str, dict[str, Any]] = {
    "marketing|start": {
        "source_dispositions": (
            "FRESH_SIGNED_WEB_CAMPAIGN_NAVIGATION",
            "BOT_MARKETING_SUGGESTIONS_NOT_REPLAYED",
            "BOT_MARKETING_PENDING_STATE_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot action starts its marketing conversation and may render short-lived suggestions. "
            "The Web opens a blank account-owned Campaign Planner and never receives Bot suggestions, "
            "Telegram identity, campaign rows or conversation state."
        ),
    },
    "marketing|back_suggestions": {
        "source_dispositions": (
            "FRESH_SIGNED_WEB_CAMPAIGN_NAVIGATION",
            "BOT_MARKETING_SUGGESTIONS_NOT_REPLAYED",
            "BOT_MARKETING_PENDING_STATE_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot action redraws its own suggestion state. The Web opens a fresh Campaign Planner "
            "without importing a suggestion index, selected idea or pending Telegram context."
        ),
    },
    "marketing|refresh": {
        "source_dispositions": (
            "FRESH_SIGNED_WEB_CAMPAIGN_NAVIGATION",
            "BOT_MARKETING_SUGGESTIONS_NOT_REPLAYED",
            "BOT_MARKETING_PENDING_STATE_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot refresh regenerates or redraws its local conversation suggestions. The Web starts "
            "a new signed planner surface and does not regenerate, copy or receive Bot suggestions."
        ),
    },
    "marketing|brief_custom": {
        "source_dispositions": (
            "FRESH_SIGNED_WEB_CAMPAIGN_NAVIGATION",
            "BOT_PENDING_CUSTOM_BRIEF_NOT_REPLAYED",
            "BOT_MARKETING_CONVERSATION_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot action waits for custom Telegram text. The Web opens its independently authorized "
            "brief form; no Bot draft, message, suggestion or conversation state crosses the boundary."
        ),
    },
    "marketing|choice|1": {
        "source_dispositions": (
            "FRESH_SIGNED_WEB_CAMPAIGN_NAVIGATION",
            "BOT_MARKETING_SUGGESTION_CHOICE_NOT_REPLAYED",
            "BOT_MARKETING_CONVERSATION_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "The Bot choice selects a transient suggestion. The Web does not accept that index and opens a blank signed Campaign Planner.",
    },
    "marketing|choice|2": {
        "source_dispositions": (
            "FRESH_SIGNED_WEB_CAMPAIGN_NAVIGATION",
            "BOT_MARKETING_SUGGESTION_CHOICE_NOT_REPLAYED",
            "BOT_MARKETING_CONVERSATION_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "The Bot choice selects a transient suggestion. The Web does not accept that index and opens a blank signed Campaign Planner.",
    },
    "marketing|choice|3": {
        "source_dispositions": (
            "FRESH_SIGNED_WEB_CAMPAIGN_NAVIGATION",
            "BOT_MARKETING_SUGGESTION_CHOICE_NOT_REPLAYED",
            "BOT_MARKETING_CONVERSATION_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "The Bot choice selects a transient suggestion. The Web does not accept that index and opens a blank signed Campaign Planner.",
    },
    "marketing|cskh": {
        "source_dispositions": (
            "FRESH_SIGNED_WEB_CAMPAIGN_NAVIGATION",
            "BOT_MARKETING_CSKH_CONTEXT_NOT_REPLAYED",
            "BOT_MARKETING_CONVERSATION_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "The Web starts a new campaign brief and does not import the Bot customer-care branch, recipient data or conversation state.",
    },
    "marketing|kind_custom": {
        "source_dispositions": (
            "FRESH_SIGNED_WEB_CAMPAIGN_NAVIGATION",
            "BOT_PENDING_MARKETING_KIND_NOT_REPLAYED",
            "BOT_MARKETING_CONVERSATION_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "The Bot waits for a custom kind. The Web opens a blank planner and never receives the Bot text or pending-state selection.",
    },
    "marketing|kind|affiliate": {
        "source_dispositions": (
            "FRESH_SIGNED_WEB_CAMPAIGN_NAVIGATION",
            "BOT_MARKETING_KIND_SELECTION_NOT_REPLAYED",
            "BOT_MARKETING_CONVERSATION_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "The Bot kind selection remains Bot-local. The Web opens a fresh Campaign Planner without preselecting or storing the Telegram choice.",
    },
    "marketing|kind|food": {
        "source_dispositions": (
            "FRESH_SIGNED_WEB_CAMPAIGN_NAVIGATION",
            "BOT_MARKETING_KIND_SELECTION_NOT_REPLAYED",
            "BOT_MARKETING_CONVERSATION_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "The Bot kind selection remains Bot-local. The Web opens a fresh Campaign Planner without preselecting or storing the Telegram choice.",
    },
    "marketing|kind|physical": {
        "source_dispositions": (
            "FRESH_SIGNED_WEB_CAMPAIGN_NAVIGATION",
            "BOT_MARKETING_KIND_SELECTION_NOT_REPLAYED",
            "BOT_MARKETING_CONVERSATION_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "The Bot kind selection remains Bot-local. The Web opens a fresh Campaign Planner without preselecting or storing the Telegram choice.",
    },
    "marketing|kind|realestate": {
        "source_dispositions": (
            "FRESH_SIGNED_WEB_CAMPAIGN_NAVIGATION",
            "BOT_MARKETING_KIND_SELECTION_NOT_REPLAYED",
            "BOT_MARKETING_CONVERSATION_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "The Bot kind selection remains Bot-local. The Web opens a fresh Campaign Planner without preselecting or storing the Telegram choice.",
    },
    "marketing|kind|service": {
        "source_dispositions": (
            "FRESH_SIGNED_WEB_CAMPAIGN_NAVIGATION",
            "BOT_MARKETING_KIND_SELECTION_NOT_REPLAYED",
            "BOT_MARKETING_CONVERSATION_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "The Bot kind selection remains Bot-local. The Web opens a fresh Campaign Planner without preselecting or storing the Telegram choice.",
    },
    "marketing|kpi": {
        "source_dispositions": (
            "FRESH_SIGNED_WEB_CAMPAIGN_NAVIGATION",
            "BOT_MARKETING_KPI_CONTEXT_NOT_REPLAYED",
            "BOT_MARKETING_CONVERSATION_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "The Web starts a new owner-scoped plan and does not import Bot KPI text, thresholds or conversation context.",
    },
    "marketing|save": {
        "source_dispositions": (
            "FRESH_SIGNED_WEB_CAMPAIGN_NAVIGATION",
            "CANONICAL_BOT_CAMPAIGN_SAVE_NOT_REPLAYED",
            "BOT_MARKETING_CONVERSATION_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "A Bot save transition is not replayed. The Web merely opens its own blank Campaign Planner; any Web plan write requires its own signed session, CSRF, idempotency and owner checks.",
    },
    "marketing|schedule": {
        "source_dispositions": (
            "FRESH_SIGNED_WEB_CAMPAIGN_NAVIGATION",
            "CANONICAL_BOT_CAMPAIGN_SCHEDULE_NOT_REPLAYED",
            "BOT_MARKETING_CONVERSATION_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "A Bot schedule transition is not replayed. The Web opens its own planner; its calendar marker is inert and its private Inbox intent has a separate opt-in contract.",
    },
}

# The frozen Bot's Main Guide is an informational, parent-level menu.  Its
# child buttons may enter Bot conversations, pending-media flows or canonical
# billing routes, so only the two finite entries below may start *fresh* Web
# navigation.  This source-only evidence never reaches the browser: the
# product shell receives only the closed capability catalog from
# ``copyfast_registry.py``.
GUIDED_START_FRESH_WEB_NAVIGATION_ACTIONS: dict[str, dict[str, Any]] = {
    "menu|guide_quick_start": {
        "capability_key": "guided_start",
        "feature_key": "feature_catalog",
        "target": "/features",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
        "source_dispositions": (
            "FRESH_SIGNED_WEB_GUIDED_START",
            "BOT_GUIDE_SECTION_CONTEXT_NOT_REPLAYED",
            "BOT_GUIDE_CHILD_CALLBACKS_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot guide renders explanatory text and a second Telegram keyboard. "
            "The Web opens its own signed feature catalog; it receives no guide section, "
            "Telegram identity, child callback, conversation, provider, job, wallet or payment state."
        ),
    },
    "menu|guide_faq": {
        "capability_key": "support",
        "feature_key": "support",
        "target": "/support",
        "authority": "SIGNED_CUSTOMER",
        "launch_mode": "WEB_NAVIGATION",
        "source_dispositions": (
            "FRESH_SIGNED_WEB_SUPPORT_NAVIGATION",
            "BOT_FAQ_REFUND_OR_SUPPORT_CONTEXT_NOT_REPLAYED",
            "NO_RAW_TELEGRAM_ID_BROWSER_INPUT",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot FAQ directs a Telegram user to support with Telegram-specific context. "
            "The Web opens owner-scoped Support Desk from its signed account and cannot replay a "
            "Telegram ID, chat transcript, screenshot, refund request or Bot support state."
        ),
    },
}

# The frozen Bot's System menu only renders administrative guidance and a
# second Telegram keyboard.  These finite entries may start a **fresh** Web
# route that repeats its own signed authority check, but no Bot runtime/data
# state, command, health check, backup operation, path, secret, ledger or
# provider/payment action crosses into the browser.  The separate Workspace
# Care entry is likewise guidance only: it never claims to clean Bot storage.
#
# Keep this registry outside ``MENU_ACTION_REGISTRY``. It contains no public
# customer catalog capability, grants no role and must never be emitted to a
# browser as raw Telegram callback data.
SYSTEM_DATA_STEWARDSHIP_FRESH_WEB_NAVIGATION_ACTIONS: dict[str, dict[str, Any]] = {
    "menu|system": {
        "target": "/admin/system",
        "classification": "admin",
        "feature_key": "admin_system",
        "authority": "SIGNED_CANONICAL_ADMIN_READ",
        "launch_mode": "WEB_NAVIGATION",
        "source_dispositions": (
            "BOT_ADMIN_ONLY",
            "FRESH_SIGNED_WEB_ADMIN_NAVIGATION",
            "BOT_SYSTEM_MENU_CONTEXT_NOT_REPLAYED",
            "BOT_SYSTEM_STATE_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot action redraws its administrative System menu. The Web opens the independently "
            "authorized canonical System read route and never receives a Telegram admin identity, menu, "
            "command, settings record, secret, infrastructure state or write authority."
        ),
    },
    "menu|system_runtime_help": {
        "target": "/admin/runtime",
        "classification": "admin",
        "feature_key": "admin_runtime",
        "authority": "SIGNED_CANONICAL_ADMIN_READ",
        "launch_mode": "WEB_NAVIGATION",
        "source_dispositions": (
            "BOT_ADMIN_ONLY",
            "FRESH_SIGNED_WEB_ADMIN_NAVIGATION",
            "BOT_SYSTEM_HELP_TEXT_NOT_REPLAYED",
            "BOT_RUNTIME_STATE_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot help text is a Telegram guidance branch. The Web starts a separately guarded Runtime "
            "read surface; it does not run a health check, inspect a worker, restart a process or expose Bot state."
        ),
    },
    "menu|system_data_status_help": {
        "target": "/admin/system",
        "classification": "admin",
        "feature_key": "admin_system",
        "authority": "SIGNED_CANONICAL_ADMIN_READ",
        "launch_mode": "WEB_NAVIGATION",
        "source_dispositions": (
            "BOT_ADMIN_ONLY",
            "FRESH_SIGNED_WEB_ADMIN_NAVIGATION",
            "BOT_SYSTEM_HELP_TEXT_NOT_REPLAYED",
            "BOT_DATA_STATUS_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot guidance describes data status without a Web adapter. The Web opens its canonical System "
            "read route only and does not import Bot database, filesystem, ledger or Telegram state."
        ),
    },
    "menu|system_backup_help": {
        "target": "/admin/backups",
        "classification": "admin",
        "feature_key": "admin_backups",
        "authority": "SIGNED_CANONICAL_ADMIN_READ",
        "launch_mode": "WEB_NAVIGATION",
        "source_dispositions": (
            "BOT_ADMIN_ONLY",
            "FRESH_SIGNED_WEB_ADMIN_NAVIGATION",
            "BOT_SYSTEM_HELP_TEXT_NOT_REPLAYED",
            "BOT_BACKUP_STATE_NOT_REPLAYED",
            "NO_BACKUP_OR_RESTORE_ACTION",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot backup help is informational and does not transfer a backup artifact or restore command. "
            "The Web opens the canonical backup metadata view only; it cannot create, delete, restore or download a Bot backup."
        ),
    },
    "menu|system_health_help": {
        "target": "/admin/runtime",
        "classification": "admin",
        "feature_key": "admin_runtime",
        "authority": "SIGNED_CANONICAL_ADMIN_READ",
        "launch_mode": "WEB_NAVIGATION",
        "source_dispositions": (
            "BOT_ADMIN_ONLY",
            "FRESH_SIGNED_WEB_ADMIN_NAVIGATION",
            "BOT_SYSTEM_HELP_TEXT_NOT_REPLAYED",
            "BOT_HEALTHCHECK_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot health help is not an executable health check. The Web opens a separately authorized Runtime "
            "read route and never claims provider, worker, service or deployment health from navigation alone."
        ),
    },
    "menu|internal_archive": {
        "target": "/admin/internal-documents",
        "classification": "admin",
        "feature_key": "admin_internal_documents",
        "authority": "SIGNED_WEB_LOCAL_ADMIN",
        "launch_mode": "WEB_NAVIGATION",
        "source_dispositions": (
            "BOT_ADMIN_ONLY",
            "FRESH_SIGNED_WEB_LOCAL_ADMIN_NAVIGATION",
            "BOT_ARCHIVE_RECORDS_NOT_REPLAYED",
            "BOT_FILE_IDENTIFIERS_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot archive callback is an admin Telegram branch. The Web opens its independently owned local-admin "
            "archive, with no Bot archive row, file identifier, Telegram attachment, retention state or download claim."
        ),
    },
    "menu|memory_storage_cleanup": {
        "target": "/account/workspace-care",
        "classification": "customer",
        "feature_key": "workspace_care",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
        "source_dispositions": (
            "BOT_STORAGE_CLEANUP_GUIDANCE_ONLY",
            "FRESH_SIGNED_WEB_WORKSPACE_CARE_NAVIGATION",
            "BOT_TEMP_FILE_TTL_NOT_REPLAYED",
            "NO_STORAGE_DELETE_OR_QUOTA_CLAIM",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot cleanup action is guidance only and explicitly performs no deletion. The Web opens Workspace Care, "
            "a navigation-only hub for independently owned notes, reminders and Data Controls; it does not clean Bot storage, quota or add-ons."
        ),
    },
}

# The frozen Bot's reviewed tax menu branches render administrative guidance,
# choices and Telegram delivery paths. Only these three explanatory buttons may
# open a fresh, independently authorized Web guidance route. They never
# transfer a callback token, Telegram identity, finance row, profile, period,
# estimate, report, export, file, payment reference, ledger, provider, archive
# or delivery state. Keep this finite registry separate from the generic menu
# map: a ``menu|tax_*`` prefix is not an authority grant.
TAX_ACCOUNTING_GUIDANCE_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS: dict[str, dict[str, Any]] = {
    "menu|finance_tax": {
        "target": "/admin/finance/tax-readiness",
        "classification": "admin",
        "feature_key": "admin_tax_readiness",
        "authority": "SIGNED_CANONICAL_ADMIN_READ",
        "launch_mode": "WEB_NAVIGATION",
        "source_dispositions": (
            "BOT_ADMIN_ONLY",
            "FRESH_SIGNED_WEB_ADMIN_NAVIGATION",
            "BOT_TAX_GUIDANCE_NOT_REPLAYED",
            "NO_CANONICAL_FINANCE_DATA_TRANSFER",
            "NO_TAX_ESTIMATE_OR_FINANCIAL_CALCULATION",
            "NO_REPORT_EXPORT_OR_FILE_DELIVERY",
            "NO_TAX_PROFILE_OR_COMPLIANCE_MUTATION",
            "NO_PAYOS_WALLET_LEDGER_OR_PROVIDER_ACTION",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot action opens its admin tax guidance menu. The Web opens a separately authorized, "
            "literal readiness checklist and receives no Telegram identity, finance data, tax profile, "
            "period, estimate, report, export, file, payment, ledger, provider or mutation authority."
        ),
    },
    "menu|tax_checklist": {
        "target": "/admin/finance/tax-readiness",
        "classification": "admin",
        "feature_key": "admin_tax_readiness",
        "authority": "SIGNED_CANONICAL_ADMIN_READ",
        "launch_mode": "WEB_NAVIGATION",
        "source_dispositions": (
            "BOT_ADMIN_ONLY",
            "FRESH_SIGNED_WEB_ADMIN_NAVIGATION",
            "BOT_TAX_GUIDANCE_NOT_REPLAYED",
            "NO_CANONICAL_FINANCE_DATA_TRANSFER",
            "NO_TAX_ESTIMATE_OR_FINANCIAL_CALCULATION",
            "NO_REPORT_EXPORT_OR_FILE_DELIVERY",
            "NO_TAX_PROFILE_OR_COMPLIANCE_MUTATION",
            "NO_PAYOS_WALLET_LEDGER_OR_PROVIDER_ACTION",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot checklist is Telegram explanatory text. The Web starts fresh static accounting guidance "
            "only and does not receive its message, source selections, financial records or compliance state."
        ),
    },
    "menu|tax_custom_help": {
        "target": "/admin/finance/tax-readiness",
        "classification": "admin",
        "feature_key": "admin_tax_readiness",
        "authority": "SIGNED_CANONICAL_ADMIN_READ",
        "launch_mode": "WEB_NAVIGATION",
        "source_dispositions": (
            "BOT_ADMIN_ONLY",
            "FRESH_SIGNED_WEB_ADMIN_NAVIGATION",
            "BOT_TAX_GUIDANCE_NOT_REPLAYED",
            "NO_CANONICAL_FINANCE_DATA_TRANSFER",
            "NO_TAX_ESTIMATE_OR_FINANCIAL_CALCULATION",
            "NO_REPORT_EXPORT_OR_FILE_DELIVERY",
            "NO_TAX_PROFILE_OR_COMPLIANCE_MUTATION",
            "NO_PAYOS_WALLET_LEDGER_OR_PROVIDER_ACTION",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot custom-period help is explanatory only. The Web does not receive a requested date range, "
            "tax period, report parameter, ledger row or calculation request."
        ),
    },
}

# These exact Bot actions inspect canonical finance data, calculate a period,
# expose historical tax configuration or begin six-file CSV delivery. They are
# intentionally visible in the static parity report as admin work still needing
# a dedicated canonical-finance contract; they are not evidence of a Web export
# or a substitute for Bot-owned data and delivery.
TAX_ACCOUNTING_CANONICAL_FINANCE_SOURCE_REVIEW_BASE_DISPOSITIONS = (
    "BOT_ADMIN_ONLY",
    "CANONICAL_BOT_FINANCE_TAX_STATE",
    "SOURCE_STATE_MACHINE_REQUIRED",
    "NO_CANONICAL_FINANCE_DATA_TRANSFER",
    "NO_TAX_ESTIMATE_OR_FINANCIAL_CALCULATION",
    "NO_REPORT_EXPORT_OR_FILE_DELIVERY",
    "NO_TAX_PROFILE_OR_COMPLIANCE_MUTATION",
    "NO_PAYOS_WALLET_LEDGER_OR_PROVIDER_ACTION",
    "NO_RUNTIME_CLAIM",
)
TAX_ACCOUNTING_CANONICAL_FINANCE_SOURCE_REVIEW_ACTIONS: dict[str, dict[str, str]] = {
    "menu|tax_estimate": {
        "operation_disposition": "CANONICAL_BOT_TAX_ESTIMATE_CALCULATION",
        "source_evidence": "The frozen Bot calculates a tax estimate from canonical finance summary and historical tax-profile state.",
    },
    "menu|tax_estimate_month": {
        "operation_disposition": "CANONICAL_BOT_TAX_ESTIMATE_CALCULATION",
        "source_evidence": "The frozen Bot calculates a current-month tax estimate from canonical finance and tax-profile state.",
    },
    "menu|tax_estimate_previous": {
        "operation_disposition": "CANONICAL_BOT_TAX_ESTIMATE_CALCULATION",
        "source_evidence": "The frozen Bot calculates a previous-month tax estimate from canonical finance and tax-profile state.",
    },
    "menu|tax_estimate_quarter": {
        "operation_disposition": "CANONICAL_BOT_TAX_ESTIMATE_CALCULATION",
        "source_evidence": "The frozen Bot calculates a quarterly tax estimate from canonical finance and tax-profile state.",
    },
    "menu|tax_export": {
        "operation_disposition": "CANONICAL_BOT_CSV_EXPORT_MENU",
        "source_evidence": "The frozen Bot opens the period selector for its canonical six-file CSV delivery flow.",
    },
    "menu|tax_export_month": {
        "operation_disposition": "CANONICAL_BOT_CSV_EXPORT_DELIVERY",
        "source_evidence": "The frozen Bot resolves the current period and sends six canonical CSV accounting files.",
    },
    "menu|tax_export_previous": {
        "operation_disposition": "CANONICAL_BOT_CSV_EXPORT_DELIVERY",
        "source_evidence": "The frozen Bot resolves the previous period and sends six canonical CSV accounting files.",
    },
    "menu|tax_export_quarter": {
        "operation_disposition": "CANONICAL_BOT_CSV_EXPORT_DELIVERY",
        "source_evidence": "The frozen Bot resolves the quarterly period and sends six canonical CSV accounting files.",
    },
    "menu|tax_export_custom_help": {
        "operation_disposition": "CANONICAL_BOT_EXPORT_PERIOD_INPUT_GUIDANCE",
        "source_evidence": "The frozen Bot emits custom-period instructions for the export flow and returns its export keyboard; the Web must not accept or replay that date input.",
    },
    "menu|tax_config": {
        "operation_disposition": "CANONICAL_BOT_TAX_PROFILE_STATE",
        "source_evidence": "The frozen Bot reads its historical tax-profile/configuration state.",
    },
}


def _tax_accounting_source_review_dispositions(action: dict[str, str]) -> tuple[str, ...]:
    """Preserve the action-specific Bot finance boundary in static audit output."""

    return (
        TAX_ACCOUNTING_CANONICAL_FINANCE_SOURCE_REVIEW_BASE_DISPOSITIONS[:2]
        + (str(action["operation_disposition"]),)
        + TAX_ACCOUNTING_CANONICAL_FINANCE_SOURCE_REVIEW_BASE_DISPOSITIONS[2:]
    )

# These main-guide entries lead to video/trend child menus with Bot-local
# pending state, output/provider guards and canonical purchase branches. The
# user requested that the Video menu be handled last, so they remain explicit
# source-review backlog records rather than silently falling back to Dashboard.
GUIDED_VIDEO_MENU_DEFERRED_ACTIONS = frozenset({
    "menu|guide_video_ai",
    "menu|guide_guided_video",
})

# The frozen Bot's stale-job help is an admin-only explanatory branch. It can
# lead toward canonical job-lock/refund confirmation state, but only this one
# literal help action may open a fresh, separately guarded Web safety guide.
# No Bot user/job identifier, queue row, lock state, confirmation, runtime,
# billing event, wallet/PayOS state or mutation crosses into the browser.
# Keep this independent from generic ``menu|*`` and ``admin_confirm_*`` maps:
# names are never a Web authority grant.
JOB_LOCK_RECOVERY_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS: dict[str, dict[str, Any]] = {
    "menu|clear_stale_jobs_help": {
        "target": "/admin/job-recovery-guide",
        "classification": "admin",
        "feature_key": "admin_job_recovery_guide",
        "authority": "SIGNED_CANONICAL_ADMIN_READ",
        "launch_mode": "WEB_NAVIGATION",
        "source_dispositions": (
            "BOT_ADMIN_ONLY",
            "FRESH_SIGNED_WEB_ADMIN_NAVIGATION",
            "BOT_JOB_LOCK_HELP_NOT_REPLAYED",
            "BOT_JOB_LOCK_STATE_NOT_REPLAYED",
            "NO_BOT_JOB_OR_USER_IDENTIFIER_TRANSFER",
            "NO_JOB_CLEAR_RETRY_REFUND_OR_CHARGE_ACTION",
            "NO_PROVIDER_WORKER_RUNTIME_CONTROL",
            "NO_PAYOS_WALLET_LEDGER_ACTION",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The Bot action only renders its admin stale-job recovery help. The Web opens a separately authorized, "
            "literal safety guide and receives no Telegram admin identity, job/user identifier, queue/lock state, "
            "confirmation context, worker/provider/runtime data, refund/billing state or mutation authority."
        ),
    },
}

# These adjacent Bot callbacks and commands are canonical mutation boundaries,
# not an extension of the help page. They can lead to job status changes,
# delivery/billing effects or a refund decision. Keep them source-review-only
# in the parity report so they cannot fall through to `/admin/callbacks` or a
# convenient-looking Web route.
JOB_LOCK_RECOVERY_CANONICAL_SOURCE_REVIEW_BASE_DISPOSITIONS = (
    "BOT_ADMIN_ONLY",
    "CANONICAL_BOT_JOB_LOCK_RECOVERY_STATE",
    "SOURCE_STATE_MACHINE_REQUIRED",
    "TELEGRAM_CONFIRMATION_CONTEXT_REQUIRED",
    "NO_BOT_JOB_OR_USER_IDENTIFIER_TRANSFER",
    "NO_JOB_CLEAR_RETRY_REFUND_OR_CHARGE_ACTION",
    "NO_PROVIDER_WORKER_RUNTIME_CONTROL",
    "NO_PAYOS_WALLET_LEDGER_ACTION",
    "NO_RUNTIME_CLAIM",
)
JOB_LOCK_RECOVERY_CANONICAL_SOURCE_REVIEW_ACTIONS: dict[str, dict[str, str]] = {
    "menu|admin_confirm_clear_stale_jobs": {
        "operation_disposition": "CANONICAL_BOT_JOB_LOCK_CLEAR_CONFIRMATION",
        "source_evidence": "The frozen Bot renders a confirmation boundary for a canonical job-lock-clear operation; it is not a browser confirmation or Web job action.",
    },
    "menu|admin_confirm_ack_clear_stale_jobs": {
        "operation_disposition": "CANONICAL_BOT_JOB_LOCK_CLEAR_ACKNOWLEDGEMENT",
        "source_evidence": "The frozen Bot acknowledgement remains inside Telegram admin confirmation context and must not become a Web action or command copy surface.",
    },
    "menu|admin_confirm_refund_job": {
        "operation_disposition": "CANONICAL_BOT_JOB_REFUND_CONFIRMATION",
        "source_evidence": "The frozen Bot confirmation can lead to a canonical job refund decision; the Web must not accept a Bot job identifier or request a refund.",
    },
    "menu|admin_confirm_ack_refund_job": {
        "operation_disposition": "CANONICAL_BOT_JOB_REFUND_ACKNOWLEDGEMENT",
        "source_evidence": "The frozen Bot acknowledgement remains an admin Telegram state transition and cannot become a browser-side financial action.",
    },
}
JOB_LOCK_RECOVERY_CANONICAL_SOURCE_REVIEW_COMMANDS: dict[str, dict[str, str]] = {
    "clear_job_lock": {
        "operation_disposition": "CANONICAL_BOT_JOB_LOCK_CLEAR_MUTATION",
        "source_evidence": "The frozen Bot command can change eligible active video-job state and may trigger canonical refund/billing effects; it is not a Web recovery API.",
    },
    "refund_job": {
        "operation_disposition": "CANONICAL_BOT_JOB_REFUND_MUTATION",
        "source_evidence": "The frozen Bot command is a canonical refund mutation and must not become a Web refund endpoint, job form or browser-side ledger action.",
    },
}


def _job_lock_recovery_source_review_dispositions(action: dict[str, str]) -> tuple[str, ...]:
    """Keep the concrete Bot job/recovery mutation boundary visible in audit output."""

    return (
        JOB_LOCK_RECOVERY_CANONICAL_SOURCE_REVIEW_BASE_DISPOSITIONS[:2]
        + (str(action["operation_disposition"]),)
        + JOB_LOCK_RECOVERY_CANONICAL_SOURCE_REVIEW_BASE_DISPOSITIONS[2:]
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
    "menu|main_ai": {
        "capability_key": "chat_workspace",
        "target": "/chat",
        "feature_key": "chat",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|hint_ai_prompt": {
        "capability_key": "prompt_studio",
        "target": "/prompt-studio",
        "feature_key": "prompt_studio",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|hint_campaign_preset": {
        "capability_key": "campaign_planner",
        "target": "/campaigns",
        "feature_key": "campaign_planner",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|main_profile": {
        "capability_key": "account",
        "target": "/account",
        "feature_key": "account",
        "authority": "SIGNED_CUSTOMER",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|main_memory": {
        "capability_key": "memory_center",
        "target": "/notes",
        "feature_key": "notes",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|hint_note": {
        "capability_key": "memory_center",
        "target": "/notes",
        "feature_key": "notes",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|hint_search_note": {
        "capability_key": "memory_center",
        "target": "/notes",
        "feature_key": "notes",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|hint_remind": {
        "capability_key": "reminder_center",
        "target": "/reminders",
        "feature_key": "reminders",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "freehub|docs": {
        "capability_key": "memory_center",
        "target": "/notes",
        "feature_key": "notes",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "freehub|notes": {
        "capability_key": "memory_center",
        "target": "/notes",
        "feature_key": "notes",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|translate": {
        "capability_key": "subtitle_studio",
        "target": "/subtitle-studio",
        "feature_key": "subtitle_studio",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|translation_language_hub": {
        "capability_key": "subtitle_studio",
        "target": "/subtitle-studio",
        "feature_key": "subtitle_studio",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|translation_text": {
        "capability_key": "subtitle_studio",
        "target": "/subtitle-studio",
        "feature_key": "subtitle_studio",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|translation_transcript": {
        "capability_key": "subtitle_studio",
        "target": "/subtitle-studio",
        "feature_key": "subtitle_studio",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|translation_document": {
        "capability_key": "documents",
        "target": "/documents",
        "feature_key": "documents",
        "authority": "SIGNED_CUSTOMER",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|profile_packages": {
        "capability_key": "membership",
        "target": "/membership",
        "feature_key": "membership",
        "authority": "CORE_CANONICAL_READ",
        "launch_mode": "READ_ONLY_CANONICAL",
    },
    "menu|main_topup": {
        "capability_key": "wallet_topup",
        "target": "/wallet/topup",
        "feature_key": "wallet_topup",
        "authority": "CORE_CANONICAL_PAYMENT",
        "launch_mode": "BRIDGE_GUARDED_PROXY",
    },
    "menu|guide_credits": {
        "capability_key": "wallet",
        "target": "/wallet",
        "feature_key": "wallet",
        "authority": "CORE_CANONICAL_READ",
        "launch_mode": "READ_ONLY_CANONICAL",
    },
    "menu|hint_pricing": {
        "capability_key": "pricing",
        "target": "/pricing",
        "feature_key": "pricing",
        "authority": "SIGNED_CUSTOMER",
        "launch_mode": "WEB_NAVIGATION",
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
    "menu|hint_doc_pdf_to_word": {
        "capability_key": "documents_pdf_to_word",
        "target": "/documents/pdf-to-word",
        "feature_key": "documents_pdf_to_word",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|hint_doc_image_to_pdf": {
        "capability_key": "documents_image_to_pdf",
        "target": "/documents/image-to-pdf",
        "feature_key": "documents_image_to_pdf",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|hint_doc_compress_pdf": {
        "capability_key": "documents_compress",
        "target": "/documents/compress",
        "feature_key": "documents_compress",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|hint_doc_split_pdf": {
        "capability_key": "documents_split",
        "target": "/documents/split",
        "feature_key": "documents_split",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|hint_doc_merge_pdf": {
        "capability_key": "documents_merge",
        "target": "/documents/merge",
        "feature_key": "documents_merge",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|hint_doc_save_document": {
        "capability_key": "asset_vault",
        "target": "/asset-vault",
        "feature_key": "asset_vault",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|main_image": {
        "capability_key": "image_studio",
        "target": "/image-studio",
        "feature_key": "image_studio",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|hint_image_tools": {
        "capability_key": "image_studio",
        "target": "/image-studio",
        "feature_key": "image_studio",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|image_prompt_start": {
        "capability_key": "image_prompt_composer",
        "target": "/image/prompt-composer",
        "feature_key": "image_prompt_composer",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|image_edit_start": {
        "capability_key": "image_edit",
        "target": "/image/edit",
        "feature_key": "image_edit",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|image_upscale_start": {
        "capability_key": "image_upscale",
        "target": "/image/upscale",
        "feature_key": "image_upscale",
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
    "menu|guide_quick_start": {
        "capability_key": "guided_start",
        "target": "/features",
        "feature_key": "feature_catalog",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|guide_image_ai": {
        "capability_key": "image_studio",
        "target": "/image-studio",
        "feature_key": "image_studio",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|guide_music_add": {
        "capability_key": "media_workspace",
        "target": "/media-workspace",
        "feature_key": "media_workspace",
        "authority": "SIGNED_CUSTOMER_WEB_NATIVE",
        "launch_mode": "WEB_NAVIGATION",
    },
    "menu|guide_faq": {
        "capability_key": "support",
        "target": "/support",
        "feature_key": "support",
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

# Exact pricing panels that merely render an informational/catalog summary in
# the Bot may open a fresh Web read surface.  This remains separate from
# ``MENU_ACTION_REGISTRY`` because it is a pricing namespace, not a general
# customer menu.  The Web never accepts a Bot package selector or purchase
# confirmation: canonical adapter/flag checks still govern each page.
PRICING_READ_NAVIGATION_REGISTRY: dict[str, dict[str, str]] = {
    "pricing|main": {
        "capability_key": "pricing",
        "target": "/pricing",
        "feature_key": "pricing",
        "authority": "SIGNED_CUSTOMER",
        "launch_mode": "WEB_NAVIGATION",
    },
    "pricing|catalog": {
        "capability_key": "pricing",
        "target": "/pricing",
        "feature_key": "pricing",
        "authority": "SIGNED_CUSTOMER",
        "launch_mode": "WEB_NAVIGATION",
    },
    "pricing|xu": {
        "capability_key": "wallet",
        "target": "/wallet",
        "feature_key": "wallet",
        "authority": "CORE_CANONICAL_READ",
        "launch_mode": "READ_ONLY_CANONICAL",
    },
    "pricing|packages": {
        "capability_key": "packages",
        "target": "/packages",
        "feature_key": "packages",
        "authority": "CORE_CANONICAL_READ",
        "launch_mode": "READ_ONLY_CANONICAL",
    },
    "pricing|package_summary": {
        "capability_key": "packages",
        "target": "/packages",
        "feature_key": "packages",
        "authority": "CORE_CANONICAL_READ",
        "launch_mode": "READ_ONLY_CANONICAL",
    },
    "pricing|my_packages": {
        "capability_key": "membership",
        "target": "/membership",
        "feature_key": "membership",
        "authority": "CORE_CANONICAL_READ",
        "launch_mode": "READ_ONLY_CANONICAL",
    },
    "pricing|plans": {
        "capability_key": "membership",
        "target": "/membership",
        "feature_key": "membership",
        "authority": "CORE_CANONICAL_READ",
        "launch_mode": "READ_ONLY_CANONICAL",
    },
    "pricing|vip": {
        "capability_key": "membership",
        "target": "/membership",
        "feature_key": "membership",
        "authority": "CORE_CANONICAL_READ",
        "launch_mode": "READ_ONLY_CANONICAL",
    },
    "pricing|member": {
        "capability_key": "membership",
        "target": "/membership",
        "feature_key": "membership",
        "authority": "CORE_CANONICAL_READ",
        "launch_mode": "READ_ONLY_CANONICAL",
    },
}

# The profile referral buttons are not merely static help.  Bot derives a
# Telegram deep link from the bot username and reads referral/reward state
# that can affect canonical Xu rewards.  The standalone Web currently has no
# reviewed internal referral read contract, so these exact actions must not
# inherit a route, generate a link, or show synthetic statistics.
PROFILE_REFERRAL_TELEGRAM_ONLY_ACTIONS = frozenset({
    "menu|profile_ref_link",
    "menu|profile_ref_policy",
    "menu|profile_ref_stats",
})

# Translation session callbacks mutate Bot-local pending state, a Telegram
# user preference, or a provider-gated voice/audio path.  The Web Subtitle
# Studio is an independently owned authoring workspace; it must never import
# these session values or claim it can translate, transcribe, synthesize
# speech, or retain the Bot's auto-translation mode.
MENU_TRANSLATION_TELEGRAM_ONLY_ACTIONS = frozenset({
    "menu|translate_more",
    "menu|translate_off",
    "menu|translate_set_ar",
    "menu|translate_set_en",
    "menu|translate_set_ja",
    "menu|translate_set_ko",
    "menu|translate_set_th",
    "menu|translate_set_vi",
    "menu|translate_set_zh",
    "menu|translation_auto_target",
    "menu|translation_language",
    "menu|translation_live_conversation",
    "menu|translation_output_voice",
    "menu|translation_stop_session",
    "menu|translation_swap_languages",
    "menu|translation_text_target_custom",
    "menu|translation_text_target_en",
    "menu|translation_text_target_ja",
    "menu|translation_text_target_ko",
    "menu|translation_text_target_th",
    "menu|translation_text_target_vi",
    "menu|translation_text_target_zh",
    "menu|translation_two_way",
    "menu|translation_voice",
})

TRANSLATION_SESSION_TELEGRAM_ONLY_CALLBACK_TEMPLATES = frozenset({
    "menu|translation_pair_back_{*}",
    "menu|translation_pair_start_{*}",
    "menu|translation_pair_swap_{*}",
})

# Video dubbing starts from a Telegram pending video and can later select
# voice/provider/output actions. The user requested Video menus be handled
# last, so this one entry remains deliberately actionable rather than falling
# through to the dashboard or pretending the generic /dubbing route is safe.
TRANSLATION_VIDEO_MENU_DEFERRED_ACTIONS = frozenset({"menu|translation_video_factory"})

# The Bot's ``/operator_menu`` handler is not an execution dispatcher.  Its
# buttons render command snippets for one Telegram admin, and many snippets
# include a later write, provider call, worker run, PayOS lookup or video
# production step.  Only these *top-level, non-production category* buttons
# can therefore open a fresh, independently authorized Admin ERP directory.
#
# Keep this registry separate from ``MENU_ACTION_REGISTRY``: it is not a
# customer capability and must never be emitted by the browser-safe public
# catalog.  The target Admin route still requires the signed server session
# plus the current canonical role; this audit mapping grants neither.
OPERATOR_MENU_CATEGORY_REGISTRY: dict[str, dict[str, str]] = {
    "opmenu|cat_control": {
        "target": "/admin",
        "admin_feature_key": "admin_overview",
        "title": "Điều hành",
    },
    "opmenu|cat_trend": {
        "target": "/admin/trends",
        "admin_feature_key": "admin_trends",
        "title": "Trend",
    },
    "opmenu|cat_affiliate": {
        "target": "/admin/growth",
        "admin_feature_key": "admin_growth",
        "title": "Affiliate",
    },
    "opmenu|cat_schedule": {
        "target": "/admin/calendar",
        "admin_feature_key": "admin_calendar",
        "title": "Kênh & lịch",
    },
    "opmenu|cat_publish": {
        "target": "/admin/publishing",
        "admin_feature_key": "admin_publishing",
        "title": "Đăng bài",
    },
    "opmenu|cat_money": {
        "target": "/admin/finance",
        "admin_feature_key": "admin_finance",
        "title": "Doanh thu",
    },
    "opmenu|cat_api": {
        "target": "/admin/runtime",
        "admin_feature_key": "admin_runtime",
        "title": "API/Auto",
    },
    "opmenu|cat_internal": {
        "target": "/admin/audit",
        "admin_feature_key": "admin_audit",
        "title": "Nội bộ",
    },
    "opmenu|dashboard": {
        "target": "/admin",
        "admin_feature_key": "admin_overview",
        "title": "Dashboard",
    },
}

# Production contains the Bot's ``makevideo``, film, worker, render, output
# and review snippets.  The user explicitly asked for the Video menu last, so
# even the category button remains a visible source-review disposition here.
OPERATOR_MENU_DEFERRED_CATEGORIES = frozenset({"opmenu|cat_production"})

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
        "candidate_boundary": "separate signed Web Video Finishing state and owner-scoped Asset Vault input",
        "authority": "Canonical Bot Telegram finalization session; separate Web-native finishing workflow",
        "next_contract": "Bot vfinal callbacks remain Telegram-only because they mutate or consume Bot finalization/media/input/export state. Web finishing must begin from its own signed draft and verified owner asset, then separately guard render/export/payment/delivery; never replay a Bot callback or state value.",
        "source_dispositions": ("BOT_VIDEO_FINALIZATION_SESSION_STATE", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "The Bot vfinal handler reads and writes per-Telegram-user finalization state and can route to pending input, selected media, provider readiness, quote/package and export guards.",
    },
    "media_preview": {
        "priority": "P0",
        "candidate_boundary": "separate Web media-catalog and owner-scoped selection contract",
        "authority": "Canonical Bot media-preview cache, Telegram delivery and selected-media state",
        "next_contract": "Create a Web-owned catalog/preview/selection contract with verified media rights, owner-scoped references and explicit downstream handoff; do not accept Bot cache indexes or replay Telegram preview callbacks.",
        "source_dispositions": ("BOT_MEDIA_PREVIEW_CACHE", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "Bot preview buttons resolve a short-lived per-user cache, deliver media or guidance through Telegram, and can mutate Bot selected-media state for later Bot-only workflows.",
    },
    "pkgbuy": {
        "priority": "P0",
        "candidate_boundary": "fresh /packages catalog navigation or canonical Bot package checkout",
        "authority": "Canonical Bot package catalog, PayOS order and entitlement settlement",
        "next_contract": "Only exact source-reviewed catalog selectors may open a fresh signed Web package catalog. Package checkout/confirmation stays Bot-canonical until a dedicated owner-scoped package-purchase bridge exists; Web must not price, create orders, finalize PayOS, grant entitlement or create a second webhook.",
        "source_dispositions": ("CANONICAL_PACKAGE_PURCHASE_SOURCE_REVIEW", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "The Bot package selector only renders a catalog detail, but its confirmation branch creates a pending canonical order, creates PayOS checkout, and later grants package entitlement after canonical settlement.",
    },
    "storage": {
        "priority": "P0",
        "candidate_boundary": "canonical Bot storage add-on order, PayOS checkout and entitlement settlement",
        "authority": "Canonical Bot storage quota/PayOS state machine",
        "next_contract": "Storage add-on menu, custom input and confirmation remain Bot-canonical until a dedicated owner-scoped storage bridge exists. Web must not turn the flow into Xu top-up, accept a Bot amount/code, create an order, finalize PayOS, grant quota or create a second webhook/ledger.",
        "source_dispositions": ("CANONICAL_BOT_STORAGE_ADDON_SOURCE_REVIEW", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "The Bot storage callback flow uses Telegram pending input, canonical orders/PayOS checkout and canonical quota entitlement settlement; it is not a Xu top-up flow.",
    },
    "payosalert": {
        "priority": "P0",
        "candidate_boundary": "TELEGRAM_ONLY",
        "authority": "Canonical Bot PayOS/admin alert flow",
        "next_contract": "Classify each alert action by source evidence; do not convert Telegram dismissal, test or renewal buttons into Web payment actions.",
        "source_dispositions": ("BOT_ADMIN_ONLY", "TELEGRAM_ALERT_CONTEXT", "NO_RUNTIME_CLAIM"),
        "source_evidence": "The observed Bot alert keyboard is sent only to owner/admin IDs and its handler rejects non-admin callers before any action. Its controls are Telegram alert/message guidance or Bot-local state, not a customer payment contract.",
    },
    "job": {
        "priority": "P0",
        "candidate_boundary": "fresh /admin/jobs navigation or canonical Bot video-job state",
        "authority": "Canonical Bot admin video-job state machine",
        "next_contract": "Only the exact read-only Bot stats callback may open a fresh signed admin jobs view. Approve/cancel and every unreviewed job callback stay Bot-canonical until a dedicated owner-scoped admin bridge action exists; Web must not accept a Bot job ID or mutate canonical job state.",
        "source_dispositions": ("BOT_ADMIN_ONLY", "CANONICAL_BOT_VIDEO_JOB_STATE", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "The Bot video-job callback handler rejects non-admin callers. Its stats branch reads canonical campaign/video_job rows, while approve/cancel resolve the Bot owner and update the canonical job status.",
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
        "candidate_boundary": "/document-workspace + independent /documents/* tools",
        "authority": "Bot pending state remains Bot-owned; Web tools are independently Web-native",
        "next_contract": "Keep every docflow callback as a source disposition until a finite, owner-scoped Web handoff is proven. A document plan may link to a fresh Asset Vault-backed tool, but must not transfer Telegram pending files, page choices, compression profile, confirmation, execution, charge or delivery state.",
        "source_dispositions": ("SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "Bot `handle_doc_tool_callback` reads and mutates USER_PENDING document files/options, can request page ranges, select Bot compression labels, and runs local execution/delivery after the Bot confirmation path. A Web navigation link is not a replay of that state machine.",
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
        "candidate_boundary": "finite Bot-state dispositions; separate Web-native or private-bridge design required",
        "authority": "Canonical Bot pending, wallet/package, provider/job and Telegram-chat state",
        "next_contract": "Use TVFLOW_CALLBACK_CONTRACT.md for each finite callback. Only a separately reviewed owner-scoped Web-native workflow or private bridge contract may replace a symbolic Bot-state boundary; do not infer rendering, content mutation, asset ownership or execution from a callback label.",
        "source_evidence": "Bot handler `handle_trend_video_flow_callback` reads/clears pending workflow and confirmation state, can inspect canonical package/Xu state, record billing events, enter provider/job guards, use Bot job IDs, or return Telegram-only guidance.",
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

# ``docflow`` is a single Telegram dispatcher family, but its finite values
# do not have one browser meaning.  Keep the detail here rather than allowing
# the generic keyword router to label a profile/confirmation as a Web feature.
# All of these records intentionally remain NEEDS_FEATURE_DISPOSITION: the
# metadata clarifies a source boundary; it does not increase Web coverage.
DOCFLOW_CALLBACK_DISPOSITIONS: dict[str, dict[str, Any]] = {
    "docflow|send_more": {
        "target": "/document-workspace",
        "resolution": "docflow_pending_file_collection_not_web_handoff",
        "source_dispositions": ("TELEGRAM_PENDING_FILE_STATE", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "Bot asks for another Telegram attachment and retains it in USER_PENDING. Web Document Workspace never accepts or transfers that file slot.",
    },
    "docflow|reset_files": {
        "target": "/document-workspace",
        "resolution": "docflow_pending_file_reset_not_web_handoff",
        "source_dispositions": ("TELEGRAM_PENDING_FILE_STATE", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "Bot clears pending Telegram files/options before collecting a new source. Web navigation must not mutate Bot state or inherit its files.",
    },
    "docflow|pop": {
        "target": "/document-workspace",
        "resolution": "docflow_pending_file_pop_not_web_handoff",
        "source_dispositions": ("TELEGRAM_PENDING_FILE_STATE", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "Bot removes the latest pending Telegram file. Web has no access to the Bot file list and uses independent Asset Vault selection.",
    },
    "docflow|clear": {
        "target": "/document-workspace",
        "resolution": "docflow_pending_file_clear_not_web_handoff",
        "source_dispositions": ("TELEGRAM_PENDING_FILE_STATE", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "Bot clears its pending document list/options. This is not a browser document operation or asset mutation.",
    },
    "docflow|ask_pages": {
        "target": "/documents/split",
        "resolution": "docflow_page_prompt_requires_fresh_web_input",
        "source_dispositions": ("TELEGRAM_PENDING_PAGE_STATE", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "Bot enters a page-range prompt against its pending Telegram PDF. The Web split tool requires a fresh owner-scoped source and independently entered page range.",
    },
    "docflow|back": {
        "target": "/document-workspace",
        "resolution": "docflow_bot_navigation_not_web_state_transfer",
        "source_dispositions": ("TELEGRAM_MESSAGE_NAVIGATION", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "Bot clears pending state and redraws its parent Telegram menu. Opening a fresh Web workspace does not restore a previous Telegram screen.",
    },
    "docflow|back_received": {
        "target": "/document-workspace",
        "resolution": "docflow_bot_navigation_not_web_state_transfer",
        "source_dispositions": ("TELEGRAM_MESSAGE_NAVIGATION", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "Bot redraws the pending-file summary. Web does not receive or render that Telegram file state.",
    },
    "docflow|main": {
        "target": "/document-workspace",
        "resolution": "docflow_bot_navigation_not_web_state_transfer",
        "source_dispositions": ("TELEGRAM_MESSAGE_NAVIGATION", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "Bot clears its document flow and returns to the Telegram main menu. The Web route starts a separate signed session surface.",
    },
    "docflow|compress|light": {
        "target": "/documents/compress",
        "resolution": "docflow_compression_profile_semantics_mismatch",
        "source_dispositions": ("PROFILE_SEMANTICS_MISMATCH", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "Bot records the label Nén nhẹ on a pending Telegram PDF. Web PDF Optimize has one verified structural profile and must not claim to reproduce Bot light/medium/strong choices.",
    },
    "docflow|compress|medium": {
        "target": "/documents/compress",
        "resolution": "docflow_compression_profile_semantics_mismatch",
        "source_dispositions": ("PROFILE_SEMANTICS_MISMATCH", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "Bot records the label Nén vừa on a pending Telegram PDF. Web PDF Optimize has one verified structural profile and must not claim to reproduce Bot light/medium/strong choices.",
    },
    "docflow|compress|strong": {
        "target": "/documents/compress",
        "resolution": "docflow_compression_profile_semantics_mismatch",
        "source_dispositions": ("PROFILE_SEMANTICS_MISMATCH", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "Bot records the label Nén mạnh on a pending Telegram PDF. Web PDF Optimize has one verified structural profile and must not claim to reproduce Bot light/medium/strong choices.",
    },
    "docflow|confirm": {
        "target": "BOT_PENDING_CONFIRMATION_REQUIRED",
        "resolution": "docflow_confirmation_not_web_execution",
        "source_dispositions": ("TELEGRAM_PENDING_CONFIRMATION", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "Bot validates pending files/options and builds a Telegram confirmation. It is not an owner-scoped Web execution, payment or delivery confirmation.",
    },
    "docflow|run": {
        "target": "BOT_PENDING_EXECUTION_REQUIRED",
        "resolution": "docflow_execution_delivery_not_web_runtime",
        "source_dispositions": ("BOT_EXECUTION_DELIVERY_BOUNDARY", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "Bot runs its pending document flow, performs delivery checks and may charge only under Bot rules. Web must not replay this action from a plan or callback.",
    },
}
DOCFLOW_DEFAULT_DISPOSITION: dict[str, Any] = {
    "target": "SOURCE_STATE_MACHINE_REQUIRED",
    "resolution": "unreviewed_docflow_source_state_machine",
    "source_dispositions": ("SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
    "source_evidence": "A docflow callback needs handler-level state review before any Web navigation or execution claim.",
}

# ``tvflow`` is the Bot's trend-video dispatcher.  Several values happen to
# contain words such as ``image``, ``video``, ``content`` or ``package``, but
# the handler reads pending Bot state, may touch the canonical Xu/package
# boundary, and can enter provider/job guards.  Never let the generic keyword
# router turn those words into an existing Web feature claim.
#
# Each disposition remains NEEDS_FEATURE_DISPOSITION.  A symbolic target is a
# review/authority boundary, not a browser route, bridge implementation, or
# authorization to replay a Telegram callback from the Web App.
TVFLOW_CALLBACK_DISPOSITIONS: dict[str, dict[str, Any]] = {
    "tvflow|cancel_content": {
        "target": "BOT_TREND_CONFIRMATION_AND_BILLING_REQUIRED",
        "resolution": "tvflow_cancel_content_requires_bot_pending_state",
        "source_dispositions": (
            "TELEGRAM_PENDING_CONFIRMATION",
            "BOT_BILLING_AUDIT_BOUNDARY",
            "SOURCE_STATE_MACHINE_REQUIRED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "Bot reads and clears a pending trend-content confirmation, then records a Bot billing event. A browser cannot cancel or reconstruct that pending state.",
    },
    "tvflow|confirm_content": {
        "target": "BOT_TREND_CONFIRMATION_AND_BILLING_REQUIRED",
        "resolution": "tvflow_confirm_content_requires_bot_billing_execution",
        "source_dispositions": (
            "TELEGRAM_PENDING_CONFIRMATION",
            "BOT_WALLET_OR_PACKAGE_BOUNDARY",
            "BOT_EXECUTION_DELIVERY_BOUNDARY",
            "SOURCE_STATE_MACHINE_REQUIRED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "Bot consumes pending trend-content confirmation, applies canonical Xu/package rules, records billing evidence, and enters its execution/delivery path. No Web execution is proven.",
    },
    "tvflow|confirm_content_package": {
        "target": "BOT_TREND_CONFIRMATION_AND_BILLING_REQUIRED",
        "resolution": "tvflow_confirm_content_requires_bot_billing_execution",
        "source_dispositions": (
            "TELEGRAM_PENDING_CONFIRMATION",
            "BOT_WALLET_OR_PACKAGE_BOUNDARY",
            "BOT_EXECUTION_DELIVERY_BOUNDARY",
            "SOURCE_STATE_MACHINE_REQUIRED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "Bot consumes pending trend-content confirmation, applies canonical Xu/package rules, records billing evidence, and enters its execution/delivery path. No Web execution is proven.",
    },
    "tvflow|cancel": {
        "target": "BOT_TREND_PENDING_STATE_REQUIRED",
        "resolution": "tvflow_cancel_requires_bot_pending_state",
        "source_dispositions": (
            "TELEGRAM_PENDING_WORKFLOW_STATE",
            "SOURCE_STATE_MACHINE_REQUIRED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "Bot clears trend workflow, confirmation, and warranty-retry pending state. A Web dashboard cancellation must not mutate or inherit those Bot slots.",
    },
    "tvflow|image_scene_1": {
        "target": "BOT_TREND_OUTPUT_AND_IMAGE_CONFIRMATION_REQUIRED",
        "resolution": "tvflow_image_scene_requires_bot_output_credit_confirmation",
        "source_dispositions": (
            "BOT_TREND_OUTPUT_STATE",
            "PROVIDER_AND_CREDIT_GUARD",
            "TELEGRAM_PENDING_CONFIRMATION",
            "SOURCE_STATE_MACHINE_REQUIRED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "Bot reads cached trend output, checks public image/provider and credit guards, then creates a separate Bot confirmation. A Web Image Studio route does not own that output or confirmation.",
    },
    "tvflow|image_scene_2": {
        "target": "BOT_TREND_OUTPUT_AND_IMAGE_CONFIRMATION_REQUIRED",
        "resolution": "tvflow_image_scene_requires_bot_output_credit_confirmation",
        "source_dispositions": (
            "BOT_TREND_OUTPUT_STATE",
            "PROVIDER_AND_CREDIT_GUARD",
            "TELEGRAM_PENDING_CONFIRMATION",
            "SOURCE_STATE_MACHINE_REQUIRED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "Bot reads cached trend output, checks public image/provider and credit guards, then creates a separate Bot confirmation. A Web Image Studio route does not own that output or confirmation.",
    },
    "tvflow|image_scene_3": {
        "target": "BOT_TREND_OUTPUT_AND_IMAGE_CONFIRMATION_REQUIRED",
        "resolution": "tvflow_image_scene_requires_bot_output_credit_confirmation",
        "source_dispositions": (
            "BOT_TREND_OUTPUT_STATE",
            "PROVIDER_AND_CREDIT_GUARD",
            "TELEGRAM_PENDING_CONFIRMATION",
            "SOURCE_STATE_MACHINE_REQUIRED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "Bot reads cached trend output, checks public image/provider and credit guards, then creates a separate Bot confirmation. A Web Image Studio route does not own that output or confirmation.",
    },
    "tvflow|save_image": {
        "target": "TELEGRAM_GUIDANCE_OR_CHAT_STATE",
        "resolution": "tvflow_save_image_is_not_a_web_asset",
        "source_dispositions": ("TELEGRAM_CHAT_OUTPUT_ONLY", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "Bot guidance says the image remains in Telegram chat and automatic project saving is not present. Web must not imply that an Asset Vault record exists.",
    },
    "tvflow|edit_prompt": {
        "target": "TELEGRAM_GUIDANCE_OR_CHAT_STATE",
        "resolution": "tvflow_prompt_guidance_is_not_web_state_transfer",
        "source_dispositions": ("TELEGRAM_GUIDANCE_OR_CHAT_STATE", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "Bot returns chat guidance for editing a trend prompt. It does not transfer a pending prompt, output, or job into a Web draft.",
    },
    "tvflow|rewrite": {
        "target": "TELEGRAM_GUIDANCE_OR_CHAT_STATE",
        "resolution": "tvflow_prompt_guidance_is_not_web_state_transfer",
        "source_dispositions": ("TELEGRAM_GUIDANCE_OR_CHAT_STATE", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "Bot returns chat guidance for rewriting a trend prompt. It does not transfer a pending prompt, output, or job into a Web draft.",
    },
    "tvflow|video_prompt": {
        "target": "TELEGRAM_GUIDANCE_OR_CHAT_STATE",
        "resolution": "tvflow_prompt_guidance_is_not_web_state_transfer",
        "source_dispositions": ("TELEGRAM_GUIDANCE_OR_CHAT_STATE", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
        "source_evidence": "Bot returns chat guidance for a video prompt and may direct the user to another Bot flow. It is not a Web video plan, provider call, or job output.",
    },
}
TVFLOW_CALLBACK_PREFIX_DISPOSITIONS: tuple[tuple[str, dict[str, Any]], ...] = (
    (
        "tvflow|admin_video_image_",
        {
            "target": "BOT_ADMIN_SMOKE_REQUIRED",
            "classification": "admin",
            "status": "TELEGRAM_ONLY",
            "resolution": "tvflow_admin_smoke_requires_bot_authority",
            "source_dispositions": ("BOT_ADMIN_SMOKE_BOUNDARY", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
            "source_evidence": "Bot dispatches an admin image-video smoke action using Bot job context. It is not a browser-admin action or a provider readiness claim.",
        },
    ),
    (
        "tvflow|image_warranty_retry_",
        {
            "target": "BOT_IMAGE_JOB_WARRANTY_REQUIRED",
            "resolution": "tvflow_warranty_retry_requires_bot_job_state",
            "source_dispositions": ("BOT_JOB_WARRANTY_BOUNDARY", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
            "source_evidence": "Bot retries a trend-image warranty path against a Bot job identifier and canonical job state. Web must not accept or replay that identifier.",
        },
    ),
    (
        "tvflow|regen_scene_",
        {
            "target": "BOT_TREND_OUTPUT_AND_IMAGE_CONFIRMATION_REQUIRED",
            "resolution": "tvflow_regen_scene_requires_bot_output_confirmation",
            "source_dispositions": ("BOT_TREND_OUTPUT_STATE", "PROVIDER_AND_CREDIT_GUARD", "TELEGRAM_PENDING_CONFIRMATION", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
            "source_evidence": "Bot regenerates an indexed trend scene from its pending/output state and can enter image confirmation. The formatted scene index is not a Web asset selector.",
        },
    ),
    (
        "tvflow|image_video_real_",
        {
            "target": "BOT_IMAGE_TO_VIDEO_CONTEXT_REQUIRED",
            "resolution": "tvflow_image_video_requires_bot_package_context",
            "source_dispositions": ("BOT_IMAGE_VIDEO_CONTEXT", "BOT_WALLET_OR_PACKAGE_BOUNDARY", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
            "source_evidence": "Bot sets public video package context from a Bot job and selected image. A Web route cannot receive that job identifier or package context.",
        },
    ),
    (
        "tvflow|image_video_prompt_",
        {
            "target": "BOT_IMAGE_TO_VIDEO_CONTEXT_REQUIRED",
            "resolution": "tvflow_image_video_prompt_requires_bot_context",
            "source_dispositions": ("BOT_IMAGE_VIDEO_CONTEXT", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
            "source_evidence": "Bot image-to-video prompt actions use a Bot job/output context. The formatted values are not owner-scoped Web asset or draft identifiers.",
        },
    ),
    (
        "tvflow|image_video_prompts_",
        {
            "target": "BOT_IMAGE_TO_VIDEO_CONTEXT_REQUIRED",
            "resolution": "tvflow_image_video_prompt_requires_bot_context",
            "source_dispositions": ("BOT_IMAGE_VIDEO_CONTEXT", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
            "source_evidence": "Bot image-to-video prompt actions use a Bot job/output context. The formatted values are not owner-scoped Web asset or draft identifiers.",
        },
    ),
    (
        "tvflow|music_image_",
        {
            "target": "BOT_IMAGE_TO_VIDEO_CONTEXT_REQUIRED",
            "resolution": "tvflow_image_video_requires_bot_context",
            "source_dispositions": ("BOT_IMAGE_VIDEO_CONTEXT", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
            "source_evidence": "Bot opens music choices for an image-video job held in Bot state. It does not prove a Web-owned media draft or music execution contract.",
        },
    ),
    (
        "tvflow|image_back_",
        {
            "target": "BOT_IMAGE_TO_VIDEO_CONTEXT_REQUIRED",
            "resolution": "tvflow_image_video_requires_bot_context",
            "source_dispositions": ("BOT_IMAGE_VIDEO_CONTEXT", "SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
            "source_evidence": "Bot returns within an image-video flow backed by Bot job state. Browser navigation must not recreate the Bot back-stack or hidden identifiers.",
        },
    ),
)
TVFLOW_DEFAULT_DISPOSITION: dict[str, Any] = {
    "target": "BOT_TRENDFLOW_SOURCE_REVIEW_REQUIRED",
    "resolution": "unreviewed_tvflow_source_state_machine",
    "source_dispositions": ("SOURCE_STATE_MACHINE_REQUIRED", "NO_RUNTIME_CLAIM"),
    "source_evidence": "A tvflow callback needs finite handler/state review before any Web navigation, bridge, provider, billing, job, asset, or execution claim.",
}

# These dynamic preview callbacks are emitted only by the Bot media-preview
# keyboard. Their formatted values are either a media kind/index pair or an
# index into a short-lived per-Telegram-user cache; they are not owner-scoped
# Web asset or media identifiers. The independently owned Web Media Workspace
# now offers a separate Asset Vault reference/preview boundary, but it cannot
# consume or replay these opaque Bot values. Each original callback is thus
# explicitly Telegram-only instead of an unresolved Web feature gap.
MEDIA_PREVIEW_CALLBACK_TEMPLATE_DISPOSITIONS: dict[str, dict[str, Any]] = {
    "play_{*}|{*}": {
        "target": "TELEGRAM_ONLY",
        "status": "TELEGRAM_ONLY",
        "resolution": "reviewed_bot_preview_play_telegram_only_web_owned_preview_separate",
        "source_dispositions": (
            "BOT_MEDIA_PREVIEW_CACHE",
            "TELEGRAM_CHAT_DELIVERY",
            "SOURCE_STATE_MACHINE_REQUIRED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "Bot resolves a music/SFX index from its short-lived per-Telegram-user preview cache and sends the audio preview into Telegram chat. The formatted values are not Web asset IDs or a browser playback contract.",
    },
    "select_{*}|{*}": {
        "target": "TELEGRAM_ONLY",
        "status": "TELEGRAM_ONLY",
        "resolution": "reviewed_bot_media_select_telegram_only_web_owned_reference_separate",
        "source_dispositions": (
            "BOT_MEDIA_PREVIEW_CACHE",
            "BOT_MEDIA_SELECTION_STATE",
            "SOURCE_STATE_MACHINE_REQUIRED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "Bot resolves a cached music/SFX result then writes selected-media state for later Bot video/image/trend/cinematic flows. The formatted values are not a Web-owned media selection or asset reference.",
    },
    "license_{*}|1": {
        "target": "TELEGRAM_ONLY",
        "status": "TELEGRAM_ONLY",
        "resolution": "reviewed_bot_media_license_telegram_only_web_rights_note_separate",
        "source_dispositions": (
            "BOT_MEDIA_PREVIEW_CACHE",
            "TELEGRAM_CHAT_GUIDANCE",
            "SOURCE_STATE_MACHINE_REQUIRED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "Bot reads the first current music/SFX preview result from its per-user cache and sends a Telegram license notice. The callback does not establish Web catalog ownership, license verification, or a browser media contract.",
    },
    "license_music|{*}": {
        "target": "TELEGRAM_ONLY",
        "status": "TELEGRAM_ONLY",
        "resolution": "reviewed_bot_media_license_telegram_only_web_rights_note_separate",
        "source_dispositions": (
            "BOT_MEDIA_PREVIEW_CACHE",
            "TELEGRAM_CHAT_GUIDANCE",
            "SOURCE_STATE_MACHINE_REQUIRED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "Bot resolves the formatted music index from its short-lived per-user preview cache and sends a Telegram license notice. The value is not a Web media ID, catalog authority, license verification, or browser media contract.",
    },
    "play_media|{*}": {
        "target": "TELEGRAM_ONLY",
        "status": "TELEGRAM_ONLY",
        "resolution": "reviewed_bot_preview_play_telegram_only_web_owned_preview_separate",
        "source_dispositions": (
            "BOT_MEDIA_PREVIEW_CACHE",
            "TELEGRAM_CHAT_DELIVERY",
            "SOURCE_STATE_MACHINE_REQUIRED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "Bot resolves the formatted media index from its short-lived per-user media-preview cache and sends the preview or source into Telegram chat. The value is not a Web asset ID or browser playback contract.",
    },
    "select_media|{*}": {
        "target": "TELEGRAM_ONLY",
        "status": "TELEGRAM_ONLY",
        "resolution": "reviewed_bot_media_select_telegram_only_web_owned_reference_separate",
        "source_dispositions": (
            "BOT_MEDIA_PREVIEW_CACHE",
            "BOT_MEDIA_SELECTION_STATE",
            "SOURCE_STATE_MACHINE_REQUIRED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "Bot resolves a cached media result then writes its selected-media state for later Bot flows. The formatted value is not a Web-owned media selection or asset reference.",
    },
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
# A dynamic callback can embed a formatted value inside a fixed segment, for
# example ``tvflow|image_video_real_{job_id}_{choice}``.  Treat that as an
# opaque template rather than dropping it from the inventory.  The grammar is
# deliberately narrow: only a segment beginning with an alphanumeric literal
# or one ``{*}`` marker may contain letters, digits, ``._-`` and further whole
# ``{*}`` markers; it never evaluates an f-string or exposes its values.
CALLBACK_TEMPLATE_SEGMENT_RE = r"(?=[A-Za-z0-9{])(?:[A-Za-z0-9_.-]|\{\*\})+"
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
# The frozen Quick Image flow delegates its nine Logo/Watermark positions to a
# generic helper.  A raw ``create_media|{*}|top_left`` template would be too
# broad to map safely because the helper also serves other image/video flows.
# These deliberately narrow patterns derive only the finite ``qi_logo_pos``
# literals when the direct Quick Image call site is present.  This remains a
# source-only transformation: no helper is imported or executed.
QUICK_IMAGE_LOGO_POSITION_HELPER_RE = re.compile(
    r"(?ms)^\s*def\s+(?P<helper>media_logo_watermark_position_keyboard)\s*\(\s*kind\b"
    r"(?P<body>.*?)(?=^\s*(?:async\s+)?def\s|\Z)"
)
QUICK_IMAGE_LOGO_POSITION_LITERAL_CALL_RE = re.compile(
    r"\b(?P<helper>media_logo_watermark_position_keyboard)\s*\(\s*['\"]image['\"]\s*,\s*[^,\r\n]+\s*,\s*"
    r"['\"](?P<prefix>qi_logo_pos)['\"]\s*,\s*['\"]create_media\|qi_logo_add['\"]"
)
QUICK_IMAGE_LOGO_POSITION_VALUES = frozenset({
    "top_left", "top_center", "top_right", "center_left", "center", "center_right",
    "bottom_left", "bottom_center", "bottom_right",
})
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

    # The canonical Bot source is multi-megabyte and produces thousands of
    # static records.  Counting newlines from character zero for every match
    # makes location collection quadratic in source size.  Build the immutable
    # line-start index once; `bisect_right` keeps exactly the same 1-based line
    # semantics without evaluating/importing the source or dropping records.
    line_starts = [0]
    line_starts.extend(match.end() for match in re.finditer(r"\n", text))
    relative_path = _relative(path, root)

    def location(match: re.Match[str]) -> dict[str, Any]:
        return {"file": relative_path, "line": bisect_right(line_starts, match.start())}

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


def _resolve_reviewed_quick_image_logo_position_callbacks(
    *,
    text: str,
    root: Path,
    path: Path,
    callback_templates: list[dict[str, Any]],
    callback_data: list[dict[str, Any]],
    seen: dict[str, set[tuple[Any, ...]]],
) -> None:
    """Derive only frozen Quick Image logo-position literals from one helper.

    The helper's generic formatted prefix is shared by regular image and video
    flows.  It becomes Quick Image evidence only when its direct call supplies
    the literal ``qi_logo_pos`` prefix and Quick Image back callback.  The
    resulting nine values stay audit evidence; the browser receives semantic
    position enums through its signed Web-native Planner, never these values.
    """

    relative_path = _relative(path, root)
    records = [record for record in callback_templates if record.get("file") == relative_path]
    if not records:
        return

    for helper_match in QUICK_IMAGE_LOGO_POSITION_HELPER_RE.finditer(text):
        helper = str(helper_match.group("helper") or "")
        start_line = _line_for_offset(text, helper_match.start())
        end_line = _line_for_offset(text, helper_match.end())
        calls = [
            {
                "prefix": str(call.group("prefix")),
                "file": relative_path,
                "line": _line_for_offset(text, call.start()),
            }
            for call in QUICK_IMAGE_LOGO_POSITION_LITERAL_CALL_RE.finditer(text)
            if call.group("helper") == helper
        ]
        if not calls:
            continue

        for template_record in records:
            template_line = int(template_record.get("line") or 0)
            if template_line < start_line or template_line > end_line:
                continue
            template = str(template_record.get("template") or "")
            if not template.startswith("create_media|{*}|") or template.count("{*}") != 1:
                continue
            suffix = template.rsplit("|", 1)[-1]
            if suffix not in QUICK_IMAGE_LOGO_POSITION_VALUES:
                continue

            derived_tokens = sorted({template.replace("{*}", call["prefix"], 1) for call in calls})
            template_record.update(
                {
                    "resolution": "reviewed_quick_image_logo_position_helper_calls",
                    "helper": helper,
                    "derived_callback_tokens": derived_tokens,
                    "literal_prefix_call_evidence": calls,
                }
            )
            for call in calls:
                token = template.replace("{*}", call["prefix"], 1)
                record = {
                    "token": token,
                    "resolution": "reviewed_quick_image_logo_position_helper_call",
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
        _resolve_reviewed_quick_image_logo_position_callbacks(
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
        "/dashboard", "/account", "/onboarding", "/chat", "/prompt-studio", "/wallet", "/packages", "/jobs", "/assets", "/asset-vault", "/support", "/tickets", "/analytics",
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
    job_lock_recovery_source_review_entry = JOB_LOCK_RECOVERY_CANONICAL_SOURCE_REVIEW_COMMANDS.get(name)
    if job_lock_recovery_source_review_entry is not None:
        # A literal Bot command can mutate canonical job, refund and billing
        # state. Never let its convenient admin-looking name imply a Web route
        # or browser command surface.
        return {
            "source_kind": "command",
            "source": f"/{command['command']}",
            "handler": command["handler"],
            "target": "CANONICAL_JOB_LOCK_RECOVERY_SOURCE_REVIEW_REQUIRED",
            "classification": "admin",
            "status": "NEEDS_FEATURE_DISPOSITION",
            "resolution": "reviewed_job_lock_recovery_command_requires_canonical_mutation_contract",
            "source_dispositions": _job_lock_recovery_source_review_dispositions(job_lock_recovery_source_review_entry),
            "source_evidence": str(job_lock_recovery_source_review_entry["source_evidence"]),
            "evidence": {"file": command["file"], "line": command["line"]},
        }
    admin = _is_admin_command(name, command["handler"], admin_guarded=bool(command.get("admin_guarded")))
    telegram_only = _is_telegram_only(name)
    interface_locale_navigation = (
        not telegram_only
        and not admin
        and name in INTERFACE_LOCALE_FRESH_WEB_NAVIGATION_COMMANDS
    )
    document_navigation_entry = DOCUMENT_FRESH_WEB_NAVIGATION_COMMANDS.get(name)
    route_override = COMMAND_ROUTE_OVERRIDES.get(name)
    if admin and not telegram_only:
        target = f"/admin/{name}"
    elif interface_locale_navigation:
        target = "/account"
    elif document_navigation_entry is not None:
        target = str(document_navigation_entry["target"])
    else:
        target = route_override or _feature_route(name)
    navigation_entrypoint = not telegram_only and not admin and name in DASHBOARD_ENTRYPOINT_COMMANDS and target == "/dashboard"
    interface_locale_navigation = interface_locale_navigation and target == "/account"
    document_navigation = not telegram_only and not admin and document_navigation_entry is not None
    dashboard_fallback = not telegram_only and not navigation_entrypoint and route_override is None and target == "/dashboard"
    status = _mapping_status(
        target,
        existing_routes,
        telegram_only,
        dashboard_fallback=dashboard_fallback,
        navigation_entrypoint=navigation_entrypoint,
        navigation_only=document_navigation or interface_locale_navigation,
    )
    if telegram_only:
        resolution = "telegram_only"
    elif navigation_entrypoint:
        resolution = "reviewed_dashboard_navigation_entrypoint"
    elif interface_locale_navigation:
        resolution = "reviewed_interface_locale_fresh_web_navigation"
    elif document_navigation:
        resolution = "reviewed_document_fresh_web_navigation"
    elif dashboard_fallback:
        resolution = "unreviewed_dashboard_fallback_requires_feature_disposition"
    else:
        resolution = "explicit_static_route_mapping"
    mapping = {
        "source_kind": "command",
        "source": f"/{command['command']}",
        "handler": command["handler"],
        "target": target if not telegram_only else "TELEGRAM_ONLY",
        "classification": "admin" if admin else "customer",
        "status": status,
        "resolution": resolution,
        "evidence": {"file": command["file"], "line": command["line"]},
    }
    if document_navigation_entry is not None and not telegram_only and not admin:
        mapping.update(
            {
                "source_dispositions": DOCUMENT_FRESH_WEB_NAVIGATION_DISPOSITIONS,
                "source_evidence": "The command may only open a fresh signed Web-native document surface. Bot pending files, file order, page range, compression profile, confirmation, execution, charge and delivery state are never transferred.",
                "document_capability_key": str(document_navigation_entry["capability_key"]),
                "document_feature_key": str(document_navigation_entry["feature_key"]),
                "document_surface": str(document_navigation_entry["surface"]),
                "document_authority": "SIGNED_CUSTOMER_WEB_NATIVE",
                "document_launch_mode": "WEB_NAVIGATION",
            }
        )
    if interface_locale_navigation:
        mapping.update(
            {
                "source_dispositions": INTERFACE_LOCALE_FRESH_WEB_NAVIGATION_DISPOSITIONS,
                "source_evidence": (
                    "The Bot command opens a language/menu chooser for a Telegram user. The Web opens a fresh "
                    "signed Account preference page only; it does not receive a Bot user ID, locale, menu, "
                    "pending state, translation mode or workflow language. A customer must explicitly choose "
                    "and CSRF-save one reviewed Web interface locale."
                ),
                "interface_locale_authority": "SIGNED_CUSTOMER_WEB_PROFILE",
                "interface_locale_launch_mode": "WEB_NAVIGATION",
                "interface_locale_supported_values": ("vi", "en", "zh"),
            }
        )
    return mapping


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


def _map_docflow_callback(identifier: str, source_kind: str, evidence: dict[str, Any]) -> dict[str, Any]:
    """Record a finite Bot document-flow state without inventing Web parity.

    The target is a review boundary or a clean Web starting point, never a
    callback payload, pending Telegram file, browser execution endpoint or
    claim that the corresponding Document Operation has run.
    """

    token = str(identifier or "").casefold()
    policy = DOCFLOW_CALLBACK_DISPOSITIONS.get(token, DOCFLOW_DEFAULT_DISPOSITION)
    return {
        "source_kind": source_kind,
        "source": identifier,
        "target": str(policy["target"]),
        "classification": "customer",
        "status": "NEEDS_FEATURE_DISPOSITION",
        "resolution": str(policy["resolution"]),
        "source_dispositions": [str(value) for value in policy["source_dispositions"]],
        "source_evidence": str(policy["source_evidence"]),
        "evidence": evidence,
    }


def _map_archive_callback(identifier: str, source_kind: str, evidence: dict[str, Any], existing_routes: set[str]) -> dict[str, Any]:
    """Keep Bot Archive callbacks inside a finite, role-checked boundary.

    A Bot archive token can include a department/type choice, temporary search
    state, pending upload/edit record or a Telegram file-delivery action.  The
    independently owned Admin Archive may only start blank from a reviewed
    directory literal; every other source remains explicit source review or
    Telegram-only rather than inheriting a generic Admin route.
    """

    token = str(identifier or "").casefold()
    if token in ARCHIVE_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS:
        target = "/admin/internal-documents"
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": target,
            "classification": "admin",
            "status": _mapping_status(target, existing_routes, telegram_only=False, navigation_only=True),
            "resolution": "reviewed_archive_fresh_admin_navigation",
            "source_dispositions": (
                "BOT_ADMIN_ONLY",
                "BOT_ARCHIVE_SELECTION_STATE_NOT_REPLAYED",
                "FRESH_SIGNED_WEB_ADMIN_NAVIGATION",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The reviewed Bot archive literal only opens/redraws an admin archive menu, type or search "
                "choice. The Web starts a fresh canonical-admin Archive directory and receives no Bot "
                "department, type, query, pending file, record, upload, edit or delivery context."
            ),
            "archive_authority": "SIGNED_CANONICAL_ADMIN_WEB_NATIVE",
            "archive_launch_mode": "WEB_NAVIGATION",
            "evidence": evidence,
        }
    if token in ARCHIVE_TELEGRAM_ONLY_ACTIONS:
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": "TELEGRAM_ONLY",
            "classification": "admin",
            "status": "TELEGRAM_ONLY",
            "resolution": "archive_preview_or_save_requires_telegram_state",
            "source_dispositions": (
                "BOT_ADMIN_ONLY",
                "TELEGRAM_ARCHIVE_RECORD_OR_DELIVERY_STATE",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The Bot preview/save branch resolves a Telegram-side archive record, pending edit/upload or "
                "file delivery path. The standalone Web Archive has separate records and never accepts the "
                "Bot identifier or replays this action."
            ),
            "evidence": evidence,
        }
    review_label = (
        "reviewed_archive_callback_requires_source_review"
        if token in ARCHIVE_SOURCE_REVIEW_ACTIONS
        else "archive_callback_requires_source_review"
    )
    return {
        "source_kind": source_kind,
        "source": identifier,
        "target": "ADMIN_INTERNAL_DOCUMENT_ARCHIVE_SOURCE_REVIEW_REQUIRED",
        "classification": "admin",
        "status": "NEEDS_FEATURE_DISPOSITION",
        "resolution": review_label,
        "source_dispositions": (
            "BOT_ADMIN_ONLY",
            "BOT_ARCHIVE_STATE_OR_IDENTIFIER_SOURCE_REVIEW",
            "SOURCE_STATE_MACHINE_REQUIRED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "An Archive callback may carry Bot department/type/search state, a pending record identifier, "
            "an edit transition, upload/delivery control or another canonical Bot archive action. It must "
            "receive finite source review before it can gain any Web meaning."
        ),
        "evidence": evidence,
    }


def _map_interface_locale_callback(
    identifier: str,
    source_kind: str,
    evidence: dict[str, Any],
    existing_routes: set[str],
) -> dict[str, Any]:
    """Keep Bot language/menu callbacks inside the signed Web profile boundary.

    A Bot language action writes a Telegram-user preference and redraws a Bot
    menu.  The three reviewed Web display catalogs may therefore open only a
    fresh Account page.  They are not browser locale writes: the signed Web
    customer must choose and CSRF-save an allowed profile value independently.
    Every other language action, including opaque formatted values, remains
    source-review-required rather than inheriting a dashboard or account route.
    """

    token = str(identifier or "").casefold()
    if token in INTERFACE_LOCALE_FRESH_WEB_NAVIGATION_ACTIONS:
        target = "/account"
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": target,
            "classification": "customer",
            "status": _mapping_status(target, existing_routes, telegram_only=False, navigation_only=True),
            "resolution": "reviewed_interface_locale_fresh_web_navigation",
            "source_dispositions": INTERFACE_LOCALE_FRESH_WEB_NAVIGATION_DISPOSITIONS,
            "source_evidence": (
                "The reviewed Bot literal changes a Telegram-user language/menu preference. It may only open "
                "a fresh signed Web Account preference page; no Bot locale, Telegram identity, menu, translation "
                "mode, workflow language or pending state reaches the browser, and the Web locale is not changed "
                "until the customer explicitly saves an allowed profile value through CSRF protection."
            ),
            "interface_locale_authority": "SIGNED_CUSTOMER_WEB_PROFILE",
            "interface_locale_launch_mode": "WEB_NAVIGATION",
            "interface_locale_supported_values": ("vi", "en", "zh"),
            "evidence": evidence,
        }

    review_label = (
        "reviewed_interface_locale_callback_requires_source_review"
        if token in INTERFACE_LOCALE_SOURCE_REVIEW_ACTIONS
        else "interface_locale_callback_requires_source_review"
    )
    return {
        "source_kind": source_kind,
        "source": identifier,
        "target": "INTERFACE_LOCALE_SOURCE_REVIEW_REQUIRED",
        "classification": "customer",
        "status": "NEEDS_FEATURE_DISPOSITION",
        "resolution": review_label,
        "source_dispositions": (
            "BOT_INTERFACE_LOCALE_OR_MENU_STATE",
            "SOURCE_STATE_MACHINE_REQUIRED",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "This Bot language/menu action can write a Telegram-user locale, redraw localized Bot UI or return "
            "to Bot menu state. It has no reviewed Web display catalog or signed-profile navigation contract, so "
            "it must not become a browser locale write, translation setting, workflow-language value or route."
        ),
        "evidence": evidence,
    }


def _map_tvflow_callback(identifier: str, source_kind: str, evidence: dict[str, Any]) -> dict[str, Any]:
    """Record a finite Bot trend-video flow without inventing Web parity.

    ``tvflow`` callbacks can look like ordinary content/image/video actions
    while the Bot handler actually relies on private pending workflow/output
    state, canonical package/Xu decisions, provider guards, job state or an
    admin-only smoke path.  Return a symbolic authority boundary so the audit
    cannot upgrade an existing Web route into a false guarded implementation.
    """

    token = str(identifier or "").casefold()
    policy = TVFLOW_CALLBACK_DISPOSITIONS.get(token)
    if policy is None:
        for prefix, prefix_policy in TVFLOW_CALLBACK_PREFIX_DISPOSITIONS:
            if token.startswith(prefix):
                policy = prefix_policy
                break
    if policy is None:
        policy = TVFLOW_DEFAULT_DISPOSITION
    return {
        "source_kind": source_kind,
        "source": identifier,
        "target": str(policy["target"]),
        "classification": str(policy.get("classification") or "customer"),
        "status": str(policy.get("status") or "NEEDS_FEATURE_DISPOSITION"),
        "resolution": str(policy["resolution"]),
        "source_dispositions": [str(value) for value in policy["source_dispositions"]],
        "source_evidence": str(policy["source_evidence"]),
        "evidence": evidence,
    }


def _map_media_preview_callback_template(template: str, evidence: dict[str, Any]) -> dict[str, Any] | None:
    """Record Bot-only preview cache actions without inventing a Web player.

    The template values are not stable resources. The Bot uses them as a
    kind/index lookup into a short-lived Telegram-user cache, then either
    delivers chat media/guidance or mutates Bot selected-media state. A future
    Web catalog may solve the product need independently, but cannot replay
    this callback or use its opaque values as Web identifiers.
    """

    token = str(template or "").casefold()
    policy = MEDIA_PREVIEW_CALLBACK_TEMPLATE_DISPOSITIONS.get(token)
    if policy is None:
        return None
    return {
        "source_kind": "callback_template",
        "source": template,
        "target": str(policy["target"]),
        "classification": "customer",
        "status": str(policy.get("status") or "NEEDS_FEATURE_DISPOSITION"),
        "resolution": str(policy["resolution"]),
        "source_dispositions": [str(value) for value in policy["source_dispositions"]],
        "source_evidence": str(policy["source_evidence"]),
        "evidence": evidence,
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


def _quick_image_planner_fresh_web_mapping(
    identifier: str,
    source_kind: str,
    evidence: dict[str, Any],
    existing_routes: set[str],
) -> dict[str, Any]:
    """Return the fresh Web-native plan boundary for reviewed draft inputs."""

    target = "/image/quick-planner"
    return {
        "source_kind": source_kind,
        "source": identifier,
        "target": target,
        "classification": "customer",
        "status": _mapping_status(target, existing_routes, telegram_only=False),
        "resolution": "reviewed_quick_image_planner_fresh_web_draft",
        "source_dispositions": (
            "FRESH_SIGNED_WEB_NATIVE_DRAFT",
            "BOT_QUICK_IMAGE_CONVERSATION_STATE_NOT_REPLAYED",
            "NO_IMAGE_PROVIDER_JOB_OR_PAYMENT",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The reviewed Quick Image draft callback only advances the Bot's temporary prompt/logo/ratio "
            "conversation. The standalone Web starts an independent signed deterministic Planner and receives "
            "no Telegram callback, selected topic, custom text, watermark, aspect, provider, tier, quote, "
            "confirm token, Bot state, job, Xu, PayOS, asset or delivery context."
        ),
        "quick_image_planner_authority": "SIGNED_CUSTOMER_WEB_NATIVE_DRAFT_ONLY",
        "quick_image_planner_launch_mode": "WEB_FRESH_DRAFT",
        "evidence": evidence,
    }


def _quick_image_planner_telegram_only_mapping(
    identifier: str,
    source_kind: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    """Keep tier and opaque confirmation transitions with the canonical Bot."""

    return {
        "source_kind": source_kind,
        "source": identifier,
        "target": "TELEGRAM_ONLY",
        "classification": "customer",
        "status": "TELEGRAM_ONLY",
        "resolution": "bot_quick_image_tier_or_confirm_requires_canonical_bot_state",
        "source_dispositions": (
            "TELEGRAM_IDENTITY_CONTEXT",
            "BOT_QUICK_IMAGE_TIER_OR_CONFIRM_STATE",
            "CANONICAL_SHOPAI_XU_JOB_OR_PAYMENT_BOUNDARY",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The reviewed Quick Image tier/back/confirm/package branch cancels or consumes a Bot-owned "
            "one-time confirmation and can inspect tier/provider/package/Xu state, create a canonical job, "
            "or begin canonical payment/delivery. The Web Planner has no adapter for those effects."
        ),
        "evidence": evidence,
    }


def _map_quick_image_planner_callback(
    identifier: str,
    source_kind: str,
    evidence: dict[str, Any],
    existing_routes: set[str],
) -> dict[str, Any] | None:
    """Map only finite Quick Image draft tokens; reject execution boundaries."""

    token = str(identifier or "").casefold()
    if token in QUICK_IMAGE_PLANNER_FRESH_WEB_CALLBACKS:
        return _quick_image_planner_fresh_web_mapping(identifier, source_kind, evidence, existing_routes)
    if token.startswith("create_media|qi_logo_pos|"):
        position = token.rsplit("|", 1)[-1]
        if position in QUICK_IMAGE_LOGO_POSITION_VALUES:
            return _quick_image_planner_fresh_web_mapping(identifier, source_kind, evidence, existing_routes)
    if token in QUICK_IMAGE_PLANNER_TELEGRAM_ONLY_CALLBACKS:
        return _quick_image_planner_telegram_only_mapping(identifier, source_kind, evidence)
    return None


def _map_callback(identifier: str, source_kind: str, evidence: dict[str, Any], existing_routes: set[str]) -> dict[str, Any]:
    token = identifier.casefold()
    quick_image_mapping = _map_quick_image_planner_callback(identifier, source_kind, evidence, existing_routes)
    if quick_image_mapping is not None:
        return quick_image_mapping
    if token.startswith("docflow|"):
        return _map_docflow_callback(identifier, source_kind, evidence)
    if token.startswith("archive|"):
        return _map_archive_callback(identifier, source_kind, evidence, existing_routes)
    if token.startswith("tvflow|"):
        return _map_tvflow_callback(identifier, source_kind, evidence)
    if token.startswith("lang|") or token in INTERFACE_LOCALE_SOURCE_REVIEW_ACTIONS:
        return _map_interface_locale_callback(identifier, source_kind, evidence, existing_routes)
    admin = _is_admin_command(token, "")
    telegram_only = _is_telegram_only(token)
    dashboard_fallback = False
    menu_entry = MENU_ACTION_REGISTRY.get(token)
    memory_navigation_entry = MEMORY_FRESH_WEB_NAVIGATION_ACTIONS.get(token)
    marketing_navigation_entry = MARKETING_FRESH_WEB_NAVIGATION_ACTIONS.get(token)
    guided_start_navigation_entry = GUIDED_START_FRESH_WEB_NAVIGATION_ACTIONS.get(token)
    system_data_stewardship_entry = SYSTEM_DATA_STEWARDSHIP_FRESH_WEB_NAVIGATION_ACTIONS.get(token)
    tax_accounting_guidance_entry = TAX_ACCOUNTING_GUIDANCE_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS.get(token)
    tax_accounting_source_review_entry = TAX_ACCOUNTING_CANONICAL_FINANCE_SOURCE_REVIEW_ACTIONS.get(token)
    job_lock_recovery_navigation_entry = JOB_LOCK_RECOVERY_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS.get(token)
    job_lock_recovery_source_review_entry = JOB_LOCK_RECOVERY_CANONICAL_SOURCE_REVIEW_ACTIONS.get(token)
    memory_storage_telegram_only = MEMORY_STORAGE_TELEGRAM_ONLY_ACTIONS.get(token)
    memory_storage_guidance = MEMORY_STORAGE_GUIDANCE_ACTIONS.get(token)
    navigation_only = menu_entry is not None
    operator_category = OPERATOR_MENU_CATEGORY_REGISTRY.get(token)
    pricing_read_entry = PRICING_READ_NAVIGATION_REGISTRY.get(token)
    if system_data_stewardship_entry is not None:
        # This finite audit-only allow-list begins a fresh, independently
        # authorized Web navigation. In particular it wins over a generic
        # storage/help Telegram-only heuristic without replaying any Bot
        # record, command, health check, backup or cleanup effect.
        target = str(system_data_stewardship_entry["target"])
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": target,
            "classification": str(system_data_stewardship_entry["classification"]),
            "status": _mapping_status(target, existing_routes, telegram_only=False, navigation_only=True),
            "resolution": "reviewed_system_data_stewardship_fresh_web_navigation",
            "source_dispositions": tuple(system_data_stewardship_entry["source_dispositions"]),
            "source_evidence": str(system_data_stewardship_entry["source_evidence"]),
            "system_data_stewardship_feature_key": str(system_data_stewardship_entry["feature_key"]),
            "system_data_stewardship_authority": str(system_data_stewardship_entry["authority"]),
            "system_data_stewardship_launch_mode": str(system_data_stewardship_entry["launch_mode"]),
            "evidence": evidence,
        }
    if tax_accounting_guidance_entry is not None:
        # This finite source-review allow-list can only start an independently
        # authorized guidance route. It intentionally wins over any generic
        # finance/tax heuristic without replaying a Bot period, ledger, export
        # path, tax profile, calculation, payment or file delivery effect.
        target = str(tax_accounting_guidance_entry["target"])
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": target,
            "classification": str(tax_accounting_guidance_entry["classification"]),
            "status": _mapping_status(target, existing_routes, telegram_only=False, navigation_only=True),
            "resolution": "reviewed_tax_accounting_guidance_fresh_web_navigation",
            "source_dispositions": tuple(tax_accounting_guidance_entry["source_dispositions"]),
            "source_evidence": str(tax_accounting_guidance_entry["source_evidence"]),
            "tax_accounting_guidance_feature_key": str(tax_accounting_guidance_entry["feature_key"]),
            "tax_accounting_guidance_authority": str(tax_accounting_guidance_entry["authority"]),
            "tax_accounting_guidance_launch_mode": str(tax_accounting_guidance_entry["launch_mode"]),
            "evidence": evidence,
        }
    if tax_accounting_source_review_entry is not None:
        # This is deliberately a finite source-review record, not an admin
        # route. A browser may not reuse Bot calculation/export controls,
        # canonical finance rows, tax profile values or file delivery state.
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": "CANONICAL_TAX_ACCOUNTING_SOURCE_REVIEW_REQUIRED",
            "classification": "admin",
            "status": "NEEDS_FEATURE_DISPOSITION",
            "resolution": "reviewed_tax_accounting_callback_requires_canonical_finance_contract",
            "source_dispositions": _tax_accounting_source_review_dispositions(tax_accounting_source_review_entry),
            "source_evidence": str(tax_accounting_source_review_entry["source_evidence"]),
            "evidence": evidence,
        }
    if job_lock_recovery_navigation_entry is not None:
        # The finite help entry can only begin a fresh, independently
        # authorized safety guide. It intentionally does not replay a Bot job
        # identifier, user, lock/queue state, confirmation, clear/retry/refund
        # decision, worker/provider/runtime payload or financial side effect.
        target = str(job_lock_recovery_navigation_entry["target"])
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": target,
            "classification": str(job_lock_recovery_navigation_entry["classification"]),
            "status": _mapping_status(target, existing_routes, telegram_only=False, navigation_only=True),
            "resolution": "reviewed_job_lock_recovery_fresh_web_navigation",
            "source_dispositions": tuple(job_lock_recovery_navigation_entry["source_dispositions"]),
            "source_evidence": str(job_lock_recovery_navigation_entry["source_evidence"]),
            "job_lock_recovery_feature_key": str(job_lock_recovery_navigation_entry["feature_key"]),
            "job_lock_recovery_authority": str(job_lock_recovery_navigation_entry["authority"]),
            "job_lock_recovery_launch_mode": str(job_lock_recovery_navigation_entry["launch_mode"]),
            "evidence": evidence,
        }
    if job_lock_recovery_source_review_entry is not None:
        # Confirmation/refund descendants remain canonical Bot mutation
        # boundaries. A browser cannot reuse a Telegram confirmation context or
        # its hidden job/user identifiers to clear, retry or refund anything.
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": "CANONICAL_JOB_LOCK_RECOVERY_SOURCE_REVIEW_REQUIRED",
            "classification": "admin",
            "status": "NEEDS_FEATURE_DISPOSITION",
            "resolution": "reviewed_job_lock_recovery_callback_requires_canonical_mutation_contract",
            "source_dispositions": _job_lock_recovery_source_review_dispositions(job_lock_recovery_source_review_entry),
            "source_evidence": str(job_lock_recovery_source_review_entry["source_evidence"]),
            "evidence": evidence,
        }
    if memory_navigation_entry is not None:
        # This is a fresh Web workspace launch, not a translation of the
        # Telegram button. The detailed boundary is kept here rather than in
        # a label/namespace heuristic so Bot state can never leak into the
        # browser even when the destinations happen to share a product name.
        target = str(memory_navigation_entry["target"])
        result = {
            "source_kind": source_kind,
            "source": identifier,
            "target": target,
            "classification": "customer",
            "status": _mapping_status(target, existing_routes, telegram_only=False, navigation_only=True),
            "resolution": "reviewed_memory_fresh_web_navigation",
            "source_dispositions": tuple(memory_navigation_entry["source_dispositions"]),
            "source_evidence": str(memory_navigation_entry["source_evidence"]),
            "memory_capability_key": str(memory_navigation_entry["capability_key"]),
            "memory_feature_key": str(memory_navigation_entry["feature_key"]),
            "memory_authority": str(memory_navigation_entry["authority"]),
            "memory_launch_mode": str(memory_navigation_entry["launch_mode"]),
            "evidence": evidence,
        }
        if menu_entry is not None:
            result["menu_capability_key"] = menu_entry["capability_key"]
            result["menu_feature_key"] = menu_entry["feature_key"]
            result["menu_authority"] = menu_entry["authority"]
            result["menu_launch_mode"] = menu_entry["launch_mode"]
        return result
    if marketing_navigation_entry is not None:
        # Marketing callbacks are only a fresh signed Web launch.  The Bot
        # source stores a per-Telegram conversation, choices and potentially a
        # canonical save/schedule transition; none of those values may cross
        # into the independent Campaign Planner.
        target = "/campaigns"
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": target,
            "classification": "customer",
            "status": _mapping_status(target, existing_routes, telegram_only=False, navigation_only=True),
            "resolution": "reviewed_marketing_fresh_web_navigation",
            "source_dispositions": tuple(marketing_navigation_entry["source_dispositions"]),
            "source_evidence": str(marketing_navigation_entry["source_evidence"]),
            "marketing_capability_key": "campaign_planner",
            "marketing_feature_key": "campaign_planner",
            "marketing_authority": "SIGNED_CUSTOMER_WEB_NATIVE",
            "marketing_launch_mode": "WEB_NAVIGATION",
            "evidence": evidence,
        }
    if guided_start_navigation_entry is not None:
        # The Bot Main Guide owns a second Telegram keyboard and explanatory
        # context. A reviewed Web launch is a new signed route only; it must
        # not turn the guide's child callback graph or support/refund context
        # into browser input or a runtime action.
        target = str(guided_start_navigation_entry["target"])
        result = {
            "source_kind": source_kind,
            "source": identifier,
            "target": target,
            "classification": "customer",
            "status": _mapping_status(target, existing_routes, telegram_only=False, navigation_only=True),
            "resolution": "reviewed_guided_start_fresh_web_navigation",
            "source_dispositions": tuple(guided_start_navigation_entry["source_dispositions"]),
            "source_evidence": str(guided_start_navigation_entry["source_evidence"]),
            "guided_start_capability_key": str(guided_start_navigation_entry["capability_key"]),
            "guided_start_feature_key": str(guided_start_navigation_entry["feature_key"]),
            "guided_start_authority": str(guided_start_navigation_entry["authority"]),
            "guided_start_launch_mode": str(guided_start_navigation_entry["launch_mode"]),
            "evidence": evidence,
        }
        if menu_entry is not None:
            result["menu_capability_key"] = menu_entry["capability_key"]
            result["menu_feature_key"] = menu_entry["feature_key"]
            result["menu_authority"] = menu_entry["authority"]
            result["menu_launch_mode"] = menu_entry["launch_mode"]
        return result
    if memory_storage_telegram_only is not None:
        # Bot quota and add-on purchase are canonical storage/payment state.
        # Do not make a convenient-looking Web Notes, Asset Vault or wallet
        # route stand in for the Bot record or its PayOS settlement path.
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": "TELEGRAM_ONLY",
            "classification": "customer",
            "status": "TELEGRAM_ONLY",
            "resolution": "bot_canonical_memory_storage_requires_adapter",
            "source_dispositions": tuple(memory_storage_telegram_only["source_dispositions"]),
            "source_evidence": str(memory_storage_telegram_only["source_evidence"]),
            "evidence": evidence,
        }
    if memory_storage_guidance is not None:
        # The Bot says this is guidance only; no deletion actually occurs.
        # Preserve that absence of a Web equivalent rather than claiming that
        # archive or Asset Vault retention is a storage-cleanup workflow.
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": "MEMORY_STORAGE_CLEANUP_CONTRACT_REQUIRED",
            "classification": "customer",
            "status": "NEEDS_FEATURE_DISPOSITION",
            "resolution": "bot_storage_cleanup_guidance_requires_web_storage_contract",
            "source_dispositions": tuple(memory_storage_guidance["source_dispositions"]),
            "source_evidence": str(memory_storage_guidance["source_evidence"]),
            "evidence": evidence,
        }
    if token == "payosalert|manual":
        # The Bot emits this only in its owner/admin PayOS-alert keyboards.
        # It creates a short-lived Bot-local manual-bill menu state for that
        # Telegram admin; it does not create an order, write the Xu ledger,
        # call PayOS, or expose a customer top-up action. The Web may only
        # open its independently authenticated admin-payment read surface.
        target = "/admin/payments"
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": target,
            "classification": "admin",
            "status": _mapping_status(target, existing_routes, telegram_only=False, navigation_only=True),
            "resolution": "reviewed_payos_alert_admin_navigation",
            "source_dispositions": (
                "BOT_ADMIN_ONLY",
                "BOT_EPHEMERAL_BILL_STATE_NOT_REPLAYED",
                "FRESH_SIGNED_WEB_ADMIN_NAVIGATION",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The Bot handler first enforces is_admin_user, then stores only a ten-minute "
                "per-admin USER_BILL_STATE and redraws the Telegram manual-payment menu. "
                "The Web opens a fresh role-checked admin view and receives no Bot state."
            ),
            "evidence": evidence,
        }
    if token in PAYOS_ALERT_TELEGRAM_ONLY_CALLBACKS:
        # These exact values are Bot-admin alert controls rather than
        # customer payment actions. Keep each source effect explicit; no
        # prefix wildcard may convert a later Bot alert into a Web control.
        contract = PAYOS_ALERT_TELEGRAM_ONLY_CALLBACKS[token]
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": "TELEGRAM_ONLY",
            "classification": "admin",
            "status": "TELEGRAM_ONLY",
            "resolution": "reviewed_payos_alert_telegram_admin_only",
            "source_dispositions": list(contract["source_dispositions"]),
            "source_evidence": str(contract["source_evidence"]),
            "evidence": evidence,
        }
    if token.startswith("payosalert|"):
        # The registered Bot handler accepts the namespace broadly, but only
        # the finite literals above are source-reviewed. A future callback
        # could mutate canonical alert/payment/deployment state, so it cannot
        # inherit the customer dashboard or the admin payment route.
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": "PAYOS_ALERT_SOURCE_REVIEW_REQUIRED",
            "classification": "admin",
            "status": "NEEDS_FEATURE_DISPOSITION",
            "resolution": "payos_alert_callback_requires_source_review",
            "source_dispositions": (
                "BOT_ADMIN_ONLY",
                "CANONICAL_BOT_PAYOS_ALERT_FLOW",
                "SOURCE_STATE_MACHINE_REQUIRED",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The Bot registers a broad payosalert dispatcher, but a new action has no reviewed "
                "source branch. It must not become a Web payment, provider, environment, or alert action."
            ),
            "evidence": evidence,
        }
    if token in PACKAGE_PURCHASE_SELECTOR_CALLBACKS:
        # These finite Bot buttons validate one catalog entry and display a
        # Telegram detail/confirmation screen. The standalone Web opens its
        # own signed package catalog without accepting the Bot type/code,
        # Telegram identity, message, price, entitlement, or next action.
        target = "/packages"
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": target,
            "classification": "customer",
            "status": _mapping_status(target, existing_routes, telegram_only=False, navigation_only=True),
            "resolution": "reviewed_package_catalog_selector_navigation",
            "source_dispositions": (
                "FRESH_SIGNED_WEB_NAVIGATION",
                "BOT_CATALOG_SELECTION_NOT_REPLAYED",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The Bot selector validates a catalog entry and redraws a Telegram detail with a later "
                "confirmation button. The Web loads its own current signed catalog and never receives the "
                "Bot package type/code, Telegram state, price, entitlement, or checkout action."
            ),
            "evidence": evidence,
        }
    if token.startswith("pkgbuy|"):
        # A new literal may be a catalog selector, support-only/manual path,
        # or canonical checkout transition. It needs a finite source review;
        # it cannot inherit either the Web catalog or the Xu top-up route.
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": "PACKAGE_PURCHASE_SOURCE_REVIEW_REQUIRED",
            "classification": "customer",
            "status": "NEEDS_FEATURE_DISPOSITION",
            "resolution": "package_purchase_callback_requires_source_review",
            "source_dispositions": (
                "CANONICAL_PACKAGE_PURCHASE_SOURCE_REVIEW",
                "SOURCE_STATE_MACHINE_REQUIRED",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The Bot package namespace contains both read-only catalog selectors and a canonical "
                "PayOS checkout branch. An unreviewed value cannot become a Web package, wallet, payment, "
                "order, entitlement, or provider action."
            ),
            "evidence": evidence,
        }
    if token == VIDEO_JOB_STATS_CALLBACK:
        # This one callback is emitted by the admin-only video-job keyboard
        # and only redraws canonical Bot stats. A fresh signed admin surface
        # may expose its independently authorized bridge projection, but it
        # never receives the Bot Telegram owner, job rows or callback state.
        target = "/admin/jobs"
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": target,
            "classification": "admin",
            "status": _mapping_status(target, existing_routes, telegram_only=False, navigation_only=True),
            "resolution": "reviewed_video_job_stats_admin_navigation",
            "source_dispositions": (
                "BOT_ADMIN_ONLY",
                "BOT_VIDEO_JOB_STATS_NOT_REPLAYED",
                "FRESH_SIGNED_WEB_ADMIN_NAVIGATION",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The Bot video-job handler first enforces is_admin_user. Its stats branch reads canonical "
                "campaign/video_job counts for the Telegram admin and redraws the Telegram message; the Web "
                "opens a fresh role-checked admin view without receiving Bot rows or callback context."
            ),
            "evidence": evidence,
        }
    if token.startswith("job|"):
        # This namespace includes canonical status mutations. A future static
        # value cannot inherit either the customer jobs screen or admin stats.
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": "BOT_VIDEO_JOB_SOURCE_REVIEW_REQUIRED",
            "classification": "admin",
            "status": "NEEDS_FEATURE_DISPOSITION",
            "resolution": "video_job_callback_requires_source_review",
            "source_dispositions": (
                "BOT_ADMIN_ONLY",
                "CANONICAL_BOT_VIDEO_JOB_STATE",
                "SOURCE_STATE_MACHINE_REQUIRED",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The Bot job namespace belongs to the admin-only video-job state machine. An unreviewed value "
                "must not become a customer route, browser job ID, canonical read, or job mutation."
            ),
            "evidence": evidence,
        }
    if token in STORAGE_ADDON_TELEGRAM_ONLY_CALLBACKS:
        # These finite customer callbacks belong to a Telegram-only storage
        # purchase conversation. They must not inherit /wallet/topup or a
        # browser storage catalog because neither carries the Bot state safely.
        contract = STORAGE_ADDON_TELEGRAM_ONLY_CALLBACKS[token]
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": "TELEGRAM_ONLY",
            "classification": "customer",
            "status": "TELEGRAM_ONLY",
            "resolution": "reviewed_storage_addon_telegram_only",
            "source_dispositions": list(contract["source_dispositions"]),
            "source_evidence": str(contract["source_evidence"]),
            "evidence": evidence,
        }
    if token.startswith("storage|"):
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": "STORAGE_ADDON_SOURCE_REVIEW_REQUIRED",
            "classification": "customer",
            "status": "NEEDS_FEATURE_DISPOSITION",
            "resolution": "storage_addon_callback_requires_source_review",
            "source_dispositions": (
                "CANONICAL_BOT_STORAGE_ADDON_SOURCE_REVIEW",
                "SOURCE_STATE_MACHINE_REQUIRED",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The Bot storage namespace contains Telegram pending input and canonical payment/quota state. "
                "An unreviewed value cannot become a Web storage request, wallet top-up, order, checkout, "
                "quota entitlement, provider action, or output claim."
            ),
            "evidence": evidence,
        }
    if token in VIDEO_FINALIZATION_TELEGRAM_ONLY_CALLBACKS:
        # These values only make sense inside the Bot finalization session.
        # In particular, a choice such as tier, aspect, music or export is not
        # safe to detach from its Telegram identity, pending media/text, quote
        # and canonical execution guards.
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": "TELEGRAM_ONLY",
            "classification": "customer",
            "status": "TELEGRAM_ONLY",
            "resolution": "reviewed_video_finalization_telegram_only",
            "source_dispositions": (
                "TELEGRAM_IDENTITY_CONTEXT",
                "BOT_VIDEO_FINALIZATION_SESSION_STATE",
                "BOT_PENDING_MEDIA_OR_TEXT_STATE",
                "CANONICAL_VIDEO_EXPORT_AND_PAYMENT_GUARDS",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The Bot vfinal handler resolves this callback against a per-Telegram-user finalization "
                "session and can update choices, selected media/input, quote/package state or guarded export "
                "paths. The separately authenticated Web Video Finishing workflow cannot replay the callback "
                "or accept its Bot state as a browser action."
            ),
            "evidence": evidence,
        }
    if token.startswith("vfinal|"):
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": "VIDEO_FINALIZATION_SOURCE_REVIEW_REQUIRED",
            "classification": "customer",
            "status": "NEEDS_FEATURE_DISPOSITION",
            "resolution": "video_finalization_callback_requires_source_review",
            "source_dispositions": (
                "BOT_VIDEO_FINALIZATION_SESSION_STATE",
                "SOURCE_STATE_MACHINE_REQUIRED",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The Bot vfinal namespace mixes draft choices with pending Telegram media/text, selected-media "
                "state, provider/readiness checks, quote/package rules and guarded exports. An unreviewed value "
                "cannot become a Web route, asset reference, render/export, provider, wallet or payment action."
            ),
            "evidence": evidence,
        }
    if token in PROFILE_REFERRAL_TELEGRAM_ONLY_ACTIONS:
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": "TELEGRAM_ONLY",
            "classification": "customer",
            "status": "TELEGRAM_ONLY",
            "resolution": "profile_referral_requires_canonical_bot_adapter",
            "source_dispositions": (
                "BOT_TELEGRAM_DEEP_LINK_IDENTITY",
                "BOT_CANONICAL_REFERRAL_REWARD_STATE",
                "NO_WEB_REFERRAL_READ_ADAPTER",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The Bot profile callback derives a Telegram referral deep link or reads referral "
                "statistics/policy backed by canonical member and reward state. The Web has no "
                "reviewed internal referral adapter, so it cannot mint a link or render rewards."
            ),
            "evidence": evidence,
        }
    if token in MENU_TRANSLATION_TELEGRAM_ONLY_ACTIONS:
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": "TELEGRAM_ONLY",
            "classification": "customer",
            "status": "TELEGRAM_ONLY",
            "resolution": "translation_session_requires_web_owned_contract",
            "source_dispositions": (
                "TELEGRAM_IDENTITY_CONTEXT",
                "BOT_TRANSLATION_SESSION_OR_PREFERENCE_STATE",
                "BOT_PENDING_TEXT_OR_MEDIA_STATE",
                "PROVIDER_GUARD_OR_TTS_PATH",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The Bot callback changes a per-Telegram-user translation session, language preference, "
                "pending text/media or provider-gated voice output. Web Subtitle Studio starts an independent "
                "signed authoring workspace and cannot accept these Bot values or claim translation/TTS output."
            ),
            "evidence": evidence,
        }
    if token in TRANSLATION_VIDEO_MENU_DEFERRED_ACTIONS:
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": "VIDEO_TRANSLATION_MENU_DEFERRED",
            "classification": "customer",
            "status": "NEEDS_FEATURE_DISPOSITION",
            "resolution": "translation_video_factory_deferred_until_video_menu_phase",
            "source_dispositions": (
                "TELEGRAM_IDENTITY_CONTEXT",
                "BOT_VIDEO_DUBBING_PENDING_STATE",
                "VIDEO_MENU_LAST",
                "SOURCE_STATE_MACHINE_REQUIRED",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The Bot translation-video entry creates a pending video dubbing state and later reaches "
                "voice/provider/output controls. It is deferred with the final Video menu rather than opening "
                "a generic browser dubbing route without a verified owner-scoped source contract."
            ),
            "evidence": evidence,
        }
    if pricing_read_entry is not None:
        target = pricing_read_entry["target"]
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": target,
            "classification": "customer",
            "status": _mapping_status(target, existing_routes, telegram_only=False, navigation_only=True),
            "resolution": "reviewed_pricing_read_navigation",
            "source_dispositions": (
                "BOT_INFORMATION_PANEL_NOT_REPLAYED",
                "FRESH_SIGNED_WEB_CANONICAL_READ"
                if pricing_read_entry["authority"] == "CORE_CANONICAL_READ"
                else "FRESH_SIGNED_WEB_INFORMATION_NAVIGATION",
                "NO_PURCHASE_OR_ENTITLEMENT_ACTION",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The reviewed Bot pricing branch renders a static pricing, package, tier, VIP or Xu "
                "information panel. The Web opens a fresh signed destination with the authority "
                "declared by this exact catalog entry; it does not carry a Bot selector, pending "
                "purchase or confirmation state."
            ),
            "pricing_capability_key": pricing_read_entry["capability_key"],
            "pricing_feature_key": pricing_read_entry["feature_key"],
            "pricing_authority": pricing_read_entry["authority"],
            "pricing_launch_mode": pricing_read_entry["launch_mode"],
            "evidence": evidence,
        }
    if operator_category is not None:
        # A category opens only the independently protected ERP *directory*.
        # It does not replay a Telegram command snippet, preserve Bot context,
        # or create an Operator API, worker, provider, payment, publish or
        # video-production action in the browser.
        target = operator_category["target"]
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": target,
            "classification": "admin",
            "status": _mapping_status(target, existing_routes, telegram_only=False, navigation_only=True),
            "resolution": "reviewed_operator_menu_category_navigation",
            "source_dispositions": (
                "BOT_ADMIN_ONLY",
                "BOT_COMMAND_SNIPPET_NOT_REPLAYED",
                "FRESH_SIGNED_WEB_ADMIN_NAVIGATION",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The Bot callback checks ADMIN_ID, then renders a category of command snippets. "
                "The Web destination starts a fresh signed Admin ERP session and independently "
                "checks canonical role, route authorization, CSRF and each module contract."
            ),
            "operator_category_title": operator_category["title"],
            "operator_admin_feature_key": operator_category["admin_feature_key"],
            "evidence": evidence,
        }
    if token in OPERATOR_MENU_DEFERRED_CATEGORIES:
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": "VIDEO_ADMIN_MENU_DEFERRED",
            "classification": "admin",
            "status": "NEEDS_FEATURE_DISPOSITION",
            "resolution": "operator_production_category_deferred_until_video_menu_phase",
            "source_dispositions": (
                "BOT_ADMIN_ONLY",
                "BOT_VIDEO_PRODUCTION_COMMANDS",
                "VIDEO_MENU_LAST",
                "SOURCE_STATE_MACHINE_REQUIRED",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The production category contains video creation, film, worker, output, review and "
                "render-related command snippets. It remains explicitly deferred until the final "
                "finite Video menu catalog, rather than inheriting an Admin or Job route."
            ),
            "evidence": evidence,
        }
    if token in GUIDED_VIDEO_MENU_DEFERRED_ACTIONS:
        # These look like simple guide links in Telegram, but each opens a
        # Bot-owned video/trend branch with pending state and later provider,
        # output and canonical billing boundaries. Keep them visible in the
        # migration report while the final Video menu is intentionally last.
        return {
            "source_kind": source_kind,
            "source": identifier,
            "target": "GUIDED_VIDEO_MENU_DEFERRED",
            "classification": "customer",
            "status": "NEEDS_FEATURE_DISPOSITION",
            "resolution": "guided_video_menu_deferred_until_video_menu_phase",
            "source_dispositions": (
                "BOT_GUIDE_SECTION_CONTEXT_NOT_REPLAYED",
                "BOT_GUIDE_CHILD_CALLBACKS_NOT_REPLAYED",
                "VIDEO_MENU_LAST",
                "SOURCE_STATE_MACHINE_REQUIRED",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The frozen Bot Main Guide opens a video or trend guide section whose child buttons enter "
                "Bot-owned pending-media, provider, output and canonical payment/job paths. It must not "
                "fall back to Dashboard or become a generic browser video route before the finite Video "
                "menu phase establishes a separate owner-scoped Web contract."
            ),
            "evidence": evidence,
        }
    if menu_entry is not None:
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
        # A finite catalog entry is reviewed as a customer navigation before
        # keyword heuristics run. For example, the public Bot help button
        # ``menu|hint_pricing`` contains an admin-like word but never grants
        # an admin surface in Web. The catalog currently contains only
        # customer destinations; a future admin action needs its own explicit
        # role-reviewed contract rather than a name-based inference.
        "classification": "customer" if menu_entry is not None else "admin" if admin else "customer",
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

    if record.get("resolution") not in {
        "reviewed_literal_prefix_helper_calls",
        "reviewed_quick_image_logo_position_helper_calls",
    }:
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
        "resolution": str(record.get("resolution") or "reviewed_literal_prefix_helper_calls"),
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
    if token.startswith("archive|"):
        # Dynamic Archive suffixes can encode Bot department/type/search state
        # or identifiers.  Keep all of them fail-closed instead of inheriting
        # the generic Admin route or a finite Archive directory literal.
        return _map_archive_callback(template, "callback_template", evidence, existing_routes)
    if token.startswith("lang|"):
        # Formatted language suffixes are opaque Bot state. Only the exact
        # reviewed literals are handled above by _map_callback; a template
        # must remain an explicit source-review boundary.
        return _map_interface_locale_callback(template, "callback_template", evidence, existing_routes)
    if token in QUICK_IMAGE_PLANNER_FRESH_WEB_CALLBACK_TEMPLATES:
        return _quick_image_planner_fresh_web_mapping(template, "callback_template", evidence, existing_routes)
    if token in QUICK_IMAGE_PLANNER_TELEGRAM_ONLY_CALLBACK_TEMPLATES:
        return _quick_image_planner_telegram_only_mapping(template, "callback_template", evidence)
    if token in MEMORY_RECORD_TELEGRAM_ONLY_CALLBACK_TEMPLATES:
        # These callbacks embed a Bot note identifier. `delete_yes` is a
        # canonical Bot write, while view/delete resolve the same Bot row for
        # a Telegram user. A signed Web Memory Center owns different UUIDs and
        # must never accept, look up or mutate this opaque value.
        mutation = token == "memory|delete_yes|{*}"
        return {
            "source_kind": "callback_template",
            "source": template,
            "target": "TELEGRAM_ONLY",
            "classification": "customer",
            "status": "TELEGRAM_ONLY",
            "resolution": "bot_memory_record_identifier_requires_telegram_context",
            "source_dispositions": (
                "TELEGRAM_IDENTITY_CONTEXT",
                "BOT_MEMORY_NOTE_IDENTIFIER",
                "BOT_MEMORY_RECORD_STATE",
                *( ("CANONICAL_BOT_MEMORY_MUTATION",) if mutation else () ),
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The Bot template resolves an opaque memory note ID against its Telegram-owned table"
                + (" and mutates the canonical Bot record." if mutation else ".")
                + " The Web never accepts the ID or replays that state."
            ),
            "evidence": evidence,
        }
    if token.startswith("memory|"):
        # A future Memory template must be source-reviewed. It may carry a
        # record identifier, delete transition, pending text/query or other
        # Bot-local state, so it cannot inherit /notes merely from the prefix.
        return {
            "source_kind": "callback_template",
            "source": template,
            "target": "BOT_MEMORY_SOURCE_REVIEW_REQUIRED",
            "classification": "customer",
            "status": "NEEDS_FEATURE_DISPOSITION",
            "resolution": "memory_callback_template_requires_source_review",
            "source_dispositions": (
                "BOT_MEMORY_STATE_OR_IDENTIFIER_SOURCE_REVIEW",
                "SOURCE_STATE_MACHINE_REQUIRED",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The Bot Memory namespace can include per-Telegram note IDs, pending input, search state "
                "or canonical mutations. A new dynamic value must be reviewed before it gains any Web meaning."
            ),
            "evidence": evidence,
        }
    if token.startswith("marketing|"):
        # A dynamic marketing value can carry a Bot suggestion index, campaign
        # identifier, pending custom text, save/schedule transition or another
        # piece of Telegram-local conversation state.  It may never inherit a
        # browser meaning merely because a finite literal can open a fresh Web
        # Campaign Planner.
        return {
            "source_kind": "callback_template",
            "source": template,
            "target": "MARKETING_SOURCE_REVIEW_REQUIRED",
            "classification": "customer",
            "status": "NEEDS_FEATURE_DISPOSITION",
            "resolution": "marketing_callback_template_requires_source_review",
            "source_dispositions": (
                "BOT_MARKETING_STATE_OR_IDENTIFIER_SOURCE_REVIEW",
                "SOURCE_STATE_MACHINE_REQUIRED",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "A new dynamic marketing callback may encode Bot suggestions, selected campaign state, "
                "pending custom text or canonical save/schedule context. It must receive source review "
                "before it has any independent Web contract."
            ),
            "evidence": evidence,
        }
    if token.startswith("tvflow|"):
        # Dynamic trend-video values include Bot job, scene and choice context.
        # Preserve the family-specific source boundary rather than allowing a
        # generic dynamic namespace route to imply Web ownership of that state.
        return _map_tvflow_callback(template, "callback_template", evidence)
    if token in TRANSLATION_SESSION_TELEGRAM_ONLY_CALLBACK_TEMPLATES:
        return {
            "source_kind": "callback_template",
            "source": template,
            "target": "TELEGRAM_ONLY",
            "classification": "customer",
            "status": "TELEGRAM_ONLY",
            "resolution": "translation_session_template_requires_web_owned_contract",
            "source_dispositions": (
                "TELEGRAM_IDENTITY_CONTEXT",
                "BOT_TRANSLATION_PAIR_DRAFT_STATE",
                "BOT_TRANSLATION_SESSION_STATE",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The dynamic value selects, swaps, starts or returns to a Bot translation-pair draft for "
                "one Telegram user. A Web workspace cannot receive that opaque mode/value or infer a "
                "translation result, session, provider action or output."
            ),
            "evidence": evidence,
        }
    if token in VIDEO_FINALIZATION_TELEGRAM_ONLY_CALLBACK_TEMPLATES:
        return {
            "source_kind": "callback_template",
            "source": template,
            "target": "TELEGRAM_ONLY",
            "classification": "customer",
            "status": "TELEGRAM_ONLY",
            "resolution": "reviewed_video_finalization_telegram_only",
            "source_dispositions": (
                "TELEGRAM_IDENTITY_CONTEXT",
                "BOT_VIDEO_FINALIZATION_SESSION_STATE",
                "BOT_PENDING_MEDIA_OR_TEXT_STATE",
                "CANONICAL_VIDEO_EXPORT_AND_PAYMENT_GUARDS",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The Bot vfinal tier value is applied only inside a per-Telegram-user finalization session, "
                "then proceeds through package, readiness and guarded export paths. The Web cannot accept the "
                "Bot tier value, quote, pending state or next action."
            ),
            "evidence": evidence,
        }
    if token.startswith("vfinal|"):
        return {
            "source_kind": "callback_template",
            "source": template,
            "target": "VIDEO_FINALIZATION_SOURCE_REVIEW_REQUIRED",
            "classification": "customer",
            "status": "NEEDS_FEATURE_DISPOSITION",
            "resolution": "video_finalization_callback_requires_source_review",
            "source_dispositions": (
                "BOT_VIDEO_FINALIZATION_SESSION_STATE",
                "SOURCE_STATE_MACHINE_REQUIRED",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The Bot vfinal namespace contains per-Telegram-user finalization state and guarded render/export "
                "transitions. An unreviewed dynamic value cannot become a Web draft, asset, quote, render/export, "
                "provider, wallet or payment action."
            ),
            "evidence": evidence,
        }
    media_preview_mapping = _map_media_preview_callback_template(template, evidence)
    if media_preview_mapping is not None:
        return media_preview_mapping
    if token == PACKAGE_PURCHASE_CONFIRM_CALLBACK_TEMPLATE:
        # This one Bot f-string is the canonical package-payment transition:
        # it creates a pending Bot order, calls PayOS, records checkout state
        # and later settles entitlement through the canonical webhook. The
        # Web's top-up API deliberately accepts only topup_xu, so neither a
        # browser checkout nor /wallet/topup is an equivalent destination.
        return {
            "source_kind": "callback_template",
            "source": template,
            "target": "TELEGRAM_ONLY",
            "classification": "customer",
            "status": "TELEGRAM_ONLY",
            "resolution": "bot_canonical_package_checkout",
            "source_dispositions": (
                "TELEGRAM_IDENTITY_CONTEXT",
                "CANONICAL_BOT_ORDER_REQUIRED",
                "CANONICAL_BOT_PAYOS_CHECKOUT",
                "CANONICAL_PACKAGE_ENTITLEMENT_SETTLEMENT",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The Bot confirm branch calls start_package_purchase, which can create a pending order, "
                "call PayOS, record checkout information and later grant package entitlement only after "
                "canonical settlement. The Web has no approved package-purchase bridge contract."
            ),
            "evidence": evidence,
        }
    if token.startswith("pkgbuy|"):
        # Do not recover a dynamic suffix as a catalog item or checkout input.
        # A later Bot callback requires a finite source review before it may
        # gain any Web representation.
        return {
            "source_kind": "callback_template",
            "source": template,
            "target": "PACKAGE_PURCHASE_SOURCE_REVIEW_REQUIRED",
            "classification": "customer",
            "status": "NEEDS_FEATURE_DISPOSITION",
            "resolution": "package_purchase_callback_requires_source_review",
            "source_dispositions": (
                "CANONICAL_PACKAGE_PURCHASE_SOURCE_REVIEW",
                "SOURCE_STATE_MACHINE_REQUIRED",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The Bot package namespace combines catalog selection and canonical checkout/entitlement "
                "state. An unreviewed dynamic suffix cannot become a Web catalog, wallet or payment action."
            ),
            "evidence": evidence,
        }
    if token in VIDEO_JOB_MUTATION_CALLBACK_TEMPLATES:
        # These dynamic callbacks carry a canonical Bot video-job identifier.
        # The Bot first checks admin authority, then resolves the job against
        # its Bot owner before changing the canonical status. The Web must not
        # accept that identifier or synthesize an approve/cancel operation.
        return {
            "source_kind": "callback_template",
            "source": template,
            "target": "TELEGRAM_ONLY",
            "classification": "admin",
            "status": "TELEGRAM_ONLY",
            "resolution": "bot_canonical_video_job_mutation",
            "source_dispositions": (
                "BOT_ADMIN_ONLY",
                "CANONICAL_BOT_JOB_MUTATION",
                "OWNER_SCOPED_BOT_JOB_REQUIRED",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The Bot video-job handler rejects non-admin callers, resolves the job by canonical ID and "
                "Telegram owner, then updates approved/cancelled status in the Bot database. No Web mutation "
                "bridge has been reviewed for this workflow."
            ),
            "evidence": evidence,
        }
    if token.startswith("job|"):
        return {
            "source_kind": "callback_template",
            "source": template,
            "target": "BOT_VIDEO_JOB_SOURCE_REVIEW_REQUIRED",
            "classification": "admin",
            "status": "NEEDS_FEATURE_DISPOSITION",
            "resolution": "video_job_callback_requires_source_review",
            "source_dispositions": (
                "BOT_ADMIN_ONLY",
                "CANONICAL_BOT_VIDEO_JOB_STATE",
                "SOURCE_STATE_MACHINE_REQUIRED",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The Bot job namespace contains canonical video-job state. An unreviewed dynamic value cannot "
                "become a browser job lookup, admin mutation, customer route, or runtime-success claim."
            ),
            "evidence": evidence,
        }
    if token == STORAGE_ADDON_CONFIRM_CALLBACK_TEMPLATE:
        return {
            "source_kind": "callback_template",
            "source": template,
            "target": "TELEGRAM_ONLY",
            "classification": "customer",
            "status": "TELEGRAM_ONLY",
            "resolution": "bot_canonical_storage_addon_checkout",
            "source_dispositions": (
                "TELEGRAM_IDENTITY_CONTEXT",
                "CANONICAL_BOT_STORAGE_ORDER_REQUIRED",
                "CANONICAL_BOT_PAYOS_CHECKOUT",
                "CANONICAL_STORAGE_ENTITLEMENT_SETTLEMENT",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The Bot storage confirm branch validates a Bot catalog spec, can create a pending canonical "
                "storage order and PayOS checkout, and grants storage quota only after canonical settlement. "
                "The Web has no approved owner-scoped storage-purchase bridge contract."
            ),
            "evidence": evidence,
        }
    if token.startswith("storage|"):
        return {
            "source_kind": "callback_template",
            "source": template,
            "target": "STORAGE_ADDON_SOURCE_REVIEW_REQUIRED",
            "classification": "customer",
            "status": "NEEDS_FEATURE_DISPOSITION",
            "resolution": "storage_addon_callback_requires_source_review",
            "source_dispositions": (
                "CANONICAL_BOT_STORAGE_ADDON_SOURCE_REVIEW",
                "SOURCE_STATE_MACHINE_REQUIRED",
                "NO_RUNTIME_CLAIM",
            ),
            "source_evidence": (
                "The Bot storage namespace combines Telegram pending input with canonical PayOS/quota state. "
                "An unreviewed dynamic value cannot become a Web catalog, top-up, order, checkout, quota, "
                "or provider action."
            ),
            "evidence": evidence,
        }
    if token == FREE_HUB_LIBRARY_CATEGORY_CALLBACK_TEMPLATE:
        # The finite Bot suffix selects one global prompt-library suggestion
        # set and then writes a short-lived Telegram pending selection.  The
        # Web opens an independent, signed, read-only Gallery from its own
        # static snapshot.  It never receives the raw suffix, resolves Bot
        # suggestions, or recreates the Telegram pending/result state.
        target = "/free-prompt-gallery"
        return {
            "source_kind": "callback_template",
            "source": template,
            "target": target,
            "classification": "customer",
            "status": _mapping_status(
                target,
                existing_routes,
                telegram_only=False,
                navigation_only=True,
            ),
            "resolution": "reviewed_freehub_library_category_navigation",
            "source_dispositions": [
                "FRESH_SIGNED_WEB_NAVIGATION",
                "BOT_PENDING_STATE_NOT_REPLAYED",
                "NO_RUNTIME_CLAIM",
            ],
            "source_evidence": (
                "The Bot uses a finite category value only to choose global prompt-library "
                "suggestions before storing temporary Telegram pending state. The Web opens "
                "its own signed Free Prompt Gallery and never accepts that value as a Bot "
                "state, prompt ID, query parameter, or browser identifier."
            ),
            "evidence": evidence,
        }
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
    if lowered in MEDIA_PREVIEW_CALLBACK_TEMPLATE_DISPOSITIONS:
        return "media_preview"
    if lowered == "menu_affiliate" or lowered.startswith("affiliate_"):
        return "affiliate"
    if lowered == "menu_freelance" or lowered.startswith("freelance_"):
        return "freelance"
    if lowered == "menu_mxh" or lowered.startswith("mxh_"):
        return "social_navigation"
    if lowered.startswith("lang|") or lowered in {"back_lang", "lang_more"}:
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
    # A finite source family such as docflow can carry stricter per-token
    # evidence than its backlog-level default.  Preserve that detail so a
    # generic family policy cannot erase a semantic mismatch or Bot-state
    # boundary during report generation.
    if source_dispositions and not item.get("source_dispositions"):
        item["source_dispositions"] = source_dispositions
    if source_evidence and not item.get("source_evidence"):
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
                "reason": "Schema 1.7 retains the 1.6 inventory corrections and records the finite Free Hub prompt-library category template as fresh signed Gallery navigation only; its Bot suggestion and pending state are not Web contracts.",
                "scope_changes": [
                    "CallbackQueryHandler registrations are Telegram transport evidence, not product actions.",
                    "Records from unreferenced handlers/ package files remain evidence-only instead of mapped/guarded runtime parity.",
                    "Bare N:N tuple values are treated as aspect-ratio configuration, while numeric-leading structured callbacks remain supported.",
                    "Embedded formatted callback values such as family_action_{*}_{*} are retained as opaque templates instead of being dropped from the static inventory.",
                    "tvflow callbacks are finite Bot-state dispositions instead of generic image/video/content/package route matches.",
                    "Dynamic media-preview callback templates are typed Bot-state dispositions instead of unresolved Web media actions.",
                    "The finite Free Hub prompt-library category template opens a fresh signed Web Gallery as navigation-only; it does not carry a Bot category token, suggestion set, or pending state into the browser.",
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
                "Schema 1.7 coverage percentages are NOT_COMPARABLE_TO_PREVIOUS_AUDIT_PERCENTAGES because the audit retains opaque callback templates, corrects false Web implications for Bot-only media-preview cache/delivery/selection callbacks, and records the finite Free Hub category template only as fresh Gallery navigation; a percentage delta is not feature progress.",
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
    audit_source = preflight.get("bot", {}).get("audit_source", {})
    audit_source_mode = str(audit_source.get("mode") or "working_tree_fallback")
    audit_source_revision = str(audit_source.get("revision") or "unavailable")
    audit_source_files = int(audit_source.get("files_materialized") or 0)
    if audit_source_mode == "git_baseline_snapshot":
        revision_summary = (
            f"- Bot source audited: static Git baseline snapshot `{audit_source_revision}` "
            f"(`{audit_source_files}` source files; working tree not used as source evidence)\n"
            f"- Bot checkout observed for drift only: `{checkout_sha}` (`{relation}`)\n"
        )
    else:
        revision_summary = f"- Bot source audited: working-tree fallback `{checkout_sha}` (`{relation}`)\n"
    if ahead is not None or behind is not None:
        revision_summary += f"- Bot drift versus requested baseline: ahead `{ahead if ahead is not None else 'unknown'}`, behind `{behind if behind is not None else 'unknown'}` commits\n"

    def write(name: str, content: str) -> None:
        path = docs_dir / name
        _write_text(path, _sanitize(content))
        generated.append(path)

    tvflow_contract_rows = [
        [
            source,
            str(policy["target"]),
            str(policy["resolution"]),
            str(policy.get("status") or "NEEDS_FEATURE_DISPOSITION"),
            ", ".join(str(value) for value in policy["source_dispositions"]),
        ]
        for source, policy in TVFLOW_CALLBACK_DISPOSITIONS.items()
    ] + [
        [
            f"{prefix}*",
            str(policy["target"]),
            str(policy["resolution"]),
            str(policy.get("status") or "NEEDS_FEATURE_DISPOSITION"),
            ", ".join(str(value) for value in policy["source_dispositions"]),
        ]
        for prefix, policy in TVFLOW_CALLBACK_PREFIX_DISPOSITIONS
    ] + [
        [
            "other tvflow|*",
            str(TVFLOW_DEFAULT_DISPOSITION["target"]),
            str(TVFLOW_DEFAULT_DISPOSITION["resolution"]),
            "NEEDS_FEATURE_DISPOSITION",
            ", ".join(str(value) for value in TVFLOW_DEFAULT_DISPOSITION["source_dispositions"]),
        ]
    ]
    media_preview_contract_rows = [
        [
            source,
            str(policy["target"]),
            str(policy["resolution"]),
            str(policy.get("status") or "NEEDS_FEATURE_DISPOSITION"),
            ", ".join(str(value) for value in policy["source_dispositions"]),
        ]
        for source, policy in MEDIA_PREVIEW_CALLBACK_TEMPLATE_DISPOSITIONS.items()
    ]
    payos_alert_contract_rows = [
        [
            "payosalert|manual",
            "/admin/payments",
            "reviewed_payos_alert_admin_navigation",
            "NAVIGATION_ONLY",
            "BOT_ADMIN_ONLY, BOT_EPHEMERAL_BILL_STATE_NOT_REPLAYED, FRESH_SIGNED_WEB_ADMIN_NAVIGATION, NO_RUNTIME_CLAIM",
        ],
    ] + [
        [
            source,
            "TELEGRAM_ONLY",
            "reviewed_payos_alert_telegram_admin_only",
            "TELEGRAM_ONLY",
            ", ".join(str(value) for value in policy["source_dispositions"]),
        ]
        for source, policy in PAYOS_ALERT_TELEGRAM_ONLY_CALLBACKS.items()
    ] + [
        [
            "other payosalert|*",
            "PAYOS_ALERT_SOURCE_REVIEW_REQUIRED",
            "payos_alert_callback_requires_source_review",
            "NEEDS_FEATURE_DISPOSITION",
            "BOT_ADMIN_ONLY, CANONICAL_BOT_PAYOS_ALERT_FLOW, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM",
        ],
    ]
    package_purchase_selector_sources = ", ".join(
        f"`{source}`" for source in sorted(PACKAGE_PURCHASE_SELECTOR_CALLBACKS)
    )
    package_purchase_contract_rows = [
        [
            "nine exact package selectors",
            "/packages",
            "reviewed_package_catalog_selector_navigation",
            "NAVIGATION_ONLY",
            "FRESH_SIGNED_WEB_NAVIGATION, BOT_CATALOG_SELECTION_NOT_REPLAYED, NO_RUNTIME_CLAIM",
        ],
        [
            PACKAGE_PURCHASE_CONFIRM_CALLBACK_TEMPLATE,
            "TELEGRAM_ONLY",
            "bot_canonical_package_checkout",
            "TELEGRAM_ONLY",
            "TELEGRAM_IDENTITY_CONTEXT, CANONICAL_BOT_ORDER_REQUIRED, CANONICAL_BOT_PAYOS_CHECKOUT, CANONICAL_PACKAGE_ENTITLEMENT_SETTLEMENT, NO_RUNTIME_CLAIM",
        ],
        [
            "other pkgbuy|*",
            "PACKAGE_PURCHASE_SOURCE_REVIEW_REQUIRED",
            "package_purchase_callback_requires_source_review",
            "NEEDS_FEATURE_DISPOSITION",
            "CANONICAL_PACKAGE_PURCHASE_SOURCE_REVIEW, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM",
        ],
    ]
    video_job_contract_rows = [
        [
            VIDEO_JOB_STATS_CALLBACK,
            "/admin/jobs",
            "reviewed_video_job_stats_admin_navigation",
            "NAVIGATION_ONLY",
            "BOT_ADMIN_ONLY, BOT_VIDEO_JOB_STATS_NOT_REPLAYED, FRESH_SIGNED_WEB_ADMIN_NAVIGATION, NO_RUNTIME_CLAIM",
        ],
    ] + [
        [
            source,
            "TELEGRAM_ONLY",
            "bot_canonical_video_job_mutation",
            "TELEGRAM_ONLY",
            "BOT_ADMIN_ONLY, CANONICAL_BOT_JOB_MUTATION, OWNER_SCOPED_BOT_JOB_REQUIRED, NO_RUNTIME_CLAIM",
        ]
        for source in sorted(VIDEO_JOB_MUTATION_CALLBACK_TEMPLATES)
    ] + [
        [
            "other job|*",
            "BOT_VIDEO_JOB_SOURCE_REVIEW_REQUIRED",
            "video_job_callback_requires_source_review",
            "NEEDS_FEATURE_DISPOSITION",
            "BOT_ADMIN_ONLY, CANONICAL_BOT_VIDEO_JOB_STATE, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM",
        ],
    ]
    video_finalization_contract_rows = [
        [
            source,
            "TELEGRAM_ONLY",
            "reviewed_video_finalization_telegram_only",
            "TELEGRAM_ONLY",
            "TELEGRAM_IDENTITY_CONTEXT, BOT_VIDEO_FINALIZATION_SESSION_STATE, BOT_PENDING_MEDIA_OR_TEXT_STATE, CANONICAL_VIDEO_EXPORT_AND_PAYMENT_GUARDS, NO_RUNTIME_CLAIM",
        ]
        for source in sorted(VIDEO_FINALIZATION_TELEGRAM_ONLY_CALLBACKS)
    ] + [
        [
            source,
            "TELEGRAM_ONLY",
            "reviewed_video_finalization_telegram_only",
            "TELEGRAM_ONLY",
            "TELEGRAM_IDENTITY_CONTEXT, BOT_VIDEO_FINALIZATION_SESSION_STATE, BOT_PENDING_MEDIA_OR_TEXT_STATE, CANONICAL_VIDEO_EXPORT_AND_PAYMENT_GUARDS, NO_RUNTIME_CLAIM",
        ]
        for source in sorted(VIDEO_FINALIZATION_TELEGRAM_ONLY_CALLBACK_TEMPLATES)
    ] + [
        [
            "other vfinal|*",
            "VIDEO_FINALIZATION_SOURCE_REVIEW_REQUIRED",
            "video_finalization_callback_requires_source_review",
            "NEEDS_FEATURE_DISPOSITION",
            "BOT_VIDEO_FINALIZATION_SESSION_STATE, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM",
        ],
    ]
    storage_addon_contract_rows = [
        [
            source,
            "TELEGRAM_ONLY",
            "reviewed_storage_addon_telegram_only",
            "TELEGRAM_ONLY",
            ", ".join(str(value) for value in contract["source_dispositions"]),
        ]
        for source, contract in STORAGE_ADDON_TELEGRAM_ONLY_CALLBACKS.items()
    ] + [
        [
            STORAGE_ADDON_CONFIRM_CALLBACK_TEMPLATE,
            "TELEGRAM_ONLY",
            "bot_canonical_storage_addon_checkout",
            "TELEGRAM_ONLY",
            "TELEGRAM_IDENTITY_CONTEXT, CANONICAL_BOT_STORAGE_ORDER_REQUIRED, CANONICAL_BOT_PAYOS_CHECKOUT, CANONICAL_STORAGE_ENTITLEMENT_SETTLEMENT, NO_RUNTIME_CLAIM",
        ],
        [
            "other storage|*",
            "STORAGE_ADDON_SOURCE_REVIEW_REQUIRED",
            "storage_addon_callback_requires_source_review",
            "NEEDS_FEATURE_DISPOSITION",
            "CANONICAL_BOT_STORAGE_ADDON_SOURCE_REVIEW, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM",
        ],
    ]
    memory_menu_contract_rows = [
        [
            source,
            str(contract["target"]),
            "reviewed_memory_fresh_web_navigation",
            "NAVIGATION_ONLY",
            ", ".join(str(value) for value in contract["source_dispositions"]),
        ]
        for source, contract in MEMORY_FRESH_WEB_NAVIGATION_ACTIONS.items()
    ] + [
        [
            source,
            "TELEGRAM_ONLY",
            "bot_canonical_memory_storage_requires_adapter",
            "TELEGRAM_ONLY",
            ", ".join(str(value) for value in contract["source_dispositions"]),
        ]
        for source, contract in MEMORY_STORAGE_TELEGRAM_ONLY_ACTIONS.items()
    ] + [
        [
            source,
            "MEMORY_STORAGE_CLEANUP_CONTRACT_REQUIRED",
            "bot_storage_cleanup_guidance_requires_web_storage_contract",
            "NEEDS_FEATURE_DISPOSITION",
            ", ".join(str(value) for value in contract["source_dispositions"]),
        ]
        for source, contract in MEMORY_STORAGE_GUIDANCE_ACTIONS.items()
    ] + [
        [
            source,
            "TELEGRAM_ONLY",
            "bot_memory_record_identifier_requires_telegram_context",
            "TELEGRAM_ONLY",
            "TELEGRAM_IDENTITY_CONTEXT, BOT_MEMORY_NOTE_IDENTIFIER, BOT_MEMORY_RECORD_STATE, NO_RUNTIME_CLAIM",
        ]
        for source in sorted(MEMORY_RECORD_TELEGRAM_ONLY_CALLBACK_TEMPLATES)
    ] + [
        [
            "other memory|{*}",
            "BOT_MEMORY_SOURCE_REVIEW_REQUIRED",
            "memory_callback_template_requires_source_review",
            "NEEDS_FEATURE_DISPOSITION",
            "BOT_MEMORY_STATE_OR_IDENTIFIER_SOURCE_REVIEW, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM",
        ],
    ]
    # The frozen Main Guide is deliberately documented as a finite top-level
    # surface. The Web receives no callback token; this table makes it clear
    # which choices open a fresh signed destination and which two video/trend
    # sections remain explicitly deferred until the final Video menu phase.
    guided_start_contract_rows = [
        [
            source,
            str(contract["target"]),
            "reviewed_guided_start_fresh_web_navigation",
            "NAVIGATION_ONLY",
            ", ".join(str(value) for value in contract["source_dispositions"]),
        ]
        for source, contract in GUIDED_START_FRESH_WEB_NAVIGATION_ACTIONS.items()
    ] + [
        [
            source,
            str(MENU_ACTION_REGISTRY[source]["target"]),
            "reviewed_exact_menu_navigation",
            "NAVIGATION_ONLY",
            "FRESH_SIGNED_WEB_NAVIGATION, BOT_GUIDE_SECTION_CONTEXT_NOT_REPLAYED, NO_RUNTIME_CLAIM",
        ]
        for source in (
            "menu|guide_image_ai",
            "menu|guide_music_add",
            "menu|guide_credits",
            "menu|support",
            "menu|main",
        )
    ] + [
        [
            source,
            "GUIDED_VIDEO_MENU_DEFERRED",
            "guided_video_menu_deferred_until_video_menu_phase",
            "NEEDS_FEATURE_DISPOSITION",
            "BOT_GUIDE_SECTION_CONTEXT_NOT_REPLAYED, BOT_GUIDE_CHILD_CALLBACKS_NOT_REPLAYED, VIDEO_MENU_LAST, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM",
        ]
        for source in sorted(GUIDED_VIDEO_MENU_DEFERRED_ACTIONS)
    ]
    system_data_stewardship_contract_rows = [
        [
            source,
            str(contract["target"]),
            "reviewed_system_data_stewardship_fresh_web_navigation",
            "NAVIGATION_ONLY",
            str(contract["classification"]),
            str(contract["authority"]),
            ", ".join(str(value) for value in contract["source_dispositions"]),
        ]
        for source, contract in SYSTEM_DATA_STEWARDSHIP_FRESH_WEB_NAVIGATION_ACTIONS.items()
    ]
    tax_accounting_guidance_contract_rows = [
        [
            source,
            str(contract["target"]),
            "reviewed_tax_accounting_guidance_fresh_web_navigation",
            "NAVIGATION_ONLY",
            str(contract["classification"]),
            str(contract["authority"]),
            ", ".join(str(value) for value in contract["source_dispositions"]),
        ]
        for source, contract in TAX_ACCOUNTING_GUIDANCE_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS.items()
    ]
    tax_accounting_source_review_contract_rows = [
        [
            source,
            "CANONICAL_TAX_ACCOUNTING_SOURCE_REVIEW_REQUIRED",
            "reviewed_tax_accounting_callback_requires_canonical_finance_contract",
            "NEEDS_FEATURE_DISPOSITION",
            "admin",
            "Canonical Bot finance/tax operation",
            ", ".join(_tax_accounting_source_review_dispositions(action)),
        ]
        for source, action in sorted(TAX_ACCOUNTING_CANONICAL_FINANCE_SOURCE_REVIEW_ACTIONS.items())
    ]
    job_lock_recovery_guidance_contract_rows = [
        [
            source,
            str(contract["target"]),
            "reviewed_job_lock_recovery_fresh_web_navigation",
            "NAVIGATION_ONLY",
            str(contract["classification"]),
            str(contract["authority"]),
            ", ".join(str(value) for value in contract["source_dispositions"]),
        ]
        for source, contract in JOB_LOCK_RECOVERY_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS.items()
    ]
    job_lock_recovery_source_review_callback_rows = [
        [
            source,
            "CANONICAL_JOB_LOCK_RECOVERY_SOURCE_REVIEW_REQUIRED",
            "reviewed_job_lock_recovery_callback_requires_canonical_mutation_contract",
            "NEEDS_FEATURE_DISPOSITION",
            "admin",
            "Canonical Bot job/refund mutation boundary",
            ", ".join(_job_lock_recovery_source_review_dispositions(action)),
        ]
        for source, action in sorted(JOB_LOCK_RECOVERY_CANONICAL_SOURCE_REVIEW_ACTIONS.items())
    ]
    job_lock_recovery_source_review_command_rows = [
        [
            f"/{source}",
            "CANONICAL_JOB_LOCK_RECOVERY_SOURCE_REVIEW_REQUIRED",
            "reviewed_job_lock_recovery_command_requires_canonical_mutation_contract",
            "NEEDS_FEATURE_DISPOSITION",
            "admin",
            "Canonical Bot job/refund mutation boundary",
            ", ".join(_job_lock_recovery_source_review_dispositions(action)),
        ]
        for source, action in sorted(JOB_LOCK_RECOVERY_CANONICAL_SOURCE_REVIEW_COMMANDS.items())
    ]
    quick_image_planner_contract_rows = [
        [
            "create_media|quick_image, qi_entry, qi_suggest, qi_refresh, qi_pick_1..3, qi_custom, qi_rewrite, qi_topics, qi_back_suggestions",
            "/image/quick-planner",
            "reviewed_quick_image_planner_fresh_web_draft",
            "fresh signed draft only; no Telegram state/callback is transferred",
        ],
        [
            "create_media|qi_logo_choice, qi_logo_add, qi_logo_skip, qi_logo_confirm, qi_logo_pos|{top_left…bottom_right}",
            "/image/quick-planner",
            "reviewed_quick_image_planner_fresh_web_draft",
            "text-only direction and nine semantic placements; no logo upload/overlay/image output",
        ],
        [
            "create_media|qi_choose_ratio, qi_ratio_{*}, qi_back_prompt, qi_back_ratio",
            "/image/quick-planner",
            "reviewed_quick_image_planner_fresh_web_draft",
            "finite prompt/ratio plan; no tier, quote or execution",
        ],
        [
            "create_media|qi_back_tier, qi_tier_{*}",
            "TELEGRAM_ONLY",
            "bot_quick_image_tier_or_confirm_requires_canonical_bot_state",
            "Bot tier/one-time confirmation state and canonical Xu/provider/job boundary",
        ],
        [
            "shopai|confirm|{*}, shopai|package|{*}",
            "TELEGRAM_ONLY",
            "bot_quick_image_tier_or_confirm_requires_canonical_bot_state",
            "opaque canonical checkout/confirmation; no browser payment, ledger, job or delivery action",
        ],
    ]

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
        + "- [`DOCFLOW_CALLBACK_CONTRACT.md`](DOCFLOW_CALLBACK_CONTRACT.md) — exact Bot document-flow callback dispositions and the navigation-only boundary to independent Web document tools.\n"
        + "- [`DOCUMENT_COMMAND_NAVIGATION_CONTRACT.md`](DOCUMENT_COMMAND_NAVIGATION_CONTRACT.md) — finite Bot document command entrypoints that only open fresh signed Web-native document pages; no Bot state or raw API is replayed.\n"
        + "- [`TVFLOW_CALLBACK_CONTRACT.md`](TVFLOW_CALLBACK_CONTRACT.md) — exact Bot trend-video callback dispositions; each is a Bot-state boundary, not Web feature parity.\n"
        + "- [`MEDIA_PREVIEW_CALLBACK_CONTRACT.md`](MEDIA_PREVIEW_CALLBACK_CONTRACT.md) — dynamic Bot media-preview callback boundaries; cache indexes and Telegram delivery are not Web media identifiers or playback claims.\n"
        + "- [`FREE_PROMPT_GALLERY_CONTRACT.md`](FREE_PROMPT_GALLERY_CONTRACT.md) — independent signed Free Prompt Gallery, including the navigation-only boundary for finite Free Hub library category callbacks.\n"
        + "- [`PAYOS_ALERT_CALLBACK_CONTRACT.md`](PAYOS_ALERT_CALLBACK_CONTRACT.md) — exact Bot-admin PayOS alert dispositions; Web neither replays alert state nor becomes a payment/provider/deployment control.\n"
        + "- [`PACKAGE_PURCHASE_CALLBACK_CONTRACT.md`](PACKAGE_PURCHASE_CALLBACK_CONTRACT.md) — finite Bot package-selector navigation plus a canonical Bot checkout boundary; it does not turn a service package into Xu top-up or browser payment.\n"
        + "- [`VIDEO_JOB_CALLBACK_CONTRACT.md`](VIDEO_JOB_CALLBACK_CONTRACT.md) — exact admin video-job stats navigation and canonical Bot mutation boundaries; raw Bot job IDs never become browser actions.\n"
        + "- [`VIDEO_FINALIZATION_CALLBACK_CONTRACT.md`](VIDEO_FINALIZATION_CALLBACK_CONTRACT.md) — exact Bot Video Finishing session boundaries; the separate signed Web workflow never replays Telegram draft, quote, export or payment callbacks.\n"
        + "- [`STORAGE_ADDON_CALLBACK_CONTRACT.md`](STORAGE_ADDON_CALLBACK_CONTRACT.md) — exact Bot storage add-on boundaries; storage quota purchase never becomes a Xu top-up or a second Web payment ledger.\n"
        + "- [`CAPABILITY_HUB_CONTRACT.md`](CAPABILITY_HUB_CONTRACT.md) — aggregate static Bot-to-Web coverage for the product catalog; no raw commands, callbacks or engine-success claim.\n"
        + "- [`WEB_ENGINE_REGISTRY_CONTRACT.md`](WEB_ENGINE_REGISTRY_CONTRACT.md) — display-only classification of Web-native, Bot companion and guarded execution boundaries.\n"
        + "- [`SUBTITLE_FORMAT_LAB_CONTRACT.md`](SUBTITLE_FORMAT_LAB_CONTRACT.md) — signed, stateless SRT↔VTT and text→SRT transform with no Bot/provider/job/payment/file-delivery claim.\n"
        + "- [`SUBTITLE_ASSET_OPERATIONS_CONTRACT.md`](SUBTITLE_ASSET_OPERATIONS_CONTRACT.md) — bounded owner-scoped Asset Vault SRT/VTT validation and verified private conversion attachment; no ASR/translation/dubbing/provider/Bot/payment claim.\n"
        + "- [`CONTENT_PROMPT_PACK_CONTRACT.md`](CONTENT_PROMPT_PACK_CONTRACT.md) — signed, stateless deterministic content-planning drafts adapted from Bot text recipes without Bot/provider/job/payment/publish claims.\n"
        + "- [`PUBLISH_REVIEW_PACK_CONTRACT.md`](PUBLISH_REVIEW_PACK_CONTRACT.md) — signed, stateless text-only review package adapted from the Bot’s pending-result formatter, with no social account/scheduler/provider/Bot/job/payment/asset/publish/delivery claim.\n"
        + "- [`CONTEXTUAL_AD_PROMPT_WIZARD_CONTRACT.md`](CONTEXTUAL_AD_PROMPT_WIZARD_CONTRACT.md) — signed, stateless contextual ad-prompt wizard adapted from Bot goal/platform/ratio/style choices, with no Meta/provider/Bot/job/payment/media-output/publish claim.\n"
        + "- [`TREND_RESEARCH_CONTRACT.md`](TREND_RESEARCH_CONTRACT.md) — signed, stateless manual trend-research checklist adapted from Bot keyword/selection/originality guidance, with no live search/scraping/provider/Bot/job/payment claim.\n"
        + "- [`MEDIA_FACTORY_BLUEPRINT_CONTRACT.md`](MEDIA_FACTORY_BLUEPRINT_CONTRACT.md) — signed, stateless Media Factory blueprint adapted from the Bot's content/video-pack plan, with no live search/provider/Bot/job/payment/media-output/publish claim.\n"
        + "- [`GUIDED_START_CALLBACK_CONTRACT.md`](GUIDED_START_CALLBACK_CONTRACT.md) — finite Main Guide dispositions: fresh signed Web navigation for Quick Start/FAQ, and explicit video/trend deferral until the final Video menu phase.\n"
        + "- [`SYSTEM_DATA_STEWARDSHIP_CALLBACK_CONTRACT.md`](SYSTEM_DATA_STEWARDSHIP_CALLBACK_CONTRACT.md) — finite System/Data and storage-cleanup dispositions: fresh guarded Web navigation with no Bot state, backup, cleanup, payment or runtime action replay.\n"
        + "- [`TAX_ACCOUNTING_GUIDANCE_CALLBACK_CONTRACT.md`](TAX_ACCOUNTING_GUIDANCE_CALLBACK_CONTRACT.md) — finite Bot tax-menu dispositions: fresh canonical-admin guidance navigation with no finance data, calculation, export, file, ledger, payment or profile action replay.\n"
        + "- [`JOB_LOCK_RECOVERY_CALLBACK_CONTRACT.md`](JOB_LOCK_RECOVERY_CALLBACK_CONTRACT.md) — finite Bot stale-job help navigation and explicit canonical job/refund mutation boundaries; the Web guide has no queue/job data or recovery control.\n"
        + "- [`QUICK_IMAGE_PLANNER_CALLBACK_CONTRACT.md`](QUICK_IMAGE_PLANNER_CALLBACK_CONTRACT.md) — finite Quick Image draft callback mapping to a signed deterministic prompt planner; tier/ShopAI/Xu/confirmation remain canonical Bot-only.\n"
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
        + "- [`MEMORY_MENU_CALLBACK_CONTRACT.md`](MEMORY_MENU_CALLBACK_CONTRACT.md) — exact Memory menu/callback boundaries; fresh Web navigation never imports Bot notes, quota, add-ons, IDs or Telegram state.\n"
        + "- [`TELEGRAM_WEB_CONNECTION.md`](TELEGRAM_WEB_CONNECTION.md) — browser-bound Telegram one-time link/login.\n"
        + "- [`BRIDGE_CONTRACT_INVENTORY.md`](BRIDGE_CONTRACT_INVENTORY.md) — static Web-to-Bot method/path compatibility, not live health.\n"
        + "- [`BOT_COMPANION_HANDOFF.md`](BOT_COMPANION_HANDOFF.md) — remaining Bot-first referral/rewards, community and help handoffs.\n"
        + "- [`FEATURE_CONFIRM_CONTRACT.md`](FEATURE_CONFIRM_CONTRACT.md) — explicit job tracking/confirm contract.\n"
        + "- [`ENGINE_DELIVERY_ADAPTER_BACKLOG.md`](ENGINE_DELIVERY_ADAPTER_BACKLOG.md) — canonical job/output/delivery prerequisites.\n"
        + "- [`ADMIN_FAILED_JOB_INCIDENTS.md`](ADMIN_FAILED_JOB_INCIDENTS.md) and [`ADMIN_WRITE_CONTRACT.md`](ADMIN_WRITE_CONTRACT.md) — guarded Admin incident/write boundaries.\n"
        + "- [`ADMIN_INTERNAL_DOCUMENT_ARCHIVE_CONTRACT.md`](ADMIN_INTERNAL_DOCUMENT_ARCHIVE_CONTRACT.md) — opt-in local-admin private document archive with isolated immutable versions; it does not migrate or call Bot internal-document state.\n",
    )
    write(
        "TVFLOW_CALLBACK_CONTRACT.md",
        "# Trend-video callback disposition contract\n\n"
        "The Bot `tvflow` dispatcher has finite source branches, but they depend on Telegram pending state, cached Bot output, canonical Xu/package/billing decisions, provider/job guards, Bot job identifiers, or Telegram chat guidance. Every entry below that is not explicitly `TELEGRAM_ONLY` remains `NEEDS_FEATURE_DISPOSITION`; its target is a symbolic authority boundary, **not** a Web route, bridge implementation, browser callback, provider action, payment action, job action, asset claim, or output-delivery claim.\n\n"
        + _markdown_table(
            ["Bot callback source", "Required authority boundary", "Audit resolution", "Status", "Source dispositions"],
            tvflow_contract_rows,
        )
        + "\n\nA future Web flow must start from Web-owned, owner-scoped input or a separately reviewed private bridge contract. It must never accept/replay Bot scene/job IDs, mutate Bot pending state, credit/debit Xu, finalize PayOS, invoke a provider from the browser, or claim a file/output exists merely because a Telegram callback was observed.\n",
    )
    write(
        "MEDIA_PREVIEW_CALLBACK_CONTRACT.md",
        "# Dynamic media-preview callback disposition contract\n\n"
        "The Bot emits these dynamic music/SFX and media-library preview callbacks only from its Telegram media-preview keyboards. Their formatted values are a media kind/index pair or short-lived cache index, not an owner-scoped Web asset, catalog record, playback authorization, media license verification, or downstream Web media-selection contract. Every original Bot callback is explicitly `TELEGRAM_ONLY`: it neither becomes a browser callback nor carries its cache index into Web. The independently owned Web Media Workspace may preview an account's separately attached Asset Vault audio reference when its dedicated feature flag is enabled; it does not consume Bot cache, selected-media state, provider results or Telegram delivery state.\n\n"
        + _markdown_table(
            ["Bot callback template", "Required authority boundary", "Audit resolution", "Status", "Source dispositions"],
            media_preview_contract_rows,
        )
        + "\n\nA future Web media experience must begin from independently verified catalog/media data and an owner-scoped reference. It must not accept a Bot cache index, replay the Telegram callback, read Bot selected-media state, claim license clearance, or trigger a Bot/video/provider action.\n",
    )
    write(
        "QUICK_IMAGE_PLANNER_CALLBACK_CONTRACT.md",
        "# Quick Image Planner callback contract\n\n"
        "The frozen Bot Quick Image conversation contains a non-executing draft grammar followed by a canonical tier/ShopAI confirmation path. The standalone Web Planner is a fresh signed, CSRF-protected deterministic prompt-plan surface at `/image/quick-planner`; it does not import Bot state, expose raw callbacks, or execute an image workflow.\n\n"
        + _markdown_table(
            ["Frozen Bot source", "Web target/boundary", "Audit resolution", "Required boundary"],
            quick_image_planner_contract_rows,
        )
        + "\n\nThe static auditor derives the nine `qi_logo_pos` values only from the direct frozen helper call that supplies the literal Quick Image prefix. It does not map the helper's shared dynamic `create_media|{*}|…` template globally because regular image/video flows also use it.\n\n"
        "The Web request accepts only a finite catalog key or an original bounded custom brief, deterministic variation, ratio, optional text brand direction and placement, and locale. It has no image upload, preview, source analysis, provider/Bot/Core Bridge call, tier, quote, confirmation token, job, asset, Xu/wallet mutation, PayOS payment, webhook, publish action or delivery. `prompt_plan_only_no_real_image` is a manual-review plan, not evidence that an image or watermark exists.\n",
    )
    write(
        "PAYOS_ALERT_CALLBACK_CONTRACT.md",
        "# PayOS alert callback disposition contract\n\n"
        "The frozen Bot emits the finite `payosalert` callbacks only from owner/admin PayOS alert keyboards, and `handle_payos_alert_callback` rejects a non-admin caller before it reads the action. These are not customer wallet/top-up controls and no value below transfers a Telegram message ID, a Bot-local mute window, a manual-bill state, a provider diagnostic, a PayOS registration state, or an environment value into the Web App.\n\n"
        + _markdown_table(
            ["Bot callback source", "Web target/boundary", "Audit resolution", "Status", "Source dispositions"],
            payos_alert_contract_rows,
        )
        + "\n\n`payosalert|manual` is the sole navigation-only exception: it opens a fresh signed, role-checked `/admin/payments` view. It does not create a payment, request a manual top-up, expose a customer route, carry Bot `USER_BILL_STATE`, add Xu, finalize PayOS, call a provider, change an environment variable, or create a webhook/ledger. `test`, `mute`, `renewed`, and `remind_later` stay Telegram-only until a separately reviewed, canonical admin contract exists.\n\n"
        "An unlisted `payosalert|*` value is deliberately unresolved. It must be source-reviewed before it can become a Web route, bridge method, payment action, diagnostics control, alert preference, or deployment setting.\n",
    )
    write(
        "PACKAGE_PURCHASE_CALLBACK_CONTRACT.md",
        "# Package-purchase callback disposition contract\n\n"
        "The frozen Bot has nine finite `pkgbuy` catalog-selector callbacks. Each validates a catalog package and redraws a Telegram detail/confirmation screen; it does not by itself create an order, call PayOS, grant entitlement, add Xu, or deliver an output. The Bot confirmation callback is a distinct stateful branch. It calls `start_package_purchase`, which may create a pending canonical order, create a PayOS checkout and later grant package entitlement only after canonical settlement.\n\n"
        + _markdown_table(
            ["Bot callback source", "Web target/boundary", "Audit resolution", "Status", "Source dispositions"],
            package_purchase_contract_rows,
        )
        + "\n\nThe exact catalog selectors are: "
        + package_purchase_selector_sources
        + ". They may open only a fresh signed `/packages` catalog. The Web receives no Bot package type/code, Telegram identity or pending state, price, entitlement, checkout URL, order ID, PayOS state, or confirmation action. `/packages` is not a browser checkout.\n\n"
        "`pkgbuy|confirm|{*}|{*}` stays Telegram-only until a separately reviewed owner-scoped package-purchase bridge exists. The Web must not price a service package, create a canonical order, issue or finalize PayOS, credit Xu, grant package entitlement, create a second webhook/ledger, or infer success from a callback. Any unlisted `pkgbuy|*` value remains source-review-required.\n",
    )
    write(
        "VIDEO_JOB_CALLBACK_CONTRACT.md",
        "# Video-job callback disposition contract\n\n"
        "The frozen Bot emits these `job` callbacks only from its admin-only video-job keyboard. Its callback handler rejects a non-admin caller before it reads the action. The `stats` branch only reads canonical Bot campaign/video-job rows and redraws a Telegram message. The `approve` and `cancel` branches resolve a canonical job ID against the Bot owner before updating the canonical job status.\n\n"
        + _markdown_table(
            ["Bot callback source", "Web target/boundary", "Audit resolution", "Status", "Source dispositions"],
            video_job_contract_rows,
        )
        + "\n\n`job|stats|0` is the sole navigation-only exception: it may open a fresh signed, role-checked `/admin/jobs` surface. It transfers no Telegram identity, Bot job ID, campaign/video-job row, cached result, provider state, output/delivery claim, or mutation into the browser. `/admin/jobs` must use its own canonical admin authorization and remain guarded if its bridge projection is unavailable.\n\n"
        "`job|approve|{*}` and `job|cancel|{*}` stay Telegram-only. The Web must not accept a Bot job ID, approve/cancel a canonical job, infer runtime completion, call a provider, debit/credit Xu, finalize PayOS, or create a second job state machine. Any unlisted `job|*` value is source-review-required.\n",
    )
    write(
        "VIDEO_FINALIZATION_CALLBACK_CONTRACT.md",
        "# Video Finishing callback disposition contract\n\n"
        "The frozen Bot `vfinal` dispatcher is a per-Telegram-user finalization state machine. Its callbacks can change a Bot draft, consume pending text/media or selected media, select a tier/scene/aspect, route toward TTS/ASR/provider readiness, or reach guarded package/export paths. A Bot callback is therefore not a Web form value, asset identifier, quote, render request, payment request, or delivery signal.\n\n"
        + _markdown_table(
            ["Bot callback source", "Web target/boundary", "Audit resolution", "Status", "Source dispositions"],
            video_finalization_contract_rows,
        )
        + "\n\nThe standalone Web has a separately authenticated Video Finishing workflow with owner-scoped assets and its own validation/idempotency/output guards. It must begin from a fresh signed Web draft; it must never replay a Bot `vfinal` callback, read/write Bot pending state, accept a Bot cache/file ID or quote, call a provider from the browser, charge Xu, finalize PayOS, or claim render/export success without a verified owner-scoped output. Any unlisted `vfinal|*` value remains source-review-required.\n",
    )
    write(
        "STORAGE_ADDON_CALLBACK_CONTRACT.md",
        "# Storage add-on callback disposition contract\n\n"
        "The frozen Bot storage add-on flow is a Telegram conversation, not a Xu top-up. Its menu draws a Bot-owned storage catalog; its custom branch stores a short-lived pending action for the Telegram user and expects a following Telegram message; and its confirmation branch validates a Bot catalog spec, can create a canonical storage order and PayOS checkout, then grants quota only after canonical settlement.\n\n"
        + _markdown_table(
            ["Bot callback source", "Web target/boundary", "Audit resolution", "Status", "Source dispositions"],
            storage_addon_contract_rows,
        )
        + "\n\nNo value above becomes `/wallet/topup`, a Web amount/code, a browser checkout, a Web storage ledger, a second PayOS webhook, or a quota grant. The Web may later add a separately reviewed owner-scoped Storage Center and bridge contract, but it must start from canonical current state rather than replay a Bot callback or Telegram pending value.\n\n"
        "Any unlisted `storage|*` value remains source-review-required. It must not create an order, call PayOS, grant quota, write storage usage, call a provider, or claim that a storage purchase succeeded.\n",
    )
    write(
        "MEMORY_MENU_CALLBACK_CONTRACT.md",
        "# Memory menu and callback disposition contract\n\n"
        "The standalone Web Memory Center is a signed, Web-owned notes and reminders workspace. The frozen Bot's "
        "Memory menu, dynamic note identifiers, storage quota and storage add-on checkout are separate source "
        "concerns. A Browser never receives a raw callback token, Telegram identity, Bot note ID, pending text, "
        "search query, Bot record, quota, add-on, order or checkout state.\n\n"
        + _markdown_table(
            ["Bot callback source", "Web target/boundary", "Audit resolution", "Status", "Source dispositions"],
            memory_menu_contract_rows,
        )
        + "\n\nThe reviewed navigation entries open a **fresh** signed Web form/list only. They do not inspect, copy "
        "or mutate Bot `memory_*` tables, and reminder navigation does not claim Telegram, email, push or any "
        "other delivery. `menu|memory_storage_status` and `menu|memory_storage_addon` remain Telegram-only "
        "until a separate owner-scoped canonical storage adapter is designed. `menu|memory_storage_cleanup` is "
        "documented separately as navigation-only Workspace Care guidance; it does not map to archive/retention, "
        "delete data, inspect quota or call a storage adapter.\n\n"
        "A dynamic `memory|view|{*}`, `memory|delete|{*}` or `memory|delete_yes|{*}` value carries a Bot "
        "record identifier and remains Telegram-only. Any other dynamic `memory|{*}` value requires source "
        "review before it can gain a Web contract.\n",
    )
    write(
        "GUIDED_START_CALLBACK_CONTRACT.md",
        "# Main Guide callback contract\n\n"
        "The frozen Bot Main Guide is a Telegram information menu. Its child buttons can enter Bot-local conversations, pending media, provider/output guards, canonical Xu/package/PayOS paths, or support context. The standalone Web never receives the callback token, Telegram identity, guide prose, child button, message, pending value, Bot job/asset, provider state, wallet mutation, payment state or output claim.\n\n"
        + _markdown_table(
            ["Frozen Bot guide action", "Web target/boundary", "Audit resolution", "Status", "Source dispositions"],
            guided_start_contract_rows,
        )
        + "\n\n`menu|guide_quick_start` starts the signed Web catalog at `/features`; it is navigation only, not a wizard execution. `menu|guide_faq` starts the signed Support Desk, which uses the Web account and owner-scoped ticket contract rather than a raw Telegram-ID field, Bot chat transcript, screenshot, refund request or status. The pre-existing image, music and canonical wallet navigation entries also begin fresh Web pages and carry no Telegram context.\n\n"
        "`menu|guide_video_ai` and `menu|guide_guided_video` are intentionally **not** routed to Dashboard or a generic Video page. They remain visible migration backlog records until the final finite Video menu phase can define an independently signed, owner-scoped Web contract without replaying the Bot state machine.\n",
    )
    write(
        "SYSTEM_DATA_STEWARDSHIP_CALLBACK_CONTRACT.md",
        "# System & Data Stewardship callback contract\n\n"
        "The frozen Bot System and storage-cleanup buttons are Telegram guidance/menu branches. The standalone Web never receives a callback token, Telegram identity, Bot admin/session state, command, database path, storage quota, add-on, temporary-file TTL, archive row, attachment, runtime payload, health check, backup artifact, secret, provider payload, Xu ledger, PayOS state, job or output claim.\n\n"
        + _markdown_table(
            ["Frozen Bot action", "Fresh Web target", "Audit resolution", "Status", "Audience", "Authority", "Source dispositions"],
            system_data_stewardship_contract_rows,
        )
        + "\n\nEvery row above is navigation only. `/admin/system`, `/admin/runtime` and `/admin/backups` repeat canonical signed-admin authorization; `/admin/internal-documents` repeats its distinct signed Web-local-admin guard; `/account/workspace-care` is a signed customer guidance hub only. A Browser cannot use this contract to run health checks, inspect a runtime, change system data, create/delete/restore/download a backup, clean storage, change quota, operate a provider, write a ledger, create a PayOS checkout, mutate a job or claim delivery.\n\n"
        "`menu|billing`, `menu|tax_*` and every Video/menu production action remain outside this finite registry. `menu|clear_stale_jobs_help` has its own finite Job-Lock Recovery Safety contract and still does not inherit System/Data authority. No namespace fallback grants a Web route.\n",
    )
    write(
        "TAX_ACCOUNTING_GUIDANCE_CALLBACK_CONTRACT.md",
        "# Tax readiness & accounting guidance callback contract\n\n"
        "The frozen Bot tax menu branches are Telegram administrative guidance and can continue into Bot-local tax profile, period, calculation, report or CSV-delivery flows. The standalone Web never receives a callback token, Telegram identity, finance row, tax profile, date range, period, estimate, calculation, report, export request, CSV/file, payment reference, wallet/Xu ledger, PayOS state, provider state, archive row, attachment or output-delivery claim.\n\n"
        + _markdown_table(
            ["Frozen Bot action", "Fresh Web target", "Audit resolution", "Status", "Audience", "Authority", "Source dispositions"],
            tax_accounting_guidance_contract_rows,
        )
        + "\n\nEvery guidance row above opens only the exact `/admin/finance/tax-readiness` page after it repeats canonical signed-admin authorization. It is not tax or legal advice, a tax calculator, a canonical finance read model, a report/export API, a file-delivery route, a tax-profile/config/compliance mutation, a payment/ledger/PayOS/provider action or a runtime claim.\n\n"
        + "The following exact Bot callbacks remain canonical-finance source-review records, not fresh Web navigation or an implied export implementation:\n\n"
        + _markdown_table(
            ["Frozen Bot action", "Web boundary", "Audit resolution", "Status", "Audience", "Authority", "Source dispositions"],
            tax_accounting_source_review_contract_rows,
        )
        + "\n\n`finance_compliance*`, `archive|dept|tax_invoice` and every unknown `menu|tax_*` value remain outside both finite registries. They require separately reviewed canonical finance/read/write or private delivery contracts; no prefix or label creates a Web route.\n",
    )
    write(
        "JOB_LOCK_RECOVERY_CALLBACK_CONTRACT.md",
        "# Job-lock recovery safety callback contract\n\n"
        "The frozen Bot stale-job help is an admin Telegram guidance branch. The actual canonical recovery path can enter confirmation state, update active video-job status and, where policy permits, trigger refund/billing effects. The standalone Web never receives a callback token, Telegram identity, user/job identifier, queue/lock state, confirmation context, worker/provider/runtime payload, output/delivery record, Xu ledger, payment/PayOS state, refund decision or mutation authority.\n\n"
        + _markdown_table(
            ["Frozen Bot action", "Fresh Web target", "Audit resolution", "Status", "Audience", "Authority", "Source dispositions"],
            job_lock_recovery_guidance_contract_rows,
        )
        + "\n\nThe one guidance row opens only the exact `/admin/job-recovery-guide` page after it repeats canonical signed-admin authorization. It is a static triage/escalation guide, not a queue console, job read model, lock inspection tool, command surface, clear/retry/refund action, worker/provider/runtime control, payment/wallet/ledger/PayOS operation or recovery/delivery promise.\n\n"
        + "The following exact Bot callbacks remain canonical mutation source-review records, not fresh Web navigation or browser confirmations:\n\n"
        + _markdown_table(
            ["Frozen Bot action", "Web boundary", "Audit resolution", "Status", "Audience", "Authority", "Source dispositions"],
            job_lock_recovery_source_review_callback_rows,
        )
        + "\n\nThe following exact Bot commands likewise remain canonical mutation source-review records. The Web must not expose, copy, parse or replay them:\n\n"
        + _markdown_table(
            ["Frozen Bot command", "Web boundary", "Audit resolution", "Status", "Audience", "Authority", "Source dispositions"],
            job_lock_recovery_source_review_command_rows,
        )
        + "\n\nAny unlisted `menu|clear_*`, `menu|admin_confirm_*`, job recovery callback or operational command requires new source review. It cannot inherit this guide, `/admin/jobs`, `/admin/callbacks`, a bridge module or a browser-side job/financial control.\n",
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
        + "FFmpeg/ffprobe runtime.\n\n"
        + "## Web-native Media Workspace preview environment\n\n"
        + "- `WEBAPP_MUSIC_MEDIA_WORKSPACE_ENABLED` (default `true`) enables the signed Web-owned collection workspace.\n"
        + "- `WEBAPP_MEDIA_WORKSPACE_PREVIEW_ENABLED` (default `false`) permits same-origin inline preview only for an active audio Asset Vault file already attached to the requesting account's active collection.\n\n"
        + "The preview flag is not a provider/library, Bot-cache, Telegram, wallet, PayOS, job, output-delivery or public-URL switch. It remains disabled until an operator accepts the private storage and traffic implications.\n",
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
        "- The Bot's `payosalert|*` controls are admin-alert callbacks, not customer billing controls. Only the source-reviewed `manual` value may open a fresh signed `/admin/payments` view; it cannot replay Bot bill state or execute a payment action. See `PAYOS_ALERT_CALLBACK_CONTRACT.md`.\n"
        "- Service package/combo checkout is distinct from Xu top-up. The Web can only open its fresh read-only `/packages` catalog for nine reviewed Bot selectors; its confirm callback stays Bot-only, and `POST /payments/create` must not accept a service package. See `PACKAGE_PURCHASE_CALLBACK_CONTRACT.md`.\n"
        "- Bot video-job stats can only open a fresh signed `/admin/jobs` view for one reviewed admin callback. Canonical approve/cancel actions stay Telegram-only until a dedicated owner-scoped admin bridge exists; the Web never accepts a Bot job ID. See `VIDEO_JOB_CALLBACK_CONTRACT.md`.\n"
        "- Bot Video Finishing callbacks remain Telegram-only because they consume or mutate the Telegram finalization session. The separately signed Web workflow starts from its own owner-scoped draft and never accepts Bot media, quote, export or payment state. See `VIDEO_FINALIZATION_CALLBACK_CONTRACT.md`.\n"
        "- Storage quota add-on purchase is distinct from Xu top-up. Bot menu/custom/confirm callbacks remain Telegram-only until an owner-scoped storage bridge exists; the Web must not create a storage order, checkout, quota entitlement, or second webhook/ledger. See `STORAGE_ADDON_CALLBACK_CONTRACT.md`.\n"
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
        + _markdown_table(["Provider", "Occurrences", "Sample files"], provider_rows or [["None detected", "", ""]])
        + "\n\n## Web-native Media Workspace preview\n\n"
        + "- `WEBAPP_MUSIC_MEDIA_WORKSPACE_ENABLED` defaults to `true` for signed Web-owned collections.\n"
        + "- `WEBAPP_MEDIA_WORKSPACE_PREVIEW_ENABLED` defaults to `false`; when enabled it permits only verified, owner-scoped, same-origin inline preview of an attached active Asset Vault audio file.\n"
        + "- This flag never enables a Bot cache/provider catalog, Telegram delivery, wallet/PayOS action, job, output claim or public URL.\n",
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


@contextmanager
def _locked_bot_source_snapshot(root: Path, baseline_sha: str):
    """Yield a static source tree for the requested Bot baseline.

    A SHA in a report is not enough when the supplied Bot worktree has moved.
    For a real Git worktree this helper reads the verified local commit through
    ``git archive`` and writes only source-suffix regular files into a temporary
    directory.  It never checks out, resets, fetches, imports or executes Bot
    code.  Non-Git roots are kept as-is so hermetic parser unit tests remain
    possible; a Git root with an unavailable requested baseline fails closed.
    """

    requested = str(baseline_sha or "").strip()
    if not (root / ".git").exists():
        yield root, {
            "mode": "working_tree_fallback",
            "reason": "not_a_git_worktree",
            "revision": "",
            "files_materialized": 0,
        }
        return
    if not re.fullmatch(r"[0-9a-f]{7,64}", requested):
        raise ValueError("Requested Bot baseline SHA is invalid; refusing to audit a Git worktree fallback")
    revision_status, revision = _git_read(root, "rev-parse", "--verify", f"{requested}^{{commit}}")
    if revision_status != 0 or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Requested Bot baseline is unavailable; refusing to audit a Git worktree fallback")
    try:
        archive = subprocess.run(
            ["git", "-C", str(root), "archive", "--format=tar", revision],
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("Unable to materialize requested Bot baseline for static audit") from exc
    if archive.returncode != 0 or not archive.stdout:
        raise ValueError("Requested Bot baseline archive is unavailable; refusing to audit a Git worktree fallback")
    if len(archive.stdout) > MAX_BASELINE_ARCHIVE_BYTES:
        raise ValueError("Requested Bot baseline archive exceeds the static audit safety limit")

    with tempfile.TemporaryDirectory(prefix="toan-aas-bot-baseline-") as temporary:
        snapshot = Path(temporary)
        materialized = 0
        try:
            with tarfile.open(fileobj=io.BytesIO(archive.stdout), mode="r:") as source_archive:
                for member in source_archive.getmembers():
                    if not member.isfile():
                        continue
                    relative = PurePosixPath(member.name)
                    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
                        raise ValueError("Requested Bot baseline archive contains an unsafe source path")
                    destination = snapshot.joinpath(*relative.parts)
                    if destination.suffix.lower() not in SOURCE_SUFFIXES:
                        continue
                    payload = source_archive.extractfile(member)
                    if payload is None:
                        continue
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(payload.read())
                    materialized += 1
        except (tarfile.TarError, OSError) as exc:
            raise ValueError("Unable to materialize requested Bot baseline source files") from exc
        if not (snapshot / "bot.py").is_file():
            raise ValueError("Requested Bot baseline has no bot.py entrypoint")
        yield snapshot, {
            "mode": "git_baseline_snapshot",
            "reason": "requested_baseline_materialized_static_only",
            "revision": revision,
            "files_materialized": materialized,
        }


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
    with _locked_bot_source_snapshot(bot_root, bot_baseline_sha) as (audit_bot_root, audit_source):
        bot_entrypoint = audit_bot_root / "bot.py"
        preflight = {
            "schema_version": SCHEMA_VERSION,
            "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "audit_mode": "static-only",
            "guarantees": [
                "No bot, web app, provider, database, payment service, environment file, or webhook is imported or executed.",
                "Only source text, Python AST, and local read-only Git revision metadata are read.",
                "A verified requested Git baseline is materialized as a temporary source-only snapshot; the Bot worktree is not used as source evidence.",
                "Report/document text is sanitized for secret-shaped literals.",
            ],
            "bot": {
                "root": str(bot_root),
                "entrypoint_present": bot_entrypoint.is_file(),
                "baseline_sha_requested": bot_baseline_sha,
                "revision": _git_revision_context(bot_root, bot_baseline_sha),
                "audit_source": audit_source,
                "baseline_bridge_source": _baseline_bridge_source_context(bot_root, bot_baseline_sha),
            },
            "webapp": {"root": str(web_root), "entrypoint_present": (web_root / "app.py").is_file()},
        }
        bot = _summarize_inventory("telegram_bot", audit_bot_root)
        web = _summarize_inventory("webapp", web_root)
        gap = _build_parity_gap(bot, web, audit_bot_root, web_root)
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
