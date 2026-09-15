# Báo cáo Nghiệm thu SPEC-03: Monitoring & Reliability Truth

**Chương trình:** `P0.WEB.ERP.PRODUCTION_COMPLETION`  
**Spec:** `P0.WEB.ERP.SPEC03.MONITORING.RELIABILITY_TRUTH`  
**Quy chuẩn áp dụng:** `owner-governed-codex`, `locked-focus-engineering`, `single-agent-anti-overengineering`  
**Baseline SHA:** `e53f8fdaf9ff0a17e3390d9d757b70c03f1b3266`  
**Branch:** `feat/p0-spec03-monitoring-reliability-truth`  
**Target Host:** `tg.toanaas.vn`  
**Trạng thái nghiệm thu:** `PASS`  

---

## 1. Tuyên bố Mở đầu Bắt buộc
Đang đọc và áp dụng skill owner-governed-codex cho task này.

---

## 2. Mục tiêu & Chân lý Giám sát (Owner Purpose & Core Truths)
Chuyển hóa toàn bộ bề mặt Monitoring / Reliability thành một không gian điều hành ERP trung thực, cô đọng và đáng tin cậy:
1. **HTTP 200 != HEALTHY**: Mã phản hồi HTTP 200 từ phong bì sạch (Clean Envelope) chỉ chứng minh tầng vận chuyển mạng thành công; không bao giờ được suy diễn thành trạng thái vận hành khỏe mạnh (HEALTHY).
2. **DISABLED AUTOPILOT => UNAVAILABLE**: Khi Autopilot chưa được cấu hình hoặc tắt theo chính sách an toàn của Owner (`TOANAAS_OPS_AUTOPILOT_ENABLED` không set), telemetry phải báo cáo trung thực là `UNAVAILABLE` với blocker code chuẩn xác `OPS_RELIABILITY_AUTOPILOT_DISABLED`. Tuyệt đối không giả mạo thành `HEALTHY`, không báo lỗi `ERROR`, không quy về `0 sự cố = hoàn hảo`.
3. **ZERO != ERROR**: Số lượng 0 worker hoạt động hay 0 tác vụ chờ là một phép đo thực nghiệm (empirical measurement) về một cụm worker đang rảnh rỗi (idle), không phải là lỗi kết nối API.
4. **CONFIGURED != HEALTHY**: Việc một nhà cung cấp bên ngoài (Provider) có cấu hình / API key không đồng nghĩa với việc provider đó đang khỏe mạnh nếu chưa qua bài kiểm thử sống (live probe). Do chốt chặn an toàn bất biến `PROVIDER_CALLS=0`, provider không được gọi probe tính phí khi giám sát thụ động.
5. **REQUIRED VS OPTIONAL DEGRADATION**:
   - Khi nguồn bắt buộc (`RUNTIME_OS`, `WEB_SQLITE`) gặp sự cố -> Trạng thái hệ thống chuyển thành `DEGRADED` hoặc `ERROR`.
   - Khi nguồn tùy chọn (`AUTOPILOT_RELIABILITY`, `CORE_BRIDGE_WORKER`) ở trạng thái `UNAVAILABLE` -> Hệ thống giữ nguyên trạng thái `HEALTHY` (với ghi chú telemetry không khả dụng), không tạo ra báo động đỏ giả toàn cục.
6. **READ-ONLY GUARANTEE**: Tuyệt đối không có nút tự động khắc phục (auto-repair), kích hoạt deploy, khởi động lại dịch vụ hoặc can thiệp ví tiền / thanh toán từ giao diện tóm tắt Reliability.

---

## 3. Ma trận Nguồn Giám sát (Monitoring Source Matrix - 8 Nguồn)

| Source ID | Tên Miền (Domain) | Thẩm Quyền (Authority) | Đường Dẫn Đọc | Chu Kỳ Cập Nhật | Tùy Chọn? | Trạng Thái Hiện Tại |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| `RUNTIME_OS` | `SYSTEM_RUNTIME` | `RUNTIME_OS_PROCESS` | `/health` | Realtime (10s) | Không | **HEALTHY** |
| `SYSTEMD_SERVICE` | `SYSTEM_RUNTIME` | `RUNTIME_OS_PROCESS` | `systemctl status` | Realtime (On-demand) | Không | **HEALTHY** |
| `WORKER_REGISTRY` | `WORKER_STATUS` | `RUNTIME_OS_PROCESS` | In-process background tasks | Realtime (Continuous) | Không | **HEALTHY** |
| `BOT_CORE_RUNTIME`| `SYSTEM_RUNTIME` | `RUNTIME_OS_PROCESS` | `toanaas-bot.service` | Realtime (On-demand) | Không | **HEALTHY** |
| `AUTOPILOT_RELIABILITY` | `RELIABILITY_TELEMETRY` | `BOT_CORE_AUTOPILOT` | `/api/v1/operations/admin/reliability/summary` | On-demand | Có | **UNAVAILABLE** |
| `FEATURE_CONFIG` | `FEATURE_STATUS` | `WEB_LOCAL_REGISTRY` | `copyfast_api._flags()` | Realtime (Continuous) | Không | **HEALTHY** |
| `FREEZE_STATE` | `FREEZE_STATE` | `BOT_CORE_POLICY` | `copyfast_api._flags()` | Realtime (Continuous) | Không | **HEALTHY** |
| `PROVIDER_HEALTH`| `PROVIDER_HEALTH` | `EXTERNAL_PROVIDERS` | Unconfigured (`PROVIDER_CALLS=0`) | None | Có | **UNAVAILABLE** |

