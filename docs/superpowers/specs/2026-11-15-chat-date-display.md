# CHAT-DATE-DISPLAY — 15/11/2026

Đang đọc và áp dụng skill owner-governed-codex cho task này.

GOAL=Ngày giờ hệ thống trên lịch sử yêu cầu, nội dung, lần lưu và hoạt động trò chuyện dễ đọc theo VI/EN/ZH; giữ nguyên ngày giờ lưu và nội dung khách.
BASE_SHA=c048dd7e70656d58f097c67bf7166b3486007bd6
BRANCH=codex/chat-date-display-20261115
TRACKER=Issue689/checklist mẹ
DEPENDENCY=PR741 đã giao:CI43689932109hai nhómPASS,deploy43690886966PASS,runtime/tree/fiveassets exact.

## Phạm vi khóa

Đúng năm thay thế Antigravity trong portal.js: thêm helper riêng
chatWorkspaceDateLabel và dùng tại bốn vị trí ngày hiển thị. Cùng cách
parse/fallback với date IIFE của thẻ root hiện có; dùng localizedDateTime
medium/short, không thay timezone hoặc giá trị lưu. Invalid/empty/bool→dash.
Giữ safeText từng consumer, toàn labels/customer/body/tags/IDs/revision/
order/filter/capability/controls và metadata mới. Không đổi shared formatter.

Worker conversation21c24b3d-8e91-4bd2-a2d5-19050b861dd1;
rawSHA d8884321aa2d0acbd0425868e8ce6a687d5676c49ea1acff4c38b7f64bb0e3eb;
root-readySHA2fdf85de863acc8fa796963007b37c2c0bca1b3865bc257bc366c22a92a7f725.
Public0e97 có cùng portal bytes với deliveredc048. Năm OLD unique1,
proposedportal LF7cb8bfb238a3bc124887279e67045f11fce722b17771ac0c9be364a1a3a74b8f;
0keys/0workerfault/0retry. Không tự viết lại app.

Allowlist ứng dụng:static/portal/portal.js only.
Test mới:tests/chat-date.test.mjs,tests/helpers/chat-date-runtime.mjs,
tests/helpers/chat-date-snapshot.mjs.
Adapter test:tests/helpers/chat-page-meta-snapshot.mjs,tests/chat-page-meta.test.mjs;
chỉ input source qua strict DATE inverse trước META→REQUEST→HISTORY, giữ oldhash.
CI:thêm một lệnh Node gồm date/meta/request tests trong bước locale có sẵn;
không đổi permissions/trigger/timeout/dependency/settings/deploy workflow.
Tài liệu:spec/report/Tester/case/current-original/motherledger/provenance.

## Acceptance và checklist

- [x] PR741 delivery đã được kiểm thực tế, làm BASE mới; không đoán mergeSHA.
- [x] Đọc proposal, actual formatter/bốn consumer và toàn test/native PREP;
  native Browser plugin absent→existing owned localhost Playwright, không production browser.
- [x] Permanent10testRED trênBASE trước app change, full actual bundle.
- [x] NativeBASEVI375detail thấy rawISO ở bốn vùng, metadata vẫn đúng,
  khôngreseed/all8tables/schema/sixplans18scenes/source/evidence/Jobs0.
- [x] Chỉ replay đúng5workerchanges; ngoài delta byte/LF exact.
- [x] OnegroupGREEN625PASS gồm date và các historical/date/source consumers bị ảnh hưởng;
  no blanket date masking/customer filtering/oldhash update.
- [x] NativeGREENR2sixaffected6unique draftdetail×3signedlocales×375light1440dark/sixshots;
  actualGETstoredDTO/order/control/customer literal unchanged.
- [x] Source reviewC0/I0/M0/docs/Tester/case1338lines146470bytesLF,
  changedmetadata1PASS/32deselected;PUSH_GATE=READY.
- [ ] Provenance/exactHEADCI.
- [ ] Merge/testedtree/exclusivedeploy/runtime/fiveassets/receipts.

Expected formatter independently uses Intl medium/short and actual process/browser
timezone. VM covers validDate/string/offset/numeric/invalid/hostile/fallback/
sameVMlocale/freeze/escape/data immutability. Native uses existing closed fake
DB only, no reseeding/product writes; invalid/capability matrix stays VM-only.
Stored raw ISO in customer-authored text stays literal.

No Bot/route-engine/provider/wallet/PayOS/auth/ENV/schema/production-data/motion
changes. PROVIDER_CALLS=0;WALLET_MUTATIONS=0. Raw-date UI change is not engine
or final-output evidence. Six Document units follow; M-FINAL01..06 remains last.

## Preflight test-harness amendment

First permanent invocation stopped before test registration: the reusable
metadata helper contains the root initializer twice, once as source and once
as the downstream adapter's string anchor. The PREP helper incorrectly required
that bare string to occur once. Change only the test runtime adapter to anchor
the actual top-level initializer with adjacent PAGE_META_BASE declaration.
Do not weaken the occurrence assertion or touch app/metadata helper.
Original log retained; corrected baseline uses a new -r2 log. This is a
coordinator harness error, not a date implementation failure.
NativeBASE already observed EXPECTED_DATE_RED in all four regions,
metadata/data/source/evidence/Jobs0 protected; do not repeat it.

## Screenshot-only correction after GREEN

Node625/625PASS and nativeGREEN6data/presentation observations passed.
Root image review found all six fullPage captures photograph the fixed
viewport plus blank document canvas, not the inner scrolled date regions.
This is a screenshot-harness defect, not an app layout/date defect.
Keep original images/run. Change only capture: scroll the real version date
at375 or run date at1440 into view, assert its box fits the viewport, then
capture the viewport. Rerun the six affected native screenshot cases once
under a new label; do not rerun625Node or BASE. All persistence/egress/source
and original four-date assertions stay intact. No extra screenshot per case.
