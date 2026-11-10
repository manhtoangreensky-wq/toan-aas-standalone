# Trang danh sách/chi tiết kế hoạch — nghiệm thu UI

TASK=VIDEO-SAVED-DETAIL-UI; LOCAL_ACCEPTANCE=PASS; DELIVERY=PENDING_RECEIPT.
BASE_SHA=652af67d8ba4706718f458ee1b26ad62bcc0b8ef; Issue689.
Branch=codex/video-saved-detail-ui-20261111. No full-goal completion claim.

## Hành vi thay đổi và phần giữ nguyên

List bỏ intro/số liệu lặp và bảng giải thích ranh giới; form tạo/thư viện còn đủ.
Detail bỏ các đoạn mô tả cách hệ thống được xây và bảng giải thích lặp. Ba dữ
kiện trạng thái/phiên bản/số cảnh giữ nguyên, chuyển thành dòng gọn thay ba ô cao.
Chips chỉ bỏ chính xác metadata từ hai nguồn tự tạo đã nhận biết; thẻ khách/
unknown/lookalike/prototype và trường sửa thẻ/dữ liệu gốc giữ nguyên. Hai marker
nguồn mâu thuẫn thì không đoán, giữ dữ liệu hiển thị. Raw internal-tag editing
semantics là bước sau, không coi lọc chips là đã dịch/migrate trường dữ liệu.

Chữ/nhãn/metadata ở giao diện sáng dùng semantic tokens hiện có, ô thời lượng
dùng bề mặt sáng phù hợp, không thêm bảng màu. Input/select/textarea mobile tối
thiểu16px; desktop/dark giữ vai trò sẵn có. Eyebrow trang trí ẩn đúng hai feature;
nhóm điều hướng UUIDdetail dùng khóa page.title sẵn có theoVI/EN/ZH. Không đổi
renderHero hay chữ ký/hàm dùng chung.178catalog keys/values giữ nguyên.

App allowlist:portal.js (5renderer spans+1section data leaf),portal-theme.css
(55dòng scoped append). Backend/auth/CSRF/session/integration/normalizer/rights/
schema/DB/ENV/provider/wallet/PayOS/Bot/route-engine/motion/service-worker/deploy
workflow và dữ liệu khách không đổi.18protectedpaths và exactworkerbytes đạt.

## Worker và test history

3Antigravity3.8FlashHighR1 độc lập, output-only; serial apply. LISTexactR1;
CSSexactR1, R2thêm min-height0 do coordinator bỏ sót min-height106px nền cũ,
không tính lỗi thợ. DETAILR1 sai một OLDanchor đóngspanthayp; R2sửa đúng một
descriptor, NEWcode/7records khác giữ;1genuinehandofffailure, không takeover.
READABILITYR1 bổ sung font/theme gaps đã đo; SECTION-LOCALER1 một display leaf.
Mọi code ứng dụng từ outputworker, không sửa trực tiếp thay thợ.

RendererRED12failed/24passed. Sau exactpatch,36newpassed;9assertions cũ còn đòi
boilerplate bị Owner yêu cầu bỏ. Chỉ đổi7visibilityassertions sang absent trong
khi vẫn kiểm literalcatalog,2intro-label checks sang create-formtitle có thật;
không bỏ action/field/data/readonly/history/hash assertions.3ambiguous tagchecks
thêm;12affectedpassed/61retained. Sectionlocale3RED->3GREEN.76acceptedcumulative;
finalCI chạy cả76fresh. SourceNode syntaxexit0.

BASE/candidate protocol48views:1392interactive tagattributes+labels+values+
buttons/rawcontext identical,digest573c42cedbd9f7e89892bb4f135fea0c59ad044a031ddc8c469dba64b77b40ed.
Finalsectionleaf chỉ display data, không can thiệp control markup hoặc raw data.

## Actual native / không replay lưu

NativeA54views:15pass/39fail,1332storedfieldmatches;24mobile detail views có15px
inputs.15lightviews dừng ở paletteharness assumption về gradientbody, nhưng dữ
liệu cũng chỉ rõ lỗi thật14label/supportsamples/list và50/detail ở1440, min1.26533.
Không gọi lỗi chữ thật là lỗi giả. Dataset6plan18scene/quickcheck/evidence giữ,
72ownedJobprocesses->0. Executedharness copies retained before correction.

NativeB chỉ chạy39failedviews;15dark cases không ảnh hưởng giữ nguyên bằng
source/rule comparator.39pass ->54aggregate(18list/36detail),1332fieldmatches.
2718recheckedtextsamples min5.331309340518602:1,0indeterminate;summary320max54px,
primarybuttonmin44px,57ownedJobprocesses->0. Originalevidence và copiedDBhash
ffe814d2a5b4fcbf45e2dc330bab577edbec4a5eb881a3b2d1799104e5bedf44 không đổi;
6plan18scene,quickcheckok. Root/body flags+colorScheme và solid editor palette
được đo; decorativebodygradients giữ observation/visualreview, không tính thành
numericbodytext contrast. Không nới ngưỡng4.5 hoặc bỏ indeterminateTEXTsamples.

Section supplement6views(3locale×320/1440) passed,0compose/save; breadcrumbs
không rawEnglishgroup.22ownedJobprocesses->0. Không rerun54layout/data cases.
Bodygradient visualreview:VI320light/dark,ZH1440light; focus hiện rõ và editor lên
trước các ô thống kê cũ.0egress/.env/media/provider/wallet/production access.

## Giới hạn và thứ tự tiếp theo

Header diagnostics quan sát9nhóm IDfield bị lặp trongBASEform, scene-title
label.control không trỏ owninput. Đây là lỗi accessibility có sẵn, controlparity
chứng minh không phải regression của patch. Ghi task namespace ngay sau đơn vị
này; không nhận mọi label association đã đạt. Rawtag-editing/old-record display,
titlelimits/otherplanners/stale-retry/auth/device/signedproduction và motion-last
vẫn mở. Không suy video/provideroutput hoặc realcustomer session LIVE.

Ops/original-feature/canonicalcase/Tester/filemetadata/provenance phải đủ trước
push; finalCI/exactHEADmerge/exactSHAdeploy/runtime/assets receipt trên Issue689
là trạng thái giao hàng, không thay bởi snapshotlocal này.
PROVIDER_CALLS=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_MUTATIONS=0;ENV_MUTATIONS=0;
LIVE_PASS=NOT_TESTED(signedproduction/device/provider);LESSON_CANDIDATE=NONE.
