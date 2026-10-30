# BÁO CÁO NGHIỆM THU: HOÀN TẤT CÁC GAP UI/UX NỘI BỘ V0 PRODUCT VIDEO VÀ VIDEO TOOLS (R218-09)

**Tuyên bố bắt buộc**: Đang đọc và áp dụng skill `owner-governed-codex` cho task này.

- **Task**: `TASK=WEBAPP_FINAL_INTERNAL_UIUX_MOTION_AND_INTEGRATION_CLOSEOUT_R1`
- **Subphase**: `SUBPHASE=WEBAPP_V0_PRODUCT_VIDEO_VIDEO_TOOLS_INTERNAL_UIUX_CLOSEOUT_R1`
- **Subtask Fix**: `SUBTASK=WEBAPP_V0_AUTHORITATIVE_BOT_CATALOG_BINDING_AND_CI_GATE_R1` (Issue #664 comment ID `6515282071`)
- **Product**: `TOAN_AAS_WEB_APP`
- **Target PR**: [#661](https://github.com/manhtoangreensky-wq/toan-aas-standalone/pull/661) (`webapp-r218-billing-ui-20261022`)
- **PR Status**: `OPEN`, `merged=false`, `mergeable=true`
- **Controller Authorization**: Issue #664 comment `6505319831` (`VIDEO_V0_AUTHORIZED=YES`), Issue #664 comment `6515282071` (`VERDICT=FIX -> Bot catalog phải được checkout/read ở explicit authority SHA trong CI; thiếu Bot source phải fail chứ không skip; VI-13 phải parse trực tiếp video_ai_edit_catalog.py; VI-PROFILE-CATALOG-32 phải parse trực tiếp video_profile_catalog.py; suite V0 phải được chạy trong exact-head GitHub CI`)
- **Thực thi**: Single-Agent, Minimal Code Footprint (`MINIMAL_CODE_FOOTPRINT=ON`), Anti-Overengineering (`YAGNI=ON`)
- **Chốt chặn an toàn bất biến**:
  - `BACKEND_MUTATION_COUNT=0` (Không chỉnh sửa router/service Python backend)
  - `REALTIME_TRANSLATE_TOUCH=NO` (Không can thiệp PR #674)
  - `WALLET_MUTATIONS=0` (Không tác động logic ví tiền/nạp rút)
  - `MERGE=NOT_RUN`, `DEPLOY=NOT_RUN`, `RESTART=NOT_RUN`
  - `PAID_CALL_COUNT=0`, `REAL_PROVIDER_NETWORK_CALL_COUNT=0` (Tuyệt đối không suy diễn từ UI sang provider execution hay paid generation)

---

## 1. RÀNG BUỘC TRỰC TIẾP BOT CATALOG VÀ BỔ SUNG GATE CI CHÍNH XÁC

Đáp ứng đầy đủ 4 yêu cầu kiểm thử và bằng chứng thực nghiệm của Controller tại comment `6515282071`:

### 1.1. Tự động Checkout Bot Repository tại Explicit Authority SHA trong CI
- Trong workflow CI `.github/workflows/webapp-quality.yml`, đã tích hợp bước tải repository Bot chính thức:
  - Repository: `https://github.com/manhtoangreensky-wq/bot.git`
  - Explicit Authority SHA: `83a994aea6fb253ee9e64fcfc845d4c31aa2934d`
  - Thư mục đích: `../bot` (nằm ngoài root Web App, bảo toàn tuyệt đối tính toàn vẹn của git status và migration evidence của Web App).
- Thiết lập biến môi trường `BOT_ROOT=${{ github.workspace }}/../bot` và `BOT_AUTHORITY_SHA=83a994aea6fb253ee9e64fcfc845d4c31aa2934d` phục vụ các bài kiểm thử.

### 1.2. Chính sách Bắt Buộc Có Nguồn Bot (Fail-Closed, Zero Skip)
- Trong `tests/v0-video-shared-contracts.test.mjs`, hàm `resolveBotRoot()` kiểm tra sự tồn tại của cả hai tệp catalog:
  - `services/video_ai_edit_catalog.py`
  - `services/video_profile_catalog.py`
- Nếu không tìm thấy tệp hoặc đường dẫn Bot, kiểm thử sẽ **FAIL NGAY LẬP TỨC** (`throw new Error(...)`), tuyệt đối không bỏ qua (`skip`) hay rơi vào kịch bản suy diễn giả mạo.
- Bổ sung kiểm tra hợp đồng thẩm quyền `VI-BOT-AUTHORITY`: xác nhận đối soát commit SHA của repository Bot với `BOT_AUTHORITY_SHA`.

### 1.3. Parse Trực Tiếp `services/video_ai_edit_catalog.py` (VI-13)
- `VI-13` đọc và phân tích cú pháp trực tiếp từ mã nguồn Bot catalog:
  - Xác thực 5 categories chuẩn: `scene`, `person`, `object`, `style`, `text`.
  - Xác thực đúng 39 capabilities phân bổ chính xác: `scene`: 12, `person`: 7, `object`: 8, `style`: 8, `text`: 4.
  - Xác thực metadata đầu vào: `requires_reference_image=True` chỉ áp dụng cho `person_replace` và `person_appearance_reference`.
  - Xác thực 7 preset styles: `detail_kind="preset"`.
  - Xác thực ranh giới an toàn: `enabled_production: bool = False`, `enabled_offline: bool = True` (mặc định tắt production, fail-closed).
  - Đối soát chéo 1:1 với Web spec (`docs/superpowers/specs/2026-10-18-r218-05-09-image-video-controls.md`) và các bộ điều khiển transform trong `static/portal/portal.js`.

### 1.4. Parse Trực Tiếp `services/video_profile_catalog.py` (VI-PROFILE-CATALOG-32)
- `VI-PROFILE-CATALOG-32` đọc và phân tích cú pháp trực tiếp từ mã nguồn Bot catalog:
  - Xác thực `SCHEMA_VERSION = 2` và `MAX_LINKED_PROFILES = 2`.
  - Xác thực 3 page groups: `sales_social`, `story_knowledge_emotion`, `industry_visual`.
  - Trích xuất toàn bộ danh mục `PROFILE_SEEDS` gồm đúng 32 profiles độc nhất:
    - `sales_social`: 10 profiles.
    - `story_knowledge_emotion`: 10 profiles.
    - `industry_visual`: 12 profiles.
  - Xác thực tính độc lập và phân biệt hoàn toàn so với bộ legacy 12 profiles.
  - Đối soát chéo 1:1 danh sách 32 profiles giữa Bot catalog và Web spec.

### 1.5. Kích Hoạt Chạy Bộ Shared Contracts Trong Exact-Head GitHub Actions CI
- Trong `.github/workflows/webapp-quality.yml`, bước `Run Web App shared contract suites` chạy tự động:
  - `node --test tests/v0-video-shared-contracts.test.mjs`
  - `node --test tests/a0-admin-shared-contracts.test.mjs`
  - `node --test tests/p5-p6-shared-contracts.test.mjs`
  - `node --test tests/f0-q0-shared-contracts.test.mjs`
- Đảm bảo CI chứng thực trực tiếp logic V0 thay vì chỉ kiểm tra cú pháp tệp.

---

## 2. KẾT QUẢ ĐÓNG 13 GAP UI/UX NỘI BỘ V0 PRODUCT VIDEO & VIDEO TOOLS

1. `VI-01` (`[x]`): AI chân thật text/ảnh/scenes/brand/review: quy trình làm việc 7 bước (*input, plan, quote, confirm, progress, result, recovery*), brand review, bố cục trang riêng tư, route `/video/product` và `/video-studio/workflow`, khóa chặt execution/mutation trái phép. *(Evidence: `tests/v0-video-shared-contracts.test.mjs`, `tests/test_video_factory_workflow_portal_contracts.py`, `static/portal/portal.js` `renderVideoFactoryWorkflow`)*
2. `VI-02` (`[x]`): Trend catalog/search/reference/source/suggestions: hỗ trợ đa nền tảng (TikTok, Reels, Shorts), 5 loại context, các tập gợi ý concept và direction, route `/video-studio/idea-planner` với API giới hạn hai chiều an toàn. *(Evidence: `tests/v0-video-shared-contracts.test.mjs`, `tests/test_video_idea_planner_portal_contracts.py`, `tests/test_copyfast_video_idea_planner.py`, `static/portal/portal.js` `renderVideoIdeaPlanner`)*
3. `VI-03` (`[x]`): Script AI/tự nhập/upload và scene editor: Story Video Plan tại route `/video-studio/story-video-plan` và Script-to-Screen tại `/video-studio/script-to-screen-planner`, 5 tốc độ đọc, 8 phong cách, trường scene editor với source/profile/preservation, prompt-only không sinh dữ liệu ghi đè. *(Evidence: `tests/v0-video-shared-contracts.test.mjs`, `tests/test_story_video_plan_portal_contracts.py`, `tests/test_copyfast_story_video_plan.py`, `static/portal/portal.js` `renderStoryVideoPlan`)*
4. `VI-04` (`[x]`): Frame video source/order/cover/duration/fit/transitions/motion/audio/text: route `/video/frame-sequence`, quản lý thứ tự khung hình, 4 chế độ fit (*crop, contain, pad, stretch*), điều chỉnh thời lượng từng khung, bố cục chạm tiếp cận trợ năng và không tổng hợp output giả. *(Evidence: `tests/v0-video-shared-contracts.test.mjs`, `tests/test_frame_video_portal_contracts.py`, `tests/test_copyfast_frame_video_operations.py`, `static/portal/portal.js` `renderFrameVideoOperations`)*
5. `VI-05` (`[x]`): Selfshot đổi cảnh/điện ảnh/timeline/preservation: Cinematic Ad Concept Composer tại `/video-studio/cinematic-concept` và Self-shot Planner tại `/video-studio/self-shot-planner`, 7 phong cách concept điện ảnh, timeline/transitions/shot_direction preservation bảo vệ gương mặt và dáng chuyển động. *(Evidence: `tests/v0-video-shared-contracts.test.mjs`, `static/portal/portal.js` `renderCinematicConceptPlanSavePanel`/`renderSelfShotScenePlannerResult`)*
6. `VI-06` (`[x]`): Storyboard grid/detail/source/prompts/addons/review: route `/video/storyboard-grid` và `/video-studio/storyboard-composer`, lưới storyboard cells, chi tiết từng khung hình, định hướng prompt, hợp đồng review/quality minh bạch. *(Evidence: `tests/v0-video-shared-contracts.test.mjs`, `tests/test_story_video_plan_portal_contracts.py`, `static/portal/portal.js` `renderStoryboardComposer`/`renderStoryboardGrid`)*
7. `VI-07` (`[x]`): Series/long bible/continuity/planning và khóa execution thật: Long-Form Roadmap Planner tại `/video-studio/long-form-planner`, quản lý chương/tập/bible tính liên tục nội dung, phân lập ranh giới kế hoạch (*planning-only*), khóa thực thi `action: "none"`. *(Evidence: `tests/v0-video-shared-contracts.test.mjs`, `tests/test_long_form_video_planner_portal_contracts.py`, `tests/test_copyfast_long_form_video_planner.py`, `static/portal/portal.js` `renderLongFormRoadmapResult`)*
8. `VI-08` (`[x]`): Idea/reference/library/profile/downloader/handoff: Video Prompt Planner tại `/video-studio/prompt-planner`, danh mục kế hoạch tinh gọn, chuyển tiếp bản nháp sang Video Plan an toàn qua `data-portal-action="video-prompt-plan-save"`. *(Evidence: `tests/v0-video-shared-contracts.test.mjs`, `tests/test_video_prompt_planner_portal_contracts.py`, `tests/test_copyfast_video_prompt_planner.py`, `static/portal/portal.js` `renderVideoPromptPlanner`)*
9. `VI-09..12` (`[x]`): Manual/AI/upgrade hub, timeline/segments/transforms/layers/exports: Video Hub tại route `/tools/video` phân lập 4 lane cốt lõi (*planning, creation, editing, delivery*), 7 bước hành trình (*input, plan, quote, confirm, progress, result, recovery*), chế độ editor mode `ai` và `manual`, các thao tác transform vận hành độc lập. *(Evidence: `tests/v0-video-shared-contracts.test.mjs`, `tests/video-uiux-locale-presentation.test.mjs`, `tests/test_video_finishing_portal_contracts.py`, `static/portal/portal.js` `renderVideoHub`/`renderVideoTransformOperations`)*
10. `VI-13` (`[x]`): 39 AI edit options/5 nhóm, detail/reference/mask/preservation/readiness: 5 nhóm độc lập (*Scene, Person, Object, Style, Text*), 39 capabilities được parse trực tiếp từ Bot catalog `services/video_ai_edit_catalog.py`, trạng thái capability readiness guard bảo vệ runtime fail-closed. *(Evidence: `tests/v0-video-shared-contracts.test.mjs`, `bot:services/video_ai_edit_catalog.py`, `docs/superpowers/specs/2026-10-18-r218-05-09-image-video-controls.md`, `static/portal/portal.js` `videoTransformOperationSources`)*
11. `VI-14` (`[x]`): Upgrade chỉ hứa khả năng runtime đã chứng minh: `data-tool-state="guarded"`, không hứa hẹn tính năng chưa chứng minh như stabilization/denoise/restore khi chưa có runtime thực nghiệm, fail-closed an toàn. *(Evidence: `tests/v0-video-shared-contracts.test.mjs`, `tests/video-guide-guard-clarity.test.mjs`, `tests/test_video_finishing_portal_contracts.py`)*
12. `VI-15` (`[x]`): Addons selected/applied, quote/report/output/download/reuse: phân tách tường minh giữa tiện ích được chọn (*selected*) và đã áp dụng (*applied*), báo giá/báo cáo minh bạch, tải tệp đính kèm đã xác thực, triệt tiêu việc sinh output giả. *(Evidence: `tests/v0-video-shared-contracts.test.mjs`, `tests/test_video_finishing_portal_contracts.py`, `static/portal/portal.js` `renderVideoFinalization`)*
13. `VI-PROFILE-CATALOG-32` (`[x]`): Đủ 32 profile/3 nhóm; catalog khác bộ legacy 12: danh mục 32 profile seeds chia 3 nhóm 10/10/12 được parse trực tiếp từ Bot catalog `services/video_profile_catalog.py`, bộ chọn hỗ trợ tìm kiếm/lọc, 1 profile chính và tối đa 2 profile liên kết, khác biệt hoàn toàn so với bộ 12 legacy. *(Evidence: `tests/v0-video-shared-contracts.test.mjs`, `bot:services/video_profile_catalog.py`, `docs/superpowers/specs/2026-10-18-r218-05-09-image-video-controls.md`)*

---

## 3. BẢO TOÀN NGUYÊN TRẠNG CÁC HÀNG BROWSER MATRIX VÀ HÀNG ĐANG MỞ (ZERO PREMATURE CLOSURE)

Tuân thủ nghiêm ngặt chỉ đạo của Controller tại Issue #664:
- **Giữ mở hàng toolbar CapCut & browser**: `- [ ] Không claim CapCut parity từ toolbar; toolbar contract đã khóa (không claim CapCut, bounded tools), browser thao tác từng nhóm duy trì mở chờ Q0 matrix.` tiếp tục giữ trạng thái mở `- [ ]`. Hợp đồng toolbar không claim CapCut đã được chứng minh, nhưng vế `browser thao tác từng nhóm` phải chờ đo tại bộ QA matrix toàn diện (Q0/L0).
- **Giữ mở 2 hàng QA tổng V0**: 2 dòng ghi chú kiểm thử hồi quy/smoke (Line 937 `[~]` và Line 940 `[~]`) tiếp tục giữ nguyên `[~]` chờ nghiệm thu runtime browser tổng thể.
- **Giữ nguyên các hàng hoãn & mở của các phân hệ khác**:
  - Voice (9 hàng mở), Music (8 hàng mở), SubDub (13 hàng mở), Image (5 hàng mở), Utilities/Support (2 hàng mở), Admin A0 (4 hàng mở gồm fixture matrix Line 781 `[ ]`), Quality Q0/M0/L0 (10 hàng mở), Motion cuối M-FINAL (6 hàng mở), Reconciliation parity matrix (1 hàng mở).
  - Toàn bộ 10 hàng hoãn ngoại vi `[→]` (Deferred Owner/External) giữ nguyên trạng thái.

---

## 4. BẢNG ĐỐI SOÁT MASTER LEDGER CHÍNH THỨC (260 ROWS)

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
REAL_INTERNAL_UIUX_GAP_REMAINING_COUNT=61
UNCLASSIFIED_MASTER_ROW_COUNT=0
BACKEND_MUTATION_COUNT=0
REALTIME_TRANSLATE_TOUCH=NO
STEP1_LEDGER_RECONCILIATION=ACCEPTED
SUBPHASE_A0_ADMIN=PASS
SUBPHASE_V0_VIDEO=PASS
```

- **Hàng `[x]` (Closed)**: **189 hàng** (120 ban đầu + 11 superseded + 15 obsolete + 13 F0/Q0/Image + 13 P5/P6 + 4 A0 Admin + 13 V0 Video đóng mới).
- **Hàng `[→]` (Deferred)**: **10 hàng**.
- **Hàng mở còn lại (`[ ]` + `[~]` + `[!]`)**: **61 hàng** (104 gap thực tế ban đầu - 43 gap đã đóng: 13 F0/Q0/Image + 13 P5/P6 + 4 A0 Admin + 13 V0 Video).
- **Kiểm tra cân bằng**: `189 + 10 + 61 = 260 hàng` (Khớp 100%, `UNCLASSIFIED_MASTER_ROW_COUNT=0`).

#### Phân bổ 61 hàng mở còn lại:
1. Reconciliation parity matrix: 1 hàng (`[~]`)
2. P1 Voice: 9 hàng (`[ ]` / `[~]` / `[!]`)
3. P2 Music: 8 hàng (`[ ]` / `[~]`)
4. P3 SubDub: 13 hàng (`[ ]` / `[~]`)
5. P4 Image: 5 hàng (`IM-00A..D` [~] + renderer [ ])
6. P5/P6 Utilities/Support: 2 hàng (renderer [ ] + browser smoke [~])
7. A0 Admin: 4 hàng (Line 781 `[ ]` Customer/admin/denied fixture browser matrix + 3 QA notes `[~]`)
8. V0 Video & Video Tools: 3 hàng (Line 937 `[~]` + Line 940 `[~]` + Line 960 `[ ]` Toolbar/Browser group matrix)
9. Q0/M0/L0 Quality & Acceptance: 10 hàng (`[ ]` / `[~]`)
10. Motion cuối (M-FINAL): 6 hàng (`[ ]`)
- **Tổng cộng**: `1 + 9 + 8 + 13 + 5 + 2 + 4 + 3 + 10 + 6 = 61 hàng`.

---

## 5. BẰNG CHỨNG KIỂM THỬ THỰC NGHIỆM (EMPIRICAL VERIFICATION)

| Suite kiểm thử | Số test | Kết quả | Thời gian |
|---|---|---|---|
| `node --test tests/v0-video-shared-contracts.test.mjs` | 15 | **15 PASSED, 0 FAILED** | 0.55s |
| `node --test tests/a0-admin-shared-contracts.test.mjs` | 6 | **6 PASSED, 0 FAILED** | 0.25s |
| `node --test tests/p5-p6-shared-contracts.test.mjs` | 14 | **14 PASSED, 0 FAILED** | 0.26s |
| `node --test tests/f0-q0-shared-contracts.test.mjs` | 8 | **8 PASSED, 0 FAILED** | 0.23s |
| `node --test tests/*video*.test.mjs` (Full Video suite) | 28 | **28 PASSED, 0 FAILED** | 0.65s |
| `pytest tests/test_portal_aura_theme_contracts.py ...` | 42 | **42 PASSED, 0 FAILED** | 2.09s |
| `node --check static/portal/*.js` (6 files) | 6 | **SYNTAX CLEAN** | 0.1s |
| `python -m compileall -q .` | - | **0 ERRORS** | 3.5s |
| `git diff --check HEAD^^ HEAD` | - | **0 WHITESPACE ERRORS** | 0.1s |

---

## 6. CHỐT CHẶN AN TOÀN VÀ TIẾP NỐI

- Dừng lại tại trạng thái candidate ready (`STOP=YES`).
- Không tự ý bước sang subphase tiếp theo khi chưa có chỉ đạo chính thức từ Controller trên Issue #664 (`QUALITY_Q0_AUTHORIZED=NO`, `MOTION_AUTHORIZED=NO`).
