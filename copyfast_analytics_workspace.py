"""Private, Web-native Analytics & Reporting Workspace.

The historical Telegram Bot remains the authority for platform integrations,
live/provider analytics, canonical reports, revenue, Xu, payments, jobs and
publishing.  This router deliberately owns none of those systems.  It gives a
signed Web account a professional, durable place to record *manual* metrics,
compare saved observations and write human-authored findings.  Every result
is calculated only from data the account saved in this Web workspace.
"""

from __future__ import annotations

import csv
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import hmac
import io
import json
import re
import sqlite3
import uuid
from typing import Any, Callable, Iterable

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import analytics_workspace_enabled, analytics_workspace_export_enabled, best_effort_transaction, ensure_copyfast_schema, read_transaction, transaction, utc_now


router = APIRouter(prefix="/api/v1/analytics-workspace", tags=["Web Analytics Workspace"])

REPORT_STATES = frozenset({"draft", "review", "finalized", "archived"})
METRIC_STATES = frozenset({"active", "archived"})
METRIC_UNITS = frozenset({"count", "percent", "duration", "custom"})
METRIC_DIRECTIONS = frozenset({"up", "down", "neutral"})
FINDING_KINDS = frozenset({"finding", "decision", "action"})
FINDING_STATES = frozenset({"active", "archived"})
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
UNSAFE_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SECRET_PATTERN = re.compile(
    r"\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|client[ _-]?secret|"
    r"password|passphrase|authorization|otp|cvv|cvc|private[ _-]?key)\b\s*(?:['\"]\s*)?(?:[:=]|\bis\b)\s*(?:['\"]\s*)?[A-Za-z0-9_./+=:-]{6,}",
    re.IGNORECASE,
)
KNOWN_SECRET_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(?:sk|pk|rk)_[A-Za-z0-9_-]{12,}|github_pat_[A-Za-z0-9_]{12}|"
    r"gh[pousr]_[A-Za-z0-9]{12}|xox[bpars]-[A-Za-z0-9-]{12}|AIza[0-9A-Za-z_-]{20}|"
    r"(?:AKIA|ASIA)[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}\.",
    re.IGNORECASE,
)
PAYMENT_PATTERN = re.compile(
    r"\b(?:txid|transaction\s+(?:hash|id|reference)|mã\s*(?:giao\s*)?(?:dịch|thanh\s*toán)|"
    r"bill|biên\s*lai|chứng\s*từ|số\s*tài\s*khoản|stk|qr\s*(?:code|thanh\s*toán))\b",
    re.IGNORECASE,
)
EXTERNAL_HANDLE_PATTERN = re.compile(
    r"\b(?:(?:provider|render|job|media|asset|file|worker|engine|platform|channel)[ _-]*(?:id|ref(?:erence)?|token|handle)|"
    r"(?:telegram[ _-]*)?bot[ _-]*(?:id|ref(?:erence)?|token|secret|handle))\b\s*(?::|=|\bis\b)\s*\S+",
    re.IGNORECASE,
)
MARKUP_EXECUTION_PATTERN = re.compile(
    r"<\s*/?\s*(?:script|svg|img|iframe|object|embed|style|link|meta|base|form|input|video|audio)\b|\bon[a-z]+\s*=",
    re.IGNORECASE,
)
URL_OR_PATH_PATTERN = re.compile(
    r"(?:\bhttps?://|\bwww\.|\b(?:file|data|javascript|blob):|(?:^|[\s\"'])"
    r"(?:[A-Za-z]:[\\/]|/[^\s]+|\\\\[^\s]+))",
    re.IGNORECASE,
)
FORMULA_PREFIX_PATTERN = re.compile(r"^\s*[=+@]", re.IGNORECASE)

MAX_REPORTS_PER_ACCOUNT = 300
MAX_METRICS_PER_REPORT = 60
MAX_SNAPSHOTS_PER_METRIC = 500
MAX_FINDINGS_PER_REPORT = 300
MAX_REPORT_VERSIONS = 100
MAX_ENTITY_VERSIONS = 80
MAX_LIST_LIMIT = 100
MAX_EVENT_LIMIT = 60
MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT = 1_024
IDEMPOTENCY_RETENTION = timedelta(hours=24)
ARCHIVED_ORDINAL_BASE = 1_000_000
MAX_DECIMAL_ABS = Decimal("1000000000000")
# A manual report can legally contain 30,000 snapshots.  A CSV attachment is
# intentionally a separate delivery boundary, so refuse a complete export
# that would exceed this bounded memory/response ceiling rather than emitting
# a silently truncated file.  It remains below the existing private Prompt
# Library export ceiling while leaving enough room for a real manual report.
MAX_MANUAL_CSV_EXPORT_BYTES = 24 * 1024 * 1024
MAX_MANUAL_CSV_EXPORT_ROWS = 32_000
# Some spreadsheet programs trim invisible order/format characters before
# evaluating a cell. Treat those prefixes like ordinary whitespace too; the
# serializer still prepends an apostrophe before emitting any matching cell.
CSV_FORMULA_PREFIX_PATTERN = re.compile(r"^[\s\ufeff\u200b\u200c\u200d\u2060]*[=+\-@]")
MANUAL_CSV_SCHEMA = "toan-aas-web-manual-analytics-csv-v1"


def _require_enabled() -> None:
    if not analytics_workspace_enabled():
        raise HTTPException(
            status_code=503,
            detail="Analytics Workspace đang tạm dừng để bảo trì. WEBAPP_ANALYTICS_WORKSPACE_ENABLED chưa được bật.",
        )


def _require_manual_csv_export_enabled() -> None:
    """Fail closed unless the separately reviewed attachment switch is on."""

    if not analytics_workspace_export_enabled():
        raise HTTPException(
            status_code=503,
            detail="Xuất CSV thủ công đang tạm dừng. WEBAPP_ANALYTICS_WORKSPACE_EXPORT_ENABLED chưa được bật.",
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
    if text and (FORMULA_PREFIX_PATTERN.search(text) or _sensitive_text(text)):
        raise ValueError(f"{label} không nhận công thức, secret, URL/đường dẫn, Bot/provider hoặc chứng từ thanh toán")
    return text


def _body(value: Any, *, label: str, maximum: int, allow_empty: bool = False) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if UNSAFE_CONTROL_PATTERN.search(text) or len(text) > maximum or (not allow_empty and not text):
        if allow_empty:
            raise ValueError(f"{label} tối đa {maximum:,} ký tự hợp lệ".replace(",", "."))
        raise ValueError(f"{label} cần từ 1 đến {maximum:,} ký tự hợp lệ".replace(",", "."))
    if text and _sensitive_text(text):
        raise ValueError(f"{label} không nhận secret, URL/đường dẫn, Bot/provider hoặc chứng từ thanh toán")
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


def _date(value: Any, *, label: str) -> str:
    text = str(value or "").strip()
    try:
        parsed = date.fromisoformat(text)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} phải có dạng YYYY-MM-DD") from exc
    if parsed.isoformat() != text:
        raise ValueError(f"{label} phải có dạng YYYY-MM-DD")
    return text


