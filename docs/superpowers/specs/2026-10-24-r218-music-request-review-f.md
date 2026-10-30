# MU08-F-REQUEST-REVIEW — xem lại lựa chọn trước xác nhận

24/10/2026 READY. BASE1e01f2417e3000a09c45186e11ee144e52a22fa5;
standalone WebApp / branchwebapp-r218-billing-ui-20261022 / PR661 / Issue664.
Dependency E accepted receipt6370628830/CI39992812318bothSUCCESS.
Luồng mới chỉ là presentation snapshot, không thêm action hoặc gửi request.

## READ và vị trí

Integration đã lưu payload gửi làm `flow.input`. `renderFormCard` dùng input
cộng transient để dựng form; existing musicQuote/hasFreshEstimate/receipt/
fingerprint/expiry quyết định confirm. `renderMusicFlowState` hiện chỉ giá,
gợi ý, báo cáo/tracking, chưa có review nội dung đã gửi.

Outcome: một section đọc-only **sau closing form, trước flowControls/CTA**,
trong cùng card. Không thêm portal-card, form, nút/chức năng giả hoặc summary
ở initial/draft/report phase. Không sửa shared helper hoặc signature.

## Allowlist / protected

1. `static/portal/portal.js`: chỉ thêm const `musicRequestReview` sau local
   `musicCopy` trong `renderFormCard`, và chèn `${musicRequestReview}` đúng
   closing tail của generic branch: `</form>${musicRequestReview}${flowControls}`.
   Không sửa nhánh Voice/Image/Video, existing gates, timer/sync/edit handlers.
2. `static/portal/portal-i18n.js`: thêm đúng4row `review.*` trong
   MUSIC_PRODUCT_COPY_ROWS, không thay row cũ.
3. `static/portal/portal-theme.css`: thêm scoped rules dưới trước FinalChat
   marker; old CSS/E/D1/D2/Chat tail giữ nguyên sau LF-normalization.
4. Mới `tests/music-request-review.test.mjs` <=260lines.

Không đổi API/backend/auth/field schema/options/transient/draft/input payload,
quote/confirm/fingerprint/expiry, provider/ví/Bot/ENV/motion hoặc old tests.
Non-Music output phải bằng BASE; ngoài hai JS insertions/copyrows/CSSblock
mọi source phải bằng BASE. Unit renderer doubles không thay SUT summary/gates.

## Gate hiển thị chính xác

Tất cả phải đúng mới dựng snapshot:

- `musicTask` đúng, `enabled` đúng và signed session có authenticated===true,
  csrfReady===true. Không session/false/stringtrue phải trả emptystring.
- flow đúng object, feature khớp route (`music_song` hoặc `music_background`),
  phase===estimate, status===awaiting_confirm.
- existing `hasFreshEstimate` và `musicQuote.confirmAllowed` đều đúng; không
  tự tính lại gate hoặc coi thiếu/invalid/negative/stringprice là hợp lệ.
  Giá 0 số hợp lệ vẫn được hiển thị theo gate cũ.
- flow.input là object không array; có own string brief không rỗng sau trim.
  Dữ liệu để render luôn snapshot `flow.input`, không transient hiện tại.

Nếu không đạt: const trả `""`, không title/note/rows trống. Không chạm các
confirm controls cũ dù summary không được dựng.

## Rows và dữ liệu

Section có `class="portal-music-request-review" data-music-request-review`
và `aria-labelledby="music-request-review-title"`; H3 id tương ứng, caption
review.note. Không aria-live tự đọc lại nguyên lyrics, không chuyển focus.

Dùng own-property scalar access, chỉ đọc whitelist; không dump JSON/unknown
fields, ID, token, providercost hoặc extra keys. Text Unicode/newline giữ
nguyên, safeText mọi data. Không cắt lyrics/brief, không dịch data khách.

- Product row: nhãn review.product, value từ nav.song/nav.background theo
  route đã khớp (không lấy tên provider/data không tin cậy).
- Tier row nếu own string basic/standard/premium; label field.tier.label,
  value option.tier.{value} (row đã có). Unknown/missing bỏ dòng.
- Mode row nếu own string song:lyrics/melody/custom hoặc background:
  background/melody/custom; label field.mode.label, option.mode.{value}.
- Song-only vocal row nếu mode lyrics/custom và ownstring auto/male/female/
  duet; label field.vocal_mode.label và option.vocal_mode.{value}.
- Song length row nếu ownstring seconds/half/full; label
  field.song_length_mode.label và option.song_length_mode.{value}.
- Duration row nếu background, hoặc song có lengthmode seconds, và ownvalue
  là integer number1..600 hoặc digitstring1..3digits có numericvalue1..600.
  Label field.duration_seconds.label (đã có đơn vị), value String(inputvalue).
  Không bool/blank/NaN/negative/decimal/object; half/full không có durationrow,
  không tự quy đổi duration hoặc nói là duration output đã tạo.
- Brief dưới DL: strong label field.brief.label + paragraph
  `class="portal-music-review-text" data-music-review-brief`, full escapedtext.
- Lyrics chỉ song mode lyrics/custom và ownstring không rỗng: details đóng
  mặc định `data-music-review-lyrics`, summary review.lyrics, pre cùng class
  portal-music-review-text. Melody/background không hiển thị inactive lyrics.

