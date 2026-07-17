"""Contract tests for the independently owned Web Support Desk.

The Support Desk deliberately has no Telegram, PayOS, wallet or provider
dependency.  These tests keep the Web-only ownership boundary meaningful as
the rest of the portal evolves.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib
import sqlite3
import sys

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_api", "copyfast_pages", "copyfast_projects", "copyfast_assets",
    "copyfast_project_packages", "copyfast_document_operations", "copyfast_image_runtime",
    "copyfast_image_operations", "copyfast_memory", "copyfast_support",
]


def make_client(
    tmp_path,
    monkeypatch,
    *,
    support_enabled: bool = True,
    legacy_allowlist_emails: str = "",
) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "copyfast-support-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-support-session-secret")
    monkeypatch.setenv("WEBAPP_SUPPORT_DESK_ENABLED", "true" if support_enabled else "false")
    # These retired variables deliberately remain populated in one test.  An
    # email/password account has no verified-email gate, so environment email
    # allowlists must never grant a support-operator role.
    if legacy_allowlist_emails:
        monkeypatch.setenv("WEBAPP_SUPPORT_MANAGER_EMAILS", legacy_allowlist_emails)
        monkeypatch.setenv("WEBAPP_SUPPORT_STAFF_EMAILS", legacy_allowlist_emails)
    else:
        monkeypatch.delenv("WEBAPP_SUPPORT_MANAGER_EMAILS", raising=False)
        monkeypatch.delenv("WEBAPP_SUPPORT_STAFF_EMAILS", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def register_and_login(client: TestClient, email: str, *, display_name: str = "Web Support Owner") -> str:
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
    return login.json()["data"]["csrf_token"]


def case_payload(key: str, **overrides) -> dict:
    payload = {
        "category": "image_error",
        "priority": "high",
        "subject": "Không tải được ảnh đã tạo",
        "detail": "Job đã hoàn tất nhưng khu vực assets chưa hiển thị ảnh đầu ra.",
        "idempotency_key": key,
    }
    payload.update(overrides)
    return payload


def create_case(client: TestClient, csrf: str, key: str = "support-case-create-0001", **overrides) -> dict:
    response = client.post(
        "/api/v1/support/cases",
        headers={"X-CSRF-Token": csrf},
        json=case_payload(key, **overrides),
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    return response.json()["data"]["case"]


def test_support_cases_are_csrf_owned_idempotent_and_private(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as first:
        csrf = register_and_login(first, "support-owner@example.com")
        payload = case_payload("support-case-create-0001")

        denied = first.post("/api/v1/support/cases", json=payload)
        assert denied.status_code == 403
        assert denied.json()["error_code"] == "REQUEST_DENIED"

        created_response = first.post(
            "/api/v1/support/cases",
            headers={"X-CSRF-Token": csrf},
            json=payload,
        )
        assert created_response.status_code == 200
        created = created_response.json()["data"]["case"]
        assert created["state"] == "new"
        assert created["revision"] == 1
        assert "detail" not in created
        assert "customer" not in created

        replay = first.post(
            "/api/v1/support/cases",
            headers={"X-CSRF-Token": csrf},
            json=payload,
        )
        assert replay.status_code == 200
        assert replay.json()["data"]["case"]["id"] == created["id"]
        collision = first.post(
            "/api/v1/support/cases",
            headers={"X-CSRF-Token": csrf},
            json=case_payload("support-case-create-0001", subject="Một yêu cầu khác cùng key"),
        )
        assert collision.status_code == 409

        listing = first.get("/api/v1/support/cases", params={"state": "all"})
        assert listing.status_code == 200
        assert listing.json()["data"]["delivery"] == "web_view_only"
        assert [item["id"] for item in listing.json()["data"]["items"]] == [created["id"]]
        assert "detail" not in listing.json()["data"]["items"][0]

        detail = first.get(f"/api/v1/support/cases/{created['id']}")
        assert detail.status_code == 200
        body = detail.json()["data"]
        assert body["delivery"] == "web_view_only"
        assert body["case"]["detail"] == payload["detail"]
        assert body["messages"] == [{
            "id": body["messages"][0]["id"],
            "author_role": "customer",
            "visibility": "public",
            "body": payload["detail"],
            "created_at": body["messages"][0]["created_at"],
        }]
        assert body["events"][0]["action"] == "case_created"

        # A Web-only case does not require a Telegram link.  A different
        # signed account sees the same not-found envelope and no private text.
        with make_client(tmp_path, monkeypatch) as second:
            csrf_second = register_and_login(second, "support-other@example.com")
            hidden = second.get(f"/api/v1/support/cases/{created['id']}")
            assert hidden.status_code == 200
            assert hidden.json()["error_code"] == "WEB_SUPPORT_CASE_NOT_FOUND"
            assert payload["detail"] not in hidden.text
            assert second.get("/api/v1/support/cases").json()["data"]["items"] == []
            denied_reply = second.post(
                f"/api/v1/support/cases/{created['id']}/reply",
                headers={"X-CSRF-Token": csrf_second},
                json={
                    "body": "Tôi không phải chủ sở hữu.",
                    "expected_revision": 1,
                    "idempotency_key": "support-other-reply-0001",
                },
            )
            assert denied_reply.status_code == 200
            assert denied_reply.json()["error_code"] == "WEB_SUPPORT_CASE_NOT_FOUND"


def test_support_case_listing_paginates_without_cross_account_metadata(tmp_path, monkeypatch):
    """The customer portal relies on this bounded owner-scoped list receipt."""
    with make_client(tmp_path, monkeypatch) as owner:
        csrf = register_and_login(owner, "support-pagination-owner@example.com")
        first_case = create_case(
            owner,
            csrf,
            "support-pagination-first-0001",
            subject="Yêu cầu cũ cần theo dõi",
        )
        second_case = create_case(
            owner,
            csrf,
            "support-pagination-second-0001",
            subject="Yêu cầu mới cần theo dõi",
        )

        first_page = owner.get("/api/v1/support/cases", params={"limit": 1, "offset": 0, "state": "all"})
        assert first_page.status_code == 200
        first_data = first_page.json()["data"]
        assert len(first_data["items"]) == 1
        assert first_data["has_more"] is True
        assert first_data["next_offset"] == 1

        second_page = owner.get("/api/v1/support/cases", params={"limit": 1, "offset": first_data["next_offset"], "state": "all"})
        assert second_page.status_code == 200
        second_data = second_page.json()["data"]
        assert len(second_data["items"]) == 1
        assert second_data["has_more"] is False
        assert second_data["next_offset"] is None
        assert {first_data["items"][0]["id"], second_data["items"][0]["id"]} == {first_case["id"], second_case["id"]}

        with make_client(tmp_path, monkeypatch) as other:
            register_and_login(other, "support-pagination-other@example.com")
            hidden = other.get("/api/v1/support/cases", params={"limit": 1, "offset": 0, "state": "all"})
            assert hidden.status_code == 200
            assert hidden.json()["data"]["items"] == []
            assert hidden.json()["data"]["has_more"] is False
            assert hidden.json()["data"]["next_offset"] is None


def test_support_admin_case_listing_is_role_guarded_and_pages_all_cases_once(tmp_path, monkeypatch):
    """Staff queue paging must not hide records after the first 50 cases.

    Cases are inserted directly only to keep this boundary test fast.  The
    role is still granted exclusively through the protected account record;
    neither the request nor a query parameter can turn the signed account
    into a Support Desk operator.
    """
    with make_client(tmp_path, monkeypatch) as client:
        register_and_login(client, "support-admin-pagination@example.com")

        denied = client.get("/api/v1/support/admin/cases", params={"limit": 50, "offset": 0, "state": "all"})
        assert denied.status_code == 403
        assert denied.json()["error_code"] == "REQUEST_DENIED"

        case_ids = [f"10000000-0000-4000-8000-{index:012d}" for index in range(1, 102)]
        with sqlite3.connect(tmp_path / "copyfast-support-test.db") as conn:
            account_id = conn.execute(
                "SELECT id FROM web_accounts WHERE email='support-admin-pagination@example.com'"
            ).fetchone()[0]
            conn.execute("UPDATE web_accounts SET role_cache='support_manager' WHERE id=?", (account_id,))
            rows = []
            for index, case_id in enumerate(case_ids, start=1):
                timestamp = f"2026-07-{index // 24 + 1:02d}T{index % 24:02d}:00:00+00:00"
                rows.append((
                    case_id,
                    account_id,
                    "general_support",
                    "normal",
                    f"Admin pagination case {index:03d}",
                    "Nội dung kiểm thử nội bộ cho phân trang hàng đợi.",
                    "new",
                    1,
                    timestamp,
                    timestamp,
                    timestamp,
                    None,
                    None,
                ))
            conn.executemany(
                """INSERT INTO web_support_cases
                   (id, account_id, category, priority, subject, initial_detail, state, revision,
                    created_at, updated_at, last_public_message_at, resolved_at, closed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                rows,
            )
            conn.commit()

        pages = []
        for offset, expected_count, expected_more, expected_next in (
            (0, 50, True, 50),
            (50, 50, True, 100),
            (100, 1, False, None),
        ):
            response = client.get(
                "/api/v1/support/admin/cases",
                params={"limit": 50, "offset": offset, "state": "all"},
            )
            assert response.status_code == 200
            data = response.json()["data"]
            assert len(data["items"]) == expected_count
            assert data["has_more"] is expected_more
            assert data["next_offset"] == expected_next
            pages.append({item["id"] for item in data["items"]})

        assert all(left.isdisjoint(right) for index, left in enumerate(pages) for right in pages[index + 1:])
        assert set().union(*pages) == set(case_ids)


