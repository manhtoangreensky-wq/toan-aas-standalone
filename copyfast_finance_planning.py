"""Web-native Finance Operations Planning for the standalone Admin ERP.

This module gives the internal Web application a small, auditable planning
surface for operating-cost budgets and expense plans.  It is deliberately not
a second payment, wallet, Xu, PayOS, revenue, refund, invoice, tax, or Bot
ledger.  In particular, it never reads a Bot table, calls the bridge/provider
or accepts manual-payment evidence.  Every record is Web-owned, carries a
server-side revision, and is available only to a signed Web administrator.
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

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, field_validator

from copyfast_auth import _record_audit, _request_id, envelope, require_admin, require_admin_csrf
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction, utc_now


router = APIRouter(prefix="/api/v1/admin/finance-planning", tags=["Web Finance Operations Planning"])


# These are planning classifications, not transaction/payment kinds.  Keep the
# vocabulary closed so neither a browser nor a stored row can make a new
# accounting/payment category appear in the product.
CATEGORIES = frozenset({
    "infrastructure",
    "provider_runtime",
    "software",
    "marketing",
    "operations",
    "other",
})
BUDGET_STATES = frozenset({"active", "archived"})
BUDGET_TRANSITIONS = {
    "active": frozenset({"archived"}),
    "archived": frozenset({"active"}),
}
COST_STATES = frozenset({"draft", "review", "approved", "archived"})
COST_TRANSITIONS = {
    "draft": frozenset({"review", "archived"}),
    "review": frozenset({"draft", "approved", "archived"}),
    "approved": frozenset({"archived"}),
    "archived": frozenset({"draft"}),
}
CATEGORY_LABELS = {
    "infrastructure": "Hạ tầng Web",
    "provider_runtime": "Runtime / provider planning",
    "software": "Phần mềm & subscription",
    "marketing": "Marketing nội bộ",
    "operations": "Vận hành nội bộ",
    "other": "Khác",
}
MAX_BUDGETS = 1_200
MAX_COST_PLANS = 5_000
MAX_LIST_LIMIT = 100
MAX_LIST_OFFSET = 10_000
MAX_AMOUNT_VND = 1_000_000_000_000
IDEMPOTENCY_RETENTION = timedelta(hours=24)
IDEMPOTENCY_MAX_RECORDS = 2_048
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
PERIOD_PATTERN = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])$")
DATE_PATTERN = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$")
UNSAFE_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
MARKUP_PATTERN = re.compile(r"(?:<\s*/?\s*[A-Za-z][^>\r\n]{0,240}>|```|\bon[a-z]+\s*=)", re.IGNORECASE)
SECRET_PATTERN = re.compile(
    r"\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|token|"
    r"client[ _-]?secret|secret(?:[ _-]?(?:key|access[ _-]?(?:key))?)?|password|passphrase|authorization)\b\s*"
    r"(?:['\"]\s*)?(?:[:=]|\bis\b)\s*(?:['\"]\s*)?(?:(?:bearer|basic)\s+)?[A-Za-z0-9_./+=:-]{1,}",
    re.IGNORECASE,
)
KNOWN_SECRET_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(?:(?:sk|pk|rk)[_-][A-Za-z0-9_-]{12,}|gh(?:p|o|u|s|r)_[A-Za-z0-9]{12,}|"
    r"github_pat_[A-Za-z0-9_]{12,}|xox(?:b|p|a|r|s)-[A-Za-z0-9-]{12,}|AIza[0-9A-Za-z_-]{20,}|"
    r"(?:AKIA|ASIA)[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
PAYMENT_PROOF_PATTERN = re.compile(
    r"\b(?:payos|tx(?:id|n)?|transaction\s+(?:hash|id|reference|no\.?|number)|"
    r"mã\s*(?:(?:giao\s*)?(?:dịch|gd)|tham\s*chiếu|thanh\s*toán)|"
    r"ma\s*(?:(?:giao\s*)?(?:dich|gd)|tham\s*chieu|thanh\s*toan)|"
    r"biên\s*lai|bien\s*lai|chứng\s*từ|chung\s*tu|bill|số\s*tài\s*khoản|"
    r"so\s*tai\s*khoan|stk|tài\s*khoản\s*(?:ngân\s*hàng|bank)|"
    r"tai\s*khoan\s*(?:ngan\s*hang|bank)|bank\s+account|account\s+(?:number|no|id)|"
    r"iban|swift(?:/bic)?|bic|routing\s*(?:number|no\.?)|viet\s*qr|momo|bank\s*transfer|"
    r"qr\s*(?:code|thanh\s*toán|thanh\s*toan)?)\b",
    re.IGNORECASE,
)
# The closed planning contract does not accept financial evidence at all.  A
# keyword-only DLP rule would still let a user paste a bare account/PAN/IBAN or
# transaction hash into an otherwise innocuous note, vendor label or purpose.
# These conservative token shapes run before persistence; they intentionally
# do not try to validate or retain the supplied identifier.
RAW_IBAN_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])(?:[A-Z]{2}\d{2}(?:[A-Z0-9][ .-]?){11,30})(?![A-Za-z0-9])",
    re.IGNORECASE,
)
RAW_ACCOUNT_OR_PAN_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])(?:\d[ .-]?){10,34}(?![A-Za-z0-9])"
)
RAW_TRANSACTION_HASH_PATTERN = re.compile(
    r"(?<![A-Fa-f0-9])(?:0x)?[A-Fa-f0-9]{32,128}(?![A-Fa-f0-9])"
)


def _flag(name: str, *, default: bool) -> bool:
    return os.environ.get(name, str(default).lower()).strip().lower() in {"1", "true", "yes", "on"}


def finance_planning_enabled() -> bool:
    """Return the independent Finance Planning feature gate.

    The dedicated switch only controls these Web-owned planning tables.  It
    does not enable canonical finance reads/writes, provider operations or
    payment flows.  The Admin ERP umbrella remains an explicit outer gate.
    """

    return _flag("WEBAPP_ADMIN_ERP_ENABLED", default=True) and _flag(
        "WEBAPP_FINANCE_PLANNING_ENABLED", default=True
    )


def _require_enabled() -> None:
    if not finance_planning_enabled():
        raise HTTPException(
            status_code=503,
            detail="Finance Operations Planning đang tạm dừng để bảo trì.",
        )


def ensure_finance_planning_schema() -> None:
    """Create only additive Web-owned planning tables.

    These tables intentionally use a distinct ``web_finance_planning_*``
    namespace.  They must never substitute Bot ``finance_*`` tables or become
    a storage location for manual payment proof, PayOS state or a Xu ledger.
    """

    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_finance_planning_budgets (
                id TEXT PRIMARY KEY,
                created_by_account_id TEXT NOT NULL,
                period TEXT NOT NULL,
                category TEXT NOT NULL,
                planned_vnd INTEGER NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                state TEXT NOT NULL,
                revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_web_finance_planning_budget_active
            ON web_finance_planning_budgets(period, category)
            WHERE archived_at IS NULL
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_finance_planning_costs (
                id TEXT PRIMARY KEY,
                created_by_account_id TEXT NOT NULL,
                period TEXT NOT NULL,
                planned_for TEXT NOT NULL,
                category TEXT NOT NULL,
                planned_vnd INTEGER NOT NULL,
                vendor_label TEXT NOT NULL DEFAULT '',
                purpose TEXT NOT NULL,
                state TEXT NOT NULL,
                revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_web_finance_planning_costs_period_state
            ON web_finance_planning_costs(period, state, updated_at DESC, id ASC)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_finance_planning_events (
                id TEXT PRIMARY KEY,
                record_kind TEXT NOT NULL,
                record_id TEXT NOT NULL,
                actor_account_id TEXT NOT NULL,
                action TEXT NOT NULL,
                state TEXT NOT NULL,
                revision INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_web_finance_planning_events_record
            ON web_finance_planning_events(record_kind, record_id, created_at DESC)
            """
        )