Mỗi DLdiv có `data-music-review-field="product|tier|mode|vocal_mode|song_length_mode|duration_seconds"`;
không input mới/edit/choose/confirm button. Không selectedsuggestionordinal/ID:
state hiện chỉ có prompt đã áp vào brief; không tạo identity mà server không có.

## Copy chính xác —4row VI/EN/ZH

| Key | VI | EN | ZH |
|---|---|---|---|
| review.title | Kiểm tra yêu cầu | Review your request | 核对请求 |
| review.note | Các lựa chọn đã gửi để nhận báo giá này. | These are the selections submitted for this quote. | 以下为获取此报价时提交的选项。 |
| review.product | Sản phẩm | Product | 产品 |
| review.lyrics | Xem lời bài hát | View lyrics | 查看歌词 |

Reuse musicCopy/musicProductText hiện có, VI fallback tương ứng. Không thêm
generic helper dependency hoặc đổi chữ ký musicCopy chỉ để truyền params.
Các existing field/option/nav labels đã có catalogue.

## CSS chốt

```css
.portal-music-request-review {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--portal-border);
  color: var(--portal-ink);
}
.portal-music-request-review h3 { margin: 0; font-size: 16px; }
.portal-music-request-review > p { color: var(--portal-muted); }
.portal-music-request-review dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 12px 0;
}
.portal-music-request-review dl > div { min-width: 0; }
.portal-music-request-review dt { color: var(--portal-muted); font-size: 13px; }
.portal-music-request-review dd { margin: 4px 0 0; color: var(--portal-ink); overflow-wrap: anywhere; }
.portal-music-request-review .portal-music-review-text {
  margin: 8px 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font: inherit;
  line-height: 1.65;
  color: var(--portal-ink);
}
.portal-music-request-review summary {
  display: flex;
  align-items: center;
  min-height: 44px;
  color: var(--portal-ink);
  cursor: pointer;
}
.portal-music-request-review summary:focus-visible { outline: 3px solid var(--portal-focus); outline-offset: 3px; }
@media (max-width: 600px) {
  .portal-music-request-review dl { grid-template-columns: minmax(0, 1fr); }
}
```

Không thêm motion/important/palette/token. Existing summarylines có thể dùng
trong section nhưng không thay DOMhooks/classởcácsảnphẩmkhác.

## Edit/expiry/session

Summary là snapshot đã gửi, caption luôn nói rõ. Khi khách sửa form ở DOM,
summary không tự thay thành input mới: confirm bị existing sync khóa và note
yêu cầu báo giá mới vẫn hoạt động. Không thêm event/timer/state mutation để
thay summary. Nếu remount khi edited/expired thì gate trả emptystring. Revert
chỉ theo existing confirm/freshness, không mở quyền mới. New estimate thay
snapshot đúng input mới. Logout/đổi session phải không giữ private snapshot.

## Tasks 2–5 phút và verify

1. Worker newtest trước: actual renderFormCard/musicQuoteState/freshness/
   voiceQuoteAmount/safeText/catalogue. Plumbing renderFields có thể double
   rỗng (không claim field/runtime); gates liên quan summary phải real.
   Dùng VM actualfunctions extract từ `  function name(` đến next `\n  }`;
   no brace-counting và không inventedcatalogue/helpernames.
2. Codex áp test, `node --test tests/music-request-review.test.mjs` phải
   assertionRED missing summary/copy, không ReferenceError/harnesscrash.
3. Worker editrecords: inline const + closingtail,4copyrows,CSSblock; Codex
   áp nguyên văn sau RED rồi focused/fullNode/nativePython+foundation.
4. SignedappQA+controlled quote state fixtures: phải ghi fixture,khôngbackend
   quote/audioproof. VI/EN/ZH/lightdark/390/1440 +small/landscape/textstress;
   valid0/future,unknown/invalid/expired,edit/revert/newquote/wrongroutefeature/
   unauthed/missinginput/unknownenum/half-full/melody/escaping/lyrics/disclosure/
   focus/noUIwrites. Confirm placement afterreview; original gatedCTA unchanged.
5. Non-Music comparators Voice/Image/Video/generic; current oldtests/JS outside
   inserts/integration/backend/Chat/E/D1D2 unchanged. Review independent.
6. H chỉ mở BUILD khi F đạt local acceptance; sau F/H mới docs/Tester/prepush/
   provenance/pushCIboth/receipt. Không push F chưa nghiệm thu để lưu tạm.

## Checklist

- [x] E accepted, BASE clean, exact data/gates/copy/allowlist/CSS trước R1.
- [x] F01 newtest204lines,RED106/172→GREEN172,0harnesserrors.
- [x] F02 exactR2+fourkeycorrection/12protected/oldtests/40nonMusicforms.
- [x] F03 controlled browser actualrenderer/AX/focus/draft/expiry/0UIwrite,
  fixture boundaries disclosed; no paid/canonicalquote/generation claim.
- [x] F04 Node1245/Python119/browser48;H mở sau gate này. FinalFH1257,
  independentC0I0M0;namespaceP2fixed. F/H final48/720AA/144assetchecks.
- [ ] FH delivery after both specs ready: docs/Tester/provenance/CI/receipt.

OneFlash3.8backgroundworker;maxR1/R2sameID,noR3. NoIDE/auth/settings/tools/
runtimeQAexport. PROVIDER_CALLS_APP=0;WALLET_MUTATIONS=0;DEPLOY=NO;
LIVE_PASS=NOT_TESTED;GOAL=ACTIVE;MOTION=LAST.
