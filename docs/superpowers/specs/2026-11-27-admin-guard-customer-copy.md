# AGC — thông báo thao tác và Admin dễ hiểu

Đang đọc và áp dụng skill owner-governed-codex cho task này.

BASE `5f316f29c9b8657c4018f5174c4c4ce4f16c1e5f`;
branch `codex/admin-guard-copy-20261127`;standalone;Issue689.
GSC prerequisite đã triển khai PR819/runtime5f316f29,CI46021673561
haiSUCCESS/456QA,deploy46027449612SUCCESS,source/assets/cacheexact,
receipt7222538286/7222538994readback. Signedproductioncòngiữmở.

Owner yêu cầu giữ đúng tiếng Việt/Anh/Trung,không câu kỹthuật thừa;
Antigravity4ExtraHigh builder,3phiếuindependentproposal-only,
rootghépcơhọc/QA/Git/ship. Standingpermissiontronggoalgiữ,
không mởlogin/settings/accountinvestigation. Workerkhôngghiappchung.

## Thiết kế hẹp

1. AGC-ACTION: giữ từngđiềukiện/thứtự củaactionBlockReason,page/context
 vàcanActkhôngđổi;chỉ trảfiniteuiTextnative,không signed/CSRF/CoreBridge/
 canonical/receipt/technicalcodes. NhánhTelegramunready dùng thông báo
 khôngthểliênkết ngắn,khônglộconfigurationnames. Paymentbranch chỉđổichữ,
 khôngđổigiá/PayOS/wallet/capability/condition.
2. AGC-SUPPORT: đổiđúngcácrowgiớithiệu/guard/loading/intro/supportboundary
 trongADMIN_SUPPORT_COPY,sửa3locale;giữkeys/placeholders/actions/recorddata,
 khôngbỏcảnhbáonộidung/nghiệpvụquyền. Bỏtoànkhunggiảithíchboundary
 ởcuốirenderSupportAdminBase;khôngbỏform/list/summary/permissionguard.
3. AGC-OPERATIONS: đổiđúngcácrowtrạngtháidisabled/unavailable/loading/
 queue/partial/intro/manageronly trongADMIN_OPERATIONS_COPY,giữphânbiệt
 chưabật/chưatảixong/khôngcóquyền/khôngcóbản ghi. Khôngẩnviệcthật.

Ba phiếutáchđoạnnguồn vàchỉtrảproposal;khôngchungmutableappstate.
Khôngmởrộngsanýmụccustomer360/CRM/Telegramnotice/engine/motion khác.

## Allowlist

Ứng dụngchỉ `static/portal/portal.js`, `static/portal/portal-i18n.js`.
ChỉactionBlockReason,SupportAdminBaseboundarysuffix vàhaiownedcopyarrays;
khôngthêmsharedhelper/signature/refactor hoặcđổikeycũ.
QA CREATE `tests/admin-guard-customer-copy.test.mjs` vàliteralreviewed
fixture `tests/fixtures/admin-guard-customer-copy.json` (31row/93value);
QAhelper/fixtures/CIchỉmởamendmentsaukhiđofailurecụthể.
Docsplan/spec/ops/comparison/Tester/master/MAPcậpnhậttheobằngchứng;
TestermetadataLFhashrefreshtrướcsourcecommit,Web-onlyprovenancesaucommit.
Protected:authmodule,canAct,allconditions/actions/inputs/escaping,
backend/Bot/bridge/provider/wallet/PayOS/ENV/schema/productiondata,
Gallery/deployworkflow/motion/10oldstatefilesunread.

## Cổng nghiệm thu

- AC01:mọiactionbranchtrảthôngbáobảnđịaVI/EN/ZH,thứtựguardgiữ;
 disabledactionkhôngtựenabled,safefallbackVI,khôngconfigurationnameleak.
- AC02:Supportguard/loading/ready rendernaturalcopy,giữcontrols/ARIA/
 attrs/data/textkhách,khôngkhungboundarytrốnghoặcgiảithíchkỹthuậtcuốitrang.
- AC03:Operationsphânbiệtdisabled/loading/unavailable/partial/manageronly,
 giữrole/capability/queuecountunknown/emptytruth,khôngtechnicalfallback.
