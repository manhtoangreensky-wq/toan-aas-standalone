"""Route-aware portal shell renderer."""

from __future__ import annotations

import html
import json
from pathlib import Path
import re

from fastapi import HTTPException
from fastapi.responses import HTMLResponse

from copyfast_registry import ALL_FEATURES, allowed_paths


ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "templates" / "portal_shell.html"
CAMPAIGN_PLAN_PATH = re.compile(r"^/campaigns/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)


def _portal_asset_version() -> str:
    """Use a deterministic local asset stamp to prevent stale portal shells."""
    asset_dir = ROOT / "static" / "portal"
    try:
        newest = max(
            (item.stat().st_mtime_ns for item in asset_dir.glob("*") if item.is_file()),
            default=0,
        )
    except OSError:
        newest = 0
    return str(newest or 1)


def _title_for(path: str) -> str:
    normalized = path.rstrip("/") or "/"
    if normalized == "/":
        return "TOAN AAS"
    if CAMPAIGN_PLAN_PATH.fullmatch(normalized):
        return "Chi tiết kế hoạch"
    for item in ALL_FEATURES:
        if item.route.split("?", 1)[0].rstrip("/") == normalized:
            return item.title
    aliases = {
        "/login": "Đăng nhập", "/register": "Tạo tài khoản", "/onboarding": "Bắt đầu với TOAN AAS",
        "/campaigns": "Campaign Planner", "/calendar": "Content Calendar", "/approvals": "Self-review Queue",
        "/image": "Studio ảnh", "/video": "Studio video", "/voice": "Studio âm thanh", "/music": "Âm nhạc & SFX",
        "/features/content": "Content & Chat", "/features/image": "Image Studio", "/features/video": "Video Studio",
        "/features/voice": "Voice Studio", "/features/music": "Music & SFX", "/features/subtitle": "Phụ đề & ngôn ngữ",
        "/features/documents": "Documents & PDF",
    }
    return aliases.get(normalized, "TOAN AAS")


def _fallback_template() -> str:
    # Keep the fallback compatible with the strict production CSP: bootstrap
    # data lives in inert JSON, never in an inline executable script.
    return """<!doctype html><html lang=\"vi\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>__PORTAL_TITLE__</title><link rel=\"stylesheet\" href=\"/static/portal/portal.css?v=__PORTAL_ASSET_VERSION__\"></head><body><main id=\"portal-root\"></main><script id=\"portal-bootstrap\" type=\"application/json\">__PORTAL_BOOTSTRAP__</script><script src=\"/static/portal/portal.js?v=__PORTAL_ASSET_VERSION__\" defer></script><script src=\"/static/portal/integration.js?v=__PORTAL_ASSET_VERSION__\" defer></script></body></html>"""


def render_portal(path: str) -> HTMLResponse:
    normalized = ("/" + path.lstrip("/")) if path else "/"
    normalized = normalized.rstrip("/") or "/"
    if normalized not in allowed_paths() and not CAMPAIGN_PLAN_PATH.fullmatch(normalized) and not any(normalized.startswith(prefix) for prefix in ("/image", "/video", "/voice", "/music", "/subtitle", "/translate", "/dubbing", "/documents", "/support", "/tickets", "/admin", "/features", "/content", "/tools", "/prompts", "/caption", "/hashtag", "/hook", "/script", "/storyboard")):
        raise HTTPException(status_code=404, detail="Trang không tồn tại")
    template = TEMPLATE.read_text(encoding="utf-8") if TEMPLATE.exists() else _fallback_template()
    payload = {
        "path": normalized,
        "title": _title_for(normalized),
        "apiBase": "/api/v1",
        "catalogUrl": "/api/v1/catalog",
        "authUrl": "/api/v1/auth/me",
    }
    output = (
        template
        .replace("__PORTAL_TITLE__", html.escape(payload["title"]))
        .replace("__PORTAL_ASSET_VERSION__", _portal_asset_version())
        .replace("__PORTAL_BOOTSTRAP__", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"))
    )
    return HTMLResponse(output)
