# Đổi kích thước ảnh — nhãn Tùy chỉnh đúng ngôn ngữ

SPEC_ID=IMAGE-RESIZE-CUSTOM-SUBTITLE-20261118.
BASE_SHA=979b80d22a90368ec97547937e219ccbd3a02deb.
BRANCH=codex/image-resize-subtitle-20261118;TRACKER=Issue689.

## Phạm vi và worker

Antigravityc9f5fcd9-c2aa-4200-a99c-0bd07455af77/R1 trả đúng hai
phép thay thế nội dòng trongportal.js. Rootđọc/đối chiếu một lượt.
Chỉ tokencustom/rỗng/thiếu có fallback được bản địa hóa qua khóa sẵn có
field.resize.preset.custom:VI Tùy chỉnh,EN Custom,ZH 自定义.
Không thêm khóa i18n/hàm hoặc đổi chữ ký/dữ liệu lưu.

Hai consumer:renderImageOperationCards và nhánhisResize trong
renderImageHistoryOperationCards. Tỷ lệ/unknown/customer strings giữ
literal,thoát HTML bởi safeText hiện hữu. constpreset cho thẻ không
phảiResize giữ nguyên. Không đổi form/quyền/actions/kíchthước/UUID/
thờigian/tênfile/download/auth/backend/API/ENV/data/money/styles/motion.
Mộtappfile đúnghai thay thế;150appfiles khác giữ.

## Bằng chứng đã đo

BASEactualfullrenderer8tests:4PASS/4RED,2510.3674ms.
RED:RSC01custom,RSC02rỗng,RSC03thiếu/undefined,RSC06cùngVMđổilocale.
ProtectedPASS:RSC04chíntỷlệ,RSC05unknown/customer/name/escape,
RSC07nonResizehistory,RSC08frozeninput/context/wholeHTML/UUID/state/
geometry/date/downloads. Chỉđổi tokencuối,không thay toàn phụ đề.
VIouter"Đổi canvas" vẫn là gapcopykhác,chưa nhận toàn trang sạch.

Exactscope151files:1changed150protected,2canonicalsubstitutions.
Scope raw5850ab73f2cfe0845ef7f93c9b7ce1078fe083500b44fb98182593908bb1a061.
Authorityraw32a2ba6daa567d9e9aee9513de21fcaa3b509fb435f3e18715cedd3319332695.
CandidateportalLF845b1e4e37b6863f3d6f0d939a548f5056719f671877d4e039361c64dfbbe5c2.
Rootreplay từng có lỗi chép ngoài scope ở ô dung lượng,đã khôi phục
trước scope gate/test/native;scope final bằngBASE+exactproposal.
Không tính lỗi replay này thành lỗi Antigravity hoặc sửa nghiệp vụ.

## GREEN và cổng còn mở

Một nhóm24tệp436NodePASS/0FAIL,38860.0317ms,gồm8actualRSC và2source.
No passinggroup rerun. Fullphysicalrenderer kiểm hai consumer3locale,
sameVMlocale/frozencontexts/controls/ratios/customer/nonResize/downloads.
Finiteleaf đúng2substitutions chỉ ở biên lịch sửEnhancemetadata và
ownsource rawcomparator;goldenhash/assertions/unknownoutside giữ nguyên.
Không globalrendererprojection hoặc forwardreplay làm acceptance.

Native12views thuộc2routes
với4failedoperationmetadata/account trongDBtạm,nooutput/noimagebytes.
Đây là dữ liệu QA mới của server thật,không phản hồi giả hoặc tạo ảnh.
Root phải đọc đầy đủ nativeprep/lifecycle trước binding/execution.
Docs/originalcomparison/Tester/prepush/provenance/CI/treeeq/deploy/
runtime/assets/receipt vẫn riêng. Không nhận PNGcuối/signedproduction/
device/Safari/wholelocale/AX/motion hoặc goalcomplete.

PROVIDER_CALLS=0;WALLET_MUTATIONS=0;ENV_PRODUCTION_CHANGES=0.

## Native failed — prerequisite hiển thị đã xác định

R1/R2dừng trước0case accepted,sau1login;allactualmetadata/labels/form/
capabilitiesđúng,0app/console/dialog/egresserrors,coredata/sourceheld,
13ownedstopped0. R2diagnostic định vị predicate visibility,chưa có
geometricwitness nên không kết luận appbug.

R3actualcenter-scroll giữ mọiassertion vẫnfail:VI375Resizecustom
subtitlex105,y463.21875,width216,height23.09375,2textranges,
insideViewportfalse/unclippedfalse/hittrue,allancestoropacity1.
Giả thuyết nearest-scroll không đủ đã bị bác bỏ;không sửa app theo
giả thuyết đó. Nguồn thực portal.css1241 épwhite-space:nowrap/
overflow:hidden/text-overflow:ellipsis,đã có trênBASE.

