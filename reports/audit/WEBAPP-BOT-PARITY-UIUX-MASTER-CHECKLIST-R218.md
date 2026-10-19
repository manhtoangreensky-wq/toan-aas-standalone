# R218 — Checklist UI/UX toàn bộ sản phẩm WebApp

Ngày 2026-10-20; cập nhật sau run `39303469636`. WIP_ADMIN_PRESENTATION_CI_GREEN_AUTH_QA_GREEN;
state-only follow-up HEAD `d6c6ccf` đang chờ CI riêng.
Source Bot được đọc-only; production chưa kiểm.
Không thay goal tổng; checklist này bổ sung và nối tiếp công việc R217 còn dở.
Từ ngày này, bảng dưới là completion ledger R218; lịch sử R217 giữ nguyên bằng chứng cũ.
Đối soát toàn bộ lịch sử trước R217 nằm tại
`reports/audit/WEBAPP-HISTORICAL-CHECKLIST-CROSSWALK-R218.md`; không dùng tài liệu cũ
để suy diễn PASS.

## Quy ước

[x] Đủ evidence đúng phạm vi. [~] Một phần, chưa đóng. [ ] Chưa thực thi/chưa chứng minh.
[!] Có gap cụ thể. [→] Kỹ thuật giữ cuối, đợi lệnh sau UI/motion.
Bất kỳ mục không browser evidence không gọi là UX/LIVE hoàn thiện.
Các mục API/provider/delivery chưa có giữ riêng ở T0 theo lệnh Owner. Chốt
lát UI bằng bằng chứng rồi tiếp tục lát UI theo thứ tự; không coi API thiếu
là lý do dừng toàn bộ UI/UX hoặc tự triển khai backend ngoài phạm vi.

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
- [x] #654 source candidate `7d126564f61d753caee5f514137ee5e2be057de7` đã push; SubDub lane patch và các lát Admin đạt kiểm thử local và CI/browser trên source HEAD.
- [x] Ghi current SHA/checks #654: Verify Web App + Authenticated WebApp QA SUCCESS ở run `39303469636`; route matrix `456/456`, `0` lỗi. State checkpoint chỉ tài liệu `d6c6ccf32e3a242c594347ac1f89033c9423616e` đã được đẩy tiếp; CI của checkpoint này đang chạy riêng.
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

- [x] VO-01 SCALAR-DRAFT — 19/10/2026: bốn chế độ chuyển trong cùng document;
  giữ nội dung/thiết lập, mức âm lượng 0 và locale; Back/Forward hoạt động,
  Ctrl/Meta-click giữ hành vi link gốc. Đổi/mất phiên xóa bản nháp Voice.
  Tệp/password không đưa vào Map hoặc browser storage. Test 7/7; browser
  18 cấu hình, gồm alias `/tts`, session cleanup và overflow; lỗi/request ngoài/
  mutation đều 0. Full Node 645/645. Reload/file selection/delivery còn mở.

- [x] VO-09 READ-STATE — 19/10/2026: phân biệt loading/failed/guarded với
  empty thật, xóa tên giọng cũ trước await và khi bootstrap, chặn response phiên
  cũ, giữ list khi readiness lỗi, retry chỉ GET. 19/19 test hành vi; cả nhóm
  inventory 34/34; full Node 638/638 sau khi giữ 6 test SubDub mới từ remote.
  Lát này không đóng management/handoff.

- [~] TTS/STT/default/saved/clone đã được bố trí trong một workspace dọc có bốn lane
  và deep link riêng; `renderVoiceWorkspaceNav()` giữ lane hiện tại bằng
  `aria-current="page"`. Draft retention và execution capability vẫn chưa đóng.
