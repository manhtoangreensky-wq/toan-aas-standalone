# PDF sang ảnh và Word — giao diện đúng ngôn ngữ

TASK=DOCUMENT-CONVERT-CUSTOMER-COPY-20261119; FSM=VERIFY.
BASE_SHA=a589008be5d7be371789551ffc11e750db46270b.
TRACKER=Issue689/comment7006239694.
PR=NOT_CREATED; DEPLOY=NOT_STARTED_FOR_THIS_BATCH.

## Phần đã thay đổi

Hai trang PDF sang ảnh và PDF sang Word dùng nhãn, mô tả, hướng dẫn,
xác nhận và lịch sử đúng VI/EN/ZH. Bỏ intro, aside, notice, notes và cụm
nhãn kỹ thuật; không tạo khung thay thế trống. Giữ hero, biểu mẫu thật,
quyền, lịch sử, làm mới, chọn nguồn và liên kết kho tệp trong chân form.
Tên/mô tả HTML đầu và sau dựng giao diện dùng cùng nội dung đã duyệt.

Word vẫn chỉ chuyển chữ bôi chọn được; không nhận dạng chữ trong ảnh,
không hứa giữ hình, bảng, phông chữ hay bố cục. Giới hạn 20 MB/30 trang
không đổi. Không đổi API, xác thực, xử lý tệp, UUID, Bot, ví, PayOS,
provider, dữ liệu khách, ENV hay motion.

## Nguồn sửa được kiểm

Ba phiên CLI dùng đăng nhập hiện có, `gemini-3.8-flash-high`, chạy song song
chỉ trả JSON trong ba thư mục riêng. Root ghép tuần tự, không shared write.
Mỗi OLD và toàn MAP đã đối chiếu nguồn GitHub công khai HTTP200 trước gửi.
Không gửi test, fixture, API/login response, secret hoặc dữ liệu khách/tài chính.

| Phiếu R1 | Conversation đã kiểm |
|---|---|
| Hai trường nguồn |4016959a-13b1-4e7f-8289-56378a80fb0c|
| Trang PDF sang ảnh và metadata |523ff7c6-8df9-4a1b-8aae-3ac0078bb922|
| Trang PDF sang Word và metadata |f5e057f5-c42e-4072-8794-27a4fd1da479|

Ba kết quả đúng schema và từng giá trị ngay lượt đầu, 0 lỗi worker,
không Root takeover ứng dụng. Đúng 13 phép thay trong 3 tệp ứng dụng;
28 khóa mới, 148/151 nguồn bảo vệ. Fixture RAW SHA256:
`e162e15e4ddff0899dcf69bee7134576c7fac7a2fb35fb1857e555d1e70c6b63`.

## Bằng chứng cục bộ

- Physical BASE: 5 đạt/11 RED, 5272.8224 ms. Candidate: 16 đạt/0 lỗi,
  13507.5012 ms. Bản portable + nguồn: 32 đạt/0 lỗi, 12875.433 ms.
- HTMLResponse đầu: BASE 1 đạt/6 RED trong 2.82s → 7 đạt trong 2.40s.
  Nhóm Python liên quan sau đó 32 đạt/3 lỗi trong 4.81s; ba lỗi được
  chạy đúng lát trên Git BASE: cùng 3 lỗi/10 bỏ chọn trong 1.36s.
  Hai lỗi do lệnh Node `-e` vượt giới hạn Windows; một kỳ vọng chữ cũ
  ở thẻ bàn giao. Không đổi ứng dụng để ép các lỗi nền này qua.
- Python collector cũ dừng ở cùng phép inverse trên BASE lẫn candidate.
  Bổ sung biên test hữu hạn DCC → Edit → PDF-utilities rồi giữ nguyên
  assertion an toàn trước đó: 10 ca inverse mới + 29 ca gốc = 39 đạt,
  4.13s. Lỗi chuẩn bị BASE đầu tiên thiếu đường import được sửa ở
  script QA tạm, không tính worker hoặc ứng dụng.
