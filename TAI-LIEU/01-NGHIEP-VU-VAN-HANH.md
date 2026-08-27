# Nghiệp vụ vận hành hiện tại — TOAN AAS Web App

Đo ngày 27/08/2026 tại branch `feature/admin-vi-en-shell-001`, BASE `2c348fead702528fe5b7b82a3b39b14550d4d1aa`.

## 1. Hệ thống gồm những gì

1. `app.py` là entrypoint FastAPI production.
2. `copyfast_pages.py` phát vỏ HTML và version asset.
3. `copyfast_auth.py` quản lý signed session, CSRF và quyền tài khoản.
4. `copyfast_api.py` cung cấp API Web/bridge; toàn source production hiện có `694` route decorator FastAPI trong `76` file Python production. Số này đo bằng AST trên `FunctionDef/AsyncFunctionDef` và loại `tests/docs/reports/node_modules/evidence/cache`.
5. `static/portal/portal.js`, `portal-i18n.js`, `portal-theme.css` dựng giao diện khách và Admin.
6. `static/portal/integration.js` hydrate dữ liệu đã được máy chủ cấp; browser không tự phong quyền.
7. Production chạy trên Ubuntu VPS `tg.toanaas.vn`; luồng ship là GitHub `main` → Actions → `/opt/toanaas/webapp` → systemd.

## 2. Phạm vi batch Admin này

- `3` file runtime giao diện được sửa: `portal.js`, `portal-i18n.js`, `portal-theme.css`.
- `8` file test/comparator được sửa hoặc tạo.
- `4` file tài liệu/tester được sửa: hai tài liệu vận hành và hai file trong `KIEM-THU/`.
- Tổng working tree trước commit: đúng `15` path (`3` runtime + `8` test/comparator + `4` tài liệu/tester).
- `0` file backend/Auth/API/DB/schema/ENV bị sửa.
- Portal hiện có `48` đăng ký trang Admin: đếm `49` occurrence `adminPage(` rồi trừ `1` function declaration.
- Repo hiện có `352` file khớp `tests/**/test_*.py`.

## 3. Admin đang vận hành như thế nào

### Shell và điều hướng

- App switcher lấy duy nhất từ `adminErpNavigation(context).groups` do máy chủ cấp.
- Sidebar chỉ hiện module của app đang mở; không liệt kê toàn hệ thống trong một drawer.
- Breadcrumb có ba tầng: TOAN AAS → app → trang.
- Locale chính của Admin là `vi/en` trong cùng DOM/component/route; không fork codebase.
- Admin không hiện PWA App FAB, AAS Bot, ví hoặc hạng thành viên của giao diện khách.
- Admin không chạy generic enter motion; nội dung first paint có opacity `1`, transform `none`, animation `none`.

### Dashboard

- KPI đọc từ `context.adminData.counts` và readiness do máy chủ trả.
- Biểu đồ thanh chỉ so sánh snapshot hiện tại; không có line chart ngày/tháng vì backend chưa cấp time series.
- Donut readiness tính từ số item `public_ready=true`; dữ liệu rỗng không vẽ `0/0` giả.
- Bảng Chi tiết kết nối có cột `STT` đánh số `1-based`, giữ toàn bộ readiness rows và không còn cắt `slice(0, 8)`.
- Cột Trạng thái render text locale hóa riêng; không dùng shared `badge()` vì helper đó cố ý trả rỗng cho `ready/guarded`.

### Bảng dữ liệu

Năm surface đã có pattern list/filter/detail thật:

| Surface | Trường đã được server redaction và Portal hiển thị |
|---|---|
| Users | ID, tên hiển thị, số dư, đã dùng, gói, ngày tạo |
| Jobs | ID, tính năng, trạng thái, chi phí, cập nhật, output, delivery, action canonical |
| Payments | mã PayOS, người dùng, VNĐ, Xu, loại, trạng thái, cập nhật |
| Providers | tính năng, trạng thái, lý do rút gọn, cập nhật |
| Tickets | mã, loại, ưu tiên, trạng thái, đính kèm, cập nhật |

- Tìm kiếm local bỏ dấu, không gọi API mới.
- Filter status chỉ lấy marker đang nhìn thấy trong bảng.
- Chọn dòng bằng click/Enter/Space; action button trong row không bị hijack.
- Inspector chỉ đọc header/cell đã hiển thị, tạo DOM bằng `textContent`; không nhận raw JSON hoặc hidden field.
- XSS fixture được giữ thành text; số lần thực thi đo được `0`.

