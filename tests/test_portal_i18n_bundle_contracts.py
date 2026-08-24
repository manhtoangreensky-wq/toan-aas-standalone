"""Focused browser contracts for the reviewed Portal UI locale bundle.

The interface preference is intentionally much narrower than workflow/content
language.  These tests exercise the standalone browser catalog in Node rather
than importing the FastAPI application or any Bot/provider module.
"""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "static" / "portal" / "portal-i18n.js"
PORTAL_BUNDLE = ROOT / "static" / "portal" / "portal.js"
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
PORTAL_CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
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
      ? { textContent: JSON.stringify({ interfaceLocale: "zh", account: { profile: { locale: "vi" } } }) }
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
  for (const key of ["chrome.newWorkflow", "chrome.installApp", "chrome.adminAppCaption", "chrome.searchAdmin", "chrome.adminCommandCount", "mobile.workspace", "nav.currentWorkflow", "account.interfaceLocale", "interfaceLocale.formLegend", "interfaceLocale.supportHeading", "page.interfaceLocale.title", "setup.title", "starter.install", "shellNav.billing", "shellNav.contentStudio", "shellNav.scriptToSeries", "shellNav.serviceStatus"]) {
    if (!api.t(key, locale)) throw new Error(`Missing ${key} translation for ${locale}`);
  }
}

const landingKeys = [
  "landing.nav.features", "landing.nav.workflow", "landing.nav.trust",
  "landing.nav.language", "landing.cta.start", "landing.cta.signIn",
  "landing.hero.title", "landing.hero.body", "landing.hero.explore",
  "landing.proof.webOwned", "landing.proof.noFakeOutput",
  "landing.proof.companionOptional", "landing.preview.title",
  "landing.workflow.title", "landing.trust.title", "landing.footer.legal"
];
for (const locale of expected) {
  for (const key of landingKeys) {
    if (!api.t(key, locale)) throw new Error(`Missing ${key} translation for ${locale}`);
  }
}

const postbackReadinessKeys = [
  "adminGeneric.postbackReadiness.route.title",
  "adminGeneric.postbackReadiness.route.description",
  "adminGeneric.postbackReadiness.intro.kicker",
  "adminGeneric.postbackReadiness.intro.title",
  "adminGeneric.postbackReadiness.intro.body",
  "adminGeneric.postbackReadiness.intro.statusTitle",
  "adminGeneric.postbackReadiness.intro.statusBody",
  "adminGeneric.postbackReadiness.checklist.kicker",
  "adminGeneric.postbackReadiness.checklist.title",
  "adminGeneric.postbackReadiness.checklist.body",
  "adminGeneric.postbackReadiness.checkpoint.scope.title",
  "adminGeneric.postbackReadiness.checkpoint.scope.body",
  "adminGeneric.postbackReadiness.checkpoint.dedupe.title",
  "adminGeneric.postbackReadiness.checkpoint.dedupe.body",
  "adminGeneric.postbackReadiness.checkpoint.handoff.title",
  "adminGeneric.postbackReadiness.checkpoint.handoff.body",
  "adminGeneric.postbackReadiness.handoff.kicker",
  "adminGeneric.postbackReadiness.handoff.title",
  "adminGeneric.postbackReadiness.handoff.body",
  "adminGeneric.postbackReadiness.handoff.itemScope.title",
  "adminGeneric.postbackReadiness.handoff.itemScope.body",
  "adminGeneric.postbackReadiness.handoff.itemAuthority.title",
  "adminGeneric.postbackReadiness.handoff.itemAuthority.body",
  "adminGeneric.postbackReadiness.handoff.itemChannel.title",
  "adminGeneric.postbackReadiness.handoff.itemChannel.body",
  "adminGeneric.postbackReadiness.limits.kicker",
  "adminGeneric.postbackReadiness.limits.title",
  "adminGeneric.postbackReadiness.limits.body",
  "adminGeneric.postbackReadiness.boundary.noConfig.title",
  "adminGeneric.postbackReadiness.boundary.noConfig.body",
  "adminGeneric.postbackReadiness.boundary.noEvents.title",
  "adminGeneric.postbackReadiness.boundary.noEvents.body",
  "adminGeneric.postbackReadiness.boundary.noFinancial.title",
  "adminGeneric.postbackReadiness.boundary.noFinancial.body",
  "adminGeneric.postbackReadiness.link.growth",
  "adminGeneric.postbackReadiness.link.audit",
  "adminGeneric.postbackReadiness.notes.integration.title",
  "adminGeneric.postbackReadiness.notes.safety.title",
  "adminGeneric.postbackReadiness.notes.scope.body",
  "adminGeneric.postbackReadiness.notes.botBoundary.body"
];
for (const locale of expected) {
  for (const key of postbackReadinessKeys) {
    if (!api.t(key, locale)) throw new Error(`Missing ${key} translation for ${locale}`);
  }
}
const reviewedPostbackReadinessCopy = {
  vi: "Postback Readiness",
  en: "Postback Readiness",
  zh: "回传准备"
};
for (const [locale, expectedCopy] of Object.entries(reviewedPostbackReadinessCopy)) {
  if (api.t("adminGeneric.postbackReadiness.route.title", locale) !== expectedCopy) {
    throw new Error("Postback Readiness route copy diverged for " + locale);
  }
}

