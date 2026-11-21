# Âm thanh — chữ khách dùng, phân trang và nhãn

TASK=MEDIA-DETAIL-CUSTOMER-COPY-20261121.
PRODUCT=standalone WebApp.
REPO=manhtoangreensky-wq/toan-aas-standalone.
BASE=051b936695638a5f083396194730861dc7831da1.
BRANCH=codex/media-detail-customer-copy-20261121.
STATUS=VISIBLE_UNIT_53RECORDS_LOCAL_GATES_ACCEPTED_RELEASE_PENDING.
TRACKER=Issue689; một comment hiện hành cho đơn vị, không issue/PR giữ chỗ.

Đang đọc và áp dụng skill owner-governed-codex cho task này.

## Quyền và thứ tự

Owner: “trong plan và checcklist thì cứ tự động cho phép không cần hỏi
lại tôi”. Việc thường lệ tự tiến hành; không đổi ENV/credential/data/
Bot/route-engine/provider/wallet/PayOS. Nhiều proposalCLI Antigravity
hiện có,modelgemini-3.8-flash-high,output-only/fullMAP; Rootserialreplay,
chỉtakeover sau hai genuinecodefail cùngfragment. Khônglogin/settings.

DependencyPR784 đã giao:CI44873207140haiSUCCESS,18browser/456authhash,
merge/runtimeBASE,deploy44875068636SUCCESS57s,source/services/assets/
buildlocal-62837b0afde36085a637 vàreceipts7049170333/7058572307 exact.
Khóa kết quả này, không lặp test/native/CI của đơn vị trước.

Checklist mẹ:_giao-viec/MEDIA-DETAIL-CUSTOMER-COPY-20261121-CHECKLIST.md.
READ inventory nguồn đã nhận; phầnphântrang cóAC/RED/OLDNEW dưới đây
đãkhóa. Proposal output-only được giao độc lập với baselinecontrast;
không ghi app trong lúc native giữ151nguồnBASE. Rootchỉreplay sau
baseline đãterminal/dọnowned0 và contract của chínhspec đượckhóa.
Amendment sauREAD: specđộc lập đãđủRED/exactproposal được replay
serial ngay; chỉnativecandidatecuối chờđủmọi applicationgate củaunit.
DETAIL/FIXED-COPY/CONTRAST chưa READY cho applicationproposal trước
khichữ/selector/RED của chínhspec đó chốt; không worker tựthiết kế.

Note: chia plan chi tiết từng spec có kết quả mở khóa; specđộc lập
output-only chạy đồngthời, phầngiữsharedmutableapp luônserial.
Mộtbranch/mộtPR sau toànunitlocalgate; không dùngPRlàmchỗlưu tạm.

## Bằng chứng READ

RootVMđối chiếu137key/411giátrịVIENZH và40fixedliteral với nguồn thật:
95primary(83detail+12board),42support,4primarykhôngcóconsumer.
InventoryRAW9a295ce620089b7b7f22d99092e773e78eec9df59ed70cd670abb0dd57fa3410.
Không nhậnsourceinventory hoặc tríchhàm thànhnativeUIproof.

Sharedimpact đãđo trongmộtbundle:

| Symbol | Runtime callsites | Ranh giới |
|---|---:|---|
| renderMemoryPagination | 10 | Chỉtupleaudio đượcđổicopy;chíncaller còn lại giữ |
| audioWorkspaceText | 330 | Khôngđổihelper/chữký hoặc dịchdữliệukhách |
| mediaWorkspaceSafetyError | 8 | CóMusicComposer/SFX/MusicLibrary/review;phảicócomparatortrướcđổichữ |
| mediaWorkspaceLine | 14 | Khôngđổinormalize/length/NUL/returntype/chữký |
| mediaWorkspaceContent | 2 | KhôngđổiCRLF/trim/giớihạn |
| mediaWorkspaceTags | 2 | Giữsplit/array/firstspelling/dedup/casefold/16limit |
| mediaAudioAssetFilterPayload | 4 | Cólisting/hydrations,khôngchỉsubmit |
| mediaCollectionPayload | 2 | Cảcreate/update,giữDTO/tokens/customervalues |
| mediaItemPayload | 1 static dispatch | Cảattach/update;detachpayloadriênggiữ |

