# Báo cáo Kiểm toán & Thiết kế Hợp đồng Ghi Tài chính SPEC-07: Financial Writes Authority & Idempotency Audit

**Chương trình:** `P0.WEB.ERP.PRODUCTION_COMPLETION`  
**Spec:** `P0.WEB.ERP.SPEC07.FINANCIAL.WRITES.AUTHORITY.IDEMPOTENCY.AUDIT`  
**Chế độ:** `OWNER-GOVERNED` | `AUDIT-FIRST` | `READ-ONLY` | `FIRST-RED-ONLY`  
**Quy chuẩn áp dụng:** `owner-governed-codex`, `locked-focus-engineering`, `single-agent-anti-overengineering`, `toanaas-system-design-and-open-apis`  
**Baseline SHA:** `a7d837a8b25720687859d1d7e6637d77529d0743`  
**Target Host:** `tg.toanaas.vn`  
**Trạng thái kiểm toán:** `PASS (100% Tiêu chí Đạt, Kiểm toán Khóa chặt Biên giới Ghi)`  

---

## 1. Tuyên bố Mở đầu Bắt buộc
Đang đọc và áp dụng skill owner-governed-codex cho task này.

---

## 2. Mục tiêu Kiểm toán (Owner Purpose)
Kiểm toán chuyên sâu và xác lập hợp đồng bất biến cho mặt bằng điều khiển ghi tài chính (financial-write control plane) TRƯỚC KHI triển khai bất kỳ tính năng ghi nào trong tương lai.
Xác định chính xác thẩm quyền (authority), tính bất biến khi gọi lại (idempotency), phân quyền bảo mật (authorization), và hợp đồng phục hồi lỗi (recovery contracts) cho 4 hành vi ghi nhạy cảm:
1. **Manual Credit** (Cộng Xu thủ công)
2. **Manual Debit** (Trừ Xu thủ công)
3. **Payment Settlement** (Quyết toán nạp tiền / ghi có)
4. **Refund** (Hoàn tiền dịch vụ)

> [!CAUTION]
> **TUYỆT ĐỐI KHÔNG THỰC THI**: Task này ở chế độ READ-ONLY & AUDIT-FIRST. Toàn bộ các chốt chặn an toàn tài chính được giữ nguyên: `NO-FINANCIAL-MUTATION`, `NO-WALLET-MUTATION`, `NO-PAYMENT-MUTATION`, `NO-SETTLEMENT`, `NO-REFUND`, `NO-PROVIDER-CALL`, `NO-CROSS-DB-WRITE`, `NO-SCHEMA-MUTATION`, `NO-ENV-MUTATION`, `NO-DEPLOY`.

---

## 3. Ma Trận Thẩm Quyền Ghi Tài Chính (Authority & Write Ownership Matrix)

### Thẩm quyền Chuẩn tắc (Canonical Authorities):
- `WALLET_AUTHORITY` = `BOT_CORE`
- `PAYMENT_GATEWAY_AUTHORITY` = `PAYOS`
- `PAYMENT_SETTLEMENT_AUTHORITY` = `BOT_CORE`
- `TOPUP_REQUEST_AUTHORITY` = `WEB_SQLITE`
- `REVENUE_AUTHORITY` = `BOT_CORE`
- `WEB_ROLE` = `READ_THROUGH_OR_PROJECTION`
- `WEB_DIRECT_WALLET_MUTATION` = `False`
- `WEB_DIRECT_BOT_DB_WRITE` = `False`

### Đặc tả Chi tiết 7 Hành vi Ghi (Write Actions Contract):

