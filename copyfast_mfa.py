"""Optional Web-native TOTP second factor for password sign-in.

This module owns only the standalone Web account factor. It never imports a
Telegram Bot, bridge, provider, wallet/Xu, PayOS, job, output, notification or
deployment adapter. Enabling it is explicit because a second factor must fail
closed rather than silently becoming a new login bypass.
"""

from __future__ import annotations

import base64
import binascii
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
import re
import secrets
import uuid
from typing import Any
from urllib.parse import quote

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from copyfast_auth import (
    _insert_session,
    _password_hash,
    _record_audit,
    _request_id,
    _rotate_account_sessions,
    _session_is_active_for_account,
    _set_session_cookie,
    _verify_password,
    browser_account_payload,
    current_session,
    envelope,
    password_login_factor_available,
    require_account,
    require_csrf,
)
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction, utc_now


router = APIRouter(prefix="/api/v1/auth", tags=["Web Account MFA"])

TOTP_PERIOD_SECONDS = 30
TOTP_DIGITS = 6
TOTP_SECRET_BYTES = 20
TOTP_ENROLLMENT_TTL_MINUTES = 15
TOTP_LOGIN_CHALLENGE_TTL_MINUTES = 5
TOTP_LOGIN_MAX_ATTEMPTS = 5
TOTP_RECOVERY_CODE_COUNT = 8
TOTP_CODE_PATTERN = re.compile(r"^[0-9]{6}$")
TOTP_RECOVERY_CODE_PATTERN = re.compile(r"^[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}$")
TOTP_OPAQUE_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{32,160}$")
TOTP_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
RECOVERY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def totp_mfa_enabled() -> bool:
    """Whether the explicitly configured Web-only TOTP factor is enabled."""

    return os.environ.get("WEBAPP_TOTP_MFA_ENABLED", "false").strip().lower() in {
        "1", "true", "yes", "on"
    }


def _urlsafe_key(raw: str) -> bytes:
    value = str(raw or "").strip()
    if not value or any(character.isspace() for character in value):
        raise RuntimeError("WEBAPP_TOTP_MFA_ENCRYPTION_KEY phải là khóa base64url 32 bytes")
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, TypeError, binascii.Error) as exc:
        raise RuntimeError("WEBAPP_TOTP_MFA_ENCRYPTION_KEY không hợp lệ") from exc
    if len(decoded) != 32:
        raise RuntimeError("WEBAPP_TOTP_MFA_ENCRYPTION_KEY phải giải mã thành đúng 32 bytes")
    return decoded


def _configuration() -> dict[str, bytes] | None:
    """Return the independent encryption/HMAC key only when MFA is opted in."""

    if not totp_mfa_enabled():
        return None
    return {"key": _urlsafe_key(os.environ.get("WEBAPP_TOTP_MFA_ENCRYPTION_KEY", ""))}


def ensure_totp_mfa_configuration() -> None:
    """Fail startup only when an operator has explicitly enabled MFA."""

    _configuration()


def totp_mfa_runtime_available() -> bool:
    """Expose a safe boolean to password login without swallowing bad config."""

    try:
        return _configuration() is not None
    except RuntimeError:
        return False


def active_totp_factor_exists(conn: Any, *, account_id: str) -> bool:
    """Return whether a password account has an active second factor.

    This deliberately does not consult the feature flag. If an already active
    factor exists while the service is paused or misconfigured, password login
    must fail closed instead of bypassing the factor.
    """

    return bool(
        conn.execute(
            "SELECT 1 FROM web_totp_factors WHERE account_id=? AND state='active' LIMIT 1",
            (account_id,),
        ).fetchone()
    )


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _now_text(value: datetime | None = None) -> str:
    return (value or _now()).isoformat(timespec="seconds")


def _future(value: Any, now: datetime | None = None) -> bool:
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return False
    if parsed.tzinfo is None:
        return False
    return parsed.astimezone(timezone.utc) > (now or _now())


def _opaque_token() -> str:
    return secrets.token_urlsafe(32)


def _token_hash(key: bytes, *, purpose: str, record_id: str, token: str) -> str:
    material = f"toan-aas/{purpose}/v1/{record_id}/{token}".encode("utf-8")
    return hmac.new(key, material, hashlib.sha256).hexdigest()


def _recovery_hash(key: bytes, *, factor_id: str, code: str) -> str:
    material = f"toan-aas/totp-recovery/v1/{factor_id}/{code}".encode("utf-8")
    return hmac.new(key, material, hashlib.sha256).hexdigest()


