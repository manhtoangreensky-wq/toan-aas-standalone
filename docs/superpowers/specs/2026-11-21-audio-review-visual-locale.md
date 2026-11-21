# Đường dẫn và số lượng tệp trong bản rà soát âm thanh

BASE=ea4da7c446059f911f3b59d61f9f92f63ea95c94.
BRANCH=codex/audio-review-visual-20261121.
STATUS=LOCAL_TESTS_PASS_RELEASE_PENDING.

Ảnh của PR787 cho thấy đường dẫn ở trang chi tiết còn “Audio Production
Hub” khi chọn VI/ZH, và tiếng Anh hiện “1 reference files”. Hai lỗi này
được tách khỏi lỗi nhãn/mô tả dính liền để có thể xử lý riêng.

Phạm vi: breadcrumb của riêng `audio-hub-detail` dùng khóa tên trung tâm
đã có; số lượng tham khảo hiển thị số ít tiếng Anh khi bằng 1, số nhiều
ở 0 và 2, VI/ZH giữ nguyên. Không đổi route, quyền, receipt, dữ liệu,
API, engine, ví hoặc motion. `summary.total` chỉ được đọc một lần tại
đúng nhánh có receipt như trước.

Antigravity breadcrumb R1 trả một record đúng. Số ít R1 đọc `total` hai
lần; R2 chuyển lần đọc ra trước nhánh receipt. Cả hai không đáp ứng
yêu cầu giữ cách đánh giá dữ liệu, nên Root sửa trực tiếp đúng biểu
thức sau hai lỗi cùng phần; không tính lỗi QA là lỗi worker.

RED 12 ca: ba lỗi đúng mục tiêu (VI/ZH breadcrumb, EN số ít). GREEN
17 ca gồm 12 tình huống ba ngôn ngữ × số lượng, hai đối chiếu toàn
nguồn BASE+record và ba kiểm tra compatibility catalogue; 0 FAIL.
Historical Node 70 PASS; một lượt khác 96 ca có 24 FAIL do Root QA
giả định sai thứ tự khóa catalogue, được sửa tại QA và 26 ca liên quan
PASS. Python historical 95 PASS và hai pressure mới PASS.
Không cộng trùng các lượt hoặc gọi đây là full CI.

Nguồn hiện tại được so nguyên tệp với BASE cộng đúng ba record;
historical projection chỉ phục vụ kiểm tra các bản trước, không thay
kiểm tra forward hiện tại. Bản này chưa có chứng cứ signed production
UI; CI/merge/deploy và kiểm tra runtime cần xác nhận riêng.

Lỗi nhãn/mô tả dính liền vẫn mở. Đề xuất Antigravity R1 chọn sai vùng;
R2 đã được chuẩn bị nhưng hệ thống duyệt tự động chặn gửi vì packet
chứa MAP nội bộ. Không tự sửa phần này khi worker mới sai một lần.
Sau đó tiếp ba shared-backend message và generic validity; motion cuối.
