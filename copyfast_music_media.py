"""Private, Web-native Audio Library & Briefing workspace.

The frozen Telegram Bot owns its own provider searches, expiring preview
state, Telegram file IDs, Xu, jobs and media delivery.  This module does not
mirror any of those systems.  It gives a signed Web account a professional
place to organise *its own* Asset Vault audio references and music/SFX briefs,
with deterministic local prompt directions, version history and explicit
copyright safeguards.  No provider, Bot bridge, wallet, PayOS, raw URL fetch,
audio transcode, waveform or generated-media claim exists in this boundary.
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
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import ensure_copyfast_schema, memory_center_enabled, music_media_workspace_enabled, read_transaction, transaction, utc_now


router = APIRouter(prefix="/api/v1/media-workspace", tags=["Web Audio Library & Briefing"])

COLLECTION_STATES = frozenset({"active", "archived"})
PROMPT_MODES = frozenset({"background", "lyrics", "script", "melody", "custom"})
ITEM_ROLES = frozenset({"music", "sfx", "reference"})
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

# Mirrors the frozen Bot's compact semantic guard at bot.py:71307-71329.
# This is deliberately a policy marker, not an artist-name classifier and not
# a claim that the Web performed copyright clearance.
COPYRIGHT_BLOCK_MARKERS = (
    "giống nghệ sĩ", "giống ca sĩ", "giống bài", "như bài", "cover bài", "remix bài",
    "beat giống", "nhạc giống", "giai điệu giống", "style của", "phong cách của",
    "clone giọng", "nhái giọng", "bắt chước giọng", "sound like", "sounds like",
    "in the style of", "voice clone", "clone voice", "copy melody", "cover song",
    "remix song", "artist style", "same melody",
)

# A compact, text-only translation of the Bot's music prompt suggestions.  It
# deliberately contains no model, provider, catalog, URL or delivery setting.
# The first and second halves reproduce the Bot's "first three / next three"
# rotation without carrying forward its Telegram pending state.
MUSIC_PROMPT_COMPOSER_MODES = frozenset({"background", "lyrics", "melody", "script", "custom"})
MUSIC_PROMPT_COMPOSER_LANGUAGES = frozenset({"vi", "en"})
MUSIC_PROMPT_COMPOSER_SETS = frozenset({"primary", "alternate"})
MUSIC_PROMPT_COMPOSER_MAX_DESCRIPTION = 500
MUSIC_PROMPT_COMPOSER_MAX_TEXT = 2_400
# The explicit Composer-to-Memory handoff owns its write in this router, but
# remains bounded by the same durable envelope as Memory Center. Do not import
# private Memory router helpers: this handoff stays independent at runtime.
MAX_MEMORY_NOTE_TITLE = 160
MAX_MEMORY_NOTE_CONTENT = 12_000
MAX_MEMORY_NOTES_PER_ACCOUNT = 1_000
MUSIC_PROMPT_COMPOSER_MARKUP_PATTERN = re.compile(
    r"(?:<\s*/?\s*[A-Za-z][^>\r\n]{0,240}>|\[[^\]\r\n]{1,160}\]\([^\)\r\n]{1,480}\)|```|\bon[a-z]+\s*=)",
    re.IGNORECASE,
)
MUSIC_PROMPT_COMPOSER_URL_OR_FILE_PATTERN = re.compile(
    r"(?:\b(?:https?|ftp)://|\bwww\.|\b(?:file|data|javascript|tg):|(?:^|\s)[A-Za-z]:[\\/]|(?:^|\s)/(?:[A-Za-z0-9_.-]+/){1,})",
    re.IGNORECASE,
)
MUSIC_PROMPT_COMPOSER_HANDLE_PATTERN = re.compile(
    r"\b(?:(?:provider|model|engine|bot|telegram|render|job|media|asset|file|output|preview|audio|music)[ _-]*"
    r"(?:id|ref(?:erence)?|token|handle|url|path)|(?:upload|download)[ _-]*(?:id|url|path))\b|(?:^|\s)@[A-Za-z0-9_]{3,}",
    re.IGNORECASE,
)
MUSIC_PROMPT_COMPOSER_COPYRIGHT_MARKERS = COPYRIGHT_BLOCK_MARKERS + (
    "giọng của", "voice of ", "in the voice of", "ca khúc của", "song by ",
    "bài của", "artist's voice", "artist voice", "singer voice",
)

AUDIO_EXTENSIONS = frozenset({".mp3", ".wav", ".m4a", ".ogg"})
AUDIO_CONTENT_TYPES = {
    ".mp3": frozenset({"audio/mpeg"}),
    ".wav": frozenset({"audio/wav", "audio/x-wav"}),
    ".m4a": frozenset({"audio/mp4"}),
    ".ogg": frozenset({"audio/ogg", "application/ogg"}),
}

MAX_COLLECTIONS_PER_STATE = 500
MAX_ITEMS_PER_COLLECTION = 250
MAX_ITEMS_PER_ACCOUNT = 3_000
MAX_VERSIONS_PER_COLLECTION = 100
MAX_LIST_LIMIT = 100
MAX_EVENT_LIMIT = 50
MAX_TITLE = 180
MAX_DESCRIPTION = 6_000
MAX_BRIEF = 6_000
MAX_CONTEXT = 160
MAX_RIGHTS_NOTE = 800
MAX_TAGS = 16
MAX_TAG_LENGTH = 48
MAX_ATTRIBUTION = 500
MAX_ITEM_LABEL = 180
MAX_DECLARED_DURATION_SECONDS = 7_200
IDEMPOTENCY_RETENTION = timedelta(hours=24)
MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT = 1_024


def _require_enabled() -> None:
    if not music_media_workspace_enabled():
        raise HTTPException(
            status_code=503,
            detail="Audio Library & Briefing đang tạm dừng để bảo trì. WEBAPP_MUSIC_MEDIA_WORKSPACE_ENABLED chưa được bật.",
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


def _copyright_marker(*parts: str) -> str:
    normalized = re.sub(r"\s+", " ", "\n".join(str(part or "") for part in parts)).strip().lower()[:12_000]
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


def _receipt_safe(response: dict[str, Any]) -> dict[str, Any]:
    """Return a replay receipt without storing creative/private free text.

    A caller receives the normal mutation envelope during its first request,
    but an idempotency replay only needs the durable identifiers, revision and
    state needed for the UI to re-hydrate its owner-scoped projection.  Keeping
    collection content in ``web_idempotency`` would create a second, less
    constrained copy of a user's brief and contradict this module's storage
    boundary.
    """
    try:
        receipt = json.loads(json.dumps(response, ensure_ascii=False))
    except (TypeError, ValueError, json.JSONDecodeError):
        return envelope(
            False,
            "Không thể tạo receipt thao tác Audio Library an toàn.",
            status_name="guarded",
            error_code="WEB_MEDIA_RECEIPT_INVALID",
        )
    if not isinstance(receipt, dict):
        return envelope(
            False,
            "Không thể tạo receipt thao tác Audio Library an toàn.",
            status_name="guarded",
            error_code="WEB_MEDIA_RECEIPT_INVALID",
        )
    data = receipt.get("data")
    if isinstance(data, dict):
        collection = data.get("collection")
        if isinstance(collection, dict):
            # These fields are rendered only from the primary collection row
            # after signed owner hydration.  Neither a brief nor a rights note
            # belongs in a generic mutation receipt that is retained for 24h.
            for field in ("description", "creative_brief", "rights_note", "description_excerpt", "brief_excerpt"):
                collection.pop(field, None)
        # The current item mutations return identifiers only, but keep this
        # defensive scrubber narrow and explicit if a future response exposes
        # an item projection.
        item = data.get("item")
        if isinstance(item, dict):
            for field in ("title_override", "attribution", "license_note"):
                item.pop(field, None)
        note = data.get("note")
        if isinstance(note, dict):
            # The short-lived generic idempotency table is not a second copy
            # of a Music Prompt Composer description or selected direction.
            # The signed owner can hydrate the actual note from Memory Center.
            data["note"] = {
                "id": str(note.get("id") or ""),
                "revision": int(note.get("revision") or 0),
                "state": str(note.get("state") or ""),
                "category": str(note.get("category") or ""),
                "priority": str(note.get("priority") or ""),
            }
    return receipt


def _idempotent(
    scope: str,
    account_id: str,
    key: str,
    request_fingerprint: str,
    operation: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    """Persist successful mutation receipts only, without raw creative text."""
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute(
            "DELETE FROM web_idempotency WHERE scope LIKE ? AND created_at < ?",
            ("web-media-workspace:%", _idempotency_cutoff()),
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
                response = json.loads(str(existing[0]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Receipt Audio Library không hợp lệ") from exc
            if not isinstance(response, dict):
                raise HTTPException(status_code=409, detail="Receipt Audio Library không hợp lệ")
            return response
        receipt_count = conn.execute(
            "SELECT COUNT(*) FROM web_idempotency WHERE scope LIKE ?",
            (f"web-media-workspace:{account_id}:%",),
        ).fetchone()
        if int(receipt_count[0] or 0) >= MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT:
            return envelope(
                False,
                "Kho receipt thao tác tạm thời đang đầy. Vui lòng thử lại sau khi các receipt cũ hết hạn.",
                status_name="guarded",
                error_code="WEB_MEDIA_IDEMPOTENCY_LIMIT",
            )
        response = operation(conn)
        if response.get("ok") is True:
            receipt = _receipt_safe(response)
            if receipt.get("ok") is not True:
                raise HTTPException(status_code=409, detail="Không thể lưu receipt Audio Library an toàn")
            conn.execute(
                """INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (scope, key, json.dumps(receipt, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
            )
            # First success and a later replay must have the same safe
            # envelope.  The client re-hydrates the owner-scoped collection
            # when it needs content, rather than treating a mutation receipt
            # as another private content store.
            response = receipt
    return response


def _collection_row(conn: Any, *, collection_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, project_id, title, description, creative_brief, prompt_mode, use_context, tags_json,
                  rights_note, policy_marker, state, revision, created_at, updated_at, archived_at
           FROM web_media_collections WHERE id=? AND account_id=?""",
        (collection_id, account_id),
    ).fetchone()


def _collection_not_found() -> dict[str, Any]:
    return envelope(
        False,
        "Không tìm thấy collection thuộc Web account hiện tại.",
        status_name="guarded",
        error_code="WEB_MEDIA_COLLECTION_NOT_FOUND",
    )


def _collection_public(row: tuple[Any, ...], *, include_content: bool = False) -> dict[str, Any]:
    marker = str(row[9] or "")
    value = {
        "id": str(row[0]),
        "project_id": str(row[1]) if row[1] else None,
        "title": str(row[2]),
        "description_excerpt": _excerpt(row[3]),
        "brief_excerpt": _excerpt(row[4]),
        "prompt_mode": str(row[5]),
        "use_context": str(row[6]),
        "tags": _decode_tags(row[7]),
        "policy": {"status": "guarded" if marker else "clear", "marker": marker or None},
        "state": str(row[10]),
        "revision": int(row[11]),
        "created_at": str(row[12]),
        "updated_at": str(row[13]),
        "archived_at": str(row[14]) if row[14] else None,
        "execution": "authoring_only",
    }
    if include_content:
        value.update({
            "description": str(row[3]),
            "creative_brief": str(row[4]),
            "rights_note": str(row[8]),
        })
    return value


def _excerpt(value: Any, *, limit: int = 260) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= limit else f"{text[: max(1, limit - 1)].rstrip()}…"


def _snapshot_from_payload(payload: "CollectionPayload", *, state: str = "active", marker: str = "") -> dict[str, Any]:
    return {
        "title": payload.title,
        "description": payload.description,
        "creative_brief": payload.creative_brief,
        "prompt_mode": payload.prompt_mode,
        "use_context": payload.use_context,
        "tags": list(payload.tags),
        "rights_note": payload.rights_note,
        "project_id": payload.project_id or None,
        "policy_marker": marker,
        "state": state,
    }


def _snapshot_from_row(row: tuple[Any, ...], *, state: str | None = None) -> dict[str, Any]:
    return {
        "title": str(row[2]),
        "description": str(row[3]),
        "creative_brief": str(row[4]),
        "prompt_mode": str(row[5]),
        "use_context": str(row[6]),
        "tags": _decode_tags(row[7]),
        "rights_note": str(row[8]),
        "project_id": str(row[1]) if row[1] else None,
        "policy_marker": str(row[9] or ""),
        "state": state or str(row[10]),
    }


def _insert_version(conn: Any, *, collection_id: str, account_id: str, revision: int, snapshot: dict[str, Any], created_at: str) -> None:
    conn.execute(
        """INSERT INTO web_media_collection_versions
           (id, collection_id, account_id, revision, snapshot_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), collection_id, account_id, revision, json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), created_at),
    )