def _factor_aad(*, account_id: str, factor_id: str) -> bytes:
    return f"toan-aas/totp-factor/v1/{account_id}/{factor_id}".encode("utf-8")


def _encrypt_secret(key: bytes, *, account_id: str, factor_id: str, secret: bytes) -> str:
    nonce = secrets.token_bytes(12)
    encrypted = AESGCM(key).encrypt(nonce, secret, _factor_aad(account_id=account_id, factor_id=factor_id))
    return base64.urlsafe_b64encode(nonce + encrypted).decode("ascii").rstrip("=")


def _decrypt_secret(key: bytes, *, account_id: str, factor_id: str, ciphertext: str) -> bytes | None:
    try:
        encoded = str(ciphertext or "")
        raw = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        if len(raw) <= 12:
            return None
        secret = AESGCM(key).decrypt(
            raw[:12],
            raw[12:],
            _factor_aad(account_id=account_id, factor_id=factor_id),
        )
    except (ValueError, TypeError, binascii.Error, InvalidTag):
        return None
    return secret if len(secret) == TOTP_SECRET_BYTES else None


def _totp_code(secret: bytes, counter: int) -> str:
    digest = hmac.new(secret, int(counter).to_bytes(8, "big"), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = (
        ((digest[offset] & 0x7F) << 24)
        | (digest[offset + 1] << 16)
        | (digest[offset + 2] << 8)
        | digest[offset + 3]
    )
    return str(binary % (10 ** TOTP_DIGITS)).zfill(TOTP_DIGITS)


def _normalize_verification(value: Any) -> tuple[str, str] | None:
    code = str(value or "").strip().upper().replace(" ", "")
    if TOTP_CODE_PATTERN.fullmatch(code):
        return "totp", code
    if TOTP_RECOVERY_CODE_PATTERN.fullmatch(code):
        return "recovery", code
    return None


def _verify_totp(secret: bytes, supplied: str, *, last_counter: Any, now: datetime | None = None) -> int | None:
    current = int((now or _now()).timestamp()) // TOTP_PERIOD_SECONDS
    try:
        previous = int(last_counter) if last_counter is not None else -1
    except (TypeError, ValueError):
        previous = -1
    # Permit a one-period clock skew but never reuse a code already accepted
    # by this factor. The enrollment confirmation itself consumes a counter,
    # so the first login must use the next authenticator code.
    for counter in (current, current - 1, current + 1):
        if counter <= previous:
            continue
        if hmac.compare_digest(_totp_code(secret, counter), supplied):
            return counter
    return None


def _new_recovery_codes() -> list[str]:
    values: set[str] = set()
    while len(values) < TOTP_RECOVERY_CODE_COUNT:
        raw = "".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(8))
        values.add(f"{raw[:4]}-{raw[4:]}")
    return sorted(values)


def _safe_mfa_status(
    conn: Any,
    *,
    account_id: str,
    password_available: bool,
    configuration: dict[str, bytes] | None,
) -> dict[str, Any]:
    row = conn.execute(
        """SELECT id, state, enrollment_expires_at
           FROM web_totp_factors
           WHERE account_id=? AND state IN ('active', 'prepared')
           ORDER BY CASE state WHEN 'active' THEN 0 ELSE 1 END, updated_at DESC, id DESC
           LIMIT 1""",
        (account_id,),
    ).fetchone()
    active = bool(row and str(row[1]) == "active")
    pending = bool(
        row
        and str(row[1]) == "prepared"
        and _future(row[2])
    )
    remaining = 0
    if active:
        remaining_row = conn.execute(
            """SELECT COUNT(*) FROM web_totp_recovery_codes
               WHERE factor_id=? AND account_id=? AND used_at IS NULL AND invalidated_at IS NULL""",
            (str(row[0]), account_id),
        ).fetchone()
        remaining = max(0, int(remaining_row[0] if remaining_row else 0))
    return {
        "enabled": active,
        "pending_enrollment": pending,
        "runtime_available": configuration is not None,
        "password_factor_available": password_available,
        "recovery_codes_remaining": remaining,
    }


