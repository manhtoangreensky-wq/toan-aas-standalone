# R217-00 — Evidence ledger và contract baseline

**Status:** `CLOSED_WITH_EVIDENCE` (documentation baseline)
**Wave:** W0
**Mục tiêu:** tạo một nguồn trạng thái duy nhất trước khi sửa UI/UX.

## File được phép

- `docs/superpowers/plans/2026-10-16-webapp-uiux-product-parity-master-plan-r217.md`
- `reports/audit/WEBAPP-UIUX-PARITY-MASTER-CHECKLIST-20261016.md`
- `.agents/state/WEBAPP-UIUX-PARITY-PLAN-20261016.yaml`

## Không được đụng

Toàn bộ mã nguồn runtime, test đang có, Bot/Core, route/engine, provider, wallet/PayOS,
production data, secrets, VPS, merge và deploy.

## Nội dung bắt buộc

1. Ghi remote/base SHA, PR hiện tại, source test evidence và live evidence thật.
2. Ghi từng defect có ID, URL/viewport, triệu chứng, trạng thái và bước đóng.
3. Ghi protected contracts: route, action, field, capability, CSRF, idempotency, revision,
   dynamic server data.
4. Ghi `PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`, `PRODUCTION_DATA_MUTATIONS=0`.

## Nghiệm thu

- Có plan, checklist và state YAML cùng chỉ tới một baseline SHA.
- Mọi `LIVE_PASS=NO` khi chưa có DOM/screenshot/console/network evidence.
- Lỗi mới được thêm vào wave đúng thứ tự, không xóa lịch sử lỗi đã mở.

## Verify

```powershell
git rev-parse HEAD
git status --short
rg -n "LIVE_PASS|PROVIDER_CALLS|WALLET_MUTATIONS|protected_contracts" reports/audit/WEBAPP-UIUX-PARITY-MASTER-CHECKLIST-20261016.md .agents/state/WEBAPP-UIUX-PARITY-PLAN-20261016.yaml
```

**Kết quả mong đợi:** SHA là `f59eacf...`, chỉ các file tài liệu mới thay đổi trong
worktree kế hoạch, các safety flag là 0 và mọi runtime gate mở được ghi rõ.
