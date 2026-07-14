"""Private, Web-native Conversation Workspace.

The historical Telegram Bot owns its own Chat Pro/Deep modes, provider
selection, quotas, Xu ledger, jobs, delivery and Telegram transcript.  This
module deliberately owns none of that state.  It gives a signed Web account a
professional place to prepare a conversation: an explicit thread, private
context cards, human-authored prompt/decision turns and bounded revision
history.  It never calls a model, Bot, provider, wallet, payment, job or
delivery system and never fabricates an AI reply.
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
from copyfast_db import chat_workspace_enabled, ensure_copyfast_schema, read_transaction, transaction, utc_now


router = APIRouter(prefix="/api/v1/chat-workspace", tags=["Web Conversation Workspace"])

THREAD_STATES = frozenset({"draft", "review", "ready", "archived"})
THREAD_MODES = frozenset({"focus", "deep", "pro"})
CARD_KINDS = frozenset({"brief", "constraint", "reference", "instruction"})
TURN_KINDS = frozenset({"prompt", "note", "decision"})
CARD_STATES = frozenset({"active", "archived"})
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
UNSAFE_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
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
# Conversation Workspace intentionally stores human-authored planning text only.
# Links, storage/blob schemes and raw local paths can accidentally become a
# transport channel for private provider assets or browser-executable content,
# so they belong in a future, separately reviewed reference/upload adapter.
URL_OR_PATH_PATTERN = re.compile(
    r"(?:\bhttps?://|\bwww\.|\b(?:file|data|javascript|blob):|(?:^|[\s\"'])"
    r"(?:[A-Za-z]:[\\/]|/[^\s]+|\\\\[^\s]+))",
    re.IGNORECASE,
)

MAX_THREADS_PER_ACCOUNT = 500
MAX_CARDS_PER_THREAD = 80
MAX_VERSIONS_PER_THREAD = 100
# Every turn advances the private thread revision.  Keep the advertised turn
# ceiling truthful: a freshly created thread starts at revision 1, therefore
# it can never retain more than 99 newly authored turns before history reaches
# its deliberately bounded retention policy.
MAX_TURNS_PER_THREAD = MAX_VERSIONS_PER_THREAD - 1
MAX_LIST_LIMIT = 100
MAX_EVENT_LIMIT = 60
MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT = 1_024
IDEMPOTENCY_RETENTION = timedelta(hours=24)
ARCHIVED_ORDINAL_BASE = 1_000_000


def _require_enabled() -> None:
    if not chat_workspace_enabled():
        raise HTTPException(
            status_code=503,
            detail="AI Chat Workspace đang tạm dừng để bảo trì. WEBAPP_CHAT_WORKSPACE_ENABLED chưa được bật.",
        )


def _uuid(value: Any, *, label: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError(f"{label} không hợp lệ") from exc


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
        SECRET_PATTERN.search(value)
        or KNOWN_SECRET_PATTERN.search(value)
        or TELEGRAM_BOT_TOKEN_PATTERN.search(value)
        or PAYMENT_PATTERN.search(value)
        or EXTERNAL_HANDLE_PATTERN.search(value)
        or MARKUP_EXECUTION_PATTERN.search(value)
        or URL_OR_PATH_PATTERN.search(value)
        or "-----begin" in value.lower()
    )


def _line(value: Any, *, label: str, minimum: int, maximum: int, allow_empty: bool = False) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if UNSAFE_CONTROL_PATTERN.search(text) or len(text) > maximum or (not allow_empty and len(text) < minimum):
        if allow_empty:
            raise ValueError(f"{label} tối đa {maximum} ký tự hợp lệ")
        raise ValueError(f"{label} cần từ {minimum} đến {maximum} ký tự hợp lệ")
    if text and _sensitive_text(text):
        raise ValueError(f"{label} không nhận secret, URL/đường dẫn, mã xác thực, tham chiếu Bot/provider hoặc chứng từ thanh toán")
    return text


def _body(value: Any, *, label: str, maximum: int, allow_empty: bool = False) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if UNSAFE_CONTROL_PATTERN.search(text) or len(text) > maximum or (not allow_empty and not text):
        if allow_empty:
            raise ValueError(f"{label} tối đa {maximum:,} ký tự hợp lệ".replace(",", "."))
        raise ValueError(f"{label} cần từ 1 đến {maximum:,} ký tự hợp lệ".replace(",", "."))
    if text and _sensitive_text(text):
        raise ValueError(f"{label} không nhận secret, URL/đường dẫn, mã xác thực, tham chiếu Bot/provider hoặc chứng từ thanh toán")
    return text


def _tags(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("Tags phải là danh sách")
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        tag = _line(item, label="Tag", minimum=1, maximum=48)
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


def _excerpt(value: Any, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= limit else f"{text[:max(1, limit - 1)].rstrip()}…"


class ThreadPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    objective: str
    mode: str = "focus"
    system_context: str = ""
    tags: list[str] = Field(default_factory=list)
    project_id: str | None = None
    prompt_template_id: str | None = None
    pinned: bool = False

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return _line(value, label="Tên hội thoại", minimum=3, maximum=180)

    @field_validator("objective")
    @classmethod
    def _objective(cls, value: str) -> str:
        return _body(value, label="Mục tiêu", maximum=8_000)

    @field_validator("mode")
    @classmethod
    def _mode(cls, value: str) -> str:
        normalized = _line(value, label="Chế độ làm việc", minimum=1, maximum=24).lower()
        if normalized not in THREAD_MODES:
            raise ValueError("Chế độ hội thoại không hợp lệ")
        return normalized

    @field_validator("system_context")
    @classmethod
    def _system_context(cls, value: str) -> str:
        return _body(value, label="Ngữ cảnh làm việc", maximum=12_000, allow_empty=True)

    @field_validator("tags")
    @classmethod
    def _tag_values(cls, value: list[str]) -> list[str]:
        return _tags(value)

    @field_validator("project_id")
    @classmethod
    def _project(cls, value: str | None) -> str | None:
        return _optional_uuid(value, label="Project ID")

    @field_validator("prompt_template_id")
    @classmethod
    def _template(cls, value: str | None) -> str | None:
        return _optional_uuid(value, label="Prompt Template ID")


class ThreadCreateRequest(ThreadPayload):
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class ThreadUpdateRequest(ThreadPayload):
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
        if normalized not in THREAD_STATES:
            raise ValueError("Trạng thái hội thoại không hợp lệ")
        return normalized


class RestoreVersionRequest(RevisionRequest):
    target_revision: int = Field(ge=1, le=MAX_VERSIONS_PER_THREAD)


class ContextPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = "brief"
    title: str
    body: str
    tags: list[str] = Field(default_factory=list)

    @field_validator("kind")
    @classmethod
    def _kind(cls, value: str) -> str:
        normalized = _line(value, label="Loại context", minimum=1, maximum=24).lower()
        if normalized not in CARD_KINDS:
            raise ValueError("Loại context card không hợp lệ")
        return normalized

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return _line(value, label="Tiêu đề context", minimum=2, maximum=180)

    @field_validator("body")
    @classmethod
    def _body(cls, value: str) -> str:
        return _body(value, label="Nội dung context", maximum=12_000)

    @field_validator("tags")
    @classmethod
    def _tag_values(cls, value: list[str]) -> list[str]:
        return _tags(value)


class ContextCreateRequest(ContextPayload, RevisionRequest):
    pass


class ContextUpdateRequest(ContextPayload, RevisionRequest):
    pass


class ContextStateRequest(RevisionRequest):
    state: str

    @field_validator("state")
    @classmethod
    def _state(cls, value: str) -> str:
        normalized = _line(value, label="Trạng thái context", minimum=1, maximum=16).lower()
        if normalized not in CARD_STATES:
            raise ValueError("Trạng thái context không hợp lệ")
        return normalized


class TurnCreateRequest(RevisionRequest):
    kind: str = "prompt"
    body: str

    @field_validator("kind")
    @classmethod
    def _kind(cls, value: str) -> str:
        normalized = _line(value, label="Loại lượt", minimum=1, maximum=20).lower()
        if normalized not in TURN_KINDS:
            raise ValueError("Loại lượt hội thoại không hợp lệ")
        return normalized

    @field_validator("body")
    @classmethod
    def _body(cls, value: str) -> str:
        return _body(value, label="Nội dung lượt", maximum=16_000)


def _boundary(**extra: Any) -> dict[str, Any]:
    """Make the no-engine authoring boundary explicit in every response."""
    return {
        "execution": "authoring_only",
        "ai_execution_available": False,
        "provider_called": False,
        "bot_called": False,
        "assistant_reply_created": False,
        "output_created": False,
        "job_created": False,
        "payment_started": False,
        "wallet_mutated": False,
        "payment_processed": False,
        "browser_file_upload": False,
        "browser_media_url": False,
        "stream_available": False,
        "output_delivery": "guarded",
        **extra,
    }


def _guarded(message: str, code: str) -> dict[str, Any]:
    return envelope(False, message, data=_boundary(), status_name="guarded", error_code=code)


def _safe_receipt(response: dict[str, Any]) -> dict[str, Any]:
    """Persist opaque IDs/revisions only, never private threads or turns."""
    if not isinstance(response, dict) or response.get("ok") is not True:
        return response
    source = response.get("data") if isinstance(response.get("data"), dict) else {}
    data = _boundary()
    thread = source.get("thread")
    if isinstance(thread, dict) and isinstance(thread.get("id"), str):
        data["thread"] = {
            "id": str(thread["id"]),
            "revision": int(thread.get("revision") or 0),
            "state": str(thread.get("state") or ""),
        }
    for name in ("context", "turn"):
        item = source.get(name)
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            data[name] = {
                "id": str(item["id"]),
                "thread_id": str(item.get("thread_id") or ""),
                "revision": int(item.get("revision") or 0),
                "state": str(item.get("state") or ""),
            }
            if name == "turn":
                data[name]["assistant_reply_created"] = False
    for name in ("history_snapshot_recorded", "context_count", "turn_count"):
        if name in source:
            data[name] = source[name]
    return envelope(
        True,
        str(response.get("message") or "Đã lưu AI Chat Workspace."),
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
        conn.execute(
            "DELETE FROM web_idempotency WHERE scope LIKE ? AND created_at < ?",
            ("web-chat-workspace:%", _idempotency_cutoff()),
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
                raise HTTPException(status_code=409, detail="Receipt AI Chat Workspace không hợp lệ") from exc
            if not isinstance(receipt, dict):
                raise HTTPException(status_code=409, detail="Receipt AI Chat Workspace không hợp lệ")
            return receipt
        count = conn.execute(
            "SELECT COUNT(*) FROM web_idempotency WHERE scope LIKE ?",
            (f"web-chat-workspace:{account_id}:%",),
        ).fetchone()
        if int(count[0] or 0) >= MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT:
            return _guarded("Kho receipt thao tác tạm thời đang đầy. Vui lòng thử lại sau.", "WEB_CHAT_WORKSPACE_IDEMPOTENCY_LIMIT")
        response = operation(conn)
        if response.get("ok") is True:
            receipt = _safe_receipt(response)
            conn.execute(
                "INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at) VALUES (?, ?, ?, ?, ?)",
                (scope, key, json.dumps(receipt, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
            )
            return receipt
        return response


def _thread_snapshot(payload: ThreadPayload, *, state: str = "draft") -> dict[str, Any]:
    return {
        "title": payload.title,
        "objective": payload.objective,
        "mode": payload.mode,
        "system_context": payload.system_context,
        "tags": list(payload.tags),
        "project_id": payload.project_id,
        "prompt_template_id": payload.prompt_template_id,
        "pinned": bool(payload.pinned),
        "state": state,
    }


def _thread_snapshot_from_row(row: tuple[Any, ...], *, state: str | None = None) -> dict[str, Any]:
    return {
        "title": str(row[3]),
        "objective": str(row[4]),
        "mode": str(row[5]),
        "system_context": str(row[6]),
        "tags": _decode_tags(row[7]),
        "project_id": str(row[1]) if row[1] else None,
        "prompt_template_id": str(row[2]) if row[2] else None,
        "pinned": bool(row[9]),
        "state": state or str(row[8]),
    }


def _thread_payload_from_snapshot(snapshot: dict[str, Any]) -> ThreadPayload:
    return ThreadPayload(
        title=snapshot.get("title", ""),
        objective=snapshot.get("objective", ""),
        mode=snapshot.get("mode", "focus"),
        system_context=snapshot.get("system_context", ""),
        tags=snapshot.get("tags", []),
        project_id=snapshot.get("project_id"),
        prompt_template_id=snapshot.get("prompt_template_id"),
        pinned=bool(snapshot.get("pinned", False)),
    )


def _thread_row(conn: Any, *, thread_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, project_id, prompt_template_id, title, objective, mode, system_context,
                  tags_json, state, pinned, revision, created_at, updated_at, archived_at
           FROM web_chat_threads WHERE id=? AND account_id=?""",
        (thread_id, account_id),
    ).fetchone()


