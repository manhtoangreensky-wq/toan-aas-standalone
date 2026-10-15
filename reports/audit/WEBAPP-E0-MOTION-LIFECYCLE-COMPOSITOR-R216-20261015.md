# R216 — Motion lifecycle, compositor và readiness

Ngày: 2026-10-15
Phạm vi: Web App standalone presentation/source contract; không đụng Bot/Core,
engine, provider, ví/Xu, PayOS, dữ liệu production, VPS hoặc deploy.

## Kết quả

- Auth entry không còn bị lần hydrate provider cắt giữa animation: render async
  chỉ thay vùng provider, còn phase `entry` được giữ đến hết hai `requestAnimationFrame`
  và timer 680ms.
- Vùng provider giữ chỗ tối thiểu 86px để Google/Apple xuất hiện muộn không đẩy
  form.
- Scroll-driven layer dùng `transform`/`opacity` compositor; không còn
  `transition: left` hoặc transition transform theo biến scroll scrub.
- Telegram giữ user gesture bằng cách mở `about:blank` trước `await`; deep link
  vẫn fail-closed và popup lỗi được đóng.
- PWA chỉ gọi native prompt khi có `beforeinstallprompt`; nếu chưa sẵn sàng thì
  hiển thị hướng dẫn cài đặt theo thiết bị, không báo cài đặt giả.
- `prefers-reduced-motion` tắt animation/transition trang trí và giữ nội dung
  đọc được.
- Catalogue auth VI/EN/ZH không còn khai báo trùng khóa `pwaFallback`; regression
  guard mới bắt lỗi duplicate key trước khi bundle được dùng.

## Follow-up R216-L — locale drift ở nút cài ứng dụng trên trang đăng nhập

- **Phát hiện runtime:** bản đang chạy tại `https://app.toanaas.vn/login` vẫn
  hiển thị `Tải & Cài đặt App TOAN AAS` ở VI, `Install TOAN AAS App` ở EN và
  `安装 TOAN AAS App` ở ZH. AX snapshot và screenshot đã ghi nhận trực tiếp.
- **Nguyên nhân nguồn:** một nhánh `renderAuth()` trong `static/portal/portal.js`
  còn hard-code chuỗi cũ, tách khỏi catalogue locale; đồng thời runtime đang
  phục vụ auth bundle cũ.
- **Đã sửa nguồn:** cả nhánh CTA trong `portal.js` và auth renderer hiện tại
  `portal-auth.js` đều dùng catalogue locale (`installGuide.title`/`text.install`),
  giữ nguyên `data-portal-action="pwa-install-prompt"` và route/action contract.
- **Regression gate:** `tests/auth-pwa-install-control.test.mjs` khóa việc không
  quay lại chuỗi cũ và bắt buộc dùng key `installGuide.title`;
  `tests/auth-locale-copy-purity.test.mjs` khóa catalogue auth không có duplicate
  key.
- **Trạng thái live:** vẫn **OPEN — deployment drift**; runtime chưa nhận source
  patch. Không deploy trong checkpoint này nên không được tuyên bố `LIVE_PASS`.

Runtime read-only evidence: `/login?lang=vi` có title `Đăng nhập · TOAN AAS`,
DOM có skip link đúng `#portal-main`, form không blank và console warning/error
không có; script thực tế là `portal-auth.js?v=local-57e76aa281dcc721fdaa`.
AX tree vẫn trả về nút `📲 Tải & Cài đặt App TOAN AAS`; EN/ZH cũng giữ hậu tố
`App`. Đây là bằng chứng auth bundle live cũ, không phải lỗi còn trong source
hiện tại.

## File/contract đã khóa

- `static/portal/portal-auth.js` — auth lifecycle, provider hydration, Telegram
  gesture, PWA readiness.
- `static/portal/portal.js` — auth install CTA locale drift fix (R216-L).
- `static/portal/portal.css` — reservation cho vùng provider.
- `static/portal/portal-theme.css` — auth entry, compositor sheen, scroll layer,
  reduced-motion fallback.
