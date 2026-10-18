# R218-02/03 — Voice và Music: vị trí và hành vi từng nhóm control

Mục tiêu: dùng luồng Bot, gom thao tác trên workspace Web; xử lý thật chỉ hiện
theo capability/DTO hiện có. Nguồn chi tiết ở inventory R218 B01–B07.
Allowed UI: static/portal/portal.js, portal-i18n.js, portal.css và test tương ứng.
Bot/backend/provider/wallet/auth contracts là protected.

## Voice

| ID | Vị trí / control | Hiện và hoạt động | State / nghiệm thu |
|---|---|---|---|
| VO-01 | Đầu trang, tab Văn bản thành giọng / Giọng thành văn bản / Kho giọng | Một workspace, deep link hiện có | Chuyển tab giữ draft đúng loại |
| VO-02 | Trên text, picker Giọng mặc định / Đã lưu | Default nam/nữ nếu capability distinct; profile có owner/status | Missing/revoked không âm thầm fallback sang giọng khác |
| VO-03 | Textarea chính + đếm từ | Lời thoại user, giữ xuống dòng/Unicode, error theo backend | Đổi giọng không mất text; XSS chỉ text |
| VO-04 | Nhóm Cách đọc: speed number+presets | 0.1–2.0x, default 1.0; Chậm/Bình thường/Nhanh | Out-of-range tại field; cập nhật quote stale |
| VO-05 | Volume slider+number | 0–200%, default 100, nguyên | 0 giữ nguyên + cảnh báo file không tiếng trước confirm |
| VO-06 | Tóm tắt trước CTA | Giọng/từ/speed/volume/giá/tổng/expiry | Quote server, không hardcode giá hoặc cộng lại ví |
| VO-07 | CTA Tạo giọng đọc, phụ Sửa nội dung/Quay lại | Quote hợp lệ + execution capability | Busy/double click/expiry/error giữ draft |
| VO-08 | Vùng kết quả | Player/tải/version/report, tạo lại/dùng Video/SubDub | File readiness thật; preview/full phân biệt |
| VO-09 | Kho: list/search/filter/page | Tên/trạng thái/default/preview/reuse | Chưa ready có retry hợp lệ; no stale account data |
| VO-10 | Menu hàng giọng | Đổi tên/đặt default/tải/xóa/dùng sản phẩm | Xóa confirm riêng; quyền chính xác; report thật |
| VO-11 | CTA Thêm giọng mở wizard/drawer | Consent → mẫu → xác nhận text → tên tùy chọn, tối đa 120 ký tự → quote → preview → lưu | Back từng bước giữ data, không giả biometric verification; giữ đúng giới hạn bridge hiện hành |
| VO-12 | STT upload/source panel | File đúng MIME/size, tiến trình/text/copy/export | Capability unavailable có lý do và hướng xử lý |
| VO-13 | Chọn giọng ở SubDub/Video | Cùng profile ID/owner, returnTo allowlisted | Quay về đúng sản phẩm với draft còn nguyên |

Bot anchors: bot.py:159975,160106,160123,160166,160261,167782,169187,169226,
169264,169455,170998,171866,174810..174915.

### Phiếu P1 VO-03/04/05 — phản hồi biểu mẫu

- Source: `static/portal/portal.js` — `renderFormCard`, `voiceFeedbackMetrics`,
  `renderVoiceFormFeedback`, `syncVoiceFormFeedback`; copy `voiceUi.form.*` và
  `voiceUi.field.speed.presetLabel`; CSS `[data-voice-muted-warning]` ở `portal-theme.css`.
- Dưới thiết lập, trước CTA: số từ tách theo khoảng trắng và số ký tự Unicode. Đây
  là phản hồi rà soát, không dùng để tính giá. Không sửa lời thoại khi đếm.
- Âm lượng đúng 0: cảnh báo file không tiếng, vẫn giữ 0. Trống hoặc khác 0 không
  hiển thị cảnh báo. Kéo thanh/nhập số cập nhật cảnh báo tại chỗ, giữ focus và draft.
