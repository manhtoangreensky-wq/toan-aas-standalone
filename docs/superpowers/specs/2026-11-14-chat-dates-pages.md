# CHAT-DATES/PAGES — 14/11/2026

BASE `7e30dd95d2d5652281f9462a73f7ba08b7801f59`, PR732 deployed.
Issue689 only; PR732 receipts6876684304/6876684561.

Owner yêu cầu: chữ ứng dụng theo VI/EN/ZH,không trình bày dạng kỹ thuật,
không sửa nội dung khách và không bỏ điều khiển thật. Antigravity được giao
hai phiên độc lập output-only,publicWebsource398+fullMAP. Bản mới7e30 giữ
nguyên ba OLD anchors; biểu thức ngày phải thay trong hàm thẻ,không toàn tệp.

|Spec|Chỉ thay|Kết quả quan sát|
|---|---|---|
|CHAT-CARD-DATE-20261114 R1|Một biểu thức trong renderChatWorkspaceCards|Ngày hợp lệ theo locale medium+short,múi giờ trình duyệt;thiếu/lỗi hiện—,không ISO/rawexception|
|CHAT-PAGINATION-20261114 R1|Một renderer+4key/locale|Aria/dòngsố/nút trước/sau đúng locale,giữ mọi phép tính/offset/disabled/action|

GOAL=Ngày dễ đọc/chuyển trang rõ ràng,không đổi dữ liệu lưu.
ALLOWED_APP=portal.js đúng biểu thức ngày trong functionscope và một hàm
pagination;portal-i18n.js đúng4key12value trướcverify/freeze.
ALLOWED_TEST=tests/chat-dates-pages.test.mjs;tests/helpers/chat-dates-pages-runtime.mjs;
tests/helpers/chat-dates-pages-snapshot.mjs;test/adapter cũ chỉ để giữ nguyên
scope/golden cũ qua đúng4key/2span đã duyệt. CI thêm testline tại bước có sẵn.
PROTECTED=rawdata/dateatrest/customertext/20cardkeys/4docfeedbackkeys/
rights/routes/IDs/actions/controls/math/coercion/loader/API/auth/schema/ENV/
Bot/provider/wallet/PayOS/CSS/motion/cache.
PROVIDER_CALLS=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_WRITES=0.

## Checklist và cổng

- [x] PR732 prerequisites:exactHEAD211e45feCI43589450424bothPASS,
  merge/runtime7e30dd95,deploy43590585769PASS,tree96606afc exact,
  services/health/4assets/protectedhashesexact,receipt cùngIssue/PR.
- [x] Candidate gộp actualVM39cases:BASE4PASS35RED→39PASS,worktree unchanged.
- [x] Permanent31BASE3PASS28RED→31PASS,nativeBASEfirstviewEXPECTED_RED.
- [x] Exact3workerchanges/2appfiles,scopedOLDglobal2/function1;
  helper/signature/dateatrest/otheroccurrence giữ;4newkeys12value.
- [x] Actual date validUTC/offset/Dateobject/missing/null/space/invalid/
  formatterthrow/empty/localeafterinit/customernames/escaping/attrs đạt.
- [x] Actual paginationempty/first/middle/last/strings/disabled/nullinvalid
  offsets/math/order/aria/keyset/localeafterinit đạt,không tạo trang giả.
- [x] Native6views VI/EN/ZH375light/1440dark,GEToffset0→50→0 bằng nút thật:
 50→5→50cards,ngày theoIntl native từserverdate,copy4keys/controls đúng;
  nofakeAPI/boot/CSS/nooverflow/error,165QAtmpmetadata/6plan18scene/evidencegiữ.
- [x] ReviewC0I0M0/17protected/golden/unknownkey/partial/hash;
  targeted+affectedregressions,compile/syntax,không rerun unrelatedsuite.
- [ ] Docs hiện tại/gốc/Tester/cases/metadata/provenance/exactCI/merge/deploy/
  runtime/assets/receipt riêng;wholegoal vàmotion vẫn mở.

## QA / special constraints

Date OLD `safeText(String(item.updated_at || "—"))` có2chỗ toàn portal nhưng
chỉ1trongrenderChatWorkspaceCards. Dùngfunctionboundaryđúngrồiapplyonce.
Không sửa biểu thức khác hoặc globalformatter. Expecteddate lấy từIntl
independent medium+short,không lấy từhelper under test;không sửa hosttimezone.

Pagination uiText thực tế khôngescape:worker dùngsafeText(uiText(...)) ở4
chỗvàfallbackVI động từcùngfrom/to/total. Điều phối sửa assumption trướcgiao,
SPEC_CORRECTION/workerfault0;không đổimathguard hoặchelper.

OwnedQA copyfakeDB,cấu hìnhchild-only/secretgiả,165metadata=3owner×55hợp lệ;
không nguồn customer thật/production,không bảng/schema mới. Browser chỉGET/
HEAD và3fakeauthPOST;chặn ngoại vi/ghi sản phẩm;dọn riêngownedJob→0.
Không hẹn giờ tựdeploy hoặc tắt dịch vụ khác.

Web–TTS generic forwarding là đường có chủ đích,khác dedicated lifecycle
không tự chứng minh routebug. VPS voice_tts execution allowlist cònfalse;
không bậtENV/quyền/thựcthi cóphí dưới phiếu này. ActualaudioNOT_OBSERVED.
OtherChatdetail/context/run/toast/Docroutes/helpercontrast/AX/auth/device/
Safari/signedproduction/M-FINAL-01..06 giữmởđúngthứtự.
