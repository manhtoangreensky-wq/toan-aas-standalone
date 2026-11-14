# CHAT-CONTEXT-CARDS / TURN-LIST — 14/11/2026

BASE `6a51975654cfb30ae228bfef9064ac3141d53081`, PR736 đã triển khai.
Một tracker Issue689 và checklist mẹ. Owner yêu cầu UI dễ dùng, đúng ngôn
ngữ; song song nhánh nối Web–Bot riêng, không trộn adapter vào release này.

## Contract

GOAL: thẻ ghi chú và danh sách nội dung dùng chữ dễ hiểu VI/EN/ZH, không
dịch hoặc lọc bất kỳ nội dung khách tự viết, không thay chức năng thật.
ALLOWED_APP: `portal.js` const contextCards, whole renderChatContextKindOptions
chỉ nhãn lựa chọn, const turnList; `portal-i18n.js`16keys48values mới trước
verify/freeze. Dùng lại nhãn loại/trạng thái/archive đã có, không đổi maps.
PROTECTED: helper signatures/raw kind/state/options order/selectedfallback,
customer title/body/tags, ordinal/revision/timestamp expressions, ID/attrs/
route/action/caps/disabled/order/constraints/persistence; tất cả auth/API/
Bot/engine/provider/finance/schema/ENV/integration/CSS/motion/cache.
Không thêm wrapper/ô rỗng, không ẩn lỗi/trạng thái quan trọng, không hứa
đầu ra AI hoặc thay ngày giờ lưu. Không refactor chung.
TEST_ALLOWLIST: test/runtime/snapshot/fixture mới; finite projection trong
test/adapters cũ theo đúng accepted full-source hash và16ordered keys.
CI chỉ thêm một test line trong bước cũ.
STOP: source mismatch, protected comparator lệch, unknown source/hash,
worker khác hợp đồng; không tự sửa ứng dụng trước hai lỗi thật cùng phần.

Hai phiên 3.8FlashHigh output-only độc lập đã trả trên publicd124+fullMAP,
không gửi currentCCS/private data. A3substitutions/8keys;B2/8keys.
Chỉ điều phối áp serial sau RED/QA gate, không hai worker ghi chung app.
note rõ là chia plan chi tiết ra thành từng spec kèm theo kết quả cần đạt
để qua spec khác, với spec đơn giản thì chạy nhiều spec một lúc, nếu spec
phức tạp thì làm từng spec.

|SPEC_ID|Kết quả|Dependency|Trạng thái|
|---|---|---|---|
|CONTEXT-CARDS|Thẻ/type-select/empty copy8keys theo locale|PR736 delivery|Worker BUILT, chưa QA|
|TURN-LIST|Kind/action/confirm/metadata labels/empty8keys theo locale|PR736 delivery|Worker BUILT, chưa QA|
|RELEASE|Docs/Tester/provenance/exactCI/merge/deploy/runtime/assets|Hai spec nghiệm thu|Chưa mở|

## Checklist

- [x] PR736 CI43612650806 hai nhóm đạt, merge/runtime6a519756,
  deploy43613796270đạt; tree590998e4exact,services/health/4assets/
  TTS+2video hashes giữ,receipts6880380587/6880380973.
- [x] Hai worker trả5OLD/NEW,16keys48values; structural review một lần
  mỗi kết quả đúng hợp đồng,0worker code failures; chưa gọi là QA PASS.
- [x] ActualVM một nhóm permanent RED→GREEN: thẻ/list rỗng/có dữ liệu,
  bốn kind+unknown/activearchived+unknown/fourthreadstate×strictcaps,
  4options order/selectedfallback/escape/locale switch/customerliteral giữ.
- [x] Permanent11:1PASS10RED và native BASE trước apply; giữ output thật.
- [x] Áp exact5workerchanges/2appfiles,16keys48values,oldorder/freeze giữ.
- [x] Native dữ liệu QA riêng có context/turn thật,3locale375/1440,
  select/disabled/confirmattrs/readability/errors/overflow/GET ownership/
  schema/evidence giữ,khôngsubmit/provider/productwrites,ownedJobs0.
- [x] Target147/147,affected286/286,Python9/syntax/compile đạt; reviewC0/I0/M0;
  chỉ chạy lại ca lỗi, không đổi app/hash/test để giấu lỗi.
- [ ] Docs hiện tại/gốc/Tester/cases/metadata/provenance/exactCI/merge/
  deploy/runtime/assets/receipt cùng Issue689/PR; signed production riêng.

History/execution/toast/Docothercopy, toàn AX/auth/device/Safari và
M-FINAL01..06 vẫn mở, motion cuối. Không nhận sạch toàn app từ hai span.
TTS helper/client đang giao riêng; backend có dependency/readiness/output
cổng riêng,không bật ENV/khả năng thực thi hoặc thay money/authauthority.
PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_WRITES=0.

Amendment tiết kiệm kiểm tra lặp: bộ permanent actual-VM chính là gate hành
vi ứng viên; chạy RED trên BASE, sau exact-worker apply chạy một nhóm GREEN
cùng các đối chiếu cũ. Không chạy thêm một candidate GREEN giống hệt trước
đó. Native BASE/green là cổng riêng vì kiểm server/DOM/dữ liệu thật.

Native cuối24unique/13ảnh,3freshservers;15threads24contexts18turnsQA/
8Chat tables/schema/evidence/6plans18scenes giữ,ownedJobs0.
Ảnh card375sáng cho thấy nhãn loại ghi chú vẫn nhạt: gap CSS có sẵn ngoài
phạm vi chữ. Ghi phiếu riêng một selector light-theme cho lượt kế, không
ẩn nhãn/không sửa CSS trong bản đã khóa hash và không nhận wholeAXPASS.
