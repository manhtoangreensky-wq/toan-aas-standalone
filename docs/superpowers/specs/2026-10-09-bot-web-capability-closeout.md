# TOAN AAS Bot → Web capability closeout — 2026-10-09 (current-main rebaseline 2026-10-10)

> Đang đọc và áp dụng skill owner-governed-codex cho task này.

## Mục tiêu

Đối chiếu từng nhóm sản phẩm Web với luồng và lựa chọn tương ứng của Bot, rồi
đóng từng khoảng trống bằng một spec hẹp có bằng chứng. “Có route”, “có form”,
“có adapter” và “đã tạo được tệp thật” là bốn trạng thái khác nhau; chỉ trạng
thái cuối cùng mới được ghi `RUNTIME_PASS`.

## Mốc nguồn và phạm vi bằng chứng

| Hạng mục | Giá trị | Giới hạn |
|---|---|---|
| Web snapshot lịch sử của audit cũ | branch `fix/shared-shell-locale-controls-20261008`, SHA `17b9494392cc063e8f9d0f39974da2569009b23d` | Chỉ dùng để hiểu các test/checkpoint lịch sử; đã bị main vượt qua, không còn là current-main authority |
| Web current main đã đối chiếu | `origin/main=86d4ee6e11ddfbc0d4e1dbf63b41d9b3ed7d859b`; docs branch `45b84de83ee9b475bb4366c3ddc2af85b82297c4`, merge-base `17b9494392cc063e8f9d0f39974da2569009b23d` | Mốc source mới nhất đã đọc ngày 2026-10-10; không xác nhận deployed/live và phải làm mới ngay trước khi code |
| Bot snapshot từ audit trước | Branch `fix/p0-subdub-smart-synth-adapter-signature-r1`, HEAD `ae85e84f27f3f5e09c4e05667a34355a758c8a8a`; 7 tracked files modified, 24 untracked status entries | Dữ liệu lịch sử; chưa tái lập trên checkout cục bộ hiện tại. Không dọn hoặc ghi đè thay đổi Bot. |
| Bot checkout đọc được hiện tại | Branch `feature/p0-webapp-copyfast1-core-bridge`, HEAD `32d6d1bfbc8040b0632a44e6a9326ed568cb1a59`, clean | Commit `ae85…` có trong object database nhưng không phải HEAD/ancestor; checkout này chưa được xác nhận là Bot main/deployed source. |
| Bot comparator khác | Detached HEAD `6476f20bdd9f8728a5db0b1d62a245b0d612aea8`, clean | Không chứa object `ae85…`; không chọn làm nguồn chuẩn thay thế. |
| Bot source folder trực tiếp | `D:\TOANAAS\bot telegram`; `bot.py` SHA-256 `7EAE9610073D3000C2A949E78E2E48E0194EB402EEDEA7F9B9328FA09D7F0B0F`, 14.966.481 bytes, LastWriteTime `2026-09-27 16:28:02`; `.git/HEAD` trỏ `fix/p0-subdub-smart-synth-adapter-signature-r1` @ `ae85e84f27f3f5e09c4e05667a34355a758c8a8a` | Chạy từ chính thư mục, `rev-parse` xác nhận worktree và ref; `git status` lỗi `fatal: this operation must be run in a work tree`. Biết ref hiện tại nhưng chưa xác minh clean/dirty, quan hệ `bot.py`–HEAD hoặc canonical/deployed source. |
| Static parity | 7.633 mapping; Web surface 37,56%; 1.923 cần disposition; 353 chưa có Web route | Kết quả quét nguồn ngày 2026-10-09; chưa tái lập riêng trên Git HEAD và dirty overlay. Đây không phải điểm chất lượng hay runtime. |
| Browser/UI regression | Ngày 2026-10-09, Node `--test` trên Music/Voice/Image/SubDub: **110 pass, 0 fail** | Chỉ chứng minh renderer/presentation/guard, không chứng minh provider/artifact |
| Cost/data gates | `PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`, `PRODUCTION_DATA_MUTATIONS=0` | Không chạy provider, không ghi ví, không ghi production |

> **Lưu ý freshness:** các bảng trạng thái sản phẩm phía dưới ban đầu được lập
> từ Web candidate `17b9494…`. Current-main source đã tiến tới `86d4ee6…`; phần
> rebaseline mới nhất ở cuối tài liệu là nguồn hiện hành để quyết định trạng
> thái. Không dùng riêng bảng cũ để giao builder hoặc tuyên bố UI hiện tại.

Nguồn Bot dùng để tham khảo là working tree đọc được. Không import `bot.py`,
không đọc secret/ENV, không gọi Telegram/provider và không coi kết quả này là
runtime production.

Các line reference Bot ở ma trận dưới đây trỏ tới nguồn đọc tại lần audit 2026-10-09;
do Bot working tree dirty, cần xác minh lại khi ledger được dựng từ Git HEAD và
ghi phần dirty overlay riêng. Git recheck ngày 2026-10-10 không sửa Bot.

## Ma trận trạng thái hiện tại

### Music

