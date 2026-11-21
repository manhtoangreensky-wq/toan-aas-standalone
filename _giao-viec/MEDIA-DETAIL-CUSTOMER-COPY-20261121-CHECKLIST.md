# Âm thanh — chữ khách dùng và nhãn dễ đọc

TASK=MEDIA-DETAIL-CUSTOMER-COPY-20261121.
BASE=051b936695638a5f083396194730861dc7831da1.
BRANCH=codex/media-detail-customer-copy-20261121.
STATUS=VISIBLE_UNIT53_LOCAL_GATES_ACCEPTED_RELEASE_PENDING.
TRACKER=Issue689; comment riêng trước BUILD, không tạo issue/PR giữ chỗ.

Đang đọc và áp dụng skill owner-governed-codex cho task này.
Owner cho phép tự tiến hành công việc thường lệ trong plan/checklist.
Không hỏi lại quyền thông thường, không nới các chốt ENV/data/provider/
wallet/PayOS/Bot/route-engine. Giao appcode bằng AntigravityCLI hiện có
gemini-3.8-flash-high/output-only/fullMAP, Rootreview/replayserial.
Chỉ takeover sau hai genuinecodefail cùngfragment, không tínhQA/spec/
transportfaults. Giữ bằng chứng đã đạt, retestfailed hoặc chưa thực thi.

DependencyPR784 đã đóng:CI44873207140haiSUCCESS,18browser/
456authhash exact,merge/runtimeBASE,deploy44875068636SUCCESS57s,
VPS/assets/buildlocal-62837b0afde36085a637 vàreceipts
Issue7049170333/PR7058572307 đọc lại đúng. Không mở lại/rerunđơn vị đó.

## Hàng đợi và kết quả cần đạt

| Thứ tự | Spec | Dependency | Kết quả mở khóa | Trạng thái |
|---|---|---|---|---|
| 1 | MDCC-READ | PR784closed | Inventory chữ/control thực,consumer scan,đủnhãnVIENZH,baselinecontrast đo thật | ACCEPTED_DIAGNOSTIC_NOT_CONFORMANCE |
| 2 | MDCC-CONTRACT/RED | READ | Chốt từngOLD/NEW/copyrow/allowlist,physicalRED vàma trậnnative/tracker | ACCEPTED |
| 3 | MDCC-PAGINATION | RED | Phân trang tệpâmthanh đúnglocale,khôngđổiquery/route/action/callerkhác | ACCEPTED_LOCAL |
| 4 | MDCC-DETAIL | RED | Bỏđúngkhung/câukỹthuật dư,giữform/tên/quyền/phiênbản/history/nútthật | ACCEPTED_LOCAL |
| 5 | MDCC-FIXED-COPY | sharedconsumercontract | Lời nhắc/validation/writefallback đúnglocale,giữrawserver/customer/payload/guards | NEXT_LOCKED_UNIT_AFTER_VISIBLE_DELIVERY |
| 6 | MDCC-CONTRAST | MEASURED_READ+RED | ChỉnếuđothậtFAIL:selectorhữuhạnđạt4.5:1,khôngđổitheme/layout/motion | ACCEPTED_LOCAL_22_KNOWN_RECOVERIES_NOT_GLOBAL_CONFORMANCE |
| 7 | MDCC-VERIFY | proposals | Rootserialreplay/physicalGREEN/sourcepins/historical/protectedregression/review | ACCEPTED_WITH_FOUR_EXACT_BASE_PYTHON_FAILURES |
| 8 | MDCC-NATIVE | VERIFY | ControlsignedGET/VIENZH/mobilePC/ảnh/nhãn/finitecontrast/isolation/owned0; keyboard/globalAX giữ queue | ACCEPTED_FINITE_SCOPE_R1_R2_R3_COMPOSED |
| 9 | MDCC-RELEASE | Native/Tester/prepush | MộtPR/exactCI/artifacts/merge/exclusivedeploy/VPS/assets/receiptreadback | WAITING |

Note: chia plan chi tiết từngspec có kếtquả để mởspec tiếp theo; các
proposal độc lập output-only có thể giao đồng thời, không sharedwrites.
Không sửa ứng dụng trước RED hoặc workerproposal đượcreview.

## Checklist bằng chứng

- [x] DependencyPR784closure và localcleantracked,BASE/branch đúng.
- [x] Inventoryconsumer và chữ đang hiện:detail/media+audiohub/pagination/
  validation/hand-off/writefallback. Không lấysourcegrep thànhUIproof.
  RootVMđối chiếu411giátrị/137keyvà40fixedliteralđúngnguồn;
  inventoryRAW9a295ce620089b7b7f22d99092e773e78eec9df59ed70cd670abb0dd57fa3410.
  95primary=83detail+12board;42support;4dormant khôngnhậnsửaUI
  chỉbằngđổikeykhôngdùng. Sharedsafety8callersvàline14callersghiđủ.
