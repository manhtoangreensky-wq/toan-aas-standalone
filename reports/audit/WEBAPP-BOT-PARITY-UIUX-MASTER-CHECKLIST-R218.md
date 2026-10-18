# R218 — Checklist UI/UX toàn bộ sản phẩm WebApp

Ngày 2026-10-18. WIP_P1_VOICE_VAULT_HANDOFF_GUARD_VERIFIED_LOCAL. Source Bot được đọc-only; production chưa kiểm.
Không thay goal tổng; checklist này bổ sung và nối tiếp công việc R217 còn dở.
Từ ngày này, bảng dưới là completion ledger R218; lịch sử R217 giữ nguyên bằng chứng cũ.
Đối soát toàn bộ lịch sử trước R217 nằm tại
`reports/audit/WEBAPP-HISTORICAL-CHECKLIST-CROSSWALK-R218.md`; không dùng tài liệu cũ
để suy diễn PASS.

## Quy ước

[x] Đủ evidence đúng phạm vi. [~] Một phần, chưa đóng. [ ] Chưa thực thi/chưa chứng minh.
[!] Có gap cụ thể. [→] Kỹ thuật giữ cuối, đợi lệnh sau UI/motion.
Bất kỳ mục không browser evidence không gọi là UX/LIVE hoàn thiện.

## Reconciliation R217 + R218 + Owner parity matrix

R217 là lịch sử/comparator, R218 là ledger thực thi hiện hành; không có mục nào của
R217 bị xóa. Bảng dưới là cổng đối soát với ma trận Owner mới nhất, để không bỏ sót
nhóm hoặc nhầm một thẻ điều hướng là một tính năng đã chạy:

| Nhóm Owner | Inventory Bot | Ledger/spec Web | Trạng thái phải theo dõi |
|---|---|---|---|
| Voice | B01–B04 | P1 VO-01..13 / R218-02 | TTS, STT, mặc định nam/nữ, kho/clone, consent, nghe thử, đặt mặc định, đổi tên/xóa, speed/volume, quote và tái sử dụng |
| Music/SFX | B05–B07 | P2 MU-01..12 / R218-03 | Nhạc nền/bài hát, style/lyrics, nam/nữ/song ca/auto, 3 gói/3 gợi ý, kho/SFX, nghe/tải/lưu/dùng lại, tiến trình và giao tệp |
| SubDub | B08–B12 | P3 SD-01..21 / R218-04 | Bốn mode cùng workspace, nguồn có/chưa có phụ đề, ngôn ngữ, default/saved/custom voice, Auto 2, Auto Multi 3–8, Smart Multi, mix, vị trí, báo giá, tiến trình và report |
| Image | B13–B15 | P4 IM-01..10 / R218-05 | Tạo ảnh/reference/prompt, mục tiêu/chủ thể/style/tỷ lệ, biến thể, AI edit, manual edit, chữ/logo, trước–sau, lịch sử và handoff Video |
| Product Video + Video Editor | B16–B20 | V0 VI-01..15 / R218-09 | 32 profile, trend/script/frame/self-shot/storyboard/series, AI/manual edit, timeline, addon, giọng/nhạc/phụ đề/logo và report |
| Dịch/Content/Free/Utilities | B21–B24 | P5 UT-01..04 / R218-06 | Dịch text/voice/file, content variants, prompt/library, QR/avatar/tỷ giá/thời tiết/downloader, copy/save/version và state |
| Memory/Documents/Assets/Projects | B25–B27 | P5 UT-05..08 / R218-06/07 | Ghi chú/reminder, PDF, kho tệp, upload/list/preview/download/quota, project/draft/version/workboard và source→result lineage |
| AutoPost | B28–B30 | P6 AP-01..05 / R218-07 | Bảy nguồn, brand/plan, kênh, lịch/hàng đợi/lịch sử, affiliate/metrics/ads, review/publish/recovery |
| Support/Account/Help | B31–B33 | P6 SP-01..02 + AC-01..02 | Trung tâm hỗ trợ, ticket/attachment/reply, profile/locale/session, gói/giá/nạp tiền/pending, Chat Pro/feedback/context help |
| Admin/internal app | B34 | A0 AD-01..05 / R218-08 | Quyền theo vai trò, bảng/biểu đồ/chi tiết, request→job→asset→report, approval UI, Web/app cùng record và quyền |

