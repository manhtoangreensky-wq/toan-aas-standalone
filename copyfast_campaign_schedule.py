"""Pure safety primitives for explicit Campaign Planner schedule intents.

This module has no router, database, Bot, bridge, provider, payment or
notification side effect.  Keeping the canonical source hash and IANA wall
time normalization in one place prevents the Campaign API and the private
Inbox scheduler from silently disagreeing about what they are authorizing.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


SCHEDULE_INTENT_STATES = frozenset({"active", "dispatched", "guarded", "cancelled"})
MAX_SCHEDULE_INTENTS_PER_ACCOUNT = 200
MAX_ACTIVE_SCHEDULE_INTENTS_PER_ACCOUNT = 50
MAX_SCHEDULE_INTENTS_PER_PLAN = 20
SCHEDULE_MIN_LEAD_SECONDS = 60
SCHEDULE_MAX_AHEAD = timedelta(days=366)
IANA_TIMEZONE_PATTERN = re.compile(r"^(?:UTC|[A-Za-z0-9._+-]+(?:/[A-Za-z0-9._+-]+)+)$")
LOCAL_TRIGGER_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?$")
SNAPSHOT_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def canonical_json_hash(payload: dict[str, Any]) -> str:
    """Return a stable SHA-256 digest without persisting the source payload."""
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def campaign_source_hash(
    *,
    title: Any,
    destination_url: Any,
    platform: Any,
    objective: Any,
    scheduled_for: Any,
    approval_status: Any,
    review_note: Any,
) -> str:
    """Hash the current Web-owned Campaign source fields only.

    ``scheduled_for`` is intentionally represented as inert planning content.
    It can make an existing explicit intent require owner reconfirmation when
    edited, but it can never create a reminder or publish schedule by itself.
    """
    return canonical_json_hash(
        {
            "title": str(title or ""),
            "destination_url": str(destination_url or ""),
            "platform": str(platform or ""),
            "objective": str(objective or ""),
            "scheduled_for": str(scheduled_for or ""),
            "approval_status": str(approval_status or ""),
            "review_note": str(review_note or ""),
        }
    )


def normalize_schedule_trigger(value: Any, timezone_name: Any) -> tuple[str, str, str]:
    """Validate an owner-selected IANA wall time without guessing DST.

    Browser ``datetime-local`` values have no offset.  Ambiguous and
    non-existent wall times are rejected instead of silently picking a fold or
    shifting the requested reminder.  The server stores a reviewable local
    wall-time/zone pair plus its normalized UTC trigger.
    """
    local = str(value or "").strip()
    zone_name = str(timezone_name or "").strip()
    if len(local) > 32 or not LOCAL_TRIGGER_PATTERN.fullmatch(local):
        raise ValueError("Thời điểm nhắc cần có dạng YYYY-MM-DDTHH:MM theo giờ địa phương")
    if len(zone_name) > 64 or not IANA_TIMEZONE_PATTERN.fullmatch(zone_name) or ".." in zone_name:
        raise ValueError("Timezone cần là IANA hợp lệ, ví dụ Asia/Ho_Chi_Minh")
    try:
        local_naive = datetime.fromisoformat(local)
    except (TypeError, ValueError) as exc:
        raise ValueError("Thời điểm nhắc không hợp lệ") from exc
    if local_naive.tzinfo is not None or local_naive.microsecond:
        raise ValueError("Thời điểm nhắc phải là giờ địa phương không kèm timezone")
    try:
        zone = ZoneInfo(zone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Timezone IANA chưa được máy chủ hỗ trợ") from exc
    candidates: list[datetime] = []
    for fold in (0, 1):
        candidate = local_naive.replace(tzinfo=zone, fold=fold)
        round_trip = candidate.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None)
        if round_trip == local_naive:
            candidates.append(candidate)
    offsets = {candidate.utcoffset() for candidate in candidates}
    if not candidates:
        raise ValueError("Thời điểm này không tồn tại trong timezone đã chọn; hãy chọn giờ khác")
    if len(offsets) > 1:
        raise ValueError("Thời điểm này bị trùng khi đổi giờ mùa hè; hãy chọn giờ khác")
    trigger = candidates[0].astimezone(timezone.utc).replace(microsecond=0)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    if trigger <= now + timedelta(seconds=SCHEDULE_MIN_LEAD_SECONDS):
        raise ValueError("Thời điểm nhắc cần cách hiện tại ít nhất 1 phút")
    if trigger > now + SCHEDULE_MAX_AHEAD:
        raise ValueError("Thời điểm nhắc chỉ được đặt tối đa 366 ngày")
    return (
        local_naive.replace(microsecond=0).isoformat(timespec="seconds"),
        zone.key,
        trigger.isoformat(timespec="seconds"),
    )
