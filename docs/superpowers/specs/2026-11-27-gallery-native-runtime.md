# GSC-RUNTIME — danh mục, sao chép và lưu cùng ngôn ngữ

Đang đọc và áp dụng skill owner-governed-codex cho task này.

BASE `29e0c154dfd247ac4b0a68cd6336ec83fb3af8ef`;
branch `codex/gallery-static-catalogue-20261127`; standalone; Issue689.
Owner đã chọn tự xử lý trong goal, nhiều phiên Antigravity4ExtraHigh,
không hỏi quyền thường lệ; root giữ Git/QA/ship, worker chỉ đề xuất.

## Nguồn và quyết định

DATA prerequisite đã đạt:117row/351value; bốn CLI terminal0,1proposal/phiên;
root semantic review một lượt;0schema/token/number/ordinary-English finding.
Candidate SHA256 `c3e1f631cd69de181a93bb64c43c1b82c6947d40d0dd058b1feeb90136cab5b7`.
420mẫu ba ngôn ngữ: title tối đa58/prompt448 ký tự JavaScript; không cần
cắt chuỗi hoặc tăng giới hạn Memory160/Gallery320/3200.

Chọn finite native resolver trên server. Không chọn dịch ở renderer đơn lẻ
vì clipboard đang lấy item.prompt và server tự dựng ghi chú từ ID; không
chọn translator tổng quát vì có nguy cơ đổi dữ liệu khách.

`lang` query optional, chỉ exact `vi/en/zh` khi có; giá trị khác kể cả
chuỗi rỗng trả422. Không có `lang` giữ nguyên canonical legacy response
và note chrome để không phá client cũ. UI mới luôn gửi locale đã mount từ
`TOANAASI18n.getLocale()`, không dùng helper locale public-auth.

Tìm kiếm bao gồm native item fields và native goal/platform labels; vẫn
giữ tìm theo ID cũ. Không thay filters/DTO/order/count/IDs/snapshot.
`free_prompt_item`, `expand_free_prompt_snapshot`, `filter_free_prompt_items`
giữ chữ ký/legacy hành vi; PromptLibrary consumer được bảo vệ.

## Allowlist và ranh giới

Ứng dụng:

- CREATE `copyfast_gallery_locale.py`: leaf static resolver, không DB/API,
 import catalogue hoặc auth; dữ liệu native và chrome riêng finite.
- CREATE `gallery_static_locales.json`: bản sao cơ học117row đã duyệt,
 không test/API/customer data; server-owned packaged source.
- MODIFY `copyfast_free_prompt_gallery.py`: ba GET dùng resolver khi có
 lang; localize trước search/paginate; legacy helpers giữ nguyên.
- MODIFY `copyfast_memory.py`: đúng Gallery note helper/handler,
 optional lang; không đổi SQL/table/ownership/auth/CSRF/payload.
- MODIFY `static/portal/portal.js`: chỉ Gallery goal/platform label lookup.
- MODIFY `static/portal/portal-i18n.js`: thêm16taxonomy key và finite
 Gallery feedback keys; không đổi51giá trị GPC đã giao.
- MODIFY `static/portal/integration.js`: Gallery locale transport,
 locale-owned cache, currentness và phản hồi action.

QA mới: `tests/test_gallery_native_locale.py`,
`tests/gallery-native-taxonomy.test.mjs`,
`tests/gallery-native-currentness.test.mjs`; helper/finite history mới chỉ
được mở bằng amendment có delta cụ thể sau khi đã đo failure cần giữ.
Không xóa assertion hoặc sửa fixture lịch sử để làm xanh.

PROTECTED: Bot/route-engine/provider/wallet/PayOS/auth module/generic api/
DB schema/SQL/ENV/credential/customer data/motion/workflows và PR818.
PROVIDER_CALLS=0product;WALLET_MUTATIONS=0;production-data-write=0.
Không chạm mười state cũ, đặc biệt không đọc file campaign state bị cấm.

## Hợp đồng leaf resolver