- Hydration cùng phiên giữ text và giá trị 0. Nhãn preset tốc độ theo locale cả trong
  accessibility tree. Không đổi payload báo giá/xác nhận, capability hoặc bridge.
- Verify: `node --test tests/voice-input-feedback.test.mjs` → 4/4; bộ inventory/flow
  cùng test mới → 64/64. Browser renderer localhost có 18 cấu hình (3 locale × 2 theme
  × 3 viewport), 2 route `/voice/tts` và `/voice/saved`/cấu hình; không có integration.js.
  Không tính dữ liệu mẫu hay source renderer thành bằng chứng đăng nhập/backend/live.
- VO-09/10/13 giữ mở: API `/voice/profiles` hiện không có search/pager/management
  contract; các link mở công cụ không mang profile ID. Không tạo nút luôn disabled
  để đánh dấu một control đã hoàn tất.

## Music

| ID | Vị trí / control | Hiện và hoạt động | State / nghiệm thu |
|---|---|---|---|
| MU-01 | Tab Nhạc nền / Bài hát / Kho nhạc & SFX | Chung workspace, form theo mode | Bài hát giữ lời; nền không lẫn vocal fields |
| MU-02 | Brief mục tiêu/phong cách/cảm xúc | Idea và style tách rõ; ví dụ thay placeholder máy móc | Validation giữ nội dung |
| MU-03 | Lời bài hát + cách nhập/tạo từ idea | Chỉ Bài hát, văn bản nguyên gốc | Không dịch lời user khi đổi locale UI |
| MU-04 | Giọng hát Nam/Nữ/Song ca/Tự động | Chỉ Bài hát, server options | Đổi tier không reset vocal |
| MU-05 | Tier Cơ bản/Tiêu chuẩn/Cao cấp | Giá/khả năng theo sản phẩm từ server | Selected/quote stale/error, không lộ provider model |
| MU-06 | Độ dài tùy chọn nâng cao | Chỉ giá trị reachable được hợp đồng hiện hành xác nhận | Half/full/18/30/60 cũ là conditional, không tự áp |
| MU-07 | 3 thẻ phương án gợi ý | Nội dung/tempo/khác biệt, Chọn/Đổi/Sửa/Back | Gợi ý khác output audio; không trừ tiền từ UI |
| MU-08 | Review + Tạo nhạc | Sản phẩm/tier/vocal/lời/phương án/tổng | Confirm chỉ khi quote/capability valid |
| MU-09 | Kết quả từng bản | Player/tên/duration/tải/lưu/dùng Video | User yêu cầu 2 bản; phải xác minh response/delivery, thiếu ghi gap |
| MU-10 | Kho/SFX search/filter/list/page | Nghe/tải/chọn dùng, tệp tự có | Empty/error/missing license/status rõ |
| MU-11 | Chỉnh nhạc | Hiển thị khả năng theo runtime | Bot action hiện chỉ guard; không vẽ editor chạy giả |
| MU-12 | Progress/report/recovery | Queued/generating/ready/delivery failed | Kiểm tra lại không resubmit/tạo tác vụ thay thế |

Bot anchors: bot.py:162316..162388,162697..162873,169508,169536,171046,
171061,172099..172105,172488..172632.

## Acceptance / thứ tự phiếu

VO-A inventory → VO-B picker/draft → VO-C clone/vault → VO-D quote/result → VO-E browser.
MU-A mode/fields → MU-B suggestions → MU-C quote/result → MU-D library/guard → MU-E browser.
Mỗi phiếu trích exact source và control IDs, một Builder RUNNING, protected diff sạch.
Verify meaningful renderer/interaction tests + browser VI/EN/ZH, themes, 375/768/1440.
Output real generation, editor engine và 2-track delivery giữ T0 nếu DTO/capability thiếu.