def _can_add_version(conn: Any, *, collection_id: str, account_id: str) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) FROM web_media_collection_versions WHERE collection_id=? AND account_id=?",
        (collection_id, account_id),
    ).fetchone()
    return int(row[0] or 0) < MAX_VERSIONS_PER_COLLECTION


def _version_limit() -> dict[str, Any]:
    return envelope(
        False,
        "Collection đã đạt giới hạn lịch sử phiên bản. Hãy archive collection cũ hoặc liên hệ hỗ trợ trước khi tiếp tục thay đổi metadata.",
        status_name="guarded",
        error_code="WEB_MEDIA_VERSION_LIMIT",
    )


def _event(conn: Any, *, account_id: str, collection_id: str, action: str, revision: int) -> None:
    conn.execute(
        """INSERT INTO web_media_events (id, account_id, collection_id, action, revision, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), account_id, collection_id, action, revision, utc_now()),
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


def _ensure_project_scope(conn: Any, *, project_id: str | None, account_id: str) -> None:
    if not project_id:
        return
    row = conn.execute(
        "SELECT id FROM web_projects WHERE id=? AND account_id=? AND state='active'",
        (project_id, account_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=422, detail="Project liên kết không hợp lệ hoặc không còn hoạt động")


def _is_audio_asset(extension: Any, content_type: Any) -> bool:
    normalized_extension = str(extension or "").strip().lower()
    normalized_type = str(content_type or "").strip().lower()
    return normalized_extension in AUDIO_EXTENSIONS and normalized_type in AUDIO_CONTENT_TYPES.get(normalized_extension, frozenset())


def _audio_asset_row(conn: Any, *, asset_id: str, account_id: str) -> tuple[Any, ...] | None:
    row = conn.execute(
        """SELECT id, project_id, display_name, original_filename, extension, content_type, byte_size,
                  state, created_at, updated_at, archived_at
           FROM web_asset_files WHERE id=? AND account_id=?""",
        (asset_id, account_id),
    ).fetchone()
    if not row or str(row[7]) != "active" or not _is_audio_asset(row[4], row[5]):
        return None
    return row


def _audio_asset_public(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "project_id": str(row[1]) if row[1] else None,
        "display_name": str(row[2]),
        "original_filename": str(row[3]),
        "extension": str(row[4]),
        "content_type": str(row[5]),
        "byte_size": int(row[6]),
        "state": str(row[7]),
        "created_at": str(row[8]),
        "updated_at": str(row[9]),
        "archived_at": str(row[10]) if row[10] else None,
        # Existing Asset Vault download remains the only private delivery
        # route.  This module deliberately never emits a storage path/URL.
        "download_available": str(row[7]) == "active",
    }


def _audio_asset_not_found() -> dict[str, Any]:
    return envelope(
        False,
        "Chỉ tệp audio active thuộc Asset Vault của bạn mới có thể được gắn vào collection.",
        status_name="guarded",
        error_code="WEB_MEDIA_AUDIO_ASSET_NOT_FOUND",
    )


def _item_public(row: tuple[Any, ...]) -> dict[str, Any]:
    # Fields 0-8 belong to the Web-native relation. Fields 9+ are a strictly
    # projected Asset Vault row; no storage key, digest or private path joins.
    asset_available = bool(row[9]) and str(row[16] or "") == "active" and _is_audio_asset(row[13], row[14])
    asset = None
    if row[9]:
        asset = {
            "id": str(row[9]),
            "project_id": str(row[10]) if row[10] else None,
            "display_name": str(row[11] or ""),
            "original_filename": str(row[12] or ""),
            "extension": str(row[13] or ""),
            "content_type": str(row[14] or ""),
            "byte_size": int(row[15] or 0),
            "state": str(row[16] or "unavailable"),
            "download_available": asset_available,
        }
    return {
        "id": str(row[0]),
        "asset_id": str(row[1]),
        "role": str(row[2]),
        "title_override": str(row[3]),
        "attribution": str(row[4]),
        "license_note": str(row[5]),
        "tags": _decode_tags(row[6]),
        "favorite": bool(row[7]),
        "user_declared_duration_seconds": int(row[8]) if row[8] is not None else None,
        "created_at": str(row[17]),
        "updated_at": str(row[18]),
        "asset": asset,
        "delivery": "asset_vault_attachment_only" if asset_available else "guarded",
    }


def _collection_detail(conn: Any, *, collection_id: str, account_id: str) -> dict[str, Any] | None:
    collection = _collection_row(conn, collection_id=collection_id, account_id=account_id)
    if not collection:
        return None
    versions = conn.execute(
        """SELECT revision, snapshot_json, created_at
           FROM web_media_collection_versions WHERE collection_id=? AND account_id=?
           ORDER BY revision DESC LIMIT 100""",
        (collection_id, account_id),
    ).fetchall()
    items = conn.execute(
        """SELECT i.id, i.asset_id, i.role, i.title_override, i.attribution, i.license_note, i.tags_json,
                  i.favorite, i.user_declared_duration_seconds,
                  a.id, a.project_id, a.display_name, a.original_filename, a.extension, a.content_type,
                  a.byte_size, a.state, i.created_at, i.updated_at
           FROM web_media_items AS i
           LEFT JOIN web_asset_files AS a ON a.id=i.asset_id AND a.account_id=i.account_id
           WHERE i.collection_id=? AND i.account_id=?
           ORDER BY i.favorite DESC, i.updated_at DESC, i.id DESC LIMIT ?""",
        (collection_id, account_id, MAX_ITEMS_PER_COLLECTION),
    ).fetchall()
    public_versions: list[dict[str, Any]] = []
    for row in versions:
        try:
            snapshot = json.loads(str(row[1] or "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            snapshot = {}
        if not isinstance(snapshot, dict):
            snapshot = {}
        public_versions.append({
            "revision": int(row[0]),
            "title": str(snapshot.get("title") or "Collection"),
            "prompt_mode": str(snapshot.get("prompt_mode") or "background"),
            "state": str(snapshot.get("state") or "active"),
            "tags": _decode_tags(json.dumps(snapshot.get("tags") if isinstance(snapshot.get("tags"), list) else [])),
            "brief_excerpt": _excerpt(snapshot.get("creative_brief")),
            "created_at": str(row[2]),
        })
    return {
        "collection": _collection_public(collection, include_content=True),
        "versions": public_versions,
        "items": [_item_public(row) for row in items],
        "item_limit": MAX_ITEMS_PER_COLLECTION,
        "item_count": len(items),
    }


def _summary_data(conn: Any, *, account_id: str) -> dict[str, Any]:
    state_rows = conn.execute(
        "SELECT state, COUNT(*) FROM web_media_collections WHERE account_id=? GROUP BY state",
        (account_id,),
    ).fetchall()
    states = {str(state): int(count) for state, count in state_rows}
    item_rows = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(CASE WHEN favorite=1 THEN 1 ELSE 0 END), 0) FROM web_media_items WHERE account_id=?",
        (account_id,),
    ).fetchone()
    latest = conn.execute(
        "SELECT updated_at FROM web_media_collections WHERE account_id=? ORDER BY updated_at DESC, id DESC LIMIT 1",
        (account_id,),
    ).fetchone()
    return {
        "collections": {
            "active": states.get("active", 0),
            "archived": states.get("archived", 0),
            "total": sum(states.values()),
            "limit_per_state": MAX_COLLECTIONS_PER_STATE,
        },
        "items": {
            "total": int(item_rows[0] or 0) if item_rows else 0,
            "favorites": int(item_rows[1] or 0) if item_rows else 0,
            "account_limit": MAX_ITEMS_PER_ACCOUNT,
            "collection_limit": MAX_ITEMS_PER_COLLECTION,
        },
        "latest_updated_at": str(latest[0]) if latest and latest[0] else None,
        "execution": {
            "authoring": "ready",
            "provider_library": "guarded",
            "generation": "guarded",
            "delivery": "asset_vault_attachment_only",
        },
    }


class CollectionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=MAX_TITLE)
    description: str = Field(default="", max_length=MAX_DESCRIPTION)
    creative_brief: str = Field(default="", max_length=MAX_BRIEF)
    prompt_mode: str = Field(default="background", max_length=24)
    use_context: str = Field(default="general", max_length=MAX_CONTEXT)
    tags: list[str] = Field(default_factory=list, max_length=MAX_TAGS)
    rights_note: str = Field(default="Tôi xác nhận có quyền sử dụng các tệp và brief trong collection này.", min_length=2, max_length=MAX_RIGHTS_NOTE)
    project_id: str = Field(default="", max_length=64)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _single_line(value, label="Tên collection", minimum=3, maximum=MAX_TITLE)

    @field_validator("description", "creative_brief")
    @classmethod
    def validate_content(cls, value: str, info: Any) -> str:
        label = "Mô tả" if str(info.field_name) == "description" else "Music brief"
        return _content(value, label=label, maximum=MAX_DESCRIPTION if label == "Mô tả" else MAX_BRIEF, allow_empty=True)

    @field_validator("use_context")
    @classmethod
    def validate_context(cls, value: str) -> str:
        return _single_line(value, label="Ngữ cảnh sử dụng", minimum=0, maximum=MAX_CONTEXT, allow_empty=True) or "general"

    @field_validator("prompt_mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        mode = _single_line(value, label="Chế độ brief", minimum=3, maximum=24).lower()
        if mode not in PROMPT_MODES:
            raise ValueError("Chế độ brief không hợp lệ")
        return mode

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        return _tags(value)

    @field_validator("rights_note")
    @classmethod
    def validate_rights_note(cls, value: str) -> str:
        return _single_line(value, label="Ghi chú quyền sử dụng", minimum=2, maximum=MAX_RIGHTS_NOTE)

    @field_validator("project_id")
    @classmethod
    def validate_project_id(cls, value: str) -> str:
        return _optional_uuid(value, label="Project ID") or ""


class CollectionCreateRequest(CollectionPayload):
    idempotency_key: str = Field(min_length=12, max_length=160)


class CollectionUpdateRequest(CollectionPayload):
    expected_revision: int = Field(ge=1, le=1_000_000)
    idempotency_key: str = Field(min_length=12, max_length=160)


class RevisionMutationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1, le=1_000_000)
    idempotency_key: str = Field(min_length=12, max_length=160)


class DuplicateRequest(RevisionMutationRequest):
    title: str = Field(default="", max_length=MAX_TITLE)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _single_line(value, label="Tên bản sao", minimum=0, maximum=MAX_TITLE, allow_empty=True)


class RestoreVersionRequest(RevisionMutationRequest):
    revision: int = Field(ge=1, le=1_000_000)


class ComposeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1, le=1_000_000)


class MediaItemPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(default="music", max_length=24)
    title_override: str = Field(default="", max_length=MAX_ITEM_LABEL)
    attribution: str = Field(default="", max_length=MAX_ATTRIBUTION)
    license_note: str = Field(default="Tôi chịu trách nhiệm kiểm tra license và quyền thương mại trước khi đăng.", min_length=2, max_length=MAX_RIGHTS_NOTE)
    tags: list[str] = Field(default_factory=list, max_length=MAX_TAGS)
    favorite: bool = False
    user_declared_duration_seconds: int | None = Field(default=None, ge=1, le=MAX_DECLARED_DURATION_SECONDS)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        role = _single_line(value, label="Vai trò audio", minimum=3, maximum=24).lower()
        if role not in ITEM_ROLES:
            raise ValueError("Vai trò audio không hợp lệ")
        return role

    @field_validator("title_override", "attribution")
    @classmethod
    def validate_item_single_line(cls, value: str, info: Any) -> str:
        maximum = MAX_ITEM_LABEL if str(info.field_name) == "title_override" else MAX_ATTRIBUTION
        label = "Tên hiển thị" if str(info.field_name) == "title_override" else "Attribution"
        return _single_line(value, label=label, minimum=0, maximum=maximum, allow_empty=True)

    @field_validator("license_note")
    @classmethod
    def validate_license_note(cls, value: str) -> str:
        return _single_line(value, label="Ghi chú license", minimum=2, maximum=MAX_RIGHTS_NOTE)

    @field_validator("tags")
    @classmethod
    def validate_item_tags(cls, value: list[str]) -> list[str]:
        return _tags(value)


class AttachMediaItemRequest(MediaItemPayload):
    asset_id: str = Field(min_length=36, max_length=64)
    expected_revision: int = Field(ge=1, le=1_000_000)
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("asset_id")
    @classmethod
    def validate_asset_id(cls, value: str) -> str:
        return _uuid(value, label="Asset Vault ID")


class UpdateMediaItemRequest(MediaItemPayload):
    expected_revision: int = Field(ge=1, le=1_000_000)
    idempotency_key: str = Field(min_length=12, max_length=160)


class DetachMediaItemRequest(RevisionMutationRequest):
    confirm: bool

    @field_validator("confirm")
    @classmethod
    def validate_confirm(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("Cần xác nhận gỡ audio khỏi collection")
        return value


def _policy_guard(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    marker = str(snapshot.get("policy_marker") or "")
    if not marker:
        return None
    return envelope(
        False,
        "Music brief có dấu hiệu yêu cầu mô phỏng nghệ sĩ/bài hát/giọng. Hãy mô tả mood, tempo, nhạc cụ, bối cảnh và cảm xúc thay vì nêu tác phẩm hoặc nghệ sĩ cụ thể.",
        data={"policy": {"status": "guarded", "marker": marker}, "execution": "not_started"},
        status_name="guarded",
        error_code="WEB_MEDIA_COPYRIGHT_GUARD",
    )


def _payload_policy_marker(payload: CollectionPayload) -> str:
    return _copyright_marker(payload.title, payload.description, payload.creative_brief, payload.use_context)


def _insert_collection(conn: Any, *, collection_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str) -> None:
    conn.execute(
        """INSERT INTO web_media_collections
           (id, account_id, project_id, title, description, creative_brief, prompt_mode, use_context, tags_json,
            rights_note, policy_marker, state, revision, created_at, updated_at, archived_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)""",
        (
            collection_id, account_id, snapshot.get("project_id"), snapshot["title"], snapshot["description"],
            snapshot["creative_brief"], snapshot["prompt_mode"], snapshot["use_context"],
            json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")), snapshot["rights_note"],
            snapshot.get("policy_marker") or "", snapshot["state"], revision, now, now,
        ),
    )


def _write_collection_update(conn: Any, *, collection_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str, archived_at: str | None) -> None:
    conn.execute(
        """UPDATE web_media_collections
           SET project_id=?, title=?, description=?, creative_brief=?, prompt_mode=?, use_context=?, tags_json=?,
               rights_note=?, policy_marker=?, state=?, revision=?, updated_at=?, archived_at=?
           WHERE id=? AND account_id=?""",
        (
            snapshot.get("project_id"), snapshot["title"], snapshot["description"], snapshot["creative_brief"],
            snapshot["prompt_mode"], snapshot["use_context"], json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")),
            snapshot["rights_note"], snapshot.get("policy_marker") or "", snapshot["state"], revision, now,
            archived_at, collection_id, account_id,
        ),
    )


def _revision_conflict() -> dict[str, Any]:
    return envelope(
        False,
        "Collection đã thay đổi ở phiên khác. Hãy làm mới trước khi tiếp tục.",
        status_name="guarded",
        error_code="WEB_MEDIA_REVISION_CONFLICT",
    )


def _composer_directions(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    """Build deterministic brief directions only; this never creates audio."""
    brief = re.sub(r"\s+", " ", str(snapshot.get("creative_brief") or "")).strip()
    context = re.sub(r"\s+", " ", str(snapshot.get("use_context") or "general")).strip() or "general"
    mode = str(snapshot.get("prompt_mode") or "background")
    mode_label = {
        "background": "nhạc nền không lời", "lyrics": "bài hát có lời nguyên gốc", "script": "hướng lời/kịch bản nhạc",
        "melody": "hướng giai điệu nguyên gốc", "custom": "brief âm nhạc tùy chỉnh",
    }.get(mode, "brief âm nhạc")
    base = brief or "nội dung sáng tạo của collection này"
    directions = (
        ("Hướng 01 · rõ mục tiêu", "Cân bằng, dễ dùng cho sản phẩm/nội dung", "clean, balanced, voice-over friendly"),
        ("Hướng 02 · nhịp nổi bật", "Tập trung hook, nhịp và điểm nhớ", "confident hook, focused rhythm, concise structure"),
        ("Hướng 03 · cảm xúc riêng", "Tạo khoảng thở và dấu ấn thẩm mỹ", "textural, spacious, distinctive emotional arc"),
    )
    output: list[dict[str, str]] = []
    for title, intent, texture in directions:
        prompt = (
            f"Original {mode_label} for {context}. Brief: {base}. "
            f"Direction: {texture}. Describe mood, tempo, instrumentation, duration and scene fit. "
            "Use an original composition; do not imitate a named artist, song, melody or voice."
        )
        output.append({"title": title, "intent": intent, "prompt": prompt[:2_400]})
    return output


def _music_prompt_composer_line(
    value: Any,
    *,
    label: str,
    minimum: int,
    maximum: int,
    allow_empty: bool = False,
) -> str:
    """Validate one transient music-plan field without widening collections.

    Durable Media Workspace collections intentionally support a broader owned
    authoring surface.  This request/response-only composer cannot accept
    markup, source media, opaque handles, secrets or payment artefacts because
    it must never become an implicit provider or delivery interface.
    """

    text = _single_line(value, label=label, minimum=minimum, maximum=maximum, allow_empty=allow_empty)
    if text and (
        MUSIC_PROMPT_COMPOSER_MARKUP_PATTERN.search(text)
        or MUSIC_PROMPT_COMPOSER_URL_OR_FILE_PATTERN.search(text)
        or MUSIC_PROMPT_COMPOSER_HANDLE_PATTERN.search(text)
    ):
        raise ValueError(f"{label} không nhận markup, URL/file, handle hoặc mã/tham chiếu hệ thống ngoài")
    return text


def _music_prompt_composer_code(value: Any, *, label: str, allowed: frozenset[str] | set[str]) -> str:
    raw = _music_prompt_composer_line(value, label=label, minimum=1, maximum=64)
    normalized = raw.lower()
    # Codes are part of the public API contract, so accepting an implicit
    # case-folded alias would make the strict client/server schema ambiguous.
    if raw != normalized or normalized not in allowed:
        raise ValueError(f"{label} không hợp lệ")
    return normalized


def _music_prompt_composer_output_line(
    value: Any,
    *,
    label: str,
    minimum: int = 2,
    maximum: int = MUSIC_PROMPT_COMPOSER_MAX_TEXT,
) -> str:
    """Revalidate local deterministic response text before rendering it."""

    return _music_prompt_composer_line(value, label=label, minimum=minimum, maximum=maximum)


def _music_prompt_composer_marker(*parts: Any) -> str:
    """Return a narrow copyright/originality guard marker, if present.

    This does not perform rights clearance.  It only prevents the static
    suggestion catalog from turning a request to imitate a song, artist,
    singer, beat, melody or vocal identity into a generic workaround prompt.
    """

    normalized = re.sub(r"\s+", " ", " ".join(str(part or "") for part in parts)).strip().casefold()[:12_000]
    for marker in MUSIC_PROMPT_COMPOSER_COPYRIGHT_MARKERS:
        if marker in normalized:
            return marker
    return ""


def _music_prompt_composer_boundary() -> dict[str, Any]:
    """Return the exact no-execution boundary for this planning receipt."""

    return {
        "execution": "web_native_deterministic_music_prompt_only",
        "input_persisted": False,
        "source_audio_inspected": False,
        "provider_called": False,
        "ai_music_called": False,
        "lyrics_generated": False,
        "audio_created": False,
        "preview_created": False,
        "output_created": False,
        "job_created": False,
        "wallet_mutated": False,
        "payment_started": False,
        "asset_saved": False,
        "collection_saved": False,
        "publish_action_created": False,
        "telegram_called": False,
        "rights_verified": False,
    }


def _music_prompt_composer_guard(marker: str) -> dict[str, Any] | None:
    if not marker:
        return None
    return envelope(
        False,
        "Mô tả cần được viết lại theo hướng nguyên bản, không mô phỏng nghệ sĩ, ca sĩ, bài hát, beat, giai điệu hoặc giọng cụ thể.",
        data=_music_prompt_composer_boundary(),
        status_name="guarded",
        error_code="WEB_MUSIC_PROMPT_COPYRIGHT_GUARD",
    )


def _music_prompt_composer_excerpt(value: Any, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= limit else f"{text[: max(1, limit - 1)].rstrip()}…"


def _music_prompt_composer_catalog(mode: str, language: str) -> list[dict[str, str]]:
    """Return six local Bot-inspired directions for first/next-three rotation."""

    catalog_mode = "lyrics" if mode in {"lyrics", "script"} else "melody" if mode == "melody" else "background"
    if catalog_mode == "lyrics":
        vi_rows = [
            ("Pop hook bán hàng", "tươi, dễ nhớ, có năng lượng mua hàng", "105-125 BPM", "pop drums, clean bass, synth hook, clap nhẹ", "30-45s", "vocal rõ hook, không mô phỏng nghệ sĩ", "Hook một câu, verse nêu vấn đề, chorus nhắc lợi ích, CTA nhẹ.", "TikTok/Reels quảng cáo sản phẩm, affiliate, launch offer"),
            ("Storytelling acoustic", "ấm, chân thật, kể chuyện", "75-95 BPM", "acoustic guitar, piano pad, soft percussion", "45-60s", "vocal tự nhiên, cảm xúc nhẹ", "Mở bằng tình huống đời thường, chuyển sang giải pháp, kết bằng câu nhớ thương hiệu.", "Brand story, UGC cảm xúc, before/after"),
            ("Jingle thương hiệu ngắn", "sáng, gọn, dễ thuộc", "115-130 BPM", "pluck, bell, light beat, simple bass", "18-25s", "vocal hook ngắn, giai điệu nguyên bản", "Tên sản phẩm, lợi ích chính và nhịp slogan ngắn; không bịa claim.", "Intro/outro quảng cáo, brand recall, shop nhỏ"),
            ("Luxury vocal nhẹ", "sang, tiết chế, cảm xúc nhẹ", "70-88 BPM", "felt piano, cinematic pad, soft strings", "30-50s", "vocal premium nhẹ, ít lời", "Ít lời, nhiều khoảng nghỉ, nhấn cảm xúc và hình ảnh thương hiệu.", "Nước hoa, mỹ phẩm, thời trang, cinematic ad"),
            ("Viral chant ngắn", "bắt tai, nhanh, nhớ ngay", "125-145 BPM", "short drums, punchy bass, original vocal texture", "10-20s", "chant ngắn, phrase nguyên bản", "Một câu hook lặp lại có kiểm soát, câu sau là lợi ích đã review hoặc CTA mềm.", "Shorts/Reels, video bán hàng nhanh"),
            ("Corporate anthem mini", "tin cậy, tích cực, chuyên nghiệp", "90-110 BPM", "piano, light drums, warm pad, clean guitar", "45-60s", "vocal truyền cảm hứng, nguyên bản", "Tầm nhìn, niềm tin và lời mời hợp tác; không hứa hẹn tuyệt đối.", "SaaS, doanh nghiệp, video giới thiệu dịch vụ"),
        ]
        en_rows = [
            ("Sales pop hook", "bright, memorable, purchase-oriented", "105-125 BPM", "pop drums, clean bass, synth hook, light claps", "30-45s", "clear hook vocal, no artist imitation", "One-line hook, problem verse, benefit chorus, gentle CTA.", "TikTok/Reels product ads, affiliate, launch offer"),
            ("Storytelling acoustic", "warm, grounded, narrative", "75-95 BPM", "acoustic guitar, piano pad, soft percussion", "45-60s", "natural vocal with gentle emotion", "Open on an everyday situation, move to a solution, end with a brand-memory line.", "Brand story, emotional UGC, before/after"),
            ("Short brand jingle", "bright, concise, easy to recall", "115-130 BPM", "pluck, bell, light beat, simple bass", "18-25s", "short vocal hook, original melody", "Product name, reviewed benefit, and a short slogan rhythm; no invented claim.", "Ad intro/outro, brand recall, small shops"),
            ("Light luxury vocal", "premium, restrained, softly emotional", "70-88 BPM", "felt piano, cinematic pad, soft strings", "30-50s", "minimal premium vocal", "Few words, more breathing room, emphasize emotion and brand imagery.", "Fragrance, cosmetics, fashion, cinematic ads"),
            ("Short viral chant", "catchy, quick, immediately memorable", "125-145 BPM", "short drums, punchy bass, original vocal texture", "10-20s", "short original chant", "Use one controlled repeated hook, then a reviewed benefit or gentle CTA.", "Shorts/Reels, fast sales video"),
            ("Mini corporate anthem", "trustworthy, positive, professional", "90-110 BPM", "piano, light drums, warm pad, clean guitar", "45-60s", "original inspirational vocal", "Vision, trust, and an invitation to collaborate; no absolute promise.", "SaaS, companies, service introduction video"),
        ]
    elif catalog_mode == "melody":
        vi_rows = [
            ("Motif 3 nốt dễ nhớ", "sáng, gọn, có nhận diện", "100-118 BPM", "piano pluck, bell, soft synth", "10-20s", "không vocal hoặc hum placeholder nhẹ", "Không lời; giữ motif nguyên bản ba nốt, không dựa vào giai điệu có sẵn.", "Logo sound, intro ngắn, brand cue"),
            ("Cinematic rise", "tăng dần, cảm xúc, mở rộng", "75-90 BPM", "strings, piano, airy pad, low hit", "20-40s", "không vocal", "Không lời; phát triển motif nguyên bản từ chi tiết nhỏ sang reveal.", "Reveal sản phẩm, before/after, ad premium"),
            ("Clean tech pulse", "hiện đại, sạch, tự động hóa", "105-124 BPM", "digital pulse, minimal synth, soft kick", "18-30s", "không vocal", "Không lời; nhịp motif sạch, chừa khoảng cho voice-over.", "AI tool, app, dashboard, tutorial"),
            ("Warm acoustic motif", "ấm, gần gũi, tin cậy", "78-96 BPM", "acoustic guitar, piano, brushed percussion", "20-45s", "không vocal", "Không lời; motif mộc nguyên bản, ưu tiên mạch kể chuyện nhẹ.", "Review, storytelling, gia đình/cảm xúc"),
            ("Viral loop", "ngắn, bắt nhịp, dễ loop", "128-140 BPM", "snappy drums, bass stab, synth lead", "8-18s", "không vocal", "Không lời; loop nguyên bản gọn, không tái tạo hook nhận diện.", "Hook đầu video, UGC, reels ngắn"),
            ("Luxury minimal", "tĩnh, cao cấp, ít nốt", "62-82 BPM", "felt piano, deep pad, subtle texture", "20-35s", "không vocal", "Không lời; tối giản khoảng nghỉ và texture nguyên bản.", "Nước hoa, mỹ phẩm, fashion, hero shot"),
        ]
        en_rows = [
            ("Memorable three-note motif", "bright, concise, identifiable", "100-118 BPM", "piano pluck, bell, soft synth", "10-20s", "no vocal or a light placeholder hum", "Instrumental only; keep an original three-note motif with no borrowed melody.", "Logo sound, short intro, brand cue"),
            ("Cinematic rise", "expanding, emotional, gradual", "75-90 BPM", "strings, piano, airy pad, low hit", "20-40s", "no vocal", "Instrumental only; grow an original motif from a small detail into a reveal.", "Product reveal, before/after, premium ad"),
            ("Clean tech pulse", "modern, clean, automated", "105-124 BPM", "digital pulse, minimal synth, soft kick", "18-30s", "no vocal", "Instrumental only; use a clean original pulse with room for voice-over.", "AI tool, app, dashboard, tutorial"),
            ("Warm acoustic motif", "warm, relatable, trustworthy", "78-96 BPM", "acoustic guitar, piano, brushed percussion", "20-45s", "no vocal", "Instrumental only; use an original acoustic motif and gentle story flow.", "Review, storytelling, family/emotion"),
            ("Viral loop", "short, rhythmic, loop-friendly", "128-140 BPM", "snappy drums, bass stab, synth lead", "8-18s", "no vocal", "Instrumental only; keep an original concise loop without recreating a recognizable hook.", "Opening hook, UGC, short reels"),
            ("Luxury minimal", "calm, premium, sparse", "62-82 BPM", "felt piano, deep pad, subtle texture", "20-35s", "no vocal", "Instrumental only; use sparse pauses and original texture.", "Fragrance, cosmetics, fashion, hero shot"),
        ]
    else:
        vi_rows = [
            ("Vui tươi / bán hàng", "sáng, tích cực, tạo cảm giác dễ mua", "110-125 BPM", "light drums, soft synth, pluck, clap nhẹ", "18-30s", "không vocal", "Không lời; ưu tiên nhạc nền gọn để voice và CTA rõ.", "TikTok/Reels/Shorts, review sản phẩm, CTA rõ"),
            ("Cinematic / cao cấp", "sang, cảm xúc vừa phải, thương hiệu", "80-95 BPM", "piano, soft strings, ambient pad, sub bass nhẹ", "30-60s", "không vocal", "Không lời; giữ không gian cảm xúc và không lấn lời đọc.", "Quảng cáo premium, key visual, reveal sản phẩm"),
            ("Nhẹ nhàng / cảm xúc", "ấm, tin cậy, kể chuyện", "70-90 BPM", "acoustic guitar, piano nhẹ, pad mềm", "30-45s", "không vocal", "Không lời; giữ câu nhạc đơn giản để kể chuyện tự nhiên.", "Voice-over, review chân thật, before/after"),
            ("Công nghệ / tương lai", "sạch, hiện đại, tự động hóa", "100-118 BPM", "minimal synth, digital pulse, clean percussion", "18-30s", "không vocal", "Không lời; nhịp sạch, không che thao tác hoặc voice-over.", "AI tool, SaaS, dashboard, automation"),
            ("Viral short / bắt tai", "nhanh, bắt nhịp, trẻ trung", "125-140 BPM", "snappy drums, bass ngắn, hook synth nguyên bản", "10-20s", "không vocal", "Không lời; hook nhạc nguyên bản ngắn, tránh motif nhận diện.", "Hook đầu video, trend, UGC ngắn"),
            ("Luxury tối giản", "tĩnh, cao cấp, ít chi tiết", "65-85 BPM", "felt piano, deep pad, soft ticks", "20-40s", "không vocal", "Không lời; khoảng nghỉ tối giản, ưu tiên hình ảnh và sản phẩm.", "Nước hoa, mỹ phẩm, thời trang, brand ad"),
        ]
        en_rows = [
            ("Bright sales", "bright, positive, purchase-friendly", "110-125 BPM", "light drums, soft synth, pluck, light claps", "18-30s", "no vocal", "Instrumental only; keep the bed concise so voice and CTA remain clear.", "TikTok/Reels/Shorts, product review, clear CTA"),
            ("Cinematic premium", "premium, moderately emotional, brand-led", "80-95 BPM", "piano, soft strings, ambient pad, light sub bass", "30-60s", "no vocal", "Instrumental only; retain emotional space without overtaking narration.", "Premium ad, key visual, product reveal"),
            ("Warm emotional", "warm, trustworthy, narrative", "70-90 BPM", "acoustic guitar, light piano, soft pad", "30-45s", "no vocal", "Instrumental only; keep a simple phrase for natural storytelling.", "Voice-over, honest review, before/after"),
            ("Technology future", "clean, modern, automated", "100-118 BPM", "minimal synth, digital pulse, clean percussion", "18-30s", "no vocal", "Instrumental only; use a clean pulse that does not mask actions or narration.", "AI tool, SaaS, dashboard, automation"),
            ("Viral short", "quick, rhythmic, youthful", "125-140 BPM", "snappy drums, short bass, original synth hook", "10-20s", "no vocal", "Instrumental only; use a short original hook and avoid a recognizable motif.", "Opening hook, trend, short UGC"),
            ("Minimal luxury", "calm, premium, sparse", "65-85 BPM", "felt piano, deep pad, soft ticks", "20-40s", "no vocal", "Instrumental only; use minimal rests and prioritize imagery and product detail.", "Fragrance, cosmetics, fashion, brand ad"),
        ]
    rows = vi_rows if language == "vi" else en_rows
    return [
        {
            "name": name,
            "mood": mood,
            "tempo": tempo,
            "instruments": instruments,
            "duration": duration,
            "vocal": vocal,
            "lyric_direction": lyric_direction,
            "use_case": use_case,
        }
        for name, mood, tempo, instruments, duration, vocal, lyric_direction, use_case in rows
    ]


class MusicPromptComposerRequest(BaseModel):
    """Strict input for the Bot-derived, non-persistent music prompt tool."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    description: StrictStr
    mode: StrictStr
    language: StrictStr
    suggestion_set: StrictStr
    selected_suggestion: StrictInt = Field(ge=1, le=3)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: StrictStr) -> str:
        return _music_prompt_composer_line(
            value,
            label="Mô tả nhạc",
            minimum=2,
            maximum=MUSIC_PROMPT_COMPOSER_MAX_DESCRIPTION,
        )

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value: StrictStr) -> str:
        return _music_prompt_composer_code(value, label="Chế độ prompt nhạc", allowed=MUSIC_PROMPT_COMPOSER_MODES)

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: StrictStr) -> str:
        return _music_prompt_composer_code(value, label="Ngôn ngữ", allowed=MUSIC_PROMPT_COMPOSER_LANGUAGES)

    @field_validator("suggestion_set")
    @classmethod
    def validate_suggestion_set(cls, value: StrictStr) -> str:
        return _music_prompt_composer_code(value, label="Nhóm gợi ý", allowed=MUSIC_PROMPT_COMPOSER_SETS)


