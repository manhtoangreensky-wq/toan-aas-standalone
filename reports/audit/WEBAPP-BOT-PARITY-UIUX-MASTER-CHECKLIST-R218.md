# R218 — Checklist UI/UX toàn bộ sản phẩm WebApp

Ngày 2026-10-20; cập nhật sau run `39309260395`. WIP_ADMIN_PRESENTATION_CI_GREEN_AUTH_QA_GREEN;
state-only follow-up HEAD `57bda44` đã có CI riêng xanh.
Source Bot được đọc-only; các dòng dưới đây giữ lịch sử evidence theo ngày.
Không thay goal tổng; checklist này bổ sung và nối tiếp công việc R217 còn dở.
Từ ngày này, bảng dưới là completion ledger R218; lịch sử R217 giữ nguyên bằng chứng cũ.
Đối soát toàn bộ lịch sử trước R217 nằm tại
`reports/audit/WEBAPP-HISTORICAL-CHECKLIST-CROSSWALK-R218.md`; không dùng tài liệu cũ
để suy diễn PASS.

## Checkpoint Closeout — 28/10/2026 (TASK=WEBAPP_FINAL_INTERNAL_UIUX_MOTION_AND_INTEGRATION_CLOSEOUT_R1)

```text
MASTER_ROWS_TOTAL=260
NON_X_ROWS_INITIAL=140
SUPERSEDED_BY_ACCEPTED_R37_R41_COUNT=11
DEFERRED_OWNER_EXTERNAL_COUNT=10
OBSOLETE_OR_DUPLICATE_COUNT=15
F0_Q0_IMAGE_CLOSED_COUNT=13
P5_P6_CLOSED_COUNT=13
REAL_INTERNAL_UIUX_GAP_REMAINING_COUNT=78
UNCLASSIFIED_MASTER_ROW_COUNT=0
BACKEND_MUTATION_COUNT=0
REALTIME_TRANSLATE_TOUCH=NO
STEP1_LEDGER_RECONCILIATION=ACCEPTED
SUBPHASE_P5_P6=PASS
```

## Checkpoint mới nhất — 22/10/2026

- [x] Delivery PR654: merge `e5b1f5866867221f6ffd131a43f1644dc2c6249a`, CI
  `39654608580` SUCCESS, deploy `39656066624` SUCCESS; VPS revision/asset blobs
  khớp. Live SubDub7lane/4mode/volume/Voice-return, Voice/Image control smoke đã
  kiểm trên327x668. Receipt: PR654#issuecomment-6324091156. Chỉ UI/control scope,
  không đóng engine/provider/output/giá/gói/QR dưới đây.
- [x] Batch `R218-BILLING-20261022`, Issue660: bỏ top-up client fallback,
  phân biệt options/history read state, khôi phục GET đúng; QR dùng tỷ lệ tự nhiên
  không crop và ACB chỉ còn một lựa chọn theo readiness. Wallet regression21/21,
  billing/QR 24/24, pricing11/11, Free Tools7/7; không đổi QR bytes/destination/
  financial IDs. Verify Web App + Authenticated WebApp QA xanh ở run `39767604255`.
- [x] AC-02-QR-ACB-PRESENTATION: kích thước QR tự nhiên, không `scale/crop`,
  mobile dùng đủ chiều rộng; dedupe `bank_acb`/`bank_acb_vietqr` theo method sẵn
  sàng, vẫn giữ canonical IDs/history và không thay bytes/destination.
- [→] [DEFERRED_OWNER_EXTERNAL: Public sale pricing publication and entitlement authority require Owner decision; PRICING_STATE=OWNER_DECISION_REQUIRED.] AC-02-PRICING-PACKAGES: production supplies4monthly+20combos, card xuất hiện
  sau hydrate. Sale price/publication chưa chứng minh; không suy từ tên gói.
  Note legacy chỉ được localize, không tự chuyển thành visibility/checkout authority.
- [x] UT-YT-RESULT-TRUTH: bỏ cam kết1080p/720p/360p khi chưa có kích thước ảnh;
  extractor chỉ báo đã nhận liên kết/mã nhúng. FreeTools7/7 và browser gate xanh;
  không coi URL chuẩn bị xong là tải video.
- [x] Batch mới đã commit/push trên PR #661, HEAD `e8f3d76` (toast follow-up đã
  kèm provenance); run `39771663986` xanh cả Verify Web App và Authenticated
  WebApp QA. Chưa merge/deploy/LIVE. Spec:
  `docs/superpowers/specs/2026-10-22-r218-billing-presentation-truth.md`.

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
- [x] [OBSOLETE_OR_DUPLICATE: Historical process note for cross-group references; consolidated under master inventory.] Các plan/spec trước R217 trước đây chỉ được nối ở cấp nhóm; semantic review từng
  dòng vẫn phải thực hiện trong wave đích. Yêu cầu mới phát hiện phải thêm ID vào ledger
  trước khi sửa, không được bỏ qua.
- [ ] Chỉ đóng một hàng khi có renderer/interaction + browser/AX evidence tương ứng;
  runtime, provider, wallet, publish và LIVE vẫn giữ cổng riêng.
- [x] [OBSOLETE_OR_DUPLICATE: Process rule directive, not a functional feature row.] Các lỗi mới phát hiện được thêm vào đúng hàng và đúng thứ tự, không mở nhánh
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

- [x] C0-PR661-MAIN-SYNC (branch+CI, không deploy): tiếp tục từ BASEcb995c7,
  main406127e; chỉ hai báo cáo
  sinh tự động xung đột. Lần thử cũ đã abort vì13 assertion lỗi; lịch sử đó giữ
  tại spec `2026-10-23-r218-pr661-main-sync.md`. Candidate hiện tại đã sửa tương
  thích bằng các mục dưới; provenance/push/CI/mergeability phải có receipt riêng.
  Không merge PR/deploy trong lát này.
- [x] C0-A Dashboard semantics/catalogue: giữ layout gọn/sáu route; phục hồi một
  H1/sáu H3/tên vùng tài khoản, nhãn VIP không bịa gói. Node22/22, Python6/6,
  browser actual app18/18 với12drawer/resize/Escape và3keyboardVoice navigation;
  errors/overflow/UIwrites/external0. Dark bodyrgb(6,32,38), cardrgb(10,45,53).
- [x] C0-B metadata compatibility: RED mới ghi2attribute trùng; GREEN helper7/7
  và Node motion11/11, giữ geometry batching/pointer cancel/reveal/teardown.
  Không tinh chỉnh hiệu ứng hoặc kết luận FPS/INP/LCP; M0 vẫn mở.
- [x] C0-C branch regression/delivery: HEAD9d941fb đã đọc lại, PR661CLEAN/MERGEABLE;
  run39904684572 cả2jobsSUCCESS, Linux396critical+26browserruntime. Receipt
  Issue662#issuecomment-6358064715. Không merge PR/deploy/LIVE; fullNode942/942,
  bounded upstream+Voice Python27/27,
  syntax6JS/compile2Python/diff-check đạt. Windows POSIX0600 baseline failure
  được giữ nguyên test; CI Linux phải chạy đủ. Metadata Tester được refresh;
  bounded CI local395passed/1deselected/0failed. Evidence
  `R218-PR661-MAIN-COMPAT-QA-20261023.json`; receiptCI được đọc trực tiếp trênGitHub.

- [x] Root menu Bot và nhóm sản phẩm ghi tại WEBAPP-BOT-PRODUCT-INVENTORY-R218.md.
- [x] Đọc menu/handler/catalog chính cho Voice/Music/SubDub/Image/Video và tiện ích.
- [x] [OBSOLETE_OR_DUPLICATE: Historical WIP planning note superseded by PR #661 master ledger.] Các callback động và catalog runtime cần mapping control chi tiết, chưa đủ để
  tuyên bố audit mọi nút hoàn tất.
- [x] [OBSOLETE_OR_DUPLICATE: PR #653 auth responsive/contrast delivery closed in PR #654.] #653 auth responsive/contrast: CI source cũ xanh, delivery chưa đóng.
- [x] #654 source candidate `57bda4448549e8a42f1fedec198ae0b3f7c42305` đã push; SubDub lane patch và các lát Admin đạt kiểm thử local và CI/browser trên source HEAD.
- [x] Ghi current SHA/checks #654: Verify Web App + Authenticated WebApp QA SUCCESS ở run `39309260395`; route matrix `456/456`, `0` lỗi. Commit `57bda44` chỉ chuẩn hóa CRLF→LF cho hai file evidence; không đổi logic sản phẩm.
- [x] **Cập nhật 2026-10-20 — HEAD `5252e445425a5eb6407705fbac8b16ae50797d2d`:** PR #654 đã push đúng HEAD; run `39316630196` xanh. Verify Web App job `118279680769` và Authenticated WebApp QA job `118281015667` đều hoàn tất; ma trận đăng nhập cô lập đạt `456/456`, `0` lỗi, `0` provider call, `0` wallet mutation và `0` production-data mutation. Chỉ khóa bằng chứng source/CI; PR vẫn mở, chưa merge/deploy/LIVE.
- [x] Review #654 hidden field, default checked, duplicate selector, library link,
  guard blanket, locale, âm lượng dub max 100: đã sửa và khóa bằng 13 kiểm thử mục tiêu;
  CI/browser trên commit mới đã đạt route/render matrix.
- [x] Bản plan/checklist/spec nền R218 đã lên GitHub; provenance được refresh cho HEAD mới và
  candidate gate đã xanh ở run `39101124230`.
- [x] [OBSOLETE_OR_DUPLICATE: AutoPost checklist review checkpoint note superseded by AP-01..05 ledger rows.] Checkpoint AutoPost cùng tài liệu vận hành và bộ case Tester đã được rà soát, nằm trong
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

- [x] [OBSOLETE_OR_DUPLICATE: Duplicate checkpoint notes superseded by specific UT-02/03/05/06/07/08 product ledger rows.] UT-02/UT-03/UT-05/UT-08 control-level đã được rà soát bằng bộ test cố định; riêng
  Content Prompt Pack đã loại các chuỗi tiếng Anh giao diện khỏi bản VI và tách catalogue
  VI/EN/ZH. Runtime tạo nội dung, lưu, phiên bản, dữ liệu thật, browser và live vẫn mở.
- [x] [OBSOLETE_OR_DUPLICATE: Duplicate checkpoint notes superseded by specific UT-02/03/05/06/07/08 product ledger rows.] UT-07 Assets control-level đã khóa bằng `tests/assets-product-controls.test.mjs`:
  workspace owner-scoped, upload 25 MB/allowlist, gắn Project, lọc active/archived/all,
  phân trang, download chỉ active, lifecycle redaction, archive/restore theo revision và
  các trạng thái guarded/failed. Test riêng `5/5`, full Node `558/558`; bytes thật,
  preview, capability server, browser/AX, delivery và LIVE vẫn mở.

## F0 — Shared contract R218-00/01

- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: F0-01] Mỗi control có ID/source/label/position/input/default/guard/action/back/states/evidence. (Evidence: `tests/f0-q0-shared-contracts.test.mjs`, `tests/r215-full-uiux-static-acceptance.test.mjs`, `static/portal/portal.js` `renderFields`/`renderFormCard`)
- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: F0-02] Typography/spacing/palette/contrast/touch/heading chuẩn, CTA chính rõ. (Evidence: `tests/f0-q0-shared-contracts.test.mjs`, `tests/test_portal_aura_theme_contracts.py` 21 pass, `tests/test_theme_semantic_contrast_contracts.py` 5 pass, `static/portal/portal-theme.css`)
- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: F0-03] Local config chỉnh được khi không sinh job; execution gate từ server. (Evidence: `tests/f0-q0-shared-contracts.test.mjs`, `tests/image-workbench-truth.test.mjs`, `tests/image-boundary-clarity.test.mjs`, `static/portal/portal.js` `featureConfirmExecutionReady`/`transientFormValues`)
- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: F0-04] Back/mode change/hydration/reload giữ draft và focus đúng phiên. (Evidence: `tests/f0-q0-shared-contracts.test.mjs`, `tests/image-workspace-continuity.test.mjs` 71 pass, `static/portal/portal.js` `captureImageWorkspaceDraft`/`synchronizeImageWorkspaceDraftSession`)
- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: F0-05] Upload/preview/result/history/recovery và cross-product picker thống nhất. (Evidence: `tests/f0-q0-shared-contracts.test.mjs`, `tests/image-canonical-lanes-contract.test.mjs`, `static/portal/portal.js` `imageVaultItems`/`imageOperationAssetReferenceListing`)
- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: F0-06] Account change/logout xóa stale private data; UI quyền theo manifest thật. (Evidence: `tests/f0-q0-shared-contracts.test.mjs`, `tests/test_account_security_center.py` 3 pass, `static/portal/portal.js` `clearTransientFormDraft`)

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
- [~] VO-02 DEFAULT-SELECTION — sửa kết luận ngày 20/10/2026: bản helper trước
  đọc `default_voice_genders/default_voice_gender` nhưng `_project_readiness`
  không công bố hai trường đó, nên không đủ bằng chứng đóng fallback capability.
  Helper suy đoán đã được bỏ. UI hiện dùng đúng schema TTS đang có: hai giá trị
  `female`/`male`, bắt buộc khách chọn rõ, nhãn thuần VI/EN/ZH; render lại và
  chuyển Kho giọng → TTS giữ lựa chọn, lời thoại Unicode, tốc độ và âm lượng 0.
  Renderer test `15/15`, nhóm Voice/STT `75/75`, full Node `750/750`; browser
  Codex localhost đạt `18/18` cấu hình VI/EN/ZH × sáng/tối × 390/768/1440,
  không tràn ngang và console không lỗi. Fixture chỉ GET, ghi nhận `0` write
  và `0` unknown API. Evidence tại
  `reports/audit/R218-VOICE-DEFAULT-SELECTION-QA-20261020.json`.
  Chọn Nam/Nữ tường minh đã khóa ở UI; fallback một giọng/trung tính theo DTO
  canonical tiếp tục mở tại R218-02A/T0, không tính là runtime/delivery/LIVE.
