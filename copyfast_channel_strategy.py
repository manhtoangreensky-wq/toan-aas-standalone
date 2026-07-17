"""Web-native Channel Strategy profiles derived from Bot ``videoref``.

The frozen Telegram flow stores one lightweight channel profile and asks for a
platform, niche, tone, audience, exclusions, affiliate choice and goal.  This
module keeps that useful product shape but gives each signed Web account a
professional, revisioned workspace.  It is intentionally independent from the
Bot database and never reads Telegram state, fetches a channel URL, calls a
social network/provider, publishes content, creates a job, or changes Xu,
PayOS or wallet state.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import re
import uuid
from typing import Any, Callable
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, field_validator

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import channel_strategy_enabled, ensure_copyfast_schema, read_transaction, transaction, utc_now


router = APIRouter(prefix="/api/v1/channel-strategy", tags=["Web Channel Strategy"])

PROFILE_STATES = frozenset({"active", "archived"})
PLATFORMS = frozenset({"tiktok", "facebook", "instagram", "youtube", "website", "other"})
GOALS = frozenset({"follow", "sales", "lead", "website", "community", "authority", "content"})
LANGUAGES = frozenset({"vi", "en"})
ASPECT_RATIOS = frozenset({"9:16", "16:9", "1:1", "4:5"})

MAX_ACTIVE_PROFILES = 100
MAX_LIST_LIMIT = 100
MAX_LIST_OFFSET = 10_000
MAX_VERSIONS_PER_PROFILE = 100
MAX_LIST_VALUES = 16
MAX_LIST_ITEM = 100
IDEMPOTENCY_RETENTION = timedelta(hours=24)
MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT = 1_024
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
UNSAFE_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
MARKUP_PATTERN = re.compile(r"(?:<\s*/?\s*[A-Za-z][^>\r\n]{0,240}>|```|\bon[a-z]+\s*=)", re.IGNORECASE)
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|token|"
    r"client[ _-]?secret|secret(?:[ _-]?(?:key|access[ _-]?(?:key))?)?|password|passphrase|authorization)\b\s*"
    r"(?:['\"]\s*)?(?:[:=]|\bis\b)\s*(?:['\"]\s*)?(?:(?:bearer|basic)\s+)?[A-Za-z0-9_./+=:-]{8,}",
    re.IGNORECASE,
)
KNOWN_SECRET_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(?:(?:sk|pk|rk)[_-][A-Za-z0-9_-]{12,}|gh(?:p|o|u|s|r)_[A-Za-z0-9]{12,}|"
    r"github_pat_[A-Za-z0-9_]{12,}|xox(?:b|p|a|r|s)-[A-Za-z0-9-]{12,}|AIza[0-9A-Za-z_-]{20,}|"
    r"(?:AKIA|ASIA)[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
CARD_LIKE_PATTERN = re.compile(r"(?<![0-9A-Za-z])[0-9](?:[\s./-]*[0-9]){12,18}(?![0-9A-Za-z])")
OTP_PATTERN = re.compile(
    r"\b(?:otp|cvv|cvc|pin|mã\s*(?:xác\s*(?:minh|thực)|otp)|ma\s*(?:xac\s*(?:minh|thuc)|otp)|"
    r"verification\s+(?:code|token)|one[ -]?time(?:\s+(?:pass(?:word|code)?|code))?)\b",
    re.IGNORECASE,
)
ORIGINALITY_PATTERN = re.compile(
    r"(?:in\s+the\s+style\s+of|sound\s+like|looks?\s+like|same\s+face\s+as|deepfake|clone\s+(?:voice|face)|"
    r"giống\s+(?:người\s+nổi\s+tiếng|ca\s+sĩ|diễn\s+viên|nghệ\s+sĩ)|phong\s+cách\s+của|bắt\s+chước|"
    r"nhái\s+(?:giọng|người)|mô\s+phỏng\s+(?:người|gương\s+mặt)|gương\s+mặt\s+giống)",
    re.IGNORECASE,
)
CLAIM_PATTERN = re.compile(
    r"(?:\b100\s*%|guarantee(?:d)?|cure(?:s|d)?|proven\s+(?:result|cure)|cam\s+kết|chắc\s+chắn|"
    r"chữa\s+khỏi|được\s+chứng\s+minh|tăng\s+follow\s+chắc\s+chắn)",
    re.IGNORECASE,
)


def _require_enabled() -> None:
    if not channel_strategy_enabled():
        raise HTTPException(
            status_code=503,
            detail="Channel Strategy đang tạm dừng để bảo trì. WEBAPP_CHANNEL_STRATEGY_ENABLED chưa được bật.",
        )


def _sensitive(value: str) -> bool:
    return bool(
        SECRET_ASSIGNMENT_PATTERN.search(value)
        or KNOWN_SECRET_PATTERN.search(value)
        or CARD_LIKE_PATTERN.search(value)
        or OTP_PATTERN.search(value)
    )


def _text(value: Any, *, label: str, minimum: int, maximum: int, allow_empty: bool = False, multiline: bool = False) -> str:
    raw = str(value or "")
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n").strip() if multiline else re.sub(r"\s+", " ", raw).strip()
    if UNSAFE_CONTROL_PATTERN.search(normalized) or len(normalized) > maximum or (not allow_empty and len(normalized) < minimum):
        if allow_empty:
            raise ValueError(f"{label} tối đa {maximum} ký tự hợp lệ")
        raise ValueError(f"{label} cần từ {minimum} đến {maximum} ký tự hợp lệ")
    if normalized and (MARKUP_PATTERN.search(normalized) or _sensitive(normalized)):
        raise ValueError(f"{label} không nhận markup, secret, token, OTP hoặc dữ liệu thẻ")
    return normalized


def _code(value: Any, *, label: str, allowed: frozenset[str]) -> str:
    normalized = _text(value, label=label, minimum=1, maximum=32).lower()
    if normalized not in allowed:
        raise ValueError(f"{label} không hợp lệ")
    return normalized


def _list(value: Any, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} phải là một danh sách")
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _text(item, label=label, minimum=1, maximum=MAX_LIST_ITEM)
        fingerprint = text.casefold()
        if fingerprint not in seen:
            seen.add(fingerprint)
            result.append(text)
    if len(result) > MAX_LIST_VALUES:
        raise ValueError(f"{label} tối đa {MAX_LIST_VALUES} mục")
    return result


def _decode_list(value: Any) -> list[str]:
    try:
        parsed = json.loads(str(value or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    result: list[str] = []
    for item in parsed:
        if not isinstance(item, str):
            continue
        try:
            result.append(_text(item, label="Danh sách profile", minimum=1, maximum=MAX_LIST_ITEM))
        except ValueError:
            continue
    return result[:MAX_LIST_VALUES]


def _channel_url(value: Any) -> str:
    url = _text(value, label="URL kênh", minimum=0, maximum=300, allow_empty=True)
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("URL kênh chỉ chấp nhận HTTPS không chứa tài khoản, query hoặc fragment")
    return url


def _id(value: Any, *, label: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail=f"{label} không hợp lệ") from exc


def _idempotency_key(value: Any) -> str:
    key = str(value or "").strip()
    if not IDEMPOTENCY_PATTERN.fullmatch(key):
        raise ValueError("Idempotency key không hợp lệ")
    return key


class ChannelProfilePayload(BaseModel):
    """Bounded, Web-owned form of Bot ``channel_profiles`` fields."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    channel_name: StrictStr
    platform: StrictStr
    channel_url: StrictStr = ""
    niche: StrictStr
    target_audience: StrictStr
    content_style: StrictStr
    tone: StrictStr = ""
    language: StrictStr = "vi"
    allowed_topics: list[StrictStr] = Field(default_factory=list)
    blocked_topics: list[StrictStr] = Field(default_factory=list)
    brand_keywords: list[StrictStr] = Field(default_factory=list)
    cta_default: StrictStr = ""
    affiliate_allowed: StrictBool = False
    product_categories: list[StrictStr] = Field(default_factory=list)
    posting_frequency: StrictStr = ""
    preferred_aspect_ratio: StrictStr = "9:16"
    preferred_duration_seconds: StrictInt = Field(default=18, ge=5, le=600)
    primary_goal: StrictStr = "content"
    notes: StrictStr = ""

    @field_validator("channel_name")
    @classmethod
    def validate_channel_name(cls, value: str) -> str:
        return _text(value, label="Tên kênh", minimum=2, maximum=120)

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, value: str) -> str:
        return _code(value, label="Nền tảng", allowed=PLATFORMS)

    @field_validator("channel_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return _channel_url(value)

    @field_validator("niche")
    @classmethod
    def validate_niche(cls, value: str) -> str:
        return _text(value, label="Ngành hoặc chủ đề kênh", minimum=2, maximum=220)

    @field_validator("target_audience")
    @classmethod
    def validate_audience(cls, value: str) -> str:
        return _text(value, label="Khán giả mục tiêu", minimum=2, maximum=300)

    @field_validator("content_style")
    @classmethod
    def validate_style(cls, value: str) -> str:
        return _text(value, label="Phong cách nội dung", minimum=2, maximum=220)

    @field_validator("tone")
    @classmethod
    def validate_tone(cls, value: str) -> str:
        return _text(value, label="Giọng điệu", minimum=0, maximum=160, allow_empty=True)

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        return _code(value, label="Ngôn ngữ", allowed=LANGUAGES)

    @field_validator("allowed_topics", "blocked_topics", "brand_keywords", "product_categories")
    @classmethod
    def validate_lists(cls, value: list[str], info) -> list[str]:
        labels = {
            "allowed_topics": "Chủ đề được ưu tiên",
            "blocked_topics": "Chủ đề cần tránh",
            "brand_keywords": "Từ khóa thương hiệu",
            "product_categories": "Nhóm sản phẩm",
        }
        return _list(value, label=labels.get(info.field_name, "Danh sách profile"))

    @field_validator("cta_default")
    @classmethod
    def validate_cta(cls, value: str) -> str:
        return _text(value, label="CTA mặc định", minimum=0, maximum=220, allow_empty=True)

    @field_validator("posting_frequency")
    @classmethod
    def validate_frequency(cls, value: str) -> str:
        return _text(value, label="Nhịp đăng", minimum=0, maximum=100, allow_empty=True)

    @field_validator("preferred_aspect_ratio")
    @classmethod
    def validate_ratio(cls, value: str) -> str:
        return _code(value, label="Tỷ lệ ưu tiên", allowed=ASPECT_RATIOS)

    @field_validator("primary_goal")
    @classmethod
    def validate_goal(cls, value: str) -> str:
        return _code(value, label="Mục tiêu chính", allowed=GOALS)

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: str) -> str:
        return _text(value, label="Ghi chú chiến lược", minimum=0, maximum=2_400, allow_empty=True, multiline=True)

    @field_validator("content_style", "tone", "cta_default", "notes")
    @classmethod
    def guard_imitation(cls, value: str) -> str:
        if value and ORIGINALITY_PATTERN.search(value):
            raise ValueError("Hồ sơ kênh không nhận yêu cầu mô phỏng tác giả hoặc người thật được nhận diện")
        # A compliance note such as "không cam kết kết quả" is a guardrail,
        # not an attempt to make the forbidden claim. Keep that useful
        # negative phrasing available to a professional channel profile.
        negative_claim_note = bool(re.search(r"(?:không|khong|not|never)\s+(?:cam\s*kết|guarantee)", value, re.IGNORECASE))
        if value and CLAIM_PATTERN.search(value) and not negative_claim_note:
            raise ValueError("Hồ sơ kênh không nhận claim tuyệt đối hoặc kết quả chưa được kiểm chứng")
        return value


