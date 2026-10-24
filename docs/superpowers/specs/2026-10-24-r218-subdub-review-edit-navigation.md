# E3-EDIT — edit an actual setting directly from review

## 1. Identity and dependency

SPEC_ID=E3-EDIT;HANDOFF_ROUND=1;SAME_DEFECT_FAILED_HANDOFFS=0;
ESCALATION=NONE;COMPLEX/SINGLE;BATCH=SD-E3-FINAL-UI.
ROOT=C:/Users/toann/Documents/Codex/_webapp-r218-voice
BASE_SHA=c5f09f2ee68e822ea56e2c4cb652731405e48753
BRANCH=webapp-r218-billing-ui-20261022;PR661;TRACKER=Issue664.
Owner: "tiếp tục xử lý triệt để theo thứ tự"; original SD18 "Sửa ngay nhóm liên quan".
GROUP local accepted receipt6381890971:84 configs+84geometry+84nonvoice;
Node1287/Python21/sourceandsupplementC0I0M0. No childpush/merge/deploy.
Next READINESS, then final168/Tester/docs/provenance/ONEE3push/exactHEADCI.
Motion LAST, goal ACTIVE; original AX/early-input unknowns remain open.

## 2. One outcome / READ / impact

Current renderSubDubSettingsRows emits key/value spans only; mode summary
also has no action. Existing controls and local draft already work; user must
manually find the setting again. Add small literal Edit actions only beside
editable values. No new instructional box/card/toolbar/modal, no hidden choices.
Buttons focus the actual active setting; native focus scrolls it into view.
Do not change mode/value/draft/URL, remount, clear language search, dispatch an
API action, or add animation/smooth scrolling. Edit mode focuses selected tab;
customer changes mode explicitly with existing controls.

Impact scan2026-10-24:
`git grep -n -i -E 'renderSubDubSettingsRows|subdub-settings-rows|data-subdub-setting' -- static tests`
Production:portal.js27045 definition/27073 rowmap/27077 container/27082 update/
27489 region/27490 render. No production consumer outside portal.js.
Existing tests:subdub-hub-presentation181,197,198,238,262,263;
subdub-review-volume-controls27;subdub-semantics-a11y26..30;
subdub-voice-groups80. These four old tests remain unchanged. Separate scan
updateSubDubSettingsSummary finds one definition/four calls in same source;
two test references in subdub-language-search170,224. No rename/signature change.

## 3. Allowed and protected files

1. static/portal/portal.js:three locale rows;bounded rowmap-only change;
   one new focusSubDubReviewSetting helper before updateSubDubSettingsSummary;
   one mode summary row edit button;two delegated-click lines before mode button.
2. static/portal/portal-theme.css:scoped CSS in section below before unique
   `/* Final light AI Chat Workspace surface */` marker, keeping marker.
3. NEW tests/subdub-review-edit-navigation.test.mjs <=220lines,6top-leveltests.
MAX_FILES_CHANGED=3 production/test. Root alone updates docs/checklist/evidence.
Protected:all old row data/full voice names/settings spans, all17 old SubDub
helpers, all old tests, integration.js/i18n/portal.css/backend/auth/Bot/route-
engine/provider/wallet/PayOS/ENV/DB/Chat/globaltokens/motion. No package/refactor.

## 4. Exact UI and implementation contract

Add `summaryEditAction` just before summarySettingsTitle in each locale:
VI `Sửa`; EN `Edit`; ZH `修改`.
New editable key set inside renderSubDubSettingsRows, before return:
source_subtitle_state,target_language,target_language_custom,voice_lane,
original_volume,dubbing_volume,subtitle_position,output_format,subtitle_format,
sub_display_type. Existing mode-dependent rows remain exactly as before.
Keep existing spans byte-for-byte; for editable keys append:
```html
<button class="portal-subdub-review-edit" type="button"
 data-subdub-review-edit="KEY" aria-label="EDIT: LABEL">EDIT</button>
```
safeText(key),safeText(copy.summaryEditAction+": "+label),safeText(action).
Only editable row wrapper adds class `portal-subdub-review-edit-row` alongside
existing portal-summary-item. source_file/source_language have no action and
unchanged wrappers. No empty third-cell/disabled Edit placeholders.
Mode summary wrapper also adds row class and appends button with key `mode`,
ARIA label EDIT+": "+copy.summaryModeKey. Existing data-subdub-summary-mode
span and all price/cost/balance/guard/report markup remain unchanged.

