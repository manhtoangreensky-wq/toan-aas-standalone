# R218 — Kế hoạch UI/UX toàn bộ sản phẩm WebApp theo Bot

Ngày 2026-10-18. Trạng thái WIP_SP01_SUPPORT_CONTROL_PUSHED_CI_UNKNOWN; chưa mở wave runtime.
Phạm vi bao gồm toàn bộ nhóm sản phẩm; SubDub là một nhóm trong kế hoạch.

## Bộ tài liệu

- Inventory: reports/audit/WEBAPP-BOT-PRODUCT-INVENTORY-R218.md (B01–B34).
- Checklist: reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-R218.md.
- R218-00/01: specs/2026-10-18-r218-00-control-contract.md.
- R218-02/03: specs/2026-10-18-r218-02-03-voice-music-controls.md.
- R218-04: specs/2026-10-18-r218-subdub-bot-parity-uiux.md.
- R218-05/09: specs/2026-10-18-r218-05-09-image-video-controls.md.
- R218-06/07/08: specs/2026-10-18-r218-06-08-utilities-admin-controls.md.
- R218-06B: specs/2026-10-18-r218-06b-utilities-qr-avatar-rate-weather-download.md.
- R218-06D: specs/2026-10-18-r218-06d-assets-product-controls.md.
- R218-06A: specs/2026-10-18-r218-06a-translation-workspace-controls.md.
- R218-07B: specs/2026-10-18-r218-07b-support-center-controls.md.
- R218-07C: specs/2026-10-18-r218-07c-account-controls.md.
- R218-10/11/12/13: specs/2026-10-18-r218-10-13-qa-motion-delivery-technical.md.
- State: .agents/state/WEBAPP-BOT-PARITY-R218.yaml.
- R217 preservation crosswalk: checklist R217 và các spec `2026-10-16-r217-*`
  được giữ làm comparator; mapping file-level sang wave R218 nằm ở phần
  “Đối soát file/spec R217 → R218” trong checklist hiện hành.

Đường dẫn specs ở trên tương đối docs/superpowers/. Mỗi nhóm spec gộp chỉ để
đọc gọn; từng phiếu thực thi và tiêu chí đóng vẫn có ID riêng.

## 1. Thứ tự bắt buộc

1. Lập và đối soát plan/checklist/spec toàn bộ sản phẩm từ menu và handler Bot.
2. Bảo toàn và chốt phần đang dở: PR #653 auth responsive/contrast; PR #654 là
   ứng viên UI SubDub cần review/CI. Không gọi thẻ disabled là tính năng hoàn tất.
3. Theo checklist mới: nền chung → Voice → Music → SubDub → Image → tiện ích,
   tài liệu/công việc → AutoPost/Support/Account → Admin trình bày → Video.
4. Product Video và các công cụ video làm cuối các wave sản phẩm.
5. Motion/hiệu năng làm cuối. Khi UI/UX và motion đủ bằng chứng, báo cáo rồi đợi
   lệnh cho backend/bridge; không tự chuyển sang các phần kỹ thuật.

## 2. Nguồn sự thật và phạm vi

- Bot đọc-only tại `D:/TOANAAS/bot telegram`; root menu
  `bot.py:72195 localized_main_menu_keyboard`.
- Hash bot.py: `7eae9610073d3000c2a949e78e2e48e0194eb402eedea7f9b9328fa09d7f0b0f`.
- Ref local đọc được: `fix/p0-subdub-smart-synth-adapter-signature-r1`.
  Bot commit và production runtime chưa xác minh trong lượt audit này.
- Menu → callback/handler → catalog → capability → output evidence là các lớp
  riêng. Tài liệu thiết kế V2 không tự chứng minh V2 đã chạy.
- Giữ stack WebApp, palette xanh dương/xanh ngọc, tối navy/chữ sáng; sáng/chữ tối.
- Không sửa Bot/route-engine/provider/wallet/PayOS/secret hoặc production data.

## 3. Gọn nhưng đủ chi tiết

Một workspace/sản phẩm, nhiều chế độ trên cùng trang. Các tùy chọn liên quan xuất
hiện theo mode; phần nâng cao có disclosure rõ ràng. Không nhân mỗi nút Bot thành
một route Web, không xóa tính năng để giảm số ô.

Mỗi control có ID, nguồn Bot, Web renderer/route, VI/EN/ZH, vị trí, input/default,
điều kiện enabled, action, next/back, loading/empty/error/stale, test và screenshot.
Chi tiết tại `2026-10-18-r218-00-control-contract.md`.

Cấu hình local có thể chỉnh khi engine chưa mở nếu không sinh tác vụ. Nút thực thi
dựa vào capability máy chủ; không hardcode khóa toàn bộ form. Giọng mặc định không
phụ thuộc việc đã có giọng cá nhân trong thư viện.

## 4. Wave / spec / điều kiện đóng

