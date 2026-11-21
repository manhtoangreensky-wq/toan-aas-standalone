# Phản hồi khi tìm và chuyển trang tệp âm thanh

TASK=MEDIA-AUDIO-READ-FEEDBACK-20261121.
PRODUCT=standalone WebApp.
REPO=manhtoangreensky-wq/toan-aas-standalone.
ROOT=C:/Users/toann/.codex/worktrees/locale-release-proof/_webapp-r218-voice.
BASE=c8b14ade33ed62f2fefb34fe0d14aca198e03a8e.
BRANCH=codex/media-audio-read-feedback-20261121.
TRACKER=Issue689; comment riêng đơn vị trước BUILD, không issue/PR giữ chỗ.
STATUS=PHYSICAL_GREEN_NATIVE_REGRESSION_PREPARATION.

## Thứ tự và quyền

PR783 đã đóng đủ CI44800229661/merge/runtimeBASE/deploy44804290178,
18browser/456authhash,6native48PNG,source/core/schema/auth/egress/owned0,
5+5assets/buildlocal-2dc390c6d1108adf5b36 và receiptIssue7047062064/
PR7048974790 đọc lại đúng. Khóa kết quả này, không chạy lại nhóm đã đạt.

Owner: “trong plan và checcklist thì cứ tự động cho phép không cần hỏi
lại tôi”. Công việc thông thường tự tiến hành trong plan; không mở
Bot/engine/provider/ví/PayOS/ENV/credential/data. Giao nhiều phiên CLI
Antigravity hiện có,modelgemini-3.8-flash-high,output-only; Root serial
replay. Hai genuinecodefail cùngfragment mới takeover; QA/spec/
transport không tính workerfailure. Không login/settings mới.

Note: chia spec chi tiết có kết quả mở khóa; ba proposal độc lập không
ghi repo có thể chạy đồng thời, gate toàn đơn vị xử lý theo thứ tự.
WholegoalACTIVE;motionM-FINAL01..06cuối.

## Source witness và khác biệt phải xử lý

hydrateMediaAudioAssets ởintegration17605 dùng audioepoch/session/path,
GETprivateaudioassetlimit50/query/offset và lọc UUID/downloadavailable.
Readyempty vàcurrentfailed đều trả `{audioAssets:[],listing}`; không
readstate riêng. Dùng mediaWorkspaceReadState là sai vì đó là trạng thái
collectionlist/detail, không phải lượt audio. Actionfilter/clear/page
hiện await rồi success bất kể outcome, kèm VI lẫn thuật ngữ kỹ thuật.
Đây là source witness; runtimeRED phải đo trước applicationproposal.

Soi ảnh hưởng: `git grep -n hydrateMediaAudioAssets -- static tests`
cho một định nghĩa và đúng hai callsites runtime cùngintegration.js;
ba referencePythonchỉtest. Không signature/rename hoặc caller ngoài
module. Chỉ thêm property `failed:true` vào return trong catch hiện tại.
Success `{audioAssets,listing}` vàstale`{stale:true}` giữ; merge/epoch/
query/transport/API/filtering không đổi. Hai consumer được sửa cùng
đơn vị để phân biệt failed khỏi empty, không thêm globalstate.

Ba phương án: suyglobalstate/empty là sai; throw từ loader sẽ đổi hợp
đồng lỗi và có thể phát cảnh báo cũ; chọn additivefailedflag tại catch
là tối thiểu và đo được, giữ cách merge failclosed hiện tại.

## Allowlist ứng dụng

1. static/portal/integration.js: chỉ catch return của
   hydrateMediaAudioAssets và hai actionbranches media-audio-filter/
   clear/page. Dùng lại mediaReadFeedbackText hiện có không đổi helper.
2. static/portal/portal-i18n.js: thêm sáu key dưới mediaReadFeedback
   trước verify/freeze, không đổi24giátrị và8key đã giao ởPR783.

Protected: mọi phần còn lại của reader, mediaWorkspaceRequestIsCurrent,
sharedtexthelper, list/detailreaders, counterlifecycle, API/query/offset/
limit50/retry, strictcapabilityexpressions, arbitrarycustomer/servertext,
payload/draft/storage/write/auth/schema/backend/portal.js/CSS/motion/
Bot/routeengine/provider/ví/PayOS/ENV/productiondata.
mediaAudioAssetFilterPayload/searchvalidation và paginatorlabel
`audio Asset Vault` cùng detailtechnicalcopy là đơn vị riêng kế tiếp,
không âm thầm gộp thêm vào thay đổi phản hồi.

## Acceptance

- AC1: rawreadercurrentfailed thêm`failed:true`; existingmergeclear và
  audioAssets/listing giữ; readyempty không cófailed;stalehìnhdạng giữ.
- AC2: filter/clear/page chỉ success khi audioepoch/session/path hiện
  tại, result khôngstale/failed. Captures collectionlist/detailepochs
  trướcawait để không thông báo sau luồng khác đã thay dữ liệu audio.
- AC3: currentfailed cảnh báo, validempty success; stale newerrequest/
  list/detail/route/session/logout/disabled im lặng, không mượn state
  collectionđểphánkếtquảaudio. Không thay callerfields/customervalues.
- AC4: capabilityfilter dùng strictmedia-workspace-view===true,
  capabilitypage strictmedia-audio-page===true giữ biểu thứcbyteexact.
  Chỉ dịchfixederrorwording; không thêm/nới chính sách quyền.
- AC5: sáu key×VIENZH literal sau; thiếu/emptytranslator fallbackVI,
  hostiletranslation chỉtextContent, khôngHTML. Khôngdịchrawservertext.
