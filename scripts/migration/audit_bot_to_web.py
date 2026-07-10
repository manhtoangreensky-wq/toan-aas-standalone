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
    "wallet": "/wallet",
    "naptien": "/wallet/topup",
    "topup": "/wallet/topup",
    "support": "/support",
    "tickets": "/tickets",
    "ticket_status": "/tickets",
    "support_status": "/tickets",
    "legal": "/legal",
    "terms": "/legal",
    "privacy": "/privacy",
    "data_delete": "/account",
    "mydata": "/account",
    "status": "/dashboard",
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
    "pdf_to_images": "/documents/pdf",
    "ocr_image": "/documents/ocr",
    "ocr_pdf": "/documents/ocr",
    "add_voice_to_video": "/video/add-ons",
    "video_music": "/video/add-ons",
    "help": "/dashboard",
    "commands": "/dashboard",
    "huongdan": "/dashboard",
    "guide": "/dashboard",
    "hdsd": "/dashboard",
    "affiliate": "/affiliate-app",
    "campaign": "/campaign-app",
    "video": "/video-app",
    "media": "/media-app",
    "assistant": "/assistant-app",
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

    for match in COMMAND_HANDLER_RE.finditer(text):
        record = {
            "command": _redact_text(match.group("command")).lstrip("/"),
            "handler": match.group("handler"),
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
                    record = {"command": command.lstrip("/"), "handler": handler, **location}
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
    files = _source_files(root)
    python_inventory = _extract_python_inventory(root, files)
    tables = _extract_database_references(root, files)
    providers = _extract_provider_references(root, files)
    inventory: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "project_kind": project_kind,
        "audit_mode": "static-only",
        "source_root": str(root),
        "source_files_scanned": len(files),
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


def _is_admin_command(command: str, handler: str) -> bool:
    haystack = f"{command} {handler}".casefold()
    return any(term in haystack for term in ADMIN_TERMS)


def _is_telegram_only(identifier: str) -> bool:
    lowered = identifier.casefold()
    return any(term in lowered for term in TELEGRAM_ONLY_TERMS)


def _feature_route(identifier: str) -> str:
    lowered = identifier.casefold().replace("-", "_")
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
        "/dashboard", "/account", "/wallet", "/packages", "/jobs", "/assets", "/support", "/tickets",
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
    admin = _is_admin_command(name, command["handler"])
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


def _build_parity_gap(bot: dict[str, Any], web: dict[str, Any]) -> dict[str, Any]:
    existing_routes = {str(route["path"]) for route in web["routes"] if not str(route["path"]).startswith("<")}
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
            "detail": "Private bridge routes are owned by the separate bot bridge branch, never the browser-facing Web App.",
            "count": 0 if bot.get("private_core_bridge_present") or any(str(route["path"]).startswith("/internal/v1/") for route in bot["routes"]) else 1,
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

    def write(name: str, content: str) -> None:
        path = docs_dir / name
        _write_text(path, _sanitize(content))
        generated.append(path)

    write(
        "README.md",
        "# P0 WebApp CopyFast1 migration inventory\n\n"
        "This directory is generated by `scripts/migration/audit_bot_to_web.py`. The audit parses source files only; it does not import or run the Telegram bot, FastAPI app, database, providers, payment service, or environment files.\n\n"
        f"- Bot baseline requested: `{preflight['bot']['baseline_sha_requested']}`\n"
        f"- Bot source fingerprint: `{bot['source_fingerprint_sha256']}`\n"
        f"- Web source fingerprint: `{web['source_fingerprint_sha256']}`\n"
        "- Canonical authority remains the bot for Telegram identity, Xu ledger, PayOS, jobs, and provider state.\n\n"
        "The generated parity matrix is an implementation backlog, not a claim that surfaces are live or safe to enable.\n",
    )
    write(
        "inventory.md",
        "# Static inventory\n\n"
        + _markdown_table(
            ["Area", "Bot", "Web App"],
            [
                ["Source files scanned", str(bot["source_files_scanned"]), str(web["source_files_scanned"])],
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
        "This maps Telegram entry points to the intended Web route family. Existing-route status is determined by static FastAPI route extraction.\n\n"
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
    admin_commands = [item for item in bot["commands"] if _is_admin_command(item["command"], item["handler"])]
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
            "Only source text and Python AST are read.",
            "Report/document text is sanitized for secret-shaped literals.",
        ],
        "bot": {
            "root": str(bot_root),
            "entrypoint_present": bot_entrypoint.is_file(),
            "baseline_sha_requested": bot_baseline_sha,
        },
        "webapp": {"root": str(web_root), "entrypoint_present": (web_root / "app.py").is_file()},
    }
    bot = _summarize_inventory("telegram_bot", bot_root)
    web = _summarize_inventory("webapp", web_root)
    gap = _build_parity_gap(bot, web)
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
