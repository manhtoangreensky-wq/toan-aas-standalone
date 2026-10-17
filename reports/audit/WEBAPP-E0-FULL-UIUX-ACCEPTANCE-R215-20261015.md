# R215 — Nghiệm thu UI/UX toàn Web App standalone

Ngày kiểm tra: 2026-10-15
Phạm vi: source presentation của customer shell, Admin shell và product lanes;
không bao gồm Bot/Core, engine, provider, ví/Xu, PayOS, dữ liệu production, VPS
hoặc deploy.

## Kết quả

- `SOURCE_GREEN`: đạt.
- Static acceptance: 5/5.
- Fixed palette, responsive shell, focus, skip link và skeleton được khóa bằng
  test riêng; không có `transition: all` trong hai stylesheet.
- `LIVE_PASS`: chưa công nhận vì QA runtime/browser cô lập chưa khả dụng. Chưa
  có screenshot/DOM thật, computed-style thật, console/network trace hoặc thao
  tác keyboard trên runtime.
- Không phát hiện thay đổi contract route/action/field/capability/CSRF/
  idempotency/revision trong checkpoint này.

## Bằng chứng terminal

```text
node --test tests/r215-full-uiux-static-acceptance.test.mjs: 5 passed, 0 failed
node --test tests/*.test.mjs: 450 passed, 0 failed
node --check static/portal/portal.js: PASS
node --check static/portal/portal-i18n.js: PASS
git diff --check: PASS
```

Đây là bằng chứng source/static cuối của checkpoint R215; browser acceptance vẫn
mở vì runtime QA cô lập chưa khả dụng.

## Checklist mapping

- Skip link → `templates/portal_shell.html` có `href="#portal-main"` và
  `<main id="portal-main" tabindex="-1">`.
- Loading → boot skeleton title/copy/grid tồn tại và có CSS responsive.
- Palette → `--portal-bg`, `--portal-accent`, dark canvas và teal dark canvas
  đều giữ token xanh/ngọc; theme dark remap semantic aliases.
- Responsive → min-width 320px, workspace `min-width:0`, mobile media query và
  overflow guard.
- Accessibility/motion guard → focus-visible, reduced-motion và cấm
  `transition: all`.
- Shell ownership → customer/Admin/product lane markers còn nguyên trong
  renderer.

## Chưa đóng

- Browser acceptance ở 375/390/768/1440, light/dark, VI/EN/ZH, keyboard/focus,
  computed style, console/network và persistence.
- R216 Motion vẫn phải xử lý lifecycle/render trước compositor/scroll, popup
  gesture, PWA readiness và đo CLS/LCP/INP.

```ini
SPEC_ID=R215-full-uiux-acceptance
STATUS=SOURCE_GREEN_BROWSER_ACCEPTANCE_OPEN
SOURCE_TESTS=focused5
BROWSER=QA_RUNTIME_UNAVAILABLE
LIVE_PASS=NO
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
DEPLOY=NO
COMMIT=NO
PUSH=NO
MERGE=NO
BLOCKERS=isolated QA runtime not supplied
```
