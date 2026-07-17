"""Bounded, Web-native Content Handoff records.

This module is a private coordination ledger for a signed Web account.  A
record can reference only opaque IDs for Web-owned Projects, Asset Vault files
and Campaign Plans after the server verifies ownership.  It deliberately does
not know an external recipient, social credential, URL, publishing destination
or provider handle.

``handed_off`` therefore has a narrow, truthful meaning: an authorised Web
Customer Care manager has recorded an internal human handoff.  It is never
evidence of a social post, external delivery, notification, Bot action,
provider result, payment, wallet mutation or job completion.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
import re
import uuid
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, field_validator, model_validator

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction, utc_now
from copyfast_native_read_models import (
    parse_native_asset_id,
    parse_native_job_id,
    resolve_native_asset,
    resolve_native_job,
)
from copyfast_support import require_support_staff


router = APIRouter(prefix="/api/v1/content-handoffs", tags=["Web Content Handoff"])


HANDOFF_STATUSES = frozenset({"draft", "review", "approved_for_handoff", "handed_off", "blocked"})
RECORD_STATES = frozenset({"active", "archived"})
STAFF_DECISIONS = frozenset({"approved_for_handoff", "handed_off", "blocked"})
MAX_ACTIVE_RECORDS_PER_ACCOUNT = 250
MAX_ASSETS_PER_RECORD = 12
MAX_NATIVE_REFS_PER_RECORD = 12
MAX_LIST_LIMIT = 100
MAX_LIST_OFFSET = 10_000
MAX_VERSIONS_PER_RECORD = 100
MAX_EVENTS_PER_RECORD = 100
MAX_IDEMPOTENCY_RECORDS_PER_ACTOR = 1_024
IDEMPOTENCY_RETENTION = timedelta(hours=24)
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
UNSAFE_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
MARKUP_PATTERN = re.compile(r"(?:<\s*/?\s*[A-Za-z][^>\r\n]{0,240}>|```|\bon[a-z]+\s*=)", re.IGNORECASE)
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|client[ _-]?secret|"
    r"password|passphrase|authorization|private[ _-]?key)\b\s*(?:['\"]\s*)?(?:[:=]|\bis\b)\s*(?:['\"]\s*)?"
    r"(?:bearer\s+)?[A-Za-z0-9_./+=:-]{8,}",
    re.IGNORECASE,
)
KNOWN_SECRET_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(?:(?:sk|pk|rk)[_-][A-Za-z0-9_-]{12,}|gh(?:p|o|u|s|r)_[A-Za-z0-9]{12,}|"
    r"github_pat_[A-Za-z0-9_]{12,}|xox(?:b|p|a|r|s)-[A-Za-z0-9-]{12,}|AIza[0-9A-Za-z_-]{20}|"
    r"(?:AKIA|ASIA)[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8})(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
PAYMENT_PATTERN = re.compile(
    r"\b(?:txid|transaction\s+(?:hash|id|reference)|mã\s*(?:giao\s*)?(?:dịch|thanh\s*toán)|"
    r"bill|biên\s*lai|chứng\s*từ|số\s*tài\s*khoản|stk|qr\s*(?:code|thanh\s*toán)|"
    r"nạp\s*(?:tiền|xu)|chuyển\s*khoản|manual\s*topup)\b",
    re.IGNORECASE,
)
EXTERNAL_TARGET_PATTERN = re.compile(
    r"(?:\bhttps?://|\bwww\.|\b(?:mailto|tel|tg|telegram|discord|slack):|(?:^|\s)@[A-Za-z0-9_]{3,}|"
    r"\b(?:channel|account|profile|page|handle|recipient|destination|webhook|callback)[ _-]*(?:id|url|token|handle)\b)",
    re.IGNORECASE,
)
CARD_LIKE_PATTERN = re.compile(r"(?<![0-9A-Za-z])[0-9](?:[\s./-]*[0-9]){12,18}(?![0-9A-Za-z])")
NATIVE_REF_TYPES = frozenset({"native_output", "native_asset"})


def content_handoff_enabled() -> bool:
    """Keep this standalone coordination surface deliberately switchable."""

    return os.environ.get("WEBAPP_CONTENT_HANDOFF_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def _require_enabled() -> None:
    if not content_handoff_enabled():
        raise HTTPException(
            status_code=503,
            detail="Content Handoff đang tạm dừng để bảo trì. WEBAPP_CONTENT_HANDOFF_ENABLED chưa được bật.",
        )


def _boundary(**extra: Any) -> dict[str, Any]:
    """State the non-execution contract in every response.

    Keeping these properties in the envelope prevents a UI from inferring a
    delivery/publish result from a normal database state transition.
    """

    return {
        "execution": "web_native_internal_handoff_record_only",
        "data_origin": "signed_account_web_owned_opaque_references",
        "external_recipient_configured": False,
        "external_url_or_handle_stored": False,
        "bot_called": False,
        "provider_called": False,
        "social_oauth_connected": False,
        "social_api_called": False,
        "publish_action_created": False,
        "external_notification_sent": False,
        "job_created": False,
        "wallet_mutated": False,
        "payment_started": False,
        "payment_processed": False,
        "external_delivery_verified": False,
        "manual_handoff_semantics": "handed_off only records an authorised internal human handoff; it is not external delivery or publication evidence.",
        **extra,
    }


def _guarded(message: str, code: str, **extra: Any) -> dict[str, Any]:
    return envelope(False, message, data=_boundary(record_persisted=False, **extra), status_name="guarded", error_code=code)


def _uuid(value: Any, *, label: str, http: bool = False) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        if http:
            raise HTTPException(status_code=422, detail=f"{label} không hợp lệ") from exc
        raise ValueError(f"{label} không hợp lệ") from exc


def _idempotency_key(value: Any) -> str:
    key = str(value or "").strip()
    if not IDEMPOTENCY_PATTERN.fullmatch(key):
        raise ValueError("Idempotency key không hợp lệ")
    return key


def _sensitive_or_external(value: str) -> bool:
    return bool(
        MARKUP_PATTERN.search(value)
        or SECRET_ASSIGNMENT_PATTERN.search(value)
        or KNOWN_SECRET_PATTERN.search(value)
        or PAYMENT_PATTERN.search(value)
        or EXTERNAL_TARGET_PATTERN.search(value)
        or CARD_LIKE_PATTERN.search(value)
        or "-----begin" in value.lower()
    )


def _text(value: Any, *, label: str, minimum: int, maximum: int, allow_empty: bool = False, multiline: bool = False) -> str:
    raw = str(value or "")
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n").strip() if multiline else re.sub(r"\s+", " ", raw).strip()
    if UNSAFE_CONTROL_PATTERN.search(normalized) or len(normalized) > maximum or (not allow_empty and len(normalized) < minimum):
        if allow_empty:
            raise ValueError(f"{label} tối đa {maximum:,} ký tự hợp lệ".replace(",", "."))
        raise ValueError(f"{label} cần từ {minimum} đến {maximum:,} ký tự hợp lệ".replace(",", "."))
    if normalized and _sensitive_or_external(normalized):
        raise ValueError(f"{label} không nhận URL/handle bên ngoài, markup, secret hoặc chứng từ thanh toán")
    return normalized


def _status(value: Any) -> str:
    result = _text(value, label="Trạng thái handoff", minimum=2, maximum=32).lower()
    if result not in HANDOFF_STATUSES:
        raise ValueError("Trạng thái handoff không hợp lệ")
    return result


def _fingerprint(payload: dict[str, Any]) -> str:
    material = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _content_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _ensure_schema() -> None:
    """Create only additive tables owned by this module.

    ``copyfast_db`` remains the shared schema authority.  These tables are
    intentionally module-local because this bounded feature is added without
    changing that shared migration file.
    """

    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_content_handoff_records (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                title TEXT NOT NULL,
                purpose TEXT NOT NULL,
                references_json TEXT NOT NULL,
                handoff_status TEXT NOT NULL DEFAULT 'draft',
                record_state TEXT NOT NULL DEFAULT 'active',
                staff_note TEXT NOT NULL DEFAULT '',
                reviewer_account_id TEXT,
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                reviewed_at TEXT,
                handed_off_at TEXT,
                archived_at TEXT,
                CHECK(handoff_status IN ('draft','review','approved_for_handoff','handed_off','blocked')),
                CHECK(record_state IN ('active','archived')),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(reviewer_account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_content_handoff_versions (
                id TEXT PRIMARY KEY,
                record_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(record_id, revision),
                FOREIGN KEY(record_id) REFERENCES web_content_handoff_records(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_content_handoff_events (
                id TEXT PRIMARY KEY,
                record_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                actor_account_id TEXT,
                actor_kind TEXT NOT NULL,
                action TEXT NOT NULL,
                from_status TEXT,
                to_status TEXT,
                revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(record_id) REFERENCES web_content_handoff_records(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id),
                FOREIGN KEY(actor_account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_content_handoff_records_account_state_updated "
            "ON web_content_handoff_records(account_id, record_state, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_content_handoff_records_staff_queue "
            "ON web_content_handoff_records(record_state, handoff_status, updated_at ASC, id ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_content_handoff_versions_record_revision "
            "ON web_content_handoff_versions(record_id, account_id, revision DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_content_handoff_events_record_created "
            "ON web_content_handoff_events(record_id, account_id, created_at DESC, id DESC)"
        )


class HandoffNativeReference(BaseModel):
    """A typed opaque link to one Web-native job output or Asset Vault row."""

    model_config = ConfigDict(extra="forbid", strict=True)

    ref_type: StrictStr
    ref_id: StrictStr

    @field_validator("ref_type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        normalized = _text(value, label="Loại native reference", minimum=2, maximum=32).lower()
        if normalized not in NATIVE_REF_TYPES:
            raise ValueError("Loại native reference Content Handoff không được hỗ trợ")
        return normalized

    @model_validator(mode="after")
    def validate_opaque_id(self):
        if self.ref_type == "native_output" and parse_native_job_id(self.ref_id) is None:
            raise ValueError("Native output ID không hợp lệ")
        if self.ref_type == "native_asset" and parse_native_asset_id(self.ref_id) is None:
            raise ValueError("Native asset ID không hợp lệ")
        return self


class HandoffReferences(BaseModel):
    """Only opaque IDs are accepted; labels and external destinations are not."""

    model_config = ConfigDict(extra="forbid", strict=True)

    project_id: StrictStr | None = None
    asset_ids: list[StrictStr] = Field(default_factory=list)
    campaign_id: StrictStr | None = None
    native_refs: list[HandoffNativeReference] = Field(default_factory=list)

    @field_validator("project_id", "campaign_id")
    @classmethod
    def validate_optional_id(cls, value: str | None, info) -> str | None:
        if value is None:
            return None
        return _uuid(value, label="Project ID" if info.field_name == "project_id" else "Campaign ID")

    @field_validator("asset_ids")
    @classmethod
    def validate_assets(cls, value: list[str]) -> list[str]:
        if len(value) > MAX_ASSETS_PER_RECORD:
            raise ValueError(f"Tối đa {MAX_ASSETS_PER_RECORD} Asset IDs cho một handoff")
        result: list[str] = []
        seen: set[str] = set()
        for candidate in value:
            asset_id = _uuid(candidate, label="Asset ID")
            if asset_id not in seen:
                seen.add(asset_id)
                result.append(asset_id)
        return result

    @field_validator("native_refs")
    @classmethod
    def validate_native_refs(cls, value: list[HandoffNativeReference]) -> list[HandoffNativeReference]:
        if len(value) > MAX_NATIVE_REFS_PER_RECORD:
            raise ValueError(f"Tối đa {MAX_NATIVE_REFS_PER_RECORD} native reference cho một handoff")
        result: list[HandoffNativeReference] = []
        seen: set[tuple[str, str]] = set()
        for reference in value:
            marker = (reference.ref_type, reference.ref_id)
            if marker in seen:
                raise ValueError("Native reference Content Handoff bị lặp")
            seen.add(marker)
            result.append(reference)
        return result

    @model_validator(mode="after")
    def require_reference(self):
        if not self.project_id and not self.asset_ids and not self.campaign_id and not self.native_refs:
            raise ValueError("Content Handoff cần ít nhất một Project, Asset, Campaign hoặc output Web-native")
        return self


class HandoffRecordPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    title: StrictStr
    purpose: StrictStr
    references: HandoffReferences
    idempotency_key: StrictStr

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _text(value, label="Tiêu đề handoff", minimum=3, maximum=180)

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, value: str) -> str:
        return _text(value, label="Mục đích handoff", minimum=8, maximum=2_500, multiline=True)

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)


class HandoffRecordUpdateRequest(HandoffRecordPayload):
    expected_revision: StrictInt = Field(ge=1)


class RevisionMutationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    expected_revision: StrictInt = Field(ge=1)
    confirm: StrictBool
    idempotency_key: StrictStr

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)


class StaffReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    decision: StrictStr
    review_note: StrictStr = ""
    expected_revision: StrictInt = Field(ge=1)
    confirm: StrictBool
    confirm_manual_handoff: StrictBool = False
    idempotency_key: StrictStr

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, value: str) -> str:
        result = _text(value, label="Quyết định handoff", minimum=2, maximum=32).lower()
        if result not in STAFF_DECISIONS:
            raise ValueError("Quyết định review không hợp lệ")
        return result

    @field_validator("review_note")
    @classmethod
    def validate_note(cls, value: str) -> str:
        return _text(value, label="Ghi chú review", minimum=0, maximum=1_200, allow_empty=True, multiline=True)

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)

    @model_validator(mode="after")
    def require_safe_confirmation(self):
        if self.decision == "handed_off" and not self.confirm_manual_handoff:
            raise ValueError("Cần xác nhận đây chỉ là ghi nhận bàn giao nội bộ thủ công")
        if self.decision in {"blocked", "handed_off"} and len(self.review_note) < 8:
            raise ValueError("Cần ghi chú review tối thiểu 8 ký tự cho quyết định này")
        return self


def _references_payload(references: HandoffReferences | dict[str, Any]) -> dict[str, Any]:
    if isinstance(references, HandoffReferences):
        source = references.model_dump()
    else:
        source = dict(references)
    native_refs: list[dict[str, str]] = []
    for value in source.get("native_refs", []) or []:
        reference = value if isinstance(value, HandoffNativeReference) else HandoffNativeReference.model_validate(value)
        native_refs.append({"ref_type": reference.ref_type, "ref_id": reference.ref_id})
    return {
        "project_id": str(source["project_id"]) if source.get("project_id") else None,
        "asset_ids": [str(item) for item in source.get("asset_ids", [])],
        "campaign_id": str(source["campaign_id"]) if source.get("campaign_id") else None,
        "native_refs": native_refs,
    }


def _decode_references(value: Any) -> dict[str, Any]:
    try:
        parsed = json.loads(str(value or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {"project_id": None, "asset_ids": [], "campaign_id": None, "native_refs": []}
    if not isinstance(parsed, dict):
        return {"project_id": None, "asset_ids": [], "campaign_id": None, "native_refs": []}
    try:
        return _references_payload(HandoffReferences.model_validate(parsed))
    except Exception:
        # Corrupt historical data must never become an external reference or
        # crash a customer's private list.  Existing rows remain visible only
        # as a guarded record until an operator investigates the database.
        return {"project_id": None, "asset_ids": [], "campaign_id": None, "native_refs": []}


def _record_row(conn: Any, *, record_id: str, account_id: str | None = None) -> tuple[Any, ...] | None:
    clauses = ["id=?"]
    params: list[Any] = [record_id]
    if account_id is not None:
        clauses.append("account_id=?")
        params.append(account_id)
    row = conn.execute(
        f"""SELECT id, account_id, title, purpose, references_json, handoff_status, record_state, staff_note,
                   reviewer_account_id, revision, created_at, updated_at, reviewed_at, handed_off_at, archived_at
              FROM web_content_handoff_records
              WHERE {' AND '.join(clauses)}""",
        tuple(params),
    ).fetchone()
    return tuple(row) if row else None


def _record_public(row: tuple[Any, ...], *, include_detail: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": str(row[0]),
        "references": _decode_references(row[4]),
        "handoff_status": str(row[5]),
        "record_state": str(row[6]),
        "revision": int(row[9]),
        "created_at": str(row[10]),
        "updated_at": str(row[11]),
        "reviewed_at": str(row[12]) if row[12] else None,
        "handed_off_at": str(row[13]) if row[13] else None,
        "archived_at": str(row[14]) if row[14] else None,
    }
    if include_detail:
        result.update({"title": str(row[2]), "purpose": str(row[3]), "staff_note": str(row[7] or "")})
    else:
        result["title"] = str(row[2])
    return result


def _snapshot(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "title": str(row[2]),
        "purpose": str(row[3]),
        "references": _decode_references(row[4]),
        "handoff_status": str(row[5]),
        "record_state": str(row[6]),
        "staff_note": str(row[7] or ""),
    }


def _insert_version(conn: Any, *, row: tuple[Any, ...]) -> None:
    conn.execute(
        """INSERT INTO web_content_handoff_versions
           (id, record_id, account_id, revision, snapshot_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            str(uuid.uuid4()),
            str(row[0]),
            str(row[1]),
            int(row[9]),
            json.dumps(_snapshot(row), ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            utc_now(),
        ),
    )


