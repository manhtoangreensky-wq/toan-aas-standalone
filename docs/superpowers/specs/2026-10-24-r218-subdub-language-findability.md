# SD-B4-LANGUAGE-FINDABILITY — tìm ngôn ngữ, không làm đổi cấu hình

## 1. Nhận dạng và dependency

- Repo: `C:/Users/toann/Documents/Codex/_webapp-r218-voice`.
- Branch: `webapp-r218-billing-ui-20261022`; PR #661; tracker #664.
- BASE_SHA: `4d66ef14aa9aa74d57cd4c3cbac1e9d35e55bb21`.
- Dependency SD-B3 đã accepted: receipt #6374462006, CI #40020963811 hai job
  SUCCESS, 456/456 trạng thái; source font 16px đã khóa.
- Owner: “tiếp tục xử lý triệt để theo thứ tự”. Thứ tự đã duyệt: B4 tìm ngôn
  ngữ → C3 cụm giọng → D3 khối rỗng → E3 nghiệm thu UI; motion cuối cùng.
- COMPLEX / SINGLE: thay renderer và delegated input trên cùng bundle.

## 2. Kết quả duy nhất cần đạt

Trong ba mode Phụ đề dịch, Lồng tiếng, Combo, khách tìm được một trong 21
ngôn ngữ đang có theo mã hoặc tên VI/EN/ZH. Tìm kiếm chỉ lọc danh sách; không
tự chọn ngôn ngữ khác, không ghi draft/request/URL/storage và không mở xử lý.
Mode Phụ đề gốc không có bộ tìm ngôn ngữ đích.

READ #33: 36/48 trạng thái có target select nhưng không có search. 21 mã Web
khớp catalog Bot snapshot đã pin, không chứng minh provider/production hỗ trợ
mọi ngôn ngữ. Không thêm mã hoặc suy diễn capability trong B4.

## 3. UI chính xác

Giữ native select; thêm đúng label, input search và một dòng status ngay
trước label/select ngôn ngữ hiện có. Không thêm combobox, popup, card hay nút.

| Panel | Select hiện có | Search ID | Status ID |
|---|---|---|---|
| TRANSLATED_SUBTITLE | subdub-target-lang | subdub-target-lang-search | subdub-target-lang-search-status |
| DUBBING_ONLY | subdub-target-lang-dub | subdub-target-lang-dub-search | subdub-target-lang-dub-search-status |
| SUBTITLE_PLUS_DUBBING | subdub-shared-target-lang | subdub-shared-target-lang-search | subdub-shared-target-lang-search-status |

Markup input: `type="search" class="portal-input"`, KHÔNG `name`,
`data-subdub-language-search`, `data-subdub-language-locale` từ locale renderer,
`autocomplete="off" spellcheck="false" maxlength="64"`, `aria-controls`
trỏ đúng select ID; `aria-describedby` trỏ đúng status. Label `for` đúng ID.
Status: `small.portal-form-note`, `data-subdub-language-search-status`,
`role="status" aria-live="polite" aria-atomic="true"`; ban đầu count 21.
Không tự focus hoặc aria-live toàn panel mới. Giữ label hiện tại của select.
Input thừa hưởng B3 font16 và native min-height; không đổi spacing/layout.

Thêm đúng bốn copy keys trong mỗi VI/EN/ZH của SUBDUB_PRESENTATION_COPY:

| Key | VI | EN | ZH |
|---|---|---|---|
| targetLangSearchLabel | Tìm ngôn ngữ | Find a language | 查找语言 |
| targetLangSearchPlaceholder | Nhập tên hoặc mã ngôn ngữ | Enter a language name or code | 输入语言名称或代码 |
| targetLangSearchResults | {count} ngôn ngữ phù hợp. Lựa chọn hiện tại được giữ nguyên. | {count} matching languages. Your current selection is kept. | 找到 {count} 种语言。当前选择保持不变。 |
| targetLangSearchEmpty | Không tìm thấy ngôn ngữ phù hợp. Lựa chọn hiện tại được giữ nguyên. | No matching language. Your current selection is kept. | 未找到匹配语言。当前选择保持不变。 |

## 4. Helper và hành vi

Thêm `updateSubDubLanguageSearch(input)` trước `renderSubDubHub`.
Không đổi chữ ký/return của helper cũ. Không thêm state/cache/persistence.