const dashboardKeys = [
  "dashboard.summary.kicker", "dashboard.summary.greeting",
  "dashboard.summary.body", "dashboard.summary.projects",
  "dashboard.summary.drafts", "dashboard.summary.processing",
  "dashboard.summary.readyDownload", "dashboard.guide.title",
  "dashboard.drafts.title", "dashboard.projects.title",
  "dashboard.work.title", "dashboard.account.title",
  "dashboard.canonical.loadingTitle", "dashboard.canonical.readyTitle",
  "dashboard.actionCenter.title", "dashboard.launchpad.title",
  "dashboard.assurance.title", "dashboard.account.linkedBody",
  "dashboard.work.kicker", "dashboard.work.body", "dashboard.assurance.body",
  "dashboard.canonical.kicker", "dashboard.canonical.loadingBody",
  "dashboard.canonical.failedTitle", "dashboard.canonical.failedBody",
  "dashboard.canonical.retry", "dashboard.canonical.checkConnection",
  "dashboard.canonical.guardedTitle", "dashboard.canonical.guardedBody",
  "dashboard.canonical.learnLink", "dashboard.canonical.openSecurity",
  "dashboard.canonical.readyBody",
  "dashboard.canonical.metrics.balanceLabel",
  "dashboard.canonical.metrics.balanceCanonicalDetail",
  "dashboard.canonical.metrics.balancePendingDetail",
  "dashboard.canonical.metrics.spentLabel",
  "dashboard.canonical.metrics.spentCanonicalDetail",
  "dashboard.canonical.metrics.spentPendingDetail",
  "dashboard.canonical.metrics.jobsLabel", "dashboard.canonical.metrics.jobsDetail",
  "dashboard.canonical.metrics.assetsLabel", "dashboard.canonical.metrics.assetsDetail",
  "dashboard.canonical.jobs.title", "dashboard.canonical.jobs.body",
  "dashboard.canonical.jobs.open", "dashboard.canonical.jobs.table.id",
  "dashboard.canonical.jobs.table.feature", "dashboard.canonical.jobs.table.status",
  "dashboard.canonical.jobs.table.output", "dashboard.canonical.jobs.emptyTitle",
  "dashboard.canonical.jobs.emptyBody", "dashboard.canonical.assets.title",
  "dashboard.canonical.assets.body", "dashboard.canonical.assets.open",
  "dashboard.canonical.assets.table.asset", "dashboard.canonical.assets.table.feature",
  "dashboard.canonical.assets.table.status", "dashboard.canonical.assets.table.delivery",
  "dashboard.canonical.assets.emptyTitle", "dashboard.canonical.assets.emptyBody",
  "dashboard.actionCenter.kicker", "dashboard.actionCenter.body",
  "dashboard.actionCenter.openAll", "dashboard.actionCenter.processing.label",
  "dashboard.actionCenter.processing.detailActive",
  "dashboard.actionCenter.processing.detailEmpty",
  "dashboard.actionCenter.processing.action", "dashboard.actionCenter.delivery.label",
  "dashboard.actionCenter.delivery.detailActive",
  "dashboard.actionCenter.delivery.detailEmpty",
  "dashboard.actionCenter.delivery.action", "dashboard.actionCenter.review.label",
  "dashboard.actionCenter.review.detailActive",
  "dashboard.actionCenter.review.detailEmpty",
  "dashboard.actionCenter.review.action", "dashboard.actionCenter.tickets.label",
  "dashboard.actionCenter.tickets.detailActive",
  "dashboard.actionCenter.tickets.detailEmpty",
  "dashboard.actionCenter.tickets.action", "dashboard.launchpad.kicker",
  "dashboard.launchpad.body", "dashboard.launchpad.pricing",
  "dashboard.launchpad.open", "dashboard.launchpad.studio.image.title",
  "dashboard.launchpad.studio.image.body", "dashboard.launchpad.studio.image.tagPrompt",
  "dashboard.launchpad.studio.image.tagAssets", "dashboard.launchpad.studio.video.title",
  "dashboard.launchpad.studio.video.body", "dashboard.launchpad.studio.video.tagDraft",
  "dashboard.launchpad.studio.video.tagJobs", "dashboard.launchpad.studio.voice.title",
  "dashboard.launchpad.studio.voice.body", "dashboard.launchpad.studio.voice.tagVault",
  "dashboard.launchpad.studio.voice.tagEstimate", "dashboard.launchpad.studio.music.title",
  "dashboard.launchpad.studio.music.body", "dashboard.launchpad.studio.music.tagPolicy",
  "dashboard.launchpad.studio.music.tagQuote", "dashboard.launchpad.studio.content.title",
  "dashboard.launchpad.studio.content.body", "dashboard.launchpad.studio.content.tagPlanning",
  "dashboard.launchpad.studio.content.tagDraft", "dashboard.launchpad.studio.documents.title",
  "dashboard.launchpad.studio.documents.body",
  "dashboard.launchpad.studio.documents.tagFiles",
  "dashboard.launchpad.studio.documents.tagGuarded",
  "dashboard.canonical.jobs.output.none",
  "dashboard.canonical.jobs.output.held",
  "dashboard.canonical.jobs.output.validated",
  "dashboard.canonical.jobs.output.reported",
  "dashboard.canonical.assets.source.webVault",
  "dashboard.canonical.assets.source.webNativeOutput",
  "dashboard.canonical.assets.source.canonicalDelivery",
  "dashboard.canonical.assets.openVaultAria",
  "dashboard.canonical.assets.openJobAria",
  "dashboard.canonical.assets.delivery.vault",
  "dashboard.canonical.assets.delivery.download",
  "dashboard.canonical.assets.delivery.signedPending",
  "dashboard.canonical.assets.delivery.unavailable",
  "dashboard.canonical.assets.delivery.reported",
  "dashboard.canonical.assets.delivery.completedPending",
  "dashboard.canonical.assets.delivery.pending"
];
for (const locale of expected) {
  for (const key of dashboardKeys) {
    if (!api.t(key, locale)) throw new Error(`Missing ${key} translation for ${locale}`);
  }
}

const financePlanningKeys = [
  "financePlanning.currency", "financePlanning.state.active",
  "financePlanning.state.archived", "financePlanning.state.draft",
  "financePlanning.state.review", "financePlanning.state.approved",
  "financePlanning.state.guarded", "financePlanning.transition.none",
  "financePlanning.period.label", "financePlanning.period.view",
  "financePlanning.pagination.previous", "financePlanning.pagination.next",
  "financePlanning.status.guarded", "financePlanning.status.loading",
  "financePlanning.status.ready", "financePlanning.status.failed",
  "financePlanning.guard.retry", "financePlanning.guard.back",
  "financePlanning.metrics.activeBudget", "financePlanning.metrics.planned",
  "financePlanning.metrics.remaining", "financePlanning.metrics.review",
  "financePlanning.budget.title", "financePlanning.cost.title"
];
for (const locale of expected) {
  for (const key of financePlanningKeys) {
    if (!api.t(key, locale)) throw new Error(`Missing ${key} translation for ${locale}`);
  }
}

