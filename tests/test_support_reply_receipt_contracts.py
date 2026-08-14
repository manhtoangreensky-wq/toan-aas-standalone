"""RED contracts for private, replay-safe Web Support Desk reply receipts.

These contracts intentionally describe the desired post-reply boundary before
the endpoint and browser implementations change.  A successful write may be
replayed through the existing idempotency record, but its reply must expose
only a small receipt; the browser must rehydrate the owner-scoped case rather
than using a returned message or case projection.
"""

from __future__ import annotations

from datetime import datetime
import importlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient


ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "static" / "portal" / "integration.js"
PORTAL = ROOT / "static" / "portal" / "portal.js"

RECEIPT_KEYS = {
    "case_id",
    "revision",
    "state",
    "visibility",
    "action",
    "created_at",
    "delivery",
}

SUCCESS_ENVELOPE_KEYS = {"ok", "status", "message", "data", "error_code"}
PERMITTED_RECEIPT_SCALAR_KEYS = {
    "case_id",
    "revision",
    "state",
    "visibility",
    "action",
    "created_at",
    "delivery",
}
PRIVATE_ENVELOPE_KEYS = {
    "case",
    "cases",
    "reply",
    "replies",
    "body",
    "bodies",
    "subject",
    "subjects",
    "detail",
    "details",
    "excerpt",
    "excerpts",
    "customer",
    "customers",
    "email",
    "emails",
    "actor",
    "actors",
    "staff",
    "staffs",
    "operator",
    "operators",
    "assignee",
    "assignees",
    "idempotency_key",
    "idempotency_keys",
    "idempotency",
    "request_id",
    "request_ids",
    "request",
    "requests",
    "audit",
    "audits",
    "asset",
    "assets",
    "attachment",
    "attachments",
    "provider",
    "providers",
    "provider_name",
    "provider_names",
    "job",
    "jobs",
    "payment",
    "payments",
    "payment_id",
    "payment_ids",
    "telegram",
    "telegrams",
    "telegram_chat_id",
    "telegram_chat_ids",
    "telegram_user_id",
    "telegram_user_ids",
    "url",
    "urls",
    "server_url",
    "server_urls",
    "server",
    "href",
    "link",
    "links",
}

SERVER_URL_SENTINEL_BASE = "https://receipt-server-url-sentinel.example.test"

_MODULES = (
    "app",
    "copyfast_db",
    "copyfast_auth",
    "copyfast_bridge",
    "copyfast_registry",
    "copyfast_api",
    "copyfast_pages",
    "copyfast_projects",
    "copyfast_assets",
    "copyfast_project_packages",
    "copyfast_document_operations",
    "copyfast_image_runtime",
    "copyfast_image_operations",
    "copyfast_memory",
    "copyfast_support",
)


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "support-reply-receipt-contracts.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-support-reply-receipt-secret")
    monkeypatch.setenv("WEBAPP_SUPPORT_DESK_ENABLED", "true")
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in _MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app, base_url=SERVER_URL_SENTINEL_BASE)


def register_and_login(client: TestClient, email: str, display_name: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "correct-horse-battery-staple",
            "display_name": display_name,
        },
    )
    assert registered.status_code == 200
    assert registered.json()["ok"] is True
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    return str(login.json()["data"]["csrf_token"])


