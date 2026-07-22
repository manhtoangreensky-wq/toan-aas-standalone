"""Secure, web-owned account/session layer for the COPYFAST portal."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import base64
from email.message import EmailMessage
import hashlib
import hmac
import json
import os
import re
import secrets
import smtplib
import ssl
import uuid
from urllib.parse import parse_qs, urlencode, urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from copyfast_db import (
    ensure_copyfast_schema,
    is_production_like_environment,
    read_transaction,
    transaction,
    utc_now,
)


router = APIRouter(tags=["COPYFAST Auth"])

SESSION_COOKIE = "toan_aas_session"
TELEGRAM_LOGIN_COOKIE = "toan_aas_telegram_login"
OAUTH_STATE_COOKIE = "toan_aas_oauth_state"
OAUTH_LINK_COOKIE = "toan_aas_oauth_link"
SESSION_TTL_HOURS = max(1, int(os.environ.get("WEB_SESSION_TTL_HOURS", "24")))
LINK_TTL_MINUTES = max(1, int(os.environ.get("TELEGRAM_LINK_TTL_MINUTES", "10")))
OAUTH_STATE_TTL_MINUTES = max(1, int(os.environ.get("WEB_OAUTH_STATE_TTL_MINUTES", "10")))
EMAIL_VERIFICATION_DEFAULT_TTL_MINUTES = 20
EMAIL_VERIFICATION_MIN_TTL_MINUTES = 5
EMAIL_VERIFICATION_MAX_TTL_MINUTES = 60
EMAIL_VERIFICATION_RATE_WINDOW_MINUTES = 15
EMAIL_VERIFICATION_MAX_STARTS_PER_WINDOW = 3
EMAIL_VERIFICATION_TOKEN_BYTES = 32
PASSWORD_RECOVERY_DEFAULT_TTL_MINUTES = 20
PASSWORD_RECOVERY_MIN_TTL_MINUTES = 5
PASSWORD_RECOVERY_MAX_TTL_MINUTES = 60
PASSWORD_RECOVERY_RATE_WINDOW_MINUTES = 15
PASSWORD_RECOVERY_MAX_STARTS_PER_WINDOW = 3
PASSWORD_RECOVERY_TOKEN_BYTES = 32
PASSWORD_RECOVERY_CONFIRM_MAX_BODY_BYTES = 4_096
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
TELEGRAM_BOT_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{5,32}$")
SMTP_HOST_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$")
EMAIL_VERIFICATION_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{32,128}$")
TELEGRAM_ONLY_EMAIL_DOMAIN = "telegram.toanaas.invalid"
OAUTH_ONLY_EMAIL_DOMAIN = "oauth.toanaas.invalid"
BRIDGE_CALLBACK_MAX_AGE_SECONDS = 300
BRIDGE_CALLBACK_MAX_FUTURE_SKEW_SECONDS = 30
BRIDGE_CALLBACK_MAX_BODY_BYTES = 2_048
BRIDGE_CALLBACK_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,160}$")
OAUTH_PROVIDER_NAMES = frozenset({"google", "github", "apple", "telegram"})
# Interface locale is a Web-owned presentation preference.  It intentionally
# does not select the language of any Studio workflow, Bot conversation or
# provider request.
INTERFACE_LOCALES = frozenset({"vi", "en", "zh"})
DEFAULT_INTERFACE_LOCALE = "vi"
# Only these providers have a verified-email contract.  Telegram's numeric
# identity remains separate from contact email and from the Bot canonical ID.
OAUTH_CONTACT_PROVIDERS = frozenset({"google", "github", "apple"})
OAUTH_STATE_VALUE_MAX_LENGTH = 256
OAUTH_STATE_COOKIE_NAME_DIGEST_LENGTH = 32
SESSION_REFERENCE_PATTERN = re.compile(r"^[0-9a-f]{64}$")
GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"
APPLE_AUTHORIZE_URL = "https://appleid.apple.com/auth/authorize"
APPLE_TOKEN_URL = "https://appleid.apple.com/auth/token"
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
TELEGRAM_OAUTH_AUTHORIZE_URL = "https://oauth.telegram.org/auth"
TELEGRAM_OAUTH_TOKEN_URL = "https://oauth.telegram.org/token"
TELEGRAM_OAUTH_JWKS_URL = "https://oauth.telegram.org/.well-known/jwks.json"
# Literal-only inventory for the static migration audit. These are names, not
# values; keeping the set explicit makes the production handoff discoverable
# even though the generic OAuth helpers construct provider-specific names.
TELEGRAM_OIDC_ENVIRONMENT_NAMES = (
    "WEBAPP_TELEGRAM_OAUTH_ENABLED",
    "TELEGRAM_OAUTH_CLIENT_ID",
    "TELEGRAM_OAUTH_CLIENT_SECRET",
)
OAUTH_HTTP_TIMEOUT_SECONDS = 8.0
# Starlette renamed these constants after the FastAPI version declared by this
# project. Resolve the modern spelling first without evaluating the deprecated
# fallback on newer runtimes, then retain a compatible value for Railway's
# pinned Starlette 0.27 dependency.
HTTP_413_PAYLOAD_TOO_LARGE = getattr(status, "HTTP_413_CONTENT_TOO_LARGE", None)
if HTTP_413_PAYLOAD_TOO_LARGE is None:
    HTTP_413_PAYLOAD_TOO_LARGE = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
HTTP_422_UNPROCESSABLE = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", None)
if HTTP_422_UNPROCESSABLE is None:
    HTTP_422_UNPROCESSABLE = status.HTTP_422_UNPROCESSABLE_ENTITY


def envelope(ok: bool, message: str, *, data: dict | None = None, status_name: str = "completed", error_code: str | None = None) -> dict:
    return {
        "ok": ok,
        "status": status_name,
        "message": message,
        "data": data or {},
        "error_code": error_code,
    }


def normalize_interface_locale(value: object) -> str:
    """Return a closed, browser-safe Web interface locale.

    This is deliberately a presentation setting only.  Callers must still
    reject unsupported submitted values where the user requested an update;
    this fallback is for persisted legacy/malformed rows before projection.
    """

    locale = str(value or "").strip().lower()
    return locale if locale in INTERFACE_LOCALES else DEFAULT_INTERFACE_LOCALE


def _bridge_callback_failure(
    message: str,
    *,
    error_code: str,
    http_status: int,
    status_name: str = "failed",
) -> JSONResponse:
    """Make a rejected Bot callback unambiguously non-successful.

    The frozen Bot bridge treats every HTTP 2xx callback response as a
    completed link. Browser-facing endpoints may safely use ``ok: false``
    envelopes with 200 for expected form states, but the private Bot callback
    must use a non-2xx status whenever the Web App rejects the proof.
    """
    return JSONResponse(
        envelope(False, message, status_name=status_name, error_code=error_code),
        status_code=http_status,
    )


def _is_production() -> bool:
    """Use the shared deployment decision for secrets and cookie policy."""
    return is_production_like_environment()


def _is_hosted_deployment() -> bool:
    """Recognise Railway/hosted environments even when their label is preview.

    Railway preview/staging deployments do not always use the literal
    ``production`` label, but they are still public HTTPS deployments and
    must never receive an unprefixed or non-Secure session cookie.  The check
    is intentionally based on platform metadata only; a developer can still
    run HTTP locally without pretending that localhost is a public service.
    """

    if _is_production():
        return True
    return any(
        os.environ.get(name, "").strip()
        for name in (
            "RAILWAY_ENVIRONMENT",
            "RAILWAY_ENVIRONMENT_ID",
            "RAILWAY_PROJECT_ID",
            "RAILWAY_SERVICE_ID",
            "RAILWAY_DEPLOYMENT_ID",
            "RAILWAY_PUBLIC_DOMAIN",
        )
    )


def _secret() -> bytes:
    value = os.environ.get("WEB_SESSION_SECRET", "").strip()
    encoded = value.encode("utf-8")
    # Never keep a deterministic local fallback in source.  A 128-bit random
    # value is the minimum safe HMAC key length and is practical for local
    # development, CI and all hosted deployments alike.
    if len(encoded) < 16:
        raise RuntimeError("WEB_SESSION_SECRET phải được cấu hình ngẫu nhiên, tối thiểu 16 byte")
    return encoded


def _cookie_secure() -> bool:
    # Explicit false is accepted only for an unhosted local HTTP workflow.
    # Any Railway metadata (including preview) forces the browser-enforced
    # Secure + __Host- cookie protections even if APP_ENV was omitted.
    return os.environ.get("WEB_COOKIE_SECURE", "").lower() in {"1", "true", "yes"} or _is_hosted_deployment()


def _cookie_name(name: str) -> str:
    """Return a host-only cookie name whenever HTTPS protection is active.

    A ``__Host-`` cookie must be Secure, host-only and Path=/ according to
    browser enforcement rules. That prevents a sibling subdomain from planting
    a competing parent-domain session/state cookie (cookie tossing). Local HTTP
    development deliberately retains the unprefixed name; a production
    deployment never reads that legacy name as a fallback.
    """
    return f"__Host-{name}" if _cookie_secure() else name


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _bounded_int_environment(name: str, default: int, minimum: int, maximum: int) -> int:
    """Read a non-secret integer configuration without creating unsafe ranges."""

    try:
        value = int(os.environ.get(name, str(default)).strip())
    except (TypeError, ValueError):
        return default
    return min(maximum, max(minimum, value))


def _email_verification_enabled() -> bool:
    """Whether the explicitly configured Web-owned SMTP flow is available."""

    return _env_flag("WEBAPP_EMAIL_VERIFICATION_ENABLED")


def _password_recovery_enabled() -> bool:
    """Whether the separately opt-in Web password recovery flow is available."""

    return _env_flag("WEBAPP_PASSWORD_RECOVERY_ENABLED")


def _email_verification_public_base_url() -> str:
    """Return the strict public origin used in a mailbox confirmation link."""

    raw = (
        os.environ.get("WEBAPP_EMAIL_VERIFICATION_PUBLIC_BASE_URL", "").strip()
        or os.environ.get("WEBAPP_PUBLIC_BASE_URL", "").strip()
    ).rstrip("/")
    if not raw:
        raise RuntimeError("WEBAPP_EMAIL_VERIFICATION_PUBLIC_BASE_URL chưa được cấu hình")
    parsed = urlparse(raw)
    local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if (
        not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise RuntimeError("WEBAPP_EMAIL_VERIFICATION_PUBLIC_BASE_URL không hợp lệ")
    if parsed.scheme != "https" and not (local_http and not _is_production()):
        raise RuntimeError("WEBAPP_EMAIL_VERIFICATION_PUBLIC_BASE_URL phải dùng HTTPS ngoài môi trường local")
    return raw


def _smtp_email_configuration() -> dict:
    """Load shared SMTP transport settings without returning them to a browser."""

    host = os.environ.get("WEBAPP_EMAIL_SMTP_HOST", "").strip()
    username = os.environ.get("WEBAPP_EMAIL_SMTP_USERNAME", "").strip()
    password = os.environ.get("WEBAPP_EMAIL_SMTP_PASSWORD", "")
    sender = os.environ.get("WEBAPP_EMAIL_VERIFICATION_FROM", "").strip().lower()
    mode = os.environ.get("WEBAPP_EMAIL_SMTP_TLS_MODE", "starttls").strip().lower()
    port = _bounded_int_environment("WEBAPP_EMAIL_SMTP_PORT", 587, 1, 65535)
    timeout_seconds = _bounded_int_environment("WEBAPP_EMAIL_SMTP_TIMEOUT_SECONDS", 10, 3, 30)
    if not host or not SMTP_HOST_PATTERN.fullmatch(host) or host.startswith(".") or host.endswith("."):
        raise RuntimeError("WEBAPP_EMAIL_SMTP_HOST không hợp lệ")
    if not username or not password:
        raise RuntimeError("WEBAPP_EMAIL_SMTP_USERNAME/PASSWORD chưa được cấu hình")
    if not EMAIL_PATTERN.fullmatch(sender):
        raise RuntimeError("WEBAPP_EMAIL_VERIFICATION_FROM phải là địa chỉ email hợp lệ")
    if mode not in {"starttls", "ssl"}:
        raise RuntimeError("WEBAPP_EMAIL_SMTP_TLS_MODE chỉ nhận starttls hoặc ssl")
    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "sender": sender,
        "mode": mode,
        "timeout_seconds": timeout_seconds,
        "public_base_url": _email_verification_public_base_url(),
    }


def _email_verification_configuration() -> dict | None:
    """Load settings for the signed-account mailbox assurance flow."""

    if not _email_verification_enabled():
        return None
    return {
        **_smtp_email_configuration(),
        "ttl_minutes": _bounded_int_environment(
            "WEBAPP_EMAIL_VERIFICATION_TTL_MINUTES",
            EMAIL_VERIFICATION_DEFAULT_TTL_MINUTES,
            EMAIL_VERIFICATION_MIN_TTL_MINUTES,
            EMAIL_VERIFICATION_MAX_TTL_MINUTES,
        ),
    }


def _password_recovery_configuration() -> dict | None:
    """Load settings for the public, non-enumerating recovery flow."""

    if not _password_recovery_enabled():
        return None
    return {
        **_smtp_email_configuration(),
        "ttl_minutes": _bounded_int_environment(
            "WEBAPP_PASSWORD_RECOVERY_TTL_MINUTES",
            PASSWORD_RECOVERY_DEFAULT_TTL_MINUTES,
            PASSWORD_RECOVERY_MIN_TTL_MINUTES,
            PASSWORD_RECOVERY_MAX_TTL_MINUTES,
        ),
    }


def ensure_email_verification_configuration() -> None:
    """Fail a deliberately enabled hosted flow early when SMTP is incomplete."""

    _email_verification_configuration()


def ensure_password_recovery_configuration() -> None:
    """Fail a deliberately enabled recovery flow early when SMTP is incomplete."""

    _password_recovery_configuration()


def email_verification_delivery_available() -> bool:
    """Expose only availability, never SMTP host/account/secret details."""

    try:
        return _email_verification_configuration() is not None
    except RuntimeError:
        return False


def _oauth_enabled(provider: str) -> bool:
    return provider in OAUTH_PROVIDER_NAMES and _env_flag(f"WEBAPP_{provider.upper()}_OAUTH_ENABLED")


def _oauth_hmac_secret() -> bytes:
    value = os.environ.get("WEB_OAUTH_IDENTITY_HMAC_SECRET", "").strip()
    if not value:
        raise RuntimeError("WEB_OAUTH_IDENTITY_HMAC_SECRET chưa được cấu hình cho OAuth")
    return value.encode("utf-8")


def _oauth_public_base_url() -> str:
    raw = os.environ.get("WEBAPP_PUBLIC_BASE_URL", "").strip().rstrip("/")
    if not raw:
        raise RuntimeError("WEBAPP_PUBLIC_BASE_URL chưa được cấu hình cho OAuth")
    parsed = urlparse(raw)
    local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise RuntimeError("WEBAPP_PUBLIC_BASE_URL không hợp lệ cho OAuth")
    if parsed.scheme != "https" and not (local_http and not _is_production()):
        raise RuntimeError("WEBAPP_PUBLIC_BASE_URL phải dùng HTTPS ngoài môi trường local")
    return raw


def _oauth_client_configuration(provider: str) -> dict:
    if provider not in OAUTH_PROVIDER_NAMES:
        raise ValueError("OAuth provider không hợp lệ")
    client_id = os.environ.get(f"{provider.upper()}_OAUTH_CLIENT_ID", "").strip()
    base_url = _oauth_public_base_url()
    if provider == "apple":
        team_id = os.environ.get("APPLE_OAUTH_TEAM_ID", "").strip()
        key_id = os.environ.get("APPLE_OAUTH_KEY_ID", "").strip()
        private_key = os.environ.get("APPLE_OAUTH_PRIVATE_KEY_BASE64", "").strip()
        if not client_id or not team_id or not key_id or not private_key:
            raise RuntimeError("OAuth apple chưa có Services ID/Team ID/Key ID/private key")
        if urlparse(base_url).scheme != "https" or not _cookie_secure():
            raise RuntimeError("OAuth apple yêu cầu HTTPS và WEB_COOKIE_SECURE=true")
        return {
            "provider": provider,
            "client_id": client_id,
            "team_id": team_id,
            "key_id": key_id,
            "private_key_base64": private_key,
            "redirect_uri": f"{base_url}/api/v1/auth/oauth/{provider}/callback",
        }
    client_secret = os.environ.get(f"{provider.upper()}_OAUTH_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise RuntimeError(f"OAuth {provider} chưa có client ID/secret")
    if urlparse(base_url).scheme == "https" and not _cookie_secure():
        raise RuntimeError(f"OAuth {provider} yêu cầu WEB_COOKIE_SECURE=true khi dùng HTTPS")
    return {
        "provider": provider,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": f"{base_url}/api/v1/auth/oauth/{provider}/callback",
    }


def ensure_oauth_configuration() -> None:
    """Fail closed if a production OAuth flag is enabled incompletely."""
    for provider in OAUTH_PROVIDER_NAMES:
        if not _oauth_enabled(provider):
            continue
        _oauth_hmac_secret()
        config = _oauth_client_configuration(provider)
        if provider in {"google", "apple", "telegram"}:
            try:
                import jwt  # type: ignore[import-not-found]  # noqa: F401
            except ImportError as exc:  # pragma: no cover - exercised by deployment configuration
                raise RuntimeError(f"OAuth {provider} cần dependency PyJWT[crypto]") from exc
        if provider == "apple":
            # Validate the Railway-only base64 .p8 key before the application
            # accepts traffic; a malformed key must not surface only after a
            # user completes a live Apple consent screen.
            _apple_client_secret(config)


def oauth_provider_status() -> dict:
    """Browser-safe availability only; never expose client IDs or secrets."""
    return {
        provider: {"enabled": _oauth_enabled(provider)}
        for provider in sorted(OAUTH_PROVIDER_NAMES)
    }


def ensure_auth_configuration() -> None:
    """Fail deployment startup before serving production sessions unsafely."""
    _secret()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _expiry(hours: int = SESSION_TTL_HOURS) -> str:
    return (_now() + timedelta(hours=hours)).isoformat(timespec="seconds")


def _link_expiry() -> str:
    return (_now() + timedelta(minutes=LINK_TTL_MINUTES)).isoformat(timespec="seconds")


def _email_verification_expiry(ttl_minutes: int) -> str:
    return (_now() + timedelta(minutes=ttl_minutes)).isoformat(timespec="seconds")


def _email_verification_window_start() -> str:
    return (
        _now() - timedelta(minutes=EMAIL_VERIFICATION_RATE_WINDOW_MINUTES)
    ).isoformat(timespec="seconds")


def _password_recovery_expiry(ttl_minutes: int) -> str:
    return (_now() + timedelta(minutes=ttl_minutes)).isoformat(timespec="seconds")


def _password_recovery_window_start() -> str:
    return (
        _now() - timedelta(minutes=PASSWORD_RECOVERY_RATE_WINDOW_MINUTES)
    ).isoformat(timespec="seconds")


def _email_verification_token_hash(challenge_id: str, token: str) -> str:
    """Hash a one-time token with the session secret before it enters SQLite."""

    material = f"toan-aas/email-verification/v1/{challenge_id}/{token}".encode("utf-8")
    return hmac.new(_secret(), material, hashlib.sha256).hexdigest()


def _password_recovery_token_hash(challenge_id: str, token: str) -> str:
    """Hash an independent recovery proof; it is never interchangeable with email assurance."""

    material = f"toan-aas/password-recovery/v1/{challenge_id}/{token}".encode("utf-8")
    return hmac.new(_secret(), material, hashlib.sha256).hexdigest()


def _email_verification_confirmation_url(config: dict, challenge_id: str, token: str) -> str:
    query = urlencode({"c": challenge_id, "t": token})
    return f"{config['public_base_url']}/api/v1/auth/email-verification/confirm?{query}"


def _password_recovery_confirmation_url(config: dict, challenge_id: str, token: str) -> str:
    query = urlencode({"c": challenge_id, "t": token})
    return f"{config['public_base_url']}/api/v1/auth/password-recovery/confirm?{query}"


def _smtp_send_email_verification(config: dict, *, recipient: str, confirmation_url: str) -> None:
    """Perform one authenticated TLS SMTP handoff without retaining payloads."""

    message = EmailMessage()
    message["From"] = config["sender"]
    message["To"] = recipient
    message["Subject"] = "Xác minh email TOAN AAS"
    message.set_content(
        "Bạn vừa yêu cầu xác minh email cho tài khoản TOAN AAS.\n\n"
        "Mở liên kết sau để xác minh quyền sở hữu mailbox này:\n"
        f"{confirmation_url}\n\n"
        "Liên kết chỉ dùng một lần và sẽ hết hạn. Nếu bạn không yêu cầu, "
        "bạn có thể bỏ qua email này."
    )
    context = ssl.create_default_context()
    connection_type = smtplib.SMTP_SSL if config["mode"] == "ssl" else smtplib.SMTP
    with connection_type(
        config["host"],
        config["port"],
        timeout=config["timeout_seconds"],
    ) as smtp:
        smtp.ehlo()
        if config["mode"] == "starttls":
            smtp.starttls(context=context)
            smtp.ehlo()
        smtp.login(config["username"], config["password"])
        smtp.send_message(message, from_addr=config["sender"], to_addrs=[recipient])


async def _send_email_verification_message(config: dict, *, recipient: str, challenge_id: str, token: str) -> None:
    """Keep potentially slow SMTP I/O outside the async event loop and DB lock."""

    confirmation_url = _email_verification_confirmation_url(config, challenge_id, token)
    await asyncio.to_thread(
        _smtp_send_email_verification,
        config,
        recipient=recipient,
        confirmation_url=confirmation_url,
    )


def _smtp_send_password_recovery(config: dict, *, recipient: str, confirmation_url: str) -> None:
    """Perform one TLS SMTP handoff for a password-reset proof."""

    message = EmailMessage()
    message["From"] = config["sender"]
    message["To"] = recipient
    message["Subject"] = "Đặt lại mật khẩu TOAN AAS"
    message.set_content(
        "Bạn vừa yêu cầu đặt lại mật khẩu cho tài khoản TOAN AAS.\n\n"
        "Mở liên kết sau để tự chọn mật khẩu mới:\n"
        f"{confirmation_url}\n\n"
        "Liên kết chỉ dùng một lần và sẽ hết hạn. Thao tác này thu hồi các "
        "phiên Web đang đăng nhập. Nếu bạn không yêu cầu, hãy bỏ qua email này."
    )
    context = ssl.create_default_context()
    connection_type = smtplib.SMTP_SSL if config["mode"] == "ssl" else smtplib.SMTP
    with connection_type(
        config["host"],
        config["port"],
        timeout=config["timeout_seconds"],
    ) as smtp:
        smtp.ehlo()
        if config["mode"] == "starttls":
            smtp.starttls(context=context)
            smtp.ehlo()
        smtp.login(config["username"], config["password"])
        smtp.send_message(message, from_addr=config["sender"], to_addrs=[recipient])


async def _send_password_recovery_message(config: dict, *, recipient: str, challenge_id: str, token: str) -> None:
    """Keep password recovery SMTP work outside the event loop and database lock."""

    confirmation_url = _password_recovery_confirmation_url(config, challenge_id, token)
    await asyncio.to_thread(
        _smtp_send_password_recovery,
        config,
        recipient=recipient,
        confirmation_url=confirmation_url,
    )


def _bridge_callback_expiry(timestamp: int) -> str:
    """Retain a callback nonce through the full accepted signature lifetime.

    A timestamp can be accepted slightly ahead of the Web clock.  Expiring a
    nonce from ``now`` would then make a captured signed callback replayable
    after the nonce is pruned but before the HMAC itself becomes stale.
    """
    issued_at = datetime.fromtimestamp(timestamp, timezone.utc)
    return (issued_at + timedelta(seconds=BRIDGE_CALLBACK_MAX_AGE_SECONDS + 5)).isoformat(timespec="seconds")


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


# A valid, process-local scrypt record makes rejected login attempts spend the
# same password-verification work whether the email exists, is inactive, or
# has a wrong password.  It deliberately never represents an account.
_DUMMY_PASSWORD_HASH = _password_hash("copyfast-dummy-password")


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


def _security_session_reference(session_id: str) -> str:
    """Return a one-way, account-scoped UI handle for a signed session.

    The database primary key and the signed cookie value are authentication
    material.  The account-security screen only needs a short-lived action
    handle, so it receives a domain-separated HMAC instead.  It is never
    accepted as a cookie, never written to audit text, and cannot be reversed
    into a session identifier by the browser.
    """

    material = f"toan-aas/security-session-reference/v1/{session_id}".encode("utf-8")
    return hmac.new(_secret(), material, hashlib.sha256).hexdigest()


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


def _oauth_expiry() -> str:
    return (_now() + timedelta(minutes=OAUTH_STATE_TTL_MINUTES)).isoformat(timespec="seconds")


def _oauth_state_hash(state_value: str) -> str:
    return hashlib.sha256(state_value.encode("utf-8")).hexdigest()


def _oauth_hmac(label: str, *parts: str) -> str:
    material = ".".join((label, *parts)).encode("utf-8")
    return hmac.new(_oauth_hmac_secret(), material, hashlib.sha256).hexdigest()


def _oauth_state_cookie_name(provider: str, state_value: str) -> str:
    """Return a browser-binding cookie name unique to one OAuth attempt.

    A single fixed state cookie made a later Google/GitHub/Apple start erase
    an earlier tab's browser proof.  The opaque state is already high entropy,
    but it is never placed in the cookie name: a separate HMAC-derived suffix
    keeps the name unguessable from ordinary browser metadata and binds it to
    the expected provider.  Each cookie remains short-lived and HttpOnly;
    independent attempts therefore cannot overwrite one another.
    """
    if provider not in OAUTH_PROVIDER_NAMES or not state_value or len(state_value) > OAUTH_STATE_VALUE_MAX_LENGTH:
        raise ValueError("OAuth state cookie không hợp lệ")
    digest = _oauth_hmac("state-cookie-name-v1", provider, state_value)[:OAUTH_STATE_COOKIE_NAME_DIGEST_LENGTH]
    return _cookie_name(f"{OAUTH_STATE_COOKIE}_v1_{provider}_{digest}")


def _oauth_state_cookie_samesite(provider: str) -> str:
    # Apple returns a cross-site form POST.  Its state proof gets a distinct
    # cookie name, so enabling Apple never weakens Google/GitHub/Telegram's
    # Lax browser binding.
    return "none" if provider == "apple" else "lax"


def _oauth_state_cookie_value(provider: str, state_value: str) -> str:
    return f"{provider}.{state_value}.{_oauth_hmac('state', provider, state_value)}"


def _parse_oauth_state_cookie(value: str | None) -> tuple[str, str] | None:
    if not value:
        return None
    parts = value.split(".", 2)
    if len(parts) != 3:
        return None
    provider, state_value, supplied = parts
    if provider not in OAUTH_PROVIDER_NAMES or not state_value:
        return None
    expected = _oauth_hmac("state", provider, state_value)
    if not hmac.compare_digest(supplied, expected):
        return None
    return provider, state_value


def _oauth_link_cookie_value(provider: str, session_id: str, ticket: str) -> str:
    return f"{provider}.{session_id}.{ticket}.{_oauth_hmac('link', provider, session_id, ticket)}"


def _parse_oauth_link_cookie(value: str | None) -> tuple[str, str, str] | None:
    if not value:
        return None
    parts = value.split(".", 3)
    if len(parts) != 4:
        return None
    provider, session_id, ticket, supplied = parts
    if provider not in OAUTH_PROVIDER_NAMES or not session_id or not ticket:
        return None
    expected = _oauth_hmac("link", provider, session_id, ticket)
    if not hmac.compare_digest(supplied, expected):
        return None
    return provider, session_id, ticket


def _oauth_derived_token(label: str, state_value: str) -> str:
    """Generate server-only PKCE verifier / OIDC nonce from opaque state."""
    digest = hmac.new(_oauth_hmac_secret(), f"{label}.{state_value}".encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _oauth_code_challenge(state_value: str) -> str:
    verifier = _oauth_derived_token("pkce", state_value)
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")


def _external_subject_hash(provider: str, subject: str) -> str:
    return _oauth_hmac("identity", provider, subject)


def _oauth_only_email(provider: str, subject: str) -> str:
    """Return a non-login alias for an isolated OAuth collision account.

    The alias is deterministic for one immutable provider subject, but it
    contains neither the raw subject nor the provider-verified contact email.
    It is a database implementation detail only: password login stays off
    and ``browser_account_payload`` replaces it with the verified contact.
    """
    if provider not in OAUTH_CONTACT_PROVIDERS or not subject:
        raise ValueError("OAuth-only alias requires a verified email provider identity")
    digest = _oauth_hmac("oauth-only-login-alias-v1", provider, subject)[:48]
    return f"oauth-{provider}-{digest}@{OAUTH_ONLY_EMAIL_DOMAIN}"


def _is_oauth_only_email(value: str) -> bool:
    email = str(value or "").strip().lower()
    providers = "|".join(sorted(OAUTH_CONTACT_PROVIDERS))
    return bool(
        re.fullmatch(
            rf"oauth-(?:{providers})-[0-9a-f]{{48}}@{re.escape(OAUTH_ONLY_EMAIL_DOMAIN)}",
            email,
        )
    )


def _verified_oauth_contact_email(identity: dict) -> str:
    """Return a freshly provider-verified email or the empty string.

    Provider parsing has to set ``email_verified`` explicitly.  Treating a
    missing flag as verified would let a future provider adapter accidentally
    broaden this boundary, so mocked/adapter identities must opt in as well.
    """
    provider = str(identity.get("provider") or "")
    email = str(identity.get("email") or "").strip().lower()
    if (
        provider not in OAUTH_CONTACT_PROVIDERS
        or identity.get("email_verified") is not True
        or not EMAIL_PATTERN.fullmatch(email)
    ):
        return ""
    return email


def _safe_oauth_return_path(value: str | None) -> str:
    candidate = str(value or "").strip()
    if not candidate or not candidate.startswith("/") or candidate.startswith("//") or "\\" in candidate:
        return "/dashboard"
    parsed = urlparse(candidate)
    if parsed.scheme or parsed.netloc or parsed.params or parsed.fragment:
        return "/dashboard"
    # The shell resolves route access itself; do not put a provider callback,
    # private API or untrusted URL into the post-login redirect.
    if candidate.startswith("/api/") or candidate.startswith("/internal/"):
        return "/dashboard"
    return candidate.split("?", 1)[0] or "/dashboard"


def _new_telegram_code() -> str:
    # Match the existing bot `/start web_<code>` and `/linkweb <code>` shape.
    return secrets.token_urlsafe(18).replace("-", "A").replace("_", "B")


def _telegram_bot_username() -> str:
    username = os.environ.get("BOT_USERNAME", "").strip().lstrip("@")
    return username if TELEGRAM_BOT_USERNAME_PATTERN.fullmatch(username) else ""


def _telegram_callback_receiver_configured() -> bool:
    # The Bot bridge already uses this directional pair.  Do not silently
    # reuse a core-bridge credential here: a callback that can establish a
    # browser identity needs an independent, deliberately configured secret.
    token = os.environ.get("WEBAPP_LINK_CALLBACK_TOKEN", "").strip()
    secret = os.environ.get("WEBAPP_LINK_CALLBACK_HMAC_SECRET", "").strip()
    return bool(token and secret)


def _telegram_bot_link_adapter_enabled() -> bool:
    """Return the explicit operator acknowledgement for the paired Bot adapter.

    The Web process can verify its own receiver credential but cannot inspect
    the Bot service's deployed revision or Railway variables.  Do not mint a
    customer-facing code merely because this process has secrets: the
    matching Bot `/start web_<code>` / `/linkweb` adapter must first have been
    deployed and deliberately enabled by the operator.  A later valid signed
    callback remains the only end-to-end proof.
    """
    return _env_flag("WEBAPP_TELEGRAM_BOT_LINK_ENABLED", False)


def _telegram_auto_register_enabled() -> bool:
    # Bot-proven Telegram identity plus a browser-bound one-time challenge is
    # sufficient to create a Web-only account. This never creates a Bot user,
    # wallet, PayOS order, provider call or grant.
    return _env_flag("WEBAPP_TELEGRAM_AUTO_REGISTER_ENABLED", True)


def _telegram_callback_observation() -> dict:
    """Return anonymous evidence that the Bot callback has worked at least once.

    A Web deployment can prove that it has a public Bot username and a local
    callback receiver, but it cannot read another Railway service's runtime
    configuration.  The only honest end-to-end signal is a callback that has
    passed the dedicated bearer/HMAC verification.  The audit table already
    records that event, so expose only its safe type and timestamp — never a
    code, account, Telegram identity, request ID, or credential.
    """
    try:
        ensure_copyfast_schema()
        with transaction() as conn:
            row = conn.execute(
                """SELECT action, created_at
                FROM web_audit_events
                WHERE action IN ('auth.telegram_login_confirm', 'auth.telegram_link_confirm')
                  AND outcome='ok'
                ORDER BY created_at DESC
                LIMIT 1"""
            ).fetchone()
    except Exception:
        # Setup/status must never leak a database error or make a public
        # authentication page unavailable.  A missing observation simply
        # means the operator still needs an end-to-end confirmation.
        row = None
    if not row:
        return {
            "bot_callback_observed": False,
            "last_valid_callback_at": "",
            "last_valid_callback_kind": "",
        }
    action, created_at = row
    return {
        "bot_callback_observed": True,
        "last_valid_callback_at": str(created_at or "")[:80],
        "last_valid_callback_kind": "login" if action == "auth.telegram_login_confirm" else "account_link",
    }


def _telegram_connection_configuration(*, include_observation: bool = False) -> dict:
    """Return safe, browser-displayable readiness for the Bot handoff only."""
    bot_ready = bool(_telegram_bot_username())
    callback_ready = _telegram_callback_receiver_configured()
    bot_adapter_enabled = _telegram_bot_link_adapter_enabled()
    missing: list[str] = []
    if not bot_ready:
        missing.append("BOT_USERNAME")
    if not callback_ready:
        missing.extend(["WEBAPP_LINK_CALLBACK_TOKEN", "WEBAPP_LINK_CALLBACK_HMAC_SECRET"])
    if not bot_adapter_enabled:
        # This is intentionally a non-secret, explicit release gate.  It
        # prevents a Web-only deploy from exposing a one-time flow before the
        # separately reviewed Bot adapter is actually live.
        missing.append("WEBAPP_TELEGRAM_BOT_LINK_ENABLED")
    connection = {
        "mode": "bot_one_time_callback",
        # Telegram Login OIDC has a separate, Web-only setup path. Expose
        # only its feature flag here so customers can distinguish it from the
        # Bot callback handoff without learning a client ID or any secret.
        "oidc_web_login_enabled": _oauth_enabled("telegram"),
        # The username/chat URL is public Bot metadata. It lets signed Web
        # companion pages hand a customer back to the canonical Telegram flow
        # without exposing a Telegram ID, Bot token or bridge credential.
        "bot_username": _telegram_bot_username(),
        "bot_chat_url": f"https://t.me/{_telegram_bot_username()}" if bot_ready else "",
        "bot_deep_link_ready": bot_ready,
        "web_callback_ready": callback_ready,
        "bot_callback_adapter_enabled": bot_adapter_enabled,
        # This Web service cannot read or prove the remote Bot's environment.
        # Keep the readiness wording honest: a successful one-time callback is
        # the end-to-end proof, not this local configuration response.
        "bot_callback_configuration_unverified": True,
        "telegram_auto_register_enabled": _telegram_auto_register_enabled(),
        "missing_configuration": missing,
        "ready": bot_ready and callback_ready and bot_adapter_enabled,
    }
    if include_observation:
        observation = _telegram_callback_observation()
        connection.update(observation)
        # This means exactly what it says: configuration on the remote Bot is
        # not claimed as verified until its signed callback has reached Web.
        connection["bot_callback_configuration_unverified"] = not observation["bot_callback_observed"]
    return connection


def _telegram_connection_required_response() -> dict:
    """Fail closed before minting a code that no configured Bot can finish."""
    connection = _telegram_connection_configuration()
    adapter_pending = not connection["bot_callback_adapter_enabled"]
    return envelope(
        False,
        (
            "Bot chưa được xác nhận đã phát hành adapter liên kết Telegram. Web chưa tạo mã để tránh một mã không thể hoàn tất."
            if adapter_pending
            else "Cầu nối Telegram chưa được cấu hình đầy đủ. Web chưa tạo mã xác minh để tránh một mã không thể hoàn tất."
        ),
        data={
            "raw_telegram_id_accepted": False,
            "missing_configuration": connection["missing_configuration"],
            "reason": "bot_adapter_not_enabled" if adapter_pending else "configuration_missing",
        },
        status_name="guarded",
        error_code="TELEGRAM_LINK_CONFIGURATION_REQUIRED",
    )


def _telegram_only_email(canonical_user_id: str) -> str:
    """Return a non-contactable, HMAC-derived internal account placeholder."""
    subject = str(canonical_user_id or "").strip().encode("utf-8")
    digest = hmac.new(_secret(), subject, hashlib.sha256).hexdigest()[:40]
    return f"telegram-{digest}@{TELEGRAM_ONLY_EMAIL_DOMAIN}"


def _is_telegram_only_email(value: str) -> bool:
    email = str(value or "").strip().lower()
    return bool(re.fullmatch(rf"telegram-[0-9a-f]{{40}}@{re.escape(TELEGRAM_ONLY_EMAIL_DOMAIN)}", email))


def password_login_factor_available(email: str, password_login_enabled: bool) -> bool:
    """Whether this account has a Web password factor that can be used now.

    Internal aliases exist solely to keep a legacy unique-email database
    column intact.  They must never become a password recovery or password
    change surface for Telegram-first/OAuth-only accounts.
    """

    normalized = str(email or "").strip().lower()
    return bool(password_login_enabled) and not _is_telegram_only_email(normalized) and not _is_oauth_only_email(normalized)


def _telegram_deep_link(code: str) -> str:
    bot_username = _telegram_bot_username()
    if not bot_username:
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


def _linked_oauth_providers(account_id: str | None) -> set[str]:
    if not account_id:
        return set()
    ensure_copyfast_schema()
    with transaction() as conn:
        rows = conn.execute(
            "SELECT provider FROM web_external_identities WHERE account_id=?",
            (account_id,),
        ).fetchall()
    return {str(row[0]) for row in rows if str(row[0]) in OAUTH_PROVIDER_NAMES}


def _oauth_verified_contact(account_id: str | None) -> tuple[str, str] | None:
    """Read the signed account's provider-verified public contact narrowly.

    This read is deliberately keyed only by the already authenticated account
    ID.  It never searches by email, and it returns no provider subject,
    token, or account identifier to browser payloads.
    """
    if not account_id:
        return None
    ensure_copyfast_schema()
    with read_transaction() as conn:
        row = conn.execute(
            """SELECT email, provider
               FROM web_account_oauth_contacts
               WHERE account_id=?""",
            (account_id,),
        ).fetchone()
    if not row:
        return None
    email = str(row[0] or "").strip().lower()
    provider = str(row[1] or "")
    if provider not in OAUTH_CONTACT_PROVIDERS or not EMAIL_PATTERN.fullmatch(email):
        return None
    return email, provider


def _email_link_verified_contact(conn, *, account_id: str, expected_email: str) -> bool:
    """Confirm a Web email-link proof still matches this login identifier."""

    normalized = str(expected_email or "").strip().lower()
    if not EMAIL_PATTERN.fullmatch(normalized):
        return False
    row = conn.execute(
        """SELECT email, verification_method
           FROM web_account_email_contacts
           WHERE account_id=?""",
        (account_id,),
    ).fetchone()
    return bool(
        row
        and str(row[1] or "") == "email_link"
        and str(row[0] or "").strip().lower() == normalized
    )


def _store_oauth_verified_contact(conn, *, account_id: str, provider: str, email: str, now: str) -> None:
    """Persist only a freshly verified OAuth contact for one Web account.

    The caller has already validated the provider identity.  There is no
    uniqueness rule on the contact address and no audit text receives it: a
    collision must leave both Web accounts independent.
    """
    normalized = str(email or "").strip().lower()
    if provider not in OAUTH_CONTACT_PROVIDERS or not EMAIL_PATTERN.fullmatch(normalized):
        return
    conn.execute(
        """INSERT INTO web_account_oauth_contacts
           (account_id, provider, email, verified_at, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(account_id) DO UPDATE SET
               provider=excluded.provider,
               email=excluded.email,
               verified_at=excluded.verified_at,
               updated_at=excluded.updated_at""",
        (account_id, provider, normalized, now, now, now),
    )


def browser_account_payload(account: dict) -> dict:
    """Return the minimum account metadata the browser needs to render safely.

    ``canonical_user_id`` is the Telegram identity used by server-to-server
    bridge calls.  It is intentionally absent from every browser-facing auth
    response; the UI only needs to know whether a link exists.
    """
    linked_providers = _linked_oauth_providers(str(account.get("id") or ""))
    email = str(account.get("email") or "")
    telegram_only = _is_telegram_only_email(email)
    oauth_internal_alias = _is_oauth_only_email(email)
    verified_contact = _oauth_verified_contact(str(account.get("id") or ""))
    password_login_enabled = bool(account.get("password_login_enabled", True))
    oauth_only = not password_login_enabled and not telegram_only
    return {
        # A Telegram-first account has an internal deterministic placeholder
        # only to satisfy the existing unique email column. An isolated
        # OAuth collision account uses a different internal alias, which is
        # likewise never displayed or accepted as a password identifier.
        # Its freshly verified OAuth contact is safe to show only to this
        # signed account.
        "email": (
            ""
            if telegram_only or (oauth_internal_alias and not verified_contact)
            else (verified_contact[0] if verified_contact else email)
        ),
        "display_name": str(account.get("display_name") or ""),
        "role": "admin" if account.get("role") == "admin" else "user",
        "telegram_linked": bool(account.get("canonical_user_id")),
        "profile": {
            "locale": normalize_interface_locale(account.get("locale")),
            "timezone": str(account.get("timezone") or "Asia/Ho_Chi_Minh"),
            "avatar_style": str(account.get("avatar_style") or "gradient"),
        },
        "login_methods": {
            "email": password_login_enabled and not telegram_only,
            # This is an OIDC Web-login proof. It is deliberately distinct
            # from `telegram` below: only the signed Bot callback may mark
            # the canonical Bot identity as linked for Xu, jobs and assets.
            "telegram_oidc": "telegram" in linked_providers,
            "telegram": bool(account.get("canonical_user_id")),
            "google": "google" in linked_providers,
            "github": "github" in linked_providers,
            "apple": "apple" in linked_providers,
        },
        # `oauth_only` is explicit UI/API truth, not a promise that a mailbox
        # verification email was sent by this Web service.
        "oauth_only": oauth_only,
        "account_type": "telegram" if telegram_only else ("oauth_only" if oauth_only else "standard"),
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
    session_id = _parse_session_cookie(request.cookies.get(_cookie_name(SESSION_COOKIE)))
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Vui lòng đăng nhập để tiếp tục")
    with transaction() as conn:
        row = conn.execute(
            """SELECT s.id, s.csrf_token, s.expires_at, a.id, a.email, a.display_name,
                      a.canonical_user_id, a.role_cache, a.is_active, a.password_login_enabled,
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
            "password_login_enabled": bool(row[9]),
            "locale": normalize_interface_locale(row[10]),
            "timezone": row[11] or "Asia/Ho_Chi_Minh",
            "avatar_style": row[12] or "gradient",
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


def _insert_session(conn, account_id: str, *, now: str | None = None) -> dict:
    """Persist a fresh signed-session record inside an existing transaction."""

    session_id = str(uuid.uuid4())
    csrf_token = secrets.token_urlsafe(32)
    expires_at = _expiry()
    created_at = now or utc_now()
    conn.execute(
        """INSERT INTO web_sessions (id, account_id, csrf_token, expires_at, created_at, last_seen_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (session_id, account_id, csrf_token, expires_at, created_at, created_at),
    )
    return {"session_id": session_id, "csrf_token": csrf_token, "expires_at": expires_at}


def _set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        _cookie_name(SESSION_COOKIE),
        _session_cookie_value(session_id),
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        max_age=SESSION_TTL_HOURS * 3600,
        path="/",
    )


def _create_session(response: Response, account_id: str) -> dict:
    ensure_copyfast_schema()
    with transaction() as conn:
        session = _insert_session(conn, account_id)
    _set_session_cookie(response, session["session_id"])
    return {"csrf_token": session["csrf_token"], "expires_at": session["expires_at"]}


def _rotate_account_sessions(conn, account_id: str, *, now: str | None = None) -> dict:
    """Revoke every existing session and create exactly one fresh session.

    Password and factor changes invalidate *all* prior signed sessions,
    including the initiating browser.  The caller must set the replacement
    cookie only after this write transaction succeeds.
    """

    rotated_at = now or utc_now()
    conn.execute(
        "UPDATE web_sessions SET revoked_at=? WHERE account_id=? AND revoked_at IS NULL",
        (rotated_at, account_id),
    )
    return _insert_session(conn, account_id, now=rotated_at)


def _session_is_active_for_account(conn, *, session_id: str, account_id: str, now: str | None = None) -> bool:
    """Recheck a signed-session actor while the caller holds its write lock.

    CSRF is proven at request entry, but another security action may rotate
    that session while this request waits for SQLite. Sensitive factor writes
    use this owner-bound check inside their transaction so stale requests do
    not commit after the rotation.
    """

    if not session_id or not account_id:
        return False
    active_at = now or utc_now()
    row = conn.execute(
        """SELECT 1 FROM web_sessions
           WHERE id=? AND account_id=? AND revoked_at IS NULL AND expires_at>?""",
        (session_id, account_id, active_at),
    ).fetchone()
    return bool(row)


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=256)
    display_name: str = Field(default="", max_length=120)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


class EmailVerificationStartRequest(BaseModel):
    """Explicit consent before the signed account asks SMTP to send a link."""

    confirm: bool = False


class PasswordRecoveryStartRequest(BaseModel):
    """Public identifier input; the endpoint always returns the same handoff."""

    email: str = Field(min_length=3, max_length=254)


class SessionRevokeRequest(BaseModel):
    session_ref: str = Field(min_length=64, max_length=64)


def _security_linked_providers(conn, account_id: str) -> set[str]:
    """Read only the signed account's provider names, never subjects/tokens."""

    rows = conn.execute(
        "SELECT provider FROM web_external_identities WHERE account_id=?",
        (account_id,),
    ).fetchall()
    return {str(row[0]) for row in rows if str(row[0]) in OAUTH_PROVIDER_NAMES}


def _security_login_methods(conn, *, account_id: str, email: str, password_login_enabled: bool) -> dict:
    """Build the intentionally minimal login-factor projection for one owner.

    Contact is deliberately an assurance label rather than a recovery
    mechanism. A password registration is never proof on its own: the signed
    account must either complete a Web-owned one-time mailbox link or present
    a matching provider-verified OAuth contact. No contact state can merge,
    reclaim, delete or access another account.
    """

    linked = _security_linked_providers(conn, account_id)
    password_available = password_login_factor_available(email, password_login_enabled)
    oauth = []
    usable_factor_count = 1 if password_available else 0
    for provider in sorted(OAUTH_PROVIDER_NAMES):
        provider_linked = provider in linked
        enabled = _oauth_enabled(provider)
        usable = provider_linked and enabled
        if usable:
            usable_factor_count += 1
        oauth.append(
            {
                "provider": provider,
                "linked": provider_linked,
                "enabled": enabled,
                # A linked, disabled provider is deliberately not removable
                # here. The operator must restore/retire configuration through
                # the controlled deployment path, never through a customer UI.
                "can_unlink": bool(usable and usable_factor_count),
            }
        )
    # Calculate each button only after all current factors are known. This
    # avoids a loop-order bug where the first linked provider appears to be
    # the last factor even when another provider follows it.
    for item in oauth:
        item["can_unlink"] = bool(
            item["linked"]
            and item["enabled"]
            and usable_factor_count > 1
        )

    normalized_email = str(email or "").strip().lower()
    contact_row = conn.execute(
        """SELECT provider, email
           FROM web_account_oauth_contacts
           WHERE account_id=?""",
        (account_id,),
    ).fetchone()
    contact_provider = str(contact_row[0]) if contact_row else ""
    contact_email = str(contact_row[1]).strip().lower() if contact_row else ""
    # The contact record is a derived convenience projection, not a standalone
    # login factor.  Recheck the immutable provider-identity binding before
    # it can serve as email-ownership evidence; this makes a stale/corrupt
    # contact row fail closed even if an interrupted maintenance operation ever
    # left it behind.
    contact_identity_exists = bool(
        contact_provider in OAUTH_CONTACT_PROVIDERS
        and conn.execute(
            """SELECT 1 FROM web_external_identities
               WHERE account_id=? AND provider=?""",
            (account_id, contact_provider),
        ).fetchone()
    )
    contact_is_verified = bool(
        contact_identity_exists
        and EMAIL_PATTERN.fullmatch(contact_email)
    )
    email_link_verified = _email_link_verified_contact(
        conn,
        account_id=account_id,
        expected_email=normalized_email,
    )
    now = utc_now()
    pending_email_verification = bool(
        conn.execute(
            """SELECT 1 FROM web_email_verification_challenges
               WHERE account_id=? AND state='sent' AND expires_at>? LIMIT 1""",
            (account_id, now),
        ).fetchone()
    )
    email_delivery_available = email_verification_delivery_available()
    # A Telegram-only placeholder is never a contact address.  Conversely, an
    # OAuth-only account can show an OAuth contact as verified even though its
    # internal unique-email alias must remain hidden from customers.
    if _is_telegram_only_email(normalized_email):
        contact = {"state": "not_applicable", "provider": "", "verified": False}
    elif email_link_verified and password_available:
        contact = {"state": "verified_email_link", "provider": "email_link", "verified": True}
    elif contact_is_verified and (
        _is_oauth_only_email(normalized_email)
        # These are normalized account-contact identifiers, not credentials
        # or an oracle on an unauthenticated endpoint.  Plain equality keeps
        # internationalized email local-parts safe; ``compare_digest`` rejects
        # non-ASCII ``str`` values on supported Python runtimes.
        or contact_email == normalized_email
    ):
        contact = {"state": "verified_oauth", "provider": contact_provider, "verified": True}
    elif password_available:
        # Do not expose a mismatched provider contact as a hint about another
        # mailbox.  The signed user sees only that this particular login email
        # has not yet been independently proven.
        contact = {"state": "unverified", "provider": "", "verified": False}
    else:
        contact = {"state": "unavailable", "provider": "", "verified": False}
    return {
        "password": {"available": password_available},
        "oauth": oauth,
        "usable_factor_count": usable_factor_count,
        "contact": contact,
        "email_verification": {
            "available": email_delivery_available,
            "can_start": bool(
                password_available
                and not contact["verified"]
                and email_delivery_available
            ),
            "pending": bool(
                password_available
                and not contact["verified"]
                and pending_email_verification
            ),
        },
    }


def _password_change_policy_error(value: str) -> str | None:
    """Keep a small, stable policy without retaining the submitted secret."""

    if len(value) < 12 or len(value) > 256:
        return "Mật khẩu mới phải có từ 12 đến 256 ký tự."
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        return "Mật khẩu mới có ký tự điều khiển không hợp lệ."
    return None


class TelegramAccountUpgradeRequest(BaseModel):
    """Add an email/password login method to the same Telegram-first account."""

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=256)


class ProfileUpdateRequest(BaseModel):
    display_name: str = Field(default="", max_length=120)
    locale: str = Field(default="vi", max_length=16)
    timezone: str = Field(default="Asia/Ho_Chi_Minh", max_length=64)


class InterfaceLocaleUpdateRequest(BaseModel):
    """The narrow, presentation-only write used by the locale navigator.

    This must remain distinct from the broader profile form: a stale language
    tab may change only its exact reviewed locale and cannot replay hidden
    display-name/time-zone/identity values into the signed account.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    locale: str = Field(min_length=2, max_length=16)


class LinkConfirmation(BaseModel):
    code: str = Field(min_length=8, max_length=128)
    canonical_user_id: str = Field(min_length=1, max_length=128)
    role: str = Field(default="user", max_length=32)
    display_name: str = Field(default="", max_length=120)


class OAuthIdentityError(RuntimeError):
    """A provider failure that is safe to expose only as a generic handoff."""


def _oauth_account_from_row(row: tuple) -> dict:
    return {
        "id": row[0],
        "email": row[1],
        "display_name": row[2] or "",
        "canonical_user_id": row[3],
        "role": row[4] or "user",
        "is_active": bool(row[5]),
        "password_login_enabled": bool(row[6]),
        "locale": normalize_interface_locale(row[7]),
        "timezone": row[8] or "Asia/Ho_Chi_Minh",
        "avatar_style": row[9] or "gradient",
    }


def _create_telegram_only_account(conn, *, canonical_user_id: str, role: str, display_name: str, request: Request) -> dict:
    """Create a minimal Web account only after signed Bot proof.

    This is deliberately a Web-only identity shell. The Bot remains the
    identity authority and is not mutated; password login is disabled and the
    placeholder email is never returned to the browser.
    """
    account_id = str(uuid.uuid4())
    now = utc_now()
    safe_role = "admin" if role == "admin" else "user"
    # The Bot can legitimately withhold a display name.  A useful Web-owned
    # default keeps profile/header rendering stable without fabricating an
    # email address or exposing the canonical Telegram identity.
    safe_name = str(display_name or "").strip()[:120] or "Người dùng Telegram"
    email = _telegram_only_email(canonical_user_id)
    conn.execute(
        """INSERT INTO web_accounts
           (id, email, password_hash, display_name, canonical_user_id, role_cache, password_login_enabled, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)""",
        (account_id, email, _password_hash(secrets.token_urlsafe(48)), safe_name, canonical_user_id, safe_role, now, now),
    )
    conn.execute(
        """INSERT INTO web_account_profiles
           (account_id, locale, timezone, avatar_style, created_at, updated_at)
           VALUES (?, 'vi', 'Asia/Ho_Chi_Minh', 'gradient', ?, ?)""",
        (account_id, now, now),
    )
    _record_audit(
        conn,
        account_id=account_id,
        canonical_user_id=canonical_user_id,
        action="auth.telegram_auto_register",
        request_id=_request_id(request),
        detail="created telegram-only web account after signed bot proof",
    )
    return {
        "id": account_id, "email": email, "display_name": safe_name,
        "canonical_user_id": canonical_user_id, "role": safe_role,
        "is_active": True, "password_login_enabled": False,
        "locale": "vi", "timezone": "Asia/Ho_Chi_Minh", "avatar_style": "gradient",
    }


def _set_oauth_state_cookie(response: Response, provider: str, state_value: str) -> None:
    response.set_cookie(
        _oauth_state_cookie_name(provider, state_value),
        _oauth_state_cookie_value(provider, state_value),
        httponly=True,
        secure=_cookie_secure(),
        # Apple posts its authorization response cross-site. Its short-lived
        # state cookie must therefore be None+Secure, while the main session
        # cookie deliberately remains Lax and is never weakened for OAuth.
        samesite=_oauth_state_cookie_samesite(provider),
        max_age=OAUTH_STATE_TTL_MINUTES * 60,
        path="/",
    )


def _matching_oauth_state_cookie_name(request: Request, provider: str, state_value: str) -> str | None:
    """Find only the signed browser proof for this callback attempt.

    The final fixed-name candidate accepts a state issued by the immediately
    preceding deployment for at most its existing TTL.  It is intentionally a
    read-only migration fallback: all new starts receive an independent
    state-specific cookie, and a callback never clears an unrelated attempt.
    """
    if provider not in OAUTH_PROVIDER_NAMES or not state_value or len(state_value) > OAUTH_STATE_VALUE_MAX_LENGTH:
        return None
    candidates = (
        _oauth_state_cookie_name(provider, state_value),
        _cookie_name(OAUTH_STATE_COOKIE),
    )
    for cookie_name in candidates:
        cookie = _parse_oauth_state_cookie(request.cookies.get(cookie_name))
        if cookie and cookie[0] == provider and hmac.compare_digest(cookie[1], state_value):
            return cookie_name
    return None


def _clear_oauth_state_cookie(
    response: Response,
    *,
    request: Request,
    provider: str,
    state_value: str,
    cookie_name: str | None = None,
) -> None:
    """Delete only the state proof consumed or rejected by this callback."""
    matching_name = cookie_name or _matching_oauth_state_cookie_name(request, provider, state_value)
    if not matching_name:
        return
    response.delete_cookie(
        matching_name,
        path="/",
        secure=_cookie_secure(),
        httponly=True,
        samesite=_oauth_state_cookie_samesite(provider),
    )


def _set_oauth_link_cookie(response: Response, provider: str, session_id: str, ticket: str) -> None:
    response.set_cookie(
        _cookie_name(OAUTH_LINK_COOKIE),
        _oauth_link_cookie_value(provider, session_id, ticket),
        httponly=True,
        secure=_cookie_secure(),
        samesite="none" if provider == "apple" else "lax",
        max_age=OAUTH_STATE_TTL_MINUTES * 60,
        path="/",
    )


def _clear_oauth_link_cookie(response: Response) -> None:
    response.delete_cookie(_cookie_name(OAUTH_LINK_COOKIE), path="/", secure=_cookie_secure(), httponly=True, samesite="lax")


def _create_oauth_state(
    provider: str,
    *,
    purpose: str,
    account_id: str | None,
    initiating_session_id: str | None,
    return_path: str,
) -> str:
    if provider not in OAUTH_PROVIDER_NAMES or purpose not in {"signin", "link"}:
        raise ValueError("OAuth state không hợp lệ")
    state_value = secrets.token_urlsafe(32)
    with transaction() as conn:
        now = utc_now()
        conn.execute("DELETE FROM web_oauth_states WHERE expires_at<=? OR consumed_at IS NOT NULL", (now,))
        conn.execute(
            """INSERT INTO web_oauth_states
            (state_hash, provider, purpose, account_id, initiating_session_id, return_path, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                _oauth_state_hash(state_value),
                provider,
                purpose,
                account_id,
                initiating_session_id,
                _safe_oauth_return_path(return_path),
                _oauth_expiry(),
                now,
            ),
        )
    return state_value


