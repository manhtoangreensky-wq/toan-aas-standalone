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
from pydantic import BaseModel, ConfigDict, Field, field_validator

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import ensure_copyfast_schema, music_media_workspace_enabled, read_transaction, transaction, utc_now


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
async def list_audio_assets(q: str = "", limit: int = 50, account: dict = Depends(require_account)):
    _require_enabled()
    query = _safe_filter(q, label="Từ khóa audio", maximum=100)
    bounded = max(1, min(int(limit), MAX_LIST_LIMIT))
    with read_transaction() as conn:
        rows = conn.execute(
            """SELECT id, project_id, display_name, original_filename, extension, content_type, byte_size,
                      state, created_at, updated_at, archived_at
               FROM web_asset_files
               WHERE account_id=? AND state='active'
               ORDER BY updated_at DESC, id DESC LIMIT 300""",
            (str(account["id"]),),
        ).fetchall()
    items = [_audio_asset_public(row) for row in rows if _is_audio_asset(row[4], row[5])]
    if query:
        needle = query.casefold()
        items = [item for item in items if needle in f"{item['display_name']} {item['original_filename']}".casefold()]
    return envelope(
        True,
        "Đã tải audio Asset Vault thuộc Web account hiện tại.",
        data={"items": items[:bounded], "has_more": len(items) > bounded, "source": "asset_vault_owner_scoped"},
        status_name="read_only",
    )


@router.get("/collections")
async def list_collections(
    limit: int = 30,
    state: str = "active",
    q: str = "",
    tag: str = "",
    prompt_mode: str = "",
    account: dict = Depends(require_account),
):
    _require_enabled()
    bounded = max(1, min(int(limit), MAX_LIST_LIMIT))
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
                ORDER BY updated_at DESC, id DESC LIMIT ?""",
            (*params, bounded + 1),
        ).fetchall()
    return envelope(
        True,
        "Đã tải Audio Library & Briefing riêng tư.",
        data={"items": [_collection_public(row) for row in rows[:bounded]], "has_more": len(rows) > bounded},
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