def _factor_row(conn: Any, *, factor_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, account_id, secret_ciphertext, enrollment_token_hash, state,
                  revision, enrollment_expires_at, enabled_at, disabled_at, last_counter
           FROM web_totp_factors
           WHERE id=? AND account_id=?""",
        (factor_id, account_id),
    ).fetchone()


def _valid_uuid(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if not TOTP_UUID_PATTERN.fullmatch(text):
        return None
    try:
        return str(uuid.UUID(text))
    except ValueError:
        return None


def create_password_login_challenge(conn: Any, *, account_id: str, now: str | None = None) -> dict[str, Any]:
    """Create one password-first, second-factor challenge in an open transaction."""

    configuration = _configuration()
    if configuration is None:
        raise RuntimeError("TOTP MFA is disabled")
    created_at = now or utc_now()
    challenge_id = str(uuid.uuid4())
    token = _opaque_token()
    expires_at = _now_text(_now() + timedelta(minutes=TOTP_LOGIN_CHALLENGE_TTL_MINUTES))
    conn.execute(
        """UPDATE web_totp_login_challenges
           SET state='superseded', updated_at=?
           WHERE account_id=? AND state='pending'""",
        (created_at, account_id),
    )
    conn.execute(
        """INSERT INTO web_totp_login_challenges
           (id, account_id, token_hash, state, attempt_count, expires_at, consumed_at, created_at, updated_at)
           VALUES (?, ?, ?, 'pending', 0, ?, NULL, ?, ?)""",
        (
            challenge_id,
            account_id,
            _token_hash(configuration["key"], purpose="totp-login", record_id=challenge_id, token=token),
            expires_at,
            created_at,
            created_at,
        ),
    )
    return {
        "mfa_required": True,
        "challenge_id": challenge_id,
        "challenge_token": token,
        "expires_in_minutes": TOTP_LOGIN_CHALLENGE_TTL_MINUTES,
        "method": "totp_or_recovery_code",
    }


class TotpEnrollmentStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=256)


class TotpEnrollmentConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factor_id: str = Field(min_length=36, max_length=36)
    enrollment_token: str = Field(min_length=32, max_length=160)
    code: str = Field(min_length=6, max_length=16)

    @field_validator("factor_id")
    @classmethod
    def _factor_id(cls, value: str) -> str:
        normalized = _valid_uuid(value)
        if not normalized:
            raise ValueError("Mã enrollment không hợp lệ")
        return normalized

    @field_validator("enrollment_token")
    @classmethod
    def _token(cls, value: str) -> str:
        normalized = value.strip()
        if not TOTP_OPAQUE_TOKEN_PATTERN.fullmatch(normalized):
            raise ValueError("Enrollment token không hợp lệ")
        return normalized

    @field_validator("code")
    @classmethod
    def _code(cls, value: str) -> str:
        normalized = _normalize_verification(value)
        if not normalized or normalized[0] != "totp":
            raise ValueError("Cần mã TOTP 6 chữ số")
        return normalized[1]


class TotpDisableRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=256)
    verification_code: str = Field(min_length=6, max_length=16)
    confirm: bool = False

    @field_validator("verification_code")
    @classmethod
    def _verification(cls, value: str) -> str:
        normalized = _normalize_verification(value)
        if not normalized:
            raise ValueError("Mã xác thực hai bước không hợp lệ")
        return normalized[1]


class TotpLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_id: str = Field(min_length=36, max_length=36)
    challenge_token: str = Field(min_length=32, max_length=160)
    code: str = Field(min_length=6, max_length=16)

    @field_validator("challenge_id")
    @classmethod
    def _challenge_id(cls, value: str) -> str:
        normalized = _valid_uuid(value)
        if not normalized:
            raise ValueError("Mã xác thực không hợp lệ")
        return normalized

    @field_validator("challenge_token")
    @classmethod
    def _challenge_token(cls, value: str) -> str:
        normalized = value.strip()
        if not TOTP_OPAQUE_TOKEN_PATTERN.fullmatch(normalized):
            raise ValueError("Mã xác thực không hợp lệ")
        return normalized

    @field_validator("code")
    @classmethod
    def _code(cls, value: str) -> str:
        normalized = _normalize_verification(value)
        if not normalized:
            raise ValueError("Mã xác thực hai bước không hợp lệ")
        return normalized[1]


def _mfa_guarded(message: str, code: str, *, status_name: str = "guarded") -> dict[str, Any]:
    return envelope(False, message, data={"mfa": {"execution": "web_native_totp_only"}}, status_name=status_name, error_code=code)


def _secure_response(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"


def _account_password_row(conn: Any, *, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, email, password_hash, display_name, canonical_user_id, role_cache,
                  is_active, password_login_enabled, locale, timezone, avatar_style
           FROM (
               SELECT a.id, a.email, a.password_hash, a.display_name, a.canonical_user_id,
                      a.role_cache, a.is_active, a.password_login_enabled,
                      p.locale, p.timezone, p.avatar_style
               FROM web_accounts a
               LEFT JOIN web_account_profiles p ON p.account_id=a.id
               WHERE a.id=?
           )""",
        (account_id,),
    ).fetchone()