| Hành vi (ACTION) | Thẩm quyền (AUTHORITY) | Chủ thể Ghi (WRITE_OWNER) | Định danh Yêu cầu (REQUIRED_IDENTITY) | Tiền điều kiện (REQUIRED_PRESTATE) | Nguồn Khóa Idempotency (IDEMPOTENCY_KEY_SOURCE) | Biên lai Kiểm toán (AUDIT_RECEIPT_SOURCE) |
|---|---|---|---|---|---|---|
| **MANUAL_CREDIT** | `BOT_CORE` | Bot Core Ledger (`/internal/v1/admin/wallet/credit`) | `CANONICAL_ADMIN` (2 tầng: Session ký + live role) | Account liên kết `canonical_user_id`, ví tồn tại, amount > 0, lý do >= 5 ký tự | Header `Idempotency-Key` scoped: `admin:{id}:credit:{user}:{key}` | Bot Core `tx_id` + `web_audit_events` |
| **MANUAL_DEBIT** | `BOT_CORE` | Bot Core Ledger (`/internal/v1/admin/wallet/debit`) | `CANONICAL_ADMIN` (2 tầng) | Account liên kết `canonical_user_id`, `balance_xu >= debit_amount` (cấm số dư âm) | Header `Idempotency-Key` scoped: `admin:{id}:debit:{user}:{key}` | Bot Core `tx_id` + `web_audit_events` |
| **PAYMENT_SETTLEMENT** | `BOT_CORE` | Bot Core Settlement Engine | `PAYOS_WEBHOOK_SIGNATURE` hoặc `CANONICAL_ADMIN` | PayOS `gateway_state == CONFIRMED`, `settlement_state == PENDING`, chưa quyết toán | PayOS `orderCode` / `paymentLinkId` (`payos_processed`) | Bot Core `payos_processed` + Ledger tx + `web_audit_events` |
| **REFUND** | `BOT_CORE` | Bot Core Ledger / Job Engine | `CANONICAL_ADMIN` (2 tầng) | Job ở trạng thái `FAILED`/`CANCELLED`, đã trừ tiền trước đó, `refund_status != COMPLETED` | Scoped: `admin:{id}:refund:{job_id}:{key}` | Bot Core refund receipt + `web_audit_events` |
| **TOPUP_REQUEST_APPROVE** | `WEB_SQLITE` | Web App Admin (`web_manual_topup_requests`) | `CANONICAL_ADMIN` / `LOCAL_ADMIN` | Yêu cầu ở `status == pending_admin_review`, đã kiểm tra biên lai ngân hàng | Mã yêu cầu `MANUAL-{id}` + receipt hash | `web_audit_events` (`action='admin.manual_topup.approve'`) |
| **TOPUP_REQUEST_REJECT** | `WEB_SQLITE` | Web App Admin (`web_manual_topup_requests`) | `LOCAL_ADMIN` / `CANONICAL_ADMIN` | Yêu cầu ở `status == pending_admin_review`, lý do 3–300 ký tự | Hash key idempotency + hash receipt xác nhận 2 pha | `web_audit_events` (`action='admin.manual_topup.reject'`) |
| **PAYOS_CHECKOUT_CREATE** | `PAYOS` | PayOS Merchant Gateway & `payos_orders` | `AUTHENTICATED_USER` + CSRF | Account liên kết `canonical_user_id`, gói thuộc catalog hợp lệ | SHA256(`owner_id` + `client_key`) lưu tại `payos_orders` | `payos_orders.order_code` + marker transient |

---

## 4. Kiểm kê Mặt bằng Ghi Hiện hành (Current Write Surface Inventory)

