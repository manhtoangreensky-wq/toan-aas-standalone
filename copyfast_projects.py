"""Independent Project Center and versioned Studio Documents for the Web App.

This module intentionally has no Bot bridge, provider, wallet or payment
dependency.  It is the first Web-owned product core: signed users can keep
their own briefs, prompts, scripts and storyboards even when Telegram is not
linked or an external execution adapter is unavailable.
"""

from __future__ import annotations

import json
import hashlib
import hmac
import re
import uuid
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, StrictBool, field_validator

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import ensure_copyfast_schema, transaction, utc_now
from copyfast_workspace_draft_contract import is_workspace_draft_feature


router = APIRouter(prefix="/api/v1/projects", tags=["Web Project Center"])

PROJECT_STATES = frozenset({"active", "archived"})
DOCUMENT_STATES = frozenset({"active", "archived"})
DOCUMENT_KINDS = frozenset({"brief", "prompt", "caption", "script", "storyboard", "content_pack", "note"})
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|"
    r"client[ _-]?secret|secret(?:[ _-]?key)?|password|passphrase|authorization)\b\s*(?:[:=]|\bis\b)\s*"
    r"(?:bearer\s+)?[A-Za-z0-9_./+=:-]{8,}",
    re.IGNORECASE,
)
CARD_LIKE_PATTERN = re.compile(r"\b(?:\d[ -]?){13,19}\b")
WORKSPACE_DRAFT_BEARER_PATTERN = re.compile(r"\bbearer\s+[A-Za-z0-9._~+/=-]{12,}\b", re.IGNORECASE)
WORKSPACE_DRAFT_KEY_PATTERN = re.compile(r"\b(?:sk|pk|rk)_[A-Za-z0-9_-]{16,}\b", re.IGNORECASE)
WORKSPACE_DRAFT_VERIFICATION_PATTERN = re.compile(
    r"\b(?:otp|mã\s*xác\s*thực|ma\s*xac\s*thuc|cvv|cvc)\s*[:=]?\s*\d{3,8}\b",
    re.IGNORECASE,
)
WORKSPACE_DRAFT_MANUAL_PAYMENT_PROOF_PATTERN = re.compile(
    r"\b(?:txid|transaction(?:\s+(?:hash|id))?|mã\s*(?:giao\s*)?dịch|ma\s*(?:giao\s*)?dich|"
    r"biên\s*lai|bien\s*lai|chứng\s*từ|chung\s*tu|bill|"
    r"(?:số|so)\s*tài\s*khoản|bank\s*account|"
    r"qr\s*(?:thanh\s*toán|payment|code)?)\b",
    re.IGNORECASE,
)
WORKSPACE_DRAFT_CARD_CANDIDATE_PATTERN = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
WORKSPACE_DRAFT_FIELD_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
WORKSPACE_DRAFT_FEATURE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,120}$")
WORKSPACE_DRAFT_ALLOWED_FIELDS = frozenset({
    "request", "prompt", "brief", "script", "instructions", "notes",
    "template", "platform", "format", "duration", "style", "goal",
    "tier", "scene_count", "duration_seconds", "display_name", "mode",
    "song_length_mode", "item_count", "output_format", "target_language",
    "operation", "page_count", "page_range", "speed",
})
WORKSPACE_DRAFT_FORBIDDEN_FIELDS = frozenset({
    "upload_ids", "upload_id", "source", "sample", "audio", "document",
    "documents", "file", "files", "attachment", "voice_profile_id",
    "web_quote_receipt", "quote_receipt", "idempotency_key", "consent",
})
WORKSPACE_DRAFT_AUTHORITY_FIELDS = frozenset({
    "user_id", "canonical_user_id", "telegram_id", "chat_id", "account_id", "wallet_id",
    "balance", "balance_xu", "credit", "credits", "xu", "charged_xu", "estimated_xu",
    "amount", "amount_vnd", "price", "cost", "currency", "payment_id", "order_code",
    "checkout_url", "webhook", "provider", "provider_id", "api_key", "api_token", "token",
    "secret", "job_id", "job_status", "status", "output", "output_url", "asset_id", "download_url",
})
WORKSPACE_DRAFT_MAX_INPUT_BYTES = 16_000


def _clean_text(value: Any, *, label: str, minimum: int, maximum: int, allow_empty: bool = False) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text and allow_empty:
        return ""
    if "\x00" in text or not minimum <= len(text) <= maximum:
        raise ValueError(f"{label} cần từ {minimum} đến {maximum} ký tự hợp lệ")
    return text


