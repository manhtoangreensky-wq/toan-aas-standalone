# R217-01 — Shell, responsive và visual foundation

**Status:** `SOURCE_GREEN_RUNTIME_OPEN`
**Wave:** W1
**Defects:** `LIVE-UI-01` header clipping, `LIVE-UI-02` PWA FAB bundle cũ.

## File có thể sửa khi Owner mở spec

- `static/portal/portal.css`
- `static/portal/portal-theme.css`
- `static/portal/portal-first-paint.css`
- `templates/index.html`
- `templates/portal_shell.html`
- các regression test mới trong `tests/` chỉ cho shell/responsive.

## Cấm sửa

Không đổi route/action/field, API, session, provider, wallet, server data, Bot/Core hoặc
đưa CSS mới vào product lane để né lỗi layout. Không thay brand blue/teal/navy.

## Thi công cụ thể

1. Landing ≤420px: brand ở hàng riêng, locale/theme/action ở hàng riêng; không phần tử
   nào có `right > viewport width`; giữ CTA và logo đọc được.
2. PWA install: không render FAB trước `beforeinstallprompt`; khi inline CTA được phép
   hiện thì đặt trong flow, không che proof/content.
3. Chuẩn hóa spacing 4/8/12/16/24/32/48px, body mobile ≥16px, target ≥44×44px.
4. Table/list ở 375/390px chuyển card dọc hoặc wrapper cuộn có tiêu đề cột; không dùng
   `overflow-x:hidden` để che nội dung thật.
5. Đo contrast light/dark theo semantic token; dark vẫn xanh navy/teal, chữ sáng không lóa.

## Acceptance

- Viewport 320/375/390/414/768/1024/1440 không có clipping/horizontal overflow.
- `scrollWidth <= clientWidth`; tất cả CTA chính nhìn thấy và focus được.
- PWA CTA ẩn khi chưa ready, không có FAB che nội dung.
- Contrast AA và screenshot light/dark đạt ở shell customer + admin.

## Verify

```powershell
node --test tests/r215-full-uiux-static-acceptance.test.mjs tests/pwa-landing-install-placement.test.mjs
git diff --check
```

**Runtime evidence:** DOM probe `scrollWidth/clientWidth`, computed color/size, screenshot
ở 390px và 1440px; thiếu runtime thì giữ `RUNTIME_UNAVAILABLE`.

## Source closeout 2026-10-16

- `static/portal/portal.css`: landing action cluster wraps at `max-width: 420px`.
- `static/portal/portal.js`: landing install banner/FAB is removed and not recreated until
  a native `beforeinstallprompt` is available; iOS guide remains eligible.
- `tests/pwa-landing-install-placement.test.mjs`: no-prompt landing regression added.
- `tests/current-main-motion-static-gates.test.mjs`: header wrap regression strengthened.
- `static/portal/portal.css`: install-guide backdrop và tab strip chuyển từ lớp đen sang
  xanh navy có alpha; giữ chữ trắng và màu nhấn xanh ngọc.
- `tests/install-modal-navy-palette.test.mjs`: khóa bảng màu modal, không cho nền đen quay lại.
- Evidence: focused W1/PWA/auth/utility/motion `39/39`; full Node `470/470`; JS syntax and
  `git diff --check` pass; regression modal navy pass riêng. Live runtime evidence is still open because the deployed asset
  fingerprint has not been rechecked after this source delivery.
