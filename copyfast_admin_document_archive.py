"""Web-native Admin Internal Document Archive.

This module ports the useful *workflow* of the Bot's internal document archive
without reading its tables, Telegram file IDs/paths, or importing Bot runtime.
It owns a separate private blob root, immutable version records and an
owner-scoped local-Web-admin workflow.  It deliberately has no Core Bridge,
provider, Xu/wallet, PayOS, job, customer, finance action, notification,
public URL, hard-delete or automatic retention executor.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import threading
import uuid
from typing import Any, BinaryIO, Callable, Iterator
from urllib.parse import quote
from zipfile import BadZipFile, ZipFile

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from starlette.background import BackgroundTask

from copyfast_auth import _record_audit, _request_id, current_session, envelope, require_admin, require_admin_csrf
from copyfast_db import (
    admin_document_archive_directory,
    admin_document_archive_enabled,
    ensure_copyfast_schema,
    read_transaction,
    transaction,
    utc_now,
)


router = APIRouter(prefix="/api/v1/admin/internal-documents", tags=["Web Admin Internal Document Archive"])


POLICY_VERSION = "web_admin_internal_document_archive_v1"
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
STORAGE_KEY_PATTERN = re.compile(r"^objects/[0-9a-f]{32}\.blob$")
CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
TAG_PATTERN = re.compile(r"^[\wÀ-ỹà-ỹ][\wÀ-ỹà-ỹ ._/-]{0,47}$", re.UNICODE)
SEARCH_SECRET_PATTERN = re.compile(
    r"\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|"
    r"client[ _-]?secret|password|passphrase|authorization)\b\s*"
    r"(?:[:=]|\bis\b)\s*(?:bearer\s+)?[A-Za-z0-9_./+=:-]{8,}",
    re.IGNORECASE,
)
PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN(?: [A-Z0-9][A-Z0-9 ]*)? PRIVATE KEY-----", re.IGNORECASE)
BEARER_PATTERN = re.compile(r"\bbearer\s+[A-Za-z0-9._~+/=-]{8,}\b", re.IGNORECASE)
CARD_LIKE_PATTERN = re.compile(r"\b(?:\d[ -]?){13,19}\b")
FILESYSTEM_PATH_PATTERN = re.compile(
    r"(?:^|[\s\"'`(])(?:[A-Za-z]:[\\/]|/(?:app|bin|boot|data|etc|home|lib|mnt|opt|private|root|run|srv|tmp|usr|var|windows|users)(?:[\\/]|$))",
    re.IGNORECASE,
)


# The taxonomy mirrors the Bot's useful category/type selection.  It does not
# import Bot constants so Web remains independently deployable and can evolve
# its local policy without silently changing Bot state.
DEPARTMENTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "customers": ("Khách hàng", ("customer_profile", "customer_request", "refund_case", "custom_order", "b2b_lead")),
    "finance_accounting": ("Tài chính/Kế toán", ("revenue_export", "expense_receipt", "payos_statement", "provider_invoice", "profit_loss_report", "accounting_export")),
    "tax_invoice": ("Hóa đơn/Thuế", ("tax_prep_file", "invoice", "receipt", "tax_notice", "accountant_note", "tax_report")),
    "contracts": ("Hợp đồng", ("b2b_contract", "service_agreement", "vendor_contract", "nda", "affiliate_agreement")),
    "hr_collaborators": ("Nhân sự/CTV", ("collaborator_profile", "permission_note", "work_agreement", "work_note", "payout_record")),
    "marketing": ("Marketing", ("campaign_plan", "content_caption", "approved_video", "posting_schedule", "kpi_report", "brand_asset")),
    "tech_codex": ("Kỹ thuật/Codex", ("codex_task", "deployment_note", "env_note", "provider_doc", "bug_report", "architecture_doc", "backup_note")),
    "legal_policy": ("Pháp lý/Chính sách", ("terms", "privacy", "refund_policy", "data_policy", "ip_policy", "customer_notice")),
    "provider_api": ("Provider/API", ("provider_doc", "provider_pricing", "smoke_test", "provider_status", "integration_note", "provider_error")),
    "accounts_assets": ("Tài khoản/Tài sản", ("domain", "hosting_vps", "paid_software", "service_account", "renewal_note", "brand_asset")),
}
TYPE_LABELS = {
    "customer_profile": "Hồ sơ khách hàng", "customer_request": "Yêu cầu khách gửi", "refund_case": "Case hoàn Xu / refund", "custom_order": "Đơn custom", "b2b_lead": "Lead B2B",
    "revenue_export": "Báo cáo doanh thu", "expense_receipt": "Phiếu/biên lai chi phí", "payos_statement": "Sao kê PayOS/ngân hàng", "provider_invoice": "Hóa đơn provider", "profit_loss_report": "Báo cáo lãi/lỗ", "accounting_export": "File xuất kế toán",
    "tax_prep_file": "File chuẩn bị thuế", "invoice": "Hóa đơn", "receipt": "Biên lai", "tax_notice": "Thông báo thuế", "accountant_note": "Ghi chú kế toán", "tax_report": "Báo cáo thuế nội bộ",
    "b2b_contract": "Hợp đồng khách hàng/B2B", "service_agreement": "Thỏa thuận dịch vụ", "vendor_contract": "Hợp đồng nhà cung cấp", "nda": "NDA / bảo mật", "affiliate_agreement": "Hợp đồng affiliate/CTV",
    "collaborator_profile": "Hồ sơ CTV", "permission_note": "Phân quyền tài khoản", "work_agreement": "Thỏa thuận làm việc", "work_note": "Ghi chú công việc", "payout_record": "Thanh toán CTV",
    "campaign_plan": "Kế hoạch chiến dịch", "content_caption": "Content/caption", "approved_video": "Video đã duyệt", "posting_schedule": "Lịch đăng bài", "kpi_report": "Báo cáo KPI", "brand_asset": "Tài nguyên thương hiệu",
    "codex_task": "Task Codex", "deployment_note": "Ghi chú deploy", "env_note": "ENV note không chứa secret", "provider_doc": "Tài liệu provider", "bug_report": "Bug report", "architecture_doc": "Tài liệu kiến trúc", "backup_note": "Ghi chú backup",
    "terms": "Điều khoản sử dụng", "privacy": "Chính sách riêng tư", "refund_policy": "Chính sách hoàn Xu/refund", "data_policy": "Chính sách dữ liệu", "ip_policy": "Chính sách sở hữu trí tuệ", "customer_notice": "Thông báo khách hàng",
    "provider_pricing": "Bảng giá provider", "smoke_test": "Smoke test", "provider_status": "Trạng thái provider", "integration_note": "Ghi chú tích hợp", "provider_error": "Lỗi provider",
    "domain": "Tên miền/domain", "hosting_vps": "Hosting/VPS", "paid_software": "Phần mềm trả phí", "service_account": "Tài khoản dịch vụ", "renewal_note": "Lịch gia hạn", "brand_asset": "Tài nguyên thương hiệu",
}
DEFAULT_RETENTION_BY_DEPARTMENT = {
    "finance_accounting": "10_years", "tax_invoice": "10_years", "contracts": "10_years",
    "legal_policy": "permanent", "tech_codex": "5_years", "provider_api": "5_years", "accounts_assets": "5_years",
}
RETENTION_LABELS = frozenset({"manual_review", "3_years", "5_years", "10_years", "permanent"})
CONFIDENTIALITY_LEVELS = frozenset({"internal", "confidential", "restricted"})
DOCUMENT_STATES = frozenset({"active", "archived", "unavailable"})
ALLOWED_EXTENSIONS = frozenset({".pdf", ".docx", ".txt"})
CANONICAL_MIME_BY_EXTENSION = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}
ACCEPTED_MIME_BY_EXTENSION = {
    ".pdf": frozenset({"application/pdf"}),
    ".docx": frozenset({"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}),
    ".txt": frozenset({"text/plain"}),
}
DOCUMENT_COLUMNS = (
    "id", "owner_account_id", "department", "document_type", "title", "tags_json", "description",
    "retention_label", "confidentiality_level", "state", "current_version_id", "lifecycle_revision",
    "created_at", "updated_at", "archived_at",
)
VERSION_COLUMNS = (
    "id", "document_id", "version_number", "uploader_account_id", "original_filename", "display_name",
    "extension", "content_type", "byte_size", "sha256", "storage_key", "availability", "created_at",
)

MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_TEXT_BYTES = 2 * 1024 * 1024
MAX_ACCOUNT_BYTES = 250 * 1024 * 1024
MAX_VERSIONS_PER_DOCUMENT = 50
MAX_DOCUMENTS_PER_ADMIN = 1_000
MAX_LIST_LIMIT = 100
MAX_HISTORY_LIMIT = 100
MAX_LIST_OFFSET = 5_000
MAX_TITLE = 180
MAX_DESCRIPTION = 2_000
MAX_TAGS = 12
MAX_IDEMPOTENCY_RECORDS_PER_ADMIN = 256
IDEMPOTENCY_RETENTION = timedelta(hours=24)
MAX_DOCX_ARCHIVE_MEMBERS = 2_000
MAX_DOCX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
MAX_PDF_PAGES = 200
CHUNK_BYTES = 1024 * 1024
DOWNLOAD_MAX_CONCURRENT = 2
_DOWNLOAD_CAPACITY = threading.BoundedSemaphore(DOWNLOAD_MAX_CONCURRENT)
ORPHAN_RETENTION_SECONDS = 60 * 60

ACKNOWLEDGEMENTS = {
    "archive": "ARCHIVE INTERNAL DOCUMENT",
    "restore": "RESTORE INTERNAL DOCUMENT",
}
ACTION_LABELS = {
    "created": "Tạo hồ sơ", "version_added": "Thêm phiên bản", "metadata_updated": "Cập nhật metadata",
    "archived": "Lưu trữ", "restored": "Khôi phục", "unavailable": "Đánh dấu không khả dụng",
}


def _require_enabled() -> None:
    if not admin_document_archive_enabled():
        raise HTTPException(
            status_code=503,
            detail="Admin Internal Document Archive đang tạm dừng. Cần bật WEBAPP_ADMIN_ERP_ENABLED và WEBAPP_ADMIN_DOCUMENT_ARCHIVE_ENABLED.",
        )


def _boundary(**extra: Any) -> dict[str, Any]:
    return {
        "execution": "web_native_admin_internal_document_archive_only",
        "data_origin": "web_admin_archive_tables_and_private_volume_only",
        "external_effects": "none",
        "legacy_bot_scope": "TELEGRAM_ONLY",
        "excluded_domains": [
            "Telegram/Bot internal_documents, Telegram file ID và file path",
            "Core bridge, Xu, wallet, PayOS, provider, job, output delivery và webhook",
            "Customer/provider/payment lookup, sharing, public URL, notification, export, hard delete và auto-purge",
        ],
        **extra,
    }


def _guarded(message: str, code: str, *, status_name: str = "guarded", **data: Any) -> dict[str, Any]:
    return envelope(False, message, data=_boundary(**data), status_name=status_name, error_code=code)


def _uuid(value: Any, *, label: str) -> str:
    candidate = str(value or "").strip()
    if not UUID_PATTERN.fullmatch(candidate):
        raise HTTPException(status_code=422, detail=f"{label} không hợp lệ")
    return str(uuid.UUID(candidate))


def _idempotency_key(value: Any) -> str:
    key = str(value or "").strip()
    if not IDEMPOTENCY_PATTERN.fullmatch(key):
        raise HTTPException(status_code=422, detail="Idempotency key không hợp lệ")
    return key


def _fingerprint(value: dict[str, Any]) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _idempotency_cutoff() -> str:
    return (datetime.now(timezone.utc) - IDEMPOTENCY_RETENTION).isoformat(timespec="seconds")


def _contains_sensitive(value: str) -> bool:
    return bool(
        PRIVATE_KEY_PATTERN.search(value)
        or BEARER_PATTERN.search(value)
        or SEARCH_SECRET_PATTERN.search(value)
        or CARD_LIKE_PATTERN.search(value)
        or FILESYSTEM_PATH_PATTERN.search(value)
    )


def _text(value: Any, *, label: str, minimum: int, maximum: int, multiline: bool, allow_empty: bool = False) -> str:
    text = str(value or "")
    if not multiline and ("\r" in text or "\n" in text):
        raise ValueError(f"{label} không được chứa xuống dòng")
    text = re.sub(r"\s+", " ", text).strip() if not multiline else "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")).strip()
    if CONTROL_PATTERN.search(text) or len(text) > maximum or (not allow_empty and len(text) < minimum):
        raise ValueError(f"{label} không hợp lệ")
    if text and _contains_sensitive(text):
        raise ValueError(f"{label} không được chứa secret, số thẻ hoặc đường dẫn private")
    return text


def _department(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in DEPARTMENTS:
        raise ValueError("Nhóm hồ sơ nội bộ không hợp lệ")
    return normalized


def _document_type(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9_]{3,64}", normalized):
        raise ValueError("Loại hồ sơ nội bộ không hợp lệ")
    return normalized


def _tags(value: Any) -> list[str]:
    if not isinstance(value, list) or len(value) > MAX_TAGS:
        raise ValueError(f"Tối đa {MAX_TAGS} tag hồ sơ")
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in value:
        tag = _text(raw, label="Tag", minimum=1, maximum=48, multiline=False).lower()
        if not TAG_PATTERN.fullmatch(tag):
            raise ValueError("Tag hồ sơ không hợp lệ")
        if tag not in seen:
            normalized.append(tag)
            seen.add(tag)
    return normalized


def _retention_label(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in RETENTION_LABELS:
        raise ValueError("Nhãn lưu giữ không hợp lệ")
    return normalized


def _confidentiality_level(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in CONFIDENTIALITY_LEVELS:
        raise ValueError("Mức bảo mật không hợp lệ")
    return normalized


def _json_tags(value: Any) -> list[str]:
    try:
        parsed = json.loads(str(value or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    try:
        return _tags(parsed)
    except ValueError:
        return []


def _query_text(value: str | None) -> str:
    text = _text(value or "", label="Từ khóa tìm", minimum=0, maximum=100, multiline=False, allow_empty=True)
    return text.casefold()


def _like(value: str) -> str:
    return "%" + value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


class ArchiveError(ValueError):
    """A validation error whose public message is safe to return to an admin."""

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def _active_admin_session_in_transaction(conn: Any, *, account_id: str, session_id: str) -> None:
    """Re-check the signed admin session while holding the write transaction."""

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


def _actor_for_write(request: Request, account: dict[str, Any]) -> tuple[str, str]:
    session = current_session(request)
    session_account = session["account"]
    if str(session_account["id"]) != str(account["id"]) or session_account.get("role") != "admin":
        raise HTTPException(status_code=401, detail="Phiên quản trị không còn hợp lệ")
    return str(account["id"]), str(session["session_id"])


def _event(
    conn: Any,
    *,
    document_id: str,
    actor_account_id: str,
    action: str,
    from_state: str | None,
    to_state: str,
    lifecycle_revision: int,
    version_number: int | None = None,
    created_at: str | None = None,
) -> None:
    conn.execute(
        """INSERT INTO web_admin_archive_events
           (id, document_id, actor_account_id, action, from_state, to_state, lifecycle_revision, version_number, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            str(uuid.uuid4()), document_id, actor_account_id, action, from_state, to_state,
            lifecycle_revision, version_number, created_at or utc_now(),
        ),
    )


