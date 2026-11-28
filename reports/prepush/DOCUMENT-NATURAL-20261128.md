# Lời hướng dẫn tài liệu — kiểm tra trước khi cập nhật kho

BASE=cf94b23e6a26010e88ebcd33b36623204c784c9a;
branch=codex/auth-draft-isolation-20261128; Issue689;
product=standalone WebApp.

## Rà soát và tài liệu hiện tại

Chỉ chữ cố định trong phần chuẩn bị tài liệu được đổi sang lời tự nhiên
VI/EN/ZH. Ba tệp ứng dụng,60record/304khóa/912giá trị; bốn phiếu
Antigravity4ExtraHigh, Root ghép cơ học, không tự viết logic ứng dụng.
Reviewer độc lập không phát hiện finding cần sửa. Nội dung khách, kiểm
tra quyền/dữ liệu, điều khiển và mọi lời báo lỗi vẫn giữ ý nghĩa.

34raw primary,176Node liên quan/lịch sử,9Python theo ledger failed-only,
cú pháp/compile/diff-check đạt. Không cộng số trùng giữa các nhóm thành
tổng toàn ứng dụng. Hai kiểm tra menu/shared đạt nhưng chưa đo riêng số.
12lượt trình duyệt cục bộ và2lượt VI nền tối có tương tác thật với ô nhập
và lựa chọn; giới hạn rõ tại PHIEN-DOCUMENT-NATURAL-20261128.

TAI-LIEU/01 ghi phạm vi đã sửa tại máy và lần phát hành trước PR821 đã
giao CF94. TAI-LIEU/02 đối chiếu chức năng chuẩn bị tài liệu với công cụ
xử lý tệp riêng; không đổi lưu kế hoạch thành tạo tệp hay mở provider.

## So với tài liệu ban đầu

Nguồn thực: copyfast_document_workspace.py, hợp đồng cũ của phần tài liệu,
masterR217/R218 và BASE. Giữ khả năng ghi yêu cầu, sắp xếp bước, tự rà soát
và lịch sử riêng; bỏ cách diễn đạt triển khai cho khách. Tách/gộp/chuyển
tệp vẫn ở công cụ riêng; không tạo đầu ra từ biểu mẫu lập yêu cầu.
Không dùng tên chức năng trong tài liệu để suy có kết quả xử lý thật.

## Chỗ làm việc cho người kiểm tra

Phiên DOCUMENT-NATURAL-20261128, manifest
KIEM-THU/PHIEN-DOCUMENT-NATURAL-20261128.md; nguồn case
KIEM-THU/DANH-SACH-CASE.md; cùng Issue689, không tạo tracker cạnh tranh.
Metadata tài liệu phải được đo lại trước source commit/provenance.

Sáu tài liệu Voice/Music được ghi chung để khép bằng chứng đã làm trước
trên BASE CF94, không coi là kiểm lại nguồn sau sửa chữ hoặc việc worker
đợt này. Không đổi sáu kết quả bản nháp thành nghiệm thu toàn lifecycle.

PUSH_GATE=READY; METADATA_REFRESH=MEASURED_BEFORE_SOURCE_FREEZE;
CI=NOT_RUN; MERGE=NO; DEPLOY=NO; LIVE_PASS=NOT_TESTED.
PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_WRITES=0.
Goal tổng, thiết bị/Safari/offline/phiên production và chuyển động còn mở.

Metadata Tester:32/33đạt; một ca quyền tệp POSIX0600 trả0666 trên Windows.
Đã chạy đúng ca đó bằng ba tệp frozen BASE trong thư mục tạm riêng:
cùng1FAIL/0666, test và script sync giữ đúng hash, NEW_FAILURES=0.
Không sửa/bỏ test; Linux CI phải chạy và đạt ca này trước merge.