1. Missing input, thiếu callable hasAttribute/getAttribute/closest, không có marker, type khác search, disabled, không nằm
   trong `.portal-subdub-hub [data-subdub-mode-panel]`, thiếu select/status,
   `aria-controls` sai select.id hoặc select.value không thuộc catalog:
   thiếu ownerDocument.createElement hoặc select.replaceChildren callable:
   trả false, không thay DOM/value/draft. Resolve select bằng selector cố định
   `select[name="target_language"]`, status bằng marker cố định trong cùng
   panel; so sánh ID với aria-controls/aria-describedby bằng chuỗi. Không
   nội suy ID vào querySelector, không fallback document toàn cục. Input type/marker là boundary thật,
   không coi mọi node trả về từ querySelectorAll là search input.
2. Locale chỉ vi/en/zh từ `data-subdub-language-locale`; mặc định vi nếu sai.
   Query string tối đa64 ký tự, dùng helper `normalizeCatalogSearch(value)`
   hiện có (KHÔNG sửa helper đó). Match substring trên mã + cả ba labels.
   Ví dụ `tieng nhat`, `ja`, `Japanese`, `日语` đều tìm ja; `zh` tìm ba mã
   zh/zh_cn/zh_tw; `Đức`/`duc` tìm de. Không có match giả từ provider ID.
3. Dựng options bằng `input.ownerDocument.createElement("option")`, đặt
   value và textContent từ catalog; `selected` đúng current value. Không
   innerHTML/query injection. Giữ thứ tự catalog. Cho phép options đang
   chọn xuất hiện dù không khớp; KHÔNG tính option pin vào số match.
   Empty query: đủ21; no match: chỉ current option, không đổi value.
   Dùng `select.replaceChildren(...options)` và giữ value cũ; không dispatch
   change, không đổi disabled/ARIA, không focus, không request/event/storage.
4. Status text từ copy locale, count thật; no match dùng câu riêng. Query
   không được đưa vào status dưới dạng HTML. Return true sau cập nhật.
5. Sau change thật ở target select, gọi helper cho search cùng panel để cập
   nhật option pin; selection/draft/review vẫn đi qua handler cũ trước đó.
6. Khi đổi mode, sau `captureSubDubDraft(subDubPage)` và trước apply draft,
   xóa query và khôi phục21 options cho các input type search có marker.
   Đây là nhánh bổ sung có phạm vi, không đổi thuật toán tab/history/draft.
   Cần reset trước apply để selected target từ mode trước luôn có option hợp
   lệ. Browser Back của Voice continuation giữ C2; tab mode vẫn replaceState.
7. Input event riêng search: gọi helper và return trước capture/summary cũ.
   Change event của chính search (native blur/change) return ngay, không
   capture/review hoặc dispatch thêm input. Change thật ở target select vẫn
   chạy đủ volume/voice/capture/review theo thứ tự cũ rồi mới refresh search.
   Không capture query. Khi remount/hydration, HTML mới search rỗng và đủ21,
   selected từ draft thật. Không mang query sang Voice hoặc tài khoản khác.

## 5. Allowlist và protected comparators

Production chỉ `static/portal/portal.js` ở các vùng: 12 copy rows; helper mới;
ba search markup; nhánh reset duy nhất trong updateSubDubModeSelection;
input/change delegated guards riêng. KHÔNG sửa normalizeCatalogSearch,
renderSubDubLanguageOptions, normalize/capture/apply/session draft, các field
cũ, Voice continuation, Music F/H/MU07-A, quote/submit, integration/backend/auth.

`static/portal/portal-theme.css`: đúng hai rule trước Final Chat:

```css
[data-subdub-language-search]::placeholder {
  color: var(--portal-input-placeholder, var(--portal-muted));
}
[data-subdub-language-search-status] { color: var(--portal-muted); }
```

Không important, palette/token mới, global rule hoặc motion. B3 font rule giữ.
New test `tests/subdub-language-search.test.mjs` ≤240 dòng, portable Node.
Mọi old test khóa nguyên. Documents/Tester/evidence được cập nhật bởi Codex.
Reverse từng record trả production về BASE sau LF normalize; ngoài record
không đổi byte. Chat tail, 12 protected source files, all old tests, helper
draft/Voice/Music/quote giữ comparator cụ thể. Không test chỉ grep source.

