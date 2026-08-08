"""Locale and protocol contracts for optional Telegram onboarding.

The catalogue owns only fixed, browser-authored presentation copy. One-time
codes, deep links, expiry, configuration state and public server/Bot messages
remain signed protocol data and never become browser authority.
"""

from __future__ import annotations

from pathlib import Path
import re

from copyfast_pages import render_portal


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")


ONBOARDING_FIXED_COPY_KEYS = frozenset(
    {
        "page.title", "page.description", "linkActionCreate", "linkActionWaiting",
        "resumeWorkflow", "enterWorkspace", "choiceAria", "independentTitle",
        "independentBody", "challengeTitle", "challengeSubtitle", "codeLabel",
        "expiryLabel", "minutes", "challengeNote", "openTelegram", "copyCommand",
        "checkNow", "checkStatus", "newCode", "replaceCodeConfirm",
        "replacePendingCodeConfirm", "replacePendingCode", "emptyTitle", "emptyBody",
        "emptyNote", "stepsAria", "stepStartTitle", "stepStartBody",
        "stepVerifyTitle", "stepVerifyBody", "stepWorkspaceTitle", "stepWorkspaceBody",
        "routeAria", "routeResumeTitle", "routeResumeBody", "routeStartTitle",
        "routeStartBody", "routeResumeState", "routeIndependentState",
        "continuationTitle", "continuationBody", "completedTitle", "completedBody",
        "completedCanonicalIdentity", "completedNoBrowserIdentity", "openDashboard",
        "assuranceSummary", "assuranceCodeTitle", "assuranceCodeBody",
        "assuranceBotTitle", "assuranceBotBody", "assuranceReturnTitle",
        "assuranceReturnBody", "recoveredReadyTitle", "recoveredExpiredTitle",
        "recoveredPendingTitle", "recoveredReadyBody", "recoveredExpiredBody",
        "recoveredPendingBody", "pausedTitle", "pausedBody", "pausedNote",
        "browser.startPending", "browser.waitingForBot", "browser.expired",
        "browser.copySuccess", "browser.completeResume", "browser.completeDashboard",
        "browser.invalidCommand", "browser.clipboardUnavailable",
    }
)

TELEGRAM_CONNECTION_FIXED_COPY_KEYS = frozenset(
    {
        "adapterPendingReason", "missingConfigReason", "unavailableReason",
        "lastKindAccountLink", "lastKindLogin", "lastCallbackAt", "verifiedTitle",
        "verifiedBody", "readyTitle", "readyBody", "adapterPendingBody",
        "missingConfigBody", "unknownBody", "notReadyTitle",
    }
)


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    return source[begin : source.index(end, begin + len(start))]


def _catalogue_keys(name: str, namespace: str, locale: str) -> set[str]:
    match = re.search(
        rf"Object\.assign\({name}\.{re.escape(locale)}, \{{(?P<body>.*?)\n  \}}\);",
        I18N,
        flags=re.DOTALL,
    )
    assert match, f"Missing reviewed {name} catalogue for {locale}"
    return set(re.findall(rf'^\s*"{re.escape(namespace)}\.([^"]+)"\s*:', match.group("body"), flags=re.MULTILINE))


def test_onboarding_has_complete_reviewed_vi_en_zh_catalogues() -> None:
    assert "const ONBOARDING_MESSAGES = { vi: {}, en: {}, zh: {} };" in I18N
    assert "const TELEGRAM_CONNECTION_MESSAGES = { vi: {}, en: {}, zh: {} };" in I18N

    onboarding = {locale: _catalogue_keys("ONBOARDING_MESSAGES", "onboarding", locale) for locale in ("vi", "en", "zh")}
    connection = {locale: _catalogue_keys("TELEGRAM_CONNECTION_MESSAGES", "telegramConnection", locale) for locale in ("vi", "en", "zh")}
    assert onboarding["vi"] == onboarding["en"] == onboarding["zh"]
    assert connection["vi"] == connection["en"] == connection["zh"]
    assert ONBOARDING_FIXED_COPY_KEYS <= onboarding["vi"]
    assert TELEGRAM_CONNECTION_FIXED_COPY_KEYS <= connection["vi"]

    assert "ONBOARDING_MESSAGES[locale]" in I18N
    assert "TELEGRAM_CONNECTION_MESSAGES[locale]" in I18N
    for key in ONBOARDING_FIXED_COPY_KEYS:
        assert I18N.count(f'"onboarding.{key}"') == 3
    for key in TELEGRAM_CONNECTION_FIXED_COPY_KEYS:
        assert I18N.count(f'"telegramConnection.{key}"') == 3


