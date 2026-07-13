# Voice Studio & Consent Vault — Web-native contract

## Mục đích

Voice Studio là workspace authoring độc lập của Web App để tổ chức **voice direction**, self-attested consent metadata, script, cue-sheet và lịch sử revision riêng tư. Nó không phải bản sao của Bot Voice Vault, provider voice profile, trình phát audio, hay đường đi tắt để clone một người.

Mỗi vault và script thuộc signed Web account, có owner check, optimistic revision, version history, idempotency và audit metadata. Text riêng tư không xuất hiện trong idempotency receipt, audit detail, URL hoặc PWA cache.

## Scope đã có

- `/voice-studio`, `/voice-studio/new`, `/voice-studio/{uuid}`.
- Tạo, sửa, archive, restore, duplicate và restore-version cho voice direction vault.
- Voice direction `delivery_style`, `brand_narration` và `consented_reference` chỉ lưu metadata; `consented_reference` bắt buộc self-attestation hoặc bản ghi consent đã thu hồi, cùng ghi chú tối thiểu. Bản ghi đã thu hồi không thể là default local và khóa toàn bộ authoring script cho đến khi có self-attestation mới.
- Tạo, sửa, archive, restore, duplicate và restore-version cho script riêng tư; có tag, pace, chỉ dẫn thể hiện và ghi chú phát âm.
- Liên kết reference owner-scoped đang active: Project Center và Creative Content Studio.
- Composer tạo đúng ba **local deterministic script scaffolds** có thể biên tập.
- Cue-sheet được ước lượng xác định từ text và pace; đây là trợ giúp review nhịp đọc, không phải transcript, subtitle, preview hay output audio.

## Quy tắc an toàn

- Bắt buộc signed session; mọi write yêu cầu CSRF, idempotency key, request ID và server-side ownership/revision check.
- `WEBAPP_VOICE_STUDIO_ENABLED` là feature flag, mặc định `true`. Body write bị chặn tại raw ASGI boundary ở 128 KiB; read/write có rate scope riêng.
- Chặn secret/token/private key/password/OTP/CVV/số thẻ/bill/TXID/QR và văn bản yêu cầu mô phỏng, nhái, clone hoặc impersonate giọng của người cụ thể.
- `self_attested` là tuyên bố metadata của người dùng, **không** phải xác minh, cấp phép hay approval để clone/preview/audio processing.
- `revoked` giữ lại metadata để audit nhưng không cho tạo/sửa/nhân bản/khôi phục script hoặc tạo cue-sheet; archive vẫn được phép để thu hồi nội dung đang hoạt động. Vault hay script đã archive cũng khóa tất cả mutation con và cue-sheet ở server.
- Module không lưu raw audio, file upload, provider voice ID, Telegram file ID, preview URL, provider payload, job, Xu, payment hoặc PayOS data.
- Composer và cue-sheet luôn trả `provider_called=false`, `audio_created=false`; giao diện phải kiểm tra các cờ này và không được hiển thị player, download hay output giả.
- PWA chỉ cache public shell. `/api/v1/voice-studio` và dữ liệu private không nằm trong cache manifest.

## Boundary với Bot và provider

Bot vẫn là authority riêng cho Telegram identity, Xu, PayOS, jobs, provider state, TTS, voice clone, preview và output delivery. Voice Studio không đọc hoặc ghi bất kỳ state nào trong số đó, và route `/voice-studio` được cố ý tách khỏi Core Bridge `/voice/*`.

Một tương lai có TTS/clone/preview chỉ có thể dùng dữ liệu Web này qua adapter riêng có authentication, consent verification, policy review, provider readiness, charge/delivery contract và kiểm thử độc lập. Không được mở rộng endpoint authoring này thành gọi provider ngầm.

## Kiểm thử trọng yếu

- `tests/test_copyfast_voice_studio.py`: signed session/CSRF, raw body cap, idempotency receipt scrub, consent/anti-imitation guard, owner isolation, revision và deterministic cue/composer boundary.
- `tests/test_voice_studio_portal_contracts.py`: route/UI/API boundary, native actions, no-bridge/no-provider/no-audio static contract và PWA exclusion.
