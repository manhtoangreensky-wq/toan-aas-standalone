# Làm mới tài liệu đúng kết quả và chữ Hội thoại dễ đọc

BASE `3477d0d83cb88d96941f5790f642cceb285463d9`, sau PR #730.
Một sổ theo dõi: Issue #689; contract `6873366957`, phụ lục R2 `6875462236`.
Đợt này chỉ thay ba đoạn ứng dụng từ hai đề xuất Antigravity, không trộn
với các phiếu Hội thoại hoặc đường tạo giọng đang làm song song.

## Kết quả theo phạm vi

- Làm mới chỉ báo thành công khi lượt đọc hiện tại trả mảng và trạng thái
  thực là `ready`. Danh sách rỗng hợp lệ vẫn thành công; đọc lỗi không thành công.
- Thay đổi trang, phiên, yêu cầu mới hơn hoặc đăng xuất khiến phản hồi cũ
  không hiện thông báo. Giữ nguyên chốt trang/quyền, trình đọc, đường yêu cầu
  và cách lấy dữ liệu: bảng đọc lịch sử; trang công cụ đọc thêm kho tệp.
- Bốn thông báo theo VI/EN/ZH, 12 giá trị mới trước kiểm tra/đóng băng từ điển.
  Không đổi các giá trị cũ hoặc dịch tên/nội dung khách.
- Chỉ màu nhãn trường trong phần Hội thoại sáng dùng màu chữ chính có sẵn.
  Không thêm màu, không đổi phông/bố cục/điều khiển/tối/chuyển động.

Antigravity refresh R1 được giao mô tả sai rằng đọc lỗi trả `null`; trình đọc
thật trả `[]` và trạng thái `failed`. R1 array-only đạt30/36, sai6 ca đọc lỗi.
R2 cùng phiên sửa tiêu chí thành mảng **và** `ready`, đạt36/36 trong kiểm tra
ứng viên. Đây là SPEC SAI của điều phối, không tính lỗi mã của worker và
không dùng làm quyền tự sửa ứng dụng. Bản áp dụng là nguyên văn R2.

## Bằng chứng đã đo

43 test thường trực RED trước áp dụng, sau áp dụng43 PASS:42 ca chạy mã xử lý
và trình đọc thật, một cổng phạm vi CSS. Nhóm224 ca chịu ảnh hưởng đạt, gồm
ba ca adapter mới chống giá trị/khóa/thứ tự không được duyệt. Nhóm41 ca
hồi quy catalog/account/video đạt. Các nhóm được ghi riêng, không suy ra
tổng phủ toàn ứng dụng.

Python:45 PASS,1 FAIL đã tồn tại ở BASE trong
`test_document_board_is_explicitly_private_in_pwa_and_app_first_responsive`.
Test đó xét `linear-gradient` trên toàn đuôi CSS; BASE cũng có đúng một lần.
`portal.css` giữ nguyên, không sửa test/motion để che lỗi.
Ba ca locale/profile/auth đạt riêng. Lượt đầu trong phiên giới hạn chưa
kết thúc ở auth; đã dừng đúng tiến trình đó, chỉ chạy lại nhóm chưa kết thúc.
`node --check` hai bundle và `python -m py_compile app.py` exit0.
Metadata Tester:32 PASS/1 lỗi quyền tệp POSIX đã biết trên Windows
(`test_owner_authorized_write_uses_private_temp_file_and_cleans_it`).
Không đổi script hoặc assertion để che khác biệt; Linux CI giữ bài kiểm tra.
Nguồn case đo1199 dòng/134569 byte LF,
SHA256 `d483242e65dead6ce17c321b7b46e9264bf11b531c9e1d2a3da8433c1b7db746`.

So sánh nguyên văn với đề xuất worker:3/3 thay đổi đúng;16 đường ứng dụng
khóa giữ BASE, gồm auth/API/bridge/DB/ví/TTS/video/Document loader/shell/
portal.js/CSS/chuyển động/cache riêng tư. Review nguồn độc lập C0/I0/M0,
không chạy lặp suite bởi người review.