def _require_memory_handoff_enabled() -> None:
    """Require the Web-owned Memory capability for an explicit durable save.

    The stateless Composer remains usable while Memory Center is under
    maintenance. The separate save route must not bypass that maintenance
    switch or create a second note store in Media Workspace.
    """

    if not memory_center_enabled():
        raise HTTPException(
            status_code=503,
            detail="Memory Center đang tạm dừng để bảo trì. WEBAPP_MEMORY_CENTER_ENABLED chưa được bật.",
        )


class MusicPromptComposerMemorySaveRequest(MusicPromptComposerRequest):
    """Narrow, explicit save of one reviewed deterministic direction.

    The browser supplies only the original bounded Composer inputs plus its
    confirmation destination and idempotency key. It cannot send a generated
    prompt/body/title, select another account, attach an audio asset, or point
    this route at a Telegram pending record.
    """

    destination: StrictStr
    idempotency_key: StrictStr

    @field_validator("destination")
    @classmethod
    def validate_destination(cls, value: StrictStr) -> str:
        if _music_prompt_composer_line(value, label="Đích lưu", minimum=1, maximum=32).lower() != "memory_note":
            raise ValueError("Music Prompt Composer hiện chỉ hỗ trợ lưu vào Memory Center")
        return "memory_note"

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: StrictStr) -> str:
        return _idempotency_key(value)


class MusicPromptComposerSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    choice: StrictInt = Field(ge=1, le=3)
    name: StrictStr
    mood: StrictStr
    tempo: StrictStr
    instruments: StrictStr
    duration: StrictStr
    vocal: StrictStr
    lyric_direction: StrictStr
    use_case: StrictStr
    prompt: StrictStr

    @field_validator("name", "mood", "tempo", "instruments", "duration", "vocal", "lyric_direction", "use_case", "prompt")
    @classmethod
    def validate_text(cls, value: StrictStr) -> str:
        return _music_prompt_composer_output_line(value, label="Nội dung hướng nhạc")


class MusicPromptComposerUsageNotes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    voice_mix_notes: StrictStr
    edit_notes: StrictStr
    rights_notes: StrictStr
    delivery_notes: StrictStr

    @field_validator("voice_mix_notes", "edit_notes", "rights_notes", "delivery_notes")
    @classmethod
    def validate_notes(cls, value: StrictStr) -> str:
        return _music_prompt_composer_output_line(value, label="Ghi chú dùng prompt nhạc")


class MusicPromptComposerResult(BaseModel):
    """Exact browser schema for a deterministic, copy-only music receipt."""

    model_config = ConfigDict(extra="forbid")

    title: StrictStr
    description: StrictStr
    mode: StrictStr
    language: StrictStr
    suggestion_set: StrictStr
    selected_suggestion: StrictInt = Field(ge=1, le=3)
    suggestions: list[MusicPromptComposerSuggestion] = Field(min_length=3, max_length=3)
    selected_direction: MusicPromptComposerSuggestion
    usage_notes: MusicPromptComposerUsageNotes
    cautions: list[StrictStr] = Field(default_factory=list, max_length=6)
    review_before_use: list[StrictStr] = Field(min_length=1, max_length=6)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: StrictStr) -> str:
        return _music_prompt_composer_output_line(value, label="Tiêu đề prompt nhạc", maximum=180)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: StrictStr) -> str:
        return _music_prompt_composer_output_line(
            value,
            label="Mô tả prompt nhạc kết quả",
            maximum=MUSIC_PROMPT_COMPOSER_MAX_DESCRIPTION,
        )

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value: StrictStr) -> str:
        return _music_prompt_composer_code(value, label="Chế độ prompt nhạc kết quả", allowed=MUSIC_PROMPT_COMPOSER_MODES)

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: StrictStr) -> str:
        return _music_prompt_composer_code(value, label="Ngôn ngữ kết quả", allowed=MUSIC_PROMPT_COMPOSER_LANGUAGES)

    @field_validator("suggestion_set")
    @classmethod
    def validate_suggestion_set(cls, value: StrictStr) -> str:
        return _music_prompt_composer_code(value, label="Nhóm gợi ý kết quả", allowed=MUSIC_PROMPT_COMPOSER_SETS)

    @field_validator("cautions", "review_before_use")
    @classmethod
    def validate_lists(cls, value: list[StrictStr], info: Any) -> list[str]:
        if not isinstance(value, list):
            raise ValueError("Danh sách review prompt nhạc không hợp lệ")
        label = "Lưu ý prompt nhạc" if info.field_name == "cautions" else "Checklist review prompt nhạc"
        return [_music_prompt_composer_output_line(item, label=label) for item in value]

    def model_post_init(self, __context: Any) -> None:
        if [item.choice for item in self.suggestions] != [1, 2, 3]:
            raise ValueError("Suggestions phải có đúng ba lựa chọn theo thứ tự")
        if self.selected_direction.model_dump() != self.suggestions[self.selected_suggestion - 1].model_dump():
            raise ValueError("Selected direction phải khớp selected suggestion")


