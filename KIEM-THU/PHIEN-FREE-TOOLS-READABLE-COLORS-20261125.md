# Phiên kiểm tra — màu chữ và nền Công cụ miễn phí

ID `FREE-TOOLS-READABLE-COLORS-20261125`; Issue #689, contract
`7154102334`. BASE `a8cf07490448548a2a1be6800fb7e146abeac726`;
nhánh `codex/free-tools-readable-colors-20261125`.
Trạng thái: `LOCAL_SCOPED_PASS_RELEASE_PENDING`.

## Phạm vi khóa

Đúng chín thay đổi do Antigravity đề xuất trong hai tệp giao diện:
hai phần CSS chỉ áp dụng cho `/free-tools`, sáu màu số liệu văn bản
và một cặp nền/chữ bên ngoài bản xem trước QR. Không đổi chữ, bố cục,
cỡ chữ, điều khiển, dữ liệu nhập, phép tính, thuật toán QR, quyền,
API, ví, nhà cung cấp hoặc chuyển động. Nền trắng bên trong ảnh QR
và độ mờ của điều khiển bị vô hiệu giữ nguyên.

Các ca `FT-RC-*` trong [nguồn ca kiểm tra](DANH-SACH-CASE.md) là
nguồn duy nhất. Không tạo thêm bảng kiểm cạnh tranh.

## Kết quả đã đo

| Nhóm | Trước sửa | Nguồn vật lý sau sửa |
|---|---|---|
| Đầu trang và tab; 360/375/768/1440, sáng/tối; 8 màn, 32 trạng thái | 320/640 mẫu dưới 4,5:1; thấp nhất 1,0513:1 | 640/640 mẫu đạt; thấp nhất 5,4733:1 |
| Nội dung ban đầu của 10 công cụ, sáng/tối; 20 màn, 286 mẫu | 94/265 mẫu đang bật và đo được dưới 4,5:1; thấp nhất 1:1 | 278/278 mẫu đang bật và đo được đạt; thấp nhất 5,0505:1 |
| Vòng đánh dấu khi dùng phím mũi tên; 8 màn | Không yêu cầu thay vòng đánh dấu | 8/8 đạt 3:1; thấp nhất 11,7725:1; vòng 3px, `focus-visible` thật |

Nhóm nội dung trước sửa có 17 mẫu chưa kết luận vì nền chuyển màu/
độ mờ. Sau sửa còn bốn mẫu chưa kết luận, đều thuộc điều khiển bị
vô hiệu; tổng tám mẫu bị vô hiệu giữ nguyên. Không cộng các quan sát
này thành số điều khiển duy nhất hoặc kết luận cả ứng dụng đạt chuẩn.

Các cặp trước/sau dùng cùng `body.portal-body`, cùng chữ, hình học,
cỡ chữ, trạng thái tab và điều khiển. Không có lỗi, yêu cầu mạng
hoặc tràn trang trong nhóm đầu trang; các nhóm nội dung và bàn phím
không có lỗi hoặc yêu cầu mạng.

Nguồn mới RED: bốn ca, một lỗi và ba đạt trước khi áp dụng đề xuất.
Nhóm tám tệp ảnh hưởng: 398 đạt, không lỗi/bỏ qua. Python có hai
nhóm đã đo riêng: chín đạt và 142 đạt; chưa cộng thành 151 ca duy
nhất. Hồi quy còn lại của 168 tệp đã đạt 4.748 lượt thành công.
Gộp với nhóm ảnh hưởng là 176 tệp được chọn, 5.146 lượt quan sát;
4.936 khóa `(file, name)` duy nhất sau bỏ ca import lặp, không lỗi/
bỏ qua. JUnit không có line/column; 14 tên ca Image Edit lấy từ
terminal hoàn tất và tên ca không đổi. Không gọi đây là một lần chạy
mới toàn bộ suite.