## 4. Ai được làm gì

- Route, app, module và dữ liệu Admin do máy chủ cấp theo signed session.
- Browser chỉ lọc/chiếu dữ liệu đã tải; không grant role, không thêm field, không ghi DB.
- Retry/refund/freeze chỉ dùng action hiện có và vẫn cần capability, CSRF, confirmation, idempotency/audit ở server.
- Batch này không gọi provider, không đổi ví/Xu/PayOS và không thay dữ liệu production.

## 5. Ngôn ngữ

- Source gate VI quét đúng `13` key Data View và `17` key shared Jobs; forbidden hit `0`.
- Mutation `Ledger` tạo đúng `1` failing test rồi đã được khôi phục; targeted cuối trở lại xanh.
- Whole-surface locale probe local đã tái sinh sau patch cho `5 route × 2 locale`, `failureCount=0`; kết quả local không được suy thành LIVE PASS.
- Server row data, ID, tên người dùng và enum nguồn không bị tự dịch.
- Keyset `vi/en/zh` của bundle vẫn bằng nhau; Admin primary switch chỉ đưa `vi/en` cho Owner.

## 6. Bằng chứng local hiện tại

- Combined Admin fresh sau patch Jobs + STT: `53 passed`.
- Fresh protected aggregate: `64 passed`.
- Node syntax `portal.js/i18n/integration`: `3/3` exit `0`.
- Python compile: exit `0`.
- `git diff --check`: exit `0`.
- Dashboard R2 mới nhất và Data Views R1 đều `PASS`, `failureCount=0`, dirty scope `15/15`; Dashboard tại cả `4` viewport có status VI `Sẵn sàng/Sẵn sàng/Cần kiểm tra`, EN `Ready/Ready/Needs review`; whole-surface locale probe `5 route × 2 locale` có `failureCount=0`.
- Comparator CI cũ đòi desktop sidebar đủ `13` group đã được sửa theo requirement mới: sidebar chỉ chiếu active group, còn command palette vẫn giữ toàn bộ route server-issued.
- Signed Admin production vẫn `LIVE_PASS=NOT_TESTED` vì chưa có Browser output thật sau patch.

## 7. Bẫy vận hành và nguyên nhân gốc

- `MERGED != DEPLOYED != LIVE`; HTTP 200 không chứng minh Admin signed render đúng.
- Full-file hash của shared theme không phải comparator bền vững khi chính theme là allowlist sửa; phải giữ semantic motion tests và hash file motion riêng.
- Donut từng có `backgroundImage=none`: custom property gradient khai ở ancestor tham chiếu angle chỉ tồn tại ở descendant nên invalid tại computed time. Gradient phải resolve trên chính donut.
- Data view từng chia layout hai lần: outer work-grid rồi inner table/inspector làm list còn `335px`. Generic data page phải full-width trước khi chia list/inspector.
- Global `badge()` cố ý ẩn `ready/guarded`; Provider filter cần marker status riêng, không sửa badge toàn hệ thống và không suy từ raw item.
- Test stub `badge()` của Dashboard từng khác production semantics nên che lỗi cột trạng thái rỗng; comparator hiện mô phỏng đúng `badge()` production và assert trực tiếp status text.
- Dịch riêng control mới là chưa đủ: hero, guard, scope, aside, notes, header và status option đều là fixed chrome phải qua locale gate.

## 8. Việc còn treo

- Batch Admin chưa commit/push/PR/deploy tại thời điểm tài liệu này được cập nhật.
- Production signed `/admin` chưa được Browser kiểm vì Chrome extension trả `ERR_BLOCKED_BY_CLIENT`; local fixture PASS không phải LIVE PASS.
- Nền Admin + năm surface đã đạt; chưa phải đủ `21` module theo tài liệu Owner. Module còn lại cần Bot/data/role contract, thiếu nguồn phải ghi `BLOCKED_SOURCE_MISSING`.
- App nội bộ mobile-first là wave riêng, chưa được gộp vào batch ship này.
- GitHub Projects chưa đọc/tạo được vì token thiếu scope `read:project`; issue #412 và labels vẫn là tracker hiện hành.
