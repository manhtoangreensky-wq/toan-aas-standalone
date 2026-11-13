# Phiên MEMBERSHIP-FALLBACK-ORIGIN-20261113

BASE: `78dc73c847a8bcf28a76bc34f00b1ae32003ac9a`. Tracker: Issue #689.

|Mục|Điều kiện nghiệm thu|Bằng chứng local|
|---|---|---|
|MFO-LOCALE|Loại gói mặc định đúng VI/EN/ZH, không thêm khóa sai namespace|60 ca renderer; khóa dịch hiện có|
|MFO-ABSENT|Thiếu/rỗng/không hợp lệ không thêm ghi chú tự sinh hoặc paragraph rỗng|Baseline 48 lỗi/60 ca; sau sửa 60/60 đạt|
|MFO-PROVIDED|Ghi chú thật/legacy/escape giữ nguyên, kể cả trùng câu mặc định cũ|So từng ghi chú và dữ liệu gốc/context|
|MFO-IDENTITY|Dòng hợp lệ đầu tiên, code+label, nguồn 100 dòng, duplicate không cho mượn ghi chú|20 tình huống ×3 locale|
|MFO-PROTECTED|Giá, số dư 0, trạng thái, controls và mọi HTML ngoài phạm vi không đổi|240 ca hồi quy; 18 tệp bảo vệ và phần còn lại của bundle khớp BASE|
|MFO-COMPONENT|12 tổ hợp 390/1440 sáng/tối, ghi chú thật và thiếu ghi chú|Renderer/CSS/khung shell thật, nguồn tổng hợp, chặn mạng|
|MFO-NATIVE|App có đăng nhập QA, trang có dữ liệu thiếu và rời trang an toàn|12 lượt xem/3 rời trang, 240 mẫu màu min5,216649621048673:1; 0 ghi kế hoạch, 0 tiến trình còn|
|MFO-DELIVERY|CI đúng HEAD, merge/deploy/runtime/assets riêng|Theo receipt trên cùng Issue #689 và PR|

Trạng thái trước push: READY cho CI/release; không tự coi là production LIVE.
Lỗi quyền tệp Windows của một ca Tester tái hiện nguyên vẹn trên BASE,
không che/skip/sửa để xanh; giữ kiểm tra Linux trên CI. Compile đạt và
51 ca Python khác đạt. Nguồn case chuẩn là `DANH-SACH-CASE.md`.
Không tạo issue case mới hoặc checklist cạnh tranh.
