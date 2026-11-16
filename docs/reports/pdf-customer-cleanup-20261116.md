# PDF tập trung vào thao tác —16/11/2026

Đang đọc và áp dụng skill owner-governed-codex cho task này.

TASK=PDF-CUSTOMER-CLEANUP, local presentation gates/source review passed;
release pending, whole goal incomplete.
BASE_SHA=2b126b40766404e4b5c0520a121d60c02760d168
BRANCH=codex/pdf-customer-cleanup-20261116
TRACKER=Issue689; initialcontract6916379103; useful-limit amendment6916718848.

## Thay đổi đúng phạm vi

Antigravity Gemini3.8FlashHigh trả READY8 + coordinator useful-limit
AMEND2 + REFERENCE11, tổng21literalchanges/3appfiles. Không có genuine
worker fault, không root-authored app repair. Reference có cùng trailingLF
boundary+1 ở cả11OLD/NEW; core exact, chỉ chuẩn hóa boundary.

Ba ready PDFpages bỏ intro/aside mô tả triển khai nội bộ, giữ nguyên form,
quyền/view/run/refresh, validation/nguồn/ngưỡng chạy, history/download/notes.
Link kho tệp hiện hữu chuyển vào footer, một cột form không để cột trống.
Giữ useful limits: Split20MB/30trang; Merge2–8PDF/mỗi20MB/tổng40MB30trang;
Compress20MB/30trang, cảVI/EN/ZH vàVI fallback.

Reference picker dùng nhãn tìm tệp, trạng thái tải/lỗi và range ngắn theo
locale; header gap6px, status/caption14px/line1.5, paginationbutton min44px.
Chỉ bỏ empty caption, giữ Previous/Next/offsets ở emptylaterpage, query,
selection và actions/route/disabled. Customer filenames/content/notes literal.
19newkeys57values +6existingrows18values; frozen order/keyset/placeholders giữ.

Candidate LF SHA256:

- portal.js `956937a837b71ba3bde13242365168071d0fccc4c5a694cd90df69633244c932`
- portal-i18n.js `dc5e3c54f1a240c9357e2dc8a3c532002b66f0783abbea4858e38c1b653cc4fd`
- portal-theme.css `a0691fb0dca191ce51b1cb59f703af8ad94a1faf6aba5d67dd6211caeba62b81`

## Bằng chứng

- BASE R1 dừng vì coordinator exposure anchor trùng quoted helper; không
  productRED/workerfault. Chỉ sửa QA anchor. R2:20tests,3PASS17expectedRED,
  2124.4531ms, không import/syntax/harness error.
- Một nhóm27files556NodePASS/0FAIL/0SKIP46920.245ms, portal/i18n syntax0.
  Không chạy lặp nhóm đã đạt.
- Actual full renderer3PDFpages×3locale, độc lập view/run/refresh strict
  true/false/string/undefined,0/1/2sources, selected fields/history/download,
  errors/notes/customerHTML/immutable records; guarded toànHTML bằngBASE.
  Ba picker kinds/readstates/query/offset0/50/malformedpagination; Previous
  hữu ích giữ ở trang sau rỗng. SameVM/fallback/hostile/missingunknownpartial
  rejection; escaped một lần, không lọc từ trên dữ liệu khách.
- Exact21serialforward/function-scoped inverse/wholeoutside,22protectedLF/
  allappPython/CIonecommand. Old hashes/assertions giữ qua finite adapters.
- Legacy Python `test_document_operation_portal_contracts.py`:BASE29PASS1.09s,
  branch29PASS1.18s. Legacy Node `documents-product-controls.test.mjs`:
  BASE3PASS1FAIL828.6769ms, branch3PASS1SAMEFAIL734.5406ms. Cùng
  “Documents forms preserve source order, ranges, and guarded choices” do
  pre-existing `/lossless/` source-label assertion. Không xóa/nới assertion,
  không gọi toàn repository xanh; new regressions trong comparator này0.