- AC04:Nodeactualhelper/renderer+i18n→RED/GREEN,unknowncustomertext
 giữ/escaping;browser390/768/1440VI/EN/ZHsáng/tối vàfocus/overflow/error.
- AC05:exactproposal/source/protectedcomparators,oldtestsnguyênassertion;
 sharedhistoricalcomparatorskhôngđượcmaskunknownchanges.
- AC06:docs/checklist→exactCI→mộtPR→merge→Webdeploy→runtime/assets/
 receipts;liveproductionriêngkhôngsuytừQA.

note rõ là chia plan chi tiết ra thành từng spec kèm theo kết quả cần đạt để
qua spec khác, với spec đơn giản thì chạy nhiều spec một lúc, nếu spec phức
tạp thì làm từng spec.

| SPEC_ID | Dependency | Kết quả mởkhóa | Trạng thái |
|---|---|---|---|
| AGC-RED | GSC_DELIVERED | Actualbranch/rendererRED,literal3locale | ACCEPTED_RED |
| AGC-ACTION | AGC-RED | Text-onlyproposal,conditionsheld | PROPOSED_EXACT |
| AGC-SUPPORT | AGC-RED | Ownedrows+oneboundaryremoval | PROPOSED_EXACT |
| AGC-OPERATIONS | AGC-RED | Ownedrows,statechanneldistinctions | PROPOSED_EXACT |
| AGC-QA | CảbaPROPOSED | Groupedtests/browser/protected | LOCAL_PASS |
| AGC-SHIP | AGC-QAPASS | OnePR/CI/merge/Webdeploy/receipts | LOCKED |

- [x] BASEruntimevàcleantrackedđãđối chiếu;10stategiữ.
- [x] Sourcefinding:actionBlockReasonlines9761..9780 technicalraw;
 AdminSupporti18n13239..13255 vàOperations12786..12803 jargon.
- [x] REDactualhelper/renderer129ca109FAIL20PASS,0collectionerror,
 literalfixture31row93value;XMLadmin-guard-copy-red-literal-nov27.
- [x] BaAGY4ExtraHighterminal0/1turnmỗiphiên,22recordexact;
 action2/support8/operations12,same-defectfailurecount0.
- [x] Rootđọcproposalrisksvàsemanticmộtlượt,ghépcơhọcđúng22cặp,
 2appfileexactproposal;129GREEN/0fail,syntax2JS+diffcheck0.
- [x] Consumerregression/browsergộp,khôngappeditkhitargetđãpass.
- [ ] Docs/Tester/Testermetadata/provenance/exactCI/release.

## Impact đã đọc

actionBlockReason địnhnghĩa9761,calls11856renderFormCard,
12239renderHero,32967onboarding,37324campaignauthoring.
Testsđọcthật: image-create-locale-presentation,voice-flow-state-presentation;
cácMusic/Voicecaseskhácstub,khôngcoilàcoveragebranchthật.
ADMIN_SUPPORT_COPYvàADMIN_OPERATIONS_COPY quaexistingcatalogue,
renderSupportAdminBase31396,renderOperationsAdmin30766.
Khôngđổisymbolhoặcgiátrịnghiệpvụ,onlyfixedcopy;grepítkhônghạrisk.

## Quyền và dừng

Workerchỉđọcpayloadsourcefinite/fullMAP vàtrảproposal,khôngtools/Git/VPS/
login/settings/testfixtures/APIresponses/ENV/secrets/customerdata.
Rootkhôngtựsửaapptrước2workersaisameacceptance. Cóspecmissing thìroot
sửaphiếu,khôngđổilỗiworker. Ngaykhitargetpassthìkhóasource,noexpansion.
ProviderCalls=0;WalletMutations=0;ProductionDataWrites=0;MOTION_LAST.

## Receipt local hiện tại