def _account_public(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "email": str(row[1]),
        "display_name": str(row[3] or ""),
        "canonical_user_id": row[4],
        "role": str(row[5] or "user"),
        "password_login_enabled": bool(row[7]),
        "locale": str(row[8] or "vi"),
        "timezone": str(row[9] or "Asia/Ho_Chi_Minh"),
        "avatar_style": str(row[10] or "gradient"),
    }


def _verified_recovery_id(conn: Any, *, key: bytes, factor_id: str, account_id: str, supplied: str) -> str | None:
    digest = _recovery_hash(key, factor_id=factor_id, code=supplied)
    row = conn.execute(
        """SELECT id FROM web_totp_recovery_codes
           WHERE factor_id=? AND account_id=? AND code_hash=?
             AND used_at IS NULL AND invalidated_at IS NULL
           LIMIT 1""",
        (factor_id, account_id, digest),
    ).fetchone()
    return str(row[0]) if row else None


@router.get("/mfa/status")
async def mfa_status(account: dict = Depends(require_account)):
    """Return only a signed owner's factor posture, never a secret or factor id."""

    ensure_copyfast_schema()
    try:
        configuration = _configuration()
    except RuntimeError:
        configuration = None
    password_available = password_login_factor_available(
        str(account.get("email") or ""),
        bool(account.get("password_login_enabled")),
    )
    with read_transaction() as conn:
        status = _safe_mfa_status(
            conn,
            account_id=str(account["id"]),
            password_available=password_available,
            configuration=configuration,
        )
    if configuration is None:
        return envelope(
            True,
            "Xác thực hai bước đang tắt hoặc chưa có khóa mã hóa hợp lệ.",
            data={"mfa": status},
            status_name="guarded",
        )
    return envelope(
        True,
        "Đã tải trạng thái xác thực hai bước.",
        data={"mfa": status},
        status_name="read_only",
    )


@router.post("/mfa/enrollment/start")
async def start_totp_enrollment(
    payload: TotpEnrollmentStartRequest,
    request: Request,
    response: Response,
    account: dict = Depends(require_csrf),
):
    """Require a current password before returning one transient setup secret."""

    ensure_copyfast_schema()
    try:
        configuration = _configuration()
    except RuntimeError:
        configuration = None
    if configuration is None:
        return _mfa_guarded("Xác thực hai bước chưa được máy chủ bật an toàn.", "WEB_TOTP_MFA_UNAVAILABLE")
    session = current_session(request)
    account_id = str(account["id"])
    factor_id = str(uuid.uuid4())
    raw_secret = secrets.token_bytes(TOTP_SECRET_BYTES)
    setup_token = _opaque_token()
    now = utc_now()
    expires_at = _now_text(_now() + timedelta(minutes=TOTP_ENROLLMENT_TTL_MINUTES))
    created = False
    with transaction() as conn:
        if not _session_is_active_for_account(
            conn,
            session_id=str(session["session_id"]),
            account_id=account_id,
            now=now,
        ):
            return _mfa_guarded("Phiên bảo mật đã thay đổi. Hãy đăng nhập lại trước khi thiết lập.", "WEB_TOTP_MFA_SESSION_STALE")
        row = _account_password_row(conn, account_id=account_id)
        password_available = bool(
            row
            and bool(row[6])
            and password_login_factor_available(str(row[1]), bool(row[7]))
        )
        password_hash = str(row[2]) if password_available and row else _password_hash(secrets.token_urlsafe(24))
        password_valid = _verify_password(payload.current_password, password_hash)
        if not row or not password_available or not password_valid:
            _record_audit(
                conn,
                account_id=account_id,
                canonical_user_id=str(account.get("canonical_user_id") or "") or None,
                action="auth.mfa_enrollment_start",
                request_id=_request_id(request),
                outcome="denied",
            )
            return _mfa_guarded("Không thể xác minh mật khẩu hiện tại để thiết lập xác thực hai bước.", "WEB_TOTP_MFA_PASSWORD_DENIED", status_name="failed")
        if active_totp_factor_exists(conn, account_id=account_id):
            return _mfa_guarded("Tài khoản này đã bật xác thực hai bước.", "WEB_TOTP_MFA_ALREADY_ENABLED")
        conn.execute(
            """UPDATE web_totp_factors
               SET state='superseded', revision=revision+1, updated_at=?
               WHERE account_id=? AND state='prepared'""",
            (now, account_id),
        )
        conn.execute(
            """INSERT INTO web_totp_factors
               (id, account_id, secret_ciphertext, enrollment_token_hash, state, revision,
                enrollment_expires_at, enabled_at, disabled_at, last_counter, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'prepared', 1, ?, NULL, NULL, NULL, ?, ?)""",
            (
                factor_id,
                account_id,
                _encrypt_secret(
                    configuration["key"],
                    account_id=account_id,
                    factor_id=factor_id,
                    secret=raw_secret,
                ),
                _token_hash(
                    configuration["key"],
                    purpose="totp-enrollment",
                    record_id=factor_id,
                    token=setup_token,
                ),
                expires_at,
                now,
                now,
            ),
        )
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="auth.mfa_enrollment_start",
            request_id=_request_id(request),
            outcome="ok",
        )
        created = True
    if not created:
        return _mfa_guarded("Không thể khởi tạo xác thực hai bước.", "WEB_TOTP_MFA_START_FAILED")
    _secure_response(response)
    manual_key = base64.b32encode(raw_secret).decode("ascii").rstrip("=")
    return envelope(
        True,
        "Đã tạo mã thiết lập tạm thời. Thêm mã này vào ứng dụng xác thực rồi xác nhận bằng mã 6 số.",
        data={
            "mfa_enrollment": {
                "factor_id": factor_id,
                "enrollment_token": setup_token,
                "manual_key": manual_key,
                "issuer": "TOAN AAS",
                "account_label": str(account.get("email") or ""),
                "algorithm": "SHA1",
                "digits": TOTP_DIGITS,
                "period_seconds": TOTP_PERIOD_SECONDS,
                "expires_in_minutes": TOTP_ENROLLMENT_TTL_MINUTES,
            }
        },
        status_name="awaiting_confirm",
    )


