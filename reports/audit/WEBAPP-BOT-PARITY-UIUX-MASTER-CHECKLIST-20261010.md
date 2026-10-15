# Checklist tổng Web App standalone — UI/UX, locale và motion

> Đây là checklist điều phối Web App. “Bot parity” ở đây chỉ là tham chiếu
> luồng và tên sản phẩm; không sửa Bot/Core trong checkpoint này.

## Quy tắc khóa phạm vi

- [x] Giữ màu xanh dương/xanh ngọc và nền tối xanh lam; không đổi sang đen
      thuần.
- [x] Ưu tiên bố cục dọc, responsive, không tràn ngang.
- [x] VI/EN/ZH dùng đúng một ngôn ngữ cho fixed chrome của từng locale.
- [x] Không dịch dữ liệu động, mã, ID, revision, timestamp hoặc receipt.
- [x] Không đổi route/action/field/capability/CSRF/idempotency/revision.
- [x] Không provider call, wallet mutation, production mutation hoặc deploy.
- [ ] Browser QA runtime cô lập được cung cấp và chạy ổn định.
- [ ] Phiếu Antigravity #217: đã soạn đúng phạm vi; lần giao ngày 2026-10-15
      không chạy vì script trả `LOI: khong tim thay agy.exe`; không dùng báo cáo
      giả để đóng checklist.

## Checkpoint đã xử lý

- [x] R207 — Content Studio board/new.
- [x] R208 — Content Studio detail.
- [x] R209 — Publish Review.
- [~] R210 — Workboard locale/presentation: source xanh; browser acceptance
      còn mở. Spec: `docs/superpowers/specs/2026-10-15-workboard-locale-r210.md`.
- [~] R211 — Notes/Memory Center locale/presentation: source xanh; browser
      acceptance còn mở. Spec: `docs/superpowers/specs/2026-10-15-memory-center-locale-r211.md`.
- [~] R212 — Campaign/Calendar/Approvals locale/presentation: source xanh;
      browser acceptance còn mở. Spec: `docs/superpowers/specs/2026-10-15-campaign-calendar-approvals-locale-r212.md`.
- [~] R213 — Các surface non-video còn fixed copy: R213-01 Free Prompt Gallery
      và R213-02 Audio Workspace shell đã xanh source; browser acceptance vẫn
      mở vì chưa có runtime QA cô lập.

## R210 — Workboard chi tiết

- [x] Hero, route title và description theo locale.
- [x] Tab bảng/danh sách/tạo mới và aria-label.
- [x] Bộ lọc, trạng thái, mức ưu tiên, phân trang.
- [x] Kanban, danh sách, metrics và empty/loading/failed/guarded.
- [x] Tạo/sửa công việc, reference picker và field help.
- [x] Checklist, lịch sử phiên bản, hoạt động.
- [x] Lịch nhắc, xác nhận lại, hủy lịch và trạng thái guard.
- [x] Catalogue `workboard.*` cân bằng VI/EN/ZH.
- [x] Action/route/field/revision contract không đổi.
- [x] Focused 64/64; Node all 420/420; syntax; diff-check.
- [ ] Render thật trên 375/390/768/1440 ở VI/EN/ZH.
- [ ] Keyboard/focus, computed style, console/network và persistence trên
      runtime QA.

## R211 — Notes/Memory Center chi tiết

- [x] Ghi chú: tạo, lọc, danh sách, chi tiết, chỉnh sửa, lưu trữ, khôi phục.
- [x] Lịch sử phiên bản, khôi phục phiên bản và lời nhắc liên kết.
- [x] Lời nhắc: tạo, sửa, lọc, hoàn tất, tạm dừng, tiếp tục và hủy.
- [x] Trạng thái hoạt động kiểm toán: đang tải, chưa xác minh, rỗng và có dữ liệu.
- [x] Phân trang, trạng thái bảo vệ, ranh giới dữ liệu và thông báo không giả giao nhận.
- [x] Catalogue `memory.*` cân bằng VI/EN/ZH (139 khóa cố định).
- [x] Chuỗi cố định của Notes/Reminders đi qua `memoryText()`; dữ liệu động
      (tiêu đề, nội dung, thẻ, thời gian, mã, ID, revision, receipt) giữ nguyên.
- [x] Route/action/field/capability/CSRF/idempotency/revision contract không đổi.
- [x] Test R211 3/3; toàn bộ Node suite 423/423; syntax; diff-check.
- [ ] Render thật trên 375/390/768/1440 ở VI/EN/ZH.
- [ ] Keyboard/focus, computed style, console/network và persistence trên
      runtime QA.

## R212 — Campaign / Calendar / Approvals chi tiết

