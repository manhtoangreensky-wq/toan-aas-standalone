# MU07-A-RETAINED-OPTIONS — quay lại bộ gợi ý đã nhận sau báo giá

BASE520174941470fab34c60c26e62607ba2d4b3568f;PR661/Issue664;24/10/2026.
COMPLEX/SINGLE. F/H dependencyacceptedreceipt6372116359/CI40001922044bothSUCCESS.
Chỉ UI memory/navigation của luồng đã có; không tạo bộgợiýmới hoặc audio.
Owner: “xử lý triệt để toàn bộ theo thứ tự ... phần cuối là xử lý motion”.

## Outcome và bố cục

Sau app đã nhận gợi ý Music thật rồi chuyển sang estimate không kèm suggestions,
vẫn mở lại cùng những gợi ý đó qua native details “Xem lại các phương án” trong
outputcard hiện có, sau current suggestions/quote và trước report/tracking.
Disclosure đóng mặc định, khôngcardmới/form/input/nútgiả/selectedID.
Caption: chọn hướng khác cần báo giá mới. Copy/Apply dùng handlers hiện có.
Applypromptkhác→briefđổi/focusbrief/quote-stale khóaCTA;khôngrestorequote cũ.

## Allowlist / locks

- portal.js:2newglobals cạnh musicWorkspaceDraftSession;newfunction
  synchronizeMusicSuggestionSnapshots(context);1mountcall ngay sau existing
  synchronizeMusicWorkspaceDraftSession(context);inline read-only fallback
  trong renderMusicFlowState và chèn retainedmarkup sau`${suggestions}`.
- portal-i18n.js:đúng2relative MUSIC_PRODUCT_COPY_ROWS rows bên dưới.
- portal-theme.css:scoped disclosure và Music-suggestions contrast CSS trước
  FinalChat marker; current/retained dùng cùng component, không globalbutton.
- New tests/music-retained-options.test.mjs<=260lines.
- Docs/checklist/evidence/Tester theo batch;mọi oldtest protected.

Không sửa signature/export/helper hiện có, existing sessiondraftsync,
renderFormCard/F/H guards,outputSection/H,Apply/copy/dispatchAction,
integration/API/normalizer/DTO/gates/schema/backend/auth/Bot/provider/ví/
PayOS/ENV/motion. Không localStorage/sessionStorage/historywrite/newrequest/
timer/async/focuschange tự động trong newcache/renderer.

## Memory lifecycle — chính xác

### Cấu trúc đầu vào mà helper thực sự đọc

Các trường CSRF nằm **trong `context.session`**, không ở root. Flow nằm
**trong `context.featureFlows[route]`**, không phải `context.flow`. Ví dụ dưới
đây chỉ minh họa contract của helper bằng dữ liệu QA, không phải token thật:

```js
const context = {
  path: "/music/song",
  session: {
    authenticated: true,
    csrfReady: true,
    csrfToken: "qa-ephemeral-session-marker"
  },
  featureFlows: {
    "/music/song": {
      feature: "music_song",
      phase: "draft",
      status: "draft",
      data: {
        draft: {
          available: true,
          content: { suggestions: [{ prompt: "Mô tả đã nhận từ máy chủ" }] }
        }
      }
    }
  }
};
```

Không thêm các field `context.csrfReady`, `context.csrfToken`, `context.route`
hoặc `context.flow` để làm test xanh. Cùng một context có thể giữ flow của cả
hai route Music; helper xử lý từng entry trong `MUSIC_PRODUCT_ROUTES`.

Newclosureglobals:
`const musicSuggestionSnapshots = new Map();`
`let musicSuggestionSnapshotSession = "";`
Không gửi/log/sessiontoken vào payload hoặc evidence. Khôngpersistdisk.

New sync function chạy trước render mỗi mount, không đổi existingauth logic:

1. Chỉ signed context.session.authenticated===true,csrfReady===true và
   csrfToken nonemptystring. Missing/false/stringtrue/tokenrỗng =>clearMap,
   clearownsessionmarker,return. Token khácmarker=>clearMap trướccapture.
2. Mỗi routeMUSIC_PRODUCT_ROUTES có expectedfeaturemusic_background/music_song.
   flow phải object/nonarray,đúngfeature,phase draft hoặcestimate, status
   draft/ready cho draft,awaiting_confirm choestimate. Data/payload phải
   object/nonarray,available!==false. Sai/missing/confirm/error/guarded=>delete
   đúngroutecache,khôngchạmroutekhác/flow/draft/quote.
