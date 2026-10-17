# Kế hoạch tổng WebApp standalone — UI/UX, parity sản phẩm, locale và motion

**Ngày lập:** 2026-10-16
**Chương trình:** `WEBAPP-UIUX-PARITY-20261016`
**Nhánh tài liệu:** `webapp-plan-r116` → push vào `webapp-checklist-r116`
**Mục tiêu:** có một thứ tự thi công duy nhất, một checklist có trạng thái và các spec đủ cụ thể để người thực hiện không phải đoán.

## 1. Phạm vi và hàng rào an toàn

Phạm vi của plan là WebApp standalone gồm customer shell, product lanes, Admin shell,
UI/UX, locale, accessibility, responsive, motion và bằng chứng browser/live. Bot/Core
chỉ là nguồn tham chiếu parity; không sửa repo Bot trong plan này.

Trong lượt lập tài liệu này **không** được:

- gọi provider trả phí, tạo job thật, trừ/nạp Xu, sửa PayOS hoặc dữ liệu production;
- đổi route, action, field, capability, CSRF, idempotency, revision hoặc server-owned data;
- đổi brand xanh dương/xanh ngọc và nền tối xanh navy thành màu đen/tím;
- merge, deploy VPS hoặc gọi API làm mutation;
- đóng một mục chỉ bằng HTTP 200 hoặc source PASS khi chưa có runtime evidence.

Các hạng mục engine/bridge/provider/wallet/PayOS được ghi ở wave deferred để không bị
bỏ sót, nhưng chỉ mở khi Owner giao task riêng và qua safety gate.

## 2. Nguồn sự thật đã đối chiếu

| Nguồn | Trạng thái dùng trong plan |
|---|---|
| `reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-20261010.md` | checklist cũ, giữ lịch sử và bằng chứng source |
| `reports/audit/WEBAPP-E0-FULL-UIUX-ACCEPTANCE-R215-20261015.md` | source gate 5/5, browser acceptance còn mở |
| `reports/audit/WEBAPP-E0-MOTION-LIFECYCLE-COMPOSITOR-R216-20261015.md` | motion source gate xanh; live drift R216-H/R216-L/R216-P còn mở |
| `reports/audit/WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.md` | 31 capability, 139 customer entrypoints, 41 admin surfaces; real-output/bridge gap được phân loại |
| `docs/superpowers/plans/2026-10-14-webapp-uiux-motion-replan-r198.md` | thứ tự R207→R216 và motion backlog trước đó |
| PR #647 / HEAD `f59eacf63a49534854dc7cde06e5baed6546dc58` | baseline remote hiện tại; PR còn mở, chưa merge/deploy |

### Bằng chứng hiện tại không được suy rộng

- Source/static: Node suite gần nhất `469 passed`, focused gates xanh, syntax và
  `git diff --check` xanh theo R216.
- Live read-only chưa phải `LIVE_PASS`: mobile landing còn clipping/FAB bundle cũ,
  `/features → /login?next=/features` còn CTA locale cũ trong bundle, auth-product
  surfaces sau đăng nhập chưa có ma trận evidence.
- Không có bằng chứng live cho Product Video, Image AI, Voice clone, Music generation,
  Smart Multi SubDub, autopost channel bridge hoặc admin duyệt tác vụ khách; các mục
  này phải giữ `OPEN/BLOCKED`, không ghi PASS.

## 3. Chuẩn thiết kế bất biến

Đây là chuẩn nghiệm thu cho mọi surface, không phải lời gợi ý chung chung.

### 3.1 Màu và chữ

- Giữ semantic token xanh dương/xanh ngọc và dark canvas xanh navy trong
  `static/portal/portal.css` và `static/portal/portal-theme.css`; không thêm palette đen
  thuần hoặc tím làm màu chủ đạo.
- Light/dark phải có cặp chữ/nền đạt WCAG AA: chữ thường ≥ 4.5:1, chữ lớn/UI ≥ 3:1;
  focus ring không được chỉ khác bằng màu nền.
- Type scale cố định: body 16px (mobile không nhỏ hơn 16px), helper 14px, label 14–16px,
  heading trang 32px desktop/28px mobile, section 24/20px, card title 18px; line-height
  body 1.5, heading 1.2–1.3. Kiểm tra chuỗi dấu tiếng Việt `Ẫ Ặ Ệ Ộ Ỡ Ự ỷ ẳ` ở mọi weight.
