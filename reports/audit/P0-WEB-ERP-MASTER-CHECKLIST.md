# MASTER CHECKLIST: P0.WEB.ERP.PRODUCTION_COMPLETION

## IMAGE UI — 2026-10-08

**SPEC_ID:** `IMAGE-UI-TRUTH-LOCALE-001` · **STATUS:** `I03_PR620_CI_PASS_READY_TO_MERGE_NO_DEPLOY`.
Nhánh local `fix/image-ui-truth-locale-20261008`, BASE
`dee0ac4ccaaf2cb3ebe147ab217e85ec419bec4c`. SubDub #619 đã merge và ghi
ĐÓNG/KHÓA trên GitHub; candidate tree = merge tree; PR CI `37755956582` và
main CI `37770140237` SUCCESS. Deploy/signed live SubDub chưa thực hiện.

- [x] Audit `/image` và `/image/create`: 24 trạng thái/ảnh, fake-ready/fake-output,
  giá -5 Xu tự đặt, copy VI trong EN/ZH, banner tương phản thấp và grid mobile bị ép.
- [x] I01-A RED: 4 kiểm thử bắt fake creation/download/readiness/price/output
  của `/image/create` và alias `/image/new` cùng lỗi đúng kỳ vọng.
- [x] I01-A code: bỏ riêng Image demo trước form thật; 3 thêm/67 xóa trong
  `portal.js`. Giữ nguyên fields/quote/confirm/tracking, backend và các sản phẩm khóa.
- [x] I01-A GREEN 4/4; Node regression 130/130; JS syntax/diff exit 0;
  Portal ngoài Image demo + 11 protected files trùng BASE.
- [x] Python BASE/candidate đều 18P/1F, exact cùng test
  `test_image_hub_private_pwa_scope_and_phone_touch_targets`. Test lấy nhầm
  media query 700px cuối file; CSS/test không đổi, `NEW_FAILURES=0`.
- [x] I01-A browser: 12 cấu hình/24 trạng thái/24 ảnh; đọc JSON + ảnh light
  desktop/dark mobile. Fake-ready/output/download/-5 Xu mất 12/12, trường thật
  `prompt/tier/format` còn 12/12; request ghi/failed resource/overflow 0;
  source hash `c125290e…` stable. Global ViewTransition vẫn có 12 lỗi, scope riêng mở.
- [x] I03 đã sửa light label/guarded-copy contrast; không suy ra toàn bộ nhóm
  công cụ Image hoàn thiện từ phạm vi hai màn hình này.
- [x] I01-B: copy cố định hành trình tạo ảnh VI/EN/ZH; Image suite 22/22,
  regression 148/148. Trường/payload/action names không đổi; gợi ý có copy/apply,
  tracking chỉ nhận ID khớp. Không đưa cost/source/private URL thành nội dung.
- [x] I01-B template QA: 48 trạng thái VI/EN/ZH × sáng/tối × 1440/360 ×
  guarded/local-draft/quote/confirmed-report; requests/resource/runtime/overflow
  0 trong ma trận same-page. Chạy lại sau sửa fixture `feature-submit` sai thành
  capability thật `feature-draft`, reset transient form trước từng kịch bản.
- [x] Amendment trình bày: Image không hiện nút xác nhận khi thiếu giá bán rõ
  nghĩa; không thay backend, giá, ví hoặc engine. Unknown không đổi thành 0.
- [x] I02: đủ 8 đích duy nhất, tạo ảnh trước, catalogue VI/EN/ZH; bỏ 4 mục lặp,
  Lossless/count 7 và mô tả xử lý/bảo đảm không có nguồn. RED 9F → GREEN 9P;
  tổng Image 31P, regression 157P.
- [x] I02 template: 12 cấu hình/24 trạng thái/24 ảnh, tám đích duy nhất và
  heading/copy đúng locale 12/12; Enter tới `/image/create` 12/12, overflow 0.
  Source hashes ổn định; 12 ViewTransition errors còn mở ở gate motion.
- [x] Amendment CI: đúng 4 Image selector/expected-href thay đổi để tìm mục
  tạo ảnh thực; giữ visibility/focus/scroll/fake-success checks. Syntax/diff đạt.
- [x] Official browser gate chạy trên candidate code `e91cfc42d9c574ce6a8d01bbc1e6bfdabb0478fe`:
  18 trang desktop/tablet/
  mobile; 6/6 kiểm tra hành vi hub; 4/4 tiện ích xác định; theme reload không
  nháy; bàn phím 6/6; lỗi JS/rejection/binding/request lỗi đều 0. 18/18 ảnh
  manifest ghi đúng SHA này.
- [x] I03 tạo ảnh: 48/48 trạng thái VI/EN/ZH × sáng/tối × 1440/360; chữ thường
  tối thiểu 5.944:1, chữ lớn 8.837:1, viền input 5.522:1; target ≥45px,
  summary 48px. Low-text/boundary/target/overflow đều 0; fields dọc.
- [x] Sửa đúng specificity summary Image: `:is(.portal-button, summary)` từng
  thắng rule 48px và để 44px bị co trong entry. QA đợi article cũ detach và
  animation hữu hạn trên main hoàn tất, không nới ngưỡng đo 44px.
- [x] I03 hub: 12 cấu hình/24 trạng thái/24 ảnh; style đạt, 8 đích duy nhất.
  12 lỗi ViewTransition điều hướng được giữ nguyên trong bằng chứng motion mở.
- [x] Hồi quy renderer 163/163; JS syntax/diff PASS; comparator 10 protected
  files + CSS/catalogue/Portal ngoài Image không đổi. Python vẫn 18P/1F nền.
- [ ] Theo dõi lỗi test mobile/PWA trên đúng CSS boundary trong scope nghiệm thu
  phù hợp; không nới hoặc sửa test ngoài I01-A để biến baseline thành xanh.
- [x] Web-only provenance refresh/verify đạt; `reports/migration` chỉ ghi
  `preflight.json` và `web_inventory.json`, không đọc/ghi bằng chứng Bot.
- [x] PR #620 CI run `37806139441` được đối chiếu log: 286 đạt, 1 lỗi duy
  nhất do readiness JSON khai 128 dòng trong khi `DANH-SACH-CASE.md` có 142.
- [x] Chỉ sửa metadata readiness của file case: 142 dòng, 34.854 byte,
  SHA-256 `612f3bbe…e91d10c8`; assertion giữ nguyên. Test metadata tái hiện
  đỏ trước sửa và xanh `1 passed` sau sửa.
- [x] Suite `test_p0_05d_tester_workspace.py` trên Windows: 32 đạt, 1 lỗi
  nền do test mode Unix `0600` nhưng Windows báo `0666`; đây không phải lỗi
  của metadata và không sửa/nới test. Hai tệp test/nguồn giống hệt `origin/main`;
  CI Linux là cổng kết luận cho nhánh PR.