Khungcomposer vàHubboard cócontrol/kếtquảthật, khôngxóa cảkhung.
Khungportal-media-detail-boundary chỉgiảithích+renderNotes(page);
nếu bỏ thìbỏđúngwrapper/khônghộptrống vàkhôngđổi sharedrenderNotes.
Sáu câu review-pack lâncận vàUIchange-request riêng giữqueue phụ,
không âmthầmmởrộngphạmvi hoặc nhận đãsạchtoànapp.

## MDCC-PAGINATION — frozen R1

Risk=BOUNDED_SHARED_PRESENTATION; worker chỉtrảproposal,khôngwrite.
ALLOWLIST=static/portal/portal.js,static/portal/portal-i18n.js.
MAX_APPLICATION_FILES_FOR_THIS_SPEC=2.
Chỉ ba canonical replacements sau, mọi byteappkhácprotected.

1. Trong renderMemoryPagination, thayđúng nhánh chọnchữ:

OLD:
```javascript
    } : className === "portal-media-pagination" && action === "media-workspace-page" ? {
```

NEW:
```javascript
    } : className === "portal-media-pagination" && (action === "media-workspace-page" || action === "media-audio-page") ? {
```

2. Trong renderMediaAudioAssetPagination:

OLD:
```javascript
    return renderMemoryPagination(listing, "audio Asset Vault", "media-audio-page", route, "data-media-audio-offset", "portal-media-pagination");
```

NEW:
```javascript
    return renderMemoryPagination(listing, audioWorkspaceText("pagination.audioFiles", "tệp âm thanh"), "media-audio-page", route, "data-media-audio-offset", "portal-media-pagination");
```

3. Thêm đúng mộtkey/ba giátrị trước verifyEqualKeysets/deepFreeze:

| Key | VI | EN | ZH |
|---|---|---|---|
| audioWorkspace.pagination.audioFiles | tệp âm thanh | audio files | 音频文件 |

Dùng baObject.assign theo locale, không đổi bất kỳkey/giátrị cósẵn.

### Acceptance và test

- AC-P1: Hai detailroots hiểnthịrange/empty/núttrước-sau/ARIA đúng
  VIENZH. CâuVIkhônglẫnAudio/AssetVault; EN/ZHkhôngrơi vềVI.
- AC-P2: Route/action/dataoffset/classes,calculation/guards/buttonattrs,
  no-page→emptystring giữ; không thêmnhánhpath hoặcđổichữký.
- AC-P3: Chíncallernonaudio cùnghai nhánhimagereference vàlookalike
  class/action đều giữfullBASEoutput; helper khác/renderdata giữ.
- AC-P4: Fullphysicalportal/i18n/mộtobservationexposure/0appfunction
  replacements, khônginverseacceptance; inputsđóngbăng/0sideeffect.
- AC-P5: Catalogueequal/frozen, đúngnewkey3values; customerdata giữ.

RED:node --test tests/media-audio-pagination-locale.test.mjs
→19ca/7PASS12assertionRED/0skip/0setupfault.
RAWreceipt d1f80200ace7108b9b6aeec462b9443c768ce2eb71b53d2b337af372e2e860a1.
Sauđóbổsunghaiimagereferencetuples vàchỉretest3caseảnhhưởng→3PASS,
khônglặp12RED hoặc bốnPASSkhôngđổi. Chínconsumerđủ,không cộng3retest
thành22ca unique.

Verify sauRootreplay:19PASS0FAIL0skip;node --check haiappfileexit0;
forwardcurrentBASE+3records vàsource151 soexplicitallowlist.
Workerverify=NOT_RUN. Lệchkỳvọng phảighiDEVIATION, khôngtựsuyPASS.

## MDCC-DETAIL/FIXED-COPY — preparation gate

### MDCC-DETAIL-COPY-A/B — frozen R1 after Root review

