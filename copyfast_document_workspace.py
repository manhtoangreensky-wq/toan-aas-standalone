"""Private Web-native Document & PDF authoring workspace.

This module is intentionally a signed-account planning surface.  It records
document briefs, workflow plans, immutable revisions and opaque references to
already-owned Asset Vault metadata.  It does not ingest a browser file, call a
provider/Bot bridge, perform OCR/translation, create a job, charge a wallet or
manufacture a document/output.  The existing ``document-operations`` router
remains the separate, bounded executor for its explicitly documented local
tools.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import re
import uuid
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import document_workspace_enabled, ensure_copyfast_schema, read_transaction, transaction, utc_now


router = APIRouter(prefix="/api/v1/document-workspace", tags=["Web Document & PDF Workspace"])

WORKSPACE_STATES = frozenset({"draft", "review", "approved", "archived"})
WRITABLE_WORKSPACE_STATES = frozenset({"draft"})
PLAN_STATES = frozenset({"active", "archived"})
DOCUMENT_TYPES = frozenset({"mixed", "pdf", "office", "text", "image", "scan"})
PLAN_OPERATIONS = frozenset({
    "organize", "split", "merge", "optimize", "image_to_pdf", "pdf_to_images",
    "pdf_to_word", "ocr", "translate", "convert", "other",
})
# A document plan is deliberately not an executable request.  This closed
# catalogue only tells the signed UI which *independent* Web-native tool may
# be opened next for a compatible planning intent.  It contains no workspace
# or Asset Vault identifier, no prefilled page/profile choice and no execution
# token, so following a link can never replay a Bot `docflow` state machine.
DOCUMENT_HANDOFF_CATALOG = (
    {
        "operation": "split",
        "availability": "available",
        "route": "/documents/split",
        "title": "Tách PDF riêng tư",
        "summary": "Mở biểu mẫu tách PDF riêng; chọn lại PDF Asset Vault và khoảng trang trong công cụ đó.",
    },
    {
        "operation": "merge",
        "availability": "available",
        "route": "/documents/merge",
        "title": "Gộp PDF riêng tư",
        "summary": "Mở biểu mẫu gộp PDF riêng; chọn lại từng PDF Asset Vault theo thứ tự trong công cụ đó.",
    },
    {
        "operation": "optimize",
        "availability": "available",
        "route": "/documents/compress",
        "title": "Tối ưu PDF có kiểm chứng",
        "summary": "Mở PDF Optimize riêng. Web chỉ dùng một profile structural đã kiểm chứng, không nhận mức nén Bot light/medium/strong.",
    },
    {
        "operation": "image_to_pdf",
        "availability": "available",
        "route": "/documents/image-to-pdf",
        "title": "Ảnh sang PDF riêng tư",
        "summary": "Mở biểu mẫu ảnh sang PDF riêng; chọn lại ảnh Asset Vault trong công cụ đó.",
    },
    {
        "operation": "pdf_to_images",
        "availability": "available",
        "route": "/documents/pdf-to-images",
        "title": "PDF sang ảnh riêng tư",
        "summary": "Mở biểu mẫu PDF sang ảnh riêng; chọn lại PDF Asset Vault trong công cụ đó.",
    },
    {
        "operation": "pdf_to_word",
        "availability": "available",
        "route": "/documents/pdf-to-word",
        "title": "PDF text sang Word riêng tư",
        "summary": "Mở biểu mẫu PDF text sang Word riêng; chọn lại PDF Asset Vault trong công cụ đó.",
    },
    {
        "operation": "ocr",
        "availability": "guarded",
        "route": None,
        "title": "OCR cần công cụ nguồn phù hợp",
        "summary": "Intent OCR chưa xác định loại nguồn hoặc runtime; Workspace không chuyển file hay tự chọn OCR thay bạn.",
    },
    {
        "operation": "translate",
        "availability": "guarded",
        "route": None,
        "title": "Dịch tài liệu đang được bảo vệ",
        "summary": "Không có handoff dịch tài liệu từ plan này; Web không gửi document đến provider hoặc Bot.",
    },
    {
        "operation": "convert",
        "availability": "guarded",
        "route": None,
        "title": "Convert cần contract riêng",
        "summary": "Chọn định dạng và nguồn trong một tool có contract riêng; plan này không tạo request convert.",
    },
    {
        "operation": "organize",
        "availability": "guidance",
        "route": None,
        "title": "Tiếp tục self-review",
        "summary": "Đây là intent tổ chức/QA. Tiếp tục cập nhật checklist và chọn một utility độc lập khi scope đã rõ.",
    },
    {
        "operation": "other",
        "availability": "guidance",
        "route": None,
        "title": "Cần xác định công cụ phù hợp",
        "summary": "Intent này không có route mặc định; không chuyển state, file hoặc yêu cầu thực thi sang browser.",
    },
)
ASSET_EXTENSIONS = frozenset({"pdf", "docx", "txt", "jpg", "jpeg", "png", "webp"})
ASSET_CONTENT_TYPES = frozenset({
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "image/jpeg", "image/png", "image/webp",
})
ASSET_PAIRS = frozenset({
    ("pdf", "application/pdf"),
    ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ("txt", "text/plain"),
    ("jpg", "image/jpeg"), ("jpeg", "image/jpeg"), ("png", "image/png"), ("webp", "image/webp"),
})
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
UNSAFE_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
URL_PATTERN = re.compile(r"(?:https?://|www\.|file:|data:|javascript:)", re.IGNORECASE)
SECRET_PATTERN = re.compile(
    r"\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|client[ _-]?secret|"
    r"password|passphrase|authorization|otp|cvv|cvc|private[ _-]?key)\b\s*(?:['\"]\s*)?(?:[:=]|\bis\b)\s*(?:['\"]\s*)?[A-Za-z0-9_./+=:-]{6,}",
    re.IGNORECASE,
)
KNOWN_SECRET_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(?:sk|pk|rk)_[A-Za-z0-9_-]{12,}|github_pat_[A-Za-z0-9_]{12}|"
    r"gh[pousr]_[A-Za-z0-9]{12,}|xox[bpars]-[A-Za-z0-9-]{12,}|AIza[0-9A-Za-z_-]{20}|"
    r"(?:AKIA|ASIA)[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}\.",
    re.IGNORECASE,
)
TELEGRAM_BOT_TOKEN_PATTERN = re.compile(r"(?<![0-9])\d{6,12}:[A-Za-z0-9_-]{20,}(?![A-Za-z0-9_-])")
PAYMENT_PATTERN = re.compile(
    r"\b(?:txid|transaction\s+(?:hash|id|reference)|mã\s*(?:giao\s*)?(?:dịch|thanh\s*toán)|"
    r"bill|biên\s*lai|chứng\s*từ|số\s*tài\s*khoản|stk|qr\s*(?:code|thanh\s*toán))\b",
    re.IGNORECASE,
)
EXTERNAL_HANDLE_PATTERN = re.compile(
    r"\b(?:(?:provider|render|job|media|asset|file|worker|engine)[ _-]*(?:id|ref(?:erence)?|token|handle)|"
    r"(?:telegram[ _-]*)?bot[ _-]*(?:id|ref(?:erence)?|token|secret|handle)|"
    r"telegram[ _-]*file[ _-]*id)\b\s*(?::|=|\bis\b)\s*\S+",
    re.IGNORECASE,
)
MARKUP_EXECUTION_PATTERN = re.compile(
    r"<\s*/?\s*(?:script|svg|img|iframe|object|embed|style|link|meta|base|form|input|video|audio)\b|\bon[a-z]+\s*=",
    re.IGNORECASE,
)

MAX_WORKSPACES_PER_ACCOUNT = 300
MAX_PLANS_PER_WORKSPACE = 120
MAX_VERSIONS_PER_ENTITY = 100
MAX_LIST_LIMIT = 100
MAX_LIST_OFFSET = 10_000
MAX_EVENT_LIMIT = 50
MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT = 1024
IDEMPOTENCY_RETENTION = timedelta(hours=24)
ARCHIVED_ORDINAL_BASE = 1_000_000


def _require_enabled() -> None:
    if not document_workspace_enabled():
        raise HTTPException(
            status_code=503,
            detail="Document & PDF Workspace đang tạm dừng để bảo trì. WEBAPP_DOCUMENT_WORKSPACE_ENABLED chưa được bật.",
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
        raise ValueError("Idempotency key không hợp lệ")
    return key


def _sensitive_text(value: str) -> bool:
    return bool(
        URL_PATTERN.search(value)
        or SECRET_PATTERN.search(value)
        or KNOWN_SECRET_PATTERN.search(value)
        or TELEGRAM_BOT_TOKEN_PATTERN.search(value)
        or PAYMENT_PATTERN.search(value)
        or EXTERNAL_HANDLE_PATTERN.search(value)
        or MARKUP_EXECUTION_PATTERN.search(value)
        or "-----begin" in value.lower()
    )


def _line(value: Any, *, label: str, minimum: int, maximum: int, allow_empty: bool = False) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if UNSAFE_CONTROL_PATTERN.search(text) or len(text) > maximum or (not allow_empty and len(text) < minimum):
        raise ValueError(f"{label} cần từ {minimum} đến {maximum} ký tự hợp lệ")
    if text and _sensitive_text(text):
        raise ValueError(f"{label} không nhận URL, secret, mã xác thực, tham chiếu ngoài hoặc chứng từ thanh toán")
    return text


def _body(value: Any, *, label: str, maximum: int, allow_empty: bool = False) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if UNSAFE_CONTROL_PATTERN.search(text) or len(text) > maximum or (not allow_empty and not text):
        raise ValueError(f"{label} cần từ 1 đến {maximum:,} ký tự hợp lệ".replace(",", "."))
    if text and _sensitive_text(text):
        raise ValueError(f"{label} không nhận URL, secret, mã xác thực, tham chiếu ngoài hoặc chứng từ thanh toán")
    return text


def _tags(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("Tags phải là danh sách")
    result: list[str] = []
    seen: set[str] = set()
    for raw in value:
        tag = _line(raw, label="Tag", minimum=1, maximum=48)
        marker = tag.casefold()
        if marker not in seen:
            seen.add(marker)
            result.append(tag)
    if len(result) > 20:
        raise ValueError("Tối đa 20 tags")
    return result


def _decode_tags(value: Any) -> list[str]:
    try:
        parsed = json.loads(str(value or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    return [str(item) for item in parsed if isinstance(item, str)][:20] if isinstance(parsed, list) else []


def _fingerprint(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _idempotency_cutoff() -> str:
    return (datetime.now(timezone.utc) - IDEMPOTENCY_RETENTION).isoformat(timespec="seconds")


def _excerpt(value: Any, limit: int = 280) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= limit else f"{text[:max(1, limit - 1)].rstrip()}…"


class WorkspacePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    document_type: str = "mixed"
    # A professional document brief needs an explicit source context and
    # objective.  Keep these required server-side to match the native form;
    # otherwise an omitted field could bypass a client-only required marker.
    source_summary: str
    objective: str
    language: str = "vi"
    target_language: str = ""
    tags: list[str] = Field(default_factory=list)
    project_id: str | None = None

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return _line(value, label="Tên workspace", minimum=2, maximum=180)

    @field_validator("document_type")
    @classmethod
    def _document_type(cls, value: str) -> str:
        normalized = _line(value, label="Loại tài liệu", minimum=1, maximum=32).lower()
        if normalized not in DOCUMENT_TYPES:
            raise ValueError("Loại tài liệu không hợp lệ")
        return normalized

    @field_validator("source_summary")
    @classmethod
    def _source_summary(cls, value: str) -> str:
        return _body(value, label="Tóm tắt nguồn", maximum=8_000)

    @field_validator("objective")
    @classmethod
    def _objective(cls, value: str) -> str:
        return _body(value, label="Mục tiêu", maximum=8_000)

    @field_validator("language", "target_language")
    @classmethod
    def _language(cls, value: str, info) -> str:
        return _line(value, label="Ngôn ngữ" if info.field_name == "language" else "Ngôn ngữ đích", minimum=1, maximum=100, allow_empty=info.field_name == "target_language")

    @field_validator("tags")
    @classmethod
    def _tag_values(cls, value: list[str]) -> list[str]:
        return _tags(value)

    @field_validator("project_id")
    @classmethod
    def _project(cls, value: str | None) -> str | None:
        return _optional_uuid(value, label="Project ID")


class WorkspaceCreateRequest(WorkspacePayload):
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class WorkspaceUpdateRequest(WorkspacePayload):
    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class RevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class LifecycleRequest(RevisionRequest):
    state: str

    @field_validator("state")
    @classmethod
    def _state(cls, value: str) -> str:
        normalized = _line(value, label="Trạng thái", minimum=1, maximum=20).lower()
        if normalized not in WORKSPACE_STATES:
            raise ValueError("Trạng thái workspace không hợp lệ")
        return normalized


class RestoreVersionRequest(RevisionRequest):
    target_revision: int = Field(ge=1, le=MAX_VERSIONS_PER_ENTITY)


class PlanPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    operation: str = "organize"
    instructions: str = ""
    source_asset_id: str | None = None
    reference_asset_id: str | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return _line(value, label="Tên document plan", minimum=2, maximum=180)

    @field_validator("operation")
    @classmethod
    def _operation(cls, value: str) -> str:
        normalized = _line(value, label="Mục đích document", minimum=1, maximum=32).lower()
        if normalized not in PLAN_OPERATIONS:
            raise ValueError("Mục đích Document Workspace không hợp lệ")
        return normalized

    @field_validator("instructions")
    @classmethod
    def _instructions(cls, value: str) -> str:
        return _body(value, label="Hướng dẫn xử lý", maximum=12_000, allow_empty=True)

    @field_validator("source_asset_id")
    @classmethod
    def _source_asset(cls, value: str | None) -> str | None:
        return _optional_uuid(value, label="Source Asset ID")

    @field_validator("reference_asset_id")
    @classmethod
    def _reference_asset(cls, value: str | None) -> str | None:
        return _optional_uuid(value, label="Reference Asset ID")

    @field_validator("tags")
    @classmethod
    def _tag_values(cls, value: list[str]) -> list[str]:
        return _tags(value)

    def model_post_init(self, __context: Any) -> None:
        if self.source_asset_id and self.source_asset_id == self.reference_asset_id:
            raise ValueError("Source Asset ID và Reference Asset ID phải khác nhau")


class PlanCreateRequest(PlanPayload):
    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class PlanUpdateRequest(PlanPayload):
    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class ReorderRequest(RevisionRequest):
    plan_ids: list[str] = Field(min_length=0, max_length=MAX_PLANS_PER_WORKSPACE)

    @field_validator("plan_ids")
    @classmethod
    def _ids(cls, value: list[str]) -> list[str]:
        values = [_uuid(item, label="Plan ID") for item in value]
        if len(values) != len(set(values)):
            raise ValueError("Plan ID không được trùng")
        return values


def _boundary(**extra: Any) -> dict[str, Any]:
    """Make the execution boundary explicit in every public response."""
    return {
        "execution": "authoring_only",
        "provider_called": False,
        "ocr_called": False,
        "translation_called": False,
        "output_created": False,
        "job_created": False,
        "payment_started": False,
        "wallet_mutated": False,
        "payment_processed": False,
        "browser_file_upload": False,
        "browser_media_url": False,
        "preview_available": False,
        "output_delivery": "guarded",
        **extra,
    }


def _guarded(message: str, code: str) -> dict[str, Any]:
    return envelope(False, message, data=_boundary(), status_name="guarded", error_code=code)


def _safe_receipt(response: dict[str, Any]) -> dict[str, Any]:
    """Persist only opaque revision receipts, never authoring text or asset metadata."""
    if not isinstance(response, dict) or response.get("ok") is not True:
        return response
    source = response.get("data") if isinstance(response.get("data"), dict) else {}
    data = _boundary()
    workspace = source.get("workspace")
    if isinstance(workspace, dict) and isinstance(workspace.get("id"), str):
        data["workspace"] = {
            "id": str(workspace["id"]),
            "revision": int(workspace.get("revision") or 0),
            "state": str(workspace.get("state") or ""),
        }
    plan = source.get("plan")
    if isinstance(plan, dict) and isinstance(plan.get("id"), str):
        data["plan"] = {
            "id": str(plan["id"]),
            "workspace_id": str(plan.get("workspace_id") or ""),
            "revision": int(plan.get("revision") or 0),
            "state": str(plan.get("state") or ""),
        }
    for name in ("reordered", "history_snapshot_recorded", "plan_count"):
        if name in source:
            data[name] = source[name]
    return envelope(
        True,
        str(response.get("message") or "Đã lưu Document & PDF Workspace."),
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
    """Run a local mutation exactly once without retaining private brief text."""
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute(
            "DELETE FROM web_idempotency WHERE scope LIKE ? AND created_at < ?",
            ("web-document-workspace:%", _idempotency_cutoff()),
        )
        existing = conn.execute(
            "SELECT response_json, request_fingerprint FROM web_idempotency WHERE scope=? AND key=?",
            (scope, key),
        ).fetchone()
        if existing:
            fingerprint = str(existing[1] or "")
            if not fingerprint or not hmac.compare_digest(fingerprint, request_fingerprint):
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho yêu cầu khác")
            try:
                receipt = json.loads(str(existing[0]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Receipt Document Workspace không hợp lệ") from exc
            if not isinstance(receipt, dict):
                raise HTTPException(status_code=409, detail="Receipt Document Workspace không hợp lệ")
            return receipt
        count = conn.execute(
            "SELECT COUNT(*) FROM web_idempotency WHERE scope LIKE ?",
            (f"web-document-workspace:{account_id}:%",),
        ).fetchone()
        if int(count[0] or 0) >= MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT:
            return _guarded("Kho receipt thao tác tạm thời đang đầy. Vui lòng thử lại sau.", "WEB_DOCUMENT_WORKSPACE_IDEMPOTENCY_LIMIT")
        response = operation(conn)
        if response.get("ok") is True:
            receipt = _safe_receipt(response)
            conn.execute(
                "INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at) VALUES (?, ?, ?, ?, ?)",
                (scope, key, json.dumps(receipt, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
            )
            return receipt
        return response


def _summary_data(conn: Any, *, account_id: str) -> dict[str, Any]:
    counts = {
        str(row[0]): int(row[1])
        for row in conn.execute(
            "SELECT lifecycle, COUNT(*) FROM web_document_workspaces WHERE account_id=? GROUP BY lifecycle",
            (account_id,),
        ).fetchall()
    }
    active_plans = conn.execute(
        "SELECT COUNT(*) FROM web_document_plans WHERE account_id=? AND state='active'",
        (account_id,),
    ).fetchone()
    return {
        "workspaces": {
            "draft": counts.get("draft", 0),
            "review": counts.get("review", 0),
            "approved": counts.get("approved", 0),
            "archived": counts.get("archived", 0),
            "total": sum(counts.values()),
            "limit_per_account": MAX_WORKSPACES_PER_ACCOUNT,
        },
        "plans": {"active": int(active_plans[0] or 0), "limit_per_workspace": MAX_PLANS_PER_WORKSPACE},
        **_boundary(),
    }


def _document_handoff_catalog() -> list[dict[str, Any]]:
    """Return a content-free route catalogue for navigation-only handoffs.

    Every item is constant, closed and independent of a workspace/plan row.
    The receiving `/documents/*` tool has to repeat its signed account, Asset
    Vault ownership, feature flag, CSRF and idempotency checks itself.
    """

    return [
        {
            **item,
            "requires_new_tool_input": True,
            "workspace_data_transferred": False,
            "auto_execute": False,
            "workspace_output_shared": False,
        }
        for item in DOCUMENT_HANDOFF_CATALOG
    ]


@router.get("/summary")
async def document_workspace_summary(account: dict = Depends(require_account)):
    _require_enabled()
    ensure_copyfast_schema()
    with read_transaction() as conn:
        data = _summary_data(conn, account_id=str(account["id"]))
    return envelope(True, "Đã tải tổng quan Document & PDF Workspace.", data=data, status_name="read_only")


@router.get("/policy")
async def document_workspace_policy(account: dict = Depends(require_account)):
    _require_enabled()
    return envelope(
        True,
        "Document & PDF Workspace chỉ lưu brief, document plan, revision và Asset Vault UUID reference thuộc Web account.",
        data={
            "allowed": ["document_brief", "document_plan", "asset_reference_metadata", "revision_history", "self_review", "local_checklist"],
            "guarded": ["browser_file_upload", "remote_media_url", "provider_execution", "ocr_execution", "translation_execution", "preview", "output_delivery"],
            "deterministic_routes": {
                "pdf_split": "/documents/split",
                "pdf_merge": "/documents/merge",
                "pdf_optimize": "/documents/compress",
                "image_to_pdf": "/documents/image-to-pdf",
                "pdf_to_images": "/documents/pdf-to-images",
                "pdf_to_word": "/documents/pdf-to-word",
            },
            "handoff_catalog": _document_handoff_catalog(),
            "notice": "Các route deterministic là capability riêng, không được gọi, chia sẻ lifecycle hoặc nhận output từ workspace này. Handoff chỉ điều hướng sang tool mới; không chuyển brief, plan, Asset Vault ID, file, page range, profile hay token.",
            **_boundary(),
        },
        status_name="read_only",
    )


def _workspace_row(conn: Any, *, workspace_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, project_id, title, document_type, source_summary, objective,
                  language, target_language, tags_json, lifecycle, revision,
                  created_at, updated_at, archived_at
           FROM web_document_workspaces WHERE id=? AND account_id=?""",
        (workspace_id, account_id),
    ).fetchone()


