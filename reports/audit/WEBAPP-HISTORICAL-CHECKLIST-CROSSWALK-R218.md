# R218 — Đối soát toàn bộ lịch sử plan / checklist / spec WebApp

Ngày đối soát: 2026-10-18
Nhánh: `webapp-r217-subdub-ui-r218`
HEAD được kiểm tra: `82ee56ceaddcb9685519c5b7376dfa121240e8f8`

## Kết luận ngắn

- R217 → R218 **đã có** crosswalk file-level trong
  `reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-R218.md`: 16 tài liệu
  R217 được nối vào wave/ledger hiện hành.
- Trước lần đối soát này, lịch sử trước R217 **chưa có** một sổ đối soát riêng;
  chỉ được bao phủ ở mức nhóm B01–B34. Vì vậy không được nói rằng đã gộp tuyệt đối
  mọi checklist cũ.
- Tài liệu này bổ sung sổ lịch sử đó. Không xóa, ghi đè hoặc tự chuyển trạng thái
  bất kỳ mục cũ nào. Mỗi mục cũ được đưa vào đúng wave hiện hành hoặc `T0` (kỹ thuật
  để cuối), còn trạng thái `[ ]`, `[~]`, `[!]`, `[→]` của ledger R218 vẫn là nguồn
  quyết định hoàn tất.
- Tại snapshot này, **unclassified source = 0** ở cấp file trong bốn thư mục
  kiểm kê: `docs/superpowers/plans` (127), `docs/superpowers/specs` (180),
  `reports/audit` (44, đã bao gồm chính sổ này) và `.agents/state` (14). Đây là bằng chứng không bỏ sót
  nguồn tài liệu; chưa phải bằng chứng mọi chức năng trong từng tài liệu đã chạy thật.

## 1. Nguồn sự thật duy nhất sau đối soát

| Vai trò | Tệp | Cách dùng |
|---|---|---|
| Ledger thực thi hiện hành | `reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-R218.md` | Trạng thái đóng/mở duy nhất; không suy diễn từ tài liệu cũ |
| Plan thứ tự thi công | `docs/superpowers/plans/2026-10-18-webapp-bot-parity-uiux-replan-r218.md` | Thứ tự C0 → F0 → P1 → P2 → P3 → P4 → P5 → P6 → A0 → V0 → Q0 → M0 → L0 → T0 |
| Inventory parity | `reports/audit/WEBAPP-BOT-PRODUCT-INVENTORY-R218.md` | B01–B34 và nguồn Bot đọc-only |
| Sổ lịch sử này | `reports/audit/WEBAPP-HISTORICAL-CHECKLIST-CROSSWALK-R218.md` | Kiểm tra không có plan/checklist/spec/state bị đứng ngoài ledger |

Quy tắc: tài liệu cũ là bằng chứng và nguồn yêu cầu; không phải bằng chứng runtime.
Một dòng cũ chỉ được đánh `[x]` ở R218 khi renderer/interaction và browser/AX/runtime
đúng phạm vi đã có bằng chứng riêng.

## 2. Số đo inventory tại HEAD

Các số dưới đây được đếm trực tiếp bằng `Get-ChildItem -File`, không ước lượng:

| Nguồn | Số tệp | Phạm vi đối soát |
|---|---:|---|
| `docs/superpowers/plans` | 127 | Plan cũ, R198, R217, R218 |
| `docs/superpowers/specs` | 180 | Spec dated và contract/reference không ngày |
| `reports/audit` | 44 | Checklist, audit, inventory, truth matrix và sổ crosswalk này |
| `.agents/state` | 14 | Trạng thái WIP/evidence của các đợt trước |
| **Tổng** | **365** | Không gồm mã nguồn hay artifact runtime |

Phân lớp plan/spec (307 tệp):

| Lớp | Số tệp | Disposition |
|---|---:|---|
| 2026-07 đến 2026-09 (trước R210) | 201 | Đã phân tuyến vào F0/P1–P6/A0/V0/M0/Q0/T0 theo bảng mục 3 |
| R198 (2026-10-14) | 1 | M0/Q0, giữ lịch sử |
| R210–R216 (2026-10-15) | 8 | Đã nhận vào F0/P5/P6/V0/Q0/M0/L0 |
| R217 (2026-10-16) | 16 | Đã có crosswalk file-level trong ledger R218 |
| R218 (2026-10-18) | 14 | Đang là spec hiện hành |
| Checkpoint 2026-10-07 đến 2026-10-08 | 5 | Đã nhận vào P1/P2/P3/V0 |
| Spec contract/reference không ngày | 62 | Đã phân loại C0 hoặc T0; không bỏ qua |
| **Tổng** | **307** | `unclassified = 0` |

