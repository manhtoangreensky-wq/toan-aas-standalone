# TOAN AAS — MA TRẬN ĐỐI SOÁT NGHIỆP VỤ KHÁCH HÀNG ↔ QUẢN TRỊ (ADMIN-LINK-01)

- **Mã kiểm toán:** `ADMIN-CUSTOMER-LINK-AUDIT-MATRIX-001`
- **Tiêu chuẩn áp dụng:** `owner-governed-codex` & `toanaas-system-design-and-open-apis`
- **Phiên bản:** `1.0.0`
- **Ngày lập:** `2026-09-15`
- **Hệ thống mục tiêu:** TOAN AAS Web App & Admin ERP (`tg.toanaas.vn`)

---

## 1. TỔNG QUAN KIẾN TRÚC PHÂN TẦNG QUYỀN HẠN

Hệ thống TOAN AAS Web App chia tách quyền hạn thành 3 phân vùng quản trị độc lập và khép kín:

| Tầng quyền hạn | Định danh Authority | Số lượng Routes | Mô tả & Trách nhiệm |
|---|---|---|---|
| **Support Staff** | `support_staff` | **5** | Nhân viên hỗ trợ kỹ thuật và CSKH (`/admin/support`, `/admin/tickets`, `/admin/documents`, `/admin/customers`, `/admin/access`). Không có quyền tài chính hoặc can thiệp hạ tầng. |
| **Local Web Admin** | `web_local_admin` | **11** | Quản trị viên cục bộ Web App (`/admin/topups`, `/admin/system-stewardship`, `/admin/audit`, v.v.). Vận hành độc lập trên SQLite Web, chỉ có quyền từ chối (`reject_only`) đơn nạp sai lệch để bảo vệ ví tiền. |
| **Canonical Admin** | `canonical_admin` | **34** | Quản trị viên cấp cao đồng bộ qua Core Bridge với Telegram Bot Core. Nắm quyền kiểm soát doanh thu, tài chính, worker, provider, pricing và jobs. |

---

## 2. MA TRẬN ĐỐI SOÁT HÀNH ĐỘNG NGHIỆP VỤ (CUSTOMER → ADMIN)

| Mã nghiệp vụ | Hành động Khách hàng (Customer Web) | Tuyến đường Khách hàng | Tuyến đường Quản trị đối soát (Admin ERP) | Tầng quyền Admin | Cơ chế An toàn & Sổ cái |
|---|---|---|---|---|---|
| **LINK-01** | Tạo yêu cầu nạp tiền thủ công (VietQR / Ngân hàng / Ví điện tử) | `/wallet/topup` (`manual`) | `/admin/topups` | `web_local_admin` | Xác nhận 2 bước (Draft → Modal Confirm). Web-local Admin chỉ `reject_only`. Duyệt cộng Xu thực hiện qua Bot Core. |
| **LINK-02** | Khởi tạo giao diện thanh toán trực tuyến PayOS | `/wallet/topup` (`payos`) | `/admin/payments` & `/admin/finance` | `canonical_admin` | Webhook PayOS độc quyền về Bot Core; Web chỉ đọc payment catalog và redirect checkout an toàn. |
| **LINK-03** | Đăng ký tài khoản mới & Đăng nhập phiên làm việc | `/register`, `/login` | `/admin/customers` | `support_staff` / `web_local_admin` | Mật khẩu băm PBKDF2/SHA-256; Session token HTTP-only ký HMAC; Redaction thông tin nhạy cảm. |
| **LINK-04** | Gửi yêu cầu hỗ trợ kỹ thuật hoặc tư vấn | `/support`, `/tickets` | `/admin/support` | `support_staff` | Form hỗ trợ độc lập trên Web, gắn ID phiên; nhân viên CSKH tra cứu lịch sử xử lý tại Admin. |
| **LINK-05** | Khởi tạo tác vụ sáng tạo nội dung (Ảnh, Video, Voice) | `/projects`, `/image-studio`, `/video-studio` | `/admin/jobs` & `/admin/workers` | `canonical_admin` | Job xếp hàng kiểm soát quota; Admin theo dõi hàng đợi worker và trạng thái delivery của từng job. |
| **LINK-06** | Xử lý lỗi tác vụ hoặc yêu cầu hoàn phí | `/jobs` (trạng thái failed/retry) | `/admin/jobs/failed` & `/admin/refunds` | `canonical_admin` | Retry và Refund yêu cầu chữ ký Admin cấp cao qua Core Bridge, chống double-charge và double-refund. |
| **LINK-07** | Đăng ký nhu cầu hợp tác / Partner Readiness | `/partner-readiness`, `/crm/leads` | `/admin/partners` & `/admin/leads` | `canonical_admin` | Thu thập thông tin doanh nghiệp, phân luồng CRM để đội ngũ kinh doanh tiếp cận. |
| **LINK-08** | Tra cứu bảng giá dịch vụ & Mua gói định kỳ | `/packages`, `/pricing` | `/admin/packages` & `/admin/pricing` | `canonical_admin` | Bảng giá đồng bộ từ backend canonical; không cho phép client tự sửa mức giá hoặc chiết khấu. |
| **LINK-09** | Quản lý bộ nhớ sáng tạo & Template Prompts | `/notes`, `/prompt-library` | `/admin/documents` | `support_staff` | Lưu trữ cá nhân trong Asset Vault; Admin chỉ lưu trữ tài liệu hướng dẫn chuẩn hóa của hệ thống. |
| **LINK-10** | Thiết lập ngôn ngữ giao diện (VI, EN, ZH) | `/account/interface-language` | 50 routes Admin ERP | Toàn bộ 3 tầng | Đồng bộ tự động qua `TOANAASI18n`; 100% route Admin và Customer có Title & Description song ngữ. |

---

## 3. KẾT LUẬN KIỂM TOÁN TÍNH TOÀN VẸN (ZERO-ORPHAN VERDICT)

1. **Tính khép kín (Zero-Orphan Route):** 100% các hành vi giao dịch, thanh toán, hỗ trợ và vận hành của Khách hàng đều có route Admin giám sát tương ứng. Không tồn tại luồng thao tác "mồ côi" không có điểm kiểm soát.
2. **Tuân thủ Chốt chặn An toàn của Owner (Gate 4):** Không có route Web nào được phép tự ý thay đổi số dư ví tiền Xu ngoài sự kiểm soát của Telegram Bot Core (`WALLET_MUTATIONS=0`).
3. **Phân định ranh giới rõ ràng:** Quyền hạn nhân viên CSKH (`support_staff`) được cô lập hoàn toàn khỏi hệ thống ví và tài chính doanh nghiệp.