- AC6: fullphysicalintegration/i18n,realdispatcher/api/reader/fences/
  toast; chỉ test-localexposure,controlledHTTP/browserboundaries.
  Queryoffset/UUID/downloadavailable/returnforms vàfrozenDTO kiểm thực.
- AC7:151appLFpins/149protected,rawbinding cho native; exactfinite
  sourceprojection mới phục vụhistoricalQA, khôngđổioldgolden/fixture/
  assertion/erroridentity. Currentacceptance dựngtiến từGitBASE.
- AC8: nativecôlập signedGET/actioncontrol thật trên detailmedia/
  audiohub,3locale/mobilePC;fault/recovery/emptypage/copyroles/focus/
  overflow,ảnhhashCRCdecode,source/core/schema/auth/egress/owned0.
  Ma trận chốt trước chạy; không productPOST/download/blob/provider/
  ví, khôngfakeDOM/control/response đểnhậnnative.

## Chữ cố định

| Key | VI | EN | ZH |
|---|---|---|---|
| audioFiltered | Đã lọc danh sách tệp âm thanh. | Audio files filtered. | 音频文件已筛选。 |
| audioAll | Đã hiển thị tất cả tệp âm thanh. | All audio files shown. | 已显示全部音频文件。 |
| audioPage | Đã tải danh sách tệp âm thanh. | Audio file list loaded. | 音频文件列表已加载。 |
| audioReadFailed | Chưa tải được danh sách tệp âm thanh. Hãy thử lại. | Could not load the audio file list. Try again. | 未能加载音频文件列表，请重试。 |
| audioFilterUnavailable | Chưa thể tìm tệp âm thanh lúc này. | Audio file search is not available right now. | 暂时无法搜索音频文件。 |
| audioPageUnavailable | Chưa thể chuyển trang tệp âm thanh lúc này. | Audio file pages are not available right now. | 暂时无法切换音频文件页面。 |

## Cổng thực hiện

| Spec | Dependency | Kết quả mở khóa |
|---|---|---|
| MARF-CONTRACT/RED | PR783closed | RuntimeREDtái hiện,scope/impact/copyđóngbăng,tracker |
| MARF-OUTCOME | RED | Mộtcatchreturnproposal failedflag,khôngreaderchange khác |
| MARF-ACTIONS | RED+copycontract | Hai branchproposal truth/guard/currentness/localized |
| MARF-CATALOGUE | RED+copycontract | Sáu key18literal đầyđủ,equal/frozen |
| MARF-VERIFY | Proposalreview/replay | PhysicalGREEN,151pins,historical/protectedregression |
| MARF-NATIVE | VERIFY | Ma trậncontrolthật/ảnh/isolationaccepted |
| MARF-RELEASE | Native/Tester/prepush | MộtPR/exactCI/artifacts/merge/exclusive deploy/VPS/receipt |

Lịch kiểm tra được chốt trước binding: phần VERIFY-source gồm physical147,
historical106 và review độc lập đã đạt. Hồi quy CI-locale rộng và native
được phép đọc song song cùng151nguồn bất biến; không bên nào sửa source,
spec/MAP hoặc tệp QA native sau binding. Đây chỉ là lịch chạy hai cổng
kiểm tra độc lập, không bỏ dependency ứng dụng hoặc nới nghiệm thu.
MARF-RELEASE vẫn khóa đến khi cả hồi quy, native, Tester và prepush đạt.

## Bằng chứng trước native

Tracker7049170333đãđăngđúngIssue689/đọclạiexact. PhysicalBASE147ca
7PASS140assertionRED,khôngsyntax/setup/boundaryfaults. Ba phiênCLI thật
trả4record;actions/catalogueexact,outcomeR1thiếuđúng1LFcuốicó sẵn ở
cảOLD/NEW. RootR1AchỉkhôiphụcBASEboundaryđó sau so từng token; không
thaycode/logic/space,khônggọimodellại,khôngtínhcodefailure/takeover.
Rootserialreplay2appfile;GREEN147PASS0FAIL0skip9,406s.
FixtureRAW`8d54a2e60594277fd952e7323f5518bed6eb2dfc2e2e42faa81100fadb515cd8`
ghim151sources/149protected và4canonicalrecords.

Ma trận native chốt trước chạy:6viewVIENZH×320dark/1440light, mỗiview
hai detailroots→12routeobservations,4PNG/root=48ảnhmới(error/recovered/
empty-filter/page50),72fixedfeedbackchecks/48transportabortqua3retry/
12heldGET. Thao tác bằngform/nút thật,khôngfakeDOM/event/state/response.
Full-documentnav có thểhủyrequestcũ;khôngdùngnativeđểnhậnfencesame-doc.
Sourceguard/countertestsvật lýriêng. GenericbuttonfocusBODYquan sát thật
vàTab/ShiftTabreachability,khôngtest-restorehoặcnhậnAXtoàncục.

NativeDB/metadata giả:original12asset+51audio/account×3=165metadata,
khôngblob/filebytes/engine/provider/output. AUDIO_ASSET_OPERATIONS và
AUDIO_CHANGE_REQUESTSfalse;khôngruntimebinary/ENVthật. Giữreadlimit
app120/60s;observerceiling90attempt/60s,viewstartgap65s. Group540s,
startup60s/action10s/cleanup5s,khôngtựretrytoànnhóm. Source151raw/LF/
spec/MAP/code/core/schema/auth/egress/owned0 vàPNGCRC/IEND/fulldecode
phảiđúng. Chỉnhậnfinalacceptance-summary sau cảisolation vàPNGgate.

NATIVE/PR/DEPLOY=NOT_RUN. Hồi quy/historical còn nghiệm thu riêng.
PROVIDER_CALLS=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_MUTATIONS=0.
