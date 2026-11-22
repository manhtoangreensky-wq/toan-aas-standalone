# Thiết kế ảnh — ngôn ngữ nhãn cố định và màu tiêu đề

BASE đang chạy `d165bad407a51a8cf6339b019a073f8a1a1eb37a`, PR #797,
CI `45045044485`, deploy `45047560707`, receipt Issue #689 `7082628798`.

Đáp ứng yêu cầu: giao diện tiếng Việt dùng chữ Việt, tiếng Anh dùng chữ Anh,
tiếng Trung dùng chữ Trung; giữ nguyên tên riêng và nội dung khách. Thay đúng
32 record đã giao worker trong ba tệp:

- `static/portal/portal.js`: nhánh tiêu đề/mô tả/đường dẫn/nhãn đầu trang
  của hai loại chi tiết ảnh và chữ của chín trường phương án.
- `static/portal/portal-i18n.js`: 24 hàng thư viện đã có, ba khóa đầu trang,
  19 khóa trường phương án; đăng ký trước khi khóa từ điển.
- `static/portal/portal-theme.css`: một quy tắc màu chữ tiêu đề thẻ chi tiết
  ở giao diện sáng.

Tiêu chí:

1. Tiêu đề, mô tả, nhãn đầu trang và breadcrumb chi tiết đúng VI/EN/ZH.
2. Thư viện, danh sách bảng, phần trống và hướng dẫn tham chiếu dùng câu ngắn
   đã xét; trạng thái không chọn được vẫn phản ánh đúng dữ liệu. Không hứa
   giữ lựa chọn chưa lưu khi mục đó vắng trong trang kết quả tìm kiếm mới.
3. Chín trường phương án đúng ngôn ngữ; giữ tên, thứ tự, required, giới hạn,
   giá trị và nguồn options. Ngoài “Tạo mới”, vẫn hướng dẫn phải chọn ảnh gốc.
4. Tiêu đề thẻ sáng đạt 4,5:1; hình học và màu tối không đổi.
5. Tên khách và chuỗi trùng các từ dịch vẫn nguyên văn, được escape. Giữ
   toàn bộ hành động, route, quyền và cơ chế giữ bản nháp vừa phát hành.
6. Nguồn bằng BASE cộng đúng 32 record; không sửa backend, auth, Bot,
   route-engine, provider, ví, PayOS, ENV, dữ liệu production hoặc motion.

Bằng chứng trước áp dụng: tiêu đề/mô tả lẫn ngôn ngữ ở sáu trường hợp;
chín nhãn phương án lẫn ngôn ngữ ở ba locale; 16/32 mẫu tiêu đề thẻ không
đạt tương phản. Đề xuất trong bộ nhớ đã qua 24 màn Chrome, 18 ca metadata,
12 đối chiếu trang khác, 72 giá trị thư viện/30 trạng thái; 32/32 mẫu màu
sau đề xuất đạt và hình học/màu tối giữ nguyên.

Thực thi: áp dụng record đã nhận, kiểm hiện vật vật lý và keyset/freeze,
biểu mẫu/option/nội dung khách/giữ bản nháp; chạy nhóm hồi quy một lượt,
rà soát độc lập một lượt, cập nhật vận hành/đối chiếu/Tester, provenance,
PR/CI/merge/deploy/runtime/assets/receipt theo thứ tự.

Chưa đóng toàn bộ locale Image: lỗi validation/phản hồi thao tác còn chữ
kỹ thuật và metadata Studio gốc nếu tái hiện sẽ là phiếu riêng. Giữ bản nháp
qua tải lỗi/đổi revision/rời trang, AX/auth/device/motion và tương tác
production sau đăng nhập vẫn mở theo checklist mẹ.

Rà soát tìm được một câu hướng dẫn hứa giữ lựa chọn quá rộng. Đây là lỗi
đặc tả của người điều phối, không tính lỗi worker. Antigravity trả đúng một
hàng sửa trung tính cho Việt/Anh/Trung; ba ca RED tái hiện trước sửa. Sau
sửa, 48 ca bị ảnh hưởng đạt, gồm 16 ca locale và 30 trạng thái thư viện
được vẽ bằng mã hiện tại. Hồi quy trước câu sửa cuối: 171 tệp/5.202 ca đạt,
không lỗi/không bỏ qua; không chạy lại toàn nhóm không bị ảnh hưởng.
