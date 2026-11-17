# Nhãn công cụ ảnh dùng chung — bằng chứng nguồn

BASE `ce40bf4089701d0ba47f46845e7061cb92d5bba1`.
Branch `codex/image-shared-plain-copy-20261117`; tracker Issue689,
report comment6956419825.

## Thay đổi có giới hạn

Ứng dụng chỉ đổi:

- `static/portal/portal-i18n.js`:21hàng/63giá trị trong
  IMAGE_OPERATION_COPY_ROWS, không thêm khóa hoặc đổi thứ tự.
- `static/portal/portal.js`:hai dòng return của renderImageResize,
  chỉ xóa nguyên hai div mỗi div ba span thông tin kỹ thuật lặp.

Hai proposal Antigravity riêng trả exact, điều phối đọc chung một lượt;
áp dụng tuần tự sau PR759 đã được triển khai và đối chiếu.
Không có lỗi thực hiện worker/không có sửa ứng dụng do điều phối tự viết.
Lỗi schema400 trước turn sinh token là lỗi mẫu kết quả, usage0, đã sửa đúng
schema; không đăng nhập lại hoặc đổi settings.

Candidate LF SHA256:

- i18n `45e5b9ba90fde2ba7af006df7c5b76505350283a8faa96706db48503692601eb`.
- portal `ff4eee9b0b7a1dd55704e3e97d7074389398b089c001f07b166346c36da9e881`.

149tệp ứng dụng khác exactBASE, gồm toàn bộ Python/auth/engine/tiền/provider/
styles/motion/templates. CI chỉ thêm lệnh chạy một file Node mới.

## Các lượt đã chạy, không gộp thành một lượt xanh giả

| Lượt | Kết quả | Thời gian |
|---|---|---|
| BASE thật,85ca |7PASS/78contentRED |7484.2387ms |
| Candidate85ca lần đầu |76PASS/9QAFAIL |11152.9626ms |
| Chỉ9ca sửa phép đếm emptydiv |9PASS |2838.9496ms |
| Hai comparator nguồn sau sửa bộ neo |2PASS |3051.7252ms |
| Ba ca completed download/save/handoff |3PASS |2446.4402ms |
|14tệp liên quan,304ca |304PASS/0FAIL |25845.6079ms |
| Metadata Tester targeted |1PASS/32deselected |0.69s |

Chín lỗi QA là kiểm nhầm hero-actions rỗng vốn có từ BASE thành ô mới.
Chỉ sửa phép so emptydiv với BASE; điều kiện phải bỏ chip, giữ h2/p/state/
quyền/retry không đổi. Hai lỗi comparator là sắp thứ tự theo toàn tệp có
khóa trùng thay vì đúng mảng. Không sửa app, không nới assertion/hash gốc.

Kiểm tra mới chạy trực tiếp hai full bundle vật lý, không dùng projection.
Các test lịch sử chỉ đảo hữu hạn21hàng/hai dòng ở biên đọc riêng của test;
giữ assertion/hash/order/rawintegrationguards và mọi byte ngoài phạm vi.
Comparator mới từ chối partial/unknown/duplicate/reordered changes, giữ
customer literal và byte bên ngoài. Không thay shared app helper.

## Giao diện và phát hành

NativeR2 đã được nhận: sáu ca VI/EN/ZH ×375sáng/1440tối,24kiểm tra bốn
nhãn mới,18kiểm tra thấy chữ sau cuộn thật,30control được kiểm tra thấy và
không tràn ngang. HTML đầu/bootstrap/header/hero giữ các trường metadata
độc lập đã chốt,không so toàn auth/bootstrap body. Mỗi ca typedGET thật1,
hai ảnh;chọn ảnh tài khoản QA/1080×1920/Tab,không submit sản phẩm.
Không lỗi trang/console/dialog/egress. Ba đăng ký/ba đăng nhập/12metadata/
không blob;giữ registerhash,đúng ba auditlogin mới,schema/otherproductdata/
source151 giữ.22tiến trình sở hữu dừng,còn0.

R1 không có ca được nhận:bộ đo lấy cả dấu và chữ dành cho trình đọc màn
hình vào nhãn;chỉ một login đã chạy trước lỗi,13tiến trình dừng,còn0.
R2 sửa riêng reader/visible-text measurement,không đổi app hoặc timeout.
Observer QA cuối SHA256
`c71dea6676358204e1197440497d5a24c52aba33f0a766c7f463f9941e88a7cf`.
Đã xem bốn ảnh raw:VI375đầu trang/vùngtrường,EN1440tốiđầu trang,
ZH375vùngtrường;ảnh phần tử có giới hạn crop,không nhận wholepage/device.
Native kiểm bốn khóa;nội dung17khóa khác dựa nguồn/consumer đã ghi riêng,
không tạo trạng thái lỗi giả để chụp ảnh.

Phát hiện riêng trong ảnh/bộ đo:ô chọnpresetdesktop cao131.828125px ở
cả ba ngôn ngữ,trong khi mobile44px. Đây là backlog bố cục tiếp theo,
không sửa ké vào hai proposal chữ;không nhận toàn UI hoàn thiện.
CI exactHEAD,merge,deploy,runtime,assets và receipt vẫn là cổng riêng.
PR759 là bản trước đã giao,không dùng thay bằng chứng phát hành ứng viên.

Nguồn case: tám ISPC trong KIEM-THU/DANH-SACH-CASE.md.
Phiên Tester IMAGE-SHARED-PLAIN-COPY-20261118 ở READY.

Không nhận toàn ứng dụng đã hết chữ kỹ thuật. Utility khác, phụ đề custom,
Compressmeta,locale/AX/auth/responsive/device/Safari/signedUI/finaloutput
và M-FINAL01..06 còn mở; motion vẫn cuối.
Phiên receiverWeb–Bot là chỉ-đọc nguồn công khai, không sửa engine hoặc
chứng minh tạo âm thanh. Không đưa candidate engine vào nhóm UI này.

`PROVIDER_CALLS=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_MUTATIONS=0;ENV_CHANGES=0`.
