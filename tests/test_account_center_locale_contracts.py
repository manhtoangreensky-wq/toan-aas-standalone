"""Static contracts for reviewed Account Center presentation copy."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")


PROFILE_KEYS = (
    "displayNameLabel",
    "emailLabel",
    "profileDefaultsLabel",
    "signInLabel",
    "telegramLabel",
    "sessionLabel",
    "telegramConnected",
    "telegramUnlinked",
    "sessionValid",
    "sessionPending",
    "emailPassword",
    "providerReady",
    "providerUnavailable",
    "providerLinked",
    "oauthLinkedState",
    "oauthReadyState",
    "oauthUnavailableState",
    "oauthVerified",
    "oauthLink",
    "oauthLinkConfirm",
    "oauthUnavailableHint",
    "oauthNoticeTitle",
    "oauthNoticeLinked",
    "oauthNoticeAlreadyLinked",
    "oauthIncompleteTitle",
    "oauthIncompleteBody",
    "methodsTitle",
    "methodsBody",
    "editorTitle",
    "editorBody",
    "editorAuditNote",
    "editorGuardHint",
    "editorSave",
    "displayNamePlaceholder",
    "displayNameHelp",
    "localeLabel",
    "localeHelp",
    "timezoneLabel",
    "timezoneHelp",
    "botLanguageTitle",
    "botLanguageBody",
    "botModeTitle",
    "botModeBody",
    "botProfileTitle",
    "botProfileBody",
    "botMyDataTitle",
    "botMyDataBody",
    "botDataDeleteTitle",
    "botDataDeleteBody",
    "botCopyCommand",
    "botUnavailableHint",
    "botCompanionTitle",
    "botCompanionBody",
    "botOpenTitle",
    "botOpenBody",
    "botOpenAction",
    "botUnavailableTitle",
    "botUnavailableBody",
    "botCompanionAria",
    "botDataDeleteBoundary",
    "upgradeTitle",
    "upgradeBody",
    "upgradeEmailLabel",
    "upgradeEmailPlaceholder",
    "upgradeEmailHelp",
    "upgradePasswordLabel",
    "upgradePasswordPlaceholder",
    "upgradePasswordConfirmLabel",
    "upgradePasswordConfirmPlaceholder",
    "upgradeAuditNote",
    "upgradeDisabledHint",
    "upgradeAction",
    "securityCheckAction",
    "securityCheckDescription",
    "linkTelegramAction",
    "linkTelegramDescription",
    "quickHealthAria",
    "quickHealthTitle",
    "linkedBody",
    "unlinkedBody",
    "sessionFact",
    "profileFact",
    "canonicalFact",
    "needsVerification",
    "ready",
    "pendingCompletion",
    "optional",
    "assurance",
    "overviewTitle",
    "overviewBody",
    "activityLink",
    "securityLink",
    "dataControlsLink",
    "telegramLinkedBody",
    "telegramUnlinkedBody",
    "sessionSecurityTitle",
    "sessionSecurityBody",
    "sessionSecurityHelp",
    "openSecurity",
    "logoutConfirm",
    "logout",
)

PROFILE_FIELD_ONLY_KEYS = (
    "displayNamePlaceholder",
    "displayNameHelp",
    "localeLabel",
    "localeHelp",
    "timezoneLabel",
    "timezoneHelp",
    "upgradeEmailLabel",
    "upgradeEmailPlaceholder",
    "upgradeEmailHelp",
    "upgradePasswordLabel",
    "upgradePasswordPlaceholder",
    "upgradePasswordConfirmLabel",
    "upgradePasswordConfirmPlaceholder",
)

ACTIVITY_KEYS = (
    "headerTime",
    "headerCategory",
    "headerAction",
    "headerStatus",
    "defaultCategory",
    "defaultAction",
    "emptyTitle",
    "emptyBody",
    "boundaryTitle",
    "boundaryBody",
    "ownerScoped",
    "maxItems",
    "noDetails",
    "recentTitle",
    "recentBody",
    "accountLink",
    "refresh",
    "refreshSuccess",
    "dataBoundaryTitle",
    "dataBoundaryBody",
)

ACTIVITY_INTEGRATION_ONLY_KEYS = ("refreshSuccess",)

METADATA_KEYS = (
    "page.accountActivity.title",
    "page.accountActivity.description",
)


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    return source[begin : source.index(end, begin + len(start))]


def test_account_profile_and_activity_copy_have_reviewed_vi_en_zh_catalogues() -> None:
    account = _between(PORTAL, "function renderAccount(page, context)", "function renderInterfaceLocaleNavigator")
    activity = _between(PORTAL, "function accountActivityStatus", "function dataControlsRequestStateLabel")

    assert "const ACCOUNT_CENTER_MESSAGES = {" in I18N
    assert "ACCOUNT_CENTER_MESSAGES[locale]" in I18N
    for key in (*PROFILE_KEYS, *ACTIVITY_KEYS):
        assert I18N.count(f'"accountCenter.{"profile" if key in PROFILE_KEYS else "activity"}.{key}"') == 3
    for key in METADATA_KEYS:
        assert I18N.count(f'"{key}"') == 3

    assert set(re.findall(r'\bcopy\("([^"]+)"', account)) == set(PROFILE_KEYS) - set(PROFILE_FIELD_ONLY_KEYS)
    assert set(re.findall(r'\bcopy\("([^"]+)"', activity)) == set(ACTIVITY_KEYS) - set(ACTIVITY_INTEGRATION_ONLY_KEYS)
    assert 'function accountCenterText(key, fallback, params)' in PORTAL
    assert 'return uiText(`accountCenter.${key}`, fallback, params);' in PORTAL
    assert "accountCenterText(" in account
    assert "accountCenterText(" in activity

    fields = _between(PORTAL, "const FIELD_SETS = Object.freeze({", "  const manifest")
    for key in PROFILE_FIELD_ONLY_KEYS:
        assert f'"accountCenter.profile.{key}"' in fields


def test_account_activity_metadata_uses_reviewed_catalogue_and_shell_title() -> None:
    assert 'if (path === "/account/activity") return uiText("page.accountActivity.title", fallback);' in PORTAL
    assert 'if (path === "/account/activity") return uiText("page.accountActivity.description", fallback);' in PORTAL
    assert '"/account/activity": {"vi": "Hoạt động tài khoản · TOAN AAS", "en": "Account activity · TOAN AAS", "zh": "账户活动 · TOAN AAS"},' in PAGES


def test_account_activity_current_workflow_navigation_uses_the_page_catalogue() -> None:
    navigation = _between(PORTAL, "const NAVIGATION_I18N_KEYS", "function localizedNavigationLabel")
    assert '"Hoạt động tài khoản": "page.accountActivity.title"' in navigation


def test_account_locale_copy_stays_presentation_only() -> None:
    account = _between(PORTAL, "function renderAccount(page, context)", "function renderInterfaceLocaleNavigator")
    activity = _between(PORTAL, "function accountActivityStatus", "function dataControlsRequestStateLabel")

    for source in (account, activity):
        lowered = source.lower()
        for forbidden in (
            "fetch(",
            "api(",
            "localstorage.",
            "sessionstorage.",
            "wallet adjustment",
            "payos webhook",
            "provider request",
        ):
            assert forbidden not in lowered

    assert 'data-portal-action="auth-logout"' in account
    assert 'data-portal-action="refresh-account-activity"' in activity
    assert "data-portal-action=\"link-oauth-${safeText(action)}\"" not in account

    refresh_action = _between(INTEGRATION, 'if (action === "refresh-account-activity") {', 'if (action === "governance-documents-refresh") {')
    assert 'i18n.t("accountCenter.activity.refreshSuccess")' in refresh_action
    assert 'toast("Đã làm mới nhật ký hoạt động Web.")' not in refresh_action