| Capability | Web hiện có | Gap đã chứng minh | Trạng thái |
|---|---|---|---|
| Nhạc nền | `/music/create`; `brief`, `mode`, `duration_seconds`; hub đánh dấu guarded | Bot bắt đầu bằng tier picker; Web thiếu tier canonical và chưa có `music_background` adapter | `UI_PRESENTATION_ONLY` |
| Bài hát có lời | `/music/song`; có `lyrics/melody/custom`, `seconds/half/full` | Thiếu tier và lựa chọn giọng `male/female/duet/auto`; Web cho `1..600s`, Bot có chuẩn tối thiểu canonical; `half` có thể bị Bot chuyển thành `full` khi readiness không đạt | `UI_CONTRACT_MISMATCH` |
| Thư viện/SFX | `/music/library`, `/music/sfx-library`, Asset Vault/metadata | Không tương đương search/preview/select provider của Bot; Prompt Composer chỉ tạo hướng dẫn chữ | `WEB_NATIVE_SEPARATE` |
| Tạo tệp âm thanh | Chưa có `copyfast_music_generation_job_bridge.py`; runtime allowlist không có music | Confirm bị chặn bởi adapter/runtime gate | `BLOCKED_BY_RUNTIME` |

**Nguồn chính:** Bot `bot.py:162316,169508,171046,171378,173739,174420`; Web
`static/portal/portal.js:733-758,24771`; `copyfast_api.py:229,6391`; test
authority-stop `tests/test_p0_webapp_v3_customer_music_generation_job_bridge.py`.

### Voice

| Capability | Web hiện có | Gap đã chứng minh | Trạng thái |
|---|---|---|---|
| Giọng mặc định | `/voice/tts` có script, nam/nữ, speed, volume; `voice_tts` có bridge và nằm trong active allowlist | Chưa chứng minh end-to-end có audio hợp lệ; test xác nhận runtime readiness không đồng nghĩa có âm thanh/job hoàn tất. Cần đối chiếu lựa chọn neutral và dải speed với Bot chuẩn. | `ACTIVE_PATH_DECLARED_ARTIFACT_UNVERIFIED` |
| Giọng đã lưu | `/voice/saved`, `voice_profile_id`, profile readiness/default marker | Có API profile và validator, nhưng portal đang gửi generic feature phase; chưa chứng minh trace vào dedicated `voice_tts` bridge và artifact | `WIRING_UNPROVEN` |
| Giọng tự thêm/clone | `/voice/clone` có tên, upload, consent | Chưa có clone job adapter/source activation; phải kiểm lại MIME/duration/owner staging; không được gọi profile Studio là giọng dùng được | `BLOCKED_BY_RUNTIME` |
| Quản lý profile | UI hiển thị metadata/readiness | Bot có listen/create audio/set default/use video/download/rename/delete; Web chưa có toàn bộ action quản lý | `PARTIAL` |

**Nguồn chính:** Bot `bot.py:63840,159975,167785,169226,169277`,
`services/voice_clone_pipeline.py:36`; Web `static/portal/portal.js:716-732,30619`,
`static/portal/integration.js:26506,38237`, `copyfast_api.py:7066,7208,6618`,
`copyfast_voice_tts_job_bridge.py:163`, `copyfast_voice_studio.py:1026`.

### Image

| Capability | Web hiện có | Gap đã chứng minh | Trạng thái |
|---|---|---|---|
| Tạo ảnh AI | `/image/create` có prompt/tier/format, draft/estimate surface, bridge validator | Runtime allowlist không có `image_create`; bridge không nhận `format`, nên có latent input mismatch khi mở runtime | `BLOCKED_BY_RUNTIME` |
| Sửa ảnh AI | Hub có edit/cleanup/resize/overlay; Bot có add/remove object, đổi nền, beauty, AI ratio/instruction | `/image/edit` là deterministic Enhance và client từ chối feature draft/estimate/confirm; chưa có AI-edit adapter/wizard | `MISSING_AI_EDIT_CONTRACT` |
| Chỉnh sửa thủ công/deterministic | Enhance API có crop/pad/blur, preset, brightness/contrast/saturation/sharpen/tone, upscale, text/logo, plain-background cleanup, PNG download/export vault | Chưa chạy artifact test trong audit này; cleanup không phải AI segmentation và upscale không thêm chi tiết mới | `IMPLEMENTED_UNVERIFIED_ARTIFACT` |

**Nguồn chính:** Bot `bot.py:61246,62225,123989`; Web
`static/portal/portal.js:668-671,24733,26048`, `static/portal/integration.js:35754,35927`,
`copyfast_api.py:2149,6916`, `copyfast_image_generation_job_bridge.py:79-87,272-274`,
`copyfast_image_operations.py:3282,3561`, `copyfast_image_studio.py:1047`.

### SubDub

| Capability | Web hiện có | Gap đã chứng minh | Trạng thái |
|---|---|---|---|
| Phụ đề gốc | Một màn, mode `SUBTITLE_ONLY`, SRT/VTT/TXT; API có bridge SubDub active | UI test xác nhận CTA vẫn guarded; chưa có browser job/artifact proof | `UI_GUARDED_SERVER_PATH_ACTIVE_UNVERIFIED` |
| Phụ đề dịch | Một màn, target language, single/bilingual, SRT/VTT; API có bridge SubDub active | Chưa chứng minh job/output thật trong browser | `UI_GUARDED_SERVER_PATH_ACTIVE_UNVERIFIED` |
| Lồng tiếng | Một màn, target language, voice placeholder, volume; API có bridge SubDub active | Voice select disabled; CTA guarded; chưa chứng minh audio/video output thật | `UI_GUARDED_SERVER_PATH_ACTIVE_UNVERIFIED` |
| Combo phụ đề + lồng tiếng | Một màn, target language, hai nhóm cấu hình, hai volume | Cấu hình volume chỉ đổi giá trị hiển thị tại chỗ; chưa chứng minh volume đi vào payload/tệp cuối | `PRESENTATION_ONLY` |
| Báo cáo | Có empty report trung thực | Chưa có request/job/result/artifact runtime proof từ browser | `NO_RUNTIME_PROOF` |

