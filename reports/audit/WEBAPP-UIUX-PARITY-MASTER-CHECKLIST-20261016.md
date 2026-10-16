# Checklist tổng WebApp standalone — UI/UX, product parity, locale và motion

**Checklist ID:** `WEBAPP-UIUX-PARITY-20261016`
**Plan:** `docs/superpowers/plans/2026-10-16-webapp-uiux-product-parity-master-plan-r217.md`
**Baseline remote:** `f59eacf63a49534854dc7cde06e5baed6546dc58`
**PR liên quan:** #647 — đang mở, chưa merge/deploy
**Ngày cập nhật:** 2026-10-16

## Cách đọc trạng thái

- `[x] CLOSED_WITH_EVIDENCE` — có source/runtime evidence đủ cho đúng phạm vi.
- `[~] SOURCE_GREEN_RUNTIME_OPEN` — source gate xanh nhưng chưa có runtime/live evidence.
- `[~] LIVE_DRIFT_OPEN` — source đã sửa, runtime còn bundle/triển khai cũ hoặc lệch.
- `[ ] TODO` — chưa thực thi.
- `[!] BLOCKED` — thiếu điều kiện bắt buộc; không được giả PASS.
- `[→] DEFERRED` — ghi nhận để không bỏ sót, mở bằng task/Owner gate riêng.

## 0. Hàng rào chung

- [x] Chỉ phạm vi WebApp standalone; Bot/Core là nguồn tham chiếu parity, không sửa trong
      checklist này.
- [x] Giữ màu xanh dương/xanh ngọc và nền tối xanh navy; không dùng đen/tím làm brand.
- [x] Không đổi route, action, field, capability, CSRF, idempotency, revision hoặc dữ liệu
      động trong các wave UI/UX.
- [x] Không provider call, wallet/Xu mutation, PayOS mutation, production data mutation,
      merge hoặc deploy trong lượt lập plan.
- [x] Fixed chrome VI/EN/ZH phải một ngôn ngữ; tên riêng/danh từ được phép giữ nguyên.
- [ ] QA runtime cô lập có URL/lệnh và tài khoản fixture ổn định.
- [ ] Antigravity handoff chỉ được đánh dấu PASS khi có log thật; không dùng báo cáo giả.

## 1. W0 — Baseline và evidence ledger

- [x] Đối chiếu remote: local cũ lệch; tạo worktree sạch từ `github/webapp-checklist-r116`.
- [x] Ghi baseline HEAD `f59eacf63a49534854dc7cde06e5baed6546dc58` và PR #647.
- [x] Ghi rõ source gate gần nhất: full Node 469/469, focused gates xanh, syntax và
      `git diff --check` xanh theo R216.
- [x] Ghi rõ live không phải PASS: R216-H mobile landing drift, R216-L next-route auth
      locale drift, R216-P live icon chưa xác minh.
- [x] Ghi 31 capability/139 customer entrypoints/41 admin surfaces từ master inventory;
      phân biệt UI partial với real-output/bridge gap.
- [x] Chốt protected contracts và safety flags trong state YAML R217.

## 2. W1 — Shell, responsive và visual foundation — Spec R217-01

- [x] Source có skip link → `#portal-main`, `<main tabindex="-1">`.
- [x] Source có boot skeleton, focus-visible, reduced-motion và guard không có
      `transition: all` trong Portal stylesheets.
- [x] Source giữ semantic dark canvas navy/teal và input tokens; không map sang obsidian.
- [~] **LIVE-UI-01:** viewport khoảng 327×667 còn clipping cụm header landing; source đã
      có media rule `max-width:420px`, cần delivery rồi chụp lại DOM/screenshot.
- [~] **LIVE-UI-02:** PWA FAB bundle cũ còn nổi che vùng proof; source đã có placement
      inline/readiness gate, cần runtime recheck.
- [x] **SOURCE-UI-01:** landing không tạo hoặc giữ banner/FAB khi chưa có
      `beforeinstallprompt`; iOS vẫn dùng hướng dẫn cài đặt riêng. Regression mới nằm ở
      `tests/pwa-landing-install-placement.test.mjs`.
- [x] **SOURCE-UI-02:** cụm điều khiển landing ở ≤420px có `flex-wrap: wrap`, giữ brand
      row và tránh ép locale/theme/CTA thành một hàng. Regression gate header đã cập nhật.
