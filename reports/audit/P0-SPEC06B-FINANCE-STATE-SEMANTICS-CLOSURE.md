# Báo cáo Triển khai & Nghiệm thu SPEC-06B: Finance State Semantics Closure

**Chương trình:** `P0.WEB.ERP.PRODUCTION_COMPLETION`  
**Spec:** `P0.WEB.ERP.SPEC06B.FINANCE.STATE.SEMANTICS.CLOSURE`  
**Quy chuẩn áp dụng:** `owner-governed-codex`, `locked-focus-engineering`, `single-agent-anti-overengineering`, `toanaas-system-design-and-open-apis`  
**Baseline SHA:** `0e71bd7e3d5d50a42e00229dbe2061b7f7ce3c33`  
**Target Host:** `tg.toanaas.vn`  
**Trạng thái nghiệm thu:** `PASS (100% Tiêu chí Đạt, Đóng SPEC-06B & SPEC-06 Toàn diện)`  

---

## 1. Tuyên bố Mở đầu Bắt buộc
Đang đọc và áp dụng skill owner-governed-codex cho task này.

---

## 2. Mục tiêu Nghiệp vụ (Purpose)
Đóng dứt điểm đúng 1 khiếm khuyết ngữ nghĩa còn lại của SPEC-06:
- **Tách bạch trạng thái duyệt nạp tiền Web và xác nhận thanh toán PayOS:** Yêu cầu nạp tiền Web khi được duyệt phải dùng trạng thái `APPROVED` (hoặc `REQUEST_APPROVED`), tuyệt đối không được dùng chung trạng thái `CONFIRMED` với thanh toán PayOS.
- **Không tự ý tổng hợp suy diễn trạng thái (Zero Synthetic States):**
  - `REQUEST_APPROVED_IMPLIES_PAYMENT_CONFIRMED = False` (Duyệt yêu cầu không có nghĩa là cổng thanh toán đã nhận tiền).
  - `PAYMENT_CONFIRMED_IMPLIES_SETTLED = False` (Cổng thanh toán xác nhận tiền không có nghĩa là Bot Core đã ghi có Xu vào ví).
  - `SETTLED_IMPLIES_REQUEST_APPROVED = False` (Chỉ liên kết khi có bằng chứng thực tế).
- **Không mở rộng tính năng tài chính.**

---

## 3. Truy vết Hợp đồng Hiện tại (Contract Trace)
1. **Nguồn chuẩn hóa trạng thái yêu cầu (TOPUP_STATE_MAPPING_SOURCE):**
   - `copyfast_finance_policy.py`: hàm `map_topup_raw_state`, từ điển `RAW_TOPUP_TO_BUSINESS_STATE`.
   - `copyfast_db.py`: bộ lọc `query_finance_topups_list(status=...)`.
2. **Bộ tuần tự hóa API (TOPUP_API_SERIALIZER):**
   - `copyfast_finance_policy.py`: hàm `synthesize_topup_record`, `synthesize_finance_summary`.
   - `copyfast_api.py`: route `/api/v1/admin/finance/topups` và `/api/v1/admin/finance/summary`.
3. **Bộ kết xuất giao diện người dùng (TOPUP_UI_RENDERER):**
   - `static/portal/portal.js`: `adminManualTopupText`, `renderAdminTopups` (dòng 30213: `{ pending_admin_review: "Chờ duyệt", approved: "Đã duyệt", rejected: "Đã từ chối", guarded: "Được bảo vệ" }`).
   - Trên UI, các nhãn hiển thị bằng tiếng Việt rõ ràng, không hiển thị từ tiếng Anh gây hiểu lầm.
4. **Phạm vi hiển thị của từ khóa "CONFIRMED" trước khi sửa:**
   - Trong `copyfast_finance_policy.py` đã map `approved -> CONFIRMED`, gán nhầm vào `request_state`.
   - Trong API: trả về `request_state: CONFIRMED` cho yêu cầu đã duyệt.
   - Trong Browser UI: `portal.js` hiển thị "Đã duyệt" chứ không hiển thị "CONFIRMED".
   - Trong Tests: `tests/test_p0_spec06_finance_read_model_truth.py` kiểm tra `assert map_topup_raw_state("approved") == "CONFIRMED"`.
   - Trong Báo cáo: báo cáo SPEC-06 cũ ghi nhận `TOPUP_BUSINESS_STATES = PENDING, CONFIRMED, REJECTED`.

