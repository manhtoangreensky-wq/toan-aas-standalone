"""Private, Web-native Voice Studio & Consent Vault.

This module deliberately keeps the standalone Web App independent from the
frozen Telegram Bot.  It stores only account-scoped *authoring metadata*:
voice-direction profiles, consent attestations, scripts, cue sheets and
revision history.  It never stores raw audio, provider voice IDs, Telegram
file IDs, preview URLs, jobs, Xu, payments, PayOS data or provider payloads.

The deterministic cue sheet is a writing aid, not a TTS/clone/transcribe
result.  A future provider adapter must have its own authenticated, reviewed
contract before it can use any Web-owned record for audio processing.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import math
import re
import uuid
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction, utc_now, voice_studio_enabled


router = APIRouter(prefix="/api/v1/voice-studio", tags=["Web Voice Studio & Consent Vault"])

VAULT_STATES = frozenset({"active", "archived"})
VAULT_KINDS = frozenset({"delivery_style", "brand_narration", "consented_reference"})
CONSENT_STATUSES = frozenset({"not_required", "self_attested", "revoked"})
SCRIPT_STATES = frozenset({"active", "archived"})
SCRIPT_KINDS = frozenset({"narration", "ad", "explainer", "podcast", "training", "custom"})
SOURCE_KINDS = frozenset({"manual", "local_deterministic_draft_only"})
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
UNSAFE_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# The Web-owned vault is an authoring boundary, not a way to request an
# imitation or clone of a person.  This compact marker intentionally errs on
# the side of asking the author to rewrite the direction.  It does not attempt
# to decide copyright, publicity or consent questions automatically.
VOICE_IMITATION_MARKERS = (
    "clone giọng", "nhái giọng", "bắt chước giọng", "giống giọng", "giống ca sĩ",
    "giống nghệ sĩ", "giọng của ", "voice clone", "clone voice", "imitate voice",
    "impersonate", "sound like", "sounds like", "in the voice of", "voice of ",
    "celebrity voice", "artist voice", "same voice",
)

SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|token|"
    r"client[ _-]?secret|aws[ _-]?secret[ _-]?access[ _-]?key|secret(?:[ _-]?(?:key|access[ _-]?)?)?|"
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

MAX_VAULTS_PER_STATE = 300
MAX_SCRIPTS_PER_VAULT = 250
MAX_SCRIPTS_PER_ACCOUNT = 3_000
MAX_VERSIONS_PER_ENTITY = 100
MAX_LIST_LIMIT = 100
MAX_EVENT_LIMIT = 50
MAX_TOTAL_STORAGE_BYTES = 24 * 1024 * 1024
MAX_TITLE = 180
MAX_LANGUAGE = 100
MAX_STYLE = 1_600
MAX_USE_CONTEXT = 1_600
MAX_CONSENT_NOTE = 1_400
MAX_SCRIPT_AUDIENCE = 500
MAX_SCRIPT_TEXT = 24_000
MAX_DELIVERY_NOTES = 5_000
MAX_PRONUNCIATION_NOTES = 3_000
MAX_TAGS = 20
MAX_TAG_LENGTH = 48
MIN_PACE_WPM = 80
MAX_PACE_WPM = 240
MAX_CUE_ITEMS = 200
IDEMPOTENCY_RETENTION = timedelta(hours=24)
MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT = 1_024


def _require_enabled() -> None:
    if not voice_studio_enabled():
        raise HTTPException(
            status_code=503,
            detail="Voice Studio đang tạm dừng để bảo trì. WEBAPP_VOICE_STUDIO_ENABLED chưa được bật.",
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
        marker = tag.casefold()
        if marker not in seen:
            seen.add(marker)
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


def _marker(*parts: str) -> str:
    normalized = re.sub(r"\s+", " ", "\n".join(str(part or "") for part in parts)).strip().lower()[:30_000]
    for marker in VOICE_IMITATION_MARKERS:
        if marker in normalized:
            return marker
    return ""


def _fingerprint(payload: dict[str, Any]) -> str:
    material = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _idempotency_cutoff() -> str:
    return (datetime.now(timezone.utc) - IDEMPOTENCY_RETENTION).isoformat(timespec="seconds")


class VaultPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str
    vault_kind: str = "delivery_style"
    language: str = "vi"
    style_notes: str = ""
    use_context: str = ""
    consent_status: str = "not_required"
    consent_note: str = ""
    is_default: bool = False
    tags: list[str] = Field(default_factory=list)
    project_id: str | None = None
    content_brief_id: str | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _single_line(value, label="Tên voice direction", minimum=2, maximum=MAX_TITLE)

    @field_validator("vault_kind")
    @classmethod
    def validate_kind(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in VAULT_KINDS:
            raise ValueError("Loại voice direction không hợp lệ")
        return normalized

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        return _single_line(value, label="Ngôn ngữ", minimum=1, maximum=MAX_LANGUAGE)

    @field_validator("style_notes")
    @classmethod
    def validate_style_notes(cls, value: str) -> str:
        return _content(value, label="Mô tả cách thể hiện", maximum=MAX_STYLE, allow_empty=True)

    @field_validator("use_context")
    @classmethod
    def validate_use_context(cls, value: str) -> str:
        return _content(value, label="Ngữ cảnh sử dụng", maximum=MAX_USE_CONTEXT, allow_empty=True)

    @field_validator("consent_status")
    @classmethod
    def validate_consent_status(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in CONSENT_STATUSES:
            raise ValueError("Trạng thái consent không hợp lệ")
        return normalized

    @field_validator("consent_note")
    @classmethod
    def validate_consent_note(cls, value: str) -> str:
        return _content(value, label="Ghi chú consent", maximum=MAX_CONSENT_NOTE, allow_empty=True)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        return _tags(value)

    @field_validator("project_id", "content_brief_id", mode="before")
    @classmethod
    def validate_reference_ids(cls, value: Any, info) -> str | None:
        label = "Project ID" if info.field_name == "project_id" else "Content Brief ID"
        return _optional_uuid(value, label=label)

    @model_validator(mode="after")
    def validate_consent_boundary(self):
        marker = _marker(self.title, self.style_notes, self.use_context, self.consent_note)
        if marker:
            raise ValueError("Voice direction không nhận yêu cầu mô phỏng, nhái hoặc clone giọng của một người cụ thể")
        if self.vault_kind == "consented_reference":
            if self.consent_status not in {"self_attested", "revoked"} or len(self.consent_note) < 12:
                raise ValueError("Reference cần self-attested consent hoặc trạng thái đã thu hồi, cùng ghi chú tối thiểu 12 ký tự")
            if self.consent_status == "revoked" and self.is_default:
                raise ValueError("Reference đã thu hồi consent không thể đặt làm direction mặc định local")
        elif self.consent_status != "not_required":
            raise ValueError("Chỉ consented reference mới được gắn trạng thái consent")
        return self


class VaultCreateRequest(VaultPayload):
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)


class VaultUpdateRequest(VaultPayload):
    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)


class RevisionMutationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)


class RestoreVersionRequest(RevisionMutationRequest):
    target_revision: int = Field(ge=1)


class ScriptPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str
    script_kind: str = "narration"
    language: str = "vi"
    audience: str = ""
    pace_wpm: int = Field(default=145, ge=MIN_PACE_WPM, le=MAX_PACE_WPM)
    script_text: str
    delivery_notes: str = ""
    pronunciation_notes: str = ""
    tags: list[str] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _single_line(value, label="Tên script", minimum=2, maximum=MAX_TITLE)

    @field_validator("script_kind")
    @classmethod
    def validate_kind(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in SCRIPT_KINDS:
            raise ValueError("Loại script không hợp lệ")
        return normalized

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        return _single_line(value, label="Ngôn ngữ", minimum=1, maximum=MAX_LANGUAGE)

    @field_validator("audience")
    @classmethod
    def validate_audience(cls, value: str) -> str:
        return _single_line(value, label="Đối tượng", minimum=0, maximum=MAX_SCRIPT_AUDIENCE, allow_empty=True)

    @field_validator("script_text")
    @classmethod
    def validate_script_text(cls, value: str) -> str:
        return _content(value, label="Lời thoại", maximum=MAX_SCRIPT_TEXT)

    @field_validator("delivery_notes")
    @classmethod
    def validate_delivery_notes(cls, value: str) -> str:
        return _content(value, label="Chỉ dẫn thể hiện", maximum=MAX_DELIVERY_NOTES, allow_empty=True)

    @field_validator("pronunciation_notes")
    @classmethod
    def validate_pronunciation_notes(cls, value: str) -> str:
        return _content(value, label="Ghi chú phát âm", maximum=MAX_PRONUNCIATION_NOTES, allow_empty=True)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        return _tags(value)

    @model_validator(mode="after")
    def validate_original_voice_direction(self):
        marker = _marker(self.title, self.script_text, self.delivery_notes, self.pronunciation_notes)
        if marker:
            raise ValueError("Script không nhận chỉ dẫn mô phỏng, nhái hoặc clone giọng của một người cụ thể")
        return self


class ScriptCreateRequest(ScriptPayload):
    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)


class ScriptUpdateRequest(ScriptPayload):
    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)


def _safe_receipt(response: dict[str, Any]) -> dict[str, Any]:
    """Keep 24-hour idempotency receipts free of scripts, notes and tags."""

    if not isinstance(response, dict) or response.get("ok") is not True:
        return response
    source = response.get("data") if isinstance(response.get("data"), dict) else {}
    data: dict[str, Any] = {}
    vault = source.get("vault")
    if isinstance(vault, dict) and isinstance(vault.get("id"), str):
        data["vault"] = {
            "id": vault["id"], "revision": int(vault.get("revision") or 0),
            "state": str(vault.get("state") or ""), "is_default": bool(vault.get("is_default")),
        }
    script = source.get("script")
    if isinstance(script, dict) and isinstance(script.get("id"), str):
        data["script"] = {
            "id": script["id"], "vault_id": str(script.get("vault_id") or ""),
            "revision": int(script.get("revision") or 0), "state": str(script.get("state") or ""),
            "source_kind": str(script.get("source_kind") or ""),
        }
    ids = source.get("script_ids")
    if isinstance(ids, list):
        data["script_ids"] = [str(item) for item in ids if isinstance(item, str)][:3]
    for name in ("execution", "provider_called", "audio_created", "history_snapshot_recorded", "script_count"):
        if name in source:
            data[name] = source[name]
    return envelope(
        True,
        str(response.get("message") or "Đã lưu Voice Studio."),
        data=data,
        status_name=str(response.get("status") or "draft"),
    )


def _idempotent(
    scope: str,
    account_id: str,
    key: str,
    request_fingerprint: str,
    operation: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute("DELETE FROM web_idempotency WHERE scope LIKE ? AND created_at < ?", ("web-voice-studio:%", _idempotency_cutoff()))
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
                raise HTTPException(status_code=409, detail="Receipt Voice Studio không hợp lệ") from exc
            if not isinstance(replay, dict):
                raise HTTPException(status_code=409, detail="Receipt Voice Studio không hợp lệ")
            return replay
        count = conn.execute("SELECT COUNT(*) FROM web_idempotency WHERE scope LIKE ?", (f"web-voice-studio:{account_id}:%",)).fetchone()
        if int(count[0] or 0) >= MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT:
            return envelope(False, "Kho receipt thao tác tạm thời đang đầy. Vui lòng thử lại sau.", status_name="guarded", error_code="WEB_VOICE_IDEMPOTENCY_LIMIT")
        response = operation(conn)
        if response.get("ok") is True:
            receipt = _safe_receipt(response)
            conn.execute(
                "INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at) VALUES (?, ?, ?, ?, ?)",
                (scope, key, json.dumps(receipt, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
            )
            return receipt
    return response


def _vault_row(conn: Any, *, vault_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, project_id, content_brief_id, title, vault_kind, language, style_notes, use_context,
                  consent_status, consent_note, tags_json, policy_marker, state, is_default, revision,
                  created_at, updated_at, archived_at
           FROM web_voice_vaults WHERE id=? AND account_id=?""",
        (vault_id, account_id),
    ).fetchone()