**Nguồn chính:** Web `copyfast_api.py:229,6975-7008`,
`static/portal/portal.js:24837,25270-25328,25355-25630`,
`tests/subdub-hub-presentation.test.mjs`; Bot `bot.py:233181-236189,239584-239646`;
bridge `copyfast_subdub_job_bridge.py:142-251,368-529,760-1114`.

### Video

| Capability | Web hiện có | Gap đã chứng minh | Trạng thái |
|---|---|---|---|
| Video local finishing | `/video/finishing`, `/video/frame-sequence`, `/video/poster`; FFmpeg private artifact path | Có implementation thật trong `copyfast_video_transform_operations.py`, nhưng chưa có artifact/live test trong lượt này | `IMPLEMENTED_UNVERIFIED_ARTIFACT` |
| Product/video AI | Một số `/video/create`, `/video/trend`, `/video/multiscene`, `/video/long`; nhiều planner | Runtime chỉ active có giới hạn; nhiều route là planning/guard, không phải output video | `PARTIAL` |
| Chỉnh sửa thủ công | Finishing Lab có ratio/fit/preset/sharpen/audio preservation | Chưa phải timeline editor; không claim “giống CapCut” | `BOUNDED_LOCAL_EDITOR` |
| Chỉnh sửa AI | Chưa có AI editor contract/runtime proof | Cần map từng Bot intent, preview, quote, confirm, output | `MISSING_AI_EDITOR_CONTRACT` |
| Catalog Bot | Bot public matrix có trend, AI real, script→video, reference, motion prompt, frame, self-shot, cinematic, long, idea, storyboard, prompt library, downloader, profile, editor, planning | Web không được gộp các route planner thành sản phẩm đã chạy | `NEEDS_PER_PRODUCT_CLOSEOUT` |

**Nguồn chính:** Bot `bot.py:93286-93613`; Web `static/portal/portal.js:24703,
17322-17401`, `copyfast_video_transform_operations.py:1-25,64-85,1369-1808`,
`docs/superpowers/specs/2026-10-07-video-ui-checkpoint-release.md`.

### Free tools, Notes/Memory, Documents và Publishing

| Nhóm | Kết luận đọc nguồn | Trạng thái |
|---|---|---|
| Free tools | Bot có Free Hub với input/result/library/docs/notes; Web mới cần catalog từng công cụ, không lấy tên hub làm đủ chức năng | `OPEN_DISPOSITION` |
| Notes/Memory | Bot có tạo/list/search/delete/reminder và priority; chưa thấy pin như một capability parity. `memory_plan` là quota/storage plan, không phải work plan | `PARTIAL_CRUD; PIN_NEW_REQUIREMENT` |
| Documents/OCR/dịch | Web có nhiều thao tác PDF/ảnh/OCR private thật; cần chạy artifact tests. Dịch subtitle có route/job bridge riêng; không gộp với planner | `IMPLEMENTED_PARTIAL` |
| Đăng bài tự động | `/publishing` hiện là review/prepare; test authority ghi `autopost_channels=MISSING`, không có owner-scoped social read API. Bot Telegram adapter có nhánh mô phỏng `TG-SIM` khi không có bot instance; Facebook/Instagram/YouTube/TikTok vẫn NEEDS_OAUTH/APP_REVIEW | `BLOCKED_BY_CONNECTION_AUTHORITY` |
| Projects/Assets/Support/Admin | Có bề mặt Web và một số private operations; từng action phải có authority, audit, idempotency và receipt, không tính route là parity | `NEEDS_ACTION_LEDGER` |

**Nguồn chính:** `docs/migration/NON_VIDEO_MENU_NAVIGATION_CATALOG.md`; Web
`static/portal/portal.js:1175-1180,15344-15347`; test
`tests/test_p0_webapp_v3_customer_autopost_channels_connection_authority_reconciliation.py`;
Bot `bot.py:72195-72211,123957-124013`, `services/autopost_publish.py:83-163`.

## Thứ tự thực hiện bắt buộc

Không mở PR tính năng rộng. Mỗi phiếu có một worker chạy tại một thời điểm và
phải đọc skill tương ứng trước khi làm.

1. `PARITY-00` — khóa provenance cho Bot Git HEAD, Bot dirty overlay, ma trận lịch sử và Web SHA thành các snapshot riêng; lập action ledger cho từng snapshot, không gọi snapshot nào là production canonical khi chưa có bằng chứng. Không sửa code. Owner chỉ cần chốt nguồn nếu phát hiện xung đột hành vi ảnh hưởng AC; việc đó không chặn kiểm kê ban đầu.
2. `PARITY-01` — workflow contract chung: input → preflight → quote → confirm → job → report/artifact; Admin/customer projection và idempotency.
3. `PARITY-02` — Voice route-chain (default/saved), sau đó `PARITY-03` clone/profile.
4. `PARITY-04` — Music background/song: tier, vocal, half/full/duration và adapter boundary.
5. `PARITY-05` — SubDub bốn mode một màn, volume payload, report/artifact; giữ màu xanh–teal và layout dọc.
6. `PARITY-06` — Image create, AI edit, deterministic edit artifact proof.
7. `PARITY-07A..P` — A Free Tools; B Notes/Memory; C Documents/PDF/OCR/translation; D Content/Prompt; E channel connection; F Auto-post/publish; G Projects; H Assets; I Jobs/History; J Support/Tickets; K Members; L Rewards; M Community/Referral; N customer Wallet/manual top-up; O Admin billing review; P remaining Admin ERP. Each parent family is split into action-level child specs after ledger reconciliation; Members and Rewards remain separate; Admin ERP is not automatically counted as Bot parity.
8. `PARITY-08A..C` — Video catalog; manual editor; AI editor. Chỉ bắt đầu sau nhóm không phải Video.
9. `PARITY-09` — UI/UX toàn site và motion WA-35/WA-36 đóng cuối; không dùng test từng sản phẩm thay cho whole-site gate.

