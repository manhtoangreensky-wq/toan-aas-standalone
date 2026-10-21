# VOICE-REPORT-PROGRESS-001 — tiến độ Voice đúng dữ liệu

Root: `C:/Users/toann/Documents/Codex/_webapp-r218-voice`.
BASE: `2c216825b2b1fdfcdc4f97853961117299e39547`; PR #654.
Dependency: VOICE-QUOTE-IDLE-001 UI đã đóng, browser22/22, Node769/769,
CI run39433228403 cả hai job xanh; giữ nguyên làm comparator.

## Một kết quả cần đạt

Trong `static/portal/portal.js::safeVoiceReport`, chỉ số hữu hạn trong [0,100]
mới được dùng làm tiến độ. Số 0 thật vẫn hiển thị 0%; null/missing, boolean,
chuỗi rỗng/toàn khoảng trắng/chuỗi số, array/object, NaN/Infinity và số ngoài
miền phải giữ unknown và không render phần trăm. Giữ phép làm tròn hiện hành.

Nguồn contract: `copyfast_api.py:1916`–`1924` chỉ nhận `int/float`, loại bool,
giữ miền 0–100 cho job progress. Không đổi server hoặc tạo trường mới.
Probe trước sửa: `progress_percent=""`, `false`, `"   "` đều trả progress0;
`null` giữ unknown vì `??`; 0/50 giữ đúng. Root cause: `Number(rawProgress)`
ép kiểu trước kiểm tra dữ liệu.

## Phạm vi và các bước 2–5 phút

1. RED: `tests/voice-report-progress-truth.test.mjs` gọi helper và renderer thật,
   kiểm invalid/0/decimal/100, thứ tự ba key và report trạng thái hiện có.
   Codex khóa test trước khi giao; Builder không đổi test để làm xanh.
2. BUILD: chỉ thay phép chuẩn hóa progress trong `safeVoiceReport`, không đổi
   chữ ký, tên hàm, schema, alias keys, priority, output/download/delivery flags,
   reason, tracking, receipt, quote, timer hay CSS. Backend/integration/Bot/
   provider/wallet/PayOS/auth/ENV/CI protected.
3. VERIFY: test riêng + `voice-flow-state-presentation` + timer/edit regression.
   Browser fixture report processing ở VI/EN/ZH, sáng/tối, 390/768/1440:
   unknown không có phần trăm, 0/50/100 có phần trăm đúng, trạng thái/CTA/file
   readiness không đổi; console/overflow/write/external0.

## Acceptance

- [x] AC01 — input không đúng kiểu/miền không hiện tiến độ giả.
- [x] AC02 — 0, số thập phân, 100 giữ đúng policy và key priority.
- [x] AC03 — report status/output/download/delivery/tracking/escaping không đổi.
- [x] AC04 — browser localized/responsive đạt; không phát request ghi/provider.
- [ ] AC05 — protected diff sạch; evidence/checklist/tài liệu cập nhật trước push.

Verify: `node --test tests/voice-report-progress-truth.test.mjs tests/voice-flow-state-presentation.test.mjs tests/voice-quote-expiry.test.mjs tests/voice-quote-edit-freshness.test.mjs`.
Expected: fail0. `node --check static/portal/portal.js`; `git diff --check` exit0.
Builder chỉ báo BUILT/FAILED/BLOCKED, không commit/push/browser/network.

Khép lát này rồi kiểm phần report/player/retry còn lại từ DTO thật; không tạo
URL tải, job, tiến độ hoặc thành công tổng hợp để đánh dấu parity runtime.

Kết quả 20/10: RED0pass/5fail → GREEN5/5, nhóm Voice75/75; browser18/18,
162 trạng thái (9 input/cấu hình). Evidence raw `../qa/r218-voice-inventory/voice-report-progress-browser.json`.
Flash R1 hết3m không code/report; Pro R2 không có trong CLI, không code/report;
Primary sửa đúng một dòng theo test immutable. Owner đổi chính sách chỉ Flash
cho các lượt sau. Probe Flash riêng READY30s có0turn/0token/response rỗng:
runtime Builder chưa hoạt động, không coi exit0/SUCCESS đó là kết quả hợp lệ.