def _boundary(*, persisted: bool) -> dict[str, Any]:
    """Make the intentional authority boundary part of every response."""

    return {
        "execution": "web_native_finance_operations_planning",
        "planning_persisted": bool(persisted),
        "canonical_finance_read": False,
        "canonical_finance_write": False,
        "bot_called": False,
        "bridge_called": False,
        "provider_called": False,
        "job_created": False,
        "wallet_mutated": False,
        "payment_started": False,
        "payment_finalized": False,
        "payos_webhook_created": False,
        "refund_created": False,
        "ledger_changed": False,
        "tax_calculated": False,
        "report_exported": False,
        "notification_sent": False,
    }


def _contains_raw_financial_identifier(value: str) -> bool:
    """Detect bare financial identifiers without retaining their value.

    Finance Planning intentionally has no payment-proof or accounting intake.
    Long digit strings are therefore not useful product data in its free-text
    fields and are treated as potentially sensitive account/PAN input.  The
    helper is shared by every free-text validator so a raw identifier cannot
    move from a budget note into a cost-plan vendor/purpose field.
    """

    return bool(
        RAW_IBAN_PATTERN.search(value)
        or RAW_ACCOUNT_OR_PAN_PATTERN.search(value)
        or RAW_TRANSACTION_HASH_PATTERN.search(value)
    )


def _clean_text(value: Any, *, label: str, minimum: int, maximum: int, multiline: bool = False, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} phải là text")
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not multiline and "\n" in normalized:
        raise ValueError(f"{label} không được xuống dòng")
    if not multiline:
        normalized = re.sub(r"\s+", " ", normalized)
    if not normalized and allow_empty:
        return ""
    if not (minimum <= len(normalized) <= maximum):
        raise ValueError(f"{label} phải có từ {minimum} đến {maximum} ký tự")
    if UNSAFE_CONTROL_PATTERN.search(normalized) or MARKUP_PATTERN.search(normalized):
        raise ValueError(f"{label} có định dạng không an toàn")
    if SECRET_PATTERN.search(normalized) or KNOWN_SECRET_PATTERN.search(normalized):
        raise ValueError(f"{label} không nhận token, mật khẩu hoặc secret")
    if PAYMENT_PROOF_PATTERN.search(normalized) or _contains_raw_financial_identifier(normalized):
        raise ValueError(f"{label} không nhận bill, TXID, QR, số tài khoản hoặc thông tin thanh toán")
    return normalized


