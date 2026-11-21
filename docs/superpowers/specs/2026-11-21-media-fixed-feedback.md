# Âm thanh — lời nhắc nhập, lưu và chuyển bước

TASK=MEDIA-FIXED-FEEDBACK-20261121.
BASE=6f04b8449d7354ca44397c199ccdda77107f577e.
BRANCH=codex/media-fixed-feedback-20261121.
STATUS=LOCAL_NATIVE_ACCEPTED_FINAL_TESTER_RELEASE_PENDING.
TRACKER=Issue689; comment riêng trước gửi worker.

Đang đọc và áp dụng skill owner-governed-codex cho task này.

## Quyền, dependency và trọng tâm

Owner cho tự tiến hành việc thường lệ trong plan/checklist, không
hỏi lại. Appcode qua CLI Antigravity hiện có gemini-3.8-flash-high,
output-only/full physical MAP; Root review gộp/replay serial. Không
login/settings/Git/VPS/ENV/provider/ví/data cho worker. Takeover chỉ
sau hai lỗi code thật cùng fragment; bộ đếm hiện0, takeoverfalse.

PR785 đã giao runtimeBASE,CI44888152941 haiSUCCESS,18browser/
456authhash exact,deploy44890203239SUCCESS56s,VPS3active-running/
trackedclean/health/5+5assets/buildlocal-88468f90c8fb203a50ac.
Issue7058931880/PR7060694584 đọc lại đúng. Không lặp đơn vị đã giao.

Đơn vị này chỉ lời nhắc cố định của15actions âm thanh, không sửa
validation rule/producer hoặc workflow. Phương án presentation-only
giữ ba safety literals làm key ở Music/SFX classifier nguyên byte.
Không đổi chữ ký/helper normalization hoặc tạo engine/âm thanh.

## READ đo thật, không phải native UI

Inventory độc lập media-fixed-feedback-read-inventory-nov21.json,
RAW94f6ef4377f0ee7c3dadf498763b5fff00c8471787ac26da84a2f47201b1dd55.
15actions/tám dispatchblocks;35exactlocalerrors=19fixedliteral
(22sourceoccurrences)+14label/min/maxexpansions+2contentmaximum.
Támtoast/fallback mỗiOLD xuất hiện đúng1lần. Bảyread-feedbackcalls
đãdịch phải giữ; các clearactions dùng object sạch, không validate
fields trực tiếp. Hydration có thể phát sinh cùng lỗi filter trước
try; không dùng điều này để dịch customerdata.

SourceintegrationRAW/LFda56dd5301c49b97873c20ce1ab611fb36636264b9ef1447a5c86359bad9cf29;
i18nRAW/LFf1066794a7ddcb1e55294654094a992dcdb1938d4256d3bc0bde4503847da8aa.
MAPRAW507a4e2a4ad72c9e84e002f3e7090c73e151db1d605cafdc64f2817c79ea039d.
151BASEsourcepins;149ngoài haiappfiles làprotected.

Consumer scan nằm đầy đủ trong inventory: safety8calls,line14,
content2,tags2,workspacefilter3,audiofilter4,collectionpayload2,
itempayload1sharedattach/update. Támproducerfunction +classifier+
mediaReadFeedbackText có exactfunctionSHA,owner:line và callsites.
Catch tại39279..39281 giữ editorial trước payload trước message.

## Literal contract và allowlist

tests/fixtures/media-fixed-feedback-contract.json là Root expected
contract, chưa phải worker/application acceptance. RAW
b1a1293fd200c49ac4348c7e2f9965df6b9d5b0ae83562fff240a1ae013eddbc.
Trong đó có đủ OLD/NEW/35errorrows/8toastrows/129VIENZHvalues,
151basepins/protectedfunctions/15actions; không dùng kỳ vọng tự sinh
từ app để nhận behavior. Canonical11records:

1. MFF-LOCAL-ERROR: hai integration records, helper trước safety
   producer và đúng một biểu thức catch.
2. MFF-ACTION-COPY: tám integration literal expressions, không đổi
   điều kiện result.message hoặc thứ tự tác vụ.
3. MFF-CATALOGUE: một append43keys trước verifyEqualKeysets; không
   sửa bất kỳ key/giá trị cũ. Equalkeysets/deepfreeze giữ.