- [x] Mỗi hàng đã có mã inventory và wave/spec; không có nhóm Owner nào nằm ngoài
  B01–B34.
- [x] Đã lập sổ đối soát lịch sử cho 365 tệp plan/spec/audit/state và 433 dòng
  checkbox cũ; `unclassified source = 0`. Đây là bằng chứng không mất nguồn tài liệu,
  không phải bằng chứng mọi control đã chạy thật.
- [~] Các plan/spec trước R217 trước đây chỉ được nối ở cấp nhóm; semantic review từng
  dòng vẫn phải thực hiện trong wave đích. Yêu cầu mới phát hiện phải thêm ID vào ledger
  trước khi sửa, không được bỏ qua.
- [ ] Chỉ đóng một hàng khi có renderer/interaction + browser/AX evidence tương ứng;
  runtime, provider, wallet, publish và LIVE vẫn giữ cổng riêng.
- [ ] Các lỗi mới phát hiện được thêm vào đúng hàng và đúng thứ tự, không mở nhánh
  ngoài ledger.

### Đối soát file/spec R217 → R218

Các tài liệu R217 không bị xoá hoặc thay thế âm thầm. Bảng này là đường truy vết
từng file sang wave hiện hành; nếu một mục chưa có evidence tương ứng thì vẫn giữ
`[~]`/`[ ]` ở wave đích, không được suy diễn là đã hoàn tất.

| Tài liệu R217 | Wave/ledger R218 tiếp nhận | Disposition |
|---|---|---|
| `reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-20261010.md` | C0, F0, Q0/M0/L0 | Giữ làm lịch sử/comparator; không xoá mục cũ |
| `2026-10-16-r217-00-evidence-ledger.md` | C0, Q0/L0 | Giữ evidence và quy tắc không suy diễn |
| `2026-10-16-r217-01-shell-responsive-foundation.md` | F0, Q0 | Shell, màu, type, responsive, touch và overflow |
| `2026-10-16-r217-02-locale-purity.md` | F0, P5/P6, Q0 | VI/EN/ZH và dữ liệu động không dịch |
| `2026-10-16-r217-03-auth-accessibility.md` | F0, AC-01, Q0/M0 | Auth lifecycle, focus, keyboard, a11y |
| `2026-10-16-r217-04-image-lane.md` | P4 | Image create/reference/AI edit/manual edit |
| `2026-10-16-r217-05-voice-lane.md` | P1 | TTS/STT, Voice Vault, clone, preview và reuse |
| `2026-10-16-r217-06-music-lane.md` | P2 | Music/SFX, tier, gợi ý, player và delivery |
| `2026-10-16-r217-07-subdub-lane.md` | P3 | Bốn mode, voice lane, Smart Multi, mix và report |
| `2026-10-16-r217-08-product-video-lane.md` | V0 | Product Video, profile, addon, report và editor |
| `2026-10-16-r217-09-admin-customer-visibility.md` | A0, P6 | Customer→Admin record, RBAC presentation và report |
| `2026-10-16-r217-09a-content-workboard-free-tools.md` | P5/P6 | Content, Free, Projects và Workboard |
| `2026-10-16-r217-10-motion-performance.md` | M0 | Motion lifecycle, compositor, reduced-motion, trace |
| `2026-10-16-r217-11-authenticated-qa-matrix.md` | Q0/L0 | Browser/AX matrix và runtime evidence |
| `2026-10-16-r217-12-live-readonly-recheck.md` | L0 | Read-only live recheck, SHA/DOM/screenshot |
| `2026-10-16-r217-13-deferred-technical-register.md` | T0 | Giữ cuối, chỉ lập register sau UI/UX/motion |

## C0 — Bảo toàn / chốt WIP

