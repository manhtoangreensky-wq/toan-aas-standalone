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
TELEGRAM_LOGIN_COOKIE = "toan_aas_telegram_login"
SESSION_TTL_HOURS = max(1, int(os.environ.get("WEB_SESSION_TTL_HOURS", "24")))
LINK_TTL_MINUTES = max(1, int(os.environ.get("TELEGRAM_LINK_TTL_MINUTES", "10")))
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
TELEGRAM_BOT_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{5,32}$")
BRIDGE_CALLBACK_MAX_AGE_SECONDS = 300
BRIDGE_CALLBACK_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,160}$")


def envelope(ok: bool, message: str, *, data: dict | None = None, status_name: str = "completed", error_code: str | None = None) -> dict:
    return {
        "ok": ok,
        "status": status_name,
        "message": message,
        "data": data or {},
        "error_code": error_code,
    }


def _is_production() -> bool:
    """Use one environment decision for secret and cookie protections."""
    values = (
        os.environ.get("APP_ENV", ""),
        os.environ.get("ENVIRONMENT", ""),
        os.environ.get("RAILWAY_ENVIRONMENT", ""),
    )
    return any(value.strip().lower() in {"production", "prod"} for value in values if value)


def _secret() -> bytes:
    value = os.environ.get("WEB_SESSION_SECRET", "").strip()
    if not value and _is_production():
        raise RuntimeError("WEB_SESSION_SECRET chưa được cấu hình")
    return (value or "copyfast-local-development-secret-only").encode("utf-8")


def _cookie_secure() -> bool:
    return os.environ.get("WEB_COOKIE_SECURE", "").lower() in {"1", "true", "yes"} or _is_production()


def ensure_auth_configuration() -> None:
    """Fail deployment startup before serving production sessions unsafely."""
    _secret()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _expiry(hours: int = SESSION_TTL_HOURS) -> str:
    return (_now() + timedelta(hours=hours)).isoformat(timespec="seconds")


def _link_expiry() -> str:
    return (_now() + timedelta(minutes=LINK_TTL_MINUTES)).isoformat(timespec="seconds")


def _bridge_callback_expiry() -> str:
    return (_now() + timedelta(seconds=BRIDGE_CALLBACK_MAX_AGE_SECONDS + 5)).isoformat(timespec="seconds")


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


def _telegram_login_cookie_value(browser_token: str) -> str:
    """Sign a short-lived Telegram login challenge separately from sessions."""
    material = f"telegram-login.{browser_token}".encode("utf-8")
    signature = hmac.new(_secret(), material, hashlib.sha256).hexdigest()
    return f"{browser_token}.{signature}"


def _parse_telegram_login_cookie(value: str | None) -> str | None:
    if not value or "." not in value:
        return None
    browser_token, signature = value.rsplit(".", 1)
    if not browser_token:
        return None
    expected = hmac.new(_secret(), f"telegram-login.{browser_token}".encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    return browser_token


def _new_telegram_code() -> str:
    # Match the existing bot `/start web_<code>` and `/linkweb <code>` shape.
    return secrets.token_urlsafe(18).replace("-", "A").replace("_", "B")


def _telegram_deep_link(code: str) -> str:
    bot_username = os.environ.get("BOT_USERNAME", "").strip().lstrip("@")
    if not TELEGRAM_BOT_USERNAME_PATTERN.fullmatch(bot_username):
        return ""
    return f"https://t.me/{bot_username}?start=web_{code}"


def _account_payload(row: tuple) -> dict:
    return {
        "id": row[0],
        "email": row[1],
        "display_name": row[2] or "",
        "canonical_user_id": row[3],
        "role": row[4] or "user",
    }


def browser_account_payload(account: dict) -> dict:
    """Return the minimum account metadata the browser needs to render safely.

    ``canonical_user_id`` is the Telegram identity used by server-to-server
    bridge calls.  It is intentionally absent from every browser-facing auth
    response; the UI only needs to know whether a link exists.
    """
    return {
        "email": str(account.get("email") or ""),
        "display_name": str(account.get("display_name") or ""),
        "role": "admin" if account.get("role") == "admin" else "user",
        "telegram_linked": bool(account.get("canonical_user_id")),
        "profile": {
            "locale": str(account.get("locale") or "vi"),
            "timezone": str(account.get("timezone") or "Asia/Ho_Chi_Minh"),
            "avatar_style": str(account.get("avatar_style") or "gradient"),
        },
        "login_methods": {
            "email": True,
            "telegram": bool(account.get("canonical_user_id")),
            # OAuth credentials are intentionally not inferred from browser
            # state. GitHub is advertised only as a setup-required option.
            "github": False,
        },
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
                      a.canonical_user_id, a.role_cache, a.is_active,
                      p.locale, p.timezone, p.avatar_style
               FROM web_sessions s JOIN web_accounts a ON a.id=s.account_id
               LEFT JOIN web_account_profiles p ON p.account_id=a.id
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
            "locale": row[9] or "vi",
            "timezone": row[10] or "Asia/Ho_Chi_Minh",
            "avatar_style": row[11] or "gradient",
        },
    }


