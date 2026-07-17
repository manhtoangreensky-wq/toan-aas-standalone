"""Web-native Admin Governance & Internal Documents Center.

This is a deliberately small, standalone Admin ERP record system.  It does
not read or write the Telegram Bot's ``internal_documents`` table, Telegram
file IDs, Bot paths, private bridge, Xu/PayOS, providers, jobs, customer,
finance, HR or contract records.  A governance record is an internal Web
draft/review record only: it is never auto-published, exported, notified or
hard-deleted by this module.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import re
import uuid
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from copyfast_auth import _record_audit, _request_id, current_session, envelope, require_admin, require_admin_csrf
from copyfast_db import ensure_copyfast_schema, governance_documents_enabled, read_transaction, transaction, utc_now


router = APIRouter(prefix="/api/v1/admin/governance", tags=["Web Governance Documents"])


POLICY_VERSION = "web_governance_documents_v1"
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
TAG_PATTERN = re.compile(r"^[\wÀ-ỹà-ỹ][\wÀ-ỹà-ỹ ._/-]{0,47}$", re.UNICODE)

# DLP intentionally checks concrete secret/file reference shapes, not ordinary
# policy-language words such as "password policy" or "API key rotation".  The
# browser receives one generic denial message and no matched fragment is ever
# written to audit/event data.
PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN(?: [A-Z0-9][A-Z0-9 ]*)? PRIVATE KEY-----", re.IGNORECASE)
BEARER_PATTERN = re.compile(r"\bbearer\s+[A-Za-z0-9._~+/=-]{8,}\b", re.IGNORECASE)
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"\b(?:password|passphrase|api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|"
    r"client[ _-]?secret|secret(?:[ _-]?key)?|authorization)\b\s*"
    r"(?:[:=]|\bis\b)\s*(?:bearer\s+)?[A-Za-z0-9_./+=:-]{6,}",
    re.IGNORECASE,
)
KNOWN_SECRET_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(?:sk|pk|rk)_[A-Za-z0-9_-]{16,}|github_pat_[A-Za-z0-9_]{16,}|"
    r"gh[pousr]_[A-Za-z0-9]{16,}|xox[bpars]-[A-Za-z0-9-]{16,}|"
    r"(?:AKIA|ASIA)[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}\.",
    re.IGNORECASE,
)
TELEGRAM_FILE_REFERENCE_PATTERN = re.compile(
    r"\b(?:telegram[ _-]?(?:file|bot)?[ _-]?(?:id|path)|file[ _-]?id|tg[ _-]?file[ _-]?(?:id|path))\b"
    r"\s*(?:[:=]|\bis\b)\s*[^\s]{8,}",
    re.IGNORECASE,
)
TELEGRAM_FILE_PATH_PATTERN = re.compile(
    r"(?:tg://|telegram://|api\.telegram\.org/file/|"
    r"\btelegram[ _-]?(?:file|bot)?[ _-]?path\s*(?:[:=]|\bis\b)\s*[^\s]{3,})",
    re.IGNORECASE,
)
# Internal governance records are not a vault for local-machine/server paths.
# Keep this deliberately targeted to absolute Windows and common server roots:
# ordinary documentation such as a public URL or a relative policy section
# must not be rejected merely because it contains a slash.
FILESYSTEM_PATH_PATTERN = re.compile(
    r"(?:^|[\s\"'`(])(?:[A-Za-z]:[\\/]|/(?:app|bin|boot|data|etc|home|lib|mnt|opt|private|root|run|srv|tmp|usr|var|windows|users)(?:[\\/]|$))",
    re.IGNORECASE,
)

DOCUMENT_STATES = frozenset({"draft", "in_review", "approved", "archived"})
RETENTION_LABELS = frozenset({"manual_review", "3_years", "5_years", "permanent"})
CONFIDENTIALITY_LEVELS = frozenset({"internal", "confidential", "restricted"})
DEPARTMENT_TYPES: dict[str, tuple[str, ...]] = {
    "marketing": ("campaign_plan", "content_caption", "posting_schedule", "kpi_report", "brand_asset"),
    "tech_codex": ("codex_task", "deployment_note", "bug_report", "architecture_doc"),
    "legal_policy": ("terms", "privacy", "data_policy", "ip_policy", "customer_notice"),
}
DEPARTMENT_LABELS = {
    "marketing": "Marketing",
    "tech_codex": "Tech & Codex",
    "legal_policy": "Legal & Policy",
}
TYPE_LABELS = {
    "campaign_plan": "Kế hoạch campaign",
    "content_caption": "Nội dung caption",
    "posting_schedule": "Lịch đăng nội bộ",
    "kpi_report": "Báo cáo KPI nội bộ",
    "brand_asset": "Tài sản thương hiệu (metadata)",
    "codex_task": "Nhiệm vụ Codex",
    "deployment_note": "Ghi chú triển khai",
    "bug_report": "Báo cáo lỗi",
    "architecture_doc": "Tài liệu kiến trúc",
    "terms": "Điều khoản nội bộ",
    "privacy": "Chính sách riêng tư",
    "data_policy": "Chính sách dữ liệu",
    "ip_policy": "Chính sách sở hữu trí tuệ",
    "customer_notice": "Thông báo khách hàng (bản nháp)",
}
STATE_LABELS = {
    "draft": "Bản nháp",
    "in_review": "Đang chờ duyệt",
    "approved": "Đã duyệt nội bộ",
    "archived": "Đã lưu trữ",
}
ACTION_LABELS = {
    "created": "Tạo tài liệu",
    "updated": "Cập nhật bản nháp",
    "submitted": "Gửi duyệt",
    "approved": "Duyệt nội bộ",
    "rejected": "Trả về bản nháp",
    "archived": "Lưu trữ",
    "restored": "Khôi phục bản nháp",
}
ACKNOWLEDGEMENTS = {
    "submit": "SUBMIT GOVERNANCE DOCUMENT FOR REVIEW",
    "approve": "APPROVE GOVERNANCE DOCUMENT",
    "reject": "REJECT GOVERNANCE DOCUMENT",
    "archive": "ARCHIVE GOVERNANCE DOCUMENT",
    "restore": "RESTORE GOVERNANCE DOCUMENT",
}

MAX_DOCUMENTS_PER_OWNER = 1_000
MAX_TITLE = 180
MAX_SUMMARY = 1_200
MAX_BODY = 48_000
MAX_REVIEW_NOTE = 1_600
MAX_TAGS = 12
MAX_LIST_LIMIT = 100
MAX_HISTORY_LIMIT = 100
MAX_LIST_OFFSET = 5_000
MAX_IDEMPOTENCY_RECORDS_PER_ADMIN = 256
IDEMPOTENCY_RETENTION = timedelta(hours=24)

DOCUMENT_COLUMNS = (
    "id",
    "owner_account_id",
    "department",
    "document_type",
    "title",
    "summary",
    "body",
    "tags_json",
    "retention_label",
    "confidentiality_level",
    "state",
    "review_note",
    "reviewer_account_id",
    "created_at",
    "updated_at",
    "submitted_at",
    "reviewed_at",
    "archived_at",
    "revision",
)


def _require_enabled() -> None:
    if not governance_documents_enabled():
        raise HTTPException(
            status_code=503,
            detail="Governance Documents đang tạm dừng. Cần bật WEBAPP_ADMIN_ERP_ENABLED và WEBAPP_GOVERNANCE_DOCUMENTS_ENABLED.",
        )


def _boundary(**extra: Any) -> dict[str, Any]:
    """Return a declarative boundary without external-execution booleans."""

    return {
        "execution": "web_native_admin_governance_documents_only",
        "data_origin": "web_governance_document_tables_only",
        "external_effects": "none",
        "publication": "not_available",
        "legacy_bot_scope": "TELEGRAM_ONLY",
        "excluded_domains": [
            "Telegram/Bot internal_documents và Telegram file ID/path",
            "Core bridge, Xu, PayOS, wallet, provider, job và output delivery",
            "Customer, finance, HR, contract, external notification và export records",
        ],
        **extra,
    }


def _guarded(message: str, code: str, *, status_name: str = "guarded", **data: Any) -> dict[str, Any]:
    return envelope(False, message, data=_boundary(**data), status_name=status_name, error_code=code)


def _uuid(value: Any, *, label: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail=f"{label} không hợp lệ") from exc


def _idempotency_key(value: Any) -> str:
    key = str(value or "").strip()
    if not IDEMPOTENCY_PATTERN.fullmatch(key):
        raise ValueError("Idempotency key không hợp lệ")
    return key


def _fingerprint(value: dict[str, Any]) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _idempotency_cutoff() -> str:
    return (datetime.now(timezone.utc) - IDEMPOTENCY_RETENTION).isoformat(timespec="seconds")


def _contains_dlp(value: str) -> bool:
    return bool(
        PRIVATE_KEY_PATTERN.search(value)
        or BEARER_PATTERN.search(value)
        or SECRET_ASSIGNMENT_PATTERN.search(value)
        or KNOWN_SECRET_PATTERN.search(value)
        or TELEGRAM_FILE_REFERENCE_PATTERN.search(value)
        or TELEGRAM_FILE_PATH_PATTERN.search(value)
        or FILESYSTEM_PATH_PATTERN.search(value)
    )


def _text(value: Any, *, label: str, minimum: int, maximum: int, multiline: bool, allow_empty: bool = False) -> str:
    text = str(value or "")
    if multiline:
        text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    else:
        text = re.sub(r"\s+", " ", text).strip()
    if CONTROL_PATTERN.search(text) or len(text) > maximum or (not allow_empty and len(text) < minimum):
        if allow_empty:
            raise ValueError(f"{label} tối đa {maximum:,} ký tự hợp lệ".replace(",", "."))
        raise ValueError(f"{label} cần từ {minimum} đến {maximum:,} ký tự hợp lệ".replace(",", "."))
    if text and _contains_dlp(text):
        raise ValueError(f"{label} không được chứa secret, Telegram file ID hoặc đường dẫn Telegram")
    return text


def _department(value: Any) -> str:
    normalized = _text(value, label="Phòng ban", minimum=2, maximum=32, multiline=False).lower()
    if normalized not in DEPARTMENT_TYPES:
        raise ValueError("Phòng ban Governance không được hỗ trợ")
    return normalized


def _document_type(value: Any) -> str:
    normalized = _text(value, label="Loại tài liệu", minimum=2, maximum=48, multiline=False).lower()
    if normalized not in TYPE_LABELS:
        raise ValueError("Loại tài liệu Governance không được hỗ trợ")
    return normalized


def _tags(value: Any) -> list[str]:
    if not isinstance(value, list) or len(value) > MAX_TAGS:
        raise ValueError(f"Tối đa {MAX_TAGS} tag Governance")
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        normalized = re.sub(r"\s+", " ", str(item or "")).strip().casefold()
        if not normalized or not TAG_PATTERN.fullmatch(normalized) or _contains_dlp(normalized):
            raise ValueError("Tag Governance không hợp lệ hoặc chứa dữ liệu nhạy cảm")
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _retention_label(value: Any) -> str:
    normalized = _text(value, label="Nhãn lưu trữ", minimum=2, maximum=32, multiline=False).lower()
    if normalized not in RETENTION_LABELS:
        raise ValueError("Nhãn lưu trữ Governance không hợp lệ")
    return normalized


def _confidentiality_level(value: Any) -> str:
    normalized = _text(value, label="Mức độ bảo mật", minimum=2, maximum=32, multiline=False).lower()
    if normalized not in CONFIDENTIALITY_LEVELS:
        raise ValueError("Mức độ bảo mật Governance không hợp lệ")
    return normalized


def _json_tags(value: Any) -> list[str]:
    try:
        parsed = json.loads(str(value or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed) else []


def _query_text(value: str | None) -> str:
    if value is None:
        return ""
    return _text(value, label="Từ khóa tìm kiếm", minimum=0, maximum=120, multiline=False, allow_empty=True)


def _like(value: str) -> str:
    return "%" + value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _active_admin_session_in_transaction(conn: Any, *, account_id: str, session_id: str) -> None:
    """Re-check signed admin state after acquiring the SQLite write lock."""

    row = conn.execute(
        """SELECT 1
           FROM web_sessions AS s JOIN web_accounts AS a ON a.id=s.account_id
           WHERE s.id=? AND s.account_id=? AND s.revoked_at IS NULL AND s.expires_at>?
             AND a.is_active=1 AND a.role_cache='admin'
           LIMIT 1""",
        (session_id, account_id, utc_now()),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Phiên quản trị không còn hợp lệ")


def _row_to_document(row: tuple[Any, ...], *, actor_account_id: str, detail: bool) -> dict[str, Any]:
    value = dict(zip(DOCUMENT_COLUMNS, row))
    owner_id = str(value["owner_account_id"])
    state = str(value["state"])
    own = owner_id == actor_account_id
    result: dict[str, Any] = {
        "id": str(value["id"]),
        "department": str(value["department"]),
        "department_label": DEPARTMENT_LABELS.get(str(value["department"]), "Governance"),
        "document_type": str(value["document_type"]),
        "document_type_label": TYPE_LABELS.get(str(value["document_type"]), "Tài liệu nội bộ"),
        "title": str(value["title"]),
        "summary": str(value["summary"] or ""),
        "tags": _json_tags(value["tags_json"]),
        "retention_label": str(value["retention_label"]),
        "confidentiality_level": str(value["confidentiality_level"]),
        "state": state,
        "state_label": STATE_LABELS.get(state, "Trạng thái nội bộ"),
        "revision": int(value["revision"]),
        "created_at": str(value["created_at"]),
        "updated_at": str(value["updated_at"]),
        "submitted_at": str(value["submitted_at"]) if value["submitted_at"] else None,
        "reviewed_at": str(value["reviewed_at"]) if value["reviewed_at"] else None,
        "archived_at": str(value["archived_at"]) if value["archived_at"] else None,
        "ownership": "own" if own else "other",
        "permissions": {
            "can_update": own and state == "draft",
            "can_submit": own and state == "draft",
            "can_review": (not own) and state == "in_review",
            "can_archive": own and state == "approved",
            "can_restore": own and state == "archived",
        },
    }
    if detail:
        result["body"] = str(value["body"])
        result["review_note"] = str(value["review_note"] or "")
        result["reviewer_relation"] = (
            "self" if value["reviewer_account_id"] and str(value["reviewer_account_id"]) == actor_account_id else
            "another_admin" if value["reviewer_account_id"] else "not_reviewed"
        )
    return result


def _fetch_document(conn: Any, *, document_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, owner_account_id, department, document_type, title, summary, body, tags_json,
                  retention_label, confidentiality_level, state, review_note, reviewer_account_id, created_at, updated_at, submitted_at,
                  reviewed_at, archived_at, revision
           FROM web_governance_documents WHERE id=? LIMIT 1""",
        (document_id,),
    ).fetchone()


