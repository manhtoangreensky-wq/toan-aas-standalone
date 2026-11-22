# Chi tiết ảnh — trạng thái chờ và giữ nội dung cùng phiên bản

BASE `e177ce5f5791fd22e517d95706331051223e0ccb`; Issue #689, contract
`7079193789`, phát hiện bản nháp `7079533020`.

Phạm vi ứng dụng: `static/portal/integration.js`, `static/portal/portal.js`,
`static/portal/portal-theme.css`. Không sửa Bot, route-engine, provider, ví,
PayOS, dữ liệu, quyền hay cơ chế xác thực. Bộ so sánh giữ nguyên nguồn ngoài
ba tệp và phần ngoài bốn record đã định.

1. Khi Back/Forward mở một chi tiết Image hợp lệ, lần vẽ đầu tiên phải xóa
   projection chi tiết trước và hiện trạng thái chờ có chữ VI/EN/ZH,
   `role=status`, `aria-live=polite`, `aria-busy=true`; kiểm quyền có trước.
2. Giữ bốn nhóm biểu mẫu độc lập khi vẽ lại cùng đường dẫn, cùng phiên đăng
   nhập và cùng phiên bản: sửa bảng, tạo phương án, sửa từng phương án.
   Nhận dạng gồm action/route/ID/revision; nhận dạng trùng thì không khôi phục.
3. Chỉ giữ tên trường trong allowlist, trường đang bật và lựa chọn còn có.
   Không lưu tệp/mật khẩu/trường ẩn, không tạo lựa chọn hoặc thay revision.
   Chụp và khôi phục trong một lần vẽ; kiểm lại phiên/route/mount hiện hành.
4. Trang khác không chạy cơ chế bản nháp mới. Màu chỉ đổi ở tiêu đề trạng
   thái chờ chi tiết sáng; tối và bố cục giữ nguyên.

Bằng chứng: BASE điều hướng 12 ca, mất nội dung 8/8; sau sửa Chrome 20 ca,
trạng thái tĩnh 36 màn, đo sáng 1,046→12,352:1 và tối 13,903:1; Node mục
tiêu 40/40, Python 90/90. Hồi quy cuối 170 tệp/5.186 ca đạt, 0 lỗi/0 bỏ qua;
Python lịch sử 136/136, shell 4/4. Phát hành cần chốt riêng.

Worker R1 bị lỗi trộn mã giả trùng, R2 thêm normalization ở trang không liên
quan; Codex tiếp quản đúng bản nháp sau hai vòng, giữ mã trạng thái/màu của
worker. Không suy ra thành công production từ báo cáo worker hoặc HTTP 200.

Việc còn mở: lỗi đọc khiến biểu mẫu biến mất, đổi revision hoặc rời trang
vẫn có thể mất nội dung; chưa có cơ chế giữ qua các trường hợp đó. Bản ngôn
ngữ tiêu đề chi tiết đã có đề xuất riêng, chờ đợt này xong mới áp dụng.
Giao diện production sau đăng nhập chưa được quan sát.
