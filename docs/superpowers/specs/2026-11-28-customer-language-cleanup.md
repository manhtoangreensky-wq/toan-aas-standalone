# Tài khoản và chọn ngôn ngữ — lời gọn, dễ dùng

BASE=2817dd9d221e04aa45945165ae60d5838cf9d920;
branch=codex/customer-language-cleanup-20261128;
repo=manhtoangreensky-wq/toan-aas-standalone;Issue689.

PR824 đã giao:CI46139279275hai nhóm đạt,18trang/456bản ghi/456ảnh
đối chiếu;Webdeploy46141881531đạt,runtimeBASE/cây9807ba77đúng
nguồn.7tệpnguồn,8trực tiếp+8theophiên bản+17cacheđúng;receipt
Issue689/7235804418vàPR824/7238862093đọc lại đúng,bốnôPRđãtick.
Đợt mới không làm lại các bước đó hoặc giả sử toàn goal đã hoàn thành.

## Phạm vi và thiết kế đã chọn theo quyền tự xử lý trong goal

Đổi lời cố định của tài khoản/thiết lập, bỏ đúng một dòng tóm tắt hồ sơ
đang lộ `vi · Asia/Ho_Chi_Minh · gradient`, và làm gọn màn hình chọn
ngôn ngữ hiện có. Giữ các trường chỉnh sửa ngôn ngữ, múi giờ, ảnh đại
diện, dữ liệu hồ sơ và mọi điều kiện quyền. Không xóa dữ liệu.

| Spec | Kết quả chính | Phạm vi | Mở bước sau |
|---|---|---|---|
| CL-ACCOUNT-LABELS |10khóaVI/EN/ZH tự nhiên,không nhãnWeb/Phiên |Giá trị trongportal-i18n.js |Chỉ khi đọc/renderer/controlsđạt |
| CL-ACCOUNT-DEFAULT-ROW |Không hiện dòng mã mặc định,giữ biểu mẫu/hồ sơ |MộtaccountRowtrongrenderAccount |So dữ liệu/điều khiển không đổi |
| CL-LANGUAGE-SELECTOR |Chỉ chọn ngôn ngữ vàlưu,khôngthẻgiảithíchthừa |renderInterfaceLocaleNavigator+5khóacũ/1khóamới |VI/EN/ZH,3lựachọn/quyền/ARIAđạt |
| CL-RELEASE |Tài liệu,kiểm đúngnguồn,gộp,cập nhật Web,đối chiếu |CùngmộtPRsaukiểmgộp |Khôngđóngtoàngoal |

Ba worker chỉ trả đề xuất trong thư mục riêng. Hai phần tài khoản độc
lập với hàm chọn ngôn ngữ;không ai ghi chung ứng dụng. Antigravity4
ExtraHighphiênCLIhiệncó,khôngđăngnhậplạihaykiểmtàikhoản. Rootghép
cơhọcsaukhinghiệmthu;chỉtựsửađúnglỗisauhailượtsaitrùngtiêuchí.

## Câu tài khoản/thiết lập

| Khóa | Câu VI đích |
|---|---|
| page.account.description |Quản lý hồ sơ, cách đăng nhập và bảo vệ tài khoản của bạn. |
| page.workspaceSetup.description |Chọn mục tiêu và cách làm việc để nhận gợi ý phù hợp. Bạn có thể thay đổi sau. |
| setup.webNative |Tùy chọn của bạn |
| accountCenter.profile.upgradeEmailHelp |Thêm email và mật khẩu cho tài khoản Telegram bạn đang dùng. Email phải chưa được sử dụng và không làm gộp tài khoản khác. |
| accountCenter.profile.unlinkedBody |Bạn vẫn có thể dùng ứng dụng khi chưa liên kết Telegram. |
| accountCenter.profile.profileFact |Hồ sơ |
| accountCenter.profile.dataControlsLink |Quản lý thông tin của bạn → |
| accountCenter.profile.sessionFact |Đăng nhập |
| accountCenter.profile.sessionLabel |Đăng nhập |
| accountCenter.profile.canonicalFact |Liên kết Telegram |

Các khóa có lịch sử ở PR824 được ghi rõ trong phiếu. Đây là đổi lựa chọn
câu chữ của Root sau quan sát đầy đủ,không tính worker sai khi đã làm
đúng câu cũ được duyệt,không reset bộ đếm lỗi cùng tiêu chí.

## Trang chọn ngôn ngữ

Giữ hero/settingsNav,một formvớithẻtiêuđề,fieldset/legend,ba radio
vi/en/zh,tênngônngữbảnđịa,đangdùng/lựachọn,nútlưu,noteid vàhai
đườngvềtài khoản/bảo mật. Không mở thêm ngôn ngữ hoặc đổi cách lưu.

Bỏ khối intro lặp,nội dung reviewed lặp trên từng lựa chọn,các kicker
không cần thiết,bốn thẻ ranh giới kỹ thuật và phần liệt kê bốn ngôn
ngữ chưa chọn được. Hai liên kết footer đang nằm trong thẻ bị bỏ phải
được giữ ở footer riêng,cùng thứ tự. Không giữ khung trống.

