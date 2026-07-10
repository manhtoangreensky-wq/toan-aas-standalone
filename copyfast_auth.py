"""Secure, web-owned account/session layer for the COPYFAST portal."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import os
import re
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from copyfast_db import ensure_copyfast_schema, transaction, utc_now


router = APIRouter(tags=["COPYFAST Auth"])

SESSION_COOKIE = "toan_aas_session"
SESSION_TTL_HOURS = max(1, int(os.environ.get("WEB_SESSION_TTL_HOURS", "24")))
LINK_TTL_MINUTES = max(1, int(os.environ.get("TELEGRAM_LINK_TTL_MINUTES", "10")))
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def envelope(ok: bool, message: str, *, data: dict | None = None, status_name: str = "completed", error_code: str | None = None) -> dict:
    return {
        "ok": ok,
        "status": status_name,
        "message": message,
        "data": data or {},
        "error_code": error_code,
    }


def _secret() -> bytes:
    value = os.environ.get("WEB_SESSION_SECRET", "").strip()
    environment = os.environ.get("APP_ENV", os.environ.get("ENVIRONMENT", "development")).lower()
    if not value and environment in {"production", "prod"}:
        raise RuntimeError("WEB_SESSION_SECRET chưa được cấu hình")
    return (value or "copyfast-local-development-secret-only").encode("utf-8")


def _cookie_secure() -> bool:
    return os.environ.get("WEB_COOKIE_SECURE", "").lower() in {"1", "true", "yes"} or os.environ.get("APP_ENV", "").lower() in {"production", "prod"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _expiry(hours: int = SESSION_TTL_HOURS) -> str:
    return (_now() + timedelta(hours=hours)).isoformat(timespec="seconds")


def _link_expiry() -> str:
    return (_now() + timedelta(minutes=LINK_TTL_MINUTES)).isoformat(timespec="seconds")


def _as_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return "scrypt$16384$8$1${}${}".format(
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(derived).decode("ascii"),
    )


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_b64, digest_b64 = encoded.split("$", 5)
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_b64.encode("ascii"))
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected))
        return hmac.compare_digest(actual, expected)
    except (TypeError, ValueError):
        return False


def _sign_session(session_id: str) -> str:
    return hmac.new(_secret(), session_id.encode("utf-8"), hashlib.sha256).hexdigest()


def _session_cookie_value(session_id: str) -> str:
    return f"{session_id}.{_sign_session(session_id)}"


def _parse_session_cookie(value: str | None) -> str | None:
    if not value or "." not in value:
        return None
    session_id, signature = value.rsplit(".", 1)
    if not session_id or not hmac.compare_digest(signature, _sign_session(session_id)):
        return None
    return session_id


def _account_payload(row: tuple) -> dict:
    return {
        "id": row[0],
        "email": row[1],
        "display_name": row[2] or "",
        "canonical_user_id": row[3],
        "role": row[4] or "user",
    }


def _record_audit(conn, *, account_id: str | None, canonical_user_id: str | None, action: str, request_id: str, target: str = "", outcome: str = "ok", detail: str = "") -> None:
    conn.execute(
        """INSERT INTO web_audit_events
        (id, account_id, canonical_user_id, action, request_id, target, outcome, detail, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), account_id, canonical_user_id, action, request_id, target, outcome, detail[:500], utc_now()),
    )


def _request_id(request: Request) -> str:
    return request.headers.get("X-Request-ID", "").strip()[:80] or str(uuid.uuid4())


def current_session(request: Request) -> dict:
    ensure_copyfast_schema()
    session_id = _parse_session_cookie(request.cookies.get(SESSION_COOKIE))
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Vui lòng đăng nhập để tiếp tục")
    with transaction() as conn:
        row = conn.execute(
            """SELECT s.id, s.csrf_token, s.expires_at, a.id, a.email, a.display_name,
                      a.canonical_user_id, a.role_cache, a.is_active
               FROM web_sessions s JOIN web_accounts a ON a.id=s.account_id
               WHERE s.id=? AND s.revoked_at IS NULL""",
            (session_id,),
        ).fetchone()
        if not row or not row[8] or _as_time(row[2]) <= _now():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập đã hết hạn")
        conn.execute("UPDATE web_sessions SET last_seen_at=? WHERE id=?", (utc_now(), session_id))
    return {
        "session_id": row[0],
        "csrf_token": row[1],
        "expires_at": row[2],
        "account": {
            "id": row[3],
            "email": row[4],
            "display_name": row[5] or "",
            "canonical_user_id": row[6],
            "role": row[7] or "user",
        },
    }


def require_account(request: Request) -> dict:
    return current_session(request)["account"]


