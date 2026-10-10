# Rà soát chức năng Bot → Web App: kết luận, plan và checklist

**SPEC_ID:** `WEBAPP-BOT-FUNCTION-PARITY-REBASELINE-20261009`
**STATUS:** `PLAN_REBASED_TO_MAIN_86d4ee6_BUTTON_LEVEL_WALLET_ADMIN_REFERENCE_GATES_ADDED_2026-10-10_PAUSE_AFTER_PLAN`
**Phạm vi lượt này:** kiểm chứng mốc source và hoàn thiện plan/checklist/spec; không sửa engine, route, Bot, giao diện sản phẩm, dữ liệu hay cấu hình. Sau khi chốt tài liệu, dừng tại đây; việc kế tiếp là khép phần UI/motion đang dở, rồi mới mở các spec theo thứ tự dưới đây.

> Goal UI/UX và motion vẫn được giữ riêng. Yêu cầu lượt này mở rộng sang rà soát đối chiếu tính năng; chỉ cập nhật tài liệu plan/spec, không triển khai engine/route hay tuyên bố runtime đã đạt.

## 1. Kết luận thẳng

**Chưa thể nói Web App đã có đầy đủ chức năng hoặc luồng làm việc tương đương Bot.** Có nhiều bề mặt và biểu mẫu Web đã được làm đẹp/kiểm thử riêng, nhưng không đồng nghĩa tác vụ thật đã chạy, có đầu ra hợp lệ, được lưu và được Admin quản lý.

“Đã đóng/khóa” ở các hồ sơ Music, Voice, SubDub, Image và Video hiện là trạng thái của một lát cắt giao diện cụ thể. Các hồ sơ đó nhiều chỗ ghi rõ không tạo media, không gửi provider, không tạo job và không chứng minh đầu ra. Không lấy số route, số callback, chữ “PASS” của renderer hay `HTTP 200` làm bằng chứng tính năng hoàn tất.

## 2. Mốc nguồn và bằng chứng rà soát

| Nguồn | Mốc/đặc điểm | Ý nghĩa và giới hạn |
|---|---|---|
| Web snapshot của lần audit trước | Branch `fix/shared-shell-locale-controls-20261008`, HEAD `17b9494392cc063e8f9d0f39974da2569009b23d`; worktree khi đó dirty | Chỉ là baseline lịch sử của các test cũ, không còn là current-main baseline. |
| Web current-main rebaseline | `origin/main` tại `86d4ee6e11ddfbc0d4e1dbf63b41d9b3ed7d859b`, đọc ngày 2026-10-10; docs branch đang ở `45b84de83ee9b475bb4366c3ddc2af85b82297c4`, merge-base `17b9494392cc063e8f9d0f39974da2569009b23d` | Current source baseline để sửa plan; không xác nhận production/deployed/live. Phải làm mới SHA ngay trước khi bắt đầu code sau khi phần UI/motion dang dở được khép. |
| Bot source folder đang đọc trực tiếp | `D:\TOANAAS\bot telegram`; `bot.py` SHA-256 `7EAE9610073D3000C2A949E78E2E48E0194EB402EEDEA7F9B9328FA09D7F0B0F`, 14.966.481 bytes, LastWriteTime `2026-09-27 16:28:02`; `.git/HEAD` trỏ tới `fix/p0-subdub-smart-synth-adapter-signature-r1` @ `ae85e84f27f3f5e09c4e05667a34355a758c8a8a` | Chạy từ chính thư mục, `git rev-parse` xác nhận top-level và `is-inside-work-tree=true`; `git status` vẫn lỗi `fatal: this operation must be run in a work tree`. Lệnh có cờ `--git-dir/--work-tree` cho kết quả `false` không nhất quán nên không dùng làm trạng thái. HEAD/ref đã biết, nhưng sạch/dirty, quan hệ giữa `bot.py` với Git HEAD và tính canonical chưa xác minh. |
| Web static fingerprint tại lúc rà | `e6bbba95c74851362009f53a9cd60c4f61994762cfda6afd8d6f306cde5ca247`; 248 tệp nguồn | Được tính trước khi thêm mục checklist trong lượt này; không phải fingerprint sau cập nhật. |
| Bot snapshot trong lần audit trước | Branch `fix/p0-subdub-smart-synth-adapter-signature-r1`; HEAD `ae85e84f27f3f5e09c4e05667a34355a758c8a8a`; 7 tracked files modified và 24 untracked entries | Giữ là bằng chứng lịch sử của lần audit trước, không coi là Git status hiện tại. Recheck lượt này tìm thấy các checkout Bot khác; xem mục recheck cuối tài liệu. |
| Bot static fingerprint tại lần rà 2026-10-09 | `dd08a974ebd2c8375dee4483591e3b769beb45180315638c50711134b6931a23`; 650 tệp nguồn được quét | Fingerprint của nguồn đọc được tại lần rà, chưa chứng minh là fingerprint riêng của Git HEAD. Giữ như bằng chứng lịch sử; cần quét riêng Git HEAD và dirty overlay để tái lập. Không import hoặc khởi chạy Bot. |
| Bộ quét | `scripts/migration/audit_bot_to_web.py`, gọi các hàm inventory tĩnh `_summarize_inventory` và `_build_parity_gap` trong bộ nhớ | Chỉ đọc văn bản/AST và đối chiếu ánh xạ; không ghi báo cáo sinh tự động, không gọi mạng/provider, DB, Telegram hay ví. |

### Kết quả đếm ở lần quét tĩnh này

- Nguồn Bot: 1.068 command, 5.596 callback data, 1.026 callback template, 85 đăng ký handler Telegram, 173 route, 668 tham chiếu job/worker; 57 record từ module không được đường import quan sát hiện tại tham chiếu. Đây là **record nguồn**, không phải số tính năng độc lập.
- Nguồn Web local: 809 route declaration, 180 tham chiếu background job, 243 bảng dữ liệu được nhắc đến, 13 provider reference, 52 đường dẫn UI. Đây là dấu vết tĩnh; không chứng minh API được gọi, có quyền, job chạy hay artifact được giao.
- Đối chiếu tạo 7.775 record nguồn; 7.633 product-action mapping sau khi tách đăng ký handler Telegram khỏi hành động sản phẩm.
- Trạng thái mapping: 2.866 `COPIED_GUARDED`; 1.368 `NAVIGATION_ONLY`; 1.117 `TELEGRAM_ONLY`; 1.923 `NEEDS_FEATURE_DISPOSITION`; 353 `NEEDS_WEB_IMPLEMENTATION`; 5 `WEB_NATIVE_READ_ONLY`; chỉ 1 `MAPPED_TO_EXISTING_ROUTE` trong schema phân loại hiện tại.
- Tỷ lệ bề mặt Web tĩnh 37,56%; tỷ lệ đã có disposition 70,18%; kiểm chứng tương đương workflow runtime 0% (`NOT_STATICALLY_VERIFIABLE`). **Các tỷ lệ này mô tả bộ phân loại tĩnh trên cây nguồn đang có; không phải điểm chất lượng sản phẩm, không phải đo LIVE, cũng không so sánh tiến độ trực tiếp với baseline cũ.**
- Các backlog đáng chú ý trong record cần phân loại: `vproduct` 653, `vprofile` 223, `vid3` 182, `adconcept` 136, `imgtool` 117, `autopost` 91, `vstory` 63, `storypack` 45, `tvflow` 34, `ticket` 30, `freehub` 30 và `docflow` 22. Con số là callback/template/command record theo family, **không phải** số chức năng bị thiếu.
- Hồ sơ cũ `FEATURE_PARITY_MATRIX.md` dùng mẫu số 4.053, bề mặt 38,69%, disposition 83,91%, runtime equivalence 0% và tự ghi `NOT_COMPARABLE_TO_PREVIOUS_AUDIT_PERCENTAGES`. Nó dựa trên mốc Bot khác; không trộn các con số cũ/mới để tuyên bố tiến bộ hoặc tụt lùi.
- Số liệu inventory trên là ảnh chụp tĩnh của nguồn đọc được ngày 2026-10-09. Git recheck ngày 2026-10-10 xác nhận Bot có thay đổi chưa commit; không gán ngược các con số này riêng cho HEAD `ae85e84…` cho đến khi chạy lại trên Git object của HEAD. Các line reference Bot trong bảng sản phẩm cũng là vị trí của working tree tại lần rà, cần tái xác nhận sau khi khóa nguồn.

### Đối chiếu theo yêu cầu sản phẩm

