"""Web-native Privacy & Data Control Center.

This module deliberately covers a small, explicit subset of content authored
inside the standalone Web App.  It neither mirrors nor controls Telegram/Bot
identity, Xu, PayOS, provider, job, delivery, asset or support-evidence data.
An erasure action is only a staged, owner-scoped review request; this release
never deletes an account, a file or an authoring record automatically.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
import uuid
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from copyfast_auth import _record_audit, _request_id, current_session, envelope, require_account, require_csrf
from copyfast_db import data_controls_enabled, ensure_copyfast_schema, read_transaction, transaction, utc_now


router = APIRouter(prefix="/api/v1/account/data-controls", tags=["Web Data Controls"])

POLICY_VERSION = "web_data_controls_v1"
SCOPE_KEY = "web_authoring_only"
ERASURE_ACKNOWLEDGEMENT = "REQUEST WEB AUTHORING ERASURE"
CANCEL_ACKNOWLEDGEMENT = "CANCEL WEB ERASURE REQUEST"
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
REQUEST_STATES = frozenset({"awaiting_review", "identity_verification_pending", "cancelled", "closed"})
MUTABLE_REQUEST_STATES = frozenset({"awaiting_review", "identity_verification_pending"})
MAX_LIST_LIMIT = 50
MAX_LIST_OFFSET = 5_000
MAX_EXPORT_RECORDS = 8_000
MAX_EXPORT_BYTES = 12 * 1024 * 1024
IDEMPOTENCY_RETENTION = timedelta(hours=24)
MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT = 64
EXPORT_SCHEMA = "toan-aas-web-authoring-data-export-v1"


def _require_enabled() -> None:
    if not data_controls_enabled():
        raise HTTPException(
            status_code=503,
            detail="Data Control Center đang tạm dừng. WEBAPP_DATA_CONTROLS_ENABLED chưa được bật.",
        )


def _boundary(**extra: Any) -> dict[str, Any]:
    """Declare the intentionally narrow Web-only control boundary."""

    return {
        "execution": "web_data_control_request_only",
        "data_origin": "explicit_web_owned_authoring_projection",
        "policy_version": POLICY_VERSION,
        "bot_called": False,
        "telegram_data_included": False,
        "bridge_called": False,
        "wallet_mutated": False,
        "payment_processed": False,
        "provider_called": False,
        "job_created": False,
        "job_or_asset_data_included": False,
        "account_deleted": False,
        "files_deleted": False,
        "support_evidence_deleted": False,
        "external_notification_sent": False,
        **extra,
    }


def _guarded(message: str, code: str) -> dict[str, Any]:
    return envelope(False, message, data=_boundary(), status_name="guarded", error_code=code)


def _uuid(value: Any, *, label: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        # A path UUID is user input just as much as a JSON field.  Never let a
        # malformed cancel URL bubble out as a generic 500/Reliability event.
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


def _json_list(value: Any) -> list[Any]:
    try:
        parsed = json.loads(str(value or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []


def _active_session_in_transaction(conn: Any, *, account_id: str, session_id: str) -> None:
    """Re-check the actor session after a write lock is acquired.

    ``require_csrf`` proves the signed session at request entry.  A second
    owner/session check prevents a request waiting on SQLite from succeeding
    after a concurrent password/factor action revoked that session.
    """

    row = conn.execute(
        """SELECT 1 FROM web_sessions
           WHERE id=? AND account_id=? AND revoked_at IS NULL AND expires_at>? LIMIT 1""",
        (session_id, account_id, utc_now()),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Phiên đăng nhập không còn hợp lệ")


def _scope_counts(conn: Any, *, account_id: str) -> dict[str, int]:
    """Count only the explicit authoring projections owned by this module."""

    statements = {
        "memory_notes": "SELECT COUNT(*) FROM web_memory_notes WHERE account_id=?",
        "memory_reminders": "SELECT COUNT(*) FROM web_memory_reminders WHERE account_id=?",
        "prompt_templates": "SELECT COUNT(*) FROM web_prompt_templates WHERE account_id=?",
        "workboard_items": "SELECT COUNT(*) FROM web_workboard_items WHERE account_id=?",
        "workboard_checklists": "SELECT COUNT(*) FROM web_workboard_checklist_items WHERE account_id=?",
    }
    counts: dict[str, int] = {}
    for key, statement in statements.items():
        row = conn.execute(statement, (account_id,)).fetchone()
        counts[key] = int(row[0] or 0) if row else 0
    return counts


def _utf8_size(value: Any) -> int:
    return len(str(value or "").encode("utf-8"))


def _export_preflight(conn: Any, *, account_id: str, account: dict[str, Any]) -> int:
    """Reject oversized source sets before materialising any export rows.

    SQLite values can outlive current form limits, so a row count alone is not
    a memory boundary.  The aggregate byte projection is intentionally
    conservative and contains every text field selected below.  Exact JSON
    encoding still has its own streaming cap because escaping adds overhead.
    """

    counts = _scope_counts(conn, account_id=account_id)
    total_records = sum(counts.values())
    if total_records > MAX_EXPORT_RECORDS:
        raise ValueError("WEB_DATA_CONTROL_EXPORT_RECORD_LIMIT")
    byte_statements = (
        """SELECT COALESCE(SUM(
                COALESCE(LENGTH(CAST(title AS BLOB)), 0) + COALESCE(LENGTH(CAST(content AS BLOB)), 0) +
                COALESCE(LENGTH(CAST(tags_json AS BLOB)), 0) + COALESCE(LENGTH(CAST(category AS BLOB)), 0) +
                COALESCE(LENGTH(CAST(priority AS BLOB)), 0) + COALESCE(LENGTH(CAST(state AS BLOB)), 0) +
                COALESCE(LENGTH(CAST(created_at AS BLOB)), 0) + COALESCE(LENGTH(CAST(updated_at AS BLOB)), 0)
            ), 0) FROM web_memory_notes WHERE account_id=?""",
        """SELECT COALESCE(SUM(
                COALESCE(LENGTH(CAST(title AS BLOB)), 0) + COALESCE(LENGTH(CAST(body AS BLOB)), 0) +
                COALESCE(LENGTH(CAST(due_at AS BLOB)), 0) + COALESCE(LENGTH(CAST(next_run_at AS BLOB)), 0) +
                COALESCE(LENGTH(CAST(timezone AS BLOB)), 0) + COALESCE(LENGTH(CAST(repeat_rule AS BLOB)), 0) +
                COALESCE(LENGTH(CAST(state AS BLOB)), 0) + COALESCE(LENGTH(CAST(last_completed_at AS BLOB)), 0) +
                COALESCE(LENGTH(CAST(completed_at AS BLOB)), 0) + COALESCE(LENGTH(CAST(created_at AS BLOB)), 0) +
                COALESCE(LENGTH(CAST(updated_at AS BLOB)), 0)
            ), 0) FROM web_memory_reminders WHERE account_id=?""",
        """SELECT COALESCE(SUM(
                COALESCE(LENGTH(CAST(title AS BLOB)), 0) + COALESCE(LENGTH(CAST(category AS BLOB)), 0) +
                COALESCE(LENGTH(CAST(product_context AS BLOB)), 0) + COALESCE(LENGTH(CAST(platform AS BLOB)), 0) +
                COALESCE(LENGTH(CAST(style AS BLOB)), 0) + COALESCE(LENGTH(CAST(language AS BLOB)), 0) +
                COALESCE(LENGTH(CAST(prompt_text AS BLOB)), 0) + COALESCE(LENGTH(CAST(negative_prompt AS BLOB)), 0) +
                COALESCE(LENGTH(CAST(variables_json AS BLOB)), 0) + COALESCE(LENGTH(CAST(tags_json AS BLOB)), 0) +
                COALESCE(LENGTH(CAST(source_note AS BLOB)), 0) + COALESCE(LENGTH(CAST(license_note AS BLOB)), 0) +
                COALESCE(LENGTH(CAST(state AS BLOB)), 0) + COALESCE(LENGTH(CAST(created_at AS BLOB)), 0) +
                COALESCE(LENGTH(CAST(updated_at AS BLOB)), 0)
            ), 0) FROM web_prompt_templates WHERE account_id=?""",
        """SELECT COALESCE(SUM(
                COALESCE(LENGTH(CAST(title AS BLOB)), 0) + COALESCE(LENGTH(CAST(description AS BLOB)), 0) +
                COALESCE(LENGTH(CAST(priority AS BLOB)), 0) + COALESCE(LENGTH(CAST(due_at AS BLOB)), 0) +
                COALESCE(LENGTH(CAST(state AS BLOB)), 0) + COALESCE(LENGTH(CAST(created_at AS BLOB)), 0) +
                COALESCE(LENGTH(CAST(updated_at AS BLOB)), 0) + COALESCE(LENGTH(CAST(archived_at AS BLOB)), 0)
            ), 0) FROM web_workboard_items WHERE account_id=?""",
        """SELECT COALESCE(SUM(
                COALESCE(LENGTH(CAST(body AS BLOB)), 0) + COALESCE(LENGTH(CAST(state AS BLOB)), 0) +
                COALESCE(LENGTH(CAST(completed_at AS BLOB)), 0) + COALESCE(LENGTH(CAST(created_at AS BLOB)), 0) +
                COALESCE(LENGTH(CAST(updated_at AS BLOB)), 0) + COALESCE(LENGTH(CAST(archived_at AS BLOB)), 0)
            ), 0) FROM web_workboard_checklist_items WHERE account_id=?""",
        """SELECT COALESCE(SUM(
                COALESCE(LENGTH(CAST(locale AS BLOB)), 0) + COALESCE(LENGTH(CAST(timezone AS BLOB)), 0) +
                COALESCE(LENGTH(CAST(avatar_style AS BLOB)), 0) + COALESCE(LENGTH(CAST(created_at AS BLOB)), 0) +
                COALESCE(LENGTH(CAST(updated_at AS BLOB)), 0)
            ), 0) FROM web_account_profiles WHERE account_id=?""",
    )
    raw_bytes = _utf8_size(account.get("display_name"))
    for statement in byte_statements:
        row = conn.execute(statement, (account_id,)).fetchone()
        raw_bytes += int(row[0] or 0) if row else 0
        if raw_bytes > MAX_EXPORT_BYTES:
            raise ValueError("WEB_DATA_CONTROL_EXPORT_SIZE_LIMIT")
    return total_records


def _encode_bounded_export(document: dict[str, Any]) -> bytes:
    """Encode incrementally and fail before an oversized response is built."""

    encoded = bytearray()
    encoder = json.JSONEncoder(ensure_ascii=False, separators=(",", ":"))
    for fragment in encoder.iterencode(document):
        chunk = fragment.encode("utf-8")
        if len(encoded) + len(chunk) > MAX_EXPORT_BYTES:
            raise ValueError("WEB_DATA_CONTROL_EXPORT_SIZE_LIMIT")
        encoded.extend(chunk)
    return bytes(encoded)


def _inventory(conn: Any, *, account_id: str) -> dict[str, Any]:
    counts = _scope_counts(conn, account_id=account_id)
    authoring_records = sum(counts.values())
    return {
        "policy_version": POLICY_VERSION,
        "scope_key": SCOPE_KEY,
        "categories": [
            {
                "key": "account_profile",
                "label": "Hồ sơ Web",
                "record_count": 1,
                "export_available": True,
                "erasure_request_available": False,
                "retention": "Hồ sơ tài khoản không bị xóa tự động trong release này.",
            },
            {
                "key": "memory_center",
                "label": "Ghi chú & nhắc việc",
                "record_count": counts["memory_notes"] + counts["memory_reminders"],
                "export_available": True,
                "erasure_request_available": True,
                "retention": "Yêu cầu xóa chỉ được ghi nhận để review, không tự xóa.",
            },
            {
                "key": "prompt_library",
                "label": "Prompt Library hiện tại",
                "record_count": counts["prompt_templates"],
                "export_available": True,
                "erasure_request_available": True,
                "retention": "Chỉ template hiện tại thuộc phạm vi Web authoring v1.",
            },
            {
                "key": "workboard",
                "label": "Workboard hiện tại",
                "record_count": counts["workboard_items"] + counts["workboard_checklists"],
                "export_available": True,
                "erasure_request_available": True,
                "retention": "Reference nội bộ, event và lịch sử không nằm trong export v1.",
            },
        ],
        "authoring_record_count": authoring_records,
        "excluded_systems": [
            "Telegram/Bot identity và Core Bridge",
            "Xu, PayOS, webhook và thanh toán",
            "Provider, job, output, Asset Vault, file/blob/path và delivery",
            "Password, session, cookie, CSRF, OAuth identity/state và raw audit",
            "Support evidence, Operations, notifications, CRM và dữ liệu bên thứ ba",
        ],
        "erasure_policy": {
            "automatic_deletion": False,
            "human_review_required": True,
            "scope": SCOPE_KEY,
            "account_or_file_deletion": False,
        },
    }


def _request_public(row: tuple[Any, ...]) -> dict[str, Any]:
    request_id, scope_key, state, revision, requested_at, updated_at, cancelled_at = row
    normalized_state = str(state or "")
    if normalized_state not in REQUEST_STATES:
        normalized_state = "closed"
    return {
        "id": str(request_id),
        "scope_key": str(scope_key),
        "state": normalized_state,
        "revision": max(1, int(revision or 1)),
        "requested_at": str(requested_at),
        "updated_at": str(updated_at),
        "cancelled_at": str(cancelled_at) if cancelled_at else None,
        "automatic_deletion": False,
        "human_review_required": True,
    }


def _request_summary(conn: Any, *, account_id: str) -> dict[str, int]:
    counts = {state: 0 for state in REQUEST_STATES}
    rows = conn.execute(
        "SELECT state, COUNT(*) FROM web_data_control_requests WHERE account_id=? GROUP BY state",
        (account_id,),
    ).fetchall()
    for row in rows:
        state = str(row[0] or "")
        if state in counts:
            counts[state] = int(row[1] or 0)
    return counts


def _safe_receipt(value: dict[str, Any]) -> dict[str, Any]:
    """Persist only the narrow JSON receipt needed for retry semantics."""

    return {
        "ok": bool(value.get("ok") is True),
        "status": str(value.get("status") or "guarded"),
        "message": str(value.get("message") or ""),
        "data": value.get("data") if isinstance(value.get("data"), dict) else _boundary(),
        "error_code": value.get("error_code"),
    }


def _idempotent(
    *,
    scope: str,
    account_id: str,
    key: str,
    request_fingerprint: str,
    operation: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute(
            "DELETE FROM web_idempotency WHERE scope LIKE ? AND created_at<?",
            ("web-data-controls:%", _idempotency_cutoff()),
        )
        existing = conn.execute(
            "SELECT response_json, request_fingerprint FROM web_idempotency WHERE scope=? AND key=?",
            (scope, key),
        ).fetchone()
        if existing:
            if str(existing[1] or "") != request_fingerprint:
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho yêu cầu Data Control khác")
            try:
                receipt = json.loads(str(existing[0]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Receipt Data Control không hợp lệ") from exc
            if not isinstance(receipt, dict):
                raise HTTPException(status_code=409, detail="Receipt Data Control không hợp lệ")
            return receipt
        count = conn.execute(
            "SELECT COUNT(*) FROM web_idempotency WHERE scope LIKE ?",
            (f"web-data-controls:{account_id}:%",),
        ).fetchone()
        if int(count[0] or 0) >= MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT:
            return _guarded("Kho receipt thao tác tạm thời đang đầy. Vui lòng thử lại sau.", "WEB_DATA_CONTROL_IDEMPOTENCY_LIMIT")
        result = operation(conn)
        if result.get("ok") is True:
            receipt = _safe_receipt(result)
            conn.execute(
                """INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (scope, key, json.dumps(receipt, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
            )
            return receipt
        return result


class ExportPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_version: str = Field(min_length=1, max_length=80)
    confirm: bool = False

    @field_validator("policy_version")
    @classmethod
    def _policy(cls, value: str) -> str:
        return str(value or "").strip()


class ErasureRequestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_version: str = Field(min_length=1, max_length=80)
    scope_key: str = Field(min_length=1, max_length=80)
    acknowledgement: str = Field(min_length=1, max_length=80)
    confirm: bool = False
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("policy_version", "scope_key", "acknowledgement")
    @classmethod
    def _line(cls, value: str) -> str:
        return str(value or "").strip()

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class CancelRequestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1, le=1_000_000)
    acknowledgement: str = Field(min_length=1, max_length=80)
    confirm: bool = False
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("acknowledgement")
    @classmethod
    def _acknowledgement(cls, value: str) -> str:
        return str(value or "").strip()

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