def _plan_row(conn: Any, *, workspace_id: str, plan_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, workspace_id, ordinal, title, operation, instructions,
                  source_asset_id, reference_asset_id, tags_json, state, revision,
                  created_at, updated_at, archived_at
           FROM web_document_plans WHERE id=? AND workspace_id=? AND account_id=?""",
        (plan_id, workspace_id, account_id),
    ).fetchone()


def _workspace_not_found() -> dict[str, Any]:
    return _guarded("Không tìm thấy workspace thuộc Web account hiện tại.", "WEB_DOCUMENT_WORKSPACE_NOT_FOUND")


def _plan_not_found() -> dict[str, Any]:
    return _guarded("Không tìm thấy document plan thuộc workspace hiện tại.", "WEB_DOCUMENT_PLAN_NOT_FOUND")


def _revision_conflict() -> dict[str, Any]:
    return _guarded("Dữ liệu đã thay đổi ở nơi khác. Hãy tải lại trước khi lưu tiếp.", "WEB_DOCUMENT_WORKSPACE_REVISION_CONFLICT")


def _workspace_writable(workspace: tuple[Any, ...]) -> dict[str, Any] | None:
    lifecycle = str(workspace[9])
    if lifecycle == "draft":
        return None
    if lifecycle == "review":
        return _guarded("Workspace đang ở Review; hãy đưa về Draft trước khi chỉnh sửa document plan.", "WEB_DOCUMENT_WORKSPACE_REVIEW_LOCKED")
    if lifecycle == "approved":
        return _guarded("Workspace đã self-review Approved; hãy đưa về Draft trước khi chỉnh sửa document plan.", "WEB_DOCUMENT_WORKSPACE_APPROVED_LOCKED")
    return _guarded("Workspace đã archive; hãy khôi phục về Draft trước khi chỉnh sửa.", "WEB_DOCUMENT_WORKSPACE_ARCHIVED")


def _project_reference(conn: Any, *, account_id: str, project_id: str | None, active: bool = True) -> dict[str, Any]:
    if not project_id:
        return {}
    state_clause = "AND state='active'" if active else ""
    row = conn.execute(
        f"SELECT id, title, state FROM web_projects WHERE id=? AND account_id=? {state_clause}",
        (project_id, account_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=422, detail="Project liên kết không hợp lệ hoặc không còn hoạt động")
    return {"project": {"id": str(row[0]), "title": str(row[1]), "state": str(row[2])}}


def _asset_row(conn: Any, *, asset_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, display_name, extension, content_type, state, updated_at
           FROM web_asset_files WHERE id=? AND account_id=?""",
        (asset_id, account_id),
    ).fetchone()


