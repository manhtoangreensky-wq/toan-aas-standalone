"""Private, Web-owned Prompt Library and Template Vault.

The frozen Telegram Bot contains an administrator-managed global prompt seed.
This module deliberately does not read that JSON file or mirror its mutable
runtime.  Instead, signed Web accounts own reusable prompt templates with
explicit metadata, immutable revisions, safe local previews and bounded
import/export.  It never calls a provider, Bot bridge, wallet, PayOS or job
runtime.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import re
import uuid
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import ensure_copyfast_schema, prompt_library_enabled, read_transaction, transaction, utc_now


router = APIRouter(prefix="/api/v1/prompt-library", tags=["Web Prompt Library"])

TEMPLATE_STATES = frozenset({"active", "archived"})
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
VARIABLE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]{0,63})\s*\}\}")
FORBIDDEN_VARIABLE_NAMES = frozenset({"__proto__", "constructor", "prototype"})
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|token|"
    r"client[ _-]?secret|aws[ _-]?secret[ _-]?access[ _-]?key|secret(?:[ _-]?(?:key|access[ _-]?key))?|"
    r"password|passphrase|authorization)"
    r"\b\s*(?:['\"]\s*)?(?:[:=]|\bis\b)\s*(?:['\"]\s*)?(?:(?:bearer|basic)\s+)?[A-Za-z0-9_./+=:-]{8,}",
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
    r"-----BEGIN(?: [A-Z0-9]+)? PRIVATE KEY-----|"
    r"-----BEGIN OPENSSH PRIVATE KEY-----|"
    r"\bssh-(?:rsa|ed25519|ecdsa)\s+[A-Za-z0-9+/]{32,}",
    re.IGNORECASE,
)
CARD_LIKE_PATTERN = re.compile(r"(?<![0-9A-Za-z])[0-9](?:[\s./-]*[0-9]){12,18}(?![0-9A-Za-z])")
OTP_PATTERN = re.compile(
    r"\b(?:otp|cvv|cvc|pin|mã\s*(?:xác\s*(?:minh|thực)|otp)|"
    r"ma\s*(?:xac\s*(?:minh|thuc)|otp)|verification\s+(?:code|token)|"
    r"one[ -]?time(?:\s+(?:pass(?:word|code)?|code))?)\b",
    re.IGNORECASE,
)
PAYMENT_PROOF_PATTERN = re.compile(
    r"\b(?:tx(?:id|n)?|transaction\s+(?:hash|id|reference|no\.?|number)|"
    r"mã\s*(?:(?:giao\s*)?(?:dịch|gd)|tham\s*chiếu|thanh\s*toán)|"
    r"ma\s*(?:(?:giao\s*)?(?:dich|gd)|tham\s*chieu|thanh\s*toan)|"
    r"biên\s*lai|bien\s*lai|chứng\s*từ|chung\s*tu|bill|số\s*tài\s*khoản|"
    r"so\s*tai\s*khoan|stk|tài\s*khoản\s*(?:ngân\s*hàng|bank)|"
    r"tai\s*khoan\s*(?:ngan\s*hang|bank)|bank\s+account|account\s+(?:number|no|id)|"
    r"qr\s*(?:code|thanh\s*toán|thanh\s*toan)?)\b",
    re.IGNORECASE,
)
UNSAFE_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# A signed account can keep a bounded working set and a bounded archive.  The
# two independent ceilings make archive/create cycles finite and let export
# cover every persisted record without silently dropping old templates.
MAX_TEMPLATES_PER_ACCOUNT = 1_000
MAX_ARCHIVED_TEMPLATES_PER_ACCOUNT = 1_000
MAX_TOTAL_TEMPLATES_PER_ACCOUNT = MAX_TEMPLATES_PER_ACCOUNT + MAX_ARCHIVED_TEMPLATES_PER_ACCOUNT
MAX_VERSIONS_PER_TEMPLATE = 100
MAX_TITLE = 180
MAX_META = 100
MAX_PROMPT = 16_000
MAX_NEGATIVE_PROMPT = 8_000
MAX_PREVIEW_OUTPUT = 128_000
MAX_NOTE = 600
MAX_TAGS = 16
MAX_TAG_LENGTH = 48
MAX_VARIABLES = 24
MAX_IMPORT_ITEMS = 50
MAX_LIST_LIMIT = 100
# Payload storage is deliberately bounded separately from record counts. It
# includes both the current template row and immutable snapshots, which are
# physically separate SQLite records. A content-sized quota prevents a single
# Web account from turning the shared signed-session database into a multi-GB
# history store just by rotating revisions.
MAX_TEMPLATE_STORAGE_BYTES = 24 * 1024 * 1024
MAX_EXPORT_BYTES = 24 * 1024 * 1024
SNAPSHOT_ROW_OVERHEAD_BYTES = 256
IDEMPOTENCY_RETENTION = timedelta(hours=24)
MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT = 2_048
SNAPSHOT_TEXT_FIELDS = (
    "title", "category", "product_context", "platform", "style", "language",
    "prompt_text", "negative_prompt", "variables_json", "tags_json", "source_note",
    "license_note",
)


def _require_prompt_library_enabled() -> None:
    if not prompt_library_enabled():
        raise HTTPException(
            status_code=503,
            detail="Prompt Library đang tạm dừng để bảo trì. WEBAPP_PROMPT_LIBRARY_ENABLED chưa được bật.",
        )


def _uuid(value: Any, *, label: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail=f"{label} không hợp lệ") from exc


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
        raise ValueError(f"Tối đa {MAX_TAGS} tags cho một template")
    return values


def _variables(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("Variables phải là một danh sách tên biến")
    values: list[str] = []
    seen: set[str] = set()
    for item in value:
        name = str(item or "").strip()
        if not VARIABLE_NAME_PATTERN.fullmatch(name):
            raise ValueError("Tên variable chỉ dùng chữ, số và gạch dưới, bắt đầu bằng chữ hoặc gạch dưới")
        if name.casefold() in FORBIDDEN_VARIABLE_NAMES:
            raise ValueError("Tên variable này được dành riêng và không thể dùng trong preview")
        fingerprint = name.casefold()
        if fingerprint not in seen:
            seen.add(fingerprint)
            values.append(name)
    if len(values) > MAX_VARIABLES:
        raise ValueError(f"Tối đa {MAX_VARIABLES} variables cho một template")
    return values


def _preview_values(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict) or len(value) > MAX_VARIABLES:
        raise ValueError("Giá trị preview không hợp lệ")
    result: dict[str, str] = {}
    for raw_name, raw_value in value.items():
        name = str(raw_name or "").strip()
        if not VARIABLE_NAME_PATTERN.fullmatch(name):
            raise ValueError("Tên variable preview không hợp lệ")
        if name.casefold() in FORBIDDEN_VARIABLE_NAMES:
            raise ValueError("Tên variable preview này được dành riêng")
        result[name] = _content(raw_value, label="Giá trị preview", maximum=600, allow_empty=True)
    return result


def _escaped_like(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _safe_filter(value: Any, *, label: str, maximum: int = MAX_META) -> str:
    try:
        return _single_line(value, label=label, minimum=0, maximum=maximum, allow_empty=True)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _fingerprint(payload: dict[str, Any]) -> str:
    material = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _content_hash(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _idempotency_cutoff() -> str:
    return (datetime.now(timezone.utc) - IDEMPOTENCY_RETENTION).isoformat(timespec="seconds")


def _idempotent(
    scope: str,
    account_id: str,
    key: str,
    request_fingerprint: str,
    operation: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    """Execute one durable mutation without retaining raw recipe material.

    Only successful writes need a retry receipt. Guarded/no-op outcomes have
    no side effect and are intentionally not persisted, preventing random
    client keys from becoming a durable growth vector.
    """
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute(
            "DELETE FROM web_idempotency WHERE scope LIKE ? AND created_at < ?",
            ("web-prompt-library:%", _idempotency_cutoff()),
        )
        existing = conn.execute(
            "SELECT response_json, request_fingerprint FROM web_idempotency WHERE scope=? AND key=?",
            (scope, key),
        ).fetchone()
        if existing:
            stored_fingerprint = str(existing[1] or "")
            if not stored_fingerprint or not hmac.compare_digest(stored_fingerprint, request_fingerprint):
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho yêu cầu khác")
            try:
                response = json.loads(str(existing[0]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Bản ghi idempotency Prompt Library không hợp lệ") from exc
            if isinstance(response, dict):
                return response
            raise HTTPException(status_code=409, detail="Bản ghi idempotency Prompt Library không hợp lệ")

        receipt_count = conn.execute(
            "SELECT COUNT(*) FROM web_idempotency WHERE scope LIKE ?",
            (f"web-prompt-library:{account_id}:%",),
        ).fetchone()
        if int(receipt_count[0] or 0) >= MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT:
            return envelope(
                False,
                "Kho receipt thao tác tạm thời đang đầy. Vui lòng thử lại sau khi các receipt cũ hết hạn.",
                status_name="guarded",
                error_code="WEB_PROMPT_IDEMPOTENCY_LIMIT",
            )
        response = operation(conn)
        if response.get("ok") is True:
            conn.execute(
                """INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (scope, key, json.dumps(response, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
            )
    return response


def _decode_list(value: Any, *, limit: int) -> list[str]:
    try:
        parsed = json.loads(str(value or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if isinstance(item, str)][:limit]


def _excerpt(value: Any, *, limit: int = 260) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def _template_public(
    row: tuple[Any, ...], *, include_content: bool = False, include_excerpt: bool = True
) -> dict[str, Any]:
    result = {
        "id": str(row[0]),
        "title": str(row[1]),
        "category": str(row[2] or ""),
        "product_context": str(row[3] or ""),
        "platform": str(row[4] or ""),
        "style": str(row[5] or ""),
        "language": str(row[6] or ""),
        "variables": _decode_list(row[9], limit=MAX_VARIABLES),
        "tags": _decode_list(row[10], limit=MAX_TAGS),
        "quality_score": int(row[13]),
        "state": str(row[14]),
        "revision": int(row[15]),
        "created_at": str(row[16]),
        "updated_at": str(row[17]),
    }
    if include_excerpt:
        result["excerpt"] = _excerpt(row[7])
    if include_content:
        result.update(
            {
                "prompt_text": str(row[7]),
                "negative_prompt": str(row[8] or ""),
                "source": str(row[11] or ""),
                "license_note": str(row[12] or ""),
            }
        )
    return result


def _version_public(row: tuple[Any, ...], *, include_content: bool = False) -> dict[str, Any]:
    result = {
        "revision": int(row[0]),
        "title": str(row[1]),
        "category": str(row[2] or ""),
        "product_context": str(row[3] or ""),
        "platform": str(row[4] or ""),
        "style": str(row[5] or ""),
        "language": str(row[6] or ""),
        "variables": _decode_list(row[9], limit=MAX_VARIABLES),
        "tags": _decode_list(row[10], limit=MAX_TAGS),
        "quality_score": int(row[13]),
        "state": str(row[14]),
        "created_at": str(row[15]),
        "excerpt": _excerpt(row[7]),
    }
    if include_content:
        result.update(
            {
                "prompt_text": str(row[7]),
                "negative_prompt": str(row[8] or ""),
                "source": str(row[11] or ""),
                "license_note": str(row[12] or ""),
            }
        )
    return result


def _template_row(conn: Any, *, template_id: str, account_id: str) -> tuple[Any, ...] | None:
    row = conn.execute(
        """SELECT id, title, category, product_context, platform, style, language, prompt_text,
                  negative_prompt, variables_json, tags_json, source_note, license_note, quality_score,
                  state, revision, created_at, updated_at
           FROM web_prompt_templates WHERE id=? AND account_id=?""",
        (template_id, account_id),
    ).fetchone()
    return tuple(row) if row else None


def _template_not_found() -> dict[str, Any]:
    return envelope(
        False,
        "Không tìm thấy template thuộc Web account hiện tại.",
        status_name="guarded",
        error_code="WEB_PROMPT_TEMPLATE_NOT_FOUND",
    )


def _snapshot_from_row(row: tuple[Any, ...], *, state: str | None = None) -> dict[str, Any]:
    return {
        "title": str(row[1]),
        "category": str(row[2] or ""),
        "product_context": str(row[3] or ""),
        "platform": str(row[4] or ""),
        "style": str(row[5] or ""),
        "language": str(row[6] or ""),
        "prompt_text": str(row[7]),
        "negative_prompt": str(row[8] or ""),
        "variables_json": str(row[9]),
        "tags_json": str(row[10]),
        "source_note": str(row[11] or ""),
        "license_note": str(row[12] or ""),
        "quality_score": int(row[13]),
        "state": state or str(row[14]),
    }


def _payload_snapshot(payload: "PromptTemplatePayload", *, state: str = "active") -> dict[str, Any]:
    return {
        "title": payload.title,
        "category": payload.category,
        "product_context": payload.product_context,
        "platform": payload.platform,
        "style": payload.style,
        "language": payload.language,
        "prompt_text": payload.prompt_text,
        "negative_prompt": payload.negative_prompt,
        "variables_json": json.dumps(payload.variables, ensure_ascii=False, separators=(",", ":")),
        "tags_json": json.dumps(payload.tags, ensure_ascii=False, separators=(",", ":")),
        "source_note": payload.source,
        "license_note": payload.license_note,
        "quality_score": int(payload.quality_score),
        "state": state,
    }


def _snapshot_storage_bytes(snapshot: dict[str, Any]) -> int:
    """Return the byte cost of one current row or immutable snapshot."""
    return SNAPSHOT_ROW_OVERHEAD_BYTES + sum(
        len(str(snapshot.get(field, "")).encode("utf-8")) for field in SNAPSHOT_TEXT_FIELDS
    )


def _stored_table_storage_bytes(conn: Any, *, table: str, account_id: str) -> int:
    # ``table`` is selected only from the two literal Web-owned table names
    # below, never from a request parameter. CAST-to-BLOB measures UTF-8 bytes
    # rather than Unicode code points, matching the actual SQLite payload.
    expression = " + ".join(f"LENGTH(CAST({field} AS BLOB))" for field in SNAPSHOT_TEXT_FIELDS)
    row = conn.execute(
        f"SELECT COALESCE(SUM({SNAPSHOT_ROW_OVERHEAD_BYTES} + {expression}), 0) FROM {table} WHERE account_id=?",
        (account_id,),
    ).fetchone()
    return int(row[0] or 0) if row else 0


def _stored_template_storage_bytes(conn: Any, *, account_id: str) -> int:
    return _stored_table_storage_bytes(conn, table="web_prompt_templates", account_id=account_id) + _stored_table_storage_bytes(
        conn, table="web_prompt_template_versions", account_id=account_id
    )


def _has_template_storage_capacity(conn: Any, *, account_id: str, additional_bytes: int) -> bool:
    return _stored_template_storage_bytes(conn, account_id=account_id) + max(0, int(additional_bytes)) <= MAX_TEMPLATE_STORAGE_BYTES


def _storage_limit_response() -> dict[str, Any]:
    return envelope(
        False,
        "Kho Prompt Library đã đạt giới hạn dung lượng an toàn của Web account. Hãy archive rồi xóa vĩnh viễn template không còn cần thiết trước khi thêm revision mới.",
        status_name="guarded",
        error_code="WEB_PROMPT_TEMPLATE_STORAGE_LIMIT",
    )


def _template_export(row: tuple[Any, ...]) -> dict[str, Any]:
    """Return the sole schema accepted by the bounded JSON importer.

    Deliberately omit account linkage, database identifiers, revisions,
    timestamps and excerpts.  An export can therefore be pasted back into the
    Web import UI without importing authority or stale persistence metadata.
    """
    public = _template_public(row, include_content=True, include_excerpt=False)
    keys = (
        "title", "category", "product_context", "platform", "style", "language",
        "prompt_text", "negative_prompt", "variables", "tags", "source",
        "license_note", "quality_score", "state",
    )
    return {key: public[key] for key in keys}


def _can_add_version(conn: Any, *, template_id: str, account_id: str) -> bool:
    count = conn.execute(
        "SELECT COUNT(*) FROM web_prompt_template_versions WHERE template_id=? AND account_id=?",
        (template_id, account_id),
    ).fetchone()
    return int(count[0] or 0) < MAX_VERSIONS_PER_TEMPLATE


def _version_limit_response() -> dict[str, Any]:
    return envelope(
        False,
        "Template đã đạt giới hạn revision an toàn. Hãy nhân bản template để tiếp tục thử nghiệm mà không làm phình lịch sử cũ.",
        status_name="guarded",
        error_code="WEB_PROMPT_TEMPLATE_VERSION_LIMIT",
    )


def _insert_version(conn: Any, *, template_id: str, account_id: str, revision: int, snapshot: dict[str, Any], created_at: str) -> None:
    conn.execute(
        """INSERT INTO web_prompt_template_versions
           (id, template_id, account_id, revision, title, category, product_context, platform, style,
            language, prompt_text, negative_prompt, variables_json, tags_json, source_note, license_note,
            quality_score, state, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            str(uuid.uuid4()), template_id, account_id, revision, snapshot["title"], snapshot["category"],
            snapshot["product_context"], snapshot["platform"], snapshot["style"], snapshot["language"],
            snapshot["prompt_text"], snapshot["negative_prompt"], snapshot["variables_json"], snapshot["tags_json"],
            snapshot["source_note"], snapshot["license_note"], snapshot["quality_score"], snapshot["state"], created_at,
        ),
    )


def _event(conn: Any, *, account_id: str, template_id: str, action: str, revision: int) -> None:
    conn.execute(
        """INSERT INTO web_prompt_template_events (id, account_id, template_id, action, revision, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), account_id, template_id, action, revision, utc_now()),
    )


def _record_template_audit(conn: Any, *, request: Request, account: dict, action: str, target: str, detail: str) -> None:
    _record_audit(
        conn,
        account_id=str(account.get("id") or "") or None,
        canonical_user_id=str(account.get("canonical_user_id") or "") or None,
        action=action,
        request_id=_request_id(request),
        target=target,
        detail=detail,
    )


def _summary_data(conn: Any, *, account_id: str) -> dict[str, Any]:
    state_rows = conn.execute(
        "SELECT state, COUNT(*) FROM web_prompt_templates WHERE account_id=? GROUP BY state",
        (account_id,),
    ).fetchall()
    variable_count = conn.execute(
        """SELECT COUNT(*) FROM web_prompt_templates
           WHERE account_id=? AND state='active' AND variables_json<>'[]'""",
        (account_id,),
    ).fetchone()
    recent = conn.execute(
        "SELECT MAX(updated_at) FROM web_prompt_templates WHERE account_id=?",
        (account_id,),
    ).fetchone()
    states = {str(row[0]): int(row[1]) for row in state_rows}
    return {
        "templates": {
            "active": states.get("active", 0),
            "archived": states.get("archived", 0),
            "with_variables": int(variable_count[0] or 0) if variable_count else 0,
            "total": sum(states.values()),
        },
        "storage": {
            "used_bytes": _stored_template_storage_bytes(conn, account_id=account_id),
            "limit_bytes": MAX_TEMPLATE_STORAGE_BYTES,
        },
        "latest_updated_at": str(recent[0]) if recent and recent[0] else None,
        "preview_execution": "local_preview_only",
    }


class PromptTemplatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=3, max_length=MAX_TITLE)
    category: str = Field(default="General", max_length=MAX_META)
    product_context: str = Field(default="general", max_length=MAX_META)
    platform: str = Field(default="general", max_length=MAX_META)
    style: str = Field(default="", max_length=MAX_META)
    language: str = Field(default="vi", max_length=MAX_META)
    prompt_text: str = Field(min_length=1, max_length=MAX_PROMPT)
    negative_prompt: str = Field(default="", max_length=MAX_NEGATIVE_PROMPT)
    variables: list[str] = Field(default_factory=list, max_length=MAX_VARIABLES)
    tags: list[str] = Field(default_factory=list, max_length=MAX_TAGS)
    source: str = Field(default="Tự soạn", min_length=2, max_length=MAX_NOTE)
    license_note: str = Field(default="Tôi có quyền sử dụng nội dung này.", min_length=2, max_length=MAX_NOTE)
    quality_score: int = Field(default=50, ge=0, le=100)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _single_line(value, label="Tên template", minimum=3, maximum=MAX_TITLE)

    @field_validator("category", "product_context", "platform", "style", "language")
    @classmethod
    def validate_metadata(cls, value: str, info: Any) -> str:
        labels = {
            "category": "Danh mục", "product_context": "Ngữ cảnh sản phẩm", "platform": "Nền tảng",
            "style": "Phong cách", "language": "Ngôn ngữ",
        }
        return _single_line(value, label=labels.get(str(info.field_name), "Metadata"), minimum=0, maximum=MAX_META, allow_empty=True)

    @field_validator("prompt_text")
    @classmethod
    def validate_prompt_text(cls, value: str) -> str:
        return _content(value, label="Prompt", maximum=MAX_PROMPT)

    @field_validator("negative_prompt")
    @classmethod
    def validate_negative_prompt(cls, value: str) -> str:
        return _content(value, label="Negative prompt", maximum=MAX_NEGATIVE_PROMPT, allow_empty=True)

    @field_validator("variables")
    @classmethod
    def validate_variables(cls, value: list[str]) -> list[str]:
        return _variables(value)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        return _tags(value)

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        return _single_line(value, label="Nguồn", minimum=2, maximum=MAX_NOTE)

    @field_validator("license_note")
    @classmethod
    def validate_license(cls, value: str) -> str:
        return _single_line(value, label="Ghi chú quyền sử dụng", minimum=2, maximum=MAX_NOTE)