def _script_row(conn: Any, *, vault_id: str, script_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, vault_id, title, script_kind, language, audience, pace_wpm, script_text,
                  delivery_notes, pronunciation_notes, tags_json, policy_marker, source_kind, state,
                  revision, created_at, updated_at, archived_at
           FROM web_voice_scripts WHERE id=? AND vault_id=? AND account_id=?""",
        (script_id, vault_id, account_id),
    ).fetchone()


def _vault_not_found() -> dict[str, Any]:
    return envelope(False, "Không tìm thấy Voice Vault thuộc Web account hiện tại.", status_name="guarded", error_code="WEB_VOICE_VAULT_NOT_FOUND")


def _script_not_found() -> dict[str, Any]:
    return envelope(False, "Không tìm thấy script thuộc Voice Vault hiện tại.", status_name="guarded", error_code="WEB_VOICE_SCRIPT_NOT_FOUND")


def _revision_conflict() -> dict[str, Any]:
    return envelope(False, "Dữ liệu đã thay đổi ở nơi khác. Hãy tải lại trước khi lưu tiếp.", status_name="guarded", error_code="WEB_VOICE_REVISION_CONFLICT")


def _vault_archived() -> dict[str, Any]:
    return envelope(False, "Voice Vault đã archive và không thể chỉnh sửa trước khi khôi phục.", status_name="guarded", error_code="WEB_VOICE_VAULT_ARCHIVED")


def _script_archived() -> dict[str, Any]:
    return envelope(False, "Script đã archive và không thể chỉnh sửa trước khi khôi phục.", status_name="guarded", error_code="WEB_VOICE_SCRIPT_ARCHIVED")


def _vault_consent_revoked(row: tuple[Any, ...]) -> bool:
    return str(row[4]) == "consented_reference" and str(row[8]) == "revoked"


def _authoring_blocked_by_revoked_consent() -> dict[str, Any]:
    return envelope(
        False,
        "Consent của reference đã được thu hồi. Chỉ có thể xem, archive hoặc cập nhật direction với self-attestation mới trước khi soạn script.",
        status_name="guarded",
        error_code="WEB_VOICE_CONSENT_REVOKED",
    )


def _excerpt(value: Any, *, limit: int = 280) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= limit else f"{text[: max(1, limit - 1)].rstrip()}…"


def _words(value: str) -> list[str]:
    return re.findall(r"\S+", str(value or ""), flags=re.UNICODE)


def _sentences(value: str) -> list[str]:
    parts = re.split(r"(?<=[.!?…])\s+|\n{2,}", str(value or "").strip())
    values = [re.sub(r"\s+", " ", item).strip() for item in parts if re.sub(r"\s+", " ", item).strip()]
    return values[:MAX_CUE_ITEMS]


def _metrics(script_text: str, pace_wpm: int) -> dict[str, int]:
    words = _words(script_text)
    sentences = _sentences(script_text)
    pace = max(MIN_PACE_WPM, min(MAX_PACE_WPM, int(pace_wpm or 145)))
    return {
        "characters": len(script_text),
        "words": len(words),
        "paragraphs": len([item for item in re.split(r"\n\s*\n", script_text) if item.strip()]),
        "sentences": len(sentences),
        "pace_wpm": pace,
        "estimated_seconds": int(math.ceil((len(words) / pace) * 60)) if words else 0,
    }


def _cue_sheet(script_text: str, pace_wpm: int) -> list[dict[str, Any]]:
    pace = max(MIN_PACE_WPM, min(MAX_PACE_WPM, int(pace_wpm or 145)))
    cursor = 0.0
    entries: list[dict[str, Any]] = []
    for index, sentence in enumerate(_sentences(script_text), start=1):
        word_count = max(1, len(_words(sentence)))
        seconds = max(0.7, (word_count / pace) * 60)
        start = round(cursor, 2)
        end = round(cursor + seconds, 2)
        entries.append({"index": index, "start_seconds": start, "end_seconds": end, "text": sentence, "word_count": word_count})
        cursor = end
    return entries


def _vault_reference_ids(row: tuple[Any, ...]) -> dict[str, str | None]:
    return {"project_id": str(row[1]) if row[1] else None, "content_brief_id": str(row[2]) if row[2] else None}


def _reference_snapshot(conn: Any, *, account_id: str, references: dict[str, str | None], require_active: bool = True) -> dict[str, Any]:
    result: dict[str, Any] = {}
    project_id = references.get("project_id")
    if project_id:
        state_clause = "AND state='active'" if require_active else ""
        row = conn.execute(
            f"SELECT id, title, state FROM web_projects WHERE id=? AND account_id=? {state_clause}",
            (project_id, account_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=422, detail="Project liên kết không hợp lệ hoặc không còn hoạt động")
        result["project"] = {"id": str(row[0]), "title": str(row[1]), "state": str(row[2])}
    brief_id = references.get("content_brief_id")
    if brief_id:
        state_clause = "AND state='active'" if require_active else ""
        row = conn.execute(
            f"SELECT id, title, content_kind, state FROM web_content_briefs WHERE id=? AND account_id=? {state_clause}",
            (brief_id, account_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=422, detail="Content Brief liên kết không hợp lệ hoặc không còn hoạt động")
        result["content_brief"] = {"id": str(row[0]), "title": str(row[1]), "content_kind": str(row[2]), "state": str(row[3])}
    return result


def _vault_snapshot(payload: VaultPayload, *, references: dict[str, Any], state: str = "active") -> dict[str, Any]:
    return {
        "title": payload.title,
        "vault_kind": payload.vault_kind,
        "language": payload.language,
        "style_notes": payload.style_notes,
        "use_context": payload.use_context,
        "consent_status": payload.consent_status,
        "consent_note": payload.consent_note,
        "is_default": bool(payload.is_default),
        "tags": list(payload.tags),
        "reference_ids": {"project_id": payload.project_id, "content_brief_id": payload.content_brief_id},
        "references": references,
        "policy_marker": _marker(payload.title, payload.style_notes, payload.use_context, payload.consent_note),
        "state": state,
    }


def _script_snapshot(payload: ScriptPayload, *, state: str = "active", source_kind: str = "manual") -> dict[str, Any]:
    return {
        "title": payload.title,
        "script_kind": payload.script_kind,
        "language": payload.language,
        "audience": payload.audience,
        "pace_wpm": payload.pace_wpm,
        "script_text": payload.script_text,
        "delivery_notes": payload.delivery_notes,
        "pronunciation_notes": payload.pronunciation_notes,
        "tags": list(payload.tags),
        "policy_marker": _marker(payload.title, payload.script_text, payload.delivery_notes, payload.pronunciation_notes),
        "source_kind": source_kind,
        "state": state,
    }


def _vault_snapshot_from_row(row: tuple[Any, ...], *, references: dict[str, Any], state: str | None = None, is_default: bool | None = None) -> dict[str, Any]:
    return {
        "title": str(row[3]), "vault_kind": str(row[4]), "language": str(row[5]),
        "style_notes": str(row[6]), "use_context": str(row[7]), "consent_status": str(row[8]),
        "consent_note": str(row[9]), "is_default": bool(row[13]) if is_default is None else bool(is_default),
        "tags": _decode_tags(row[10]), "reference_ids": _vault_reference_ids(row), "references": references,
        "policy_marker": str(row[11] or ""), "state": state or str(row[12]),
    }


def _script_snapshot_from_row(row: tuple[Any, ...], *, state: str | None = None) -> dict[str, Any]:
    return {
        "title": str(row[2]), "script_kind": str(row[3]), "language": str(row[4]), "audience": str(row[5]),
        "pace_wpm": int(row[6]), "script_text": str(row[7]), "delivery_notes": str(row[8]),
        "pronunciation_notes": str(row[9]), "tags": _decode_tags(row[10]), "policy_marker": str(row[11] or ""),
        "source_kind": str(row[12]), "state": state or str(row[13]),
    }


def _vault_payload_from_snapshot(snapshot: dict[str, Any]) -> VaultPayload:
    reference_ids = snapshot.get("reference_ids") if isinstance(snapshot.get("reference_ids"), dict) else {}
    return VaultPayload.model_validate({
        "title": snapshot.get("title", ""), "vault_kind": snapshot.get("vault_kind", ""),
        "language": snapshot.get("language", "vi"), "style_notes": snapshot.get("style_notes", ""),
        "use_context": snapshot.get("use_context", ""), "consent_status": snapshot.get("consent_status", "not_required"),
        "consent_note": snapshot.get("consent_note", ""), "is_default": bool(snapshot.get("is_default")),
        "tags": snapshot.get("tags", []), "project_id": reference_ids.get("project_id"),
        "content_brief_id": reference_ids.get("content_brief_id"),
    })


def _script_payload_from_snapshot(snapshot: dict[str, Any]) -> ScriptPayload:
    return ScriptPayload.model_validate({
        "title": snapshot.get("title", ""), "script_kind": snapshot.get("script_kind", "narration"),
        "language": snapshot.get("language", "vi"), "audience": snapshot.get("audience", ""),
        "pace_wpm": snapshot.get("pace_wpm", 145), "script_text": snapshot.get("script_text", ""),
        "delivery_notes": snapshot.get("delivery_notes", ""), "pronunciation_notes": snapshot.get("pronunciation_notes", ""),
        "tags": snapshot.get("tags", []),
    })


def _vault_public(row: tuple[Any, ...], *, include_content: bool = False) -> dict[str, Any]:
    marker = str(row[11] or "")
    consent_revoked = _vault_consent_revoked(row)
    value = {
        "id": str(row[0]), "project_id": str(row[1]) if row[1] else None,
        "content_brief_id": str(row[2]) if row[2] else None, "title": str(row[3]),
        "vault_kind": str(row[4]), "language": str(row[5]), "style_excerpt": _excerpt(row[6], limit=220),
        "use_context_excerpt": _excerpt(row[7], limit=180), "consent_status": str(row[8]),
        "has_consent_note": bool(str(row[9] or "")), "tags": _decode_tags(row[10]),
        "policy": {"status": "guarded" if marker or consent_revoked else "clear", "marker": marker or ("consent_revoked" if consent_revoked else None)},
        "authoring_status": "guarded" if consent_revoked else "ready",
        "state": str(row[12]), "is_default": bool(row[13]), "revision": int(row[14]),
        "created_at": str(row[15]), "updated_at": str(row[16]), "archived_at": str(row[17]) if row[17] else None,
        "execution": "metadata_only", "provider_status": "not_connected", "preview_available": False,
    }
    if include_content:
        value.update({"style_notes": str(row[6]), "use_context": str(row[7]), "consent_note": str(row[9])})
    return value


def _script_public(row: tuple[Any, ...], *, include_content: bool = False) -> dict[str, Any]:
    marker = str(row[11] or "")
    value = {
        "id": str(row[0]), "vault_id": str(row[1]), "title": str(row[2]), "script_kind": str(row[3]),
        "language": str(row[4]), "audience_excerpt": _excerpt(row[5], limit=160), "pace_wpm": int(row[6]),
        "script_excerpt": _excerpt(row[7], limit=360), "delivery_notes_excerpt": _excerpt(row[8], limit=180),
        "has_pronunciation_notes": bool(str(row[9] or "")), "tags": _decode_tags(row[10]),
        "policy": {"status": "guarded" if marker else "clear", "marker": marker or None},
        "source_kind": str(row[12]), "state": str(row[13]), "revision": int(row[14]),
        "created_at": str(row[15]), "updated_at": str(row[16]), "archived_at": str(row[17]) if row[17] else None,
        "metrics": _metrics(str(row[7]), int(row[6])), "execution": "authoring_only",
        "provider_called": False, "audio_created": False,
    }
    if include_content:
        value.update({"audience": str(row[5]), "script_text": str(row[7]), "delivery_notes": str(row[8]), "pronunciation_notes": str(row[9])})
    return value


def _vault_version_public(row: tuple[Any, ...]) -> dict[str, Any]:
    try:
        snapshot = json.loads(str(row[1] or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        snapshot = {}
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    return {
        "revision": int(row[0]), "title": str(snapshot.get("title") or "Voice direction"),
        "vault_kind": str(snapshot.get("vault_kind") or "delivery_style"), "state": str(snapshot.get("state") or "active"),
        "is_default": bool(snapshot.get("is_default")), "style_excerpt": _excerpt(snapshot.get("style_notes"), limit=220),
        "created_at": str(row[2]),
    }


def _script_version_public(row: tuple[Any, ...]) -> dict[str, Any]:
    try:
        snapshot = json.loads(str(row[1] or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        snapshot = {}
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    text = str(snapshot.get("script_text") or "")
    return {
        "revision": int(row[0]), "title": str(snapshot.get("title") or "Voice script"),
        "script_kind": str(snapshot.get("script_kind") or "narration"), "state": str(snapshot.get("state") or "active"),
        "script_excerpt": _excerpt(text, limit=300), "metrics": _metrics(text, int(snapshot.get("pace_wpm") or 145)),
        "created_at": str(row[2]),
    }


def _insert_vault(conn: Any, *, vault_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str) -> None:
    refs = snapshot["reference_ids"]
    conn.execute(
        """INSERT INTO web_voice_vaults
           (id, account_id, project_id, content_brief_id, title, vault_kind, language, style_notes, use_context,
            consent_status, consent_note, tags_json, policy_marker, state, is_default, revision, created_at, updated_at, archived_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (vault_id, account_id, refs.get("project_id"), refs.get("content_brief_id"), snapshot["title"], snapshot["vault_kind"],
         snapshot["language"], snapshot["style_notes"], snapshot["use_context"], snapshot["consent_status"], snapshot["consent_note"],
         json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")), snapshot["policy_marker"], snapshot["state"],
         1 if snapshot.get("is_default") else 0, revision, now, now, now if snapshot["state"] == "archived" else None),
    )


def _write_vault(conn: Any, *, vault_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str, archived_at: str | None) -> None:
    refs = snapshot["reference_ids"]
    conn.execute(
        """UPDATE web_voice_vaults
           SET project_id=?, content_brief_id=?, title=?, vault_kind=?, language=?, style_notes=?, use_context=?,
               consent_status=?, consent_note=?, tags_json=?, policy_marker=?, state=?, is_default=?, revision=?, updated_at=?, archived_at=?
           WHERE id=? AND account_id=?""",
        (refs.get("project_id"), refs.get("content_brief_id"), snapshot["title"], snapshot["vault_kind"], snapshot["language"],
         snapshot["style_notes"], snapshot["use_context"], snapshot["consent_status"], snapshot["consent_note"],
         json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")), snapshot["policy_marker"], snapshot["state"],
         1 if snapshot.get("is_default") else 0, revision, now, archived_at, vault_id, account_id),
    )


def _insert_vault_version(conn: Any, *, vault_id: str, account_id: str, revision: int, snapshot: dict[str, Any], created_at: str) -> None:
    conn.execute(
        "INSERT INTO web_voice_vault_versions (id, vault_id, account_id, revision, snapshot_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), vault_id, account_id, revision, json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), created_at),
    )


def _insert_script(conn: Any, *, script_id: str, vault_id: str, account_id: str, ordinal: int, snapshot: dict[str, Any], revision: int, now: str) -> None:
    conn.execute(
        """INSERT INTO web_voice_scripts
           (id, vault_id, account_id, ordinal, title, script_kind, language, audience, pace_wpm, script_text,
            delivery_notes, pronunciation_notes, tags_json, policy_marker, source_kind, state, revision, created_at, updated_at, archived_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (script_id, vault_id, account_id, ordinal, snapshot["title"], snapshot["script_kind"], snapshot["language"], snapshot["audience"],
         snapshot["pace_wpm"], snapshot["script_text"], snapshot["delivery_notes"], snapshot["pronunciation_notes"],
         json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")), snapshot["policy_marker"], snapshot["source_kind"],
         snapshot["state"], revision, now, now, now if snapshot["state"] == "archived" else None),
    )


def _write_script(conn: Any, *, script_id: str, vault_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str, archived_at: str | None) -> None:
    conn.execute(
        """UPDATE web_voice_scripts
           SET title=?, script_kind=?, language=?, audience=?, pace_wpm=?, script_text=?, delivery_notes=?, pronunciation_notes=?,
               tags_json=?, policy_marker=?, source_kind=?, state=?, revision=?, updated_at=?, archived_at=?
           WHERE id=? AND vault_id=? AND account_id=?""",
        (snapshot["title"], snapshot["script_kind"], snapshot["language"], snapshot["audience"], snapshot["pace_wpm"],
         snapshot["script_text"], snapshot["delivery_notes"], snapshot["pronunciation_notes"],
         json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")), snapshot["policy_marker"], snapshot["source_kind"],
         snapshot["state"], revision, now, archived_at, script_id, vault_id, account_id),
    )


def _insert_script_version(conn: Any, *, script_id: str, account_id: str, revision: int, snapshot: dict[str, Any], created_at: str) -> None:
    conn.execute(
        "INSERT INTO web_voice_script_versions (id, script_id, account_id, revision, snapshot_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), script_id, account_id, revision, json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), created_at),
    )


def _can_add_version(conn: Any, *, table: str, entity_column: str, entity_id: str, account_id: str) -> bool:
    row = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {entity_column}=? AND account_id=?", (entity_id, account_id)).fetchone()
    return int(row[0] or 0) < MAX_VERSIONS_PER_ENTITY


def _event(conn: Any, *, account_id: str, vault_id: str, action: str, revision: int, script_id: str | None = None) -> None:
    conn.execute(
        """INSERT INTO web_voice_studio_events
           (id, account_id, vault_id, script_id, entity_type, action, revision, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), account_id, vault_id, script_id, "script" if script_id else "vault", action, revision, utc_now()),
    )


