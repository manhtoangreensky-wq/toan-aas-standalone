# PDF-CUSTOMER-CLEANUP — 16/11/2026

Đang đọc và áp dụng skill owner-governed-codex cho task này.

GOAL=Ba công cụ PDF tập trung vào thao tác thật, không intro/aside giải thích
nội bộ; phần tìm tệp có chữ rõ ràng, header không dính, giữ điều hướng cần dùng.
BASE_SHA=2b126b40766404e4b5c0520a121d60c02760d168
BRANCH=codex/pdf-customer-cleanup-20261116
TRACKER=Issue #689; contract trước giao6916379103.
DEPENDENCY=PR749 đã giao: CI43863230530 hai nhóm SUCCESS,
treeaa5bd7ad5e0d5dd42801fc8e401bdd6b63b7b646 exact,
merge/runtime2b126b40766404e4b5c0520a121d60c02760d168,
deploy43865201248 SUCCESS; services/health/năm assets exact;
receipts Issue6916141029/PR6916377502.

## Hai phiếu đã trả kết quả, đã áp đúng patch

| SPEC_ID giữ nguyên | Kết quả chính | Proposal R1 |
|---|---|---|
| PDF-READY-CUSTOMER-UI-20261116 | Ba ready pages gọn, giữ form/history/notes/vault link |8literalchanges/19keys57values |
| OPERATION-REFERENCE-CUSTOMER-UI-20261116 | Plain copy/header spacing, bỏ empty caption nhưng giữ Previous/Next |11literalchanges/0newkeys18editedvalues |

Hai phiên độc lập output-only Gemini3.8FlashHigh, dùng CLI/login có sẵn;
cả hai completion code0, zero worker code faults/retries.
READY root-ready SHA565413b6486ee3b73c651ac0b29412298d53095f3c0a91b6ea901fa82742841c.
REFERENCE root-ready SHAbe2fa1c9615af3b7d77d359c9bec5d882f06d7582fea40ac928353bb5b4d4795.
REFERENCE OLD/NEW đều thêm cùng một LF cuối mỗi đoạn; structural comparison
đã xác nhận toàn core exact và common delta+1 cho cả11edits. Chỉ chuẩn hóa
ranh giới bằng OLD/NEW đã duyệt, không sửa code worker hay gọi lại.

Phụ lục R1A-LIMIT-COPY (Issue6916718848) do coordinator bổ sung, đã được
Antigravity trả đúng/code0: giữ giới hạn Nén PDF20MB/30pages trong description
VI/EN/ZH và VI fallback trước khi bỏ aside. Không phải lỗi/retry worker.
Hai thay thế bổ sung, không thêm key/logic;21literal changes tổng cộng.

## Allowlist / bảo vệ

APP=static/portal/portal.js,static/portal/portal-i18n.js,
static/portal/portal-theme.css. Chỉ21literal edits. Replay READY→AMEND→REFERENCE;
inverse REFERENCE→AMEND→READY. Sáu READY JS edits gắn đúng owner function;
Split/Compress chủ ý có reason NEW giống nhau nên inverse không dùng
global-first-match. Không thay nguyên function hay guarded branch vừa giao.
CSS cùng prepend vào Split footer nhưng giữ nguyên OLD, không overwrite
prefix của nhau hoặc Compress EOF rules.

READY bỏ technical intro và aside, chuyển link kho tệp hiện có vào footer,
giữ form factory/values/validation/controls/action/route/type/novalidate/
canRun/canView/canRefresh/source thresholds/historycards/pagination/notes.
Chỉ reason copy và hai display constants hết consumer bị bỏ. Generic
localized empty card defaults hiện hữu được dùng; không fake data/output.
REFERENCE giữ mọi pagination offset/previous/next/early return/returned
truthiness/query/readState/selection/action/route/disabled. Trang rỗng ở
offset>0 vẫn giữ Previous; chỉ bỏ caption rỗng. Sáu hàng dịch hiện hữu đổi
đúng18values, giữ keyset/order/placeholders. CSS chỉ component picker:
header grid gap6px; status/caption14px line1.5; paginationbutton min44px/font14.
READY CSS chỉ scoped single-column grid modifier ba trang.

PROTECTED=All appPython/backend/auth/CSRF/ENV/DB/schema/productiondata/
integration/portal.css/motion/themeJS/serviceworker/Bot/engine/provider/
wallet/PayOS. Customer filenames/content/notes phải literal, không word filter.

TESTNEW=tests/pdf-customer-cleanup.test.mjs,
tests/helpers/pdf-customer-cleanup-runtime.mjs,
tests/helpers/pdf-customer-cleanup-snapshot.mjs,
tests/fixtures/pdf-customer-cleanup-reviewed.json.
Historical adapters tối thiểu: PDF-USABILITY source loaders và snapshot
đảo exact customer cleanup trước inverse cũ; CSS đảo exact hai prefix trước
Compress EOF→Split→Chat. Giữ old hashes/whole outside/assertions.
Sáu edited existing catalog rows phải được phục hồi đúng value/order trước
old catalog hashes; không dùng broad prefix masking. CI chỉ thêm một command.
Docs/Tester/cases/checklist/metadata/provenance theo cùng pipeline.

