# Nội dung kế hoạch do máy chủ sinh ra — nghiệm thu ngôn ngữ

TASK=VIDEO-OUTPUT-COPY; LOCAL_ACCEPTED; delivery pending.
BASE_SHA=1b76f75d952fc5457458acc9030501139c6e0984.
Branch: codex/video-output-copy-20261111. Tracker: Issue #689.

## Kết quả người dùng nhìn thấy

Hai công cụ chuyển động ảnh và định dạng tham chiếu không chỉ dịch nhãn giao
diện: các tiêu đề, hướng hình ảnh, góc quay, chuyển cảnh, âm thanh, ghi chú và
danh sách rà soát do máy chủ tạo cũng theo ngôn ngữ nội dung đang chọn.
Tên/chủ đề/khán giả do khách nhập giữ nguyên; không thay từ bên trong dữ liệu khách.

Image Motion dùng mã ngôn ngữ vi/en/zh có sẵn trong định hướng ảnh. Giá trị
khác giữ nguyên ở dữ liệu tham chiếu và kế hoạch; chỉ chữ hệ thống dùng bản
dự phòng tiếng Việt, không tuyên bố hỗ trợ ngôn ngữ chưa có. Reference Format
giữ đúng lựa chọn vi/en hiện tại, không thêm zh vào schema hoặc giao diện.
Ngôn ngữ giao diện và ngôn ngữ nội dung là hai lựa chọn khác nhau.

134 cụm chữ công khai × ba ngôn ngữ được giao bốn phiên Antigravity riêng.
Hai phiên tiếp theo trả đúng hai hàm tạo kế hoạch và một dòng import theo
contract. Tệp dữ liệu mới chỉ có hai hằng từ điển, 141 dòng/134 mục, không có
hàm, import, lời gọi hay tác dụng phụ. Các placeholder được đổi tên hữu hạn
thành {p0}/{p1}; giá trị gốc được truyền một lần qua format, không eval hay
quét lại chuỗi khách nhập. Khác biệt CRLF/LF được chuẩn hóa khi so patch, không
phải lỗi worker và không sửa nội dung code trả về.

## Bằng chứng đã đo

| Cổng | Kết quả | Giới hạn |
|---|---|---|
| Dữ liệu dịch | 402 giá trị đạt: 401 giữ + 1 kiểm lại thứ tự placeholder tiếng Trung | Thứ tự named placeholder theo ngữ pháp; định danh/số lần xuất hiện giữ nguyên |
| Pure baseline | 192 Image + 1.200 Reference = 1.392 trường hợp; 36.000 lượt kiểm chữ còn lỗi | Cấu trúc, dữ liệu khách, ID, thời lượng và tính xác định đã đạt |
| Pure sau sửa | Hai test RED chuyển GREEN; một test schema cũ giữ PASS | Bao phủ mọi lựa chọn, ngôn ngữ hỗ trợ, fallback và literal {p0}/{p1} trong dữ liệu khách |
| API hồi quy | 6/6 test hiện có đạt, 2 cảnh báo deprecation cũ | Không bỏ assertions quyền, CSRF, ownership, idempotency hay ranh giới an toàn |
| Native postfix | 12/12 view, 6/6 luồng UI tạo–xác nhận–lưu–GET đọc lại–mở | 320 tối có thao tác; 1440 sáng xem ban đầu, không full-cross theme |
| Nội dung thực | 153 trường chữ hệ thống trong 6 phản hồi thật đúng ngôn ngữ đã chọn | Image vi/en/zh, Reference vi/en; giao diện zh của Reference vẫn chọn nội dung vi |
| Lưu thật | 6 kế hoạch/18 cảnh và phiên bản khớp; quick_check=ok | Metadata đầu vào thử riêng, không tạo byte ảnh/video |
| An toàn | 0 kết nối ngoài, 0 .env/media read, 0 provider/ví/production write; 46 tiến trình Job → 0 | Không truy vấn hay dọn tiến trình khác |
| Nguồn | Chỉ hai hàm và một import thay đổi; 16 tệp nhạy cảm giữ nguyên | Global catalog, helper, model/schema, caller, timing/guard không đổi |

Artifact: video-output-copy-pure-baseline.json, video-output-api-regression-nov11.log,
video-output-final-source-review-nov11.json và thư mục
video-output-final-native-nov11-batch-a/ (summary, isolation, 36 ảnh, phản hồi thật).
Nguồn trước/sau lượt native khớp. Không chạy lại các luồng đã đạt sau sửa tài liệu.

## Không nhận vơ phần chưa hoàn tất

Kế hoạch cũ không được di chuyển hoặc viết lại. Nhãn cố định và phần đầu ghi
chú tiếng Anh trên trang chi tiết kế hoạch là bước tiếp theo, không nằm trong
hai hàm này. Các công cụ video khác vẫn cần rà nội dung hệ thống riêng.
Reference current-input/stale-response/session, Image actual edit/retry,
toàn-app locale/AX/auth/device, signed production và motion cuối còn mở.
Không suy video/provider-output thành công từ việc tạo và lưu kế hoạch văn bản.

Tài liệu vận hành/đối chiếu chức năng và phiên Tester đã cập nhật trước push.
CI/provenance/exact-HEAD merge/exact-SHA deploy/runtime/file hashes/HTTPS assets
là các cổng riêng, chờ receipt. PROVIDER_CALLS=0; WALLET_MUTATIONS=0;
PRODUCTION_DATA_MUTATIONS=0; LIVE_PASS=NOT_TESTED; LESSON_CANDIDATE=NONE.

## Gate reopened before merge: title-prefix budget

PR715 chưa merge. Kiểm tra thêm 40 biên độ dài so với BASE phát hiện bốn
regression mới: Image VI tên150/155/160 và Reference VI chủ đề150. Các đầu
vào này từng lưu được nhưng tiền tố bản dịch dài làm vượt giới hạn180. Đây
là tiêu chí thiếu trong phiếu điều phối, không phải worker làm sai TARGET.
Trạng thái nghiệm thu cần bổ sung cổng này trước phát hành; các bằng chứng
về 400 giá trị dịch khác và bốn luồng không phải VI vẫn được giữ.

Chỉ rút gọn hai tiền tố VI, không cắt tên khách, không tăng giới hạn hoặc
đổi schema/code. Bốn regression tests đã RED. Lượt CI cũ42880606997 bị hủy
chủ động vì không phải bản cuối; cần final HEAD CI mới sau patch. Hai luồng
VI với đầu vào150ký tự phải tạo/lưu/đọc lại đầy đủ; không chạy lại toàn matrix.

Gate này đã đóng trước final push: worker trả đúng hai giá trị VI, 400 giá trị
khác/code/schema/giới hạn không đổi. Bốn regression tests GREEN; 40 so sánh
với BASE có 0 regression mới, 11 trường hợp bị từ chối tương đương BASE vẫn
ghi nhận là giới hạn cũ, không nhận là đã giải quyết.

Hai luồng VI có tên/chủ đề150ký tự đã tạo–xác nhận–lưu–đọc lại–mở thành công,
tên khách đầy đủ; tiêu đề mới168/172ký tự. DB tạm đúng2plan/6scene, không lỗi
hoặc egress; source binding và cleanup đạt. Giữ bốn luồng không phải VI cùng
các view/402-value evidence không bị ảnh hưởng, không chạy lại1.392case/toàn
native. Artifact video-output-boundary-native-nov11-batch-a/.
