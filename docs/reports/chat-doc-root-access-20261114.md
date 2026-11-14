# Trò chuyện và Tài liệu: chữ đúng ngôn ngữ, giữ quyền thật

BASE: `7ef5e3c6ade86acff9a9578f36f9c85287a37a73`, bản PR #726 đã triển khai.
Tracker duy nhất: Issue #689; contract6870991133/phụlục6871179447.

## Phạm vi đã sửa

Tiêu đề/mô tả của đúng `/chat` và `/documents` dùng bốn khóa dịch hiện có.
Không thêm alias tên sản phẩm toàn cục: tên hội thoại do khách đặt, kể cả
“AI Chat Workspace” hoặc “Document Studio”, vẫn là dữ liệu nguyên văn.

Trong riêng nhánh chưa có quyền xem của Chat, heading và hai tình huống cần
đăng nhập/chưa bật cho phiên dùng ba khóa mới. Trong cùng nhánh của Document
Hub, hai khóa mới mô tả hạn chế truy cập; bỏ đúng hàng ba tag triển khai lặp,
không tạo ô thay thế hoặc khẳng định dữ liệu đã mất. Năm khóa/15giá trị được
đăng ký trước kiểm tra keyset và khóa từ điển. Toàn bộ khóa/giá trị cũ giữ nguyên.

Các điều kiện/quyền, form, controls, dữ liệu, nhánh có quyền, loading/failed/
ready, auth/API/backend/engine/provider/Bot/ví/thanh toán/ENV/schema/CSP/motion
không đổi. Mọi mã ứng dụng từ đề xuất worker; không tiếp quản tự viết logic.

Consumers dùng chung title/description còn có header/breadcrumb/menu/command/
moduleCard. Khi catalog không có entry-key, thẻ `/chat` và `/documents` dùng
nhãn root mới làm fallback; khi có entry-key thì nhãn entry cũ vẫn ưu tiên.
Không đổi precedence, href, search-index hoặc dữ liệu. Native kiểm riêng cả
thẻ từ API có entry và thao tác mở root thật.

## Bằng chứng local

- 57ca ban đầu:18baselinePASS/39RED→57PASS. Bổ sung adapter/cardconsumer/
  tên khách trùng tên sản phẩm thành72ca cuối,72/72đạt.
- Rộng554Node có512đạt/42lỗi comparator cũ khi thêm khóa/chữ đã được phép.
  Adapter hữu hạn chỉ nhận đúng năm giá trị mới và đúng root/cardmarkup;
  không xóa text tùy ý hoặc thay goldenhash. Nhóm chịu ảnh hưởng358/358đạt,
  72ca cuối cũng đạt; các số có chồng lấn, không cộng thành tổng duy nhất.
  Kết quả các bài không đổi trước đó được giữ, không chạy lại chỉ để tăng số.
  Chín ca keycount/hash của ba planner cũ tiếp tục dùng cùng adapter exact-five:
  RED294ca285PASS/9FAIL, sau nối adapter303/303đạt (gồm9ca adapterAccount).
  Hash/literal cũ giữ nguyên, không dùng prefix-filter bỏ tùy ý khóa mới.
- 32Pythonđạt/1CSS-tail lỗi nguyên vẹn trên BASE: tìm gradient trong toàn bộ
  phần CSS sau marker, không riêng Document Board. Không sửa CSS/motion để xanh.
  Ca đòi tag đã được phép bỏ đổi sang hai consumer locale, giữ mọi điều kiện/
  loading/error/download/private/PWA khác. Compile app/page và hai bundle đạt.
- So nguồn đảo đúng sáu thay đổi worker khớp mọi byte khác của portal/i18n
  với BASE;18tệp bảo vệ khác không đổi. Keyset verification/deepFreeze giữ.
  Rà soát độc lập không phát hiện blocker, không chạy lặp suites.

Native24view hai root390/1440VI/EN/ZHsáng/tối, dùng theme-toggle thật; thêm
12viewthẻ hai nhóm và12click thật đến root. Không lỗi trang/console/tràn ngang,
không gọi ngoài hoặc ghi sản phẩm/ví/provider/production. Bản saoQA6kế hoạch/
18cảnh/lịch sử và bằng chứng gốc giữ; mỗi lượt cuối19tiến trình sở hữu→0.
Feature flags tắt chỉ trong childserverQA để nhận guard thật từ backend; không
fake bootstrap/API hay sửa `.env`, môi trường máy hoặc production.

## Sai sót khảo sát và giới hạn được giữ rõ

R1 được giao chèn khóa trước `const api`, nhưng chỗ đó nằm sau deepFreeze.
Nghiệm thu VM phát hiện lỗi object-not-extensible, đã rút assignments sai,
giao catalog-R2 trước verify/freeze. Đây là SPEC SAI do người giao, không lỗi
worker hoặc cớ tự sửa app. Lời dịch/tên khóa R1 giữ nguyên ở R2.

Native đầu vào Chat có quyền nên vào authoring, không phải access guard;
đã tách fixture child-only đúng điều kiện. Kiểm chống trang trắng được sửa
từ150ký tự sang heading+nội dung thật để không loại tiếng Trung hợp lệ.
Một lần TestClient bị kẹt trong môi trường hạn chế được dừng đúng PID/lệnh
sở hữu; không lấy đó làm PASS hoặc thay đổi auth để vượt qua.

Đợt này không dịch toàn bộ authoring/detail hoặc mọi trạng thái Chat/Documents.
Thiết bị/Safari, signed production/provider output, auth/AX toàn app và motion
cuối vẫn mở. CIexactHEAD, merge/deploy/runtime/assets cùng receipt ởIssue689/PR
là các cổng riêng sau local; không suy LIVE từ source hoặc HTTP200.
