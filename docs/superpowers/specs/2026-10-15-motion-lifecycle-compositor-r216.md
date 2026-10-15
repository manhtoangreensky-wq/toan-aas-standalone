# R216 — Motion lifecycle, compositor và readiness

Ngày: 2026-10-15
Phạm vi: Web App standalone presentation-only. Không chạm Bot/Core, engine,
provider, ví/Xu, PayOS, dữ liệu production, VPS hoặc deploy.

## Mục tiêu

Khóa các nguyên nhân khiến hiệu ứng bị cắt, giật hoặc giả trạng thái:

1. Auth hydration không được chuyển `entry → settled` giữa animation.
2. Khu vực provider không tăng chiều cao khi `/auth/providers` trả về muộn.
3. Landing sheen và các biến đổi do scroll chỉ dùng thuộc tính compositor.
4. Scroll-driven transform không có transition gây trễ sau ngón tay.
5. Telegram popup được mở đồng bộ trước `await` và deep link vẫn fail-closed.
6. PWA chỉ gọi native install prompt khi browser phát readiness thật; trạng
   thái hướng dẫn thủ công phải nói đúng, không tạo CTA giả.
7. `prefers-reduced-motion` luôn hiển thị nội dung đầy đủ; source chỉ ghi nhận
   contract CLS/LCP/INP khi chưa có runtime QA.
8. Auth install CTA phải dùng catalogue locale chung, không được giữ copy cũ
   có `App` xen trong VI/ZH hoặc copy không đồng nhất giữa các nhánh renderer.
9. Landing ở viewport hẹp phải giữ nguyên hàng thương hiệu, bọc cụm ngôn ngữ/
   giao diện/nút hành động xuống hàng riêng; nút cài PWA trên landing phải nằm
   trong CTA cuối trang, không nổi đè vùng nội dung.
10. Features hydration phải giữ đúng `portal-main` và route `/features` sau các
    lần đọc async; phản hồi cũ không được dựng lại DOM sau khi shell đã thay.

## Phạm vi file được phép

- `static/portal/portal-auth.js`
- `static/portal/portal.js` (chỉ nhánh auth install CTA locale drift R216-L)
- `static/portal/portal-theme.css`
- `static/portal/portal.css` (chỉ media rule header landing ≤420px)
- `templates/dashboard.html` (chỉ giới hạn shorthand hover transition)
- `static/portal/portal-motion.js` (chỉ khi regression yêu cầu)
- `static/portal/portal-features.js` (chỉ lifecycle cleanup của Features motion)
- `tests/r216-motion-lifecycle-compositor.test.mjs`
- `tests/auth-pwa-install-control.test.mjs` (regression R216-L)
- `tests/current-main-motion-static-gates.test.mjs` (regression responsive header)
- `tests/pwa-landing-install-placement.test.mjs` (regression PWA landing placement)
- report/state/checklist R215/R216.

Không đổi route, action, field, capability, CSRF, idempotency, revision hoặc
server-owned data.

## Hợp đồng chuyển động

### Auth entry

- Kích hoạt: lần render đầu của trang đăng nhập/đăng ký.
- Thời lượng mục tiêu: 680ms, một lần; `entry` không bị async provider render
  cắt ngang.
- Hydration chỉ cập nhật `.portal-auth-primary` khi MFA và thay vùng social;
  không dựng lại `main` hoặc khởi động lại animation.
- `settled` chỉ được ghi sau hai animation frame và timer hữu hạn; môi trường
  không có animation API phải fail-open về trạng thái tĩnh.
- Mobile và reduced-motion: nội dung hiện ngay, không ẩn vĩnh viễn.

### Provider layout stability

- Vùng `.portal-direct-social-auth` có chiều cao tối thiểu đủ cho Telegram và
  một hàng provider; Google/Apple xuất hiện sau async không làm đẩy form.
- Không tạo provider, output hoặc trạng thái đăng nhập giả.

### Landing scroll

- Biến đổi phụ thuộc `--landing-scroll-progress` dùng `transform`/`opacity`;
  không transition `left` hoặc transition `transform` theo scrub.
- Hover/focus có thể transition riêng, nhưng không được làm chậm giá trị do
  scroll ghi mỗi frame.
- Reduced-motion bỏ toàn bộ chuyển động trang trí và giữ nội dung đọc được.
- Nếu người dùng bật reduced-motion trong lúc landing đang chạy, lifecycle phải
  tháo listener, huỷ RAF/timer/observer/pointer và trả DOM về trạng thái tĩnh.
- Callback IntersectionObserver/RAF/focus của Features phải bị vô hiệu và huỷ
  khi route unmount; callback cũ không được sửa DOM đã tách.
- Scroll hot path không được đổi `background`/`background-color` theo progress;
  hiệu ứng nền phụ chỉ dùng pseudo-element với `opacity`/`transform`.
- Không áp `will-change`/`translateZ(0)` blanket lên toàn bộ page/card/table;
  chỉ dùng hint ở control có animation thực sự.

### Existing readiness locks

- Telegram: `window.open("about:blank", "_blank")` trước API `await`; link chỉ
  nhận `https://t.me` hợp lệ, popup lỗi thì đóng, popup bị chặn thì điều hướng
  cùng tab.
- PWA: `beforeinstallprompt` hợp lệ mới gọi `.prompt()`; nếu chưa có thì hiển
  thị hướng dẫn trình duyệt trung thực; standalone/appinstalled ẩn CTA.
- Auth catalogue VI/EN/ZH không được khai báo trùng khóa; duplicate-key guard
  phải chạy cùng regression locale trước khi giao source.

## Regression acceptance

- `node --test tests/r216-motion-lifecycle-compositor.test.mjs` xanh.
- `node --test tests/auth-telegram-popup-order.test.mjs tests/auth-pwa-install-control.test.mjs`
  xanh.