class PromptTemplateCreateRequest(PromptTemplatePayload):
    idempotency_key: str = Field(min_length=12, max_length=160)


class PromptTemplateUpdateRequest(PromptTemplatePayload):
    expected_revision: int = Field(ge=1, le=1_000_000)
    idempotency_key: str = Field(min_length=12, max_length=160)


class RevisionMutationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1, le=1_000_000)
    idempotency_key: str = Field(min_length=12, max_length=160)


class RestoreVersionRequest(RevisionMutationRequest):
    revision: int = Field(ge=1, le=1_000_000)


class DuplicateRequest(RevisionMutationRequest):
    title: str = Field(default="", max_length=MAX_TITLE)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _single_line(value, label="Tên bản sao", minimum=0, maximum=MAX_TITLE, allow_empty=True)


class PurgeRequest(RevisionMutationRequest):
    """A deliberate, audited irreversible removal for archived records only."""

    confirm: bool

    @field_validator("confirm")
    @classmethod
    def validate_confirm(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("Cần xác nhận xóa vĩnh viễn template đã archive")
        return value


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1, le=1_000_000)
    values: dict[str, str] = Field(default_factory=dict)

    @field_validator("values")
    @classmethod
    def validate_values(cls, value: dict[str, str]) -> dict[str, str]:
        return _preview_values(value)