def _export_document(conn: Any, *, account_id: str, account: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """Build a bounded direct snapshot from an explicit safe-table allowlist."""

    total_records = _export_preflight(conn, account_id=account_id, account=account)
    profile_row = conn.execute(
        """SELECT profile.locale, profile.timezone, profile.avatar_style, profile.created_at, profile.updated_at
           FROM web_account_profiles AS profile WHERE profile.account_id=?""",
        (account_id,),
    ).fetchone()
    profile = {
        "display_name": str(account.get("display_name") or ""),
        "locale": str(profile_row[0]) if profile_row else str(account.get("locale") or "vi"),
        "timezone": str(profile_row[1]) if profile_row else str(account.get("timezone") or "Asia/Ho_Chi_Minh"),
        "avatar_style": str(profile_row[2]) if profile_row else str(account.get("avatar_style") or "gradient"),
        "created_at": str(profile_row[3]) if profile_row else None,
        "updated_at": str(profile_row[4]) if profile_row else None,
    }
    note_rows = conn.execute(
        """SELECT title, content, tags_json, category, priority, state, revision, created_at, updated_at
           FROM web_memory_notes WHERE account_id=? ORDER BY created_at ASC, id ASC LIMIT ?""",
        (account_id, MAX_EXPORT_RECORDS + 1),
    ).fetchall()
    reminder_rows = conn.execute(
        """SELECT title, body, due_at, next_run_at, timezone, repeat_rule, state, revision,
                  last_completed_at, completed_at, created_at, updated_at
           FROM web_memory_reminders WHERE account_id=? ORDER BY created_at ASC, id ASC LIMIT ?""",
        (account_id, MAX_EXPORT_RECORDS + 1),
    ).fetchall()
    prompt_rows = conn.execute(
        """SELECT title, category, product_context, platform, style, language, prompt_text,
                  negative_prompt, variables_json, tags_json, source_note, license_note,
                  quality_score, state, revision, created_at, updated_at
           FROM web_prompt_templates WHERE account_id=? ORDER BY created_at ASC, id ASC LIMIT ?""",
        (account_id, MAX_EXPORT_RECORDS + 1),
    ).fetchall()
    workboard_rows = conn.execute(
        """SELECT id, title, description, priority, due_at, state, revision, created_at, updated_at, archived_at
           FROM web_workboard_items WHERE account_id=? ORDER BY created_at ASC, id ASC LIMIT ?""",
        (account_id, MAX_EXPORT_RECORDS + 1),
    ).fetchall()
    checklist_rows = conn.execute(
        """SELECT item_id, ordinal, body, is_done, state, revision, completed_at, created_at, updated_at, archived_at
           FROM web_workboard_checklist_items WHERE account_id=? ORDER BY item_id ASC, ordinal ASC, id ASC LIMIT ?""",
        (account_id, MAX_EXPORT_RECORDS + 1),
    ).fetchall()
    observed_records = len(note_rows) + len(reminder_rows) + len(prompt_rows) + len(workboard_rows) + len(checklist_rows)
    if observed_records != total_records or observed_records > MAX_EXPORT_RECORDS:
        raise ValueError("WEB_DATA_CONTROL_EXPORT_RECORD_LIMIT")
    checklist_by_item: dict[str, list[dict[str, Any]]] = {}
    for row in checklist_rows:
        checklist_by_item.setdefault(str(row[0]), []).append(
            {
                "ordinal": int(row[1] or 0),
                "body": str(row[2] or ""),
                "done": bool(row[3]),
                "state": str(row[4] or ""),
                "revision": int(row[5] or 1),
                "completed_at": str(row[6]) if row[6] else None,
                "created_at": str(row[7]),
                "updated_at": str(row[8]),
                "archived_at": str(row[9]) if row[9] else None,
            }
        )
    workboard: list[dict[str, Any]] = []
    for row in workboard_rows:
        item_id = str(row[0])
        workboard.append(
            {
                "title": str(row[1] or ""),
                "description": str(row[2] or ""),
                "priority": str(row[3] or "normal"),
                "due_at": str(row[4]) if row[4] else None,
                "state": str(row[5] or ""),
                "revision": int(row[6] or 1),
                "created_at": str(row[7]),
                "updated_at": str(row[8]),
                "archived_at": str(row[9]) if row[9] else None,
                "checklist": checklist_by_item.get(item_id, []),
            }
        )
    document = {
        "schema": EXPORT_SCHEMA,
        "policy_version": POLICY_VERSION,
        "generated_at": utc_now(),
        "scope": {
            "key": SCOPE_KEY,
            "description": "Current Web-authored profile, Memory, Prompt Library and Workboard records only.",
            "includes_history": False,
            "includes_assets_or_outputs": False,
        },
        "profile": profile,
        "memory": {
            "notes": [
                {
                    "title": str(row[0] or ""),
                    "content": str(row[1] or ""),
                    "tags": _json_list(row[2]),
                    "category": str(row[3] or ""),
                    "priority": str(row[4] or "normal"),
                    "state": str(row[5] or ""),
                    "revision": int(row[6] or 1),
                    "created_at": str(row[7]),
                    "updated_at": str(row[8]),
                }
                for row in note_rows
            ],
            "reminders": [
                {
                    "title": str(row[0] or ""),
                    "body": str(row[1] or ""),
                    "due_at": str(row[2]),
                    "next_run_at": str(row[3]),
                    "timezone": str(row[4] or "Asia/Ho_Chi_Minh"),
                    "repeat_rule": str(row[5] or "none"),
                    "state": str(row[6] or ""),
                    "revision": int(row[7] or 1),
                    "last_completed_at": str(row[8]) if row[8] else None,
                    "completed_at": str(row[9]) if row[9] else None,
                    "created_at": str(row[10]),
                    "updated_at": str(row[11]),
                }
                for row in reminder_rows
            ],
        },
        "prompt_library": [
            {
                "title": str(row[0] or ""),
                "category": str(row[1] or ""),
                "product_context": str(row[2] or ""),
                "platform": str(row[3] or ""),
                "style": str(row[4] or ""),
                "language": str(row[5] or ""),
                "prompt_text": str(row[6] or ""),
                "negative_prompt": str(row[7] or ""),
                "variables": _json_list(row[8]),
                "tags": _json_list(row[9]),
                "source_note": str(row[10] or ""),
                "license_note": str(row[11] or ""),
                "quality_score": int(row[12] or 0),
                "state": str(row[13] or ""),
                "revision": int(row[14] or 1),
                "created_at": str(row[15]),
                "updated_at": str(row[16]),
            }
            for row in prompt_rows
        ],
        "workboard": workboard,
        "excluded_systems": _inventory(conn, account_id=account_id)["excluded_systems"],
    }
    return document, total_records


@router.get("/summary")
async def summary(account: dict = Depends(require_account)):
    _require_enabled()
    ensure_copyfast_schema()
    account_id = str(account["id"])
    with read_transaction() as conn:
        inventory = _inventory(conn, account_id=account_id)
        request_counts = _request_summary(conn, account_id=account_id)
    return envelope(
        True,
        "Tổng quan Data Control chỉ thuộc dữ liệu authoring do Web App sở hữu.",
        data=_boundary(inventory=inventory, request_counts=request_counts),
        status_name="read_only",
    )


@router.get("/requests")
async def list_requests(
    limit: int = 20,
    offset: int = 0,
    account: dict = Depends(require_account),
):
    _require_enabled()
    bounded = max(1, min(int(limit), MAX_LIST_LIMIT))
    bounded_offset = int(offset)
    if bounded_offset < 0 or bounded_offset > MAX_LIST_OFFSET:
        raise HTTPException(status_code=422, detail="Offset Data Control không hợp lệ")
    ensure_copyfast_schema()
    with read_transaction() as conn:
        rows = conn.execute(
            """SELECT id, scope_key, state, revision, requested_at, updated_at, cancelled_at
               FROM web_data_control_requests WHERE account_id=?
               ORDER BY requested_at DESC, id DESC LIMIT ? OFFSET ?""",
            (str(account["id"]), bounded + 1, bounded_offset),
        ).fetchall()
    return envelope(
        True,
        "Lịch sử yêu cầu Data Control của signed Web account.",
        data=_boundary(
            items=[_request_public(tuple(row)) for row in rows[:bounded]],
            has_more=len(rows) > bounded,
            next_offset=bounded_offset + bounded if len(rows) > bounded else None,
        ),
        status_name="read_only",
    )


@router.post("/export.json")
async def export_authoring_data(payload: ExportPayload, request: Request, account: dict = Depends(require_csrf)):
    """Return a bounded, current JSON attachment without retaining a second copy."""

    _require_enabled()
    if not payload.confirm or payload.policy_version != POLICY_VERSION:
        return _guarded(
            "Cần xác nhận export theo policy Data Control hiện tại trước khi tạo file riêng tư.",
            "WEB_DATA_CONTROL_EXPORT_CONFIRMATION_REQUIRED",
        )
    actor = current_session(request)
    if str(actor["account"]["id"]) != str(account["id"]):
        raise HTTPException(status_code=401, detail="Phiên đăng nhập không còn hợp lệ")
    ensure_copyfast_schema()
    try:
        with read_transaction() as conn:
            document, record_count = _export_document(conn, account_id=str(account["id"]), account=account)
        body = _encode_bounded_export(document)
    except ValueError as exc:
        if str(exc) == "WEB_DATA_CONTROL_EXPORT_RECORD_LIMIT":
            return _guarded(
                "Phạm vi dữ liệu Web hiện vượt giới hạn export trực tiếp. Không có file một phần được tạo.",
                "WEB_DATA_CONTROL_EXPORT_RECORD_LIMIT",
            )
        if str(exc) == "WEB_DATA_CONTROL_EXPORT_SIZE_LIMIT":
            return _guarded(
                "Phạm vi dữ liệu Web hiện vượt giới hạn export trực tiếp. Không có file một phần được tạo.",
                "WEB_DATA_CONTROL_EXPORT_SIZE_LIMIT",
            )
        raise
    with transaction() as conn:
        _active_session_in_transaction(conn, account_id=str(account["id"]), session_id=str(actor["session_id"]))
        _record_audit(
            conn,
            account_id=str(account["id"]),
            canonical_user_id=None,
            action="web.data_control.export",
            request_id=_request_id(request),
            target=SCOPE_KEY,
            detail=f"generated bounded direct Web authoring JSON export records={record_count} bytes={len(body)}; no Bot, Telegram, wallet, payment, provider, job, asset or file state included",
        )
    return Response(
        content=body,
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="toan-aas-web-authoring-data.json"',
            "Cache-Control": "no-store, private",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "sandbox",
            "Cross-Origin-Resource-Policy": "same-origin",
        },
    )


