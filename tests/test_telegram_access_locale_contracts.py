"""Contracts for localized, protocol-safe Telegram and OAuth access UI.

The test deliberately executes the standalone browser catalogue in Node.  It
does not import FastAPI, the Bot, or any provider: fixed UI copy is local, but
the one-time challenge protocol remains server/Bot owned.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")


TELEGRAM_KEYS = frozenset(
    {
        "expiredFallback",
        "expiredTitle",
        "newCode",
        "accountRequiredTitle",
        "accountRequiredFallback",
        "createAccount",
        "emailSignIn",
        "challengeTitle",
        "challengeBody",
        "openTelegram",
        "copyCommand",
        "completeSignIn",
        "checkNow",
        "recoveredTitle",
        "recoveredBody",
        "replaceCodeConfirm",
        "title",
        "body",
        "signIn",
        "sectionTitle",
        "sectionBody",
        "noProviderConfigured",
        "linkPanelTitle",
        "linkPanelHint",
        "pendingProviders",
        "startPending",
        "accountRequiredFallbackToast",
        "expiredFallbackToast",
        "waitingFallback",
    }
)

PROVIDER_KEYS = frozenset(
    {
        "telegramWebOnlySuffix",
        "appleAction",
        "telegramAction",
        "continueWith",
        "registerOrContinueWith",
        "telegramRegisterDescription",
        "registerDescription",
        "telegramSignInDescription",
        "signInDescription",
        "unavailableDescription",
        "unavailableTitle",
        "unavailableState",
        "registerSectionTitle",
        "registerSectionBody",
        "noProviderForRegistration",
        "pendingProviderMethods",
    }
)


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    return source[begin : source.index(end, begin + len(start))]


def _catalogue_keys(locale: str) -> set[str]:
    match = re.search(
        rf"Object\.assign\(TELEGRAM_ACCESS_MESSAGES\.{locale}, \{{(?P<body>.*?)\n  \}}\);",
        I18N,
        flags=re.DOTALL,
    )
    assert match, f"missing TELEGRAM_ACCESS_MESSAGES for {locale}"
    return set(re.findall(r'^\s*"access\.(?:telegram|provider)\.([^"\s]+)"\s*:', match.group("body"), flags=re.MULTILINE))


def _runtime_copy() -> dict[str, dict[str, str]]:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for the Portal locale runtime contract")

    keys = sorted([*(f"access.telegram.{key}" for key in TELEGRAM_KEYS), *(f"access.provider.{key}" for key in PROVIDER_KEYS)])
    script = r'''
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync(process.argv[1], "utf8");
const keys = JSON.parse(process.argv[2]);
const documentElement = { lang: "vi", dir: "ltr", setAttribute() {} };
const context = {
  document: { documentElement, getElementById() { return null; }, title: "" },
  JSON,
  URL,
  URLSearchParams,
  CustomEvent: function CustomEvent() {},
  dispatchEvent() { return true; }
};
context.globalThis = context;
vm.createContext(context);
vm.runInContext(source, context, { filename: process.argv[1] });
const api = context.TOANAASI18n;
const output = {};
for (const locale of ["vi", "en", "zh"]) {
  api.setLocale(locale);
  output[locale] = Object.fromEntries(keys.map((key) => [key, api.t(key)]));
}
process.stdout.write(JSON.stringify(output));
'''
    result = subprocess.run(
        [node, "-e", script, str(ROOT / "static" / "portal" / "portal-i18n.js"), json.dumps(keys)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_telegram_access_catalogue_is_complete_and_has_real_vi_en_zh_copy() -> None:
    assert "const TELEGRAM_ACCESS_MESSAGES = { vi: {}, en: {}, zh: {} };" in I18N
    assert "TELEGRAM_ACCESS_MESSAGES[locale]" in I18N

    expected = TELEGRAM_KEYS | PROVIDER_KEYS
    catalogues = {locale: _catalogue_keys(locale) for locale in ("vi", "en", "zh")}
    assert catalogues["vi"] == catalogues["en"] == catalogues["zh"]
    assert expected <= catalogues["vi"]
    for key in expected:
        namespace = "telegram" if key in TELEGRAM_KEYS else "provider"
        assert I18N.count(f'"access.{namespace}.{key}"') == 3

    copy = _runtime_copy()
    for locale in ("vi", "en", "zh"):
        assert all(value.strip() for value in copy[locale].values())
    assert copy["vi"]["access.telegram.signIn"] == "Đăng nhập với Telegram"
    assert copy["en"]["access.telegram.signIn"] == "Sign in with Telegram"
    assert copy["zh"]["access.telegram.signIn"] == "使用 Telegram 登录"
    assert copy["vi"]["access.provider.unavailableState"] == "Chờ cấu hình máy chủ"
    assert copy["en"]["access.provider.unavailableState"] == "Awaiting server configuration"
    assert copy["zh"]["access.provider.unavailableState"] == "等待服务器配置"


def test_login_and_registration_renderers_localize_only_fixed_access_copy() -> None:
    provider = _between(PORTAL, "function renderPublicOAuthCard", "function renderExpiredTelegramLoginChallenge")
    expired = _between(PORTAL, "function renderExpiredTelegramLoginChallenge", "function renderTelegramLoginMethod")
    login = _between(PORTAL, "function renderTelegramLoginMethod", "function renderOAuthRegistrationMethods")
    registration = _between(PORTAL, "function renderOAuthRegistrationMethods", "function renderAuth")
    rendered = provider + expired + login + registration

    assert "function accessPresentationText(" in PORTAL
    for key in TELEGRAM_KEYS:
        # Integration-only browser fallbacks are deliberately absent from the
        # renderer; all other fixed Telegram strings must pass through i18n.
        if key.endswith("Toast") or key in {"startPending", "waitingFallback"}:
            continue
        assert f'accessPresentationText("telegram.{key}"' in rendered
    for key in PROVIDER_KEYS:
        assert f'"provider.{key}"' in rendered

    # Signed protocol values remain data.  Fixed locale copy never translates
    # or manufactures a code, identity, link result, provider status or URL.
    for requirement in (
        "safeTelegramLink(data.deep_link)",
        "safeText(code)",
        "safeText(deepLink)",
        "safeText(flow.message || accessPresentationText",
        "safeText(detail)",
        "publicOAuthStartPath(provider, continuation, context)",
    ):
        assert requirement in rendered
    lowered = rendered.lower()
    for forbidden in (
        "localstorage",
        "sessionstorage",
        "telegram_id",
        "wallet",
        "payos",
        "fetch(",
        "api(",
    ):
        assert forbidden not in lowered


def test_browser_fallbacks_are_localized_without_protocol_or_storage_drift() -> None:
    start = _between(INTEGRATION, 'if (action === "start-telegram-login")', 'if (action === "refresh-telegram-login")')
    refresh = _between(INTEGRATION, "async function refreshTelegramLoginChallenge", "async function completeTelegramLoginChallenge")
    resume = _between(INTEGRATION, "async function resumeTelegramLoginChallenge", "async function completeTelegramLinkChallenge")
    source = start + refresh + resume

    assert "function publicAccessText(" in INTEGRATION
    for key in (
        "telegram.startPending",
        "telegram.accountRequiredFallbackToast",
        "telegram.expiredFallbackToast",
        "telegram.waitingFallback",
    ):
        assert f'publicAccessText("{key}"' in source
    assert "result.message || publicAccessText" in source
    assert "failure.message || publicAccessText" in source

    for request in (
        'api("/auth/telegram/login/start", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })',
        'api("/auth/telegram/login/status")',
        'api("/auth/telegram/login/complete", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })',
    ):
        assert request in (INTEGRATION + source)
    lowered = source.lower()
    for forbidden in ("localstorage", "sessionstorage", "telegram_id"):
        assert forbidden not in lowered
    assert not re.search(r"\bcode\s*:", source)
    assert not re.search(r"\bdeep_link\s*:", source)
