# Hội thoại và lịch sử Tài liệu — phần chữ có quyền sử dụng

BASE=`d14c6f0e1e0ecbef2dbba53b60cec48db67b2763`; tracker Issue689,
contract6871799821. PR727 đã triển khai, receipt6871791490/6871791756;
postmerge CI43556634274 cũng đạt cả hai jobs.

## Hành vi hiện tại trong phạm vi

19 câu/nhãn cố định ở phần mở đầu, tạo/lọc/danh sách rỗng của Hội thoại,
8 nhãn bộ lọc và 5 thông báo tải/lỗi/thử lại của Tài liệu dùng đúng VI/EN/ZH.
32 khóa mới/96 giá trị được thêm trước kiểm tra khóa và khóa từ điển;
mọi khóa/giá trị cũ giữ nguyên. Lời nhắc tạo/lọc dùng từ dễ hiểu, không mất
các loại dữ liệu không được nhập. Lưu nội dung thủ công không bị mô tả thành
câu trả lời tự động hoặc việc trừ Xu.

Không đổi dữ liệu khách, số đếm, quyền, thuộc tính điều khiển, lựa chọn gửi đi,
hành động, URL, bản nháp, phân trang hoặc nguồn dữ liệu. Sáu tag đã ẩn của
Tài liệu giữ nguyên; không giao xóa dựa vào chữ chỉ có trong nguồn. Nhánh sẵn
sàng của Tài liệu và chi tiết Hội thoại giữ nguyên toàn bộ.

Mã ứng dụng là đúng chín thay đổi trong ba đề xuất Antigravity:
authoringR2, filterR1, document-readR1. So dựng lại từ BASE bằng các OLD/NEW
của worker khớp toàn bộ hai bundle sau chuẩn hóa LF; không có sửa logic trực
tiếp. AuthoringR1 bị giữ lại vì thiếu cấm nội dung tệp ở VI và còn chữ khó hiểu;
R2 giữ cùng phiếu/phiên. Không gọi lại hai phần không bị lỗi.

## Kiểm tra

- 52 ca ban đầu:12PASS/40RED; sau áp dụng52PASS. Thêm ba ca chống adapter che
  lỗi thành55 ca mới. Chạy cùng72 ca root-access trước:127/127PASS.
- 186 ca chịu ảnh hưởng (nhãn/helper cũ, hội viên, landing, ranh giới Chat,
  điều khiển tài liệu) đạt. 288 ca catalog/planner lịch sử đạt. Các nhóm có
  thể chồng lấn, không cộng thành tổng duy nhất.
- Adapter chỉ nhận đúng32 khóa đã duyệt và hash giá trị/thứ tự theo từng
  locale; thay bất kỳ giá trị nào bị từ chối, khóa lạ/tên khách vẫn giữ.
  Hash/golden cũ không đổi. Bộ so HTML chỉ phục hồi vị trí chữ hữu hạn.
- 45PythonPASS/1 lỗi CSS-tail nguyên vẹn: ca DocumentBoard tìm gradient trong
  toàn bộ phần CSS sau marker. CSS giống BASE, cùng lỗi đã ghi ở các đợt trước;
  không sửa CSS/motion hoặc làm yếu điều kiện đó. Python source/UI syntax đạt.
- Metadata32PASS/1 lỗi chmod600 trên Windows đã có: test và script đồng bộ
  không đổi so BASE; không sửa quyền hoặc test để che. File case mới đo đúng
  1162dòng/131456byte, SHA2060492347f6abebca401bac2464ec35f24941644e040abaef56ca368d1290b7;
  metadata giữ các trường remote/P0/48case/safety lịch sử. CI Linux là cổng riêng.

Native có48 lượt xem hợp lệ:3locale×390/1440×sáng/tối×Hội thoại hoặc ba trạng
thái Tài liệu.12 lần chờ→đọc lỗi có kiểm soát→nút thử lại thực nhận GET200;
24 thao tác chọn/gõ/áp dụng lọc thực nhận danh sách từ API QA. Các lần đọc lỗi
có48 request bị chủ động ngắt do cơ chế thử đọc lại;48 thông báo mạng tương ứng
được ghi riêng, không giấu lỗi trang khác. Không lỗi trang/tràn ngang/lỗi console
không giải thích trong48 lượt được nhận.

Giữ32 lượt VI/EN đã xong trong run đầu, nơi đầu pha ZH chạm giới hạn đọc thật:
10 thông báo429 được giữ là lỗi của pha chưa nhận, log chứng minh chúng chỉ
xuất hiện sau khi bắt đầu ZH. Tách server mới hoàn tất16 lượt ZH, không đổi/tắt
giới hạn và không chạy lại các lượt VI/EN. Aggregate xác minh48 tổ hợp duy nhất,
cùng hash nguồn, ảnh đầy đủ,12 lần thử lại/24 lần lọc. Không báo cả run đầu PASS.

Hai nguồn bằng chứng cuối giữ6 kế hoạch/18 cảnh/lịch sử và bằng chứng gốc,
nguồn không đổi;22 và14 tiến trình sở hữu đều dọn về0. Chỉ cấu hình servercon
QA, không sửa `.env`/máy/production.0provider/ví/ghi sản phẩm/production.

## Giới hạn và việc tiếp

Chưa đóng toàn Hội thoại/Tài liệu: các trường nhập/chi tiết, thẻ có dữ liệu,
phân trang, lời báo sau thao tác và một số heading còn ngoài phạm vi. Ảnh đầu
Hội thoại còn ba thống kê0 chiếm chiều cao; giữ comparator số liệu đợt này,
giao phần thu gọn riêng, không lén đổi cấu trúc trong phiếu dịch chữ.
Toàn route/AX/auth/device/Safari/signed production và motion cuối vẫn mở.

Đường Web–Bot chạy song song: audit TTS và1PASS/3RED trong DB tạm đã khoanh
lỗi hoàn tất trước âm thanh. Đã giao phiếu sửa riêng, chưa áp dụng engine code
vào nhánh UI. Không suy actual Bot/provider output từ transport tổng hợp.
CIexactHEAD/merge/deploy/runtime/assets/receipt là cổng riêng sau local.