def _context_row(conn: Any, *, thread_id: str, context_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, thread_id, ordinal, kind, title, body, tags_json, state, revision,
                  created_at, updated_at, archived_at
           FROM web_chat_context_cards WHERE id=? AND thread_id=? AND account_id=?""",
        (context_id, thread_id, account_id),
    ).fetchone()


def _turn_row(conn: Any, *, thread_id: str, turn_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, thread_id, ordinal, kind, body, state, revision, created_at, updated_at, archived_at
           FROM web_chat_turns WHERE id=? AND thread_id=? AND account_id=?""",
        (turn_id, thread_id, account_id),
    ).fetchone()


def _thread_not_found() -> dict[str, Any]:
    return _guarded("Không tìm thấy hội thoại thuộc Web account hiện tại.", "WEB_CHAT_WORKSPACE_NOT_FOUND")


def _context_not_found() -> dict[str, Any]:
    return _guarded("Không tìm thấy context card thuộc hội thoại hiện tại.", "WEB_CHAT_CONTEXT_NOT_FOUND")


def _turn_not_found() -> dict[str, Any]:
    return _guarded("Không tìm thấy lượt ghi chú thuộc hội thoại hiện tại.", "WEB_CHAT_TURN_NOT_FOUND")


def _revision_conflict() -> dict[str, Any]:
    return _guarded("Dữ liệu đã thay đổi ở một phiên khác. Hãy tải lại trước khi tiếp tục.", "WEB_CHAT_WORKSPACE_REVISION_CONFLICT")


