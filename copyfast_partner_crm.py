"""Private, Web-native Partner & Lead CRM for signed TOAN AAS accounts.

This deliberately small CRM keeps customer-owned partnership and sales-lead
notes in the standalone Web database.  It is not a referral system: it never
calculates commissions, tracks attribution, creates a payout, grants a promo
or membership, contacts a person, or connects to a social platform.  The
frozen Telegram Bot and historical ``affiliate_ops.py`` / ``erp_core.py`` are
not imported or consulted.

The router is intentionally self-contained until an explicit application/UI
integration is reviewed.  Its tables are additive and created lazily here so
this module does not modify the shared database-schema file.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
import re
import uuid
from typing import Any, Callable, Iterator

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, field_validator

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_admin, require_csrf
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction, utc_now


router = APIRouter(prefix="/api/v1/partner-crm", tags=["Web Partner & Lead CRM"])

LEAD_KINDS = frozenset({"customer", "partner", "agency", "creator", "reseller", "other"})
LEAD_STAGES = frozenset({"draft", "qualified", "review", "proposal", "won", "lost", "archived"})
CONSENT_STATES = frozenset({"unknown", "documented", "not_granted", "withdrawn"})
SOURCE_KINDS = frozenset({"manual", "inbound", "partner_intro", "event", "other"})
STAGE_TRANSITIONS = {
    "draft": frozenset({"qualified", "lost", "archived"}),
    "qualified": frozenset({"review", "proposal", "lost", "archived"}),
    "review": frozenset({"proposal", "lost", "archived"}),
    "proposal": frozenset({"won", "lost", "archived"}),
    "won": frozenset({"archived"}),
    "lost": frozenset({"archived"}),
    # Restore is deliberately conservative: an archived record can return
    # only to an unqualified draft, never to a fabricated commercial stage.
    "archived": frozenset({"draft"}),
}

MAX_ACTIVE_LEADS = 250
MAX_NOTES_PER_LEAD = 250
MAX_LIST_LIMIT = 100
MAX_LIST_OFFSET = 10_000
MAX_TAGS = 12
MAX_TAG_LENGTH = 48
IDEMPOTENCY_RETENTION = timedelta(hours=24)
MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT = 1_024
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]{1,64}@[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$")
UNSAFE_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
MARKUP_PATTERN = re.compile(r"(?:<\s*/?\s*[A-Za-z][^>\r\n]{0,240}>|```|\bon[a-z]+\s*=)", re.IGNORECASE)
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|token|"
    r"client[ _-]?secret|secret(?:[ _-]?(?:key|access[ _-]?(?:key))?)?|password|passphrase|authorization)\b\s*"
    r"(?:['\"]\s*)?(?:[:=]|\bis\b)\s*(?:['\"]\s*)?(?:(?:bearer|basic)\s+)?[A-Za-z0-9_./+=:-]{8,}",
    re.IGNORECASE,
)
KNOWN_SECRET_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(?:(?:sk|pk|rk)[_-][A-Za-z0-9_-]{12,}|gh(?:p|o|u|s|r)_[A-Za-z0-9]{12,}|"
    r"github_pat_[A-Za-z0-9_]{12,}|xox(?:b|p|a|r|s)-[A-Za-z0-9-]{12,}|AIza[0-9A-Za-z_-]{20,}|"
    r"(?:AKIA|ASIA)[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
CARD_LIKE_PATTERN = re.compile(r"(?<![0-9A-Za-z])[0-9](?:[\s./-]*[0-9]){12,18}(?![0-9A-Za-z])")
OTP_PATTERN = re.compile(
    r"\b(?:otp|cvv|cvc|pin|mã\s*(?:xác\s*(?:minh|thực)|otp)|ma\s*(?:xac\s*(?:minh|thuc)|otp)|"
    r"verification\s+(?:code|token)|one[ -]?time(?:\s+(?:pass(?:word|code)?|code))?)\b",
    re.IGNORECASE,
)
# Consultation requests deliberately use a closed catalog owned by this
# router.  It mirrors the useful Web-facing topics of Support's Consultation
# Brief, but does not import Support or create an implicit path from a
# non-persistent brief to CRM.  Keep these records distinct so a future
# Support change cannot silently widen this persistent CRM contract.
CONSULTATION_CRM_CATALOG_VERSION = "2026-07-24"
CONSULTATION_CRM_STORAGE_SCOPE = "crm_draft_storage_only"
CONSULTATION_CRM_CONSENT_NOTE = (
    "Khách đã xác nhận chỉ lưu lead draft CRM trong Web; không phải consent liên hệ."
)
CONSULTATION_CRM_GROUPS: tuple[dict[str, Any], ...] = (
    {
        "id": "premium",
        "title": "Gói cao cấp",
        "summary": "Làm rõ phạm vi sử dụng và mức hỗ trợ cần trao đổi trước khi tạo lead draft riêng tư.",
        "services": (
            {
                "id": "web-premium-creator",
                "category": "premium_lead",
                "title": "Cá nhân / Creator",
                "summary": "Tư vấn cách tổ chức công việc sáng tạo cá nhân trong Web App.",
                "prompt": "Nêu loại nội dung và nhịp làm việc bạn muốn tối ưu.",
            },
            {
                "id": "web-premium-shop",
                "category": "premium_lead",
                "title": "Shop / Affiliate",
                "summary": "Làm rõ nhu cầu nội dung, vận hành hoặc báo cáo cho hoạt động bán hàng.",
                "prompt": "Nêu quy trình bán hàng hoặc kênh nội dung cần được trao đổi.",
            },
            {
                "id": "web-premium-business",
                "category": "premium_lead",
                "title": "Doanh nghiệp",
                "summary": "Chuẩn bị bối cảnh đội nhóm và yêu cầu vận hành ở mức không nhạy cảm.",
                "prompt": "Nêu quy mô công việc, vai trò sử dụng và ràng buộc cần cân nhắc.",
            },
            {
                "id": "web-premium-private",
                "category": "premium_lead",
                "title": "Trao đổi riêng về nhu cầu",
                "summary": "Đặt câu hỏi về phạm vi phù hợp mà không tạo báo giá hoặc cam kết dịch vụ.",
                "prompt": "Nêu vấn đề cần làm rõ và tiêu chí bạn muốn dùng để đánh giá.",
            },
        ),
    },
    {
        "id": "custom_bot",
        "title": "Giải pháp tùy chỉnh",
        "summary": "Mô tả bài toán Web ở mức tổng quát; yêu cầu này không tạo Bot, kết nối hay cấu hình mới.",
        "services": (
            {
                "id": "web-custom-shop",
                "category": "custom_bot_lead",
                "title": "Quy trình cho shop",
                "summary": "Trao đổi về luồng hỗ trợ hoạt động bán hàng hoặc vận hành shop.",
                "prompt": "Nêu các bước thủ công hiện tại và điểm cần được cải thiện.",
            },
            {
                "id": "web-custom-content",
                "category": "custom_bot_lead",
                "title": "Quy trình nội dung",
                "summary": "Làm rõ nhu cầu biên tập, phê duyệt hoặc tổ chức nội dung.",
                "prompt": "Nêu loại nội dung, các bước review và kết quả cần có.",
            },
            {
                "id": "web-custom-support",
                "category": "custom_bot_lead",
                "title": "Quy trình hỗ trợ khách hàng",
                "summary": "Xác định bối cảnh hỗ trợ và thông tin cần tổ chức trong Web.",
                "prompt": "Nêu các nhóm câu hỏi hoặc bước chăm sóc cần được làm rõ.",
            },
            {
                "id": "web-custom-internal",
                "category": "custom_bot_lead",
                "title": "Vận hành nội bộ",
                "summary": "Trao đổi nhu cầu phối hợp, theo dõi hoặc chuẩn hóa công việc nội bộ.",
                "prompt": "Nêu vai trò tham gia, quy trình hiện có và điểm đang bị gián đoạn.",
            },
            {
                "id": "web-custom-custom",
                "category": "custom_bot_lead",
                "title": "Bài toán khác",
                "summary": "Bắt đầu từ vấn đề cụ thể trước khi đánh giá phạm vi phù hợp.",
                "prompt": "Nêu vấn đề cốt lõi và kết quả tối thiểu bạn muốn đạt được.",
            },
        ),
    },
    {
        "id": "service",
        "title": "Tư vấn dịch vụ",
        "summary": "Chọn loại công việc để chuẩn bị yêu cầu rõ ràng; không kích hoạt engine, báo giá hoặc output.",
        "services": (
            {
                "id": "web-service-image",
                "category": "service_consulting",
                "title": "Ảnh / thiết kế",
                "summary": "Tìm hiểu loại đầu ra hình ảnh hoặc quy trình thiết kế phù hợp.",
                "prompt": "Nêu loại ảnh, mục đích sử dụng và tiêu chí đầu ra cần làm rõ.",
            },
            {
                "id": "web-service-video",
                "category": "service_consulting",
                "title": "Video",
                "summary": "Làm rõ nhu cầu video, cấu trúc nội dung và cách review trong Web.",
                "prompt": "Nêu mục tiêu video, định dạng dự kiến và các bước bạn muốn trao đổi.",
            },
            {
                "id": "web-service-frame-video",
                "category": "service_consulting",
                "title": "Ảnh thành video",
                "summary": "Chuẩn bị câu hỏi về biến đổi hình ảnh thành chuyển động hoặc storyboard.",
                "prompt": "Nêu loại tư liệu đầu vào và phong cách chuyển động muốn tìm hiểu.",
            },
            {
                "id": "web-service-document",
                "category": "service_consulting",
                "title": "Tài liệu / PDF",
                "summary": "Trao đổi nhu cầu xử lý, tổ chức hoặc xuất tài liệu trong luồng phù hợp.",
                "prompt": "Nêu loại tài liệu và thao tác hoặc kết quả cần được tư vấn.",
            },
            {
                "id": "web-service-voice",
                "category": "service_consulting",
                "title": "Giọng nói / âm thanh",
                "summary": "Làm rõ use case audio, lời đọc hoặc nội dung cần chuẩn bị.",
                "prompt": "Nêu mục đích sử dụng âm thanh và yêu cầu nội dung ở mức tổng quát.",
            },
            {
                "id": "web-service-package",
                "category": "service_consulting",
                "title": "Gói và khả năng sử dụng",
                "summary": "Đặt câu hỏi về khả năng phù hợp, không tạo đơn hoặc thay đổi giá/quyền.",
                "prompt": "Nêu cách bạn dự định sử dụng và điều cần được làm rõ trước khi quyết định.",
            },
        ),
    },
)
CONSULTATION_CRM_SERVICES = {
    str(service["id"]): {**service, "group_id": str(group["id"])}
    for group in CONSULTATION_CRM_GROUPS
    for service in group["services"]
}
EMAIL_ADDRESS_PATTERN = re.compile(
    r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9][A-Za-z0-9._%+-]{0,63}@[A-Za-z0-9-]{1,63}(?:\.[A-Za-z0-9-]{1,63})+(?![A-Za-z0-9.-])",
    re.IGNORECASE,
)
PHONE_NUMBER_PATTERN = re.compile(r"(?<!\d)(?:\+?84|0)(?:[\s().-]*\d){8,10}(?!\d)")
CONTACT_LABEL_PATTERN = re.compile(
    r"\b(?:email|e-mail|zalo|telegram|phone|số\s*điện\s*thoại|so\s*dien\s*thoai|sđt|sdt)\s*(?:[:=]|là|la)\s*\S+",
    re.IGNORECASE,
)
TELEGRAM_HANDLE_PATTERN = re.compile(r"(?<![A-Za-z0-9._])@[A-Za-z][A-Za-z0-9_]{4,31}\b")
# This intake is not a manual-payment or receipt-review surface.  Rejecting
# these markers server-side keeps a direct API caller from storing payment
# evidence in an otherwise private CRM narrative just because the Portal has
# already hidden that flow.
CONSULTATION_PAYMENT_PROOF_PATTERN = re.compile(
    r"\b(?:tx(?:id|n)?|transaction\s+(?:hash|id|reference|no\.?|number)|"
    r"mã\s*(?:(?:giao\s*)?(?:dịch|gd)|tham\s*chiếu|thanh\s*toán)|"
    r"ma\s*(?:(?:giao\s*)?(?:dich|gd)|tham\s*chieu|thanh\s*toan)|"
    r"biên\s*lai|bien\s*lai|chứng\s*từ|chung\s*tu|bill|số\s*tài\s*khoản|"
    r"so\s*tai\s*khoan|stk|tài\s*khoản\s*(?:ngân\s*hàng|bank)|"
    r"tai\s*khoan\s*(?:ngan\s*hang|bank)|bank\s+account|account\s+(?:number|no|id)|"
    r"qr\s*(?:code|thanh\s*toán|thanh\s*toan)?)\b",
    re.IGNORECASE,
)


def partner_crm_enabled() -> bool:
    """Keep the isolated CRM fail-closed when an operator disables it."""

    return os.environ.get("WEBAPP_PARTNER_CRM_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def _require_enabled() -> None:
    if not partner_crm_enabled():
        raise HTTPException(
            status_code=503,
            detail="Partner & Lead CRM đang tạm dừng để bảo trì. WEBAPP_PARTNER_CRM_ENABLED chưa được bật.",
        )


def ensure_partner_crm_schema() -> None:
    """Create only the isolated Partner CRM tables, never Bot/ERP tables."""

    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_partner_crm_leads (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                lead_name TEXT NOT NULL,
                organization TEXT NOT NULL DEFAULT '',
                contact_email TEXT NOT NULL DEFAULT '',
                lead_kind TEXT NOT NULL,
                opportunity_summary TEXT NOT NULL,
                source_kind TEXT NOT NULL DEFAULT 'manual',
                source_label TEXT NOT NULL DEFAULT '',
                tags_json TEXT NOT NULL DEFAULT '[]',
                consent_status TEXT NOT NULL DEFAULT 'unknown',
                consent_note TEXT NOT NULL DEFAULT '',
                stage TEXT NOT NULL DEFAULT 'draft',
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_partner_crm_notes (
                id TEXT PRIMARY KEY,
                lead_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(lead_id) REFERENCES web_partner_crm_leads(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_partner_crm_events (
                id TEXT PRIMARY KEY,
                lead_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                action TEXT NOT NULL,
                stage TEXT NOT NULL,
                revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(lead_id) REFERENCES web_partner_crm_leads(id),
                FOREIGN KEY(account_id) REFERENCES web_accounts(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_partner_crm_leads_account_stage_updated "
            "ON web_partner_crm_leads(account_id, stage, updated_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_partner_crm_notes_lead_account_created "
            "ON web_partner_crm_notes(lead_id, account_id, created_at DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_web_partner_crm_events_lead_account_created "
            "ON web_partner_crm_events(lead_id, account_id, created_at DESC, id DESC)"
        )


def _sensitive(value: str) -> bool:
    return bool(
        SECRET_ASSIGNMENT_PATTERN.search(value)
        or KNOWN_SECRET_PATTERN.search(value)
        or CARD_LIKE_PATTERN.search(value)
        or OTP_PATTERN.search(value)
    )


def _text(
    value: Any,
    *,
    label: str,
    minimum: int,
    maximum: int,
    allow_empty: bool = False,
    multiline: bool = False,
) -> str:
    raw = str(value or "")
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n").strip() if multiline else re.sub(r"\s+", " ", raw).strip()
    if UNSAFE_CONTROL_PATTERN.search(normalized) or len(normalized) > maximum or (not allow_empty and len(normalized) < minimum):
        if allow_empty:
            raise ValueError(f"{label} tối đa {maximum} ký tự hợp lệ")
        raise ValueError(f"{label} cần từ {minimum} đến {maximum} ký tự hợp lệ")
    if normalized and (MARKUP_PATTERN.search(normalized) or _sensitive(normalized)):
        raise ValueError(f"{label} không nhận markup, secret, token, OTP hoặc dữ liệu thẻ")
    return normalized


def _contains_consultation_contact(value: str) -> bool:
    """Reject direct contact data from the signed-account intake narrative.

    The signed Web account owns the new CRM record.  Letting a browser put an
    email, phone number, Zalo reference or Telegram handle into its free text
    would turn a storage-only consent into an ambiguous contact instruction.
    """

    text = str(value or "")
    return bool(
        EMAIL_ADDRESS_PATTERN.search(text)
        or PHONE_NUMBER_PATTERN.search(text)
        or CONTACT_LABEL_PATTERN.search(text)
        or TELEGRAM_HANDLE_PATTERN.search(text)
    )


def _consultation_line(value: Any, *, label: str, minimum: int, maximum: int) -> str:
    normalized = _text(value, label=label, minimum=minimum, maximum=maximum)
    if _contains_consultation_contact(normalized):
        raise ValueError(
            "Yêu cầu tư vấn dùng signed Web account; không nhập email, số điện thoại, Zalo hoặc Telegram vào nội dung"
        )
    if CONSULTATION_PAYMENT_PROOF_PATTERN.search(normalized):
        raise ValueError("Yêu cầu tư vấn không nhận bill, TXID, số tài khoản, QR hoặc thông tin thanh toán")
    return normalized


def _consultation_text(value: Any, *, label: str, minimum: int, maximum: int) -> str:
    normalized = _text(value, label=label, minimum=minimum, maximum=maximum, multiline=True)
    if _contains_consultation_contact(normalized):
        raise ValueError(
            "Yêu cầu tư vấn dùng signed Web account; không nhập email, số điện thoại, Zalo hoặc Telegram vào nội dung"
        )
    if CONSULTATION_PAYMENT_PROOF_PATTERN.search(normalized):
        raise ValueError("Yêu cầu tư vấn không nhận bill, TXID, số tài khoản, QR hoặc thông tin thanh toán")
    return normalized


def _code(value: Any, *, label: str, allowed: frozenset[str]) -> str:
    normalized = _text(value, label=label, minimum=1, maximum=32).lower()
    if normalized not in allowed:
        raise ValueError(f"{label} không hợp lệ")
    return normalized


def _email(value: Any) -> str:
    normalized = _text(value, label="Email liên hệ", minimum=0, maximum=254, allow_empty=True).lower()
    if normalized and not EMAIL_PATTERN.fullmatch(normalized):
        raise ValueError("Email liên hệ không hợp lệ")
    return normalized


def _consultation_service_id(value: Any) -> str:
    normalized = _text(value, label="Loại tư vấn Web", minimum=3, maximum=64).lower()
    if normalized not in CONSULTATION_CRM_SERVICES:
        raise ValueError("Loại tư vấn Web không hợp lệ")
    return normalized


def _consultation_service_public(service: dict[str, Any]) -> dict[str, str]:
    """Project one immutable catalog entry; no prices or contact controls."""

    return {
        "id": str(service["id"]),
        "group_id": str(service["group_id"]),
        "category": str(service["category"]),
        "title": str(service["title"]),
        "summary": str(service["summary"]),
        "prompt": str(service["prompt"]),
    }


def _consultation_catalog_public() -> list[dict[str, Any]]:
    return [
        {
            "id": str(group["id"]),
            "title": str(group["title"]),
            "summary": str(group["summary"]),
            "services": [_consultation_service_public(CONSULTATION_CRM_SERVICES[str(service["id"])]) for service in group["services"]],
        }
        for group in CONSULTATION_CRM_GROUPS
    ]


def _tags(value: Any) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("Tags phải là danh sách")
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        tag = _text(item, label="Tag", minimum=1, maximum=MAX_TAG_LENGTH)
        fingerprint = tag.casefold()
        if fingerprint not in seen:
            seen.add(fingerprint)
            result.append(tag)
    if len(result) > MAX_TAGS:
        raise ValueError(f"Tags tối đa {MAX_TAGS} mục")
    return result


def _decode_tags(value: Any) -> list[str]:
    try:
        parsed = json.loads(str(value or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    try:
        return _tags(parsed)
    except ValueError:
        return []


def _uuid(value: Any, *, label: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail=f"{label} không hợp lệ") from exc


def _idempotency_key(value: Any) -> str:
    key = str(value or "").strip()
    if not IDEMPOTENCY_PATTERN.fullmatch(key):
        raise ValueError("Idempotency key không hợp lệ")
    return key


class LeadFields(BaseModel):
    """Bounded, owner-authored metadata; never a contact/payout instruction."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    lead_name: StrictStr
    organization: StrictStr = ""
    contact_email: StrictStr = ""
    lead_kind: StrictStr = "customer"
    opportunity_summary: StrictStr
    source_kind: StrictStr = "manual"
    source_label: StrictStr = ""
    tags: list[StrictStr] = Field(default_factory=list)
    consent_status: StrictStr = "unknown"
    consent_note: StrictStr = ""

    @field_validator("lead_name")
    @classmethod
    def validate_lead_name(cls, value: str) -> str:
        return _text(value, label="Tên lead", minimum=2, maximum=120)

    @field_validator("organization")
    @classmethod
    def validate_organization(cls, value: str) -> str:
        return _text(value, label="Tổ chức", minimum=0, maximum=160, allow_empty=True)

    @field_validator("contact_email")
    @classmethod
    def validate_contact_email(cls, value: str) -> str:
        return _email(value)

    @field_validator("lead_kind")
    @classmethod
    def validate_lead_kind(cls, value: str) -> str:
        return _code(value, label="Nhóm lead", allowed=LEAD_KINDS)

    @field_validator("opportunity_summary")
    @classmethod
    def validate_opportunity_summary(cls, value: str) -> str:
        return _text(value, label="Nhu cầu hoặc cơ hội", minimum=4, maximum=1_000, multiline=True)

    @field_validator("source_kind")
    @classmethod
    def validate_source_kind(cls, value: str) -> str:
        return _code(value, label="Nguồn lead", allowed=SOURCE_KINDS)

    @field_validator("source_label")
    @classmethod
    def validate_source_label(cls, value: str) -> str:
        return _text(value, label="Nhãn nguồn", minimum=0, maximum=160, allow_empty=True)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        return _tags(value)

    @field_validator("consent_status")
    @classmethod
    def validate_consent_status(cls, value: str) -> str:
        return _code(value, label="Trạng thái consent", allowed=CONSENT_STATES)

    @field_validator("consent_note")
    @classmethod
    def validate_consent_note(cls, value: str) -> str:
        return _text(value, label="Ghi chú consent", minimum=0, maximum=500, allow_empty=True, multiline=True)

    def model_post_init(self, __context: Any) -> None:
        # A CRM must not imply consent from a blank or browser-invented field.
        if self.consent_status in {"documented", "withdrawn"} and len(self.consent_note) < 4:
            raise ValueError("Consent documented hoặc withdrawn cần ghi chú tối thiểu 4 ký tự")