def require_admin(request: Request) -> dict:
    session = current_session(request)
    if session["account"]["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chỉ quản trị viên được phép truy cập")
    return session["account"]


async def require_canonical_admin(request: Request) -> dict:
    """Require both the signed web session and the bot's current admin role.

    The web session deliberately keeps only a cached display role so the UI can
    render without exposing any Telegram credential.  Privileged *pages* must
    still ask the private core before serving their HTML: an account which has
    since lost bot admin access cannot keep browsing Admin ERP from a stale
    cookie.  All privileged JSON actions are independently checked again by
    the bot bridge.
    """
    account = require_admin(request)
    canonical_user_id = str(account.get("canonical_user_id") or "").strip()
    if not canonical_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản chưa có quyền quản trị canonical")
    # Import lazily to keep the session module usable in isolated auth tests.
    from copyfast_bridge import bridge_request

    result = await bridge_request(
        "GET",
        "/internal/v1/me",
        params={"user_id": canonical_user_id},
        request_id=_request_id(request),
        actor_id=canonical_user_id,
    )
    current_role = str((result.get("data") or {}).get("role") or "")
    if not result.get("ok") or current_role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Quyền quản trị canonical chưa được xác nhận")
    return account


def require_csrf(request: Request) -> dict:
    session = current_session(request)
    supplied = request.headers.get("X-CSRF-Token", "")
    if not supplied or not hmac.compare_digest(supplied, session["csrf_token"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token không hợp lệ")
    return session["account"]


def require_admin_csrf(request: Request) -> dict:
    account = require_csrf(request)
    if account["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chỉ quản trị viên được phép thực hiện thao tác này")
    return account


def _create_session(response: Response, account_id: str) -> dict:
    ensure_copyfast_schema()
    session_id = str(uuid.uuid4())
    csrf_token = secrets.token_urlsafe(32)
    expires_at = _expiry()
    now = utc_now()
    with transaction() as conn:
        conn.execute(
            """INSERT INTO web_sessions (id, account_id, csrf_token, expires_at, created_at, last_seen_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, account_id, csrf_token, expires_at, now, now),
        )
    response.set_cookie(
        SESSION_COOKIE,
        _session_cookie_value(session_id),
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        max_age=SESSION_TTL_HOURS * 3600,
        path="/",
    )
    return {"csrf_token": csrf_token, "expires_at": expires_at}


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=256)
    display_name: str = Field(default="", max_length=120)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class LinkConfirmation(BaseModel):
    code: str = Field(min_length=8, max_length=128)
    canonical_user_id: str = Field(min_length=1, max_length=128)
    role: str = Field(default="user", max_length=32)
    display_name: str = Field(default="", max_length=120)


@router.post("/register")
async def register(payload: RegisterRequest, request: Request, response: Response):
    email = payload.email.strip().lower()
    if not EMAIL_PATTERN.fullmatch(email):
        return envelope(False, "Email không hợp lệ", status_name="failed", error_code="INVALID_EMAIL")
    ensure_copyfast_schema()
    account_id = str(uuid.uuid4())
    now = utc_now()
    try:
        with transaction() as conn:
            conn.execute(
                """INSERT INTO web_accounts
                (id, email, password_hash, display_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (account_id, email, _password_hash(payload.password), payload.display_name.strip(), now, now),
            )
            _record_audit(conn, account_id=account_id, canonical_user_id=None, action="auth.register", request_id=_request_id(request))
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            return envelope(False, "Email đã được sử dụng", status_name="failed", error_code="EMAIL_EXISTS")
        raise
    session = _create_session(response, account_id)
    return envelope(True, "Đăng ký thành công. Hãy liên kết Telegram để dùng dữ liệu bot.", data={"account_id": account_id, **session}, status_name="awaiting_confirm")


@router.post("/login")
async def login(payload: LoginRequest, request: Request, response: Response):
    ensure_copyfast_schema()
    email = payload.email.strip().lower()
    with transaction() as conn:
        row = conn.execute(
            "SELECT id, email, password_hash, display_name, canonical_user_id, role_cache, is_active FROM web_accounts WHERE email=?",
            (email,),
        ).fetchone()
        if not row or not row[6] or not _verify_password(payload.password, row[2]):
            _record_audit(conn, account_id=row[0] if row else None, canonical_user_id=None, action="auth.login", request_id=_request_id(request), outcome="denied")
            return envelope(False, "Email hoặc mật khẩu không đúng", status_name="failed", error_code="LOGIN_DENIED")
        account = {
            "id": row[0], "email": row[1], "display_name": row[3] or "",
            "canonical_user_id": row[4], "role": row[5] or "user",
        }
        _record_audit(conn, account_id=row[0], canonical_user_id=row[4], action="auth.login", request_id=_request_id(request))
    session = _create_session(response, account["id"])
    return envelope(True, "Đăng nhập thành công", data={"account": account, **session})


@router.post("/logout")
async def logout(request: Request, response: Response, account: dict = Depends(require_csrf)):
    session_id = _parse_session_cookie(request.cookies.get(SESSION_COOKIE))
    with transaction() as conn:
        conn.execute("UPDATE web_sessions SET revoked_at=? WHERE id=?", (utc_now(), session_id))
        _record_audit(conn, account_id=account["id"], canonical_user_id=account["canonical_user_id"], action="auth.logout", request_id=_request_id(request))
    response.delete_cookie(SESSION_COOKIE, path="/")
    return envelope(True, "Đã đăng xuất")


@router.get("/me")
async def me(request: Request, account: dict = Depends(require_account)):
    session = current_session(request)
    return envelope(True, "Phiên hợp lệ", data={"account": account, "csrf_token": session["csrf_token"], "expires_at": session["expires_at"]})


@router.post("/telegram/link/start")
async def start_telegram_link(request: Request, account: dict = Depends(require_csrf)):
    code = secrets.token_urlsafe(18).replace("-", "A").replace("_", "B")
    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    with transaction() as conn:
        conn.execute("DELETE FROM telegram_link_codes WHERE account_id=? AND consumed_at IS NULL", (account["id"],))
        conn.execute(
            """INSERT INTO telegram_link_codes (code_hash, account_id, expires_at, created_at)
            VALUES (?, ?, ?, ?)""",
            (code_hash, account["id"], _link_expiry(), utc_now()),
        )
        _record_audit(conn, account_id=account["id"], canonical_user_id=account["canonical_user_id"], action="auth.telegram_link_start", request_id=_request_id(request))
    bot_username = os.environ.get("BOT_USERNAME", "").lstrip("@")
    return envelope(True, "Mở deep link Telegram hoặc gửi /linkweb kèm mã này cho bot để xác nhận liên kết.", data={"code": code, "expires_in_minutes": LINK_TTL_MINUTES, "deep_link": f"https://t.me/{bot_username}?start=web_{code}" if bot_username else ""}, status_name="awaiting_confirm")


@router.get("/telegram/link/status")
async def telegram_link_status(account: dict = Depends(require_account)):
    return envelope(True, "Trạng thái liên kết", data={"linked": bool(account["canonical_user_id"]), "canonical_user_id": account["canonical_user_id"]}, status_name="completed" if account["canonical_user_id"] else "awaiting_confirm")


def _bridge_callback_authorized(request: Request) -> bool:
    configured = os.environ.get("CORE_BRIDGE_CALLBACK_TOKEN", os.environ.get("CORE_BRIDGE_TOKEN", ""))
    supplied = request.headers.get("X-TOAN-AAS-BRIDGE-TOKEN", "")
    return bool(configured and supplied and hmac.compare_digest(configured, supplied))


@router.post("/internal/telegram-link/confirm")
async def confirm_telegram_link(payload: LinkConfirmation, request: Request):
    """Private callback for the bot after a user proves ownership in Telegram."""
    if not _bridge_callback_authorized(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bridge authentication failed")
    code_hash = hashlib.sha256(payload.code.encode("utf-8")).hexdigest()
    with transaction() as conn:
        row = conn.execute(
            "SELECT account_id, expires_at, consumed_at FROM telegram_link_codes WHERE code_hash=?",
            (code_hash,),
        ).fetchone()
        if not row or row[2] or _as_time(row[1]) <= _now():
            return envelope(False, "Mã liên kết không hợp lệ hoặc đã hết hạn", status_name="failed", error_code="LINK_CODE_INVALID")
        role = "admin" if payload.role == "admin" else "user"
        conn.execute(
            """UPDATE web_accounts SET canonical_user_id=?, role_cache=?, display_name=COALESCE(NULLIF(?, ''), display_name), updated_at=? WHERE id=?""",
            (payload.canonical_user_id, role, payload.display_name.strip(), utc_now(), row[0]),
        )
        conn.execute(
            "UPDATE telegram_link_codes SET consumed_at=?, canonical_user_id=? WHERE code_hash=?",
            (utc_now(), payload.canonical_user_id, code_hash),
        )
        _record_audit(conn, account_id=row[0], canonical_user_id=payload.canonical_user_id, action="auth.telegram_link_confirm", request_id=_request_id(request))
    return envelope(True, "Đã xác nhận liên kết Telegram", data={"canonical_user_id": payload.canonical_user_id})
