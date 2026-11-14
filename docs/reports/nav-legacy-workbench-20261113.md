# Nhãn nhóm đúng ngôn ngữ và bỏ khối kết quả điền sẵn

BASE: `c4da5f4a90a4ca37c46b66220c81928b806a4f2a`, bản PR #725 đã triển khai.
Tracker duy nhất: Issue #689; amendment `6844353007`.

## Thay đổi giới hạn

Thêm một alias cố định `AI Studio` vào bản đồ nhãn, dùng khóa dịch
`shellNav.aiStudios` đã có. Việt hiện “Xưởng sáng tạo AI”, Anh/Trung theo
khóa hiện có; manifest, dictionary và tên/dữ liệu khách không bị sửa.

Helper `renderInteractiveFeatureWorkbench(page, context)` nay trả chuỗi rỗng,
giữ nguyên tên/chữ ký và cả ba consumers. Bỏ ba panel video/tài liệu/nội dung
với sáu nút chỉ gọi alert, giá/sẵn sàng/phần cứng/độ chính xác tự ghi và kết
quả viết sẵn. Không dựng panel, nút, thông báo hoặc ô thay thế. Ba link
`/studio` lặp bên trong panel được bỏ cùng panel; điều hướng ứng dụng và
mọi form/result/action bên ngoài giữ nguyên.

Helper cũ không dùng context, không có form/action/API thực sự. Không sửa
engine, provider, ví/giá thật, auth/API/backend, ENV/schema, CSP hoặc motion.
Image/Music vốn rỗng vẫn rỗng; không biến trạng thái được chặn thành sẵn sàng.
Mã mới của hai thay đổi đều từ đề xuất worker, không có tiếp quản tự viết
logic. Ngữ cảnh OLD bị thiếu đúng một ký tự ghép emoji được đối chiếu lại
nguồn gốc; NEW giữ nguyên từng byte.

## Bằng chứng local

- Alias: 27 ca, baseline3đạt/24lỗi →27đạt.
- Helper/renderer: 138 ca, baseline62đạt/76lỗi →138đạt. Có 18 đầu vào helper
  và 20 route ×3 ngôn ngữ ×2 trạng thái; toàn bộ dữ liệu, HTML và controls
  ngoài đúng panel cũ giữ nguyên.
- Nhóm hồi quy421/421 Node đạt, đã gồm các nhóm trên và Image/Music; không
  cộng các lần chạy chồng lấn. Cú pháp JS và compile app/page đạt.
- 30 ca Python đạt; một assertion CSS-tail cũ lỗi y hệt BASE, vì tìm ký tự
  `#` trên toàn phần cuối stylesheet. Không sửa theme/motion hoặc bỏ ca đó.
- Một kiểm tra Music cũ đòi nguyên văn nhánh/comment được thay bằng thực thi
  helper thật ở hai route và nhóm Music, giữ hai chốt caller. Không đổi Music.
- So nguồn phục hồi đúng hai thay đổi khớp toàn bộ bundle BASE; ba consumers
  và18tệp bảo vệ khác giữ nguyên. Rà soát độc lập không phát hiện blocker.

Native đúng entry của nhóm ảnh/tài liệu/nội dung ở390/1440, Việt/Anh/Trung,
sáng:18lượt xem/18click thật sang nhóm video,0panel giả/console/pageerror/
tràn ngang. Lượt trước khi bỏ helper có36lỗi inline-handler bị CSP chặn;
lượt cuối0, CSP/logs không bị nới/ẩn. Không provider/ghi sản phẩm/ví/production,
bản sao QA6kế hoạch/18cảnh/lịch sử và bằng chứng gốc giữ nguyên;21tiến trình
sở hữu dọn về0. Đăng nhập QA tạo phiên riêng, không khẳng định byte DB sao chép
không đổi sau đăng nhập.

## Những điều không suy rộng

`/features` root dùng bundle danh mục nhẹ riêng, không dùng renderer chung;
ba ca renderer root cũ không phải bằng chứng UI root production. Native dùng
các trang nhóm thật. Các lượt đầu dừng do bộ kiểm tra chọn sai entry hoặc so
chữ DOM với chữ CSS viết hoa; chỉ sửa bộ kiểm tra, không sửa thêm ứng dụng.

Phiếu bỏ status-grid Hội viên được rút vì CSS đã ẩn sẵn, không chấm lỗi worker,
không áp dụng đề xuất đó. Không đóng locale/clutter toàn app hoặc khả năng
nhìn thấy lỗi thật bằng một phép kiểm tra source.

CI đúng HEAD, merge/deploy đúng SHA, runtime/services/assets và receipt ở cùng
Issue #689/PR là các cổng riêng sau local. Thiết bị/Safari, signed production,
provider output, auth/AX toàn app và M-FINAL-01..06 vẫn mở; motion vẫn cuối.
