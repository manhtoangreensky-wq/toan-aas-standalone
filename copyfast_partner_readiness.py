"""Private Web-native Partner Readiness profile.

This module is deliberately a signed-account metadata workspace, not an
affiliate, referral, CRM, directory, matching, contact, payment or execution
surface.  It never imports a Bot/bridge/provider adapter.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import re
import uuid
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, field_validator

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import ensure_copyfast_schema, partner_readiness_enabled, read_transaction, transaction, utc_now


router = APIRouter(prefix="/api/v1/partner-readiness", tags=["Partner Readiness"])

STATES = frozenset({"draft", "review", "submitted", "archived"})
CAPABILITIES = frozenset({"brief_review", "content_system", "creative_direction", "workflow_design", "quality_review", "handoff_documentation"})
PREFERRED_BRIEFS = frozenset({"product_content", "campaign", "brand_system", "operations", "education"})
AVAILABILITY = frozenset({"open", "limited", "unavailable"})
RATE_DISPLAY = frozenset({"on_request", "range_discussion", "not_shown"})
VISIBILITY = frozenset({"private", "handoff_ready"})
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
CONTROL_PATTERN = re.compile(r"[\x00-\x1f\x7f]")
MARKUP_OR_URL = re.compile(r"<[^>]*>|(?:\bwww\.|[A-Za-z][A-Za-z0-9+.-]{1,15}://|(?:https?|mailto|javascript|data|file|ftp|tel|sms):)", re.IGNORECASE)
HANDLE_OR_CONTACT = re.compile(r"(?:\b[\w.+-]+@[\w-]+\.[\w.-]+\b|(?<!\w)@[A-Za-z][A-Za-z0-9_]{3,31}\b|\b(?:telegram|zalo|phone|email|liên\s*hệ|lien\s*he)\b|(?<!\d)0\d{8,10}(?!\d))", re.IGNORECASE)
SECRET = re.compile(r"\b(?:api[ _-]?(?:key|token)|access[ _-]?token|secret|password|passphrase|authorization|otp|cvv|cvc|private[ _-]?key)\b", re.IGNORECASE)
PAYMENT = re.compile(r"\b(?:payos|txid|transaction|bill|biên\s*lai|chứng\s*từ|số\s*tài\s*khoản|stk|card|thẻ|payment|payout|commission|recipient|người\s*nhận)\b|(?:\d[\d., ]{2,}\s*(?:đ|vnd|usd|\$))", re.IGNORECASE)
REFERRAL = re.compile(r"\b(?:referral|affiliate|ref\s*code|mã\s*giới\s*thiệu|mã\s*ref)\b", re.IGNORECASE)
CREDENTIAL_ASSIGNMENT = re.compile(
    r"\b(?:[A-Za-z][A-Za-z0-9]*(?:[_-](?:token|secret|key|credential|password|jwt))|"
    r"token|bearer|credential|secret|key|jwt|api[ _-]?(?:key|token)|access[ _-]?token)"
    r"\s*[:=]\s*\S+",
    re.IGNORECASE,
)
ADMIN_IDENTITY = re.compile(
    r"\b(?:admin(?:istrator)?|operator|staff|manager)[\s_-]+"
    r"(?:identity|id|account|user)\b\s*[:=]?\s*\S*",
    re.IGNORECASE,
)
RETENTION = timedelta(hours=24)
MAX_RECEIPTS = 1024


def _require_enabled() -> None:
    if not partner_readiness_enabled():
        raise HTTPException(status_code=503, detail="Partner Readiness đang tạm dừng để bảo trì.")


def _private(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Vary"] = "Cookie"


def _boundary(*, profile_persisted: bool, interest_submitted: bool = False) -> dict[str, Any]:
    return {
        "execution": "web_native_partner_readiness_profile_only",
        "profile_persisted": bool(profile_persisted),
        "interest_submitted": bool(interest_submitted),
        "bot_called": False, "telegram_called": False, "bridge_called": False,
        "provider_called": False, "job_created": False, "wallet_mutated": False,
        "xu_mutated": False, "payment_started": False, "payos_called": False,
        "referral_created": False, "attribution_created": False, "commission_created": False,
        "payout_created": False, "public_listing_created": False, "matching_started": False,
        "contact_released": False, "crm_record_created": False, "notification_sent": False,
        "delivery_created": False,
    }


def _text(value: Any, *, label: str, minimum: int, maximum: int, allow_empty: bool = False) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if CONTROL_PATTERN.search(text) or len(text) > maximum or (not allow_empty and len(text) < minimum):
        raise ValueError(f"{label} cần từ {minimum} đến {maximum} ký tự hợp lệ")
    if text and (MARKUP_OR_URL.search(text) or HANDLE_OR_CONTACT.search(text) or SECRET.search(text) or PAYMENT.search(text) or REFERRAL.search(text) or CREDENTIAL_ASSIGNMENT.search(text) or ADMIN_IDENTITY.search(text)):
        raise ValueError(f"{label} không nhận markup, URL, liên hệ, secret, thanh toán hoặc referral")
    return text


def _closed(value: Any, *, label: str, allowed: frozenset[str], limit: int) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} phải là danh sách")
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        code = _text(item, label=label, minimum=1, maximum=48).lower()
        if code not in allowed:
            raise ValueError(f"{label} không hợp lệ")
        if code not in seen:
            seen.add(code)
            result.append(code)
    if len(result) > limit:
        raise ValueError(f"{label} tối đa {limit} mục")
    return result


def _code(value: Any, *, label: str, allowed: frozenset[str]) -> str:
    code = _text(value, label=label, minimum=1, maximum=48).lower()
    if code not in allowed:
        raise ValueError(f"{label} không hợp lệ")
    return code


def _key(value: Any) -> str:
    key = str(value or "").strip()
    if not IDEMPOTENCY_PATTERN.fullmatch(key):
        raise ValueError("Idempotency key không hợp lệ")
    return key


class ProfilePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    service_focus: StrictStr
    capabilities: list[StrictStr]
    availability: StrictStr
    rate_display_preference: StrictStr
    preferred_briefs: list[StrictStr]
    portfolio_summary: StrictStr = ""
    collaboration_note: StrictStr = ""
    visibility_draft: StrictStr = "private"
    expected_revision: StrictInt = Field(ge=0)
    idempotency_key: StrictStr

    @field_validator("service_focus")
    @classmethod
    def validate_focus(cls, value: str) -> str:
        return _text(value, label="Trọng tâm dịch vụ", minimum=4, maximum=240)

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, value: list[str]) -> list[str]:
        return _closed(value, label="Năng lực", allowed=CAPABILITIES, limit=8)

    @field_validator("availability")
    @classmethod
    def validate_availability(cls, value: str) -> str:
        return _code(value, label="Khả dụng", allowed=AVAILABILITY)

    @field_validator("rate_display_preference")
    @classmethod
    def validate_rate(cls, value: str) -> str:
        return _code(value, label="Cách hiển thị mức phí", allowed=RATE_DISPLAY)

    @field_validator("preferred_briefs")
    @classmethod
    def validate_briefs(cls, value: list[str]) -> list[str]:
        return _closed(value, label="Loại brief ưu tiên", allowed=PREFERRED_BRIEFS, limit=8)

    @field_validator("portfolio_summary")
    @classmethod
    def validate_portfolio(cls, value: str) -> str:
        return _text(value, label="Tóm tắt portfolio", minimum=0, maximum=1200, allow_empty=True)

    @field_validator("collaboration_note")
    @classmethod
    def validate_note(cls, value: str) -> str:
        return _text(value, label="Ghi chú hợp tác", minimum=0, maximum=1200, allow_empty=True)

    @field_validator("visibility_draft")
    @classmethod
    def validate_visibility(cls, value: str) -> str:
        return _code(value, label="Mức sẵn sàng", allowed=VISIBILITY)

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _key(value)


class RevisionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_revision: StrictInt = Field(ge=1)
    idempotency_key: StrictStr

    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _key(value)


class InterestPayload(RevisionPayload):
    confirm_interest: StrictBool

    def model_post_init(self, __context: Any) -> None:
        if self.confirm_interest is not True:
            raise ValueError("Bạn cần xác nhận gửi interest receipt")


def _fingerprint(payload: BaseModel) -> str:
    data = payload.model_dump(exclude={"idempotency_key"})
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _profile_row(conn, account_id: str):
    return conn.execute(
        """SELECT id, service_focus, capabilities_json, availability, rate_display_preference,
                  preferred_briefs_json, portfolio_summary, collaboration_note, visibility_draft,
                  state, revision, created_at, updated_at, archived_at
           FROM web_partner_readiness_profiles WHERE account_id=?""", (account_id,)
    ).fetchone()


def _decode_list(value: Any) -> list[str]:
    try:
        parsed = json.loads(str(value or "[]"))
    except (ValueError, TypeError, json.JSONDecodeError):
        return []
    return [item for item in parsed if isinstance(item, str)] if isinstance(parsed, list) else []


def _profile(row) -> dict[str, Any]:
    return {
        "id": str(row[0]), "service_focus": str(row[1]), "capabilities": _decode_list(row[2]),
        "availability": str(row[3]), "rate_display_preference": str(row[4]),
        "preferred_briefs": _decode_list(row[5]), "portfolio_summary": str(row[6]),
        "collaboration_note": str(row[7]), "visibility_draft": str(row[8]), "state": str(row[9]),
        "revision": int(row[10]), "created_at": str(row[11]), "updated_at": str(row[12]),
        "archived_at": str(row[13]) if row[13] else None,
    }


def _summary(profile: dict[str, Any]) -> dict[str, Any]:
    return {"revision": int(profile["revision"]), "state": str(profile["state"])}


def _snapshot(profile: dict[str, Any]) -> dict[str, Any]:
    return {key: profile[key] for key in ("service_focus", "capabilities", "availability", "rate_display_preference", "preferred_briefs", "portfolio_summary", "collaboration_note", "visibility_draft", "state", "revision")}


def _record_version_event(conn, *, profile: dict[str, Any], account_id: str, action: str) -> None:
    now = utc_now()
    conn.execute(
        "INSERT INTO web_partner_readiness_versions (id, profile_id, account_id, revision, snapshot_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), profile["id"], account_id, profile["revision"], json.dumps(_snapshot(profile), ensure_ascii=False, separators=(",", ":")), now),
    )
    conn.execute(
        "INSERT INTO web_partner_readiness_events (id, profile_id, account_id, action, state, revision, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), profile["id"], account_id, action, profile["state"], profile["revision"], now),
    )


def _receipt(response: dict[str, Any]) -> dict[str, Any]:
    source = response.get("data") if isinstance(response.get("data"), dict) else {}
    data = _boundary(profile_persisted=bool(source.get("profile_persisted")), interest_submitted=bool(source.get("interest_submitted")))
    if isinstance(source.get("profile"), dict):
        data["profile"] = {key: source["profile"][key] for key in ("revision", "state") if key in source["profile"]}
    if isinstance(source.get("interest_receipt"), dict):
        data["interest_receipt"] = dict(source["interest_receipt"])
    return envelope(True, str(response.get("message") or "Đã lưu readiness profile."), data=data, status_name=str(response.get("status") or "draft"))


def _idempotent(scope: str, account_id: str, key: str, fingerprint: str, operation: Callable[[Any], dict[str, Any]]) -> dict[str, Any]:
    ensure_copyfast_schema()
    cutoff = (datetime.now(timezone.utc) - RETENTION).isoformat(timespec="seconds")
    with transaction() as conn:
        conn.execute("DELETE FROM web_idempotency WHERE scope LIKE ? AND created_at < ?", ("web-partner-readiness:%", cutoff))
        existing = conn.execute("SELECT response_json, request_fingerprint FROM web_idempotency WHERE scope=? AND key=?", (scope, key)).fetchone()
        if existing:
            if not hmac.compare_digest(str(existing[1] or ""), fingerprint):
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho yêu cầu khác")
            try:
                saved = json.loads(str(existing[0]))
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Interest receipt không hợp lệ") from exc
            if not isinstance(saved, dict):
                raise HTTPException(status_code=409, detail="Interest receipt không hợp lệ")
            return saved
        count = conn.execute("SELECT COUNT(*) FROM web_idempotency WHERE scope LIKE ?", (f"web-partner-readiness:{account_id}:%",)).fetchone()
        if int(count[0] or 0) >= MAX_RECEIPTS:
            raise HTTPException(status_code=409, detail="Kho receipt tạm thời đang đầy")
        response = operation(conn)
        receipt = _receipt(response)
        conn.execute("INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at) VALUES (?, ?, ?, ?, ?)", (scope, key, json.dumps(receipt, ensure_ascii=False, separators=(",", ":")), fingerprint, utc_now()))
        return receipt


def _audit(conn, account: dict[str, Any], request: Request, *, action: str, profile: dict[str, Any]) -> None:
    _record_audit(conn, account_id=str(account["id"]), canonical_user_id=account.get("canonical_user_id"), action=f"web.partner_readiness.{action}", request_id=_request_id(request), target="partner_readiness_profile", detail=f"state={profile['state']};revision={profile['revision']}")


def _conflict(message: str) -> None:
    raise HTTPException(status_code=409, detail=message)


@router.get("/policy")
def get_policy(response: Response, account: dict[str, Any] = Depends(require_account)) -> dict[str, Any]:
    _require_enabled(); _private(response)
    data = _boundary(profile_persisted=False)
    data.update({"states": ["draft", "review", "submitted", "archived"], "capabilities": sorted(CAPABILITIES), "availability": sorted(AVAILABILITY), "rate_display_preferences": sorted(RATE_DISPLAY), "preferred_briefs": sorted(PREFERRED_BRIEFS), "visibility_drafts": sorted(VISIBILITY), "interest_receipt_only": True})
    return envelope(True, "Đã tải chính sách Partner Readiness riêng tư.", data=data, status_name="completed")


@router.get("/profile")
def get_profile(response: Response, account: dict[str, Any] = Depends(require_account)) -> dict[str, Any]:
    _require_enabled(); _private(response); ensure_copyfast_schema()
    with read_transaction() as conn:
        row = _profile_row(conn, str(account["id"]))
    data = _boundary(profile_persisted=False); data["profile"] = _profile(row) if row else None
    return envelope(True, "Đã tải Partner Readiness profile riêng tư.", data=data, status_name=data["profile"]["state"] if data["profile"] else "draft")


@router.get("/profile/history")
def get_history(response: Response, account: dict[str, Any] = Depends(require_account)) -> dict[str, Any]:
    _require_enabled(); _private(response); ensure_copyfast_schema()
    with read_transaction() as conn:
        rows = conn.execute("SELECT revision, snapshot_json, created_at FROM web_partner_readiness_versions WHERE account_id=? ORDER BY revision DESC", (str(account["id"]),)).fetchall()
        events = conn.execute("SELECT action, state, revision, created_at FROM web_partner_readiness_events WHERE account_id=? ORDER BY created_at DESC, id DESC LIMIT 100", (str(account["id"]),)).fetchall()
    versions = []
    for revision, raw, created_at in rows:
        try: snapshot = json.loads(str(raw))
        except (ValueError, TypeError, json.JSONDecodeError): snapshot = {}
        versions.append({"revision": int(revision), "snapshot": snapshot if isinstance(snapshot, dict) else {}, "created_at": str(created_at)})
    data = _boundary(profile_persisted=False); data.update({"versions": versions, "events": [{"action": str(item[0]), "state": str(item[1]), "revision": int(item[2]), "created_at": str(item[3])} for item in events]})
    return envelope(True, "Đã tải lịch sử readiness profile riêng tư.", data=data, status_name="completed")


@router.patch("/profile")
def patch_profile(payload: ProfilePayload, request: Request, response: Response, account: dict[str, Any] = Depends(require_account), _: dict[str, Any] = Depends(require_csrf)) -> dict[str, Any]:
    _require_enabled(); _private(response); account_id = str(account["id"])
    def operation(conn):
        row = _profile_row(conn, account_id)
        if row is None:
            if payload.expected_revision != 0: _conflict("Profile chưa tồn tại hoặc revision không còn phù hợp")
            now, profile_id = utc_now(), str(uuid.uuid4())
            conn.execute("INSERT INTO web_partner_readiness_profiles (account_id, id, service_focus, capabilities_json, availability, rate_display_preference, preferred_briefs_json, portfolio_summary, collaboration_note, visibility_draft, state, revision, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', 1, ?, ?)", (account_id, profile_id, payload.service_focus, json.dumps(payload.capabilities), payload.availability, payload.rate_display_preference, json.dumps(payload.preferred_briefs), payload.portfolio_summary, payload.collaboration_note, payload.visibility_draft, now, now))
            profile = _profile(_profile_row(conn, account_id)); action = "create"
        else:
            profile = _profile(row)
            if profile["revision"] != payload.expected_revision: _conflict("Profile đã được thay đổi. Hãy tải lại trước khi tiếp tục.")
            if profile["state"] not in {"draft", "review"}:
                _conflict("Profile chỉ có thể sửa khi đang draft hoặc review")
            state, revision, now = ("draft" if profile["state"] == "review" else profile["state"]), profile["revision"] + 1, utc_now()
            conn.execute("UPDATE web_partner_readiness_profiles SET service_focus=?, capabilities_json=?, availability=?, rate_display_preference=?, preferred_briefs_json=?, portfolio_summary=?, collaboration_note=?, visibility_draft=?, state=?, revision=?, updated_at=? WHERE account_id=? AND revision=?", (payload.service_focus, json.dumps(payload.capabilities), payload.availability, payload.rate_display_preference, json.dumps(payload.preferred_briefs), payload.portfolio_summary, payload.collaboration_note, payload.visibility_draft, state, revision, now, account_id, payload.expected_revision))
            profile = _profile(_profile_row(conn, account_id)); action = "update"
        _record_version_event(conn, profile=profile, account_id=account_id, action=action); _audit(conn, account, request, action=action, profile=profile)
        data = _boundary(profile_persisted=True); data["profile"] = _summary(profile)
        return envelope(True, "Đã lưu Partner Readiness profile riêng tư.", data=data, status_name=profile["state"])
    return _idempotent(f"web-partner-readiness:{account_id}:profile:patch", account_id, payload.idempotency_key, _fingerprint(payload), operation)


def _transition(*, endpoint: str, expected: str | frozenset[str], target: str, action: str, interest: bool = False):
    def handler(payload: RevisionPayload | InterestPayload, request: Request, response: Response, account: dict[str, Any] = Depends(require_account), _: dict[str, Any] = Depends(require_csrf)) -> dict[str, Any]:
        _require_enabled(); _private(response); account_id = str(account["id"])
        def operation(conn):
            row = _profile_row(conn, account_id)
            if row is None: _conflict("Không tìm thấy readiness profile thuộc Web account hiện tại")
            profile = _profile(row)
            if profile["revision"] != payload.expected_revision: _conflict("Profile đã được thay đổi. Hãy tải lại trước khi tiếp tục.")
            allowed = expected if isinstance(expected, frozenset) else frozenset({expected})
            if profile["state"] not in allowed: _conflict("Trạng thái readiness profile không cho phép thao tác này")
            revision, now = profile["revision"] + 1, utc_now()
            archived_at = now if target == "archived" else None
            conn.execute("UPDATE web_partner_readiness_profiles SET state=?, revision=?, updated_at=?, archived_at=? WHERE account_id=? AND revision=?", (target, revision, now, archived_at, account_id, payload.expected_revision))
            profile = _profile(_profile_row(conn, account_id))
            receipt = None
            if interest:
                conn.execute("INSERT INTO web_partner_readiness_interest_submissions (id, profile_id, account_id, profile_revision, created_at) VALUES (?, ?, ?, ?, ?)", (str(uuid.uuid4()), profile["id"], account_id, profile["revision"], now))
                receipt = {"revision": profile["revision"], "kind": "interest_receipt_only"}
            _record_version_event(conn, profile=profile, account_id=account_id, action=action); _audit(conn, account, request, action=action, profile=profile)
            data = _boundary(profile_persisted=True, interest_submitted=interest); data["profile"] = _summary(profile)
            if receipt: data["interest_receipt"] = receipt
            return envelope(True, "Đã lưu trạng thái Partner Readiness riêng tư.", data=data, status_name=profile["state"])
        return _idempotent(f"web-partner-readiness:{account_id}:profile:{endpoint}", account_id, payload.idempotency_key, _fingerprint(payload), operation)
    return handler


@router.post("/profile/request-review")
def request_review(payload: RevisionPayload, request: Request, response: Response, account: dict[str, Any] = Depends(require_account), csrf: dict[str, Any] = Depends(require_csrf)) -> dict[str, Any]:
    return _transition(endpoint="request-review", expected="draft", target="review", action="request_review")(payload, request, response, account, csrf)


@router.post("/profile/interest")
def submit_interest(payload: InterestPayload, request: Request, response: Response, account: dict[str, Any] = Depends(require_account), csrf: dict[str, Any] = Depends(require_csrf)) -> dict[str, Any]:
    """Create one explicit local interest receipt; it is not a contact action."""

    return _transition(endpoint="interest", expected="review", target="submitted", action="interest_submitted", interest=True)(payload, request, response, account, csrf)


@router.post("/profile/archive")
def archive_profile(payload: RevisionPayload, request: Request, response: Response, account: dict[str, Any] = Depends(require_account), csrf: dict[str, Any] = Depends(require_csrf)) -> dict[str, Any]:
    return _transition(endpoint="archive", expected=frozenset({"draft", "review", "submitted"}), target="archived", action="archive")(payload, request, response, account, csrf)


@router.post("/profile/restore")
def restore_profile(payload: RevisionPayload, request: Request, response: Response, account: dict[str, Any] = Depends(require_account), csrf: dict[str, Any] = Depends(require_csrf)) -> dict[str, Any]:
    return _transition(endpoint="restore", expected="archived", target="draft", action="restore")(payload, request, response, account, csrf)
