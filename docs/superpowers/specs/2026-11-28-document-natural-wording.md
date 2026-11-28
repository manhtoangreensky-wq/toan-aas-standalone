# Lời dễ hiểu cho phần chuẩn bị tài liệu

## Yêu cầu và phạm vi

Owner: “tuyệt đối không có 1 từ kỹ thuật nào, phải cho câu từ hết sức tự nhiên … QA … là cái gì xóa hết làm lại câu từ bình thường cho khách dùng thấy đỡ rối”.

BASE `cf94b23e6a26010e88ebcd33b36623204c784c9a`; nhánh
`codex/auth-draft-isolation-20261128`; kho
`manhtoangreensky-wq/toan-aas-standalone`; sổ theo dõi duy nhất Issue #689.

Chỉ sửa chữ cố định khách nhìn thấy ở `/document-workspace`, `/new` và
trang chi tiết, gồm tiêu đề, biểu mẫu, lựa chọn, lời nhắc và thông báo.
Giữ nguyên các điều kiện, quyền, đường dẫn, thuộc tính điều khiển, dữ liệu,
trạng thái, giới hạn nhập, cách lưu và chức năng. Không dịch nội dung khách.
Tên riêng và định dạng tệp quen thuộc như PDF, Word được giữ.

Nguồn đã quan sát: chạy renderer thật với từ điển cuối cho tiếng Việt.
Trang danh sách hiện “QA checklist”, “processing plan”, “metadata”,
“signed account”, “CSRF”, “owner-check”; biểu mẫu và lời nhắc cũng còn
chữ pha tiếng Anh. Không dùng việc tìm chuỗi đơn thuần để kết luận màn
hình khác có lỗi. Các chuỗi chết và khóa nội bộ không đổi.

## Bảng công việc theo thứ tự

| Mục | Kết quả cần đạt | Phụ thuộc | Trạng thái |
|---|---|---|---|
| DOC-PLAIN-FORM | Danh sách, trường nhập, lựa chọn, tiêu đề dùng lời tự nhiên VI/EN/ZH | Nguồn hiện tại và bộ kiểm tra | Đã kiểm tại máy |
| DOC-PLAIN-DETAIL | Chi tiết, lịch sử, thao tác, hướng dẫn mở công cụ dùng lời tự nhiên | Cùng nguồn; đề xuất riêng | Đã kiểm tại máy |
| DOC-PLAIN-FEEDBACK | Lỗi nhập và thông báo của phần tài liệu không lộ từ nội bộ | Cùng nguồn; đề xuất riêng | Đã kiểm tại máy |
| DOC-PLAIN-READ | Lời nhắc khi tìm/làm mới và phản hồi từ máy chủ dùng lời tự nhiên, giữ nguyên kết quả thật | Không sửa trùng ba phiếu đầu | Đã kiểm tại máy |
| DOC-PLAIN-CHECK | Rà gộp bốn đề xuất; chữ, dữ liệu và điều khiển không sai | Bốn đề xuất đã về |34raw/176Node/9Python;review đạt |
| DOC-PLAIN-DELIVERY | Cập nhật tài liệu, kiểm tra, đưa lên web và đối chiếu | Kiểm tra gộp đạt | Đang chuẩn bị;chưa đưa lên web |

Bốn phiếu độc lập chỉ trả đề xuất trong bốn thư mục riêng, không ghi chung
mã ứng dụng. Antigravity dùng `gemini-4-hydrogen-xhigh`, phiên hiện có;
không kiểm tra tài khoản, đăng nhập lại hoặc đổi cài đặt. Người điều phối
ghép và kiểm tra một lần cho mỗi nhóm đã xong. Nếu cùng tiêu chí sai hai
lượt thì mới tự sửa đúng chỗ sai.

## Câu chữ đích

- document brief → yêu cầu tài liệu.
- processing plan → bước xử lý.
- QA/self-review → rà soát.
- metadata/reference → thông tin/tệp đã chọn, theo ngữ cảnh.
- draft/archive/revision → bản nháp/lưu trữ/phiên bản.
- Nội dung hướng dẫn nói điều khách làm được, không giảng cách hệ thống chạy.
- Giữ lời giới hạn đúng sự thật: ở đây chỉ lưu yêu cầu và bước chuẩn bị;
  muốn tách/gộp/chuyển tệp phải mở công cụ tương ứng, chọn lại tệp.
- Không đổi trạng thái chưa làm thành thành công, không làm nút khóa hoạt động.
- Không xóa hướng dẫn bắt buộc, lời xác nhận, giới hạn riêng tư hoặc yêu cầu đăng nhập.

## Tiêu chí và bằng chứng

- [x] AC1: Danh sách, tạo mới, thiếu quyền, thiếu bản ghi và bốn trạng thái
  chi tiết không còn từ triển khai trong chữ cố định; bằng chứng renderer
  VI/EN/ZH và ảnh xem trực tiếp.
- [x] AC2: Nhãn, ví dụ nhập, trợ giúp, lựa chọn và lời xác nhận đúng ngôn ngữ;
  dữ liệu khách có chữ giống thuật ngữ vẫn nguyên vẹn và được hiển thị an toàn.
- [x] AC3: Thuộc tính điều khiển, trạng thái khóa, thứ tự nút, đường dẫn,
  tên trường, giá trị lựa chọn và nội dung đầu vào không đổi; so sánh với BASE.
