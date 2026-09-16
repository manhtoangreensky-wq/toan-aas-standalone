# Báo cáo Triển khai & Nghiệm thu SPEC-06: Finance Read Model Truth

**Chương trình:** `P0.WEB.ERP.PRODUCTION_COMPLETION`  
**Spec:** `P0.WEB.ERP.SPEC06.FINANCE.READ_MODEL.TRUTH`  
**Quy chuẩn áp dụng:** `owner-governed-codex`, `locked-focus-engineering`, `single-agent-anti-overengineering`, `toanaas-system-design-and-open-apis`  
**Baseline SHA:** `34e45087fd839b118a27f7203fd6d38e7c12dce8`  
**Target Host:** `tg.toanaas.vn`  
**Trạng thái nghiệm thu:** `PASS (100% Tiêu chí Đạt, Đóng SPEC-06 Toàn diện)`  

---

## 1. Tuyên bố Mở đầu Bắt buộc
Đang đọc và áp dụng skill owner-governed-codex cho task này.

---

## 2. Mục tiêu Vận hành (Owner Purpose)
Xây dựng phân hệ Tài chính (Finance / Payments / Topups) dạng Read-Model trung thực, an toàn tuyệt đối cho ERP:
1. **Sự kiện dòng tiền:** Quản trị viên nắm bắt minh bạch mọi sự kiện phát sinh liên quan đến tiền bạc, topup yêu cầu, thanh toán PayOS và trạng thái ví.
2. **Phân biệt rạch ròi 3 tầng thanh toán:**
   - **Tầng yêu cầu nạp (Topup Request):** Quản lý trên Web SQLite (`web_manual_topup_requests`).
   - **Tầng sự kiện cổng thanh toán (Payment Gateway Event):** Thẩm quyền thuộc PayOS.
   - **Tầng đối soát & ghi có ví (Settlement & Wallet Credit):** Thẩm quyền độc quyền của Bot Core (`BOT_CORE`). Tuyệt đối không đánh đồng `PAYMENT_CONFIRMED == WALLET_CREDITED`.
3. **Trung thực về Ví tiền (Wallet Truth):** Cấm tạo số dư 0 ảo (`FAKE_ZERO_WALLET_BALANCE = 0`). Khi Core Bridge chưa kết nối hoặc ví chưa truy xuất được, trường `balance_xu` phải giữ `None` (hiển thị `Chưa khả dụng`), tuyệt đối không hiển thị `0 Xu`.
4. **Trung thực về Doanh thu (Revenue Truth):** Doanh thu trên Web chỉ tính các yêu cầu nạp tiền duyệt thủ công trên Web (`scope = WEB_ONLY_MANUAL_TOPUPS`), độ bao phủ là một phần (`coverage = PARTIAL`), dán nhãn chuẩn xác `Known Web Revenue`, tuyệt đối cấm dán nhãn `Total Revenue`. Cấm suy diễn dữ liệu tài chính không khả dụng thành 0 (`UNKNOWN_REVENUE_AS_ZERO = False`, `UNAVAILABLE_FINANCE_VALUE_AS_ZERO = False`).
5. **Khóa chặt Control Plane:** Tuyệt đối không có nút duyệt nạp tiền, cộng tiền thủ công, trừ tiền, quyết toán hay hoàn tiền trên giao diện Web (`MANUAL_CREDIT_ACTIONS = 0`, `MANUAL_DEBIT_ACTIONS = 0`, `SETTLEMENT_ACTIONS = 0`, `REFUND_ACTIONS = 0`, `PAYOS_ACTIONS = 0`, `WALLET_ACTIONS = 0`). Mọi endpoint ghi nguy hiểm đều khóa chặt fail-closed với mã `WEBAPP_ADMIN_WRITES_DISABLED`.

---

## 3. Ma Trận Thẩm Quyền Tài Chính (Finance Authority Matrix)
- `CUSTOMER_AUTHORITY`: `WEB_SQLITE` (Nguồn: `web_accounts`, `web_account_topup_codes`)
- `WALLET_AUTHORITY`: `BOT_CORE` (Nguồn: Bot Core `/internal/v1/admin/wallet` hoặc Core Bridge)
- `PAYMENT_GATEWAY_AUTHORITY`: `PAYOS` (Nguồn: PayOS Gateway)
- `PAYMENT_SETTLEMENT_AUTHORITY`: `BOT_CORE` (Nguồn: Bot Core Ledger)
- `TOPUP_REQUEST_AUTHORITY`: `WEB_SQLITE` (Nguồn: `web_manual_topup_requests`)
- `JOB_AUTHORITY`: `BOT_CORE` (Nguồn: Bot Core Jobs)
- `REVENUE_AUTHORITY`: `BOT_CORE` (Nguồn: Bot Core Ledger / Revenue Engine)
- `WEB_ROLE`: `READ_THROUGH_OR_PROJECTION`
- `WEB_DIRECT_BOT_DB_WRITE`: **False**
- `CUSTOMER_FINANCE_AND_FINANCE_PAGE_SHARE_AUTHORITY`: **True**
- `JOB_BILLING_AND_FINANCE_PAGE_SHARE_SEMANTICS`: **True**