Các mục trên là parent wave, không phải phiếu code gộp. Trước khi giao việc,
chẻ thành spec con theo một capability/hành động độc lập: Voice mặc định / saved
voice / clone; Music nền / bài có lời; SubDub bốn mode riêng; Image tạo AI / sửa
AI / thủ công; từng free tool và từng nhóm trong sổ action; từng capability
Video có mặt ở Bot. AI editor và manual/timeline editor là hai spec khác nhau.
Số lượng spec cho các family chưa kiểm kê chỉ chốt sau `PARITY-00`, không dựa
trên ước lượng.

## Definition of Done cho từng phiếu

- [ ] Source SHA và trạng thái đọc được ghi riêng cho Bot Git HEAD, Bot dirty overlay, ma trận lịch sử và Web; không nhập chúng thành một baseline.
- [ ] Form/route có đúng field và semantics Bot, nhưng không port callback/session/secret.
- [ ] Server authority, owner scope, CSRF, validation, audit và idempotency được kiểm bằng fixture/local adapter.
- [ ] `DRAFT`, `ESTIMATE`, `QUEUED`, `PROCESSING`, `COMPLETED`, `FAILED` phân biệt; không gọi draft/job id là output.
- [ ] Artifact thật được parse/probe: bytes, MIME/container, duration/dimensions, owner và download.
- [ ] UI có VI/EN/ZH tách biệt, chữ tương phản, form một cột, mobile 360px, empty/loading/error/focus.
- [ ] Reduced motion và performance comparator đạt; không animate layout.
- [ ] Lệnh kiểm thử, exit code, failure count và bằng chứng ảnh/JSON được lưu.
- [ ] Không có provider call, wallet mutation, production data mutation trong audit/local gate.

## Các mục không được đánh dấu xong trong lượt rà này

`music_background`, `music_song`, `voice_clone`, `image_create_runtime`,
`image_ai_edit`, `subdub_runtime_output`, `video_ai_catalog`, `video_ai_editor`,
`autopost_channels/publish`, toàn bộ parity Free tools/Notes và `WA-35/WA-36`.

## Owner completeness gate — yêu cầu ngày 2026-10-10

Không được kết luận “đã đủ như Bot” cho riêng năm sản phẩm chính khi những
nhóm khác còn chưa được lập sổ. `PARITY-00` phải tạo một dòng cho mọi action
nguồn đã đăng ký/được gọi tới, giữ cả hành động không đưa lên Web và ghi lý do.
Mỗi dòng tối thiểu có `source_id`, `bot_sha`, vị trí Bot, family/capability,
input/options/readiness, Web surface/endpoint/adapter, quyền/chủ sở hữu, report
Admin/khách, output/artifact, test và disposition. Không làm mất action do
trùng alias hoặc callback template; dynamic ID phải ghi rõ cách bao phủ. Chỉ
được gọi sổ đầy đủ khi tổng record khớp auditor và `UNKNOWN=0`.

### Các capability bắt buộc phải được đối chiếu riêng

1. **Music:** tạo nhạc nền; tạo bài hát có lời; độ dài/giọng theo đúng Bot;
   thư viện/SFX và xử lý tệp âm thanh tách riêng.
2. **Image:** tạo mới bằng AI; sửa ảnh bằng AI; chỉnh sửa thủ công hoặc
   deterministic. Mỗi nhóm có đầu vào, output và trạng thái thật riêng.
3. **Voice:** giọng mặc định/preset; profile đã lưu; giọng người dùng tự thêm
   hoặc clone; consent, readiness và quản lý profile. Profile không được gọi là
   dùng được nếu chưa tạo ra âm thanh hợp lệ.
4. **SubDub:** phụ đề nguồn, lồng tiếng, phụ đề gốc/dịch theo Bot, combo phụ đề
   + lồng tiếng trên một màn; hai mức âm lượng phải được gửi vào xử lý thật.
5. **Video — cuối thứ tự:** từng sản phẩm video của Bot; reconcile seed list
   trong plan gồm AI video, trend/research, script/image/reference-to-video,
   motion/frame, self-shot/cinematic/long/multiscene, idea/storyboard/prompt,
   intake/download/profile và editor. Editor AI và editor thủ công/timeline
   phải là hai dòng riêng. Seed list không thay inventory chuẩn Bot.
6. **Nhóm còn lại:** Free Tools từng công cụ; Notes/Memory/reminders; Documents,
   PDF/OCR/translation; Content; channel connection; Auto-post từ duyệt/lịch đến
   receipt; Projects/Workboard; Assets/Downloads; Jobs/History; Support/Ticket;
   Members; Rewards; Community/Referral; Admin/ERP và mọi family khác action
   ledger phát hiện. Mỗi family có checklist riêng; Members và Rewards không
   được gộp. Mọi hành động bên trong vẫn tách thành phiếu action độc lập.
   Chỉ ghi ghim/lưu trữ hoặc thao tác khác nếu nguồn Bot chứng minh hoặc Owner
   phê duyệt thành yêu cầu mới.