- [~] VO-12 STT đã có control-level source panel: tệp audio/video, Tự nhận diện hoặc
  ngôn ngữ nguồn, và Văn bản/SRT/VTT trong `FIELD_SETS.voiceStt`; route `/voice/stt`
  và alias `/voice/asr` được nối vào manifest, status, hub, quick switch và workspace.
  Contract `tests/voice-workspace-stt-contract.test.mjs` đạt `4/4`, quick-switch VI/EN/ZH
  kiểm đúng 152 destination, full Node trước lát này đạt `598/598`. Lát presentation mới
  tách rõ tiêu đề/mô tả/kết quả của chép lời khỏi TTS, khóa upload/estimate nếu chưa có
  `voice_stt` capability riêng và không dùng bộ đếm âm lượng/TTS feedback cho STT.
  Test `tests/voice-stt-form-presentation.test.mjs` đạt `18/18`; Edge localhost đạt
  18 cấu hình VI/EN/ZH × sáng/tối × 390/768/1440, lỗi trang/console/request ngoài/
  mutation/overflow đều 0. Upload thật, MIME/size/ownership, progress, transcript/
  copy/export, delivery và LIVE vẫn guarded.
- [ ] Default nữ/nam distinct hoặc fallback một default theo capability.
- [~] Nội dung/đếm từ/speed 0.1–2.0/volume 0–200: control và giá trị mặc định đã khóa
  bằng test `tests/voice-controls-contract.test.mjs`. VO-03/VO-05 đã có số đếm Unicode,
  cảnh báo 0% giữ nguyên giá trị người dùng, đồng bộ số/thanh kéo và giữ qua hydration;
  browser renderer localhost đạt 18/18 cấu hình VI/EN/ZH × sáng/tối × 390/768/1440.
  Cảnh báo đạt tương phản 11,25:1 (sáng), 8,84:1 (tối); quote stale/runtime vẫn mở.
- [~] Quote/expiry/confirm/progress/player/download/report/retry: expiry client đã tôn trọng `quote_expires_at`/`quote_valid_until`/`expires_at`; quote quá hạn không render CTA confirm và yêu cầu làm mới. Báo cáo control-level nay chỉ đọc tín hiệu `report`/`job`/`result` do máy chủ trả về, hiển thị trạng thái/tiến độ/tệp/tải xuống/bàn giao khi có cờ canonical, giới hạn reason 240 ký tự và không lộ `output_url` hay tạo CTA tải giả; test `voice-flow-state-presentation` đạt `51/51`, full Node đạt `601/601`. Progress/player/retry/runtime delivery vẫn mở.
- [ ] Kho giọng search/page/status/default/preview/rename/delete/reuse.
- [~] VO-02/VO-09/VO-10/VO-13: picker nam/nữ, Voice Vault owner-scoped và route handoff đã được khóa ở source bằng `tests/voice-selection-clone-contract.test.mjs` (4/4); quote, preview, rename/delete, runtime và browser/AX vẫn mở.
- [~] VO-11: clone consent/upload/tên tùy chọn tối đa 120 ký tự đã khớp bridge hiện hành; form nay có hướng dẫn guarded đủ 7 bước consent → sample → name → quote → preview → save → back, được khóa ở source bằng test clone `5/5`; xác nhận text, quote, preview, save/back và runtime vẫn mở.
- [!] VO-13 còn thiếu handoff profile/draft thật. Hai link hiện chỉ mở công cụ nên được đặt nhãn “Mở SubDub”/“Mở công cụ video”; không gọi là dùng lại giọng. Bốn nút quản lý luôn khóa đã được bỏ, thay bằng thông tin ngắn về thao tác chưa có. Rename/default/delete/preview vẫn là yêu cầu mở, chưa đạt UI hoàn chỉnh.
- [!] Contract gap R218-02A đã được tách riêng tại
  `docs/superpowers/specs/2026-10-18-r218-02a-voice-vault-canonical-contract.md`:
  Bot có phân trang, đếm tổng, đặt mặc định, nghe thử, đổi tên, xóa mềm và
  dùng cho Video; Web giữ GET metadata. Rà soát 19/10 trên Bot ref
  `4d086cc` cho thấy API bỏ qua tham số phân trang và total chỉ bằng số mục trả
  về (mặc định tối đa 50). Các proxy management suy đoán ở `c6bc455` đã được
  gỡ. Chưa có management endpoint, mutation receipt, preview delivery hoặc
  handoff profile/draft thật; phần này giữ tại T0. Không chuyển các mục này
  sang `[x]` khi chưa có endpoint + browser/owner evidence.
