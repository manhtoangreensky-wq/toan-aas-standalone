# Báo cáo Triển khai & Nghiệm thu SPEC-05: Operations / Jobs Truth

**Chương trình:** `P0.WEB.ERP.PRODUCTION_COMPLETION`  
**Spec:** `P0.WEB.ERP.SPEC05.OPERATIONS.JOBS.TRUTH`  
**Quy chuẩn áp dụng:** `owner-governed-codex`, `locked-focus-engineering`, `single-agent-anti-overengineering`  
**Baseline SHA:** `060c9a40a76729382b89b1c3386da53d7b646364`  
**Target Host:** `tg.toanaas.vn`  
**Trạng thái nghiệm thu:** `PASS (100% Tiêu chí Đạt, Đóng SPEC-05 Toàn diện)`  

---

## 1. Tuyên bố Mở đầu Bắt buộc
Đang đọc và áp dụng skill owner-governed-codex cho task này.

---

## 2. Mục tiêu Vận hành (Owner Purpose)
Xây dựng phân hệ Vận hành / Tác vụ (Operations / Jobs) tinh gọn, trung thực, an toàn tuyệt đối cho ERP:
1. **Sự thật tác vụ:** Quản trị viên nắm bắt chính xác công việc nào tồn tại, đang chạy, đang xếp hàng, thất bại hay đã xong.
2. **Quyền sở hữu:** Liên kết rõ ràng tác vụ với khách hàng (`customer_id`, `canonical_user_id`) và dự án (`project_id`, `service_context`).
3. **Cần chú ý:** Chỉ kích hoạt cờ `attention_required` dựa trên sự thật cụ thể (`FAILED`, `BLOCKED`, lỗi delivery/output, đối soát thủ công, hoàn tiền chờ giải quyết).
4. **Độ tươi mới & Thẩm quyền:** Minh bạch nguồn dữ liệu gốc (`JOB_AUTHORITY = BOT_CORE`), vai trò Web là `READ_THROUGH_OR_PROJECTION`.
5. **Trung thực về số liệu:** Tuân thủ `UNKNOWN != 0`, `UNAVAILABLE != HEALTHY`, `EMPTY != UNKNOWN`. Khi nguồn bridge chưa sẵn sàng, hiển thị `status = UNAVAILABLE` và `counts = null`, tuyệt đối cấm tạo số lượng 0 giả mạo (`FAKE_ZERO_JOB_COUNT = 0`).

---

## 3. Hợp đồng Thẩm quyền & Bất Biến An Toàn (Authority Contract)
- `JOB_AUTHORITY`: `BOT_CORE`
- `WEB_ROLE`: `READ_THROUGH_OR_PROJECTION`
- `WEB_DIRECT_BOT_DB_WRITE`: **False**
- `JOB_MUTATION_AVAILABLE`: **False**
- `RETRY_ACTIONS`: **0**
- `CANCEL_ACTIONS`: **0**
- `REQUEUE_ACTIONS`: **0**
- `FORCE_COMPLETE_ACTIONS`: **0**
- `PROVIDER_ACTIONS`: **0**
- `FAKE_ZERO_JOB_COUNT`: **0**
- `ZERO WRITE ON JOBS`: Toàn bộ các thao tác ghi (retry, refund) trên web đều đóng chốt fail-closed với mã `WEBAPP_ADMIN_WRITES_DISABLED`.

---

## 4. Bảng Tra Phân Loại Trạng Thái Nghiệp Vụ (State Taxonomy)
Hệ thống chuẩn hóa toàn bộ các trạng thái thô từ Bot Core và Web Local về 6 trạng thái nghiệp vụ chuẩn:
- **QUEUED:** `queued`, `pending`, `submitted`, `wait`, `waiting`.
- **RUNNING:** `processing`, `running`, `in_progress`, `rendering`, `generating`.
- **SUCCEEDED:** `completed`, `succeeded`, `success`, `done`, `delivered`.
- **FAILED:** `failed`, `failed_no_charge`, `error`, `timeout`.
- **BLOCKED:** `cancelled`, `canceled`, `refunded`, `guarded`, `awaiting_confirm`, `draft`, `blocked`, `hold`.
- **UNKNOWN:** Giá trị rỗng, `None` hoặc chưa xác định.

---

## 5. Xác Định & Đóng Lỗi Đầu Tiên (First-Red Resolution)
- **First-Red:** Trước đây route `/admin/jobs` khi Core Bridge chưa cấu hình (`CORE_BRIDGE_NOT_CONFIGURED`) chỉ trả về envelope rỗng không cấu trúc; thiếu bảng phân loại 6 trạng thái nghiệp vụ; thiếu các API chuẩn `/api/v1/operations/jobs`, `/api/v1/operations/jobs/failed`, `/api/v1/operations/jobs/{id}`; và phân hệ Customer CRM (SPEC-04) chưa kết nối cờ chú ý từ tác vụ.
- **Giải pháp:**
  - Xây dựng `copyfast_operations_jobs_policy.py`: pure policy module định nghĩa thẩm quyền, bảng map trạng thái chuẩn, bộ đánh giá chú ý dựa trên sự thật, hàm tổng hợp bản ghi tác vụ và phong bì tổng quan trung thực không số 0 ảo (`counts = None` khi `UNAVAILABLE`).
  - Nâng cấp `copyfast_api.py`: chuẩn hóa endpoint `/admin/jobs` và `/admin/jobs/{job_id}`, bổ sung các route `/api/v1/operations/jobs`, `/api/v1/operations/jobs/failed`, `/api/v1/operations/jobs/{job_id}`, khóa chặt retry/refund fail-closed.
  - Tích hợp vào `copyfast_customer_crm_policy.py`: cho phép đưa dữ liệu tác vụ vào CRM context và tự động cảnh báo trong `action_required` khi có tác vụ cần chú ý.

---

## 6. Kết Quả Kiểm Thử & Chốt Chặn An Toàn
- **Kiểm thử chuyên biệt SPEC-05:** 10/10 tests PASSED (`tests/test_p0_spec05_operations_jobs_truth.py`).
- **Toàn bộ bộ kiểm thử P0 Specs:** 67/67 tests PASSED (SPEC-00: 7, SPEC-01: 8, SPEC-02: 12, SPEC-03: 14, SPEC-03B: 8, SPEC-04: 8, SPEC-05: 10).
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
- **SPEC05_PASS:** **YES**
- **BLOCKERS:** **NONE**