Runner đầu hết giới hạn 600 giây, chưa xuất ca nào. Lượt tách theo
tệp đạt 4.292 lượt ở 165 tệp; ba tệp chỉ số 3/119/126 hết giới hạn
180 giây. Các lần phục hồi riêng đạt 14/88/354 ca, không đổi nguồn
hoặc assertion. Quan sát cho thấy các ma trận renderer nguồn nặng
tiêu thụ CPU; phục hồi dùng Node 24, `test-isolation=none`, từng tệp.
Timeout và lượt phục hồi đầu bị ngắt được giữ trong bằng chứng,
không cộng kết quả chưa hoàn tất và không tính lỗi code worker.
Metadata Python 1/1 và py_compile app/helper/test Python thay đổi
exit 0 đã được phiên chính quan sát; phiên tài liệu không chạy lặp.
Review gộp một lượt: C0/I0/M0; reviewer không chạy lại các nhóm test.

## Bằng chứng và cách kiểm tiếp

Các tệp bằng chứng được lưu ngoài repo, theo tên:

- `free-tools-contrast-baseline-r2-nov25/summary.json` và
  `free-tools-contrast-physical-r2-nov25/summary.json`.
- `free-tools-panels-baseline-r2-nov25/summary.json` và
  `free-tools-panels-physical-r2-nov25/summary.json`.
- `free-tools-keyboard-focus-red-nov25/summary.json`: kết quả đạt,
  dù tên thư mục có chữ `red`; không có sửa vòng focus bổ sung.
- `free-tools-colors-affected-nov25.xml`: 398 lượt đạt.
- `free-tools-colors-regression-ledger-nov25.json`: sổ gộp 176 tệp,
  5.146 lượt, 4.936 khóa duy nhất; không lỗi/bỏ qua.

Lệnh kiểm nguồn: `node --test tests/free-tools-readable-colors.test.mjs`.
Metadata nguồn ca đã đo và được cập nhật sau thay đổi câu bằng chứng.
Bản HEAD chính xác,
CI, merge, deploy, bản thực tế, sức khỏe dịch vụ, 5+5 tệp và biên
nhận còn là các cổng phát hành riêng; chưa ghi nhận chúng ở phiên này.

## Giới hạn giữ mở

Chrome chạy renderer/CSS/tab handler thật với dữ liệu giả, không phải
toàn bộ khởi động hoặc đăng nhập ứng dụng. Chỉ nội dung ban đầu của
công cụ được đo; không bấm tạo QR, tra cứu, lưu, tải hoặc gọi nguồn
bên ngoài. Không nhận đầu ra thao tác, giao diện production sau
đăng nhập, thiết bị thật, Safari, toàn-app locale/accessibility hoặc
motion đã đạt. Không sửa Bot/engine/auth/backend/ENV/dữ liệu thật.
`PROVIDER_CALLS=0`; `WALLET_MUTATIONS=0`; `WHOLE_GOAL_COMPLETE=NO`.

Trước push, main đã triển khai PR808/runtimefbcbfdf4. Phụ lục
Issue689/7161431864 và merge86a0504a kế thừa đúng upstream; chín record
màu không đổi. Comparator lịch sử bổ sung đúng hai insertion banner,
nguồn vật lý so fixedmain+9record. Nhóm giao nhau10tệp422/422,
Pythoninverse3/3 đạt; không cộng vào sổ full trước sync. CI cuối và
provenance mới vẫn là cổng phát hành, không dùng CI upstream bị lỗi.

Hòa nhập tiếp PR810 tại0a9022ce: phụ lục689/7168548459, mergec7ac3f7b.
Giữ UI upstream; màu vẫn chín record. QA inverse ba record catalog có
hash fixed-main trước/sau, giữ byte lạ và assertion cũ; nguồn vật lý so
0a9022ce+9record, `portal.css` nguyên main.27tệp/538lượt Node,
Python98/98 và reviewC0/I0/M0 đạt. Ca Python câu lịch sử lỗi cùng
main/ứng viên giữ báo riêng. CI45652044355 đạt trên63ad906a, không
thay freshCI bản ghép; phát hành vẫn cần provenance/CI/runtime/assets.