Hai proposal output-only độc lập; Root replay serial. A chỉ 46 hàng
chữ VI/EN/ZH (45 override hiện có + một placeholder), 42 fallback
expressions và một catalogue append, tổng43records. B chỉ4records:
bỏ3span noAudioAction/noProviderAction/attachFooter và trọn khung
portal-media-detail-boundary; khôngđổi sharedrenderNotes hoặc để ôrỗng.
Mỗi OLDcount1;46portalspans khôngchồng nhau. Composer/Hubboard,
forms/buttons/rights/history/download/handoff/customerdata giữ nguyên.

Hợp đồng nguồn đã Rootreview:
media-detail-copy-contract-prep-nov21.json RAW
4c2d971971552e884b16ad1f8785ae8e1f910fa9bdf377cacdf80c69b92bf7b7.
Literal packets được dựng bởi media-detail-copy-dispatch-nov21.cjs;
expected.json/packet.md/schema/proof riêng immutable cho A vàB.
FullactualMAP và3publicBASEsources đãđối chiếuanonymous exact.
Root sửa đúng composeEmpty trướcdispatch: “Gợi ý chưa được lưu.
Hãy sao chép nếu muốn giữ lại.”; EN/ZH tương ứng, không hứa lifetime
củaRAM hoặc tạoâmthanh. Đây là sửa contract, không lỗi worker.

AC-D1: Copy/nút/gợiý/placeholder của detail hairoots đúngVIENZH,
fallbackVI đúng khi thiếu translator, không dịch customerdata.
AC-D2: Bốn explanatorynodes biến mất, không mất nút/field/form/card
result/handoff/download/confirm/history/capability.
AC-D3: Chỉ copy/text-bearing attrs thay; controlnames/actions/routes/
values/options/range/required/disabled/revision giữBASEexact.
AC-D4: Nguyênphysicalportal+i18n/một exposure/0functionreplacement/
frozeninputs/0sideeffects; title/tags/customerHTML giữescapedliteral.
RED27unique=13PASS14assertionRED/0skip/0setupfault; sáu noteschecks
đã bổ sung precondition chứng minh BASE thật sự có3note và chỉretest
sáu ca đó→6assertionRED cùngreason, không cộng thêmcaseunique.
Lệnh: node --test tests/media-detail-customer-copy.test.mjs
GREEN sauA+B:27PASS0FAIL0skip. Native/AX/contrast vẫn làgate riêng.

Kếtquảcầnđạt:kháchchỉthấychữcầnthiếtbằnglocaleđangchọn,không
câumô tảCSRF/API/owner/runtime/provider/idempotency/metadata/draft-only
hoặckhunggiảithíchdư. Khôngđổiquyền/form/control/renderresult/UUID/
revision/history/date/events/downloadavailability/payload/backend.
Giữrights/policynote cầnthiết,khôngbiến trangvănbảnthànhlờihứa
tạoâmthanh. Mọititle/brief/tags/file/license/customerfield truthy và
rawservermessage/error giữ, chỉfixedUI/fallback đượcdịch.

Phảikhóa OLDNEW/copyrows/AC vàphysicalRED từngspec trướcgiao. Đây
không phải phiếu cho worker tựchọnxóa/bổsungngoàiallowlist.
Handoffrevalidation/currentness vàsubmission/idempotency/busy/
acknowledged/refresh/navigation đặcbiệt protected.

## MDCC-CONTRAST — READ gate, chưa được sửa CSS

### MDCC-FORM-NAMESPACE + MDCC-CONTRAST — frozen R1

Rootđãđọcfacts12AXfindings: attach.tags cólabels[],IDtags lặp2,
cả2forlabel trỏfirstcollectioninput. Khôngsửa renderFields shared.
Chỉ1record thêm5thargument `"media-item-attach"` vào đúngcaller
renderFields(mediaAttachFields(...),canAttach,context,defaults).
Bảyname/value/action/capability/payload giữ; cácID/for/help của đúng
form đượcnamespace cùng nhau, collection/filterIDs cònnguyên.
SáuphysicalRED(VIENZH×2roots) đềuassertionFAIL đúngnamespace/0setupfault;
GREEN: node --test tests/media-detail-form-labels.test.mjs →6PASS.
Consumer scan không có hardcoded portal-field-tags/asset_id trong
runtime static/portal hoặc scripts/ci; không đổi fieldnames/API.

