# Ba công cụ lập kế hoạch: giao diện thực dụng và luồng lưu

TASK=REMAINING-PLANNER-UI; local accepted, phát hành còn mở.
BASE_SHA=e63f073f460e551438fbb8e3627ec232353f3efe.
Branch: codex/remaining-planner-ui-20261110. Tracker: Issue #689.

## Thay đổi đang được kiểm tra

Ba trang Từ kịch bản đến hình ảnh, Ý tưởng quảng cáo và Bảng phân cảnh bỏ
khối giới thiệu, số đếm trang trí, ô giải thích giới hạn thực thi và đoạn kỹ
thuật ở đầu biểu mẫu. Giữ nguyên 16/10/10 trường, lựa chọn, sự đồng thuận,
kết quả, nút xác nhận lưu và kiểm tra quyền. Không mở tính năng tạo video
chỉ bằng cách bỏ chữ báo khóa. Các công cụ thực sự tạo và lưu kế hoạch văn bản.

Các lỗi hoạt động được phát hiện từ đầu ra bộ tạo kế hoạch và phiên đăng nhập
thật trên máy, không chỉ từ HTML giả định:

- Bộ chuẩn hóa rút gọn làm mất metadata đã kiểm tra, khiến bước kiểm tra tiếp
  theo loại kết quả hoặc biên nhận hợp lệ. Giữ lại đúng metadata đã xác minh;
  không bỏ bộ chuẩn hóa hoặc dựng cờ còn thiếu.
- Trình duyệt không được cấp mã tài khoản nội bộ. Điều kiện phản hồi so sánh
  mã không có nên loại lượt hiện tại. Dùng dấu phiên riêng trong RAM đã có từ
  xác thực, giữ toàn bộ epoch, đường dẫn, điều kiện đăng nhập và bật tính năng.
  Không gửi dấu này như định danh hay quyền trong dữ liệu yêu cầu.
- Ba giá trị số của ô chọn Cinematic được HTML trả về dạng chuỗi. Chuyển đúng
  ba chuỗi thập phân chuẩn trong bộ so khớp biểu mẫu; bộ chuẩn hóa vận chuyển
  vẫn yêu cầu đúng kiểu số và từ chối dữ liệu không hợp lệ.
- Cảnh báo sau khi sửa lựa chọn và thông báo nổi sau tạo/lưu còn trộn ngôn ngữ.
  Sửa chữ hiển thị, giữ lỗi thật, thời gian tự đóng, chống lặp và ARIA.

## Bằng chứng đã có và giới hạn

| Cổng | Kết quả đo được | Giới hạn |
|---|---|---|
|Biểu mẫu|18 lượt dựng; 178 khóa mới mỗi ngôn ngữ; giữ scalar/constraint|Không thay cho thao tác trình duyệt|
|Chữ và an toàn kết quả|150 ca theo sổ:109 giữ,41 sửa;44 lượt kiểm phần chữ/catalog đạt|Chỉ chữ cố định; không dịch dữ liệu khách|
|Metadata|36 ca và3 bộ kiểm kết quả thực đạt|Không bỏ normalization/source match|
|Dấu phiên|30/30 đạt|Không chứng minh đăng nhập production hay quyền máy chủ|
|Biểu mẫu Cinematic|RED29/30, GREEN30/30|Chuỗi sai, lựa chọn đổi và action sai vẫn bị chặn|
|Cảnh báo chỉnh sửa|RED0/15, GREEN15/15|R2 trả lại đúng tên dataset bị worker đổi ngoài phạm vi|
|Catalog gốc|9951 giá trị/locale giữ nguyên,6 ca catalog cuối đạt|Khóa mới được kiểm riêng, không miễn kiểm giá trị cũ|
|Python nguồn|25/27 đạt ban đầu;1 kỳ vọng chữ đã cập nhật và ca đó đạt|1 phép dò menu đã fail giống BASE; không đổi menu để ép xanh|
|Python backend rộng|Hai lượt giới hạn240giây chưa hoàn tất; lượt sau87 dấu đạt|Không báo cả suite PASS; mã backend không đổi|
|Native đầu tiên|Một view ScriptVI320:16trường/font/focus/khung đạt,2compose thật|Dừng trước lưu; phát hiện toast và khác biệt chữ hoa do CSS trong harness|
|Toast thao tác|138 ca sửa đạt+15unknown/dedupe giữ=153;46 câu/8 key mỗi locale|Không giấu lỗi; câu lạ giữ nguyên|
|Native cuối|18/18 view,9/9 luồng;18compose+9save,đọc/mở9plan/42scene|320tối thao tác thật,1440sáng ban đầu,VI/EN/ZH;không fullcrossedthemes|
|Native đọc được|162/162 mẫu tương phản sáng đạt,min5,7971:1;mobile>=16px,54ảnh|Focus/nhãn/khung/console đạt;không thiết bị thật/Safari|
|Cô lập|SQLitequick_checkok;9plan/42scene/phiên bản đúng;0egress/provider/ví|Không dữ liệu production;server/browser do runner mở đã đóng|

R1 operation-feedback chưa áp dụng vì phiếu của điều phối trích thừa sáu câu
Motion và thiếu thông báo máy chủ. R1A thay đúng danh sách; không tính lỗi
phiếu cho Antigravity. Worker tự tick kiểm thử không được chấp nhận làm bằng chứng.

Tổng398khóa mới mỗi locale (178field+208outer/result+4feedback+8operation),
9951giá trị cũ giữ nguyên. Bộ dựng gắn namespace đã quy định cho tám category
key ngắn worker trả về; không đổi giá trị dịch hay fragment code nào.
Source comparator phục hồi mọi byte Portal ngoài23hàm cho phép; integration
khớp đúng hunk worker đã review,14tệp nhạy cảm giữ nguyên;CSSđúng3rule.
Artifact native:remaining-planner-final-native-nov10-batch-b/summary.json,
isolation.json và54ảnh;source trước/sau không đổi. Không chạy lại các flow
đã đạt sau cập nhật tài liệu.

## Trước khi đẩy và phát hành

Phiên kiểm thử riêng: `KIEM-THU/PHIEN-REMAINING-PLANNER-20261110.md`.
Tài liệu vận hành và đối chiếu chức năng gốc cập nhật theo kết quả cuối.
CI chạy kiểm tra mới; provenance sinh sau commit source/docs và kiểm tại HEAD.
Merge đúng HEAD đã đạt, deploy đúng merge SHA, rồi đối chiếu runtime, dịch vụ
và từng asset HTTPS riêng. Không suy LIVE từ CI, dịch vụ active hoặc HTTP200.

Toàn goal vẫn mở: hai công cụ video còn lại, nội dung máy chủ/trang kế hoạch
đã lưu, khối thừa ở các trang khác, responsive/AX/bàn phím/phục hồi/đăng nhập,
thiết bị và motion cuối. Production browser đang bị tắt trong Work settings;
không đổi cài đặt hoặc dùng đường vòng.

PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_MUTATIONS=0.
DEPLOY=NOT_YET; LIVE_PASS=NOT_TESTED; LESSON_CANDIDATE=NONE.
