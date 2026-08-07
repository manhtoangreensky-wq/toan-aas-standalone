"""Presentation-only locale contracts for the signed Web Data Control Center.

The Data Control Center may translate only reviewed fixed Portal copy.  It
must not reinterpret a server projection, a request identifier/revision,
timestamp, policy/version/acknowledgement literal, or server result message.
"""

from pathlib import Path
import re

from copyfast_pages import render_portal


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")


DATA_CONTROLS_RENDERER_KEYS = (
    "guardedDisabledBody",
    "guardedSessionBody",
    "guardedProjectionBody",
    "guardedTitle",
    "guardedScope",
    "guardedNoAutomatic",
    "guardedNoBot",
    "accountLink",
    "botBoundaryTitle",
    "botBoundaryBody",
    "loadingTitle",
    "loadingBody",
    "categoryAccountProfileLabel",
    "categoryAccountProfileDetail",
    "categoryMemoryCenterLabel",
    "categoryMemoryCenterDetail",
    "categoryPromptLibraryLabel",
    "categoryPromptLibraryDetail",
    "categoryWorkboardLabel",
    "categoryWorkboardDetail",
    "categoryFallbackLabel",
    "categoryFallbackDetail",
    "erasureAvailable",
    "exportOnly",
    "recordSummary",
    "emptyScopeTitle",
    "emptyScopeBody",
    "requestAwaitingReview",
    "requestIdentityVerificationPending",
    "requestCancelled",
    "requestClosed",
    "requestGuarded",
    "cancelConfirm",
    "cancelAction",
    "cancelUnavailableCapability",
    "cancelUnavailableState",
    "requestSummary",
    "requestScopeSummary",
    "emptyRequestsTitle",
    "emptyRequestsBody",
    "exportDisabledTitle",
    "requestDisabledTitle",
    "heroEyebrow",
    "heroTitle",
    "heroBody",
    "heroAuthoringCount",
    "heroPendingCount",
    "heroExportBounded",
    "scopeTitle",
    "scopeBody",
    "exportTitle",
    "exportBody",
    "exportBoundary",
    "exportConfirm",
    "exportAction",
    "refreshAction",
    "erasureTitle",
    "erasureBody",
    "erasureConfirm",
    "erasureAcknowledgement",
    "erasureNote",
    "erasureAction",
    "systemsTitle",
    "systemsBody",
    "botStepTitle",
    "botStepBody",
    "webStepTitle",
    "webStepBody",
    "noHiddenStepTitle",
    "noHiddenStepBody",
    "historyTitle",
    "historyBody",
    "historyLimit",
)

DATA_CONTROLS_ACTION_KEYS = (
    "actionRefreshRouteError",
    "actionRefreshCapabilityError",
    "actionRefreshSuccess",
    "actionExportRouteError",
    "actionExportCapabilityError",
    "actionExportSuccess",
    "actionRequestRouteError",
    "actionRequestCapabilityError",
    "actionRequestConfirmationError",
    "actionRequestPending",
    "actionRequestProjectionError",
    "actionRequestSuccess",
    "actionCancelRouteError",
    "actionCancelCapabilityError",
    "actionCancelInvalidError",
    "actionCancelPending",
    "actionCancelProjectionError",
    "actionCancelSuccess",
)

DATA_CONTROLS_INTEGRATION_FALLBACK_KEYS = (
    "actionReadStateError",
    "actionProjectionInvalidError",
    "actionBoundaryError",
    "actionExportServerError",
    "actionExportResponseError",
    "actionExportSizeError",
)


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    return source[begin : source.index(end, begin + len(start))]


def test_data_controls_uses_a_reviewed_vi_en_zh_fixed_copy_catalogue() -> None:
    view = _between(PORTAL, "function renderAccountDataControls", "const GOVERNANCE_DOCUMENT_LABELS")
    state_labels = _between(PORTAL, "function dataControlsRequestStateLabel", "function dataControlsRequestBadgeState")

    assert "function dataControlsText(key, fallback, params)" in PORTAL
    assert 'const copy = (key, fallback, params) => dataControlsText(key, fallback, params);' in view
    rendered_keys = set(re.findall(r'\bcopy\("([^"]+)"', view)) | set(
        re.findall(r'\bdataControlsText\("([^"]+)"', state_labels)
    )
    for key in DATA_CONTROLS_RENDERER_KEYS:
        assert key in rendered_keys or f'"{key}"' in PORTAL
    for key in rendered_keys:
        assert I18N.count(f'"accountCenter.dataControls.{key}"') == 3

    # Dynamic data remains a server projection and is escaped at the render
    # boundary. Locale lookup may only receive reviewed fixed-key material.
    for requirement in (
        "String(item.recordCount)",
        "request.requestedAt",
        "request.updatedAt",
        "String(request.revision)",
        "safeText(request.id)",
    ):
        assert requirement in view
    assert 'safeText(copy("recordSummary"' in view
    assert 'safeText(copy("requestSummary"' in view
    assert "localStorage." not in view
    assert "sessionStorage." not in view


