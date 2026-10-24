# SD-B3 — báo cáo trước push

Đang đọc và áp dụng skill owner-governed-codex cho task này.

TASK=SD-B3-INPUT-FONT
BASE_SHA=06afc2c3abc554e69c7be36604fee310f877c8c6
HEAD_SHA=Working source/docs; final SHA recorded from Git/Issue664 after commit, not predicted.
BRANCH=webapp-r218-billing-ui-20261022
PR=https://github.com/manhtoangreensky-wq/toan-aas-standalone/pull/661
TRACKER=https://github.com/manhtoangreensky-wq/toan-aas-standalone/issues/664
CONTRACT_RECEIPT=6373966632;MU07-Adependencyaccepted6373888334.

## 1. Review code và nghiệp vụ hiện tại

Một productionfile, bốn dòng CSS: thêm rule `font-size:16px` cho
`.portal-subdub-hub :is(.portal-input,.portal-select)` trước FinalChat.
Không sửa global class, radio/checkbox, JS, field/name/ID/value/ARIA/disabled,
auth/API/schema/engine/Bot/provider/ví/PayOS/ENV hoặc motion.
Root cause: SubDub còn kế thừa generic15px thay vì có override đọc/nhập.
Không tuyên bố đo hoặc sửa native iOS autozoom bằng CSS assertion.

Flash3.8HighR1 source-only trả exact1record, SUCCESS117.4125259s/1turn,
command10521UTF16chars,workerVERIFYNOT_RUN. Không R2/R3 hoặc mởIDE/settings.
Root chỉ apply sau actualfontRED; independentreviewC0/I0/M0. Exactworker
composition và reverse toànCSS về BASE sauLFnormalize; JS/backend/oldtests/
Chat không đổi. Không fix ké search/Smartduplicate/emptyreport.

OPERATIONS_DOCS=TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md, branch/QA notproduction.
INITIAL_FEATURE_DOC=docs/superpowers/specs/2026-10-18-r218-subdub-bot-parity-uiux.md,SD01..21.
COMPARISON_DOC=TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md.
ORDERED_PLAN=docs/superpowers/plans/2026-10-24-r218-subdub-ui-closeout.md.
Từng21SDrequirement giữ UIlock/gap/T0 riêng. CurrentREAD48:21targetcodesmatch
pinnedBotcatalog,36targetstatesfont15/nosearch,24Smartboxeslặp/48emptyreports.
B3 chỉ font;B4search→C3voice→D3emptyreview→E3finalUI,technicalauthorityT0.
Không biến cócontrols thành upload/ASR/dịch/dub/speaker/quote/job/outputPASS.

## 2. Verify và giới hạn

- ActualREDexit1:sourcefile/source-language/segmentformat/position đều15px,
  cần>=16. Assertion rõ,0harnesserrors. ProductionchưaapplykhiRED.
- FinalGREEN96configs,552visibleinput/selectsamples đều16px; VIENZH,
  fourmodes,light390/1440,dark390/1440/360/375/768/844landscape.
- Actualsourcewithsubtitles/formatshort/positiontopcenter/targetJapanese,
  Smartlane/7choices,number/rangegốc0/lồng200,đổimode/chọnlạitabgốcgiữdraft;
  disabledsourcefile/sourcelanguage/CTA giữ;focus+Tabthật;Musicbrief16px.
- 288 downloaded/sourceLFhashchecks khớp;overflow/errors/external/UIwrites0.
  QAauth/locale/sessionlastseen writes temporaryDB during setup only.
- RawfinalSHA d7edaef2c6c4ee2d5491dce572e0c259645bd9a2fc4e1ea78b35326f37d5fe4c.
  ImagesVIlight/darkmobile inspected; evidenceR218-SUBDUB-INPUT-FONT-QA-20261024.json.
- Firstgreen16pxthentimeout: harnessexpectedbrowserBackforreplaceStatetabs.
  Correctedonlytesttochooseoriginaltab;noapphistorychange/failedrawretained.
  Firstfinal96alreadyfontPASS;complete96addsactualsource/format/position/Tab.
- FocusedNode68pass0fail3346.5482ms; fullNode1276pass0fail0skip13406.8104ms.
  Python21pass/1existingwarning0.89s. Syntax/compileall6relevantmodulesexit0.
  FullrepositorypytestNOT_RUN;historicaltechnicalT0notmodified.
- OwnedQA92105/96476/85885 closednewlineexit0;temporaryDB/assetsremoved;
  listeners51978/55730/14007=0 readoutside sandbox;nootherprocessstopped.

Browserpluginabsent;existingheadlessEdge/Playwright/noinstall/novisiblebrowser.
Not OStextscale/nativekeyboard/installedPWA/offline/SWupdate/alltextAA/FPS/
LCP/INP/CLS/production/LIVEproof. No nativefeature/provider call or fixtures.
Motion stayslast;thisfontpatchdoesnotclosejank.

## 3. Tester và push gate

TESTER_PROJECT_ID=R218-SUBDUB-B3-20261024
TESTER_PROJECT_STATUS=READY
TESTER_CASES=KIEM-THU/DANH-SACH-CASE.md SDB3-01..03,sameBASE/PR661/Issue664.
TESTER_METADATA=704splitlines/86480UTF8LFbytes/SHA4017ae9591f77b3932fed18c4618f4d4cd9dd9bc14f388ed3f1c3fa6e3d994b6.
TESTER_GATE=32pass/1POSIXdeselected/1existingwarning0.96s;Linux testunchanged.
GITHUB_SETUP=ReuseIssue664/PR661;22labels/12requiredlastreadback;two templates
unchanged;Projectsnotrevalidated/missingprojectscope,noauthrefresh;closed412untouched.
PUSH_GATE=READY_AFTER_CLEAN_SOURCE_DOCS_COMMIT_AND_WEB_ONLY_PROVENANCE_VERIFY.

Source/docscommit→cleanHEADWebonlyrefresh+verify→commit2generatedfiles→
onepushremote`github`→exactHEAD/readback/CIboth→receipt/tickB3only.
Do notmerge/deployunfinishedwholePR/master. No receipt-onlytrackedcommitloop;
finaltruthreceipt/ignoredresumeledgerrolledforwardnextrealcodebatch.

BASELINE_FAILURES=4visible15pxassertioninputs in firstRED.
BRANCH_FAILURES=0 declaredapplicationchecks;harnessBackerrorcorrectedwithoutappchange.
NEW_FAILURES=0 comparabledeclaredscope;remoteCIpending.
PROTECTED_COMPARATORS=PASSexactR1/fullCSSreverse/JSbackendtestsChat.
PROVIDER_CALLS=0 applicationproviders;authorizedGeminihandoffseparatelydisclosed.
WALLET_MUTATIONS=0;PRODUCTION_DATA_MUTATIONS=0;DEPLOY=NO;LIVE_PASS=NOT_TESTED.
BLOCKERS=NONE forlocalB301..304;B305remotegatepending.
GOAL=ACTIVE;MOTION=LAST;LESSON_CANDIDATE=NONE.