def require_account(request: Request) -> dict:
    return current_session(request)["account"]


def require_admin(request: Request) -> dict:
    session = current_session(request)
    if session["account"]["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chỉ quản trị viên được phép truy cập")
    return session["account"]


async def _require_current_canonical_admin(request: Request, account: dict) -> dict:
    """Verify an already-authenticated admin against the bot authority.

    The web session deliberately keeps only a cached display role so the UI can
    render without exposing any Telegram credential.  Privileged *pages* must
    still ask the private core before serving their HTML: an account which has
    since lost bot admin access cannot keep browsing Admin ERP from a stale
    cookie.  All privileged JSON actions are independently checked again by
    the bot bridge.
    """
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


async def require_canonical_admin(request: Request) -> dict:
    """Require a signed session plus the bot's current canonical admin role."""
    return await _require_current_canonical_admin(request, require_admin(request))


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


async def require_canonical_admin_csrf(request: Request) -> dict:
    """CSRF-protected admin write that also re-checks the bot's live role.

    A cached browser role is intentionally insufficient for *every* Admin ERP
    JSON write, just as it is insufficient for the HTML shell.  Keeping this
    as a dependency prevents a newly demoted Telegram admin from retrying an
    old, valid Web session to trigger bridge actions.
    """
    return await _require_current_canonical_admin(request, require_admin_csrf(request))


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
    # Do this before the insert attempt for both new and existing addresses.
    # The endpoint deliberately does not create a signed session, so its
    # browser-visible result cannot reveal whether an email already existed.
    password_hash = _password_hash(payload.password)
    try:
        with transaction() as conn:
            conn.execute(
                """INSERT INTO web_accounts
                (id, email, password_hash, display_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (account_id, email, password_hash, payload.display_name.strip(), now, now),
            )
            conn.execute(
                """INSERT INTO web_account_profiles
                (account_id, locale, timezone, avatar_style, created_at, updated_at)
                VALUES (?, 'vi', 'Asia/Ho_Chi_Minh', 'gradient', ?, ?)""",
                (account_id, now, now),
            )
            _record_audit(conn, account_id=account_id, canonical_user_id=None, action="auth.register", request_id=_request_id(request))
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            # Existing and newly-created accounts receive the same public
            # handoff below.  Do not set a cookie or return an account ID/CSRF
            # token here: login is the only password flow that starts a signed
            # session, making this response non-enumerating by design.
            pass
        else:
            raise
    return envelope(
        True,
        "Nếu email chưa có tài khoản, yêu cầu đăng ký đã được tiếp nhận. Hãy đăng nhập để tiếp tục hoặc dùng chức năng khôi phục mật khẩu khi được phát hành.",
        status_name="awaiting_confirm",
    )


@router.post("/login")
async def login(payload: LoginRequest, request: Request, response: Response):
    ensure_copyfast_schema()
    email = payload.email.strip().lower()
    with transaction() as conn:
        row = conn.execute(
            """SELECT a.id, a.email, a.password_hash, a.display_name, a.canonical_user_id, a.role_cache, a.is_active,
                      p.locale, p.timezone, p.avatar_style
               FROM web_accounts a LEFT JOIN web_account_profiles p ON p.account_id=a.id
               WHERE a.email=?""",
            (email,),
        ).fetchone()
        if not row or not row[6] or not _verify_password(payload.password, row[2]):
            _record_audit(conn, account_id=row[0] if row else None, canonical_user_id=None, action="auth.login", request_id=_request_id(request), outcome="denied")
            return envelope(False, "Email hoặc mật khẩu không đúng", status_name="failed", error_code="LOGIN_DENIED")
        account = {
            "id": row[0], "email": row[1], "display_name": row[3] or "",
            "canonical_user_id": row[4], "role": row[5] or "user",
            "locale": row[7] or "vi", "timezone": row[8] or "Asia/Ho_Chi_Minh", "avatar_style": row[9] or "gradient",
        }
        _record_audit(conn, account_id=row[0], canonical_user_id=row[4], action="auth.login", request_id=_request_id(request))
    session = _create_session(response, account["id"])
    return envelope(True, "Đăng nhập thành công", data={"account": browser_account_payload(account), **session})


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
    return envelope(
        True,
        "Phiên hợp lệ",
        data={
            "account": browser_account_payload(account),
            "csrf_token": session["csrf_token"],
            "expires_at": session["expires_at"],
        },
    )


@router.post("/telegram/login/start")
async def start_telegram_login(request: Request, response: Response):
    """Start passwordless sign-in without accepting a raw Telegram ID.

    The visible code is proven only inside the already authenticated Telegram
    bot. A separate HttpOnly browser challenge prevents a copied code from
    issuing a Web session in another browser.
    """
    ensure_copyfast_schema()
    code = _new_telegram_code()
    browser_token = secrets.token_urlsafe(32)
    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    browser_token_hash = hashlib.sha256(browser_token.encode("utf-8")).hexdigest()
    with transaction() as conn:
        now = utc_now()
        conn.execute("DELETE FROM telegram_login_codes WHERE expires_at<=?", (now,))
        conn.execute(
            """INSERT INTO telegram_login_codes
            (code_hash, browser_token_hash, expires_at, created_at)
            VALUES (?, ?, ?, ?)""",
            (code_hash, browser_token_hash, _link_expiry(), now),
        )
        _record_audit(conn, account_id=None, canonical_user_id=None, action="auth.telegram_login_start", request_id=_request_id(request))
    response.set_cookie(
        TELEGRAM_LOGIN_COOKIE,
        _telegram_login_cookie_value(browser_token),
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        max_age=LINK_TTL_MINUTES * 60,
        path="/",
    )
    return envelope(
        True,
        "Mở Telegram để xác minh quyền sở hữu, sau đó quay lại Web để hoàn tất đăng nhập.",
        data={
            "code": code,
            "expires_in_minutes": LINK_TTL_MINUTES,
            "deep_link": _telegram_deep_link(code),
            "raw_telegram_id_accepted": False,
        },
        status_name="awaiting_confirm",
    )


def _telegram_login_challenge(request: Request) -> tuple[str, str] | None:
    browser_token = _parse_telegram_login_cookie(request.cookies.get(TELEGRAM_LOGIN_COOKIE))
    if not browser_token:
        return None
    return browser_token, hashlib.sha256(browser_token.encode("utf-8")).hexdigest()


def _clear_telegram_login_cookie(response: Response) -> None:
    response.delete_cookie(
        TELEGRAM_LOGIN_COOKIE,
        path="/",
        secure=_cookie_secure(),
        httponly=True,
        samesite="lax",
    )


@router.get("/telegram/login/status")
async def telegram_login_status(request: Request, response: Response):
    """Report challenge state only; POST /complete is the session write."""
    challenge = _telegram_login_challenge(request)
    if not challenge:
        return envelope(False, "Hãy tạo một mã đăng nhập Telegram mới.", data={"ready": False}, status_name="guarded", error_code="TELEGRAM_LOGIN_CHALLENGE_REQUIRED")
    _browser_token, token_hash = challenge
    with transaction() as conn:
        row = conn.execute(
            "SELECT expires_at, consumed_at, canonical_user_id FROM telegram_login_codes WHERE browser_token_hash=?",
            (token_hash,),
        ).fetchone()
        if not row or _as_time(row[0]) <= _now():
            conn.execute("DELETE FROM telegram_login_codes WHERE browser_token_hash=?", (token_hash,))
            _clear_telegram_login_cookie(response)
            return envelope(False, "Mã đăng nhập Telegram đã hết hạn. Hãy tạo mã mới.", data={"ready": False}, status_name="failed", error_code="TELEGRAM_LOGIN_EXPIRED")
        if not row[1] or not row[2]:
            return envelope(True, "Đang chờ bot xác minh Telegram.", data={"ready": False}, status_name="awaiting_confirm")
    return envelope(True, "Telegram đã được xác minh. Bạn có thể hoàn tất đăng nhập an toàn.", data={"ready": True}, status_name="awaiting_confirm")


@router.post("/telegram/login/complete")
async def complete_telegram_login(request: Request, response: Response):
    """Exchange one browser-bound, bot-verified challenge for a session."""
    challenge = _telegram_login_challenge(request)
    if not challenge:
        return envelope(False, "Phiên xác minh Telegram không còn hợp lệ. Hãy tạo mã mới.", status_name="guarded", error_code="TELEGRAM_LOGIN_CHALLENGE_REQUIRED")
    _browser_token, token_hash = challenge
    account: dict | None = None
    with transaction() as conn:
        row = conn.execute(
            "SELECT code_hash, expires_at, consumed_at, canonical_user_id FROM telegram_login_codes WHERE browser_token_hash=?",
            (token_hash,),
        ).fetchone()
        if not row or _as_time(row[1]) <= _now():
            conn.execute("DELETE FROM telegram_login_codes WHERE browser_token_hash=?", (token_hash,))
            _clear_telegram_login_cookie(response)
            return envelope(False, "Mã đăng nhập Telegram đã hết hạn. Hãy tạo mã mới.", status_name="failed", error_code="TELEGRAM_LOGIN_EXPIRED")
        if not row[2] or not row[3]:
            return envelope(False, "Bot chưa xác minh Telegram cho mã này.", status_name="awaiting_confirm", error_code="TELEGRAM_LOGIN_PENDING")
        account_row = conn.execute(
            "SELECT id, email, display_name, canonical_user_id, role_cache, is_active FROM web_accounts WHERE canonical_user_id=?",
            (row[3],),
        ).fetchone()
        if not account_row or not account_row[5]:
            conn.execute("DELETE FROM telegram_login_codes WHERE code_hash=?", (row[0],))
            _clear_telegram_login_cookie(response)
            _record_audit(conn, account_id=None, canonical_user_id=None, action="auth.telegram_login_complete", request_id=_request_id(request), outcome="denied", detail="no active linked web account")
            return envelope(False, "Telegram đã được xác minh nhưng chưa có tài khoản Web đang hoạt động. Hãy đăng ký/đăng nhập email một lần rồi liên kết Telegram.", status_name="guarded", error_code="TELEGRAM_LOGIN_ACCOUNT_REQUIRED")
        account = {
            "id": account_row[0], "email": account_row[1], "display_name": account_row[2] or "",
            "canonical_user_id": account_row[3], "role": account_row[4] or "user",
        }
        conn.execute("DELETE FROM telegram_login_codes WHERE code_hash=?", (row[0],))
        _record_audit(conn, account_id=account["id"], canonical_user_id=account["canonical_user_id"], action="auth.telegram_login_complete", request_id=_request_id(request))
    _clear_telegram_login_cookie(response)
    session = _create_session(response, account["id"])
    return envelope(True, "Đăng nhập Telegram thành công", data={"account": browser_account_payload(account), **session})


@router.post("/telegram/link/start")
async def start_telegram_link(request: Request, account: dict = Depends(require_csrf)):
    code = _new_telegram_code()
    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    initiating_session_id = current_session(request)["session_id"]
    with transaction() as conn:
        conn.execute("DELETE FROM telegram_link_codes WHERE account_id=? AND consumed_at IS NULL", (account["id"],))
        conn.execute(
            """INSERT INTO telegram_link_codes (code_hash, account_id, expires_at, initiating_session_id, created_at)
            VALUES (?, ?, ?, ?, ?)""",
            (code_hash, account["id"], _link_expiry(), initiating_session_id, utc_now()),
        )
        _record_audit(conn, account_id=account["id"], canonical_user_id=account["canonical_user_id"], action="auth.telegram_link_start", request_id=_request_id(request))
    deep_link = _telegram_deep_link(code)
    return envelope(True, "Mở deep link Telegram hoặc gửi /linkweb kèm mã này cho bot để xác nhận liên kết.", data={"code": code, "expires_in_minutes": LINK_TTL_MINUTES, "deep_link": deep_link}, status_name="awaiting_confirm")


@router.get("/telegram/link/status")
async def telegram_link_status(account: dict = Depends(require_account)):
    linked = bool(account["canonical_user_id"])
    return envelope(True, "Trạng thái liên kết", data={"linked": linked}, status_name="completed" if linked else "awaiting_confirm")


async def _bridge_callback_authorized(request: Request) -> bool:
    """Authenticate the bot-to-web link callback as a separate private channel.

    The callback is intentionally not allowed to reuse the browser-facing core
    bearer token.  It requires its own bearer token *and* an HMAC over the
    exact body, timestamp and one-time request ID.  The persistent nonce table
    makes a captured request unusable after its first attempt or process
    restart; the one-time link code then provides a second replay boundary.
    """
    token = os.environ.get("WEBAPP_LINK_CALLBACK_TOKEN", os.environ.get("CORE_BRIDGE_CALLBACK_TOKEN", "")).strip()
    secret = os.environ.get("WEBAPP_LINK_CALLBACK_HMAC_SECRET", os.environ.get("CORE_BRIDGE_CALLBACK_HMAC_SECRET", "")).strip()
    supplied_token = request.headers.get("X-TOAN-AAS-BRIDGE-TOKEN", "")
    timestamp = request.headers.get("X-TOAN-AAS-Timestamp", "")
    request_id = request.headers.get("X-TOAN-AAS-Request-ID", "")
    signature = request.headers.get("X-TOAN-AAS-Signature", "")
    if not token or not secret or not supplied_token or not hmac.compare_digest(token, supplied_token):
        return False
    if not timestamp.isdigit() or not BRIDGE_CALLBACK_REQUEST_ID_PATTERN.fullmatch(request_id):
        return False
    if abs(int(_now().timestamp()) - int(timestamp)) > BRIDGE_CALLBACK_MAX_AGE_SECONDS:
        return False
    body = await request.body()
    digest = hashlib.sha256(body).hexdigest()
    material = f"{timestamp}.{request_id}.{request.method.upper()}.{request.url.path}.{digest}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), material, hashlib.sha256).hexdigest()
    if not signature or not hmac.compare_digest(signature, expected):
        return False
    with transaction() as conn:
        conn.execute("DELETE FROM web_bridge_callback_nonces WHERE expires_at<=?", (_now().isoformat(timespec="seconds"),))
        if conn.execute("SELECT 1 FROM web_bridge_callback_nonces WHERE request_id=?", (request_id,)).fetchone():
            return False
        conn.execute(
            "INSERT INTO web_bridge_callback_nonces (request_id, expires_at, created_at) VALUES (?, ?, ?)",
            (request_id, _bridge_callback_expiry(), utc_now()),
        )
    return True


@router.post("/internal/telegram-link/confirm")
async def confirm_telegram_link(payload: LinkConfirmation, request: Request):
    """Private callback for the bot after a user proves ownership in Telegram."""
    if not await _bridge_callback_authorized(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bridge authentication failed")
    code_hash = hashlib.sha256(payload.code.encode("utf-8")).hexdigest()
    canonical_user_id = payload.canonical_user_id.strip()
    if not canonical_user_id:
        return envelope(False, "Telegram identity không hợp lệ", status_name="failed", error_code="LINK_IDENTITY_INVALID")
    with transaction() as conn:
        row = conn.execute(
            "SELECT account_id, expires_at, consumed_at, initiating_session_id FROM telegram_link_codes WHERE code_hash=?",
            (code_hash,),
        ).fetchone()
        if not row:
            # The Bot intentionally calls the same signed callback for both
            # link and passwordless-login codes. Login codes are browser-bound
            # separately and do not update any account here; the matching
            # browser performs the one-time session exchange afterwards.
            login_row = conn.execute(
                "SELECT expires_at, consumed_at FROM telegram_login_codes WHERE code_hash=?",
                (code_hash,),
            ).fetchone()
            if not login_row or login_row[1] or _as_time(login_row[0]) <= _now():
                return envelope(False, "Mã liên kết không hợp lệ hoặc đã hết hạn", status_name="failed", error_code="LINK_CODE_INVALID")
            conn.execute(
                "UPDATE telegram_login_codes SET consumed_at=?, canonical_user_id=? WHERE code_hash=?",
                (utc_now(), canonical_user_id, code_hash),
            )
            _record_audit(conn, account_id=None, canonical_user_id=None, action="auth.telegram_login_confirm", request_id=_request_id(request))
            return envelope(True, "Đã xác minh Telegram cho phiên đăng nhập Web", data={"mode": "login"})
        if row[2] or _as_time(row[1]) <= _now():
            return envelope(False, "Mã liên kết không hợp lệ hoặc đã hết hạn", status_name="failed", error_code="LINK_CODE_INVALID")
        account_id, _expires_at, _consumed_at, initiating_session_id = row
        existing = conn.execute(
            "SELECT id FROM web_accounts WHERE canonical_user_id=? AND id<>?",
            (canonical_user_id, account_id),
        ).fetchone()
        if existing:
            _record_audit(
                conn,
                account_id=account_id,
                canonical_user_id=None,
                action="auth.telegram_link_confirm",
                request_id=_request_id(request),
                outcome="denied",
                detail="canonical identity already linked to another account",
            )
            return envelope(False, "Tài khoản Telegram này đã liên kết với một tài khoản Web khác", status_name="failed", error_code="TELEGRAM_ALREADY_LINKED")
        role = "admin" if payload.role == "admin" else "user"
        conn.execute(
            """UPDATE web_accounts SET canonical_user_id=?, role_cache=?, display_name=COALESCE(NULLIF(?, ''), display_name), updated_at=? WHERE id=?""",
            (canonical_user_id, role, payload.display_name.strip(), utc_now(), account_id),
        )
        conn.execute(
            "UPDATE telegram_link_codes SET consumed_at=?, canonical_user_id=? WHERE code_hash=?",
            (utc_now(), canonical_user_id, code_hash),
        )
        # A successful link changes the account's canonical Telegram identity.
        # Other existing web sessions must not silently inherit that identity.
        # The session that created this one-time code remains valid so the user
        # can finish onboarding without an unnecessary login loop.  Legacy
        # codes without a recorded initiating session fail closed by revoking
        # every active session for that account.
        revoked_at = utc_now()
        if initiating_session_id:
            conn.execute(
                "UPDATE web_sessions SET revoked_at=? WHERE account_id=? AND id<>? AND revoked_at IS NULL",
                (revoked_at, account_id, initiating_session_id),
            )
        else:
            conn.execute(
                "UPDATE web_sessions SET revoked_at=? WHERE account_id=? AND revoked_at IS NULL",
                (revoked_at, account_id),
            )
        _record_audit(conn, account_id=account_id, canonical_user_id=canonical_user_id, action="auth.telegram_link_confirm", request_id=_request_id(request))
    return envelope(True, "Đã xác nhận liên kết Telegram", data={"canonical_user_id": canonical_user_id})
