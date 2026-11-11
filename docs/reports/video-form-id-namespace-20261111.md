# Nhãn ô nhập kế hoạch/cảnh — nghiệm thu liên kết đúng biểu mẫu

TASK=VIDEO-FORM-ID-NAMESPACE; LOCAL_ACCEPTANCE=PASS; DELIVERY=PENDING_RECEIPT.
BASE_SHA=b1a48e09f9f3aa5882f2861feaafdfef1d327e2d; Issue689.
Branch=codex/video-form-id-namespace-20261111.

## Root cause và sửa tối thiểu

Plan edit, scene create và3scene edit forms cùng dùng renderFields nhưng bỏ
tham số namespace có sẵn.9nhóm IDlặp, title/tags5lần và7fieldscene4lần;
native scene-title label.control trỏ sang ô khác. Đây là lỗiBASEđã đo, không
phải regression từ PR717dọnUI. Không sửa lén helper hoặc bù bằng focusJS.

Antigravity3.8FlashHigh một phiên output-onlyR1 trả đúng4callreplacements:
plancreate prefixvideo-plan-create; planupdate prefixvideo-plan-<planUUID>;
scenecreate prefixvideo-scene-create-<planUUID>; sceneupdate video-scene-<sceneUUID>.
Existing helper tự sinh id/for/aria-describedby nhất quán từnamespace. Tất cả
tênfield/name/value/options/disabled/required/action/route/confirmation/revision/
session/normalizer/backend/CSS/i18n/motion/schema/DB/ENV/provider/wallet/Bot/
route-engine giữ nguyên.19protectedpaths và mọi byte khác củaportal.js đạt.

## Evidence

Real-renderer RED24failed/3passed,3locales×4states(draft/readonly/approved/archived)
vànewform;5forms/3scenes. Saupatch27passed/0failed,Node syntaxexit0.
24BASE/candidateviews entireHTML ngoài id/for/aria-describedby identical và raw
normalizedrecords exact;digest44666752d83c8184820be6189260c618fa1b0cf9c8ee1f59527883c2f23a99f3.

Workerpayload exact,0handofffailure. Applyadapter ban đầu nhận hunks theo role
không theo sourceorder nên từ chối trước ghi; coordinator sắp thứ tự hunks
theo source để truyền nguyên NEWbytes, không đổi codeworker hay tính lỗithợ.

Native12views chuẩn bị:3locale×320/1440×list/detail có3cảnhđãlưu. Bấm nhãn thật
cho mọi enabledcontrol, kiểm native.control/document.activeElement; no focus()
fallback. Copied ownedDB/evidencehash/sourcebindings,6plan18scene/quickcheck/
Jobcleanup phải đạt;0compose/save/provider/wallet/productiondata/.env/media.
NATIVE=PASS:12/12views,336native label/controlassociations+336actualclickfocus,
0disabledcontrol/0valuechanges,12screenshots,3syntheticlogins,0compose/save.
6plan18scene/contenthash/quickcheckok/sourcebinding/originalevidence giữ,
30ownedJobprocesses->0;0egress/.env/media/provider/wallet/productionaccess.
Một ảnhVI320lastscenefield kiểm trựcquan:focusring rõ,nhãn điều khiển ownfield.
Không lặp54viewlayout hoặc thao tác tạo/lưu đã đạt trướcđó. Rawgeneratedtags
trong ôsửa vẫnhiểnthị, là bướcmetadata-editpresentation kếtiếp,khôngnhậnđãdịch.

## Bàn giao và giới hạn

CIhậu-mergePR71742914178475 firstattempt:VerifySUCCESS nhưng ChromeCDPstartup
failed2attempts trước khi app được mở. Chạy lại đúngfailedjob một lần, giữlog;
không suy applicationregression, không đổi code/ENV/workflow/deploy. Finalfeature
CI42912273015 và runtime/hash/asset proof của717 vẫn là bằng chứng riêng.
Scopedrerun42914178475 đãcompletedSUCCESS, cả2jobsSUCCESS; không source/ENV/
workflow/production change hoặc redeploy. Firststartupfailure history retained.

Đây chỉ là ID/label association trongVideoforms, không nhận wholeappAX/device/
Safari/signedproduction/provideroutput. Rawtag-editing/oldrecords/titlelimits/
otherplanners/currentinput/stale/retry/auth/device/signedLIVE/motion-last cònmở.
Ops/original-feature/case/Tester/filemetadata/provenance phải xong trước push;
finalCI/exactHEADmerge/exactSHAdeploy/runtime/assets riêng trênIssue689.
PROVIDER_CALLS=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_MUTATIONS=0;ENV_MUTATIONS=0;
LIVE_PASS=NOT_TESTED(signedproduction/device/provider);LESSON_CANDIDATE=NONE.
