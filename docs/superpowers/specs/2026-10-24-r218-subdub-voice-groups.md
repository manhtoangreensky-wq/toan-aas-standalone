# E3-GROUP — compact semantic voice groups, all seven choices retained

## Contract / dependency
BASE_SHA=3d5e59dc4303cb0fb50fbf5cd9e59795541945af
ROOT=C:/Users/toann/Documents/Codex/_webapp-r218-voice
BRANCH=webapp-r218-billing-ui-20261022;PR661/Issue664/parent6380189875.
RANGEacceptedLOCALreceipt6381116731:GREEN72+supplement24/Node1281/Python21/
sourceC0I0M0;LCacceptedLOCALreceipt6380807646. BotharelocalnotremoteCIproof.
OwnerSD07:groupDefault/Saved/Add/SmartAuto;allBotchoicesretained/optimizedWeb,
no meaninglessboxes/experimentalcopy/fakecapability. MotionLAST/goalACTIVE.
COMPLEX/SINGLE/oneFlash3.8worker,R1R2maxsameE3-GROUP/noR3.
No childpush;oneE3batchdeliveryafterGROUP/EDIT/READINESS/finalQA.

## READ and one outcome
voiceLaneHtml currently emits flat sevenlabels inonegrid;eachlabel min64px/
border/background/padding11. Groupingmissing(confirmedindependentsourceaudit,
original2026-10-18-r218-subdub-bot-parity-uiux.md SD07).
Target:4borderlessgrouprows/compactlabelrows,all7nativechoicesalwaysvisible,
sameDOMorder/name/values/checkedsingle/draft/callbacks/Voice/sourceCTAguards.
No4newcards/accordion/subtabs/dropdown/hidingradio/newstate/JSkeyboardhandler.

## Allowlist
1.static/portal/portal.js:ONLY33newcopyrows(11keys*3localeobjects) beforeeach
voiceLaneLabel and boundedlocalvoiceLaneHtmlmarkup/data declarations.
Keepoldlanesarray/fullcopykeys/callbackmapandtailsharednote+Voice+Smart+
speaker markup unchanged exceptgroupedfieldsetdatahook.
2.static/portal/portal-theme.css:ONLYscopedgroupCSSbelowbeforeFinalChatmarker.
3.NEWtests/subdub-voice-groups.test.mjs<=240lines,exactly6top-leveltests,
executeactualrenderer,notgrep productiontext. Alloldtestsunchanged.
Docs/evidence/state/TesterbyCodexonly. ProtectedallotherJS/17helpers/
integration/i18n/portal.css/backend/auth/Bot/provider/wallet/PayOS/ENV/
RANGE-LC-B4-C3-D3/Chat/globaltokens/motion. No rename/signature/refactor.

## Exact copy (do not change old full names)
| Newkey | VI | EN | ZH |
|---|---|---|---|
| voiceGroupDefault | Mặc định | Default | 默认音色 |
| voiceGroupSaved | Đã lưu | Saved voices | 已保存 |
| voiceGroupAdd | Thêm giọng | Add voice | 添加音色 |
| voiceGroupAuto | Tự động thông minh | Smart automation | 智能自动 |
| voiceCompactFemale | Nữ | Female | 女声 |
| voiceCompactMale | Nam | Male | 男声 |
| voiceCompactSaved | Thư viện giọng | Voice Library | 音色库 |
| voiceCompactCustom | Giọng tự thêm | Uploaded voice | 自定义音色 |
| voiceCompactAutoTwo | Auto 2 | Auto 2 | 自动双人 |
| voiceCompactAutoMulti | 3–8 người nói | 3–8 speakers | 3–8 位说话人 |
| voiceCompactSmart | Smart Multi | Smart Multi | Smart Multi |

Old7fullvoiceLane*names remaininputaria-labelandreviewmapping. Compacttext
mustbecontainedinfullaccessible name(case-insensitive). No<option>IDs/
providerprofile/preview/count/quote orreadinessbadge fabricated.