def _music_prompt_composer_suggestions(payload: MusicPromptComposerRequest) -> list[dict[str, Any]]:
    catalog = _music_prompt_composer_catalog(payload.mode, payload.language)
    offset = 0 if payload.suggestion_set == "primary" else 3
    selected = catalog[offset:offset + 3]
    description = _music_prompt_composer_excerpt(payload.description, 180)
    result: list[dict[str, Any]] = []
    for choice, item in enumerate(selected, start=1):
        if payload.language == "vi":
            prompt = (
                f"Hướng nhạc nguyên bản để biên tập, không tạo audio: {item['name']} cho {description}; "
                f"mood {item['mood']}; tempo {item['tempo']}; nhạc cụ {item['instruments']}; "
                f"thời lượng {item['duration']}; vocal {item['vocal']}; hướng lời {item['lyric_direction']}; "
                "không mô phỏng nghệ sĩ, bài hát, giai điệu, beat hoặc giọng cụ thể."
            )
        else:
            prompt = (
                f"Original editorial music direction only, no audio creation: {item['name']} for {description}; "
                f"mood {item['mood']}; tempo {item['tempo']}; instruments {item['instruments']}; "
                f"duration {item['duration']}; vocal {item['vocal']}; lyric direction {item['lyric_direction']}; "
                "do not imitate a named artist, song, melody, beat, or voice."
            )
        result.append({"choice": choice, **item, "prompt": prompt})
    return result


def _music_prompt_composer_usage_notes(*, language: str, mode: str) -> dict[str, str]:
    if language == "vi":
        return {
            "voice_mix_notes": "Giữ nhạc thấp hơn lời đọc và chừa khoảng nghỉ; đây chỉ là note biên tập, không xử lý hoặc mix audio.",
            "edit_notes": f"Dùng hướng {mode} để review nhịp, hook, tempo và điểm chuyển cảnh trước khi chuyển sang workflow riêng.",
            "rights_notes": "Tự xác nhận license, attribution, quyền thương mại, thương hiệu và mọi reference; tool này không xác minh quyền.",
            "delivery_notes": "Prompt chỉ để copy hoặc biên tập. Không có audio, preview, output, job hoặc delivery nào được tạo từ receipt này.",
        }
    return {
        "voice_mix_notes": "Keep music below narration and leave breathing room; this is editorial guidance only and does not mix or process audio.",
        "edit_notes": f"Use the {mode} direction to review pacing, hook, tempo, and transitions before moving to a separate workflow.",
        "rights_notes": "Independently confirm license, attribution, commercial rights, brands, and every reference; this tool verifies none of them.",
        "delivery_notes": "Prompts are for copying or editing only. This receipt creates no audio, preview, output, job, or delivery.",
    }


def _compose_music_prompt(payload: MusicPromptComposerRequest) -> dict[str, Any]:
    """Build the Bot-derived suggestion receipt without creating music/media."""

    suggestions = _music_prompt_composer_suggestions(payload)
    if payload.language == "vi":
        title = "Gói gợi ý prompt nhạc"
        cautions = [
            "Đây là hướng prompt dạng văn bản; không tạo nhạc, lyrics, audio, preview, output hoặc job.",
            "Không dùng hướng này để mô phỏng nghệ sĩ, ca sĩ, bài hát, beat, giai điệu hoặc giọng cụ thể.",
            "Mọi claim, tên riêng, thương hiệu, lời bài hát, license và điều khoản phát hành cần được review riêng.",
        ]
        review = [
            "Rà soát tính nguyên bản và tính chính xác của description trước khi dùng ở nơi khác.",
            "Xác nhận quyền với lời, thương hiệu, người, reference, sample và quyền thương mại trước khi tạo audio ở workflow riêng.",
            "Kiểm tra nhạc không che voice, CTA hoặc thông tin quan trọng trước khi biên tập bản phát hành.",
        ]
    else:
        title = "Music prompt direction pack"
        cautions = [
            "This is a text-only prompt direction; it creates no music, lyrics, audio, preview, output, or job.",
            "Do not use this direction to imitate a named artist, singer, song, beat, melody, or voice.",
            "Every claim, name, brand, lyric, license, and release term needs separate review.",
        ]
        review = [
            "Review originality and the accuracy of the description before use elsewhere.",
            "Confirm rights for lyrics, brands, people, references, samples, and commercial use before a separate audio workflow.",
            "Check that music does not mask narration, CTA, or important information before release editing.",
        ]
    result = {
        "title": title,
        "description": payload.description,
        "mode": payload.mode,
        "language": payload.language,
        "suggestion_set": payload.suggestion_set,
        "selected_suggestion": payload.selected_suggestion,
        "suggestions": suggestions,
        "selected_direction": dict(suggestions[payload.selected_suggestion - 1]),
        "usage_notes": _music_prompt_composer_usage_notes(language=payload.language, mode=payload.mode),
        "cautions": cautions,
        "review_before_use": review,
    }
    return MusicPromptComposerResult.model_validate(result).model_dump()


