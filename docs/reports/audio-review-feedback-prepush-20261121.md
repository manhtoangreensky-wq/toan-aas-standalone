# Trước phát hành — rà soát bộ sưu tập âm thanh

TASK=AUDIO-REVIEW-FEEDBACK-20261121.
BASE=7cb8cb10486f5c175dca5db2c286a9f93a133c23.
BRANCH=codex/audio-review-feedback-20261121.
TRACKER=Issue689/comment7062778377.
PUSH_GATE=FINAL_MANIFEST_AND_CI_PENDING.

Tài liệu vận hành và đối chiếu chức năng gốc đã được bổ sung; tám case
ARF có nguồn duy nhất và phiên kiểm tra riêng. Dùng tracker và mẫu có
sẵn, không tạo thẻ giữ chỗ. Phiếu worker không chứa dữ liệu khách,
thông tin đăng nhập hoặc cấu hình bí mật.

Review gộp 11 record/3 tệp ứng dụng; 151 nguồn/148 bảo vệ/21 hàm
được đối chiếu. Node ledger 5.002 unique PASS/158 tệp; Python historical
95 PASS; portal-contract 3 PASS/1 lỗi literal cũ trùng exact BASE.
Native run03 6 view/6 metadata POST/12 ảnh giải mã, 0 domain writes,
provider, ví, egress sai và tiến trình còn chạy. Hash và kích thước 12
ảnh cùng 80 receipt Node đã được đối chiếu lại.

Chỉ công bố các tệp ứng dụng, kiểm tra và tài liệu trong phạm vi ARF;
mọi `.agents/state/**` bị loại trước khi đọc, quét nội dung hoặc stage.
Manifest, kiểm tra bí mật, CI, merge, deploy, VPS và receipt sau phát
hành vẫn phải được xác minh riêng. Không suy signed UI hoặc đầu ra
âm thanh từ HTTP 200 hay hash asset. Ba visual followup được đưa vào
đầu hàng đợi tiếp theo; goal chưa hoàn tất.