def _period(value: Any) -> str:
    normalized = str(value or "").strip()
    if not PERIOD_PATTERN.fullmatch(normalized):
        raise ValueError("Kỳ kế hoạch phải theo dạng YYYY-MM")
    try:
        datetime.strptime(normalized + "-01", "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("Kỳ kế hoạch không hợp lệ") from exc
    return normalized


def _planned_for(value: Any, *, period: str) -> str:
    normalized = str(value or "").strip()
    if not DATE_PATTERN.fullmatch(normalized):
        raise ValueError("Ngày kế hoạch phải theo dạng YYYY-MM-DD")
    try:
        parsed = datetime.strptime(normalized, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("Ngày kế hoạch không hợp lệ") from exc
    if parsed.strftime("%Y-%m") != period:
        raise ValueError("Ngày kế hoạch phải thuộc đúng kỳ đã chọn")
    return normalized


def _category(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in CATEGORIES:
        raise ValueError("Nhóm chi phí kế hoạch không hợp lệ")
    return normalized


def _amount(value: Any) -> int:
    # Pydantic's StrictInt prevents float/string coercion before this helper.
    if isinstance(value, bool) or not isinstance(value, int) or not (1 <= value <= MAX_AMOUNT_VND):
        raise ValueError("Giá trị kế hoạch VND không hợp lệ")
    return int(value)


def _idempotency_key(value: Any) -> str:
    normalized = str(value or "").strip()
    if not IDEMPOTENCY_PATTERN.fullmatch(normalized):
        raise ValueError("Idempotency key không hợp lệ")
    return normalized


def _uuid(value: Any, *, label: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail=f"{label} không hợp lệ") from exc


def _list_limit(value: int) -> int:
    return max(1, min(int(value), MAX_LIST_LIMIT))


def _list_offset(value: int) -> int:
    return max(0, min(int(value), MAX_LIST_OFFSET))


class BudgetCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    period: StrictStr
    category: StrictStr
    planned_vnd: StrictInt
    note: StrictStr = ""
    confirm_budget: StrictBool
    idempotency_key: StrictStr

    @field_validator("period")
    @classmethod
    def validate_period(cls, value: str) -> str:
        return _period(value)

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        return _category(value)

    @field_validator("planned_vnd")
    @classmethod
    def validate_amount(cls, value: int) -> int:
        return _amount(value)

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str) -> str:
        return _clean_text(value, label="Ghi chú ngân sách", minimum=0, maximum=500, multiline=True, allow_empty=True)

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)

    def model_post_init(self, __context: Any) -> None:
        if self.confirm_budget is not True:
            raise ValueError("Cần xác nhận trước khi lưu ngân sách kế hoạch")


class CostPlanCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    period: StrictStr
    planned_for: StrictStr
    category: StrictStr
    planned_vnd: StrictInt
    vendor_label: StrictStr = ""
    purpose: StrictStr
    confirm_plan: StrictBool
    idempotency_key: StrictStr

    @field_validator("period")
    @classmethod
    def validate_period(cls, value: str) -> str:
        return _period(value)

    @field_validator("planned_for")
    @classmethod
    def validate_date_shape(cls, value: str) -> str:
        if not DATE_PATTERN.fullmatch(value.strip()):
            raise ValueError("Ngày kế hoạch phải theo dạng YYYY-MM-DD")
        return value.strip()

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        return _category(value)

    @field_validator("planned_vnd")
    @classmethod
    def validate_amount(cls, value: int) -> int:
        return _amount(value)

    @field_validator("vendor_label")
    @classmethod
    def validate_vendor(cls, value: str) -> str:
        return _clean_text(value, label="Nhãn đối tác", minimum=0, maximum=120, allow_empty=True)

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, value: str) -> str:
        return _clean_text(value, label="Mục đích kế hoạch", minimum=4, maximum=700, multiline=True)

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)

    def model_post_init(self, __context: Any) -> None:
        _planned_for(self.planned_for, period=self.period)
        if self.confirm_plan is not True:
            raise ValueError("Cần xác nhận trước khi tạo kế hoạch chi phí")


class BudgetStateRequest(BaseModel):
    """Archive or restore one Web-owned budget with optimistic concurrency."""

    model_config = ConfigDict(extra="forbid", strict=True)

    state: StrictStr
    expected_revision: StrictInt = Field(ge=1)
    confirm_change: StrictBool
    idempotency_key: StrictStr

    @field_validator("state")
    @classmethod
    def validate_state(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in BUDGET_STATES:
            raise ValueError("Trạng thái ngân sách không hợp lệ")
        return normalized

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)

    def model_post_init(self, __context: Any) -> None:
        if self.confirm_change is not True:
            raise ValueError("Cần xác nhận trước khi đổi trạng thái ngân sách")


class CostPlanStateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    state: StrictStr
    expected_revision: StrictInt = Field(ge=1)
    confirm_change: StrictBool
    idempotency_key: StrictStr

    @field_validator("state")
    @classmethod
    def validate_state(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in COST_STATES:
            raise ValueError("Trạng thái kế hoạch không hợp lệ")
        return normalized

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)

    def model_post_init(self, __context: Any) -> None:
        if self.confirm_change is not True:
            raise ValueError("Cần xác nhận trước khi đổi trạng thái kế hoạch")


def _budget_public(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "period": str(row[1]),
        "category": str(row[2]),
        "category_label": CATEGORY_LABELS.get(str(row[2]), "Khác"),
        "planned_vnd": int(row[3]),
        "note": str(row[4]),
        "state": str(row[5]),
        "revision": int(row[6]),
        "created_at": str(row[7]),
        "updated_at": str(row[8]),
        "archived_at": str(row[9]) if row[9] else None,
        "execution": "web_native_finance_budget_plan",
    }


def _cost_public(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "period": str(row[1]),
        "planned_for": str(row[2]),
        "category": str(row[3]),
        "category_label": CATEGORY_LABELS.get(str(row[3]), "Khác"),
        "planned_vnd": int(row[4]),
        "vendor_label": str(row[5]),
        "purpose": str(row[6]),
        "state": str(row[7]),
        "revision": int(row[8]),
        "created_at": str(row[9]),
        "updated_at": str(row[10]),
        "archived_at": str(row[11]) if row[11] else None,
        "execution": "web_native_finance_cost_plan",
    }


def _audit(conn: Any, *, request: Request, account: dict, action: str, record_id: str, detail: str) -> None:
    _record_audit(
        conn,
        account_id=str(account["id"]),
        canonical_user_id=None,
        action=action,
        request_id=_request_id(request),
        target=f"web-finance-planning:{record_id}",
        detail=detail[:280],
    )


