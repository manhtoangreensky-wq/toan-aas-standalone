# Chỉnh ảnh — màu chữ hướng dẫn giao diện sáng

SPEC_ID=IMAGE-ENHANCE-LIGHT-STEP-COLOR-20261118.
BASE_SHA=c1fdd4bf35c8563d8dd15dc27619022d3e1b7350.
BRANCH=codex/image-enhance-step-color-20261118;TRACKER=Issue689.

Antigravity0ec097d5-5b46-48d8-9147-dfec771bdc07/R1 đã trả đúng
một addition CSS. Worker không chạy kiểm tra; các số zero tự ghi đã
được bác bỏ trong authority,không dùng làm bằng chứng PASS.
Root dùng lại proposal,không giao lại hoặc tự viết sửa ứng dụng khác.

Chỉ hai selector strong/span dưới .portal-page.portal-image-enhance
và html:not([data-portal-theme="dark"]) dùng color:var(--portal-ink).
Không sửa chữ,phông,kích thước,bố cục,quyền,form,dữ liệu hoặc motion.
Một tệp ứng dụng thay đổi;150tệp khác giữ nguyên.

## RED đã đo

Source3tests:2PASS/1missing-ruleRED,339.1789ms.
NativeBASE actualfullserver6views VI/EN/ZH375sáng/1440tối:
36computedcolorrows/36known/0unknown. Ba lightviews có18mismatches:
strongrgb(236,251,255),spanrgb(143,169,181) thay vì actualnode
--portal-ink #073a45. Darkcolors được lưu để khóa nguyên,không yêu cầu
darksemantic equality và không tính tỷ lệ WCAG từ nền gradient.
Root đã xem ảnhVI375steps thực tế trước sửa: tiêu đề rất nhạt.

Fresh3register3login12metadata/noassetbytes,0page/console/dialog/
overflow/egress/unexpectedwrite;oldauditexact+3login/schema/coredata/
source151/binding/fixture/scopegiữ,22ownedstopped0. Không tạo ảnh.

## GREEN đã đo

Một actualGREENgroup đạt6views/36knowncolors/0unknown,3lightviews
18nodes đều rgb(7,58,69),0mismatch;18darknodes color/textfill khớpBASE.
So sánh exact toàn capturedstylemaps,text,font,document-spacegeometry,
list/itemlayout,identity/capabilities/read/form/metadata đạt.
Không thay layout/wordwrap/font hoặc chỉnh dữ liệu để so sánh.
54metadata/help paintwitness cộng36steptextpaintwitness,24ảnh.
RootxemrawVI375lightsteps/EN1440darksteps/ZH375lightsteps.
Fresh3register3login12metadata/noblobs,oldregisterauditexact+3login/
schema/coredata/source151/binding/fixture/scopegiữ,22ownedstopped0;
0page/console/dialog/overflow/egress/unexpectedwrite/toast.

Nhóm16tệp357NodePASS/0FAIL,39843.4063ms,bao gồm3color/source tests
và các source/comparator cũ. Không rerun passinggroup.
QA chỉ thêm finiteleaf đúng một addition tại Resizeheight historical
themeboundary vàownsource rawreader;goldenhash/oldassertions giữ.
Acceptance fullphysicalstyle/renderer;không chèn CSS/state/response.
Nativebindings đối chiếu150protected với1exactcandidate theo scope.
BASEsummaryrawSHAfa371b16e4abc14d6c4295251204cd74027ca08ad751cceac9183e2f54104ecc;
GREENsummaryrawSHA718fb5f7503653673041ad75c784d65afedfd49f9ecf92d8df7483af4a58cbbe.

## Trước phát hành và gate còn mở

Chỉ color ở light được phép đổi;textfill chỉ đi theo color khi hai lượt
đều đo đúng quan hệ đó. Tọa độ viewport/scroll là quan sát tạm,không dùng
làm thay thế hình học tài liệu. Currentdocs/originalcomparison/Tester/
prepushREADY,case1664lines174217LFbytes/
SHAa888e07e5d1c9d65ee3fe15a67774e68586683c2416ab2d717e15728c9eec73c.
Metadata1PASS32deselected0.66s;helpersyntax/diffcheckexit0.
Sourceprovenance/CI/merge/treeeq/exactSHAdeploy/runtime/services/assets
vàreceipt vẫn riêng,không báo deployed từ localGREEN.

AuthorityrawSHA5d3257a1b37ae709ff293cab1fe6537f35d401ee386287d7644d757e90b4b581.
ScopeexpectedGREENrawSHAc3dfab448756fed423de345731d064e17c31f8a5be028537c7138a42fa4f1f92.
BaselineCSSLF153ae3f84afcd2b528ba762d307374df3f188a2e6e7867d51e2d4867329ced56.
ExpectedcandidateCSSLF00d5ec74c956509628f277be2d3d67863e158d452bebf6a1a4d336ef01b8dfa5.
Rootđọc đủ helper90lines,observer và383assembledlifecycle trước adoption.
AssembledSHA90dca668440284204e31cd434f3aab4471ca6486c0af4ead776202196bf58cb5.
NativeBASE vàGREEN tách binding/setup,dữ liệu mới;GREEN chỉ đọc safehashed
computedstyle evidence,không tái dùng auth/account/DB/log/session.

Không nhận wholelocale/AX/default-light-without-attribute runtime/
signedproductionUI/finalPNG/device/Safari/motion hoặc toàngoal.
PROVIDER_CALLS=0;WALLET_MUTATIONS=0;ENV_PRODUCTION_CHANGES=0.