ContractIssue689comment7222860285 đãreadbackexact trướcdispatch.
AGYconversationACTION9dbcc5de-90b9-4a79-9a07-d1e98831c3f3,
SUPPORTdac917b7-aadc-4c2a-b14b-c6866ccbcf8d,
OPERATIONSfab6a78b-c666-4cc9-ae63-a8e2c20576aa,
modelgemini-4-hydrogen-xhigh,verifyNOT_RUN(worker).
Rootmachineđãconfirmbefore/afterexactvàuniqueall22anchors.
Firstpreflightrootdừngtrướcinferencevìmộtrolelabeltrùng2bảng;
neo thêmfollowingrowđúngowner,khôngtínhworkerfailure/khôngappchange.
AppLFhashportal c59c7676dcb1e7f30d404f6d66ac19ab4c8c8ff6d4aa1ff7ea7c7cb428abb591;
i18n e00ccdd40c454eaea71eb361720f915a50444a9eba841f30ae9dd8f5b10f1c79.
HaiappfilekhóaởhashnàytrừkhiACmớicóREDkhảtái hiện.

## AGC-HISTORY-QA — amendment sau hai raw-source failures

Consumer group đã kết thúc:222ca,220PASS/2FAIL. Cả hai failure nằm trong
`tests/gallery-native-history.test.mjs`, ca “current raw app matches exactly
five owned edits”, cho portal.js và portal-i18n.js. Pin GSC giữ nguyên;
không sửa ứng dụng hoặc rebase hash/fixture lịch sử để làm xanh.

QA-only allowlist trước sửa:
CREATE `tests/fixtures/admin-guard-customer-copy-history.json`,
`tests/helpers/admin-guard-customer-copy-historical.mjs`,
`tests/admin-guard-customer-copy-history.test.mjs`;
MODIFY `tests/helpers/gallery-native-historical.mjs` đúng import/hook
AGC inverse trước GSC runtime inverse; MODIFY
`tests/gallery-native-history.test.mjs` đúng raw-reader projection trước
hash comparison, giữ nguyên expected hash, fixture và assertions.
Python/snapshot helper chưa mở khi chưa có consumer RED tương ứng.

Fixture lấy cơ học đúng22cặp đã nghiệm thu và provenance ba conversation;
Support removal có after rỗng phải freeze cả owner before/after và
kiểm owner/slot, không replace chuỗi rỗng. Source inverse chỉ đảo đúng
delta finite; toàn raw current phải trở về GitBASE5f316f29 độc lập.
Pressure phải giữ old/no-signal/idempotence/unknown ngoài owner; từ chối
partial/changed/duplicate/detached/wrong-owner/reordered input.
Primary129ca tiếp tục đọc raw application, không projection.
Root chỉ recovery hai ca đã FAIL sau khi pressure đạt;220PASS giữ.

Browser gate độc lập dùng actual renderer/guard/i18n/CSS trên localhost:
VI/EN/ZH × sáng/tối ×390/768/1440 × sáu trạng thái=108view;36hero
disabled-title cases; sáu ảnh đại diện. Giữ controls/escaping/Tab/44px/
16px/no-overflow/error,0external/API/auth/provider/wallet/proddata.
Đây là component gate, không thay mounted/signed-production proof.

### AGC-QA-FIXTURE — actual action-set precedence

Browser thực dùng WEB_LOCAL_ACTIONS thấy payment-create thuộc tập này,
nên đi qua nhánh local-action trước nhánh topup-catalog như BASE. Diagnostic
GitBASE và current cùng canAct=false; BASE trả câu local cũ, current trả
actionBlockReason.planUnavailable. Không đổi thứ tự/điều kiện ứng dụng.
Primary fixture trước chỉ đặt hai local actions nên tạo reachability giả
cho nhánh topup. Allowlist QA MODIFY
`tests/admin-guard-customer-copy.test.mjs` lấy nguyên constant thực, sửa
đúng ba kỳ vọng payment ở VI/EN/ZH theo precedence thực; chỉ chạy lại ba
ca bị thay input. Nhãn topup riêng vẫn là finite copy đã được giao nhưng
không được ghi là đã có bằng chứng reachable trong runtime.
Browser fixture Telegram-unready phải bridge.available=false để không
mô tả nhầm tài khoản đã liên kết; chỉ sửa runner ngoài repo, không app.