- Fixed chrome của VI/EN/ZH dùng đúng một ngôn ngữ; chỉ giữ tên riêng/danh từ sản phẩm
  được phép (`Telegram`, `PayOS`, `TikTok`, `Facebook`, `SFX`, `ASR`, `SRT`, `Content
  Studio`). Không dịch ID, URL, timestamp, receipt hoặc dữ liệu server.

### 3.2 Bố cục, component và thao tác

- Spacing scale chỉ dùng 4/8/12/16/24/32/48px; radius 12px cho field/card và 16px cho
  panel lớn; border 1px theo semantic token; không đặt số lẻ tùy ý.
- Mobile-first, breakpoint evidence bắt buộc ở 320/375/390/414/768/1024/1440px; không
  có horizontal overflow. Bảng rộng chuyển thành card dọc hoặc wrapper cuộn có nhãn.
- Mọi target chạm/click ≥44×44px, khoảng cách giữa target ≥8px; icon-only button có
  accessible name và dùng SVG hiện có, không dùng emoji làm icon.
- Mỗi form có label thật, helper/error ngay cạnh field, trạng thái disabled/loading/
  success/failed/guarded; không dùng placeholder thay label.
- Mỗi surface có một CTA chính, CTA phụ đặt sau disclosure; trạng thái động phải ghi
  rõ `draft`, `đang xử lý`, `hoàn tất`, `bị chặn`, `cần thử lại` và output thật/không có.

### 3.3 Motion và hiệu năng

- Chỉ animate `transform` và `opacity` trong hot path; cấm `transition: all`, `left`,
  `width`, `height` cho scroll/drag. Micro interaction 150–300ms, entry 240–450ms,
  exit nhanh hơn entry; easing ease-out/ease-in, không dùng linear cho UI.
- Auth render chỉ có một entry lifecycle; async hydration không giết animation hoặc
  làm thay đổi chiều cao provider. Scroll reveal phải xuất hiện khi phần tử vào viewport,
  không tạo vùng trống chờ một nhịp cuộn.
- `prefers-reduced-motion: reduce` tắt parallax/stagger và vẫn giữ trạng thái nội dung;
  cleanup observer/RAF/timer/listener khi unmount hoặc đổi route.
- PWA install CTA chỉ hiển thị sau `beforeinstallprompt` thật hoặc hướng dẫn có trạng
  thái; không để FAB che nội dung. Mục tiêu đo runtime: CLS < 0.10, LCP ≤2.5s, INP ≤200ms
  ở viewport đại diện; nếu chưa đo được ghi `RUNTIME_UNAVAILABLE`.

## 4. Thứ tự wave duy nhất

Không nhảy wave. Mỗi wave chỉ chuyển sang `CLOSED` khi checklist và evidence của wave
đó đều xanh.

### W0 — Baseline, evidence ledger và source/live drift

Khóa SHA, inventory route/product/admin, protected contracts, live defects và trạng thái
QA runtime. Cập nhật checklist ngay sau mọi lần verify. Đầu ra: spec R217-00.

### W1 — Shell, responsive và visual foundation

Sửa theo thứ tự mobile header/overflow → type/spacing hierarchy → dark/light contrast →
table/card stacking → PWA placement. Không làm motion để che layout lỗi. Đầu ra: R217-01.

### W2 — Locale purity và copy convention

Quét fixed chrome customer + admin + product lanes ở VI/EN/ZH; tách fixed copy khỏi
server data; khóa duplicate key và fallback sai ngôn ngữ. Đầu ra: R217-02.

### W3 — Auth lifecycle, first paint và accessibility

Giữ skip link, main target, server/guard boundary hiện có; kiểm tra auth async, provider
reservation, skeleton, focus, keyboard, error/empty/guarded. Đầu ra: R217-03.

### W4 — Product IA/UX theo lane, lấy flow Bot làm tham chiếu

Mỗi lane chỉ một workspace chính, có input → options → preflight → confirm → progress →
result/recovery; có báo cáo thật và boundary rõ khi engine/bridge chưa sẵn sàng. Chia nhỏ:

1. Image: tạo ảnh AI, chỉnh sửa ảnh, upload/reference, preset, output gallery.
2. Voice: giọng mặc định, giọng lưu/tải lên, preview, clone/voice library, export.
3. Music: nhạc nền và nhạc có lời trên một hub, preset, lyrics/instrumental, preview,
   output/history.