- Native R1 completed0case vì coordinator giả định control đã≥16px.
  Prior PDF-USABILITY native thực tế đo15px. Giữ R1evidence, amendmentR2
  chỉ preserve floor15px và record mọi control<16; không nhận iOS/font16/AX.
- Native R2 exit0:6owned signed emptyforms VI Split/EN Merge/ZH Compress,
  mỗi375light+1440dark;2mobileformcrops đã xem. One actual Find/ClearGETpair
  dùngq=PDF rồi omitsq; Tab→Find thật; fields/history/notes exact sauClear;
  khôngoverflow/overlap/pageerror/consoleerror. Không gửi operation/create.
-9tables/schema/6plans18scenes/versions/idempotency/source/evidence giữ,
 3fakeQAlogins/0productwrites/reseed/egress/provider/wallet, ownedJobactive0.
- Native summarySHA256
  `142513711f24891a24e0f5c530689a6c5a8f2ef9deb736dfbb7873c309903834`.
  Source review độc lậpC0/I0/M0 đúng3hashes, không chạy lại test/native.
  Scope script sửa riêng importURL Windows của coordinator trước exit0;
  không phải app failure hay workerfault.

## Giới hạn và việc còn mở

Không nhận toàn PDF sạchlocale: Merge fieldlabels/help còn VI/technical,
default page notes vàcác công cụ/headings khác còn cần phiếu riêng. Giữ
customer/customnotes không phải chấp thuận mọi default internalcopy.
Guarded/failure/laterpagination/filledoutputs cóactualrendererVMproof,
không phải native đã quan sát hay tệp đầu ra thật.

PDF-INPUT-FONT16-20261116 còn mở, contractIssue6917285933: Antigravity
output-only bằngmodel mới nhất trong CLI đã kiểm trên16/11,khôngloginmới.
Đơn vị CSS mobilefont riêng chưa áp vào ứng viên này; desktopbaseline15px.
Catalogue light/descriptions/fallback, remaininglocale/responsive/AX/auth/
keyboard/device/Safari/signedproductionUI/realoutput/M-FINAL01..06 vẫn mở.
Motion vẫn cuối; không thu hẹp goal thành PDF.

PR749 trước đó đã giao: exactCI43863230530, merge/runtime2b126b4076,
treeaa5bd7ad5e0d5dd42801fc8e401bdd6b63b7b646,
deploy43865201248SUCCESS, services/health/5assets exact;
receiptsIssue6916141029/PR6916377502.

OPERATIONS_DOCS_UPDATED=TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md
INITIAL_FEATURE_COMPARISON=TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md
TESTER_PROJECT_ID=PDF-CUSTOMER-CLEANUP-20261116
TESTER_PROJECT_STATUS=READY
TESTER_SCOPE=KIEM-THU/PHIEN-PDF-CUSTOMER-CLEANUP-20261116.md
Canonical case1448lines155764LFbytes,
SHA256051bc58625af8d3e3ebfc5c1b28666b92068d2e3a9a5ea64db7264b1330be181.
Metadata gate1PASS32deselected0.67s. Một lệnh chọn sai tên -k trước đó chỉ
deselected33tests; không tính thànhPASS, đã chạy lại đúng1case.
Historical remote/P0/labels/Projects observations giữ,khôngrevalidateremote.
PUSH_GATE=READY; provenance/CI/release separate.
FILES_CHANGED=3appfiles/tests/finiteadapters/CIonecommand/docs/Tester.
TESTS=556NodePASS;29PythonPASS;legacyNode3PASS1baselineequivalentFAIL.
BASELINE_FAILURES=17expectednewtestRED plus1legacy/losslessassertion.
BRANCH_FAILURES=0newtests,1unchangedlegacy;NEW_FAILURES=0.
PROTECTED_COMPARATORS=exact21inverse/outside/22LF/allappPython/nativebinding.
PROVIDER_CALLS=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_WRITES=0.
DEPLOY=NO for current unit;LIVE_PASS=NOT_TESTED signedproductionUI/output.
BLOCKERS=Provenance/exactHEADCI/release gates pending;wholegoal remains open.
LESSON_CANDIDATE=NONE.