3. values là payload.content object/nonarray nếu có,ngược lại payload.
   Nếu own suggestions tồn tại: phảiarray;lọc object/nonarray có ownprompt
   string qua realcanonicalDraftText;takefirst3valid,khôngpadding/dedupe/shuffle.
   Clone mới chỉ prompt/name,mood,tempo,instrument,duration,vocal,use_case.
   Prompt dùng normalizedcanonicaltext;metadata chỉownstring<=2000,không
   copyunknownkeys/object/IDs/token/provider/price. Khôngmutate inputarray.
   Ítnhất1valid=>set{feature,suggestions};0valid/nonarray=>deletecache.
4. Không có own suggestions: phase draft=>delete;phaseestimate=>giữ snapshot
   đã nhận cùngroute/session,khôngkhởitạogiả. Explicitempty/malformed/error
   không được fallback về bộ cũ. Bound:2routes×tốiđa3items,khônghistoryvôhạn.
5. Reload khởi tạoMaprỗng. Mode/Back cùngdocument cùngsession có thể giữ hai
   route độc lập. Logout/tokenchange/phasesubmit/missingflow phảixóatheoluật.

## Rendering fallback

Existing renderMusicFlowState vẫn quyết định valid/status/payload/available,
quote/normal suggestions/report/tracking. Không thay những calculations đó.

Chỉ fallback nếu valid,flow.phaseestimate,statusawaiting_confirm,available,
values KHÔNG có own suggestions;newcache/marker đã tồn tại,cachedfeaturekhớp
expected,cachedsuggestionsnonemptyarray. Khôngfallbackinitial/draft/confirm/
wrongfeature/explicitempty/malformed. Renderer chỉ đọcMap,không mutate.

Vì renderer được dùng độc lập trong các harness/consumer cũ, đọc cache bằng
`typeof musicSuggestionSnapshots !== "undefined"` và marker tương tự;
thiếucache=>khôngfallback,khôngthrow hoặc tạo data. Không stub SUT bằng helper.

Markup:
```html
<details class="portal-music-suggestion-history" data-music-suggestion-history>
  <summary>localized suggestion.historyTitle</summary>
  <p>localized suggestion.historyNote</p>
  <!-- actual renderMusicCanonicalSuggestions(cached.suggestions,route,featureDraftTarget(flow,route)) -->
</details>
```
Không thêm heading lặp,aria-live/auto-open/focus,button hoặc selectedidentity.
Toàn bộ data vẫnsafeText qua existingrenderer. Existing price/confirm không
được suy từ history. Receipt/fingerprint/flow.input không bị phục hồi/ghi đè.

## Copy / CSS exact

| Relative key | VI | EN | ZH |
|---|---|---|---|
| suggestion.historyTitle | Xem lại các phương án | Review previous options | 查看之前的方案 |
| suggestion.historyNote | Chọn hướng khác sẽ cần báo giá mới. | Choosing another direction requires a new quote. | 选择其他方向后需要重新报价。 |

Registry tự prefixmusicProduct.,không doubleprefix. Existinglabels không đổi.
CSS exact trước FinalChat:
```css
.portal-music-suggestion-history { margin-top: 16px; }
.portal-feature-workspace--music-task .portal-music-canonical-suggestions {
  --portal-saas-teal: var(--portal-action);
  --portal-saas-emerald: var(--portal-action);
}
.portal-feature-workspace--music-task .portal-suggestion-card-head span { color: var(--portal-muted); }
.portal-music-suggestion-history > summary {
  display: flex;
  align-items: center;
  min-height: 44px;
  color: var(--portal-ink);
  cursor: pointer;
}
.portal-music-suggestion-history > summary:focus-visible { outline: 3px solid var(--portal-focus); outline-offset: 3px; }
.portal-music-suggestion-history > p { color: var(--portal-muted); margin: 8px 0; }
```
Khôngmotion/important/newtoken/palette.

### A04 clarification trước local acceptance — tương phản nút