---

## 4. Hợp đồng Trạng thái Ngữ nghĩa (Semantic Status Contract)
Hệ thống chuẩn hóa 6 giá trị trạng thái vận hành duy nhất:
- `HEALTHY`: Nguồn thẩm quyền phản hồi và đáp ứng 100% tiêu chí sức khỏe.
- `DEGRADED`: Nguồn thẩm quyền phản hồi nhưng một hoặc nhiều tiêu chí sức khỏe thất bại (ví dụ: phát sinh sự cố mở).
- `UNAVAILABLE`: Nguồn dữ liệu chủ động tắt hoặc chưa được cấu hình (ví dụ: Autopilot telemetry).
- `UNKNOWN`: Không thể đưa ra kết luận xác đáng từ dữ liệu hiện có.
- `ERROR`: Nguồn bắt buộc đáng lẽ phải có nhưng truy xuất hoặc xử lý thất bại (exception/crash).
- `STALE`: Dữ liệu quá thời hạn hợp đồng độ tươi (freshness contract).

Logic đánh giá được đóng gói thuần túy tại `copyfast_reliability_policy.py`:
- `evaluate_semantic_status(...)`
- `evaluate_multi_source_status(...)`

---

## 5. Kết quả Kiểm thử Thực nghiệm (14/14 Test Cases Passed)
Được kiểm chứng tự động qua bộ test: `tests/test_p0_spec03_monitoring_reliability_truth.py`

| Case # | Mô tả Yêu cầu Nghiệm thu | Kết quả | Ghi chú Kỹ thuật |
| :---: | :--- | :---: | :--- |
| **01** | `HTTP 200 != HEALTHY` | **PASS** | Kiểm chứng tiêu chí sức khỏe thất bại trên HTTP 200 cho ra `DEGRADED`/`UNAVAILABLE` |
| **02** | `disabled Autopilot => UNAVAILABLE` | **PASS** | Autopilot tắt trả về `OPS_RELIABILITY_AUTOPILOT_DISABLED`, status `guarded`, semantic `UNAVAILABLE` |
| **03** | `enabled + healthy fixture => HEALTHY` | **PASS** | Autopilot bật + secret chuẩn + 0 sự cố => `HEALTHY` |
| **04** | `enabled + degraded fixture => DEGRADED` | **PASS** | Autopilot bật + có sự cố mở/vượt ngưỡng => `DEGRADED` |
| **05** | `source exception => ERROR` | **PASS** | Nguồn thẩm quyền phát sinh exception đánh giá thành `ERROR` |
| **06** | `source absent => UNKNOWN or UNAVAILABLE` | **PASS** | Chưa cấu hình => `UNAVAILABLE`; không xác định tiêu chuẩn => `UNKNOWN` |
| **07** | `zero workers != worker API failure` | **PASS** | 0 active workers là trạng thái idle hợp lệ, không đánh đồng thành `ERROR` |
| **08** | `provider configured != provider healthy` | **PASS** | Provider có API key nhưng không có live probe (`PROVIDER_CALLS=0`) => `UNAVAILABLE` |
| **09** | `freeze active renders active truthfully` | **PASS** | Khi freeze kích hoạt, trạng thái vận hành hiển thị trung thực là `DEGRADED`/bảo trì |
| **10** | `optional unavailable does not fake global failure` | **PASS** | Telemetry `UNAVAILABLE` không kéo sập trạng thái chung của hệ thống runtime khỏe |
| **11** | `required runtime error affects global status` | **PASS** | Lỗi tại `RUNTIME_OS` kéo trạng thái chung về `ERROR`/`DEGRADED` chính xác |
| **12** | `dashboard health semantics stay compatible` | **PASS** | `/internal/v1/admin/summary` giữ nguyên multi-source health contract tương thích |
| **13** | `no banned technical copy on business surface` | **PASS** | Không lộ 'Core Bridge', 'clean envelope', 'SQLite authority' trên HTML nghiệp vụ |
| **14** | `no mutation controls on Reliability summary` | **PASS** | Endpoint summary trả về `read_only`, không chứa bất kỳ mutation action nào |

---

## 6. Chốt chặn An toàn Vận hành (Safety Gates Verification)
- `PRODUCTION_DB_MUTATIONS`: 0 (Không thay đổi schema hoặc dữ liệu DB sản xuất)
- `WALLET_MUTATIONS`: 0 (Không can thiệp ví Xu)
- `PAYMENT_MUTATIONS`: 0 (Không can thiệp PayOS / giao dịch thanh toán)
- `ENV_MUTATIONS`: 0 (Không tự ý thêm/sửa biến môi trường)
- `SECRET_MUTATIONS`: 0 (Không thay đổi secrets)
- `PROVIDER_CALLS`: 0 (Không gọi API bên ngoài tốn phí)
- `AUTOPILOT_ACTIVATED`: KHÔNG (Autopilot duy trì tắt an toàn theo lệnh Owner)