| Nhóm | Điều đã có bằng chứng | Kết luận chức năng so với Bot | Việc cần chốt trong plan |
|---|---|---|---|
| Music | Checkpoint #618 được theo sau bởi #621 (`a5e3685`): `static/portal/portal.js` thêm tier/giá, `vocal_mode`, `lyrics` và lựa chọn độ dài bài hát; `copyfast_music_job_bridge.py` cùng API job routes cho `music_background`/`music_song` có trong current main. | **Kết luận cũ “thiếu tier/adapter” đã stale.** Tuy nhiên chưa có regression render/interaction trên current main và chưa có bằng chứng runtime/live/file âm thanh cuối. Giá đang hiện ở option UI phải khớp estimate canonical, không được xem UI là nguồn giá. | Rà lại đủ hai form và mọi nút trên `86d4ee6…`; đối chiếu field/payload/quote/confirm/result với bridge hiện tại; kiểm file âm thanh thật chỉ ở gate được duyệt. Thư viện/SFX/tệp âm thanh vẫn là các luồng riêng. |
| Image | `/image` và `/image/create` có hub/form/copy; đã gỡ một số demo/fake-ready/fake-output và cải thiện locale/trình bày. Checklist ghi rõ không suy ra toàn bộ nhóm Image đã hoàn thiện. | **Chưa chứng minh** tạo ảnh AI thực, chỉnh sửa ảnh AI, hoặc chỉnh sửa thủ công đều chạy tới file ảnh đầu ra. | Lập riêng luồng tạo, sửa AI và thao tác thủ công; xác thực ảnh đầu vào thuộc người dùng, preview và artifact đầu ra. |
| Voice | Có UI TTS, giọng đã lưu, clone và trạng thái. Hồ sơ Voice nói rõ không có claim audio/job/delivery thật. | **Chưa chứng minh** giọng mặc định trả âm thanh thật, giọng do người dùng thêm/clone dùng lại được, hay đầu ra kiểm tra được. | Tách mặc định, saved voice và clone; ghi nhận đồng ý/nguồn mẫu, capability thật, ID giọng phía provider và kiểm tra bytes/MIME/duration của âm thanh. |
| SubDub | Một màn hình có bốn chế độ và hai thanh âm lượng; API có route/bridge và `subdub` nằm trong allowlist runtime. | **Chưa chứng minh end-to-end:** test UI hiện tại xác nhận CTA đang `guarded`, vùng kết quả rỗng, và volume chỉ đổi giá trị hiển thị. Cờ runtime/route không chứng minh browser đã xử lý và giao đúng file. | Giữ một màn; nối bốn mode tới đúng payload/job; đưa hai mức âm lượng vào payload và kiểm tra trên file cuối; chứng minh request/job/report/artifact khớp ở khách và Admin. |
| Video | Có checkpoint UI cho hub, Video nhanh và Video nhiều cảnh; checklist vẫn để mở self-shot/trend/storyboard/Video dài/công cụ biên tập và motion. | **Chưa đủ toàn bộ sản phẩm Video.** Không có bằng chứng ở đây cho chỉnh sửa AI, chỉnh sửa thủ công như timeline/editor, xuất bản hoặc file kết quả end-to-end. | Làm Video sau các nhóm khác; catalog từng sản phẩm rồi tách AI editor và manual editor thành spec riêng. |
| Free tools | Hồ sơ trình bày ghi nhận 4 tiện ích xác định đã được kiểm tra trong một gate UI. | **Chưa chứng minh đủ toàn bộ Free Hub của Bot**; lần quét còn 30 record `freehub` cần gán đích/ý nghĩa. | Liệt kê từng tiện ích, đầu vào/đầu ra, miễn phí hay có giới hạn, lưu hay không lưu, và Web-native route. |
| Đăng bài tự động | Web có bề mặt Publishing; Bot có nhóm `autopost` và các thực thể hàng đợi/receipt trong inventory nguồn. | **Chưa chứng minh** kết nối kênh, lịch, approval, queue, publish thật, receipt, retry/idempotency hoặc Admin theo dõi kết quả. | Tách soạn nháp, duyệt, lịch, gửi, kết quả/receipt và lỗi; không báo “đã đăng” chỉ vì tạo draft/job. |
| Ghi chú/Memory | Inventory nguồn Bot có `memory_notes`, `memory_plans`, `memory_reminders`, `memory_events`; mapping cũ có lối vào `/notes`. Nguồn đã đọc xác nhận tạo/list/search/delete/reminder và priority; `memory_plan` là quota/storage plan. | **Có dấu vết, chưa có chứng cứ parity CRUD và chạy thật.** Route vào Notes không chứng minh tạo/lưu/nhắc việc an toàn; chưa có bằng chứng pin/archive như capability Bot. | Đối chiếu chính xác create/list/search/delete/reminder/priority. Chỉ thêm edit/update nếu Bot source xác nhận; pin/archive phải ghi `OWNER_NEW_REQUIREMENT` nếu không có trong Bot. Kiểm owner và phản hồi lỗi. |
| Các nhóm còn lại | Bộ quét thấy các family content/chat prompt, document/OCR/translation, support/ticket, asset/vault, package/membership, admin/ERP và các bề mặt khác. | **Chưa thể gọi đầy đủ:** 1.923 record chưa có disposition và 353 record chưa có route; status tĩnh không xác nhận server auth, bridge hay output. | Đóng sổ từng family bằng Web-native / canonical bridge / read-only / admin-only / Telegram-only có lý do, rồi kiểm tra hành động đầu-cuối. |

## 2A. Khóa phạm vi “không sót” theo yêu cầu Owner ngày 2026-10-10

Danh sách dưới đây bắt buộc phải có dòng đối chiếu trong action ledger. Nó
không tự xác nhận Web đã có chức năng, và không cho phép thêm lựa chọn không có
trong nguồn Bot. Mục không thấy bằng chứng Bot phải ghi
`NOT_FOUND_IN_PINNED_BOT_SOURCE` hoặc `OWNER_NEW_REQUIREMENT`, không tự coi là đã
có.

- **Music:** hai sản phẩm tách bạch: tạo nhạc nền và tạo bài hát có lời; đối
  chiếu đúng kiểu đầu vào, lựa chọn giọng/độ dài và giới hạn Bot thực sự có.
  Thư viện, âm thanh hiệu ứng và công cụ tệp âm thanh là nhóm riêng, không tính
  thành bộ tạo nhạc.
- **Image:** tạo ảnh AI mới; sửa ảnh AI từ ảnh do chính tài khoản sở hữu; chỉnh
  sửa thủ công/deterministic như crop, resize, màu, chữ/logo hoặc thao tác khác
  chỉ khi inventory Bot xác nhận. Không gọi xóa nền deterministic là AI edit.
- **Voice:** giọng mặc định/preset; dùng lại giọng đã lưu; thêm/nhân bản giọng
  của người dùng; đồng ý và quyền sử dụng mẫu; nghe thử, chọn mặc định, sửa tên
  hoặc xóa profile chỉ khi Bot có hành động tương ứng. Tách trạng thái “có
  profile” khỏi “dùng được để tạo âm thanh”.
- **SubDub:** trên một màn có bốn lựa chọn theo Bot: phụ đề nguồn, chỉ lồng
  tiếng, phụ đề (gốc/dịch theo khả năng Bot), và phụ đề kèm lồng tiếng; âm
  thanh gốc/giọng đọc phải có tác dụng trong payload và tệp cuối, không chỉ đổi
  số hiển thị.
- **Video (làm sau nhóm không phải Video):** đối chiếu từng entry Bot, không
  gộp thành một thẻ “Video”. Danh sách seed cần reconcile gồm video AI,
  xu hướng/nghiên cứu, kịch bản→video, ảnh→video, video tham chiếu,
  prompt/chuyển động, frame, tự quay, cinematic, video dài/nhiều cảnh/nhân
  vật, ý tưởng, storyboard, thư viện prompt, tải/tiếp nhận video, profile và
  công cụ biên tập. Chỉnh sửa AI và chỉnh sửa thủ công/timeline là hai
  capability riêng. Chỉ giữ capability được Bot source chuẩn xác nhận.
- **Tất cả nhóm còn lại:** từng công cụ miễn phí; Notes/Memory/reminder; tài
  liệu/PDF/OCR/dịch; soạn nội dung; kết nối kênh, duyệt, lịch, đăng bài, receipt
  và retry; projects, assets, jobs/history, support/ticket, membership/reward,
  community/referral và hành động admin/ERP. Đây là seed list, không thay mẫu số
  action ledger.

**Cổng không bỏ sót (bắt buộc trước khi mở spec triển khai):** ledger phải bao
phủ command, callback literal/template, conversation/handler có đường gọi từ
entrypoint, Web action và hành động Admin có liên quan. Mỗi dòng có source SHA +
vị trí nguồn, capability/family, input/options, điều kiện/quyền, cost gate nếu
có, output, Admin/customer report, Web route/API/adapter, kiểm thử/bằng chứng
và disposition có lý do. Alias được nối vào capability canonical nhưng không
được làm rơi record nguồn. `UNKNOWN/UNREVIEWED=0` mới được đóng inventory; các
action Bot-only, Admin-only, read-only hoặc không tương đương phải có lý do cụ
thể và người duyệt. Số route hay test trình bày không thay thế cổng này.

### Kết luận UX/motion cho phạm vi goal đang chạy

Các hồ sơ có ma trận UI tốt cho một số màn và checkpoint; điều đó đáng giữ. Tuy vậy toàn bộ ứng dụng **chưa thể đánh dấu hoàn thiện UI/UX và motion**: shared-shell/locale/nút nổi và whole-site motion còn mở; `WA-35/WA-36` chưa có đủ bằng chứng đóng. Tài liệu được gửi kèm nêu “12 ViewTransition invalid-state errors”, nhưng lượt này chưa tái hiện/đo lỗi đó trên `origin/main=86d4ee6…`, nên phải ghi `CLAIM_NOT_REPRODUCED_ON_CURRENT_MAIN`, không ghi đó là lỗi đã xác minh. R11 gần nhất là candidate cũ `17b9494… + dirty overlay`, `PARTIAL_MEASUREMENT_NOT_PASS`: 16/16 phép đo, `CLS=0`, `pageErrors=0`, nhưng thiếu `animationend` 8/8 normal rows, 4/16 long task >200 ms (max 311 ms), 10/16 frame gap >200 ms (max 450 ms); WA-35/36 vẫn OPEN. Lượt này không chụp lại UI/live và không đưa ra điểm thẩm mỹ mới.

## 3. Ranh giới an toàn và cách làm

- Bot là nguồn đối chiếu cho capability và thứ tự nghiệp vụ; mẫu sản phẩm bên ngoài chỉ là nguồn tham khảo cách trình bày. **Không sửa Bot, không port Telegram callback/session/pending-state sang trình duyệt, không lấy mẫu thị trường làm nguồn nghiệp vụ.** Callback/command vận hành, broadcast, emergency, freeze, provider key và thao tác owner có thể phải giữ Telegram-only/admin-only.
- Không tạo cầu ghi Web↔Bot tùy tiện. Mỗi chức năng cần ghi rõ nguồn dữ liệu, chủ sở hữu, quyền, request/job/provider ID, trạng thái, audit và đường giao artifact.
- Confirm phải idempotent; refresh/status là chỉ đọc; chỉ tạo `JOB_ID` sau khi qua preflight/admission; fail-closed khi thiếu adapter/quyền/nguồn/giá; không fake accepted, pending, success, phí hay Xu.
- Không có provider call tính phí, sửa ENV/secret, thay ví/PayOS, ghi dữ liệu production, migration phá hủy, deploy hoặc merge trong plan này. Kiểm tra giao diện có thể dùng fixture/local adapter; kiểm thử output thật cần cổng duyệt provider riêng.
- Từng phiếu builder phải đọc đúng skill đầy đủ trước khi làm. Theo chỉ đạo mới nhất: giao `Gemini 3.8 Flash` trước, nếu không đạt AC thì chuyển `Gemini 3.1 Pro`; nếu Pro vẫn không đạt thì Codex/root trực tiếp xử lý, không thêm Sol làm tầng trung gian. `WORKER_LOCK=1`; một spec chỉ có một worker RUNNING.

## 4. Plan theo thứ tự — mỗi spec có cổng riêng

Các `SPEC-02..08` dưới đây là nhóm/wave, **không giao một phiếu lớn cho nhiều
chức năng**. Sau `SPEC-00`, mỗi capability nguồn thành một spec con, một phiếu,
một người chạy, một AC và một bộ bằng chứng. Nhánh/tên spec chính xác cho những
capability ngoài danh sách Owner nêu sẽ sinh từ ledger; không đoán số lượng
trước khi khóa Bot source.

### SPEC-00 — Khóa nguồn đối chiếu và dựng sổ hành động Bot → Web (P0, trước mọi code)