New focusSubDubReviewSetting(button):
- Return false for null/missing closest, non-.portal-subdub-hub, unsupported key,
  missing selected mode, invalid mode key, missing/hidden/aria-hidden active
  panel, missing/disabled/:disabled target or missing focus function.
- Root from button.closest('.portal-subdub-hub'); selected mode from existing
  `[data-subdub-mode-select][aria-selected="true"]`; validate Object.hasOwn
  SUBDUB_PRODUCT_MODES before using mode to locate panel. No arbitrary selector
  value from button key; explicit constant selector map only.
- Key mode -> selected mode button.
- source_subtitle_state -> root stage1 checked input[name="subdub-subtitle-source-state"].
- All other keys -> validated active panel only, never hidden sibling:
  target_language:select[name="target_language"];
  target_language_custom:input[name="target_language_custom"];
  voice_lane:[data-subdub-voice-lane-input]:checked;
  original_volume:input[type="number"][data-subdub-local-volume="original"];
  dubbing_volume:input[type="number"][data-subdub-local-volume="dubbing"];
  subtitle_position:input[name^="subdub_"][name$="_subtitle_position"]:checked;
  output_format:input[name$="-output-format"]:checked;
  subtitle_format:select[name="subtitle_format"];
  sub_display_type:select[name="sub_display_type"],input[name="sub_display_type"]:checked.
- target.focus() then return true. No focus({preventScroll:true}), scrollIntoView,
  state writes, dispatch, capture/apply/update, history, timers or new listeners.
Delegated click before existing subDubModeButton:
```js
const subDubReviewEdit = event.target.closest(".portal-subdub-hub [data-subdub-review-edit]");
if (focusSubDubReviewSetting(subDubReviewEdit)) { event.preventDefault(); return; }
```
Do not modify any existing line in old mode/Voice/input/change/keydown handlers.

Exact CSS, no other styling or motion:
```css
:root .portal-page.portal-subdub-hub .portal-subdub-review-edit-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.4fr) auto;
  align-items: center;
  gap: 8px;
}
:root .portal-page.portal-subdub-hub .portal-subdub-review-edit {
  min-width: 44px;
  min-height: 44px;
  padding: 8px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--portal-ink);
  font: inherit;
  font-size: 13px;
  line-height: 1.4;
  text-decoration: underline;
  cursor: pointer;
}
:root .portal-page.portal-subdub-hub .portal-subdub-review-edit:focus-visible {
  outline: 2px solid var(--portal-ink);
  outline-offset: 2px;
}
@media (max-width: 480px) {
  :root .portal-page.portal-subdub-hub .portal-subdub-review-edit-row {
    grid-template-columns: minmax(0, 1fr) auto;
  }
  :root .portal-page.portal-subdub-hub .portal-subdub-review-edit-row > .portal-summary-key,
  :root .portal-page.portal-subdub-hub .portal-subdub-review-edit-row > .portal-summary-value {
    grid-column: 1;
    text-align: left;
  }
  :root .portal-page.portal-subdub-hub .portal-subdub-review-edit {
    grid-column: 2;
    grid-row: 1 / span 2;
  }
}
```

## 5. Ordered small steps / new unit / RED

One worker, tasks2–5minutes each, gate shared:
1. New test artifact only: actual renderer block constSUBDUB_PRODUCT_MODES to
   before renderDocumentHub plus actual companion helper; no catch-and-swallow.
   Production test doubles only irrelevant hero/badge/windowlocation/locale/
   safeText/transient map, never review rows/actions/state. Existing GROUP unit
   harness40..48 is complete reference; root supplies it in packet.
