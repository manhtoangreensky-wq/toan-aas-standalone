# FAMILY-CHROME-NATIVE-20261127

Đang đọc và áp dụng skill owner-governed-codex cho task này.

BASE `363d6ca55081eea4089ebf489cd183b09ba1aa96`;
branch `codex/feature-family-native-chrome-20261127`; tracker Issue689.
FBC135 đã giao bằng PR815, CI45878733080 haiSUCCESS,
deploy45883173277SUCCESS, runtime/treeclean/3active/health/14assets exact,
cache đổi local-e7809e796370701c66db→local-51a084b6f92683d45a0f.
Receipts7201561348/7201561707 đã đọc lại exact. Không làm lại FBC135.

## Kết quả duy nhất

Bảy trang nhóm công cụ có câu chữ dễ hiểu theo VI/EN/ZH và không lặp
phần giới thiệu: bỏ đúng kicker/mô tả ở section dưới hero, giữ heading,
CTA về danh mục, navigation và thẻ thật. Nhánh rỗng dùng hai câu hữu ích,
không diễn giải registry/Core Bridge/nguồn chuẩn hoặc cách triển khai.
Ba AGY4ExtraHigh R1 đã trả đề xuất; root kiểm gộp một lần:
7khóa/21giá trị,20đổi/1giữ(VImusic.title),một exactreturnline bỏ2node.
Không R2/workerfail hoặc root authoring app logic. Candidate tách riêng
đã qua63ca actualrenderer; đó chưa phải BUILD trong ứng dụng.

## Phạm vi ứng dụng và shared effects có chủ đích

- `static/portal/portal-i18n.js`: family.emptyTitle/emptyBody,
  group.image.description, group.voice.description, group.subtitle.description,
  group.music.title/description. Giữ key/order và810entryvalues FBC135.
- `static/portal/portal.js`: một returnline của renderFeatureFamily;
  không sửa hàm dùng chung, chữ ký, condition, quyền hoặc dữ liệu.
- Groupcopy được dùng bởi hero/navigation/explorer và full-catalog section:
  chữ mới tại mọi consumer là có chủ đích. Renderer rootlight riêng giữ nguyên.
- family.emptyTitle cũng dùng ở fallbackunknownfamily; title mới có chủ đích,
  nhưng not-found/guard/layout/route không đổi, không mở nhóm không hợp lệ.
- Statusgrid đã CSSẩn; capability/workbench helpers trả rỗng. Không sửa lại.
- Giữ customertext,route/key/order/group/state/engine/readiness/capabilities,
  controls/ID/ARIA/values/disabled/validation,auth/backend/API/Bot/routeengine/
  provider/wallet/PayOS/ENV/schema/productiondata/motion.
- CSS bất biến trong batch. Findingmàu/bố cục có sẵn phải thànhprerequisite
  riêng có evidence, không sửa ké hoặc dùng fixture thiếucontext làm lý do.

## QA allowlist trước BUILD

Mới: `tests/fixtures/feature-family-native-chrome.json`,
`tests/feature-family-native-chrome.test.mjs`,
`tests/feature-family-native-chrome-history.test.mjs`,
`tests/helpers/feature-family-native-chrome-historical.mjs`,
`tests/helpers/feature_family_native_chrome_historical.py`,
`tests/test_feature_family_native_chrome_historical.py`.
Nối hữu hạn trước FBC trong
`tests/helpers/feature-catalog-full-bundle135-historical.mjs` và
`tests/helpers/feature_catalog_full_bundle135_historical.py`, giữ guard
locale/array cũ trước snapshotleaf. Không đổi interface/hàm ứng dụng.
`tests/feature-catalog-full-bundle135.test.mjs` trở thành historicalinput
qua FCHsourceleaf, giữ fixture/pin/kỳ vọng; FCHacceptance mới đọc rawphysical.
Đăng ký testmới vào `.github/workflows/webapp-quality.yml`.

Sourceleaf khóa fixture/BASE/before-afterpins/exact21records/owner/locale/
unique/order. Không dùng wholecurrenthash để làm mất unknownbytes.
Portal chỉ đảo đúng returnline trong functionowner. Snapshot giữ7key/locale,
đảo20giá trị đãduyệt,giữ unknownentry/order/identity; old/noownedmarkerpass.
Không sửa oldfixture/151pins/expectedhashes hoặc nới assertion.

GREENtarget541PASS; Pythonaffected164 có163PASS/1guard-classification
FAIL: duplicatedMediaStudioowner bịFCHleafchặntrướcvàtrảFCHmessage,
trongkhioldFBCcontractyêucầuFBCmessage. ROOT_QA_GUARD_PRECEDENCE,
khôngapp/workerdefect. Giữ FBCownerguard trênsourcecóFBCaddedmarkers
trướcFCHleaf ở cảNode/Python,giữnguyên guard gốc/phépso/kỳvọng.
Thêmca composedNodeguardRED; chỉrerun oldFBCpressure/caPythonfail/
rawfamilystatic mới,chưa lặp541ca hoặc163Pythonđãđạt.

