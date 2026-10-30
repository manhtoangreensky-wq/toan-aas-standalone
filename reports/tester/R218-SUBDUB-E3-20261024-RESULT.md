Đang đọc và áp dụng skill owner-governed-codex cho task này.

# Tester độc lập — R218-SDE3-TESTER-20261024

## Kết luận và ranh giới

VERDICT=READY_FOR_PARENT_LOCAL_ACCEPTANCE

Chấp nhận **phạm vi E3 local đã đo**: LABEL/CONTRAST/RANGE/GROUP/EDIT/READINESS
và ma trận cuối. Không chấp nhận toàn bộ 21 yêu cầu như đã hoàn thành; không
phải READY_TO_MERGE, deployed, LIVE hay whole-goal COMPLETE. SD-15 còn thiếu
nút Bật/tắt riêng, đã được giữ là UI gap OPEN, không đẩy sang T0 engine.

Tester không phải Builder. Tôi đọc script/source, parse toàn bộ bốn JSON gốc,
tự tính lại tổ hợp/hash/counter, xem bốn ảnh và chạy mới hai bộ test chỉ định.
Runtime trong báo cáo là **independent inspection of existing root artifacts**,
không phải một browser run mới của Tester. Không khởi động/tắt server, mở
browser/window, gọi mạng, tạo issue/project/chat, cài gói hoặc sửa source/tests.

```text
TASK=R218-SDE3-TESTER-20261024; READY_FOR_PARENT_LOCAL_ACCEPTANCE
ROOT=C:/Users/toann/Documents/Codex/_webapp-r218-voice
BRANCH=webapp-r218-billing-ui-20261022
BASE_SHA=79cd75d3d8ee50685bbecd4056f7d84a79f8e68a
READINESS_BASE_SHA=7e35f0ab78a32b2d4d7bffc7536a4dd381c21151
HEAD_SHA=26a966e25778229a0b76cfb045fa384d5d34b4eb
PR=661; ISSUE=664
FILES_CHANGED=_giao-viec/TESTER-45-SDE3-RESULT.md only by this Tester
TESTS=fresh Node 74 passed/0 failed; fresh portable pytest 32 passed/1 deselected/1 existing warning; both exit0
BASELINE_FAILURES=NOT_RUN by Tester; no checkout/source mutation authorized
BRANCH_FAILURES=0 applicable failures in the two fresh targeted commands
NEW_FAILURES=UNKNOWN as a baseline-vs-branch runtime comparison; not inferred from unchanged old test blobs
PROTECTED_COMPARATORS=parent production diff2; readiness exact8/reverseLF/17helpers/14files/674oldtests; parent672oldtests; Chat33functions+CSS-tail; worktree source/tests clean vs HEAD
PROVIDER_CALLS=0 by Tester; inspected runtime artifacts record external0/UIwrites0
WALLET_MUTATIONS=0
ENV_MUTATIONS=0 persistent; authorized process-local PYTHONPATH only for pytest command
DEPLOY=NO
RUNTIME_SHA=NOT_APPLICABLE to production; local served assets bound by LF hashes below
LIVE_PASS=NOT_TESTED
BLOCKERS=NONE for this scoped local acceptance; final delivery/main compatibility/provenance/exact-HEAD CI remain parent gates
LESSON_CANDIDATE=NONE; AUTO_PROMOTION=OFF
```

FSM: READ (active AGENTS + both owner kernels + locked-focus + single-agent +
system-design + verification contract) → CONTRACT (read-only evidence/tests,
report-only write) → BUILD (no app build/change) → REVIEW → VERIFY → REPORT.
LEARN không tạo file/candidate do không có quyền ghi ngoài report.

Các file docs/metadata đã dirty trước task thuộc parent; tôi không ghi đè hoặc
nhận là thay đổi của Tester. Không commit/push/merge/deploy trong task này.

## Findings C/I/M