`gallery_copy(kind,id,field,lang)->str`: exact static lookup, thiếu
key/locale không silent fallback.
`localized_gallery_item(item,lang)->dict`: giữ9key/ID/goals/platforms,
chỉ dựng category_title/industry/title/prompt từ cùng native category/industry.
`gallery_taxonomy_label(kind,id,lang)->str`: finite goal/platform lookup,
unknown ID trả nguyên văn; không đổi arbitrary customer text.
`gallery_locale_text(key,lang)->str`: finite catalog description,
copy instruction và note chrome. Không dynamic translation/network.

Memory note mới chứa nguyên prompt native ở đoạn riêng; title/category/
intro/footer/version/identifier labels native. Không update ghi chú cũ.
Fingerprint effective VI giữ encoding legacy; EN/ZH thêm `lang` vào
fingerprint. Samekey+same locale replay; khác locale collision409;
legacy VI retry vẫn replay cùng note, không ghi lại.
Client scope `memory:gallery-save:<id>:<locale>` và fingerprint
`<id>:<locale>`; giữ uncertain VI key khi VI→EN→VI.

## Client ownership/currentness

Locale-owner RAM riêng ngoài DTO. Khi mismatch, invalidate list/detail và
xóa bốn projections cũ trước await. Không reuse catalogue chỉ vì cùng snapshot.
Capture active locale một lần/operation. Currentness gồm epoch, session,
route, signed state, enabled flag và locale; kiểm trước/sau mỗi await.
Global hydrate reset hiện có vẫn giữ; listener emit:false không bị giả định
là có sự kiện đổi locale.

Catalogue/list/detail cũ không merge. Copy stale không clipboard/toast/
xóa lựa chọn mới. Save server có thể đã hoàn thành hợp lệ, nhưng receipt/
error cũ không merge/toast/clear selection/account/locale mới. `finally`
luôn release và discard submission khi đã acknowledged.
Action filter/refresh/detail chỉ báo thành công khi có kết quả hiện tại;
không báo thành công khi load fail hoặc stale.
Loading locale mới phải thể hiện đang tải, không hiện dữ liệu ngôn ngữ cũ
hoặc thông báo không có kết quả giả. Không thêm khung giải thích trống.

## Thứ tự và checklist

note rõ là chia plan chi tiết ra thành từng spec kèm theo kết quả cần đạt để
qua spec khác, với spec đơn giản thì chạy nhiều spec một lúc, nếu spec phức
tạp thì làm từng spec.

- [x] GSC-DATA —117row/351value/420expanded, frozen receipt.
- [x] READ transport audit và impact scan; quyết định legacy/native ở trên.
- [x] GSC-RED — Python14ca:13RED/1PASS; taxonomy54RED;
 client49ca:34RED/15PASS. Tests hành vi endpoints/Memory, renderer, client race;
 lỗi do thiếu native behavior, không phải lỗi fixture/import.
- [x] GSC-LEAF — static resolver+packaged data;420samples/117approvedrows,
 proposal-byte-exact,0inputmutation/unknowntextchange/invalidlocaleaccepted;
 pure verification exit0, không DB/API. Independent với UIlabels.
- [x] GSC-TAXONOMY —16key/48value, giữ IDs/unknown text, escaped render;
 Node54ca GREEN exit0 sau RED, JS syntax/diffcheck exit0.
- [x] GSC-SERVER —ba reads và Gallery save dùng native leaf; strict lang;
 không đổi payload/DTO/SQL; legacy replay/PromptLibrary giữ.
 Primary14PASS; affected34ca32PASS/2BASE-equivalent thiếu tzdata trên Windows,
 hai ca đã tái hiện cùng ID/cùng nguyên nhân với BASE source bất biến trong RAM.
 Không sửa app/test để né môi trường;compile3Python0,6protectedbytecomparators.