class LeadCreateRequest(LeadFields):
    idempotency_key: StrictStr

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)


class ConsultationRequestFields(BaseModel):
    """The deliberately narrow customer consultation contract.

    It is not a variant of ``LeadFields``.  In particular the browser cannot
    choose a source, stage, consent state, tag, contact address or lead kind.
    The server pins those values only after an explicit storage confirmation.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    service_id: StrictStr
    request_title: StrictStr
    need_summary: StrictStr

    @field_validator("service_id")
    @classmethod
    def validate_service_id(cls, value: str) -> str:
        return _consultation_service_id(value)

    @field_validator("request_title")
    @classmethod
    def validate_request_title(cls, value: str) -> str:
        return _consultation_line(value, label="Tiêu đề yêu cầu", minimum=4, maximum=120)

    @field_validator("need_summary")
    @classmethod
    def validate_need_summary(cls, value: str) -> str:
        return _consultation_text(value, label="Nhu cầu cần tư vấn", minimum=12, maximum=1_000)


class ConsultationPreviewRequest(ConsultationRequestFields):
    """Validated but intentionally non-persistent first stage."""


class ConsultationConfirmRequest(ConsultationRequestFields):
    consent_to_store: StrictBool
    confirm_create: StrictBool
    idempotency_key: StrictStr

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)

    def model_post_init(self, __context: Any) -> None:
        if self.consent_to_store is not True:
            raise ValueError("Bạn cần xác nhận consent chỉ để lưu lead draft CRM trong Web")
        if self.confirm_create is not True:
            raise ValueError("Bạn cần xác nhận tạo lead draft CRM trước khi tiếp tục")


class LeadUpdateRequest(LeadFields):
    expected_revision: StrictInt = Field(ge=1)
    idempotency_key: StrictStr

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)


class StageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    stage: StrictStr
    expected_revision: StrictInt = Field(ge=1)
    idempotency_key: StrictStr

    @field_validator("stage")
    @classmethod
    def validate_stage(cls, value: str) -> str:
        return _code(value, label="Pipeline stage", allowed=LEAD_STAGES)

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)


class ConsentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    consent_status: StrictStr
    consent_note: StrictStr = ""
    expected_revision: StrictInt = Field(ge=1)
    idempotency_key: StrictStr

    @field_validator("consent_status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return _code(value, label="Trạng thái consent", allowed=CONSENT_STATES)

    @field_validator("consent_note")
    @classmethod
    def validate_note(cls, value: str) -> str:
        return _text(value, label="Ghi chú consent", minimum=0, maximum=500, allow_empty=True, multiline=True)

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)

    def model_post_init(self, __context: Any) -> None:
        if self.consent_status in {"documented", "withdrawn"} and len(self.consent_note) < 4:
            raise ValueError("Consent documented hoặc withdrawn cần ghi chú tối thiểu 4 ký tự")


class NoteCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    body: StrictStr
    expected_revision: StrictInt = Field(ge=1)
    idempotency_key: StrictStr

    @field_validator("body")
    @classmethod
    def validate_body(cls, value: str) -> str:
        return _text(value, label="Ghi chú lead", minimum=2, maximum=2_000, multiline=True)

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _idempotency_key(value)


def _boundary(*, lead_persisted: bool) -> dict[str, Any]:
    """Explicitly prevent CRM metadata from looking like an action engine."""

    return {
        "execution": "web_native_partner_lead_crm_only",
        "lead_persisted": bool(lead_persisted),
        "telegram_state_changed": False,
        "bot_called": False,
        "bridge_called": False,
        "provider_called": False,
        "remote_lookup_called": False,
        "social_platform_called": False,
        "contacted": False,
        "notification_sent": False,
        "job_created": False,
        "wallet_mutated": False,
        "payment_started": False,
        "payout_created": False,
        "referral_ledger_changed": False,
        "promo_or_membership_changed": False,
        "publish_action_created": False,
    }


def _snapshot(payload: LeadFields, *, stage: str) -> dict[str, Any]:
    return {
        "lead_name": payload.lead_name,
        "organization": payload.organization,
        "contact_email": payload.contact_email,
        "lead_kind": payload.lead_kind,
        "opportunity_summary": payload.opportunity_summary,
        "source_kind": payload.source_kind,
        "source_label": payload.source_label,
        "tags": payload.tags,
        "consent_status": payload.consent_status,
        "consent_note": payload.consent_note,
        "stage": stage,
    }


def _consultation_snapshot(payload: ConsultationRequestFields) -> tuple[dict[str, Any], dict[str, str]]:
    """Build the only CRM projection allowed for a customer consultation.

    This function intentionally owns every generic CRM field.  A caller can
    pass only the closed service identifier and two safe narrative fields;
    no browser-provided CRM metadata reaches ``LeadFields``.
    """

    service = CONSULTATION_CRM_SERVICES[payload.service_id]
    selection = _consultation_service_public(service)
    lead_fields = LeadFields(
        lead_name=payload.request_title,
        organization="",
        contact_email="",
        lead_kind="customer",
        opportunity_summary=payload.need_summary,
        source_kind="inbound",
        source_label=f"Yêu cầu tư vấn Web · {selection['title']}",
        tags=["web-consultation", payload.service_id],
        consent_status="documented",
        consent_note=CONSULTATION_CRM_CONSENT_NOTE,
    )
    return _snapshot(lead_fields, stage="draft"), selection


LEAD_COLUMN_NAMES = (
    "id", "account_id", "lead_name", "organization", "contact_email", "lead_kind", "opportunity_summary",
    "source_kind", "source_label", "tags_json", "consent_status", "consent_note", "stage", "revision",
    "created_at", "updated_at", "archived_at",
)
LEAD_COLUMNS = ", ".join(LEAD_COLUMN_NAMES)
# The manager directory intentionally selects only pipeline metadata.  In
# particular it must not select the owner account, display name, contact
# detail, free-form tags, narrative or even the lead UUID: the directory is
# cross-account visibility without a cross-account detail endpoint.  Tags are
# valid owner input but may contain a person or organisation identifier, so
# they are not anonymous pipeline metadata.
MANAGER_LEAD_COLUMNS = ", ".join((
    "l.lead_kind",
    "l.stage",
    "l.consent_status",
    "l.revision",
    "l.updated_at",
    "l.archived_at",
))


def _lead_row(conn: Any, *, lead_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        f"SELECT {LEAD_COLUMNS} FROM web_partner_crm_leads WHERE id=? AND account_id=?",
        (lead_id, account_id),
    ).fetchone()


def _lead_snapshot(row: tuple[Any, ...], *, stage: str | None = None, consent_status: str | None = None, consent_note: str | None = None) -> dict[str, Any]:
    return {
        "lead_name": str(row[2]),
        "organization": str(row[3]),
        "contact_email": str(row[4]),
        "lead_kind": str(row[5]),
        "opportunity_summary": str(row[6]),
        "source_kind": str(row[7]),
        "source_label": str(row[8]),
        "tags": _decode_tags(row[9]),
        "consent_status": consent_status if consent_status is not None else str(row[10]),
        "consent_note": consent_note if consent_note is not None else str(row[11]),
        "stage": stage if stage is not None else str(row[12]),
    }


def _lead_public(row: tuple[Any, ...], *, include_detail: bool = False) -> dict[str, Any]:
    value = {
        "id": str(row[0]),
        "lead_name": str(row[2]),
        "organization": str(row[3]),
        "lead_kind": str(row[5]),
        "stage": str(row[12]),
        "tags": _decode_tags(row[9]),
        "consent_status": str(row[10]),
        "revision": int(row[13]),
        "created_at": str(row[14]),
        "updated_at": str(row[15]),
        "archived_at": str(row[16]) if row[16] else None,
        "execution": "web_owned_partner_lead",
    }
    if include_detail:
        value.update(_lead_snapshot(row))
    return value


def _manager_directory_item(row: tuple[Any, ...]) -> dict[str, Any]:
    """Return a deliberately redacted, read-only manager directory row.

    The local Web manager may monitor anonymous pipeline health, but does not
    receive a contact address, private opportunity narrative, note, source
    detail, free-form tag, identifier, or mutation control.  A live
    canonical-admin directory would require a separately approved bridge
    boundary and is intentionally absent.
    """

    return {
        "lead_kind": str(row[0]),
        "stage": str(row[1]),
        "consent_status": str(row[2]),
        "revision": int(row[3]),
        "updated_at": str(row[4]),
        "archived_at": str(row[5]) if row[5] else None,
        "execution": "web_manager_read_only_partner_lead_directory",
    }


def _note_public(row: tuple[Any, ...]) -> dict[str, Any]:
    return {"id": str(row[0]), "body": str(row[1]), "created_at": str(row[2])}


def _event_public(row: tuple[Any, ...]) -> dict[str, Any]:
    return {"action": str(row[0]), "stage": str(row[1]), "revision": int(row[2]), "created_at": str(row[3])}


def _event(conn: Any, *, lead_id: str, account_id: str, action: str, stage: str, revision: int) -> None:
    conn.execute(
        """INSERT INTO web_partner_crm_events (id, lead_id, account_id, action, stage, revision, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), lead_id, account_id, action, stage, revision, utc_now()),
    )


