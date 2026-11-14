# CHAT-CONTEXT-LABEL-CONTRAST — 15/11/2026

BASE `87afb6b62dbe14fdc6a4f818161afaa5a0c6399d`,PR737đãtriểnkhai.
MộttrackerIssue689 vàchecklistmẹ. Gap quan sát ở nhãn loại ghi chú sáng:
rule cũ chỉ `.portal-field > label`, saved-context dùng `label > span`.

## Contract

GOAL=nhãn loại ghi chú đọc rõ ở theme sáng, không đổi dark hoặc nội dung.
ALLOWED_APP=`static/portal/portal-theme.css`,exact1EOFappend củaAntigravity.
Một selector:
`html:not([data-portal-theme="dark"]) .portal-chat-workspace-detail .portal-chat-context-edit .portal-field > span`
với duy nhất `color: var(--portal-ink);`.
PROTECTED=toàn CSS ngoàiappend,font/layout/visibility/dark/motion,allJS/
Python/auth/API/route/IDs/caps/constraints/customerdata/ENV/schema/Bot/
route-engine/provider/wallet/PayOS/productiondata.
TEST_ALLOWLIST=one tiny CSSsource regression/strict finite CSSprojection
trong existingtest helper để cácCSSsnapshotcũ vẫn giữnguyênscope.
Không broaden prefixfilter/thêm !important/ẩnlabel hoặc đổistyle khác.
STOP=baseline khôngthựcđo<4.5,unsupportedcolor/background,source/data lệch,
workerproposalngoàimộtappend;không manufactureRED/wholeAXPASS.

Antigravity3.8FlashHighR1conversation4a60bc9a-9694-4249-8f4b-8c420f0f6940
đãtrảđúngmộtOLD/NEW,eOFanchorunique,exactaddition;workerVERIFYNOT_RUN.
Chỉ sourcepublic6a519CSS+oldmarkup+fullMAP,khôngprivatecode/test/data.

## Checklist và bằng chứng cần đạt

- [x] PrerequisitePR737CI43637617007bothPASS,merge/runtime87afb6b6,
  deploy43638826851PASS,treee412a18fexact,services/health/4assets/protected
  Websourcesgiữ;receipts6883936992/6883937294.
- [x] Reviewproposal1literalappendkhớpexactspec,0workercodefailures.
- [x] RootđọcđủPREPcontract/wrapperPY/CJS/transform/observer,
  syntax-only2commandsexit0,khôngruntime/appmutation.
- [x] BaselinefreshownedQA1VI375draftdetailGET;trêncùngtrangđo375light/
 1440dark,actualcomputedRGBAlayers/luminancecontrast;light<4.5thật.
 0forminteraction/no24copyrerun,allcurrentcopy/controls/data giữ.
- [x] TargetedpermanentCSS2=1PASS1REDtrướcapply,exactworkerappend→5GREEN.
- [x] GreenfreshQA cùng1detail/2observations:light>=4.5;dark/sentinel/
  markup/customerdata/IDs/controls/copyexactbaseline. CSSonlyexactappend
  CRLF→LFnormalizationriêngCSS;19othersourcepathsrawexact.
- [x] QA15threads24contexts18turns/8Chattables/schema/evidence/
 6plans18scenes giữ,ownedJob0/noerror/overflow/external/productwrite.
- [x] Source/diff/smallaffectedtests/Pythoncompile/reviewC0/I0/M0;khônglặp
 147/286wordmatrixđãđạtchỉvìđổimộtmàuchữ.
- [ ] Docs/Tester/case/metadata/provenance/exactCI/merge/deploy/runtime/
  assets/receiptcùngIssue689/PR.

HistoryVersionsR1/ActivityR2 đangchuẩnbịgate riêng,kếsaucontrastunit.
Toànlocale/responsive/AX/auth/device/Safari/signedproduction/M-FINAL01..06
vẫn mở,motioncuối. Không engine/financial/runtimecapabilityworktronggoalnày.

## Bằng chứng và sửa bộ đo, không sửa ứng dụng để làm xanh

BASEr1/r2 FAIL được giữ. R2 đo light1.2653297845023375/dark11.52797430592563
nhưng chốt rawDOM giữa hai viewport sai vì chỉ ba control thêm `style=""`.
Bộ đo được sửa giới hạn: giữ rawDOM/hash, chỉ trên clone bỏ đúng empty-style
ở INPUT/TEXTAREA, ghi tag/name/id; parser độc lập và probe bắt đổi name/value/
disabled/nonempty-style/other-tag/whitespace. BASEr3 được nhận, không đổi
nhãn, dữ liệu hay source. Không quy lỗi sản phẩm hoặc worker.

Greenr1 FAIL do object hiện tại có optional undefined dataset keys còn JSON
baseline bỏ các keys đó. Chỉ sửa so sánh tám block về cùng JSON wire shape,
bắt buộc cả hai block tồn tại, giữ rawDOM/computed/semantic/source/dữ liệu.
Không sửa CSS để che lỗi. Greenr2 được nhận:light12.351554732138213,
dark11.52797430592563 exact;sentinel/font/layout/19protectedrawpaths/
source/evidence/data giữ,Jobs0. Một detailGET/twoobservations mỗi lượt,
không lặp24wordmatrix. CSSrawprefix byteexact và LFonlyappend exact.