def _document_asset_public(row: tuple[Any, ...]) -> dict[str, Any]:
    """Return selection metadata, never an original filename/blob/path/key."""
    return {
        "id": str(row[0]),
        "display_name": str(row[1]),
        # Asset Vault persists canonical extensions with a leading dot.  Keep
        # that UI-friendly representation public while normalizing it below
        # for the strict allowlist comparison.
        "extension": f".{str(row[2]).lower().lstrip('.')}",
        "content_type": str(row[3]).lower(),
        "state": str(row[4]),
        "updated_at": str(row[5]),
    }


def _is_document_asset(row: tuple[Any, ...]) -> bool:
    extension = str(row[2]).lower().lstrip(".")
    content_type = str(row[3]).lower()
    return extension in ASSET_EXTENSIONS and content_type in ASSET_CONTENT_TYPES and (extension, content_type) in ASSET_PAIRS


def _active_document_asset(conn: Any, *, asset_id: str | None, account_id: str, label: str) -> dict[str, Any] | None:
    if not asset_id:
        return None
    row = _asset_row(conn, asset_id=asset_id, account_id=account_id)
    if not row or str(row[4]) != "active" or not _is_document_asset(row):
        raise HTTPException(
            status_code=422,
            detail=f"{label} phải là PDF, DOCX, TXT hoặc ảnh JPEG/PNG/WebP đang hoạt động thuộc Web account",
        )
    return _document_asset_public(row)


def _validate_asset_refs(conn: Any, *, account_id: str, snapshot: dict[str, Any]) -> None:
    """Validate opaque UUID references server-side without exposing storage data."""
    source = snapshot.get("source_asset_id")
    reference = snapshot.get("reference_asset_id")
    if source and source == reference:
        raise HTTPException(status_code=422, detail="Source Asset ID và Reference Asset ID phải khác nhau")
    _active_document_asset(conn, asset_id=source, account_id=account_id, label="Source Asset reference")
    _active_document_asset(conn, asset_id=reference, account_id=account_id, label="Reference Asset reference")


def _workspace_snapshot(payload: WorkspacePayload, *, lifecycle: str = "draft") -> dict[str, Any]:
    return {
        "title": payload.title,
        "document_type": payload.document_type,
        "source_summary": payload.source_summary,
        "objective": payload.objective,
        "language": payload.language,
        "target_language": payload.target_language,
        "tags": list(payload.tags),
        "project_id": payload.project_id,
        "lifecycle": lifecycle,
    }


def _workspace_snapshot_from_row(row: tuple[Any, ...], *, lifecycle: str | None = None) -> dict[str, Any]:
    return {
        "title": str(row[2]),
        "document_type": str(row[3]),
        "source_summary": str(row[4]),
        "objective": str(row[5]),
        "language": str(row[6]),
        "target_language": str(row[7]),
        "tags": _decode_tags(row[8]),
        "project_id": str(row[1]) if row[1] else None,
        "lifecycle": lifecycle or str(row[9]),
    }


def _workspace_payload_from_snapshot(snapshot: dict[str, Any]) -> WorkspacePayload:
    return WorkspacePayload.model_validate({
        "title": snapshot.get("title", ""),
        "document_type": snapshot.get("document_type", "mixed"),
        "source_summary": snapshot.get("source_summary", ""),
        "objective": snapshot.get("objective", ""),
        "language": snapshot.get("language", "vi"),
        "target_language": snapshot.get("target_language", ""),
        "tags": snapshot.get("tags", []),
        "project_id": snapshot.get("project_id"),
    })


def _plan_snapshot(payload: PlanPayload, *, state: str = "active") -> dict[str, Any]:
    return {
        "title": payload.title,
        "operation": payload.operation,
        "instructions": payload.instructions,
        "source_asset_id": payload.source_asset_id,
        "reference_asset_id": payload.reference_asset_id,
        "tags": list(payload.tags),
        "state": state,
    }


def _plan_snapshot_from_row(row: tuple[Any, ...], *, state: str | None = None) -> dict[str, Any]:
    return {
        "title": str(row[3]),
        "operation": str(row[4]),
        "instructions": str(row[5]),
        "source_asset_id": str(row[6]) if row[6] else None,
        "reference_asset_id": str(row[7]) if row[7] else None,
        "tags": _decode_tags(row[8]),
        "state": state or str(row[9]),
    }


def _plan_payload_from_snapshot(snapshot: dict[str, Any]) -> PlanPayload:
    return PlanPayload.model_validate({
        "title": snapshot.get("title", ""),
        "operation": snapshot.get("operation", "organize"),
        "instructions": snapshot.get("instructions", ""),
        "source_asset_id": snapshot.get("source_asset_id"),
        "reference_asset_id": snapshot.get("reference_asset_id"),
        "tags": snapshot.get("tags", []),
    })


