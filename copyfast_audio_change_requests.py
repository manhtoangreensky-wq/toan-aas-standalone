"""Owner-scoped Audio Hub draft -> estimate -> confirm requests.

This module is deliberately a narrow Web-native layer over the verified local
``copyfast_audio_asset_operations`` executor.  A request begins only from an
active Audio Hub collection item that already references an owner-scoped Asset
Vault audio file.  It never accepts source bytes, paths, FFmpeg controls,
provider/Bot input, wallet/Xu, PayOS, price or payment data.

The existing direct ``/api/v1/audio-asset-operations`` routes remain intact
for their dedicated Audio Asset Operations surface.  This opt-in flow exists
only to give Audio Hub a durable, explicit confirmation boundary.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import re
from typing import Any, Callable
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, field_validator

import copyfast_audio_asset_operations as audio_operations
from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import (
    asset_vault_enabled,
    audio_change_requests_enabled,
    ensure_copyfast_schema,
    transaction,
    utc_now,
)


router = APIRouter(prefix="/api/v1/audio-change-requests", tags=["Web Audio Change Requests"])

UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
REQUEST_STATES = frozenset({"draft", "awaiting_confirm", "queued", "processing", "completed", "failed", "guarded", "unavailable"})
TERMINAL_OPERATION_STATES = frozenset({"completed", "failed", "guarded", "unavailable"})
IDEMPOTENCY_RETENTION = timedelta(hours=24)
MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT = 256
MAX_LIST_LIMIT = 50

OPERATION_SPECS = {
    "inspect": {
        "kind": audio_operations.AUDIO_INSPECT_KIND,
        "target_format": None,
        "normalization_profile": None,
    },
    "convert_mp3": {
        "kind": audio_operations.AUDIO_CONVERT_KIND,
        "target_format": "mp3",
        "normalization_profile": None,
    },
    "convert_m4a": {
        "kind": audio_operations.AUDIO_CONVERT_KIND,
        "target_format": "m4a",
        "normalization_profile": None,
    },
    "normalize": {
        "kind": audio_operations.AUDIO_NORMALIZE_KIND,
        "target_format": audio_operations.NORMALIZE_TARGET_FORMAT,
        "normalization_profile": audio_operations.NORMALIZE_PROFILE,
    },
}

REQUEST_COLUMNS = (
    "id, account_id, collection_id, media_item_id, source_asset_id, operation, target_format, normalization_profile, "
    "state, revision, collection_revision, source_sha256, source_byte_size, source_lifecycle_revision, source_format, "
    "operation_id, failure_code, created_at, estimated_at, confirmed_at, updated_at"
)


class AudioChangeRequestGuard(Exception):
    """A safe transition guard that never includes source-private details."""

    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.message = message
        self.code = code


class _RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AudioChangeDraftRequest(_RequestModel):
    collection_id: StrictStr = Field(min_length=36, max_length=36)
    item_id: StrictStr = Field(min_length=36, max_length=36)
    operation: StrictStr = Field(min_length=3, max_length=24)
    idempotency_key: StrictStr = Field(min_length=12, max_length=160)

    @field_validator("collection_id")
    @classmethod
    def validate_collection_id(cls, value: StrictStr) -> str:
        return _uuid(value, label="Collection ID")

    @field_validator("item_id")
    @classmethod
    def validate_item_id(cls, value: StrictStr) -> str:
        return _uuid(value, label="Audio reference ID")

    @field_validator("operation")
    @classmethod
    def validate_operation(cls, value: StrictStr) -> str:
        operation = str(value or "").strip().lower()
        if operation not in OPERATION_SPECS:
            raise ValueError("Loại thay đổi audio không hợp lệ")
        return operation

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: StrictStr) -> str:
        return _idempotency_key(value)


class AudioChangeEstimateRequest(_RequestModel):
    expected_revision: StrictInt = Field(ge=1, le=1_000_000)
    idempotency_key: StrictStr = Field(min_length=12, max_length=160)

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: StrictStr) -> str:
        return _idempotency_key(value)


class AudioChangeConfirmRequest(AudioChangeEstimateRequest):
    confirm: StrictBool

    @field_validator("confirm")
    @classmethod
    def validate_confirm(cls, value: StrictBool) -> bool:
        if value is not True:
            raise ValueError("Cần xác nhận rõ ràng trước khi chạy thay đổi audio")
        return True


def _uuid(value: str, *, label: str) -> str:
    candidate = str(value or "").strip()
    if not UUID_PATTERN.fullmatch(candidate):
        raise HTTPException(status_code=422, detail=f"{label} không hợp lệ")
    return str(uuid.UUID(candidate))


def _idempotency_key(value: str | None) -> str:
    key = str(value or "").strip()
    if not IDEMPOTENCY_PATTERN.fullmatch(key):
        raise HTTPException(status_code=422, detail="Idempotency key không hợp lệ")
    return key


def _require_feature() -> None:
    if not audio_change_requests_enabled():
        raise HTTPException(status_code=503, detail="Audio Change Request chưa được bật cho môi trường này")
    if not asset_vault_enabled():
        raise HTTPException(status_code=503, detail="Audio Change Request cần Asset Vault private đã được bật")


def _fingerprint(payload: dict[str, Any]) -> str:
    material = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _idempotency_cutoff() -> str:
    return (datetime.now(timezone.utc) - IDEMPOTENCY_RETENTION).isoformat()


def _receipt_from_row(row: Any, *, fingerprint: str) -> dict[str, Any] | None:
    if not row:
        return None
    if not hmac.compare_digest(str(row[1] or ""), fingerprint):
        raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho yêu cầu khác")
    try:
        response = json.loads(str(row[0] or ""))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=409, detail="Receipt Audio Change Request không hợp lệ") from exc
    if not isinstance(response, dict):
        raise HTTPException(status_code=409, detail="Receipt Audio Change Request không hợp lệ")
    return response


def _idempotency_scope(account_id: str, action: str, request_id: str | None = None) -> str:
    suffix = f":{request_id}" if request_id else ""
    return f"web-audio-change-request:{account_id}:{action}{suffix}"


def _idempotency_existing(conn: Any, *, scope: str, key: str, fingerprint: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT response_json, request_fingerprint FROM web_idempotency WHERE scope=? AND key=?",
        (scope, key),
    ).fetchone()
    return _receipt_from_row(row, fingerprint=fingerprint)


def _idempotency_has_capacity(conn: Any, *, account_id: str) -> bool:
    conn.execute(
        "DELETE FROM web_idempotency WHERE scope LIKE ? AND created_at < ?",
        (f"web-audio-change-request:{account_id}:%", _idempotency_cutoff()),
    )
    row = conn.execute(
        "SELECT COUNT(*) FROM web_idempotency WHERE scope LIKE ?",
        (f"web-audio-change-request:{account_id}:%",),
    ).fetchone()
    return int(row[0] or 0) < MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT if row else False


def _store_receipt(
    conn: Any,
    *,
    scope: str,
    account_id: str,
    key: str,
    fingerprint: str,
    response: dict[str, Any],
) -> dict[str, Any]:
    existing = _idempotency_existing(conn, scope=scope, key=key, fingerprint=fingerprint)
    if existing is not None:
        return existing
    if not _idempotency_has_capacity(conn, account_id=account_id):
        return envelope(
            False,
            "Kho receipt Audio Change Request đang đầy. Hãy thử lại sau.",
            status_name="guarded",
            error_code="WEB_AUDIO_CHANGE_REQUEST_IDEMPOTENCY_LIMIT",
        )
    try:
        serialized = json.dumps(response, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail="Không thể lưu receipt Audio Change Request an toàn") from exc
    conn.execute(
        """INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (scope, key, serialized, fingerprint, utc_now()),
    )
    return response


