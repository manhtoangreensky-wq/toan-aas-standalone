import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portalSource = fs.readFileSync(path.join(root, "static", "portal", "portal.js"), "utf8");
const i18nSource = fs.readFileSync(path.join(root, "static", "portal", "portal-i18n.js"), "utf8");
const start = portalSource.indexOf("function renderMobileNav(page) {");
const end = portalSource.indexOf("function isAdminMobileSurface(page)", start);
assert.ok(start >= 0 && end > start, "customer mobile dock renderer must remain present");
const dockSource = portalSource.slice(start, end);

function loadMessages() {
  const document = { title: "", documentElement: { lang: "", setAttribute() {} } };
  const window = { document, navigator: { language: "vi" }, dispatchEvent() {}, CustomEvent: function CustomEvent() {} };
  const context = vm.createContext({ window, document, Intl, Date, Number, String, Object, Array, Set, Map, Math, RegExp });
  vm.runInContext(i18nSource, context, { filename: "portal-i18n.js" });
  return window.TOANAASI18n.messages;
}

const messages = loadMessages();
const mobileItems = [
  ["studio", "/studio", "mobile.studio", "Công cụ", "Studio", "工作室"],
  ["publishing", "/publishing", "mobile.publishing", "Đăng bài", "Publishing", "发布"],
  ["projects", "/projects", "mobile.projects", "Dự án", "Projects", "项目"],
  ["wallet", "/wallet", "mobile.wallet", "Ví Xu", "Credits", "积分"],
  ["account", "/account", "mobile.account", "Tài khoản", "Account", "账户"],
];

test("customer mobile dock preserves the five current destinations and localized copy", () => {
  assert.equal(mobileItems.length, 5);
  assert.equal(new Set(mobileItems.map(([key]) => key)).size, 5);
  assert.equal(new Set(mobileItems.map(([, route]) => route)).size, 5);

  for (const [key, route, localeKey, ...labels] of mobileItems) {
    const sourceRow = `["${key}", "${route}", uiText("${localeKey}"`;
    assert.ok(dockSource.includes(sourceRow), `mobile nav must keep ${route} on ${localeKey}`);
    assert.ok(dockSource.includes(`uiText("${localeKey}", "${labels[0]}")`), `${localeKey} fallback should be Vietnamese`);
    for (const [index, locale] of ["vi", "en", "zh"].entries()) {
      assert.ok(messages[locale][localeKey], `${locale}.${localeKey} copy must exist`);
      assert.equal(messages[locale][localeKey], labels[index], `${locale}.${localeKey} must use reviewed copy`);
    }
  }
});

test("customer mobile dock remains locale presentation only and keeps current-route selection", () => {
  assert.ok(dockSource.includes("const current = isMobileNavCurrent(key, page);"));
  assert.ok(dockSource.includes("aria-current=\"page\""));
  assert.ok(dockSource.includes("safeText(label)"));
  assert.ok(dockSource.includes("portalIcon(icon)"));
});
