# Trước phát hành — phản hồi lỗi rà soát âm thanh

BASE=3c5d3ca62496126ade250ac78e0cbf3efeb6c79e.
STATUS=LOCAL_CHECKED_RELEASE_PENDING.

Hai phiếu Antigravity R1 trả đúng ba record trên `integration.js` và
`portal-i18n.js`: im lặng khi phản hồi lỗi thuộc request đã cũ, và
dịch đúng ba thông báo cố định. API, backend, quyền, receipt và thông
tin khách giữ nguyên. Đối chiếu toàn nguồn với BASE cộng ba record đạt.

Kiểm tra cục bộ: 35 case mục tiêu, 76 Node historical, 122 Python
historical và 5 Python pressure đạt. Hồi quy rộng có một assertion
historical cần cập nhật đầu vào; sau chạy lại phần liên quan, ledger
5.058 case Node phân biệt đạt, bao phủ 163 tệp. Một ca server trên
dữ liệu riêng đạt; lượt đầu bị chặn socket nội bộ không tính là PASS.

Đã bổ sung tài liệu vận hành, đối chiếu chức năng và sáu case tester.
Manifest/secret, provenance, CI, merge, deploy và runtime là các cổng
riêng cần xác nhận trước khi nhận phần này đã giao. Signed production
UI và toàn bộ goal chưa được chứng nhận.