def _thread_writable(thread: tuple[Any, ...]) -> dict[str, Any] | None:
    state = str(thread[8])
    if state != "draft":
        return _guarded("Hội thoại chỉ có thể chỉnh sửa khi ở trạng thái bản nháp. Hãy đưa về bản nháp trước.", "WEB_CHAT_WORKSPACE_REVIEW_LOCKED")
    return None


def _project_reference(conn: Any, *, account_id: str, project_id: str | None, active: bool = True) -> dict[str, Any] | None:
    if not project_id:
        return None
    clause = " AND state='active'" if active else ""
    row = conn.execute(
        f"SELECT id, title, state, updated_at FROM web_projects WHERE id=? AND account_id=?{clause}",
        (project_id, account_id),
    ).fetchone()
    if not row:
        return None
    return {"id": str(row[0]), "title": str(row[1]), "state": str(row[2]), "updated_at": str(row[3])}


def _prompt_reference(conn: Any, *, account_id: str, template_id: str | None, active: bool = True) -> dict[str, Any] | None:
    if not template_id:
        return None
    clause = " AND state='active'" if active else ""
    row = conn.execute(
        f"SELECT id, title, category, platform, state, updated_at FROM web_prompt_templates WHERE id=? AND account_id=?{clause}",
        (template_id, account_id),
    ).fetchone()
    if not row:
        return None
    return {
        "id": str(row[0]), "title": str(row[1]), "category": str(row[2]), "platform": str(row[3]),
        "state": str(row[4]), "updated_at": str(row[5]),
    }


def _validate_references(conn: Any, *, account_id: str, snapshot: dict[str, Any]) -> None:
    project_id = snapshot.get("project_id")
    if project_id and not _project_reference(conn, account_id=account_id, project_id=str(project_id), active=True):
        raise HTTPException(status_code=422, detail="Project reference không thuộc account hiện tại hoặc đã archive")
    template_id = snapshot.get("prompt_template_id")
    if template_id and not _prompt_reference(conn, account_id=account_id, template_id=str(template_id), active=True):
        raise HTTPException(status_code=422, detail="Prompt template reference không thuộc account hiện tại hoặc đã archive")


def _thread_counts(conn: Any, *, thread_id: str, account_id: str) -> tuple[int, int]:
    contexts = conn.execute(
        "SELECT COUNT(*) FROM web_chat_context_cards WHERE thread_id=? AND account_id=? AND state='active'",
        (thread_id, account_id),
    ).fetchone()
    turns = conn.execute(
        "SELECT COUNT(*) FROM web_chat_turns WHERE thread_id=? AND account_id=? AND state='active'",
        (thread_id, account_id),
    ).fetchone()
    return int(contexts[0] or 0), int(turns[0] or 0)


def _thread_public(row: tuple[Any, ...], *, context_count: int = 0, turn_count: int = 0, include_content: bool = False) -> dict[str, Any]:
    item = {
        "id": str(row[0]),
        "project_id": str(row[1]) if row[1] else None,
        "prompt_template_id": str(row[2]) if row[2] else None,
        "title": str(row[3]),
        "objective_excerpt": _excerpt(row[4]),
        "mode": str(row[5]),
        "tags": _decode_tags(row[7]),
        "state": str(row[8]),
        "pinned": bool(row[9]),
        "revision": int(row[10]),
        "created_at": str(row[11]),
        "updated_at": str(row[12]),
        "archived_at": str(row[13]) if row[13] else None,
        "context_count": int(context_count),
        "turn_count": int(turn_count),
        "assistant_reply_created": False,
        "output_created": False,
    }
    if include_content:
        item["objective"] = str(row[4])
        item["system_context"] = str(row[6])
    return item


def _context_public(row: tuple[Any, ...], *, include_content: bool = True) -> dict[str, Any]:
    item = {
        "id": str(row[0]), "thread_id": str(row[1]), "ordinal": int(row[2]), "kind": str(row[3]),
        "title": str(row[4]), "tags": _decode_tags(row[6]), "state": str(row[7]), "revision": int(row[8]),
        "created_at": str(row[9]), "updated_at": str(row[10]), "archived_at": str(row[11]) if row[11] else None,
    }
    if include_content:
        item["body"] = str(row[5])
    return item


def _turn_public(row: tuple[Any, ...], *, include_content: bool = True) -> dict[str, Any]:
    item = {
        "id": str(row[0]), "thread_id": str(row[1]), "ordinal": int(row[2]), "kind": str(row[3]),
        "state": str(row[5]), "revision": int(row[6]), "created_at": str(row[7]),
        "updated_at": str(row[8]), "archived_at": str(row[9]) if row[9] else None,
        "assistant_reply_created": False,
    }
    if include_content:
        item["body"] = str(row[4])
    return item


def _version_public(row: tuple[Any, ...]) -> dict[str, Any]:
    try:
        snapshot = json.loads(str(row[1]))
    except (TypeError, ValueError, json.JSONDecodeError):
        snapshot = {}
    if not isinstance(snapshot, dict):
        snapshot = {}
    return {
        "revision": int(row[0]), "title": _excerpt(snapshot.get("title", ""), 180),
        "mode": str(snapshot.get("mode", "focus")), "state": str(snapshot.get("state", "draft")),
        "pinned": bool(snapshot.get("pinned", False)), "created_at": str(row[2]),
    }


def _insert_thread(conn: Any, *, thread_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str) -> None:
    conn.execute(
        """INSERT INTO web_chat_threads
           (id, account_id, project_id, prompt_template_id, title, objective, mode, system_context,
            tags_json, state, pinned, revision, created_at, updated_at, archived_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)""",
        (
            thread_id, account_id, snapshot["project_id"], snapshot["prompt_template_id"], snapshot["title"],
            snapshot["objective"], snapshot["mode"], snapshot["system_context"],
            json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")), snapshot["state"],
            int(bool(snapshot["pinned"])), revision, now, now,
        ),
    )


def _write_thread(
    conn: Any, *, thread_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str, archived_at: str | None
) -> None:
    conn.execute(
        """UPDATE web_chat_threads
           SET project_id=?, prompt_template_id=?, title=?, objective=?, mode=?, system_context=?, tags_json=?,
               state=?, pinned=?, revision=?, updated_at=?, archived_at=?
           WHERE id=? AND account_id=?""",
        (
            snapshot["project_id"], snapshot["prompt_template_id"], snapshot["title"], snapshot["objective"],
            snapshot["mode"], snapshot["system_context"], json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")),
            snapshot["state"], int(bool(snapshot["pinned"])), revision, now, archived_at, thread_id, account_id,
        ),
    )


def _insert_version(conn: Any, *, thread_id: str, account_id: str, revision: int, snapshot: dict[str, Any], now: str) -> None:
    conn.execute(
        """INSERT INTO web_chat_thread_versions (id, thread_id, account_id, revision, snapshot_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), thread_id, account_id, revision, json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), now),
    )


def _can_add_version(conn: Any, *, thread_id: str, account_id: str) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) FROM web_chat_thread_versions WHERE thread_id=? AND account_id=?",
        (thread_id, account_id),
    ).fetchone()
    return int(row[0] or 0) < MAX_VERSIONS_PER_THREAD


def _next_ordinal(conn: Any, *, table: str, thread_id: str, account_id: str, archived: bool = False) -> int:
    state = "archived" if archived else "active"
    row = conn.execute(
        f"SELECT COALESCE(MAX(ordinal), 0) FROM {table} WHERE thread_id=? AND account_id=? AND state=?",
        (thread_id, account_id, state),
    ).fetchone()
    value = int(row[0] or 0) + 1
    return max(ARCHIVED_ORDINAL_BASE, value) if archived else value


def _event(
    conn: Any, *, account_id: str, thread_id: str, entity_type: str, entity_id: str | None, action: str, revision: int
) -> None:
    conn.execute(
        """INSERT INTO web_chat_workspace_events
           (id, account_id, thread_id, entity_type, entity_id, action, revision, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), account_id, thread_id, entity_type, entity_id, action, revision, utc_now()),
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


