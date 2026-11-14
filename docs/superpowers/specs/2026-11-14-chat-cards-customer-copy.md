# CHAT-CARDS-CUSTOMER-COPY — 14/11/2026

BASE `398cea1c4f6f6f256c646fa382a78563e66b8939`, PR731 đã triển khai,
receipt Issue689 `6876023868` / PR731 `6876024174`.
Một checklist mẹ và Issue689; không tạo tracker hoặc PR rỗng khác.

Owner: chữ ứng dụng phải dễ hiểu theo VI/EN/ZH, không thuật ngữ triển khai,
không thông báo tương tự bản mẫu/thử nghiệm, không khối giải thích vô dụng.
Giữ tên/nội dung khách và thương hiệu. Giao các phiên Antigravity độc lập;
điều phối nghiệm thu gộp một lần, áp dụng tuần tự không ghi đè.

## Phạm vi khóa và thứ tự

|Spec|Thay đổi duy nhất|Kết quả quan sát|
|---|---|---|
|CHAT-BOUNDARY-REMOVE-20261114|Một return trong renderChatWorkspaceBoundary|Không aside giải thích triển khai ở root/detail; execution panel và controls giữ|
|CHAT-CARDS-CUSTOMER-COPY-20261114|renderChatWorkspaceCards +20 khóa/locale|Thẻ, số ghi chú/lượt, nhãn trạng thái/cách soạn/nút theo ngôn ngữ; dữ liệu khách giữ|

Hai worker chỉ trả OLD/NEW, nguồn Web công khai BASE3477+fullMAP; mã portal.js
BASE398 không đổi so BASE3477. Chỉ i18n thêm4 khóa Document của PR731, phải
giữ nguyên khi áp dụng20 khóa mới. Không gửi test/fixture/API/auth/customer/
financial/Bot source hoặc cấu hình máy chủ ra ngoài.

B timeout được nối cùng phiên, không tính CODE_FAILURE. Nhãn guarded trong
phiếu do điều phối chốt chưa đúng yêu cầu Owner; amendment chỉ đổi ba giá trị
và fallback VI thành “Chưa thể mở” / “Cannot open yet” / “暂时无法打开”.
Không đổi20 khóa/cấu trúc/tham số/hành vi; SPEC_CORRECTION,workerfault0.

ALLOWED_APP=static/portal/portal.js (hai đoạn);static/portal/portal-i18n.js
(20key×3 trướcverify/freeze). Coordinator chỉ áp dụng nguyên văn đề xuất đã rà.
Amendment sau review I1: thêm đúng một rule EOF portal-theme.css cho
`.portal-chat-workspace .portal-chat-workspace-layout > .portal-chat-workspace-create:only-child`
với `grid-column: 1 / -1`. Không đổi grid-template/width/padding/controls/motion.
Đây phần bố cục bị thiếu trong đặc tả bỏ aside,không phải workerfault.
ALLOWED_TEST=tests/chat-cards-customer-copy.test.mjs;
tests/helpers/chat-cards-customer-runtime.mjs;
tests/helpers/chat-cards-customer-snapshot.mjs;
tests/fixtures/chat-cards-customer-copy-reviewed.json;
các consumer test/helper cũ bị đúng hai đoạn và20 khóa này ảnh hưởng.
Thêm hai tệp test/helper CSS only-child và adapter comparator màu chữ PR731;
không sửa expectation/goldenhash ngoài đúng phần đã duyệt.
Chỉ thêm lệnh test vào bước CI có sẵn; không đổi quyền hoặc deploy workflow.
CI amendment:cho phép sửa đúng assertion SP-02 trong
tests/p5-p6-shared-contracts.test.mjs đòi aside cũ thành consumer thật giữ
execution status vàdisabled capability. Không đổi các13case khác/test expectation
quyền/historicalledger. Run43588773451HEAD3f6883e6 là13PASS/1stale-sourceFAIL,
không tính workerfault;không đổi app/native evidence.

PROTECTED=helper/signature/global mode/state maps; route/ID/permissions/
API/loader/auth/schema/ENV/provider/Bot/wallet/PayOS/motion/CSS/cache;
field/control/count/revision/date/numeric-coercion/tags/customer literals.

## Checklist nghiệm thu

