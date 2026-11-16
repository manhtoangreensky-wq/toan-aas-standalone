# Cỡ chữ nhập PDF trên điện thoại — 16/11/2026

Đang đọc và áp dụng skill owner-governed-codex cho task này.

TASK=PDF-INPUT-FONT16-20261116; local gates passed, release pending.
BASE_SHA=efe06a2964c9e32778e673689410b9e93c939cc3
BRANCH=codex/pdf-input-font16-20261116
TRACKER=Issue #689; contract6917285933.

## Thay đổi

Antigravity dùng `gemini-3.8-flash-high`, model Gemini cao nhất thực tế
CLI liệt kê ngày16/11; phiên đăng nhập sẵn có. R1 code0, đúng một thay
thế CSS, không có genuine worker fault hay root-authored app repair.
Chỉ input/select/textarea trong ba form Tách/Gộp/Nén PDF nhận16px khi
chiều rộng≤767px. Màn hình≥768px giữ15px. Toàn bộ outside CSS giữ nguyên;
không đổi label/help/button, màu/layout/motion, route/quyền/validation.
Portal/i18n toàn bộ LF text bằng BASE; không thay app Python/backend/data.

Theme LF SHA256 `63af94c70c6f63626e797634f78baf1a6bf502156ebcc1617a235a4300476e09`.
Proposal SHA256 `319ecf8cc1efd42cf3299c3e014be7ca4771da715f28d2a889e6fa1400f7deb7`.

## Bằng chứng đã đo

- Actual raw CSS BASE:8tests,4PASS/4expectedRED,548.9254ms;
  không import/syntax/harness error. Thiếu đúng media rule.
- Một nhóm28tệp:564NodePASS/0FAIL/0SKIP,43663.3933ms.
  Không chạy lại nhóm đã đạt. Test mới đọc raw CSS trước mọi projection.
- Exactworkerforward/inverse/wholeoutside;finite helper chặn partial/
  unknown/duplicate/misplaced và giữ unknown outside bytes. Hai historical
  adapters chỉ đảo CSS trước cleanup→Compress→Split→Chat, giữ old assertions/
  hashes. Portal/i18n không bị chiếu ngược.
- NativeR1:0observations/TypeError thiếu reference.newRows do coordinator
  nối thiếu input observer cũ. App/fixture không đổi; không workerfault.
  R2 đọc cleanupfixture qua boundSHA trong nativeCopySource, so19strings/
  locale, giữ R1 evidence và toàn bộ timeout/isolation/gates.
- NativeR2exit0:VI Split/EN Merge/ZH Compress, mỗi375light/390dark/
  767light/768dark/1440dark,15cases/70control samples:
  **42mobile16px /28desktop15px**. Không overflow/fieldoverlap/errors.
  Hai crops đã xem;one real Find/ClearGET vàTab→Find,fields/history/notes
  exact sauClear;không gửi thao tác xử lý tệp.
-9tables/schema/6plans18scenes/versions/idempotency/source/evidence giữ,
  3fakeQAlogins/0productwrites/reseed/egress/provider/wallet/ownedJobactive0.
- Native summarySHA256
  `a9a6bff8ce305930dafe934e48c60a9723fb4d0086408383e051d81fab1d64f7`.
- Scope exit0:24protectedLF/allappPython/exactoutside/CIonecommand/native
  source+original evidence bytebindings. Independent source reviewC0/I0/M0
  đúng candidate, không chạy lặp tests/native.

Legacy document comparators không chạy lặp: portal/i18n nguồn đầu vào
giữ nguyên từng LF byte so với PR750. Bằng chứng trước:Python29PASSboth,
Node3PASS1sameBASE/losslessFAILboth. Old assertion giữ;không nhận toànrepo xanh.

## Giới hạn

Không nhận Safari/iOS thiết bị thật/zoom,wholeAX/locale/auth,production signed
UI hay output PDF thật từ kiểm font. Defaultnotes/Mergefields/toolskhác/
catalogue/fullgoal/M-FINAL còn mở,motioncuối. MergefieldsR1code0,
3changes/7keys21values,NOT_APPLIED/NOT_QA,contract6917766121.
PR750 đã giao:CI43874550883bothSUCCESS/treee8985865/whole diff0,
deploy43876776533SUCCESS/runtimeefe06a29/services/health/5assetsexact;
receiptsIssue6917466951/PR6917965895.

OPERATIONS_DOCS_UPDATED=TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md
INITIAL_FEATURE_COMPARISON=TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md
TESTER_PROJECT_ID=PDF-INPUT-FONT16-20261116;TESTER_PROJECT_STATUS=READY
TESTER_SCOPE=KIEM-THU/PHIEN-PDF-INPUT-FONT16-20261116.md
Canonical case1462lines156827LFbytes,
SHA2568fcf4abc75a17c0e8f23fa35883a55310fd4ca96fd8b5d8b3d9df56166b7754d.
Metadata gate1PASS32deselected0.75s. Historical remote/P0/labels/Projects
observations giữ nguyên; không nhận vừa revalidate remote.
PUSH_GATE=READY
FILES_CHANGED=1appCSS/tests/twoCSS-onlyadapters/CIonecommand/docs/Tester.
TESTS=564NodePASS;native15cases/70samples;source reviewC0/I0/M0.
BASELINE_FAILURES=4expectednewtestRED;unchangedlegacyfailure retained.
BRANCH_FAILURES=0affectedtests;NEW_FAILURES=0affectedtests.
PROTECTED_COMPARATORS=24LF/allappPython/outside/source/evidence/native data.
PROVIDER_CALLS=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_WRITES=0.
DEPLOY=NO for this font unit;LIVE_PASS=NOT_TESTED signed production/output.
BLOCKERS=Provenance/exactHEADCI/release gates pending.
LESSON_CANDIDATE=NONE.