- `tests/r216-motion-lifecycle-compositor.test.mjs` — 6 regression gates.
- `tests/test_auth_reference_login_001_contracts.py` — cập nhật phase contract
  theo lifecycle mới.
- `docs/superpowers/specs/2026-10-15-motion-lifecycle-compositor-r216.md` —
  spec/evidence ledger.

## Bằng chứng terminal

```text
node --test tests/r216-motion-lifecycle-compositor.test.mjs
6 passed, 0 failed

node --test tests/auth-telegram-popup-order.test.mjs tests/auth-pwa-install-control.test.mjs
15 passed, 0 failed

node --test tests/*.test.mjs
458 passed, 0 failed

node --check static/portal/portal-auth.js
node --check static/portal/portal-motion.js
node --check static/portal/portal.js
node --check static/portal/portal-i18n.js
PASS (4/4)

git diff --check
PASS

py_compile (17 touched Python contract files)
PASS
```

`pytest` chưa chạy được: Python bundled trong workspace không có module
`pytest`; không cài dependency trong checkpoint này.

## Acceptance ledger

| Spec | Kết quả source | Runtime |
|---|---|---|
| R216-A auth lifecycle | GREEN — focused 2/2 | Chưa có browser QA |
| R216-B provider stability | GREEN — focused 1/1, `min-height: 86px` | Chưa đo CLS thật |
| R216-C compositor/scroll | GREEN — focused 2/2 | Chưa đo FPS/INP thật |
| R216-D Telegram gesture | GREEN — regression hiện có | Chưa thao tác browser |
| R216-E PWA readiness | GREEN — regression hiện có | Chưa thao tác browser |
| R216-F reduced-motion | GREEN — focused 1/1, full Node 458/458 | Chưa đo CLS/LCP/INP thật |
| R216-G browser acceptance | OPEN | QA runtime cô lập chưa khả dụng |
| R216-L locale drift CTA đăng nhập | GREEN — source regression + duplicate-key guard; full Node 458/458 | OPEN — live còn chuỗi cũ do chưa deploy |

## Chưa được tuyên bố

Chưa có DOM snapshot, screenshot, computed style, console/network trace,
keyboard/focus interaction, FPS/LCP/INP/CLS measurement trên runtime QA cô lập;
vì vậy `LIVE_PASS=NO`. Source green không đồng nghĩa deployed/live.

```ini
TASK=R216-motion-lifecycle-compositor
BASE_SHA=44f5fdacf2435c47e8d8a16eb04115d2d916bcd1
HEAD_SHA=LOCAL_BRANCH_HEAD (verify with `git rev-parse HEAD`)
FILES_CHANGED=static/portal/portal-auth.js; static/portal/portal.css; static/portal/portal-theme.css; static/portal/portal.js; tests/auth-pwa-install-control.test.mjs; tests/r216-motion-lifecycle-compositor.test.mjs; tests/test_auth_reference_login_001_contracts.py; docs/superpowers/specs/2026-10-15-motion-lifecycle-compositor-r216.md; checklist/state
TESTS=R216 6/6; locale/PWA focused 22/22; full Node 458/458; JS syntax 5/5; py_compile 17/17; diff-check PASS
BASELINE_FAILURES=0
BRANCH_FAILURES=0
NEW_FAILURES=0
PROTECTED_COMPARATORS=routes/actions/fields/capabilities/csrf/idempotency/revisions/dynamic_server_data
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
DEPLOY=NO
RUNTIME_SHA=NOT_AVAILABLE
LIVE_PASS=NO
BLOCKERS=live deployment still carries legacy auth copy; isolated QA metrics runtime unavailable; pytest module unavailable in bundled Python
COMMIT=YES (local branch; exact SHA is reported from `git rev-parse HEAD`)
PUSH=NO
MERGE=NO
```