@router.post("/mfa/enrollment/confirm")
async def confirm_totp_enrollment(
    payload: TotpEnrollmentConfirmRequest,
    request: Request,
    response: Response,
    account: dict = Depends(require_csrf),
):
    """Activate a prepared factor only after a fresh authenticator proof."""

    ensure_copyfast_schema()
    try:
        configuration = _configuration()
    except RuntimeError:
        configuration = None
    if configuration is None:
        return _mfa_guarded("Xác thực hai bước chưa được máy chủ bật an toàn.", "WEB_TOTP_MFA_UNAVAILABLE")
    session = current_session(request)
    account_id = str(account["id"])
    now_value = _now()
    now = _now_text(now_value)
    recovery_codes: list[str] = []
    with transaction() as conn:
        if not _session_is_active_for_account(
            conn,
            session_id=str(session["session_id"]),
            account_id=account_id,
            now=now,
        ):
            return _mfa_guarded("Phiên bảo mật đã thay đổi. Hãy bắt đầu lại thiết lập.", "WEB_TOTP_MFA_SESSION_STALE")
        factor = _factor_row(conn, factor_id=payload.factor_id, account_id=account_id)
        expected = (
            _token_hash(
                configuration["key"],
                purpose="totp-enrollment",
                record_id=payload.factor_id,
                token=payload.enrollment_token,
            )
            if factor
            else ""
        )
        valid_prepared = bool(
            factor
            and str(factor[4]) == "prepared"
            and _future(factor[6], now_value)
            and hmac.compare_digest(str(factor[3]), expected)
        )
        secret = (
            _decrypt_secret(
                configuration["key"],
                account_id=account_id,
                factor_id=str(factor[0]),
                ciphertext=str(factor[2]),
            )
            if valid_prepared and factor
            else None
        )
        counter = _verify_totp(secret, payload.code, last_counter=None, now=now_value) if secret else None
        if counter is None:
            _record_audit(
                conn,
                account_id=account_id,
                canonical_user_id=str(account.get("canonical_user_id") or "") or None,
                action="auth.mfa_enrollment_confirm",
                request_id=_request_id(request),
                outcome="denied",
            )
            return _mfa_guarded("Mã xác thực hai bước không hợp lệ hoặc thiết lập đã hết hạn.", "WEB_TOTP_MFA_ENROLLMENT_DENIED", status_name="failed")
        changed = conn.execute(
            """UPDATE web_totp_factors
               SET state='active', enrollment_token_hash='', enrollment_expires_at=NULL,
                   enabled_at=?, last_counter=?, revision=revision+1, updated_at=?
               WHERE id=? AND account_id=? AND state='prepared'""",
            (now, counter, now, payload.factor_id, account_id),
        )
        if changed.rowcount != 1:
            return _mfa_guarded("Thiết lập xác thực hai bước đã được thay đổi. Hãy tải lại trạng thái.", "WEB_TOTP_MFA_ENROLLMENT_STALE")
        recovery_codes = _new_recovery_codes()
        for code in recovery_codes:
            conn.execute(
                """INSERT INTO web_totp_recovery_codes
                   (id, factor_id, account_id, code_hash, created_at, used_at, invalidated_at)
                   VALUES (?, ?, ?, ?, ?, NULL, NULL)""",
                (
                    str(uuid.uuid4()),
                    payload.factor_id,
                    account_id,
                    _recovery_hash(configuration["key"], factor_id=payload.factor_id, code=code),
                    now,
                ),
            )
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="auth.mfa_enrollment_confirm",
            request_id=_request_id(request),
            outcome="ok",
        )
    _secure_response(response)
    return envelope(
        True,
        "Đã bật xác thực hai bước. Lưu các mã khôi phục ngay; chúng chỉ được hiển thị lần này.",
        data={
            "mfa": {
                "enabled": True,
                "pending_enrollment": False,
                "runtime_available": True,
                "recovery_codes_remaining": len(recovery_codes),
            },
            "recovery_codes": recovery_codes,
        },
        status_name="completed",
    )


