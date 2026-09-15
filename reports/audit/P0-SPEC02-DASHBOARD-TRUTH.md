# Báo cáo Nghiệm thu SPEC-02: Dashboard Real Operational Truth

**Chương trình:** `P0.WEB.ERP.PRODUCTION_COMPLETION`  
**Spec:** `P0.WEB.ERP.SPEC02.DASHBOARD.REAL_OPERATIONAL_TRUTH`  
**Quy chuẩn áp dụng:** `owner-governed-codex`, `locked-focus-engineering`, `single-agent-anti-overengineering`  
**Baseline SHA:** `03325cf577de4fd090abea9088c8980a6a028e29`  
**Runtime SHA:** `03325cf577de4fd090abea9088c8980a6a028e29`  
**Trạng thái nghiệm thu:** `PASS`  

---

## 1. Tuyên bố Mở đầu Bắt buộc
Đang đọc và áp dụng skill owner-governed-codex cho task này.

---

## 2. Mục tiêu & Nguyên tắc Cốt lõi của SPEC-02
SPEC-02 biến `/admin` từ giao diện hiển thị số liệu ước đoán/kết hợp trực tiếp từ DB Bot thành Trung tâm Điều hành Vận hành Trung thực (Honest ERP Operational Command Center):
1. **DASHBOARD_FAKE_METRICS = 0**: Loại bỏ toàn bộ số liệu giả định, heuristic `max(users_count, row[0])`, hoặc query cross-database trực tiếp vào `toandaas_system.db`.
2. **DASHBOARD_DEMO_FALLBACKS = 0**: Không dùng số liệu demo tĩnh khi không tìm thấy nguồn dữ liệu.
3. **DASHBOARD_UNKNOWN_AS_ZERO = 0**: Dữ liệu chưa xác định hoặc không khả dụng phải hiển thị rõ `Chưa xác định` hoặc `Không khả dụng`, tuyệt đối không ép thành `0`. Giá trị `0` là một phép đo thực tế (empirical measurement), không phải là dữ liệu bị thiếu.
4. **DASHBOARD_API_ERROR_AS_EMPTY = 0**: Khi API bridge hoặc DB có sự cố, giao diện hiển thị thẻ thông báo trung thực `Chưa có số liệu vận hành` kèm nút làm mới an toàn, không hiển thị trang trắng.
5. **REVENUE_SCOPE = WEB_ONLY**: Doanh thu trên Web App chỉ phản ánh phạm vi Web nội bộ, tuyệt đối cấm tuyên bố `TOTAL_SYSTEM_REVENUE`.
6. **WALLET_MUTATIONS = 0**: Giao diện Dashboard không có bất kỳ form/action nạp/rút/cộng trừ Xu trực tiếp.
7. **DANGEROUS_WRITE_ACTIONS = 0**: Không đặt các nút retry job hàng loạt, ban user hoặc xóa tài khoản trực tiếp trên dashboard root.
8. **MULTI-SOURCE HEALTH MODEL**: Tách biệt trung thực 3 nguồn trạng thái:
   - `system_runtime`: HEALTHY (Process FastAPI)
   - `workers`: HEALTHY (Internal background worker)
   - `reliability_telemetry`: UNAVAILABLE (Bot Autopilot telemetry chưa kết nối, không giả mạo thành HEALTHY).
9. **PROTECTED WORK**: Bảo vệ nguyên vẹn PR #437 Admin IA consolidation (7 nhóm, 10 primary links, 38 secondary tabs), portal scroll ownership (`portal-workspace`), semantic Light/Dark tokens và không vi phạm từ vựng kỹ thuật tiếng Việt bị cấm.

---

## 3. Danh mục KPI Vận hành Thực tế (Operational KPI Inventory)

| KPI Key | Nhãn Tiếng Việt | Ghi chú Tiếng Việt | Nguồn Thẩm quyền (Authority) | Công thức Tính | Ý nghĩa khi = 0 | Trạng thái khi lỗi |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `action_required` | Cần xử lý ngay | Tổng các yêu cầu cần xử lý | `WEB_SQLITE` | `pending_topups + open_support + pending_approvals` | 0 yêu cầu cần xử lý (hệ thống trơn tru) | Không khả dụng |
| `total_customers` | Tài khoản người dùng | Dữ liệu tài khoản đã kiểm tra | `WEB_SQLITE.web_accounts` | `SELECT count(*) FROM web_accounts` | 0 tài khoản đăng ký | Không khả dụng |
| `pending_topups` | Nạp tiền chờ duyệt | Chờ đối soát thanh toán | `WEB_SQLITE.web_manual_topup_requests` | `SELECT count(*) FROM web_manual_topup_requests WHERE status = 'pending_admin_review'` | 0 yêu cầu nạp chờ duyệt | Không khả dụng |
| `open_support` | Phiếu hỗ trợ mở | Yêu cầu hỗ trợ chưa đóng | `WEB_SQLITE.web_support_cases` | `SELECT count(*) FROM web_support_cases WHERE state IN ('new', 'reviewing', 'waiting_user', 'waiting_provider', 'refund_pending')` | 0 phiếu hỗ trợ mở | Không khả dụng |
| `failed_jobs` | Tác vụ gặp sự cố | Các tác vụ cần kiểm tra | `WEB_SQLITE.web_ops_followups` | `SELECT count(*) FROM web_ops_followups WHERE state = 'open'` | 0 tác vụ lỗi | Không khả dụng |