def _music_prompt_composer_memory_note(composer: dict[str, Any]) -> tuple[str, str, list[str]]:
    """Serialize the server-recomputed selected direction as one Web note.

    This is not a generic note body sent by the browser. The persisted text is
    derived from the same strict Composer result inside the write transaction,
    so the selected direction remains canonical and cannot be replaced with
    arbitrary browser-authored content.
    """

    try:
        result = MusicPromptComposerResult.model_validate(composer).model_dump()
        selected = dict(result["selected_direction"])
        usage = dict(result["usage_notes"])
        title = _single_line(
            "Music Prompt Composer",
            label="Tiêu đề ghi chú",
            minimum=3,
            maximum=MAX_MEMORY_NOTE_TITLE,
        )
        lines = [
            "Music Prompt Composer — bản nháp Web đã được dựng lại trên máy chủ.",
            f"Mô tả: {result['description']}",
            f"Chế độ: {result['mode']}",
            f"Ngôn ngữ: {result['language']}",
            f"Nhóm gợi ý: {result['suggestion_set']}",
            f"Lựa chọn đã lưu: {result['selected_suggestion']}",
            "",
            "## Hướng nhạc đã chọn",
            f"Tên: {selected['name']}",
            f"Mood: {selected['mood']}",
            f"Tempo: {selected['tempo']}",
            f"Nhạc cụ: {selected['instruments']}",
            f"Thời lượng: {selected['duration']}",
            f"Vocal: {selected['vocal']}",
            f"Hướng lời: {selected['lyric_direction']}",
            f"Ngữ cảnh dùng: {selected['use_case']}",
            "",
            "## Prompt đã chọn",
            str(selected["prompt"]),
            "",
            "## Ghi chú biên tập",
            f"- Voice/mix: {usage['voice_mix_notes']}",
            f"- Biên tập: {usage['edit_notes']}",
            f"- Quyền: {usage['rights_notes']}",
            f"- Delivery: {usage['delivery_notes']}",
            "",
            "## Lưu ý",
        ]
        lines.extend(f"- {item}" for item in result["cautions"])
        lines.extend(("", "## Kiểm tra trước khi sử dụng"))
        lines.extend(f"- {item}" for item in result["review_before_use"])
        lines.extend(
            (
                "",
                "Ghi chú này không tạo nhạc, lyrics, audio, preview, output, job, tài sản, thanh toán, publish hay gửi Telegram.",
            )
        )
        content = _content(
            "\n".join(lines),
            label="Nội dung ghi chú Music Prompt Composer",
            maximum=MAX_MEMORY_NOTE_CONTENT,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return title, content, [
        "music-prompt-composer",
        f"music-mode-{result['mode']}",
        f"music-language-{result['language']}",
    ]


def _music_prompt_composer_memory_boundaries(
    *,
    draft_recomputed_on_server: bool = True,
    web_note_persisted: bool = True,
) -> dict[str, bool | str]:
    """State the exact side effects of Composer-to-Memory handoff."""

    return {
        "execution": "web_native_memory_note_server_recomputed",
        "draft_recomputed_on_server": draft_recomputed_on_server,
        "web_note_persisted": web_note_persisted,
        "browser_result_persisted": False,
        "pending_bot_save_created": False,
        "telegram_state_changed": False,
        "bot_called": False,
        "bridge_called": False,
        "source_audio_inspected": False,
        "provider_called": False,
        "ai_music_called": False,
        "lyrics_generated": False,
        "audio_created": False,
        "preview_created": False,
        "output_created": False,
        "job_created": False,
        "wallet_mutated": False,
        "payment_started": False,
        "asset_saved": False,
        "collection_saved": False,
        "publish_action_created": False,
        "delivery_created": False,
        "fact_checked": False,
        "rights_verified": False,
    }


@router.post("/tools/music-prompt-composer")
async def compose_music_prompt(
    payload: MusicPromptComposerRequest,
    account: dict = Depends(require_csrf),
):
    """Return a transient music direction receipt with no media execution."""

    _require_enabled()
    del account  # Signed session/CSRF is the only account boundary for this tool.
    guarded = _music_prompt_composer_guard(_music_prompt_composer_marker(payload.description))
    if guarded:
        return guarded
    composer = _compose_music_prompt(payload)
    return envelope(
        True,
        "Đã tạo ba hướng prompt nhạc dạng văn bản để review. Không có nhạc, lyrics, audio, preview, output, job, thanh toán hoặc Telegram action nào được tạo.",
        data={"composer": composer, **_music_prompt_composer_boundary()},
        status_name="draft",
    )


@router.post("/tools/music-prompt-composer/save")
async def save_music_prompt_composer_to_memory(
    payload: MusicPromptComposerMemorySaveRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Persist one server-recomputed music direction as a private Web note.

    This is deliberately separate from the stateless Composer preview. It
    never reads or creates Bot pending state, calls a bridge/provider, creates
    a job, changes wallet/payment state, stores an audio asset, writes a media
    collection, publishes content, or delivers media. Only the signed Web
    account receives an owner-scoped Memory Center note.
    """

    _require_enabled()
    _require_memory_handoff_enabled()
    marker = _music_prompt_composer_marker(payload.description)
    if marker:
        return envelope(
            False,
            "Mô tả cần được viết lại theo hướng nguyên bản trước khi lưu vào Memory Center.",
            data={
                "destination": "memory_note",
                **_music_prompt_composer_memory_boundaries(
                    draft_recomputed_on_server=False,
                    web_note_persisted=False,
                ),
            },
            status_name="guarded",
            error_code="WEB_MUSIC_PROMPT_COPYRIGHT_GUARD",
        )

    account_id = str(account["id"])
    key = _idempotency_key(payload.idempotency_key)
    fingerprint = _fingerprint(
        {
            "action": "music_prompt_composer_memory_save",
            "destination": payload.destination,
            "description": payload.description,
            "mode": payload.mode,
            "language": payload.language,
            "suggestion_set": payload.suggestion_set,
            "selected_suggestion": payload.selected_suggestion,
        }
    )

    def operation(conn: Any) -> dict[str, Any]:
        # Recompute the exact selected direction inside the write transaction.
        # The browser never sends generated prompt/body/title material.
        composer = _compose_music_prompt(payload)
        note_title, note_content, tags = _music_prompt_composer_memory_note(composer)
        active_count = conn.execute(
            "SELECT COUNT(*) FROM web_memory_notes WHERE account_id=? AND state='active'",
            (account_id,),
        ).fetchone()
        if int(active_count[0] or 0) >= MAX_MEMORY_NOTES_PER_ACCOUNT:
            return envelope(
                False,
                "Memory Center đã đạt giới hạn ghi chú đang hoạt động cho Web account này.",
                data={
                    "destination": "memory_note",
                    **_music_prompt_composer_memory_boundaries(
                        draft_recomputed_on_server=True,
                        web_note_persisted=False,
                    ),
                },
                status_name="guarded",
                error_code="WEB_MEMORY_NOTE_LIMIT",
            )
        note_id = str(uuid.uuid4())
        now = utc_now()
        category = "Music Prompt Composer"
        priority = "normal"
        tags_json = json.dumps(tags, ensure_ascii=False, separators=(",", ":"))
        conn.execute(
            """INSERT INTO web_memory_notes
               (id, account_id, title, content, tags_json, category, priority, state, revision, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'active', 1, ?, ?)""",
            (note_id, account_id, note_title, note_content, tags_json, category, priority, now, now),
        )
        conn.execute(
            """INSERT INTO web_memory_note_versions
               (id, note_id, account_id, revision, title, content, tags_json, category, priority, created_at)
               VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), note_id, account_id, note_title, note_content, tags_json, category, priority, now),
        )
        conn.execute(
            """INSERT INTO web_memory_events (id, account_id, note_id, reminder_id, action, created_at)
               VALUES (?, ?, ?, NULL, ?, ?)""",
            (str(uuid.uuid4()), account_id, note_id, "note_created", now),
        )
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="web.media_workspace.music_prompt_composer.save_memory",
            request_id=_request_id(request),
            target=note_id,
            detail="server-recomputed music prompt direction saved as web-owned memory note",
        )
        return envelope(
            True,
            "Đã lưu hướng prompt nhạc vào Memory Center của Web. Không tạo pending Telegram, nhạc, audio, job, tài sản, thanh toán hay publish.",
            data={
                "note": {
                    "id": note_id,
                    "revision": 1,
                    "state": "active",
                    "category": category,
                    "priority": priority,
                },
                "destination": "memory_note",
                **_music_prompt_composer_memory_boundaries(),
            },
            status_name="completed",
        )

    return _idempotent(
        f"web-media-workspace:{account_id}:music-prompt-composer:save-memory",
        account_id,
        key,
        fingerprint,
        operation,
    )


@router.get("/summary")
async def media_workspace_summary(account: dict = Depends(require_account)):
    _require_enabled()
    with read_transaction() as conn:
        data = _summary_data(conn, account_id=str(account["id"]))
    return envelope(True, "Tổng quan Audio Library & Briefing của Web account hiện tại.", data=data, status_name="read_only")


@router.get("/policy")
async def media_workspace_policy(account: dict = Depends(require_account)):
    _require_enabled()
    return envelope(
        True,
        "Chính sách Audio Library & Briefing được nạp ở chế độ chỉ đọc.",
        data={
            "policy": [
                "Không yêu cầu mô phỏng nghệ sĩ, bài hát, giai điệu, beat hoặc giọng cụ thể.",
                "Bạn tự kiểm tra quyền thương mại, attribution, license và điều khoản nền tảng trước khi đăng.",
                "Chỉ Asset Vault audio thuộc Web account hiện tại được gắn vào collection; URL, Telegram file ID và provider preview không được nhận.",
            ],
            "guarded_capabilities": ["provider_library", "ai_generation", "audio_enhance", "audio_translate", "mux_render", "provider_preview"],
            "execution": "authoring_only",
        },
        status_name="read_only",
    )


@router.get("/audio-assets")
async def list_audio_assets(
    q: str = "",
    limit: int = 50,
    offset: int = 0,
    account: dict = Depends(require_account),
):
    _require_enabled()
    query = _safe_filter(q, label="Từ khóa audio", maximum=100)
    bounded = max(1, min(int(limit), MAX_LIST_LIMIT))
    bounded_offset = max(0, min(int(offset), 10_000))
    audio_clauses: list[str] = []
    audio_params: list[Any] = []
    # Keep the SQL predicate exactly aligned with ``_is_audio_asset``.  The
    # old implementation fetched the newest 300 arbitrary Vault files and
    # filtered them in Python, which made an older valid audio impossible to
    # find or attach once a user had a busy Asset Vault.
    for extension in sorted(AUDIO_EXTENSIONS):
        content_types = sorted(AUDIO_CONTENT_TYPES.get(extension, frozenset()))
        placeholders = ", ".join("?" for _ in content_types)
        audio_clauses.append(f"(LOWER(extension)=? AND LOWER(content_type) IN ({placeholders}))")
        audio_params.extend([extension, *content_types])
    clauses = ["account_id=?", "state='active'", f"({' OR '.join(audio_clauses)})"]
    params: list[Any] = [str(account["id"]), *audio_params]
    if query:
        like = f"%{_escaped_like(query)}%"
        clauses.append("(display_name LIKE ? ESCAPE '\\' OR original_filename LIKE ? ESCAPE '\\')")
        params.extend([like, like])
    with read_transaction() as conn:
        rows = conn.execute(
            """SELECT id, project_id, display_name, original_filename, extension, content_type, byte_size,
                      state, created_at, updated_at, archived_at
               FROM web_asset_files
               WHERE """ + " AND ".join(clauses) + """
               ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?""",
            (*params, bounded + 1, bounded_offset),
        ).fetchall()
    items = [_audio_asset_public(row) for row in rows[:bounded]]
    has_more = len(rows) > bounded
    return envelope(
        True,
        "Đã tải audio Asset Vault thuộc Web account hiện tại.",
        data={
            "items": items,
            "has_more": has_more,
            "next_offset": bounded_offset + bounded if has_more else None,
            "filters": {"q": query},
            "pagination": {"limit": bounded, "offset": bounded_offset, "returned": len(items)},
            "source": "asset_vault_owner_scoped",
        },
        status_name="read_only",
    )


@router.get("/collections")
async def list_collections(
    limit: int = 30,
    offset: int = 0,
    state: str = "active",
    q: str = "",
    tag: str = "",
    prompt_mode: str = "",
    account: dict = Depends(require_account),
):
    _require_enabled()
    bounded = max(1, min(int(limit), MAX_LIST_LIMIT))
    bounded_offset = max(0, min(int(offset), 10_000))
    state_filter = str(state or "active").strip().lower()
    if state_filter not in {*COLLECTION_STATES, "all"}:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái collection không hợp lệ")
    query = _safe_filter(q, label="Từ khóa collection", maximum=100)
    tag_filter = _safe_filter(tag, label="Tag", maximum=MAX_TAG_LENGTH)
    mode_filter = _safe_filter(prompt_mode, label="Chế độ brief", maximum=24).lower()
    if mode_filter and mode_filter not in PROMPT_MODES:
        raise HTTPException(status_code=422, detail="Bộ lọc chế độ brief không hợp lệ")
    clauses = ["account_id=?"]
    params: list[Any] = [str(account["id"])]
    if state_filter != "all":
        clauses.append("state=?")
        params.append(state_filter)
    if mode_filter:
        clauses.append("prompt_mode=?")
        params.append(mode_filter)
    if query:
        like = f"%{_escaped_like(query)}%"
        clauses.append("(title LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\' OR creative_brief LIKE ? ESCAPE '\\')")
        params.extend([like, like, like])
    if tag_filter:
        clauses.append("tags_json LIKE ? ESCAPE '\\'")
        params.append(f"%{_escaped_like(tag_filter)}%")
    with read_transaction() as conn:
        rows = conn.execute(
            f"""SELECT id, project_id, title, description, creative_brief, prompt_mode, use_context, tags_json,
                       rights_note, policy_marker, state, revision, created_at, updated_at, archived_at
                FROM web_media_collections WHERE {' AND '.join(clauses)}
                ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?""",
            (*params, bounded + 1, bounded_offset),
        ).fetchall()
    items = [_collection_public(row) for row in rows[:bounded]]
    has_more = len(rows) > bounded
    return envelope(
        True,
        "Đã tải Audio Library & Briefing riêng tư.",
        data={
            "items": items,
            "has_more": has_more,
            "next_offset": bounded_offset + bounded if has_more else None,
            "filters": {"q": query, "tag": tag_filter, "prompt_mode": mode_filter, "state": state_filter},
            "pagination": {"limit": bounded, "offset": bounded_offset, "returned": len(items)},
        },
        status_name="read_only",
    )


