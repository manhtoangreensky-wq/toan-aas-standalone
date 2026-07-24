"""Focused safety and UX contracts for the app-first Delivery Center."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "DELIVERY_CENTER_RECORD_IDENTITY_CONTRACT.md").read_text(encoding="utf-8")


def _section(start: str, end: str) -> str:
    offset = PORTAL.index(start)
    return PORTAL[offset:PORTAL.index(end, offset + len(start))]


def test_asset_vault_namespace_is_never_presented_as_a_job_or_delivery() -> None:
    identity = _section("function assetRecordIdentity(item)", "function assetRecordBadge(item)")
    link = _section("function assetJobLink(item)", "function assetDeliveryState(item, surface)")
    delivery = _section("function assetDeliveryState(item, surface)", "function exactJobAssets(job, source)")

    assert 'assetId.startsWith("wna:v1:")' in identity
    assert 'kind: "web_vault"' in identity
    assert 'label: "Tệp riêng Web"' in identity
    assert 'if (assetRecordIdentity(item).kind === "web_vault") return "/asset-vault";' in PORTAL
    assert 'if (identity.kind === "web_vault") {' in link
    assert 'href="/asset-vault"' in link
    assert 'href="/jobs/${encodeURIComponent(assetId)}"' in link
    assert 'data-delivery="vault">Tệp riêng Web · không phải output' in delivery
    assert 'if (identity.kind === "web_vault") {' in delivery


def test_job_output_and_download_guards_remain_exact_and_owner_scoped() -> None:
    output_assets = _section("function exactJobAssets(job, source)", "function canonicalXu(value)")
    lifecycle = _section("function renderJobDeliveryLifecycle(job, context, source)", "function renderJobRecoverySupport(job, context, source)")

    assert 'String(item.id || "").trim() === jobId' in output_assets
    assert 'item && item.download_ready === true && item.delivery_ready === true' in PORTAL
    assert 'href="${safeText(deliveryPath)}" rel="noreferrer"' in PORTAL
    assert "Không có mốc lịch sử hoặc file nào được suy diễn." in lifecycle
    assert "Chưa có asset trùng ID job" in PORTAL
    assert 'href="#job-recovery-support"' in PORTAL
    assert 'id="job-recovery-support"' in PORTAL


def test_delivery_center_keeps_semantic_desktop_table_and_mobile_cards() -> None:
    jobs = _section("function renderJobs(page, context)", "function renderJobDetail(page, context)")
    assets = _section("function renderAssets(page, context)", "function validVaultAssetId(value)")

    assert 'renderDeliveryRecords("jobs"' in jobs
    assert 'renderDeliveryRecords("assets"' in assets
    assert 'renderJobDeliverySummary(allJobs)' in jobs
    assert 'renderAssetDeliverySummary(allAssets)' in assets
    assert 'role="status" aria-live="polite"' in jobs
    assert 'role="status" aria-live="polite"' in assets
    assert ".portal-delivery-desktop-records" in CSS
    assert ".portal-delivery-mobile-records" in CSS
    assert "@media (max-width: 700px)" in CSS
    assert ".portal-delivery-desktop-records { display: none; }" in CSS
    assert ".portal-delivery-mobile-records { display: grid; gap: 10px; }" in CSS


def test_vault_sources_have_their_own_filter_and_cannot_fall_into_waiting_delivery() -> None:
    assets = _section("function renderAssets(page, context)", "function validVaultAssetId(value)")

    assert '["web_vault", "Tệp riêng Web"]' in PORTAL
    assert 'if (identity.kind === "web_vault") return value === "web_vault";' in assets
    assert 'if (value === "web_vault") return false;' in assets
    assert '"failed", "web_vault"' in INTEGRATION
    assert "Tệp Web riêng chỉ xuất hiện sau khi bạn lưu vào Asset Vault" in assets


def test_filters_refresh_and_motion_follow_accessible_app_controls() -> None:
    assert "function filterBar(filters, selected, action, attribute, label, counts)" in PORTAL
    assert 'class="portal-filter-result" role="status" aria-live="polite"' in PORTAL
    assert "function setDeliveryReadStatus(route, message)" in INTEGRATION
    assert "function isSafeDeliveryReadRecord(item)" in INTEGRATION
    assert "function deliveryReadItemsOrThrow(result, label)" in INTEGRATION
    assert 'items.length > 100 || !items.every(isSafeDeliveryReadRecord)' in INTEGRATION
    assert '/^[A-Za-z0-9._:-]{1,160}$/.test(id)' in INTEGRATION
    assert '/^[A-Za-z0-9._:-]{1,64}$/.test(status)' in INTEGRATION
    assert 'setActionBusy(action, route, true);' in INTEGRATION
    assert 'setDeliveryReadStatus("/jobs", "Đang kiểm tra job canonical thuộc signed session…");' in INTEGRATION
    assert 'setDeliveryReadStatus("/assets", "Đang kiểm tra metadata và delivery thuộc signed session…");' in INTEGRATION
    assert 'deliveryReadItemsOrThrow(result, "Job Center")' in INTEGRATION
    assert 'deliveryReadItemsOrThrow(result, "Assets")' in INTEGRATION
    assert ".portal-filter-button {" in CSS
    assert "min-height: 40px;" in CSS
    assert ".portal-filter-button { min-height: 44px;" in CSS
    assert "@media (prefers-reduced-motion: reduce)" in CSS


def test_documented_boundary_excludes_new_mutations_or_private_cache() -> None:
    assert "presentation-only" in CONTRACT
    assert "wna:v1:*" in CONTRACT
    assert "download_ready === true" in CONTRACT
    assert "delivery_ready === true" in CONTRACT
    assert "No Browser/Portal retry, cancel, refund, charge, provider call or payment" in CONTRACT
    assert "No PWA/private-cache change" in CONTRACT
