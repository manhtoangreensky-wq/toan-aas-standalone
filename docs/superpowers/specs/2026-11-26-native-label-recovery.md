# UI-NATIVE-LABEL-RECOVERY-20261126

Đang đọc và áp dụng skill owner-governed-codex cho task này.

BASE/runtime `1a57e62152855b1cff39956d43ad0ccfd5f3d5cb`; nhánh
`codex/native-label-recovery-20261126`; cùng Issue #689.
PR811 đã phát hành, hai receipt7184206269/7184206373 đọc lại đúng.
Không làm lại Composer hoặc đợt màu đã đạt.

## Bằng chứng và thứ tự

Tái dùng artifact authenticated15091732002 của CI45762823823, đúng
testedHEAD404ba427/tree bằng BASE đã triển khai.456route records đạt
các gate tải trang/locale/theme/reload/không tràn; runner không kiểm
ngữ nghĩa mọi câu chữ hoặc label. Không chạy lại matrix để tìm lỗi này.

1. NLR-IDENTITY: fallback `Phiên bảo mật đang chờ` bị dùng làm tên ở
   header/dashboard, kể cả EN/ZH. Chỉ xử lý fallback trình bày:
   `displayName()` trả rỗng khi không có tên; header dùng nhãn Tài khoản
   đang có; dashboard dùng bạn/there/您. Mọi candidate có thật giữ
   nguyên precedence/trim/80ký tự; không đổi profile/session/auth.
2. NLR-VOICE-RANGE: Voice TTS có nhãn slider `Thanh âm lượng` ở8viewEN
   và8viewZH trong CI. Hai field definitions lưu key chưa có namespace;
   renderer chung đã hỗ trợ key đầy đủ. Chỉ sửa hai key thành
   `voiceUi.field.volume_percent.label`, không sửa renderer chung.
3. NLR-SUBDUB-EXTENSION: banner có hai CTA và nội dung hardcodeVI,
   cần dịch toàn khối bằng dictionary riêng, giữ URL/href/download,
   layout, thao tác và các con số đang hiển thị. Không mở hoặc gọi
   tiện ích/provider/giá/ví trong kiểm thử. Packet chuẩn bị riêng.
4. NLR-SUBDUB-READABLE: đo màu/chạm/focus của chính banner qua HTTP
   component trước. Chỉ BUILD nếu có RED đo được; không tự đổi style.

Hai bước đầu SIMPLE, có thể giao đề xuất độc lập cùng các bước đã
READY. Mọi worker chỉ trả OLD/NEW, không cùng ghi file; root tích hợp
theo thứ tự sau khi đối chiếu. Một branch/PR cho batch, motion cuối.

## Allowlist và bảo vệ

Ứng dụng: `static/portal/portal.js`, `portal-i18n.js`; CSS chỉ được mở
cho bước4 sau bằng chứng RED và phụ lục trước BUILD. Tests/fixture/
helper historical hữu hạn, tài liệu/Tester/CI registration được phép.
Không đổi tên hoặc chữ ký helper. `displayName()` chỉ có hai consumer
ứng dụng cùng tệp: `renderHeader()` và `renderDashboardWorkspaceSummary()`.
Những nơi này chỉ đổi fallback, không đổi guard, account, data hoặc API.

Cấm Bot/engine/provider/wallet/PayOS/ENV/secrets/schema/production data,
backend, auth logic, upload, giá/thanh toán và motion. Không gửi worker
artifact CI, fixture/API/login responses hoặc dữ liệu tài khoản; chỉ
fixed public UI source/approved copy/fullMAP. Giữ10state có sẵn,
không đọc/chạm state LOCALE-CAMPAIGN.

## Checklist

- [x] Đối chiếu CI hiện tại và đọc source xác minh nguyên nhân NLR-01/02.
- [x] Test actual renderer12case RED9fail/3pass,không lỗi khởi tạo;
  sau hai corrections đủ12/12 trong nhóm83observations.
- [x] Hai worker4ExtraHigh đầu trả đúng records, verify=NOT_RUN.
- [x] Contract/copy/bannerRED3locale,hai session độc lập trảexact;
  sau đó hai phiếu correction,0worker codefail.
