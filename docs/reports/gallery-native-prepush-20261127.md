# GSC — cổng bàn giao trước push

Đang đọc và áp dụng skill owner-governed-codex cho task này.

Product=standalone WebApp;repo=`manhtoangreensky-wq/toan-aas-standalone`;
BASE/HEAD=`29e0c154dfd247ac4b0a68cd6336ec83fb3af8ef`;
branch=`codex/gallery-static-catalogue-20261127`;working diff chưa commit.
Issue689 là tracker chung;không tạo Issue/PR/Project trống.

Checkpointrelease:sourcef0813d9517a93bce1380fd14240c8d7d339c8403,
provenancec2824cf107411e1a1ece4153851a04743fc2bc16 đãpush/cùngPR819.
CI46006189663FAILPythonhistoricalcollection;QA-onlyrecovery thêm
convergence187pressurePASS,18consumer255ca253PASS/2BASE-equivalent,
warningtarget1GREEN. HaiBASEfail cùngtestfunction/line222ImageStudio và
line25Audiohandoff đòi câu kỹthuật đãbỏ. Không đổiapp/expectedpins.
Recoverydelta chỉQA/docs vàcùngCIline;sourcecommit/provenance mới trước
pushnextHEAD.41sourcefiles+2metadata=43,app7giữnguyên.

## Ba phần bàn giao

1. Current operations đã cập nhật:
   `TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md`. Phân biệt PR818 đã giao
   với ứng viên GSC local;không lấy kết quả local thay production.
2. Initial/current comparison:
   `TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md`,đối chiếu chức năng gốc
   từ `docs/migration/FREE_PROMPT_GALLERY_CONTRACT.md`.
   Canonical140mẫu giữ;native text/newnote/clientcache thay đúng phạm vi.
3. Phiên Tester local:
   `KIEM-THU/PHIEN-GALLERY-NATIVE-20261127.md`;
   nguồn case `KIEM-THU/DANH-SACH-CASE.md`;
   kết quả `reports/tester/GALLERY-NATIVE-20261127.md`.
   ID=GALLERY-NATIVE-20261127;không bịa GitHubProject.

Đã đọc GitHub27/11:repo công khai,defaultmain vàmainSHA đều khớpBASE;
Issue689OPEN,nhãnđang-test/case-test/codex,không có ProjectItem.
Có22nhãn,trong đó đủ12nhãn Tester;nhánh này chưa có PR trùng.
Owner đã duyệt riêng runtimefile27/11;comment7219170926 công bố đúng
file vàreadbackexact16416ký tự. Không bypass rejection hoặc mở Issue mới.

## Phạm vi code và bằng chứng đã khóa

Bảy tệp ứng dụng chỉ theo đề xuất Antigravity4ExtraHigh hoặc dữ liệu đã
duyệt. Root đã đối chiếu byte từng edit,không tự viết bản sửa app thayworker.
117row/351value/420native expansion;16taxonomy keys/48values;feedback
24keys/72values gồm loading. Canonical/public IDs/DTO/body/SQL/auth/CSRF,
ghi chú cũ và các miền Bot/engine/provider/wallet/PayOS giữ.

Local đã đo:14backendprimary,54taxonomy,55currentness đều đạt;
34backendaffected32PASS/2BASE-equivalentmissingtzdata với exactBASEproof;
70finitehistorypressure/135affectedUI/51PythonhistoryPASS.
Browser54nativeviews,0app error/overflow/egress;input16,target44.
Backend/leafreviewC0/I0/M0;clientfindingcachedreuse được tái hiện và khép
đúng delta bằngworker+55GREEN. Không lặp whole-source review.

## Cổng local đã đạt và release còn mở

- Consumer closure121tệp đã khép:3121PASS giữ nguyên;40observedFAIL
 được chạy lại đúng40testname ở28file→40PASS/0FAIL/0SKIP/0ERROR,exit0.
 Runtime/backendfiniteinverse169pressurePASS;oldpins/assertionsgiữ.
- Transport historical Python reader đã khép:75pressurePASS;
 static/mount/stale8ca7PASS/1BASEFAIL. Baseline line115 đã tái hiện
 cùng assertion với immutableBASE source trong RAM,không đổi kỳ vọng.
- MountedE2E actualapp3locale390px đã đạt:exit0,3flowPASS;
 display/clipboard/privateMemorynote exact,mỗi account0→1note;
 0unexpected/pageerror/consoleerror,serverexit0. Local không production.
- CI wiring được kiểm YAML/byteguardexit0,chỉ hai runlines mới.
- Exact source commit và Web-only provenance chưa tạo.
- Runtimecontract7219170926 đã công bố sauOwnerduyệt đúngfile,readbackexact;
 trimmedLFbodySHA256def57cde68a6f2ef16cd4518626ded1745ba9567fb10438eb4de991bf1a7c43d.
- Exact-headCI,PR/merge/Webdeploy/runtime/assets/cache/receipt chưa chạy.
 Signed-production vẫn mở.

```text
CODE_REVIEW=backend C0/I0/M0; client cached finding closed by exact worker delta and behavioral evidence
OPERATIONS_DOCS_UPDATED=TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md
INITIAL_FEATURE_DOC=docs/migration/FREE_PROMPT_GALLERY_CONTRACT.md
INITIAL_FEATURE_COMPARISON=TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md
TESTER_PROJECT_ID=GALLERY-NATIVE-20261127 (local QA session, not GitHub Project)
TESTER_PROJECT_STATUS=READY
GITHUB_TRACKER=Issue689 OPEN, existing labels; no ProjectItem
PUSH_GATE=READY_AFTER_REQUIRED_WEB_PROVENANCE_REFRESH_AND_VERIFY
COMMIT=SOURCE_AND_FIRST_PROVENANCE_DONE; RECOVERY_PENDING
PUSH=FIRST_HEAD_c2824cf1_DONE; RECOVERY_PENDING
MERGE=NO
DEPLOY=NO
LIVE_PASS=NOT_TESTED
PROVIDER_CALLS=0 product
WALLET_MUTATIONS=0
```