- [x] Corrective commits đã push lên PR #620; run `37809597058` trên HEAD
  `5e720824c9b4f6aab3b826956334eeb1b76165b6` SUCCESS: bounded contracts
  `389 passed, 16 warnings`; browser gate 18 ảnh/6 hub × 3 viewport, hub
  `6/6`, tiện ích `4/4`, runtime `26 passed`, diff whitespace sạch.
- [x] PR #620 được GitHub xác nhận `OPEN`, `CLEAN`, một check `SUCCESS`;
  checkpoint này ở trạng thái sẵn sàng merge, chưa deploy.
- [ ] Shared-shell locale/nút nổi, Video hoãn và whole-site motion giữ thứ tự;
  ViewTransition lỗi vẫn mở, không báo PASS từ kiểm thử Image/SubDub.
- State: `.agents/state/IMAGE-UI-TRUTH-LOCALE-001-20261008.yaml`.
- Audit/spec/evidence local: `../../evidence/IMAGE-UI-AUDIT-20261008.md`,
  `../../evidence/IMAGE-UI-TRUTH-LOCALE-001-DRAFT-20261008.md`.
- I03 evidence: `../../evidence/IMAGE-I03-VERIFY-20261008.md`; JSON/ảnh ở
  `../../qa/20261007-video-uiux/image-i03-final-20261008/` và
  `image-i03-hub-final-20261008/`; official gate SHA-bound ở
  `../../qa/20261007-video-uiux/image-i03-official-e91cfc42-20261008/`.
  CI/PR/release còn mở.
- `PROVIDER_CALLS=0 WALLET_MUTATIONS=0 PRODUCTION_DATA_MUTATIONS=0`.

---

## KẾ HOẠCH UI/UX TỪNG NÚT — CURRENT-MAIN REBASELINE 2026-10-10

**SPEC_ID:** `WEBAPP-PRODUCT-CONTROL-BY-CONTROL-UX-20261010`<br>
**CURRENT_MAIN ĐÃ ĐỌC:** `86d4ee6e11ddfbc0d4e1dbf63b41d9b3ed7d859b`<br>
**Plan tổng:** `docs/superpowers/plans/2026-10-09-bot-web-function-parity-replan.md`<br>
**Spec capability:** `docs/superpowers/specs/2026-10-09-bot-web-capability-closeout.md`<br>
**Spec từng điều khiển:** `docs/superpowers/specs/2026-10-10-webapp-product-control-by-control-ux.md`<br>
**Spec shared shell:** `docs/superpowers/specs/2026-10-10-webapp-shared-shell-ui-closeout.md`<br>
**Trạng thái:** Plan được rebaseline và bổ sung spec; inventory từng DOM control, Bot canonical source và toàn bộ product UI vẫn OPEN. Hoàn tất phần tài liệu thì dừng; lượt sau tiếp tục việc UI/motion dang dở trước khi mở plan mới.

**Checklist điều phối riêng (không trộn với backlog ERP P0):**
`reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-20261010.md`.
**Đặc tả motion toàn site:**
`docs/superpowers/specs/2026-10-10-motion-webapp-surfaces-final.md`.

### A. Bằng chứng và sửa kết luận stale

- [x] Xác nhận plan/docs branch `45b84de…` còn dựa trên merge-base `17b9494…`, trong khi `origin/main` là `86d4ee6…`.
- [x] Đọc 11 commit first-parent #621–#634 sau base; xác nhận direct presentation-file touch là `static/portal/portal.js`, cùng các thay đổi API/DB, Music/Image/Video/Document Translation bridge và R4–R10 runtime matrices.
- [x] Sửa kết luận Music cũ: PR #621 thêm tier/giá, `vocal_mode`, `lyrics`, `song_length_mode`; bridge/API đã có trong source. UI current-main chưa được browser revalidate, quote/confirm correlation và audio output chưa được chứng minh.
- [x] Sửa ngôn ngữ của claim “12 ViewTransition invalid-state errors”: chưa được tái hiện trên current main nên ghi `CLAIM_NOT_REPRODUCED_ON_CURRENT_MAIN`; WA-35/36 vẫn OPEN.
- [x] Tạo spec con bắt buộc để mô tả từng nút/control; không tạo plan tổng thứ ba.
- [ ] Sau khi khép phần motion hiện đang dở, cập nhật `CURRENT_MAIN_SHA` lần nữa trước khi code; nếu khác `86d4ee6…`, chạy lại source-touch matrix.

### B. Cổng inventory — không giao builder trước khi đạt

- [ ] Khóa Bot Git SHA canonical và ghi riêng dirty overlay; cho tới khi khóa xong, không tuyên bố đủ/chưa đủ parity dựa trên một checkout bất kỳ.
- [ ] Dựng Bot action ledger đầy đủ cho command/callback/template/handler/admin action; alias không được làm rơi record; `UNKNOWN/UNREVIEWED=0` cho snapshot đã chốt.
- [ ] Tạo `reports/audit/WEBAPP-PRODUCT-UI-ACTION-LEDGER.md` và `.json` từ đúng current main + rendered route DOM; chưa được tạo trong task này.
- [ ] Đối chiếu route ↔ source renderer ↔ DOM button/control ↔ event handler ↔ endpoint/payload ↔ state/report. Mỗi route/action pair là record riêng; `CONTROL_UNKNOWN=0` mới được code capability đó.
- [ ] Mỗi record có source SHA/path/line, route, selector, label VI/EN/ZH, aria/help, intent, visible/enabled/disabled reason, quyền/owner, input/validation, request/payload, quote/cost, idempotency, state transition, success/error/recovery, report/artifact, responsive/a11y/theme/motion, test command/output và evidence.
- [ ] Nếu thiếu endpoint, payload, quyền, giá, trạng thái, hành vi lỗi hoặc output: ghi `UNKNOWN`/`BACKEND_GAP`, hỏi đúng owner/engine lane và không cho builder tự đoán.
- [ ] Ticket builder có đủ đường dẫn file, selector/dòng, spec đầy đủ, file cấm sửa, một lệnh verify chạy được + kết quả mong đợi; worker đọc skill tương ứng; `WORKER_LOCK=1`.

### C. Bảng sản phẩm/surface cần xử lý — không suy từ PR cũ