def _advance_thread(
    conn: Any, *, thread: tuple[Any, ...], account_id: str, now: str, action: str, entity_type: str, entity_id: str | None
) -> tuple[Any, ...]:
    thread_id = str(thread[0])
    if not _can_add_version(conn, thread_id=thread_id, account_id=account_id):
        raise HTTPException(status_code=409, detail="Hội thoại đã đạt giới hạn lịch sử phiên bản")
    snapshot = _thread_snapshot_from_row(thread, state="draft")
    revision = int(thread[10]) + 1
    _write_thread(conn, thread_id=thread_id, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
    _insert_version(conn, thread_id=thread_id, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
    _event(conn, account_id=account_id, thread_id=thread_id, entity_type=entity_type, entity_id=entity_id, action=action, revision=revision)
    changed = _thread_row(conn, thread_id=thread_id, account_id=account_id)
    if not changed:
        raise HTTPException(status_code=500, detail="Không thể đọc lại hội thoại")
    return changed


def _references_listing(conn: Any, *, account_id: str) -> dict[str, Any]:
    projects = conn.execute(
        "SELECT id, title, updated_at FROM web_projects WHERE account_id=? AND state='active' ORDER BY updated_at DESC, id DESC LIMIT 100",
        (account_id,),
    ).fetchall()
    templates = conn.execute(
        """SELECT id, title, category, platform, tags_json, updated_at
           FROM web_prompt_templates WHERE account_id=? AND state='active'
           ORDER BY updated_at DESC, id DESC LIMIT 100""",
        (account_id,),
    ).fetchall()
    return {
        "projects": [{"id": str(row[0]), "title": str(row[1]), "updated_at": str(row[2])} for row in projects],
        "prompt_templates": [
            {"id": str(row[0]), "title": str(row[1]), "category": str(row[2]), "platform": str(row[3]), "tags": _decode_tags(row[4]), "updated_at": str(row[5])}
            for row in templates
        ],
        **_boundary(),
    }


def _thread_detail(conn: Any, *, thread_id: str, account_id: str) -> dict[str, Any] | None:
    thread = _thread_row(conn, thread_id=thread_id, account_id=account_id)
    if not thread:
        return None
    context_count, turn_count = _thread_counts(conn, thread_id=thread_id, account_id=account_id)
    versions = conn.execute(
        """SELECT revision, snapshot_json, created_at FROM web_chat_thread_versions
           WHERE thread_id=? AND account_id=? ORDER BY revision DESC LIMIT ?""",
        (thread_id, account_id, MAX_VERSIONS_PER_THREAD),
    ).fetchall()
    contexts = conn.execute(
        """SELECT id, thread_id, ordinal, kind, title, body, tags_json, state, revision, created_at, updated_at, archived_at
           FROM web_chat_context_cards WHERE thread_id=? AND account_id=?
           ORDER BY CASE state WHEN 'active' THEN 0 ELSE 1 END, ordinal ASC, created_at ASC LIMIT ?""",
        (thread_id, account_id, MAX_CARDS_PER_THREAD),
    ).fetchall()
    turns = conn.execute(
        """SELECT id, thread_id, ordinal, kind, body, state, revision, created_at, updated_at, archived_at
           FROM web_chat_turns WHERE thread_id=? AND account_id=?
           ORDER BY CASE state WHEN 'active' THEN 0 ELSE 1 END, ordinal ASC, created_at ASC LIMIT ?""",
        (thread_id, account_id, MAX_TURNS_PER_THREAD),
    ).fetchall()
    events = conn.execute(
        """SELECT entity_type, entity_id, action, revision, created_at FROM web_chat_workspace_events
           WHERE thread_id=? AND account_id=? ORDER BY created_at DESC, id DESC LIMIT ?""",
        (thread_id, account_id, MAX_EVENT_LIMIT),
    ).fetchall()
    return {
        "thread": _thread_public(thread, context_count=context_count, turn_count=turn_count, include_content=True),
        "versions": [_version_public(row) for row in versions],
        "contexts": [_context_public(row) for row in contexts],
        "turns": [_turn_public(row) for row in turns],
        "events": [
            {"entity_type": str(row[0]), "entity_id": str(row[1]) if row[1] else None, "action": str(row[2]), "revision": int(row[3]), "created_at": str(row[4])}
            for row in events
        ],
        "references": {
            "project": _project_reference(conn, account_id=account_id, project_id=str(thread[1]) if thread[1] else None, active=False),
            "prompt_template": _prompt_reference(conn, account_id=account_id, template_id=str(thread[2]) if thread[2] else None, active=False),
        },
        **_boundary(),
    }


def _summary_data(conn: Any, *, account_id: str) -> dict[str, Any]:
    counts = {
        str(row[0]): int(row[1])
        for row in conn.execute(
            "SELECT state, COUNT(*) FROM web_chat_threads WHERE account_id=? GROUP BY state", (account_id,)
        ).fetchall()
    }
    contexts = conn.execute("SELECT COUNT(*) FROM web_chat_context_cards WHERE account_id=? AND state='active'", (account_id,)).fetchone()
    turns = conn.execute("SELECT COUNT(*) FROM web_chat_turns WHERE account_id=? AND state='active'", (account_id,)).fetchone()
    return {
        "threads": {state: counts.get(state, 0) for state in ("draft", "review", "ready", "archived")} | {"total": sum(counts.values()), "limit_per_account": MAX_THREADS_PER_ACCOUNT},
        "contexts": {"active": int(contexts[0] or 0), "limit_per_thread": MAX_CARDS_PER_THREAD},
        "human_authored_turns": {"active": int(turns[0] or 0), "limit_per_thread": MAX_TURNS_PER_THREAD},
        **_boundary(),
    }


def _allowed_transition(current: str, target: str) -> bool:
    return target in {
        "draft": {"review", "archived"},
        "review": {"draft", "ready", "archived"},
        "ready": {"draft", "archived"},
        "archived": {"draft"},
    }.get(current, set())


@router.get("/summary")
async def chat_workspace_summary(account: dict = Depends(require_account)):
    _require_enabled()
    ensure_copyfast_schema()
    with read_transaction() as conn:
        data = _summary_data(conn, account_id=str(account["id"]))
    return envelope(True, "Đã tải tổng quan AI Chat Workspace.", data=data, status_name="read_only")


@router.get("/policy")
async def chat_workspace_policy(account: dict = Depends(require_account)):
    _require_enabled()
    return envelope(
        True,
        "AI Chat Workspace chỉ lưu hội thoại do bạn soạn, context card, prompt/decision note và revision Web-owned.",
        data={
            "allowed": ["thread_metadata", "manual_context", "human_authored_prompt", "decision_note", "revision_history", "project_reference", "prompt_template_reference"],
            "guarded": ["model_execution", "assistant_reply", "provider_stream", "telegram_transcript", "bot_mode", "wallet_charge", "job", "file_output", "delivery"],
            "notice": "Focus, Deep và Pro là profile biên tập cục bộ; không là model, quota hoặc quyền Bot. AI execution chỉ được bật bằng engine/adapter Web riêng đã kiểm định.",
            **_boundary(),
        },
        status_name="read_only",
    )


@router.get("/references")
async def chat_workspace_references(account: dict = Depends(require_account)):
    _require_enabled()
    ensure_copyfast_schema()
    with read_transaction() as conn:
        data = _references_listing(conn, account_id=str(account["id"]))
    return envelope(True, "Đã tải liên kết Project và Prompt Library thuộc account hiện tại.", data=data, status_name="read_only")


@router.get("/threads")
async def chat_workspace_threads(
    state: str = "all", q: str = "", limit: int = 50, offset: int = 0, account: dict = Depends(require_account)
):
    _require_enabled()
    ensure_copyfast_schema()
    normalized_state = str(state or "all").strip().lower()
    if normalized_state not in {"all", *THREAD_STATES}:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái không hợp lệ")
    normalized_q = re.sub(r"\s+", " ", str(q or "")).strip()
    if len(normalized_q) > 100 or UNSAFE_CONTROL_PATTERN.search(normalized_q) or _sensitive_text(normalized_q):
        raise HTTPException(status_code=422, detail="Từ khoá tìm kiếm không hợp lệ")
    safe_limit = min(max(int(limit or 50), 1), MAX_LIST_LIMIT)
    clauses = ["t.account_id=?"]
    values: list[Any] = [str(account["id"])]
    if normalized_state != "all":
        clauses.append("t.state=?")
        values.append(normalized_state)
    if normalized_q:
        pattern = "%" + normalized_q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        clauses.append("(t.title LIKE ? ESCAPE '\\' OR t.objective LIKE ? ESCAPE '\\' OR t.tags_json LIKE ? ESCAPE '\\')")
        values.extend([pattern, pattern, pattern])
    with read_transaction() as conn:
        total_row = conn.execute(
            f"SELECT COUNT(*) FROM web_chat_threads t WHERE {' AND '.join(clauses)}", values
        ).fetchone()
        total = int(total_row[0] or 0)
        requested_offset = max(int(offset or 0), 0)
        last_page_offset = max(0, ((total - 1) // safe_limit) * safe_limit) if total else 0
        safe_offset = min(requested_offset, last_page_offset)
        rows = conn.execute(
            f"""SELECT t.id, t.project_id, t.prompt_template_id, t.title, t.objective, t.mode, t.system_context,
                       t.tags_json, t.state, t.pinned, t.revision, t.created_at, t.updated_at, t.archived_at,
                       (SELECT COUNT(*) FROM web_chat_context_cards c WHERE c.thread_id=t.id AND c.account_id=t.account_id AND c.state='active'),
                       (SELECT COUNT(*) FROM web_chat_turns u WHERE u.thread_id=t.id AND u.account_id=t.account_id AND u.state='active')
                FROM web_chat_threads t WHERE {' AND '.join(clauses)}
                ORDER BY t.pinned DESC, t.updated_at DESC, t.id DESC LIMIT ? OFFSET ?""",
            [*values, safe_limit, safe_offset],
        ).fetchall()
        items = [_thread_public(row[:14], context_count=int(row[14] or 0), turn_count=int(row[15] or 0)) for row in rows]
    returned = len(items)
    has_more = safe_offset + returned < total
    return envelope(
        True,
        "Đã tải danh sách hội thoại Web-owned.",
        data={
            "items": items,
            "filter": {"state": normalized_state, "q": normalized_q},
            "pagination": {
                "total": total, "limit": safe_limit, "offset": safe_offset, "returned": returned,
                "has_more": has_more,
                "next_offset": safe_offset + returned if has_more else None,
                "previous_offset": max(0, safe_offset - safe_limit) if safe_offset > 0 else None,
            },
            **_boundary(),
        },
        status_name="read_only",
    )


@router.get("/threads/{thread_id}")
async def chat_workspace_detail(thread_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    try:
        resolved = _uuid(thread_id, label="Thread ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ensure_copyfast_schema()
    with read_transaction() as conn:
        data = _thread_detail(conn, thread_id=resolved, account_id=str(account["id"]))
    if not data:
        return _thread_not_found()
    return envelope(True, "Đã tải hội thoại Web-owned.", data=data, status_name="read_only")


@router.get("/threads/{thread_id}/execution-status")
async def chat_workspace_execution_status(thread_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    try:
        resolved = _uuid(thread_id, label="Thread ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ensure_copyfast_schema()
    with read_transaction() as conn:
        thread = _thread_row(conn, thread_id=resolved, account_id=str(account["id"]))
    if not thread:
        return _thread_not_found()
    return _guarded("AI execution chưa được cấu hình cho Web App. Thread vẫn có thể được biên tập và rà soát cục bộ.", "WEB_CHAT_EXECUTION_GUARDED")


@router.post("/threads")
async def chat_workspace_create(
    payload: ThreadCreateRequest, request: Request, account: dict = Depends(require_csrf)
):
    _require_enabled()
    account_id = str(account["id"])
    snapshot = _thread_snapshot(payload)
    fingerprint = _fingerprint({"action": "create_thread", "payload": snapshot})

    def operation(conn: Any) -> dict[str, Any]:
        total = conn.execute(
            "SELECT COUNT(*) FROM web_chat_threads WHERE account_id=?", (account_id,)
        ).fetchone()
        # Archive retains the private audit/revision record. Count it too so
        # archive/create cycles cannot grow account data without a bound.
        if int(total[0] or 0) >= MAX_THREADS_PER_ACCOUNT:
            return _guarded("Đã đạt giới hạn lưu trữ hội thoại của account.", "WEB_CHAT_WORKSPACE_LIMIT")
        _validate_references(conn, account_id=account_id, snapshot=snapshot)
        now = utc_now()
        thread_id = str(uuid.uuid4())
        _insert_thread(conn, thread_id=thread_id, account_id=account_id, snapshot=snapshot, revision=1, now=now)
        _insert_version(conn, thread_id=thread_id, account_id=account_id, revision=1, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, thread_id=thread_id, entity_type="thread", entity_id=None, action="thread_created", revision=1)
        row = _thread_row(conn, thread_id=thread_id, account_id=account_id)
        if not row:
            raise HTTPException(status_code=500, detail="Không thể tạo hội thoại")
        _audit(conn, request=request, account=account, action="chat_workspace_created", target=thread_id, detail="Created Web-native conversation thread")
        return envelope(True, "Đã tạo hội thoại Web-native. AI chưa được gọi.", data={"thread": _thread_public(row), **_boundary()}, status_name="draft")

    return _idempotent(f"web-chat-workspace:{account_id}:create_thread", account_id, payload.idempotency_key, fingerprint, operation)


@router.patch("/threads/{thread_id}")
async def chat_workspace_update(
    thread_id: str, payload: ThreadUpdateRequest, request: Request, account: dict = Depends(require_csrf)
):
    _require_enabled()
    try:
        resolved = _uuid(thread_id, label="Thread ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    account_id = str(account["id"])
    snapshot = _thread_snapshot(payload)
    fingerprint = _fingerprint({"action": "update_thread", "thread_id": resolved, "expected_revision": payload.expected_revision, "payload": snapshot})

    def operation(conn: Any) -> dict[str, Any]:
        row = _thread_row(conn, thread_id=resolved, account_id=account_id)
        if not row:
            return _thread_not_found()
        blocked = _thread_writable(row)
        if blocked:
            return blocked
        if int(row[10]) != payload.expected_revision:
            return _revision_conflict()
        if not _can_add_version(conn, thread_id=resolved, account_id=account_id):
            return _guarded("Hội thoại đã đạt giới hạn lịch sử phiên bản.", "WEB_CHAT_WORKSPACE_HISTORY_LIMIT")
        _validate_references(conn, account_id=account_id, snapshot=snapshot)
        now = utc_now()
        revision = int(row[10]) + 1
        _write_thread(conn, thread_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_version(conn, thread_id=resolved, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, thread_id=resolved, entity_type="thread", entity_id=None, action="thread_updated", revision=revision)
        changed = _thread_row(conn, thread_id=resolved, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể cập nhật hội thoại")
        contexts, turns = _thread_counts(conn, thread_id=resolved, account_id=account_id)
        _audit(conn, request=request, account=account, action="chat_workspace_updated", target=resolved, detail="Updated Web-native conversation thread")
        return envelope(True, "Đã cập nhật hội thoại Web-native.", data={"thread": _thread_public(changed, context_count=contexts, turn_count=turns), **_boundary()}, status_name="draft")

    return _idempotent(f"web-chat-workspace:{account_id}:thread:{resolved}:update", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/threads/{thread_id}/lifecycle")
async def chat_workspace_lifecycle(
    thread_id: str, payload: LifecycleRequest, request: Request, account: dict = Depends(require_csrf)
):
    _require_enabled()
    try:
        resolved = _uuid(thread_id, label="Thread ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    account_id = str(account["id"])
    fingerprint = _fingerprint({"action": "thread_lifecycle", "thread_id": resolved, "state": payload.state, "expected_revision": payload.expected_revision})

    def operation(conn: Any) -> dict[str, Any]:
        row = _thread_row(conn, thread_id=resolved, account_id=account_id)
        if not row:
            return _thread_not_found()
        current = str(row[8])
        if int(row[10]) != payload.expected_revision:
            return _revision_conflict()
        if current == payload.state:
            contexts, turns = _thread_counts(conn, thread_id=resolved, account_id=account_id)
            return envelope(True, "Hội thoại đã ở trạng thái này.", data={"thread": _thread_public(row, context_count=contexts, turn_count=turns), **_boundary()}, status_name=current)
        if not _allowed_transition(current, payload.state):
            return _guarded("Chuyển trạng thái hội thoại không hợp lệ.", "WEB_CHAT_WORKSPACE_LIFECYCLE_INVALID")
        if not _can_add_version(conn, thread_id=resolved, account_id=account_id):
            return _guarded("Hội thoại đã đạt giới hạn lịch sử phiên bản.", "WEB_CHAT_WORKSPACE_HISTORY_LIMIT")
        # A reference can become archived while its thread is archived. Do
        # not reactivate a stale Project/Prompt Library reference silently.
        snapshot = _thread_snapshot_from_row(row, state=payload.state)
        if payload.state != "archived":
            _validate_references(conn, account_id=account_id, snapshot=snapshot)
        now = utc_now()
        revision = int(row[10]) + 1
        _write_thread(conn, thread_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=now if payload.state == "archived" else None)
        _insert_version(conn, thread_id=resolved, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, thread_id=resolved, entity_type="thread", entity_id=None, action=f"thread_{payload.state}", revision=revision)
        changed = _thread_row(conn, thread_id=resolved, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể cập nhật trạng thái hội thoại")
        contexts, turns = _thread_counts(conn, thread_id=resolved, account_id=account_id)
        _audit(conn, request=request, account=account, action="chat_workspace_lifecycle", target=resolved, detail=f"Set chat workspace lifecycle {payload.state}")
        return envelope(True, "Đã cập nhật lifecycle hội thoại Web-native.", data={"thread": _thread_public(changed, context_count=contexts, turn_count=turns), **_boundary()}, status_name=payload.state)

    return _idempotent(f"web-chat-workspace:{account_id}:thread:{resolved}:lifecycle", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/threads/{thread_id}/restore-version")
async def chat_workspace_restore_version(
    thread_id: str, payload: RestoreVersionRequest, request: Request, account: dict = Depends(require_csrf)
):
    _require_enabled()
    try:
        resolved = _uuid(thread_id, label="Thread ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    account_id = str(account["id"])
    fingerprint = _fingerprint({"action": "restore_thread_version", "thread_id": resolved, "target_revision": payload.target_revision, "expected_revision": payload.expected_revision})

    def operation(conn: Any) -> dict[str, Any]:
        row = _thread_row(conn, thread_id=resolved, account_id=account_id)
        if not row:
            return _thread_not_found()
        blocked = _thread_writable(row)
        if blocked:
            return blocked
        if int(row[10]) != payload.expected_revision:
            return _revision_conflict()
        if not _can_add_version(conn, thread_id=resolved, account_id=account_id):
            return _guarded("Hội thoại đã đạt giới hạn lịch sử phiên bản.", "WEB_CHAT_WORKSPACE_HISTORY_LIMIT")
        stored = conn.execute(
            "SELECT snapshot_json FROM web_chat_thread_versions WHERE thread_id=? AND account_id=? AND revision=?",
            (resolved, account_id, payload.target_revision),
        ).fetchone()
        if not stored:
            return _guarded("Không tìm thấy revision hội thoại để khôi phục.", "WEB_CHAT_WORKSPACE_VERSION_NOT_FOUND")
        try:
            restored_payload = _thread_payload_from_snapshot(json.loads(str(stored[0])))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=409, detail="Revision hội thoại không hợp lệ") from exc
        snapshot = _thread_snapshot(restored_payload, state="draft")
        _validate_references(conn, account_id=account_id, snapshot=snapshot)
        now = utc_now()
        revision = int(row[10]) + 1
        _write_thread(conn, thread_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_version(conn, thread_id=resolved, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, thread_id=resolved, entity_type="thread", entity_id=None, action="thread_version_restored", revision=revision)
        changed = _thread_row(conn, thread_id=resolved, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể khôi phục revision hội thoại")
        contexts, turns = _thread_counts(conn, thread_id=resolved, account_id=account_id)
        _audit(conn, request=request, account=account, action="chat_workspace_version_restored", target=resolved, detail="Restored chat workspace revision")
        return envelope(True, "Đã khôi phục revision metadata của hội thoại. Context và lượt ghi chú giữ nguyên.", data={"thread": _thread_public(changed, context_count=contexts, turn_count=turns), "history_snapshot_recorded": True, **_boundary()}, status_name="draft")

    return _idempotent(f"web-chat-workspace:{account_id}:thread:{resolved}:restore-version", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/threads/{thread_id}/contexts")
async def chat_workspace_context_create(
    thread_id: str, payload: ContextCreateRequest, request: Request, account: dict = Depends(require_csrf)
):
    _require_enabled()
    try:
        resolved = _uuid(thread_id, label="Thread ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    account_id = str(account["id"])
    snapshot = payload.model_dump(exclude={"expected_revision", "idempotency_key"})
    fingerprint = _fingerprint({"action": "create_context", "thread_id": resolved, "expected_revision": payload.expected_revision, "payload": snapshot})

    def operation(conn: Any) -> dict[str, Any]:
        thread = _thread_row(conn, thread_id=resolved, account_id=account_id)
        if not thread:
            return _thread_not_found()
        blocked = _thread_writable(thread)
        if blocked:
            return blocked
        if int(thread[10]) != payload.expected_revision:
            return _revision_conflict()
        count = conn.execute("SELECT COUNT(*) FROM web_chat_context_cards WHERE thread_id=? AND account_id=? AND state='active'", (resolved, account_id)).fetchone()
        if int(count[0] or 0) >= MAX_CARDS_PER_THREAD:
            return _guarded("Đã đạt giới hạn context card đang hoạt động của hội thoại.", "WEB_CHAT_CONTEXT_LIMIT")
        now = utc_now()
        context_id = str(uuid.uuid4())
        ordinal = _next_ordinal(conn, table="web_chat_context_cards", thread_id=resolved, account_id=account_id)
        conn.execute(
            """INSERT INTO web_chat_context_cards
               (id, thread_id, account_id, ordinal, kind, title, body, tags_json, state, revision, created_at, updated_at, archived_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', 1, ?, ?, NULL)""",
            (context_id, resolved, account_id, ordinal, payload.kind, payload.title, payload.body, json.dumps(payload.tags, ensure_ascii=False, separators=(",", ":")), now, now),
        )
        changed_thread = _advance_thread(conn, thread=thread, account_id=account_id, now=now, action="context_created", entity_type="context", entity_id=context_id)
        context = _context_row(conn, thread_id=resolved, context_id=context_id, account_id=account_id)
        if not context:
            raise HTTPException(status_code=500, detail="Không thể tạo context card")
        contexts, turns = _thread_counts(conn, thread_id=resolved, account_id=account_id)
        _audit(conn, request=request, account=account, action="chat_context_created", target=context_id, detail="Created Web-native chat context")
        return envelope(True, "Đã thêm context card. Không có AI hoặc provider nào được gọi.", data={"thread": _thread_public(changed_thread, context_count=contexts, turn_count=turns), "context": _context_public(context), "context_count": contexts, **_boundary()}, status_name="draft")

    return _idempotent(f"web-chat-workspace:{account_id}:thread:{resolved}:context:create", account_id, payload.idempotency_key, fingerprint, operation)


@router.patch("/threads/{thread_id}/contexts/{context_id}")
async def chat_workspace_context_update(
    thread_id: str, context_id: str, payload: ContextUpdateRequest, request: Request, account: dict = Depends(require_csrf)
):
    _require_enabled()
    try:
        resolved_thread = _uuid(thread_id, label="Thread ID")
        resolved_context = _uuid(context_id, label="Context ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    account_id = str(account["id"])
    snapshot = payload.model_dump(exclude={"expected_revision", "idempotency_key"})
    fingerprint = _fingerprint({"action": "update_context", "thread_id": resolved_thread, "context_id": resolved_context, "expected_revision": payload.expected_revision, "payload": snapshot})

    def operation(conn: Any) -> dict[str, Any]:
        thread = _thread_row(conn, thread_id=resolved_thread, account_id=account_id)
        if not thread:
            return _thread_not_found()
        blocked = _thread_writable(thread)
        if blocked:
            return blocked
        if int(thread[10]) != payload.expected_revision:
            return _revision_conflict()
        context = _context_row(conn, thread_id=resolved_thread, context_id=resolved_context, account_id=account_id)
        if not context:
            return _context_not_found()
        if str(context[7]) != "active":
            return _guarded("Context card đã archive; hãy khôi phục trước khi chỉnh sửa.", "WEB_CHAT_CONTEXT_ARCHIVED")
        now = utc_now()
        revision = int(context[8]) + 1
        conn.execute(
            """UPDATE web_chat_context_cards SET kind=?, title=?, body=?, tags_json=?, revision=?, updated_at=?
               WHERE id=? AND thread_id=? AND account_id=?""",
            (payload.kind, payload.title, payload.body, json.dumps(payload.tags, ensure_ascii=False, separators=(",", ":")), revision, now, resolved_context, resolved_thread, account_id),
        )
        changed_thread = _advance_thread(conn, thread=thread, account_id=account_id, now=now, action="context_updated", entity_type="context", entity_id=resolved_context)
        changed = _context_row(conn, thread_id=resolved_thread, context_id=resolved_context, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể cập nhật context card")
        contexts, turns = _thread_counts(conn, thread_id=resolved_thread, account_id=account_id)
        _audit(conn, request=request, account=account, action="chat_context_updated", target=resolved_context, detail="Updated Web-native chat context")
        return envelope(True, "Đã cập nhật context card.", data={"thread": _thread_public(changed_thread, context_count=contexts, turn_count=turns), "context": _context_public(changed), **_boundary()}, status_name="draft")

    return _idempotent(f"web-chat-workspace:{account_id}:thread:{resolved_thread}:context:{resolved_context}:update", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/threads/{thread_id}/contexts/{context_id}/state")
async def chat_workspace_context_state(
    thread_id: str, context_id: str, payload: ContextStateRequest, request: Request, account: dict = Depends(require_csrf)
):
    _require_enabled()
    try:
        resolved_thread = _uuid(thread_id, label="Thread ID")
        resolved_context = _uuid(context_id, label="Context ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    account_id = str(account["id"])
    fingerprint = _fingerprint({"action": "context_state", "thread_id": resolved_thread, "context_id": resolved_context, "state": payload.state, "expected_revision": payload.expected_revision})

    def operation(conn: Any) -> dict[str, Any]:
        thread = _thread_row(conn, thread_id=resolved_thread, account_id=account_id)
        if not thread:
            return _thread_not_found()
        blocked = _thread_writable(thread)
        if blocked:
            return blocked
        if int(thread[10]) != payload.expected_revision:
            return _revision_conflict()
        context = _context_row(conn, thread_id=resolved_thread, context_id=resolved_context, account_id=account_id)
        if not context:
            return _context_not_found()
        if str(context[7]) == payload.state:
            contexts, turns = _thread_counts(conn, thread_id=resolved_thread, account_id=account_id)
            return envelope(True, "Context card đã ở trạng thái này.", data={"thread": _thread_public(thread, context_count=contexts, turn_count=turns), "context": _context_public(context), **_boundary()}, status_name="draft")
        now = utc_now()
        ordinal = _next_ordinal(conn, table="web_chat_context_cards", thread_id=resolved_thread, account_id=account_id, archived=payload.state == "archived")
        revision = int(context[8]) + 1
        conn.execute(
            """UPDATE web_chat_context_cards SET ordinal=?, state=?, revision=?, updated_at=?, archived_at=?
               WHERE id=? AND thread_id=? AND account_id=?""",
            (ordinal, payload.state, revision, now, now if payload.state == "archived" else None, resolved_context, resolved_thread, account_id),
        )
        changed_thread = _advance_thread(conn, thread=thread, account_id=account_id, now=now, action=f"context_{payload.state}", entity_type="context", entity_id=resolved_context)
        changed = _context_row(conn, thread_id=resolved_thread, context_id=resolved_context, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể thay đổi context card")
        contexts, turns = _thread_counts(conn, thread_id=resolved_thread, account_id=account_id)
        _audit(conn, request=request, account=account, action="chat_context_state", target=resolved_context, detail=f"Set chat context state {payload.state}")
        return envelope(True, "Đã cập nhật trạng thái context card.", data={"thread": _thread_public(changed_thread, context_count=contexts, turn_count=turns), "context": _context_public(changed), **_boundary()}, status_name="draft")

    return _idempotent(f"web-chat-workspace:{account_id}:thread:{resolved_thread}:context:{resolved_context}:state", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/threads/{thread_id}/turns")
async def chat_workspace_turn_create(
    thread_id: str, payload: TurnCreateRequest, request: Request, account: dict = Depends(require_csrf)
):
    _require_enabled()
    try:
        resolved = _uuid(thread_id, label="Thread ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    account_id = str(account["id"])
    fingerprint = _fingerprint({"action": "create_turn", "thread_id": resolved, "expected_revision": payload.expected_revision, "kind": payload.kind, "body": payload.body})

    def operation(conn: Any) -> dict[str, Any]:
        thread = _thread_row(conn, thread_id=resolved, account_id=account_id)
        if not thread:
            return _thread_not_found()
        blocked = _thread_writable(thread)
        if blocked:
            return blocked
        if int(thread[10]) != payload.expected_revision:
            return _revision_conflict()
        count = conn.execute("SELECT COUNT(*) FROM web_chat_turns WHERE thread_id=? AND account_id=? AND state='active'", (resolved, account_id)).fetchone()
        if int(count[0] or 0) >= MAX_TURNS_PER_THREAD:
            return _guarded("Đã đạt giới hạn lượt ghi chú đang hoạt động của hội thoại.", "WEB_CHAT_TURN_LIMIT")
        now = utc_now()
        turn_id = str(uuid.uuid4())
        ordinal = _next_ordinal(conn, table="web_chat_turns", thread_id=resolved, account_id=account_id)
        conn.execute(
            """INSERT INTO web_chat_turns
               (id, thread_id, account_id, ordinal, kind, body, state, revision, created_at, updated_at, archived_at)
               VALUES (?, ?, ?, ?, ?, ?, 'active', 1, ?, ?, NULL)""",
            (turn_id, resolved, account_id, ordinal, payload.kind, payload.body, now, now),
        )
        changed_thread = _advance_thread(conn, thread=thread, account_id=account_id, now=now, action="turn_created", entity_type="turn", entity_id=turn_id)
        turn = _turn_row(conn, thread_id=resolved, turn_id=turn_id, account_id=account_id)
        if not turn:
            raise HTTPException(status_code=500, detail="Không thể thêm lượt ghi chú")
        contexts, turns = _thread_counts(conn, thread_id=resolved, account_id=account_id)
        _audit(conn, request=request, account=account, action="chat_turn_created", target=turn_id, detail="Created human-authored chat turn")
        return envelope(True, "Đã thêm lượt ghi chú do bạn soạn. Chưa có phản hồi AI.", data={"thread": _thread_public(changed_thread, context_count=contexts, turn_count=turns), "turn": _turn_public(turn), "turn_count": turns, **_boundary()}, status_name="draft")

    return _idempotent(f"web-chat-workspace:{account_id}:thread:{resolved}:turn:create", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/threads/{thread_id}/turns/{turn_id}/state")
async def chat_workspace_turn_state(
    thread_id: str, turn_id: str, payload: ContextStateRequest, request: Request, account: dict = Depends(require_csrf)
):
    _require_enabled()
    try:
        resolved_thread = _uuid(thread_id, label="Thread ID")
        resolved_turn = _uuid(turn_id, label="Turn ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    account_id = str(account["id"])
    fingerprint = _fingerprint({"action": "turn_state", "thread_id": resolved_thread, "turn_id": resolved_turn, "state": payload.state, "expected_revision": payload.expected_revision})

    def operation(conn: Any) -> dict[str, Any]:
        thread = _thread_row(conn, thread_id=resolved_thread, account_id=account_id)
        if not thread:
            return _thread_not_found()
        blocked = _thread_writable(thread)
        if blocked:
            return blocked
        if int(thread[10]) != payload.expected_revision:
            return _revision_conflict()
        turn = _turn_row(conn, thread_id=resolved_thread, turn_id=resolved_turn, account_id=account_id)
        if not turn:
            return _turn_not_found()
        if str(turn[5]) == payload.state:
            contexts, turns = _thread_counts(conn, thread_id=resolved_thread, account_id=account_id)
            return envelope(True, "Lượt ghi chú đã ở trạng thái này.", data={"thread": _thread_public(thread, context_count=contexts, turn_count=turns), "turn": _turn_public(turn), **_boundary()}, status_name="draft")
        now = utc_now()
        ordinal = _next_ordinal(conn, table="web_chat_turns", thread_id=resolved_thread, account_id=account_id, archived=payload.state == "archived")
        revision = int(turn[6]) + 1
        conn.execute(
            """UPDATE web_chat_turns SET ordinal=?, state=?, revision=?, updated_at=?, archived_at=?
               WHERE id=? AND thread_id=? AND account_id=?""",
            (ordinal, payload.state, revision, now, now if payload.state == "archived" else None, resolved_turn, resolved_thread, account_id),
        )
        changed_thread = _advance_thread(conn, thread=thread, account_id=account_id, now=now, action=f"turn_{payload.state}", entity_type="turn", entity_id=resolved_turn)
        changed = _turn_row(conn, thread_id=resolved_thread, turn_id=resolved_turn, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể thay đổi lượt ghi chú")
        contexts, turns = _thread_counts(conn, thread_id=resolved_thread, account_id=account_id)
        _audit(conn, request=request, account=account, action="chat_turn_state", target=resolved_turn, detail=f"Set chat turn state {payload.state}")
        return envelope(True, "Đã cập nhật trạng thái lượt ghi chú.", data={"thread": _thread_public(changed_thread, context_count=contexts, turn_count=turns), "turn": _turn_public(changed), **_boundary()}, status_name="draft")

    return _idempotent(f"web-chat-workspace:{account_id}:thread:{resolved_thread}:turn:{resolved_turn}:state", account_id, payload.idempotency_key, fingerprint, operation)


@router.get("/events")
async def chat_workspace_events(limit: int = 50, account: dict = Depends(require_account)):
    _require_enabled()
    ensure_copyfast_schema()
    safe_limit = min(max(int(limit or 50), 1), MAX_EVENT_LIMIT)
    with read_transaction() as conn:
        rows = conn.execute(
            """SELECT thread_id, entity_type, entity_id, action, revision, created_at
               FROM web_chat_workspace_events WHERE account_id=?
               ORDER BY created_at DESC, id DESC LIMIT ?""",
            (str(account["id"]), safe_limit),
        ).fetchall()
    return envelope(
        True,
        "Đã tải activity AI Chat Workspace.",
        data={"items": [{"thread_id": str(row[0]), "entity_type": str(row[1]), "entity_id": str(row[2]) if row[2] else None, "action": str(row[3]), "revision": int(row[4]), "created_at": str(row[5])} for row in rows], **_boundary()},
        status_name="read_only",
    )
