"""Focused contracts for the role-aware Admin ERP navigation directory."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import copyfast_admin_erp_navigation as navigation


def _client_for(account: dict | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(navigation.router)
    if account is not None:
        # The production dependency reads this account from the signed,
        # server-side session store.  Tests override only the dependency, not
        # a query/body value that a browser could submit.
        app.dependency_overrides[navigation.require_account] = lambda: account
    return TestClient(app)


def _module_ids(payload: dict) -> set[str]:
    return {
        module["id"]
        for group in payload["data"]["groups"]
        for module in group["modules"]
    }


def test_navigation_requires_a_signed_account(monkeypatch) -> None:
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-admin-navigation-secret")
    with _client_for() as client:
        response = client.get("/api/v1/admin/navigation")
    assert response.status_code == 401


def test_customer_cannot_turn_a_browser_role_hint_into_admin_navigation(monkeypatch) -> None:
    calls: list[str] = []

    async def unexpected_canonical_check(_request):
        calls.append("canonical")
        raise AssertionError("Non-admin sessions must never call the Bot bridge")

    monkeypatch.setattr(navigation, "require_canonical_admin", unexpected_canonical_check)
    account = {
        "id": "web-customer",
        "email": "customer@example.com",
        "role": "user",
        "canonical_user_id": "not-authorized",
    }
    with _client_for(account) as client:
        response = client.get("/api/v1/admin/navigation")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["status"] == "guarded"
    assert body["data"]["groups"] == []
    assert body["data"]["access"] == {
        "canonical_admin": False,
        "web_support": False,
        "web_support_scope": "none",
        "web_local_admin": False,
    }
    assert calls == []
    # The manifest never echoes browser identity, the cached role, or the
    # canonical ID back into a navigation response.
    assert "customer@example.com" not in str(body["data"])
    assert "not-authorized" not in str(body["data"])


def test_support_operator_receives_only_web_native_staff_modules(monkeypatch) -> None:
    monkeypatch.setenv("WEBAPP_SUPPORT_DESK_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_AUTOPILOT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_RELIABILITY_FOLLOWUP_ENABLED", "true")

    async def unexpected_canonical_check(_request):
        raise AssertionError("Support-only sessions must not call the Bot bridge")

    monkeypatch.setattr(navigation, "require_canonical_admin", unexpected_canonical_check)
    account = {"id": "support-operator", "role": "support_operator"}
    with _client_for(account) as client:
        response = client.get("/api/v1/admin/navigation")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "read_only"
    assert body["data"]["access"] == {
        "canonical_admin": False,
        "web_support": True,
        "web_support_scope": "operator",
        "web_local_admin": False,
    }
    assert [group["id"] for group in body["data"]["groups"]] == ["support_operations"]
    assert _module_ids(body) == {"support", "operations", "reliability", "content_handoffs", "operations_desk"}
    operations = next(module for module in body["data"]["groups"][0]["modules"] if module["id"] == "operations")
    assert operations["source"] == "web_native"
    assert operations["availability"] == "web_native"
    assert operations["capability"] == "read_only_operations"
    assert all(module["authority"] == "web_support" for module in body["data"]["groups"][0]["modules"])
    handoffs = next(module for module in body["data"]["groups"][0]["modules"] if module["id"] == "content_handoffs")
    assert handoffs["route"] == "/admin/content-handoffs"
    assert handoffs["capability"] == "internal_handoff_review_with_server_role_check"
    desk = next(module for module in body["data"]["groups"][0]["modules"] if module["id"] == "operations_desk")
    assert desk["route"] == "/admin/work-queue"
    assert desk["availability"] == "web_native"
    assert desk["capability"] == "redacted_cross_queue_read_only_with_server_role_check"


def test_canonical_groups_require_flag_and_live_authority(monkeypatch) -> None:
    account = {"id": "admin", "role": "admin", "canonical_user_id": "canonical-admin"}
    bridge_checks: list[str] = []

    async def canonical_ok(_request):
        bridge_checks.append("checked")
        return account

    # An admin is also a server-side Support manager, so stub that separate
    # role check to keep the canonical grouping assertion focused.
    monkeypatch.setattr(navigation, "require_support_staff", lambda _account: (_ for _ in ()).throw(HTTPException(status_code=403)))
    monkeypatch.setattr(navigation, "require_canonical_admin", canonical_ok)
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
    with _client_for(account) as client:
        response = client.get("/api/v1/admin/navigation")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["access"]["canonical_admin"] is True
    assert body["data"]["access"]["web_support"] is False
    assert body["data"]["access"]["web_local_admin"] is True
    group_ids = {group["id"] for group in body["data"]["groups"]}
    assert {"command_center", "commerce", "delivery_runtime", "content_growth", "governance", "web_private_crm"} <= group_ids
    assert {"payments", "jobs", "audit", "publishing", "partner_crm_manager"} <= _module_ids(body)
    assert bridge_checks == ["checked"]
    canonical_modules = [
        module
        for group in body["data"]["groups"]
        for module in group["modules"]
        if module["authority"] == "canonical_admin"
    ]
    assert canonical_modules
    assert all(module["availability"] in {"canonical_read", "guarded_directory", "web_native"} for module in canonical_modules)
    audit_module = next(module for module in canonical_modules if module["id"] == "audit")
    assert audit_module["source"] == "web_native"
    assert audit_module["capability"] == "redacted_web_audit_read"
    assert all("write" not in module["capability"] for module in canonical_modules)

    # Turning the feature flag off must fail closed before a live bridge call
    # and must remove the canonical map rather than serving it from a cache.
    bridge_checks.clear()
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "false")
    with _client_for(account) as disabled:
        blocked = disabled.get("/api/v1/admin/navigation")
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "guarded"
    assert blocked.json()["data"]["groups"] == []
    assert bridge_checks == []


def test_erp_kill_switch_hides_web_native_staff_navigation_too(monkeypatch) -> None:
    """The admin-directory switch cannot leave staff shortcuts discoverable."""

    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_SUPPORT_DESK_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_AUTOPILOT_ENABLED", "true")

    async def unexpected_canonical_check(_request):
        raise AssertionError("The ERP kill switch must short-circuit the Bot bridge")

    monkeypatch.setattr(navigation, "require_canonical_admin", unexpected_canonical_check)
    account = {"id": "support-operator", "role": "support_operator"}
    with _client_for(account) as client:
        response = client.get("/api/v1/admin/navigation")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "guarded"
    assert body["data"]["groups"] == []
    # This remains a server-derived access fact, not a browser role claim; the
    # kill switch only removes ERP navigation discovery.
    assert body["data"]["access"]["web_support"] is True
    assert body["data"]["access"]["web_support_scope"] == "operator"


def test_local_web_admin_crm_directory_stays_distinct_from_canonical_admin(monkeypatch) -> None:
    """A failed Bot check may not erase or upgrade the local redacted CRM scope."""

    account = {"id": "web-admin", "role": "admin", "canonical_user_id": "stale-or-absent"}

    async def canonical_denied(_request):
        raise HTTPException(status_code=403, detail="canonical role unavailable")

    monkeypatch.setattr(navigation, "require_canonical_admin", canonical_denied)
    monkeypatch.setattr(navigation, "require_support_staff", lambda _account: (_ for _ in ()).throw(HTTPException(status_code=403)))
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PARTNER_CRM_ENABLED", "true")
    with _client_for(account) as client:
        response = client.get("/api/v1/admin/navigation")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "read_only"
    assert body["data"]["access"] == {
        "canonical_admin": False,
        "web_support": False,
        "web_support_scope": "none",
        "web_local_admin": True,
    }
    groups = {group["id"]: group for group in body["data"]["groups"]}
    # A stale canonical role must not erase local Web-native governance.  It
    # may expose only Web-local, redacted modules and never a Bot authority.
    assert set(groups) == {"web_private_crm", "web_governance_documents"}
    assert _module_ids(body) == {"partner_crm_manager", "governance_documents"}
    assert all(
        module["authority"] == "web_local_admin"
        for group in groups.values()
        for module in group["modules"]
    )
    module = groups["web_private_crm"]["modules"][0]
    assert module["authority"] == "web_local_admin"
    assert module["availability"] == "web_native"
    assert module["capability"] == "redacted_cross_account_pipeline_read_only"
    governance = groups["web_governance_documents"]["modules"][0]
    assert governance["authority"] == "web_local_admin"
    assert governance["capability"] == "internal_document_lifecycle_review_version_audit"
