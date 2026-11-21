# Trước phát hành — tách nhãn và mô tả âm thanh

BASE=cd9c5c14263e1397531056e318a9f46394a8562d.
STATUS=LOCAL_CHECKED_RELEASE_PENDING.

Đề xuất Antigravity R2 thêm đúng một rule CSS cho bốn cặp nhãn/mô tả
trong kết quả rà soát. Không đổi nội dung, cấu trúc, route hoặc chức
năng. CSS được đối chiếu nguyên tệp với BASE cộng rule này.

Renderer và trình duyệt cục bộ đã kiểm VI/EN/ZH trên mobile/desktop:
6 bố cục, 24 cặp tách dòng, 6 ảnh mới được giải mã và kiểm hash; phần
ngoài vùng không đổi. Hồi quy liên quan 47 PASS; các kiểm tra historical
có phép chiếu riêng, không thay cổng so nguồn mới. Lượt riêng với 24
tệp có dùng CSS đạt 350 PASS/0 FAIL; không cộng trùng với lượt 47.
Bằng chứng này không phải signed UI production.

CI, merge, deploy, runtime và kiểm tra tệp công khai phải được xác nhận
riêng. Hai phiếu thông báo đã nhận đề xuất, giữ để xử lý sau đơn vị này.
