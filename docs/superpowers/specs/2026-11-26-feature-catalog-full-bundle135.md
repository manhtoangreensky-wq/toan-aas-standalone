# CATALOGUE-FULL-BUNDLE135-20261126

Đang đọc và áp dụng skill owner-governed-codex cho task này.

BASE `fdfe2f753e641c5a5ecc7d6a19305fa3c42b7b30`;
branch `codex/catalogue-full-bundle135-20261126`;Issue689.
PR814 đã giao:CI45826768615haiSUCCESS,deploy45830982258SUCCESS,
runtime/tree/14assetskhớp;receipt7193742593/7193743263readbackexact.
Không làm lạiCVN/CD108 hoặc mở đăng nhập production mới.

## Kết quả duy nhất và bảo vệ

Đồng bộ135mục/810giá trị đã được review trong bộ chữ nhẹ sang
namespace `featureCatalog.entry.*` của bộ chữ đầy đủ. APIi18n thực tế
hiện có96mục/192field mỗi locale. Thiếu39mục/234giá trị;286mô tả
đã có cần đồng bộ;290giá trị đang đúng giữ nguyên. Tổng520giá trị:
117tên mới và403mô tả mới/đổi. BaAGY4ExtraHigh R1,45keymỗi phiên,
đã trả nguyên văn810giá trị,root kiểm exact một lượt;không dịch lại.
ContractIssue689/7193096148đãreadback;khôngcóworkerfailure.

Ứng dụng chỉ mở dữ liệu `static/portal/portal-i18n.js`.
Giữ288titleđãcó/hai descriptionđãđúng,mọi namespace khác,wrapper/
hàm,135key/route/order/group,quyền,guard,state,payload,tìmkiếm,
customertext,backend/API/auth/Bot/engine/provider/wallet/PayOS/
ENV/schema/data/motion. Không sửa `portal.js`,CSS hoặc bộ chữ nhẹ.
Các trang dùng catalog mode nhận entrycopy rõ ràng thay pagefallback
khi thêm key mới;destination-pagecopy giữ nguyên ngoại trừ alias cố định
`/documents` dùng `featureCatalog.entry.documents.description` trong
`localizedPageDescription` (`portal.js:10259`). Mô tả trang này nhận đúng
bản chữ canonical VI/EN/ZH có chủ đích; không sửa logic hoặc dữ liệu người dùng.
Năm account-header aliases chỉ dùng title đã có nên không thay đổi.
Đây là ROOT_SPEC_OMISSION, không phải worker defect. `workspace_menu`
giữ nhánh riêng hiện có;non-catalog/unknown-route fallback giữ.

## QA mở trước BUILD

Thêm fixture `tests/fixtures/feature-catalog-full-bundle135.json`,
primary `tests/feature-catalog-full-bundle135.test.mjs`,
pressure `tests/feature-catalog-full-bundle135-history.test.mjs`,
helperfinite `tests/helpers/feature-catalog-full-bundle135-historical.mjs`,
helperđọcactualconsumer `tests/helpers/feature-catalog-full-bundle135-render.mjs`.
Nối cảsource vàsnapshot ở `tests/helpers/native-label-recovery-historical.mjs`.
Giữ guard locale/array củaNLRsnapshot chạy trước leaf mới.

`tests/native-label-recovery-source.test.mjs` và
`tests/feature-catalog-dynamic-card-locale.test.mjs` trở thành kiểm
tra lịch sử qua finiteFBCprojection,giữmọi fixture/kỳ vọng cũ;
ghi rõ historical,không gọi projection làrawcurrent.
Consumer run2532ca có51fail tại ba comparator Chat/Documents do HTML
đọc raw current nhưng snapshot messages đã về mốc cũ. Mở thêm đúng hai
QA reader `tests/helpers/chat-document-usable-snapshot.mjs` và
`tests/chat-document-usable-copy.test.mjs`: đưa i18n qua finite FBC source
inverse trước VM để HTML và dictionary cùng epoch lịch sử. Giữ toàn bộ
assertion/fixture/pin và three raw-current documents acceptance mới.
Đây là ROOT_QA_CONSUMER_INPUT_MIXED_EPOCH, không worker/app defect.
Chỉ chạy lại ba tệp consumer bị ảnh hưởng, không lặp 2481 ca đã đạt
hoặc browser/app không đổi.
Thêm `tests/feature-catalog-full-bundle135-documents.test.mjs` chạy
`localizedPageDescription` thật cho hai dạng metadata `/documents` ở ba locale,
BASE RED rồi current GREEN bằng switch chỉ trong tiến trình QA con.
Helper chỉ xuất thêm hàm consumer thật, không thay renderer hoặc ứng dụng.
Đăng ký ba test mới trong `.github/workflows/webapp-quality.yml`.
Không sửa151pins/fixtures hoặc nới assertion. NewFBCacceptance
phải đọc nguồn vật lý;canonical810 tham chiếu fixtureCD108 đã khóa
LFhash0decec95d52d462c18482c823cb7032d8c4f5815cbc78516659f86036430f294.