| Wave | Spec | Nội dung | Điều kiện đóng |
|---|---|---|---|
| C0 | R218-00 | WIP #653/#654, nguồn Bot, inventory, mapping controls | Checkpoint đủ; không mất việc cũ |
| F0 | R218-01 | Shell/type/color/spacing/upload/result/states chung | Browser locale/theme/mobile/keyboard đạt |
| P1 | R218-02 | Voice TTS/STT/default/saved/clone/preview/reuse | Đủ control, consent/state/return flow |
| P2 | R218-03 | Music nền/bài hát/kho/SFX/chỉnh nhạc | Đủ gợi ý/vocal/tier/result; gap editor/2 bản ghi riêng |
| P3 | R218-04 | SubDub 4 mode + mọi policy giọng/ngôn ngữ/mixing/report | Đủ Auto 2, Auto Multi 3–8, Smart Multi riêng |
| P4 | R218-05 | Ảnh AI/reference/prompt/AI edit/manual edit | Đủ mục tiêu/style/ratio/biến thể/local tools |
| P5 | R218-06 | Dịch/Content/Free/Memory/Docs/Assets/Projects | Mỗi menu root và submenu có disposition |
| P6 | R218-07 | AutoPost/Brand/Channels/Calendar/Affiliate/Support/Account | Luồng đầy đủ, nối sản phẩm và trạng thái thật |
| A0 | R218-08 | Admin presentation/role matrix/task/report | Bảng dọc, chi tiết, fixture quyền và references đạt |
| V0 | R218-09 | Video các lane/32 profile/AI edit/manual/upgrade | Đủ catalog và từng control, không claim CapCut |
| Q0 | R218-10 | Tổng UI/UX/locale/a11y/responsive | Evidence từng requirement; không chỉ số route/test |
| M0 | R218-11 | Motion/auth/render lifecycle/perceived performance | Không cut/restart motion; trace/reduced-motion đạt |
| L0 | R218-12 | Delivery/live khi được phép | SHA đúng + thao tác/DOM/screenshot phù hợp |
| T0 | R218-13 | Technical register | Chỉ plan, đợi lệnh sau UI/motion |

### Checkpoint UT-01 — 18/10/2026

Đã lát control-level cho `/subtitle-studio/new?intent=translation&pair=...`:
workspace dọc có nguồn tự nhận diện, 21 ngôn ngữ đích, tìm kiếm cục bộ, giữ
bản gốc, dịch hai chiều, trạng thái bắt đầu/dừng, kết quả và lịch sử. Panel
không phải form và không thêm API action; capability server chưa công bố nên
execution vẫn `guarded`. Test riêng 4/4 và full Node 549/549 đạt. UT-01 vẫn
`[~]`; backend/quote/job/output/browser/live giữ ở wave kỹ thuật.

### Checkpoint UT-04 — 18/10/2026

Workspace `/free-tools` đã mở rộng từ 6 lên 10 tab/panel: QR hiện có, Ảnh đại
diện AI, Tỷ giá & quy đổi Xu, Thời tiết và Tải video & media. Bốn lane mới có
form dọc, quyền/nguồn dữ liệu, empty result và nút thực thi guarded; không gọi
API ngoài, không tạo ảnh, không lấy số liệu, không tải tệp. Test focused 5/5 và
full Node 549/549 đạt. UT-04 vẫn `[~]`; runtime nguồn thật, browser/AX và
delivery giữ ở wave QA/technical.

## 5. Bố cục cụ thể

- App H1 32–40px, mobile 28–32px; H2 24px; body 16px/line-height 1.5.
- Label 14–16px; spacing 8/12/16/24/32px; card padding 24px desktop/16px mobile.
- Control tối thiểu 44px; focus rõ; chọn/disabled/error không chỉ dùng màu.
- Desktop preview/source và cấu hình chia vùng; DOM order theo thứ tự thao tác.
  Mobile một cột: nguồn → mode → thiết lập → review → kết quả.
- VI sạch tiếng Việt ngoài tên riêng; EN sạch tiếng Anh; ZH tương ứng.
  Bot dùng tham chiếu tính năng, không chép các chuỗi Bot còn pha ngôn ngữ.
- Một CTA chính; hành động phụ theo nhóm. Chỉ mở download khi file thực sự sẵn sàng.

## Checkpoint UT-06 — Documents/PDF control-level

Đã khóa lớp trình bày của Tài liệu/PDF bằng spec
`2026-10-18-r218-06c-documents-product-controls.md` và test
`tests/documents-product-controls.test.mjs`. Bảng tài liệu giữ một nơi, nhóm PDF cơ
bản/chuyển đổi/OCR, form nguồn theo Asset Vault, thứ tự nhiều tệp, page range, lựa chọn
tối ưu, xác nhận và lịch sử kết quả. Chưa đánh dấu runtime: capability, bytes/preview,
quote/job/output/delivery, browser/AX và LIVE vẫn chờ các wave kỹ thuật/QA.

## Checkpoint UT-07 — Assets control-level

