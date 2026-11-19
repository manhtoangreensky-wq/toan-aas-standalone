# Chỉnh ảnh — câu chữ dễ hiểu và bốn lựa chọn gọn

TASK=IMAGE-EDIT-CUSTOMER-CLEANUP-20261119.
BASE_SHA=f8932643c1408d6565a0f1574f9bdd47ffac267b.
BRANCH=codex/image-edit-customer-cleanup-20261119.
TRACKER=Issue689/comment7004266812.

## Thứ tự và phạm vi

PR774 PDF phải được gộp, triển khai và có receipt trước khi áp dụng.
Ba worker Antigravity3.8FlashHigh chỉ trả patch ở thư mục riêng:

1. Fields R1:12 dòng catalogue; bỏ chữ Preset/Cinematic/thuật toán dư.
2. Page R2:renderImageEnhance và8 dòng catalogue; bỏ intro/aside/notice/notes
   cùng hai cụm state-meta, giữ hero/nav/form/history/quyền/retry.
   Chuyển liên kết kho tệp vào chân form, không xóa liên kết.
3. Mobile R1:một khối CSS scoped Chỉnh ảnh, max700px. Bốn dòng≥44px,
   đủ tên/href/aria-current/viền chọn/focus; ẩn mô tả dài và link lặp.
   Badge tiếp tục ẩn như BASEtheme8855–8859, không bật lại chữ kỹ thuật dư.

Đúng22 edits,3 tệp ứng dụng:portal.js/portal-i18n.js/portal.css;148 tệp khác
giữ nguyên. Giữ tám trường,required/disabled/custom/options/mã/bounds,
phóng2lần/4096điểmảnh/16triệuđiểmảnh và cảnh báo không thêm chi tiết.
Không backend/auth/API/schema/engine/Bot/provider/ví/PayOS/ENV/motion/data.

Fixture: tests/fixtures/image-edit-customer-copy-reviewed.json.
RAW_SHA=7032192534419999f7528e3a6dbf08151b5db6ed96b3c49c7ecb300a6434007f.
PageR1 có ba OLDclosingtag bị mã hóa sai; R2 trả đúng3 literal corrections,
giữ nguyên NEW/8rows; same-fragment failure1, không vòng3 hoặc Root takeover.

## Acceptance

- 20 khóa đúngVI/EN/ZH; customer/brand/unknownpreset giữ và escape an toàn.
- Không khung trống; đủ form/history/pagination/kho tệp và các chốt quyền.
- Currentrenderer nhận fullphysicalbundles; GitBASE độc lập và toàn byte
  ngoài22 thay đổi giữ nguyên. Không projection current UI.
- Unit kiểm strictboolean,sourceempty/ready,loading/failed,refresh,bounds,
  inputfrozen và nguyênHTML các routePDF/Resize/History.
- Native24view:VI/EN/ZH×sáng/tối×320×844,414×896,768×414,1024×768.
  ChọnTùy chỉnh/Tab/Shift+Tab thật;48mobilelinks≥44px;không submit/tạo ảnh.
- Source151/core/schema/authaudit/egress giữ,owned0;parse/hash48PNG.
- UNKNOWNpaint,wholeAX/recovery/auth/late/device/Safari/signedproduction/
  finalimage giữ cổng riêng; motionM-FINAL01..06 ở cuối.

## QA và phát hành

Finiteleaf chỉ đảo22 edits exact, pin fixture, giữ golden/assertion/negative
và unknownoutside. Nối PDFhistoricalboundary sau guard; PDFcurrentrenderer
vẫn physical, chỉ source comparator stage Edit. RouteEdit không còn thuộc
mảng HTML bất biến của đợt PDF vì chính là scope mới.
Help/Headings cũ được phân loại rõ LEGACY_HISTORICAL_RENDER_COMPARATOR,
giữ mọi assertion/hash/vector, không dùng làm currentUI proof.
ChatCSS stage đúng một append trong comparator riêng,source.css/renderer giữ.
Không sửa genericruntime/pageMetaSources.

CI chỉ thêm một dòng gọi hai bài mới,không đổi trigger/quyền/timeout/matrix456.
Đạt local→docs/Tester/review→onePR/exactHEADCI→merge/treeeq→exclusiveSHAdeploy
→VPS/services/health/5+5assets/receipts. Không tạo PR lưu việc còn dở.