- **Critical 0 / Important 0 mới trong phạm vi sáu remediation E3 đã khóa.**
- **Minor 1 — SD15-F01, đã giải quyết cách ghi tài liệu; implementation OPEN.**
  Spec gốc tại `docs/superpowers/specs/2026-10-18-r218-subdub-bot-parity-uiux.md:34`
  yêu cầu “Bật/tắt” và slider/number. Final crosswalk ban đầu chỉ ghi mức 0–100
  và giữ 0, thiếu qualifier rằng chưa có nút Bật/tắt riêng. Source chỉ chứng minh
  local 0%-mute, không chứng minh dedicated toggle. Đã báo parent; đọc lại
  `reports/audit/R218-SUBDUB-FINAL-UI-CROSSWALK-20261024.md:32` và `:42`, cùng
  `reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-R218.md:576`, xác nhận
  qualifier được khôi phục và `SD-D4-ORIGINAL-AUDIO-TOGGLE` OPEN. Không sửa
  production source, không gọi đây là SD-15 hoàn tất, không chuyển UI gap này
  thành T0 engine. Đây không phải lỗi mới do readiness gây ra.

Không retrodiagnose lịch sử: original C3 AX mismatch cause UNKNOWN; original
LC run state UNKNOWN. Fix hiện tại chỉ đóng current native early-authoring
defect có RED/GREEN riêng. Đã parse lại READ72 hash `47d1070c…ff3685`:
36 early mismatch; 27 đổi control; 9 không đổi đều DUBBING_ONLY nhưng vẫn
mismatch tức thời; 36 stable sạch. Không gọi toàn bộ 36 là mất dữ liệu.

Một phép so ad-hoc ban đầu exit1 do **lỗi checker của Tester**: so toàn bộ JS
suffix từ first renderChat tới EOF, vô tình bao cả SubDub cố ý đổi. Không phải
product failure. Đã thay bằng bounded comparison 33 Chat functions, literal
CSS tail và Git blob trees, tất cả exit0. Không thay app/test để làm xanh.

## Tám case — nguồn duy nhất KIEM-THU/DANH-SACH-CASE.md

| Case | Kết quả | Bằng chứng độc lập / giới hạn |
|---|---|---|
| SDE3-01 | PASS_LOCAL_ONLY | Parent168 unique đúng Cartesian 4 mode × VI/EN/ZH × light/dark × 7 viewport; complete168; script assert title/URL/oneactive/ARIA, source choice, 21 target/search, format/position/line/display, local mix/mute/keyboard/review/Voice. T0 không bị tick. |
| SDE3-02 | PASS_LOCAL_ONLY | Hai Dub mode: group4, membership2/1/1/3, lane7, Auto callbacks riêng; parent588 choices/168 returns. Fresh grouped-unit kiểm native order/full ARIA/compact names và subtitle-only không lộ voice; browser scripts so full ARIA với review. |
| SDE3-03 | PASS_LOCAL_ONLY | Parent leaf text14448 min5.2237991112, AA0/unknown0; labels0/font0/range168 min200×44. EDIT168 text1218/focus336 min12.3515547/5.86008095, button44×44, geometry/text2x. Không whole-page WCAG/native text-scale claim. |
| SDE3-04 | PASS_LOCAL_ONLY | Native72: actual real auth/me fetch→hold→fulfill cùng response; early36 enabled0, normal-click timeout + Tab blocked36; ready72 coherent, mode loops72, guards/anchors giữ, assets288. Không forced click/fake API/session payload. |
| SDE3-05 | PASS_LOCAL_ONLY | Pending12 unique VI/EN/ZH × light/dark ×390/1440, actual visible AX/status, min11.7724811322/unknown0, readyAbsent12; không có own asset hashes. Binding bằng companion72 + cùng origin/server context, không bịa thêm12 asset checks. |
| SDE3-06 | PASS_LOCAL_ONLY | EDIT168:1218 click/336 keyboard/1050 actual edits; per-Edit snapshots/URL/mode/root/request unchanged; focus visible/uncovered, mode loops168/Voice returns168. Fresh unit kiểm same-HTML child identity/E607 và valid instant-center focus/E608, invalid/disabled fail closed. |
| SDE3-07 | PASS_LOCAL_ONLY | Exact8 readiness records/reverse whole LF;17 whole helpers; đúng14 historical protected files;674 old tests từ readinessBASE và672 old tests từ parentBASE cùng blob. Chat33functions/CSS-tail không đổi; source/tests working tree bằng HEAD. Historical UNKNOWN giữ. |
| SDE3-08 | PASS_LOCAL_ONLY (boundary only) | Docs/readiness/crosswalk phân biệt local/CI/deployed/LIVE; 21 IDs còn đủ; dedicated on/off vẫn UI OPEN và engine/T0 còn nguyên. Exact final CI, main integration, merge/deploy/LIVE NOT_RUN, không được coi PASS từ local result này. |

