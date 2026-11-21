# Âm thanh — lời nhắc nhập, lưu và chuyển bước

TASK=MEDIA-FIXED-FEEDBACK-20261121.
BASE=6f04b8449d7354ca44397c199ccdda77107f577e.
BRANCH=codex/media-fixed-feedback-20261121.
STATUS=LOCAL_NATIVE_TESTER_ACCEPTED_RELEASE_PENDING.
TRACKER=Issue689/comment7060930950; đọc lại body đúng trước gửi.

Đang đọc và áp dụng skill owner-governed-codex cho task này.

Owner cho tự tiến hành công việc thường lệ trong plan/checklist,
không hỏi lại. Appcode qua CLI Antigravity hiện có, model
gemini-3.8-flash-high/output-only/full physical MAP; Root review
gộp một lần/replay tuần tự. Chỉ takeover sau hai genuine codefail
cùng fragment; QA/spec/schema faults không tính. Không mới login/
settings/Git/VPS/ENV/auth/customerdata cho worker.

PR785 đã đóng:CI44888152941 haiSUCCESS18m33s/4m19s,artifacts
14701721427/14701092959,18+456head/hash exact. Merge/runtimeBASE,
treef24dfb9a44d8a7ecfcdf66b27257ad4a00f2df90 exact.
Deploy44890203239SUCCESS56s,VPS3active-running/trackedclean/health,
5+5assets/buildlocal-88468f90c8fb203a50ac;Issue7058931880/
PR7060694584 đọc lại đúng. Không rerun/mở lại đơn vị đã giao.

## Hàng đợi và điều kiện mở khóa

| Thứ tự | Spec | Dependency | Kết quả cần đạt | Trạng thái |
|---|---|---|---|---|
| 1 | MFF-READ | PR785closed | source/consumer/safetyclassifier scan, actual fixed strings/actions và comparator | ACCEPTED_SOURCE_DIAGNOSTIC |
| 2 | MFF-CONTRACT/RED | READ | literal OLD/NEW/VIENZH,151pins,physical RED không setupfault | ACCEPTED_207CASES37PASS170ASSERTION_RED |
| 3 | MFF-LOCAL-ERROR | RED | exact local fixed errors đúnglocale tại allowedactions; producer/rules/rawserver/customervalues giữ | LOCAL_GREEN_REVIEW_CLOSED |
| 4 | MFF-ACTION-COPY | RED | tám toast/fallback đúnglocale, giữ API/order/guards/submission/currentness | LOCAL_GREEN_REVIEW_CLOSED |
| 5 | MFF-VERIFY | proposals | serialreplay/GREEN/source/protected/Historical/reviewmộtlượt | ACCEPTED_LOCAL_SOURCE_RUNTIME_HISTORY |
| 6 | MFF-NATIVE | VERIFY | signedDBtạm/controls/feedback/ảnh/isolation,khôngfakeDOM/provider/ví | ACCEPTED_FINITE36_TOASTS36_NEW_PNG |
| 7 | MFF-RELEASE | Native/Tester/prepush | mộtPR/exactCI/artifacts/merge/deploy/VPS/assets/receipt | WAITING |

Note: chia plan chi tiết từngspec có kếtquả để mởspec tiếp theo;
proposal output-only độc lập có thể chạy đồng thời, shared appwrites
luôn Root replay tuần tự. Không appbuild trước physicalRED.

## Thiết kế phạm vi

Thay chữ tại presentation consumer, không đổi các validation producers:
mediaWorkspaceSafetyError/Line/Content/Tags/filter/collection/item,
Music/SFX editorial classifier giữ nguyên bytes/rules/return/throws.
Genericcatch chỉ thêm action-scoped expression sau editorialError,
trước raw error fallback. Mapper chỉ exact known local messages của
15 actions, không regex/substr dịch dữ liệu người dùng. API errors có
payload hoặc status dương phải giữ nguyên message/identity/precedence.
Nonallowlisted actions không gọi mapper, không đọc thêm error getters.

Hai appfiles dự kiến integration.js/portal-i18n.js. Renderer/CSS/motion/
auth/API/backend/Bot/route-engine/provider/wallet/PayOS/data giữ. Bản
chuẩn bị cũ media-detail-fixed-copy-contract-nov21.cjs chưa READY,
chưa JSON/chưa worker/chưa áp dụng; không tái chạy để sửa producer.

## Checklist bằng chứng

- [x] DependencyPR785closed,realBASE/branch/trackedclean,8statepreserved.
- [x] Scan đủ shared producers/classifier/catch/actions/fixedcopy,
  bảngfile:line và sốoccurrences; fullphysicalsource, khônggrepthànhUIproof.
- [x] Contractliteral/copyrows/allowlist/native/AC/RED trước BUILD.
  Rootfixture b1a1293fd200c49ac4348c7e2f9965df6b9d5b0ae83562fff240a1ae013eddbc:
  35errors+8toast/43keys129literal/11records2appfiles,151BASEpins;
  độc lậpinventory35message/támtoast khớp đúng toàn bộ.
- [x] PhysicalRED đúnglỗi; fullbundle/mộtexposure/0replacedfunctions,
  callerinputs frozen; rawserver/customervalues/nonallowlisted giữ.
  Localerrors126cases5PASS121assertionRED;actions78cases30PASS48RED;
  source3cases2PASS1RED. Tổng207unique37PASS170RED/0skip/setupfault.
  Támtoasttypes đủVIENZH×2roots qua actualdispatcherAPI/DTO/hydration/
  navigation/focus asserts trướccopydiff;30truthyservermessagePASS.
