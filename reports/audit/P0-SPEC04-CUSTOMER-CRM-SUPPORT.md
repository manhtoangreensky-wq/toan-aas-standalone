# Báo cáo Triển khai & Nghiệm thu SPEC-04: Customer CRM & Support

**Chương trình:** `P0.WEB.ERP.PRODUCTION_COMPLETION`  
**Spec:** `P0.WEB.ERP.SPEC04.CUSTOMER.CRM_SUPPORT`  
**Quy chuẩn áp dụng:** `owner-governed-codex`, `locked-focus-engineering`, `single-agent-anti-overengineering`  
**Baseline SHA:** `2cb8d1431361feb4fef44e272f82b69551332cda`  
**Target Host:** `tg.toanaas.vn`  
**Trạng thái nghiệm thu:** `PASS (100% Tiêu chí Đạt, Đóng SPEC-04 Toàn diện)`  

---

## 1. Tuyên bố Mở đầu Bắt buộc
Đang đọc và áp dụng skill owner-governed-codex cho task này.

---

## 2. Mục tiêu Vận hành (Owner Purpose)
Xây dựng phân hệ CRM & Hỗ trợ khách hàng (Customer / CRM / Support) tinh gọn, trung thực, an toàn tuyệt đối cho ERP vận hành:
1. Xác định chính xác khách hàng là ai (`CUSTOMER_MASTER = WEB_SQLITE`, bảng `web_accounts`).
2. Xác minh định danh Web đã nối với Telegram hay chưa theo mô hình liên kết độc lập (`FEDERATED_IDENTITY_LINK`), không tự ý hợp nhất dữ liệu bừa bãi.
3. Đọc ngữ cảnh sản phẩm / dịch vụ an toàn từ profile và workspace setup.
4. Quản lý yêu cầu hỗ trợ qua bảng `web_support_cases` và `web_support_messages` do Web sở hữu.
5. Xác định rõ sự việc cần admin chú ý dựa trên sự thật cụ thể (`action_required`).
6. Trích xuất sự thật về nạp tiền, thanh toán và tác vụ ở chế độ chỉ đọc trung thực (`UNAVAILABLE` khi chưa có bridge, tuyệt đối không tạo số dư 0 ảo).

---

## 3. Hợp đồng Thẩm quyền & An toàn Dữ liệu (Authority Contract)
- `CUSTOMER_MASTER`: `WEB_SQLITE` (`web_accounts`, PK `id`)
- `SUPPORT_CASE_AUTHORITY`: `WEB_SQLITE` (`web_support_cases`, PK `id`)
- `TELEGRAM_IDENTITY`: `FEDERATED_IDENTITY_LINK` (`web_accounts.canonical_user_id`, `telegram_link_codes`)
- `WALLET_AUTHORITY`: `BOT_CORE`
- `JOB_AUTHORITY`: `BOT_CORE / CORE_BRIDGE_READ_MODEL`
- `PAYMENT_GATEWAY_AUTHORITY`: `PAYOS`
- `WEB_DIRECT_WALLET_MUTATION`: **NO**
- `WEB_DIRECT_BOT_DB_WRITE`: **NO**
- `WEB_DIRECT_PAYOS_SETTLEMENT`: **NO**
- `IDENTITY_RELINK_WRITE_ACTIONS`: **0**
- `MANUAL_PAYMENT_SETTLEMENT_ACTIONS`: **0**
- `SCHEMA_CHANGE_REQUIRED`: **NO** (Không tạo bảng mới, tận dụng hoàn toàn schema hiện hữu).

---

## 4. Xác Định & Đóng Lỗi Đầu Tiên (First-Red Resolution)
- **First-Red:** Trước đây `_filters(q, status)` trong `copyfast_admin_customer_directory.py` chỉ tìm theo `display_name` và `email`, không tìm được theo Web Customer ID (`a.id`) hoặc Telegram User ID (`a.canonical_user_id`). Đồng thời hệ thống thiếu hàm đánh giá chuẩn trạng thái liên kết định danh (`LINKED`, `UNLINKED`, `UNKNOWN`, `CONFLICT`) và bộ tổng hợp ngữ cảnh CRM 7 phần.
- **Giải pháp:**
  - Bổ sung `copyfast_customer_crm_policy.py`: chuẩn hóa trạng thái định danh liên kết, hàm tổng hợp `synthesize_customer_crm_context`.
  - Nâng cấp `copyfast_admin_customer_directory.py`: mở rộng `_filters` tìm kiếm giới hạn theo cả `a.id` và `a.canonical_user_id`, bổ sung endpoint `GET /api/v1/admin/customers/{account_id}/crm`.
  - Giữ nguyên vẹn 100% hợp đồng cũ cho `admin-customer-directory.js` để bảo toàn kiểm thử hồi quy.

---

## 5. 7 Phân Vùng Chi Tiết Khách Hàng (Customer Detail CRM Sections)
1. **OVERVIEW:** ID khách hàng, tên hiển thị, email công khai, trạng thái tài khoản, loại tài khoản, vai trò, thời gian tạo/cập nhật.
2. **IDENTITY:** Mô hình liên kết Telegram `FEDERATED`, trạng thái `LINKED` / `UNLINKED` / `UNKNOWN` / `CONFLICT`, ID Telegram, bằng chứng liên kết, 0 thao tác gán chéo.
3. **SERVICE CONTEXT:** Ngôn ngữ, múi giờ, kiểu avatar, tiến trình khởi tạo workspace.
4. **SUPPORT:** Tổng số case, số case đang mở, danh sách case gần nhất từ `web_support_cases`.
5. **PAYMENTS / TOPUPS:** Tổng số yêu cầu nạp, số yêu cầu chờ duyệt từ `web_manual_topup_requests`, 0 thao tác quyết toán thủ công.
6. **WALLET SUMMARY:** Nguồn `BOT_CORE`, trạng thái `UNAVAILABLE`, số dư `null` (không tạo số 0 giả mạo).
7. **JOBS SUMMARY:** Nguồn `BOT_CORE / CORE_BRIDGE_READ_MODEL`, trạng thái `UNAVAILABLE`.
8. **ACTION REQUIRED:** Chỉ kích hoạt khi có sự thật: case hỗ trợ đang mở, yêu cầu nạp tiền chờ duyệt, hoặc xung đột định danh.

---

## 6. Kết Quả Kiểm Thử & Chốt Chặn An Toàn
- **Kiểm thử chuyên biệt SPEC-04:** 8/8 tests PASSED (`tests/test_p0_spec04_customer_crm_support.py`).
- **Toàn bộ bộ kiểm thử hồi quy:** 91/91 tests PASSED (SPEC-00, SPEC-01, SPEC-02, SPEC-03, SPEC-03B, SPEC-04, portal contracts).
- **Lỗi mới phát sinh:** **0** (`NEW_FAILURES=0`).
- **Chốt chặn an toàn:**
  - `PROVIDER_CALLS`: 0
  - `WALLET_MUTATIONS`: 0
  - `PAYMENT_MUTATIONS`: 0
  - `BOT_DB_MUTATIONS`: 0
  - `ENV_MUTATIONS`: 0
  - `PRODUCTION_DB_SCHEMA_MUTATIONS`: 0

---

## 7. Kết Luận Nghiệm Thu
- **SPEC04_PASS:** **YES**
- **BLOCKERS:** **NONE**