def _oauth_authorization_url(provider: str, state_value: str) -> str:
    config = _oauth_client_configuration(provider)
    params = {
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "response_type": "code",
        "state": state_value,
        "code_challenge": _oauth_code_challenge(state_value),
        "code_challenge_method": "S256",
    }
    if provider == "google":
        params.update({"scope": "openid email profile", "nonce": _oauth_derived_token("nonce", state_value), "prompt": "select_account"})
        return f"{GOOGLE_AUTHORIZE_URL}?{urlencode(params)}"
    if provider == "apple":
        # Apple uses a form POST callback for name/email scopes. Its token
        # exchange authenticates the client with a short-lived ES256 JWT,
        # rather than the generic PKCE code verifier used above.
        apple_params = {
            "client_id": config["client_id"],
            "redirect_uri": config["redirect_uri"],
            "response_type": "code id_token",
            "response_mode": "form_post",
            "scope": "name email",
            "state": state_value,
            "nonce": _oauth_derived_token("nonce", state_value),
        }
        return f"{APPLE_AUTHORIZE_URL}?{urlencode(apple_params)}"
    if provider == "telegram":
        # Telegram's current Login product supports standards-based OIDC
        # authorization-code flow with PKCE. The browser is redirected only
        # to Telegram; its code and tokens never return to portal JavaScript.
        params.update({
            "scope": "openid profile",
            "nonce": _oauth_derived_token("nonce", state_value),
        })
        return f"{TELEGRAM_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"
    params.update({"scope": "read:user user:email", "allow_signup": "true"})
    return f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"