- [x] AC4: Kiểm tra đầu vào vẫn chấp nhận/từ chối đúng như trước;
  thông báo lỗi tự nhiên; không có yêu cầu mạng mới.
- [x] AC5: Khóa dịch cũ không đổi; khóa mới đủ VI/EN/ZH, không trùng,
  được thêm trước kiểm tra và đóng băng từ điển.
- [ ] AC6: Kiểm tra liên quan, cú pháp, tài liệu bàn giao và bằng chứng phát hành.

Mọi thay đổi ngoài các đoạn chữ đã giao phải bị từ chối. Bot, bộ tạo nội dung,
tiền, nạp/rút, dữ liệu thật, bảo mật, môi trường và chuyển động đều được giữ.
Sáu tài liệu về bản nháp giọng đọc/âm nhạc đang chưa ghi nhận vẫn được giữ
riêng, không được coi là sản phẩm của bốn phiếu này.

## Phụ lục phản hồi

Kiểm tra mã nguồn tiếp theo cho thấy lời nhắc tìm/làm mới nằm trước đoạn
tạo yêu cầu; đồng thời lời báo từ máy chủ được ưu tiên hơn câu dự phòng.
Vì vậy bổ sung DOC-PLAIN-READ trước khi ghép thay đổi, không chấm lỗi phiếu
FEEDBACK vì phiếu đó đã yêu cầu giữ nguyên thứ tự ưu tiên. Chỉ bản sao
phục vụ hiển thị được đổi `message`; kết quả trả về, nội dung `.data`,
chi tiết lỗi, trạng thái, giới hạn và mọi yêu cầu gửi đi vẫn nguyên vẹn.
Không thay kết quả chưa thành công thành thành công.

## Phụ lục sau khi rà gộp đề xuất đầu

- Đã chạy 34 ca trên bản ghép riêng, chưa sửa mã ứng dụng: 7 đạt, 27 chưa
  đạt. Sáu ca phản hồi còn chờ READ; nhãn tìm kiếm cũng thuộc READ.
- Tên phần ở đầu trang chi tiết lấy từ `supportTicketHeroSection`, không
  thuộc hai đoạn đổi tiêu đề đã giao. Bổ sung đúng một nhánh riêng cho
  trang yêu cầu tài liệu; không sửa nhãn hoặc cách hoạt động trang khác.
  Đây là thiếu phạm vi của người giao, không chấm lỗi cho người nhận.
- Kiểm tra chữ đã chặn nhầm từ tiếng Anh thông thường “processing” khi đi
  cùng “steps”. Chỉ cấm cụm tên nội bộ “processing plan”; vẫn cấm pha
  tiếng Anh trong chữ cố định tiếng Việt. Không bỏ các kiểm tra điều khiển,
  quyền, dữ liệu khách hoặc từ nội bộ khác.
- Tương tự, “signed in” là lời đăng nhập tiếng Anh thông thường và
  “content and scope” là nhãn phạm vi tài liệu; chỉ chặn tên triển khai
  “signed session/account”. Cả “scope”, “signed”, “processing” vẫn bị chặn
  khi lẫn vào câu tiếng Việt. Không tính lỗi bộ kiểm tra này cho người nhận.
- “Target format” cũng chỉ bị coi là chữ pha khi ở câu tiếng Việt; trong
  biểu mẫu tiếng Anh đây là định dạng tệp khách muốn nhận, không phải tên
  nội bộ. Bộ chặn từ triển khai còn lại và kiểm tra dữ liệu/điều khiển giữ.
- Lời mô tả công cụ phải khớp giới hạn thật: tách một trang/dải liên tiếp
  thành một PDF mới; nén khi có thể; PDF sang Word chỉ chuyển phần chữ có
  thể chọn, không đọc chữ trong ảnh hoặc giữ nguyên cách dàn trang.
- Đổi nốt câu “mã kỹ thuật hệ thống” thành lời chỉ dẫn nhập yêu cầu thông
  thường. Trạng thái đã rà soát không được diễn đạt thành chứng nhận nội
  dung đầy đủ hoặc đúng sự thật.

DOC-PLAIN-READ lượt đầu trả về chưa làm vì người giao thiếu danh sách chính
xác các thao tác lưu. Đã bổ sung đủ mười tên thao tác, câu báo tương ứng
và cấu trúc kết quả/lỗi đang dùng cho lượt hai. Không có thay đổi mã từ
lượt một và không tính đây là lỗi người nhận việc.

PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_WRITES=0.
LESSON_CANDIDATE=NONE.

## Kết quả đo cuối tại máy

60record/304khóa mới/912giá trị VI/EN/ZH, ba tệp ứng dụng.
34raw primary đạt; hai reader lịch sử và bộ pressure mới176/176đạt.
Python9ca theo failed-only ledger:5đạt ban đầu, đúng4ca hồi phục4/4đạt.
12lượt trình duyệt và2lượt VI tối; phạm vi/giới hạn ảnh ghi ở manifest.
Rà tĩnh độc lập0finding; cú pháp/compile/diff-check mã0.
Các kiểm tra lịch sử chỉ dùng inverse hữu hạn; raw primary không dùng.
Không có phát hành mới hoặc bằng chứng phiên production ở mốc này.
