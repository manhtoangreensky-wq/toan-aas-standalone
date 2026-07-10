"""Static contracts for the presentation-only customer portal.

These checks deliberately verify the browser bundle rather than a bot fixture:
the Web App must not turn a reported engine output into a downloadable asset
until the canonical bridge publishes a signed delivery contract.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")


def test_portal_never_offers_download_for_reported_output_metadata() -> None:
    assert "Chờ delivery canonical" in PORTAL
    assert "Engine đã báo output" in PORTAL
    assert "function assetDeliveryState(item)" in PORTAL
    assert "Output hợp lệ · chờ URL ký" in PORTAL
    assert "data-portal-action=\"asset-download\"" not in PORTAL
    assert "window.location.assign(`/assets/" not in PORTAL
    assert "asset-download" not in INTEGRATION
    assert "/api/operator/" not in INTEGRATION


def test_job_polling_uses_only_the_signed_web_api() -> None:
    assert "const JOB_POLL_INTERVAL_MS = 15000;" in INTEGRATION
    assert "const JOB_POLL_MAX_BACKOFF_MS = 60000;" in INTEGRATION
    assert "function scheduleJobPolling" in INTEGRATION
    assert "jobPollFailures += 1;" in INTEGRATION
    assert "retryDelay" in INTEGRATION
    assert 'api("/jobs")' in INTEGRATION
    assert "provider" not in INTEGRATION[INTEGRATION.index("function scheduleJobPolling"):INTEGRATION.index("function featurePageStates")]


def test_dashboard_hydrates_only_canonical_metadata() -> None:
    assert 'path === "/dashboard"' in INTEGRATION
    assert 'api("/wallet")' in INTEGRATION
    assert "Tài sản gần đây" in PORTAL
    assert "Không đồng nghĩa delivery" in PORTAL


def test_portal_uses_canonical_price_tiers_and_real_telegram_link_flow() -> None:
    assert 'optionsFrom: "imageTiers"' in PORTAL
    assert 'optionsFrom: "videoTiers"' in PORTAL
    assert 'optionsFrom: "packages"' in PORTAL
    assert '"start-telegram-link"' in PORTAL
    assert '"start-telegram-link"' in INTEGRATION
    assert 'api("/pricing")' in INTEGRATION
    assert 'api("/packages")' in INTEGRATION
    assert 'api("/auth/telegram/link/status")' in INTEGRATION


def test_feature_flow_keeps_sanitized_form_values_and_staged_upload_ids() -> None:
    assert "const priorInput = priorFlow" in INTEGRATION
    assert "const values = { ...priorInput, ...fields };" in INTEGRATION
    assert "input: featureInput" in INTEGRATION
    assert "const fieldValues = { ...(flow && flow.input" in PORTAL
    assert "transientFormDrafts" in PORTAL
    assert "tệp đã vào staging canonical" in PORTAL


def test_quote_capable_workflows_can_estimate_directly_and_confirm_only_a_fresh_quote() -> None:
    assert 'featurePage("/chat"' in PORTAL
    assert 'action: "feature-estimate"' in PORTAL
    assert 'featurePage("/voice/tts"' in PORTAL
    assert "function flowHasFreshEstimate(flow)" in PORTAL
    assert "flow.estimateFingerprint" in PORTAL
    assert "const estimateAvailable = featurePhase === \"estimate\"" in INTEGRATION
    assert "Thông tin đã thay đổi hoặc chưa có estimate canonical hợp lệ" in INTEGRATION


def test_feature_submissions_are_single_flight_and_reuse_an_idempotency_key_for_a_matching_input() -> None:
    assert "const draftScope = `feature:${route}:${featurePhase}`;" in INTEGRATION
    assert "featureSubmission = acquireSubmission(draftScope, initialFingerprint);" in INTEGRATION
    assert "idempotency_key: featureSubmission.key" in INTEGRATION
    assert "setActionBusy(action, route, true);" in INTEGRATION
    assert "setActionBusy(action, route, false);" in INTEGRATION


def test_workflow_forms_follow_the_supported_bot_contracts_before_staging() -> None:
    assert "videoStoryboard" in PORTAL
    assert 'name: "duration_seconds"' in PORTAL
    assert 'name: "platform"' in PORTAL
    assert 'name: "template"' in PORTAL
    assert 'name: "voice_profile_id"' in PORTAL
    assert "requiredUpload: true" in PORTAL
    assert '"image_to_pdf"' in PORTAL
    assert "LANGUAGE_OPTIONS" in PORTAL
    assert "function validateFeatureIntake(feature, route, fields)" in INTEGRATION
    assert "Voice Clone cần một mẫu audio" in INTEGRATION
    assert "Gộp PDF cần ít nhất hai tệp" in INTEGRATION
    assert "Image-to-Video chỉ nhận JPG, PNG hoặc WebP" in INTEGRATION


def test_keyboard_forms_and_mobile_navigation_are_accessible() -> None:
    assert 'type="submit"' in PORTAL
    assert "form.reportValidity()" in PORTAL
    assert "dispatchAction(event.target, getBootstrap());" in PORTAL
    assert "function focusSnapshot()" in PORTAL
    assert "function restoreFocus(snapshot)" in PORTAL
    assert "sidebar.setAttribute(\"aria-modal\", \"true\")" in PORTAL
    assert "function setWorkspaceInert(opened)" in PORTAL
    assert '"/wallet/topup", "Nạp Xu"' in PORTAL
    assert '"/packages", "Gói dịch vụ"' in PORTAL
    assert "prefers-reduced-motion" in (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")


def test_pending_link_code_hides_duplicate_hero_action_and_requires_confirmation() -> None:
    assert "const linkPending = page.action === \"start-telegram-link\"" in PORTAL
    assert 'data-portal-confirm="Tạo mã mới sẽ hủy mã đang hiển thị.' in PORTAL
    assert "if (confirmation && !window.confirm(confirmation)) return;" in PORTAL


def test_account_uses_read_only_session_data_and_server_side_logout() -> None:
    assert 'layout: "account", fields: [], action: "none"' in PORTAL
    assert "Hồ sơ canonical" in PORTAL
    assert 'data-portal-action="auth-logout"' in PORTAL
    assert '"auth-logout": Boolean(account && me.csrf_token)' in INTEGRATION
    assert 'api("/auth/logout"' in INTEGRATION


def test_initial_hydration_is_deduplicated_and_bfcache_refresh_is_explicit() -> None:
    assert "function startInitialHydration()" in INTEGRATION
    assert "if (!initialHydration) initialHydration = hydrate().catch(() => {});" in INTEGRATION
    assert "if (event.persisted) hydrate().catch(() => {});" in INTEGRATION


def test_login_return_path_is_internal_and_unlinked_accounts_go_to_onboarding() -> None:
    assert "function safeReturnPath(value)" in INTEGRATION
    assert 'value.startsWith("//")' in INTEGRATION
    assert 'window.location.assign(account.canonical_user_id ? (requested || "/dashboard") : "/onboarding");' in INTEGRATION


def test_payment_ui_only_renders_vetted_canonical_checkout_data() -> None:
    assert "function safePayosCheckout(value)" in PORTAL
    assert 'url.hostname === "pay.payos.vn"' in PORTAL
    assert "Yêu cầu thanh toán canonical" in PORTAL
    assert 'data-portal-action="refresh-payment"' in PORTAL
    assert 'api(`/payments/${encodeURIComponent(paymentId)}`)' in INTEGRATION
    assert "paymentFlow" in INTEGRATION


def test_job_and_payment_statuses_are_not_conflated() -> None:
    assert "function paymentStatus(item)" in PORTAL
    assert 'paid: "completed"' in PORTAL
    job_slice = PORTAL[PORTAL.index("function jobStatus(item)"):PORTAL.index("function paymentStatus(item)")]
    assert 'paid: "completed"' not in job_slice
    assert '"cancelled", "Đã hủy"' in PORTAL
    assert '"refunded", "Đã hoàn Xu"' in PORTAL


def test_readiness_maps_all_feature_route_aliases_not_only_catalog_routes() -> None:
    assert "Object.entries(FEATURE_BY_PATH).forEach" in INTEGRATION
    assert 'api("/features/status")' in INTEGRATION
    assert "pageStates: featurePageStates(base().catalog || [], readiness.data || {})" in INTEGRATION
    assert 'path === "/tts" || path.startsWith("/voice")' in INTEGRATION
    assert 'context.pageStates[normalizePath(context.path)]' in PORTAL


def test_client_capabilities_respect_the_copyfast_master_flag() -> None:
    assert "const copyfastEnabled = Boolean(status.flags && status.flags.copyfast_enabled);" in INTEGRATION
    assert "const bridgeAvailable = Boolean(copyfastEnabled" in INTEGRATION
    assert '"refresh-admin": Boolean(status.flags && status.flags.admin_erp_enabled' in INTEGRATION


def test_ticket_and_payment_submissions_are_single_flight_and_idempotent_in_memory() -> None:
    assert "function acquireSubmission(scope, fingerprint)" in INTEGRATION
    assert "const submissions = new Map();" in INTEGRATION
    assert 'acquireSubmission("ticket", `${subject}\\n${detailText}`)' in INTEGRATION
    assert 'acquireSubmission("payment", packageId)' in INTEGRATION
    assert 'window.location.assign("/tickets");' in INTEGRATION


def test_job_asset_and_ticket_views_only_filter_redacted_canonical_metadata() -> None:
    assert "const ASSET_FILTERS" in PORTAL
    assert "const TICKET_FILTERS" in PORTAL
    assert "function jobCost(item)" in PORTAL
    assert "function ticketStatus(item)" in PORTAL
    assert 'data-portal-action="filter-assets"' not in PORTAL  # attributes are generated by filterBar
    assert 'filterBar(ASSET_FILTERS, selected, "filter-assets"' in PORTAL
    assert 'filterBar(TICKET_FILTERS, selected, "filter-tickets"' in PORTAL
    assert 'assetFilter: source.getAttribute("data-asset-filter")' in PORTAL
    assert 'ticketFilter: source.getAttribute("data-ticket-filter")' in PORTAL
    assert 'if (action === "filter-assets")' in INTEGRATION
    assert 'if (action === "filter-tickets")' in INTEGRATION


def test_admin_route_aliases_use_existing_read_only_bridge_modules() -> None:
    assert "const ADMIN_MODULE_ALIASES" in INTEGRATION
    assert 'backup: "backups", export: "reports"' in INTEGRATION
    assert "function adminEndpointForPath(path)" in INTEGRATION
    assert "await api(adminEndpointForPath(path))" in INTEGRATION


def test_registration_copy_does_not_claim_unimplemented_email_verification() -> None:
    assert "email verification được Core Bridge thực thi" not in PORTAL
    assert "xác minh email chưa được bật trong phase này" in PORTAL


def test_feature_planning_state_is_distinguished_from_provider_engine_readiness() -> None:
    assert "const planningAvailable = page.type === \"feature\" && page.action !== \"none\"" in PORTAL
    assert "Planning draft sẵn sàng; engine vẫn được bảo vệ" in PORTAL


def test_support_form_does_not_silently_drop_a_file_attachment() -> None:
    assert 'name: "attachment"' not in PORTAL
    assert "form hiện tại không nhận hoặc bỏ qua file" in PORTAL


def test_admin_surfaces_are_explicitly_read_only_without_a_write_adapter() -> None:
    assert 'action: "none"' in PORTAL
    assert "Chế độ chỉ đọc" in PORTAL
    assert "data-portal-action=\"admin-review\"" not in PORTAL
    assert "admin-retry" not in PORTAL
    assert "admin-refund" not in PORTAL
    assert "admin-freeze" not in PORTAL
    assert "admin-retry" not in INTEGRATION
    assert "admin-refund" not in INTEGRATION
    assert "admin-freeze" not in INTEGRATION
