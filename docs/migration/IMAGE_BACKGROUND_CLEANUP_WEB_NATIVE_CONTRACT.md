# Image Background Cleanup Web-native contract

## Phạm vi

`image_background_cleanup` là một Image Operation Web-native độc lập. Nó nhận
duy nhất `source_asset_id`, một profile đóng (`white_studio`, `light_neutral`
hoặc `dark_neutral`) và `idempotency_key` từ signed Web session. Nguồn phải là
ảnh active thuộc Asset Vault của cùng account.

Máy chủ chỉ duyệt flood-fill từ các pixel ở mép ảnh và làm trong suốt vùng
liên thông có màu gần profile đã chọn. Output phải là PNG RGBA cùng kích thước,
có ít nhất một pixel trong suốt, được mở lại, hash và kiểm tra storage trước
khi download. Không tìm thấy nền phù hợp là trạng thái thất bại rõ ràng; không
có output thay thế.

## Ranh giới authority

- Web giữ operation record, output private và lịch sử owner-scoped của utility
  này.
- Web không gọi Bot/Core Bridge, provider, RemoveBG/Cutout, Telegram, jobs,
  wallet, Xu, PayOS hoặc webhook cho operation này.
- File nguồn không bị sửa. Browser không gửi bytes ảnh, URL, path, mask, màu
  RGB tự do hay tham số decoder.
- `/image/remove-background` vẫn là route bridge canonical riêng và tiếp tục
  guarded; không dùng callback `imgtool|*` để khởi chạy utility này.
- Service worker không cache endpoint operation hoặc PNG riêng tư.

## UI và lifecycle

Route customer là `/image/background-cleanup`. Portal chỉ mở form sau khi
Asset Vault và lịch sử riêng đã hydrate thành công. Flow là:

`draft → confirm → queued/processing → completed|failed|guarded`

Download chỉ hiện khi server trả `completed`, `download_ready=true` và signed
ownership/integrity còn hợp lệ. History combined chỉ nhận kind
`image_background_cleanup` qua allowlist typed; lỗi đọc private data xóa
projection cũ thay vì hiển thị cache hoặc tài sản Bot.

## Feature gate

`WEBAPP_IMAGE_BACKGROUND_CLEANUP_ENABLED` mặc định tắt ở môi trường local/test.
Flag chỉ cấp capability cho route Web-native này; nó không bật provider, bridge,
payment hay bất kỳ writer ledger nào.

## Kiểm thử bắt buộc

- Backend: success/private PNG, idempotency, profile ngoài allowlist, no-match,
  cross-owner, tampered output và disabled gate.
- Portal: route/layout, CSRF/idempotency payload, typed history hydration,
  guarded canonical remove-background route, không browser bytes/cache/provider
  action.
- Parity: raw `imgtool|*` vẫn fail-closed trong migration audit.
