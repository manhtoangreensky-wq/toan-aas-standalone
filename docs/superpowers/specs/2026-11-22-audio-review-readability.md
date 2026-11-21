# Tách nhãn và mô tả trong bản rà soát âm thanh

BASE=cd9c5c14263e1397531056e318a9f46394a8562d.
STATUS=LOCAL_CHECKED_RELEASE_PENDING.

Ảnh từ PR787 và kiểm tra trình duyệt cục bộ xác nhận nhãn cùng phần
mô tả của từng mục rà soát dính trên một dòng ở 320px và 1440px.
Chỉ điều chỉnh trình bày trong `portal-audio-hub-review-pack` trên
trang `audio-hub-detail`: nhãn và mô tả thành hai dòng. Giữ nội dung,
cấu trúc, nút, quyền, dữ liệu, API, motion và các trang khác.

Antigravity R1 chọn sai vùng, R2 trả đúng một rule CSS sau khi Owner
xác nhận. Từ chối tự động trước R2 không tính là lỗi worker. Root đối
chiếu và áp dụng đúng đề xuất. Kiểm tra toàn tệp CSS bằng BASE cộng
đúng một rule, đồng thời giữ kiểm tra historical riêng.

Trình duyệt cục bộ dùng HTML từ renderer thật, CSS thật và dữ liệu giả:
VI/EN/ZH × mobile tối/desktop sáng, 6 bố cục/24 cặp nhãn-mô tả,
6 ảnh mới, phần ngoài vùng không đổi, không gọi mạng. Sáu ảnh đã được
kiểm hash/kích thước và giải mã. Ba ảnh đại diện đã được xem trực tiếp.
Đây không phải phiên đăng nhập production hay kiểm tra toàn accessibility.

Hồi quy đầu 42 PASS/5 FAIL do các kiểm tra historical còn chốt CSS cũ;
đã thêm phép chiếu chỉ cho dữ liệu historical, không thay kiểm tra
forward toàn tệp hiện tại. Lượt liên quan sau sửa QA: 47 PASS/0 FAIL.
Một lượt riêng với 24 tệp kiểm tra có dùng CSS: 350 PASS/0 FAIL/0 skip;
các module được nhập có thể trùng những lượt khác nên không cộng tổng.
CI/merge/deploy/VPS và live là các cổng riêng chưa hoàn tất.

Hai phiếu tiếp theo về phản hồi lỗi cũ và ba thông báo chưa dịch đã
trả đề xuất; giữ nguyên kết quả, chỉ áp dụng sau khi đơn vị này được
phát hành. Goal toàn bộ và motion vẫn mở.