class ChannelProfileCreateRequest(ChannelProfilePayload):
    idempotency_key: StrictStr

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)


class ChannelProfileUpdateRequest(ChannelProfilePayload):
    expected_revision: StrictInt = Field(ge=1)
    idempotency_key: StrictStr

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)


class RevisionMutationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    expected_revision: StrictInt = Field(ge=1)
    idempotency_key: StrictStr

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)


class StrategyPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    expected_revision: StrictInt = Field(ge=1)


def _boundary(*, profile_persisted: bool) -> dict[str, Any]:
    """Honest side-effect contract for a Web-only profile operation."""

    return {
        "execution": "web_native_channel_strategy_profile_only",
        "profile_persisted": bool(profile_persisted),
        "telegram_state_changed": False,
        "bot_called": False,
        "bridge_called": False,
        "channel_url_fetched": False,
        "social_platform_called": False,
        "provider_called": False,
        "job_created": False,
        "wallet_mutated": False,
        "payment_started": False,
        "asset_saved": False,
        "publish_action_created": False,
        "delivery_created": False,
        "analytics_claim_verified": False,
    }


def _preview_boundary() -> dict[str, Any]:
    return {
        **_boundary(profile_persisted=False),
        "execution": "web_native_deterministic_channel_strategy_preview_only",
        "strategy_persisted": False,
    }


