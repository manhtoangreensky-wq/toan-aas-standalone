import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import vm from "node:vm";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const PORTAL = readFileSync(join(ROOT, "static/portal/portal.js"), "utf8");
const I18N_SRC = readFileSync(join(ROOT, "static/portal/portal-i18n.js"), "utf8");

const start = PORTAL.indexOf("const ADMIN_TAB_GROUPS = [");
const end = PORTAL.indexOf("function renderAdminModuleTabs", start);
assert.ok(start >= 0 && end > start, "Admin tab catalogue must remain present");
const catalogue = PORTAL.slice(start, end);

test("Vietnamese Admin module tabs do not leak generic English UI terms", () => {
  const labels = [...catalogue.matchAll(/\blabel:\s*"([^"]+)"/g)].map((match) => match[1]);
  assert.ok(labels.length >= 40, `expected the complete Admin tab catalogue, found ${labels.length}`);
  const genericEnglish = /\b(?:Autopilot|Leads|Support Desk|Tickets|Jobs|Automation Monitor|Providers?|Workers|Runtime|Features|Freeze|Packages|Promo|Analytics|Affiliate|System Stewardship|Audit)\b/i;
  assert.deepEqual(labels.filter((label) => genericEnglish.test(label)), [], "VI labels must be translated; keep product/acronym names only when intentional");
});

test("English Admin module tab labels remain explicit", () => {
  const labels = [...catalogue.matchAll(/\blabelEn:\s*"([^"]+)"/g)].map((match) => match[1]);
  assert.ok(labels.length >= 40, `expected the complete English Admin tab catalogue, found ${labels.length}`);
  assert.ok(labels.includes("Analytics"));
  assert.ok(labels.includes("Provider Cost"));
  assert.ok(labels.includes("System"));
});

function fn(name) {
  const a = PORTAL.indexOf(`  function ${name}(`);
  const b = PORTAL.indexOf('\n  }', a) + 4;
  assert.ok(a >= 0 && b > a, `Function ${name} must be present`);
  return PORTAL.slice(a, b);
}

const routeMapStart = PORTAL.indexOf("  const ADMIN_ERP_ROUTE_I18N = Object.freeze({");
const routeMapEnd = PORTAL.indexOf("  function adminErpGroupText(", routeMapStart);
assert.ok(routeMapStart >= 0 && routeMapEnd > routeMapStart, "ADMIN_ERP_ROUTE_I18N must be present");
const routeMapCode = PORTAL.slice(routeMapStart, routeMapEnd);

const groupsStart = PORTAL.indexOf("  const ADMIN_TAB_GROUPS = [");
const groupsEnd = PORTAL.indexOf("  function renderAdminModuleTabs(", groupsStart);
assert.ok(groupsStart >= 0 && groupsEnd > groupsStart, "ADMIN_TAB_GROUPS must be present");
const groupsCode = PORTAL.slice(groupsStart, groupsEnd);

const SPECIAL_LABELS = {
  "/admin/commercial": {
    vi: "Trung tâm thương mại",
    en: "Commercial center",
    zh: "商务中心",
  },
  "/legal": {
    vi: "Pháp lý & quyền riêng tư",
    en: "Legal & privacy",
    zh: "法律与隐私",
  },
};

const ARIA_LABELS = {
  vi: "Phân hệ nghiệp vụ",
  en: "Module sections",
  zh: "业务模块",
};

function parseTabs(html) {
  const navMatch = html.match(/<nav\s+class="portal-admin-tabs"\s+aria-label="([^"]*)">/);
  const ariaLabel = navMatch ? navMatch[1] : null;
  const tabRegex = /<a\s+class="([^"]*)"\s+href="([^"]*)"(?:\s+aria-current="([^"]*)")?>([\s\S]*?)<\/a>/g;
  const tabs = [];
  let m;
  while ((m = tabRegex.exec(html)) !== null) {
    tabs.push({
      class: m[1],
      href: m[2],
      ariaCurrent: m[3] || null,
      label: m[4],
    });
  }
  return { ariaLabel, tabs };
}