## Exact helper data and markup
Retainold `const lanes` array andlaneCallbacksmapbyte-for-byte. Addlocals:
```js
const compactLabels = {
  default_female: copy.voiceCompactFemale, default_male: copy.voiceCompactMale,
  saved_voice: copy.voiceCompactSaved, custom_voice: copy.voiceCompactCustom,
  auto_two: copy.voiceCompactAutoTwo, auto_multi_3_8: copy.voiceCompactAutoMulti,
  smart_multi: copy.voiceCompactSmart
};
const groups = [
  ["default", copy.voiceGroupDefault, lanes.slice(0, 2)],
  ["saved", copy.voiceGroupSaved, lanes.slice(2, 3)],
  ["add", copy.voiceGroupAdd, lanes.slice(3, 4)],
  ["auto", copy.voiceGroupAuto, lanes.slice(4)]
];
```
Outerfieldsetaddboolean `data-subdub-voice-grouped`;keepfieldsetlegend/note
aria-describedby. Replaceonlyflatgrid withgroupsmap. Eachgroupstructure:
```html
<div class="portal-subdub-voice-group" role="group"
 data-subdub-voice-group="GROUPKEY"
 id="subdub-voice-group-GROUPKEY-SUFFIX"
 aria-labelledby="subdub-voice-group-title-GROUPKEY-SUFFIX">
 <p class="portal-subdub-voice-group-title"
 id="subdub-voice-group-title-GROUPKEY-SUFFIX">LOCALIZED_GROUP_TITLE</p>
 <div class="portal-subdub-voice-lane-grid portal-subdub-voice-group-choices">
  SAME_OLD_LABEL_AND_INPUT_WITH_TWO_CHANGES_BELOW
 </div>
</div>
```
Wrapfourgroupsin `<div class="portal-subdub-voice-groups">...`.
For eacholdlane labelkeepclass/is-selected/data-status/data-subdub-voice-lane/
conditionalcallback;inputkeepsname/type/value/data/checked andadds
`aria-label="${safeText(label)}"`. Stronguses `safeText(compactLabels[value])`
insteadfulltext. Valuesgroupkeys/titles/suffixesmustsafeText;suffixdub/combo.
NOT4radiogroups. No focusableheading. Sharednote/link/inerttailstayonceoutside
groupsandunchanged. No <small> instruction per option.

## Exact CSS (feature-specificity protects dark heading)
```css
:root .portal-page.portal-subdub-hub [data-subdub-voice-grouped] .portal-subdub-voice-groups {
  display: grid;
  gap: 12px;
}
:root .portal-page.portal-subdub-hub [data-subdub-voice-grouped] .portal-subdub-voice-group {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  column-gap: 16px;
  row-gap: 4px;
}
:root .portal-page.portal-subdub-hub [data-subdub-voice-grouped] .portal-subdub-voice-group-title {
  flex: 0 1 140px;
  min-width: 0;
  margin: 0;
  padding-block: 12px;
  color: var(--portal-ink);
  font-weight: 700;
  line-height: 1.4;
}
:root .portal-page.portal-subdub-hub [data-subdub-voice-grouped] .portal-subdub-voice-group-choices {
  display: flex;
  flex: 1 1 220px;
  flex-wrap: wrap;
  gap: 8px;
  min-width: 0;
}
:root .portal-page.portal-subdub-hub [data-subdub-voice-grouped] .portal-subdub-voice-lane {
  align-items: center;
  min-width: min-content;
  max-width: 100%;
  min-height: 44px;
  padding: 8px 10px;
  gap: 8px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  box-shadow: none;
}
:root .portal-page.portal-subdub-hub [data-subdub-voice-grouped] .portal-subdub-voice-lane.is-selected {
  background: var(--portal-surface-soft);
  box-shadow: inset 0 0 0 1px var(--portal-action);
}
:root .portal-page.portal-subdub-hub [data-subdub-voice-grouped] .portal-subdub-voice-lane:focus-within {
  outline: 2px solid var(--portal-ink);
  outline-offset: 2px;
}
@media (max-width: 720px) {
  :root .portal-page.portal-subdub-hub [data-subdub-voice-grouped] .portal-subdub-voice-group-title {
    flex-basis: 100%;
    padding-block: 0;
  }
  :root .portal-page.portal-subdub-hub [data-subdub-voice-grouped] [data-subdub-voice-group="auto"] .portal-subdub-voice-group-choices {
    flex-direction: column;
    align-items: stretch;
  }
}
```
Noextraimportant/palette/token/fontfamily/media/motion/globalrules. Existing
inktokenforfocusgivescontrasttarget,notnewhardcodedcolor. Naturalcomponent
wrapworksinsideComboevenwhenviewportdesktop. Text2xmaywrap,nevernowrap/fixedheight.

