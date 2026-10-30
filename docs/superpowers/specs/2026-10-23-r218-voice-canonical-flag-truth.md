# VO-CANONICAL-FLAG-TRUTH — trạng thái giọng không suy từ dữ liệu sai kiểu

BASE_SHA=9d941fbd52e444d3093f781c48f49ea6dcf30350
Branch: webapp-r218-billing-ui-20261022; repo standalone; PR661; trackerIssue662.
Phân loại: COMPLEX/SINGLE vì hai builder dùng chung một nguồn giọng; một worker
Flash3.8 tại một thời điểm. Không thay mục tiêu parity Bot của toàn bộ Voice.

## READ — bằng chứng và nguyên nhân

C0 đã có receipt CI terminalSUCCESS run39904684572; không mở lại C0.
Probe renderer thật với catalogue EN ngày23/10 cho thấy booleanfalse hiển thị
đúng trạng thái chưa sẵn sàng, còn chuỗi `"false"`/`"0"`, object và array lại
hiện Default/Available for speech/Preview information exists. Đây là lỗi UI
trên dữ liệu sai kiểu có kiểm soát, không phải khẳng định API production đang sai.
Nguyên nhân: JavaScript truthiness thay vì kiểm booleantrue.

Impact scan `git grep -n -E 'profile\.(tts_ready|is_default|preview_ready)' -- static/portal/portal.js`:

| Dòng BASE | Điểm dùng | Số điều kiện |
|---:|---|---:|
|11253|renderFields: chọn profile có tts_ready|1|
|11254|renderFields: nhãn mặc định|1|
|11751|renderFormCard nhánh Voice: chọn profile có tts_ready|1|
|11752|renderFormCard nhánh Voice: nhãn mặc định|1|
|32906|renderVoiceVault: default/tts-ready/preview metadata|3|

Một production file, ba vùng, bảy predicate; không rename/chỉnh chữ ký/shared
helper. Baseline focused39/39. Backend projection chỉ được đọc để đối chiếu;
không thay contract, quyền hoặc dữ liệu canonical trong phiếu này.

## CONTRACT — phạm vi khóa

- Production allowlist: `static/portal/portal.js`, đúng bảy predicate trên.
- Test allowlist: `tests/voice-inventory-presentation.test.mjs`; mở rộng harness
  renderer thật/catalogue thật đang có, giữ mọi test hiện hành.
- Thay `profile.tts_ready`, `profile.is_default`, `profile.preview_ready` ở các
  vị trí trên bằng phép so sánh `=== true`; không helper/refactor/normalization.
- Protected: API/backend/bridge/auth/CSRF, integration, i18n, CSS, schema, wallet/
  PayOS, provider/Bot, quyền/capability, route, input/estimate/job/output và mọi
  delta C0/Voice/Music/SubDub đã nghiệm thu.
- Không sửa chữ Việt của generic option trong cùng patch. Đó là finding locale
  riêng nếu còn được render ở một sản phẩm; không sửa ké lỗi này.
- Không thêm nút management/preview hoặc biến metadata thành audio thật.

## Thứ tự task và tiêu chí đóng

1. TEST (2–5 phút): thêm các case dùng renderer thật ởVI/EN/ZH, với giá trị false,
   undefined/null, số0/1/-1, chuỗi rỗng/false/true/0/1, object/array. Chỉ true thật
   được mang nhãn mặc định/ready/preview metadata. Mong đợi lấy từ literal độc lập,
   không dùng hàm i18n cần test để tính cả expected lẫn actual.
2. SELECT (2–5 phút): kiểm trực tiếp renderFields và renderFormCard nhánhVoice:
   tts_ready sai kiểu không thành option; true thật vẫn có option, thiếuID vẫn bị
   loại, is_default sai kiểu không thêm marker nhưng không loại giọng ready thật.
3. BUILD (2–5 phút): chỉ bảy phép so sánh; không đổi nhãn/route/field/palette.
4. Codex REVIEW/VERIFY: áp test trước để có RED đúng assertion, sau đó patch
   production; focused Voice, fullNode, sourcePython10 vàsyntax/diff comparator.