const adminFinanceWorkspaceKeys = [
  "adminFinance.hub.kicker", "adminFinance.hub.title",
  "adminFinance.stream.payments.title",
  "adminFinance.stream.financePlanning.description",
  "adminFinance.tax.checkpoint.source.title",
  "adminFinance.tax.handoff.title",
  "adminFinance.tax.boundary.noLedger.title"
];
for (const locale of expected) {
  for (const key of adminFinanceWorkspaceKeys) {
    if (!api.t(key, locale)) throw new Error(`Missing ${key} translation for ${locale}`);
  }
}

const adminSecurityAccessKeys = [
  "adminGeneric.securityAccess.state.loadingTitle",
  "adminGeneric.securityAccess.state.integrityGuardedTitle",
  "adminGeneric.securityAccess.metric.mfaRuntime.label",
  "adminGeneric.securityAccess.panel.rateLimit.title",
  "adminGeneric.securityAccess.boundary.0",
  "adminGeneric.securityAccess.route.securityTitle",
  "adminGeneric.securityAccess.route.accessDescription"
];
for (const locale of expected) {
  for (const key of adminSecurityAccessKeys) {
    if (!api.t(key, locale)) throw new Error(`Missing ${key} translation for ${locale}`);
  }
}

const adminAutomationMonitorKeys = [
  "adminGeneric.automationMonitor.state.loadingTitle",
  "adminGeneric.automationMonitor.scheduler.ready",
  "adminGeneric.automationMonitor.metric.inboxCenter.label",
  "adminGeneric.automationMonitor.aggregate.guardedTitle",
  "adminGeneric.automationMonitor.boundary.noControlPlane.title",
  "adminGeneric.automationMonitor.route.title",
  "adminGeneric.automationMonitor.route.description"
];
for (const locale of expected) {
  for (const key of adminAutomationMonitorKeys) {
    if (!api.t(key, locale)) throw new Error(`Missing ${key} translation for ${locale}`);
  }
}

const adminSystemStewardshipKeys = [
  "adminGeneric.systemStewardship.route.title",
  "adminGeneric.systemStewardship.route.description",
  "adminGeneric.systemStewardship.card.automation.title",
  "adminGeneric.systemStewardship.card.backups.description",
  "adminGeneric.systemStewardship.authority.canonical",
  "adminGeneric.systemStewardship.action.requiresCanonical",
  "adminGeneric.systemStewardship.intro.title",
  "adminGeneric.systemStewardship.section.local.title",
  "adminGeneric.systemStewardship.boundary.noDeploy.title"
];
for (const locale of expected) {
  for (const key of adminSystemStewardshipKeys) {
    if (!api.t(key, locale)) throw new Error(`Missing ${key} translation for ${locale}`);
  }
}

const reviewedAdminSecurityAccessCopy = {
  vi: {
    loadingTitle: "Đang xác minh Security & Access Posture",
    boundary: "Chỉ hiển thị aggregate Web-native; không có account, email, session, token, secret, IP hoặc audit detail."
  },
  en: {
    loadingTitle: "Verifying Security & Access Posture",
    boundary: "Only Web-native aggregates are shown; no accounts, emails, sessions, tokens, secrets, IP addresses, or audit details."
  },
  zh: {
    loadingTitle: "正在验证安全与访问态势",
    boundary: "仅显示 Web 原生汇总数据；不提供账户、邮箱、会话、令牌、密钥、IP 或审计详情。"
  }
};
for (const [locale, reviewed] of Object.entries(reviewedAdminSecurityAccessCopy)) {
  if (api.t("adminGeneric.securityAccess.state.loadingTitle", locale) !== reviewed.loadingTitle) {
    throw new Error(`Security loading copy diverged for ${locale}`);
  }
  if (api.t("adminGeneric.securityAccess.boundary.0", locale) !== reviewed.boundary) {
    throw new Error(`Security boundary copy diverged for ${locale}`);
  }
}

const reviewedAutomationMonitorCopy = {
  vi: "Đang xác minh receipt private",
  en: "Verifying the private receipt",
  zh: "正在验证私有回执"
};
for (const [locale, expectedCopy] of Object.entries(reviewedAutomationMonitorCopy)) {
  if (api.t("adminGeneric.automationMonitor.state.loadingTitle", locale) !== expectedCopy) {
    throw new Error(`Automation Monitor loading copy diverged for ${locale}`);
  }
}

const reviewedSystemStewardshipCopy = {
  vi: "System & Data Stewardship",
  en: "System & Data Stewardship",
  zh: "系统与数据治理"
};
for (const [locale, expectedCopy] of Object.entries(reviewedSystemStewardshipCopy)) {
  if (api.t("adminGeneric.systemStewardship.route.title", locale) !== expectedCopy) {
    throw new Error("System & Data Stewardship route copy diverged for " + locale);
  }
}

const customerAuthoringKeys = [
  "workspaceDrafts.page.title", "workspaceDrafts.page.description",
  "workspaceDrafts.filter.searchLabel", "workspaceDrafts.pagination.range",
  "workspaceDrafts.card.resume", "workspaceDrafts.boundary.title",
  "projectCenter.page.title", "projectCenter.page.description",
  "projectCenter.filter.searchLabel", "projectCenter.pagination.range",
  "projectCenter.authoring.createTitle", "projectCenter.guard.title",
  "project.page.title", "project.detail.title", "project.detail.documentsTitle",
  "project.document.kind.brief", "project.document.create", "project.boundary.title",
  "projectPackage.panel.title", "projectPackage.panel.create", "projectPackage.panel.emptyTitle"
];
for (const locale of expected) {
  for (const key of customerAuthoringKeys) {
    if (!api.t(key, locale)) throw new Error(`Missing ${key} translation for ${locale}`);
  }
}