- [x] GSC-CLIENT —lang transport/cache ownership/currentness/copy/save;
 R1A103ca100PASS/3FAIL ở stale-finally controls, R2 sửa đúng hai block.
 Sau R2:51currentnessPASS (thêm hai ca đối chứng), không chạy lại54taxonomy
 không đổi; không tự sửa ứng dụng, worker-code-failure1.
 One-pass client review phát hiện cachedA reselection chưa invalidate
 CopyB đang chờ;newcase RED1 đã tái hiện. Đây là acceptance gap khác
 stale-finally đã sửa;giao Antigravity riêng cached-reselectionR1,
 giữ cùngSPEC,không reset lịch sử hoặc giao vòngba cho cùng lỗi.
 CachedR1 xử lý đúng originalgap nhưng thiếu hai hướng control đối xứng
 do phiếu root chỉ nêu copy;R1A bổ sung đúng siblingdetail/copy/save,
 save chỉ được mở lại khi capability cho phép. Final55PASS/0fail,
 gồm cachedCopyB→ViewA,DetailB→CopyA,SaveA→ViewA và deniedsave.
 Không thêm state/generic refactor;mọi appdelta byte-exact workerproposals.
- [x] GSC-ACTIONS —finite VI/EN/ZH feedback, không câu kỹ thuật/raw server
 text, không toast success khi thất bại hoặc phản hồi cũ.
- [x] GSC-HISTORY-QA —amendment local sau affectedUI131ca:
 124PASS/7FAIL do comparator nguồn/bộ chữ khóa mốc PR818 chưa chiếu delta
 mới. Không sửa pin/fixture/assertion cũ. Thêm đúng fixture finite mới,
 helper source/snapshot inverse và pressure tests; hook trước GPC inverse.
 Primary native luôn đọc raw. Phần này không thay ứng dụng hoặc tính
 worker lỗi.70pressurePASS;hookfiniteentry→GPC/GPR;affectedgroup sauhook
 135PASS/0fail (file setup đã mở lại4ca thật).Pythonhistory51PASS.
- [x] GSC-QA local —nghiệm thu gộp phần đã xong;browser54cảnh
 390/768/1440 ×VI/EN/ZH, light/dark, keyboard/escaping/firstpaint,
 fake DB/clipboard,0provider/0wallet; không kiểm lại PR818 không đổi.
 Browser là actual renderer/normalizer/i18n/CSS;clientrace là fullintegrationVM;
 không thay cho signed-production/fullshell/device/Safari.
- [x] Docs hiện trạng/comparison/master checklist/Tester đã cập nhật đúng
 kết quảlocal;37taskfiles gồm7app/17QA/12docs/1workflow.
- [ ] Sourcecommit vàprovenance Web-only saupublicationgate.
- [ ] Exact-headCI→mộtPR→merge→Webdeploy→runtime/assets/cache→receipt.
- [ ] Signed-production final behavior chỉ tick khi có bằng chứng riêng;
 không suy ra từ public asset byte parity.

GSC-HISTORY-QA allowlist amendment:
CREATE `tests/fixtures/gallery-native-history.json`,
`tests/helpers/gallery-native-historical.mjs`,
`tests/gallery-native-history.test.mjs`;
MODIFY đúng QA hooks trong
`tests/helpers/gallery-customer-copy-historical.mjs`,
`tests/gallery-customer-copy.test.mjs`,
`tests/gallery-readability.test.mjs`.
Không sửa7tệp ứng dụng để trả lại UI cũ. Không thay fixture/pin cũ.
Snapshot inverse chỉ bỏ đủ40owned new keys/locale với exact value/order;
source inverse chỉ đảo các delta renderer/i18n có record bất biến.
Partial/changed/duplicate/reordered/misplaced phải fail, unknown bytes giữ.

### GSC-TRANSPORT-HISTORY-QA — amendment local sau nguồn cũ

Đã chạy đúng ba file static/mount/stale một lượt:8ca,5PASS/3FAIL.
Mount signed entrypoint PASS; một failure tại portal-contract line115 là
baseline đã biết từPR818; hai failure mới là exact literal URL không lang
và currentness call chưa có capturedlocale. Native behavior55ca đọc raw
đã kiểm mạnh hơn; không trả source/app về URL/guard cũ để làm xanh.

QA-only allowlist bổ sung trước sửa:
CREATE `tests/fixtures/gallery-native-transport-history.json`,
`tests/helpers/gallery_native_transport_historical.py`,
`tests/test_gallery_native_transport_historical.py`;
MODIFY duy nhất import/input reader của
`tests/test_free_prompt_gallery_portal_contracts.py` và
`tests/test_project_prompt_stale_response_contracts.py`.
Không sửa assertion/kỳ vọng hoặc PORTAL input ở ca baseline115.
Fixture ghi đúng11integration records từR1A7/R2two/cacheR1one/cacheR1Aone;
inverse đảo từ cuối về đầu,exact source/owner/order,không broad regex.
75pressurePASS;static/mount/stale7PASS/1BASEFAIL,cùngBASEassertionline115
đã tái hiện vớiimmutableBASEsource trongRAM. Không đổi kỳ vọng/app.