- [x] Prerequisite PR731 exactHEAD CI43584766006 cả2jobsPASS,merge/runtime398cea1c,
  deploy43585904925PASS,tree d307b2ba exact,services/health/4assets/protectedhashes exact.
- [x] Candidate35 ca dùng actual VM renderer:BASE4PASS/31RED,candidate35PASS,
  không ghi app. Bộ kiểm đảo patch được sửa bằng exactoffset,khôngsửa worker.
- [x] Permanent tests RED trên BASE398 trước áp dụng:38case3PASS/35FAIL;
  expectedcopy từ bảng phiếu,
  không suy ra từ implementation. Tên ca nêu lỗi thực mà nó bắt được.
- [x] Đúng4workerchanges/3appfiles gồmCSSprerequisite;20key60value mới;
  mọi giá trị/thứ tự cũ giữ,
  unknown/mutated/partial/reordered key/source bị bắt,không prefixfilter.
- [x] Locale/empty/5states/4modes/pinned/permission/invalidID/hostilecustomer/
  numericfallback/runtime-language-switch và root/detail boundary đạt.
- [x] Native baseline→bản sửa,375/1440 sáng/tối VI/EN/ZH:thẻ dữ liệu QA có thật,
  click href thật,không aside/emptyreplacement/tràn/lỗi;không gọi model/provider.
- [x] I1-SINGLE-COLUMN:đo actual form/layout width trước/sauCSS,4VIroot375/1440
  sáng/tối+1detail1440sentinel;không khoảng trống sau bỏaside. AntigravityA
  prerequisite chỉ trả1CSSpatch;không tự sửa trước2workerfault.
  24view copy/data/navigation đã đạt vẫn được giữ,không chạy lại để tăng số.
- [x] Hồi quy các scope đã khóa:309NodePASS,9ChatPythonPASS,syntax/compileexit0;
  sourceexact4workerchanges/16protectedpaths. ReviewI1→C0I0M0 sauCSS+geometry;
  lỗi BASE phải có comparator,không skip/weaken để làm đẹp.
- [ ] Docs hiện tại/gốc/Tester/case/metadata/provenance/finalexactHEADCI đạt.
- [x] PR/merge/deploy/runtime/assets/receipt cùngIssue689;chỉ chốt phần có evidence.
- [x] DeliveryPR732HEAD211e45fe,CI43589450424bothPASS,merge/runtime7e30dd95,
  deploy43590585769PASS,tree96606afc exact,services/health/4assets/protectedhashes.
  ReceiptIssue6896876684304/PR7326876684561.

QA chỉ SQLite/asset tạm, fake account đã sở hữu, secret ngẫu nhiên child-only,
chặn egress ngoài localhost và mọi ghi sản phẩm từ browser. Nếu cần dữ liệu thẻ,
chỉ seed metadata trong bản sao QA riêng và ghi rõ số/schema/fingerprint trước
và sau; không sửa DB bằng chứng gốc hoặc production, không sửa môi trường máy.

Sửa đặc tả dữ liệu QA trước áp dụng: native chỉ dùng4 trạng thái và3 cách soạn
được cổng nhập thật chấp nhận; mỗi owner có5 bản ghi hợp lệ (draft lặp với ID/
tên riêng),tổng15. Guarded/UNKNOWN kiểm bằng VM như dữ liệu không hợp lệ,
không seed rồi coi đó là một trạng thái nghiệp vụ thực. Lượt fixture sai bị
loader từ chối đúng chốt,không được tính lỗi ứng dụng hay lỗi Antigravity.

## Còn mở và điểm dừng

Không phải toàn Chat detail/run/context/pagination/toast đã dịch; phần ngoài
hai đoạn vẫn mở. Web–TTS đọc VPS cho thấy voice_tts không trong danh sách
thực thi; không bật ENV/quyền thực thi hoặc gọi có phí dưới phiếu UI.
Actual audio NOT_OBSERVED; route/engine cần hợp đồng riêng.
Motion M-FINAL-01..06 vẫn cuối.

Dừng đúng phần nếu patch ngoài phạm vi, new regression, snapshot không đủ
chặt, phải đổi quyền/dữ liệu thật hoặc thiếu bằng chứng đầu ra. Không dừng
các phần độc lập đang có thể làm an toàn.