if (api.normalizeLocale("zh-CN") !== "zh") throw new Error("Chinese display alias did not normalize");
if (api.normalizeLocale("zh-TW") !== "en") throw new Error("Traditional Chinese must not masquerade as Simplified Chinese");
if (api.normalizeLocale("ja") !== "en") throw new Error("Unreviewed interface locale did not fall back to English");
if (api.t("starter.install", "zh") !== "安装入门套件") throw new Error("Reviewed Chinese text is unavailable");
if (api.t("starter.install", "en") !== "Install Starter Kit") throw new Error("Reviewed English text is unavailable");
if (api.t("shellNav.contentStudio", "zh") !== "内容工作室") throw new Error("Reviewed Chinese App Shell text is unavailable");
if (api.t("shellNav.billing", "en") !== "Billing & plans") throw new Error("Reviewed English App Shell text is unavailable");
if (api.t("missing.translation.key", "vi") !== "") throw new Error("Unknown key must not invent a translation");
if (api.currentLocale() !== "zh") throw new Error("Server bootstrap interface locale did not win over profile fallback");
if (api.localeTag("zh") !== "zh-CN") throw new Error("Reviewed Chinese Intl tag is unavailable");
if (!api.formatNumber(1234567, "en") || !api.formatDateTime("2026-07-22T00:00:00Z", { timeZone: "UTC", year: "numeric", month: "short", day: "2-digit" }, "zh")) {
  throw new Error("Locale presentation helpers are unavailable");
}
if (api.compareText("10", "2", "en") <= 0) throw new Error("Locale collator did not use numeric presentation order");

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


def _node_portal_first_mount_snapshot() -> dict:
    """Mount the real Portal shell with only its signed locale bootstrap.

    This deliberately has no profile projection, matching the first server
    response before the authenticated integration performs `/auth/me`
    hydration.  A lightweight DOM shim is enough because the Portal renderer
    is presentation-only; it lets this contract catch a language flash that a
    static HTML or i18n-bundle test cannot observe.
    """

    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for the Portal first-mount locale contract")

    script = r'''
const fs = require("fs");
const vm = require("vm");
const i18nPath = process.argv[1];
const portalPath = process.argv[2];
const i18nSource = fs.readFileSync(i18nPath, "utf8");
const portalSource = fs.readFileSync(portalPath, "utf8");

function createClassList() {
  const values = new Set();
  return {
    add(...names) { names.forEach((name) => values.add(String(name))); },
    remove(...names) { names.forEach((name) => values.delete(String(name))); },
    contains(name) { return values.has(String(name)); },
    toggle(name, force) {
      const enabled = force === undefined ? !values.has(String(name)) : Boolean(force);
      if (enabled) values.add(String(name)); else values.delete(String(name));
      return enabled;
    }
  };
}

function createElement() {
  const attributes = {};
  return {
    hidden: false,
    innerHTML: "",
    textContent: "",
    dataset: {},
    classList: createClassList(),
    setAttribute(name, value) { attributes[name] = String(value); },
    getAttribute(name) { return attributes[name] || ""; },
    removeAttribute(name) { delete attributes[name]; },
    hasAttribute(name) { return Object.prototype.hasOwnProperty.call(attributes, name); },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    addEventListener() {},
    removeEventListener() {},
    matches() { return false; },
    closest() { return null; },
    focus() {}
  };
}

const bootstrap = createElement();
bootstrap.textContent = JSON.stringify({
  path: "/dashboard",
  title: "概览 · TOAN AAS",
  interfaceLocale: "zh",
  apiBase: "/api/v1",
  buildId: "local"
});
const sidebar = createElement();
const header = createElement();
const main = createElement();
const shell = createElement();
const mobileNav = createElement();
const commandPalette = createElement();
const skipLink = createElement();
const nodes = {
  "[data-portal-sidebar]": sidebar,
  "[data-portal-header]": header,
  "[data-portal-main]": main,
  "[data-portal-shell]": shell,
  "[data-portal-mobile-nav]": mobileNav,
  "[data-portal-command-palette]": commandPalette,
  ".skip-link": skipLink
};
let domReady = null;
const documentElement = {
  lang: "zh-CN",
  dir: "ltr",
  attributes: {},
  setAttribute(name, value) { this.attributes[name] = String(value); }
};
const document = {
  documentElement,
  body: createElement(),
  title: "概览 · TOAN AAS",
  readyState: "loading",
  activeElement: null,
  getElementById(id) { return id === "portal-bootstrap" ? bootstrap : null; },
  querySelector(selector) { return nodes[selector] || null; },
  querySelectorAll() { return []; },
  addEventListener(type, handler) { if (type === "DOMContentLoaded") domReady = handler; },
  createElement() { return createElement(); }
};
const context = {
  console,
  JSON,
  URL,
  URLSearchParams,
  Intl,
  document,
  location: { pathname: "/dashboard", search: "" },
  CustomEvent: function CustomEvent(type, init) { this.type = type; this.detail = init && init.detail; },
  HTMLElement: function HTMLElement() {},
  addEventListener() {},
  removeEventListener() {},
  dispatchEvent() { return true; },
  matchMedia() { return { matches: false }; },
  requestAnimationFrame(callback) { if (typeof callback === "function") callback(); return 0; }
};
context.window = context;
context.globalThis = context;
vm.createContext(context);
vm.runInContext(i18nSource, context, { filename: i18nPath });
vm.runInContext(portalSource, context, { filename: portalPath });
if (typeof domReady !== "function") throw new Error("Portal did not register a first mount");
domReady();
const firstMount = documentElement.attributes["data-portal-locale"];
const firstSidebar = sidebar.innerHTML;

context.TOANAASPortal.mount({ path: "/dashboard", interfaceLocale: "zh", profile: { locale: "en" } });
const hydratedProfile = documentElement.attributes["data-portal-locale"];
const englishSidebar = sidebar.innerHTML;

context.TOANAASPortal.mount({ path: "/dashboard", interfaceLocale: "zh", profile: { locale: "zh" } });
const chineseSidebar = sidebar.innerHTML;

context.TOANAASPortal.mount({ path: "/dashboard", interfaceLocale: "vi", profile: { locale: "vi" } });
const vietnameseSidebar = sidebar.innerHTML;
const vietnameseMain = main.innerHTML;

context.TOANAASPortal.mount({ path: "/dashboard", interfaceLocale: "zh", profile: { locale: "zh-TW" } });
const invalidProfile = documentElement.attributes["data-portal-locale"];
process.stdout.write(JSON.stringify({ firstMount, hydratedProfile, invalidProfile, documentLang: documentElement.lang, firstSidebar, englishSidebar, chineseSidebar, vietnameseSidebar, vietnameseMain }));
'''
    try:
        result = subprocess.run(
            [node, "-e", script, str(BUNDLE), str(PORTAL_BUNDLE)],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except OSError as exc:
        pytest.skip(f"Node subprocess is unavailable in this test runner: {exc}")
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout)