Parent vẫn FAILED_NATIVE,không nhận436Node là full UI acceptance.
Phụlục prerequisiteIMAGE-RESIZE-SUBTITLE-READABILITY-20261118 trướcBUILD:
giữ2enumJSedits;thêm1CSSrule duy nhất trongportal-theme.css cho
card-subtitle hai routeResize/history. Allhistorysubtitles được phép
xuống dòng/tăng chiều cao tự nhiên;không đổi text/font/width/metadata/
form/rights/otherroute. Allowlistcombined2appfiles/149protected.
AntigravityR1 được giao outputonly,từCSS/MAP công khai;
CSSAGYR1fd4ec668-6b48-4bbf-8726-848d3c2f37ee đã trảexactoneaddition,
Rootreviewonce và áp đúngrule;chưa nhậnnativeGREENmới.
Không tăngtimeout hoặc làm yếu visibility.

Childauthorityraw48d3a038e51e355b15d24026d7585c09b42477634f424985f9e2c7176e6cfd50.
CombinedscopeBASE+2JS+1CSS:2appfiles/149protected/3canonicaledits,
rawb02219dbd92618622fc7fe8a96c7e332f55204df6983ee8e9984d1c577cfa4dd.
Candidateportalgiữ845b1e4e…;themeLF9706f04bc230531f2e4bb77a6bb0c715061711cd33ca8510104859e25285639f.

WrapsourceBASEcó1missing-ruleRED,1inversePASS;authoritytest ban đầu
đọc nhầmportal-theme thay vìportal.css,Root sửa duy nhất nguồn đọc
vàchỉfailedauthority1PASS464.1862ms. Đây làQA/specfault,khôngworkerfault.
Sauapply:nhóm6tệpCSSaffected56PASS/0FAIL19071.8945ms.
Không chạy lại436enumtests. Newfinitewrapleaf tạiColor historicaltheme
boundary/ownsourcecomparator;oldhash/assertions/unknownoutsideheld.
FreshnativeR4 sẽ giữ đủ12case/48visibilitywitness,thêmcomputedwrap
assertions vàcombined2sourcepins,khôngépDOM/CSS/APIđểgiảPASS.

## Kết quả nghiệm thu cục bộ cuối — R5

Phạm vi cuối thay thế mốc một tệp ở đầu báo cáo: hai tệp ứng dụng,
149 tệp bảo vệ, đúng ba thay đổi chuẩn (hai JS, một CSS). Không mở rộng
thành dọn toàn trang; chữ “Đổi canvas” vẫn thuộc mục kế tiếp.

R4 giữ nguyên trạng thái lỗi: đạt một màn VI375 Resize rồi chờ sai
assetVaultReadState tại History. integration.js15569 không tải Kho tài sản
trên History;15633 chỉ tải lịch sử. Root sửa đúng hai điều kiện QA trong
R5, không sửa ứng dụng, không tăng thời gian hoặc làm yếu kiểm tra chữ.
R4 dừng17tiến trình sở hữu về0; không dùng màn R4 làm bằng chứng R5.

R5 thực chạy đủ12màn VI/EN/ZH ×375sáng/1440tối ×Resize/History.
48phụ đề có đầy đủ vùng chữ trong viewport, không cắt, nhận hit, mọi cha
hiển thị; computed normal/anywhere/visible/clip đúng.48ảnh thẻ đã lưu;
Root xem ảnh VI375Resize,EN1440History,ZH375History trực tiếp.
Nhãn/tỷ lệ/customerliteral/metadata/ownership/form/actions giữ nguyên.
0page/console/dialog/cleanup/egress/unexpectedwrite/overflow errors.
Ba đăng ký mới,ba đăng nhập; audit cũ đúng từng hàng,thêm đúng3login,
schema/coredata/151source/binding/hai fixture/scope giữ.
28tiến trình sở hữu đã dừng,còn0.

Native summary SHA256:
2de06bf4bfd069ba8ceb6d122e68968688679c99b85e857b255e9a1672b05e88.
Isolation summary SHA256:
8484af9b050510839ed5ab1d7d0cf85e0231f67f3f3895e07c2d4a0d3795324a.
Không chạy lại436/56nhóm đã đạt. Các lỗi QA không tính thành lỗi worker.
CI/merge/deploy/runtime/assets/receipt vẫn là cổng phát hành riêng.
LIVE_PASS=NOT_TESTED;không nhận signed production/finalPNG/wholegoal.