def _oauth_redirect(reason: str, *, path: str = "/login") -> RedirectResponse:
    # Reasons are internal fixed slugs only. Never pass a provider response,
    # access token, email address or unvalidated `next` URL to the browser.
    allowed = {"unavailable", "cancelled", "failed", "state", "session", "link-required", "linked", "already-linked"}
    safe_reason = reason if reason in allowed else "failed"
    separator = "&" if "?" in path else "?"
    return RedirectResponse(f"{path}{separator}oauth={safe_reason}", status_code=status.HTTP_303_SEE_OTHER)


def _consume_oauth_state(request: Request, provider: str, state_value: str) -> dict | None:
    cookie_name = _matching_oauth_state_cookie_name(request, provider, state_value)
    if not cookie_name:
        return None
    with transaction() as conn:
        row = conn.execute(
            """SELECT provider, purpose, account_id, initiating_session_id, return_path, expires_at, consumed_at
               FROM web_oauth_states WHERE state_hash=?""",
            (_oauth_state_hash(state_value),),
        ).fetchone()
        if not row or row[0] != provider or row[6] or _as_time(row[5]) <= _now():
            return None
        conn.execute("UPDATE web_oauth_states SET consumed_at=? WHERE state_hash=?", (utc_now(), _oauth_state_hash(state_value)))
    return {
        "provider": row[0],
        "purpose": row[1],
        "account_id": row[2],
        "initiating_session_id": row[3],
        "return_path": row[4],
        # This value remains server-internal.  It lets every callback outcome
        # remove exactly its own proof instead of invalidating other tabs.
        "_state_cookie_name": cookie_name,
    }


async def _oauth_json_request(method: str, url: str, **kwargs) -> dict:
    try:
        async with httpx.AsyncClient(timeout=OAUTH_HTTP_TIMEOUT_SECONDS, follow_redirects=False) as client:
            response = await client.request(method, url, **kwargs)
    except httpx.HTTPError as exc:
        raise OAuthIdentityError("OAuth provider không phản hồi") from exc
    if response.status_code < 200 or response.status_code >= 300:
        raise OAuthIdentityError("OAuth provider từ chối yêu cầu")
    try:
        payload = response.json()
    except ValueError as exc:
        raise OAuthIdentityError("OAuth provider trả dữ liệu không hợp lệ") from exc
    if not isinstance(payload, dict):
        raise OAuthIdentityError("OAuth provider trả dữ liệu không hợp lệ")
    return payload


async def _verify_google_id_token(id_token: str, *, client_id: str, expected_nonce: str) -> dict:
    """Verify a Google OIDC ID token using fixed Google JWKS endpoints."""
    try:
        import jwt  # type: ignore[import-not-found]

        header = jwt.get_unverified_header(id_token)
        if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
            raise OAuthIdentityError("Google ID token không hợp lệ")
        jwks = await _oauth_json_request("GET", GOOGLE_JWKS_URL, headers={"Accept": "application/json"})
        keys = jwks.get("keys")
        if not isinstance(keys, list):
            raise OAuthIdentityError("Google JWKS không hợp lệ")
        matching = next((item for item in keys if isinstance(item, dict) and item.get("kid") == header["kid"] and item.get("kty") == "RSA"), None)
        if not matching:
            raise OAuthIdentityError("Google signing key không hợp lệ")
        key = jwt.PyJWK.from_dict(matching).key
        claims = jwt.decode(
            id_token,
            key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=["https://accounts.google.com", "accounts.google.com"],
            options={"require": ["exp", "iat", "sub", "nonce"]},
        )
    except OAuthIdentityError:
        raise
    except Exception as exc:  # PyJWT errors intentionally stay generic.
        raise OAuthIdentityError("Google ID token không được xác minh") from exc
    if not hmac.compare_digest(str(claims.get("nonce") or ""), expected_nonce):
        raise OAuthIdentityError("Google nonce không hợp lệ")
    verified = claims.get("email_verified")
    if verified not in {True, "true", "True"}:
        raise OAuthIdentityError("Google email chưa được xác minh")
    email = str(claims.get("email") or "").strip().lower()
    subject = str(claims.get("sub") or "").strip()
    if not EMAIL_PATTERN.fullmatch(email) or not subject:
        raise OAuthIdentityError("Google identity không hợp lệ")
    return {
        "provider": "google",
        "subject": subject,
        "email": email,
        "email_verified": True,
        "display_name": str(claims.get("name") or "").strip()[:120],
    }


async def _fetch_google_identity(code: str, state_value: str) -> dict:
    config = _oauth_client_configuration("google")
    tokens = await _oauth_json_request(
        "POST",
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "redirect_uri": config["redirect_uri"],
            "grant_type": "authorization_code",
            "code_verifier": _oauth_derived_token("pkce", state_value),
        },
        headers={"Accept": "application/json"},
    )
    id_token = str(tokens.get("id_token") or "")
    if not id_token:
        raise OAuthIdentityError("Google không trả identity token")
    return await _verify_google_id_token(
        id_token,
        client_id=config["client_id"],
        expected_nonce=_oauth_derived_token("nonce", state_value),
    )


async def _verify_telegram_id_token(id_token: str, *, client_id: str, expected_nonce: str) -> dict:
    """Verify a Telegram OIDC token and extract only the canonical user hint.

    Telegram's OIDC `sub` can be an application-specific stable subject,
    while the optional `profile` claim `id` is the Telegram user ID that
    the Bot sees. We validate both cryptographically, store only an HMAC of
    `id` in the Web identity table, and never return either raw value to the
    browser. This lets the later Bot deep-link prove that it is the same
    Telegram account before the portal treats any Bot data as canonical.
    """
    try:
        import jwt  # type: ignore[import-not-found]

        header = jwt.get_unverified_header(id_token)
        # BotFather's default Telegram Login signing algorithm is RS256. Do
        # not silently accept a different administrator-selected algorithm:
        # failing closed avoids broadening the JWT verifier unexpectedly.
        if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
            raise OAuthIdentityError("Telegram ID token không hợp lệ")
        jwks = await _oauth_json_request("GET", TELEGRAM_OAUTH_JWKS_URL, headers={"Accept": "application/json"})
        keys = jwks.get("keys")
        if not isinstance(keys, list):
            raise OAuthIdentityError("Telegram JWKS không hợp lệ")
        matching = next(
            (
                item for item in keys
                if isinstance(item, dict)
                and item.get("kid") == header["kid"]
                and item.get("kty") == "RSA"
                and item.get("use", "sig") == "sig"
                and item.get("alg", "RS256") == "RS256"
            ),
            None,
        )
        if not matching:
            raise OAuthIdentityError("Telegram signing key không hợp lệ")
        key = jwt.PyJWK.from_dict(matching).key
        claims = jwt.decode(
            id_token,
            key,
            algorithms=["RS256"],
            audience=client_id,
            issuer="https://oauth.telegram.org",
            options={"require": ["exp", "iat", "sub", "nonce", "id"]},
        )
    except OAuthIdentityError:
        raise
    except Exception as exc:  # PyJWT/JWKS errors are intentionally generic.
        raise OAuthIdentityError("Telegram ID token không được xác minh") from exc
    if not hmac.compare_digest(str(claims.get("nonce") or ""), expected_nonce):
        raise OAuthIdentityError("Telegram nonce không hợp lệ")
    raw_id = claims.get("id")
    if isinstance(raw_id, bool):
        raise OAuthIdentityError("Telegram identity không hợp lệ")
    telegram_user_id = str(raw_id or "").strip()
    if not re.fullmatch(r"[1-9][0-9]{0,19}", telegram_user_id):
        raise OAuthIdentityError("Telegram identity không hợp lệ")
    if not str(claims.get("sub") or "").strip():
        raise OAuthIdentityError("Telegram identity không hợp lệ")
    display_name = str(claims.get("name") or claims.get("preferred_username") or "").strip()[:120]
    return {
        "provider": "telegram",
        # Use the Bot-compatible numeric ID, not OIDC's app-specific `sub`,
        # as the HMAC-protected external-identity key.
        "subject": telegram_user_id,
        "email": "",
        "email_verified": False,
        "display_name": display_name,
    }


async def _fetch_telegram_identity(code: str, state_value: str) -> dict:
    config = _oauth_client_configuration("telegram")
    basic_credentials = base64.b64encode(
        f"{config['client_id']}:{config['client_secret']}".encode("utf-8")
    ).decode("ascii")
    tokens = await _oauth_json_request(
        "POST",
        TELEGRAM_OAUTH_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config["redirect_uri"],
            "client_id": config["client_id"],
            "code_verifier": _oauth_derived_token("pkce", state_value),
        },
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {basic_credentials}",
        },
    )
    id_token = str(tokens.get("id_token") or "")
    if not id_token:
        raise OAuthIdentityError("Telegram không trả identity token")
    return await _verify_telegram_id_token(
        id_token,
        client_id=config["client_id"],
        expected_nonce=_oauth_derived_token("nonce", state_value),
    )