### GSC-CI-WIRING — amendment cổng native chưa được gọi

READ workflow27/11 cho thấy step Gallery chỉ gọi GPC/GPR cũ;không có
native taxonomy/currentness/history/server tests. Local PASS không thay
cho gate exact-head của source mới.
Allowlist bổ sung MODIFY `.github/workflows/webapp-quality.yml` đúng hai
run lines trong step regression đang có:
Node ba native suites và pytest hai native suites.
Giữ nguyên triggers/permissions/actions versions/env/dependencies/timeouts/
concurrency/Bot legacy gates/deploy workflow. Đây là QA wiring,không app
implementation hoặc nâng quyền. Không chạy lại các suite đã đạt chỉ vì
thêm dòng CI;exact-headCI vẫn phải có kết quả riêng sau publication gate.

### GSC-RUNTIME-HISTORY-QA — amendment sau consumer closure

Consumer closure đã kết thúc, không còn RUNNING:3161ca/121file,
3121PASS/40FAIL ở28file. Các failure đọc source cũ chưa đảo đúng11record
integration và7record backend GSC đã nghiệm thu; không phải quyền sửa app.
Không chạy lại3121ca đã đạt. Giữ nguyên assertion, fixture và pin lịch sử.

QA-only allowlist trước sửa:
CREATE `tests/fixtures/gallery-native-backend-history.json`,
`tests/helpers/gallery-native-runtime-historical.mjs`,
`tests/gallery-native-runtime-history.test.mjs`;
MODIFY `tests/helpers/gallery-native-historical.mjs` đúng import và hook
runtime inverse trước target guard; cập nhật đúng native Node run line
trong `.github/workflows/webapp-quality.yml` để gọi pressure suite mới.
Fixture backend lấy cơ học7cặp OLD/NEW từ serverR1A; integration dùng lại
fixture11record đã khóa, không tạo hoặc sửa kỳ vọng app.

Acceptance: exact full current source đảo về GitBASE cho cả3file;
unknownbytes/olderinput/idempotence giữ; partial/changed/duplicate/
detached/wrongslot/foreignfile phải không bị âm thầm chấp nhận.
Không broad regex hoặc hash rebasing. Primary native tests đọc raw.
Root kiểm helper/pressure rồi chạy lại đúng28file có failure; chỉ mở rộng
consumer nếu hook mới làm input thay đổi ngoài phạm vi đã đo.

Đã khép27/11:169pressurePASS một lượt;root đọc toànhelper/test rồihook
trướcfiles.hasguard. Recovery chỉ40testname từngFAIL trong28file:
exit0,XML40PASS/0FAIL/0SKIP/0ERROR;3121PASS trước không chạy lại.
Backendfixture7record proposalexact;pin/sourceassertion cũ không đổi.
CI giữ đúng2runlines,6native suites;YAML/byteguardexit0.
Evidence `gallery-native-consumer-recovery-nov27.xml`;
fixtureLFhash `d6fedb7c38b7abec4cd138069dc5aa2634945aff7003b1b0039407c66fa5733f`.

Mounted E2E độc lập dùng actualapp,3locale390px,DB/asset/secret giả
child-only,loopback/socket/endpoint allowlist. Luồng:profilelocale→
signedGallery→filter→detail→clipboard→nativeconfirm→privateMemorynote.
Không provider/wallet/production-data hoặc cleanup thư mục người dùng.
Kết quả27/11:runner đầu VI/EN đạt,ZH dừng doexpecthtmlzh thayzh-CN
vàlogo nội bộ thiếuallowlist;chỉ QAtool sửa,không appfailure.
Runner sau sửa exit0,VI/EN/ZH3flowPASS,0unexpected/pageerror/consoleerror;
profilefirstmount vàdisplay/clipboard/note exact,mỗi account0→1note,
serverexit0. Evidence `gallery-mounted-KIuDXw/summary.json` và3ảnh.
Không suy signedproduction/device/Safari/motion/PWAcache từlocalgate.