Đã khóa lớp trình bày của Asset Vault bằng spec
`2026-10-18-r218-06d-assets-product-controls.md` và test
`tests/assets-product-controls.test.mjs`. Workspace giữ upload private có allowlist/25 MB,
gắn Project, lọc active/archived/all, phân trang, tải chỉ bản ghi active, lifecycle redaction
và archive/restore theo revision. Test riêng đạt `5/5`; full Node đạt `558/558`. Đây chỉ là
control-level evidence; upload bytes thật, preview, capability server, browser/AX, delivery
và LIVE vẫn mở. Sau checkpoint này tiếp tục AP/Support/Account theo checklist, không nhảy
sang motion.

## Checkpoint R218-07A — AutoPost Hub control-level

Đã khóa một workspace `/publishing` theo trình tự nguồn → thương hiệu/kế hoạch → kênh →
lịch/hàng đợi → báo cáo/lịch sử. Bảy nguồn Bot được trình bày riêng: chủ đề/ý tưởng, URL,
Affiliate, tệp đa phương tiện, video TOAN AAS, ảnh TOAN AAS và ý tưởng từ kế hoạch. Channel
Strategy, Content Calendar và gói rà soát trước khi đăng được nối bằng handoff Web-native;
OAuth, publish, queue, affiliate metrics và delivery vẫn `guarded` vì chưa có capability
server hợp lệ. Fixed chrome đã cân bằng VI/EN/ZH, desktop/tablet/mobile giữ bố cục dọc.

Spec và test: `docs/superpowers/specs/2026-10-18-r218-07-autopost-hub-controls.md`,
`tests/autopost-hub-product-controls.test.mjs`. Đây là control-level evidence cho AP-01..05,
không phải bằng chứng kênh đã kết nối hoặc bài đăng đã giao. Local verify hiện tại: AutoPost
`4/4`, full Node `562/562`, hai lệnh `node --check` và `git diff --check` đạt; browser/AX,
CI và LIVE vẫn chưa được suy diễn.

## Checkpoint R218-07B — Trung tâm hỗ trợ khách hàng control-level

Đã khóa lát trình bày và contract cho `/support`, `/tickets`, `/tickets/:id`,
`/admin/support` và `/admin/support/:id`: tiếp nhận, danh sách/lọc/phân trang, chi tiết/
dòng thời gian, phản hồi công khai/nội bộ, trạng thái/khôi phục, phản hồi kết quả và
liên kết bằng chứng từ Asset Vault. Bố cục giữ một workspace dọc, màu xanh/ngọc và
chuyển lưới case thành một cột ở `<=620px`; bản Việt dùng “Trung tâm hỗ trợ khách hàng”.
Không upload bytes thô, không tạo ticket Bot, provider, wallet, payment hoặc thông báo ngoài Web.

Spec và test: `docs/superpowers/specs/2026-10-18-r218-07b-support-center-controls.md`,
`tests/support-hub-product-controls.test.mjs`. Local verify: Support `4/4`, full Node
`566/566`, cả hai lệnh `node --check` và `git diff --check` đạt. Đây mới là
control-level evidence; capability server, browser/AX, CI, delivery và LIVE vẫn mở.

## 6. Phiếu thực thi cho từng spec

1. Inventory controls: menu/callback/handler, từng mục chưa rõ ghi OPEN.
2. Wireframe và bảng nút/field/states, exact files được phép sửa và protected files.
3. Lát UI nhỏ có thể review độc lập; không refactor luồng đã khóa.
4. Test hành vi meaningful: chọn/back/hydration/reload/error; không chỉ regex tồn tại.
5. Browser QA: VI/EN/ZH × light/dark × 375/390/768/1440; shell mở rộng
   320/414/1024. Screenshot + AX, contrast/type/touch/overflow measurements.
6. Cập nhật checklist/evidence/tài liệu; push đúng candidate và đọc CI HEAD mới.

Một Builder RUNNING tại một thời điểm. Phiếu không tham chiếu mơ hồ hội thoại.
Không bỏ assertion hoặc thêm field ẩn chỉ để test xanh.

## 7. Điều kiện không được suy diễn

- Music editor Bot hiện guard; parser nhiều track không chứng minh giao 2 bản.
- Video AI edit catalog có 39 khả năng nhưng production mặc định disabled.
- Video long/multiscene có planning UI; public execution có thể locked.
- Profile video 32 loại là metadata kế hoạch, không phải 32 engine.
- SubDub 4-lane V2 shared-master docs là DESIGN; cần đối chiếu V1 đang hoạt động.
- Candidate #654 bảy thẻ disabled, map rỗng và volume controls không chứng minh
  kết nối giọng hoặc kết quả thật; vẫn OPEN cho review/browser.

## 8. Motion cuối và technical register

Motion dùng transform/opacity, micro 150–300ms; kiểm hydration không cắt animation,
route cleanup/observer/RAF/timer, reduced-motion, skeleton không gây shift.
Đo CLS <0.10, LCP ≤2.5s, INP ≤200ms khi có trace hợp lệ; không bịa số.

DTO/capability/Voice Library projection, upload/quote/job bridge, xử lý provider,
artifact, quyền server, OAuth/publish, wallet/PayOS nằm R218-13. Không triển khai
các mục này trong wave UI; khi hết UI/UX/motion báo cáo và đợi lệnh.
