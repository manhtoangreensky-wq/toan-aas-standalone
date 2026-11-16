# Số liệu trên thẻ tài liệu — 16/11/2026

TASK=DOCUMENT-CARD-METRICS-20261116, local verification complete; release pending.
BASE_SHA=b3c1749fdc0876164cf9b3bedd64290fdf4d9bf4
BRANCH=codex/document-card-metrics-20261116
TRACKER=Issue #689, contract comment6914616496.

## Thay đổi đúng phạm vi

Antigravity Gemini3.8FlashHigh bằng phiên CLI hiện có trả bốn thay thế:
ba phần chữ số liệu trong renderer thẻ tài liệu và một khối thêm13 key
VI/EN/ZH, tổng39 giá trị. Không đăng nhập mới hoặc thay cài đặt.
R1 đã đúng phiếu; R1A chỉ bổ sung năm cách đếm EN do người điều phối làm rõ,
không phải worker code retry. Cả hai không có lỗi code worker.
Proposal R1A SHA256:
`53d7b9e2654e82c37d0dac08829325f7341df49224b839a32d6daea0cef3b354`.

Số trang/tệp/ảnh được trình bày theo ngôn ngữ hiện tại, không còn chữ
`private` hoặc khẳng định “đã xác minh” trong ba ô số liệu này.
Không dịch/xóa các chữ đó khi thuộc tên tệp/nội dung thật của khách.
Thiếu tệp vẫn báo chưa có; quyền tải và trạng thái không được sửa.
Giữ toàn bộ condition/coercion/count/bytes/savings/downloadPath/strict
capabilities, tên/biểu tượng/lựa chọn/ngày của PR747 và mọi actions/DOM attrs.

Chỉ hai tệp app thay đổi:

- `static/portal/portal.js` LF SHA256
  `027499a7e7ee821b9306d77ec30f2a847817fde83afd127d3d88041192498d00`.
- `static/portal/portal-i18n.js` LF SHA256
  `e2443981bd87f6ef0673b07b129977746a3a6f0d4c895bc64904004839d66968`.

## Bằng chứng local

- BASE actual-renderer16 lỗi đúng chữ/catalog/hash chưa áp;
  không import/syntax/harness error,1708.1065ms.
- Một nhóm25 tệp: **521 Node PASS /0 FAIL /0 SKIP**,41745.4586ms.
  Không chạy lại nhóm đã đạt.
- Actual full bundle: chín kind, ba locale, completed/processing/guarded/
  failed/unavailable, strict true/false/string/undefined capabilities,
  download_ready strict, source/output count1/many/zero/string/bad/fraction/
  negative, bytes/savings/percent branches, fallback/same-VM locale.
- Tham số không pre-escape; một lần escape cả câu; hostile translation
  không sinh HTML/double escape; tên tệp kỹ thuật/thương hiệu giữ nguyên.
  Whole HTML ngoài đúng ba ô số liệu bằng BASE; dữ liệu không bị mutate.
-13 ordered/frozen key/locale; prior catalogue nguyên vẹn; unknown/missing/
  changed-value rejected. Exact finite four-edit inverse chạy trước Display
  inverse rồi các comparator PDF/Card/Date/Meta/Request/History;
  old hashes và assertion không bị đổi hay bỏ.
- Native: ba signed empty `/documents` histories VI/EN/ZH375px light,
  real GET/refresh/locale và một VI crop đã được xem.
  Cards/downloads=0, không seed record hoàn tất hoặc fake API/output.
  Filled metrics là actual-renderer VM-only, không phải native output proof.
- Chín product tables/schema, sáu plans/mười tám scenes/versions/idempotency,
 20 source before/after và15 original evidence hashes giữ nguyên;
 0 product writes/reseed/egress/provider, ownedJob active0.
- Source gate exit0: bốn exact replay/inverse/whole outside,
 22 protected LF comparators, all app Python unchanged, CI chỉ thêm một
 command, native source byte binding.

## Tình trạng giao bản và phần còn lại

PR747 trước đó đã giao: CI43821671694 hai nhóm SUCCESS;
merge/runtime b3c1749fdc0876164cf9b3bedd64290fdf4d9bf4;
deploy43853462350 SUCCESS; ba dịch vụ active-running/health/năm HTTPS
assets exact; receipts Issue6910067903 / PR6914555619.

Source review độc lập C0/I0/M0 cho đúng hai frozen app hashes; không chạy lại
Node/test/VM/native hay scope gate. Tài liệu vận hành và đối chiếu gốc đã
cập nhật; phiên Tester `DOCUMENT-CARD-METRICS-20261116` READY.
Canonical case1417lines/152989LFbytes, SHA256
`7fb5f2ca92d783d8e40c5b0f8014789d638b0c4355504a4ffd242fca87e1bc82`;
changed metadata1PASS/32deselected/0.44s. Historical remote/P0/labels/Projects
observations giữ, không tạo tracker cạnh tranh hoặc nhận vừa revalidate remote.
PUSH_GATE=READY.

Đợt metrics này chờ provenance và
exact-head CI → merge → deploy → runtime/asset receipt.
Compress-light contrast/PDF guarded copy/catalogue light owner/descriptions/
fallback hub và other forms/headings/reference helper còn trong hàng đợi.
Full locale/responsive/AX/keyboard/auth/device/Safari/signed production UI/
real final output/M-FINAL01..06 vẫn mở; motion cuối.

FILES_CHANGED=2 app files, tests/finite adapters/one CI command/docs only.
BASELINE_FAILURES=16 expected.
BRANCH_FAILURES=0; NEW_FAILURES=0 in the declared grouped run.
PROTECTED_COMPARATORS=22LF/all appPython/exact outside/native data unchanged.
PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_WRITES=0.
DEPLOY=NO for this unit; LIVE_PASS=NOT_TESTED for signed production UI/output.
BLOCKERS=Release gates pending; no whole-goal completion claim.
