# Phiên kiểm tra danh mục câu lệnh theo ngôn ngữ

Đang đọc và áp dụng skill owner-governed-codex cho task này.

ID=GALLERY-NATIVE-20261127;Issue689;BASE29e0c154dfd247ac4b0a68cd6336ec83fb3af8ef;
branchcodex/gallery-static-catalogue-20261127;HEAD hiện chưa commit.
ContractDATA7216006483 giữ;runtimecontract7219170926 đã công bố đúngfile
sauOwnerduyệt vàreadbackexact16416ký tự. Đây là phiênTesterlocal,
không phảiGitHubProject mới.

## Đầu vào và acceptance

117row/351value nativeVI/EN/ZH của static Web catalogue,7×20=140mẫu/locale.
Không dữ liệu khách, provider, ví, production jobs hoặc production notes.
Một ngôn ngữ thống nhất cho danh mục/tìm kiếm/chi tiết/copy/newsave.
No-lang canonical giữ;strictlang/body;legacyVI replay;locale-qualified
client retry scope;phản hồi cũ im lặng và không bật control của mẫu mới.

## Bằng chứng local đã có

| Cổng | Kết quả |
|---|---|
| Data schema/token/number/meaning |117row/351value,0machine finding,rootsemantic1lượt |
| Pure native leaf |420samples,0inputmutation/unknownchange/invalidlocaleaccepted |
| Taxonomy renderer |54RED→54GREEN;16key48value |
| Backend primary |13RED/1PASS→14PASS |
| Backend affected |32PASS/2FAIL;2BASE tái hiện cùng IDs/thiếu tzdata Windows |
| Client R1A |100/103PASS;3stale-finally failure gửi lại worker đúng phạm vi |
| Client R2 |51PASS gồm2pressurecase mới;root không tự sửa ứng dụng |
| Client independent review |C0/I1/M0:cachedA reselection finding đã tái hiện RED và khép bằng worker+final55GREEN |
| Client cuối |55PASS/0fail;cachedselection/controlownership/capabilityguard khépfindingđã tái hiện |
| Protected |3Pythoncompile0;6sourcecomparators byte-exact |
| Browser |54cảnh list/detail/loading×VI/EN/ZH×390/768/1440×light/dark;0error/overflow/egress |
| Backend+leaf one-pass review |C0/I0/M0;no rerun suites |
| Historical affected UI |131ca124PASS/7FAIL→finiteleaf70PASS→135affectedPASS;Pythonhistory51PASS |
| Python transport history |75pressurePASS;8static/mount/stale7PASS/1BASEFAIL,cùng BASEassertionline115 |
| Consumer closure |121file:3121PASS giữ;40observedFAIL→40PASS/0FAIL/0SKIP/0ERROR,đúng28file |
| Runtime/backend finitehistory |169pressurePASS,11integration+7backendrecords,rootreview/hookcomplete |
| CI wiring |YAML/byteguardexit0,chỉ hai native runlines;exactheadCI chưa chạy |
| Actual mountedE2E |3locale390×844 PASS;profilefirstmount,filter/detail/clipboard/newprivateMemorynote;0unexpected/pageerror/consoleerror |

Evidence local:gallery-static-data-frozen-nov27.json,
gallery-native-independent-receipt-nov27.json,gallery-server-receipt-nov27.json,
gallery-native-browser-complete-dto-nov27/summary.json và ảnh VI/EN/ZH.
Commands/exit thật được lưu cùng receipts/terminal;không cộng các suite
chồng nhau thành tổng toàn app.

Browser dùng Playwright/Chrome có sẵn vì Browser plugin không có;không cài
gói. Actual renderer/normalizer/i18n/CSS quaHTTP,DOM/focus/select/query có
kiểm;54componentviews không chứng minhclientfetch/auth/fullshell.
Gate mounted riêng đã chạy actualapp/signedshell/fetch/clipboard/note,
DB/secret giả child-only,3localePASS sau sửa hai lỗi runner;
evidence `gallery-mounted-KIuDXw/summary.json`,3ảnh,serverexit0.
Không chứng minhdevice/Safari/production/PWAcache/motion.
Client VM chạy nguyên integration.js thật,deferred fetch/clipboard boundary,
không mock chức năng production. Backend chỉ DB/secret giả trong QAchild.

## Checklist bàn giao còn mở

- [x] Historical input inverse70pressure+135composed+51Python đạt;oldpins/fixtures giữ.
- [x] Cached-reselection RED→55currentnessGREEN,reviewfinding đóng theo bằng chứng đúngdelta.
- [x] Client one-pass review với finding đã khép,không lặp whole-source review.
- [x] Runtime/backend inverse169pressurePASS;40ca từngFAIL ở28file đềuGREEN,
 không chạy lại3121ca đã đạt.
- [x] Actual mountedE2E3locale,clipboard/newprivateMemorynote trongDBtạm.
- [ ] Manifest/provenance/secret gate final.
- [x] Công bố runtimecontract đúngquyền,comment7219170926/readbackexact.
- [ ] Một push/PR cuối sauWeb-onlyprovenance refresh/verify.
- [ ] Exact-headCI,merge,Web-onlydeploy/runtime/assets/cache/receipt.
- [ ] Signed-production exact behavior có bằng chứng riêng hoặc để mở.

STATUS=READY_FOR_RELEASE_CI;PUSH_GATE=READY_AFTER_WEB_PROVENANCE;DEPLOY=NO;LIVE_PASS=NOT_TESTED.
Không dùng trạng thái local hoặc PR818 cũ để đóng lô native mới.