- [x] Source recheck sau W1: focused PWA/auth/utility/motion `39/39`, toàn bộ Node
      `470/470`, `node --check static/portal/portal.js`, `git diff --check` đạt.
- [!] Python Admin/PWA contract chưa chạy: bundled Python không có module `pytest`; đây
      là blocker công cụ, không ghi PASS giả.
- [~] Live recheck 2026-10-16 ở `/welcome?lang=vi`, viewport `327×668` vẫn nhận
      `local-57e76aa281dcc721fdaa`: `.portal-landing-nav-actions` là `nowrap`, right≈372
      vượt viewport 327 và `.portal-pwa-fab-trigger` còn fixed/display:flex. Source fix
      chưa được đưa lên runtime; giữ `LIVE-UI-01/LIVE-UI-02` mở.
- [x] Delivery evidence 2026-10-16: GitHub PR #647 vẫn `Open`; trang PR hiển thị
      `This branch has not been deployed` và `No deployments`. Đây là nguyên nhân xác nhận
      của live drift; không đánh dấu `LIVE_PASS` khi chưa có delivery được Owner cho phép.
- [ ] Đo viewport 320/375/390/414/768/1024/1440 ở light/dark; ghi `scrollWidth <= clientWidth`.
- [ ] Đo type/spacing/contrast thật; body ≥16px mobile, target ≥44×44px, contrast AA.
- [ ] Xác minh bảng/list chuyển hàng dọc hoặc wrapper có nhãn trên 375/390px.

## 3. W2 — Locale purity — Spec R217-02

- [x] Source locale R210 Workboard, R211 Memory, R212 Campaign, R213 Gallery/Audio,
      R214 Video có focused tests và catalogue VI/EN/ZH.
- [x] Source auth CTA dùng catalogue, có duplicate-key regression.
- [x] W2 source regression mới: locale/auth catalogue `272/272` Node pass; `portal-i18n.js`
      và `portal-auth.js` syntax pass. Admin fallback copy vừa dọn `Web audit metadata`,
      `Feature/provider readiness` và các nhãn vai trò/quyền hạn generic trong VI.
- [~] **LIVE-I18N-01:** next-route `/features → /login?next=/features` từng lộ
      `Tải & Cài đặt App TOAN AAS` trong bundle cũ; phải recheck đúng URL sau delivery.
- [ ] Quét fixed chrome toàn customer/Admin/product lanes; lập danh sách chuỗi English lọt
      trong VI và Vietnamese lọt trong EN/ZH; không sửa server data/ID/URL.
- [ ] Kiểm tra fallback locale, duplicate key, option label và aria-label ở VI/EN/ZH.
- [ ] Evidence: `node --test tests/auth-locale-copy-purity.test.mjs tests/*locale*.test.mjs`
      và browser AX tree theo locale.

## 4. W3 — Auth lifecycle, first paint và accessibility — Spec R217-03

- [x] Source auth entry giữ entry→settled lifecycle; provider reservation tránh layout shift.
- [x] Source Telegram giữ user gesture, PWA prompt chỉ gọi khi readiness thật.
- [x] Skip link, labels, autocomplete, aria-busy, password cleanup và reduced-motion guards
      đã có regression theo R216.
- [x] Auth source contract: intro bắt đầu ở đầu bố cục khi provider card cao
      (`align-items/align-content:start`, `padding-top:68px`); responsive auth header
      kiểm tra đúng ba hàng brand/locale/actions. Direct source checks của hai contract đạt.
- [x] Auth/customer/motion source regression bổ sung `31/31` pass; auth focused `16/16`
      pass. Python pytest vẫn không có trong runtime nên không đánh dấu pytest PASS.
- [ ] QA unauthenticated route matrix: `/dashboard`, `/features`, `/image/create`,
      `/subdub`, `/music`, `/voice`, `/admin` đều fail-closed đúng next path.
- [ ] QA authenticated first paint: skeleton → shell → data; không chớp trang hoặc render
      panel rỗng trước redirect.
- [ ] Keyboard: Tab order theo thứ tự thị giác, focus visible, Escape/Back cho modal/drawer,
      lỗi nằm cạnh field và không có focus trap.
