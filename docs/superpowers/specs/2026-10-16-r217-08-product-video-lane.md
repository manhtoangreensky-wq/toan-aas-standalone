# R217-08 — Product Video UI/UX parity

**Status:** `TODO`
**Wave:** W4
**Surface:** `/tools/video`, `/video/create`, `/video/multiscene`, `/video-studio`,
`/video/poster`, `/video/finishing`.

## File có thể sửa khi mở

- video hub/form/studio renderer trong `static/portal/`;
- video presentation/catalogue tests.

## Cấm sửa

Không tự nối provider/worker, không fake MP4, không đổi quote/charge/idempotency/route.

## Contract giao diện

- Hub hiển thị lane theo mục tiêu: prompt-to-video, image-to-video, multi-scene, long video,
  reference/storyboard/script/idea và local edit.
- Form chính chỉ hỏi input cần thiết; advanced settings trong disclosure.
- Flow giữ bảy bước `input → plan → quote → confirm → progress → result → recovery`;
  status và report tách khỏi khả năng download.
- AI edit và manual edit có boundary rõ, timeline/scene/version/history và handoff sang
  Audio/Image/SubDub.

## Acceptance

- Nhóm tác vụ dọc, CTA không lẫn jargon kỹ thuật, mobile không tràn ngang.
- Mỗi lane có empty/loading/guarded/failed/completed; output thật mới có download.
- Locale, keyboard/focus, report và evidence không đổi core contract.

## Verify

```powershell
node --test tests/video-uiux-locale-presentation.test.mjs
node --test tests/*.test.mjs
```

Nếu test tên cũ không tồn tại, dùng đúng focused test được ghi trong R214 và lưu lệnh đã
chạy; không bỏ qua vì khác tên.

## Current source audit 2026-10-16

Video Hub and Studio presentation tests are green and preserve the ordered brief-to-report
flow. AI edit, manual timeline editing, render MP4 and delivery remain guarded/planning
surfaces; no provider output or real artifact evidence exists.