## Impact scan trước code

`git grep -n -E 'free_prompt_item\(|filter_free_prompt_items\(|_gallery_memory_note_fields\(|freePromptGalleryItemsPath\(|freePromptGalleryRequestIsCurrent\(' -- '*.py' '*.js' '*.mjs' ':!.agents/state/**'`

Đo27/11:7file/26chỗ. Trong đó production4file:

- `copyfast_free_prompt_gallery.py`:211,273,351,388;
- `copyfast_memory.py`:498,506,937;
- `copyfast_prompt_library.py`:1150 (protected, không sửa);
- `static/portal/integration.js`:7050,17353,17550,17554,17555,17558,
 17574,17578,17591,17606,17611,17620.

QA3file: `tests/test_copyfast_free_prompt_gallery.py`:211,212,214;
`tests/test_free_prompt_gallery_memory_save.py`:66;
`tests/test_project_prompt_stale_response_contracts.py`:120,123.
Giữ API public canonical; chỉ helper Gallery private có optional captured
locale. Không coi grep ít file là bằng chứng ít rủi ro.

## Bằng chứng và stop conditions

Backend verify: Python pytest focused native+legacy Gallery/Memory/PromptLibrary
trong process có DB/secret giả, không production/provider.
JS verify: Node test real extracted functions/VM+complete DTO fixtures,
deferred reads/clipboard/save, literal native expectations.
Browser chỉ localhost cô lập; không tạo production notes.
Compile các file Python đã đổi; syntaxcheck ba JS; protected hash/diff.

Dừng đúng spec khi worker lệch allowlist, thiếu dữ liệu, native field
fallback, test lỗi hoặc comparator thay đổi; worker sửa lại đúng lỗi tối đa
hai lượt. Không dừng phần độc lập đã được giao và không mở scope ngoài goal.
Chưa có runtime output thì không ghi application/LIVE hoàn thành.

## Tình trạng lưu sổ và vận chuyển

Owner đã duyệt riêng đúngfile ngày27/11;runtimecontract đã công bố
nguyên văn vào Issue689,bìnhluận7219170926,đọc lại exact16416ký tự.
TrimmedLFbodySHA256 `def57cde68a6f2ef16cd4518626ded1745ba9567fb10438eb4de991bf1a7c43d`.
Gate publication được mở bằng xác nhận Owner,không bypass rejection.
Đoạn trước trong bản comment là lịch sử lúc chưa có quyền;đây là cập nhật
deliverylocal saureadback. ContractDATA7216006483 giữ nguyên.

Ba worker runtime lượt đầu sandbox dừng trước inference:0turn/0token,
DNS/socket bị giới hạn; không phải bằng chứng cần đăng nhập lại và không
tính worker-code-failure. Đã được phép chạy lại đúng ba phiếu qua network
access, cả ba terminal0/1turn với model `gemini-4-hydrogen-xhigh`.
Root sửa thiếu spec tags chứa cảgoal+platform trước khi có worker turn;
không đổ lỗi worker.69giá trị feedback đã đọc một lượt và tích hợp cùng
GSC-CLIENT;loading thêm3value,tổng24key/72value.

GSC-SERVER R1 yêu cầu BLOCKED vì root ghi thiếu tên module leaf trong phiếu;
R1A bổ sung `copyfast_gallery_locale` rồi trả7edits/2file. Root ghép
byte-exact; worker-code-failures0. GSC-CLIENT R1 thiếu MESSAGES binding và
bối cảnh outer-catch; root bổ sung R1A,worker đã trả terminal0 và final
R2/cacheproposals đã khép bằng55GREEN. Hai thiếu spec
không bị dùng làm lý do tự sửa ứng dụng hoặc tính worker trượt.

Python TestClient sandbox kẹt local socketpair có stack thực nghiệm.
QA đã chạy đúng child cô lập với loopback, DB/secret giả;14ca kết thúc
27,69giây như RED ở trên. Không đổi ENV hệ thống/dotenv/production.