- [x] Trackercomment và ba output-only packets/fullactualMAP/publicsourceproof.
  Comment7060930950 readbackexact; anonymous publicBASEintegration/i18n/
  MAPđốichiếuđúng. Ba packet riêngerrors/actions/catalogue chốt2/8/1records,
  fullphysicalMAPRAW/LFđúng, khôngtest/fixture/API/login/ENV/customerdata.
  BaCLIgemini-3.8-flash-high đãstarted;chưanhậnproposal/appPASS.
- [x] Nhiềuphiếu output-only/fullMAP,rootreviewgộp/replayserial.
  Ba result terminalexit0/structuredSUCCESS;exact2/8/1records,
  RAWerrorsdcc07f9d1f62b8ed3d00f1248a5ffd240fd5b7c78ad832dfa2cabe754e871298,
  actionscdd7fa0c344f6125ec80db21ba96af48d9d90bd31b6d14b1c3e5ed7af56ff6d3,
  catalogue56ad317381ac9623fc8e0c6dec42925b5c3f74afbf8799435c527a45a35b4c86.
  Rootpreflight151BASE rồi mechanicalreplay đúng11record/haiappfiles,
  10sharedfunction giữexact,149protectedRAW/LFkhôngđổi.
  Codefailure0/takeoverfalse,khônglogin/settings.
- [x] TargetedGREEN207ca +6existingMusic/SFXcases=213PASS0FAIL0skip,
  integration/i18nsyntaxexit0. Khôngclaimnative/fullregression/release.
  Reviewgộp0Critical/Important sau đónggapQA bằng9ca mới(6realAPI422
  rawknown/customer+3BASE/currentProxygetter). Rootroleexpectation
  false receipt3PASS6FAIL giữ;failed-only6PASS,222uniquePASScontexts,
  khônglặp213/appkhôngđổi/workerfail0.
- [x] FinitehistoricalQAamendment:SOURCE_RED14rows4fail(mộtsetuprow),
  thêmMFFsnapshot/reviewedfixture,compose trướcMDCChistoricalhelper;
  chỉinput/name adaptation predecessor source suite,khôngđổigolden.
  Newleaf17+audio-source24→41PASS;3predecessorfailed-only→3PASS,
  giữ10PASSkhônglặp.Historical54uniquecontexts,fixtureRAW808d89af...
  Currentforward11gatekhônginverse.Workflowsơthêm1lệnh5MFFsuites.
- [x] PythonQA-onlylatestleaf:current15ca10PASS5FAIL,4identifiedBASE+
  1legacyhandoffcopyassertionmới. Helperhữuhạn+pressuretests vàchỉ
  action-input củađúngtesthandoffđãRED;khôngsửaoldrequiredlist/app.
  New26pressure+1failed-only=27PASS0FAIL/exit0,giữ10priorPASS.
  BốnidentifiedstaticfailuređangđốichiếuriêngtrênexactBASE6f04b844,
  chưađượcnhậnbaselinechỉtừreceiptBASE051b.
- [x] GREEN/current151/protected149/producerclassifierexact/
  payload+rulevectors/currentness/auth/API/writeguards giữ.
  Localeblock154file,giữbảyfileđãchạyđủ;147filecònlại đã
  chạy4600receiptcases0FAIL0SKIP/exit0. Khôngsumthẳngreceiptcounts;
  Testerreconcileowner+nameoncemớiđượcclaimuniquepassingcontexts.
  Workflowchỉthêm5MFFNodefiles và26casePythonpressurefile vào
  existingcommands,khôngtrigger/permissions/deploy.
- [x] ExactBASE6f04b844bốnstaticassertionfailure khớpcurrentID/message/
  assertionlocation;14publicsourcefiles,pytestexit1fourFAIL/0errors/
  skips,khôngimportapp/ENV/DB. Extraoldhandoffassertionkhôngbaseline.
- [x] Nativefinite signedDBtạm/realcontrols/noDOMfabrication,
  expectedbeforeafter/audit/ảnh/source/core/schema/auth/egress/owned0.
  Contract36feedback/36newPNG:collectiontitlebaASCIIspaces(validity
  true,length3trướcclick),attach17tags,audioquerysyntheticpassword
  marker;nativefill/select/click+restore,noPOST. RendererreportValidity
  hiệncóđượctôntrọng,khôngx/force/bypass. Binding78ab8ba6...khóa
  actualruninputs. Run01PermissionError/0case/owned0/falsegiữ;
  run02samecode/bindingexit0/133.487s,36newtoasts+36newPNGdecode,
  120GET/peak50per60s/zerolocalHTTPattempt;source151/core/schema/
  auth3login-noother/egress0/owned0. Appkhôngđổi saunative.
- [x] Ops/crosswalk/támcase/Tester/audit/prepush/manifestdry/
  secret/excludeallstate. Tester4804uniquePASS0FAIL0SKIP/all154files,
  0Critical/Important;metadata1PASS32deselected/audit35pins,
  30scoped+2provenance/9stateexcluded/source151/149protected/
  10sharedfunction/diffcheck/zeroactualsecrethits.
- [ ] MộtPR/exactCI/artifacts/merge-tree/exclusivedeploy/VPS/receipts.

Không paidprovider/realjob/productionwrites/ENV hoặc ví/PayOS. Toàn
goalACTIVE/incomplete;6review-packmessages/locale/AX/auth/device/
Safari/signedUI/genericfocus sauđơnvịnày;motionM-FINAL01..06cuối.