### Gate đánh giá Web surface cho mỗi action

Một action chỉ được `RUNTIME_VERIFIED` khi kiểm chứng được input → server
authority/owner → preflight và giá/cost gate nếu có → confirm idempotent → job
thật → báo cáo khách/Admin → artifact thuộc đúng owner. Các nhãn `route có`,
`form có`, `adapter có`, `HTTP 200`, `draft`, `estimate` hoặc `job id` chỉ là
bằng chứng một bước, không phải hoàn tất. UI của từng action phải qua kiểm tra
luồng dọc dễ hiểu, một hành động chính, trạng thái trống/đang xử lý/lỗi/kết
quả, VI/EN/ZH không trộn, giữ bảng màu xanh–teal, responsive/mobile, tương phản,
focus và reduced-motion. Live/provider acceptance là cổng riêng, không thuộc
110 test trình bày đã chạy.

## Verify đã chạy trong lượt rà

```text
node --test tests/music-hub-presentation.test.mjs \
  tests/voice-flow-state-presentation.test.mjs \
  tests/voice-inventory-presentation.test.mjs \
  tests/image-hub-locale-presentation.test.mjs \
  tests/image-create-locale-presentation.test.mjs \
  tests/image-workbench-truth.test.mjs \
  tests/subdub-hub-presentation.test.mjs
```

Kết quả terminal: `tests 110`, `pass 110`, `fail 0`, `cancelled 0`, `skipped 0`,
exit `0`. Đây là presentation/guard regression, **không phải LIVE_PASS**.

Lần chạy lại 2026-10-10 trên Web candidate `17b9494392cc063e8f9d0f39974da2569009b23d`
+ dirty overlay: `110/110` pass. Assertion SubDub ghi rõ volume đổi phần hiển
thị tại chỗ; vì vậy không đánh dấu volume hoặc luồng media là hoàn tất.

```ini
SPEC_ID=WEBAPP-BOT-CAPABILITY-CLOSEOUT-20261009
STATUS=READ_ONLY_RECHECK_BOT_GIT_BASELINE_NOT_LOCKED_2026-10-10_PLAN_UPDATED_IMPLEMENTATION_NOT_STARTED
WEB_HEAD=17b9494392cc063e8f9d0f39974da2569009b23d (dirty local overlay)
BOT_BASELINE_CANDIDATE=ae85e84f27f3f5e09c4e05667a34355a758c8a8a (resolved current D-source HEAD via explicit --git-dir; local main=a992dd38b20ae56333e3a5869800016eca0730c5 and origin/main ref=381d335961bea01db60cda99f0dfe98e2b2d1760 diverge; canonical/deployed source not proven)
BOT_SOURCE_FOLDER=D:\TOANAAS\bot telegram (HEAD=ae85e84f27f3f5e09c4e05667a34355a758c8a8a on fix/p0-subdub-smart-synth-adapter-signature-r1 via explicit --git-dir; git -C is Permission denied; status/diff fail because Git does not recognize a work tree; bot.py working blob 47a4123c differs from HEAD/index blob 62ef6c72)
BOT_WORKTREE_STATUS=BOT_PY_MODIFIED_CONFIRMED_REST_UNVERIFIED
BOT_GIT_HEAD=ae85e84f27f3f5e09c4e05667a34355a758c8a8a (resolved current local HEAD via explicit --git-dir; canonical/deployed Bot baseline not locked)
BOT_CURRENT_LOCAL_CANDIDATE=feature/p0-webapp-copyfast1-core-bridge@32d6d1bfbc8040b0632a44e6a9326ed568cb1a59 (clean; canonical status unconfirmed)
BOT_COMPARATOR=detached@6476f20bdd9f8728a5db0b1d62a245b0d612aea8 (clean; target baseline unavailable)
BOT_BASELINE_ARCHIVE=FAILED_CLOSED_OVER_64_MIB
FILES_CHANGED_PREVIOUS_RECHECK=3 planning/audit documents; PRODUCT_CODE_CHANGED=0
FILES_CHANGED_THIS_UPDATE=2 plan/spec documents; PRODUCT_CODE_CHANGED=0
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
WEB_UI_PRESENTATION_RECHECK=110_PASS_0_FAIL
FULL_BOT_ACTION_LEDGER=OPEN_UNKNOWN_COUNT_NOT_RECONCILED
COMMIT=NO
PUSH=NO
MERGE=NO
DEPLOY=NO
LIVE_PASS=NO
BLOCKERS=HEAD-vs-dirty-overlay inventory not yet separated; complete action ledger; workflow authority; capability adapters/artifact proofs; WA-35/WA-36 motion gate
CURRENT_BLOCKERS=canonical Bot source not locked; D source Git refuses worktree status; auditor archive exceeds 64 MiB; complete action ledger; capability runtime/artifact proofs; WA-35/WA-36 motion gate
```

## Recheck bổ sung: độ bao phủ thật của ma trận sản phẩm — 2026-10-10