- [x] Đo foreground/alpha/background ancestry nhãn thực ởsáng/tối;
  ảnhmờkhôngtựthànhratioFAIL. Chuẩn bịrunnertrước, Rootadopt rồi chạy.
  Baselinereadchốt6viewVIENZH×320dark/1440light,12detailroots/
  12PNGfullpage(heightthựctừIHDR),3formthậtcollection/filter/attach.
  ItemformchưacótrongseednênghiNOT_PRESENT,khôngnhậncoveragegiả;
  candidateitem-formcoverage cònphảichốttrongcontractcuối.
  Readbaseline151rawLF/specMAPchecklistcodefreeze;metadata165/
  3register3login/0blob/productwrite/provider/ví;group480s/start60/
  action10/cleanup5/PNGdecode30,observer72read60s/app120khôngđổi.
  NềnkhôngxácđịnhtrảUNDETERMINED,chỉsốđothậtđượcdùngmởCSSscope.
  R1diagnosticrun01NOT_ACCEPTED/0PNG/owned0:observerđòibaform
  cùnghiệntrongscrollviewport,dù3formthậtđủcontrols/enabled.
  Giữfalse receipts/source151/core/schema/auth/egressunchanged.
  R2chỉQA:cuộnthậtđếntừngcontrol,đogánlabel/helpđúngvịtrí,
  giữnguyên120control/600textrunvàcácboundđãchốt;khôngCSS/DOM/
  value/capability injection. 12PNGlàfinalscrollpose,khônggiảvờảnh
  fullPagebaoquáthếtinnerscroll. ChưađođạtkhôngnhậnCSSfixed.
  R2run02NOT_ACCEPTED/0acceptedview/0PNG/owned0: bộđo dừng tại
  tags ở form gắn tệp vì cổng QA cấm ghi nhận thiếu nhãn. Không tính
  thành lỗi code worker hoặc kết luận nguyên nhân AX khi chưa có facts.
  R3chỉQA: giữexact-one-control/native-scroll/bounds và mọi cổng
  source/core/schema/auth/egress/PNG; ghi finding nhãn thiếu/rỗng với
  field.labels/for/ARIA/duplicateID/DOM/paint hữu hạn, không dựng nhãn.
  Lưu partial measurement ngay từng control, complete=false tới hết
  vòng. Baseline complete có thể có FAIL/UNDETERMINED/AX findings;
  không đồng nghĩa tương phản/AX/app đạt. R1/R2 giữ nguyên.
  R3run03terminalexit0:6views/12roots/264controlobservations/
  12freshPNGđủSHA/CRC/IEND/full-decode;source151rawLF/core/schema/
  checklist/MAP/code exact,3login audit đúngkhôngcórowkhác,
  productwrites/provider/ví0,ownedactive0. Root receipt:
  media-detail-contrast-baseline-root-reviewed-nov21.json.
  Đo308PASS/108FAIL/280UNDETERMINED associations,khôngphải108node
  unique;12AXfindings đềuattach.tags do2portal-field-tags cùngID,
  cả2label trỏfirstcollectioninput,attach.labels[]. ChưađạtUI/AX.
  READ diagnostic đãđủ; item này chỉtick saucandidate fixes/QA.
  ThêmMDCC-FORM-NAMESPACE trước nativecandidate: chỉcaller namespace
  riêng cho form/row âmthanh,không đổi renderFields dùng chung,
  fieldname/value/action/DTO/UUID/capability/history.
  SauREAD terminal/owned0, mỗi spec có RED+exactproposal+contract riêng
  được replayserial vàGREEN; khôngcần giữappBASE chờspecđộc lậpkhác.
  Nativecandidatecuối vẫnchờtoànunit applicationgatesđủ.
- [x] ContractchốtfullcopyVIENZH/phạmvi/điềukiệnbỏpanel/AC/native,tracker.
- [x] PhysicalREDtái hiện, khôngsyntax/setupfault hoặcmirrorassertion.
  Phầnpaginationđãđo19ca/7PASS12assertionRED/0skip/0setupfault,
  hai detailroots×VIENZH×range-empty;non-audiotuples giữBASEexact.
  Bằngchứngmedia-detail-audio-pagination-red-nov21.xml,
  RAWsha d1f80200ace7108b9b6aeec462b9443c768ce2eb71b53d2b337af372e2e860a1.
  Chưa nhậnfullunitRED hoặcappfix.