- [~] Renderer/interaction + browser/AX/screenshots: VO-03/04/05 và navigation Voice Vault đã kiểm bằng Edge localhost với dữ liệu mẫu, 18/18 cấu hình, lỗi trang/console/overflow/kết nối ngoài/mutation đều 0. Nhãn trình đọc màn hình của preset tốc độ đã sạch VI/EN/ZH. STT presentation mới đạt 18/18 cấu hình với focus/overflow/locale và không có TTS feedback/audio giả; browser upload/AX runtime, backend/delivery và live vẫn mở.
  Lát READ-STATE được kiểm thêm bằng shell/renderer/integration.js production
  trên localhost với API fixture chỉ-đọc; kết quả và ảnh tại
  `../qa/r218-voice-inventory/result.json`. Không tính là backend/LIVE.

## P2 — Music R218-03 (MU-01..12)

- [~] MU-00 control-level local đã khóa theo C0; các mục runtime và delivery dưới đây chưa đóng.
- [~] MU-00 browser presentation — 19/10/2026: `/music/create` và `/music/song` đã kiểm bằng Edge localhost với 36 cấu hình (VI/EN/ZH × sáng/tối × 390/768/1440 × 2 workspace), giữ field bài hát riêng, không hiện audio/player/giá/download giả; page/console/request ngoài/write/unknown API/overflow đều `0`. Đây là fixture đọc-only, chưa phải generation/player/delivery/LIVE.
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
- [~] Regression SubDub hiện hành đạt `20/20` focused tests; simulation kiểm `24` tổ hợp
  locale/mode/theme, giữ Smart Multi/Auto 2/Auto Multi 3–8 riêng, 7 vị trí phụ đề và
  trạng thái guarded. Browser authenticated/runtime/upload thật vẫn mở.
- [ ] Renderer/interaction + browser/AX/screenshots đạt.

## P4 — Image R218-05 (IM-01..10)

- [~] Tạo nhanh/prompt từ ảnh/AI edit/manual đã có 4 mode dọc rõ trên `/image/create`;
  `prompt` nối `/image-studio`, `aiEdit` nối `/image/transform`, `manual` nối `/image/edit`.
  Đây mới là control-level projection; source/reference, AI runtime, upload, preview,
  before/after, quote, result và delivery vẫn chưa có bằng chứng.
- [~] Regression control-level Image đạt `52/52` focused tests: hub 8 route duy nhất,
  create/edit/prompt/localized mode, quote guard, draft/report truth và không có output/giá/
  download giả. Browser authenticated/upload/preview/runtime/delivery vẫn mở.
- [~] Image browser presentation đạt `18` cấu hình VI/EN/ZH × sáng/tối × 390/768/1440;
  bốn mode, guarded state, focus/overflow và page/console/request ngoài/write/unknown API
  đều đạt `0`. Shell logo được loại khỏi selector output; không có media/output/download giả.
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
- [~] Admin focused locale/layout regression đạt `21/21` trên các module tab, customer 360,
  finance/topup, provider, shell boundary và stewardship. Browser role fixture, dynamic
  data, approval/runtime và live vẫn mở.
- [~] Smoke Admin trước đây gồm 72 tổ hợp route/locale/OS scheme/viewport. Probe cũ
  chỉ kiểm nội dung/focus/overflow/network; không đủ kết luận role, locale, rail dọc
  hoặc dark mode hoàn thiện. Không dùng số 72 làm bằng chứng các mục đó đã đóng.
