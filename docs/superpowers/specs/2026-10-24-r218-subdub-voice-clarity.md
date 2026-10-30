# SD-C3-VOICE-CLARITY — bỏ khối giọng thừa, không bỏ chức năng

## 1. Contract

- Repo `C:/Users/toann/Documents/Codex/_webapp-r218-voice`.
- Branch `webapp-r218-billing-ui-20261022`, PR661 / Issue664.
- BASE_SHA `89f6d6fe1a12047e79fa76a06f51a46c784dff95`.
- Dependency B4 accepted: receipt6379454063, CI40027725649 hai job SUCCESS,
  456/456 trạng thái. B4 search21/draft/Voice, B3 font16 và B2/C2/D2/E2 khóa.
- Owner: “tiếp tục xử lý triệt để theo thứ tự”; trước đó yêu cầu ẩn sạch ô
  thừa/vô nghĩa, không rút gọn mất chức năng. UI/UX trước, motion cuối.
- SIMPLE / SINGLE, một production file CSS. Không thay business logic.

## 2. READ và một kết quả cần đạt

Trong hai mode Lồng tiếng/Combo, voiceLaneHtml có đủ7 radios: nữ/nam mặc
định, giọng đã lưu, giọng tự thêm, Auto2, Auto Multi3–8, Smart Multi. Bên
dưới còn một fieldset Smart có legend và cùng một đoạn văn hai lần, không
có input/button/output hoặc dữ liệu speaker. Bên trên có hint lặp lại ghi
chú draft/readiness chung. READ48 đo24 trạng thái nhìn thấy khối lặp.

Kết quả: giữ7 lựa chọn thật và một ghi chú chung; ẩn fieldset Smart đang
guarded chỉ có mô tả và generic hint trùng. Không ẩn lane Smart, link kho
giọng, nguồn/target/mix/subtitle/review hoặc lỗi/kết quả có dữ liệu.

## 3. Allowlist và CSS chính xác

Chỉ `static/portal/portal-theme.css`, thêm ngay trước unique marker
`/* Final light AI Chat Workspace surface */`:

```css
.portal-subdub-hub .portal-subdub-smart-multi[data-status="guarded"],
.portal-subdub-hub .portal-subdub-voice-lane-hint {
  display: none;
}
```

Không thêm property, important, token, palette, media query hoặc motion.
Không đổi `data-status` bằng production JavaScript, không xóa source/DOM/
copykeys. Future Smart fieldset với status khác guarded KHÔNG bị selector
này ẩn. Guarded speaker-map có rule riêng, giữ nguyên. Ghi chú chung có
aria-describedby vẫn hiện; radio và Voice continuation giữ nguyên.

Protected: toàn bộ JS/i18n/portal.css/backend/API/auth/Bot/provider/ví/PayOS/
ENV/dữ liệu, B4 search/normalizer/draft/Voice/Music/quote, oldtests, Chat tail.
Docs/checklist/evidence/Tester cho batch do Codex cập nhật. Không viết unit
chỉ grep CSS; dùng actual browser RED/GREEN và old regression nguyên vẹn.

## 4. Acceptance và bằng chứng mở khóa D3

- C301: baseline signed QA Lồng/Combo ởVI/EN/ZH/sángtối/3901440 cho24 trạng
  thái; desired hidden assertion thất bại vì Smartfieldset/hint còn hiện.
  Không gọi marker tồn tại trong HTML là đã giấu khỏi visual/AX.
- C302: final48 dubbing/combo configs:2mode×3locale×8 viewport/theme
  (light3901440;dark3901440/360375768844ngang). Smartguardedfieldset/hint
  visible0/AX0, sharednote1, radios7visible/1checked; từng lane vẫn chọn được
  và review đúng. Auto2/Multi3–8/Smart vẫn có3callback khác nhau.
- C303: saved/custom mở đúng Voice workspace và return; mode transition giữ
  lane/mix0_200/customISO/language21/B4filter, source/CTAguarded nguyên.
  Phụ đề gốc/dịch không tự xuất hiện lựa chọn giọng. Một CSS-only diagnostic
  đổi Smartfieldset statusready được phép để kiểm selector không giấu nhầm
  non-guarded; KHÔNG dùng diagnostic đóng capability/engine.
- C304: không overflow/errors/external/UIwrites sau authsetup; keyboard và
  AX/ảnh. Không có newtext cần đo màu mới, không tuyên bố toàntrangAA từ C3.
  Asset hash khớp source LF, production reverse rule trả đúng toànCSS về BASE;
  JS/backend/oldtests/Chat không đổi. FullNode baseline1281, focusedSubDub,
  PythonCSScontracts, review độc lập.
- C305: cập nhật operations/comparison/Tester/prepush/provenance, mộtpush
  đúng nhánh, CI exactHEAD hai job và receipt trước tick C3/unlock D3.

Chỉ nghiệm thu clarity/dedupe hiện tại; grouping redesign và runtime của
giọng đã lưu/clone/speaker/dub còn theo SD01..21/T0, không bị xóa khỏi scope.
Không giả player/profile/giá/Smart execution. Không sửa báo cáo rỗng D3 ké.

## 5. Bước 2–5 phút và checklist trước BUILD

- [x] Đọc renderer/CSS/oldtests, tìm đúng inertfieldset/hint/note/radio.
- [x] B4 receipt/CI/readback, BASE/branch/phạm vi khóa rõ.
- [x] C301 browserRED24/visibleinert24/errors0/expectedassertionexit1 trướcpatch.
- [x] Flash3.8LowR1SUCCESS34.9398881s/1turn/139outputtokens,exact1record;noR2/noR3.
- [x] C302/C303 final48/336choices/96VoiceReturns/AX/inertboxhint0/note1/radio7/callbacks3/B4mixdraftgatesheld.
- [x] C304 Node1281/focused54/Python21/reviewC0I0M0/reversewholeCSS/JSbackendoldtestsChatunchanged/144LFassetchecks/errors0.
- [x] C305 Tester/docs/provenance/push/CIreceipt: SOURCE00239d7f/HEAD00a34c2b,
  CI40061704379bothSUCCESS456records/receipt6379877100/readback. Scoped only.

### AX-readiness diagnostic và giới hạn

Firstgreen30rows rồi ENdark844Dubbing AX-note literal mismatch, visualnote
vẫn có; originalsnapshot thiếu nên causeUNKNOWN. Probe3sameviewport đều
notevisual/AXtrue. QA bổ sung wait đúnglocaleDOMtrướcfreshAX vàrawcapture
khi tái hiện, không nới textassertion; final48 đạt, không đổi app. Giữ E3
readiness/hydration audit mở; không báo đã sửa rootcause từ lượt xanh sau.
Ảnhfieldset cófixedheadercrop, chỉ hỗ trợdedupe; actual336radio interactions
mới chứng minh giữ7lane. Non-guardedstatusdiagnostic chỉCSS,khôngengineproof.

Lệnh root: `node <QA>/browser-SDC3.cjs <isolatedorigin> red|green`, REDexit1
khi visiblefieldset/hint khác0, GREENexit0 với48configs và0errors/overflow.
`node --test tests/*.test.mjs`→1281pass/0fail; PythonCSScontracts→0fail.
Worker chỉ source/spec/MAP allowlist, không tools/Git/IDE/login/settings/
QAdata/ENV/Bot. R1/R2 tốiđa cùngSPEC_ID; noR3; sau2gatefails Solxhigh takeover.
Application PROVIDER_CALLS=0; WALLET_MUTATIONS=0; DEPLOY=NO;
LIVE_PASS=NOT_TESTED; GOAL=ACTIVE; MOTION=LAST.