Các checklist có dòng checkbox cũ được giữ nguyên và nối vào ledger:

| Checklist/audit nguồn | Số dòng checkbox đo được | Nơi nhận |
|---|---:|---|
| `WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-20261010.md` | 115 | F0/P5/P6/V0/Q0/M0/L0 |
| `WEBAPP-UIUX-PARITY-MASTER-CHECKLIST-20261016.md` | 234 | C0/F0/P1–P6/A0/V0/Q0/M0/L0/T0 |
| `P0-WEB-ERP-MASTER-CHECKLIST.md` | 84 | P1/P2/P3/P4/V0/A0/AC-02/T0 |
| Các audit narrative/P0/A09 không dùng checkbox | Không áp dụng | C0/P5/P6/A0/T0 theo bảng mục 3 |

Tổng dòng checkbox cũ được truy vết: **433**. Con số này chỉ là số dòng checklist,
không phải số tính năng đã hoàn tất.

## 3. Crosswalk lịch sử → wave R218

### 3.1 Nền chung, màu, chữ, responsive, auth và motion

| Nguồn lịch sử | Wave hiện hành | Mục không được bỏ |
|---|---|---|
| `2026-07-26-teal-cyan-ui-foundation*`, `2026-07-27-teal-sky-*`, `2026-07-27-unified-teal-sky-*`, `2026-07-28-customer-workspace-shell*`, `2026-08-02-aura-*` | F0/Q0 | Token xanh dương/xanh ngọc, nền navy, type scale, tương phản, bố cục dọc, responsive |
| `2026-07-28-teal-sky-ui-motion-foundation*`, `2026-08-09-landing-motion-*`, `2026-08-12-*-motion*`, `2026-10-14-webapp-uiux-motion-replan-r198.md` | M0/Q0 | Hydration không cắt animation, transform/opacity, reduced-motion, cleanup, CLS/LCP/INP |
| `2026-07-26-dashboard-reviewed-locales*`, `2026-08-03-public-auth-*`, `2026-08-03-account-center-*`, `2026-08-04-data-controls-*`, `2026-08-08-telegram-access-*` | F0/AC-01/Q0 | VI/EN/ZH sạch, auth return path, stale private data, keyboard/focus |
| `2026-07-31-first-run-workspace-*`, `2026-07-31-onboarding-*`, `2026-07-31-workspace-menu-*`, `2026-08-14-command-palette-sidebar-i18n.md` | F0/AC-01/Q0 | Menu, first-run, command palette, mobile navigation, aria-current |

### 3.2 Voice, Music/SFX, SubDub, Image và Video

| Nguồn lịch sử | Wave hiện hành | Mục không được bỏ |
|---|---|---|
| `2026-07-28-audio-hub-*`, `2026-07-31-voice-studio-*`, `2026-10-07-voice-*`, `2026-10-08-voice-flow-state-presentation.md` | P1 | TTS/STT, mặc định nam/nữ, kho/clone, consent, preview, speed/volume, quote, reuse |
| `2026-07-31-music-sfx-*`, `2026-10-08-music-hub-ui-closeout.md` | P2 | Nhạc nền/bài hát, lyrics/vocal mode, ba tier/ba gợi ý, kho/SFX, player, delivery |
| `2026-10-08-subdub-single-screen-ui.md`, `P0-WEB-ERP-MASTER-CHECKLIST.md` phần SubDub | P3 | Bốn mode một workspace, nguồn có/chưa có phụ đề, Auto 2, Auto Multi 3–8, Smart Multi, mix, report |
| `2026-07-29-image-tools-*`, `2026-08-01-image-tools-*`, `2026-08-02-image-prompt-*`, `2026-08-09-image-*`, `2026-08-10-image-*`, `2026-08-11-image-*`, `2026-08-12-reference-first-*` | P4 | Tạo/reference/prompt, AI edit, manual edit, chữ/logo, before/after, history, handoff Video |
| `2026-10-07-video-ui-checkpoint-release.md`, `2026-08-10-subtitle-quality-readability.md`, `2026-08-13-ai-studio-explorer.md` | V0 | Product Video, 32 profile, storyboard/series/self-shot, editor AI/manual, addons, report |

### 3.3 Utilities, Content, Documents, Assets, Projects, AutoPost và Support

