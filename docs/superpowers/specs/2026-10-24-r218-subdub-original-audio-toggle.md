# SD-D4 — công tắc âm thanh gốc, khôi phục mức vừa dùng

SPEC_ID=SD-D4-ORIGINAL-AUDIO-TOGGLE; HANDOFF_ROUND=2; FAILED_HANDOFFS=2.
BASE_SHA=ba4b2dfa1be096e35198e8bf60f3fa5596ed5af8.
Branch webapp-r218-billing-ui-20261022; PR661; Issue664; COMPLEX/SINGLE.
Dependency E3 ACCEPTED receipt6384081882/CI40092099397bothSUCCESS456records.
Owner: “Duyệt: khôi phục mức vừa dùng”; “Cho phép đúng gói SD-D4 R1 + MAP”.
No worker may receive Bot source/runtime/customer/credential payloads.

## 1. Một kết quả cần đạt

Hai panel Dubbing và Combo có công tắc âm gốc thực sự điều khiển cấu hình local:
tắt→0, nhập/kéo dương→bật, bật lại→mức dương gần nhất trong cùng bản nháp;
nếu chưa có mức nhớ hợp lệ thì100 là default Web hiện tại. Không đổi default
ban đầu, dubbing0–200, ackmute, engine/provider/auth/identity fence hoặc motion.
Bot source đã xác nhận on/off riêng; restore-last là tối ưu Web Owner đã duyệt,
không tuyên bố Bot đang restore-last hoặc fallback30 là giá trị server thật.

## 2. Allowlist và khóa phạm vi

- Production: `static/portal/portal.js` duy nhất, chỉ các điểm ở mục3.
- NEW `tests/subdub-original-audio-toggle.test.mjs`: đúng6test, tối đa240dòng.
- Root giữ docs/checklist/evidence; worker chỉ trả JSON stdout, không ghi file.
- Cấm CSS/i18n bundle/integration/backend/Bot/Multi/engine/provider/wallet/ENV/
  DB/oldtests/Chat/motion/dependency/Git/IDE/browser/login/settings/deploy.
- Không đổi tên/chữ ký/return contract cũ; không refactor monolith để thỏa trần.
- Pure render, capture/apply/snapshot/session-fence, review rows/E607/E608,
  language-search/7voice/3Auto/modes/Voice continuation giữ nguyên whole function,
  trừ đúng exception volume updater/normalizer/Set/renderer/listener ở mục3.

## 3. Đặc tả implementation chính xác

### Copy và native control

Thêm `audioOriginalToggleLabel` ngay trước mỗi `audioOriginalLabel`:
VI `Giữ âm thanh gốc`; EN `Keep original audio`; ZH `保留原始音频`.
Trong `localVolumeControlsHtml`, chỉ `kind === "original"` dựng thêm một label
class `portal-subdub-radio-option`, checkbox native `type="checkbox" role="switch"`,
ID `subdub-original-audio-toggle-${suffix}`, data-subdub-original-audio-toggle.
Label có for đúngID và chứa input, dùng đúng copy; checked khi Number(value)>0.
Không name/value mới tham gia capture, không aria-checked string bị stale,
không card/pill/alert, không thêm dòng review hoặc nút engine/callback giả.
Giữ range/number editable ở0. Label/hit target dùng CSS hiện có, tối thiểu44×44.
Hình thức navy/blue/teal hiện tại, không CSS mới, không animation.

### Nhớ mức dương, không tạo trạng thái bật/tắt thứ hai

Checked luôn suy từ actual original volume, không lưu boolean song song.
Chỉ thêm key `original_volume_restore` vào SUBDUB_SHARED_DRAFT_FIELDS.
Thêm đúng branch normalizer cho key này: primitive string/number, nonempty,
integer1–100 thì trả canonical decimal string; còn lại null. 0 không là mức nhớ.
Các branch cũ giữ nguyên, đặc biệt original0–100/dubbing0–200/ack/dropfields.
Key chỉ là metadata bản nháp trong tab, không localStorage/sessionStorage,
không request, không hiển thị ra review, không có giá trị file/profile/provider.
Snapshot/capture/apply/session clear giữ nguyên; Set/normalizer tự preserve key.

### Một helper mới và route qua volume updater hiện có