def _insert_version(conn: Any, *, row: tuple[Any, ...], actor_account_id: str, action: str, created_at: str) -> None:
    value = dict(zip(DOCUMENT_COLUMNS, row))
    conn.execute(
        """INSERT INTO web_governance_document_versions
           (id, document_id, revision, actor_account_id, action, state, department, document_type,
            title, summary, body, tags_json, retention_label, confidentiality_level, review_note, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            str(uuid.uuid4()),
            str(value["id"]),
            int(value["revision"]),
            actor_account_id,
            action,
            str(value["state"]),
            str(value["department"]),
            str(value["document_type"]),
            str(value["title"]),
            str(value["summary"] or ""),
            str(value["body"]),
            str(value["tags_json"]),
            str(value["retention_label"]),
            str(value["confidentiality_level"]),
            str(value["review_note"] or ""),
            created_at,
        ),
    )


def _insert_event(
    conn: Any,
    *,
    document_id: str,
    actor_account_id: str,
    action: str,
    from_state: str | None,
    to_state: str,
    revision: int,
    created_at: str,
) -> None:
    conn.execute(
        """INSERT INTO web_governance_document_events
           (id, document_id, actor_account_id, action, from_state, to_state, revision, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), document_id, actor_account_id, action, from_state, to_state, revision, created_at),
    )