QA thực tế phát hiện primary button kế thừa global gradient `!important`:
chữ trắng trên hai stop rgb(13,148,136)/rgb(5,150,105), tương phản 3,744/3,768.
Không sửa global rule hoặc thêm `!important`. Hai custom properties đã có ở
trên chỉ được override trong Music suggestions component sang existing `--portal-action`;
không tạo token/palette mới, giữ hover/filter/transform/motion nguyên trạng.
Đây là SPEC_GAP trong CSS ban đầu; logic/cache không mở lại. Bộ đo QA phải
tính background-image thực: gradient opaque có cùng màu ở mọi stop là nền
màu đó, không coi transparent backgroundColor là nền trắng 1:1. Giữ evidence
probe cũ và chạy lại cả normal/hover/focus khi mở acceptance A04.

Probe A04 tiếp theo đã qua bốn cấu hình sáng, rồi bắt ordinal “Phương án N”
ở tối có tương phản3,896:1. Scoped rule bổ sung dùng existingmuted. Cả hai
rule gợi ý áp dụng trong Musicproductworkspace cho **cùng component** ở bộ
hiện tại và bộ được giữ lại; không để card hiện tại tiếp tục chữ/nút khó đọc.
Không chạm F/Hform,confirm,globalprimarybutton hoặc sản phẩm khác. Selector
history vẫn chỉ margin/disclosure; alias đặt trên Music suggestions component.

## Acceptance / evidence

- A01:actualsync+actualrenderer draft3→estimateomit→disclosureclosed+cùng3;
  initialestimatewithoutpriorcache0;directestimatewithownsuggestionsnodup.
- A02:strictsession/tokenrotation/logout/missingflow/wrongfeature/errors/
  confirm/explicitempty/malformed clear,2routeisolation,ownscalarboundaries,
  originalinputimmutable,renderreadonly,storage/network/timers0.
- A03:actualCopy/Applyhandler sau mởhistory → prompt2 vào brieffocusgiữ,
  existingfreshnessblocksconfirm/Fsummary;newquote mới có thể tiếp tục.
  KhôngmintselectedID/restorequote/history tới endpoint.
- A04:VIENZH/theme/mobile/desktop/landscape/keyboardAX/disclosure44/AA4.5/
  text2x/nooverflow/errors/UIwrites/external;assetbyteskhớpsource.
- A05:oldcurrentdraft/quote0unknown/report/tracking/nonMusic/F/H/D1D2/E/
  integration/API/backend/auth/Chattail không đổi ngoàiallowlist.
- A06:focused/fullNode1257baseline/Pythonbounded/independentreview/Tester/
  docs/provenance/singlepushCIreceipt. MU07tổng/next-set/edit-regenerateOPEN.

Newtests phảiunit REDmissinghistory trướcproduction,khôngReferenceError.
Actual signedQA với controlled clientflowfixtures đượckhai báo rõ;không gọi
draft/estimate/confirm/provider thật để lấygợiý. Không dùng fixtures đóng T0.

## Checklist trước BUILD

- [x] READBotpin+WebDTO+gap đãlập tạiR218-MU07-BOT-WEB-CONTRACT-20261024.md.
- [x] F/Haccepted;scope/state/copy/CSS/lifecycle/negative gates chốt.
- [x] A01 RED19/18expectedassertions/harness0→GREEN19;actualbaseline24missinghistory→green48.
- [x] A02 ownership/lifecycle/bounds/0sideeffects:19actualhelperunit+48browserclearchecks.
- [x] A03 actualChoose/Edit/Back interactions,quote-stalepreserved:48mountedUIrecords.
- [x] A04 signedbrowser48/2304AA>=5.217/48hover>=5.161/48focus>=5.2/keyboardAX/44px/144LFassetchecks/0errors.
- [x] A05 Node1276/Python119/9exactrecords/13functions/12files/oldtests/Chat/independentreviewC0I0M0.
- [ ] A06 deliverydocs/Tester/provenance/CI/receipt.

Evidence `reports/audit/R218-MUSIC-RETAINED-OPTIONS-QA-20261024.json`.
R1FlashLow57.895231s failedgate;R2FlashHigh446.9415278s malformed/contextshape;
noR3. Solxhigh sameSPEC_ID supplied exact immutablepatches. Localgatesonly;
A06 requiresremoteCI/receipt. WholeMU07 and motion/runtime remainOPEN.

OneFlash3.8backgroundsource-onlyR1/R2max,noR3. WorkerkhôngGit/tools/UI/ENV/
auth/settings/runtimeQAdata. AppPROVIDER_CALLS=0;WALLET_MUTATIONS=0;
DEPLOY=NO;LIVE_PASS=NOT_TESTED;goalACTIVE;motionLAST.