Thêm `updateSubDubOriginalAudioToggle(control)` trước volume updater hoặc trước
voice-lane updater; function declaration, không new global cache. Return boolean.
Guard trước mọi write: actual control có closest/getAttribute/hasAttribute;
signed `subDubWorkspaceDraftSession` không rỗng; root `.portal-subdub-hub`
dataset.subdubAuthoringReady === "true"; control không disabled/readOnly;
active panel không hidden, mode chỉ DUBBING_ONLY hoặc SUBTITLE_PLUS_DUBBING;
đủ original number/range và đúng checkbox datahook. Wrong/missing/hidden/
unready/disabled/foreign kind/invalid numeric ->false, không đổi draft/DOM.
Không query document hoặc panel khác làm fallback.

Nếu control là checkbox: lấy last valid positive từ actual range, rồi private
restore, rồi draft original value, rồi100. Khi off, nhớ actual positive nếu có,
đặt cả number/range0; khi on và actualrange0 thì dùng restore hoặc100. Gọi
existing updateSubDubLocalVolume(number) để xử lý output/error/mute và checkbox.
On/Off lặp từ input+change phải idempotent, không reset lần hai về100.

Nếu control là original number/range: chỉ xử lý khi normalize hợp lệ và không
badInput. Checked suy từ actual valid range. Nhớ mức dương mới; nếu vừa thành0
mà chưa có private restore, lấy positive draft trước capture. Không ghi0 hoặc
invalid vào privatekey. Preserve mọi shared/mode key khác, foreign route draft.
Chỉ ghi private key vào sanitized subDubDraftSnapshot rồi transientFormDrafts
cho `/subdub`; không tự tạo session/adopt anonymous draft.

Trong updateSubDubLocalVolume chỉ hai additive hooks, giữ nguyên thân cũ:
1. Sau null guard: nếu có hasAttribute function và hasAttribute togglehook,
   return new helper(control). Không dùng getAttribute !== null để nhận hook:
   legacy typed tests có getAttribute trả cùng một kind cho mọi key.
2. Sau toàn bộ valid pair/output/error/mute/ack xử lý cũ, trước returntrue:
   kindoriginal gọi new helper(volumeInput); nonToggle branch không gọi ngược
   old updater, nên checkbox→number path chỉ reentry một lần, không recursion loop.
   Bỏ qua helperfalse không đổi returntrue/old update behavior của legacy control.

Hai input/change delegates chỉ mở rộng selector volumeInput để gồm original
togglehook. Giữ nguyên old updater→voice updater→capture→summary order/search
earlyreturns và không thêm global helper dependency vào chunk delegates.
Không sửa bind/apply/session/capture bằng nhánh khác hoặc clickhandler mới.
Existing applySubDubDraftDom gọi old updater, nhờ hook checkbox giữ đúng sau mode/
Voice remount. Dubbing không chạy original helper, ack của dubbing không thay.

## 4. Sáu unit behavior tests và RED

Actual renderer block SUBDUB_PRODUCT_MODES→before renderDocumentHub, actual
subDubVoiceCompanionUrl, actual Map/normalizer/updater/capture/apply/session.
Factory two-argument render(page,context), locale/safeText/badge/renderHero stubs
chỉ I/O phụ; context.session signed thật trong unit fixture, không fake runtime.
Đưa Map vào new Function bằng tham số transientFormDrafts, trả Map ở outer scope.
Draft shape `{shared:{...},modes:{DUBBING_ONLY:{},SUBTITLE_PLUS_DUBBING:{}}}`.
No swallowed eval errors; use existing updater as entrypoint so BASE assertion
RED không thành ReferenceError gọi helper chưa có. Expectations literal độc lập.

1. Actual renderer:12mode/localeviews, chỉ2Dubpanels có đúng2unique native switch,
   associated label/role/checked0vs37; readyenabled/unreadydisabled; oldguards giữ.
2. Actual updater checkbox:37→off0/private37→on37; double input/change idempotent;
   missing/invalidrestore fallback100; pairs/output/review đồng bộ, không request.
3. Manual original range/number:37→0→on37,1/100, invalid giữ lastvalid/flag/key;
   apply/hydrate old updater cũng sync checkbox; không ảnh hưởng dubbing.
4. Private normalizer/snapshot/capture:1/37/100 valid,0/101/empty/NaN/float/bool
   invalid; old keys exact; signed same retains, account change/logout clears.
