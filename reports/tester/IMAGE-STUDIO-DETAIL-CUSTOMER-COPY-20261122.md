# Kết quả cục bộ — chi tiết thiết kế ảnh

BASE `f6aee803a72a80bf70cd0a4ce786858f94f9d7cc`; 22 record từ sáu
phiếu Antigravity: 21 dòng dịch và một quy tắc màu. Nguồn vật lý bằng
BASE cộng đúng record; helper lịch sử giữ phần ngoài phạm vi.

24 trạng thái renderer, 63 giá trị dịch và nội dung khách giả đạt.
48 màn/96 mẫu: sáng2,02115→5,79710:1; tối tối thiểu5,52248:1,
màu và hình học giữ. Zero lỗi trang/mạng/tràn, nhập và chọn tỷ lệ đạt.
30 Node mục tiêu và 237 Python đạt sau sửa hai câu.
Không có provider/ví.

Hồi quy167tệp/5151ca:5145PASS/6FAIL tại `legacy-decorative-workbench.test.mjs`
do mô tả thẻ ảnh được thay có chủ ý. Giữ so sánh toàn bộ markup và controls;
đối chiếu đúng một câu được duyệt, retest138/138PASS. Không chạy lại5145ca
đã đạt hoặc nhận một lượt fullPASS mới.

Review phát hiện câu cũ của spec suy đoán nguyên nhân khi không có dữ liệu;
hai dòng R2 dùng câu trung tính, thêm18ca theo trạng thái/locale/route.
Lỗi chưa hiển thị chờ riêng vẫn mở ở Issue689/comment7078219437.
CI, merge, deploy và signed production UI là
các cổng riêng, chưa nhận từ kiểm tra cục bộ.