async def _fetch_github_identity(code: str, state_value: str) -> dict:
    config = _oauth_client_configuration("github")
    tokens = await _oauth_json_request(
        "POST",
        GITHUB_TOKEN_URL,
        data={
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "code": code,
            "redirect_uri": config["redirect_uri"],
            "code_verifier": _oauth_derived_token("pkce", state_value),
        },
        headers={"Accept": "application/json"},
    )
    access_token = str(tokens.get("access_token") or "")
    if not access_token:
        raise OAuthIdentityError("GitHub không trả access token")
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {access_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    profile = await _oauth_json_request("GET", GITHUB_USER_URL, headers=headers)
    # `/user/emails` returns a JSON list; use a separate request here so the
    # generic JSON helper remains strict for token/profile objects.
    try:
        async with httpx.AsyncClient(timeout=OAUTH_HTTP_TIMEOUT_SECONDS, follow_redirects=False) as client:
            emails_response = await client.get(GITHUB_EMAILS_URL, headers=headers)
        if emails_response.status_code < 200 or emails_response.status_code >= 300:
            raise OAuthIdentityError("GitHub email không khả dụng")
        emails = emails_response.json()
    except OAuthIdentityError:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        raise OAuthIdentityError("GitHub email không khả dụng") from exc
    if not isinstance(emails, list):
        raise OAuthIdentityError("GitHub email không hợp lệ")
    email_entry = next((item for item in emails if isinstance(item, dict) and item.get("primary") is True and item.get("verified") is True), None)
    if not email_entry:
        email_entry = next((item for item in emails if isinstance(item, dict) and item.get("verified") is True), None)
    email = str((email_entry or {}).get("email") or "").strip().lower()
    subject = str(profile.get("id") or "").strip()
    if not EMAIL_PATTERN.fullmatch(email) or not subject:
        raise OAuthIdentityError("GitHub identity không hợp lệ")
    display_name = str(profile.get("name") or profile.get("login") or "").strip()[:120]
    return {
        "provider": "github",
        "subject": subject,
        "email": email,
        "email_verified": True,
        "display_name": display_name,
    }


def _apple_private_key(config: dict) -> str:
    encoded = "".join(str(config.get("private_key_base64") or "").split())
    try:
        raw = base64.b64decode(encoded + "=" * (-len(encoded) % 4), validate=True)
        key = raw.decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise OAuthIdentityError("Apple private key không hợp lệ") from exc
    if "BEGIN PRIVATE KEY" not in key or "END PRIVATE KEY" not in key:
        raise OAuthIdentityError("Apple private key không hợp lệ")
    return key


def _apple_client_secret(config: dict) -> str:
    """Create a short-lived ES256 Apple client secret; never persist it."""
    try:
        import jwt  # type: ignore[import-not-found]

        now = int(_now().timestamp())
        return str(
            jwt.encode(
                {
                    "iss": config["team_id"],
                    "iat": now,
                    "exp": now + 300,
                    "aud": "https://appleid.apple.com",
                    "sub": config["client_id"],
                },
                _apple_private_key(config),
                algorithm="ES256",
                headers={"kid": config["key_id"]},
            )
        )
    except OAuthIdentityError:
        raise
    except Exception as exc:
        raise OAuthIdentityError("Không thể tạo Apple client secret") from exc


async def _verify_apple_id_token(id_token: str, *, client_id: str, expected_nonce: str) -> dict:
    try:
        import jwt  # type: ignore[import-not-found]

        header = jwt.get_unverified_header(id_token)
        # Apple client *secrets* are ES256, but Apple-issued ID tokens are
        # signed with Apple's RSA JWKS and must be verified as RS256.
        if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
            raise OAuthIdentityError("Apple ID token không hợp lệ")
        jwks = await _oauth_json_request("GET", APPLE_JWKS_URL, headers={"Accept": "application/json"})
        keys = jwks.get("keys")
        if not isinstance(keys, list):
            raise OAuthIdentityError("Apple JWKS không hợp lệ")
        matching = next(
            (
                item for item in keys
                if isinstance(item, dict)
                and item.get("kid") == header["kid"]
                and item.get("kty") == "RSA"
                and item.get("use", "sig") == "sig"
                and item.get("alg", "RS256") == "RS256"
            ),
            None,
        )
        if not matching:
            raise OAuthIdentityError("Apple signing key không hợp lệ")
        key = jwt.PyJWK.from_dict(matching).key
        claims = jwt.decode(
            id_token,
            key,
            algorithms=["RS256"],
            audience=client_id,
            issuer="https://appleid.apple.com",
            options={"require": ["exp", "iat", "sub", "nonce"]},
        )
    except OAuthIdentityError:
        raise
    except Exception as exc:
        raise OAuthIdentityError("Apple ID token không được xác minh") from exc
    if not hmac.compare_digest(str(claims.get("nonce") or ""), expected_nonce):
        raise OAuthIdentityError("Apple nonce không hợp lệ")
    subject = str(claims.get("sub") or "").strip()
    if not subject:
        raise OAuthIdentityError("Apple identity không hợp lệ")
    verified = claims.get("email_verified")
    email = str(claims.get("email") or "").strip().lower()
    if email and verified not in {True, "true", "True"}:
        raise OAuthIdentityError("Apple email chưa được xác minh")
    if email and not EMAIL_PATTERN.fullmatch(email):
        raise OAuthIdentityError("Apple email không hợp lệ")
    return {
        "provider": "apple",
        "subject": subject,
        "email": email,
        "email_verified": bool(email),
    }


def _apple_display_name(value: str | None) -> str:
    """Use the optional first-authorization name for display only, never ID."""
    raw = str(value or "")
    if not raw or len(raw) > 4096:
        return ""
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return ""
    name = data.get("name") if isinstance(data, dict) else None
    if not isinstance(name, dict):
        return ""
    pieces = [str(name.get(key) or "").strip() for key in ("firstName", "lastName")]
    display_name = " ".join(item for item in pieces if item)
    return "".join(character for character in display_name if ord(character) >= 32).strip()[:120]


async def _fetch_apple_identity(code: str, state_value: str, *, display_name: str = "") -> dict:
    config = _oauth_client_configuration("apple")
    tokens = await _oauth_json_request(
        "POST",
        APPLE_TOKEN_URL,
        data={
            "client_id": config["client_id"],
            "client_secret": _apple_client_secret(config),
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": config["redirect_uri"],
        },
        headers={"Accept": "application/json"},
    )
    id_token = str(tokens.get("id_token") or "")
    if not id_token:
        raise OAuthIdentityError("Apple không trả identity token")
    identity = await _verify_apple_id_token(
        id_token,
        client_id=config["client_id"],
        expected_nonce=_oauth_derived_token("nonce", state_value),
    )
    identity["display_name"] = display_name
    return identity


async def _fetch_oauth_identity(provider: str, code: str, state_value: str) -> dict:
    if provider == "google":
        return await _fetch_google_identity(code, state_value)
    if provider == "telegram":
        return await _fetch_telegram_identity(code, state_value)
    if provider == "github":
        return await _fetch_github_identity(code, state_value)
    raise OAuthIdentityError("OAuth provider không hợp lệ")


def _oauth_signin_account(identity: dict, request: Request) -> tuple[dict | None, str]:
    provider = str(identity.get("provider") or "")
    subject = str(identity.get("subject") or "")
    verified_contact_email = _verified_oauth_contact_email(identity)
    display_name = str(identity.get("display_name") or "").strip()[:120]
    if provider not in OAUTH_PROVIDER_NAMES or not subject:
        return None, "failed"
    subject_hash = _external_subject_hash(provider, subject)
    with transaction() as conn:
        row = conn.execute(
            """SELECT a.id, a.email, a.display_name, a.canonical_user_id, a.role_cache, a.is_active,
                      a.password_login_enabled, p.locale, p.timezone, p.avatar_style
               FROM web_external_identities i JOIN web_accounts a ON a.id=i.account_id
               LEFT JOIN web_account_profiles p ON p.account_id=a.id
               WHERE i.provider=? AND i.subject_hash=?""",
            (provider, subject_hash),
        ).fetchone()
        if row:
            account = _oauth_account_from_row(row)
            if not account["is_active"]:
                _record_audit(conn, account_id=account["id"], canonical_user_id=account["canonical_user_id"], action="oauth.signin", request_id=_request_id(request), target=provider, outcome="denied", detail="inactive account")
                return None, "failed"
            now = utc_now()
            # A previous mapping remains the sign-in authority even when a
            # provider omits a contact on a later callback (notably Apple).
            # Refresh the Web-owned contact only where this very identity
            # supplied a new, explicitly verified address and it cannot turn
            # a password account into a different person's mailbox.
            if verified_contact_email and (
                not account["password_login_enabled"]
                or hmac.compare_digest(str(account["email"] or "").strip().lower(), verified_contact_email)
            ):
                _store_oauth_verified_contact(
                    conn,
                    account_id=account["id"],
                    provider=provider,
                    email=verified_contact_email,
                    now=now,
                )
            conn.execute("UPDATE web_external_identities SET last_login_at=? WHERE provider=? AND subject_hash=?", (now, provider, subject_hash))
            _record_audit(conn, account_id=account["id"], canonical_user_id=account["canonical_user_id"], action="oauth.signin", request_id=_request_id(request), target=provider)
            return account, "ok"
        if provider == "telegram":
            # A verified Telegram OIDC profile contains the actual Telegram
            # user ID in its signed `id` claim. If the same ID is already
            # canonical from the Bot callback, this is the one safe automatic
            # join: both independent proofs identify the exact same Telegram
            # principal. It avoids forcing established Bot users to create a
            # duplicate Web account solely to use Telegram Login.
            canonical_row = conn.execute(
                """SELECT a.id, a.email, a.display_name, a.canonical_user_id, a.role_cache, a.is_active,
                          a.password_login_enabled, p.locale, p.timezone, p.avatar_style
                   FROM web_accounts a LEFT JOIN web_account_profiles p ON p.account_id=a.id
                   WHERE a.canonical_user_id=?""",
                (subject,),
            ).fetchone()
            if canonical_row:
                account = _oauth_account_from_row(canonical_row)
                if not account["is_active"]:
                    _record_audit(conn, account_id=account["id"], canonical_user_id=account["canonical_user_id"], action="oauth.signin", request_id=_request_id(request), target=provider, outcome="denied", detail="inactive canonical Telegram account")
                    return None, "failed"
                now = utc_now()
                conn.execute(
                    """INSERT INTO web_external_identities (provider, subject_hash, account_id, created_at, last_login_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (provider, subject_hash, account["id"], now, now),
                )
                _record_audit(conn, account_id=account["id"], canonical_user_id=account["canonical_user_id"], action="oauth.signin", request_id=_request_id(request), target=provider, detail="attached verified Telegram OIDC to canonical Bot account")
                return account, "ok"
        # A first Apple authorization may not include an email. Existing
        # identities were handled above, but a new Google/GitHub/Apple
        # account requires an explicit freshly verified contact. Telegram is
        # the exception: its signed profile ID is a login identity and gets a
        # non-contactable internal placeholder until the customer optionally
        # adds Email + password.
        contact_email = ""
        isolated_collision = False
        if provider == "telegram":
            account_email = _telegram_only_email(subject)
        else:
            contact_email = verified_contact_email
            if not contact_email:
                _record_audit(conn, account_id=None, canonical_user_id=None, action="oauth.signin", request_id=_request_id(request), target=provider, outcome="denied", detail="new provider identity has no verified email")
                return None, "failed"
            # Do not load, mutate, audit against, or issue a session for the
            # pre-existing account. A presence check is enough to select a
            # separate internal alias for the freshly verified OAuth user.
            email_collision = conn.execute(
                "SELECT 1 FROM web_accounts WHERE email=? LIMIT 1",
                (contact_email,),
            ).fetchone()
            isolated_collision = bool(email_collision)
            account_email = _oauth_only_email(provider, subject) if isolated_collision else contact_email
            if isolated_collision:
                # The HMAC alias should be unique to this immutable identity.
                # A conflicting legacy/corrupt alias is guarded instead of
                # attaching this sign-in to any account we did not create.
                alias_taken = conn.execute(
                    "SELECT 1 FROM web_accounts WHERE email=? LIMIT 1",
                    (account_email,),
                ).fetchone()
                if alias_taken:
                    _record_audit(conn, account_id=None, canonical_user_id=None, action="oauth.signin", request_id=_request_id(request), target=provider, outcome="denied", detail="oauth-only internal alias is already reserved")
                    return None, "failed"
        account_id = str(uuid.uuid4())
        now = utc_now()
        conn.execute(
            """INSERT INTO web_accounts
            (id, email, password_hash, display_name, password_login_enabled, created_at, updated_at)
            VALUES (?, ?, ?, ?, 0, ?, ?)""",
            (account_id, account_email, _password_hash(secrets.token_urlsafe(48)), display_name, now, now),
        )
        conn.execute(
            """INSERT INTO web_account_profiles
            (account_id, locale, timezone, avatar_style, created_at, updated_at)
            VALUES (?, 'vi', 'Asia/Ho_Chi_Minh', 'gradient', ?, ?)""",
            (account_id, now, now),
        )
        conn.execute(
            """INSERT INTO web_external_identities (provider, subject_hash, account_id, created_at, last_login_at)
            VALUES (?, ?, ?, ?, ?)""",
            (provider, subject_hash, account_id, now, now),
        )
        if contact_email:
            _store_oauth_verified_contact(
                conn,
                account_id=account_id,
                provider=provider,
                email=contact_email,
                now=now,
            )
        account = {
            "id": account_id, "email": account_email, "display_name": display_name, "canonical_user_id": None,
            "role": "user", "is_active": True, "password_login_enabled": False,
            "locale": "vi", "timezone": "Asia/Ho_Chi_Minh", "avatar_style": "gradient",
        }
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=None,
            action="oauth.signin",
            request_id=_request_id(request),
            target=provider,
            detail=(
                "created isolated oauth-only web account after verified-contact collision"
                if isolated_collision
                else "created oauth-only web account"
            ),
        )
    return account, "ok"


def _link_oauth_identity(
    identity: dict,
    account: dict,
    request: Request,
    *,
    initiating_session_id: str,
) -> tuple[str, dict | None]:
    """Attach one OAuth factor and rotate every prior signed session.

    The callback validates its state/browser proof before this call. A second
    owner-bound check inside this mutation transaction closes the small window
    in which another security action can rotate the initiating session.
    """

    provider = str(identity.get("provider") or "")
    subject = str(identity.get("subject") or "")
    verified_contact_email = _verified_oauth_contact_email(identity)
    if provider not in OAUTH_PROVIDER_NAMES or not subject or not initiating_session_id:
        return "failed", None
    subject_hash = _external_subject_hash(provider, subject)
    with transaction() as conn:
        if not _session_is_active_for_account(
            conn,
            session_id=initiating_session_id,
            account_id=str(account["id"]),
        ):
            _record_audit(
                conn,
                account_id=account["id"],
                canonical_user_id=account["canonical_user_id"],
                action="oauth.link",
                request_id=_request_id(request),
                target=provider,
                outcome="denied",
                detail="initiating signed session is no longer active",
            )
            return "session", None
        # A customer who already has a canonical Bot identity may only attach
        # Telegram Login for that same signed Telegram user. This preserves
        # the one-person, one-canonical-identity boundary across OIDC and the
        # Bot deep-link without ever exposing either ID to JavaScript.
        if provider == "telegram" and account.get("canonical_user_id") and not hmac.compare_digest(str(account["canonical_user_id"]), subject):
            _record_audit(conn, account_id=account["id"], canonical_user_id=account["canonical_user_id"], action="oauth.link", request_id=_request_id(request), target=provider, outcome="denied", detail="Telegram OIDC identity does not match canonical Bot identity")
            return "failed", None
        same_provider = conn.execute(
            "SELECT subject_hash FROM web_external_identities WHERE account_id=? AND provider=?",
            (account["id"], provider),
        ).fetchone()
        if same_provider:
            outcome = "already-linked" if hmac.compare_digest(str(same_provider[0]), subject_hash) else "failed"
            if outcome == "already-linked" and verified_contact_email and hmac.compare_digest(
                str(account.get("email") or "").strip().lower(),
                verified_contact_email,
            ):
                _store_oauth_verified_contact(
                    conn,
                    account_id=account["id"],
                    provider=provider,
                    email=verified_contact_email,
                    now=utc_now(),
                )
            _record_audit(conn, account_id=account["id"], canonical_user_id=account["canonical_user_id"], action="oauth.link", request_id=_request_id(request), target=provider, outcome="denied" if outcome == "failed" else "ok", detail="provider already linked" if outcome == "already-linked" else "different provider identity already linked")
            return outcome, None
        existing = conn.execute(
            "SELECT account_id FROM web_external_identities WHERE provider=? AND subject_hash=?",
            (provider, subject_hash),
        ).fetchone()
        if existing:
            _record_audit(conn, account_id=account["id"], canonical_user_id=account["canonical_user_id"], action="oauth.link", request_id=_request_id(request), target=provider, outcome="denied", detail="identity linked to another account")
            return "failed", None
        now = utc_now()
        conn.execute(
            """INSERT INTO web_external_identities (provider, subject_hash, account_id, created_at, last_login_at)
            VALUES (?, ?, ?, ?, ?)""",
            (provider, subject_hash, account["id"], now, now),
        )
        # Explicit linking proves control of the signed Web account, not
        # ownership of every contact a provider happens to return. Only mark
        # a contact verified when it exactly equals the account's existing
        # login address; never replace it and never merge another account.
        if verified_contact_email and hmac.compare_digest(
            str(account.get("email") or "").strip().lower(),
            verified_contact_email,
        ):
            _store_oauth_verified_contact(
                conn,
                account_id=account["id"],
                provider=provider,
                email=verified_contact_email,
                now=now,
            )
        replacement = _rotate_account_sessions(conn, account["id"], now=now)
        _record_audit(conn, account_id=account["id"], canonical_user_id=account["canonical_user_id"], action="oauth.link", request_id=_request_id(request), target=provider)
    return "linked", replacement


def _oauth_bound_link_account(state_data: dict) -> dict | None:
    """Validate the session that minted a cross-site OAuth link state.

    Apple returns to the callback by cross-site form POST, where the normal
    Lax session cookie is intentionally absent.  The dedicated short-lived
    state/link cookies plus this live-session lookup preserve the same account
    binding without weakening the main session cookie policy.
    """
    account_id = str(state_data.get("account_id") or "")
    session_id = str(state_data.get("initiating_session_id") or "")
    if not account_id or not session_id:
        return None
    with transaction() as conn:
        row = conn.execute(
            """SELECT a.id, a.email, a.display_name, a.canonical_user_id, a.role_cache, a.is_active,
                      a.password_login_enabled, p.locale, p.timezone, p.avatar_style, s.expires_at
               FROM web_sessions s JOIN web_accounts a ON a.id=s.account_id
               LEFT JOIN web_account_profiles p ON p.account_id=a.id
               WHERE s.id=? AND s.account_id=? AND s.revoked_at IS NULL""",
            (session_id, account_id),
        ).fetchone()
        if not row or not row[5] or _as_time(row[10]) <= _now():
            return None
        conn.execute("UPDATE web_sessions SET last_seen_at=? WHERE id=?", (utc_now(), session_id))
    return _oauth_account_from_row(row[:10])


@router.post("/register")
async def register(payload: RegisterRequest, request: Request, response: Response):
    email = payload.email.strip().lower()
    # HMAC-derived OAuth collision aliases are Web-internal identifiers, not
    # addresses a customer may reserve for email/password sign-in.
    if not EMAIL_PATTERN.fullmatch(email) or _is_oauth_only_email(email):
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
        "Nếu email chưa có tài khoản, yêu cầu đăng ký đã được tiếp nhận. Hãy đăng nhập để tiếp tục; sau đó bạn có thể xác minh mailbox từ Bảo mật tài khoản khi adapter email được cấu hình.",
        status_name="awaiting_confirm",
    )


@router.post("/login")
async def login(payload: LoginRequest, request: Request, response: Response):
    ensure_copyfast_schema()
    email = payload.email.strip().lower()
    internal_oauth_alias = _is_oauth_only_email(email)
    with transaction() as conn:
        row = conn.execute(
            """SELECT a.id, a.email, a.password_hash, a.display_name, a.canonical_user_id, a.role_cache, a.is_active, a.password_login_enabled,
                      p.locale, p.timezone, p.avatar_style
               FROM web_accounts a LEFT JOIN web_account_profiles p ON p.account_id=a.id
               WHERE a.email=?""",
            (email,),
        ).fetchone()
        password_hash = row[2] if row and row[6] and row[7] and not internal_oauth_alias else _DUMMY_PASSWORD_HASH
        password_valid = _verify_password(payload.password, password_hash)
        if not row or not row[6] or not row[7] or internal_oauth_alias or not password_valid:
            _record_audit(conn, account_id=row[0] if row else None, canonical_user_id=None, action="auth.login", request_id=_request_id(request), outcome="denied")
            return envelope(False, "Email hoặc mật khẩu không đúng", status_name="failed", error_code="LOGIN_DENIED")
        # A Web-native TOTP factor is deliberately enforced after the
        # constant-work password check and before any signed session exists.
        # The browser receives only one opaque, short-lived challenge; it
        # never sees an account id, factor id, secret or recovery-code hash.
        # If an active factor exists while its runtime is paused or invalid,
        # fail closed rather than silently bypassing second-factor protection.
        from copyfast_mfa import (
            active_totp_factor_exists,
            create_password_login_challenge,
            totp_mfa_runtime_available,
        )
        if active_totp_factor_exists(conn, account_id=str(row[0])):
            if not totp_mfa_runtime_available():
                _record_audit(
                    conn,
                    account_id=row[0],
                    canonical_user_id=row[4],
                    action="auth.login",
                    request_id=_request_id(request),
                    outcome="guarded",
                )
                return envelope(
                    False,
                    "Xác thực hai bước đang tạm không khả dụng. Không có phiên nào được tạo.",
                    status_name="guarded",
                    error_code="WEB_TOTP_MFA_UNAVAILABLE",
                )
            try:
                mfa_challenge = create_password_login_challenge(conn, account_id=str(row[0]))
            except RuntimeError:
                _record_audit(
                    conn,
                    account_id=row[0],
                    canonical_user_id=row[4],
                    action="auth.login",
                    request_id=_request_id(request),
                    outcome="guarded",
                )
                return envelope(
                    False,
                    "Xác thực hai bước đang tạm không khả dụng. Không có phiên nào được tạo.",
                    status_name="guarded",
                    error_code="WEB_TOTP_MFA_UNAVAILABLE",
                )
            _record_audit(
                conn,
                account_id=row[0],
                canonical_user_id=row[4],
                action="auth.mfa_login_challenge",
                request_id=_request_id(request),
                outcome="ok",
            )
            return envelope(
                True,
                "Mật khẩu đã được xác minh. Nhập mã xác thực hai bước để hoàn tất đăng nhập.",
                data=mfa_challenge,
                status_name="awaiting_confirm",
            )
        account = {
            "id": row[0], "email": row[1], "display_name": row[3] or "",
            "canonical_user_id": row[4], "role": row[5] or "user",
            "password_login_enabled": bool(row[7]),
            "locale": normalize_interface_locale(row[8]), "timezone": row[9] or "Asia/Ho_Chi_Minh", "avatar_style": row[10] or "gradient",
        }
        _record_audit(conn, account_id=row[0], canonical_user_id=row[4], action="auth.login", request_id=_request_id(request))
    session = _create_session(response, account["id"])
    return envelope(True, "Đăng nhập thành công", data={"account": browser_account_payload(account), **session})


@router.post("/logout")
async def logout(request: Request, response: Response, account: dict = Depends(require_csrf)):
    session_id = _parse_session_cookie(request.cookies.get(_cookie_name(SESSION_COOKIE)))
    with transaction() as conn:
        conn.execute("UPDATE web_sessions SET revoked_at=? WHERE id=?", (utc_now(), session_id))
        _record_audit(conn, account_id=account["id"], canonical_user_id=account["canonical_user_id"], action="auth.logout", request_id=_request_id(request))
    response.delete_cookie(_cookie_name(SESSION_COOKIE), path="/", secure=_cookie_secure(), httponly=True, samesite="lax")
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


@router.get("/security/sessions")
async def security_sessions(request: Request, account: dict = Depends(require_account)):
    """List at most twenty live owner sessions without exposing identifiers.

    The portal receives an HMAC action reference plus timestamps only.  It
    never receives the database session ID, signed cookie, CSRF token, IP or
    user-agent, so this view cannot become a secondary credential inventory.
    """

    session = current_session(request)
    now = utc_now()
    with read_transaction() as conn:
        rows = conn.execute(
            """SELECT id, created_at, last_seen_at, expires_at
               FROM web_sessions
               WHERE account_id=? AND revoked_at IS NULL AND expires_at>?
               ORDER BY last_seen_at DESC, id DESC
               LIMIT 20""",
            (account["id"], now),
        ).fetchall()
    sessions = [
        {
            "session_ref": _security_session_reference(str(row[0])),
            "current": hmac.compare_digest(str(row[0]), str(session["session_id"])),
            "created_at": str(row[1]),
            "last_seen_at": str(row[2]),
            "expires_at": str(row[3]),
        }
        for row in rows
    ]
    return envelope(
        True,
        "Đã tải các phiên đăng nhập đang hoạt động.",
        data={"sessions": sessions},
        status_name="read_only",
    )


@router.post("/security/sessions/revoke")
async def revoke_security_session(
    payload: SessionRevokeRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Revoke one non-current session selected by an opaque owner handle."""

    current = current_session(request)
    if current["account"]["id"] != account["id"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập không còn hợp lệ")
    actor_session_id = str(current["session_id"])
    reference = payload.session_ref.strip().lower()
    revoked = False
    stale_actor = False
    with transaction() as conn:
        now = utc_now()
        if not _session_is_active_for_account(
            conn,
            session_id=actor_session_id,
            account_id=account["id"],
            now=now,
        ):
            stale_actor = True
            _record_audit(
                conn,
                account_id=account["id"],
                canonical_user_id=None,
                action="auth.security_session_revoke",
                request_id=_request_id(request),
                outcome="denied",
                detail="initiating signed session is no longer active",
            )
        else:
            # Session references are generated only by the capped list endpoint.
            # Querying the same bounded, owner-scoped set prevents an unbounded
            # HMAC comparison loop and makes a foreign reference indistinguishable
            # from an expired or malformed local reference.
            if SESSION_REFERENCE_PATTERN.fullmatch(reference):
                rows = conn.execute(
                    """SELECT id FROM web_sessions
                       WHERE account_id=? AND revoked_at IS NULL AND expires_at>?
                       ORDER BY last_seen_at DESC, id DESC
                       LIMIT 20""",
                    (account["id"], now),
                ).fetchall()
                for row in rows:
                    candidate_id = str(row[0])
                    if hmac.compare_digest(reference, _security_session_reference(candidate_id)):
                        if not hmac.compare_digest(candidate_id, actor_session_id):
                            changed = conn.execute(
                                """UPDATE web_sessions SET revoked_at=?
                                   WHERE id=? AND account_id=? AND revoked_at IS NULL AND expires_at>?""",
                                (now, candidate_id, account["id"], now),
                            )
                            revoked = changed.rowcount == 1
                        break
            _record_audit(
                conn,
                account_id=account["id"],
                canonical_user_id=None,
                action="auth.security_session_revoke",
                request_id=_request_id(request),
                outcome="ok" if revoked else "noop",
            )
    if stale_actor:
        return JSONResponse(
            envelope(
                False,
                "Phiên đăng nhập không còn hợp lệ. Hãy đăng nhập lại trước khi quản lý phiên.",
                status_name="guarded",
                error_code="SECURITY_SESSION_STALE",
            ),
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    return envelope(
        True,
        "Đã cập nhật trạng thái phiên đăng nhập.",
        data={"revoked": revoked},
        status_name="completed",
    )


@router.post("/security/sessions/revoke-others")
async def revoke_other_security_sessions(
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Idempotently revoke every other active signed session for this owner."""

    current = current_session(request)
    if current["account"]["id"] != account["id"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập không còn hợp lệ")
    actor_session_id = str(current["session_id"])
    stale_actor = False
    revoked_count = 0
    with transaction() as conn:
        now = utc_now()
        if not _session_is_active_for_account(
            conn,
            session_id=actor_session_id,
            account_id=account["id"],
            now=now,
        ):
            stale_actor = True
            _record_audit(
                conn,
                account_id=account["id"],
                canonical_user_id=None,
                action="auth.security_sessions_revoke_others",
                request_id=_request_id(request),
                outcome="denied",
                detail="initiating signed session is no longer active",
            )
        else:
            changed = conn.execute(
                """UPDATE web_sessions SET revoked_at=?
                   WHERE account_id=? AND id<>? AND revoked_at IS NULL AND expires_at>?""",
                (now, account["id"], actor_session_id, now),
            )
            revoked_count = max(0, int(changed.rowcount))
            _record_audit(
                conn,
                account_id=account["id"],
                canonical_user_id=None,
                action="auth.security_sessions_revoke_others",
                request_id=_request_id(request),
                outcome="ok" if revoked_count else "noop",
            )
    if stale_actor:
        return JSONResponse(
            envelope(
                False,
                "Phiên đăng nhập không còn hợp lệ. Hãy đăng nhập lại trước khi quản lý phiên.",
                status_name="guarded",
                error_code="SECURITY_SESSION_STALE",
            ),
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    return envelope(
        True,
        "Đã thu hồi các phiên đăng nhập khác.",
        data={"revoked_count": revoked_count},
        status_name="completed",
    )


@router.post("/security/password")
async def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    response: Response,
    account: dict = Depends(require_csrf),
):
    """Change a Web password and rotate every previously signed session."""

    policy_error = _password_change_policy_error(payload.new_password)
    if policy_error:
        return envelope(False, policy_error, status_name="failed", error_code="PASSWORD_POLICY_INVALID")
    # Both values are browser-supplied. This policy check is not a comparison
    # with a stored secret, so Unicode-safe equality avoids `compare_digest`'s
    # non-ASCII string TypeError; `_verify_password` remains constant-time.
    if payload.current_password == payload.new_password:
        return envelope(
            False,
            "Mật khẩu mới cần khác mật khẩu hiện tại.",
            status_name="failed",
            error_code="PASSWORD_POLICY_INVALID",
        )

    # CSRF proves the actor at request entry. Preserve the signed-session ID
    # and verify it again while the password write lock is held: another
    # factor/password action may rotate or revoke this session while the
    # request is waiting for SQLite. Do not let that stale request mint the
    # replacement session for a new password.
    actor_session = current_session(request)
    if actor_session["account"]["id"] != account["id"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập không còn hợp lệ")
    actor_session_id = str(actor_session["session_id"])
    replacement = None
    stale_actor = False
    with transaction() as conn:
        now = utc_now()
        if not _session_is_active_for_account(
            conn,
            session_id=actor_session_id,
            account_id=account["id"],
            now=now,
        ):
            stale_actor = True
            _record_audit(
                conn,
                account_id=account["id"],
                canonical_user_id=None,
                action="auth.security_password_change",
                request_id=_request_id(request),
                outcome="denied",
                detail="initiating signed session is no longer active",
            )
        else:
            row = conn.execute(
                """SELECT email, password_hash, password_login_enabled, is_active
                   FROM web_accounts WHERE id=?""",
                (account["id"],),
            ).fetchone()
            password_available = bool(
                row
                and bool(row[2])
                and bool(row[3])
                and password_login_factor_available(str(row[0]), bool(row[2]))
            )
            stored_hash = str(row[1]) if row and password_available else _DUMMY_PASSWORD_HASH
            verified = _verify_password(payload.current_password, stored_hash)
            if not password_available or not verified:
                _record_audit(
                    conn,
                    account_id=account["id"],
                    canonical_user_id=None,
                    action="auth.security_password_change",
                    request_id=_request_id(request),
                    outcome="denied",
                )
                return envelope(
                    False,
                    "Không thể xác minh mật khẩu hiện tại.",
                    status_name="failed",
                    error_code="PASSWORD_CHANGE_DENIED",
                )
            conn.execute(
                "UPDATE web_accounts SET password_hash=?, updated_at=? WHERE id=?",
                (_password_hash(payload.new_password), now, account["id"]),
            )
            replacement = _rotate_account_sessions(conn, account["id"], now=now)
            _record_audit(
                conn,
                account_id=account["id"],
                canonical_user_id=None,
                action="auth.security_password_change",
                request_id=_request_id(request),
            )
    if stale_actor:
        return JSONResponse(
            envelope(
                False,
                "Phiên đăng nhập không còn hợp lệ. Hãy đăng nhập lại trước khi đổi mật khẩu.",
                status_name="guarded",
                error_code="SECURITY_SESSION_STALE",
            ),
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    # Never send the session ID to the browser response. The cookie is the
    # only transport for it, while the new CSRF token is intentionally part of
    # the signed-session bootstrap payload.
    _set_session_cookie(response, str(replacement["session_id"]))
    return envelope(
        True,
        "Đã đổi mật khẩu và thu hồi các phiên đăng nhập cũ.",
        data={"csrf_token": replacement["csrf_token"], "expires_at": replacement["expires_at"]},
        status_name="completed",
    )


@router.get("/security/login-methods")
async def security_login_methods(account: dict = Depends(require_account)):
    """Expose only factor availability needed by the Account Security UI."""

    with read_transaction() as conn:
        row = conn.execute(
            "SELECT email, password_login_enabled FROM web_accounts WHERE id=? AND is_active=1",
            (account["id"],),
        ).fetchone()
        methods = _security_login_methods(
            conn,
            account_id=account["id"],
            email=str(row[0]) if row else "",
            password_login_enabled=bool(row[1]) if row else False,
        )
    return envelope(
        True,
        "Đã tải phương thức đăng nhập.",
        data={"login_methods": methods},
        status_name="read_only",
    )


def _email_verification_challenge_id(value: str) -> str:
    """Normalize one UUID without accepting a database or path identifier."""

    candidate = str(value or "").strip().lower()
    try:
        parsed = uuid.UUID(candidate)
    except (TypeError, ValueError, AttributeError):
        return ""
    return candidate if str(parsed) == candidate else ""


def _email_verification_token(value: str) -> str:
    token = str(value or "").strip()
    return token if EMAIL_VERIFICATION_TOKEN_PATTERN.fullmatch(token) else ""


def _email_verification_html(*, completed: bool, can_confirm: bool, challenge_id: str = "", token: str = "") -> HTMLResponse:
    """Return a tiny no-store confirmation page with no external resources."""

    if completed:
        heading = "Email đã được xác minh"
        body = (
            "Quyền sở hữu mailbox đã được ghi nhận cho tài khoản Web phù hợp. "
            "Bạn có thể quay lại ứng dụng để tiếp tục."
        )
        action = '<p><a href="/account/security">Mở Bảo mật tài khoản</a></p>'
    elif can_confirm:
        heading = "Xác nhận quyền sở hữu email"
        body = (
            "Bạn sắp xác minh mailbox này cho một tài khoản TOAN AAS. "
            "Chỉ tiếp tục nếu chính bạn vừa yêu cầu thao tác này."
        )
        action = (
            '<form method="post" action="/api/v1/auth/email-verification/confirm">'
            f'<input type="hidden" name="c" value="{challenge_id}" autocomplete="off">'
            f'<input type="hidden" name="t" value="{token}" autocomplete="off">'
            '<input type="hidden" name="confirm" value="email-link" autocomplete="off">'
            '<button type="submit">Xác minh email</button>'
            "</form>"
        )
    else:
        heading = "Liên kết xác minh không còn hợp lệ"
        body = (
            "Liên kết có thể đã hết hạn, đã được dùng hoặc bị thay thế bởi một yêu cầu mới. "
            "Hãy đăng nhập và yêu cầu một liên kết mới nếu cần."
        )
        action = '<p><a href="/login">Mở đăng nhập</a></p>'
    response = HTMLResponse(
        "<!doctype html><html lang=\"vi\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{heading} | TOAN AAS</title>"
        "<style>body{margin:0;background:#07131c;color:#edf7fb;font:16px/1.55 system-ui,sans-serif}"
        "main{max-width:600px;margin:12vh auto;padding:32px;border:1px solid #244454;border-radius:18px;background:#0c202b}"
        "h1{font-size:28px;margin:0 0 12px}p{color:#b9ced8}button,a{display:inline-block;padding:10px 16px;border-radius:10px;"
        "border:0;background:#57d1c9;color:#062126;font-weight:700;text-decoration:none;cursor:pointer}</style>"
        "</head><body><main>"
        f"<h1>{heading}</h1><p>{body}</p>{action}"
        "</main></body></html>",
        status_code=200,
        headers={
            "Cache-Control": "no-store, private",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
        },
    )
    return response


async def _read_email_verification_confirmation(request: Request) -> tuple[str, str] | None:
    """Read the small manual confirmation form without accepting an upload."""

    declared = request.headers.get("content-length", "").strip()
    if declared:
        try:
            if int(declared) < 0 or int(declared) > 1024:
                return None
        except ValueError:
            return None
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/x-www-form-urlencoded":
        return None
    body = await request.body()
    if len(body) > 1024:
        return None
    try:
        parsed = parse_qs(
            body.decode("utf-8"),
            keep_blank_values=True,
            strict_parsing=True,
            max_num_fields=3,
        )
    except (UnicodeDecodeError, ValueError):
        return None
    if set(parsed) != {"c", "t", "confirm"} or any(len(values) != 1 for values in parsed.values()):
        return None
    if parsed["confirm"][0] != "email-link":
        return None
    challenge_id = _email_verification_challenge_id(parsed["c"][0])
    token = _email_verification_token(parsed["t"][0])
    return (challenge_id, token) if challenge_id and token else None


@router.post("/security/email-verification/start")
async def start_email_verification(
    payload: EmailVerificationStartRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Send one explicit, owner-scoped mailbox verification challenge.

    The delivery call is deliberately outside the SQLite transaction. A
    challenge remains unusable until the authenticated SMTP handoff succeeds,
    and both the token and recipient address remain absent from browser data.
    """

    if not payload.confirm:
        return envelope(
            False,
            "Hãy xác nhận trước khi yêu cầu gửi liên kết xác minh email.",
            status_name="guarded",
            error_code="EMAIL_VERIFICATION_CONFIRM_REQUIRED",
        )
    try:
        config = _email_verification_configuration()
    except RuntimeError:
        config = None
    if config is None:
        with transaction() as conn:
            _record_audit(
                conn,
                account_id=account["id"],
                canonical_user_id=None,
                action="auth.email_verification_start",
                request_id=_request_id(request),
                outcome="denied",
            )
        return JSONResponse(
            envelope(
                False,
                "Dịch vụ xác minh email chưa được cấu hình để gửi liên kết thật.",
                status_name="guarded",
                error_code="EMAIL_VERIFICATION_UNAVAILABLE",
            ),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    actor = current_session(request)
    if str(actor["account"]["id"]) != str(account["id"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập không còn hợp lệ")
    actor_session_id = str(actor["session_id"])
    now = utc_now()
    challenge_id = str(uuid.uuid4())
    token = secrets.token_urlsafe(EMAIL_VERIFICATION_TOKEN_BYTES)
    stale_actor = False
    rate_limited = False
    already_verified = False
    unavailable_factor = False
    with transaction() as conn:
        if not _session_is_active_for_account(
            conn,
            session_id=actor_session_id,
            account_id=account["id"],
            now=now,
        ):
            stale_actor = True
            outcome = "denied"
        else:
            row = conn.execute(
                """SELECT email, password_login_enabled
                   FROM web_accounts WHERE id=? AND is_active=1""",
                (account["id"],),
            ).fetchone()
            email = str(row[0]).strip().lower() if row else ""
            password_enabled = bool(row[1]) if row else False
            if not password_login_factor_available(email, password_enabled):
                unavailable_factor = True
                outcome = "denied"
            else:
                methods = _security_login_methods(
                    conn,
                    account_id=str(account["id"]),
                    email=email,
                    password_login_enabled=password_enabled,
                )
                already_verified = bool(methods["contact"]["verified"])
                if already_verified:
                    outcome = "noop"
                else:
                    recent = conn.execute(
                        """SELECT COUNT(*) FROM web_email_verification_challenges
                           WHERE account_id=? AND created_at>?""",
                        (account["id"], _email_verification_window_start()),
                    ).fetchone()
                    rate_limited = int(recent[0]) >= EMAIL_VERIFICATION_MAX_STARTS_PER_WINDOW
                    if rate_limited:
                        outcome = "denied"
                    else:
                        conn.execute(
                            """UPDATE web_email_verification_challenges
                               SET state='superseded', updated_at=?
                               WHERE account_id=? AND state IN ('prepared', 'sent')
                                 AND consumed_at IS NULL""",
                            (now, account["id"]),
                        )
                        conn.execute(
                            """INSERT INTO web_email_verification_challenges
                               (id, account_id, email, token_hash, state, expires_at, created_at, updated_at)
                               VALUES (?, ?, ?, ?, 'prepared', ?, ?, ?)""",
                            (
                                challenge_id,
                                account["id"],
                                email,
                                _email_verification_token_hash(challenge_id, token),
                                _email_verification_expiry(int(config["ttl_minutes"])),
                                now,
                                now,
                            ),
                        )
                        outcome = "prepared"
        _record_audit(
            conn,
            account_id=account["id"],
            canonical_user_id=None,
            action="auth.email_verification_start",
            request_id=_request_id(request),
            outcome=outcome,
        )
    if stale_actor:
        return JSONResponse(
            envelope(
                False,
                "Phiên đăng nhập không còn hợp lệ. Hãy đăng nhập lại trước khi yêu cầu xác minh email.",
                status_name="guarded",
                error_code="SECURITY_SESSION_STALE",
            ),
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    if unavailable_factor:
        return envelope(
            False,
            "Tài khoản này chưa có phương thức Email + mật khẩu có thể xác minh.",
            status_name="guarded",
            error_code="EMAIL_VERIFICATION_FACTOR_UNAVAILABLE",
        )
    if already_verified:
        return envelope(
            True,
            "Email của tài khoản này đã có bằng chứng xác minh.",
            data={"email_verification": {"started": False, "pending": False}},
            status_name="completed",
        )
    if rate_limited:
        return JSONResponse(
            envelope(
                False,
                "Bạn đã yêu cầu quá nhiều liên kết xác minh. Hãy thử lại sau ít phút.",
                status_name="guarded",
                error_code="EMAIL_VERIFICATION_RATE_LIMITED",
            ),
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(EMAIL_VERIFICATION_RATE_WINDOW_MINUTES * 60)},
        )
    try:
        await _send_email_verification_message(
            config,
            recipient=email,
            challenge_id=challenge_id,
            token=token,
        )
    except Exception:
        # SMTP libraries can expose host/user details in exception strings.
        # Never return or persist those values. The stale challenge stays
        # unusable, so a timeout cannot become an unearned mailbox proof.
        with transaction() as conn:
            conn.execute(
                """UPDATE web_email_verification_challenges
                   SET state='failed', updated_at=?
                   WHERE id=? AND account_id=? AND state='prepared'""",
                (utc_now(), challenge_id, account["id"]),
            )
            _record_audit(
                conn,
                account_id=account["id"],
                canonical_user_id=None,
                action="auth.email_verification_delivery",
                request_id=_request_id(request),
                outcome="failed",
            )
        return JSONResponse(
            envelope(
                False,
                "Chưa thể gửi liên kết xác minh. Không có email nào được xem là đã xác minh.",
                status_name="guarded",
                error_code="EMAIL_VERIFICATION_DELIVERY_FAILED",
            ),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    marked_sent = False
    with transaction() as conn:
        changed = conn.execute(
            """UPDATE web_email_verification_challenges
               SET state='sent', sent_at=?, updated_at=?
               WHERE id=? AND account_id=? AND state='prepared'""",
            (utc_now(), utc_now(), challenge_id, account["id"]),
        )
        marked_sent = changed.rowcount == 1
        _record_audit(
            conn,
            account_id=account["id"],
            canonical_user_id=None,
            action="auth.email_verification_delivery",
            request_id=_request_id(request),
            outcome="ok" if marked_sent else "superseded",
        )
    if not marked_sent:
        return envelope(
            False,
            "Yêu cầu xác minh đã được thay thế bởi một yêu cầu mới hơn. Hãy dùng liên kết mới nhất.",
            status_name="guarded",
            error_code="EMAIL_VERIFICATION_SUPERSEDED",
        )
    return envelope(
        True,
        "Đã gửi liên kết xác minh. Hãy mở email và tự xác nhận trước khi liên kết hết hạn.",
        data={
            "email_verification": {
                "started": True,
                "pending": True,
                "expires_in_minutes": int(config["ttl_minutes"]),
            }
        },
        status_name="awaiting_confirm",
    )


@router.get("/email-verification/confirm", response_class=HTMLResponse)
async def email_verification_confirmation_page(request: Request):
    """Render a manual confirmation page; a link preview cannot consume proof."""

    challenge_id = _email_verification_challenge_id(request.query_params.get("c", ""))
    token = _email_verification_token(request.query_params.get("t", ""))
    return _email_verification_html(
        completed=False,
        can_confirm=bool(challenge_id and token),
        challenge_id=challenge_id,
        token=token,
    )


@router.post("/email-verification/confirm", response_class=HTMLResponse)
async def confirm_email_verification(request: Request):
    """Consume a one-time mailbox proof only after a user submits the page."""

    parsed = await _read_email_verification_confirmation(request)
    if parsed is None:
        return _email_verification_html(completed=False, can_confirm=False)
    challenge_id, token = parsed
    now = utc_now()
    completed = False
    with transaction() as conn:
        row = conn.execute(
            """SELECT account_id, email, token_hash, state, expires_at
               FROM web_email_verification_challenges WHERE id=?""",
            (challenge_id,),
        ).fetchone()
        try:
            expires_active = bool(row and _as_time(str(row[4])) > _now())
        except (TypeError, ValueError):
            expires_active = False
        valid = bool(
            row
            and str(row[3]) == "sent"
            and expires_active
            and hmac.compare_digest(
                str(row[2]),
                _email_verification_token_hash(challenge_id, token),
            )
        )
        if valid:
            account_id = str(row[0])
            email = str(row[1]).strip().lower()
            account_row = conn.execute(
                """SELECT email, password_login_enabled, is_active
                   FROM web_accounts WHERE id=?""",
                (account_id,),
            ).fetchone()
            account_matches = bool(
                account_row
                and bool(account_row[2])
                and password_login_factor_available(str(account_row[0]), bool(account_row[1]))
                and str(account_row[0]).strip().lower() == email
            )
            if account_matches:
                conn.execute(
                    """INSERT INTO web_account_email_contacts
                       (account_id, email, verification_method, verified_at, created_at, updated_at)
                       VALUES (?, ?, 'email_link', ?, ?, ?)
                       ON CONFLICT(account_id) DO UPDATE SET
                           email=excluded.email,
                           verification_method=excluded.verification_method,
                           verified_at=excluded.verified_at,
                           updated_at=excluded.updated_at""",
                    (account_id, email, now, now, now),
                )
                consumed = conn.execute(
                    """UPDATE web_email_verification_challenges
                       SET state='consumed', consumed_at=?, updated_at=?
                       WHERE id=? AND state='sent'""",
                    (now, now, challenge_id),
                )
                completed = consumed.rowcount == 1
                if completed:
                    conn.execute(
                        """UPDATE web_email_verification_challenges
                           SET state='superseded', updated_at=?
                           WHERE account_id=? AND id<>? AND state IN ('prepared', 'sent')""",
                        (now, account_id, challenge_id),
                    )
                    _record_audit(
                        conn,
                        account_id=account_id,
                        canonical_user_id=None,
                        action="auth.email_verification_confirm",
                        request_id=_request_id(request),
                        outcome="ok",
                    )
        if not completed:
            _record_audit(
                conn,
                account_id=str(row[0]) if row else None,
                canonical_user_id=None,
                action="auth.email_verification_confirm",
                request_id=_request_id(request),
                outcome="denied",
            )
    return _email_verification_html(completed=completed, can_confirm=False)


def _password_recovery_challenge_id(value: str) -> str:
    """Normalize a recovery UUID without accepting an arbitrary database key."""

    return _email_verification_challenge_id(value)


def _password_recovery_token(value: str) -> str:
    """Keep recovery proof validation explicit even though its token shape matches email links."""

    return _email_verification_token(value)


def _password_recovery_html(
    *,
    completed: bool,
    can_confirm: bool,
    challenge_id: str = "",
    token: str = "",
    issue: str = "",
) -> HTMLResponse:
    """Render a no-store, scanner-safe password recovery confirmation page."""

    if completed:
        heading = "Mật khẩu đã được đặt lại"
        body = (
            "Mật khẩu mới đã được lưu và các phiên Web đang đăng nhập đã được thu hồi. "
            "Hãy đăng nhập lại bằng mật khẩu mới."
        )
        action = '<p><a href="/login">Mở đăng nhập</a></p>'
    elif can_confirm:
        heading = "Chọn mật khẩu mới"
        body = (
            "Chỉ tiếp tục nếu bạn vừa yêu cầu đặt lại mật khẩu. Xác nhận này chỉ "
            "dùng liên kết một lần và không tự đăng nhập bạn."
        )
        alert = (
            f'<p class="alert">{issue}</p>'
            if issue
            else ""
        )
        action = (
            f"{alert}"
            '<form method="post" action="/api/v1/auth/password-recovery/confirm">'
            f'<input type="hidden" name="c" value="{challenge_id}" autocomplete="off">'
            f'<input type="hidden" name="t" value="{token}" autocomplete="off">'
            '<input type="hidden" name="confirm" value="password-recovery" autocomplete="off">'
            '<label>Mật khẩu mới'
            '<input type="password" name="password" minlength="12" maxlength="256" '
            'autocomplete="new-password" required></label>'
            '<label>Xác nhận mật khẩu mới'
            '<input type="password" name="confirm_password" minlength="12" maxlength="256" '
            'autocomplete="new-password" required></label>'
            '<button type="submit">Đặt lại mật khẩu</button>'
            "</form>"
        )
    else:
        heading = "Liên kết đặt lại mật khẩu không còn hợp lệ"
        body = (
            "Liên kết có thể đã hết hạn, đã được dùng hoặc bị thay thế bởi một yêu cầu mới. "
            "Bạn có thể gửi lại yêu cầu từ trang đăng nhập nếu cần."
        )
        action = '<p><a href="/password-recovery">Yêu cầu liên kết mới</a></p>'
    response = HTMLResponse(
        "<!doctype html><html lang=\"vi\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{heading} | TOAN AAS</title>"
        "<style>body{margin:0;background:#07131c;color:#edf7fb;font:16px/1.55 system-ui,sans-serif}"
        "main{max-width:600px;margin:12vh auto;padding:32px;border:1px solid #244454;border-radius:18px;background:#0c202b}"
        "h1{font-size:28px;margin:0 0 12px}p,label{color:#b9ced8}label{display:block;margin:14px 0 8px;font-weight:700}"
        "input{box-sizing:border-box;width:100%;margin-top:6px;padding:10px;border:1px solid #356070;border-radius:10px;background:#07131c;color:#edf7fb}"
        "button,a{display:inline-block;margin-top:18px;padding:10px 16px;border-radius:10px;border:0;background:#57d1c9;color:#062126;font-weight:700;text-decoration:none;cursor:pointer}"
        ".alert{padding:10px 12px;border-radius:10px;background:#45262b;color:#ffdadd}</style>"
        "</head><body><main>"
        f"<h1>{heading}</h1><p>{body}</p>{action}"
        "</main></body></html>",
        status_code=200,
        headers={
            "Cache-Control": "no-store, private",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
        },
    )
    return response


async def _read_password_recovery_confirmation(request: Request) -> tuple[str, str, str, str] | None:
    """Read the bounded HTML form without accepting files or arbitrary fields."""

    declared = request.headers.get("content-length", "").strip()
    if declared:
        try:
            if int(declared) < 0 or int(declared) > PASSWORD_RECOVERY_CONFIRM_MAX_BODY_BYTES:
                return None
        except ValueError:
            return None
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/x-www-form-urlencoded":
        return None
    body = await request.body()
    if len(body) > PASSWORD_RECOVERY_CONFIRM_MAX_BODY_BYTES:
        return None
    try:
        parsed = parse_qs(
            body.decode("utf-8"),
            keep_blank_values=True,
            strict_parsing=True,
            max_num_fields=5,
        )
    except (UnicodeDecodeError, ValueError):
        return None
    if set(parsed) != {"c", "t", "confirm", "password", "confirm_password"} or any(
        len(values) != 1 for values in parsed.values()
    ):
        return None
    if parsed["confirm"][0] != "password-recovery":
        return None
    challenge_id = _password_recovery_challenge_id(parsed["c"][0])
    token = _password_recovery_token(parsed["t"][0])
    password = parsed["password"][0]
    confirmation = parsed["confirm_password"][0]
    if not challenge_id or not token:
        return None
    return challenge_id, token, password, confirmation


async def _deliver_password_recovery_challenge(
    *,
    config: dict,
    account_id: str,
    email: str,
    challenge_id: str,
    token: str,
    request_id: str,
) -> None:
    """Deliver a prepared recovery proof after the generic browser response."""

    ensure_copyfast_schema()
    with read_transaction() as conn:
        pending = conn.execute(
            """SELECT 1 FROM web_password_recovery_challenges
               WHERE id=? AND account_id=? AND state='prepared' AND expires_at>?""",
            (challenge_id, account_id, utc_now()),
        ).fetchone()
    if not pending:
        return
    try:
        await _send_password_recovery_message(
            config,
            recipient=email,
            challenge_id=challenge_id,
            token=token,
        )
    except Exception:
        # SMTP exceptions may contain private transport details. They are
        # intentionally neither returned to the browser nor stored in audit
        # text. A failed prepared record cannot ever reset a password.
        with transaction() as conn:
            changed = conn.execute(
                """UPDATE web_password_recovery_challenges
                   SET state='failed', updated_at=?
                   WHERE id=? AND account_id=? AND state='prepared'""",
                (utc_now(), challenge_id, account_id),
            )
            _record_audit(
                conn,
                account_id=account_id,
                canonical_user_id=None,
                action="auth.password_recovery_delivery",
                request_id=request_id,
                outcome="failed" if changed.rowcount == 1 else "superseded",
            )
        return
    with transaction() as conn:
        now = utc_now()
        changed = conn.execute(
            """UPDATE web_password_recovery_challenges
               SET state='sent', sent_at=?, updated_at=?
               WHERE id=? AND account_id=? AND state='prepared'""",
            (now, now, challenge_id, account_id),
        )
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=None,
            action="auth.password_recovery_delivery",
            request_id=request_id,
            outcome="ok" if changed.rowcount == 1 else "superseded",
        )


def _password_recovery_acknowledgement() -> dict:
    """Keep every public request response identical to prevent enumeration."""

    return envelope(
        True,
        "Nếu email thuộc một tài khoản Email + mật khẩu đang hoạt động, chúng tôi sẽ gửi liên kết đặt lại khi dịch vụ email được bật. Hãy kiểm tra mailbox của bạn.",
        data={"password_recovery": {"accepted": True}},
        status_name="awaiting_confirm",
    )


@router.post("/password-recovery/start")
async def start_password_recovery(
    payload: PasswordRecoveryStartRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Prepare a mailbox reset proof without revealing account or delivery state."""

    try:
        config = _password_recovery_configuration()
    except RuntimeError:
        # Enabled-but-invalid configuration is rejected during normal app
        # startup. Keep this route generic as an additional non-enumerating
        # fail-closed boundary for isolated router/test mounts.
        config = None
    email = payload.email.strip().lower()
    if config is None or not EMAIL_PATTERN.fullmatch(email) or _is_oauth_only_email(email) or _is_telegram_only_email(email):
        with transaction() as conn:
            _record_audit(
                conn,
                account_id=None,
                canonical_user_id=None,
                action="auth.password_recovery_start",
                request_id=_request_id(request),
                outcome="ignored",
            )
        return _password_recovery_acknowledgement()

    now = utc_now()
    challenge_id = str(uuid.uuid4())
    token = secrets.token_urlsafe(PASSWORD_RECOVERY_TOKEN_BYTES)
    queued = None
    with transaction() as conn:
        row = conn.execute(
            """SELECT id, email, password_login_enabled, is_active, canonical_user_id
               FROM web_accounts WHERE email=?""",
            (email,),
        ).fetchone()
        account_id = str(row[0]) if row else ""
        account_email = str(row[1]).strip().lower() if row else ""
        password_available = bool(
            row
            and bool(row[3])
            and password_login_factor_available(account_email, bool(row[2]))
        )
        outcome = "ignored"
        if password_available:
            recent = conn.execute(
                """SELECT COUNT(*) FROM web_password_recovery_challenges
                   WHERE account_id=? AND created_at>?""",
                (account_id, _password_recovery_window_start()),
            ).fetchone()
            if int(recent[0]) < PASSWORD_RECOVERY_MAX_STARTS_PER_WINDOW:
                conn.execute(
                    """UPDATE web_password_recovery_challenges
                       SET state='superseded', updated_at=?
                       WHERE account_id=? AND state IN ('prepared', 'sent')
                         AND consumed_at IS NULL""",
                    (now, account_id),
                )
                conn.execute(
                    """INSERT INTO web_password_recovery_challenges
                       (id, account_id, email, token_hash, state, expires_at, created_at, updated_at)
                       VALUES (?, ?, ?, ?, 'prepared', ?, ?, ?)""",
                    (
                        challenge_id,
                        account_id,
                        account_email,
                        _password_recovery_token_hash(challenge_id, token),
                        _password_recovery_expiry(int(config["ttl_minutes"])),
                        now,
                        now,
                    ),
                )
                queued = {
                    "account_id": account_id,
                    "email": account_email,
                    "challenge_id": challenge_id,
                    "token": token,
                }
                outcome = "queued"
            else:
                outcome = "rate_limited"
        _record_audit(
            conn,
            account_id=account_id or None,
            canonical_user_id=str(row[4]) if row and row[4] else None,
            action="auth.password_recovery_start",
            request_id=_request_id(request),
            outcome=outcome,
        )
    if queued:
        background_tasks.add_task(
            _deliver_password_recovery_challenge,
            config=config,
            account_id=queued["account_id"],
            email=queued["email"],
            challenge_id=queued["challenge_id"],
            token=queued["token"],
            request_id=_request_id(request),
        )
    return _password_recovery_acknowledgement()


@router.get("/password-recovery/confirm", response_class=HTMLResponse)
async def password_recovery_confirmation_page(request: Request):
    """Show a manual form; GET/link scanners cannot reset a password."""

    challenge_id = _password_recovery_challenge_id(request.query_params.get("c", ""))
    token = _password_recovery_token(request.query_params.get("t", ""))
    return _password_recovery_html(
        completed=False,
        can_confirm=bool(challenge_id and token),
        challenge_id=challenge_id,
        token=token,
    )


@router.post("/password-recovery/confirm", response_class=HTMLResponse)
async def confirm_password_recovery(request: Request):
    """Consume one mailbox proof, set a fresh password and revoke Web sessions."""

    parsed = await _read_password_recovery_confirmation(request)
    if parsed is None:
        return _password_recovery_html(completed=False, can_confirm=False)
    challenge_id, token, new_password, confirmation = parsed
    policy_error = _password_change_policy_error(new_password)
    if policy_error:
        return _password_recovery_html(
            completed=False,
            can_confirm=True,
            challenge_id=challenge_id,
            token=token,
            issue=policy_error,
        )
    if new_password != confirmation:
        return _password_recovery_html(
            completed=False,
            can_confirm=True,
            challenge_id=challenge_id,
            token=token,
            issue="Xác nhận mật khẩu mới chưa khớp.",
        )

    now = utc_now()
    completed = False
    retry_issue = ""
    with transaction() as conn:
        row = conn.execute(
            """SELECT account_id, email, token_hash, state, expires_at
               FROM web_password_recovery_challenges WHERE id=?""",
            (challenge_id,),
        ).fetchone()
        try:
            expires_active = bool(row and _as_time(str(row[4])) > _now())
        except (TypeError, ValueError):
            expires_active = False
        valid = bool(
            row
            and str(row[3]) == "sent"
            and expires_active
            and hmac.compare_digest(
                str(row[2]),
                _password_recovery_token_hash(challenge_id, token),
            )
        )
        if valid:
            account_id = str(row[0])
            email = str(row[1]).strip().lower()
            account_row = conn.execute(
                """SELECT email, password_hash, password_login_enabled, is_active, canonical_user_id
                   FROM web_accounts WHERE id=?""",
                (account_id,),
            ).fetchone()
            account_matches = bool(
                account_row
                and bool(account_row[3])
                and password_login_factor_available(str(account_row[0]), bool(account_row[2]))
                and str(account_row[0]).strip().lower() == email
            )
            stored_hash = str(account_row[1]) if account_matches else _DUMMY_PASSWORD_HASH
            if account_matches and _verify_password(new_password, stored_hash):
                retry_issue = "Mật khẩu mới cần khác mật khẩu hiện tại."
            elif account_matches:
                consumed = conn.execute(
                    """UPDATE web_password_recovery_challenges
                       SET state='consumed', consumed_at=?, updated_at=?
                       WHERE id=? AND account_id=? AND state='sent'""",
                    (now, now, challenge_id, account_id),
                )
                if consumed.rowcount == 1:
                    conn.execute(
                        "UPDATE web_accounts SET password_hash=?, updated_at=? WHERE id=?",
                        (_password_hash(new_password), now, account_id),
                    )
                    conn.execute(
                        "UPDATE web_sessions SET revoked_at=? WHERE account_id=? AND revoked_at IS NULL",
                        (now, account_id),
                    )
                    conn.execute(
                        """UPDATE web_password_recovery_challenges
                           SET state='superseded', updated_at=?
                           WHERE account_id=? AND id<>? AND state IN ('prepared', 'sent')""",
                        (now, account_id, challenge_id),
                    )
                    completed = True
                    _record_audit(
                        conn,
                        account_id=account_id,
                        canonical_user_id=str(account_row[4]) if account_row[4] else None,
                        action="auth.password_recovery_confirm",
                        request_id=_request_id(request),
                        outcome="ok",
                    )
        if not completed and not retry_issue:
            _record_audit(
                conn,
                account_id=str(row[0]) if row else None,
                canonical_user_id=None,
                action="auth.password_recovery_confirm",
                request_id=_request_id(request),
                outcome="denied",
            )
        elif retry_issue:
            _record_audit(
                conn,
                account_id=str(row[0]) if row else None,
                canonical_user_id=None,
                action="auth.password_recovery_confirm",
                request_id=_request_id(request),
                outcome="noop",
            )
    response = _password_recovery_html(
        completed=completed,
        can_confirm=bool(retry_issue),
        challenge_id=challenge_id if retry_issue else "",
        token=token if retry_issue else "",
        issue=retry_issue,
    )
    if completed:
        # A recovery never creates or rotates a session. Clear any stale cookie
        # in the browser that submitted the link after server-side revocation.
        response.delete_cookie(
            _cookie_name(SESSION_COOKIE),
            path="/",
            secure=_cookie_secure(),
            httponly=True,
            samesite="lax",
        )
    return response


@router.post("/security/oauth/{provider}/unlink")
async def unlink_security_oauth(
    provider: str,
    request: Request,
    response: Response,
    account: dict = Depends(require_csrf),
):
    """Detach one safe OAuth factor without allowing a customer lockout."""

    normalized_provider = provider.strip().lower()
    if normalized_provider not in OAUTH_PROVIDER_NAMES:
        with transaction() as conn:
            _record_audit(
                conn,
                account_id=account["id"],
                canonical_user_id=None,
                action="auth.security_oauth_unlink",
                request_id=_request_id(request),
                outcome="denied",
            )
        return envelope(
            False,
            "Phương thức đăng nhập không hợp lệ.",
            status_name="guarded",
            error_code="OAUTH_PROVIDER_INVALID",
        )
    if not _oauth_enabled(normalized_provider):
        with transaction() as conn:
            _record_audit(
                conn,
                account_id=account["id"],
                canonical_user_id=None,
                action="auth.security_oauth_unlink",
                request_id=_request_id(request),
                outcome="denied",
            )
        return envelope(
            False,
            "Phương thức này đang không khả dụng để quản lý trên Web.",
            status_name="guarded",
            error_code="OAUTH_PROVIDER_DISABLED",
        )
    # A Telegram-first Bot account has a canonical Bot identity outside this
    # OIDC table. Even with an extra OIDC proof, the UI/API must not present a
    # misleading "unlink Telegram" operation for that account type.
    if normalized_provider == "telegram" and _is_telegram_only_email(str(account.get("email") or "")):
        with transaction() as conn:
            _record_audit(
                conn,
                account_id=account["id"],
                canonical_user_id=None,
                action="auth.security_oauth_unlink",
                request_id=_request_id(request),
                outcome="denied",
            )
        return envelope(
            False,
            "Tài khoản Telegram-first không hỗ trợ gỡ liên kết Telegram tại đây.",
            status_name="guarded",
            error_code="TELEGRAM_UNLINK_NOT_AVAILABLE",
        )

    # The CSRF dependency proves the actor at request entry. Preserve its
    # signed-session id and verify it again *inside* the mutation transaction:
    # another security action may revoke/rotate it while this request waits
    # for SQLite's write lock.
    actor_session = current_session(request)
    if actor_session["account"]["id"] != account["id"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập không còn hợp lệ")
    actor_session_id = str(actor_session["session_id"])
    replacement = None
    guarded = False
    stale_actor = False
    now = utc_now()
    with transaction() as conn:
        if not _session_is_active_for_account(
            conn,
            session_id=actor_session_id,
            account_id=account["id"],
            now=now,
        ):
            stale_actor = True
            outcome = "denied"
        else:
            row = conn.execute(
                "SELECT email, password_login_enabled FROM web_accounts WHERE id=? AND is_active=1",
                (account["id"],),
            ).fetchone()
            methods = _security_login_methods(
                conn,
                account_id=account["id"],
                email=str(row[0]) if row else "",
                password_login_enabled=bool(row[1]) if row else False,
            )
            linked = {str(item["provider"]) for item in methods["oauth"] if item["linked"]}
            if normalized_provider not in linked:
                outcome = "noop"
            elif int(methods["usable_factor_count"]) <= 1:
                guarded = True
                outcome = "denied"
            else:
                conn.execute(
                    "DELETE FROM web_external_identities WHERE account_id=? AND provider=?",
                    (account["id"], normalized_provider),
                )
                # The contact table has at most one contact per account. Remove
                # it only when it belongs to the factor being detached; a contact
                # from another still-linked provider remains untouched.
                conn.execute(
                    "DELETE FROM web_account_oauth_contacts WHERE account_id=? AND provider=?",
                    (account["id"], normalized_provider),
                )
                replacement = _rotate_account_sessions(conn, account["id"], now=now)
                outcome = "ok"
        _record_audit(
            conn,
            account_id=account["id"],
            canonical_user_id=None,
            action="auth.security_oauth_unlink",
            request_id=_request_id(request),
            outcome=outcome,
        )
    if stale_actor:
        return JSONResponse(
            envelope(
                False,
                "Phiên đăng nhập không còn hợp lệ. Hãy đăng nhập lại trước khi thay đổi phương thức đăng nhập.",
                status_name="guarded",
                error_code="SECURITY_SESSION_STALE",
            ),
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    if guarded:
        return envelope(
            False,
            "Hãy giữ lại ít nhất một phương thức đăng nhập đang hoạt động.",
            status_name="guarded",
            error_code="SECURITY_LAST_LOGIN_FACTOR",
        )
    if replacement:
        _set_session_cookie(response, str(replacement["session_id"]))
    return envelope(
        True,
        "Đã cập nhật phương thức đăng nhập.",
        data=(
            {"unlinked": True, "csrf_token": replacement["csrf_token"], "expires_at": replacement["expires_at"]}
            if replacement
            else {"unlinked": False}
        ),
        status_name="completed",
    )


@router.post("/profile")
async def update_profile(payload: ProfileUpdateRequest, request: Request, account: dict = Depends(require_csrf)):
    """Update only Web-owned presentation defaults for the signed account."""
    display_name = payload.display_name.strip()
    locale = payload.locale.strip().lower()
    timezone_name = payload.timezone.strip()
    if any(ord(character) < 32 for character in display_name):
        return envelope(False, "Tên hiển thị có ký tự không hợp lệ.", status_name="failed", error_code="PROFILE_DISPLAY_NAME_INVALID")
    if locale not in INTERFACE_LOCALES:
        return envelope(False, "Ngôn ngữ hồ sơ chưa được hỗ trợ.", status_name="failed", error_code="PROFILE_LOCALE_INVALID")
    if timezone_name not in {"Asia/Ho_Chi_Minh", "UTC"}:
        return envelope(False, "Múi giờ hồ sơ chưa được hỗ trợ.", status_name="failed", error_code="PROFILE_TIMEZONE_INVALID")
    with transaction() as conn:
        now = utc_now()
        conn.execute(
            "UPDATE web_accounts SET display_name=?, updated_at=? WHERE id=?",
            (display_name, now, account["id"]),
        )
        conn.execute(
            """INSERT INTO web_account_profiles
            (account_id, locale, timezone, avatar_style, created_at, updated_at)
            VALUES (?, ?, ?, 'gradient', ?, ?)
            ON CONFLICT(account_id) DO UPDATE SET locale=excluded.locale, timezone=excluded.timezone, updated_at=excluded.updated_at""",
            (account["id"], locale, timezone_name, now, now),
        )
        _record_audit(conn, account_id=account["id"], canonical_user_id=account["canonical_user_id"], action="auth.profile_update", request_id=_request_id(request))
    updated = {
        **account,
        "display_name": display_name,
        "locale": locale,
        "timezone": timezone_name,
        "avatar_style": "gradient",
    }
    return envelope(True, "Đã cập nhật hồ sơ Web.", data={"account": browser_account_payload(updated)}, status_name="completed")


@router.post("/profile/interface-locale")
async def update_interface_locale(
    payload: InterfaceLocaleUpdateRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Persist one reviewed Web UI locale without touching other profile data.

    This is intentionally a local presentation preference. It never accepts
    a Bot language/callback, workflow language, identity, role, wallet,
    payment, provider or job field, and returns only the confirmed locale.
    """

    locale = payload.locale.lower()
    if locale not in INTERFACE_LOCALES:
        return envelope(
            False,
            "Ngôn ngữ giao diện chưa được hỗ trợ.",
            status_name="failed",
            error_code="PROFILE_LOCALE_INVALID",
        )
    with transaction() as conn:
        now = utc_now()
        # Existing profile values stay untouched. The insert path only covers
        # a legacy signed account that has no profile row yet.
        conn.execute(
            """INSERT INTO web_account_profiles
            (account_id, locale, timezone, avatar_style, created_at, updated_at)
            VALUES (?, ?, 'Asia/Ho_Chi_Minh', 'gradient', ?, ?)
            ON CONFLICT(account_id) DO UPDATE SET locale=excluded.locale, updated_at=excluded.updated_at""",
            (account["id"], locale, now, now),
        )
        _record_audit(
            conn,
            account_id=account["id"],
            canonical_user_id=account["canonical_user_id"],
            action="auth.interface_locale_update",
            request_id=_request_id(request),
        )
    return envelope(
        True,
        "Đã cập nhật ngôn ngữ giao diện.",
        data={"profile": {"locale": locale}},
        status_name="completed",
    )


@router.post("/telegram-account/upgrade")
async def upgrade_telegram_account(
    payload: TelegramAccountUpgradeRequest,
    request: Request,
    response: Response,
    account: dict = Depends(require_csrf),
):
    """Attach email/password to the current Bot-proven Telegram-first account.

    This is an explicit account upgrade, never an automatic merge. The signed
    session and CSRF check prove control of the existing Web account, while
    the unique email constraint prevents a Telegram identity from silently
    taking over a separate email/OAuth account.
    """
    email = payload.email.strip().lower()
    if not EMAIL_PATTERN.fullmatch(email) or _is_oauth_only_email(email):
        return envelope(False, "Email không hợp lệ.", status_name="failed", error_code="INVALID_EMAIL")
    if not _is_telegram_only_email(str(account.get("email") or "")) or bool(account.get("password_login_enabled")):
        return envelope(
            False,
            "Tài khoản hiện tại đã có phương thức đăng nhập Email hoặc không phải hồ sơ Telegram-first cần nâng cấp.",
            status_name="guarded",
            error_code="TELEGRAM_ACCOUNT_UPGRADE_NOT_NEEDED",
        )

    # This is a security-factor mutation: retain the signed session that
    # passed CSRF at request entry and recheck it under the write transaction.
    # Otherwise a browser session revoked by another security action while it
    # waits on SQLite could still attach a password and receive a replacement
    # cookie for the Telegram-first account.
    actor_session = current_session(request)
    if actor_session["account"]["id"] != account["id"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập không còn hợp lệ")
    actor_session_id = str(actor_session["session_id"])
    replacement = None
    stale_actor = False
    with transaction() as conn:
        now = utc_now()
        if not _session_is_active_for_account(
            conn,
            session_id=actor_session_id,
            account_id=account["id"],
            now=now,
        ):
            stale_actor = True
            _record_audit(
                conn,
                account_id=account["id"],
                canonical_user_id=account["canonical_user_id"],
                action="auth.telegram_account_upgrade",
                request_id=_request_id(request),
                outcome="denied",
                detail="initiating signed session is no longer active",
            )
        else:
            existing = conn.execute("SELECT id FROM web_accounts WHERE email=? AND id<>?", (email, account["id"])).fetchone()
            if existing:
                # Do not disclose whether an address belongs to a password or an
                # OAuth account. Account consolidation needs an explicit recovery
                # process, not an identity transfer from this browser request.
                _record_audit(
                    conn,
                    account_id=account["id"],
                    canonical_user_id=account["canonical_user_id"],
                    action="auth.telegram_account_upgrade",
                    request_id=_request_id(request),
                    outcome="denied",
                    detail="requested email belongs to another web account",
                )
                return envelope(
                    False,
                    "Email này chưa thể dùng để nâng cấp tài khoản. Hãy dùng email khác hoặc liên hệ hỗ trợ để xử lý hai tài khoản riêng biệt.",
                    status_name="guarded",
                    error_code="EMAIL_UPGRADE_UNAVAILABLE",
                )
            result = conn.execute(
                """UPDATE web_accounts
                   SET email=?, password_hash=?, password_login_enabled=1, updated_at=?
                   WHERE id=? AND password_login_enabled=0""",
                (email, _password_hash(payload.password), now, account["id"]),
            )
            if result.rowcount != 1:
                _record_audit(
                    conn,
                    account_id=account["id"],
                    canonical_user_id=account["canonical_user_id"],
                    action="auth.telegram_account_upgrade",
                    request_id=_request_id(request),
                    outcome="denied",
                    detail="account changed while upgrade was submitted",
                )
                return envelope(False, "Tài khoản vừa thay đổi. Hãy làm mới trang rồi thử lại.", status_name="guarded", error_code="TELEGRAM_ACCOUNT_UPGRADE_CONFLICT")
            replacement = _rotate_account_sessions(conn, account["id"], now=now)
            _record_audit(
                conn,
                account_id=account["id"],
                canonical_user_id=account["canonical_user_id"],
                action="auth.telegram_account_upgrade",
                request_id=_request_id(request),
            )
    if stale_actor:
        return JSONResponse(
            envelope(
                False,
                "Phiên đăng nhập không còn hợp lệ. Hãy đăng nhập lại trước khi thêm phương thức Email.",
                status_name="guarded",
                error_code="SECURITY_SESSION_STALE",
            ),
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    _set_session_cookie(response, str(replacement["session_id"]))
    updated = {**account, "email": email, "password_login_enabled": True}
    return envelope(
        True,
        "Đã thêm đăng nhập Email + mật khẩu cho tài khoản Telegram hiện tại.",
        data={
            "account": browser_account_payload(updated),
            "csrf_token": replacement["csrf_token"],
            "expires_at": replacement["expires_at"],
        },
        status_name="completed",
    )


@router.get("/providers")
async def oauth_providers():
    """Expose only provider availability, never OAuth client configuration."""
    return envelope(True, "Trạng thái phương thức đăng nhập", data={"providers": oauth_provider_status()})


@router.get("/telegram/connection/status")
async def telegram_connection_status():
    """Expose safe setup booleans for the Bot→Web identity handoff.

    This deliberately cannot inspect Bot secrets or claim the remote Bot is
    online. It tells the portal whether this Web deployment can issue a valid
    deep link and accept the signed callback the existing Bot adapter sends.
    """
    connection = _telegram_connection_configuration(include_observation=True)
    ready = bool(connection["ready"])
    observed = bool(connection.get("bot_callback_observed"))
    if not ready:
        message = "Web đang chờ cấu hình cầu nối Telegram an toàn."
    elif observed:
        message = "Web đã xác minh ít nhất một callback Telegram hợp lệ từ Bot."
    else:
        message = "Web đã sẵn sàng tạo deep link và nhận callback Telegram; đang chờ Bot xác minh mã lần đầu."
    return envelope(
        ready,
        message,
        # `ready` is deliberately duplicated inside the safe status payload.
        # The Portal reads the data object after envelope normalization and
        # must use this three-part release gate rather than reconstructing it
        # from only the Web-side credentials.
        data=connection,
        status_name="completed" if ready else "guarded",
        error_code=None if ready else "TELEGRAM_LINK_CONFIGURATION_REQUIRED",
    )


@router.post("/oauth/{provider}/link/start")
async def start_oauth_link(provider: str, request: Request, response: Response, account: dict = Depends(require_csrf)):
    provider = provider.strip().lower()
    if not _oauth_enabled(provider):
        return envelope(False, "Phương thức đăng nhập này chưa được cấu hình.", status_name="guarded", error_code="OAUTH_PROVIDER_DISABLED")
    session = current_session(request)
    ticket = secrets.token_urlsafe(24)
    _set_oauth_link_cookie(response, provider, session["session_id"], ticket)
    with transaction() as conn:
        _record_audit(conn, account_id=account["id"], canonical_user_id=account["canonical_user_id"], action="oauth.link_start", request_id=_request_id(request), target=provider)
    return envelope(
        True,
        "Sắp chuyển sang nhà cung cấp để liên kết đăng nhập.",
        data={"start_path": f"/api/v1/auth/oauth/{provider}/start?link=1"},
        status_name="awaiting_confirm",
    )


@router.get("/oauth/{provider}/start")
async def start_oauth(provider: str, request: Request):
    provider = provider.strip().lower()
    if not _oauth_enabled(provider):
        return _oauth_redirect("unavailable")
    try:
        purpose = "signin"
        account_id: str | None = None
        initiating_session_id: str | None = None
        if request.query_params.get("link") == "1":
            session = current_session(request)
            link_cookie = _parse_oauth_link_cookie(request.cookies.get(_cookie_name(OAUTH_LINK_COOKIE)))
            if not link_cookie or link_cookie[0] != provider or link_cookie[1] != session["session_id"]:
                response = _oauth_redirect("session", path="/account")
                _clear_oauth_link_cookie(response)
                return response
            purpose = "link"
            account_id = session["account"]["id"]
            initiating_session_id = session["session_id"]
        state_value = _create_oauth_state(
            provider,
            purpose=purpose,
            account_id=account_id,
            initiating_session_id=initiating_session_id,
            return_path=_safe_oauth_return_path(request.query_params.get("next")),
        )
        authorization_url = _oauth_authorization_url(provider, state_value)
    except (HTTPException, RuntimeError, ValueError):
        response = _oauth_redirect("unavailable" if purpose == "signin" else "session", path="/account" if purpose == "link" else "/login")
        if request.query_params.get("link") == "1":
            _clear_oauth_link_cookie(response)
        return response
    response = RedirectResponse(authorization_url, status_code=status.HTTP_303_SEE_OTHER)
    _set_oauth_state_cookie(response, provider, state_value)
    if purpose == "link":
        _clear_oauth_link_cookie(response)
    with transaction() as conn:
        _record_audit(conn, account_id=account_id, canonical_user_id=None, action="oauth.start", request_id=_request_id(request), target=provider, detail=purpose)
    return response


async def _oauth_callback_impl(provider: str, request: Request, values: dict[str, str], *, apple_display_name: str = "") -> RedirectResponse:
    """Consume one OAuth state and complete either sign-in or explicit link."""
    if not _oauth_enabled(provider):
        return _oauth_redirect("unavailable")
    state_value = str(values.get("state") or "")
    if not state_value or len(state_value) > OAUTH_STATE_VALUE_MAX_LENGTH:
        response = _oauth_redirect("state")
        _clear_oauth_state_cookie(response, request=request, provider=provider, state_value=state_value)
        return response
    state_data = _consume_oauth_state(request, provider, state_value)
    if not state_data:
        response = _oauth_redirect("state")
        _clear_oauth_state_cookie(response, request=request, provider=provider, state_value=state_value)
        return response
    provider_error = str(values.get("error") or "")
    code = str(values.get("code") or "")
    if provider_error or not code:
        with transaction() as conn:
            _record_audit(conn, account_id=state_data["account_id"], canonical_user_id=None, action="oauth.callback", request_id=_request_id(request), target=provider, outcome="denied", detail="provider cancelled or omitted authorization code")
        response = _oauth_redirect("cancelled" if provider_error == "access_denied" else "failed", path="/account" if state_data["purpose"] == "link" else "/login")
        _clear_oauth_state_cookie(response, request=request, provider=provider, state_value=state_value, cookie_name=state_data["_state_cookie_name"])
        return response
    try:
        identity = await _fetch_apple_identity(code, state_value, display_name=apple_display_name) if provider == "apple" else await _fetch_oauth_identity(provider, code, state_value)
        if identity.get("provider") != provider:
            raise OAuthIdentityError("provider identity mismatch")
    except OAuthIdentityError:
        with transaction() as conn:
            _record_audit(conn, account_id=state_data["account_id"], canonical_user_id=None, action="oauth.callback", request_id=_request_id(request), target=provider, outcome="denied", detail="provider identity verification failed")
        response = _oauth_redirect("failed", path="/account" if state_data["purpose"] == "link" else "/login")
        _clear_oauth_state_cookie(response, request=request, provider=provider, state_value=state_value, cookie_name=state_data["_state_cookie_name"])
        return response
    except Exception:
        # Treat unexpected provider client failures exactly like a failed
        # verification.  Do not leak third-party details to browser/audit.
        with transaction() as conn:
            _record_audit(conn, account_id=state_data["account_id"], canonical_user_id=None, action="oauth.callback", request_id=_request_id(request), target=provider, outcome="denied", detail="provider callback failed")
        response = _oauth_redirect("failed", path="/account" if state_data["purpose"] == "link" else "/login")
        _clear_oauth_state_cookie(response, request=request, provider=provider, state_value=state_value, cookie_name=state_data["_state_cookie_name"])
        return response
    if state_data["purpose"] == "link":
        if provider == "apple":
            account = _oauth_bound_link_account(state_data)
            if not account:
                response = _oauth_redirect("session", path="/account")
                _clear_oauth_state_cookie(response, request=request, provider=provider, state_value=state_value, cookie_name=state_data["_state_cookie_name"])
                return response
        else:
            try:
                session = current_session(request)
            except HTTPException:
                response = _oauth_redirect("session", path="/account")
                _clear_oauth_state_cookie(response, request=request, provider=provider, state_value=state_value, cookie_name=state_data["_state_cookie_name"])
                return response
            if session["session_id"] != state_data["initiating_session_id"] or session["account"]["id"] != state_data["account_id"]:
                response = _oauth_redirect("session", path="/account")
                _clear_oauth_state_cookie(response, request=request, provider=provider, state_value=state_value, cookie_name=state_data["_state_cookie_name"])
                return response
            account = session["account"]
        outcome, replacement = _link_oauth_identity(
            identity,
            account,
            request,
            initiating_session_id=str(state_data.get("initiating_session_id") or ""),
        )
        response = _oauth_redirect(outcome, path="/account")
        if replacement:
            # Do not place the fresh CSRF token in a redirect URL or callback
            # body. The browser receives only its replacement HttpOnly cookie;
            # the normal authenticated `/me` bootstrap returns the new CSRF.
            _set_session_cookie(response, str(replacement["session_id"]))
        _clear_oauth_state_cookie(response, request=request, provider=provider, state_value=state_value, cookie_name=state_data["_state_cookie_name"])
        return response
    account, outcome = _oauth_signin_account(identity, request)
    if not account:
        response = _oauth_redirect(outcome)
        _clear_oauth_state_cookie(response, request=request, provider=provider, state_value=state_value, cookie_name=state_data["_state_cookie_name"])
        return response
    return_path = _safe_oauth_return_path(state_data["return_path"])
    # OAuth establishes a signed Web account with its own Workspace. Telegram
    # linking is an optional companion integration, not an execution gate, so
    # an email/Google/GitHub/Apple user returns straight to the validated Web
    # route they intentionally opened.
    target = return_path
    response = RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)
    _create_session(response, account["id"])
    _clear_oauth_state_cookie(response, request=request, provider=provider, state_value=state_value, cookie_name=state_data["_state_cookie_name"])
    return response


@router.get("/oauth/{provider}/callback")
async def oauth_callback(provider: str, request: Request):
    provider = provider.strip().lower()
    if provider == "apple":
        response = _oauth_redirect("failed")
        _clear_oauth_state_cookie(
            response,
            request=request,
            provider="apple",
            state_value=str(request.query_params.get("state") or ""),
        )
        return response
    return await _oauth_callback_impl(
        provider,
        request,
        {
            "state": str(request.query_params.get("state") or ""),
            "error": str(request.query_params.get("error") or ""),
            "code": str(request.query_params.get("code") or ""),
        },
    )


@router.post("/oauth/apple/callback")
async def apple_oauth_callback(request: Request):
    # Apple returns the `code`/`state` as a cross-site form POST. Bound its
    # body before parsing to keep this public callback from becoming an upload
    # sink. The submitted `id_token`/email/name are never trusted as identity.
    body = await request.body()
    if len(body) > 16_384:
        return _oauth_redirect("failed")
    try:
        form = await request.form()
    except Exception:
        return _oauth_redirect("failed")
    values = {key: str(form.get(key) or "") for key in ("state", "error", "code", "user")}
    return await _oauth_callback_impl("apple", request, values, apple_display_name=_apple_display_name(values["user"]))


async def _telegram_challenge_input_rejection(request: Request) -> JSONResponse | None:
    """Reject a browser-supplied Telegram identity instead of silently ignoring it.

    The old prototype accepted a raw `telegram_id` field but could never
    safely use it as proof. A clear 422 makes the replacement flow obvious:
    start the challenge, open the Bot deep link, and let the Bot callback
    establish identity from its authenticated Telegram user.
    """
    body = await request.body()
    if not body or not body.strip():
        return None
    if len(body) > 1_024:
        return JSONResponse(
            envelope(False, "Đăng nhập Telegram không nhận dữ liệu từ browser. Hãy dùng nút Đăng nhập với Telegram để Bot xác minh.", status_name="failed", error_code="TELEGRAM_BROWSER_INPUT_NOT_ACCEPTED"),
            status_code=HTTP_422_UNPROCESSABLE,
        )
    try:
        value = json.loads(body)
    except (TypeError, ValueError, UnicodeDecodeError):
        value = None
    if value == {}:
        return None
    message = (
        "Không nhập Telegram ID vào Web. Hãy dùng nút Đăng nhập với Telegram để Bot xác minh quyền sở hữu."
        if isinstance(value, dict) and "telegram_id" in value
        else "Liên kết Telegram không nhận dữ liệu từ browser. Hãy dùng mã một lần và xác minh trong Bot."
    )
    return JSONResponse(
        envelope(False, message, status_name="failed", error_code="TELEGRAM_BROWSER_INPUT_NOT_ACCEPTED"),
        status_code=HTTP_422_UNPROCESSABLE,
    )


@router.post("/telegram/login/start")
async def start_telegram_login(request: Request, response: Response):
    """Start passwordless sign-in without accepting a raw Telegram ID.

    The visible code is proven only inside the already authenticated Telegram
    bot. A separate HttpOnly browser challenge prevents a copied code from
    issuing a Web session in another browser.
    """
    rejected_input = await _telegram_challenge_input_rejection(request)
    if rejected_input is not None:
        return rejected_input
    if not bool(_telegram_connection_configuration()["ready"]):
        return _telegram_connection_required_response()
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
        _cookie_name(TELEGRAM_LOGIN_COOKIE),
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
    browser_token = _parse_telegram_login_cookie(request.cookies.get(_cookie_name(TELEGRAM_LOGIN_COOKIE)))
    if not browser_token:
        return None
    return browser_token, hashlib.sha256(browser_token.encode("utf-8")).hexdigest()


def _clear_telegram_login_cookie(response: Response) -> None:
    response.delete_cookie(
        _cookie_name(TELEGRAM_LOGIN_COOKIE),
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
            "SELECT expires_at, consumed_at, canonical_user_id, failure_code FROM telegram_login_codes WHERE browser_token_hash=?",
            (token_hash,),
        ).fetchone()
        if not row or _as_time(row[0]) <= _now():
            conn.execute("DELETE FROM telegram_login_codes WHERE browser_token_hash=?", (token_hash,))
            _clear_telegram_login_cookie(response)
            return envelope(False, "Mã đăng nhập Telegram đã hết hạn. Hãy tạo mã mới.", data={"ready": False}, status_name="failed", error_code="TELEGRAM_LOGIN_EXPIRED")
        if row[3] == "TELEGRAM_LOGIN_ACCOUNT_REQUIRED":
            return envelope(
                False,
                "Telegram này chưa liên kết với tài khoản Web. Hãy đăng ký/đăng nhập email, liên kết Telegram trong Thiết lập tài khoản, rồi tạo mã đăng nhập mới.",
                data={"ready": False, "restart_required": True},
                status_name="guarded",
                error_code="TELEGRAM_LOGIN_ACCOUNT_REQUIRED",
            )
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
            "SELECT code_hash, expires_at, consumed_at, canonical_user_id, failure_code FROM telegram_login_codes WHERE browser_token_hash=?",
            (token_hash,),
        ).fetchone()
        if not row or _as_time(row[1]) <= _now():
            conn.execute("DELETE FROM telegram_login_codes WHERE browser_token_hash=?", (token_hash,))
            _clear_telegram_login_cookie(response)
            return envelope(False, "Mã đăng nhập Telegram đã hết hạn. Hãy tạo mã mới.", status_name="failed", error_code="TELEGRAM_LOGIN_EXPIRED")
        if row[4] == "TELEGRAM_LOGIN_ACCOUNT_REQUIRED":
            return envelope(
                False,
                "Telegram này chưa liên kết với tài khoản Web. Hãy đăng ký/đăng nhập email và liên kết Telegram trước khi dùng đăng nhập Telegram.",
                status_name="guarded",
                error_code="TELEGRAM_LOGIN_ACCOUNT_REQUIRED",
            )
        if not row[2] or not row[3]:
            return envelope(False, "Bot chưa xác minh Telegram cho mã này.", status_name="awaiting_confirm", error_code="TELEGRAM_LOGIN_PENDING")
        account_row = conn.execute(
            """SELECT a.id, a.email, a.display_name, a.canonical_user_id, a.role_cache, a.is_active, a.password_login_enabled,
                      p.locale, p.timezone, p.avatar_style
               FROM web_accounts a LEFT JOIN web_account_profiles p ON p.account_id=a.id
               WHERE a.canonical_user_id=?""",
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
            "password_login_enabled": bool(account_row[6]),
            "locale": normalize_interface_locale(account_row[7]), "timezone": account_row[8] or "Asia/Ho_Chi_Minh",
            "avatar_style": account_row[9] or "gradient",
        }
        conn.execute("DELETE FROM telegram_login_codes WHERE code_hash=?", (row[0],))
        _record_audit(conn, account_id=account["id"], canonical_user_id=account["canonical_user_id"], action="auth.telegram_login_complete", request_id=_request_id(request))
    _clear_telegram_login_cookie(response)
    session = _create_session(response, account["id"])
    return envelope(True, "Đăng nhập Telegram thành công", data={"account": browser_account_payload(account), **session})


@router.post("/telegram/link/start")
async def start_telegram_link(request: Request, account: dict = Depends(require_csrf)):
    rejected_input = await _telegram_challenge_input_rejection(request)
    if rejected_input is not None:
        return rejected_input
    if account["canonical_user_id"]:
        return envelope(
            False,
            "Tài khoản này đã liên kết Telegram. Để bảo vệ dữ liệu canonical, Web không cho thay Telegram identity bằng mã mới.",
            status_name="guarded",
            error_code="TELEGRAM_RELINK_NOT_ALLOWED",
        )
    if not bool(_telegram_connection_configuration()["ready"]):
        return _telegram_connection_required_response()
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
async def telegram_link_status(request: Request, account: dict = Depends(require_account)):
    """Return only session-bound progress for a pending Bot link.

    The opaque code and canonical Telegram identity never return to the
    browser.  A second browser session for the same Web account must not learn
    that a different tab has a live linking capability, nor may it complete
    the binding.
    """
    linked = bool(account["canonical_user_id"])
    if linked:
        return envelope(True, "Telegram đã liên kết", data={"linked": True}, status_name="completed")

    session_id = current_session(request)["session_id"]
    now = _now()
    with transaction() as conn:
        conn.execute("DELETE FROM telegram_link_codes WHERE account_id=? AND expires_at<=?", (account["id"], now.isoformat(timespec="seconds")))
        row = conn.execute(
            """SELECT expires_at, canonical_user_id
               FROM telegram_link_codes
               WHERE account_id=? AND initiating_session_id=? AND consumed_at IS NULL AND expires_at>?
               ORDER BY created_at DESC
               LIMIT 1""",
            (account["id"], session_id, now.isoformat(timespec="seconds")),
        ).fetchone()
    if not row:
        return envelope(True, "Chưa có mã liên kết đang chờ trong tab này.", data={"linked": False}, status_name="awaiting_confirm")

    seconds_remaining = max(0, int((_as_time(row[0]) - now).total_seconds()))
    ready_to_complete = bool(row[1])
    if ready_to_complete:
        message = "Bot đã xác minh Telegram. Tab đã tạo mã cần hoàn tất liên kết an toàn."
    else:
        message = "Đang chờ Bot xác minh mã liên kết Telegram."
    return envelope(
        True,
        message,
        data={
            "linked": False,
            "pending": not ready_to_complete,
            "ready_to_complete": ready_to_complete,
            "expires_in_seconds": seconds_remaining,
            "expires_in_minutes": max(1, (seconds_remaining + 59) // 60),
        },
        status_name="awaiting_confirm",
    )


class _BridgeCallbackBodyTooLarge(Exception):
    """Raised before JSON parsing when an internal callback exceeds its cap."""


async def _read_bounded_bridge_callback_body(request: Request) -> bytes:
    """Read an exact callback body without making the endpoint an upload sink."""
    declared_length = request.headers.get("Content-Length", "").strip()
    if declared_length:
        try:
            declared_bytes = int(declared_length)
            if declared_bytes < 0 or declared_bytes > BRIDGE_CALLBACK_MAX_BODY_BYTES:
                raise _BridgeCallbackBodyTooLarge()
        except ValueError:
            raise _BridgeCallbackBodyTooLarge() from None
    chunks: list[bytes] = []
    received = 0
    async for chunk in request.stream():
        received += len(chunk)
        if received > BRIDGE_CALLBACK_MAX_BODY_BYTES:
            raise _BridgeCallbackBodyTooLarge()
        chunks.append(chunk)
    return b"".join(chunks)


async def _bridge_callback_authorized(request: Request) -> tuple[bytes, str] | None:
    """Authenticate the bot-to-web link callback as a separate private channel.

    The callback is intentionally not allowed to reuse the browser-facing core
    bearer token.  It requires its own bearer token *and* an HMAC over the
    exact body, timestamp and one-time request ID.  The persistent nonce table
    makes a captured request unusable after its first attempt or process
    restart; the one-time link code then provides a second replay boundary.
    """
    # Identity proof has a dedicated directional credential.  Do not fall
    # back to the general core-bridge callback pair: accepting either pair
    # would silently widen the authority that can attach a Telegram identity
    # to a Web account.
    token = os.environ.get("WEBAPP_LINK_CALLBACK_TOKEN", "").strip()
    secret = os.environ.get("WEBAPP_LINK_CALLBACK_HMAC_SECRET", "").strip()
    supplied_token = request.headers.get("X-TOAN-AAS-BRIDGE-TOKEN", "")
    timestamp = request.headers.get("X-TOAN-AAS-Timestamp", "")
    request_id = request.headers.get("X-TOAN-AAS-Request-ID", "")
    signature = request.headers.get("X-TOAN-AAS-Signature", "")
    if not token or not secret or not supplied_token or not hmac.compare_digest(token, supplied_token):
        return None
    if not timestamp.isdigit() or len(timestamp) > 12 or not BRIDGE_CALLBACK_REQUEST_ID_PATTERN.fullmatch(request_id):
        return None
    timestamp_value = int(timestamp)
    age_seconds = int(_now().timestamp()) - timestamp_value
    if age_seconds > BRIDGE_CALLBACK_MAX_AGE_SECONDS or age_seconds < -BRIDGE_CALLBACK_MAX_FUTURE_SKEW_SECONDS:
        return None
    body = await _read_bounded_bridge_callback_body(request)
    digest = hashlib.sha256(body).hexdigest()
    material = f"{timestamp}.{request_id}.{request.method.upper()}.{request.url.path}.{digest}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), material, hashlib.sha256).hexdigest()
    if not signature or not hmac.compare_digest(signature, expected):
        return None
    with transaction() as conn:
        conn.execute("DELETE FROM web_bridge_callback_nonces WHERE expires_at<=?", (_now().isoformat(timespec="seconds"),))
        if conn.execute("SELECT 1 FROM web_bridge_callback_nonces WHERE request_id=?", (request_id,)).fetchone():
            return None
        conn.execute(
            "INSERT INTO web_bridge_callback_nonces (request_id, expires_at, created_at) VALUES (?, ?, ?)",
            (request_id, _bridge_callback_expiry(timestamp_value), utc_now()),
        )
    return body, request_id


@router.post("/internal/telegram-link/confirm")
@router.post("/internal/telegram-link/confirm/")
async def confirm_telegram_link(request: Request):
    """Private callback for the bot after a user proves ownership in Telegram."""
    try:
        authorized = await _bridge_callback_authorized(request)
    except _BridgeCallbackBodyTooLarge:
        return _bridge_callback_failure(
            "Callback Telegram vượt quá kích thước cho phép.",
            error_code="BRIDGE_CALLBACK_BODY_TOO_LARGE",
            http_status=HTTP_413_PAYLOAD_TOO_LARGE,
        )
    if not authorized:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bridge authentication failed")
    body, callback_request_id = authorized
    try:
        payload = LinkConfirmation.model_validate_json(body)
    except ValidationError:
        return _bridge_callback_failure(
            "Dữ liệu callback Telegram không hợp lệ.",
            error_code="LINK_CALLBACK_INVALID",
            http_status=HTTP_422_UNPROCESSABLE,
        )
    # The release gate is also an emergency stop, not merely a UI hint.  A
    # code issued shortly before an operator disables the paired Bot adapter
    # must not remain capable of attaching a canonical Telegram identity.
    # Authenticate first so this endpoint never reveals release state to an
    # unauthenticated caller; do not consume the one-time code on this guard.
    if not _telegram_bot_link_adapter_enabled():
        return _bridge_callback_failure(
            "Cầu nối Telegram đang tạm dừng để bảo trì. Hãy tạo mã mới sau khi Bot adapter được bật lại.",
            error_code="TELEGRAM_LINK_ADAPTER_DISABLED",
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            status_name="guarded",
        )
    code_hash = hashlib.sha256(payload.code.encode("utf-8")).hexdigest()
    canonical_user_id = payload.canonical_user_id.strip()
    if not canonical_user_id:
        return _bridge_callback_failure(
            "Telegram identity không hợp lệ",
            error_code="LINK_IDENTITY_INVALID",
            http_status=HTTP_422_UNPROCESSABLE,
        )
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
                return _bridge_callback_failure(
                    "Mã liên kết không hợp lệ hoặc đã hết hạn",
                    error_code="LINK_CODE_INVALID",
                    http_status=status.HTTP_410_GONE,
                )
            linked_account = conn.execute(
                "SELECT id, is_active FROM web_accounts WHERE canonical_user_id=?",
                (canonical_user_id,),
            ).fetchone()
            if linked_account and not linked_account[1]:
                _record_audit(
                    conn,
                    account_id=linked_account[0],
                    canonical_user_id=canonical_user_id,
                    action="auth.telegram_login_confirm",
                    request_id=callback_request_id,
                    outcome="denied",
                    detail="canonical identity belongs to inactive web account",
                )
                conn.execute(
                    "UPDATE telegram_login_codes SET consumed_at=?, failure_code=? WHERE code_hash=?",
                    (utc_now(), "TELEGRAM_LOGIN_ACCOUNT_REQUIRED", code_hash),
                )
                return _bridge_callback_failure(
                    "Telegram này đang gắn với một tài khoản Web không hoạt động.",
                    error_code="TELEGRAM_LOGIN_ACCOUNT_REQUIRED",
                    http_status=status.HTTP_409_CONFLICT,
                    status_name="guarded",
                )
            if not linked_account:
                if not _telegram_auto_register_enabled():
                    _record_audit(
                        conn,
                        account_id=None,
                        canonical_user_id=canonical_user_id,
                        action="auth.telegram_login_confirm",
                        request_id=callback_request_id,
                        outcome="denied",
                        detail="no active linked web account and auto register disabled",
                    )
                    conn.execute(
                        "UPDATE telegram_login_codes SET consumed_at=?, failure_code=? WHERE code_hash=?",
                        (utc_now(), "TELEGRAM_LOGIN_ACCOUNT_REQUIRED", code_hash),
                    )
                    return _bridge_callback_failure(
                        "Telegram chưa liên kết với tài khoản Web đang hoạt động. Hãy đăng ký/đăng nhập email một lần rồi liên kết Telegram.",
                        error_code="TELEGRAM_LOGIN_ACCOUNT_REQUIRED",
                        http_status=status.HTTP_409_CONFLICT,
                        status_name="guarded",
                    )
                created = _create_telegram_only_account(
                    conn,
                    canonical_user_id=canonical_user_id,
                    role="admin" if payload.role == "admin" else "user",
                    display_name=payload.display_name,
                    request=request,
                )
                linked_account = (created["id"],)
            conn.execute(
                "UPDATE telegram_login_codes SET consumed_at=?, canonical_user_id=?, failure_code=NULL WHERE code_hash=?",
                (utc_now(), canonical_user_id, code_hash),
            )
            _record_audit(conn, account_id=linked_account[0], canonical_user_id=canonical_user_id, action="auth.telegram_login_confirm", request_id=callback_request_id)
            return envelope(True, "Đã xác minh Telegram cho phiên đăng nhập Web", data={"mode": "login"})
        if row[2] or _as_time(row[1]) <= _now():
            return _bridge_callback_failure(
                "Mã liên kết không hợp lệ hoặc đã hết hạn",
                error_code="LINK_CODE_INVALID",
                http_status=status.HTTP_410_GONE,
            )
        account_id, _expires_at, _consumed_at, initiating_session_id = row
        # The deep-link code is not enough to mutate a Web account.  The
        # signed Bot proof must still be paired with the live browser session
        # which created it.  A logout, expiry or session rotation invalidates
        # the code before it can be confirmed.
        active_session = conn.execute(
            """SELECT 1 FROM web_sessions
               WHERE id=? AND account_id=? AND revoked_at IS NULL AND expires_at>?""",
            (initiating_session_id, account_id, utc_now()),
        ).fetchone() if initiating_session_id else None
        if not active_session:
            conn.execute("UPDATE telegram_link_codes SET consumed_at=? WHERE code_hash=?", (utc_now(), code_hash))
            _record_audit(
                conn,
                account_id=account_id,
                canonical_user_id=None,
                action="auth.telegram_link_confirm",
                request_id=callback_request_id,
                outcome="denied",
                detail="initiating browser session is missing, revoked, or expired",
            )
            return _bridge_callback_failure(
                "Phiên Web đã tạo mã liên kết không còn hợp lệ. Hãy tạo mã mới trong Web.",
                error_code="LINK_SESSION_INVALID",
                http_status=status.HTTP_410_GONE,
                status_name="guarded",
            )
        account_row = conn.execute(
            "SELECT canonical_user_id, is_active FROM web_accounts WHERE id=?",
            (account_id,),
        ).fetchone()
        if not account_row or not account_row[1]:
            _record_audit(
                conn,
                account_id=account_id,
                canonical_user_id=None,
                action="auth.telegram_link_confirm",
                request_id=callback_request_id,
                outcome="denied",
                detail="target web account is missing or inactive",
            )
            return _bridge_callback_failure(
                "Tài khoản Web của mã liên kết không còn hoạt động.",
                error_code="LINK_ACCOUNT_REQUIRED",
                http_status=status.HTTP_404_NOT_FOUND,
            )
        existing_canonical_user_id = str(account_row[0] or "")
        if existing_canonical_user_id:
            _record_audit(
                conn,
                account_id=account_id,
                canonical_user_id=existing_canonical_user_id,
                action="auth.telegram_link_confirm",
                request_id=callback_request_id,
                outcome="denied",
                detail="attempted to replace an existing canonical Telegram identity",
            )
            return _bridge_callback_failure(
                "Tài khoản Web này đã liên kết Telegram; Web không cho thay identity canonical bằng mã liên kết.",
                error_code="TELEGRAM_RELINK_NOT_ALLOWED",
                http_status=status.HTTP_409_CONFLICT,
                status_name="guarded",
            )
        pending_identity = conn.execute(
            "SELECT canonical_user_id FROM telegram_link_codes WHERE code_hash=?",
            (code_hash,),
        ).fetchone()
        if pending_identity and pending_identity[0]:
            if hmac.compare_digest(str(pending_identity[0]), canonical_user_id):
                return envelope(
                    True,
                    "Bot đã xác minh Telegram. Hãy quay lại đúng tab Web đã tạo mã để hoàn tất liên kết.",
                    data={"mode": "link", "browser_confirmation_required": True},
                    status_name="awaiting_confirm",
                )
            _record_audit(
                conn,
                account_id=account_id,
                canonical_user_id=None,
                action="auth.telegram_link_confirm",
                request_id=callback_request_id,
                outcome="denied",
                detail="attempted to replace a pending Bot-confirmed Telegram identity",
            )
            return _bridge_callback_failure(
                "Mã liên kết này đã được Bot xác minh cho một Telegram khác.",
                error_code="LINK_CODE_ALREADY_CONFIRMED",
                http_status=status.HTTP_409_CONFLICT,
                status_name="guarded",
            )
        telegram_oidc = conn.execute(
            "SELECT subject_hash FROM web_external_identities WHERE account_id=? AND provider='telegram'",
            (account_id,),
        ).fetchone()
        if telegram_oidc:
            try:
                expected_telegram_oidc = _external_subject_hash("telegram", canonical_user_id)
            except RuntimeError:
                _record_audit(
                    conn,
                    account_id=account_id,
                    canonical_user_id=None,
                    action="auth.telegram_link_confirm",
                    request_id=callback_request_id,
                    outcome="denied",
                    detail="Telegram OIDC identity HMAC configuration unavailable",
                )
                return _bridge_callback_failure(
                    "Telegram Login đang thiếu cấu hình bảo vệ identity. Hãy liên hệ hỗ trợ để khôi phục cấu hình trước khi liên kết Bot.",
                    error_code="TELEGRAM_OIDC_CONFIGURATION_REQUIRED",
                    http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
                    status_name="guarded",
                )
            if not hmac.compare_digest(str(telegram_oidc[0]), expected_telegram_oidc):
                _record_audit(
                    conn,
                    account_id=account_id,
                    canonical_user_id=None,
                    action="auth.telegram_link_confirm",
                    request_id=callback_request_id,
                    outcome="denied",
                    detail="Telegram OIDC identity does not match signed Bot identity",
                )
                return _bridge_callback_failure(
                    "Tài khoản Web này đã xác thực bằng một Telegram khác. Hãy xác nhận đúng cùng tài khoản Telegram trong Bot.",
                    error_code="TELEGRAM_OIDC_MISMATCH",
                    http_status=status.HTTP_409_CONFLICT,
                    status_name="guarded",
                )
        existing = conn.execute(
            "SELECT id FROM web_accounts WHERE canonical_user_id=? AND id<>?",
            (canonical_user_id, account_id),
        ).fetchone()
        pending_elsewhere = conn.execute(
            """SELECT 1 FROM telegram_link_codes c
               JOIN web_sessions s ON s.id=c.initiating_session_id AND s.account_id=c.account_id
               WHERE c.canonical_user_id=? AND c.account_id<>? AND c.consumed_at IS NULL AND c.expires_at>?
                 AND s.revoked_at IS NULL AND s.expires_at>?
               LIMIT 1""",
            (canonical_user_id, account_id, utc_now(), utc_now()),
        ).fetchone()
        if existing or pending_elsewhere:
            _record_audit(
                conn,
                account_id=account_id,
                canonical_user_id=None,
                action="auth.telegram_link_confirm",
                request_id=callback_request_id,
                outcome="denied",
                detail="canonical identity already linked or pending on another account",
            )
            return _bridge_callback_failure(
                "Tài khoản Telegram này đã liên kết hoặc đang chờ xác nhận ở một tài khoản Web khác",
                error_code="TELEGRAM_ALREADY_LINKED",
                http_status=status.HTTP_409_CONFLICT,
            )
        role = "admin" if payload.role == "admin" else "user"
        conn.execute(
            """UPDATE telegram_link_codes
               SET canonical_user_id=?, bot_confirmed_at=?, confirmed_role=?, confirmed_display_name=?
               WHERE code_hash=?""",
            (canonical_user_id, utc_now(), role, payload.display_name.strip(), code_hash),
        )
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=canonical_user_id,
            action="auth.telegram_link_confirm",
            request_id=callback_request_id,
            detail="Bot proof recorded; awaiting initiating browser CSRF completion",
        )
    return envelope(
        True,
        "Bot đã xác minh Telegram. Hãy quay lại đúng tab Web đã tạo mã để hoàn tất liên kết.",
        data={"mode": "link", "browser_confirmation_required": True},
        status_name="awaiting_confirm",
    )


@router.post("/telegram/link/complete")
async def complete_telegram_link(request: Request, account: dict = Depends(require_csrf)):
    """Commit a Bot-confirmed link only from the initiating CSRF session.

    The Bot callback intentionally never attaches an identity to a Web
    account by itself.  This final browser request provides a separate
    session-bound proof of intent and prevents a copied deep-link code from
    becoming a direct account-takeover primitive.
    """
    session_id = current_session(request)["session_id"]
    now = utc_now()
    with transaction() as conn:
        session_row = conn.execute(
            """SELECT 1 FROM web_sessions
               WHERE id=? AND account_id=? AND revoked_at IS NULL AND expires_at>?""",
            (session_id, account["id"], now),
        ).fetchone()
        if not session_row:
            return envelope(
                False,
                "Phiên Web đã hết hạn. Hãy đăng nhập lại trước khi liên kết Telegram.",
                status_name="guarded",
                error_code="LINK_SESSION_INVALID",
            )
        row = conn.execute(
            """SELECT code_hash, expires_at, canonical_user_id, confirmed_role, confirmed_display_name
               FROM telegram_link_codes
               WHERE account_id=? AND initiating_session_id=? AND consumed_at IS NULL AND expires_at>?
               ORDER BY created_at DESC
               LIMIT 1""",
            (account["id"], session_id, now),
        ).fetchone()
        if not row:
            return envelope(
                False,
                "Không có mã liên kết đang chờ trong phiên Web này. Hãy tạo mã mới.",
                status_name="guarded",
                error_code="LINK_CODE_INVALID",
            )
        code_hash, _expires_at, canonical_user_id, confirmed_role, confirmed_display_name = row
        if not canonical_user_id:
            return envelope(
                False,
                "Bot chưa xác minh Telegram cho mã này.",
                status_name="awaiting_confirm",
                error_code="TELEGRAM_LINK_PENDING",
            )
        account_row = conn.execute(
            "SELECT canonical_user_id, is_active FROM web_accounts WHERE id=?",
            (account["id"],),
        ).fetchone()
        if not account_row or not account_row[1]:
            return envelope(
                False,
                "Tài khoản Web không còn hoạt động.",
                status_name="guarded",
                error_code="LINK_ACCOUNT_REQUIRED",
            )
        if account_row[0]:
            return envelope(
                False,
                "Tài khoản này đã liên kết Telegram; Web không cho thay identity canonical.",
                status_name="guarded",
                error_code="TELEGRAM_RELINK_NOT_ALLOWED",
            )
        telegram_oidc = conn.execute(
            "SELECT subject_hash FROM web_external_identities WHERE account_id=? AND provider='telegram'",
            (account["id"],),
        ).fetchone()
        if telegram_oidc:
            try:
                expected_telegram_oidc = _external_subject_hash("telegram", str(canonical_user_id))
            except RuntimeError:
                return envelope(
                    False,
                    "Telegram Login đang thiếu cấu hình bảo vệ identity. Hãy liên hệ hỗ trợ để khôi phục cấu hình trước khi liên kết Bot.",
                    status_name="guarded",
                    error_code="TELEGRAM_OIDC_CONFIGURATION_REQUIRED",
                )
            if not hmac.compare_digest(str(telegram_oidc[0]), expected_telegram_oidc):
                return envelope(
                    False,
                    "Tài khoản Web này đã xác thực bằng một Telegram khác. Hãy xác nhận đúng cùng tài khoản Telegram trong Bot.",
                    status_name="guarded",
                    error_code="TELEGRAM_OIDC_MISMATCH",
                )
        existing = conn.execute(
            "SELECT id FROM web_accounts WHERE canonical_user_id=? AND id<>?",
            (canonical_user_id, account["id"]),
        ).fetchone()
        if existing:
            return envelope(
                False,
                "Tài khoản Telegram này đã liên kết với một tài khoản Web khác.",
                status_name="guarded",
                error_code="TELEGRAM_ALREADY_LINKED",
            )
        role = "admin" if confirmed_role == "admin" else "user"
        conn.execute(
            """UPDATE web_accounts
               SET canonical_user_id=?, role_cache=?, display_name=COALESCE(NULLIF(?, ''), display_name), updated_at=?
               WHERE id=?""",
            (canonical_user_id, role, str(confirmed_display_name or "").strip(), now, account["id"]),
        )
        conn.execute(
            "UPDATE telegram_link_codes SET consumed_at=? WHERE code_hash=?",
            (now, code_hash),
        )
        # Identity changed only after the initiating browser deliberately
        # completed the binding.  Other sessions never inherit it silently.
        conn.execute(
            "UPDATE web_sessions SET revoked_at=? WHERE account_id=? AND id<>? AND revoked_at IS NULL",
            (now, account["id"], session_id),
        )
        _record_audit(
            conn,
            account_id=account["id"],
            canonical_user_id=str(canonical_user_id),
            action="auth.telegram_link_complete",
            request_id=_request_id(request),
            detail="initiating browser completed Bot-confirmed Telegram identity",
        )
    return envelope(True, "Telegram đã được liên kết an toàn.", data={"linked": True}, status_name="completed")