- [x] AD-01A/AD-03A: banner/lối tắt overview chỉ theo module máy chủ đã cấp;
  aggregate nạp tiền thiếu khác `0` thật, không suy total từ list page. Unknown và
  diagnostics theo VI/EN/ZH, contrast unknown 5,80:1. Test hành vi 18/18; browser
  18 cấu hình × 6 trạng thái (108), page/console/external/write/unknown API/overflow 0.
  Artifact `../qa/r218-voice-inventory/admin-shortcuts.json`. Chỉ đóng projection UI;
  không đóng RBAC server, tiền hoặc LIVE.
- [x] AD-02-THEME-A: đã bỏ chốt JS luôn ép Admin light/xóa preference; chọn Dark/System
  có tác dụng, nút theme hiện và ≥44px. Giữ mặc định Admin light theo policy cũ,
  lưu theme Admin bằng key riêng, không đổi preference khách; query sai/storage bị chặn
  không phá UI. `tests/portal-admin-theme-preference.test.mjs` 17/17; full Node 704/704.
- [x] AD-02-THEME-B (core surfaces): nhánh Admin dark dùng navy sẵn có `#0b132b`, thẻ
  `#1c2541`, chữ sáng; không sửa palette khách hay luồng auth. Cặp CTA/tab/sidebar sáng
  dùng teal đậm sẵn có để đạt AA. Browser 24 cases: VI/EN/ZH × 375/390/768/1440 ×
  `/admin` và `/admin/login`, kiểm cả hai theme, keyboard cycle, persisted preference,
  email draft không mất khi đổi theme, drawer/Escape, bảng chẩn đoán và meta theme-color.
  Tương phản chữ đã đo min 7,61:1 dark / 5,24:1 light; page/console/external/write/
  unknown API/overflow 0. Artifact `../qa/r218-voice-inventory/admin-theme.json`.
- [~] AD-02-THEME tổng còn cần QA từng module/bảng có dữ liệu thật, biểu đồ và trạng
  thái động; không dùng 24 cases core để đóng toàn bộ Admin. Đối soát: chỉ đặt OS dark
  không có nghĩa đã chọn Dark khi policy mặc định Admin vẫn là Light.
- [x] AD-02-MOBILE-DATA-CARDS (lát trình bày): trên điện thoại, bảng dữ liệu Admin
  xếp thành thẻ dọc, không tràn ngang; `thead` vẫn hiện diện trong cây trợ năng; badge,
  trạng thái và nút tự xuống dòng. Fixture browser trước đó đạt 8/8 cấu hình: VI/EN ×
  sáng/tối × 390/1440px; tại 390px vùng bảng 318/318px, lọc có kết quả/không kết quả,
  xóa lọc giữ focus, Enter chọn dòng và mở inspector, 1440px giữ bảng native; lỗi trang/
  console/request ngoài/request ghi/API lạ đều 0. Test nguồn `3/3`, toàn bộ Node `706/706`.
  Ảnh: `../qa/r218-voice-inventory/admin-data-mobile-qa-{vi,en}-{light,dark}.png`.
  Đây là fixture tổng hợp chỉ đọc, không chứng minh RBAC/backend/dữ liệu thật. Rerun mới
  19/10 bằng Edge profile tạm ngoài sandbox đạt 8/8: table/8 headings trong AX, lọc/empty/
  clear-focus/Enter-inspector, mobile 318/318px và native desktop table. Lỗi trang/console/
  request ngoài/write/API lạ đều 0. Artifact mới `../qa/r218-voice-inventory/admin-data-reviewed.json`
  (SHA256 `8995d3f057bffe687850967652fbc1de7799dc3d1d0068bc3590c87ce2e0c636`).
- [~] AD-02-MOBILE-DATA: bảng Admin đã giữ semantic table trên desktop/tablet và chuyển
  từng bản ghi thành thẻ dọc ở `<=560px`; nhãn cột lấy trực tiếp từ `thead`, giữ lọc/chọn
  dòng/inspector và không thêm dữ liệu hay quyền. Lát cards đã có bằng chứng riêng ở trên;
  QA từng module với role được phân quyền/từ chối, dữ liệu động, biểu đồ và runtime vẫn mở.