def _workspace_public(row: tuple[Any, ...], *, plan_count: int = 0, include_content: bool = False) -> dict[str, Any]:
    value = {
        "id": str(row[0]),
        "project_id": str(row[1]) if row[1] else None,
        "title": str(row[2]),
        "document_type": str(row[3]),
        "source_summary_excerpt": _excerpt(row[4], 360),
        "objective_excerpt": _excerpt(row[5], 360),
        "language": str(row[6]),
        "target_language": str(row[7]),
        "tags": _decode_tags(row[8]),
        "state": str(row[9]),
        "revision": int(row[10]),
        "created_at": str(row[11]),
        "updated_at": str(row[12]),
        "archived_at": str(row[13]) if row[13] else None,
        "plan_count": int(plan_count),
        **_boundary(),
    }
    if include_content:
        value.update({"source_summary": str(row[4]), "objective": str(row[5])})
    return value


def _asset_available(conn: Any, *, asset_id: str | None, account_id: str) -> bool:
    if not asset_id:
        return False
    row = _asset_row(conn, asset_id=asset_id, account_id=account_id)
    return bool(row and str(row[4]) == "active" and _is_document_asset(row))


def _plan_public(
    conn: Any,
    row: tuple[Any, ...],
    *,
    account_id: str,
    include_content: bool = False,
    versions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Expose IDs/availability only for saved reference fields, never file metadata."""
    value = {
        "id": str(row[0]),
        "workspace_id": str(row[1]),
        "ordinal": int(row[2]),
        "title": str(row[3]),
        "operation": str(row[4]),
        "instructions_excerpt": _excerpt(row[5], 420),
        "source_asset_id": str(row[6]) if row[6] else None,
        "reference_asset_id": str(row[7]) if row[7] else None,
        "source_asset_available": _asset_available(conn, asset_id=str(row[6]) if row[6] else None, account_id=account_id),
        "reference_asset_available": _asset_available(conn, asset_id=str(row[7]) if row[7] else None, account_id=account_id),
        "tags": _decode_tags(row[8]),
        "state": str(row[9]),
        "revision": int(row[10]),
        "created_at": str(row[11]),
        "updated_at": str(row[12]),
        "archived_at": str(row[13]) if row[13] else None,
        **_boundary(),
    }
    if include_content:
        value["instructions"] = str(row[5])
    if versions is not None:
        value["versions"] = versions
    return value


def _workspace_version_public(row: tuple[Any, ...]) -> dict[str, Any]:
    try:
        snapshot = json.loads(str(row[1] or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        snapshot = {}
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    return {
        "revision": int(row[0]),
        "title": str(snapshot.get("title") or "Document workspace"),
        "document_type": str(snapshot.get("document_type") or "mixed"),
        "state": str(snapshot.get("lifecycle") or "draft"),
        "source_summary_excerpt": _excerpt(snapshot.get("source_summary"), 280),
        "created_at": str(row[2]),
    }


def _plan_version_public(row: tuple[Any, ...]) -> dict[str, Any]:
    try:
        snapshot = json.loads(str(row[1] or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        snapshot = {}
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    return {
        "revision": int(row[0]),
        "title": str(snapshot.get("title") or "Document plan"),
        "operation": str(snapshot.get("operation") or "organize"),
        "state": str(snapshot.get("state") or "active"),
        "instructions_excerpt": _excerpt(snapshot.get("instructions"), 260),
        "created_at": str(row[2]),
    }


def _insert_workspace(conn: Any, *, workspace_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str) -> None:
    conn.execute(
        """INSERT INTO web_document_workspaces
           (id, account_id, project_id, title, document_type, source_summary, objective,
            language, target_language, tags_json, lifecycle, revision, created_at, updated_at, archived_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            workspace_id, account_id, snapshot.get("project_id"), snapshot["title"], snapshot["document_type"],
            snapshot["source_summary"], snapshot["objective"], snapshot["language"], snapshot["target_language"],
            json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")), snapshot["lifecycle"], revision,
            now, now, now if snapshot["lifecycle"] == "archived" else None,
        ),
    )


def _write_workspace(
    conn: Any, *, workspace_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str, archived_at: str | None
) -> None:
    conn.execute(
        """UPDATE web_document_workspaces
           SET project_id=?, title=?, document_type=?, source_summary=?, objective=?, language=?, target_language=?,
               tags_json=?, lifecycle=?, revision=?, updated_at=?, archived_at=? WHERE id=? AND account_id=?""",
        (
            snapshot.get("project_id"), snapshot["title"], snapshot["document_type"], snapshot["source_summary"],
            snapshot["objective"], snapshot["language"], snapshot["target_language"],
            json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")), snapshot["lifecycle"],
            revision, now, archived_at, workspace_id, account_id,
        ),
    )


def _insert_workspace_version(
    conn: Any, *, workspace_id: str, account_id: str, revision: int, snapshot: dict[str, Any], now: str
) -> None:
    conn.execute(
        """INSERT INTO web_document_workspace_versions
           (id, workspace_id, account_id, revision, snapshot_json, created_at) VALUES (?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), workspace_id, account_id, revision, json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), now),
    )


def _insert_plan(
    conn: Any, *, plan_id: str, workspace_id: str, account_id: str, ordinal: int, snapshot: dict[str, Any], revision: int, now: str
) -> None:
    conn.execute(
        """INSERT INTO web_document_plans
           (id, workspace_id, account_id, ordinal, title, operation, instructions, source_asset_id,
            reference_asset_id, tags_json, state, revision, created_at, updated_at, archived_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            plan_id, workspace_id, account_id, ordinal, snapshot["title"], snapshot["operation"],
            snapshot["instructions"], snapshot.get("source_asset_id"), snapshot.get("reference_asset_id"),
            json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")), snapshot["state"], revision,
            now, now, now if snapshot["state"] == "archived" else None,
        ),
    )


def _write_plan(
    conn: Any, *, plan_id: str, workspace_id: str, account_id: str, snapshot: dict[str, Any], revision: int,
    now: str, archived_at: str | None, ordinal: int | None = None,
) -> None:
    updates = "title=?, operation=?, instructions=?, source_asset_id=?, reference_asset_id=?, tags_json=?, state=?, revision=?, updated_at=?, archived_at=?"
    values: list[Any] = [
        snapshot["title"], snapshot["operation"], snapshot["instructions"], snapshot.get("source_asset_id"),
        snapshot.get("reference_asset_id"), json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")),
        snapshot["state"], revision, now, archived_at,
    ]
    if ordinal is not None:
        updates = "ordinal=?, " + updates
        values.insert(0, ordinal)
    values.extend([plan_id, workspace_id, account_id])
    conn.execute(f"UPDATE web_document_plans SET {updates} WHERE id=? AND workspace_id=? AND account_id=?", values)


def _insert_plan_version(conn: Any, *, plan_id: str, account_id: str, revision: int, snapshot: dict[str, Any], now: str) -> None:
    conn.execute(
        """INSERT INTO web_document_plan_versions
           (id, plan_id, account_id, revision, snapshot_json, created_at) VALUES (?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), plan_id, account_id, revision, json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), now),
    )


def _can_add_version(conn: Any, *, table: str, entity_column: str, entity_id: str, account_id: str) -> bool:
    row = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {entity_column}=? AND account_id=?", (entity_id, account_id)).fetchone()
    return int(row[0] or 0) < MAX_VERSIONS_PER_ENTITY


def _next_active_ordinal(conn: Any, *, workspace_id: str, account_id: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(ordinal), 0) FROM web_document_plans WHERE workspace_id=? AND account_id=? AND state='active'",
        (workspace_id, account_id),
    ).fetchone()
    return int(row[0] or 0) + 1


def _normalise_archived_ordinals(conn: Any, *, workspace_id: str, account_id: str) -> None:
    """Use a negative staging range so the unique workspace ordinal never collides."""
    rows = conn.execute(
        """SELECT id FROM web_document_plans WHERE workspace_id=? AND account_id=? AND state='archived'
           ORDER BY archived_at ASC, id ASC""",
        (workspace_id, account_id),
    ).fetchall()
    for index, row in enumerate(rows, start=1):
        conn.execute(
            "UPDATE web_document_plans SET ordinal=? WHERE id=? AND workspace_id=? AND account_id=?",
            (-index, str(row[0]), workspace_id, account_id),
        )
    for index, row in enumerate(rows, start=1):
        conn.execute(
            "UPDATE web_document_plans SET ordinal=? WHERE id=? AND workspace_id=? AND account_id=?",
            (ARCHIVED_ORDINAL_BASE + index - 1, str(row[0]), workspace_id, account_id),
        )


def _next_archived_ordinal(conn: Any, *, workspace_id: str, account_id: str) -> int:
    _normalise_archived_ordinals(conn, workspace_id=workspace_id, account_id=account_id)
    row = conn.execute(
        "SELECT COALESCE(MAX(ordinal), 0) FROM web_document_plans WHERE workspace_id=? AND account_id=? AND state='archived'",
        (workspace_id, account_id),
    ).fetchone()
    return max(ARCHIVED_ORDINAL_BASE, int(row[0] or 0) + 1)


def _event(conn: Any, *, account_id: str, workspace_id: str, action: str, revision: int, plan_id: str | None = None) -> None:
    conn.execute(
        """INSERT INTO web_document_workspace_events
           (id, account_id, workspace_id, plan_id, entity_type, action, revision, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), account_id, workspace_id, plan_id, "plan" if plan_id else "workspace", action, revision, utc_now()),
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


