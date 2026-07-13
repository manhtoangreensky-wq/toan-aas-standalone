# Creative Content Studio — Web-native contract

## Mục đích

Creative Content Studio là workspace authoring độc lập của Web App cho content brief, caption/hashtag, content ideas, hook/script, storyboard và content pack. Đây không phải UI giả lập Telegram và không là adapter gọi provider.

Mỗi bản ghi thuộc signed Web account, có owner check, optimistic revision, version history, audit metadata và archive/restore. Các dữ liệu text riêng tư không được đưa vào idempotency receipt, audit detail, PWA cache hoặc URL.

## Scope đã có

- `/content-studio`, `/content-studio/new`, `/content-studio/{uuid}`.
- Tạo, sửa, archive, restore, duplicate và restore-version cho Content Brief.
- Liên kết reference owner-scoped đang active: Project, Campaign, Prompt Library, Audio Library.
- Tạo content piece thủ công; chọn piece cho brief; sửa, archive, restore, duplicate và restore-version content piece.
- Lịch sử brief và history theo từng content piece.
- Composer tạo đúng ba **local deterministic drafts**. Các khung này là scaffold có thể biên tập, không phải kết quả AI hay deliverable.

## Quy tắc an toàn

- Bắt buộc signed session; tất cả write yêu cầu CSRF, idempotency key, request ID và server-side ownership/revision check.
- `WEBAPP_CONTENT_STUDIO_ENABLED` là feature flag. Body write bị chặn ở raw ASGI boundary tại 128 KiB; giới hạn read/write có scope riêng.
- Chặn secret/token/private key/password/OTP/CVV/số thẻ/bill/TXID/QR và các yêu cầu mô phỏng tác giả, nghệ sĩ hoặc phong cách cụ thể.
- Không có Bot bridge, Telegram, Xu ledger, PayOS/webhook, provider request, job, publish, export hoặc delivery trong module này.
- `compose` trả `execution=local_deterministic_draft_only`, `provider_called=false`, `charge_started=false`; UI kiểm tra các cờ này trước khi rehydrate.
- PWA chỉ cache public shell. `/api/v1/content-studio` và dữ liệu private không nằm trong cache manifest.

## Boundary với Bot

Bot vẫn là authority riêng cho Telegram identity, Xu, PayOS, jobs và trạng thái provider. Content Studio không đọc hay sửa các state đó. Nếu một future workflow cần gửi content sang engine/publish, nó phải có contract và review riêng; không được mở rộng composer hiện tại thành execution ngầm.

## Kiểm thử trọng yếu

- `tests/test_copyfast_content_studio.py`: CSRF, owner isolation, raw body cap, idempotency receipt scrub, policy guard, compose local-only và revision safety.
- `tests/test_content_studio_portal_contracts.py`: route/UI/API boundary, native actions, PWA exclusion và no-bridge/static safety checks.