def create_case(
    client: TestClient,
    csrf: str,
    *,
    subject: str = "Receipt riêng tư cho phản hồi Support",
    detail: str = "Case này chỉ được dùng để kiểm tra receipt Web-native an toàn.",
) -> dict:
    response = client.post(
        "/api/v1/support/cases",
        headers={"X-CSRF-Token": csrf},
        json={
            "category": "image_error",
            "priority": "normal",
            "subject": subject,
            "detail": detail,
            "idempotency_key": "support-receipt-case-create-0001",
        },
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    return response.json()["data"]["case"]


def set_role(database: Path, email: str, role: str) -> None:
    with sqlite3.connect(database) as conn:
        conn.execute("UPDATE web_accounts SET role_cache=? WHERE email=?", (role, email))
        conn.commit()


def message_count(database: Path, case_id: str) -> int:
    with sqlite3.connect(database) as conn:
        row = conn.execute("SELECT COUNT(*) FROM web_support_messages WHERE case_id=?", (case_id,)).fetchone()
    assert row is not None
    return int(row[0])


def case_revision(database: Path, case_id: str) -> int:
    with sqlite3.connect(database) as conn:
        row = conn.execute("SELECT revision FROM web_support_cases WHERE id=?", (case_id,)).fetchone()
    assert row is not None
    return int(row[0])


def assert_case_unchanged(database: Path, case_id: str, *, count: int, revision: int) -> None:
    assert message_count(database, case_id) == count
    assert case_revision(database, case_id) == revision


def assert_reply_receipt(
    payload: dict,
    *,
    case_id: str,
    revision: int,
    action: str,
    state: str,
    visibility: str,
    private_values: tuple[str, ...],
) -> dict:
    """The only successful durable reply projection allowed to the browser."""
    assert payload["ok"] is True
    assert payload["status"] == "completed"
    assert payload["error_code"] is None
    assert set(payload) == SUCCESS_ENVELOPE_KEYS
    assert not (set(payload) & PRIVATE_ENVELOPE_KEYS)
    # The top-level public message is allowed to describe the safe Web-only
    # outcome, but it must never echo submitted content or case-private data.
    top_level = {key: value for key, value in payload.items() if key != "data"}
    rendered_top_level = json.dumps(top_level, ensure_ascii=False)
    for private_value in private_values:
        assert private_value not in rendered_top_level
    assert set(payload["data"]) == {"receipt"}
    rendered_envelope = json.dumps(payload, ensure_ascii=False)
    for private_value in private_values:
        assert private_value not in rendered_envelope
    for forbidden in PRIVATE_ENVELOPE_KEYS:
        assert f'"{forbidden}"' not in rendered_envelope
    receipt = payload["data"]["receipt"]
    assert isinstance(receipt, dict)
    assert set(receipt) == RECEIPT_KEYS == PERMITTED_RECEIPT_SCALAR_KEYS
    assert receipt["case_id"] == case_id
    assert receipt["revision"] == revision
    assert receipt["action"] == action
    assert receipt["visibility"] == visibility
    assert receipt["delivery"] == "web_view_only"
    assert receipt["state"] == state
    assert isinstance(receipt["created_at"], str) and receipt["created_at"].endswith("+00:00")
    assert datetime.fromisoformat(receipt["created_at"]).tzinfo is not None
    for forbidden in PRIVATE_ENVELOPE_KEYS:
        assert forbidden not in receipt
    return receipt


def test_customer_reply_receipt_is_content_free_replayable_and_collision_safe(tmp_path, monkeypatch) -> None:
    database = tmp_path / "support-reply-receipt-contracts.db"
    with make_client(tmp_path, monkeypatch) as client:
        customer_email = "receipt-customer@example.com"
        customer_marker = "CUSTOMER-SENTINEL-CUSTOMER-RECEIPT"
        subject_marker = "CASE-SUBJECT-PRIVATE-CUSTOMER-RECEIPT"
        detail_marker = "CASE-DETAIL-PRIVATE-CUSTOMER-RECEIPT"
        asset_marker = "ASSET-SENTINEL-CUSTOMER-RECEIPT"
        provider_marker = "PROVIDER-SENTINEL-CUSTOMER-RECEIPT"
        payment_marker = "PAYMENT-SENTINEL-CUSTOMER-RECEIPT"
        telegram_marker = "TELEGRAM-SENTINEL-CUSTOMER-RECEIPT"
        csrf = register_and_login(client, customer_email, customer_marker)
        case = create_case(
            client,
            csrf,
            subject=f"{subject_marker} {provider_marker}",
            detail=f"{detail_marker} {asset_marker} {payment_marker}",
        )
        before = message_count(database, case["id"])
        before_revision = case_revision(database, case["id"])
        request_id_sentinel = "request-sentinel-customer-reply-0001"
        payload = {
            "body": f"Tôi đã thử lại trên Web và cần Support Desk xem thêm lịch sử case. {telegram_marker}",
            "expected_revision": 1,
            "idempotency_key": "idempotency-sentinel-customer-reply-0001",
        }
        reply_headers = {"X-CSRF-Token": csrf, "X-Request-ID": request_id_sentinel}

        first_response = client.post(
            f"/api/v1/support/cases/{case['id']}/reply",
            headers=reply_headers,
            json=payload,
        )
        assert first_response.status_code == 200
        first = first_response.json()
        after_first = message_count(database, case["id"])
        assert after_first == before + 1
        assert case_revision(database, case["id"]) == before_revision + 1

        replay_response = client.post(
            f"/api/v1/support/cases/{case['id']}/reply",
            headers=reply_headers,
            json=payload,
        )
        assert replay_response.status_code == 200
        assert replay_response.json() == first
        assert_case_unchanged(database, case["id"], count=after_first, revision=before_revision + 1)

        collision_response = client.post(
            f"/api/v1/support/cases/{case['id']}/reply",
            headers=reply_headers,
            json={**payload, "body": "Một phản hồi khác không được ghi cùng idempotency key."},
        )
        assert collision_response.status_code == 409
        assert_case_unchanged(database, case["id"], count=after_first, revision=before_revision + 1)

        assert_reply_receipt(
            first,
            case_id=case["id"],
            revision=2,
            action="customer_reply",
            state="new",
            visibility="public",
            private_values=(
                subject_marker,
                detail_marker,
                payload["body"],
                customer_email,
                customer_marker,
                asset_marker,
                provider_marker,
                payment_marker,
                telegram_marker,
                payload["idempotency_key"],
                request_id_sentinel,
                str(first_response.request.url),
                SERVER_URL_SENTINEL_BASE,
            ),
        )


@pytest.mark.parametrize(
    ("visibility", "next_state"),
    (("public", "waiting_user"), ("internal", "new")),
)
def test_operator_reply_receipt_is_content_free_replayable_and_collision_safe(
    tmp_path,
    monkeypatch,
    visibility: str,
    next_state: str,
) -> None:
    database = tmp_path / "support-reply-receipt-contracts.db"
    customer_email = f"receipt-customer-{visibility}@example.com"
    operator_email = f"receipt-operator-{visibility}@example.com"
    customer_marker = f"CUSTOMER-SENTINEL-OPERATOR-{visibility.upper()}"
    staff_marker = f"STAFF-SENTINEL-OPERATOR-{visibility.upper()}"
    subject_marker = f"CASE-SUBJECT-PRIVATE-OPERATOR-{visibility.upper()}"
    detail_marker = f"CASE-DETAIL-PRIVATE-OPERATOR-{visibility.upper()}"
    asset_marker = f"ASSET-SENTINEL-OPERATOR-{visibility.upper()}"
    provider_marker = f"PROVIDER-SENTINEL-OPERATOR-{visibility.upper()}"
    payment_marker = f"PAYMENT-SENTINEL-OPERATOR-{visibility.upper()}"
    telegram_marker = f"TELEGRAM-SENTINEL-OPERATOR-{visibility.upper()}"
    with make_client(tmp_path, monkeypatch) as customer:
        customer_csrf = register_and_login(customer, customer_email, customer_marker)
        case = create_case(
            customer,
            customer_csrf,
            subject=f"{subject_marker} {provider_marker}",
            detail=f"{detail_marker} {asset_marker} {payment_marker}",
        )

    with make_client(tmp_path, monkeypatch) as operator:
        operator_csrf = register_and_login(operator, operator_email, staff_marker)
        set_role(database, operator_email, "support_operator")
        before = message_count(database, case["id"])
        before_revision = case_revision(database, case["id"])
        request_id_sentinel = f"request-sentinel-operator-{visibility}-0001"
        payload = {
            "body": f"Phản hồi {visibility} chỉ được giao trong Web Support Desk. {telegram_marker}",
            "visibility": visibility,
            "next_state": next_state,
            "expected_revision": 1,
            "idempotency_key": f"idempotency-sentinel-operator-{visibility}-0001",
            "confirm": True,
        }
        reply_headers = {"X-CSRF-Token": operator_csrf, "X-Request-ID": request_id_sentinel}

        first_response = operator.post(
            f"/api/v1/support/admin/cases/{case['id']}/reply",
            headers=reply_headers,
            json=payload,
        )
        assert first_response.status_code == 200
        first = first_response.json()
        after_first = message_count(database, case["id"])
        assert after_first == before + 1
        assert case_revision(database, case["id"]) == before_revision + 1

        replay_response = operator.post(
            f"/api/v1/support/admin/cases/{case['id']}/reply",
            headers=reply_headers,
            json=payload,
        )
        assert replay_response.status_code == 200
        assert replay_response.json() == first
        assert_case_unchanged(database, case["id"], count=after_first, revision=before_revision + 1)

        collision_response = operator.post(
            f"/api/v1/support/admin/cases/{case['id']}/reply",
            headers=reply_headers,
            json={**payload, "body": f"Một ghi chú {visibility} khác cùng key."},
        )
        assert collision_response.status_code == 409
        assert_case_unchanged(database, case["id"], count=after_first, revision=before_revision + 1)

        assert_reply_receipt(
            first,
            case_id=case["id"],
            revision=2,
            action="operator_reply",
            state=next_state,
            visibility=visibility,
            private_values=(
                subject_marker,
                detail_marker,
                payload["body"],
                customer_email,
                operator_email,
                customer_marker,
                staff_marker,
                asset_marker,
                provider_marker,
                payment_marker,
                telegram_marker,
                payload["idempotency_key"],
                request_id_sentinel,
                str(first_response.request.url),
                SERVER_URL_SENTINEL_BASE,
            ),
        )


def test_reply_receipt_contract_preserves_csrf_confirmation_and_stale_revision_guards(tmp_path, monkeypatch) -> None:
    database = tmp_path / "support-reply-receipt-contracts.db"
    with make_client(tmp_path, monkeypatch) as customer:
        customer_csrf = register_and_login(customer, "receipt-guard-customer@example.com", "Khách guard receipt")
        case = create_case(customer, customer_csrf)
        before_count = message_count(database, case["id"])
        before_revision = case_revision(database, case["id"])
        customer_admin = customer.post(
            f"/api/v1/support/admin/cases/{case['id']}/reply",
            headers={"X-CSRF-Token": customer_csrf},
            json={"body": "Khách không thể gọi admin reply.", "visibility": "public", "expected_revision": 1, "idempotency_key": "support-receipt-customer-admin-forbidden-0001", "confirm": True},
        )
        assert customer_admin.status_code == 403
        assert_case_unchanged(database, case["id"], count=before_count, revision=before_revision)
        denied = customer.post(
            f"/api/v1/support/cases/{case['id']}/reply",
            json={"body": "Không có CSRF.", "expected_revision": 1, "idempotency_key": "support-receipt-customer-no-csrf-0001"},
        )
        assert denied.status_code == 403
        assert_case_unchanged(database, case["id"], count=before_count, revision=before_revision)
        stale = customer.post(
            f"/api/v1/support/cases/{case['id']}/reply",
            headers={"X-CSRF-Token": customer_csrf},
            json={"body": "Revision cũ không được ghi.", "expected_revision": 2, "idempotency_key": "support-receipt-customer-stale-0001"},
        )
        assert stale.status_code == 200
        assert stale.json()["error_code"] == "WEB_SUPPORT_CASE_CONFLICT"
        assert "receipt" not in stale.json().get("data", {})
        assert_case_unchanged(database, case["id"], count=before_count, revision=before_revision)

    with make_client(tmp_path, monkeypatch) as anonymous:
        denied = anonymous.post(
            f"/api/v1/support/cases/{case['id']}/reply",
            json={"body": "Khách ẩn danh không thể reply.", "expected_revision": 1, "idempotency_key": "support-receipt-anonymous-forbidden-0001"},
        )
        assert denied.status_code == 401
        assert_case_unchanged(database, case["id"], count=before_count, revision=before_revision)

    with make_client(tmp_path, monkeypatch) as second_customer:
        second_csrf = register_and_login(second_customer, "receipt-second-customer@example.com", "Khách thứ hai guard receipt")
        denied = second_customer.post(
            f"/api/v1/support/cases/{case['id']}/reply",
            headers={"X-CSRF-Token": second_csrf},
            json={"body": "Khách khác không thể reply case này.", "expected_revision": 1, "idempotency_key": "support-receipt-cross-owner-forbidden-0001"},
        )
        assert denied.status_code == 200
        denied_payload = denied.json()
        assert denied_payload["ok"] is False
        assert denied_payload["status"] == "guarded"
        assert denied_payload["error_code"] == "WEB_SUPPORT_CASE_NOT_FOUND"
        assert "receipt" not in denied_payload.get("data", {})
        rendered_denial = json.dumps(denied_payload, ensure_ascii=False)
        for private_value in (
            case["id"],
            "receipt-guard-customer@example.com",
            "receipt-second-customer@example.com",
            "Khách khác không thể reply case này.",
        ):
            assert private_value not in rendered_denial
        assert_case_unchanged(database, case["id"], count=before_count, revision=before_revision)

    with make_client(tmp_path, monkeypatch) as operator:
        operator_email = "receipt-guard-operator@example.com"
        operator_csrf = register_and_login(operator, operator_email, "Điều phối guard receipt")
        set_role(database, operator_email, "support_operator")
        before_count = message_count(database, case["id"])
        before_revision = case_revision(database, case["id"])
        denied = operator.post(
            f"/api/v1/support/admin/cases/{case['id']}/reply",
            json={"body": "Không có CSRF.", "visibility": "public", "expected_revision": 1, "idempotency_key": "support-receipt-operator-no-csrf-0001", "confirm": True},
        )
        assert denied.status_code == 403
        assert_case_unchanged(database, case["id"], count=before_count, revision=before_revision)
        unconfirmed = operator.post(
            f"/api/v1/support/admin/cases/{case['id']}/reply",
            headers={"X-CSRF-Token": operator_csrf},
            json={"body": "Chưa xác nhận.", "visibility": "public", "expected_revision": 1, "idempotency_key": "support-receipt-operator-no-confirm-0001", "confirm": False},
        )
        assert unconfirmed.status_code == 422
        assert_case_unchanged(database, case["id"], count=before_count, revision=before_revision)
        stale = operator.post(
            f"/api/v1/support/admin/cases/{case['id']}/reply",
            headers={"X-CSRF-Token": operator_csrf},
            json={"body": "Revision cũ không được ghi.", "visibility": "public", "expected_revision": 2, "idempotency_key": "support-receipt-operator-stale-0001", "confirm": True},
        )
        assert stale.status_code == 200
        assert stale.json()["error_code"] == "WEB_SUPPORT_CASE_CONFLICT"
        assert "receipt" not in stale.json().get("data", {})
        assert_case_unchanged(database, case["id"], count=before_count, revision=before_revision)


def _reply_handler_sections(source: str) -> tuple[str, str]:
    customer_start = source.index('if (action === "support-case-reply")')
    customer_end = source.index('if (action === "support-case-resolution-feedback")', customer_start)
    operator_start = source.index('if (action === "support-admin-case-reply")')
    operator_end = source.index('if (action === "support-admin-case-update")', operator_start)
    return source[customer_start:customer_end], source[operator_start:operator_end]


def _reply_receipt_sections(source: str) -> str:
    customer, operator = _reply_handler_sections(source)
    sections = [customer, operator]
    for marker in ("function supportReplyReceiptProjection", "function renderSupportReplyReceipt"):
        start = source.find(marker)
        if start < 0:
            continue
        end = source.find("\n  function ", start + len(marker))
        sections.append(source[start:] if end < 0 else source[start:end])
    return "\n".join(sections)


def test_reply_handlers_require_an_exact_safe_receipt_before_discarding_retry_keys() -> None:
    integration = INTEGRATION.read_text(encoding="utf-8")
    assert "function supportReplyReceiptProjection" in integration
    assert "function supportReplyRouteIsCurrent" in integration
    assert "function supportReplyDetailMatches" in integration
    for fragment in (
        'const keys = ["case_id", "revision", "state", "visibility", "action", "created_at", "delivery"]',
        "Object.keys(data).length !== 1",
        "Object.keys(receipt).length !== keys.length",
        "validSupportCaseId(receipt.case_id)",
        "Number.isSafeInteger(receipt.revision)",
        "SUPPORT_CASE_STATES.has(receipt.state)",
        'receipt.delivery !== "web_view_only"',
        "Date.parse(String(receipt.created_at || \"\"))",
    ):
        assert fragment in integration

    customer, operator = _reply_handler_sections(integration)
    for section, hydration in ((customer, "hydrateSupportCase(caseId)"), (operator, "hydrateSupportAdminCase(caseId)")):
        assert "const receipt = supportReplyReceiptProjection(result, expected);" in section
        assert "if (!receipt) throw new Error" in section
        assert section.index("supportReplyReceiptProjection(result, expected)") < section.index("discardSubmission(scope, submission)")
        assert section.index("supportReplyReceiptProjection(result, expected)") < section.index(hydration)
        assert section.index(hydration) < section.index("discardSubmission(scope, submission)")
        assert "Number.isInteger(error.status)" not in section


def test_reply_receipt_memory_stays_private_to_the_current_tab_and_route() -> None:
    integration = INTEGRATION.read_text(encoding="utf-8")
    combined = PORTAL.read_text(encoding="utf-8") + "\n" + integration
    assert "supportCustomerReplyReceipt" in combined
    assert "supportAdminReplyReceipt" in combined
    assert "function renderSupportReplyReceipt" in combined
    assert "data-support-reply-receipt" in combined
    for reset_field in ("supportCustomerReplyReceipt: {}", "supportAdminReplyReceipt: {}"):
        assert reset_field in integration
    receipt_sections = _reply_receipt_sections(combined)
    assert "localStorage" not in receipt_sections
    assert "sessionStorage" not in receipt_sections
    assert "URLSearchParams" not in receipt_sections