def test_onboarding_renderers_translate_fixed_copy_and_escape_dynamic_values() -> None:
    connection = _between(PORTAL, "function telegramConnectionBlockReason", "function safeOnboardingContinuation")
    recovered = _between(PORTAL, "function renderRecoveredTelegramLinkChallenge", "function starterKitCatalogItem")
    onboarding = _between(PORTAL, "function renderOnboarding(page, context)", "function authProviderMark(provider)")
    page_title = _between(PORTAL, "function localizedPageTitle", "function documentTitle")
    page_description = _between(PORTAL, "function localizedPageDescription", "function initials")
    rendered = connection + recovered + onboarding + page_title + page_description

    assert "function onboardingText(" in PORTAL
    assert "function telegramConnectionText(" in PORTAL
    onboarding_keys = set(re.findall(r'\bonboardingText\(\s*"([^"]+)"', rendered))
    connection_keys = set(re.findall(r'\btelegramConnectionText\(\s*"([^"]+)"', rendered))
    # Step and assurance rows pass a reviewed static key through their compact
    # data arrays, so also account for those literal key declarations.
    declared_keys = set(re.findall(r'"((?:step|assurance)[A-Za-z]+)"', rendered))
    assert ONBOARDING_FIXED_COPY_KEYS - {key for key in ONBOARDING_FIXED_COPY_KEYS if key.startswith("browser.")} <= onboarding_keys | declared_keys
    assert TELEGRAM_CONNECTION_FIXED_COPY_KEYS <= connection_keys

    # These values are delivered by the signed server/Bot flow. Keep them at
    # an escaped render boundary instead of treating them as browser authority.
    for requirement in (
        "safeText(code)",
        "safeText(deepLink)",
        "message: flow.message",
        "safeText(message",
        "String(data.expires_in_minutes",
        "safeText(text)",
        "missing.join",
    ):
        assert requirement in rendered

    for forbidden in (r"\blocalStorage\s*[.(]", r"\bsessionStorage\s*[.(]", r"\btelegram_id\b"):
        assert not re.search(forbidden, rendered)


def test_onboarding_actions_keep_server_messages_protocol_and_browser_boundary() -> None:
    completion = _between(INTEGRATION, "async function completeTelegramLinkChallenge", "function recoverTelegramLinkFlow")
    recovered = _between(INTEGRATION, "function recoverTelegramLinkFlow", "function resumeTelegramLinkChallenge")
    start_action = _between(
        INTEGRATION,
        'if (action === "start-telegram-link")',
        'if (action === "refresh-account-activity")',
    )
    copy_action = _between(
        INTEGRATION,
        'if (action === "copy-telegram-link-command")',
        'if (action === "copy-bot-companion-command")',
    )
    copy_helper = _between(INTEGRATION, "async function copyTelegramLinkCommand", "function copyBotCompanionCommand")
    action_source = completion + recovered + start_action + copy_action + copy_helper

    assert "function onboardingText(" in INTEGRATION
    for key in (
        "browser.startPending", "browser.waitingForBot", "browser.expired",
        "browser.copySuccess", "browser.completeResume", "browser.completeDashboard",
        "browser.invalidCommand", "browser.clipboardUnavailable",
    ):
        assert f'onboardingText("{key}"' in action_source
        assert I18N.count(f'"onboarding.{key}"') == 3

    # A server public message wins; a localized browser sentence is only the
    # fallback when the signed API did not supply one.
    assert "completed.message || fallback" in action_source
    assert "result.message || onboardingText" in action_source

    for request in (
        'api("/auth/telegram/link/start", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })',
        'api("/auth/telegram/link/status")',
        'api("/auth/telegram/link/complete", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })',
        'const botCommand = code ? `/linkweb ${code}` : "";',
        'data-portal-action="start-telegram-link"',
        'data-portal-action="refresh-link-status"',
        'data-portal-action="copy-telegram-link-command"',
    ):
        assert request in (PORTAL + action_source)
    assert r"/^\/linkweb\s+[A-Za-z0-9_-]{12,160}$/" in copy_helper

    for forbidden in (r"\blocalStorage\s*[.(]", r"\bsessionStorage\s*[.(]", r"\btelegram_id\b"):
        assert not re.search(forbidden, action_source)


def test_onboarding_first_paint_is_route_and_locale_specific() -> None:
    expected = {
        "vi": {
            "title": "Bắt đầu với TOAN AAS",
            "description": "Bắt đầu với Workspace Web độc lập hoặc liên kết Telegram bằng mã một lần an toàn khi cần dữ liệu canonical do Bot xác minh.",
        },
        "en": {
            "title": "Get started with TOAN AAS",
            "description": "Start with an independent Web Workspace or securely link Telegram with a one-time code when Bot-verified canonical data is needed.",
        },
        "zh": {
            "title": "开始使用 TOAN AAS",
            "description": "先独立使用 Web 工作台；仅在需要 Bot 验证的权威数据时，使用一次性代码安全关联 Telegram。",
        },
    }

    assert "_PORTAL_SHELL_DESCRIPTIONS" in PAGES
    assert '"/onboarding": {' in PAGES
    assert ".replace(\"__PORTAL_DESCRIPTION__\", html.escape(_shell_description_for(normalized, locale), quote=True))" in PAGES

    for locale, copy in expected.items():
        response = render_portal("/onboarding", interface_locale=locale)
        assert response.status_code == 200
        assert f"<title>{copy['title']}</title>".encode("utf-8") in response.body
        assert f'<meta name="description" content="{copy["description"]}">'.encode("utf-8") in response.body
