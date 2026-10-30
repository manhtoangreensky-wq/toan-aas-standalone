# R218 SubDub E3 — single-batch pre-push report

Đang đọc và áp dụng skill owner-governed-codex cho task này.

PRODUCT=standaloneWebApp;BRANCH=webapp-r218-billing-ui-20261022;PR661;Issue664.
PARENT_BASE=79cd75d3d8ee50685bbecd4056f7d84a79f8e68a.
UI_SOURCE=26a966e25778229a0b76cfb045fa384d5d34b4eb.
PUSH_GATE=DOCS_TESTER_MAIN_COMPAT_READY_FINAL_PROVENANCE_NEXT_GIT_GATE
PUSH=NO;MERGE_TO_MAIN=NO;DEPLOY=NO;LIVE_PASS=NOT_TESTED.

## One cohesive E3 source batch

Five local checkpoints,notfive pushes:6da9b14a labels/contrast,
3d5e59dc ranges,c5f09f2e groups,7e35f0ab Edit,26a966e2 readiness.
ComparedwithparentBASE onlyproductionportal.js andportal-theme.css changed:
JS168added15removed,CSS110added0removed. Three new SubDub testfiles;
672oldtestpaths areprotected. No API/auth/integration/engine/payment/Bot edits.

Parentactual168unique/588choices168VoiceReturns/672fourLFassetchecks;
14448nondecorativeleaftextsamples min5.223799/unknown0/AAfail0;
168rangesmin200×44. Allstrictsummarycounters0:interaction/unlabelled/AXnote/
range/font/overflow/reportvisible/missingEdit/errors/external/UIwrites.
Readinessnative72/pending12/EDIT168 independentlyvalidatedC0I0M0;
parentindependentTesterREADY_FOR_SCOPED_LOCAL_ACCEPTANCE. FullNode1301/focused74/PythonCSS21;
Testerportable32pass1deselected/1existingwarning. FullpytestNOT_RUN/T0retained.

## Operating docs and initial feature comparison

TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md haslatestreadinesscandidate behavior,
actualrootcause/counts and exact productionNOT_MEASURED boundaries.
TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md comparesoriginal2026-10-18 spec,
including localsettingsonlyaftergenuinesession and non-authority of engine UI.
reports/audit/R218-SUBDUB-FINAL-UI-CROSSWALK-20261024.md retainsall21SDIDs,
concrete UIevidence and separateT0gaps. OriginalsourceREADfindings/history
remaininlowersection;latestcandidateat top. No requirementdiscarded.
Deadcode/library/borrowedimages auditNOT_RUN,notblanket“clean”claim.
TesteridentifiedoriginalSD15dedicatedon/offUIstillabsent;0%muteworksisnotfull
SD15completion. Crosswalkqualifierrestored/masterSD-D4OPENimmediatelyafter
scopedE3deliverybeforeImage;notT0,norequirementdiscarded. NoUIcodechangehere.

## Independent Tester workspace

SessionR218-SDE3-TESTER-20261024 manifestreports/tester/R218-SUBDUB-E3-20261024.md.
8newSDE3cases inuniqueKIEM-THU/DANH-SACH-CASE.md;old48WAcasesunchanged.
Guideupdated;portableLFfilemetadata remeasured/32portablecontractspass.
Remote22labels/12requiredpresent;2localforms retained. Projectlist unavailable
missingread:project,noauthrefresh/login/logout/permissionchanges.
No bulkissuecreation;useexistingIssue664,closed412untouched.
Testerdoesnotreplaceactualruntimewithsourceonly:rootraw168independently
parsed,ownfocused/portabletests;freshindependentbrowserrunnotrequiredbyseat.

## Newly discovered main compatibility gate before delivery

ReadbackPR661OPEN/DIRTY,remoteHEAD79cd75d3. Newmain0e1b49b5 containsSFX#663.
Read-onlymerge-tree findsconflictsONLYpreflight.json/web_inventory.json;
UIassets sourceconflict0. MainSFXcode/test/docs must bepreservedbyte-exact.
AMENDMENT-45-SDE3-DELIVERY-MAIN-COMPAT.md recordsorderedmechanicalmerge
maininto feature (notfeatureinto main),cleanmergedsource/Webonlyprovenance
refresh+verify,exactmain5file/UI4assetcomparators andfreshlocalregressions.
No rebase/forcepush/sourcefix/provider/wallet/production actionauthorizedbythisgate.
Do notpush untilgeneratedevidence matchesmergedsource/Testeraccepted.