4. SubDub: một giao diện với phụ đề gốc, dịch phụ đề, lồng tiếng, combo; chọn 1/nhiều
   giọng, Smart Multi auto-detect, thư viện giọng liên kết Voice, ngôn ngữ theo catalog.
5. Video: product lanes, AI edit và manual edit, scene/timeline, upload/reference,
   progress, result/download/recovery.
6. Content/Workboard/Free Tools/Notes/Projects: tạo, lưu, sửa, phiên bản, lịch,
   publishing boundary, empty/loading/error và handoff.

Đầu ra: R217-04…R217-08; mỗi lane có một spec hẹp và test riêng, không gom refactor.

### W5 — Admin/customer visibility và permission presentation

Rà soát Admin shell theo chiều dọc, menu, operations, billing/top-up, jobs/assets,
customer directory, support, audit, reliability, ERP data views. Mọi tác vụ khách phải
chỉ ra record/request/job/report tương ứng; owner thấy toàn bộ, role khác theo policy.
UI-only contract được nghiệm thu trước; bridge/RBAC/server mutation ghi deferred nếu
chưa có bằng chứng backend. Đầu ra: R217-09.

### W6 — Motion lifecycle và perceived performance

Chỉ mở sau W1–W5 source gate. Đóng lần lượt auth render, skeleton/CLS, hover/focus,
scroll reveal, compositor, reduced motion, popup gesture, PWA readiness, then trace
CLS/LCP/INP/FPS. Đầu ra: R217-10.

### W7 — Authenticated QA matrix và parity evidence

Dựng fixture QA cô lập không provider/wallet mutation; ma trận route×locale×theme×viewport
cho customer và Admin; kiểm tra keyboard/focus, console/network, persistence, state
transitions và output boundary. Không dùng production làm QA. Đầu ra: R217-11.

### W8 — Live read-only recheck sau delivery hợp lệ

Chỉ đọc runtime sau khi code đã được Owner cho phép delivery. Recheck các defect live
R216-H/L/P, chụp DOM/screenshot/console/network/asset fingerprint, so sánh SHA. Không
merge/deploy trong plan này. Đầu ra: R217-12.

### W9 — Deferred technical program (không thực thi trong lượt tài liệu)

Giữ danh sách không được quên: Web-to-Bot adapter và real output polling/download cho
Video/Image/Voice/Music/SubDub, Smart Multi backend, autopost channel token bridge,
support ticket bridge, Admin cross-bridge trace, manual top-up approval wiring. Các mục
này chỉ mở bằng task riêng có Owner gate `PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0` cho QA
và không được đánh tráo thành UI PASS. Đầu ra: R217-13 deferred register.

## 5. Quy tắc nghiệm thu và trạng thái

Trạng thái hợp lệ: `TODO`, `SOURCE_GREEN_RUNTIME_OPEN`, `LIVE_DRIFT_OPEN`, `BLOCKED`,
`DEFERRED`, `CLOSED_WITH_EVIDENCE`. Một spec chỉ đóng khi có:

1. diff đúng allowed paths và không đụng protected contracts;
2. lệnh verify ghi số pass/fail thật, `git diff --check`, syntax phù hợp;
3. browser evidence tương ứng (DOM + screenshot + console/network + viewport) nếu spec
   yêu cầu runtime;
4. checklist cập nhật cùng commit hoặc commit kế tiếp, có SHA và ngày;
5. báo cáo trung thực `PROVIDER_CALLS`, `WALLET_MUTATIONS`, `PRODUCTION_DATA_MUTATIONS`,
   `DEPLOY`, `LIVE_PASS`.

Không coi `MERGED`, `HTTP 200`, hoặc source-only test là live success.

## 6. Lệnh kiểm tra chuẩn

```powershell
node --test tests/r215-full-uiux-static-acceptance.test.mjs
node --test tests/r216-motion-lifecycle-compositor.test.mjs tests/current-main-motion-static-gates.test.mjs
node --test tests/*.test.mjs
node --check static/portal/portal.js
node --check static/portal/portal-auth.js
node --check static/portal/portal-motion.js
git diff --check
```

Khi QA runtime được cấp, bổ sung browser matrix theo R217-11; không thay các lệnh trên
bằng kiểm tra thủ công không có output.

## 7. Điều kiện dừng của lượt này

Lượt hiện tại chỉ tạo tài liệu và push branch. Không sửa mã nguồn sản phẩm, không chạy
provider, không login/mutation, không merge/deploy. Sau khi push, báo cáo SHA/link và
dừng chờ Owner mở wave tiếp theo.
