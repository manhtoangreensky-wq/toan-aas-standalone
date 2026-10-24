# MU07-A — báo cáo trước push

Đang đọc và áp dụng skill owner-governed-codex cho task này.

TASK=MU07-A-RETAINED-OPTIONS
BASE_SHA=520174941470fab34c60c26e62607ba2d4b3568f
HEAD_SHA=Source/docs working tree; final actual SHA is recorded by Git and Issue664 receipt after delivery, not predicted here.
BRANCH=webapp-r218-billing-ui-20261022
PR=https://github.com/manhtoangreensky-wq/toan-aas-standalone/pull/661
TRACKER=https://github.com/manhtoangreensky-wq/toan-aas-standalone/issues/664
CONTRACT_RECEIPT=6372408836;handoff/escalation6372935730;F/Hdependency6372116359.

## 1. Code review và tài liệu vận hành hiện tại

Ba production files: portal.js56insertions/1deletion, i18n2insertions,
themeCSS18insertions. Thêm hai closure globals, helper đồng bộ snapshot,
một mount call và read-only fallback sau estimate. Không đổi signature hoặc
thân helper cũ. Memory bound hai route × tối đa ba prompt thực nhận, strict
signed/CSRF/token lifecycle. Chỉ clone own string fields allowlist; explicit
empty/error/guard/confirm không hồi sinh dữ liệu cũ. Native details đóng,
Copy/Apply handler cũ giữ quote-stale; không restore quote/receipt hoặc giả ID.

Nguyên nhân mất lựa chọn: estimate thay flow.data nên draft suggestions mất.
Không thay integration để ghép lại flow cũ; UI giữ snapshot độc lập có fence.
A04 actual-gradient3.744/3.768 và darkordinal3.896 có evidence riêng trước
amendment. Sol CSS chỉ dùng existing action/muted tokens trên cùng Music
suggestion component; không global rule, palette, important hoặc motion mới.

R1Flash3.8Low57.895231s/1turn source/test gatefail; R2Flash3.8High446.9415278s/
1turn malformedJSON/contextshape. Không apply/repairR2 thành accepted, noR3.
Root thừa nhận fixture context.session/featureFlows cần cụ thể hơn trong spec.
Solxhigh takeover cùngSPEC_ID/newtestRED→exact immutableproductionpatches.
Independent source review C0/I0/M0, composition9records/3productionfiles;
13protectedfunctions/12files/oldtests/Chattail không đổi sau LF normalization.
F/H/sessiondraftsync/Apply/dispatch/quote guards/API/auth/backend/Bot/ví/PayOS/
ENV/provider/motion không sửa.

OPERATIONS_DOCS=TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md, current branch/QA behavior, not production.
INITIAL_FEATURE_DOC=docs/superpowers/specs/2026-10-18-r218-02-03-voice-music-controls.md MU01..12.
COMPARISON_DOC=TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md + remainingMusiccrosswalk + pinnedBot/Webcontractaudit.
MU07-A chỉ đóng quay lại bộ cũ/chọn/sửa/local field lifecycle; wholeMU07 và
next-set/edit-regenerate/stylemapping/half-full/audio2tracks/player/editor/
delivery/runtime/LIVE còn mở. Không dùng pinnedBotbranch làm productiontruth.

## 2. Bằng chứng verify

- NewunitRED19total/1pass/18expectedassertfail/0harnesserrors1377.8832ms →
  GREEN19pass0fail3524.4898ms;test171lines,actualsync/renderer/catalogue.
- Browserbaseline24/24missinghistory,errors/external/UIwrites0,expectedexit1.
- Final48signedapp+controlledclientflow/capabilityfixtures,actual handlers:
  Apply1→estimateomit→closedhistory→Apply2→staleF/confirm→edit/newquote→
  modeBack→logout/token/explicitempty. All48records true; no native calls.