Hai applicationfiles:
static/portal/integration.js và static/portal/portal-i18n.js.
Không sửa renderer/CSS/motion/auth/backend/API/DTO/UUID/storage/
Bot/route-engine/provider/wallet/PayOS/ENV/productiondata.

QA mới: tests/helpers/media-fixed-feedback-runtime.mjs,
tests/media-fixed-feedback.test.mjs,
tests/media-fixed-feedback-actions.test.mjs,
tests/media-fixed-feedback-source.test.mjs,
tests/media-fixed-feedback-error-boundaries.test.mjs và expectedfixture.
Finite historical adapter chỉ được bổ sung vào allowlist sau
SOURCE_RED cụ thể; không sửa golden/fixture lịch sử để làm xanh.

## Hành vi chính xác

Helper mediaWorkspaceFeedbackText(key,fallback) dùng namespace
audioWorkspace.feedback, trả fallback khi thiếu translator/t,
translation rỗng/nonstring hoặc trả nguyên fullkey. Fallback VI
thuộc Root literal contract; không nội suy customerdata.

mediaWorkspaceErrorText(error) chỉ exact own known message trong
map35rows, không substring/regex/trim/casefold/dynamic labels.
Chỉ object không có property payload/status (kể cả kế thừa hoặc
giá trị0/null/undefined) mới được map; mọi API marker giữ nguyên.
Unknown/near-match/customer/prototype-named messages trảnull,
không mutate Error/status/payload/identity. Không đổi producer.

Genericcatch dùng inline fifteen-action includes trước gọi helper;
nonallowedactions không lookuphelper hoặc đọc thêm errorgetters.
EditorialError vẫn đứng đầu, payload.message/error.message/global
fallback giữ nguyên. Publish/calendar special toast và severity giữ.

15actions: media-workspace-filter/filter-clear,media-audio-filter/
filter-clear,media-collection-create/update/archive/restore/duplicate/
restore-version/compose,media-item-attach/update/detach và
media-audio-operation-handoff. Không include library/editorial/
review-pack hoặc ba page/refreshactions đã giao.

Támtoast/fallback: createbusy,created,saved,lifecycleupdated,
composed,itemupdated,handoffopened vàhandOffsourcemissing.
Mọi truthy result.message thắng bản dịch, rawservermessage giữ;
outputreceipt/guards/API/idempotency/busy/acknowledge/hydrateorder/
navigation/focus không đổi. Gợi ý chỉ được gọi là gợi ý văn bản.

## Acceptance và RED

AC01:35exactlocalerrors/8toastfallbacks đúngVIENZH; missing/key/
empty/nonstring translator vềVI. Unknown/server/customer giữ.
AC02:114realdispatcher invalid-input vectors (19×3locale×2root)
đúngtext/noHTTP/frozeninputs; không giả lập productionfunction.
AC03:8realdispatcher action feedbacks×6locale/root có actual API/
DTO/hydration/navigation/focus/submission assertions trướcasserttext.
30truthy-server-message vectors giữliteral, không dịch khách.
AC04:sharedproducer/classifier/readhelperfunctionbytes giữ và
validpayload/normalization/CRLF/bounds/tags/favorite/UUID/counters/
API/auth/lifecycle không đổi;149protectedRAW/LFBASEexact.
AC05:currentacceptance là BASE+11forwardrecords, không inverse;
historicalprojector hữu hạn chỉ kiểmđầu vào cũ, giữoldgolden/errors.
AC06:finite native/signedtempDB/realcontrols/locale/ảnh/source/core/
schema/auth/egress/owned0; khôngfakeDOM/state/response hoặc paidcalls.
AC07:Tester/prepush/docs/onePR/exactCI/artifacts/merge/exclusive
deploy/VPS/assets/build/receipts; không suy globalAX/wholegoal/output.

Physical RED command:
node --test tests/media-fixed-feedback.test.mjs
→126cases/5PASS121assertionRED/0skip/0setupfault.
Helper sau đó chỉ mở thêm bounded controlledmetadataHTTP để chạy
actioncopy suite, không sửa ứng dụng hoặc thayproductionfunctions.
Giữ126receipt, không cộng lại khi GREEN.

