# MU-NATIVE-ERROR-FOCUS-D0 — phục hồi focus sau lỗi hai form

23/10/2026, LOCAL_UI_ACCEPTED_DELIVERY_PENDING. Contract lưu trước BUILD.
Một dependency để B04 đạt, không resetB
haihandoff. RootC:/Users/toann/Documents/Codex/_webapp-r218-voice;
branchwebapp-r218-billing-ui-20261022;PR661/Issue664;
GitBASEfc8deb6a96566021a58cdcdf8ab77ed6796539cd.
BoverlayintegrationSHA2560a737c3e1d0755d7a8259350b059c37ec19ed4ee9631815b01f5d58989e2f9fa.
Owner “tiếp tục”; UI/UX trước,motioncuối;Flash3.8nền,noIDE/login/settings.

## Bằng chứng và kết quả duy nhất

ActualsignedQA51738/390dark: focus BUTTON→BODY khi gửi(disabled)→BODY khi
lỗi(reenabled). BASEfc8deb6 và Bcandidate giống hệt. Comparator dùng JS-source
overlay riêng từngrevision, API nativePOSTabort thật; khôngAPIresponsefixture.
`../qa/r218-music-sfx-errors-20261023/focus-comparator.json`. Bcopy24/24,
53focused/1006full/21Python không được dùng để tickfocus. Đây là baselinebug
riêng, không do dịchcopy. B04 giữ mở cho tới D0 có strictbrowserPASS.

Khách gửi bằng nút, khi request bị lỗi mà chưa chuyển đi nơi khác, focus phải
trở về chính nút gửi đã được bật lại. Không giành focus khỏi input khác, không
focus target đã bị tháo, không dùng request muộn/sai route/epoch, không đụng
success/copyrightguard merge hoặc native navigation.

## Phạm vi/thiết kế cố định

Chỉ2filesBuilder:static/portal/integration.js trong đúng2nativeaction,
tests/music-sfx-error-focus.test.mjs mới. Khônghelperchung/CSS/portal.js/
i18n/payload/safety/API/auth/provider/wallet/Bot/motion. Existingtests giữ nguyên.
Codex quản lý spec/checklist/master/state/evidence/Tester. Không newDOM/control.

Trong từngblock Music vàSFX, sau payload và trước requestepoch:

```javascript
const composeFocusTarget = window.document && window.document.activeElement;
const restoreComposeFocusTarget = composeFocusTarget && typeof composeFocusTarget.matches === "function" && composeFocusTarget.matches('EXACT_SELECTOR') ? composeFocusTarget : null;
let restoreComposeFocus = false;
```

EXACT_SELECTORMusic:
`form[data-portal-action="music-direction-preset-compose"][data-portal-route="/media-workspace/music-directions"] [data-music-direction-submit]`.
SFX:
`form[data-portal-action="sfx-cue-sheet-compose"][data-portal-route="/media-workspace/sfx-cue-sheet"] [data-sfx-cue-sheet-submit]`.
Usewindow.documentguard so extractedoldVMharnesses do not gain a new global
document dependency. Browserdocument/source selectors remain exact.

Trong catch, chỉnhánh `if (!guarded || !STRICT_GUARD_HELPER(...))` đặt
`restoreComposeFocus = true;` trướcinlinefeedback rồi rethrow như cũ.
Trong finally, ở **bên trong** existing route/request/pendingepochguard,
ngay sau `setActionBusy(action, route, false);`:

```javascript
if (restoreComposeFocus && restoreComposeFocusTarget && restoreComposeFocusTarget.isConnected && window.document.activeElement === window.document.body) restoreComposeFocusTarget.focus({ preventScroll: true });
```

Không focusởsuccess/validguard; không chỉnhcopy,Bhelper,validator,fields,
pendingstatus/requestepochs,CSRF/body/state. Phải giữ tất cả statement ngoài
capture3lines/flag1line/restore1line mỗiaction byteequalBoverlay.

## Testfirst và bước2–5phút