## New unit behavior (6 tests)
Useactualrendererharnessenvironmentmatchingexistingpresentationtest:
sourceconstSUBDUB_PRODUCT_MODES→beforefunctionrenderDocumentHub, plusactual
subDubVoiceCompanionUrl;newFunctionprovidedwindowlocation/interfaceLocaleFor/
safeText/badge/renderHero/transientFormDrafts. Onlyirrelevanthero/badgestubs.
Do NOTmockgroups/controls/callbacks/review/draft output;assertrealrenderedHTML.
Literalexpectedfullnamesbelowfromoldsource,notcomputedusingSUTcopyhelper.
Fullnamesliteralrequirementsforunit:
| Value | VI full | EN full | ZH full |
|---|---|---|---|
| default_female | Giọng nữ mặc định | Default female voice | 默认女声 |
| default_male | Giọng nam mặc định | Default male voice | 默认男声 |
| saved_voice | Giọng đã lưu trong Thư viện giọng | Saved voice from Voice Library | 音色库中的已保存音色 |
| custom_voice | Giọng tự thêm có xác nhận quyền sử dụng | Uploaded voice with consent | 已确认授权的自定义音色 |
| auto_two | Auto 2 · tự nhận diện hai người nói | Auto 2 · detect two speakers | 自动双人 · 识别两位说话人 |
| auto_multi_3_8 | Auto Multi · tự nhận diện 3–8 người nói | Auto Multi · detect 3–8 speakers | 自动多人 · 识别 3–8 位说话人 |
| smart_multi | Smart Multi · phân bổ nhiều giọng thông minh | Smart Multi · intelligent multi-voice mapping | Smart Multi · 智能分配多人音色 |

1.Fourlocalizedgroups+uniqueheadingIDs/labelledby ineachvoicepanel.
2.Exactmembers2/1/1/3/DOMorder/sameinputname/onechecked;all7fullARIALabels.
3.CompactdisplaylabelscontainmentinfullnameandreviewFULLoldnameforeach7lane
   usingliteralmaps,3locales/twoDubbingmodes.
4.Threecallbackmapunchanged,sharednote/linkonceperpanel,inertSmart/speaker
   retained,sourcefile/CTA stilldisabled.
5.ActiveSUBTITLE_ONLY/TRANSLATED_SUBTITLEpanels have0voicegroups;wholeHTML
   stillhasbothhiddenvoicepanels(8groups/14radios),IDsnotduplicated.
6.Selectedsaved/customdraftwithja/pt-BR/0_200 retainsreview/VoiceURLreturnmode;
   actualrenderedcontextnotmockstateassertions.
ExtractactivepanelHTMLbyactualsectionboundary;don'tmistakehiddenpanelsfor
activevoiceUI. Assertfixtureevaluationerrors normally,nevercatch-and-swallow.
Exactly6top-leveltests/nofakecoverage;<=240lines,oldtestsnochanges.

## Acceptance and ordered evidence
G501:actualbaselineRED36(twoDubbingmodes*VIENZH*lightdark*3203901440);
0semanticgroups/7visiblechoices,oldflatgridheightrecorded;desired4assertfails.
NewunitappliedALONEbeforeproduction;REDforgroup/ARIAabsence,0harnesserrors.
G502:GREENunit6/focused60/fullNode1287/PythonCSS21 ifcountsunchangedelse
reportactual. Alloldtests/protectedcomparatorsunchanged.
G503:actual84voiceconfigs(two modes*3locales*2theme*7views3203753904147681440/
844landscape):4groupsnames/uniqueIDs/7visiblechoices/onechecked/3callbacks/
fullARIA andfullreview;eachlabelclickandnativeArrowRightacrossallwrappers.
84additionalnonvoicepanelcheckshave0visiblevoicechoices.
G504:Default2choiceswhenfit/Auto3rowsphone;no4newgroupcards/choiceborder0/
backgroundtransparentunlessselected;min44labeltarget;contrastnormal>=4.5/
focus>=3andunknown0;actualtext2xwrap/nohiddenchoice/overflow0. For36matched
baselineconfigs,newgroupsheight<oldflatgridheight. Actualscreenshots320390/
desktopboth themesinspected;noimagealonepass.
G505:Mode/VoiceSavedCustomreturn/latesttargetB4/customISO/mix0_200/mute/
draft/review/gates/C3dedupe/D3report/RANGEgeometry/LCassociationsretained.
0appconsole/pageerrors/external/UIwrites;LFresponseassetshashsource.
G506:exactR1records/reverseallowededits/17protectedhelpers/12files/oldtests/
Chat;reviewC0I0/docs/ledger/localcheckpoint,notparentdelivery.
No paidengine/profile/upload/capability/AAglobal/nativeiOS/motion/LIVEclaim.
ParentreadinessUNKNOWNretained;stablechildwaitactualauthenticatedbootstrap
beforeinteraction,notforcedready/bypassedauthbusiness. Nochildpush.

