import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portalPath = path.join(root, "static", "portal", "portal.js");
const i18nPath = path.join(root, "static", "portal", "portal-i18n.js");
const portalSource = fs.readFileSync(portalPath, "utf8");
const headerStart = portalSource.indexOf("  function renderHeader(page, context) {");
const headerEnd = portalSource.indexOf("\n  function renderFields(", headerStart);
assert.ok(headerStart >= 0 && headerEnd > headerStart, "portal header renderer must remain present");
const headerSource = portalSource.slice(headerStart, headerEnd);

function loadI18n() {
  const document = { title: "", documentElement: { lang: "", setAttribute() {} } };
  const window = {
    document,
    navigator: { language: "vi" },
    dispatchEvent() {},
    CustomEvent: function CustomEvent() {},
  };
  const context = vm.createContext({ window, document, Intl, Date, Number, String, Object, Array, Set, Map, Math, RegExp });
  vm.runInContext(fs.readFileSync(i18nPath, "utf8"), context, { filename: i18nPath });
  return window.TOANAASI18n;
}

function renderCustomerHeader(locale, role = "member") {
  const i18n = loadI18n();
  i18n.setLocale(locale, { emit: false });
  const runtime = vm.createContext({
    uiText: (key, fallback, params) => i18n.t(key, params) || fallback,
    displayName: () => "QA User",
    isAdminPortalSurface: () => false,
    activeAdminNavigationGroup: () => null,
    localizedPageTitle: (page) => page.title,
    localizedNavigationLabel: (value) => value,
    safeText: (value) => String(value ?? ""),
    canonicalWalletProjection: (wallet) => wallet,
    interfaceLocaleFor: () => locale,
    initials: () => "QU",
    portalIcon: () => "",
    ICONS: new Proxy({}, { get: () => "" }),
    hasLiveCanonicalAdmin: (context) => context.liveAdmin === true,
    renderThemeToggle: () => "",
    pageStatusBadge: () => "",
    window: {},
  });
  vm.runInContext(`${headerSource}\nglobalThis.renderHeader = renderHeader;`, runtime);
  return runtime.renderHeader(
    { section: "Account", title: "Account" },
    {
      profile: { role },
      session: { authenticated: true, role, email: "qa@example.invalid" },
      wallet: { balance_xu: 0 },
      pwaEnabled: false,
    },
  );
}

const requiredCopyKeys = [
  "chrome.accountMembershipBadge",
  "featureCatalog.entry.membership.title",
  "chrome.accountMenu.membershipDescription",
  "featureCatalog.entry.wallet.title",
  "chrome.accountMenu.walletDescription",
  "featureCatalog.entry.wallet_topup.title",
  "chrome.accountMenu.topupDescription",
  "featureCatalog.entry.account.title",
  "chrome.accountMenu.profileDescription",
  "featureCatalog.entry.account_security.title",
  "chrome.accountMenu.securityDescription",
  "chrome.adminAppCaption",
  "chrome.accountMenu.adminDescription",
  "accountCenter.profile.logout",
  "accountCenter.profile.logoutConfirm",
];

test("customer account dropdown renders complete VI/EN/ZH copy without changing links or logout", () => {
  const i18n = loadI18n();
  for (const locale of ["vi", "en", "zh"]) {
    const html = renderCustomerHeader(locale, "admin");
    const messages = i18n.messages[locale];
    for (const key of requiredCopyKeys) {
      assert.ok(messages[key]?.trim(), `${locale}.${key} must have reviewed copy`);
      assert.ok(html.includes(messages[key]), `${locale}.${key} must appear in the customer dropdown`);
    }
    for (const key of requiredCopyKeys.filter((candidate) => candidate.startsWith("chrome.accountMenu."))) {
      assert.ok(messages[key].length <= 40, `${locale}.${key} must stay concise for the compact dropdown`);
    }
    assert.deepEqual(
      [...html.matchAll(/<a class="portal-user-dropdown-item" href="([^"]+)"/g)].map((match) => match[1]),
      ["/membership", "/wallet", "/wallet/topup", "/account", "/account/security", "/admin"],
      `${locale} customer links must keep their routes and order`,
    );
    assert.match(html, /data-portal-action="auth-logout"/);
    assert.ok(html.includes(`data-portal-confirm="${messages["accountCenter.profile.logoutConfirm"]}"`));
    assert.ok(html.includes(`<span>${messages["accountCenter.profile.logout"]}</span>`));
    assert.doesNotMatch(html, /Quyền Lợi|Thông tin tài khoản & quyền lợi Xu|Ví & Số dư Xu|Nạp Xu, kiểm tra số dư|Cổng thanh toán PayOS VietQR|Hồ sơ & Cài đặt|Quản lý tài khoản, đổi Avatar|Bảo mật & Đổi mật khẩu|Phiên đăng nhập, mật khẩu|Trang Quản Trị Admin ERP|Quản lý người dùng, duyệt Xu, tài chính & hệ thống|Đăng xuất \/ Thoát tài khoản/);
  }
});

test("account dropdown locale keys are declared once in each supported locale", () => {
  const i18nSource = fs.readFileSync(i18nPath, "utf8");
  const localizedKeys = requiredCopyKeys.filter((key) => key.startsWith("chrome.accountMenu.") || key === "chrome.accountMembershipBadge");
  for (const key of localizedKeys) {
    assert.equal(i18nSource.split(`"${key}":`).length - 1, 3, `${key} must have exactly one definition for vi/en/zh`);
  }
});

test("customer Admin entry remains limited to Admin roles and stays in its original position", () => {
  const regular = renderCustomerHeader("en", "member");
  const admin = renderCustomerHeader("en", "admin");
  const regularRoutes = [...regular.matchAll(/<a class="portal-user-dropdown-item" href="([^"]+)"/g)].map((match) => match[1]);
  const adminRoutes = [...admin.matchAll(/<a class="portal-user-dropdown-item" href="([^"]+)"/g)].map((match) => match[1]);
  assert.deepEqual(regularRoutes, ["/membership", "/wallet", "/wallet/topup", "/account", "/account/security"]);
  assert.deepEqual(adminRoutes, ["/membership", "/wallet", "/wallet/topup", "/account", "/account/security", "/admin"]);
});