Đọc trực tiếp `bot_to_web_parity_matrix.json` trên Web candidate cho thấy file
ghi Bot SHA `e0ce16e5d4ba6816d4f5205aad662eba8c635045`, tổng 39, map 39 và
`100%`; SHA-256 file là
`45EBA76C1FBE6D41E34319F472C118E8556A79A53D6D54688C615C9E0E116F90`. 39 dòng
chỉ bao gồm Video/storyboard, Image, Voice, Music, SubDub, Content, Documents,
Autopost, Jobs, Wallet và Packages. Matrix không liệt kê Free Tools,
Notes/Memory/reminders, Support/Ticket, Admin/ERP, Community/Referral, kết quả
receipt/retry của đăng bài, AI editor hay timeline editor. Bot SHA trên matrix
khác candidate `ae85e84f…` và chưa gắn được với nguồn Bot canonical/deployed.

Do đó `100%` chỉ là tỷ lệ hoàn thành ánh xạ của 39 dòng được chọn; không phải
độ bao phủ mọi capability Bot hoặc bằng chứng runtime. Riêng F21
`music_instrumental` đang trỏ tới `Music Library Browser`, không chứng minh tạo
nhạc nền; F20 trỏ tới brief sáng tác, không chứng minh bài hát có lời đã render.
Ma trận cũng không phân biệt AI edit ảnh với thao tác deterministic, chưa thể
đóng voice clone/saved-profile lifecycle, và không chứng minh bốn mode SubDub
đã chạy payload/output riêng. Các test hiện có nêu rõ music adapter/kênh mạng
xã hội còn thiếu; test SubDub xác nhận bốn mode ở lớp trình bày và volume chỉ
đổi giá trị hiển thị. Giữ toàn bộ các capability đó `OPEN/UNVERIFIED`.

**Checklist của spec:**

- [x] Xác định chính xác phạm vi và fingerprint của ma trận 39 mục.
- [x] Ghi các nhóm bị ma trận bỏ ngoài và các mục dễ bị tính nhầm (thư viện ≠ tạo nhạc, thao tác ảnh cục bộ ≠ AI edit, planner ≠ media output).
- [ ] Khóa canonical Bot SHA và Web base SHA; inventory riêng Git HEAD/dirty overlay.
- [ ] Reconcile mọi action thành ledger có nguồn, quyền, luồng, output, Admin/customer report, test và disposition; đạt `UNKNOWN=0`.
- [ ] Kiểm chứng đầu-cuối từng spec; chưa có artifact/live evidence thì không ghi `RUNTIME_PASS`.

## Recheck nguồn hiện hành — 2026-10-10

- Auditor được gọi với baseline `ae85…` và report/docs đặt ngoài repo; terminal
  trả `audit failed: Requested Bot baseline archive exceeds the static audit safety limit`.
  Không nâng giới hạn một cách mù quáng và không có inventory mới được sinh trong repo.
- `bot_to_web_parity_matrix.json` chỉ có 39 dòng capability,
  tất cả `OPTIMIZED_FLOW` nên trường tổng báo `100%`. Không lấy mẫu số nhỏ này làm
  bằng chứng tương đương toàn Bot; nó không thay thế action ledger toàn nguồn,
  vốn chưa được tái lập trên Git HEAD.
- Lượt Node chạy lại từ đúng gốc Web repo đạt `110 pass / 0 fail`; phạm vi chỉ
  renderer, locale, guard và trạng thái rỗng cho Music/Voice/Image/SubDub. Đây
  không kiểm tra provider/job/output media hoặc live.
- Trạng thái chính thức của spec vẫn là `OPEN`: chọn Bot source canonical; kiểm
  tra auditor để đọc source văn bản theo allowlist/giới hạn từng file mà không
  nới guard tổng 64 MiB; tách HEAD và dirty overlay; tạo ledger đầy đủ có
  `UNKNOWN/UNREVIEWED=0` rồi mới mở các spec code.

## Recheck tiếp theo — 2026-10-10

- Quyền đọc thư mục `D:\TOANAAS\bot telegram` được cấp trong lượt này. Một
  lần kiểm tra ban đầu đã báo nhầm rằng không có `.git`; kiểm tra tiếp theo xác
  nhận `.git/HEAD` trỏ tới `fix/p0-subdub-smart-synth-adapter-signature-r1` @
  `ae85e84f27f3f5e09c4e05667a34355a758c8a8a`. Chạy `rev-parse` từ chính thư
  mục xác nhận `is-inside-work-tree=true`; `git status` vẫn lỗi `fatal: this
  operation must be run in a work tree`; vì vậy không suy ra clean/dirty. Không đọc
  `.env`/secret, không import/chạy Bot và không sửa dữ liệu Bot. `bot.py` có SHA-256
  `7EAE9610073D3000C2A949E78E2E48E0194EB402EEDEA7F9B9328FA09D7F0B0F`, size
  14.966.481 bytes, LastWriteTime `2026-09-27 16:28:02`; không thể gán cho Git
  HEAD hoặc kết luận cây Bot sạch.
- Đối chiếu code Web hiện tại: `WEB_RUNTIME_EXECUTION_ACTIVE_FEATURES` gồm
  `subdub`, `voice_tts`, `video_ai_prompt`. SubDub có bridge tạo/replay và
  dispatch; test giao diện hiện tại vẫn khẳng định CTA `guarded`, báo cáo trống
  và hai volume chỉ cập nhật giao diện. `image_create` có API/bridge nhưng không
  nằm trong allowlist active. `music_generation` và `autopost_channels` có
  authority-stop tests xác nhận adapter/kết nối còn thiếu.
