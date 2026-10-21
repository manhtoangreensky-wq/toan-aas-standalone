# SD-D2 — Rà soát cấu hình và cân âm thanh rõ ràng

Thực thi sau SD-C2 UI/delivery gate, trước SD-E2 semantics. Một completion
ledger tại `WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-R218.md`; không mở ledger khác.

## CONTRACT

Allowed: `static/portal/portal.js` chỉ renderSubDubHub, SubDub copy VI/EN/ZH,
capture/normalize/update local draft; `static/portal/portal.css` chỉ lớp mới
`.portal-subdub-volume-number` và bố cục con trong `.portal-subdub-volume-controls`;
`tests/subdub-review-volume-controls.test.mjs`, SubDub regression, docs/evidence.
Protected: SD-B2/SD-C2 behavior, Voice/Music đã khóa, theme/token/motion, backend,
auth/schema/API/DTO/provider/Bot/ví, quote/receipt/job/download guard và quyền.

## SD-D2A — bước3 cho thấy lựa chọn thật (làm trước)

1. READ2–5phút: đọc `renderSubDubHub`, draft helpers và copy hiện tại; khóa
   các row giá/chi phí/số dư lấy server. Không tính hoặc bịa giá từ cấu hình.
2. RED2–5phút: thao tác mode/draft khác mặc định; hiện tại Stage3 chỉ có mode
   và các row tiền, nên test phải bắt thiếu target/lane/mix/vị trí/format.
3. BUILD2–5phút: thêm nhóm `Thiết lập của bạn` / `Your settings` / `你的设置`.
   Hàng dọc: nguồn phụ đề có/chưa có, ngôn ngữ nguồn/tệp chưa có, target,
   kiểu giọng, gốc%, lồng tiếng%, vị trí/kiểu phụ đề và định dạng đúng mode.
   Không hiện row không phù hợp. Nhãn lấy copy locale; dữ liệu được escape.
4. VERIFY2–5phút: đổi lựa chọn bằng input/change và đổi mode cập nhật summary
   tại chỗ từ cùng draft, không remount form, không request/mutation; unknown
   source/giá/duration/speaker-count giữ unknown, không thành0 hoặc kết quả giả.

   Dùng draft đã chuẩn hóa và truyền `nextMode` khi đổi tab; không đọc query
   trước `replaceState`. Custom ISO hiển thị riêng, không tự coi là ghi đè
   dropdown khi chưa có contract. Nguồn phụ đề chỉ là khai báo của người dùng;
   tệp/ngôn ngữ đã nhận diện, profile cụ thể, speaker-count vẫn chưa xác minh.
   Subtitle có format/rule/position; Translate thêm target/custom/display;
   Dubbing có target/custom/lane/mix; Combo gộp các row phù hợp, không row ẩn.

## SD-D2B — slider + số và mute (sau D2A)

5. RED2–5phút: test thiếu number input và cảnh báo0. Cả hai chiều nhập số↔kéo
   slider phải giữ0/100/200 và output/summary cùng giá trị, kể cả mode/remount.
6. BUILD2–5phút: number input có nhãn đầy đủ, step1, min0, max gốc100/dub200,
   target44px, cỡ chữ16px, rộng80–96px; không thay token màu. Event sync cặp
   control trước capture để control cũ không ghi đè giá trị mới. Không dispatch
   event đệ quy. Số rỗng/sai bounds hiện lỗi rõ, giữ giá trị hợp lệ gần nhất.
7. BUILD2–5phút: khi dub0 hiện inline `Giọng lồng tiếng đang tắt trong cấu hình`
   và checkbox xác nhận cục bộ, đủ VI/EN/ZH; gốc0 có thông báo tương ứng.
   Ack0 không phải receipt hoặc quyền gửi xử lý; khi âm lượng rời0 thì xóa ack,
   quay lại0 phải xác nhận lại. Mức mới chưa áp dụng vào output khi xử lý guarded.
8. VERIFY2–5phút: input/output/summary/ack và giữ focus đúng; không mở CTA,
   không network/storage/provider/wallet. Browser375/390/768/1440 × themes ×
   profile VI/EN/ZH, keyboard Arrow/number entry, label/AX/ảnh, no overflow/error.

## AC / evidence gate

- [x] D2A summary phản ánh chính xác cấu hình hiện tại theo mode/locale.
- [x] D2B number/range/output/summary đồng bộ, 0 không reset, bounds rõ.
- [x] Mute0 có cảnh báo/ack local trung thực; không bị hiểu là output/receipt.
- [x] Focus/form giữ nguyên khi cập nhật; palette xanh/ngọc/chữ sáng không đổi.
- [x] Browser thật+AX/ảnh, source/protected comparator và regression đạt.
- [ ] Docs/tester/provenance/PR đúng candidate, CI xanh; không deploy/LIVE suy đoán. Đang chờ commit/push wave này.

## Evidence SD-D2 — 21/10/2026

- RED browser bắt thiếu summary và number input; GREEN `subdub-review-volume-green-20261021.json`.
- Browser GREEN: 24/24 cấu hình VI/EN/ZH × sáng/tối × 375/390/768/1440; lỗi trang/console/request ghi/request ngoài/overflow đều `0`. Đã kiểm số↔thanh kéo hai chiều, giá trị sai, mute cục bộ, đổi mode, Voice-return, đổi phiên và AX/ảnh. Không upload, quote, job, provider, ví hoặc output thật.
- Node targeted: 44/44 pass, full Node 880/880 pass, exit0; `node --check static/portal/portal.js` và `portal-i18n.js` exit0. Python scoped 49/49 pass; các lỗi ngoài scope/baseline được giữ nguyên và phân loại, không làm yếu test. Reviewer độc lập: 0 Critical/Important; khoảng trống updater đã bổ sung test helper production.
- CSS chỉ đổi bố cục con volume controls và number style; token xanh/ngọc, theme và motion được bảo vệ. Giá/chi phí/nguồn tệp/ngôn ngữ nhận diện vẫn unknown nếu không có dữ liệu server.

Verify: `node --test tests/subdub-review-volume-controls.test.mjs tests/subdub-local-draft-state.test.mjs tests/subdub-hub-presentation.test.mjs tests/subdub-voice-continuation.test.mjs`
→0fail; sau đó full Node và browser QA cô lập. Nếu cần sửa hợp đồng API/engine/
quote để thực thi, ghi T0 và không code trong SD-D2. Motion vẫn làm cuối.