- [x] Raw-source acceptance BASE+exactrecords; các assertions/pins cũ
  giữ qua inverse hữu hạn, unknown bytes/keys không bị che.
- [x] Browser3locale×2theme×mobile/desktop, labels/Tab/focus/chạm/
  không tràn và mọi href/values/limits/disabled/guards giữ nguyên.
- [x] Review gộpC0/I0/M0; không rerun bởi reviewer.16Pythonstatic
  đạt,compile/syntax/diffexit0;7harnessrecovery56/56.
- [ ] Docs/Tester/provenance → exact-headCI → merge/tree → Webdeploy →
  runtime/assets/receipt. Signed UI/fullauth/device/Safari vẫn riêng.

### Phụ lục CI45773932118 — test chọn nhầm selector

CI ở HEADa20f38fe qua nhóm hồi quy/bridge/ComposerAPI nhưng critical
contracts dừng1fail/134pass; authenticatedQA bịskip. Test
`test_primary_actions_use_the_accessible_dark_teal_and_readable_on_action_text`
đọc suffixselector của banner trước selector nút chung. Local đúng
testcase RED1fail; cùng testcase với CSS BASE1a57 bất biếnPASS.
Phụ lục Issue689/comment7185636101 ghi trước sửa.

Chỉ mở1dòng regex trong `tests/test_teal_cyan_ui_foundation_contracts.py`:
neo đầu selector vàMULTILINE; không đổi token/nền/chữ/contrastassertions,
không inversephysicalCSS,không sửaứng dụng/fixture10records/pins.
Đây là QAparser/ngườiđiềuphối,0workercodefail. Chạy lại đúngfile ảnhhưởng,
native-source guards rồi cậpnhậtdocs/provenance vàcùngPR812;CI mới
phải đạt trướcmerge/deploy. Không trộn CVN proposal vàoNLRrelease.

Lệnh đầu: `node --test tests/native-label-recovery.test.mjs`.
Kỳ vọng RED9fail/3pass trước sửa; số thực tế phải được ghi, không
đổi assertion để ép trùng dự đoán. Sau sửa12pass/0fail/0skip.
`node --check` cả hai JS và `git diff --check` phải exit0.

Catalog `/features`, Free Prompt Gallery và Admin còn các câu cũ
trong artifact; giữ backlog đúng wave, không sửa ké trong NLR-01/02.
Store install destination và tính đúng của claim giá tiện ích chưa
được chứng minh; localization không được dùng để đóng các gate này.

## Phụ lục NLR-SUBDUB-EXTENSION / READABLE trước BUILD

Audit componentHTTP12view VI/EN/ZH×light/dark×375/1440,252samples:
108quan sát màu dưới4,5:1,min1,02775 và24touch observations dưới44px.
Hai link đều cao24px. Không pageerror/requestngoài/tràn. Đây là
observations lặp, không phải132lỗi độc lập. Mở scopeCSS riêng banner.

GET link ChromeWebStore hiện tại trả301 về trang chủ, không có mã
extension tronghref; không thể dùng làm CTA cài sản phẩm. Gói tải
hiện có `/api/v1/live-translate/extension-download` trả200ZIP21.873byte,
CRC toàn bộ9tệp đạt,manifestV3,đủ7tệp bắt buộc. Không cài/chạy extension.
Chỉ bỏ link Store sai; giữ downloadhref/filename, không xóa tính năng.
Hai con số mức cước đang hiện có source/test riêng; chỉ dịch lời,
không sửa hoặc kiểm hành vi thanh toán trong batchUI.

Worker3 trả đúng hai record: thay nguyên khối `extensionBannerHtml`
bằng cùng một banner có13key bản dịch VI/EN/ZH; chỉ1downloadCTA; giữ
ba bước cài/đăng nhập/số dư. Bỏ lời hứa hoạt động “mọi tab” và câu
liên kết số dư tự động không cần cho cài đặt. Hướng dẫn kỹ thuật dùng
tên điều khiển Chrome thật ở một details đóng mặc định; không tạo ô
giải thích trống. Không thêm sự kiệnJavaScript hoặc thay downloadAPI.

