# MASTER CHECKLIST: P0.WEB.ERP.PRODUCTION_COMPLETION

## VIDEO UI CHECKPOINT — 2026-10-07

**UI RELEASE:** `CLOSED_LOCKED` — giữ nguyên ba màn sản phẩm đã nghiệm thu.
Video ngoài ba màn này và motion toàn site vẫn mở bên dưới.

Owner chốt: merge checkpoint Video đang làm, sau đó ưu tiên Voice → Music →
SubDub → các tính năng khác, rồi quay lại Video còn lại sau cùng. Checkpoint
đã squash-merge vào standalone main tại `8a040d0c2af0cdcb2ebd89a27f5f2caa9beff952`.

- [x] Hub Video, Video nhanh và Video nhiều cảnh: VI/EN/ZH × sáng/tối ×
  1440×900/375×812 = 36/36 kiểm tra giao diện thật trên QA cô lập.
- [x] 10 điểm đến duy nhất; tool/input đầu tiên hiện trong viewport, form dọc,
  hướng dẫn và thiết lập thêm thao tác bằng Enter, menu đóng/mở/Escape đúng.
- [x] Không tràn ngang, drawer đóng không che nội dung, không có khung mẫu
  RTX4090/video tạo sẵn hoặc tuyên bố trừ Xu giả trên hai form.
- [x] Màu computed: chữ nhỏ nhất 4.515:1; viền input nhỏ nhất 3.399:1.
- [x] 60 ảnh QA gắn hash nguồn/ảnh; runtime của ba route 0 lỗi.
- [x] Cập nhật spec, nghiệp vụ, đối chiếu tài liệu gốc và case nguồn Tester.
- [x] Official Web contracts, PR #616 CI, squash merge và deploy đã có bằng
  chứng riêng: PR CI 389 Web contracts + 26 runtime assertions + 18 CI
  screenshots; Main CI và deploy đều thành công. Runtime SHA được đối chiếu
  với Web nginx ACTIVE trong hồ sơ đóng PR #616.
- [ ] Lỗi ViewTransition ở bước đăng nhập/điều hướng và cổng motion cuối còn mở.
- [ ] Self-shot/trend/storyboard/Video dài/motion-guide và các công cụ biên tập
  chưa thuộc checkpoint này, giữ mở để quay lại đúng điểm đang làm.
