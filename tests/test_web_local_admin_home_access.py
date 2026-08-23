"""Runtime contracts for the Web-local Admin landing-page authority boundary."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import HTMLResponse

import app as webapp


def _request(path: str) -> Request:
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "headers": [],
            "client": ("test-client", 12345),
            "server": ("testserver", 443),
        }
    )


def _portal_response(_path: str, *, interface_locale: str | None = None) -> HTMLResponse:
    assert interface_locale == "vi"
    return HTMLResponse("<main>Admin ERP</main>")


def test_web_local_admin_opens_admin_home_without_canonical_bridge(monkeypatch) -> None:
    account = {"id": "web-admin", "role": "admin", "canonical_user_id": None, "locale": "vi"}
    guard_calls: list[str] = []

    def local_admin(_request: Request) -> dict:
        guard_calls.append("web_local_admin")
        return account

    async def canonical_admin(_request: Request) -> dict:
        guard_calls.append("canonical_admin")
        raise AssertionError("Exact /admin must not call the canonical Bot bridge")

    monkeypatch.setattr(webapp.copyfast_auth, "require_admin", local_admin)
    monkeypatch.setattr(webapp, "require_canonical_admin", canonical_admin)
    monkeypatch.setattr(webapp, "current_session", lambda _request: {"account": account})
    monkeypatch.setattr(webapp, "render_portal", _portal_response)

    response = asyncio.run(webapp.page("admin", _request("/admin")))

    assert response.status_code == 200
    assert response.media_type == "text/html"
    assert guard_calls == ["web_local_admin"]


def test_customer_remains_forbidden_from_admin_home(monkeypatch) -> None:
    account = {"id": "customer", "role": "user", "canonical_user_id": None, "locale": "vi"}

    def local_denied(_request: Request) -> dict:
        raise HTTPException(status_code=403, detail="Chỉ quản trị viên được phép truy cập")

    async def canonical_denied(_request: Request) -> dict:
        raise HTTPException(status_code=403, detail="Chỉ quản trị viên được phép truy cập")

    monkeypatch.setattr(webapp.copyfast_auth, "require_admin", local_denied)
    monkeypatch.setattr(webapp, "require_canonical_admin", canonical_denied)
    monkeypatch.setattr(webapp, "current_session", lambda _request: {"account": account})

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(webapp.page("admin", _request("/admin")))

    assert exc_info.value.status_code == 403


def test_canonical_admin_child_route_keeps_live_bot_guard(monkeypatch) -> None:
    guard_calls: list[str] = []

    def unexpected_local_guard(_request: Request) -> dict:
        raise AssertionError("Canonical child route must not use only the Web-local role")

    async def canonical_denied(_request: Request) -> dict:
        guard_calls.append("canonical_admin")
        raise HTTPException(status_code=403, detail="Tài khoản chưa có quyền quản trị canonical")

    monkeypatch.setattr(webapp.copyfast_auth, "require_admin", unexpected_local_guard)
    monkeypatch.setattr(webapp, "require_canonical_admin", canonical_denied)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(webapp.page("admin/users", _request("/admin/users")))

    assert exc_info.value.status_code == 403
    assert guard_calls == ["canonical_admin"]