def test_support_admin_case_listing_filters_web_native_customer_care_metadata_only(tmp_path, monkeypatch):
    """Staff can filter queue metadata without supplying an account identifier."""

    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "support-care-filter-manager@example.com")
        technical = create_case(client, csrf, "support-care-filter-technical-0001", subject="Case kỹ thuật cần điều phối")
        defaulted = create_case(client, csrf, "support-care-filter-default-0001", subject="Case chưa được điều phối")
        product = create_case(client, csrf, "support-care-filter-product-0001", subject="Case sản phẩm cần điều phối")
        database = tmp_path / "copyfast-support-test.db"
        now = "2026-07-16T12:00:00+00:00"
        with sqlite3.connect(database) as conn:
            manager_id = conn.execute(
                "SELECT id FROM web_accounts WHERE email=?",
                ("support-care-filter-manager@example.com",),
            ).fetchone()[0]
            conn.execute("UPDATE web_accounts SET role_cache='support_manager' WHERE id=?", (manager_id,))
            conn.executemany(
                """INSERT INTO web_support_case_controls
                   (case_id, team_queue, assigned_account_id, sla_class, first_staff_touched_at,
                    escalation_state, escalation_reason, escalation_requested_at,
                    escalation_acknowledged_at, escalation_resolved_at,
                    escalation_actor_account_id, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        technical["id"], "technical", manager_id, "priority", now,
                        "requested", "Cần rà soát technical nội bộ.", now, None, None, manager_id, now,
                    ),
                    (
                        product["id"], "product", manager_id, "critical", now,
                        "acknowledged", "Đang có quản lý xử lý nội bộ.", now, now, None, manager_id, now,
                    ),
                ],
            )
            conn.commit()

        technical_only = client.get(
            "/api/v1/support/admin/cases",
            params={
                "team_queue": "technical", "assignment": "assigned",
                "sla_class": "priority", "escalation_state": "requested",
            },
        )
        assert technical_only.status_code == 200
        technical_data = technical_only.json()["data"]
        assert [item["id"] for item in technical_data["items"]] == [technical["id"]]
        assert technical_data["filters"] == {
            "state": "all", "category": "", "team_queue": "technical",
            "assignment": "assigned", "sla_class": "priority", "care_sla_status": "all",
            "escalation_state": "requested",
        }
        assert "assigned_account_id" not in str(technical_only.request.url)
        # The queue list can name the assignee but must not fan out an
        # internal account identifier or an escalation narrative to every
        # staff browser.  A case-specific manager detail retains its narrowly
        # scoped roster ID for the triage selector.
        listed_care = technical_data["items"][0]["care"]
        assert listed_care["assignee"] == {"display_name": "Web Support Owner"}
        assert "reason" not in listed_care["escalation"]

        detail = client.get(f"/api/v1/support/admin/cases/{technical['id']}")
        assert detail.status_code == 200
        assert detail.json()["data"]["case"]["care"]["assignee"]["id"] == manager_id

        # ``mine`` is identity-derived on the server. The browser sends only
        # the fixed enum, yet it can combine the view with the ordinary queue
        # filters without receiving a roster/account identifier in the list.
        mine = client.get("/api/v1/support/admin/cases", params={"assignment": "mine"})
        assert mine.status_code == 200
        mine_data = mine.json()["data"]
        assert {item["id"] for item in mine_data["items"]} == {technical["id"], product["id"]}
        assert mine_data["filters"]["assignment"] == "mine"
        assert "assigned_account_id" not in str(mine.request.url)
        assert manager_id not in str(mine_data)
        mine_technical = client.get(
            "/api/v1/support/admin/cases",
            params={"assignment": "mine", "team_queue": "technical"},
        )
        assert mine_technical.status_code == 200
        assert [item["id"] for item in mine_technical.json()["data"]["items"]] == [technical["id"]]

        register_and_login(client, "support-care-filter-operator@example.com")
        with sqlite3.connect(database) as conn:
            operator_id = conn.execute(
                "SELECT id FROM web_accounts WHERE email=?",
                ("support-care-filter-operator@example.com",),
            ).fetchone()[0]
            conn.execute("UPDATE web_accounts SET role_cache='support_operator' WHERE id=?", (operator_id,))
            conn.commit()
        operator_detail = client.get(f"/api/v1/support/admin/cases/{technical['id']}")
        assert operator_detail.status_code == 200
        assert "id" not in operator_detail.json()["data"]["case"]["care"]["assignee"]
        operator_mine = client.get("/api/v1/support/admin/cases", params={"assignment": "mine"})
        assert operator_mine.status_code == 200
        assert operator_mine.json()["data"]["items"] == []
        assert operator_mine.json()["data"]["filters"]["assignment"] == "mine"
        # An unrecognized browser query parameter cannot turn the signed
        # operator into the manager or reveal the manager's cases.
        forged_mine = client.get(
            "/api/v1/support/admin/cases",
            params={"assignment": "mine", "assigned_account_id": manager_id},
        )
        assert forged_mine.status_code == 200
        assert forged_mine.json()["data"]["items"] == []
        assert manager_id not in str(forged_mine.json()["data"])

        default_only = client.get(
            "/api/v1/support/admin/cases",
            params={
                "team_queue": "general", "assignment": "unassigned",
                "sla_class": "standard", "escalation_state": "none",
            },
        )
        assert default_only.status_code == 200
        assert [item["id"] for item in default_only.json()["data"]["items"]] == [defaulted["id"]]

        for name, value in (
            ("team_queue", "untrusted_queue"),
            ("assignment", "account-id-must-not-be-a-filter"),
            ("sla_class", "instant"),
            ("escalation_state", "external"),
        ):
            rejected = client.get("/api/v1/support/admin/cases", params={name: value})
            assert rejected.status_code == 422


def test_support_admin_case_listing_filters_current_customer_care_sla_status_server_side(tmp_path, monkeypatch):
    """The first-touch target is filtered before pagination, not in the browser."""

    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "support-care-sla-filter-manager@example.com")
        cases = {
            "pending": create_case(client, csrf, "support-care-sla-pending-0001", subject="Case chờ tiếp nhận"),
            "overdue_unacknowledged": create_case(client, csrf, "support-care-sla-overdue-0001", subject="Case quá hạn tiếp nhận"),
            "within_target": create_case(client, csrf, "support-care-sla-within-0001", subject="Case đã nhận đúng hạn"),
            "breached": create_case(client, csrf, "support-care-sla-breached-0001", subject="Case đã nhận quá hạn"),
            "unavailable": create_case(client, csrf, "support-care-sla-unavailable-0001", subject="Case thiếu mốc bắt đầu"),
        }
        database = tmp_path / "copyfast-support-test.db"
        now = datetime.now(timezone.utc).replace(microsecond=0)
        created_at = {
            "pending": (now - timedelta(hours=1)).isoformat(),
            "overdue_unacknowledged": (now - timedelta(hours=25)).isoformat(),
            "within_target": (now - timedelta(hours=30)).isoformat(),
            "breached": (now - timedelta(hours=30)).isoformat(),
            "unavailable": "not-a-web-timestamp",
        }
        with sqlite3.connect(database) as conn:
            manager_id = conn.execute(
                "SELECT id FROM web_accounts WHERE email=?",
                ("support-care-sla-filter-manager@example.com",),
            ).fetchone()[0]
            conn.execute("UPDATE web_accounts SET role_cache='support_manager' WHERE id=?", (manager_id,))
            conn.executemany(
                "UPDATE web_support_cases SET created_at=?, updated_at=? WHERE id=?",
                [(created_at[status], created_at[status], case["id"]) for status, case in cases.items()],
            )
            conn.executemany(
                """INSERT INTO web_support_case_controls
                   (case_id, team_queue, assigned_account_id, sla_class, first_staff_touched_at,
                    escalation_state, escalation_reason, escalation_requested_at,
                    escalation_acknowledged_at, escalation_resolved_at,
                    escalation_actor_account_id, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'none', '', NULL, NULL, NULL, NULL, ?)""",
                [
                    # An invalid touch timestamp is treated exactly like no
                    # touch by _sla_public, so it remains a pending target.
                    (cases["pending"]["id"], "technical", manager_id, "standard", "not-a-touch-timestamp", now.isoformat()),
                    (cases["overdue_unacknowledged"]["id"], "technical", manager_id, "standard", None, now.isoformat()),
                    (cases["within_target"]["id"], "product", manager_id, "critical", (now - timedelta(hours=29)).isoformat(), now.isoformat()),
                    (cases["breached"]["id"], "technical", manager_id, "priority", (now - timedelta(hours=20)).isoformat(), now.isoformat()),
                    (cases["unavailable"]["id"], "general", None, "standard", None, now.isoformat()),
                ],
            )
            conn.commit()

        for status, case in cases.items():
            response = client.get("/api/v1/support/admin/cases", params={"care_sla_status": status})
            assert response.status_code == 200
            data = response.json()["data"]
            assert [item["id"] for item in data["items"]] == [case["id"]]
            assert data["filters"]["care_sla_status"] == status
            assert data["items"][0]["care"]["sla"]["status"] == status
            # Staff lists remain redacted even while the server derives a
            # status from control metadata and its own clock.
            assert manager_id not in str(data)

        combined = client.get(
            "/api/v1/support/admin/cases",
            params={
                "assignment": "mine",
                "team_queue": "technical",
                "care_sla_status": "overdue_unacknowledged",
            },
        )
        assert combined.status_code == 200
        assert [item["id"] for item in combined.json()["data"]["items"]] == [cases["overdue_unacknowledged"]["id"]]
        assert manager_id not in str(combined.json()["data"])

        invalid = client.get("/api/v1/support/admin/cases", params={"care_sla_status": "external_clock"})
        assert invalid.status_code == 422


def test_support_case_lifecycle_rejects_sensitive_manual_payment_content_and_sanitizes_audit(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "support-lifecycle@example.com")
        secret_probe = "api_key=" + "sk_" + "1234567890abcdefghi"
        blocked_secret = client.post(
            "/api/v1/support/cases",
            headers={"X-CSRF-Token": csrf},
            json=case_payload("support-case-secret-0001", detail=secret_probe),
        )
        assert blocked_secret.status_code == 422
        blocked_payment_proof = client.post(
            "/api/v1/support/cases",
            headers={"X-CSRF-Token": csrf},
            json=case_payload("support-case-payment-proof-0001", detail="Đây là TXID: abcd1234 và bill thanh toán."),
        )
        assert blocked_payment_proof.status_code == 422
        forged_browser_role = client.post(
            "/api/v1/support/cases",
            headers={"X-CSRF-Token": csrf},
            json={**case_payload("support-case-forged-role-0001"), "admin_id": "browser-forged"},
        )
        assert forged_browser_role.status_code == 422
        assert client.get("/api/v1/support/cases", params={"q": secret_probe}).status_code == 422

        audit_subject = "Nội dung ticket không được ghi vào audit"
        audit_detail = "Mô tả riêng tư chỉ phục vụ cho nhân viên hỗ trợ Web."
        case = create_case(
            client,
            csrf,
            "support-case-lifecycle-0001",
            subject=audit_subject,
            detail=audit_detail,
        )

        missing_confirm = client.post(
            f"/api/v1/support/cases/{case['id']}/close",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 1, "idempotency_key": "support-close-missing-confirm-0001"},
        )
        assert missing_confirm.status_code == 422
        closed = client.post(
            f"/api/v1/support/cases/{case['id']}/close",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 1, "idempotency_key": "support-close-0001", "confirm": True},
        )
        assert closed.status_code == 200
        assert closed.json()["data"]["case"]["state"] == "closed"
        assert closed.json()["data"]["case"]["revision"] == 2

        closed_reply = client.post(
            f"/api/v1/support/cases/{case['id']}/reply",
            headers={"X-CSRF-Token": csrf},
            json={
                "body": "Vui lòng mở lại để tiếp tục.",
                "expected_revision": 2,
                "idempotency_key": "support-closed-reply-0001",
            },
        )
        assert closed_reply.status_code == 200
        assert closed_reply.json()["error_code"] == "WEB_SUPPORT_CASE_CLOSED"

        reopened = client.post(
            f"/api/v1/support/cases/{case['id']}/reopen",
            headers={"X-CSRF-Token": csrf},
            json={"expected_revision": 2, "idempotency_key": "support-reopen-0001", "confirm": True},
        )
        assert reopened.status_code == 200
        assert reopened.json()["data"]["case"]["state"] == "reviewing"
        assert reopened.json()["data"]["case"]["revision"] == 3

        reply = client.post(
            f"/api/v1/support/cases/{case['id']}/reply",
            headers={"X-CSRF-Token": csrf},
            json={
                "body": "Tôi đã kiểm tra lại trên trình duyệt khác.",
                "expected_revision": 3,
                "idempotency_key": "support-reply-0001",
            },
        )
        assert reply.status_code == 200
        assert reply.json()["data"]["case"]["revision"] == 4
        stale = client.post(
            f"/api/v1/support/cases/{case['id']}/reply",
            headers={"X-CSRF-Token": csrf},
            json={
                "body": "Không được ghi khi bản đã cũ.",
                "expected_revision": 3,
                "idempotency_key": "support-reply-stale-0001",
            },
        )
        assert stale.status_code == 200
        assert stale.json()["error_code"] == "WEB_SUPPORT_CASE_CONFLICT"

        with sqlite3.connect(tmp_path / "copyfast-support-test.db") as conn:
            audit_rows = conn.execute("SELECT detail FROM web_audit_events WHERE action LIKE 'web.support.%'").fetchall()
        assert audit_rows
        assert all(audit_subject not in row[0] and audit_detail not in row[0] for row in audit_rows)
        source = (open("copyfast_support.py", encoding="utf-8").read()).lower()
        assert "import copyfast_bridge" not in source
        assert "copyfast_bridge." not in source
        assert "import requests" not in source
        assert "import httpx" not in source


def test_support_intake_allows_ordinary_account_transaction_words_but_blocks_payment_identifiers(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "support-word-boundary@example.com")
        ordinary = create_case(
            client,
            csrf,
            "support-ordinary-words-0001",
            subject="Review account workflow",
            detail="Please review this account workflow and transaction state; there is no payment reference in this case.",
        )
        assert ordinary["id"]

        account_number = client.post(
            "/api/v1/support/cases",
            headers={"X-CSRF-Token": csrf},
            json=case_payload(
                "support-account-number-0001",
                detail="I was asked to provide an account number for a payment reference.",
            ),
        )
        assert account_number.status_code == 422
        transaction_id = client.post(
            "/api/v1/support/cases",
            headers={"X-CSRF-Token": csrf},
            json=case_payload(
                "support-transaction-id-0001",
                detail="The payment screen displays transaction id abc-123, please check it.",
            ),
        )
        assert transaction_id.status_code == 422


def test_support_rejects_sensitive_literals_and_card_separators_at_every_write_sink(tmp_path, monkeypatch):
    """The server, not the browser, blocks sensitive prose before persistence."""
    blocked_values = (
        "sk_" + "abcdefghijklmnopqrstuvwxyz123456",
        "ghp_" + "abcdefghijklmnopqrstuvwxyz123456789012345678",
        "AIza" + "SyDUMMYEXAMPLEKEY123456789012345",
        "AKIA" + "IOSFODNN7EXAMPLE",
        "Mã xác thực: 123456",
        "STK: 0123456789",
        "Tài khoản ngân hàng 0123456789",
        "Bank account: 0123456789",
        "Mã GD 1234567890",
        "4111 1111 1111 1111",
        "4111  1111  1111  1111",
        "4111.1111.1111.1111",
        "4111/1111/1111/1111",
        "4111\n1111\n1111\n1111",
    )
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "support-sensitive-sinks@example.com")
        case = create_case(client, csrf, "support-sensitive-base-0001")

        def assert_rejected(response, value: str) -> None:
            assert response.status_code == 422
            # The application-level validation handler deliberately does not
            # reflect Pydantic's raw invalid input back to the client.
            assert response.json()["error_code"] == "REQUEST_INVALID"
            assert value not in response.text

        for index, value in enumerate(blocked_values):
            assert_rejected(
                client.post(
                    "/api/v1/support/cases",
                    headers={"X-CSRF-Token": csrf},
                    json=case_payload(f"support-sensitive-create-{index:02d}-0001", detail=value),
                ),
                value,
            )
            assert_rejected(
                client.post(
                    f"/api/v1/support/cases/{case['id']}/reply",
                    headers={"X-CSRF-Token": csrf},
                    json={
                        "body": value,
                        "expected_revision": 1,
                        "idempotency_key": f"support-sensitive-reply-{index:02d}-0001",
                    },
                ),
                value,
            )

        # The same signed account receives its operator role only from the
        # server-side account table.  Direct admin writes use the identical
        # content guard, so a crafted browser request cannot bypass it.
        with sqlite3.connect(tmp_path / "copyfast-support-test.db") as conn:
            conn.execute(
                "UPDATE web_accounts SET role_cache='support_manager' WHERE email='support-sensitive-sinks@example.com'"
            )
            conn.commit()

        for index, value in enumerate(blocked_values):
            assert_rejected(
                client.post(
                    f"/api/v1/support/admin/cases/{case['id']}/reply",
                    headers={"X-CSRF-Token": csrf},
                    json={
                        "body": value,
                        "visibility": "internal",
                        "expected_revision": 1,
                        "idempotency_key": f"support-sensitive-admin-reply-{index:02d}-0001",
                        "confirm": True,
                    },
                ),
                value,
            )
            assert_rejected(
                client.post(
                    f"/api/v1/support/admin/cases/{case['id']}/update",
                    headers={"X-CSRF-Token": csrf},
                    json={
                        "state": "reviewing",
                        "priority": "normal",
                        "operation_note": value,
                        "expected_revision": 1,
                        "idempotency_key": f"support-sensitive-admin-update-{index:02d}-0001",
                        "confirm": True,
                    },
                ),
                value,
            )

        # `_safe_line` protects the subject as well as long-form fields.
        assert_rejected(
            client.post(
                "/api/v1/support/cases",
                headers={"X-CSRF-Token": csrf},
                json=case_payload(
                    "support-sensitive-subject-0001",
                    subject=blocked_values[0],
                    detail="Nội dung hợp lệ nhưng chủ đề không được là token.",
                ),
            ),
            blocked_values[0],
        )

        with sqlite3.connect(tmp_path / "copyfast-support-test.db") as conn:
            messages = [str(row[0]) for row in conn.execute("SELECT body FROM web_support_messages WHERE case_id=?", (case["id"],))]
            revision = conn.execute("SELECT revision FROM web_support_cases WHERE id=?", (case["id"],)).fetchone()[0]
        assert revision == 1
        assert len(messages) == 1
        assert all(value not in "\n".join(messages) for value in blocked_values)


def test_support_admin_same_state_updates_preserve_original_resolved_and_closed_times(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "support-timestamp-manager@example.com")
        case = create_case(client, csrf, "support-timestamp-case-0001")
        with sqlite3.connect(tmp_path / "copyfast-support-test.db") as conn:
            conn.execute(
                "UPDATE web_accounts SET role_cache='support_manager' WHERE email='support-timestamp-manager@example.com'"
            )
            conn.commit()

        def update_case(expected_revision: int, state: str, key: str, note: str) -> dict:
            response = client.post(
                f"/api/v1/support/admin/cases/{case['id']}/update",
                headers={"X-CSRF-Token": csrf},
                json={
                    "state": state,
                    "priority": "normal",
                    "operation_note": note,
                    "expected_revision": expected_revision,
                    "idempotency_key": key,
                    "confirm": True,
                },
            )
            assert response.status_code == 200
            assert response.json()["ok"] is True
            return response.json()["data"]["case"]

        resolved = update_case(1, "resolved", "support-resolve-0001", "Đã xử lý bước đầu và chờ rà soát nội bộ.")
        assert resolved["state"] == "resolved"
        assert resolved["resolved_at"]
        # Avoid a same-second false positive: use durable, deliberately old
        # values before repeating each same-state update. A regression that
        # writes `utc_now()` again would now be observable deterministically.
        resolved_marker = "2001-02-03T04:05:06+00:00"
        with sqlite3.connect(tmp_path / "copyfast-support-test.db") as conn:
            conn.execute("UPDATE web_support_cases SET resolved_at=? WHERE id=?", (resolved_marker, case["id"]))
            conn.commit()
        resolved_again = update_case(2, "resolved", "support-resolve-repeat-0001", "Giữ nguyên thời điểm đã xử lý khi cập nhật triage.")
        assert resolved_again["resolved_at"] == resolved_marker
        assert resolved_again["closed_at"] is None

        closed = update_case(3, "closed", "support-close-admin-0001", "Đóng case sau khi hoàn tất xác nhận nội bộ.")
        assert closed["state"] == "closed"
        assert closed["closed_at"]
        closed_marker = "2002-03-04T05:06:07+00:00"
        with sqlite3.connect(tmp_path / "copyfast-support-test.db") as conn:
            conn.execute("UPDATE web_support_cases SET closed_at=? WHERE id=?", (closed_marker, case["id"]))
            conn.commit()
        closed_again = update_case(4, "closed", "support-close-admin-repeat-0001", "Giữ nguyên thời điểm đóng khi chỉ sửa triage.")
        assert closed_again["closed_at"] == closed_marker
        assert closed_again["resolved_at"] == resolved_marker


def test_support_staff_uses_server_side_role_csrf_confirm_and_private_notes(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as customer:
        customer_csrf = register_and_login(customer, "support-customer@example.com", display_name="Khách hỗ trợ")
        case = create_case(customer, customer_csrf, "support-staff-case-0001")

        unauthorized = customer.get("/api/v1/support/admin/summary")
        assert unauthorized.status_code == 403
        assert unauthorized.json()["error_code"] == "REQUEST_DENIED"
        protected_page = customer.get("/admin/support", follow_redirects=False)
        assert protected_page.status_code == 403
        assert protected_page.json()["error_code"] == "REQUEST_DENIED"

        # Role state is set only in the server-side account store for this
        # test.  No request body/query parameter can grant operator access.
        with sqlite3.connect(tmp_path / "copyfast-support-test.db") as conn:
            conn.execute(
                "INSERT INTO web_accounts (id, email, password_hash, display_name, canonical_user_id, role_cache, is_active, password_login_enabled, created_at, updated_at) "
                "SELECT 'test-support-admin', 'support-manager@example.com', password_hash, 'Support Manager', NULL, 'support_manager', 1, 1, created_at, updated_at "
                "FROM web_accounts WHERE email='support-customer@example.com'"
            )
            conn.execute(
                "INSERT INTO web_account_profiles (account_id, locale, timezone, avatar_style, created_at, updated_at) "
                "SELECT 'test-support-admin', locale, timezone, avatar_style, created_at, updated_at "
                "FROM web_account_profiles WHERE account_id=(SELECT id FROM web_accounts WHERE email='support-customer@example.com')"
            )
            conn.commit()

        # The duplicate test principal reuses a known password hash, but is
        # otherwise a distinct signed account with the server-side admin role.
        with make_client(tmp_path, monkeypatch) as manager:
            manager_login = manager.post(
                "/api/v1/auth/login",
                json={"email": "support-manager@example.com", "password": "correct-horse-battery-staple"},
            )
            assert manager_login.status_code == 200
            manager_csrf = manager_login.json()["data"]["csrf_token"]
            summary = manager.get("/api/v1/support/admin/summary")
            assert summary.status_code == 200
            assert summary.json()["data"]["operator_role"] == "manager"
            assert manager.get("/admin/support", follow_redirects=False).status_code == 200

            no_csrf = manager.post(
                f"/api/v1/support/admin/cases/{case['id']}/reply",
                json={
                    "body": "Đã nhận yêu cầu.", "visibility": "internal", "expected_revision": 1,
                    "idempotency_key": "support-admin-no-csrf-0001", "confirm": True,
                },
            )
            assert no_csrf.status_code == 403
            no_confirm = manager.post(
                f"/api/v1/support/admin/cases/{case['id']}/reply",
                headers={"X-CSRF-Token": manager_csrf},
                json={
                    "body": "Ghi chú nội bộ không hiển thị cho khách.", "visibility": "internal", "expected_revision": 1,
                    "idempotency_key": "support-admin-no-confirm-0001", "confirm": False,
                },
            )
            assert no_confirm.status_code == 422

            internal_text = "Ghi chú nội bộ không hiển thị cho khách."
            internal = manager.post(
                f"/api/v1/support/admin/cases/{case['id']}/reply",
                headers={"X-CSRF-Token": manager_csrf},
                json={
                    "body": internal_text, "visibility": "internal", "expected_revision": 1,
                    "idempotency_key": "support-admin-internal-0001", "confirm": True,
                },
            )
            assert internal.status_code == 200
            assert internal.json()["data"]["case"]["revision"] == 2
            admin_detail = manager.get(f"/api/v1/support/admin/cases/{case['id']}").json()["data"]
            assert any(item["body"] == internal_text and item["visibility"] == "internal" for item in admin_detail["messages"])
            assert all("author_display_name" in item for item in admin_detail["messages"])

            public = manager.post(
                f"/api/v1/support/admin/cases/{case['id']}/reply",
                headers={"X-CSRF-Token": manager_csrf},
                json={
                    "body": "Đội hỗ trợ đã xem và đang chờ bạn xác nhận lại.", "visibility": "public", "expected_revision": 2,
                    "idempotency_key": "support-admin-public-0001", "confirm": True,
                },
            )
            assert public.status_code == 200
            assert public.json()["data"]["case"]["state"] == "waiting_user"
            assert public.json()["data"]["case"]["revision"] == 3

            note = "Đã xác minh và chuyển sang trạng thái giải quyết."
            updated = manager.post(
                f"/api/v1/support/admin/cases/{case['id']}/update",
                headers={"X-CSRF-Token": manager_csrf},
                json={
                    "state": "resolved", "priority": "normal", "operation_note": note,
                    "expected_revision": 3, "idempotency_key": "support-admin-update-0001", "confirm": True,
                },
            )
            assert updated.status_code == 200
            assert updated.json()["data"]["case"]["state"] == "resolved"

        # Reopen a fresh app/client so the assertion is made from the
        # customer's signed session, not from an admin display projection.
        with make_client(tmp_path, monkeypatch) as customer_again:
            customer_login = customer_again.post(
                "/api/v1/auth/login",
                json={"email": "support-customer@example.com", "password": "correct-horse-battery-staple"},
            )
            assert customer_login.status_code == 200
            customer_detail = customer_again.get(f"/api/v1/support/cases/{case['id']}").json()["data"]
            messages = customer_detail["messages"]
            assert internal_text not in str(messages)
            assert any(item["visibility"] == "public" and item["author_role"] == "operator" for item in messages)
            customer_actions = {item["action"] for item in customer_detail["events"]}
            assert "operator_noted_internal" not in customer_actions
            assert "operator_updated" not in customer_actions
            with sqlite3.connect(tmp_path / "copyfast-support-test.db") as conn:
                audit_rows = conn.execute("SELECT detail FROM web_audit_events WHERE action='web.support.admin.update'").fetchall()
            assert audit_rows
            assert all(note not in row[0] for row in audit_rows)


def test_support_staff_role_is_provisioned_server_side_email_allowlists_are_ignored_and_flag_fails_closed(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch, legacy_allowlist_emails="support-operator@example.com") as client:
        register_and_login(client, "support-operator@example.com")
        unsafe_allowlist = client.get("/api/v1/support/admin/summary")
        assert unsafe_allowlist.status_code == 403
        assert unsafe_allowlist.json()["error_code"] == "REQUEST_DENIED"

        with sqlite3.connect(tmp_path / "copyfast-support-test.db") as conn:
            conn.execute(
                "UPDATE web_accounts SET role_cache='support_operator' WHERE email='support-operator@example.com'"
            )
            conn.commit()
        # `current_session()` reloads the account role from the server-side
        # account store. The browser did not supply an ID or a role claim.
        summary = client.get("/api/v1/support/admin/summary")
        assert summary.status_code == 200
        assert summary.json()["data"]["operator_role"] == "operator"

    with make_client(tmp_path, monkeypatch, support_enabled=False) as disabled:
        register_and_login(disabled, "support-disabled@example.com")
        response = disabled.get("/api/v1/support/summary")
        assert response.status_code == 503
        assert response.json()["ok"] is False