def _idempotent(
    *,
    scope: str,
    account_id: str,
    key: str,
    fingerprint: str,
    operation: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    ensure_copyfast_schema()
    with transaction() as conn:
        existing = _idempotency_existing(conn, scope=scope, key=key, fingerprint=fingerprint)
        if existing is not None:
            return existing
        if not _idempotency_has_capacity(conn, account_id=account_id):
            return envelope(
                False,
                "Kho receipt Audio Change Request đang đầy. Hãy thử lại sau.",
                status_name="guarded",
                error_code="WEB_AUDIO_CHANGE_REQUEST_IDEMPOTENCY_LIMIT",
            )
        response = operation(conn)
        if response.get("ok") is True:
            return _store_receipt(
                conn,
                scope=scope,
                account_id=account_id,
                key=key,
                fingerprint=fingerprint,
                response=response,
            )
        return response


def _request_from_row(row: Any) -> dict[str, Any]:
    values = dict(zip(REQUEST_COLUMNS.replace(" ", "").split(","), tuple(row), strict=True))
    values["revision"] = int(values["revision"] or 0)
    values["collection_revision"] = int(values["collection_revision"] or 0)
    values["source_byte_size"] = int(values["source_byte_size"] or 0)
    values["source_lifecycle_revision"] = int(values["source_lifecycle_revision"] or 0)
    return values


def _request_row(conn: Any, *, request_id: str, account_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        f"SELECT {REQUEST_COLUMNS} FROM web_audio_change_requests WHERE id=? AND account_id=?",
        (request_id, account_id),
    ).fetchone()
    return _request_from_row(row) if row else None


def _request_not_found() -> dict[str, Any]:
    return envelope(
        False,
        "Không tìm thấy Audio Change Request thuộc Web account hiện tại.",
        status_name="guarded",
        error_code="WEB_AUDIO_CHANGE_REQUEST_NOT_FOUND",
    )


def _source_guard(message: str = "Collection hoặc audio reference không còn sẵn sàng cho request này.") -> AudioChangeRequestGuard:
    return AudioChangeRequestGuard(message, "WEB_AUDIO_CHANGE_REQUEST_SOURCE_GUARDED")


def _current_attachment(
    conn: Any,
    *,
    account_id: str,
    collection_id: str,
    media_item_id: str,
) -> dict[str, Any]:
    row = conn.execute(
        """SELECT c.id, c.revision, c.state, i.id, i.asset_id
             FROM web_media_collections AS c
             JOIN web_media_items AS i
               ON i.collection_id=c.id AND i.account_id=c.account_id
            WHERE c.id=? AND c.account_id=? AND i.id=?""",
        (collection_id, account_id, media_item_id),
    ).fetchone()
    if not row:
        raise _source_guard()
    if str(row[2] or "") != "active":
        raise AudioChangeRequestGuard(
            "Collection đã archive. Hãy khôi phục và lập request mới trước khi tiếp tục.",
            "WEB_AUDIO_CHANGE_REQUEST_SOURCE_CHANGED",
        )
    source = audio_operations._owner_source(conn, account_id=account_id, source_asset_id=str(row[4] or ""))
    if source is None:
        raise _source_guard("Audio reference không còn là Asset Vault source hợp lệ của Web account hiện tại.")
    return {
        "collection_id": str(row[0]),
        "collection_revision": int(row[1] or 0),
        "media_item_id": str(row[3]),
        "source": source,
    }


def _snapshot_matches(record: dict[str, Any], current: dict[str, Any]) -> bool:
    source = current["source"]
    return (
        int(record["collection_revision"]) == int(current["collection_revision"])
        and str(record["source_asset_id"]) == str(source["asset_id"])
        and hmac.compare_digest(str(record["source_sha256"]), str(source["sha256"]))
        and int(record["source_byte_size"]) == int(source["byte_size"])
        and int(record["source_lifecycle_revision"]) == int(source["lifecycle_revision"])
        and str(record["source_format"]) == str(source["format"])
    )


def _assert_snapshot_current(conn: Any, *, record: dict[str, Any], account_id: str) -> dict[str, Any]:
    current = _current_attachment(
        conn,
        account_id=account_id,
        collection_id=str(record["collection_id"]),
        media_item_id=str(record["media_item_id"]),
    )
    if not _snapshot_matches(record, current):
        raise AudioChangeRequestGuard(
            "Collection hoặc audio source đã thay đổi. Hãy lập request mới trước khi tiếp tục.",
            "WEB_AUDIO_CHANGE_REQUEST_SOURCE_CHANGED",
        )
    return current


def _operation_plan(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "operation": str(record["operation"]),
        "target_format": str(record["target_format"]) if record["target_format"] else None,
        "normalization_profile": str(record["normalization_profile"]) if record["normalization_profile"] else None,
        "source_format": str(record["source_format"]),
        "source_byte_size": int(record["source_byte_size"]),
        "requires_confirmation": True,
        "execution": "private_web_native_audio_operation",
    }


def _linked_operation(conn: Any, *, record: dict[str, Any]) -> dict[str, Any] | None:
    operation_id = str(record.get("operation_id") or "")
    if not operation_id:
        return None
    row = conn.execute(
        f"SELECT {audio_operations.OPERATION_SELECT} FROM web_audio_asset_operations WHERE id=? AND account_id=?",
        (operation_id, str(record["account_id"])),
    ).fetchone()
    return audio_operations._operation_public_with_verified_output(tuple(row)) if row else None


def _effective_operation_state(operation: dict[str, Any] | None) -> str:
    if not operation:
        return "guarded"
    state = str(operation.get("state") or "guarded")
    kind = str(operation.get("kind") or "")
    if state == "completed" and kind in audio_operations.TRANSFORM_KINDS and operation.get("output_available") is not True:
        return "unavailable"
    return state if state in REQUEST_STATES else "guarded"


def _request_public(record: dict[str, Any], *, linked_operation: dict[str, Any] | None = None) -> dict[str, Any]:
    operation = linked_operation
    state = _effective_operation_state(operation) if operation else str(record["state"] or "guarded")
    if state not in REQUEST_STATES:
        state = "guarded"
    result: dict[str, Any] = {
        "id": str(record["id"]),
        "collection_id": str(record["collection_id"]),
        "media_item_id": str(record["media_item_id"]),
        "requested_operation": str(record["operation"]),
        "state": state,
        "status": state,
        "revision": int(record["revision"]),
        "collection_revision": int(record["collection_revision"]),
        "target_format": str(record["target_format"]) if record["target_format"] else None,
        "normalization_profile": str(record["normalization_profile"]) if record["normalization_profile"] else None,
        "requires_confirmation": state == "awaiting_confirm",
        "created_at": str(record["created_at"]),
        "estimated_at": str(record["estimated_at"]) if record["estimated_at"] else None,
        "confirmed_at": str(record["confirmed_at"]) if record["confirmed_at"] else None,
        "updated_at": str(record["updated_at"]),
    }
    if state == "awaiting_confirm":
        result["plan"] = _operation_plan(record)
    if operation is None:
        result["operation"] = str(record["operation"])
    else:
        result["operation"] = operation
    return result


def _request_envelope(record: dict[str, Any], *, linked_operation: dict[str, Any] | None = None) -> dict[str, Any]:
    public = _request_public(record, linked_operation=linked_operation)
    state = str(public["state"])
    if state == "draft":
        return envelope(True, "Đã lưu Audio Change Request. Hãy yêu cầu ước tính trước khi xác nhận.", data={"request": public}, status_name="draft")
    if state == "awaiting_confirm":
        return envelope(True, "Đã kiểm tra request. Hãy xem lại lựa chọn rồi xác nhận rõ ràng.", data={"request": public}, status_name="awaiting_confirm")
    if state == "completed":
        return envelope(True, "Audio Change Request đã hoàn tất với receipt private đã xác minh.", data={"request": public}, status_name="completed")
    if state in {"queued", "processing"}:
        return envelope(False, "Audio Change Request đang xử lý; chưa có output để dùng trước khi xác minh.", data={"request": public}, status_name=state, error_code="WEB_AUDIO_CHANGE_REQUEST_PENDING")
    if state == "unavailable":
        return envelope(False, "Output audio không còn qua kiểm tra integrity để dùng an toàn.", data={"request": public}, status_name="unavailable", error_code="WEB_AUDIO_CHANGE_REQUEST_OUTPUT_UNAVAILABLE")
    return envelope(False, "Audio Change Request đang được bảo vệ và chưa tạo output mới.", data={"request": public}, status_name=state, error_code="WEB_AUDIO_CHANGE_REQUEST_GUARDED")


def _mark_guarded(conn: Any, *, record: dict[str, Any], account: dict, request: Request, code: str) -> dict[str, Any]:
    now = utc_now()
    changed = conn.execute(
        """UPDATE web_audio_change_requests
               SET state='guarded', failure_code=?, revision=revision + 1, updated_at=?
             WHERE id=? AND account_id=? AND operation_id IS NULL AND state IN ('draft', 'awaiting_confirm')""",
        (code[:80], now, str(record["id"]), str(record["account_id"])),
    ).rowcount
    refreshed = _request_row(conn, request_id=str(record["id"]), account_id=str(record["account_id"])) or record
    if changed:
        _record_audit(
            conn,
            account_id=str(record["account_id"]),
            canonical_user_id=str(account.get("canonical_user_id") or ""),
            action="web.audio_change_request.guarded",
            request_id=_request_id(request),
            target=str(record["id"]),
            outcome="guarded",
            detail=f"code={code[:80]};collection=owner_scoped",
        )
    return refreshed


def _guarded_record_response(record: dict[str, Any], *, message: str, error_code: str) -> dict[str, Any]:
    return envelope(
        False,
        message,
        data={"request": _request_public(record)},
        status_name="guarded",
        error_code=error_code,
    )


@router.get("/drafts")
async def list_audio_change_requests(
    collection_id: str | None = Query(default=None, max_length=36),
    limit: int = Query(default=20, ge=1, le=MAX_LIST_LIMIT),
    account: dict = Depends(require_account),
):
    _require_feature()
    ensure_copyfast_schema()
    account_id = str(account["id"])
    selected_collection = _uuid(collection_id, label="Collection ID") if collection_id else None
    with transaction() as conn:
        if selected_collection:
            rows = conn.execute(
                f"""SELECT {REQUEST_COLUMNS} FROM web_audio_change_requests
                      WHERE account_id=? AND collection_id=? ORDER BY updated_at DESC, id DESC LIMIT ?""",
                (account_id, selected_collection, int(limit)),
            ).fetchall()
        else:
            rows = conn.execute(
                f"""SELECT {REQUEST_COLUMNS} FROM web_audio_change_requests
                      WHERE account_id=? ORDER BY updated_at DESC, id DESC LIMIT ?""",
                (account_id, int(limit)),
            ).fetchall()
        requests = []
        for row in rows:
            record = _request_from_row(row)
            requests.append(_request_public(record, linked_operation=_linked_operation(conn, record=record)))
    return envelope(
        True,
        "Đã tải Audio Change Request riêng tư của Web account hiện tại.",
        data={"requests": requests, "collection_id": selected_collection, "source": "web_native"},
        status_name="read_only",
    )


@router.get("/drafts/{request_id}")
async def get_audio_change_request(request_id: str, account: dict = Depends(require_account)):
    _require_feature()
    request_id = _uuid(request_id, label="Audio Change Request ID")
    ensure_copyfast_schema()
    with transaction() as conn:
        record = _request_row(conn, request_id=request_id, account_id=str(account["id"]))
        if not record:
            return _request_not_found()
        linked = _linked_operation(conn, record=record)
    return _request_envelope(record, linked_operation=linked)


@router.post("/drafts")
async def create_audio_change_request(payload: AudioChangeDraftRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_feature()
    account_id = str(account["id"])
    key = _idempotency_key(payload.idempotency_key)
    fingerprint = _fingerprint(
        {
            "collection_id": payload.collection_id,
            "item_id": payload.item_id,
            "operation": payload.operation,
        }
    )

    def operation(conn: Any) -> dict[str, Any]:
        try:
            current = _current_attachment(
                conn,
                account_id=account_id,
                collection_id=payload.collection_id,
                media_item_id=payload.item_id,
            )
        except AudioChangeRequestGuard as exc:
            return envelope(False, exc.message, status_name="guarded", error_code=exc.code)
        source = current["source"]
        spec = OPERATION_SPECS[payload.operation]
        request_id = str(uuid.uuid4())
        now = utc_now()
        conn.execute(
            """INSERT INTO web_audio_change_requests
               (id, account_id, collection_id, media_item_id, source_asset_id, operation, target_format,
                normalization_profile, state, revision, collection_revision, source_sha256, source_byte_size,
                source_lifecycle_revision, source_format, operation_id, failure_code, created_at, estimated_at,
                confirmed_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'draft', 1, ?, ?, ?, ?, ?, NULL, NULL, ?, NULL, NULL, ?)""",
            (
                request_id,
                account_id,
                payload.collection_id,
                payload.item_id,
                str(source["asset_id"]),
                payload.operation,
                spec["target_format"],
                spec["normalization_profile"],
                int(current["collection_revision"]),
                str(source["sha256"]),
                int(source["byte_size"]),
                int(source["lifecycle_revision"]),
                str(source["format"]),
                now,
                now,
            ),
        )
        record = _request_row(conn, request_id=request_id, account_id=account_id)
        if not record:
            raise RuntimeError("Không thể tạo Audio Change Request")
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=str(account.get("canonical_user_id") or ""),
            action="web.audio_change_request.draft",
            request_id=_request_id(request),
            target=request_id,
            detail=f"operation={payload.operation};collection=owner_scoped",
        )
        return _request_envelope(record)

    return _idempotent(
        scope=_idempotency_scope(account_id, "draft"),
        account_id=account_id,
        key=key,
        fingerprint=fingerprint,
        operation=operation,
    )


@router.post("/drafts/{request_id}/estimate")
async def estimate_audio_change_request(
    request_id: str,
    payload: AudioChangeEstimateRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    _require_feature()
    request_id = _uuid(request_id, label="Audio Change Request ID")
    account_id = str(account["id"])
    key = _idempotency_key(payload.idempotency_key)
    fingerprint = _fingerprint({"request_id": request_id, "revision": payload.expected_revision, "action": "estimate"})

    def operation(conn: Any) -> dict[str, Any]:
        record = _request_row(conn, request_id=request_id, account_id=account_id)
        if not record:
            return _request_not_found()
        if int(record["revision"]) != int(payload.expected_revision):
            return _guarded_record_response(record, message="Request đã thay đổi ở phiên khác. Hãy làm mới trước khi ước tính.", error_code="WEB_AUDIO_CHANGE_REQUEST_REVISION_CONFLICT")
        if str(record["state"]) != "draft" or record.get("operation_id"):
            return _guarded_record_response(record, message="Request hiện không ở trạng thái có thể ước tính lại.", error_code="WEB_AUDIO_CHANGE_REQUEST_ESTIMATE_GUARDED")
        try:
            _assert_snapshot_current(conn, record=record, account_id=account_id)
        except AudioChangeRequestGuard as exc:
            guarded = _mark_guarded(conn, record=record, account=account, request=request, code=exc.code)
            return _guarded_record_response(guarded, message=exc.message, error_code=exc.code)
        try:
            # This validates the server-owned flag, topology and trusted
            # binary locations only. It deliberately does not copy, probe or
            # render an audio file during an estimate.
            audio_operations._require_runtime()
        except HTTPException:
            return _guarded_record_response(record, message="Audio runtime chưa sẵn sàng để lập request xác nhận an toàn.", error_code="WEB_AUDIO_CHANGE_REQUEST_RUNTIME_GUARDED")
        now = utc_now()
        conn.execute(
            """UPDATE web_audio_change_requests
                   SET state='awaiting_confirm', revision=revision + 1, estimated_at=?, updated_at=?, failure_code=NULL
                 WHERE id=? AND account_id=? AND state='draft' AND revision=?""",
            (now, now, request_id, account_id, payload.expected_revision),
        )
        updated = _request_row(conn, request_id=request_id, account_id=account_id)
        if not updated or str(updated["state"]) != "awaiting_confirm":
            return _guarded_record_response(record, message="Request đã thay đổi trước khi hoàn tất ước tính. Hãy làm mới.", error_code="WEB_AUDIO_CHANGE_REQUEST_REVISION_CONFLICT")
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=str(account.get("canonical_user_id") or ""),
            action="web.audio_change_request.estimate",
            request_id=_request_id(request),
            target=request_id,
            detail=f"operation={updated['operation']};execution=not_started",
        )
        return _request_envelope(updated)

    return _idempotent(
        scope=_idempotency_scope(account_id, "estimate", request_id),
        account_id=account_id,
        key=key,
        fingerprint=fingerprint,
        operation=operation,
    )


@router.post("/drafts/{request_id}/confirm")
async def confirm_audio_change_request(
    request_id: str,
    payload: AudioChangeConfirmRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    _require_feature()
    request_id = _uuid(request_id, label="Audio Change Request ID")
    account_id = str(account["id"])
    key = _idempotency_key(payload.idempotency_key)
    fingerprint = _fingerprint({"request_id": request_id, "revision": payload.expected_revision, "confirm": True})
    scope = _idempotency_scope(account_id, "confirm", request_id)
    ensure_copyfast_schema()

    with transaction() as conn:
        existing = _idempotency_existing(conn, scope=scope, key=key, fingerprint=fingerprint)
        if existing is not None:
            return existing
        if not _idempotency_has_capacity(conn, account_id=account_id):
            return envelope(False, "Kho receipt Audio Change Request đang đầy. Hãy thử lại sau.", status_name="guarded", error_code="WEB_AUDIO_CHANGE_REQUEST_IDEMPOTENCY_LIMIT")
        record = _request_row(conn, request_id=request_id, account_id=account_id)
        if not record:
            return _request_not_found()
        if int(record["revision"]) != int(payload.expected_revision):
            return _guarded_record_response(record, message="Request đã thay đổi ở phiên khác. Hãy làm mới trước khi xác nhận.", error_code="WEB_AUDIO_CHANGE_REQUEST_REVISION_CONFLICT")
        if record.get("operation_id"):
            return _guarded_record_response(record, message="Request này đã liên kết một thao tác audio; hãy làm mới trạng thái thay vì xác nhận lại.", error_code="WEB_AUDIO_CHANGE_REQUEST_ALREADY_CONFIRMED")
        if str(record["state"]) != "awaiting_confirm":
            return _guarded_record_response(record, message="Hãy lập ước tính mới trước khi xác nhận thay đổi audio.", error_code="WEB_AUDIO_CHANGE_REQUEST_CONFIRM_GUARDED")
        try:
            _assert_snapshot_current(conn, record=record, account_id=account_id)
        except AudioChangeRequestGuard as exc:
            guarded = _mark_guarded(conn, record=record, account=account, request=request, code=exc.code)
            return _guarded_record_response(guarded, message=exc.message, error_code=exc.code)

    def reservation_precondition(conn: Any, source: dict[str, Any]) -> None:
        current_record = _request_row(conn, request_id=request_id, account_id=account_id)
        if not current_record or str(current_record["state"]) != "awaiting_confirm" or int(current_record["revision"]) != int(payload.expected_revision):
            raise AudioChangeRequestGuard(
                "Request đã thay đổi trước khi có thể tạo thao tác audio. Hãy làm mới.",
                "WEB_AUDIO_CHANGE_REQUEST_REVISION_CONFLICT",
            )
        current = _assert_snapshot_current(conn, record=current_record, account_id=account_id)
        expected = current["source"]
        if (
            str(source.get("asset_id") or "") != str(expected["asset_id"])
            or not hmac.compare_digest(str(source.get("sha256") or ""), str(expected["sha256"]))
            or int(source.get("byte_size") or 0) != int(expected["byte_size"])
            or int(source.get("lifecycle_revision") or 0) != int(expected["lifecycle_revision"])
            or str(source.get("format") or "") != str(expected["format"])
        ):
            raise AudioChangeRequestGuard(
                "Audio source đã thay đổi trước khi tạo thao tác. Hãy lập request mới.",
                "WEB_AUDIO_CHANGE_REQUEST_SOURCE_CHANGED",
            )

    spec = OPERATION_SPECS[str(record["operation"])]
    try:
        raw = await audio_operations.execute_audio_asset_operation(
            kind=str(spec["kind"]),
            target_format=spec["target_format"],
            normalization_profile=spec["normalization_profile"],
            source_asset_id=str(record["source_asset_id"]),
            idempotency_key=f"audio-change-operation:{request_id}",
            request=request,
            account=account,
            reservation_precondition=reservation_precondition,
        )
    except AudioChangeRequestGuard as exc:
        with transaction() as conn:
            current = _request_row(conn, request_id=request_id, account_id=account_id)
            guarded = _mark_guarded(conn, record=current or record, account=account, request=request, code=exc.code)
        return _guarded_record_response(guarded, message=exc.message, error_code=exc.code)

    data = raw.get("data") if isinstance(raw, dict) and isinstance(raw.get("data"), dict) else {}
    operation = data.get("operation") if isinstance(data, dict) and isinstance(data.get("operation"), dict) else None
    operation_id = str(operation.get("id") or "") if operation else ""
    if not UUID_PATTERN.fullmatch(operation_id):
        with transaction() as conn:
            current = _request_row(conn, request_id=request_id, account_id=account_id)
            guarded = _mark_guarded(conn, record=current or record, account=account, request=request, code="WEB_AUDIO_CHANGE_REQUEST_EXECUTOR_GUARDED")
        return _guarded_record_response(guarded, message="Không thể liên kết receipt Audio Asset Operation an toàn.", error_code="WEB_AUDIO_CHANGE_REQUEST_EXECUTOR_GUARDED")

    with transaction() as conn:
        current = _request_row(conn, request_id=request_id, account_id=account_id)
        if not current:
            return _request_not_found()
        existing_operation_id = str(current.get("operation_id") or "")
        if existing_operation_id and existing_operation_id != operation_id:
            return _guarded_record_response(current, message="Request đã có liên kết thao tác khác và đang được bảo vệ.", error_code="WEB_AUDIO_CHANGE_REQUEST_ALREADY_CONFIRMED")
        if not existing_operation_id:
            state = _effective_operation_state(operation)
            now = utc_now()
            conn.execute(
                """UPDATE web_audio_change_requests
                       SET operation_id=?, state=?, confirmed_at=?, updated_at=?, revision=revision + 1, failure_code=NULL
                     WHERE id=? AND account_id=? AND operation_id IS NULL""",
                (operation_id, state, now, now, request_id, account_id),
            )
            _record_audit(
                conn,
                account_id=account_id,
                canonical_user_id=str(account.get("canonical_user_id") or ""),
                action="web.audio_change_request.confirm",
                request_id=_request_id(request),
                target=request_id,
                outcome=state,
                detail=f"operation=linked;state={state}",
            )
        current = _request_row(conn, request_id=request_id, account_id=account_id) or current
        linked = _linked_operation(conn, record=current)
        response = _request_envelope(current, linked_operation=linked)
        return _store_receipt(
            conn,
            scope=scope,
            account_id=account_id,
            key=key,
            fingerprint=fingerprint,
            response=response,
        )