- [x] NhiềuphiếuAGYđộc lập/fullMAP/publicsources/modelđúng;rootreplayserial.
  Phântrang R1 đã trả exact3records/modelgemini-3.8-flash-high/exit0,
  proposalRAW3fc0a55766e0146dffc9f53b283d02c998ae0110f48a4aab918cafa886d4f843;
  applicationwrites0/codefail0/takeoverfalse. Chưa replay khi151BASE
  đang chờ đo. Không hỏi lại quyền cho việc thường lệ trong checklist.
- [x] GREEN/151pins/protecteddomains/historical/reviewmộtlượt.
  Pagination19GREEN;detail+namespace33GREEN/0FAIL/0skip;2appJSsyntaxPASS.
  ForwardBASE+52exactrecords trên3appfiles;148protectedRAW/LFexact.
  Fixture reviewedRAW0f70cfcad4ba7c71e8930caebdcc177b848fcc13078ace59a2cfa9498273e002.
  Groupedsource/history193ca=191PASS2FAIL dohistpr782 cũ khóaaudio
  pagerchữVI. Sửaduy nhấtinputhistoricalprojector của3consumerchecks,
  retest3changed→3PASS;khôngđổiapp/fixturecũ hoặc lặp190PASSkhôngđổi.
  Currentraw52record/151pin acceptance khôngdùnginverseprojector.
- [x] Nativecurrentcontrols/data/ảnhdecode/finitecontrast/nhãn/isolation.
  Keyboard/globalAX/Safari/device vẫn là mục toàn goal, không nhận đã chạy.
- [x] Ops/crosswalk/master/Tester/audit/manifest/secret/excludeallstate.
  Final supplement0Critical/Important,4565uniqueNodePASS/0FAIL/0skip,
  đúng149locale files,4303selected+262imported-ownercases.
  Metadata1PASS/32deselected;manifest35scoped+2provenance dựkiến,
  támstateexcluded/secret0/source151/protected148/diffcheck.
- [ ] MộtPR/exactHEADCI/artifacts/merge-tree/exclusivedeploy/VPS/receipt.

## Phạm vi dự kiến, chưa BUILD

Ứng dụng dự kiến portal.js/integration.js/portal-i18n.js; nếucontrast
đoFAIL thì bổ sung selectorportal-theme.css chínhxác vào contracttrước
proposal. Không đổi sharedsignatures/validationrules/requestorder/
DTO/UUID/rawmessage/idempotency/revision/storage/auth/readers/API/engine/
wallet/provider hoặcmotion. Mọifilekhácprotected151.

Fullcustomerdata literal giữ nguyên, kể cảtextAnh đãlưu. ChỉfixedUI/
fallback doapp sở hữu đượcdịch. Không biến "không tạo âmthanh ở đây"
thànhlời hứađầura; chỉgiữ giải thíchcầnthiết cho kháchbằngcâudễhiểu,
bỏkhungvôdụng khôngmất chức năng. Productwritesnative/provider/ví0.

WholegoalACTIVE/incomplete;locale/AX/auth/device/Safari/signedUI và
genericfocus giữqueue;motionM-FINAL01..06cuối.

## Khóa đơn vị giao hàng trước khi QA candidate

Theo Owner “nào xong merge/deploy cái đó”: đơn vị hiện tại chỉgiao
chữvisible/detail/pagination/nhãn/màu đãchốt52records/3appfiles.
MDCC-FIXED-COPY làđơn vị kếtiếp ngay saudelivery,khôngtickhoặcnhậnxong.
Lýdo ranhgiới:3safetyliterals dùnglàmstablekeys ởMusic/SFXerrorclassifier;
thayproducerchung sẽchạm ngoài visibleunit. Producer/classifier cùng
integration.js giữBASEexact; đơnvịkếtiếp chỉconsumer presentation với
comparatorrõ trướcRED. Không sửa khác rồi giữtreo mộtPR,không bỏviệc.

Candidatefresh6views×2roots/12PNG có1metadataitem/owner trongDBtạm,
4formthật gồmitem-update;full52forward/148protected/151candidatepins;
spec/checklist/MAP/QAinputsfreeze,JSONLcontroljournalbounded,code/
schema/core/authaudit/egress/owned0. Khôngfill/submit/download/player/
provider hoặc fakeDOM/CSS/response. UnknownpaintUNDETERMINEDgiữ;
candidateDiagnosticComplete không phảiAXconformance hoặcscopedPASS.
R1packetA/B/C HTTP400 schemaenum làlỗiRoot, giữreceipts;R2minimum1
đãtrảexact43/4/2records,workerfail0/takeoverfalse. Khônglogin/settings.

