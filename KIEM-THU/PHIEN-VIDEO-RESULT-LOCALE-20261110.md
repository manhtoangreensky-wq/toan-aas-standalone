# Phiên kiểm thử — chữ trong kết quả kế hoạch video, 10/11/2026

SESSION_ID=VIDEO-RESULT-LOCALE-20261110.
BASE_SHA=dac863c9796cc4ef7b077d65579a70300b6d4cc7.
Theo dõi: Issue #689. Không tạo lại bảng công việc hoặc các ca lịch sử.

Phạm vi: khối kết quả hướng dẫn chuyển động và kế hoạch video dài; VI/EN/ZH;
điện thoại/máy tính; sáng/tối. Không bao gồm phần biểu mẫu bên ngoài khối kết quả.
Không dùng dữ liệu khách thật, không bấm tạo nội dung hoặc lưu trên production.

| Ca | Kết quả bắt buộc | Bằng chứng hiện có |
|---|---|---|
| RESULT-LOCALE-01 | Tên mục, hướng dẫn, cảnh báo dữ liệu cũ, trạng thái rỗng và xác nhận lưu bên trong hai kết quả đúng ngôn ngữ | 45/45 kiểm thử dựng giao diện qua bộ chuẩn hóa thật |
| RESULT-DATA-02 | Tên riêng, Facebook/TikTok, chữ khách viết, thời gian và tỷ lệ không bị dịch hoặc đổi | Cùng bộ 45 ca; dữ liệu gốc giữ nguyên |
| RESULT-GUARD-03 | Nguồn khớp mới có nút lưu; thiếu quyền thì vô hiệu; nguồn không khớp không có nút | Cùng bộ 45 ca, đủ ba trạng thái lưu |
| RESULT-CATALOG-04 | Không đổi các bản dịch cũ hoặc 178 khóa không gian video | 9.266 mục cũ mỗi ngôn ngữ giữ nguyên |
| RESULT-WRAP-05 | Đọc hết mô tả trên điện thoại, giữ xuống dòng và chuỗi dài không dấu cách | Đạt: ca 390px từ sáu ô tràn về 0; ma trận bổ sung 24/24, 12 ca di động giữ nguyên 321 ký tự và xuống dòng |
| RESULT-REGRESSION-06 | Không đổi chức năng, đường dẫn hoặc phần ứng dụng ngoài phạm vi | Review độc lập đạt; Node 1.969/1.969; Python 24 đạt và một lỗi kỳ vọng nguồn cũ giống BASE |
| RESULT-DELIVERY-07 | CI đúng mã; merge, deploy, phiên bản máy chủ và tệp thực tế được đối chiếu riêng | Chưa phát hành |

Lệnh chạy lại: `node --test tests/video-planning-result-locale.test.mjs`.
Kỳ vọng: 45 đạt, 0 lỗi. Chỉ lệnh này xanh không thay nghiệm thu trình duyệt.

TESTER_PROJECT_STATUS=READY_FOR_TARGETED_REPLAY.
RELEASE_STATUS=LOCAL_GATES_ACCEPTED_CI_PENDING.
Trình duyệt: 48 lượt đo, 42 tổ hợp khác nhau; 0 ô mô tả bị cắt, lỗi trang,
yêu cầu ngoài máy này hoặc ghi sản phẩm. Ma trận tổng hợp dùng một quan sát
chỉ-đọc để chờ tiến trình nạp ban đầu trước khi đặt dữ liệu tổng hợp.
Không công nhận toàn bộ ứng dụng đã hết chữ sai ngôn ngữ hoặc hết giật từ phiên này.