def _clean_content(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if "\x00" in text or not 1 <= len(text) <= 12_000:
        raise ValueError("Nội dung Studio cần từ 1 đến 12.000 ký tự hợp lệ")
    if SECRET_ASSIGNMENT_PATTERN.search(text) or CARD_LIKE_PATTERN.search(text):
        raise ValueError("Studio Document không nhận secret, token, mật khẩu hoặc số thẻ")
    return text


def _looks_like_payment_card(candidate: str) -> bool:
    """Return true only for a plausible Luhn-valid payment-card number."""
    digits = "".join(character for character in candidate if character.isdigit())
    if not 13 <= len(digits) <= 19 or len(set(digits)) == 1:
        return False
    total = 0
    for index, character in enumerate(reversed(digits)):
        number = int(character)
        if index % 2:
            number *= 2
            if number > 9:
                number -= 9
        total += number
    return total % 10 == 0


def _assert_safe_workspace_draft_snapshot(title: str, values: dict[str, str]) -> None:
    """Revalidate persisted draft text before it becomes a durable Studio document.

    The normal Workspace intake performs this validation already.  This second
    check is intentionally local to the Project boundary because an upgraded
    or manually repaired database row is still untrusted input here.  It
    prevents the Studio document/audit path from becoming a second storage
    location for credentials, payment proof or card data.
    """
    content = "\n".join([title, *values.values()])
    if WORKSPACE_DRAFT_MANUAL_PAYMENT_PROOF_PATTERN.search(content):
        raise ValueError("WORKSPACE_DRAFT_INVALID")
    if any(pattern.search(content) for pattern in (
        SECRET_ASSIGNMENT_PATTERN,
        WORKSPACE_DRAFT_BEARER_PATTERN,
        WORKSPACE_DRAFT_KEY_PATTERN,
        WORKSPACE_DRAFT_VERIFICATION_PATTERN,
    )):
        raise ValueError("WORKSPACE_DRAFT_INVALID")
    if any(_looks_like_payment_card(match.group(0)) for match in WORKSPACE_DRAFT_CARD_CANDIDATE_PATTERN.finditer(content)):
        raise ValueError("WORKSPACE_DRAFT_INVALID")


def _uuid(value: str, *, label: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail=f"{label} không hợp lệ") from exc


def _idempotency_key(value: str) -> str:
    key = str(value or "").strip()
    if not IDEMPOTENCY_PATTERN.fullmatch(key):
        raise HTTPException(status_code=422, detail="Idempotency key không hợp lệ")
    return key


def _idempotent(scope: str, key: str, operation: Callable[[Any], dict[str, Any]]) -> dict[str, Any]:
    """Atomically replay a Web-owned mutation without delegating to Bot."""
    ensure_copyfast_schema()
    with transaction() as conn:
        existing = conn.execute(
            "SELECT response_json FROM web_idempotency WHERE scope=? AND key=?",
            (scope, key),
        ).fetchone()
        if existing:
            try:
                response = json.loads(str(existing[0]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Bản ghi idempotency Web không hợp lệ") from exc
            if isinstance(response, dict):
                return response
            raise HTTPException(status_code=409, detail="Bản ghi idempotency Web không hợp lệ")
        response = operation(conn)
        conn.execute(
            "INSERT INTO web_idempotency (scope, key, response_json, created_at) VALUES (?, ?, ?, ?)",
            (scope, key, json.dumps(response, ensure_ascii=False, separators=(",", ":")), utc_now()),
        )
    return response


def _project_public(row: tuple[Any, ...]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": str(row[0]),
        "title": str(row[1]),
        "summary": str(row[2] or ""),
        "objective": str(row[3] or ""),
        "state": str(row[4]),
        "created_at": str(row[5]),
        "updated_at": str(row[6]),
    }
    if len(row) > 7:
        result["document_count"] = int(row[7] or 0)
    return result


def _document_public(row: tuple[Any, ...], *, include_content: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": str(row[0]),
        "project_id": str(row[1]),
        "kind": str(row[2]),
        "title": str(row[3]),
        "revision": int(row[4]),
        "state": str(row[5]),
        "created_at": str(row[6]),
        "updated_at": str(row[7]),
    }
    if include_content:
        result["content"] = str(row[8])
    return result


def _document_not_found() -> dict[str, Any]:
    return envelope(
        False,
        "Không tìm thấy Studio Document thuộc Web account hiện tại.",
        status_name="guarded",
        error_code="STUDIO_DOCUMENT_NOT_FOUND",
    )


def _project_not_found() -> dict[str, Any]:
    return envelope(
        False,
        "Không tìm thấy Project thuộc Web account hiện tại.",
        status_name="guarded",
        error_code="WEB_PROJECT_NOT_FOUND",
    )


class ProjectCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    summary: str = Field(default="", max_length=1_000)
    objective: str = Field(default="", max_length=160)
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _clean_text(value, label="Tên Project", minimum=3, maximum=160)

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, value: str) -> str:
        return _clean_text(value, label="Tóm tắt", minimum=0, maximum=1_000, allow_empty=True)

    @field_validator("objective")
    @classmethod
    def validate_objective(cls, value: str) -> str:
        return _clean_text(value, label="Mục tiêu", minimum=0, maximum=160, allow_empty=True)


class ProjectUpdateRequest(ProjectCreateRequest):
    state: str = Field(default="active", max_length=16)

    @field_validator("state")
    @classmethod
    def validate_state(cls, value: str) -> str:
        state = str(value or "").strip().lower()
        if state not in PROJECT_STATES:
            raise ValueError("Trạng thái Project không hợp lệ")
        return state


class StudioDocumentCreateRequest(BaseModel):
    kind: str = Field(min_length=2, max_length=40)
    title: str = Field(min_length=3, max_length=160)
    content: str = Field(min_length=1, max_length=12_000)
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, value: str) -> str:
        kind = str(value or "").strip().lower()
        if kind not in DOCUMENT_KINDS:
            raise ValueError("Loại Studio Document chưa được hỗ trợ")
        return kind

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _clean_text(value, label="Tên Studio Document", minimum=3, maximum=160)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        return _clean_content(value)


class StudioDocumentUpdateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    content: str = Field(min_length=1, max_length=12_000)
    expected_revision: int = Field(ge=1, le=1_000_000)
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _clean_text(value, label="Tên Studio Document", minimum=3, maximum=160)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        return _clean_content(value)


class StudioDocumentRestoreRequest(BaseModel):
    expected_revision: int = Field(ge=1, le=1_000_000)
    idempotency_key: str = Field(min_length=12, max_length=160)


class WorkspaceDraftAttachRequest(BaseModel):
    """Request to create one immutable Web-only draft snapshot."""

    confirmed: StrictBool
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("confirmed")
    @classmethod
    def validate_confirmation(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("Hãy xác nhận trước khi tạo snapshot Studio từ bản nháp")
        return value


def _workspace_draft_snapshot(*, feature_key: Any, title: Any, input_json: Any) -> tuple[str, str, dict[str, str]]:
    """Validate a stored draft before turning it into Studio content.

    Draft rows are normally produced by the stricter Workspace API, but the
    database is still an untrusted boundary after upgrades or manual repair.
    A malformed row must therefore fail closed instead of becoming a
    document containing forbidden authority, file or payment fields.
    """
    feature = str(feature_key or "").strip()
    if not WORKSPACE_DRAFT_FEATURE_PATTERN.fullmatch(feature) or not is_workspace_draft_feature(feature):
        raise ValueError("WORKSPACE_DRAFT_INVALID")
    clean_title = _clean_text(title, label="Tên bản nháp", minimum=3, maximum=120)
    try:
        decoded = json.loads(str(input_json or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("WORKSPACE_DRAFT_INVALID") from exc
    if not isinstance(decoded, dict) or not 1 <= len(decoded) <= 30:
        raise ValueError("WORKSPACE_DRAFT_INVALID")
    values: dict[str, str] = {}
    for raw_name, raw_value in decoded.items():
        name = str(raw_name or "").strip()
        normalized_name = "".join(character for character in name.lower() if character.isalnum())
        if (
            not WORKSPACE_DRAFT_FIELD_PATTERN.fullmatch(name)
            or name not in WORKSPACE_DRAFT_ALLOWED_FIELDS
            or name in WORKSPACE_DRAFT_FORBIDDEN_FIELDS
            or name in WORKSPACE_DRAFT_AUTHORITY_FIELDS
            or normalized_name in {
                "userid", "canonicaluserid", "telegramid", "chatid", "accountid", "walletid",
                "balancexu", "chargedxu", "estimatedxu", "paymentid", "ordecode", "checkouturl",
                "providerid", "apikey", "apitoken", "jobid", "jobstatus", "outputurl", "assetid",
                "downloadurl",
            }
        ):
            raise ValueError("WORKSPACE_DRAFT_INVALID")
        if not isinstance(raw_value, str):
            raise ValueError("WORKSPACE_DRAFT_INVALID")
        text = raw_value.strip()
        if not text:
            continue
        if "\x00" in text or len(text) > 4_000:
            raise ValueError("WORKSPACE_DRAFT_INVALID")
        values[name] = text
    if not values:
        raise ValueError("WORKSPACE_DRAFT_INVALID")
    encoded = json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > WORKSPACE_DRAFT_MAX_INPUT_BYTES:
        raise ValueError("WORKSPACE_DRAFT_INVALID")
    _assert_safe_workspace_draft_snapshot(clean_title, values)
    content = "\n".join([f"Workflow: {feature}", f"Bản nháp: {clean_title}", *[f"{key}: {values[key]}" for key in sorted(values)]])
    try:
        content = _clean_content(content)
    except ValueError as exc:
        raise ValueError("WORKSPACE_DRAFT_INVALID") from exc
    document_title = _clean_text(f"{clean_title} · Studio", label="Tên Studio Document", minimum=3, maximum=160)
    return document_title, content, values


def _workspace_draft_attach_receipt(conn: Any, *, account_id: str, project_id: str, draft_id: str) -> dict[str, Any] | None:
    """Rebuild a minimal receipt from opaque owner-scoped IDs."""
    row = conn.execute(
        """SELECT p.id, p.title, p.summary, p.objective, p.state, p.created_at, p.updated_at,
                  d.id, d.project_id, d.kind, d.title, d.revision, d.state, d.created_at, d.updated_at,
                  d.content, w.id, w.feature_key, w.title, w.state, w.created_at, w.updated_at
           FROM web_workspace_draft_handoffs h
           JOIN web_projects p ON p.id=h.project_id AND p.account_id=h.account_id
           JOIN web_studio_documents d ON d.id=h.document_id AND d.account_id=h.account_id
           JOIN web_workspace_drafts w ON w.id=h.draft_id AND w.account_id=h.account_id
           WHERE h.account_id=? AND h.project_id=? AND h.draft_id=?""",
        (account_id, project_id, draft_id),
    ).fetchone()
    if not row:
        return None
    project = _project_public(tuple(row[:7]))
    document = _document_public(tuple(row[7:16]))
    source = {"id": str(row[16]), "feature_key": str(row[17]), "state": str(row[19])}
    return {
        "project": project,
        "document": document,
        "draft": source,
        "source": {"draft": source},
        "links": {
            "project": f"/projects/{project_id}",
            "document": f"/projects/documents/{document['id']}",
        },
        "boundary": "web_owned_snapshot_only",
    }


def _workspace_draft_attach_idempotent(
    *, scope: str, key: str, request_fingerprint: str, operation: Callable[[Any], dict[str, Any]]
) -> dict[str, Any]:
    """Replay attach responses and reject a reused key with another request."""
    ensure_copyfast_schema()
    with transaction() as conn:
        existing = conn.execute(
            "SELECT response_json, request_fingerprint FROM web_idempotency WHERE scope=? AND key=?",
            (scope, key),
        ).fetchone()
        if existing:
            stored_fingerprint = str(existing[1] or "")
            if stored_fingerprint and not hmac.compare_digest(stored_fingerprint, request_fingerprint):
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho yêu cầu handoff khác")
            try:
                response = json.loads(str(existing[0] or ""))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Receipt handoff Web không hợp lệ") from exc
            if not isinstance(response, dict):
                raise HTTPException(status_code=409, detail="Receipt handoff Web không hợp lệ")
            return response
        response = operation(conn)
        conn.execute(
            "INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at) VALUES (?, ?, ?, ?, ?)",
            (scope, key, json.dumps(response, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
        )
        return response


@router.post("/{project_id}/workspace-drafts/{draft_id}/attach")
async def attach_workspace_draft(
    project_id: str,
    draft_id: str,
    payload: WorkspaceDraftAttachRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Create one immutable Studio snapshot from an owned active draft.

    This is deliberately a Web-only authoring handoff.  It never resumes a
    Bot workflow, calls a provider, creates a job, charges Xu or touches
    PayOS.  The source draft remains active and unchanged.
    """
    project_id = _uuid(project_id, label="Mã Project")
    draft_id = _uuid(draft_id, label="Mã bản nháp")
    key = _idempotency_key(payload.idempotency_key)
    scope = f"web-project:{account['id']}:{project_id}:draft:{draft_id}:attach"
    request_fingerprint = hashlib.sha256(
        json.dumps({"project_id": project_id, "draft_id": draft_id}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    def operation(conn: Any) -> dict[str, Any]:
        # Durable pair uniqueness wins over a changed retry key.  A repeated
        # click therefore returns the original receipt without another row.
        existing = _workspace_draft_attach_receipt(
            conn, account_id=str(account["id"]), project_id=project_id, draft_id=draft_id
        )
        if existing:
            return envelope(
                True,
                "Bản nháp này đã được đưa vào Project trước đó; trả lại receipt hiện có.",
                data=existing,
                status_name="completed",
            )

        project = conn.execute(
            "SELECT id, title, summary, objective, state, created_at, updated_at FROM web_projects WHERE id=? AND account_id=?",
            (project_id, str(account["id"])),
        ).fetchone()
        if not project:
            return _project_not_found()
        if str(project[4]) != "active":
            return envelope(
                False,
                "Project đã lưu trữ; hãy mở lại Project trước khi đưa bản nháp vào Studio.",
                status_name="guarded",
                error_code="WEB_PROJECT_ARCHIVED",
            )
        draft = conn.execute(
            """SELECT id, feature_key, title, input_json, state, created_at, updated_at
               FROM web_workspace_drafts WHERE id=? AND account_id=?""",
            (draft_id, str(account["id"])),
        ).fetchone()
        if not draft:
            return envelope(
                False,
                "Không tìm thấy bản nháp thuộc tài khoản hiện tại.",
                status_name="guarded",
                error_code="WORKSPACE_DRAFT_NOT_FOUND",
            )
        if str(draft[4]) != "active":
            return envelope(
                False,
                "Bản nháp đã lưu trữ không thể đưa vào Project. Hãy tiếp tục brief để tạo bản mới.",
                status_name="guarded",
                error_code="WORKSPACE_DRAFT_ARCHIVED",
            )
        try:
            document_title, content, _values = _workspace_draft_snapshot(
                feature_key=draft[1], title=draft[2], input_json=draft[3]
            )
        except ValueError:
            return envelope(
                False,
                "Bản nháp không còn hợp lệ để tạo snapshot Studio; dữ liệu gốc vẫn được giữ nguyên.",
                status_name="guarded",
                error_code="WORKSPACE_DRAFT_INVALID",
            )

        document_id = str(uuid.uuid4())
        handoff_id = str(uuid.uuid4())
        now = utc_now()
        conn.execute(
            """INSERT INTO web_studio_documents
               (id, project_id, account_id, kind, title, content, revision, state, created_at, updated_at)
               VALUES (?, ?, ?, 'brief', ?, ?, 1, 'active', ?, ?)""",
            (document_id, project_id, str(account["id"]), document_title, content, now, now),
        )
        conn.execute(
            """INSERT INTO web_studio_document_versions
               (id, document_id, account_id, revision, title, content, created_at)
               VALUES (?, ?, ?, 1, ?, ?, ?)""",
            (str(uuid.uuid4()), document_id, str(account["id"]), document_title, content, now),
        )
        conn.execute(
            """INSERT INTO web_workspace_draft_handoffs
               (id, account_id, project_id, draft_id, document_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (handoff_id, str(account["id"]), project_id, draft_id, document_id, now),
        )
        conn.execute(
            "UPDATE web_projects SET updated_at=? WHERE id=? AND account_id=?",
            (now, project_id, str(account["id"])),
        )
        _record_audit(
            conn,
            account_id=str(account["id"]),
            canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="web.workspace_draft.attach",
            request_id=_request_id(request),
            target=document_id,
            outcome="ok",
            detail=f"web-owned draft snapshot project:{project_id} draft:{draft_id} feature:{draft[1]}",
        )
        receipt = _workspace_draft_attach_receipt(
            conn, account_id=str(account["id"]), project_id=project_id, draft_id=draft_id
        )
        if not receipt:
            raise RuntimeError("Workspace draft handoff receipt missing after insert")
        return envelope(
            True,
            "Đã đưa bản nháp vào Project Studio dưới dạng Studio Document phiên bản 1.",
            data=receipt,
            status_name="completed",
        )

    return _workspace_draft_attach_idempotent(
        scope=scope,
        key=key,
        request_fingerprint=request_fingerprint,
        operation=operation,
    )


@router.get("")
async def list_projects(
    q: str | None = None,
    state: str = "all",
    limit: int = 30,
    offset: int = 0,
    account: dict = Depends(require_account),
):
    """List only the signed account's Web-owned projects.

    Search, state and paging remain bounded and owner-scoped so the portal can
    browse a mature workspace without caching or reconstructing a project
    index in the browser.
    """
    bounded_limit = max(1, min(int(limit), 100))
    bounded_offset = max(0, min(int(offset), 10_000))
    requested_state = str(state or "all").strip().lower()
    if requested_state not in {"all", *PROJECT_STATES}:
        raise HTTPException(status_code=422, detail="Trạng thái lọc Project không hợp lệ")
    needle = _clean_text(q, label="Từ khóa tìm Project", minimum=0, maximum=100, allow_empty=True)
    if needle and (SECRET_ASSIGNMENT_PATTERN.search(needle) or CARD_LIKE_PATTERN.search(needle)):
        raise HTTPException(status_code=422, detail="Từ khóa tìm Project không nhận secret, token hoặc số thẻ")
    where = ["p.account_id=?"]
    params: list[Any] = [str(account["id"])]
    if requested_state != "all":
        where.append("p.state=?")
        params.append(requested_state)
    if needle:
        escaped = needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where.append("(p.title LIKE ? ESCAPE '\\' OR p.summary LIKE ? ESCAPE '\\' OR p.objective LIKE ? ESCAPE '\\')")
        params.extend([f"%{escaped}%", f"%{escaped}%", f"%{escaped}%"])
    predicate = " AND ".join(where)
    ensure_copyfast_schema()
    with transaction() as conn:
        rows = conn.execute(
            f"""SELECT p.id, p.title, p.summary, p.objective, p.state, p.created_at, p.updated_at,
                      COUNT(d.id) AS document_count
               FROM web_projects p
               LEFT JOIN web_studio_documents d ON d.project_id=p.id AND d.account_id=p.account_id AND d.state='active'
               WHERE {predicate}
               GROUP BY p.id
               ORDER BY CASE WHEN p.state='active' THEN 0 ELSE 1 END, p.updated_at DESC, p.id DESC
               LIMIT ? OFFSET ?""",
            (*params, bounded_limit + 1, bounded_offset),
        ).fetchall()
    has_more = len(rows) > bounded_limit
    items = [_project_public(tuple(row)) for row in rows[:bounded_limit]]
    return envelope(
        True,
        "Danh sách Project của Web Workspace.",
        data={
            "items": items,
            "has_more": has_more,
            "next_offset": bounded_offset + len(items) if has_more else None,
            "filters": {"q": needle, "state": requested_state},
            "pagination": {"limit": bounded_limit, "offset": bounded_offset, "returned": len(items)},
        },
        status_name="read_only",
    )


@router.post("")
async def create_project(payload: ProjectCreateRequest, request: Request, account: dict = Depends(require_csrf)):
    """Create a Web-owned Project without invoking Bot, payment or provider."""
    key = _idempotency_key(payload.idempotency_key)
    scope = f"web-project:{account['id']}:create"

    def operation(conn: Any) -> dict[str, Any]:
        project_id = str(uuid.uuid4())
        now = utc_now()
        conn.execute(
            """INSERT INTO web_projects (id, account_id, title, summary, objective, state, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 'active', ?, ?)""",
            (project_id, str(account["id"]), payload.title, payload.summary, payload.objective, now, now),
        )
        _record_audit(
            conn,
            account_id=str(account["id"]),
            canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="web.project.create",
            request_id=_request_id(request),
            target=project_id,
            outcome="ok",
            detail="web-owned project created",
        )
        project = _project_public((project_id, payload.title, payload.summary, payload.objective, "active", now, now, 0))
        return envelope(
            True,
            "Đã tạo Project trong Web Workspace. Chưa gọi Bot, provider, PayOS hoặc Xu.",
            data={"project": project},
            status_name="completed",
        )

    return _idempotent(scope, key, operation)


@router.get("/documents/{document_id}")
async def get_studio_document(document_id: str, account: dict = Depends(require_account)):
    """Read one bounded Studio Document and its version metadata for its owner."""
    document_id = _uuid(document_id, label="Mã Studio Document")
    ensure_copyfast_schema()
    with transaction() as conn:
        row = conn.execute(
            """SELECT id, project_id, kind, title, revision, state, created_at, updated_at, content
               FROM web_studio_documents WHERE id=? AND account_id=?""",
            (document_id, str(account["id"])),
        ).fetchone()
        if not row:
            return _document_not_found()
        versions = conn.execute(
            """SELECT revision, title, created_at FROM web_studio_document_versions
               WHERE document_id=? AND account_id=? ORDER BY revision DESC LIMIT 50""",
            (document_id, str(account["id"])),
        ).fetchall()
    return envelope(
        True,
        "Studio Document đã được nạp từ Web Workspace.",
        data={
            "document": _document_public(tuple(row), include_content=True),
            "versions": [{"revision": int(item[0]), "title": str(item[1]), "created_at": str(item[2])} for item in versions],
        },
        status_name="read_only",
    )


@router.patch("/documents/{document_id}")
async def update_studio_document(
    document_id: str,
    payload: StudioDocumentUpdateRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Save a new immutable version using optimistic revision control."""
    document_id = _uuid(document_id, label="Mã Studio Document")
    key = _idempotency_key(payload.idempotency_key)
    scope = f"web-project:{account['id']}:document:{document_id}:update"

    def operation(conn: Any) -> dict[str, Any]:
        current = conn.execute(
            """SELECT id, project_id, kind, title, revision, state, created_at, updated_at, content
               FROM web_studio_documents WHERE id=? AND account_id=?""",
            (document_id, str(account["id"])),
        ).fetchone()
        if not current:
            return _document_not_found()
        current_revision = int(current[4])
        if str(current[5]) != "active":
            return envelope(False, "Studio Document đã lưu trữ không thể chỉnh sửa.", status_name="guarded", error_code="STUDIO_DOCUMENT_ARCHIVED")
        if current_revision != payload.expected_revision:
            return envelope(
                False,
                "Studio Document đã có phiên bản mới. Hãy tải lại trước khi lưu để tránh ghi đè.",
                data={"current_revision": current_revision},
                status_name="guarded",
                error_code="STUDIO_DOCUMENT_CONFLICT",
            )
        next_revision = current_revision + 1
        now = utc_now()
        conn.execute(
            """UPDATE web_studio_documents SET title=?, content=?, revision=?, updated_at=?
               WHERE id=? AND account_id=? AND revision=? AND state='active'""",
            (payload.title, payload.content, next_revision, now, document_id, str(account["id"]), current_revision),
        )
        conn.execute(
            """INSERT INTO web_studio_document_versions (id, document_id, account_id, revision, title, content, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), document_id, str(account["id"]), next_revision, payload.title, payload.content, now),
        )
        _record_audit(
            conn,
            account_id=str(account["id"]),
            canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="web.studio_document.update",
            request_id=_request_id(request),
            target=document_id,
            outcome="ok",
            detail=f"web-owned studio document revision:{next_revision}",
        )
        document = _document_public((document_id, current[1], current[2], payload.title, next_revision, "active", current[6], now, payload.content), include_content=True)
        return envelope(True, "Đã lưu phiên bản mới của Studio Document trên Web.", data={"document": document}, status_name="completed")

    return _idempotent(scope, key, operation)


@router.post("/documents/{document_id}/restore/{revision}")
async def restore_studio_document_version(
    document_id: str,
    revision: int,
    payload: StudioDocumentRestoreRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Restore a prior Web-only version as a new immutable revision."""
    document_id = _uuid(document_id, label="Mã Studio Document")
    if not 1 <= int(revision) <= 1_000_000:
        raise HTTPException(status_code=422, detail="Phiên bản Studio Document không hợp lệ")
    key = _idempotency_key(payload.idempotency_key)
    scope = f"web-project:{account['id']}:document:{document_id}:restore:{revision}"

    def operation(conn: Any) -> dict[str, Any]:
        current = conn.execute(
            """SELECT id, project_id, kind, title, revision, state, created_at, updated_at, content
               FROM web_studio_documents WHERE id=? AND account_id=?""",
            (document_id, str(account["id"])),
        ).fetchone()
        if not current:
            return _document_not_found()
        current_revision = int(current[4])
        if current_revision != payload.expected_revision:
            return envelope(
                False,
                "Studio Document đã có phiên bản mới. Hãy tải lại trước khi khôi phục.",
                data={"current_revision": current_revision},
                status_name="guarded",
                error_code="STUDIO_DOCUMENT_CONFLICT",
            )
        source = conn.execute(
            """SELECT title, content FROM web_studio_document_versions
               WHERE document_id=? AND account_id=? AND revision=?""",
            (document_id, str(account["id"]), int(revision)),
        ).fetchone()
        if not source:
            return envelope(False, "Không tìm thấy phiên bản Studio Document thuộc Web account hiện tại.", status_name="guarded", error_code="STUDIO_DOCUMENT_VERSION_NOT_FOUND")
        next_revision = current_revision + 1
        now = utc_now()
        conn.execute(
            """UPDATE web_studio_documents SET title=?, content=?, revision=?, updated_at=?
               WHERE id=? AND account_id=? AND revision=? AND state='active'""",
            (str(source[0]), str(source[1]), next_revision, now, document_id, str(account["id"]), current_revision),
        )
        conn.execute(
            """INSERT INTO web_studio_document_versions (id, document_id, account_id, revision, title, content, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), document_id, str(account["id"]), next_revision, str(source[0]), str(source[1]), now),
        )
        _record_audit(
            conn,
            account_id=str(account["id"]),
            canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="web.studio_document.restore",
            request_id=_request_id(request),
            target=document_id,
            outcome="ok",
            detail=f"web-owned studio document restored_from:{revision} to:{next_revision}",
        )
        document = _document_public((document_id, current[1], current[2], str(source[0]), next_revision, "active", current[6], now, str(source[1])), include_content=True)
        return envelope(True, "Đã khôi phục phiên bản Studio Document thành một phiên bản mới.", data={"document": document}, status_name="completed")

    return _idempotent(scope, key, operation)


@router.get("/{project_id}")
async def get_project(project_id: str, account: dict = Depends(require_account)):
    """Read a project and bounded document metadata only for its owner."""
    project_id = _uuid(project_id, label="Mã Project")
    ensure_copyfast_schema()
    with transaction() as conn:
        row = conn.execute(
            """SELECT p.id, p.title, p.summary, p.objective, p.state, p.created_at, p.updated_at,
                      COUNT(d.id) AS document_count
               FROM web_projects p
               LEFT JOIN web_studio_documents d ON d.project_id=p.id AND d.account_id=p.account_id AND d.state='active'
               WHERE p.id=? AND p.account_id=?
               GROUP BY p.id""",
            (project_id, str(account["id"])),
        ).fetchone()
        if not row:
            return _project_not_found()
        documents = conn.execute(
            """SELECT id, project_id, kind, title, revision, state, created_at, updated_at
               FROM web_studio_documents WHERE project_id=? AND account_id=?
               ORDER BY CASE WHEN state='active' THEN 0 ELSE 1 END, updated_at DESC, id DESC LIMIT 100""",
            (project_id, str(account["id"])),
        ).fetchall()
    return envelope(
        True,
        "Project Web Workspace đã được nạp.",
        data={"project": _project_public(tuple(row)), "documents": [_document_public(tuple(item)) for item in documents]},
        status_name="read_only",
    )


@router.patch("/{project_id}")
async def update_project(
    project_id: str,
    payload: ProjectUpdateRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Update Web-owned project metadata without changing any integration state."""
    project_id = _uuid(project_id, label="Mã Project")
    key = _idempotency_key(payload.idempotency_key)
    scope = f"web-project:{account['id']}:{project_id}:update"

    def operation(conn: Any) -> dict[str, Any]:
        current = conn.execute(
            "SELECT id, title, summary, objective, state, created_at, updated_at FROM web_projects WHERE id=? AND account_id=?",
            (project_id, str(account["id"])),
        ).fetchone()
        if not current:
            return _project_not_found()
        now = utc_now()
        conn.execute(
            """UPDATE web_projects SET title=?, summary=?, objective=?, state=?, updated_at=?
               WHERE id=? AND account_id=?""",
            (payload.title, payload.summary, payload.objective, payload.state, now, project_id, str(account["id"])),
        )
        _record_audit(
            conn,
            account_id=str(account["id"]),
            canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="web.project.update",
            request_id=_request_id(request),
            target=project_id,
            outcome="ok",
            detail=f"web-owned project state:{payload.state}",
        )
        project = _project_public((project_id, payload.title, payload.summary, payload.objective, payload.state, current[5], now, 0))
        return envelope(True, "Đã cập nhật Project trên Web.", data={"project": project}, status_name="completed")

    return _idempotent(scope, key, operation)


@router.get("/{project_id}/documents")
async def list_project_documents(project_id: str, account: dict = Depends(require_account)):
    """List document metadata only after project ownership has been checked."""
    project_id = _uuid(project_id, label="Mã Project")
    ensure_copyfast_schema()
    with transaction() as conn:
        owner = conn.execute("SELECT id FROM web_projects WHERE id=? AND account_id=?", (project_id, str(account["id"]))).fetchone()
        if not owner:
            return _project_not_found()
        rows = conn.execute(
            """SELECT id, project_id, kind, title, revision, state, created_at, updated_at
               FROM web_studio_documents WHERE project_id=? AND account_id=?
               ORDER BY CASE WHEN state='active' THEN 0 ELSE 1 END, updated_at DESC, id DESC LIMIT 100""",
            (project_id, str(account["id"])),
        ).fetchall()
    return envelope(True, "Danh sách Studio Document của Project.", data={"items": [_document_public(tuple(row)) for row in rows]}, status_name="read_only")


@router.post("/{project_id}/documents")
async def create_studio_document(
    project_id: str,
    payload: StudioDocumentCreateRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Create a versioned, user-authored Studio Document inside a Project."""
    project_id = _uuid(project_id, label="Mã Project")
    key = _idempotency_key(payload.idempotency_key)
    scope = f"web-project:{account['id']}:{project_id}:document:create"

    def operation(conn: Any) -> dict[str, Any]:
        owner = conn.execute("SELECT id, state FROM web_projects WHERE id=? AND account_id=?", (project_id, str(account["id"]))).fetchone()
        if not owner:
            return _project_not_found()
        if str(owner[1]) != "active":
            return envelope(False, "Project đã lưu trữ; hãy mở lại Project trước khi thêm Studio Document.", status_name="guarded", error_code="WEB_PROJECT_ARCHIVED")
        document_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        now = utc_now()
        conn.execute(
            """INSERT INTO web_studio_documents
               (id, project_id, account_id, kind, title, content, revision, state, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 1, 'active', ?, ?)""",
            (document_id, project_id, str(account["id"]), payload.kind, payload.title, payload.content, now, now),
        )
        conn.execute(
            """INSERT INTO web_studio_document_versions
               (id, document_id, account_id, revision, title, content, created_at)
               VALUES (?, ?, ?, 1, ?, ?, ?)""",
            (version_id, document_id, str(account["id"]), payload.title, payload.content, now),
        )
        conn.execute("UPDATE web_projects SET updated_at=? WHERE id=? AND account_id=?", (now, project_id, str(account["id"])))
        _record_audit(
            conn,
            account_id=str(account["id"]),
            canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="web.studio_document.create",
            request_id=_request_id(request),
            target=document_id,
            outcome="ok",
            detail=f"web-owned studio document kind:{payload.kind}",
        )
        document = _document_public((document_id, project_id, payload.kind, payload.title, 1, "active", now, now, payload.content), include_content=True)
        return envelope(
            True,
            "Đã lưu Studio Document có phiên bản đầu tiên trong Project Web.",
            data={"document": document},
            status_name="completed",
        )

    return _idempotent(scope, key, operation)
