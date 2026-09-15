# SPEC-00: MA TRẬN HỢP ĐỒNG XÁC THỰC NGHIỆP VỤ CANONICAL

- **Program:** `P0.WEB.ERP.PRODUCTION_COMPLETION`
- **Task:** `P0.WEB.ERP.SPEC00.TRUTH_CONTRACT.NORMALIZATION`
- **Target Host:** `tg.toanaas.vn` (`/opt/toanaas/webapp`)
- **Base / Runtime SHA:** `03325cf577de4fd090abea9088c8980a6a028e29`
- **Tiêu chuẩn kiểm toán:** `owner-governed-codex` & `locked-focus-engineering`

---

## 1. BẢNG KHÓA SỰ THẬT BÁO CÁO (NORMALIZED REPORTING TRUTH)

> [!IMPORTANT]
> Sửa chữa và bình thường hóa trạng thái báo cáo toàn hệ thống theo đúng hiện trạng thực tế:

```ini
FULL_WEB_APP_LIVE=NO
MONITORING_LIVE=PARTIAL
FINANCE_LIVE=PARTIAL
ADMIN_WRITE_LIVE=PARTIAL
DATA_TRUTH_STATUS=PARTIAL
ZERO_IS_NOT_UNKNOWN=TRUE
HTTP200_IS_NOT_BUSINESS_SUCCESS=TRUE
WALLET_DIRECT_MUTATIONS_PERMITTED=FALSE
TOTAL_FUNCTIONS=54
WORKING_FUNCTIONS=29
PARTIAL_FUNCTIONS=14
EMPTY_VALID_FUNCTIONS=2
PLACEHOLDER_FUNCTIONS=4
READ_ONLY_FUNCTIONS=5
HARDCODED_METRIC_PAGES=3
```

**Lý do bình thường hóa (Justification):**
1. Có 14 chức năng đang ở trạng thái `PARTIAL` (chưa hoàn thiện telemetry, thiếu live trigger, hoặc chỉ ghi cục bộ).
2. Có 4 chức năng đang là `PLACEHOLDER` (chưa có nghiệp vụ thật phía sau).
3. Có 3 trang chứa số liệu hardcoded (`/admin/finance/planning`, `/admin/growth`, `/admin/trends`).
4. Phân hệ tài chính chưa tổng hợp giao dịch từ Telegram Bot Core.
5. Telemetry của phân hệ Giám sát chưa được kích hoạt đầy đủ do cờ Autopilot đang tắt.
6. Chưa có bộ kiểm thử tự động trình duyệt thật E2E trên các thiết bị di động.

---

## 2. MA TRẬN BẰNG CHỨNG HỢP ĐỒNG 54 CHỨC NĂNG (CONTRACT ACCEPTANCE MATRIX)