def _audit(conn: Any, *, request: Request, account: dict, action: str, target: str, detail: str) -> None:
    _record_audit(
        conn,
        account_id=str(account["id"]),
        canonical_user_id=None,
        action=action,
        request_id=_request_id(request),
        target=target,
        detail=detail[:280],
    )


def _fingerprint(value: dict[str, Any]) -> str:
    material = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _safe_receipt(response: dict[str, Any]) -> dict[str, Any]:
    """Retain only opaque identifiers/state in a replayable receipt."""

    if not isinstance(response, dict) or response.get("ok") is not True:
        return response
    source = response.get("data") if isinstance(response.get("data"), dict) else {}
    data: dict[str, Any] = {}
    lead = source.get("lead") if isinstance(source.get("lead"), dict) else {}
    if isinstance(lead.get("id"), str):
        data["lead"] = {
            "id": lead["id"],
            "revision": int(lead.get("revision") or 0),
            "stage": str(lead.get("stage") or ""),
        }
    note = source.get("note") if isinstance(source.get("note"), dict) else {}
    if isinstance(note.get("id"), str):
        data["note"] = {"id": note["id"], "created_at": str(note.get("created_at") or "")}
    # Consultation confirmations are replayable, but never retain customer
    # title/summary (or any generic CRM narrative) in the idempotency table.
    # Preserve only server-owned selection and the exact, narrow consent
    # interpretation so a replay cannot look like an outbound-contact grant.
    consultation = source.get("consultation") if isinstance(source.get("consultation"), dict) else {}
    service_id = consultation.get("service_id")
    if isinstance(service_id, str) and service_id in CONSULTATION_CRM_SERVICES:
        data["consultation"] = {
            "service_id": service_id,
            "catalog_version": CONSULTATION_CRM_CATALOG_VERSION,
        }
    if source.get("intake_consent_scope") == CONSULTATION_CRM_STORAGE_SCOPE:
        data["intake_consent_scope"] = CONSULTATION_CRM_STORAGE_SCOPE
    if source.get("outbound_contact_authorized") is False:
        data["outbound_contact_authorized"] = False
    for field in _boundary(lead_persisted=False):
        if field in source:
            data[field] = source[field]
    return envelope(
        True,
        str(response.get("message") or "Đã lưu thay đổi CRM riêng tư."),
        data=data,
        status_name=str(response.get("status") or "draft"),
    )


