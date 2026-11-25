# FREE-TOOLS-READABLE-COLORS-20261125 — kết quả trong phạm vi

BASE `a8cf07490448548a2a1be6800fb7e146abeac726`, Issue #689,
contract `7154102334`. Trạng thái `LOCAL_SCOPED_PASS_RELEASE_PENDING`.
[Phiên và tiêu chí](../../KIEM-THU/PHIEN-FREE-TOOLS-READABLE-COLORS-20261125.md);
nguồn ca duy nhất là `KIEM-THU/DANH-SACH-CASE.md`, nhóm `FT-RC-*`.

## Thay đổi được kiểm

Chín record do Antigravity trả, chỉ đổi màu trong `portal.js` và
`portal-theme.css`. CSS khóa dưới `.portal-page.portal-free-tools`.
Sáu số liệu và vỏ QR đổi màu, nền ảnh QR bên trong vẫn trắng.
Chữ, hình học, font, tab, controls, disabled, giá trị/thuật toán/
actions và các miền bảo vệ giữ nguyên. Không có sửa focus bổ sung.
Những thiếu sót bảng màu/đặc tả trước đó là lỗi điều phối, không phải
lỗi code worker; `workerCodeFailures=0`.

## Kiểm tra nguồn và hồi quy

- Test mới trên nguồn trước sửa: 4 ca, 1 fail/3 pass.
- Nhóm 8 tệp ảnh hưởng: 398 pass/0 fail/0 skip; đã gồm test mới.
- Python: nhóm màu/inverse/theme/auth-contrast 9 pass; nhóm navigation/
  foundation/aura/i18n 142 pass. Chưa nhận 151 ca duy nhất.
- Hồi quy Node còn lại: 168 tệp được chọn, 4.748 lượt thành công.
  Cùng nhóm ảnh hưởng là 176 tệp chọn, 5.146 lượt quan sát,
  4.936 khóa `(file, name)` duy nhất; 0 fail/0 skip. JUnit không
  có line/column; 14 ca Image Edit dựa vào terminal hoàn tất và
  tên ca không đổi. Không gọi sổ gộp này là một lượt mới toàn suite.
- Runner đầu `ETIMEDOUT` sau 600 giây, chưa xuất test case. R2
  đạt 4.292 lượt ở 165 tệp; ba tệp chỉ số 3/119/126 hết giới hạn
  180 giây. Phục hồi riêng đạt 14/88/354 ca. Ma trận renderer nguồn
  nặng được quan sát tiêu thụ CPU; phục hồi dùng Node 24,
  `test-isolation=none`, một tệp mỗi lượt. Không đổi mã ứng dụng
  hoặc assertion. Giữ bằng chứng timeout và lần phục hồi đầu bị
  ngắt; không tính các lượt chưa hoàn tất hoặc lỗi code Antigravity.
- Metadata readiness Python 1/1 và py_compile app/helper/test Python
  thay đổi exit 0 đã được phiên chính quan sát; không chạy lặp.
- Review độc lập một lượt: C0/I0/M0, sẵn sàng cho CI đúng HEAD; không
  chạy lại test chỉ để tạo thêm số lượt.

## Đo Chrome nguồn vật lý

Browser plugin không có trong phiên; dùng Chrome riêng, renderer/CSS/
tab handler thật với dữ liệu giả và `body.portal-body` đại diện.
Luồng: mở `/free-tools` → xem sáng/tối, hover/focus/chọn tab bằng bàn
phím → chữ và nền rõ, vòng bàn phím nhìn thấy, controls không đổi.

Đầu trang: 8 màn ở 360/375/768/1440 × sáng/tối, 32 trạng thái,
640 mẫu. BASE có 320 mẫu dưới 4,5:1; sau sửa 0/640, thấp nhất
5,4732500812:1. Text/geometry/font/tab bằng baseline cùng ngữ cảnh;
không lỗi, yêu cầu mạng hoặc tràn.

Nội dung: 20 màn ban đầu của 10 công cụ × sáng/tối, 286 mẫu quan sát.
BASE có 94/265 mẫu đang bật và đo được dưới 4,5:1, thấp nhất 1:1.
Sau sửa 278/278 mẫu đang bật và đo được đạt, thấp nhất
5,0504608850:1. BASE có 17 mẫu chưa kết luận; sau sửa còn bốn mẫu
đều disabled. Tám mẫu disabled giữ nguyên. Text/geometry/IDs/disabled
bằng baseline, không lỗi hoặc mạng. Không coi số mẫu là số control.

Bàn phím thật `ArrowRight`: 8 màn, `focus-visible`, vòng solid 3px;
0 dưới 3:1, thấp nhất 11,7724811322:1, không lỗi hoặc mạng.
`free-tools-keyboard-focus-red-nov25` là kết quả PASS trước amendment
được đề xuất; amendment đó không được áp dụng.

## Giữ mở trước phát hành

Sổ `free-tools-colors-regression-ledger-nov25.json` là bằng chứng
gộp hồi quy, không thay bằng chứng CI hoặc giao diện production.
Chờ provenance, CI đúng HEAD,
merge, deploy, runtime/health, 5 tệp trực tiếp + 5 URL có phiên bản,
biên nhận Issue #689. Chưa xác nhận giao diện production sau đăng
nhập, toàn bộ bootstrap/auth/API, trạng thái sau hành động/đầu ra,
thiết bị thật/Safari hoặc whole-app compliance. Không gọi QR/nguồn
bên ngoài, không ghi dữ liệu thật, không chạm provider/ví/ENV.
Toàn goal và motion cuối vẫn mở.

## Kiểm tương thích main sau cùng

PR808 đã có trên main/VPS tạifbcbfdf4; phụ lục689/7161431864 trước
merge86a0504a. Chín record màu giữ nguyên; API/realtime/extension/pricing
và test upstream bằng đúng main. Một comparator hữu hạn bổ sung hai
insertion banner29dòng; không thay assertion cũ hoặc bỏ kiểm thay đổi lạ.
Nguồn vật lý vẫn so main cố định+9record.10tệp giao nhau422/422,
Pythoninverse3/3 đạt. Không nhận full regression sau sync; CI mới trên
HEAD cuối bắt buộc. CI upstream lỗi fingerprint cũ không dùng làm PASS.

CI PR80945637352354 sau đó phát hiện pin lịch sử toàn nguồn còn hash
API trước PR808. Mapping QA chỉ nhận đúng hai hash fixedmain của
API/realtime; nội dung lạ giữ nguyên, test rawphysicalđòi exactmain và
pin/assertion gốc không đổi.17tệp452/452đạt,0skip;reviewC0I0M0.
Đây là sửa tương thích kiểm tra, ứng dụng0thayđổi; không nhận runtime
API/tiền/provider từ hash. Vẫn cần freshCI trên cùngPR809 trước giao.

PR810 sync: phụ lục689/7168548459, mergec7ac3f7b, fixed-main0a9022ce.
Ba UI upstream giữ nguyên, chín record màu không đổi. Inverse ba record
catalog có hash toàn nguồn cố định, giữ byte lạ trong/ngoài record và
giữ lỗi assertion cũ; không thay toàn tệp theo hash. Nhóm cuối27tệp/
538lượt JavaScript và Python98/98 đạt; review delta cuốiC0/I0/M0.
Ca Python bổ sung đòi câu lịch sử lỗi cùng trên main/ứng viên báo riêng.
CI45652044355 hai job đạt cho63ad906a, artefact15043310897/15042896999;
không phải CI bản ghép. Provenance/CI/merge/deploy/live bản ghép còn mở.
