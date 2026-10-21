# R218 — AD-01-PRICING-NAV-LOCALE

## Kết quả duy nhất / thứ tự

Các tab phân hệ Admin dùng đúng locale hồ sơ VI/EN/ZH, vẫn giữ nguyên tập route,
quyền được máy chủ cấp, alias, current-tab và ngoại lệ /legal hiện có.
Giữ SPEC_ID đã phát hiện trên Pricing; root nằm trong renderAdminModuleTabs dùng chung.
Sau Codex ACCEPTED mới mở Pricing fixed-copy → mobile → affordance. Motion cuối.

## Nhận dạng và bằng chứng trước giao

- Worktree: `C:/Users/toann/Documents/Codex/_webapp-r218-voice`.
- HEAD detached1730ea41ffda53e6bcd068f45a49c8c9f6949929, ref github/webapp-r217-subdub-ui-r218.
- COMPLEX/SINGLE; BATCH R218-A0; một worker; PR cuối hiện có #654. Không Git mutation.
- Owner: “trừ khi là danh từ tiếng anh còn lại bản tiếng việt tất cả phải tiếng việt,
  bản tiếng anh thì toàn bộ tiếng anh”; “motion làm cuối cùng”.
- Source trước task: portal.js SHA256
  `5ac629c4fd9a6559da64e60917ca74a50fd92d82b415c7fd8cf8ae5731dcb9ca`;
  i18n `14e6e15d94cd70e9331599ba06fe0990c77e36b8dc9eae2c519bddcb971275ea`.
- Đã ACCEPTED local: data cards,35 state labels,header zh; Pricing truth72/72 và
  Node713/713. Không sửa các phần này.
- Browser Pricing EN có tabs VI dù renderer/profile en. Source renderAdminModuleTabs
  đọc context.locale và typeof currentLocale; đây không phải nguồn locale profile/interface
  đang dùng ở phần còn lại. Hàm hiện cũng không có nhánh ZH.
- Inventory thật:9groups,54tab occurrences,48unique paths. ADMIN_ERP_ROUTE_I18N có46paths
  và đủ catalogue native VI/EN/ZH; ngoại lệ /admin/commercial và /legal.
- Hai test locale hiện có chỉ xem declaration label/labelEn, chưa gọi renderer.

## File/context và scope

Parent AGENTS: C:/Users/toann/Documents/Codex/AGENTS.md. Không tìm thấy repo-root
AGENTS/MAP/PROGRESS/business-rules trong worktree này. Các quyết định cần thiết đã chép ở đây.

Allowed source/test:

1. static/portal/portal.js: chỉ renderAdminModuleTabs khoảng11830–11848.
2. static/portal/portal-i18n.js: chỉ3 adminModuleTabs.* keys mới mỗi VI/EN/ZH.
3. tests/admin-module-tabs-locale-purity.test.mjs: giữ2 test hiện có, thêm7 behavior tests.

Phase A chỉ file3. Phase B chỉ files1/2, khóa test sau Codex RED.
Report output được phép dưới _giao-viec. Không sửa checklist/spec/state hoặc file khác.
Không sửa ADMIN_TAB_GROUPS, ADMIN_ERP_ROUTE_I18N, adminErpNavigation, interfaceLocaleFor,
route registry, role policy, alias/current matching, href, CSS/Pricing/backend/integration.
Không rename/chữ ký/helper refactor. MAX_SOURCE_FILES_CHANGED=3 theo hai phase.

## Code hiện trạng và code đích — phase B chỉ sau RED

Đổi dòng locale trong function:

```js
// before
    const isEn = (context && context.locale === "en") || (typeof currentLocale !== "undefined" && currentLocale === "en");
// after
    const locale = interfaceLocaleFor(context);
```

Đổi đúng dòng chọn label trong map:

```js
// before
      const label = isEn && tab.labelEn ? tab.labelEn : tab.label;
// after
      const fallback = locale === "en" && tab.labelEn ? tab.labelEn : tab.label;
      const label = tab.path === "/admin/commercial"
        ? uiText("adminModuleTabs.commercial", fallback)
        : tab.path === "/legal"
          ? uiText("adminModuleTabs.legal", fallback)
          : adminErpRouteText(tab.path, fallback);
```

Nav aria-label đổi thành `${safeText(uiText("adminModuleTabs.ariaLabel", "Phân hệ nghiệp vụ"))}`.
Giữ nguyên các dòng filter/group/current/anchor class và href khác.

| Key | VI | EN | ZH |
|---|---|---|---|
| adminModuleTabs.ariaLabel | Phân hệ nghiệp vụ | Module sections | 业务模块 |
| adminModuleTabs.commercial | Trung tâm thương mại | Commercial center | 商务中心 |
| adminModuleTabs.legal | Pháp lý & quyền riêng tư | Legal & privacy | 法律与隐私 |

Thêm9 entries gần5 adminPricingReadState keys vừa có. Không đổi old dictionary values.

## Phase A — test hành vi, 2–5 phút