---

## 4. Phân Biệt Trạng Thái & Bảng Tra (State Taxonomy & Invariants)
### Topup Request States (Thẩm quyền Web SQLite):
- `pending_admin_review` -> `PENDING` (Yêu cầu nạp chờ duyệt, chưa quyết toán ví)
- `approved` -> `CONFIRMED` (Yêu cầu nạp đã xác nhận)
- `rejected` -> `REJECTED` (Yêu cầu nạp bị từ chối)

### Invariants Bất Biến:
- `REQUEST_STATE != PAYMENT_GATEWAY_EVENT != WALLET_SETTLEMENT`
- `PAYMENT_CONFIRMED_NOT_EQUAL_WALLET_CREDITED = True`
- `FAKE_ZERO_WALLET_BALANCE = 0`
- `UNKNOWN_REVENUE_AS_ZERO = False`
- `UNAVAILABLE_FINANCE_VALUE_AS_ZERO = False`
- `MANUAL_CREDIT_ACTIONS = 0`
- `MANUAL_DEBIT_ACTIONS = 0`
- `SETTLEMENT_ACTIONS = 0`
- `REFUND_ACTIONS = 0`
- `PAYOS_ACTIONS = 0`
- `WALLET_ACTIONS = 0`

---

## 5. Danh Mục Endpoints & Giao Diện
- **HTML Shells:**
  - `GET /admin/finance`: Tổng quan tài chính & giao dịch
  - `GET /admin/finance/topups`: Danh sách yêu cầu nạp tiền
  - `GET /admin/finance/payments`: Danh sách thanh toán PayOS projection
- **JSON Read APIs:**
  - `GET /api/v1/admin/finance/summary` & `GET /api/v1/admin/finance`
  - `GET /api/v1/admin/finance/topups` & `GET /api/v1/admin/topups` (hỗ trợ pagination `limit`, `offset`, filters `status`, `account_id`)
  - `GET /api/v1/admin/finance/payments`
- **Fail-Closed Write Endpoints (An Toàn Tuyệt Đối):**
  - `POST /api/v1/admin/finance/credit` -> `WEBAPP_ADMIN_WRITES_DISABLED`
  - `POST /api/v1/admin/finance/debit` -> `WEBAPP_ADMIN_WRITES_DISABLED`
  - `POST /api/v1/admin/finance/settle` -> `WEBAPP_ADMIN_WRITES_DISABLED`
  - `POST /api/v1/admin/finance/refund` -> `WEBAPP_ADMIN_WRITES_DISABLED`

---

## 6. Xác Định & Đóng Lỗi Đầu Tiên (First-Red Resolution)
- **First-Red:** Bộ fixture kiểm thử admin gặp lỗi 403 Forbidden do tài khoản `acc-admin-01` được gieo mầm trong SQLite ban đầu chưa khai báo `canonical_user_id='7126457028'`, khiến bộ phận bảo mật `copyfast_auth._require_current_canonical_admin` từ chối trước khi gọi Core Bridge.
- **Giải pháp:**
  - Bổ sung `canonical_user_id='7126457028'` vào cấu trúc gieo mầm tài khoản admin, kích hoạt cơ chế xác thực nội bộ của `CoreBridgeClient`.
  - Toàn bộ 16 bài kiểm thử của SPEC-06 ngay lập tức vượt qua xuất sắc.

---

## 7. Kết Quả Kiểm Thử & Chốt Chặn An Toàn
- **Kiểm thử chuyên biệt SPEC-06:** 16/16 tests PASSED (`tests/test_p0_spec06_finance_read_model_truth.py`).
- **Toàn bộ bộ kiểm thử P0 Specs:** 90/90 tests PASSED (SPEC-00: 7, SPEC-01: 8, SPEC-02: 12, SPEC-03: 14, SPEC-03B: 8, SPEC-04: 8, SPEC-05: 10, SPEC-05B: 7, SPEC-06: 16).
- **Lỗi mới phát sinh:** **0** (`NEW_FAILURES=0`).
- **Chốt chặn an toàn:**
  - `PROVIDER_CALLS`: 0
  - `WALLET_MUTATIONS`: 0
  - `PAYMENT_MUTATIONS`: 0
  - `SETTLEMENT_MUTATIONS`: 0
  - `BOT_DB_MUTATIONS`: 0
  - `WEB_WALLET_MUTATIONS`: 0
  - `ENV_MUTATIONS`: 0
  - `PRODUCTION_DB_SCHEMA_MUTATIONS`: 0

---

## 8. Kết Luận Nghiệm Thu
- **SPEC06_PASS:** **YES**
- **BLOCKERS:** **NONE**