@router.post("/collections")
async def create_collection(payload: CollectionCreateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    marker = _payload_policy_marker(payload)
    snapshot = _snapshot_from_payload(payload, marker=marker)
    fingerprint = _fingerprint({
        "title": payload.title, "description": _hash(payload.description), "brief": _hash(payload.creative_brief),
        "mode": payload.prompt_mode, "context": payload.use_context, "tags": payload.tags,
        "rights": _hash(payload.rights_note), "project_id": payload.project_id or None,
    })

    def operation(conn: Any) -> dict[str, Any]:
        guard = _policy_guard(snapshot)
        if guard:
            return guard
        count = conn.execute(
            "SELECT COUNT(*) FROM web_media_collections WHERE account_id=? AND state='active'",
            (account_id,),
        ).fetchone()
        if int(count[0] or 0) >= MAX_COLLECTIONS_PER_STATE:
            return envelope(False, "Đã đạt giới hạn collection active của Web account. Hãy archive collection cũ trước.", status_name="guarded", error_code="WEB_MEDIA_COLLECTION_LIMIT")
        _ensure_project_scope(conn, project_id=snapshot.get("project_id"), account_id=account_id)
        collection_id = str(uuid.uuid4())
        now = utc_now()
        _insert_collection(conn, collection_id=collection_id, account_id=account_id, snapshot=snapshot, revision=1, now=now)
        _insert_version(conn, collection_id=collection_id, account_id=account_id, revision=1, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, collection_id=collection_id, action="collection_created", revision=1)
        _audit(conn, request=request, account=account, action="web.media.collection.create", target=collection_id, detail=f"mode={snapshot['prompt_mode']};project={'yes' if snapshot.get('project_id') else 'no'}")
        row = _collection_row(conn, collection_id=collection_id, account_id=account_id)
        return envelope(
            True,
            "Đã tạo Audio Library collection riêng tư.",
            data={"collection": _collection_public(row, include_content=True), "execution": "authoring_only"},
            status_name="draft",
        )

    return _idempotent(f"web-media-workspace:{account_id}:collection:create", account_id, key, fingerprint, operation)


@router.get("/collections/{collection_id}")
async def get_collection(collection_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    collection_id = _uuid(collection_id, label="Collection ID")
    with read_transaction() as conn:
        detail = _collection_detail(conn, collection_id=collection_id, account_id=str(account["id"]))
    if not detail:
        return _collection_not_found()
    return envelope(True, "Đã tải collection riêng tư cùng history và audio references.", data=detail, status_name="read_only")


@router.patch("/collections/{collection_id}")
async def update_collection(collection_id: str, payload: CollectionUpdateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    collection_id = _uuid(collection_id, label="Collection ID")
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    marker = _payload_policy_marker(payload)
    snapshot = _snapshot_from_payload(payload, marker=marker)
    fingerprint = _fingerprint({
        "id": collection_id, "revision": payload.expected_revision, "title": payload.title,
        "description": _hash(payload.description), "brief": _hash(payload.creative_brief), "mode": payload.prompt_mode,
        "context": payload.use_context, "tags": payload.tags, "rights": _hash(payload.rights_note), "project_id": payload.project_id or None,
    })

    def operation(conn: Any) -> dict[str, Any]:
        row = _collection_row(conn, collection_id=collection_id, account_id=account_id)
        if not row:
            return _collection_not_found()
        if int(row[11]) != payload.expected_revision:
            return _revision_conflict()
        if str(row[10]) != "active":
            return envelope(False, "Collection đã archive và không thể chỉnh sửa trước khi khôi phục.", status_name="guarded", error_code="WEB_MEDIA_COLLECTION_ARCHIVED")
        guard = _policy_guard(snapshot)
        if guard:
            return guard
        if not _can_add_version(conn, collection_id=collection_id, account_id=account_id):
            return _version_limit()
        _ensure_project_scope(conn, project_id=snapshot.get("project_id"), account_id=account_id)
        revision = int(row[11]) + 1
        now = utc_now()
        _write_collection_update(conn, collection_id=collection_id, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_version(conn, collection_id=collection_id, account_id=account_id, revision=revision, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, collection_id=collection_id, action="collection_updated", revision=revision)
        _audit(conn, request=request, account=account, action="web.media.collection.update", target=collection_id, detail=f"revision={revision};mode={snapshot['prompt_mode']}")
        updated = _collection_row(conn, collection_id=collection_id, account_id=account_id)
        return envelope(
            True,
            "Đã lưu phiên bản collection mới.",
            data={"collection": _collection_public(updated, include_content=True), "execution": "authoring_only"},
            status_name="draft",
        )

    return _idempotent(f"web-media-workspace:{account_id}:collection:{collection_id}:update", account_id, key, fingerprint, operation)


def _collection_state_transition(*, collection_id: str, payload: RevisionMutationRequest, request: Request, account: dict, target_state: str, action: str) -> dict[str, Any]:
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    fingerprint = _fingerprint({"id": collection_id, "revision": payload.expected_revision, "action": action})

    def operation(conn: Any) -> dict[str, Any]:
        row = _collection_row(conn, collection_id=collection_id, account_id=account_id)
        if not row:
            return _collection_not_found()
        if int(row[11]) != payload.expected_revision:
            return _revision_conflict()
        if str(row[10]) == target_state:
            return envelope(False, "Collection đã ở trạng thái yêu cầu.", status_name="guarded", error_code="WEB_MEDIA_COLLECTION_STATE")
        snapshot = _snapshot_from_row(row, state=target_state)
        if target_state == "active":
            # History remains bounded.  A collection archived at that ceiling
            # must still be restorable: failing restore would make an ordinary
            # archive a permanent, surprising state transition.  The response
            # explicitly says when this transition could not add a snapshot.
            _ensure_project_scope(conn, project_id=snapshot.get("project_id"), account_id=account_id)
        revision = int(row[11]) + 1
        now = utc_now()
        archived_at = now if target_state == "archived" else None
        _write_collection_update(conn, collection_id=collection_id, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=archived_at)
        snapshot_recorded = _can_add_version(conn, collection_id=collection_id, account_id=account_id)
        if snapshot_recorded:
            _insert_version(conn, collection_id=collection_id, account_id=account_id, revision=revision, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, collection_id=collection_id, action=action if snapshot_recorded else f"{action}_without_snapshot", revision=revision)
        _audit(conn, request=request, account=account, action=f"web.media.collection.{action}", target=collection_id, detail=f"revision={revision};snapshot={'yes' if snapshot_recorded else 'no'}")
        updated = _collection_row(conn, collection_id=collection_id, account_id=account_id)
        return envelope(
            True,
            "Đã cập nhật trạng thái collection."
            + (" Lịch sử đã đạt giới hạn nên lần chuyển trạng thái này không thêm snapshot mới." if not snapshot_recorded else ""),
            data={
                "collection": _collection_public(updated, include_content=True),
                "history_snapshot_recorded": snapshot_recorded,
                "execution": "authoring_only",
            },
            status_name="draft",
        )

    return _idempotent(f"web-media-workspace:{account_id}:collection:{collection_id}:{action}", account_id, key, fingerprint, operation)


@router.post("/collections/{collection_id}/archive")
async def archive_collection(collection_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    return _collection_state_transition(collection_id=_uuid(collection_id, label="Collection ID"), payload=payload, request=request, account=account, target_state="archived", action="collection_archived")


@router.post("/collections/{collection_id}/restore")
async def restore_collection(collection_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    return _collection_state_transition(collection_id=_uuid(collection_id, label="Collection ID"), payload=payload, request=request, account=account, target_state="active", action="collection_restored")


@router.post("/collections/{collection_id}/duplicate")
async def duplicate_collection(collection_id: str, payload: DuplicateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    collection_id = _uuid(collection_id, label="Collection ID")
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    fingerprint = _fingerprint({"id": collection_id, "revision": payload.expected_revision, "title": payload.title})

    def operation(conn: Any) -> dict[str, Any]:
        source = _collection_row(conn, collection_id=collection_id, account_id=account_id)
        if not source:
            return _collection_not_found()
        if int(source[11]) != payload.expected_revision:
            return _revision_conflict()
        active_count = conn.execute("SELECT COUNT(*) FROM web_media_collections WHERE account_id=? AND state='active'", (account_id,)).fetchone()
        if int(active_count[0] or 0) >= MAX_COLLECTIONS_PER_STATE:
            return envelope(False, "Đã đạt giới hạn collection active của Web account. Hãy archive collection cũ trước.", status_name="guarded", error_code="WEB_MEDIA_COLLECTION_LIMIT")
        snapshot = _snapshot_from_row(source, state="active")
        snapshot["title"] = payload.title or f"{snapshot['title']} (bản sao)"
        snapshot["policy_marker"] = _copyright_marker(snapshot["title"], snapshot["description"], snapshot["creative_brief"], snapshot["use_context"])
        guard = _policy_guard(snapshot)
        if guard:
            return guard
        _ensure_project_scope(conn, project_id=snapshot.get("project_id"), account_id=account_id)
        new_id = str(uuid.uuid4())
        now = utc_now()
        _insert_collection(conn, collection_id=new_id, account_id=account_id, snapshot=snapshot, revision=1, now=now)
        _insert_version(conn, collection_id=new_id, account_id=account_id, revision=1, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, collection_id=new_id, action="collection_duplicated", revision=1)
        _audit(conn, request=request, account=account, action="web.media.collection.duplicate", target=new_id, detail=f"source={collection_id};items_not_copied=yes")
        created = _collection_row(conn, collection_id=new_id, account_id=account_id)
        return envelope(
            True,
            "Đã nhân bản collection. Audio references không được sao chép tự động để tránh gắn nhầm bối cảnh.",
            data={"collection": _collection_public(created, include_content=True), "execution": "authoring_only"},
            status_name="draft",
        )

    return _idempotent(f"web-media-workspace:{account_id}:collection:{collection_id}:duplicate", account_id, key, fingerprint, operation)


@router.post("/collections/{collection_id}/restore-version")
async def restore_collection_version(collection_id: str, payload: RestoreVersionRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    collection_id = _uuid(collection_id, label="Collection ID")
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    fingerprint = _fingerprint({"id": collection_id, "revision": payload.expected_revision, "restore": payload.revision})

    def operation(conn: Any) -> dict[str, Any]:
        current = _collection_row(conn, collection_id=collection_id, account_id=account_id)
        if not current:
            return _collection_not_found()
        if int(current[11]) != payload.expected_revision:
            return _revision_conflict()
        if str(current[10]) != "active":
            return envelope(False, "Hãy khôi phục collection trước khi khôi phục một version metadata.", status_name="guarded", error_code="WEB_MEDIA_COLLECTION_ARCHIVED")
        if not _can_add_version(conn, collection_id=collection_id, account_id=account_id):
            return _version_limit()
        row = conn.execute(
            "SELECT snapshot_json FROM web_media_collection_versions WHERE collection_id=? AND account_id=? AND revision=?",
            (collection_id, account_id, payload.revision),
        ).fetchone()
        if not row:
            return envelope(False, "Không tìm thấy phiên bản collection thuộc Web account hiện tại.", status_name="guarded", error_code="WEB_MEDIA_VERSION_NOT_FOUND")
        try:
            stored = json.loads(str(row[0]))
            restored_payload = CollectionPayload.model_validate({
                "title": stored.get("title"), "description": stored.get("description", ""),
                "creative_brief": stored.get("creative_brief", ""), "prompt_mode": stored.get("prompt_mode", "background"),
                "use_context": stored.get("use_context", "general"), "tags": stored.get("tags", []),
                "rights_note": stored.get("rights_note", ""), "project_id": stored.get("project_id") or "",
            })
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=409, detail="Snapshot collection không hợp lệ") from exc
        marker = _payload_policy_marker(restored_payload)
        snapshot = _snapshot_from_payload(restored_payload, state="active", marker=marker)
        guard = _policy_guard(snapshot)
        if guard:
            return guard
        _ensure_project_scope(conn, project_id=snapshot.get("project_id"), account_id=account_id)
        revision = int(current[11]) + 1
        now = utc_now()
        _write_collection_update(conn, collection_id=collection_id, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_version(conn, collection_id=collection_id, account_id=account_id, revision=revision, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, collection_id=collection_id, action="collection_version_restored", revision=revision)
        _audit(conn, request=request, account=account, action="web.media.collection.restore_version", target=collection_id, detail=f"from_revision={payload.revision};to_revision={revision};items_unchanged=yes")
        updated = _collection_row(conn, collection_id=collection_id, account_id=account_id)
        return envelope(
            True,
            "Đã khôi phục metadata thành revision mới. Audio references không bị thay đổi tự động.",
            data={"collection": _collection_public(updated, include_content=True), "execution": "authoring_only"},
            status_name="draft",
        )

    return _idempotent(f"web-media-workspace:{account_id}:collection:{collection_id}:restore-version:{payload.revision}", account_id, key, fingerprint, operation)


@router.post("/collections/{collection_id}/compose")
async def compose_collection_brief(collection_id: str, payload: ComposeRequest, account: dict = Depends(require_csrf)):
    """Return deterministic textual directions; never call an AI/music engine."""
    _require_enabled()
    collection_id = _uuid(collection_id, label="Collection ID")
    with read_transaction() as conn:
        row = _collection_row(conn, collection_id=collection_id, account_id=str(account["id"]))
    if not row:
        return _collection_not_found()
    if int(row[11]) != payload.expected_revision:
        return _revision_conflict()
    if str(row[10]) != "active":
        return envelope(False, "Collection đã archive. Hãy khôi phục trước khi soạn hướng prompt.", status_name="guarded", error_code="WEB_MEDIA_COLLECTION_ARCHIVED")
    snapshot = _snapshot_from_row(row)
    guard = _policy_guard(snapshot)
    if guard:
        return guard
    if not str(snapshot.get("creative_brief") or "").strip():
        return envelope(False, "Hãy thêm Music brief trước khi tạo hướng prompt cục bộ.", status_name="guarded", error_code="WEB_MEDIA_BRIEF_REQUIRED")
    return envelope(
        True,
        "Đã tạo 3 hướng brief cục bộ. Đây là text authoring, không phải yêu cầu AI, audio output, job hoặc báo giá.",
        data={
            "collection_id": collection_id,
            "revision": int(row[11]),
            "directions": _composer_directions(snapshot),
            "execution": "local_deterministic_draft_only",
            "provider_called": False,
            "charge_started": False,
        },
        status_name="draft",
    )


def _collection_for_item_mutation(conn: Any, *, collection_id: str, account_id: str, expected_revision: int) -> tuple[Any, ...] | dict[str, Any]:
    collection = _collection_row(conn, collection_id=collection_id, account_id=account_id)
    if not collection:
        return _collection_not_found()
    if int(collection[11]) != expected_revision:
        return _revision_conflict()
    if str(collection[10]) != "active":
        return envelope(False, "Collection đã archive và không thể thay đổi audio references.", status_name="guarded", error_code="WEB_MEDIA_COLLECTION_ARCHIVED")
    return collection


def _increment_item_revision(conn: Any, *, collection: tuple[Any, ...], account_id: str, action: str, request: Request, account: dict, target: str, detail: str) -> int:
    revision = int(collection[11]) + 1
    now = utc_now()
    conn.execute(
        "UPDATE web_media_collections SET revision=?, updated_at=? WHERE id=? AND account_id=?",
        (revision, now, str(collection[0]), account_id),
    )
    _event(conn, account_id=account_id, collection_id=str(collection[0]), action=action, revision=revision)
    _audit(conn, request=request, account=account, action=f"web.media.item.{action}", target=target, detail=f"collection={collection[0]};revision={revision};{detail}")
    return revision


@router.post("/collections/{collection_id}/items")
async def attach_media_item(collection_id: str, payload: AttachMediaItemRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    collection_id = _uuid(collection_id, label="Collection ID")
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    fingerprint = _fingerprint({
        "collection": collection_id, "revision": payload.expected_revision, "asset": payload.asset_id, "role": payload.role,
        "label": payload.title_override, "attribution": _hash(payload.attribution), "license": _hash(payload.license_note),
        "tags": payload.tags, "favorite": payload.favorite, "duration": payload.user_declared_duration_seconds,
    })

    def operation(conn: Any) -> dict[str, Any]:
        collection = _collection_for_item_mutation(conn, collection_id=collection_id, account_id=account_id, expected_revision=payload.expected_revision)
        if isinstance(collection, dict):
            return collection
        asset = _audio_asset_row(conn, asset_id=payload.asset_id, account_id=account_id)
        if not asset:
            return _audio_asset_not_found()
        count = conn.execute("SELECT COUNT(*) FROM web_media_items WHERE collection_id=? AND account_id=?", (collection_id, account_id)).fetchone()
        if int(count[0] or 0) >= MAX_ITEMS_PER_COLLECTION:
            return envelope(False, "Collection đã đạt giới hạn audio references.", status_name="guarded", error_code="WEB_MEDIA_COLLECTION_ITEM_LIMIT")
        account_count = conn.execute("SELECT COUNT(*) FROM web_media_items WHERE account_id=?", (account_id,)).fetchone()
        if int(account_count[0] or 0) >= MAX_ITEMS_PER_ACCOUNT:
            return envelope(False, "Web account đã đạt giới hạn audio references.", status_name="guarded", error_code="WEB_MEDIA_ACCOUNT_ITEM_LIMIT")
        duplicate = conn.execute("SELECT id FROM web_media_items WHERE collection_id=? AND asset_id=?", (collection_id, payload.asset_id)).fetchone()
        if duplicate:
            return envelope(False, "Tệp audio này đã nằm trong collection.", status_name="guarded", error_code="WEB_MEDIA_ITEM_EXISTS")
        item_id = str(uuid.uuid4())
        now = utc_now()
        conn.execute(
            """INSERT INTO web_media_items
               (id, collection_id, account_id, asset_id, role, title_override, attribution, license_note, tags_json,
                favorite, user_declared_duration_seconds, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (item_id, collection_id, account_id, payload.asset_id, payload.role, payload.title_override, payload.attribution,
             payload.license_note, json.dumps(payload.tags, ensure_ascii=False, separators=(",", ":")), int(payload.favorite),
             payload.user_declared_duration_seconds, now, now),
        )
        revision = _increment_item_revision(conn, collection=collection, account_id=account_id, action="item_attached", request=request, account=account, target=item_id, detail=f"role={payload.role};asset=owner_checked")
        return envelope(
            True,
            "Đã gắn audio Asset Vault vào collection. Đây là reference riêng tư, không phải media output hay yêu cầu render.",
            data={
                "item_id": item_id,
                "collection_id": collection_id,
                "revision": revision,
                "execution": "authoring_only",
                "delivery": "asset_vault_attachment_only",
            },
            status_name="draft",
        )

    return _idempotent(f"web-media-workspace:{account_id}:collection:{collection_id}:item:attach", account_id, key, fingerprint, operation)


@router.patch("/collections/{collection_id}/items/{item_id}")
async def update_media_item(collection_id: str, item_id: str, payload: UpdateMediaItemRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    collection_id = _uuid(collection_id, label="Collection ID")
    item_id = _uuid(item_id, label="Media item ID")
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    fingerprint = _fingerprint({
        "collection": collection_id, "item": item_id, "revision": payload.expected_revision, "role": payload.role,
        "label": payload.title_override, "attribution": _hash(payload.attribution), "license": _hash(payload.license_note),
        "tags": payload.tags, "favorite": payload.favorite, "duration": payload.user_declared_duration_seconds,
    })

    def operation(conn: Any) -> dict[str, Any]:
        collection = _collection_for_item_mutation(conn, collection_id=collection_id, account_id=account_id, expected_revision=payload.expected_revision)
        if isinstance(collection, dict):
            return collection
        row = conn.execute("SELECT id FROM web_media_items WHERE id=? AND collection_id=? AND account_id=?", (item_id, collection_id, account_id)).fetchone()
        if not row:
            return envelope(False, "Không tìm thấy audio reference thuộc collection hiện tại.", status_name="guarded", error_code="WEB_MEDIA_ITEM_NOT_FOUND")
        now = utc_now()
        conn.execute(
            """UPDATE web_media_items SET role=?, title_override=?, attribution=?, license_note=?, tags_json=?, favorite=?,
               user_declared_duration_seconds=?, updated_at=? WHERE id=? AND collection_id=? AND account_id=?""",
            (payload.role, payload.title_override, payload.attribution, payload.license_note,
             json.dumps(payload.tags, ensure_ascii=False, separators=(",", ":")), int(payload.favorite), payload.user_declared_duration_seconds,
             now, item_id, collection_id, account_id),
        )
        revision = _increment_item_revision(conn, collection=collection, account_id=account_id, action="item_updated", request=request, account=account, target=item_id, detail=f"role={payload.role};favorite={int(payload.favorite)}")
        return envelope(
            True,
            "Đã cập nhật metadata audio reference.",
            data={
                "item_id": item_id,
                "collection_id": collection_id,
                "revision": revision,
                "execution": "authoring_only",
                "delivery": "asset_vault_attachment_only",
            },
            status_name="draft",
        )

    return _idempotent(f"web-media-workspace:{account_id}:collection:{collection_id}:item:{item_id}:update", account_id, key, fingerprint, operation)


@router.post("/collections/{collection_id}/items/{item_id}/detach")
async def detach_media_item(collection_id: str, item_id: str, payload: DetachMediaItemRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    collection_id = _uuid(collection_id, label="Collection ID")
    item_id = _uuid(item_id, label="Media item ID")
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    fingerprint = _fingerprint({"collection": collection_id, "item": item_id, "revision": payload.expected_revision, "detach": True})

    def operation(conn: Any) -> dict[str, Any]:
        collection = _collection_for_item_mutation(conn, collection_id=collection_id, account_id=account_id, expected_revision=payload.expected_revision)
        if isinstance(collection, dict):
            return collection
        row = conn.execute("SELECT id FROM web_media_items WHERE id=? AND collection_id=? AND account_id=?", (item_id, collection_id, account_id)).fetchone()
        if not row:
            return envelope(False, "Không tìm thấy audio reference thuộc collection hiện tại.", status_name="guarded", error_code="WEB_MEDIA_ITEM_NOT_FOUND")
        conn.execute("DELETE FROM web_media_items WHERE id=? AND collection_id=? AND account_id=?", (item_id, collection_id, account_id))
        revision = _increment_item_revision(conn, collection=collection, account_id=account_id, action="item_detached", request=request, account=account, target=item_id, detail="asset_remains_in_vault=yes")
        return envelope(
            True,
            "Đã gỡ audio reference khỏi collection. Tệp gốc vẫn nằm nguyên trong Asset Vault.",
            data={
                "item_id": item_id,
                "collection_id": collection_id,
                "revision": revision,
                "execution": "authoring_only",
                "delivery": "asset_vault_attachment_only",
            },
            status_name="draft",
        )

    return _idempotent(f"web-media-workspace:{account_id}:collection:{collection_id}:item:{item_id}:detach", account_id, key, fingerprint, operation)


@router.get("/events")
async def media_workspace_events(limit: int = 40, account: dict = Depends(require_account)):
    _require_enabled()
    bounded = max(1, min(int(limit), MAX_EVENT_LIMIT))
    with read_transaction() as conn:
        rows = conn.execute(
            """SELECT id, collection_id, action, revision, created_at
               FROM web_media_events WHERE account_id=? ORDER BY created_at DESC, id DESC LIMIT ?""",
            (str(account["id"]), bounded),
        ).fetchall()
    return envelope(
        True,
        "Đã tải hoạt động Audio Library & Briefing riêng tư.",
        data={"items": [{"id": str(row[0]), "collection_id": str(row[1]), "action": str(row[2]), "revision": int(row[3]), "created_at": str(row[4])} for row in rows]},
        status_name="read_only",
    )