def _audit(
    conn: Any,
    *,
    actor_account_id: str,
    document_id: str,
    action: str,
    request: Request,
    state: str,
) -> None:
    # Never put title, body, tag, review note or any DLP candidate in the
    # generic audit table. The target is a local UUID, not a Bot/canonical ID.
    _record_audit(
        conn,
        account_id=actor_account_id,
        canonical_user_id=None,
        action=f"web.governance.document.{action}",
        request_id=_request_id(request),
        target=document_id,
        detail=f"web-native governance document lifecycle action={action} state={state}; no Bot, bridge, payment, provider, job, publication or notification effect",
    )


def _receipt(*, document_id: str, state: str, revision: int, updated_at: str, action: str) -> dict[str, Any]:
    return envelope(
        True,
        f"Đã {ACTION_LABELS.get(action, 'ghi nhận')} tài liệu Governance.",
        data=_boundary(
            action=action,
            document={
                "id": document_id,
                "state": state,
                "state_label": STATE_LABELS.get(state, "Trạng thái nội bộ"),
                "revision": revision,
                "updated_at": updated_at,
            },
        ),
        status_name=state,
    )


def _idempotent(
    *,
    scope: str,
    account_id: str,
    session_id: str,
    key: str,
    request_fingerprint: str,
    operation: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    """Persist only compact write receipts, never document body snapshots."""

    ensure_copyfast_schema()
    with transaction() as conn:
        _active_admin_session_in_transaction(conn, account_id=account_id, session_id=session_id)
        conn.execute(
            "DELETE FROM web_idempotency WHERE scope LIKE ? AND created_at<?",
            ("web-governance:%", _idempotency_cutoff()),
        )
        existing = conn.execute(
            "SELECT response_json, request_fingerprint FROM web_idempotency WHERE scope=? AND key=?",
            (scope, key),
        ).fetchone()
        if existing:
            if str(existing[1] or "") != request_fingerprint:
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho thao tác Governance khác")
            try:
                receipt = json.loads(str(existing[0]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Receipt Governance không hợp lệ") from exc
            if not isinstance(receipt, dict):
                raise HTTPException(status_code=409, detail="Receipt Governance không hợp lệ")
            return receipt
        count = conn.execute(
            "SELECT COUNT(*) FROM web_idempotency WHERE scope LIKE ?",
            (f"web-governance:{account_id}:%",),
        ).fetchone()
        if int(count[0] or 0) >= MAX_IDEMPOTENCY_RECORDS_PER_ADMIN:
            return _guarded(
                "Kho receipt Governance tạm thời đang đầy. Vui lòng thử lại sau.",
                "WEB_GOVERNANCE_IDEMPOTENCY_LIMIT",
            )
        result = operation(conn)
        if result.get("ok") is True:
            conn.execute(
                """INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (scope, key, json.dumps(result, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
            )
        return result


class DocumentCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    department: str
    document_type: str
    title: str
    summary: str = ""
    body: str
    tags: list[str] = Field(default_factory=list)
    retention_label: str = "manual_review"
    confidentiality_level: str = "internal"
    idempotency_key: str

    @field_validator("department")
    @classmethod
    def _valid_department(cls, value: str) -> str:
        return _department(value)

    @field_validator("document_type")
    @classmethod
    def _valid_type(cls, value: str) -> str:
        return _document_type(value)

    @field_validator("title")
    @classmethod
    def _valid_title(cls, value: str) -> str:
        return _text(value, label="Tiêu đề", minimum=3, maximum=MAX_TITLE, multiline=False)

    @field_validator("summary")
    @classmethod
    def _valid_summary(cls, value: str) -> str:
        return _text(value, label="Tóm tắt", minimum=0, maximum=MAX_SUMMARY, multiline=True, allow_empty=True)

    @field_validator("body")
    @classmethod
    def _valid_body(cls, value: str) -> str:
        return _text(value, label="Nội dung", minimum=1, maximum=MAX_BODY, multiline=True)

    @field_validator("tags")
    @classmethod
    def _valid_tags(cls, value: list[str]) -> list[str]:
        return _tags(value)

    @field_validator("retention_label")
    @classmethod
    def _valid_retention_label(cls, value: str) -> str:
        return _retention_label(value)

    @field_validator("confidentiality_level")
    @classmethod
    def _valid_confidentiality_level(cls, value: str) -> str:
        return _confidentiality_level(value)

    @field_validator("idempotency_key")
    @classmethod
    def _valid_key(cls, value: str) -> str:
        return _idempotency_key(value)

    @model_validator(mode="after")
    def _matching_type(self) -> "DocumentCreatePayload":
        if self.document_type not in DEPARTMENT_TYPES[self.department]:
            raise ValueError("Loại tài liệu không thuộc phòng ban Governance đã chọn")
        return self


class DocumentUpdatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    summary: str | None = None
    body: str | None = None
    tags: list[str] | None = None
    retention_label: str | None = None
    confidentiality_level: str | None = None
    expected_revision: int = Field(ge=1, le=1_000_000)
    idempotency_key: str

    @field_validator("title")
    @classmethod
    def _valid_title(cls, value: str | None) -> str | None:
        return _text(value, label="Tiêu đề", minimum=3, maximum=MAX_TITLE, multiline=False) if value is not None else None

    @field_validator("summary")
    @classmethod
    def _valid_summary(cls, value: str | None) -> str | None:
        return _text(value, label="Tóm tắt", minimum=0, maximum=MAX_SUMMARY, multiline=True, allow_empty=True) if value is not None else None

    @field_validator("body")
    @classmethod
    def _valid_body(cls, value: str | None) -> str | None:
        return _text(value, label="Nội dung", minimum=1, maximum=MAX_BODY, multiline=True) if value is not None else None

    @field_validator("tags")
    @classmethod
    def _valid_tags(cls, value: list[str] | None) -> list[str] | None:
        return _tags(value) if value is not None else None

    @field_validator("retention_label")
    @classmethod
    def _valid_retention_label(cls, value: str | None) -> str | None:
        return _retention_label(value) if value is not None else None

    @field_validator("confidentiality_level")
    @classmethod
    def _valid_confidentiality_level(cls, value: str | None) -> str | None:
        return _confidentiality_level(value) if value is not None else None

    @field_validator("idempotency_key")
    @classmethod
    def _valid_key(cls, value: str) -> str:
        return _idempotency_key(value)

    @model_validator(mode="after")
    def _changed(self) -> "DocumentUpdatePayload":
        if not ({"title", "summary", "body", "tags", "retention_label", "confidentiality_level"} & self.model_fields_set):
            raise ValueError("Cần có ít nhất một trường tài liệu để cập nhật")
        return self


class TransitionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1, le=1_000_000)
    acknowledgement: str = Field(min_length=1, max_length=80)
    confirm: bool = False
    review_note: str = ""
    idempotency_key: str

    @field_validator("acknowledgement")
    @classmethod
    def _ack(cls, value: str) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()

    @field_validator("review_note")
    @classmethod
    def _note(cls, value: str) -> str:
        return _text(value, label="Ghi chú review", minimum=0, maximum=MAX_REVIEW_NOTE, multiline=True, allow_empty=True)

    @field_validator("idempotency_key")
    @classmethod
    def _valid_key(cls, value: str) -> str:
        return _idempotency_key(value)


def _actor_for_write(request: Request, account: dict[str, Any]) -> tuple[str, str]:
    session = current_session(request)
    session_account = session["account"]
    if str(session_account["id"]) != str(account["id"]) or session_account.get("role") != "admin":
        raise HTTPException(status_code=401, detail="Phiên quản trị không còn hợp lệ")
    return str(account["id"]), str(session["session_id"])


def _transition_request(
    *,
    document_id: str,
    payload: TransitionPayload,
    request: Request,
    account: dict[str, Any],
    action: str,
) -> dict[str, Any]:
    _require_enabled()
    document_id = _uuid(document_id, label="Mã tài liệu Governance")
    expected_ack = ACKNOWLEDGEMENTS[action]
    if not payload.confirm or payload.acknowledgement != expected_ack:
        return _guarded(
            "Cần xác nhận đúng câu xác nhận Governance trước khi thay đổi lifecycle tài liệu.",
            "WEB_GOVERNANCE_CONFIRMATION_REQUIRED",
        )
    if action == "reject" and not payload.review_note:
        return _guarded(
            "Cần ghi chú review trước khi trả tài liệu về bản nháp.",
            "WEB_GOVERNANCE_REJECTION_NOTE_REQUIRED",
        )
    actor_account_id, session_id = _actor_for_write(request, account)
    fingerprint = _fingerprint(
        {
            "document_id": document_id,
            "action": action,
            "expected_revision": payload.expected_revision,
            "acknowledgement": payload.acknowledgement,
            "confirm": payload.confirm,
            "review_note": payload.review_note,
        }
    )
    scope = f"web-governance:{actor_account_id}:document:{document_id}:{action}"

    def operation(conn: Any) -> dict[str, Any]:
        current = _fetch_document(conn, document_id=document_id)
        if not current:
            return _guarded("Không tìm thấy tài liệu Governance đang có quyền truy cập.", "WEB_GOVERNANCE_DOCUMENT_NOT_FOUND")
        value = dict(zip(DOCUMENT_COLUMNS, current))
        owner_id = str(value["owner_account_id"])
        state = str(value["state"])
        revision = int(value["revision"])
        if revision != payload.expected_revision:
            return _guarded("Tài liệu Governance đã có revision mới. Hãy tải lại trước khi tiếp tục.", "WEB_GOVERNANCE_DOCUMENT_CONFLICT")

        if action in {"submit", "archive", "restore"} and owner_id != actor_account_id:
            return _guarded("Không tìm thấy tài liệu Governance có thể thực hiện thao tác.", "WEB_GOVERNANCE_DOCUMENT_NOT_FOUND")
        if action in {"approve", "reject"} and owner_id == actor_account_id:
            return _guarded("Cần một quản trị viên khác thực hiện review tài liệu này.", "WEB_GOVERNANCE_REVIEW_SEPARATION_REQUIRED")

        expected_state = {
            "submit": "draft",
            "approve": "in_review",
            "reject": "in_review",
            "archive": "approved",
            "restore": "archived",
        }[action]
        if state != expected_state:
            return _guarded("Tài liệu Governance không ở trạng thái phù hợp cho thao tác này.", "WEB_GOVERNANCE_INVALID_TRANSITION")

        now = utc_now()
        next_revision = revision + 1
        if action == "submit":
            next_state = "in_review"
            params = (next_state, next_revision, now, now, document_id, owner_id, revision)
            updated = conn.execute(
                """UPDATE web_governance_documents
                   SET state=?, revision=?, updated_at=?, submitted_at=?, review_note='', reviewer_account_id=NULL,
                       reviewed_at=NULL, archived_at=NULL
                   WHERE id=? AND owner_account_id=? AND revision=? AND state='draft'""",
                params,
            )
        elif action == "approve":
            next_state = "approved"
            updated = conn.execute(
                """UPDATE web_governance_documents
                   SET state=?, revision=?, updated_at=?, reviewer_account_id=?, review_note=?, reviewed_at=?
                   WHERE id=? AND revision=? AND state='in_review' AND owner_account_id<>?""",
                (next_state, next_revision, now, actor_account_id, payload.review_note, now, document_id, revision, actor_account_id),
            )
        elif action == "reject":
            next_state = "draft"
            updated = conn.execute(
                """UPDATE web_governance_documents
                   SET state=?, revision=?, updated_at=?, reviewer_account_id=?, review_note=?, reviewed_at=?
                   WHERE id=? AND revision=? AND state='in_review' AND owner_account_id<>?""",
                (next_state, next_revision, now, actor_account_id, payload.review_note, now, document_id, revision, actor_account_id),
            )
        elif action == "archive":
            next_state = "archived"
            updated = conn.execute(
                """UPDATE web_governance_documents
                   SET state=?, revision=?, updated_at=?, archived_at=?
                   WHERE id=? AND owner_account_id=? AND revision=? AND state='approved'""",
                (next_state, next_revision, now, now, document_id, owner_id, revision),
            )
        else:  # restore
            next_state = "draft"
            updated = conn.execute(
                """UPDATE web_governance_documents
                   SET state=?, revision=?, updated_at=?, archived_at=NULL, submitted_at=NULL,
                       reviewer_account_id=NULL, review_note='', reviewed_at=NULL
                   WHERE id=? AND owner_account_id=? AND revision=? AND state='archived'""",
                (next_state, next_revision, now, document_id, owner_id, revision),
            )
        if int(updated.rowcount or 0) != 1:
            return _guarded("Tài liệu Governance đã thay đổi đồng thời. Hãy tải lại trước khi tiếp tục.", "WEB_GOVERNANCE_DOCUMENT_CONFLICT")
        next_row = _fetch_document(conn, document_id=document_id)
        if not next_row:
            raise RuntimeError("Governance document disappeared after a guarded update")
        # Endpoint intents use short verbs (``submit``/``reject``), while the
        # immutable event/version vocabulary records the completed transition.
        # Keeping that mapping here prevents an unhandled SQLite CHECK error
        # and makes history independent of a particular HTTP route spelling.
        recorded_action = {
            "submit": "submitted",
            "approve": "approved",
            "reject": "rejected",
            "archive": "archived",
            "restore": "restored",
        }[action]
        _insert_version(conn, row=next_row, actor_account_id=actor_account_id, action=recorded_action, created_at=now)
        _insert_event(
            conn,
            document_id=document_id,
            actor_account_id=actor_account_id,
            action=recorded_action,
            from_state=state,
            to_state=next_state,
            revision=next_revision,
            created_at=now,
        )
        _audit(
            conn,
            actor_account_id=actor_account_id,
            document_id=document_id,
            action=recorded_action,
            request=request,
            state=next_state,
        )
        return _receipt(document_id=document_id, state=next_state, revision=next_revision, updated_at=now, action=recorded_action)

    return _idempotent(
        scope=scope,
        account_id=actor_account_id,
        session_id=session_id,
        key=payload.idempotency_key,
        request_fingerprint=fingerprint,
        operation=operation,
    )


@router.get("/policy")
async def policy(request: Request, account: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    _require_enabled()
    del request, account
    departments = [
        {
            "key": department,
            "label": DEPARTMENT_LABELS[department],
            "document_types": [
                {"key": doc_type, "label": TYPE_LABELS[doc_type]}
                for doc_type in document_types
            ],
        }
        for department, document_types in DEPARTMENT_TYPES.items()
    ]
    return envelope(
        True,
        "Đã nạp policy Governance Documents Web-native.",
        data=_boundary(
            policy_version=POLICY_VERSION,
            departments=departments,
            lifecycle={
                "states": [{"key": state, "label": STATE_LABELS[state]} for state in ("draft", "in_review", "approved", "archived")],
                "transitions": {
                    "draft": ["in_review"],
                    "in_review": ["approved", "draft"],
                    "approved": ["archived"],
                    "archived": ["draft"],
                },
                "review_separation": "Người tạo không thể tự duyệt hoặc tự từ chối tài liệu của mình.",
                "publication": "Không có auto-publish hoặc external notification trong release này.",
            },
            confirmations={
                "submit_review": ACKNOWLEDGEMENTS["submit"],
                "approve": ACKNOWLEDGEMENTS["approve"],
                "reject": ACKNOWLEDGEMENTS["reject"],
                "archive": ACKNOWLEDGEMENTS["archive"],
                "restore": ACKNOWLEDGEMENTS["restore"],
            },
            limits={
                "title_characters": MAX_TITLE,
                "summary_characters": MAX_SUMMARY,
                "body_characters": MAX_BODY,
                "review_note_characters": MAX_REVIEW_NOTE,
                "tags": MAX_TAGS,
                "retention_labels": sorted(RETENTION_LABELS),
                "confidentiality_levels": sorted(CONFIDENTIALITY_LEVELS),
                "documents_per_creator": MAX_DOCUMENTS_PER_OWNER,
            },
            retention_notice="Nhãn lưu trữ chỉ là nhãn vận hành nội bộ, không phải tư vấn pháp lý hoặc chính sách lưu giữ pháp lý.",
        ),
        status_name="read_only",
    )


@router.get("/summary")
async def summary(request: Request, account: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    _require_enabled()
    ensure_copyfast_schema()
    account_id = str(account["id"])
    with read_transaction() as conn:
        rows = conn.execute(
            "SELECT state, COUNT(*) FROM web_governance_documents GROUP BY state"
        ).fetchall()
        own_total = conn.execute(
            "SELECT COUNT(*) FROM web_governance_documents WHERE owner_account_id=?",
            (account_id,),
        ).fetchone()
        reviewable = conn.execute(
            """SELECT COUNT(*) FROM web_governance_documents
               WHERE state='in_review' AND owner_account_id<>?""",
            (account_id,),
        ).fetchone()
    counts = {state: 0 for state in DOCUMENT_STATES}
    for state, count in rows:
        if str(state) in counts:
            counts[str(state)] = int(count or 0)
    return envelope(
        True,
        "Đã nạp tổng quan Governance Documents.",
        data=_boundary(
            summary={
                "by_state": counts,
                "own_documents": int(own_total[0] or 0) if own_total else 0,
                "reviewable_by_current_admin": int(reviewable[0] or 0) if reviewable else 0,
                "published_documents": 0,
                "external_notifications": 0,
            },
            scope="admin_scoped_web_governance_metadata",
        ),
        status_name="read_only",
    )


@router.get("/documents")
async def list_documents(
    request: Request,
    department: str = Query("all", max_length=32),
    document_type: str = Query("all", max_length=48),
    state: str = Query("all", max_length=24),
    scope: str = Query("all", max_length=16),
    q: str | None = Query(None, max_length=120),
    limit: int = Query(30, ge=1, le=MAX_LIST_LIMIT),
    offset: int = Query(0, ge=0, le=MAX_LIST_OFFSET),
    account: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    _require_enabled()
    ensure_copyfast_schema()
    account_id = str(account["id"])
    normalized_department = str(department or "all").strip().lower()
    normalized_type = str(document_type or "all").strip().lower()
    normalized_state = str(state or "all").strip().lower()
    normalized_scope = str(scope or "all").strip().lower()
    if normalized_department != "all" and normalized_department not in DEPARTMENT_TYPES:
        raise HTTPException(status_code=422, detail="Bộ lọc phòng ban Governance không hợp lệ")
    if normalized_type != "all" and normalized_type not in TYPE_LABELS:
        raise HTTPException(status_code=422, detail="Bộ lọc loại tài liệu Governance không hợp lệ")
    if normalized_department != "all" and normalized_type != "all" and normalized_type not in DEPARTMENT_TYPES[normalized_department]:
        raise HTTPException(status_code=422, detail="Loại tài liệu không thuộc phòng ban Governance đã chọn")
    if normalized_state != "all" and normalized_state not in DOCUMENT_STATES:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái Governance không hợp lệ")
    if normalized_scope not in {"all", "mine", "review"}:
        raise HTTPException(status_code=422, detail="Phạm vi tài liệu Governance không hợp lệ")
    query_text = _query_text(q)
    clauses: list[str] = []
    params: list[Any] = []
    if normalized_department != "all":
        clauses.append("department=?")
        params.append(normalized_department)
    if normalized_type != "all":
        clauses.append("document_type=?")
        params.append(normalized_type)
    if normalized_state != "all":
        clauses.append("state=?")
        params.append(normalized_state)
    if normalized_scope == "mine":
        clauses.append("owner_account_id=?")
        params.append(account_id)
    elif normalized_scope == "review":
        clauses.extend(("state='in_review'", "owner_account_id<>?"))
        params.append(account_id)
    if query_text:
        clauses.append("(title LIKE ? ESCAPE '\\' OR summary LIKE ? ESCAPE '\\' OR tags_json LIKE ? ESCAPE '\\')")
        params.extend((_like(query_text), _like(query_text), _like(query_text)))
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with read_transaction() as conn:
        rows = conn.execute(
            f"""SELECT id, owner_account_id, department, document_type, title, summary, body, tags_json,
                      retention_label, confidentiality_level, state, review_note, reviewer_account_id, created_at, updated_at, submitted_at,
                      reviewed_at, archived_at, revision
               FROM web_governance_documents{where}
               ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?""",
            [*params, int(limit) + 1, int(offset)],
        ).fetchall()
    has_more = len(rows) > int(limit)
    documents = [_row_to_document(tuple(row), actor_account_id=account_id, detail=False) for row in rows[: int(limit)]]
    return envelope(
        True,
        "Đã nạp danh sách Governance Documents.",
        data=_boundary(
            documents=documents,
            has_more=has_more,
            next_offset=int(offset) + int(limit) if has_more else None,
            filters={
                "department": normalized_department,
                "document_type": normalized_type,
                "state": normalized_state,
                "scope": normalized_scope,
                "q": query_text,
            },
        ),
        status_name="read_only",
    )


@router.get("/documents/{document_id}")
async def get_document(document_id: str, request: Request, account: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    _require_enabled()
    document_id = _uuid(document_id, label="Mã tài liệu Governance")
    ensure_copyfast_schema()
    with read_transaction() as conn:
        row = _fetch_document(conn, document_id=document_id)
    if not row:
        return _guarded("Không tìm thấy tài liệu Governance đang có quyền truy cập.", "WEB_GOVERNANCE_DOCUMENT_NOT_FOUND")
    return envelope(
        True,
        "Đã nạp tài liệu Governance.",
        data=_boundary(document=_row_to_document(tuple(row), actor_account_id=str(account["id"]), detail=True)),
        status_name="read_only",
    )


@router.get("/documents/{document_id}/versions")
async def list_versions(
    document_id: str,
    request: Request,
    limit: int = Query(30, ge=1, le=MAX_HISTORY_LIMIT),
    offset: int = Query(0, ge=0, le=MAX_LIST_OFFSET),
    account: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    _require_enabled()
    document_id = _uuid(document_id, label="Mã tài liệu Governance")
    ensure_copyfast_schema()
    account_id = str(account["id"])
    with read_transaction() as conn:
        document = _fetch_document(conn, document_id=document_id)
        if not document:
            rows: list[tuple[Any, ...]] = []
        else:
            rows = conn.execute(
                """SELECT id, revision, actor_account_id, action, state, department, document_type,
                          title, summary, body, tags_json, retention_label, confidentiality_level, review_note, created_at
                   FROM web_governance_document_versions WHERE document_id=?
                   ORDER BY revision DESC, id DESC LIMIT ? OFFSET ?""",
                (document_id, int(limit) + 1, int(offset)),
            ).fetchall()
    if not document:
        return _guarded("Không tìm thấy tài liệu Governance đang có quyền truy cập.", "WEB_GOVERNANCE_DOCUMENT_NOT_FOUND")
    has_more = len(rows) > int(limit)
    versions: list[dict[str, Any]] = []
    for row in rows[: int(limit)]:
        versions.append(
            {
                "id": str(row[0]),
                "revision": int(row[1]),
                "actor_relation": "self" if str(row[2]) == account_id else "another_admin",
                "action": str(row[3]),
                "action_label": ACTION_LABELS.get(str(row[3]), "Cập nhật lifecycle"),
                "state": str(row[4]),
                "state_label": STATE_LABELS.get(str(row[4]), "Trạng thái nội bộ"),
                "department": str(row[5]),
                "document_type": str(row[6]),
                "title": str(row[7]),
                "summary": str(row[8] or ""),
                "body": str(row[9]),
                "tags": _json_tags(row[10]),
                "retention_label": str(row[11]),
                "confidentiality_level": str(row[12]),
                "review_note": str(row[13] or ""),
                "created_at": str(row[14]),
            }
        )
    return envelope(
        True,
        "Đã nạp lịch sử phiên bản Governance.",
        data=_boundary(
            document_id=document_id,
            versions=versions,
            has_more=has_more,
            next_offset=int(offset) + int(limit) if has_more else None,
            immutable_history=True,
        ),
        status_name="read_only",
    )


@router.get("/documents/{document_id}/events")
async def list_events(
    document_id: str,
    request: Request,
    limit: int = Query(30, ge=1, le=MAX_HISTORY_LIMIT),
    offset: int = Query(0, ge=0, le=MAX_LIST_OFFSET),
    account: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    _require_enabled()
    document_id = _uuid(document_id, label="Mã tài liệu Governance")
    ensure_copyfast_schema()
    account_id = str(account["id"])
    with read_transaction() as conn:
        document = _fetch_document(conn, document_id=document_id)
        if not document:
            rows: list[tuple[Any, ...]] = []
        else:
            rows = conn.execute(
                """SELECT id, actor_account_id, action, from_state, to_state, revision, created_at
                   FROM web_governance_document_events WHERE document_id=?
                   ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?""",
                (document_id, int(limit) + 1, int(offset)),
            ).fetchall()
    if not document:
        return _guarded("Không tìm thấy tài liệu Governance đang có quyền truy cập.", "WEB_GOVERNANCE_DOCUMENT_NOT_FOUND")
    has_more = len(rows) > int(limit)
    events = [
        {
            "id": str(row[0]),
            "actor_relation": "self" if str(row[1]) == account_id else "another_admin",
            "action": str(row[2]),
            "action_label": ACTION_LABELS.get(str(row[2]), "Cập nhật lifecycle"),
            "from_state": str(row[3]) if row[3] else None,
            "to_state": str(row[4]),
            "to_state_label": STATE_LABELS.get(str(row[4]), "Trạng thái nội bộ"),
            "revision": int(row[5]),
            "created_at": str(row[6]),
        }
        for row in rows[: int(limit)]
    ]
    return envelope(
        True,
        "Đã nạp audit lifecycle Governance đã redaction.",
        data=_boundary(
            document_id=document_id,
            events=events,
            has_more=has_more,
            next_offset=int(offset) + int(limit) if has_more else None,
            actor_identity="redacted_to_self_or_another_admin",
        ),
        status_name="read_only",
    )


@router.post("/documents")
async def create_document(
    payload: DocumentCreatePayload,
    request: Request,
    account: dict[str, Any] = Depends(require_admin_csrf),
) -> dict[str, Any]:
    _require_enabled()
    actor_account_id, session_id = _actor_for_write(request, account)
    fingerprint = _fingerprint(
        {
            "department": payload.department,
            "document_type": payload.document_type,
            "title": payload.title,
            "summary": payload.summary,
            "body": payload.body,
            "tags": payload.tags,
            "retention_label": payload.retention_label,
            "confidentiality_level": payload.confidentiality_level,
        }
    )
    scope = f"web-governance:{actor_account_id}:document:create"

    def operation(conn: Any) -> dict[str, Any]:
        count = conn.execute(
            "SELECT COUNT(*) FROM web_governance_documents WHERE owner_account_id=?",
            (actor_account_id,),
        ).fetchone()
        if int(count[0] or 0) >= MAX_DOCUMENTS_PER_OWNER:
            return _guarded("Đã đạt giới hạn tài liệu Governance cho quản trị viên hiện tại.", "WEB_GOVERNANCE_DOCUMENT_LIMIT")
        now = utc_now()
        document_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO web_governance_documents
               (id, owner_account_id, department, document_type, title, summary, body, tags_json, retention_label, confidentiality_level,
                state, review_note, reviewer_account_id, created_at, updated_at, submitted_at,
                reviewed_at, archived_at, revision)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', '', NULL, ?, ?, NULL, NULL, NULL, 1)""",
            (
                document_id,
                actor_account_id,
                payload.department,
                payload.document_type,
                payload.title,
                payload.summary,
                payload.body,
                json.dumps(payload.tags, ensure_ascii=False, separators=(",", ":")),
                payload.retention_label,
                payload.confidentiality_level,
                now,
                now,
            ),
        )
        row = _fetch_document(conn, document_id=document_id)
        if not row:
            raise RuntimeError("Governance document was not available after create")
        _insert_version(conn, row=row, actor_account_id=actor_account_id, action="created", created_at=now)
        _insert_event(
            conn,
            document_id=document_id,
            actor_account_id=actor_account_id,
            action="created",
            from_state=None,
            to_state="draft",
            revision=1,
            created_at=now,
        )
        _audit(conn, actor_account_id=actor_account_id, document_id=document_id, action="created", request=request, state="draft")
        return _receipt(document_id=document_id, state="draft", revision=1, updated_at=now, action="created")

    return _idempotent(
        scope=scope,
        account_id=actor_account_id,
        session_id=session_id,
        key=payload.idempotency_key,
        request_fingerprint=fingerprint,
        operation=operation,
    )


@router.patch("/documents/{document_id}")
async def update_document(
    document_id: str,
    payload: DocumentUpdatePayload,
    request: Request,
    account: dict[str, Any] = Depends(require_admin_csrf),
) -> dict[str, Any]:
    _require_enabled()
    document_id = _uuid(document_id, label="Mã tài liệu Governance")
    actor_account_id, session_id = _actor_for_write(request, account)
    supplied = payload.model_dump(exclude_unset=True)
    fingerprint = _fingerprint({"document_id": document_id, **supplied})
    scope = f"web-governance:{actor_account_id}:document:{document_id}:update"

    def operation(conn: Any) -> dict[str, Any]:
        current = _fetch_document(conn, document_id=document_id)
        if not current:
            return _guarded("Không tìm thấy tài liệu Governance có thể cập nhật.", "WEB_GOVERNANCE_DOCUMENT_NOT_FOUND")
        value = dict(zip(DOCUMENT_COLUMNS, current))
        if str(value["owner_account_id"]) != actor_account_id:
            return _guarded("Không tìm thấy tài liệu Governance có thể cập nhật.", "WEB_GOVERNANCE_DOCUMENT_NOT_FOUND")
        if str(value["state"]) != "draft":
            return _guarded("Chỉ bản nháp Governance mới có thể chỉnh sửa nội dung.", "WEB_GOVERNANCE_DRAFT_REQUIRED")
        if int(value["revision"]) != payload.expected_revision:
            return _guarded("Tài liệu Governance đã có revision mới. Hãy tải lại trước khi tiếp tục.", "WEB_GOVERNANCE_DOCUMENT_CONFLICT")
        title = payload.title if "title" in supplied else str(value["title"])
        summary = payload.summary if "summary" in supplied else str(value["summary"] or "")
        body = payload.body if "body" in supplied else str(value["body"])
        tags = payload.tags if "tags" in supplied else _json_tags(value["tags_json"])
        retention_label = payload.retention_label if "retention_label" in supplied else str(value["retention_label"])
        confidentiality_level = payload.confidentiality_level if "confidentiality_level" in supplied else str(value["confidentiality_level"])
        now = utc_now()
        next_revision = int(value["revision"]) + 1
        updated = conn.execute(
            """UPDATE web_governance_documents
               SET title=?, summary=?, body=?, tags_json=?, retention_label=?, confidentiality_level=?, revision=?, updated_at=?
               WHERE id=? AND owner_account_id=? AND state='draft' AND revision=?""",
            (
                title,
                summary,
                body,
                json.dumps(tags, ensure_ascii=False, separators=(",", ":")),
                retention_label,
                confidentiality_level,
                next_revision,
                now,
                document_id,
                actor_account_id,
                payload.expected_revision,
            ),
        )
        if int(updated.rowcount or 0) != 1:
            return _guarded("Tài liệu Governance đã thay đổi đồng thời. Hãy tải lại trước khi tiếp tục.", "WEB_GOVERNANCE_DOCUMENT_CONFLICT")
        row = _fetch_document(conn, document_id=document_id)
        if not row:
            raise RuntimeError("Governance document disappeared after update")
        _insert_version(conn, row=row, actor_account_id=actor_account_id, action="updated", created_at=now)
        _insert_event(
            conn,
            document_id=document_id,
            actor_account_id=actor_account_id,
            action="updated",
            from_state="draft",
            to_state="draft",
            revision=next_revision,
            created_at=now,
        )
        _audit(conn, actor_account_id=actor_account_id, document_id=document_id, action="updated", request=request, state="draft")
        return _receipt(document_id=document_id, state="draft", revision=next_revision, updated_at=now, action="updated")

    return _idempotent(
        scope=scope,
        account_id=actor_account_id,
        session_id=session_id,
        key=payload.idempotency_key,
        request_fingerprint=fingerprint,
        operation=operation,
    )


@router.post("/documents/{document_id}/submit-review")
async def submit_review(
    document_id: str,
    payload: TransitionPayload,
    request: Request,
    account: dict[str, Any] = Depends(require_admin_csrf),
) -> dict[str, Any]:
    return _transition_request(document_id=document_id, payload=payload, request=request, account=account, action="submit")


@router.post("/documents/{document_id}/approve")
async def approve_document(
    document_id: str,
    payload: TransitionPayload,
    request: Request,
    account: dict[str, Any] = Depends(require_admin_csrf),
) -> dict[str, Any]:
    return _transition_request(document_id=document_id, payload=payload, request=request, account=account, action="approve")


@router.post("/documents/{document_id}/reject")
async def reject_document(
    document_id: str,
    payload: TransitionPayload,
    request: Request,
    account: dict[str, Any] = Depends(require_admin_csrf),
) -> dict[str, Any]:
    return _transition_request(document_id=document_id, payload=payload, request=request, account=account, action="reject")


@router.post("/documents/{document_id}/archive")
async def archive_document(
    document_id: str,
    payload: TransitionPayload,
    request: Request,
    account: dict[str, Any] = Depends(require_admin_csrf),
) -> dict[str, Any]:
    return _transition_request(document_id=document_id, payload=payload, request=request, account=account, action="archive")


@router.post("/documents/{document_id}/restore")
async def restore_document(
    document_id: str,
    payload: TransitionPayload,
    request: Request,
    account: dict[str, Any] = Depends(require_admin_csrf),
) -> dict[str, Any]:
    return _transition_request(document_id=document_id, payload=payload, request=request, account=account, action="restore")
