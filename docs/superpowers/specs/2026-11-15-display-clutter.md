# DISPLAY-CLUTTER — 15/11/2026

Đang đọc và áp dụng skill owner-governed-codex cho task này.

GOAL=Bỏ đúng bốn phần hiển thị giải thích nội bộ không giúp khách thao tác; giữ nguyên lời báo tải/lỗi, nút thử lại và toàn bộ công cụ.
BASE_SHA=206eccc2eabe546ac11be89c26423eb9bf58df81
BRANCH=codex/display-clutter-20261115
TRACKER=Issue689/checklist mẹ
DEPENDENCY=PR744 đã giao: exactHEAD CI43713208147 cả hai nhóm đạt;
merge/tested tree66c3e0b9ba2e8655b23c99e51536681397a115b4;
deploy43732595353 đạt, runtime/source/services/health/fiveassets khớp.

## Phạm vi khóa

Áp nguyên văn ba proposal Antigravity đã trả, không viết lại mã ứng dụng:

1. `document-read-meta-clutter-public-nov15-r1/root-ready-proposal.json`:
   hai thay thế, chỉ bỏ hai `div.portal-state-meta` trong trạng thái tải và lỗi
   lịch sử tài liệu. Giữ nguyên hai đoạn `p/uiText` và `${retry}`.
2. `catalog-route-notice-public-nov15-r1/root-ready-proposal.json`:
   chỉ thân hàm `renderRouteEngineBoundary(context)` trả chuỗi rỗng.
3. `catalog-family-audit-public-nov15-r1/root-ready-proposal.json`:
   chỉ thân hàm `renderCapabilityHubFamilySummary(context, familyKey)` trả chuỗi rỗng.

Tổng bốn thay thế trong `static/portal/portal.js`, không khóa dịch mới.
Hai hàm hiển thị không đổi tên/chữ ký/callsite; không tạo khung rỗng.
Đây không phải sửa/xóa/bật route-engine hoặc chứng minh kết nối Bot.

Test mới dự kiến:
`tests/display-clutter.test.mjs`,
`tests/helpers/display-clutter-runtime.mjs`,
`tests/helpers/display-clutter-snapshot.mjs`,
`tests/fixtures/display-clutter-reviewed.json`.
Các adapter/expectation cũ đã đọc và được phép sửa đúng phạm vi:
`tests/helpers/document-pdf-ui-snapshot.mjs` gọi inverse bốn đoạn trước PDF;
`tests/helpers/document-pdf-ui-runtime.mjs` áp cùng inverse hữu hạn cho input
của suite PDF lịch sử, còn suite DISPLAY mới chạy nguyên nguồn thực tế;
`tests/test_feature_catalog_locale_contracts.py` và
`tests/test_route_engine_deferred_portal_contracts.py` đổi riêng kỳ vọng DOM
của notice thành chuỗi rỗng. Giữ mọi assertion descriptor/normalizer, keyset,
không dữ liệu giá/tiền, quyền và callsites. Không sửa app Python.
chỉ inverse hữu hạn bốn đoạn trước chuỗi projection cũ, giữ nguyên hash,
whole-HTML assertion, control/role/customer-content assertion.
CI chỉ thêm một targeted command vào bước kiểm tra hiện có.
Docs/Tester/current-operation/original-comparison/cases/checklist/provenance
được cập nhật đúng bằng chứng trước push.

PROTECTED_FILES=Mọi app Python, i18n, CSS, integration, auth/CSRF, DB/schema,
ENV, Bot, engine/provider, ví/PayOS/thanh toán, dữ liệu production, motion.
PROTECTED_BEHAVIOR=normalizeRouteEngineDescriptor; capabilityHubFamily;
registeredFeatureFamilyEntries/customerCatalog; manifest/canonical routes;
điều kiện quyền strict; thẻ/nút/đường dẫn; retry; loading/error paragraphs;
normalizers/DTO/counts; ghi chú, nội dung và tên tệp khách.

## Checklist / acceptance

- [x] Chốt PR744 delivery trước khi bind BASE; local tracked-clean, giữ state Owner.
- [x] Root đọc ba proposal và hàm/caller hiện tại; cả bốn OLD phải unique1 khi replay.
- [x] Root đọc test/runtime/inverse/fixture; app chưa đổi khi chạy BASE.
- [x] BASE RED bằng renderer thật: 10 FAIL đúng các phần dư/source còn cũ,
  không lỗi import/syntax/harness. R2 làm rõ normalized component-context
  thay vì bootstrap DTO; đây là điều chỉnh phiếu/test, không lỗi Antigravity.
