# E3-READINESS — native authoring readiness, no anonymous draft adoption

## Identity / dependency / one outcome

SPEC_ID=E3-READINESS;PHASE=REPORT;HANDOFF_ROUND=2;FAILED_HANDOFFS=2.
ROOT=C:/Users/toann/Documents/Codex/_webapp-r218-voice
BASE_SHA=7e35f0ab78a32b2d4d7bffc7536a4dd381c21151
BRANCHwebapp-r218-billing-ui-20261022/PR661/Issue664.
DependsEDITLOCALreceipt6382683426. READcontract6382724646/finding6382804310.
Owner "tiếp tục xử lý triệt để theo thứ tự";allWebUI/noemptymeaninglessboxes,
noexperimentalcopy/motionLAST. COMPLEX/SINGLE;oneFlash3.8workerperrepo.
R1/R2maxsameSPEC_IDthenSolxhighnarrowtakeover/noR3/counterreset.

ActualREAD72:36held-realmeearly/36stable,early36reviewmismatch/27changed
controls afterhydration;9unchangedallDUBBING_ONLYstill6immediatemismatches.
Stable0mismatch0loss/AXnote0/errors-external-UIwrites0/288LFassets;
rawSHA47d1070c69e0fd57bc3f922d2ef0c11ba89945d47b1345663e43723c53ff3685.
IndependentC0/I1/M0 confirms currentpreauthauthoringdefect;exactevents retaining
9DubcasesUNKNOWN,notall36inputloss. Sourcecapture returnsnullwithoutdraft
session while editablecontrols acceptinput;reviewdefaultsdiffer. Auth/session
clearfences and integrationPromiseall/remount areprotected,notchanged.
U1C3AXnotreproducedcauseUNKNOWN;U2samecurrentsymptomproved/originalrun
stateunknown. Thisfixdoesnotretroactivelydiagnoseoriginalmissingcaptures.

Outcome:unverifiedSubDubcannotacceptnormalnativeauthoring;real signedremount
enableslocalsettingsonly,keepspermanentupload/engineguards;normalreadyUI and
publiclinks/layout unchanged. No anonymousdraftcarryover/authbusinesschange.
Nochildpush/merge/deploy;parentfinal/Tester/provenance/oneE3pushCIremain.

## Allowlist / protected

1.static/portal/portal.js ONLY:
  - three copy rows before modeSelectorLabel;
  - one new pure subDubAuthoringMarkup helper before renderSubDubHub;
  - localsession/readinessconst+articledatahook+onependinginlineparagraph;
  - finalreturn viahelper, no oldtemplatecontrols rewrite/wrapper;
  - updateSubDubSettingsSummary nextHtml expression wrapped viahelper and
    root.dataset readinessflag;existingE607cacheguard unchanged.
2.NEWtests/subdub-authoring-readiness.test.mjs <=220lines/exactly6tests.
NO CSSneeded:existingportal-form-note/readinessink;NOnewvisualcard/fieldset/
gridwrapper/animation/style/token/icon. Rootdocs/checklists/auditsonly.
ALLoldtests/17existinghelpers exceptdeclarednextHtml wrapper/renderHub small
insertions protected. Especiallycapture/sync/normalizer/Voicecontinuation/
auth/integration/backend/Bot/engine/provider/wallet/PayOS/ENV/DB/motion/Chat.
No renames/signatures/storage/globalcache/requests/newpackages/refactor.

## Exact copy

Newkey authoringSessionPending beforeeach existingmodeSelectorLabel:
VI `Thiết lập mở sau khi phiên đăng nhập được xác nhận.`
EN `Settings open after your sign-in session is confirmed.`
ZH `登录状态确认后即可编辑设置。`
Shown onceONLYunverified,inlinep/form-note/role=status,nobox/pill/fakebusy.
Do not say loginfailed/loadingcomplete/engineavailable;thisisfactuallocalgate.

