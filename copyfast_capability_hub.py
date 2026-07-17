"""Safe, aggregate-only Bot-to-Web capability hub metadata.

The migration auditor writes a large static parity matrix for engineers.  The
portal needs a much smaller product-facing view of that matrix: feature-family
coverage and safe route destinations, never raw callback payloads, handlers,
source locations, admin commands, secrets or any claim that an engine ran.

This module only reads the committed, sanitized audit report as data.  It
never imports the Telegram bot, opens an environment file, calls a provider,
or reaches the Core Bridge.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parent
DEFAULT_REPORT_PATH = ROOT / "reports" / "migration" / "parity_gap.json"
SAFE_ROUTE = re.compile(r"^/[a-z0-9][a-z0-9/_-]{0,180}$", re.IGNORECASE)
MAX_COMMAND_MAPPINGS = 2_000


# These are product families, not engine declarations.  A route only gives a
# user a stable place to continue their workflow; readiness remains server
# controlled by the existing catalog/feature capability contracts.
FAMILY_SPECS: tuple[dict[str, str], ...] = (
    {
        "key": "content",
        "title": "Content & Chat",
        "route": "/features/content",
        "description": "Prompt, chat, caption, script, storyboard, campaign và planning.",
    },
    {
        "key": "image",
        "title": "Image Studio",
        "route": "/features/image",
        "description": "Art direction, image workflow và utility ảnh riêng tư.",
    },
    {
        "key": "video",
        "title": "Video Studio",
        "route": "/features/video",
        "description": "Brief video, scene planning, review và delivery flow.",
    },
    {
        "key": "voice",
        "title": "Voice Studio",
        "route": "/features/voice",
        "description": "Voice direction, TTS, consent và workflow giọng nói.",
    },
    {
        "key": "music",
        "title": "Music & SFX",
        "route": "/features/music",
        "description": "Music brief, song, SFX và audio library.",
    },
    {
        "key": "subtitle",
        "title": "Phụ đề & ngôn ngữ",
        "route": "/features/subtitle",
        "description": "Transcript, ASR, SRT/VTT, translation và dubbing.",
    },
    {
        "key": "documents",
        "title": "Documents & PDF",
        "route": "/features/documents",
        "description": "Document workspace, OCR, PDF và deterministic utilities.",
    },
    {
        "key": "commerce",
        "title": "Ví, gói & quyền lợi",
        "route": "/wallet",
        "description": "Ví Xu, pricing, membership và lịch sử canonical.",
    },
    {
        "key": "delivery",
        "title": "Jobs & tài sản",
        "route": "/jobs",
        "description": "Theo dõi job, delivery và tài sản đã qua ownership check.",
    },
    {
        "key": "workspace",
        "title": "Workspace & tài khoản",
        "route": "/dashboard",
        "description": "Project, bản nháp, workboard, memory, account và hỗ trợ.",
    },
)
FAMILY_BY_KEY = {item["key"]: item for item in FAMILY_SPECS}

_CACHE_KEY: tuple[int, int] | None = None
_CACHE_VALUE: dict[str, Any] | None = None


def _safe_route(value: object) -> str:
    route = str(value or "").strip()
    if not SAFE_ROUTE.fullmatch(route) or route.startswith("//") or "\\" in route:
        return ""
    return route


def _family_for_mapping(source: object, target: object) -> str:
    """Classify a sanitized static mapping into a user-facing feature family."""

    route = _safe_route(target).lower()
    text = f"{source or ''} {target or ''}".lower().replace("-", "_")
    if route.startswith("/image") or any(token in text for token in ("image", "anh", "upscale", "background_remove")):
        return "image"
    if route.startswith(("/video", "/studio")) or any(token in text for token in ("video", "film", "scene", "render")):
        return "video"
    if route.startswith("/voice") or any(token in text for token in ("voice", "tts", "voiceover", "clone")):
        return "voice"
    if route.startswith("/music") or any(token in text for token in ("music", "song", "sfx", "audio")):
        return "music"
    if route.startswith(("/subtitle", "/translate", "/dubbing", "/asr")) or any(
        token in text for token in ("subtitle", "translate", "dubb", "asr", "srt", "vtt")
    ):
        return "subtitle"
    if route.startswith("/documents") or any(token in text for token in ("document", "doc_", "pdf", "ocr", "compress", "merge")):
        return "documents"
    if route.startswith(("/wallet", "/packages", "/membership", "/pricing", "/rewards", "/referrals")) or any(
        token in text for token in ("wallet", "payos", "payment", "topup", "xu", "vip", "member", "package", "gift", "promo")
    ):
        return "commerce"
    if route.startswith(("/jobs", "/assets", "/asset-vault")) or any(token in text for token in ("job", "asset", "delivery", "queue")):
        return "delivery"
    if route.startswith(("/chat", "/content", "/prompt", "/campaign", "/calendar", "/approvals")) or any(
        token in text for token in ("chat", "prompt", "caption", "hashtag", "hook", "script", "storyboard", "campaign")
    ):
        return "content"
    return "workspace"


def _empty_hub() -> dict[str, Any]:
    return {
        "available": False,
        "audit_mode": "static-only",
        "audit": {
            "commands": 0,
            "callback_handlers": 0,
            "callback_data": 0,
            "mapped": 0,
            "guarded": 0,
            "telegram_only": 0,
        },
        "families": [
            {
                **spec,
                "customer_command_count": 0,
                "mapped_route_count": 0,
                "guarded_route_count": 0,
                "telegram_only_count": 0,
            }
            for spec in FAMILY_SPECS
        ],
    }


def build_capability_hub(parity_gap: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a browser-safe aggregate of one sanitized static audit result.

    The input is intentionally treated as untrusted JSON.  Only small counts,
    fixed family labels, and pre-approved same-origin route shapes survive.
    No raw Bot command, callback, handler, source file, line number or target
    outside the product route grammar is returned.
    """

    if not isinstance(parity_gap, Mapping):
        return _empty_hub()
    if parity_gap.get("audit_mode") != "static-only":
        return _empty_hub()
    source_counts = parity_gap.get("source_counts")
    status_counts = parity_gap.get("mapping_status_counts")
    mappings = parity_gap.get("command_mappings")
    if not isinstance(source_counts, Mapping) or not isinstance(status_counts, Mapping) or not isinstance(mappings, list):
        return _empty_hub()

    def count(name: str) -> int:
        value = source_counts.get(name, 0)
        return int(value) if isinstance(value, int) and 0 <= value <= 100_000 else 0

    def status_count(name: str) -> int:
        value = status_counts.get(name, 0)
        return int(value) if isinstance(value, int) and 0 <= value <= 100_000 else 0

    families: dict[str, dict[str, Any]] = {
        spec["key"]: {
            **spec,
            "customer_command_count": 0,
            "mapped_route_count": 0,
            "guarded_route_count": 0,
            "telegram_only_count": 0,
        }
        for spec in FAMILY_SPECS
    }

    for record in mappings[:MAX_COMMAND_MAPPINGS]:
        if not isinstance(record, Mapping):
            continue
        # Browser Hub intentionally excludes staff/admin implementation detail.
        classification = str(record.get("classification") or "").lower()
        target = str(record.get("target") or "")
        if classification != "customer" or target.startswith("/admin"):
            continue
        status = str(record.get("status") or "")
        family = families[_family_for_mapping(record.get("source"), target)]
        family["customer_command_count"] += 1
        if status == "MAPPED_TO_EXISTING_ROUTE" and _safe_route(target):
            family["mapped_route_count"] += 1
        elif status == "COPIED_GUARDED" and _safe_route(target):
            family["guarded_route_count"] += 1
        elif status == "TELEGRAM_ONLY":
            family["telegram_only_count"] += 1

    return {
        "available": True,
        "audit_mode": "static-only",
        "audit": {
            "commands": count("commands"),
            "callback_handlers": count("callback_handlers"),
            "callback_data": count("callback_data"),
            "mapped": status_count("MAPPED_TO_EXISTING_ROUTE"),
            "guarded": status_count("COPIED_GUARDED"),
            "telegram_only": status_count("TELEGRAM_ONLY"),
        },
        "families": list(families.values()),
    }


def capability_hub(report_path: Path = DEFAULT_REPORT_PATH) -> dict[str, Any]:
    """Load the current committed audit report with a tiny file-stat cache."""

    global _CACHE_KEY, _CACHE_VALUE
    try:
        stat = report_path.stat()
        cache_key = (int(stat.st_mtime_ns), int(stat.st_size))
    except OSError:
        return _empty_hub()
    if _CACHE_KEY == cache_key and _CACHE_VALUE is not None:
        return deepcopy(_CACHE_VALUE)
    try:
        raw = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return _empty_hub()
    value = build_capability_hub(raw if isinstance(raw, Mapping) else None)
    _CACHE_KEY = cache_key
    _CACHE_VALUE = value
    return deepcopy(value)