def _audit(
    conn: Any,
    *,
    request: Request,
    actor_account_id: str,
    document_id: str,
    action: str,
    state: str,
    version_number: int | None = None,
) -> None:
    """Record an opaque audit receipt; names, paths and document content never enter it."""

    suffix = f" version={version_number}" if version_number is not None else ""
    _record_audit(
        conn,
        account_id=actor_account_id,
        canonical_user_id=None,
        action=f"web.admin_archive.{action}",
        request_id=_request_id(request),
        target=document_id,
        detail=(
            "web-native admin internal archive lifecycle action="
            f"{action} state={state}{suffix}; no Bot, bridge, provider, payment, wallet, job, public URL or notification effect"
        ),
    )


def _fetch_document(conn: Any, *, document_id: str, owner_account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, owner_account_id, department, document_type, title, tags_json, description,
                  retention_label, confidentiality_level, state, current_version_id, lifecycle_revision,
                  created_at, updated_at, archived_at
           FROM web_admin_archive_documents
           WHERE id=? AND owner_account_id=? LIMIT 1""",
        (document_id, owner_account_id),
    ).fetchone()


def _fetch_version(conn: Any, *, version_id: str, owner_account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT v.id, v.document_id, v.version_number, v.uploader_account_id, v.original_filename,
                  v.display_name, v.extension, v.content_type, v.byte_size, v.sha256, v.storage_key,
                  v.availability, v.created_at
           FROM web_admin_archive_versions AS v
           JOIN web_admin_archive_documents AS d ON d.id=v.document_id
           WHERE v.id=? AND d.owner_account_id=? LIMIT 1""",
        (version_id, owner_account_id),
    ).fetchone()


def _version_public(row: tuple[Any, ...], *, current: bool = False) -> dict[str, Any]:
    value = dict(zip(VERSION_COLUMNS, row))
    return {
        "id": str(value["id"]),
        "version_number": int(value["version_number"]),
        "filename": str(value["display_name"]),
        "extension": str(value["extension"]),
        "content_type": str(value["content_type"]),
        "byte_size": int(value["byte_size"]),
        "availability": str(value["availability"]),
        "created_at": str(value["created_at"]),
        "is_current": current,
    }


def _document_public(
    row: tuple[Any, ...],
    *,
    current_version: tuple[Any, ...] | None = None,
    detail: bool = False,
) -> dict[str, Any]:
    value = dict(zip(DOCUMENT_COLUMNS, row))
    state = str(value["state"])
    current = _version_public(current_version, current=True) if current_version else None
    current_available = bool(current and current["availability"] == "available")
    result: dict[str, Any] = {
        "id": str(value["id"]),
        "department": str(value["department"]),
        "department_label": DEPARTMENTS.get(str(value["department"]), ("Hồ sơ nội bộ", ()))[0],
        "document_type": str(value["document_type"]),
        "document_type_label": TYPE_LABELS.get(str(value["document_type"]), "Hồ sơ nội bộ"),
        "title": str(value["title"]),
        "tags": _json_tags(value["tags_json"]),
        "retention_label": str(value["retention_label"]),
        "confidentiality_level": str(value["confidentiality_level"]),
        "state": state,
        "revision": int(value["lifecycle_revision"]),
        "created_at": str(value["created_at"]),
        "updated_at": str(value["updated_at"]),
        "archived_at": str(value["archived_at"]) if value["archived_at"] else None,
        "current_version": current,
        "permissions": {
            "can_update": state == "active",
            "can_add_version": state == "active",
            "can_download": state == "active" and current_available,
            "can_archive": state == "active",
            "can_restore": state == "archived" and current_available,
        },
    }
    if detail:
        result["description"] = str(value["description"] or "")
        result["owner_relation"] = "self"
        result["archive_policy"] = "retention metadata only; no automatic deletion"
    return result


def _current_version(conn: Any, *, current_version_id: str | None, owner_account_id: str) -> tuple[Any, ...] | None:
    return _fetch_version(conn, version_id=str(current_version_id or ""), owner_account_id=owner_account_id) if current_version_id else None