- Auth install CTA không chứa chuỗi `Tải & Cài đặt App TOAN AAS` và dùng
  `uiText("installGuide.title", ...)`.
- `node --check` cho các JavaScript đã chạm.
- `node --test tests/*.test.mjs` không có failure mới so với 459 baseline.
- Inline renderer styles không được dùng `transition: all`; motion gate phải
  kiểm tra cả JavaScript renderer, không chỉ stylesheet.
- Dashboard cũ chỉ transition `transform` và `border-color`, không shorthand all-property.
- Landing mobile header phải wrap thay vì clipping; PWA landing control phải static
  trong final CTA khi có `--landing-inline` class.
- `git diff --check` xanh.
- Không tuyên bố LIVE_PASS nếu chưa có DOM/screenshot/console/interaction từ
  QA runtime.

## Evidence ledger

| Spec | Acceptance | Evidence | Trạng thái |
|---|---|---|---|
| R216-A auth lifecycle | hydrate không cắt entry, không dựng lại main | focused 2/2 + full Node 469/469 + source diff | GREEN (source) |
| R216-B provider stability | vùng social không layout shift | focused 1/1 + CSS contract (`min-height: 86px`) | GREEN (source) |
| R216-C compositor/scroll | không `transition:left`, không scrub lag | focused 2/2 + hot-path gates + full Node 469/469 + CSS diff | GREEN (source) |
| R216-D Telegram | popup trước await, link fail-closed | existing popup test | GREEN (source) |
| R216-E PWA | native prompt chỉ khi readiness | existing PWA test | GREEN (source) |
| R216-F reduced motion | static content + performance notes | focused 1/1 + motion/static/palette/features 26/26 + full Node 469/469; runtime metrics pending | GREEN (static) |
| R216-G browser acceptance | DOM/screenshot/computed style/console/interaction | Fixture server dựng được; bundled Chromium thiếu executable; Chrome hệ thống exit 13 trước remote debugging | OPEN |
| R216-L auth install locale | VI/EN/ZH dùng cùng key locale, không hard-code `App`, không duplicate key | source regression + duplicate-key guard + full Node 469/469; direct login AX recheck xanh nhưng `/features` → `/login?next=/features` còn CTA cũ | SOURCE GREEN / LIVE DRIFT OPEN |
| R216-H landing mobile header | header không clipping ở ≤420px, controls wrap xuống hàng | source media rule + static regression; live screenshot khoảng 327x667 ghi nhận bundle cũ còn clipping; PWA placement regression đã xanh | SOURCE GREEN / LIVE DRIFT OPEN |
| R216-I Features hydration lifecycle | async response chỉ render khi đúng `portal-main` và `/features` | `feature-catalog-route-presentation.test.mjs` 6/6 + JS syntax + diff-check | GREEN (source) |

## Kết quả source gate ngày 2026-10-15

```text
node --test tests/r216-motion-lifecycle-compositor.test.mjs: 10 passed, 0 failed
node --test tests/auth-telegram-popup-order.test.mjs tests/auth-pwa-install-control.test.mjs: 15 passed, 0 failed
node --test tests/**/*.test.mjs: 469 passed, 0 failed
node --test tests/current-main-motion-static-gates.test.mjs tests/r216-motion-lifecycle-compositor.test.mjs tests/feature-catalog-route-presentation.test.mjs: 26 passed, 0 failed (latest recheck)
node --test tests/feature-catalog-route-presentation.test.mjs: 6 passed, 0 failed
node --test tests/current-main-motion-static-gates.test.mjs tests/r216-motion-lifecycle-compositor.test.mjs tests/auth-locale-copy-purity.test.mjs tests/auth-pwa-install-control.test.mjs: 31 passed, 0 failed (prior focused ledger)
node --check static/portal/portal-auth.js: PASS
node --check static/portal/portal-motion.js: PASS
node --check static/portal/portal.js: PASS
git diff --check: PASS
py_compile (17 touched Python contract files): PASS
pytest: NOT RUN — bundled Python không có module pytest
```

R216 chỉ khóa presentation/source contract. Không ghi `LIVE_PASS` khi chưa có
DOM, screenshot, computed style, console/network, keyboard/focus và số đo
CLS/LCP/INP từ runtime QA cô lập.

## Delegation/QA evidence — 2026-10-15

Phiếu `PHIEU-217` đã được chuẩn bị cho Antigravity để rà soát riêng template
Dashboard và static motion gate. Lần giao lại qua script trả
`LOI: khong tim thay agy.exe`; không có báo cáo thợ và không được tính là PASS.
QA cục bộ cũng chưa mở được Chrome session: Playwright bundled không có
Chromium, Chrome hệ thống kết thúc với `exitCode=13` trước remote debugging.

Live read-only recheck ngày 2026-10-15 trên `/login?lang=vi|en|zh` ghi nhận
đúng một ngôn ngữ trên fixed chrome, skip link `#portal-main`, nền navy/xanh
ngọc và không còn hậu tố `App` xen trong vùng hiển thị. Đây là bằng chứng riêng
cho R216-L; không đóng R216-G và không ghi `LIVE_PASS` cho toàn app.

Live read-only landing recheck cùng ngày ở viewport hẹp khoảng 327×667 ghi nhận
bundle đang chạy chưa có source delivery mới: logo/brand giữ hàng đầu nhưng
cụm locale/theme/action bị cắt ở mép phải; nút PWA dạng FAB cũ nằm cố định góc
trái và che một phần danh sách proof. Source hiện tại đã có media rule bọc header
và quy tắc placement inline trong `portal-theme.css`; cần recheck sau delivery,
không được suy diễn source xanh thành `LIVE_PASS`.
