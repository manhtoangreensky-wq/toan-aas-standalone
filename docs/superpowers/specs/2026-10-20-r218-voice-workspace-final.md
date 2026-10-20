# VOICE-WORKSPACE-FINAL-001 — intake rõ đúng từng chế độ

Baseline đã giao GitHub: 2c216825b2b1fdfcdc4f97853961117299e39547.
Tiếp sau VOICE-REPORT-PROGRESS-001 UI: focused75/75, browser18/18/162 states.
Thay đổi tiến độ một dòng đang chờ checkpoint wave, giữ làm comparator.

## Evidence trước sửa

App/DB QA cô lập tại localhost9423, đăng ký/đăng nhập tài khoản tổng hợp rồi
chỉ GET: `/voice/tts`, `/voice/stt`, `/voice/saved`, `/voice/clone` đều200,
console/overflow0. DOM lưu `../qa/r218-voice-inventory/product-ui-probe.json`:
STT source_language có empty và auto cùng nhãn Tự nhận diện, mặc định empty;
clone form dùng Chuẩn bị giọng đọc; VI STT có audio/MIME, report pending còn canonical.

## Phạm vi và kết quả

Allowed `static/portal/portal.js`, `portal-i18n.js`, bổ sung test
`tests/voice-stt-form-presentation.test.mjs`; không đổi assertion đã khóa.
Protected: backend/integration/auth/Bot/provider/wallet/CI/CSS, quote/timer,
consent required, file ownership và quyền upload/submit.

1. STT field source_language: bỏ emptyLabel trùng, defaultValue=auto; giữ
   nguyên catalog và giá trị ngôn ngữ canonical. Một lựa chọn Tự nhận diện.
2. Khách đã đăng nhập và csrfReady có thể chỉnh lựa chọn ngôn ngữ/định dạng
   tại chỗ khi engine chưa mở. File vẫn disabled theo `enabled`; CTA gửi xử lý
   vẫn disabled; không mở capability hay tự lưu. Map/session cleanup hiện có
   giữ lựa chọn khi chuyển chế độ, không lưu File.
3. Route clone dùng namespace clone cho title/ready/guarded/draft/note và
   confirm copy, không dùng lời đọc văn bản. VI/EN/ZH đúng ngôn ngữ, giữ consent.
4. Dọn audio/MIME/canonical khỏi VI cố định trong phần Voice; copy ngắn, rõ.

Mỗi bước 2–5 phút; Builder runtime Flash hiện không khả dụng: probe READY30s
response rỗng/0turn/0token, log auth không nhận phiên CLI. Không dùng Pro theo
Owner; không mở GUI/auth/settings; Primary tiếp tục công việc đã được giao.

## Checklist

- [x] Test renderer thật: STT auto một lần/default auto; scalar config được
  chọn khi signed nhưng File/submit không được mở; unsigned giữ khóa.
- [x] Clone heading/note đúng cả ba locale, TTS copy/consent không đổi.
- [x] Browser app QA: VI/EN/ZH × sáng/tối ×390/768/1440; đổi mode/back giữ
  source_language/output_format; không submit/request ghi.
- [x] Protected comparator + syntax + evidence/master cập nhật.

Verify: `node --test tests/voice-stt-form-presentation.test.mjs tests/voice-selection-clone-contract.test.mjs tests/voice-workspace-draft-navigation.test.mjs tests/voice-report-progress-truth.test.mjs` → fail0.
Không coi scalar config hoặc source UI là nhận dạng, nhân bản giọng hay giao tệp.

RED18pass/9fail →GREEN27/27 trong STT renderer; nhóm44/44, full Node783/783.
App QA thật18/18, sau auth chỉGET; hai lần đổi locale fixture qua endpoint
CSRF QA để khớp signed profile, không production. VI/EN12 và ZH6 được ghép
từ cùng source sau sửa kỳ vọng HTML zh-CN đúng contract. Raw:
`../qa/r218-voice-inventory/voice-workspace-final-browser.json`.
Harness phải chờ form đúng route, không chỉ URL, vì view transition bất đồng
bộ. Hiện tượng detached lúc chụp còn là quan sát M0, chưa phải kết luận lỗi app.