class PromptTemplateImportPayload(PromptTemplatePayload):
    """The intentionally small, round-trippable export/import shape.

    IDs, revisions, timestamps, excerpts and account identifiers are never
    imported.  ``state`` is retained so an archive export does not become an
    unexpected collection of active templates on import.
    """

    state: str = Field(default="active", min_length=6, max_length=8)

    @field_validator("state")
    @classmethod
    def validate_state(cls, value: str) -> str:
        state = str(value or "").strip().lower()
        if state not in TEMPLATE_STATES:
            raise ValueError("Trạng thái template import không hợp lệ")
        return state


class ImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    templates: list[PromptTemplateImportPayload] = Field(min_length=1, max_length=MAX_IMPORT_ITEMS)
    idempotency_key: str = Field(min_length=12, max_length=160)


@router.get("/summary")
async def prompt_library_summary(account: dict = Depends(require_account)):
    """Return owner-scoped counts only; content remains in private detail routes."""
    _require_prompt_library_enabled()
    with read_transaction() as conn:
        data = _summary_data(conn, account_id=str(account["id"]))
    return envelope(True, "Tổng quan Prompt Library của Web account hiện tại.", data=data, status_name="read_only")


@router.get("/templates")
async def list_templates(
    limit: int = 30,
    state: str = "active",
    q: str = "",
    category: str = "",
    platform: str = "",
    product_context: str = "",
    tag: str = "",
    account: dict = Depends(require_account),
):
    """Search only private template metadata for the signed Web account."""
    _require_prompt_library_enabled()
    bounded_limit = max(1, min(int(limit), MAX_LIST_LIMIT))
    state_filter = str(state or "active").strip().lower()
    if state_filter not in {*TEMPLATE_STATES, "all"}:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái template không hợp lệ")
    query = _safe_filter(q, label="Từ khóa tìm kiếm", maximum=100)
    category_filter = _safe_filter(category, label="Danh mục", maximum=MAX_META)
    platform_filter = _safe_filter(platform, label="Nền tảng", maximum=MAX_META)
    context_filter = _safe_filter(product_context, label="Ngữ cảnh sản phẩm", maximum=MAX_META)
    tag_filter = _safe_filter(tag, label="Tag", maximum=MAX_TAG_LENGTH)
    account_id = str(account["id"])
    clauses = ["account_id=?"]
    params: list[Any] = [account_id]
    if state_filter != "all":
        clauses.append("state=?")
        params.append(state_filter)
    for column, value in (("category", category_filter), ("platform", platform_filter), ("product_context", context_filter)):
        if value:
            clauses.append(f"{column} LIKE ? ESCAPE '\\'")
            params.append(f"%{_escaped_like(value)}%")
    if tag_filter:
        clauses.append("tags_json LIKE ? ESCAPE '\\'")
        params.append(f"%{_escaped_like(tag_filter)}%")
    if query:
        like = f"%{_escaped_like(query)}%"
        clauses.append(
            "(title LIKE ? ESCAPE '\\' OR category LIKE ? ESCAPE '\\' OR product_context LIKE ? ESCAPE '\\' "
            "OR platform LIKE ? ESCAPE '\\' OR style LIKE ? ESCAPE '\\' OR language LIKE ? ESCAPE '\\' "
            "OR prompt_text LIKE ? ESCAPE '\\' OR negative_prompt LIKE ? ESCAPE '\\' OR tags_json LIKE ? ESCAPE '\\')"
        )
        params.extend([like] * 9)
    with read_transaction() as conn:
        rows = conn.execute(
            f"""SELECT id, title, category, product_context, platform, style, language, prompt_text,
                       negative_prompt, variables_json, tags_json, source_note, license_note, quality_score,
                       state, revision, created_at, updated_at
                FROM web_prompt_templates WHERE {' AND '.join(clauses)}
                ORDER BY CASE state WHEN 'active' THEN 0 ELSE 1 END, quality_score DESC, updated_at DESC, id DESC
                LIMIT ?""",
            (*params, bounded_limit + 1),
        ).fetchall()
        facet_rows = conn.execute(
            """SELECT category, product_context, platform, tags_json FROM web_prompt_templates
               WHERE account_id=? AND state='active' ORDER BY updated_at DESC LIMIT 500""",
            (account_id,),
        ).fetchall()
    has_more = len(rows) > bounded_limit
    facets: dict[str, dict[str, int]] = {"categories": {}, "contexts": {}, "platforms": {}, "tags": {}}
    for row in facet_rows:
        for key, value in (("categories", str(row[0] or "")), ("contexts", str(row[1] or "")), ("platforms", str(row[2] or ""))):
            if value:
                facets[key][value] = facets[key].get(value, 0) + 1
        for item in _decode_list(row[3], limit=MAX_TAGS):
            facets["tags"][item] = facets["tags"].get(item, 0) + 1
    return envelope(
        True,
        "Danh sách template riêng của Web account hiện tại.",
        data={
            "items": [_template_public(tuple(row)) for row in rows[:bounded_limit]],
            "has_more": has_more,
            "facets": {
                name: [{"name": value, "count": count} for value, count in sorted(values.items(), key=lambda pair: (-pair[1], pair[0].casefold()))[:30]]
                for name, values in facets.items()
            },
        },
        status_name="read_only",
    )