- [x] ADMIN-RUNTIME-BOOT: browser fixture ban đầu dùng nhầm symbol một-A `window.TOANASPortal`
  trong khi production export đúng hai-A `window.TOANAASPortal`; đã sửa harness và chạy lại
  đúng consumer generic. Probe headless đạt `12/12` VI/EN/ZH × sáng/tối × 390/1440,
  `errors/writes/external/unknown=0`, không còn blocker runtime của production symbol.
  Artifact `../qa/r218-voice-inventory/admin-commercial-pricing-probe.json`, SHA256
  `4E5947CF4FA2A86035B786FC5996AFD85E7EADCB312B1E72954A2BF18664331D`. Backend/RBAC,
  CI, production và LIVE vẫn là phạm vi mở.
- [x] AD-02-STATE-LOCALE (local UI): thêm 14 mapping để đủ 35 state và catalogue VI/EN/ZH;
  VI backlog dịch thành “Việc chờ xử lý”. RED pass1/fail6 → GREEN7/7, full Node713/713,
  syntax/diff check và comparator enum/function/Python/integration/workflow đạt. Browser
  12/12 × VI/EN/ZH × sáng/tối × 390/1440, state đúng locale; layout/filter/empty/focus/
  keyboard giữ nguyên, lỗi/write/external/unknown0. Spec `2026-10-19-r218-admin-state-locale.md`;
  artifact `../qa/r218-voice-inventory/admin-state-locale.json` SHA256
  `85ebdac2270a7dc393137f4fe5e35717ec7a56518b14d2bb1d459eeac6f73561`. Chưa CI/deploy/LIVE.
- [x] AD-02-PRICING-LOCALE: specialised `/admin/pricing` renderer/cards đã chuyển fixed
  chrome sang `adminPricing.*` đủ VI/EN/ZH; browser 12/12 không còn locale finding. Generic
  table `renderAdminDataTable` cũng đã bỏ schema jargon và dùng `adminGeneric.pricing.*`;
  focused/full source xanh và đúng consumer generic browser 12/12, không overflow, không
  request ghi/API lạ. Chỉ đóng localhost read-only presentation; editor/backend/RBAC/CI/
  production/LIVE còn mở.
- [x] AD-02-PRICING-DATA-TRUTH (local UI): bỏ7 giá/approval client fallback; phân biệt
  missing/malformed với verified empty; giữ server IDs/labels/25/0, giá thiếu—; base version
  chưa xác minh khóa đúng hai nút/reason và giữ base value rỗng, valid base vẫn authoring.
  Corrected immutable RED18 checks →GREEN72/72 states; Node713/713, syntax/diff0, source
  ngoài2functions/old i18n values/CSS/tests/backend/integration/workflow giữ nguyên.
  Artifact `admin-pricing-truth.json` SHA256
  `3c5b0063939fe299eb976d5786b3ad0518940b89c1dee02dc4a302b4208c93ab` trong QA folder.
  Data-truth, locale, mobile và affordance của specialised renderer đã accepted local; CI/
  deploy/LIVE và generic commercial consumer còn mở.
- [x] AD-02-PRICING-LOCALE runtime (specialised renderer): browser 12/12 VI/EN/ZH × sáng/tối
  ×390/1440 không còn locale finding; fixed chrome/card dùng namespace `adminPricing`.
  Generic commercial editor/table vẫn là backlog riêng.
- [x] AD-01-PRICING-NAV-LOCALE: root shared renderer dùng profile/interface locale; focused9/9,
  full Node720/720, browser12/12; registry, authorizedRoutes, aliases, legal exception và
  hrefs giữ nguyên.
- [x] AD-02-PRICING-MOBILE: bảng desktop ẩn ở ≤700px và card dọc hiện; 72 trạng thái truth
  và 12 cấu hình presentation đạt, không overflow.