| Khóa | Câu VI đích |
|---|---|
| page.interfaceLocale.description |Chọn ngôn ngữ bạn muốn dùng trong ứng dụng. |
| interfaceLocale.formLegend |Ngôn ngữ hiển thị |
| interfaceLocale.formHelp |Chọn một ngôn ngữ rồi bấm Lưu ngôn ngữ. |
| interfaceLocale.saveHelp |Lựa chọn này không dịch hoặc thay đổi nội dung bạn đã nhập. |
| interfaceLocale.save |Lưu ngôn ngữ |
| interfaceLocale.saveBlocked (mới) |Chưa thể lưu lựa chọn. Hãy tải lại trang và thử lại. |

Lời title khi nút bị khóa phải qua khóa mới,không còn signed session/
CSRF. Điều kiện khóa giữ nguyên;không đổi capability,request,session,
auth,profilepayload,timezonethực hoặcbootstrap. Khôngdịchdữliệukhách.

## Nghiệm thu

- [x] C1:10câu tài khoản/thiết lập đúngnghĩaVI/EN/ZH;khônglộWeb/Phiên.
- [x] C2:Dòngmãmặcđịnhbiếnkhỏiphầntómtắt;mọitrường/giátrịformgiữ.
- [x] C3:Trangngônngữđủ3lựachọnvàcáclinkthật;khôngcácvùngthừanêu trên.
- [x] C4:Quyềnlưu,checked/disabled,action,route,id,ARIA,dữliệukháchgiữ;
  chỉtitlecốđịnhđượcdịch,keysetchỉthêm1khóađủbangônngữ.
- [x] C5:Rawprimary,browser390/1440,sáng/tối,đọctừnhiên vàpressure
  đúngphạmvi;kiểmgộpmộtlượtrồichỉkhépphầnlỗi.
- [ ] C6:Tài liệu/Tester/nguồn/CI/merge/Webdeploy/runtime/tài nguyên/
  receiptđúngbản;cácphầnchưachứngminhvẫnmở.

Cácmãthờigian/language/avatarStylevẫncòntrongdữliệuđúngnhưtrước,
chỉbỏdòngtómtắtkhôngcầnthiết.Khôngxóa/hidebiểumẫu,nhãntênriêng,
lệnhthật,thôngbáolỗithật hoặc dùngthaychuỗichungtrênHTML.

KhôngBot/route-engine/provider/ví/PayOS/ENV/dữliệuthật/motion.
PROVIDER_CALLS=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_WRITES=0.
Ghi chú mặc định workspace và các mục lifecycle/thiết bị/offline/phiên
production vẫn ở danh sách tiếp theo;motion giữ bước cuối.

## Lượt đầu và điều chỉnh tên ngôn ngữ

Ba worker đã trả đề xuất. Bản ghép riêng (chưa ghi vào ứng dụng) chạy
22 ca: 10 đạt, 12 ca trang ngôn ngữ dừng đúng ở tên bản địa. Các phép
so điều khiển, dữ liệu, quyền, vùng thừa và lời kỹ thuật trước đó đạt.

Nguồn cũ dùng `uiText("locale.vi/en/zh",...)`, nên tên được dịch theo
ngôn ngữ giao diện chứ không luôn là tên bản địa như Root đã mô tả.
Đây là thiếu đối chiếu của Root, không tính worker sai khi giữ lookup
cũ. Chốt rõ: ba tên lựa chọn cố định là “Tiếng Việt”, “English”, “中文”,
vẫn giữ `lang="vi/en/zh-CN"` và các giá trị radio `vi/en/zh`.

Giao CL-LANGUAGE-SELECTOR lượt 2 chỉ ba biểu thức tên trong đề xuất
lượt 1; không giao lại 6 câu dịch hoặc sửa phần khác. Không tính một
lượt thất bại giả cho worker; giữ bằng chứng 12 ca đang thiếu. Chỉ
kiểm lại đúng 12 ca trang ngôn ngữ, không chạy lặp 10 ca đã đạt.

## Nghiệm thu tại máy và phạm vi đầu vào kiểm tra lịch sử

Lượt2đúng3biểuthứctênđãđạt12/12;giữ10caseđãđạtlượt1thành
ledger22case.Vẫn16câudịch,48recordghépcơhọc,2tệpứngdụng.
Browseractual-shell42lượtVI/EN/ZH390/1440sáng/tốiđạt,0lỗi/tràn/
kếtnốingoài;đãchọnradio,gõtên,giữdisabledsavevàfooter/ARIA.
Ràđộclậpđúngdiff:APPROVE,khôngfinding.Khôngtựviếtlogicứngdụng.

Lượtảnhhưởnglịchsử142casecó134đạt/8lỗi:old134primarycó2fullsource/
keysetguardfail,old413historycó5failvànguồnAccountsnapshotdừngkhi
old413recordđãcóthayđổimới.Cácoldrenderer/nút/dữliệukhácvẫnđạt.
Khôngchạylạitoànbộnhómđãđạt.Chỉtạoleafinversehữuhạnmớiđúng
48record/16câudịch,chạytrướcleaf413cũ;oldfixture/hash/assertiongiữ.

