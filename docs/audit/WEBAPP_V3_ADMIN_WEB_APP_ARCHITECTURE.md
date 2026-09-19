# WEBAPP V3 ADMIN WEB & INTERNAL APP ARCHITECTURE AUDIT

> **Mã nhiệm vụ**: `P0.WEBAPP.V3.FULL.PRODUCT.IA.UX.ADMIN.REBASE.AUDIT`  
> **Chương trình**: `P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1`  
> **Repository**: `manhtoangreensky-wq/toan-aas-standalone`  
> **Trạng thái**: `CANONICAL AUDIT & REPLAN`  
> **Ngày lập**: 19/09/2026

---

## 1. MÔ HÌNH VẬN HÀNH ADMIN WEB (ADMIN WEB OPERATING MODEL)

Admin Web của hệ sinh thái TOAN AAS được định vị là:
**ĐIỀU HÀNH CHIẾN LƯỢC (EXECUTIVE MANAGEMENT) + VẬN HÀNH HỆ THỐNG (SYSTEM OPERATIONS) + CHĂM SÓC KHÁCH HÀNG (CUSTOMER OPERATIONS)**.

Admin cho phép người quản trị có thẩm quyền quan sát và xử lý toàn diện các thực thể kinh doanh mà khách hàng thao tác trên Web/Bot, nhưng **tuyệt đối không biến thành một trình chỉnh sửa cơ sở dữ liệu tùy tiện (Arbitrary Database Editor)**.

### 1.1. 13 Phân Hệ Quản Trị Trọng Yếu (Admin Target Domains)

```
┌────────────────────────────────────────────────────────────────────────┐
│                        TOAN AAS ADMIN WEB CONTROL                      │
├───────────────────┬───────────────────┬────────────────────────────────┤
│ 1. TỔNG HÀNH DINH │ 2. KHÁCH HÀNG CRM │ 3. QUẢN LÝ SẢN PHẨM            │
│ (Executive Cmd)   │ (Customer 360)    │ (Product Catalog)              │
├───────────────────┼───────────────────┼────────────────────────────────┤
│ 4. GIÁ & GÓI CƯỚC │ 5. TÀI CHÍNH      │ 6. HÀNG ĐỢI & JOBS             │
│ (Dynamic Pricing) │ (Topup, Ledger)   │ (Queue & Orchestrator)         │
├───────────────────┼───────────────────┼────────────────────────────────┤
│ 7. KHO THÀNH PHẨM │ 8. XUẤT BẢN       │ 9. HẠ TẦNG & PROVIDER          │
│ (Delivery Vault)  │ (Social Dispatch) │ (Health & Rate Limits)         │
├───────────────────┼───────────────────┼────────────────────────────────┤
│ 10. SỨC KHỎE HT   │ 11. NHẬT KÝ AUDIT │ 12. PHIẾU HỖ TRỢ               │
│ (System & Workers)│ (Security & Trace)│ (Support Desk)                 │
├───────────────────┴───────────────────┴────────────────────────────────┤
│ 13. BÁO CÁO & PHÂN TÍCH DOANH NGHIỆP (Analytics & Cohort Insights)    │
└────────────────────────────────────────────────────────────────────────┘
```

### 1.2. Bộ 5 Câu Hỏi Bất Biến Cho Mọi Màn Hình Admin (5 Operational Questions)
Mỗi trang quản trị phải cung cấp câu trả lời tức thì cho người điều hành:
1. **Chuyện gì đang diễn ra? (WHAT IS HAPPENING?)**: Tổng số đơn, số lượng job đang chạy, doanh thu nạp trong ngày.
2. **Điểm nào cần can thiệp ngay? (WHAT NEEDS ATTENTION?)**: Có đơn nạp tiền nào bị nghẽn? Có job render nào bị timeout? Có provider nào hết tiền?
3. **Tại sao lại xảy ra? (WHY?)**: Lý do khách quan (ngân hàng chưa khớp mã, provider trả lỗi 429 quá tải, khách hàng thiếu số dư).
4. **Tôi được phép làm gì an toàn? (WHAT MAY I SAFELY DO?)**: Các nút hành động có thẩm quyền (Duyệt nạp tiền 2 bước, Thử lại job, Đổi provider dự phòng).
5. **Điều gì đã xảy ra sau khi tôi thao tác? (WHAT HAPPENED AFTER I DID IT?)**: Nhật ký kiểm toán ghi nhận tức thì (Ai làm, lúc nào, kết quả ra sao, mã biên nhận).

---

## 2. MA TRẬN LIÊN KẾT KHÁCH HÀNG <-> QUẢN TRỊ (CUSTOMER-ADMIN LINKAGE MATRIX)

Admin có thể giám sát toàn bộ hoạt động của khách hàng một cách độc lập mà **không cần mạo danh (impersonate) khách hàng**:

| Năng Lực Khách Hàng | Tuyến Khách Hàng | Thực Thể Dữ Liệu | Tuyến Quản Trị Danh Sách | Tuyến Quản Trị Chi Tiết | Thao Tác Admin Được Phép | Thẩm Quyền Gốc (Authority) |
|:---|:---|:---|:---|:---|:---|:---|
| Tạo Video AI | `/studio` | `video_jobs` | `/admin/jobs?type=video` | `/admin/jobs/{id}` | Xem prompt, tiến độ scene, hủy job treo, thử lại cảnh lỗi | Bot SQLite `video_jobs` |
| Tạo Giọng Nói TTS | `/voice` | `voice_jobs` | `/admin/jobs?type=voice` | `/admin/jobs/{id}` | Nghe thử file kết quả, kiểm tra vi phạm nội dung | Bot SQLite `voice_jobs` |
| Nạp Tiền Chuyển Khoản | `/wallet/topup` | `web_manual_topup_requests` | `/admin/topups` | `/admin/topups?id={id}` | Phê duyệt 2 bước, từ chối kèm lý do | Web DB + Bot Core Ledger |
| Xem Số Dư & Lịch Sử Ví | `/wallet` | `credit_events` | `/admin/wallet` | `/admin/wallet/{user_id}` | Xem đối soát sổ cái. **CẤM sửa số dư tùy ý** | Bot SQLite `credit_events` |
| Gửi Yêu Cầu Hỗ Trợ | `/support/tickets` | `web_support_tickets` | `/admin/tickets` | `/admin/tickets/{id}` | Trả lời khách hàng, đóng/mở ticket, gán nhân viên | Web DB `web_support_tickets` |
| Xem Bảng Giá | `/pricing` | `dynamic_pricing_catalog` | `/admin/pricing` | `/admin/pricing/{sku}` | Tạo bản nháp giá, tính diff biên lợi nhuận, xuất bản | Web DB `dynamic_pricing` |

---

## 3. TRIẾT LÝ GHI DỮ LIỆU CỦA ADMIN (ADMIN WRITE PHILOSOPHY)

Để bảo đảm an toàn dữ liệu tuyệt đối theo tiêu chuẩn của Owner:
1. **Chỉ ghi dữ liệu tại nơi có thẩm quyền xác thực (Canonical Authority)**: Admin chỉ thực hiện các thao tác CRUD khi đã có API adapter kiểm chứng tính hợp lệ và ghi nhận kiểm toán (audit).
2. **Khóa chặt các cổng nhạy cảm (Owner Safety Gates)**:
   - Tuyệt đối cấm chỉnh sửa biến môi trường (`ENV`), token, API keys trên giao diện Web.
   - Tuyệt đối cấm can thiệp trực tiếp mã SQL vào database production.
   - Tuyệt đối cấm tạo endpoint nạp/trừ tiền tùy ý mà không qua quy trình đối soát biên lai nạp tiền hoặc hoàn tiền chính thức.
   - Tuyệt đối cấm khởi động lại dịch vụ máy chủ từ giao diện web thông thường.
3. **Phản hồi minh bạch khi chưa hỗ trợ (Fail-Closed)**: Bất kỳ tính năng quản trị nào chưa có adapter backend thật sẽ hiển thị trạng thái `ĐANG BẢO VỆ / CHƯA KHẢ DỤNG (GUARDED)`, nêu rõ adapter còn thiếu thay vì hiển thị nút bấm giả gây mất dữ liệu.

---

## 4. MÔ HÌNH ỨNG DỤNG NỘI BỘ (ADMIN MOBILE APP MODEL)

Admin Mobile App được thiết kế theo nguyên tắc:
**TOÀN BỘ NĂNG LỰC ADMIN WEB AN TOÀN + PHÂN HỆ VẬN HÀNH DOANH NGHIỆP NỘI BỘ**.

Ứng dụng dùng chung hệ thống danh tính (`auth`) và hợp đồng API backend với Web App, không tạo ra một backend độc lập thứ hai.

### 4.1. Đối Chiếu 21 Phân Hệ Từ Tài Liệu Tham Khảo Của Owner (`bảng chức năng.png`)

