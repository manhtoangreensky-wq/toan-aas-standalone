# CATALOGUE-DESCRIPTIONS108-20261126

Đang đọc và áp dụng skill owner-governed-codex cho task này.

BASE `de870867a27edb02a0d944b3539c0623f1cde3eb`;
nhánh `codex/catalogue-descriptions108-20261126`; Issue689.
PR813 đã giao: CI45817536627 hai job SUCCESS, deploy45821431028
SUCCESS, runtime/tree/14asset khớp; receipt7192334539/7192334547
đã đọc lại nguyên văn. Không sửa lại 27 mục Video hoặc đợt CVN.

## Kết quả và phạm vi khóa

Giản lược mô tả 108 mục cũ của root `/features` thành câu khách hàng
dễ hiểu trong VI/EN/ZH. Không đổi title, key, thứ tự, route, nhóm,
quyền, trạng thái, tìm kiếm, chức năng hoặc giới hạn thực sự.
324 giá trị đã được ba phiên Gemini4ExtraHigh R1 đề xuất và rà gộp
một lượt C0/I6/M6; R2 chỉ sửa đúng32field,giữ292field.
Ba ambiguity workspace/operations/PDFsplit được giải quyết bằng
nghĩa chung có căn cứ, không tính worker failure.
So nguồn tại BASE:322description sẽ đổi,2giá trị đã đúng giữ nguyên.

Ứng dụng chỉ mở `static/portal/portal-feature-catalog-copy.js`.
Root chỉ tích hợp dữ liệu đã khóa; không tự viết lại chức năng.
Giữ27Video và mọi title/wrapper/style; không đổi renderer/CSS/
registry/auth/API/backend/Bot/engine/provider/wallet/PayOS/ENV/
schema/data/motion. Full-bundle/family copy là phạm vi kế tiếp,
không giả rằng bộ chữ nhẹ sửa được mọi trang.

## QA được mở và thứ tự

Thêm:
- `tests/fixtures/feature-catalog-descriptions108.json`
- `tests/feature-catalog-descriptions108.test.mjs`
- `tests/feature-catalog-descriptions108-history.test.mjs`
- `tests/helpers/feature-catalog-descriptions108-historical.mjs`

Điểm nối tối thiểu:
- `tests/helpers/feature-catalog-video-native-historical.mjs` gọi leaf
  mới trước khi đảo9recordCVN; không đổi chữ ký.
- Hai test `feature-catalog-video-native.test.mjs` và
  `feature-catalog-video-native-history.test.mjs` nhận source CVN
  lịch sử sau finite CD108 inverse, giữ tất cả kỳ vọng/fixture cũ.
- `.github/workflows/webapp-quality.yml` đăng ký hai test mới.

Soi trước sửa: lệnh
`rg -n 'featureCatalogVideoNativeHistoricalSource|feature-catalog-video-native-historical|feature-catalog-video-native\.json|feature-catalog-video-native\.test' tests .github/workflows -g '*.mjs' -g '*.yml'`.
Năm tệp/bảy vị trí: workflow:120; CVNhistory:12; CVNtest:10;
CVNhelper:5,20; NLRhelper:3,12. Không đổi interface ứng dụng.
14source-pinconsumer đã được xác định ở phụ lục CVN trước.

Không sửa151pins/fixture cũ hoặc nới purity/inventory. CD108 mới
phải kiểm nguyên văn nguồn vật lý, không được gọi inverse để
kiểm chính đầu vào hiện tại. Test CVN được ghi rõ là historical,
không tiếp tục gọi projection là raw physical source.
Leaf mới chỉ đảo exact reviewed322records,bindfixtureLFhash/BASE/
before-afterpins,OLD/unrelatedpassthrough,idempotent,giữunknownbytes.
Partial/changed/duplicate/detached/reordered phải bị phát hiện;
không có marker mới thì giữ source cho goldenpin gốc bắt lỗi.

## Checklist nhìn thấy được

- [x] PR813 delivered và hai receipt đọc lại trước mở BUILD.
- [x] Ba R1/ba R2, review324giá trị một lượt,32delta exact,292giữ.
- [x] Đóng fixture/record/pins từ đúng BASE trước sửa ứng dụng.
- [x] RED actual renderer trước app edit, đo kết quả thật.
- [x] Tích hợp đúng322record mô tả,không đổi source ngoài allowlist.
- [x] RED/GREEN finite history và amended CVN expectations giữ nguyên.
- [x] Renderer thực tế108×3locale;135inventory/title/27Video held,
  href/search/input/three states/unknownfallback và rawsource đúng.
- [x] Source-pin consumers liên quan một lượt, không chạy lại unrelated.
- [x] Browser12view đúng serverbodyclass/customerShell/normalizer:
  search/clear/Tab,text≥4,5:1,focus≥3:1,target≥44px,0overflow/errors/
  external/unmeasured. Không dùng số đo CVN cũ thay bằng chứng mới.
- [x] Review gộp C0/I0/M0/docs vận hành/đối chiếu chức năng/Tester.
- [ ] Metadata/source/protected/secretmanifest và provenance.
- [ ] Provenance/exactCI2jobs/merge/tree/exclusiveWebdeploy/runtime/
  7+7assets/receiptIssue689+PRreadback.
- [ ] Signedproduction/full-appauth/draft/AX/device/Safari và motion
  M-FINAL01..06 giữ mở; motion cuối, toàn goal chưa hoàn thành.

Verify: `node --test tests/feature-catalog-descriptions108.test.mjs`
và `node --test tests/feature-catalog-descriptions108-history.test.mjs`
→0fail/skip sau sửa; số ca ghi từ output, không suy đoán.
`node --check static/portal/portal-feature-catalog-copy.js` và
`git diff --check` →exit0. PROVIDER_CALLS=0product;
WALLET_MUTATIONS=0;PRODUCTION_DATA_WRITES=0.

## Phụ lục QA sau GREEN đầu

RendererRED329=323fail/6pass/0error;historyRED8=7fail/1pass/0error.
Nguồn đã tích hợp đúng322records,afterhash
`6ca65ab581a72e731203c68ec1e38516305d4c70fd6803c7691234f61c74b1a6`.
GREEN đầu451ca449pass/2fail:purityZH thiếu tên định dạngPNG và
leaf chưa chặn record cuốiZH bị dời raEOF nhưng vẫn đúng thứtự.
Chỉ thêmPNG trong `tests/feature-catalog-customer-card-locale.test.mjs`
và guard ranh giới locale ởleaf;giữ app/fixture/pins/regex vàmọi
kỳ vọng cũ. Đây là hai điểmQA điều phối,không tăngworkerfailure.
Phụ lục Issue689/7192590237 đã đọc lại đúng. Failed-onlyrecovery2pass;
affectedhistory112pass;15sourceconsumers233pass. Browser12view mới
5220samples,min5,0855507509/focus5,8600809480/target44,0finding/
error/overflow/external/unmeasured;ảnh375sáng/tối đã mở. Không lấy
số cũ làm evidence mới hoặc cộng các lượt chồng thành tổngcase.
