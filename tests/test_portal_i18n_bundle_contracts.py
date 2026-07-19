"""Focused browser contracts for the reviewed Portal UI locale bundle.

The interface preference is intentionally much narrower than workflow/content
language.  These tests exercise the standalone browser catalog in Node rather
than importing the FastAPI application or any Bot/provider module.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "static" / "portal" / "portal-i18n.js"
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
SHELL_TEMPLATE = (ROOT / "templates" / "portal_shell.html").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    finish = source.index(end, begin)
    return source[begin:finish]


def _node_i18n_snapshot() -> dict:
    """Load the browser-only bundle in an isolated, minimal DOM-like context."""

    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for the Portal i18n runtime contract")

    script = r'''
const fs = require("fs");
const vm = require("vm");
const sourcePath = process.argv[1];
const source = fs.readFileSync(sourcePath, "utf8");

const documentElement = {
  lang: "vi",
  dir: "ltr",
  attributes: {},
  setAttribute(name, value) { this.attributes[name] = String(value); }
};
const document = {
  documentElement,
  title: "",
  getElementById(id) {
    return id === "portal-bootstrap"
      ? { textContent: JSON.stringify({ account: { profile: { locale: "vi" } } }) }
      : null;
  }
};
const context = {
  document,
  console,
  JSON,
  URL,
  URLSearchParams,
  CustomEvent: function CustomEvent(type, init) {
    this.type = type;
    this.detail = init && init.detail;
  },
  dispatchEvent() { return true; }
};
context.globalThis = context;
vm.createContext(context);
vm.runInContext(source, context, { filename: sourcePath });

const api = context.TOANAASI18n;
if (!api || api !== context.TOAN_AAS_I18N) throw new Error("Portal i18n API was not exposed");
const expected = ["vi", "en", "zh"];
const localeCodes = api.getLocales().map((locale) => locale.code);
if (JSON.stringify(localeCodes) !== JSON.stringify(expected)) {
  throw new Error(`Unexpected reviewed locale catalog: ${JSON.stringify(localeCodes)}`);
}

const referenceKeys = Object.keys(api.messages.vi).sort();
for (const locale of expected) {
  const keys = Object.keys(api.messages[locale]).sort();
  if (JSON.stringify(keys) !== JSON.stringify(referenceKeys)) {
    throw new Error(`Locale keyset diverged for ${locale}`);
  }
  for (const key of ["chrome.newWorkflow", "chrome.installApp", "mobile.workspace", "account.interfaceLocale", "setup.title", "starter.install"]) {
    if (!api.t(key, locale)) throw new Error(`Missing ${key} translation for ${locale}`);
  }
}

if (api.normalizeLocale("zh-CN") !== "zh") throw new Error("Chinese display alias did not normalize");
if (api.normalizeLocale("ja") !== "en") throw new Error("Unreviewed interface locale did not fall back to English");
if (api.t("starter.install", "zh") !== "安装入门套件") throw new Error("Reviewed Chinese text is unavailable");
if (api.t("starter.install", "en") !== "Install Starter Kit") throw new Error("Reviewed English text is unavailable");
if (api.t("missing.translation.key", "vi") !== "") throw new Error("Unknown key must not invent a translation");

api.setLocale("zh-CN", { emit: false, titleKey: "page.account.title" });
if (api.currentLocale() !== "zh") throw new Error("setLocale did not select Chinese");
if (documentElement.lang !== "zh-CN" || documentElement.dir !== "ltr") throw new Error("Document language metadata was not updated");
if (documentElement.attributes["data-portal-locale"] !== "zh") throw new Error("Document locale marker was not updated");
if (!document.title) throw new Error("Localized document title was not applied");

api.setLocale("ja", { emit: false });
if (api.currentLocale() !== "en" || documentElement.lang !== "en") {
  throw new Error("Unreviewed interface locale did not use the English display fallback");
}

process.stdout.write(JSON.stringify({
  locales: localeCodes,
  keyCount: referenceKeys.length,
  activeLocale: api.currentLocale(),
  documentLocale: documentElement.attributes["data-portal-locale"]
}));
'''
    try:
        result = subprocess.run(
            [node, "-e", script, str(BUNDLE)],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except OSError as exc:
        # Some Windows sandboxes expose Node on PATH but cannot give a child
        # valid pipe handles. The static contracts below still protect that
        # runner without misreporting its infrastructure limitation as a UI
        # regression.
        pytest.skip(f"Node subprocess is unavailable in this test runner: {exc}")
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout)


def test_i18n_bundle_has_equal_reviewed_vi_en_zh_coverage_at_runtime() -> None:
    snapshot = _node_i18n_snapshot()
    assert snapshot["locales"] == ["vi", "en", "zh"]
    assert snapshot["keyCount"] >= 100
    assert snapshot["activeLocale"] == "en"
    assert snapshot["documentLocale"] == "en"


def test_i18n_bundle_is_presentation_only_without_browser_persistence_or_network() -> None:
    source = BUNDLE.read_text(encoding="utf-8")

    # The catalog may read the signed bootstrap locale and update document
    # metadata, but it must never become an account store, a network client,
    # a workflow action dispatcher or a second source of state.
    for forbidden in (
        "localStorage",
        "sessionStorage",
        "indexedDB",
        "XMLHttpRequest",
        "fetch(",
        "navigator.serviceWorker",
        "history.pushState",
        "window.location",
        "api(",
        "setTimeout(",
        "setInterval(",
    ):
        assert forbidden not in source

    for required in (
        "function bootstrapLocale()",
        "function verifyEqualKeysets()",
        "function setLocale(value, options)",
        'Object.defineProperty(global, "TOANAASI18n"',
        'Object.defineProperty(global, "TOAN_AAS_I18N"',
    ):
        assert required in source


def test_shell_build_and_pwa_load_i18n_before_portal_runtime_without_private_cache() -> None:
    fallback_shell = _between(PAGES, "def _fallback_template()", "\n\ndef render_portal").replace('\\"', '"')
    for shell in (SHELL_TEMPLATE, fallback_shell):
        i18n = shell.index('/static/portal/portal-i18n.js?v=__PORTAL_ASSET_VERSION__')
        portal = shell.index('/static/portal/portal.js?v=__PORTAL_ASSET_VERSION__')
        integration = shell.index('/static/portal/integration.js?v=__PORTAL_ASSET_VERSION__')
        assert i18n < portal < integration
        assert 'data-portal-locale="vi"' in shell

    build_sources = _between(PAGES, "_PORTAL_BUILD_SOURCE_FILES = (", ")\n\n")
    assert '"portal-i18n.js",' in build_sources

    shell_cache = _between(WORKER, "const SHELL = Object.freeze([", "]);\nconst SHELL_PATHS")
    public_navigation = _between(WORKER, "const PUBLIC_NAVIGATION_PATHS = Object.freeze([", "]);\n// This is deliberately redundant")
    private_paths = _between(WORKER, "const PRIVATE_PATH_PREFIXES = Object.freeze([", "]);\n\nself.addEventListener(\"install\"")
    assert '"/static/portal/portal-i18n.js",' in shell_cache
    assert '"/static/portal/portal-i18n.js",' not in public_navigation
    assert '"/static/portal/portal-i18n.js",' not in private_paths
    assert '"/api/' not in shell_cache
    assert '"/starter-kits"' not in shell_cache
    assert '"/account"' not in shell_cache


def test_interface_locale_is_closed_and_separate_from_workflow_language_contracts() -> None:
    workflow_options = _between(PORTAL, "const LANGUAGE_OPTIONS = Object.freeze([", "// Interface locale intentionally")
    interface_options = _between(PORTAL, "const INTERFACE_LOCALE_OPTIONS = Object.freeze([", "]);\n\n  const FIELD_SETS")
    profile_fields = _between(PORTAL, "    profile: [", "    adminFilter: [")
    setup_projection = _between(INTEGRATION, "const INTERFACE_LOCALES", "// Keep the browser catalog closed")

    # Canonical workflow actions still retain their deliberately broader set;
    # a profile preference must not silently restrict translation/dubbing/etc.
    for workflow_value in ('value: "zh_cn"', 'value: "ja"', 'value: "auto"'):
        assert workflow_value in workflow_options

    assert interface_options.count('value: "') == 3
    for locale in ("vi", "en", "zh"):
        assert f'value: "{locale}"' in interface_options
    for disallowed_interface_value in ('value: "zh_cn"', 'value: "ja"', 'value: "auto"'):
        assert disallowed_interface_value not in interface_options

    assert 'name: "locale"' in profile_fields
    assert "options: INTERFACE_LOCALE_OPTIONS" in profile_fields
    assert "options: LANGUAGE_OPTIONS" not in profile_fields
    assert "target_language" not in profile_fields
    assert 'const INTERFACE_LOCALES = new Set(["vi", "en", "zh"]);' in setup_projection
    for forbidden in ("target_language", "source_language", "workflow_language", "telegram_id", "canonical_user_id"):
        assert forbidden not in setup_projection


def test_core_portal_renderers_consume_reviewed_locale_keys() -> None:
    chrome = _between(PORTAL, "function renderMobileNav(page)", "function normalizeCommandSearch(value)")
    hero = _between(PORTAL, "function renderHero(page, context)", "const FEATURE_CATALOG_GROUPS")
    account = _between(PORTAL, "function renderAccount(page, context)", "function renderAccountSecurity(page, context)")
    setup = _between(PORTAL, "function renderWorkspaceSetup(page, context)", "function renderOnboarding(page, context)")
    starter = _between(PORTAL, "function starterKitRecordCounts(kit)", "function renderWorkspaceSetup(page, context)")

    for required in (
        'uiText("mobile.workspace"',
        'uiText("chrome.searchWorkspace"',
        'uiText("chrome.openNavigation"',
        'uiText("chrome.installApp"',
    ):
        assert required in chrome or required in PORTAL
    assert "const STATE_I18N_KEYS" in PORTAL
    assert "function stateLabel(status)" in PORTAL
    assert "localizedPageTitle(page, context)" in hero
    assert "localizedPageDescription(page)" in hero
    assert "options: INTERFACE_LOCALE_OPTIONS" in PORTAL
    for required in ('uiText("account.display_name"', 'uiText("account.profile"', 'uiText("account.save"'):
        assert required in account or required in PORTAL
    for required in ('uiText("setup.role"', 'uiText("setup.focusTitle"', 'uiText("setup.saveAndEnter"'):
        assert required in setup
    for required in ('uiText("starter.catalogTitle"', 'uiText("starter.confirmationTitle"', 'uiText("starter.scopeTitle"'):
        assert required in starter