Chỉ1recordCSS append4rule sauanchor darkvaultdropzonesmall đãpublic:
light2detailroots×3formcollectionupdate/audiofilter/itemattach:
field>label→var(--portal-ink),fieldhelp/formnote→var(--portal-muted);
lightaudiofilterbackground→var(--portal-surface-soft);
darkaudiofilterformnote→var(--portal-ink). Khôngđổi token/font/layout/
spacing/focus/motion hoặc globalthemerule.
RED là đoactual108FAILassociations trongREADR3, không phải testgrepCSS.
Candidate phảiđo node cònhiểnthị≥4.5 và nhãntrỏđúngcontrolthật;
280UNDETERMINED khôngtựbiếnthànhPASS. Itemformpopulated chưađượcđo
khôngnhậnđãsửa. Gói2records literal:
media-detail-labels-agy-nov21-r1/expected.json,fullactualMAP/
4publicsources anonymousexact,khôngtest/APIresponse/customerdata.

Baseline151BASEexact,6viewsVIENZH×320dark/1440light×2roots,
12newPNGactualfullpageheight; chỉmetadata165/3register3login/
childfakesecret/0blob/0productPOST/provider/ví. Source/core/schema/
auth/egress/owned0 vàảnhhashCRCdecode giữ. Flagsaudiooperations/
changerequestsfalse. ItemformNOT_PRESENT_IN_NATIVE_SEED; candidate
coverageitemform vẫnphảichốt, khôngnhậnproofgiả.

R1observeryêucầubaformcùngvisiblekhôngphùhợpinnerscroll;0accepted/
0PNG/owned0/sourceheld,false receiptgiữ. R2dùngnative scroll
từngcontrolthật,khôngCSS/DOM/value/capabilityinjection;khônggiảm
ngưỡnghoặcmởrate. Group480/start60/action10/cleanup5/PNG30,
observer72read60s/app120giữ. MộtđođầyđủcóthểgồmFAILhoặcUNDETERMINED;
khôngđượcnhậnconformance từscreenshotmờhoặcgiảđịnhnềntrắng.
ChỉmeasuredFAILselector đãRootreviewmới mởCSSproposal.

## Các cổng còn lại và toàn goal

Đơnvịvisible hiện tại chốt52records/3appfiles;Rootđãreview4proposal
exact3/43/4/2,replayserial,19pagination+27copy+6namespaceGREEN.
Fixturetests/fixtures/media-detail-customer-copy-reviewed.json RAW
0f70cfcad4ba7c71e8930caebdcc177b848fcc13078ace59a2cfa9498273e002
bind47copyrows(45override2new)/151pins/9boundedhistoryfragments.
integration.js cùngstableMusic/SFXerrorclassifier giữBASEexact.
MDCC-FIXED-COPY phảiđơnvịkếtiếp ngay sauvisible delivery,chưađạt/
khôngtick. ScopeboundarynàygiữlệnhOwner giaođếnđâuđứtđiểmđếnđó,
khônggiữvisiblefix chờconsumerpolicycontracts ngoàiphạmvi3file.
SổtheodõiIssue689 cùngcomment,khôngissue/PRtrốngmới.

CandidateQA mới thêm3syntheticowneditems trướcDBsnapshots,khôngproduct
POST/schema/blob/collectionrevision/history/policychanges. SignedGET
đối chiếu1item/owner và4formđủ;6views/12roots/12freshPNG;
label.control/field.labels/duplicateID/locale/controlvalues/history/
actualpaint+journal/isolation. 52recordexpected vàBASE3snapshots pin;
148protectedRAWLF/candidate151/spec/checklist/MAP/QAhashfreeze.
Đođầyđủcófindingvẫngiữdiagnostic;scopedaccept riêng,UNDETERMINED
khôngsuyPASS,keyboard/Safari/device/globalAX/signedproductionUIchưanhận.

### CandidateR1 kết quả và prerequisite MDCC-ITEM-CONTRAST