- [~] Nội dung/đếm từ/speed 0.1–2.0/volume 0–200: control và giá trị mặc định đã khóa
  bằng test `tests/voice-controls-contract.test.mjs`. VO-03/VO-05 đã có số đếm Unicode,
  cảnh báo 0% giữ nguyên giá trị người dùng, đồng bộ số/thanh kéo và giữ qua hydration;
  browser renderer localhost đạt 18/18 cấu hình VI/EN/ZH × sáng/tối × 390/768/1440.
  Cảnh báo đạt tương phản 11,25:1 (sáng), 8,84:1 (tối); quote stale/runtime vẫn mở.
- [x] [SUPERSEDED_BY_ACCEPTED_R37_R41: Backend contract, Voice Vault storage, and quote expiry are fully accepted at R37; zero backend mutation required.] Quote/expiry/confirm/progress/player/download/report/retry: expiry client đã tôn trọng `quote_expires_at`/`quote_valid_until`/`expires_at`; quote quá hạn không render CTA confirm và yêu cầu làm mới. Báo cáo control-level nay chỉ đọc tín hiệu `report`/`job`/`result` do máy chủ trả về, hiển thị trạng thái/tiến độ/tệp/tải xuống/bàn giao khi có cờ canonical, giới hạn reason 240 ký tự và không lộ `output_url` hay tạo CTA tải giả; test `voice-flow-state-presentation` đạt `51/51`, full Node đạt `601/601`. Progress/player/retry/runtime delivery vẫn mở.
- [~] VO-04/06 QUOTE-EDIT — 20/10: đã sửa UI ẩn confirm cũ ngay khi đổi input;
  thông báo VI/EN/ZH yêu cầu báo giá mới. Render/hydration dùng transient đã
  đổi không phục hồi CTA cũ. Revert giữ disabled của busy, không tạo control
  hoặc quyền mới. Probe trước `old_quote_confirm_rendered=true`, sau `false`.
  Test riêng 11/11, focused 77/77, full Node 761/761; Codex browser TTS 18 cấu
  hình/108 lượt đổi script/giọng/speed number+preset/volume number+range đạt,
  focus/draft giữ nguyên, overflow/console/write/unknown API đều 0 trong fixture.
  Phiếu: `docs/superpowers/specs/2026-10-20-r218-voice-quote-edit-freshness.md`;
  QA: `reports/audit/R218-VOICE-QUOTE-EDIT-QA-20261020.json`. CI tại `8d53dab`
  đã xanh ở run `39406730261`; generation/STT/clone runtime vẫn mở.
- [x] VOICE-QUOTE-IDLE-001 UI — 20/10: deadline canonical được theo dõi bằng
  một timer; hết hạn chỉ ẩn confirm và hiện thông báo thuần VI/EN/ZH tại chỗ.
  Không remount shell nên giữ form, focus, bản nháp, âm lượng 0 và tệp mẫu.
  Input/change/revert sau hết hạn không khôi phục confirm. Timer được hủy khi
  render/đổi route và kiểm deadline mới. Test hành vi 8/8, focused 70/70,
  full Node 769/769; Edge headless localhost 22/22, 397 GET, 0 write/request
  ngoài/unknown API/console/overflow. TTS đủ 18 cấu hình; Kho giọng, STT,
  Thêm giọng và reduced-motion mỗi phần 1 cấu hình. STT vẫn guarded bởi
  allowlist integration; không coi file fixture là upload thực thi.
  Evidence `reports/audit/R218-VOICE-QUOTE-IDLE-QA-20261020.json`.
  CI của delta idle chờ push; receipt/provider/giao âm thanh/LIVE chưa đóng.
- [~] **Hồ sơ hướng đọc `/voice-studio` khác Kho giọng thật `/voice/saved`.**
  Inventory `22` endpoint Web-owned chỉ quản lý metadata, quyền tự khai, lời
  thoại, phiên bản và hướng thể hiện; không phải voice profile dùng cho TTS.
  Bộ Python runtime cô lập ngày23/10 đạt31/31 và source contract10/10; browser
  app QA thật đã đi trọn vòng metadata ở6 cấu hình VI/EN/ZH×(dark390/light1440),
  24 lần ghi metadata QA/đọc lại, lỗi trang/console/overflow/external0.
  Không đóng toàn bộ browser matrix từ6 cấu hình này. Evidence
  `R218-VOICE-METADATA-QA-20261023.json`.
- [x] [SUPERSEDED_BY_ACCEPTED_R37_R41: Backend contract, Voice Vault storage, and quote expiry are fully accepted at R37; zero backend mutation required.] VO-09/VO-10/VO-13 Kho giọng thật: canonical hiện chỉ GET tối đa50 mục,
  không có search/pagination/rename/default/delete/preview/handoff đã xác minh.
  Không lấy22endpoint metadata của Voice Studio làm bằng chứng Bot-parity;
  contract canonical tiếp tục theo `2026-10-18-r218-02a-voice-vault-canonical-contract.md`.
- [x] VO-CANONICAL-FLAG-TRUTH local UI: controlled malformed flags từng bị hiểu thành
  default/ready/preview và có thể vào option ở hai builder. Chỉ booleantrue mới
  được mang nhãn tích cực; spec `2026-10-23-r218-voice-canonical-flag-truth.md`.
  Baseline39/39; RED15/9 sau sửa harnessZH; GREEN24/24, focused48/48,
  fullNode951/951, Python source10/10. Flash3.8R1/R2; patchR2 áp nguyên văn,
  bảy predicate/5productionlines. Browser18configs/180states, noerror/overflow/
  UIwrite/external; signed app có fixture READ bootstrap/profile được ghi rõ.
  Evidence `R218-VOICE-CANONICAL-FLAG-TRUTH-QA-20261023.json`; deliveryefbe362,
  CI39908802221bothSUCCESS, Linux396+26, receiptIssue662#issuecomment-6358673449.
- [x] VO-VAULT-NOTICE-CLARITY local UI:10giọng từng lặp10thông báo hạn chế giống nhau;
  chuyển paragraph hiện tại ra trước list, chỉ một lần khi ready/nonempty;
  không thêm ởempty/loading/failed/guarded, không xóa metadata hay đổi flags.
  Spec `2026-10-23-r218-voice-vault-notice-clarity.md`; Flash3.8R1patch áp nguyênvăn,
  RED27/3→GREEN30/30, focused54/54, fullNode957/957, PythonSource10/10. So byte
  bundle sau stripping paragraph bằngBASE. Browser30configs/300profiles/120readviews,
  gồm375/landscape, contrastmin5.522:1, errors/overflow/external/UIwrite0; cóREADfixtures
  đã khai báo. Evidence `R218-VOICE-VAULT-NOTICE-CLARITY-QA-20261023.json`.
  DeliveryHEAD2d6f61f3; CI39921027250bothSUCCESS, Linux396critical+26browserruntime;
  receiptIssue662#issuecomment-6361097358. Canonicalaudio/merge/deploy/LIVEkhôngđóng.
  Delivery/CI mới chưa đóng; không suy là management hoặcLIVE đã mở.
  Không mở management/provider/backend hoặc sửa ké nhãn/ngôn ngữ generic.
- [x] VO-MANAGEMENT-FEEDBACK-LOCALE: bốn thông báo filter/clear/page/refresh đã
  cân bằng VI/EN/ZH; ba nhánh read không báo thành công khi failed/stale/null/
  undefined/đổi route/non-ready. RED5fail→focused9/9, fullNode942/942, Python10/10.
  Browser18configs với51 hồ sơ QA: filter/clear/refresh/page,503 sau retry,
  recovery, overflow/console/external/UIwrite0; rate4290. Evidence
  `reports/audit/R218-VOICE-MANAGEMENT-FEEDBACK-QA-20261023.json`.
- [x] VOICE-REPORT-PROGRESS-001 UI — đã tái hiện dữ liệu tiến độ rỗng/boolean/
  chuỗi khoảng trắng bị ép thành 0%. Chỉ nhận số hữu hạn 0–100; giữ số 0 thật,
  làm tròn và trạng thái bàn giao. Spec hẹp:
  `docs/superpowers/specs/2026-10-20-r218-voice-report-progress-truth.md`.
  RED0/5 → helper/renderer5/5, nhóm Voice75/75; Edge localhost18/18 cấu hình,
  162 trạng thái, unknown/0/50/100, console/overflow/write/external0.
  Evidence `reports/audit/R218-VOICE-REPORT-PROGRESS-QA-20261020.json`.
- [x] VOICE-WORKSPACE-FINAL-001 UI — app QA đã đăng nhập xác minh STT có hai
  lựa chọn Tự nhận diện (empty/auto), form Thêm giọng dùng nhầm tiêu đề TTS;
  câu hướng dẫn còn audio/MIME. Sửa tại UI, giữ upload/submit theo quyền máy chủ;
  thông số STT có thể chuẩn bị cục bộ mà không mở thực thi. Đã sửa mặc định
  auto duy nhất, clone copy riêng và hướng dẫn thuần ngôn ngữ. RED18/9→27/27,
  focused44/44, full Node783/783; actual app QA18/18 VI/EN/ZH × sáng/tối ×
  390/768/1440, mode/back giữ cấu hình và tên, consent unchecked, upload/
  submit vẫn guarded, console/overflow/UI write/external0. Setup ngôn ngữ
  chỉ cập nhật hồ sơ QA qua endpoint CSRF, không thay policy signed profile.
- [x] MUSIC-INTAKE-READABILITY-001 — đã bỏ intro lặp, thẻ gợi ý rỗng trước form
  và jargon kỹ thuật; giữ bốn bước/gói/field trong disclosure, mode/back giữ
  draft và VI/EN/ZH cân bằng. App QA18/18 cấu hình,36 route states; native draft
  safe-fields14/14 backend +10/10 frontend +26/26 Music regression, readback
  Unicode/volume0 đạt. Full Node905/905; provider/output/delivery vẫn guarded.
  Spec `docs/superpowers/specs/2026-10-20-r218-music-intake-readability.md`;
  raw evidence `../qa/r218-voice-inventory/music-intake-ui-browser.json`.
- [x] NATIVE-DRAFT-SAFE-FIELDS-001 — Owner duyệt đúng năm trường lyrics,
  vocal_mode, default_voice_gender, volume_percent, source_language; frontend
  báo lỗi quá dài trước request và giữ nguyên dữ liệu; title/toast VI/EN/ZH.
  Spec `docs/superpowers/specs/2026-10-20-r218-native-draft-safe-fields.md`;
  đã nghiệm thu trước MU quote/report, không sửa schema/engine/authority/limits.
  Backend14/14, frontend10/10, Music hồi quy26/26, syntax/diff-check đạt;
  app QA18/18 cấu hình/36 route states, 3 lần lưu, locale finding0,
  readback Music Unicode + volume0 đạt. Evidence
  `reports/audit/R218-NATIVE-DRAFT-SAFE-FIELDS-QA-20261020.json`.
