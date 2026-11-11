# Trước phát hành — MEMBERSHIP-PLAIN-LANGUAGE-20261111

BASE: `e2afca85d96ed6a19c941924e5344ea40869cfac`.
Repo: `manhtoangreensky-wq/toan-aas-standalone`; Issue #689.

## Review và đối chiếu

Ứng dụng chỉ sửa ba tệp: bốn text node của banner, nhãn gói công bố riêng và
bỏ một render danh sách ghi chú tĩnh trong renderer Hội viên; 14 khóa dịch và
năm khóa mới; CSS chỉ callout Hội viên/CTA trong đó. Không sửa helper chuẩn
hóa, manifest, logic quyền lợi/giá/số dư, API/auth, backend, dữ liệu khách,
ENV/schema, provider/Bot hoặc motion. Nhãn catalog dùng chung giữ nguyên.

Tài liệu vận hành và đối chiếu chức năng ban đầu tiếp tục được cập nhật tại
`TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md` và `02-CHUC-NANG-GOC-VA-HIEN-TAI.md`.
Không dựng lại danh sách chức năng hoặc tuyên bố toàn app đã hoàn tất locale.

## Tester

TESTER_PROJECT_ID=MEMBERSHIP-PLAIN-LANGUAGE-20261111.
TESTER_PROJECT_STATUS=READY.
Nguồn ca: `KIEM-THU/DANH-SACH-CASE.md`, MPL-COPY đến MPL-REGRESSION.
Phiên độc lập: `KIEM-THU/PHIEN-MEMBERSHIP-PLAIN-LANGUAGE-20261111.md`.
Builder chỉ trả đề xuất; nghiệm thu dựa vào renderer thật, UI native và terminal.

## Kết quả có bằng chứng

- 12 ca dữ liệu/locale qua RED → GREEN, giữ custom technical words trong dữ liệu.
- 556 ca Node hồi quy đạt; sau sửa màu cuối chỉ 67 ca ảnh hưởng chạy lại, đều đạt.
- 5 ca Python/metadata đạt; siêu dữ liệu ca kiểm tra đo lại theo UTF-8/LF.
- 12 view sáng/tối390/1440, ba locale, 240 mẫu màu trên năm trạng thái;
  min5,216649621048673:1, không mẫu không xác định, không lỗi/tràn ngang.
- Ba lượt rời trang giữ layout cũ; bản ghi kế hoạch/cảnh sao chép, bằng chứng gốc và source không đổi trong
  chạy, không product/wallet/production write, provider call hoặc tiến trình sót.

Các lượt thiếu tương phản bị từ chối trước phát hành; sửa đúng phần tối và giữ
bằng chứng phần không đổi. Chưa merge/deploy trong thời điểm viết báo cáo.

PUSH_GATE=READY đúng phạm vi này. Chỉ gộp khi CI đúng HEAD đạt; sau đó triển khai
đúng merge SHA và đối chiếu runtime/asset. Signed production/device/Safari,
đầu ra provider và motion không suy ra từ local hay CI.
