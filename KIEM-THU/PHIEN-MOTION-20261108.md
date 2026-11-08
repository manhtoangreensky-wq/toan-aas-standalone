# Phiên kiểm thử chuyển động — 08/11/2026

SESSION_ID=MOTION-LIFECYCLE-20261108
STATUS=DEPLOYED_RUNTIME_VERIFIED_SIGNED_LIVE_OPEN
BASE_SHA=b7a639cbdca7d5b56b4e238d956ad3af2e636bbb
SOURCE_SHA=27175790f3ee01112684149dbbccdff0033c4b2b
PRODUCTION_LIVE=NOT_TESTED

Sổ duy nhất: [Issue689](https://github.com/manhtoangreensky-wq/toan-aas-standalone/issues/689).
Receipt: [chuyển động](../docs/reports/motion-20261108.md); bằng chứng tổng hợp: [Chrome](../reports/ui-qa/motion-20261108/lifecycle-browser.json).

- [x] RED thực tế: menu2lỗi/sáu chốt an toàn; landing dynamic reduce còn nút bật nhưng vô tác dụng.
- [x] Antigravity trả patch; review allowlist hai tệp JS, không đổi backend/route/DTO/auth authority.
- [x] FullNode1877/1877; nhóm33/33; hai mutation chứng minh test bắt lỗi cũ.
- [x] Chrome menu8/8; landing normal replay lần2 + dynamic/initial reduce đạt.
- [x] Independent release review:12/12;0Critical/0Important; public links/JSON/provenance reviewed.
- [x] Exact-commit CI `42517213551`: Web/Auth/browser/runtime/whitespace all SUCCESS.
- [x] Merge `745fabbd`, deploy `42518106973`, runtime SHA/service health verified.
- [ ] Signed production interaction và đo giật còn lại. Không đánh dấu toàn goal hoàn tất.
- [x] F2 hidden copilot scroll: browser đóng 0 đọc/ghi, mở 4 ghi, bản gõ giữ; Node trợ lý22/22.
- [x] F1 startup layout getter: một dòng worker patch; source test và Chrome profile đạt; Layout harness75,07ms diagnostic.
- [x] Exact-commit CI/merge/deploy cho F1/F2.

Chạy lại phần repository-owned:
```powershell
node --test tests/customer-sidebar-hydration.test.mjs tests/landing-reduced-replay-cleanup.test.mjs tests/customer-header-hydration.test.mjs tests/customer-command-palette-hydration.test.mjs tests/current-main-motion-static-gates.test.mjs tests/r216-motion-lifecycle-compositor.test.mjs
node --check static/portal/portal.js
node --check static/portal/portal-motion.js
```

Trình duyệt: menu đang mở tại390px → dữ liệu nền cùng trang/cùng phiên → vẫn mở/giữ focus; Escape → đóng/trả focus nút menu. Lặp thường/giảm chuyển động. Sau đổi trang/phiên/đăng xuất/Admin/locale/tên đầu trang → đóng và nền hết inert. Landing thường bấm phát lại → sequence tăng; đổi giảm chuyển động → nút ẩn/không focus; tải đầu giảm chuyển động → static. Không gọi provider, tạo job, thao tác ví hoặc dữ liệu production.

VPS runtime đã đối chiếu sau deploy. Signed production interaction qua trình duyệt người dùng và FPS/long-task trên thiết bị thật vẫn chưa có bằng chứng trực tiếp; không thay thế bằng HTTP200 hoặc QA cô lập.