- **Mục tiêu:** kiểm kê được mọi action Bot mà không giả định checkout nào là production canonical. Mốc đã biết gồm Git HEAD ứng viên `ae85e84…`, working tree `D:\TOANAAS\bot telegram` có `bot.py` khác blob HEAD, các checkout khác trong `work/`, ma trận 39 mục trỏ SHA `e0ce16e…`, và Web HEAD/dirty overlay. Chúng là các nguồn đối chiếu riêng, chưa được nhập làm một.
- **Làm ngay, không chờ khóa production SHA:** tạo provenance riêng cho (A) Git HEAD Bot, (B) dirty/untracked overlay Bot đọc được, (C) ma trận 39 mục như nguồn lịch sử độc lập, và (D) Web HEAD + overlay. Với mỗi nguồn, ghi SHA/fingerprint, thời điểm, trạng thái truy cập và giới hạn. Nếu Git không đọc được worktree status, kiểm kê Git object bằng allowlist tệp nguồn và giới hạn kích thước từng blob/tổng; kiểm overlay bằng hash độc lập. Không nới giới hạn 64 MiB mù quáng; không đọc `.env`/secret, không tạo archive không giới hạn, không reset/stash/xóa hoặc sửa Bot.
- **Đầu ra:** ledger machine-readable + bảng đọc được, bao phủ mọi command/callback literal/template, conversation/handler có đường gọi và action Admin. Mỗi dòng có source snapshot, vị trí, family/capability, input/options/readiness/cost, disposition, Web target, authority/owner, report khách/Admin, output/test/evidence. Alias/dynamic callback được nối về action canonical nhưng không làm mất record gốc. Dòng chưa phân loại phải nằm trong `UNKNOWN`, không giấu trong dashboard.
- **Nghiệm thu:** số dòng reconcile được với từng inventory nguồn; `UNKNOWN/UNREVIEWED=0` cho mỗi snapshot đã đọc. Hành động Telegram-only/admin-only/read-only có lý do và reviewer. Khác biệt hành vi giữa HEAD và overlay ghi thành `BOT_SOURCE_CONFLICT`; chỉ cần Owner chọn nguồn chuẩn khi conflict đó ảnh hưởng AC/code, không chặn việc dựng inventory ban đầu.
- **Verify:** chạy auditor tĩnh trên Git HEAD và overlay riêng, lặp fingerprint/count; không chạy Bot, provider, DB hay production action. Cho đến khi hoàn tất, kết luận giới hạn theo snapshot; không tuyên bố “đủ như Bot” hoặc “production parity”.

### SPEC-01 — Hợp đồng workflow chung và báo cáo Admin/khách (P0)

- **Mục tiêu:** mọi tác vụ được quảng bá có cùng ngôn ngữ trạng thái và được Admin theo dõi theo quyền.
- **Hợp đồng:** một trang/luồng nêu rõ input → lựa chọn → báo giá (nếu áp dụng) → xác nhận → xử lý → kết quả/lỗi; `REQUEST_ID` trước preflight, `JOB_ID` sau Admission Pass, `PROVIDER_TASK_ID` riêng; chống trùng xác nhận; status/refresh chỉ đọc. Web được gom nhiều tác vụ thành một thao tác khi hợp lý, nhưng mỗi mục con vẫn có định danh, quyền, cost gate, trạng thái, lỗi, artifact và báo cáo riêng; batch phải thể hiện `partial_success` khi chỉ một phần thành công, không được biến thành một job/charge giả.
- **Báo cáo:** sản phẩm/chế độ, actor/owner, thời điểm, request/job, bước, trạng thái thật, lỗi khôi phục được, artifact hợp lệ và quyền truy cập; che provider ID/secret khỏi khách. Admin nhìn thấy/ xử lý đúng quyền; không dùng giao diện để cấp quyền thay server.
- **Nghiệm thu:** không tác vụ nào báo hoàn thành chỉ vì HTTP 200, metadata, queue/job id hoặc nút sáng; báo cáo nguồn khách nối được đến đúng record Admin. Batch không mất trạng thái từng mục, không nhân đôi khi retry và cho phép thấy rõ thành công/thất bại một phần.
- **Verify:** contract tests cho confirm idempotency, quyền, status read-only, empty/error/timeout, artifact ownership, audit receipt, duplicate batch và partial failure bằng adapter giả/local.

### SPEC-02 — Voice: giọng mặc định, giọng lưu và giọng tự thêm (P1)

- **Mục tiêu:** TTS mặc định và voice clone là hai capability khác nhau; giọng tự thêm chỉ dùng được khi có consent, profile/ID hợp lệ và readiness thật.
- **Nghiệm thu:** giọng mặc định tạo được âm thanh hợp lệ; saved voice chỉ chọn profile sẵn sàng; clone lưu ID provider đúng, không giả lập profile đã sẵn sàng; trạng thái từ chối/lỗi không làm mất mẫu/consent.
- **Verify:** adapter fixture xác nhận đúng tuyến và policy; khi được duyệt live, artifact bytes > 0, MIME/codec/duration hợp lệ và tải đúng user; không lộ ID nội bộ.
- **Phạm vi UI của chat này:** chỉ kiểm form dọc, nhãn/tình trạng, ngôn ngữ và trạng thái; không thay engine/field/action đã khóa.

### SPEC-03 — Music: nhạc nền và nhạc có lời (P2)

- **Mục tiêu:** hai lựa chọn sản phẩm rõ ràng, không nhầm thư viện/SFX với sáng tác AI.
- **Nhạc nền:** Bot options và duration phải được đọc từ SHA chuẩn; các tuỳ chọn không tạo thành form quá tải. Kết quả là file âm thanh thật hoặc lỗi cụ thể.
- **Bài hát có lời:** có lời/ý tưởng và độ dài đúng hợp đồng Bot (nửa bài/toàn bài); không hiện lựa chọn theo số giây nếu Bot không có; không giả job khi thiếu adapter.
- **Nghiệm thu:** route/form/quote/confirm/result đúng mode; đầu ra kiểm tra được; thư viện và công cụ tệp âm thanh được phân nhóm riêng.
- **Verify:** test riêng từng mode, thiếu adapter, bấm lặp, output rỗng và trạng thái provider; UI không báo thành công từ draft.

### SPEC-04 — SubDub: một giao diện, bốn chế độ thực thi (P3)

- **Mục tiêu:** phụ đề gốc; lồng tiếng; phụ đề dịch; phụ đề + lồng tiếng trên cùng màn; hiện đúng trường theo lựa chọn.
- **Nghiệm thu:** file nguồn có ownership; âm lượng gốc/giọng đọc được gửi và áp dụng thật; ASR → SRT/VTT → dịch tuỳ chọn → TTS → mux tuỳ năng lực; lỗi mux trả đúng những artifact có thật, không dựng MP4 giả.
- **Báo cáo:** trạng thái theo bước, tệp đầu ra, thời lượng/định dạng, lỗi và hướng xử lý; Admin thấy cùng request có actor/permission chính xác.
- **Verify:** fixture kiểm thứ tự, bốn mode, idempotency, ownership và file thật trong môi trường được duyệt; không gọi provider tính phí khi chưa duyệt.

### SPEC-05 — Image: tạo ảnh AI, sửa ảnh AI và chỉnh sửa thủ công (P4)

- **Mục tiêu:** tách “tạo ảnh mới” và “chỉnh sửa ảnh có sẵn”; ghi rõ tác vụ AI và thao tác thủ công khác nhau ở đâu.
- **Nghiệm thu:** nguồn ảnh của đúng owner, tuỳ chọn/prompt có nhãn dễ hiểu, preview không giả, output là image bytes hợp lệ với MIME/kích thước; lỗi/guard không hiện giá, job hoặc kết quả giả.
- **Verify:** test tạo và sửa riêng, ảnh đầu vào thiếu/sai quyền, output rỗng, retry và tải asset đúng chủ sở hữu.

### SPEC-06 — Các nhóm không phải Video (P5, mỗi nhóm là phiếu nhỏ riêng)

- **06A Free Tools:** lập danh sách đủ từng công cụ; phân loại deterministic miễn phí, quota hoặc provider; có đầu vào/đầu ra thật, nêu rõ lưu hay không lưu. 4 tiện ích UI đã thấy không thay cho catalog đầy đủ.
- **06B Notes/Memory:** bắt đầu bằng action Bot đã xác nhận: tạo/list/search/delete/reminder/priority; kiểm tra edit/update và danh mục trước khi ghi vào scope. Không tính `memory_plan` là work plan. Ghim/lưu trữ chỉ là `OWNER_NEW_REQUIREMENT` nếu không tìm thấy trong Bot. Kiểm owner, thời gian và empty/error state.
- **06C Documents/OCR/Translation:** PDF/OCR/nén/chuyển đổi/ASR/dịch; phân biệt preview/draft với file đã xuất; owner-scoped asset và format thực.
- **06D Content/Prompt:** tách soạn, lưu, sao chép, áp dụng và xuất; bản nháp không phải đầu ra đã giao.
- **06E Channel connection** và **06F Auto-post:** tách kết nối/ủy quyền khỏi soạn, duyệt, lên lịch, gửi, receipt và retry/idempotency; không báo đã đăng khi chưa có receipt.
- **06G Projects**, **06H Assets/Downloads**, **06I Jobs/History**, **06J Support/Tickets**, **06K Members**, **06L Rewards**, **06M Community/Referral:** mỗi nhóm có action catalog và quyền/record riêng; Members ≠ Rewards; project/task ≠ product job.
- **06N Wallet/manual top-up khách hàng:** spec giao diện dọc cho chọn phương thức → nhập số tiền → xác nhận → mới hiện hướng dẫn thanh toán/mã/QR theo contract; tạo yêu cầu pending không đồng nghĩa đã cộng Xu.
- **06O Admin billing review:** hàng chờ nạp thủ công, đối chiếu tài khoản/số tiền/phương thức/nội dung chuyển khoản/chứng từ; chỉ hiện duyệt/từ chối theo quyền và server contract, có lý do/audit/idempotency. Đây là luồng Admin riêng, không gộp vào parity UI của khách.
- **06P Admin ERP còn lại:** lập catalog cho từng hành động quản trị theo role/record/audit; không suy rằng mọi thao tác Admin có đối tác trong Bot và không sửa RBAC/payment logic trong lane UI.
- **Nghiệm thu chung:** mỗi hành động có một kết quả kiểm chứng được hoặc được loại rõ `Telegram-only/admin-only/read-only` với lý do; không bỏ sót family trong ledger SPEC-00.

### SPEC-07 — Toàn bộ Video và biên tập (P6, làm sau các nhóm khác)