def _audit(conn: Any, *, request: Request, account: dict, action: str, target: str, detail: str) -> None:
    _record_audit(
        conn,
        account_id=str(account["id"]), canonical_user_id=None, action=action, request_id=_request_id(request),
        target=target, detail=detail[:320],
    )


def _account_storage_bytes(conn: Any, *, account_id: str) -> int:
    queries = (
        """SELECT COALESCE(SUM(COALESCE(LENGTH(CAST(title AS BLOB)),0)+COALESCE(LENGTH(CAST(style_notes AS BLOB)),0)+
               COALESCE(LENGTH(CAST(use_context AS BLOB)),0)+COALESCE(LENGTH(CAST(consent_note AS BLOB)),0)+COALESCE(LENGTH(CAST(tags_json AS BLOB)),0)),0)
               FROM web_voice_vaults WHERE account_id=?""",
        """SELECT COALESCE(SUM(COALESCE(LENGTH(CAST(title AS BLOB)),0)+COALESCE(LENGTH(CAST(audience AS BLOB)),0)+
               COALESCE(LENGTH(CAST(script_text AS BLOB)),0)+COALESCE(LENGTH(CAST(delivery_notes AS BLOB)),0)+
               COALESCE(LENGTH(CAST(pronunciation_notes AS BLOB)),0)+COALESCE(LENGTH(CAST(tags_json AS BLOB)),0)),0)
               FROM web_voice_scripts WHERE account_id=?""",
        "SELECT COALESCE(SUM(COALESCE(LENGTH(CAST(snapshot_json AS BLOB)),0)),0) FROM web_voice_vault_versions WHERE account_id=?",
        "SELECT COALESCE(SUM(COALESCE(LENGTH(CAST(snapshot_json AS BLOB)),0)),0) FROM web_voice_script_versions WHERE account_id=?",
    )
    return sum(int((conn.execute(query, (account_id,)).fetchone() or [0])[0] or 0) for query in queries)