def test_data_controls_actions_localize_browser_messages_without_changing_requests() -> None:
    actions = _between(
        INTEGRATION,
        'if (action === "data-controls-refresh")',
        'if (action === "account-security-refresh")',
    )

    assert "function dataControlsText(key, fallback, params)" in INTEGRATION
    action_keys = set(re.findall(r'\bdataControlsText\("([^"]+)"', actions))
    for key in DATA_CONTROLS_ACTION_KEYS:
        assert key in action_keys
        assert I18N.count(f'"accountCenter.dataControls.{key}"') == 3

    integration_fallbacks = _between(
        INTEGRATION,
        "async function hydrateDataControls",
        "async function hydrateWorkspaceDrafts",
    )
    fallback_keys = set(re.findall(r'\bdataControlsText\("([^"]+)"', integration_fallbacks))
    for key in DATA_CONTROLS_INTEGRATION_FALLBACK_KEYS:
        assert key in fallback_keys
        assert I18N.count(f'"accountCenter.dataControls.{key}"') == 3

    for request in (
        'fetch(`${API}/account/data-controls/export.json`',
        'api("/account/data-controls/erasure-requests"',
        'api(`/account/data-controls/erasure-requests/${encodeURIComponent(requestId)}/cancel`',
        'acknowledgement: DATA_CONTROLS_ERASURE_ACKNOWLEDGEMENT',
        'acknowledgement: DATA_CONTROLS_CANCEL_ACKNOWLEDGEMENT',
        "idempotency_key: submission.key",
        "expected_revision: expectedRevision",
        "await hydrateDataControls(0)",
    ):
        assert request in actions or request in INTEGRATION
    assert "result.message || dataControlsText" in actions
    assert '"/data_delete"' not in actions


def test_data_controls_has_localized_document_metadata_and_first_paint_title() -> None:
    title = _between(PORTAL, "function localizedPageTitle", "function documentTitle")
    description = _between(PORTAL, "function localizedPageDescription", "function initials")
    navigation = _between(PORTAL, "const NAVIGATION_I18N_KEYS", "function localizedNavigationLabel")

    for key in ("page.dataControls.title", "page.dataControls.description"):
        assert I18N.count(f'"{key}"') == 3
    assert 'if (path === "/account/data-controls") return uiText("page.dataControls.title", fallback);' in title
    assert 'if (path === "/account/data-controls") return uiText("page.dataControls.description", fallback);' in description
    assert '"Kiểm soát dữ liệu Web": "page.dataControls.title"' in navigation
    assert '"/account/data-controls": {"vi": "Kiểm soát dữ liệu Web · TOAN AAS", "en": "Web data controls · TOAN AAS", "zh": "Web 数据控制 · TOAN AAS"},' in PAGES


def test_data_controls_first_paint_description_is_route_and_locale_specific() -> None:
    expected_descriptions = {
        "vi": "Xuất dữ liệu authoring thuộc Web và tạo yêu cầu review xóa theo phạm vi, không tác động Bot hoặc hệ thống canonical khác.",
        "en": "Export Web-owned authoring data and create scope-bound erasure-review requests without affecting the Bot or another canonical system.",
        "zh": "导出 Web 拥有的创作数据，并创建范围受限的删除审核请求，不影响 Bot 或其他权威系统。",
    }

    assert "_PORTAL_SHELL_DESCRIPTIONS" in PAGES
    assert "def _shell_description_for(path: str, locale: str) -> str:" in PAGES
    assert '"/account/data-controls": {' in PAGES
    assert ".replace(\"__PORTAL_DESCRIPTION__\", html.escape(_shell_description_for(normalized, locale), quote=True))" in PAGES

    for locale, description in expected_descriptions.items():
        assert f'"{locale}": "{description}"' in PAGES
        response = render_portal("/account/data-controls", interface_locale=locale)
        assert response.status_code == 200
        assert f'<meta name="description" content="{description}">'.encode("utf-8") in response.body