- [x] Root menu Bot và nhóm sản phẩm ghi tại WEBAPP-BOT-PRODUCT-INVENTORY-R218.md.
- [x] Đọc menu/handler/catalog chính cho Voice/Music/SubDub/Image/Video và tiện ích.
- [~] Các callback động và catalog runtime cần mapping control chi tiết, chưa đủ để
  tuyên bố audit mọi nút hoàn tất.
- [~] #653 auth responsive/contrast: CI source cũ xanh, delivery chưa đóng.
- [x] #654 candidate source đã push; SubDub lane patch đạt kiểm thử local và CI/browser trên HEAD `148be4f6ec18e3c7fe3abfee8ca8a34ee1a5d099`.
- [x] Ghi current SHA/checks #653/#654 và disposition trước mở wave mới: Verify Web App + Authenticated WebApp QA SUCCESS, run `39101124230`, route matrix `456/456`.
- [x] Review #654 hidden field, default checked, duplicate selector, library link,
  guard blanket, locale, âm lượng dub max 100: đã sửa và khóa bằng 13 kiểm thử mục tiêu;
  CI/browser trên commit mới đã đạt route/render matrix.
- [x] Bản plan/checklist/spec nền R218 đã lên GitHub; provenance được refresh cho HEAD mới và
  candidate gate đã xanh ở run `39101124230`.
- [~] Checkpoint AutoPost cùng tài liệu vận hành và bộ case Tester đã được rà soát, nằm trong
  đợt push hiện tại; cần CI/browser/AX riêng trước khi chuyển thành bằng chứng delivery.
- [x] VO-04/VO-05 Voice controls đã có candidate local `814b70cee2b6f4d2d1d2db23c903bfc0ca3d50bd`:
  tốc độ số `0,1–2,0` với mặc định `1,0` và 3 preset; âm lượng slider `0–200` đồng bộ
  với đúng một field số. Targeted `3/3`, Voice regression `97/97`, full Node `530/530`,
  `node --check` và `git diff --check` đều đạt; chưa có CI/live/runtime execution evidence.
- [x] MU-00 Music control-level local đã khóa: `/music/create` và `/music/song` dùng một
  workspace dọc gồm 4 bước, 3 tier và 3 ô phương án guarded; không còn provider badge, giá,
  player, MP3 hoặc download giả. Form song giữ `brief/tier/mode/vocal_mode/lyrics/song_length_mode/
  duration_seconds`; route nền cô lập các field song-only; trạng thái thiếu capability không tự
  mở field. Catalogue `musicProduct.*` cân bằng VI/EN/ZH; test mới `7/7`, focused Music+Voice
  `19/19`, focused Music hub/prompt/library `25/25`, full Node `537/537`, syntax và diff-check đạt.
  Đây chỉ là UI/control-level local; quote, confirm, generation, player/download/save/reuse,
  editor, delivery và browser/CI/live vẫn mở.

- [~] UT-02/UT-03/UT-05/UT-08 control-level đã được rà soát bằng bộ test cố định; riêng
  Content Prompt Pack đã loại các chuỗi tiếng Anh giao diện khỏi bản VI và tách catalogue
  VI/EN/ZH. Runtime tạo nội dung, lưu, phiên bản, dữ liệu thật, browser và live vẫn mở.
- [~] UT-07 Assets control-level đã khóa bằng `tests/assets-product-controls.test.mjs`:
  workspace owner-scoped, upload 25 MB/allowlist, gắn Project, lọc active/archived/all,
  phân trang, download chỉ active, lifecycle redaction, archive/restore theo revision và
  các trạng thái guarded/failed. Test riêng `5/5`, full Node `558/558`; bytes thật,
  preview, capability server, browser/AX, delivery và LIVE vẫn mở.

## F0 — Shared contract R218-00/01

