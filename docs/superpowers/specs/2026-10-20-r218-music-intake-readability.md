# MUSIC-INTAKE-READABILITY-001 — mô tả trước, hướng dẫn gọn

Root C:/Users/toann/Documents/Codex/_webapp-r218-voice; PR654;
baseline delivered2c21682, Voice local report/intake đang được nghiệm thu trước.
Chỉ mở BUILD sau khi Voice-workspace-final đạt source/browser.

## Evidence và kết quả cần đạt

App QA localhost9423 đăng nhập thật/DB tạm; `/music/create` và `/music/song`
đều200, console/overflow0. DOM raw `../qa/r218-voice-inventory/product-ui-probe.json`
cho thấy H1 và H2 lặp nguyên tiêu đề/mô tả; 4 bước + 3 thẻ gói + 3 thẻ gợi ý
trống nằm trước form; các label/help còn brief/capability/canonical/server,
panel bên dưới lộ Engine/Workflow/music_background/companion/Project Center.

Một workspace Music cho mỗi mode, đưa cấu hình làm việc lên đầu; giữ thông tin
chi tiết trong disclosure có tên, không xóa tùy chọn Bot hoặc tạo kết quả giả.

## Allowed / protected

Allowed `static/portal/portal.js` trong `renderMusicProductGuidance`,
`musicProductFields`, nhánh Music của `renderFormCard`/`renderWorkspace`;
`portal-i18n.js::musicProduct`; CSS selector mới chỉ Music;
test Music tương ứng và ledger/evidence.
Không đổi Voice helpers/timer/consent/schema, backend/integration, auth,
provider, wallet/PayOS, CI hoặc action/field/option values.

## Bước thực thi, từng bước 2–5 phút

1. Guidance trở thành điều hướng rõ Nhạc nền/Bài hát/Kho nhạc & SFX/Tạo SFX.
   Chỉ một tiêu đề chính của sản phẩm; link có aria-current và nhãn bản địa.
   Giữ href chuẩn, không giả có engine/editor. Hai mode tạo nhạc chuyển
   trong document bằng helper Music riêng: chỉ nhận hai href đã biết,
   signed session; Ctrl/Meta/middle/target/download giữ hành vi link gốc.
   Giữ Map draft theo route, lang/theme query có allowlist; mỗi mode giữ
   brief/lyrics/vocal/tier/duration riêng. Session đổi/mất token chỉ xóa draft
   Music, không đụng Voice hoặc dữ liệu khác. Hook cleanup ở mount trước render;
   không gửi request hay mở quyền. Thêm test hành vi navigation/session.
2. Bốn bước và giải thích ba gói giữ đủ trong `<details>` đóng mặc định;
   summary “Xem quy trình và các gói”, min44px/focus đúng token. Bỏ ba thẻ
   phương án rỗng khỏi màn hình đầu; chỉ ghi trạng thái chờ gợi ý gọn.
   MU-B sẽ render phương án có dữ liệu thật, không coi placeholder là kết quả.
3. Form vẫn đủ field/option/mode/giọng/tier/lyrics/duration, giữ local draft và
   capability submit. Empty labels và draft actions dùng catalogue Music đủ
   VI/EN/ZH, không generic VI rơi vào bản EN. VI dùng “mô tả”, “hệ thống”,
   “bản nháp”; không brief/canonical/capability/server.
4. Nhánh Music không render status/summary kỹ thuật hoặc Bot-handoff panel
   Engine/Workflow/companion. Giữ thông tin trạng thái cần thiết ở hero/form/
   kết quả. Không đổi generic handoff của sản phẩm khác.
5. Renderer/interaction và browser trên app QA: VI/EN/ZH × sáng/tối ×
   390/768/1440 ×2 route; mở hướng dẫn thấy đủ chi tiết; đầu trang không có
   3 thẻ gợi ý rỗng; form giữ option values/guard; không audio/price/download giả.

## Gate và phần sau

- [ ] AC01 hierarchy: title không lặp, mode nav, form trước nội dung mở rộng.
- [ ] AC02 đủ lựa chọn gói/vocal/lyrics/duration/3 bước review trong hướng dẫn.
- [ ] AC03 locale và local draft actions đúng cả ba ngôn ngữ; palette giữ nguyên.
- [ ] AC04 source/browser/AX/screenshot/console/overflow, mutation0.
- [ ] AC05 protected Voice/backend/integration sạch.

`node --test tests/music-product-controls.test.mjs tests/music-flow-state-and-surface-contract.test.mjs` phải fail0.
Thêm renderer test cho hierarchy/disclosure và locale, không chỉ đếm regex.
Muốn sửa assertion cũ đếm3 placeholder phải ghi rõ: thay bằng kiểm không có
thẻ âm nhạc/gợi ý giả khi dữ liệu thiếu, không giảm nội dung có dữ liệu thật.

Sau A: MU-B suggestions/quote/report; MU-C library/SFX/states; browser của
từng phần rồi chuyển SubDub. Runtime/2 bản nhạc/editor giữ T0 nếu contract thiếu.
Builder chỉ dùng Gemini3.8Flash khi runtime hoạt động; probe READY0turn hiện
không nhận authCLI nên không tiếp tục vòng gọi vô ích hoặc dùng Pro. Primary
thực hiện phần được giao trong lúc ghi rõ runtime Builder bị lỗi.