@router.post("/templates")
async def create_template(payload: PromptTemplateCreateRequest, request: Request, account: dict = Depends(require_csrf)):
    """Create a private reusable template without starting any AI execution."""
    _require_prompt_library_enabled()
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    snapshot = _payload_snapshot(payload)
    fingerprint = _fingerprint(
        {
            "title": payload.title,
            "prompt_sha256": _content_hash(payload.prompt_text),
            "negative_prompt_sha256": _content_hash(payload.negative_prompt),
            "variables": payload.variables,
            "tags": payload.tags,
            "metadata": [payload.category, payload.product_context, payload.platform, payload.style, payload.language],
            "source_sha256": _content_hash(payload.source),
            "license_sha256": _content_hash(payload.license_note),
            "quality_score": payload.quality_score,
        }
    )

    def operation(conn: Any) -> dict[str, Any]:
        count = conn.execute("SELECT COUNT(*) FROM web_prompt_templates WHERE account_id=? AND state='active'", (account_id,)).fetchone()
        if int(count[0] or 0) >= MAX_TEMPLATES_PER_ACCOUNT:
            return envelope(False, "Đã đạt giới hạn template active của Web account. Hãy archive template cũ trước.", status_name="guarded", error_code="WEB_PROMPT_TEMPLATE_LIMIT")
        if not _has_template_storage_capacity(
            conn, account_id=account_id, additional_bytes=_snapshot_storage_bytes(snapshot) * 2
        ):
            return _storage_limit_response()
        template_id = str(uuid.uuid4())
        now = utc_now()
        conn.execute(
            """INSERT INTO web_prompt_templates
               (id, account_id, title, category, product_context, platform, style, language, prompt_text,
                negative_prompt, variables_json, tags_json, source_note, license_note, quality_score, state,
                revision, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', 1, ?, ?)""",
            (
                template_id, account_id, snapshot["title"], snapshot["category"], snapshot["product_context"],
                snapshot["platform"], snapshot["style"], snapshot["language"], snapshot["prompt_text"],
                snapshot["negative_prompt"], snapshot["variables_json"], snapshot["tags_json"], snapshot["source_note"],
                snapshot["license_note"], snapshot["quality_score"], now, now,
            ),
        )
        _insert_version(conn, template_id=template_id, account_id=account_id, revision=1, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, template_id=template_id, action="template_created", revision=1)
        _record_template_audit(conn, request=request, account=account, action="web.prompt_library.create", target=template_id, detail="web-owned prompt template created")
        row = (template_id, snapshot["title"], snapshot["category"], snapshot["product_context"], snapshot["platform"], snapshot["style"], snapshot["language"], snapshot["prompt_text"], snapshot["negative_prompt"], snapshot["variables_json"], snapshot["tags_json"], snapshot["source_note"], snapshot["license_note"], snapshot["quality_score"], "active", 1, now, now)
        return envelope(True, "Đã lưu template vào Prompt Library.", data={"template": _template_public(row, include_excerpt=False)}, status_name="completed")

    return _idempotent(f"web-prompt-library:{account_id}:template:create", account_id, key, fingerprint, operation)