Sourceleaf bindfixture/BASE/fullbefore-afterpins/exactrecords,
ownerFEATURE_CATALOG_MESSAGES/locale/unique/order;không enforce
wholecurrenthash bên tronginverse. Snapshotleaf bỏ đúng78key mới
mỗi locale,khôi phục286description vàgiữ unknownentry/identity/order.
OLD/no-owned-marker passthrough đểgoldenpin gốc bắt phần khôngduyệt.
Partial/changed/duplicate/detached/reordered phải fail.

Soiảnhhưởng: `rg -n 'nativeLabelRecoveryHistoricalSource|nativeLabelRecoveryHistoricalSnapshot|native-label-recovery-historical' tests -g '*.mjs'`.
Năm tệp/15dòng khớp:CD108history:7;CVNhistory:8;Composerhelper:3,25,36;
NLRhelper:11,22;NLRsource:6,26,32,46–50. HaiđiểmnốiQA dùngchung,
không thayinterfaceứngdụng. Source+snapshot consumers phải chạy
đúng nhóm ảnh hưởng,không lặp nhóm không đổi.

## Checklist theo thứ tự

- [x] PR814 delivery/receiptreadback hoàn tất.
- [x] BaAGYR1/135key/810exact canonicalvalues đã khóa;không semanticredo.
- [x] Freeze newfixture/records/before-afterhash từ đúngBASE.
- [x] Actuali18nAPI/moduleCardRED trước appedit;nguồn/hàm consumer thật.
- [x] Tích hợp520giá trị đúng accepteddata;không authorapplogic.
- [x] Source+snapshotRED/GREEN;typeguardprecedence/unknownidentities/
  oldpins/fixtures/expectations và rawcurrentacceptance giữ.
- [x] Primary810values/135cards/VIENZH/known+nonnatalog+unknownfallback
  trong GREEN458; alias documents riêng3RED→3GREEN,phụlục7199225755exact.
- [x] Source/snapshot consumerclosure110tệp2532ca:2481pass/51QAfail;
  phụlục7199695259 trước hai readerfix,ba tệp215pass/exit0 khép51lỗi.
  Ledger2532unique là hợp nhất receipt,không freshwhole run;
  không tăng workerfail vì lỗiQA/specroot,không appchange.
- [x] Browser actualfulli18n+moduleCard/CSS/customerShell/đúngbodycontext,
  12viewVIENZH/sángtối375/1440,text≥4,5:1/focus≥3/target44,
  0unknown/error/overflow/external;không dùng lightbundle làm fullproof.
- [ ] Reviewgộp/docs/featurecomparison/Tester/metadata/manifest/provenance.
- [ ] ExactHEADCI2jobs/mergepin/tree/exclusiveWebdeploy/runtime/7+7assets/
  receiptIssue689+PRreadback. Không dừng ởmerge/deploy.
- [ ] Signedproduction/fullapp/familychrome/Gallery/Admin/actionBlockReason/
  auth/draft/AX/device/Safari/motionLAST giữ mở;toàngoal chưa hoàn thành.

Verify: `node --test tests/feature-catalog-full-bundle135.test.mjs`
và `node --test tests/feature-catalog-full-bundle135-history.test.mjs`
→0fail/skip sau sửa,số thật lấy từoutput.
`node --check static/portal/portal-i18n.js`;`git diff --check`→exit0.
PROVIDER_CALLS=0product;WALLET_MUTATIONS=0;PRODUCTION_DATA_WRITES=0.
