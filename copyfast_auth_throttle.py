"""Durable, privacy-preserving throttles for password credential attempts.

This module deliberately owns only a small Web session-database counter.  It
does not authenticate a request, change account state, call a provider, or
store a raw email address, forwarded address, password, session identifier,
or request payload.  The existing in-process gate in :mod:`app` remains a
cheap pre-parse flood control; this counter adds an atomic, restart-safe
second gate after FastAPI has bounded and validated credential fields.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import hmac
import ipaddress
import os
from pathlib import Path
import sqlite3
import time
from typing import Iterator

from fastapi import Request

from copyfast_db import session_database_path, utc_now


_ACTIONS = frozenset({"login", "register", "password_change"})
# The client bucket keeps one noisy network/browser from consuming every
# attempt available to a shared address.  The email-global bucket below is a
# separate HMAC-only scope that closes the inverse bypass: an attacker cannot
# reset a target account's password-guess budget by rotating client addresses.
_CLIENT_DEFAULTS = {
    "login": (20, 15 * 60),
    "register": (8, 60 * 60),
    # A signed session + CSRF are required before this bucket is consumed,
    # but the bounded durable counter still protects a stolen session from
    # unlimited current-password guessing.
    "password_change": (8, 15 * 60),
}
_GLOBAL_DEFAULTS = {
    # These are deliberately higher than the per-client values, but still
    # bound a distributed guess against one address.  They reset naturally;
    # the throttle is not a permanent account lockout mechanism.
    "login": (40, 15 * 60),
    "register": (16, 60 * 60),
    "password_change": (16, 15 * 60),
}
_MIN_WINDOW_SECONDS = 60
_MAX_WINDOW_SECONDS = 24 * 60 * 60
_MIN_ATTEMPTS = 1
_MAX_ATTEMPTS = 100
_MIN_GLOBAL_ATTEMPTS = 2
_MAX_GLOBAL_ATTEMPTS = 200
_DEFAULT_DB_TIMEOUT_SECONDS = 0.20
_MAX_DB_TIMEOUT_SECONDS = 0.50


@dataclass(frozen=True)
class ThrottleDecision:
    """The only result exposed to the route wrapper.

    ``reason`` is an internal fixed value, never a database exception or
    customer-controlled identifier.  It lets the wrapper select a stable,
    non-enumerating response without leaking persistence diagnostics.
    """

    allowed: bool
    retry_after_seconds: int
    reason: str


def normalize_email(value: str) -> str:
    """Match the password routes' conservative account lookup normalization."""

    return str(value or "").strip().lower()


def _positive_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return min(max(value, minimum), maximum)


def policy_for(action: str) -> tuple[int, int]:
    """Return the bounded per-client ``(attempt_limit, window_seconds)``."""

    if action not in _ACTIONS:
        raise ValueError("Unsupported auth throttle action")
    default_limit, default_window = _CLIENT_DEFAULTS[action]
    prefix = f"WEBAPP_AUTH_{action.upper()}_THROTTLE_"
    return (
        _positive_int(f"{prefix}LIMIT", default_limit, minimum=_MIN_ATTEMPTS, maximum=_MAX_ATTEMPTS),
        _positive_int(f"{prefix}WINDOW_SECONDS", default_window, minimum=_MIN_WINDOW_SECONDS, maximum=_MAX_WINDOW_SECONDS),
    )


def global_policy_for(action: str) -> tuple[int, int]:
    """Return the bounded cross-client policy for one HMACed email address.

    It deliberately has a separate namespace from ``policy_for``.  An
    operator can tune a temporary incident response without weakening the
    local/client bucket, but cannot configure an unbounded global window.
    """

    if action not in _ACTIONS:
        raise ValueError("Unsupported auth throttle action")
    default_limit, default_window = _GLOBAL_DEFAULTS[action]
    prefix = f"WEBAPP_AUTH_{action.upper()}_GLOBAL_THROTTLE_"
    return (
        _positive_int(
            f"{prefix}LIMIT",
            default_limit,
            minimum=_MIN_GLOBAL_ATTEMPTS,
            maximum=_MAX_GLOBAL_ATTEMPTS,
        ),
        _positive_int(
            f"{prefix}WINDOW_SECONDS",
            default_window,
            minimum=_MIN_WINDOW_SECONDS,
            maximum=_MAX_WINDOW_SECONDS,
        ),
    )


def _secret() -> bytes | None:
    """Return a domain-separated HMAC root without exposing its value.

    The dedicated secret is optional so existing deployments can inherit the
    already-required session secret.  The purpose labels below prevent reuse
    of the raw root as a direct database key or a browser-visible value.
    """

    configured = os.environ.get("WEBAPP_AUTH_THROTTLE_HMAC_SECRET", "").strip()
    fallback = os.environ.get("WEB_SESSION_SECRET", "").strip()
    value = configured or fallback
    return value.encode("utf-8") if value else None