Impact trước QA hook: `git grep -n -E
'galleryNativeHistoricalSource|galleryNativeHistoricalSnapshot' -- tests`
đo5file/11chỗ:gallery-customer-copy.test.mjs:6,80,95;
gallery-native-history.test.mjs:7;gallery-readability.test.mjs:6,30;
helpers/gallery-customer-copy-historical.mjs:6,17,60;
helpers/gallery-native-historical.mjs:40,79 (số dòng trước hook).
Không đổi signature/snapshot; leafAGC chạy trước GSC trên source input.
Đây không phải bằng chứng hạ risk; primary actualapp vẫn đọc raw.
Rootreview pressure phát hiện5foreign enclosing-owner mutation chưa throw;
5RED→21targetedGREEN sau lexical gapguard finite,giữ158PASS trước.
Không sửa app/fixture/pin hoặc chạy lại nhóm consumer đã đạt.

### AGC-PYTHON-HISTORY-QA — sau hai Python raw-source RED

Đã chạy đúng hai parameter portal/i18n của
`test_actual_full_source_is_exact_locked_construction_and_inverse_equals_git_base`:
2FAIL tại line72, actual AGC hashes khác pin GSC như Node đã đo.
Allowlist QA CREATE `tests/helpers/admin_guard_customer_copy_historical.py`,
`tests/test_admin_guard_customer_copy_historical.py`; MODIFY
`tests/helpers/gallery_native_historical.py` đúng import/hook trước transport
inverse và `tests/test_gallery_native_historical.py` đúng raw-reader finite
AGC projection. Giữ nguyên digest assertion, CURRENT construction và fixture
GSC. Dùng lại fixture AGC22record/5owner pin85dc5ee0,không tạo pin mới.
Port cùng owner/slot/context-gap checks; foreign/no-signal/old giữ,
partial/changed/duplicate/detached/enclosing-owner phải failclosed.
Không import app/DB/auth,không snapshot helper hoặc ứng dụng mới.
Pressure mới chạy một lượt; sau root review chỉ recovery hai Python RED.

### AGC-SNAPSHOT-HISTORY-QA — sau ba dictionary RED

Hai consumer Gallery đọc source/snapshot mới chạy130ca:127PASS/3FAIL,
đúng “Gallery vi/en/zh leaves every unrelated fixed message and key
unchanged”. Source comparator đã đạt; snapshot còn thấy19row đổi và12key
AGC mới. Không sửa fixture hoặc kỳ vọng Gallery.
Allowlist QA mở rộng đúng helper/test AGC Node mới và hook đầu
`galleryNativeHistoricalSnapshot` trong `tests/helpers/gallery-native-historical.mjs`.
Export finite snapshot inverse dùng lại22record/5owner fixture bất biến:
old19row đúng locale/order trả nguyên array; new31key đúng value/order
khôi phục19row và loại đúng12newactionkeys. Unknown pairs giữ identity/
order/bytes; partial/mixed/changed/duplicate/reordered/foreign-locale fail.
Không thêm snapshot vào Python hoặc ứng dụng. Root chạy pressure snapshot
mới một lượt rồi recovery đúng3consumerFAILED,giữ127PASS đã có.

### AGC-CI-WIRING

Workflow hiện tại không gọi các suite AGC mới. Allowlist bổ sung MODIFY
`.github/workflows/webapp-quality.yml` đúng hai runlines native Gallery:
append Node primary/history AGC và Python pressure AGC. Không đổi
triggers/permissions/env/actions/dependencies/concurrency/deploy hoặc
các lệnh regression cũ. Local gate không thay exact-head CI.

## Local QA cuối trước bàn giao

Consumer222uniquePASS (220giữ+2recovery);Galleryconsumer130uniquePASS
(127giữ+3snapshotrecovery);PythonGSCrawreader2RED→2GREEN.
Node sourcepressure179 (158+21mới),snapshot34;Pythonpressure198PASS.
Native129ledger:126giữ+3paymentfixturecorrectedGREEN,không cộng132.
Browser108uniqueviews/36disabledhero/6ảnh,0error/overflow/egress,
input16,target44. Sáu ảnh đã xem;Support saufocus không firstpaint.
Khôngđo contrastmatrix/fullmount/auth/device/Safari/signedproduction.
Apphashkhóa giữ;worker-code-failure0;root-app-logic-authored0.
Metadata/provenance/exactCI vàrelease vẫn mở,khôngđóng toàngoal.