function getExpectedLabel(path, locale, routeMap, messages) {
  if (SPECIAL_LABELS[path]) {
    return SPECIAL_LABELS[path][locale];
  }
  const i18nKey = routeMap[path];
  assert.ok(i18nKey, `Route ${path} must be present in ADMIN_ERP_ROUTE_I18N`);
  const text = messages[locale] && messages[locale][i18nKey];
  assert.ok(text, `Translation key ${i18nKey} must exist for locale ${locale}`);
  return text;
}

function makeContext(targetLocale, allowedRoutes, path) {
  const wrongLocale = targetLocale === "en" ? "vi" : "en";
  return {
    profile: { locale: targetLocale },
    interfaceLocale: targetLocale,
    locale: wrongLocale,
    allowedRoutes,
    path,
  };
}

function createHarness(targetLocale) {
  const ctx = {
    console,
    Intl,
    Set,
    Map,
    Array,
    Object,
    String,
    Boolean,
    Number,
    RegExp,
  };
  ctx.window = ctx;
  ctx.globalThis = ctx;
  ctx.location = { pathname: "/admin/pricing" };
  vm.createContext(ctx);

  vm.runInContext(I18N_SRC, ctx);

  if (ctx.TOANAASI18n && typeof ctx.TOANAASI18n.setLocale === "function") {
    ctx.TOANAASI18n.setLocale(targetLocale, { emit: false });
  }

  ctx.adminErpNavigation = (context) => ({
    routes: new Set(context && context.allowedRoutes ? context.allowedRoutes : []),
  });

  ctx.uiText = (key, fallback, params) =>
    ctx.TOANAASI18n.has(key) ? ctx.TOANAASI18n.t(key, params, targetLocale) : fallback;

  const code = [
    routeMapCode,
    groupsCode,
    fn("safeText"),
    fn("normalizePath"),
    fn("portalI18n"),
    fn("reviewedInterfaceLocale"),
    fn("interfaceLocaleFor"),
    fn("adminErpRouteText"),
    fn("renderAdminModuleTabs"),
    "globalThis.ADMIN_TAB_GROUPS = ADMIN_TAB_GROUPS;",
    "globalThis.ADMIN_ERP_ROUTE_I18N = ADMIN_ERP_ROUTE_I18N;",
  ].join("\n\n");

  vm.runInContext(code, ctx);

  return {
    groups: ctx.ADMIN_TAB_GROUPS,
    routeMap: ctx.ADMIN_ERP_ROUTE_I18N,
    renderTabs: (page, context) => ctx.renderAdminModuleTabs(page, context),
    safeText: ctx.safeText,
    messages: ctx.TOANAASI18n.messages,
  };
}

test("Vietnamese admin module tabs render all 9 groups with native catalogue labels and aria-label", () => {
  const harness = createHarness("vi");
  for (const group of harness.groups) {
    const allowedRoutes = group.tabs.map((t) => t.path);
    const activeRoute = group.tabs[0].path;
    const page = { routePath: activeRoute };
    const context = makeContext("vi", allowedRoutes, activeRoute);
    const html = harness.renderTabs(page, context);

    const { ariaLabel, tabs } = parseTabs(html);
    assert.equal(ariaLabel, harness.safeText(ARIA_LABELS.vi));
    assert.equal(tabs.length, group.tabs.length);

    group.tabs.forEach((expectedTab, index) => {
      const rendered = tabs[index];
      assert.equal(rendered.href, expectedTab.path);
      const expectedLabel = getExpectedLabel(expectedTab.path, "vi", harness.routeMap, harness.messages);
      assert.equal(rendered.label, harness.safeText(expectedLabel));

      if (index === 0) {
        assert.ok(rendered.class.includes("is-active"));
        assert.equal(rendered.ariaCurrent, "page");
      } else {
        assert.ok(!rendered.class.includes("is-active"));
        assert.equal(rendered.ariaCurrent, null);
      }
    });
  }
});