@router.post("/mfa/disable")
async def disable_totp(
    payload: TotpDisableRequest,
    request: Request,
    response: Response,
    account: dict = Depends(require_csrf),
):
    """Disable a factor only with current password plus TOTP or recovery proof."""

    ensure_copyfast_schema()
    try:
        configuration = _configuration()
    except RuntimeError:
        configuration = None
    if configuration is None:
        return _mfa_guarded("Xác thực hai bước chưa được máy chủ bật an toàn.", "WEB_TOTP_MFA_UNAVAILABLE")
    if not payload.confirm:
        return _mfa_guarded("Cần xác nhận rõ ràng trước khi tắt xác thực hai bước.", "WEB_TOTP_MFA_CONFIRM_REQUIRED")
    session = current_session(request)
    account_id = str(account["id"])
    now_value = _now()
    now = _now_text(now_value)
    replacement: dict[str, str] | None = None
    with transaction() as conn:
        if not _session_is_active_for_account(
            conn,
            session_id=str(session["session_id"]),
            account_id=account_id,
            now=now,
        ):
            return _mfa_guarded("Phiên bảo mật đã thay đổi. Hãy đăng nhập lại trước khi tiếp tục.", "WEB_TOTP_MFA_SESSION_STALE")
        account_row = _account_password_row(conn, account_id=account_id)
        password_available = bool(
            account_row
            and bool(account_row[6])
            and password_login_factor_available(str(account_row[1]), bool(account_row[7]))
        )
        password_hash = str(account_row[2]) if password_available and account_row else _password_hash(secrets.token_urlsafe(24))
        password_valid = _verify_password(payload.current_password, password_hash)
        factor_row = conn.execute(
            """SELECT id, account_id, secret_ciphertext, enrollment_token_hash, state,
                      revision, enrollment_expires_at, enabled_at, disabled_at, last_counter
               FROM web_totp_factors
               WHERE account_id=? AND state='active'
               ORDER BY updated_at DESC, id DESC LIMIT 1""",
            (account_id,),
        ).fetchone()
        normalized = _normalize_verification(payload.verification_code)
        valid_factor = False
        recovery_id: str | None = None
        next_counter: int | None = None
        if password_valid and factor_row and normalized:
            factor_id = str(factor_row[0])
            if normalized[0] == "totp":
                secret = _decrypt_secret(
                    configuration["key"],
                    account_id=account_id,
                    factor_id=factor_id,
                    ciphertext=str(factor_row[2]),
                )
                next_counter = _verify_totp(
                    secret,
                    normalized[1],
                    last_counter=factor_row[9],
                    now=now_value,
                ) if secret else None
                valid_factor = next_counter is not None
            else:
                recovery_id = _verified_recovery_id(
                    conn,
                    key=configuration["key"],
                    factor_id=factor_id,
                    account_id=account_id,
                    supplied=normalized[1],
                )
                valid_factor = recovery_id is not None
        if not valid_factor or not account_row:
            _record_audit(
                conn,
                account_id=account_id,
                canonical_user_id=str(account.get("canonical_user_id") or "") or None,
                action="auth.mfa_disable",
                request_id=_request_id(request),
                outcome="denied",
            )
            return _mfa_guarded("Không thể xác minh yêu cầu tắt xác thực hai bước.", "WEB_TOTP_MFA_DISABLE_DENIED", status_name="failed")
        factor_id = str(factor_row[0])
        changed = conn.execute(
            """UPDATE web_totp_factors
               SET state='disabled', disabled_at=?, last_counter=COALESCE(?, last_counter),
                   revision=revision+1, updated_at=?
               WHERE id=? AND account_id=? AND state='active'""",
            (now, next_counter, now, factor_id, account_id),
        )
        if changed.rowcount != 1:
            return _mfa_guarded("Trạng thái xác thực hai bước đã thay đổi. Hãy tải lại.", "WEB_TOTP_MFA_DISABLE_STALE")
        if recovery_id:
            conn.execute(
                """UPDATE web_totp_recovery_codes
                   SET used_at=?
                   WHERE id=? AND factor_id=? AND account_id=? AND used_at IS NULL AND invalidated_at IS NULL""",
                (now, recovery_id, factor_id, account_id),
            )
        conn.execute(
            """UPDATE web_totp_recovery_codes
               SET invalidated_at=COALESCE(invalidated_at, ?)
               WHERE factor_id=? AND account_id=?""",
            (now, factor_id, account_id),
        )
        replacement = _rotate_account_sessions(conn, account_id, now=now)
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="auth.mfa_disable",
            request_id=_request_id(request),
            outcome="ok",
        )
    if not replacement:
        return _mfa_guarded("Không thể cập nhật phiên bảo mật sau khi tắt xác thực hai bước.", "WEB_TOTP_MFA_DISABLE_FAILED")
    _set_session_cookie(response, replacement["session_id"])
    _secure_response(response)
    return envelope(
        True,
        "Đã tắt xác thực hai bước và làm mới signed session. Các mã khôi phục cũ không còn dùng được.",
        data={
            "mfa": {
                "enabled": False,
                "pending_enrollment": False,
                "runtime_available": True,
                "recovery_codes_remaining": 0,
            },
            "csrf_token": replacement["csrf_token"],
            "expires_at": replacement["expires_at"],
        },
        status_name="completed",
    )