ActualmaincompatSOURCE `2a9250793c55936083a5f26dfa368af82757d71d` nowcommitted:
main5nonartifactfiles byte-exact andUI4assets byte-exact toacceptedcandidate;
only2generatedartifactconflicts resolvedwith declaredintermediatemainversions,
thenWeb-onlyrefresh oncleantrackedsource snapshot. NoSFXlogic authoredhere.
FreshNode1301/0fail0skip/21992.9395ms. IsolatedPythoncombined85pass1deselected/
2warnings/6.18s,exit0;externalconnectattempts0,36Windowslocalloopbackconnects.
Syntax/compile8modules/diffexit0. Providers/productionDBnotused.

QA history retained:initialnetworkguard blockedWindowsasyncio127.0.0.1selfpipe,
15fail70pass1deselected20.96s beforeapprequests;QAguardcorrectedloopbackonly.
Sandboxloopbackrerunthenhung;ownedexactwrapperPID19028 verified/nochildren,
stoppedonlythatwrapper;terminal-1,ownedtempgti3r0myremovedafterabsolute-path/
reparse checks. Approvedoutside-sandboxsameQA85pass;noapp/test/securitychange.
LocalclonefirstMSYSsandboxAccessDenied;freshuniquelocalcloneoutsideapproved,
Web-onlyrefresh+verifyexit0 atsource2a925079. NoBotread/import/provider.

This report is a sourcecheckpoint document. Its own edit changes the audit
fingerprint; aftercommittingcurrentdocs,regenerate2WebevidenceJSON fromclean
finalsource andverify atfinaldeliveryHEAD BEFOREpush. Actualfingerprint livesin
reports/migration/preflight.json andweb_inventory.json,notself-referentialhere.
GitHubIssue664finalreceipt willrecordexactdeliveryHEAD/run/result separately.

## Runtime cleanup and truth boundaries

Ownedbrowsers82556/37435/45772terminal0;QAserver48945newlineexit0.
Outsideprobe52156listener0 andisolatedtemp0vfy_b36removed. Nootherprocessstop.
ActualQSusers onlyinremovedisolatedDB. Providers/bridge/PayOSoff.
HistoricalU1C3AXcauseUNKNOWN/U2originalLCrunstateUNKNOWN retained;
currentearlyauthoringREAD36mismatch27changednot36loss,nowUIgatefixed.
Upload/ASR/translation/canonicalvoices/speakers/quote/jobs/filedelivery/reuseT0.
NativeSafari/iOS/OStextscale/PWA/motion/FPS/LCP/CLS/INP notproved.
GoalACTIVE;motionLAST. AfterallUIUX+motion,stopforOwnerbeforetechnicalT0.

## Final delivery evidence fields — populate from actual terminal only

TESTER=SCOPED_LOCAL_ACCEPTED;MAIN_COMPAT=PASS;PROVENANCE=FINAL_SOURCE_REFRESH_REQUIRED;FINAL_HEAD=NOT_YET_CREATED.
TESTER_DISPOSITION=ACCEPTED_LOCAL_ONLY_REPORT_SHA9b5f29a4aafd8f423d9eaf21a5d09a99466d7f4490509aebfe330d8b453e82b9;
fresh74Node/32portable1deselected;runtime4rawindependentinspection,notnewbrowser.
REMOTE_HEAD=79cd75d3d8ee50685bbecd4056f7d84a79f8e68a;CI_EXACT_HEAD=NOT_RUN.
PROVIDER_CALLS_APP=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_MUTATIONS=0;
ENV_PERSISTENT_MUTATIONS=0;AUTH_SETTINGS_MUTATIONS=0.
No wholeSubDub/master/runtime/LIVE/goalcompletion fromthisUIbatch.
