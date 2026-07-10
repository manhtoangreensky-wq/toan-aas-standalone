"""Route-aware portal shell renderer."""

from __future__ import annotations

import html
import json
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import HTMLResponse

from copyfast_registry import ALL_FEATURES, allowed_paths


ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "templates" / "portal_shell.html"


def _title_for(path: str) -> str:
    normalized = path.rstrip("/") or "/"
    if normalized == "/":
        return "TOAN AAS"
    for item in ALL_FEATURES:
        if item.route.split("?", 1)[0].rstrip("/") == normalized:
            return item.title
    aliases = {
        "/login": "Đăng nhập", "/register": "Tạo tài khoản", "/onboarding": "Bắt đầu với TOAN AAS",
        "/image": "Studio ảnh", "/video": "Studio video", "/voice": "Studio âm thanh", "/music": "Âm nhạc & SFX",
    }
    return aliases.get(normalized, "TOAN AAS")


def _fallback_template() -> str:
    # Keep the fallback compatible with the strict production CSP: bootstrap
    # data lives in inert JSON, never in an inline executable script.
    return """<!doctype html><html lang=\"vi\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>__PORTAL_TITLE__</title><link rel=\"stylesheet\" href=\"/static/portal/portal.css\"></head><body><main id=\"portal-root\"></main><script id=\"portal-bootstrap\" type=\"application/json\">__PORTAL_BOOTSTRAP__</script><script src=\"/static/portal/portal.js\" defer></script><script src=\"/static/portal/integration.js\" defer></script></body></html>"""


def render_portal(path: str) -> HTMLResponse:
    normalized = ("/" + path.lstrip("/")) if path else "/"
    normalized = normalized.rstrip("/") or "/"
    if normalized not in allowed_paths() and not any(normalized.startswith(prefix) for prefix in ("/image", "/video", "/voice", "/music", "/subtitle", "/translate", "/dubbing", "/documents", "/support", "/tickets", "/admin", "/features", "/content", "/tools", "/prompts", "/caption", "/hashtag", "/hook", "/script", "/storyboard")):
        raise HTTPException(status_code=404, detail="Trang không tồn tại")
    template = TEMPLATE.read_text(encoding="utf-8") if TEMPLATE.exists() else _fallback_template()
    payload = {
        "path": normalized,
        "title": _title_for(normalized),
        "apiBase": "/api/v1",
        "catalogUrl": "/api/v1/catalog",
        "authUrl": "/api/v1/auth/me",
    }
    output = template.replace("__PORTAL_TITLE__", html.escape(payload["title"])).replace("__PORTAL_BOOTSTRAP__", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"))
    return HTMLResponse(output)