@router.post("/login/mfa")
async def complete_mfa_login(payload: TotpLoginRequest, request: Request, response: Response):
    """Finish a password-first login after a single TOTP/recovery proof."""

    ensure_copyfast_schema()
    try:
        configuration = _configuration()
    except RuntimeError:
        configuration = None
    if configuration is None:
        return _mfa_guarded("Xác thực hai bước đang tạm không khả dụng. Không có phiên nào được tạo.", "WEB_TOTP_MFA_UNAVAILABLE")
    now_value = _now()
    now = _now_text(now_value)
    session_payload: dict[str, str] | None = None
    account_payload: dict[str, Any] | None = None
    with transaction() as conn:
        challenge = conn.execute(
            """SELECT id, account_id, token_hash, state, attempt_count, expires_at
               FROM web_totp_login_challenges WHERE id=?""",
            (payload.challenge_id,),
        ).fetchone()
        expected = (
            _token_hash(
                configuration["key"],
                purpose="totp-login",
                record_id=payload.challenge_id,
                token=payload.challenge_token,
            )
            if challenge
            else ""
        )
        valid_challenge = bool(
            challenge
            and str(challenge[3]) == "pending"
            and int(challenge[4]) < TOTP_LOGIN_MAX_ATTEMPTS
            and _future(challenge[5], now_value)
            and hmac.compare_digest(str(challenge[2]), expected)
        )
        if not valid_challenge:
            return _mfa_guarded("Mã xác thực hai bước không còn hợp lệ. Hãy đăng nhập lại từ đầu.", "WEB_TOTP_MFA_LOGIN_CHALLENGE_INVALID", status_name="failed")
        account_id = str(challenge[1])
        account_row = _account_password_row(conn, account_id=account_id)
        factor = conn.execute(
            """SELECT id, account_id, secret_ciphertext, enrollment_token_hash, state,
                      revision, enrollment_expires_at, enabled_at, disabled_at, last_counter
               FROM web_totp_factors
               WHERE account_id=? AND state='active'
               ORDER BY updated_at DESC, id DESC LIMIT 1""",
            (account_id,),
        ).fetchone()
        normalized = _normalize_verification(payload.code)
        accepted_counter: int | None = None
        recovery_id: str | None = None
        accepted = False
        if account_row and bool(account_row[6]) and factor and normalized:
            factor_id = str(factor[0])
            if normalized[0] == "totp":
                secret = _decrypt_secret(
                    configuration["key"],
                    account_id=account_id,
                    factor_id=factor_id,
                    ciphertext=str(factor[2]),
                )
                accepted_counter = _verify_totp(
                    secret,
                    normalized[1],
                    last_counter=factor[9],
                    now=now_value,
                ) if secret else None
                accepted = accepted_counter is not None
            else:
                recovery_id = _verified_recovery_id(
                    conn,
                    key=configuration["key"],
                    factor_id=factor_id,
                    account_id=account_id,
                    supplied=normalized[1],
                )
                accepted = recovery_id is not None
        if not accepted:
            attempts = min(TOTP_LOGIN_MAX_ATTEMPTS, int(challenge[4]) + 1)
            state = "locked" if attempts >= TOTP_LOGIN_MAX_ATTEMPTS else "pending"
            conn.execute(
                """UPDATE web_totp_login_challenges
                   SET attempt_count=?, state=?, updated_at=?
                   WHERE id=? AND state='pending'""",
                (attempts, state, now, payload.challenge_id),
            )
            _record_audit(
                conn,
                account_id=account_id,
                canonical_user_id=str(account_row[4]) if account_row and account_row[4] else None,
                action="auth.mfa_login",
                request_id=_request_id(request),
                outcome="denied",
            )
            return _mfa_guarded("Mã xác thực hai bước không đúng hoặc đã dùng. Hãy thử lại hoặc đăng nhập lại.", "WEB_TOTP_MFA_LOGIN_DENIED", status_name="failed")
        factor_id = str(factor[0])
        if accepted_counter is not None:
            changed_factor = conn.execute(
                """UPDATE web_totp_factors
                   SET last_counter=?, revision=revision+1, updated_at=?
                   WHERE id=? AND account_id=? AND state='active'
                     AND (last_counter IS NULL OR last_counter<?)""",
                (accepted_counter, now, factor_id, account_id, accepted_counter),
            )
            if changed_factor.rowcount != 1:
                return _mfa_guarded("Mã xác thực hai bước vừa được dùng. Hãy chờ mã mới.", "WEB_TOTP_MFA_CODE_REPLAYED", status_name="failed")
        if recovery_id:
            changed_recovery = conn.execute(
                """UPDATE web_totp_recovery_codes
                   SET used_at=?
                   WHERE id=? AND factor_id=? AND account_id=? AND used_at IS NULL AND invalidated_at IS NULL""",
                (now, recovery_id, factor_id, account_id),
            )
            if changed_recovery.rowcount != 1:
                return _mfa_guarded("Mã khôi phục vừa được dùng. Hãy đăng nhập lại.", "WEB_TOTP_MFA_RECOVERY_REPLAYED", status_name="failed")
        consumed = conn.execute(
            """UPDATE web_totp_login_challenges
               SET state='consumed', consumed_at=?, updated_at=?
               WHERE id=? AND state='pending'""",
            (now, now, payload.challenge_id),
        )
        if consumed.rowcount != 1:
            return _mfa_guarded("Phiên xác thực đã thay đổi. Hãy đăng nhập lại.", "WEB_TOTP_MFA_LOGIN_STALE", status_name="failed")
        session_payload = _insert_session(conn, account_id, now=now)
        account_payload = _account_public(account_row)
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=str(account_row[4]) if account_row[4] else None,
            action="auth.mfa_login",
            request_id=_request_id(request),
            outcome="ok",
        )
    if not session_payload or not account_payload:
        return _mfa_guarded("Không thể hoàn tất xác thực hai bước.", "WEB_TOTP_MFA_LOGIN_FAILED")
    _set_session_cookie(response, session_payload["session_id"])
    _secure_response(response)
    return envelope(
        True,
        "Đăng nhập và xác thực hai bước thành công.",
        data={
            "account": browser_account_payload(account_payload),
            "csrf_token": session_payload["csrf_token"],
            "expires_at": session_payload["expires_at"],
        },
        status_name="completed",
    )
