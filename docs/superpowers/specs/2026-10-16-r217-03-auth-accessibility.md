# R217-03 — Auth lifecycle, first paint và accessibility

**Status:** `SOURCE_GREEN_RUNTIME_OPEN`
**Wave:** W3

## File có thể sửa

- `static/portal/portal-auth.js`
- `static/portal/portal.js`
- `static/portal/portal-first-paint.css`
- `templates/portal_shell.html`
- auth/accessibility regression tests.

## Cấm sửa

Không đổi cơ chế session/signature/CSRF, provider call, user data, route policy hoặc
thực hiện đăng nhập production.

## Thi công cụ thể

1. Chỉ một auth entry lifecycle; Promise hydrate không gọi render làm cắt animation hoặc
   đổi chiều cao provider.
2. Unauthenticated direct route redirect trước khi hiển thị dashboard shell; giữ `next`
   an toàn và không open redirect.
3. Skeleton mô phỏng sidebar/header/KPI; không dùng spinner trống duy nhất.
4. Skip link tới `#portal-main`, main `tabindex=-1`, label/aria-busy/autocomplete/focus
   và lỗi gần field.
5. Modal/drawer có focus management, Escape/Back, disabled/loading/success/failed state.

## Acceptance

- Route chưa auth không chớp nội dung protected trước redirect.
- Auth hydrate giữ layout ổn định, provider card không nhảy chiều cao.
- Tab order theo visual order; mọi interactive control có accessible name.
- `prefers-reduced-motion` vẫn hiển thị nội dung ngay.

## Verify

```powershell
python -m pytest tests/test_auth_entry_motion_contracts.py tests/test_auth_first_paint_cls_contracts.py -q
node --test tests/auth-telegram-popup-order.test.mjs tests/auth-pwa-install-control.test.mjs
node --check static/portal/portal-auth.js
```

Nếu bundled Python không chạy, ghi lỗi harness thật và giữ `RUNTIME_UNAVAILABLE`; không
đổi lệnh thành PASS giả.

## Source closeout 2026-10-16

- Auth entry layout contract fixed: `.portal-auth-page` starts content at the top with
  `align-items:start`, `align-content:start`, and `padding-top:68px`.
- Responsive contract boundary now stops before the later Admin drawer layer, so the
  auth three-row `brand → locale → actions` check does not inspect unrelated CSS.
- Direct source checks for the entry layout and responsive three-row contract pass.
- Node auth/customer/motion regression: `31/31`; auth/PWA focused: `16/16`.
- Authenticated browser route matrix and runtime AX/console/network evidence remain open.