def _hmac_digest(purpose: str, value: str) -> str | None:
    secret = _secret()
    if secret is None:
        return None
    try:
        material = f"toan-aas/auth-throttle/v1/{purpose}\x00{value}".encode("utf-8")
    except UnicodeEncodeError:
        # A malformed Unicode scalar is not a reason to expose a 500 or to
        # write an alternate raw representation.  The route fails closed.
        return None
    return hmac.new(secret, material, hashlib.sha256).hexdigest()


def email_fingerprint(value: str) -> str | None:
    """One-way stable key for a normalized email; never return/store plaintext."""

    return _hmac_digest("email", normalize_email(value))


def email_global_scope_fingerprint(action: str, email_hmac: str) -> str | None:
    """Return an internal HMAC-only scope shared by every client of an email.

    The existing additive table's third key column is intentionally reused
    for this domain-separated sentinel rather than changing its composite
    primary key on a live SQLite database.  It is another opaque HMAC digest,
    not the literal ``global`` marker, raw email, or client address.
    """

    if action not in _ACTIONS or len(email_hmac) != 64:
        return None
    return _hmac_digest("email-global-scope", f"{action}\x00{email_hmac}")


def _trusted_proxy_networks() -> tuple[ipaddress._BaseNetwork, ...]:
    """Parse only an explicit restrictive proxy allowlist.

    A malformed item invalidates the whole setting rather than partially
    trusting an operator typo.  With no valid allowlist, spoofable forwarded
    headers are ignored and the direct ASGI peer remains the scoped signal.
    """

    raw = os.environ.get("WEBAPP_AUTH_TRUSTED_PROXY_CIDRS", "").strip()
    if not raw:
        return ()
    values = [item.strip() for item in raw.split(",") if item.strip()]
    if not values:
        return ()
    try:
        networks = tuple(ipaddress.ip_network(value, strict=False) for value in values)
    except ValueError:
        return ()
    # Do not let a configuration such as 0.0.0.0/0 turn every direct peer
    # into a trusted proxy.  /8 IPv4 and /32 IPv6 are still broad enough for
    # real private/managed proxy ranges while rejecting accidental internet
    # catch-alls.  Operators can list multiple exact ranges when necessary.
    if any(
        network.prefixlen < (8 if network.version == 4 else 32)
        for network in networks
    ):
        return ()
    return networks


def _direct_peer(request: Request) -> ipaddress._BaseAddress | None:
    candidate = str(request.client.host) if request.client and request.client.host else ""
    try:
        return ipaddress.ip_address(candidate)
    except ValueError:
        return None


def _forwarded_client(request: Request, peer: ipaddress._BaseAddress | None) -> ipaddress._BaseAddress | None:
    """Accept X-Forwarded-For only from a directly trusted peer."""

    if peer is None or not any(peer in network for network in _trusted_proxy_networks()):
        return None
    raw_header = request.headers.get("x-forwarded-for", "")
    # Keep parser work bounded and reject an invalid chain rather than falling
    # back to a selectively attacker-chosen value.
    if not raw_header or len(raw_header) > 512:
        return None
    candidate = raw_header.split(",", 1)[0].strip()
    try:
        return ipaddress.ip_address(candidate)
    except ValueError:
        return None


def client_scope_fingerprint(request: Request) -> str | None:
    """HMAC the effective client address; raw address never leaves this call."""

    peer = _direct_peer(request)
    effective = _forwarded_client(request, peer) or peer
    # A missing ASGI peer must stay deterministic, not generate unbounded
    # process-local identities.  Its literal is HMACed before persistence.
    scope = str(effective) if effective is not None else "unknown"
    return _hmac_digest("client-scope", scope)