2. Six behavior tests: localized actionable rows4modes3locales; readonly file/
   source-language no Edit and mode action present; exact active scope mapping
   all10keys+mode with focus on real helper and guarded negatives; checked
   radio/zero-volume preserve values and no writes; no action in nonexistent
   mode rows and customISO conditional row; escaped labels/copy and unchanged
   settings text/full names/draft/review. Literal expected keysets; no source
   grep/mirrored expectations/framework-only test. DOM doubles must implement
   exact query selectors, closest/getAttribute/matches(:disabled)/focus and
   throw unexpected selector; do not mock the helper or its decision.
3. Production edits as exact old/new replacement records; no whole-source file.
   Root first applies NEWTEST only -> expected assertion RED, zero harness
   errors; then exact production records -> six GREEN and regressions.
No evaluation errors hidden to manufacture expected RED; typeof missinghelper
can be asserted explicitly as absent behavior, not swallowed ReferenceError.

## 6. Acceptance checklist / observable evidence

E601:actualbaseline24configs=4modes*VIENZH*lightdark*390px,zero Edit buttons
confirmed;desiredactionassertionexit1. Test-onlyREDbefore anyproduction.
E602:actual renderer/helper unit6/focusedSubDub66/fullNode1293 expected if
no unrelated count changes;PythonCSS21/syntaxcompile6/diff0. Report actual.
E603:actualsigned168configs=4modes*VIENZH*lightdark*7views3203753904147681440/
844landscape. Every visible Edit button click, keyboard Enter/Space selected
subset; exact real focus value/field and visible viewport/scroll container.
Before/after same mode,draft,controls,URL,DOM root instance,no new requests;
edit disabled targets must fail closed and not focus hidden controls.
E604:button targets>=44x44/textcontrast>=4.5/focus>=3/unknown0;rowtextnot
overlap/clip/overflow,2xtext wrap;desktop/phone both themes inspected.
E605:change target/customISO/voice/mix0_200/subtitle formats-position-display/
source state through Edit and assert review updates; mode and saved/custom
Voice return retains latest settings;LC/RANGE/GROUP/B4/C3/D3 gates preserved.
AssetsLFmatch;page/console/external/UIwrites0. Setup authwrites are isolated.
E606:independentreview C0I0,exactpacket/reverseallowlist,17oldhelpers/12files/
alloldtests/Chatunchanged;docs/master/state/localcheckpointandreceipt.
NoLIVE/upload/audio/engine/fullpageWCAG/nativeSafari/OStextscale/motionclaim.