- Spec: `docs/superpowers/specs/2026-10-07-video-ui-checkpoint-release.md`.
- Hồ sơ merge/deploy: [PR #616](https://github.com/manhtoangreensky-wq/toan-aas-standalone/pull/616),
  PR CI run `37630929796`, Main CI run `37631528823`, deploy run `37632060634`.
- `PROVIDER_CALLS=0 WALLET_MUTATIONS=0 PRODUCTION_DATA_MUTATIONS=0`;
  API/engine của main được giữ nguyên, parent goal ACTIVE.

## VOICE UI RELEASE — 2026-10-08

**SPEC_ID:** `WEBAPP-VOICE-UI-CLOSEOUT-20261007` · **STATUS:** `DEPLOYED_SOURCE_VERIFIED_AUTHENTICATED_LIVE_OPEN`.

**UI SOURCE/RELEASE:** `CLOSED_LOCKED`; đã ghi trên đầu PR #617.
Không sửa lại renderer/khóa dịch/CSS sản phẩm Voice trong các checkpoint sau.
Gate kiểm tra có đăng nhập là một mục chỉ-đọc còn mở riêng.

- [x] Voice hub/forms/inventory/Studio/detail/Composer/flow-state presentation
  checkpoints reviewed; six renderer suites 110/110 pass.
- [x] Pre-release review reproduced and fixed two additional UI defects:
  resumed-draft save-new label empty in VI/EN/ZH; ambiguous `cost_xu` used as a
  price fallback. Existing action/field/server authority contracts preserved.
- [x] Update operating/source-comparison docs and VUI-01..04 case source before
  push. Existing labels and issue templates were read; Projects lacks
  `read:project`, so no automatic scope refresh or Project-write claim.
- [x] Stage only Voice hunks and publish candidate `6ef97e1` as draft
  [PR #617](https://github.com/manhtoangreensky-wq/toan-aas-standalone/pull/617).
  Local official browser gate: 18 pages, 6/6 primary keyboard checks, 4 tools;
  runtime assertions 26/26. Provenance gate passes on exact release HEAD.
- [x] Ubuntu Web CI run `37724197462` passed: 389 Web contracts, 26 runtime
  assertions and 18 browser screenshots; 6/6 primary keyboard checks.
  PR #617 squash-merged at `e405cbee28f0687f528eab7d66a71ef1623125f4`;
  merge tree matches tested candidate exactly. Windows suite completed
  387 passed/2 failed before case metadata was corrected (target retest now
  passed); the unchanged POSIX assertion passed in Ubuntu CI.
- [x] Main CI `37724519640` SUCCESS; deploy `37724809429` SUCCESS; runtime
  SHA `e405cbee28f0687f528eab7d66a71ef1623125f4`; tracked diff 0 and Web/nginx
  active. Three production assets match immutable Git blobs exactly.
- [x] Anonymous production entry at 1440×900/375×900 redirects to login with
  visible auth form; no overflow, page error or POST. Evidence:
  `../../qa/20261007-video-uiux/voice-production-e405cbe/readback.json`.
- [ ] Authenticated production Voice presentation remains open; QA logged-in
  results do not replace this gate. No claim of real audio, job or delivery.
- [x] Voice code release closed; Music/SubDub changes remain separate.
- [ ] Shared shell locale, floating controls and whole-site motion remain open.

## MUSIC HUB UI — 2026-10-08

**SPEC_ID:** `MUSIC-HUB-UI-CLOSEOUT-20261008` · **STATUS:** Music UI đã được
kiểm chứng cục bộ; chưa commit/push/merge/deploy. SubDub cũng đã qua QA cục bộ.
Thứ tự tiếp: Music → SubDub → các tính năng khác → quay
lại phần Video còn lại → motion toàn site.

- [ ] Close Music release on `fix/music-ui-closeout-20261008`, BASE
  `e405cbee28f0687f528eab7d66a71ef1623125f4`; exact-candidate renderer/browser/
  Web CI, one PR and separate deploy/source readback.
- [ ] Music CI primary-link selection must follow its real first creation card;
  preserve every Voice selector and all fail-closed focus/visibility assertions.

- [x] Đối chiếu ảnh và ma trận nền `/music`: 12/12 locale × sáng/tối ×
  1440×900/375×812; chưa thấy tràn ngang hoặc lỗi runtime của route.
- [x] Ghi defect đã xác nhận: lẫn ngôn ngữ, số liệu/chất lượng/bản quyền không
  có nguồn, lựa chọn sáng tác nằm sâu, nhóm lối tắt lặp lại danh mục.
- [x] Bản địa hóa toàn bộ chữ cố định của trang Music VI/EN/ZH; không để Anh–Việt trộn trong
  cùng giao diện.
- [x] Đưa ba lối sáng tác hiện có lên trước, giữ trạng thái chưa khả dụng đúng
  sự thật; thư viện/tệp âm thanh đang dùng được đặt sau.
- [x] Bỏ thẻ trùng và mọi tuyên bố “Stereo 320k”, “Royalty-Free”, chuẩn phòng
  thu hoặc bản quyền thương mại chưa có căn cứ; chỉ giữ số đếm đích đến duy
  nhất nếu tính từ route thực.
- [x] Rà lại màn hình 375×812 và 1440×900 ở hai giao diện sáng/tối; màu xanh–teal,
  12/12 trường hợp, không tràn ngang/lỗi route, sáu đường dẫn đúng; tương phản
  chữ tối thiểu 4.635:1 sáng / 4.812:1 tối.
- [x] Không gửi form sáng tác, không tạo nhạc/âm thanh, không gọi provider,
  không sửa route/engine/ví; QA chỉ kiểm tra phần trình bày.
- [ ] Sửa locale dùng chung: ảnh EN/ZH vẫn thấy tiếng Việt ở thanh điều hướng/
  thanh công cụ; đây là lỗi shared shell, chưa nằm trong Music slice.
- [ ] Rà vị trí nút nổi trợ lý/cài ứng dụng và cảnh báo ViewTransition trong
  checkpoint shared shell/motion; không tự vá bằng CSS cục bộ của Music.
- [ ] Ghi nhận QA nền: 23 Python contract đạt; một bài cũ
  `test_library_routes_do_not_fall_back_to_generic_assets_or_audio_execution`
  lỗi vì đòi nhánh `/assets` legacy. `integration.js` và file test trùng hệt
  `origin/main`, nên không tính là hồi quy; chưa sửa test ngoài phạm vi.
- Bằng chứng ảnh/JSON: `../../qa/20261007-video-uiux/music-hub-ui-closeout-20261008/`.
- Spec: `docs/superpowers/specs/2026-10-08-music-hub-ui-closeout.md`.
- Baseline: `../../qa/20261007-video-uiux/music-hub-audit-20261008/` (12/12).
- `PROVIDER_CALLS=0 WALLET_MUTATIONS=0 PRODUCTION_DATA_MUTATIONS=0`.

---

**Hệ sinh thái:** TOAN AAS Web App & Admin ERP  
**Runtime Target:** tg.toanaas.vn (/opt/toanaas/webapp)  
**Historical ERP baseline SHA (not current runtime verification):** 03325cf577de4fd090abea9088c8980a6a028e29
**Tiêu chuẩn vận hành:** owner-governed-codex & locked-focus-engineering  
**Quy tắc:** Làm tuần tự từng SPEC, không làm PR khổng lồ, soi lại checklist này mỗi khi bắt đầu và kết thúc một SPEC mới.

---

## BẢNG BẢO VỆ KHỐI LƯỢNG ĐÃ ĐẠT (CANONICAL PROTECTED WORK)

> [!IMPORTANT]
> Tuyệt đối KHÔNG tái cấu trúc (refactor/rewrite) các khối sau nếu không có bằng chứng lỗi ĐỎ (RED evidence) mới:
> 1. PR #437 Admin IA consolidation (Cấu trúc 7 nhóm, 10 primary navigation links, 38 secondary tabs).
> 2. Portal shell scroll ownership (.portal-workspace sở hữu cuộn chính, .portal-sidebar độc lập, không desync).
> 3. Semantic Light/Dark token architecture (portal-theme.css, Obsidian palette, không dùng màu ngọc lam đục).
> 4. Phân định biên giới xác thực 3 tầng RBAC (support_staff, web_local_admin, canonical_admin).
> 5. Chốt chặn an toàn bất biến ví tiền: Web App không mutate ví trực tiếp (WALLET_MUTATIONS=0).
> 6. Robustness Clean Envelope HTTP 200 của Reliability (trả về trạng thái availability có cấu trúc, không sập 503).

---

## NGUYÊN TẮC BẤT BIẾN TOÀN CỤC (GLOBAL INVARIANTS)

1. ZERO != UNKNOWN: Số 0 là dữ liệu đo được; chưa có dữ liệu phải hiển thị '-' hoặc 'Không khả dụng'.
2. HTTP 200 != business success: Phản hồi 200 với phong bì rỗng/lỗi upstream không được coi là hoàn thành.
3. EMPTY != ERROR: Dữ liệu sạch 0 bản ghi khác hoàn toàn với lỗi truy vấn hay sập kết nối.
4. DEPLOYED != LIVE_PROVEN: Code đã deploy lên VPS chưa đồng nghĩa là đã chứng minh chạy sống qua E2E.
5. UI visibility != server authorization: Nút bấm nhìn thấy trên giao diện không có nghĩa là server đã cấp quyền.
6. Web App must not become wallet authority: Web App chỉ là Read-Only / Draft initiator; Bot Core là thẩm quyền ví tối cao.
7. No production fake KPI: Tuyệt đối không dùng số liệu giả mạo trên dashboard quản trị.
8. No demo fallback presented as production data: Không hiển thị dữ liệu demo giả làm dữ liệu vận hành thật.
9. No cross-database synchronization without explicit authority map: Cấm sync DB khi chưa chốt thẩm quyền (SPEC-01).
10. Historical routes must remain compatible: 100% routes cũ phải có redirect hoặc canonical subview tương ứng.
11. Every write must have auth + validation + audit + idempotency: Mọi hành động ghi phải có kiểm tra quyền, validate, ghi nhật ký và chống trùng lặp.
12. No ENV/security/DB/wallet mutation without required Owner gate: Cấm tự ý can thiệp các chốt chặn an toàn của Owner.

---

## MA TRẬN TIẾN ĐỘ 19 SPECS (MASTER CHECKLIST)

| SPEC ID | Tên SPEC | Giai đoạn | Mục tiêu cốt lõi | Trạng thái |
|---|---|---|---|:---:|
| **SPEC-00** | Canonical Truth & Acceptance Contracts | PHASE A | Khóa sự thật, sửa báo cáo LIVE=NO/PARTIAL, chuẩn hóa ma trận hợp đồng 54 functions | 🟢 COMPLETED |
| **SPEC-01** | Data Authority & Cross-System Boundary | PHASE A | Thiết lập bản đồ thẩm quyền cho 36 thực thể, khóa 4 corrections thẩm quyền | 🟢 PASS_WITH_CONTRACT_CORRECTIONS |
| **SPEC-02** | ERP Dashboard Truth | PHASE B | Dashboard chỉ lấy số liệu thật, xóa tỷ lệ %, xử lý UNKNOWN/UNAVAILABLE | 🟢 COMPLETED |
| **SPEC-03** | Monitoring & Reliability Truth | PHASE B | Telemetry sống, tách bạch HTTP 200 with data unavailable khỏi trạng thái xanh | 🟢 COMPLETED |
| **SPEC-04** | Customer / CRM / Support | PHASE B | Hợp nhất 1 nguồn chân lý khách hàng, xóa overlap lead, đồng bộ ticket | 🟢 COMPLETED |
| **SPEC-05** | Operations / Jobs / Handoffs | PHASE B | Đồng nhất ngôn ngữ vận hành, job lỗi có runbook ngữ cảnh, hàng đợi chuẩn | 🟢 COMPLETED |
| **SPEC-06** | Finance Read Model | PHASE B | Read model từ nguồn chân lý, nêu rõ phạm vi Doanh thu (WEB_ONLY, BOT_ONLY) | 🟢 COMPLETED |
| **SPEC-07** | Topup / Payment Write Safety | PHASE C | Chứng minh biên giới ghi nạp tiền: CSRF, Idempotency, Audit, không mutate ví | 🟢 COMPLETED |
| **SPEC-08** | Security / Password / RBAC | PHASE C | Xác nhận mật khẩu hiện tại khi đổi pass, vòng đời session, khóa quyền server | ⚪ PENDING |
| **SPEC-09** | Audit / Reports | PHASE C | Khai thác bộ lọc backend đã có (Date range, actor, pagination) lên giao diện UI | ⚪ PENDING |
| **SPEC-10** | Remove Fake / Placeholder Operational Data | PHASE D | Xóa sạch số liệu hardcoded tại /admin/finance/planning, /admin/growth, /admin/trends | ⚪ PENDING |
| **SPEC-11** | Content / Growth / Planning Completion | PHASE D | Gán đúng nhãn cho từng module: WORKING, READ_ONLY_REFERENCE, EMPTY_VALID, NOT_AVAILABLE | ⚪ PENDING |
| **SPEC-12** | API Error-State Semantics | PHASE D | Phân tách 7 trạng thái phản hồi API: Success data, empty, unavailable, 403, validation, upstream, 500 | ⚪ PENDING |
| **SPEC-13** | UI Density / Page Simplification | PHASE E | Tối ưu mật độ thông tin, dọn bớt chữ giới thiệu thừa, tăng giá trị nghiệp vụ trên màn hình | ⚪ PENDING |
| **SPEC-14** | Responsive / Accessibility / Real Browser E2E | PHASE E | Kiểm thử trình duyệt thật trên 5 viewports (1920, 1440, 1280, 768, 375 mobile) | ⚪ PENDING |
| **SPEC-15** | Cross-System Projection / Sync | PHASE F | Kiến trúc projection dữ liệu 1 chiều có kiểm soát từ Bot Core về Web ERP | ⚪ PENDING |
| **SPEC-16** | Observability / Auditability | PHASE F | Tương quan request_id, actor, domain, action, chống lộ bí mật và PII | ⚪ PENDING |
| **SPEC-17** | Production Live Acceptance | PHASE G | Nghiệm thu từng domain trên môi trường production thực tế | ⚪ PENDING |
| **SPEC-18** | Dead Code / Consolidation Cleanup | PHASE H | Dọn dẹp code rác, route cũ không dùng sau khi toàn bộ hành vi đã xanh | ⚪ PENDING |

---

## BẢNG CHỐT CHẶN AN TOÀN BẮT BUỘC CỦA OWNER (OWNER GATES)

- [ ] **GATE-A**: Thay đổi ENV TOANAAS_OPS_AUTOPILOT_ENABLED (Cần lệnh duyệt rõ ràng từ Owner).
- [ ] **GATE-B**: Bất kỳ kiến trúc đồng bộ dữ liệu Web ↔ Bot nào có quyền ghi (Cần Owner phê duyệt thiết kế).
- [ ] **GATE-C**: Bất kỳ migration schema nào hoặc sửa đổi DB production (Cấm tự ý thực hiện).
- [ ] **GATE-D**: Bất kỳ can thiệp nào vào logic thanh toán hoặc quyết toán ví tiền (Bất biến).
- [ ] **GATE-E**: Bất kỳ thay đổi nào đối với chính sách phân quyền RBAC/Security (Cần Owner duyệt).
- [ ] **GATE-F**: Bất kỳ thao tác dọn dẹp dữ liệu (purge demo) có tính phá hủy (Cấm tự ý chạy).
- [ ] **GATE-G**: Bất kỳ tích hợp nhà cung cấp hoặc secret/API key mới nào (Cần Owner cung cấp).
- [ ] **GATE-H**: Deploy/restart dịch vụ khi chưa có yêu cầu mã nguồn bắt buộc.