test("English admin module tabs render all 9 groups with native catalogue labels and aria-label without Vietnamese leaks", () => {
  const harness = createHarness("en");
  const vietnameseLeak = /\b(?:Tổng quan|Khách hàng|Đầu mối|Vận hành|Độ ổn định|Tài chính|Kinh doanh|Quản trị|Bàn hỗ trợ|Phiếu hỗ trợ|Tác vụ|Hàng bàn giao|Giám sát|Sổ tay|Nhà cung cấp|Tiến trình|Môi trường chạy|Tính năng|Bảo trì|Đóng băng|Hoàn tiền|Đối soát|Kế hoạch|Chuẩn bị|Chiến dịch|Lịch nội dung|Hàng duyệt|Xuất bản|Tăng trưởng|Xu hướng|Hệ thống|An ninh|Quyền truy cập|Nhật ký|Báo cáo|Sao lưu|Kho tài liệu|Kho hồ sơ|Pháp lý|Riêng tư)\b/i;

  for (const group of harness.groups) {
    const allowedRoutes = group.tabs.map((t) => t.path);
    const activeRoute = group.tabs[0].path;
    const page = { routePath: activeRoute };
    const context = makeContext("en", allowedRoutes, activeRoute);
    const html = harness.renderTabs(page, context);

    const { ariaLabel, tabs } = parseTabs(html);
    assert.equal(ariaLabel, harness.safeText(ARIA_LABELS.en));
    assert.ok(!vietnameseLeak.test(ariaLabel), "Aria label must not leak Vietnamese");
    assert.equal(tabs.length, group.tabs.length);

    group.tabs.forEach((expectedTab, index) => {
      const rendered = tabs[index];
      assert.equal(rendered.href, expectedTab.path);
      const expectedLabel = getExpectedLabel(expectedTab.path, "en", harness.routeMap, harness.messages);
      assert.equal(rendered.label, harness.safeText(expectedLabel));
      assert.ok(!vietnameseLeak.test(rendered.label), `EN tab ${expectedTab.path} must not leak Vietnamese: ${rendered.label}`);

      if (index === 0) {
        assert.ok(rendered.class.includes("is-active"));
        assert.equal(rendered.ariaCurrent, "page");
      } else {
        assert.ok(!rendered.class.includes("is-active"));
        assert.equal(rendered.ariaCurrent, null);
      }
    });
  }
});

test("Chinese admin module tabs render all 9 groups with native catalogue labels and aria-label", () => {
  const harness = createHarness("zh");
  const vietnameseLeak = /\b(?:Tổng quan|Khách hàng|Đầu mối|Vận hành|Độ ổn định|Tài chính|Kinh doanh|Quản trị|Bàn hỗ trợ|Phiếu hỗ trợ|Tác vụ|Hàng bàn giao|Giám sát|Sổ tay|Nhà cung cấp|Tiến trình|Môi trường chạy|Tính năng|Bảo trì|Đóng băng|Hoàn tiền|Đối soát|Kế hoạch|Chuẩn bị|Chiến dịch|Lịch nội dung|Hàng duyệt|Xuất bản|Tăng trưởng|Xu hướng|Hệ thống|An ninh|Quyền truy cập|Nhật ký|Báo cáo|Sao lưu|Kho tài liệu|Kho hồ sơ|Pháp lý|Riêng tư)\b/i;

  for (const group of harness.groups) {
    const allowedRoutes = group.tabs.map((t) => t.path);
    const activeRoute = group.tabs[0].path;
    const page = { routePath: activeRoute };
    const context = makeContext("zh", allowedRoutes, activeRoute);
    const html = harness.renderTabs(page, context);

    const { ariaLabel, tabs } = parseTabs(html);
    assert.equal(ariaLabel, harness.safeText(ARIA_LABELS.zh));
    assert.ok(!vietnameseLeak.test(ariaLabel), "Aria label must not leak Vietnamese");
    assert.equal(tabs.length, group.tabs.length);

    group.tabs.forEach((expectedTab, index) => {
      const rendered = tabs[index];
      assert.equal(rendered.href, expectedTab.path);
      const expectedLabel = getExpectedLabel(expectedTab.path, "zh", harness.routeMap, harness.messages);
      assert.equal(rendered.label, harness.safeText(expectedLabel));
      assert.ok(!vietnameseLeak.test(rendered.label), `ZH tab ${expectedTab.path} must not leak Vietnamese: ${rendered.label}`);

      if (index === 0) {
        assert.ok(rendered.class.includes("is-active"));
        assert.equal(rendered.ariaCurrent, "page");
      } else {
        assert.ok(!rendered.class.includes("is-active"));
        assert.equal(rendered.ariaCurrent, null);
      }
    });
  }
});

