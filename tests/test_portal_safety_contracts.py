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
    assert "data-portal-action=\"asset-download\"" not in PORTAL
    assert "download_ready" not in PORTAL
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
    assert "renderFields(page.fields, enabled, context, flow && flow.input)" in PORTAL
    assert "tệp đã vào staging canonical" in PORTAL


def test_pending_link_code_hides_duplicate_hero_action_and_requires_confirmation() -> None:
    assert "const linkPending = page.action === \"start-telegram-link\"" in PORTAL
    assert 'data-portal-confirm="Tạo mã mới sẽ hủy mã đang hiển thị.' in PORTAL
    assert "if (confirmation && !window.confirm(confirmation)) return;" in PORTAL


def test_initial_hydration_is_deduplicated_and_bfcache_refresh_is_explicit() -> None:
    assert "function startInitialHydration()" in INTEGRATION
    assert "if (!initialHydration) initialHydration = hydrate().catch(() => {});" in INTEGRATION
    assert "if (event.persisted) hydrate().catch(() => {});" in INTEGRATION


def test_support_form_does_not_silently_drop_a_file_attachment() -> None:
    assert 'name: "attachment"' not in PORTAL
    assert "form hiện tại không nhận hoặc bỏ qua file" in PORTAL


def test_admin_surfaces_are_explicitly_read_only_without_a_write_adapter() -> None:
    assert 'action: "none"' in PORTAL
    assert "Chế độ chỉ đọc" in PORTAL
    assert "data-portal-action=\"admin-review\"" not in PORTAL
