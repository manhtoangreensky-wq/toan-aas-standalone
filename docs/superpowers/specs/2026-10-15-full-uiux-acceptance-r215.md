# R215 — Nghiệm thu UI/UX toàn Web App standalone

## Mục tiêu

Khóa source gate chung sau R214 trước khi mở R216 Motion. Kiểm tra các bất biến
presentation đã được Owner yêu cầu: bố cục dọc/responsive, màu xanh dương–xanh
ngọc, khả năng đọc sáng/tối, keyboard focus, skip link, skeleton loading,
customer/Admin shell và các product lane. Không thay đổi business flow.

## Phạm vi hẹp

- `templates/portal_shell.html`: skip link, `portal-main`, skeleton boot.
- `static/portal/portal.css` và `static/portal/portal-theme.css`: palette,
  theme mapping, responsive/overflow, focus và reduced-motion static gates.
- `static/portal/portal.js`: chỉ kiểm tra route/shell ownership, không chỉnh code
  trong checkpoint này.
- `tests/r215-full-uiux-static-acceptance.test.mjs` và evidence/report/state.

## Contract bị khóa

- Không đổi route, action, field, capability, CSRF, idempotency, revision,
  dữ liệu server-owned hoặc component ownership.
- Không đổi màu sang đen thuần; dark theme phải giữ canvas xanh/navy và chữ sáng.
- Không provider call, job, ví/Xu, PayOS, production mutation, Bot/Core,
  backend, VPS, deploy hoặc browser storage.
- Browser runtime acceptance vẫn là cổng riêng; source test không thay thế
  DOM/screenshot/console/network bằng chứng thật.

## Acceptance

- Skip link trỏ đúng `#portal-main`, `main` có `tabindex=-1` và boot skeleton có
  cấu trúc title/copy/grid.
- Token light/dark giữ xanh–xanh ngọc, tương phản chữ/nền và mapping theme thật.
- Shell có min-width an toàn, workspace không tràn ngang, mobile media query giữ
  card theo cột dọc.
- Focus-visible và reduced-motion có fallback; không dùng `transition: all`.
- Customer/Admin/product lane markers vẫn tồn tại trong renderer.
- Focused test, full Node suite, syntax và diff-check xanh.
- Nếu không có QA runtime: `BROWSER=QA_RUNTIME_UNAVAILABLE`, `LIVE_PASS=NO`.