- [ ] Evidence DOM/AX/screenshot/console/network; không login production nếu không có fixture.

## 5. W4 — Product lanes lấy flow Bot làm tham chiếu

Mọi lane dưới đây phải có một workspace chính và cùng state contract:
`input → options → preflight → confirm → progress → result/recovery`. UI không được
hiển thị thành công giả khi engine/bridge chưa có.

### 5.1 Image — Spec R217-04

- [x] Source presentation focused `188/188` cho Image/Voice/Music/SubDub/Video; UI giữ
      guarded boundary và không tạo output giả.

- [ ] Một entry `/image/create` có tạo ảnh AI và chỉnh sửa ảnh; không buộc người dùng mò
      route khác để upload/reference.
- [ ] Có prompt, tỉ lệ, style/preset, image reference/upload, biến thể, preview và lịch sử.
- [ ] Có trạng thái draft/guarded/processing/completed/failed; output gallery chỉ cho tải
      khi asset thật, không dùng `output available` giả.
- [ ] Nút chính, disclosure nâng cao, helper/error và mobile stacking được khóa bằng test.
- [ ] Phân biệt source UI green với `REAL_OUTPUT` chưa có bridge; evidence phải ghi rõ.
- [!] Image AI edit/reference upload/preview/delivery thật chưa có evidence; `/image/edit`
      hiện là Image Enhance deterministic và `/image-studio` là planning metadata.

### 5.2 Voice — Spec R217-05

- [ ] Một workspace có giọng mặc định, giọng tự thêm/tải file, voice library, preview,
      lưu/xóa có guard và chọn giọng cho sản phẩm khác.
- [ ] Liên kết selector giọng với SubDub/Music khi chỉ là presentation; không tự tạo clone
      hoặc gọi provider trong QA.
- [ ] Có text/language/rate/pitch/volume, preview loading, result/download/recovery,
      báo cáo request/job/output thật.
- [ ] Tách rõ `voice_tts` source pass với `voice_clone` runtime blocked.
- [!] Voice TTS/clone/preview/output runtime vẫn guarded; Voice Library chưa nối vào
      SubDub bằng evidence UI/runtime xác thực.

### 5.3 Music — Spec R217-06

- [ ] Một hub có hai mode rõ: tạo nhạc nền và tạo nhạc có lời; mode switch không làm mất
      input đã nhập.
- [ ] Nhạc nền: mood/style/duration/instrument/volume; nhạc có lời: lyrics/topic/language
      và vocal/instrumental; preset và preview dùng cùng hệ component.
- [ ] Có progress/result/history/export và cảnh báo boundary nếu generation bridge chưa có.
- [ ] Mobile mode switch/card/list theo hàng dọc; không trộn thuật ngữ English trong VI.
- [!] Hai hướng nhạc nền/nhạc có lời có entry/catalogue nhưng generation/export thật vẫn
      guarded; không có provider/output evidence.

### 5.4 SubDub — Spec R217-07

- [ ] Chỉ một giao diện cho phụ đề gốc, dịch phụ đề, lồng tiếng và combo; không chia route
      khiến người dùng đoán luồng.
- [ ] Chọn mode bằng segmented control/radio có nhãn: `Phụ đề gốc`, `Dịch phụ đề`,
      `Lồng tiếng`, `Phụ đề + lồng tiếng`.
- [ ] Có Smart Multi auto-detect: một giọng, hai giọng hoặc nhiều giọng; hiển thị mapping
      vai/giọng và cho phép override trước confirm.
- [ ] Voice selector lấy giọng mặc định/giọng đã lưu/giọng upload từ Voice library; có
      preview, volume giọng gốc/giọng lồng tiếng, subtitle style và target language.
- [ ] Ngôn ngữ dùng catalog đầy đủ theo năng lực Bot; mặc định tự nhận diện → tiếng Việt,
      sau đó EN/ZH và các target khác, không hard-code danh sách hẹp ở UI.
- [ ] Kết quả phải có video/track/subtitle artifact thật hoặc trạng thái bị chặn cụ thể;
      không dùng card “xong” cho draft.
- [!] `SMART_MULTI_UI_MISSING`: chưa có auto-detect/mapping một-hai-nhiều giọng; chưa có
      `SUBDUB_VOICE_LIBRARY_LINK_MISSING`; target language UI đang hẹp (VI/EN/ZH/JA/KO)
      so với contract mã ngôn ngữ rộng hơn của backend. Upload/CTA vẫn guarded.

