# CATALOGUE-VIDEO-NATIVE-20261126 — root danh mục video

Đang đọc và áp dụng skill owner-governed-codex cho task này.

BASE/runtime `ccf824a1482ef3ae7fd2d4187932902e36ddbc14`;
nhánh `codex/catalogue-video-native-20261126`; Issue689.
PR812 đã giao:CI45801754797 hai jobSUCCESS,deploy45805852583SUCCESS,
treeaa65173f bằngtested01b7,VPS/5+5assetskhớp;receipt7190141777/
7190142542 đọc lại đúng. Không sửa lại NLR hoặc gộp lẫn nhánh cũ.

## Lỗi và consumer thật

Root `/features` dùng `portal-feature-catalog-copy.js` trước
`portal-features.js`,không dùng bundleportal.js/i18n đầyđủ.
Thiếu đúng27Videoentries trongbộchữ108mục hiệncó làm renderer giữ
nguyên tênAnh/môtảViệtnguồn. Không đổi locale/auth/renderer đểnéthiếu.
Các trangfamily/workspace khác là phạmvi riêng,còn tronggoal.

Ứngdụng chỉ sửa `static/portal/portal-feature-catalog-copy.js`.
Đúng9insertionrecords do3AGY4ExtraHighR1 trả;R2sửa35values đãreview,
127valuescònnguyên. 27keys×3locale,title/description=162values.
Giữ nguyên108entry cũmỗilocale vàmọibytewrapper/style;khôngrefactor
legacyfilelớn. BeforeLFhash164b3dbe7384a78985e5c1f279eebea12f7f5cb4c74e4091b7396821d596a799;
after8680e808c06e64358fe63ed08a7b06d21f9ccdc08e48f6e3cf4a19de35f4e329.
Fixture mới chứa expectedcopy,27immutablekey/route,beforecopyvàrecords.

## Acceptance và bảo vệ

- Đủ chính xác135thẻ=108cũ+27Video;ba ngônngữđủtitle/description,
  không genericEnglish trongVI/ZH;propernames/AI/MP4/WebM giữ khi cần.
- Môtả trungtính,không hứa khảdụng/tạo/xuất/tải khi chưa có bằngchứng.
  Planningtools chỉlậpkếhoạch;cảnh tựquay cầnquyền;referencekhông
  phântíchvideo;preview chỉ tệp riêngđãcó.
- Giữ mọi key/route/order/group/engine/readiness/href/searchterms,
  quyền/guard/disabled/inputsource/escaping/fallbackkhóalạ.
- Giữ toàn bộBot/routeengine/provider/wallet/PayOS/ENV/schema/data,
  auth/API/backend/motion,NLR3sourcepins và108entrycũ.
- BrowserHTTP VI/EN/ZH×light/dark×375/1440,search/clear/Tab/135cards,
  nooverflow/error/external;chữđo≥4,5:1/focus≥3:1,target≥44px.
  Componentfixturecôngkhai không chứng minh signedhydration/production.

## Hàng đợi và checklist

| SPEC | Kết quả | Dependency |
|---|---|---|
| CVN-A | 9 mục quy trình/kịch bản có đủ chữnative | Đềxuấtđãđạt,R2delta7 |
| CVN-B | 9 mục ýtưởng/thamkhảo/tạo video | Đềxuấtđãđạt,R2delta3 |
| CVN-C | 9 mục côngcụ/điềuphối video | Đềxuấtđãđạt,R2delta25 |
| CVN-VERIFY | exactsource+87rendererchecks+oldinventory+browser | NLRđãgiao;A/B/C |
| CVN-RELEASE | docs/Tester/CI/merge/Webdeploy/runtime/receipt | VERIFY |

- [x] NLR delivered/receipt readback trướcBUILD mới.
- [x] Sourceaudit đủ27key/route vàconsumerloadorder.
- [x]3R1proposals,reviewgộpC0/I2/M4;3R2exact35corrections,0appwrite.
- [x] ActualrendererRED87case83fail/4pass/0error trướcappedit.
- [x] Chỉtíchhợp9finalrecords vàfixture/test;rawsourcehashđúng.
- [x] GREEN87checks,3statesmỗithẻ,108oldentriesvàkhóalạgiữ.
- [x] Testinventorycũexact108→exact135;giữ135=108+27vàpurity,
  chỉthêmMP4/WEBMproperformatallowlistZH,khôngnớigenericEnglish.
- [x] Browser12viewđúngcontextshell/customer vànormalizerthật;
  không dùng những lượtharnessthiếucontext làmappfailure/PASS.
- [x] ReviewgộpC0/I0/M0/docsvậnhành/đốichiếuchứcnăng/Tester/CIregistration.
- [ ] Web-onlyprovenance/exactCI/merge/tree/exclusivedeploy/runtime/
  assetnhẹ+assetcũ/receiptIssue689+PRđọc lạiđúng.
- [ ] Signedproduction/full-appplaincopy/AX/auth/draft/device/Safari/
  motion cuối vẫn riêng;không nhận toàngoalhoànthành.

## QA và phạm vi tệp

Thêm `tests/feature-catalog-video-native.test.mjs`,
`tests/fixtures/feature-catalog-video-native.json`;chỉnhđúnginventory/
format trong `tests/feature-catalog-customer-card-locale.test.mjs`.
Đăngkýnodegroup trong`.github/workflows/webapp-quality.yml`.
Tài liệu/Tester/readinessmetadata/provenance dùngcác tệpsẵn,không tạo
project/issue/PR trống. Không sửa frontendrenderer/CSS/registry/backend.

`node --test tests/feature-catalog-video-native.test.mjs tests/feature-catalog-customer-card-locale.test.mjs`
→0fail/skip;newrendererfile87cases. `node --check`copybundle và
`git diff --check`→exit0. Sốobservationskhông cộng thành testunique.
BaselineNodeREDđã cósourcecopy/rendererhash bằngBASEccf;khôngrerun
matrixkhôngliênquan. Pythonbundle-splitcũcófinding500line/innerHTML
static chưađượcchứngminhbaseline;khôngsửaassertions đểépqua.

SAME_DEFECT_FAILURES: giữA/CmộtlầnfindingchữR1,Bspecclarification;
R2trảđúng;rootchỉtíchhợpmechanicalkhôngtựviếtlạicodeứngdụng.
PROVIDER_CALLS=0product;WALLET_MUTATIONS=0;PRODUCTION_DATA_WRITES=0.
Mọi gatechưađạt vẫn mở;motionLAST.