- **Mục tiêu:** đối chiếu từng loại Bot Video trước khi làm; không gộp mọi sản phẩm vào một form.
- **Phải có disposition riêng:** Video đơn; ảnh→Video/chữ→Video/nhân vật hoặc avatar nếu Bot có; nhiều cảnh; Video dài/chunk; trend; storyboard/script-to-screen; self-shot; hoàn thiện/render/export; chỉnh sửa AI; chỉnh sửa thủ công/timeline.
- **Chỉnh sửa AI và thủ công là hai spec riêng:** mode AI phải có task/preview/result thật; mode thủ công phải kiểm input timeline/trim/crop/scene/audio/caption và quy trình lưu/xuất. Không khẳng định “giống CapCut” nếu chưa có timeline và file xuất được kiểm chứng.
- **Nghiệm thu:** từng scene đầu ra hợp lệ; file cuối có bytes/container/duration/dimensions hợp lệ; poll/status không gửi lại task; package, quote, confirm, charge và delivery theo authority đã phê duyệt.

### SPEC-08 — Rà soát UI/UX, ngôn ngữ, responsive và motion (chạy theo lát cắt; đóng cổng toàn site sau cùng)

- Giữ nguyên màu xanh–teal/blue hiện có; không đổi giao diện tối sang nền đen. Form và danh sách theo cột dọc; một primary action rõ; thông tin nâng cao mở có chủ đích.
- Tiếng Việt tự nhiên, không xen văn xuôi tiếng Anh; bản tiếng Anh thuần Anh, locale khác không rơi về tiếng Việt. Giữ danh từ riêng/tên sản phẩm khi cần.
- Đo chữ thường ≥4.5:1, chữ lớn/ranh giới UI ≥3:1, hit target ≥44px; kiểm 360/375/768/1440px, bàn phím/focus, trạng thái trống/đang chạy/thành công/lỗi.
- Motion dùng transform/opacity, phản hồi thao tác rõ, không animate layout, có `prefers-reduced-motion`; không chốt smooth nếu còn lỗi console, transition hoặc tải nhảy.
- **WA-35/WA-36 giữ OPEN:** xử lý lỗi ViewTransition; truy nguyên frame 277–392 ms; sửa link evidence thiếu; có comparator/Tester receipt gắn SHA. Các checkpoint sản phẩm không đóng thay cho cổng motion toàn site.
- Đặc tả motion cuối riêng: `docs/superpowers/specs/2026-10-10-motion-webapp-surfaces-final.md` (`MOTION-WEBAPP-SURFACES-FINAL-20261010`). Tài liệu này tách vòng đời animation khỏi lỗi khựng/frame gap và định nghĩa ma trận rapid navigation, Back/Forward, auth, hydration/remount, route failure, normal/reduced motion.
- **Nghiệm thu cuối:** browser matrix trên source SHA cố định; lưu ảnh/JSON/console/network và kết quả đo; kiểm Web/App shell sau khi từng nhóm giao diện hoàn tất.

### 4A. Các spec con bắt buộc (tách nhỏ, chạy đúng thứ tự)

| Thứ tự | Spec con | Phạm vi riêng; không gộp | Cổng đóng của chính spec |
|---|---|---|---|
| 1 | `SPEC-00A` | Khóa Bot Git HEAD/Web SHA và tính fingerprint riêng cho HEAD, Bot dirty overlay, Web dirty overlay | Ba mốc có thể tái lập; không dùng dirty code làm baseline |
| 2 | `SPEC-00B` | Ledger đủ command/callback/template/conversation/handler/action và disposition | Tổng record khớp auditor; `UNKNOWN=0`; Telegram-only/admin-only có lý do |
| 3 | `SPEC-01` | Hợp đồng workflow + báo cáo Admin/khách | Contract quyền, owner, idempotency, job/result/report được test local |
| 4–6 | `SPEC-02A/B/C` | Voice mặc định; dùng/quản lý saved voice; giọng tự thêm/clone+consent — mỗi dòng là phiếu riêng | Không lấy profile/readiness làm audio; mỗi lane có AC và artifact riêng |
| 7–8 | `SPEC-03A/B` | Tạo nhạc nền; bài hát có lời — hai form/luồng/AC riêng | Không gộp SFX/library; file âm thanh hợp lệ hoặc lỗi thật |
| 9–12 | `SPEC-04A/B/C/D` | Phụ đề nguồn; lồng tiếng; phụ đề gốc/dịch theo Bot; combo — cùng một shell nhưng mỗi mode một spec con | Đúng payload, âm lượng có hiệu lực, đúng artifact và báo cáo cho mode đang chọn |
| 13–15 | `SPEC-05A/B/C` | Tạo ảnh AI; sửa ảnh AI; chỉnh thủ công/deterministic — tách ba lane | File ảnh thật, quyền owner, MIME/dimension và preview hợp lệ |
| Trước thiết kế màn | `UI-REF-00` | Tối đa 2 tham chiếu sản phẩm chính thức cho mỗi nhóm giao diện; ghi URL/ngày truy cập, mẫu bố cục/tương tác áp dụng và lý do | Tham chiếu chỉ định hướng trình bày; Bot/current server contract mới quyết định nghiệp vụ; giữ brand xanh–teal, không sao chép tài sản/nhận diện. |
| 16+ | `SPEC-06A..P` | A Free Tools; B Notes/Memory; C Documents/OCR/Translation; D Content; E channel connection; F Auto-post; G Projects; H Assets; I Jobs/History; J Support; K Members; L Rewards; M Community; N Wallet/manual top-up khách; O Admin billing review; P Admin ERP còn lại | Mỗi control/action có phiếu riêng; Members ≠ Rewards; Wallet/Admin approval là luồng nhạy cảm riêng; Admin ERP không gộp với luồng khách. |
| Sau hết nhóm trên | `SPEC-07A..N` | Mỗi capability Video được Bot source xác nhận có một spec riêng; editor thủ công/timeline và editor AI luôn tách | Spec con Video được sinh từ ledger chính xác; không bỏ sản phẩm vì tên route khác |
| Cuối cùng | `SPEC-08` + `MOTION-WEBAPP-SURFACES-FINAL-20261010` | UI/UX và motion toàn site trên source SHA cố định | Whole-site browser matrix và WA-35/WA-36 evidence; không thay bằng pass của từng màn |

**Quy tắc giao việc:** mỗi spec con được giao riêng theo builder order Owner đã
chốt: Gemini 3.8 Flash trước → không đạt cùng AC mới đến Gemini 3.1 Pro → Pro
không đạt thì Codex/root xử lý trực tiếp; không thêm tầng trung gian. Builder
đọc đủ skill hiện hành ngay trước phiếu; Codex review độc lập; `WORKER_LOCK=1`.
Chat UI/UX/motion không tự sửa route/engine; chỉ nhận contract/source SHA đã
khóa để hoàn thiện bề mặt và kiểm bằng chứng UI.

## 5. Checklist tổng: không đánh dấu hoàn tất sớm

- [x] Đọc hồ sơ checklist/spec gần nhất cho Image, Video, Voice, Music và SubDub; phân biệt rõ bằng chứng UI với đầu ra engine.
- [x] Chạy đối chiếu inventory tĩnh Bot ↔ Web trên nội dung nguồn đọc được; lưu lại fingerprint/count và kết luận 0% runtime equivalence tĩnh.
- [x] Ghi nhận mẫu số audit cũ và mới khác nhau; không cộng/trừ phần trăm để nhận tiến độ.
- [x] 2026-10-10: ghi nhận snapshot lịch sử của một checkout Bot từng có 7 tracked modified và 24 untracked entries; không coi đó là trạng thái hiện tại của `D:\TOANAAS\bot telegram`.
- [x] 2026-10-10: đọc được `.git/HEAD` tại `D:\TOANAAS\bot telegram`, thấy ref `fix/p0-subdub-smart-synth-adapter-signature-r1`; SHA ứng viên từng được ghi ở lượt trước, nhưng chưa khóa nguồn chuẩn.
- [x] 2026-10-10: dùng explicit `--git-dir/--work-tree` phân giải current HEAD=`ae85e84f27f3f5e09c4e05667a34355a758c8a8a`; local `main`=`a992dd38b20ae56333e3a5869800016eca0730c5`, local tracking `origin/main`=`381d335961bea01db60cda99f0dfe98e2b2d1760`; refs không ancestor nhau nên canonical chưa xác định.
- [x] 2026-10-10: `bot.py` working blob `47a4123c...` khác HEAD/index blob `62ef6c72...`; file này chắc chắn modified, còn status toàn worktree chưa đọc được.
- [x] 2026-10-10: chạy lại 7 bộ Node cho Music/Voice/Image/SubDub; terminal `110 pass, 0 fail`, chỉ là bằng chứng presentation/locale/guard.
- [ ] Khóa Git HEAD làm inventory chuẩn có thể tái lập; quét dirty overlay riêng; chạy lại inventory cho cả hai lớp.
- [ ] Xuất ledger đầy đủ cho mọi Bot action; phân loại từng dòng và không để `unknown/unreviewed`.
- [ ] Chốt contract chung workflow, report Admin/khách, quyền và đường artifact trước khi làm các chức năng phụ thuộc.
- [ ] Voice: giọng mặc định, saved voice, giọng tự thêm/clone; test file tiếng nói thật sau cổng duyệt.
- [ ] Music: nhạc nền; bài hát có lời nửa/toàn bài; tách thư viện/SFX; test file âm thanh thật sau cổng duyệt.
- [ ] SubDub: bốn mode một giao diện; volume áp dụng thật; job/report và artifact phụ đề/âm thanh/Video.
- [ ] Image: tạo ảnh AI; sửa ảnh AI; thao tác thủ công; xác minh artifact và quyền sở hữu.
- [ ] Đối chiếu đủ Free Tools, Notes/Memory, Documents/OCR/Translation, Content, Autopost/Publishing, Projects/Assets/Support, Membership/Admin và mọi family còn lại.
- [ ] Tách từng capability thành một spec con (Voice 3, Music 2, SubDub 4, Image 3; các nhóm còn lại/video sinh spec con theo ledger), không giao gộp nhiều hành động độc lập.
- [ ] Sau khi phần không phải Video đóng, xử lý catalog Video đầy đủ; tách AI editor và manual editor.
- [ ] Duy trì WA-35/36 trong checklist live; không đóng bằng bằng chứng của một sản phẩm riêng.
- [ ] Chạy local contract/browser test từng spec; chỉ chạy live/provider test khi được duyệt riêng và có fixture/tài khoản/cost gate phù hợp.
- [ ] Chỉ đóng spec khi có source SHA, lệnh + output test, ảnh/JSON hoặc artifact, trạng thái PR/merge/deploy/live tách biệt và reviewer độc lập khi cần.

## 6. Thứ tự và cổng giao việc

1. SPEC-00 source baseline/ledger → SPEC-01 workflow/Admin contract.
2. Sau khi khóa nguồn/ledger, chốt tham chiếu giao diện `UI-REF-00`, rồi Landing/Shared Shell → Voice → Music → SubDub → Image → Wallet/manual top-up + Admin billing review → từng nhóm không phải Video còn lại (06A–06P).
3. Video (SPEC-07) cuối theo thứ tự Owner đã chốt.
4. WA-35/WA-36 được theo dõi liên tục trong goal UI/UX & motion hiện hành; toàn-site acceptance đóng sau khi các bề mặt cuối ổn định.