### 5.5 Product Video — Spec R217-08

- [ ] Hub dọc liệt kê các lane video hiện có, mỗi lane có mục tiêu, input, output và
      boundary riêng; không gộp tên kỹ thuật vào CTA.
- [ ] `/video/create` và `/video/multiscene` giữ flow bảy bước nhập → plan → quote →
      confirm → progress → result → recovery.
- [ ] Có AI edit và manual edit: scene/timeline, poster, caption/audio handoff, upload/
      reference, version/history và report.
- [ ] Không tuyên bố real MP4/provider output khi parity matrix đang `PARTIAL` hoặc
      `BLOCKED_BY_RUNTIME`; phải link request/job/report thật nếu có.
- [!] `VIDEO_AI_MANUAL_EDIT_UI_MISSING`: AI edit/manual edit/timeline/render MP4/delivery
      chưa có evidence; Video Studio hiện là planning/scene/review/version metadata.

### 5.6 Content, Workboard, Free Tools, Notes, Projects — Spec R217-09A

- [ ] Mỗi surface có create/edit/save/archive/restore/version/history phù hợp và state
      empty/loading/error/guarded.
- [ ] Campaign/Calendar/Approval có mốc, trạng thái, lịch, review và handoff; không đổi
      server action/CSRF/revision.
- [ ] Free Tools/Prompt Gallery có filter, copy/save và phân biệt fixed chrome với prompt
      data; Workboard có board/list/card dọc trên mobile.
- [ ] Ghi nhận những phần chỉ là planning/draft, không gọi là sản phẩm đã tạo.

## 6. W5 — Admin và liên kết customer — Spec R217-09

- [x] Source Admin fallback locale đã dọn các nhãn kỹ thuật generic; focused Admin tab +
      motion suite `29/29` pass.
- [x] Admin module navigation đã chuyển thành danh sách dọc, `min-height:44px`, không còn
      `overflow-x:auto`/`min-width:max-content` trong scoped tab layer.

- [ ] Admin shell/menu/operations/billing/jobs/assets/customer/support/audit/reliability/
      ERP trình bày theo hàng dọc, nhóm rõ, không lẫn tiếng Anh trong VI.
- [ ] Owner thấy toàn bộ; role khác chỉ thấy module/action theo policy hiển thị. UI phải
      nói rõ quyền bị thiếu thay vì nút chết.
- [ ] Mỗi customer action có request/job/asset/report reference và trạng thái audit trên
      Admin; không tự bịa record nếu backend chưa nối.
- [ ] Manual top-up UI có amount/method/reference/status/approve/reject/reason và audit
      trail; phần mutation/ledger vẫn `DEFERRED` nếu chưa có Owner gate.
- [ ] Admin data tables ở mobile chuyển card dọc hoặc wrapper có tiêu đề cột; chart có
      legend/label không dùng màu đơn độc.
- [ ] Evidence source dùng các test `tests/test_admin_*`, browser QA cần canonical_admin
      fixture cô lập; không gọi production wallet.
- [!] Manual top-up có draft/confirm receipt/idempotency ở source nhưng chưa có canonical
      admin fixture/runtime evidence chứng minh duyệt và ghi ledger; giữ mutation deferred.

## 7. W6 — Motion và perceived performance — Spec R217-10

- [x] Source auth double-render, provider reservation, `left` transition, stale observer/
      RAF, reduced-motion listener, blanket will-change và PWA gesture đã có regression
      theo R216.
- [x] Current source motion/admin focused suite `29/29` pass; product presentation suite
      `188/188` pass; runtime FPS/CLS/LCP/INP vẫn mở.
- [~] Browser motion acceptance còn mở: chưa có trace FPS/CLS/LCP/INP và chưa chứng minh
      scroll reveal không tạo vùng trống trên runtime mới.
- [ ] Kiểm tra entry/stagger 240–450ms, micro 150–300ms, exit nhanh hơn entry; không animate
      quá 1–2 nhóm chính mỗi view, không dùng linear cho UI.
- [ ] Kiểm tra route unmount: observer/RAF/timer/listener bị hủy và async hydration không
      ghi vào shell đã thay.