- [ ] Mỗi control có ID/source/label/position/input/default/guard/action/back/states/evidence.
- [ ] Typography/spacing/palette/contrast/touch/heading chuẩn, CTA chính rõ.
- [ ] Local config chỉnh được khi không sinh job; execution gate từ server.
- [ ] Back/mode change/hydration/reload giữ draft và focus đúng phiên.
- [ ] Upload/preview/result/history/recovery và cross-product picker thống nhất.
- [ ] Account change/logout xóa stale private data; UI quyền theo manifest thật.

## P1 — Voice R218-02 (VO-01..13)

- [ ] TTS/STT/default/saved/clone được bố trí trong workspace.
- [ ] Default nữ/nam distinct hoặc fallback một default theo capability.
- [~] Nội dung/đếm từ/speed 0.1–2.0/volume 0–200: control và giá trị mặc định đã khóa
  bằng test `tests/voice-controls-contract.test.mjs`; cảnh báo volume 0 và quote stale
  vẫn chờ contract/runtime evidence.
- [ ] Quote/expiry/confirm/progress/player/download/report/retry đúng state.
- [ ] Kho giọng search/page/status/default/preview/rename/delete/reuse.
- [~] VO-02/VO-09/VO-10/VO-13: picker nam/nữ, Voice Vault owner-scoped và route handoff đã được khóa ở source bằng `tests/voice-selection-clone-contract.test.mjs` (4/4); quote, preview, rename/delete, runtime và browser/AX vẫn mở.
- [~] VO-11: clone consent/upload/tên tùy chọn tối đa 120 ký tự đã khớp bridge hiện hành; form nay có hướng dẫn guarded đủ 7 bước consent → sample → name → quote → preview → save → back, được khóa ở source bằng test clone `5/5`; xác nhận text, quote, preview, save/back và runtime vẫn mở.
- [~] Voice Vault dùng chung với SubDub/Video, owner scope/return draft. UI đã có vùng dùng lại dọc với link mở SubDub/Video và trạng thái quản lý hồ sơ rõ ràng; đổi tên/đặt mặc định/xóa/nghe thử vẫn khóa cho tới khi server trả capability owner-scoped, signed preview và handoff giữ draft có profile ID.
- [ ] Renderer/interaction + browser/AX/screenshots đạt, không provider calls.

## P2 — Music R218-03 (MU-01..12)

- [~] MU-00 control-level local đã khóa theo C0; các mục runtime và delivery dưới đây chưa đóng.
- [ ] Nhạc nền/Bài hát/Kho nhạc-SFX/Chỉnh nhạc; capability thật.
- [ ] Brief/style/lyrics/vocal nam/nữ/song ca/auto/3 tier, không mất draft.
- [ ] Ba gợi ý chọn/đổi/sửa; quote/confirm/review rõ.
- [ ] Player/tải/save/reuse/history/progress và generation vs delivery failure.
- [!] Hai bản kết quả là yêu cầu cần contract confirmation; parser nhiều track
  không chứng minh Bot đã giao đủ hai bản.
- [!] Editor nhạc Bot hiện guard; UI không giả có editor thực thi.
- [ ] Duration/half/full chỉ options reachable, không chép menu legacy làm authority.
- [ ] Renderer/interaction + browser/AX/screenshots đạt.

## P3 — SubDub R218-04 (SD-01..21)

- [x] Shell một trang/bốn tab, mode/query/keyboard và panel tại chỗ đã khóa bằng test presentation.
- [~] Source đã có lựa chọn “đã có/chưa có phụ đề”, bộ chọn tệp và trạng thái source rõ ràng;
  upload/preview/metadata/progress/cancel/replace/error vẫn chờ capability máy chủ.
- [~] Auto source mặc định tự nhận diện; target hiển thị catalog đầy đủ, Việt đứng trước rồi Anh/Trung;
  tìm kiếm runtime và giữ gốc/dịch theo DTO thật vẫn chưa có bằng chứng.
- [ ] Default Nữ/Nam; saved picker + custom Voice wizard, return đúng draft.
- [~] Auto 2, Auto Multi 3–8 và Smart Multi đã tách thành ba lane canonical riêng,
  mapping callback rõ; server capability/execution vẫn mở.
