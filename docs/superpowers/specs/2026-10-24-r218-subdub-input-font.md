# SD-B3-INPUT-FONT — đọc và nhập không phải phóng chữ riêng

BOUNDED/SIMPLE/SINGLE;BASE06afc2c3abc554e69c7be36604fee310f877c8c6.
RootC:/Users/toann/Documents/Codex/_webapp-r218-voice;branchwebapp-r218-billing-ui-20261022.
PR661/Issue664. DependencyMU07-Areceipt6373888334/CI40016578805bothSUCCESS.
Owner: “xử lý triệt để toàn bộ theo thứ tự ... phần cuối là xử lý motion”.
ThisisexistingapprovedUIreadabilityrequirement,nofeature/backendexpansion.

## READ / root cause

ActualsignedQA48states:36target-language selects computed15px, both themes,
VIENZH/3901440. Inherited generic `.portal-select` font has not been overridden
forSubDub as Musicwas. NativeiOS autozoom not measured, do notclaimfixeddevice
behavior;threshold16px is acceptance for text-entryreadability/zoomrisk.
NoJS/option/lane/quote/providerchangesrequired.

## Exact scope / design

Only productionfile `static/portal/portal-theme.css`, insert one scopedrule
before unique `/* Final light AI Chat Workspace surface */` marker:

```css
.portal-subdub-hub :is(.portal-input, .portal-select) {
  font-size: 16px;
}
```

Nootherproperty/CSSrule/token/rawpalette/important/mediaquery/motion.
Do notchangegenericinputruleorFinalChattail. Bothsourcefileinput/disabled
sourceselect,numbervolumeinput,target/custom/position/formatselectkeep
originalvalue/disabled/readiness/name/ID/layout/focus/ARIA/gate.
Do notgrowradio/checkboxbecauseonlyportal-input/selectclassesaretargeted.
Existingblue/navy/teal/fontfamily/spacingnotchanged. Nootherproductsaffected.

Allowedtest:root-ownedactualbrowserRED/GREENscript outsidecommittedrepo,
existingfocused/fullNodesuites unchanged. No pointlessgrep-onlynewunittest.
Docs/Tester/master/state/evidenceallowedasdelivery,workerCSSonly.
Protected:allJS/i18n/API/backend/auth/Bot/provider/ví/PayOS/ENV/productiondata,
existingSD-B2/C2/D2/E2/MusicFH/MU07-A/alloldtests/Chattail/motion.

## Acceptance gates

- B301:actualbaselineassertcomputedfont>=16 failsas15px,notselector/harnesserror.
  SourcepatchonlyafterRED. Scriptchecksrealvisibleinput/selectnodes.
- B302:final96configs=48READmatrixbaseline+48small/tablet/landscape (modes4 ×
  VIENZH/themes/3901440plusdark360375768844), everyvisibleclassinput/select
  computed16px;no horizontaloverflow. Countnodes, notfixedmockexpectation.
- B303:language/source-state/format/voice/volume0and200 remainactualinteractive;
  switchmodeandselectoriginaltabkeepsdraft;allgates/sourcefile/CTAremain disabled. Music
  unaffectedfont/controlcomparators. NoAPIresponsefixturesneeded.
- B304:syntax/fullNode1276baseline/focusedSD,PythonscopedCSScontracts;
  independentdiffreviewandreverse-removalmakesCSSexactBASEafterLFnormalize;
  JS/i18n/portal.css/backend/oldtests/Chatbyteequalbaseline.
- B305:docs/comparison/Testercases/prepush/Webonlyprovenance/singlepush/CIboth/
  receipt;thenunlockB4,notwholeSubDub/motion/runtime.

## Checklist before BUILD

- [x] READactual48/36font15/sourceCSS;MU07-Aaccepted.
- [x] ScopeexactoneCSSrule/oneproductionfile;bounds/protectedcomparators.
- [x] B301actual4font15assertionREDexit1/0harnesserrorsbeforepatch.
- [x] Flash3.8HighR1SUCCESS117.4125259s/1turn,exact1CSSrecord;noR2/noR3.
- [x] B302final96/552font16samples/288LFassetchecks/focus+Tab/screenshots/overflow0;noallAXclaim.
- [x] B303actualsource/format/position/language/Smart/volume0-200/modereturn/gatespreserved96.
- [x] B304focused68/fullNode1276/Python21/reviewC0I0M0/reverseCSS/JSbackendoldtestsChatunchanged.
- [x] B305Tester32/docs/provenancea9d49f62/source32d3b4e2/HEAD4d66ef14/CI40020963811bothSUCCESS456records/receipt6374462006/IssueB3checkedreadback.

## Steps 2–5minutes each / verify

1. WorkerreturnsJSON`PRODUCTION_EDITS:[{path,old,new}],REPORT`withonlyCSSrule,
   noTOOLS/writes/Git/terminal/network/IDE/auth/settings/runtimeQAdata.
2. Rootrunsbaselinebrowser`node <QA>/subdub-input-font.cjs <isolatedorigin> red`
   →exit1font15assertion;thenapplyexactworkerpatchafterreview.
3. Rootsamebrowsergreen→0fontfailures/overflow/errors/external/UIwrites;
   actualSDcontrolsandMusiccomparators.NoOSDynamicType/nativeiOSclaim.
4. `node --test tests/*.test.mjs`→1276pass/0fail;
   `python -m pytest -q tests/test_portal_aura_theme_contracts.py`→0fail;
   reverseinsertion+LFnormalizeCSSBASEequalandprotectedfilesunchanged.
5. DeliveryonlyafteralllocalACpass;nofakeUIorstyle-onlywholeproductPASS.

PROVIDER_CALLS_APP=0;WALLET_MUTATIONS=0;DEPLOY=NO;LIVE_PASS=NOT_TESTED.
GOALACTIVE;languageSearch/Smartduplicate/reportemptyremainB4/C3/D3,
donotfixwithinB3. MotionLAST/runtimejankrequiresseparatefinalevidence.

### QA clarification, no production change

FirstGREENprobe confirmed16px then timedout because harnessusedbrowserBack
to return an in-place tab. ExistingupdateSubDubModeSelection intentionally
usesreplaceState, notpushState. Tabreturn meansselectoriginaltab;browserBack
forVoicecontinuation staysC2locked. FailedrawSDB3-green retained;correctonly
harness and record finalseparately. Do notchangehistorylogicforthistest.