- Chạy lại đúng 7 bộ Node UI test trên candidate Web + dirty overlay trong lượt rà hiện tại:
  `tests 110`, `pass 110`, `fail 0`, `cancelled 0`, `skipped 0`, exit `0`.
  Đây chỉ là presentation/locale/guard proof, không phải media/runtime/live pass.
- Trạng thái sau recheck: `BOT_GIT_HEAD=ae85e84f27f3f5e09c4e05667a34355a758c8a8a`
  (ref metadata), `BOT_WORKTREE_STATUS=UNVERIFIED_GIT_STATUS_FAILS`,
  `BOT_CANONICAL_BASELINE=NOT_LOCKED`,
  `FULL_ACTION_LEDGER=OPEN`, `UNKNOWN_COUNT=NOT_MEASURED`.

## Recheck trong lượt hiện tại — 2026-10-10

- Chạy lại 7 bộ Node cho Music/Voice/Image/SubDub: `tests 110`, `pass 110`,
  `fail 0`, `cancelled 0`, `skipped 0`, exit `0`. Các test chỉ chứng minh
  presentation, locale, field và guard; không chứng minh media, job, artifact
  hay live execution.
- `git -C "D:\TOANAAS\bot telegram" rev-parse --show-toplevel` trả exit `128`
  (`Permission denied`). Với explicit `--git-dir/--work-tree`, Git phân giải
  root và HEAD=`ae85e84f27f3f5e09c4e05667a34355a758c8a8a`, nhưng báo
  `--is-inside-work-tree=false`; `status` và `diff` vẫn không chạy được.
- So sánh object trực tiếp: `HEAD:bot.py` và index cùng blob `62ef6c72...`, còn
  `hash-object --path=bot.py` của working file là `47a4123c...`. Vậy `bot.py`
  hiện đã sửa so với HEAD; không thể kết luận các file khác sạch/dirty. Local
  `main=a992dd38...` và tracking `origin/main=381d3359...` khác feature HEAD,
  không ancestor nhau; tracking ref chưa chứng minh trạng thái GitHub/runtime.
- Không sửa source Bot/Web, không gọi provider, không thay ví hoặc dữ liệu
  production. Giữ `CANONICAL_BOT_BASELINE=NOT_LOCKED`,
  `FULL_ACTION_LEDGER=OPEN`, `UNKNOWN_COUNT=NOT_MEASURED`.

## Xác nhận theo yêu cầu kiểm kê sản phẩm — 2026-10-10

- Đã chạy lại 7 bộ kiểm tra `Music/Voice/Image/SubDub` trên Web local; terminal
  trả `tests 110`, `pass 110`, `fail 0`, `cancelled 0`, `skipped 0`, exit `0`.
  Đây là bằng chứng renderer/locale/guard. Assertion ghi rõ SubDub CTA vẫn bị
  chặn và volume chỉ đổi giá trị hiển thị; Image chưa quảng cáo output trước
  server result; Voice không biến readiness thành audio/job. Không có provider,
  job media hay artifact thật nào được chạy.
- Lượt này được cấp quyền đọc riêng thư mục Bot; HEAD đọc được qua explicit
  Git-dir là `ae85e84f27f3f5e09c4e05667a34355a758c8a8a`, branch
  `fix/p0-subdub-smart-synth-adapter-signature-r1`. `git -C` trả
  `Permission denied`; explicit Git-dir cho phép đọc object nhưng `status` vẫn
  lỗi `fatal: this operation must be run in a work tree`. Blob `HEAD:bot.py` và
  index là `62ef6c72...`, còn working file là `47a4123c...` (SHA-256
  `7EAE9610...`). Vì vậy chỉ xác định được Bot working tree có ít nhất một sửa
  đổi; chưa xác định canonical/deployed SHA hoặc trạng thái các file còn lại.
- **Kết luận:** vẫn chưa có bằng chứng WebApp đầy đủ/tương đương Bot. Inventory
  toàn nguồn và tất cả các capability đang mở trong ma trận vẫn phải đi qua
  `SPEC-00A → SPEC-00B`; không đổi trạng thái sản phẩm sang `RUNTIME_VERIFIED`.
- Trạng thái: `BOT_CANONICAL_BASELINE=NOT_LOCKED`,
  `FULL_ACTION_LEDGER=OPEN`, `UNKNOWN_COUNT=NOT_MEASURED`,
  `PRODUCT_CODE_CHANGED=0`, `PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`,
  `PRODUCTION_DATA_MUTATIONS=0`, `COMMIT=NO`, `PUSH=NO`, `MERGE=NO`,
  `DEPLOY=NO`, `LIVE_PASS=NO`.

## Current-main correction + button-level UI/UX contract — 2026-10-10

### Những dữ kiện mới thay thế kết luận lịch sử

- Đối chiếu first-parent từ `17b9494…` tới `86d4ee6…` có 11 commit (#621–#634).
  Trong các đường trình bày được so trực tiếp, `static/portal/portal.js` là
  file bị sửa sau UI checkpoint; đồng thời API/DB, bridge Music/Image/Video/
  Document Translation và R4–R10 runtime matrices đã đổi. Mọi UI checkpoint
  trước đó chỉ là bằng chứng của SHA cũ.
- Music #621 trực tiếp thêm vào `portal.js` tier/giá nhạc nền (130/150/200
  Xu), tier/giá bài hát (200/250/300 Xu), `vocal_mode`, `lyrics`,
  `song_length_mode` và độ dài. Current source có `music_background` và
  `music_song` bridge/API. Vì vậy kết luận cũ “Web thiếu tier/adapter” đã stale;
  nhưng UI hiện tại vẫn cần test render/interaction/quote/confirm và file audio.