def _snapshot(payload: ChannelProfilePayload, *, state: str) -> dict[str, Any]:
    return {
        "channel_name": payload.channel_name,
        "platform": payload.platform,
        "channel_url": payload.channel_url,
        "niche": payload.niche,
        "target_audience": payload.target_audience,
        "content_style": payload.content_style,
        "tone": payload.tone,
        "language": payload.language,
        "allowed_topics": payload.allowed_topics,
        "blocked_topics": payload.blocked_topics,
        "brand_keywords": payload.brand_keywords,
        "cta_default": payload.cta_default,
        "affiliate_allowed": bool(payload.affiliate_allowed),
        "product_categories": payload.product_categories,
        "posting_frequency": payload.posting_frequency,
        "preferred_aspect_ratio": payload.preferred_aspect_ratio,
        "preferred_duration_seconds": int(payload.preferred_duration_seconds),
        "primary_goal": payload.primary_goal,
        "notes": payload.notes,
        "state": state,
    }


def _profile_row(conn: Any, *, profile_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, account_id, channel_name, platform, channel_url, niche, target_audience,
                  content_style, tone, language, allowed_topics_json, blocked_topics_json,
                  brand_keywords_json, cta_default, affiliate_allowed, product_categories_json,
                  posting_frequency, preferred_aspect_ratio, preferred_duration_seconds,
                  primary_goal, notes, state, revision, created_at, updated_at, archived_at
           FROM web_channel_strategy_profiles WHERE id=? AND account_id=?""",
        (profile_id, account_id),
    ).fetchone()


def _profile_snapshot_from_row(row: tuple[Any, ...], *, state: str | None = None) -> dict[str, Any]:
    return {
        "channel_name": str(row[2]),
        "platform": str(row[3]),
        "channel_url": str(row[4]),
        "niche": str(row[5]),
        "target_audience": str(row[6]),
        "content_style": str(row[7]),
        "tone": str(row[8]),
        "language": str(row[9]),
        "allowed_topics": _decode_list(row[10]),
        "blocked_topics": _decode_list(row[11]),
        "brand_keywords": _decode_list(row[12]),
        "cta_default": str(row[13]),
        "affiliate_allowed": bool(row[14]),
        "product_categories": _decode_list(row[15]),
        "posting_frequency": str(row[16]),
        "preferred_aspect_ratio": str(row[17]),
        "preferred_duration_seconds": int(row[18]),
        "primary_goal": str(row[19]),
        "notes": str(row[20]),
        "state": state or str(row[21]),
    }


def _profile_public(row: tuple[Any, ...], *, include_detail: bool = False) -> dict[str, Any]:
    value = {
        "id": str(row[0]),
        "channel_name": str(row[2]),
        "platform": str(row[3]),
        "niche": str(row[5]),
        "target_audience_excerpt": _excerpt(row[6], 180),
        "content_style": str(row[7]),
        "primary_goal": str(row[19]),
        "affiliate_allowed": bool(row[14]),
        "state": str(row[21]),
        "revision": int(row[22]),
        "created_at": str(row[23]),
        "updated_at": str(row[24]),
        "archived_at": str(row[25]) if row[25] else None,
        "execution": "web_owned_profile",
    }
    if include_detail:
        value.update(_profile_snapshot_from_row(row))
    return value


def _excerpt(value: Any, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= limit else f"{text[: max(1, limit - 1)].rstrip()}…"


def _version_public(row: tuple[Any, ...]) -> dict[str, Any]:
    try:
        snapshot = json.loads(str(row[3] or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        snapshot = {}
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    return {
        "revision": int(row[2]),
        "channel_name": _excerpt(snapshot.get("channel_name"), 120),
        "platform": str(snapshot.get("platform") or "other"),
        "niche": _excerpt(snapshot.get("niche"), 180),
        "state": str(snapshot.get("state") or "active"),
        "created_at": str(row[4]),
    }


def _summary(conn: Any, *, account_id: str) -> dict[str, int]:
    rows = conn.execute(
        "SELECT state, COUNT(*) FROM web_channel_strategy_profiles WHERE account_id=? GROUP BY state",
        (account_id,),
    ).fetchall()
    values = {str(row[0]): int(row[1]) for row in rows}
    return {"active": values.get("active", 0), "archived": values.get("archived", 0), "total": sum(values.values())}


def _not_found() -> dict[str, Any]:
    return envelope(
        False,
        "Không tìm thấy Hồ sơ kênh thuộc Web account hiện tại.",
        data=_boundary(profile_persisted=False),
        status_name="guarded",
        error_code="WEB_CHANNEL_STRATEGY_PROFILE_NOT_FOUND",
    )


def _revision_conflict() -> dict[str, Any]:
    return envelope(
        False,
        "Hồ sơ kênh đã được thay đổi ở nơi khác. Hãy tải lại trước khi tiếp tục.",
        data=_boundary(profile_persisted=False),
        status_name="guarded",
        error_code="WEB_CHANNEL_STRATEGY_REVISION_CONFLICT",
    )


def _state_conflict() -> dict[str, Any]:
    return envelope(
        False,
        "Hồ sơ kênh đang archive. Hãy khôi phục trước khi chỉnh sửa hoặc tạo strategy preview.",
        data=_boundary(profile_persisted=False),
        status_name="guarded",
        error_code="WEB_CHANNEL_STRATEGY_STATE_CONFLICT",
    )


def _insert_profile(conn: Any, *, profile_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str, archived_at: str | None = None) -> None:
    conn.execute(
        """INSERT INTO web_channel_strategy_profiles
           (id, account_id, channel_name, platform, channel_url, niche, target_audience,
            content_style, tone, language, allowed_topics_json, blocked_topics_json,
            brand_keywords_json, cta_default, affiliate_allowed, product_categories_json,
            posting_frequency, preferred_aspect_ratio, preferred_duration_seconds,
            primary_goal, notes, state, revision, created_at, updated_at, archived_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            profile_id, account_id, snapshot["channel_name"], snapshot["platform"], snapshot["channel_url"], snapshot["niche"],
            snapshot["target_audience"], snapshot["content_style"], snapshot["tone"], snapshot["language"],
            json.dumps(snapshot["allowed_topics"], ensure_ascii=False), json.dumps(snapshot["blocked_topics"], ensure_ascii=False),
            json.dumps(snapshot["brand_keywords"], ensure_ascii=False), snapshot["cta_default"], int(bool(snapshot["affiliate_allowed"])),
            json.dumps(snapshot["product_categories"], ensure_ascii=False), snapshot["posting_frequency"],
            snapshot["preferred_aspect_ratio"], int(snapshot["preferred_duration_seconds"]), snapshot["primary_goal"],
            snapshot["notes"], snapshot["state"], revision, now, now, archived_at,
        ),
    )