Root verify:node --test tests/subdub-review-edit-navigation.test.mjs ->6pass0fail;
node --test tests/subdub*.test.mjs;node --test tests/*.test.mjs;
Python pytest -q tests/test_portal_aura_theme_contracts.py;compile6.
Browser command:node <QA>/browser-SDE3-EDIT.cjs <isolatedorigin> red|green.
WorkerVERIFY=NOT_RUN;Con số lệch ->LỆCH;khôngchạyđược->NOT_RUN;cấmtựsuyĐẠT.

## 7. Safety, memory, delivery gates

Only stdout artifacts; no worker tools/files/terminal/Git/network/browser/IDE/
login/logout/settings changes; source-only allowlist to authorized Gemini.
No ENV/secret/customer/runtimepayloads/DB/provider/payment/production.
R1 then sameID/R2max then Solxhigh narrow takeover/noR3/no counter reset.
2026-10-24GROUP:invalid JSON/tokenlimit preventedapply;outputonlynarrowrecords,
not fullfiles;keep output concise enough and validONEJSON with no fences.
2026-10-24LC:theme cascade needs strong scoped selector;no!important/newtoken.
2026-10-24READINESS:stable-auth child waits actualbootstrap,notforcedready;
original early-input/AX UNKNOWN remains separate and must not be hidden.

Before eventualE3push:review currentoperatingdocs+originalSD01..21comparison;
independentTesterprojectready+result;currentmaster no lost requirement;then
onepush `github` (origin is local bundle),exactHEADCI andreceipt. Nochildpush.
PROVIDER_CALLS_APP=0;WALLET_MUTATIONS=0;DEPLOY=NO;LIVE_PASS=NOT_TESTED.
Stop affectedaction on SHA/branch drift,outsideallowlist,secret,failedgate,
another worker,or need for protecteddomain change. No expansion from urgency.

## Contract clarification before any source application — same E3-EDIT

Independent contract review C0/I1/M1 found ROOT_SPEC defects, not worker code:
1. subtitlePositionHtml emits SELECT in all three subtitle modes, not radios.
   Effective subtitle_position mapping supersedes section4 input selector:
   `select[name^="subdub_"][name$="_subtitle_position"]` in active panel,
   without :checked. New test fixture must represent literal actual SELECT;
   a mock accepting the wrong input selector must not manufacture success.
2. renderSubDubSettingsRows is one of previous17helpers. Effective comparator
   protects16wholehelpers plus its exact row-building prefix/mode conditions/
   fullnames/existing spans; ONLY allowed edit-set+rowmap may change. Do not
   claim all17wholehelpers unchanged after an intentional rowmap change.
No production EDIT code applied while R1 stdout worker is running. Preserve
R1 artifact, classify these as SPEC_GAP, sameID/R2if correction needed, noR3.
All other selectors/keysets were source-verified; scope/authority unchanged.

## R2 repair gate — same E3-EDIT, R1 not applied

R1SUCCESS390.3542173s/1turn/strict8records, but independentC0/I2/M1:
wrong `data-subdub-panel` lookup blocks all new actions; actual panel selector
is `[data-subdub-mode-panel="${selectedMode}"]`. Source state must include
stage1 selector above. Newunit230trimEnd/231splitlines>220; wrong modequeries,
mirrored wrong panel/control types, insufficient exact keyset and state proof.
Neither NEW_TEST nor production from R1 applied. R2 must preserve all other
seven R1 production records byte-identical; return only corrected helper/map
record NEW plus NEW_TEST full module<=220lines/exactly6tests and report.
Root assembles original8records replacing only helper new-string. R2 doesn't
change original anchor or accepted other records. NoR3/counterreset.

Literal mode/query pairs:
SUBTITLE_ONLY/subtitle_only;TRANSLATED_SUBTITLE/translated_subtitle;
DUBBING_ONLY/dubbing_only;SUBTITLE_PLUS_DUBBING/subtitle_plus_dubbing.
Literal action sets excluding separate mode:
- SUBTITLE_ONLY:source_subtitle_state,subtitle_position,output_format,subtitle_format.
- TRANSLATED_SUBTITLE:source_subtitle_state,target_language,subtitle_position,output_format,sub_display_type.
- DUBBING_ONLY:source_subtitle_state,target_language,voice_lane,original_volume,dubbing_volume.
- SUBTITLE_PLUS_DUBBING:Dub set +subtitle_position,output_format,sub_display_type.
target_language_custom only nonempty and non-SUBTITLE_ONLY; use validja+pt-BR.
Mode action always present. No custom target select option exists.

Tests must execute actual helper with per-mode actual typed controls; correct
source stage1 and active-panel attributes/selectors, missing-mode fields null,
inactive sibling sentinel never focused. Cover missingpanel/target/selectedmode,
invalidkey/mode,hidden/aria-hiddenpanel,own/inheriteddisabled,missingfocus.
Invoke helper before comparing selectedradio/value0_200/draft/root-state;
checking untouched input fixture without helper call is not preservation proof.
For escaping, provide hostile action/label copy on a fresh evaluated renderer
instance (return SUBDUB_PRESENTATION_COPY in test factory if needed), assert
literal encoded aria/text plus exact normal fullvoice/ISO/0_200 review spans.
Do not weaken old tests, invent private APIs, catch eval errors or assert only
source inclusion. Six named tests, complete fixture, concise<=220lines.

## E607 runtime correction — same spec/round after actual browser failure

Exact8Solrecords applied only after actualunitRED0pass6assertions0harness;
GREEN6/focused66/fullNode1293/PythonCSS21. Browserthenfound real blur→change→
no-opsummaryreplacement removing pressedEdit beforeclick. Confirmed rawtrace:
mousedownconnected→ISOchange→reviewmutation1/disconnect→mouseup/no click;
reviewHTML identical,ISOko-KR/authtrue/CSRFpresent,focusBODY/desiredexit1.
Not an authbusiness or retainedREADINESSrootcause diagnosis.
Boundedamendment `_giao-viec/AMENDMENT-42-SDE3-EDIT-BLUR.md` adds E607:
permit ONLY same-HTML guard in updateSubDubSettingsSummary with element-local
last-generatedHTML property. No global/storage/identity/API/history/motion.
Preserveall8records andsixexistingnewtestbodies;extendnewtestfactory+append7th
behavior test<=220total;actual6GREEN+1RED beforeguard,7GREENafter.
Protect15wholehelpers+two bounded exceptions,oldtests/12files/Chatunchanged.
NoAGYR3/counterreset/newSPEC;sameSolxhigh takeover. Full168mustretest without
QAforcingblurbeforeeachclick or weakeningfocus/draft/DOM/request assertions.

## E608 focus visibility — same spec/round, no motion tuning

NativefocusprovedcorrectyetpositionSELECTunderstickyheader;actual15actions
at320/375/390 showpositiontargety~0/header65/uncoveredfalse. Scopedamendment
`_giao-viec/AMENDMENT-42-SDE3-EDIT-VISIBILITY.md` allowsONLYnativeinstant
center scroll onvalidtargetafterfocus,optionalmethodcheck;noCSS/shell/motion
oroldhelperchange. Append8thnewunit<=240total/previous7exact;current9RED7+1
beforetenthrecord,then8GREEN/15actionprobe/full168 unchangedstrictchecks.
Original8+E607recordsimmutable;noAGYR3/reset/newSPEC. GoalACTIVE,motionLAST.

## Local acceptance — E601..E608, delivery/parent still open

Actual initial RED24missing24;newunit-onlyRED0pass6assert0harness before8records.
E607actualRED6pass1assert0harness→guard7GREEN/blurprobeGREEN. E608actualRED7pass
1assert0harness→tenthrecord8GREEN/15actualactionsuncovered. Original7newtest
bodies unchanged/newunit232lines<=240. Source/currentunit exactly10records,
reversewholeJSCSSBASELF,15wholehelpers12files673oldtestpaths/Chatunchanged;
rootandindependentcomparator0/sourceC0I0M0. No AGYR3/counterreset.

Final actual signed168configs/1218Editclicks/336EnterSpace/1050actualedits
reviewupdates/168modeRoundTrips/168VoiceReturns;URL/mode/draft/rootidentity/
requestcountunchangedperEdit;disabledtargetsretainEditfocus;targetcenterhit
uncovered/no hiddencontrol. Targets44x44,1218textmin12.35155/336focusmin5.86008,
unknown0,2xgeometrynooverlapclipoverflow;504LFassets matchsource/errors-external-
UIwrites-overflow0. Finalbrowser83515exit0. Node1295/20.6354979s/focused68/
2297.8798ms/unit8/181.1246ms/PythonCSS21/1.19s/syntaxcompile6diff0.
Ownedserver68259exit0/tempremoved/listener57350=0. FullpytestNOT_RUN/T0unchanged.

Evidence `reports/audit/R218-SUBDUB-REVIEW-EDIT-QA-20261024.json` records all
failedrounds/runtimefailures/amendments/QAcorrections and hash provenance.
Visibilityprobe reusedfolderoverwrotefirstREDraw/screenshots;do not mislabel
currentGREENraw asoldRED. Originalbaseline terminal+separatefullmatrixfailure
remain;actualnewunit8REDandstrictfinal168provide independentboundedproof.
OriginalC3AX/LCearlyinputUNKNOWNstillE3-READINESS,notclosedbytheseUIbugs.
NextREADINESSformalcontract;thenparentfinal168/Tester/docs/provenance/onepush.
Nochildpush/merge/deploy/providerwallet/LIVE/motioncompletionclaim.