| Nguồn lịch sử | Wave hiện hành | Mục không được bỏ |
|---|---|---|
| `2026-07-29-content-handoff-workboard-*`, `2026-07-31-content-studio-*`, `2026-08-12-feature-catalog-locales.md`, `2026-08-13-workboard-*` | P5/P6 | Content, prompt/library, variant, CTA, workboard, project, handoff |
| `2026-08-09-translation-target-preset.md`, `2026-08-10-document-*`, `2026-08-11-document-*`, `2026-08-12-pdf-to-images-*` | P5 | Dịch text/voice/file, PDF/OCR, range, Asset Vault source, result/download gate |
| `2026-07-31-memory-prompt-*`, `2026-07-31-asset-vault-*`, `2026-07-31-project-center-*` | P5 | Ghi chú/reminder, kho tệp, private scope, quota, history, version, restore |
| `2026-08-01-archive-terminal-*`, `2026-08-01-ticket-terminal-*`, `2026-08-01-workboard-task-*` | P5/P6 | State machine, recovery, ticket/task callback, source→result lineage |
| `2026-07-27-community-trust-center-*`, `2026-07-29-support-*`, `2026-07-31-support-desk-*` | P6 | Trung tâm hỗ trợ, ticket, phản hồi, escalation, feedback |
| `2026-08-24-web-local-admin-home-access.md`, `2026-09-12-a09-admin-exhaustive-locale-audit.md` | A0/P6 | Admin/customer visibility, locale route, role/permission presentation |

### 3.4 Billing, Admin/ERP và tài liệu kỹ thuật được giữ riêng

| Nguồn lịch sử | Wave hiện hành | Ghi chú an toàn |
|---|---|---|
| Các plan/spec `2026-07-26-admin-*`, `2026-07-29-admin-*`, `2026-07-31-admin-*`, `2026-08-01-admin-*`, `2026-08-02-aura-erp-*`, `2026-08-03-admin-*` | A0; phần tài chính ghi AC-02/T0 | Chỉ làm UI/read model khi có evidence; duyệt nạp tiền, ví, PayOS và financial write không tự mở |
| `P0-SPEC00..07-*`, `P0-WEB-ERP-MASTER-CHECKLIST.md`, `WEB_APP_FULL_UIUX_FUNCTIONAL_STABILIZATION_R1.*`, `WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.*`, `A09-*` | C0/A0/P6/AC-02/T0 | Giữ truth contract, RBAC, audit, admin/customer link và safety gate; không coi narrative report là runtime PASS |
| 62 spec contract không ngày (`*_CALLBACK_CONTRACT`, `*_MAP`, `*_INVENTORY`, `KNOWN_GAPS*`, `ENV_AND_PROVIDER_MAP*`, `PAYOS_*`, `VIDEO_*`, ...) | C0/T0 theo loại | Là nguồn tham chiếu callback/authority/deferred; không bị xóa và không được biến thành UI claim |

## 4. Cổng chống bỏ sót

- [x] Tất cả tệp trong bốn thư mục đã được đếm và có disposition trong mục 2–3;
  không có file ngoài sổ (`unclassified source = 0`).
- [x] Checklist cũ không bị xóa; 433 dòng checkbox cũ vẫn truy được qua đường dẫn gốc.
- [x] R217 đã có crosswalk file-level; R218 là ledger hiện hành, không tạo ledger song song.
- [x] Những mục chưa đủ evidence vẫn giữ `[ ]`, `[~]`, `[!]` hoặc `[→]`; không chuyển
  sang `[x]` chỉ vì đã gộp tài liệu.
- [ ] Line-by-line semantic review của mọi câu mô tả trong 307 plan/spec vẫn là công
  việc thực thi theo từng wave. Khi gặp một yêu cầu không khớp bảng trên, phải thêm ID
  vào ledger R218 trước khi sửa code; không được bỏ qua hoặc tự đoán.
- [ ] Browser/AX/runtime/live evidence cho các wave còn mở vẫn chưa được suy diễn từ
  crosswalk này.

## 5. Thứ tự sau khi gộp

1. Chốt WIP đang dở và kiểm tra trạng thái CI của PR hiện hành.
2. F0/shared contract và AC-01 Account theo ledger hiện tại.
3. P1 Voice → P2 Music → P3 SubDub → P4 Image.
4. P5 utilities/content/documents/assets/projects → P6 AutoPost/Support/Account.
5. A0 Admin/internal app → V0 Product Video/Video Editor.
6. Q0 browser/AX/responsive/locale → M0 motion/performance.
7. L0 delivery/live khi có lệnh; T0 technical register sau UI/UX và motion.

Không được nhảy qua mục `[ ]`/`[~]` của wave trước để làm mục mới, trừ khi Owner đổi
thứ tự bằng lệnh rõ ràng.

## 6. Giới hạn kết luận

Crosswalk chứng minh **không bỏ sót nguồn tài liệu và có một thứ tự duy nhất**. Nó không
chứng minh mọi sản phẩm đã có backend/provider/output thật. Các claim đó vẫn cần renderer,
interaction, browser/AX, runtime và delivery evidence riêng theo checklist R218.