5. Browser18 cấu hình VI/EN/ZH ×2theme ×390/768/1440 với GET profile fixture rõ
   nguồn, signed localhost app. Kiểm list/details/select, true/false/malformed,
   keyboard/focus, lỗi/tràn ngang; chặn ngoài localhost và mọi UI write.
6. Tài liệu vận hành/đối chiếu gốc/caseTester, provenance, push branch và CI đúng
   HEAD. Không merge PR/deploy trong spec UI này; goal tổng giữ ACTIVE.

### Acceptance criteria

- AC-01: thẻ kho giọng chỉ hiển thị nhãn tích cực khi từng flag là booleantrue;
  mọi giá trị khác không được hiển thị thành true, kể cả string `"true"`.
- AC-02: cả hai select builder chỉ nhận profile cóID và tts_ready===true; marker
  mặc định chỉ nhận is_default===true. Dữ liệu input không bị mutate.
- AC-03: true/false bình thường, escaping tên, status/consent, thứ tự/limit50,
  route/form/capability/noaudio/nooutput và VI/EN/ZH giữ nguyên.
- AC-04: browser matrix18/18, không console/page error/overflow/external/UIwrite;
  fixture read-only không được gọi là canonical API/provider/output/LIVE đã đạt.
- AC-05: diff đúng allowlist, fullNode/source contracts/provenance/CI có output;
  closed C0 và canonical management gap không bị đánh dấu lại sai.

RED/GREEN: `node --test tests/voice-inventory-presentation.test.mjs`.
Regression: `node --test tests/*.test.mjs`; pytest hai Voice source contract files;
`node --check static/portal/portal.js`; `git diff --check`.
Worker không tự chạy tool trong stdout-only transport: ghi NOT_RUN, không suy PASS.

Stop: cần sửa ngoài7predicate, đổi capability/API, source lệchBASE, testharness
không thực thi target thật, có worker khác hoặc dữ liệu/secret/provider mutation.
HANDOFF_ROUND tối đa2; sau hai lần sai cùngAC mới Codex tiếp quản đúng phạm vi.
PROVIDER_CALLS_APP=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_MUTATIONS=0;
DEPLOY=NO; LIVE_PASS=NOT_TESTED.

## QA fixture amendment — trước browser nghiệm thu

QA server không cấu hình bridge và tài khoản QA chưa liên kết Telegram, nên
bootstrap đúng thiết kế không gọi GET profiles. Hai lượt đầu dừng ở trạng thái
guarded, không phải RED hợp lệ cho lỗi flag và không phải lỗi production.
Để kiểm target renderer trong signed app, Playwright chỉ sửa hai READ response
ở trình duyệt: `auth/me.data.account.telegram_linked=true` và `core/status`
configured/copyfast flags cho phép đọc. Phiên/account/CSRF thật từ DB tạm giữ
nguyên; không sửa role, source auth, DB liên kết, ENV hay server authority.
provider_calls_enabled/web_feature_execution_available vẫnfalse và execution
features rỗng. GET profiles dùng DTO fixture; mọi UI write/external request bị
chặn. Bằng chứng chỉ là rendered UI/integration dưới fixture đọc, không phải
canonical bridge/auth-link/provider/preview/output đã hoạt động thật.

## Local acceptance — 23/10/2026 12:52 +07

R1 test output15pass/9fail có một assertionZH sai vì substring; production patch
R1 chưa áp vì context lặp. R2 sửa cả hai; corrected test-onlyRED15pass/9fail đúng
lỗi, rồi productionR2 áp nguyên văn. Không có vòng3 hoặc Codex sửa source tay.
GREEN24presentation/48focusedVoice/951fullNode/10Python source. BoundedCI local
395passed/1WindowsPOSIXdeselected/0failed/16warnings,112.86s; Linux CI phải chạy
testPOSIX giữ nguyên. Syntax/compile/diff-check đạt; bảy predicate trên5dòng.

Browser18/18configs,180profile states với fixture amendment đã khai báo; errors/
overflow/UIwrite/external0. Tài khoản/locale setup chỉ DB tạm. ServerQA76092 đã
dừng qua newline, exit0; DB/assets dọn, listener43347 không còn. Chỉ localUI
được nhận; sourcecommit/provenance/push/CI và canonical management/LIVE chưa đóng.