- [ ] Speaker map/preview/override chỉ khi có dữ liệu; ambiguous/review/fallback rõ.
- [~] Original audio toggle 0–100, dub 0–200 và number+slider; static dub max 200 đã có,
  number control/backend/browser evidence vẫn mở.
- [~] Subtitle position đã có đủ 7 slot cho các mode có phụ đề; format/mono-bilingual/original-translated
  source/review runtime vẫn mở.
- [ ] Quote/progress/result/report/download/recovery không giả.
- [~] Review candidate #654 theo spec mới: không còn count thẻ disabled là hoàn tất;
  lane selector/link/callback đã được kiểm thử static và CI/browser route/render; chưa có
  bằng chứng backend capability, upload, quote, job, result hoặc delivery.
- [ ] Renderer/interaction + browser/AX/screenshots đạt.

## P4 — Image R218-05 (IM-01..10)

- [~] Tạo nhanh/prompt từ ảnh/AI edit/manual đã có 4 mode dọc rõ trên `/image/create`;
  `prompt` nối `/image-studio`, `aiEdit` nối `/image/transform`, `manual` nối `/image/edit`.
  Đây mới là control-level projection; source/reference, AI runtime, upload, preview,
  before/after, quote, result và delivery vẫn chưa có bằng chứng.
- [ ] Reference goal/subject/style/ratio/negative prompt/3 biến thể.
- [ ] Tạo nhanh 5 gợi ý/tự nhập; 7 tier/watermark/quote/confirm.
- [ ] AI thêm/xóa/nền/màu/product/ratio/custom, phương án và readiness.
- [ ] Manual crop/pad/blur/pixel/text/logo/position/brightness/color/local upscale.
- [ ] Before-after/reset/history/save/reuse/Video, artifact readiness đúng.
- [ ] Renderer/interaction + browser/AX/screenshots đạt.

## P5/P6 — Các sản phẩm còn lại R218-06/07

- [~] UT-01 Dịch text/voice/file/two-way/source-target/start-stop/result. Control-level
  đã có workspace dọc ở `/subtitle-studio/new?intent=translation&pair=...`: nguồn
  tự nhận diện, catalog đích 21 ngôn ngữ, tìm kiếm cục bộ, giữ bản gốc, hai chiều,
  khu vực bắt đầu/dừng, kết quả và lịch sử; VI/EN/ZH riêng, panel không gửi API.
  Test `tests/translation-workspace-controls.test.mjs` đạt `4/4`, full Node đạt
  `548/548`. Capability xử lý thật, DTO, quote/confirm, tiến trình, kết quả,
  lịch sử, browser và live vẫn mở; không đánh dấu runtime parity.
- [~] UT-02 Content idea/caption/hashtag/hook/script/CTA đã có workspace/brief/detail và
  Prompt Pack với gợi ý, trạng thái rỗng, ranh giới xử lý, lưu vào Ghi chú và locale VI/EN/ZH;
  edit/save/version/handoff runtime chưa có bằng chứng.
- [~] UT-03 Free/prompt library/search/filter/copy/save/publish pack/quota đã có các projection
  giao diện và trạng thái guarded; `Content Prompt Pack` fixed chrome đã cân bằng VI/EN/ZH,
  không trộn tiếng Anh ở bản VI; quota/runtime/provider chưa chứng minh.
- [~] UT-04 QR/avatar/tỷ giá/thời tiết/downloader: `/free-tools` đã có 10 tab/panel
  accessible, giữ QR hiện có và bổ sung lane Ảnh đại diện AI, Tỷ giá & quy đổi Xu,
  Thời tiết, Tải video & media. Mỗi lane có input dọc, preview/result rỗng,
  quyền sử dụng hoặc nguồn dữ liệu, state guarded và nút thực thi khóa khi chưa có
  capability; VI/EN/ZH có catalogue riêng. Test `tests/free-tools-hub-presentation.test.mjs`
  đạt `5/5`, full Node đạt `549/549`; API ngoài, dữ liệu thật, refresh/stale/error
  runtime, downloader delivery, browser/AX và live vẫn mở.