### Màn hình thực ở localhost cô lập

Hội thoại:6 lượt375 dọc,812×375 ngang,1440 máy tính, sáng/tối,66 nhãn.
Tương phản nhỏ nhất sáng từ1.2653297845 lên8.6438517935:1;
tối11.5279743059:1 giữ nguyên. Không tràn ngang/lỗi trang/console.
Detail cùng selector và renderer tám trường đã được kiểm, nhưng chưa có
lượt signed-native detail riêng: không dùng root để khẳng định toàn bộ AX.

Tài liệu:12 trạng thái, VI/EN/ZH × bảng375 sáng/công cụ1440 tối × lỗi/phục hồi.
Sáu lần đọc lỗi có thông báo `alert` đúng ngôn ngữ; sáu lần đọc lại GET200
mới có thông báo `status` đã cập nhật.48 lượt GET lịch sử/kho tệp được ghi,
24 lần abort chủ động và24 lỗi mạng tương ứng được tách riêng;0 lỗi trang/
console bất ngờ/tràn ngang. Không trả phản hồi thành công giả.

Hai lượt giữ nguyên6 kế hoạch/18 cảnh và bằng chứng gốc trong bản sao QA;
13 tiến trình Hội thoại và20 tiến trình Tài liệu do từng lượt sở hữu đều về0.
Không ghi sản phẩm/production, không gọi provider hoặc thay tiền. Lượt đầu
Chat QA trong phiên giới hạn chưa mở server trong60s,0 lượt xem; lượt
được phép sau đó ready3.267s và6/6 đạt. Giữ cả bằng chứng chưa đạt, không
tính lỗi môi trường là lỗi Antigravity.

Bằng chứng cục bộ:

- `document-feedback-contrast-red-nov14.log`:43 RED trước áp dụng.
- `document-refresh-scope-nov14.json`:3 worker changes/16 protected paths.
- `chat-label-contrast-native-nov14-accepted-d/chat-label-contrast-native-summary.json`.
- `document-refresh-native-nov14-accepted-a/document-refresh-native-summary.json`.

Các tệp trên nằm trong thư mục bằng chứng của phiên, không công bố dữ liệu
đăng nhập/DB/API khách lên GitHub. Báo cáo này chỉ công bố số đo tổng hợp.

## Giao hàng và phần còn mở

Nơi kiểm thử có sẵn: mẫu case/lỗi, đủ12/12 nhãn đã đối chiếu GitHub ngày
14/11/2026, phiên kiểm thử riêng và nguồn case duy nhất trong repo.
Không tạo issue hoặc bảng theo dõi cạnh tranh. Provenance, exact-head CI,
merge, deploy và SHA/runtime/assets sẽ có receipt riêng trên Issue #689/PR.

Chưa coi toàn ứng dụng hết thuật ngữ: thẻ/chi tiết/khối giải thích khác của
Hội thoại, các công cụ/lịch sử/thông báo Tài liệu ngoài phiếu, helper text
nhạt, toàn AX/auth/device/Safari/signed-production và motion cuối vẫn mở.
Không xóa chốt an toàn hay giả đầu ra thật để giao diện trông sẵn sàng.

Ba phiên Antigravity độc lập được giao tiếp: hai phiếu chữ/khối dư Hội thoại
và một phiếu đọc đường Web–TTS. Kiểm tra nguồn thấy trạng thái trang `ready`
có thể chỉ là được soạn bản nháp; dedicated confirm còn cần biên nhận chuẩn
bị và âm thanh thực. Chưa quan sát bytes/phát/giải mã âm thanh từ Web–Bot.
Không đưa Bot/engine/provider/ví/ENV vào bản sửa UI này.

`PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`, `LIVE_OUTPUT=NOT_OBSERVED`.
Toàn goal vẫn đang mở; merge/deploy không thay bằng chứng đầu ra thực.