| Endpoint / Hàm | Phương thức | Tệp mã nguồn & Dòng | Bộ phận Bảo vệ (Guard) | Trạng thái Hiện tại | Mã lỗi Trả về |
|---|---|---|---|---|---|
| `/api/v1/admin/finance/credit` | POST | `copyfast_api.py:5929-5942` | `require_canonical_admin` | **LOCKED_FAIL_CLOSED** | `WEBAPP_ADMIN_WRITES_DISABLED` |
| `/api/v1/admin/finance/debit` | POST | `copyfast_api.py:5930-5942` | `require_canonical_admin` | **LOCKED_FAIL_CLOSED** | `WEBAPP_ADMIN_WRITES_DISABLED` |
| `/api/v1/admin/finance/settle` | POST | `copyfast_api.py:5931-5942` | `require_canonical_admin` | **LOCKED_FAIL_CLOSED** | `WEBAPP_ADMIN_WRITES_DISABLED` |
| `/api/v1/admin/finance/refund` | POST | `copyfast_api.py:5932-5942` | `require_canonical_admin` | **LOCKED_FAIL_CLOSED** | `WEBAPP_ADMIN_WRITES_DISABLED` |
| `/api/v1/admin/jobs/{job_id}/refund` | POST | `copyfast_api.py:6017-6037` | `require_canonical_admin_csrf` + flag | **GUARDED_CANONICAL_BRIDGE** | `WEBAPP_ADMIN_WRITES_DISABLED` (mặc định) |
| `/api/v1/admin/payments/manual/{id}/draft` | POST | `copyfast_api.py:4967-5010` | `require_admin_csrf` + flag | **GUARDED_LOCAL_REJECT_RECEIPT** | `WEBAPP_ADMIN_WRITES_DISABLED` |
| `/api/v1/admin/payments/manual/{id}/confirm` | POST | `copyfast_api.py:5013-5050` | `require_admin_csrf` + flag | **GUARDED_LOCAL_REJECT_CONFIRM** | `WEBAPP_ADMIN_WRITES_DISABLED` |
| `/api/v1/payments/manual` | POST | `copyfast_api.py:5055-5120` | `require_csrf` | **ACTIVE_CUSTOMER_REQUEST_INTAKE** | Khởi tạo đơn nạp ở Web SQLite (0 Xu) |
| `/api/v1/payments/create` | POST | `copyfast_api.py:5219-5350` | `require_csrf` | **ACTIVE_PAYOS_CHECKOUT_DISPATCH** | Điều hướng thanh toán PayOS (0 Xu) |

---

## 5. Hợp đồng Chống Trùng lặp & Phục hồi Lỗi (Idempotency & Recovery Contracts)

1. **Phân vùng Scope Khóa Idempotency:**
   - Định dạng chuẩn tắc: `{domain}:{actor_id}:{action}:{target_id}`.
   - Ngăn chặn triệt để xung đột khóa chéo giữa các admin hoặc giữa các đối tượng khác nhau.
2. **Quy tắc Xử lý Gọi Lặp (Duplicate Request Policy):**
   - **Cùng Key + Cùng Payload:** Hệ thống trả về kết quả đã lưu trong bộ nhớ (`idempotent_replay = True`), không thực thi lại thao tác ghi phía sau.
   - **Cùng Key + Khác Payload:** Hệ thống trả về lỗi `409 Conflict` (`IDEMPOTENCY_CONFLICT`), cấm ghi đè hoặc thực thi thao tác khác dưới cùng 1 mã khóa.
   - **Cùng Key + Thao tác Đang Xử lý:** Hệ thống trả về `409 Conflict` / `425 Too Early` (`IDEMPOTENCY_IN_PROGRESS`), chặn hiện tượng race-condition.
3. **Cơ chế Xác nhận Hai Pha (Two-Phase Confirmation Receipt):**
   - Áp dụng cho các thao tác can thiệp quản trị: Tạo biên lai mã hóa có thời hạn (TTL = 300 giây).
   - Thao tác xác nhận bắt buộc nộp kèm biên lai hợp lệ; chỉ được tiêu thụ 1 lần duy nhất (`consumed_at IS NULL`).
4. **Hợp đồng Phục hồi khi Gặp Lỗi Mạng / Sập Kết nối (Recovery Contract):**
   - Khi gọi bridge sang Bot Core bị timeout: Web App giải phóng cờ tạm (`transient marker`) và giữ nguyên trạng thái chờ.
   - Client thử lại với cùng `Idempotency-Key`: Bot Core đối soát bảng `payos_processed` hoặc transaction log để trả về kết quả chính xác, tuyệt đối không trừ/cộng tiền 2 lần.
   - Tuyệt đối cấm Web App tự ý "ghi có lạc quan" (optimistic wallet credit) khi chưa nhận được xác nhận từ Bot Core.

---

## 6. Kết Quả Kiểm Thử & Nghiệm Thu (Empirical Verification)
- **Bộ kiểm thử SPEC-07:** 8/8 tests PASSED (`tests/test_p0_spec07_financial_writes_authority_idempotency_audit.py`).
- **Toàn bộ 11 bộ kiểm thử P0 Specs:** 109/109 tests PASSED (SPEC-00 qua SPEC-07).
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

## 7. Kết Luận
- **SPEC07_AUDIT_PASS:** **YES**
- **FINANCIAL_WRITES_CONTROL_PLANE_FROZEN:** **YES**
- **BLOCKERS:** **NONE**