def _receipt(
    *, document_id: str, state: str, revision: int, updated_at: str, action: str, version_number: int | None = None
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "id": document_id,
        "state": state,
        "revision": revision,
        "updated_at": updated_at,
    }
    if version_number is not None:
        document["version_number"] = version_number
    return envelope(
        True,
        f"Đã {ACTION_LABELS.get(action, 'ghi nhận')} hồ sơ nội bộ.",
        data=_boundary(action=action, document=document),
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
    """Run one owner-scoped mutation once and retain only its compact receipt."""

    ensure_copyfast_schema()
    with transaction() as conn:
        _active_admin_session_in_transaction(conn, account_id=account_id, session_id=session_id)
        conn.execute("DELETE FROM web_idempotency WHERE scope LIKE ? AND created_at<?", ("web-admin-archive:%", _idempotency_cutoff()))
        existing = conn.execute(
            "SELECT response_json, request_fingerprint FROM web_idempotency WHERE scope=? AND key=?",
            (scope, key),
        ).fetchone()
        if existing:
            if not hmac.compare_digest(str(existing[1] or ""), request_fingerprint):
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho thao tác kho hồ sơ khác")
            try:
                receipt = json.loads(str(existing[0]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Receipt kho hồ sơ không hợp lệ") from exc
            if not isinstance(receipt, dict):
                raise HTTPException(status_code=409, detail="Receipt kho hồ sơ không hợp lệ")
            return receipt
        count = conn.execute("SELECT COUNT(*) FROM web_idempotency WHERE scope LIKE ?", (f"web-admin-archive:{account_id}:%",)).fetchone()
        if int(count[0] or 0) >= MAX_IDEMPOTENCY_RECORDS_PER_ADMIN:
            return _guarded("Kho receipt nội bộ đang đầy. Vui lòng thử lại sau.", "WEB_ADMIN_ARCHIVE_IDEMPOTENCY_LIMIT")
        result = operation(conn)
        if result.get("ok") is True:
            conn.execute(
                """INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (scope, key, json.dumps(result, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
            )
        return result


class ArchiveMetadataUpdatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    department: str | None = None
    document_type: str | None = None
    title: str | None = None
    tags: list[str] | None = None
    description: str | None = None
    retention_label: str | None = None
    confidentiality_level: str | None = None
    expected_revision: int = Field(ge=1, le=1_000_000)
    idempotency_key: str

    @field_validator("department")
    @classmethod
    def _valid_department(cls, value: str | None) -> str | None:
        return _department(value) if value is not None else None

    @field_validator("document_type")
    @classmethod
    def _valid_type(cls, value: str | None) -> str | None:
        return _document_type(value) if value is not None else None

    @field_validator("title")
    @classmethod
    def _valid_title(cls, value: str | None) -> str | None:
        return _text(value, label="Tiêu đề", minimum=3, maximum=MAX_TITLE, multiline=False) if value is not None else None

    @field_validator("tags")
    @classmethod
    def _valid_tags(cls, value: list[str] | None) -> list[str] | None:
        return _tags(value) if value is not None else None

    @field_validator("description")
    @classmethod
    def _valid_description(cls, value: str | None) -> str | None:
        return _text(value, label="Mô tả", minimum=0, maximum=MAX_DESCRIPTION, multiline=True, allow_empty=True) if value is not None else None

    @field_validator("retention_label")
    @classmethod
    def _valid_retention(cls, value: str | None) -> str | None:
        return _retention_label(value) if value is not None else None

    @field_validator("confidentiality_level")
    @classmethod
    def _valid_confidentiality(cls, value: str | None) -> str | None:
        return _confidentiality_level(value) if value is not None else None

    @field_validator("idempotency_key")
    @classmethod
    def _valid_key(cls, value: str) -> str:
        return _idempotency_key(value)

    @model_validator(mode="after")
    def _changed(self) -> "ArchiveMetadataUpdatePayload":
        if not ({"department", "document_type", "title", "tags", "description", "retention_label", "confidentiality_level"} & self.model_fields_set):
            raise ValueError("Cần có ít nhất một trường metadata để cập nhật")
        return self


class ArchiveTransitionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1, le=1_000_000)
    acknowledgement: str = Field(min_length=1, max_length=80)
    confirm: bool = False
    idempotency_key: str

    @field_validator("acknowledgement")
    @classmethod
    def _ack(cls, value: str) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()

    @field_validator("idempotency_key")
    @classmethod
    def _valid_key(cls, value: str) -> str:
        return _idempotency_key(value)


def _archive_root() -> Path:
    try:
        root = admin_document_archive_directory()
        root.mkdir(parents=True, exist_ok=True)
        if root.is_symlink() or not root.is_dir():
            raise RuntimeError("Private archive root không an toàn")
        for name in ("objects", ".staging"):
            child = root / name
            child.mkdir(parents=True, exist_ok=True)
            if child.is_symlink() or not child.is_dir():
                raise RuntimeError("Private archive directory không an toàn")
        return root
    except (OSError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail="Private storage của kho hồ sơ chưa sẵn sàng") from exc


def _storage_path(storage_key: str) -> Path:
    if not STORAGE_KEY_PATTERN.fullmatch(str(storage_key or "")):
        raise ValueError("Storage key kho hồ sơ không hợp lệ")
    root = _archive_root()
    path = root / Path(storage_key)
    try:
        path.resolve().relative_to(root.resolve())
    except (OSError, ValueError) as exc:
        raise ValueError("Storage key vượt private root") from exc
    return path


def _safe_filename(value: Any) -> tuple[str, str]:
    candidate = str(value or "").strip()
    if (
        not candidate or len(candidate) > 180 or CONTROL_PATTERN.search(candidate)
        or "/" in candidate or "\\" in candidate or _contains_sensitive(candidate)
    ):
        raise ArchiveError("Tên tệp hồ sơ không hợp lệ", "WEB_ADMIN_ARCHIVE_FILENAME_INVALID")
    extension = Path(candidate).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS or candidate.endswith("."):
        raise ArchiveError("Kho hồ sơ hiện chỉ nhận PDF, DOCX hoặc TXT", "WEB_ADMIN_ARCHIVE_TYPE_UNSUPPORTED")
    stem = Path(candidate).stem.strip()
    if not stem or stem in {".", ".."}:
        raise ArchiveError("Tên tệp hồ sơ không hợp lệ", "WEB_ADMIN_ARCHIVE_FILENAME_INVALID")
    return candidate, extension


def _safe_display_name(value: Any, *, fallback: str) -> str:
    if value is None or not str(value).strip():
        return fallback
    candidate = _text(value, label="Tên hiển thị tệp", minimum=1, maximum=180, multiline=False)
    if "/" in candidate or "\\" in candidate:
        raise ArchiveError("Tên hiển thị tệp không hợp lệ", "WEB_ADMIN_ARCHIVE_FILENAME_INVALID")
    expected_extension = Path(fallback).suffix.lower()
    supplied_extension = Path(candidate).suffix.lower()
    if not supplied_extension:
        candidate = f"{candidate}{expected_extension}"
    elif supplied_extension != expected_extension:
        raise ArchiveError("Tên hiển thị phải giữ đúng phần mở rộng của tệp", "WEB_ADMIN_ARCHIVE_FILENAME_INVALID")
    return candidate


def _content_type(uploaded: UploadFile, extension: str) -> str:
    declared = str(uploaded.content_type or "").strip().lower().split(";", 1)[0]
    if declared not in ACCEPTED_MIME_BY_EXTENSION[extension]:
        raise ArchiveError("Content-Type tệp hồ sơ không hợp lệ", "WEB_ADMIN_ARCHIVE_CONTENT_TYPE_INVALID")
    return CANONICAL_MIME_BY_EXTENSION[extension]


async def _stage_upload(uploaded: UploadFile) -> tuple[Path, int, str, bytes]:
    """Store an untrusted multipart part temporarily while deriving its digest.

    The caller must remove the returned staging file unless it is atomically
    promoted into `objects/` inside the successful write operation.
    """

    root = _archive_root()
    descriptor = -1
    staged_path: Path | None = None
    digest = hashlib.sha256()
    byte_size = 0
    prefix = b""
    try:
        descriptor, raw_path = tempfile.mkstemp(prefix="archive-", suffix=".upload", dir=root / ".staging")
        staged_path = Path(raw_path)
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = -1
            while True:
                chunk = await uploaded.read(CHUNK_BYTES)
                if not chunk:
                    break
                byte_size += len(chunk)
                if byte_size > MAX_FILE_BYTES:
                    raise ArchiveError("Tệp vượt giới hạn 25 MiB của kho hồ sơ", "WEB_ADMIN_ARCHIVE_FILE_TOO_LARGE")
                if len(prefix) < 4096:
                    prefix += chunk[: 4096 - len(prefix)]
                digest.update(chunk)
                handle.write(chunk)
        if byte_size <= 0:
            raise ArchiveError("Tệp hồ sơ đang rỗng", "WEB_ADMIN_ARCHIVE_FILE_EMPTY")
        return staged_path, byte_size, digest.hexdigest(), prefix
    except ArchiveError:
        if staged_path is not None:
            staged_path.unlink(missing_ok=True)
        raise
    except (OSError, RuntimeError) as exc:
        if staged_path is not None:
            staged_path.unlink(missing_ok=True)
        raise ArchiveError("Không thể ghi private storage của kho hồ sơ", "WEB_ADMIN_ARCHIVE_STORAGE_UNAVAILABLE") from exc
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        try:
            await uploaded.close()
        except (OSError, RuntimeError):
            pass


def _validate_pdf(path: Path, *, prefix: bytes) -> None:
    if not prefix.startswith(b"%PDF-"):
        raise ArchiveError("Tệp PDF không có cấu trúc hợp lệ", "WEB_ADMIN_ARCHIVE_PDF_INVALID")
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ArchiveError("Runtime kiểm tra PDF chưa sẵn sàng", "WEB_ADMIN_ARCHIVE_PDF_RUNTIME_UNAVAILABLE") from exc
    try:
        reader = PdfReader(str(path), strict=True)
        if reader.is_encrypted:
            raise ArchiveError("PDF mã hóa không được hỗ trợ trong kho hồ sơ", "WEB_ADMIN_ARCHIVE_PDF_ENCRYPTED")
        if len(reader.pages) < 1 or len(reader.pages) > MAX_PDF_PAGES:
            raise ArchiveError("PDF vượt giới hạn trang của kho hồ sơ", "WEB_ADMIN_ARCHIVE_PDF_PAGE_LIMIT")
    except ArchiveError:
        raise
    except Exception as exc:
        raise ArchiveError("Không thể xác minh cấu trúc PDF", "WEB_ADMIN_ARCHIVE_PDF_INVALID") from exc


def _validate_docx(path: Path) -> None:
    try:
        with ZipFile(path) as archive:
            members = archive.infolist()
            if not members or len(members) > MAX_DOCX_ARCHIVE_MEMBERS:
                raise ArchiveError("DOCX vượt giới hạn cấu trúc kho hồ sơ", "WEB_ADMIN_ARCHIVE_DOCX_INVALID")
            total = 0
            names: set[str] = set()
            for info in members:
                name = str(info.filename or "")
                normalized = name.replace("\\", "/")
                if not name or normalized.startswith("/") or normalized.startswith("../") or "/../" in normalized or "\x00" in normalized:
                    raise ArchiveError("DOCX chứa đường dẫn không an toàn", "WEB_ADMIN_ARCHIVE_DOCX_INVALID")
                if normalized.casefold().endswith("vbaproject.bin") or normalized.casefold().endswith(".bin"):
                    raise ArchiveError("DOCX macro/binary không được hỗ trợ", "WEB_ADMIN_ARCHIVE_DOCX_MACRO_REJECTED")
                total += max(0, int(info.file_size))
                if total > MAX_DOCX_UNCOMPRESSED_BYTES:
                    raise ArchiveError("DOCX vượt giới hạn giải nén", "WEB_ADMIN_ARCHIVE_DOCX_INVALID")
                names.add(normalized)
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise ArchiveError("DOCX không có cấu trúc Word hợp lệ", "WEB_ADMIN_ARCHIVE_DOCX_INVALID")
    except ArchiveError:
        raise
    except (BadZipFile, OSError, ValueError) as exc:
        raise ArchiveError("Không thể xác minh cấu trúc DOCX", "WEB_ADMIN_ARCHIVE_DOCX_INVALID") from exc


def _validate_txt(path: Path, *, byte_size: int) -> None:
    if byte_size > MAX_TEXT_BYTES:
        raise ArchiveError("TXT vượt giới hạn 2 MiB của kho hồ sơ", "WEB_ADMIN_ARCHIVE_TEXT_TOO_LARGE")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ArchiveError("TXT phải dùng UTF-8 hợp lệ", "WEB_ADMIN_ARCHIVE_TEXT_INVALID") from exc
    if not text.strip():
        raise ArchiveError("TXT hồ sơ đang rỗng", "WEB_ADMIN_ARCHIVE_FILE_EMPTY")
    if _contains_sensitive(text):
        raise ArchiveError("TXT không được chứa secret, số thẻ hoặc đường dẫn private", "WEB_ADMIN_ARCHIVE_DLP_REJECTED")


def _validate_staged_file(path: Path, *, extension: str, byte_size: int, prefix: bytes) -> None:
    if extension == ".pdf":
        _validate_pdf(path, prefix=prefix)
    elif extension == ".docx":
        _validate_docx(path)
    elif extension == ".txt":
        _validate_txt(path, byte_size=byte_size)
    else:  # Defensive only; extension is already allow-listed before staging.
        raise ArchiveError("Loại tệp hồ sơ không được hỗ trợ", "WEB_ADMIN_ARCHIVE_TYPE_UNSUPPORTED")


def _promote_staged_file(staged: Path, *, storage_key: str) -> Path:
    target = _storage_path(storage_key)
    if target.exists() or target.is_symlink():
        raise ArchiveError("Private object key đã tồn tại", "WEB_ADMIN_ARCHIVE_STORAGE_COLLISION")
    try:
        os.replace(staged, target)
        # `mkstemp` follows the local umask. Normalise the final private blob
        # explicitly rather than rejecting a safe upload simply because a
        # developer machine inherited a group-writable umask.
        os.chmod(target, 0o600)
        target_stat = os.stat(target, follow_symlinks=False)
        mode = stat.S_IMODE(target_stat.st_mode)
        # Windows exposes only a compatibility subset of POSIX mode bits, so
        # a `0o666` result there does not mean the private directory ACL is
        # world writable.  On POSIX keep the stricter mode check; in both
        # cases symlinks/non-regular targets are rejected above.
        if not stat.S_ISREG(target_stat.st_mode) or (os.name != "nt" and mode & 0o022):
            target.unlink(missing_ok=True)
            raise ArchiveError("Private object không an toàn", "WEB_ADMIN_ARCHIVE_STORAGE_UNAVAILABLE")
        return target
    except ArchiveError:
        raise
    except OSError as exc:
        raise ArchiveError("Không thể chốt private object của kho hồ sơ", "WEB_ADMIN_ARCHIVE_STORAGE_UNAVAILABLE") from exc


def _open_verified_private_file(path: Path, *, expected_bytes: int, expected_digest: str) -> BinaryIO | None:
    """Open one non-symlink descriptor and re-hash it before it can be delivered."""

    descriptor = -1
    stream: BinaryIO | None = None
    try:
        parent = os.lstat(path.parent)
        before = os.lstat(path)
        if stat.S_ISLNK(parent.st_mode) or not stat.S_ISDIR(parent.st_mode) or stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            return None
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0))
        pinned = os.fstat(descriptor)
        if not stat.S_ISREG(pinned.st_mode) or pinned.st_size != expected_bytes or (before.st_dev, before.st_ino) != (pinned.st_dev, pinned.st_ino):
            return None
        stream = os.fdopen(descriptor, "rb", closefd=True)
        descriptor = -1
        digest = hashlib.sha256()
        while True:
            chunk = stream.read(CHUNK_BYTES)
            if not chunk:
                break
            digest.update(chunk)
        if not hmac.compare_digest(digest.hexdigest(), expected_digest):
            return None
        stream.seek(0)
        accepted = stream
        stream = None
        return accepted
    except (OSError, ValueError):
        return None
    finally:
        if stream is not None:
            stream.close()
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass


def _seal_verified_private_file(stream: BinaryIO, *, expected_bytes: int, expected_digest: str) -> BinaryIO | None:
    """Copy a pinned blob into a temporary sealed descriptor for HTTP delivery."""

    sealed: BinaryIO | None = None
    try:
        sealed = tempfile.TemporaryFile(mode="w+b")
        digest = hashlib.sha256()
        byte_size = 0
        while True:
            chunk = stream.read(CHUNK_BYTES)
            if not chunk:
                break
            byte_size += len(chunk)
            if byte_size > expected_bytes:
                return None
            digest.update(chunk)
            sealed.write(chunk)
        if byte_size != expected_bytes or not hmac.compare_digest(digest.hexdigest(), expected_digest):
            return None
        sealed.seek(0)
        result = sealed
        sealed = None
        return result
    except (OSError, ValueError):
        return None
    finally:
        try:
            stream.close()
        except OSError:
            pass
        if sealed is not None:
            sealed.close()


def _private_chunks(stream: BinaryIO) -> Iterator[bytes]:
    try:
        while True:
            chunk = stream.read(CHUNK_BYTES)
            if not chunk:
                break
            yield chunk
    finally:
        stream.close()


def _release_download_capacity() -> None:
    _DOWNLOAD_CAPACITY.release()


def _private_download_response(stream: BinaryIO, *, byte_size: int, content_type: str, filename: str) -> StreamingResponse:
    safe_name = str(filename or "download").replace("\r", " ").replace("\n", " ").strip() or "download"
    return StreamingResponse(
        _private_chunks(stream),
        media_type=content_type,
        background=BackgroundTask(lambda: (stream.close(), _release_download_capacity())),
        headers={
            "Content-Length": str(byte_size),
            "Content-Disposition": f"attachment; filename*=utf-8''{quote(safe_name)}",
            "Cache-Control": "no-store, private",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "sandbox",
        },
    )


async def _multipart_values(request: Request, *, allowed: set[str], required: set[str]) -> tuple[dict[str, str], UploadFile]:
    """Parse an exact, single-file multipart shape instead of silently ignoring fields."""

    try:
        form = await request.form()
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Multipart hồ sơ không hợp lệ") from exc
    values: dict[str, str] = {}
    uploaded: UploadFile | None = None
    for key, raw in form.multi_items():
        if key not in allowed:
            raise HTTPException(status_code=422, detail="Multipart hồ sơ có trường không được hỗ trợ")
        if key == "file":
            # `Request.form()` yields Starlette's UploadFile implementation;
            # FastAPI's exported class is a subclass in some dependency
            # versions, so an `isinstance(..., fastapi.UploadFile)` check
            # rejects every valid multipart upload.  Require the minimal
            # trusted file interface instead, never a string form value.
            if uploaded is not None or not hasattr(raw, "filename") or not hasattr(raw, "read") or not hasattr(raw, "close"):
                raise HTTPException(status_code=422, detail="Cần đúng một tệp hồ sơ")
            uploaded = raw  # type: ignore[assignment]
            continue
        if key in values:
            raise HTTPException(status_code=422, detail="Multipart hồ sơ không được lặp trường metadata")
        if not isinstance(raw, str):
            raise HTTPException(status_code=422, detail="Metadata multipart hồ sơ không hợp lệ")
        values[key] = raw
    if uploaded is None or not required.issubset(set(values) | {"file"}):
        raise HTTPException(status_code=422, detail="Thiếu trường bắt buộc của multipart hồ sơ")
    return values, uploaded


def _parse_form_tags(value: str | None) -> list[str]:
    try:
        parsed = json.loads(value or "[]")
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ArchiveError("Tags multipart phải là JSON array", "WEB_ADMIN_ARCHIVE_TAGS_INVALID") from exc
    return _tags(parsed)


def _parse_expected_revision(value: str | None) -> int:
    try:
        revision = int(str(value or ""))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Revision hồ sơ không hợp lệ") from exc
    if revision < 1 or revision > 1_000_000:
        raise HTTPException(status_code=422, detail="Revision hồ sơ không hợp lệ")
    return revision


def _document_and_current(conn: Any, *, document_id: str, owner_account_id: str) -> tuple[tuple[Any, ...] | None, tuple[Any, ...] | None]:
    document = _fetch_document(conn, document_id=document_id, owner_account_id=owner_account_id)
    if not document:
        return None, None
    value = dict(zip(DOCUMENT_COLUMNS, document))
    return document, _current_version(conn, current_version_id=value["current_version_id"], owner_account_id=owner_account_id)


def _taxonomies() -> list[dict[str, Any]]:
    return [
        {
            "key": key,
            "label": label,
            "default_retention_label": DEFAULT_RETENTION_BY_DEPARTMENT.get(key, "3_years"),
            "document_types": [{"key": document_type, "label": TYPE_LABELS.get(document_type, document_type)} for document_type in types],
        }
        for key, (label, types) in DEPARTMENTS.items()
    ]


@router.get("/policy")
async def policy(request: Request, account: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    _require_enabled()
    del request, account
    return envelope(
        True,
        "Đã nạp policy Admin Internal Document Archive.",
        data=_boundary(
            policy_version=POLICY_VERSION,
            departments=_taxonomies(),
            lifecycle={
                "states": ["active", "archived", "unavailable"],
                "transitions": {"active": ["archived"], "archived": ["active"], "unavailable": []},
                "versioning": "Mỗi upload tạo phiên bản blob bất biến mới; không sửa hoặc xóa cứng phiên bản.",
            },
            confirmations=ACKNOWLEDGEMENTS,
            limits={
                "allowed_extensions": sorted(ALLOWED_EXTENSIONS),
                "file_bytes": MAX_FILE_BYTES,
                "account_retained_bytes": MAX_ACCOUNT_BYTES,
                "versions_per_document": MAX_VERSIONS_PER_DOCUMENT,
                "documents_per_admin": MAX_DOCUMENTS_PER_ADMIN,
                "tags": MAX_TAGS,
                "retention_labels": sorted(RETENTION_LABELS),
                "confidentiality_levels": sorted(CONFIDENTIALITY_LEVELS),
            },
            retention_notice="Nhãn lưu giữ chỉ là metadata vận hành nội bộ; không có auto-delete, auto-purge hoặc tư vấn pháp lý.",
            download_scope="Owner admin signed session only; private files are re-hashed and sealed before delivery.",
        ),
        status_name="read_only",
    )


@router.get("/summary")
async def summary(request: Request, account: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    _require_enabled()
    ensure_copyfast_schema()
    del request
    account_id = str(account["id"])
    with read_transaction() as conn:
        rows = conn.execute(
            "SELECT state, COUNT(*) FROM web_admin_archive_documents WHERE owner_account_id=? GROUP BY state",
            (account_id,),
        ).fetchall()
        retained = conn.execute(
            """SELECT COALESCE(SUM(v.byte_size), 0)
               FROM web_admin_archive_versions AS v JOIN web_admin_archive_documents AS d ON d.id=v.document_id
               WHERE d.owner_account_id=?""",
            (account_id,),
        ).fetchone()
        unavailable = conn.execute(
            """SELECT COUNT(*) FROM web_admin_archive_versions AS v JOIN web_admin_archive_documents AS d ON d.id=v.document_id
               WHERE d.owner_account_id=? AND v.availability='unavailable'""",
            (account_id,),
        ).fetchone()
    counts = {state: 0 for state in DOCUMENT_STATES}
    for state, count in rows:
        if str(state) in counts:
            counts[str(state)] = int(count or 0)
    used_bytes = int(retained[0] or 0) if retained else 0
    return envelope(
        True,
        "Đã nạp tổng quan kho hồ sơ nội bộ.",
        data=_boundary(
            summary={
                "by_state": counts,
                "retained_bytes": used_bytes,
                "retained_bytes_limit": MAX_ACCOUNT_BYTES,
                "retained_bytes_remaining": max(0, MAX_ACCOUNT_BYTES - used_bytes),
                "unavailable_versions": int(unavailable[0] or 0) if unavailable else 0,
                "external_sync": "none",
            },
            scope="owner_scoped_web_admin_archive_metadata",
        ),
        status_name="read_only",
    )


@router.get("/documents")
async def list_documents(
    request: Request,
    department: str = Query("all", max_length=32),
    document_type: str = Query("all", max_length=64),
    state: str = Query("all", max_length=24),
    q: str | None = Query(None, max_length=100),
    limit: int = Query(30, ge=1, le=MAX_LIST_LIMIT),
    offset: int = Query(0, ge=0, le=MAX_LIST_OFFSET),
    account: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    _require_enabled()
    ensure_copyfast_schema()
    del request
    account_id = str(account["id"])
    normalized_department = str(department or "all").strip().lower()
    normalized_type = str(document_type or "all").strip().lower()
    normalized_state = str(state or "all").strip().lower()
    if normalized_department != "all" and normalized_department not in DEPARTMENTS:
        raise HTTPException(status_code=422, detail="Bộ lọc nhóm hồ sơ nội bộ không hợp lệ")
    if normalized_type != "all" and normalized_type not in TYPE_LABELS:
        raise HTTPException(status_code=422, detail="Bộ lọc loại hồ sơ nội bộ không hợp lệ")
    if normalized_department != "all" and normalized_type != "all" and normalized_type not in DEPARTMENTS[normalized_department][1]:
        raise HTTPException(status_code=422, detail="Loại hồ sơ không thuộc nhóm đã chọn")
    if normalized_state != "all" and normalized_state not in DOCUMENT_STATES:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái hồ sơ không hợp lệ")
    query_text = _query_text(q)
    clauses = ["d.owner_account_id=?"]
    params: list[Any] = [account_id]
    if normalized_department != "all":
        clauses.append("d.department=?")
        params.append(normalized_department)
    if normalized_type != "all":
        clauses.append("d.document_type=?")
        params.append(normalized_type)
    if normalized_state != "all":
        clauses.append("d.state=?")
        params.append(normalized_state)
    if query_text:
        clauses.append("(d.title LIKE ? ESCAPE '\\' OR d.tags_json LIKE ? ESCAPE '\\' OR d.description LIKE ? ESCAPE '\\' OR v.display_name LIKE ? ESCAPE '\\')")
        params.extend((_like(query_text), _like(query_text), _like(query_text), _like(query_text)))
    where = " AND ".join(clauses)
    with read_transaction() as conn:
        rows = conn.execute(
            f"""SELECT d.id, d.owner_account_id, d.department, d.document_type, d.title, d.tags_json, d.description,
                       d.retention_label, d.confidentiality_level, d.state, d.current_version_id, d.lifecycle_revision,
                       d.created_at, d.updated_at, d.archived_at,
                       v.id, v.document_id, v.version_number, v.uploader_account_id, v.original_filename, v.display_name,
                       v.extension, v.content_type, v.byte_size, v.sha256, v.storage_key, v.availability, v.created_at
                FROM web_admin_archive_documents AS d
                LEFT JOIN web_admin_archive_versions AS v ON v.id=d.current_version_id
                WHERE {where}
                ORDER BY d.updated_at DESC, d.id DESC LIMIT ? OFFSET ?""",
            [*params, int(limit) + 1, int(offset)],
        ).fetchall()
    has_more = len(rows) > int(limit)
    documents = [
        _document_public(tuple(row[: len(DOCUMENT_COLUMNS)]), current_version=tuple(row[len(DOCUMENT_COLUMNS):]) if row[len(DOCUMENT_COLUMNS)] else None)
        for row in rows[: int(limit)]
    ]
    return envelope(
        True,
        "Đã nạp danh sách kho hồ sơ nội bộ.",
        data=_boundary(
            documents=documents,
            has_more=has_more,
            next_offset=int(offset) + int(limit) if has_more else None,
            filters={"department": normalized_department, "document_type": normalized_type, "state": normalized_state, "q": query_text},
        ),
        status_name="read_only",
    )


@router.get("/documents/{document_id}")
async def get_document(document_id: str, request: Request, account: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    _require_enabled()
    document_id = _uuid(document_id, label="Mã hồ sơ nội bộ")
    ensure_copyfast_schema()
    del request
    account_id = str(account["id"])
    with read_transaction() as conn:
        document, current = _document_and_current(conn, document_id=document_id, owner_account_id=account_id)
    if not document:
        return _guarded("Không tìm thấy hồ sơ nội bộ đang có quyền truy cập.", "WEB_ADMIN_ARCHIVE_DOCUMENT_NOT_FOUND")
    return envelope(True, "Đã nạp hồ sơ nội bộ.", data=_boundary(document=_document_public(document, current_version=current, detail=True)), status_name="read_only")


@router.get("/documents/{document_id}/versions")
async def list_versions(
    document_id: str,
    request: Request,
    limit: int = Query(30, ge=1, le=MAX_HISTORY_LIMIT),
    offset: int = Query(0, ge=0, le=MAX_LIST_OFFSET),
    account: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    _require_enabled()
    document_id = _uuid(document_id, label="Mã hồ sơ nội bộ")
    ensure_copyfast_schema()
    del request
    account_id = str(account["id"])
    with read_transaction() as conn:
        document = _fetch_document(conn, document_id=document_id, owner_account_id=account_id)
        rows = conn.execute(
            """SELECT id, document_id, version_number, uploader_account_id, original_filename, display_name,
                      extension, content_type, byte_size, sha256, storage_key, availability, created_at
               FROM web_admin_archive_versions WHERE document_id=? ORDER BY version_number DESC, id DESC LIMIT ? OFFSET ?""",
            (document_id, int(limit) + 1, int(offset)),
        ).fetchall() if document else []
    if not document:
        return _guarded("Không tìm thấy hồ sơ nội bộ đang có quyền truy cập.", "WEB_ADMIN_ARCHIVE_DOCUMENT_NOT_FOUND")
    current_id = str(dict(zip(DOCUMENT_COLUMNS, document))["current_version_id"] or "")
    has_more = len(rows) > int(limit)
    return envelope(
        True,
        "Đã nạp phiên bản hồ sơ nội bộ.",
        data=_boundary(
            document_id=document_id,
            versions=[_version_public(tuple(row), current=str(row[0]) == current_id) for row in rows[: int(limit)]],
            immutable_history=True,
            has_more=has_more,
            next_offset=int(offset) + int(limit) if has_more else None,
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
    document_id = _uuid(document_id, label="Mã hồ sơ nội bộ")
    ensure_copyfast_schema()
    del request
    account_id = str(account["id"])
    with read_transaction() as conn:
        document = _fetch_document(conn, document_id=document_id, owner_account_id=account_id)
        rows = conn.execute(
            """SELECT id, actor_account_id, action, from_state, to_state, lifecycle_revision, version_number, created_at
               FROM web_admin_archive_events WHERE document_id=? ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?""",
            (document_id, int(limit) + 1, int(offset)),
        ).fetchall() if document else []
    if not document:
        return _guarded("Không tìm thấy hồ sơ nội bộ đang có quyền truy cập.", "WEB_ADMIN_ARCHIVE_DOCUMENT_NOT_FOUND")
    has_more = len(rows) > int(limit)
    return envelope(
        True,
        "Đã nạp audit lifecycle kho hồ sơ đã redaction.",
        data=_boundary(
            document_id=document_id,
            events=[
                {
                    "id": str(row[0]), "actor_relation": "self" if str(row[1]) == account_id else "another_admin",
                    "action": str(row[2]), "action_label": ACTION_LABELS.get(str(row[2]), "Cập nhật lifecycle"),
                    "from_state": str(row[3]) if row[3] else None, "to_state": str(row[4]),
                    "revision": int(row[5]), "version_number": int(row[6]) if row[6] is not None else None, "created_at": str(row[7]),
                }
                for row in rows[: int(limit)]
            ],
            actor_identity="redacted_to_self_or_another_admin", has_more=has_more,
            next_offset=int(offset) + int(limit) if has_more else None,
        ),
        status_name="read_only",
    )


@router.post("/documents/upload")
async def upload_document(
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    account: dict[str, Any] = Depends(require_admin_csrf),
) -> dict[str, Any]:
    _require_enabled()
    key = _idempotency_key(idempotency_key)
    values, uploaded = await _multipart_values(
        request,
        allowed={"file", "department", "document_type", "title", "tags_json", "description", "retention_label", "confidentiality_level"},
        required={"department", "document_type", "title"},
    )
    try:
        department = _department(values["department"])
        document_type = _document_type(values["document_type"])
        if document_type not in DEPARTMENTS[department][1]:
            raise ArchiveError("Loại hồ sơ không thuộc nhóm đã chọn", "WEB_ADMIN_ARCHIVE_TYPE_MISMATCH")
        title = _text(values["title"], label="Tiêu đề", minimum=3, maximum=MAX_TITLE, multiline=False)
        tags = _parse_form_tags(values.get("tags_json"))
        description = _text(values.get("description", ""), label="Mô tả", minimum=0, maximum=MAX_DESCRIPTION, multiline=True, allow_empty=True)
        retention_label = _retention_label(values.get("retention_label") or DEFAULT_RETENTION_BY_DEPARTMENT.get(department, "3_years"))
        confidentiality_level = _confidentiality_level(values.get("confidentiality_level") or "internal")
        original_filename, extension = _safe_filename(uploaded.filename)
        content_type = _content_type(uploaded, extension)
        staged, byte_size, digest, prefix = await _stage_upload(uploaded)
        try:
            await run_in_threadpool(_validate_staged_file, staged, extension=extension, byte_size=byte_size, prefix=prefix)
        except Exception:
            staged.unlink(missing_ok=True)
            raise
    except ArchiveError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    actor_account_id, session_id = _actor_for_write(request, account)
    fingerprint = _fingerprint(
        {
            "department": department, "document_type": document_type, "title": title, "tags": tags,
            "description": description, "retention_label": retention_label, "confidentiality_level": confidentiality_level,
            "filename": original_filename, "content_type": content_type, "byte_size": byte_size, "sha256": digest,
        }
    )
    scope = f"web-admin-archive:{actor_account_id}:document:create"
    storage_key = f"objects/{uuid.uuid4().hex}.blob"
    promoted = False
    committed = False

    def operation(conn: Any) -> dict[str, Any]:
        nonlocal promoted
        document_count = conn.execute(
            "SELECT COUNT(*) FROM web_admin_archive_documents WHERE owner_account_id=?", (actor_account_id,)
        ).fetchone()
        if int(document_count[0] or 0) >= MAX_DOCUMENTS_PER_ADMIN:
            return _guarded("Đã đạt giới hạn số hồ sơ cho quản trị viên hiện tại.", "WEB_ADMIN_ARCHIVE_DOCUMENT_LIMIT")
        retained = conn.execute(
            """SELECT COALESCE(SUM(v.byte_size), 0) FROM web_admin_archive_versions AS v
               JOIN web_admin_archive_documents AS d ON d.id=v.document_id WHERE d.owner_account_id=?""",
            (actor_account_id,),
        ).fetchone()
        if int(retained[0] or 0) + byte_size > MAX_ACCOUNT_BYTES:
            return _guarded("Dung lượng private archive còn lại không đủ cho tệp này.", "WEB_ADMIN_ARCHIVE_QUOTA_EXCEEDED")
        now = utc_now()
        document_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        _promote_staged_file(staged, storage_key=storage_key)
        promoted = True
        conn.execute(
            """INSERT INTO web_admin_archive_documents
               (id, owner_account_id, department, document_type, title, tags_json, description, retention_label,
                confidentiality_level, state, current_version_id, lifecycle_revision, created_at, updated_at, archived_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, 1, ?, ?, NULL)""",
            (document_id, actor_account_id, department, document_type, title, json.dumps(tags, ensure_ascii=False, separators=(",", ":")),
             description, retention_label, confidentiality_level, version_id, now, now),
        )
        conn.execute(
            """INSERT INTO web_admin_archive_versions
               (id, document_id, version_number, uploader_account_id, original_filename, display_name, extension,
                content_type, byte_size, sha256, storage_key, availability, created_at)
               VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, 'available', ?)""",
            (version_id, document_id, actor_account_id, original_filename, original_filename, extension, content_type, byte_size, digest, storage_key, now),
        )
        _event(conn, document_id=document_id, actor_account_id=actor_account_id, action="created", from_state=None, to_state="active", lifecycle_revision=1, version_number=1, created_at=now)
        _audit(conn, request=request, actor_account_id=actor_account_id, document_id=document_id, action="created", state="active", version_number=1)
        return _receipt(document_id=document_id, state="active", revision=1, updated_at=now, action="created", version_number=1)

    try:
        result = _idempotent(scope=scope, account_id=actor_account_id, session_id=session_id, key=key, request_fingerprint=fingerprint, operation=operation)
        committed = promoted and result.get("ok") is True
        return result
    except ArchiveError as exc:
        raise HTTPException(status_code=503, detail=exc.message) from exc
    finally:
        if not promoted:
            staged.unlink(missing_ok=True)
        elif not committed:
            # The blob is promoted before its SQLite row so a DB error never
            # produces a metadata row that points at a missing object. If the
            # transaction rolls back afterwards, remove only this opaque,
            # request-local orphan; reconciliation is the fallback if the
            # process crashes before this finally block.
            try:
                _storage_path(storage_key).unlink(missing_ok=True)
            except (OSError, ValueError, HTTPException):
                pass


@router.patch("/documents/{document_id}")
async def update_document(
    document_id: str,
    payload: ArchiveMetadataUpdatePayload,
    request: Request,
    account: dict[str, Any] = Depends(require_admin_csrf),
) -> dict[str, Any]:
    _require_enabled()
    document_id = _uuid(document_id, label="Mã hồ sơ nội bộ")
    actor_account_id, session_id = _actor_for_write(request, account)
    supplied = payload.model_dump(exclude_unset=True)
    fingerprint = _fingerprint({"document_id": document_id, **supplied})
    scope = f"web-admin-archive:{actor_account_id}:document:{document_id}:metadata"

    def operation(conn: Any) -> dict[str, Any]:
        current = _fetch_document(conn, document_id=document_id, owner_account_id=actor_account_id)
        if not current:
            return _guarded("Không tìm thấy hồ sơ có thể cập nhật.", "WEB_ADMIN_ARCHIVE_DOCUMENT_NOT_FOUND")
        value = dict(zip(DOCUMENT_COLUMNS, current))
        if str(value["state"]) != "active":
            return _guarded("Chỉ hồ sơ active mới được cập nhật metadata.", "WEB_ADMIN_ARCHIVE_ACTIVE_REQUIRED")
        if int(value["lifecycle_revision"]) != payload.expected_revision:
            return _guarded("Hồ sơ đã có revision mới. Hãy tải lại trước khi tiếp tục.", "WEB_ADMIN_ARCHIVE_DOCUMENT_CONFLICT")
        department = payload.department if "department" in supplied else str(value["department"])
        document_type = payload.document_type if "document_type" in supplied else str(value["document_type"])
        if document_type not in DEPARTMENTS[department][1]:
            return _guarded("Loại hồ sơ không thuộc nhóm đã chọn.", "WEB_ADMIN_ARCHIVE_TYPE_MISMATCH")
        title = payload.title if "title" in supplied else str(value["title"])
        tags = payload.tags if "tags" in supplied else _json_tags(value["tags_json"])
        description = payload.description if "description" in supplied else str(value["description"] or "")
        retention_label = payload.retention_label if "retention_label" in supplied else str(value["retention_label"])
        confidentiality_level = payload.confidentiality_level if "confidentiality_level" in supplied else str(value["confidentiality_level"])
        now = utc_now()
        next_revision = int(value["lifecycle_revision"]) + 1
        updated = conn.execute(
            """UPDATE web_admin_archive_documents
               SET department=?, document_type=?, title=?, tags_json=?, description=?, retention_label=?, confidentiality_level=?,
                   lifecycle_revision=?, updated_at=?
               WHERE id=? AND owner_account_id=? AND state='active' AND lifecycle_revision=?""",
            (department, document_type, title, json.dumps(tags, ensure_ascii=False, separators=(",", ":")), description, retention_label,
             confidentiality_level, next_revision, now, document_id, actor_account_id, payload.expected_revision),
        )
        if int(updated.rowcount or 0) != 1:
            return _guarded("Hồ sơ đã thay đổi đồng thời. Hãy tải lại trước khi tiếp tục.", "WEB_ADMIN_ARCHIVE_DOCUMENT_CONFLICT")
        _event(conn, document_id=document_id, actor_account_id=actor_account_id, action="metadata_updated", from_state="active", to_state="active", lifecycle_revision=next_revision, created_at=now)
        _audit(conn, request=request, actor_account_id=actor_account_id, document_id=document_id, action="metadata_updated", state="active")
        return _receipt(document_id=document_id, state="active", revision=next_revision, updated_at=now, action="metadata_updated")

    return _idempotent(scope=scope, account_id=actor_account_id, session_id=session_id, key=payload.idempotency_key, request_fingerprint=fingerprint, operation=operation)


@router.post("/documents/{document_id}/versions/upload")
async def upload_version(
    document_id: str,
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    account: dict[str, Any] = Depends(require_admin_csrf),
) -> dict[str, Any]:
    _require_enabled()
    document_id = _uuid(document_id, label="Mã hồ sơ nội bộ")
    key = _idempotency_key(idempotency_key)
    values, uploaded = await _multipart_values(request, allowed={"file", "display_name", "expected_revision"}, required={"expected_revision"})
    expected_revision = _parse_expected_revision(values.get("expected_revision"))
    try:
        original_filename, extension = _safe_filename(uploaded.filename)
        display_name = _safe_display_name(values.get("display_name"), fallback=original_filename)
        content_type = _content_type(uploaded, extension)
        staged, byte_size, digest, prefix = await _stage_upload(uploaded)
        try:
            await run_in_threadpool(_validate_staged_file, staged, extension=extension, byte_size=byte_size, prefix=prefix)
        except Exception:
            staged.unlink(missing_ok=True)
            raise
    except ArchiveError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
    actor_account_id, session_id = _actor_for_write(request, account)
    fingerprint = _fingerprint({"document_id": document_id, "expected_revision": expected_revision, "display_name": display_name, "filename": original_filename, "content_type": content_type, "byte_size": byte_size, "sha256": digest})
    scope = f"web-admin-archive:{actor_account_id}:document:{document_id}:version"
    storage_key = f"objects/{uuid.uuid4().hex}.blob"
    promoted = False
    committed = False

    def operation(conn: Any) -> dict[str, Any]:
        nonlocal promoted
        document = _fetch_document(conn, document_id=document_id, owner_account_id=actor_account_id)
        if not document:
            return _guarded("Không tìm thấy hồ sơ có thể thêm phiên bản.", "WEB_ADMIN_ARCHIVE_DOCUMENT_NOT_FOUND")
        value = dict(zip(DOCUMENT_COLUMNS, document))
        if str(value["state"]) != "active":
            return _guarded("Chỉ hồ sơ active mới nhận phiên bản mới.", "WEB_ADMIN_ARCHIVE_ACTIVE_REQUIRED")
        if int(value["lifecycle_revision"]) != expected_revision:
            return _guarded("Hồ sơ đã có revision mới. Hãy tải lại trước khi tiếp tục.", "WEB_ADMIN_ARCHIVE_DOCUMENT_CONFLICT")
        version_count = conn.execute("SELECT COUNT(*) FROM web_admin_archive_versions WHERE document_id=?", (document_id,)).fetchone()
        if int(version_count[0] or 0) >= MAX_VERSIONS_PER_DOCUMENT:
            return _guarded("Hồ sơ đã đạt giới hạn phiên bản bất biến.", "WEB_ADMIN_ARCHIVE_VERSION_LIMIT")
        retained = conn.execute(
            """SELECT COALESCE(SUM(v.byte_size), 0) FROM web_admin_archive_versions AS v
               JOIN web_admin_archive_documents AS d ON d.id=v.document_id WHERE d.owner_account_id=?""", (actor_account_id,)
        ).fetchone()
        if int(retained[0] or 0) + byte_size > MAX_ACCOUNT_BYTES:
            return _guarded("Dung lượng private archive còn lại không đủ cho phiên bản này.", "WEB_ADMIN_ARCHIVE_QUOTA_EXCEEDED")
        next_version = int(version_count[0] or 0) + 1
        next_revision = int(value["lifecycle_revision"]) + 1
        now = utc_now()
        version_id = str(uuid.uuid4())
        _promote_staged_file(staged, storage_key=storage_key)
        promoted = True
        conn.execute(
            """INSERT INTO web_admin_archive_versions
               (id, document_id, version_number, uploader_account_id, original_filename, display_name, extension,
                content_type, byte_size, sha256, storage_key, availability, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'available', ?)""",
            (version_id, document_id, next_version, actor_account_id, original_filename, display_name, extension, content_type, byte_size, digest, storage_key, now),
        )
        updated = conn.execute(
            """UPDATE web_admin_archive_documents SET current_version_id=?, lifecycle_revision=?, updated_at=?
               WHERE id=? AND owner_account_id=? AND state='active' AND lifecycle_revision=?""",
            (version_id, next_revision, now, document_id, actor_account_id, expected_revision),
        )
        if int(updated.rowcount or 0) != 1:
            raise ArchiveError("Hồ sơ đã thay đổi đồng thời", "WEB_ADMIN_ARCHIVE_DOCUMENT_CONFLICT")
        _event(conn, document_id=document_id, actor_account_id=actor_account_id, action="version_added", from_state="active", to_state="active", lifecycle_revision=next_revision, version_number=next_version, created_at=now)
        _audit(conn, request=request, actor_account_id=actor_account_id, document_id=document_id, action="version_added", state="active", version_number=next_version)
        return _receipt(document_id=document_id, state="active", revision=next_revision, updated_at=now, action="version_added", version_number=next_version)

    try:
        result = _idempotent(scope=scope, account_id=actor_account_id, session_id=session_id, key=key, request_fingerprint=fingerprint, operation=operation)
        committed = promoted and result.get("ok") is True
        return result
    except ArchiveError as exc:
        raise HTTPException(status_code=409 if exc.code == "WEB_ADMIN_ARCHIVE_DOCUMENT_CONFLICT" else 503, detail=exc.message) from exc
    finally:
        if not promoted:
            staged.unlink(missing_ok=True)
        elif not committed:
            try:
                _storage_path(storage_key).unlink(missing_ok=True)
            except (OSError, ValueError, HTTPException):
                pass


def _transition_document(
    *,
    document_id: str,
    payload: ArchiveTransitionPayload,
    request: Request,
    account: dict[str, Any],
    action: str,
) -> dict[str, Any]:
    _require_enabled()
    document_id = _uuid(document_id, label="Mã hồ sơ nội bộ")
    if not payload.confirm or payload.acknowledgement != ACKNOWLEDGEMENTS[action]:
        return _guarded("Cần xác nhận đúng câu xác nhận trước khi thay đổi lifecycle hồ sơ.", "WEB_ADMIN_ARCHIVE_CONFIRMATION_REQUIRED")
    actor_account_id, session_id = _actor_for_write(request, account)
    fingerprint = _fingerprint({"document_id": document_id, "action": action, "expected_revision": payload.expected_revision})
    scope = f"web-admin-archive:{actor_account_id}:document:{document_id}:{action}"
    required_state = "active" if action == "archive" else "archived"
    next_state = "archived" if action == "archive" else "active"
    recorded_action = "archived" if action == "archive" else "restored"

    def operation(conn: Any) -> dict[str, Any]:
        document, current = _document_and_current(conn, document_id=document_id, owner_account_id=actor_account_id)
        if not document:
            return _guarded("Không tìm thấy hồ sơ có thể thay đổi lifecycle.", "WEB_ADMIN_ARCHIVE_DOCUMENT_NOT_FOUND")
        value = dict(zip(DOCUMENT_COLUMNS, document))
        if str(value["state"]) != required_state:
            return _guarded("Trạng thái hồ sơ không phù hợp với thao tác này.", "WEB_ADMIN_ARCHIVE_STATE_CONFLICT")
        if int(value["lifecycle_revision"]) != payload.expected_revision:
            return _guarded("Hồ sơ đã có revision mới. Hãy tải lại trước khi tiếp tục.", "WEB_ADMIN_ARCHIVE_DOCUMENT_CONFLICT")
        if action == "restore" and (not current or str(dict(zip(VERSION_COLUMNS, current))["availability"]) != "available"):
            return _guarded("Không thể khôi phục khi phiên bản hiện tại chưa qua kiểm tra integrity.", "WEB_ADMIN_ARCHIVE_CURRENT_VERSION_UNAVAILABLE")
        now = utc_now()
        next_revision = int(value["lifecycle_revision"]) + 1
        archived_at = now if action == "archive" else None
        updated = conn.execute(
            """UPDATE web_admin_archive_documents SET state=?, archived_at=?, lifecycle_revision=?, updated_at=?
               WHERE id=? AND owner_account_id=? AND state=? AND lifecycle_revision=?""",
            (next_state, archived_at, next_revision, now, document_id, actor_account_id, required_state, payload.expected_revision),
        )
        if int(updated.rowcount or 0) != 1:
            return _guarded("Hồ sơ đã thay đổi đồng thời. Hãy tải lại trước khi tiếp tục.", "WEB_ADMIN_ARCHIVE_DOCUMENT_CONFLICT")
        version_number = int(dict(zip(VERSION_COLUMNS, current))["version_number"]) if current else None
        _event(conn, document_id=document_id, actor_account_id=actor_account_id, action=recorded_action, from_state=required_state, to_state=next_state, lifecycle_revision=next_revision, version_number=version_number, created_at=now)
        _audit(conn, request=request, actor_account_id=actor_account_id, document_id=document_id, action=recorded_action, state=next_state, version_number=version_number)
        return _receipt(document_id=document_id, state=next_state, revision=next_revision, updated_at=now, action=recorded_action, version_number=version_number)

    return _idempotent(scope=scope, account_id=actor_account_id, session_id=session_id, key=payload.idempotency_key, request_fingerprint=fingerprint, operation=operation)


@router.post("/documents/{document_id}/archive")
async def archive_document(
    document_id: str,
    payload: ArchiveTransitionPayload,
    request: Request,
    account: dict[str, Any] = Depends(require_admin_csrf),
) -> dict[str, Any]:
    return _transition_document(document_id=document_id, payload=payload, request=request, account=account, action="archive")


@router.post("/documents/{document_id}/restore")
async def restore_document(
    document_id: str,
    payload: ArchiveTransitionPayload,
    request: Request,
    account: dict[str, Any] = Depends(require_admin_csrf),
) -> dict[str, Any]:
    return _transition_document(document_id=document_id, payload=payload, request=request, account=account, action="restore")


def _mark_version_unavailable(
    *,
    document_id: str,
    version_id: str,
    request: Request,
    actor_account_id: str,
    session_id: str,
) -> None:
    """Fail closed after a private file verification failure; never disclose why."""

    ensure_copyfast_schema()
    with transaction() as conn:
        _active_admin_session_in_transaction(conn, account_id=actor_account_id, session_id=session_id)
        document = _fetch_document(conn, document_id=document_id, owner_account_id=actor_account_id)
        if not document:
            return
        value = dict(zip(DOCUMENT_COLUMNS, document))
        version = _fetch_version(conn, version_id=version_id, owner_account_id=actor_account_id)
        if not version:
            return
        version_value = dict(zip(VERSION_COLUMNS, version))
        now = utc_now()
        conn.execute("UPDATE web_admin_archive_versions SET availability='unavailable' WHERE id=? AND document_id=?", (version_id, document_id))
        if str(value["state"]) != "unavailable":
            revision = int(value["lifecycle_revision"]) + 1
            conn.execute(
                """UPDATE web_admin_archive_documents SET state='unavailable', lifecycle_revision=?, updated_at=?
                   WHERE id=? AND owner_account_id=?""",
                (revision, now, document_id, actor_account_id),
            )
            _event(conn, document_id=document_id, actor_account_id=actor_account_id, action="unavailable", from_state=str(value["state"]), to_state="unavailable", lifecycle_revision=revision, version_number=int(version_value["version_number"]), created_at=now)
            _audit(conn, request=request, actor_account_id=actor_account_id, document_id=document_id, action="unavailable", state="unavailable", version_number=int(version_value["version_number"]))


async def _download_version(
    *,
    document_id: str,
    version: tuple[Any, ...],
    request: Request,
    actor_account_id: str,
    session_id: str,
) -> dict[str, Any] | StreamingResponse:
    value = dict(zip(VERSION_COLUMNS, version))
    try:
        path = _storage_path(str(value["storage_key"]))
    except HTTPException:
        return _guarded("Private storage của kho hồ sơ chưa sẵn sàng.", "WEB_ADMIN_ARCHIVE_STORAGE_UNAVAILABLE")
    except ValueError:
        path = None
    if path is None or str(value["availability"]) != "available":
        _mark_version_unavailable(document_id=document_id, version_id=str(value["id"]), request=request, actor_account_id=actor_account_id, session_id=session_id)
        return _guarded("Tệp private không qua được kiểm tra integrity.", "WEB_ADMIN_ARCHIVE_FILE_UNAVAILABLE")
    if not _DOWNLOAD_CAPACITY.acquire(blocking=False):
        return _guarded("Kho private đang có nhiều lượt tải. Vui lòng thử lại sau.", "WEB_ADMIN_ARCHIVE_DOWNLOAD_BUSY")
    stream: BinaryIO | None = None
    sealed: BinaryIO | None = None
    handed_off = False
    try:
        stream = await run_in_threadpool(
            _open_verified_private_file, path, expected_bytes=int(value["byte_size"]), expected_digest=str(value["sha256"])
        )
        if stream is None:
            _mark_version_unavailable(document_id=document_id, version_id=str(value["id"]), request=request, actor_account_id=actor_account_id, session_id=session_id)
            return _guarded("Tệp private không qua được kiểm tra integrity.", "WEB_ADMIN_ARCHIVE_FILE_UNAVAILABLE")
        sealed = await run_in_threadpool(
            _seal_verified_private_file, stream, expected_bytes=int(value["byte_size"]), expected_digest=str(value["sha256"])
        )
        stream = None
        if sealed is None:
            _mark_version_unavailable(document_id=document_id, version_id=str(value["id"]), request=request, actor_account_id=actor_account_id, session_id=session_id)
            return _guarded("Tệp private không qua được kiểm tra integrity.", "WEB_ADMIN_ARCHIVE_FILE_UNAVAILABLE")
        response = _private_download_response(sealed, byte_size=int(value["byte_size"]), content_type=str(value["content_type"]), filename=str(value["display_name"]))
        sealed = None
        handed_off = True
        return response
    finally:
        if stream is not None:
            stream.close()
        if sealed is not None:
            sealed.close()
        if not handed_off:
            _release_download_capacity()


@router.get("/documents/{document_id}/download", response_model=None)
async def download_current_document(
    document_id: str,
    request: Request,
    account: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any] | StreamingResponse:
    _require_enabled()
    document_id = _uuid(document_id, label="Mã hồ sơ nội bộ")
    ensure_copyfast_schema()
    actor_account_id, session_id = _actor_for_write(request, account)
    with read_transaction() as conn:
        document, version = _document_and_current(conn, document_id=document_id, owner_account_id=actor_account_id)
    if not document or not version or str(dict(zip(DOCUMENT_COLUMNS, document))["state"]) != "active":
        return _guarded("Không tìm thấy hồ sơ active có thể tải.", "WEB_ADMIN_ARCHIVE_DOCUMENT_NOT_FOUND")
    return await _download_version(document_id=document_id, version=version, request=request, actor_account_id=actor_account_id, session_id=session_id)


@router.get("/versions/{version_id}/download", response_model=None)
async def download_version(
    version_id: str,
    request: Request,
    account: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any] | StreamingResponse:
    _require_enabled()
    version_id = _uuid(version_id, label="Mã phiên bản hồ sơ")
    ensure_copyfast_schema()
    actor_account_id, session_id = _actor_for_write(request, account)
    with read_transaction() as conn:
        version = _fetch_version(conn, version_id=version_id, owner_account_id=actor_account_id)
        document = _fetch_document(conn, document_id=str(version[1]), owner_account_id=actor_account_id) if version else None
    if not document or not version or str(dict(zip(DOCUMENT_COLUMNS, document))["state"]) != "active":
        return _guarded("Không tìm thấy phiên bản active có thể tải.", "WEB_ADMIN_ARCHIVE_DOCUMENT_NOT_FOUND")
    return await _download_version(document_id=str(version[1]), version=version, request=request, actor_account_id=actor_account_id, session_id=session_id)


def reconcile_admin_document_archive_storage() -> None:
    """Safely remove old orphan staging/blob files only from the dedicated root.

    The routine never deletes a metadata-referenced version and deliberately
    does not implement retention expiry. It is best-effort and opt-in, so a
    missing Railway volume cannot make application startup unhealthy.
    """

    if not admin_document_archive_enabled():
        return
    ensure_copyfast_schema()
    try:
        root = _archive_root()
    except HTTPException:
        return
    with read_transaction() as conn:
        referenced = {str(row[0]) for row in conn.execute("SELECT storage_key FROM web_admin_archive_versions").fetchall()}
    cutoff = datetime.now(timezone.utc).timestamp() - ORPHAN_RETENTION_SECONDS
    for directory, is_objects in ((root / ".staging", False), (root / "objects", True)):
        try:
            candidates = list(directory.iterdir())
        except OSError:
            continue
        for candidate in candidates:
            try:
                if not candidate.is_file() or candidate.is_symlink() or candidate.stat().st_mtime > cutoff:
                    continue
                relative = candidate.resolve().relative_to(root.resolve()).as_posix()
            except (OSError, ValueError):
                continue
            if is_objects and relative in referenced:
                continue
            try:
                candidate.unlink(missing_ok=True)
            except OSError:
                continue
