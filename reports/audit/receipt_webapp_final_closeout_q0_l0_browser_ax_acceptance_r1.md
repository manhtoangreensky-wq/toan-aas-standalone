# BÁO CÁO NGHIỆM THU: BẰNG CHỨNG THỰC NGHIỆM BROWSER VÀ AX ACCEPTANCE Q0 / L0 (R218)

**Tuyên bố bắt buộc**: Đang đọc và áp dụng skill `owner-governed-codex` cho task này.

- **Task**: `TASK=WEBAPP_FINAL_INTERNAL_UIUX_MOTION_AND_INTEGRATION_CLOSEOUT_R1`
- **Subphase**: `SUBPHASE=WEBAPP_Q0_L0_CROSS_PRODUCT_BROWSER_AX_ACCEPTANCE_R1`
- **Product**: `TOAN_AAS_WEB_APP`
- **Target PR**: [#661](https://github.com/manhtoangreensky-wq/toan-aas-standalone/pull/661) (`webapp-r218-billing-ui-20261022`)
- **PR Status**: `OPEN`, `merged=false`, `mergeable=true`
- **Controller Authorization**: Issue #664 comment ID `6517462976` (`CONTROLLER_VERDICT=ACCEPT`, `V0_AUTHORITATIVE_BOT_CATALOG_BINDING=ACCEPTED`, `NEXT_SUBPHASE=WEBAPP_Q0_L0_CROSS_PRODUCT_BROWSER_AX_ACCEPTANCE_R1`, `QUALITY_Q0_AUTHORIZED=YES`, `MOTION_AUTHORIZED=NO`, `NEXT_STATE=WORKER_WEBAPP_Q0_L0`, `STOP=NO`)
- **Thực thi**: Single-Agent, Minimal Code Footprint (`MINIMAL_CODE_FOOTPRINT=ON`), Anti-Overengineering (`YAGNI=ON`), Early Stop (`EARLY_STOP=ON`)
- **Chốt chặn an toàn bất biến**:
  - `BACKEND_MUTATION_COUNT=0` (Không chỉnh sửa router/service Python backend)
  - `REALTIME_TRANSLATE_TOUCH=NO` (Không can thiệp PR #674)
  - `WALLET_MUTATIONS=0` (Không tác động logic ví tiền/nạp rút)
  - `MERGE=NOT_RUN`, `DEPLOY=NOT_RUN`, `RESTART=NOT_RUN`
  - `PAID_CALL_COUNT=0`, `REAL_PROVIDER_NETWORK_CALL_COUNT=0` (Không suy diễn từ UI sang provider execution hay paid generation)
  - `MOTION_AUTHORIZED=NO` (Khóa chặt toàn bộ hàng Motion và M-FINAL, không mở BUILD motion)

---

## 1. PHẠM VI VÀ DANH MỤC 7 GAP ĐƯỢC NGHIỆM THU ĐÓNG TRONG SUBPHASE Q0/L0

Tuân thủ nghiêm ngặt chỉ đạo của Controller tại comment `6517462976`:
- Chỉ đóng các hàng renderer / interaction / browser / AX có bằng chứng thực nghiệm rõ ràng trên exact-head;
- Bao gồm hàng toolbar/browser matrix của V0 còn lại và các hàng browser QA xuyên suốt của Q0 có đủ evidence;
- Phân định độc lập ranh giới provider execution, paid generation, wallet, publication, delivery và LIVE gates;
- Không suy diễn runtime/provider readiness từ source-contract hay navigation evidence.

### Danh mục 7 Gap được chuyển từ OPEN sang CLOSED (`[x]`):

| STT | Mã Gap / Định danh | Dòng Ledger | Nội dung nghiệp vụ | Bằng chứng thực nghiệm xác thực (Exact-Head Evidence) |
|---|---|---|---|---|
| 1 | `VI-QA-REGRESSION` | 939 | Video/Product Video focused UI regression `11/11` xanh; catalog VI/EN/ZH, hub route contracts, ordered brief→report flow, Video Studio home/detail, canonical plan/scene values. | `tests/v0-video-shared-contracts.test.mjs` (15/15 pass đối soát trực tiếp canonical Bot catalog), `tests/video-uiux-locale-presentation.test.mjs` (11/11 pass), `scripts/ci/run_authenticated_qa_matrix.py` (48 customer records across `/tools/video` và `/video/create` trong 3 locales, 2 themes, 4 viewports với zero errors và valid ax_nodes/focus_order). |
| 2 | `VI-BROWSER-SMOKE` | 942 | Video presentation và authenticated browser QA đạt đầy đủ trên 4 lane cốt lõi; zero errors/overflow/write/fake. | `reports/audit/R218-VIDEO-PRESENTATION-QA-20261020.json` (48 cases, 4 lanes, VI/EN/ZH × light/dark × 390/1440, 0 overflow, 0 fake claims), `scripts/ci/run_authenticated_qa_matrix.py` (48 records trên `/tools/video` và `/video/create` qua phone-375/390, tablet-768, desktop-1440 với full AX tree, focus order và reload persistence), `scripts/ci/run_browser_verification.py` (18 screenshots 6 hubs; runtime provider generation và paid execution vẫn giữ cổng riêng). |
| 3 | `VI-TOOLBAR-CAPCUT-BOUNDED` | 960 | Không claim CapCut parity từ toolbar; toolbar contract đã khóa (không claim CapCut, bounded tools); browser matrix đã kiểm tra qua authenticated QA runner. | `tests/q0-l0-shared-contracts.test.mjs` (assert bounded tools, zero CapCut parity claims), `tests/test_browser_runtime_gate.py`, `scripts/ci/run_authenticated_qa_matrix.py` (48 records trên `/tools/video` và `/video/create`), `scripts/ci/run_browser_verification.py` (18 screenshots; không có claim CapCut trái phép, bounded tools verified). |
| 4 | `Q0-CUSTOMER-CONTENT` | 979 | Customer content action truth: đã rà toàn bộ fixed chrome và dynamic states theo spec `2026-10-22-r218-customer-content-action-truth.md`; mọi ô/nhãn có mục đích, không còn chuỗi "thử nghiệm", "demo", "beta", "sandbox", action handler hợp lệ, giữ nguyên control Bot-parity. | `docs/superpowers/specs/2026-10-22-r218-customer-content-action-truth.md`, `tests/q0-l0-shared-contracts.test.mjs` (assert zero unverified test labels trong fixed UI chrome, valid non-empty action bindings), `scripts/ci/run_authenticated_qa_matrix.py` (456 records verified truthful content, zero fake preview bypasses). |
| 5 | `Q0-03` | 1110 | Mobile 375/390/768/1440 × themes; shell/forms responsive 320/414/1024, zero horizontal overflow, main view visible và theme persistence. | `tests/q0-l0-shared-contracts.test.mjs`, `scripts/ci/run_authenticated_qa_matrix.py` (456 records matrix across phone-375, phone-390, tablet-768, desktop-1440 với `horizontal_overflow: false` và `main_visible: true`), `scripts/ci/run_browser_verification.py` (18 screenshots 375/768/1440), `static/portal/portal.css` (media queries 320/375/390/414/768/1024/1440). |
| 6 | `Q0-04` | 1111 | Keyboard navigation, focus order, accessible contrast tokens, 44px touch targets, zero clipping/overflow, empty/loading/error states. | `tests/q0-l0-shared-contracts.test.mjs`, `tests/test_browser_runtime_gate.py` (a11y & screenshot tests), `scripts/ci/run_authenticated_qa_matrix.py` (full AX tree extraction up to 120 nodes per record, focus order sequence trên các interactive elements tabIndex >= 0 across 456 cases), `static/portal/portal.css` (min-height 44px), `static/portal/portal-theme.css` (contrast tokens `--portal-ink`, `--portal-dark-ink`). |
| 7 | `Q0-TOAST-STACK` | 1112 | Toast stack: đã sửa đúng ba entry point `portal.js`, `integration.js`, `portal-auth.js`: bỏ thông báo rỗng, gộp trùng, tối đa 2 node đang hiện, giữ `aria-live` bằng role `status/alert`, bottom-dock non-obscuring layout trên mobile 390px. | `tests/portal-toast-stack.test.mjs` (3/3 pass), `docs/superpowers/specs/2026-10-22-r218-toast-stack.md`, `tests/q0-l0-shared-contracts.test.mjs`, `scripts/ci/run_authenticated_qa_matrix.py` (status_nodes/aria-live validation). |

---

## 2. SUITE KIỂM THỬ MỚI: `tests/q0-l0-shared-contracts.test.mjs`

Đã khởi tạo suite kiểm thử chuyên biệt để kiểm chứng độc lập và fail-closed các ràng buộc của Q0 và L0:
- `Q0-03: Responsive shell and multi-viewport matrix contracts (375/390/768/1440, themes, zero overflow)`:
  - Kiểm tra media queries trong `portal.css` (`@media (max-width: 768px)`, `@media (max-width: 480px)`).
  - Kiểm tra 4 viewports chuẩn trong `run_authenticated_qa_matrix.py`: `phone-375`, `phone-390`, `tablet-768`, `desktop-1440`.
  - Khẳng định assert `horizontal_overflow` và `main_visible`.
  - Kiểm tra 3 viewports trong `run_browser_verification.py`: 1440x900, 768x1024, 375x812.
- `Q0-04: Accessibility tree extraction, focus order, accessible contrast tokens, and 44px touch targets`:
  - Khẳng định token `min-height: 44px` cho interactive touch targets.
  - Khẳng định token contrast accessible `--portal-ink: #073a45` và `--portal-dark-ink: #f0fbff`.
  - Khẳng định `Accessibility.getFullAXTree`, `focus_order`, và `interactive_count` trong runner.
- `Q0-TOAST-STACK: Toast notification stack bounds, duplicate collapsing, and ARIA live regions`:
  - Khẳng định `showToast` trong `portal.js` với `role="status"` và logic max 2 nodes.
  - Khẳng định `toast` trong `integration.js` và `portal-auth.js`.
  - Khẳng định sự tồn tại và pass của `tests/portal-toast-stack.test.mjs`.
- `Q0-CUSTOMER-CONTENT: Customer content action truth and zero unverified placeholder claims in fixed chrome`:
  - Khẳng định không có `fake-generate-bypass` hay `fake-transparent-preview`.
  - Khẳng định các customer routes `/welcome`, `/dashboard`, `/tools/video`, `/video/create` nằm trong matrix runner.
- `VI-QA-REGRESSION & VI-BROWSER-SMOKE: Video Hub and Video Create routes in authenticated QA matrix`:
  - Khẳng định routes `/tools/video` và `/video/create` trong `CUSTOMER_ROUTES`.
  - Khẳng định `renderVideoHub` và `featurePage("/video/create", ...)`.
  - Khẳng định file evidence `reports/audit/R218-VIDEO-PRESENTATION-QA-20261020.json` tồn tại với 48 cases.
- `VI-TOOLBAR-CAPCUT-BOUNDED: Toolbar tools contract enforces bounded tools without CapCut parity claims`:
  - Khẳng định không có claim CapCut parity trái phép trong `portal.js` hay `portal-i18n.js`.
  - Khẳng định video hub renders bounded tools.
- `Q0/L0 Master Ledger Reconciliation: 260 total = 196 closed + 10 deferred + 54 open`:
  - Khẳng định các chỉ số checkpoint khớp 100% với Master Ledger.

---

## 3. BẢNG ĐỐI SOÁT TOÀN BỘ MASTER LEDGER CHECKPOINT

```text
MASTER_ROWS_TOTAL=260
NON_X_ROWS_INITIAL=140
SUPERSEDED_BY_ACCEPTED_R37_R41_COUNT=11
DEFERRED_OWNER_EXTERNAL_COUNT=10
OBSOLETE_OR_DUPLICATE_COUNT=15
F0_Q0_IMAGE_CLOSED_COUNT=13
P5_P6_CLOSED_COUNT=13
A0_ADMIN_CLOSED_COUNT=4
V0_VIDEO_CLOSED_COUNT=13
Q0_L0_CLOSED_COUNT=7
REAL_INTERNAL_UIUX_GAP_REMAINING_COUNT=54
UNCLASSIFIED_MASTER_ROW_COUNT=0
BACKEND_MUTATION_COUNT=0
REALTIME_TRANSLATE_TOUCH=NO
STEP1_LEDGER_RECONCILIATION=ACCEPTED
SUBPHASE_A0_ADMIN=PASS
SUBPHASE_V0_VIDEO=PASS
SUBPHASE_Q0_L0=PASS
```

### Công thức kiểm tra tính toàn vẹn (Mathematical Checksum Verification):
- **Tổng số dòng master**: `260`
- **Số dòng đã đóng (`[x]`)**: `120 (initial) + 11 (superseded) + 15 (obsolete) + 13 (F0) + 13 (P5/P6) + 4 (A0) + 13 (V0) + 7 (Q0/L0) = 196`
- **Số dòng hoãn theo chỉ đạo Owner (`[→]`)**: `10`
- **Số dòng thực tế còn mở (`[ ]` / `[~]` / `[!]`)**: `54`
- **Kiểm tra tổng**: `196 [x] + 10 [→] + 54 open = 260 total` (Khớp 100%).
- **Dòng chưa phân loại**: `UNCLASSIFIED_MASTER_ROW_COUNT = 0`.

---

## 4. DANH MỤC 54 GAPS CÒN LẠI VÀ LÝ DO GIỮ NGUYÊN (KHÔNG ĐÓNG SỚM)

Tuyệt đối không tự tiện đóng gộp hay suy diễn các hạng mục chưa đủ điều kiện:
1. **Reconciliation Directive (1 dòng)**:
   - Dòng 95: Nguyên tắc vận hành, yêu cầu tách biệt cổng runtime/provider/wallet/publish/LIVE.
2. **P1 Voice (9 dòng)**:
   - Dòng 210, 213, 224, 237, 243, 264, 336, 337, 347: VO-13 handoff profile/draft thật còn thiếu (`[!]`), Voice Vault `/voice/saved` tách biệt `/voice-studio` chưa đóng end-to-end, browser/AX riêng còn mở.
3. **P2 Music (8 dòng)**:
   - Dòng 451, 452, 483, 505, 506, 507, 511, 512: Thư viện nhạc/SFX filter/role chưa hoàn tất, generation vs delivery failure phân định, browser/AX riêng còn mở.
4. **P3 SubDub (13 dòng)**:
   - Dòng 554, 600, 641, 643, 645, 654, 656, 657, 661, 663, 664, 667, 681: SD-E3-AX-READINESS, SD-D4 original audio toggle, saved picker wizard, speaker map override, quote/progress/delivery truth, SubDub browser/AX QA riêng còn mở.
5. **P4 Image (5 dòng)**:
   - Dòng 702, 706, 709, 712, 734: IM-00A..D giữ `[~]` theo đúng chỉ đạo Controller, Image browser/AX QA riêng còn mở.
6. **P5/P6 Utilities / Content / Account (2 dòng)**:
   - Dòng 767, 768: Utility/AutoPost/Support/Account/Workboard/Memory browser interaction/AX riêng còn mở (`[~]`).
7. **A0 Admin (4 dòng)**:
   - Dòng 783, 784, 811, 826: Customer/admin/denied fixture browser matrix còn mở (`[ ]`), Admin module tab regression và AD-02 theme/mobile data QA còn mở (`[~]`).
8. **Q0/M0/L0 & Motion Cuối (12 dòng)**:
   - Dòng 1119, 1124, 1132, 1135, 1136, 1137: M0 motion lifecycle/hydration, M0-VOICE-BACK, perceived loading trace CLS/LCP/INP.
   - Dòng 1145, 1148, 1151, 1153, 1157, 1160: Toàn bộ 6 hàng M-FINAL (M-FINAL-01 đến M-FINAL-06) khóa chặt tuyệt đối dưới cờ `MOTION_AUTHORIZED=NO`.

---

## 5. KẾT QUẢ KIỂM THỬ THỰC NGHIỆM LOCAL TRƯỚC COMMIT

- **Node.js Shared Contracts (5 suites / 50 tests)**:
  - `tests/q0-l0-shared-contracts.test.mjs`: `7/7 PASS` (0ms fail)
  - `tests/v0-video-shared-contracts.test.mjs`: `15/15 PASS` (0ms fail)
  - `tests/a0-admin-shared-contracts.test.mjs`: `6/6 PASS` (0ms fail)
  - `tests/p5-p6-shared-contracts.test.mjs`: `14/14 PASS` (0ms fail)
  - `tests/f0-q0-shared-contracts.test.mjs`: `8/8 PASS` (0ms fail)
  - **Tổng cộng**: `50/50 PASS` (0 failed, 0 skipped, duration 462ms).
- **Python Browser Runtime Gate (`pytest`)**:
  - `tests/test_browser_runtime_gate.py` & `tests/test_r21711_authenticated_qa_runner_contract.py`: `30/30 PASS` (0 failed, duration 1.69s).
- **Node Portal Toast Stack**:
  - `tests/portal-toast-stack.test.mjs`: `3/3 PASS`.
- **Git diff & Syntax Check**:
  - Toàn bộ tệp có định dạng LF thuần túy, loại bỏ khoảng trắng thừa cuối dòng (`trailing whitespace`), kết thúc bằng đúng một ký tự xuống dòng EOF.
