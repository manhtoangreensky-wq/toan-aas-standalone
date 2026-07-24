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
from copyfast_starter_kits import STARTER_KIT_BY_KEY


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
STARTER_KIT_KEYS = frozenset(STARTER_KIT_BY_KEY)
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
    "portal-i18n.js",
    "portal.js",
    "integration.js",
    "service-worker.js",
    "manifest.webmanifest",
    "offline.html",
)

# The portal shell is rendered before its browser catalog and hydration
# complete. Keep this tiny first-paint catalog server-owned and deliberately
# separate from customer content, generated output, workflow languages and
# Bot preferences. A signed Web profile may choose only these reviewed
# presentation locales; anonymous/public pages remain Vietnamese by design.
_INTERFACE_LOCALES = frozenset({"vi", "en", "zh"})
_PORTAL_SHELL_COPY = {
    "vi": {
        "html_lang": "vi",
        "description": "TOAN AAS Workspace — giao diện Web an toàn.",
        "skip_navigation": "Bỏ qua điều hướng",
        "main_navigation": "Điều hướng chính",
        "quick_navigation": "Điều hướng nhanh",
        "boot_message": "Đang khởi tạo giao diện TOAN AAS…",
        "noscript": "Vui lòng bật JavaScript để dùng ứng dụng TOAN AAS.",
        "workspace_title": "TOAN AAS Workspace",
    },
    "en": {
        "html_lang": "en",
        "description": "TOAN AAS Workspace — secure Web interface.",
        "skip_navigation": "Skip navigation",
        "main_navigation": "Main navigation",
        "quick_navigation": "Quick navigation",
        "boot_message": "Starting TOAN AAS…",
        "noscript": "Please enable JavaScript to use TOAN AAS.",
        "workspace_title": "TOAN AAS Workspace",
    },
    "zh": {
        "html_lang": "zh-CN",
        "description": "TOAN AAS 工作台 — 安全的 Web 界面。",
        "skip_navigation": "跳过导航",
        "main_navigation": "主导航",
        "quick_navigation": "快捷导航",
        "boot_message": "正在启动 TOAN AAS…",
        "noscript": "请启用 JavaScript 以使用 TOAN AAS。",
        "workspace_title": "TOAN AAS 工作台",
    },
}
_PORTAL_SHELL_TITLES = {
    "/": {"vi": "TOAN AAS", "en": "TOAN AAS", "zh": "TOAN AAS"},
    "/app": {"vi": "TOAN AAS Workspace", "en": "TOAN AAS Workspace", "zh": "TOAN AAS 工作台"},
    "/dashboard": {"vi": "Tổng quan · TOAN AAS", "en": "Overview · TOAN AAS", "zh": "概览 · TOAN AAS"},
    "/login": {"vi": "Đăng nhập · TOAN AAS", "en": "Sign in · TOAN AAS", "zh": "登录 · TOAN AAS"},
    "/register": {"vi": "Tạo tài khoản · TOAN AAS", "en": "Create account · TOAN AAS", "zh": "创建账户 · TOAN AAS"},
    "/onboarding": {"vi": "Bắt đầu với TOAN AAS", "en": "Get started with TOAN AAS", "zh": "开始使用 TOAN AAS"},
    "/account": {"vi": "Tài khoản · TOAN AAS", "en": "Account · TOAN AAS", "zh": "账户 · TOAN AAS"},
    "/account/interface-language": {"vi": "Ngôn ngữ giao diện · TOAN AAS", "en": "Interface language · TOAN AAS", "zh": "界面语言 · TOAN AAS"},
    "/workspace/setup": {"vi": "Thiết lập workspace · TOAN AAS", "en": "Workspace setup · TOAN AAS", "zh": "工作台设置 · TOAN AAS"},
    "/workspace-menu": {"vi": "Chuyển workspace · TOAN AAS", "en": "Switch workspace · TOAN AAS", "zh": "切换工作台 · TOAN AAS"},
    "/starter-kits": {"vi": "Starter Kits · TOAN AAS", "en": "Starter Kits · TOAN AAS", "zh": "入门套件 · TOAN AAS"},
}


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
    if normalized == "/starter-kits":
        return "Starter Kits"
    if normalized.startswith("/starter-kits/"):
        key = normalized.removeprefix("/starter-kits/")
        kit = STARTER_KIT_BY_KEY.get(key)
        if kit:
            return f"Starter Kit · {kit['title']}"
    if normalized == "/content/handoffs/new":
        return "Content Handoff mới"
    if normalized == "/crm/leads/new":
        return "Lead mới"
    if normalized == "/crm/consultations/new":
        return "Gửi nhu cầu tư vấn"
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


def _interface_locale(value: object) -> str:
    """Normalize a signed Web presentation locale without accepting aliases.

    Profile writes already enforce this allowlist in ``copyfast_auth``. The
    shell repeats it because this module also serves public pages and must
    never interpolate a request/header/query value into HTML metadata.
    """

    candidate = value.strip().lower() if isinstance(value, str) else ""
    return candidate if candidate in _INTERFACE_LOCALES else "vi"


def _shell_title_for(path: str, locale: str) -> str:
    normalized = path.rstrip("/") or "/"
    titles = _PORTAL_SHELL_TITLES.get(normalized)
    if titles:
        return titles[locale]
    # Do not present a Vietnamese route title as if it were reviewed English
    # or Simplified Chinese. The browser catalog upgrades individual workspace
    # titles as those renderers opt in; the first paint stays truthful now.
    return _PORTAL_SHELL_COPY[locale]["workspace_title"]