def _detail(conn: Any, *, template_id: str, account_id: str) -> dict[str, Any] | None:
    row = _template_row(conn, template_id=template_id, account_id=account_id)
    if not row:
        return None
    versions = conn.execute(
        """SELECT revision, title, category, product_context, platform, style, language, prompt_text,
                  negative_prompt, variables_json, tags_json, source_note, license_note, quality_score, state, created_at
           FROM web_prompt_template_versions WHERE template_id=? AND account_id=?
           ORDER BY revision DESC LIMIT 100""",
        (template_id, account_id),
    ).fetchall()
    return {"template": _template_public(row, include_content=True), "versions": [_version_public(tuple(version)) for version in versions]}


@router.get("/templates/{template_id}")
async def get_template(template_id: str, account: dict = Depends(require_account)):
    _require_prompt_library_enabled()
    template_id = _uuid(template_id, label="Mã template")
    with read_transaction() as conn:
        detail = _detail(conn, template_id=template_id, account_id=str(account["id"]))
    if not detail:
        return _template_not_found()
    return envelope(True, "Chi tiết template riêng của Web account hiện tại.", data=detail, status_name="read_only")


@router.get("/templates/{template_id}/versions")
async def template_versions(template_id: str, account: dict = Depends(require_account)):
    _require_prompt_library_enabled()
    template_id = _uuid(template_id, label="Mã template")
    account_id = str(account["id"])
    with read_transaction() as conn:
        row = _template_row(conn, template_id=template_id, account_id=account_id)
        if not row:
            return _template_not_found()
        rows = conn.execute(
            """SELECT revision, title, category, product_context, platform, style, language, prompt_text,
                      negative_prompt, variables_json, tags_json, source_note, license_note, quality_score, state, created_at
               FROM web_prompt_template_versions WHERE template_id=? AND account_id=?
               ORDER BY revision DESC LIMIT 100""",
            (template_id, account_id),
        ).fetchall()
    return envelope(True, "Lịch sử phiên bản template riêng tư.", data={"items": [_version_public(tuple(row), include_content=True) for row in rows]}, status_name="read_only")