Static legacy comparators: `tests/documents-product-controls.test.mjs` chỉ
thêm exact cleanup inverse cho input trước assertion cũ;
`tests/test_document_operation_portal_contracts.py` dùng cùng reviewed
21-edit fixture qua test-only finite inverse, không bỏ các kiểm tra an toàn.
Helper dùng riêng cho test là `tests/helpers/pdf_customer_cleanup_static.py`;
không được import vào app/runtime. Assertion cũ giữ nguyên.
Baseline đã đo trước app edits: Python29PASS1.09s; Node3PASS/1FAIL828.6769ms,
failID “Documents forms preserve source order, ranges, and guarded choices”
do pre-existing `/lossless/` source-label expectation của đợt PDF UI cũ.
Không tính lỗi này là worker fault hoặc new regression; không sửa app/ẩn
assertion để làm baseline xanh. Branch phải giữ cùng ID hoặc có amendment riêng.

## Checklist / acceptance

- [x] PR749 đã giao trước BASE, tracked clean và Owner state preserved.
- [x] Hai output completion0/exact19edits sau LF-boundary-only review,
  candidate JS parse-only, chưa áp app/QA.
- [x] Fixture bound BASE/21edits gồm phụ lục useful limits;3appfiles/
 19newkeys57values/6editedrows18values. Đã replay đúng21edits.
- [x] BASE actual-renderer RED đúng readycopy/reference UI/CSS, không harness lỗi.
- [x] BASE renderer R1 preflight dừng vì neo root trùng với quoted helper;
  chỉ QA exposure anchor sửa thành newline+export. R2 chạy20tests:
 3PASS/17expectedRED2124.4531ms, không import/syntax/harness lỗi.
  Log R1 giữ riêng, không tính Antigravity fault hoặc product RED.
- [x] Exact serial forward/function-scoped reverse/whole outside giữ.
- [x] Actual ba PDFpages×ba locales: strict independent view/run/refresh,
  empty/filled/query/reference/errors/notes/customerHTML; forms/actions/controls/
  validation/historycards giữ, guarded fullHTML bằng BASE, không cột trống.
- [x] Actual ba picker kinds×ba locales×offset0/50/has_more/malformed/readStates:
  query/selection/disabled/actions/attrs exact; empty later page Previous giữ;
  first-empty no nav vẫn rỗng, no redundant caption.
- [x] Plain readycopy và reference editedrows/fallback/sameVM/freeze/keyset/
  placeholders/oneescape/hostile/missingunknownpartial rejection; raw data giữ.
- [x] Một nhóm GREEN/regression27files556PASS/0FAIL/0SKIP46920.245ms;
  không chạy lặp phần đã đạt. LegacyPython29PASS; legacyNode3PASS/1sameBASEFAIL.
- [x] Native R2 actual signed375light+1440dark, VI Split/EN Merge/ZH Compress:
 6cases/2viewedcrops/1realFindClearGETpair, Tab→Find, nooverflow/overlap.
  Previous emptylaterpage và44px pagination VM-only trừ offset thực quan sát;
  không fake API/quyền/output, không nhận wholelocale/AX hay native16px.
- [x] Data/schema/plans/scenes/source/evidence unchanged, productwrites0/
  reseed0/egress0/provider0/wallet0/Jobs0.
- [x] Independent source review C0/I0/M0,3frozenhashes;scope22LF/allappPython/
  exact21inverse/outside/CI+1/nativebytebinding đạt. Docs hiện tại/đối chiếu
  gốc/Tester PDF-CUSTOMER-CLEANUP-20261116 READY.
- [ ] Provenance → exactHEADCIboth → exactmergedtree → exclusivedeploy →
  runtime/services/health/assets/receipts.

TESTS=`node --test tests/pdf-customer-cleanup.test.mjs` plus affected chain in
one grouped final run. Native uses owned localhost, no production browser.
STOP=OLD/hash nonunique/mismatch, unexpected outside/protected changes or
verification fail. Không tự sửa app trước hai genuine worker faults của
cùng fragment. Coordinator/harness/spec lỗi không tính worker fault.
Các PDF tools khác/catalogue/full locale/responsive/AX/keyboard/auth/device/
Safari/signedproductionUI/real finaloutput/M-FINAL01..06 vẫn mở, motion cuối.

## Native QA amendment R2 — lỗi giả định về cỡ chữ

R1 hoàn thành0case, dừng đúng assertion assumed input/select/textarea>=16px.
Native của đợt PDF-USABILITY đã đo Split source/range375light+1440dark và
Compress source375light là15px.21edits hiện tại không đổi cỡ chữ các control
này. Không tính đây là lỗi Antigravity hoặc mới hồi quy; giữ nguyên log R1.
R2 chỉ chạy6case chưa xong, cùng fixture/candidate hashes, ghi mọi control
dưới16px và kiểm floor15px không giảm so với baseline đã đo. Tách
PDF-INPUT-FONT16-20261116 thành việc còn mở, giao Antigravity riêng; không
nhận mobile16px/iOS/wholeAX đạt. Các gate khác, timeout, dữ liệu, GET thật,
source/evidence và owned cleanup không đổi.

R2 đã chạy exit0: nativePassed/infrastructureAcceptedtrue,6cases,2crops đã
xem,1realFind/ClearGETpair,3fakeQAlogins,0console/pageerrors/egress/
productwrites/reseed/provider/wallet,9tables/6plans18scenes/source/evidence
giữ vàownedJobactive0. SummarySHA256
142513711f24891a24e0f5c530689a6c5a8f2ef9deb736dfbb7873c309903834.
Mọi control được quan sát dưới16px vẫn15px; finding còn mở riêng,
contract Antigravity Issue6917285933, không áp patch font vào đơn vị này.
