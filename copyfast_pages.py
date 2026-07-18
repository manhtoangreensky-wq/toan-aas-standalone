"""Route-aware portal shell renderer."""

from __future__ import annotations

import html
import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path
import re

from fastapi import HTTPException
from fastapi.responses import HTMLResponse

from copyfast_registry import ALL_FEATURES, allowed_paths


ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "templates" / "portal_shell.html"
CAMPAIGN_PLAN_PATH = re.compile(r"^/campaigns/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
PROJECT_PATH = re.compile(r"^/projects/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
PROMPT_LIBRARY_PATH = re.compile(r"^/prompt-library/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
MEDIA_WORKSPACE_PATH = re.compile(r"^/media-workspace/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
CONTENT_STUDIO_PATH = re.compile(r"^/content-studio/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
VOICE_STUDIO_PATH = re.compile(r"^/voice-studio/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
VIDEO_STUDIO_PATH = re.compile(r"^/video-studio/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
SUBTITLE_STUDIO_PATH = re.compile(r"^/subtitle-studio/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
IMAGE_STUDIO_PATH = re.compile(r"^/image-studio/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
DOCUMENT_WORKSPACE_PATH = re.compile(r"^/document-workspace/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
CHAT_WORKSPACE_PATH = re.compile(r"^/chat/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
ANALYTICS_WORKSPACE_PATH = re.compile(r"^/analytics/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
WORKBOARD_PATH = re.compile(r"^/workboard/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
CONTENT_HANDOFF_PATH = re.compile(r"^/content/handoffs/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
PARTNER_CRM_PATH = re.compile(r"^/crm/leads/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
_PORTAL_BUILD_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
_PORTAL_BUILD_ID_ENVIRONMENT_KEYS = (
    # Explicit application configuration has priority.  Railway values are
    # intentionally only a build stamp; neither identifier is a credential.
    "APP_BUILD_ID",
    "RAILWAY_GIT_COMMIT_SHA",
    "RAILWAY_DEPLOYMENT_ID",
)
_PORTAL_BUILD_SOURCE_FILES = (
    "portal.css",
    "portal.js",
    "integration.js",
    "service-worker.js",
    "manifest.webmanifest",
    "offline.html",
)


def _safe_portal_build_id(value: object) -> str | None:
    """Return a public-only build identifier, never an arbitrary env value.

    This value is embedded in public HTML and a service-worker script URL, so
    it must be an opaque, bounded cache key rather than a deployment message,
    URL, secret or untrusted HTML fragment.
    """

    candidate = value if isinstance(value, str) else ""
    return candidate if _PORTAL_BUILD_ID.fullmatch(candidate) else None


@lru_cache(maxsize=1)
def _local_portal_build_id() -> str:
    """Hash the public shell source for a deterministic no-environment fallback."""

    digest = hashlib.sha256()
    asset_dir = ROOT / "static" / "portal"
    for filename in _PORTAL_BUILD_SOURCE_FILES:
        digest.update(filename.encode("utf-8"))
        digest.update(b"\0")
        try:
            digest.update((asset_dir / filename).read_bytes())
        except OSError:
            # The fallback remains deterministic even in a partial local
            # checkout; deployment must still supply a complete shell.
            digest.update(b"missing")
        digest.update(b"\0")
    return f"local-{digest.hexdigest()[:20]}"


def _portal_build_id() -> str:
    """Choose a validated deployment ID or a deterministic public-shell hash."""

    for key in _PORTAL_BUILD_ID_ENVIRONMENT_KEYS:
        safe_value = _safe_portal_build_id(os.getenv(key))
        if safe_value:
            return safe_value
    return _local_portal_build_id()


def _portal_asset_version() -> str:
    """Use the same safe build ID for shell URLs and worker generation."""

    return _portal_build_id()


def _title_for(path: str) -> str:
    normalized = path.rstrip("/") or "/"
    if normalized == "/":
        return "TOAN AAS"
    if normalized == "/documents/split":
        return "Tách PDF riêng tư"
    if normalized == "/documents/merge":
        return "Gộp PDF riêng tư"
    if normalized == "/documents/compress":
        return "Tối ưu PDF riêng tư"
    if normalized == "/documents/image-to-pdf":
        return "Ảnh sang PDF riêng tư"
    if normalized == "/documents/pdf-to-images":
        return "PDF sang ảnh riêng tư"
    if normalized == "/documents/pdf-to-word":
        return "PDF có text → Word riêng tư"
    if normalized == "/documents/pdf-ocr":
        return "OCR PDF riêng tư"
    if normalized == "/documents/pdf-ocr-to-word":
        return "OCR PDF → Word riêng tư"
    if normalized == "/notes":
        return "Memory Center"
    if normalized == "/reminders":
        return "Nhắc việc"
    if normalized == "/prompt-library/new":
        return "Template Prompt mới"
    if normalized == "/content-studio/new":
        return "Content Brief mới"
    if normalized == "/voice-studio/new":
        return "Voice direction mới"
    if normalized == "/video-studio/new":
        return "Video plan mới"
    if normalized == "/subtitle-studio/new":
        return "Transcript project mới"
    if normalized == "/image-studio/new":
        return "Artboard mới"
    if normalized == "/document-workspace/new":
        return "Document brief mới"
    if normalized == "/chat/new":
        return "Hội thoại mới"
    if normalized == "/analytics/new":
        return "Báo cáo Analytics mới"
    if normalized == "/workboard/new":
        return "Thẻ công việc mới"
    if normalized == "/content/handoffs/new":
        return "Content Handoff mới"
    if normalized == "/crm/leads/new":
        return "Lead mới"
    if PROMPT_LIBRARY_PATH.fullmatch(normalized):
        return "Prompt Library"
    if CONTENT_STUDIO_PATH.fullmatch(normalized):
        return "Creative Content Studio"
    if VOICE_STUDIO_PATH.fullmatch(normalized):
        return "Voice Studio"
    if VIDEO_STUDIO_PATH.fullmatch(normalized):
        return "Video Production Studio"
    if SUBTITLE_STUDIO_PATH.fullmatch(normalized):
        return "Subtitle & Transcript Workspace"
    if IMAGE_STUDIO_PATH.fullmatch(normalized):
        return "Image Creative Studio"
    if DOCUMENT_WORKSPACE_PATH.fullmatch(normalized):
        return "Document & PDF Workspace"
    if CHAT_WORKSPACE_PATH.fullmatch(normalized):
        return "AI Chat Workspace"
    if ANALYTICS_WORKSPACE_PATH.fullmatch(normalized):
        return "Analytics Workspace"
    if WORKBOARD_PATH.fullmatch(normalized):
        return "Workboard & Review Queue"
    if CONTENT_HANDOFF_PATH.fullmatch(normalized):
        return "Content Handoff"
    if PARTNER_CRM_PATH.fullmatch(normalized):
        return "Partner & Lead CRM"
    if MEDIA_WORKSPACE_PATH.fullmatch(normalized):
        return "Audio Library & Briefing"
    if CAMPAIGN_PLAN_PATH.fullmatch(normalized):
        return "Chi tiết kế hoạch"
    if PROJECT_PATH.fullmatch(normalized):
        return "Project Center"
    for item in ALL_FEATURES:
        if item.route.split("?", 1)[0].rstrip("/") == normalized:
            return item.title
    aliases = {
        "/welcome": "Giới thiệu TOAN AAS", "/login": "Đăng nhập", "/register": "Tạo tài khoản", "/onboarding": "Bắt đầu với TOAN AAS",
        "/campaigns": "Campaign Planner", "/calendar": "Content Calendar", "/approvals": "Self-review Queue", "/projects": "Project Center",
        "/operations": "Operations Center", "/admin/operations": "Operations Autopilot",
        "/image": "Studio ảnh", "/image-studio": "Image Creative Studio", "/document-workspace": "Document & PDF Workspace", "/video": "Studio video", "/video-studio": "Video Production Studio", "/subtitle-studio": "Subtitle & Transcript Workspace", "/voice": "Studio âm thanh", "/music": "Âm nhạc & SFX",
        "/chat": "AI Chat Workspace", "/analytics": "Analytics Workspace", "/features/content": "Content & Chat", "/features/image": "Image Studio", "/features/video": "Video Studio",
        "/features/voice": "Voice Studio", "/features/music": "Music & SFX", "/features/subtitle": "Phụ đề & ngôn ngữ",
        "/features/documents": "Documents & PDF", "/content/handoffs": "Content Handoff", "/crm/leads": "Partner & Lead CRM",
    }
    return aliases.get(normalized, "TOAN AAS")


def _fallback_template() -> str:
    # Keep the fallback compatible with the strict production CSP: bootstrap
    # data lives in inert JSON, never in an inline executable script.
    return """<!doctype html><html lang=\"vi\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>__PORTAL_TITLE__</title><link rel=\"stylesheet\" href=\"/static/portal/portal.css?v=__PORTAL_ASSET_VERSION__\"></head><body><main id=\"portal-root\"></main><script id=\"portal-bootstrap\" type=\"application/json\">__PORTAL_BOOTSTRAP__</script><script src=\"/static/portal/portal.js?v=__PORTAL_ASSET_VERSION__\" defer></script><script src=\"/static/portal/integration.js?v=__PORTAL_ASSET_VERSION__\" defer></script></body></html>"""


def render_portal(path: str) -> HTMLResponse:
    normalized = ("/" + path.lstrip("/")) if path else "/"
    normalized = normalized.rstrip("/") or "/"
    if normalized not in allowed_paths() and normalized not in {"/chat/new", "/analytics/new", "/workboard/new", "/content/handoffs/new", "/crm/leads/new"} and not CAMPAIGN_PLAN_PATH.fullmatch(normalized) and not PROJECT_PATH.fullmatch(normalized) and not PROMPT_LIBRARY_PATH.fullmatch(normalized) and not MEDIA_WORKSPACE_PATH.fullmatch(normalized) and not CONTENT_STUDIO_PATH.fullmatch(normalized) and not VOICE_STUDIO_PATH.fullmatch(normalized) and not VIDEO_STUDIO_PATH.fullmatch(normalized) and not SUBTITLE_STUDIO_PATH.fullmatch(normalized) and not IMAGE_STUDIO_PATH.fullmatch(normalized) and not DOCUMENT_WORKSPACE_PATH.fullmatch(normalized) and not CHAT_WORKSPACE_PATH.fullmatch(normalized) and not ANALYTICS_WORKSPACE_PATH.fullmatch(normalized) and not WORKBOARD_PATH.fullmatch(normalized) and not CONTENT_HANDOFF_PATH.fullmatch(normalized) and not PARTNER_CRM_PATH.fullmatch(normalized) and not any(normalized.startswith(prefix) for prefix in ("/image", "/video", "/voice", "/music", "/subtitle", "/translate", "/dubbing", "/documents", "/document-workspace", "/support", "/tickets", "/admin", "/features", "/content", "/crm", "/tools", "/prompts", "/prompt-library", "/media-workspace", "/content-studio", "/voice-studio", "/video-studio", "/subtitle-studio", "/image-studio", "/caption", "/hashtag", "/hook", "/script", "/storyboard")):
        raise HTTPException(status_code=404, detail="Trang không tồn tại")
    template = TEMPLATE.read_text(encoding="utf-8") if TEMPLATE.exists() else _fallback_template()
    build_id = _portal_build_id()
    payload = {
        "path": normalized,
        "title": _title_for(normalized),
        "apiBase": "/api/v1",
        "catalogUrl": "/api/v1/catalog",
        "authUrl": "/api/v1/auth/me",
        # This public opaque value is deliberately separate from sessions,
        # accounts and API data.  The browser passes it only to the root
        # service-worker URL so each deployed public shell owns one cache.
        "buildId": build_id,
    }
    output = (
        template
        .replace("__PORTAL_TITLE__", html.escape(payload["title"]))
        .replace("__PORTAL_ASSET_VERSION__", build_id)
        .replace("__PORTAL_BOOTSTRAP__", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"))
    )
    return HTMLResponse(output)