def _event(conn: Any, *, record_kind: str, record_id: str, account_id: str, action: str, state: str, revision: int) -> None:
    conn.execute(
        """INSERT INTO web_finance_planning_events
           (id, record_kind, record_id, actor_account_id, action, state, revision, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), record_kind, record_id, account_id, action, state, revision, utc_now()),
    )


def _fingerprint(value: dict[str, Any]) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _safe_receipt(response: dict[str, Any]) -> dict[str, Any]:
    """Persist an idempotency receipt without planning text or amounts."""

    if not isinstance(response, dict) or response.get("ok") is not True:
        return response
    source = response.get("data") if isinstance(response.get("data"), dict) else {}
    data: dict[str, Any] = {}
    for key in ("budget", "cost_plan"):
        item = source.get(key) if isinstance(source.get(key), dict) else {}
        if isinstance(item.get("id"), str):
            data[key] = {
                "id": item["id"],
                "state": str(item.get("state") or ""),
                "revision": int(item.get("revision") or 0),
            }
    for key, value in _boundary(persisted=False).items():
        if key in source:
            data[key] = value
    return envelope(
        True,
        str(response.get("message") or "Đã lưu kế hoạch vận hành Web."),
        data=data,
        status_name=str(response.get("status") or "completed"),
    )


def _idempotent(
    *,
    scope: str,
    key: str,
    fingerprint: str,
    operation: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    ensure_finance_planning_schema()
    cutoff = (datetime.now(timezone.utc) - IDEMPOTENCY_RETENTION).isoformat(timespec="seconds")
    with transaction() as conn:
        conn.execute("DELETE FROM web_idempotency WHERE scope LIKE ? AND created_at < ?", ("web-finance-planning:%", cutoff))
        existing = conn.execute(
            "SELECT response_json, request_fingerprint FROM web_idempotency WHERE scope=? AND key=?",
            (scope, key),
        ).fetchone()
        if existing:
            if not hmac.compare_digest(str(existing[1] or ""), fingerprint):
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho yêu cầu khác")
            try:
                receipt = json.loads(str(existing[0]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Receipt Finance Planning không hợp lệ") from exc
            if not isinstance(receipt, dict):
                raise HTTPException(status_code=409, detail="Receipt Finance Planning không hợp lệ")
            return receipt
        count = conn.execute(
            "SELECT COUNT(*) FROM web_idempotency WHERE scope LIKE ?", ("web-finance-planning:%",)
        ).fetchone()
        if int(count[0] or 0) >= IDEMPOTENCY_MAX_RECORDS:
            return envelope(
                False,
                "Kho receipt Finance Planning tạm thời đang đầy. Vui lòng thử lại sau.",
                data=_boundary(persisted=False),
                status_name="guarded",
                error_code="WEB_FINANCE_PLANNING_IDEMPOTENCY_LIMIT",
            )
        result = operation(conn)
        if result.get("ok") is True:
            receipt = _safe_receipt(result)
            conn.execute(
                "INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at) VALUES (?, ?, ?, ?, ?)",
                (scope, key, json.dumps(receipt, ensure_ascii=False, separators=(",", ":")), fingerprint, utc_now()),
            )
            # A first submission receives the complete, server-validated
            # record so the UI can refresh deterministically.  Only a later
            # replay gets the deliberately minimal receipt above.
            return result
    return result


def _summary(period: str) -> dict[str, Any]:
    ensure_finance_planning_schema()
    with read_transaction() as conn:
        budget_rows = conn.execute(
            """SELECT category, COALESCE(SUM(planned_vnd), 0)
               FROM web_finance_planning_budgets
               WHERE period=? AND state='active' AND archived_at IS NULL
               GROUP BY category""",
            (period,),
        ).fetchall()
        cost_rows = conn.execute(
            """SELECT category, COALESCE(SUM(planned_vnd), 0), COUNT(*)
               FROM web_finance_planning_costs
               WHERE period=? AND state != 'archived' AND archived_at IS NULL
               GROUP BY category""",
            (period,),
        ).fetchall()
        review_rows = conn.execute(
            """SELECT category, COALESCE(SUM(planned_vnd), 0), COUNT(*)
               FROM web_finance_planning_costs
               WHERE period=? AND state='review' AND archived_at IS NULL
               GROUP BY category""",
            (period,),
        ).fetchall()
    budget_by_category = {str(category): int(amount or 0) for category, amount in budget_rows}
    cost_by_category = {str(category): (int(amount or 0), int(count or 0)) for category, amount, count in cost_rows}
    review_by_category = {str(category): (int(amount or 0), int(count or 0)) for category, amount, count in review_rows}
    categories: list[dict[str, Any]] = []
    for category in sorted(CATEGORIES):
        budget = budget_by_category.get(category, 0)
        cost, count = cost_by_category.get(category, (0, 0))
        review, review_count = review_by_category.get(category, (0, 0))
        categories.append({
            "category": category,
            "category_label": CATEGORY_LABELS[category],
            "budget_vnd": budget,
            "planned_vnd": cost,
            "remaining_vnd": budget - cost,
            "cost_plan_count": count,
            "review_vnd": review,
            "review_count": review_count,
        })
    return {
        "period": period,
        "budget_vnd": sum(item["budget_vnd"] for item in categories),
        "planned_vnd": sum(item["planned_vnd"] for item in categories),
        "remaining_vnd": sum(item["remaining_vnd"] for item in categories),
        "cost_plan_count": sum(item["cost_plan_count"] for item in categories),
        "review_vnd": sum(item["review_vnd"] for item in categories),
        "review_count": sum(item["review_count"] for item in categories),
        "categories": categories,
    }


def _default_period() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


@router.get("/policy")
def finance_planning_policy(_account: dict = Depends(require_admin)):
    _require_enabled()
    return envelope(
        True,
        "Finance Operations Planning chỉ lưu kế hoạch Web-native.",
        data={
            "categories": [{"id": key, "label": CATEGORY_LABELS[key]} for key in sorted(CATEGORIES)],
            "budget_states": sorted(BUDGET_STATES),
            "budget_transitions": {key: sorted(value) for key, value in BUDGET_TRANSITIONS.items()},
            "cost_states": sorted(COST_STATES),
            "cost_transitions": {key: sorted(value) for key, value in COST_TRANSITIONS.items()},
            "amount_currency": "VND",
            "manual_payment_evidence_accepted": False,
            **_boundary(persisted=False),
        },
        status_name="completed",
    )


@router.get("/summary")
def finance_planning_summary(
    period: str = Query(default="", max_length=7),
    _account: dict = Depends(require_admin),
):
    _require_enabled()
    selected_period = _period(period or _default_period())
    return envelope(
        True,
        "Đã nạp tổng quan kế hoạch vận hành Web.",
        data={"summary": _summary(selected_period), **_boundary(persisted=False)},
        status_name="completed",
    )


@router.get("/budgets")
def list_budgets(
    period: str = Query(default="", max_length=7),
    state: str = Query(default="active", max_length=16),
    limit: int = Query(default=30, ge=1, le=MAX_LIST_LIMIT),
    offset: int = Query(default=0, ge=0, le=MAX_LIST_OFFSET),
    _account: dict = Depends(require_admin),
):
    _require_enabled()
    selected_period = _period(period or _default_period())
    selected_state = str(state or "active").strip().lower()
    if selected_state not in {"all", *BUDGET_STATES}:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái ngân sách không hợp lệ")
    safe_limit, safe_offset = _list_limit(limit), _list_offset(offset)
    ensure_finance_planning_schema()
    clauses = ["period=?"]
    params: list[Any] = [selected_period]
    if selected_state == "active":
        clauses.append("state='active' AND archived_at IS NULL")
    elif selected_state == "archived":
        clauses.append("state='archived'")
    where = " AND ".join(clauses)
    with read_transaction() as conn:
        total_row = conn.execute(
            f"SELECT COUNT(*) FROM web_finance_planning_budgets WHERE {where}", params
        ).fetchone()
        rows = conn.execute(
            f"""SELECT id, period, category, planned_vnd, note, state, revision, created_at, updated_at, archived_at
                FROM web_finance_planning_budgets WHERE {where}
                ORDER BY category ASC, updated_at DESC, id ASC LIMIT ? OFFSET ?""",
            [*params, safe_limit, safe_offset],
        ).fetchall()
    total = int(total_row[0] or 0)
    items = [_budget_public(row) for row in rows]
    return envelope(
        True,
        "Đã nạp ngân sách kế hoạch Web.",
        data={
            "items": items,
            "period": selected_period,
            "state": selected_state,
            "limit": safe_limit,
            "offset": safe_offset,
            "total": total,
            "has_more": safe_offset + len(items) < total,
            "next_offset": safe_offset + len(items) if safe_offset + len(items) < total else None,
            **_boundary(persisted=False),
        },
        status_name="completed",
    )


@router.get("/cost-plans")
def list_cost_plans(
    period: str = Query(default="", max_length=7),
    state: str = Query(default="all", max_length=16),
    category: str = Query(default="all", max_length=32),
    limit: int = Query(default=50, ge=1, le=MAX_LIST_LIMIT),
    offset: int = Query(default=0, ge=0, le=MAX_LIST_OFFSET),
    _account: dict = Depends(require_admin),
):
    _require_enabled()
    selected_period = _period(period or _default_period())
    selected_state = str(state or "all").strip().lower()
    selected_category = str(category or "all").strip().lower()
    if selected_state not in {"all", *COST_STATES}:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái kế hoạch không hợp lệ")
    if selected_category not in {"all", *CATEGORIES}:
        raise HTTPException(status_code=422, detail="Bộ lọc nhóm kế hoạch không hợp lệ")
    safe_limit, safe_offset = _list_limit(limit), _list_offset(offset)
    ensure_finance_planning_schema()
    clauses = ["period=?"]
    params: list[Any] = [selected_period]
    if selected_state != "all":
        clauses.append("state=?")
        params.append(selected_state)
    if selected_category != "all":
        clauses.append("category=?")
        params.append(selected_category)
    where = " AND ".join(clauses)
    with read_transaction() as conn:
        total_row = conn.execute(
            f"SELECT COUNT(*) FROM web_finance_planning_costs WHERE {where}", params
        ).fetchone()
        rows = conn.execute(
            f"""SELECT id, period, planned_for, category, planned_vnd, vendor_label, purpose,
                       state, revision, created_at, updated_at, archived_at
                FROM web_finance_planning_costs WHERE {where}
                ORDER BY planned_for ASC, updated_at DESC, id ASC LIMIT ? OFFSET ?""",
            [*params, safe_limit, safe_offset],
        ).fetchall()
    total = int(total_row[0] or 0)
    items = [_cost_public(row) for row in rows]
    return envelope(
        True,
        "Đã nạp kế hoạch chi phí Web.",
        data={
            "items": items,
            "period": selected_period,
            "state": selected_state,
            "category": selected_category,
            "limit": safe_limit,
            "offset": safe_offset,
            "total": total,
            "has_more": safe_offset + len(items) < total,
            "next_offset": safe_offset + len(items) if safe_offset + len(items) < total else None,
            **_boundary(persisted=False),
        },
        status_name="completed",
    )


@router.post("/budgets")
def create_budget(request: Request, payload: BudgetCreateRequest, account: dict = Depends(require_admin_csrf)):
    _require_enabled()
    account_id = str(account["id"])
    fingerprint = _fingerprint({
        "period": payload.period,
        "category": payload.category,
        "planned_vnd": payload.planned_vnd,
        "note": payload.note,
        "confirm_budget": payload.confirm_budget,
    })

    def operation(conn: Any) -> dict[str, Any]:
        total = conn.execute("SELECT COUNT(*) FROM web_finance_planning_budgets").fetchone()
        if int(total[0] or 0) >= MAX_BUDGETS:
            return envelope(False, "Kho ngân sách kế hoạch đã đạt giới hạn an toàn.", data=_boundary(persisted=False), status_name="guarded", error_code="WEB_FINANCE_PLANNING_BUDGET_LIMIT")
        duplicate = conn.execute(
            "SELECT id FROM web_finance_planning_budgets WHERE period=? AND category=? AND archived_at IS NULL",
            (payload.period, payload.category),
        ).fetchone()
        if duplicate:
            return envelope(False, "Kỳ và nhóm này đã có ngân sách đang hoạt động. Hãy archive bản cũ trước.", data=_boundary(persisted=False), status_name="guarded", error_code="WEB_FINANCE_PLANNING_BUDGET_EXISTS")
        record_id, now = str(uuid.uuid4()), utc_now()
        conn.execute(
            """INSERT INTO web_finance_planning_budgets
               (id, created_by_account_id, period, category, planned_vnd, note, state, revision, created_at, updated_at, archived_at)
               VALUES (?, ?, ?, ?, ?, ?, 'active', 1, ?, ?, NULL)""",
            (record_id, account_id, payload.period, payload.category, payload.planned_vnd, payload.note, now, now),
        )
        row = conn.execute(
            """SELECT id, period, category, planned_vnd, note, state, revision, created_at, updated_at, archived_at
               FROM web_finance_planning_budgets WHERE id=?""",
            (record_id,),
        ).fetchone()
        _event(conn, record_kind="budget", record_id=record_id, account_id=account_id, action="budget_created", state="active", revision=1)
        _audit(conn, request=request, account=account, action="finance_planning.budget_created", record_id=record_id, detail=f"period={payload.period};category={payload.category};revision=1")
        return envelope(True, "Đã tạo ngân sách kế hoạch Web.", data={"budget": _budget_public(row), **_boundary(persisted=True)}, status_name="completed")

    return _idempotent(scope=f"web-finance-planning:budget:create:{account_id}", key=payload.idempotency_key, fingerprint=fingerprint, operation=operation)


@router.post("/budgets/{budget_id}/state")
def change_budget_state(
    budget_id: str,
    request: Request,
    payload: BudgetStateRequest,
    account: dict = Depends(require_admin_csrf),
):
    """Archive/restore a budget without editing history or a financial ledger."""

    _require_enabled()
    record_id = _uuid(budget_id, label="Mã ngân sách")
    account_id = str(account["id"])
    fingerprint = _fingerprint({
        "id": record_id,
        "state": payload.state,
        "expected_revision": payload.expected_revision,
        "confirm_change": payload.confirm_change,
    })

    def operation(conn: Any) -> dict[str, Any]:
        row = conn.execute(
            """SELECT id, period, category, planned_vnd, note, state, revision, created_at, updated_at, archived_at
               FROM web_finance_planning_budgets WHERE id=?""",
            (record_id,),
        ).fetchone()
        if not row:
            return envelope(False, "Không tìm thấy ngân sách kế hoạch Web.", data=_boundary(persisted=False), status_name="guarded", error_code="WEB_FINANCE_PLANNING_BUDGET_NOT_FOUND")
        current_state, current_revision = str(row[5]), int(row[6])
        if current_revision != payload.expected_revision:
            return envelope(False, "Ngân sách đã được thay đổi ở nơi khác. Hãy tải lại trước khi tiếp tục.", data=_boundary(persisted=False), status_name="guarded", error_code="WEB_FINANCE_PLANNING_REVISION_CONFLICT")
        if payload.state not in BUDGET_TRANSITIONS.get(current_state, frozenset()):
            return envelope(False, "Chuyển trạng thái ngân sách không hợp lệ.", data=_boundary(persisted=False), status_name="guarded", error_code="WEB_FINANCE_PLANNING_STATE_CONFLICT")
        if payload.state == "active":
            active_duplicate = conn.execute(
                """SELECT id FROM web_finance_planning_budgets
                   WHERE period=? AND category=? AND state='active' AND archived_at IS NULL AND id != ?""",
                (str(row[1]), str(row[2]), record_id),
            ).fetchone()
            if active_duplicate:
                return envelope(False, "Đã có ngân sách đang hoạt động cho kỳ và nhóm này. Không thể khôi phục bản cũ.", data=_boundary(persisted=False), status_name="guarded", error_code="WEB_FINANCE_PLANNING_BUDGET_EXISTS")
        next_revision, now = current_revision + 1, utc_now()
        archived_at = now if payload.state == "archived" else None
        conn.execute(
            """UPDATE web_finance_planning_budgets
               SET state=?, revision=?, updated_at=?, archived_at=?
               WHERE id=? AND revision=?""",
            (payload.state, next_revision, now, archived_at, record_id, current_revision),
        )
        updated = conn.execute(
            """SELECT id, period, category, planned_vnd, note, state, revision, created_at, updated_at, archived_at
               FROM web_finance_planning_budgets WHERE id=?""",
            (record_id,),
        ).fetchone()
        _event(conn, record_kind="budget", record_id=record_id, account_id=account_id, action="budget_state_changed", state=payload.state, revision=next_revision)
        _audit(conn, request=request, account=account, action="finance_planning.budget_state_changed", record_id=record_id, detail=f"state={payload.state};revision={next_revision}")
        return envelope(True, "Đã cập nhật trạng thái ngân sách kế hoạch Web.", data={"budget": _budget_public(updated), **_boundary(persisted=True)}, status_name=payload.state)

    return _idempotent(scope=f"web-finance-planning:budget:{record_id}:state:{account_id}", key=payload.idempotency_key, fingerprint=fingerprint, operation=operation)


@router.post("/cost-plans")
def create_cost_plan(request: Request, payload: CostPlanCreateRequest, account: dict = Depends(require_admin_csrf)):
    _require_enabled()
    account_id = str(account["id"])
    fingerprint = _fingerprint({
        "period": payload.period,
        "planned_for": payload.planned_for,
        "category": payload.category,
        "planned_vnd": payload.planned_vnd,
        "vendor_label": payload.vendor_label,
        "purpose": payload.purpose,
        "confirm_plan": payload.confirm_plan,
    })

    def operation(conn: Any) -> dict[str, Any]:
        total = conn.execute("SELECT COUNT(*) FROM web_finance_planning_costs").fetchone()
        if int(total[0] or 0) >= MAX_COST_PLANS:
            return envelope(False, "Kho kế hoạch chi phí đã đạt giới hạn an toàn.", data=_boundary(persisted=False), status_name="guarded", error_code="WEB_FINANCE_PLANNING_COST_LIMIT")
        record_id, now = str(uuid.uuid4()), utc_now()
        conn.execute(
            """INSERT INTO web_finance_planning_costs
               (id, created_by_account_id, period, planned_for, category, planned_vnd, vendor_label, purpose,
                state, revision, created_at, updated_at, archived_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'draft', 1, ?, ?, NULL)""",
            (record_id, account_id, payload.period, payload.planned_for, payload.category, payload.planned_vnd, payload.vendor_label, payload.purpose, now, now),
        )
        row = conn.execute(
            """SELECT id, period, planned_for, category, planned_vnd, vendor_label, purpose,
                       state, revision, created_at, updated_at, archived_at
                FROM web_finance_planning_costs WHERE id=?""",
            (record_id,),
        ).fetchone()
        _event(conn, record_kind="cost_plan", record_id=record_id, account_id=account_id, action="cost_plan_created", state="draft", revision=1)
        _audit(conn, request=request, account=account, action="finance_planning.cost_plan_created", record_id=record_id, detail=f"period={payload.period};category={payload.category};state=draft;revision=1")
        return envelope(True, "Đã tạo kế hoạch chi phí Web ở trạng thái draft.", data={"cost_plan": _cost_public(row), **_boundary(persisted=True)}, status_name="draft")

    return _idempotent(scope=f"web-finance-planning:cost:create:{account_id}", key=payload.idempotency_key, fingerprint=fingerprint, operation=operation)


@router.post("/cost-plans/{cost_plan_id}/state")
def change_cost_plan_state(
    cost_plan_id: str,
    request: Request,
    payload: CostPlanStateRequest,
    account: dict = Depends(require_admin_csrf),
):
    _require_enabled()
    record_id = _uuid(cost_plan_id, label="Mã kế hoạch chi phí")
    account_id = str(account["id"])
    fingerprint = _fingerprint({
        "id": record_id,
        "state": payload.state,
        "expected_revision": payload.expected_revision,
        "confirm_change": payload.confirm_change,
    })

    def operation(conn: Any) -> dict[str, Any]:
        row = conn.execute(
            """SELECT id, period, planned_for, category, planned_vnd, vendor_label, purpose,
                       state, revision, created_at, updated_at, archived_at
                FROM web_finance_planning_costs WHERE id=?""",
            (record_id,),
        ).fetchone()
        if not row:
            return envelope(False, "Không tìm thấy kế hoạch chi phí Web.", data=_boundary(persisted=False), status_name="guarded", error_code="WEB_FINANCE_PLANNING_COST_NOT_FOUND")
        current_state, current_revision = str(row[7]), int(row[8])
        if current_revision != payload.expected_revision:
            return envelope(False, "Kế hoạch đã được thay đổi ở nơi khác. Hãy tải lại trước khi tiếp tục.", data=_boundary(persisted=False), status_name="guarded", error_code="WEB_FINANCE_PLANNING_REVISION_CONFLICT")
        if payload.state not in COST_TRANSITIONS.get(current_state, frozenset()):
            return envelope(False, "Chuyển trạng thái kế hoạch không hợp lệ.", data=_boundary(persisted=False), status_name="guarded", error_code="WEB_FINANCE_PLANNING_STATE_CONFLICT")
        next_revision, now = current_revision + 1, utc_now()
        archived_at = now if payload.state == "archived" else None
        conn.execute(
            """UPDATE web_finance_planning_costs
               SET state=?, revision=?, updated_at=?, archived_at=?
               WHERE id=? AND revision=?""",
            (payload.state, next_revision, now, archived_at, record_id, current_revision),
        )
        updated = conn.execute(
            """SELECT id, period, planned_for, category, planned_vnd, vendor_label, purpose,
                       state, revision, created_at, updated_at, archived_at
                FROM web_finance_planning_costs WHERE id=?""",
            (record_id,),
        ).fetchone()
        _event(conn, record_kind="cost_plan", record_id=record_id, account_id=account_id, action="cost_plan_state_changed", state=payload.state, revision=next_revision)
        _audit(conn, request=request, account=account, action="finance_planning.cost_plan_state_changed", record_id=record_id, detail=f"state={payload.state};revision={next_revision}")
        return envelope(True, "Đã cập nhật trạng thái kế hoạch chi phí Web.", data={"cost_plan": _cost_public(updated), **_boundary(persisted=True)}, status_name=payload.state)

    return _idempotent(scope=f"web-finance-planning:cost:{record_id}:state:{account_id}", key=payload.idempotency_key, fingerprint=fingerprint, operation=operation)