- [x] Áp nguyên văn bốn thay thế; inverse khôi phục nguyên BASE, ngoài phạm vi exact.
- [x] Một nhóm22tệp490NodePASS;22PythonPASS,khôngchạylạinhómđãđạt.
- [x] VI/EN/ZH, loading/failed/ready, retry/quyền, catalog/family và no-empty-wrapper
  có bằng chứng; native chỉ dùng localhost cô lập/dữ liệu có sẵn, không giả kết quả.
- [x] ReviewđộclậpC0/I0/M0;23protectedLF/outside/nativebindingexit0;
  tài liệu vận hành/đối chiếu gốc/Tester đủ,case1377lines149616LFbytes;
  metadata1PASS32deselected0.98s;PUSH_GATE=READY.
- [ ] Provenance + exact-head CI, merge/tree, exclusive deploy, runtime/assets/receipt.

TESTS=`node --test tests/display-clutter.test.mjs` cùng đúng comparators bị ảnh hưởng;
BASE phải RED đúng lỗi hiển thị, candidate phải exit0/FAIL0.
Không đổi expected hash cũ, không bỏ assertion hoặc mask unknown/outside change.
Native không seed/delete/filter dữ liệu, không tạo tác vụ xử lý hay gọi provider.
Mọi bảng/rows/schema/plans/scenes/versions/idempotency/source/evidence phải giữ nguyên.
Cleanup chỉ owned child handles/Job; không dừng server khác.

Native R1 dừng đúng cổng, không có observation: root đã dùng nhầm điều kiện
hydration toàn bundle cho `/features`, trong khi route thực dùng
`portal-features.js` nhẹ và chỉ GET catalog+auth/me. Đây là lỗi harness của
người điều phối, không lỗi ứng dụng/Antigravity. Nguồn và dữ liệu giữ nguyên,
owned Job0; không coi R1 là PASS. R2 chỉ sửa điều kiện chờ theo chủ sở hữu thật:
`/features` kiểm `data-portal-features-state=ready`; family dùng bundle chính.
Nhánh `/features` nhẹ vốn không vẽ hai khối bị bỏ, nên chỉ là canh hồi quy
không thay đổi. Bằng chứng thay đổi trực tiếp thuộc family thật và Document VM.
Không mở rộng bản sửa sang `portal-features.js` hoặc giả route/request.
R2/R3 dừng trước nhận observation do harness kỳ vọng alias `/voice/tts`,
trong khi `copyfast_registry.py:151` công bố `/voice/create`. Mẫu an toàn
R3 chứng minh catalog ready,135cards,notice0/audit0/overflow0; không tính PASS.
R4 sửa đúng link kỳ vọng sang route registry thật, không đổi ứng dụng.
R4 đã quan sát catalogue VI nhưng dừng ở expectation aside-visible sai:
CSS BASE `portal.css:8887` vốn ẩn toàn `.portal-status-grid`. R5 chỉ kiểm
aside/ba metrics còn trong DOM và ghi trạng thái visible thực, không ép hiện
hay đổi CSS. Không gọi phần audit vốn bị ẩn là thay đổi trực quan mới.

PROHIBITED_ACTIONS=ENV/credential/security changes, product-provider calls,
wallet/payment mutations, production-data writes, Bot/engine implementation,
giả trạng thái thành công, ẩn lỗi thật/quyền/nút cần thiết, refactor/motion.
STOP_CONDITIONS=OLD không unique, source ngoài allowlist đổi, evidence/binding lệch,
kiểm thử không đạt hoặc phải sửa phần bị khóa.

## Thứ tự kế tiếp, không làm lẫn trong đơn vị này

PDF readability đã đo hai mẫu riêng, chưa là nghiệm thu tương phản/AX;
giao CSS riêng sau tính toán và chốt phạm vi.
Tên tài liệu dự phòng, mô tả thao tác/metrics/ngày, catalogue-hub prose và
locale/AX/auth/device/Safari/signed production/final output còn mở.
Motion M-FINAL01..06 vẫn làm cuối. Goal không thu nhỏ theo bản đang sửa.

PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_WRITES=0.