CandidateR1terminal149.399s/384controls/12PNG:diagnosticaccepted nhưng
scopedfalse,0label/0duplicateID;427PASS22FAIL163UNDETERMINED.
22FAIL chỉMedia/light itemform mớiđượcđo;18copyfindings là2readerQA
đãxácđịnh(requiredstar/mainheadinglồng),khôngđổiappcopy.
MDCC-ITEM-CONTRAST R1 mớiđãtrảexact1record,proposalRAW
8d0024abe765b6d7d238c91145c9bf2e1330c6bc00bf3d022adef1b675a8c243,
Rootreplayđúng1CSSrule,khôngsửaHub/dark/token/layout/JS.
Current53records/5proposalworkers,fixtureRAW
a2209d2a371b0323480cadaa01d1726ac330c5fc6c3cc5473b13df8726fd79bd.
Sourcegate13PASS xácminhfull53forward/151pins/148protected vàprovenance.

Groupedreviewkhôngcònfindingmở;1ImportantQAcoveragefixturegợiý thiếu
3receiptflagsđãsửa,6changed+1negativecase→7PASS,appkhôngđổi.
Regressioncurrent141files4388cases=4361PASS27FAIL; chỉlegacyCSS
golden/currentcataloguereference cầnfinitehistoricalinputmigration.
Giữ4361PASS;retest17file-slices failed/previouslyunexecuted/changed
source53gate→allPASS0FAIL0skip,khônglặpfull141 hoặcworkerproposal.
R2native mới chỉ18failedcopyreaders+3Media/light itemform(30controlpieces);
giữ354controlproof và9PNGR1khôngbịCSSrulemớikhớp. 3freshPNG+9retained,
khônggọi12fresh;414passedcopycheckrecordsgiữ,432distinctchecks=414+18.
163unknownpaintkhôngtựPASS/globalAXclaim. Tấtsource53/148protected/
currentdocs/MAP/QAdeps/R1receipts vàPNGhashfreeze trướcbind/run.

## Candidate R2 kết quả và R3 QA-only contract

R2 terminal 135.138s, diagnostic accepted/scoped false. Ba ảnh mới đã
giải mã đầy đủ + chín ảnh R1 giữ nguyên; 30 control pieces mới thay đúng
30/384, giữ 354. Không label finding, duplicate ID hoặc contrast FAIL.
21/22 known recoveries đo PASS; năm fresh UNDETERMINED gồm một label
favorite ZH/light và bốn association khác, không tự nâng thành PASS.
163 unknown trước đó giữ NOT_CLAIMED. Source151/current53, schema,
product core, auth audit, code, egress, owned0 đạt comparator.

12 copy findings còn lại là QA kỳ vọng thiếu hậu tố hỗ trợ trình đọc:
VI `Bắt buộc`, EN `Required`, ZH `必填`. Actual required=true, đúng
một label và label.control liên kết đúng. Không xóa hoặc sửa ứng dụng.
R3 đối chiếu offline exact native actual text = fixed label + đúng
hậu tố đã biết, actual required/association facts và frozen53source;
không strip tùy ý, không gọi đây là phép đo hình ảnh mới.

R3 chỉ native một root ZH/light 1440×900 Media, một control favorite
(index6), một PNG mới. Giữ 383 control proofs và 11 PNG đã pin/hash.
Chỉ loại possible cover khi computed position absolute/fixed và
clip rect hữu hạn theo px có diện tích toán học bằng 0; ghi clip,
position, bounds và lý do rõ. Không loại theo classname, không đoán
nền, không bỏ unknown clip. Cần actual ratio >=4.5 cho label cuối.
21 recovery đã đạt và sáu Hub titles giữ nguyên; chỉ đo thiếu, không
lặp whole batch. Bốn fresh unknown khác +163 unknown cũ vẫn chưa nhận
conformance. Các bound startup60/action10/group480/cleanup5/PNG30/
read72per60s/app120 cùng source/core/schema/auth/egress/owned0 giữ.
Mọi receipt R1/R2 scoped false giữ nguyên, không ghi đè lịch sử.

R3 terminal exit0/11.668s, bindingRAW
e1ecf0a77fec665510c06b8d940f37fa39291ec15bc911bdde63a71b4c0aef9b.
DiagnosticAccepted=true/scopedAccepted=true; actual favorite label
`标记此音频` ratio12.351554732138213 trên ngưỡng4.5. Actual computed
cover absolute/rect(0px,0px,0px,0px) được ghi bounds và zeroarea,
không đoán nền. 21retained+1fresh=22 known recoveries;12offline exact
required-annotation checks và6HubtitlePASS giữ. Một controlpiece mới
+383retained=384distinct;1newPNG giải mã+11retained hash exact.
Source151/current53/core/schema/auth/egress giữ, owned0; không
productwrite/provider/ví. R1/R2 false receipts còn nguyên. 163+4 unknown
không thành PASS; globalAX/contrast/signedproductionUI/output chưa nhận.