@router.post("/erasure-requests")
async def create_erasure_request(
    payload: ErasureRequestPayload,
    request: Request,
    account: dict = Depends(require_csrf),
):
    _require_enabled()
    if (
        not payload.confirm
        or payload.policy_version != POLICY_VERSION
        or payload.scope_key != SCOPE_KEY
        or payload.acknowledgement != ERASURE_ACKNOWLEDGEMENT
    ):
        return _guarded(
            "Cần xác nhận đúng phạm vi Web authoring hiện tại trước khi gửi yêu cầu review xóa dữ liệu.",
            "WEB_DATA_CONTROL_ERASURE_CONFIRMATION_REQUIRED",
        )
    actor = current_session(request)
    if str(actor["account"]["id"]) != str(account["id"]):
        raise HTTPException(status_code=401, detail="Phiên đăng nhập không còn hợp lệ")
    account_id = str(account["id"])
    request_fingerprint = _fingerprint(
        {
            "policy_version": payload.policy_version,
            "scope_key": payload.scope_key,
            "acknowledgement": payload.acknowledgement,
            "confirm": payload.confirm,
        }
    )
    scope = f"web-data-controls:{account_id}:erasure-request"

    def operation(conn: Any) -> dict[str, Any]:
        _active_session_in_transaction(conn, account_id=account_id, session_id=str(actor["session_id"]))
        # A changed idempotency key must not manufacture an unbounded stack of
        # equivalent privacy requests.  One live request per account/scope is
        # sufficient for the human-review workflow; the signed owner can still
        # cancel it and submit a new one later if their intent changes.
        pending = conn.execute(
            """SELECT id, scope_key, state, revision, requested_at, updated_at, cancelled_at
               FROM web_data_control_requests
               WHERE account_id=? AND request_kind='erasure' AND scope_key=?
                 AND state IN ('awaiting_review', 'identity_verification_pending')
               ORDER BY requested_at DESC, id DESC LIMIT 1""",
            (account_id, SCOPE_KEY),
        ).fetchone()
        if pending:
            return _guarded(
                "Đã có một yêu cầu review xóa dữ liệu Web đang mở. Hãy theo dõi hoặc hủy yêu cầu đó trước.",
                "WEB_DATA_CONTROL_ERASURE_ALREADY_PENDING",
            ) | {"data": _boundary(request=_request_public(tuple(pending)))}
        now = utc_now()
        state = "awaiting_review" if bool(account.get("password_login_enabled")) else "identity_verification_pending"
        blockers = {
            "automatic_deletion": False,
            "human_review_required": True,
            "excluded_systems": _inventory(conn, account_id=account_id)["excluded_systems"],
        }
        request_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO web_data_control_requests
               (id, account_id, request_kind, scope_key, state, policy_version, blocker_summary_json,
                requested_at, updated_at, cancelled_at, closed_at, revision)
               VALUES (?, ?, 'erasure', ?, ?, ?, ?, ?, ?, NULL, NULL, 1)""",
            (
                request_id,
                account_id,
                SCOPE_KEY,
                state,
                POLICY_VERSION,
                json.dumps(blockers, ensure_ascii=False, separators=(",", ":")),
                now,
                now,
            ),
        )
        conn.execute(
            """INSERT INTO web_data_control_request_events
               (id, request_id, account_id, action, state, revision, created_at)
               VALUES (?, ?, ?, 'requested', ?, 1, ?)""",
            (str(uuid.uuid4()), request_id, account_id, state, now),
        )
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=None,
            action="web.data_control.erasure_requested",
            request_id=_request_id(request),
            target=SCOPE_KEY,
            detail="owner recorded a Web authoring erasure review request; no account, authoring record, file, support evidence, Bot, wallet, payment, provider or job data was deleted",
        )
        public = {
            "id": request_id,
            "scope_key": SCOPE_KEY,
            "state": state,
            "revision": 1,
            "requested_at": now,
            "updated_at": now,
            "cancelled_at": None,
            "automatic_deletion": False,
            "human_review_required": True,
        }
        message = (
            "Đã ghi nhận yêu cầu review xóa dữ liệu Web authoring. Chưa có dữ liệu nào bị xóa."
            if state == "awaiting_review"
            else "Đã ghi nhận yêu cầu nhưng cần xác minh identity theo quy trình riêng. Chưa có dữ liệu nào bị xóa."
        )
        return envelope(True, message, data=_boundary(request=public), status_name=state)

    return _idempotent(
        scope=scope,
        account_id=account_id,
        key=payload.idempotency_key,
        request_fingerprint=request_fingerprint,
        operation=operation,
    )


@router.post("/erasure-requests/{request_id}/cancel")
async def cancel_erasure_request(
    request_id: str,
    payload: CancelRequestPayload,
    request: Request,
    account: dict = Depends(require_csrf),
):
    _require_enabled()
    request_id = _uuid(request_id, label="Mã yêu cầu Data Control")
    if not payload.confirm or payload.acknowledgement != CANCEL_ACKNOWLEDGEMENT:
        return _guarded(
            "Cần xác nhận rõ ràng trước khi hủy yêu cầu review xóa dữ liệu Web.",
            "WEB_DATA_CONTROL_CANCEL_CONFIRMATION_REQUIRED",
        )
    actor = current_session(request)
    if str(actor["account"]["id"]) != str(account["id"]):
        raise HTTPException(status_code=401, detail="Phiên đăng nhập không còn hợp lệ")
    account_id = str(account["id"])
    request_fingerprint = _fingerprint(
        {
            "request_id": request_id,
            "expected_revision": payload.expected_revision,
            "acknowledgement": payload.acknowledgement,
            "confirm": payload.confirm,
        }
    )
    scope = f"web-data-controls:{account_id}:erasure-request:{request_id}:cancel"

    def operation(conn: Any) -> dict[str, Any]:
        _active_session_in_transaction(conn, account_id=account_id, session_id=str(actor["session_id"]))
        row = conn.execute(
            """SELECT id, scope_key, state, revision, requested_at, updated_at, cancelled_at
               FROM web_data_control_requests WHERE id=? AND account_id=? AND request_kind='erasure'""",
            (request_id, account_id),
        ).fetchone()
        if not row:
            return _guarded("Không tìm thấy yêu cầu Data Control đang có quyền truy cập.", "WEB_DATA_CONTROL_REQUEST_NOT_FOUND")
        current = _request_public(tuple(row))
        if int(current["revision"]) != payload.expected_revision:
            return _guarded("Yêu cầu Data Control đã có revision mới. Hãy tải lại trước khi tiếp tục.", "WEB_DATA_CONTROL_REQUEST_CONFLICT")
        if str(current["state"]) not in MUTABLE_REQUEST_STATES:
            return _guarded("Yêu cầu Data Control không còn có thể hủy.", "WEB_DATA_CONTROL_REQUEST_NOT_MUTABLE")
        now = utc_now()
        next_revision = int(current["revision"]) + 1
        updated = conn.execute(
            """UPDATE web_data_control_requests
               SET state='cancelled', revision=?, updated_at=?, cancelled_at=?
               WHERE id=? AND account_id=? AND revision=? AND state IN ('awaiting_review', 'identity_verification_pending')""",
            (next_revision, now, now, request_id, account_id, payload.expected_revision),
        )
        if int(updated.rowcount or 0) != 1:
            return _guarded("Yêu cầu Data Control đã thay đổi đồng thời. Hãy tải lại trước khi tiếp tục.", "WEB_DATA_CONTROL_REQUEST_CONFLICT")
        conn.execute(
            """INSERT INTO web_data_control_request_events
               (id, request_id, account_id, action, state, revision, created_at)
               VALUES (?, ?, ?, 'cancelled', 'cancelled', ?, ?)""",
            (str(uuid.uuid4()), request_id, account_id, next_revision, now),
        )
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=None,
            action="web.data_control.erasure_cancelled",
            request_id=_request_id(request),
            target=SCOPE_KEY,
            detail="owner cancelled a pending Web authoring erasure review request; no account, authoring record, file, support evidence, Bot, wallet, payment, provider or job data was changed",
        )
        return envelope(
            True,
            "Đã hủy yêu cầu review xóa dữ liệu Web. Không có dữ liệu nào bị xóa.",
            data=_boundary(
                request={
                    **current,
                    "state": "cancelled",
                    "revision": next_revision,
                    "updated_at": now,
                    "cancelled_at": now,
                }
            ),
            status_name="cancelled",
        )

    return _idempotent(
        scope=scope,
        account_id=account_id,
        key=payload.idempotency_key,
        request_fingerprint=request_fingerprint,
        operation=operation,
    )