def _write_profile(conn: Any, *, profile_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str, archived_at: str | None) -> None:
    conn.execute(
        """UPDATE web_channel_strategy_profiles
           SET channel_name=?, platform=?, channel_url=?, niche=?, target_audience=?, content_style=?, tone=?, language=?,
               allowed_topics_json=?, blocked_topics_json=?, brand_keywords_json=?, cta_default=?, affiliate_allowed=?,
               product_categories_json=?, posting_frequency=?, preferred_aspect_ratio=?, preferred_duration_seconds=?,
               primary_goal=?, notes=?, state=?, revision=?, updated_at=?, archived_at=?
           WHERE id=? AND account_id=?""",
        (
            snapshot["channel_name"], snapshot["platform"], snapshot["channel_url"], snapshot["niche"], snapshot["target_audience"],
            snapshot["content_style"], snapshot["tone"], snapshot["language"],
            json.dumps(snapshot["allowed_topics"], ensure_ascii=False), json.dumps(snapshot["blocked_topics"], ensure_ascii=False),
            json.dumps(snapshot["brand_keywords"], ensure_ascii=False), snapshot["cta_default"], int(bool(snapshot["affiliate_allowed"])),
            json.dumps(snapshot["product_categories"], ensure_ascii=False), snapshot["posting_frequency"], snapshot["preferred_aspect_ratio"],
            int(snapshot["preferred_duration_seconds"]), snapshot["primary_goal"], snapshot["notes"], snapshot["state"], revision, now,
            archived_at, profile_id, account_id,
        ),
    )


def _insert_version(conn: Any, *, profile_id: str, account_id: str, revision: int, snapshot: dict[str, Any], created_at: str) -> None:
    conn.execute(
        """INSERT INTO web_channel_strategy_profile_versions
           (id, profile_id, account_id, revision, snapshot_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), profile_id, account_id, revision, json.dumps(snapshot, ensure_ascii=False, sort_keys=True), created_at),
    )


def _can_add_version(conn: Any, *, profile_id: str, account_id: str) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) FROM web_channel_strategy_profile_versions WHERE profile_id=? AND account_id=?",
        (profile_id, account_id),
    ).fetchone()
    return int(row[0] or 0) < MAX_VERSIONS_PER_PROFILE


def _event(conn: Any, *, account_id: str, profile_id: str, action: str, revision: int) -> None:
    conn.execute(
        """INSERT INTO web_channel_strategy_events (id, account_id, profile_id, action, revision, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), account_id, profile_id, action, revision, utc_now()),
    )