def _node_command_palette_filter_snapshot() -> dict:
    """Exercise the real filter helper with a minimal rendered palette.

    The shell's i18n catalogue stays browser-only, so this keeps the check in
    the same JavaScript runtime without importing the FastAPI application or
    creating a signed session.  It verifies the text a user sees after an
    actual query rather than merely checking source strings.
    """

    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for the command-palette filter contract")

    script = r'''
const fs = require("fs");
const sourcePath = process.argv[1];
const source = fs.readFileSync(sourcePath, "utf8");
function extract(start, end) {
  const offset = source.indexOf(start);
  if (offset < 0) throw new Error(`missing ${start}`);
  const finish = source.indexOf(end, offset + start.length);
  if (finish < 0) throw new Error(`missing end ${end}`);
  return source.slice(offset, finish);
}
const messages = {
  vi: {
    "chrome.commandCount": "{count} workspace có thể mở trong phiên này.",
    "chrome.commandEmpty": "Không tìm thấy workspace phù hợp. Hãy thử tên tính năng hoặc đường dẫn khác.",
    "chrome.adminCommandCount": "{count} mục ERP có thể mở trong phiên này.",
    "chrome.no_results": "Không tìm thấy kết quả."
  },
  en: {
    "chrome.commandCount": "{count} workspaces are available in this session.",
    "chrome.commandEmpty": "No matching workspace found. Try a feature name or another path.",
    "chrome.adminCommandCount": "{count} ERP destinations available in this session.",
    "chrome.no_results": "No results found."
  },
  zh: {
    "chrome.commandCount": "本次会话可打开 {count} 个工作台。",
    "chrome.commandEmpty": "未找到匹配的工作台。请尝试功能名称或其他路径。",
    "chrome.adminCommandCount": "此会话可打开 {count} 个 ERP 入口。",
    "chrome.no_results": "未找到结果。"
  }
};
let locale = "en";
let palette = null;
function uiText(key, fallback, params) {
  const raw = (messages[locale] && messages[locale][key]) || fallback;
  return String(raw).replace(/\{count\}/g, String(params && params.count !== undefined ? params.count : ""));
}
const document = { querySelector(selector) { return selector === "[data-portal-command-palette]" ? palette : null; } };
const runtime = [
  extract("function normalizeCommandSearch(value)", "function commandPaletteItems(context, page)"),
  extract("function filterCommandPalette(value)", "function closeCommandPalette(options)")
].join("\n");
eval(runtime);
function item(search) {
  return { hidden: false, getAttribute(name) { return name === "data-command-search" ? search : ""; } };
}
function run(activeLocale, surface, query) {
  locale = activeLocale;
  const empty = { hidden: true, textContent: "" };
  const count = { textContent: "" };
  const commandSurface = { getAttribute(name) { return name === "data-portal-command-surface" ? surface : ""; } };
  const items = [item("dashboard overview"), item("asset vault")];
  palette = {
    hidden: false,
    querySelector(selector) {
      if (selector === "[data-portal-command-empty]") return empty;
      if (selector === "[data-portal-command-count]") return count;
      if (selector === "[data-portal-command-surface]") return commandSurface;
      return null;
    },
    querySelectorAll(selector) { return selector === "[data-portal-command-item]" ? items : []; }
  };
  filterCommandPalette(query);
  return { count: count.textContent, emptyHidden: empty.hidden, visible: items.filter((entry) => !entry.hidden).length };
}
process.stdout.write(JSON.stringify({
  customerEnMatch: run("en", "customer", "dashboard"),
  customerEnEmpty: run("en", "customer", "missing"),
  customerViEmpty: run("vi", "customer", "missing"),
  customerZhEmpty: run("zh", "customer", "missing"),
  adminEnEmpty: run("en", "admin", "missing"),
  adminZhEmpty: run("zh", "admin", "missing")
}));
'''
    try:
        result = subprocess.run(
            [node, "-e", script, str(PORTAL_BUNDLE)],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except OSError as exc:
        pytest.skip(f"Node subprocess is unavailable in this test runner: {exc}")
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout)


def test_i18n_bundle_has_equal_reviewed_vi_en_zh_coverage_at_runtime() -> None:
    snapshot = _node_i18n_snapshot()
    assert snapshot["locales"] == ["vi", "en", "zh"]
    assert snapshot["keyCount"] >= 100
    assert snapshot["activeLocale"] == "en"
    assert snapshot["documentLocale"] == "en"


