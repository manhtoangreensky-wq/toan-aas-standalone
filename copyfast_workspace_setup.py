"""Private, Web-native first-run workspace setup profile.

This module stores only a signed Web account's declared working preferences.
It never imports the Telegram Bot, calls the bridge or a provider, creates a
job, changes wallet/payment state, publishes content, or sends a notification.
The profile is a navigation/discovery aid rather than an authority grant.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

from copyfast_auth import (
    DEFAULT_INTERFACE_LOCALE,
    INTERFACE_LOCALES,
    _record_audit,
    _request_id,
    envelope,
    require_account,
    require_csrf,
)
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction, utc_now


router = APIRouter(prefix="/api/v1/workspace/setup", tags=["Web Workspace Setup"])

SETUP_STATES = frozenset({"not_started", "completed", "skipped"})
ROLES = frozenset({"solo_creator", "team_lead", "operator", "learner"})
GOALS = frozenset({"organize_work", "create_content", "build_brand", "run_operations", "learn_workflows"})
EXPERIENCE_LEVELS = frozenset({"new", "growing", "advanced"})
FOCUS_AREAS = frozenset({"projects", "content", "image", "voice", "music", "subtitle", "documents", "automation"})
MAX_FOCUS_AREAS = 3
MAX_REVISION = 2_147_483_647
MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT = 1_024
IDEMPOTENCY_RETENTION = timedelta(hours=24)
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
TIMEZONE_PATTERN = re.compile(r"^(?:UTC|[A-Za-z0-9._+-]+(?:/[A-Za-z0-9._+-]+)+)$")


def _boundary(*, profile_persisted: bool = False) -> dict[str, bool | str]:
    """Describe this bounded Web-only action without implying execution."""

    return {
        "execution": "web_native_workspace_setup_profile",
        "profile_persisted": profile_persisted,
        "bot_called": False,
        "bridge_called": False,
        "provider_called": False,
        "job_created": False,
        "wallet_mutated": False,
        "payment_started": False,
        "publish_action_created": False,
        "notification_sent": False,
    }


def _idempotency_key(value: str) -> str:
    normalized = str(value or "").strip()
    if not IDEMPOTENCY_PATTERN.fullmatch(normalized):
        raise ValueError("Idempotency key không hợp lệ")
    return normalized


def _idempotency_cutoff() -> str:
    """Return the bounded retention watermark for this module's receipts."""

    return (datetime.now(timezone.utc) - IDEMPOTENCY_RETENTION).isoformat(timespec="seconds")


def _guarded(message: str, error_code: str) -> dict[str, Any]:
    """Return a truthful no-write response for a bounded local safeguard."""

    return envelope(
        False,
        message,
        data={"boundary": _boundary(profile_persisted=False)},
        status_name="guarded",
        error_code=error_code,
    )


def _fingerprint(payload: dict[str, Any]) -> str:
    material = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _enum(value: str, allowed: frozenset[str], *, label: str, allow_empty: bool = False) -> str:
    normalized = str(value or "").strip()
    if not normalized and allow_empty:
        return ""
    if normalized not in allowed:
        raise ValueError(f"{label} không hợp lệ")
    return normalized


def _focus_areas(value: list[str]) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("Nhóm studio cần là một danh sách")
    if len(value) > MAX_FOCUS_AREAS:
        raise ValueError("Chỉ chọn tối đa 3 nhóm studio")
    normalized: list[str] = []
    for item in value:
        focus = _enum(item, FOCUS_AREAS, label="Nhóm studio")
        if focus in normalized:
            raise ValueError("Không được chọn trùng nhóm studio")
        normalized.append(focus)
    return normalized