test("Vietnamese Pricing view renders only authorized routes /admin/pricing and /admin/packages with active state and localized copy", () => {
  const harness = createHarness("vi");
  const allowedRoutes = ["/admin/pricing", "/admin/packages"];
  const page = { routePath: "/admin/pricing" };
  const context = makeContext("vi", allowedRoutes, "/admin/pricing");
  const html = harness.renderTabs(page, context);

  const { ariaLabel, tabs } = parseTabs(html);
  assert.equal(ariaLabel, harness.safeText(ARIA_LABELS.vi));
  assert.equal(tabs.length, 2);
  assert.deepEqual(tabs.map((t) => t.href), ["/admin/pricing", "/admin/packages"]);

  assert.ok(tabs[0].class.includes("is-active"));
  assert.equal(tabs[0].ariaCurrent, "page");
  assert.equal(tabs[0].label, harness.safeText(getExpectedLabel("/admin/pricing", "vi", harness.routeMap, harness.messages)));

  assert.ok(!tabs[1].class.includes("is-active"));
  assert.equal(tabs[1].ariaCurrent, null);
  assert.equal(tabs[1].label, harness.safeText(getExpectedLabel("/admin/packages", "vi", harness.routeMap, harness.messages)));

  assert.ok(!tabs.some((t) => t.href === "/admin/commercial"));
  assert.ok(!tabs.some((t) => t.href === "/admin/promos"));
});

test("English Pricing view renders only authorized routes /admin/pricing and /admin/packages with active state and localized copy", () => {
  const harness = createHarness("en");
  const allowedRoutes = ["/admin/pricing", "/admin/packages"];
  const page = { routePath: "/admin/pricing" };
  const context = makeContext("en", allowedRoutes, "/admin/pricing");
  const html = harness.renderTabs(page, context);

  const { ariaLabel, tabs } = parseTabs(html);
  assert.equal(ariaLabel, harness.safeText(ARIA_LABELS.en));
  assert.equal(tabs.length, 2);
  assert.deepEqual(tabs.map((t) => t.href), ["/admin/pricing", "/admin/packages"]);

  assert.ok(tabs[0].class.includes("is-active"));
  assert.equal(tabs[0].ariaCurrent, "page");
  assert.equal(tabs[0].label, harness.safeText(getExpectedLabel("/admin/pricing", "en", harness.routeMap, harness.messages)));

  assert.ok(!tabs[1].class.includes("is-active"));
  assert.equal(tabs[1].ariaCurrent, null);
  assert.equal(tabs[1].label, harness.safeText(getExpectedLabel("/admin/packages", "en", harness.routeMap, harness.messages)));

  assert.ok(!tabs.some((t) => t.href === "/admin/commercial"));
  assert.ok(!tabs.some((t) => t.href === "/admin/promos"));
});

test("Chinese Pricing view renders only authorized routes /admin/pricing and /admin/packages with active state and localized copy", () => {
  const harness = createHarness("zh");
  const allowedRoutes = ["/admin/pricing", "/admin/packages"];
  const page = { routePath: "/admin/pricing" };
  const context = makeContext("zh", allowedRoutes, "/admin/pricing");
  const html = harness.renderTabs(page, context);

  const { ariaLabel, tabs } = parseTabs(html);
  assert.equal(ariaLabel, harness.safeText(ARIA_LABELS.zh));
  assert.equal(tabs.length, 2);
  assert.deepEqual(tabs.map((t) => t.href), ["/admin/pricing", "/admin/packages"]);

  assert.ok(tabs[0].class.includes("is-active"));
  assert.equal(tabs[0].ariaCurrent, "page");
  assert.equal(tabs[0].label, harness.safeText(getExpectedLabel("/admin/pricing", "zh", harness.routeMap, harness.messages)));

  assert.ok(!tabs[1].class.includes("is-active"));
  assert.equal(tabs[1].ariaCurrent, null);
  assert.equal(tabs[1].label, harness.safeText(getExpectedLabel("/admin/packages", "zh", harness.routeMap, harness.messages)));

  assert.ok(!tabs.some((t) => t.href === "/admin/commercial"));
  assert.ok(!tabs.some((t) => t.href === "/admin/promos"));
});