@router.patch("/templates/{template_id}")
async def update_template(template_id: str, payload: PromptTemplateUpdateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_prompt_library_enabled()
    template_id = _uuid(template_id, label="Mã template")
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    snapshot = _payload_snapshot(payload)
    fingerprint = _fingerprint(
        {
            "expected_revision": payload.expected_revision,
            "title": payload.title,
            "prompt_sha256": _content_hash(payload.prompt_text),
            "negative_prompt_sha256": _content_hash(payload.negative_prompt),
            "variables": payload.variables,
            "tags": payload.tags,
            "metadata": [payload.category, payload.product_context, payload.platform, payload.style, payload.language],
            "source_sha256": _content_hash(payload.source),
            "license_sha256": _content_hash(payload.license_note),
            "quality_score": payload.quality_score,
        }
    )

    def operation(conn: Any) -> dict[str, Any]:
        current = _template_row(conn, template_id=template_id, account_id=account_id)
        if not current:
            return _template_not_found()
        if str(current[14]) != "active":
            return envelope(False, "Template đã archive. Hãy khôi phục trước khi chỉnh sửa.", status_name="guarded", error_code="WEB_PROMPT_TEMPLATE_ARCHIVED")
        if int(current[15]) != payload.expected_revision:
            return envelope(False, "Template đã có phiên bản mới. Hãy tải lại trước khi lưu.", data={"current_revision": int(current[15])}, status_name="guarded", error_code="WEB_PROMPT_TEMPLATE_CONFLICT")
        if not _can_add_version(conn, template_id=template_id, account_id=account_id):
            return _version_limit_response()
        current_snapshot = _snapshot_from_row(current)
        additional_bytes = (_snapshot_storage_bytes(snapshot) * 2) - _snapshot_storage_bytes(current_snapshot)
        if not _has_template_storage_capacity(conn, account_id=account_id, additional_bytes=additional_bytes):
            return _storage_limit_response()
        next_revision = int(current[15]) + 1
        now = utc_now()
        conn.execute(
            """UPDATE web_prompt_templates SET title=?, category=?, product_context=?, platform=?, style=?, language=?,
               prompt_text=?, negative_prompt=?, variables_json=?, tags_json=?, source_note=?, license_note=?,
               quality_score=?, revision=?, updated_at=?
               WHERE id=? AND account_id=? AND revision=? AND state='active'""",
            (
                snapshot["title"], snapshot["category"], snapshot["product_context"], snapshot["platform"], snapshot["style"], snapshot["language"],
                snapshot["prompt_text"], snapshot["negative_prompt"], snapshot["variables_json"], snapshot["tags_json"], snapshot["source_note"], snapshot["license_note"],
                snapshot["quality_score"], next_revision, now, template_id, account_id, int(current[15]),
            ),
        )
        _insert_version(conn, template_id=template_id, account_id=account_id, revision=next_revision, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, template_id=template_id, action="template_updated", revision=next_revision)
        _record_template_audit(conn, request=request, account=account, action="web.prompt_library.update", target=template_id, detail=f"web-owned prompt template revision:{next_revision}")
        row = (template_id, snapshot["title"], snapshot["category"], snapshot["product_context"], snapshot["platform"], snapshot["style"], snapshot["language"], snapshot["prompt_text"], snapshot["negative_prompt"], snapshot["variables_json"], snapshot["tags_json"], snapshot["source_note"], snapshot["license_note"], snapshot["quality_score"], "active", next_revision, current[16], now)
        return envelope(True, "Đã lưu phiên bản template mới.", data={"template": _template_public(row, include_excerpt=False)}, status_name="completed")

    return _idempotent(f"web-prompt-library:{account_id}:template:{template_id}:update", account_id, key, fingerprint, operation)


def _state_transition(*, template_id: str, payload: RevisionMutationRequest, request: Request, account: dict, action: str) -> dict[str, Any]:
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    fingerprint = _fingerprint({"expected_revision": payload.expected_revision, "action": action})
    target_state = "archived" if action == "archive" else "active"

    def operation(conn: Any) -> dict[str, Any]:
        current = _template_row(conn, template_id=template_id, account_id=account_id)
        if not current:
            return _template_not_found()
        if int(current[15]) != payload.expected_revision:
            return envelope(False, "Template đã có phiên bản mới. Hãy tải lại trước khi tiếp tục.", data={"current_revision": int(current[15])}, status_name="guarded", error_code="WEB_PROMPT_TEMPLATE_CONFLICT")
        if str(current[14]) == target_state:
            return envelope(False, "Trạng thái template không thể chuyển đổi theo thao tác này.", status_name="guarded", error_code="WEB_PROMPT_TEMPLATE_STATE_INVALID")
        if action == "restore":
            active_count = conn.execute(
                "SELECT COUNT(*) FROM web_prompt_templates WHERE account_id=? AND state='active'",
                (account_id,),
            ).fetchone()
            if int(active_count[0] or 0) >= MAX_TEMPLATES_PER_ACCOUNT:
                return envelope(
                    False,
                    "Đã đạt giới hạn template active của Web account. Hãy archive template khác trước khi khôi phục.",
                    status_name="guarded",
                    error_code="WEB_PROMPT_TEMPLATE_LIMIT",
                )
        if action == "archive":
            archived_count = conn.execute(
                "SELECT COUNT(*) FROM web_prompt_templates WHERE account_id=? AND state='archived'",
                (account_id,),
            ).fetchone()
            if int(archived_count[0] or 0) >= MAX_ARCHIVED_TEMPLATES_PER_ACCOUNT:
                return envelope(
                    False,
                    "Kho archive đã đạt giới hạn an toàn. Hãy xuất và dọn kho trước khi archive thêm.",
                    status_name="guarded",
                    error_code="WEB_PROMPT_TEMPLATE_ARCHIVE_LIMIT",
                )
        next_revision = int(current[15]) + 1
        now = utc_now()
        snapshot = _snapshot_from_row(current, state=target_state)
        current_snapshot = _snapshot_from_row(current)
        additional_bytes = (_snapshot_storage_bytes(snapshot) * 2) - _snapshot_storage_bytes(current_snapshot)
        can_record_snapshot = _can_add_version(conn, template_id=template_id, account_id=account_id) and _has_template_storage_capacity(
            conn, account_id=account_id, additional_bytes=additional_bytes
        )
        # Archive remains a durable cleanup path even when history capacity is
        # exhausted: its content is unchanged, so the lifecycle/audit event is
        # sufficient while the user can purge the archived record to reclaim
        # bytes. Restore, however, must retain a complete immutable snapshot.
        if action != "archive" and not _can_add_version(conn, template_id=template_id, account_id=account_id):
            return _version_limit_response()
        if action != "archive" and not _has_template_storage_capacity(
            conn, account_id=account_id, additional_bytes=additional_bytes
        ):
            return _storage_limit_response()
        snapshot_recorded = can_record_snapshot
        conn.execute(
            """UPDATE web_prompt_templates SET state=?, revision=?, updated_at=?
               WHERE id=? AND account_id=? AND revision=?""",
            (target_state, next_revision, now, template_id, account_id, int(current[15])),
        )
        if snapshot_recorded:
            _insert_version(conn, template_id=template_id, account_id=account_id, revision=next_revision, snapshot=snapshot, created_at=now)
        _event(
            conn,
            account_id=account_id,
            template_id=template_id,
            action=(f"template_{action}d" if action == "archive" else "template_restored") + ("" if snapshot_recorded else "_without_snapshot"),
            revision=next_revision,
        )
        _record_template_audit(
            conn,
            request=request,
            account=account,
            action=f"web.prompt_library.{action}",
            target=template_id,
            detail=f"web-owned prompt template state:{target_state};history_snapshot={'recorded' if snapshot_recorded else 'skipped_at_capacity'}",
        )
        row = (template_id, snapshot["title"], snapshot["category"], snapshot["product_context"], snapshot["platform"], snapshot["style"], snapshot["language"], snapshot["prompt_text"], snapshot["negative_prompt"], snapshot["variables_json"], snapshot["tags_json"], snapshot["source_note"], snapshot["license_note"], snapshot["quality_score"], target_state, next_revision, current[16], now)
        message = "Đã archive template." if action == "archive" else "Đã khôi phục template vào Prompt Library."
        return envelope(True, message, data={"template": _template_public(row, include_excerpt=False), "history_snapshot_recorded": snapshot_recorded}, status_name="completed")

    return _idempotent(f"web-prompt-library:{account_id}:template:{template_id}:{action}", account_id, key, fingerprint, operation)


@router.post("/templates/{template_id}/archive")
async def archive_template(template_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_prompt_library_enabled()
    return _state_transition(template_id=_uuid(template_id, label="Mã template"), payload=payload, request=request, account=account, action="archive")


@router.post("/templates/{template_id}/restore")
async def restore_template(template_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_prompt_library_enabled()
    return _state_transition(template_id=_uuid(template_id, label="Mã template"), payload=payload, request=request, account=account, action="restore")


@router.post("/templates/{template_id}/duplicate")
async def duplicate_template(template_id: str, payload: DuplicateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_prompt_library_enabled()
    template_id = _uuid(template_id, label="Mã template")
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    fingerprint = _fingerprint({"expected_revision": payload.expected_revision, "title": payload.title})

    def operation(conn: Any) -> dict[str, Any]:
        source = _template_row(conn, template_id=template_id, account_id=account_id)
        if not source:
            return _template_not_found()
        if str(source[14]) != "active":
            return envelope(False, "Chỉ template active mới có thể nhân bản.", status_name="guarded", error_code="WEB_PROMPT_TEMPLATE_ARCHIVED")
        if int(source[15]) != payload.expected_revision:
            return envelope(False, "Template đã có phiên bản mới. Hãy tải lại trước khi nhân bản.", data={"current_revision": int(source[15])}, status_name="guarded", error_code="WEB_PROMPT_TEMPLATE_CONFLICT")
        count = conn.execute("SELECT COUNT(*) FROM web_prompt_templates WHERE account_id=? AND state='active'", (account_id,)).fetchone()
        if int(count[0] or 0) >= MAX_TEMPLATES_PER_ACCOUNT:
            return envelope(False, "Đã đạt giới hạn template active của Web account.", status_name="guarded", error_code="WEB_PROMPT_TEMPLATE_LIMIT")
        snapshot = _snapshot_from_row(source, state="active")
        snapshot["title"] = payload.title or f"{snapshot['title']} — bản sao"
        if not _has_template_storage_capacity(
            conn, account_id=account_id, additional_bytes=_snapshot_storage_bytes(snapshot) * 2
        ):
            return _storage_limit_response()
        new_id = str(uuid.uuid4())
        now = utc_now()
        conn.execute(
            """INSERT INTO web_prompt_templates
               (id, account_id, title, category, product_context, platform, style, language, prompt_text,
                negative_prompt, variables_json, tags_json, source_note, license_note, quality_score, state,
                revision, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', 1, ?, ?)""",
            (new_id, account_id, snapshot["title"], snapshot["category"], snapshot["product_context"], snapshot["platform"], snapshot["style"], snapshot["language"], snapshot["prompt_text"], snapshot["negative_prompt"], snapshot["variables_json"], snapshot["tags_json"], snapshot["source_note"], snapshot["license_note"], snapshot["quality_score"], now, now),
        )
        _insert_version(conn, template_id=new_id, account_id=account_id, revision=1, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, template_id=new_id, action="template_duplicated", revision=1)
        _record_template_audit(conn, request=request, account=account, action="web.prompt_library.duplicate", target=new_id, detail=f"web-owned prompt template duplicated_from:{template_id}")
        row = (new_id, snapshot["title"], snapshot["category"], snapshot["product_context"], snapshot["platform"], snapshot["style"], snapshot["language"], snapshot["prompt_text"], snapshot["negative_prompt"], snapshot["variables_json"], snapshot["tags_json"], snapshot["source_note"], snapshot["license_note"], snapshot["quality_score"], "active", 1, now, now)
        return envelope(True, "Đã tạo bản sao template trong Prompt Library.", data={"template": _template_public(row, include_excerpt=False)}, status_name="completed")

    return _idempotent(f"web-prompt-library:{account_id}:template:{template_id}:duplicate", account_id, key, fingerprint, operation)


@router.post("/templates/{template_id}/purge")
async def purge_archived_template(template_id: str, payload: PurgeRequest, request: Request, account: dict = Depends(require_csrf)):
    """Irreversibly remove an archived template after explicit confirmation."""
    _require_prompt_library_enabled()
    template_id = _uuid(template_id, label="Mã template")
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    fingerprint = _fingerprint({"expected_revision": payload.expected_revision, "confirm": True, "action": "purge"})

    def operation(conn: Any) -> dict[str, Any]:
        current = _template_row(conn, template_id=template_id, account_id=account_id)
        if not current:
            return _template_not_found()
        if str(current[14]) != "archived":
            return envelope(False, "Chỉ template đã archive mới có thể xóa vĩnh viễn.", status_name="guarded", error_code="WEB_PROMPT_TEMPLATE_PURGE_REQUIRES_ARCHIVE")
        if int(current[15]) != payload.expected_revision:
            return envelope(False, "Template đã có phiên bản mới. Hãy tải lại trước khi xóa vĩnh viễn.", data={"current_revision": int(current[15])}, status_name="guarded", error_code="WEB_PROMPT_TEMPLATE_CONFLICT")
        conn.execute("DELETE FROM web_prompt_template_events WHERE template_id=? AND account_id=?", (template_id, account_id))
        conn.execute("DELETE FROM web_prompt_template_versions WHERE template_id=? AND account_id=?", (template_id, account_id))
        deleted = conn.execute(
            "DELETE FROM web_prompt_templates WHERE id=? AND account_id=? AND state='archived' AND revision=?",
            (template_id, account_id, int(current[15])),
        )
        if int(deleted.rowcount or 0) != 1:
            # Raising makes transaction() roll back the already-issued child
            # deletes instead of committing a partial irreversible purge.
            raise HTTPException(status_code=409, detail="Template đã thay đổi trước khi xóa vĩnh viễn. Hãy tải lại.")
        _record_template_audit(conn, request=request, account=account, action="web.prompt_library.purge", target=template_id, detail="web-owned archived prompt template purged")
        return envelope(True, "Đã xóa vĩnh viễn template đã archive cùng version history riêng tư.", data={"template_id": template_id, "purged": True}, status_name="completed")

    return _idempotent(f"web-prompt-library:{account_id}:template:{template_id}:purge", account_id, key, fingerprint, operation)


@router.post("/templates/{template_id}/restore-version")
async def restore_template_version(template_id: str, payload: RestoreVersionRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_prompt_library_enabled()
    template_id = _uuid(template_id, label="Mã template")
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    fingerprint = _fingerprint({"expected_revision": payload.expected_revision, "restore_revision": payload.revision})

    def operation(conn: Any) -> dict[str, Any]:
        current = _template_row(conn, template_id=template_id, account_id=account_id)
        if not current:
            return _template_not_found()
        if str(current[14]) != "active":
            return envelope(False, "Template đã archive. Hãy khôi phục trước khi khôi phục phiên bản.", status_name="guarded", error_code="WEB_PROMPT_TEMPLATE_ARCHIVED")
        if int(current[15]) != payload.expected_revision:
            return envelope(False, "Template đã có phiên bản mới. Hãy tải lại trước khi khôi phục.", data={"current_revision": int(current[15])}, status_name="guarded", error_code="WEB_PROMPT_TEMPLATE_CONFLICT")
        if not _can_add_version(conn, template_id=template_id, account_id=account_id):
            return _version_limit_response()
        source = conn.execute(
            """SELECT revision, title, category, product_context, platform, style, language, prompt_text,
                      negative_prompt, variables_json, tags_json, source_note, license_note, quality_score, state, created_at
               FROM web_prompt_template_versions WHERE template_id=? AND account_id=? AND revision=?""",
            (template_id, account_id, payload.revision),
        ).fetchone()
        if not source:
            return envelope(False, "Không tìm thấy phiên bản template thuộc Web account hiện tại.", status_name="guarded", error_code="WEB_PROMPT_TEMPLATE_VERSION_NOT_FOUND")
        source_tuple = tuple(source)
        snapshot = {
            "title": str(source_tuple[1]), "category": str(source_tuple[2] or ""), "product_context": str(source_tuple[3] or ""),
            "platform": str(source_tuple[4] or ""), "style": str(source_tuple[5] or ""), "language": str(source_tuple[6] or ""),
            "prompt_text": str(source_tuple[7]), "negative_prompt": str(source_tuple[8] or ""), "variables_json": str(source_tuple[9]),
            "tags_json": str(source_tuple[10]), "source_note": str(source_tuple[11] or ""), "license_note": str(source_tuple[12] or ""),
            "quality_score": int(source_tuple[13]), "state": "active",
        }
        current_snapshot = _snapshot_from_row(current)
        additional_bytes = (_snapshot_storage_bytes(snapshot) * 2) - _snapshot_storage_bytes(current_snapshot)
        if not _has_template_storage_capacity(conn, account_id=account_id, additional_bytes=additional_bytes):
            return _storage_limit_response()
        next_revision = int(current[15]) + 1
        now = utc_now()
        conn.execute(
            """UPDATE web_prompt_templates SET title=?, category=?, product_context=?, platform=?, style=?, language=?,
               prompt_text=?, negative_prompt=?, variables_json=?, tags_json=?, source_note=?, license_note=?,
               quality_score=?, state='active', revision=?, updated_at=?
               WHERE id=? AND account_id=? AND revision=? AND state='active'""",
            (snapshot["title"], snapshot["category"], snapshot["product_context"], snapshot["platform"], snapshot["style"], snapshot["language"], snapshot["prompt_text"], snapshot["negative_prompt"], snapshot["variables_json"], snapshot["tags_json"], snapshot["source_note"], snapshot["license_note"], snapshot["quality_score"], next_revision, now, template_id, account_id, int(current[15])),
        )
        _insert_version(conn, template_id=template_id, account_id=account_id, revision=next_revision, snapshot=snapshot, created_at=now)
        _event(conn, account_id=account_id, template_id=template_id, action="template_version_restored", revision=next_revision)
        _record_template_audit(conn, request=request, account=account, action="web.prompt_library.restore_version", target=template_id, detail=f"web-owned prompt template restored_from:{payload.revision}")
        row = (template_id, snapshot["title"], snapshot["category"], snapshot["product_context"], snapshot["platform"], snapshot["style"], snapshot["language"], snapshot["prompt_text"], snapshot["negative_prompt"], snapshot["variables_json"], snapshot["tags_json"], snapshot["source_note"], snapshot["license_note"], snapshot["quality_score"], "active", next_revision, current[16], now)
        return envelope(True, "Đã khôi phục phiên bản thành một revision mới.", data={"template": _template_public(row, include_excerpt=False)}, status_name="completed")

    return _idempotent(f"web-prompt-library:{account_id}:template:{template_id}:restore-version:{payload.revision}", account_id, key, fingerprint, operation)


@router.post("/templates/{template_id}/preview")
async def preview_template(template_id: str, payload: PreviewRequest, account: dict = Depends(require_csrf)):
    """Render declared ``{{variables}}`` locally; this is never an AI request."""
    _require_prompt_library_enabled()
    template_id = _uuid(template_id, label="Mã template")
    account_id = str(account["id"])
    with read_transaction() as conn:
        row = _template_row(conn, template_id=template_id, account_id=account_id)
    if not row:
        return _template_not_found()
    if str(row[14]) != "active":
        return envelope(
            False,
            "Template đã archive. Hãy khôi phục trước khi tạo preview cục bộ.",
            status_name="guarded",
            error_code="WEB_PROMPT_TEMPLATE_ARCHIVED",
        )
    if int(row[15]) != payload.expected_revision:
        return envelope(False, "Template đã có phiên bản mới. Hãy tải lại trước khi preview.", data={"current_revision": int(row[15])}, status_name="guarded", error_code="WEB_PROMPT_TEMPLATE_CONFLICT")
    declared = _decode_list(row[9], limit=MAX_VARIABLES)
    declared_names = frozenset(declared)
    unexpected = sorted(set(payload.values) - declared_names)
    if unexpected:
        raise HTTPException(status_code=422, detail="Preview chỉ nhận variables đã khai báo trong template")

    def render_local(source: str) -> str | None:
        """Substitute each original placeholder once without re-parsing values."""
        pieces: list[str] = []
        cursor = 0
        output_size = 0
        for match in PLACEHOLDER_PATTERN.finditer(source):
            literal = source[cursor:match.start()]
            name = match.group(1)
            replacement = payload.values[name] if name in declared_names and name in payload.values else match.group(0)
            output_size += len(literal) + len(replacement)
            if output_size > MAX_PREVIEW_OUTPUT:
                return None
            pieces.extend((literal, replacement))
            cursor = match.end()
        tail = source[cursor:]
        output_size += len(tail)
        if output_size > MAX_PREVIEW_OUTPUT:
            return None
        pieces.append(tail)
        return "".join(pieces)

    rendered = render_local(str(row[7]))
    rendered_negative = render_local(str(row[8] or ""))
    if rendered is None or rendered_negative is None:
        return envelope(
            False,
            "Preview vượt giới hạn kích thước an toàn. Hãy rút gọn prompt hoặc giá trị variable.",
            status_name="guarded",
            error_code="WEB_PROMPT_TEMPLATE_PREVIEW_LIMIT",
        )
    return envelope(
        True,
        "Preview cục bộ đã được tạo. Không có AI execution, provider call, job hoặc charge.",
        data={"prompt_text": rendered, "negative_prompt": rendered_negative, "execution": "local_preview_only"},
        status_name="read_only",
    )


@router.post("/import")
async def import_templates(payload: ImportRequest, request: Request, account: dict = Depends(require_csrf)):
    """Append a bounded JSON payload; URL fetch and file-path import are forbidden."""
    _require_prompt_library_enabled()
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    snapshots = [_payload_snapshot(item, state=item.state) for item in payload.templates]
    fingerprint = _fingerprint(
        {
            "count": len(snapshots),
            "templates": [
                {
                    "title": item["title"], "prompt_sha256": _content_hash(item["prompt_text"]),
                    "negative_prompt_sha256": _content_hash(item["negative_prompt"]), "variables_json": item["variables_json"],
                    "tags_json": item["tags_json"], "metadata": [item["category"], item["product_context"], item["platform"], item["style"], item["language"]],
                    "source_sha256": _content_hash(item["source_note"]), "license_sha256": _content_hash(item["license_note"]), "quality_score": item["quality_score"],
                    "state": item["state"],
                }
                for item in snapshots
            ],
        }
    )

    def operation(conn: Any) -> dict[str, Any]:
        active_requested = sum(1 for snapshot in snapshots if snapshot["state"] == "active")
        archived_requested = sum(1 for snapshot in snapshots if snapshot["state"] == "archived")
        active_count = conn.execute(
            "SELECT COUNT(*) FROM web_prompt_templates WHERE account_id=? AND state='active'",
            (account_id,),
        ).fetchone()
        archived_count = conn.execute(
            "SELECT COUNT(*) FROM web_prompt_templates WHERE account_id=? AND state='archived'",
            (account_id,),
        ).fetchone()
        if int(active_count[0] or 0) + active_requested > MAX_TEMPLATES_PER_ACCOUNT:
            return envelope(False, "Import vượt giới hạn template active của Web account.", status_name="guarded", error_code="WEB_PROMPT_TEMPLATE_LIMIT")
        if int(archived_count[0] or 0) + archived_requested > MAX_ARCHIVED_TEMPLATES_PER_ACCOUNT:
            return envelope(False, "Import vượt giới hạn kho archive của Web account.", status_name="guarded", error_code="WEB_PROMPT_TEMPLATE_ARCHIVE_LIMIT")
        if not _has_template_storage_capacity(
            conn,
            account_id=account_id,
            additional_bytes=sum(_snapshot_storage_bytes(snapshot) * 2 for snapshot in snapshots),
        ):
            return _storage_limit_response()
        now = utc_now()
        imported: list[dict[str, Any]] = []
        for snapshot in snapshots:
            template_id = str(uuid.uuid4())
            conn.execute(
                """INSERT INTO web_prompt_templates
                   (id, account_id, title, category, product_context, platform, style, language, prompt_text,
                    negative_prompt, variables_json, tags_json, source_note, license_note, quality_score, state,
                    revision, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)""",
                (template_id, account_id, snapshot["title"], snapshot["category"], snapshot["product_context"], snapshot["platform"], snapshot["style"], snapshot["language"], snapshot["prompt_text"], snapshot["negative_prompt"], snapshot["variables_json"], snapshot["tags_json"], snapshot["source_note"], snapshot["license_note"], snapshot["quality_score"], snapshot["state"], now, now),
            )
            _insert_version(conn, template_id=template_id, account_id=account_id, revision=1, snapshot=snapshot, created_at=now)
            _event(conn, account_id=account_id, template_id=template_id, action="template_imported", revision=1)
            row = (template_id, snapshot["title"], snapshot["category"], snapshot["product_context"], snapshot["platform"], snapshot["style"], snapshot["language"], snapshot["prompt_text"], snapshot["negative_prompt"], snapshot["variables_json"], snapshot["tags_json"], snapshot["source_note"], snapshot["license_note"], snapshot["quality_score"], snapshot["state"], 1, now, now)
            imported.append(_template_public(row, include_excerpt=False))
        _record_template_audit(conn, request=request, account=account, action="web.prompt_library.import", target="batch", detail=f"web-owned prompt templates imported:{len(imported)}")
        return envelope(True, f"Đã import {len(imported)} template vào Prompt Library.", data={"items": imported, "imported": len(imported)}, status_name="completed")

    return _idempotent(f"web-prompt-library:{account_id}:import", account_id, key, fingerprint, operation)


@router.post("/export")
async def export_templates(account: dict = Depends(require_csrf)):
    """Return a CSRF-protected private JSON attachment without a storage artifact."""
    _require_prompt_library_enabled()
    account_id = str(account["id"])
    with read_transaction() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM web_prompt_templates WHERE account_id=?",
            (account_id,),
        ).fetchone()
        if int(count[0] or 0) > MAX_TOTAL_TEMPLATES_PER_ACCOUNT:
            return Response(
                content=json.dumps(
                    envelope(
                        False,
                        "Kho template vượt giới hạn export an toàn. Hãy liên hệ vận hành để dọn dữ liệu trước khi export.",
                        status_name="guarded",
                        error_code="WEB_PROMPT_LIBRARY_EXPORT_LIMIT",
                    ),
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                media_type="application/json",
                status_code=413,
            )
        rows = conn.execute(
            """SELECT id, title, category, product_context, platform, style, language, prompt_text,
                      negative_prompt, variables_json, tags_json, source_note, license_note, quality_score,
                      state, revision, created_at, updated_at
               FROM web_prompt_templates WHERE account_id=? ORDER BY updated_at DESC, id DESC""",
            (account_id,),
        )
        exported_at = utc_now()
        prefix = (
            b'{"schema":'
            + json.dumps("toan-aas-web-prompt-library-v1", ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            + b',"exported_at":'
            + json.dumps(exported_at, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            + b',"templates":['
        )
        suffix = b"]}"
        parts = [prefix]
        projected_bytes = len(prefix) + len(suffix)
        wrote_item = False
        for row in rows:
            encoded = json.dumps(_template_export(tuple(row)), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            separator = b"," if wrote_item else b""
            if projected_bytes + len(separator) + len(encoded) > MAX_EXPORT_BYTES:
                return Response(
                    content=json.dumps(
                        envelope(
                            False,
                            "Bản export vượt giới hạn dung lượng an toàn. Hãy archive và xóa vĩnh viễn template không còn cần thiết trước khi export.",
                            status_name="guarded",
                            error_code="WEB_PROMPT_LIBRARY_EXPORT_LIMIT",
                        ),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                    media_type="application/json",
                    status_code=413,
                )
            parts.extend((separator, encoded))
            projected_bytes += len(separator) + len(encoded)
            wrote_item = True
    content = b"".join((*parts, suffix))
    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="toan-aas-prompt-library.json"',
            "Cache-Control": "no-store, private",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "sandbox",
        },
    )


@router.get("/events")
async def prompt_library_events(limit: int = 40, account: dict = Depends(require_account)):
    """Expose an audit-safe owner timeline without raw prompt/license content."""
    _require_prompt_library_enabled()
    bounded_limit = max(1, min(int(limit), 100))
    account_id = str(account["id"])
    with read_transaction() as conn:
        rows = conn.execute(
            """SELECT id, template_id, action, revision, created_at FROM web_prompt_template_events
               WHERE account_id=? ORDER BY created_at DESC, id DESC LIMIT ?""",
            (account_id, bounded_limit),
        ).fetchall()
    return envelope(
        True,
        "Hoạt động Prompt Library của Web account hiện tại.",
        data={"items": [{"id": str(row[0]), "template_id": str(row[1]), "action": str(row[2]), "revision": int(row[3]), "created_at": str(row[4])} for row in rows]},
        status_name="read_only",
    )
