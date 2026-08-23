# Web-local Admin Home Access Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cho phép signed Web Admin mở trang tổng quan HTML `/admin` mà không hạ bất kỳ guard canonical API/write nào.

**Architecture:** Chỉ tách exact route `/admin` sang `copyfast_auth.require_admin(request)`. Mọi `/admin/*` canonical route tiếp tục dùng `require_canonical_admin`; navigation endpoint tiếp tục quyết định nhóm Web-local/canonical từ server.

**Tech Stack:** FastAPI, Python 3, pytest, signed SQLite session, server-authorized Admin ERP navigation.

---

## File map và khóa phạm vi

- Create `tests/test_web_local_admin_home_access.py`: tái hiện contradiction và bảo vệ ba authority boundary.
- Modify `app.py:2755-2768`: tách exact `/admin` khỏi canonical child route family.
- Regenerate `docs/migration/README.md`, `reports/migration/preflight.json`, `reports/migration/web_inventory.json` nếu audit fingerprint thay đổi.
- Không sửa `copyfast_auth.py`, `copyfast_admin_erp_navigation.py`, CSS/JS, database/schema, ENV/secret, wallet/PayOS/provider/job.

## Task 1: RED — khóa contract trang Admin Web-local

**Files:**
- Create: `tests/test_web_local_admin_home_access.py`
- Read: `app.py:2699-2787`

- [ ] **Step 1: Tạo test file với nội dung đầy đủ**

```python
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
```

- [ ] **Step 2: Chạy RED trước khi sửa production**

Run:

```powershell
py -m pytest tests/test_web_local_admin_home_access.py -q
```

Expected: đúng `1 failed, 2 passed`; failure là `Exact /admin must not call the canonical Bot bridge`.

## Task 2: GREEN — sửa một authority branch trong `app.py`

**Files:**
- Modify: `app.py:2755-2768`
- Test: `tests/test_web_local_admin_home_access.py`

- [ ] **Step 1: Thay đúng nhánh cuối của Admin page guard**

Thay:

```python
    elif normalized == "/admin" or (normalized.startswith("/admin/") and normalized != "/admin/login"):
        await require_canonical_admin(request)
```

bằng:

```python
    elif normalized == "/admin":
        copyfast_auth.require_admin(request)
    elif normalized.startswith("/admin/") and normalized != "/admin/login":
        await require_canonical_admin(request)
```

Không sửa thứ tự hai nhánh Support/Web-local ở phía trên.

- [ ] **Step 2: Chạy GREEN mục tiêu**

Run:

```powershell
py -m pytest tests/test_web_local_admin_home_access.py -q
```

Expected: `3 passed`.

- [ ] **Step 3: Chạy compile và Admin regression**

Run:

```powershell
py -m py_compile app.py
py -m pytest tests/test_web_local_admin_home_access.py tests/test_admin_erp_navigation.py tests/test_aura_app_surface_shell_contracts.py tests/test_aura_erp_data_surfaces_contracts.py tests/test_product_harmony_ui_contracts.py tests/test_admin_customer_directory_portal_contracts.py -q
git diff --check
```

Expected: compile exit `0`; toàn bộ test pass; diff check exit `0`.

- [ ] **Step 4: Soi phạm vi rồi commit source**

Run:

```powershell
git diff --name-only
git diff -- app.py tests/test_web_local_admin_home_access.py
git add -- app.py tests/test_web_local_admin_home_access.py
git commit -m "fix(admin): allow web admin home shell"
```

Expected: source commit chỉ chứa đúng hai file.

## Task 3: Cập nhật migration evidence bắt buộc

**Files:**
- Modify generated: `docs/migration/README.md`
- Modify generated: `reports/migration/preflight.json`
- Modify generated: `reports/migration/web_inventory.json`

- [ ] **Step 1: Sinh evidence từ source commit sạch**

Run:

```powershell
$sourceSha = (git rev-parse HEAD).Trim()
py scripts/migration/audit_bot_to_web.py --bot-root "D:\TOANAAS\bot telegram" --web-root . --bot-baseline-sha b29d0d474974075f4cba963d2c510f49d2d1b3e4 --web-revision $sourceSha --report-dir reports/migration --docs-dir docs/migration
```

Expected: exit `0`; không import/run Bot, FastAPI, database, provider hoặc payment service.

- [ ] **Step 2: Khóa đúng generated delta và commit evidence**

Run:

```powershell
git status --short
git diff --check
git add -- docs/migration/README.md reports/migration/preflight.json reports/migration/web_inventory.json
git commit -m "chore(audit): bind web-local admin home evidence"
```

Expected: evidence commit chỉ chứa ba file generated trên.

## Task 4: Báo cáo BUILT cho Codex, không tự ship

- [ ] **Step 1: Trả báo cáo chính xác**

```text
SPEC_ID=ADMIN-HOME-ACCESS-001
STATUS=BUILT|FAILED|BLOCKED
BASE_SHA=ff2d8ea68b64f2759b292b840dcfcbfdead7e928
HEAD_SHA=<git rev-parse HEAD>
FILES_CHANGED=<exact list>
DIFF_SUMMARY=<short summary>
RED_OUTPUT=<exact 1 failed, 2 passed evidence>
VERIFY_COMMANDS=<exact commands>
VERIFY_OUTPUT=<exact pass counts>
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
COMMIT=<source and evidence commits>
PUSH=NO
PR=NO
MERGE=NO
DEPLOY=NO
BLOCKERS=<none or exact blocker>
```

Codex sẽ tự review, push, PR, merge, deploy và live test sau hai vòng review đạt.