## Exact pure helper — quote-aware, SubDub strings only

```js
  function subDubAuthoringMarkup(html, ready) {
    if (ready === true) return html;
    return html.replace(/<(?:button|input|select|textarea)\b(?:"[^"]*"|'[^']*'|[^'">])*>/gi, (tag) => {
      const attributes = tag.replace(/"[^"]*"|'[^']*'/g, "");
      return /\sdisabled(?:\s|=|\/?>)/i.test(attributes) ? tag : tag.replace(/^<([a-z]+)/i, "<$1 disabled");
    });
  }
```
GeneratedHTMLonly,notsanitizer/API/parserforarbitrarydocuments. Fullready
returnsoriginalstringexact;unreadyonlyaddsboolean disabled tofourformtag
families,neveranchors/options/labels/values/names/IDs/ARIA/callbacks/text.
Quotedattrvalues removedonlyfromtemporarydisabled-detectionstring;opening
tagregexaccountsfor>`insidequotes`;do notsimplematchdisabledwordinsidequotes.
Existingdisabledattr retainedexact/notduplicated;NEVER disabled="false".

## Exact renderer / summary amendments

Inside renderSubDubHub aftercopy andbeforedraft:
```js
    const session = context && context.session;
    const authoringReady = Boolean(session && session.authenticated === true
      && typeof session.csrfToken === "string" && session.csrfToken.length > 0);
```
SamepredicateasexistingSubDubdraft-sessionprecondition;noCSRFcreation/readiness
override/secretoutput orAPIpermission. csrfReadyflagnotnewauthority;permanent
serverguards unchanged. Missing/falseauth/missing-or-empty-nonstringtokenfalse.

Articleopening adds only data-subdub-authoring-ready="true|false",literalvalue.
ImmediatelyafterrenderHero, beforeexistingmodepicker insert conditional:
```js
      ${authoringReady ? "" : `<p class="portal-form-note" role="status" data-subdub-authoring-session-status>${safeText(copy.authoringSessionPending)}</p>`}
```
No extra title/description/empty region. FinalrenderHubreturn:
`return subDubAuthoringMarkup(rendered, authoringReady);`
Existingrenderedconst/stages/mode/contentremainexact otherwise.

ExistingupdateSummarycurrentnextHtml line becomes ONLY:
```js
    const nextHtml = subDubAuthoringMarkup(renderSubDubSettingsRows(subDubDraftSnapshot(), mode, root.getAttribute("lang")), root.dataset?.subdubAuthoringReady === "true");
```
KeepE607element-localcachecomparison/assignment/returnexact,alloldmode/locale/
draftguards unchanged. Newrootdataset markergeneratedbyrenderHub,notnetwork
authority. Absent/falsemarkerkeepsregeneratedEditnative-disabled;truemarker
keepsrowmarkup. No oldhandler/keymap/capture/sessionfunctionchanges.

## Ordered 2–5min tasks, one shared gate

1.NEWunitartifact first:actualrendererblock constSUBDUB_PRODUCT_MODES→before
  renderDocumentHub +actualcompanionURLhelper. Sameenvironment windowlocation,
  interfaceLocaleFor(context)=>context.locale,safeTextescape5chars,irrelevant
  hero/badgestubs,realtransientMap. Expose actualrenderHub/newMarkup/updateSummary
  usingtypeofnewhelper nullfortrueRED,not swallowedReferenceError. NoSUTmock.