## Root commands / opening next child
node <QA>/browser-SDE3-GROUP.cjs <isolatedorigin> red|green
REDexit1expectedmissing4groups;GREENexit0/84voiceconfigs/0declaredfailures.
node --test tests/subdub-voice-groups.test.mjs ->6pass0failaftertrueRED.
node --test tests/subdub*.test.mjs;node --test tests/*.test.mjs.
python -m pytest -q tests/test_portal_aura_theme_contracts.py.
OnlyafterG501..506localPASS→EDIT(nextoriginalqueue);newUIcopy/READINESS
findingskeptbeforeparentfinal168/Testerdocs/provenance/ONEE3pushCIreceipt.
PROVIDER_CALLS_APP=0;WALLET_MUTATIONS=0;DEPLOY=NO;LIVE_PASS=NOT_TESTED.

## R2 clarification — same E3-GROUP, no production applied

R1handoffFAILED:innerJSONextrabrace/CSSoldmarker0matches/newunitwrongactive
sectionanddraftshape/weakreviewguardassertions. R1raw+reviewretained.
RootSPECgap:packetmustsupplyliteralshared/modesdraftshape,notinferfromharness.

Correctfixture:
```js
{ shared: { voice_lane: lane, target_language: "ja", target_language_custom: "pt-BR",
    original_volume: "0", dubbing_volume: "200" },
  modes: { DUBBING_ONLY: {}, SUBTITLE_PLUS_DUBBING: {} } }
```
Actualquerymodesdubbing_only/subtitle_plus_dubbing;activepaneluppercasekeys.
Extractpanelwithregexsectionopeningdata-subdub-mode-panel=EXACTKEYthenits
closingsection,notfirstsection/notopenTag.includes('hidden')becausearia-hidden
falsecontainswordhidden. No nestedsectionsinsidecurrentpanels;groupdivsokay.
Reviewassertmustextractspan[data-subdub-setting=voice_lane]andcompareexact
literalFULLname,nothtml.includes(full). Sourcefileid/CTAopeningtagsmustboth
haveBOOLEANdisabled,notanyguardedtoken. Selectedtagcheckcheckedattribute
andvaluewithregexnotattributeorderassumption. Unit6mustassertjaSELECTED,
pt-BRinputVALUE,mix0/200DOMreviewanddecodedreturn_toquerymodeexact.
R2keep4R1JSrecordsbyteidentical,fixCSSmarkeractualuniqueFinalChat(fullstring),
complete6testmodule<=240lines/rootfirstapplytestonlyforRED. InnerJSONmust
strictparseasONEobject,notextrabrace/fences/comment. NoR3/counterreset.

## Local acceptance — 24/10/2026, parent/delivery open

R1 transport/new-unit gates failed; R2 output-token-limit truncation failed.
Neither invalid artifact was applied. Sol xhigh repaired packet/new unit only;
four R1 JS records and SPEC CSS body retained exactly. True unit-only RED:
6 tests/2 pass/4 expected assertion failures/0 harness errors, then exact
production packet GREEN6; focused60/fullNode1287/PythonCSS21/compile6 passed.
Independent source/new-unit review C0/I0/M0; reverse whole JS/CSS equals BASE
after LF normalization, 17 helpers/12 files/672 old test paths/Chat unchanged.

Actual signed-browser84 configurations: 588 label clicks/588 native arrows/
168 Voice returns/84 mode round trips; 1008 text+84 focus samples min8.836529,
unknown0; target min75.46875x44, text2x no overflow/hidden choice, 252 LF asset
checks match. All36 matched height comparisons shorter by65.203125–156.359375px.
Supplement84 geometry scenarios closed review gaps: Default two same row in
82 cases that fit; two narrow cases wrap; all48 phone Auto rows stacked.
84 nonvoice checks assert zero visible voice input/label/group across page.
Page/console/external/UIwrites/overflow0. Six useful 320/390/1440 theme crops
inspected. First exact2px focus runner rejected actual3px: QA now checks >=2px
solid and contrast>=3, no app edit or cause claim. Raw failure preserved.
Owned browser/server terminal0, tempDB removed/listener6821=0.

Evidence: `reports/audit/R218-SUBDUB-VOICE-GROUPS-QA-20261024.json`.
G501..G506 local acceptance met; no child push/merge/deploy. E3-EDIT is next;
READINESS/parent final168/Tester/docs/provenance/onepush remain. No broader
SubDub/voice capability/engine/LIVE/motion closure. Goal ACTIVE.