- Image #623 thêm canonical Image Generation bridge; không thể giữ trạng thái
  `BLOCKED_BY_RUNTIME` của snapshot cũ nếu chưa đối chiếu lại current-main guard
  và runtime matrix. Điều đó cũng chưa chứng minh file ảnh cuối đã giao thành
  công.
- Tệp người dùng gửi nói có 12 ViewTransition invalid-state errors. Lượt này
  không có trace có thể tái lập trên `86d4ee6…`; status đúng là
  `CLAIM_NOT_REPRODUCED_ON_CURRENT_MAIN`. WA-35/36 vẫn OPEN. R11 trên candidate
  cũ cũng fail acceptance, không được nâng thành PASS.

### Không được giao code cho đến khi mỗi nút có hợp đồng riêng

Spec con bắt buộc: `docs/superpowers/specs/2026-10-10-webapp-product-control-by-control-ux.md`.
Đầu ra inventory sau này: `reports/audit/WEBAPP-PRODUCT-UI-ACTION-LEDGER.md`
và `.json`; chúng chưa được tạo trong task plan này. Mỗi nút, link, control,
state-dependent action và route/action pair phải có một record, tối thiểu gồm:

```text
CURRENT_MAIN_SHA + source path/line + route + stable DOM selector
exact VI/EN/ZH label + aria name/help + user intent
visible/enabled precondition + disabled reason + role/owner
input/validation + method/endpoint/payload + quote/cost authority
idempotency/duplicate behavior + exact state transition
success feedback/next step + errors/recovery/input retention
Admin/customer report link + result/asset/download ownership
destructive confirm/undo + responsive/keyboard/touch/focus
theme/contrast/reduced-motion + runnable test command/output + evidence path
disposition; UNKNOWN/BACKEND_GAP is explicit, never guessed away
```

### Layout/state rules for all product specs

- Product hubs and ordinary forms/lists use clear vertical grouping. Each page
  has one primary action; secondary/history/tool links do not compete. Do not
  convert editor canvas/timeline into a vertical stack when that breaks the
  real editing task; only editor canvas/timeline may use horizontal space by
  functional necessity.
- Every applicable action defines default, hover, focus-visible,
  active/selected, disabled with reason, loading/deduplicate, success, validation,
  permission failure, server/network error, retry/cancel, and reduced-motion
  behavior. Unused states require `NOT_APPLICABLE` plus reason.
- Failure preserves entered data. Paid/job actions use canonical quote and
  idempotency; draft/estimate/job ID/HTTP 200 never becomes success copy by
  itself. Destructive actions need explicit impact/confirmation or supported
  undo. Navigation controls define destination and back/scroll behavior.
- Keep blue–teal brand tokens, dark-blue surfaces with light readable text,
  VI/EN/ZH purity, WCAG AA contrast and 44×44px touch targets. Do not invent
  colors or labels from memory; read the exact current token and source copy.
- Before a builder is assigned, its ticket must include exact file paths, source
  selector/lines, complete behavior contract, explicit files not to edit, one
  runnable verify command and expected output. Otherwise `NOT_READY_FOR_BUILDER`.

### Updated execution order

1. Chốt plan/checklist/spec và dừng ở ranh giới hiện tại.
2. Lượt tiếp theo khép phần UI/motion đang dở; không chen thêm product mới.
3. Refresh current main; khóa Bot canonical/dirty provenance; tạo action ledger
   và control ledger trước implementation.
4. Hoàn tất cổng tham khảo `UI-REF-00`; Landing/Welcome → Shared shell → Voice →
   Music → SubDub → Image → customer Wallet/manual top-up + Admin billing review → từng nhóm khác
   không phải Video → từng product/editor Video riêng → whole-site motion và final
   matrix.

### Checklist/spec được tách riêng để thi công không đoán

- Checklist điều phối tổng theo giai đoạn và cổng dừng:
  `reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-20261010.md`.
- Sổ điều khiển từng nút (chưa tạo cho đến khi current source/DOM được kiểm):
  `docs/superpowers/specs/2026-10-10-webapp-product-control-by-control-ux.md`.
- Đặc tả motion cuối toàn site, bao gồm WA-35/WA-36 và vòng đời chuyển trang:
  `docs/superpowers/specs/2026-10-10-motion-webapp-surfaces-final.md`.
- Đặc tả Wallet khách hàng và Admin billing:
  `docs/superpowers/specs/2026-10-10-webapp-wallet-admin-ui-closeout.md`.

Đây là tài liệu điều phối và đặc tả, không phải xác nhận mọi capability đã có
hoặc hoạt động. Các action thực tế chỉ được tách thành phiếu nhỏ sau khi Bot
source canonical và ledger đã khóa; mọi `UNKNOWN` ngoài phạm vi được giữ công
khai, không tự lấp bằng suy đoán.

Trạng thái: `CURRENT_MAIN=86d4ee6…` (baseline đã đọc, cần refresh sau); `MUSIC=
REVALIDATE_AFTER_621`; `IMAGE=REVALIDATE_AFTER_623`; `UI_CONTROL_LEDGER=NOT_CREATED`;
`BOT_CANONICAL=NOT_LOCKED`; `UNKNOWN=NOT_ZERO_OR_NOT_MEASURED`;
`WA35/WA36=OPEN`; `IMPLEMENTATION_STARTED=NO` trong lượt cập nhật plan này.
