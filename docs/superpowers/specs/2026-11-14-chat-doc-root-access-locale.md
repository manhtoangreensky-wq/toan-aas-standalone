# Trò chuyện/Tài liệu: tiêu đề và thông báo giới hạn truy cập

BASE: `7ef5e3c6ade86acff9a9578f36f9c85287a37a73`, PR #726 đã triển khai.
Tracker duy nhất: Issue #689; contract `6870991133`, phụ lục `6871179447`.

## Thứ tự và phạm vi khóa

|Mục|Kết quả cần đạt|Dependency|
|---|---|---|
|CHAT-DOC-ROOT-HEADERS|Tiêu đề/mô tả đúng `/chat` và `/documents` dùng bốn khóa hiện có|Nguồn thật và entry đã xác minh|
|CHAT-ACCESS-PLAIN-LANGUAGE|Ba khóa mới VI/EN/ZH, giữ phân biệt cần đăng nhập/chưa bật cho phiên|Không đổi điều kiện hoặc nhánh có quyền|
|DOCUMENTS-ACCESS-PLAIN-LANGUAGE|Hai khóa mới VI/EN/ZH; giữ hạn chế truy cập, bỏ ba tag triển khai lặp|Không đổi loading/failed/ready/controls|
|GROUP-VERIFY|Renderer thật, từ điển, dữ liệu/controls/markup hữu hạn, native đúng root|Ba kết quả được rà gộp|
|DELIVERY|Tài liệu/Tester/provenance, CIexactHEAD, merge/deploy/runtime/assets|Local đã đạt|

Các worker chạy độc lập, chỉ trả đề xuất, không ghi chung repo. Không dùng
alias dịch toàn cục cho hai tên sản phẩm: tiêu đề trang chi tiết do khách đặt,
kể cả trùng tên sản phẩm, không được coi là nhãn cố định.

Chỉ hai đoạn root trong `localizedPageTitle`/`localizedPageDescription`, phần
chữ của `!canView` ở `renderChatWorkspace` và `renderDocumentHub`, cùng năm
khóa mới/15giá trị. Mọi manifest/dictionary cũ, helper/chữ ký/normalizer, quyền/
auth/API/backend/engine/provider/Bot/ví/thanh toán/ENV/schema/CSP/motion và các
nhánh có quyền/lỗi thực ngoài scope đều giữ nguyên.

## Checklist và bằng chứng

- [x] Đọc entry thật: hai root dùng portal/integration; chỉ auth/features có entry khác.
- [x] Nguồn public exactcommit/fullMAP được đối chiếu byte; không gửi test/fixture/API/data.
- [x]57renderer baseline18đạt/39lỗi trước sửa, có guarded/authoring/loading/failed/ready.
- [x] Ba đề xuất R1 giữ đúng điều kiện và nội dung trong phạm vi.
- [x] Lỗi vị trí chèn từ điển do phiếu yêu cầu sau freeze đã được nhận trách nhiệm.
- [x] Hai catalog-R2 chèn trước verify/freeze, giữ nguyên mọi key/value đã trả.
- [x] Khởi tạoVM/72ca cuối, dictionary cũ/data/controls/HTML và tên khách trùng sản phẩm đạt.
- [x] Native24view root sáng/tối và12view/12clickthẻ nhóm390/1440VI/EN/ZH.
- [x]358affectedNode,32Python/1BASECSSfailure,compile và review độc lập đạt trong phạm vi.
- [ ] Tài liệu/Tester/metadata và cổng phát hành cuối.
- [ ] CI đúng HEAD, merge/deploy/runtime/assets, receipt tại cùng Issue/PR.

R1 insertion-point là SPEC SAI, không chấm lỗi worker hoặc mở quyền tự sửa
logic. Đã rút riêng assignments sai khỏi local, không phát hành; hai phiếu
catalog-R2 giữ nguyên từ ngữ/tên khóa, chỉ đăng ký trước `verifyEqualKeysets()`
và `deepFreeze(MESSAGES)`. Hai chốt này không được bỏ, chuyển hoặc vô hiệu.

Đợt này không đóng nội dung Chat/Documents khi đã có quyền hoặc toàn bộ trang
chi tiết. Toàn tuyến locale/clutter, responsive/AX/auth/device/Safari, signed
production/provider output và M-FINAL-01..06 vẫn mở; motion giữ cuối.

## Phụ lục tác động consumer và kiểm thử lịch sử

`localizedPageTitle`/`localizedPageDescription` có consumers trong title,
header/breadcrumb/menu/command/moduleCard. Khi dữ liệu không có khóa entry
danh mục, cùng nhãn cố định của `/chat` và `/documents` cũng được dùng làm
fallback cho hai thẻ mở công cụ; href/action/data/search index giữ nguyên.
Khi danh mục API có entry-key hợp lệ, khóa entry có sẵn vẫn ưu tiên và chữ
thẻ giữ nguyên. Không đổi precedence, route/manifest hoặc dịch tên khách.
Native có thêm đối chiếu thẻ nhóm thật; renderer root `/features` cũ không
được dùng làm bằng chứng entry danh mục root đang chạy.

Adapter lịch sử mới chỉ chấp nhận đúng năm key/15giá trị mới đã đo; giá trị
khác, key không thuộc phạm vi và mọi giá trị cũ đều giữ cho golden hash kiểm.
Hai ca whole-dictionary cũ dùng adapter này thay vì cập nhật hash. Hai ca
whole-HTML lịch sử chỉ phục hồi chính xác root hero/guard và h3/p của thẻ
`href="/chat"`/`href="/documents"`, không bỏ các text node khác. Thêm ca
mutation và consumer thật để chặn việc adapter che sai chữ/dữ liệu.

Ca nguồn Document Board không còn đòi tag “Không có output giả” đã được phép
bỏ; thay bằng hai consumer khóa dịch của guard, giữ toàn bộ kiểm tra loading/
failed/download/private/PWA khác. Một ca CSS-tail có sẵn tìm gradient trên
mọi CSS phía sau marker vẫn giữ nguyên và đối chiếu lỗi BASE riêng; không sửa
theme/motion. Native chống trang trắng dùng heading+nội dung thật, không bắt
tiếng Trung đạt ngưỡng150ký tự. Đây là sửa harness, không thay ứng dụng.

Chín ca golden-catalog ở ba nhóm planner cũng cần cùng adapter exact-five
để chỉ bỏ đúng năm key mới đã đo trước khi so hash cũ. RED294ca285PASS/9FAIL
đúng keycount; giữ nguyên mọi hash/golden/literal cũ, không filter theo prefix.
Chỉ nối adapter có mutation-reject vào helper lịch sử đã dùng chung.