Mỗi spec chỉ có một `RUNNING`. Builder đọc skill cần thiết đầy đủ ngay trước mỗi phiếu: core Owner skills, skill domain UI/UX, và skill engine tương ứng trong workstream engine. Với yêu cầu hiện tại, chat này chỉ giữ audit/UI/UX/motion; không tự gửi việc hoặc sửa engine ở workstream khác.

## 7. Trạng thái cuối lượt rà

```ini
SPEC_ID=WEBAPP-BOT-FUNCTION-PARITY-REBASELINE-20261009
STATUS=READ_ONLY_RECHECK_BOT_GIT_BASELINE_NOT_LOCKED_2026-10-10_PLAN_UPDATED_IMPLEMENTATION_NOT_STARTED
BOT_BASELINE_CANDIDATE=ae85e84f27f3f5e09c4e05667a34355a758c8a8a (resolved current D-source HEAD via explicit --git-dir; local main=a992dd38b20ae56333e3a5869800016eca0730c5 and origin/main ref=381d335961bea01db60cda99f0dfe98e2b2d1760 diverge; canonical/deployed source not proven)
BOT_CURRENT_LOCAL_CHECKOUT=feature/p0-webapp-copyfast1-core-bridge@32d6d1bfbc8040b0632a44e6a9326ed568cb1a59 (clean; not confirmed canonical Bot main/deployed source)
BOT_COMPARATOR_CHECKOUT=detached@6476f20bdd9f8728a5db0b1d62a245b0d612aea8 (clean; does not contain candidate ae85 object)
BOT_SOURCE_FOLDER=D:\TOANAAS\bot telegram (HEAD=ae85e84f27f3f5e09c4e05667a34355a758c8a8a on fix/p0-subdub-smart-synth-adapter-signature-r1 via explicit --git-dir; git -C is Permission denied; status/diff fail because Git does not recognize a work tree; bot.py working blob 47a4123c differs from HEAD/index blob 62ef6c72)
BOT_WORKTREE_STATUS=BOT_PY_MODIFIED_CONFIRMED_REST_UNVERIFIED
BOT_GIT_HEAD=ae85e84f27f3f5e09c4e05667a34355a758c8a8a (resolved current local HEAD; canonical/deployed Bot baseline not locked)
BOT_CANONICAL_BASELINE=NOT_LOCKED
BOT_STATIC_AUDIT=FAILED_CLOSED_ARCHIVE_OVER_64_MIB (no inventory output generated in repo)
BOT_SOURCE_FINGERPRINT_RECORDED_2026-10-09=dd08a974ebd2c8375dee4483591e3b769beb45180315638c50711134b6931a23 (historical scope not independently bound to Git HEAD)
WEB_HEAD=17b9494392cc063e8f9d0f39974da2569009b23d
WEB_WORKTREE=DIRTY
WEB_SOURCE_FINGERPRINT=STALE_AFTER_CURRENT_DOC_UPDATES; RECOMPUTE_BEFORE_ANY_PR
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
AUDIT_DOCS_PREVIOUS_RECHECK=3 (plan, capability spec, master checklist updated)
AUDIT_DOCS_THIS_UPDATE=2 (plan and capability spec authored in the parity recheck; publishing these documents is a separate docs-only action)
PRODUCT_CODE_CHANGED=0
ENGINE_OR_ROUTE_FILES_CHANGED=0
PRODUCT_CODE_COMMIT=NO
PRODUCT_CODE_PUSH=NO
PRODUCT_CODE_MERGE=NO
PRODUCT_CODE_DEPLOY=NO
LIVE_PASS=NO
NEXT=LOCK_CANONICAL_BOT_SOURCE;MAKE_STATIC_AUDIT_HANDLE_SOURCE_LIMITS_SAFELY;FREEZE_ACTION_LEDGER_UNKNOWN_0
```

### Recheck chính xác ma trận 39 mục và câu trả lời theo yêu cầu Owner — 2026-10-10

Đã đọc trực tiếp `bot_to_web_parity_matrix.json` trên Web candidate
`17b9494392cc063e8f9d0f39974da2569009b23d`:

- File tự khai `bot_reference_sha=e0ce16e5d4ba6816d4f5205aad662eba8c635045`,
  `total_bot_customer_functions=39`, `mapped_web_functions=39`,
  `parity_percentage=100%`; SHA-256 của file là
  `45EBA76C1FBE6D41E34319F472C118E8556A79A53D6D54688C615C9E0E116F90`.
- 39 dòng chỉ gồm các nhóm: Video 8 + storyboard 1, Image 6, Voice 4, Music 3,
  SubDub 4, Content 4, Documents 3, Autopost 2, Jobs 1, Wallet 2, Packages 1.
  Vì vậy con số 100% là tỷ lệ của **39 dòng trong ma trận rút gọn**, không phải
  tỷ lệ hoàn thành toàn bộ Bot. `bot_reference_sha` này cũng khác Bot HEAD ứng
  viên `ae85e84f…`; chưa xác minh ma trận đang khớp Bot canonical/deployed nào.
- Không có dòng riêng cho Free Tools, Notes/Memory/reminders, Support/Ticket,
  Admin/ERP, Community/Referral, receipt/retry của đăng bài, editor AI và
  timeline editor. Cũng không tách nhạc nền được tạo mới khỏi thư viện nhạc,
  AI edit ảnh khỏi thao tác lọc/deterministic, hoặc bốn mode SubDub thành các
  workflow có payload/output riêng.

| Yêu cầu Owner | Bằng chứng Web hiện đọc được | Kết luận hiện tại |
|---|---|---|
| Tạo nhạc nền + bài hát có lời | Ma trận F20/F21 trỏ lần lượt tới `Music Composer Brief` và `Music Library Browser`; runtime allowlist không có `music_generation`, authority test ghi adapter còn thiếu. | Chưa có bằng chứng hai luồng tạo nhạc chạy tới tệp thật; thư viện nhạc nền không thay cho bộ tạo nhạc nền. |
| Ảnh AI + sửa ảnh AI + sửa thủ công | Có form tạo và một số thao tác deterministic; allowlist không có `image_create`; tài liệu hiện phân biệt riêng AI edit còn thiếu với crop/resize/adjustment cục bộ. | Chưa đủ: AI create chưa được xác minh runtime, AI edit chưa có hợp đồng/adapter được chứng minh, thủ công mới ở mức implementation chưa xác minh artifact. |
| Voice mặc định + voice tự thêm | `voice_tts` nằm trong allowlist; profile/saved voice và clone có mặt ở bề mặt UI nhưng khác nhau về wiring/readiness. | Chưa chứng minh audio TTS đầu-cuối; clone bị chặn/chưa có adapter; CRUD profile còn thiếu action so với nguồn Bot. |
| SubDub bốn mode trên một màn | Kiểm tra trình bày có `SUBTITLE_ONLY`, `TRANSLATED_SUBTITLE`, `DUBBING_ONLY`, `SUBTITLE_PLUS_DUBBING`; test ghi CTA `guarded`, kết quả rỗng và volume chỉ đổi số hiển thị. | Đúng hướng về bố cục lựa chọn, chưa chứng minh payload, âm lượng, job, báo cáo và artifact thật. |
| Đủ sản phẩm Video, AI editor + manual editor | Có planner và một số local finishing operation; bằng chứng hiện có nói rõ chưa có AI editor được xác minh và local finishing chưa phải timeline editor. | Chưa đủ; lập catalog từng capability từ Bot, tách AI editor khỏi timeline editor; Video vẫn làm cuối. |
| Free tools, đăng bài tự động, Notes và các nhóm còn lại | Một số Web-native surface tồn tại; test authority của Autopost xác nhận chưa có kết nối kênh. Notes/reminder Web-owned không chứng minh Bot Memory parity hoặc gửi nhắc thật. Nhiều nhóm không có trong ma trận 39 mục. | Chưa thể gọi là đầy đủ; phải reconcile từng action, authority, trạng thái, đầu ra, quyền Admin và lý do loại trừ. |

Nguồn kiểm tra tĩnh bổ sung: `copyfast_api.py:229` chỉ khai allowlist
`subdub`, `video_ai_prompt`, `voice_tts`; test SubDub
`tests/subdub-hub-presentation.test.mjs:100-171`, test Music
`tests/test_p0_webapp_v3_customer_music_generation_job_bridge.py`, và test
Autopost `tests/test_p0_webapp_v3_customer_autopost_channels_connection_authority_reconciliation.py`.
Các contract test là bằng chứng về giới hạn/guard, không phải bằng chứng live.

Checklist cập nhật cho lần rà này:

- [x] Đọc hash, mẫu số và toàn bộ 39 dòng của ma trận hiện hành; thống kê nhóm và ghi nhận Bot SHA tham chiếu chưa khóa.
- [x] Đối chiếu các yêu cầu cụ thể Music/Image/Voice/SubDub/Video với allowlist và contract/presentation tests liên quan.
- [x] Ghi rõ các family không có trong ma trận 39 mục; không dùng nhãn `100%` để đóng parity tổng.
- [ ] Khóa Bot canonical/deployed SHA, tách HEAD và dirty overlay; dựng action ledger đủ command/callback/template/handler/action với `UNKNOWN=0`.
- [ ] Tạo phiếu nhỏ sau khi ledger khóa: Voice → Music → SubDub → Image → từng nhóm không phải Video → Video cuối; mỗi phiếu có AC và artifact evidence riêng.
- [ ] Chỉ đóng capability sau khi có server authority/owner, request/job/report Admin-khách, idempotency, output hợp lệ và test; provider/live cần duyệt riêng.

`RUNTIME_PARITY=NOT_VERIFIED`; `BOT_CANONICAL_BASELINE=NOT_LOCKED`;
`FULL_ACTION_LEDGER=OPEN`; `UNKNOWN_COUNT=NOT_MEASURED`. Đây là kết quả rà soát
và replan, không phải tuyên bố hoàn tất hoặc yêu cầu bắt đầu code.

### Recheck bổ sung ngày 2026-10-10

- Chạy lại bộ contract UI cho Music/Voice/Image/SubDub trên ứng dụng Web local:
  `node --test tests/music-hub-presentation.test.mjs tests/voice-flow-state-presentation.test.mjs tests/voice-inventory-presentation.test.mjs tests/image-hub-locale-presentation.test.mjs tests/image-create-locale-presentation.test.mjs tests/image-workbench-truth.test.mjs tests/subdub-hub-presentation.test.mjs`.
  Đã chạy lại trong lượt rà hiện tại; terminal: `tests 110`, `pass 110`, `fail 0`, `cancelled 0`, `skipped 0`, exit `0`.