- [x] Bảng kế hoạch: trạng thái bảo vệ, đang tải, lỗi, rỗng và quyền chỉ xem.
- [x] Tạo kế hoạch: brief, CTA, mục tiêu, nền tảng, mốc nội bộ và nút gửi.
- [x] Chi tiết kế hoạch: thông tin trạng thái, liên kết, mốc lịch, ghi chú và
      ranh giới dữ liệu; không thay đổi ID hoặc dữ liệu động.
- [x] Cập nhật trạng thái/tự rà soát và chỉnh sửa kế hoạch qua helper locale;
      giữ nguyên action, CSRF, idempotency và revision.
- [x] Lịch nội dung: đổi tháng, lọc trạng thái/nền tảng, agenda, ngày trống,
      thông báo cửa sổ dữ liệu và điều hướng về chi tiết.
- [x] Lời nhắc trong ứng dụng: tạo, xác nhận lại, hủy, trạng thái bảo vệ,
      timezone và guard source/revision.
- [x] Hàng tự rà soát: metrics, danh sách cần xử lý, trạng thái rỗng và liên
      kết sang quy trình quản trị chính thức.
- [x] Catalogue `campaignUi.*` cân bằng VI/EN/ZH (204 khóa) và được gộp vào
      `MESSAGES` trước khi Portal render.
- [x] Fixed chrome Campaign không còn cụm tiếng Anh xen trong vùng renderer;
      dữ liệu động (tiêu đề, ghi chú, URL, ID, timestamp, receipt) giữ nguyên.
- [x] Route/action/field/capability/CSRF/idempotency/revision contract không đổi.
- [x] Test R212 2/2; toàn bộ Node suite 425/425; syntax; diff-check.
- [ ] Render thật trên 375/390/768/1440 ở VI/EN/ZH.
- [ ] Keyboard/focus, computed style, console/network và persistence trên
      runtime QA.

## Hàng đợi theo thứ tự

- [x] R211 — Notes/Memory Center: source xanh; browser acceptance còn mở.
- [x] R212 — Campaign/Calendar/Approvals: source xanh; browser acceptance còn mở.
- [x] R213 — Các surface non-video còn fixed copy: source xanh; browser
      acceptance còn mở vì QA runtime cô lập chưa khả dụng.
- [~] R214 — Video UI/UX và product lanes: source xanh; browser acceptance còn
      mở vì QA runtime cô lập chưa khả dụng. Spec:
      `docs/superpowers/specs/2026-10-15-video-uiux-r214.md`; report:
      `reports/audit/WEBAPP-E0-VIDEO-UIUX-R214-20261015.md`.
- [~] R215 — Nghiệm thu UI/UX toàn app: static source gate xanh; browser
      acceptance còn mở vì QA runtime cô lập chưa khả dụng. Spec:
      `docs/superpowers/specs/2026-10-15-full-uiux-acceptance-r215.md`; report:
      `reports/audit/WEBAPP-E0-FULL-UIUX-ACCEPTANCE-R215-20261015.md`.
- [~] R216 — Motion source gate đã xanh; browser acceptance và CLS/LCP/INP runtime
      còn mở. Spec: `docs/superpowers/specs/2026-10-15-motion-lifecycle-compositor-r216.md`;
      report: `reports/audit/WEBAPP-E0-MOTION-LIFECYCLE-COMPOSITOR-R216-20261015.md`.
- [x] R216-L — Nút cài ứng dụng ở cả hai auth renderer đã bỏ chuỗi trộn `App`,
      dùng catalogue locale (`installGuide.title`/`text.install`) và có regression
      gate; không đổi action/route. Catalogue auth hiện không còn khóa trùng và
      đã có regression kiểm tra trùng khóa.
- [~] R216-L live recheck — lần đọc trước trên `/login?lang=vi|en|zh` xác nhận
      fixed chrome theo đúng từng locale và không còn hậu tố `App` xen trong
      vùng hiển thị; tuy nhiên lần kiểm tra mới nhất `/features` chuyển tới
      `/login?next=/features` và AX lại thấy `Tải & Cài đặt App TOAN AAS`.
      Recheck lần 4 ngày 2026-10-15 trên đúng URL vẫn thấy nút cũ trong AX và
      screenshot. Source locale vẫn xanh nhưng live drift trên next-route auth
      còn mở; probe DOM lần 5 vẫn thấy chuỗi cũ trong nút ẩn (`visible=false`),
      không đăng nhập hoặc gửi biểu mẫu.
- [~] R216-H live recheck — viewport khoảng 327×667 vẫn nhận bundle landing cũ:
      header bị cắt cụm locale/theme/action và FAB PWA cũ che một phần proof.
      Source media rule và placement inline đã xanh; chờ delivery rồi chụp lại
      live trước khi đóng.

## R213-01 — Free Prompt Gallery locale chrome

