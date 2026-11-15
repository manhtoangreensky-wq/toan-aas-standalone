# DOCUMENT-CARD-COPY —15/11/2026

Đang đọc và áp dụng skill owner-governed-codex cho task này.

GOAL=Thông báo chưa có kết quả, nhãn tải/lưu/xác nhận và trạng thái rỗng mặc định của thẻ tài liệu dùng chữ dễ hiểu đúng VI/EN/ZH; không tạo hoặc hứa kết quả chưa có.
BASE_SHA=5bc8f3cdf500e8035e55789cd8c30fb18e779eb6
BRANCH=codex/document-card-copy-20261115
TRACKER=Issue689/checklist mẹ
DEPENDENCY=DATEPR742đãgiao:CI43706589548bothSUCCESS,deploy43707642952SUCCESS,runtime/tree/services/health/fiveassets exact.

## Ba phiếu trong một đơn vị renderer

Áp nối tiếp đúng ba đề xuất Antigravity đã trả, không gọi lại worker:
pending7keys, actions14keys, defaultempty2keys. Tổng sáu thay thế nguyên văn
trong portal.js/i18n.js,23keys×3locale=69values.
Chỉ cùng một thẻ tài liệu; không trộn ba gói Document khác hoặc catalogue.
Đơn vị là presentation-only; không đổi helper/state/downloadpath/quyền.

|Phiếu|Đầu ra chính|Điều kiện giữ|
|---|---|---|
|DOC-CARD-PENDING|7nhánh thông báo dễ hiểu,escaped đúng|Conditions/status/kind/download-ready giữ|
|DOC-CARD-ACTIONS|14fixedlabels/buttons/confirmtexts|URL/attrs/actions/strictcaps/metrics/customerfilename giữ|
|DOC-CARD-EMPTY-DEFAULT|2defaultargs dùng currentlocale|Customemptyargs/bodythẻ giữ|

Allowlistapp:static/portal/portal.js và static/portal/portal-i18n.js.
Tests mới và exacthistoricaladapters trong tests/; CI chỉ thêm targetedcommand
vào existinglocale step, không đổi quyền/trigger/timeout/settings.
Docs/Tester/current-original/checklist/provenance theo cổng trướcpush.
Protected:mọiappPython/auth/DB/provider/engine/Bot/ví/PayOS/ENV/schema/
integration/CSS/motion/route/CSRF/session/ownership và dữ liệu sản phẩm.
Không đổi selected/sourceMetric/outputMetric/fallbackFilename/icon/rawdates
còn lại; chúng cần phiếu riêng, không nhận toàn màn hình đã sạch chữ.

ExpectedGREEN LF sau6literalreplay:
portal4e287a1bdf0c55de5e74b6c32afabfcc36d26de57c57fdef0c5b86a00ab47f0f;
i18ndd5ce0c7e6a35e1135d571813baf6136d5f38571b41aae39e1a8313744545a0b.
Mỗi OLD unique1 tại bước áp, ba chèn catalog trước cùng marker theo thứ tự;
nguyên văn các giá trị worker/canonicalcopy, không broadreplace.

## Checklist / acceptance

- [x] PR742delivery kiểm thực tế; newBASE xác định, không đoán merge.
- [x] Root đọc actual3proposals/fullcardrenderer/state/callers.
- [x] Permanent10RED trước ứng dụng:7pendingbranches,allkinds/states/download/
  caps/customempty/customerliteral/fallback/locale/escaping/catalogguards.
- [x] NativeBASEactual/documents/split defaultconsumer,VI375 thấy oldtext;
  actualsignedGETempty,wholeoperationsDB0,noreseed/Jobs0.
- [x] Replay6changes/2files/23keys69values,wholeoutside/20protected exact.
- [x] Group635nghiệmthu632+3affected gồm actualcard và impactedhistoricalchain,khôngmasktừ/
  thayoldhash/bỏcustomercontrolassertions.
- [x] NativeGREENsixobservations3signedprofiles375light1440dark/3mobile
  crops đúng emptyregion;source/evidence/9tables/schema/6plans18scenes giữ.
- [x] Source-reviewC0/I0/M0/current-originaldocs/Tester/case1351lines147541bytesLF,
  changedmetadata1PASS32deselected/PUSH_GATE=READY.
- [ ] Provenance/exactHEADCI.
- [ ] Merge/tree/exclusivedeploy/runtime/fiveassets/receipt riêng.

Native chỉ kiểm actualdefaultempty tại/documents/split. /documentsroot
truyền customemptyargs nên không được dùng làm chứng cứ default.
Pending/download/action branches thuộc actualfullbundleVM; không tạo
completedfixture/output/download_ready giả trong native.
Đầu DBcopywholeweb_document_operations phải0, không thì stopNO_EMPTY_QA_DB;
không seed/xóa/lọc để chế danh sách rỗng. Chỉfakeauth3POST vàproductGET/HEAD.
Chỉ bật DocumentOperations/root trong childQAenvriêng;khônghost/.env.
Provider/wallet/productionwrites0. Signedproduction UI/finaloutput/wholeAX/
auth/device/Safari/M-FINAL vẫn mở,motioncuối.

## Amendment sau nhóm GREEN đầu

Nhóm635ca:633PASS/2FAIL. Native6actualemptyobservations đạt.
HaiFAIL là whole-i18n source assertions của DATE/META cũ: inputportal và
catalog đã chiếu đúng23keys, nhưng rawi18n source vẫn chứa ba block thêm.
Đây là thiếu testadapter của điều phối, không lỗi ứng dụng/Antigravity.

Allowlist thêm private test-only documentCardHistoricalI18nSource:
dựng nguyên văn ba block addition từ reviewedfixture23keys theo thứ tự,
chỉ bỏ đúng một completeaddition trước marker, chặn partial/duplicate/
value drift; mọi bytes ngoài addition giữ để oldwholehash tiếp tục bắt.
Hai oldtestsource inputs dùng phép chiếu này, không đổi hash hoặc assertion.
Test mới sourcegate thêm inverse/partial/duplicate/outsidei18n checks.
Chỉ chạy lại đúng hai oldFAIL và một sourcegate bị sửa;633PASS không chạy lại.
