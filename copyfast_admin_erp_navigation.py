"""Server-authorized navigation metadata for the Web Admin ERP.

This is deliberately a *directory*, not a second Admin API.  It returns no
customer records, operational counters, bridge responses, configuration or
secrets.  Its only job is to let the Portal render the portions of the Admin
ERP that the signed Web account is currently allowed to discover.

There are three authority domains:

* canonical Admin ERP pages remain available only after the Bot authority
  confirms a live admin role; and
* Support Desk, Operations and Reliability are Web-native staff surfaces
  whose role is checked from the server-side signed Web account store.
* The redacted Partner CRM manager directory, Governance Documents Center and
  Internal Document Archive are Web-native surfaces for a locally provisioned
  Web admin. They are deliberately not presented as canonical Bot Admin
  capabilities.

Keeping those domains separate prevents a browser role, an email allow-list,
or a stale cached Admin role from turning into permission to navigate the
canonical surface.  The endpoint does not invoke the Bot bridge for a
non-admin account, and it never claims that a read route can perform a write.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from copyfast_auth import envelope, require_account, require_canonical_admin
from copyfast_db import autopilot_enabled, reliability_followup_enabled, support_desk_enabled
from copyfast_support import require_support_staff


router = APIRouter(prefix="/api/v1/admin", tags=["COPYFAST Admin ERP Navigation"])


_MODULE_DESCRIPTIONS = {
    "overview": "Tổng quan chỉ đọc từ nguồn canonical đã redaction.",
    "users": "Tìm và xem người dùng theo read model canonical.",
    "tickets": "Ticket canonical, tách biệt với Web Support Desk.",
    "wallet": "Read model Ví & Xu; Web không là ledger writer.",
    "payments": "Payment read model; không tạo webhook hoặc đối soát thủ công.",
    "topups": "Trạng thái nạp canonical; không nhận bill, QR hay TXID ở Web.",
    "revenue": "Báo cáo doanh thu theo adapter canonical.",
    "refunds": "Xem refund; quyết định write cần policy canonical riêng.",
    "pricing": "Giá và gói theo cấu hình canonical đang được công bố.",
    "packages": "Package read model có role check riêng.",
    "promos": "Danh mục khuyến mãi có guard và audit riêng.",
    "jobs": "Job read model, status và output vẫn cần ownership/delivery check.",
    "failed_jobs": "Danh sách job lỗi chỉ đọc; retry không được suy đoán.",
    "providers": "Provider health/cost đã redaction, không có credential hoặc control trực tiếp.",
    "provider_cost": "Chi phí provider từ adapter canonical nếu đã công bố.",
    "workers": "Worker/runtime metadata đã redaction.",
    "features": "Readiness theo feature; browser không bật provider.",
    "freezes": "Maintenance state; write phải qua confirmation và canonical policy.",
    "runtime": "Runtime read model, không có deploy hay repair executor.",
    "leads": "Lead read model sau role check.",
    "audit": "Audit canonical có redaction và access check riêng.",
    "reports": "Báo cáo/export chỉ khi adapter được công bố.",
    "system": "System read model, không lộ secret hoặc deployment control.",
    "backups": "Backup metadata chỉ đọc, không có restore action trong release này.",
    "security_posture": "Security posture Web-native đã redaction; chỉ aggregate Web-owned, không có session, secret hay control từ browser.",
    "access_posture": "Access posture Web-native chỉ đọc; không có danh tính, role grant/revoke hay thay đổi quyền.",
    "operations_desk": "Bàn điều phối chỉ đọc, tổng hợp metadata Web-native đã redaction; không có Bot, provider, payment, wallet, job hoặc delivery action.",
    "support": "Case queue Web-native; không thay đổi Bot, Xu, PayOS hay delivery.",
    "operations": "Operations metadata và recorded approvals, không có external executor.",
    "reliability": "Reliability follow-up metadata, không tự sửa code hay deploy.",
    "content_handoffs": "Hàng review bàn giao nội bộ Web-native; không có publish, delivery, provider, Xu hay PayOS.",
    "partner_crm_manager": "Directory CRM Web-native đã redaction, chỉ đọc; không có cross-account write hay dữ liệu liên hệ.",
    "governance_documents": "Kho tài liệu vận hành nội bộ Web-native có review/version/audit; không đọc tài liệu, file hay authority Telegram Bot.",
    "internal_document_archive": "Kho hồ sơ Web-native local-admin có blob private, phiên bản bất biến, metadata/audit và download kiểm tra integrity; tách khỏi Bot, Asset Vault khách hàng và Governance Documents.",
}

_GROUP_DESCRIPTIONS = {
    "command_center": "Overview, user và canonical ticket read models.",
    "commerce": "Finance read models; wallet/PayOS authority vẫn ở canonical core.",
    "delivery_runtime": "Jobs, readiness và runtime metadata; không có provider control trực tiếp.",
    "content_growth": "Điều hướng các center content/growth; directory vẫn guarded cho đến khi có adapter riêng.",
    "governance": "Audit, reports và system read models canonical có redaction/authority riêng.",
    "support_operations": "Web-native CSKH và Operations metadata, không có financial/provider executor.",
    "web_private_crm": "Giám sát CRM Web-native đã redaction; tách biệt với canonical Bot Admin và financial authority.",
    "web_governance_documents": "Kho tài liệu Governance Web-native, có lifecycle nội bộ nhưng không phải tư vấn pháp lý, file export hay Bot authority.",
    "web_internal_document_archive": "Kho hồ sơ nội bộ Web-native local-admin có file private và version bất biến; không phải Bot archive, Asset Vault khách hàng, ledger, PayOS hay provider action.",
    "web_security_access_posture": "Security và Access posture Web-native, chỉ đọc aggregate đã redaction; không gọi Bot/Core Bridge hoặc thực hiện session, MFA hay quyền control.",
}


def _enabled(name: str, *, default: bool) -> bool:
    """Read a boolean feature flag without importing the bridge API module."""
    return os.environ.get(name, str(default).lower()).strip().lower() in {"1", "true", "yes", "on"}


def admin_erp_enabled() -> bool:
    """Whether canonical Admin ERP navigation may be exposed at all."""
    return _enabled("WEBAPP_ADMIN_ERP_ENABLED", default=True)


def _server_role(account: dict[str, Any]) -> str:
    """Normalize the role loaded by ``require_account`` from signed storage.

    This helper must never be called with browser-provided form data.  The
    endpoint receives its account only from ``require_account``.
    """
    return str(account.get("role") or "").strip().lower()


def _module(
    module_id: str,
    title: str,
    route: str,
    *,
    authority: str,
    source: str,
    availability: str,
    capability: str,
) -> dict[str, str]:
    """Return small, presentation-safe navigation metadata.

    Route availability is intentionally descriptive rather than a promise of
    a completed provider, payment, job or ledger action.  Canonical pages are
    read through their existing bridge route and can still return a guarded
    envelope when the canonical adapter is not ready.
    """
    return {
        "id": module_id,
        "title": title,
        "route": route,
        "authority": authority,
        "source": source,
        "availability": availability,
        "capability": capability,
        "description": _MODULE_DESCRIPTIONS.get(module_id, "Module có authority do máy chủ kiểm tra riêng."),
    }


def _group(
    group_id: str,
    title: str,
    *,
    authority: str,
    modules: Iterable[dict[str, str]],
) -> dict[str, Any]:
    return {
        "id": group_id,
        "title": title,
        "description": _GROUP_DESCRIPTIONS.get(group_id, "Nhóm nghiệp vụ được máy chủ cấp theo authority hiện tại."),
        "authority": authority,
        "modules": list(modules),
    }


def _canonical_module(module_id: str, title: str, route: str, *, capability: str = "canonical_read") -> dict[str, str]:
    return _module(
        module_id,
        title,
        route,
        authority="canonical_admin",
        source="core_bridge",
        availability="canonical_read",
        capability=capability,
    )


def _directory_module(module_id: str, title: str, route: str) -> dict[str, str]:
    """An existing Portal directory whose adapter remains intentionally guarded.

    Campaigns, publishing, growth and trend centers have real Portal routes,
    but their current adapters are explicitly directory/read-only shells.  A
    different label from ``canonical_read`` prevents navigation metadata from
    presenting those pages as a working provider, publishing or payout API.
    """
    return _module(
        module_id,
        title,
        route,
        authority="canonical_admin",
        source="portal_directory",
        availability="guarded_directory",
        capability="navigation_only",
    )


def _web_admin_read_module(module_id: str, title: str, route: str, *, capability: str) -> dict[str, str]:
    """A canonical-admin-gated read model owned by the standalone Web App."""
    return _module(
        module_id,
        title,
        route,
        authority="canonical_admin",
        source="web_native",
        availability="web_native",
        capability=capability,
    )


def canonical_groups() -> list[dict[str, Any]]:
    """Return canonical-only groups for a *live-verified* Bot admin.

    Every route below exists in the Portal registry.  This map contains no
    write route: retry/refund/freeze remain separately CSRF-protected and
    disabled unless their own reviewed canonical write adapters are enabled.
    """
    return [
        _group(
            "command_center",
            "Command Center",
            authority="canonical_admin",
            modules=[
                _canonical_module("overview", "Tổng quan ERP", "/admin"),
                _canonical_module("users", "Người dùng", "/admin/users"),
                _canonical_module("tickets", "Tickets canonical", "/admin/tickets"),
            ],
        ),
        _group(
            "commerce",
            "Commerce & Finance",
            authority="canonical_admin",
            modules=[
                _canonical_module("wallet", "Ví & Xu", "/admin/wallet"),
                _canonical_module("payments", "Thanh toán", "/admin/payments"),
                _canonical_module("topups", "Nạp Xu", "/admin/topups"),
                _canonical_module("revenue", "Doanh thu", "/admin/revenue"),
                _canonical_module("refunds", "Hoàn tiền", "/admin/refunds"),
                _canonical_module("pricing", "Giá & gói", "/admin/pricing"),
                _canonical_module("packages", "Packages", "/admin/packages"),
                _canonical_module("promos", "Khuyến mãi", "/admin/promos"),
                _directory_module("finance", "Finance & Revenue", "/admin/finance"),
            ],
        ),
        _group(
            "delivery_runtime",
            "Delivery & Runtime",
            authority="canonical_admin",
            modules=[
                _canonical_module("jobs", "Jobs", "/admin/jobs"),
                _canonical_module("failed_jobs", "Jobs thất bại", "/admin/jobs/failed"),
                _canonical_module("providers", "Providers & chi phí", "/admin/providers"),
                _canonical_module("provider_cost", "Chi phí provider", "/admin/provider-cost"),
                _canonical_module("workers", "Workers", "/admin/workers"),
                _canonical_module("features", "Feature readiness", "/admin/features"),
                _canonical_module("freezes", "Bảo trì & freeze", "/admin/freezes"),
                _canonical_module("runtime", "Runtime", "/admin/runtime"),
            ],
        ),
        _group(
            "content_growth",
            "Content, Growth & Channels",
            authority="canonical_admin",
            modules=[
                _directory_module("campaigns", "Campaign Center", "/admin/campaigns"),
                _directory_module("calendar", "Content Calendar", "/admin/calendar"),
                _directory_module("approvals", "Approval Queue", "/admin/approvals"),
                _directory_module("publishing", "Publishing & Channels", "/admin/publishing"),
                _directory_module("analytics", "Analytics", "/admin/analytics"),
                _canonical_module("leads", "Leads", "/admin/leads"),
                _directory_module("growth", "Growth & Affiliate", "/admin/growth"),
                _directory_module("trends", "Trends & Reference", "/admin/trends"),
            ],
        ),
        _group(
            "governance",
            "Governance & Security",
            authority="canonical_admin",
            modules=[
                _web_admin_read_module("audit", "Audit Explorer Web-native", "/admin/audit", capability="redacted_web_audit_read"),
                _canonical_module("reports", "Báo cáo", "/admin/reports"),
                _canonical_module("system", "Hệ thống", "/admin/system"),
                _canonical_module("backups", "Sao lưu", "/admin/backups"),
            ],
        ),
    ]


def support_groups(staff_role: str) -> list[dict[str, Any]]:
    """Return only Web-native staff surfaces.

    The feature states are derived server-side from the same feature flags the
    real endpoints use.  A disabled surface stays visible as guarded metadata
    for an already-authorized operator, but it is not presented as a working
    automation or external delivery capability.
    """
    support_state = "web_native" if support_desk_enabled() else "guarded"
    operations_state = "web_native" if autopilot_enabled() else "guarded"
    reliability_state = (
        "web_native" if autopilot_enabled() and reliability_followup_enabled() else "guarded"
    )
    content_handoff_state = "web_native" if _enabled("WEBAPP_CONTENT_HANDOFF_ENABLED", default=True) else "guarded"
    # The Desk is a separate, read-only aggregation of the existing
    # Web-native queues.  It must follow the ERP directory kill switch rather
    # than imply that the underlying source service is healthy or writable.
    operations_desk_state = "web_native" if _enabled("WEBAPP_ADMIN_ERP_ENABLED", default=True) else "guarded"
    return [
        _group(
            "support_operations",
            "Customer Care & Operations",
            authority="web_support",
            modules=[
                _module(
                    "support",
                    "Web Support Desk",
                    "/admin/support",
                    authority="web_support",
                    source="web_native",
                    availability=support_state,
                    capability="case_triage_and_confirmed_case_updates",
                ),
                _module(
                    "operations",
                    "Operations Autopilot",
                    "/admin/operations",
                    authority="web_support",
                    source="web_native",
                    availability=operations_state,
                    capability=(
                        "read_only_operations" if staff_role == "operator"
                        else "recorded_approval_decisions_only"
                    ),
                ),
                _module(
                    "reliability",
                    "Reliability Follow-up",
                    "/admin/reliability",
                    authority="web_support",
                    source="web_native",
                    availability=reliability_state,
                    capability="local_followup_metadata_lifecycle",
                ),
                _module(
                    "content_handoffs",
                    "Content Handoff Queue",
                    "/admin/content-handoffs",
                    authority="web_support",
                    source="web_native",
                    availability=content_handoff_state,
                    capability="internal_handoff_review_with_server_role_check",
                ),
                _module(
                    "operations_desk",
                    "Operations Desk",
                    "/admin/work-queue",
                    authority="web_support",
                    source="web_native",
                    availability=operations_desk_state,
                    capability="redacted_cross_queue_read_only_with_server_role_check",
                ),
            ],
        )
    ]


def web_local_admin_groups() -> list[dict[str, Any]]:
    """Return standalone Web admin surfaces that are not Bot-canonical.

    ``/admin/crm/leads`` independently uses ``require_admin`` and returns
    only redacted cross-account pipeline metadata. ``/admin/automation`` is a
    Web-owned read-only scheduler receipt monitor. ``/admin/security`` and
    ``/admin/access`` share an identifier-free security/access posture read
    model. ``/admin/governance`` and ``/admin/internal-documents`` are
    separately flagged Web-owned internal document surfaces. Keeping these in
    distinct authority groups prevents a signed Web administrator from being
    visually or semantically promoted into a Bot/canonical administrator.
    """

    crm_state = "web_native" if _enabled("WEBAPP_PARTNER_CRM_ENABLED", default=True) else "guarded"
    governance_state = (
        "web_native"
        if _enabled("WEBAPP_ADMIN_ERP_ENABLED", default=True)
        and _enabled("WEBAPP_GOVERNANCE_DOCUMENTS_ENABLED", default=False)
        else "guarded"
    )
    archive_state = (
        "web_native"
        if _enabled("WEBAPP_ADMIN_ERP_ENABLED", default=True)
        and _enabled("WEBAPP_ADMIN_DOCUMENT_ARCHIVE_ENABLED", default=False)
        else "guarded"
    )
    automation_state = "web_native" if _enabled("WEBAPP_ADMIN_ERP_ENABLED", default=True) else "guarded"
    security_access_state = "web_native" if _enabled("WEBAPP_ADMIN_ERP_ENABLED", default=True) else "guarded"
    return [
        _group(
            "web_private_crm",
            "Web CRM Governance",
            authority="web_local_admin",
            modules=[
                _module(
                    "partner_crm_manager",
                    "CRM Manager Directory",
                    "/admin/crm/leads",
                    authority="web_local_admin",
                    source="web_native",
                    availability=crm_state,
                    capability="redacted_cross_account_pipeline_read_only",
                ),
            ],
        ),
        _group(
            "web_governance_documents",
            "Governance Documents",
            authority="web_local_admin",
            modules=[
                _module(
                    "governance_documents",
                    "Kho tài liệu nội bộ",
                    "/admin/governance",
                    authority="web_local_admin",
                    source="web_native",
                    availability=governance_state,
                    capability="internal_document_lifecycle_review_version_audit",
                ),
            ],
        ),
        _group(
            "web_internal_document_archive",
            "Internal Document Archive",
            authority="web_local_admin",
            modules=[
                _module(
                    "internal_document_archive",
                    "Kho hồ sơ nội bộ",
                    "/admin/internal-documents",
                    authority="web_local_admin",
                    source="web_native",
                    availability=archive_state,
                    capability="owner_scoped_immutable_private_document_versions",
                ),
            ],
        ),
        _group(
            "web_automation_monitor",
            "Automation Monitor",
            authority="web_local_admin",
            modules=[
                _module(
                    "automation_monitor",
                    "Automation Monitor",
                    "/admin/automation",
                    authority="web_local_admin",
                    source="web_native",
                    availability=automation_state,
                    capability="redacted_scheduler_receipt_read_only",
                ),
            ],
        ),
        _group(
            "web_security_access_posture",
            "Security & Access Posture",
            authority="web_local_admin",
            modules=[
                _module(
                    "security_posture",
                    "Security Posture",
                    "/admin/security",
                    authority="web_local_admin",
                    source="web_native",
                    availability=security_access_state,
                    capability="redacted_web_security_posture_read_only",
                ),
                _module(
                    "access_posture",
                    "Access Posture",
                    "/admin/access",
                    authority="web_local_admin",
                    source="web_native",
                    availability=security_access_state,
                    capability="redacted_web_access_posture_read_only",
                ),
            ],
        ),
    ]


def _support_role(account: dict[str, Any]) -> str | None:
    """Check the protected Web staff role without touching the Bot bridge."""
    try:
        return require_support_staff(account)
    except HTTPException as exc:
        # The Support helper only denies a non-staff account with 403.  Do not
        # convert an unexpected future failure into a permissive navigation
        # response.
        if exc.status_code in {401, 403}:
            return None
        raise


async def _has_live_canonical_admin(request: Request, account: dict[str, Any]) -> bool:
    """Fail closed if the Bot cannot confirm an existing Web admin session."""
    if not admin_erp_enabled() or _server_role(account) != "admin":
        return False
    try:
        await require_canonical_admin(request)
    except HTTPException:
        # A cached Web ``admin`` role is only a display hint.  Do not return a
        # canonical navigation map until the Bot authority confirms it again.
        return False
    return True


@router.get("/navigation")
async def navigation(request: Request, account: dict[str, Any] = Depends(require_account)) -> dict[str, Any]:
    """Return the Admin ERP directory authorized for this signed Web account.

    This endpoint intentionally returns an empty, guarded directory for an
    ordinary signed customer.  That keeps global Portal bootstrap stable while
    ensuring admin routes remain undiscoverable and independently guarded by
    their own server-side endpoint/page checks.
    """
    erp_enabled = admin_erp_enabled()
    staff_role = _support_role(account)
    live_canonical_admin = await _has_live_canonical_admin(request, account)
    # The umbrella ERP flag is a deliberate kill switch for *all* Admin
    # navigation, including this independent Web-native directory.  The route
    # itself still owns its own ``require_admin`` check, but a disabled ERP
    # workspace must not continue advertising staff surfaces from a cache.
    web_local_admin = erp_enabled and _server_role(account) == "admin"

    groups: list[dict[str, Any]] = []
    # WEBAPP_ADMIN_ERP_ENABLED is an umbrella discovery kill switch.  Web
    # Support remains a separately protected service at its own exact routes,
    # but its Admin ERP shortcuts must not survive after the administrator has
    # disabled the ERP directory.  This also prevents a stale staff shell from
    # treating the feature flag as canonical-only.
    if erp_enabled and staff_role:
        groups.extend(support_groups(staff_role))
    if web_local_admin:
        groups.extend(web_local_admin_groups())
    if live_canonical_admin:
        groups.extend(canonical_groups())

    data = {
        "groups": groups,
        "access": {
            "canonical_admin": live_canonical_admin,
            "web_support": bool(staff_role),
            # This is the server-derived operational scope of the current
            # account, not a browser-provided authorization claim.
            "web_support_scope": staff_role or "none",
            # This is a local signed-account role used only for the explicitly
            # redacted, read-only Web CRM directory.  It never asserts a live
            # Bot admin role and must not grant canonical navigation.
            "web_local_admin": web_local_admin,
        },
        "boundaries": [
            "Navigation metadata contains no records, counts, secrets, bridge payloads or provider configuration.",
            "Canonical modules remain read-only navigation entries; their own endpoint re-checks live Bot admin authority.",
            "Web Support, Operations and Reliability do not mutate Bot identity, PayOS, Xu ledger, provider jobs, deployments or external delivery.",
            "Web CRM Governance is a local, redacted read-only directory; it is not a canonical Bot Admin surface and cannot write cross-account data.",
            "Every write remains behind its own server-side permission, CSRF, confirmation, idempotency and audit contract.",
        ],
    }
    if groups:
        return envelope(
            True,
            "Đã nạp điều hướng Admin ERP theo quyền server-side hiện tại.",
            data=data,
            status_name="read_only",
        )
    return envelope(
        True,
        "Tài khoản Web này chưa được cấp không gian Admin ERP hoặc Support Desk.",
        data=data,
        status_name="guarded",
    )