## Đối chiếu 21 SD: có UI không đồng nghĩa có engine

Đã đọc spec gốc, crosswalk mới và source thật; script đếm đúng SD-01..21 và
21 hàng final tương ứng, không lẫn bảng READ lịch sử. Các entry points:
`portal.js:26254` resolve mode; `:26895` mode update; `:26953` local volume;
`:27051` settings rows; `:27114` focus Edit; `:27221` identity/session fence;
`:27292` markup readiness; `:27300` hub renderer.

| SD | Đối chiếu local/source | Phần vẫn chưa hoàn thành |
|---|---|---|
| 01 | 4 mode/query/ARIA/keyboard, mode loops | 4 engine thực |
| 02 | `portal.js:27429` label/accept/native-disabled source | Upload bytes/metadata/progress/cancel/replace/preview/owner |
| 03 | Source state có/chưa trong stage1; radio/review giữ | Actual file/cue/ASR binding |
| 04 | `:27442` source-language auto/disabled | Detection/provider language capability |
| 05 | Target catalog21/search/ja/custom ISO theo locale | Catalog không là toàn bộ provider support; translation output |
| 06 | Formats/mono-bilingual/line settings và companion links | Cue edit/ownership/original-translated speech/output file |
| 07 | `:27383` bốn semantic groups, 7 radios, full ARIA | Canonical voice capability |
| 08 | Female/male local choice không đòi personal profile ID | Engine/default voice availability |
| 09 | Saved→Voice/saved→return giữ draft | Real picker/preview/default/owner application receipt |
| 10 | Custom→Voice/clone→safe return | Consent/upload/name/quote/preview/save thật |
| 11 | Auto2 callback riêng | Real 2-speaker detection/assignment/output |
| 12 | AutoMulti3–8 callback riêng, không fake count | Server count/map/override |
| 13 | Smart callback riêng, không gộp auto_many | Quality/cost/canonical capability/execution |
| 14 | `:27404` guarded map, không tạo rows người nói ảo | Detect/ambiguous/preview/override/fallback/report |
| 15 | Original slider+number0–100, preserve0/review | **UI dedicated on/off OPEN SD-D4**, thêm actual mix/audio T0 riêng |
| 16 | Dub0–200/zero ack/range-number-review | Actual output loudness/limit/engine |
| 17 | 7 positions/mono-bilingual/line/formats theo mode | Style/cue render/server capability/file |
| 18 | Editable review rows+mode Edit, đúng focus | Duration/count/cost/expiry/real quote; readonly rows không nút giả |
| 19 | `:27617` native-disabled CTA/source guards | Admission/quote/dedup/progress/retry/charges/job |
| 20 | `:27622` initial empty guarded report ẩn | Real refs/stages/download/delivery/failure/recovery |
| 21 | Safe Voice continuation/draft/return mode | Canonical profile/file/subtitle→Video/Projects/Admin reuse |

Đã đọc section readiness đầu `TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md` và
`TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md`: không có production revision
hoặc số production bịa; nhận định mismatch36/changed27 đúng raw; không bỏ
upload/ASR/voice/detection/quote/job/output/reuse T0. Các section cũ giữ lịch sử,
không dùng lịch sử để ghi đè bằng chứng mới.