- [~] UT-05 Notes create/list/search/detail/edit/reminder/delete confirmation đã có Memory
  Center/Reminder shell, locale và contract owner-scoped; dữ liệu thật, browser và live chưa
  chứng minh.
- [~] UT-06 Documents/PDF control-level đã khóa bằng `tests/documents-product-controls.test.mjs`:
  bảng một nơi, 9 workflow, nguồn Asset Vault, tách theo page range, gộp/ảnh→PDF tối đa
  8 ô theo thứ tự, tối ưu lossless, OCR/PDF→ảnh/Word, confirm, empty/guarded/result và
  tải chỉ khi `completed + download_ready`. Spec chi tiết tại
  `docs/superpowers/specs/2026-10-18-r218-06c-documents-product-controls.md`.
  Capability server, upload/preview/output/delivery, browser/AX và LIVE vẫn mở.
- [~] UT-07 Assets upload/list/filter/page/download/lifecycle/quota/privacy control-level
  đã khóa tại `docs/superpowers/specs/2026-10-18-r218-06d-assets-product-controls.md`;
  upload bytes thật, preview, quota/expiry do server công bố, browser/AX và delivery vẫn mở.
- [~] UT-08 Projects/Workboard task/dependency/status/assignee/dates/report đã có Project
  Center, Workboard dọc, checklist, lịch, lịch sử và trạng thái; browser fixture/runtime chưa
  chứng minh.
- [~] AP-01 AutoPost Hub đã khóa presentation bảy nguồn và source lineage ở `/publishing`; picker bytes/URL và capability server vẫn mở.
- [~] AP-02 AutoPost Hub đã có trình tự brand/content plan → draft/review/calendar bằng các handoff Web-native; edit/version thật vẫn mở.
- [~] AP-03 AutoPost Hub đã có lane platform/connection/expiry/target ở trạng thái guarded; OAuth và kết nối kênh chưa mở.
- [~] AP-04 AutoPost Hub đã có lane queue/published history/status/detail/cancel/review/recovery ở trạng thái guarded; chưa có receipt publish thật.
- [~] AP-05 AutoPost Hub đã có lane Affiliate/import/list/filter/ads/metrics ở trạng thái guarded; không hiển thị số liệu suy đoán.
- [~] AC-01 Profile/locale/session/security và stale data cleanup; control-level đã có
  test `tests/account-control-level-contract.test.mjs` đạt `6/6`, full Node đạt `574/574`;
  browser/AX, session runtime và live vẫn mở. Control ledger theo
  `docs/superpowers/specs/2026-10-18-r218-07c-account-controls.md` (AC-01A..E).
- [x] AC-01 locale subgate: cả ba block catalogue Account Security tiếng Việt
  (liên hệ/phiên, MFA/tình trạng và action/error) đã loại bỏ generic English, giữ
  nguyên tên riêng/acronym và placeholder; test riêng `2/2`, Account regression
  `11/11`, full Node mới nhất `574/574`. Đây chỉ là source-locale evidence;
  browser/AX, session runtime và control-level runtime vẫn chưa đóng AC-01.
- [~] AC-02 Packages/pricing/topup/history/detail/pending, không wallet mutation;
  control-level đã có `tests/account-billing-control-level-contract.test.mjs` đạt `5/5`,
  full Node mới nhất `579/579`; ví/lịch sử canonical, nạp thủ công bắt buộc method+amount
  trước QR, PayOS/catalog fail-closed và Admin handoff giữ request/confirmation boundary.
  Browser/AX, bytes/QR runtime, pending record thật, approval/credit và LIVE vẫn mở;
  control ledger theo `docs/superpowers/specs/2026-10-18-r218-07c-account-controls.md`
  (AC-02A..D). QR chỉ sau method+amount+readiness; approval/credit giữ T0.
- [~] SP-01 Support/ticket/attachments/replies/status/escalation/task refs đã khóa lát
  control-level bằng spec `docs/superpowers/specs/2026-10-18-r218-07b-support-center-controls.md`
  và test `tests/support-hub-product-controls.test.mjs` đạt `4/4`; full Node đạt
  `566/566`, syntax và `git diff --check` đạt. Capability server, dữ liệu thật,
  browser/AX và LIVE vẫn mở; không đánh dấu runtime parity.