def _fallback_template() -> str:
    # Keep the fallback compatible with the strict production CSP: bootstrap
    # data lives in inert JSON, never in an inline executable script.
    return """<!doctype html><html lang=\"__PORTAL_HTML_LANG__\" dir=\"ltr\" data-portal-locale=\"__PORTAL_LOCALE__\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><meta name=\"description\" content=\"__PORTAL_DESCRIPTION__\"><title>__PORTAL_TITLE__</title><link rel=\"stylesheet\" href=\"/static/portal/portal.css?v=__PORTAL_ASSET_VERSION__\"></head><body><a class=\"skip-link\" href=\"#portal-main\">__PORTAL_SKIP_NAVIGATION__</a><main id=\"portal-root\" aria-label=\"__PORTAL_MAIN_NAVIGATION__\"><p>__PORTAL_BOOT_MESSAGE__</p></main><noscript>__PORTAL_NOSCRIPT__</noscript><script id=\"portal-bootstrap\" type=\"application/json\">__PORTAL_BOOTSTRAP__</script><script src=\"/static/portal/portal-i18n.js?v=__PORTAL_ASSET_VERSION__\" defer></script><script src=\"/static/portal/portal.js?v=__PORTAL_ASSET_VERSION__\" defer></script><script src=\"/static/portal/integration.js?v=__PORTAL_ASSET_VERSION__\" defer></script></body></html>"""


def render_portal(path: str, *, interface_locale: str | None = None) -> HTMLResponse:
    normalized = ("/" + path.lstrip("/")) if path else "/"
    normalized = normalized.rstrip("/") or "/"
    is_starter_kit_detail = normalized.startswith("/starter-kits/") and normalized.removeprefix("/starter-kits/") in STARTER_KIT_KEYS
    if normalized not in allowed_paths() and normalized not in {"/chat/new", "/analytics/new", "/workboard/new", "/content/handoffs/new", "/crm/leads/new", "/starter-kits"} and not is_starter_kit_detail and not CAMPAIGN_PLAN_PATH.fullmatch(normalized) and not PROJECT_PATH.fullmatch(normalized) and not PROMPT_LIBRARY_PATH.fullmatch(normalized) and not MEDIA_WORKSPACE_PATH.fullmatch(normalized) and not CONTENT_STUDIO_PATH.fullmatch(normalized) and not VOICE_STUDIO_PATH.fullmatch(normalized) and not VIDEO_STUDIO_PATH.fullmatch(normalized) and not SUBTITLE_STUDIO_PATH.fullmatch(normalized) and not IMAGE_STUDIO_PATH.fullmatch(normalized) and not DOCUMENT_WORKSPACE_PATH.fullmatch(normalized) and not CHAT_WORKSPACE_PATH.fullmatch(normalized) and not ANALYTICS_WORKSPACE_PATH.fullmatch(normalized) and not WORKBOARD_PATH.fullmatch(normalized) and not CONTENT_HANDOFF_PATH.fullmatch(normalized) and not PARTNER_CRM_PATH.fullmatch(normalized) and not any(normalized.startswith(prefix) for prefix in ("/image", "/video", "/voice", "/music", "/subtitle", "/translate", "/dubbing", "/documents", "/document-workspace", "/support", "/tickets", "/admin", "/features", "/content", "/crm", "/tools", "/prompts", "/prompt-library", "/media-workspace", "/content-studio", "/voice-studio", "/video-studio", "/subtitle-studio", "/image-studio", "/caption", "/hashtag", "/hook", "/script", "/storyboard")):
        raise HTTPException(status_code=404, detail="Trang không tồn tại")
    locale = _interface_locale(interface_locale)
    shell_copy = _PORTAL_SHELL_COPY[locale]
    template = TEMPLATE.read_text(encoding="utf-8") if TEMPLATE.exists() else _fallback_template()
    build_id = _portal_build_id()
    payload = {
        "path": normalized,
        "title": _shell_title_for(normalized, locale),
        # This carries only an allowlisted presentation code. It does not
        # disclose account/profile data and is never a persistence channel.
        "interfaceLocale": locale,
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
        .replace("__PORTAL_HTML_LANG__", shell_copy["html_lang"])
        .replace("__PORTAL_LOCALE__", locale)
        .replace("__PORTAL_DESCRIPTION__", html.escape(shell_copy["description"], quote=True))
        .replace("__PORTAL_SKIP_NAVIGATION__", html.escape(shell_copy["skip_navigation"]))
        .replace("__PORTAL_MAIN_NAVIGATION__", html.escape(shell_copy["main_navigation"], quote=True))
        .replace("__PORTAL_QUICK_NAVIGATION__", html.escape(shell_copy["quick_navigation"], quote=True))
        .replace("__PORTAL_BOOT_MESSAGE__", html.escape(shell_copy["boot_message"]))
        .replace("__PORTAL_NOSCRIPT__", html.escape(shell_copy["noscript"]))
        .replace("__PORTAL_ASSET_VERSION__", build_id)
        .replace("__PORTAL_BOOTSTRAP__", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"))
    )
    return HTMLResponse(output)