2.Sixbehavior tests<=220lines,independentliteralexpectations:
  (a) all12mode/localeviews unverifiedcontexts(missing,falseauth/missingempty/
      nonstringtoken) havepositiveactualformcontrols andZEROenablednative
      openingtags;reasononce,rootmarkerfalse. Noauthcontexttests silentlyready.
  (b) genuine-ready realrender keepsall7lane/4mode/publiclinks/values/callbacks,
      editableformcontrolsnotdisabled;file/sourceLanguage/CTAstilldisabled,
      roottrue/reasonabsent. Use literal namedguardedtargets,notallreadyclaim.
  (c) actualpurehelperquote-awarefixtures:fourtagfamilies,disabledboolean/
      quoteddisabledattr/no duplicates;titlecontainingdisabledor>mustnot
      be mistakenforattr;anchors/escapedtext/non-formtags unchanged;
      strictreadytrueidentity/unreadyidempotence.
  (d) actualupdateSummary withroot.dataset false/missing/true,actualrowHTML
      gatefollowsreadiness;repeatedHTMLkeepsE607nodeidentity,readinesschange
      writesonce. Real draft/renderer,typedDOMdouble withonlytrueboundaryI/O.
  (e) actualrender/helperdoesnotmutatesigned/anonymousdraftMap/window/session
      fixture;no anonymousadoption/storage/network/history;guardedcontrols
      retaincopy/selectedvalues. Do not assertonlyuntouchedmockproperties
      without invoking actualfunctions.
  (f) readyunreadystructuralcomparison:onlydataflag/status/disabledattributes
      differ, hierarchy/classes/IDs/values/anchorhref/copyoldnamespreserved;
      fieldset/gridwrappernone;locale exactpendingtext independentliteralmap.
3.Productionexactold/newrecords only. RootappliesNEWTESTalone→expectedRED
  newbehavior0harness,then exactproduction→6GREEN;alloldtestsunchanged.
  Oldrenderfixtureslackingsession nowexpecteddisabledcontrolsbutsamevalues/
  structure;do notweakengenuine-readypredicateoroldassertions to forcegreen.

## Acceptance

R711:actualREAD72beforecode remainsRED proof;newtest-onlyREDbeforeproduction.
R712:6newunit/focused74/fullNode1301 expected ifcountsunrelatedunchanged;
  PythonCSS21/syntaxcompile6/diff0. Reportactual,notpromise.
R713:36early/36stable sameactualheldrealresponsecases. Earlybuttons/inputs/
  selects native-disabled includingmode/Edit;normalclick/keyboard mustnot
  author;noforce=true/noJSvalue-setting ondisabledcontrols. Releaseidentical
  realresponse then sameauthoring/review/signeddraft works,nomismatch/loss.
  Provepermanentfile/sourceLanguage/CTAremain disabled andpublicanchorsretained.
R714:allfourmodes/locales/themes/7views final168 stable matrix keepsLABEL/
  CONTRAST/RANGE/GROUP/EDIT/B4/C3/D3/Voiceflow/keyboard/44targets/gates/assets/
  errors-external-UIwrites-overflow0. No newlayoutshift/wrapper/regression.
  Pendinginline actualvisualAX/contrast>=4.5 once/readyabsent;themephone+desktop.
R715:actualnoanonymouscarryover/freshaccountsessionfence testsunchanged;
  originalC3AXUNKNOWNnotretroactivelyclosed/U2originalstateunknownretained.
R716:exactpacket/reversewholeJSBASELF/protectedfunctions/files/oldtestsChat,
  independentreviewC0I0/currentdocs/checklist/state/localcheckpoint/receipt;
  thenparentfinal/Tester/docs/provenance/ONEE3push/exactHEADCI,nomerge/deploy.