| Surface | Checkpoint gần nhất | Delta sau checkpoint/current-main cần rà | Trạng thái / việc tiếp theo |
|---|---|---|---|
| Video | #616 | Video job bridge, API và runtime matrices R5–R10 đổi; còn nhiều sản phẩm/editor | OPEN; để sau cùng, từng sản phẩm một; AI editor và manual/timeline tách riêng. |
| Voice | #617 | Runtime admission/contracts R4–R10 đổi | OPEN; revalidate TTS mặc định, saved voice, clone/profile và từng action quản lý. |
| Music | #618 | #621 sửa `portal.js`, thêm tier/giá/vocal/lyrics/length và bridge/API | OPEN; bắt buộc test `/music/create`, `/music/song`, quote→confirm và report; giá UI không là authority. |
| SubDub | #619 | API/runtime matrices sau checkpoint; old local evidence chỉ thấy guard và volume cục bộ | OPEN; một màn/bốn mode; verify từng payload, volume, report và artifact. |
| Image | #620 | #623 thêm Image Generation bridge; runtime matrices thay đổi | OPEN; tách AI create, AI edit, deterministic/manual; recheck guard/output. |
| Free Tools | Chưa có catalog đủ | Chưa có action-level inventory current-main | OPEN; mỗi tool có form/action/result riêng. |
| Notes / Memory / Reminders | Chưa có catalog đủ | Bot canonical chưa khóa; CRUD/runtime chưa được chứng minh | OPEN; action create/list/search/update/delete/reminder/priority tách riêng nếu source xác nhận. |
| Documents / PDF / OCR / Translation | Chưa có closeout từng action | Thêm Document Translation bridge sau baseline | OPEN; tách upload/inspect/translate/convert/export/download/retry và kiểm file thật. |
| Content / Prompt tools | Chưa có closeout mọi action | Draft text không chứng minh AI output/publish | OPEN; tách compose/save/copy/apply/export và ghi đúng giới hạn. |
| Auto-post / Channels | Chưa có closeout publish | Kết nối/authority/receipt chưa tái xác minh trên `86d4ee6…` | OPEN; không hiện “Đăng” như sẵn dùng nếu thiếu kênh/approval/receipt. |
| Projects / Workboard | Chưa có action catalog | Chưa revalidate route/DOM từng nút | OPEN; tách tạo/sửa/giao việc/hoàn tất/lọc; không trộn job engine. |
| Assets / Downloads | Chưa có action catalog | Metadata != file sẵn sàng | OPEN; tách preview/download/delete/share và owner/readiness. |
| Support / Tickets | Chưa có closeout toàn action | Chưa đối chiếu từng trạng thái/attachment/report | OPEN; giữ input lỗi, phản hồi dễ hiểu và đường khôi phục. |
| Members | Chưa có closeout | Vai trò, quyền, thành viên được cấp và trạng thái từng action chưa có ledger current-main | OPEN; xác minh authority trước khi tạo/đổi quyền; không tạo CTA giả. |
| Rewards | Chưa có closeout | Điều kiện, số dư/điểm và lịch sử reward chưa có action map current-main | OPEN; tách quyền đọc/ghi, nguồn tính và lịch sử; không suy từ màn Members. |
| Community / Referral | Chưa có closeout | Chưa có current-main action map | OPEN; disposition từng action và quyền riêng. |
| Admin ERP | Checklist legacy 19 specs | Không phải chứng nhận từng nút hiện tại; API/runtime còn đổi | OPEN; role/record/audit/confirm/undo/report phải ghi từng action. |
| Shared shell | Chưa có closeout toàn shell | `portal.js` đổi sau checkpoint; source current cần rendered recheck | OPEN; nav/account/locale/theme/install/assistant/back/focus ở anonymous + signed. |
| Motion | WA-35/36 chưa đóng | R11 cũ fail; 12 lỗi trong tài liệu chưa xác minh trên main | OPEN; khép việc đang dở, rồi rerun normal/reduced, rapid/back-forward trên current main. |

### D. Checklist UI/UX cho từng nút/control

Áp dụng checklist con trong spec `2026-10-10-webapp-product-control-by-control-ux.md` cho **từng dòng**, không đánh dấu thay cho cả route:

- [ ] Default/hover/focus-visible/active/selected/disabled + lý do/loading/duplicate lock.
- [ ] Success chỉ sau kết quả đúng; validation/server/permission/offline error có thông báo và cách sửa.
- [ ] Submit lỗi không xóa input; retry idempotent; cancel/destructive chỉ khi API hỗ trợ thật.
- [ ] Mọi trạng thái có copy đủ VI/EN/ZH; aria-label/help/error khớp trạng thái.
- [ ] Một primary action rõ; form/list theo cột dọc; không nhồi các nút ngang hàng.
- [ ] Giữ màu xanh–teal; dark mode xanh đậm + chữ sáng, không chuyển sang nền đen.
- [ ] Contrast thường ≥4.5:1, chữ lớn/UI ≥3:1, hit target ≥44×44px; Tab/focus và touch dùng được.
- [ ] 360/375/768/1440px không tràn, chồng, cắt; input không mất focus khi hiện bàn phím.
- [ ] Motion giúp hiểu phản hồi, không animate layout; reduced-motion vẫn dùng đầy đủ.
- [ ] Có test interaction thật trên rendered state + screenshot/DOM/console evidence; snapshot string hoặc route 200 một mình không PASS.

### E. Thứ tự thực hiện khóa

1. [ ] Chốt plan/checklist/spec và dừng tại đây.
2. [ ] Lượt kế tiếp tiếp tục phần UI/motion hiện đang dở; giữ nguyên các thay đổi worktree; không mở sản phẩm mới.
3. [ ] Khi việc dở đóng: recheck main, khóa Bot source, dựng Bot action ledger + Web control ledger.
4. [ ] Shared shell theo spec riêng → Voice → Music → SubDub → Image → từng nhóm không phải Video (Members và Rewards là hai nhóm riêng) → Video từng sản phẩm/editor → whole-site motion/final certification.
5. [ ] Sau mỗi spec: Tester độc lập, review checklist live, nếu lỗi thì sửa đúng spec gốc rồi chạy lại bằng chứng trước khi qua spec kế tiếp.

**Trạng thái chốt task plan:** `PLAN_UPDATED=YES`; `BUTTON_LEDGER=NOT_CREATED`; `BOT_CANONICAL_SHA=NOT_LOCKED`; `WA35/WA36=OPEN`; `PRODUCT_CODE_CHANGED=0`; `PROVIDER_CALLS=0`; `WALLET_MUTATIONS=0`; `PRODUCTION_DATA_MUTATIONS=0`; `DEPLOY=NO`; `LIVE_PASS=NO`.

### WA-35 motion measurement update — R11 / 2026-10-10

- [x] Hydrated local matrix collected: 16/16 route × viewport × motion rows; `CLS=0`, browser page errors `0` in all rows.
- [ ] Performance acceptance remains open: 4/16 rows contain a long task over 200 ms (maximum 311 ms); 10/16 rows contain a frame gap over 200 ms (maximum 450 ms).
- [ ] Motion-duration assertion remains unverified: computed entrance appears in all 8 normal rows and in 0 reduced-motion rows, but the harness recorded no `animationend` event for the 8 normal rows and exited `1`; do not mark WA-35 PASS.
- [ ] Attribute the remaining long frames/tasks, correct the event instrumentation or measurement timing, then rerun the same matrix and protected comparators before closing WA-35/WA-36.
- Evidence: `evidence/motion-wa35-measured-20261010-r11.md`. Run is local QA only; no provider, wallet, production-data, merge, or deploy action.

### WA-35 follow-up — R27–R35 / 2026-10-10