Impact scan trước code: `git grep -n -e 'updateSubDubModeSelection(' -e
'bindInteractions(' -- static tests` có runtime definitions/calls trong
portal.js và test consumers. Không rename/export/signature/refactor; chỉ
additive isolated guards trong bundle, giữ đầy đủ old regression tests.

## 6. Acceptance / evidence trước qua C3

- B401: actual signed baseline thiếu search → assertion RED rõ, không lỗi
  selector/harness; unit dùng actual helper RED nếu chưa có, không fake SUT.
- B402: actual helper theo 3 locale: aliases/code/diacritics/empty/no-match,
  selected pin/no implicit change, HTML-safe, bound64, invalid-root no-op,
  zero network/storage/events/draft mutation. Expected IDs/count viết literal.
- B403: 96 configs = 4 mode × 3 locale ×8 viewport/theme. Ba target panel có
  search và link label/ARIA đúng; source-only không có. Gõ/focus/Tab/chọn
  thật, no-match/clear/nhập Unicode, mode reset/latest target và remount giữ
  draft/giọng/mix0/200/customISO; Voice continuation quay lại; source/CTA
  guarded nguyên. Không API response/client-flow fixtures cần cho luồng này.
- B404: chữ/placeholder/status mới AA>=4.5 trên sáng/tối; input>=16px và
  height>=44; focus/AX, 2x scoped text, 360/375/390/768/844 ngang/1440 không
  overflow. 0 page/console/external/UIwrites sau QA auth setup; asset hashes
  matched LF. Không coi OS Dynamic Type/native iOS/PWA/motion là đã đo.
- B405: focused/fullNode1276 baseline +new tests, Python bounded, syntax,
  independent source review, comparators, docs/comparison/Testercases,
  prepush/provenance/singlepush/CI đúng HEAD/receipt trước tick/unlock C3.

Application PROVIDER_CALLS=0; WALLET_MUTATIONS=0; DEPLOY=NO;
LIVE_PASS=NOT_TESTED. Không gửi QA token, DB hoặc Bot source tới worker.
Flash3.8 R1/R2 tối đa; cùng SPEC_ID/counter, không R3; Solxhigh takeover chỉ
sau hai lần fail cùng acceptance. Không login/logout/settings hoặc IDE mới.

## 7. Checklist trước BUILD

- [x] SD-B3 receipt/CI/readback và branch/BASE được xác minh.
- [x] READ current source, tìm đúng 3 target select và lifecycle mode/draft.
- [x] Contract reset option trước apply, scope/shared impacts, copy/CSS rõ.
- [x] B401 browserRED48/missing36;Sol-repaired BASEunit5assertionRED/0harnesserrors153.9235ms.
- [x] FlashR1/R2review/historygiữ;R2sourceapplied10recordsverbatimaftercleanRED,Solnewtestonly/noR3.
- [x] B402 unit5GREEN176.4382ms/privacy/no-effects/bound64/HTML/negativefixture/order/reset21.
- [x] B403/B404 actual96/72target24source-only/288AAmin5.2238/input16height46/focusAX/2x/latesttarget-Voice-draft/288LFassetchecks/0errors;visual6supplement.
- [x] B405 Node1281/Python111/reviewC0I0M0/Tester32/docs/provenance4bb98050/SOURCE93cf390d/HEAD89f6d6fe/pushreadback/CI40027725649bothSUCCESS456records/receipt6379454063/IssueB4checkedreadback.

## R1 review trước apply — R2 cùng SPEC_ID, không reset lịch sử

FlashHighR1 SUCCESS237.4791486s/1turn, response JSON parse/syntax candidate
đạt nhưng code/test gate chưa đạt. Test artifact thực211 dòng (report nói185
là sai số), đã apply test-only; RED4 failures gồm3 missing-helper assertions
và parent, syntax0; production chưa áp. BrowserRED48/missing36/errors0.

R2 phải sửa đúng các finding: refresh target sau capture/review; resolve IDs
không nội suy selector và kiểm DOM methods/ownerDocument; unit không nuốt
mọi eval error, có assertion thật cho bound64/HTML/zeroI/O/draft/event/focus/
invalid boundaries. Combo markup phải đứng trước label ngôn ngữ cũ.
Root bổ sung spec gap về native search change/blur ở mục4.7 trước R2.
Không sửa oldtests hoặc code ngoài allowlist; noR3. Nếu R2 fail cùng gate,
Solxhigh tiếp quản cùng ID/counter, không giả R1/R2 đã accepted.