Commandsrootonly:node --test tests/subdub-authoring-readiness.test.mjs;
node --test tests/subdub*.test.mjs;node --test tests/*.test.mjs;
python -m pytest -q tests/test_portal_aura_theme_contracts.py;compile6;
node <QA>/browser-SDE3-READINESS.cjs <isolatedorigin>.
WorkerVERIFY=NOT_RUN. Con số lệch->LỆCH;khôngchạyđược->NOT_RUN;cấmtựsuyĐẠT.

## Frozen scope / delivery

Source-onlystdout/no tools/runtime/customer/tokenpayloads;rootapply/QA/Git.
Noinstall/IDE/browserwindow/login/logout/settings/ENV/authbusiness/integration/
schema/Bot/engine/provider/wallet/productionmutation. Stopaffectedactionfor
SHA/branch/outsideallowlist/secret/failinggate/anotherworker;noopportunisticfix.
PROVIDER_CALLS_APP=0/WALLET_MUTATIONS=0/DEPLOY=NO/LIVE_PASS=NOT_TESTED.
MotionLAST/goalACTIVE. NoAGYR3/counterreset/childpush.

## R2 NEW_TEST-only repair — same spec, source frozen

R1sourceC0/I0/M0/exact8records;allfrozenSHA46b97b444b32b5d33decbe00ab1fd469a24ad1bc0205ef4756d969a3d8596c53.
NoR1source/testapplied. Rawnewunit6allHARNESSerrors(draftsundefined);other
badfixture/weakassertions in REVIEW-44-SDE3-READINESS-R1.md. R2 returnsONLY
NEW_TEST6<=220lines+REPORT,not anynewproductionrecord. Rootassemblesoriginal8.
ExposeactualMap as transientFormDrafts innewFunctionorattachouterMapafterfn,
neverundefinedouterlexicalreference. NewFactorymustassertallsourceboundaries.
Allunverifiedcontexts×all12mode/localeviews,notrotation. Genuine-readyall12
views:exact3permanentdisabledguardsbyactualsourcefile/sourceLang/CTA,EVERY
othernativecontrolenabled;4modebuttons/7choicespervoicepanel/3callbacks/
publicanchorsandselectedvaluesretained. No inventeddata-subdub-mode attribute.
SummarydoubleEXACTqueries:[data-subdub-settings-rows]and
[data-subdub-mode-select][aria-selected="true"],modeButtongetAttribute only
data-subdub-mode-select→DUBBING_ONLY. Rootdatasetfalse/missing/true;record
actualrowwritesANDchildidentity onrepeats,readinesschangewritesonce.
Keep existingfieldsets,notassertnone. Bothstatesnormalizeonlynewflag/status/
addeddisabled,comparehierarchy+links/values;sourcecomparatorprotectsno wrapper.
Map/session/windowbefore-after snapshotonlyAFTERactualrender/helpercalls;
assertactualcheckedcustomvoice/selectedja/customISO0_200/fullreviewspans,
notgenericincludes ofoptionsalwayspresent. Noevalcatch/swallowederrors.
R2test-onlyREDbeforeanysource;twofailures→Solxhighsamecounter/noR3.
Pendingstatusoutsidepanel mustalsobevisible/inactualAX/readable4.5unknown0,
phone+desktop/lightdark;rootQAaddsseparatepending-statecoverage.

## Local empirical result — no parent/delivery/engine completion claim

FlashR1/R2newunitgatesfailed;Solxhigh repairedonlynewunit172lines6tests.
All8R1productionrecordsbyteidentical. Actualtest-onlyRED0pass6expectedassert/
0harness/189.1968ms thenapply;GREEN6/435.8412ms/focused74/fullNode1301/
PythonCSS21/syntaxcompile6diff0. Source+runtimeindependentC0I0M0.
Nativeactual72/36heldrealresponseearly0enabledordinaryclickTabblocked36/
readycoherent72/288LFassets;pending12VIENZHlightdark3901440actualvisibleAX/
readyabsent/min11.772481unknown0;finalstable168/1218clicks336keyboard1050edits/
168modeLoops168VoiceReturns504assets/44x44/text12.35155focus5.86008unknown0/
errors-external-UIwrites-overflow0. Pending12doesnothaveownassethashcapture.
Evidence reports/audit/R218-SUBDUB-AUTHORING-READINESS-QA-20261024.json.
R716localcheckpoint/receipt finalizing;parentfinal/Tester/docs/comparison/
provenance/oneE3push/exactHEADCI open. HistoricalU1/U2UNKNOWNtruthretained.