- [x] AD-04-PRICING-AFFORDANCE: draft create/save/publish chỉ enabled khi có base catalogue
  hợp lệ và capability server-issued; thiếu readiness/capability disabled; publish vẫn guarded,
  không suy diễn backend hoặc quyền tiền. Browser findingCodes=[]; real RBAC/publish/LIVE mở.
- [x] AD-02-GENERIC-LOCALE-CLOSEOUT (local UI): khóa các bản dịch VI còn lẫn thuật ngữ
  tiếng Anh trong tra cứu kiểm soát, bảo trì, hàng chờ sự cố và trạng thái bảo mật/quyền
  truy cập; fallback nút thử lại cũng thuần tiếng Việt. Giữ nguyên Bot, Core Bridge, PayOS,
  Xu, CSRF, mã route/ID và toàn bộ authority/payload. Test focused `11/11`, syntax hai JS
  và `git diff --check` đạt. Spec `docs/superpowers/specs/2026-10-20-r218-admin-generic-locale-closeout.md`;
  full Node/CI/browser/backend/production/LIVE phải recheck theo đúng HEAD.
- [x] AD-02-DYNAMIC-CHART-PROJECTION (local UI): biểu đồ và chú giải tùy chọn chỉ nhận
  `data.chart` do máy chủ cấp; chặn adapter `compatibility_guarded`, giới hạn 1–12 điểm,
  nhãn/giá trị số không âm và tone legend theo allowlist. Thanh dữ liệu có tên vùng,
  mô tả, giá trị và `role="img"` để không phụ thuộc màu; không tự tạo số liệu, không
  fetch/write/provider/capability mới, không thêm motion và giữ palette token hiện có.
  Test nguồn `3/3`, focused Admin `14/14`, full Node `728/728`, `node --check` hai JS
  và `git diff --check` đạt. Browser fixture chưa chạy được trong sandbox do Playwright
  không tạo được thư mục tạm; không đóng QA role/module, dữ liệu thật, approval, backend,
  CI, production hoặc LIVE. Phần tổng AD-02 vẫn mở.
- [x] AD-03-RECORD-REFERENCES (local UI): Inspector Admin nhận projection tùy chọn
  `admin_record_references` chỉ do server cấp, tối đa 6 liên kết loại `request`, `job`,
  `asset`, `report`, `audit`; ID/nhãn bị giới hạn và path chỉ qua allowlist nội bộ
  `/admin`, `/jobs`, `/assets`, `/reports`, `/audit`. URL ngoài, `//`, `\\`, dot-segment và path
  không hợp lệ bị loại; DOM link được tạo bằng API an toàn, không chèn HTML thô.
  Bảng giữ metadata `data-admin-record-references`, Inspector có vùng “Liên kết hồ sơ”,
  nhãn loại cân bằng VI/EN/ZH. Test nguồn `2/2`, focused Admin sau slice `16/16`,
  full Node `730/730`, syntax hai JS và `git diff --check` đạt. Authenticated route/render
  matrix cùng source đạt `456/456` ở run `39303469636`, nhưng không inject record fixture
  để chứng minh liên kết hồ sơ. Đây chỉ là projection UI chỉ đọc; AD-03 tổng (role/RBAC,
  record thật, bridge request→job→asset→report→audit, backend, production và LIVE) vẫn mở.
- [x] AD-03-ROLE-MODULE (local UI): projection manifest quyền do máy chủ cấp chỉ
  nhận nhóm/phân hệ khi `read_state=ready`; route chỉ nằm dưới `/admin`, loại route
  trùng, route ngoài Admin, `//` nội bộ, `\\` và dot-segment thường/mã hóa (`..`, `%2e`);
  trạng thái lạ chuyển thành `guarded`, `available/canonical_read/web_native` chỉ
  được trình bày là `read_only`. Không suy quyền từ `context.isAdmin`, browser role,
  ID nhóm hoặc capability; không thêm route, write, provider, RBAC thật hay dữ liệu
  record. Test projection `2/2`, focused Admin `18/18`, full Node `732/732`, syntax
  hai JS và `git diff --check` đạt. Authenticated route/render matrix đạt `456/456` ở run
  `39303469636`; role/RBAC server-issued manifest và dynamic record fixture vẫn chưa được
  chứng minh. AD-03 tổng và chuỗi request→job→asset→report→audit vẫn mở.