Soi ảnh hưởng trước BUILD đã chạy:
`rg -n 'featureCatalogFullBundle135HistoricalSource|featureCatalogFullBundle135HistoricalSnapshot|feature_catalog_full_bundle135_historical_source|feature-catalog-full-bundle135-historical' tests -g '*.mjs' -g '*.py'`.
10tệp/19dòng dùng trực tiếp: chat-document-usable-copy11/31;
dynamic-card7/12;Composer7/40;chat-documenthelper8/57;
FBCJSleaf20/48;FBCPython25;NLRsource7/24;NLRJS4/13/27;
NLRPython4/14;PythonFBCtest10. Không đổi signature; consumerclosure
phải xét cả mjs và Python, không lặp thiếu sót FBC135.
Appgroupcopy: portal.js10182/10330/12312/12611/12647/12649/12650/
22235/22246;emptytitle22221/22244,emptybody22244.

## Acceptance và bằng chứng

- Freeze source/21records/20changedvalues/1held từ đúngBASE trướcappedit.
- Raw actuali18n/actualfamilyrenderer,7family×3locale×filled/empty.
  Expectedcopy độc lập từ reviewedproposal; không stub icon/escape/guard.
- Emptyfixture dùng một entry thuộc nhóm khác; catalog[] tự bật fallback
  nên không được giả là validempty. Probe3localeđãquan sát đúng.
- Hero còn tên/mô tả một lần,section chỉ giữ heading/CTA/cards; không ôtrống.
  So toàn markup/control/context/input ngoài hai node/20values vớiBASE.
- Unknownfamily giữnotfound; dữ liệu khách có `<script>` đượcescape/giữnghĩa.
- 810entryvalues/keyset bênngoàiheld,allappsource=BASE+21exactrecords.
- FiniteNode/Pythonpressure:OLD/current/idempotence/partial/changed/duplicate/
  detached/owner/order/unknownbytes,không silentlynormalizeunrevieweddata.
- BrowserHTTPfullrenderer/CSS/customerShell/bodycontext:7families×3locale×
  375/1440×light/dark filled; sharedempty3locale×4view. Text≥4,5:1,
  focus≥3:1,targets44px,0errors/overflow/egress;header/cardscopes ghi rõ.
  Component không chứng minh authhydration/signedproduction/device/Safari.
- Reviewgộp1lượt; chỉ rerunphầnfail/ảnhhưởng khi sửa,không lặp810semantic.
- Docsops/comparison/Tester/master/readiness/manifest/secret/protected/
  provenance→mộtPR/exactHEADCI2SUCCESS→pinnedmerge/treeexact→exclusiveWeb
  deploy/runtime/14assets/cacheversion/receiptIssue689+PRreadback.

## Checklist thứ tự

- [x] PR815 delivery và hai receiptreadback exact.
- [x] BaR1/21values/1returnline reviewed;isolatedcandidate63PASS,khôngappwrites.
- [x] Contracttracker7201641353/readback;fixturefrozen trênBASE mới.
- [x] NewprimaryRED72=67fail5pass và pressureRED trước app/helperintegration.
- [x] Ghép21acceptedrecords,khôngauthorapp;finitehistoryNode/PythonGREEN.
- [x] OutsideDOM/control/input/810values;541primary/2533closurePASS.
- [x] Browser96view5196samples/0finding,min4,9871;FCRprerequisiteđãkhép.
- [x] ReviewFCH/FCRmỗiphần1lượtC0I0M0;docs/Testerđãcó.
- [x] Metadata/manifest/provenance đãkhépPR816.
- [x] ExactCI45945310401haiSUCCESS;merge/runtimebf95e401,
  tree7e057484 bằngtestedtree;Webdeploy45948237821SUCCESS.
  VPSsạch/3active/health/7+7assets/cachelocal-780dbd9e3e3684897e17;
  receiptsIssue6897211048271/PR8167211048279readbackexact.
- [ ] FullgoalGallery/Admin/actionBlockReason/auth/draft/AX/device/Safari/
  signedproductionvẫnmở,motionM-FINAL01..06LAST.

Verify: `node --test tests/feature-family-native-chrome.test.mjs` và
historytest; `python -m pytest --noconftest -q
tests/test_feature_family_native_chrome_historical.py` →0fail/skip.
PROVIDER_CALLS=0product; WALLET_MUTATIONS=0; PRODUCTION_DATA_WRITES=0.

FCRprerequisite cóspec riêng cùngngàyfeature-family-readability:
CSSonly4colorappend. Khôngsửaké;ba lỗi BASE vàeyebrow cóRED,
bốnAGY4ExtraHighproposalđãreview/ghép,source5GREEN vàbrowser96GREEN.
CSS cũ giữ nguyên,nền/outline/layout/motion không đổi.4rootviews0match.
Pythonledger181unique180PASS/1BASEFAIL,NEW_FAILURES=0. Không trả lại
câu kỹthuật ởtest_portal_safety_contracts.py391;testkhôngsửa.
