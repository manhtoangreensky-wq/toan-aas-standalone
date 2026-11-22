# Trước phát hành — nhãn biểu mẫu thiết kế ảnh

Ứng viên trên BASE `05b7ba761bd35cf4da498443db9046ed59429d90` chỉ dịch
nhãn và gợi ý cố định của bộ trường tạo/chỉnh sửa. Hai record worker
được đối chiếu với toàn nguồn; 18 khóa/54 giá trị. Các giới hạn, dữ liệu,
quyền và thao tác giữ nguyên.

11 kiểm tra mục tiêu, 12 màn cô lập và sáu đối chiếu renderer đã đạt.
147 Python đạt; hồi quy 165 tệp có sáu lỗi helper, sau sửa và chạy lại
hai tệp 47/47 đạt, đủ sáu case từng lỗi. Tài liệu vận hành, đối chiếu chức năng và phiên
Tester được cập nhật; dùng Issue689 hiện hữu khi ghi báo cáo phát hành.

Các kiểm tra lịch sử chỉ đảo đúng record đã duyệt, giữ các byte ngoài
phạm vi và kiểm tra cũ. Cổng CI/merge/deploy/runtime/signed UI được xác
minh riêng. Lựa chọn tỷ lệ và những phần chữ khác chưa được nhận hoàn tất.
