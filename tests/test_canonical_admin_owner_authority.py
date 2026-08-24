"""Canonical Admin authority contracts for live Bot roles."""

from __future__ import annotations

import asyncio
import importlib

import pytest
from fastapi import HTTPException
from starlette.requests import Request


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "path": "/api/v1/admin/summary",
            "raw_path": b"/api/v1/admin/summary",
            "query_string": b"",
            "headers": [],
            "client": ("test-client", 12345),
            "server": ("testserver", 443),
        }
    )


def _run_guard(monkeypatch, *, ok: bool, role: str) -> dict:
    copyfast_auth = importlib.import_module("copyfast_auth")
    copyfast_bridge = importlib.import_module("copyfast_bridge")

    async def bridge_request(*_args, **_kwargs) -> dict:
        return {"ok": ok, "data": {"role": role}}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", bridge_request)
    account = {"id": "web-admin", "role": "admin", "canonical_user_id": "canonical-owner-id"}
    return asyncio.run(copyfast_auth._require_current_canonical_admin(_request(), account))


def test_canonical_admin_role_is_allowed(monkeypatch) -> None:
    account = _run_guard(monkeypatch, ok=True, role="admin")

    assert account["role"] == "admin"


def test_canonical_owner_role_is_allowed_after_normalization(monkeypatch) -> None:
    account = _run_guard(monkeypatch, ok=True, role=" Owner ")

    assert account["role"] == "admin"


@pytest.mark.parametrize("role", ["user", "", "unknown"])
def test_non_admin_canonical_roles_are_forbidden(monkeypatch, role: str) -> None:
    with pytest.raises(HTTPException) as exc_info:
        _run_guard(monkeypatch, ok=True, role=role)

    assert exc_info.value.status_code == 403


def test_failed_bridge_envelope_is_forbidden_even_for_owner(monkeypatch) -> None:
    with pytest.raises(HTTPException) as exc_info:
        _run_guard(monkeypatch, ok=False, role="owner")

    assert exc_info.value.status_code == 403