Worker4 trả một insertionCSS riêng:
`.portal-subdub-hub .portal-subdub-extension-card` dùng surface/ink/
muted/border/action tokens; phụ kiện badge/step dùng surfaceStrong.
Stepgrid minmax(min(100%,260px),1fr),gap16px;step12px;body14px/1,6;
link vàsummary≥44px;focus2px vàtokenfocus có!important để thắng
shorthandchung. Headercopygrow; chỉ đổi màu/geometry của chínhbanner,
không đổi palette hoặc styletrangkhác. Primarybutton giữ rolemàu
sángaction/onaction,tối rail/railtext; không nối globalselector.

Hai phiếuoutput-only không ghi source và không trùng anchor. Sau nhận,
root tích hợp theo4+1+2+1=8records rồi verify gộp một lượt. Testbanner
phải RED3locale trướcBUILD; sau sửa đủ13keys/39values/1href chuẩn,
details/nativekeyboard;12browserviews với text≥4,5,focus≥3 và44px.
Không bấm nút tải/cài trong QA; ZIP được kiểm riêng chỉ-đọc.

Spec/QA lỗi do người giao không tính worker codefail. Bốn tasks này
không mở auth/business/provider/wallet/ENV/data/motion. Contract được
cập nhật cùng comment7184533142,không tạotrackerkhác.

### Điểm nối QA trước tích hợp

Fixture mới khóa8OLD/NEWrecords và fullsourcehashBASE/sau của3tệp.
Helper inverse mới JS/Python chỉ đảo8record đó, giữunknown/partial/
duplicate và14dictionarykeys (13banner+1guest). ReaderComposerhistorical
gọi inverseNLR trước inverse53recordcũ; snapshot cũng đảo14key trước.
Không đổi assertion hoặc sourcepin39+14recordcũ.

RawacceptanceComposer không được chiếu nguồn hiện tại: dựng
BASE6ec003db+53record, kiểm pin cũ, rồi nối đúng8recordNLR áp dụng
cho cùngfile và kiểm pinNLR. Sau đó so fullrawphysicalbytes. Test mới
NLR luôn đọcraw, khônginverse. Đăngký3NLRtests trongqualityworkflow.
QAhelper import/historicalcomposition không vào applicationbundle.

### Hai thiếu sót spec được đo sau tích hợp — trước correction BUILD

Bốn workerR1 trả exact8records, không codefailure. Nguồn vật lý gộp
46case có44pass/2fail: dashboardVI/ZH hiện “there” vì người giao dùng
`dashboardText("summary.guest","bạn")`, nhưng helper này nhận params,
không nhận fallback. Chuỗi `"bạn"` bị i18n coi là locale không biết.
Giữ test12case; worker correction chỉ đổi đúng callsite thành
`uiText("dashboard.summary.guest","bạn")`, không sửa helper/dictionary.

Browser12view có6quan sát paragraph trong details tối đạt4,4696:1;
mọi touch/focus/link/nativecopy khác đạt. Computedcolor rgb131,165,173,
background15,61,71; matched rule dark `.portal-page :is(...,p,...)`
ghi đè rule mới. Mộtview chẩn đoán tái hiện. CorrectionCSS thêm đúng
`:root .portal-page.portal-subdub-hub .portal-subdub-extension-card
.portal-subdub-extension-guide p { color: var(--portal-ink); }`,
không đổi nền/font/bố cục hoặc rule chung.

Hai corrections output-only4ExtraHigh độc lập, append2amendments riêng;
8records gốc bất biến, tổng10. Pin source sau cập nhật, inverse đảo
amendments trước8gốc; rawacceptance nối cả hai sau pin cũ. Các cổng
testnguồn/greeting và12view cuối giữ nguyên, không nới4,5:1.

Nhóm ảnh hưởng83case có76pass/7harnessfail do các bộ test cũ trích riêng
rendererSubDub mà không cấp dependencyuiText mới của banner. Sửa setup
chỉ thêm fallback-copyfunction ở bảy testauthoring/semantics/originalaudio/
reviewedit/reviewvolume/voicegroups/hubpresentation; giữ rawsource,
mọi assert guard/draft/volume/ARIA và cấu trúc. Không dùng các stub đó
để nhận nativecopy; testbanner mới chạyactuali18nVM ở ba locale riêng.
Không sửa ứng dụng hoặc assertion để làm xanh lỗi harness.
