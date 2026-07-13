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
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "1.0"
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
    "creative_flow": "/studio",
    "film": "/studio",
    "media_factory": "/studio",
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
    "ocr_pdf": "/documents/ocr",
    "add_voice_to_video": "/video/add-ons",
    "video_music": "/video/add-ons",
    "help": "/guides",
    "source_help": "/guides",
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
    r"\bCallbackQueryHandler\s*\(\s*(?P<handler>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)[\s\S]{0,360}?\bpattern\s*=\s*(['\"])(?P<pattern>[^'\"\r\n]+)\2"
)
CALLBACK_DATA_RE = re.compile(r"\bcallback_data\s*=\s*(['\"])(?P<token>[^'\"\r\n]+)\1")
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


def _source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        try:
            relative_parts = path.relative_to(root).parts
        except ValueError:
            continue
        if any(part in EXCLUDED_DIRS for part in relative_parts):
            continue
        files.append(path)
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


def _extract_python_inventory(root: Path, files: list[Path]) -> dict[str, Any]:
    commands: list[dict[str, Any]] = []
    callback_handlers: list[dict[str, Any]] = []
    callback_data: list[dict[str, Any]] = []
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
                        token = _literal_string(keyword.value) or "<dynamic-callback-data>"
                        record = {"token": token, **location}
                        _append_unique(callback_data, seen["callback_data"], record, ("token", "file", "line"))

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

    return {
        "commands": sorted(commands, key=lambda item: (item["command"], item["file"], item["line"])),
        "callback_handlers": sorted(callback_handlers, key=lambda item: (item["pattern"], item["file"], item["line"])),
        "callback_data": sorted(callback_data, key=lambda item: (item["token"], item["file"], item["line"])),
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
            "conversations": len(python_inventory["conversations"]),
            "routes": len(python_inventory["routes"]),
            "background_jobs": len(python_inventory["background_jobs"]),
            "env_references": len(python_inventory["env_references"]),
            "database_tables": len({record["table"] for record in tables}),
            "providers": len(providers),
        },
    }
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
        "/dashboard", "/account", "/onboarding", "/wallet", "/packages", "/jobs", "/assets", "/support", "/tickets",
        "/membership", "/status", "/studio",
        "/notes", "/reminders", "/referrals", "/rewards", "/community", "/guides", "/growth", "/campaign",
        "/pricing", "/legal", "/privacy", "/content", "/image", "/video", "/voice", "/music", "/subtitle",
        "/translate", "/dubbing", "/asr", "/documents", "/features", "/admin", "/tools", "/prompts",
        "/caption", "/hashtag", "/hook", "/script", "/storyboard",
    )
    return normalized == "/" or normalized.startswith(prefixes)


def _mapping_status(target: str, existing_routes: set[str], telegram_only: bool) -> str:
    if telegram_only:
        return "TELEGRAM_ONLY"
    if _route_exists(target, existing_routes):
        return "MAPPED_TO_EXISTING_ROUTE"
    if _compatibility_surface_exists(target, existing_routes):
        return "COPIED_GUARDED"
    return "NEEDS_WEB_IMPLEMENTATION"


def _map_command(command: dict[str, Any], existing_routes: set[str]) -> dict[str, Any]:
    name = command["command"].casefold()
    admin = _is_admin_command(name, command["handler"], admin_guarded=bool(command.get("admin_guarded")))
    telegram_only = _is_telegram_only(name)
    if admin and not telegram_only:
        target = f"/admin/{name}"
    else:
        target = COMMAND_ROUTE_OVERRIDES.get(name, _feature_route(name))
    status = _mapping_status(target, existing_routes, telegram_only)
    return {
        "source_kind": "command",
        "source": f"/{command['command']}",
        "handler": command["handler"],
        "target": target if not telegram_only else "TELEGRAM_ONLY",
        "classification": "admin" if admin else "customer",
        "status": status,
        "evidence": {"file": command["file"], "line": command["line"]},
    }


def _map_callback(identifier: str, source_kind: str, evidence: dict[str, Any], existing_routes: set[str]) -> dict[str, Any]:
    token = identifier.casefold()
    admin = _is_admin_command(token, "")
    telegram_only = _is_telegram_only(token)
    if admin and not telegram_only:
        target = "/admin/callbacks"
    else:
        target = _feature_route(token)
    status = _mapping_status(target, existing_routes, telegram_only)
    return {
        "source_kind": source_kind,
        "source": identifier,
        "target": target if not telegram_only else "TELEGRAM_ONLY",
        "classification": "admin" if admin else "customer",
        "status": status,
        "evidence": evidence,
    }


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
    return {str(route["path"]) for route in records if str(route.get("file") or "") in route_files}