def _has_storage_capacity(conn: Any, *, account_id: str, snapshot: dict[str, Any]) -> bool:
    added = len(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) * 2
    return _account_storage_bytes(conn, account_id=account_id) + added <= MAX_TOTAL_STORAGE_BYTES


def _clear_other_default(conn: Any, *, account_id: str, except_id: str, now: str) -> bool:
    rows = conn.execute(
        """SELECT id, project_id, content_brief_id, title, vault_kind, language, style_notes, use_context,
                  consent_status, consent_note, tags_json, policy_marker, state, is_default, revision,
                  created_at, updated_at, archived_at
           FROM web_voice_vaults WHERE account_id=? AND id<>? AND state='active' AND is_default=1""",
        (account_id, except_id),
    ).fetchall()
    # Validate every side-effect before writing any of them. A default switch
    # must never clear a current default without being able to preserve its
    # revision history as well.
    if any(not _can_add_version(conn, table="web_voice_vault_versions", entity_column="vault_id", entity_id=str(row[0]), account_id=account_id) for row in rows):
        return False
    for row in rows:
        references = _reference_snapshot(conn, account_id=account_id, references=_vault_reference_ids(row), require_active=False)
        snapshot = _vault_snapshot_from_row(row, references=references, is_default=False)
        revision = int(row[14]) + 1
        _write_vault(conn, vault_id=str(row[0]), account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_vault_version(conn, vault_id=str(row[0]), account_id=account_id, revision=revision, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, vault_id=str(row[0]), action="default_cleared", revision=revision)
    return True


def _summary_data(conn: Any, *, account_id: str) -> dict[str, Any]:
    vault_states = {str(row[0]): int(row[1]) for row in conn.execute("SELECT state, COUNT(*) FROM web_voice_vaults WHERE account_id=? GROUP BY state", (account_id,)).fetchall()}
    script_states = {str(row[0]): int(row[1]) for row in conn.execute("SELECT state, COUNT(*) FROM web_voice_scripts WHERE account_id=? GROUP BY state", (account_id,)).fetchall()}
    kinds = {str(row[0]): int(row[1]) for row in conn.execute("SELECT vault_kind, COUNT(*) FROM web_voice_vaults WHERE account_id=? AND state='active' GROUP BY vault_kind", (account_id,)).fetchall()}
    default_row = conn.execute("SELECT id FROM web_voice_vaults WHERE account_id=? AND state='active' AND is_default=1 LIMIT 1", (account_id,)).fetchone()
    return {
        "vaults": {"active": vault_states.get("active", 0), "archived": vault_states.get("archived", 0), "total": sum(vault_states.values()), "limit_per_state": MAX_VAULTS_PER_STATE},
        "scripts": {"active": script_states.get("active", 0), "archived": script_states.get("archived", 0), "total": sum(script_states.values()), "limit_per_vault": MAX_SCRIPTS_PER_VAULT, "limit_per_account": MAX_SCRIPTS_PER_ACCOUNT},
        "by_kind": kinds, "default_vault_id": str(default_row[0]) if default_row else None,
        "execution": "authoring_only", "provider_called": False, "audio_created": False,
    }


def _references_listing(conn: Any, *, account_id: str) -> dict[str, list[dict[str, Any]]]:
    projects = conn.execute("SELECT id, title, updated_at FROM web_projects WHERE account_id=? AND state='active' ORDER BY updated_at DESC, id DESC LIMIT 100", (account_id,)).fetchall()
    briefs = conn.execute("SELECT id, title, content_kind, updated_at FROM web_content_briefs WHERE account_id=? AND state='active' ORDER BY updated_at DESC, id DESC LIMIT 100", (account_id,)).fetchall()
    return {
        "projects": [{"id": str(row[0]), "title": str(row[1]), "updated_at": str(row[2])} for row in projects],
        "content_briefs": [{"id": str(row[0]), "title": str(row[1]), "content_kind": str(row[2]), "updated_at": str(row[3])} for row in briefs],
    }


def _vault_detail(conn: Any, *, vault_id: str, account_id: str) -> dict[str, Any] | None:
    vault = _vault_row(conn, vault_id=vault_id, account_id=account_id)
    if not vault:
        return None
    versions = conn.execute("SELECT revision, snapshot_json, created_at FROM web_voice_vault_versions WHERE vault_id=? AND account_id=? ORDER BY revision DESC LIMIT ?", (vault_id, account_id, MAX_VERSIONS_PER_ENTITY)).fetchall()
    scripts = conn.execute(
        """SELECT id, vault_id, title, script_kind, language, audience, pace_wpm, script_text, delivery_notes,
                  pronunciation_notes, tags_json, policy_marker, source_kind, state, revision, created_at, updated_at, archived_at
           FROM web_voice_scripts WHERE vault_id=? AND account_id=?
           ORDER BY CASE state WHEN 'active' THEN 0 ELSE 1 END, ordinal ASC, updated_at DESC, id DESC LIMIT ?""",
        (vault_id, account_id, MAX_SCRIPTS_PER_VAULT),
    ).fetchall()
    events = conn.execute(
        "SELECT action, entity_type, script_id, revision, created_at FROM web_voice_studio_events WHERE vault_id=? AND account_id=? ORDER BY created_at DESC, id DESC LIMIT ?",
        (vault_id, account_id, MAX_EVENT_LIMIT),
    ).fetchall()
    refs = _reference_snapshot(conn, account_id=account_id, references=_vault_reference_ids(vault), require_active=False)
    return {
        "vault": _vault_public(vault, include_content=True), "versions": [_vault_version_public(row) for row in versions],
        "scripts": [_script_public(row, include_content=True) for row in scripts],
        "events": [{"action": str(row[0]), "entity_type": str(row[1]), "script_id": str(row[2]) if row[2] else None, "revision": int(row[3]), "created_at": str(row[4])} for row in events],
        "references": refs, "script_count": len(scripts), "script_limit": MAX_SCRIPTS_PER_VAULT,
    }


def _script_detail(conn: Any, *, vault_id: str, script_id: str, account_id: str) -> dict[str, Any] | None:
    script = _script_row(conn, vault_id=vault_id, script_id=script_id, account_id=account_id)
    if not script:
        return None
    versions = conn.execute("SELECT revision, snapshot_json, created_at FROM web_voice_script_versions WHERE script_id=? AND account_id=? ORDER BY revision DESC LIMIT ?", (script_id, account_id, MAX_VERSIONS_PER_ENTITY)).fetchall()
    return {"script": _script_public(script, include_content=True), "versions": [_script_version_public(row) for row in versions]}


def _compose_scaffolds(vault: tuple[Any, ...]) -> list[dict[str, Any]]:
    """Build three transparent local writing scaffolds, never audio output."""
    title = str(vault[3])
    language = str(vault[5]) or "vi"
    style = str(vault[6]) or "rõ ràng và tự nhiên"
    context = str(vault[7]) or "bối cảnh đã chọn"
    tags = _decode_tags(vault[10])
    common = f"Voice direction: {title}\nCách thể hiện: {style}\nNgữ cảnh: {context}"
    return [
        {"title": "Khung lời mở đầu", "script_kind": "narration", "language": language, "audience": "", "pace_wpm": 145,
         "script_text": f"[Mở đầu — thay bằng thông tin đã kiểm tra]\n\n{common}\n\nĐiểm cần nói: [ ]\nLý do người nghe nên chú ý: [ ]",
         "delivery_notes": "Đọc chậm, rõ ý. Đây là khung biên tập cục bộ, không phải audio preview hoặc TTS.", "pronunciation_notes": "", "tags": tags},
        {"title": "Khung nội dung chính", "script_kind": "explainer", "language": language, "audience": "", "pace_wpm": 145,
         "script_text": f"[Nội dung chính]\n\n{common}\n\nÝ 1: [ ]\nÝ 2: [ ]\nVí dụ hoặc bằng chứng cần xác minh: [ ]",
         "delivery_notes": "Chia câu theo nhịp tự nhiên; người biên tập chịu trách nhiệm về claim cuối cùng.", "pronunciation_notes": "", "tags": tags},
        {"title": "Khung kết & CTA", "script_kind": "ad", "language": language, "audience": "", "pace_wpm": 145,
         "script_text": f"[Kết]\n\nTóm tắt: [ ]\nBước tiếp theo: [ ]\n\n{common}",
         "delivery_notes": "Giữ CTA rõ ràng; chưa có publish, delivery, charge hoặc output audio trong Voice Studio.", "pronunciation_notes": "", "tags": tags},
    ]


@router.get("/summary")
async def voice_studio_summary(account: dict = Depends(require_account)):
    _require_enabled()
    ensure_copyfast_schema()
    with read_transaction() as conn:
        return envelope(True, "Voice Studio đã sẵn sàng cho authoring Web-native.", data=_summary_data(conn, account_id=str(account["id"])), status_name="completed")


@router.get("/policy")
async def voice_studio_policy(account: dict = Depends(require_account)):
    _require_enabled()
    return envelope(True, "Boundary Voice Studio đã được công bố.", data={
        "execution": "authoring_only", "provider_called": False, "audio_created": False,
        "raw_audio_stored": False, "provider_voice_ids_stored": False, "telegram_file_ids_stored": False,
        "tts": "guarded", "voice_clone": "guarded", "preview": "guarded", "output_delivery": "guarded",
        "consent": "self_attested_metadata_only", "cue_sheet": "local_deterministic_writing_aid",
    }, status_name="read_only")


@router.get("/references")
async def voice_studio_references(account: dict = Depends(require_account)):
    _require_enabled()
    ensure_copyfast_schema()
    with read_transaction() as conn:
        return envelope(True, "Đã nạp reference Web-owned thuộc account hiện tại.", data=_references_listing(conn, account_id=str(account["id"])), status_name="completed")


@router.get("/vaults")
async def list_vaults(q: str = "", tag: str = "", state: str = "all", limit: int = 100, account: dict = Depends(require_account)):
    _require_enabled()
    ensure_copyfast_schema()
    query = _safe_filter(q, label="Từ khoá", maximum=100)
    tag_filter = _safe_filter(tag, label="Tag", maximum=MAX_TAG_LENGTH)
    state_value = str(state or "all").strip().lower()
    if state_value not in {"all", *VAULT_STATES}:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái không hợp lệ")
    bounded = max(1, min(MAX_LIST_LIMIT, int(limit)))
    where = ["account_id=?"]
    params: list[Any] = [str(account["id"])]
    if state_value != "all":
        where.append("state=?")
        params.append(state_value)
    if query:
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where.append("(title LIKE ? ESCAPE '\\' OR style_notes LIKE ? ESCAPE '\\' OR use_context LIKE ? ESCAPE '\\')")
        params.extend([f"%{escaped}%", f"%{escaped}%", f"%{escaped}%"])
    if tag_filter:
        escaped = tag_filter.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where.append("tags_json LIKE ? ESCAPE '\\'")
        params.append(f"%{escaped}%")
    with read_transaction() as conn:
        rows = conn.execute(
            f"""SELECT id, project_id, content_brief_id, title, vault_kind, language, style_notes, use_context,
                       consent_status, consent_note, tags_json, policy_marker, state, is_default, revision,
                       created_at, updated_at, archived_at
                FROM web_voice_vaults WHERE {' AND '.join(where)}
                ORDER BY CASE state WHEN 'active' THEN 0 ELSE 1 END, is_default DESC, updated_at DESC, id DESC LIMIT ?""",
            (*params, bounded),
        ).fetchall()
        return envelope(True, "Đã nạp Voice Vault riêng tư.", data={"items": [_vault_public(row) for row in rows], "limit": bounded}, status_name="completed")


@router.post("/vaults")
async def create_vault(payload: VaultCreateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    account_id = str(account["id"])
    fingerprint = _fingerprint({"operation": "vault-create", **payload.model_dump(exclude={"idempotency_key"})})

    def operation(conn: Any) -> dict[str, Any]:
        count = conn.execute("SELECT COUNT(*) FROM web_voice_vaults WHERE account_id=? AND state='active'", (account_id,)).fetchone()
        if int(count[0] or 0) >= MAX_VAULTS_PER_STATE:
            return envelope(False, "Voice Vault đã đạt giới hạn bản ghi đang hoạt động.", status_name="guarded", error_code="WEB_VOICE_VAULT_LIMIT")
        references = _reference_snapshot(conn, account_id=account_id, references={"project_id": payload.project_id, "content_brief_id": payload.content_brief_id})
        snapshot = _vault_snapshot(payload, references=references)
        if not _has_storage_capacity(conn, account_id=account_id, snapshot=snapshot):
            return envelope(False, "Voice Studio đã đạt giới hạn lưu trữ authoring riêng tư.", status_name="guarded", error_code="WEB_VOICE_STORAGE_LIMIT")
        vault_id = str(uuid.uuid4())
        now = utc_now()
        if snapshot["is_default"] and not _clear_other_default(conn, account_id=account_id, except_id=vault_id, now=now):
            return envelope(False, "Không thể đổi direction mặc định vì lịch sử của direction hiện tại đã đạt giới hạn an toàn.", status_name="guarded", error_code="WEB_VOICE_VERSION_LIMIT")
        _insert_vault(conn, vault_id=vault_id, account_id=account_id, snapshot=snapshot, revision=1, now=now)
        _insert_vault_version(conn, vault_id=vault_id, account_id=account_id, revision=1, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, vault_id=vault_id, action="vault_created", revision=1)
        _audit(conn, request=request, account=account, action="web.voice.vault.create", target=vault_id, detail=f"kind={payload.vault_kind};default={int(payload.is_default)}")
        row = _vault_row(conn, vault_id=vault_id, account_id=account_id)
        return envelope(True, "Đã tạo Voice Vault Web-native.", data={"vault": _vault_public(row) if row else {}, "execution": "metadata_only", "provider_called": False, "audio_created": False}, status_name="draft")

    return _idempotent(f"web-voice-studio:{account_id}:vault:create", account_id, payload.idempotency_key, fingerprint, operation)


@router.get("/vaults/{vault_id}")
async def get_vault(vault_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    resolved = _uuid(vault_id, label="Voice Vault ID")
    with read_transaction() as conn:
        detail = _vault_detail(conn, vault_id=resolved, account_id=str(account["id"]))
    return envelope(True, "Đã nạp Voice Vault riêng tư.", data=detail, status_name="completed") if detail else _vault_not_found()


@router.patch("/vaults/{vault_id}")
async def update_vault(vault_id: str, payload: VaultUpdateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    resolved = _uuid(vault_id, label="Voice Vault ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"operation": "vault-update", "vault_id": resolved, **payload.model_dump(exclude={"idempotency_key"})})

    def operation(conn: Any) -> dict[str, Any]:
        existing = _vault_row(conn, vault_id=resolved, account_id=account_id)
        if not existing:
            return _vault_not_found()
        if str(existing[12]) != "active":
            return _vault_archived()
        if int(existing[14]) != payload.expected_revision:
            return _revision_conflict()
        if not _can_add_version(conn, table="web_voice_vault_versions", entity_column="vault_id", entity_id=resolved, account_id=account_id):
            return envelope(False, "Voice Vault đã đạt giới hạn lịch sử phiên bản.", status_name="guarded", error_code="WEB_VOICE_VERSION_LIMIT")
        references = _reference_snapshot(conn, account_id=account_id, references={"project_id": payload.project_id, "content_brief_id": payload.content_brief_id})
        snapshot = _vault_snapshot(payload, references=references)
        if not _has_storage_capacity(conn, account_id=account_id, snapshot=snapshot):
            return envelope(False, "Voice Studio đã đạt giới hạn lưu trữ authoring riêng tư.", status_name="guarded", error_code="WEB_VOICE_STORAGE_LIMIT")
        now = utc_now()
        if snapshot["is_default"] and not _clear_other_default(conn, account_id=account_id, except_id=resolved, now=now):
            return envelope(False, "Không thể đổi direction mặc định vì lịch sử của direction hiện tại đã đạt giới hạn an toàn.", status_name="guarded", error_code="WEB_VOICE_VERSION_LIMIT")
        revision = int(existing[14]) + 1
        _write_vault(conn, vault_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_vault_version(conn, vault_id=resolved, account_id=account_id, revision=revision, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, vault_id=resolved, action="vault_updated", revision=revision)
        _audit(conn, request=request, account=account, action="web.voice.vault.update", target=resolved, detail=f"revision={revision};default={int(payload.is_default)}")
        row = _vault_row(conn, vault_id=resolved, account_id=account_id)
        return envelope(True, "Đã lưu revision Voice Vault mới.", data={"vault": _vault_public(row) if row else {}, "history_snapshot_recorded": True, "execution": "metadata_only", "provider_called": False, "audio_created": False}, status_name="draft")

    return _idempotent(f"web-voice-studio:{account_id}:vault:{resolved}:update", account_id, payload.idempotency_key, fingerprint, operation)


def _vault_state_mutation(vault_id: str, payload: RevisionMutationRequest | RestoreVersionRequest, request: Request, account: dict, *, action: str) -> dict[str, Any]:
    account_id = str(account["id"])
    resolved = _uuid(vault_id, label="Voice Vault ID")
    source_revision = payload.target_revision if isinstance(payload, RestoreVersionRequest) else None
    fingerprint = _fingerprint({"operation": f"vault-{action}", "vault_id": resolved, "expected_revision": payload.expected_revision, "source_revision": source_revision})

    def operation(conn: Any) -> dict[str, Any]:
        existing = _vault_row(conn, vault_id=resolved, account_id=account_id)
        if not existing:
            return _vault_not_found()
        if int(existing[14]) != payload.expected_revision:
            return _revision_conflict()
        if not _can_add_version(conn, table="web_voice_vault_versions", entity_column="vault_id", entity_id=resolved, account_id=account_id):
            return envelope(False, "Voice Vault đã đạt giới hạn lịch sử phiên bản.", status_name="guarded", error_code="WEB_VOICE_VERSION_LIMIT")
        current_state = str(existing[12])
        now = utc_now()
        if action == "archive":
            if current_state != "active":
                return _vault_archived()
            refs = _reference_snapshot(conn, account_id=account_id, references=_vault_reference_ids(existing), require_active=False)
            snapshot = _vault_snapshot_from_row(existing, references=refs, state="archived", is_default=False)
            event = "vault_archived"
        elif action == "restore":
            if current_state != "archived":
                return envelope(False, "Voice Vault đang hoạt động.", status_name="guarded", error_code="WEB_VOICE_VAULT_ACTIVE")
            count = conn.execute("SELECT COUNT(*) FROM web_voice_vaults WHERE account_id=? AND state='active'", (account_id,)).fetchone()
            if int(count[0] or 0) >= MAX_VAULTS_PER_STATE:
                return envelope(False, "Voice Vault đã đạt giới hạn bản ghi đang hoạt động.", status_name="guarded", error_code="WEB_VOICE_VAULT_LIMIT")
            refs = _reference_snapshot(conn, account_id=account_id, references=_vault_reference_ids(existing), require_active=True)
            snapshot = _vault_snapshot_from_row(existing, references=refs, state="active")
            event = "vault_restored"
        elif action == "restore-version":
            source = conn.execute("SELECT snapshot_json FROM web_voice_vault_versions WHERE vault_id=? AND account_id=? AND revision=?", (resolved, account_id, source_revision)).fetchone()
            if not source:
                return envelope(False, "Không tìm thấy phiên bản Voice Vault cần khôi phục.", status_name="guarded", error_code="WEB_VOICE_VERSION_NOT_FOUND")
            try:
                saved = json.loads(str(source[0]))
                restored_payload = _vault_payload_from_snapshot(saved if isinstance(saved, dict) else {})
            except (TypeError, ValueError, json.JSONDecodeError):
                return envelope(False, "Phiên bản Voice Vault không hợp lệ.", status_name="guarded", error_code="WEB_VOICE_VERSION_INVALID")
            if current_state != "active":
                return _vault_archived()
            refs = _reference_snapshot(conn, account_id=account_id, references={"project_id": restored_payload.project_id, "content_brief_id": restored_payload.content_brief_id}, require_active=True)
            snapshot = _vault_snapshot(restored_payload, references=refs, state="active")
            event = "vault_version_restored"
        else:
            raise HTTPException(status_code=500, detail="Thao tác Voice Vault không hỗ trợ")
        if snapshot.get("is_default") and snapshot["state"] == "active" and not _clear_other_default(conn, account_id=account_id, except_id=resolved, now=now):
            return envelope(False, "Không thể đổi direction mặc định vì lịch sử của direction hiện tại đã đạt giới hạn an toàn.", status_name="guarded", error_code="WEB_VOICE_VERSION_LIMIT")
        revision = int(existing[14]) + 1
        _write_vault(conn, vault_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=now if snapshot["state"] == "archived" else None)
        _insert_vault_version(conn, vault_id=resolved, account_id=account_id, revision=revision, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, vault_id=resolved, action=event, revision=revision)
        _audit(conn, request=request, account=account, action=f"web.voice.vault.{action}", target=resolved, detail=f"revision={revision}")
        row = _vault_row(conn, vault_id=resolved, account_id=account_id)
        return envelope(True, "Đã cập nhật trạng thái Voice Vault.", data={"vault": _vault_public(row) if row else {}, "history_snapshot_recorded": True, "execution": "metadata_only", "provider_called": False, "audio_created": False}, status_name="draft")

    return _idempotent(f"web-voice-studio:{account_id}:vault:{resolved}:{action}{':' + str(source_revision) if source_revision else ''}", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/vaults/{vault_id}/archive")
async def archive_vault(vault_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    return _vault_state_mutation(vault_id, payload, request, account, action="archive")


@router.post("/vaults/{vault_id}/restore")
async def restore_vault(vault_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    return _vault_state_mutation(vault_id, payload, request, account, action="restore")


@router.post("/vaults/{vault_id}/restore-version")
async def restore_vault_version(vault_id: str, payload: RestoreVersionRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    return _vault_state_mutation(vault_id, payload, request, account, action="restore-version")


@router.post("/vaults/{vault_id}/duplicate")
async def duplicate_vault(vault_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    resolved = _uuid(vault_id, label="Voice Vault ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"operation": "vault-duplicate", "vault_id": resolved, "expected_revision": payload.expected_revision})

    def operation(conn: Any) -> dict[str, Any]:
        existing = _vault_row(conn, vault_id=resolved, account_id=account_id)
        if not existing:
            return _vault_not_found()
        if str(existing[12]) != "active":
            return _vault_archived()
        if _vault_consent_revoked(existing):
            return _authoring_blocked_by_revoked_consent()
        if int(existing[14]) != payload.expected_revision:
            return _revision_conflict()
        count = conn.execute("SELECT COUNT(*) FROM web_voice_vaults WHERE account_id=? AND state='active'", (account_id,)).fetchone()
        if int(count[0] or 0) >= MAX_VAULTS_PER_STATE:
            return envelope(False, "Voice Vault đã đạt giới hạn bản ghi đang hoạt động.", status_name="guarded", error_code="WEB_VOICE_VAULT_LIMIT")
        refs = _reference_snapshot(conn, account_id=account_id, references=_vault_reference_ids(existing), require_active=True)
        source = _vault_snapshot_from_row(existing, references=refs, is_default=False)
        source["title"] = _single_line(f"{source['title']} (bản sao)", label="Tên Voice Vault", minimum=2, maximum=MAX_TITLE)
        if not _has_storage_capacity(conn, account_id=account_id, snapshot=source):
            return envelope(False, "Voice Studio đã đạt giới hạn lưu trữ authoring riêng tư.", status_name="guarded", error_code="WEB_VOICE_STORAGE_LIMIT")
        created_id = str(uuid.uuid4())
        now = utc_now()
        _insert_vault(conn, vault_id=created_id, account_id=account_id, snapshot=source, revision=1, now=now)
        _insert_vault_version(conn, vault_id=created_id, account_id=account_id, revision=1, snapshot=source, created_at=now)
        _event(conn, account_id=account_id, vault_id=created_id, action="vault_duplicated", revision=1)
        _audit(conn, request=request, account=account, action="web.voice.vault.duplicate", target=created_id, detail=f"source={resolved}")
        row = _vault_row(conn, vault_id=created_id, account_id=account_id)
        return envelope(True, "Đã nhân bản Voice Vault riêng tư.", data={"vault": _vault_public(row) if row else {}, "execution": "metadata_only", "provider_called": False, "audio_created": False}, status_name="draft")

    return _idempotent(f"web-voice-studio:{account_id}:vault:{resolved}:duplicate", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/vaults/{vault_id}/compose")
async def compose_vault_scripts(vault_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    resolved = _uuid(vault_id, label="Voice Vault ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"operation": "vault-compose-local", "vault_id": resolved, "expected_revision": payload.expected_revision})

    def operation(conn: Any) -> dict[str, Any]:
        vault = _vault_row(conn, vault_id=resolved, account_id=account_id)
        if not vault:
            return _vault_not_found()
        if str(vault[12]) != "active":
            return _vault_archived()
        if _vault_consent_revoked(vault):
            return _authoring_blocked_by_revoked_consent()
        if int(vault[14]) != payload.expected_revision:
            return _revision_conflict()
        existing_count = conn.execute("SELECT COUNT(*) FROM web_voice_scripts WHERE vault_id=? AND account_id=? AND state='active'", (resolved, account_id)).fetchone()
        account_count = conn.execute("SELECT COUNT(*) FROM web_voice_scripts WHERE account_id=? AND state='active'", (account_id,)).fetchone()
        scaffolds = _compose_scaffolds(vault)
        if int(existing_count[0] or 0) + len(scaffolds) > MAX_SCRIPTS_PER_VAULT or int(account_count[0] or 0) + len(scaffolds) > MAX_SCRIPTS_PER_ACCOUNT:
            return envelope(False, "Không đủ chỗ để thêm 3 khung script cục bộ.", status_name="guarded", error_code="WEB_VOICE_SCRIPT_LIMIT")
        snapshots = [_script_snapshot(ScriptPayload.model_validate(item), source_kind="local_deterministic_draft_only") for item in scaffolds]
        if any(not _has_storage_capacity(conn, account_id=account_id, snapshot=item) for item in snapshots):
            return envelope(False, "Voice Studio đã đạt giới hạn lưu trữ authoring riêng tư.", status_name="guarded", error_code="WEB_VOICE_STORAGE_LIMIT")
        ordinal_row = conn.execute("SELECT COALESCE(MAX(ordinal), 0) FROM web_voice_scripts WHERE vault_id=? AND account_id=?", (resolved, account_id)).fetchone()
        ordinal = int(ordinal_row[0] or 0)
        now = utc_now()
        ids: list[str] = []
        for snapshot in snapshots:
            ordinal += 1
            script_id = str(uuid.uuid4())
            _insert_script(conn, script_id=script_id, vault_id=resolved, account_id=account_id, ordinal=ordinal, snapshot=snapshot, revision=1, now=now)
            _insert_script_version(conn, script_id=script_id, account_id=account_id, revision=1, snapshot=snapshot, created_at=now)
            _event(conn, account_id=account_id, vault_id=resolved, script_id=script_id, action="script_composed_local", revision=1)
            ids.append(script_id)
        _event(conn, account_id=account_id, vault_id=resolved, action="vault_composed_local", revision=int(vault[14]))
        _audit(conn, request=request, account=account, action="web.voice.vault.compose", target=resolved, detail=f"scripts={len(ids)};execution=local")
        return envelope(True, "Đã tạo 3 khung script cục bộ để biên tập.", data={"vault": _vault_public(vault), "script_ids": ids, "execution": "local_deterministic_draft_only", "provider_called": False, "audio_created": False}, status_name="draft")

    return _idempotent(f"web-voice-studio:{account_id}:vault:{resolved}:compose", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/vaults/{vault_id}/scripts")
async def create_script(vault_id: str, payload: ScriptCreateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    resolved = _uuid(vault_id, label="Voice Vault ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"operation": "script-create", "vault_id": resolved, **payload.model_dump(exclude={"idempotency_key"})})

    def operation(conn: Any) -> dict[str, Any]:
        vault = _vault_row(conn, vault_id=resolved, account_id=account_id)
        if not vault:
            return _vault_not_found()
        if str(vault[12]) != "active":
            return _vault_archived()
        if _vault_consent_revoked(vault):
            return _authoring_blocked_by_revoked_consent()
        if int(vault[14]) != payload.expected_revision:
            return _revision_conflict()
        vault_count = conn.execute("SELECT COUNT(*) FROM web_voice_scripts WHERE vault_id=? AND account_id=? AND state='active'", (resolved, account_id)).fetchone()
        account_count = conn.execute("SELECT COUNT(*) FROM web_voice_scripts WHERE account_id=? AND state='active'", (account_id,)).fetchone()
        if int(vault_count[0] or 0) >= MAX_SCRIPTS_PER_VAULT or int(account_count[0] or 0) >= MAX_SCRIPTS_PER_ACCOUNT:
            return envelope(False, "Voice Studio đã đạt giới hạn script riêng tư.", status_name="guarded", error_code="WEB_VOICE_SCRIPT_LIMIT")
        snapshot = _script_snapshot(payload)
        if not _has_storage_capacity(conn, account_id=account_id, snapshot=snapshot):
            return envelope(False, "Voice Studio đã đạt giới hạn lưu trữ authoring riêng tư.", status_name="guarded", error_code="WEB_VOICE_STORAGE_LIMIT")
        ordinal_row = conn.execute("SELECT COALESCE(MAX(ordinal), 0) FROM web_voice_scripts WHERE vault_id=? AND account_id=?", (resolved, account_id)).fetchone()
        script_id = str(uuid.uuid4())
        now = utc_now()
        _insert_script(conn, script_id=script_id, vault_id=resolved, account_id=account_id, ordinal=int(ordinal_row[0] or 0) + 1, snapshot=snapshot, revision=1, now=now)
        _insert_script_version(conn, script_id=script_id, account_id=account_id, revision=1, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, vault_id=resolved, script_id=script_id, action="script_created", revision=1)
        _audit(conn, request=request, account=account, action="web.voice.script.create", target=script_id, detail=f"vault={resolved};kind={payload.script_kind}")
        row = _script_row(conn, vault_id=resolved, script_id=script_id, account_id=account_id)
        return envelope(True, "Đã thêm script riêng tư vào Voice Vault.", data={"script": _script_public(row) if row else {}, "execution": "authoring_only", "provider_called": False, "audio_created": False}, status_name="draft")

    return _idempotent(f"web-voice-studio:{account_id}:vault:{resolved}:script:create", account_id, payload.idempotency_key, fingerprint, operation)


@router.get("/vaults/{vault_id}/scripts/{script_id}")
async def get_script(vault_id: str, script_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    resolved_vault = _uuid(vault_id, label="Voice Vault ID")
    resolved_script = _uuid(script_id, label="Script ID")
    with read_transaction() as conn:
        detail = _script_detail(conn, vault_id=resolved_vault, script_id=resolved_script, account_id=str(account["id"]))
    return envelope(True, "Đã nạp script riêng tư.", data=detail, status_name="completed") if detail else _script_not_found()


@router.patch("/vaults/{vault_id}/scripts/{script_id}")
async def update_script(vault_id: str, script_id: str, payload: ScriptUpdateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    resolved_vault = _uuid(vault_id, label="Voice Vault ID")
    resolved_script = _uuid(script_id, label="Script ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"operation": "script-update", "vault_id": resolved_vault, "script_id": resolved_script, **payload.model_dump(exclude={"idempotency_key"})})

    def operation(conn: Any) -> dict[str, Any]:
        vault = _vault_row(conn, vault_id=resolved_vault, account_id=account_id)
        if not vault:
            return _vault_not_found()
        if str(vault[12]) != "active":
            return _vault_archived()
        if _vault_consent_revoked(vault):
            return _authoring_blocked_by_revoked_consent()
        existing = _script_row(conn, vault_id=resolved_vault, script_id=resolved_script, account_id=account_id)
        if not existing:
            return _script_not_found()
        if str(existing[13]) != "active":
            return _script_archived()
        if int(existing[14]) != payload.expected_revision:
            return _revision_conflict()
        if not _can_add_version(conn, table="web_voice_script_versions", entity_column="script_id", entity_id=resolved_script, account_id=account_id):
            return envelope(False, "Script đã đạt giới hạn lịch sử phiên bản.", status_name="guarded", error_code="WEB_VOICE_VERSION_LIMIT")
        snapshot = _script_snapshot(payload)
        if not _has_storage_capacity(conn, account_id=account_id, snapshot=snapshot):
            return envelope(False, "Voice Studio đã đạt giới hạn lưu trữ authoring riêng tư.", status_name="guarded", error_code="WEB_VOICE_STORAGE_LIMIT")
        now = utc_now()
        revision = int(existing[14]) + 1
        _write_script(conn, script_id=resolved_script, vault_id=resolved_vault, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_script_version(conn, script_id=resolved_script, account_id=account_id, revision=revision, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, vault_id=resolved_vault, script_id=resolved_script, action="script_updated", revision=revision)
        _audit(conn, request=request, account=account, action="web.voice.script.update", target=resolved_script, detail=f"vault={resolved_vault};revision={revision}")
        row = _script_row(conn, vault_id=resolved_vault, script_id=resolved_script, account_id=account_id)
        return envelope(True, "Đã lưu revision script mới.", data={"script": _script_public(row) if row else {}, "history_snapshot_recorded": True, "execution": "authoring_only", "provider_called": False, "audio_created": False}, status_name="draft")

    return _idempotent(f"web-voice-studio:{account_id}:vault:{resolved_vault}:script:{resolved_script}:update", account_id, payload.idempotency_key, fingerprint, operation)


def _script_state_mutation(vault_id: str, script_id: str, payload: RevisionMutationRequest | RestoreVersionRequest, request: Request, account: dict, *, action: str) -> dict[str, Any]:
    account_id = str(account["id"])
    resolved_vault = _uuid(vault_id, label="Voice Vault ID")
    resolved_script = _uuid(script_id, label="Script ID")
    source_revision = payload.target_revision if isinstance(payload, RestoreVersionRequest) else None
    fingerprint = _fingerprint({"operation": f"script-{action}", "vault_id": resolved_vault, "script_id": resolved_script, "expected_revision": payload.expected_revision, "source_revision": source_revision})

    def operation(conn: Any) -> dict[str, Any]:
        vault = _vault_row(conn, vault_id=resolved_vault, account_id=account_id)
        if not vault:
            return _vault_not_found()
        if str(vault[12]) != "active":
            return _vault_archived()
        existing = _script_row(conn, vault_id=resolved_vault, script_id=resolved_script, account_id=account_id)
        if not existing:
            return _script_not_found()
        if int(existing[14]) != payload.expected_revision:
            return _revision_conflict()
        if not _can_add_version(conn, table="web_voice_script_versions", entity_column="script_id", entity_id=resolved_script, account_id=account_id):
            return envelope(False, "Script đã đạt giới hạn lịch sử phiên bản.", status_name="guarded", error_code="WEB_VOICE_VERSION_LIMIT")
        current_state = str(existing[13])
        if _vault_consent_revoked(vault) and action != "archive":
            return _authoring_blocked_by_revoked_consent()
        if action == "archive":
            if current_state != "active":
                return _script_archived()
            snapshot = _script_snapshot_from_row(existing, state="archived")
            event = "script_archived"
        elif action == "restore":
            if str(vault[12]) != "active":
                return _vault_archived()
            if current_state != "archived":
                return envelope(False, "Script đang hoạt động.", status_name="guarded", error_code="WEB_VOICE_SCRIPT_ACTIVE")
            count = conn.execute("SELECT COUNT(*) FROM web_voice_scripts WHERE vault_id=? AND account_id=? AND state='active'", (resolved_vault, account_id)).fetchone()
            if int(count[0] or 0) >= MAX_SCRIPTS_PER_VAULT:
                return envelope(False, "Voice Vault đã đạt giới hạn script đang hoạt động.", status_name="guarded", error_code="WEB_VOICE_SCRIPT_LIMIT")
            snapshot = _script_snapshot_from_row(existing, state="active")
            event = "script_restored"
        elif action == "restore-version":
            if str(vault[12]) != "active" or current_state != "active":
                return _script_archived() if current_state != "active" else _vault_archived()
            saved = conn.execute("SELECT snapshot_json FROM web_voice_script_versions WHERE script_id=? AND account_id=? AND revision=?", (resolved_script, account_id, source_revision)).fetchone()
            if not saved:
                return envelope(False, "Không tìm thấy phiên bản script cần khôi phục.", status_name="guarded", error_code="WEB_VOICE_VERSION_NOT_FOUND")
            try:
                parsed = json.loads(str(saved[0]))
                restored_payload = _script_payload_from_snapshot(parsed if isinstance(parsed, dict) else {})
            except (TypeError, ValueError, json.JSONDecodeError):
                return envelope(False, "Phiên bản script không hợp lệ.", status_name="guarded", error_code="WEB_VOICE_VERSION_INVALID")
            snapshot = _script_snapshot(restored_payload, source_kind=str((parsed if isinstance(parsed, dict) else {}).get("source_kind") or "manual"))
            event = "script_version_restored"
        else:
            raise HTTPException(status_code=500, detail="Thao tác script không hỗ trợ")
        now = utc_now()
        revision = int(existing[14]) + 1
        _write_script(conn, script_id=resolved_script, vault_id=resolved_vault, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=now if snapshot["state"] == "archived" else None)
        _insert_script_version(conn, script_id=resolved_script, account_id=account_id, revision=revision, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, vault_id=resolved_vault, script_id=resolved_script, action=event, revision=revision)
        _audit(conn, request=request, account=account, action=f"web.voice.script.{action}", target=resolved_script, detail=f"vault={resolved_vault};revision={revision}")
        row = _script_row(conn, vault_id=resolved_vault, script_id=resolved_script, account_id=account_id)
        return envelope(True, "Đã cập nhật trạng thái script.", data={"script": _script_public(row) if row else {}, "history_snapshot_recorded": True, "execution": "authoring_only", "provider_called": False, "audio_created": False}, status_name="draft")

    return _idempotent(f"web-voice-studio:{account_id}:vault:{resolved_vault}:script:{resolved_script}:{action}{':' + str(source_revision) if source_revision else ''}", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/vaults/{vault_id}/scripts/{script_id}/archive")
async def archive_script(vault_id: str, script_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    return _script_state_mutation(vault_id, script_id, payload, request, account, action="archive")


@router.post("/vaults/{vault_id}/scripts/{script_id}/restore")
async def restore_script(vault_id: str, script_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    return _script_state_mutation(vault_id, script_id, payload, request, account, action="restore")


@router.post("/vaults/{vault_id}/scripts/{script_id}/restore-version")
async def restore_script_version(vault_id: str, script_id: str, payload: RestoreVersionRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    return _script_state_mutation(vault_id, script_id, payload, request, account, action="restore-version")


@router.post("/vaults/{vault_id}/scripts/{script_id}/duplicate")
async def duplicate_script(vault_id: str, script_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    resolved_vault = _uuid(vault_id, label="Voice Vault ID")
    resolved_script = _uuid(script_id, label="Script ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"operation": "script-duplicate", "vault_id": resolved_vault, "script_id": resolved_script, "expected_revision": payload.expected_revision})

    def operation(conn: Any) -> dict[str, Any]:
        vault = _vault_row(conn, vault_id=resolved_vault, account_id=account_id)
        if not vault:
            return _vault_not_found()
        if str(vault[12]) != "active":
            return _vault_archived()
        if _vault_consent_revoked(vault):
            return _authoring_blocked_by_revoked_consent()
        existing = _script_row(conn, vault_id=resolved_vault, script_id=resolved_script, account_id=account_id)
        if not existing:
            return _script_not_found()
        if str(existing[13]) != "active":
            return _script_archived()
        if int(existing[14]) != payload.expected_revision:
            return _revision_conflict()
        count = conn.execute("SELECT COUNT(*) FROM web_voice_scripts WHERE vault_id=? AND account_id=? AND state='active'", (resolved_vault, account_id)).fetchone()
        if int(count[0] or 0) >= MAX_SCRIPTS_PER_VAULT:
            return envelope(False, "Voice Vault đã đạt giới hạn script đang hoạt động.", status_name="guarded", error_code="WEB_VOICE_SCRIPT_LIMIT")
        snapshot = _script_snapshot_from_row(existing)
        snapshot["title"] = _single_line(f"{snapshot['title']} (bản sao)", label="Tên script", minimum=2, maximum=MAX_TITLE)
        if not _has_storage_capacity(conn, account_id=account_id, snapshot=snapshot):
            return envelope(False, "Voice Studio đã đạt giới hạn lưu trữ authoring riêng tư.", status_name="guarded", error_code="WEB_VOICE_STORAGE_LIMIT")
        ordinal_row = conn.execute("SELECT COALESCE(MAX(ordinal), 0) FROM web_voice_scripts WHERE vault_id=? AND account_id=?", (resolved_vault, account_id)).fetchone()
        created_id = str(uuid.uuid4())
        now = utc_now()
        _insert_script(conn, script_id=created_id, vault_id=resolved_vault, account_id=account_id, ordinal=int(ordinal_row[0] or 0) + 1, snapshot=snapshot, revision=1, now=now)
        _insert_script_version(conn, script_id=created_id, account_id=account_id, revision=1, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, vault_id=resolved_vault, script_id=created_id, action="script_duplicated", revision=1)
        _audit(conn, request=request, account=account, action="web.voice.script.duplicate", target=created_id, detail=f"source={resolved_script};vault={resolved_vault}")
        row = _script_row(conn, vault_id=resolved_vault, script_id=created_id, account_id=account_id)
        return envelope(True, "Đã nhân bản script riêng tư.", data={"script": _script_public(row) if row else {}, "execution": "authoring_only", "provider_called": False, "audio_created": False}, status_name="draft")

    return _idempotent(f"web-voice-studio:{account_id}:vault:{resolved_vault}:script:{resolved_script}:duplicate", account_id, payload.idempotency_key, fingerprint, operation)


@router.get("/vaults/{vault_id}/scripts/{script_id}/cue-sheet")
async def script_cue_sheet(vault_id: str, script_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    resolved_vault = _uuid(vault_id, label="Voice Vault ID")
    resolved_script = _uuid(script_id, label="Script ID")
    with read_transaction() as conn:
        vault = _vault_row(conn, vault_id=resolved_vault, account_id=str(account["id"]))
        script = _script_row(conn, vault_id=resolved_vault, script_id=resolved_script, account_id=str(account["id"]))
    if not vault:
        return _vault_not_found()
    if str(vault[12]) != "active":
        return _vault_archived()
    if _vault_consent_revoked(vault):
        return _authoring_blocked_by_revoked_consent()
    if not script:
        return _script_not_found()
    if str(script[13]) != "active":
        return _script_archived()
    text = str(script[7])
    pace = int(script[6])
    return envelope(True, "Đã tạo cue-sheet cục bộ để review script.", data={
        "script_id": resolved_script, "metrics": _metrics(text, pace), "items": _cue_sheet(text, pace),
        "execution": "local_deterministic_writing_aid", "provider_called": False, "audio_created": False,
        "notice": "Cue-sheet là ước lượng theo text; không phải transcript, audio preview, SRT hay output TTS.",
    }, status_name="completed")


@router.get("/events")
async def list_events(limit: int = 50, account: dict = Depends(require_account)):
    _require_enabled()
    bounded = max(1, min(MAX_EVENT_LIMIT, int(limit)))
    with read_transaction() as conn:
        rows = conn.execute(
            "SELECT vault_id, script_id, entity_type, action, revision, created_at FROM web_voice_studio_events WHERE account_id=? ORDER BY created_at DESC, id DESC LIMIT ?",
            (str(account["id"]), bounded),
        ).fetchall()
    return envelope(True, "Đã nạp hoạt động Voice Studio.", data={"items": [{"vault_id": str(row[0]), "script_id": str(row[1]) if row[1] else None, "entity_type": str(row[2]), "action": str(row[3]), "revision": int(row[4]), "created_at": str(row[5])} for row in rows], "limit": bounded}, status_name="completed")
