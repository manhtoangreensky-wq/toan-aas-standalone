# R218-07B — Trung tâm hỗ trợ khách hàng: control-level UI/UX

Ngày 2026-10-18. Phạm vi chỉ là WebApp standalone; đây là lát control-level,
không phải bằng chứng runtime, ticket Bot, provider, thanh toán hoặc triển khai.

## 1. Phạm vi route

- Khách hàng: `/support`, `/tickets`, `/tickets/:id`.
- Nhân sự được cấp quyền: `/admin/support`, `/admin/support/:id`.
- Bằng chứng: chỉ chọn tệp đã tồn tại trong Asset Vault riêng của tài khoản;
  Trung tâm hỗ trợ không nhận upload bytes thô.

## 2. Bảng control bắt buộc

| Nhóm | Control và trạng thái phải thể hiện |
|---|---|
| Tiếp nhận | Nhóm yêu cầu, tiêu đề, mô tả, mức ưu tiên, liên kết ngữ cảnh; thiếu phiên/quyền thì khóa rõ lý do |
| Danh sách | Lọc nhóm/trạng thái, phân trang, số liệu theo trạng thái, rỗng/đang tải/lỗi/bảo vệ; chỉ hiển thị record thuộc owner |
| Chi tiết | Mã yêu cầu, revision, dòng thời gian, phản hồi, trạng thái, đóng/mở lại và hướng xử lý an toàn |
| Phản hồi | Gửi phản hồi khách hàng, giữ bản nháp khi hydration; không hiển thị nội dung audit riêng tư |
| Bằng chứng | Chọn Asset Vault, xác nhận đã che dữ liệu nhạy cảm, giới hạn loại/kích thước, liên kết theo revision; tải qua signed route khi server cho phép |
| Quản trị | Phản hồi công khai/nội bộ tách riêng; cập nhật trạng thái/mức ưu tiên có ghi chú, role và revision do server xác minh |
| Hỗ trợ theo ngữ cảnh | Tư vấn, checklist và liên kết task/report chỉ tạo bản nháp hoặc reference, không tự tạo ticket/provider/job |

## 3. Quy tắc trình bày

- Một workspace dọc, thứ tự thao tác từ tiếp nhận → danh sách → chi tiết →
  phản hồi/bằng chứng; mobile `<=620px` chuyển lưới case thành một cột.
- Giữ palette xanh dương/xanh ngọc; không dùng nền đen. Trạng thái guarded,
  rỗng, lỗi và đang tải phải có nội dung giải thích, không dùng dữ liệu giả.
- Bản Việt dùng “Trung tâm hỗ trợ khách hàng” và từ ngữ tự nhiên; bản EN/ZH
  dùng catalogue riêng, không rơi chuỗi giữa các locale.
- Giữ target thao tác, focus-visible, nhãn form và thứ tự bàn phím; không đổi
  route/action/field/capability/CSRF/idempotency/revision.

## 4. Ranh giới an toàn

- Không gọi Bot, Telegram, provider, OAuth, email, wallet/Xu, PayOS hoặc
  notification ngoài Web.
- Không tự suy diễn trạng thái nhà cung cấp, hoàn tiền, giao tệp hoặc đã xử lý.
- Mọi write thật phải dừng ở capability, CSRF, ownership, revision và
  idempotency do máy chủ xác nhận; control-level không được gọi là runtime PASS.

## 5. Bằng chứng lát hiện tại

- `tests/support-hub-product-controls.test.mjs`: **4/4**.
- Full `node --test tests/*.test.mjs`: **566/566**.
- `node --check static/portal/portal.js`: đạt.
- `node --check static/portal/portal-i18n.js`: đạt.
- `git diff --check`: đạt.

## 6. Điều kiện đóng

Lát này chỉ chuyển từ `[~]` sang `[x]` sau khi có renderer/interaction,
browser/AX evidence trên VI/EN/ZH và ma trận desktop/tablet/mobile. Capability
server, dữ liệu thật, upload/preview, queue, delivery, CI, deploy và LIVE vẫn là
cổng riêng trong R218-10..13.