## Bốn raw artifact — parse đầy đủ và tính lại, không chỉ đọc summary

QA root `C:/Users/toann/Documents/Codex/qa/r218-music-review-FH-20261024`.

| Thư mục chứa result.json | SHA-256 raw đã đo lại | Kết quả tự tính |
|---|---|---|
| SDE3-final-20261024-r1 | 249be2cfe57d9d9464156358cf1e2529ddc674a99ba05f35ea6fa88e7734782a |168unique/complete,588choices,168returns,672 asset comparisons; text14448/large192/min5.223799111200577; range168/min200×44 |
| SDE3-READINESS-native-green-1792839341797 |1851c1f9a14d48901f80aac438281dfaf373550a9ed84cc245bd76907f12de89 |72unique=36early+36stable; earlyEnabled0/normalBlocked36/readyMismatch0/modeLoops72/assets288 |
| SDE3-READINESS-pending-1792839578984 |0323f95687dc3ad38b397aa88798d72674b9f6486ac7f60c6aebbf77570130fa |12unique/visibleAX12/readyAbsent12/min11.77248113218246/unknown0/ownAssets0 |
| SDE3-EDIT-readiness-final-20261024-r1 |4598041a730d5366f841c93cdc9b387b971a53548fbc56ef676c9b68d1a5684e |168unique/1218click/336keyboard/1050edits/168modeLoops/168VoiceReturns/504assets |

Parent counters tự tính đều0: interaction/AA/unlabelled/noteAX/unknown/range
hit/input-font/overflow/report-visible/missingEdit/page-console error/external/
UIwrites. Companion72/pending12/EDIT168 có errors/external/UIwrites0. EDIT
text1218/focus336; min text12.351554732138213, focus5.860080947953878,
unknown0, min buttons44×44; positive/inViewport/uncovered cho mọi recorded click.

672 và504 là **row-level LF comparisons**, không phải số unique HTTP response
hoặc người dùng. Parent có42 page configurations, mỗi page dùng bốn mode;
served hashes được sao vào từng row. Native72 ghi bốn asset mỗi configuration.
Pending12 không chụp asset riêng, không được tính vào các số hash này.

Đã đọc nguyên script `audit-SDE3-final.cjs`, so với `audit-SDE3.cjs`; đọc
`browser-SDE3-READINESS.cjs`, `pending-SDE3-READINESS.cjs`,
`readiness-metrics.cjs`, `browser-SDE3-EDIT.cjs`. Xác nhận final script chờ
signed readiness; selector callback chỉ choice lane, không gom retained inert
Smart fieldset; exact4 asset keyset/hash frozen lúc QA-start; mọi strict counter
gác bằng assert0, D3 reportRects không chỉ được đo mà bị gác; chỉ loại leaf
decorative có aria-hidden khỏi AA. Review source script không phải chạy lại
browser. `git diff --no-index` giữa hai script exit1 là kết quả có diff, không
phải QA assertion failure.

Đã mở thực tế bốn PNG: `vi-light-390-initial.png`,
`vi-dark-1440-initial.png`, `vi-light-390-DUBBING_ONLY-config.png`,
`vi-dark-390-DUBBING_ONLY-review.png`. Chữ/group/7 choices/review/guard phù
hợp nội dung đo; đây là viewport/element crops có sticky shell, không đủ để
chứng minh full-page WCAG/CLS/INP hay mọi màn hình không bị che.

## Source provenance và protected comparators

LF SHA-256 hiện tại khớp frozen parent hashes và mọi served hash đã ghi:

| Asset | SHA-256 UTF-8 LF |
|---|---|
| portal.js | d2eb7048f62619ed22a01b9cae70cd6672d55cb22948cf818c654edc2e8c522e |
| portal.css | 514dd76e2c6714fa49a6b19f9dfd672a5a7121fbbd8469b2a354893fd521e3b3 |
| portal-theme.css | 59cfaa8dc6486c869377a431241dffdbbc2a0a52d16ded7448f7b61d4a9ee711 |
| integration.js | 5ac46bc3fccdc893f73fa07efa3e0d56677606f2bf6d2617f5a540c5f8339912 |