- Đây chỉ là kiểm tra renderer, locale, field/guard và trạng thái báo cáo rỗng.
  Riêng SubDub xác nhận điều khiển âm lượng chỉ cập nhật giá trị hiển thị; Voice
  và Image xác nhận không giả đầu ra. Kết quả này **không chứng minh** adapter,
  provider, job hay tệp media thật.
- Ghi chú lịch sử từ lần rà trước: khi đó không tái lập được Git status Bot bằng
  `git -C` (`Permission denied` khi vào worktree). Recheck hiện hành bên dưới đã
  đọc được hai checkout khác, nhưng chưa xác định được checkout canonical và
  chưa khóa inventory; `PARITY-00` vẫn mở.

### Recheck nguồn và completeness gate — 2026-10-10 (trạng thái hiện hành)

- Đọc chỉ-đọc được hai checkout cục bộ khác nhau; chúng không xác định được
  source Bot canonical hiện tại:
  - `toanaas-bot-copyfast1-bridge`: branch
    `feature/p0-webapp-copyfast1-core-bridge`, HEAD
    `32d6d1bfbc8040b0632a44e6a9326ed568cb1a59`, clean. Commit ứng viên
    `ae85e84f27f3f5e09c4e05667a34355a758c8a8a` tồn tại trong object database,
    nhưng không phải HEAD và không phải ancestor của HEAD này.
  - `p0-bot-comparator-6476`: detached HEAD
    `6476f20bdd9f8728a5db0b1d62a245b0d612aea8`, clean; không có object `ae85`.
  - Vì vậy snapshot dirty 7 tracked/24 untracked và fingerprint Bot ghi ở lần
    audit trước vẫn chỉ là **bằng chứng lịch sử**, chưa tái lập trong checkout
    hiện có và chưa đủ để chọn source canonical.
- Đã thử dùng auditor `scripts/migration/audit_bot_to_web.py` với Git baseline
  `ae85…`, Web HEAD `17b9494…`, report/docs đặt trong thư mục tạm ngoài repo.
  Auditor từ chối an toàn với output terminal:
  `audit failed: Requested Bot baseline archive exceeds the static audit safety limit`.
  Không có báo cáo mới được ghi vào repo; không sửa Bot, Web code hoặc dữ liệu.
- Cách khép blocker: không tăng giới hạn 64 MiB mù quáng. Tách việc rà auditor
  thành spec nhỏ: dùng `git ls-tree` để chốt tập tệp nguồn văn bản canonical;
  loại trừ dữ liệu, file đính kèm, `.env` và tài liệu không phải nguồn chạy; đọc
  từng blob theo giới hạn kích thước từng file + tổng; giữ kiểm tra path traversal,
  secret redaction và fail-closed. Chạy riêng trên Bot HEAD đã được Owner chốt
  và dirty overlay, rồi đối chiếu lại tổng với auditor trước khi đóng `PARITY-00`.
- `bot_to_web_parity_matrix.json` hiện có 39 dòng capability, đều gắn
  `OPTIMIZED_FLOW` và báo `100%`. Đây là ma trận rút gọn theo sản phẩm, **không**
  phải action ledger đầy đủ; không dùng con số này để trả lời “đã đủ mọi chức năng
  Bot chưa”. Sổ tổng thể cũ 7.633 mapping cũng chưa được tái lập trên Git HEAD.
- Chạy lại đúng gốc repo bằng Node bundled trên 7 bộ Music/Voice/Image/SubDub:
  `tests 110`, `pass 110`, `fail 0`, `cancelled 0`, `skipped 0`, exit `0`.
  Chúng xác nhận presentation/locale/guard và trạng thái rỗng; SubDub xác nhận
  volume chỉ đổi giá trị hiển thị. Không có provider, job, artifact hoặc live
  result được kiểm thử.
- Cập nhật trạng thái: `CANONICAL_BOT_BASELINE=NOT_LOCKED`,
  `FULL_ACTION_LEDGER=OPEN`, `UNKNOWN_COUNT=NOT_MEASURED`,
  `RUNTIME_PARITY=NOT_VERIFIED`. Không được đánh dấu hoàn thành rà soát “không sót”
  cho đến khi SPEC-00 đạt `UNKNOWN/UNREVIEWED=0` và từng nhóm có disposition.

### Recheck trong lượt hiện tại — 2026-10-10

- Chạy lại 7 bộ Node cho Music/Voice/Image/SubDub: `tests 110`, `pass 110`,
  `fail 0`, `cancelled 0`, `skipped 0`, exit `0`. Đây là presentation/locale/guard;
  không xác nhận provider, job, artifact media hoặc live result.
- `git -C "D:\TOANAAS\bot telegram" rev-parse --show-toplevel` trả exit `128`
  (`Permission denied`). Dùng explicit `--git-dir/--work-tree` phân giải được
  root và HEAD=`ae85e84f27f3f5e09c4e05667a34355a758c8a8a`, nhưng
  `--is-inside-work-tree=false`, `status`/`diff` đều fail. `git ls-tree` xác nhận
  HEAD và index có cùng `bot.py` blob `62ef6c72...`; `hash-object --path=bot.py`
  trên working file ra `47a4123c...`, chứng minh riêng `bot.py` đã sửa. Không suy
  ra tình trạng các file khác.
- Local `main`=`a992dd38...`, local `origin/main`=`381d3359...`; cả hai khác
  feature HEAD và không ancestor nhau. `origin/main` chỉ là tracking ref cục bộ;
  chưa xác minh GitHub hiện hành hay commit đang chạy trên Bot production.
- Giữ `PARITY-00=OPEN`: Git HEAD local đã phân giải nhưng source canonical/deployed
  và trạng thái toàn worktree chưa khóa. Không sửa Bot/Web engine, không gọi
  provider, không sửa ví hoặc dữ liệu production.

### Xác nhận theo yêu cầu kiểm kê sản phẩm — 2026-10-10

- Chạy lại trực tiếp 7 bộ kiểm tra trình bày Music/Voice/Image/SubDub trên Web
  hiện tại: `tests 110`, `pass 110`, `fail 0`, `cancelled 0`, `skipped 0`, exit
  `0`. Đây chỉ là bằng chứng giao diện/locale/guard; một số assertion xác nhận
  execution vẫn bị chặn hoặc kết quả còn rỗng, không chứng minh chức năng sản
  phẩm tạo được media.
- Quyền đọc riêng `D:\TOANAAS\bot telegram` được cấp trong lượt này. Đọc được
  `.git/HEAD` và xác định ref `fix/p0-subdub-smart-synth-adapter-signature-r1`;
  Git object xác nhận HEAD `ae85e84f27f3f5e09c4e05667a34355a758c8a8a`. Tuy nhiên,
  `git -C` vẫn trả `Permission denied`; gọi bằng `--git-dir/--work-tree` đọc được
  HEAD nhưng `status` dừng với `fatal: this operation must be run in a work tree`.
  `HEAD:bot.py`/index blob `62ef6c72...` khác working blob `47a4123c...` và SHA-256
  working file `7EAE9610...`; Bot đang có ít nhất một thay đổi chưa gán vào
  baseline. Không thể kết luận status của các file khác hoặc Bot canonical/deployed.
- **Không xác nhận đủ như Bot.** Giữ `SPEC-00A/00B` mở; không đóng inventory,
  không mở spec code phụ thuộc, không chạy Bot/provider và không sửa Bot.
- Trạng thái sau kiểm tra: `CANONICAL_BOT_BASELINE=NOT_LOCKED`,
  `FULL_ACTION_LEDGER=OPEN`, `UNKNOWN/UNREVIEWED=NOT_ZERO_OR_NOT_MEASURED`,
  `RUNTIME_PARITY=NOT_VERIFIED`, `PRODUCT_CODE_CHANGED=0`,
  `PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`, `PRODUCTION_DATA_MUTATIONS=0`.

### Read-only recheck cho yêu cầu kiểm kê hiện tại — 2026-10-10

- Đọc-only checkout gốc `C:\Users\toann\Documents\Codex\toan-aas-standalone`:
  branch `main`, clean, HEAD `ea914bb45966237106d8a8e8c1464604ffaba42b`.
- Cây đang dùng cho công việc UI ở `work\toanaas-video-ui-release-20261007`:
  HEAD `17b9494392cc063e8f9d0f39974da2569009b23d`, dirty; không coi phần
  chưa commit là `main`, production hoặc bằng chứng LIVE.
- Đọc và phân tích JSON ma trận của checkout gốc: có 39 ID riêng, cả 39 đều
  gắn nhãn `OPTIMIZED_FLOW`. Đây chỉ xác nhận ma trận ánh xạ 39 dòng; nó không
  chứa tiêu chí nghiệm thu theo từng hành động, kết quả job hay kiểm tra artifact,
  vì vậy không thay được action ledger đầy đủ hoặc bằng chứng chạy.
- Lệnh `git -C "D:\TOANAAS\bot telegram" ...` trong lượt này trả
  `Permission denied`. Không đọc được trạng thái Git đầy đủ của thư mục Bot;
  giữ nguyên `BOT_CANONICAL_BASELINE=NOT_LOCKED` theo giới hạn bằng chứng đã ghi.
- Lượt này chỉ xác minh trạng thái checkout/ma trận và đọc kế hoạch; không chạy
  lại bộ test, không sửa mã sản phẩm/Bot, không gọi provider, không ghi dữ liệu,
  không commit/push/merge/deploy.
- Trạng thái checklist không đổi: `SPEC-00A/00B=OPEN`,
  `FULL_ACTION_LEDGER=OPEN`, `UNKNOWN/UNREVIEWED=NOT_ZERO_OR_NOT_MEASURED`,
  `RUNTIME_PARITY=NOT_VERIFIED`.

### Xác nhận phạm vi theo yêu cầu Owner — 2026-10-10

Phạm vi dưới đây đã được đối chiếu lại với yêu cầu mới nhất. Dấu `[x]` chỉ
nghĩa là yêu cầu đã được ghi vào plan/spec; **không** có nghĩa tính năng đã
được triển khai hoặc nghiệm thu.

- [x] Music tách **tạo nhạc nền** và **tạo bài hát có lời**; thư viện, SFX và
  xử lý tệp âm thanh không được tính thay cho hai luồng tạo nhạc.
- [x] Image tách **tạo ảnh AI**, **sửa ảnh bằng AI** và **chỉnh sửa
  thủ công/deterministic**; không gắn nhãn thao tác thủ công là AI.
- [x] Voice đối chiếu **giọng mặc định/preset**, **giọng đã lưu/chọn mặc định**
  và **giọng người dùng tự thêm/clone**, gồm consent và khả năng thực sự tạo
  audio.
- [x] SubDub giữ một giao diện với bốn lựa chọn: **phụ đề nguồn**, **chỉ lồng
  tiếng**, **phụ đề gốc/dịch theo khả năng Bot**, **phụ đề + lồng tiếng**; âm
  lượng gốc/giọng đọc phải có bằng chứng trong payload và tệp cuối.
