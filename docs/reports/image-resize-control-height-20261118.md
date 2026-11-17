# Chiều cao ô nhập Đổi kích thước ảnh —18/11/2026

BASE_SHA=4180d4e2ec0ac4303037b409e55cb5f86106fa84.
Branch=codex/resize-control-height-20261118.
Tracker=Issue689; không tạo tracker khác.

## Phạm vi và nguyên nhân

Ô chọn kích thước trên máy tính bị kéo cao theo ô chọn ảnh kèm vùng tìm
kiếm. Bằng chứng cũ đo 131,828125 px ở cả ba ngôn ngữ; mobile 44 px.
Chẩn đoán chỉ thay `align-content:start` đưa ô chọn về 44 px và giữ nguyên
chiều rộng. Ứng dụng thêm đúng một rule CSS riêng cho năm field của form
Resize, không thay renderer, chữ, chức năng, tùy chọn, quyền hoặc xử lý ảnh.

Antigravity R1 trả đúng OLD/NEW; điều phối áp nguyên đề xuất. Không có lỗi
thực hiện worker hoặc điều phối tự sửa ứng dụng. 150 tệp ứng dụng còn lại,
gồm toàn bộ Python/JS/auth/engine/tiền/motion/templates, khớp BASE.

Theme LF SHA256:
`153ae3f84afcd2b528ba762d307374df3f188a2e6e7867d51e2d4867329ced56`.

## Bằng chứng, không gộp các lượt thành một lần xanh giả

| Phép kiểm | Kết quả |
|---|---|
| Chrome geometry, BASE, 12 tổ hợp | 6 desktop RED, 6 mobile PASS;4,03s |
| Cùng phép kiểm trên candidate | 12 PASS;3,56s |
| Hai assertion nguồn mới ban đầu | 2 PASS;262,8264ms |
| Nhóm nguồn có lọc tên qua bảy tệp | 9 PASS/1 FAIL;10559,549ms; ba PASS là module không có tên khớp |
| Chỉ ba assertion bị ảnh hưởng sau sửa reader | 3 PASS;3685,0607ms |
| Native mới, actual localhost READY | 6/6;VI/EN/ZH×375 sáng/1440 tối |

Lỗi assertion lịch sử do adapter QA từ chối bản sao rule cũ trước khi
comparator gốc được kiểm tra. Chỉ sửa biên đọc QA: đảo đúng phần CSS mới,
giữ mutation/duplicate cũ cho comparator gốc. Không sửa assertion/hash gốc,
không sửa ứng dụng để qua bộ đo.

Native đo đủ 30 control: select 44 px, input 44,5 px; chiều rộng nằm trong
viewport. Mỗi ca GET ảnh thật một lần/hai item, chọn ảnh của tài khoản QA,
nhập1080×1920, Tab đúng thứ tự, không submit. Không tràn ngang, lỗi trang,
console, dialog, request ngoài hoặc ghi sản phẩm.

Môi trường mới có ba đăng ký/ba đăng nhập/12 metadata/không blob. Hash ba
audit đăng ký giữ; chỉ thêm đúng ba login. Schema/dữ liệu sản phẩm còn lại,
151 nguồn/binding/fixture/scope giữ. 22 tiến trình sở hữu dừng, còn0.
Điều phối đã xem bốn ảnh raw: VI1440 vùng form, VI375 đầu trang,
EN1440 đầu trang, ZH375 vùng form; crop có fixed UI không chứng minh toàn
trang. Browser plugin không có; dùng Chrome/Playwright đã kiểm tra sẵn.

## Ranh giới phát hành

PR760 trước đó đã giao runtime4180d4e2. Kết quả ở đây là nguồn và QA cô lập
của thay đổi CSS mới; CI đúng HEAD, merge, deploy, SHA máy chủ và tài nguyên
công khai phải có receipt riêng. Không nhận signed production UI, Safari,
thiết bị thật, PNG/âm thanh cuối hoặc toàn goal hoàn tất. Các utility còn
chữ kỹ thuật, Compress metadata, locale/AX/auth/responsive và motion còn mở.
Motion M-FINAL01..06 vẫn cuối.

PROVIDER_CALLS=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_MUTATIONS=0;ENV_CHANGES=0.
