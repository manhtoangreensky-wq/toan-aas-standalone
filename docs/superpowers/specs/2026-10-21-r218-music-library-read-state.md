# MU-E-01 — Tải đúng thư viện và phản hồi đúng kết quả

BASE_SHA=7569f61420e3fe243d5a453e7f1912497d1e8503; PR654.
Đây là bước tiếp theo sau Music review; MU-E chưa đóng toàn bộ.

## CONTRACT

- Allowed: `static/portal/integration.js` chỉ `hydrateMusicLibrary`, nhánh
  bốn action thư viện trong `handleAction` và helper bản địa hóa riêng;
  `static/portal/portal.js` chỉ empty/loading của `renderMusicLibrary` và nhánh
  riêng `portal-music-library-pagination` trong paginator (không đổi chữ ký);
  `static/portal/portal-i18n.js` chỉ `musicLibrary.*`; test và bằng chứng.
- Protected: bộ kiểm role/response/boundary, endpoint/DTO/quyền, epoch/session,
  storage, backend/auth/schema, engine/provider/Bot/ví/thanh toán, mọi nhóm khác.
- Không thêm khả năng nghe/tải/tạo nhạc; không thay CSS hoặc palette navy/teal.

## Lỗi đã xác minh

1. Bootstrap luôn tạo listing Music; SFX hydrate kế thừa role Music và throw
   trước GET. Không được nới validator: listing cũ chỉ tái sử dụng nếu cùng role.
2. Hydration trả failed/stale nhưng action vẫn toast success; toast hardcode VI.
3. Query rỗng kết quả bị mô tả như toàn thư viện không có nội dung.
4. Loading được đánh dấu guarded và thiếu aria-busy.
5. Paginator thật hardcode VI cho mọi class ngoài Memory; test cũ thay toàn
   paginator bằng `<nav>1</nav>` nên che lỗi. Chỉ bản địa hóa nhánh Music.

## Thứ tự / acceptance

- [x] A1 Test RED: SFX từ bootstrap Music phải GET role=sfx, offset0, q rỗng;
  chuyển role không mang từ khóa/trang cũ. Cùng role vẫn giữ q/offset.
- [x] A2 Failed/malformed không có card cũ hoặc success; stale không có toast;
  giữ epoch/auth/role gate, không ghi storage và không gọi endpoint khác.
- [x] A3 Search/clear/page/refresh có phản hồi VI/EN/ZH theo kết quả thật;
  phân trang không tự gọi “trang tiếp” khi đang quay lại trang trước.
- [x] A4 Query-empty khác true-empty; loading có aria-busy và state processing;
  không cho bấm lại nút đang tải. Nội dung người dùng giữ nguyên và escape.
- [x] A5 Node hành vi dùng hydrator/projector/handler thật với transport QA;
  browser hồ sơ locale thật cho hai route/alias, pending/failed/empty/query/
  clear/page và route-race. Có desktop/mobile, AX/ảnh, lỗi và network counters.
- [~] A6 Review/diff, full Node853/853, Python metadata/i18n/motion29/29;
  Library boundary5pass/1baseline-fail đã đối chiếu. Provenance/CI mới chờ delivery.

Verify: `node --test tests/music-library-runtime-state.test.mjs tests/music-library-locale-purity.test.mjs`
→ 0fail; `python -m pytest -q tests/test_music_library_portal_contracts.py`
→ 0fail. Browser dùng server/DB QA cô lập, không submit feature/provider.

Chưa đo phần nào thì để mở phần đó; không suy ra toàn bộ Music đã tương đương Bot.
Evidence: `reports/audit/R218-MUSIC-LIBRARY-READ-STATE-QA-20261021.json`;
36 focused tests, browser39 và protected12/generic20 comparators không khác.
