"""Independent Project Center and versioned Studio Documents for the Web App.

This module intentionally has no Bot bridge, provider, wallet or payment
dependency.  It is the first Web-owned product core: signed users can keep
their own briefs, prompts, scripts and storyboards even when Telegram is not
linked or an external execution adapter is unavailable.
"""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import ensure_copyfast_schema, transaction, utc_now


router = APIRouter(prefix="/api/v1/projects", tags=["Web Project Center"])

PROJECT_STATES = frozenset({"active", "archived"})
DOCUMENT_STATES = frozenset({"active", "archived"})
DOCUMENT_KINDS = frozenset({"brief", "prompt", "caption", "script", "storyboard", "content_pack", "note"})
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|"
    r"client[ _-]?secret|password|passphrase|authorization)\b\s*(?:[:=]|\bis\b)\s*"
    r"(?:bearer\s+)?[A-Za-z0-9_./+=:-]{8,}",
    re.IGNORECASE,
)
CARD_LIKE_PATTERN = re.compile(r"\b(?:\d[ -]?){13,19}\b")


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


@router.get("")
async def list_projects(limit: int = 30, account: dict = Depends(require_account)):
    """List only the signed account's Web-owned projects."""
    bounded_limit = max(1, min(int(limit), 100))
    ensure_copyfast_schema()
    with transaction() as conn:
        rows = conn.execute(
            """SELECT p.id, p.title, p.summary, p.objective, p.state, p.created_at, p.updated_at,
                      COUNT(d.id) AS document_count
               FROM web_projects p
               LEFT JOIN web_studio_documents d ON d.project_id=p.id AND d.account_id=p.account_id AND d.state='active'
               WHERE p.account_id=?
               GROUP BY p.id
               ORDER BY CASE WHEN p.state='active' THEN 0 ELSE 1 END, p.updated_at DESC, p.id DESC
               LIMIT ?""",
            (str(account["id"]), bounded_limit + 1),
        ).fetchall()
    has_more = len(rows) > bounded_limit
    return envelope(
        True,
        "Danh sách Project của Web Workspace.",
        data={"items": [_project_public(tuple(row)) for row in rows[:bounded_limit]], "has_more": has_more},
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
