# R217-09 — Admin shell, customer visibility và permission presentation

**Status:** `TODO`
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