def _can_add_version(conn: Any, *, record_id: str, account_id: str) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) FROM web_content_handoff_versions WHERE record_id=? AND account_id=?",
        (record_id, account_id),
    ).fetchone()
    return int(row[0] or 0) < MAX_VERSIONS_PER_RECORD


def _event(
    conn: Any,
    *,
    record_id: str,
    account_id: str,
    actor_account_id: str | None,
    actor_kind: str,
    action: str,
    from_status: str | None,
    to_status: str | None,
    revision: int,
) -> None:
    conn.execute(
        """INSERT INTO web_content_handoff_events
           (id, record_id, account_id, actor_account_id, actor_kind, action, from_status, to_status, revision, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            str(uuid.uuid4()), record_id, account_id, actor_account_id, actor_kind, action,
            from_status, to_status, revision, utc_now(),
        ),
    )


def _audit(conn: Any, *, request: Request, account: dict, action: str, target: str, detail: str) -> None:
    _record_audit(
        conn,
        account_id=str(account["id"]),
        canonical_user_id=None,
        action=action,
        request_id=_request_id(request),
        target=target,
        outcome="ok",
        detail=detail[:320],
    )


def _not_found() -> dict[str, Any]:
    return _guarded("Không tìm thấy Content Handoff thuộc phạm vi quyền hiện tại.", "WEB_CONTENT_HANDOFF_NOT_FOUND")


def _revision_conflict(current_revision: int) -> dict[str, Any]:
    return _guarded(
        "Content Handoff đã có revision mới. Hãy tải lại trước khi tiếp tục.",
        "WEB_CONTENT_HANDOFF_REVISION_CONFLICT",
        current_revision=current_revision,
    )


def _record_archived() -> dict[str, Any]:
    return _guarded("Content Handoff đã archive. Hãy restore trước khi tiếp tục workflow.", "WEB_CONTENT_HANDOFF_ARCHIVED")


def _references_owned(conn: Any, *, account_id: str, references: dict[str, Any]) -> bool:
    """Verify every opaque ID inside the same write transaction.

    The ledger saves IDs only, not titles, file paths, URLs, provider handles
    or campaign destinations.  A single missing or foreign ID fails as one
    generic validation result so an account cannot enumerate another account's
    records.
    """

    project_id = references.get("project_id")
    if project_id:
        project = conn.execute(
            "SELECT id FROM web_projects WHERE id=? AND account_id=? AND state='active'",
            (project_id, account_id),
        ).fetchone()
        if not project:
            return False
    campaign_id = references.get("campaign_id")
    if campaign_id:
        campaign = conn.execute(
            "SELECT id FROM web_campaign_plans WHERE id=? AND account_id=?",
            (campaign_id, account_id),
        ).fetchone()
        if not campaign:
            return False
    asset_ids = list(references.get("asset_ids") or [])
    if asset_ids:
        placeholders = ",".join("?" for _ in asset_ids)
        rows = conn.execute(
            f"SELECT id FROM web_asset_files WHERE account_id=? AND state='active' AND id IN ({placeholders})",
            (account_id, *asset_ids),
        ).fetchall()
        if len({str(row[0]) for row in rows}) != len(asset_ids):
            return False
    for raw_reference in references.get("native_refs", []) or []:
        try:
            reference = HandoffNativeReference.model_validate(raw_reference)
        except Exception:
            return False
        if reference.ref_type == "native_output":
            job = resolve_native_job(conn, account_id, reference.ref_id)
            # ``output`` is created only by the read model after all direct
            # downloader integrity rules pass. A completed DB state alone is
            # never enough to treat an output as safe for handoff lineage.
            if not job or str(job.get("state") or "") != "completed" or not isinstance(job.get("output"), dict):
                return False
        elif reference.ref_type == "native_asset":
            asset = resolve_native_asset(conn, account_id, reference.ref_id)
            if not asset or str(asset.get("state") or "") != "active":
                return False
        else:  # Defensive even though the Pydantic model is closed.
            return False
    return True


_SAFE_LINEAGE_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,180}$")
_SAFE_LINEAGE_MEDIA_TYPE = re.compile(
    r"^[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+(?:; charset=(?:utf-8|us-ascii))?$"
)
_SAFE_LINEAGE_STATES = frozenset({"draft", "queued", "processing", "completed", "failed", "guarded", "active", "archived"})


def _safe_lineage_output(value: Any) -> dict[str, Any] | None:
    """Select delivery-neutral metadata from an already sealed output dict."""

    if not isinstance(value, dict):
        return None
    filename = str(value.get("filename") or "")
    content_type = str(value.get("content_type") or "")
    byte_size = value.get("byte_size")
    if (
        not _SAFE_LINEAGE_FILENAME.fullmatch(filename)
        or not _SAFE_LINEAGE_MEDIA_TYPE.fullmatch(content_type)
        or isinstance(byte_size, bool)
        or not isinstance(byte_size, int)
        or byte_size <= 0
    ):
        return None
    return {"filename": filename, "content_type": content_type, "byte_size": byte_size}


def _lineage_reference(conn: Any, *, account_id: str, reference: dict[str, str]) -> dict[str, Any]:
    """Return a private, stable status view without reviving invalid output.

    The stored reference is immutable history. If its source later disappears,
    is archived, or loses its sealed-output contract, the lineage remains
    visible as unavailable instead of being turned into a delivery claim.
    """

    ref_type = str(reference["ref_type"])
    ref_id = str(reference["ref_id"])
    if ref_type == "native_output":
        job = resolve_native_job(conn, account_id, ref_id)
        raw_state = str(job.get("state") or "") if job else ""
        state = raw_state if raw_state in _SAFE_LINEAGE_STATES else "unavailable"
        output = _safe_lineage_output(job.get("output")) if job and raw_state == "completed" else None
        available = raw_state == "completed" and output is not None
        return {
            "ref_type": ref_type,
            "ref_id": ref_id,
            "state": state,
            "status": "completed" if available else "unavailable",
            "availability": "available" if available else "unavailable",
            "output": output,
        }
    asset = resolve_native_asset(conn, account_id, ref_id)
    raw_state = str(asset.get("state") or "") if asset else ""
    state = raw_state if raw_state in _SAFE_LINEAGE_STATES else "unavailable"
    available = raw_state == "active"
    return {
        "ref_type": ref_type,
        "ref_id": ref_id,
        "state": state,
        "status": "active" if available else "unavailable",
        "availability": "available" if available else "unavailable",
        "output": None,
    }


def _safe_receipt(response: dict[str, Any]) -> dict[str, Any]:
    """Idempotency receipts deliberately omit purpose, notes and references."""

    if not isinstance(response, dict) or response.get("ok") is not True:
        return response
    source = response.get("data") if isinstance(response.get("data"), dict) else {}
    data = _boundary(record_persisted=False)
    record = source.get("record") if isinstance(source.get("record"), dict) else {}
    if isinstance(record.get("id"), str):
        data["record"] = {
            "id": record["id"],
            "revision": int(record.get("revision") or 0),
            "handoff_status": str(record.get("handoff_status") or ""),
            "record_state": str(record.get("record_state") or ""),
        }
        data["record_persisted"] = True
    return envelope(
        True,
        str(response.get("message") or "Đã lưu Content Handoff nội bộ."),
        data=data,
        status_name=str(response.get("status") or "completed"),
    )


def _idempotent(
    *,
    scope: str,
    actor_account_id: str,
    key: str,
    request_fingerprint: str,
    operation: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    _ensure_schema()
    cutoff = (datetime.now(timezone.utc) - IDEMPOTENCY_RETENTION).isoformat(timespec="seconds")
    with transaction() as conn:
        conn.execute("DELETE FROM web_idempotency WHERE scope LIKE ? AND created_at < ?", ("web-content-handoff:%", cutoff))
        existing = conn.execute(
            "SELECT response_json, request_fingerprint FROM web_idempotency WHERE scope=? AND key=?",
            (scope, key),
        ).fetchone()
        if existing:
            existing_fingerprint = str(existing[1] or "")
            if not existing_fingerprint or not hmac.compare_digest(existing_fingerprint, request_fingerprint):
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho yêu cầu Content Handoff khác")
            try:
                receipt = json.loads(str(existing[0]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Receipt Content Handoff không hợp lệ") from exc
            if not isinstance(receipt, dict):
                raise HTTPException(status_code=409, detail="Receipt Content Handoff không hợp lệ")
            return receipt
        count = conn.execute(
            "SELECT COUNT(*) FROM web_idempotency WHERE scope LIKE ?",
            (f"web-content-handoff:{actor_account_id}:%",),
        ).fetchone()
        if int(count[0] or 0) >= MAX_IDEMPOTENCY_RECORDS_PER_ACTOR:
            return _guarded("Kho receipt Content Handoff tạm thời đang đầy. Vui lòng thử lại sau.", "WEB_CONTENT_HANDOFF_IDEMPOTENCY_LIMIT")
        response = operation(conn)
        if response.get("ok") is True:
            receipt = _safe_receipt(response)
            conn.execute(
                """INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (scope, key, json.dumps(receipt, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
            )
            return receipt
        return response


def _detail(conn: Any, *, record_id: str, account_id: str) -> dict[str, Any] | None:
    record = _record_row(conn, record_id=record_id, account_id=account_id)
    if not record:
        return None
    versions = conn.execute(
        """SELECT revision, created_at FROM web_content_handoff_versions
           WHERE record_id=? AND account_id=? ORDER BY revision DESC LIMIT ?""",
        (record_id, account_id, MAX_VERSIONS_PER_RECORD),
    ).fetchall()
    events = conn.execute(
        """SELECT actor_kind, action, from_status, to_status, revision, created_at
           FROM web_content_handoff_events
           WHERE record_id=? AND account_id=? ORDER BY created_at DESC, id DESC LIMIT ?""",
        (record_id, account_id, MAX_EVENTS_PER_RECORD),
    ).fetchall()
    return {
        "record": _record_public(record, include_detail=True),
        "versions": [{"revision": int(row[0]), "created_at": str(row[1])} for row in versions],
        "events": [
            {
                "actor_kind": str(row[0]),
                "action": str(row[1]),
                "from_status": str(row[2]) if row[2] else None,
                "to_status": str(row[3]) if row[3] else None,
                "revision": int(row[4]),
                "created_at": str(row[5]),
            }
            for row in events
        ],
    }


def _summary(conn: Any, *, account_id: str) -> dict[str, Any]:
    active_rows = conn.execute(
        """SELECT handoff_status, COUNT(*) FROM web_content_handoff_records
           WHERE account_id=? AND record_state='active' GROUP BY handoff_status""",
        (account_id,),
    ).fetchall()
    archived = conn.execute(
        "SELECT COUNT(*) FROM web_content_handoff_records WHERE account_id=? AND record_state='archived'",
        (account_id,),
    ).fetchone()
    statuses = {state: 0 for state in sorted(HANDOFF_STATUSES)}
    for status, count in active_rows:
        if str(status) in statuses:
            statuses[str(status)] = int(count)
    return {
        "active_statuses": statuses,
        "active_total": sum(statuses.values()),
        "archived_total": int(archived[0] or 0) if archived else 0,
        "workflow": ["draft", "review", "approved_for_handoff", "handed_off", "blocked"],
    }


def _make_record_response(conn: Any, *, record_id: str, account_id: str, message: str) -> dict[str, Any]:
    current = _record_row(conn, record_id=record_id, account_id=account_id)
    if not current:
        raise RuntimeError("Content Handoff biến mất trong transaction của chính nó")
    return envelope(
        True,
        message,
        data=_boundary(record=_record_public(current, include_detail=True), record_persisted=True),
        status_name=str(current[5]),
    )


def _assert_confirmation(payload: RevisionMutationRequest) -> None:
    if not payload.confirm:
        raise HTTPException(status_code=422, detail="Cần xác nhận thao tác Content Handoff")


@router.get("/policy")
async def content_handoff_policy():
    _require_enabled()
    return envelope(
        True,
        "Content Handoff chỉ là sổ bàn giao nội bộ Web-native; không có publish hoặc delivery bên ngoài.",
        data=_boundary(
            workflow={
                "customer": ["draft", "review"],
                "staff": ["approved_for_handoff", "handed_off", "blocked"],
                "archive": ["active", "archived"],
            },
            allowed_reference_types=["project_id", "asset_ids", "campaign_id", "native_refs"],
            native_reference_contract={
                "native_output": "owner-scoped opaque Web-native job ID; must be completed with a sealed output at create or update time",
                "native_asset": "owner-scoped opaque active Asset Vault ID",
                "lineage_read": "reveals only availability and filename/content_type/byte_size from a sealed output; never URL, storage key, hash, provider, Bot, payment or raw ID",
                "external_delivery_implied": False,
            },
        ),
        status_name="read_only",
    )


@router.get("/summary")
async def content_handoff_summary(account: dict = Depends(require_account)):
    _require_enabled()
    _ensure_schema()
    with read_transaction() as conn:
        data = _summary(conn, account_id=str(account["id"]))
    return envelope(True, "Đã tải tổng quan Content Handoff riêng tư.", data=_boundary(**data), status_name="read_only")


@router.get("/records")
async def list_handoff_records(
    status: str = "all",
    include_archived: bool = False,
    limit: int = 30,
    offset: int = 0,
    account: dict = Depends(require_account),
):
    _require_enabled()
    account_id = str(account["id"])
    requested_status = str(status or "all").strip().lower()
    if requested_status != "all" and requested_status not in HANDOFF_STATUSES:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái Content Handoff không hợp lệ")
    bounded = max(1, min(int(limit), MAX_LIST_LIMIT))
    bounded_offset = int(offset)
    if bounded_offset < 0 or bounded_offset > MAX_LIST_OFFSET:
        raise HTTPException(status_code=422, detail="Offset danh sách Content Handoff không hợp lệ")
    clauses = ["account_id=?"]
    params: list[Any] = [account_id]
    if not include_archived:
        clauses.append("record_state='active'")
    if requested_status != "all":
        clauses.append("handoff_status=?")
        params.append(requested_status)
    _ensure_schema()
    with read_transaction() as conn:
        rows = conn.execute(
            f"""SELECT id, account_id, title, purpose, references_json, handoff_status, record_state, staff_note,
                       reviewer_account_id, revision, created_at, updated_at, reviewed_at, handed_off_at, archived_at
                FROM web_content_handoff_records WHERE {' AND '.join(clauses)}
                ORDER BY CASE handoff_status WHEN 'review' THEN 0 WHEN 'blocked' THEN 1 WHEN 'draft' THEN 2
                   WHEN 'approved_for_handoff' THEN 3 ELSE 4 END, updated_at DESC, id DESC LIMIT ? OFFSET ?""",
            (*params, bounded + 1, bounded_offset),
        ).fetchall()
    return envelope(
        True,
        "Đã tải Content Handoff của Web account hiện tại.",
        data=_boundary(
            items=[_record_public(tuple(row)) for row in rows[:bounded]],
            has_more=len(rows) > bounded,
            next_offset=bounded_offset + bounded if len(rows) > bounded else None,
        ),
        status_name="read_only",
    )


@router.get("/records/{record_id}")
async def get_handoff_record(record_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    record_id = _uuid(record_id, label="Content Handoff ID", http=True)
    _ensure_schema()
    with read_transaction() as conn:
        detail = _detail(conn, record_id=record_id, account_id=str(account["id"]))
    if not detail:
        return _not_found()
    return envelope(True, "Đã tải Content Handoff, revision và lịch sử nội bộ.", data=_boundary(**detail), status_name="read_only")


@router.get("/records/{record_id}/lineage")
async def get_handoff_lineage(record_id: str, account: dict = Depends(require_account)):
    """Read current safe availability for native references owned by this user."""

    _require_enabled()
    record_id = _uuid(record_id, label="Content Handoff ID", http=True)
    account_id = str(account["id"])
    _ensure_schema()
    with read_transaction() as conn:
        record = _record_row(conn, record_id=record_id, account_id=account_id)
        if not record:
            return _not_found()
        references = _decode_references(record[4])
        native_refs = list(references.get("native_refs") or [])
        lineage = [
            _lineage_reference(conn, account_id=account_id, reference=reference)
            for reference in native_refs
            if isinstance(reference, dict)
            and str(reference.get("ref_type") or "") in NATIVE_REF_TYPES
            and isinstance(reference.get("ref_id"), str)
        ]
    return envelope(
        True,
        "Đã tải lineage Web-native hiện tại. Availability không phải bằng chứng publish hoặc delivery bên ngoài.",
        data=_boundary(
            record={
                "id": str(record[0]),
                "revision": int(record[9]),
                "handoff_status": str(record[5]),
                "record_state": str(record[6]),
            },
            lineage=lineage,
        ),
        status_name="read_only",
    )


@router.post("/records")
async def create_handoff_record(payload: HandoffRecordPayload, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    account_id = str(account["id"])
    references = _references_payload(payload.references)
    fingerprint = _fingerprint({"action": "create", "title": payload.title, "purpose": payload.purpose, "references": references})

    def operation(conn: Any) -> dict[str, Any]:
        count = conn.execute(
            "SELECT COUNT(*) FROM web_content_handoff_records WHERE account_id=? AND record_state='active'",
            (account_id,),
        ).fetchone()
        if int(count[0] or 0) >= MAX_ACTIVE_RECORDS_PER_ACCOUNT:
            return _guarded("Đã đạt giới hạn Content Handoff đang hoạt động. Hãy archive record cũ trước.", "WEB_CONTENT_HANDOFF_LIMIT")
        if not _references_owned(conn, account_id=account_id, references=references):
            return _guarded("Project, Asset hoặc Campaign không tồn tại, không còn active hoặc không thuộc Web account hiện tại.", "WEB_CONTENT_HANDOFF_REFERENCE_INVALID")
        record_id = str(uuid.uuid4())
        now = utc_now()
        conn.execute(
            """INSERT INTO web_content_handoff_records
               (id, account_id, title, purpose, references_json, handoff_status, record_state, staff_note,
                reviewer_account_id, revision, created_at, updated_at, reviewed_at, handed_off_at, archived_at)
               VALUES (?, ?, ?, ?, ?, 'draft', 'active', '', NULL, 1, ?, ?, NULL, NULL, NULL)""",
            (record_id, account_id, payload.title, payload.purpose, json.dumps(references, ensure_ascii=False, sort_keys=True), now, now),
        )
        record = _record_row(conn, record_id=record_id, account_id=account_id)
        if not record:
            raise RuntimeError("Không thể tạo Content Handoff")
        _insert_version(conn, row=record)
        _event(conn, record_id=record_id, account_id=account_id, actor_account_id=account_id, actor_kind="owner", action="record_created", from_status=None, to_status="draft", revision=1)
        _audit(conn, request=request, account=account, action="web.content_handoff.create", target=record_id, detail="web-native content handoff draft created")
        return _make_record_response(
            conn,
            record_id=record_id,
            account_id=account_id,
            message="Đã tạo draft Content Handoff riêng tư. Không có recipient, publish, notification hoặc delivery bên ngoài.",
        )

    return _idempotent(
        scope=f"web-content-handoff:{account_id}:record:create",
        actor_account_id=account_id,
        key=payload.idempotency_key,
        request_fingerprint=fingerprint,
        operation=operation,
    )


@router.patch("/records/{record_id}")
async def update_handoff_record(record_id: str, payload: HandoffRecordUpdateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    record_id = _uuid(record_id, label="Content Handoff ID", http=True)
    account_id = str(account["id"])
    references = _references_payload(payload.references)
    fingerprint = _fingerprint(
        {
            "action": "update", "record_id": record_id, "expected_revision": payload.expected_revision,
            "title": payload.title, "purpose": payload.purpose, "references": references,
        }
    )

    def operation(conn: Any) -> dict[str, Any]:
        current = _record_row(conn, record_id=record_id, account_id=account_id)
        if not current:
            return _not_found()
        if int(current[9]) != payload.expected_revision:
            return _revision_conflict(int(current[9]))
        if str(current[6]) == "archived":
            return _record_archived()
        if str(current[5]) not in {"draft", "blocked"}:
            return _guarded("Chỉ draft hoặc record bị block mới có thể chỉnh sửa. Hãy tạo revision mới trước khi review lại.", "WEB_CONTENT_HANDOFF_EDIT_STATE_INVALID")
        previous_status = str(current[5])
        if not _can_add_version(conn, record_id=record_id, account_id=account_id):
            return _guarded("Content Handoff đã đạt giới hạn revision an toàn.", "WEB_CONTENT_HANDOFF_VERSION_LIMIT")
        if not _references_owned(conn, account_id=account_id, references=references):
            return _guarded("Project, Asset hoặc Campaign không tồn tại, không còn active hoặc không thuộc Web account hiện tại.", "WEB_CONTENT_HANDOFF_REFERENCE_INVALID")
        next_status = "draft"
        next_revision = int(current[9]) + 1
        now = utc_now()
        changed = conn.execute(
            """UPDATE web_content_handoff_records
               SET title=?, purpose=?, references_json=?, handoff_status=?, staff_note='', reviewer_account_id=NULL,
                   revision=?, updated_at=?, reviewed_at=NULL, handed_off_at=NULL
               WHERE id=? AND account_id=? AND revision=?""",
            (
                payload.title, payload.purpose, json.dumps(references, ensure_ascii=False, sort_keys=True), next_status,
                next_revision, now, record_id, account_id, payload.expected_revision,
            ),
        )
        if changed.rowcount != 1:
            return _revision_conflict(int(current[9]))
        current = _record_row(conn, record_id=record_id, account_id=account_id)
        if not current:
            raise RuntimeError("Không thể nạp lại Content Handoff sau update")
        _insert_version(conn, row=current)
        _event(
            conn, record_id=record_id, account_id=account_id, actor_account_id=account_id, actor_kind="owner",
            action="record_reopened" if previous_status == "blocked" else "record_updated",
            from_status=previous_status, to_status=next_status, revision=int(current[9]),
        )
        _audit(conn, request=request, account=account, action="web.content_handoff.update", target=record_id, detail=f"revision={int(current[9])};status=draft")
        return _make_record_response(
            conn,
            record_id=record_id,
            account_id=account_id,
            message="Đã lưu revision Content Handoff mới ở draft. Chưa có hành động external nào được tạo.",
        )

    return _idempotent(
        scope=f"web-content-handoff:{account_id}:record:{record_id}:update",
        actor_account_id=account_id,
        key=payload.idempotency_key,
        request_fingerprint=fingerprint,
        operation=operation,
    )


@router.post("/records/{record_id}/submit-review")
async def submit_handoff_for_review(record_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    _assert_confirmation(payload)
    record_id = _uuid(record_id, label="Content Handoff ID", http=True)
    account_id = str(account["id"])
    fingerprint = _fingerprint({"action": "submit_review", "record_id": record_id, "expected_revision": payload.expected_revision})

    def operation(conn: Any) -> dict[str, Any]:
        current = _record_row(conn, record_id=record_id, account_id=account_id)
        if not current:
            return _not_found()
        if int(current[9]) != payload.expected_revision:
            return _revision_conflict(int(current[9]))
        if str(current[6]) == "archived":
            return _record_archived()
        if str(current[5]) != "draft":
            return _guarded("Chỉ draft mới có thể gửi review.", "WEB_CONTENT_HANDOFF_REVIEW_STATE_INVALID")
        if not _can_add_version(conn, record_id=record_id, account_id=account_id):
            return _guarded("Content Handoff đã đạt giới hạn revision an toàn.", "WEB_CONTENT_HANDOFF_VERSION_LIMIT")
        next_revision = int(current[9]) + 1
        now = utc_now()
        conn.execute(
            """UPDATE web_content_handoff_records SET handoff_status='review', revision=?, updated_at=?
               WHERE id=? AND account_id=? AND revision=?""",
            (next_revision, now, record_id, account_id, payload.expected_revision),
        )
        current = _record_row(conn, record_id=record_id, account_id=account_id)
        if not current:
            raise RuntimeError("Không thể nạp lại Content Handoff sau submit review")
        _insert_version(conn, row=current)
        _event(conn, record_id=record_id, account_id=account_id, actor_account_id=account_id, actor_kind="owner", action="review_requested", from_status="draft", to_status="review", revision=int(current[9]))
        _audit(conn, request=request, account=account, action="web.content_handoff.submit_review", target=record_id, detail=f"revision={int(current[9])}")
        return _make_record_response(
            conn,
            record_id=record_id,
            account_id=account_id,
            message="Đã đưa Content Handoff vào hàng review nội bộ. Không có notification hay external handoff được gửi.",
        )

    return _idempotent(
        scope=f"web-content-handoff:{account_id}:record:{record_id}:submit-review",
        actor_account_id=account_id,
        key=payload.idempotency_key,
        request_fingerprint=fingerprint,
        operation=operation,
    )


def _lifecycle_mutation(
    *,
    record_id: str,
    payload: RevisionMutationRequest,
    request: Request,
    account: dict,
    target_state: str,
    action: str,
) -> dict[str, Any]:
    _assert_confirmation(payload)
    account_id = str(account["id"])
    fingerprint = _fingerprint(
        {"action": action, "record_id": record_id, "expected_revision": payload.expected_revision, "target_state": target_state}
    )

    def operation(conn: Any) -> dict[str, Any]:
        current = _record_row(conn, record_id=record_id, account_id=account_id)
        if not current:
            return _not_found()
        if int(current[9]) != payload.expected_revision:
            return _revision_conflict(int(current[9]))
        if str(current[6]) == target_state:
            return _guarded("Content Handoff đã ở trạng thái lifecycle yêu cầu.", "WEB_CONTENT_HANDOFF_LIFECYCLE_STATE")
        if not _can_add_version(conn, record_id=record_id, account_id=account_id):
            return _guarded("Content Handoff đã đạt giới hạn revision an toàn.", "WEB_CONTENT_HANDOFF_VERSION_LIMIT")
        next_revision = int(current[9]) + 1
        now = utc_now()
        conn.execute(
            """UPDATE web_content_handoff_records SET record_state=?, revision=?, updated_at=?, archived_at=?
               WHERE id=? AND account_id=? AND revision=?""",
            (target_state, next_revision, now, now if target_state == "archived" else None, record_id, account_id, payload.expected_revision),
        )
        current = _record_row(conn, record_id=record_id, account_id=account_id)
        if not current:
            raise RuntimeError("Không thể nạp lại Content Handoff sau lifecycle change")
        _insert_version(conn, row=current)
        _event(
            conn, record_id=record_id, account_id=account_id, actor_account_id=account_id, actor_kind="owner",
            action=action, from_status=str(current[5]), to_status=str(current[5]), revision=int(current[9]),
        )
        _audit(conn, request=request, account=account, action=f"web.content_handoff.{action}", target=record_id, detail=f"revision={int(current[9])};record_state={target_state}")
        message = "Đã archive Content Handoff; workflow nội bộ sẽ không tiếp tục khi record đang archive." if target_state == "archived" else "Đã restore Content Handoff về lifecycle active; trạng thái handoff trước đó được giữ nguyên."
        return _make_record_response(conn, record_id=record_id, account_id=account_id, message=message)

    return _idempotent(
        scope=f"web-content-handoff:{account_id}:record:{record_id}:{action}",
        actor_account_id=account_id,
        key=payload.idempotency_key,
        request_fingerprint=fingerprint,
        operation=operation,
    )


@router.post("/records/{record_id}/archive")
async def archive_handoff_record(record_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    return _lifecycle_mutation(
        record_id=_uuid(record_id, label="Content Handoff ID", http=True),
        payload=payload,
        request=request,
        account=account,
        target_state="archived",
        action="record_archived",
    )


@router.post("/records/{record_id}/restore")
async def restore_handoff_record(record_id: str, payload: RevisionMutationRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    return _lifecycle_mutation(
        record_id=_uuid(record_id, label="Content Handoff ID", http=True),
        payload=payload,
        request=request,
        account=account,
        target_state="active",
        action="record_restored",
    )


def _staff_role(account: dict) -> str:
    """Ask the existing signed-account Support Desk authority, never a browser field."""

    return require_support_staff(account)


@router.get("/admin/records")
async def staff_list_handoff_records(
    status: str = "review",
    limit: int = 50,
    offset: int = 0,
    account: dict = Depends(require_account),
):
    _require_enabled()
    role = _staff_role(account)
    requested_status = str(status or "review").strip().lower()
    if requested_status != "all" and requested_status not in HANDOFF_STATUSES:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái Content Handoff không hợp lệ")
    bounded = max(1, min(int(limit), MAX_LIST_LIMIT))
    bounded_offset = int(offset)
    if bounded_offset < 0 or bounded_offset > MAX_LIST_OFFSET:
        raise HTTPException(status_code=422, detail="Offset hàng review Content Handoff không hợp lệ")
    clauses = ["record_state='active'"]
    params: list[Any] = []
    if requested_status != "all":
        clauses.append("handoff_status=?")
        params.append(requested_status)
    _ensure_schema()
    with read_transaction() as conn:
        rows = conn.execute(
            f"""SELECT id, account_id, title, purpose, references_json, handoff_status, record_state, staff_note,
                       reviewer_account_id, revision, created_at, updated_at, reviewed_at, handed_off_at, archived_at
                FROM web_content_handoff_records WHERE {' AND '.join(clauses)}
                ORDER BY CASE handoff_status WHEN 'review' THEN 0 WHEN 'approved_for_handoff' THEN 1 WHEN 'blocked' THEN 2 ELSE 3 END,
                         updated_at ASC, id ASC LIMIT ? OFFSET ?""",
            (*params, bounded + 1, bounded_offset),
        ).fetchall()
    return envelope(
        True,
        "Đã tải hàng Content Handoff nội bộ cho Customer Care.",
        data=_boundary(
            operator_role=role,
            items=[_record_public(tuple(row), include_detail=True) for row in rows[:bounded]],
            has_more=len(rows) > bounded,
            next_offset=bounded_offset + bounded if len(rows) > bounded else None,
        ),
        status_name="read_only",
    )


@router.post("/admin/records/{record_id}/review")
async def staff_review_handoff_record(record_id: str, payload: StaffReviewRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    if not payload.confirm:
        raise HTTPException(status_code=422, detail="Cần xác nhận quyết định review Content Handoff")
    role = _staff_role(account)
    record_id = _uuid(record_id, label="Content Handoff ID", http=True)
    actor_account_id = str(account["id"])
    fingerprint = _fingerprint(
        {
            "action": "staff_review", "record_id": record_id, "decision": payload.decision,
            "expected_revision": payload.expected_revision, "review_note_sha256": _content_hash(payload.review_note),
            "confirm_manual_handoff": payload.confirm_manual_handoff,
        }
    )

    def operation(conn: Any) -> dict[str, Any]:
        current = _record_row(conn, record_id=record_id)
        if not current:
            return _not_found()
        account_id = str(current[1])
        if int(current[9]) != payload.expected_revision:
            return _revision_conflict(int(current[9]))
        if str(current[6]) == "archived":
            return _record_archived()
        current_status = str(current[5])
        if payload.decision in {"approved_for_handoff", "handed_off"} and role != "manager":
            return _guarded("Chỉ Customer Care manager hoặc admin signed Web mới có thể approve hoặc ghi nhận handoff nội bộ.", "WEB_CONTENT_HANDOFF_STAFF_MANAGER_REQUIRED")
        if payload.decision == "approved_for_handoff" and current_status != "review":
            return _guarded("Chỉ record đang review mới có thể được approve cho handoff.", "WEB_CONTENT_HANDOFF_STAFF_TRANSITION_INVALID")
        if payload.decision == "handed_off" and current_status != "approved_for_handoff":
            return _guarded("Chỉ record đã approve mới có thể ghi nhận handoff nội bộ.", "WEB_CONTENT_HANDOFF_STAFF_TRANSITION_INVALID")
        if payload.decision == "blocked" and current_status not in {"review", "approved_for_handoff"}:
            return _guarded("Chỉ record đang review hoặc đã approve mới có thể block.", "WEB_CONTENT_HANDOFF_STAFF_TRANSITION_INVALID")
        if not _can_add_version(conn, record_id=record_id, account_id=account_id):
            return _guarded("Content Handoff đã đạt giới hạn revision an toàn.", "WEB_CONTENT_HANDOFF_VERSION_LIMIT")
        next_revision = int(current[9]) + 1
        now = utc_now()
        conn.execute(
            """UPDATE web_content_handoff_records
               SET handoff_status=?, staff_note=?, reviewer_account_id=?, revision=?, updated_at=?, reviewed_at=?, handed_off_at=?
               WHERE id=? AND revision=?""",
            (
                payload.decision, payload.review_note, actor_account_id, next_revision, now, now,
                now if payload.decision == "handed_off" else (str(current[13]) if current[13] else None),
                record_id, payload.expected_revision,
            ),
        )
        current = _record_row(conn, record_id=record_id)
        if not current:
            raise RuntimeError("Không thể nạp lại Content Handoff sau staff review")
        _insert_version(conn, row=current)
        action = {
            "approved_for_handoff": "staff_approved_for_handoff",
            "blocked": "staff_blocked",
            "handed_off": "staff_manual_handoff_recorded",
        }[payload.decision]
        _event(
            conn, record_id=record_id, account_id=account_id, actor_account_id=actor_account_id, actor_kind=f"staff_{role}",
            action=action, from_status=current_status, to_status=payload.decision, revision=int(current[9]),
        )
        _audit(
            conn, request=request, account=account, action="web.content_handoff.staff_review", target=record_id,
            detail=f"decision={payload.decision};revision={int(current[9])};role={role}",
        )
        message = {
            "approved_for_handoff": "Đã approve Content Handoff cho bước bàn giao nội bộ tiếp theo. Chưa có delivery hoặc publish bên ngoài.",
            "blocked": "Đã block Content Handoff kèm ghi chú review. Không có action bên ngoài nào xảy ra.",
            "handed_off": "Đã ghi nhận bàn giao nội bộ do nhân sự thực hiện. Đây không phải bằng chứng delivery, notification hoặc publish bên ngoài.",
        }[payload.decision]
        return _make_record_response(conn, record_id=record_id, account_id=account_id, message=message)

    return _idempotent(
        scope=f"web-content-handoff:{actor_account_id}:staff-review:{record_id}",
        actor_account_id=actor_account_id,
        key=payload.idempotency_key,
        request_fingerprint=fingerprint,
        operation=operation,
    )