def _safe_focus_areas(value: object) -> list[str]:
    try:
        decoded = json.loads(str(value or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(decoded, list):
        return []
    result: list[str] = []
    for item in decoded:
        if isinstance(item, str) and item in FOCUS_AREAS and item not in result:
            result.append(item)
    return result[:MAX_FOCUS_AREAS]


def _safe_profile(row: tuple[Any, ...] | None) -> dict[str, Any]:
    if not row:
        return {
            "setup_state": "not_started",
            "role": "",
            "goal": "",
            "experience": "",
            "focus_areas": [],
            "revision": 0,
            "completed_at": "",
            "updated_at": "",
        }
    state = str(row[0] or "")
    role = str(row[1] or "")
    goal = str(row[2] or "")
    experience = str(row[3] or "")
    try:
        revision = int(row[5] or 0)
    except (TypeError, ValueError):
        revision = 0
    return {
        "setup_state": state if state in SETUP_STATES else "not_started",
        "role": role if role in ROLES else "",
        "goal": goal if goal in GOALS else "",
        "experience": experience if experience in EXPERIENCE_LEVELS else "",
        "focus_areas": _safe_focus_areas(row[4]),
        "revision": max(0, min(MAX_REVISION, revision)),
        "completed_at": str(row[6] or ""),
        "updated_at": str(row[7] or ""),
    }


def _safe_preferences(account: dict[str, Any]) -> dict[str, str]:
    # The interface locale is a Web presentation setting.  It is not a
    # workflow/source/target language and must remain a closed projection.
    locale = str(account.get("locale") or DEFAULT_INTERFACE_LOCALE).strip().lower()
    timezone = str(account.get("timezone") or "Asia/Ho_Chi_Minh").strip()
    return {
        "locale": locale if locale in INTERFACE_LOCALES else DEFAULT_INTERFACE_LOCALE,
        "timezone": timezone if TIMEZONE_PATTERN.fullmatch(timezone) and len(timezone) <= 64 else "Asia/Ho_Chi_Minh",
    }


def _read_profile(account_id: str) -> dict[str, Any]:
    ensure_copyfast_schema()
    with read_transaction() as conn:
        row = conn.execute(
            """SELECT setup_state, role, goal, experience, focus_areas_json,
                      revision, completed_at, updated_at
               FROM web_workspace_setup_profiles WHERE account_id=?""",
            (account_id,),
        ).fetchone()
    return _safe_profile(row)


def _idempotent(
    scope: str,
    account_id: str,
    key: str,
    request_fingerprint: str,
    operation: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    """Run one profile mutation once; reject a reused key with new input."""

    ensure_copyfast_schema()
    with transaction() as conn:
        # Receipts are only for safely replaying a recently acknowledged
        # account mutation. Prune only this module's prefix and cap each
        # signed account so random unique keys cannot grow the SQLite volume
        # forever. Existing matching keys are still checked before the cap.
        conn.execute(
            "DELETE FROM web_idempotency WHERE scope LIKE ? AND created_at < ?",
            ("web-workspace-setup:%", _idempotency_cutoff()),
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
                raise HTTPException(status_code=409, detail="Bản ghi idempotency Workspace Setup không hợp lệ") from exc
            if isinstance(response, dict):
                return response
            raise HTTPException(status_code=409, detail="Bản ghi idempotency Workspace Setup không hợp lệ")
        count = conn.execute(
            "SELECT COUNT(*) FROM web_idempotency WHERE scope LIKE ?",
            (f"web-workspace-setup:{account_id}:%",),
        ).fetchone()
        if int(count[0] or 0) >= MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT:
            return _guarded(
                "Kho receipt thiết lập Workspace tạm thời đang đầy. Vui lòng thử lại sau.",
                "WEB_WORKSPACE_SETUP_IDEMPOTENCY_LIMIT",
            )
        response = operation(conn)
        if response.get("ok") is True:
            conn.execute(
                """INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (scope, key, json.dumps(response, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
            )
            return response
        return response


class WorkspaceSetupRequest(BaseModel):
    """Closed-vocabulary setup choices; browser never sends account identity."""

    model_config = ConfigDict(extra="forbid", strict=True)

    intent: str = Field(min_length=4, max_length=16)
    role: str = Field(default="", max_length=32)
    goal: str = Field(default="", max_length=32)
    experience: str = Field(default="", max_length=16)
    focus_areas: list[str] = Field(default_factory=list, max_length=MAX_FOCUS_AREAS)
    expected_revision: StrictInt = Field(ge=0, le=MAX_REVISION)
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("intent")
    @classmethod
    def validate_intent(cls, value: str) -> str:
        normalized = str(value or "").strip()
        if normalized not in {"complete", "skip"}:
            raise ValueError("Intent Workspace Setup không hợp lệ")
        return normalized

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        return _enum(value, ROLES, label="Vai trò", allow_empty=True)

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, value: str) -> str:
        return _enum(value, GOALS, label="Mục tiêu", allow_empty=True)

    @field_validator("experience")
    @classmethod
    def validate_experience(cls, value: str) -> str:
        return _enum(value, EXPERIENCE_LEVELS, label="Mức trải nghiệm", allow_empty=True)

    @field_validator("focus_areas")
    @classmethod
    def validate_focus_areas(cls, value: list[str]) -> list[str]:
        return _focus_areas(value)

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: str) -> str:
        return _idempotency_key(value)

    @model_validator(mode="after")
    def validate_intent_shape(self) -> "WorkspaceSetupRequest":
        if self.intent == "complete":
            if not self.role or not self.goal or not self.experience or not self.focus_areas:
                raise ValueError("Hoàn tất thiết lập cần vai trò, mục tiêu, mức trải nghiệm và ít nhất một nhóm studio")
        elif self.role or self.goal or self.experience or self.focus_areas:
            raise ValueError("Bỏ qua thiết lập không nhận lựa chọn dang dở")
        return self


@router.get("")
async def get_workspace_setup(request: Request, account: dict = Depends(require_account)) -> dict[str, Any]:
    """Read the signed account's Web-only setup profile."""

    profile = _read_profile(str(account["id"]))
    return envelope(
        True,
        "Đã tải thiết lập Workspace của tài khoản Web.",
        data={
            "profile": profile,
            "preferences": _safe_preferences(account),
            "boundary": _boundary(profile_persisted=profile["setup_state"] != "not_started"),
        },
        status_name="read_only",
    )


@router.post("")
async def save_workspace_setup(
    payload: WorkspaceSetupRequest,
    request: Request,
    account: dict = Depends(require_csrf),
) -> dict[str, Any]:
    """Complete or explicitly skip first-run setup under signed ownership."""

    account_id = str(account["id"])
    scope = f"web-workspace-setup:{account_id}:save"
    fingerprint = _fingerprint(
        {
            "intent": payload.intent,
            "role": payload.role,
            "goal": payload.goal,
            "experience": payload.experience,
            "focus_areas": payload.focus_areas,
            "expected_revision": payload.expected_revision,
        }
    )

    def operation(conn: Any) -> dict[str, Any]:
        current_row = conn.execute(
            """SELECT setup_state, role, goal, experience, focus_areas_json,
                      revision, completed_at, updated_at
               FROM web_workspace_setup_profiles WHERE account_id=?""",
            (account_id,),
        ).fetchone()
        current = _safe_profile(current_row)
        if current["revision"] != payload.expected_revision:
            raise HTTPException(status_code=409, detail="Thiết lập đã được thay đổi ở nơi khác. Hãy tải lại trước khi tiếp tục.")

        now = utc_now()
        completed = payload.intent == "complete"
        next_state = "completed" if completed else "skipped"
        next_role = payload.role if completed else ""
        next_goal = payload.goal if completed else ""
        next_experience = payload.experience if completed else ""
        next_focus = payload.focus_areas if completed else []
        next_revision = current["revision"] + 1
        completed_at = now if completed else ""
        if current_row is None:
            conn.execute(
                """INSERT INTO web_workspace_setup_profiles
                   (account_id, setup_state, role, goal, experience, focus_areas_json,
                    revision, completed_at, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    account_id,
                    next_state,
                    next_role,
                    next_goal,
                    next_experience,
                    json.dumps(next_focus, ensure_ascii=False, separators=(",", ":")),
                    next_revision,
                    completed_at or None,
                    now,
                    now,
                ),
            )
        else:
            cursor = conn.execute(
                """UPDATE web_workspace_setup_profiles
                   SET setup_state=?, role=?, goal=?, experience=?, focus_areas_json=?,
                       revision=?, completed_at=?, updated_at=?
                   WHERE account_id=? AND revision=?""",
                (
                    next_state,
                    next_role,
                    next_goal,
                    next_experience,
                    json.dumps(next_focus, ensure_ascii=False, separators=(",", ":")),
                    next_revision,
                    completed_at or None,
                    now,
                    account_id,
                    payload.expected_revision,
                ),
            )
            if cursor.rowcount != 1:
                raise HTTPException(status_code=409, detail="Thiết lập đã được thay đổi ở nơi khác. Hãy tải lại trước khi tiếp tục.")

        profile = {
            "setup_state": next_state,
            "role": next_role,
            "goal": next_goal,
            "experience": next_experience,
            "focus_areas": next_focus,
            "revision": next_revision,
            "completed_at": completed_at,
            "updated_at": now,
        }
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="web.workspace_setup.complete" if completed else "web.workspace_setup.skip",
            request_id=_request_id(request),
            target="workspace-setup",
            detail="web-owned workspace setup profile updated",
        )
        return envelope(
            True,
            "Đã hoàn tất thiết lập Workspace." if completed else "Đã bỏ qua thiết lập Workspace. Bạn có thể cập nhật sau.",
            data={
                "profile": profile,
                "preferences": _safe_preferences(account),
                "boundary": _boundary(profile_persisted=True),
            },
            status_name="completed" if completed else "skipped",
        )

    return _idempotent(scope, account_id, payload.idempotency_key, fingerprint, operation)
