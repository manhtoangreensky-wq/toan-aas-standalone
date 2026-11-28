# Phiên rà lời tài khoản và chọn ngôn ngữ

ID=CUSTOMER-LANGUAGE-CLEANUP-20261128;product=standalone WebApp;
repo=manhtoangreensky-wq/toan-aas-standalone;Issue689;
branch=codex/customer-language-cleanup-20261128;
BASE=2817dd9d221e04aa45945165ae60d5838cf9d920.

## Phạm vi khóa và nguồn giao việc

Hai tệp ứng dụng,48record ghép từ đề xuất Antigravity4ExtraHigh:
15khóa cũ và một khóa mới,16dòng dịch VI/EN/ZH. Ba luồng đề xuất
độc lập;Root ghép cơ học sau nghiệm thu,không tự viết logic ứng dụng.
Lượt tên bản địa thứ hai chỉ sửa ba biểu thức còn dùng tên đã dịch;
thiếu đối chiếu củaRoot không tính lỗi worker.

Tài khoản bỏ đúng một dòng tóm tắt mã mặc định;giữ form/hồ sơ. Trang
ngôn ngữ bỏ các vùng giải thích dư,giữ ba radio vi/en/zh,tên bản địa,
quyền/trạng thái/nút lưu/ARIA và hai liên kết. Không đổi xác thực,
Bot,route-engine,provider,ví,PayOS,ENV,dữ liệu thật hoặc motion.

## Ledger nghiệm thu

| Case | Bằng chứng hiện có và giới hạn |
|---|---|
| CLC-COPY |22ca riêng biệt:10đạt lượt đầu+12affected-only sau sửa tên;không gọi là một lượt chạy toàn bộ mới |
| CLC-PROFILE |Renderer trước/sau giữ normalized data,controls,giá trị và nội dung khách;chỉ bỏ dòng tóm tắt;đã gõ trường hồ sơ |
| CLC-LANGUAGE |42lượt xem thực quaHTTP:3ngôn ngữ×390tối/1440sáng×7trạng thái;0lỗi/tràn/kết nối ngoài;radio,disabled,focus,ARIA,footerđạt |
| CLC-HISTORY |48record/16giá trị hữu hạn,mã bămfixture7b7447e638ed9f9dbf250ec4b544f7dd786758009fceb2c4c7b2746befd3dacd;đang khép các reader cũ sau lỗi đã đo |
| CLC-DELIVERY |Chưa phát hành đợt mới;phải kiểm đúng nguồn,gộp,cập nhật riêng Web,đối chiếu runtime/tài nguyên và đọc lại receipt |

Rà độc lập ứng dụng:APPROVE,không finding;điều kiện là khép bằng chứng
trình duyệt và đầu vào lịch sử. Trình duyệt42lượt đã khép. Đã xem ảnh
VI390trangngônngữ vàEN1440nút bịkhóa;không cần đổiCSS.

## Lịch sử kiểm tra và cách giữ bài kiểm tra cũ

Nhóm ảnh hưởng ban đầu142ca:134đạt/8lỗi,không lỗi ứng dụng mới.
Hai guard của primary cũ,5case lịch sử và một file account dừng khi
khởi tạo do lời mới. Chỉ thêm leaf hữu hạn trước epoch413cũ,không đổi
fixture,pin,kỳ vọng hoặc bài kiểm tra mới nhất đang đọc ứng dụng thật.

Leaf mới:10case Node chứng minh hoàn nguyên chính xác,giữ bytes lạ,
CRLF,thứ tự khóa và từ chối thiếu/đổi/lặp48record/16giá trị. Lượt đầu
identity10RED;green28case có4lỗi helper củaRoot;recovery13/13đạt,
gồm10case leaf và3snapshot cũ. Không tính lỗi helper thành lỗi worker.
Python3/4đạt,lỗi còn lại là MemoryError khi giữ traceback toàn bundle;
pressure dùng đúng bộrecord hữu hạn,failed-only1/1đạt. Bằng chứng
roundtrip nguồn thật và ba casePythonđã đạt được giữ,không sửa app.

AccountNode10/11đạt,đúng một case còn đòi phần giải thích đã chủ ý bỏ.
NavigatorPython4/5đạt,đúng một case đòi bốn ngôn ngữ không chọn được.
Chỉ neo đầu vào hai reader đó;assertion giữ nguyên. Các lượt khép và
kiểm liên quan cuối phải ghi bổ sung trước khi chốt nguồn.

Đã khép:AccountNodefailed-only1/1đạt;NavigatorPythonfailed-only1/1
đạt.Nhóm137Pythonliênquancó136đạt,đúngcaseAccountđếmnhãncũ
failed-only1/1đạt sau neoPORTAL.Quyền/logicứngdụngkhôngđổi.
Hai casePythonpressure ởinputhữuhạnđềuđạt;haicaseđốichiếunguồn
thậtđãđạtđượcgiữthànhledger4case,khôngcộnglượttrùng.

Reviewerchỉràphầnleaf/hookmới:APPROVE,khôngfinding;khôngràlại
ứngdụnghaychạytests.Cúpháp2appfile,py_compileapp.pyvànămtest/
helper,diffcheckđềumã0.Haifileứngdụngvẫngiữđúnghashbảnghép.
NhómmetadataWindowsphảigiữlỗinềnPOSIXđãđo,nếucònlỗimới
thìkhôngmởpush;Linuxtrênkhovẫnphảiquađủtrướckhigộp.

## Giới hạn còn mở

PR825lượt46147192160/HEAD03c19150dừng ở đúng một caseZH của
account-dashboard-plain-language. Helpertest chọn lần xuất hiện đầu
của“登录方式”trongherođãđổichữ,khôngphảimụcphươngthứcđăngnhập.
ChỉI18Nđầuvàofiletestcũnhậnleafmới;renderer/sectionWith/assertion/
haiappfilegiữ.Failed-onlyZH1/1đạt;bảnkiểmHEADmớivẫnbắtbuộc.

Chưa lưu thật hoặc mở phiên khách production. Không suy toàn bộ auth/
bản nháp/race/accessibility/thiết bị/Safari/offline/motion từ42ảnh.
Ghi chú workspace là đợt tiếp theo;motion vẫn cuối,toàn goal chưa xong.
PROVIDER_CALLS=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_WRITES=0.
