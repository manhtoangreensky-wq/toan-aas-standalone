# MU-NATIVE-PRESENTATION-D2 — form và kết quả thật, không khối thừa

23/10/2026. READY trước R1. D1 đã ACCEPTED scoped branch delivery.
Repo C:/Users/toann/Documents/Codex/_webapp-r218-voice;
branch webapp-r218-billing-ui-20261022; PR661/Issue664.
Source anchor 3e91dbd8244c0f51b42139c86cd62cdb0e243af1; D1 CI39975608329
terminal SUCCESS cả hai job,receipt664#issuecomment-6368236480;IssueD1tick
readbacktrue/D2open. Dependency đủ trước READY/RUNNING.
`2026-10-23-r218-music-presentation-d2-draft.md` là lịch sử giả thuyết;
chỉ file này là hợp đồng thực thi D2 khi dependency đạt. Không reset SPEC_ID.

## Outcome và phạm vi khóa

Theo yêu cầu Owner: ẩn ô vô nghĩa, không chữ thử nghiệm/demo/beta, không
chức năng/output giả; giữ palette/token xanh/ngọc/navy và native form thật.
Hai route `/media-workspace/music-directions`, `/media-workspace/sfx-cue-sheet`.
Không đổi stack, global design system, shell/navbar, API/engine/provider/ví.

- Ban đầu đúng 1 `.portal-card` nhìn thấy: form. Không intro/stat5/3/0,
  boundary, empty result, scope panel hoặc cột rỗng.
- Sau native success đúng 2 card: form + kết quả có đủ 3 item. Không xóa
  server title/description/cautions/review/content, cắt chữ hay dịch dữ liệu.
- Một H1 đúng ngôn ngữ, gắn trực tiếp trong từng renderer, không sửa helper
  `renderHero`, `localizedPageTitle` hoặc `localizedPageDescription` dùng chung.
  Hai page definitions có `action:"none"`; generic hero không chứa CTA nghiệp vụ.
- Một ghi chú ngắn ở form nói rõ kết quả là văn bản, không giả tệp âm thanh.
  Giữ các cảnh báo nội dung thực và lỗi/guard/pending/success/focus hiện có.
- Khi edit làm receipt stale: cảnh báo localized hiện ngay trong result,
  gồm SFX stale sau remount. Không thay state/source comparison/edit helpers.

## Allowlist và comparator

Builder được sửa đúng:

1. `static/portal/portal.js`: trong `renderMusicDirectionPresets`,
   `renderSfxCueSheet`, `renderMusicDirectionPresetResult`, `renderSfxCueSheetResult`.
   Chỉ header HTML cục bộ, 2 scope class hooks, 1 SFX family data hook,
   2 result body-suffix wrappers, 2 localized stale paragraphs, form copy fallback.
2. `static/portal/portal-i18n.js`: đúng 8 rows trong hai namespace bên dưới.
3. `static/portal/portal-theme.css`: block scoped bên dưới, ngay trước
   `/* Final light AI Chat Workspace surface */`, sau D1 rules. Không nối EOF.
4. Mới `tests/music-sfx-presentation-layout.test.mjs`, tối đa 250 dòng.

Codex quản lý spec/checklist/master/state/evidence/docs/Tester/Git. Không sửa
test cũ, signature/function dùng chung, normalizer, fields/required/min/max/
options, preset IDs/maps, transient draft, stale comparison/edit functions,
receipt placement, integration.js, API/auth/Bot/backend/provider/ENV/ví/motion.
Comparator: áp đúng worker edit records; reverse edits bằng BASE sau LF
normalization; 11 protected files của D1 và toàn bộ old tests không đổi;
D1 9 rows/2 field schemas/2 CSS rules giữ nguyên, Chat marker→EOF giữ nguyên.

## HTML chính xác

Trong mỗi page renderer, thay duy nhất `${renderHero(page, context)}` bằng:

```html
<header class="portal-hero"><div class="portal-hero-copy"><h1 class="portal-title">${safeText(musicDirectionUiText("page.workspaceTitle", "Hướng âm nhạc"))}</h1></div></header>
```

