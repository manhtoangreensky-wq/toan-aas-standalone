# Phiên kiểm tra — chữ giao diện thiết kế ảnh

BASE runtime `d165bad407a51a8cf6339b019a073f8a1a1eb37a`, Issue #689;
contract `7082649992`. Case ISLC trong `DANH-SACH-CASE.md` là nguồn duy nhất.

Ba locale Việt/Anh/Trung, chi tiết Studio/Hub, trạng thái đang tải/lỗi/sẵn
sàng; thư viện rỗng/có dữ liệu/lọc và tham chiếu không chọn được. Kiểm tên
khách, nội dung có ký tự đặc biệt, đầy đủ field names/options/required/limits.
Không gửi form thật hoặc gọi dịch vụ ngoài.

Đã kiểm mã vật lý bằng 16 Node mục tiêu, Chrome24 màn ở 375/1440, 32 mẫu
màu và hai ca nhập toàn bộ trường dài/lựa chọn. Keyset thêm đúng 22 khóa
cân bằng, từ điển giữ khóa bất biến. Hồi quy 171 tệp/5.202 ca đạt trước
câu sửa cuối; bốn tệp Image ngoài nhóm có 16 ca đạt. Sáu ca header/sidebar
đã kiểm riêng cũng nằm trong hồi quy, không cộng lặp. Python lịch sử/vault/
điều hướng 155/155 và màu 90/90 đạt.

Review chỉ ra câu hứa giữ lựa chọn chưa lưu quá rộng. Worker trả đúng một
hàng rút gọn ba ngôn ngữ; ba ca RED tái hiện và 48 ca bị ảnh hưởng sau sửa
đạt. Trong đó có 30 trạng thái thư viện trên renderer nguồn vật lý: rỗng,
có dữ liệu, có lọc, ảnh không chọn được, dự án chưa đặt tên. Không sửa
logic chọn/đọc dữ liệu. Gate phát hành vẫn cần bằng chứng riêng.

Không dùng bản dịch này làm bằng chứng toàn locale, đầu ra ảnh/provider
hoặc tương tác production sau đăng nhập.
