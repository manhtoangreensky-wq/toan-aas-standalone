"""Private, Web-native Creative Content Studio.

The Telegram Bot remains an independent product with its own AI engines,
provider state, Xu, payments, jobs, delivery and Telegram conversations.
This module intentionally does not mirror or call any of them.  It gives a
signed Web account a durable professional authoring workspace for captions,
hooks, scripts, storyboards and content packs.  Its only automatic operation
creates explicitly-labelled deterministic local draft scaffolds; no generated
media, provider execution, charge, publishing or delivery is claimed here.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import re
import uuid
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import content_studio_enabled, ensure_copyfast_schema, read_transaction, transaction, utc_now


router = APIRouter(prefix="/api/v1/content-studio", tags=["Web Creative Content Studio"])

BRIEF_STATES = frozenset({"active", "archived"})
CONTENT_KINDS = frozenset({"caption_hashtag", "content_ideas", "hook_script", "content_pack", "storyboard"})
VARIANT_KINDS = frozenset({"caption", "hashtag_set", "hook", "script", "storyboard", "content_pack", "content_ideas", "custom"})
VARIANT_STATES = frozenset({"active", "archived"})
SOURCE_KINDS = frozenset({"manual", "local_deterministic_draft_only"})
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
UNSAFE_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|token|"
    r"client[ _-]?secret|aws[ _-]?secret[ _-]?access[ _-]?key|secret(?:[ _-]?(?:key|access[ _-]?key))?|"
    r"password|passphrase|authorization)\b\s*(?:['\"]\s*)?(?:[:=]|\bis\b)\s*(?:['\"]\s*)?"
    r"(?:(?:bearer|basic)\s+)?[A-Za-z0-9_./+=:-]{8,}",
    re.IGNORECASE,
)
BEARER_PATTERN = re.compile(r"\bbearer\s+[A-Za-z0-9._~+/=-]{12,}\b", re.IGNORECASE)
KNOWN_SECRET_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(?:(?:sk|pk|rk)[_-][A-Za-z0-9_-]{12,}|"
    r"gh(?:p|o|u|s|r)_[A-Za-z0-9]{12,}|github_pat_[A-Za-z0-9_]{12,}|"
    r"xox(?:b|p|a|r|s)-[A-Za-z0-9-]{12,}|AIza[0-9A-Za-z_-]{20,}|"
    r"(?:AKIA|ASIA)[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN(?: [A-Z0-9]+)? PRIVATE KEY-----|-----BEGIN OPENSSH PRIVATE KEY-----|"
    r"\bssh-(?:rsa|ed25519|ecdsa)\s+[A-Za-z0-9+/]{32,}",
    re.IGNORECASE,
)
CARD_LIKE_PATTERN = re.compile(r"(?<![0-9A-Za-z])[0-9](?:[\s./-]*[0-9]){12,18}(?![0-9A-Za-z])")
OTP_PATTERN = re.compile(
    r"\b(?:otp|cvv|cvc|pin|mã\s*(?:xác\s*(?:minh|thực)|otp)|ma\s*(?:xac\s*(?:minh|thuc)|otp)|"
    r"verification\s+(?:code|token)|one[ -]?time(?:\s+(?:pass(?:word|code)?|code))?)\b",
    re.IGNORECASE,
)
PAYMENT_PROOF_PATTERN = re.compile(
    r"\b(?:tx(?:id|n)?|transaction\s+(?:hash|id|reference|no\.?|number)|"
    r"mã\s*(?:(?:giao\s*)?(?:dịch|gd)|tham\s*chiếu|thanh\s*toán)|ma\s*(?:(?:giao\s*)?(?:dich|gd)|tham\s*chieu|thanh\s*toan)|"
    r"biên\s*lai|bien\s*lai|chứng\s*từ|chung\s*tu|bill|số\s*tài\s*khoản|so\s*tai\s*khoan|stk|"
    r"tài\s*khoản\s*(?:ngân\s*hàng|bank)|tai\s*khoan\s*(?:ngan\s*hang|bank)|bank\s+account|"
    r"account\s+(?:number|no|id)|qr\s*(?:code|thanh\s*toán|thanh\s*toan)?)\b",
    re.IGNORECASE,
)

# A compact policy marker only.  This is not copyright clearance and does not
# try to classify artists, authors or brands.  It keeps imitation requests out
# of the local-draft authoring boundary until a separately reviewed policy
# workflow exists.
COPYRIGHT_BLOCK_MARKERS = (
    "giống nghệ sĩ", "giống ca sĩ", "giống bài", "như bài", "cover bài", "remix bài",
    "style của", "phong cách của", "nhái giọng", "bắt chước giọng", "sound like",
    "sounds like", "in the style of", "copy melody", "cover song", "remix song",
    "artist style", "same melody",
)

MAX_BRIEFS_PER_STATE = 500
MAX_VARIANTS_PER_BRIEF = 250
MAX_VARIANTS_PER_ACCOUNT = 3_000
MAX_VERSIONS_PER_ENTITY = 100
MAX_LIST_LIMIT = 100
MAX_EVENT_LIMIT = 50
MAX_TOTAL_STORAGE_BYTES = 24 * 1024 * 1024
MAX_TITLE = 180
MAX_SUBJECT = 700
MAX_OBJECTIVE = 500
MAX_AUDIENCE = 500
MAX_PLATFORM = 100
MAX_TONE = 160
MAX_LANGUAGE = 100
MAX_CALL_TO_ACTION = 600
MAX_BRIEF_TEXT = 12_000
MAX_CONSTRAINTS = 6_000
MAX_RIGHTS_NOTE = 1_000
MAX_VARIANT_TEXT = 20_000
MAX_VARIANT_NOTE = 2_000
MAX_TAGS = 20
MAX_TAG_LENGTH = 48
IDEMPOTENCY_RETENTION = timedelta(hours=24)
MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT = 1_024


def _require_enabled() -> None:
    if not content_studio_enabled():
        raise HTTPException(
            status_code=503,
            detail="Creative Content Studio đang tạm dừng để bảo trì. WEBAPP_CONTENT_STUDIO_ENABLED chưa được bật.",
        )


def _uuid(value: Any, *, label: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail=f"{label} không hợp lệ") from exc


def _optional_uuid(value: Any, *, label: str) -> str | None:
    raw = str(value or "").strip()
    return _uuid(raw, label=label) if raw else None


def _idempotency_key(value: Any) -> str:
    key = str(value or "").strip()
    if not IDEMPOTENCY_PATTERN.fullmatch(key):
        raise HTTPException(status_code=422, detail="Idempotency key không hợp lệ")
    return key


def _sensitive_text(value: str) -> bool:
    return bool(
        SECRET_ASSIGNMENT_PATTERN.search(value)
        or BEARER_PATTERN.search(value)
        or KNOWN_SECRET_PATTERN.search(value)
        or PRIVATE_KEY_PATTERN.search(value)
        or CARD_LIKE_PATTERN.search(value)
        or OTP_PATTERN.search(value)
        or PAYMENT_PROOF_PATTERN.search(value)
    )


def _single_line(value: Any, *, label: str, minimum: int, maximum: int, allow_empty: bool = False) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if UNSAFE_CONTROL_PATTERN.search(text) or len(text) > maximum or (not allow_empty and len(text) < minimum):
        if allow_empty:
            raise ValueError(f"{label} tối đa {maximum} ký tự hợp lệ")
        raise ValueError(f"{label} cần từ {minimum} đến {maximum} ký tự hợp lệ")
    if text and _sensitive_text(text):
        raise ValueError(f"{label} không nhận secret, token, mã xác thực, dữ liệu thẻ hoặc chứng từ thanh toán")
    return text


def _content(value: Any, *, label: str, maximum: int, allow_empty: bool = False) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if UNSAFE_CONTROL_PATTERN.search(text) or len(text) > maximum or (not allow_empty and not text):
        if allow_empty:
            raise ValueError(f"{label} tối đa {maximum:,} ký tự hợp lệ".replace(",", "."))
        raise ValueError(f"{label} cần từ 1 đến {maximum:,} ký tự hợp lệ".replace(",", "."))
    if text and _sensitive_text(text):
        raise ValueError(f"{label} không nhận secret, token, mã xác thực, dữ liệu thẻ hoặc chứng từ thanh toán")
    return text


def _tags(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("Tags phải là một danh sách")
    values: list[str] = []
    seen: set[str] = set()
    for item in value:
        tag = _single_line(item, label="Tag", minimum=1, maximum=MAX_TAG_LENGTH)
        fingerprint = tag.casefold()
        if fingerprint not in seen:
            seen.add(fingerprint)
            values.append(tag)
    if len(values) > MAX_TAGS:
        raise ValueError(f"Tối đa {MAX_TAGS} tags")
    return values


def _decode_tags(value: Any) -> list[str]:
    try:
        parsed = json.loads(str(value or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    return [str(item) for item in parsed if isinstance(item, str)][:MAX_TAGS] if isinstance(parsed, list) else []


def _safe_filter(value: Any, *, label: str, maximum: int = 100) -> str:
    return _single_line(value, label=label, minimum=0, maximum=maximum, allow_empty=True)


def _escaped_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _marker(*parts: str) -> str:
    normalized = re.sub(r"\s+", " ", "\n".join(str(part or "") for part in parts)).strip().lower()[:20_000]
    for marker in COPYRIGHT_BLOCK_MARKERS:
        if marker in normalized:
            return marker
    return ""


def _fingerprint(payload: dict[str, Any]) -> str:
    material = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _hash(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _idempotency_cutoff() -> str:
    return (datetime.now(timezone.utc) - IDEMPOTENCY_RETENTION).isoformat(timespec="seconds")


def _safe_receipt(response: dict[str, Any]) -> dict[str, Any]:
    """Return a replay-safe mutation receipt without authored material.

    The Web client hydrates the signed owner projection after every durable
    mutation.  A 24-hour generic idempotency record therefore contains only
    opaque IDs, revision/state metadata and local-execution facts, never a
    second copy of a private brief, variant, tag, reference snapshot or note.
    """

    if not isinstance(response, dict) or response.get("ok") is not True:
        return response
    source = response.get("data")
    source = source if isinstance(source, dict) else {}
    data: dict[str, Any] = {}
    brief = source.get("brief")
    if isinstance(brief, dict) and isinstance(brief.get("id"), str):
        data["brief"] = {
            "id": brief["id"],
            "revision": int(brief.get("revision") or 0),
            "state": str(brief.get("state") or ""),
            "selected_variant_id": str(brief["selected_variant_id"]) if brief.get("selected_variant_id") else None,
        }
    variant = source.get("variant")
    if isinstance(variant, dict) and isinstance(variant.get("id"), str):
        data["variant"] = {
            "id": variant["id"],
            "brief_id": str(variant.get("brief_id") or ""),
            "revision": int(variant.get("revision") or 0),
            "state": str(variant.get("state") or ""),
            "source_kind": str(variant.get("source_kind") or ""),
        }
    ids = source.get("variant_ids")
    if isinstance(ids, list):
        data["variant_ids"] = [str(item) for item in ids if isinstance(item, str)][:3]
    for field in ("history_snapshot_recorded", "variant_count", "execution", "provider_called", "charge_started"):
        if field in source:
            data[field] = source[field]
    return envelope(True, str(response.get("message") or "Đã lưu thao tác Content Studio."), data=data, status_name=str(response.get("status") or "draft"))


def _idempotent(
    scope: str,
    account_id: str,
    key: str,
    request_fingerprint: str,
    operation: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    """Persist only successful Studio receipts and make replay content-free."""

    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute(
            "DELETE FROM web_idempotency WHERE scope LIKE ? AND created_at < ?",
            ("web-content-studio:%", _idempotency_cutoff()),
        )
        existing = conn.execute(
            "SELECT response_json, request_fingerprint FROM web_idempotency WHERE scope=? AND key=?",
            (scope, key),
        ).fetchone()
        if existing:
            stored = str(existing[1] or "")
            if not stored or not hmac.compare_digest(stored, request_fingerprint):
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho yêu cầu khác")
            try:
                replay = json.loads(str(existing[0]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Receipt Content Studio không hợp lệ") from exc
            if not isinstance(replay, dict):
                raise HTTPException(status_code=409, detail="Receipt Content Studio không hợp lệ")
            return replay
        receipt_count = conn.execute(
            "SELECT COUNT(*) FROM web_idempotency WHERE scope LIKE ?",
            (f"web-content-studio:{account_id}:%",),
        ).fetchone()
        if int(receipt_count[0] or 0) >= MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT:
            return envelope(
                False,
                "Kho receipt thao tác tạm thời đang đầy. Vui lòng thử lại sau khi các receipt cũ hết hạn.",
                status_name="guarded",
                error_code="WEB_CONTENT_IDEMPOTENCY_LIMIT",
            )
        response = operation(conn)
        if response.get("ok") is True:
            receipt = _safe_receipt(response)
            conn.execute(
                """INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (scope, key, json.dumps(receipt, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
            )
            return receipt
    return response


def _brief_row(conn: Any, *, brief_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, project_id, campaign_plan_id, prompt_template_id, media_collection_id,
                  title, content_kind, subject, objective, audience, platform, tone, language,
                  call_to_action, brief_text, constraints, tags_json, rights_note, policy_marker,
                  state, selected_variant_id, revision, created_at, updated_at, archived_at
           FROM web_content_briefs WHERE id=? AND account_id=?""",
        (brief_id, account_id),
    ).fetchone()


def _variant_row(conn: Any, *, brief_id: str, variant_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, brief_id, kind, ordinal, title, content_text, note, tags_json, source_kind,
                  source_brief_revision, state, revision, created_at, updated_at, archived_at
           FROM web_content_variants WHERE id=? AND brief_id=? AND account_id=?""",
        (variant_id, brief_id, account_id),
    ).fetchone()


def _brief_not_found() -> dict[str, Any]:
    return envelope(
        False,
        "Không tìm thấy content brief thuộc Web account hiện tại.",
        status_name="guarded",
        error_code="WEB_CONTENT_BRIEF_NOT_FOUND",
    )


def _variant_not_found() -> dict[str, Any]:
    return envelope(
        False,
        "Không tìm thấy content piece thuộc brief hiện tại.",
        status_name="guarded",
        error_code="WEB_CONTENT_VARIANT_NOT_FOUND",
    )


def _excerpt(value: Any, *, limit: int = 280) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= limit else f"{text[: max(1, limit - 1)].rstrip()}…"


def _brief_public(row: tuple[Any, ...], *, include_content: bool = False) -> dict[str, Any]:
    marker = str(row[18] or "")
    value = {
        "id": str(row[0]),
        "project_id": str(row[1]) if row[1] else None,
        "campaign_plan_id": str(row[2]) if row[2] else None,
        "prompt_template_id": str(row[3]) if row[3] else None,
        "media_collection_id": str(row[4]) if row[4] else None,
        "title": str(row[5]),
        "content_kind": str(row[6]),
        "subject_excerpt": _excerpt(row[7], limit=180),
        "brief_excerpt": _excerpt(row[14]),
        "platform": str(row[10]),
        "tone": str(row[11]),
        "language": str(row[12]),
        "tags": _decode_tags(row[16]),
        "policy": {"status": "guarded" if marker else "clear", "marker": marker or None},
        "state": str(row[19]),
        "selected_variant_id": str(row[20]) if row[20] else None,
        "revision": int(row[21]),
        "created_at": str(row[22]),
        "updated_at": str(row[23]),
        "archived_at": str(row[24]) if row[24] else None,
        "execution": "authoring_only",
    }
    if include_content:
        value.update(
            {
                "subject": str(row[7]),
                "objective": str(row[8]),
                "audience": str(row[9]),
                "call_to_action": str(row[13]),
                "brief_text": str(row[14]),
                "constraints": str(row[15]),
                "rights_note": str(row[17]),
            }
        )
    return value


def _variant_public(row: tuple[Any, ...], *, include_content: bool = False) -> dict[str, Any]:
    value = {
        "id": str(row[0]),
        "brief_id": str(row[1]),
        "kind": str(row[2]),
        "ordinal": int(row[3]),
        "title": str(row[4]),
        "content_excerpt": _excerpt(row[5], limit=360),
        "note_excerpt": _excerpt(row[6], limit=180),
        "tags": _decode_tags(row[7]),
        "source_kind": str(row[8]),
        "source_brief_revision": int(row[9]),
        "state": str(row[10]),
        "revision": int(row[11]),
        "created_at": str(row[12]),
        "updated_at": str(row[13]),
        "archived_at": str(row[14]) if row[14] else None,
        "execution": "authoring_only",
    }
    if include_content:
        value.update({"content_text": str(row[5]), "note": str(row[6])})
    return value


def _policy_guard(marker: str) -> dict[str, Any] | None:
    if not marker:
        return None
    return envelope(
        False,
        "Brief cần được viết lại theo hướng nguyên bản, không mô phỏng tác giả, nghệ sĩ, bài hát hoặc phong cách cụ thể.",
        status_name="guarded",
        error_code="WEB_CONTENT_ORIGINALITY_GUARD",
    )


def _event(
    conn: Any,
    *,
    account_id: str,
    brief_id: str,
    action: str,
    revision: int,
    variant_id: str | None = None,
) -> None:
    conn.execute(
        """INSERT INTO web_content_studio_events
           (id, account_id, brief_id, variant_id, entity_type, action, revision, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            str(uuid.uuid4()),
            account_id,
            brief_id,
            variant_id,
            "variant" if variant_id else "brief",
            action,
            revision,
            utc_now(),
        ),
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


def _reference_snapshot(conn: Any, *, account_id: str, references: dict[str, str | None], require_active: bool = True) -> dict[str, Any]:
    """Owner-scope every reference and snapshot only safe metadata."""

    result: dict[str, Any] = {}
    project_id = references.get("project_id")
    if project_id:
        clause = "AND state='active'" if require_active else ""
        row = conn.execute(
            f"SELECT id, title, state FROM web_projects WHERE id=? AND account_id=? {clause}",
            (project_id, account_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=422, detail="Project liên kết không hợp lệ hoặc không còn hoạt động")
        result["project"] = {"id": str(row[0]), "title": str(row[1]), "state": str(row[2])}
    campaign_id = references.get("campaign_plan_id")
    if campaign_id:
        row = conn.execute(
            "SELECT id, title, platform, approval_status FROM web_campaign_plans WHERE id=? AND account_id=?",
            (campaign_id, account_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=422, detail="Campaign liên kết không hợp lệ")
        result["campaign"] = {
            "id": str(row[0]),
            "title": str(row[1]),
            "platform": str(row[2]),
            "approval_status": str(row[3]),
        }
    template_id = references.get("prompt_template_id")
    if template_id:
        clause = "AND state='active'" if require_active else ""
        row = conn.execute(
            f"SELECT id, title, revision, state FROM web_prompt_templates WHERE id=? AND account_id=? {clause}",
            (template_id, account_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=422, detail="Prompt template liên kết không hợp lệ hoặc không còn hoạt động")
        result["prompt_template"] = {
            "id": str(row[0]),
            "title": str(row[1]),
            "revision": int(row[2]),
            "state": str(row[3]),
        }
    collection_id = references.get("media_collection_id")
    if collection_id:
        clause = "AND state='active'" if require_active else ""
        row = conn.execute(
            f"SELECT id, title, revision, state FROM web_media_collections WHERE id=? AND account_id=? {clause}",
            (collection_id, account_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=422, detail="Audio collection liên kết không hợp lệ hoặc không còn hoạt động")
        result["media_collection"] = {
            "id": str(row[0]),
            "title": str(row[1]),
            "revision": int(row[2]),
            "state": str(row[3]),
        }
    return result


def _references_from_row(row: tuple[Any, ...]) -> dict[str, str | None]:
    return {
        "project_id": str(row[1]) if row[1] else None,
        "campaign_plan_id": str(row[2]) if row[2] else None,
        "prompt_template_id": str(row[3]) if row[3] else None,
        "media_collection_id": str(row[4]) if row[4] else None,
    }


class BriefPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str
    content_kind: str
    subject: str
    objective: str = ""
    audience: str = ""
    platform: str = ""
    tone: str = ""
    language: str = "vi"
    call_to_action: str = ""
    brief_text: str
    constraints: str = ""
    tags: list[str] = Field(default_factory=list)
    rights_note: str = ""
    project_id: str | None = None
    campaign_plan_id: str | None = None
    prompt_template_id: str | None = None
    media_collection_id: str | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _single_line(value, label="Tiêu đề brief", minimum=2, maximum=MAX_TITLE)

    @field_validator("content_kind")
    @classmethod
    def validate_content_kind(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in CONTENT_KINDS:
            raise ValueError("Loại Content Studio không hợp lệ")
        return normalized

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, value: str) -> str:
        return _single_line(value, label="Chủ đề", minimum=2, maximum=MAX_SUBJECT)

    @field_validator("objective")
    @classmethod
    def validate_objective(cls, value: str) -> str:
        return _single_line(value, label="Mục tiêu", minimum=0, maximum=MAX_OBJECTIVE, allow_empty=True)

    @field_validator("audience")
    @classmethod
    def validate_audience(cls, value: str) -> str:
        return _single_line(value, label="Đối tượng", minimum=0, maximum=MAX_AUDIENCE, allow_empty=True)

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, value: str) -> str:
        return _single_line(value, label="Nền tảng", minimum=0, maximum=MAX_PLATFORM, allow_empty=True)

    @field_validator("tone")
    @classmethod
    def validate_tone(cls, value: str) -> str:
        return _single_line(value, label="Giọng điệu", minimum=0, maximum=MAX_TONE, allow_empty=True)

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        return _single_line(value, label="Ngôn ngữ", minimum=1, maximum=MAX_LANGUAGE)

    @field_validator("call_to_action")
    @classmethod
    def validate_call_to_action(cls, value: str) -> str:
        return _content(value, label="CTA", maximum=MAX_CALL_TO_ACTION, allow_empty=True)

    @field_validator("brief_text")
    @classmethod
    def validate_brief_text(cls, value: str) -> str:
        return _content(value, label="Nội dung brief", maximum=MAX_BRIEF_TEXT)

    @field_validator("constraints")
    @classmethod
    def validate_constraints(cls, value: str) -> str:
        return _content(value, label="Ràng buộc", maximum=MAX_CONSTRAINTS, allow_empty=True)

    @field_validator("rights_note")
    @classmethod
    def validate_rights_note(cls, value: str) -> str:
        return _content(value, label="Ghi chú quyền sử dụng", maximum=MAX_RIGHTS_NOTE, allow_empty=True)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        return _tags(value)

    @field_validator("project_id", "campaign_plan_id", "prompt_template_id", "media_collection_id", mode="before")
    @classmethod
    def validate_reference_ids(cls, value: Any, info) -> str | None:
        labels = {
            "project_id": "Project ID",
            "campaign_plan_id": "Campaign ID",
            "prompt_template_id": "Prompt template ID",
            "media_collection_id": "Audio collection ID",
        }
        return _optional_uuid(value, label=labels.get(info.field_name, "Reference ID"))


class BriefCreateRequest(BriefPayload):
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)


class BriefUpdateRequest(BriefPayload):
    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)


class RevisionMutationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)


class DuplicateRequest(RevisionMutationRequest):
    title: str = ""

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _single_line(value, label="Tiêu đề bản sao", minimum=0, maximum=MAX_TITLE, allow_empty=True)


class RestoreVersionRequest(RevisionMutationRequest):
    target_revision: int = Field(ge=1)


class ComposeRequest(RevisionMutationRequest):
    pass


class VariantPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    kind: str
    title: str
    content_text: str
    note: str = ""
    tags: list[str] = Field(default_factory=list)

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in VARIANT_KINDS:
            raise ValueError("Loại content piece không hợp lệ")
        return normalized

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _single_line(value, label="Tiêu đề content piece", minimum=2, maximum=MAX_TITLE)

    @field_validator("content_text")
    @classmethod
    def validate_content_text(cls, value: str) -> str:
        return _content(value, label="Nội dung content piece", maximum=MAX_VARIANT_TEXT)

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str) -> str:
        return _content(value, label="Ghi chú content piece", maximum=MAX_VARIANT_NOTE, allow_empty=True)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        return _tags(value)


class VariantCreateRequest(VariantPayload):
    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)


class VariantUpdateRequest(VariantPayload):
    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)


class VariantDuplicateRequest(RevisionMutationRequest):
    title: str = ""

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _single_line(value, label="Tiêu đề bản sao", minimum=0, maximum=MAX_TITLE, allow_empty=True)


class VariantRestoreVersionRequest(RevisionMutationRequest):
    target_revision: int = Field(ge=1)


class SelectVariantRequest(RevisionMutationRequest):
    variant_id: str

    @field_validator("variant_id")
    @classmethod
    def validate_variant_id(cls, value: str) -> str:
        return _uuid(value, label="Content piece ID")


def _payload_references(payload: BriefPayload) -> dict[str, str | None]:
    return {
        "project_id": payload.project_id or None,
        "campaign_plan_id": payload.campaign_plan_id or None,
        "prompt_template_id": payload.prompt_template_id or None,
        "media_collection_id": payload.media_collection_id or None,
    }


def _snapshot_from_payload(
    payload: BriefPayload,
    *,
    state: str = "active",
    marker: str = "",
    references: dict[str, Any] | None = None,
    selected_variant_id: str | None = None,
) -> dict[str, Any]:
    return {
        "title": payload.title,
        "content_kind": payload.content_kind,
        "subject": payload.subject,
        "objective": payload.objective,
        "audience": payload.audience,
        "platform": payload.platform,
        "tone": payload.tone,
        "language": payload.language,
        "call_to_action": payload.call_to_action,
        "brief_text": payload.brief_text,
        "constraints": payload.constraints,
        "tags": list(payload.tags),
        "rights_note": payload.rights_note,
        "references": references or {},
        "reference_ids": _payload_references(payload),
        "policy_marker": marker,
        "state": state,
        "selected_variant_id": selected_variant_id,
    }


def _snapshot_from_row(
    row: tuple[Any, ...],
    *,
    state: str | None = None,
    references: dict[str, Any] | None = None,
    selected_variant_id: str | None = None,
) -> dict[str, Any]:
    return {
        "title": str(row[5]),
        "content_kind": str(row[6]),
        "subject": str(row[7]),
        "objective": str(row[8]),
        "audience": str(row[9]),
        "platform": str(row[10]),
        "tone": str(row[11]),
        "language": str(row[12]),
        "call_to_action": str(row[13]),
        "brief_text": str(row[14]),
        "constraints": str(row[15]),
        "tags": _decode_tags(row[16]),
        "rights_note": str(row[17]),
        "references": references or {},
        "reference_ids": _references_from_row(row),
        "policy_marker": str(row[18] or ""),
        "state": state or str(row[19]),
        "selected_variant_id": selected_variant_id if selected_variant_id is not None else (str(row[20]) if row[20] else None),
    }


def _variant_snapshot_from_payload(
    payload: VariantPayload,
    *,
    state: str = "active",
    source_kind: str = "manual",
    source_brief_revision: int = 1,
) -> dict[str, Any]:
    return {
        "kind": payload.kind,
        "title": payload.title,
        "content_text": payload.content_text,
        "note": payload.note,
        "tags": list(payload.tags),
        "source_kind": source_kind,
        "source_brief_revision": source_brief_revision,
        "state": state,
    }


def _variant_snapshot_from_row(row: tuple[Any, ...], *, state: str | None = None) -> dict[str, Any]:
    return {
        "kind": str(row[2]),
        "title": str(row[4]),
        "content_text": str(row[5]),
        "note": str(row[6]),
        "tags": _decode_tags(row[7]),
        "source_kind": str(row[8]),
        "source_brief_revision": int(row[9]),
        "state": state or str(row[10]),
    }


def _insert_brief(conn: Any, *, brief_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str) -> None:
    reference_ids = snapshot["reference_ids"]
    conn.execute(
        """INSERT INTO web_content_briefs
           (id, account_id, project_id, campaign_plan_id, prompt_template_id, media_collection_id,
            title, content_kind, subject, objective, audience, platform, tone, language, call_to_action,
            brief_text, constraints, tags_json, rights_note, policy_marker, state, selected_variant_id,
            revision, created_at, updated_at, archived_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            brief_id,
            account_id,
            reference_ids.get("project_id"),
            reference_ids.get("campaign_plan_id"),
            reference_ids.get("prompt_template_id"),
            reference_ids.get("media_collection_id"),
            snapshot["title"],
            snapshot["content_kind"],
            snapshot["subject"],
            snapshot["objective"],
            snapshot["audience"],
            snapshot["platform"],
            snapshot["tone"],
            snapshot["language"],
            snapshot["call_to_action"],
            snapshot["brief_text"],
            snapshot["constraints"],
            json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")),
            snapshot["rights_note"],
            snapshot["policy_marker"],
            snapshot["state"],
            snapshot.get("selected_variant_id"),
            revision,
            now,
            now,
            now if snapshot["state"] == "archived" else None,
        ),
    )


def _write_brief(
    conn: Any,
    *,
    brief_id: str,
    account_id: str,
    snapshot: dict[str, Any],
    revision: int,
    now: str,
    archived_at: str | None,
) -> None:
    reference_ids = snapshot["reference_ids"]
    conn.execute(
        """UPDATE web_content_briefs
           SET project_id=?, campaign_plan_id=?, prompt_template_id=?, media_collection_id=?,
               title=?, content_kind=?, subject=?, objective=?, audience=?, platform=?, tone=?, language=?,
               call_to_action=?, brief_text=?, constraints=?, tags_json=?, rights_note=?, policy_marker=?,
               state=?, selected_variant_id=?, revision=?, updated_at=?, archived_at=?
           WHERE id=? AND account_id=?""",
        (
            reference_ids.get("project_id"),
            reference_ids.get("campaign_plan_id"),
            reference_ids.get("prompt_template_id"),
            reference_ids.get("media_collection_id"),
            snapshot["title"],
            snapshot["content_kind"],
            snapshot["subject"],
            snapshot["objective"],
            snapshot["audience"],
            snapshot["platform"],
            snapshot["tone"],
            snapshot["language"],
            snapshot["call_to_action"],
            snapshot["brief_text"],
            snapshot["constraints"],
            json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")),
            snapshot["rights_note"],
            snapshot["policy_marker"],
            snapshot["state"],
            snapshot.get("selected_variant_id"),
            revision,
            now,
            archived_at,
            brief_id,
            account_id,
        ),
    )


def _insert_brief_version(conn: Any, *, brief_id: str, account_id: str, revision: int, snapshot: dict[str, Any], created_at: str) -> None:
    conn.execute(
        """INSERT INTO web_content_brief_versions
           (id, brief_id, account_id, revision, snapshot_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), brief_id, account_id, revision, json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), created_at),
    )


def _can_add_brief_version(conn: Any, *, brief_id: str, account_id: str) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) FROM web_content_brief_versions WHERE brief_id=? AND account_id=?",
        (brief_id, account_id),
    ).fetchone()
    return int(row[0] or 0) < MAX_VERSIONS_PER_ENTITY


def _insert_variant(
    conn: Any,
    *,
    variant_id: str,
    brief_id: str,
    account_id: str,
    ordinal: int,
    snapshot: dict[str, Any],
    revision: int,
    now: str,
) -> None:
    conn.execute(
        """INSERT INTO web_content_variants
           (id, brief_id, account_id, kind, ordinal, title, content_text, note, tags_json, source_kind,
            source_brief_revision, state, revision, created_at, updated_at, archived_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            variant_id,
            brief_id,
            account_id,
            snapshot["kind"],
            ordinal,
            snapshot["title"],
            snapshot["content_text"],
            snapshot["note"],
            json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")),
            snapshot["source_kind"],
            snapshot["source_brief_revision"],
            snapshot["state"],
            revision,
            now,
            now,
            now if snapshot["state"] == "archived" else None,
        ),
    )


def _write_variant(
    conn: Any,
    *,
    variant_id: str,
    brief_id: str,
    account_id: str,
    snapshot: dict[str, Any],
    revision: int,
    now: str,
    archived_at: str | None,
) -> None:
    conn.execute(
        """UPDATE web_content_variants
           SET kind=?, title=?, content_text=?, note=?, tags_json=?, source_kind=?, source_brief_revision=?,
               state=?, revision=?, updated_at=?, archived_at=?
           WHERE id=? AND brief_id=? AND account_id=?""",
        (
            snapshot["kind"],
            snapshot["title"],
            snapshot["content_text"],
            snapshot["note"],
            json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")),
            snapshot["source_kind"],
            snapshot["source_brief_revision"],
            snapshot["state"],
            revision,
            now,
            archived_at,
            variant_id,
            brief_id,
            account_id,
        ),
    )


def _insert_variant_version(conn: Any, *, variant_id: str, account_id: str, revision: int, snapshot: dict[str, Any], created_at: str) -> None:
    conn.execute(
        """INSERT INTO web_content_variant_versions
           (id, variant_id, account_id, revision, snapshot_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), variant_id, account_id, revision, json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), created_at),
    )


def _can_add_variant_version(conn: Any, *, variant_id: str, account_id: str) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) FROM web_content_variant_versions WHERE variant_id=? AND account_id=?",
        (variant_id, account_id),
    ).fetchone()
    return int(row[0] or 0) < MAX_VERSIONS_PER_ENTITY


def _version_limit(entity: str) -> dict[str, Any]:
    return envelope(
        False,
        f"{entity} đã đạt giới hạn lịch sử phiên bản. Hãy archive bản cũ hoặc liên hệ hỗ trợ trước khi tiếp tục thay đổi.",
        status_name="guarded",
        error_code="WEB_CONTENT_VERSION_LIMIT",
    )


def _serialized_bytes(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _account_storage_bytes(conn: Any, *, account_id: str) -> int:
    """Bound authored current data and immutable snapshots, never external data."""

    values: list[int] = []
    queries = (
        """SELECT COALESCE(SUM(
               COALESCE(LENGTH(CAST(title AS BLOB)),0)+COALESCE(LENGTH(CAST(subject AS BLOB)),0)+
               COALESCE(LENGTH(CAST(objective AS BLOB)),0)+COALESCE(LENGTH(CAST(audience AS BLOB)),0)+
               COALESCE(LENGTH(CAST(call_to_action AS BLOB)),0)+COALESCE(LENGTH(CAST(brief_text AS BLOB)),0)+
               COALESCE(LENGTH(CAST(constraints AS BLOB)),0)+COALESCE(LENGTH(CAST(tags_json AS BLOB)),0)+
               COALESCE(LENGTH(CAST(rights_note AS BLOB)),0)
           ),0) FROM web_content_briefs WHERE account_id=?""",
        """SELECT COALESCE(SUM(
               COALESCE(LENGTH(CAST(title AS BLOB)),0)+COALESCE(LENGTH(CAST(content_text AS BLOB)),0)+
               COALESCE(LENGTH(CAST(note AS BLOB)),0)+COALESCE(LENGTH(CAST(tags_json AS BLOB)),0)
           ),0) FROM web_content_variants WHERE account_id=?""",
        "SELECT COALESCE(SUM(COALESCE(LENGTH(CAST(snapshot_json AS BLOB)),0)),0) FROM web_content_brief_versions WHERE account_id=?",
        "SELECT COALESCE(SUM(COALESCE(LENGTH(CAST(snapshot_json AS BLOB)),0)),0) FROM web_content_variant_versions WHERE account_id=?",
    )
    for query in queries:
        row = conn.execute(query, (account_id,)).fetchone()
        values.append(int(row[0] or 0))
    return sum(values)


def _has_storage_capacity(conn: Any, *, account_id: str, additional_bytes: int) -> bool:
    return _account_storage_bytes(conn, account_id=account_id) + max(0, int(additional_bytes)) <= MAX_TOTAL_STORAGE_BYTES


def _storage_limit() -> dict[str, Any]:
    return envelope(
        False,
        "Content Studio đã đạt giới hạn lưu trữ authoring riêng tư của Web account. Hãy archive hoặc dọn bản nháp cũ trước.",
        status_name="guarded",
        error_code="WEB_CONTENT_STORAGE_LIMIT",
    )


def _latest_brief_references(conn: Any, *, brief_id: str, account_id: str) -> dict[str, Any]:
    row = conn.execute(
        """SELECT snapshot_json FROM web_content_brief_versions
           WHERE brief_id=? AND account_id=? ORDER BY revision DESC LIMIT 1""",
        (brief_id, account_id),
    ).fetchone()
    if not row:
        return {}
    try:
        snapshot = json.loads(str(row[0] or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    references = snapshot.get("references") if isinstance(snapshot, dict) else {}
    return references if isinstance(references, dict) else {}


def _brief_version_public(row: tuple[Any, ...]) -> dict[str, Any]:
    try:
        snapshot = json.loads(str(row[1] or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        snapshot = {}
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    references = snapshot.get("references") if isinstance(snapshot.get("references"), dict) else {}
    return {
        "revision": int(row[0]),
        "title": str(snapshot.get("title") or "Content brief"),
        "content_kind": str(snapshot.get("content_kind") or "caption_hashtag"),
        "state": str(snapshot.get("state") or "active"),
        "brief_excerpt": _excerpt(snapshot.get("brief_text")),
        "references": references,
        "created_at": str(row[2]),
    }


def _variant_version_public(row: tuple[Any, ...]) -> dict[str, Any]:
    try:
        snapshot = json.loads(str(row[1] or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        snapshot = {}
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    return {
        "revision": int(row[0]),
        "title": str(snapshot.get("title") or "Content piece"),
        "kind": str(snapshot.get("kind") or "custom"),
        "state": str(snapshot.get("state") or "active"),
        "content_excerpt": _excerpt(snapshot.get("content_text"), limit=360),
        "created_at": str(row[2]),
    }


def _brief_detail(conn: Any, *, brief_id: str, account_id: str) -> dict[str, Any] | None:
    brief = _brief_row(conn, brief_id=brief_id, account_id=account_id)
    if not brief:
        return None
    version_rows = conn.execute(
        """SELECT revision, snapshot_json, created_at FROM web_content_brief_versions
           WHERE brief_id=? AND account_id=? ORDER BY revision DESC LIMIT ?""",
        (brief_id, account_id, MAX_VERSIONS_PER_ENTITY),
    ).fetchall()
    variants = conn.execute(
        """SELECT id, brief_id, kind, ordinal, title, content_text, note, tags_json, source_kind,
                  source_brief_revision, state, revision, created_at, updated_at, archived_at
           FROM web_content_variants
           WHERE brief_id=? AND account_id=?
           ORDER BY CASE state WHEN 'active' THEN 0 ELSE 1 END, ordinal ASC, updated_at DESC, id DESC
           LIMIT ?""",
        (brief_id, account_id, MAX_VARIANTS_PER_BRIEF),
    ).fetchall()
    events = conn.execute(
        """SELECT action, entity_type, variant_id, revision, created_at
           FROM web_content_studio_events WHERE brief_id=? AND account_id=?
           ORDER BY created_at DESC, id DESC LIMIT ?""",
        (brief_id, account_id, MAX_EVENT_LIMIT),
    ).fetchall()
    return {
        "brief": _brief_public(brief, include_content=True),
        "versions": [_brief_version_public(row) for row in version_rows],
        "variants": [_variant_public(row, include_content=True) for row in variants],
        "events": [
            {
                "action": str(row[0]),
                "entity_type": str(row[1]),
                "variant_id": str(row[2]) if row[2] else None,
                "revision": int(row[3]),
                "created_at": str(row[4]),
            }
            for row in events
        ],
        "references": _latest_brief_references(conn, brief_id=brief_id, account_id=account_id),
        "variant_limit": MAX_VARIANTS_PER_BRIEF,
        "variant_count": len(variants),
    }


def _variant_detail(conn: Any, *, brief_id: str, variant_id: str, account_id: str) -> dict[str, Any] | None:
    variant = _variant_row(conn, brief_id=brief_id, variant_id=variant_id, account_id=account_id)
    if not variant:
        return None
    versions = conn.execute(
        """SELECT revision, snapshot_json, created_at FROM web_content_variant_versions
           WHERE variant_id=? AND account_id=? ORDER BY revision DESC LIMIT ?""",
        (variant_id, account_id, MAX_VERSIONS_PER_ENTITY),
    ).fetchall()
    return {
        "variant": _variant_public(variant, include_content=True),
        "versions": [_variant_version_public(row) for row in versions],
    }


def _summary_data(conn: Any, *, account_id: str) -> dict[str, Any]:
    state_rows = conn.execute(
        "SELECT state, COUNT(*) FROM web_content_briefs WHERE account_id=? GROUP BY state",
        (account_id,),
    ).fetchall()
    variant_rows = conn.execute(
        "SELECT state, COUNT(*) FROM web_content_variants WHERE account_id=? GROUP BY state",
        (account_id,),
    ).fetchall()
    kind_rows = conn.execute(
        """SELECT content_kind, COUNT(*) FROM web_content_briefs
           WHERE account_id=? AND state='active' GROUP BY content_kind""",
        (account_id,),
    ).fetchall()
    states = {str(state): int(count) for state, count in state_rows}
    variant_states = {str(state): int(count) for state, count in variant_rows}
    return {
        "briefs": {
            "active": states.get("active", 0),
            "archived": states.get("archived", 0),
            "total": sum(states.values()),
            "limit_per_state": MAX_BRIEFS_PER_STATE,
        },
        "variants": {
            "active": variant_states.get("active", 0),
            "archived": variant_states.get("archived", 0),
            "total": sum(variant_states.values()),
            "limit_per_brief": MAX_VARIANTS_PER_BRIEF,
            "limit_per_account": MAX_VARIANTS_PER_ACCOUNT,
        },
        "by_kind": {str(kind): int(count) for kind, count in kind_rows},
        "execution": "authoring_only",
    }


def _brief_marker(payload: BriefPayload) -> str:
    return _marker(payload.title, payload.subject, payload.brief_text, payload.constraints, payload.call_to_action)


def _variant_marker(payload: VariantPayload) -> str:
    return _marker(payload.title, payload.content_text, payload.note)


def _brief_version_capacity_additional(snapshot: dict[str, Any]) -> int:
    return _serialized_bytes(snapshot) * 2


def _variant_version_capacity_additional(snapshot: dict[str, Any]) -> int:
    return _serialized_bytes(snapshot) * 2


def _brief_state_conflict() -> dict[str, Any]:
    return envelope(
        False,
        "Content brief đã archive và không thể chỉnh sửa trước khi khôi phục.",
        status_name="guarded",
        error_code="WEB_CONTENT_BRIEF_ARCHIVED",
    )


def _variant_state_conflict() -> dict[str, Any]:
    return envelope(
        False,
        "Content piece đã archive và không thể chỉnh sửa trước khi khôi phục.",
        status_name="guarded",
        error_code="WEB_CONTENT_VARIANT_ARCHIVED",
    )


def _revision_conflict() -> dict[str, Any]:
    return envelope(
        False,
        "Dữ liệu đã thay đổi ở nơi khác. Hãy tải lại brief trước khi lưu tiếp.",
        status_name="guarded",
        error_code="WEB_CONTENT_REVISION_CONFLICT",
    )


def _brief_payload_from_snapshot(snapshot: dict[str, Any]) -> BriefPayload:
    reference_ids = snapshot.get("reference_ids") if isinstance(snapshot.get("reference_ids"), dict) else {}
    return BriefPayload.model_validate(
        {
            "title": snapshot.get("title", ""),
            "content_kind": snapshot.get("content_kind", ""),
            "subject": snapshot.get("subject", ""),
            "objective": snapshot.get("objective", ""),
            "audience": snapshot.get("audience", ""),
            "platform": snapshot.get("platform", ""),
            "tone": snapshot.get("tone", ""),
            "language": snapshot.get("language", "vi"),
            "call_to_action": snapshot.get("call_to_action", ""),
            "brief_text": snapshot.get("brief_text", ""),
            "constraints": snapshot.get("constraints", ""),
            "tags": snapshot.get("tags", []),
            "rights_note": snapshot.get("rights_note", ""),
            "project_id": reference_ids.get("project_id"),
            "campaign_plan_id": reference_ids.get("campaign_plan_id"),
            "prompt_template_id": reference_ids.get("prompt_template_id"),
            "media_collection_id": reference_ids.get("media_collection_id"),
        }
    )


def _variant_payload_from_snapshot(snapshot: dict[str, Any]) -> VariantPayload:
    return VariantPayload.model_validate(
        {
            "kind": snapshot.get("kind", ""),
            "title": snapshot.get("title", ""),
            "content_text": snapshot.get("content_text", ""),
            "note": snapshot.get("note", ""),
            "tags": snapshot.get("tags", []),
        }
    )


def _selected_variant_id(conn: Any, *, brief_id: str, account_id: str, candidate: Any) -> str | None:
    raw = str(candidate or "").strip()
    if not raw:
        return None
    try:
        candidate_id = _uuid(raw, label="Content piece ID")
    except HTTPException:
        return None
    row = _variant_row(conn, brief_id=brief_id, variant_id=candidate_id, account_id=account_id)
    return candidate_id if row and str(row[10]) == "active" else None


def _references_listing(conn: Any, *, account_id: str) -> dict[str, list[dict[str, Any]]]:
    projects = conn.execute(
        """SELECT id, title, state, updated_at FROM web_projects
           WHERE account_id=? AND state='active' ORDER BY updated_at DESC, id DESC LIMIT 100""",
        (account_id,),
    ).fetchall()
    campaigns = conn.execute(
        """SELECT id, title, platform, approval_status, updated_at FROM web_campaign_plans
           WHERE account_id=? ORDER BY updated_at DESC, id DESC LIMIT 100""",
        (account_id,),
    ).fetchall()
    templates = conn.execute(
        """SELECT id, title, revision, state, updated_at FROM web_prompt_templates
           WHERE account_id=? AND state='active' ORDER BY updated_at DESC, id DESC LIMIT 100""",
        (account_id,),
    ).fetchall()
    collections = conn.execute(
        """SELECT id, title, revision, state, updated_at FROM web_media_collections
           WHERE account_id=? AND state='active' ORDER BY updated_at DESC, id DESC LIMIT 100""",
        (account_id,),
    ).fetchall()
    return {
        "projects": [{"id": str(row[0]), "title": str(row[1]), "state": str(row[2]), "updated_at": str(row[3])} for row in projects],
        "campaigns": [
            {
                "id": str(row[0]),
                "title": str(row[1]),
                "platform": str(row[2]),
                "approval_status": str(row[3]),
                "updated_at": str(row[4]),
            }
            for row in campaigns
        ],
        "prompt_templates": [
            {"id": str(row[0]), "title": str(row[1]), "revision": int(row[2]), "state": str(row[3]), "updated_at": str(row[4])}
            for row in templates
        ],
        "media_collections": [
            {"id": str(row[0]), "title": str(row[1]), "revision": int(row[2]), "state": str(row[3]), "updated_at": str(row[4])}
            for row in collections
        ],
    }


def _compose_scaffolds(row: tuple[Any, ...]) -> list[dict[str, Any]]:
    """Create three transparent, deterministic authoring scaffolds.

    These are compositional templates, never an AI, engine, provider, job or
    media-output result.  The labels deliberately keep the writer in charge of
    editing every claim before external use.
    """

    kind = str(row[6])
    subject = str(row[7])
    objective = str(row[8]) or "làm rõ giá trị chính"
    audience = str(row[9]) or "khách hàng phù hợp"
    platform = str(row[10]) or "kênh đã chọn"
    tone = str(row[11]) or "rõ ràng, tự nhiên"
    cta = str(row[13]) or "Chọn bước tiếp theo phù hợp."
    tags = _decode_tags(row[16])
    common = f"Chủ đề: {subject}\nMục tiêu: {objective}\nĐối tượng: {audience}\nNền tảng: {platform}\nGiọng điệu: {tone}"
    if kind == "caption_hashtag":
        return [
            {
                "kind": "caption",
                "title": "Khung caption · Góc 01",
                "content_text": f"{common}\n\nMở đầu: [nỗi đau hoặc lợi ích cụ thể]\nNội dung: [2–3 ý có thể kiểm chứng]\nCTA: {cta}",
                "note": "Khung nháp cục bộ; thay thế các phần trong ngoặc bằng thông tin đã kiểm chứng.",
                "tags": tags,
            },
            {
                "kind": "caption",
                "title": "Khung caption · Góc 02",
                "content_text": f"{common}\n\nHook: [một quan sát ngắn]\nCâu chuyện: [bối cảnh → thay đổi → kết quả]\nCTA: {cta}",
                "note": "Khung nháp cục bộ; không tự xác minh số liệu hoặc tuyên bố sản phẩm.",
                "tags": tags,
            },
            {
                "kind": "hashtag_set",
                "title": "Bộ hashtag biên tập",
                "content_text": "Hashtag thương hiệu: [#thuonghieu]\nHashtag chủ đề: [#chude]\nHashtag ngữ cảnh: [#ngucanh]\n\nChọn 3–8 hashtag phù hợp với từng nền tảng; bỏ hashtag không có liên quan.",
                "note": "Khung tag không tự tra cứu xu hướng hoặc hiệu suất.",
                "tags": tags,
            },
        ]
    if kind == "content_ideas":
        return [
            {
                "kind": "content_ideas",
                "title": "Góc nội dung · Vấn đề",
                "content_text": f"{common}\n\nGóc triển khai: nêu một vấn đề người xem tự nhận ra.\nMở đầu: [vấn đề]\n3 ý chính: [ý 1] · [ý 2] · [ý 3]\nCTA: {cta}",
                "note": "Khung brief cục bộ; người viết xác minh insight trước khi dùng.",
                "tags": tags,
            },
            {
                "kind": "content_ideas",
                "title": "Góc nội dung · Quy trình",
                "content_text": f"{common}\n\nGóc triển khai: chia sẻ quy trình hoặc checklist.\nBước 1: [ ]\nBước 2: [ ]\nBước 3: [ ]\nCTA: {cta}",
                "note": "Khung brief cục bộ; không tự tạo dữ liệu nghiên cứu.",
                "tags": tags,
            },
            {
                "kind": "content_ideas",
                "title": "Góc nội dung · Kết quả có điều kiện",
                "content_text": f"{common}\n\nGóc triển khai: mô tả kết quả trong điều kiện rõ ràng.\nĐiều kiện: [ ]\nBằng chứng cần bổ sung: [ ]\nCTA: {cta}",
                "note": "Khung nháp cục bộ; tránh đưa ra cam kết không có chứng cứ.",
                "tags": tags,
            },
        ]
    if kind == "hook_script":
        return [
            {
                "kind": "hook",
                "title": "Hook · Vấn đề rõ ràng",
                "content_text": f"{common}\n\nHook: “Nếu bạn đang gặp [vấn đề cụ thể], hãy thử xem lại [điểm then chốt].”",
                "note": "Khung hook cục bộ; thay thế phần ngoặc bằng thông tin phù hợp.",
                "tags": tags,
            },
            {
                "kind": "script",
                "title": "Script · 15 giây",
                "content_text": f"0–3s: [Hook]\n3–10s: [Một insight hoặc bước thực tế]\n10–13s: [Ví dụ/bằng chứng đã kiểm tra]\n13–15s: {cta}\n\n{common}",
                "note": "Khung kịch bản cục bộ, không bao gồm giọng đọc, render hoặc output media.",
                "tags": tags,
            },
            {
                "kind": "script",
                "title": "Script · 30 giây",
                "content_text": f"0–4s: [Hook]\n4–12s: [Bối cảnh]\n12–22s: [Quy trình hoặc so sánh]\n22–27s: [Bằng chứng cần xác minh]\n27–30s: {cta}\n\n{common}",
                "note": "Khung kịch bản cục bộ; biên tập viên chịu trách nhiệm về claim cuối cùng.",
                "tags": tags,
            },
        ]
    if kind == "content_pack":
        return [
            {
                "kind": "content_pack",
                "title": "Content pack · Thông điệp",
                "content_text": f"Thông điệp chính: [một câu rõ ràng]\nLý do tin: [bằng chứng cần bổ sung]\nCTA: {cta}\n\n{common}",
                "note": "Khung pack cục bộ; không phải bộ nội dung đã được publish hoặc phê duyệt.",
                "tags": tags,
            },
            {
                "kind": "caption",
                "title": "Content pack · Caption",
                "content_text": f"[Hook]\n\n[Giải thích ngắn theo giọng {tone}]\n\n{cta}\n\n{common}",
                "note": "Caption khung cục bộ; kiểm tra quyền sử dụng tài sản và claim trước khi đăng.",
                "tags": tags,
            },
            {
                "kind": "hashtag_set",
                "title": "Content pack · Checklist xuất bản",
                "content_text": "□ Đã kiểm tra tính chính xác của claim\n□ Đã xác nhận quyền sử dụng tài sản\n□ Đã điều chỉnh tỉ lệ/định dạng theo nền tảng\n□ Đã có người chịu trách nhiệm duyệt\n□ Chưa có thao tác publish trong workspace này",
                "note": "Checklist nội bộ; không tạo lịch hoặc gửi nội dung ra kênh bên ngoài.",
                "tags": tags,
            },
        ]
    return [
        {
            "kind": "storyboard",
            "title": "Storyboard · Cảnh 01",
            "content_text": f"Cảnh 01 — Mở\nMục đích: đặt ngữ cảnh cho {subject}.\nKhung hình: [ ]\nHành động: [ ]\nText/VO: [ ]\n\n{common}",
            "note": "Khung storyboard cục bộ; không render hình/video hoặc tạo job.",
            "tags": tags,
        },
        {
            "kind": "storyboard",
            "title": "Storyboard · Cảnh 02",
            "content_text": "Cảnh 02 — Giá trị\nMục đích: trình bày insight hoặc quy trình.\nKhung hình: [ ]\nChuyển động: [ ]\nText/VO: [ ]\nBằng chứng cần xác nhận: [ ]",
            "note": "Khung storyboard cục bộ; camera, asset và âm thanh phải được đội ngũ sản xuất xác nhận.",
            "tags": tags,
        },
        {
            "kind": "storyboard",
            "title": "Storyboard · Cảnh 03",
            "content_text": f"Cảnh 03 — Kết\nMục đích: củng cố ý chính và CTA.\nKhung hình: [ ]\nText/VO: {cta}\nKiểm tra quyền sử dụng asset: [ ]",
            "note": "Khung storyboard cục bộ; chưa có output media hoặc lịch xuất bản.",
            "tags": tags,
        },
    ]


@router.get("/summary")
async def content_studio_summary(account: dict = Depends(require_account)):
    _require_enabled()
    with read_transaction() as conn:
        data = _summary_data(conn, account_id=str(account["id"]))
    return envelope(True, "Đã tải tổng quan Creative Content Studio riêng tư.", data=data, status_name="read_only")


@router.get("/policy")
async def content_studio_policy(account: dict = Depends(require_account)):
    _require_enabled()
    return envelope(
        True,
        "Content Studio chỉ lưu brief và content piece của signed Web account.",
        data={
            "execution": "authoring_only",
            "compose_execution": "local_deterministic_draft_only",
            "provider_called": False,
            "charge_started": False,
            "guardrails": [
                "Không gọi Bot, provider, payment, ví, job, publish hoặc delivery.",
                "Không lưu URL, path, file ID, token, mã xác thực hoặc chứng từ thanh toán.",
                "Mọi content piece cần được người dùng biên tập và xác minh trước khi sử dụng bên ngoài.",
                "Yêu cầu mô phỏng tác giả, nghệ sĩ hoặc phong cách cụ thể được chặn ở policy guard.",
            ],
        },
        status_name="read_only",
    )


@router.get("/references")
async def content_studio_references(account: dict = Depends(require_account)):
    _require_enabled()
    with read_transaction() as conn:
        data = _references_listing(conn, account_id=str(account["id"]))
    return envelope(True, "Đã tải các reference riêng tư có thể liên kết vào brief.", data=data, status_name="read_only")


@router.get("/briefs")
async def list_briefs(
    limit: int = 30,
    state: str = "active",
    q: str = "",
    tag: str = "",
    content_kind: str = "",
    account: dict = Depends(require_account),
):
    _require_enabled()
    bounded = max(1, min(int(limit), MAX_LIST_LIMIT))
    state_filter = str(state or "active").strip().lower()
    if state_filter not in {*BRIEF_STATES, "all"}:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái content brief không hợp lệ")
    kind_filter = _safe_filter(content_kind, label="Loại content", maximum=32).lower()
    if kind_filter and kind_filter not in CONTENT_KINDS:
        raise HTTPException(status_code=422, detail="Bộ lọc loại Content Studio không hợp lệ")
    query = _safe_filter(q, label="Từ khóa content brief", maximum=100)
    tag_filter = _safe_filter(tag, label="Tag", maximum=MAX_TAG_LENGTH)
    clauses = ["account_id=?"]
    params: list[Any] = [str(account["id"])]
    if state_filter != "all":
        clauses.append("state=?")
        params.append(state_filter)
    if kind_filter:
        clauses.append("content_kind=?")
        params.append(kind_filter)
    if query:
        like = f"%{_escaped_like(query)}%"
        clauses.append("(title LIKE ? ESCAPE '\\' OR subject LIKE ? ESCAPE '\\' OR brief_text LIKE ? ESCAPE '\\')")
        params.extend([like, like, like])
    if tag_filter:
        clauses.append("tags_json LIKE ? ESCAPE '\\'")
        params.append(f"%{_escaped_like(tag_filter)}%")
    with read_transaction() as conn:
        rows = conn.execute(
            f"""SELECT id, project_id, campaign_plan_id, prompt_template_id, media_collection_id,
                       title, content_kind, subject, objective, audience, platform, tone, language,
                       call_to_action, brief_text, constraints, tags_json, rights_note, policy_marker,
                       state, selected_variant_id, revision, created_at, updated_at, archived_at
                FROM web_content_briefs WHERE {' AND '.join(clauses)}
                ORDER BY updated_at DESC, id DESC LIMIT ?""",
            (*params, bounded + 1),
        ).fetchall()
    return envelope(
        True,
        "Đã tải danh sách Content Studio riêng tư.",
        data={"items": [_brief_public(row) for row in rows[:bounded]], "has_more": len(rows) > bounded},
        status_name="read_only",
    )


@router.post("/briefs")
async def create_brief(payload: BriefCreateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    account_id = str(account["id"])
    marker = _brief_marker(payload)
    references = _payload_references(payload)
    fingerprint = _fingerprint(
        {
            "title": payload.title,
            "kind": payload.content_kind,
            "subject": _hash(payload.subject),
            "objective": _hash(payload.objective),
            "audience": _hash(payload.audience),
            "brief": _hash(payload.brief_text),
            "constraints": _hash(payload.constraints),
            "cta": _hash(payload.call_to_action),
            "tags": payload.tags,
            "rights": _hash(payload.rights_note),
            "references": references,
        }
    )

    def operation(conn: Any) -> dict[str, Any]:
        guard = _policy_guard(marker)
        if guard:
            return guard
        count = conn.execute(
            "SELECT COUNT(*) FROM web_content_briefs WHERE account_id=? AND state='active'",
            (account_id,),
        ).fetchone()
        if int(count[0] or 0) >= MAX_BRIEFS_PER_STATE:
            return envelope(
                False,
                "Đã đạt giới hạn content brief active của Web account. Hãy archive brief cũ trước.",
                status_name="guarded",
                error_code="WEB_CONTENT_BRIEF_LIMIT",
            )
        reference_snapshot = _reference_snapshot(conn, account_id=account_id, references=references)
        snapshot = _snapshot_from_payload(payload, marker=marker, references=reference_snapshot)
        if not _has_storage_capacity(conn, account_id=account_id, additional_bytes=_brief_version_capacity_additional(snapshot)):
            return _storage_limit()
        brief_id = str(uuid.uuid4())
        now = utc_now()
        _insert_brief(conn, brief_id=brief_id, account_id=account_id, snapshot=snapshot, revision=1, now=now)
        _insert_brief_version(conn, brief_id=brief_id, account_id=account_id, revision=1, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, brief_id=brief_id, action="brief_created", revision=1)
        _audit(conn, request=request, account=account, action="web.content.brief.create", target=brief_id, detail=f"kind={payload.content_kind};references={len(reference_snapshot)}")
        created = _brief_row(conn, brief_id=brief_id, account_id=account_id)
        return envelope(
            True,
            "Đã tạo Content Studio brief riêng tư.",
            data={"brief": _brief_public(created, include_content=True), "execution": "authoring_only"},
            status_name="draft",
        )

    return _idempotent(f"web-content-studio:{account_id}:brief:create", account_id, payload.idempotency_key, fingerprint, operation)


@router.get("/briefs/{brief_id}")
async def get_brief(brief_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    brief_id = _uuid(brief_id, label="Content brief ID")
    with read_transaction() as conn:
        detail = _brief_detail(conn, brief_id=brief_id, account_id=str(account["id"]))
    if not detail:
        return _brief_not_found()
    return envelope(True, "Đã tải Content Studio brief cùng history và content pieces.", data=detail, status_name="read_only")


@router.patch("/briefs/{brief_id}")
async def update_brief(brief_id: str, payload: BriefUpdateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    brief_id = _uuid(brief_id, label="Content brief ID")
    account_id = str(account["id"])
    marker = _brief_marker(payload)
    references = _payload_references(payload)
    fingerprint = _fingerprint(
        {
            "id": brief_id,
            "revision": payload.expected_revision,
            "title": payload.title,
            "kind": payload.content_kind,
            "subject": _hash(payload.subject),
            "objective": _hash(payload.objective),
            "audience": _hash(payload.audience),
            "brief": _hash(payload.brief_text),
            "constraints": _hash(payload.constraints),
            "cta": _hash(payload.call_to_action),
            "tags": payload.tags,
            "rights": _hash(payload.rights_note),
            "references": references,
        }
    )

    def operation(conn: Any) -> dict[str, Any]:
        current = _brief_row(conn, brief_id=brief_id, account_id=account_id)
        if not current:
            return _brief_not_found()
        if int(current[21]) != payload.expected_revision:
            return _revision_conflict()
        if str(current[19]) != "active":
            return _brief_state_conflict()
        guard = _policy_guard(marker)
        if guard:
            return guard
        if not _can_add_brief_version(conn, brief_id=brief_id, account_id=account_id):
            return _version_limit("Content brief")
        reference_snapshot = _reference_snapshot(conn, account_id=account_id, references=references)
        snapshot = _snapshot_from_payload(
            payload,
            marker=marker,
            references=reference_snapshot,
            selected_variant_id=_selected_variant_id(conn, brief_id=brief_id, account_id=account_id, candidate=current[20]),
        )
        if not _has_storage_capacity(conn, account_id=account_id, additional_bytes=_serialized_bytes(snapshot)):
            return _storage_limit()
        revision = int(current[21]) + 1
        now = utc_now()
        _write_brief(conn, brief_id=brief_id, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_brief_version(conn, brief_id=brief_id, account_id=account_id, revision=revision, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, brief_id=brief_id, action="brief_updated", revision=revision)
        _audit(conn, request=request, account=account, action="web.content.brief.update", target=brief_id, detail=f"revision={revision};kind={payload.content_kind}")
        updated = _brief_row(conn, brief_id=brief_id, account_id=account_id)
        return envelope(
            True,
            "Đã lưu phiên bản Content Studio brief mới.",
            data={"brief": _brief_public(updated, include_content=True), "execution": "authoring_only"},
            status_name="draft",
        )

    return _idempotent(f"web-content-studio:{account_id}:brief:{brief_id}:update", account_id, payload.idempotency_key, fingerprint, operation)


def _brief_state_transition(
    *,
    brief_id: str,
    payload: RevisionMutationRequest,
    request: Request,
    account: dict,
    target_state: str,
    action: str,
) -> dict[str, Any]:
    account_id = str(account["id"])
    fingerprint = _fingerprint({"id": brief_id, "revision": payload.expected_revision, "action": action})

    def operation(conn: Any) -> dict[str, Any]:
        current = _brief_row(conn, brief_id=brief_id, account_id=account_id)
        if not current:
            return _brief_not_found()
        if int(current[21]) != payload.expected_revision:
            return _revision_conflict()
        if str(current[19]) == target_state:
            return envelope(
                False,
                "Content brief đã ở trạng thái yêu cầu.",
                status_name="guarded",
                error_code="WEB_CONTENT_BRIEF_STATE",
            )
        references = _references_from_row(current)
        # A restore makes a record editable again, so all new external
        # references must still be active and owner-scoped.  Archive is always
        # permitted even if an old reference was later archived.
        reference_snapshot = (
            _reference_snapshot(conn, account_id=account_id, references=references)
            if target_state == "active"
            else _latest_brief_references(conn, brief_id=brief_id, account_id=account_id)
        )
        snapshot = _snapshot_from_row(
            current,
            state=target_state,
            references=reference_snapshot,
            selected_variant_id=_selected_variant_id(conn, brief_id=brief_id, account_id=account_id, candidate=current[20]),
        )
        revision = int(current[21]) + 1
        now = utc_now()
        _write_brief(
            conn,
            brief_id=brief_id,
            account_id=account_id,
            snapshot=snapshot,
            revision=revision,
            now=now,
            archived_at=now if target_state == "archived" else None,
        )
        snapshot_recorded = _can_add_brief_version(conn, brief_id=brief_id, account_id=account_id)
        if snapshot_recorded:
            _insert_brief_version(conn, brief_id=brief_id, account_id=account_id, revision=revision, snapshot=snapshot, created_at=now)
        _event(
            conn,
            account_id=account_id,
            brief_id=brief_id,
            action=action if snapshot_recorded else f"{action}_without_snapshot",
            revision=revision,
        )
        _audit(
            conn,
            request=request,
            account=account,
            action=f"web.content.brief.{action}",
            target=brief_id,
            detail=f"revision={revision};snapshot={'yes' if snapshot_recorded else 'no'}",
        )
        updated = _brief_row(conn, brief_id=brief_id, account_id=account_id)
        return envelope(
            True,
            "Đã cập nhật trạng thái Content Studio brief."
            + (" Lịch sử đã đạt giới hạn nên lần chuyển trạng thái này không thêm snapshot mới." if not snapshot_recorded else ""),
            data={
                "brief": _brief_public(updated, include_content=True),
                "history_snapshot_recorded": snapshot_recorded,
                "execution": "authoring_only",
            },
            status_name="draft",
        )

    return _idempotent(f"web-content-studio:{account_id}:brief:{brief_id}:{action}", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/briefs/{brief_id}/archive")
async def archive_brief(brief_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    return _brief_state_transition(
        brief_id=_uuid(brief_id, label="Content brief ID"),
        payload=payload,
        request=request,
        account=account,
        target_state="archived",
        action="brief_archived",
    )


@router.post("/briefs/{brief_id}/restore")
async def restore_brief(brief_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    return _brief_state_transition(
        brief_id=_uuid(brief_id, label="Content brief ID"),
        payload=payload,
        request=request,
        account=account,
        target_state="active",
        action="brief_restored",
    )


@router.post("/briefs/{brief_id}/duplicate")
async def duplicate_brief(brief_id: str, payload: DuplicateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    brief_id = _uuid(brief_id, label="Content brief ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"id": brief_id, "revision": payload.expected_revision, "title": payload.title})

    def operation(conn: Any) -> dict[str, Any]:
        source = _brief_row(conn, brief_id=brief_id, account_id=account_id)
        if not source:
            return _brief_not_found()
        if int(source[21]) != payload.expected_revision:
            return _revision_conflict()
        if str(source[19]) != "active":
            return _brief_state_conflict()
        count = conn.execute(
            "SELECT COUNT(*) FROM web_content_briefs WHERE account_id=? AND state='active'",
            (account_id,),
        ).fetchone()
        if int(count[0] or 0) >= MAX_BRIEFS_PER_STATE:
            return envelope(False, "Đã đạt giới hạn content brief active của Web account. Hãy archive brief cũ trước.", status_name="guarded", error_code="WEB_CONTENT_BRIEF_LIMIT")
        references = _reference_snapshot(conn, account_id=account_id, references=_references_from_row(source))
        snapshot = _snapshot_from_row(source, state="active", references=references, selected_variant_id=None)
        snapshot["title"] = payload.title or f"{snapshot['title']} (bản sao)"
        marker = _marker(snapshot["title"], snapshot["subject"], snapshot["brief_text"], snapshot["constraints"], snapshot["call_to_action"])
        guard = _policy_guard(marker)
        if guard:
            return guard
        snapshot["policy_marker"] = marker
        if not _has_storage_capacity(conn, account_id=account_id, additional_bytes=_brief_version_capacity_additional(snapshot)):
            return _storage_limit()
        new_id = str(uuid.uuid4())
        now = utc_now()
        _insert_brief(conn, brief_id=new_id, account_id=account_id, snapshot=snapshot, revision=1, now=now)
        _insert_brief_version(conn, brief_id=new_id, account_id=account_id, revision=1, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, brief_id=new_id, action="brief_duplicated", revision=1)
        _audit(conn, request=request, account=account, action="web.content.brief.duplicate", target=new_id, detail=f"source={brief_id};kind={snapshot['content_kind']}")
        duplicated = _brief_row(conn, brief_id=new_id, account_id=account_id)
        return envelope(
            True,
            "Đã nhân bản Content Studio brief. Content pieces không được sao chép tự động để tránh nhầm lẫn với nội dung đã review.",
            data={"brief": _brief_public(duplicated, include_content=True), "execution": "authoring_only"},
            status_name="draft",
        )

    return _idempotent(f"web-content-studio:{account_id}:brief:{brief_id}:duplicate", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/briefs/{brief_id}/restore-version")
async def restore_brief_version(brief_id: str, payload: RestoreVersionRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    brief_id = _uuid(brief_id, label="Content brief ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"id": brief_id, "revision": payload.expected_revision, "target_revision": payload.target_revision})

    def operation(conn: Any) -> dict[str, Any]:
        current = _brief_row(conn, brief_id=brief_id, account_id=account_id)
        if not current:
            return _brief_not_found()
        if int(current[21]) != payload.expected_revision:
            return _revision_conflict()
        if str(current[19]) != "active":
            return _brief_state_conflict()
        version = conn.execute(
            """SELECT snapshot_json FROM web_content_brief_versions
               WHERE brief_id=? AND account_id=? AND revision=?""",
            (brief_id, account_id, payload.target_revision),
        ).fetchone()
        if not version:
            return envelope(False, "Không tìm thấy phiên bản brief cần khôi phục.", status_name="guarded", error_code="WEB_CONTENT_VERSION_NOT_FOUND")
        try:
            stored = json.loads(str(version[0] or "{}"))
            recovered = _brief_payload_from_snapshot(stored if isinstance(stored, dict) else {})
        except (TypeError, ValueError, json.JSONDecodeError):
            return envelope(False, "Phiên bản brief không còn hợp lệ để khôi phục.", status_name="guarded", error_code="WEB_CONTENT_VERSION_INVALID")
        marker = _brief_marker(recovered)
        guard = _policy_guard(marker)
        if guard:
            return guard
        if not _can_add_brief_version(conn, brief_id=brief_id, account_id=account_id):
            return _version_limit("Content brief")
        references = _reference_snapshot(conn, account_id=account_id, references=_payload_references(recovered))
        snapshot = _snapshot_from_payload(
            recovered,
            marker=marker,
            references=references,
            selected_variant_id=_selected_variant_id(conn, brief_id=brief_id, account_id=account_id, candidate=stored.get("selected_variant_id") if isinstance(stored, dict) else None),
        )
        if not _has_storage_capacity(conn, account_id=account_id, additional_bytes=_serialized_bytes(snapshot)):
            return _storage_limit()
        revision = int(current[21]) + 1
        now = utc_now()
        _write_brief(conn, brief_id=brief_id, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_brief_version(conn, brief_id=brief_id, account_id=account_id, revision=revision, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, brief_id=brief_id, action="brief_version_restored", revision=revision)
        _audit(conn, request=request, account=account, action="web.content.brief.restore_version", target=brief_id, detail=f"from_revision={payload.target_revision};revision={revision}")
        updated = _brief_row(conn, brief_id=brief_id, account_id=account_id)
        return envelope(True, "Đã khôi phục phiên bản Content Studio brief.", data={"brief": _brief_public(updated, include_content=True), "execution": "authoring_only"}, status_name="draft")

    return _idempotent(f"web-content-studio:{account_id}:brief:{brief_id}:restore-version", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/briefs/{brief_id}/compose")
async def compose_brief(brief_id: str, payload: ComposeRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    brief_id = _uuid(brief_id, label="Content brief ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"id": brief_id, "revision": payload.expected_revision, "operation": "compose-local-drafts"})

    def operation(conn: Any) -> dict[str, Any]:
        brief = _brief_row(conn, brief_id=brief_id, account_id=account_id)
        if not brief:
            return _brief_not_found()
        if int(brief[21]) != payload.expected_revision:
            return _revision_conflict()
        if str(brief[19]) != "active":
            return _brief_state_conflict()
        guard = _policy_guard(str(brief[18] or ""))
        if guard:
            return guard
        scaffolds = _compose_scaffolds(brief)
        existing = conn.execute(
            "SELECT COUNT(*) FROM web_content_variants WHERE brief_id=? AND account_id=?",
            (brief_id, account_id),
        ).fetchone()
        account_variants = conn.execute(
            "SELECT COUNT(*) FROM web_content_variants WHERE account_id=?",
            (account_id,),
        ).fetchone()
        if int(existing[0] or 0) + len(scaffolds) > MAX_VARIANTS_PER_BRIEF or int(account_variants[0] or 0) + len(scaffolds) > MAX_VARIANTS_PER_ACCOUNT:
            return envelope(
                False,
                "Đã đạt giới hạn content piece của brief hoặc Web account. Hãy archive/bớt bản nháp trước khi tạo thêm.",
                status_name="guarded",
                error_code="WEB_CONTENT_VARIANT_LIMIT",
            )
        additional = sum(_serialized_bytes(item) * 2 for item in scaffolds)
        if not _has_storage_capacity(conn, account_id=account_id, additional_bytes=additional):
            return _storage_limit()
        ordinal_row = conn.execute(
            "SELECT COALESCE(MAX(ordinal), 0) FROM web_content_variants WHERE brief_id=? AND account_id=?",
            (brief_id, account_id),
        ).fetchone()
        ordinal = int(ordinal_row[0] or 0)
        now = utc_now()
        ids: list[str] = []
        for scaffold in scaffolds:
            variant_payload = VariantPayload.model_validate(scaffold)
            marker = _variant_marker(variant_payload)
            if marker:
                return _policy_guard(marker) or envelope(False, "Content piece bị chặn.", status_name="guarded")
            ordinal += 1
            variant_id = str(uuid.uuid4())
            snapshot = _variant_snapshot_from_payload(
                variant_payload,
                source_kind="local_deterministic_draft_only",
                source_brief_revision=int(brief[21]),
            )
            _insert_variant(conn, variant_id=variant_id, brief_id=brief_id, account_id=account_id, ordinal=ordinal, snapshot=snapshot, revision=1, now=now)
            _insert_variant_version(conn, variant_id=variant_id, account_id=account_id, revision=1, snapshot=snapshot, created_at=now)
            _event(conn, account_id=account_id, brief_id=brief_id, variant_id=variant_id, action="variant_composed_local", revision=1)
            ids.append(variant_id)
        _event(conn, account_id=account_id, brief_id=brief_id, action="brief_composed_local", revision=int(brief[21]))
        _audit(conn, request=request, account=account, action="web.content.brief.compose", target=brief_id, detail=f"kind={brief[6]};variants={len(ids)};execution=local")
        return envelope(
            True,
            "Đã tạo 3 khung nháp cục bộ để bạn biên tập. Đây không phải kết quả AI, job, output media hoặc nội dung đã publish.",
            data={
                "brief": _brief_public(brief, include_content=True),
                "variant_ids": ids,
                "variant_count": len(ids),
                "execution": "local_deterministic_draft_only",
                "provider_called": False,
                "charge_started": False,
            },
            status_name="draft",
        )

    return _idempotent(f"web-content-studio:{account_id}:brief:{brief_id}:compose", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/briefs/{brief_id}/variants")
async def create_variant(brief_id: str, payload: VariantCreateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    brief_id = _uuid(brief_id, label="Content brief ID")
    account_id = str(account["id"])
    marker = _variant_marker(payload)
    fingerprint = _fingerprint(
        {
            "brief_id": brief_id,
            "brief_revision": payload.expected_revision,
            "kind": payload.kind,
            "title": payload.title,
            "content": _hash(payload.content_text),
            "note": _hash(payload.note),
            "tags": payload.tags,
        }
    )

    def operation(conn: Any) -> dict[str, Any]:
        brief = _brief_row(conn, brief_id=brief_id, account_id=account_id)
        if not brief:
            return _brief_not_found()
        if int(brief[21]) != payload.expected_revision:
            return _revision_conflict()
        if str(brief[19]) != "active":
            return _brief_state_conflict()
        guard = _policy_guard(marker)
        if guard:
            return guard
        brief_count = conn.execute(
            "SELECT COUNT(*) FROM web_content_variants WHERE brief_id=? AND account_id=?",
            (brief_id, account_id),
        ).fetchone()
        account_count = conn.execute(
            "SELECT COUNT(*) FROM web_content_variants WHERE account_id=?",
            (account_id,),
        ).fetchone()
        if int(brief_count[0] or 0) >= MAX_VARIANTS_PER_BRIEF or int(account_count[0] or 0) >= MAX_VARIANTS_PER_ACCOUNT:
            return envelope(
                False,
                "Đã đạt giới hạn content piece của brief hoặc Web account. Hãy archive/bớt bản nháp trước khi tạo thêm.",
                status_name="guarded",
                error_code="WEB_CONTENT_VARIANT_LIMIT",
            )
        snapshot = _variant_snapshot_from_payload(payload, source_kind="manual", source_brief_revision=int(brief[21]))
        if not _has_storage_capacity(conn, account_id=account_id, additional_bytes=_variant_version_capacity_additional(snapshot)):
            return _storage_limit()
        ordinal_row = conn.execute(
            "SELECT COALESCE(MAX(ordinal), 0) FROM web_content_variants WHERE brief_id=? AND account_id=?",
            (brief_id, account_id),
        ).fetchone()
        variant_id = str(uuid.uuid4())
        now = utc_now()
        _insert_variant(
            conn,
            variant_id=variant_id,
            brief_id=brief_id,
            account_id=account_id,
            ordinal=int(ordinal_row[0] or 0) + 1,
            snapshot=snapshot,
            revision=1,
            now=now,
        )
        _insert_variant_version(conn, variant_id=variant_id, account_id=account_id, revision=1, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, brief_id=brief_id, variant_id=variant_id, action="variant_created", revision=1)
        _audit(conn, request=request, account=account, action="web.content.variant.create", target=variant_id, detail=f"brief={brief_id};kind={payload.kind}")
        created = _variant_row(conn, brief_id=brief_id, variant_id=variant_id, account_id=account_id)
        return envelope(
            True,
            "Đã thêm content piece vào brief.",
            data={"brief": _brief_public(brief), "variant": _variant_public(created, include_content=True), "execution": "authoring_only"},
            status_name="draft",
        )

    return _idempotent(f"web-content-studio:{account_id}:brief:{brief_id}:variant:create", account_id, payload.idempotency_key, fingerprint, operation)


@router.get("/briefs/{brief_id}/variants/{variant_id}")
async def get_variant(brief_id: str, variant_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    brief_id = _uuid(brief_id, label="Content brief ID")
    variant_id = _uuid(variant_id, label="Content piece ID")
    with read_transaction() as conn:
        detail = _variant_detail(conn, brief_id=brief_id, variant_id=variant_id, account_id=str(account["id"]))
    if not detail:
        return _variant_not_found()
    return envelope(True, "Đã tải content piece cùng lịch sử phiên bản riêng tư.", data=detail, status_name="read_only")


@router.patch("/briefs/{brief_id}/variants/{variant_id}")
async def update_variant(
    brief_id: str,
    variant_id: str,
    payload: VariantUpdateRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    _require_enabled()
    brief_id = _uuid(brief_id, label="Content brief ID")
    variant_id = _uuid(variant_id, label="Content piece ID")
    account_id = str(account["id"])
    marker = _variant_marker(payload)
    fingerprint = _fingerprint(
        {
            "brief_id": brief_id,
            "variant_id": variant_id,
            "revision": payload.expected_revision,
            "kind": payload.kind,
            "title": payload.title,
            "content": _hash(payload.content_text),
            "note": _hash(payload.note),
            "tags": payload.tags,
        }
    )

    def operation(conn: Any) -> dict[str, Any]:
        brief = _brief_row(conn, brief_id=brief_id, account_id=account_id)
        if not brief:
            return _brief_not_found()
        variant = _variant_row(conn, brief_id=brief_id, variant_id=variant_id, account_id=account_id)
        if not variant:
            return _variant_not_found()
        if int(variant[11]) != payload.expected_revision:
            return _revision_conflict()
        if str(variant[10]) != "active":
            return _variant_state_conflict()
        guard = _policy_guard(marker)
        if guard:
            return guard
        if not _can_add_variant_version(conn, variant_id=variant_id, account_id=account_id):
            return _version_limit("Content piece")
        snapshot = _variant_snapshot_from_payload(payload, source_kind="manual", source_brief_revision=int(brief[21]))
        if not _has_storage_capacity(conn, account_id=account_id, additional_bytes=_serialized_bytes(snapshot)):
            return _storage_limit()
        revision = int(variant[11]) + 1
        now = utc_now()
        _write_variant(
            conn,
            variant_id=variant_id,
            brief_id=brief_id,
            account_id=account_id,
            snapshot=snapshot,
            revision=revision,
            now=now,
            archived_at=None,
        )
        _insert_variant_version(conn, variant_id=variant_id, account_id=account_id, revision=revision, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, brief_id=brief_id, variant_id=variant_id, action="variant_updated", revision=revision)
        _audit(conn, request=request, account=account, action="web.content.variant.update", target=variant_id, detail=f"brief={brief_id};revision={revision};kind={payload.kind}")
        updated = _variant_row(conn, brief_id=brief_id, variant_id=variant_id, account_id=account_id)
        return envelope(
            True,
            "Đã lưu phiên bản content piece mới.",
            data={"brief": _brief_public(brief), "variant": _variant_public(updated, include_content=True), "execution": "authoring_only"},
            status_name="draft",
        )

    return _idempotent(f"web-content-studio:{account_id}:brief:{brief_id}:variant:{variant_id}:update", account_id, payload.idempotency_key, fingerprint, operation)


def _variant_state_transition(
    *,
    brief_id: str,
    variant_id: str,
    payload: RevisionMutationRequest,
    request: Request,
    account: dict,
    target_state: str,
    action: str,
) -> dict[str, Any]:
    account_id = str(account["id"])
    fingerprint = _fingerprint({"brief_id": brief_id, "variant_id": variant_id, "revision": payload.expected_revision, "action": action})

    def operation(conn: Any) -> dict[str, Any]:
        brief = _brief_row(conn, brief_id=brief_id, account_id=account_id)
        if not brief:
            return _brief_not_found()
        current = _variant_row(conn, brief_id=brief_id, variant_id=variant_id, account_id=account_id)
        if not current:
            return _variant_not_found()
        if int(current[11]) != payload.expected_revision:
            return _revision_conflict()
        if str(current[10]) == target_state:
            return envelope(False, "Content piece đã ở trạng thái yêu cầu.", status_name="guarded", error_code="WEB_CONTENT_VARIANT_STATE")
        snapshot = _variant_snapshot_from_row(current, state=target_state)
        revision = int(current[11]) + 1
        now = utc_now()
        _write_variant(
            conn,
            variant_id=variant_id,
            brief_id=brief_id,
            account_id=account_id,
            snapshot=snapshot,
            revision=revision,
            now=now,
            archived_at=now if target_state == "archived" else None,
        )
        snapshot_recorded = _can_add_variant_version(conn, variant_id=variant_id, account_id=account_id)
        if snapshot_recorded:
            _insert_variant_version(conn, variant_id=variant_id, account_id=account_id, revision=revision, snapshot=snapshot, created_at=now)
        if target_state == "archived" and str(brief[20] or "") == variant_id:
            # Never retain a selected piece that can no longer be edited or
            # used as the active authoring selection. This is an integrity
            # cleanup, not a browser-controlled role/permission mutation.
            conn.execute(
                "UPDATE web_content_briefs SET selected_variant_id=? WHERE id=? AND account_id=?",
                (None, brief_id, account_id),
            )
        _event(
            conn,
            account_id=account_id,
            brief_id=brief_id,
            variant_id=variant_id,
            action=action if snapshot_recorded else f"{action}_without_snapshot",
            revision=revision,
        )
        _audit(
            conn,
            request=request,
            account=account,
            action=f"web.content.variant.{action}",
            target=variant_id,
            detail=f"brief={brief_id};revision={revision};snapshot={'yes' if snapshot_recorded else 'no'}",
        )
        updated = _variant_row(conn, brief_id=brief_id, variant_id=variant_id, account_id=account_id)
        return envelope(
            True,
            "Đã cập nhật trạng thái content piece."
            + (" Lịch sử đã đạt giới hạn nên lần chuyển trạng thái này không thêm snapshot mới." if not snapshot_recorded else ""),
            data={
                "brief": _brief_public(_brief_row(conn, brief_id=brief_id, account_id=account_id)),
                "variant": _variant_public(updated, include_content=True),
                "history_snapshot_recorded": snapshot_recorded,
                "execution": "authoring_only",
            },
            status_name="draft",
        )

    return _idempotent(f"web-content-studio:{account_id}:brief:{brief_id}:variant:{variant_id}:{action}", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/briefs/{brief_id}/variants/{variant_id}/archive")
async def archive_variant(brief_id: str, variant_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    return _variant_state_transition(
        brief_id=_uuid(brief_id, label="Content brief ID"),
        variant_id=_uuid(variant_id, label="Content piece ID"),
        payload=payload,
        request=request,
        account=account,
        target_state="archived",
        action="variant_archived",
    )


@router.post("/briefs/{brief_id}/variants/{variant_id}/restore")
async def restore_variant(brief_id: str, variant_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    return _variant_state_transition(
        brief_id=_uuid(brief_id, label="Content brief ID"),
        variant_id=_uuid(variant_id, label="Content piece ID"),
        payload=payload,
        request=request,
        account=account,
        target_state="active",
        action="variant_restored",
    )


@router.post("/briefs/{brief_id}/variants/{variant_id}/duplicate")
async def duplicate_variant(brief_id: str, variant_id: str, payload: VariantDuplicateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    brief_id = _uuid(brief_id, label="Content brief ID")
    variant_id = _uuid(variant_id, label="Content piece ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"brief_id": brief_id, "variant_id": variant_id, "revision": payload.expected_revision, "title": payload.title})

    def operation(conn: Any) -> dict[str, Any]:
        brief = _brief_row(conn, brief_id=brief_id, account_id=account_id)
        if not brief:
            return _brief_not_found()
        source = _variant_row(conn, brief_id=brief_id, variant_id=variant_id, account_id=account_id)
        if not source:
            return _variant_not_found()
        if int(source[11]) != payload.expected_revision:
            return _revision_conflict()
        if str(source[10]) != "active":
            return _variant_state_conflict()
        count = conn.execute("SELECT COUNT(*) FROM web_content_variants WHERE brief_id=? AND account_id=?", (brief_id, account_id)).fetchone()
        account_count = conn.execute("SELECT COUNT(*) FROM web_content_variants WHERE account_id=?", (account_id,)).fetchone()
        if int(count[0] or 0) >= MAX_VARIANTS_PER_BRIEF or int(account_count[0] or 0) >= MAX_VARIANTS_PER_ACCOUNT:
            return envelope(False, "Đã đạt giới hạn content piece của brief hoặc Web account.", status_name="guarded", error_code="WEB_CONTENT_VARIANT_LIMIT")
        snapshot = _variant_snapshot_from_row(source, state="active")
        snapshot["title"] = payload.title or f"{snapshot['title']} (bản sao)"
        marker = _marker(snapshot["title"], snapshot["content_text"], snapshot["note"])
        guard = _policy_guard(marker)
        if guard:
            return guard
        if not _has_storage_capacity(conn, account_id=account_id, additional_bytes=_variant_version_capacity_additional(snapshot)):
            return _storage_limit()
        ordinal = conn.execute(
            "SELECT COALESCE(MAX(ordinal), 0) FROM web_content_variants WHERE brief_id=? AND account_id=?",
            (brief_id, account_id),
        ).fetchone()
        new_id = str(uuid.uuid4())
        now = utc_now()
        _insert_variant(conn, variant_id=new_id, brief_id=brief_id, account_id=account_id, ordinal=int(ordinal[0] or 0) + 1, snapshot=snapshot, revision=1, now=now)
        _insert_variant_version(conn, variant_id=new_id, account_id=account_id, revision=1, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, brief_id=brief_id, variant_id=new_id, action="variant_duplicated", revision=1)
        _audit(conn, request=request, account=account, action="web.content.variant.duplicate", target=new_id, detail=f"source={variant_id};brief={brief_id}")
        duplicated = _variant_row(conn, brief_id=brief_id, variant_id=new_id, account_id=account_id)
        return envelope(True, "Đã nhân bản content piece.", data={"brief": _brief_public(brief), "variant": _variant_public(duplicated, include_content=True), "execution": "authoring_only"}, status_name="draft")

    return _idempotent(f"web-content-studio:{account_id}:brief:{brief_id}:variant:{variant_id}:duplicate", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/briefs/{brief_id}/variants/{variant_id}/restore-version")
async def restore_variant_version(
    brief_id: str,
    variant_id: str,
    payload: VariantRestoreVersionRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    _require_enabled()
    brief_id = _uuid(brief_id, label="Content brief ID")
    variant_id = _uuid(variant_id, label="Content piece ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"brief_id": brief_id, "variant_id": variant_id, "revision": payload.expected_revision, "target_revision": payload.target_revision})

    def operation(conn: Any) -> dict[str, Any]:
        brief = _brief_row(conn, brief_id=brief_id, account_id=account_id)
        if not brief:
            return _brief_not_found()
        current = _variant_row(conn, brief_id=brief_id, variant_id=variant_id, account_id=account_id)
        if not current:
            return _variant_not_found()
        if int(current[11]) != payload.expected_revision:
            return _revision_conflict()
        if str(current[10]) != "active":
            return _variant_state_conflict()
        version = conn.execute(
            """SELECT snapshot_json FROM web_content_variant_versions
               WHERE variant_id=? AND account_id=? AND revision=?""",
            (variant_id, account_id, payload.target_revision),
        ).fetchone()
        if not version:
            return envelope(False, "Không tìm thấy phiên bản content piece cần khôi phục.", status_name="guarded", error_code="WEB_CONTENT_VERSION_NOT_FOUND")
        try:
            stored = json.loads(str(version[0] or "{}"))
            recovered = _variant_payload_from_snapshot(stored if isinstance(stored, dict) else {})
        except (TypeError, ValueError, json.JSONDecodeError):
            return envelope(False, "Phiên bản content piece không còn hợp lệ để khôi phục.", status_name="guarded", error_code="WEB_CONTENT_VERSION_INVALID")
        guard = _policy_guard(_variant_marker(recovered))
        if guard:
            return guard
        if not _can_add_variant_version(conn, variant_id=variant_id, account_id=account_id):
            return _version_limit("Content piece")
        source_kind = str(stored.get("source_kind") or "manual") if isinstance(stored, dict) else "manual"
        source_kind = source_kind if source_kind in SOURCE_KINDS else "manual"
        source_brief_revision = int(stored.get("source_brief_revision") or int(brief[21])) if isinstance(stored, dict) else int(brief[21])
        snapshot = _variant_snapshot_from_payload(recovered, source_kind=source_kind, source_brief_revision=max(1, source_brief_revision))
        if not _has_storage_capacity(conn, account_id=account_id, additional_bytes=_serialized_bytes(snapshot)):
            return _storage_limit()
        revision = int(current[11]) + 1
        now = utc_now()
        _write_variant(conn, variant_id=variant_id, brief_id=brief_id, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_variant_version(conn, variant_id=variant_id, account_id=account_id, revision=revision, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, brief_id=brief_id, variant_id=variant_id, action="variant_version_restored", revision=revision)
        _audit(conn, request=request, account=account, action="web.content.variant.restore_version", target=variant_id, detail=f"brief={brief_id};from_revision={payload.target_revision};revision={revision}")
        updated = _variant_row(conn, brief_id=brief_id, variant_id=variant_id, account_id=account_id)
        return envelope(True, "Đã khôi phục phiên bản content piece.", data={"brief": _brief_public(brief), "variant": _variant_public(updated, include_content=True), "execution": "authoring_only"}, status_name="draft")

    return _idempotent(f"web-content-studio:{account_id}:brief:{brief_id}:variant:{variant_id}:restore-version", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/briefs/{brief_id}/select-variant")
async def select_variant(brief_id: str, payload: SelectVariantRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    brief_id = _uuid(brief_id, label="Content brief ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"brief_id": brief_id, "revision": payload.expected_revision, "variant_id": payload.variant_id})

    def operation(conn: Any) -> dict[str, Any]:
        current = _brief_row(conn, brief_id=brief_id, account_id=account_id)
        if not current:
            return _brief_not_found()
        if int(current[21]) != payload.expected_revision:
            return _revision_conflict()
        if str(current[19]) != "active":
            return _brief_state_conflict()
        variant = _variant_row(conn, brief_id=brief_id, variant_id=payload.variant_id, account_id=account_id)
        if not variant or str(variant[10]) != "active":
            return _variant_not_found()
        reference_snapshot = _reference_snapshot(conn, account_id=account_id, references=_references_from_row(current))
        snapshot = _snapshot_from_row(current, references=reference_snapshot, selected_variant_id=payload.variant_id)
        revision = int(current[21]) + 1
        now = utc_now()
        _write_brief(conn, brief_id=brief_id, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        snapshot_recorded = _can_add_brief_version(conn, brief_id=brief_id, account_id=account_id)
        if snapshot_recorded:
            _insert_brief_version(conn, brief_id=brief_id, account_id=account_id, revision=revision, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, brief_id=brief_id, variant_id=payload.variant_id, action="variant_selected" if snapshot_recorded else "variant_selected_without_snapshot", revision=revision)
        _audit(conn, request=request, account=account, action="web.content.brief.select_variant", target=brief_id, detail=f"variant={payload.variant_id};revision={revision};snapshot={'yes' if snapshot_recorded else 'no'}")
        updated = _brief_row(conn, brief_id=brief_id, account_id=account_id)
        return envelope(
            True,
            "Đã chọn content piece cho brief.",
            data={
                "brief": _brief_public(updated, include_content=True),
                "variant": _variant_public(variant),
                "history_snapshot_recorded": snapshot_recorded,
                "execution": "authoring_only",
            },
            status_name="draft",
        )

    return _idempotent(f"web-content-studio:{account_id}:brief:{brief_id}:select-variant", account_id, payload.idempotency_key, fingerprint, operation)


@router.get("/events")
async def content_studio_events(limit: int = 40, account: dict = Depends(require_account)):
    _require_enabled()
    bounded = max(1, min(int(limit), MAX_EVENT_LIMIT))
    with read_transaction() as conn:
        rows = conn.execute(
            """SELECT brief_id, variant_id, entity_type, action, revision, created_at
               FROM web_content_studio_events WHERE account_id=?
               ORDER BY created_at DESC, id DESC LIMIT ?""",
            (str(account["id"]), bounded),
        ).fetchall()
    return envelope(
        True,
        "Đã tải hoạt động Content Studio riêng tư.",
        data={
            "items": [
                {
                    "brief_id": str(row[0]),
                    "variant_id": str(row[1]) if row[1] else None,
                    "entity_type": str(row[2]),
                    "action": str(row[3]),
                    "revision": int(row[4]),
                    "created_at": str(row[5]),
                }
                for row in rows
            ]
        },
        status_name="read_only",
    )