| Mã FN | Phân hệ (Domain) | Tên chức năng | Route | Endpoint API | Implemented | Unit Test | Integ Test | Browser Proven | Real Data | Write Proven | Prod Proven | Trạng thái |
|---|---|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **FN-01** | `AUTH_ACCOUNT` | User Login | `/login` | `POST /api/v1/auth/login` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **WORKING** |
| **FN-02** | `AUTH_ACCOUNT` | User Registration | `/register` | `POST /api/v1/auth/register` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **WORKING** |
| **FN-03** | `AUTH_ACCOUNT` | Session Revocation / Logout | `/logout` | `POST /api/v1/auth/logout` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **WORKING** |
| **FN-04** | `AUTH_ACCOUNT` | User Profile Management | `/profile` | `GET/PUT /api/v1/auth/me` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **WORKING** |
| **FN-05** | `AUTH_ACCOUNT` | Password Change | `/security` | `POST /api/v1/auth/change-password` | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | **PARTIAL** |
| **FN-06** | `CUSTOMER_CRM_SUPPORT` | Customer Directory View | `/admin/customers` | `GET /api/v1/admin/customers` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | **WORKING** |
| **FN-07** | `CUSTOMER_CRM_SUPPORT` | Customer Account Status Control | `/admin/customers` | `POST /api/v1/admin/customers/status` | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | **PARTIAL** |
| **FN-08** | `CUSTOMER_CRM_SUPPORT` | CRM Lead Submission | `/partner-readiness` | `POST /api/v1/crm/leads` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **WORKING** |
| **FN-09** | `CUSTOMER_CRM_SUPPORT` | CRM Lead Management | `/admin/crm/leads` | `GET /api/v1/crm/leads` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | **WORKING** |
| **FN-10** | `CUSTOMER_CRM_SUPPORT` | Customer Support Case Creation | `/support` | `POST /api/v1/support/cases` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **WORKING** |
| **FN-11** | `CUSTOMER_CRM_SUPPORT` | Support Case Review & Triage | `/admin/support` | `GET/PUT /api/v1/support/cases` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **WORKING** |
| **FN-12** | `OPERATIONS_JOBS` | Operations Work Queue | `/admin/operations` | `GET /api/v1/operations/jobs` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | **WORKING** |
| **FN-13** | `OPERATIONS_JOBS` | Failed Jobs Inspection | `/admin/jobs/failed` | `GET /api/v1/operations/jobs/failed` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | **EMPTY_VALID** |
| **FN-14** | `OPERATIONS_JOBS` | Failed Job Retry Action | `/admin/jobs/failed` | `POST /api/v1/operations/jobs/retry` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | **PARTIAL** |
| **FN-15** | `OPERATIONS_JOBS` | Content Handoffs Publishing Queue | `/admin/content-handoffs` | `GET /api/v1/operations/handoffs` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | **WORKING** |
| **FN-16** | `OPERATIONS_JOBS` | Content Publishing Approval | `/admin/approvals` | `POST /api/v1/operations/approvals` | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | **PARTIAL** |
| **FN-17** | `OPERATIONS_JOBS` | Job Recovery Runbook Guide | `/admin/job-recovery-guide` | `GET /api/v1/operations/guide` | ✅ | ✅ | ❌ | ✅ | ❌ | — | ❌ | **READ_ONLY** |
| **FN-18** | `RELIABILITY_MONITORING` | Host & Uvicorn Runtime Health | `/health` | `GET /api/v1/core/status` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | **WORKING** |
| **FN-19** | `RELIABILITY_MONITORING` | Worker Pool Status & Monitoring | `/admin/workers` | `GET /api/v1/operations/workers` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | **WORKING** |
| **FN-20** | `RELIABILITY_MONITORING` | Operations Reliability Summary | `/admin/reliability` | `GET /api/v1/operations/admin/reliability/summary` | ✅ | ✅ | ✅ | ✅ | ❌ | — | ❌ | **PARTIAL** |
| **FN-21** | `RELIABILITY_MONITORING` | Feature Freezes & Maintenance Lock | `/admin/freezes` | `GET/POST /api/v1/operations/freezes` | ✅ | ✅ | ❌ | ✅ | ✅ | — | ❌ | **PARTIAL** |
| **FN-22** | `RELIABILITY_MONITORING` | Provider Health & Upstream Probe | `/admin/providers` | `GET /api/v1/operations/providers` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | **WORKING** |
| **FN-23** | `FINANCE_PAYMENT` | Customer Wallet Balance Read Model | `/wallet` | `GET /api/v1/payments/wallet` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | **WORKING** |
| **FN-24** | `FINANCE_PAYMENT` | Manual Topup VietQR Draft Creation | `/wallet` | `POST /api/v1/payments/topup` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **WORKING** |
| **FN-25** | `FINANCE_PAYMENT` | PayOS Online Checkout Initiation | `/wallet` | `POST /api/v1/payments/payos/checkout` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **WORKING** |
| **FN-26** | `FINANCE_PAYMENT` | Admin Manual Topups Review Queue | `/admin/topups` | `GET /api/v1/admin/topups` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | **WORKING** |
| **FN-27** | `FINANCE_PAYMENT` | Admin Reject Invalid Topup Draft | `/admin/topups` | `POST /api/v1/admin/topups/reject` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **WORKING** |
| **FN-28** | `FINANCE_PAYMENT` | Revenue & Settlement Summary | `/admin/revenue` | `GET /api/v1/admin/revenue` | ✅ | ✅ | ✅ | ✅ | ❌ | — | ❌ | **PARTIAL** |
| **FN-29** | `FINANCE_PAYMENT` | Refund History & Registry | `/admin/refunds` | `GET /api/v1/admin/refunds` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | **EMPTY_VALID** |
| **FN-30** | `FINANCE_PAYMENT` | Provider Cost Tracking | `/admin/provider-cost` | `GET /api/v1/admin/provider-cost` | ✅ | ✅ | ❌ | ✅ | ❌ | — | ❌ | **PARTIAL** |
| **FN-31** | `FINANCE_PAYMENT` | Financial Planning & Projections | `/admin/finance/planning` | `GET /api/v1/finance/planning` | ❌ | ❌ | ❌ | ✅ | ❌ | — | ❌ | **PLACEHOLDER** |
| **FN-32** | `PRODUCT_COMMERCE` | Public Pricing Catalog | `/pricing` | `GET /api/v1/packages/pricing` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | **WORKING** |
| **FN-33** | `PRODUCT_COMMERCE` | Package Tier Management | `/admin/packages` | `GET /api/v1/packages` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | **WORKING** |
| **FN-34** | `PRODUCT_COMMERCE` | Discount & Promo Code Engine | `/admin/promos` | `GET /api/v1/packages/promos` | ❌ | ❌ | ❌ | ✅ | ❌ | — | ❌ | **PLACEHOLDER** |
| **FN-35** | `PRODUCT_COMMERCE` | Feature Catalog Explorer | `/features` | `GET /api/v1/features/catalog` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | **READ_ONLY** |
| **FN-36** | `CONTENT_GROWTH` | Campaign Management | `/admin/campaigns` | `GET /api/v1/campaigns` | ✅ | ✅ | ❌ | ✅ | ✅ | — | ❌ | **PARTIAL** |
| **FN-37** | `CONTENT_GROWTH` | Publishing Editorial Calendar | `/admin/calendar` | `GET /api/v1/calendar` | ✅ | ✅ | ❌ | ✅ | ✅ | — | ❌ | **PARTIAL** |
| **FN-38** | `CONTENT_GROWTH` | Publishing Channels Configuration | `/admin/publishing` | `GET /api/v1/publishing/channels` | ✅ | ✅ | ❌ | ✅ | ✅ | — | ❌ | **PARTIAL** |
| **FN-39** | `CONTENT_GROWTH` | Performance Analytics Dashboard | `/admin/analytics` | `GET /api/v1/analytics/summary` | ✅ | ✅ | ❌ | ✅ | ❌ | — | ❌ | **PARTIAL** |
| **FN-40** | `CONTENT_GROWTH` | Growth & Acquisition Strategy | `/admin/growth` | `GET /api/v1/growth/summary` | ❌ | ❌ | ❌ | ✅ | ❌ | — | ❌ | **PLACEHOLDER** |
| **FN-41** | `CONTENT_GROWTH` | Ad Postback Integration Readiness | `/admin/growth/postback-readiness` | `GET /api/v1/growth/postback` | ❌ | ❌ | ❌ | ✅ | ❌ | — | ❌ | **PLACEHOLDER** |
| **FN-42** | `CONTENT_GROWTH` | Trend Discovery Engine | `/admin/trends` | `GET /api/v1/trends` | ❌ | ❌ | ❌ | ✅ | ❌ | — | ❌ | **PARTIAL** |
| **FN-43** | `ADMINISTRATION_SECURITY_AUDIT` | Admin Master Dashboard | `/admin` | `GET /api/v1/admin/dashboard` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | **WORKING** |
| **FN-44** | `ADMINISTRATION_SECURITY_AUDIT` | User Accounts Administration | `/admin/users` | `GET /api/v1/admin/users` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | **WORKING** |
| **FN-45** | `ADMINISTRATION_SECURITY_AUDIT` | RBAC Role & Permission Inspection | `/admin/access` | `GET /api/v1/admin/access` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | **WORKING** |
| **FN-46** | `ADMINISTRATION_SECURITY_AUDIT` | Audit Log Event Explorer | `/admin/audit` | `GET /api/v1/audit/events` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | **WORKING** |
| **FN-47** | `ADMINISTRATION_SECURITY_AUDIT` | Security Configuration & Session Invalidation | `/admin/security` | `GET /api/v1/admin/security` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | **WORKING** |
| **FN-48** | `ADMINISTRATION_SECURITY_AUDIT` | System Stewardship & Safety Controls | `/admin/system-stewardship` | `GET /api/v1/admin/stewardship` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | **WORKING** |
| **FN-49** | `ADMINISTRATION_SECURITY_AUDIT` | Database Backup Management | `/admin/backups` | `GET /api/v1/admin/backups` | ✅ | ✅ | ❌ | ✅ | ✅ | — | ❌ | **PARTIAL** |
| **FN-50** | `ADMINISTRATION_SECURITY_AUDIT` | Administrative Reporting Export | `/admin/reports` | `GET /api/v1/admin/reports` | ✅ | ✅ | ❌ | ✅ | ✅ | — | ❌ | **PARTIAL** |
| **FN-51** | `GOVERNANCE_DOCUMENTS_LEGAL` | Governance Policies Archive | `/admin/governance` | `GET /api/v1/governance/policies` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | **WORKING** |
| **FN-52** | `GOVERNANCE_DOCUMENTS_LEGAL` | Internal Operational Documents | `/admin/internal-documents` | `GET /api/v1/governance/docs` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | **WORKING** |
| **FN-53** | `GOVERNANCE_DOCUMENTS_LEGAL` | Tax & Financial Compliance Readiness | `/admin/finance/tax-readiness` | `GET /api/v1/governance/tax-readiness` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | **WORKING** |
| **FN-54** | `GOVERNANCE_DOCUMENTS_LEGAL` | Legal Terms & Privacy Public Archive | `/legal` | `GET /api/v1/governance/legal` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | **READ_ONLY** |

---

## 3. NGUYÊN TẮC NGHIỆM THU CHUYỂN TRẠNG THÁI CHO CÁC SPEC TIẾP THEO

1. **Không công nhận WORKING chỉ vì HTTP 200:** Một endpoint trả về HTTP 200 nhưng chứa dữ liệu trống rỗng, dữ liệu giả mạo, hoặc thông báo cờ tắt chỉ được tính là `PARTIAL` hoặc `EMPTY_VALID`.
2. **Chỉ công nhận WORKING khi hội tụ đủ 4 bằng chứng:**
   - `IMPLEMENTED = True`
   - `UNIT_TESTED = True`
   - `REAL_DATA_PROVEN = True` (Dữ liệu từ bảng SQLite thật hoặc tiến trình OS thật)
   - Nếu là hành vi ghi (Write Action): Bắt buộc có `WRITE_PROVEN = True` với xác thực CSRF, Idempotency và Audit log.
3. **Khóa an toàn ví tiền tuyệt đối:** Không chức năng nào được phép cấp cờ `WRITE_PROVEN` nếu hành động đó tự ý sửa đổi số dư ví người dùng ngoài thẩm quyền của Telegram Bot Core.