Chỉ thêm test, không sửa source. Giữ nguyên2 test hiện có. Thêm import node:vm và
đọc catalogue thật từ static/portal/portal-i18n.js.

Hàm trích source dùng nguyên cách sau; không đi tìm helper bằng hàng chục view_file:

```js
function fn(name) {
  const a = PORTAL.indexOf(`  function ${name}(`);
  const b = PORTAL.indexOf('\n  }', a) + 4;
  assert.ok(a >= 0 && b > a, name);
  return PORTAL.slice(a, b);
}
```

Các đoạn/địa chỉ đã xác minh:

- ROUTE_MAP: từ `  const ADMIN_ERP_ROUTE_I18N = Object.freeze({` đến trước
  `  function adminErpGroupText(`, khoảng90–142.
- GROUPS: từ `  const ADMIN_TAB_GROUPS = [` đến trước `  function renderAdminModuleTabs(`,
  khoảng11714–11829.
- fn helpers: safeText, normalizePath(2291), portalI18n(gần200), reviewedInterfaceLocale,
  interfaceLocaleFor(472–497), adminErpRouteText(148), renderAdminModuleTabs(11830).
- VM ctx.window=ctx; ctx.location={pathname:'/admin/pricing'}; nạp catalogue thật trước,
  setLocale(locale,{emit:false}). ctx.adminErpNavigation=(context)=>({routes:new Set(context.allowedRoutes)}).
  Đây là fixture phép chiếu routes được cấp, không phải mô phỏng backend RBAC.
- Được dùng adapter vào catalogue thật:
  `ctx.uiText=(key,fallback,params)=>ctx.TOANAASI18n.has(key)?ctx.TOANAASI18n.t(key,params,locale):fallback`.
  Không stub label hoặc interfaceLocaleFor. Không trích toàn DOM/app vào VM.
- VM expose groups/routeMap/renderTabs để test. Context mỗi render có profile.locale và
  interfaceLocale đúng target, còn context.locale cố ý sai (en→vi, vi/zh→en) để bắt bug cũ.
  pathname/path/routePath theo page đang test.

7 test mới:

1–3. Mỗi locale một test: render9groups với tập route của group được cấp. Chọn route đầu
group. Kiểm đủ anchors và label đúng catalogue native:46known paths dùng messages[locale]
[routeMap[path]], hai ngoại lệ dùng bảng trên. aria-label đúng bảng. So HTML label qua
safeText để không sai vì &amp;. Không rò tiếng Việt trong EN/ZH fixed chrome.
4–6. Mỗi locale một test: Pricing chỉ cấp /admin/pricing và /admin/packages; đúng2 hrefs,
active pricing aria-current đúng, không có commercial/promos; aria/copy đúng locale.
7. Một test lặp3locale: null page,non-admin,unknown route,denied hoặc chỉ1tab trả rỗng;
alias /admin/leads với routes CRM/users giữ đúng current CRM link; governance vẫn giữ
ngoại lệ /legal và các href đúng. Không suy quyền theo prefix.

Expected total trong file:9 tests (2 old+7new). Trước fix cần RED đúng locale/labels;
không bịa số fail, Codex đo. Report A rồi dừng. Không tự phase B.

## Gate / acceptance

- AC01: toàn9groups/48paths có nhãn VI/EN/ZH đúng catalogue,3 special/aria keys đầy đủ.
- AC02: dùng profile/interface locale thật; legacy context.locale không quyết định label.
- AC03: registry/groups/role filter/alias/legal exception/current/href giữ nguyên.
- AC04: function ngoài scope và mọi old i18n values, Pricing truth/CSS/backend/integration
  không đổi;2 test cũ giữ nguyên, test mới không bị nới sau RED.
- AC05: focused9/9, full Node720/720 (713old+7new), syntax/diff0; Pricing browser nav
  VI/EN/ZH ×light/dark ×390/1440, labels/aria/route interaction/focus đúng, lỗi/write/
  external/unknown0. Không đóng backend role hoặc toàn Admin từ fixture này.

Codex chạy `node --test tests/admin-module-tabs-locale-purity.test.mjs` để lấy RED;
sau phase B cùng test GREEN9/9, full Node, syntax/diff và browser. Worker không chạy
shell/terminal/lệnh/browser/network/Git/package/ENV/DB/provider/wallet/production/IDE trust.

## Reports / stop

Phase A: _giao-viec/BAO-CAO-05A-AD-01-PRICING-NAV-LOCALE.md.
Phase B: _giao-viec/BAO-CAO-05B-AD-01-PRICING-NAV-LOCALE.md.
Mỗi báo cáo ghi phase/HANDOFF_ROUND/SPEC_ID/HEAD/files/AC/verify NOT_RUN/giả định và
COMMIT/PUSH/PR/MERGE/DEPLOY=NO; không sửa checklist hoặc tự ACCEPTED. Dừng nếu source
khác, thiếu helper, cần đổi registry/roles/route hoặc vượt allowlist. Báo đúng thiếu
dữ kiện, không dò ngoài phạm vi vô hạn. Cùng SPEC_ID qua các lượt; code-failure counter0.