def test_admin_and_table_chrome_have_reviewed_vi_en_zh_copy() -> None:
    source = BUNDLE.read_text(encoding="utf-8")
    expected = {
        "table.horizontalScroll.region": (
            "Bảng dữ liệu có thể cuộn ngang. Dùng phím mũi tên trái và phải để xem toàn bộ cột.",
            "This data table scrolls horizontally. Use the Left and Right Arrow keys to view all columns.",
            "此数据表可水平滚动。使用左右箭头键查看所有列。",
        ),
        "table.horizontalScroll.hint": (
            "Cuộn ngang để xem các cột còn lại.",
            "Scroll horizontally to view the remaining columns.",
            "水平滚动以查看其余列。",
        ),
        "adminHome.directory.title": (
            "Danh mục Admin ERP",
            "Admin ERP directory",
            "Admin ERP 目录",
        ),
        "adminHome.queues.support.title": (
            "Chăm sóc khách hàng & Hỗ trợ",
            "Customer support",
            "客户支持",
        ),
        "adminHome.readiness.refresh": ("Làm mới", "Refresh", "刷新"),
        "chrome.customerAppCaption": ("Không gian làm việc AI", "AI workspace", "AI 工作台"),
        "chrome.adminAppCaption": ("Trung tâm quản trị", "System administration", "系统管理"),
        "chrome.searchAdmin": ("Tìm điều hướng ERP", "Search ERP navigation", "搜索 ERP 导航"),
        "chrome.adminCommandCount": (
            "{count} mục ERP có thể mở trong phiên này.",
            "{count} ERP destinations available in this session.",
            "此会话可打开 {count} 个 ERP 入口。",
        ),
    }
    for key, translations in expected.items():
        for translation in translations:
            assert f'"{key}": "{translation}"' in source


def test_customer_sidebar_and_command_palette_follow_the_reviewed_interface_locale() -> None:
    """Signed customer chrome must not fall back to Vietnamese after locale change."""

    source = BUNDLE.read_text(encoding="utf-8")
    expected = {
        "app.workspace": ("TOAN AAS Không gian làm việc", "TOAN AAS Workspace", "TOAN AAS 工作台"),
        "chrome.commandEmpty": (
            "Không tìm thấy không gian làm việc phù hợp. Hãy thử tên tính năng hoặc đường dẫn khác.",
            "No matching workspace found. Try a feature name or another path.",
            "未找到匹配的工作台。请尝试功能名称或其他路径。",
        ),
        "chrome.commandCount": (
            "{count} không gian làm việc có thể mở trong phiên này.",
            "{count} workspaces are available in this session.",
            "本次会话可打开 {count} 个工作台。",
        ),
    }
    for key, translations in expected.items():
        for translation in translations:
            assert f'"{key}": "{translation}"' in source

    sidebar = _between(PORTAL, "function renderSidebar(page, context)", "function renderHeader(page, context)")
    command_filter = _between(PORTAL, "function filterCommandPalette(value)", "function closeCommandPalette(options)")

    assert 'uiText("chrome.customerAppCaption", "Không gian làm việc AI")' in sidebar
    assert 'uiText("chrome.adminAppCaption", "Trung tâm quản trị")' in sidebar
    assert 'uiText("app.workspace", "TOAN AAS Workspace")' not in sidebar
    assert 'uiText("chrome.commandCount"' in command_filter


def test_command_palette_filter_localizes_match_and_empty_counts_for_customer_and_admin() -> None:
    snapshot = _node_command_palette_filter_snapshot()

    assert snapshot["customerEnMatch"] == {
        "count": "1 workspaces are available in this session.",
        "emptyHidden": True,
        "visible": 1,
    }
    assert snapshot["customerEnEmpty"] == {
        "count": "0 workspaces are available in this session.",
        "emptyHidden": False,
        "visible": 0,
    }
    assert snapshot["customerViEmpty"]["count"] == "0 workspace có thể mở trong phiên này."
    assert snapshot["customerZhEmpty"]["count"] == "本次会话可打开 0 个工作台。"
    assert snapshot["adminEnEmpty"]["count"] == "0 ERP destinations available in this session."
    assert snapshot["adminZhEmpty"]["count"] == "此会话可打开 0 个 ERP 入口。"


def test_customer_authoring_uses_reviewed_copy_without_translating_records() -> None:
    """Workspace and Project UI copy is localised; customer records stay data."""

    source = BUNDLE.read_text(encoding="utf-8")
    expected = {
        "workspaceDrafts.page.title": ("Bản nháp Workspace", "Workspace drafts", "工作台草稿"),
        "workspaceDrafts.filter.searchLabel": ("Tìm bản nháp", "Search drafts", "搜索草稿"),
        "workspaceDrafts.card.resume": ("Tiếp tục brief", "Continue brief", "继续简报"),
        "workspaceDrafts.card.attach": ("Đưa vào Project", "Add to Project", "加入项目"),
        "workspaceDrafts.card.attachProjectLabel": ("Đưa vào Project", "Add to Project", "加入项目"),
        "projectCenter.page.title": ("Project Operations Board", "Project Operations Board", "项目运营看板"),
        "projectCenter.filter.searchLabel": ("Tìm Project", "Search projects", "搜索项目"),
        "projectCenter.authoring.createTitle": ("Tạo Project", "Create a project", "创建项目"),
        "project.page.title": ("Project Workspace", "Project Workspace", "项目工作区"),
        "project.detail.documentsTitle": ("Studio Documents", "Studio Documents", "工作室文档"),
        "project.document.create": ("Thêm Studio Document", "Add Studio Document", "添加工作室文档"),
        "projectPackage.panel.title": ("Project Packages", "Project Packages", "项目套餐"),
    }
    for key, translations in expected.items():
        for translation in translations:
            assert f'"{key}": "{translation}"' in source

    workspace = _between(PORTAL, "function workspaceDraftText", "const PROJECT_DOCUMENT_KINDS")
    project_center = _between(PORTAL, "function projectCenterText", "// Memory Center")
    project_detail = _between(PORTAL, "function renderProjectDetail", "function renderFeatureFamily")
    project_packages = _between(PORTAL, "function projectPackageText", "function renderProjectPackages")
    page_titles = _between(PORTAL, "function localizedPageTitle", "function documentTitle")
    page_descriptions = _between(PORTAL, "function localizedPageDescription", "function initials")

    assert "function workspaceDraftText" in workspace
    assert "workspaceDraftText(" in workspace
    assert "function projectCenterText" in project_center
    assert "projectCenterText(" in project_center
    assert "function projectText" in project_center
    assert "projectText(" in project_center + project_detail
    assert "function projectPackageText" in project_packages
    assert "projectPackageText(" in project_packages
    assert 'path === "/workspace"' in page_titles
    assert 'path === "/projects"' in page_titles
    assert "path.startsWith(\"/projects/\")" in page_titles
    assert 'path === "/workspace"' in page_descriptions
    assert 'path === "/projects"' in page_descriptions
    # Dynamic titles/briefs/documents remain server/customer data and are
    # escaped for presentation rather than sent through the UI catalog.
    assert 'safeText(String(project.title ||' in project_detail
    assert 'safeText(String(project.summary ||' in project_detail
    assert 'safeText(String(document.title ||' in project_detail


