# Hội viên: ngôn ngữ rõ ràng và khả năng đọc

BASE: `e2afca85d96ed6a19c941924e5344ea40869cfac`, bản đã triển khai từ PR #723.
Theo dõi duy nhất: Issue #689, kho WebApp standalone.

## Phạm vi khóa

- Bốn đoạn chữ của hộp dẫn Bảng giá theo Việt/Anh/Trung; không lộ đường dẫn
  kỹ thuật trong nhãn, giữ nguyên hai liên kết và nút thật.
- 14 khóa mô tả/trạng thái Hội viên dùng ngôn ngữ dành cho khách. Thiếu thông
  tin gói/trạng thái không bị diễn giải thành khẳng định khách không có gói.
- Nhãn gói công bố riêng tại Hội viên; không đổi nhãn dùng chung ở Bảng giá.
- Bỏ đúng danh sách giải thích triển khai tĩnh dưới phần nguyên tắc; không
  bỏ nguyên tắc ngắn, trạng thái thiếu dữ liệu, lỗi thật, quyền lợi hoặc nút.
- Màu chữ và nút riêng trong hộp dẫn Bảng giá, không thay layout, nút nơi khác
  hoặc motion. Màu phải được đo ở cả sáng/tối và thường/rê chuột/focus.

Không đổi ví/thanh toán, giá, quy tắc quyền lợi, API/auth, dữ liệu khách, Bot,
provider, ENV hoặc schema. Tên/trạng thái gói và ghi chú khách có chứa chữ kỹ
thuật vẫn được giữ nguyên; không áp dụng bộ lọc dịch/xóa toàn trang.

## Bằng chứng và cổng chưa hoàn tất

12 ca renderer thật đạt với thiếu ví, số dư 0/thông tin gói thiếu, VIP và có
danh mục được duyệt ở ba ngôn ngữ. So sánh hữu hạn đúng chữ được duyệt, toàn
bộ controls/HTML ngoài phạm vi và dữ liệu/raw input giữ nguyên. Adapter lịch
sử chỉ nhận đúng 19 khóa đã duyệt, vẫn từ chối giá trị bị sửa ngoài phạm vi.
Nhóm hồi quy chịu ảnh hưởng 556/556 ca Node đạt; 5 ca Python/metadata đạt.

Kiểm tra trình duyệt trước phát hành phát hiện chữ sáng có tỷ lệ thấp nhất
1,0796:1; sửa chữ sáng đạt nhưng liên kết/nút tối còn dưới 4,5:1. Các lượt này
bị đánh dấu không đạt, không dùng việc không có lỗi console thay bằng chứng
khả năng đọc. Bản sửa tiếp theo đạt 12 giao diện Việt/Anh/Trung, 390/1440,
sáng/tối. Đo 240 mẫu ở thường, hover/focus của cả nút và liên kết: thấp nhất
5,216649621048673:1, không mẫu không xác định. Ba lượt rời trang giữ đúng vùng
thông báo; không lỗi trang/console/tràn ngang, không ghi kế hoạch và DB QA cũ
giữ nguyên. Toàn bộ tiến trình QA sở hữu đã dừng.

Mã ứng dụng chỉ do các phiếu trả kết quả trong phạm vi: 14 khóa dịch (40 giá trị
thực sự đổi, 2 giá trị đã phù hợp giữ nguyên), 15 giá trị mới của năm khóa,
bốn text node, một nhãn hiển thị, một phép bỏ render ghi chú và CSS callout
riêng. Không tiếp quản tự viết mã ứng dụng trong nhóm này. Sau thay đổi màu
cuối chỉ chạy lại 67 ca chịu ảnh hưởng, giữ bằng chứng 556 ca trước đó; không
cộng hai nhóm chồng lấn thành số ca duy nhất lớn hơn.

Nhóm local đã đạt; CI đúng HEAD, merge, deploy và runtime/assets là các cổng
giao hàng kế tiếp, chưa suy ra từ kết quả local.

Đợt này không đóng locale/clutter toàn app. Nhãn họ gói mặc định và nội dung
thay thế cho ghi chú thiếu có nguồn riêng, vẫn cần kiểm tra bảo toàn dữ liệu;
không tự sửa bộ chuẩn hóa dùng chung. Thiết bị thật, Safari, phiên production
sau đăng nhập, đầu ra provider và motion vẫn có cổng riêng.