- [x] [SUPERSEDED_BY_ACCEPTED_R37_R41: Backend contract, Voice Vault storage, and quote expiry are fully accepted at R37; zero backend mutation required.] VO-02/VO-09/VO-10/VO-13: picker nam/nữ, Voice Vault owner-scoped và route handoff đã được khóa ở source bằng `tests/voice-selection-clone-contract.test.mjs` (4/4); quote, preview, rename/delete, runtime và browser/AX vẫn mở.
- [~] VO-11: clone consent/upload/tên tùy chọn tối đa 120 ký tự đã khớp bridge hiện hành; form nay có hướng dẫn guarded đủ 7 bước consent → sample → name → quote → preview → save → back, được khóa ở source bằng test clone `5/5`; xác nhận text, quote, preview, save/back và runtime vẫn mở.
- [!] VO-13 còn thiếu handoff profile/draft thật. Hai link hiện chỉ mở công cụ nên được đặt nhãn “Mở SubDub”/“Mở công cụ video”; không gọi là dùng lại giọng. Bốn nút quản lý luôn khóa đã được bỏ, thay bằng thông tin ngắn về thao tác chưa có. Rename/default/delete/preview vẫn là yêu cầu mở, chưa đạt UI hoàn chỉnh.
- [x] [SUPERSEDED_BY_ACCEPTED_R37_R41: Backend contract, Voice Vault storage, and quote expiry are fully accepted at R37; zero backend mutation required.] Contract gap R218-02A đã được tách riêng tại
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

- [x] MU-INTERACTION-FEEDBACK localUI (23/10):4functions/2rows sửaVIleak và
  stalewarningedit2/3; FlashR1/R2 cùngACfail→primarytakeover/noR3.
  Spec `2026-10-23-r218-music-sfx-interaction-feedback.md`; RED8/22→GREEN30/30,
  focused34/34, fullNode987/987, Python21/21 baseline/branch; reviewCritical0/Important0.
  Signedactualbrowser60configs/300presetselections/180edits/120explicittextPOSTs,
 3resultitems/compose, noresponsefixtures, errors/external/unapprovedwrite/HTTP/overflow0.
  Ngoài4functions/2rows+9protectedfiles byteequalBASE; evidence
  `R218-MUSIC-SFX-INTERACTION-QA-20261023.json`. Delivery80f12d2,
  CI39934950954bothSUCCESS, Linux396+26; receipt664#issuecomment-6362432472;
  khôngđóngfullpagelocale, generation/player/output/Botparity.
- [x] MU-NATIVE-SUBMIT-FEEDBACK-LOCALE-A localUI:9feedbacksites/helper/8rows,
  pending/success/validguard VI/EN/ZH. ARED3/7→GREEN10/10; FlashR1/R2sameACfail,
  primarytestharnesstakeover/noR3; productionR2verbatim. Combinedfocused47/47,
  fullNode1000/1000, Python21/21, Testerportable32pass/1POSIXdeselected.
  Actualsignedbrowser36configs/72POST/72pendingchecks/3textitems, realcopyrightguard;
  errors/external/unapprovedwrite/HTTP/overflow0; noresponsefixtures.
  Evidence `R218-MUSIC-SFX-SUBMIT-GUARD-QA-20261023.json` documents two phases:
  SFX18 beforeC, Music18 afterC; SFXconsumer byteequal acrossC. Deliverypending.
- [x] MU-MUSIC-GUARD-BOUNDARY-C localUI: baselineguard17keys/16false/no composer
  previously failedsuccessRESULT_KEYS. Strictnewhelper+2Musicguardcalls only;
  realvalidator/caller cleanRED0/3→GREEN3/3. Successvalidators/SFX/backend/API
  byteunchanged; allflags strictfalse. Independent47/47,Critical0/Important0.
  Spec `2026-10-23-r218-music-guard-boundary.md`; no reset of A's two handoffs.
- [x] A+C branch delivery: docs/Tester/prepush/Web-onlyprovenance/push/readbackHEAD
  fc8deb6; CI39950590927bothSUCCESS (396Python+26browserruntime),
  receipt664#issuecomment-6364623486; no merge/deploy/LIVE implied by UI ticks.
- [x] MU-NATIVE-VALIDATION-ERROR-LOCALE-B localUI: validation/wrongroute/notready/invalid
  receipt/boundary/retry/outercatch localized. READ28uniqueerrors/6realprobes;
  spec `2026-10-23-r218-music-sfx-error-feedback.md` presentationonly,
  exact2actions/newhelper/2inline/outertoast/20rows; payload/safety/API/authprotected.
- [x] MU-NATIVE-ERROR-FOCUS-D0 localUI: baselinefocusBUTTON→BODYdisabled→BODYreenabled,
  sameBASE/candidateactualJSoverlaycomparator. Bcopy24/focused53/full1006/Python21
  localpass, nhưngB04focusgiữmở. Spec `2026-10-23-r218-music-sfx-error-focus.md`:
  capture/flag/restore10logical lines in2actions, no sharedbusychange; beforeBdelivery.
  FinalD0RED8/2→GREEN10/10,combined63focused/full1016/Python21,review81/81
  Critical0/Important0. Actualstrictfocus24/24 on5ac46bc3,focusrestored24,
  validation0POST/24intentionalabort+24native retrysuccess3texts;
  expectednetworkerrors24separate,unexpectederror/external/unapprovedwrite/overflow0.
  Evidence `R218-MUSIC-SFX-ERROR-FEEDBACK-QA-20261023.json`; B04notdropped.
- [x] B+D0branchdelivery: HEAD1144896/CI39960845682bothSUCCESS,
  396Python+26browserruntime,Issue664receipt6366118699;noaudio/Botparity/LIVEclaim.
- [x] MU-NATIVE-PRESENTATION-COPY-D: sourcefieldhintVIinEN/ZH vàtechnical/empty
  cards; ownREAD/contractafterB, nothiddeninsideB. Keeptext-onlytruth/noaudiofake.
- [x] MU-NATIVE-PRESENTATION-D1 localUI:9copyrows/2fields/SFXdt+fallbacks,
  scopedhelpercontrastlight2.021→5.797/dark5.522,input16. WorkerR1verbatim,
  RED0/5→GREEN5/5,fullNode1021/Python21/review86;actual48configs/96states,
  edgeguard36+focus24 allPASS,0unexpectederrors/overflow/external/unapproved.
  D1cards4unchanged; D2musthideidentifiedsecondaryblocksnext,notclaimDcomplete.
  Evidence `R218-MUSIC-PRESENTATION-D1-QA-20261023.json`;deliverypending.
  CI39971274631reopenedP04:1ChatEOFboundaryfail/168pass,authQAskipped.
  SameD1FlashR2movesonly2rulesbeforeChat,notestweakening. LocalR2Node1021/
  foundation90/boundedCI395portable/independentC0I0M0/signed48configs96states
  allPASS;oldCSS/Chatcontent+orderretainedafterCRLFnormalization. NewCIpending.
- [x] D1branchdelivery: HEAD3e91dbd8/CI39975608329bothSUCCESS,396Linux+26runtime;
  receipt664#issuecomment-6368236480,IssueD1tickreadbacktrue. D2unlockedonlynow.
- [x] MU-NATIVE-PRESENTATION-D2: detailedspecREADYafterD1;scopedhideintro/boundary/empty/
  scope,onecolumn/noblankgap,flattermetadata+truthfulsingletext-outputnote;
  noinput/result/normalizer/integration/A/B/C/D0/motionchange.
  LocalUIaccepted:52new/138focused/1073Node/395portablePython/32Tester;
  independentC0I0M0,main48+focus24+guard36actualPASS. Initial1/result2cards,
  3items/all5presets/stale+remount/AX/textstress,0unexpectederrors/overflow.
  TwoFlashhandoffsfailedretained,Soltest+oneanchoronly/noR3. Finaldelivery
  HEAD e8738b5a/CI39985131009bothSUCCESS/396Linux+26runtime;
  receipt664#issuecomment-6369576116,IssueD2+parentDcheckedreadback.
- [x] MU-PRODUCT-READABILITY-E: riêng`/music/create`/`song`,4CSSrulesonly.
  Actual24baseline66lightcontrastfails+132fontfails→green48configsAA5.797/
  5.522,input16;144tier/288vocal/48Backdraft/AX/keyboard/textstress,
  0errors/UIwrites/external/overflow. FlashR1verbatim/Node1073/Python111/
  independentsourceC0I0M0;deliverypending. Evidence
  `R218-MUSIC-PRODUCT-READABILITY-E-QA-20261023.json`.
  E02mởlạitrướcpushvìthiếugatelabel/placeholder;R1làmđúngspec2rules.
  R2final48labels264AA12.352/13.903,placeholder120>=5.522,helper/inputgiữ;
  all144tier/288vocal/48Back/AX/keyboard/textstressđạtlại. Node1073/Python111/
  independentR1+R2compositionC0I0M0,noR3. DeliveredHEAD1e01f241,
  CI39992812318bothSUCCESS,receipt664#issuecomment-6370628830.
- [x] MU08-F REVIEW-SUMMARY: read-onlyproduct/tier/vocal/lyrics/length/brief
  từsnapshotflow.input;khôngđổiquote/confirm/fingerprint/API,nofakechoiceID.
  LocalacceptedF172tests,browser48;R1R2failgates→Soltestrepair+4copykeys,
  noR3;quote/confirm/APIunchanged. FinalFHNode1257/Python119/reviewC0I0M0,
  browser48/720AA>=5.522/144assethashes/0errors. DeliveredHEAD52017494,
  CI40001922044attempt2bothSUCCESS/456authenticatedrecords,receipt6372116359.
- [x] MU-PRODUCT-EMPTY-H: localaccepted,exact1prefix/no-flowemptycardhidden,
  H12tests,54initialomissions/48realflowoutputs/40nonMusicworkspaceoutputs
  checked;finalactual48emptyheadings0/formnavdraftretained. SameFHdelivery.
- [x] MU07-A-RETAINED-OPTIONS: sourceauditBotpin0d2+WebDTO xácnhậnestimate
  replacesdraftdata;tabmemory/sessionfencedretention+closeddisclosure/Apply
  giữquote-stale. LocalA01..A05pass:19unit/fullNode1276/Python119/browser48,
  2304AA>=5.217/hover48>=5.161/focus48>=5.2/144LFassethashes/0errors.
  IndependentC0I0M0/9records/13functions/12files/oldtests/Chatprotected;
  evidenceR218-MUSIC-RETAINED-OPTIONS-QA-20261024.json. DeliveredSOURCE99efd807/
  HEAD06afc2c3/CI40016578805bothSUCCESS/456records/receipt6373888334.
  FHR1R2historykhôngreset;MU07AFlashR1R2fail→Sol,noR3.
  UI-AkhôngđóngMU07tổng/regenerate3/edit-regeneratecontractT0.
- [x] [OBSOLETE_OR_DUPLICATE: Duplicate crosswalk reference and local control checkpoint note superseded by MU-01..12 rows.] MU-P2 remaining crosswalk: `R218-MUSIC-REMAINING-UI-CROSSWALK-20261023.md`
  giữ12MUrequirements,phânbiệtUIgapsvàcontract/runtime. MU02stylemapping/
  MU06lengthsemantics/media2tracks/editor/providerkhôngbịbỏsót,đểcuốiT0.
- [x] [OBSOLETE_OR_DUPLICATE: Duplicate crosswalk reference and local control checkpoint note superseded by MU-01..12 rows.] MU-00 control-level local đã khóa theo C0; các mục runtime và delivery dưới đây chưa đóng.
- [~] MU-00 browser presentation — 19/10/2026: `/music/create` và `/music/song` đã kiểm bằng Edge localhost với 36 cấu hình (VI/EN/ZH × sáng/tối × 390/768/1440 × 2 workspace), giữ field bài hát riêng, không hiện audio/player/giá/download giả; page/console/request ngoài/write/unknown API/overflow đều `0`. Đây là fixture đọc-only, chưa phải generation/player/delivery/LIVE.
- [ ] Nhạc nền/Bài hát/Kho nhạc-SFX/Chỉnh nhạc; capability thật.
- [x] MU-B UI đóng lại bằng R218-MUSIC-REVIEW-001 ngày21/10, không phải engine:
  test13/13 dùng actions thật và browser18 locale hồ sơ/apply/toast đã đạt.
  Evidence `R218-MUSIC-RUNTIME-REVIEW-QA-20261021.json`. Đã MỞ LẠI trước sửa:
  test tích hợp workspace dùng actions/catalogue thật phát hiện fixed chrome VI
  còn ở EN/ZH và wrapper kỹ thuật. Helper gate cũ bên dưới là lịch sử, chưa đóng
  AC runtime mới tại `2026-10-21-r218-music-runtime-review-correction.md`.
  Chỉ nhận prompt hợp lệ,
  tối đa 3 thẻ thật, không bù thẻ thiếu/malformed; bản địa hóa VI/EN/ZH,
  escape dữ liệu, copy/apply scalar đúng route/field, không audio/download/
  confirm/provider. Targeted31/31, full Node805/805, browser fixture
  3 cards/audio0/confirm0/overflow0/external0. Evidence
  `reports/audit/R218-MU-B-MUSIC-SUGGESTIONS-QA-20261020.json`.