def _advance_workspace_for_plan(
    conn: Any, *, workspace: tuple[Any, ...], account_id: str, now: str, action: str, plan_id: str | None = None
) -> tuple[Any, ...]:
    workspace_id = str(workspace[0])
    if not _can_add_version(
        conn, table="web_document_workspace_versions", entity_column="workspace_id", entity_id=workspace_id, account_id=account_id
    ):
        raise HTTPException(status_code=409, detail="Workspace đã đạt giới hạn lịch sử phiên bản")
    snapshot = _workspace_snapshot_from_row(workspace, lifecycle="draft")
    revision = int(workspace[10]) + 1
    _write_workspace(conn, workspace_id=workspace_id, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
    _insert_workspace_version(conn, workspace_id=workspace_id, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
    _event(conn, account_id=account_id, workspace_id=workspace_id, plan_id=plan_id, action=action, revision=revision)
    changed = _workspace_row(conn, workspace_id=workspace_id, account_id=account_id)
    if not changed:
        raise HTTPException(status_code=500, detail="Không thể đọc lại document workspace")
    return changed


def _references_listing(conn: Any, *, account_id: str) -> dict[str, Any]:
    projects = conn.execute(
        "SELECT id, title, updated_at FROM web_projects WHERE account_id=? AND state='active' ORDER BY updated_at DESC, id DESC LIMIT 100",
        (account_id,),
    ).fetchall()
    assets = conn.execute(
        """SELECT id, display_name, extension, content_type, state, updated_at
           FROM web_asset_files WHERE account_id=? AND state='active'
           ORDER BY updated_at DESC, id DESC LIMIT 100""",
        (account_id,),
    ).fetchall()
    return {
        "projects": [{"id": str(row[0]), "title": str(row[1]), "updated_at": str(row[2])} for row in projects],
        "document_assets": [_document_asset_public(row) for row in assets if _is_document_asset(row)],
        **_boundary(),
    }


def _plan_versions(conn: Any, *, plan_id: str, account_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """SELECT revision, snapshot_json, created_at FROM web_document_plan_versions
           WHERE plan_id=? AND account_id=? ORDER BY revision DESC LIMIT 20""",
        (plan_id, account_id),
    ).fetchall()
    return [_plan_version_public(row) for row in rows]


def _workspace_detail(conn: Any, *, workspace_id: str, account_id: str) -> dict[str, Any] | None:
    workspace = _workspace_row(conn, workspace_id=workspace_id, account_id=account_id)
    if not workspace:
        return None
    plan_count = conn.execute(
        "SELECT COUNT(*) FROM web_document_plans WHERE workspace_id=? AND account_id=? AND state='active'",
        (workspace_id, account_id),
    ).fetchone()
    versions = conn.execute(
        """SELECT revision, snapshot_json, created_at FROM web_document_workspace_versions
           WHERE workspace_id=? AND account_id=? ORDER BY revision DESC LIMIT ?""",
        (workspace_id, account_id, MAX_VERSIONS_PER_ENTITY),
    ).fetchall()
    plans = conn.execute(
        """SELECT id, workspace_id, ordinal, title, operation, instructions, source_asset_id,
                  reference_asset_id, tags_json, state, revision, created_at, updated_at, archived_at
           FROM web_document_plans WHERE workspace_id=? AND account_id=?
           ORDER BY CASE state WHEN 'active' THEN 0 ELSE 1 END, ordinal ASC, updated_at DESC, id DESC LIMIT ?""",
        (workspace_id, account_id, MAX_PLANS_PER_WORKSPACE),
    ).fetchall()
    events = conn.execute(
        """SELECT action, entity_type, plan_id, revision, created_at FROM web_document_workspace_events
           WHERE workspace_id=? AND account_id=? ORDER BY created_at DESC, id DESC LIMIT ?""",
        (workspace_id, account_id, MAX_EVENT_LIMIT),
    ).fetchall()
    refs = _project_reference(conn, account_id=account_id, project_id=str(workspace[1]) if workspace[1] else None, active=False)
    return {
        "workspace": _workspace_public(workspace, plan_count=int(plan_count[0] or 0), include_content=True),
        "versions": [_workspace_version_public(row) for row in versions],
        "plans": [
            _plan_public(
                conn, row, account_id=account_id, include_content=True,
                versions=_plan_versions(conn, plan_id=str(row[0]), account_id=account_id),
            )
            for row in plans
        ],
        "events": [
            {
                "action": str(row[0]),
                "entity_type": str(row[1]),
                "plan_id": str(row[2]) if row[2] else None,
                "revision": int(row[3]),
                "created_at": str(row[4]),
            }
            for row in events
        ],
        "references": refs,
        **_boundary(),
    }


def _plan_count(conn: Any, *, workspace_id: str, account_id: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM web_document_plans WHERE workspace_id=? AND account_id=? AND state='active'",
        (workspace_id, account_id),
    ).fetchone()
    return int(row[0] or 0)


def _estimate(conn: Any, *, workspace: tuple[Any, ...], account_id: str) -> dict[str, Any]:
    blocked = _workspace_writable(workspace)
    if blocked:
        return blocked
    rows = conn.execute(
        """SELECT id, ordinal, title, operation, source_asset_id, reference_asset_id
           FROM web_document_plans WHERE workspace_id=? AND account_id=? AND state='active'
           ORDER BY ordinal ASC, id ASC""",
        (str(workspace[0]), account_id),
    ).fetchall()
    operations = {operation: sum(1 for row in rows if str(row[3]) == operation) for operation in sorted(PLAN_OPERATIONS)}
    source_refs = sum(1 for row in rows if row[4])
    reference_refs = sum(1 for row in rows if row[5])
    return envelope(
        True,
        "Đã tính checklist document plan cục bộ.",
        data={
            "workspace_id": str(workspace[0]),
            "plan_count": len(rows),
            "operations": operations,
            "source_reference_count": source_refs,
            "reference_asset_count": reference_refs,
            "items": [
                {
                    "plan_id": str(row[0]),
                    "ordinal": int(row[1]),
                    "title": str(row[2]),
                    "operation": str(row[3]),
                    "has_source_asset_reference": bool(row[4]),
                    "has_reference_asset_reference": bool(row[5]),
                }
                for row in rows
            ],
            "notice": "Đây là checklist authoring; không OCR/dịch/chuyển đổi, không tạo output, job, charge hoặc trạng thái thực thi.",
            **_boundary(),
        },
        status_name="read_only",
    )


def _allowed_transition(current: str, target: str) -> bool:
    return target in {
        "draft": {"review", "archived"},
        "review": {"draft", "approved", "archived"},
        "approved": {"draft", "archived"},
        "archived": {"draft"},
    }.get(current, set())


@router.get("/references")
async def document_workspace_references(account: dict = Depends(require_account)):
    _require_enabled()
    ensure_copyfast_schema()
    with read_transaction() as conn:
        data = _references_listing(conn, account_id=str(account["id"]))
    return envelope(True, "Đã tải Project và Asset Vault references thuộc Web account hiện tại.", data=data, status_name="read_only")


@router.get("/workspaces")
async def document_workspaces(
    state: str = Query(default="active", max_length=20),
    q: str = Query(default="", max_length=180),
    limit: int = Query(default=30, ge=1, le=MAX_LIST_LIMIT),
    offset: int = Query(default=0, ge=0, le=MAX_LIST_OFFSET),
    account: dict = Depends(require_account),
):
    _require_enabled()
    normalized_state = str(state or "active").strip().lower()
    if normalized_state not in {"active", *WORKSPACE_STATES}:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái workspace không hợp lệ")
    needle = re.sub(r"\s+", " ", str(q or "")).strip()
    if UNSAFE_CONTROL_PATTERN.search(needle) or _sensitive_text(needle):
        raise HTTPException(status_code=422, detail="Từ khóa tìm kiếm không hợp lệ")
    where = ["w.account_id=?"]
    values: list[Any] = [str(account["id"])]
    if normalized_state == "active":
        where.append("w.lifecycle<>'archived'")
    else:
        where.append("w.lifecycle=?")
        values.append(normalized_state)
    if needle:
        where.append("(w.title LIKE ? ESCAPE '\\' OR w.source_summary LIKE ? ESCAPE '\\' OR w.objective LIKE ? ESCAPE '\\')")
        wildcard = "%" + needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        values.extend([wildcard, wildcard, wildcard])
    # Fetch one bounded sentinel row so the owner-scoped library can page
    # without a separate count query or a disclosure of records outside this
    # account/filter.  The public projection below deliberately remains an
    # excerpt-only workspace card.
    values.extend([limit + 1, offset])
    ensure_copyfast_schema()
    with read_transaction() as conn:
        rows = conn.execute(
            f"""SELECT w.id, w.project_id, w.title, w.document_type, w.source_summary, w.objective,
                       w.language, w.target_language, w.tags_json, w.lifecycle, w.revision,
                       w.created_at, w.updated_at, w.archived_at,
                       (SELECT COUNT(*) FROM web_document_plans p WHERE p.workspace_id=w.id AND p.account_id=w.account_id AND p.state='active')
                FROM web_document_workspaces w WHERE {' AND '.join(where)} ORDER BY w.updated_at DESC, w.id DESC LIMIT ? OFFSET ?""",
            values,
        ).fetchall()
        has_more = len(rows) > limit
        items = [_workspace_public(row[:14], plan_count=int(row[14] or 0)) for row in rows[:limit]]
    return envelope(
        True,
        "Đã tải document workspaces.",
        data={
            "items": items,
            "has_more": has_more,
            "next_offset": offset + limit if has_more else None,
            # Search phrases can be sensitive authoring metadata.  The client
            # already owns the current in-memory query, so echo only the
            # non-sensitive lifecycle filter instead of reflecting `q`.
            "filters": {"state": normalized_state},
            "pagination": {"limit": limit, "offset": offset, "returned": len(items)},
            **_boundary(),
        },
        status_name="read_only",
    )


@router.get("/workspaces/{workspace_id}")
async def document_workspace_detail(workspace_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    resolved = _uuid(workspace_id, label="Workspace ID")
    ensure_copyfast_schema()
    with read_transaction() as conn:
        data = _workspace_detail(conn, workspace_id=resolved, account_id=str(account["id"]))
    if not data:
        return _workspace_not_found()
    return envelope(True, "Đã tải document workspace.", data=data, status_name=str(data["workspace"]["state"]))


@router.post("/workspaces")
async def document_workspace_create(
    payload: WorkspaceCreateRequest,
    request: Request,
    account: dict = Depends(require_account),
    _csrf: None = Depends(require_csrf),
):
    _require_enabled()
    account_id = str(account["id"])
    snapshot = _workspace_snapshot(payload)
    fingerprint = _fingerprint({"action": "create_workspace", "payload": snapshot})

    def operation(conn: Any) -> dict[str, Any]:
        count = conn.execute(
            "SELECT COUNT(*) FROM web_document_workspaces WHERE account_id=? AND lifecycle<>'archived'", (account_id,)
        ).fetchone()
        if int(count[0] or 0) >= MAX_WORKSPACES_PER_ACCOUNT:
            return _guarded("Đã đạt giới hạn document workspaces đang hoạt động.", "WEB_DOCUMENT_WORKSPACE_LIMIT")
        _project_reference(conn, account_id=account_id, project_id=snapshot.get("project_id"))
        now = utc_now()
        workspace_id = str(uuid.uuid4())
        _insert_workspace(conn, workspace_id=workspace_id, account_id=account_id, snapshot=snapshot, revision=1, now=now)
        _insert_workspace_version(conn, workspace_id=workspace_id, account_id=account_id, revision=1, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, workspace_id=workspace_id, action="workspace_created", revision=1)
        row = _workspace_row(conn, workspace_id=workspace_id, account_id=account_id)
        if not row:
            raise HTTPException(status_code=500, detail="Không thể đọc lại document workspace")
        _audit(conn, request=request, account=account, action="document_workspace_created", target=workspace_id, detail="Created document workspace")
        return envelope(
            True, "Đã tạo document workspace ở trạng thái Draft.",
            data={"workspace": _workspace_public(row), **_boundary()}, status_name="draft",
        )

    return _idempotent(f"web-document-workspace:{account_id}:create_workspace", account_id, payload.idempotency_key, fingerprint, operation)


@router.patch("/workspaces/{workspace_id}")
async def document_workspace_update(
    workspace_id: str,
    payload: WorkspaceUpdateRequest,
    request: Request,
    account: dict = Depends(require_account),
    _csrf: None = Depends(require_csrf),
):
    _require_enabled()
    resolved = _uuid(workspace_id, label="Workspace ID")
    account_id = str(account["id"])
    snapshot = _workspace_snapshot(payload)
    fingerprint = _fingerprint({"action": "update_workspace", "workspace_id": resolved, "expected_revision": payload.expected_revision, "payload": snapshot})

    def operation(conn: Any) -> dict[str, Any]:
        row = _workspace_row(conn, workspace_id=resolved, account_id=account_id)
        if not row:
            return _workspace_not_found()
        blocked = _workspace_writable(row)
        if blocked:
            return blocked
        if int(row[10]) != payload.expected_revision:
            return _revision_conflict()
        if not _can_add_version(conn, table="web_document_workspace_versions", entity_column="workspace_id", entity_id=resolved, account_id=account_id):
            return _guarded("Workspace đã đạt giới hạn lịch sử phiên bản.", "WEB_DOCUMENT_WORKSPACE_VERSION_LIMIT")
        _project_reference(conn, account_id=account_id, project_id=snapshot.get("project_id"))
        now = utc_now()
        revision = int(row[10]) + 1
        _write_workspace(conn, workspace_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_workspace_version(conn, workspace_id=resolved, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, workspace_id=resolved, action="workspace_updated", revision=revision)
        changed = _workspace_row(conn, workspace_id=resolved, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể đọc lại document workspace")
        _audit(conn, request=request, account=account, action="document_workspace_updated", target=resolved, detail="Updated document workspace")
        return envelope(
            True, "Đã lưu revision document workspace mới.",
            data={"workspace": _workspace_public(changed, plan_count=_plan_count(conn, workspace_id=resolved, account_id=account_id)), **_boundary()},
            status_name="draft",
        )

    return _idempotent(f"web-document-workspace:{account_id}:workspace:{resolved}:update", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/workspaces/{workspace_id}/lifecycle")
async def document_workspace_lifecycle(
    workspace_id: str,
    payload: LifecycleRequest,
    request: Request,
    account: dict = Depends(require_account),
    _csrf: None = Depends(require_csrf),
):
    _require_enabled()
    resolved = _uuid(workspace_id, label="Workspace ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({
        "action": "workspace_lifecycle", "workspace_id": resolved,
        "expected_revision": payload.expected_revision, "state": payload.state,
    })

    def operation(conn: Any) -> dict[str, Any]:
        row = _workspace_row(conn, workspace_id=resolved, account_id=account_id)
        if not row:
            return _workspace_not_found()
        if int(row[10]) != payload.expected_revision:
            return _revision_conflict()
        current = str(row[9])
        if current == payload.state:
            return _guarded("Workspace đã ở trạng thái yêu cầu.", "WEB_DOCUMENT_WORKSPACE_STATE_UNCHANGED")
        if not _allowed_transition(current, payload.state):
            return _guarded("Chuyển trạng thái workspace không hợp lệ.", "WEB_DOCUMENT_WORKSPACE_TRANSITION_INVALID")
        if not _can_add_version(conn, table="web_document_workspace_versions", entity_column="workspace_id", entity_id=resolved, account_id=account_id):
            return _guarded("Workspace đã đạt giới hạn lịch sử phiên bản.", "WEB_DOCUMENT_WORKSPACE_VERSION_LIMIT")
        snapshot = _workspace_snapshot_from_row(row, lifecycle=payload.state)
        if payload.state == "draft":
            _project_reference(conn, account_id=account_id, project_id=snapshot.get("project_id"))
        now = utc_now()
        revision = int(row[10]) + 1
        _write_workspace(
            conn, workspace_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision,
            now=now, archived_at=now if payload.state == "archived" else None,
        )
        _insert_workspace_version(conn, workspace_id=resolved, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, workspace_id=resolved, action=f"workspace_{payload.state}", revision=revision)
        changed = _workspace_row(conn, workspace_id=resolved, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể đọc lại document workspace")
        _audit(conn, request=request, account=account, action="document_workspace_lifecycle", target=resolved, detail=f"Set workspace lifecycle {payload.state}")
        return envelope(
            True, "Đã cập nhật trạng thái self-review document workspace.",
            data={"workspace": _workspace_public(changed, plan_count=_plan_count(conn, workspace_id=resolved, account_id=account_id)), **_boundary()},
            status_name=str(changed[9]),
        )

    return _idempotent(
        f"web-document-workspace:{account_id}:workspace:{resolved}:lifecycle:{payload.state}",
        account_id, payload.idempotency_key, fingerprint, operation,
    )


@router.post("/workspaces/{workspace_id}/restore-version")
async def document_workspace_restore_version(
    workspace_id: str,
    payload: RestoreVersionRequest,
    request: Request,
    account: dict = Depends(require_account),
    _csrf: None = Depends(require_csrf),
):
    _require_enabled()
    resolved = _uuid(workspace_id, label="Workspace ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({
        "action": "workspace_restore_version", "workspace_id": resolved,
        "expected_revision": payload.expected_revision, "target_revision": payload.target_revision,
    })

    def operation(conn: Any) -> dict[str, Any]:
        row = _workspace_row(conn, workspace_id=resolved, account_id=account_id)
        if not row:
            return _workspace_not_found()
        blocked = _workspace_writable(row)
        if blocked:
            return blocked
        if int(row[10]) != payload.expected_revision:
            return _revision_conflict()
        if not _can_add_version(conn, table="web_document_workspace_versions", entity_column="workspace_id", entity_id=resolved, account_id=account_id):
            return _guarded("Workspace đã đạt giới hạn lịch sử phiên bản.", "WEB_DOCUMENT_WORKSPACE_VERSION_LIMIT")
        version = conn.execute(
            """SELECT snapshot_json FROM web_document_workspace_versions
               WHERE workspace_id=? AND account_id=? AND revision=?""",
            (resolved, account_id, payload.target_revision),
        ).fetchone()
        if not version:
            return _guarded("Không tìm thấy revision workspace cần khôi phục.", "WEB_DOCUMENT_WORKSPACE_VERSION_NOT_FOUND")
        try:
            decoded = json.loads(str(version[0]))
            restored_payload = _workspace_payload_from_snapshot(decoded if isinstance(decoded, dict) else {})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=409, detail="Revision document workspace không hợp lệ") from exc
        snapshot = _workspace_snapshot(restored_payload, lifecycle="draft")
        _project_reference(conn, account_id=account_id, project_id=snapshot.get("project_id"))
        now = utc_now()
        revision = int(row[10]) + 1
        _write_workspace(conn, workspace_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_workspace_version(conn, workspace_id=resolved, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, workspace_id=resolved, action="workspace_version_restored", revision=revision)
        changed = _workspace_row(conn, workspace_id=resolved, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể đọc lại document workspace")
        _audit(conn, request=request, account=account, action="document_workspace_version_restored", target=resolved, detail="Restored document workspace revision")
        return envelope(
            True, "Đã khôi phục revision document workspace vào Draft.",
            data={
                "workspace": _workspace_public(changed, plan_count=_plan_count(conn, workspace_id=resolved, account_id=account_id)),
                "history_snapshot_recorded": True,
                **_boundary(),
            },
            status_name="draft",
        )

    return _idempotent(
        f"web-document-workspace:{account_id}:workspace:{resolved}:restore-version:{payload.target_revision}",
        account_id, payload.idempotency_key, fingerprint, operation,
    )


@router.post("/workspaces/{workspace_id}/plans")
async def document_plan_create(
    workspace_id: str,
    payload: PlanCreateRequest,
    request: Request,
    account: dict = Depends(require_account),
    _csrf: None = Depends(require_csrf),
):
    _require_enabled()
    resolved = _uuid(workspace_id, label="Workspace ID")
    account_id = str(account["id"])
    snapshot = _plan_snapshot(payload)
    fingerprint = _fingerprint({"action": "create_plan", "workspace_id": resolved, "expected_revision": payload.expected_revision, "payload": snapshot})

    def operation(conn: Any) -> dict[str, Any]:
        workspace = _workspace_row(conn, workspace_id=resolved, account_id=account_id)
        if not workspace:
            return _workspace_not_found()
        blocked = _workspace_writable(workspace)
        if blocked:
            return blocked
        if int(workspace[10]) != payload.expected_revision:
            return _revision_conflict()
        count = conn.execute(
            "SELECT COUNT(*) FROM web_document_plans WHERE workspace_id=? AND account_id=? AND state='active'",
            (resolved, account_id),
        ).fetchone()
        if int(count[0] or 0) >= MAX_PLANS_PER_WORKSPACE:
            return _guarded("Đã đạt giới hạn document plans đang hoạt động.", "WEB_DOCUMENT_PLAN_LIMIT")
        _validate_asset_refs(conn, account_id=account_id, snapshot=snapshot)
        now = utc_now()
        plan_id = str(uuid.uuid4())
        _insert_plan(
            conn, plan_id=plan_id, workspace_id=resolved, account_id=account_id,
            ordinal=_next_active_ordinal(conn, workspace_id=resolved, account_id=account_id), snapshot=snapshot, revision=1, now=now,
        )
        _insert_plan_version(conn, plan_id=plan_id, account_id=account_id, revision=1, snapshot=snapshot, now=now)
        changed_workspace = _advance_workspace_for_plan(
            conn, workspace=workspace, account_id=account_id, now=now, action="plan_created", plan_id=plan_id,
        )
        plan = _plan_row(conn, workspace_id=resolved, plan_id=plan_id, account_id=account_id)
        if not plan:
            raise HTTPException(status_code=500, detail="Không thể đọc lại document plan")
        _audit(conn, request=request, account=account, action="document_plan_created", target=plan_id, detail="Created document plan")
        return envelope(
            True, "Đã tạo document plan.",
            data={
                "workspace": _workspace_public(changed_workspace, plan_count=_plan_count(conn, workspace_id=resolved, account_id=account_id)),
                "plan": _plan_public(conn, plan, account_id=account_id),
                **_boundary(),
            },
            status_name="draft",
        )

    return _idempotent(
        f"web-document-workspace:{account_id}:workspace:{resolved}:plan:create",
        account_id, payload.idempotency_key, fingerprint, operation,
    )


@router.patch("/workspaces/{workspace_id}/plans/{plan_id}")
async def document_plan_update(
    workspace_id: str,
    plan_id: str,
    payload: PlanUpdateRequest,
    request: Request,
    account: dict = Depends(require_account),
    _csrf: None = Depends(require_csrf),
):
    _require_enabled()
    resolved_workspace = _uuid(workspace_id, label="Workspace ID")
    resolved_plan = _uuid(plan_id, label="Plan ID")
    account_id = str(account["id"])
    snapshot = _plan_snapshot(payload)
    fingerprint = _fingerprint({
        "action": "update_plan", "workspace_id": resolved_workspace, "plan_id": resolved_plan,
        "expected_revision": payload.expected_revision, "payload": snapshot,
    })

    def operation(conn: Any) -> dict[str, Any]:
        workspace = _workspace_row(conn, workspace_id=resolved_workspace, account_id=account_id)
        if not workspace:
            return _workspace_not_found()
        blocked = _workspace_writable(workspace)
        if blocked:
            return blocked
        plan = _plan_row(conn, workspace_id=resolved_workspace, plan_id=resolved_plan, account_id=account_id)
        if not plan:
            return _plan_not_found()
        if int(plan[10]) != payload.expected_revision:
            return _revision_conflict()
        if str(plan[9]) != "active":
            return _guarded("Document plan đã archive; hãy khôi phục trước khi chỉnh sửa.", "WEB_DOCUMENT_PLAN_ARCHIVED")
        if not _can_add_version(conn, table="web_document_plan_versions", entity_column="plan_id", entity_id=resolved_plan, account_id=account_id):
            return _guarded("Document plan đã đạt giới hạn lịch sử phiên bản.", "WEB_DOCUMENT_PLAN_VERSION_LIMIT")
        _validate_asset_refs(conn, account_id=account_id, snapshot=snapshot)
        now = utc_now()
        revision = int(plan[10]) + 1
        _write_plan(
            conn, plan_id=resolved_plan, workspace_id=resolved_workspace, account_id=account_id,
            snapshot=snapshot, revision=revision, now=now, archived_at=None,
        )
        _insert_plan_version(conn, plan_id=resolved_plan, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        changed_workspace = _advance_workspace_for_plan(
            conn, workspace=workspace, account_id=account_id, now=now, action="plan_updated", plan_id=resolved_plan,
        )
        changed = _plan_row(conn, workspace_id=resolved_workspace, plan_id=resolved_plan, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể đọc lại document plan")
        _audit(conn, request=request, account=account, action="document_plan_updated", target=resolved_plan, detail="Updated document plan")
        return envelope(
            True, "Đã lưu revision document plan mới.",
            data={
                "workspace": _workspace_public(changed_workspace, plan_count=_plan_count(conn, workspace_id=resolved_workspace, account_id=account_id)),
                "plan": _plan_public(conn, changed, account_id=account_id),
                **_boundary(),
            },
            status_name="draft",
        )

    return _idempotent(
        f"web-document-workspace:{account_id}:workspace:{resolved_workspace}:plan:{resolved_plan}:update",
        account_id, payload.idempotency_key, fingerprint, operation,
    )


def _plan_state_mutation(
    workspace_id: str,
    plan_id: str,
    payload: RevisionRequest,
    request: Request,
    account: dict,
    *,
    action: str,
) -> dict[str, Any]:
    _require_enabled()
    resolved_workspace = _uuid(workspace_id, label="Workspace ID")
    resolved_plan = _uuid(plan_id, label="Plan ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({
        "action": f"plan_{action}", "workspace_id": resolved_workspace, "plan_id": resolved_plan,
        "expected_revision": payload.expected_revision,
    })

    def operation(conn: Any) -> dict[str, Any]:
        workspace = _workspace_row(conn, workspace_id=resolved_workspace, account_id=account_id)
        if not workspace:
            return _workspace_not_found()
        blocked = _workspace_writable(workspace)
        if blocked:
            return blocked
        plan = _plan_row(conn, workspace_id=resolved_workspace, plan_id=resolved_plan, account_id=account_id)
        if not plan:
            return _plan_not_found()
        if int(plan[10]) != payload.expected_revision:
            return _revision_conflict()
        target_state = "archived" if action == "archive" else "active"
        if str(plan[9]) == target_state:
            return _guarded("Document plan đã ở trạng thái yêu cầu.", "WEB_DOCUMENT_PLAN_STATE_UNCHANGED")
        if not _can_add_version(conn, table="web_document_plan_versions", entity_column="plan_id", entity_id=resolved_plan, account_id=account_id):
            return _guarded("Document plan đã đạt giới hạn lịch sử phiên bản.", "WEB_DOCUMENT_PLAN_VERSION_LIMIT")
        snapshot = _plan_snapshot_from_row(plan, state=target_state)
        if target_state == "active":
            _validate_asset_refs(conn, account_id=account_id, snapshot=snapshot)
            ordinal = _next_active_ordinal(conn, workspace_id=resolved_workspace, account_id=account_id)
        else:
            ordinal = _next_archived_ordinal(conn, workspace_id=resolved_workspace, account_id=account_id)
        now = utc_now()
        revision = int(plan[10]) + 1
        _write_plan(
            conn, plan_id=resolved_plan, workspace_id=resolved_workspace, account_id=account_id,
            snapshot=snapshot, revision=revision, now=now, archived_at=now if target_state == "archived" else None,
            ordinal=ordinal,
        )
        _insert_plan_version(conn, plan_id=resolved_plan, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        changed_workspace = _advance_workspace_for_plan(
            conn, workspace=workspace, account_id=account_id, now=now, action=f"plan_{action}d", plan_id=resolved_plan,
        )
        changed = _plan_row(conn, workspace_id=resolved_workspace, plan_id=resolved_plan, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể đọc lại document plan")
        _audit(conn, request=request, account=account, action=f"document_plan_{action}d", target=resolved_plan, detail=f"{action.title()}d document plan")
        return envelope(
            True, "Đã cập nhật trạng thái document plan.",
            data={
                "workspace": _workspace_public(changed_workspace, plan_count=_plan_count(conn, workspace_id=resolved_workspace, account_id=account_id)),
                "plan": _plan_public(conn, changed, account_id=account_id),
                **_boundary(),
            },
            status_name="draft",
        )

    return _idempotent(
        f"web-document-workspace:{account_id}:workspace:{resolved_workspace}:plan:{resolved_plan}:{action}",
        account_id, payload.idempotency_key, fingerprint, operation,
    )


@router.post("/workspaces/{workspace_id}/plans/{plan_id}/archive")
async def document_plan_archive(
    workspace_id: str, plan_id: str, payload: RevisionRequest, request: Request,
    account: dict = Depends(require_account), _csrf: None = Depends(require_csrf),
):
    return _plan_state_mutation(workspace_id, plan_id, payload, request, account, action="archive")


@router.post("/workspaces/{workspace_id}/plans/{plan_id}/restore")
async def document_plan_restore(
    workspace_id: str, plan_id: str, payload: RevisionRequest, request: Request,
    account: dict = Depends(require_account), _csrf: None = Depends(require_csrf),
):
    return _plan_state_mutation(workspace_id, plan_id, payload, request, account, action="restore")


@router.post("/workspaces/{workspace_id}/plans/{plan_id}/restore-version")
async def document_plan_restore_version(
    workspace_id: str,
    plan_id: str,
    payload: RestoreVersionRequest,
    request: Request,
    account: dict = Depends(require_account),
    _csrf: None = Depends(require_csrf),
):
    _require_enabled()
    resolved_workspace = _uuid(workspace_id, label="Workspace ID")
    resolved_plan = _uuid(plan_id, label="Plan ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({
        "action": "restore_plan_version", "workspace_id": resolved_workspace, "plan_id": resolved_plan,
        "expected_revision": payload.expected_revision, "target_revision": payload.target_revision,
    })

    def operation(conn: Any) -> dict[str, Any]:
        workspace = _workspace_row(conn, workspace_id=resolved_workspace, account_id=account_id)
        if not workspace:
            return _workspace_not_found()
        blocked = _workspace_writable(workspace)
        if blocked:
            return blocked
        plan = _plan_row(conn, workspace_id=resolved_workspace, plan_id=resolved_plan, account_id=account_id)
        if not plan:
            return _plan_not_found()
        if int(plan[10]) != payload.expected_revision:
            return _revision_conflict()
        if str(plan[9]) != "active":
            return _guarded("Document plan đã archive; hãy khôi phục trước khi restore revision.", "WEB_DOCUMENT_PLAN_ARCHIVED")
        if not _can_add_version(conn, table="web_document_plan_versions", entity_column="plan_id", entity_id=resolved_plan, account_id=account_id):
            return _guarded("Document plan đã đạt giới hạn lịch sử phiên bản.", "WEB_DOCUMENT_PLAN_VERSION_LIMIT")
        version = conn.execute(
            "SELECT snapshot_json FROM web_document_plan_versions WHERE plan_id=? AND account_id=? AND revision=?",
            (resolved_plan, account_id, payload.target_revision),
        ).fetchone()
        if not version:
            return _guarded("Không tìm thấy revision document plan cần khôi phục.", "WEB_DOCUMENT_PLAN_VERSION_NOT_FOUND")
        try:
            decoded = json.loads(str(version[0]))
            restored_payload = _plan_payload_from_snapshot(decoded if isinstance(decoded, dict) else {})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=409, detail="Revision document plan không hợp lệ") from exc
        snapshot = _plan_snapshot(restored_payload, state="active")
        _validate_asset_refs(conn, account_id=account_id, snapshot=snapshot)
        now = utc_now()
        revision = int(plan[10]) + 1
        _write_plan(
            conn, plan_id=resolved_plan, workspace_id=resolved_workspace, account_id=account_id,
            snapshot=snapshot, revision=revision, now=now, archived_at=None,
        )
        _insert_plan_version(conn, plan_id=resolved_plan, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        changed_workspace = _advance_workspace_for_plan(
            conn, workspace=workspace, account_id=account_id, now=now, action="plan_version_restored", plan_id=resolved_plan,
        )
        changed = _plan_row(conn, workspace_id=resolved_workspace, plan_id=resolved_plan, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể đọc lại document plan")
        _audit(conn, request=request, account=account, action="document_plan_version_restored", target=resolved_plan, detail="Restored document plan revision")
        return envelope(
            True, "Đã khôi phục revision document plan.",
            data={
                "workspace": _workspace_public(changed_workspace, plan_count=_plan_count(conn, workspace_id=resolved_workspace, account_id=account_id)),
                "plan": _plan_public(conn, changed, account_id=account_id),
                "history_snapshot_recorded": True,
                **_boundary(),
            },
            status_name="draft",
        )

    return _idempotent(
        f"web-document-workspace:{account_id}:workspace:{resolved_workspace}:plan:{resolved_plan}:restore-version:{payload.target_revision}",
        account_id, payload.idempotency_key, fingerprint, operation,
    )


@router.post("/workspaces/{workspace_id}/plans/reorder")
async def document_plans_reorder(
    workspace_id: str,
    payload: ReorderRequest,
    request: Request,
    account: dict = Depends(require_account),
    _csrf: None = Depends(require_csrf),
):
    _require_enabled()
    resolved = _uuid(workspace_id, label="Workspace ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({
        "action": "reorder_plans", "workspace_id": resolved,
        "expected_revision": payload.expected_revision, "plan_ids": payload.plan_ids,
    })

    def operation(conn: Any) -> dict[str, Any]:
        workspace = _workspace_row(conn, workspace_id=resolved, account_id=account_id)
        if not workspace:
            return _workspace_not_found()
        blocked = _workspace_writable(workspace)
        if blocked:
            return blocked
        if int(workspace[10]) != payload.expected_revision:
            return _revision_conflict()
        active = conn.execute(
            """SELECT id FROM web_document_plans WHERE workspace_id=? AND account_id=? AND state='active'
               ORDER BY ordinal ASC, id ASC""",
            (resolved, account_id),
        ).fetchall()
        active_ids = [str(row[0]) for row in active]
        if set(payload.plan_ids) != set(active_ids) or len(payload.plan_ids) != len(active_ids):
            return _guarded("Thứ tự phải chứa chính xác mọi document plan đang hoạt động.", "WEB_DOCUMENT_PLAN_REORDER_INVALID")
        _normalise_archived_ordinals(conn, workspace_id=resolved, account_id=account_id)
        # Temporarily move active rows out of the target ordinal range before
        # swapping, preserving the schema's UNIQUE(workspace_id, ordinal).
        for index, plan_key in enumerate(payload.plan_ids, start=1):
            conn.execute(
                """UPDATE web_document_plans SET ordinal=?
                   WHERE id=? AND workspace_id=? AND account_id=? AND state='active'""",
                (-index, plan_key, resolved, account_id),
            )
        now = utc_now()
        for index, plan_key in enumerate(payload.plan_ids, start=1):
            conn.execute(
                """UPDATE web_document_plans SET ordinal=?, updated_at=?
                   WHERE id=? AND workspace_id=? AND account_id=? AND state='active'""",
                (index, now, plan_key, resolved, account_id),
            )
        changed_workspace = _advance_workspace_for_plan(
            conn, workspace=workspace, account_id=account_id, now=now, action="plans_reordered",
        )
        _audit(conn, request=request, account=account, action="document_plans_reordered", target=resolved, detail="Reordered document plans")
        return envelope(
            True, "Đã cập nhật thứ tự document plans.",
            data={
                "workspace": _workspace_public(changed_workspace, plan_count=_plan_count(conn, workspace_id=resolved, account_id=account_id)),
                "reordered": len(payload.plan_ids),
                **_boundary(),
            },
            status_name="draft",
        )

    return _idempotent(
        f"web-document-workspace:{account_id}:workspace:{resolved}:plans:reorder",
        account_id, payload.idempotency_key, fingerprint, operation,
    )


@router.get("/workspaces/{workspace_id}/estimate")
async def document_workspace_estimate(workspace_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    resolved = _uuid(workspace_id, label="Workspace ID")
    ensure_copyfast_schema()
    with read_transaction() as conn:
        workspace = _workspace_row(conn, workspace_id=resolved, account_id=str(account["id"]))
        if not workspace:
            return _workspace_not_found()
        return _estimate(conn, workspace=workspace, account_id=str(account["id"]))


def _events_data(conn: Any, *, account_id: str, limit: int) -> dict[str, Any]:
    rows = conn.execute(
        """SELECT action, entity_type, workspace_id, plan_id, revision, created_at
           FROM web_document_workspace_events WHERE account_id=? ORDER BY created_at DESC, id DESC LIMIT ?""",
        (account_id, limit),
    ).fetchall()
    return {
        "items": [
            {
                "action": str(row[0]),
                "entity_type": str(row[1]),
                "workspace_id": str(row[2]),
                "plan_id": str(row[3]) if row[3] else None,
                "revision": int(row[4]),
                "created_at": str(row[5]),
            }
            for row in rows
        ],
        **_boundary(),
    }


@router.get("/events")
async def document_workspace_events(
    limit: int = Query(default=MAX_EVENT_LIMIT, ge=1, le=MAX_EVENT_LIMIT),
    account: dict = Depends(require_account),
):
    _require_enabled()
    ensure_copyfast_schema()
    with read_transaction() as conn:
        data = _events_data(conn, account_id=str(account["id"]), limit=limit)
    return envelope(True, "Đã tải lịch sử Document & PDF Workspace.", data=data, status_name="read_only")


@router.get("/history")
async def document_workspace_history(
    limit: int = Query(default=MAX_EVENT_LIMIT, ge=1, le=MAX_EVENT_LIMIT),
    account: dict = Depends(require_account),
):
    """Compatibility-friendly alias of the same owner-scoped safe event list."""
    return await document_workspace_events(limit=limit, account=account)