node --test tests/media-fixed-feedback-actions.test.mjs
→78cases/30PASS48assertionRED/0skip/0setupfault.
Mỗi failed case đã qua assertions API/order/shape/navigation trước
copydiff; tám loại thông báo đủVIENZH×2roots. FakeHTTP chỉ ranh giới
VM, không phải realprovider/native/production. Handoff chỉ3GET và
không operationPOST, source/item metadata dạngđầyđủ, khôngfilebytes.

Sourceforward/protectedfunctiongate riêng ba ca:2PASS1assertionRED.
Tổng207uniquecases=37PASS170assertionRED,khôngskips/setupfaults.
BaAGYproposals đúng2/8/1records đãreplayserial;207new+6existingMusic/
SFXcases=213GREEN0FAIL0skip. Reviewgộp phát hiện một gapQA: thêm
6realAPI422known/rawcustomer cases và3fullBASE-vs-candidate physical
Proxy/gettercases cho nonallowedcatch. Receiptđầu9ca3PASS6FAIL do
Root kỳ vọng nhầm role=“status”;actualerrorrole=“alert” đúng. Chỉ sửa
kỳvọngrole vàretest6failed→6PASS,giữ3getterPASS. Tổng222uniquePASS
contexts,khônglặp213;appkhôngđổi/workerfail0. Review0Critical/Important.
Worker không nhận test/fixture/APIresponse/token/login/ENV/customerdata.
Root chạy GREEN sau serialreplay; giữ kếtquả đạt, chỉ retest phần
đổi/sai/chưa thực thi. Chưa có source/native/tester/release không
đánh dấu toàn đơn vị accepted.

## Native contract trước binding

Chuẩn bị6viewVIENZH×320dark/1440light×2roots=12rootobservations;
3realDOMvalidationinteractions/root=36feedback+36newfullPagePNG.
KhôngproductPOST/operationPOST/blob/download/provider;mọiattempt
ngoài initialsignedmetadataGET/auth3login làfindingFAIL. Chỉnative
fill/select/click,khôngDOM/CSS/response/state/function injection.

Case1 collectionupdate.title dùng đúng baASCIIspaces, không “x”.
READ bổ sung portal.js40251:renderer vẫn gọi reportValidity mặc dù
formnovalidate/titleminLength3. Ba spaces phải có actualvalue length3
vàvalidity.valid=true trướcclick;unchangedintegrationtrim sẽ từchối
bằng rowvalidation.collectionTitleLength. Nếu browser khôngcho qua,
ghi finding/khôngforce hoặcbypass. Đây là sửaQAspectrướcRun,khônglỗiapp.
Restoreoriginalfieldbằngnativefill.

Case2 itemattach: chọnopaqueassetUUID từactualownedDOMoption,giữrole
music/licensehợp lệ,tagsnative17distinct TAG1..TAG17→rowvalidation.tagCount;
restoreoriginalvalues. Case3 audiofilter.q native
`password=QA_ONLY_NOT_A_SECRET`→rowsafety.secret;producerđãđothậttrả
đúngliteral,đâylàtesttextgiảkhôngcredential;restoreoriginalq.
Mỗisubmitphảicónewrealtoastnode/rolealert/visible/exactlocaleexpected,
khôngnhậnstaletoast. Khôngthêmngưỡng4500ms;action10s,đodurationthật.

Source151/current11/149protected/10sharedfunctions/spec/checklist/
MAP/QAinputsfreeze;source/core/schema/auth3login-nootherrows/egress/
owned0. startup60/action10/group480/cleanup5/PNG30/reads72per60s/
route24/app120giữ. 36PNGactualSHA/CRC/IEND/full-decode,khôngreuseold.
KhôngnhậnglobalAX/contrast/engineoutput/signedproductionUI. Generic
renderer validitywarning cònVIởnguồn làlocalequeue riêng,không lén
mởscopeMFFhoặctuyênbốtoànappđãsạchlocale.