5. Actual apply + two panel draft lifecycle:muted và remembered37 qua mode/return
   reconstruction vẫn0/off; on37; unrelated route/target/voice/subtitle keys giữ.
6. Actual delegated input/change chunk với actual volume/capture/summary functions,
   typed DOM đúng selector; switch toggles before capture/review, original0
   never touches dubbing0/acktrue hoặc200; pending/disabled/hidden no privatewrite.

NEW_TEST only applied first: `node --test tests/subdub-original-audio-toggle.test.mjs`
must assertionRED with0harness; then only approved production records, GREEN6.
Do not edit old tests to make candidate pass. Report actual counts, not guesses.

## 5. Runtime/regression acceptance

Root runs focusedSubDub expected80/fullNode expected1307 if unrelated countstable;
PythonCSS21/portableTester32+1WindowsPOSIXdeselected/syntaxcompile/diff0.
Signed isolated QA: twoDub×VIENZH×lightdark×390/768/1440/844landscape=48cases.
Click/Space/off/on/manual0/1/37/100/invalid/review/2modeLoops/Voice saved+custom
returns while muted, thenon restores37; dubbing200 and0+ack remain independent.
Supplement both nonvoice modes×3locale×2theme×390/1440=24, global visible switch0.
Pending held-actual-response12:0enabled switches before signedready; ready then
normal behavior. Exact assets, labels/AX,44target,contrast>=4.5/focus>=3/unknown0,
text2x geometry/errors/external/UIwrites/overflow0. No forceclick/fake session.
Unit fences plus actual account replacement/logout clear private restore.
No full-pageWCAG/nativeSafari/iOS/PWA/motion/performance/engineoutput claim.

## 6. Protected comparisons, handoff and delivery

Base has19pre-render SubDubhelpers;17remainwhole-exact,with2declaredexceptions:
oldvolumeupdater twoadditivehooks andnormalizer privatekeybranch only.
Set adds only1key, renderer adds only copy/switch.
Two delegate selectors widened only. All oldtests/Chat CSS+functions/API/auth/
integration/backend/mainSFX5files/motion byte-exact. No signaturerename/refactor.
Consumer grep: production onlyportal.js; external matches are3testharness files,
normalizer only1testfile; no external production import/consumer to alter.

One workerFlash3.8 R1/R2max same SPEC_ID; aftertwofailedgates Solxhigh narrowtakeover,
noR3. Source-only JSON NEW_TEST/PRODUCTION_EDITS/REPORT; no tool/file/Git/browser/
network/settings work byworker. Root applies/tests/reviews; no workerPASS claim.
AfterallAC: independent review/Tester/currentdocs/crosswalk/provenance/onebatch
push/exactHEADCI/receipt. No merge/deploy or otherproduct/technical scope.
Con số lệch→LỆCH; không chạy→NOT_RUN; cấm tự suy ĐẠT.
PROVIDER_CALLS_APP=0;WALLET_MUTATIONS=0;DEPLOY=NO;LIVE_PASS=NOT_TESTED;
GOAL=ACTIVE;MOTION=LAST.

## R1 gate result và R2 correction contract — chưa áp dụng production

R1outerSUCCESS423.7250344s nhưnghandoffFAILED:6newtests271lines>240;
BASE0pass6assert0harness/candidate4pass2assert0harness. TestIDs sai suffix và
DOMclosestkhôngmatchcombinedselector;khôngsửa appđểkhớptest sai.
ActualbrowserRED48/48thiếuswitch/errors0/raw874aa00d…111723.
Rootguardprobes trênactualcandidate:foreigncheckboxclone/invalidrange vẫn được
helperchấpnhậntruevàghiDOM/draft,vi phạmfence trướcwrite. Chưaapplysource/test.

R2sameSPEC_ID/HANDOFF_ROUND2/FAILED_HANDOFFS1. Chỉrecordindex6helperguards+
NEW_TESTđượcsửa;8recordcòn lại frozen byteSHA
e77b67326848bf2f8dec02460309313e0f3758406124d36534928cbda58940d7.
Oldvolumeupdater+twohooks trongrecord6 phải nguyênbyte soR1;khôngthêmCSS.

Guardnewhelper bổ sungtrước mọiwrite:

- panel cógetAttribute/querySelector functions;rangetype range/numbertype number/
  toggle typecheckbox;counterparts nằm đúngpanel,khôngdisabled/readOnly.
- Checkboxhook control phải chính `toggleCheckbox`,typecheckbox;foreign clone
  cóhook/closest giống nhau vẫnfalse,khôngghi trạngthái hayprivatekey.
- Branchcheckbox kiểm normalize actualrange vàrange.validity.badInput;
  null/invalidrange ->false trước setvalue/checked/draft. No fallback100đểnuốt
  range invalid. Canonical0 là hợp lệ vàđượcbật thànhrestore/default100.
- Nonnumericcontrol hoặcoriginalkind sai/khôngphảinumber/rangepanel actual
  false;legacyoldtypedfixtureskhôngcóroot/toggle vẫnold updaterreturn behavior.
- Numericinvalid quaold updatervẫnđượcsetaria-invalid/showerror nhưcũ;
  chỉ cấm mới private/value/checked mutationngoàifailclosedhelper.

R2newtestgọn<=240lines6tests;fixturefactorydùnghelpercontrolchung giảmboilerplate,
khônggộpmachine-longlineđểnétrần. Actualrenderer12mode/localeviewsđúngquery,
rootreadyfalse/true;IDs `subdub-original-audio-toggle-dub` và`...-combo`.
Label là `<label for=...><input ...> text</label>`,khôngregexmongtextngaysau`>`
củalabel. Capture actualtag attributes/labelbody,validtwoinputids7voicelanes.

DOMclosestphảihỗtrợEXACTcombineddelegateselectorplusstandaloneroot/panel/
voice/searchselect;unknownselectorthrow. Actualsummarydoublephảiđủrowsregion/
selectedmode/getAttribute(lang),capturestage1/panels/controls,notnulltohideI/O.
Mapstate assertions sauactualcalls,notoldobject reference;independentexpected
restore37/zero/acktrue/dub200/unchangedforeignroute. Fullinvalidcontexts,foreign
identity/invalidrange/disabledcounterparts/hidden/unready/logout guardsprobed.
NEWTEST-onlyactualREDbeforeproduction vẫnrootgatebắtbuộc. R2fail→Solxhigh,
khôngR3/counterreset/sourceexpansion.

## Checkpoint implementation — 24/10/2026

R2 production proposal C0/I0/M0, newunit failed245lines/4harnesserrors.
Same-counter Solxhigh repaired NEW_TEST only,215lines6tests;all9production
records frozenSHA3b9dacc9a8495e7f2b52ed2aff996eff1a6d703707551b55c347531974c6a574.
Actual NEW_TEST-only RED6assert/0harness/exit1/175.6253ms before source;
then exact9records applied, GREEN6/exit0/281.8306ms. Focused80/0/1771.1795ms;
fullNode1307/0/15350.8214ms;isolatedPython85/1deselected/2existingwarnings3.98s,
externalconnect0/localIPC36/tempremoved. Syntax/compile6/diff exit0.

QA first run stopped at raw URL equality after Voice return; actual locked
safeReturnPath allows only /subdub?mode=finiteMode, adds locale, not theme.
This was QA expectation, not SD-D4 source bug. Corrected comparator keeps
rawURLexact on mode roundtrip and canonicalmode+locale URLexact on Voice return;
actual theme/locale/allcontrols/review remain full snapshot comparators.
First failure rawSDD4-green-1792851549843 preserved. FreshQA48+42 running;
independent review/Tester/delivery still open. No runtime or LIVE PASS yet.

LATEST actual48terminalPASS/rawd48beec7…275780;96VoiceReturns48modeLoops,
48text2xgeometry/192assetchecks/labelmin270x44/text12.351554/focus5.860080,
allstrictcounters0. Supplement42terminalPASS/raw5167f89c…72844/24nonvoice+
12pending+6realaccountfences/168assets;exactGETauth/me4016afterlogouteach1,
response+consoleURL/messagecaptured/othersnotignored,unexpectederrors0.
Accountcasespaced31s respectsregister4/login8per60s;authrateunchanged.
Allownedbrowser/serverterminal0;26271/48150/58023notlistening/3QAtempsremoved.
IndependentcodereviewC0I0M0/exact9records/17helpers/676oldtests,ownunit6/gate0.
IndependentTester anddelivery remainOPEN;noLIVE/engine/full21claim.