- [x] Có helper `freePromptGalleryText()` và catalogue cân bằng VI/EN/ZH.
- [x] Localize intro, thống kê, bộ lọc, trạng thái kết quả, phân trang, chi tiết
      prompt, xác nhận lưu và receipt; không dịch prompt/title/tag/ID do server trả.
- [x] Nhãn, placeholder, help text và option mặc định của bộ lọc không còn
      literal tiếng Việt; VI/ZH không còn fixed English UI; EN không fallback
      tiếng Việt.
- [x] Giữ nguyên route `/free-prompt-gallery`, các `data-portal-action`,
      `data-free-prompt-gallery-*`, nút sao chép/lưu và boundary không thực thi.
- [x] Test R213-01 focused 5/5, toàn bộ Node suite 430/430, syntax và
      diff-check.
- [ ] Browser runtime QA cô lập vẫn là điều kiện mở; không tuyên bố LIVE_PASS.

## R213-02 — Audio Workspace / Audio Hub shell locale

- [x] Có helper `audioWorkspaceText()` và catalogue VI/EN/ZH cân bằng cho
      shell/home của `/media-workspace` và `/audio-hub`.
- [x] Đã localize overview, policy boundary, create/list/filter shell, audit
      feed, collection-card chrome và Audio Hub next-step cards; option values
      và server-owned collection data không đổi.
- [x] Đã localize nhãn mode/event mà shell dùng; không đổi prompt mode, role,
      route, action, capability, CSRF, idempotency hoặc revision.
- [x] Test focused R213-02 5/5; toàn bộ Node suite 435/435; syntax và
      `git diff --check` xanh.
- [ ] Detail/editor và browser acceptance giữ trạng thái mở cho spec riêng;
      không tuyên bố LIVE_PASS.

## R214 — Video UI/UX và locale presentation

- [x] Video Hub `/tools/video` có nhóm tác vụ dọc, CTA rõ, trạng thái
      ready/guarded và boundary trước xử lý.
- [x] `/video/create` và `/video/multiscene` giữ core fields (`brief`,
      `scene_count`, `format`) trước, thiết lập phụ trong disclosure và flow
      bảy bước nhập → plan → quote → confirm → progress → result → recovery.
- [x] Video Studio `/video-studio` và detail giữ form plan, cảnh, runtime
      estimate, version/history, activity, trạng thái và boundary metadata-only.
- [x] Catalogue `videoUi.*` và `videoStudioUi.*` có keyset cân bằng VI/EN/ZH;
      fixed chrome không trộn ngôn ngữ ở các surface R214.
- [x] Dữ liệu động, ID, revision, timestamp, tags và canonical route/action/
      field/capability/CSRF/idempotency không đổi.
- [x] Không có output/provider/job/wallet claim giả trong Video Hub/form/Studio.
- [x] Focused R214 10/10; toàn bộ Node suite 445/445; syntax và
      `git diff --check` xanh.
- [ ] Render thật trên 375/390/768/1440 ở VI/EN/ZH.
- [ ] Keyboard/focus, computed style, console/network và persistence trên
      runtime QA.
- [ ] `LIVE_PASS` chỉ ghi sau khi QA runtime cô lập có bằng chứng DOM/screenshot
      và tương tác thật.

## R215 — Nghiệm thu UI/UX toàn Web App

- [x] Skip link trỏ đúng `#portal-main`; `<main>` có `tabindex="-1"`.
- [x] Boot skeleton có title/copy/grid, không dùng spinner trống làm shell duy nhất.
- [x] Palette light/dark giữ xanh dương–xanh ngọc; dark canvas là navy/teal,
      chữ sáng và focus tương phản.
- [x] Shell responsive có min-width an toàn, workspace không tràn ngang và
      media query mobile giữ card theo hàng dọc.
- [x] Focus-visible và reduced-motion static fallback tồn tại; không có
      `transition: all` trong Portal stylesheets.
- [x] Customer/Admin/product lane markers vẫn tồn tại; không đổi route/action/
      field/capability/CSRF/idempotency/revision.
- [x] Focused R215 5/5.
- [ ] Full browser matrix VI/EN/ZH × light/dark × 375/390/768/1440.
- [ ] Keyboard/focus, computed style, console/network và persistence trên QA runtime.
- [ ] Chỉ chuyển R215 sang đóng sau khi có evidence runtime; R216 Motion chỉ mở
      sau source gate này.

## Motion backlog bắt buộc sau UI/UX

- [x] Chặn render auth lần hai cắt animation entry; giữ nguyên DOM chính,
      chờ lifecycle entry kết thúc rồi mới chuyển `settled`.
- [x] Giữ ổn định chiều cao vùng provider auth khi dữ liệu Google/Apple hydrate;
      không layout shift.
