# DOCUMENT-CARD-METRICS — 16/11/2026

Đang đọc và áp dụng skill owner-governed-codex cho task này.

GOAL=Chữ ở ba ô số liệu trên thẻ tài liệu theo VI/EN/ZH, bỏ chữ nội bộ và
không biến trạng thái chưa có tệp thành thành công.
BASE_SHA=b3c1749fdc0876164cf9b3bedd64290fdf4d9bf4
BRANCH=codex/document-card-metrics-20261116
TRACKER=Issue #689 / checklist mẹ hiện có.
DEPENDENCY=PR747 đã giao: exact-head CI43821671694 hai nhóm SUCCESS;
merged/runtime b3c1749fdc0876164cf9b3bedd64290fdf4d9bf4;
tested/merged tree6778c61672610a493aed543db38511cbcc60b3c0;
deploy43853462350 SUCCESS; ba dịch vụ active-running, health và năm asset
HTTPS khớp; Issue receipt6910067903 / PR receipt6914555619.

## Phạm vi và thứ tự

1. Giữ kết quả R1 của Antigravity: bốn thay thế đúng phiếu, không áp dụng.
   R1 không có lỗi code. Người điều phối sửa riêng năm nhãn đếm EN để dùng
   được cả số 1, rồi giao R1A bằng phiên CLI có sẵn, Gemini3.8FlashHigh.
   Không tính phụ lục chữ này là worker retry.
2. Viết test trước khi áp app, chạy BASE để thấy lỗi chữ thực tế.
3. Nhận R1A, kiểm toàn bộ OLD/NEW, áp cơ học đúng bốn thay thế; không tự viết
   app patch, không thay condition/coercion/control hay phần vừa giao.
4. Chạy một nhóm kiểm tra cuối. Chỉ chạy lại đúng phần lỗi nếu cần.
5. Kiểm source độc lập, cập nhật tài liệu vận hành/đối chiếu gốc/phiên Tester
   rồi mới push; exact-head CI → merge → một deploy → runtime/asset receipt.

ALLOWLISTapp=static/portal/portal.js, static/portal/portal-i18n.js.
Trong portal.js chỉ `sourceMetric`, `thirdMetric`, `outputMetric` thuộc
`renderDocumentOperationCards`. Trong i18n chỉ thêm 13 key/locale,
tổng39 giá trị, ngay trước verifyEqualKeysets.

Tests mới: `tests/document-card-metrics.test.mjs`,
`tests/helpers/document-card-metrics-runtime.mjs`,
`tests/helpers/document-card-metrics-snapshot.mjs`,
`tests/fixtures/document-card-metrics-reviewed.json`.
Historical adapters chỉ thêm inverse hữu hạn của đúng bốn thay thế TRƯỚC
display inverse trong `document-card-display-runtime.mjs` và
`document-card-display-snapshot.mjs`. Giữ hash/whole-HTML/khách/quyền cũ;
không thêm broad masking hoặc nới assertion.
CI chỉ thêm một command. Docs/Tester/cases/checklist/provenance được cập nhật.

PROTECTED=All app Python/backend/auth/CSRF/DB/ENV/schema/integration/CSS/
motion/Bot/engine/provider/wallet/PayOS/production data.
Giữ chín nhánh sản phẩm, mọi condition/thứ tự/Number/Number.isInteger/
Math.max/sourceCount/sourcePages/outputPages/savedBytes/savedPercent,
vaultBytes, state/downloadPath/capability strict true, actions/DOM attrs,
tên và nội dung khách, names/selection/date vừa giao, thứ tự thẻ.
Không sửa tên hàm/chữ ký, thêm helper app hay refactor.

## Acceptance / checklist

- [x] PR747 đã giao trước BASE; Owner state chưa theo dõi được giữ nguyên.
- [x] R1 structural exact, completion0, workerCodeFailures0, NOT_APPLIED/NOT_QA.
- [x] R1A exact: ba JS chunk giống R1; chỉ năm EN value của phiếu được sửa;
  giữ 13 key/39 value/thứ tự, VI/ZH và tám EN value khác nguyên vẹn.
- [x] BASE16RED đúng chữ/catalog/hash; không import/syntax/harness.
- [x] Source, output, third cells đúng VI/EN/ZH cho chín kind, count1/many/
  zero/string/bad, input/output pages, bytes/savings, mọi trạng thái/quyền.
- [x] Không in `private` hay khẳng định “đã xác minh” từ số liệu; tên tệp khách
  có các chữ đó vẫn nguyên vẹn. Missing/guarded/failed không tạo download giả.
- [x] Một lần escape cả câu; tham số không pre-escape; hostile translations
  không tạo HTML hay double escape. Bộ dịch frozen/keyset/order, same-VM locale,
  fallback và missing/unknown key checks giữ.
- [x] Whole HTML ngoài đúng ba ô số liệu và toàn bộ dữ liệu/controls bằng BASE.
  Empty history giữ nguyên. Finite inverse khôi phục toàn bộ hai tệp BASE.
- [x] Một nhóm25tệp521NodePASS/0FAIL/0SKIP41745.4586ms, không rerun.
- [x] Source review độc lập C0/I0/M0, đúng hai frozen app hashes;
  không chạy lại test/VM/native/scope gate.
- [x] Native ba signed empty-history VI/EN/ZH375light trên QA sở hữu; không seed tệp
  hoàn tất hoặc fake API. Filled metrics chỉ nhận bằng chứng actual-renderer
  VM nếu QA hiện có không chứa output thật.
- [x] Product tables/schema/plans/scenes/source/evidence hashes giữ; Jobs0,
  không product writes/reseed/egress/provider/money.
- [x] Tài liệu hiện tại/đối chiếu gốc/Tester READY; case1417lines152989LFbytes,
  SHA7fb5f2ca92d783d8e40c5b0f8014789d638b0c4355504a4ffd242fca87e1bc82,
  metadata1PASS32deselected0.44s, historical remote/P0 metadata giữ.
- [ ] Provenance/CI/merge/deploy/
  runtime5assets/receipts đúng revision. Không đóng whole goal từ local.

TESTS=`node --test tests/document-card-metrics.test.mjs` và nhóm chain affected
Display/PDF/Card/Date/Meta/Request/History cùng một lượt cuối.
STOP=OLD không duy nhất, hash lệch, ngoài allowlist, verification lỗi hoặc
cần protected mutation.
PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_WRITES=0.
Full locale/responsive/AX/keyboard/auth/device/Safari/signed-production UI/
final output/M-FINAL01..06 vẫn mở; motion cuối.