def _build_parity_gap(bot: dict[str, Any], web: dict[str, Any], bot_root: Path, web_root: Path) -> dict[str, Any]:
    existing_routes = _runtime_web_route_paths(web, web_root)
    bridge_contract = _bridge_contract_inventory(bot_root, web_root)
    telegram_link_contract = _telegram_link_callback_contract(bot_root, web_root)
    command_mappings = [_map_command(command, existing_routes) for command in bot["commands"]]
    callback_mappings = [
        _map_callback(record["pattern"], "callback_handler", {"file": record["file"], "line": record["line"]}, existing_routes)
        for record in bot["callback_handlers"]
    ]
    callback_mappings.extend(
        _map_callback(record["token"], "callback_data", {"file": record["file"], "line": record["line"]}, existing_routes)
        for record in bot["callback_data"]
    )
    conversation_mappings = [
        {
            "source_kind": "conversation",
            "source": f"ConversationHandler at {record['file']}:{record['line']}",
            "target": "/workflow",
            "classification": "customer",
            "status": "NEEDS_WEB_IMPLEMENTATION",
            "evidence": {"file": record["file"], "line": record["line"]},
        }
        for record in bot["conversations"]
    ]
    mappings = command_mappings + callback_mappings + conversation_mappings
    status_counts = Counter(item["status"] for item in mappings)
    mapped = status_counts["MAPPED_TO_EXISTING_ROUTE"] + status_counts["COPIED_GUARDED"]
    source_total = len(mappings)
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
                "commands": len(command_mappings),
                "callback_handlers": len(bot["callback_handlers"]),
                "callback_data": len(bot["callback_data"]),
                "conversations": len(conversation_mappings),
                "total_mappings": source_total,
            },
            "mapping_status_counts": dict(sorted(status_counts.items())),
            "implemented_coverage_percent": round((mapped / source_total * 100), 2) if source_total else 0.0,
            "guarded_surface_coverage_percent": round(((mapped + status_counts["TELEGRAM_ONLY"]) / source_total * 100), 2) if source_total else 100.0,
            "mapping_coverage_percent": 100.0 if source_total == len(mappings) else 0.0,
            "bridge_contract": bridge_contract,
            "telegram_link_callback_contract": telegram_link_contract,
            "command_mappings": command_mappings,
            "callback_mappings": callback_mappings,
            "conversation_mappings": conversation_mappings,
            "gaps": gaps,
            "notes": [
                "Every statically discovered command/callback/conversation is represented in this matrix.",
                "COPIED_GUARDED is a real signed/guarded Web compatibility surface, not a provider, wallet, job, or output success claim.",
                "MAPPED_TO_EXISTING_ROUTE only confirms a static Web route was found; it does not prove auth, wallet, provider, job, or output parity.",
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
        + "- [`JOB_SUPPORT_RECOVERY.md`](JOB_SUPPORT_RECOVERY.md) — safe job-to-ticket recovery handoff.\n"
        + "- [`CONTENT_OPERATIONS_ADMIN.md`](CONTENT_OPERATIONS_ADMIN.md) — guarded Campaign/Calendar/Publishing/Admin navigation.\n"
        + "- [`ASSET_VAULT_CONTRACT.md`](ASSET_VAULT_CONTRACT.md) — private Web-owned source storage and owner-scoped delivery.\n"
        + "- [`PROJECT_PACKAGE_CONTRACT.md`](PROJECT_PACKAGE_CONTRACT.md) — private immutable Project ZIP exports.\n"
        + "- [`PDF_SPLIT_CONTRACT.md`](PDF_SPLIT_CONTRACT.md), [`PDF_MERGE_CONTRACT.md`](PDF_MERGE_CONTRACT.md) and [`PDF_OPTIMIZE_CONTRACT.md`](PDF_OPTIMIZE_CONTRACT.md) — bounded private PDF structure operations.\n"
        + "- [`IMAGE_TO_PDF_CONTRACT.md`](IMAGE_TO_PDF_CONTRACT.md) — ordered private image-to-PDF delivery.\n"
        + "- [`PDF_TO_IMAGES_CONTRACT.md`](PDF_TO_IMAGES_CONTRACT.md) — Bot-compatible 2× PDF raster delivery as verified private PNG or deterministic PNG ZIP.\n"
        + "- [`PDF_TO_WORD_CONTRACT.md`](PDF_TO_WORD_CONTRACT.md) — real text-only private PDF-to-DOCX extraction.\n"
        + "- [`IMAGE_RESIZE_ASPECT_CONTRACT.md`](IMAGE_RESIZE_ASPECT_CONTRACT.md) and [`IMAGE_ENHANCE_CONTRACT.md`](IMAGE_ENHANCE_CONTRACT.md) — bounded local private image artifacts.\n"
        + "- [`TELEGRAM_WEB_CONNECTION.md`](TELEGRAM_WEB_CONNECTION.md) — browser-bound Telegram one-time link/login.\n"
        + "- [`BRIDGE_CONTRACT_INVENTORY.md`](BRIDGE_CONTRACT_INVENTORY.md) — static Web-to-Bot method/path compatibility, not live health.\n"
        + "- [`BOT_COMPANION_HANDOFF.md`](BOT_COMPANION_HANDOFF.md) — Bot-first notes, reminders, referral/rewards, community and help handoffs.\n"
        + "- [`FEATURE_CONFIRM_CONTRACT.md`](FEATURE_CONFIRM_CONTRACT.md) — explicit job tracking/confirm contract.\n"
        + "- [`ENGINE_DELIVERY_ADAPTER_BACKLOG.md`](ENGINE_DELIVERY_ADAPTER_BACKLOG.md) — canonical job/output/delivery prerequisites.\n"
        + "- [`ADMIN_FAILED_JOB_INCIDENTS.md`](ADMIN_FAILED_JOB_INCIDENTS.md) and [`ADMIN_WRITE_CONTRACT.md`](ADMIN_WRITE_CONTRACT.md) — guarded Admin incident/write boundaries.\n",
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
                ["Callback handlers", str(bot["counts"]["callback_handlers"]), "n/a"],
                ["Callback-data values", str(bot["counts"]["callback_data"]), "n/a"],
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
        f"Discovered `{bot['counts']['commands']}` registered commands, `{bot['counts']['callback_handlers']}` callback handlers, and `{bot['counts']['callback_data']}` callback-data values from static source.\n\n"
        + ("Excluded clearly named Bot drafts: `" + "`, `".join(bot.get("excluded_noncanonical_source_files", [])) + "`.\n\n" if bot.get("excluded_noncanonical_source_files") else "")
        + _markdown_table(["Command", "Handler", "Source"], sampled_commands or [["None discovered", "", ""]])
        + "\n\nThe full command/callback inventory is in `reports/migration/bot_inventory.json`.\n",
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
        for item in (gap["command_mappings"] + gap["callback_mappings"] + gap["conversation_mappings"])[:200]
    ]
    write(
        "parity-matrix.md",
        "# Parity matrix\n\n"
        f"Safe Web surface coverage: **{gap['implemented_coverage_percent']}%** (`MAPPED_TO_EXISTING_ROUTE` + `COPIED_GUARDED`). "
        "All source items are represented in the JSON matrix; this page shows the first 200 records.\n\n"
        + _markdown_table(["Source type", "Bot entry", "Web target", "Status"], parity_rows or [["None discovered", "", "", ""]])
        + "\n\n`COPIED_GUARDED` means a signed/guarded compatibility page exists; it never claims an engine, payment, or output completed. `NEEDS_WEB_IMPLEMENTATION` remains actionable.\n",
    )
    route_rows = [[item["source"], item["target"], item["status"]] for item in gap["command_mappings"][:200]]
    write(
        "route-map.md",
        "# Route and action map\n\n"
        "This maps Telegram entry points to the intended Web route family. Existing-route status uses the signed `app.py` entrypoint plus its directly included routers; unmounted legacy decorators are not treated as production routes.\n\n"
        + _markdown_table(["Telegram command", "Web route/action", "Status"], route_rows or [["None discovered", "", ""]]),
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
        + "\n\nNo destructive migration or schema synchronization is authorized by this inventory.\n",
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
        + _markdown_table(["Provider", "Occurrences", "Sample files"], provider_rows or [["None detected", "", ""]]),
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
        + "\n\nThese are static findings. Resolve each through contracts and tests before marking a Web App flow complete.\n",
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
                ["Callbacks", str(bot["counts"]["callback_handlers"]), "Mapped or explicitly TELEGRAM_ONLY"],
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
        f"Safe Web surface coverage: **{gap['implemented_coverage_percent']}%**. This is an actionable migration baseline, not a LIVE or engine-success claim.\n\n"
        + _markdown_table(["Source type", "Bot entry", "Web target", "Status"], parity_rows)
        + "\n\nAllowed implementation statuses: `COPIED_WORKING`, `COPIED_GUARDED`, `ADMIN_ONLY`, `READ_ONLY`, `NEEDS_CORE_BRIDGE`, `BOT_NOT_WORKING`, `NOT_FOUND`.\n",
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
        "Every admin page requires signed session, canonical role, CSRF on writes, confirmation, idempotency where applicable, and audit events.\n\n"
        + _markdown_table(["Bot command", "Handler", "Planned Web target"], [[f"/{item['command']}", item["handler"], f"/admin/{item['command']}"] for item in admin_commands[:200]] or [["None discovered", "", ""]]),
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
        + "\n\nA guarded feature remains visible with safe Vietnamese copy and must not call a provider or claim an output.\n",
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