- [x] Latest partial localhost QA is recorded in `reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-20261010.md` and `docs/superpowers/specs/2026-10-10-motion-webapp-surfaces-final.md` on HEAD `45b84de…` plus the documented dirty source overlay; it is not main or production evidence.
- [x] Dashboard R34/R35 observed 10 `mount()` calls, including 9 hydration-driven calls matching 9 `integration.merge()` calls. R35 still recorded one completed 0.68-second entrance and no cancel; animation replay is not established.
- [x] Existing lifecycle/fallback harnesses ran against the recorded dirty source overlay: 7 passed; the older baseline reproduces hydration replay and current code settles same-route hydration. This is not a browser performance attribution test.
- [ ] Long tasks (223/198/252 ms) and the 700 ms frame gap remain unattributed; no RED regression currently identifies their source. Keep WA-35/WA-36 OPEN and do not claim smooth-load or motion acceptance.
- R35 next step is superseded by the R36 sample-matrix evidence below; performance RCA and full route/state coverage remain open.

### WA-35/36 R36 — 2026-10-10

- [x] Isolated localhost Chrome/Playwright QA: 16/16 rows across four routes, two viewports and normal/reduced motion; page/console/request/external/CLS/overflow errors are zero.
- [x] Normal entrance assertions pass 8/8 at `0.68s`; reduced mode has no hero/main entrance in 8/8. Features reveals all 12 groups in all four mode/viewport rows.
- [ ] Performance fails: long tasks `>200ms` in 11/16 rows (maximum `761ms`); frame gaps `>200ms` in 16/16 (maximum `866.7ms`). Worst LoAF `874.7ms`, blocking `749.7ms`; source attribution partial, so no motion-only cause established.
- [ ] Dashboard normal leaves hidden, zero-height `.portal-dashboard-assurance` `is-pending`; CSS intentionally hides technical assurance. Verify the motion target/acceptance contract without treating it as visible customer content.
- Evidence: `C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\outputs\wa35-r36-attributed-20261010\matrix.json` and 16 PNG/JSON rows outside the repository. `FOCUSED_HYDRATED_MOTION_PASS`, exit `0`, is only a focused motion/browser/layout pass—not performance or full-site PASS.
- Next: trace the R36 long frames on the same QA fixture, compare normal/reduced and cold/warm, extend route/auth/navigation coverage, then make a narrowly scoped change only if motion-owned RED evidence is reproducible. Do not change route/engine bundles from this task.

## VIDEO UI CHECKPOINT — 2026-10-07

**UI RELEASE:** `CLOSED_LOCKED` — giữ nguyên ba màn sản phẩm đã nghiệm thu.
Video ngoài ba màn này và motion toàn site vẫn mở bên dưới.

Owner chốt: merge checkpoint Video đang làm, sau đó ưu tiên Voice → Music →
SubDub → các tính năng khác, rồi quay lại Video còn lại sau cùng. Checkpoint
đã squash-merge vào standalone main tại `8a040d0c2af0cdcb2ebd89a27f5f2caa9beff952`.

- [x] Hub Video, Video nhanh và Video nhiều cảnh: VI/EN/ZH × sáng/tối ×
  1440×900/375×812 = 36/36 kiểm tra giao diện thật trên QA cô lập.
- [x] 10 điểm đến duy nhất; tool/input đầu tiên hiện trong viewport, form dọc,
  hướng dẫn và thiết lập thêm thao tác bằng Enter, menu đóng/mở/Escape đúng.
- [x] Không tràn ngang, drawer đóng không che nội dung, không có khung mẫu
  RTX4090/video tạo sẵn hoặc tuyên bố trừ Xu giả trên hai form.
- [x] Màu computed: chữ nhỏ nhất 4.515:1; viền input nhỏ nhất 3.399:1.
- [x] 60 ảnh QA gắn hash nguồn/ảnh; runtime của ba route 0 lỗi.
- [x] Cập nhật spec, nghiệp vụ, đối chiếu tài liệu gốc và case nguồn Tester.
- [x] Official Web contracts, PR #616 CI, squash merge và deploy đã có bằng
  chứng riêng: PR CI 389 Web contracts + 26 runtime assertions + 18 CI
  screenshots; Main CI và deploy đều thành công. Runtime SHA được đối chiếu
  với Web nginx ACTIVE trong hồ sơ đóng PR #616.
- [ ] Lỗi ViewTransition ở bước đăng nhập/điều hướng và cổng motion cuối còn mở.
- [ ] Self-shot/trend/storyboard/Video dài/motion-guide và các công cụ biên tập
  chưa thuộc checkpoint này, giữ mở để quay lại đúng điểm đang làm.