- [ ] SP-02 Guide/Chat Pro/feedback/community, context help đúng sản phẩm.
- [ ] Mỗi nhóm renderer/interaction + browser evidence, không chỉ navigation.

## A0 — Admin / nội bộ R218-08

- [ ] AD-01 Sidebar dọc/module/search theo quyền; Owner đủ, role khác theo policy.
- [ ] AD-02 Tables/list/mobile cards/detail/charts/legend/filter/empty-state.
- [ ] AD-03 Customer→Admin request/job/asset/report/audit reference đúng record.
- [ ] AD-04 Approval/finance UI có reason/review/error, money execution giữ T0.
- [ ] AD-05 Web và app cùng chức năng theo quyền, app ưu tiên công việc/mobile.
- [ ] Customer/admin/denied fixture browser matrix, không production mutation.

## V0 — Product Video và video tools R218-09 (làm cuối sản phẩm)

- [ ] VI-01 AI chân thật text/ảnh/scenes/brand/review.
- [ ] VI-02 Trend catalog/search/reference/source/suggestions.
- [ ] VI-03 Script AI/tự nhập/upload và scene editor.
- [ ] VI-04 Frame video source/order/cover/duration/fit/transitions/motion/audio/text.
- [ ] VI-05 Selfshot đổi cảnh/điện ảnh/timeline/preservation.
- [ ] VI-06 Storyboard grid/detail/source/prompts/addons/review.
- [ ] VI-07 Series/long bible/continuity/planning và khóa execution thật.
- [ ] VI-08 Idea/reference/library/profile/downloader/handoff.
- [ ] VI-09..12 Manual/AI/upgrade hub, timeline/segments/transforms/layers/exports.
- [ ] VI-13 39 AI edit options/5 nhóm, detail/reference/mask/preservation/readiness.
- [ ] VI-14 Upgrade chỉ hứa khả năng runtime đã chứng minh.
- [ ] VI-15 Addons selected/applied, quote/report/output/download/reuse.
- [ ] Đủ 32 profile/3 nhóm; catalog khác bộ legacy 12.
- [ ] Không claim CapCut parity từ toolbar; browser thao tác từng nhóm.

## Q0/M0/L0 — Nghiệm thu rồi motion, rồi báo cáo

- [ ] Inventory B01–B34 → control ledger; unclassified=0 hoặc ghi reason rõ từng mục.
- [ ] VI/EN/ZH sạch; dữ liệu user/tên riêng không bị dịch.
- [ ] Mobile 375/390/768/1440 × themes; shell/forms thêm 320/414/1024.
- [ ] Keyboard/focus/label/contrast/touch/overflow/empty/loading/error/recovery.
- [ ] Motion không bị hydration cắt/restart; route cleanup, reduced-motion.
- [ ] Trace/perceived loading: CLS/LCP/INP có số đo hoặc blocker cụ thể.
- [ ] CI đúng HEAD và authorized live SHA/DOM/screenshots/interaction đúng scope.
- [ ] Báo cáo UI/UX/motion, giữ goal chưa complete nếu requirements còn mở.
- [ ] Hết UI/UX/motion thì đợi lệnh cho T0.

## T0 — Kỹ thuật cuối, chưa triển khai

- [→] Canonical DTO/capability/catalog/Voice Library/speaker mapping.
- [→] Upload/quote/job/output bridge, paid providers và artifact delivery.
- [→] Backend RBAC/ABAC, cross-product references và mutation nghiệp vụ.
- [→] OAuth/publish/ads, wallet/PayOS/manual approval/ledger.
- [→] Mọi gap có trigger/input/authority/idempotency/audit/failure/evidence riêng.

PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_MUTATIONS=0.
MERGE/DEPLOY/LIVE không suy từ tests. Trạng thái delivery theo PR/checkpoint hiện tại.