def _audit(conn: Any, *, request: Request, account: dict, action: str, target: str, detail: str) -> None:
    _record_audit(
        conn,
        account_id=str(account["id"]),
        canonical_user_id=None,
        action=action,
        request_id=_request_id(request),
        target=target,
        detail=detail[:320],
    )


def _fingerprint(payload: dict[str, Any]) -> str:
    material = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _safe_receipt(response: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(response, dict) or response.get("ok") is not True:
        return response
    source = response.get("data") if isinstance(response.get("data"), dict) else {}
    data: dict[str, Any] = {}
    profile = source.get("profile") if isinstance(source.get("profile"), dict) else {}
    if isinstance(profile.get("id"), str):
        data["profile"] = {
            "id": profile["id"],
            "revision": int(profile.get("revision") or 0),
            "state": str(profile.get("state") or ""),
        }
    for field in _boundary(profile_persisted=False):
        if field in source:
            data[field] = source[field]
    return envelope(
        True,
        str(response.get("message") or "Đã lưu Hồ sơ kênh riêng tư."),
        data=data,
        status_name=str(response.get("status") or "draft"),
    )


def _idempotent(
    scope: str,
    account_id: str,
    key: str,
    fingerprint: str,
    operation: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    ensure_copyfast_schema()
    cutoff = (datetime.now(timezone.utc) - IDEMPOTENCY_RETENTION).isoformat(timespec="seconds")
    with transaction() as conn:
        conn.execute("DELETE FROM web_idempotency WHERE scope LIKE ? AND created_at < ?", ("web-channel-strategy:%", cutoff))
        existing = conn.execute("SELECT response_json, request_fingerprint FROM web_idempotency WHERE scope=? AND key=?", (scope, key)).fetchone()
        if existing:
            if not hmac.compare_digest(str(existing[1] or ""), fingerprint):
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho yêu cầu khác")
            try:
                receipt = json.loads(str(existing[0]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Receipt Hồ sơ kênh không hợp lệ") from exc
            if not isinstance(receipt, dict):
                raise HTTPException(status_code=409, detail="Receipt Hồ sơ kênh không hợp lệ")
            return receipt
        count = conn.execute("SELECT COUNT(*) FROM web_idempotency WHERE scope LIKE ?", (f"web-channel-strategy:{account_id}:%",)).fetchone()
        if int(count[0] or 0) >= MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT:
            return envelope(
                False,
                "Kho receipt thao tác tạm thời đang đầy. Vui lòng thử lại sau.",
                data=_boundary(profile_persisted=False),
                status_name="guarded",
                error_code="WEB_CHANNEL_STRATEGY_IDEMPOTENCY_LIMIT",
            )
        response = operation(conn)
        if response.get("ok") is True:
            receipt = _safe_receipt(response)
            conn.execute(
                "INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at) VALUES (?, ?, ?, ?, ?)",
                (scope, key, json.dumps(receipt, ensure_ascii=False, separators=(",", ":")), fingerprint, utc_now()),
            )
            return receipt
    return response


def _profile_detail(conn: Any, *, profile_id: str, account_id: str) -> dict[str, Any] | None:
    profile = _profile_row(conn, profile_id=profile_id, account_id=account_id)
    if not profile:
        return None
    versions = conn.execute(
        """SELECT id, profile_id, revision, snapshot_json, created_at
           FROM web_channel_strategy_profile_versions
           WHERE profile_id=? AND account_id=? ORDER BY revision DESC LIMIT ?""",
        (profile_id, account_id, MAX_VERSIONS_PER_PROFILE),
    ).fetchall()
    events = conn.execute(
        """SELECT action, revision, created_at FROM web_channel_strategy_events
           WHERE profile_id=? AND account_id=? ORDER BY created_at DESC, id DESC LIMIT 50""",
        (profile_id, account_id),
    ).fetchall()
    return {
        "profile": _profile_public(profile, include_detail=True),
        "versions": [_version_public(row) for row in versions],
        "events": [{"action": str(row[0]), "revision": int(row[1]), "created_at": str(row[2])} for row in events],
    }


def _goal_label(goal: str, language: str) -> str:
    labels = {
        "follow": {"vi": "tăng follow", "en": "grow followers"},
        "sales": {"vi": "bán hàng", "en": "support sales"},
        "lead": {"vi": "tạo lead/inbox", "en": "generate leads"},
        "website": {"vi": "kéo website", "en": "drive website visits"},
        "community": {"vi": "xây cộng đồng", "en": "build community"},
        "authority": {"vi": "xây uy tín", "en": "build authority"},
        "content": {"vi": "xây nền nội dung", "en": "build a content foundation"},
    }
    return labels[goal][language]


def _platform_label(platform: str) -> str:
    return {"tiktok": "TikTok", "facebook": "Facebook/Reels", "instagram": "Instagram", "youtube": "YouTube", "website": "Website", "other": "Nền tảng khác"}.get(platform, platform)


def _strategy(profile: dict[str, Any]) -> dict[str, Any]:
    language = str(profile["language"])
    goal = _goal_label(str(profile["primary_goal"]), language)
    platform = _platform_label(str(profile["platform"]))
    topics = [str(item) for item in profile["allowed_topics"]] or [str(profile["niche"])]
    blocked = [str(item) for item in profile["blocked_topics"]]
    if language == "en":
        title = f"Channel strategy preview: {profile['channel_name']}"
        summary = f"A reviewable {platform} direction for {profile['niche']} to {goal}; it is not a forecast, social-account action, or publishing plan."
        pillars = [
            {"title": "Useful repeatable format", "direction": f"Turn {topics[0]} into clear, original explainers for {profile['target_audience']}."},
            {"title": "Trust and context", "direction": f"Use {profile['content_style']} with {profile['tone'] or 'a consistent voice'}; make each claim reviewable before use."},
            {"title": "Conversation and next step", "direction": f"End with a proportional CTA: {profile['cta_default'] or 'invite one appropriate next step without pressure.'}"},
        ]
        review = [
            "This is a deterministic planning preview, not live trend research, audience data, analytics, reach or conversion evidence.",
            "Verify claims, prices, availability, platform rules, rights and local relevance before publishing.",
            "Do not imitate a named creator or reuse third-party media without the needed rights.",
        ]
        cadence = profile["posting_frequency"] or "Choose a sustainable manual cadence before scheduling anything."
    else:
        title = f"Bản xem trước Channel Strategy: {profile['channel_name']}"
        summary = f"Direction {platform} có thể review cho {profile['niche']} nhằm {goal}; không phải dự báo, hành động social account hoặc kế hoạch tự đăng."
        pillars = [
            {"title": "Format có thể lặp lại", "direction": f"Chuyển {topics[0]} thành các nội dung nguyên bản, dễ hiểu cho {profile['target_audience']}."},
            {"title": "Ngữ cảnh và độ tin cậy", "direction": f"Dùng phong cách {profile['content_style']} với {profile['tone'] or 'giọng văn nhất quán'}; mọi claim cần được review trước khi dùng."},
            {"title": "Hội thoại và bước tiếp theo", "direction": f"Kết bằng CTA vừa phải: {profile['cta_default'] or 'mời người xem thực hiện một bước tiếp theo phù hợp, không gây áp lực.'}"},
        ]
        review = [
            "Đây là direction deterministic, không phải dữ liệu trend live, dữ liệu khán giả, analytics, bằng chứng reach hoặc conversion.",
            "Kiểm tra claim, giá, khả dụng, quy định nền tảng, quyền sử dụng và mức phù hợp địa phương trước khi đăng.",
            "Không mô phỏng creator được nhận diện hoặc dùng lại media bên thứ ba khi chưa có quyền phù hợp.",
        ]
        cadence = profile["posting_frequency"] or "Hãy tự chọn nhịp đăng bền vững trước khi lập lịch bất kỳ nội dung nào."
    guardrails = [
        f"Chủ đề ưu tiên: {', '.join(topics[:6])}.",
        f"Tỷ lệ ưu tiên: {profile['preferred_aspect_ratio']} · thời lượng direction: {profile['preferred_duration_seconds']} giây.",
        "Affiliate được phép theo hồ sơ; vẫn phải tự kiểm tra disclosure và chính sách nền tảng." if profile["affiliate_allowed"] else "Không đưa affiliate vào direction trừ khi bạn chủ động cập nhật hồ sơ và tự kiểm tra disclosure.",
    ]
    if blocked:
        guardrails.append(f"Tránh: {', '.join(blocked[:6])}.")
    if profile["brand_keywords"]:
        guardrails.append(f"Từ khóa/brand cần đối chiếu: {', '.join(profile['brand_keywords'][:6])}.")
    return {
        "title": title,
        "profile_id": str(profile["id"]),
        "profile_revision": int(profile["revision"]),
        "summary": summary,
        "content_pillars": pillars,
        "cadence_direction": cadence,
        "guardrails": guardrails,
        "next_workflows": [
            {"label": "Creative Content Studio", "route": "/content-studio", "purpose": "Lưu brief và content piece để biên tập riêng tư."},
            {"label": "Content Prompt Pack", "route": "/content/prompt-pack", "purpose": "Tạo pack text để review từ một chủ đề đã tự kiểm tra."},
            {"label": "Workboard", "route": "/workboard", "purpose": "Theo dõi các bước review và việc cần làm, không tự publish."},
        ],
        "review_before_use": review,
    }


@router.get("/summary")
async def channel_strategy_summary(account: dict = Depends(require_account)):
    _require_enabled()
    ensure_copyfast_schema()
    with read_transaction() as conn:
        data = _summary(conn, account_id=str(account["id"]))
    return envelope(True, "Đã tải tổng quan Hồ sơ kênh riêng tư.", data=data, status_name="read_only")


@router.get("/profiles")
async def list_channel_profiles(
    limit: int = 30,
    state: str = "active",
    q: str = "",
    offset: int = Query(0, ge=0, le=MAX_LIST_OFFSET),
    account: dict = Depends(require_account),
):
    _require_enabled()
    ensure_copyfast_schema()
    bounded = max(1, min(int(limit), MAX_LIST_LIMIT))
    state_filter = str(state or "active").strip().lower()
    if state_filter not in {*PROFILE_STATES, "all"}:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái Hồ sơ kênh không hợp lệ")
    query = _text(q, label="Từ khóa Hồ sơ kênh", minimum=0, maximum=100, allow_empty=True)
    clauses = ["account_id=?"]
    params: list[Any] = [str(account["id"])]
    if state_filter != "all":
        clauses.append("state=?")
        params.append(state_filter)
    if query:
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{escaped}%"
        clauses.append("(channel_name LIKE ? ESCAPE '\\' OR niche LIKE ? ESCAPE '\\' OR target_audience LIKE ? ESCAPE '\\')")
        params.extend([like, like, like])
    safe_offset = int(offset)
    with read_transaction() as conn:
        rows = conn.execute(
            f"""SELECT id, account_id, channel_name, platform, channel_url, niche, target_audience,
                       content_style, tone, language, allowed_topics_json, blocked_topics_json,
                       brand_keywords_json, cta_default, affiliate_allowed, product_categories_json,
                       posting_frequency, preferred_aspect_ratio, preferred_duration_seconds,
                       primary_goal, notes, state, revision, created_at, updated_at, archived_at
                FROM web_channel_strategy_profiles WHERE {' AND '.join(clauses)}
                ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?""",
            (*params, bounded + 1, safe_offset),
        ).fetchall()
    items = [_profile_public(row) for row in rows[:bounded]]
    returned = len(items)
    has_more = len(rows) > bounded
    return envelope(
        True,
        "Đã tải danh sách Hồ sơ kênh riêng tư.",
        data={
            "items": items,
            # Do not reflect a private free-text query back into the API
            # response. The signed client already owns its current filter;
            # only the safe categorical state is needed to verify the page.
            "filters": {"state": state_filter},
            "pagination": {"limit": bounded, "offset": safe_offset, "returned": returned},
            # Keep the original top-level `has_more` shape for existing Web
            # clients while adding a deterministic next-page cursor.
            "has_more": has_more,
            "next_offset": safe_offset + returned if has_more else None,
            "previous_offset": max(0, safe_offset - bounded) if safe_offset > 0 else None,
        },
        status_name="read_only",
    )


@router.get("/profiles/{profile_id}")
async def get_channel_profile(profile_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    ensure_copyfast_schema()
    profile_id = _id(profile_id, label="Hồ sơ kênh ID")
    with read_transaction() as conn:
        detail = _profile_detail(conn, profile_id=profile_id, account_id=str(account["id"]))
    if not detail:
        return _not_found()
    return envelope(True, "Đã tải Hồ sơ kênh, lịch sử và hoạt động riêng tư.", data=detail, status_name="read_only")


@router.post("/profiles")
async def create_channel_profile(payload: ChannelProfileCreateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    account_id = str(account["id"])
    snapshot = _snapshot(payload, state="active")
    fingerprint = _fingerprint({"action": "create", "snapshot": snapshot})

    def operation(conn: Any) -> dict[str, Any]:
        count = conn.execute(
            "SELECT COUNT(*) FROM web_channel_strategy_profiles WHERE account_id=? AND state='active'",
            (account_id,),
        ).fetchone()
        if int(count[0] or 0) >= MAX_ACTIVE_PROFILES:
            return envelope(
                False,
                "Đã đạt giới hạn Hồ sơ kênh active. Hãy archive hồ sơ cũ trước.",
                data=_boundary(profile_persisted=False),
                status_name="guarded",
                error_code="WEB_CHANNEL_STRATEGY_PROFILE_LIMIT",
            )
        profile_id = str(uuid.uuid4())
        now = utc_now()
        _insert_profile(conn, profile_id=profile_id, account_id=account_id, snapshot=snapshot, revision=1, now=now)
        _insert_version(conn, profile_id=profile_id, account_id=account_id, revision=1, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, profile_id=profile_id, action="profile_created", revision=1)
        _audit(conn, request=request, account=account, action="web.channel_strategy.profile.create", target=profile_id, detail=f"platform={payload.platform};goal={payload.primary_goal}")
        created = _profile_row(conn, profile_id=profile_id, account_id=account_id)
        return envelope(
            True,
            "Đã tạo Hồ sơ kênh riêng tư. Chưa có kết nối nền tảng, analytics hoặc publish nào được tạo.",
            data={"profile": _profile_public(created, include_detail=True), **_boundary(profile_persisted=True)},
            status_name="draft",
        )

    return _idempotent(f"web-channel-strategy:{account_id}:profile:create", account_id, payload.idempotency_key, fingerprint, operation)


@router.patch("/profiles/{profile_id}")
async def update_channel_profile(profile_id: str, payload: ChannelProfileUpdateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    profile_id = _id(profile_id, label="Hồ sơ kênh ID")
    account_id = str(account["id"])
    snapshot = _snapshot(payload, state="active")
    fingerprint = _fingerprint({"action": "update", "profile_id": profile_id, "expected_revision": payload.expected_revision, "snapshot": snapshot})

    def operation(conn: Any) -> dict[str, Any]:
        current = _profile_row(conn, profile_id=profile_id, account_id=account_id)
        if not current:
            return _not_found()
        if int(current[22]) != payload.expected_revision:
            return _revision_conflict()
        if str(current[21]) != "active":
            return _state_conflict()
        if not _can_add_version(conn, profile_id=profile_id, account_id=account_id):
            return envelope(
                False,
                "Hồ sơ kênh đã đạt giới hạn lịch sử version. Hãy tạo bản mới trước khi tiếp tục thay đổi.",
                data=_boundary(profile_persisted=False),
                status_name="guarded",
                error_code="WEB_CHANNEL_STRATEGY_VERSION_LIMIT",
            )
        revision = int(current[22]) + 1
        now = utc_now()
        _write_profile(conn, profile_id=profile_id, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_version(conn, profile_id=profile_id, account_id=account_id, revision=revision, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, profile_id=profile_id, action="profile_updated", revision=revision)
        _audit(conn, request=request, account=account, action="web.channel_strategy.profile.update", target=profile_id, detail=f"revision={revision};platform={payload.platform}")
        updated = _profile_row(conn, profile_id=profile_id, account_id=account_id)
        return envelope(
            True,
            "Đã lưu version Hồ sơ kênh mới. Chưa có hành động social hoặc publish nào được tạo.",
            data={"profile": _profile_public(updated, include_detail=True), **_boundary(profile_persisted=True)},
            status_name="draft",
        )

    return _idempotent(f"web-channel-strategy:{account_id}:profile:{profile_id}:update", account_id, payload.idempotency_key, fingerprint, operation)


def _state_transition(*, profile_id: str, payload: RevisionMutationRequest, request: Request, account: dict, target_state: str, action: str) -> dict[str, Any]:
    account_id = str(account["id"])
    fingerprint = _fingerprint({"action": action, "profile_id": profile_id, "expected_revision": payload.expected_revision})

    def operation(conn: Any) -> dict[str, Any]:
        current = _profile_row(conn, profile_id=profile_id, account_id=account_id)
        if not current:
            return _not_found()
        if int(current[22]) != payload.expected_revision:
            return _revision_conflict()
        if str(current[21]) == target_state:
            return envelope(
                False,
                "Hồ sơ kênh đã ở trạng thái yêu cầu.",
                data=_boundary(profile_persisted=False),
                status_name="guarded",
                error_code="WEB_CHANNEL_STRATEGY_STATE",
            )
        if target_state == "active":
            active_count = conn.execute(
                "SELECT COUNT(*) FROM web_channel_strategy_profiles WHERE account_id=? AND state='active'",
                (account_id,),
            ).fetchone()
            if int(active_count[0] or 0) >= MAX_ACTIVE_PROFILES:
                return envelope(
                    False,
                    "Đã đạt giới hạn Hồ sơ kênh active. Hãy archive hồ sơ khác trước khi khôi phục.",
                    data=_boundary(profile_persisted=False),
                    status_name="guarded",
                    error_code="WEB_CHANNEL_STRATEGY_PROFILE_LIMIT",
                )
        if not _can_add_version(conn, profile_id=profile_id, account_id=account_id):
            return envelope(
                False,
                "Hồ sơ kênh đã đạt giới hạn lịch sử version.",
                data=_boundary(profile_persisted=False),
                status_name="guarded",
                error_code="WEB_CHANNEL_STRATEGY_VERSION_LIMIT",
            )
        snapshot = _profile_snapshot_from_row(current, state=target_state)
        revision = int(current[22]) + 1
        now = utc_now()
        _write_profile(
            conn,
            profile_id=profile_id,
            account_id=account_id,
            snapshot=snapshot,
            revision=revision,
            now=now,
            archived_at=now if target_state == "archived" else None,
        )
        _insert_version(conn, profile_id=profile_id, account_id=account_id, revision=revision, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, profile_id=profile_id, action=action, revision=revision)
        _audit(conn, request=request, account=account, action=f"web.channel_strategy.profile.{action}", target=profile_id, detail=f"revision={revision}")
        updated = _profile_row(conn, profile_id=profile_id, account_id=account_id)
        return envelope(
            True,
            "Đã cập nhật trạng thái Hồ sơ kênh riêng tư.",
            data={"profile": _profile_public(updated, include_detail=True), **_boundary(profile_persisted=True)},
            status_name="draft",
        )

    return _idempotent(f"web-channel-strategy:{account_id}:profile:{profile_id}:{action}", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/profiles/{profile_id}/archive")
async def archive_channel_profile(profile_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    return _state_transition(profile_id=_id(profile_id, label="Hồ sơ kênh ID"), payload=payload, request=request, account=account, target_state="archived", action="profile_archived")


@router.post("/profiles/{profile_id}/restore")
async def restore_channel_profile(profile_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    return _state_transition(profile_id=_id(profile_id, label="Hồ sơ kênh ID"), payload=payload, request=request, account=account, target_state="active", action="profile_restored")


@router.post("/profiles/{profile_id}/strategy-preview")
async def preview_channel_strategy(profile_id: str, payload: StrategyPreviewRequest, request: Request, account: dict = Depends(require_csrf)):
    """Create a transient deterministic direction from a current Web profile.

    The preview writes only a sanitized audit action.  It never performs a
    channel lookup, social search, audience/analytics query, provider call,
    Bot/bridge request, job/payment operation or publication.
    """

    _require_enabled()
    ensure_copyfast_schema()
    profile_id = _id(profile_id, label="Hồ sơ kênh ID")
    account_id = str(account["id"])
    with transaction() as conn:
        current = _profile_row(conn, profile_id=profile_id, account_id=account_id)
        if not current:
            return _not_found()
        if int(current[22]) != payload.expected_revision:
            return _revision_conflict()
        if str(current[21]) != "active":
            return _state_conflict()
        profile = _profile_public(current, include_detail=True)
        _event(conn, account_id=account_id, profile_id=profile_id, action="strategy_previewed", revision=int(current[22]))
        _audit(conn, request=request, account=account, action="web.channel_strategy.profile.preview", target=profile_id, detail=f"revision={int(current[22])}")
    return envelope(
        True,
        "Đã tạo direction Channel Strategy để bạn review. Không có social lookup, analytics, Bot, provider, job, thanh toán hoặc publish action.",
        data={"profile": profile, "strategy": _strategy(profile), **_preview_boundary()},
        status_name="draft",
    )