- [x] Video được xếp sau các nhóm còn lại; đối chiếu từng sản phẩm Bot và tách
  **biên tập AI** khỏi **biên tập thủ công/timeline**.
- [x] Nhóm còn lại không bị bỏ khỏi sổ: từng Free Tool; Notes/Memory/reminder;
  Documents/PDF/OCR/translation; Content; kết nối kênh, duyệt, lịch, đăng,
  receipt/retry; Projects, Assets, Jobs/History, Support/Ticket, Members,
  Rewards, Community/Referral, Admin/ERP và family phát hiện mới; Members và
  Rewards được theo dõi như hai capability riêng.
- [ ] Khóa được Bot source canonical + Web base SHA; status hiện vẫn
  `BOT_CANONICAL_BASELINE=NOT_LOCKED`.
- [ ] Tạo action ledger đầy đủ từ nguồn chuẩn, reconcile mọi command/callback/
  template/handler/action, đạt `UNKNOWN/UNREVIEWED=0`.
- [ ] Trước khi giao builder, tách từng capability thành phiếu nhỏ có file nguồn
  cụ thể, phạm vi được phép/cấm, context phải đọc, một lệnh kiểm tra chạy được
  kèm kết quả mong đợi; builder đọc đúng skill trước mỗi phiếu.
- [ ] Xác minh runtime, quyền sở hữu, báo cáo khách/Admin và artifact thật cho
  từng action; hiện không có sản phẩm nào được đóng nhờ đợt kiểm tra này.
- [ ] Đóng UI/UX và motion trên toàn site, bao gồm WA-35/WA-36; kiểm tra sản
  phẩm riêng không thay thế cổng toàn site.

#### Kiểm tra trình bày tái chạy trong lượt này

Lệnh chạy tại Web worktree `17b9494392cc063e8f9d0f39974da2569009b23d` cộng
dirty overlay đang có:

```text
node --test tests/music-hub-presentation.test.mjs tests/voice-flow-state-presentation.test.mjs tests/voice-inventory-presentation.test.mjs tests/image-hub-locale-presentation.test.mjs tests/image-create-locale-presentation.test.mjs tests/image-workbench-truth.test.mjs tests/subdub-hub-presentation.test.mjs
ℹ tests 110
ℹ pass 110
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
exit 0
```

Phạm vi của bộ test là renderer/locale/guard, không chạy provider hay job media.
Nó cũng xác nhận SubDub vẫn không có bằng chứng output và hai thanh âm lượng
chỉ cập nhật giá trị hiển thị; Voice readiness không đồng nghĩa đã có audio;
Image không đưa ra output trước server result. Music route/presentation được
kiểm tra, nhưng không chứng minh tạo được nhạc. Do đó giữ
`RUNTIME_PARITY=NOT_VERIFIED`, `PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`,
`PRODUCTION_DATA_MUTATIONS=0`, `PRODUCT_CODE_CHANGED=0`, `COMMIT=NO`, `PUSH=NO`,
`MERGE=NO`, `DEPLOY=NO`, `LIVE_PASS=NO`.

### WA-35 measurement addendum — 2026-10-10

R11 completed collection of the 16-row hydrated local matrix for the four
customer routes at desktop/mobile sizes with normal/reduced motion. It is a
measurement result, not a passing acceptance run: `CLS=0` and page errors are
`0`, while 4/16 rows have a long task over 200 ms (maximum 311 ms), 10/16 have
a frame gap over 200 ms (maximum 450 ms), and the harness records no
`animationend` event in any of the 8 normal-motion rows. The runner exits `1`
at its 680 ms duration assertion, so WA-35 stays OPEN and no full motion or
smooth-load claim is made. The summary and exact per-row measurements are in
`evidence/motion-wa35-measured-20261010-r11.md`; remaining work is to repair the
measurement gate, attribute the frame delays, and rerun the same matrix plus
protected comparators.

## 9. Rebaseline current main và bổ sung cổng đặc tả từng nút — 2026-10-10

### 9.1 Kết quả kiểm tra thiếu sót thật

Lần đọc này đối chiếu tệp người dùng gửi với Git source; nội dung tệp được coi
là đầu vào cần kiểm chứng, không tự động coi mọi nhận định là lỗi đã xác minh.

| Nhận định trong đầu vào | Kết quả kiểm chứng | Cách xử lý trong plan |
|---|---|---|
| Plan đang bind snapshot cũ | **Đúng.** Docs branch `45b84de…` có merge-base `17b9494…`; `origin/main` đã là `86d4ee6…`. Có 11 commit first-parent sau base, từ #621 tới #634. | Từ nay dùng current-main SHA làm baseline mới; làm mới SHA trước mỗi wave sau khi phần đang dở khép lại. |
| Music UI #618 vẫn đại diện UI hiện tại | **Sai nếu dùng như bằng chứng cuối.** PR #621 (`a5e3685`) trực tiếp thay `static/portal/portal.js`: thêm tier/giá, `vocal_mode`, `lyrics` và độ dài bài hát; đồng thời thêm `copyfast_music_job_bridge.py` và API contract. | Thay kết luận cũ “thiếu tier/adapter” bằng `CURRENT_MAIN_REVALIDATION_REQUIRED`; kiểm UI handler/quote/confirm với bridge hiện hành. |
| Engine/runtime merges sau checkpoint không thể đổi contract UI | **Thiếu sót thật.** Từ merge-base đến main, current source đổi API/DB và Music/Image/Video/document bridges cùng runtime matrices; route, trạng thái khả dụng, quote và kết quả cần được so lại dù CSS không đổi. | Mỗi product phải có bảng source-touch → trường/nút chịu ảnh hưởng → test lại. UI lane chỉ trình bày contract, không tự sửa engine. |
| Có 12 lỗi ViewTransition uncaught trên main | **Chưa xác minh trên current main.** Tệp gửi nêu con số nhưng không kèm run SHA/trace có thể tái lập trên `86d4ee6…`; không được ghi là defect current-main đã xác nhận. | Ghi `CLAIM_NOT_REPRODUCED_ON_CURRENT_MAIN`; WA-35/36 vẫn OPEN. R11 chỉ là candidate cũ và runner fail như mục trước. |
| Plan đã chỉ rõ UI từng nút để builder không đoán | **Chưa đạt ở mức kiểm kê thực tế.** Existing plan chia capability và acceptance cấp nhóm, nhưng chưa bắt buộc DOM selector, mỗi nhãn/locale, điều kiện bật/tắt, request/payload, state, lỗi/khôi phục, quyền, focus/mobile và một lệnh test cho từng control. | Thêm spec `WEBAPP-PRODUCT-CONTROL-BY-CONTROL-UX-20261010`; trước code phải tạo ledger từ nguồn đã khóa và sinh phiếu action-level, cấm dispatch khi action còn `UNKNOWN`. |
| Luồng nạp thủ công khách → Admin | **Thiếu trong bản plan trước:** Wallet/payment mới được nhắc như authority cần giữ, chưa có checklist riêng cho nhập tiền, thời điểm hiện QR/mã, pending và duyệt Admin. Đây là yêu cầu Owner đã nêu nhưng chưa được tái xác minh trên current main. | Thêm spec `WEBAPP_WALLET_ADMIN_UI_CLOSEOUT_20261010`; kiểm từ customer top-up đến Admin review theo server contract; mọi thử nghiệm chỉ dùng QA cô lập, không sửa ví/payment và không tạo giao dịch production. |
| Tham khảo UX thị trường trước khi thiết kế | **Thiếu tiêu chí có thể kiểm:** plan chưa bắt buộc ghi nguồn tham khảo, ngày xem, pattern áp dụng và ranh giới không sao chép. | Thêm `UI-REF-00`: tối đa 2 nguồn chính thức liên quan mỗi nhóm, lưu URL/ngày và pattern; Bot/API vẫn là nguồn chức năng, tham khảo ngoài chỉ giúp bố cục/tương tác. |
| Admin ERP nằm trong nhóm parity Bot → Web | **Dễ gây nhập nhằng:** nhiều quyền quản trị là app-native, không nhất thiết có hành động Bot tương đương. | Tách Admin billing review và Admin ERP thành `06O/06P`; đối chiếu Bot khi có, nếu không thì ghi `ADMIN_ONLY`/`OWNER_NEW_REQUIREMENT`, không tự gán thiếu parity. |

### 9.2 Current-main source baseline và đường revalidation

`origin/main=86d4ee6e11ddfbc0d4e1dbf63b41d9b3ed7d859b` là mốc source mới
nhất được đọc trong lượt này. So với `17b9494…`, direct presentation-file
delta được xác minh là `static/portal/portal.js`; runtime/contract delta gồm
`copyfast_api.py`, `copyfast_db.py`, các bridge Music/Image/Video/Document
Translation và R4–R10 route/runtime matrices. Đây là **source comparison**,
không phải browser/live/deploy evidence.