SFX dùng `sfxCueSheetUiText("page.workspaceTitle", "Gợi ý hiệu ứng âm thanh")`.
Không sửa hàm hero dùng chung hoặc page definitions. Form card/header/control
tiếp tục tồn tại. Dùng localized `form.title`/`form.body` đã chốt ở bảng.

Scope section cuối mỗi page thêm đúng class `portal-music-directions-scope`
hoặc `portal-sfx-cue-sheet-scope`, không đổi nội dung/`renderNotes(page)`.
SFX metadata span chứa `cue_family` thêm `data-sfx-cue-sheet-family`.
Không xóa enum/state hoặc đổi giá trị; chỉ ẩn khỏi presentation.

Trong hai valid result renderers, chỉ wrap phần `result.bodySuffix` đang có
bằng `<span class="portal-native-output-detail">...</span>`; giữ nguyên
server description đứng trước. Giữ nguyên `result.note` trong DOM, ẩn scoped.
Thêm trước closing section valid result, không thêm vào empty branch:

```html
<p class="portal-native-stale-note">${safeText(musicDirectionUiText("form.stale", "Nội dung đã thay đổi. Các hướng bên dưới thuộc nội dung trước; lập lại hướng âm nhạc để cập nhật."))}</p>
```

SFX dùng helper/form.stale/fallback SFX hiện có nguyên văn. Không thêm key
stale mới, không sửa `data-stale`, aria-live, heading tabindex hoặc edit helper.
CSS chỉ hiện paragraph khi result có `data-stale="true"`, đồng thời ẩn
pseudo `::after` cũ hardcoded VI. Warning thật không bị xóa sau SFX remount.

## Copy — đúng 8 rows (VI / EN / ZH)

| Namespace/key | VI | EN | ZH |
|---|---|---|---|
| musicDirectionUi.page.workspaceTitle | Hướng âm nhạc | Music directions | 音乐方向 |
| musicDirectionUi.form.body | Chọn phong cách và mô tả cảnh, người nghe, cảm xúc bạn muốn truyền tải. | Choose a style and describe the scene, audience and mood. | 选择风格，并描述场景、受众和情绪。 |
| musicDirectionUi.form.note | Nhận ba hướng âm nhạc bằng văn bản để biên tập; không tạo tệp nhạc. | Get three music directions as text for editing; no audio file is created. | 获取三个供编辑的文字音乐方向；不会生成音频文件。 |
| sfxCueSheetUi.page.workspaceTitle | Gợi ý hiệu ứng âm thanh | Sound effect planning | 音效规划 |
| sfxCueSheetUi.form.title | Bảng gợi ý hiệu ứng | SFX cue sheet | 音效提示表 |
| sfxCueSheetUi.form.body | Chọn loại hiệu ứng và mô tả những điểm cần nhấn trong video. | Choose an effect type and describe the video moments to emphasize. | 选择音效类型，并描述视频中需要突出的时刻。 |
| sfxCueSheetUi.form.note | Nhận một bảng gồm ba gợi ý hiệu ứng bằng văn bản; không tạo tệp âm thanh. | Get one cue sheet with three text-based effect suggestions; no audio file is created. | 获取一张包含三个文字音效建议的提示表；不会生成音频文件。 |
| sfxCueSheetUi.form.submit | Lập bảng gợi ý hiệu ứng | Create SFX cue sheet | 创建音效提示表 |

Các fallback tương ứng trong 2 page renderers bằng literal VI ở bảng.
Không thay Music submit/pending/success/error copy đã khóa A/B/C/D0.

## CSS — scoped, không đổi palette hoặc D1

Worker thêm nguyên block dưới trước Final Chat marker. `article` specificity
giữ scoped overrides thắng theme rules xuất hiện sau marker, không `!important`.

