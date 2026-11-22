# Trước phát hành — chờ và bản đang sửa của chi tiết ảnh

BASE `e177ce5f5791fd22e517d95706331051223e0ccb`; Issue #689.
Khi mở bảng khác, giao diện nay có trạng thái chờ rõ ràng. Khi vẽ lại cùng
bảng và cùng phiên bản, các biểu mẫu giữ riêng nội dung đang gõ. Phiên,
revision, quyền, nhận dạng trùng và lựa chọn vô hiệu được kiểm tra trước khi
khôi phục. Chỉ ba tệp ứng dụng thay đổi; không có backend, ENV, provider,
ví, Bot, PayOS hoặc dữ liệu production.

Đã cập nhật vận hành, đối chiếu chức năng gốc, case và phiên Tester ISDL.
Node mục tiêu 40, nhóm riêng 16, Python màu 90 đạt; Chrome 20 tình huống và
36 màn tĩnh đạt; rà soát độc lập không có lỗi chặn mới. Hồi quy cuối
170 tệp/5.186 ca đạt, 0 lỗi/0 bỏ qua; Python bổ sung 136+4 đạt.
Dấu vết nguồn cần chốt trước push. Giao diện sau đăng nhập production chưa được
quan sát; các trường hợp bản nháp qua lỗi đọc/đổi revision/rời trang còn mở.

CI đầu `45042526505` đã qua nhóm JavaScript nhưng dừng sau 110 kiểm tra
Python tại `test_closed_mobile_sidebar_is_removed_from_keyboard_and_accessibility_navigation`.
Nguyên nhân là helper kiểm thử cắt đến lần gán `main.innerHTML` đầu tiên,
nay nằm trong nhánh giữ bản nháp nên cắt dở một khối. Hai bài Node về
header/sidebar cùng gặp lỗi cú pháp khi lấy đoạn mã; ứng dụng không lỗi
cú pháp. Đổi điểm kết thúc về câu cập nhật phiên header, giữ toàn bộ
assertion. RED 6/6→GREEN 6/6; nhóm điều hướng Python 15/15 đạt.
Không thay mã ứng dụng hoặc chạy lại các ca hồi quy đã đạt ở máy local.