| Product / surface | Current-main contract đã xác minh | UI closeout gần nhất | Thay đổi sau checkpoint cần xét | Trạng thái hiện tại và bước kế tiếp |
|---|---|---|---|---|
| Landing / Welcome | Chưa có catalog từng CTA/section current-main trong lượt này; đây là bề mặt khách công khai, không suy từ ảnh lịch sử. | Chưa có closeout control-level | Cần recheck route/DOM/locale/claims trên current main. | `NOT_AUDITED_CONTROL_BY_CONTROL`; kiểm H1, thông điệp chính, CTA, điều hướng auth→app, VI/EN/ZH và mobile. |
| Video | Các route/flow đã có checkpoint hub, nhanh, nhiều cảnh; không coi planner là file video cuối. | #616 | `copyfast_product_video_job_bridge.py`, API và runtime matrices R5–R10 thay đổi; chưa thấy direct `portal.js` delta ngoài #621. | `CHECKPOINT_ONLY_REVALIDATE`; sau các nhóm khác, lập từng action/editor spec từ Bot ledger rồi test route/guard/result. |
| Voice | Current source có TTS, saved/profile/clone surfaces; route/feature controls phải được reconcile với runtime admission. | #617 | #622 runtime admission và R4–R10 contracts/matrices; không có direct presentation path delta được thấy ngoài `portal.js` Music edit. | `CHECKPOINT_ONLY_REVALIDATE`; tách TTS mặc định, saved voice, clone/profile và từng nút quản lý. |
| Music | `/music/create` = `music_background`; `/music/song` có form riêng. Current `portal.js` có background tier 130/150/200 Xu; song tier 200/250/300 Xu, `vocal_mode` auto/male/female/duet, `lyrics`, `song_length_mode` seconds/half/full và duration. Bridge canonical hiện có hai sản phẩm/giá tương ứng trong source. | #618 | **#621 sửa `portal.js` trực tiếp** và thêm Music bridge/API. UI gửi generic feature phase theo mapping; vẫn cần kiểm tương quan exact action → estimate/confirm/bridge/receipt. | `MUST_REVALIDATE`; test toàn bộ control trên `/music/create` và `/music/song`, không chỉ form render. Giá option UI không phải thẩm quyền; phải khớp quote/receipt server. |
| SubDub | Checkpoint mô tả một màn/bốn mode, nhưng local UI test trước đó chỉ thấy guarded CTA/volume local; chưa có file output evidence. | #619 | API/runtime truth matrices tiếp tục đổi; không có direct presentation path change được thấy từ base tới main. | `CHECKPOINT_ONLY_REVALIDATE`; kiểm từng mode, payload/volume/result/report Admin; không gọi local slider là xử lý thật. |
| Image | Current main có Image Generation bridge mới và các trạng thái runtime được cập nhật. | #620 | #623 thêm `copyfast_image_generation_job_bridge.py`; API/runtime matrices R4–R10 thay đổi. | `MUST_REVALIDATE`; tách tạo AI, sửa AI và deterministic edit; map mọi nút tới contract đúng và kiểm output/ownership. |
| Free Tools | Có bề mặt/hub; chưa có catalog current-main control-by-control trong tài liệu này. | Chưa có closeout đủ catalog | Runtime/source inventory thay đổi sau base; chưa đối chiếu action từng tool. | `NOT_AUDITED_CONTROL_BY_CONTROL`; lấy từng action từ Bot ledger + DOM, không đếm hub/card là đủ. |
| Notes / Memory / Reminders | Các capability được nêu ở audit cũ chưa tạo thành action ledger hoàn chỉnh. | Chưa có closeout đủ CRUD | Chưa có current-main action map trong lượt này. | `NOT_AUDITED_CONTROL_BY_CONTROL`; mỗi create/list/search/update/delete/reminder/priority phải có dòng riêng nếu Bot source xác nhận. |
| Documents / PDF / OCR / Translation | Current main thêm Document Translation bridge; route tồn tại không chứng minh tệp dịch được xuất. | Chưa có closeout theo từng nút | `copyfast_document_translate_bridge.py` và API/runtime matrices đổi. | `REVALIDATE_REQUIRED`; tách upload/inspect/translate/convert/download/retry và kiểm file thật ở môi trường được phép. |
| Content / Prompt tools | Có Web surfaces/prompt tools, nhưng draft text không đồng nghĩa AI/provider output hoặc publish. | Chưa có closeout theo mọi action | Không có direct presentation-path delta được xác minh trong lượt này. | `NOT_AUDITED_CONTROL_BY_CONTROL`; tách compose/save/copy/apply/export theo contract thật. |
| Auto-post / Channels | Audit authority trước đó từng ghi channel connection thiếu; trạng thái đó chưa được tái xác minh trên `86d4ee6…`. | Chưa có closeout publish | Chưa có recheck current-main channel/OAuth/receipt evidence. | `REVALIDATE_BACKEND_AND_UI`; không để nút “Đăng” xuất hiện sẵn nếu chưa có channel authority/approval/receipt. |
| Projects / Workboard | Có route/records riêng; không phải Bot job và không được gán nhãn lẫn nhau. | Chưa có closeout từng action | Chưa có current-main control inventory. | `NOT_AUDITED_CONTROL_BY_CONTROL`; tách tạo/sửa/hoàn tất/phân công/lọc và trạng thái. |
| Assets / Downloads | Có private asset surfaces; không lấy metadata/available badge làm bằng chứng tải file được. | Chưa có closeout từng action | Route/engine inventory chưa đối chiếu qua UI hiện tại. | `NOT_AUDITED_CONTROL_BY_CONTROL`; tách preview/download/delete/share, owner check và file readiness. |
| Support / Tickets | Support surface có route/API; chưa đối chiếu mọi form/status/attachment/report. | Chưa có closeout toàn action | Cần recheck route + current copy. | `NOT_AUDITED_CONTROL_BY_CONTROL`; form giữ input khi lỗi, action/ticket state và response rõ. |
| Wallet / manual top-up + Admin billing | Tài liệu cũ có route khách `/wallet/topup` và nhiều báo cáo lỗi trước đây; lần này chưa tái kiểm toàn bộ current-main flow, số tiền, thời điểm hiện QR/mã và Admin approval. | Chưa có closeout control-level hiện hành | Cần đọc lại route/DOM/API/permission và map Bot payment contract sau khi khóa nguồn; không suy từ ảnh cũ. | `REVALIDATE_HIGH_RISK`; Customer amount → confirm → instructions → pending; Admin review/approve/reject theo quyền, audit và idempotency; thử nghiệm không tạo wallet/production mutation. |
| Members | Chưa có action catalog current-main trong lượt này. | Chưa có closeout | Chưa có current-main control inventory về role/thành viên/audit. | `UNKNOWN`; kiểm quyền/owner và audit trước khi vẽ action. |
| Rewards | Chưa có action catalog current-main trong lượt này. | Chưa có closeout | Chưa có current-main control inventory về điều kiện/điểm/lịch sử. | `UNKNOWN`; xác minh authority và điều kiện; không gộp với Members. |
| Community / Referral | Chưa có action catalog current-main trong lượt này. | Chưa có closeout | Chưa có current-main control inventory. | `UNKNOWN`; chỉ giữ chức năng có nguồn/owner rõ. |
| Admin ERP | Checklist legacy 19-spec có nhiều trạng thái lịch sử, không phải chứng nhận mọi nút Admin hiện nay. | Các đợt Admin trước đây, chưa có button catalog current-main | Runtime matrices/API tiếp tục đổi; chưa rebaseline trang Admin trong lượt này. | `REBASELINE_REQUIRED`; mỗi thao tác quản trị cần role, record, audit, confirm/undo, lỗi và bằng chứng riêng. |
| Shared shell | Shell/locale/theme/navigation đang là nguồn dùng chung; current-main direct UI diff phải kiểm lại theo rendered state, không dựa dirty worktree. | Không có closeout toàn shell | `portal.js` thay đổi; `portal-i18n.js`, CSS/theme/template không đổi trong file-diff giữa base và main. | `OPEN`; inventory nav/account/locale/theme/install/assistant/focus/back ở anonymous + signed. |
| Motion | `portal-motion.js` tại current main có tree hash `2bb208658eb989ad32c83bbaadf58fe75cebd564`; source main không đổi từ base được so. | WA-35/36 chưa đóng | R11 là local candidate `17b9494… + dirty overlay`, không phải current main; nguồn gửi nêu 12 lỗi nhưng chưa có trace current-main. | `OPEN_NOT_REPRODUCED_ON_MAIN`; sau khi khép phần motion dang dở, rerun cold/warm, normal/reduced, rapid/back-forward trên current main. |

### 9.3 Thứ tự cập nhật sau khi chốt plan

1. **Task hiện tại:** hoàn tất tài liệu plan/checklist/spec rồi dừng. Không triển
   khai UI trong cùng lượt.
2. **Việc kế tiếp — phần đang dở, không mở product mới:** giữ nguyên mọi thay đổi
   trong worktree `work/toanaas-video-ui-release-20261007`; tiếp tục WA-35 entrance
   lifecycle RCA. Probe phải ghi `animationstart/end/cancel`, `getAnimations()`,
   `isConnected`, class/`data-portal-motion` mutation và mẫu computed state
   khoảng 5 giây đầu cho `/dashboard` và `/features`. Phân biệt animation bị huỷ,
   thay CSS, remount/gỡ DOM hay event listener sai; chỉ sau khi có RED evidence
   mới viết test hồi quy rồi sửa đúng nguyên nhân. Đồng thời tách riêng điều tra
   long task/frame gap, chạy WA-36 reduced-motion và protected comparators. Không
   reset/stash/rebase mù, không dùng production/provider.
3. Chỉ sau khi việc dở dang đóng tại ranh giới an toàn: fetch/rebase lại main,
   khóa Bot source theo `SPEC-00`, tạo action ledger và control ledger; nếu
   current main tiến sau `86d4ee6…`, cập nhật matrix trước khi giao việc.
4. Sau inventory: ghi tham chiếu `UI-REF-00` → landing/welcome → shared shell theo
   spec riêng → Voice → Music → SubDub → Image → Wallet/manual top-up và Admin
   billing review (spec riêng) → từng nhóm không phải Video (Members và Rewards
   là hai nhóm riêng) → mọi sản phẩm Video/editor → whole-site motion/final matrix.
5. Một capability/control nhỏ mỗi spec; không bật nhiều `RUNNING` cùng lúc.
   Builder brief phải có đường dẫn file, dòng/selector, spec hoàn chỉnh, file
   cấm sửa, lệnh verify và output mong đợi; thiếu một mục thì chưa giao.
6. Checklist điều phối riêng cho wave và từng action nằm tại
   `reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-20261010.md`; shared
   shell có spec riêng tại
   `docs/superpowers/specs/2026-10-10-webapp-shared-shell-ui-closeout.md`;
   không dùng checklist ERP P0 cũ làm bằng chứng đóng UI sản phẩm.

### 9.4 Trạng thái chốt lượt plan

```ini
PLAN=UPDATED_WITH_CURRENT_MAIN_REBASELINE_BUTTON_LEVEL_WALLET_ADMIN_AND_REFERENCE_GATES
CURRENT_MAIN_SHA=86d4ee6e11ddfbc0d4e1dbf63b41d9b3ed7d859b
BUTTON_CONTROL_LEDGER=NOT_CREATED_YET; REQUIRED_BEFORE_PRODUCT_CODE
UI_REFERENCE_GATE=REQUIRED_AFTER_SOURCE_LEDGER; NOT_RUN
WALLET_ADMIN_SPEC=READY_FOR_REBASELINE; CUSTOMER_AND_ADMIN_UI_NEED_CURRENT_MAIN_REVALIDATION
TASK_CHECKLIST=reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-20261010.md
MOTION_FINAL_SPEC=docs/superpowers/specs/2026-10-10-motion-webapp-surfaces-final.md
SHARED_SHELL_SPEC=docs/superpowers/specs/2026-10-10-webapp-shared-shell-ui-closeout.md
WALLET_ADMIN_SPEC=docs/superpowers/specs/2026-10-10-webapp-wallet-admin-ui-closeout.md
BOT_CANONICAL_BASELINE=NOT_LOCKED
FULL_ACTION_LEDGER=OPEN
WA35=OPEN_PARTIAL_MEASUREMENT_R11
WA36=OPEN
PRODUCT_CODE_CHANGED_THIS_TASK=0
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
DEPLOY=NO
LIVE_PASS=NO
NEXT=STOP_AFTER_PLAN; RESUME_WA35_ENTRANCE_LIFECYCLE_RCA; THEN_REBASELINE_AND_EXECUTE_PLAN
```
