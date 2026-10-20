# SD-B2 — Giữ cấu hình cục bộ giữa các mode SubDub

BASE_SHA=83b6623f45e1c9e99a341690f54fbef3884081c2; dependency: SD-01..21
control-level. Đây chỉ là lớp UI/UX; không mở engine, upload, quote, job hay
provider.

## Contract

Allowed: `static/portal/portal.js` và `tests/subdub-hub-presentation.test.mjs`;
spec/evidence/checklist/state. Protected: Bot/API/DTO/auth/schema/wallet,
CSS/palette/motion, route aliases, callback names, guarded CTA/report, file input.
Draft chỉ nằm trong `transientFormDrafts` của signed tab-memory; không URL,
localStorage, cookie hoặc provider ID.

## Acceptance

- [x] Khi có cấu hình local khác mặc định, render lại Dubbing và Combo giữ
  target, custom target, lane giọng, âm lượng gốc 0, âm lượng lồng tiếng 200,
  vị trí phụ đề và kiểu hiển thị tương thích.
- [x] Mode selection chụp panel đang mở trước khi đổi; panel mới nhận các
  trường tương thích; giá trị `0` không bị `|| default` làm mất.
- [x] Input/change trong SubDub cập nhật draft tab-memory; mode query/CTA/report
  guarded và field không phù hợp không biến thành payload thực thi.
- [~] Test21/21 focused; browser/AX/mobile/rerender bằng integration thật chưa
  chạy trong spec này. Handoff Voice, number/mute và semantics để SD-C2..E2.

Verify: `node --test tests/subdub-hub-presentation.test.mjs` →21/21; syntax
`node --check static/portal/portal.js` → exit0. Provider/wallet/deploy/live=0/0/NO/NOT_TESTED.