- Spec: `docs/superpowers/specs/2026-10-07-video-ui-checkpoint-release.md`.
- Hồ sơ merge/deploy: [PR #616](https://github.com/manhtoangreensky-wq/toan-aas-standalone/pull/616),
  PR CI run `37630929796`, Main CI run `37631528823`, deploy run `37632060634`.
- `PROVIDER_CALLS=0 WALLET_MUTATIONS=0 PRODUCTION_DATA_MUTATIONS=0`;
  API/engine của main được giữ nguyên, parent goal ACTIVE.

## VOICE UI RELEASE — 2026-10-08

**SPEC_ID:** `WEBAPP-VOICE-UI-CLOSEOUT-20261007` · **STATUS:** `DEPLOYED_SOURCE_VERIFIED_AUTHENTICATED_LIVE_OPEN`.

**UI SOURCE/RELEASE:** `CLOSED_LOCKED`; đã ghi trên đầu PR #617.
Không sửa lại renderer/khóa dịch/CSS sản phẩm Voice trong các checkpoint sau.
Gate kiểm tra có đăng nhập là một mục chỉ-đọc còn mở riêng.

- [x] Voice hub/forms/inventory/Studio/detail/Composer/flow-state presentation
  checkpoints reviewed; six renderer suites 110/110 pass.
- [x] Pre-release review reproduced and fixed two additional UI defects:
  resumed-draft save-new label empty in VI/EN/ZH; ambiguous `cost_xu` used as a
  price fallback. Existing action/field/server authority contracts preserved.
- [x] Update operating/source-comparison docs and VUI-01..04 case source before
  push. Existing labels and issue templates were read; Projects lacks
  `read:project`, so no automatic scope refresh or Project-write claim.
- [x] Stage only Voice hunks and publish candidate `6ef97e1` as draft
  [PR #617](https://github.com/manhtoangreensky-wq/toan-aas-standalone/pull/617).
  Local official browser gate: 18 pages, 6/6 primary keyboard checks, 4 tools;
  runtime assertions 26/26. Provenance gate passes on exact release HEAD.
- [x] Ubuntu Web CI run `37724197462` passed: 389 Web contracts, 26 runtime
  assertions and 18 browser screenshots; 6/6 primary keyboard checks.
  PR #617 squash-merged at `e405cbee28f0687f528eab7d66a71ef1623125f4`;
  merge tree matches tested candidate exactly. Windows suite completed
  387 passed/2 failed before case metadata was corrected (target retest now
  passed); the unchanged POSIX assertion passed in Ubuntu CI.
- [x] Main CI `37724519640` SUCCESS; deploy `37724809429` SUCCESS; runtime
  SHA `e405cbee28f0687f528eab7d66a71ef1623125f4`; tracked diff 0 and Web/nginx
  active. Three production assets match immutable Git blobs exactly.
- [x] Anonymous production entry at 1440×900/375×900 redirects to login with
  visible auth form; no overflow, page error or POST. Evidence:
  `../../qa/20261007-video-uiux/voice-production-e405cbe/readback.json`.
- [ ] Authenticated production Voice presentation remains open; QA logged-in
  results do not replace this gate. No claim of real audio, job or delivery.
- [x] Voice code release closed; Music/SubDub changes remain separate.
- [ ] Shared shell locale, floating controls and whole-site motion remain open.

## MUSIC HUB UI — 2026-10-08

**SPEC_ID:** `MUSIC-HUB-UI-CLOSEOUT-20261008` · **STATUS:** `DEPLOYED_SOURCE_VERIFIED_CLOSED_LOCKED`.
Music đã merge/deploy và ghi CLOSED/LOCKED trên [PR #618](https://github.com/manhtoangreensky-wq/toan-aas-standalone/pull/618#issuecomment-6052708871). Không sửa lại Music renderer/catalogue/CSS trong các checkpoint sau. SubDub đã qua QA cục bộ nhưng chưa release.
Thứ tự tiếp: SubDub → các tính năng khác → quay lại phần Video còn lại → motion toàn site.

- [x] Close Music release on `fix/music-ui-closeout-20261008`, BASE
  `e405cbee28f0687f528eab7d66a71ef1623125f4`; exact-candidate renderer/browser/
  Web CI, one PR and separate deploy/source readback.
- [x] Music CI primary-link selection follows its real first creation card;
  preserve every Voice selector and all fail-closed focus/visibility assertions.
- [x] Exact candidate `431e851`: 12/12 Music UI cases, vertical groups and
  primary visibility 12/12; contrast light 4.635:1 / dark 5.522:1, card touch
  height minimum 154px; Enter reaches `/music/create` with confirm still gated.
  Node Music/Voice 117/117; official QA 18 captures, 6/6 focus, runtime 26/26.
- [x] Main CI `37729895916` and deploy `37730228430` succeeded; runtime SHA
  `e70175a5f8b4d30bdf99de939b80d2de2e54ee18`; Web/nginx active, health OK,
  source diff 0, production asset Git-blob match 3/3. Anonymous public entry
  at 1440/375 shows login form with zero overflow/errors/POSTs.
- [ ] Global motion remains OPEN: fresh matrix records 12 uncaught
  ViewTransition invalid-state errors on navigation. `portal-motion.js` is
  unchanged; do not report whole-site motion PASS from Music UI tests.

- [x] Đối chiếu ảnh và ma trận nền `/music`: 12/12 locale × sáng/tối ×
  1440×900/375×812; chưa thấy tràn ngang hoặc lỗi runtime của route.
- [x] Ghi defect đã xác nhận: lẫn ngôn ngữ, số liệu/chất lượng/bản quyền không
  có nguồn, lựa chọn sáng tác nằm sâu, nhóm lối tắt lặp lại danh mục.
- [x] Bản địa hóa toàn bộ chữ cố định của trang Music VI/EN/ZH; không để Anh–Việt trộn trong
  cùng giao diện.
- [x] Đưa ba lối sáng tác hiện có lên trước, giữ trạng thái chưa khả dụng đúng
  sự thật; thư viện/tệp âm thanh đang dùng được đặt sau.
- [x] Bỏ thẻ trùng và mọi tuyên bố “Stereo 320k”, “Royalty-Free”, chuẩn phòng
  thu hoặc bản quyền thương mại chưa có căn cứ; chỉ giữ số đếm đích đến duy
  nhất nếu tính từ route thực.
- [x] Rà lại màn hình 375×812 và 1440×900 ở hai giao diện sáng/tối; màu xanh–teal,
  12/12 trường hợp, không tràn ngang/lỗi route, sáu đường dẫn đúng; tương phản
  chữ tối thiểu 4.635:1 sáng / 4.812:1 tối.
- [x] Không gửi form sáng tác, không tạo nhạc/âm thanh, không gọi provider,
  không sửa route/engine/ví; QA chỉ kiểm tra phần trình bày.
- [ ] Sửa locale dùng chung: ảnh EN/ZH vẫn thấy tiếng Việt ở thanh điều hướng/
  thanh công cụ; đây là lỗi shared shell, chưa nằm trong Music slice.
- [ ] Rà vị trí nút nổi trợ lý/cài ứng dụng và cảnh báo ViewTransition trong
  checkpoint shared shell/motion; không tự vá bằng CSS cục bộ của Music.
- [ ] Ghi nhận QA nền: 23 Python contract đạt; một bài cũ
  `test_library_routes_do_not_fall_back_to_generic_assets_or_audio_execution`
  lỗi vì đòi nhánh `/assets` legacy. `integration.js` và file test trùng hệt
  `origin/main`, nên không tính là hồi quy; chưa sửa test ngoài phạm vi.
- Bằng chứng ảnh/JSON: `../../qa/20261007-video-uiux/music-hub-ui-closeout-20261008/`.
- Spec: `docs/superpowers/specs/2026-10-08-music-hub-ui-closeout.md`.
- Baseline: `../../qa/20261007-video-uiux/music-hub-audit-20261008/` (12/12).
- `PROVIDER_CALLS=0 WALLET_MUTATIONS=0 PRODUCTION_DATA_MUTATIONS=0`.

## SUBDUB SINGLE-SCREEN UI — 2026-10-08

**SPEC_ID:** `SUBDUB-SINGLE-SCREEN-UI-20261008` · **STATUS:** `MERGED_CODE_RELEASE_CLOSED_LOCKED_DEPLOY_NOT_PERFORMED`.

Current closeout: PR #619 MERGED at `dee0ac4ccaaf2cb3ebe147ab217e85ec419bec4c`,
candidate `fb7ce0175be8be0a6189ac9e99a957a63423591d`; both trees
`841cfe730d45b59e1e71cc85d14fe2239dcfd9af` match exactly. PR CI `37755956582`
and main CI `37770140237` SUCCESS. GitHub description records ĐÓNG/KHÓA;
do not reopen or edit SubDub product code. Deploy and authenticated live remain
separate open gates. The earlier intermediate CI/HEAD notes below are historical.
Video checkpoint PR #616 is already recorded merged/deployed. Keep this slice
strictly to the customer presentation layer; the media engine and route
integration remain outside this UI/UX work.

**Exact tested code snapshot:** `e4070e3bf6710be1e5388c12e20800aae0ee5ea3`,
on branch `fix/subdub-ui-closeout-20261008` based on current `origin/main`
`e70175a5f8b4d30bdf99de939b80d2de2e54ee18`. The later local commit only
refreshes Web migration provenance and release documentation. PR #619 is open;
its exact current HEAD `7203a61e7c2c9c7bd25fde42f4aca5b895eb11eb` has a green
CI run. Merge, deployment, and production runtime readback remain pending.

- [x] Confirm the current four lanes and guarded source/price/run gates from
  `renderSubDubHub` and the canonical SubDub authority report.
- [x] Record current gaps: mode changes reload `/subdub`; no independent
  original/dubbed level controls; empty state says “Preparing”; `zh` falls back
  to Vietnamese; current tracked screenshots predate this source by months.
- [x] S1: four accessible mode choices switch the visible configuration in one
  screen and keep the selected mode/review summary aligned.
- [x] S2: separate local-only original and dubbed audio levels; no request,
  persistence, upload, quote, task, output, or wallet effect.
- [x] S3: honest empty report, complete VI/EN/ZH copy, preserved blue–teal
  theme, keyboard/touch support, 360px no-overflow and contrast checks.
- [x] Renderer/handler contracts 9/9; Voice/Music/SubDub regression 61/61;
  existing Python SubDub UI contract 9/9; JS syntax and diff checks pass.
- [x] Actual Portal template, JavaScript handlers, i18n, theme and motion in QA:
  12 locale/theme/viewport cases, 48 mode changes with Enter and click/touch.
  Exactly one panel, preserved query and independent local volume values;
  no action event, request, runtime error, failed resource, duplicate ID or
  horizontal overflow. Minimum text 5.23:1, boundary 3.51:1, target height 44px.
- [x] Saved 48 screenshots and source hashes in
  `../../qa/20261007-video-uiux/subdub-shell-verified-20261008/browser-review.json`.
  Initial incomplete-wrapper images are superseded.
- [x] Rechecked exact snapshot `e4070e3`: 12 configurations, 48 local mode
  changes, text 5.23:1, control boundary 3.61:1, target 44px; no request or
  action event. Exact evidence: `../../qa/qa/subdub-exact-e4070e3/browser-review.json`.
- [x] Re-ran exact UI contracts on this snapshot: Node renderer 9/9,
  Python UI contract 9/9, JavaScript syntax and `git diff --check` pass.
- [x] Initial PR CI run `37751231194` stopped before product tests because
  committed migration Web provenance still described an older source fingerprint.
  Refreshed only Web provenance from the final clean branch and verified it locally;
  current fingerprint is `2f666de233f59299528546fb04bf87d45a0c9a8d3e0906630a1fdb0f016db746`.
- [x] Pushed one SubDub-only branch and opened PR #619; closed PR #617 (Voice),
  #618 (Music), and #616 (Video) were not reused or reopened.
- [x] Fresh PR CI run `37752312011` passed on HEAD
  `7203a61e7c2c9c7bd25fde42f4aca5b895eb11eb`: migration evidence, Python compile,
  JavaScript syntax, bounded Web contracts, browser verification/runtime assertions,
  evidence upload, and diff whitespace checks all succeeded. PR #619 is mergeable;
  merge remained pending at that HEAD. Deployment and production readback remain separately gated.
- [ ] Follow-up run `37754429472` on documentation-only HEAD
  `107f8180421473a1711d89a583ee3fc76e432949` failed at migration evidence before
  product tests: the checklist/state update changed the eligible source fingerprint
  from recorded `2f666de233f5…` to current `ee5cbdd4cbda…`. Refresh only Web
  provenance after the final documentation update, verify locally, and require a
  fresh green PR run. No product test ran in the failed attempt; do not merge yet.
- [x] Recorded the failure cause in commit `845cab9` and confirmed the official
  clean-tree Web refresh plus local verifier pass on that intermediate tree
  (fingerprint `1ab5ba0082010393612012980580d46e2c512b97a41f38cc7034d617a606adf8`).
  This is historical/intermediate evidence, not the final fingerprint after this
  checklist update. The current exact-HEAD CI result is authoritative on PR #619;
  merge only when that check is green. Deployment remains separately gated.
  Voice/Music/Video product blocks are CLOSED/LOCKED.
- [ ] Shared shell locale/floating controls and whole-site motion remain open;
  QA here proves SubDub content only. `integration.js` was excluded from the
  isolated fixture; no execution, signed-session or real-output claim.
- Spec: `docs/superpowers/specs/2026-10-08-subdub-single-screen-ui.md`.
- State: `.agents/state/WEBAPP-SUBDUB-HUB-UI-20261008.yaml`.
- `PROVIDER_CALLS=0 WALLET_MUTATIONS=0 PRODUCTION_DATA_MUTATIONS=0`.

---

**Hệ sinh thái:** TOAN AAS Web App & Admin ERP  
**Runtime Target:** tg.toanaas.vn (/opt/toanaas/webapp)  
**Historical ERP baseline SHA (not current runtime verification):** 03325cf577de4fd090abea9088c8980a6a028e29
**Tiêu chuẩn vận hành:** owner-governed-codex & locked-focus-engineering  
**Quy tắc:** Làm tuần tự từng SPEC, không làm PR khổng lồ, soi lại checklist này mỗi khi bắt đầu và kết thúc một SPEC mới.

---

## BẢNG BẢO VỆ KHỐI LƯỢNG ĐÃ ĐẠT (CANONICAL PROTECTED WORK)

> [!IMPORTANT]
> Tuyệt đối KHÔNG tái cấu trúc (refactor/rewrite) các khối sau nếu không có bằng chứng lỗi ĐỎ (RED evidence) mới:
> 1. PR #437 Admin IA consolidation (Cấu trúc 7 nhóm, 10 primary navigation links, 38 secondary tabs).
> 2. Portal shell scroll ownership (.portal-workspace sở hữu cuộn chính, .portal-sidebar độc lập, không desync).
> 3. Semantic Light/Dark token architecture (portal-theme.css, Obsidian palette, không dùng màu ngọc lam đục).
> 4. Phân định biên giới xác thực 3 tầng RBAC (support_staff, web_local_admin, canonical_admin).
> 5. Chốt chặn an toàn bất biến ví tiền: Web App không mutate ví trực tiếp (WALLET_MUTATIONS=0).
> 6. Robustness Clean Envelope HTTP 200 của Reliability (trả về trạng thái availability có cấu trúc, không sập 503).

---

## NGUYÊN TẮC BẤT BIẾN TOÀN CỤC (GLOBAL INVARIANTS)

1. ZERO != UNKNOWN: Số 0 là dữ liệu đo được; chưa có dữ liệu phải hiển thị '-' hoặc 'Không khả dụng'.
2. HTTP 200 != business success: Phản hồi 200 với phong bì rỗng/lỗi upstream không được coi là hoàn thành.
3. EMPTY != ERROR: Dữ liệu sạch 0 bản ghi khác hoàn toàn với lỗi truy vấn hay sập kết nối.
4. DEPLOYED != LIVE_PROVEN: Code đã deploy lên VPS chưa đồng nghĩa là đã chứng minh chạy sống qua E2E.
5. UI visibility != server authorization: Nút bấm nhìn thấy trên giao diện không có nghĩa là server đã cấp quyền.
6. Web App must not become wallet authority: Web App chỉ là Read-Only / Draft initiator; Bot Core là thẩm quyền ví tối cao.
7. No production fake KPI: Tuyệt đối không dùng số liệu giả mạo trên dashboard quản trị.
8. No demo fallback presented as production data: Không hiển thị dữ liệu demo giả làm dữ liệu vận hành thật.
9. No cross-database synchronization without explicit authority map: Cấm sync DB khi chưa chốt thẩm quyền (SPEC-01).
10. Historical routes must remain compatible: 100% routes cũ phải có redirect hoặc canonical subview tương ứng.
11. Every write must have auth + validation + audit + idempotency: Mọi hành động ghi phải có kiểm tra quyền, validate, ghi nhật ký và chống trùng lặp.
12. No ENV/security/DB/wallet mutation without required Owner gate: Cấm tự ý can thiệp các chốt chặn an toàn của Owner.

---

## MA TRẬN TIẾN ĐỘ 19 SPECS (MASTER CHECKLIST)

| SPEC ID | Tên SPEC | Giai đoạn | Mục tiêu cốt lõi | Trạng thái |
|---|---|---|---|:---:|
| **SPEC-00** | Canonical Truth & Acceptance Contracts | PHASE A | Khóa sự thật, sửa báo cáo LIVE=NO/PARTIAL, chuẩn hóa ma trận hợp đồng 54 functions | 🟢 COMPLETED |
| **SPEC-01** | Data Authority & Cross-System Boundary | PHASE A | Thiết lập bản đồ thẩm quyền cho 36 thực thể, khóa 4 corrections thẩm quyền | 🟢 PASS_WITH_CONTRACT_CORRECTIONS |
| **SPEC-02** | ERP Dashboard Truth | PHASE B | Dashboard chỉ lấy số liệu thật, xóa tỷ lệ %, xử lý UNKNOWN/UNAVAILABLE | 🟢 COMPLETED |
| **SPEC-03** | Monitoring & Reliability Truth | PHASE B | Telemetry sống, tách bạch HTTP 200 with data unavailable khỏi trạng thái xanh | 🟢 COMPLETED |
| **SPEC-04** | Customer / CRM / Support | PHASE B | Hợp nhất 1 nguồn chân lý khách hàng, xóa overlap lead, đồng bộ ticket | 🟢 COMPLETED |
| **SPEC-05** | Operations / Jobs / Handoffs | PHASE B | Đồng nhất ngôn ngữ vận hành, job lỗi có runbook ngữ cảnh, hàng đợi chuẩn | 🟢 COMPLETED |
| **SPEC-06** | Finance Read Model | PHASE B | Read model từ nguồn chân lý, nêu rõ phạm vi Doanh thu (WEB_ONLY, BOT_ONLY) | 🟢 COMPLETED |
| **SPEC-07** | Topup / Payment Write Safety | PHASE C | Chứng minh biên giới ghi nạp tiền: CSRF, Idempotency, Audit, không mutate ví | 🟢 COMPLETED |
| **SPEC-08** | Security / Password / RBAC | PHASE C | Xác nhận mật khẩu hiện tại khi đổi pass, vòng đời session, khóa quyền server | ⚪ PENDING |
| **SPEC-09** | Audit / Reports | PHASE C | Khai thác bộ lọc backend đã có (Date range, actor, pagination) lên giao diện UI | ⚪ PENDING |
| **SPEC-10** | Remove Fake / Placeholder Operational Data | PHASE D | Xóa sạch số liệu hardcoded tại /admin/finance/planning, /admin/growth, /admin/trends | ⚪ PENDING |
| **SPEC-11** | Content / Growth / Planning Completion | PHASE D | Gán đúng nhãn cho từng module: WORKING, READ_ONLY_REFERENCE, EMPTY_VALID, NOT_AVAILABLE | ⚪ PENDING |
| **SPEC-12** | API Error-State Semantics | PHASE D | Phân tách 7 trạng thái phản hồi API: Success data, empty, unavailable, 403, validation, upstream, 500 | ⚪ PENDING |
| **SPEC-13** | UI Density / Page Simplification | PHASE E | Tối ưu mật độ thông tin, dọn bớt chữ giới thiệu thừa, tăng giá trị nghiệp vụ trên màn hình | ⚪ PENDING |
| **SPEC-14** | Responsive / Accessibility / Real Browser E2E | PHASE E | Kiểm thử trình duyệt thật trên 5 viewports (1920, 1440, 1280, 768, 375 mobile) | ⚪ PENDING |
| **SPEC-15** | Cross-System Projection / Sync | PHASE F | Kiến trúc projection dữ liệu 1 chiều có kiểm soát từ Bot Core về Web ERP | ⚪ PENDING |
| **SPEC-16** | Observability / Auditability | PHASE F | Tương quan request_id, actor, domain, action, chống lộ bí mật và PII | ⚪ PENDING |
| **SPEC-17** | Production Live Acceptance | PHASE G | Nghiệm thu từng domain trên môi trường production thực tế | ⚪ PENDING |
| **SPEC-18** | Dead Code / Consolidation Cleanup | PHASE H | Dọn dẹp code rác, route cũ không dùng sau khi toàn bộ hành vi đã xanh | ⚪ PENDING |

---

## BẢNG CHỐT CHẶN AN TOÀN BẮT BUỘC CỦA OWNER (OWNER GATES)

- [ ] **GATE-A**: Thay đổi ENV TOANAAS_OPS_AUTOPILOT_ENABLED (Cần lệnh duyệt rõ ràng từ Owner).
- [ ] **GATE-B**: Bất kỳ kiến trúc đồng bộ dữ liệu Web ↔ Bot nào có quyền ghi (Cần Owner phê duyệt thiết kế).
- [ ] **GATE-C**: Bất kỳ migration schema nào hoặc sửa đổi DB production (Cấm tự ý thực hiện).
- [ ] **GATE-D**: Bất kỳ can thiệp nào vào logic thanh toán hoặc quyết toán ví tiền (Bất biến).
- [ ] **GATE-E**: Bất kỳ thay đổi nào đối với chính sách phân quyền RBAC/Security (Cần Owner duyệt).
- [ ] **GATE-F**: Bất kỳ thao tác dọn dẹp dữ liệu (purge demo) có tính phá hủy (Cấm tự ý chạy).
- [ ] **GATE-G**: Bất kỳ tích hợp nhà cung cấp hoặc secret/API key mới nào (Cần Owner cung cấp).
- [ ] **GATE-H**: Deploy/restart dịch vụ khi chưa có yêu cầu mã nguồn bắt buộc.

---

## BOT → WEB APP FUNCTION PARITY REVIEW — 2026-10-09 (Git recheck 2026-10-10)

**SPEC_ID:** `WEBAPP-BOT-FUNCTION-PARITY-REBASELINE-20261009`
**STATUS:** `READ_ONLY_RECHECK_PARTIAL_BOT_BASELINE_NOT_LOCKED_2026-10-10_PLAN_READY_IMPLEMENTATION_NOT_STARTED`
**Plan/checklist chi tiết:** `docs/superpowers/plans/2026-10-09-bot-web-function-parity-replan.md`.
**Ma trận capability/spec:** `docs/superpowers/specs/2026-10-09-bot-web-capability-closeout.md`.

- [x] Đối chiếu chỉ-đọc các hồ sơ UI Image/Video/Voice/Music/SubDub; các nhãn
  đóng/khóa chỉ thuộc lát cắt giao diện, không chứng minh engine hoặc artifact.
- [x] Quét inventory tĩnh trên nguồn Bot đọc được và cây Web local: 7.633
  product-action mapping; bề mặt Web tĩnh 37,56%; 1.923 record cần disposition,
  353 chưa có route Web; runtime equivalence `0% / NOT_STATICALLY_VERIFIABLE`.
- [x] Lần audit trước ghi nhận Bot branch `fix/p0-subdub-smart-synth-adapter-signature-r1`,
  HEAD `ae85e84f27f3f5e09c4e05667a34355a758c8a8a`; 7 tracked file sửa và 24
  untracked entry. Giữ đây là snapshot lịch sử, không dọn/stash/reset, không lấy
  phần chưa commit làm baseline chuẩn. Web HEAD `17b9494…` đang dirty.
- [ ] Quét Git HEAD Bot và dirty overlay thành hai lớp có fingerprint riêng; xuất
  ledger từng action, đối soát tổng record và không để `unknown/unreviewed`.
- [ ] Đóng workflow/report Admin contract; lần lượt Voice → Music → SubDub →
  Image → nhóm phi Video (Free Tools, Notes/Memory, Documents/OCR/Translation,
  Content/Autopost, Projects/Assets/Support/Membership/Admin) → Video cuối.
- [ ] Giữ WA-35/WA-36 OPEN; không tuyên bố toàn site UI/UX/motion hoàn thiện từ
  test của một route. Chat này không sửa route/engine; chỉ làm trong phạm vi
  UI/UX và motion của goal hiện hành.
- [x] 2026-10-10: thêm cổng “không sót” theo yêu cầu Owner: Music nền/bài có
  lời; Image tạo/sửa AI/chỉnh thủ công; Voice mặc định/saved/clone; SubDub bốn
  mode một màn; toàn bộ catalog Video với AI editor và manual editor tách riêng;
  Free Tools, Notes/Memory, tài liệu/OCR/dịch, Content/Autopost và mọi family
  Bot khác phải có dòng trong ledger. Chi tiết ở plan/spec liên kết phía trên.
- [x] Chạy lại 7 bộ kiểm tra trình bày Music/Voice/Image/SubDub trên Web candidate
  `17b9494392cc063e8f9d0f39974da2569009b23d` + dirty overlay: `110 pass, 0 fail`.
  Đây là UI/locale/guard regression; không chứng minh job/provider/media output.
- [ ] Cổng inventory vẫn mở: chốt Bot Git HEAD và dirty overlay riêng, reconcile
  mọi command/callback/template/handler với action ledger, `UNKNOWN=0`, rồi mới
  được tuyên bố hoàn tất rà soát đủ chức năng.
- [x] Recheck metadata Git ở tiến trình hiện tại: checkout Bot đọc được là branch
  `feature/p0-webapp-copyfast1-core-bridge`, HEAD
  `32d6d1bfbc8040b0632a44e6a9326ed568cb1a59`, clean; `ae85…` tồn tại trong object
  database nhưng không phải HEAD/ancestor. Comparator riêng detached HEAD
  `6476f20bdd9f8728a5db0b1d62a245b0d612aea8`, clean, không chứa `ae85…`. Chưa có
  bằng chứng hai checkout này là Bot main/deployed source.
- [ ] Chọn và khóa Bot source canonical bằng Git SHA; không lấy snapshot 7.633
  mapping/fingerprint cũ làm kết quả tái lập của SHA đó.
- [ ] Chạy static inventory baseline `ae85…` bằng auditor hiện hữu: auditor fail
  closed vì Git archive vượt `MAX_BASELINE_ARCHIVE_BYTES=64 MiB`. Không nới trần
  mù quáng; thiết kế đọc allowlist source blobs với giới hạn từng file/tổng,
  loại trừ `.env`, data/attachments và giữ path-traversal/secret guards.
- [ ] Tái lập inventory riêng cho Bot HEAD và dirty overlay, reconcile mọi record
  thành action ledger và `UNKNOWN/UNREVIEWED=0`.
- [x] Đối chiếu `bot_to_web_parity_matrix.json`: file có 39 mục capability, 39/39
  `OPTIMIZED_FLOW`, `100%` trong phạm vi hẹp; không phải danh mục đầy đủ của Bot.
- [x] Chạy lại 7 bộ UI/locale/guard Music/Voice/Image/SubDub từ repo root: `110
  pass, 0 fail`; không kiểm provider/job/artifact/live.
- [ ] Trước khi giao builder, chẻ parent wave thành spec con một capability/một
  phiếu: Voice 3 lane, Music 2, SubDub 4 mode, Image 3 lane; các tính năng khác
  và từng sản phẩm Video lấy số lượng từ ledger. Editor AI/manual luôn tách.
- [ ] Nghiệm thu từng action theo luồng input → quyền/owner → preflight/quote →
  confirm idempotent → job → báo cáo Admin/khách → artifact thật. Với giao diện:
  giữ xanh–teal, bố cục dọc rõ ràng, VI/EN/ZH sạch, mobile/contrast/focus/motion;
  test live/provider cần gate riêng.
- [x] 2026-10-10: browser kiểm tra riêng `portal-motion.js` trên Chrome headless
  (Playwright Node đóng gói, fixture cục bộ): `reads=0`, `readsAfterWrite=0`,
  3 nhóm đầu hiển thị và nhóm dưới màn hình hiện sau cuộn;
  `WORKSPACE_MOTION_LAYOUT_BATCHING_PASS`. Edge thoát sớm; Python runtime thiếu
  pytest/Playwright. Đây chỉ là regression của motion component, không phải app
  đã hydrate hay full-route/performance PASS; WA-35/WA-36 vẫn OPEN. Reduced-motion
  fixture ở `390×844` cũng xác nhận cả 3 nhóm luôn hiện, `pending=0`, opacity `1`:
  `WORKSPACE_MOTION_REDUCED_MOTION_VISIBLE_PASS`.
- **Lưu ý provenance:** mục checklist này nằm trong `reports/audit`, là nguồn
  được fingerprint Web tính đến. Fingerprint `8eef38f8…` là kết quả sau lần cập nhật
  checklist trước đó; lần chỉnh tài liệu hiện tại làm fingerprint đó cũ. Cần tính
  lại Web provenance sau khi tài liệu chốt và trước PR. Không cập nhật báo cáo sinh
  tự động trong lượt rà này.
- `PROVIDER_CALLS=0 WALLET_MUTATIONS=0 PRODUCTION_DATA_MUTATIONS=0`.