Allowlistkiểmtra:tạofixturecustomer-language-cleanup-history.json,
helperscustomer-language-cleanup-historical.mjs/.pyvàpressuretestmới;
neoleafvàcustomer-natural-followup-historical.mjs/.py;neođầuvào
oldcustomer-natural-followup-copy.test.mjsvàhistorytest.Pythonreader/
oldtestkhácchỉđượcbổsungnếufailđãđotừsourcehiệntại.
Rawprimary22mớiluônđọcứngdụngthật,khôngdùnginverse. Khóamới
saveBlockedchỉbịbóctronginputoldtestkhiđúngtoàn48record/16giátrị;
nộidunglạbênngoàiđượcgiữđểoldguardtựbắt.

Đăng ký hai test Node mới và test Python hữu hạn vào đúng nhóm kiểm
tra sẵn có của `.github/workflows/webapp-quality.yml`; không đổi quyền,
trigger, giới hạn thời gian hoặc bước triển khai. Các reader cũ còn
khóa phần giải thích đã bỏ chỉ được neo đầu vào sau khi đo lỗi thực tế.

Đã đo thêm: nhóm Account Node có10/11đạt,đúng một case AC-01A/AC-01B
còn đòi câu noBotState đã chủ ý bỏ. Nhóm Python Navigator có4/5đạt,
đúng một case còn đòi bốn ngôn ngữ chỉ liệt kê,không chọn được. Cho
phép neo đúng nguồnPORTALcủa `tests/account-control-level-contract.test.mjs`
và `tests/test_interface_locale_navigator_portal_contracts.py` qua leaf
mới;giữ nguyên assertion/kỳ vọng và chỉ kiểm lại hai case đó.

Nhóm Python liên quan137case có136đạt/1fail:account-center vẫn đếm
profileDefaultsLabel trong renderer dù dòng tóm tắt đã chủ ý bỏ.
Cho phép neo đúngPORTALđầu vào của `tests/test_account_center_locale_contracts.py`
qua leaf mới,giữI18N/expectationcũ và chỉ chạy lạicasefail đó.

## Khép nghiệm thu cục bộ

Hai caseNode/PythonNavigatorđãfailed-onlyđạt;137Pythonliênquanđã
khép đúngcaseAccount1/1,giữ136kết quả đã đạt. NewleafNode10/10đạt,
Python4case có ledger nguồn thật2đạt,bộrecord hữu hạn2đạt;không còn
MemoryError,tránh giữ toànbundletrongtraceback. Bảyinputhookcũchỉ
thêmnguồnđầuvào,khôngđổiassertion/pin/fixture. Reviewerphầnmớichỉ
ràhistoryđãAPPROVE,khôngfinding,khôngràlạiứngdụnghoặclặptests.
Cúpháphaitệpứngdụng,py_compileappvànămtest/helper,diffcheckmã0.
Haihashứngdụngvẫnbằngbảnghépđãkiểm;C6vẫnchờbảnkiểmtrênkho/
gộp/cậpnhậtWeb/đốichiếuvàreceipt,khôngcoitoàngoalxong.

## PR825 — đầu vào Account/Dashboard cũ

Run46147192160/HEAD03c1915004521e3019039abf62b599370840761a
dừng ở đúng một caseZH của `tests/account-dashboard-plain-language.test.mjs`:
helpersectionWithlấy lần xuất hiện đầu của“登录方式”,nay trùng trong
herođãđổilời,nên trả sectiongiới thiệu thay vì mục phương thức đăng nhập.
Không phải mất nút hoặc đổi quyền.Thay sharedsectionWithsẽmởrộng
phạmvi không cần thiết;chỉ cho phép I18N đầu vào của filetestnàyqua
leafmớiđểgiữepochcũ,khôngđổiassertion/renderer/dữliệu/nút hoặc
haiappfile. Chỉ chạy lại caseZHfail;những case cũ đã đạt giữ kết quả.
Tài liệu phiên/prepush/metadata ghi lượt lỗi;haiWebprovenance tạo lại
sau chốt nguồn. Bản kiểm mới đúngHEADvẫn bắt buộc trước gộp.

## 29/11 — giữ nguyên thay đổi đồng thời trên main

MainđãnhậnPR826/a75ad840ca145e9a733febe012dd78b43df2772b.
AmendmentIssue689/7245441432ghi trước khi ghép:chỉhaiJSONWeb
do máy tạo cóxungđột.Tám tệp nguồn/testcủaPR826được giữ đúng
blobGitvàhashLF;workflowgiữnguồnmainchỉthêmhai lệnh testđã khai.
HaiappfilecủađợtlờivàBASEfixturebấtbiếnkhôngđổi;khôngsửalại
realtime/extension/settlementhoặcBot.Nguồnđãghép72374faf491f9e4dbbb9b1c66dfb46e060b2706c;
hiệuchỉnhtài liệu/metadatađãđorồitạolạihaibáocáoWeb.C6vẫnmở.
