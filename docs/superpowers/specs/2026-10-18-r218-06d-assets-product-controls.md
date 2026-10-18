# R218-06D — Asset Vault product controls

Ngày 2026-10-18. Phạm vi này khóa UI/UX và control contract của Asset Vault Web;
không mở capability server, không tạo tệp thật và không thay thế bằng Tài sản Bot.

## Mục tiêu

Asset Vault phải là một workspace riêng, bố cục dọc và dễ dùng, chỉ hiển thị dữ liệu
owner-scoped của signed Web account. Người dùng có thể hiểu rõ bốn nhóm thao tác:

1. Thêm tệp riêng tư và tùy chọn gắn Project.
2. Tìm/lọc danh sách active, archived hoặc tất cả bản ghi được server trả về.
3. Tải chỉ bản ghi active; bản ghi archived không được hiện nút tải.
4. Mở panel vòng đời, xem trạng thái/lý do/revision/tham chiếu đã redaction và chỉ
   khôi phục khi server công bố `restore_available=true` cùng `lifecycle_revision` hợp lệ.

## Control contract

| Control | Nguồn/điều kiện | Trạng thái cần thể hiện | Hành vi bắt buộc |
|---|---|---|---|
| `asset-vault-upload` | signed account + CSRF + `assetVaultEnabled` | guarded/ready/processing/failed | `FormData`, định dạng allowlist, tối đa 25 MB, idempotency, không gửi Bot/provider |
| `asset-vault-filter` | owner-scoped list capability | active/archived/all, empty/failed | lọc tại API, reset offset về 0, không ghi query vào URL/storage |
| `asset-vault-page` | list capability | có trang trước/trang sau | giới hạn 50 bản ghi, offset hữu hạn 0–10000 |
| `asset-vault-refresh` | signed account + vault capability | loading/ready/failed | tải lại danh sách và lifecycle đang mở, không giữ dữ liệu cũ khi lỗi |
| `asset-vault-lifecycle-open` | signed account + lifecycle view | loading/ready/guarded | đọc đúng asset UUID, không hiển thị path/hash/storage key/operation ID |
| `asset-vault-archive` | CSRF + archive capability | active → archived hoặc lỗi thật | đọc lifecycle trước, gửi `expected_revision` và idempotency key |
| `asset-vault-lifecycle-restore` | CSRF + restore capability | archived → active hoặc guarded | chỉ cho phép khi server xác nhận `restore_available` và revision; có xác nhận trước thao tác |
| download | bản ghi active + UUID hợp lệ | ready hoặc không có nút | URL same-origin `/api/v1/asset-vault/:id/download`; archived bị khóa |

## Ranh giới dữ liệu và an toàn

- Không dùng localStorage, sessionStorage, PWA cache, URL công khai hoặc fallback sang
  `/assets` của Bot.
- Mỗi yêu cầu list/lifecycle bị khóa bằng session epoch, request epoch, route hiện tại,
  account đã xác thực và `assetVaultEnabled`; phản hồi muộn không được ghi sang phiên khác.
- Khi đọc list lỗi, phải xóa `vaultItems`, đặt `assetVaultReadState=failed` và không
  giữ thẻ của account trước.
- Archive/restore dùng revision do server đọc ngay trước mutation; không suy diễn revision
  từ card cũ hoặc đồng hồ trình duyệt.
- Không gọi provider, không tạo job, không trừ Xu, không sửa PayOS và không tạo output giả.

## Visual/UX contract

- Giữ palette xanh dương/xanh ngọc hiện tại; không đổi sang nền đen.
- Upload, ranh giới thư viện, bộ lọc, danh sách và lifecycle nằm trong các khối dọc rõ ràng.
- Lưới thẻ hai cột trên màn hình rộng, một cột ở breakpoint nhỏ; pagination và form không
  gây tràn ngang.
- Tên tệp, Project, dung lượng và thời điểm cập nhật có hierarchy rõ; trạng thái archived,
  guarded, failed và processing không dùng màu/nhãn gây hiểu nhầm là đã hoàn tất.

## Bằng chứng control-level

- Test riêng: `tests/assets-product-controls.test.mjs` — **5/5 đạt**.
- Full Node suite sau checkpoint: **558/558 đạt**.
- `node --check static/portal/portal.js` và `node --check static/portal/portal-i18n.js`;
  `git diff --check` phải đạt trước push.
- Đây chưa phải runtime/browser/LIVE evidence: upload bytes thật, preview, capability server,
  download delivery, browser AX và production recheck vẫn mở ở UT-07.
