# BÁO CÁO NGHIỆM THU: HOÀN TẤT CÁC GAP UI/UX NỘI BỘ P5/P6 (UTILITIES, CONTENT, PROJECTS, AUTOPOST, SUPPORT, ACCOUNT)

**Tuyên bố bắt buộc**: Đang đọc và áp dụng skill `owner-governed-codex` cho task này.

- **Task**: `TASK=WEBAPP_FINAL_INTERNAL_UIUX_MOTION_AND_INTEGRATION_CLOSEOUT_R1`
- **Subphase**: `SUBPHASE=WEBAPP_P5_P6_UTILITIES_CONTENT_PROJECTS_AUTOPOST_SUPPORT_ACCOUNT_R1`
- **Product**: `TOAN_AAS_WEB_APP`
- **Target PR**: [#661](https://github.com/manhtoangreensky-wq/toan-aas-standalone/pull/661) (`webapp-r218-billing-ui-20261022`)
- **PR Status**: `OPEN`, `merged=false`, `mergeable=true`
- **Controller Authorization**: Issue #664 comment `6489060394` (`P5_P6_AUTHORIZED=YES`, `NEXT_STATE=WORKER_WEBAPP_P5_P6`, `STOP=NO`)
- **Thực thi**: Single-Agent, Minimal Code Footprint (`MINIMAL_CODE_FOOTPRINT=ON`), Anti-Overengineering (`YAGNI=ON`)
- **Chốt chặn an toàn**:
  - `BACKEND_MUTATION_COUNT=0` (Zero thay đổi backend Python)
  - `REALTIME_TRANSLATE_TOUCH=NO` (Zero can thiệp PR #674)
  - `ADMIN_A0_AUTHORIZED=NO` (Dừng lại đúng ranh giới, chưa triển khai A0 Admin khi chưa có Controller ACCEPT)
  - `MERGE=NOT_RUN`, `DEPLOY=NOT_RUN`, `RESTART=NOT_RUN`
  - `PAID_CALL_COUNT=0`, `REAL_PROVIDER_NETWORK_CALL_COUNT=0`

---

## 1. KẾT QUẢ ĐÓNG 13 GAP UI/UX NỘI BỘ P5/P6

Toàn bộ 13 hạng mục sản phẩm nội bộ thuộc nhóm P5/P6 đã được thẩm định, xây dựng bài kiểm tra hợp đồng dùng chung chuyên biệt [tests/p5-p6-shared-contracts.test.mjs](file:///D:/TOANAAS/toan-aas-standalone/tests/p5-p6-shared-contracts.test.mjs) (**14/14 PASSED**), và ánh xạ bằng chứng trực tiếp vào Master Ledger:

1. `UT-01` (`[x]`): Workspace dịch thuật đa ngôn ngữ (`/subtitle-studio/new?intent=translation`): nguồn tự nhận diện, catalog 21 ngôn ngữ đích, tìm kiếm cục bộ, giữ bản gốc, đảo chiều dịch, bắt đầu/dừng có guard, kết quả và lịch sử. *(Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/translation-workspace-controls.test.mjs` 4/4 pass, `static/portal/portal.js` `renderTranslationWorkspace`)*
2. `UT-02` (`[x]`): Creative Content Studio: 5 workflow nội dung (caption & hashtag, ý tưởng nội dung, hook & script, content pack, storyboard), form brief, Prompt Pack gợi ý, lưu vào Ghi chú, catalogue VI/EN/ZH >140 keys. *(Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/content-studio-locale-presentation.test.mjs`, `tests/content-prompt-pack-locale-presentation.test.mjs`, `static/portal/portal.js` `renderContentStudio`/`renderContentPromptPack`)*
3. `UT-03` (`[x]`): Free Prompt Library & Gallery: thư viện gợi ý có lọc/tìm kiếm, sao chép/áp dụng vào Studio, trạng thái guarded, zero số liệu ảo. *(Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/free-prompt-gallery-locale-presentation.test.mjs`, `tests/prompt-authoring-locale-presentation.test.mjs`, `static/portal/portal.js` `renderFreePromptGallery`/`renderPromptStudio`)*
4. `UT-05` (`[x]`): Notes & Memory Center: quản lý ghi chú owner-scoped, lọc tag, trạng thái nhắc việc (reminder), hộp thoại xác nhận xóa an toàn. *(Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/memory-center-locale-presentation.test.mjs`, `static/portal/portal.js` `renderMemoryNotes`/`renderMemoryReminders`)*
5. `UT-06` (`[x]`): Documents Studio: 9 workflow PDF/tài liệu (tách trang, gộp, nén lossless, OCR, chuyển đổi), liên kết Asset Vault, thứ tự tệp, trạng thái thực thi guarded, tải xuống chỉ khi hoàn tất. *(Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/documents-product-controls.test.mjs` 4/4 pass, `tests/document-utility-guard-clarity.test.mjs`, `static/portal/portal.js` `renderDocumentWorkspace`)*
6. `UT-07` (`[x]`): Asset Vault: kho tài sản owner-scoped, upload allowlist 25MB, phân loại dự án, phân trang, lưu trữ/phục hồi lifecycle. *(Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/assets-product-controls.test.mjs` 5/5 pass, `static/portal/portal.js` `renderAssetVault`/`renderAssets`)*
7. `UT-08` (`[x]`): Projects & Workboard: quản lý dự án, Workboard dọc, phân công, trạng thái, phụ thuộc, lịch trình, danh sách kiểm tra (checklist). *(Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/project-center-guard-clarity.test.mjs`, `tests/workboard-locale-presentation.test.mjs`, `static/portal/portal.js` `renderProjectCenter`/`renderWorkboardBoard`)*
8. `AP-02` (`[x]`): AutoPost Hub: luồng Web-native brand/content plan → draft/review/calendar từ 7 nguồn, ranh giới xuất bản ngoài guarded. *(Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/autopost-hub-product-controls.test.mjs` 4/4 pass, `tests/campaign-planner-locale-presentation.test.mjs`, `static/portal/portal.js` `renderAutoPostHub`/`renderCampaignPlanner`)*
9. `AC-01` (`[x]`): Account Profile & Security: hồ sơ cá nhân, ngôn ngữ giao diện (vi/en/zh), múi giờ, quản lý phiên đăng nhập, đổi mật khẩu, liên kết Telegram, danh tính OAuth, xóa sạch draft khi đăng xuất. *(Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/account-control-level-contract.test.mjs` 6/6 pass, `tests/test_account_security_center.py` 12 pass, `static/portal/portal.js` `renderAccount`/`renderAccountSecurity`)*
10. `AC-01-AVATAR-PERSISTENCE` (`[x]`): Avatar presets chuyển toàn bộ sang local SVG data URI (`avatarPresetDataUri`), loại bỏ hoàn toàn cuộc gọi ra ngoài (DiceBear), bảo toàn hợp đồng hồ sơ. *(Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/account-avatar-presets-local.test.mjs`, `static/portal/portal.js` `avatarPresetDataUri`)*
11. `AC-02` (`[x]`): Billing, Packages & Topup: số dư và lịch sử giao dịch canonical từ server, bảng giá công khai chỉ đọc, luồng nạp thủ công bắt buộc chọn method + nhập amount trước khi hiện QR, PayOS fail-closed. *(Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/account-billing-control-level-contract.test.mjs` 5/5 pass, `tests/billing-metadata-recovery.test.mjs`, `static/portal/portal.js` `renderWallet`)*
12. `SP-01` (`[x]`): Support Center: danh sách yêu cầu hỗ trợ owner-scoped, phân trang, đính kèm bằng chứng, phản hồi hai chiều, nâng cấp xử lý (escalation). *(Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/support-hub-product-controls.test.mjs` 4/4 pass, `tests/support-admin-guard-clarity.test.mjs`, `static/portal/portal.js` `renderSupportCaseCards`/`renderSupportEvidence`)*
13. `SP-02` (`[x]`): Context Help, Support Advisor & Community Trust Center: hướng dẫn theo ngữ cảnh sản phẩm, phiếu tham vấn trực tuyến, cổng thông tin cộng đồng với ranh giới kênh xác minh. *(Evidence: `tests/p5-p6-shared-contracts.test.mjs`, `tests/chat-boundary-clarity.test.mjs`, `static/portal/portal.js` `renderSupportAdvisor`/`renderSupportConsultationBrief`/`renderCommunityTrustCenter`)*

---

## 2. BẢO TOÀN NGUYÊN TRẠNG CÁC HÀNG ĐANG MỞ (ZERO PREMATURE CLOSURE)

Tuân thủ nghiêm ngặt chỉ đạo của Controller:
- **Các hàng Q0 mở**: `Q0-03` (mobile responsive 375/390/768/1440), `Q0-04` (keyboard/a11y/recovery) tiếp tục giữ `- [ ]`; `Q0-TOAST-STACK` tiếp tục giữ `- [~]` chờ bài đo runtime QA.
- **Các hàng P4 Image mở**: 4 dòng ghi chú trung gian `IM-00A..D` tiếp tục giữ `- [~]`; dòng renderer/browser/AX Image (Line 730) tiếp tục giữ `- [ ]`.
- **Hàng P2 Music mở**: Dòng renderer/browser/AX Music (Line 508) tiếp tục giữ `- [ ]`.
- **Hàng P5/P6 mở**: Dòng renderer/browser/AX (Line 800 `- [ ]`) và dòng browser smoke tổng (Line 801 `- [~]`) tiếp tục giữ mở chờ pha Motion cuối.

---

## 3. BẢNG ĐỐI SOÁT MASTER LEDGER CHÍNH THỨC (260 ROWS)

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

### Tổng hợp số hàng Master Ledger R218:
- **Tổng số hàng**: 260 hàng.
- **Hàng `[x]`**: **172 hàng** (120 ban đầu + 11 superseded + 15 obsolete + 13 F0/Q0/Image + 13 P5/P6 đóng mới).
- **Hàng `[→]` (Deferred)**: **10 hàng**.
- **Hàng mở còn lại (`[ ]` + `[~]`)**: **78 hàng** (104 gap thực tế ban đầu - 26 gap đã đóng).
- **Kiểm tra cân bằng**: `172 + 10 + 78 = 260 hàng` (Khớp 100%, `UNCLASSIFIED_MASTER_ROW_COUNT=0`).

### Phân bổ 78 hàng mở còn lại theo từng phân hệ:
1. Reconciliation parity matrix: 1 hàng
2. P1 Voice: 9 hàng
3. P2 Music: 8 hàng
4. P3 SubDub: 13 hàng
5. P4 Image: 5 hàng (`IM-00A..D` [~] + renderer [ ])
6. P5/P6 Utilities/Support: 2 hàng (renderer [ ] + browser smoke [~])
7. A0 Admin: 8 hàng
8. V0 Video & Video Tools: 16 hàng
9. Q0/M0/L0 Quality & Acceptance: 10 hàng (gồm `Q0-03`, `Q0-04`, `Q0-TOAST-STACK`)
10. Motion cuối (M-FINAL): 6 hàng
- **Tổng cộng**: `1 + 9 + 8 + 13 + 5 + 2 + 8 + 16 + 10 + 6 = 78 hàng`.

---

## 4. BẰNG CHỨNG KIỂM THỬ THỰC NGHIỆM (EMPIRICAL VERIFICATION)

| Suite kiểm thử | Số test | Kết quả | Thời gian |
|---|---|---|---|
| `node --test tests/p5-p6-shared-contracts.test.mjs` | 14 | **14 PASSED, 0 FAILED** | 0.78s |
| `node --test tests/f0-q0-shared-contracts.test.mjs` | 8 | **8 PASSED, 0 FAILED** | 0.45s |
| `node --test tests/*translation*.test.mjs tests/*content*.test.mjs ...` (P5/P6 suite) | 92 | **92 PASSED, 0 FAILED** | 2.47s |
| `node --test tests/*image*.test.mjs` (Image suite) | 71 | **71 PASSED, 0 FAILED** | 1.12s |
| `pytest tests/test_account_security_center.py` | 12 | **12 PASSED, 0 FAILED** | 0.35s |
| `pytest tests/test_portal_aura_theme_contracts.py` | 21 | **21 PASSED, 0 FAILED** | 0.65s |
| `pytest tests/test_theme_semantic_contrast_contracts.py` | 5 | **5 PASSED, 0 FAILED** | 6.55s |
| `node --check static/portal/*.js` (6 files) | 6 | **SYNTAX CLEAN** | 0.1s |
| `python -m compileall -q .` | - | **0 ERRORS** | 3.5s |
| `git diff --check` | 2 files | **0 WHITESPACE ERRORS** | 0.1s |

---

## 5. CHỐT CHẶN AN TOÀN VÀ TIẾP NỐI

- Dừng lại tại trạng thái candidate ready (`STOP=YES`).
- Không tự ý thực hiện Phase 5 (A0 Admin) cho đến khi nhận được chỉ đạo và phê duyệt chính thức từ Controller (`ADMIN_A0_AUTHORIZED=NO`).
