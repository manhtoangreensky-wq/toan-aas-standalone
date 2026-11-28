# Phiên rà soát lời hướng dẫn tài liệu

ID=DOCUMENT-NATURAL-20261128; product=standalone WebApp;
repo=manhtoangreensky-wq/toan-aas-standalone; Issue689;
branch=codex/auth-draft-isolation-20261128;
BASE=cf94b23e6a26010e88ebcd33b36623204c784c9a.

## Phạm vi và kết quả đã đo

Ba tệp ứng dụng: portal.js, integration.js, portal-i18n.js. Bốn phiếu
Antigravity4ExtraHigh chỉ trả đề xuất, không ghi chung ứng dụng. Tổng
60 record ghép đã kiểm; 304 khóa mới, đủ 912 giá trị VI/EN/ZH. Không đổi
khóa cũ. Root không tự viết logic ứng dụng.

| Case | Bằng chứng thực tế |
|---|---|
| DOC-WORDING | Raw renderer/validator/API helper:34/34 đạt,0lỗi |
| DOC-CONTROLS | Cùng34ca: tên trường/giá trị/giới hạn/nút/quyền/route/dữ liệu khách giữ |
| DOC-REPLY | Cùng34ca: chỉ lời hiển thị đổi, result/data giữ đúng đối tượng; lỗi409 giữ payload/status |
| DOC-LOCALES | VI/EN/ZH danh sách/tạo/thiếu quyền/thiếu bản ghi/bốn trạng thái chi tiết |
| DOC-HISTORY |176/176 Node:160ca hai reader cũ và16ca inverse hữu hạn mới |
| DOC-PYTHON | Nhóm9:5đạt trước; đúng4ca phụ thuộc chữ cũ được sửa input hữu hạn rồi4/4đạt |
| DOC-BROWSER |12lượt render thật/styles thật qua HTTP cục bộ,390/1440VI/EN/ZH; chọn loại và gõ chữ giữ |
| DOC-VI-DARK |2lượt biểu mẫu VI390 với đúng thuộc tính nền tối;0lỗi; đã xem ảnh |
| DOC-REVIEW | Rà tĩnh độc lập:0finding Critical/Important/Minor; không chạy lại tests |
| DOC-DELIVERY | Chưa CI/merge/deploy đợt này; chỉ tick khi có bằng chứng riêng |

Node kiểm p5-p6 và menu khách cũng đạt trong nhóm đầu; không đo riêng tổng
số của hai tệp, không cộng thành tổng kiểm thử toàn ứng dụng.
Cú pháp ba JS, py_compile app.py và ba tệp Python liên quan, git diff
--check đều mã0. Có cảnh báo Pydantic cũ, không sửa cấu hình ngoài phạm vi.

## Giới hạn của ảnh và thử trên máy

Chỉ renderer và kiểu dáng vật lý được phục vụ qua HTTP cô lập. Không phải
phiên khách đã đăng nhập trên production, không thực hiện gửi/lưu trên máy
chủ thật hoặc tạo tệp. Lượt12đầu có wrapper đặt nhầm thuộc tính nền và ảnh
toàn trang gặp vùng cuộn; không dùng làm bằng chứng màu/tương phản/toàn
trang. Chỉ sửa công cụ kiểm tra, rồi lấy đúng2ảnh VI tối; không sửa CSS app.

Không sửa nội dung khách, engine/Bot, xác thực, quyền, ví, nạp tiền, API
máy chủ, cấu hình, dữ liệu thật hoặc chuyển động. Không đổi nút khóa thành
nút dùng được, không nói lưu kế hoạch là tạo tệp kết quả.

## Lịch sử cần giữ

READ lượt1 chưa làm vì phiếu thiếu danh sách chính xác10thao tác; lượt2
được bổ sung, không tính lỗi worker. Các phụ lục về tên đầu trang chi tiết
và giới hạn công cụ là thiếu context của Root. Bộ dò chữ ban đầu chặn nhầm
tiếng Anh thông thường đã sửa đúng theo ngôn ngữ; không nới kiểm tra dữ
liệu/nút/quyền. Các lượt thất bại vẫn giữ, không đổi thành PASS.

Inverse chỉ dành cho đầu vào kiểm tra lịch sử, dùng60record và304giá trị
đúng hash; thiếu/đổi/lặp bị từ chối, nội dung lạ được giữ. Raw primary đọc
ứng dụng hiện tại, không gọi inverse. Không sửa fixture/hash/assertion cũ.

LOCAL=TARGETED_PASS; DELIVERY=PENDING; LIVE_PASS=NOT_TESTED;
PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_WRITES=0.
Toàn goal vẫn mở, chuyển động giữ bước cuối.

Metadata Tester có32PASS/1FAIL chỉ ở chế độ quyền tệp POSIX trên Windows.
Frozen BASE tái hiện đúng1FAIL/0666 thay0600; nguồn test và script sync
không đổi. Không tính lỗi này thành hồi quy ứng dụng, không bỏ test và
vẫn yêu cầu Linux CI đạt. Chốt hash tài liệu được đo lại sau phụ lục này.
