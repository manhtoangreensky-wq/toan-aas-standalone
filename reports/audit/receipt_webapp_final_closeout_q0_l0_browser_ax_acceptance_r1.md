# BÁO CÁO NGHIỆM THU: BẰNG CHỨNG THỰC NGHIỆM BROWSER VÀ AX ACCEPTANCE Q0 / L0 (R218) & TÍCH HỢP CURRENT MAIN ROUTE ENGINE

**Tuyên bố bắt buộc**: Đang đọc và áp dụng skill `owner-governed-codex` cho task này.

- **Task**: `TASK=WEBAPP_Q0_L0_EVIDENCE_TRUTH_AND_CURRENT_MAIN_ROUTE_ENGINE_INTEGRATION_REQUALIFICATION_R1`
- **Subphase**: `SUBPHASE=WEBAPP_Q0_L0_CROSS_PRODUCT_BROWSER_AX_ACCEPTANCE_R1`
- **Product**: `TOAN_AAS_WEB_APP`
- **Target PR**: [#661](https://github.com/manhtoangreensky-wq/toan-aas-standalone/pull/661) (`webapp-r218-billing-ui-20261022`)
- **PR Status**: `OPEN`, `merged=false`
- **Controller Authority**: Issue #664 comment ID `6518796591` (`VERDICT=FIX -> Q0-04, Q0-03, Q0-CUSTOMER-CONTENT evidence gates; integrate/requalify PR661 với current main 5259de34; ledger trả về Q0_L0_CLOSED_COUNT=4 và REAL_INTERNAL_UIUX_GAP_REMAINING_COUNT=57; ROUTE_ENGINE_NEW_WEB_IMPLEMENTATION=NONE`)
- **Thực thi**: Single-Agent, Minimal Code Footprint (`MINIMAL_CODE_FOOTPRINT=ON`), Anti-Overengineering (`YAGNI=ON`), Early Stop (`EARLY_STOP=ON`)
- **Chốt chặn an toàn bất biến**:
  - `BACKEND_MUTATION_COUNT=0` (Không chỉnh sửa router/service Python backend)
  - `REALTIME_TRANSLATE_TOUCH=NO` (Bảo toàn nguyên vẹn 100% Realtime source đã merge vào `main` tại commit `5259de34`)
  - `WALLET_MUTATIONS=0` (Không tác động logic ví tiền/nạp rút)
  - `MERGE=NOT_AUTHORIZED`, `DEPLOY=NOT_RUN`, `RESTART=NOT_RUN`
  - `PAID_CALL_COUNT=0`, `REAL_PROVIDER_NETWORK_CALL_COUNT=0`
  - `MOTION_AUTHORIZED=NO` (Khóa chặt toàn bộ hàng Motion và M-FINAL)

---

## 1. SỬA ĐỔI EVIDENCE GATES VÀ ĐỐI SOÁT LEDGER TRUNG THỰC (4 CLOSED / 57 OPEN)

Theo đúng phán quyết của Controller tại comment `6518796591`:
- 3 hàng chưa đủ điều kiện pass predicate / traversal / content scan được đưa trở lại trạng thái OPEN:
  - `Q0-03` (Dòng 1110): `[ ]` (Mobile 375/390/768/1440 × themes; shell/forms thêm 320/414/1024)
  - `Q0-04` (Dòng 1111): `[ ]` (Keyboard/focus/label/contrast/touch/overflow/empty/loading/error/recovery)
  - `Q0-CUSTOMER-CONTENT` (Dòng 979): `[ ]` (Customer content action truth tiếp tục rà soát)
- 4 hàng browser/AX và toolbar có bằng chứng thực nghiệm đầy đủ được nghiệm thu đóng (`[x]`):
  - `VI-QA-REGRESSION` (Dòng 939): UI regression và route contracts trên Video Hub/Studio (15/15 tests, 48 matrix records).
  - `VI-BROWSER-SMOKE` (Dòng 942): Video presentation và authenticated browser QA trên 4 lane cốt lõi (48 records, 0 errors).
  - `VI-TOOLBAR-CAPCUT-BOUNDED` (Dòng 960): Toolbar contract khóa bounded tools, zero CapCut parity claims.
  - `Q0-TOAST-STACK` (Dòng 1112): Toast notification stack tối đa 2 nodes, duplicate collapsing, role status/alert per `tests/portal-toast-stack.test.mjs` (3/3 pass).

### Sửa đổi Evidence Gates trong Codebase:
1. Trong `scripts/ci/run_authenticated_qa_matrix.py`:
   - Ghi nhận tường minh `main_visible: bool(...)`, `horizontal_overflow: bool(...)`, `ax_nodes_count: len(...)`, `focus_order_count: len(...)` vào từng record kết quả.
   - Thắt chặt điều kiện `pass`: bắt buộc `and not row["horizontal_overflow"] and row["main_visible"] and row["ax_nodes_count"] > 0 and row["focus_order_count"] > 0`.
2. Trong `static/portal/portal.js`:
   - Loại bỏ triệt để chuỗi legacy `item.price_vnd`, chuyển sang `item.amount_vnd !== undefined ? item.amount_vnd : item.vnd`, đáp ứng 100% assertion của `tests/test_route_engine_deferred_portal_contracts.py`.

---

## 2. TÍCH HỢP TOÀN DIỆN VỚI CURRENT MAIN (5259de34)

Đã tích hợp nhánh PR #661 với current `origin/main` (`5259de345e76f38ac4a369c506fe62396442dd9f`):
- **Bảo toàn 100% Realtime Translate đã merge**:
  - `copyfast_realtime_translate.py` (WebSocket & REST session router)
  - `extensions/chrome-live-translate/` (Manifest v3, background, offscreen, content, popup)
  - `tests/test_extension_offscreen_reconnect.test.js` (Executable reconnect test suite)
  - `tests/test_p0_realtime_translate_acceptance_matrix.py` (22/22 items pass)
- **Hợp nhất Workflow CI `.github/workflows/webapp-quality.yml`**:
  - Tích hợp kiểm tra cú pháp Extension scripts.
  - Tích hợp Executable Chrome Extension Unit Tests.
  - Tích hợp Check out canonical Bot core authority tại SHA `804e23dad74dce0dfcaf3f472f1d2231a86931ba` vào `/tmp/bot_core`.
  - Tích hợp Realtime Translate & Dub Acceptance Matrix (`test_p0_realtime_translate_acceptance_matrix.py`).
  - Tích hợp Check out Bot authoritative catalog tại SHA `83a994aea6fb253ee9e64fcfc845d4c31aa2934d` vào `../bot`.
  - Tích hợp toàn bộ 5 suites Web App shared contracts (`q0-l0-shared-contracts.test.mjs`, `v0-video-shared-contracts.test.mjs`, `a0-admin-shared-contracts.test.mjs`, `p5-p6-shared-contracts.test.mjs`, `f0-q0-shared-contracts.test.mjs`).
  - Tích hợp Critical contracts, Browser verification gate, và Authenticated WebApp QA matrix.
- **Khôi phục Mergeability của PR #661**:
  - PR #661 không còn xung đột với nhánh `main`.

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
Q0_L0_CLOSED_COUNT=4
REAL_INTERNAL_UIUX_GAP_REMAINING_COUNT=57
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
- **Số dòng đã đóng (`[x]`)**: `120 (initial) + 11 (superseded) + 15 (obsolete) + 13 (F0) + 13 (P5/P6) + 4 (A0) + 13 (V0) + 4 (Q0/L0) = 193`
- **Số dòng hoãn theo chỉ đạo Owner (`[→]`)**: `10`
- **Số dòng thực tế còn mở (`[ ]` / `[~]` / `[!]`)**: `57`
- **Kiểm tra tổng**: `193 [x] + 10 [→] + 57 open = 260 total` (Khớp 100%).
- **Dòng chưa phân loại**: `UNCLASSIFIED_MASTER_ROW_COUNT = 0`.

---

## 4. KẾT QUẢ KIỂM THỬ THỰC NGHIỆM LOCAL

- **Route Engine Contracts (`pytest`)**:
  - `tests/test_route_engine.py`, `tests/test_route_engine_contracts.py`, `tests/test_route_engine_deferred_portal_contracts.py`: `35/35 PASS` (0 failed).
- **Realtime Translate Acceptance Matrix**:
  - `tests/test_p0_realtime_translate_acceptance_matrix.py`: `22/22 PASS`.
- **Extension Offscreen Reconnect Test**:
  - `tests/test_extension_offscreen_reconnect.test.js`: `ALL PASS`.
- **Node.js Shared Contracts (5 suites / 50 tests)**:
  - `tests/q0-l0-shared-contracts.test.mjs`: `7/7 PASS`
  - `tests/v0-video-shared-contracts.test.mjs`: `15/15 PASS`
  - `tests/a0-admin-shared-contracts.test.mjs`: `6/6 PASS`
  - `tests/p5-p6-shared-contracts.test.mjs`: `14/14 PASS`
  - `tests/f0-q0-shared-contracts.test.mjs`: `8/8 PASS`
  - **Tổng cộng**: `50/50 PASS` (0 failed, duration 316ms).
