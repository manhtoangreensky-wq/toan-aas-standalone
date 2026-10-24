# VO-CANONICAL-FLAG-TRUTH — cổng push

Đang đọc và áp dụng skill owner-governed-codex cho task này.

TASK=VO-CANONICAL-FLAG-TRUTH
BASE_SHA=9d941fbd52e444d3093f781c48f49ea6dcf30350
HEAD_SHA=b397ef488c0a5b089eedca9c7053c3d8d2187c77
HEAD_SEMANTICS=Reviewed clean source/docs/test commit; this prepush report and generated evidence may follow it.
BRANCH=webapp-r218-billing-ui-20261022
TRACKING_ISSUE=https://github.com/manhtoangreensky-wq/toan-aas-standalone/issues/662
PR=https://github.com/manhtoangreensky-wq/toan-aas-standalone/pull/661

## Review và phạm vi thay đổi

Production chỉ đổi bảy predicate trên năm dòng của portal.js. Không helper,
rename/refactor hay sửa nhãn. is_default/tts_ready/preview_ready cần===true cho
nhãn tích cực; hai select builders cũng chỉ nhậnID+tts_ready===true. Giọng ready
thật vẫn được giữ khi default sai kiểu, chỉ bỏ marker. Không sửa API, auth,
capability, i18n, palette, motion, backend hay triển khai management/preview.

FILES_CHANGED=
- static/portal/portal.js
- tests/voice-inventory-presentation.test.mjs
- docs/superpowers/specs/2026-10-23-r218-voice-canonical-flag-truth.md
- reports/audit/R218-VOICE-CANONICAL-FLAG-TRUTH-QA-20261023.json
- reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-R218.md
- .agents/state/WEBAPP-BOT-PARITY-R218.yaml
- TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md
- TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md
- KIEM-THU/DANH-SACH-CASE.md
- reports/migration/p0-05d-tester-workspace.json

OPERATIONS_DOCS_UPDATED=TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md, mục Voice boolean flags
INITIAL_FEATURE_DOC=docs/superpowers/specs/2026-10-18-r218-02a-voice-vault-canonical-contract.md; actual voiceUi.library catalogue
INITIAL_FEATURE_COMPARISON=TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md, bảng Voice canonical flags

## Verify độc lập với worker

TESTS=
- `node --test tests/voice-inventory-presentation.test.mjs`: corrected RED15pass/
  9assertionfail -> GREEN24/24. R1 substring assertionZH đã sửa trước RED đúng;
  không tính syntax/harness lỗi là test bắt được sản phẩm.
- Focused Voice3files48/48; `node --test --test-reporter=tap tests/*.test.mjs`
  full951/951,0failed/0skipped,exit0.
- pytest two Voice source-contract files10/10,1existingdeprecationwarning,exit0.
- Exact49selection entries in webapp-quality workflow: Windows395passed,
  1deselected POSIX0600 baseline,0failed,16warnings,112.86s,exit0. No committed
  skip or test weakening; LinuxCI must run the unchanged test before merging.
- JS syntax, py_compile app.py/copyfast_pages.py, JSON/YAML parse and diff-check
  exit0. Protected path diff is empty for API/auth/bridge/billing/integration/
  i18n/portal.css/theme/motion/app.py.
- Actual signed localhost app with documented browser-only READ fixtures:
  18configs/180profile states, strict labels/options/keyboard/escaping/noaudio;
  errors/overflow/external/UIwrite/unexpectedHTTPerrors0. Browser runnerexit0.

BASELINE_FAILURES=Truthiness falsely conferred flags; existing Windows POSIX0600 platform assertion
BRANCH_FAILURES=0 applicable failures; one Windows baseline assertion deselected onCLIonly
NEW_FAILURES=0 in verified comparators
PROTECTED_COMPARATORS=FullNode951/951; signedauth/wallet contracts in395local passes; no protected-file source diff

## Tester và delivery

TESTER_PROJECT_ID=R218-VOICE-FLAG-20261023
TESTER_PROJECT_STATUS=READY
TESTER_SCOPE=KIEM-THU/DANH-SACH-CASE.md VFLAG-01..04
TESTER_EVIDENCE=reports/audit/R218-VOICE-CANONICAL-FLAG-TRUTH-QA-20261023.json
TESTER_EVIDENCE_DIR=C:/Users/toann/Documents/Codex/qa/r218-voice-flag-truth-20261023
RAW_BROWSER_JSON_SHA256=749b7110af1a84b52f56c6871f35e7cab8b828ec419909fcf28da218ca61eef0
GITHUB_TESTER_SETUP=Issue662 reused; required12labels and2templates verified in the preceding C0 wave; closed412 untouched
GITHUB_PROJECTS=NOT_REVALIDATED_MISSING_READ_PROJECT_SCOPE; no auth refresh/logout
PUSH_GATE=READY_AFTER_FINAL_PROVENANCE_VERIFY
MERGE_GATE=CLOSED_FOR_THIS_UI_SLICE
DEPLOY=NO
LIVE_PASS=NOT_TESTED

QA fixture truth: real account/CSRF/role in temporaryDB, READ response projection
of Telegram-linked and bridge/copyfast flags only to reach the target renderer;
server has no bridge and provider execution remainsfalse. DTO profile fixtures
are not proof of canonicalAPI, Telegram link, preview/audio/output or LIVE.
Initial two browser attempts remainedguarded due missing fixture bootstrap;
not counted as productRED. Final18configs passed. ServerPTY76092 stopped via
newline,exit0; tempDB/assets cleaned and listener43347 absent. All workers terminal.

Refresh/verify provenance on clean finalsource/docsHEAD, commit only the two
generated reports, push currentbranch once and read back exactHEAD/CI. Record
delivery in Issue662; do not manufacture another receipt-only commit/CI loop.
Remaining canonical management/preview/apply/reuse and finalM0 stayopen.

PROVIDER_CALLS_APP=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
PERSISTENT_ENV_MUTATIONS=0
GOAL=ACTIVE
LESSON_CANDIDATE=NONE