def _db_timeout_seconds() -> float:
    raw = os.environ.get("WEBAPP_AUTH_THROTTLE_DB_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return _DEFAULT_DB_TIMEOUT_SECONDS
    try:
        parsed = float(raw)
    except ValueError:
        return _DEFAULT_DB_TIMEOUT_SECONDS
    return min(max(parsed, 0.01), _MAX_DB_TIMEOUT_SECONDS)


@contextmanager
def _short_write_transaction() -> Iterator[sqlite3.Connection]:
    """Acquire the durable counter lock promptly or let the caller fail closed."""

    path = session_database_path()
    parent = Path(path).expanduser().resolve().parent
    parent.mkdir(parents=True, exist_ok=True)
    timeout = _db_timeout_seconds()
    connection = sqlite3.connect(path, timeout=timeout)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute(f"PRAGMA busy_timeout={max(1, int(timeout * 1000))}")
    try:
        connection.execute("BEGIN IMMEDIATE")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _bucket_row(
    conn: sqlite3.Connection,
    *,
    action: str,
    email_hmac: str,
    scope_hmac: str,
    now: int,
) -> tuple[int, int] | None:
    """Return ``(attempts, expires_at_epoch)`` for one current opaque bucket."""

    row = conn.execute(
        """SELECT attempts, expires_at_epoch
           FROM web_auth_throttle_buckets
           WHERE action=? AND email_hmac=? AND client_scope_hmac=?""",
        (action, email_hmac, scope_hmac),
    ).fetchone()
    if row is None or int(row[1]) <= now:
        return None
    return int(row[0]), int(row[1])


def _consume_bucket(
    conn: sqlite3.Connection,
    *,
    action: str,
    email_hmac: str,
    scope_hmac: str,
    row: tuple[int, int] | None,
    now: int,
    window_seconds: int,
) -> None:
    """Consume an already-authorized opaque bucket inside the caller lock."""

    if row is None:
        conn.execute(
            """INSERT INTO web_auth_throttle_buckets
            (action, email_hmac, client_scope_hmac, attempts, window_started_at, expires_at_epoch, updated_at)
            VALUES (?, ?, ?, 1, ?, ?, ?)
            ON CONFLICT(action, email_hmac, client_scope_hmac) DO UPDATE SET
                attempts=excluded.attempts,
                window_started_at=excluded.window_started_at,
                expires_at_epoch=excluded.expires_at_epoch,
                updated_at=excluded.updated_at""",
            (action, email_hmac, scope_hmac, now, now + window_seconds, utc_now()),
        )
        return
    conn.execute(
        """UPDATE web_auth_throttle_buckets
           SET attempts=attempts+1, updated_at=?
           WHERE action=? AND email_hmac=? AND client_scope_hmac=?""",
        (utc_now(), action, email_hmac, scope_hmac),
    )


def consume_fingerprints(
    *,
    action: str,
    email_hmac: str,
    client_scope_hmac: str,
    now_epoch: int | None = None,
) -> ThrottleDecision:
    """Atomically consume one durable credential-attempt slot.

    Callers provide HMAC values only.  The SQLite ``BEGIN IMMEDIATE`` lock
    serializes concurrent worker/replica attempts, and no in-memory state is
    involved, so a normal process restart cannot reset the bucket.
    """

    global_scope_hmac = email_global_scope_fingerprint(action, email_hmac)
    if (
        action not in _ACTIONS
        or len(email_hmac) != 64
        or len(client_scope_hmac) != 64
        or global_scope_hmac is None
        or hmac.compare_digest(global_scope_hmac, client_scope_hmac)
    ):
        return ThrottleDecision(False, 60, "unavailable")
    client_limit, client_window_seconds = policy_for(action)
    global_limit, global_window_seconds = global_policy_for(action)
    now = int(time.time() if now_epoch is None else now_epoch)
    try:
        with _short_write_transaction() as conn:
            # Expiry is indexed in the additive schema.  This removes old
            # one-way keys while preserving the current atomic transaction.
            conn.execute("DELETE FROM web_auth_throttle_buckets WHERE expires_at_epoch<=?", (now,))
            # Both buckets are loaded and consumed under the *same* short
            # BEGIN IMMEDIATE transaction.  A rotating client cannot race a
            # shared-email budget, and an exhausted global budget never
            # increments arbitrary client rows.
            global_row = _bucket_row(
                conn, action=action, email_hmac=email_hmac, scope_hmac=global_scope_hmac, now=now,
            )
            client_row = _bucket_row(
                conn, action=action, email_hmac=email_hmac, scope_hmac=client_scope_hmac, now=now,
            )
            if global_row is not None and global_row[0] >= global_limit:
                retry_after = max(1, min(_MAX_WINDOW_SECONDS, global_row[1] - now))
                return ThrottleDecision(False, retry_after, "limited")
            if client_row is not None and client_row[0] >= client_limit:
                retry_after = max(1, min(_MAX_WINDOW_SECONDS, client_row[1] - now))
                return ThrottleDecision(False, retry_after, "limited")
            _consume_bucket(
                conn,
                action=action,
                email_hmac=email_hmac,
                scope_hmac=global_scope_hmac,
                row=global_row,
                now=now,
                window_seconds=global_window_seconds,
            )
            _consume_bucket(
                conn,
                action=action,
                email_hmac=email_hmac,
                scope_hmac=client_scope_hmac,
                row=client_row,
                now=now,
                window_seconds=client_window_seconds,
            )
            return ThrottleDecision(True, 0, "allowed")
    except (OSError, sqlite3.Error, ValueError):
        # Never expose disk paths, SQLite errors, or raw request identity.
        # The route turns this into a small public 503 guard.
        return ThrottleDecision(False, 60, "unavailable")


def consume(request: Request, *, action: str, email: str) -> ThrottleDecision:
    """Fingerprint a bounded validated credential request and consume a slot."""

    email_hmac = email_fingerprint(email)
    client_hmac = client_scope_fingerprint(request)
    if email_hmac is None or client_hmac is None:
        return ThrottleDecision(False, 60, "unavailable")
    return consume_fingerprints(action=action, email_hmac=email_hmac, client_scope_hmac=client_hmac)
