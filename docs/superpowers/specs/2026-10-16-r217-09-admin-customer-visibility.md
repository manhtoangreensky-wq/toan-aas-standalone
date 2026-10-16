# R217-09 — Admin shell, customer visibility và permission presentation

**Status:** `SOURCE_GREEN_RUNTIME_OPEN`
**Wave:** W5
**Surface:** Admin login/shell, operations, billing/top-up, jobs/assets, customer directory,
support, audit, reliability, ERP data views và customer action reports.

## File có thể sửa khi mở

- admin/customer presentation modules trong `static/portal/`;
- admin templates/styles;
- contract tests `tests/test_admin_*` và browser fixture tests.

## Cấm sửa

Không tự cấp quyền, không sửa RBAC/ABAC backend, không mutate wallet/PayOS, không đổi
ledger/customer data, không gọi Bot/Core bridge từ UI task.

## Contract giao diện

- Navigation theo nhóm dọc, một heading/CTA mỗi panel, không dùng hàng ngang dày đặc.
- Owner thấy toàn bộ; role khác thấy menu/action theo permission snapshot, nút bị chặn có
  lý do và hướng dẫn xin quyền.
- Customer action phải liên kết request/job/asset/report/audit; Admin không hiển thị card
  thành công nếu không có record thật.
- Top-up manual presentation có amount/method/reference/status/approve/reject/reason,
  nhưng mutation ledger chỉ là deferred.
- Bảng/chart có card fallback trên mobile, legend/heading/empty/loading/error, locale sạch.

## Acceptance

- Admin thao tác được bằng keyboard, 44px target, contrast AA, light/dark navy/teal,
  375/390/768/1440 không clipping.
- Mỗi action trong Admin có bằng chứng report hoặc status `NOT_CONNECTED`/`GUARDED` rõ.
- Không có “UI PASS” thay cho server permission/bridge PASS.

## Verify

```powershell
python -m pytest tests/test_admin_*.py -q
```

Chỉ kết luận PASS theo output thật; nếu bundled Python/fixture không chạy, ghi BLOCKED và
không tự sửa dependency production.

## Source closeout 2026-10-16

- Admin module tabs now render as a vertical grid with `min-height:44px`, normal wrapping,
  and no horizontal overflow in the scoped Admin layer.
- Generic Admin fallback labels now use the VI/EN/ZH catalogue for role check, read-only,
  authority boundary, Web audit metadata and provider readiness copy.
- Admin/module/locale/motion focused Node evidence: `29/29`.
- Manual top-up draft/confirm and idempotency presentation exists in source, but actual
  approval/ledger effect still requires an isolated canonical-admin fixture and remains
  deferred; no wallet mutation was performed.

## Source closeout bổ sung 2026-10-16

- Provider table fixed chrome now uses balanced `adminProviderUi.*` locale keys for columns,
  configuration/availability/health/routing badges, empty state and read-only detail action.
  Provider IDs, capability payloads, route and provider operations remain untouched.
- Manual top-up approval/rejection fixed chrome now uses balanced
  `adminManualTopup.approval.*` keys for approve/reject headings, note placeholders and
  confirmation buttons. Existing draft/confirmation actions remain unchanged; no ledger or
  wallet mutation was opened.
- New Node regressions: Admin Provider + Manual Top-up `4/4`; full Node suite `506/506`.
  Python admin fixture and browser runtime remain open.

## Source closeout bổ sung 2026-10-16 — SOURCE-ADMIN-03

- `/admin/publishing` domain center now uses balanced `adminDomainUi.publishing.*` copy for
  title/description, Campaign Center, Content Calendar, Approval Queue, Analytics and its
  three authority boundaries. The four routes remain filtered by the signed server manifest.
- Admin domain/provider/top-up focused regression passes `6/6`; full Node suite passes
  `508/508`. No RBAC/ABAC, provider operation, wallet or PayOS mutation was changed.

### Source closeout bổ sung — SOURCE-ADMIN-04

- `/admin/growth` và `/admin/trends` dùng catalogue `adminDomainUi.growth.*` và
  `adminDomainUi.trends.*` cho title, description, stream và boundary; server route allowlist
  và read-only authority không đổi.
- Admin domain/provider/top-up focused regression đạt `7/7`; full Node suite đạt `509/509`.

### Source closeout bổ sung — SOURCE-ADMIN-05 (2026-10-17)

- Customer 360 và safety modal đã chuyển fixed chrome còn sót sang catalogue
  `adminCustomer360.*` cân bằng VI/EN/ZH: an toàn tài khoản, trạng thái đăng nhập/phiên,
  nút khóa/mở khóa, ví/tài chính, tác vụ/tệp bàn giao, hỗ trợ, nhật ký, cảnh báo, nhãn lý do,
  nút đóng và hủy.
- Dữ liệu động (customer ID, role/status, case/audit payload, số tiền và số dư),
  `admin-customer-ban-open`, `admin-customer-unban-open`, `admin-customer-safety-close`,
  `admin-customer-ban-submit`, `admin-customer-unban-submit`, route và safety boundary giữ
  nguyên. Không mở wallet/ledger mutation hoặc Core Bridge write.
- Regression mới `tests/admin-customer-360-locale-purity.test.mjs` đạt `3/3`; full Node suite
  đạt `512/512`; syntax `static/portal/portal.js` và `static/portal/portal-i18n.js`,
  `git diff --check` đều đạt; comparator giữ nguyên 771 action, 630 route và 439 field
  occurrence, không có mục thêm/xóa.
- Python contract `tests/test_p0_webapp_v2_05_admin_customer_360.py` chưa chạy được do môi
  trường thiếu `py`/`pytest`; browser/runtime canonical-admin fixture và ledger effect vẫn
  `OPEN`/`DEFERRED`, không được suy diễn thành PASS.

### Source closeout bổ sung — SOURCE-ADMIN-06 (2026-10-17)

- Admin shell `pageStatusBadge` không còn hardcode fixed chrome trộn VI/EN. Bốn nhãn
  `canonical_bridge`, `web_planning` và `runtime_generator` (ready/guarded) dùng
  `adminHome.boundary.*` cân bằng VI/EN/ZH.
- Giữ nguyên boundary/status semantics, route/action, capability và dữ liệu server; không
  mở write hoặc thay đổi permission enforcement.
- Regression `tests/admin-shell-boundary-locale.test.mjs` đạt `5/5`; syntax Portal `2/2`
  đạt. Full Node, browser/runtime và Python contract vẫn là các cổng riêng.