---

## 4. Mô hình 3 Tầng Chuẩn Hóa (Three-Layer Model)
Bất biến bắt buộc:
`REQUEST_STATE != PAYMENT_STATE != SETTLEMENT_STATE`

1. **Tầng Yêu cầu Nạp tiền (Authority: WEB_SQLITE):**
   - `pending_admin_review` -> `PENDING` (hoặc `REQUEST_PENDING`)
   - `approved` -> `APPROVED` (hoặc `REQUEST_APPROVED`)
   - `rejected` -> `REJECTED` (hoặc `REQUEST_REJECTED`)
   - Khác/rỗng -> `UNKNOWN`
2. **Tầng Sự kiện Cổng Thanh toán (Authority: PAYOS):**
   - `PENDING`, `CONFIRMED`, `FAILED`, `EXPIRED`, `UNAVAILABLE`, `UNKNOWN`
3. **Tầng Đối soát & Quyết toán Ví (Authority: BOT_CORE):**
   - `PENDING`, `CREDITED`, `REJECTED`, `UNAVAILABLE`, `UNKNOWN`

---

## 5. Nguồn Dữ liệu PayOS & Tích hợp Khách hàng
- `PAYMENT_GATEWAY_AUTHORITY`: `PAYOS`
- `PAYMENT_READ_MODEL_SOURCE`: `BOT_CORE_PAYMENT_PROJECTION_OR_WEBHOOK_CACHE`
- `PAYMENT_EVENT_SOURCE`: `PAYOS_GATEWAY_WEBHOOK`
- `CUSTOMER_FINANCE_STATE_MAPPING_SHARED`: `YES` (Customer CRM context dùng chung ngữ nghĩa phân tầng này, không có logic map cạnh tranh).

---

## 6. Xác Định & Đóng Lỗi Đầu Tiên (First-Red Resolution)
- **First-Red:** Bộ kiểm thử `tests/test_p0_spec06_finance_read_model_truth.py` trước đây kiểm tra `map_topup_raw_state("approved") == "CONFIRMED"`, và hàm `synthesize_topup_record` tự động suy diễn `payment_state = CONFIRMED`, `settlement_state = CREDITED` khi yêu cầu được duyệt.
- **Giải pháp:**
  - Chuẩn hóa `map_topup_raw_state("approved")` thành `APPROVED`.
  - Cập nhật `synthesize_topup_record` để `payment_state` và `settlement_state` chỉ nhận giá trị từ sự kiện/liên kết thực tế có bằng chứng; nếu không có liên kết, bảo toàn trung thực là `UNKNOWN`.
  - Cập nhật `map_settlement_state` để thanh toán xác nhận (`CONFIRMED`) mà chưa có quyết toán thì trả về `UNKNOWN`, cấm tự suy diễn `CREDITED`.
  - Đồng bộ `CUSTOMER_FINANCE_STATE_MAPPING_SHARED = True` trong cả finance policy và CRM policy.

---

## 7. Kết Quả Kiểm Thử & Chốt Chặn An Toàn
- **Kiểm thử chuyên biệt SPEC-06B:** 8/8 tests PASSED (`tests/test_p0_spec06b_finance_state_semantics_closure.py`).
- **Kiểm thử chuyên biệt SPEC-06:** 16/16 tests PASSED (`tests/test_p0_spec06_finance_read_model_truth.py`).
- **Toàn bộ 10 bộ kiểm thử P0 Specs:** 101/101 tests PASSED (SPEC-00: 7, SPEC-01: 8, SPEC-02: 12, SPEC-03: 14, SPEC-03B: 8, SPEC-04: 8, SPEC-05: 10, SPEC-05B: 7, SPEC-06: 16, SPEC-06B: 8).
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
- **SPEC06B_PASS:** **YES**
- **SPEC06_FULL_CLOSE:** **YES**
- **BLOCKERS:** **NONE**