def test_customer_authoring_first_paint_titles_are_reviewed_for_all_locales() -> None:
    titles = _between(PAGES, "_PORTAL_SHELL_TITLES = {", "}\n\n\ndef _safe_portal_build_id")
    assert '"/workspace": {"vi": "Bản nháp Workspace · TOAN AAS", "en": "Workspace drafts · TOAN AAS", "zh": "工作台草稿 · TOAN AAS"}' in titles
    shell_titles = _between(PAGES, "def _shell_title_for", "\n\ndef _fallback_template")
    assert "if PROJECT_PATH.fullmatch(normalized):" in shell_titles
    for title in ("Project Workspace · TOAN AAS", "项目工作区 · TOAN AAS"):
        assert title in shell_titles


def test_customer_authoring_has_no_untranslated_nested_or_package_surface() -> None:
    """A Project flow stays localised through its editor, notes, and package library."""

    source = BUNDLE.read_text(encoding="utf-8")
    expected = {
        "projectCenter.notes.integrationTitle": ("Trạng thái tích hợp", "Integration status", "集成状态"),
        "project.editor.title": ("Studio Document editor", "Studio Document editor", "工作室文档编辑器"),
        "project.editor.save": ("Lưu phiên bản mới", "Save new version", "保存新版本"),
        "projectPackage.page.title": ("Project Packages", "Project Packages", "项目套餐"),
        "projectPackage.page.guardTitle": ("Project Packages chưa được bật", "Project Packages are not enabled", "项目套餐尚未启用"),
        "projectPackage.page.historyTitle": ("Lịch sử Project Packages", "Project Package history", "项目套餐历史"),
    }
    for key, translations in expected.items():
        for translation in translations:
            assert f'"{key}": "{translation}"' in source

    editor = _between(PORTAL, "function renderStudioDocumentEditor", "function validProjectPackageId")
    project_center = _between(PORTAL, "function projectCenterText", "// Memory Center")
    package_surface = _between(PORTAL, "function renderProjectPackages", "function renderProjectDetail")
    page_titles = _between(PORTAL, "function localizedPageTitle", "function documentTitle")
    page_descriptions = _between(PORTAL, "function localizedPageDescription", "function initials")

    assert "projectText(" in editor
    assert "projectKindLabel(" in editor
    assert "renderProjectCenterNotes(" in project_center
    assert "projectPackageText(" in package_surface
    assert 'path === "/project-packages"' in page_titles
    assert 'path === "/project-packages"' in page_descriptions

    titles = _between(PAGES, "_PORTAL_SHELL_TITLES = {", "}\n\n\ndef _safe_portal_build_id")
    assert '"/project-packages": {"vi": "Project Packages · TOAN AAS", "en": "Project Packages · TOAN AAS", "zh": "项目套餐 · TOAN AAS"}' in titles


def test_portal_first_mount_keeps_signed_server_locale_until_profile_hydration() -> None:
    snapshot = _node_portal_first_mount_snapshot()
    assert snapshot["firstMount"] == "zh"
    assert snapshot["hydratedProfile"] == "en"
    assert snapshot["invalidProfile"] == "zh"
    assert snapshot["documentLang"] == "zh-CN"
    assert "工作台" in snapshot["firstSidebar"]
    assert "新建" in snapshot["firstSidebar"]
    assert "钱包与套餐" in snapshot["firstSidebar"]
    assert "Workspace" in snapshot["englishSidebar"]
    assert "Create" in snapshot["englishSidebar"]
    assert "Billing &amp; plans" in snapshot["englishSidebar"]
    assert "Không gian làm việc" in snapshot["vietnameseSidebar"]
    assert "Workspace" not in snapshot["vietnameseSidebar"]
    assert "Tạo mới" in snapshot["vietnameseSidebar"]
    assert "Ví &amp; gói" in snapshot["vietnameseSidebar"]
    assert "AI 工作台" in snapshot["firstSidebar"]
    assert "AI workspace" in snapshot["englishSidebar"]
    assert "Không gian làm việc AI" in snapshot["vietnameseSidebar"]
    assert "AI 工作台" in snapshot["chineseSidebar"]


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
        assert 'lang="__PORTAL_HTML_LANG__"' in shell
        assert 'data-portal-locale="__PORTAL_LOCALE__"' in shell

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
    assert '"/account/interface-language"' not in shell_cache
    assert '"/account/interface-language"' not in public_navigation


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
    for disallowed_interface_value in ('value: "zh_cn"', 'value: "ja"', 'value: "ko"', 'value: "th"', 'value: "ar"', 'value: "auto"'):
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
        'uiText("mobile.home"',
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
    assert 'const copy = (key, fallback, params) => accountCenterText(`profile.${key}`, fallback, params);' in account
    for required in ('copy("displayNameLabel"', 'copy("editorTitle"', 'copy("editorSave"'):
        assert required in account
    for required in ('uiText("setup.role"', 'uiText("setup.focusTitle"', 'uiText("setup.saveAndEnter"'):
        assert required in setup
    for required in ('uiText("starter.catalogTitle"', 'uiText("starter.confirmationTitle"', 'uiText("starter.scopeTitle"'):
        assert required in starter