| # | Phân Hệ Nghiệp Vụ | Tên Tiếng Anh | Admin Web | App Nội Bộ | Thẩm Quyền / Nguồn Dữ Liệu |
|:---:|:---|:---|:---:|:---:|:---|
| 1 | Quản lý quan hệ khách hàng | Customer Relationship Management (CRM) | `CÓ` | `CÓ` | Web SQLite `web_accounts` + Bot `users` |
| 2 | Quản lý dự án | Project Management | `CÓ` | `CÓ` | Web `web_projects` / Tasks |
| 3 | Quản lý thu chi | Finance & Cash Flow | `CÓ` | `CÓ` | Web DB `web_manual_topups` + PayOS |
| 4 | Quản lý bán hàng | Sales Management | `CÓ` | `CÓ` | Đơn hàng, gói cước, hoa hồng cộng tác viên |
| 5 | Quản lý nhân sự (hồ sơ) | Employee Records | `CÓ` | `CÓ` | Hồ sơ nhân viên, phân quyền vai trò (Role) |
| 6 | Quản lý tài sản thiết bị | Asset & Equipment Management | `CÓ` | `CÓ` | Máy chủ VPS, tài khoản AI (Kling/Veo), thiết bị |
| 7 | Quản lý kho | Inventory Management | `CÓ` | `CÓ` | Kho lưu trữ media, kho tài nguyên template |
| 8 | Quản lý sản xuất | Manufacturing Management | `CÓ` | `CÓ` | Dây chuyền render video, cụm GPU worker |
| 9 | Quản lý mua hàng | Purchase Management | `CÓ` | `CÓ` | Mua credit API, thanh toán thẻ nhà cung cấp |
| 10 | Quản lý mục tiêu kinh doanh | Business Goal Management | `CÓ` | `CÓ` | Doanh số tháng, số lượng video mục tiêu |
| 11 | Mạng xã hội cơ bản | Basic Social Network | `PHỤ` | `CHÍNH` | Bảng tin nội bộ công ty, chia sẻ thành tích |
| 12 | Quản lý OKRs | OKR Management | `CÓ` | `CÓ` | Theo dõi chỉ số then chốt phòng ban |
| 13 | Chấm công & bảng lương | Attendance & Payroll | `CÓ` | `CHÍNH` | Check-in di động, tính công, duyệt lương |
| 14 | Hệ thống chat | Chat System | `CÓ` | `CHÍNH` | Chat nội bộ đội ngũ, thông báo tức thì |
| 15 | Banner PR nội bộ | Internal PR Banners | `CÓ` | `CÓ` | Banner thông báo chiến dịch trên app |
| 16 | Theo dõi khối lượng công việc| Workload Tracking | `CÓ` | `CÓ` | Bảng phân bổ tải công việc theo nhân sự |
| 17 | Phê duyệt yêu cầu | Request Approvals | `CÓ` | `CHÍNH` | Duyệt đơn xin nghỉ, tạm ứng, đề xuất chi phí |
| 18 | AI Business | AI Business Assistant | `CÓ` | `CÓ` | Trợ lý AI hỏi đáp dữ liệu nội bộ |
| 19 | Email doanh nghiệp | Business Email | `CÓ` | `CÓ` | Liên kết hòm thư tác nghiệp |
| 20 | App khách hàng có sẵn | Existing Customer App | `LIÊN KẾT` | `LIÊN KẾT` | Cổng thông tin khách hàng TOAN AAS |
| 21 | App nhân viên có sẵn | Existing Employee App | `LIÊN KẾT` | `LIÊN KẾT` | Ứng dụng tác nghiệp nội bộ nhân viên |

---

## 5. BÀI HỌC TỪ VIDEO & TÀI LIỆU THAM KHẢO (REFERENCE MEDIA LEARNINGS)

Sau khi kiểm tra đối chiếu các tài liệu tham khảo: `web.mp4`, `app mẫu.mp4`, `App nội bộ.mp4`, `web app mẫu.mp4`, `7966686583629.mp4`:

### 5.1. Những Gì Cần Học Hỏi (What to Learn)
1. **Mật độ thông tin cao (Information Density)**: Cách bố trí thẻ số liệu KPI kết hợp bảng chi tiết và bộ lọc linh hoạt giúp người quản lý nắm bắt toàn cục chỉ trong 3 giây.
2. **Khung điều hướng đáy di động (Mobile Bottom Nav 5 mục)**: `Trang chủ` - `Công việc` - `Tạo nhanh (+)` - `Nội bộ` - `Cá nhân`. Giúp thao tác bằng 1 tay nhanh chóng, tránh mở drawer cồng kềnh.
3. **Ngăn chi tiết trượt (Detail Drawer)**: Bấm vào một dòng trong bảng mở ngăn trượt bên phải hiển thị toàn bộ lịch sử mà không cần tải lại trang.

### 5.2. Những Gì TUYỆT ĐỐI CẤM Sao Chép (Forbidden Clones)
1. **Không sao chép thương hiệu, logo hoặc giao diện gốc của Odoo hay các mẫu demo**: Giữ nguyên nhận diện thương hiệu TOAN AAS.
2. **Không đưa số liệu giả lập vào môi trường vận hành**: Không lấy các danh sách sản phẩm, giá tiền hoặc tên nhân sự demo trong video làm dữ liệu thật.
3. **Không áp dụng gamification (sao rơi, quà tặng) vào Admin quản trị**: Giữ Admin sạch sẽ, nghiêm túc, tập trung vào hiệu suất công việc.
