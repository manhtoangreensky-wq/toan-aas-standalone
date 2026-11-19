# Phiên kiểm tra — PDF sang ảnh và Word

TESTER_PROJECT_ID=DOCUMENT-CONVERT-CUSTOMER-COPY-20261119.
STATUS=READY_FOR_EXACT_HEAD_CI.
BASE_SHA=a589008be5d7be371789551ffc11e750db46270b.
TRACKER=Issue689/comment7006239694.
Nguồn case: [DANH-SACH-CASE.md](DANH-SACH-CASE.md).

- [x] PR774/775 giao và receipt xong trước đợt này.
- [x] Ba Antigravity R1 schema/exact đạt, 13 phép thay/3 tệp ứng dụng/
  28 khóa/148 nguồn bảo vệ, không Root takeover.
- [x] BASE physical 5 đạt/11 RED → 16 đạt; portable/source 32 đạt.
- [x] HTML đầu BASE 1 đạt/6 RED → 7 đạt.
- [x] Quyền thiếu/false/chuỗi, nguồn rỗng, làm mới, nội dung khách,
  history/cards/download và 7 trang bảo vệ được so nguyên bundle.
- [x] Word giữ giới hạn chữ bôi chọn, không hứa OCR/bố cục/hình/bảng/phông.
- [x] BASE/GREEN hai trang, mỗi nhóm 24 cấu hình, tổng 96/192 PNG;
  parse/CRC/hash/kích thước, 42 tiến trình/nhóm về 0.
- [x] GREEN không panel thừa/khung trống, kho tệp focusable trong form,
  ba locale/sáng tối/Tab thật; không ghi sản phẩm, media, provider hoặc ví.
- [x] 264 BASE/288 GREEN paint UNKNOWN giữ mở; Root xem VI320 tối/
  EN768 ngang sáng; không nhận toàn bộ tương phản/khả năng tiếp cận.
- [x] Ba lỗi export Python tái hiện y hệt BASE (2 Win206/1 chữ cũ).
  Collector inverse cũ BASE/current lỗi tương đương; biên QA hữu hạn
  sửa collector, giữ toàn bộ 29 assertion gốc + 10 ca mới: 39 đạt.
- [x] Affected Node: 1.691 ca giữ + 10 tên lỗi đạt + 132 ca trước đó
  chưa chạy đạt = 1.833 ca duy nhất. Ca OLD mới 1 đạt; không chạy lại
  cả nhóm hoặc native. Metadata Tester 2 đạt/31 bỏ chọn, 0.66s.
- [x] Review C0/I0/M0, Root đọc đủ; prepush READY 39 tệp/secret0,
  nguồn ứng dụng giữ đúng13phép thay. Không ghi toàn repository xanh.
  Lượt đầu 1.691 đạt/14 lỗi comparator trong 242926.9242 ms; giữ ca đạt,
  chỉ sửa biên hữu hạn và chạy lại ca thất bại/chưa được thực thi.
- [x] PR776/HEAD4c24489e CI44512041758haiSUCCESS723s/272s,
  18browser/456authhashkhớp;merge/runtime8ba0d045/treedf253937.
- [x] Deploy44515050253SUCCESS66s/3active-running/health/assetskhớp;
  receiptIssue7006239694/PR7007830023đọclạiđúng.
- [ ] Production có đăng nhập và tệp PNG/ZIP/DOCX cuối: NOT_TESTED,
  không được tick từ CI hoặc health200.

Các cấu hình: VI/EN/ZH × light/dark × 320×844, 414×896, 768×414,
1024×768. Chỉ QA cô lập, cờ chuyển đổi trong child, không sửa ENV máy
hay production. [Báo cáo](../docs/reports/document-convert-customer-copy-20261119.md).