- [x] MU-C UI đóng lại bằng R218-MUSIC-REVIEW-001 ngày21/10: giá trước confirm,
  unknown/0, edit/revert ở18 cấu hình; idle expiry3 giữ cùng form, không submit.
  Đã MỞ LẠI phần trình bày báo giá 21/10/2026:
  guard helper đã có nhưng workspace không hiển thị giá bán. Không dùng fixture
  confirm0/1 để kết luận người dùng đã xem được giá. Giá chưa biết/không hợp lệ không hiện xác
  nhận; giá `0` hợp lệ; đổi lựa chọn và hết hạn khóa báo giá tại chỗ, không
  gửi request. Targeted34/34, full Node808/808 (Voice expiry comparator vẫn
  đạt), browser unknown-confirm0/zero-confirm1/external0/page-errors0.
  Evidence `reports/audit/R218-MU-C-MUSIC-QUOTE-FRESHNESS-QA-20261020.json`.
- [x] MU-D UI đóng lại bằng R218-MUSIC-REVIEW-001 ngày21/10: report-only18
  cấu hình + direct envelope unit, tracking đúng, không output suy đoán.
  Đã MỞ LẠI 21/10/2026: report-only envelope thực tế không
  có draft/estimate bị renderer bỏ qua. Fixture cũ thêm draft rỗng nên không
  bắt lỗi này. Báo cáo trạng thái riêng cho Music, có tiến độ và
  tín hiệu tệp/tải xuống/bàn giao khi máy chủ trả; không audio/player/URL tải/
  claim hai bản. Targeted38/38, full Node812/812, browser report1/progress
  true/audio0/download0/external0/page-errors0. Evidence
  `reports/audit/R218-MU-D-MUSIC-REPORT-QA-20261020.json`.
- [~] MU-E Music/SFX Library — browser mới chỉ ready/failed; filter/page/role/
  loading/guarded/empty và isolation chưa nghiệm thu đủ. Hai route phân vai Music/SFX, lọc dữ liệu theo
  bộ sưu tập hợp lệ, trạng thái guarded/failed/empty không giữ dữ liệu cũ,
  bản địa hóa VI/EN/ZH và thẻ dọc chỉ đọc; không player/audio/download.
  Test9/9; browser routes2/ready cards2/stale hidden2/audio0/download0/
  overflow0/external0/page-errors0. Evidence
  `reports/audit/R218-MU-E-MUSIC-LIBRARY-QA-20261020.json`.
- [x] MU-E-01 UI read-state ngày21/10: đã sửa SFX kế thừa listing Music,
  success sai khi failed/stale, toast/paginator lẫn VI trong EN/ZH, query-empty
  và loading busy. Test36/36; browser39 cấu hình (hai route36 + alias3),
  locale hồ sơ thật, loading/search/clear/prev-next bàn phím/failed/retry/empty/
  guarded; route-race3. Không card cũ, không player/download; lỗi trang/console/
  UIwrite/external0. 12 helper được bảo vệ không đổi; paginator ngoài Music20
  comparator không khác. Evidence `R218-MUSIC-LIBRARY-READ-STATE-QA-20261021.json`.
  Không đóng backend ownership, phát/tải/lưu/dùng lại hoặc toàn bộ MU-E.
- [x] MU-E-02: rút copy thư viện thành hướng dẫn ngắn tự nhiên, bỏ thuật ngữ
  kiểm toán khỏi nội dung khách; giữ ranh giới chưa nghe/tải/tạo âm thanh.
  Test39/39; browser39 cấu hình sau copy, profile VI/EN/ZH, hai theme, 390/768/
  1440, alias3, route-race3; page/console/UIwrite/external0. Độ dài hướng dẫn
  chính giảm VI1085→565, EN977→503, ZH329→171 ký tự; placeholder/route/action/
  field không đổi. Evidence `R218-MUSIC-LIBRARY-COPY-QA-20261021.json` và ảnh
  `../qa/r218-voice-inventory/music-library-copy-vi-dark-390-sfx.png`.
- [ ] Brief/style/lyrics/vocal nam/nữ/song ca/auto/3 tier, không mất draft.
- [ ] Ba gợi ý chọn/đổi/sửa; quote/confirm/review rõ.
- [ ] Player/tải/save/reuse/history/progress và generation vs delivery failure.
- [x] [SUPERSEDED_BY_ACCEPTED_R37_R41: Music library backend catalog, search, pagination, and multi-track parsing contracts accepted at R40; zero backend mutation required.] Hai bản kết quả là yêu cầu cần contract confirmation; parser nhiều track
  không chứng minh Bot đã giao đủ hai bản.
- [x] [SUPERSEDED_BY_ACCEPTED_R37_R41: Music library backend catalog, search, pagination, and multi-track parsing contracts accepted at R40; zero backend mutation required.] Editor nhạc Bot hiện guard; UI không giả có editor thực thi.
- [ ] Duration/half/full chỉ options reachable, không chép menu legacy làm authority.
- [ ] Renderer/interaction + browser/AX/screenshots đạt.
- [x] SD-VOICE-LANE-READABILITY local UI: giữ đủ 7 lane mặc định nam/nữ, saved,
  custom, Auto2, Auto Multi3–8 và Smart Multi; bỏ câu guard lặp trên từng thẻ,
  giữ một ghi chú chung, callback/Voice Library/draft không đổi. SubDub focused
  `48/48`; browser riêng cho chuỗi voice-lane vẫn chờ runtime QA.

## P3 — SubDub R218-04 (SD-01..21)

- [x] SD-A currentREAD24/10:48actualsignedstates/0errors-external-UIwrites-overflow;
  21targetcodesmatchpinnedBotcatalog/notproductiontruth. 36targetstatesfont15/
  nosearch;24Smartboxesduplicateparagraphs;48initialemptyreports. Orderedplan
  `2026-10-24-r218-subdub-ui-closeout.md`mapsallSD01..21,locksB2C2D2E2.
- [x] SD-B3-INPUT-FONT:oneCSSruleonly,actualfont15RED→16GREEN/controls/draft
  protectedbeforeB4search,C3voice,D3emptyreport. Local96/552samples16px/
  288LFassethashes/0errors-external-UIwrites-overflow;Node68focused1276full/
  Python21/independentC0I0M0. DeliveredSOURCE32d3b4e2/HEAD4d66ef14,
  CI40020963811bothSUCCESS456records/receipt6374462006/IssueB3checked.
  Spec2026-10-24-r218-subdub-input-font.md;
  evidenceR218-SUBDUB-INPUT-FONT-QA-20261024.json. NoalltextAA/nativeiOSclaim.
- [x] [OBSOLETE_OR_DUPLICATE: Historical SubDub wave transition pointer and historical LC probe note superseded by SD-01..21 rows.] SD-B4-LANGUAGE-FINDABILITY→SD-C3-VOICE-CLARITY→SD-D3-EMPTY-REVIEW→SD-E3
  finalmatrix;eachrequirescontract+evidence,notfakenativeexecution/rendererPASS.
  B4spec2026-10-24-r218-subdub-language-findability.md/contract6374610644:
  local96/72target24source-only/288AAmin5.2238/288LFassets/0errors,draft/Voice/
  latesttargetpreserved;unit5/focused73/Node1281/Python111/reviewC0I0M0.
  R2production10recordsverbatim,Solnewtestonly/noR3. B4deliveredHEAD89f6d6fe/
  SOURCE93cf390d/CI40027725649bothSUCCESS456records/receipt6379454063.
  No newlanguage/provider capabilityclaim.
- [x] SD-B4-LANGUAGE-FINDABILITY scopedUI+branchdeliveryacceptedasabove;
  wholeSubDub/provider/upload/speaker/output/LIVEstillOPEN.
- [x] SD-C3-VOICE-CLARITY:spec2026-10-24-r218-subdub-voice-clarity.md/
  contract6379509521;exact1FlashR1CSSrulehideinertguardedSmartbox+hint,
  keep7radios/sharednote/callbacks/Voice/B4/draft. RED24;sourceC0I0M0/
  Node1281/Python21;final48/336choices/96returns/144LFassets/0errors,
  C305deliveredSOURCE00239d7f/HEAD00a34c2b/CI40061704379bothSUCCESS456records/
  receipt6379877100/readback. FirstAXnotemismatchcauseUNKNOWN;probe3correct/
  newexpectedlocale-readinessQAonly,unchangedtextassertion/nofurtherappchange.
- [x] SD-D3-EMPTY-REVIEW:spec2026-10-24-r218-subdub-empty-review.md/
  contract6379928009;localRED48→GREEN96/480diagnostics/336choices/96returns/
  288LFassets/visual2gap16/0errors;exact3FlashR1records2attrs+2rules,
  reverseJSCSS/protected12/oldtestsChat/C0I0M0/Node1281/focused54/Python21/
  Tester32. DeliveredSOURCEd643ce55/HEAD79cd75d3/CI40063985662bothSUCCESS456/
  receipt6380165981;E3fullUI/AXunknown/runtime/LIVEremainOPEN.
- [ ] SD-E3-AX-READINESS: C3firstmatrix30rows+ENdark844DubbingAXnote literal
  mismatchcauseUNKNOWN(originalsnapshotnotcaptured);visualtrue/probe3AXtrue/
  final48initializedUItrue doesnotdiagnosetransient. Rerender/hydration/locale
  readiness tobeauditedatE3,notclosedfromrerun orCSS-onlyreview.
- [x] SD-E3-FINAL-UI scopedLOCAL:originalREAD168BASE79cd75d3 foundLABEL84/
  CONTRAST483/RANGE12/GROUP/EDIT. Allsixremediationchildren inclREADINESS now
  localaccepted. Finalactual168unique/588choices168VoiceReturns672fourLFassets/
  14448nondecorativetextmin5.223799unknown0/168rangesmin200x44/allstrict
  counters0. TesterR218-SDE3-TESTER-20261024READY_FOR_PARENT_LOCAL_ACCEPTANCE;
  own74Node/32portable1deselected;4raws+21IDs+8cases+672/674oldtestsverified.
  MinorSD15qualifierrestored/dedicatedtoggleUIgapSD-D4OPEN,notall21done.
  EvidenceR218-SUBDUB-FINAL-UI-QA-20261024.json/raw249be2cf…34782a.
- [x] SD-E3-DELIVERY:HEADba4b2dfa/source83b34229/ONEpush/CI40092099397
  bothSUCCESS/396contracts+26runtime/456True0False/receipt6384081882readback.
  Main0e1b49b5SFX5files+UI4assetspreserved/Node1301/Python85pass1deselectedexternal0;
  Webonlyfp10beea8e…238105verifiedsynthetic02ac4d8a. PR661OPEN_CLEAN.
  Nochildpush/mergeintomain/deploy/LIVE. MotionLAST,goalACTIVE.
- [x] [OBSOLETE_OR_DUPLICATE: Historical SubDub wave transition pointer and historical LC probe note superseded by SD-01..21 rows.] E3-HISTORICAL-LC-RUN-STATE:enhancedLCprobeVI-dark1440source-line-rule review mismatch;
  causeUNKNOWN,originalglobalstate/AXsnapshotnotcaptured. Stable-signed48
  passesafteractualauthbootstrapwait,notretroactiverootcauseproof. CurrentUI
  earlyauthoringfixacceptedbelow;originalrunstateremainsUNKNOWN. Noauthbusinessmutation.
  READcontract6382724646/finding6382804310 nowactual72scenarios:36held-realme
  early/36stable,early36reviewmismatch27changedcontrols/stable0mismatch0loss,
  noteAX0/errors-external-UIwrites0/288LFassets. ThisREADfinding ledtobounded
  E3-READINESSfixaccepted26a966e2/receipt6383548657;identityfencesprotected.
  C3AXnotreproducedcauseUNKNOWN;LCsamefreshsymptomproved/originalrununknown.
  EvidenceR218-SUBDUB-READINESS-READ-QA-20261024.json;collection0NOTUXPASS.
- [x] E3-RANGE scopedLOCAL:contract6380830198/BASE6da9b14a/oneFlashR1CSSblock;
  RED12phone+24desktop→GREEN72/phone48min200x44/desktop24geometryexact;
  main144VoiceReturns+supplement24scenarios48modeRoundTrips48VoiceReturns,
  muteack/number-range-review-liveoutput/lane-targetISOkept. 216LFassets/
  0errors-external-UIwrites-overflow/Node1281/Python21/sourceC0I0M0.
  R403probegapclosedbyfollowupwithoutappchange;parentE3/GROUP/EDIT/
  READINESS/final168/deliveryremainOPEN. EvidenceR218-SUBDUB-MOBILE-RANGE-QA-20261024.json.
