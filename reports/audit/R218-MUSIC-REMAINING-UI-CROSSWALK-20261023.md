# R218 Music — đối soát yêu cầu còn lại, tách UI khỏi engine

Ngày 23/10/2026. BASE `e8738b5ac6078c86e8793632cab3d0f3488e3f09`.
Standalone WebApp; branch `webapp-r218-billing-ui-20261022`; PR661 / Issue664.
Nguồn yêu cầu: Music MU01..12 trong spec
`2026-10-18-r218-02-03-voice-music-controls.md`, master P2 và chỉ thị Owner.
Chỉ đọc source WebApp; không sửa Bot/runtime/provider/ví.

D1–D2 đã nhận tại receipts6368236480/6369576116, CI39985131009 cả hai job
thành công. Không làm lại hai trang native đã khóa. E là phạm vi khác:
hai product form `/music/create` và `/music/song`.

## 1. Yêu cầu → bằng chứng → phần chưa xong

| ID | Frontend hiện có | Bằng chứng / source anchor | Phần còn mở và hành động đúng |
|---|---|---|---|
| MU01 — mode/draft | Nav Nền/Bài hát/Kho/SFX; chuyển nền↔bài hát cùng document | portal.js11558/25947; 27 test VM; actual E48 mode/Back draft checks | Reload/file/canonical execution/LIVE chưa chứng minh; không dựng lại tab |
| MU02 — idea/style | Hai form chỉ có brief, chưa có ô style riêng | FIELD_SETS.music/song864/870; job bridge198/205 nhận style_prompt; draft API520–527 nhận style, không style_prompt | Chốt mapping draft+estimate+confirm trước; không thêm field bị server bỏ qua |
| MU03 — lời/từ idea | Song có mode/lyrics Unicode, không lẫn background | portal.js873; E24 song configs giữ lyrics qua tier/vocal/mode | Tạo lời từ idea chưa có runtime proof; placeholder không phải generation PASS |
| MU04 — giọng hát | Đủ auto/male/female/duet | portal.js874/bridge57; actual E288 vocal checks | Chưa chứng minh giọng trong tệp audio output |
| MU05 — ba tier | basic/standard/premium; không hardcode giá bán | portal.js866/872/11534; E144 tier checks; quote tests có 0/unknown | Giá canonical/runtime chỉ từ receipt; không tự tính Xu |
| MU06 — độ dài | seconds/half/full và số giây trong form | portal.js876/API2252/integration1984; job bridge143/207 chỉ normalize giây | Semantic contract gap; không tự quy đổi half/full hoặc sửa min theo suy đoán |
| MU07 — ba gợi ý | Tối đa 3 item server, Copy/Apply prompt vào brief | portal.js32203/39216; integrated tests và receipt review cũ | Chưa đủ workflow Đổi/Sửa/Back riêng; đổi bộ gợi ý cần contract, không fabricate alternate set |
| MU08 — review/confirm | Giá server và confirm gate có; thiếu summary input đã gửi | portal.js11612/11697/32248; integration38674 giữ flow.input | UI gap F: sản phẩm/tier/vocal/lyrics/length/brief read-only; không sửa DTO/confirm |
| MU09 — output/2 bản | Report/tracking; public job có một artifact_url | portal.js32228; music job bridge324 | Chưa có proof 2 audio/player/tải/lưu/reuse; không vẽ hai audio card cho đủ yêu cầu |
| MU10 — thư viện/SFX | Metadata/search/clear/refresh/pagination | portal.js14690; MU-E01/E02 evidence39 configs | Nghe/tải/chọn dùng thật ngoài metadata authority; không giả sound catalog |
| MU11 — chỉnh nhạc | Chưa có Web Music editor contract được xác minh | Không thấy renderer/editor proof trong inventory Music | T0 contract/runtime backlog; không dựng editor giả |
| MU12 — tiến trình/phục hồi | Report status/progress/output/download/delivery/reason, job link | portal.js32228; report-only 50% và direct queued test | Delivery failure và retry không resubmit cần runtime proof; không dùng tạo lại thay status check |

Ba suite đã chạy độc lập:

```powershell
node --test tests/music-product-controls.test.mjs tests/music-workspace-draft-navigation.test.mjs tests/music-workspace-runtime-integration.test.mjs
```

Kết quả 27/27, exit0,1289.1715ms. “Runtime integration” ở tên file vẫn là
VM renderer/fixture envelopes, không phải native backend runtime. Control test
có synthetic fields nên không chứng minh actual FIELD_SETS đủ style hay
engine thực thi đúng duration/giọng.

## 2. Finding UI thật và hàng đợi không bỏ sót việc

1. **E — độ đọc/nhập:** actual baseline24 có 66 lỗi tương phản nền sáng
   (2,021:1) và 132 ô nhập15px. Flash R1 trả hai scoped CSS rules;
   actual R1 green48 có 264 helper/264 input đạt AA/16px. Ảnh QA phát hiện
   thiếu gate nhãn/placeholder nên E02 đã mở lại trước push; R2 bổ sung đúng
   hai rule còn lại, final48 nhãn264/placeholder120 cũng đạt AA. Tổng14dòng/
   4rule, không đổi JS. Chỉ đóng delivery khi CI mới/receipt đạt.
2. **F — review trước xác nhận:** sau E delivery, thêm summary read-only
   từ `flow.input` của estimate hợp lệ. Dữ liệu cũ được ghi rõ là snapshot
   đã gửi; quote expiry/fingerprint/confirm giữ nguyên. Không giả ordinal/ID
   phương án vì Apply hiện chỉ lưu prompt vào brief. Missing field không bù
   giả; half/full chỉ là lựa chọn, không tự diễn giải số giây.
3. **MU07 — chọn/sửa/quay lại:** thao tác sửa brief sau Apply đã tồn tại.
   Chốt workflow riêng trước khi thêm nút. Nếu không có contract đổi bộ
   gợi ý thì đưa T0, không tạo các bộ ngẫu nhiên giả.
4. **Technical/runtime backlog:** style mapping, duration semantics, audio,
   hai bản kết quả, editor và provider vẫn được giữ. Đây là các mục làm cuối
   theo chỉ thị Owner, không xóa khỏi scope hoặc tick từ UI PASS.
5. Xong Music UI có bằng chứng thì tiếp SubDub/Image/Utilities/Admin/Video;
   motion cuối cùng.

## 3. Giới hạn bằng chứng

Không kết luận whole Music/Bot parity/audio generation/payment/LIVE PASS.
Không đổi engine/schema/ENV/API/wallet/PayOS/auth/Bot. E dùng app QA đã đăng
nhập và không API fixtures, nhưng vẫn là localhost. OS Dynamic Type, bàn phím
máy thật, installed PWA, production và output cần các cổng riêng.
Mọi yêu cầu không có bằng chứng tương ứng vẫn để mở.