- [ ] Kiểm tra `prefers-reduced-motion` trước và khi đang chạy; nội dung vẫn hiển thị.
- [ ] Chụp Performance trace đại diện desktop/mobile; ghi CLS <0.10, LCP ≤2.5s, INP ≤200ms
      hoặc ghi blocker nếu runtime không đo được.

## 8. W7 — Authenticated QA matrix — Spec R217-11

- [!] QA runtime cô lập chưa được cung cấp ổn định; không tự động tạo tài khoản production.
- [ ] Tạo fixture `customer_qa` và `canonical_admin_qa` chỉ trong DB QA cô lập, không ví,
      không provider, không bridge mutation.
- [ ] Ma trận route × locale (VI/EN/ZH) × theme (light/dark) × viewport
      (375/390/768/1440) cho customer và Admin.
- [ ] Mỗi route kiểm tra DOM title/heading/CTA/field, AX labels, focus, screenshot,
      console error/warning, network request và persistence sau reload.
- [ ] Các lane Image/Voice/Music/SubDub/Video phải có evidence từng state; nếu engine chưa
      có, evidence phải chứng minh guarded boundary chứ không gọi output PASS.

## 9. W8 — Live read-only recheck — Spec R217-12

- [~] Recheck R216-L `/features → /login?next=/features`: bundle cũ từng lộ CTA có chữ
      `App`; cần đọc lại sau delivery.
- [~] Recheck R216-H landing 327×667: header clipping và PWA FAB bundle cũ từng còn;
      cần DOM/screenshot mới.
- [ ] Recheck R216-P auth install icon wrapper/18px stable box trên direct login và
      next-route.
- [ ] Ghi asset fingerprint, runtime SHA nếu có, viewport, URL, timestamp, screenshot,
      AX, console/network; chỉ đóng khi evidence mới trùng source SHA.
- [ ] Không bấm CTA tạo job, không đăng nhập production, không deploy/merge trong wave này.

## 10. W9 — Deferred technical register — Spec R217-13

- [→] Web-to-Bot adapter cho Product Video/Image/Voice/Music/SubDub và job polling/output
      MP4/PNG/audio/subtitle.
- [→] Smart Multi backend auto-detect, voice mapping và catalog ngôn ngữ thực thi.
- [→] Autopost channel token bridge, publish queue thực tế và support ticket bridge.
- [→] Admin cross-bridge trace, customer task report và permission enforcement server-side.
- [→] Manual top-up approval → ledger/Xu mutation; chỉ mở sau Owner gate wallet/PayOS.
- [→] Các mục deferred phải có request ID/job ID/provider task ID, idempotency, audit,
      fail-closed và provider/wallet safety proof trước khi code.

## 11. Tổng trạng thái tại ngày 2026-10-16

| Nhóm | Đã có bằng chứng | Đang mở | Bị chặn/hoãn |
|---|---:|---:|---:|
| Source UI/UX/locale/static motion | 1 baseline xanh | 3 live drift/runtime gates | 0 |
| Responsive/PWA live | source fix + 39 focused / 470 Node | 2 (R216-H/R216-P) | QA runtime |
| Customer product parity UI | shell/partial nhiều lane | 6 lane acceptance | real-output bridge |
| Admin/customer wiring UI | source contracts rải rác | 1 master surface audit | backend/permission mutation |
| Authenticated QA | 0 | toàn ma trận | fixture/runtime |
| Technical parity/real output | 0 cho bridge AI | 0 trong wave UI | W9 deferred |

## 12. Quy tắc cập nhật bắt buộc

Mỗi lần làm một spec phải cập nhật ngay bảng này với `status`, `date`, `HEAD_SHA`, lệnh
verify, số pass/fail, screenshot/DOM evidence và blocker. Không xóa item đã đóng; nếu
phát hiện lỗi mới, thêm một dòng ở đúng wave và ghi `OPEN`. Checklist này là ledger duy
nhất để quyết định wave tiếp theo.

```ini
STATUS=PLAN_CHECKLIST_SPEC_READY_WAITING_OWNER
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
MERGE=NO
DEPLOY=NO
LIVE_PASS=NO
NEXT_ACTION=Owner mở W1 hoặc chỉ định spec cụ thể; chưa thực thi code trong lượt này
```