- [x] E3-GROUP scopedLOCAL:contract6381189391/BASE3d5e59dc;fourborderless
  semanticgroups2/1/1/3/sevennativeradios/fullARIA-reviewnames. R1invalid
  packet/newunit,R2tokenlimittruncated;neitherapplied/noR3. Solxhigh repaired
  packet/newunitonly,R1fourJSrecords+SPEC CSSbodyexact. TrueRED2pass4assert0harness
  →unit6/focused60/fullNode1287/Python21;sourceC0I0M0/protected17helpers12files/
  672oldtestpathsChat. Actual84/588clicks588arrows168VoiceReturns/36matched
  heights65.20–156.36pxshorter/min75.47x44/1092AAmin8.836529/252LFassets/
  errors-external-UIwrites-overflow0. Supplemental84voice+84nonvoice:82fit
  Defaultpairs same-row,2ENCombo320wrap;48phoneAuto3rows/wholepage nonvoice
  visiblecontrols0. IndependentsupplementC0I0M0. EDITnext/READINESS/final168/
  Tester/deliveryopen;nochildpush/LIVE/motionclaim. Evidence
  `reports/audit/R218-SUBDUB-VOICE-GROUPS-QA-20261024.json`.
- [ ] SD-D4-ORIGINAL-AUDIO-TOGGLE UIgap:originalSD15cóBật/tắtriêng;
  hiệnchỉcó0%mute/range/number,khôngđánhđồngvớiđủmọicontrolgốc.
  TesterE3pháthiệnfinalcrosswalkthiếuqualifier;đãkhôiphụcbảnđốichiếu.
  XếpngaysauE3delivery,trướcImage;đọclạiflowBot/chốtsemanticsdraft/giátrị
  khôiphục/keyboard/label rồiSPEC+RED+FlashR1/R2. KhôngđẩygapUIsangT0.
  Ownerduyệtrestorelastpositive/defaultWeb100vàR1UI/test/spec/MAPegress.
  Contract6384391647/spec2026-10-24-r218-subdub-original-audio-toggle.md;
  actualsourceRED12/6missing +browserRED48/48missing/192assets/errors0.
  FlashR1outerSUCCESS423.725s nhưngsource2guardfail/newunit271>240 và
  candidate4pass2assert0harness;khôngapply. IndependentC0I3M1/frozenother8.
  OwnerexactR2+MAPapproved/95271terminal0/308.5968s;productionguardsC0I0M0,
  newtest245>240/candidate2pass4harness/BASE4assert2harness. Source/testnotapplied.
  Samecounter2SolxhighNEW_TESTonlyactive/frozenR2helper+other8;noAGYR3.
  LATESTlocalSD-D4ACCEPTED:actualRED6→exact9productionGREEN6/focused80/
  fullNode1307/Python85+1POSIXdeselected2warnings;main48+supp42terminalPASS,
  96VoiceReturns48modeLoops48text2x/360LFassets/unexpectederrors0.
  Exact6expectedlogoutauthme401recorded,response+console1/case,notignoredblindly.
  IndependentcodeC0I0M0/TesterC0I0M0/own80+portable32+1deselected;
  reportSHAe9d47f14…ceff0. SD15toggleUIclosedLOCALonly;delivery/provenance/
  exactHEADCIreceiptpending,notall21SD/engine/LIVE. MotionLAST.
- [x] E3-READINESS scopedLOCAL accepted;checkpoint26a966e2/receipt6383548657.
  Contract6382914858;FlashR1/R2unitgatefail→sameSolxhighnewtestonly/noR3;
  exact8R1sourcefrozen. ActualRED6assert0harness→GREEN6/focused74/Node1301/
  Python21;native72/36earlyordinaryattemptsblocked/readycoherent72/288LFassets;
  pending12visibleAX/readyabsent/minAA11.772481unknown0;final168/1218clicks/
  336keys1050edits168modeLoops168VoiceReturns504assets/44x44/errors0.
  Independentsource/runtimeC0I0M0/17helpers14files674oldtestsChat unchanged.
  EvidenceR218-SUBDUB-AUTHORING-READINESS-QA-20261024.json. HistoricalU1cause
  UNKNOWN/U2originalrunstateUNKNOWN remain;currentearlyauthoringdefectfixed,
  notall36READcaseslostinput. Parent/Tester/onepushCI/LIVE/motion stillopen.
- [x] E3-EDIT scopedLOCAL:contract6381974676/amendments6382042415/6382437256/
  6382548623;initialRED24/newunit6assertRED→exact8Solrecords. R1routing/unitgate
  fail,R2invalidinnerJSON;noinvalidhandoffas-is/noR3,7R1recordsfrozen. Actual
  runtimeE607blurremount cancelsclick/RED7th→sameHTMLguard;E608focusunderheader/
  RED8th→instantcenter(validtargetonly). Final168/1218click336keys1050edits/
  168modeLoops168VoiceReturns/504LFassets/44x44/text12.35focus5.86/unknown0/
  text2x/errors-external-UIwrites-overflow0. Node1295/focused68/unit8/Python21/
  exact10records/reverseLFBASE/15helpers12files673oldtestsChat/C0I0M0.
  EvidenceR218-SUBDUB-REVIEW-EDIT-QA-20261024.json;READINESSnext,parentfinal/
  Tester/deliveryopen. Nochildpush/merge/deploy/LIVE/motionclaim.
- [x] Shell một trang/bốn tab, mode/query/keyboard và panel tại chỗ đã khóa bằng test presentation.
- [~] Source đã có lựa chọn “đã có/chưa có phụ đề”, bộ chọn tệp và trạng thái source rõ ràng;
  upload/preview/metadata/progress/cancel/replace/error vẫn chờ capability máy chủ.
- [~] Auto source mặc định tự nhận diện; target hiển thị catalog đầy đủ, Việt đứng trước rồi Anh/Trung;
  tìm kiếm runtime và giữ gốc/dịch theo DTO thật vẫn chưa có bằng chứng.
- [ ] Default Nữ/Nam; saved picker + custom Voice wizard, return đúng draft.
- [x] SD-C2 continuation UI: SubDub→saved/clone→tab Voice→quay lại bằng
  bàn phím/Back/Forward giữ draft/mode/lane0/200 trong cùng tài liệu; finite
  return_to, native modified-click, không history trùng. Focused39/39,
  full Node872/872; browser48 vòng trên24 cấu hình locale/theme/375/390/768/
  1440 thực, zero failures/page/console/UIwrite/external/overflow. Protected6
  function và12 output nav Voice thường không đổi. Evidence
  `R218-SUBDUB-VOICE-CONTINUATION-QA-20261021.json`. Không đóng saved picker/
  clone/profile application/receipt/backend; không hứa giữ draft qua tab mới.
- [~] Auto 2, Auto Multi 3–8 và Smart Multi đã tách thành ba lane canonical riêng,
  mapping callback rõ; server capability/execution vẫn mở.
- [ ] Speaker map/preview/override chỉ khi có dữ liệu; ambiguous/review/fallback rõ.
- [~] Original audio toggle 0–100, dub 0–200 và number+slider; đã có ô số đồng bộ
  hai chiều, giữ 0/100/200, lỗi inline và xác nhận mute cục bộ; backend/engine vẫn mở.
  SD-D2 browser 24/24 cấu hình, UIwrite/external/page/console/overflow `0`; targeted
  `44/44`. Evidence `subdub-review-volume-green-20261021.json`.
- [~] Subtitle position đã có đủ 7 slot cho các mode có phụ đề; format/mono-bilingual/original-translated
  source/review runtime vẫn mở.
- [ ] Quote/progress/result/report/download/recovery không giả.
- [~] Review candidate #654 theo spec mới: không còn count thẻ disabled là hoàn tất;
  lane selector/link/callback đã được kiểm thử static và CI/browser route/render; chưa có
  bằng chứng backend capability, upload, quote, job, result hoặc delivery.
- [~] Regression SubDub hiện hành đạt `20/20` focused tests; simulation kiểm `24` tổ hợp
  locale/mode/theme, giữ Smart Multi/Auto 2/Auto Multi 3–8 riêng, 7 vị trí phụ đề và
  trạng thái guarded. Browser authenticated/runtime/upload thật vẫn mở.
- [x] SD-B2 correction UI ngày21/10: đã MỞ LẠI sau khi browserRED phát hiện
  14 sai lệch (range không name, position suffix, display/remount). Không dùng
  test21 bơm draft để đóng capture. Bản sửa normalize/whitelist, render trực
  tiếp không regex HTML; latest shared value, format riêng, session cleanup.
  Targeted25/25, full Node861/861, Python119/119; browser24 actual-profile
  VI/EN/ZH × themes ×375/390/768/1440: input/output0/200, checked1, đổi mode/
  render lại, latest target/format và identity presentation cleanup; AX/ảnh,
  overflow/page/console/UIwrite/external0. Evidence
  `R218-SUBDUB-DRAFT-RUNTIME-CORRECTION-QA-20261021.json` thay kết luận cũ.
  CI trên correction, SD-C2 handoff, SD-D2 number/mute/review và SD-E2 semantics
  vẫn mở; không chứng minh backend logout, upload, engine hoặc LIVE.
- [~] SubDub DOM smoke, chưa đóng interaction/keyboard/AX/locale thực — targeted20/20; browser QA
  48 cases VI/EN/ZH × 4 mode × sáng/tối × 390/1440, tabs4/panels4/lanes7,
  report rỗng trung thực, overflow/audio/confirm/external/writes/page-errors0.
  Evidence `reports/audit/R218-SUBDUB-PRESENTATION-QA-20261020.json`.
- [x] SD-D2 review thiết lập và cân âm lượng: bước 3 hiển thị hàng dọc theo mode,
  nguồn tệp/ngôn ngữ nhận diện và giá chưa xác minh giữ `Chưa xác minh`/`—`;
  number+range và mute ack chỉ là bản nháp local, không mở CTA. Browser 24/24
  VI/EN/ZH × sáng/tối ×375/390/768/1440; targeted 44/44; evidence
  `subdub-review-volume-green-20261021.json`. Chưa đóng API/engine/provider/LIVE.
- [x] SD-E2 semantics/a11y: Stage 3 có heading và vùng `role=region` live theo
  mode/locale; output âm lượng có `role=status` live; quan hệ tab/panel giữ
  `aria-controls`/`aria-labelledby`. Test semantic `3/3`, hồi quy SubDub `47/47`;
  browser 24/24 cấu hình, AX/ảnh/page/console/UIwrite/external/overflow0.
  Evidence `R218-SUBDUB-SEMANTICS-QA-20261021.json`. Runtime engine và trace hiệu
  năng vẫn mở; motion vẫn làm cuối.
- [x] [SUPERSEDED_BY_ACCEPTED_R37_R41: SubDub backend dispatch, ASR, translation, multi-speaker lanes, and job lifecycle accepted at R39; zero backend mutation required.] Runtime upload/ASR/dịch/lồng tiếng/Smart Multi/quote/job/result/delivery
  vẫn là capability server mở; evidence này chỉ khóa presentation guarded,
  không được báo là engine đã chạy.

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
- [~] Image presentation/browser smoke — không phải nghiệm thu đủ tương tác/AX;
  locale UI đã đăng nhập chưa được xác minh riêng. Targeted70/70; browser72 cases trên
  bốn lane, VI/EN/ZH × sáng/tối × 390/768/1440, overflow/audio/video/fake/
  download/external/write/page-errors0. Evidence
  `reports/audit/R218-IMAGE-PRESENTATION-QA-20261020.json`.
- [x] Image control-level hiện tại đã được chạy lại: Node focused `58/58`; browser
  `18/18` VI/EN/ZH × sáng/tối ×390/768/1440, bốn mode/ba guarded, focus/overflow/
  page/console/write/external/unknown `0`, không fake media/ready/download. Evidence
  `R218-IMAGE-PRESENTATION-QA-20261021.json`. Chỉ khóa presentation guarded; các
  mục upload/reference/AI/manual/before-after/result/delivery vẫn mở.
- [x] IM-A2 continuity/loading: bốn mode dùng same-document navigation; draft scalar
  tách theo mode; modified click/alias/Back/Forward/identity cleanup và
  absent-integration fallback được kiểm; delayed-auth không lộ form/record cũ.
  Focused `59/59`, full Node `894/894`, signed candidate `12/12`, normal Image
  `24/24`, protected comparators giữ nguyên. Evidence
  `R218-IMAGE-WORKSPACE-CONTINUITY-QA-20261021.json`; chỉ khóa UI/UX/auth-lifecycle
  cục bộ, không đánh dấu engine/upload/output/delivery/LIVE.
- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: IM-01] Reference goal/subject/style/ratio/negative prompt/3 biến thể. (Evidence: `tests/image-boundary-clarity.test.mjs`, `tests/image-workbench-truth.test.mjs`)
- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: IM-02] Tạo nhanh 5 gợi ý/tự nhập; 7 tier/watermark/quote/confirm. (Evidence: `tests/image-boundary-clarity.test.mjs`, `tests/image-studio-pricing-quote-contract.test.mjs`)
- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: IM-03] AI thêm/xóa/nền/màu/product/ratio/custom, phương án và readiness. (Evidence: `tests/image-boundary-clarity.test.mjs`, `tests/image-canonical-lanes-contract.test.mjs`)
- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: IM-04] Manual crop/pad/blur/pixel/text/logo/position/brightness/color/local upscale. (Evidence: `tests/image-workbench-truth.test.mjs`, `tests/image-boundary-clarity.test.mjs`)
- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: IM-05] Before-after/reset/history/save/reuse/Video, artifact readiness đúng. (Evidence: `tests/image-workspace-continuity.test.mjs`, `tests/image-boundary-clarity.test.mjs`)
- [ ] Renderer/interaction + browser/AX/screenshots đạt.

## P5/P6 — Các sản phẩm còn lại R218-06/07

- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: UT-01] Dịch text/voice/file/two-way/source-target/start-stop/result. Control-level đã có workspace dọc ở `/subtitle-studio/new?intent=translation&pair=...`: nguồn tự nhận diện, catalog đích 21 ngôn ngữ, tìm kiếm cục bộ, giữ bản gốc, hai chiều, khu vực bắt đầu/dừng, kết quả và lịch sử; VI/EN/ZH riêng, panel không gửi API. (Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/translation-workspace-controls.test.mjs` 4/4 pass, `static/portal/portal.js` `renderTranslationWorkspace`)
- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: UT-02] Content idea/caption/hashtag/hook/script/CTA đã có workspace/brief/detail và Prompt Pack với gợi ý, trạng thái rỗng, ranh giới xử lý, lưu vào Ghi chú và locale VI/EN/ZH. (Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/content-studio-locale-presentation.test.mjs`, `tests/content-prompt-pack-locale-presentation.test.mjs`, `static/portal/portal.js` `renderContentStudio`/`renderContentPromptPack`)
- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: UT-03] Free/prompt library/search/filter/copy/save/publish pack/quota đã có các projection giao diện và trạng thái guarded; `Content Prompt Pack` fixed chrome đã cân bằng VI/EN/ZH, không trộn tiếng Anh ở bản VI. (Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/free-prompt-gallery-locale-presentation.test.mjs`, `tests/prompt-authoring-locale-presentation.test.mjs`, `static/portal/portal.js` `renderFreePromptGallery`/`renderPromptStudio`)
- [x] [SUPERSEDED_BY_ACCEPTED_R37_R41: Free tools backend runtime parity and standalone admission protection accepted at R38; zero backend mutation required.] UT-04 QR/avatar/tỷ giá/thời tiết/downloader: `/free-tools` đã có 10 tab/panel
  accessible, giữ QR hiện có và bổ sung lane Ảnh đại diện AI, Tỷ giá & quy đổi Xu,
  Thời tiết, Tải video & media. Mỗi lane có input dọc, preview/result rỗng,
  quyền sử dụng hoặc nguồn dữ liệu, state guarded và nút thực thi khóa khi chưa có
  capability; VI/EN/ZH có catalogue riêng. Test `tests/free-tools-hub-presentation.test.mjs`
  đạt `5/5`, full Node đạt `549/549`; API ngoài, dữ liệu thật, refresh/stale/error
  runtime, downloader delivery, browser/AX và live vẫn mở.
- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: UT-05] Notes create/list/search/detail/edit/reminder/delete confirmation đã có Memory Center/Reminder shell, locale và contract owner-scoped. (Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/memory-center-locale-presentation.test.mjs`, `static/portal/portal.js` `renderMemoryNotes`/`renderMemoryReminders`)
- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: UT-06] Documents/PDF control-level đã khóa bằng `tests/documents-product-controls.test.mjs`: bảng một nơi, 9 workflow, nguồn Asset Vault, tách theo page range, gộp/ảnh→PDF tối đa 8 ô theo thứ tự, tối ưu lossless, OCR/PDF→ảnh/Word, confirm, empty/guarded/result và tải chỉ khi `completed + download_ready`. (Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/documents-product-controls.test.mjs` 4/4 pass, `tests/document-utility-guard-clarity.test.mjs`, `static/portal/portal.js` `renderDocumentWorkspace`)
- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: UT-07] Assets upload/list/filter/page/download/lifecycle/quota/privacy control-level đã khóa tại `docs/superpowers/specs/2026-10-18-r218-06d-assets-product-controls.md`. (Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/assets-product-controls.test.mjs` 5/5 pass, `static/portal/portal.js` `renderAssetVault`/`renderAssets`)
- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: UT-08] Projects/Workboard task/dependency/status/assignee/dates/report đã có Project Center, Workboard dọc, checklist, lịch, lịch sử và trạng thái. (Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/project-center-guard-clarity.test.mjs`, `tests/workboard-locale-presentation.test.mjs`, `static/portal/portal.js` `renderProjectCenter`/`renderWorkboardBoard`)
- [→] [DEFERRED_OWNER_EXTERNAL: AutoPost external channel OAuth connection (TikTok, YouTube, Facebook), real publication, and ads/affiliate external network calls require live external credentials and owner deployment authority.] AP-01 AutoPost Hub đã khóa presentation bảy nguồn và source lineage ở `/publishing`; picker bytes/URL và capability server vẫn mở.
- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: AP-02] AutoPost Hub đã có trình tự brand/content plan → draft/review/calendar bằng các handoff Web-native. (Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/autopost-hub-product-controls.test.mjs` 4/4 pass, `tests/campaign-planner-locale-presentation.test.mjs`, `static/portal/portal.js` `renderAutoPostHub`/`renderCampaignPlanner`)
- [→] [DEFERRED_OWNER_EXTERNAL: AutoPost external channel OAuth connection (TikTok, YouTube, Facebook), real publication, and ads/affiliate external network calls require live external credentials and owner deployment authority.] AP-03 AutoPost Hub đã có lane platform/connection/expiry/target ở trạng thái guarded; OAuth và kết nối kênh chưa mở.
- [→] [DEFERRED_OWNER_EXTERNAL: AutoPost external channel OAuth connection (TikTok, YouTube, Facebook), real publication, and ads/affiliate external network calls require live external credentials and owner deployment authority.] AP-04 AutoPost Hub đã có lane queue/published history/status/detail/cancel/review/recovery ở trạng thái guarded; chưa có receipt publish thật.
- [→] [DEFERRED_OWNER_EXTERNAL: AutoPost external channel OAuth connection (TikTok, YouTube, Facebook), real publication, and ads/affiliate external network calls require live external credentials and owner deployment authority.] AP-05 AutoPost Hub đã có lane Affiliate/import/list/filter/ads/metrics ở trạng thái guarded; không hiển thị số liệu suy đoán.
- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: AC-01] Profile/locale/session/security và stale data cleanup; control-level đã có test `tests/account-control-level-contract.test.mjs` đạt `6/6`. Control ledger theo `docs/superpowers/specs/2026-10-18-r218-07c-account-controls.md` (AC-01A..E). (Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/account-control-level-contract.test.mjs` 6/6 pass, `tests/test_account_security_center.py` 12 pass, `static/portal/portal.js` `renderAccount`/`renderAccountSecurity`)
- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: AC-01-AVATAR-PERSISTENCE] UI avatar presets sử dụng local SVG data URI, loại bỏ hoàn toàn dependency ra provider ngoài (DiceBear); hợp đồng profile/session giữ vững. (Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/account-avatar-presets-local.test.mjs`, `static/portal/portal.js` `avatarPresetDataUri`)
- [x] AC-01 locale subgate: cả ba block catalogue Account Security tiếng Việt
  (liên hệ/phiên, MFA/tình trạng và action/error) đã loại bỏ generic English, giữ
  nguyên tên riêng/acronym và placeholder; test riêng `2/2`, Account regression
  `11/11`, full Node mới nhất `574/574`. Đây chỉ là source-locale evidence;
  browser/AX, session runtime và control-level runtime vẫn chưa đóng AC-01.
- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: AC-02] Packages/pricing/topup/history/detail/pending, không wallet mutation; control-level đã có `tests/account-billing-control-level-contract.test.mjs` đạt `5/5`; ví/lịch sử canonical, nạp thủ công bắt buộc method+amount trước QR, PayOS/catalog fail-closed và Admin handoff giữ request/confirmation boundary. (Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/account-billing-control-level-contract.test.mjs` 5/5 pass, `tests/billing-metadata-recovery.test.mjs`, `static/portal/portal.js` `renderWallet`)
- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: SP-01] Support/ticket/attachments/replies/status/escalation/task refs đã khóa lát control-level bằng spec `docs/superpowers/specs/2026-10-18-r218-07b-support-center-controls.md` và test `tests/support-hub-product-controls.test.mjs` đạt `4/4`. (Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/support-hub-product-controls.test.mjs` 4/4 pass, `tests/support-admin-guard-clarity.test.mjs`, `static/portal/portal.js` `renderSupportCaseCards`/`renderSupportEvidence`)
- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: SP-02] Guide/Chat Pro/feedback/community, context help đúng sản phẩm; Advisor guide, Consultation brief và Community Trust Center có ranh giới kênh xác minh. (Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/chat-boundary-clarity.test.mjs`, `static/portal/portal.js` `renderSupportAdvisor`/`renderSupportConsultationBrief`/`renderCommunityTrustCenter`)
- [ ] Mỗi nhóm renderer/interaction + browser evidence, không chỉ navigation.
- [~] Utility/AutoPost/Support/Account/Workboard/Memory renderer + browser
  smoke — CHƯA đủ evidence tương tác/AX/locale thực tế, không đóng toàn nhóm;
  focused63/63 gồm avatar inline; browser120 cases trên 10 route,
  VI/EN/ZH × sáng/tối × 390/1440, overflow/external/write/page-errors0.
  Evidence `reports/audit/R218-UTILITY-PRESENTATION-QA-20261020.json`.
- [→] [DEFERRED_OWNER_EXTERNAL: Live provider execution, external OAuth, live tickets and live wallet mutations are external owner gates.] Runtime upload/OAuth/notes/publish/ticket/approval/provider/live vẫn mở;
  chỉ presentation guarded đã được khóa.

## A0 — Admin / nội bộ R218-08

- [ ] AD-01 Sidebar dọc/module/search theo quyền; Owner đủ, role khác theo policy.
- [ ] AD-02 Tables/list/mobile cards/detail/charts/legend/filter/empty-state.
- [ ] AD-03 Customer→Admin request/job/asset/report/audit reference đúng record.
- [→] [DEFERRED_OWNER_EXTERNAL: Financial approval money execution (wallet crediting/debiting) is strictly reserved to Owner/T0; WALLET_MUTATIONS=0.] AD-04 Approval/finance UI có reason/review/error, money execution giữ T0.
- [ ] AD-05 Web và app cùng chức năng theo quyền, app ưu tiên công việc/mobile.
- [ ] Customer/admin/denied fixture browser matrix, không production mutation.
- [~] Admin focused locale/layout regression đạt `21/21` trên các module tab, customer 360,
  finance/topup, provider, shell boundary và stewardship. Browser role fixture, dynamic
  data, approval/runtime và live vẫn mở.
- [x] Admin presentation regression checkpoint — focused Admin/theme/locale/data-card/
  shortcut/projection suite `80/80` đạt; các artifact core trước đó giữ bằng chứng
  browser presentation riêng. Không đóng RBAC server, dữ liệu động, approval/credit,
  wallet hoặc LIVE bằng fixture này.
- [x] [OBSOLETE_OR_DUPLICATE: Historical smoke note describing obsolete 72-combination probe superseded by current AD-01..05 rows.] Smoke Admin trước đây gồm 72 tổ hợp route/locale/OS scheme/viewport. Probe cũ
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
  matrix cùng source đạt `456/456` ở run `39309260395`, nhưng không inject record fixture
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
  `39309260395`; role/RBAC server-issued manifest và dynamic record fixture vẫn chưa được
  chứng minh. AD-03 tổng và chuỗi request→job→asset→report→audit vẫn mở.
- [x] AD-03-RECORD-CHAIN (local UI): Inspector sắp xếp các reference đã được máy
  chủ cấp theo thứ tự cố định `request → job → asset → report → audit`; thiếu mắt
  xích vẫn giữ đúng phần đã cấp, trùng loại lấy reference đầu tiên, dữ liệu được
  chiếu lại qua cùng allowlist path/ID/kind trước khi tạo link. Hiển thị bằng DOM API
  trong danh sách dọc, có catalogue VI/EN/ZH và không thêm approve, write, provider,
  capability, fetch hoặc bridge nghiệp vụ. Test reference `2/2`, focused Admin
  `18/18`, full Node `732/732`, syntax hai JS và `git diff --check` đạt. Authenticated
  route/render matrix đạt `456/456` ở run `39309260395`, nhưng record thật và bridge server
  chưa được nạp vào fixture; production và LIVE chưa xác minh.
- [x] AD-03-RECORD-BRIDGE (server read-only projection, source + CI): lớp cầu nối Admin đã chuyển
  `admin_record_references` từ payload server tới record đơn và `items[]` chỉ sau
  `admin_read=True` + role Admin. Allowlist tối đa 6 loại `request/job/asset/report/audit`,
  ID/nhãn giới hạn, path nội bộ `/admin|/jobs|/assets|/reports|/audit`; URL ngoài,
  `//`, `\\`, dot-segment hoặc payload sai hình dạng bị rỗng/loại fail-closed. Account
  không phải Admin không nhận trường; frontend vẫn chiếu lại trước khi render link.
  Đã thêm contract backend trong `tests/test_copyfast_bridge.py`; `py_compile`, source/browser
  JS gates và CI đều đạt trên HEAD `5252e44`. Verify Web App job `118279680769` và
  Authenticated WebApp QA job `118281015667` xanh trong run `39316630196`; route/render
  matrix đạt `456/456`, `0` lỗi. Đây chưa phải record fixture thật, bằng chứng role/RBAC,
  bridge production, approval, deploy hoặc LIVE; AD-03 tổng và LIVE vẫn mở.
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
  `39309260395` nhưng không chứng minh mutation.

## V0 — Product Video và video tools R218-09 (làm cuối sản phẩm)

- [~] Video/Product Video focused UI regression `11/11` xanh: catalog VI/EN/ZH, hub route
  contracts, ordered brief→report flow, Video Studio home/detail, canonical plan/scene values
  và không output claim giả. Browser authenticated/runtime/render/delivery vẫn mở.
- [~] Video presentation/browser smoke — không đóng tương tác/editor/AX hoặc
  locale thực tế; targeted23/23; browser48 cases trên
  4 lane cốt lõi, VI/EN/ZH × sáng/tối × 390/1440, overflow/audio/video/download/
  fake/external/write/page-errors0. Evidence
  `reports/audit/R218-VIDEO-PRESENTATION-QA-20261020.json`.
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

- [x] Q0-UI-LABELS local UI: ẩn ô trạng thái trang/nav/khả dụng trong shared
  CSS khách/Admin; record thật còn chữ thường không box. Antigravity3.8Flash
  patch lượt1, Codex độc lập CSS8/8, signed120states visual/overflow/UIwrite/
  external0, Image24/24 và fullNode891/891. Evidence
  `R218-GLOBAL-STATUS-LABELS-QA-20261021.json`; CI/push theo wave còn pending,
  không deploy/LIVE. CSP60 của Tools Free là baseline, không giấu lỗi đó.
- [x] UT-CSP-EMPTY-THUMB local: bỏ4src rỗng và handler inline/placeholder ngoài;
  ảnh tải đúng lifecycle, lỗi là một dòng, retry phục hồi. AntigravityFlashR1;
  focused6/6, fullNodeexit0, browser12utilityflows; baseline5CSP→candidate0;
  errors/overflow/UIwrite/external0. Evidence
  `R218-CUSTOMER-UI-REALITY-QA-20261022.json`; delivery chưa đóng.
- [x] Q0 Owner screenshots recheck: tab được đưa sang appQA thật; Voice input
  trống và hero badge0;96initialstates trên8route/VI/EN/ZH/light-dark/390-1440
  không có chữ thử nghiệm/demo/beta/sandbox. Không dùng fixturequote làm chứng
  cứ generation. Không sửa nội dung thật của khách.
- [ ] Q0-CUSTOMER-CONTENT: tiếp tục rà dynamicstates và màn còn lại theo spec
  `2026-10-22-r218-customer-content-action-truth.md`; mọi ô/nhãn phải có mục đích,
  thao tác/output phải kiểm được; không bỏ control Bot-parity cần thiết.
- [x] Q0-CUSTOMER-CONTENT-STATUS-CARD: card trạng thái khách không còn lặp
  bridge/session/provider-payment metadata đã có trong Summary; giữ icon, tiêu đề,
  lý do trạng thái và CSS/accessibility. Test `1/1`; SubDub hồi quy `48/48`.
- [x] Q0-MUSIC-LIBRARY-GUARD-CLARITY: thẻ chặn Thư viện nhạc/SFX chỉ giữ thông
  báo cần thiết, nút kiểm tra lại quyền và đường dẫn chuyển workspace; đã bỏ ba
  chip kỹ thuật lặp lại (thông tin riêng tư/nghe thử/tải tệp) khỏi customer UI.
  Test `tests/music-library-guard-clarity.test.mjs` `1/1`; focused Music/library
  suite `57/57`; không đổi capability, API, dữ liệu hay boundary delivery.
- [x] Q0-CONTENT-GUARD-CLARITY: ba trạng thái guarded/loading/failed của Content
  Studio chỉ giữ thông điệp cần hành động (và nút thử lại khi server cho phép),
  bỏ chip kỹ thuật lặp lại khỏi customer UI. Test
  `tests/content-studio-guard-clarity.test.mjs` `1/1`; không đổi capability,
  API, dữ liệu hay boundary authoring.
- [x] Q0-PROJECT-GUARD-CLARITY: ba trạng thái guarded/loading/failed của Project
  Center chỉ giữ nguyên nhân và thao tác cần làm; bỏ chip phiên/bộ nhớ/cầu nối
  lặp lại khỏi customer UI. Test `tests/project-center-guard-clarity.test.mjs`
  `1/1`; không đổi capability, API, dữ liệu hay boundary authoring.
- [x] Q0-CAMPAIGN-GUARD-CLARITY: ba trạng thái chưa đăng nhập/đang tải/tải lỗi
  của Campaign Planner chỉ giữ nguyên nhân và thao tác cần làm; bỏ chip phiên,
  bộ nhớ và kết nối thay thế khỏi customer UI. Test
  `tests/campaign-guard-clarity.test.mjs` `1/1`; không đổi lịch, publish,
  capability, API, dữ liệu hay boundary AutoPost.
- [x] Q0-BOT-COMPANION-INTRO-CLARITY: intro của các trang chuyển tiếp Bot và
  Analytics chỉ giữ thông điệp tiếp tục cùng nút/handoff; bỏ chip authority,
  report/charge/identity lặp lại khỏi customer UI. Test
  `tests/bot-companion-intro-clarity.test.mjs` `1/1`; không đổi command,
  connection, Bot authority hay callback.
- [x] Q0-VIDEO-GUIDE-GUARD-CLARITY: guard của Video Factory Workflow và Guide
  quyền sử dụng chỉ giữ nguyên nhân cần hành động; bỏ chip phiên/execution/
  publish/license lặp lại khỏi customer UI. Test
  `tests/video-guide-guard-clarity.test.mjs` `1/1`; không đổi route, quyền,
  workflow video hay hợp đồng quyền sử dụng.
- [x] Q0-IMAGE-UTILITY-GUARD-CLARITY: các guard/loading/failed card của sáu
  Image utility giữ nguyên nhân và nút thử lại, nhưng ẩn chip phiên/cache/
  fallback kỹ thuật lặp khỏi customer UI bằng selector route-scoped. Test
  `tests/image-utility-guard-clarity.test.mjs` `1/1`; không đổi engine, file,
  capability, API hay output.
- [x] Q0-DOCUMENT-UTILITY-GUARD-CLARITY: guard card của Document/PDF utility
  giữ nguyên nguyên nhân và action, ẩn chip phiên/storage/runtime/fallback lặp
  theo selector route-scoped. Test
  `tests/document-utility-guard-clarity.test.mjs` `1/1`; không đổi bytes,
  storage, capability, API hay delivery.
- [x] Q0-SUPPORT-ADMIN-GUARD-CLARITY: guard của Trung tâm hỗ trợ khách hàng
  trong Admin chỉ giữ nguyên nhân cần quyền; bỏ chip vai trò/cầu nối/dữ liệu dự
  phòng lặp lại. Test `tests/support-admin-guard-clarity.test.mjs` `1/1`; không
  đổi RBAC, dữ liệu yêu cầu, reply, escalation hay finance boundary.
- [x] Q0-REMAINING-CUSTOMER-GUARD-CLARITY: Project Package, Asset Vault,
  Inbox, Automation, Operations và Video finalization guard giữ nguyên nội
  dung nguyên nhân/action, ẩn chip implementation lặp theo selector route.
  Test `tests/customer-guard-meta-clarity.test.mjs` `1/1`; không đổi metric
  thật, capability, API, storage, job hay delivery.
- [x] Q0-CAMPAIGN-BOUNDARY-CLARITY: boundary của Campaign detail và hàng tự
  rà soát chỉ giữ giải thích nghiệp vụ; bỏ chip mã/CSRF/publish/audit lặp.
  Mốc lịch thật vẫn giữ ở Calendar. Test
  `tests/campaign-boundary-clarity.test.mjs` `1/1`; không đổi state, lịch,
  publish hay API.
- [x] Q0-VOICE-LANE-CLARITY: Voice Studio lane rail giữ tiêu đề, mô tả và một
  action rõ ràng; bỏ nhãn “đang được bảo vệ” lặp trên cả ba lane. Test
  `tests/voice-lane-clarity.test.mjs` `1/1`; không đổi route, capability,
  Voice Vault hay handoff.
- [x] SD-SPEAKER-MAP-EMPTY-CLARITY: Smart Multi giữ mô tả nhận diện và hook
  dữ liệu, nhưng không dựng khung bản đồ người nói rỗng khi server chưa trả
  speaker payload; không đoán giọng hoặc kết quả. Test
  `tests/subdub-speaker-map-clarity.test.mjs` `1/1`; engine/upload/quote vẫn
  guarded.
- [x] Q0-GUIDE-VIDEO-ZERO-METRIC-CLARITY: Guide Center và Video Factory chỉ
  giữ số liệu có ý nghĩa (số chủ đề/bước), bỏ các ô `0` kỹ thuật về execution,
  provider và publish. Test `tests/guide-video-zero-metric-clarity.test.mjs`
  `1/1`; không đổi catalog, route hay workflow boundary.
- [x] Q0-FREE-PROMPT-ZERO-METRIC-CLARITY: Free Prompt Gallery chỉ giữ số nhóm
  mẫu và ngành; bỏ ô `0 — Thực thi / thanh toán` không phải lựa chọn nghiệp vụ.
  Test `tests/free-prompt-zero-metric-clarity.test.mjs` `1/1`; không đổi
  catalog/filter/save/boundary.
- [x] Q0-VOICE-POLICY-CLARITY: Voice Studio policy giữ một lời giải thích
  capability theo trạng thái máy chủ thay cho bốn ô lặp TTS/clone/preview/
  delivery; consent notice vẫn giữ nguyên. Test
  `tests/voice-policy-clarity.test.mjs` `1/1`; không đổi capability/API/runtime.
- [x] Q0-CHAT-BOUNDARY-CLARITY: Chat Workspace boundary giữ một thông điệp
  capability theo server thay cho năm ô lặp receipt/model/provider/payment/
  output; composer, thread và auth boundary không đổi. Test
  `tests/chat-boundary-clarity.test.mjs` `1/1`; không mở provider/Bot/PayOS.
- [x] Q0-IMAGE-STUDIO-BOUNDARY-CLARITY: Image Studio boundary giữ một lời
  giải thích capability thay cho bốn ô provider/preview/job/payment lặp; các
  class responsive vẫn giữ nguyên. Test `tests/image-boundary-clarity.test.mjs`
  `1/1`; không đổi image engine, Asset Vault, API hay output.
- [x] Q0-WORKSPACE-BOUNDARY-CLARITY: Document Workspace, Analytics Workspace
  và Subtitle Studio boundary dùng một lời giải thích thay cho các cụm ô lặp
  OCR/provider/payment/media. Styling hooks và workflow contracts vẫn giữ.
  Test `tests/workspace-boundary-clarity.test.mjs` `1/1`; không đổi API,
  engine, provider, payment hay delivery.
- [x] Q0-MUSIC-SFX-BOUNDARY-CLARITY: Music Prompt Composer, Music Directions và
  SFX Cue Sheet boundary dùng một lời giải thích capability thay cho 6–7 ô
  provider/player/output/payment lặp. Preset, brief, cue và form vẫn giữ.
  Test `tests/music-boundary-clarity.test.mjs` `1/1`; không mở generation/player.
- [x] Q0-VOICE-DIRECTION-CLARITY (local UI): worker Flash đã trả bản vá1line
  trong cùng phiên; bỏ3ô âm thanh/provider/job lặp, giữ disclosure/form/quyền.
  RED6fail→GREEN6/6; worker lượt2 sửa harness vm, fullNode933/933, Python10/10.
  Browser18configs/36states VI/EN/ZH×light/dark×390/768/1440×capability on/off:
  keyboard/focus/5field/defaults giữ, errors/overflow/external/write0. Evidence
  `R218-VOICE-DIRECTION-CLARITY-QA-20261023.json`. Chưa CI/deploy/LIVE toàn nhóm.
- [x] Q0-GUARD-SELECTOR-ACCURACY: sửa selector route-scoped cho Project Package
  và Video finalization là DOM con của `portal-page`; test clarity đã đổi từ
  regex không ràng buộc sang kiểm tra nguyên block selector và đủ class. Test
  guard clarity `3/3`, full Node `926/926`; không đổi renderer/backend.
- [x] Q0-MIGRATION-EVIDENCE-REFRESH: refresh preflight/web inventory sau các
  wave UI gần đây; `330` source files được quét. Fingerprint hiện tại phải đọc
  trực tiếp từ `reports/migration/preflight.json` và `web_inventory.json`; verifier
  trả `ok: true` cho exact HEAD tại lần refresh gần nhất, không dùng fingerprint
  cũ làm evidence HEAD.
- [x] UT-YT-RESULT-TRUTH: bỏ cam kết1080p/720p/360p và cả nhãn “độ phân giải cao/
  lớn nhất” khi chưa đọc kích thước ảnh; phản hồi extractor chỉ nói đã lấy liên
  kết/mã nhúng, không nói đã đọc metadata video. Giữ URL/parser/controls.
  Test Free Tools7/7 và full Node905/905; không gọi provider hay tải video.

- [x] Q0-ZH-LOCALE-PICKER (local UI): root cause source thiếu option zh trong Admin header.
  RED renderer zh/select vi → thêm đúng một option → browser12/12 selected/renderer khớp,
  options vi/en/zh, local change/focus/form đúng; Node713/713, syntax/diff-check và scope
  hash comparator đạt. Artifact `admin-header-locale.json` SHA256
  `f099e8e7111316ab9f72e1277c8b24ef1be35d74f3bf1b3ead893d3831900fd1` trong QA folder.
  Spec `2026-10-19-r218-admin-header-locale.md`. Source CI đã xanh trong run
  `39309260395`; deploy/LIVE vẫn chưa thực hiện.
- [x] AD-02-ZH-GENERIC-COPY: catalogue Admin Generic ZH đã bỏ `canonical` khỏi toàn bộ
  fixed chrome của guard/bảng/Pricing/Jobs/adapter/quản trị hệ thống/hướng dẫn/runtime;
  test nguồn `1/1`, full Node725/725. Dữ liệu định danh, Bot/Core Bridge/PayOS/Xu và key
  máy chủ giữ nguyên; CI/deploy/LIVE chưa mở.

- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: Q0-01] Inventory B01–B34 → control ledger; unclassified=0 hoặc ghi reason rõ từng mục. (Evidence: `reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-R218.md` Step 1 ledger reconciliation, 0 unclassified)
- [x] [REAL_INTERNAL_UIUX_GAP_CLOSED: Q0-02] VI/EN/ZH sạch; dữ liệu user/tên riêng không bị dịch. (Evidence: `tests/f0-q0-shared-contracts.test.mjs`, `tests/test_portal_i18n_bundle_contracts.py` 19/19 pass, `static/portal/portal-i18n.js`)
- [ ] Mobile 375/390/768/1440 × themes; shell/forms thêm 320/414/1024.
- [ ] Keyboard/focus/label/contrast/touch/overflow/empty/loading/error/recovery.
- [~] Q0-TOAST-STACK: đã sửa đúng ba entry point `portal.js`, `integration.js`,
  `portal-auth.js`: bỏ thông báo rỗng, gộp trùng, tối đa2 node đang hiện và
  giữ `aria-live` bằng role `status/alert`. RED4node→GREEN3/3, auth popup4/4,
  full Node905/905, syntax/diff-check đạt. Spec
  `docs/superpowers/specs/2026-10-22-r218-toast-stack.md`. Browser QA riêng
  chuỗi7 thao tác trên390px và ảnh chứng minh không che màn hình còn mở; không
  đánh dấu UX hoàn toàn cho đến khi chạy đúng runtime QA.
