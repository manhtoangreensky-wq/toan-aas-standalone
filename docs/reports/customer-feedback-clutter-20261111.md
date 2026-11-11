# Thông báo rõ ràng và dọn nội dung thừa — 11/11/2026

Nguồn đối chiếu: `8371c43d147b0074c71c00dc4d3f7f9927894d5c`.
Theo dõi và bằng chứng giao hàng: Issue #689 của kho WebApp standalone.

## Phạm vi thay đổi

1. Trang Lập định dạng tham chiếu giữ thông báo ở hàng riêng ngoài vùng nội
   dung cuộn. Thông báo thật và nút khôi phục cùng nhìn thấy, không che nội dung
   hướng dẫn. Không có khoảng trống khi không có thông báo. Nội dung dài có thể
   cuộn bằng bàn phím; khi đổi trang, vùng thông báo trở lại vị trí ban đầu.
2. Trang Hội viên bỏ đúng một khối tĩnh báo danh mục cấp bậc không khả dụng và
   giải thích triển khai. Không bỏ trạng thái thiếu dữ liệu thật, quyền lợi,
   số dư hợp lệ, gói hay các liên kết thao tác.
3. Landing thay đúng câu giới thiệu quy trình ở Việt/Anh/Trung bằng hướng dẫn
   chọn công cụ, chuẩn bị, xem lại và lưu nội dung. Không đổi các bước hoặc
   hứa hẹn tạo ra kết quả cuối.

## Kiểm tra trong phạm vi

- 94 ca Node đạt, gồm 10 ca vòng đời bố cục, 12 ca Hội viên, 3 ca câu giới
  thiệu landing và các ca bảo vệ thao tác cũ.
- 12 ca Python đạt; có 2 cảnh báo thư viện cũ, không thay thư viện để giấu cảnh báo.
- 24 trạng thái thông báo đang hiện đạt: mỗi ngôn ngữ có trạng thái sau tạo,
  khôi phục, bàn phím, 390 sáng, 768 sáng/tối và 1440 sáng/tối. Không dùng việc
  bấm xuyên thông báo hoặc thông báo hết hạn làm bằng chứng không bị che.
- 12 lượt xem Hội viên/landing đạt ở Việt/Anh/Trung, 390/1440 sáng; 3 lượt
  chuyển khỏi trang tham chiếu trả lại đúng vùng thông báo. Không có lỗi trang,
  lỗi console, tràn ngang hay lần ghi kế hoạch trong nhóm chỉ đọc này.
- Mỗi ngôn ngữ dùng dữ liệu kiểm tra tách biệt: đúng một lần tạo kế hoạch và
  một lần lưu bị mất phản hồi. Các bản ghi gốc, bản sao bằng chứng và mã nguồn
  giữ nguyên trong quá trình chạy; không có lời gọi dịch vụ tạo nội dung,
  thay đổi ví hoặc ghi production. Không tạo lại dữ liệu khách.
- Lượt đầu đẩy thông báo ngoài màn hình; lượt hai chuyển chỗ che lên nội dung.
  Cả hai bị từ chối trước phát hành. Chỉ sửa trực tiếp đúng phần bố cục sau
  hai lượt đó; không thay cách tạo, lưu, thử lại, đăng nhập hoặc API.

Đợt này không đóng toàn bộ giao diện đa ngôn ngữ, thiết bị thật, Safari, phiên
khách trên production hoặc motion. Kiểm tra hiển thị và giao hàng tiếp tục ghi
trong phiên kiểm tra cùng ngày; merge, deploy và LIVE là các bằng chứng riêng.
