# Công cụ miễn phí — màu chữ/nền, báo cáo trước phát hành 25/11/2026

BASE `a8cf07490448548a2a1be6800fb7e146abeac726`, nhánh
`codex/free-tools-readable-colors-20261125`, contract Issue #689
`7154102334`. Đợt UI riêng; mục tiêu toàn ứng dụng vẫn mở.

Các tab chọn và nhãn của Công cụ miễn phí trước đây có chữ tối trên
nền tối hoặc chữ sáng trên nền nhạt. Chín record từ Gemini4ExtraHigh
thay cặp màu ở đúng hai tệp ứng dụng; không đổi chức năng. Nền ảnh QR
bên trong giữ trắng, trường/giá trị nhập và thuật toán giữ nguyên.

## Review và xác minh

- Nguồn mới RED 1 lỗi/3 đạt; nhóm tám tệp ảnh hưởng398/398 đạt.
- Hồi quy còn lại168tệp chọn/4.748lượt đạt; tổng176tệp chọn/5.146lượt,
  4.936khóa file/name duy nhất. JUnit không có line/column;14ca ImageEdit
  được xác minh terminal và tên test nguồn không đổi. Không cộng test import.
- Lượt gộp600s không xuất testcase; R2 có165tệp/4.292lượt đạt, ba tệp
  chậm kiểm riêng14/88/354đạt. Recovery bị gián đoạn không tính. Không
  sửa assertion hoặc ứng dụng để vượt cổng; không nhận một lượt fullsuite.
- Python hai nhóm9/142đạt báo riêng; metadata1/1,py_compileexit0.
- Chrome8view360/375/768/1440 sáng/tối,32trạng thái:640/640mẫu chữ
  đạt4,5:1,min5,4733;20viewpanel ban đầu:278/278mẫu đang bật đo được
  đạt,min5,0505. Tám phần tử vô hiệu giữ nguyên; bốn mẫu không chắc
  thuộc disabled không nhận PASS.
- ArrowRight thật8view,focus-visible3px,min11,7725:1. Đề xuất thêm
  focus `!important` không cần thiết và không được áp dụng.
- Text/hình học/font/controls/disabled được đối chiếu cùng ngữ cảnh
  `body.portal-body`; mạng/ghi/provider/ví/ENV/dữ liệu thật0.
- Review đọc diff một lượt C0/I0/M0; không lặp test bởi reviewer.

Từ source chưa có output thật của nhà cung cấp, không suy đoán số người,
dữ liệu hoặc tiền. Chỉ thân panel ban đầu được đo; full-bootstrap,
signed production, Safari/thiết bị thật và toàn-app compliance chưa kiểm.

## Tài liệu và Tester

[Vận hành](../../TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md) ghi hành vi hiện tại;
[đối chiếu](../../TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md) giữ chức năng
ban đầu và chỉ ra cặp màu sai. PR800 được ghi đúng receipt cuối
7153868208, không tiếp tục dùng trạng thái chờ cũ.

[Phiên Tester](../../KIEM-THU/PHIEN-FREE-TOOLS-READABLE-COLORS-20261125.md),
[báo cáo](../../reports/tester/FREE-TOOLS-READABLE-COLORS-20261125.md),
chín case FT-RC trong [nguồn ca](../../KIEM-THU/DANH-SACH-CASE.md) và
readiness đã cập nhật. Dùng Issue689 và bộ nhãn/mẫu issue hiện có;
không tạo project/thẻ trống trùng lặp. Thiếu quyền Projects không mở
đăng nhập hoặc nâng quyền.

Nguồn giữ đúng chín record; historical inverse hữu hạn giữ unknown
bytes, từ chối partial/duplicate. Tệp Bot/engine/auth/API/tiền/provider/
ENV/schema và workflow deploy không đổi. Chỉ thêm đăng ký hai kiểm tra
nguồn của đợt màu vào quality workflow.

Source commit → refresh/verify Web-only provenance → commit evidence →
một PR → CI đúng HEAD → merge/tree → triển khai đúng SHA → runtime/
health/5+5assets/receipt là các cổng còn lại. Không nhận màu đã lên web
từ kết quả cục bộ. Composer và motion thuộc các bước tiếp theo.

## Bổ sung hòa nhập main

Main đã triển khai PR808 tại `fbcbfdf4f6dc3563ceba8b4f2815ae1ebb63d90b`
trước khi nhánh màu push; phụ lục689/7161431864 ghi trước merge86a0504a.
API/realtime/extension/pricing và hai test upstream giữ nguyên byte.
Chín record màu không thay đổi. Chỉ bổ sung QA cho đúng hai insertion
banner29dòng bằng fixture có SHA cố định, không ẩn thay đổi tùy ý.
Nguồn vật lý vẫn được so toàn tệp với main mới+9record.

Mười tệp giao nhau422/422 và Python inverse3/3 đạt sau sync. CI upstream
45599142644 lỗi provenance cũ; nhánh màu làm mới Web-only provenance
và yêu cầu CI mới đầy đủ trên HEAD cuối. Sổ hồi quy lớn phía trên thuộc
trạng thái trước sync, không được cộng lại hoặc nhận đã chạy full lần nữa.

CI đầu PR80945637352354 phát hiện pin lịch sử API chưa chấp nhận đúng
PR808 đã triển khai. Bốn tệp QA thêm đối chiếu hữu hạn cho đúng hai hash
nguồn API/realtime, giữ pin gốc, dữ liệu lạ và kiểm rawphysicalfixedmain.
17tệp nguồn452/452đạt,reviewC0/I0/M0; ứng dụng0thayđổi. Sửa cùngPR,
refresh/verifyprovenance vàCIHEADmới trướcmerge. Không dùng rawhash
để nhận API, wallet hoặc provider thực thi thành công.

## Main PR810 — bằng chứng hợp nhất cuối

Phụ lục689/7168548459 và mergec7ac3f7b giữ nguyên UI đã triển khai tại
0a9022ce. Nguồn màu vẫn đúng chín record gốc; `portal.css` nguyên main.
QA thêm đúng ba record catalog, xác minh toàn nguồn với hash cố định,
không thay toàn tệp để bỏ mất byte lạ. Chuỗi inverse giữ assertion/pin
cũ, unknown prefix/suffix/internal và lỗi duplicate/edited record.

27tệp JavaScript538/538, ba tệp Python98/98 đạt; review cuốiC0/I0/M0.
Một ca Python bổ sung đòi câu lịch sử lỗi giống trên fixed-main và ứng
viên; báo riêng, không sửa app hay nới assertion. Lượt QA trước chưa
đạt không cộng. CI45652044355 đạt trên63ad906a, artefact15043310897/
15042896999, không thay CI bản ghép. Tài liệu vận hành/đối chiếu,
phiên Tester, checklist và metadata ghi phần hòa nhập này.
Refresh/verify Web-only provenance sau source commit, push cùngPR809
và CI đúng HEAD vẫn là điều kiện trước merge/triển khai.