```css
article.portal-page:is(.portal-music-directions, .portal-sfx-cue-sheet) {
  gap: 16px;
}
article.portal-page.portal-music-directions :is(.portal-music-directions-intro, .portal-music-directions-boundary, .portal-music-directions-scope),
article.portal-page.portal-sfx-cue-sheet :is(.portal-sfx-cue-sheet-intro, .portal-sfx-cue-sheet-boundary, .portal-sfx-cue-sheet-scope),
article.portal-page.portal-music-directions .portal-music-directions-result:not([aria-live="polite"]),
article.portal-page.portal-sfx-cue-sheet .portal-sfx-cue-sheet-result:not([data-sfx-cue-sheet-receipt]) {
  display: none;
}
article.portal-page:is(.portal-music-directions, .portal-sfx-cue-sheet) :is(.portal-music-directions-layout, .portal-sfx-cue-sheet-layout) {
  grid-template-columns: minmax(0, 1fr);
  grid-template-areas: none;
  gap: 16px;
}
article.portal-page.portal-sfx-cue-sheet .portal-sfx-cue-sheet-layout > :is(.portal-sfx-cue-sheet-form, .portal-sfx-cue-sheet-result) {
  grid-area: auto;
}
article.portal-page:is(.portal-music-directions, .portal-sfx-cue-sheet) :is(.portal-music-directions-meta, .portal-sfx-cue-sheet-meta) > span {
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: var(--portal-muted);
  font-size: 13px;
}
article.portal-page.portal-sfx-cue-sheet [data-sfx-cue-sheet-family],
article.portal-page:is(.portal-music-directions, .portal-sfx-cue-sheet) .portal-native-output-detail,
article.portal-page:is(.portal-music-directions, .portal-sfx-cue-sheet) :is(.portal-music-directions-result, .portal-sfx-cue-sheet-result) > .portal-form-note,
article.portal-page:is(.portal-music-directions, .portal-sfx-cue-sheet) .portal-native-stale-note,
article.portal-page:is(.portal-music-directions, .portal-sfx-cue-sheet) :is(.portal-music-directions-result, .portal-sfx-cue-sheet-result)[data-stale="true"]::after {
  display: none;
}
article.portal-page:is(.portal-music-directions, .portal-sfx-cue-sheet) :is(.portal-music-directions-result, .portal-sfx-cue-sheet-result)[data-stale="true"] > .portal-native-stale-note {
  display: block;
  margin: 12px 0 0;
  color: var(--portal-warning);
  font-size: 14px;
  line-height: 1.65;
}
```

Nếu actual computed layout vẫn sai, ghi FAIL; không tự thêm specificityhack,
global rule, opacity hack, CSS reorder hoặc sửa lớp Chat/test cũ.

## Tasks 2–5 phút, RED trước source

1. Worker trả test mới (≤250 lines) dùng real catalogue, real 4 renderers,
   real safeText; doubles chỉ normalizer/input plumbing, ghi giới hạn rõ.
   Literal expected 8 rows/3 locales độc lập. Kiểm oneH1, scope/family hooks,
   localized stale p và suffix wrappers, giữ actual server strings escaped.
   Không dùng mock renderer thay SUT hoặc sửa test cũ.
2. Codex áp test trước; `node --test tests/music-sfx-presentation-layout.test.mjs`
   phải assertion RED đúng missingcopy/hooks/header, không SyntaxError/harness.
3. Worker production edit records stdout JSON. Codex áp nguyên văn sau RED;
   focused/new GREEN, full Node, Python native4files+foundation/bounded CI.
4. Codex actual signed browser: initial1/result2 card, 5presets/tool,3items,
   proper hierarchy/onecolumn/no gaps, submit44px/input16px/helperAA. Check
   VI/EN/ZH×light/dark×390/1440 +360/375/768/844landscape; text2x;
   all actual native POSTs only. No fixture API-success/media/audio assertions.
5. Edits1/2/3: result data remains, stale p correct locale, old pseudo hidden;
   SFX unrelated remount preserves edited draft/stale/result via existing logic.
   Real guard/error/retry/pending/focus controls unchanged. No hidden card's
   text/focusables in AX tree, 0unexpectederrors/overflow/external/unapproved.
6. Review/comparators/docs/currentoperations/initialcomparison/Tester/prepush/
   provenance/push/readback/newCIbothjobs/receipt664 before next spec.