def test_app_shell_navigation_uses_the_reviewed_locale_catalogue() -> None:
    navigation = _between(PORTAL, "const NAVIGATION_I18N_KEYS", "function localizedNavigationLabel")
    localized_navigation = _between(PORTAL, "function localizedNavigationLabel", "function localizedPageTitle")
    command_palette = _between(PORTAL, "function commandPaletteItems", "function renderCommandPalette")
    static_navigation = _between(PORTAL, "function navGroups", "function matchesRouteFamily")

    for label, key in (
        ("Tài sản", "nav.assets"),
        ("Ví & gói", "shellNav.billing"),
        ("Content Studio", "shellNav.contentStudio"),
        ("Image Operations Hub", "shellNav.imageOperationsHub"),
        ("Automation Center", "shellNav.automationCenter"),
        ("Script-to-Screen & Phim dài tập", "shellNav.scriptToSeries"),
    ):
        assert f'"{label}": "{key}"' in navigation

    assert 'source.startsWith("ERP · ")' in localized_navigation
    assert 'uiText("shellNav.erp", "ERP")' in localized_navigation
    assert 'title: localizedNavigationLabel(String(candidate.title || "TOAN AAS"))' in command_palette
    assert 'section: localizedNavigationLabel(String(candidate.section || "Workspace"))' in command_palette
    assert ".portal-nav-link > span:not(.portal-nav-icon)" in PORTAL_CSS
    assert "overflow-wrap: anywhere;" in PORTAL_CSS

    static_labels = set(re.findall(r'\["/[^"\n]+", "([^"]+)", ICONS\.', static_navigation))
    static_labels.update(re.findall(r'^\s*label: "([^"]+)"', static_navigation, flags=re.MULTILINE))
    unmapped_labels = sorted(
        label for label in static_labels
        if f'"{label}": ' not in navigation
    )
    assert not unmapped_labels, f"Static App Shell labels missing i18n keys: {unmapped_labels}"


def test_vietnamese_shell_dashboard_and_admin_navigation_copy_is_clear() -> None:
    snapshot = _node_portal_first_mount_snapshot()
    visible_html = snapshot["vietnameseSidebar"] + " " + snapshot["vietnameseMain"]
    visible_text = html.unescape(re.sub(r"<[^>]+>", " ", visible_html))
    visible_text = re.sub(r"\s+", " ", visible_text).strip()

    for token in (
        "Workspace", "Project", "Projects", "Web-owned", "workflow", "brief",
        "canonical", "signed", "authoring", "version", "Studio", "Job", "Ticket",
        "Prompt", "Estimate", "consent", "contract", "delivery", "provider", "output",
        "role", "browser", "server",
    ):
        assert not re.search(rf"\b{re.escape(token)}\b", visible_text, re.IGNORECASE), token

    for label in (
        "Không gian làm việc", "Nội dung & Trò chuyện", "Công cụ nội dung",
        "Công cụ hình ảnh", "Hạng hội viên", "Yêu cầu hỗ trợ của tôi",
    ):
        assert label in visible_text

    group_map = _between(PORTAL, "const ADMIN_ERP_GROUP_I18N", "const ADMIN_ERP_ROUTE_I18N")
    route_map = _between(PORTAL, "const ADMIN_ERP_ROUTE_I18N", "function adminErpGroupText")
    admin_normalizer = _between(PORTAL, "function adminErpNavigation(context)", "function adminRouteIcon(route)")

    for group_id in (
        "support_operations", "web_private_crm", "web_finance_operations_planning",
        "web_governance_documents", "web_internal_document_archive", "web_automation_monitor",
        "web_system_stewardship", "web_security_access_posture", "command_center", "commerce",
        "delivery_runtime", "content_growth", "governance",
    ):
        assert f'"{group_id}"' in group_map

    for route in (
        "/admin", "/admin/access", "/admin/analytics", "/admin/approvals", "/admin/audit",
        "/admin/automation", "/admin/backups", "/admin/calendar", "/admin/campaigns",
        "/admin/content-handoffs", "/admin/crm/leads", "/admin/customers", "/admin/features",
        "/admin/finance", "/admin/finance/planning", "/admin/finance/tax-readiness",
        "/admin/freezes", "/admin/governance", "/admin/growth", "/admin/growth/postback-readiness",
        "/admin/internal-documents", "/admin/job-recovery-guide", "/admin/jobs", "/admin/jobs/failed",
        "/admin/leads", "/admin/operations", "/admin/packages", "/admin/payments", "/admin/pricing",
        "/admin/promos", "/admin/provider-cost", "/admin/providers", "/admin/publishing",
        "/admin/refunds", "/admin/reliability", "/admin/reports", "/admin/revenue", "/admin/runtime",
        "/admin/security", "/admin/support", "/admin/system", "/admin/system-stewardship",
        "/admin/tickets", "/admin/topups", "/admin/trends", "/admin/users", "/admin/wallet",
        "/admin/workers", "/admin/work-queue",
    ):
        assert f'"{route}"' in route_map

    assert 'adminDeliveryRuntimeNavigationText(route, "title", moduleTitle)' in admin_normalizer
    assert 'adminDeliveryRuntimeGroupText(id, "title", title)' in admin_normalizer
    assert 'if (field === "title") return adminErpRouteText(route, fallback);' in PORTAL
    assert 'if (field === "title") return adminErpGroupText(groupId, fallback);' in PORTAL

    source = BUNDLE.read_text(encoding="utf-8")
    admin_vi = _between(source, "  const ADMIN_HOME_MESSAGES = {\n    vi: {", "    },\n    en: {")
    admin_vi_copy = " ".join(re.findall(r':\s*"((?:[^"\\]|\\.)*)"', admin_vi))
    for token in (
        "capability", "Core Bridge", "shell", "Client route", "FastAPI", "signed", "canonical",
        "render", "role check", "queue", "ledger", "Support", "Case", "triage", "Job", "Payment",
        "topup", "refund", "Audit", "Governance", "readiness", "Adapter", "module",
    ):
        assert token not in admin_vi_copy