- Current+retained2304textsamples AAmin5.217;hover48min5.161/focus48min5.2;
  disclosure44px/Enter/AX/text2x/nooverflow. Errors/external/UIwrites0.
- 144response/sourcehashchecks matched afterUTF8CRLF→LF; no rawbyteidentity
  claim. RawfinalSHA c3621776f01a684d80e7569b03da88d9a0f332be64b385d9bf845eef60e1e38f.
  RepresentativeVIlight/create and dark/song mobile images inspected.
- FullNode1276pass0fail0skip14296.0041ms;boundedPython119pass/2existingwarnings
  74.32s. FullrepositorypytestNOT_RUN;historicaltechnicalfailuresT0unchanged.
- node--checkportal/i18n/newtest exit0; compileall seven relevantPythonmodules
  exit0. No bot.py in WebApp contract; no Bot import/run required or attempted.
- OwnQAserver57885newline terminalexit0;tempDB/assets06pqmj78removed;
  outside-sandbox read-onlyGet-NetTCPConnection32417 count0. Otherprocessesuntouched.

Evidence `reports/audit/R218-MUSIC-RETAINED-OPTIONS-QA-20261024.json`.
Browserpluginabsent; existingheadlessEdge/Playwright/noinstall/novisiblebrowser.
QAauth/locale/sessionlastseen writes only ephemeralDB during setup; no claim
zeroDBwrites. No OS DynamicType/nativekeyboard/PWA/FPS/LCP/INP/CLS/production
proof. Back-readiness is diagnostic only; motion remains last and open.

## 3. Tester và push gate

TESTER_PROJECT_ID=R218-MUSIC-MU07A-20261024
TESTER_PROJECT_STATUS=READY
TESTER_CASES=KIEM-THU/DANH-SACH-CASE.md MU07A-01..06, sameBASE/PR661/Issue664.
TESTER_METADATA=687splitlines/85177UTF8LFbytes/SHA415a02dcc1a6091b047d2febef794740b77b06e6698a9995d0d6a2608b550f49.
TESTER_GATE=32pass/1POSIXfilemodedeselected/1existingwarning4.73s/exit0; no test weakened for Windows. Initial gate exposed stale metadata31pass/1fail; only manifest refreshed, then32pass.
GITHUB_SETUP=PR661OPEN/CLEAN exactHEAD52017494 andIssue664OPEN readback;22labels/12requiredpresent;two templates unchanged;Projects not revalidated/missingprojectscope, noauthrefresh or massissuecreation;closed412 untouched.
PUSH_GATE=READY_AFTER_CLEAN_SOURCE_DOCS_COMMIT_AND_WEB_ONLY_PROVENANCE_VERIFY.

Source/docscommit first; on cleanHEAD refresh+verify Web-onlyprovenance,
commit onlypreflight.json/web_inventory.json, then singlepushremote`github`
(origin islocalbundle). Read remoteSHA and bothCIjobs on exactnewHEAD; receipt
required before tickA06/MU07-A. Do not merge/deploy unfinishedPR/master.
No receipt-only trackedcommit/provenance/CIloop; roll finalreceipt in next
realcodebatch. MERGED!=DEPLOYED!=LIVE. GoalACTIVE, followorderedUIchecklist.

BASELINE_FAILURES=18expectedunitassertions +24expectedmissinghistorybrowserstates.
BRANCH_FAILURES=0 in declared application suites; metadatafail fixed with remeasurement, no runtime change.
NEW_FAILURES=0 in comparable declaredscope; freshremoteCIpending.
PROTECTED_COMPARATORS=PASS;BLOCKERS=NONE forA01_A05;A06remoteverificationpending.
PROVIDER_CALLS=0 applicationproviders; authorizedGeminisourcehandoffs separately disclosed.
WALLET_MUTATIONS=0;DEPLOY=NO;LIVE_PASS=NOT_TESTED;GOAL=ACTIVE;MOTION=LAST.
LESSON_CANDIDATE=NONE.