Full commands: `node --test --test-concurrency=2 tests/*.test.mjs` (D1 1021);
Python native Music/SFX4files (D1 21); foundation90; boundedCI Linux396,
Windows395+1POSIXdeselected; `node --check`2JS, `git diff --check`.
Browser plugin absent → existing Playwright/Edge headless, task-owned DB only.
No new packages or visible IDE/browser; source-only Gemini packet, no QA data.

## Checklist và giới hạn

- [x] D1 terminalCIbothSUCCESS/receipt; BASE HEAD readback; READY trước worker.
- [x] P01 newtest assertionRED→GREEN,8rows/3locales, realrenderers/escape.
- [x] P02 sourceexact/oldtests+11protected+Chat/D1 unchanged; no drift.
- [x] P03 actualsignedinitial1/result2,3items/allpresets; localized stale warning,
  SFX remount/focus/error/guard/draft; AX/viewport/contrast/scale gates all đạt.
- [x] P04 regression/review/docs/Tester/prepush/provenance/pushCI/receipt.

One worker/project, Flash3.8 background, max R1/R2 same D2, no R3.
Không take over code trước hai lượt cùng acceptance không đạt. Spec gap ghi
đúng loại, giữ lịch sử. PROVIDER_CALLS_APP=0;WALLET_MUTATIONS=0;
PRODUCTION_DATA_MUTATIONS=0;DEPLOY=NO;LIVE_PASS=NOT_TESTED;GOAL=ACTIVE.
Music generation/player/download/save/reuse/Bot parity và motion vẫn mở riêng.

## Handoff history — P01 chưa đạt, không reset counter

R1Flash83.130014s/1turn/24records/210linetest. Test áp nguyên văn rồi chạy
exit1 trước assertions vì cataloguevariable khôngtồntại và fixtures/depssai;
index22SFXoldanchor0match/fallbackstalechanged. Khôngáp production.
R2source-only28582chars/command29447,53.0409963s/1turn/outerSUCCESSnhưng
responseempty;workerđòiRunCommandbịauto-denied. Khôngnớiquyền/settings/auth,
khôngR3. Sau2handoffP01chưađạt,CodexSolxhighchỉsửanewtestvàindex22anchor;
23productionrecordsR1khácgiữnguyên. Receipt664#6368677809.

Soltestrepair178lines:cleanRED52total/15pass/37assertionfail0harnesserror;
23R1records+index22correctionapplied;focused138/138,fullNode1073/1073,
boundedCI395portable/1POSIXdeselected/16warnings124.10s. Independent138/138,
C0/I0/M0;outside4renderers/11protected/oldtests/Chat/D1LF-normalizedunchanged.
Actualmaingreen-final48configs/96initial-resultstates/48nativePOST3items,
144editchecks/24SFXremounts/144AXhiddenchecks/48textstresspassed.
Raw3a162c32833ad95b8bd56e5729cbc859cb529b4ac8151d7ece6a0948fc333f25.
Firstmatrix46completedthenheightassertFAILnotnumericcapturedretainedin`green`;
probe44pxstatic/finite180mstransition,sub44notreproduced/causeunproven.
Finalrecheckawaitsfinitebuttonanimations,threshold44unchanged;noappmotionedit.
Error/guard/focusregression/deliveryvẫncổngriêng,chưatickP03/P04từmainonly.
Finalactualedge:focus24strict/24abort+24native retrysuccess,guard36configs/
72POSTattempts/72pendingchecks/36success+36denied,all3items;expectednetwork
console24separate,unexpectederror/external/unapproved/overflow0. P03accepted.
All5ownedQAserversclosedexit0/tempremoved/listeners0. P04deliverypending.
FinalP04accepted:HEAD e8738b5a/CI39985131009bothSUCCESS/396Linux+26runtime,
receiptIssue664#6369576116;IssueD2+parentDtickreadback. D2closedinscope,
fullMusic/audio/Botparity/merge/deploy/LIVEvẫnmở. RollstatusinErealcodebatch.
