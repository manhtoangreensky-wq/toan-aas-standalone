# Âm thanh: thông báo cũ và ba thông báo chưa dịch

BASE=3c5d3ca62496126ade250ac78e0cbf3efeb6c79e.
SOURCE_BASE_FOR_INTEGRATION_AND_I18N=cd9c5c14263e1397531056e318a9f46394a8562d.
STATUS=LOCAL_CHECKED_RELEASE_PENDING.

## Thứ tự

Xử lý lỗi tách nhãn/mô tả đã ghi trong checklist trước. Sau đó xử lý
phản hồi lỗi cũ và ba thông báo chưa dịch; không đổi thứ tự chỉ vì đã
có test RED. Các công việc có thể được chuẩn bị song song mà không
ghi lên cùng nguồn hoặc làm thay kết quả worker.

Owner đã xác nhận làm mọi việc trong goal. Phiếu tách dòng R2 được gửi
lại; hai phiếu độc lập cho phản hồi cũ và ba câu thông báo cũng đang
chạy dạng chỉ trả đề xuất, đầy đủ MAP. Root chỉ áp dụng tuần tự sau
khi kiểm tra; không có ứng dụng nào được worker tự ghi.

Hai phiếu phản hồi cũ và locale đã trả đúng ba record theo phiếu. Root
thử riêng hai đề xuất trong bộ nhớ với bundle thật:
16 case hiện tại/cũ theo VI/EN/ZH và lỗi mạng đạt; không thay test trên
nguồn vật lý hoặc CI, không suy rằng đã triển khai. Đơn vị tách dòng
đã được gộp PR789 và triển khai run44941535803; VPS chạy đúng BASE.
Một lượt riêng chín case ứng viên trong bộ nhớ cũng đạt: tám giá trị
không thuộc danh sách dịch giữ nguyên và một lỗi cũ không mở khóa
request mới, trong khi lỗi hiện tại vẫn hiện. Không cộng hai lượt thành
một full run trên nguồn vật lý.

Sau khi PR789 triển khai, Root áp dụng tuần tự đúng ba record vào hai
tệp ứng dụng. Nguồn vật lý BASE+record và 35 kiểm tra mục tiêu PASS.
Hồi quy historical đầu 24 PASS/36 FAIL do phép chiếu cũ chưa nhận
record mới; sau bổ sung phép chiếu hữu hạn, 76 Node PASS và 122 Python
historical PASS. Năm kiểm tra Python mới cũng đạt. Bộ hồi quy rộng ban
đầu 5.015 dòng: 5.014 PASS và một kiểm tra historical của bản visual
cần nhận diện thay đổi mới; sau điều chỉnh đầu vào historical, hai case
liên quan PASS. Đối chiếu theo tệp+tên: 5.132 dòng trừ 74 dòng trùng/
thay thế = 5.058 case phân biệt PASS, 0 FAIL/0 skip, đủ 163 tệp được
chọn. Đây là kết quả ghép nhiều lượt, không phải một full run mới.
Lượt kiểm tra server ban đầu không hoàn thành; chẩn đoán cho thấy
trình kiểm thử bị kẹt tại socket nội bộ khi tạo event loop trong môi
trường hạn chế. Lượt mới với quyền kết nối cục bộ, ENV tiến trình giả,
dotenv tắt và cơ sở dữ liệu riêng đạt 1 PASS trong 4,59 giây: kiểm tra
quyền, revision, lỗi không tìm thấy và không lưu kết quả rà soát. Hai
cảnh báo thư viện được giữ trong log. Không gọi đây là UI production
hoặc kết quả provider.

## 1. Phản hồi lỗi đã cũ

Nhánh `audio-hub-review-pack-compose` kiểm tra route/session/revision
sau phản hồi thành công. Khi `api()` ném lỗi, outer catch hiện thông
báo mà không kiểm lại request còn hiện hành. Trong VM chạy bundle thật,
HTTP giả được giải phóng sau đổi route, đăng xuất, revision, tắt chức
năng hoặc khi có request mới: cả 5 tình huống đều hiện cảnh báo cũ,
trái với yêu cầu im lặng. RED 5/5 assertion, không skip; test giả không
gọi mạng/provider/ví. Không suy rằng các thao tác khác cùng lỗi.

Kiểm tra bổ sung ba tình huống: lỗi request cũ về sau khi request mới
đã thành công và lỗi mạng cũ về sau đổi trang đều vẫn hiện cảnh báo;
lỗi không xác định của request hiện tại vẫn hiện và nút được mở lại.
Kết quả 1 PASS/2 FAIL, không skip. Receipt tách riêng, không cộng thành
một lượt với RED 5/5.
Thêm sáu kiểm tra giữ hành vi hiện có đã PASS: bốn chuỗi không thuộc
danh sách cố định giữ nguyên, một kết quả hiện tại vẫn merge/focus,
và route sai bị chặn trước request. Các kiểm tra này phải giữ đạt sau
khi áp dụng hai đề xuất.

Mục tiêu: lỗi từ request cũ không hiện, không merge, không focus và
không mở khóa request mới; lỗi của request hiện tại vẫn báo bình thường.
Giữ preflight, kiểm tra route/session/revision, thứ tự `finally`, API,
payload, quyền, các action khác và dữ liệu. Không đổi cơ chế đăng nhập.

## 2. Ba câu thông báo

Ba câu cố định từ Web: không tìm thấy bộ sưu tập, revision đã đổi và
tạm dừng để bảo trì. `app.py` đưa lỗi HTTP vào `envelope.message`;
`api()` ném `ok:false`; outer catch của action review đi qua helper
hiển thị hiện có, chưa ánh xạ ba câu đó. Test bundle thật với HTTP giả
cho VI/EN/ZH: RED 9/9 vì còn hiện câu gốc kỹ thuật/sai ngôn ngữ.

Mục tiêu: đúng câu dễ hiểu theo ngôn ngữ, giữ lỗi là lỗi, không đổi
thông tin khách hoặc chuỗi server không biết, không dịch theo substring.
Không đổi backend, API, số lần POST, provider, ví hay dữ liệu.
Kỳ vọng dịch trong test là đề xuất, không phải bản đã phát hành.

## 3. Cổng hoàn thành

- Antigravity nhận phiếu và trả sửa theo phạm vi được duyệt; Root kiểm
  độc lập. Chỉ sửa trực tiếp từng phần sau hai lỗi code thực sự của
  worker cùng phần. Từ chối cấp quyền không tính là lỗi worker.
- Test RED phải chuyển đạt cho cả 5 phản hồi cũ và 9 câu theo locale;
  bổ sung test lỗi hiện tại, success cũ, overlap, unknown/customer text
  và action khác, giữ nguyên dữ liệu cùng kiểm tra bảo vệ.
- Ghi bằng chứng cục bộ, CI và runtime riêng; không đồng nhất merge,
  deploy, UI sau đăng nhập hay kết quả provider.
- Không báo toàn goal hoặc motion hoàn tất khi checklist còn mở.