def _decimal(value: Any, *, label: str) -> str:
    raw = str(value or "").strip()
    if not raw or len(raw) > 40 or FORMULA_PREFIX_PATTERN.search(raw) or "e" in raw.lower():
        raise ValueError(f"{label} phải là số thập phân dương theo dạng thường")
    try:
        parsed = Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{label} phải là số thập phân hợp lệ") from exc
    if not parsed.is_finite() or parsed < 0 or parsed > MAX_DECIMAL_ABS:
        raise ValueError(f"{label} nằm ngoài giới hạn an toàn")
    normalized = parsed.normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _fingerprint(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _idempotency_cutoff() -> str:
    return (datetime.now(timezone.utc) - IDEMPOTENCY_RETENTION).isoformat(timespec="seconds")


def _excerpt(value: Any, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= limit else f"{text[:max(1, limit - 1)].rstrip()}…"


def _boundary(**extra: Any) -> dict[str, Any]:
    """Declare the manual-only analytics boundary in every API response."""
    return {
        "execution": "manual_measurement_only",
        "data_origin": "user_supplied_only",
        "local_calculation": True,
        "bot_called": False,
        "provider_called": False,
        "social_api_called": False,
        "platform_data_connected": False,
        "platform_data_verified": False,
        "ai_recommendation_created": False,
        "canonical_revenue": False,
        "wallet_mutated": False,
        "payment_started": False,
        "payment_processed": False,
        "job_created": False,
        "publish_action_created": False,
        "browser_file_upload": False,
        "external_url_import": False,
        "report_file_created": False,
        "output_delivery": "not_applicable",
        **extra,
    }


def _guarded(message: str, code: str) -> dict[str, Any]:
    return envelope(False, message, data=_boundary(), status_name="guarded", error_code=code)


class ReportPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    objective: str
    context_label: str = ""
    period_start: str
    period_end: str
    project_id: str | None = None
    campaign_plan_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    summary_note: str = ""

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return _line(value, label="Tên báo cáo", minimum=3, maximum=180)

    @field_validator("objective")
    @classmethod
    def _objective(cls, value: str) -> str:
        return _body(value, label="Mục tiêu đo lường", maximum=2_000)

    @field_validator("context_label")
    @classmethod
    def _context_label(cls, value: str) -> str:
        return _line(value, label="Nhãn bối cảnh", minimum=0, maximum=160, allow_empty=True)

    @field_validator("period_start", "period_end")
    @classmethod
    def _period(cls, value: str) -> str:
        return _date(value, label="Khoảng thời gian")

    @field_validator("project_id")
    @classmethod
    def _project(cls, value: str | None) -> str | None:
        return _optional_uuid(value, label="Project ID")

    @field_validator("campaign_plan_id")
    @classmethod
    def _campaign(cls, value: str | None) -> str | None:
        return _optional_uuid(value, label="Campaign plan ID")

    @field_validator("tags")
    @classmethod
    def _tag_values(cls, value: list[str]) -> list[str]:
        return _tags(value)

    @field_validator("summary_note")
    @classmethod
    def _summary_note(cls, value: str) -> str:
        return _body(value, label="Ghi chú tổng quan", maximum=6_000, allow_empty=True)

    def model_post_init(self, __context: Any) -> None:
        start = date.fromisoformat(self.period_start)
        end = date.fromisoformat(self.period_end)
        if end < start or (end - start).days > 366:
            raise ValueError("Khoảng thời gian phải theo thứ tự hợp lệ và không quá 366 ngày")


class ReportCreateRequest(ReportPayload):
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class ReportUpdateRequest(ReportPayload):
    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class ReportRevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class LifecycleRequest(ReportRevisionRequest):
    state: str

    @field_validator("state")
    @classmethod
    def _state(cls, value: str) -> str:
        normalized = _line(value, label="Trạng thái", minimum=1, maximum=20).lower()
        if normalized not in REPORT_STATES:
            raise ValueError("Trạng thái báo cáo không hợp lệ")
        return normalized


class ManualCsvExportRequest(BaseModel):
    """A narrow concurrency receipt for one private CSV attachment.

    Exporting a finalized report is deliberately not an idempotent stored
    mutation.  The revision proves the browser is still looking at the same
    owner-scoped finalized report immediately before the server serializes
    data; the server never accepts report content from the browser.
    """

    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1)


class RestoreVersionRequest(ReportRevisionRequest):
    target_revision: int = Field(ge=1)


class MetricPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    unit: str = "count"
    direction: str = "neutral"
    description: str = ""

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return _line(value, label="Tên metric", minimum=2, maximum=120)

    @field_validator("unit")
    @classmethod
    def _unit(cls, value: str) -> str:
        normalized = _line(value, label="Đơn vị metric", minimum=1, maximum=20).lower()
        if normalized not in METRIC_UNITS:
            raise ValueError("Đơn vị metric không hợp lệ")
        return normalized

    @field_validator("direction")
    @classmethod
    def _direction(cls, value: str) -> str:
        normalized = _line(value, label="Chiều đánh giá", minimum=1, maximum=20).lower()
        if normalized not in METRIC_DIRECTIONS:
            raise ValueError("Chiều đánh giá metric không hợp lệ")
        return normalized

    @field_validator("description")
    @classmethod
    def _description(cls, value: str) -> str:
        return _body(value, label="Ghi chú metric", maximum=1_200, allow_empty=True)


class MetricCreateRequest(MetricPayload):
    expected_report_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class MetricUpdateRequest(MetricPayload):
    expected_report_revision: int = Field(ge=1)
    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class EntityStateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_report_revision: int = Field(ge=1)
    expected_revision: int = Field(ge=1)
    state: str
    idempotency_key: str

    @field_validator("state")
    @classmethod
    def _state(cls, value: str) -> str:
        normalized = _line(value, label="Trạng thái", minimum=1, maximum=16).lower()
        if normalized not in METRIC_STATES:
            raise ValueError("Trạng thái record không hợp lệ")
        return normalized

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class SnapshotPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observed_on: str
    value: str
    source_label: str = ""
    note: str = ""

    @field_validator("observed_on")
    @classmethod
    def _observed_on(cls, value: str) -> str:
        return _date(value, label="Ngày quan sát")

    @field_validator("value")
    @classmethod
    def _value(cls, value: str) -> str:
        return _decimal(value, label="Giá trị metric")

    @field_validator("source_label")
    @classmethod
    def _source_label(cls, value: str) -> str:
        return _line(value, label="Nhãn nguồn tự khai", minimum=0, maximum=160, allow_empty=True)

    @field_validator("note")
    @classmethod
    def _note(cls, value: str) -> str:
        return _body(value, label="Ghi chú snapshot", maximum=1_800, allow_empty=True)


class SnapshotCreateRequest(SnapshotPayload):
    expected_report_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class SnapshotUpdateRequest(SnapshotPayload):
    expected_report_revision: int = Field(ge=1)
    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class FindingPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = "finding"
    body: str

    @field_validator("kind")
    @classmethod
    def _kind(cls, value: str) -> str:
        normalized = _line(value, label="Loại nhận định", minimum=1, maximum=20).lower()
        if normalized not in FINDING_KINDS:
            raise ValueError("Loại nhận định không hợp lệ")
        return normalized

    @field_validator("body")
    @classmethod
    def _body(cls, value: str) -> str:
        return _body(value, label="Nội dung nhận định", maximum=6_000)


class FindingCreateRequest(FindingPayload):
    expected_report_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class FindingUpdateRequest(FindingPayload):
    expected_report_revision: int = Field(ge=1)
    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class FindingStateRequest(EntityStateRequest):
    @field_validator("state")
    @classmethod
    def _state(cls, value: str) -> str:
        normalized = _line(value, label="Trạng thái nhận định", minimum=1, maximum=16).lower()
        if normalized not in FINDING_STATES:
            raise ValueError("Trạng thái nhận định không hợp lệ")
        return normalized


# Route implementation follows below.  Helpers stay deliberately local to
# this router so a future platform integration cannot accidentally inherit
# the Web-only manual-data trust boundary.


def _safe_receipt(response: dict[str, Any]) -> dict[str, Any]:
    """Persist only opaque mutation receipts, never private narratives/data."""
    if not isinstance(response, dict) or response.get("ok") is not True:
        return response
    source = response.get("data") if isinstance(response.get("data"), dict) else {}
    data = _boundary()
    report = source.get("report")
    if isinstance(report, dict) and isinstance(report.get("id"), str):
        data["report"] = {
            "id": str(report["id"]),
            "revision": int(report.get("revision") or 0),
            "state": str(report.get("state") or ""),
        }
    for name in ("metric", "snapshot", "finding"):
        item = source.get(name)
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            data[name] = {
                "id": str(item["id"]),
                "report_id": str(item.get("report_id") or ""),
                "revision": int(item.get("revision") or 0),
                "state": str(item.get("state") or ""),
            }
    for name in ("history_snapshot_recorded", "metric_count", "snapshot_count", "finding_count"):
        if name in source:
            data[name] = source[name]
    return envelope(
        True,
        str(response.get("message") or "Đã lưu Analytics Workspace."),
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
            ("web-analytics-workspace:%", _idempotency_cutoff()),
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
                raise HTTPException(status_code=409, detail="Receipt Analytics Workspace không hợp lệ") from exc
            if not isinstance(receipt, dict):
                raise HTTPException(status_code=409, detail="Receipt Analytics Workspace không hợp lệ")
            return receipt
        count = conn.execute(
            "SELECT COUNT(*) FROM web_idempotency WHERE scope LIKE ?",
            (f"web-analytics-workspace:{account_id}:%",),
        ).fetchone()
        if int(count[0] or 0) >= MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT:
            return _guarded("Kho receipt thao tác tạm thời đang đầy. Vui lòng thử lại sau.", "WEB_ANALYTICS_IDEMPOTENCY_LIMIT")
        response = operation(conn)
        if response.get("ok") is True:
            receipt = _safe_receipt(response)
            conn.execute(
                "INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at) VALUES (?, ?, ?, ?, ?)",
                (scope, key, json.dumps(receipt, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
            )
            return receipt
        return response


def _report_snapshot(payload: ReportPayload, *, state: str = "draft") -> dict[str, Any]:
    return {
        "title": payload.title,
        "objective": payload.objective,
        "context_label": payload.context_label,
        "period_start": payload.period_start,
        "period_end": payload.period_end,
        "project_id": payload.project_id,
        "campaign_plan_id": payload.campaign_plan_id,
        "tags": list(payload.tags),
        "summary_note": payload.summary_note,
        "state": state,
        "restore_scope": "metadata_only",
    }


def _report_snapshot_from_row(row: tuple[Any, ...], *, state: str | None = None) -> dict[str, Any]:
    return {
        "title": str(row[3]),
        "objective": str(row[4]),
        "context_label": str(row[5]),
        "period_start": str(row[6]),
        "period_end": str(row[7]),
        "project_id": str(row[1]) if row[1] else None,
        "campaign_plan_id": str(row[2]) if row[2] else None,
        "tags": _decode_tags(row[9]),
        "summary_note": str(row[8]),
        "state": state or str(row[10]),
        "restore_scope": "metadata_only",
    }


def _report_payload_from_snapshot(snapshot: dict[str, Any]) -> ReportPayload:
    return ReportPayload(
        title=snapshot.get("title", ""), objective=snapshot.get("objective", ""),
        context_label=snapshot.get("context_label", ""), period_start=snapshot.get("period_start", ""),
        period_end=snapshot.get("period_end", ""), project_id=snapshot.get("project_id"),
        campaign_plan_id=snapshot.get("campaign_plan_id"), tags=snapshot.get("tags", []),
        summary_note=snapshot.get("summary_note", ""),
    )


def _metric_snapshot(payload: MetricPayload, *, state: str = "active", ordinal: int = 0) -> dict[str, Any]:
    return {
        "name": payload.name, "unit": payload.unit, "direction": payload.direction,
        "description": payload.description, "state": state, "ordinal": ordinal,
    }


def _snapshot_snapshot(payload: SnapshotPayload, *, state: str = "active") -> dict[str, Any]:
    return {
        "observed_on": payload.observed_on, "value": payload.value,
        "source_label": payload.source_label, "note": payload.note, "state": state,
    }


def _finding_snapshot(payload: FindingPayload, *, state: str = "active", ordinal: int = 0) -> dict[str, Any]:
    return {"kind": payload.kind, "body": payload.body, "state": state, "ordinal": ordinal}


def _report_row(conn: Any, *, report_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, project_id, campaign_plan_id, title, objective, context_label, period_start, period_end,
                  summary_note, tags_json, state, revision, created_at, updated_at, archived_at
           FROM web_analytics_reports WHERE id=? AND account_id=?""",
        (report_id, account_id),
    ).fetchone()


def _metric_row(conn: Any, *, report_id: str, metric_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, report_id, ordinal, name, unit, direction, description, state, revision, created_at, updated_at, archived_at
           FROM web_analytics_metrics WHERE id=? AND report_id=? AND account_id=?""",
        (metric_id, report_id, account_id),
    ).fetchone()


def _snapshot_row(conn: Any, *, report_id: str, metric_id: str, snapshot_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, report_id, metric_id, observed_on, value_decimal, source_label, note, state, revision,
                  created_at, updated_at, archived_at
           FROM web_analytics_snapshots WHERE id=? AND report_id=? AND metric_id=? AND account_id=?""",
        (snapshot_id, report_id, metric_id, account_id),
    ).fetchone()


def _finding_row(conn: Any, *, report_id: str, finding_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, report_id, ordinal, kind, body, state, revision, created_at, updated_at, archived_at
           FROM web_analytics_findings WHERE id=? AND report_id=? AND account_id=?""",
        (finding_id, report_id, account_id),
    ).fetchone()


def _report_not_found() -> dict[str, Any]:
    return _guarded("Không tìm thấy báo cáo thuộc Web account hiện tại.", "WEB_ANALYTICS_REPORT_NOT_FOUND")


def _metric_not_found() -> dict[str, Any]:
    return _guarded("Không tìm thấy metric thuộc báo cáo hiện tại.", "WEB_ANALYTICS_METRIC_NOT_FOUND")


def _snapshot_not_found() -> dict[str, Any]:
    return _guarded("Không tìm thấy snapshot thuộc metric hiện tại.", "WEB_ANALYTICS_SNAPSHOT_NOT_FOUND")


def _finding_not_found() -> dict[str, Any]:
    return _guarded("Không tìm thấy nhận định thuộc báo cáo hiện tại.", "WEB_ANALYTICS_FINDING_NOT_FOUND")


def _revision_conflict() -> dict[str, Any]:
    return _guarded("Dữ liệu đã thay đổi ở một phiên khác. Hãy tải lại trước khi tiếp tục.", "WEB_ANALYTICS_REVISION_CONFLICT")


def _report_writable(report: tuple[Any, ...]) -> dict[str, Any] | None:
    if str(report[10]) != "draft":
        return _guarded("Báo cáo chỉ có thể sửa dữ liệu khi ở trạng thái bản nháp. Hãy đưa về bản nháp trước.", "WEB_ANALYTICS_REVIEW_LOCKED")
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


def _campaign_reference(conn: Any, *, account_id: str, campaign_id: str | None, active: bool = True) -> dict[str, Any] | None:
    if not campaign_id:
        return None
    clause = " AND approval_status!='archived'" if active else ""
    row = conn.execute(
        f"SELECT id, title, approval_status, updated_at FROM web_campaign_plans WHERE id=? AND account_id=?{clause}",
        (campaign_id, account_id),
    ).fetchone()
    if not row:
        return None
    return {"id": str(row[0]), "title": str(row[1]), "state": str(row[2]), "updated_at": str(row[3])}


def _validate_references(conn: Any, *, account_id: str, snapshot: dict[str, Any]) -> None:
    project_id = snapshot.get("project_id")
    if project_id and not _project_reference(conn, account_id=account_id, project_id=str(project_id), active=True):
        raise HTTPException(status_code=422, detail="Project reference không thuộc account hiện tại hoặc đã archive")
    campaign_id = snapshot.get("campaign_plan_id")
    if campaign_id and not _campaign_reference(conn, account_id=account_id, campaign_id=str(campaign_id), active=True):
        raise HTTPException(status_code=422, detail="Campaign plan reference không thuộc account hiện tại hoặc đã archive")


def _report_public(row: tuple[Any, ...], *, metric_count: int = 0, snapshot_count: int = 0, finding_count: int = 0, include_content: bool = False) -> dict[str, Any]:
    item = {
        "id": str(row[0]), "project_id": str(row[1]) if row[1] else None,
        "campaign_plan_id": str(row[2]) if row[2] else None, "title": str(row[3]),
        "objective_excerpt": _excerpt(row[4]), "context_label": str(row[5]),
        "period_start": str(row[6]), "period_end": str(row[7]), "tags": _decode_tags(row[9]),
        "state": str(row[10]), "revision": int(row[11]), "created_at": str(row[12]),
        "updated_at": str(row[13]), "archived_at": str(row[14]) if row[14] else None,
        "metric_count": int(metric_count), "snapshot_count": int(snapshot_count), "finding_count": int(finding_count),
        "data_origin": "user_supplied_only", "platform_data_verified": False,
    }
    if include_content:
        item["objective"] = str(row[4])
        item["summary_note"] = str(row[8])
    return item


def _metric_public(row: tuple[Any, ...], *, include_content: bool = True) -> dict[str, Any]:
    item = {
        "id": str(row[0]), "report_id": str(row[1]), "ordinal": int(row[2]), "name": str(row[3]),
        "unit": str(row[4]), "direction": str(row[5]), "state": str(row[7]), "revision": int(row[8]),
        "created_at": str(row[9]), "updated_at": str(row[10]), "archived_at": str(row[11]) if row[11] else None,
    }
    if include_content:
        item["description"] = str(row[6])
    return item


def _snapshot_public(row: tuple[Any, ...], *, include_content: bool = True) -> dict[str, Any]:
    item = {
        "id": str(row[0]), "report_id": str(row[1]), "metric_id": str(row[2]), "observed_on": str(row[3]),
        "value": str(row[4]), "state": str(row[7]), "revision": int(row[8]), "created_at": str(row[9]),
        "updated_at": str(row[10]), "archived_at": str(row[11]) if row[11] else None,
        "source_kind": "manual_entry", "platform_data_verified": False,
    }
    if include_content:
        item["source_label"] = str(row[5])
        item["note"] = str(row[6])
    return item


def _finding_public(row: tuple[Any, ...], *, include_content: bool = True) -> dict[str, Any]:
    item = {
        "id": str(row[0]), "report_id": str(row[1]), "ordinal": int(row[2]), "kind": str(row[3]),
        "state": str(row[5]), "revision": int(row[6]), "created_at": str(row[7]),
        "updated_at": str(row[8]), "archived_at": str(row[9]) if row[9] else None,
        "ai_recommendation_created": False,
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
        "state": str(snapshot.get("state", "draft")), "restore_scope": "metadata_only",
        "created_at": str(row[2]),
    }


def _decimal_text(value: Decimal) -> str:
    text = format(value.normalize(), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _metric_comparison(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    active = [item for item in snapshots if item.get("state") == "active"]
    active.sort(key=lambda item: (str(item.get("observed_on") or ""), str(item.get("id") or "")), reverse=True)
    if not active:
        return {"latest_value": None, "previous_value": None, "delta": None, "change_percent": None, "sample_count": 0}
    latest = Decimal(str(active[0]["value"]))
    previous = Decimal(str(active[1]["value"])) if len(active) > 1 else None
    delta = latest - previous if previous is not None else None
    percent = (delta / previous * Decimal("100")) if previous not in {None, Decimal("0")} and delta is not None else None
    return {
        "latest_value": _decimal_text(latest), "previous_value": _decimal_text(previous) if previous is not None else None,
        "delta": _decimal_text(delta) if delta is not None else None,
        "change_percent": _decimal_text(percent) if percent is not None else None,
        "sample_count": len(active),
    }


def _next_ordinal(conn: Any, *, table: str, report_id: str, account_id: str, archived: bool = False) -> int:
    state = "archived" if archived else "active"
    row = conn.execute(
        f"SELECT COALESCE(MAX(ordinal), 0) FROM {table} WHERE report_id=? AND account_id=? AND state=?",
        (report_id, account_id, state),
    ).fetchone()
    value = int(row[0] or 0) + 1
    return max(ARCHIVED_ORDINAL_BASE, value) if archived else value


def _trim_versions(conn: Any, *, table: str, foreign_column: str, entity_id: str, account_id: str, limit: int) -> None:
    rows = conn.execute(
        f"SELECT id FROM {table} WHERE {foreign_column}=? AND account_id=? ORDER BY revision DESC, id DESC LIMIT -1 OFFSET ?",
        (entity_id, account_id, limit),
    ).fetchall()
    if rows:
        conn.executemany(f"DELETE FROM {table} WHERE id=?", [(str(row[0]),) for row in rows])


def _insert_report_version(conn: Any, *, report_id: str, account_id: str, revision: int, snapshot: dict[str, Any], now: str) -> None:
    conn.execute(
        """INSERT INTO web_analytics_report_versions (id, report_id, account_id, revision, snapshot_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), report_id, account_id, revision, json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), now),
    )
    _trim_versions(conn, table="web_analytics_report_versions", foreign_column="report_id", entity_id=report_id, account_id=account_id, limit=MAX_REPORT_VERSIONS)


def _insert_metric_version(conn: Any, *, metric_id: str, account_id: str, revision: int, snapshot: dict[str, Any], now: str) -> None:
    conn.execute(
        """INSERT INTO web_analytics_metric_versions (id, metric_id, account_id, revision, snapshot_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), metric_id, account_id, revision, json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), now),
    )
    _trim_versions(conn, table="web_analytics_metric_versions", foreign_column="metric_id", entity_id=metric_id, account_id=account_id, limit=MAX_ENTITY_VERSIONS)


def _insert_snapshot_version(conn: Any, *, snapshot_id: str, account_id: str, revision: int, snapshot: dict[str, Any], now: str) -> None:
    conn.execute(
        """INSERT INTO web_analytics_snapshot_versions (id, snapshot_id, account_id, revision, snapshot_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), snapshot_id, account_id, revision, json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), now),
    )
    _trim_versions(conn, table="web_analytics_snapshot_versions", foreign_column="snapshot_id", entity_id=snapshot_id, account_id=account_id, limit=MAX_ENTITY_VERSIONS)


def _insert_finding_version(conn: Any, *, finding_id: str, account_id: str, revision: int, snapshot: dict[str, Any], now: str) -> None:
    conn.execute(
        """INSERT INTO web_analytics_finding_versions (id, finding_id, account_id, revision, snapshot_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), finding_id, account_id, revision, json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), now),
    )
    _trim_versions(conn, table="web_analytics_finding_versions", foreign_column="finding_id", entity_id=finding_id, account_id=account_id, limit=MAX_ENTITY_VERSIONS)


def _event(conn: Any, *, account_id: str, report_id: str, entity_type: str, entity_id: str | None, action: str, revision: int) -> None:
    conn.execute(
        """INSERT INTO web_analytics_workspace_events
           (id, account_id, report_id, entity_type, entity_id, action, revision, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), account_id, report_id, entity_type, entity_id, action, revision, utc_now()),
    )


def _audit(conn: Any, *, request: Request, account: dict, action: str, target: str, detail: str) -> None:
    _record_audit(
        conn, account_id=str(account["id"]), canonical_user_id=None, action=action,
        request_id=_request_id(request), target=target, detail=detail[:320],
    )


def _touch_report(conn: Any, *, report_id: str, account_id: str, now: str) -> None:
    conn.execute("UPDATE web_analytics_reports SET updated_at=? WHERE id=? AND account_id=?", (now, report_id, account_id))


def _report_counts(conn: Any, *, report_id: str, account_id: str) -> tuple[int, int, int]:
    metrics = conn.execute("SELECT COUNT(*) FROM web_analytics_metrics WHERE report_id=? AND account_id=? AND state='active'", (report_id, account_id)).fetchone()
    snapshots = conn.execute("SELECT COUNT(*) FROM web_analytics_snapshots WHERE report_id=? AND account_id=? AND state='active'", (report_id, account_id)).fetchone()
    findings = conn.execute("SELECT COUNT(*) FROM web_analytics_findings WHERE report_id=? AND account_id=? AND state='active'", (report_id, account_id)).fetchone()
    return int(metrics[0] or 0), int(snapshots[0] or 0), int(findings[0] or 0)


def _references_listing(conn: Any, *, account_id: str) -> dict[str, Any]:
    projects = conn.execute(
        "SELECT id, title, updated_at FROM web_projects WHERE account_id=? AND state='active' ORDER BY updated_at DESC, id DESC LIMIT 100",
        (account_id,),
    ).fetchall()
    campaigns = conn.execute(
        """SELECT id, title, objective, approval_status, updated_at FROM web_campaign_plans
           WHERE account_id=? AND approval_status!='archived' ORDER BY updated_at DESC, id DESC LIMIT 100""",
        (account_id,),
    ).fetchall()
    return {
        "projects": [{"id": str(row[0]), "title": str(row[1]), "updated_at": str(row[2])} for row in projects],
        "campaign_plans": [
            {"id": str(row[0]), "title": str(row[1]), "objective": _excerpt(row[2], 180), "state": str(row[3]), "updated_at": str(row[4])}
            for row in campaigns
        ],
        **_boundary(),
    }


def _report_detail(conn: Any, *, report_id: str, account_id: str) -> dict[str, Any] | None:
    report = _report_row(conn, report_id=report_id, account_id=account_id)
    if not report:
        return None
    metrics_rows = conn.execute(
        """SELECT id, report_id, ordinal, name, unit, direction, description, state, revision, created_at, updated_at, archived_at
           FROM web_analytics_metrics WHERE report_id=? AND account_id=? ORDER BY state='active' DESC, ordinal ASC, created_at ASC LIMIT ?""",
        (report_id, account_id, MAX_METRICS_PER_REPORT * 2),
    ).fetchall()
    snapshots_rows = conn.execute(
        """SELECT id, report_id, metric_id, observed_on, value_decimal, source_label, note, state, revision, created_at, updated_at, archived_at
           FROM web_analytics_snapshots WHERE report_id=? AND account_id=? ORDER BY observed_on DESC, created_at DESC LIMIT ?""",
        (report_id, account_id, MAX_METRICS_PER_REPORT * MAX_SNAPSHOTS_PER_METRIC),
    ).fetchall()
    findings_rows = conn.execute(
        """SELECT id, report_id, ordinal, kind, body, state, revision, created_at, updated_at, archived_at
           FROM web_analytics_findings WHERE report_id=? AND account_id=? ORDER BY state='active' DESC, ordinal ASC, created_at ASC LIMIT ?""",
        (report_id, account_id, MAX_FINDINGS_PER_REPORT * 2),
    ).fetchall()
    versions_rows = conn.execute(
        """SELECT revision, snapshot_json, created_at FROM web_analytics_report_versions
           WHERE report_id=? AND account_id=? ORDER BY revision DESC LIMIT ?""",
        (report_id, account_id, MAX_REPORT_VERSIONS),
    ).fetchall()
    events_rows = conn.execute(
        """SELECT action, entity_type, entity_id, revision, created_at FROM web_analytics_workspace_events
           WHERE report_id=? AND account_id=? ORDER BY created_at DESC, id DESC LIMIT ?""",
        (report_id, account_id, MAX_EVENT_LIMIT),
    ).fetchall()
    metrics = [_metric_public(tuple(row)) for row in metrics_rows]
    snapshots = [_snapshot_public(tuple(row)) for row in snapshots_rows]
    findings = [_finding_public(tuple(row)) for row in findings_rows]
    by_metric: dict[str, list[dict[str, Any]]] = {}
    for item in snapshots:
        by_metric.setdefault(str(item["metric_id"]), []).append(item)
    comparisons = {
        str(metric["id"]): _metric_comparison(by_metric.get(str(metric["id"]), [])) for metric in metrics
    }
    metric_count, snapshot_count, finding_count = _report_counts(conn, report_id=report_id, account_id=account_id)
    snapshot = _report_snapshot_from_row(report)
    return {
        "report": _report_public(report, metric_count=metric_count, snapshot_count=snapshot_count, finding_count=finding_count, include_content=True),
        "metrics": metrics, "snapshots": snapshots, "findings": findings,
        "comparisons": comparisons, "versions": [_version_public(tuple(row)) for row in versions_rows],
        "events": [
            {"action": str(row[0]), "entity_type": str(row[1]), "entity_id": str(row[2]) if row[2] else None,
             "revision": int(row[3]), "created_at": str(row[4])}
            for row in events_rows
        ],
        "references": {
            "project": _project_reference(conn, account_id=account_id, project_id=snapshot.get("project_id"), active=False),
            "campaign_plan": _campaign_reference(conn, account_id=account_id, campaign_id=snapshot.get("campaign_plan_id"), active=False),
        },
        **_boundary(),
    }


def _insert_report(conn: Any, *, report_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str) -> None:
    conn.execute(
        """INSERT INTO web_analytics_reports
           (id, account_id, project_id, campaign_plan_id, title, objective, context_label, period_start, period_end,
            summary_note, tags_json, state, revision, created_at, updated_at, archived_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)""",
        (
            report_id, account_id, snapshot["project_id"], snapshot["campaign_plan_id"], snapshot["title"],
            snapshot["objective"], snapshot["context_label"], snapshot["period_start"], snapshot["period_end"],
            snapshot["summary_note"], json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")),
            snapshot["state"], revision, now, now,
        ),
    )


def _write_report(
    conn: Any, *, report_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str, archived_at: str | None
) -> None:
    conn.execute(
        """UPDATE web_analytics_reports
           SET project_id=?, campaign_plan_id=?, title=?, objective=?, context_label=?, period_start=?, period_end=?,
               summary_note=?, tags_json=?, state=?, revision=?, updated_at=?, archived_at=?
           WHERE id=? AND account_id=?""",
        (
            snapshot["project_id"], snapshot["campaign_plan_id"], snapshot["title"], snapshot["objective"],
            snapshot["context_label"], snapshot["period_start"], snapshot["period_end"], snapshot["summary_note"],
            json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")), snapshot["state"], revision,
            now, archived_at, report_id, account_id,
        ),
    )


def _validate_snapshot_window(report: tuple[Any, ...], observed_on: str) -> None:
    if observed_on < str(report[6]) or observed_on > str(report[7]):
        raise HTTPException(status_code=422, detail="Ngày quan sát phải nằm trong khoảng thời gian của báo cáo")


def _active_snapshot_collision(
    conn: Any, *, metric_id: str, observed_on: str, account_id: str, exclude_id: str | None = None
) -> bool:
    query = "SELECT id FROM web_analytics_snapshots WHERE metric_id=? AND observed_on=? AND account_id=? AND state='active'"
    values: list[Any] = [metric_id, observed_on, account_id]
    if exclude_id:
        query += " AND id<>?"
        values.append(exclude_id)
    return conn.execute(query, values).fetchone() is not None


def _report_lifecycle_allowed(current: str, target: str) -> bool:
    transitions = {
        "draft": {"review", "archived"},
        "review": {"draft", "finalized", "archived"},
        "finalized": {"draft", "review", "archived"},
        "archived": {"draft"},
    }
    return target in transitions.get(current, set())


def _manual_csv_export_error(message: str, code: str, *, status_code: int) -> Response:
    """Return a private JSON guard instead of a partial/broken attachment."""

    return Response(
        content=json.dumps(_guarded(message, code), ensure_ascii=False, separators=(",", ":")),
        media_type="application/json",
        status_code=status_code,
        headers={
            "Cache-Control": "no-store, private",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "sandbox",
        },
    )


def _csv_cell(value: Any) -> str:
    """Make every legacy/manual cell inert when opened in a spreadsheet.

    The Analytics authoring validators block most formula prefixes, but an
    attachment must defend independently because legacy rows and multiline
    narrative fields can still begin with a spreadsheet expression.  Prefix
    an apostrophe before *any* leading whitespace + formula sigil; CSV quoting
    alone does not stop Excel/Sheets formula evaluation.
    """

    text = "" if value is None else str(value)
    return f"'{text}" if CSV_FORMULA_PREFIX_PATTERN.search(text) else text


def _manual_csv_bytes(
    *,
    report: tuple[Any, ...],
    metrics: Iterable[tuple[Any, ...]],
    snapshots: Iterable[tuple[Any, ...]],
    findings: Iterable[tuple[Any, ...]],
    row_count: int,
    exported_at: str,
) -> tuple[bytes, int] | None:
    """Build one bounded, complete manual-report CSV in memory.

    ``None`` means the full attachment crossed a hard row/byte bound.  The
    caller must return a guarded error rather than emitting a partial report;
    a partial CSV would look complete to a customer and undermine the review
    record.  Only the current *active* manual records are serialized.  UUIDs,
    account identity, campaign/project references, versions, events, audit
    records, paths and all external authority fields remain server-side.
    """

    if row_count > MAX_MANUAL_CSV_EXPORT_ROWS:
        return None

    report_values = {
        "title": str(report[3]),
        "state": str(report[10]),
        "revision": int(report[11]),
        "period_start": str(report[6]),
        "period_end": str(report[7]),
        "context_label": str(report[5]),
        "tags": ", ".join(_decode_tags(report[9])),
        "objective": str(report[4]),
        "summary_note": str(report[8]),
    }
    columns = (
        "schema", "exported_at", "record_type", "report_title", "report_state", "report_revision",
        "period_start", "period_end", "context_label", "tags", "objective", "summary_note",
        "metric_ordinal", "metric_name", "metric_unit", "metric_direction", "metric_description", "metric_state",
        "observed_on", "metric_value", "source_label", "snapshot_note", "snapshot_state",
        "finding_ordinal", "finding_kind", "finding_body", "finding_state",
    )
    # Keep the live serializer itself within the byte bound.  Checking only
    # after a large StringIO was complete would still let a legacy report
    # allocate far beyond the advertised attachment limit in process memory.
    buffer = io.BytesIO()
    buffer.write(b"\xef\xbb\xbf")
    text_buffer = io.TextIOWrapper(buffer, encoding="utf-8", newline="", write_through=True)
    writer = csv.writer(text_buffer, lineterminator="\r\n")
    writer.writerow(columns)
    if buffer.tell() > MAX_MANUAL_CSV_EXPORT_BYTES:
        return None

    def write(record_type: str, *values: Any) -> bool:
        writer.writerow([_csv_cell(value) for value in (MANUAL_CSV_SCHEMA, exported_at, record_type, *values)])
        return buffer.tell() <= MAX_MANUAL_CSV_EXPORT_BYTES

    report_prefix = (
        report_values["title"], report_values["state"], report_values["revision"],
        report_values["period_start"], report_values["period_end"], report_values["context_label"],
        report_values["tags"], report_values["objective"], report_values["summary_note"],
    )
    blanks = ("",) * 15
    if not write("report", *report_prefix, *blanks):
        return None
    for metric in metrics:
        metric_values = (
            int(metric[0]), str(metric[1]), str(metric[2]), str(metric[3]), str(metric[4]), str(metric[5]),
        )
        if not write("metric", *report_prefix, *metric_values, *(("",) * 9)):
            return None
    for snapshot in snapshots:
        metric_values = (
            int(snapshot[0]), str(snapshot[1]), str(snapshot[2]), str(snapshot[3]), str(snapshot[4]), str(snapshot[5]),
        )
        snapshot_values = (str(snapshot[6]), str(snapshot[7]), str(snapshot[8]), str(snapshot[9]), str(snapshot[10]))
        if not write("snapshot", *report_prefix, *metric_values, *snapshot_values, *(("",) * 4)):
            return None
    for finding in findings:
        finding_values = (int(finding[0]), str(finding[1]), str(finding[2]), str(finding[3]))
        if not write("finding", *report_prefix, *(("",) * 11), *finding_values):
            return None

    text_buffer.flush()
    content = buffer.getvalue()
    return (content, row_count) if len(content) <= MAX_MANUAL_CSV_EXPORT_BYTES else None


def _manual_csv_records(
    conn: Any, *, report_id: str, account_id: str
) -> tuple[int, Iterable[tuple[Any, ...]], Iterable[tuple[Any, ...]], Iterable[tuple[Any, ...]]] | None:
    """Preflight and stream active, owner-scoped records without ``fetchall``.

    A completed attachment may be at most 32,000 rows, yet legacy data can
    predate application-level creation limits. Count the exact active query
    shapes first, refusing oversized data before any narrative rows are read.
    The three cursors remain lazy so the byte-capped serializer never holds a
    30k-row report (or a malicious legacy equivalent) in process memory.
    """

    counts = conn.execute(
        """SELECT
               (SELECT COUNT(*) FROM web_analytics_metrics
                WHERE report_id=? AND account_id=? AND state='active'),
               (SELECT COUNT(*)
                FROM web_analytics_snapshots s
                INNER JOIN web_analytics_metrics m
                  ON m.id=s.metric_id AND m.report_id=s.report_id AND m.account_id=s.account_id
                WHERE s.report_id=? AND s.account_id=? AND s.state='active' AND m.state='active'),
               (SELECT COUNT(*) FROM web_analytics_findings
                WHERE report_id=? AND account_id=? AND state='active')""",
        (report_id, account_id, report_id, account_id, report_id, account_id),
    ).fetchone()
    row_count = 1 + sum(int(value or 0) for value in (counts or (0, 0, 0)))
    if row_count > MAX_MANUAL_CSV_EXPORT_ROWS:
        return None

    metrics = conn.execute(
        """SELECT ordinal, name, unit, direction, description, state
           FROM web_analytics_metrics
           WHERE report_id=? AND account_id=? AND state='active'
           ORDER BY ordinal ASC, id ASC""",
        (report_id, account_id),
    )
    snapshots = conn.execute(
        """SELECT m.ordinal, m.name, m.unit, m.direction, m.description, m.state,
                      s.observed_on, s.value_decimal, s.source_label, s.note, s.state
           FROM web_analytics_snapshots s
           INNER JOIN web_analytics_metrics m
             ON m.id=s.metric_id AND m.report_id=s.report_id AND m.account_id=s.account_id
           WHERE s.report_id=? AND s.account_id=? AND s.state='active' AND m.state='active'
           ORDER BY m.ordinal ASC, s.observed_on ASC, s.id ASC""",
        (report_id, account_id),
    )
    findings = conn.execute(
        """SELECT ordinal, kind, body, state
           FROM web_analytics_findings
           WHERE report_id=? AND account_id=? AND state='active'
           ORDER BY ordinal ASC, id ASC""",
        (report_id, account_id),
    )
    return row_count, metrics, snapshots, findings


@router.get("/summary")
async def analytics_workspace_summary(account: dict = Depends(require_account)):
    _require_enabled()
    ensure_copyfast_schema()
    account_id = str(account["id"])
    with read_transaction() as conn:
        report_rows = conn.execute(
            "SELECT state, COUNT(*) FROM web_analytics_reports WHERE account_id=? GROUP BY state", (account_id,)
        ).fetchall()
        metric_count = conn.execute(
            "SELECT COUNT(*) FROM web_analytics_metrics WHERE account_id=? AND state='active'", (account_id,)
        ).fetchone()
        snapshot_count = conn.execute(
            "SELECT COUNT(*) FROM web_analytics_snapshots WHERE account_id=? AND state='active'", (account_id,)
        ).fetchone()
        finding_count = conn.execute(
            "SELECT COUNT(*) FROM web_analytics_findings WHERE account_id=? AND state='active'", (account_id,)
        ).fetchone()
    counts = {str(row[0]): int(row[1] or 0) for row in report_rows}
    return envelope(
        True,
        "Đã tải tổng quan số liệu do Web account tự nhập.",
        data={
            "reports": {state: counts.get(state, 0) for state in REPORT_STATES} | {"total": sum(counts.values()), "limit_per_account": MAX_REPORTS_PER_ACCOUNT},
            "metrics": {"active": int(metric_count[0] or 0), "limit_per_report": MAX_METRICS_PER_REPORT},
            "snapshots": {"active": int(snapshot_count[0] or 0), "limit_per_metric": MAX_SNAPSHOTS_PER_METRIC},
            "findings": {"active": int(finding_count[0] or 0), "limit_per_report": MAX_FINDINGS_PER_REPORT},
            "notice": "Mọi số liệu là do bạn nhập và chỉ được tính cục bộ; không phải dữ liệu nền tảng, Bot hay báo cáo doanh thu canonical.",
            **_boundary(),
        },
        status_name="read_only",
    )


@router.get("/policy")
async def analytics_workspace_policy(account: dict = Depends(require_account)):
    _require_enabled()
    return envelope(
        True,
        "Analytics Workspace chỉ lưu metric, snapshot và nhận định do bạn tự nhập.",
        data={
            "allowed": [
                "manual_metric_definition", "manual_snapshot", "deterministic_comparison", "human_authored_finding",
                "web_project_reference", "web_campaign_reference", "finalized_manual_csv_export",
            ],
            "guarded": [
                "social_platform_api", "live_analytics", "bot_report", "canonical_campaign_report", "provider_analytics",
                "ai_insight", "revenue", "wallet", "payment", "job", "publish", "csv_import",
                "pdf_delivery", "stored_report_file_export",
            ],
            "notice": "Nhãn nguồn chỉ là mô tả do bạn tự ghi; Web không kết nối, đồng bộ hoặc xác minh dữ liệu của bất kỳ nền tảng nào. Khi feature flag riêng được bật, chỉ report finalized mới được xuất CSV attachment tạm thời từ dữ liệu Web tự nhập; đó không phải CSV Campaign/Bot canonical.",
            **_boundary(),
        },
        status_name="read_only",
    )


@router.get("/references")
async def analytics_workspace_references(account: dict = Depends(require_account)):
    _require_enabled()
    ensure_copyfast_schema()
    with read_transaction() as conn:
        data = _references_listing(conn, account_id=str(account["id"]))
    return envelope(True, "Đã tải Project và Campaign Planner thuộc Web account hiện tại.", data=data, status_name="read_only")


@router.get("/reports")
async def analytics_workspace_reports(
    state: str = "all", q: str = "", limit: int = 50, offset: int = 0, account: dict = Depends(require_account)
):
    _require_enabled()
    ensure_copyfast_schema()
    normalized_state = str(state or "all").strip().lower()
    if normalized_state not in {"all", *REPORT_STATES}:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái không hợp lệ")
    normalized_q = re.sub(r"\s+", " ", str(q or "")).strip()
    if len(normalized_q) > 100 or UNSAFE_CONTROL_PATTERN.search(normalized_q) or FORMULA_PREFIX_PATTERN.search(normalized_q) or _sensitive_text(normalized_q):
        raise HTTPException(status_code=422, detail="Từ khoá tìm kiếm không hợp lệ")
    safe_limit = min(max(int(limit or 50), 1), MAX_LIST_LIMIT)
    clauses = ["r.account_id=?"]
    values: list[Any] = [str(account["id"])]
    if normalized_state != "all":
        clauses.append("r.state=?")
        values.append(normalized_state)
    if normalized_q:
        pattern = "%" + normalized_q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        clauses.append("(r.title LIKE ? ESCAPE '\\' OR r.objective LIKE ? ESCAPE '\\' OR r.tags_json LIKE ? ESCAPE '\\')")
        values.extend([pattern, pattern, pattern])
    with read_transaction() as conn:
        total_row = conn.execute(f"SELECT COUNT(*) FROM web_analytics_reports r WHERE {' AND '.join(clauses)}", values).fetchone()
        total = int(total_row[0] or 0)
        requested_offset = max(int(offset or 0), 0)
        last_page_offset = max(0, ((total - 1) // safe_limit) * safe_limit) if total else 0
        safe_offset = min(requested_offset, last_page_offset)
        rows = conn.execute(
            f"""SELECT r.id, r.project_id, r.campaign_plan_id, r.title, r.objective, r.context_label, r.period_start, r.period_end,
                       r.summary_note, r.tags_json, r.state, r.revision, r.created_at, r.updated_at, r.archived_at,
                       (SELECT COUNT(*) FROM web_analytics_metrics m WHERE m.report_id=r.id AND m.account_id=r.account_id AND m.state='active'),
                       (SELECT COUNT(*) FROM web_analytics_snapshots s WHERE s.report_id=r.id AND s.account_id=r.account_id AND s.state='active'),
                       (SELECT COUNT(*) FROM web_analytics_findings f WHERE f.report_id=r.id AND f.account_id=r.account_id AND f.state='active')
                FROM web_analytics_reports r WHERE {' AND '.join(clauses)}
                ORDER BY r.updated_at DESC, r.id DESC LIMIT ? OFFSET ?""",
            [*values, safe_limit, safe_offset],
        ).fetchall()
        items = [_report_public(tuple(row[:15]), metric_count=int(row[15] or 0), snapshot_count=int(row[16] or 0), finding_count=int(row[17] or 0)) for row in rows]
    returned = len(items)
    has_more = safe_offset + returned < total
    return envelope(
        True,
        "Đã tải thư viện báo cáo Web-owned.",
        data={
            "items": items, "filter": {"state": normalized_state, "q": normalized_q},
            "pagination": {"total": total, "limit": safe_limit, "offset": safe_offset, "returned": returned, "has_more": has_more,
                           "next_offset": safe_offset + returned if has_more else None,
                           "previous_offset": max(0, safe_offset - safe_limit) if safe_offset > 0 else None},
            **_boundary(),
        },
        status_name="read_only",
    )


@router.get("/reports/{report_id}")
async def analytics_workspace_detail(report_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    try:
        resolved = _uuid(report_id, label="Report ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ensure_copyfast_schema()
    with read_transaction() as conn:
        data = _report_detail(conn, report_id=resolved, account_id=str(account["id"]))
    if not data:
        return _report_not_found()
    return envelope(True, "Đã tải báo cáo số liệu Web-owned.", data=data, status_name="read_only")


@router.post("/reports/{report_id}/export.csv")
async def analytics_workspace_manual_csv_export(
    report_id: str, payload: ManualCsvExportRequest, request: Request, account: dict = Depends(require_csrf)
):
    """Return a bounded manual-only CSV attachment for one finalized report.

    The server re-reads every row from the signed owner's database; browser
    detail state is never used as source data.  This is intentionally not a
    Bot campaign report, platform export, asset, job, stored file or delivery
    record.  Finalized reports are child-write locked, and the second revision
    check below closes a lifecycle change between initial read and attachment.
    """

    _require_enabled()
    _require_manual_csv_export_enabled()
    try:
        resolved = _uuid(report_id, label="Report ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ensure_copyfast_schema()
    account_id = str(account["id"])
    row_count = 0
    with read_transaction() as conn:
        report = _report_row(conn, report_id=resolved, account_id=account_id)
        if not report:
            return _manual_csv_export_error(
                "Không tìm thấy báo cáo thuộc Web account hiện tại.",
                "WEB_ANALYTICS_REPORT_NOT_FOUND",
                status_code=404,
            )
        if int(report[11]) != payload.expected_revision:
            return _manual_csv_export_error(
                "Dữ liệu đã thay đổi ở một phiên khác. Hãy tải lại trước khi xuất CSV.",
                "WEB_ANALYTICS_REVISION_CONFLICT",
                status_code=409,
            )
        if str(report[10]) != "finalized":
            return _manual_csv_export_error(
                "Chỉ report đã chốt nội bộ mới có thể xuất CSV dữ liệu Web thủ công.",
                "WEB_ANALYTICS_MANUAL_CSV_FINALIZED_REQUIRED",
                status_code=409,
            )
        records = _manual_csv_records(conn, report_id=resolved, account_id=account_id)
        if records is None:
            serialized = None
        else:
            row_count, metrics, snapshots, findings = records
            serialized = _manual_csv_bytes(
                report=report,
                metrics=metrics,
                snapshots=snapshots,
                findings=findings,
                row_count=row_count,
                exported_at=utc_now(),
            )
    if serialized is None:
        return _manual_csv_export_error(
            "Báo cáo vượt giới hạn CSV an toàn. Không có file một phần được tạo; hãy giảm dữ liệu active rồi thử lại.",
            "WEB_ANALYTICS_MANUAL_CSV_EXPORT_LIMIT",
            status_code=413,
        )
    content, row_count = serialized

    # Do not release an attachment after its lifecycle/revision changed.
    # Child data cannot be written while finalized, so this recheck proves the
    # complete read above is still the same signed owner's final review.
    try:
        # The audit/recheck is observability rather than an account mutation.
        # Do not let an unrelated long SQLite writer turn a CSV click into a
        # 30-second wait or an unhandled failure. If this short transaction
        # cannot prove-and-audit the same finalized revision, release no file.
        with best_effort_transaction(timeout_seconds=0.25) as conn:
            current = _report_row(conn, report_id=resolved, account_id=account_id)
            if not current:
                return _manual_csv_export_error(
                    "Không tìm thấy báo cáo thuộc Web account hiện tại.",
                    "WEB_ANALYTICS_REPORT_NOT_FOUND",
                    status_code=404,
                )
            if int(current[11]) != payload.expected_revision:
                return _manual_csv_export_error(
                    "Dữ liệu đã thay đổi ở một phiên khác. Hãy tải lại trước khi xuất CSV.",
                    "WEB_ANALYTICS_REVISION_CONFLICT",
                    status_code=409,
                )
            if str(current[10]) != "finalized":
                return _manual_csv_export_error(
                    "Chỉ report đã chốt nội bộ mới có thể xuất CSV dữ liệu Web thủ công.",
                    "WEB_ANALYTICS_MANUAL_CSV_FINALIZED_REQUIRED",
                    status_code=409,
                )
            _audit(
                conn,
                request=request,
                account=account,
                action="analytics_report_manual_csv_exported",
                target=resolved,
                detail=f"manual_csv;revision={payload.expected_revision};rows={row_count};bytes={len(content)}",
            )
    except sqlite3.OperationalError:
        # A bounded lock refusal is an expected protection response, not an
        # application crash. Keep it out of the Web reliability incident feed
        # that records unexpected 5xx responses after this router returns.
        request.state.reliability_expected_failure = True
        return _manual_csv_export_error(
            "Hệ thống đang đồng bộ dữ liệu. CSV chưa được xác nhận audit; vui lòng thử lại sau ít phút.",
            "WEB_ANALYTICS_MANUAL_CSV_RETRY_LATER",
            status_code=503,
        )

    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Length": str(len(content)),
            "Content-Disposition": 'attachment; filename="toan-aas-manual-analytics.csv"',
            "Cache-Control": "no-store, private",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "sandbox",
            "Cross-Origin-Resource-Policy": "same-origin",
        },
    )


@router.post("/reports")
async def analytics_workspace_create_report(
    payload: ReportCreateRequest, request: Request, account: dict = Depends(require_csrf)
):
    _require_enabled()
    account_id = str(account["id"])
    snapshot = _report_snapshot(payload)
    fingerprint = _fingerprint({"action": "create_report", "payload": snapshot})

    def operation(conn: Any) -> dict[str, Any]:
        total = conn.execute("SELECT COUNT(*) FROM web_analytics_reports WHERE account_id=?", (account_id,)).fetchone()
        if int(total[0] or 0) >= MAX_REPORTS_PER_ACCOUNT:
            return _guarded("Đã đạt giới hạn lưu trữ báo cáo của account.", "WEB_ANALYTICS_REPORT_LIMIT")
        _validate_references(conn, account_id=account_id, snapshot=snapshot)
        now = utc_now()
        report_id = str(uuid.uuid4())
        _insert_report(conn, report_id=report_id, account_id=account_id, snapshot=snapshot, revision=1, now=now)
        _insert_report_version(conn, report_id=report_id, account_id=account_id, revision=1, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, report_id=report_id, entity_type="report", entity_id=None, action="report_created", revision=1)
        report = _report_row(conn, report_id=report_id, account_id=account_id)
        if not report:
            raise HTTPException(status_code=500, detail="Không thể tạo báo cáo")
        _audit(conn, request=request, account=account, action="analytics_report_created", target=report_id, detail="Created manual analytics report")
        return envelope(True, "Đã tạo báo cáo số liệu riêng tư. Chưa có kết nối nền tảng hoặc Bot.", data={"report": _report_public(report), "history_snapshot_recorded": True, **_boundary()}, status_name="draft")

    return _idempotent(f"web-analytics-workspace:{account_id}:report:create", account_id, payload.idempotency_key, fingerprint, operation)


@router.patch("/reports/{report_id}")
async def analytics_workspace_update_report(
    report_id: str, payload: ReportUpdateRequest, request: Request, account: dict = Depends(require_csrf)
):
    _require_enabled()
    try:
        resolved = _uuid(report_id, label="Report ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    account_id = str(account["id"])
    snapshot = _report_snapshot(payload)
    fingerprint = _fingerprint({"action": "update_report", "report_id": resolved, "expected_revision": payload.expected_revision, "payload": snapshot})

    def operation(conn: Any) -> dict[str, Any]:
        report = _report_row(conn, report_id=resolved, account_id=account_id)
        if not report:
            return _report_not_found()
        blocked = _report_writable(report)
        if blocked:
            return blocked
        if int(report[11]) != payload.expected_revision:
            return _revision_conflict()
        _validate_references(conn, account_id=account_id, snapshot=snapshot)
        now = utc_now()
        revision = int(report[11]) + 1
        _write_report(conn, report_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_report_version(conn, report_id=resolved, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, report_id=resolved, entity_type="report", entity_id=None, action="report_updated", revision=revision)
        changed = _report_row(conn, report_id=resolved, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể cập nhật báo cáo")
        metrics, snapshots, findings = _report_counts(conn, report_id=resolved, account_id=account_id)
        _audit(conn, request=request, account=account, action="analytics_report_updated", target=resolved, detail="Updated manual analytics report")
        return envelope(True, "Đã lưu revision metadata báo cáo mới.", data={"report": _report_public(changed, metric_count=metrics, snapshot_count=snapshots, finding_count=findings), "history_snapshot_recorded": True, **_boundary()}, status_name="draft")

    return _idempotent(f"web-analytics-workspace:{account_id}:report:{resolved}:update", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/reports/{report_id}/lifecycle")
async def analytics_workspace_lifecycle(
    report_id: str, payload: LifecycleRequest, request: Request, account: dict = Depends(require_csrf)
):
    _require_enabled()
    try:
        resolved = _uuid(report_id, label="Report ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    account_id = str(account["id"])
    fingerprint = _fingerprint({"action": "report_lifecycle", "report_id": resolved, "state": payload.state, "expected_revision": payload.expected_revision})

    def operation(conn: Any) -> dict[str, Any]:
        report = _report_row(conn, report_id=resolved, account_id=account_id)
        if not report:
            return _report_not_found()
        if int(report[11]) != payload.expected_revision:
            return _revision_conflict()
        current = str(report[10])
        if current == payload.state:
            metrics, snapshots, findings = _report_counts(conn, report_id=resolved, account_id=account_id)
            return envelope(True, "Báo cáo đã ở trạng thái này.", data={"report": _report_public(report, metric_count=metrics, snapshot_count=snapshots, finding_count=findings), **_boundary()}, status_name=current)
        if not _report_lifecycle_allowed(current, payload.state):
            return _guarded("Chuyển trạng thái báo cáo không hợp lệ.", "WEB_ANALYTICS_LIFECYCLE_DENIED")
        snapshot = _report_snapshot_from_row(report, state=payload.state)
        if payload.state == "draft":
            _validate_references(conn, account_id=account_id, snapshot=snapshot)
        now = utc_now()
        revision = int(report[11]) + 1
        _write_report(
            conn, report_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision, now=now,
            archived_at=now if payload.state == "archived" else None,
        )
        _insert_report_version(conn, report_id=resolved, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, report_id=resolved, entity_type="report", entity_id=None, action=f"report_{payload.state}", revision=revision)
        changed = _report_row(conn, report_id=resolved, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể cập nhật trạng thái báo cáo")
        metrics, snapshots, findings = _report_counts(conn, report_id=resolved, account_id=account_id)
        _audit(conn, request=request, account=account, action="analytics_report_lifecycle", target=resolved, detail=f"Set analytics report state {payload.state}")
        return envelope(True, "Đã cập nhật lifecycle báo cáo nội bộ.", data={"report": _report_public(changed, metric_count=metrics, snapshot_count=snapshots, finding_count=findings), "history_snapshot_recorded": True, **_boundary()}, status_name=payload.state)

    return _idempotent(f"web-analytics-workspace:{account_id}:report:{resolved}:lifecycle", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/reports/{report_id}/restore-version")
async def analytics_workspace_restore_version(
    report_id: str, payload: RestoreVersionRequest, request: Request, account: dict = Depends(require_csrf)
):
    _require_enabled()
    try:
        resolved = _uuid(report_id, label="Report ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    account_id = str(account["id"])
    fingerprint = _fingerprint({"action": "restore_report_version", "report_id": resolved, "target_revision": payload.target_revision, "expected_revision": payload.expected_revision})

    def operation(conn: Any) -> dict[str, Any]:
        report = _report_row(conn, report_id=resolved, account_id=account_id)
        if not report:
            return _report_not_found()
        blocked = _report_writable(report)
        if blocked:
            return blocked
        if int(report[11]) != payload.expected_revision:
            return _revision_conflict()
        stored = conn.execute(
            "SELECT snapshot_json FROM web_analytics_report_versions WHERE report_id=? AND account_id=? AND revision=?",
            (resolved, account_id, payload.target_revision),
        ).fetchone()
        if not stored:
            return _guarded("Không tìm thấy revision metadata để khôi phục.", "WEB_ANALYTICS_VERSION_NOT_FOUND")
        try:
            restored_payload = _report_payload_from_snapshot(json.loads(str(stored[0])))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=409, detail="Revision báo cáo không hợp lệ") from exc
        snapshot = _report_snapshot(restored_payload, state="draft")
        _validate_references(conn, account_id=account_id, snapshot=snapshot)
        now = utc_now()
        revision = int(report[11]) + 1
        _write_report(conn, report_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_report_version(conn, report_id=resolved, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, report_id=resolved, entity_type="report", entity_id=None, action="report_version_restored", revision=revision)
        changed = _report_row(conn, report_id=resolved, account_id=account_id)
        if not changed:
            raise HTTPException(status_code=500, detail="Không thể khôi phục revision báo cáo")
        metrics, snapshots, findings = _report_counts(conn, report_id=resolved, account_id=account_id)
        _audit(conn, request=request, account=account, action="analytics_report_version_restored", target=resolved, detail="Restored analytics report metadata revision")
        return envelope(True, "Đã khôi phục metadata báo cáo. Metric, snapshot và nhận định giữ nguyên.", data={"report": _report_public(changed, metric_count=metrics, snapshot_count=snapshots, finding_count=findings), "history_snapshot_recorded": True, **_boundary()}, status_name="draft")

    return _idempotent(f"web-analytics-workspace:{account_id}:report:{resolved}:restore-version", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/reports/{report_id}/metrics")
async def analytics_workspace_create_metric(
    report_id: str, payload: MetricCreateRequest, request: Request, account: dict = Depends(require_csrf)
):
    _require_enabled()
    try:
        resolved = _uuid(report_id, label="Report ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    account_id = str(account["id"])
    snapshot = _metric_snapshot(payload)
    fingerprint = _fingerprint({"action": "create_metric", "report_id": resolved, "expected_report_revision": payload.expected_report_revision, "payload": snapshot})

    def operation(conn: Any) -> dict[str, Any]:
        report = _report_row(conn, report_id=resolved, account_id=account_id)
        if not report:
            return _report_not_found()
        blocked = _report_writable(report)
        if blocked:
            return blocked
        if int(report[11]) != payload.expected_report_revision:
            return _revision_conflict()
        count = conn.execute("SELECT COUNT(*) FROM web_analytics_metrics WHERE report_id=? AND account_id=?", (resolved, account_id)).fetchone()
        if int(count[0] or 0) >= MAX_METRICS_PER_REPORT:
            return _guarded("Đã đạt giới hạn metric của báo cáo.", "WEB_ANALYTICS_METRIC_LIMIT")
        now = utc_now()
        metric_id = str(uuid.uuid4())
        ordinal = _next_ordinal(conn, table="web_analytics_metrics", report_id=resolved, account_id=account_id)
        conn.execute(
            """INSERT INTO web_analytics_metrics
               (id, report_id, account_id, ordinal, name, unit, direction, description, state, revision, created_at, updated_at, archived_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', 1, ?, ?, NULL)""",
            (metric_id, resolved, account_id, ordinal, payload.name, payload.unit, payload.direction, payload.description, now, now),
        )
        _insert_metric_version(conn, metric_id=metric_id, account_id=account_id, revision=1, snapshot=_metric_snapshot(payload, ordinal=ordinal), now=now)
        _touch_report(conn, report_id=resolved, account_id=account_id, now=now)
        _event(conn, account_id=account_id, report_id=resolved, entity_type="metric", entity_id=metric_id, action="metric_created", revision=1)
        metric = _metric_row(conn, report_id=resolved, metric_id=metric_id, account_id=account_id)
        changed_report = _report_row(conn, report_id=resolved, account_id=account_id)
        if not metric or not changed_report:
            raise HTTPException(status_code=500, detail="Không thể tạo metric")
        metrics, snapshots, findings = _report_counts(conn, report_id=resolved, account_id=account_id)
        _audit(conn, request=request, account=account, action="analytics_metric_created", target=metric_id, detail="Created manual analytics metric")
        return envelope(True, "Đã thêm metric riêng tư. Chưa kết nối dữ liệu nền tảng.", data={"report": _report_public(changed_report, metric_count=metrics, snapshot_count=snapshots, finding_count=findings), "metric": _metric_public(metric), "metric_count": metrics, **_boundary()}, status_name="draft")

    return _idempotent(f"web-analytics-workspace:{account_id}:report:{resolved}:metric:create", account_id, payload.idempotency_key, fingerprint, operation)


@router.patch("/reports/{report_id}/metrics/{metric_id}")
async def analytics_workspace_update_metric(
    report_id: str, metric_id: str, payload: MetricUpdateRequest, request: Request, account: dict = Depends(require_csrf)
):
    _require_enabled()
    try:
        resolved_report = _uuid(report_id, label="Report ID")
        resolved_metric = _uuid(metric_id, label="Metric ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    account_id = str(account["id"])
    snapshot = _metric_snapshot(payload)
    fingerprint = _fingerprint({"action": "update_metric", "report_id": resolved_report, "metric_id": resolved_metric, "expected_report_revision": payload.expected_report_revision, "expected_revision": payload.expected_revision, "payload": snapshot})

    def operation(conn: Any) -> dict[str, Any]:
        report = _report_row(conn, report_id=resolved_report, account_id=account_id)
        if not report:
            return _report_not_found()
        blocked = _report_writable(report)
        if blocked:
            return blocked
        if int(report[11]) != payload.expected_report_revision:
            return _revision_conflict()
        metric = _metric_row(conn, report_id=resolved_report, metric_id=resolved_metric, account_id=account_id)
        if not metric:
            return _metric_not_found()
        if str(metric[7]) != "active":
            return _guarded("Metric đã archive; hãy khôi phục trước khi chỉnh sửa.", "WEB_ANALYTICS_METRIC_ARCHIVED")
        if int(metric[8]) != payload.expected_revision:
            return _revision_conflict()
        now = utc_now()
        revision = int(metric[8]) + 1
        conn.execute(
            """UPDATE web_analytics_metrics SET name=?, unit=?, direction=?, description=?, revision=?, updated_at=?
               WHERE id=? AND report_id=? AND account_id=?""",
            (payload.name, payload.unit, payload.direction, payload.description, revision, now, resolved_metric, resolved_report, account_id),
        )
        _insert_metric_version(conn, metric_id=resolved_metric, account_id=account_id, revision=revision, snapshot=_metric_snapshot(payload, ordinal=int(metric[2])), now=now)
        _touch_report(conn, report_id=resolved_report, account_id=account_id, now=now)
        _event(conn, account_id=account_id, report_id=resolved_report, entity_type="metric", entity_id=resolved_metric, action="metric_updated", revision=revision)
        changed = _metric_row(conn, report_id=resolved_report, metric_id=resolved_metric, account_id=account_id)
        changed_report = _report_row(conn, report_id=resolved_report, account_id=account_id)
        if not changed or not changed_report:
            raise HTTPException(status_code=500, detail="Không thể cập nhật metric")
        metrics, snapshots, findings = _report_counts(conn, report_id=resolved_report, account_id=account_id)
        _audit(conn, request=request, account=account, action="analytics_metric_updated", target=resolved_metric, detail="Updated manual analytics metric")
        return envelope(True, "Đã lưu revision metric mới.", data={"report": _report_public(changed_report, metric_count=metrics, snapshot_count=snapshots, finding_count=findings), "metric": _metric_public(changed), **_boundary()}, status_name="draft")

    return _idempotent(f"web-analytics-workspace:{account_id}:report:{resolved_report}:metric:{resolved_metric}:update", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/reports/{report_id}/metrics/{metric_id}/state")
async def analytics_workspace_metric_state(
    report_id: str, metric_id: str, payload: EntityStateRequest, request: Request, account: dict = Depends(require_csrf)
):
    _require_enabled()
    try:
        resolved_report = _uuid(report_id, label="Report ID")
        resolved_metric = _uuid(metric_id, label="Metric ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    account_id = str(account["id"])
    fingerprint = _fingerprint({"action": "metric_state", "report_id": resolved_report, "metric_id": resolved_metric, "state": payload.state, "expected_report_revision": payload.expected_report_revision, "expected_revision": payload.expected_revision})

    def operation(conn: Any) -> dict[str, Any]:
        report = _report_row(conn, report_id=resolved_report, account_id=account_id)
        if not report:
            return _report_not_found()
        blocked = _report_writable(report)
        if blocked:
            return blocked
        if int(report[11]) != payload.expected_report_revision:
            return _revision_conflict()
        metric = _metric_row(conn, report_id=resolved_report, metric_id=resolved_metric, account_id=account_id)
        if not metric:
            return _metric_not_found()
        if int(metric[8]) != payload.expected_revision:
            return _revision_conflict()
        if str(metric[7]) == payload.state:
            metrics, snapshots, findings = _report_counts(conn, report_id=resolved_report, account_id=account_id)
            return envelope(True, "Metric đã ở trạng thái này.", data={"report": _report_public(report, metric_count=metrics, snapshot_count=snapshots, finding_count=findings), "metric": _metric_public(metric), **_boundary()}, status_name="draft")
        now = utc_now()
        ordinal = _next_ordinal(conn, table="web_analytics_metrics", report_id=resolved_report, account_id=account_id, archived=payload.state == "archived")
        revision = int(metric[8]) + 1
        conn.execute(
            """UPDATE web_analytics_metrics SET ordinal=?, state=?, revision=?, updated_at=?, archived_at=?
               WHERE id=? AND report_id=? AND account_id=?""",
            (ordinal, payload.state, revision, now, now if payload.state == "archived" else None, resolved_metric, resolved_report, account_id),
        )
        metric_snapshot = _metric_snapshot(
            MetricPayload(name=str(metric[3]), unit=str(metric[4]), direction=str(metric[5]), description=str(metric[6])),
            state=payload.state, ordinal=ordinal,
        )
        _insert_metric_version(conn, metric_id=resolved_metric, account_id=account_id, revision=revision, snapshot=metric_snapshot, now=now)
        _touch_report(conn, report_id=resolved_report, account_id=account_id, now=now)
        _event(conn, account_id=account_id, report_id=resolved_report, entity_type="metric", entity_id=resolved_metric, action=f"metric_{payload.state}", revision=revision)
        changed = _metric_row(conn, report_id=resolved_report, metric_id=resolved_metric, account_id=account_id)
        changed_report = _report_row(conn, report_id=resolved_report, account_id=account_id)
        if not changed or not changed_report:
            raise HTTPException(status_code=500, detail="Không thể cập nhật trạng thái metric")
        metrics, snapshots, findings = _report_counts(conn, report_id=resolved_report, account_id=account_id)
        _audit(conn, request=request, account=account, action="analytics_metric_state", target=resolved_metric, detail=f"Set analytics metric state {payload.state}")
        return envelope(True, "Đã cập nhật trạng thái metric.", data={"report": _report_public(changed_report, metric_count=metrics, snapshot_count=snapshots, finding_count=findings), "metric": _metric_public(changed), **_boundary()}, status_name="draft")

    return _idempotent(f"web-analytics-workspace:{account_id}:report:{resolved_report}:metric:{resolved_metric}:state", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/reports/{report_id}/metrics/{metric_id}/snapshots")
async def analytics_workspace_create_snapshot(
    report_id: str, metric_id: str, payload: SnapshotCreateRequest, request: Request, account: dict = Depends(require_csrf)
):
    _require_enabled()
    try:
        resolved_report = _uuid(report_id, label="Report ID")
        resolved_metric = _uuid(metric_id, label="Metric ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    account_id = str(account["id"])
    snapshot = _snapshot_snapshot(payload)
    fingerprint = _fingerprint({"action": "create_snapshot", "report_id": resolved_report, "metric_id": resolved_metric, "expected_report_revision": payload.expected_report_revision, "payload": snapshot})

    def operation(conn: Any) -> dict[str, Any]:
        report = _report_row(conn, report_id=resolved_report, account_id=account_id)
        if not report:
            return _report_not_found()
        blocked = _report_writable(report)
        if blocked:
            return blocked
        if int(report[11]) != payload.expected_report_revision:
            return _revision_conflict()
        metric = _metric_row(conn, report_id=resolved_report, metric_id=resolved_metric, account_id=account_id)
        if not metric:
            return _metric_not_found()
        if str(metric[7]) != "active":
            return _guarded("Metric đã archive; hãy khôi phục trước khi thêm snapshot.", "WEB_ANALYTICS_METRIC_ARCHIVED")
        _validate_snapshot_window(report, payload.observed_on)
        count = conn.execute("SELECT COUNT(*) FROM web_analytics_snapshots WHERE metric_id=? AND account_id=?", (resolved_metric, account_id)).fetchone()
        if int(count[0] or 0) >= MAX_SNAPSHOTS_PER_METRIC:
            return _guarded("Đã đạt giới hạn snapshot của metric.", "WEB_ANALYTICS_SNAPSHOT_LIMIT")
        if _active_snapshot_collision(conn, metric_id=resolved_metric, observed_on=payload.observed_on, account_id=account_id):
            return _guarded("Metric đã có một snapshot đang hoạt động ở ngày này.", "WEB_ANALYTICS_SNAPSHOT_DUPLICATE")
        now = utc_now()
        snapshot_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO web_analytics_snapshots
               (id, report_id, metric_id, account_id, observed_on, value_decimal, source_label, note, state, revision, created_at, updated_at, archived_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', 1, ?, ?, NULL)""",
            (snapshot_id, resolved_report, resolved_metric, account_id, payload.observed_on, payload.value, payload.source_label, payload.note, now, now),
        )
        _insert_snapshot_version(conn, snapshot_id=snapshot_id, account_id=account_id, revision=1, snapshot=snapshot, now=now)
        _touch_report(conn, report_id=resolved_report, account_id=account_id, now=now)
        _event(conn, account_id=account_id, report_id=resolved_report, entity_type="snapshot", entity_id=snapshot_id, action="snapshot_created", revision=1)
        changed = _snapshot_row(conn, report_id=resolved_report, metric_id=resolved_metric, snapshot_id=snapshot_id, account_id=account_id)
        changed_report = _report_row(conn, report_id=resolved_report, account_id=account_id)
        if not changed or not changed_report:
            raise HTTPException(status_code=500, detail="Không thể tạo snapshot")
        metrics, snapshots, findings = _report_counts(conn, report_id=resolved_report, account_id=account_id)
        _audit(conn, request=request, account=account, action="analytics_snapshot_created", target=snapshot_id, detail="Created manual analytics snapshot")
        return envelope(True, "Đã ghi nhận snapshot do bạn tự nhập.", data={"report": _report_public(changed_report, metric_count=metrics, snapshot_count=snapshots, finding_count=findings), "snapshot": _snapshot_public(changed), "snapshot_count": snapshots, **_boundary()}, status_name="draft")

    return _idempotent(f"web-analytics-workspace:{account_id}:report:{resolved_report}:metric:{resolved_metric}:snapshot:create", account_id, payload.idempotency_key, fingerprint, operation)


@router.patch("/reports/{report_id}/metrics/{metric_id}/snapshots/{snapshot_id}")
async def analytics_workspace_update_snapshot(
    report_id: str, metric_id: str, snapshot_id: str, payload: SnapshotUpdateRequest, request: Request, account: dict = Depends(require_csrf)
):
    _require_enabled()
    try:
        resolved_report = _uuid(report_id, label="Report ID")
        resolved_metric = _uuid(metric_id, label="Metric ID")
        resolved_snapshot = _uuid(snapshot_id, label="Snapshot ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    account_id = str(account["id"])
    snapshot = _snapshot_snapshot(payload)
    fingerprint = _fingerprint({"action": "update_snapshot", "report_id": resolved_report, "metric_id": resolved_metric, "snapshot_id": resolved_snapshot, "expected_report_revision": payload.expected_report_revision, "expected_revision": payload.expected_revision, "payload": snapshot})

    def operation(conn: Any) -> dict[str, Any]:
        report = _report_row(conn, report_id=resolved_report, account_id=account_id)
        if not report:
            return _report_not_found()
        blocked = _report_writable(report)
        if blocked:
            return blocked
        if int(report[11]) != payload.expected_report_revision:
            return _revision_conflict()
        metric = _metric_row(conn, report_id=resolved_report, metric_id=resolved_metric, account_id=account_id)
        if not metric:
            return _metric_not_found()
        record = _snapshot_row(conn, report_id=resolved_report, metric_id=resolved_metric, snapshot_id=resolved_snapshot, account_id=account_id)
        if not record:
            return _snapshot_not_found()
        if str(record[7]) != "active":
            return _guarded("Snapshot đã archive; hãy khôi phục trước khi chỉnh sửa.", "WEB_ANALYTICS_SNAPSHOT_ARCHIVED")
        if int(record[8]) != payload.expected_revision:
            return _revision_conflict()
        _validate_snapshot_window(report, payload.observed_on)
        if _active_snapshot_collision(conn, metric_id=resolved_metric, observed_on=payload.observed_on, account_id=account_id, exclude_id=resolved_snapshot):
            return _guarded("Metric đã có một snapshot đang hoạt động ở ngày này.", "WEB_ANALYTICS_SNAPSHOT_DUPLICATE")
        now = utc_now()
        revision = int(record[8]) + 1
        conn.execute(
            """UPDATE web_analytics_snapshots SET observed_on=?, value_decimal=?, source_label=?, note=?, revision=?, updated_at=?
               WHERE id=? AND report_id=? AND metric_id=? AND account_id=?""",
            (payload.observed_on, payload.value, payload.source_label, payload.note, revision, now, resolved_snapshot, resolved_report, resolved_metric, account_id),
        )
        _insert_snapshot_version(conn, snapshot_id=resolved_snapshot, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        _touch_report(conn, report_id=resolved_report, account_id=account_id, now=now)
        _event(conn, account_id=account_id, report_id=resolved_report, entity_type="snapshot", entity_id=resolved_snapshot, action="snapshot_updated", revision=revision)
        changed = _snapshot_row(conn, report_id=resolved_report, metric_id=resolved_metric, snapshot_id=resolved_snapshot, account_id=account_id)
        changed_report = _report_row(conn, report_id=resolved_report, account_id=account_id)
        if not changed or not changed_report:
            raise HTTPException(status_code=500, detail="Không thể cập nhật snapshot")
        metrics, snapshots, findings = _report_counts(conn, report_id=resolved_report, account_id=account_id)
        _audit(conn, request=request, account=account, action="analytics_snapshot_updated", target=resolved_snapshot, detail="Updated manual analytics snapshot")
        return envelope(True, "Đã cập nhật snapshot do bạn tự nhập.", data={"report": _report_public(changed_report, metric_count=metrics, snapshot_count=snapshots, finding_count=findings), "snapshot": _snapshot_public(changed), **_boundary()}, status_name="draft")

    return _idempotent(f"web-analytics-workspace:{account_id}:report:{resolved_report}:metric:{resolved_metric}:snapshot:{resolved_snapshot}:update", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/reports/{report_id}/metrics/{metric_id}/snapshots/{snapshot_id}/state")
async def analytics_workspace_snapshot_state(
    report_id: str, metric_id: str, snapshot_id: str, payload: EntityStateRequest, request: Request, account: dict = Depends(require_csrf)
):
    _require_enabled()
    try:
        resolved_report = _uuid(report_id, label="Report ID")
        resolved_metric = _uuid(metric_id, label="Metric ID")
        resolved_snapshot = _uuid(snapshot_id, label="Snapshot ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    account_id = str(account["id"])
    fingerprint = _fingerprint({"action": "snapshot_state", "report_id": resolved_report, "metric_id": resolved_metric, "snapshot_id": resolved_snapshot, "state": payload.state, "expected_report_revision": payload.expected_report_revision, "expected_revision": payload.expected_revision})

    def operation(conn: Any) -> dict[str, Any]:
        report = _report_row(conn, report_id=resolved_report, account_id=account_id)
        if not report:
            return _report_not_found()
        blocked = _report_writable(report)
        if blocked:
            return blocked
        if int(report[11]) != payload.expected_report_revision:
            return _revision_conflict()
        metric = _metric_row(conn, report_id=resolved_report, metric_id=resolved_metric, account_id=account_id)
        if not metric:
            return _metric_not_found()
        record = _snapshot_row(conn, report_id=resolved_report, metric_id=resolved_metric, snapshot_id=resolved_snapshot, account_id=account_id)
        if not record:
            return _snapshot_not_found()
        if int(record[8]) != payload.expected_revision:
            return _revision_conflict()
        if str(record[7]) == payload.state:
            metrics, snapshots, findings = _report_counts(conn, report_id=resolved_report, account_id=account_id)
            return envelope(True, "Snapshot đã ở trạng thái này.", data={"report": _report_public(report, metric_count=metrics, snapshot_count=snapshots, finding_count=findings), "snapshot": _snapshot_public(record), **_boundary()}, status_name="draft")
        if payload.state == "active" and _active_snapshot_collision(conn, metric_id=resolved_metric, observed_on=str(record[3]), account_id=account_id, exclude_id=resolved_snapshot):
            return _guarded("Không thể khôi phục vì metric đã có snapshot hoạt động cùng ngày.", "WEB_ANALYTICS_SNAPSHOT_DUPLICATE")
        now = utc_now()
        revision = int(record[8]) + 1
        conn.execute(
            """UPDATE web_analytics_snapshots SET state=?, revision=?, updated_at=?, archived_at=?
               WHERE id=? AND report_id=? AND metric_id=? AND account_id=?""",
            (payload.state, revision, now, now if payload.state == "archived" else None, resolved_snapshot, resolved_report, resolved_metric, account_id),
        )
        snapshot_value = SnapshotPayload(observed_on=str(record[3]), value=str(record[4]), source_label=str(record[5]), note=str(record[6]))
        _insert_snapshot_version(conn, snapshot_id=resolved_snapshot, account_id=account_id, revision=revision, snapshot=_snapshot_snapshot(snapshot_value, state=payload.state), now=now)
        _touch_report(conn, report_id=resolved_report, account_id=account_id, now=now)
        _event(conn, account_id=account_id, report_id=resolved_report, entity_type="snapshot", entity_id=resolved_snapshot, action=f"snapshot_{payload.state}", revision=revision)
        changed = _snapshot_row(conn, report_id=resolved_report, metric_id=resolved_metric, snapshot_id=resolved_snapshot, account_id=account_id)
        changed_report = _report_row(conn, report_id=resolved_report, account_id=account_id)
        if not changed or not changed_report:
            raise HTTPException(status_code=500, detail="Không thể cập nhật trạng thái snapshot")
        metrics, snapshots, findings = _report_counts(conn, report_id=resolved_report, account_id=account_id)
        _audit(conn, request=request, account=account, action="analytics_snapshot_state", target=resolved_snapshot, detail=f"Set analytics snapshot state {payload.state}")
        return envelope(True, "Đã cập nhật trạng thái snapshot.", data={"report": _report_public(changed_report, metric_count=metrics, snapshot_count=snapshots, finding_count=findings), "snapshot": _snapshot_public(changed), **_boundary()}, status_name="draft")

    return _idempotent(f"web-analytics-workspace:{account_id}:report:{resolved_report}:metric:{resolved_metric}:snapshot:{resolved_snapshot}:state", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/reports/{report_id}/findings")
async def analytics_workspace_create_finding(
    report_id: str, payload: FindingCreateRequest, request: Request, account: dict = Depends(require_csrf)
):
    _require_enabled()
    try:
        resolved_report = _uuid(report_id, label="Report ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    account_id = str(account["id"])
    finding = _finding_snapshot(payload)
    fingerprint = _fingerprint({"action": "create_finding", "report_id": resolved_report, "expected_report_revision": payload.expected_report_revision, "payload": finding})

    def operation(conn: Any) -> dict[str, Any]:
        report = _report_row(conn, report_id=resolved_report, account_id=account_id)
        if not report:
            return _report_not_found()
        blocked = _report_writable(report)
        if blocked:
            return blocked
        if int(report[11]) != payload.expected_report_revision:
            return _revision_conflict()
        count = conn.execute(
            "SELECT COUNT(*) FROM web_analytics_findings WHERE report_id=? AND account_id=?",
            (resolved_report, account_id),
        ).fetchone()
        if int(count[0] or 0) >= MAX_FINDINGS_PER_REPORT:
            return _guarded("Đã đạt giới hạn nhận định của báo cáo.", "WEB_ANALYTICS_FINDING_LIMIT")
        now = utc_now()
        finding_id = str(uuid.uuid4())
        ordinal = _next_ordinal(conn, table="web_analytics_findings", report_id=resolved_report, account_id=account_id)
        conn.execute(
            """INSERT INTO web_analytics_findings
               (id, report_id, account_id, ordinal, kind, body, state, revision, created_at, updated_at, archived_at)
               VALUES (?, ?, ?, ?, ?, ?, 'active', 1, ?, ?, NULL)""",
            (finding_id, resolved_report, account_id, ordinal, payload.kind, payload.body, now, now),
        )
        _insert_finding_version(conn, finding_id=finding_id, account_id=account_id, revision=1, snapshot=_finding_snapshot(payload, ordinal=ordinal), now=now)
        _touch_report(conn, report_id=resolved_report, account_id=account_id, now=now)
        _event(conn, account_id=account_id, report_id=resolved_report, entity_type="finding", entity_id=finding_id, action="finding_created", revision=1)
        changed = _finding_row(conn, report_id=resolved_report, finding_id=finding_id, account_id=account_id)
        changed_report = _report_row(conn, report_id=resolved_report, account_id=account_id)
        if not changed or not changed_report:
            raise HTTPException(status_code=500, detail="Không thể tạo nhận định")
        metrics, snapshots, findings = _report_counts(conn, report_id=resolved_report, account_id=account_id)
        _audit(conn, request=request, account=account, action="analytics_finding_created", target=finding_id, detail="Created human-authored analytics finding")
        return envelope(True, "Đã thêm nhận định do bạn tự viết.", data={"report": _report_public(changed_report, metric_count=metrics, snapshot_count=snapshots, finding_count=findings), "finding": _finding_public(changed), "finding_count": findings, **_boundary()}, status_name="draft")

    return _idempotent(f"web-analytics-workspace:{account_id}:report:{resolved_report}:finding:create", account_id, payload.idempotency_key, fingerprint, operation)


@router.patch("/reports/{report_id}/findings/{finding_id}")
async def analytics_workspace_update_finding(
    report_id: str, finding_id: str, payload: FindingUpdateRequest, request: Request, account: dict = Depends(require_csrf)
):
    _require_enabled()
    try:
        resolved_report = _uuid(report_id, label="Report ID")
        resolved_finding = _uuid(finding_id, label="Finding ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    account_id = str(account["id"])
    finding = _finding_snapshot(payload)
    fingerprint = _fingerprint({"action": "update_finding", "report_id": resolved_report, "finding_id": resolved_finding, "expected_report_revision": payload.expected_report_revision, "expected_revision": payload.expected_revision, "payload": finding})

    def operation(conn: Any) -> dict[str, Any]:
        report = _report_row(conn, report_id=resolved_report, account_id=account_id)
        if not report:
            return _report_not_found()
        blocked = _report_writable(report)
        if blocked:
            return blocked
        if int(report[11]) != payload.expected_report_revision:
            return _revision_conflict()
        record = _finding_row(conn, report_id=resolved_report, finding_id=resolved_finding, account_id=account_id)
        if not record:
            return _finding_not_found()
        if str(record[5]) != "active":
            return _guarded("Nhận định đã archive; hãy khôi phục trước khi chỉnh sửa.", "WEB_ANALYTICS_FINDING_ARCHIVED")
        if int(record[6]) != payload.expected_revision:
            return _revision_conflict()
        now = utc_now()
        revision = int(record[6]) + 1
        conn.execute(
            """UPDATE web_analytics_findings SET kind=?, body=?, revision=?, updated_at=?
               WHERE id=? AND report_id=? AND account_id=?""",
            (payload.kind, payload.body, revision, now, resolved_finding, resolved_report, account_id),
        )
        _insert_finding_version(conn, finding_id=resolved_finding, account_id=account_id, revision=revision, snapshot=_finding_snapshot(payload, ordinal=int(record[2])), now=now)
        _touch_report(conn, report_id=resolved_report, account_id=account_id, now=now)
        _event(conn, account_id=account_id, report_id=resolved_report, entity_type="finding", entity_id=resolved_finding, action="finding_updated", revision=revision)
        changed = _finding_row(conn, report_id=resolved_report, finding_id=resolved_finding, account_id=account_id)
        changed_report = _report_row(conn, report_id=resolved_report, account_id=account_id)
        if not changed or not changed_report:
            raise HTTPException(status_code=500, detail="Không thể cập nhật nhận định")
        metrics, snapshots, findings = _report_counts(conn, report_id=resolved_report, account_id=account_id)
        _audit(conn, request=request, account=account, action="analytics_finding_updated", target=resolved_finding, detail="Updated human-authored analytics finding")
        return envelope(True, "Đã cập nhật nhận định do bạn tự viết.", data={"report": _report_public(changed_report, metric_count=metrics, snapshot_count=snapshots, finding_count=findings), "finding": _finding_public(changed), **_boundary()}, status_name="draft")

    return _idempotent(f"web-analytics-workspace:{account_id}:report:{resolved_report}:finding:{resolved_finding}:update", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/reports/{report_id}/findings/{finding_id}/state")
async def analytics_workspace_finding_state(
    report_id: str, finding_id: str, payload: FindingStateRequest, request: Request, account: dict = Depends(require_csrf)
):
    _require_enabled()
    try:
        resolved_report = _uuid(report_id, label="Report ID")
        resolved_finding = _uuid(finding_id, label="Finding ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    account_id = str(account["id"])
    fingerprint = _fingerprint({"action": "finding_state", "report_id": resolved_report, "finding_id": resolved_finding, "state": payload.state, "expected_report_revision": payload.expected_report_revision, "expected_revision": payload.expected_revision})

    def operation(conn: Any) -> dict[str, Any]:
        report = _report_row(conn, report_id=resolved_report, account_id=account_id)
        if not report:
            return _report_not_found()
        blocked = _report_writable(report)
        if blocked:
            return blocked
        if int(report[11]) != payload.expected_report_revision:
            return _revision_conflict()
        record = _finding_row(conn, report_id=resolved_report, finding_id=resolved_finding, account_id=account_id)
        if not record:
            return _finding_not_found()
        if int(record[6]) != payload.expected_revision:
            return _revision_conflict()
        if str(record[5]) == payload.state:
            metrics, snapshots, findings = _report_counts(conn, report_id=resolved_report, account_id=account_id)
            return envelope(True, "Nhận định đã ở trạng thái này.", data={"report": _report_public(report, metric_count=metrics, snapshot_count=snapshots, finding_count=findings), "finding": _finding_public(record), **_boundary()}, status_name="draft")
        now = utc_now()
        revision = int(record[6]) + 1
        ordinal = _next_ordinal(conn, table="web_analytics_findings", report_id=resolved_report, account_id=account_id, archived=payload.state == "archived")
        conn.execute(
            """UPDATE web_analytics_findings SET ordinal=?, state=?, revision=?, updated_at=?, archived_at=?
               WHERE id=? AND report_id=? AND account_id=?""",
            (ordinal, payload.state, revision, now, now if payload.state == "archived" else None, resolved_finding, resolved_report, account_id),
        )
        finding_value = FindingPayload(kind=str(record[3]), body=str(record[4]))
        _insert_finding_version(conn, finding_id=resolved_finding, account_id=account_id, revision=revision, snapshot=_finding_snapshot(finding_value, state=payload.state, ordinal=ordinal), now=now)
        _touch_report(conn, report_id=resolved_report, account_id=account_id, now=now)
        _event(conn, account_id=account_id, report_id=resolved_report, entity_type="finding", entity_id=resolved_finding, action=f"finding_{payload.state}", revision=revision)
        changed = _finding_row(conn, report_id=resolved_report, finding_id=resolved_finding, account_id=account_id)
        changed_report = _report_row(conn, report_id=resolved_report, account_id=account_id)
        if not changed or not changed_report:
            raise HTTPException(status_code=500, detail="Không thể cập nhật trạng thái nhận định")
        metrics, snapshots, findings = _report_counts(conn, report_id=resolved_report, account_id=account_id)
        _audit(conn, request=request, account=account, action="analytics_finding_state", target=resolved_finding, detail=f"Set analytics finding state {payload.state}")
        return envelope(True, "Đã cập nhật trạng thái nhận định.", data={"report": _report_public(changed_report, metric_count=metrics, snapshot_count=snapshots, finding_count=findings), "finding": _finding_public(changed), **_boundary()}, status_name="draft")

    return _idempotent(f"web-analytics-workspace:{account_id}:report:{resolved_report}:finding:{resolved_finding}:state", account_id, payload.idempotency_key, fingerprint, operation)


@router.get("/reports/{report_id}/events")
async def analytics_workspace_events(report_id: str, limit: int = 30, account: dict = Depends(require_account)):
    _require_enabled()
    try:
        resolved_report = _uuid(report_id, label="Report ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    safe_limit = max(1, min(int(limit), MAX_EVENT_LIMIT))
    ensure_copyfast_schema()
    with read_transaction() as conn:
        report = _report_row(conn, report_id=resolved_report, account_id=str(account["id"]))
        if not report:
            raise HTTPException(status_code=404, detail="Không tìm thấy báo cáo Analytics Workspace")
        rows = conn.execute(
            """SELECT action, entity_type, entity_id, revision, created_at FROM web_analytics_workspace_events
               WHERE report_id=? AND account_id=? ORDER BY created_at DESC, id DESC LIMIT ?""",
            (resolved_report, str(account["id"]), safe_limit),
        ).fetchall()
        metrics, snapshots, findings = _report_counts(conn, report_id=resolved_report, account_id=str(account["id"]))
        return envelope(True, "Đã tải hoạt động Analytics Workspace.", data={
            "report": _report_public(report, metric_count=metrics, snapshot_count=snapshots, finding_count=findings),
            "events": [{"action": str(row[0]), "entity_type": str(row[1]), "entity_id": str(row[2]) if row[2] else None, "revision": int(row[3]), "created_at": str(row[4])} for row in rows],
            **_boundary(),
        }, status_name=str(report[10]))
