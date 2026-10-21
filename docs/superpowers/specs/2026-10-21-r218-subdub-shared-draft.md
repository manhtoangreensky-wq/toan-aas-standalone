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

- [x] Mở lại và sửa: test phải thao tác control thật và capture trước khi đổi mode,
  không bơm sẵn draft. Range không name và position có suffix phải normalize.
- [x] Khi có cấu hình local khác mặc định, render lại Dubbing và Combo giữ
  target, custom target, lane giọng, âm lượng gốc 0, âm lượng lồng tiếng 200,
  vị trí phụ đề và kiểu hiển thị tương thích.
- [x] Mode selection chụp panel đang mở trước khi đổi; panel mới nhận các
  trường tương thích; giá trị `0` không bị `|| default` làm mất.
- [x] Input/change trong SubDub cập nhật draft tab-memory; mode query/CTA/report
  guarded và field không phù hợp không biến thành payload thực thi.
- [x] Correction25/25 focused và browser24 cấu hình signed QA hồ sơ VI/EN/ZH
  × sáng/tối ×375/390/768/1440: Dubbing→Combo→Dubbing→Combo→render lại,
  latest target, format riêng, identity projection cleanup, AX/ảnh, lỗi/UIwrite/
  external/overflow0. Backend logout và quyền server không được suy ra từ projection.
- [ ] CI mới trên source correction còn cần kết thúc; Handoff Voice,
  number/mute và semantics vẫn ở SD-C2..E2.

## Amendment trước correction

Không tiếp tục vá bằng regex HTML hoặc đổi thứ tự attribute để chiều test.
Render giá trị đã chuẩn hóa trực tiếp vào template; dùng chung scalar draft
cho control tương thích, format riêng giữ theo mode. Không lưu File, URL,
profile/provider ID. Session thay đổi/đăng xuất phải xóa slot `/subdub` qua
presentation session gate tương tự Voice/Music (không đổi auth server).
Mở rộng allowed chỉ thêm test hành vi `tests/subdub-local-draft-state.test.mjs`
và hook SubDub riêng trong mount; không thay signature/hành vi Voice/Music.
Browser signed QA kiểm Dubbing→Combo→Dubbing→render lại, output0/200 và một
radio được chọn; stale session và dữ liệu không hợp lệ phải fail-closed.

Evidence correction: `reports/audit/R218-SUBDUB-DRAFT-RUNTIME-CORRECTION-QA-20261021.json`.
BrowserRED14 sai lệch trước sửa; GREEN24/24 không còn sai lệch. Full Node861/861,
Python119/119 gồm UI foundation/metadata/i18n/motion. Không dùng test21 cũ hay
comment chứa câu cũ để thay thế kiểm chứng hành vi.

Verify: `node --test tests/subdub-hub-presentation.test.mjs` →21/21; syntax
`node --check static/portal/portal.js` → exit0. Provider/wallet/deploy/live=0/0/NO/NOT_TESTED.
