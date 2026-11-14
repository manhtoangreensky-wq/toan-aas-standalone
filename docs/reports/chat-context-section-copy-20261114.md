# Ghi chú, nội dung và ô ghim dùng đúng ngôn ngữ

BASE `d124b867c81ca0882a74721661fd8880e0451b8d`, PR735 đã triển khai.
Hai phiên Antigravity 3.8 Flash High độc lập trả đúng sáu thay đổi trong hai
tệp ứng dụng,17keys/51values VI/EN/ZH. Theo dõi duy nhất Issue689.

## Thay đổi đã kiểm

Hai phần thêm ghi chú/nội dung dùng tiêu đề, hướng dẫn và nút dễ hiểu.
Sáu tiêu đề/hướng dẫn danh sách đúng ngôn ngữ. Ô ghim ở tạo mới và chỉnh sửa
có nhãn riêng theo locale, không còn dùng chữ Việt mặc định trong EN/ZH.
Chỉ thêm checkboxLabel vào field; generic checkbox renderer giữ nguyên.

Giữ nguyên kiểu/tên/ID/value/checked/disabled của ô nhập, thứ tự các khối,
helper calls, badge calls, bốn state/capability gates, route/revision/constraints
và mọi nội dung khách. Không lọc media/studio/brand khi do khách tự viết.
Không sửa auth/API/Bot/engine/finance/ENV/schema/integration/CSS/motion.

## Bằng chứng

Candidate VM27BASE0PASS27RED→21PASS/6harnessfail; tham số mặc định trong
bộ đo đã biến undefined capability thànhtrue. Sửa riêng bộ đo,6affectedPASS,
không sửa app/worker hoặc lặp21ca đã đạt.

Permanent10BASE0PASS10RED. Sau áp worker, nhóm135=131PASS/4historical-adapter
fail. Adapter mới ban đầu kiểm nguồn lịch sử quá sớm; sửa nhánh chỉ nhận diện
khóa mới, chuyển nguyên nguồn cũ tới hash gate cũ,4affectedPASS. Hash cũ giữ.

Nhóm ảnh hưởng286=285PASS/1test mutation lịch sử fail: thêm checkboxLabel
làm nguyên khối field19 cũ không còn trong source, nên replacement thành
no-op. Chỉ chiếu đúng accepted new scope trước mutation và assert target1.
Thêm regression lịch sử marker-free giữ nguồn/guard; lượt affected2 có
regression1PASS và test cũ vẫn fail do tên gate từ chối khác. Regex hữu hạn
nhận đúng gate mới, affected cuối1PASS. Không đổi app, không skip/assertion
weaken, không nhận là một lượt135/286xanh. Giữ báo cáo lỗi gốc.

Python9PASS, syntax hai JS/py_compile app.py/diff check exit0. Freeze đo trên
từ điển VM thật trước projection;17keys giá trị/thứ tự giữ, thiếu/đổi/đảo/
khóa mới lạ bị từ chối. Whole-detail và dòng ghim có hash độc lập; old source
không bị ghi đè khi không thuộc phạm vi mới.

Review nguồn độc lập C0/I0/M0: hai app files khớp byte LF đúng sáu worker
substitutions.17 protected paths và toàn Python giữ BASE.

### Giao diện với server QA riêng

Baseline first VI375draft đã tái hiện chữ cũ trước apply. Green dùng ba
server riêng,VI/EN/ZH ×375 sáng/1440 tối ×draft/review/ready/archived:
24/24 unique states đạt,13ảnh; không chạy lặp ngôn ngữ đã đạt.
Actual href/list/detail/runs GET giữ ownership; root checkbox thay chọn
rồi trả lại, không submit.17keys và các form/field/lifecycle cũ đúng.

Không console/page/dialog/overflow/external requests/product writes.
Mỗi lượt đúng3fakeauthPOST, còn lạiGET/HEAD;15 hội thoại metadata QA/
6plans18scenes/schema/fingerprint/evidence giữ, owned Jobs đều về0.
Ảnh mẫu VI375 thêm ghi chú và EN1440 thêm nội dung đã được xem.

Nguồn app LF SHA256:

- portal.js `fbc74998f4777e4706972da81a42a2f0a8d18ffcfaa86ca43eccac289141d1da`
- i18n `b3130e575a44cd4fa7c3f4edb30fb41164afc39b616d8cbafb879963539cc835`

Bằng chứng cục bộ: `chat-context-section-permanent-red-nov14.log`,
`chat-context-section-green-prior-nov14.log`, `...affected4-nov14.log`,
`...affected-nov14.log`, `...affected2-nov14.log`,
`...affected1-final-nov14.log`, `chat-context-section-native-aggregate-nov14.json`.
Không công bố DB/token/tài khoản/API response/dữ liệu khách.

## Giao hàng và phần giữ mở

PR735 HEAD97ad8252, CI43609528286 hai nhóm đạt; merged/runtime d124b867,
deploy43610620888 đạt, tree85ad980b exact;4assets/services/health giữ.
Receipts Issue6896879820281 và PR7356879820732.
Đợt hiện tại còn cổng provenance/exactCI/merge/deploy/runtime/assets/receipt.

ContextCards, turnList, history, execution/toast/Doc other copy, toàn AX/
auth/device/Safari/signed production và M-FINAL01..06 vẫn mở, không ẩn
những chữ ngoài phiếu để báo hết. Route TTS chạy riêng: đã xác minh Web
generic không có receiver tương ứng ở listener Bot. Chưa tạo job/âm thanh
thật; cần liên kết receipt/job bền vững trước bản sửa. Không đổi quyền/ENV/
financial rules hoặc gọi provider để ép đạt.

`PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`, `PRODUCTION_DATA_WRITES=0`.