`git diff parentBASE..SOURCE` production chỉ `static/portal/portal.js` và
`static/portal/portal-theme.css`; diff đầy đủ đã đọc. Không đổi auth/backend/
engine/wallet/API schema. CSS mới scoped SubDub; event handler mới scoped
`.portal-subdub-hub [data-subdub-review-edit]`; focus không submit/navigation.

Readiness packet8 records SHA256
`46b97b444b32b5d33decbe00ab1fd469a24ad1bc0205ef4756d969a3d8596c53`:
đã áp ảo vào7e35 trong memory, bằng toàn bộ current JS LF, reverse về đúng
baseline. Không execute packet hay ghi source. Whole helper17 vẫn bằng7e35:
resolveSubDubJourneyMode, resolveSubDubLocale, renderSubDubLanguageOptions,
updateSubDubModeSelection, handleSubDubModeKeydown, updateSubDubLocalVolume,
updateSubDubVoiceLaneSelection, normalizeSubDubDraftValue, subDubDraftSnapshot,
subDubDraftValue, renderSubDubSettingsRows, subDubDraftControlName,
captureSubDubDraft, applySubDubDraftDom, synchronizeSubDubWorkspaceDraftSession,
updateSubDubLanguageSearch, focusSubDubReviewSetting. Identity fence và E607
không thay bởi readiness.

Đúng14 historical files so Git blobs7e35→SOURCE đều bằng nhau:

```text
static/portal/integration.js
static/portal/portal-theme.css
static/portal/portal.css
static/portal/portal-motion.js
static/portal/portal-i18n.js
static/portal/portal-auth.js
copyfast_auth.py
copyfast_pages.py
copyfast_api.py
copyfast_bridge.py
app.py
config.py
billing.py
templates/portal_shell.html
```

674 old test paths từ7e35 và672 từ parentBASE đều giữ blob. Ngoài đúng14
trên, own explicit comparator còn kiểm service-worker và SubDub bridge bằng
blob. Chat33 named functions giữ toàn bộ function text so parentBASE; CSS
literal `/* Final light AI Chat Workspace surface */` tới EOF bằng parentBASE.
Không so toàn bộ JS tail từ Chat vì SubDub nằm sau Chat và được phép đổi.

## Lệnh chạy mới và output terminal

Working directory cho test là ROOT ghi ở đầu báo cáo.

```powershell
node --test --test-reporter=spec tests/subdub*.test.mjs
```

Exit0; `tests 74`, `pass 74`, `fail 0`, cancelled/skipped/todo0,
duration867.1471ms. Gồm readiness6, Edit8, groups6 cùng các SubDub regression.

```powershell
$env:PYTHONPATH='C:/Users/toann/Documents/Codex/_wa35-r74-qa-python-20261012/site-packages'; & 'C:/Users/toann/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m pytest -q tests/test_p0_05d_tester_workspace.py -k 'not test_owner_authorized_write_uses_private_temp_file_and_cleans_it'
```

Exit0; `32 passed, 1 deselected, 1 warning in 0.69s`. Warning hiện tại:
`config.py:27`, Pydantic class-based Config deprecated. POSIX private-temp
write case không chạy trên Windows theo contract, **không báo33pass**.

```powershell
git diff --unified=2 79cd75d3d8ee50685bbecd4056f7d84a79f8e68a 26a966e25778229a0b76cfb045fa384d5d34b4eb -- static/portal/portal.js
git diff --unified=5 79cd75d3d8ee50685bbecd4056f7d84a79f8e68a 26a966e25778229a0b76cfb045fa384d5d34b4eb -- static/portal/portal.js static/portal/portal-theme.css
git diff --check -- static/portal/portal.js static/portal/portal-theme.css tests
git diff --exit-code HEAD -- static tests '*.py' templates .github
git rev-parse HEAD
```

