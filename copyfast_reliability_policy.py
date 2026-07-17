"""Pure policy helpers for Web Runtime Reliability Follow-up.

The follow-up feature is intentionally observation-only.  It accepts no raw
request data, stores no diagnostic text and does not decide or perform a
repair.  This module has no database, network, environment, logging, Bot,
provider, wallet, payment or deployment dependency so the API layer can use
one deterministic policy for every request.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


FIVE_MINUTE_BUCKET_MINUTES = 5
UNEXPECTED_5XX = "unexpected_5xx"

# Only these Web-owned private API families may become aggregate reliability
# signals.  The value is a fixed label, never a raw route or request value.
# Keep this closed list deliberately small.  New execution/integration routes
# require an explicit policy review before they can be observed here.
WEB_NATIVE_ROUTE_FAMILIES: tuple[tuple[str, str], ...] = (
    ("/api/v1/analytics-workspace", "analytics_workspace"),
    ("/api/v1/asset-vault", "asset_vault"),
    ("/api/v1/chat-workspace", "chat_workspace"),
    ("/api/v1/content-studio", "content_studio"),
    ("/api/v1/document-operations", "document_operations"),
    ("/api/v1/document-workspace", "document_workspace"),
    ("/api/v1/image-operations", "image_operations"),
    ("/api/v1/image-studio", "image_studio"),
    ("/api/v1/inbox", "notification_inbox"),
    ("/api/v1/media-workspace", "media_workspace"),
    ("/api/v1/memory", "memory_center"),
    ("/api/v1/projects", "projects"),
    ("/api/v1/prompt-library", "prompt_library"),
    ("/api/v1/subtitle-studio", "subtitle_studio"),
    ("/api/v1/support/cases", "support_desk"),
    ("/api/v1/support/events", "support_desk"),
    ("/api/v1/support/summary", "support_desk"),
    ("/api/v1/video-studio", "video_studio"),
    ("/api/v1/voice-studio", "voice_studio"),
    ("/api/v1/workboard", "workboard"),
)
ROUTE_FAMILY_NAMES = frozenset(family for _, family in WEB_NATIVE_ROUTE_FAMILIES)

# These are checked before the allowlist to protect against accidentally
# widening a prefix later.  It also means ``/api/v1/support/admin/...`` never
# inherits the customer Support Desk family.
EXCLUDED_PATH_SEGMENTS = frozenset({"admin", "auth", "bridge", "internal", "payments", "wallet"})

FOLLOWUP_SOURCE_KINDS = frozenset({"runtime_signal", "support_triage"})
FOLLOWUP_STATES = frozenset({"open", "acknowledged", "resolved", "superseded"})
FOLLOWUP_SEVERITIES = frozenset({"low", "medium", "high", "critical"})
# This is metadata validation only.  Actual authorization must continue to
# use the canonical, signed-account checks at the API boundary.
FOLLOWUP_REQUIRED_ROLES = frozenset({"operator", "manager"})
FOLLOWUP_EVENT_ACTIONS = frozenset({"opened", "acknowledged", "resolved", "superseded"})

DEFAULT_SIGNAL_THRESHOLD = 3
MIN_SIGNAL_THRESHOLD = 1
MAX_SIGNAL_THRESHOLD = 1_000


def normalize_route_family(path: Any) -> str | None:
    """Return a fixed family label only for an exact allowed private route.

    The function intentionally rejects query/hash fragments, encoded paths,
    repeated separators and all excluded control-plane segments rather than
    attempting a permissive URL normalization.  Returning ``None`` means no
    reliability signal may be recorded for that request.
    """
    if not isinstance(path, str):
        return None
    candidate = path.strip()
    if (
        not candidate
        or len(candidate) > 512
        or not candidate.startswith("/")
        or "?" in candidate
        or "#" in candidate
        or "\\" in candidate
        or "%" in candidate
        or "//" in candidate
    ):
        return None
    parts = tuple(part for part in candidate.split("/") if part)
    if not parts or any(part in EXCLUDED_PATH_SEGMENTS for part in parts):
        return None
    for prefix, family in WEB_NATIVE_ROUTE_FAMILIES:
        if candidate == prefix or candidate.startswith(prefix + "/"):
            return family
    return None


def valid_route_family(value: Any) -> bool:
    """Whether a persisted family is one of this module's fixed labels."""
    return isinstance(value, str) and value in ROUTE_FAMILY_NAMES


def signal_code_for_status(status_code: Any) -> str | None:
    """Return the sole sanitized signal code for an HTTP 5xx response.

    Neither a status sub-code nor exception type/message is retained.  This
    prevents the reliability record from becoming a second diagnostic log.
    """
    if isinstance(status_code, bool):
        return None
    try:
        numeric_status = int(status_code)
    except (TypeError, ValueError):
        return None
    return UNEXPECTED_5XX if 500 <= numeric_status <= 599 else None


def sanitize_signal_code(_: Any = None) -> str:
    """Return the only signal label permitted in Runtime Follow-up records."""
    return UNEXPECTED_5XX


def utc_five_minute_bucket(moment: datetime) -> datetime:
    """Floor an aware timestamp to its UTC five-minute aggregation bucket."""
    if not isinstance(moment, datetime) or moment.tzinfo is None:
        raise ValueError("Runtime signal timestamp phải là datetime có timezone")
    utc_moment = moment.astimezone(timezone.utc)
    minute = (utc_moment.minute // FIVE_MINUTE_BUCKET_MINUTES) * FIVE_MINUTE_BUCKET_MINUTES
    return utc_moment.replace(minute=minute, second=0, microsecond=0)


def utc_five_minute_bucket_key(moment: datetime) -> str:
    """Return the stable UTC ISO representation used when creating a bucket."""
    return utc_five_minute_bucket(moment).isoformat(timespec="seconds")


def parse_signal_threshold(
    value: Any,
    *,
    default: int = DEFAULT_SIGNAL_THRESHOLD,
    minimum: int = MIN_SIGNAL_THRESHOLD,
    maximum: int = MAX_SIGNAL_THRESHOLD,
) -> int | None:
    """Parse one bounded threshold without reading configuration itself.

    ``None``/an empty string means use the caller-provided default.  Invalid
    or out-of-range explicit values return ``None`` so a configuration layer
    can guard rather than silently enabling an unexpected threshold.
    """
    if isinstance(default, bool) or isinstance(minimum, bool) or isinstance(maximum, bool):
        return None
    try:
        default_number = int(default)
        minimum_number = int(minimum)
        maximum_number = int(maximum)
    except (TypeError, ValueError):
        return None
    if minimum_number < 1 or maximum_number < minimum_number or not minimum_number <= default_number <= maximum_number:
        return None
    if value is None or (isinstance(value, str) and not value.strip()):
        return default_number
    if isinstance(value, bool):
        return None
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return parsed if minimum_number <= parsed <= maximum_number else None


def _valid_enum(value: Any, allowed: frozenset[str]) -> bool:
    return isinstance(value, str) and value in allowed


def valid_followup_source_kind(value: Any) -> bool:
    return _valid_enum(value, FOLLOWUP_SOURCE_KINDS)


def valid_followup_state(value: Any) -> bool:
    return _valid_enum(value, FOLLOWUP_STATES)


def valid_followup_severity(value: Any) -> bool:
    return _valid_enum(value, FOLLOWUP_SEVERITIES)


def valid_followup_required_role(value: Any) -> bool:
    return _valid_enum(value, FOLLOWUP_REQUIRED_ROLES)


def valid_followup_event_action(value: Any) -> bool:
    return _valid_enum(value, FOLLOWUP_EVENT_ACTIONS)
