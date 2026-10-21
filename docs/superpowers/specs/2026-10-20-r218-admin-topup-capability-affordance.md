# R218 AD-04 — Nạp thủ công: affordance theo capability

## Mục tiêu

Khóa lỗi trình bày trong hàng đợi nạp thủ công: danh sách desktop và thẻ mobile
không được hiển thị nút tạo quyết định duyệt/cộng Xu khi phiên hiện tại chưa có
capability máy chủ `admin-manual-topup-write`.

## Phạm vi được phép

- `static/portal/portal.js`: chỉ renderer của bảng/thẻ nạp thủ công.
- `tests/admin-manual-topup-capability-presentation.test.mjs`: source contract.
- Không sửa API, capability authority, wallet, ledger, PayOS, CSRF, idempotency,
  database, provider hoặc runtime approval.

## Hợp đồng

1. `writeEnabled` phải được lấy từ `context.capabilities["admin-manual-topup-write"] === true`.
2. Với `pending_admin_review` và `writeEnabled=false`, bảng và thẻ chỉ hiển thị
   nhãn read-only có lý do quyền hạn; tuyệt đối không có
   `data-portal-action="admin-manual-topup-draft"`.
3. Nút xem chi tiết vẫn hoạt động để người có quyền đọc kiểm tra record.
4. Với `writeEnabled=true`, affordance draft approve giữ nguyên; form inspector
   vẫn là ranh giới xác nhận cuối và không mở thêm mutation phía client.
5. `expected_xu`/`approved_xu` chỉ được hiển thị khi máy chủ cấp; thiếu dữ liệu thì
   hiển thị `—`, tuyệt đối không suy `amount_vnd / 100` ở trình duyệt.
6. State draft cũ cũng không được dựng modal xác nhận khi capability ghi đã mất.
7. Nhãn read-only phải dùng catalogue `adminManualTopup` hiện hành, không hardcode
   thêm chuỗi tiếng Anh hoặc thuật ngữ kỹ thuật vào giao diện.

## Bằng chứng nghiệm thu

- `node --test tests/admin-manual-topup-capability-presentation.test.mjs` — 3/3.
- `node --check static/portal/portal.js` — PASS.
- `node --test` — toàn bộ suite xanh.
- `git diff --check` — PASS.

Đây là khóa UI/UX chỉ đọc. Không suy diễn rằng capability thật, quyền RBAC,
approval, cộng Xu hoặc LIVE đã được chứng minh.