1. Viết test thật2actionblocks+catalogue Bhelper khôngcần dịch lại. Extract
Music→SFX→music-prompt-compose markers, normalizeCRLF bằngchar13; khôngbroad
functionrange. SimulateDOMbutton/body/othercontrol và focus spy. Busytrue làm
activeElementbody (nativeobserved); APIfailurethenexpectfocuscall1/preventScroll.
Payload/strictguardvalidation doubles chỉ cho focuscontrolflow; khôngfullDTOclaim.
2. Baseline phải REDassertionfocuscall0, khôngRefError doepoch/route/caps.
Exact4epochvars,route/media-workspace/...,base.capabilitiesstricttrue.
3. Áp đúng10logicalfocuslines/2actions như thiết kế; no otherstatementchange.
4. Codex realQA strictfocus24configs + nonsteal tests, fullregression/docdelivery.

## Acceptance/checklist

- [x] READbaseline/candidateactualfocus comparator chứng minh lỗi cũ; B04giữmở.
- [x] F01 focusflowtest RED→GREEN cho2tools; correctpriorbutton/error/current
route/epoch/connected/BODY→focus1preventScroll; khôngsuccess/validguardrestore.
- [x] F02 otheractiveinput/notpriorbutton/disconnected/staleepoch/wrongroute
khôngfocus; khônggiànhfocus user hoặc thêmimplicitPOST/merge/navigation.
- [x] F03 only capture/flag/restore; allBcopy/15validators/API/10files unchanged;
existing53focused+MusicLibrary18/fullNode1006/Python21 giữ xanh.
- [x] F04 signedQA24 VI/EN/ZH×light/dark×390/1440 strictpriorbuttonfocus sau
intentionalPOSTabort,localvalidation0POST,retrynative3results,0unexpectederrors/
external/unapprovedwrite/overflow. Expectednetworkfaults ghi riêng.
- [ ] F05 review/docs/Tester/prepush/provenance/push/readback/newCI/Issue664receipt;
chỉ sau đó tick B và D0, khôngwholeMusic/audio/LIVE.

VerifyCodex: `node --test tests/music-sfx-error-focus.test.mjs` REDthenGREEN;
`node --test --test-concurrency=2 tests/*.test.mjs`; Python4native/portal21;
QAcommand `node ../qa/r218-music-sfx-errors-20261023/browser.cjs http://127.0.0.1:51738 green require-focus`.

OneFlash3.8worker,round1/2max,sameF01,nothirdround. Source/test/ticket/MAP only,
stdoutJSON only,no tool/Git/terminal/browser/network/filewrite/ENVsettings.
PROVIDER_CALLS_APP=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_MUTATIONS=0;
DEPLOY=NO;LIVE_PASS=NOT_TESTED;GOAL=ACTIVE;MOTION=LAST.

## Kết quả đo

R1Flash3.8Low75.719576s/test197lines/source10logicalfocuslines; testcleanRED
1pass1fail nhưngthiếuepoch/routesF02. R2Flash3.8Low61.6642279s/1turn test104lines,
productionexactR1identical; test8pass2cleanRED. R2 bỏcaseotherfocusduringrequest/
directguardcóởR1; saihaiF02completeness, primarythêmđúng2tablecases, khôngR3.
SourceR1/R2ápnguyênvăn, khôngCodexsửaproductionD0. GREEN10/10,focused63/63,
fullNode1016/1016,Python21/21. Independent81/81,Critical0/Important0; comparator
reverseD0=Boverlay0a737c3e,15helpers/10files unchanged.

Actualsignedstrictfocus24/24: priorbuttonrestored24,validation0POST,
24intentionalPOSTaborts/24expectedconsoleERR_CONNECTION_RESET,24native
retrysuccess3textitems,unexpectederror/external/unapprovedwrite/overflow0.
NoAPIresponsefixtures; all24downloadedJSsha5ac46bc3...; rawbrowserSHA
2b2c75da4b950ce78421064e7d11e1a35dcdae2562c86d706d2aa2b1b7535946.
SyntheticDOMunitprovesguards/controlflowonly; realbrowserseparate. Baseline
comparisonJSoverlays explicitlydisclosed, notcountedasfixture-freefinalQA.
QA39795stoppedexit0,tempremoved,listener51738=0outsideSandbox; workersboth
exit0/terminal,noIDE/auth/settingschange. Firstlaunchauto-reviewdeniedbefore
CreateProcess; publicMAPblob3916d78/specreceipt6365407001proof→samecommand
re-reviewedapproved. No runtimepayloadexport/no workaround.
