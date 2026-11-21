# Kiểm tra phản hồi lỗi rà soát âm thanh

BASE=3c5d3ca62496126ade250ac78e0cbf3efeb6c79e.
STATUS=LOCAL_CHECKED_RELEASE_PENDING.
Nguồn case: `DANH-SACH-CASE.md`, nhóm AUDIO-REVIEW-CURRENT-ERRORS.

| Case | Bằng chứng cục bộ |
|---|---|
| ARE-CURRENT | Các phản hồi cũ sau đổi trạng thái/overlap không hiện; yêu cầu hiện tại vẫn hoạt động |
| ARE-LOCALE | Ba câu × VI/EN/ZH, lỗi vẫn là alert |
| ARE-PRESERVE | Unknown/customer, success/focus, route sai và số POST |
| ARE-SOURCE | Toàn hai tệp bằng BASE của nội dung đó cộng ba record đã duyệt |
| ARE-REGRESSION | 5.058 unique Node PASS/163 tệp; Python historical122+5 PASS; server riêng 1 PASS |
| ARE-DELIVERY | CI, merge, deploy, VPS và signed UI cần xác nhận |

RED ban đầu: 14 lỗi ở ba câu và phản hồi cũ; kiểm tra bổ sung hai lỗi
cũ/1 hành vi hiện tại đạt. Sau sửa, 35 case mục tiêu đạt. Hồi quy rộng
5.015 dòng có một lỗi so nguồn historical; sau cập nhật đầu vào và chạy
lại phần liên quan, ledger 5.058 tình huống phân biệt PASS/0 FAIL.
Không gọi ledger là một lượt chạy mới.

Một lượt server đầu bị kẹt khi môi trường tạo socket nội bộ; lượt
sau với quyền kết nối cục bộ và dotenv tắt đạt 1 PASS trong 4,59 giây.
Không dùng dữ liệu khách hoặc gọi provider/ví. Signed production UI,
toàn accessibility, motion và audio đầu ra chưa được chứng nhận.
