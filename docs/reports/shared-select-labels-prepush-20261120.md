# Báo cáo trước phát hành — nhãn lựa chọn dùng chung

TASK=SHARED-SELECT-LABELS-20261120.
BASE_SHA=46423a6df9af67ac7ccabd88686d4cb42523a078.
BRANCH=codex/shared-select-labels-20261120.
TRACKER=Issue #689, comment 7033958929, đúng kho standalone.
PUSH_GATE=READY_AFTER_EXPLICIT_MANIFEST.

## 1. Review và tài liệu vận hành hiện tại

Đúng hai tệp ứng dụng, năm phép thay đã được Antigravity trả đề xuất và
Root nghiệm thu: ba biểu thức nhãn, bốn khóa dịch VI/EN/ZH và một nhánh
riêng cho tiêu đề `/reminders`. Hai fixture bất biến; 151 nguồn kiểm hash,
149 nguồn bảo vệ. Review độc lập không finding chặn. Chú thích QA được
làm rõ, không đổi assertion. Hai lệnh CI bổ sung; không thay trigger,
quyền, phụ thuộc, timeout hoặc cách triển khai.

`TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md` đã phân biệt production PR779 với ứng
viên nhãn local, ghi hành vi thật, số kiểm tra và giới hạn. Không đọc dữ
liệu khách để tự điền số lượng hay cấu hình. Không đổi auth/API/backend,
Bot/route-engine/provider/ví/PayOS/ENV/dữ liệu/CSS/motion.

## 2. Đối chiếu chức năng gốc

Không có hợp đồng gốc riêng cho nhãn bộ chọn trong phạm vi docs/migration
đã tìm; dùng chính source BASE. Bảng đối chiếu trong
`TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md` giữ UUID/filter/selection,
strict flags, required/disabled/ARIA/escaping và tên khách. Fallback
PDF/image không thể tới với DTO hợp lệ giữ nguyên, không giả dữ liệu.
Lỗi thiếu danh sách dự án ở `/asset-vault` vẫn là task chức năng kế tiếp.

## 3. Phiên Tester và bằng chứng

Phiên riêng `SHARED-SELECT-LABELS-20261120`, sáu mã case trong
`KIEM-THU/DANH-SACH-CASE.md`; hướng dẫn, BASE, phạm vi, tiêu chí, hồi quy
và giới hạn trong `KIEM-THU/PHIEN-SHARED-SELECT-LABELS-20261120.md`.
Giữ lịch sử tracker #412, 48 case/P0, nhãn/mẫu và quyền Projects; không
tạo hàng loạt thẻ, không đổi dữ liệu remote lịch sử để làm đẹp báo cáo.
Metadata Tester đã kiểm lại hai ca đạt sau lần cập nhật cuối.

- Nhãn: BASE 43 đạt / 19 RED → 62 đạt.
- Tiêu đề: BASE 3 đạt / 4 RED → 7 đạt.
- Chuỗi nguồn: 32 đạt sau nhánh tiêu đề; không cộng trùng 30 trước đó.
- Node bị ảnh hưởng: 5305 ca thực thi đạt; một bootstrap thiếu nguồn Bot
  bên ngoài tái hiện với đầu vào BASE, không skip hoặc sửa Bot.
- Python: hợp 126 đạt / 17 lỗi trùng BASE; không nhận toàn kho xanh.
- Native: chín cấu hình trước / 18 PNG + ba sau / sáu PNG, không chạy lại
  chín cấu hình đã đạt. Giữ receipt remaining `false`; không nhận một
  matrix 12 cấu hình cùng nguồn. GET thật và chọn bàn phím native đạt.
- Toàn bộ 24 ảnh đã kiểm hash, kích thước, chunk/CRC/IEND và giải mã đầy
  đủ. 30 đầu vào receipt/ảnh không đổi. Root đã đọc validator và kết quả.
- Nguồn/schema/core/auth audit/egress/mã runner giữ đúng, owned process 0.

## 4. Cổng xuất bản và phần không được nhận hoàn thành

Chỉ stage các tệp trong manifest đã quét; loại tên cả ba tệp state trước
mọi thao tác đọc/stage. Không mở campaign-state của Owner. Báo cáo audit
chỉ mang tên bằng chứng và hash, không chứa credential/ENV/dữ liệu khách.
Sau source commit chỉ làm mới hai tệp provenance Web bằng script có sẵn,
kiểm lại chúng rồi mới push đúng remote `github`.

Một PR, CI đúng HEAD, tree khi merge bằng bản được kiểm, deploy độc
quyền đúng SHA, đối chiếu VPS/tài nguyên và đọc lại biên nhận trên cùng
tracker. Các cổng đó chưa chạy tại thời điểm báo cáo này.

Không nhận đã kiểm native giọng canonical, signed production UI, output
tệp/engine, Safari/thiết bị hoặc toàn bộ accessibility. Chữ kỹ thuật và
giá trị ứng dụng `general` ở vùng khác vẫn thuộc backlog đã ghi nhận.
Goal vẫn mở; `M-FINAL-01..06` luôn làm cuối.
