# CHAT-DETAIL-CONTEXT/SECTION-COPY — 14/11/2026

BASE `d124b867c81ca0882a74721661fd8880e0451b8d`, PR735 đã triển khai.
Chỉ Issue689 và checklist mẹ hiện có; không tạo hàng đợi cạnh tranh.
Hai phiên Antigravity độc lập, output-only, explicit3.8 Flash High, đã trả
sáu OLD/NEW. Chỉ nguồn công khai20c3+fullMAP, không dữ liệu riêng.

## Contract và thứ tự

GOAL: Phần thêm ghi chú/nội dung, tiêu đề danh sách và ô ghim dùng chữ khách
hiểu theo VI/EN/ZH; không thay hành vi, không đổi nội dung do khách tự viết.
ALLOWED_APP: `portal.js` hai const contextCreate/turnCreate; final return
của renderChatWorkspaceDetail với sáu vị trí chữ; dòng pinned field chỉ thêm
checkboxLabel. `portal-i18n.js` thêm đúng17keys/51values trước verify/freeze.
ALLOWED_TEST: test/runtime/snapshot/fixture mới; adapter lịch sử chỉ chuẩn hóa
exact accepted whole-detail hash/pinned line/ordered17keys, giữ sửa lạ.
CI thêm một test line vào bước đã có, không đổi quyền/workflow deploy.
PROTECTED: toàn shared field/helper/guard/signature/global maps/capabilities,
route/action/IDs/revisions/constraints/form attrs/disabled/order/customer
data/state/persistence; auth/API/Bot/engine/provider/finance/schema/ENV/
integration/CSS/motion/cache. Không xóa lỗi/thông báo quan trọng để làm PASS.
STOP: source hoặc protected comparator lệch, worker patch ngoài sáu đoạn,
thiếu bằng chứng; không sửa trực tiếp trước hai lỗi thật cùng fragment.

Hai patch độc lập chỉ được áp serial bởi điều phối sau PR735 delivery.
note rõ là chia plan chi tiết ra thành từng spec kèm theo kết quả cần đạt
để qua spec khác, với spec đơn giản thì chạy nhiều spec một lúc, nếu spec
phức tạp thì làm từng spec.

|SPEC_ID|Kết quả|Dependency|Trạng thái|
|---|---|---|---|
|CONTEXT-COPY|10keys/locale; hai form dễ hiểu, controls giữ|PR735 delivery|Worker BUILT, chờ permanent/native|
|SECTION-COPY|7keys/locale; sáu headings và checkbox đúng locale|PR735 delivery|Worker BUILT, chờ permanent/native|
|CSE-RELEASE|Provenance/exactCI/merge/deploy/runtime/assets|Hai spec nghiệm thu|Chưa mở|
|TTS-INGRESS|Xác minh receiver/target và contract nối thật|Độc lập UI|Chỉ đọc/đề xuất, không code trong release UI|

## Checklist nghiệm thu

- [x] PR735 CI43609528286 hai nhóm đạt; merged/runtime d124b867;
  deploy43610620888 đạt; tree85ad980b exact. Ba dịch vụ running/healthok,
  4public assets/TTS+2video hashes exact; receipts6879820281/6879820732.
- [x] Hai worker R1 trả đúng sáu thay đổi,17keys51values. Kiểm cấu trúc
  một lần mỗi kết quả; zero worker code failures.
- [x] Candidate27 BASE0PASS27RED; ứng viên21PASS/6 harness failures.
  Lỗi bộ đo: default JS parameter biến undefined capability thànhtrue.
  Sửa riêng harness, sáu ca ảnh hưởng6PASS; không đổi app/worker để làm xanh.
  Giữ cả báo cáo lỗi và affected report, không chạy lặp21ca đã đạt.
- [x] Permanent10/10RED và baseline native first-draft RED trước apply.
- [x] Áp đúng sáu worker substitutions,17keys/51values; old values/order/
  real frozen dictionaries giữ, không thay generic checkbox renderer.
- [x] ActualVM root/detail checkbox và hai create forms: state/capability/
  disabled/tags/helper args/IDs/escaping/customer literals giữ.
- [x] Native VI/EN/ZH375 sáng/1440 tối, bốn state/server riêng:
 17keys đúng; checkbox root/detail giữ input/state/không submit; actual GET,
  no errors/overflow/provider/product writes; QA DB/schema/evidence giữ,
  owned processes→0. Không đổi RateGuard/auth.
- [x] Một nhóm target+affected/Python/syntax/protected/review; chỉ chạy lại
  failures bị ảnh hưởng. Strict adapters reject partial/mutation/reorder.
- [ ] Docs hiện tại/gốc, Tester/cases/metadata/provenance/exact CI/merge/
  deploy/runtime/assets/receipt cùng Issue/PR.

## Giới hạn không được giấu

ContextCards, turnList, history, execution/toast, các công cụ Tài liệu còn
ngoài phạm vi; không nhận toàn trang sạch chữ kỹ thuật. Giữ nguyên nội dung
khách kể cả media/studio/Bot/Facebook/TikTok. Không blanket replace/filter.
Toàn AX/auth/device/Safari/signed production và M-FINAL01..06 vẫn mở.
TTS ingress có bằng chứng riêng: receiver generic không đăng ký trong nguồn
Bot đúng SHA; listener thực tế là Bot, OpenAPI không có generic estimate/
confirm. Chưa feature POST hoặc âm thanh thật; không tự bật ENV/quyền/
provider hoặc thay quy tắc tài chính để nối hai lifecycle.

PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_WRITES=0.

## Kết quả local và sửa riêng bộ đo lịch sử

Nhóm135 test:131PASS/4lỗi adapter lịch sử, sau sửa helper riêng4affectedPASS.
Helper mới chỉ chuẩn hóa whole-detail có khóa mới khi khớp hash; nguồn cũ
đi nguyên vẹn tới gate cũ, không đổi các hằng hash. Dòng ghim kiểm hash riêng.
Nhóm ảnh hưởng286:285PASS/1historical mutation test lỗi vì đoạn mục tiêu cũ
không còn xuất hiện sau thêm checkboxLabel. Project về đúng nguồn cũ đã
duyệt trước mutation, assert mục tiêu xuất hiện một lần. Lượt affected giữ
thêm1regressionPASS, test cũ chỉ khác tên gate từ chối; sửa regex hữu hạn,
affected cuối1PASS. Không đổi app hoặc worker. Không nhận một lượt135/286
xanh; giữ mọi report lỗi và chỉ chạy lại ca ảnh hưởng.
Test bổ sung: nguồn cũ không có khóa mới vẫn nguyên byte; sửa writable vẫn
bị gate summary cũ từ chối. Python9PASS;syntax/compile exit0.

Native ba fresh servers VI/EN/ZH8state/lượt,24 unique aggregatePASS/13ảnh;
checkbox root thay chọn rồi trả lại, không submit. Dữ liệu/schema/evidence/
15 hội thoại QA/6plans18scenes giữ;0errors/overflow/external/productwrites,
owned Jobs về0. Hai app files khớp byte LF đúng sáu đề xuất worker;
17 protected paths/allPython không đổi, review nguồn C0/I0/M0.