- [x] AD-03-RECORD-CHAIN (local UI): Inspector sắp xếp các reference đã được máy
  chủ cấp theo thứ tự cố định `request → job → asset → report → audit`; thiếu mắt
  xích vẫn giữ đúng phần đã cấp, trùng loại lấy reference đầu tiên, dữ liệu được
  chiếu lại qua cùng allowlist path/ID/kind trước khi tạo link. Hiển thị bằng DOM API
  trong danh sách dọc, có catalogue VI/EN/ZH và không thêm approve, write, provider,
  capability, fetch hoặc bridge nghiệp vụ. Test reference `2/2`, focused Admin
  `18/18`, full Node `732/732`, syntax hai JS và `git diff --check` đạt. Authenticated
  route/render matrix đạt `456/456` ở run `39303469636`, nhưng record thật và bridge server
  chưa được nạp vào fixture; production và LIVE chưa xác minh.
- [x] AD-04-CAPABILITY-AFFORDANCE (local UI): Hàng đợi nạp thủ công không còn hiển
  thị nút tạo quyết định duyệt/cộng Xu trong bảng hoặc thẻ mobile khi server chưa cấp
  `admin-manual-topup-write`; thay bằng nhãn chỉ đọc có lý do quyền hạn, vẫn giữ nút
  xem chi tiết. Khi capability đã cấp, affordance draft hiện hành và inspector xác
  nhận cuối không đổi. `expected_xu`/`approved_xu` chỉ hiển thị từ máy chủ; thiếu thì
  để `—`, không suy `amount_vnd / 100` ở trình duyệt; state draft cũ cũng không dựng
  modal xác nhận khi capability ghi đã mất. Test nguồn `3/3` tại
  `tests/admin-manual-topup-capability-presentation.test.mjs`; slice chỉ sửa renderer,
  không mở wallet/ledger/PayOS/API ghi. Capability thật, approval, cộng Xu, browser
  tương tác nghiệp vụ, production và LIVE vẫn mở; route/render matrix CI đã xanh ở run
  `39303469636` nhưng không chứng minh mutation.

## V0 — Product Video và video tools R218-09 (làm cuối sản phẩm)

- [~] Video/Product Video focused UI regression `11/11` xanh: catalog VI/EN/ZH, hub route
  contracts, ordered brief→report flow, Video Studio home/detail, canonical plan/scene values
  và không output claim giả. Browser authenticated/runtime/render/delivery vẫn mở.
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

- [x] Q0-ZH-LOCALE-PICKER (local UI): root cause source thiếu option zh trong Admin header.
  RED renderer zh/select vi → thêm đúng một option → browser12/12 selected/renderer khớp,
  options vi/en/zh, local change/focus/form đúng; Node713/713, syntax/diff-check và scope
  hash comparator đạt. Artifact `admin-header-locale.json` SHA256
  `f099e8e7111316ab9f72e1277c8b24ef1be35d74f3bf1b3ead893d3831900fd1` trong QA folder.
  Spec `2026-10-19-r218-admin-header-locale.md`. Source CI đã xanh trong run
  `39303469636`; deploy/LIVE vẫn chưa thực hiện.
- [x] AD-02-ZH-GENERIC-COPY: catalogue Admin Generic ZH đã bỏ `canonical` khỏi toàn bộ
  fixed chrome của guard/bảng/Pricing/Jobs/adapter/quản trị hệ thống/hướng dẫn/runtime;
  test nguồn `1/1`, full Node725/725. Dữ liệu định danh, Bot/Core Bridge/PayOS/Xu và key
  máy chủ giữ nguyên; CI/deploy/LIVE chưa mở.

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