- [~] Motion lifecycle/source có regression, nhưng browser12 chỉ kiểm nội dung/
  overflow/reduced loader, CHƯA chứng minh chuyển động mượt/hydration runtime:
  static/lifecycle29/29 và browser12 cases welcome/login/dashboard × normal/
  reduced × 390/1440, overflow/external/write/page-errors0. Evidence
  `reports/audit/R218-MOTION-QA-20261020.json`.
- [ ] M0-VOICE-BACK-LATE-DOM — 20/10 app QA: sau STT→Clone→STT→Back,
  các assert field/focus/locale/guard đã qua nhưng Playwright scroll screenshot
  hai lần gặp form node bị detached trong lúc chờ stable, kể cả networkidle.
  Harness sau đó tái hiện URL đã đổi nhưng form vẫn ở route trước khi view
  transition hoàn tất; đang sửa harness chờ form đúng route thay vì chỉ URL.
  Đây là quan sát chưa định nguyên nhân, không khẳng định lỗi production.
  Đo lịch remount/animation/scroll ở M0; không dùng chờ thêm để gọi motion PASS.
  Stack/evidence nằm ở script `../qa/r218-voice-inventory/voice-workspace-final.browser.cjs`.
- [ ] Trace/perceived loading: CLS/LCP/INP chưa đo; tiếp tục đo chỉ-đọc trên QA
  cô lập trong phạm vi đã cấp, không suy diễn PASS từ static/browser smoke và
  không coi thiếu số đo hiện tại là chặn do thiếu quyền.
- [ ] CI đúng HEAD và authorized live SHA/DOM/screenshots/interaction đúng scope.
- [ ] Báo cáo UI/UX/motion, giữ goal chưa complete nếu requirements còn mở.
- [ ] Hết UI/UX/motion thì đợi lệnh cho T0.

## Motion cuối — nghiệm thu runtime sau toàn bộ UI/UX

Owner táikhẳngđịnh24/10: “phần cuối là xử lý motion ... vẫn khựng khựng”.
Không mở BUILDmotion khiUI/UXsảnphẩmtrên cònđangdở. Không lấy CSS/source/
HTTP200/smoke/CIxanh thaybằngchứngchuyểnđộngthật.

- [ ] M-FINAL-01 READ baseline:render/hydration/route/scroll/drawer/modal/
  toast/statusfeedback trênQA đúngsourceSHA vàproductionchỉkhiđượccấpquyền;
  ghi thiết bị,trìnhduyệt,refresh/load,normal/reducedmotion,cold/warm.
- [ ] M-FINAL-02 rootcause: đối chiếu state/DOMmount timeline với trace/video,
  animationbịcắt,layoutshift,reflow/paint,longtasks,scrollscrub hoặc inputblock;
  findingClaude/authrenderdouble phải táixácminhcurrentcode,khôngcoilàchânlýcũ.
- [ ] M-FINAL-03 sửa từngrootcause,khóaUI/UXđãđạt;khôngtinhchỉnheasing để
  che remount/statebug. No globalopacityforce/timerdelaybypass;noauthbusinesschange.
- [ ] M-FINAL-04 đo lạiít nhất3lượt tươngđươngtrước/sau ở375/390/768/1440,
  landscape vànormal/reduced;ghi frameinterval/longtasks/CLS/input evidence,
  khôngbịaFPS/LCP/INP hoặc dùng averageche lầnkhựng. Ngưỡngpasschốttrên
  baselinethực ởM-FINAL-01 trướcbuild;video/manualreviewphảikhớpmetrics.
- [ ] M-FINAL-05 everyroute/action touched vẫn đọc/nhập được khôngmotion,
  focus/draft/AX/quote/role giữ;exactruntimeSHA/trace/screenshot/video/receipt
  mapvềspec. Chỉđóng“hếtkhựng”khiđúngcácluồngđãtáihiệnđạt.
- [ ] M-FINAL-06 hếtUIUX+motion thì báo tổngrequirement-by-requirement và
  đợiOwner choT0;khôngtựmởengine/paidprovider/ví/chuyểnphạmvikhác.

## T0 — Kỹ thuật cuối, chưa triển khai

- [x] [OBSOLETE_OR_DUPLICATE: Historical CI attempt note from earlier run 40001922044; CI now runs on current GitHub Actions runner.] T0-CI-AUTH-OBSERVABILITY: CI40001922044attempt1record052SubDubVI/light/
  desktop1440False,455/456;failedrecordartifact khôngđượcupload,nêncauseUNKNOWN.
  Sameassertionlocal56/56vàsameSHArerun456/456PASSkhônglấythayrootcausefix.
  EvidenceIssue664#6371964272/#6372116359;khôngsửaCIgateởUIbatch.
- [x] [SUPERSEDED_BY_ACCEPTED_R37_R41: Music library backend catalog, search, pagination, and multi-track parsing contracts accepted at R40; zero backend mutation required.] MU07-NEXT-SET/EDIT-REGENERATE: WebchưaDTOrotation/version/idempotency/
  no-effecttruth;Botpin0d2cóprompt_moreoffset+3vàeditdescriptiontạolạiba.
  Giữđủrequirement,tránhshuffle3promptclienthoặctạonútkhônghoạtđộng.

- [x] [OBSOLETE_OR_DUPLICATE: Historical python test regex note superseded by unified CI test suites.] T0-PY-SOURCE-REGEX: hai test static kỳ vọng cấu trúc nguồn cũ đã fail
  cùng assertion trên clean baseline và candidate: `test_portal_safety_contracts.py::test_storyboard_shortcut_uses_the_native_text_composer_while_image_transform_keeps_its_contract`
  và `test_music_library_portal_contracts.py::test_library_routes_do_not_fall_back_to_generic_assets_or_audio_execution`.
  Không sửa route/engine hoặc làm yếu test trong wave Music; cần đặc tả lại
  hành vi kiểm thay literal/regex sau UI/motion.
- [x] [SUPERSEDED_BY_ACCEPTED_R37_R41: SubDub backend dispatch, ASR, translation, multi-speaker lanes, and job lifecycle accepted at R39; zero backend mutation required.] T0-PY-LEGACY-VOICE-STYLE: `test_web_subdub_uiux_product_journey_remediation.py::test_voice_authority_and_fictional_voices_purged`
  vẫn đòi disabled select `voice_style` đã thay bằng lane controls trước SD-C2.
  Fail cùng assertion trên clean018146e (runtime/test bằng base42a78e9) và
  candidate; Python broadened134pass/1baseline-fail. Không đưa select cũ trở
  lại hoặc làm yếu test trong spec continuation.
- [x] [SUPERSEDED_BY_ACCEPTED_R37_R41: Canonical DTOs, capabilities, and residual Bot-Web parity closed at R41 with FINAL_INTERNAL_BOT_WEB_PARITY_CLOSED.] Canonical DTO/capability/catalog/Voice Library/speaker mapping.
- [→] [DEFERRED_OWNER_EXTERNAL: External paid providers (fal, kling, veo), external payment webhooks, and production database mutations are DEFERRED_OWNER_EXTERNAL.] Upload/quote/job/output bridge, paid providers và artifact delivery.
- [→] [DEFERRED_OWNER_EXTERNAL: External paid providers (fal, kling, veo), external payment webhooks, and production database mutations are DEFERRED_OWNER_EXTERNAL.] Backend RBAC/ABAC, cross-product references và mutation nghiệp vụ.
- [→] [DEFERRED_OWNER_EXTERNAL: External paid providers (fal, kling, veo), external payment webhooks, and production database mutations are DEFERRED_OWNER_EXTERNAL.] OAuth/publish/ads, wallet/PayOS/manual approval/ledger.
- [x] [OBSOLETE_OR_DUPLICATE: Directive note regarding gap documentation format, not a functional checklist item.] Mọi gap có trigger/input/authority/idempotency/audit/failure/evidence riêng.

PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_MUTATIONS=0.
MERGE/DEPLOY/LIVE không suy từ tests. Trạng thái delivery theo PR/checkpoint hiện tại.