- Native BASE: 24 cấu hình/trang, 48 PNG/trang; GREEN tương tự.
  Đủ 96 cấu hình/192 PNG cho hai phase, PNG parse/CRC/kích thước/hash;
  không chạy native lại khi tổng hợp. Mỗi nhóm 42 tiến trình sở hữu
  đã về 0. BASE ảnh 63.454s, Word 63.143s; GREEN ảnh 65.100s,
  Word 65.429s. Startup/group/action/cleanup giữ 60/180/10/5.
- Bốn nhóm giữ source151/binding/code/core/schema/auth-audit; 12 hàng
  metadata/nhóm, không blob/output. Chỉ có ba đăng ký và ba đăng nhập
  QA hợp lệ; không ghi sản phẩm, egress, provider, ví hoặc lỗi console.
- GREEN: mỗi cấu hình đủ form, nguồn, Tab/Shift+Tab và một liên kết kho
  tệp focusable; 0 intro/aside/notice/notes/state-meta. Tên khách giả
  giữ nguyên/thoát ký tự, không bị dịch. Root xem ảnh VI320 tối và
  EN768 ngang sáng trước/sau; không suy rằng mọi điểm màu đã đạt.

BASE có 264 mẫu paint UNKNOWN, GREEN 288; giữ toàn bộ witness và giới hạn.
Không dùng `0 automatic findings` để nhận WCAG/contrast toàn ứng dụng.
Current renderer luôn nhận nguyên bundle vật lý; inverse chỉ ở biên QA
lịch sử, ghim fixture và kiểm các sai lệch/mất/trùng/sai thứ tự.
CI thêm đúng hai lệnh chạy nhóm mới, không đổi quyền/trigger/deps/timeout.

## Phần còn phải chốt

Affected Node một lượt 79 tệp: 1.691 đạt/14 lỗi trong 242926.9242 ms.
Lỗi ở các biên so nguồn lịch sử chưa stage phép thay mới; không đổi
ứng dụng, không tính Antigravity sai. Riêng PDF-utilities physical dừng
trước đăng ký vì catalog mới chen giữa anchor cũ, được chẩn đoán một lần
đúng tệp. Giữ 1.691 ca đạt; chỉ sửa comparator hữu hạn và chạy lại lát
thất bại/chưa thực thi, không chạy lại cả nhóm.

Đã sửa đúng mười biên QA lịch sử và marker-free OLD passthrough trong
helper mới, giữ nguyên mọi assertion/golden/negative. Chạy lại đúng
10 tên lỗi: 10/10 đạt, 6873.2822 ms; bốn tệp trước đó chưa đăng ký ca:
132/132 đạt, 30436.386 ms. Ca mới bảo vệ lỗi OLD: 1/1 đạt, 861.3317 ms.
Không chạy lại 1.691 ca đã đạt hoặc native/application. Tổng duy nhất
của affected đã hoàn tất là 1.833 ca đạt; nhóm mới có 33 ca duy nhất
(32 đã chạy trước + 1 bổ sung), không cộng trùng physical tạm.
Metadata Tester 2 đạt/31 bỏ chọn trong 0.66s; sáu DCC case, 1767 dòng/
183986 byte LF, SHA256 `6a0fbaa59c1439dc62fac6e5d71b9407704507941c42c67e22d911bfc5aec302`.
Compile app.py/pages thật, hai bundle JS syntax và YAML workflow đều đạt.

Review độc lập C0/I0/M0, Root đọc đầy đủ; SHA256
`64befd51081f856063477d26be8aace38026f7f4b721004adf813820c52aca44`.
Prepush READY: manifest 39 tệp, 0 tệp khớp mẫu secret, source151 và
hai lệnh CI đúng phạm vi. Currentops/crosswalk/sáu case/Tester hoàn tất.
Một PR/exact HEAD CI, merge/cây nguồn/deploy/VPS/assets/receipt được
ghi tiếp bằng chứng giao nhận riêng; không dừng ở trạng thái merge.
Giao diện production có đăng nhập và tệp chuyển đổi cuối NOT_TESTED.
Goal toàn ứng dụng ACTIVE/incomplete; motion M-FINAL-01..06 cuối.
Không dùng đợt này nhận xử lý xong các mục contrast/recovery/auth/device/
Safari/stale-response hoặc đầu ra sản phẩm còn mở.