Historicalamendment sauSOURCE_RED: predecessor13case source suite
vàaudio-readsourcefile đãchạy14receiptrows/4fail (mộtrow là setup-
contractfailure,khôngnhậnthànhmộtbehaviorcase). ChỉmởfiniteMFF
snapshotleaf/reviewedprovenancefixture +composition đầu MDCChelper
vàhistoricalinput/name adaptation của predecessor source suite.
Oldfixture/golden/errors giữ;currentacceptance vẫnforward11khônginverse.
Fixtureprovenance reviewedRAW808d89af0587a53a13bb78e83be5e8fab6f6e7e98240183b9966766ae5febfa6,
9boundedhistoricalregions và3workerproofs. Newleaf17cases+audio-source24
previouslysetupfailed=41PASS;predecessor3failed-only→3PASS,giữ10PASS
còn lại. Historicalunique54contexts,khônglặpnhữngcaseđãđạt. Source
current3gates vẫnforwardRootcontract11records,khôngdùnginverse.
Workflowchỉthêmmộtlệnh5MFFsuitesđãchạy,khôngtrigger/permission/deploy.
Pythoncurrent15cađãđo10PASS5FAIL:bốnfailuređãcótừBASEvềPortal/CSS
giữnguyên, một legacyhandoffassertion cònđòichữcũ“khôngtựdùngnguồncũ”.
MởQA-onlyamendment hữuhạn:PythonMFFhistoricalintegrationhelperđọc
reviewed9fragmentauthority,pressuretestsriêngvàchỉaction-input trong
đúngtest_handoff_freshly_rechecks_signed_detail_then_only_navigates_and_rehydrates.
Sourceguardkhácvẫnphysical,oldrequiredlist/golden/errorsgiữ;
currentactionsemantics đãcóphysicaldispatcher8feedbackchecks và
forward11/source151gate;khôngsửaappđểgiữcâukỹthuậtcũ.

Pythonhistoryamendment đãchạy26newpressurecases+đúngmộttesthandoff
failed-only=27PASS0FAIL/exit0;giữ10priorPASS,khônglặpba suite.
Bốnstaticfailurecũđược đối chiếu riêng trên exactBASE6f04b844 trước
publication;khôngđổiapp/golden đểchefailure. Workflowchỉbổsung
Pythonpressurefile vào commandhistorical đãcó,khôngđổi trigger,
permissions hoặc deploy.

Localeblock hiện154file=149predecessor+5MFF;giữbảyfile đãchạyđủ,
chỉchạy147filechưathựcthi,concurrency8/bound900s. Receipt
media-fixed-feedback-regression-remaining147-nov21.xml:
4600receiptcases/PASS0FAIL0SKIP/exit0. RawJUnit
d63efeed712bfede476bd34e199e527b48095c93b17f188ec99ee9ebdcae5913.
Đây là receiptcount,khôngcộngthẳngvới222/54đểclaimuniquecases;
Tester reconcile owner+case một lần,giữmọifalse receipt.
Ứngdụnggiữnguyên11replayrecords,workerfail0/takeoverfalse.

ExactBASE6f04b844 publicsource14file/fourIDs đãđo:pytestexit1/
4assertionFAIL/0error/skip;currentID/message/locationkhớpđủbốn.
Extraoldhandoffcomparisonkhônggọilàbaseline:đãsửaQA-onlyvà27PASS.
NativebindingRAW78ab8ba679a37d0107bbc57f76aea43debf6067e9826d65859ac34e952a8ee41:
run01localhostPermissionError/0case/0PNG/owned0/overallfalsegiữ;
run02samecode/binding,quyềnkếtnốiriêng,exit0/133.487s.
6view/12roots/36newtoasts/36newPNGfull-decode,0localHTTPattempt,
120metadataGET/peak50per60s,source151/core/schema/auth3login-noother/
egress0/owned0đạt. Chỉba validationmessagesnative,khôngclaimeight
write-native/output/globalAX/motion/signedproductionUI.
Spec/checklistcậpnhật sau run làreporting;frozenruninputs vẫn giữ
trongbindingreceipt,app151khôngđổi saunative.

## Thứ tự và cổng chuyển

READ→contract/RED/tracker→ba independent output-onlyproposals
(2/8/1records/fullMAP)→Rootreviewgộp/serialreplay→targetedGREEN/
source151/protected/historical/regression→finiteNative/Tester/
prepush→onePR/exactCI/artifacts/merge/exclusivedeploy/VPS/receipts.

ToàngoalACTIVE/incomplete;reviewpackcopy/locale/AX/auth/device/
Safari/signedUI/genericfocus tiếp checklist;motionM-FINAL01..06cuối.
PROVIDER_CALLS=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_MUTATIONS=0.