*Ghi chú tương thích ngược (Backward Compatibility):*  
Các keys cũ `users`, `payments`, `worker_jobs`, `engine_jobs` vẫn được giữ trong API bridge projection để không gây lỗi cho các client cũ, nhưng giao diện ưu tiên render nhóm KPI ERP trung thực mới khi có dữ liệu.

---

## 4. Mô hình Sức khỏe Hệ thống Đa Nguồn (Multi-Source Health Model)

```
[Dashboard Status Overview]
 ├── system_runtime: HEALTHY (Web FastAPI Server Process Uptime)
 ├── workers: HEALTHY (Web In-process Background Tasks)
 └── reliability_telemetry: UNAVAILABLE (Bot Autopilot Telemetry Stream Disconnected)
```

Không gộp (collapse) cả 3 nguồn vào một huy hiệu xanh duy nhất khi luồng telemetry thực sự chưa được tích hợp.

---

## 5. Bằng chứng Kiểm thử Thực nghiệm (Empirical Verification Evidence)

### 5.1. Syntax Compilation
```bash
python -m py_compile copyfast_db.py copyfast_bridge.py copyfast_api.py tests/test_p0_spec02_admin_dashboard_truth.py
# Exit code: 0 (No syntax errors)
```

### 5.2. SPEC-02 Dedicated Test Suite (`tests/test_p0_spec02_admin_dashboard_truth.py`)
```bash
python -m pytest tests/test_p0_spec02_admin_dashboard_truth.py -s -o cache_dir="C:/Users/toann/AppData/Local/Temp/.pytest_cache"
```
**Kết quả:**
- `test_dashboard_kpi_sources_are_authoritative`: PASSED
- `test_no_fake_metrics_or_direct_bot_sqlite_queries`: PASSED
- `test_zero_remains_zero`: PASSED
- `test_unknown_does_not_become_zero`: PASSED
- `test_api_error_renders_honest_empty_guard`: PASSED
- `test_revenue_display_scope_is_web_only`: PASSED
- `test_wallet_is_read_only_on_dashboard`: PASSED
- `test_dashboard_has_no_direct_dangerous_write_actions`: PASSED
- `test_system_health_multi_source_truth`: PASSED
- `test_navigation_consolidation_protected`: PASSED
- `test_light_dark_semantic_classes_remain_intact`: PASSED
- `test_no_banned_technical_copy_on_dashboard`: PASSED
**Tổng:** 12/12 PASSED (100%).

### 5.3. Full Regression Test Suite
```bash
python -m pytest tests/test_p0_spec00_truth_contract.py tests/test_p0_spec01_data_authority_contract.py tests/test_p0_spec02_admin_dashboard_truth.py tests/test_admin_detail_dashboard_002_contracts.py tests/test_admin_erp_professional_vi_003_contracts.py tests/test_copyfast_bridge.py -s -o cache_dir="C:/Users/toann/AppData/Local/Temp/.pytest_cache"
```
**Kết quả:**
- `tests/test_p0_spec00_truth_contract.py`: 7 passed
- `tests/test_p0_spec01_data_authority_contract.py`: 8 passed
- `tests/test_p0_spec02_admin_dashboard_truth.py`: 12 passed
- `tests/test_admin_detail_dashboard_002_contracts.py`: 5 passed
- `tests/test_admin_erp_professional_vi_003_contracts.py`: 14 passed
- `tests/test_copyfast_bridge.py`: 30 passed
**Tổng:** 76/76 PASSED (100%).

---

## 6. Kết luận & Chuyển giao
SPEC-02 đã hoàn tất đầy đủ mọi yêu cầu kỹ thuật và ràng buộc bất biến của Owner:
- Zero DB schema mutations.
- Zero wallet direct mutations.
- Zero fake metrics & demo fallbacks.
- Tự động chuẩn bị chuyển sang SPEC-03 (`DATA_EXPLORER.QUERY_RUNTIME`).
