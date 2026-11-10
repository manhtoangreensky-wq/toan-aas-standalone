# Phiên kiểm thử — xác nhận lưu kế hoạch và lựa chọn, 10/11/2026

SESSION_ID=VIDEO-PLAN-CONFIRMATION-20261110.
BASE_SHA=b5410b5e587337f0d050e70d1a92fcaff85adc17. Theo dõi: Issue #689.

| Ca | Kết quả cần có | Bằng chứng đã đạt |
|---|---|---|
| PLAN-CONFIRM-01 | Tạo -> xác nhận -> lưu -> đọc lại -> bấm mở kế hoạch đúng tài khoản | 12/12 native, đúng UUID/phiên bản1/3cảnh; DBtạm12kếhoạch/36cảnh |
| PLAN-GUARD-02 | Không hiện thành công từ phản hồi sai hoặc thiếu quyền; không lưu trùng đang chờ | 84/84 thực thi handler thật, gồm51phản hồi sai và quyền/khóa gửi lặp |
| PLAN-COMPOSE-03 | Chấp nhận đúng câu cấm cố định trong kết quả, không miễn kiểm tra nội dung nguy hiểm | 108/108; đầu vào và21vị trí khác vẫn bị chặn |
| MOTION-OPTIONS-04 |19nhãn đúng VI/EN/ZH;9/3/7mã, mặc định, scalar và quyền giữ nguyên |15/15renderer;24/24native |
| MOTION-NAME-05 | Tên dài hiện đầy đủ khi cần, tên ngắn không có dòng thừa; giữ ô chọn chuẩn |20/20helper;28/28dòng cần hiện;24trạng thái ngắn không để dòng |
| MOTION-READ-06 |320/390/414/1440 sáng/tối: ô trong khung, font/target/contrast đạt |24/24; tương phản thấp nhất5,5253sáng/5,5225tối |
| PLAN-REGRESSION-07 | Không đổi bản dịch cũ, dữ liệu, xử lý máy chủ hoặc tiền |332/332focused;2256/2256Node; review0Critical/Important |
| PLAN-DELIVERY-08 | CI đúng mã; merge/deploy/runtime/tệp thực tế được đối chiếu riêng | Chờ phát hành |

Các kiểm tra mới nằm trong năm tệp `tests/video-*.test.mjs` tương ứng receipt,
options, confirmation-flow, compose-guard và selected-name. Không chạy lại các
cổng local trên mã không đổi; chỉ dùng lại receipt/SHA theo quy tắc Owner.

Hai quan sát còn mở, không tính là đã sửa: một lần chủ đề rỗng chưa rõ nguyên
nhân (không tái hiện trong12ca trace cuối), và hai vị trí trước bấm có thanh
điều hướng che tâm nút nhưng bấm bình thường vẫn mở được kế hoạch.

TESTER_PROJECT_STATUS=READY; RELEASE_STATUS=LOCAL_ACCEPTED_CI_PENDING.
Không dùng dữ liệu khách, không provider/ví/production; chưa chứng minh toàn
trang đã dịch hết, thiết bị thật hoặc độ mượt chuyển động.