Tất cả exit0; hai lệnh diff đầu có nội dung đúng hai production UI files;
check/worktree comparator không output, HEAD đúng fullSOURCE ở đầu report.

Read-only verification bổ sung bằng Node stdin/`node -e`: `JSON.parse` bốn
raw đầy đủ; SHA256 bytes gốc; assert đủ Cartesian/unique row, every counter,
source hashes/asset keysets; Git `ls-tree -r` blob maps để so protected/old
tests; LF metadata bytes/line/hash; exact8 packet/reverse17helpers và33Chat
functions/CSS-tail. Các bounded check này đều exit0, output
`ALL_ASSERTIONS_PASSED`/`allBlobsUnchanged:true`. Hash raw còn đo độc lập bằng
`Get-FileHash -Algorithm SHA256 -LiteralPath <bốn đường dẫn result.json nêu trên>`.

Root-reported fullNode1301/PythonCSS21/compile6 được đọc trong audit JSON,
**không rerun bởi Tester** và không dùng thay fresh targeted results ở trên.
Full repository pytest/baseline checkout NOT_RUN trong phiên này.

## Tester workspace: metadata portable và case cũ

Đã normalize CRLF→LF rồi đo lại UTF-8 bytes, line count và SHA256 của **6/6**
`local_files` trong `reports/migration/p0-05d-tester-workspace.json`:

| File | LF lines / bytes | LF SHA-256 |
|---|---|---|
| .github/ISSUE_TEMPLATE/01-case-test.yml |113 /3098 |7e327aa36a26763198a6e092cbfc87491fa7fa160bbd861c38d8aaece2824508 |
| .github/ISSUE_TEMPLATE/02-bao-loi.yml |100 /2557 |212f9ce4b6b4459b5a1041ff70ac855fbdae110417e3dddd09d6d898c75841a4 |
| KIEM-THU/DANH-SACH-CASE.md |779 /94262 |be038085cfa882358fa3e16443b230fbb80868d6f76503f7627c5376299f3cb8 |
| KIEM-THU/HUONG-DAN-TESTER.md |298 /26516 |22abd42b7b78599ee4a5bba7cfb587a51b128785b1a639f7150bfd8d0c87eb93 |
| scripts/tester_case_sync.py |212 /8601 |7f621362e137ee6d2db3518da0ca8ad84c8e368c792b25faec8d6450a42f43c6 |
| tests/test_p0_05d_tester_workspace.py |385 /17905 |33edaabf3c31e006f72638e0eb6f38473fb68572b8716b3e10f36d6b4e764b46 |

48 hàng WA-01..48 hiện tại bằng nguyên văn hàng từ SOURCE; không đổi case cũ.
Bảng đầu E3 có chính xác SDE3-01..08 mới, session manifest/guide cùng source
candidate. Remote22 labels/required12/Project thiếu read:project là evidence
parent, Tester không gọi GitHub/auth-refresh để xác nhận lại.

## NOT_RUN / OPEN — không được chuyển thành PASS

- Native Safari/iOS/physical touch/native keyboard, OS text scale, PWA.
- Full-page accessibility, motion-final-wave, animation/performance traces,
  FPS/CLS/INP; CSS text2x simulation không phải OS/native text scale.
- Dedicated original-audio on/off UI: OPEN SD-D4; 0%-mute không đóng toàn SD15.
- Upload/ASR/translation/canonical voices/profile application/consent/preview/
  speaker detection-mapping/quote/admission/dedup/charge/job/output/download/
  delivery-recovery/cross-product reuse: T0 hoặc separate capability contracts.
- Exact final deliveryHEAD CI, main compatibility, merge, deployment runtime
  SHA, VPS service checks, production data/user counts và LIVE output.
- Original C3 AX cause và original LC run state: UNKNOWN, không sửa lại lịch sử.

Parent có thể nhận local E3 evidence này rồi xử lý delivery/provenance gates.
Không dùng report này để tự merge/deploy hoặc tuyên bố toàn goal hoàn tất.