- [x] Thay transition `left` bằng transform compositor.
- [x] Sửa scroll reveal để biến đổi do scroll không bị transition trễ một nhịp.
- [x] Không còn inline `transition: all` trong Portal renderer; gate static kiểm
      tra cả JavaScript renderer và stylesheet.
- [x] Dashboard template cũ bỏ shorthand transition mọi thuộc tính; hover chỉ
      chuyển `transform`/`border-color`. Motion/static/features focused 26/26,
      full Node 469/469, JS syntax 4/4, py_compile 17/17 và diff-check đạt
      ngày 2026-10-15.
- [x] Features route huỷ IntersectionObserver, RAF, timer và listener `focusin`
      khi unmount; callback cũ không còn sửa DOM đã tách. Regression riêng
      `feature-catalog-route-presentation.test.mjs` đạt 6/6; hydrate async cũng
      bị chặn nếu `portal-main` đã bị thay hoặc đường dẫn không còn là
      `/features`.
- [x] Landing lắng nghe thay đổi `prefers-reduced-motion` và huỷ lifecycle đang
      chạy; metadata scroll chỉ ghi khi giá trị đổi, bỏ biến offset không có CSS
      consumer, bỏ gradient nền phụ thuộc progress khỏi hot path.
- [x] Gỡ `will-change`/`translateZ(0)` áp blanket lên mọi page/card/table; chỉ
      giữ hint compositor ở các control thực sự có motion. Focused motion mới
      đạt 19/19; dark input palette gate và full Node đạt 469/469.
- [x] Dark theme dùng nền navy/xanh và ô nhập dùng token `--portal-dark-*`;
      không còn map sang palette obsidian gần đen.
- [x] Features hydration giữ định danh `portal-main` và route `/features` qua
      toàn bộ lần đọc async; kết quả cũ không được render vào shell đã thay.
      Dấu `/` cuối được chuẩn hóa nên `/features` và `/features/` dùng cùng
      acceptance; regression `feature-catalog-route-presentation.test.mjs` đạt
      6/6.
- [x] Giữ user gesture khi mở Telegram sau async; regression test hiện có xanh.
- [x] PWA install chỉ gọi native prompt khi `beforeinstallprompt` thật; không
      còn toast giả, regression test hiện có xanh.
- [x] Auth install CTA dùng catalogue locale `installGuide.title`; không còn
      hard-code `Tải & Cài đặt App TOAN AAS` trong source.
- [x] Auth install CTA dùng icon SVG theo cùng hệ `portal-icon`, không dùng
      emoji phụ thuộc font; `auth-pwa-install-control.test.mjs` kiểm tra cả
      cấu trúc icon và bản dịch VI/EN/ZH.
- [x] Verify reduced-motion và ghi static contract cho CLS/LCP/INP; nội dung
      vẫn đọc được và motion được tắt an toàn.
- [ ] Đo CLS/LCP/INP thật trên QA runtime; chưa có runtime nên chưa đóng.
- [~] Landing header ở màn hình hẹp đã có nhánh responsive riêng: giữ nguyên
      hàng thương hiệu và bọc cụm ngôn ngữ/giao diện/nút hành động xuống hàng,
      không ép tràn ngang. Static gate đạt 1/1; live 327×667 còn drift do
      bundle cũ nên browser recheck sau source delivery vẫn mở.

## Cổng nghiệm thu chung

- [ ] Không còn fixed English xen trong VI/ZH trên surface đã đóng.
- [ ] Desktop/tablet/mobile không clipping, overlap hoặc horizontal overflow.
- [ ] Heading/type scale tương phản và dễ đọc; CTA có thứ bậc rõ.
- [ ] Empty/loading/failed/guarded/report state trung thực.
- [ ] Không dead click, không fake output, không tự ý tạo job/provider.
- [ ] Có screenshot/DOM/runtime evidence trước khi ghi PASS.

## Trạng thái bằng chứng hiện tại

```ini
CURRENT=R216-L
SOURCE=GREEN
BROWSER=PARTIAL_LIVE_AX_SCREENSHOT_AUTH_LOCALE_DRIFT_ON_FEATURES_NEXT_ROUTE;LANDING_HEADER_PWA_DRIFT_OLD_BUNDLE;QA_FIXTURE_LOCALHOST_BLOCKED
LIVE_PASS=NO
COMMIT=LOCAL_BRANCH_HEAD
PUSH=YES (webapp-checklist-r116)
PR=OPEN #647
PR_URL=https://github.com/manhtoangreensky-wq/toan-aas-standalone/pull/647
MERGE=NO
DEPLOY=NO
NEXT=RECHECK_R216_L_NEXT_ROUTE_AND_R216_H_LANDING_AFTER_DELIVERY;ANTIGRAVITY_217_WHEN_AGY_AVAILABLE;FULL_BROWSER_ACCEPTANCE_RUNTIME_METRICS
```