test("Admin module tabs edge cases across VI/EN/ZH: empty returns, CRM alias resolution, and governance legal exception", () => {
  for (const locale of ["vi", "en", "zh"]) {
    const harness = createHarness(locale);

    // 1. Null page returns empty string
    assert.equal(harness.renderTabs(null, makeContext(locale, ["/admin/pricing"], "/admin/pricing")), "");

    // 2. Non-admin route returns empty string
    assert.equal(harness.renderTabs({ routePath: "/welcome" }, makeContext(locale, ["/welcome"], "/welcome")), "");
    assert.equal(harness.renderTabs({ routePath: "/dashboard" }, makeContext(locale, ["/dashboard"], "/dashboard")), "");

    // 3. Unknown admin route returns empty string
    assert.equal(harness.renderTabs({ routePath: "/admin/unknown-nonexistent-subpath" }, makeContext(locale, [], "/admin/unknown-nonexistent-subpath")), "");

    // 4. Denied (empty routes) returns empty string on groups without legal exception
    assert.equal(harness.renderTabs({ routePath: "/admin/pricing" }, makeContext(locale, [], "/admin/pricing")), "");

    // 5. Only 1 tab authorized returns empty string
    assert.equal(harness.renderTabs({ routePath: "/admin/pricing" }, makeContext(locale, ["/admin/pricing"], "/admin/pricing")), "");

    // 6. Alias /admin/leads with routes CRM/users retains active CRM link without prefix inference
    const crmContext = makeContext(locale, ["/admin/crm/leads", "/admin/users"], "/admin/leads");
    const crmHtml = harness.renderTabs({ routePath: "/admin/leads" }, crmContext);
    const { ariaLabel: crmAria, tabs: crmTabs } = parseTabs(crmHtml);
    assert.equal(crmAria, harness.safeText(ARIA_LABELS[locale]));
    assert.equal(crmTabs.length, 2);
    assert.deepEqual(crmTabs.map((t) => t.href), ["/admin/crm/leads", "/admin/users"]);

    const activeCrmTab = crmTabs.find((t) => t.href === "/admin/crm/leads");
    assert.ok(activeCrmTab, "CRM tab must be present");
    assert.ok(activeCrmTab.class.includes("is-active"));
    assert.equal(activeCrmTab.ariaCurrent, "page");
    assert.equal(activeCrmTab.label, harness.safeText(getExpectedLabel("/admin/crm/leads", locale, harness.routeMap, harness.messages)));

    const usersTab = crmTabs.find((t) => t.href === "/admin/users");
    assert.ok(usersTab, "Users tab must be present");
    assert.ok(!usersTab.class.includes("is-active"));
    assert.equal(usersTab.ariaCurrent, null);
    assert.equal(usersTab.label, harness.safeText(getExpectedLabel("/admin/users", locale, harness.routeMap, harness.messages)));

    // 7. Governance retains /legal exception even when /legal is not in authorized routes
    const govContext = makeContext(locale, ["/admin/governance"], "/admin/governance");
    const govHtml = harness.renderTabs({ routePath: "/admin/governance" }, govContext);
    const { ariaLabel: govAria, tabs: govTabs } = parseTabs(govHtml);
    assert.equal(govAria, harness.safeText(ARIA_LABELS[locale]));
    assert.equal(govTabs.length, 2);
    assert.deepEqual(govTabs.map((t) => t.href), ["/admin/governance", "/legal"]);

    const activeGovTab = govTabs.find((t) => t.href === "/admin/governance");
    assert.ok(activeGovTab, "Governance active tab must be present");
    assert.ok(activeGovTab.class.includes("is-active"));
    assert.equal(activeGovTab.ariaCurrent, "page");
    assert.equal(activeGovTab.label, harness.safeText(getExpectedLabel("/admin/governance", locale, harness.routeMap, harness.messages)));

    const legalTab = govTabs.find((t) => t.href === "/legal");
    assert.ok(legalTab, "Legal tab must be present via exception");
    assert.ok(!legalTab.class.includes("is-active"));
    assert.equal(legalTab.ariaCurrent, null);
    assert.equal(legalTab.label, harness.safeText(getExpectedLabel("/legal", locale, harness.routeMap, harness.messages)));
  }
});