Run01terminalexit1 nhưngdiagnosticaccepted:6views/12roots/384control
observations/12freshdecodedPNG/149.399s,source151/code/core/schema/
authauditexact/owned0;0label/0duplicateID. 427PASS/22FAIL/163UNDETERMINED
paintassociations. Các22FAIL còn lại thật sự là8nhãn/help khácnhau của
item-update trênmedia-workspace/light,RGB220,230,238 trênwhite ratio1.2653.
Chỉmở1CSSrule lightMediaDetail itemform>labelspan/small/checkboxspan
→var(--portal-ink),khôngđổiHub/dark/layout/JS/motion hoặc52recordđãđạt.
Đây làformmớilầnđầuđượcđo,khônglỗiworker củagóitrước.
GóimớiMDCC-ITEM-CONTRAST R1/fullMAP/outputonly/1record/schema minimum1;
Rootreview rồireplayserial,forward53/candidatepinsmới.

18copyfindings làQA:12lầnlabel córequiredstar bịextractnhầmspanẩn
thaychoactualtextnode,6lầnHubselectorh2 lấycảtitlecủareviewpacklồng.
Khôngđổichữứngdụng;R2QA phảiđọcactualtextnodes,loạiaria-hidden và
scopeheadingchính. GiữR1falsescopedreceipt;khôngtínhworkerfail.
R2chỉretestfailedcopychecks và3Media/lightcontrastslices;nhữngsource/
control/locale/paint đãđạtkhôngđổiđượcgiữbằngchứngcócomparatorrõ.

### R2 terminal và R3 failed-only contract

R2 diagnostic accepted/scoped false, 135.138s: 30 fresh item controls
+354 retained=384 distinct, ba ảnh mới giải mã+chín ảnh R1 retained.
Không contrast FAIL/label finding/duplicate ID. 21/22 known contrast
recoveries PASS; năm fresh unknown còn lại không được nâng thành PASS.
12 copy findings đều là exact required-label suffix: VI `Bắt buộc`,
EN `Required`, ZH `必填`, đúng native required=true/label.control.
Giữ nhãn hỗ trợ tiếp cận, không sửa app. R3 chỉ đối chiếu offline 12
actual texts với fixed label+known suffix và exact association facts.

Một native root ZH/light 1440×900 Media chỉ đo favorite control index6,
một PNG mới; giữ 383 control proofs, 11 ảnh pinned và 21 recoveries.
Phép đo ghi computed clip/position/bounds của possible cover; chỉ bỏ
cover absolute/fixed có clip rect finite px với zero mathematical
area. Không classname-only exemption, không bỏ unknown clip hoặc đoán
nền. Nhãn cuối phải có actual ratio >=4.5. 163 unknown cũ và bốn fresh
unknown khác giữ NOT_CLAIMED, không nhận toàn bộ contrast/AX.
Frozen53/151pins/docs/MAP/QA/retained-receipts; bound60/10/480/5/30
và rolling72per60s/app120 giữ nguyên. Không app write, control submit,
provider/ví/data thật; owned active cuối=0. R1/R2 false receipts giữ.

R3 đã terminal exit0/11.668s: scoped accepted, nhãn cuối ratio
12.351554732138213, actual clipped cover có computed zero-area proof.
22 known recoveries=21retained+1fresh;12offline annotation/6Hubtitle
checks đạt theo đúng nguồn thật. 384distinctcontrols=383retained+1new;
12 ảnh coverage=11retained+1newdecoded, không gọi là12ảnh mới.
Source151/core/schema/auth/egress/owned0 giữ. 163+4 unknown và global
AX/contrast/keyboard/device/Safari/productionUI/output không nhận PASS.
Ứng dụng giữ đúng53record, không sửa sau native. Phát hành còn mở.

VERIFY→currentforward/sourcepins/historical/protectedregression/
groupedreview;NATIVE→controls/locale/geometry/keyboard/data/ảnh/isolation;
PREPUSH→ops/crosswalk/master7Tester/audit/manifest/secret/excludeallstate;
RELEASE→onePR/exactCI/artifacts/merge-tree/exclusivedeploy/VPS/assets/
receipt cùngtracker đọc lại đúng. Chưa cóbằngchứng thìchưatick.

WholegoalACTIVE/incomplete;locale/AX/auth/device/Safari/signedUI/
genericfocus vẫn mở;motionM-FINAL01..06 cuối.
PROVIDER_CALLS=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_MUTATIONS=0.