def _idempotent(
    scope: str,
    account_id: str,
    key: str,
    fingerprint: str,
    operation: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    ensure_partner_crm_schema()
    cutoff = (datetime.now(timezone.utc) - IDEMPOTENCY_RETENTION).isoformat(timespec="seconds")
    with transaction() as conn:
        conn.execute("DELETE FROM web_idempotency WHERE scope LIKE ? AND created_at < ?", ("web-partner-crm:%", cutoff))
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
                raise HTTPException(status_code=409, detail="Receipt Partner CRM không hợp lệ") from exc
            if not isinstance(receipt, dict):
                raise HTTPException(status_code=409, detail="Receipt Partner CRM không hợp lệ")
            return receipt
        count = conn.execute(
            "SELECT COUNT(*) FROM web_idempotency WHERE scope LIKE ?",
            (f"web-partner-crm:{account_id}:%",),
        ).fetchone()
        if int(count[0] or 0) >= MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT:
            return envelope(
                False,
                "Kho receipt CRM tạm thời đang đầy. Vui lòng thử lại sau.",
                data=_boundary(lead_persisted=False),
                status_name="guarded",
                error_code="WEB_PARTNER_CRM_IDEMPOTENCY_LIMIT",
            )
        response = operation(conn)
        if response.get("ok") is True:
            receipt = _safe_receipt(response)
            conn.execute(
                "INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at) VALUES (?, ?, ?, ?, ?)",
                (scope, key, json.dumps(receipt, ensure_ascii=False, separators=(",", ":")), fingerprint, utc_now()),
            )
            return receipt
    return response


def _not_found() -> dict[str, Any]:
    return envelope(
        False,
        "Không tìm thấy lead thuộc Web account hiện tại.",
        data=_boundary(lead_persisted=False),
        status_name="guarded",
        error_code="WEB_PARTNER_CRM_LEAD_NOT_FOUND",
    )


def _revision_conflict() -> dict[str, Any]:
    return envelope(
        False,
        "Lead đã được thay đổi ở nơi khác. Hãy tải lại trước khi tiếp tục.",
        data=_boundary(lead_persisted=False),
        status_name="guarded",
        error_code="WEB_PARTNER_CRM_REVISION_CONFLICT",
    )


def _state_conflict() -> dict[str, Any]:
    return envelope(
        False,
        "Lead đang archive. Hãy khôi phục về draft trước khi thay đổi nội dung, note hoặc consent.",
        data=_boundary(lead_persisted=False),
        status_name="guarded",
        error_code="WEB_PARTNER_CRM_ARCHIVED",
    )


def _insert_lead(conn: Any, *, lead_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str, archived_at: str | None = None) -> None:
    conn.execute(
        """INSERT INTO web_partner_crm_leads
           (id, account_id, lead_name, organization, contact_email, lead_kind, opportunity_summary,
            source_kind, source_label, tags_json, consent_status, consent_note, stage, revision,
            created_at, updated_at, archived_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            lead_id, account_id, snapshot["lead_name"], snapshot["organization"], snapshot["contact_email"],
            snapshot["lead_kind"], snapshot["opportunity_summary"], snapshot["source_kind"], snapshot["source_label"],
            json.dumps(snapshot["tags"], ensure_ascii=False), snapshot["consent_status"], snapshot["consent_note"],
            snapshot["stage"], revision, now, now, archived_at,
        ),
    )


def _write_lead(
    conn: Any,
    *,
    lead_id: str,
    account_id: str,
    snapshot: dict[str, Any],
    revision: int,
    now: str,
    archived_at: str | None,
) -> None:
    conn.execute(
        """UPDATE web_partner_crm_leads
           SET lead_name=?, organization=?, contact_email=?, lead_kind=?, opportunity_summary=?,
               source_kind=?, source_label=?, tags_json=?, consent_status=?, consent_note=?,
               stage=?, revision=?, updated_at=?, archived_at=?
           WHERE id=? AND account_id=?""",
        (
            snapshot["lead_name"], snapshot["organization"], snapshot["contact_email"], snapshot["lead_kind"],
            snapshot["opportunity_summary"], snapshot["source_kind"], snapshot["source_label"],
            json.dumps(snapshot["tags"], ensure_ascii=False), snapshot["consent_status"], snapshot["consent_note"],
            snapshot["stage"], revision, now, archived_at, lead_id, account_id,
        ),
    )


def _lead_detail(conn: Any, *, lead_id: str, account_id: str) -> dict[str, Any] | None:
    lead = _lead_row(conn, lead_id=lead_id, account_id=account_id)
    if not lead:
        return None
    notes = conn.execute(
        """SELECT id, body, created_at FROM web_partner_crm_notes
           WHERE lead_id=? AND account_id=? ORDER BY created_at DESC, id DESC LIMIT ?""",
        (lead_id, account_id, MAX_NOTES_PER_LEAD),
    ).fetchall()
    events = conn.execute(
        """SELECT action, stage, revision, created_at FROM web_partner_crm_events
           WHERE lead_id=? AND account_id=? ORDER BY created_at DESC, id DESC LIMIT 100""",
        (lead_id, account_id),
    ).fetchall()
    return {
        "lead": _lead_public(lead, include_detail=True),
        "notes": [_note_public(row) for row in notes],
        "events": [_event_public(row) for row in events],
    }


def _summary(conn: Any, *, account_id: str) -> dict[str, Any]:
    rows = conn.execute(
        "SELECT stage, COUNT(*) FROM web_partner_crm_leads WHERE account_id=? GROUP BY stage",
        (account_id,),
    ).fetchall()
    counts = {str(row[0]): int(row[1]) for row in rows}
    return {"by_stage": {stage: counts.get(stage, 0) for stage in sorted(LEAD_STAGES)}, "total": sum(counts.values())}


def _require_current(row: tuple[Any, ...], *, expected_revision: int) -> dict[str, Any] | None:
    if int(row[13]) != expected_revision:
        return _revision_conflict()
    if str(row[12]) == "archived":
        return _state_conflict()
    return None


@router.get("/policy")
async def partner_crm_policy(account: dict = Depends(require_account)):
    _require_enabled()
    return envelope(
        True,
        "Partner & Lead CRM chỉ lưu metadata và ghi chú riêng tư; không gửi liên hệ hoặc thay đổi referral/payout.",
        data={
            "canonical_admin_directory_available": False,
            "canonical_admin_directory_reason": "Chưa có directory cross-account vì module không gọi Bot/Core Bridge để xác minh quyền canonical.",
            "manager_directory_available": str(account.get("role") or "user") == "admin",
            "manager_directory_boundary": "Chỉ role admin của Web session, chỉ đọc metadata đã redact; không có cross-account detail hoặc write.",
            "stages": sorted(LEAD_STAGES),
            "consent_states": sorted(CONSENT_STATES),
            **_boundary(lead_persisted=False),
        },
        status_name="read_only",
    )


@router.get("/consultations/catalog")
async def consultation_catalog(_account: dict = Depends(require_account)):
    """List a closed, account-gated consultation catalog without a write.

    This is a customer intake, not a generic CRM form.  It is not
    personalized from Bot state, does not quote a price, collect contact data,
    create a support case, or start a provider/payment/job flow.
    """

    _require_enabled()
    boundaries = _boundary(lead_persisted=False)
    return envelope(
        True,
        "Chọn loại tư vấn để chuẩn bị yêu cầu trong Web; chưa có lead hoặc liên hệ nào được tạo.",
        data={
            "catalog_version": CONSULTATION_CRM_CATALOG_VERSION,
            "groups": _consultation_catalog_public(),
            "boundaries": boundaries,
            "delivery": "web_native_partner_lead_crm_only",
            "persistence": "none",
            "automation": "none",
            "contact_collection": False,
            "outbound_contact_authorized": False,
            **boundaries,
        },
        status_name="read_only",
    )


@router.post("/consultations/preview")
async def preview_consultation(
    payload: ConsultationPreviewRequest,
    _account: dict = Depends(require_csrf),
):
    """Validate a consultation request without inserting any CRM record."""

    _require_enabled()
    _, selection = _consultation_snapshot(payload)
    boundaries = _boundary(lead_persisted=False)
    return envelope(
        True,
        "Đã kiểm tra yêu cầu. Chưa có lead được tạo; hãy đọc lại và xác nhận lưu draft nếu bạn muốn tiếp tục.",
        data={
            "catalog_version": CONSULTATION_CRM_CATALOG_VERSION,
            "selection": selection,
            "request": {
                "service_id": payload.service_id,
                "request_title": payload.request_title,
                "need_summary": payload.need_summary,
            },
            "stage": "draft",
            "record_created": False,
            "input_persisted": False,
            "intake_consent_scope": CONSULTATION_CRM_STORAGE_SCOPE,
            "outbound_contact_authorized": False,
            "boundaries": boundaries,
            **boundaries,
        },
        status_name="awaiting_confirm",
    )


@router.post("/consultations")
async def confirm_consultation(
    payload: ConsultationConfirmRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Persist one owner-scoped CRM draft after explicit storage consent.

    The confirmation does not authorize an email, Telegram, Zalo, phone,
    marketing or sales contact.  It merely documents the signed account's
    affirmative choice to store its own request as a private Web CRM draft.
    """

    _require_enabled()
    account_id = str(account["id"])
    snapshot, selection = _consultation_snapshot(payload)
    fingerprint = _fingerprint(
        {
            "action": "consultation_confirm",
            "catalog_version": CONSULTATION_CRM_CATALOG_VERSION,
            "service_id": payload.service_id,
            "request_title": payload.request_title,
            "need_summary": payload.need_summary,
            "intake_consent_scope": CONSULTATION_CRM_STORAGE_SCOPE,
        }
    )

    def operation(conn: Any) -> dict[str, Any]:
        count = conn.execute(
            "SELECT COUNT(*) FROM web_partner_crm_leads WHERE account_id=? AND stage!='archived'",
            (account_id,),
        ).fetchone()
        if int(count[0] or 0) >= MAX_ACTIVE_LEADS:
            return envelope(
                False,
                "Đã đạt giới hạn lead chưa archive. Hãy archive lead cũ trước khi tạo yêu cầu tư vấn mới.",
                data=_boundary(lead_persisted=False),
                status_name="guarded",
                error_code="WEB_PARTNER_CRM_LEAD_LIMIT",
            )
        lead_id = str(uuid.uuid4())
        now = utc_now()
        _insert_lead(conn, lead_id=lead_id, account_id=account_id, snapshot=snapshot, revision=1, now=now)
        _event(conn, lead_id=lead_id, account_id=account_id, action="consultation_lead_confirmed", stage="draft", revision=1)
        _audit(
            conn,
            request=request,
            account=account,
            action="web.partner_crm.consultation.create",
            target=lead_id,
            detail=f"service={payload.service_id};scope={CONSULTATION_CRM_STORAGE_SCOPE};stage=draft",
        )
        created = _lead_row(conn, lead_id=lead_id, account_id=account_id)
        return envelope(
            True,
            "Đã tạo lead draft riêng tư từ yêu cầu tư vấn. Không có liên hệ, notification, báo giá hoặc job nào được tạo.",
            data={
                "lead": _lead_public(created),
                "consultation": {
                    "service_id": selection["id"],
                    "catalog_version": CONSULTATION_CRM_CATALOG_VERSION,
                },
                "intake_consent_scope": CONSULTATION_CRM_STORAGE_SCOPE,
                "outbound_contact_authorized": False,
                **_boundary(lead_persisted=True),
            },
            status_name="draft",
        )

    return _idempotent(
        f"web-partner-crm:{account_id}:consultation:create",
        account_id,
        payload.idempotency_key,
        fingerprint,
        operation,
    )


@router.get("/summary")
async def partner_crm_summary(account: dict = Depends(require_account)):
    _require_enabled()
    ensure_partner_crm_schema()
    with read_transaction() as conn:
        data = _summary(conn, account_id=str(account["id"]))
    return envelope(True, "Đã tải tổng quan Partner & Lead CRM riêng tư.", data=data, status_name="read_only")


@router.get("/manager/leads")
async def manager_lead_directory(
    limit: int = 50,
    stage: str = "all",
    offset: int = 0,
    account: dict = Depends(require_admin),
):
    """Read-only, redacted pipeline directory for a signed Web manager.

    This intentionally does not use a Core Bridge or Bot lookup.  It is not a
    canonical-live admin endpoint, is not a lead detail endpoint, and cannot
    mutate another account's data.  A separately reviewed canonical boundary
    can replace it later if operational policy requires that stronger check.
    """

    _require_enabled()
    ensure_partner_crm_schema()
    bounded = max(1, min(int(limit), MAX_LIST_LIMIT))
    bounded_offset = int(offset)
    if bounded_offset < 0 or bounded_offset > MAX_LIST_OFFSET:
        raise HTTPException(status_code=422, detail="Offset directory CRM không hợp lệ")
    stage_filter = str(stage or "all").strip().lower()
    if stage_filter not in {*LEAD_STAGES, "all"}:
        raise HTTPException(status_code=422, detail="Bộ lọc pipeline stage không hợp lệ")
    # Do not join ``web_accounts`` here.  The cross-account manager directory
    # has no reason to select, filter by, or otherwise expose account identity;
    # a tautology keeps the optional stage predicate composable without
    # reintroducing an identity-bearing table alias.
    clauses = ["1=1"]
    params: list[Any] = []
    if stage_filter != "all":
        clauses.append("l.stage=?")
        params.append(stage_filter)
    with read_transaction() as conn:
        rows = conn.execute(
            f"""SELECT {MANAGER_LEAD_COLUMNS}
                FROM web_partner_crm_leads l
                WHERE {' AND '.join(clauses)}
                ORDER BY l.updated_at DESC, l.id DESC LIMIT ? OFFSET ?""",
            (*params, bounded + 1, bounded_offset),
        ).fetchall()
    return envelope(
        True,
        "Đã tải directory pipeline quản lý ở chế độ chỉ đọc, với dữ liệu lead đã redact.",
        data={
            "items": [_manager_directory_item(row) for row in rows[:bounded]],
            "has_more": len(rows) > bounded,
            "next_offset": bounded_offset + bounded if len(rows) > bounded else None,
            "cross_account_write_available": False,
            "contact_detail_available": False,
            "notes_available": False,
            **_boundary(lead_persisted=False),
        },
        status_name="read_only",
    )


@router.get("/leads")
async def list_leads(
    limit: int = 30,
    stage: str = "all",
    q: str = "",
    offset: int = 0,
    account: dict = Depends(require_account),
):
    _require_enabled()
    ensure_partner_crm_schema()
    bounded = max(1, min(int(limit), MAX_LIST_LIMIT))
    bounded_offset = int(offset)
    if bounded_offset < 0 or bounded_offset > MAX_LIST_OFFSET:
        raise HTTPException(status_code=422, detail="Offset danh sách lead CRM không hợp lệ")
    stage_filter = str(stage or "all").strip().lower()
    if stage_filter not in {*LEAD_STAGES, "all"}:
        raise HTTPException(status_code=422, detail="Bộ lọc pipeline stage không hợp lệ")
    query = _text(q, label="Từ khóa lead", minimum=0, maximum=100, allow_empty=True)
    clauses = ["account_id=?"]
    params: list[Any] = [str(account["id"])]
    if stage_filter != "all":
        clauses.append("stage=?")
        params.append(stage_filter)
    if query:
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{escaped}%"
        clauses.append("(lead_name LIKE ? ESCAPE '\\' OR organization LIKE ? ESCAPE '\\' OR opportunity_summary LIKE ? ESCAPE '\\')")
        params.extend([like, like, like])
    with read_transaction() as conn:
        rows = conn.execute(
            f"SELECT {LEAD_COLUMNS} FROM web_partner_crm_leads WHERE {' AND '.join(clauses)} "
            "ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?",
            (*params, bounded + 1, bounded_offset),
        ).fetchall()
    return envelope(
        True,
        "Đã tải danh sách lead riêng tư.",
        data={
            "items": [_lead_public(row) for row in rows[:bounded]],
            "has_more": len(rows) > bounded,
            "next_offset": bounded_offset + bounded if len(rows) > bounded else None,
        },
        status_name="read_only",
    )


@router.get("/leads/{lead_id}")
async def get_lead(lead_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    ensure_partner_crm_schema()
    resolved = _uuid(lead_id, label="Lead ID")
    with read_transaction() as conn:
        detail = _lead_detail(conn, lead_id=resolved, account_id=str(account["id"]))
    if not detail:
        return _not_found()
    return envelope(True, "Đã tải lead, ghi chú và timeline riêng tư.", data=detail, status_name="read_only")


@router.post("/leads")
async def create_lead(payload: LeadCreateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    account_id = str(account["id"])
    snapshot = _snapshot(payload, stage="draft")
    fingerprint = _fingerprint({"action": "create", "snapshot": snapshot})

    def operation(conn: Any) -> dict[str, Any]:
        count = conn.execute(
            "SELECT COUNT(*) FROM web_partner_crm_leads WHERE account_id=? AND stage!='archived'",
            (account_id,),
        ).fetchone()
        if int(count[0] or 0) >= MAX_ACTIVE_LEADS:
            return envelope(
                False,
                "Đã đạt giới hạn lead chưa archive. Hãy archive lead cũ trước.",
                data=_boundary(lead_persisted=False),
                status_name="guarded",
                error_code="WEB_PARTNER_CRM_LEAD_LIMIT",
            )
        lead_id = str(uuid.uuid4())
        now = utc_now()
        _insert_lead(conn, lead_id=lead_id, account_id=account_id, snapshot=snapshot, revision=1, now=now)
        _event(conn, lead_id=lead_id, account_id=account_id, action="lead_created", stage="draft", revision=1)
        _audit(conn, request=request, account=account, action="web.partner_crm.lead.create", target=lead_id, detail="stage=draft")
        created = _lead_row(conn, lead_id=lead_id, account_id=account_id)
        return envelope(
            True,
            "Đã lưu lead draft riêng tư. Không có liên hệ, notification, referral hoặc payout nào được tạo.",
            data={"lead": _lead_public(created), **_boundary(lead_persisted=True)},
            status_name="draft",
        )

    return _idempotent(f"web-partner-crm:{account_id}:lead:create", account_id, payload.idempotency_key, fingerprint, operation)


@router.patch("/leads/{lead_id}")
async def update_lead(lead_id: str, payload: LeadUpdateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    resolved = _uuid(lead_id, label="Lead ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint(
        {"action": "update", "lead_id": resolved, "expected_revision": payload.expected_revision, "snapshot": _snapshot(payload, stage="active")}
    )

    def operation(conn: Any) -> dict[str, Any]:
        current = _lead_row(conn, lead_id=resolved, account_id=account_id)
        if not current:
            return _not_found()
        conflict = _require_current(current, expected_revision=payload.expected_revision)
        if conflict:
            return conflict
        snapshot = _snapshot(payload, stage=str(current[12]))
        revision = int(current[13]) + 1
        now = utc_now()
        _write_lead(conn, lead_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _event(conn, lead_id=resolved, account_id=account_id, action="lead_updated", stage=snapshot["stage"], revision=revision)
        _audit(conn, request=request, account=account, action="web.partner_crm.lead.update", target=resolved, detail=f"revision={revision}")
        updated = _lead_row(conn, lead_id=resolved, account_id=account_id)
        return envelope(
            True,
            "Đã cập nhật lead riêng tư. Không có liên hệ hoặc hành động thương mại nào được gửi.",
            data={"lead": _lead_public(updated), **_boundary(lead_persisted=True)},
            status_name="draft",
        )

    return _idempotent(f"web-partner-crm:{account_id}:lead:{resolved}:update", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/leads/{lead_id}/stage")
async def set_lead_stage(lead_id: str, payload: StageRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    resolved = _uuid(lead_id, label="Lead ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint(
        {"action": "stage", "lead_id": resolved, "expected_revision": payload.expected_revision, "stage": payload.stage}
    )

    def operation(conn: Any) -> dict[str, Any]:
        current = _lead_row(conn, lead_id=resolved, account_id=account_id)
        if not current:
            return _not_found()
        if int(current[13]) != payload.expected_revision:
            return _revision_conflict()
        old_stage = str(current[12])
        if payload.stage not in STAGE_TRANSITIONS.get(old_stage, frozenset()):
            return envelope(
                False,
                "Chuyển pipeline stage không hợp lệ cho lead hiện tại.",
                data=_boundary(lead_persisted=False),
                status_name="guarded",
                error_code="WEB_PARTNER_CRM_STAGE_TRANSITION",
            )
        snapshot = _lead_snapshot(current, stage=payload.stage)
        revision = int(current[13]) + 1
        now = utc_now()
        _write_lead(
            conn,
            lead_id=resolved,
            account_id=account_id,
            snapshot=snapshot,
            revision=revision,
            now=now,
            archived_at=now if payload.stage == "archived" else None,
        )
        _event(conn, lead_id=resolved, account_id=account_id, action="stage_changed", stage=payload.stage, revision=revision)
        _audit(conn, request=request, account=account, action="web.partner_crm.lead.stage", target=resolved, detail=f"from={old_stage};to={payload.stage};revision={revision}")
        updated = _lead_row(conn, lead_id=resolved, account_id=account_id)
        return envelope(
            True,
            "Đã cập nhật pipeline stage riêng tư. Không có publish, contact hoặc payout nào được tạo.",
            data={"lead": _lead_public(updated), **_boundary(lead_persisted=True)},
            status_name="draft",
        )

    return _idempotent(f"web-partner-crm:{account_id}:lead:{resolved}:stage", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/leads/{lead_id}/consent")
async def set_lead_consent(lead_id: str, payload: ConsentRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    resolved = _uuid(lead_id, label="Lead ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint(
        {
            "action": "consent",
            "lead_id": resolved,
            "expected_revision": payload.expected_revision,
            "consent_status": payload.consent_status,
            "consent_note": payload.consent_note,
        }
    )

    def operation(conn: Any) -> dict[str, Any]:
        current = _lead_row(conn, lead_id=resolved, account_id=account_id)
        if not current:
            return _not_found()
        conflict = _require_current(current, expected_revision=payload.expected_revision)
        if conflict:
            return conflict
        snapshot = _lead_snapshot(
            current,
            consent_status=payload.consent_status,
            consent_note=payload.consent_note,
        )
        revision = int(current[13]) + 1
        now = utc_now()
        _write_lead(conn, lead_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _event(conn, lead_id=resolved, account_id=account_id, action="consent_recorded", stage=snapshot["stage"], revision=revision)
        _audit(
            conn,
            request=request,
            account=account,
            action="web.partner_crm.lead.consent",
            target=resolved,
            detail=f"status={payload.consent_status};revision={revision}",
        )
        updated = _lead_row(conn, lead_id=resolved, account_id=account_id)
        return envelope(
            True,
            "Đã ghi nhận trạng thái consent riêng tư. CRM không tự gửi liên hệ hay notification.",
            data={"lead": _lead_public(updated), **_boundary(lead_persisted=True)},
            status_name="draft",
        )

    return _idempotent(f"web-partner-crm:{account_id}:lead:{resolved}:consent", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/leads/{lead_id}/notes")
async def create_lead_note(lead_id: str, payload: NoteCreateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    resolved = _uuid(lead_id, label="Lead ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint(
        {"action": "note", "lead_id": resolved, "expected_revision": payload.expected_revision, "body": payload.body}
    )

    def operation(conn: Any) -> dict[str, Any]:
        current = _lead_row(conn, lead_id=resolved, account_id=account_id)
        if not current:
            return _not_found()
        conflict = _require_current(current, expected_revision=payload.expected_revision)
        if conflict:
            return conflict
        note_count = conn.execute(
            "SELECT COUNT(*) FROM web_partner_crm_notes WHERE lead_id=? AND account_id=?",
            (resolved, account_id),
        ).fetchone()
        if int(note_count[0] or 0) >= MAX_NOTES_PER_LEAD:
            return envelope(
                False,
                "Lead đã đạt giới hạn ghi chú riêng tư.",
                data=_boundary(lead_persisted=False),
                status_name="guarded",
                error_code="WEB_PARTNER_CRM_NOTE_LIMIT",
            )
        revision = int(current[13]) + 1
        now = utc_now()
        snapshot = _lead_snapshot(current)
        _write_lead(conn, lead_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        note_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO web_partner_crm_notes (id, lead_id, account_id, body, created_at) VALUES (?, ?, ?, ?, ?)",
            (note_id, resolved, account_id, payload.body, now),
        )
        _event(conn, lead_id=resolved, account_id=account_id, action="note_added", stage=snapshot["stage"], revision=revision)
        _audit(conn, request=request, account=account, action="web.partner_crm.lead.note", target=resolved, detail=f"revision={revision}")
        updated = _lead_row(conn, lead_id=resolved, account_id=account_id)
        return envelope(
            True,
            "Đã lưu ghi chú CRM riêng tư. Không có notification hoặc liên hệ nào được gửi.",
            data={
                "lead": _lead_public(updated),
                "note": {"id": note_id, "created_at": now},
                **_boundary(lead_persisted=True),
            },
            status_name="draft",
        )

    return _idempotent(f"web-partner-crm:{account_id}:lead:{resolved}:note", account_id, payload.idempotency_key, fingerprint, operation)
