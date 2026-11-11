# Hội viên: chữ cố định đúng ngôn ngữ, giữ nguyên dữ liệu thật

Tiếp theo PR #723 đã triển khai, hai phiếu độc lập chỉ trả đề xuất để nghiệm
thu trên nhánh riêng. Không sửa logic quyền lợi, ví, thanh toán hoặc API.

- [x] Xác định bốn đoạn chữ của hộp dẫn sang Bảng giá đang cố định tiếng Việt.
- [x] Xác định 14 khóa mô tả/trạng thái cố định còn giải thích triển khai.
- [x] Có kiểm tra RED 12 trạng thái renderer, giữ chữ kỹ thuật trong dữ liệu khách.
- [x] Nghiệm thu phiếu hộp dẫn Bảng giá: Việt/Anh/Trung, giữ đủ liên kết và markup.
- [x] Nghiệm thu phiếu 14 khóa mô tả: thông tin thiếu vẫn là thiếu, không bịa quyền lợi/gói.
- [x] Nghiệm thu nhãn gói công bố riêng của Hội viên, không đổi nhãn Bảng giá chung.
- [x] Kiểm tra native, snapshot lịch sử và hồi quy đúng phần chịu ảnh hưởng.
- [x] Bỏ riêng danh sách giải thích kỹ thuật tĩnh dưới nguyên tắc quyền lợi;
  giữ tiêu đề/nguyên tắc ngắn, mọi dữ liệu, trạng thái và hành động thật.
- [x] Sửa riêng độ tương phản chữ hộp dẫn Bảng giá theo token sẵn có;
  không đổi bố cục; nút chính được kiểm riêng ở mục kế tiếp.
- [x] Kiểm riêng nút Bảng giá trong hộp: cặp màu nền/chữ rõ và đo được ở
  trạng thái thường, rê chuột, focus; không đổi nút ở nơi khác hoặc motion.
- [ ] Phát hành đúng bản đạt, đối chiếu VPS và ghi receipt cùng Issue #689.

Giữ nguyên tên gói/trạng thái/ghi chú của khách, số dư 0, giá và danh mục thật,
các nút và trạng thái chờ xác minh. Không đổi nhãn danh mục dùng chung trên
Bảng giá; nếu cần nhãn mới chỉ dùng tại trang Hội viên. Không tạo ô trống hay
ẩn lỗi thật. Phạm vi này chưa bao gồm mọi câu của trang hoặc toàn ứng dụng.
