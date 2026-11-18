# Nén PDF — tiêu đề và mô tả đúng ngôn ngữ

SPEC_ID=PDF-COMPRESS-OUTER-META-20261117.
BASE_SHA=560377ad7de7c7ba647923c8dcb143f2022c26d5.
Branch=codex/pdf-compress-meta-20261118;trackerIssue689.

## Thay đổi và nguồn đề xuất

Dùng lại proposal Antigravity R1 đã trả ở phiếu17/11,không gọi lại worker.
Đúng năm addition trên ba tệp:hai mục metadata trong copyfast_pages.py,
hai nhánh exactroute /documents/compress trong helper title/description,
hai khóa/6giá trị VI/EN/ZH trong từ điển. Không đổi chữ ký helper hoặc
form/xử lý/giới hạn/quyền/dữ liệu.148tệp ứng dụng khác giữ,kểcảCSSResize.

Kỳ vọng độc lập:

- VI:Nén PDF / Giảm dung lượng PDF khi có thể. Tệp gốc được giữ nguyên.
- EN:Compress PDF / Reduce a PDF's file size where possible. The original stays unchanged.
- ZH:压缩 PDF / 在可行时减小 PDF 文件大小。原文件将保持不变。

## Các lượt đã đo

| Kiểm tra | BASE | Candidate |
|---|---|---|
| Renderer22ca |7PASS/15metadataRED,5196,8636ms |22PASS,5476,3336ms |
| ActualHTMLResponse3locale |3RED,2,93s |3PASS,2,31s |
| Neighboring shell |Không đổi3nguồnngoàiphạmviđãđốichiếu |12PASS,6,68s |
| Affectedsource14tệp |Không dùng số cũ thay lượt mới |127PASS/1QAFAIL,22112,3137ms |
| Chỉ assertion QAreader được sửa |N/A |1PASS,3124,3346ms |
| Chromeactualrendererfixture |N/A |6PASS,zeroexternalrequests/sourceunchanged |

Một lỗi QA là fixture mutation của Resize thay OLD nằm ngay tại đoạn
Compress mới có giữ OLDlàmneo. Comparator đã đảo hữu hạn đúng addition
Compress trước khi tạo mutation cũ;assertion/hash gốc không đổi,không sửa
appđểquaQA. Không chạy lại127ca đã đạt.

Các test mục tiêu đọc fullbundle vật lý. Bộ chuyển test sang CI chỉ đổi
đường dẫn/import/authorityfixture,giữ35assertionNode+14Python cùng hai SHA
authoritygốc. Testhistories chỉ đảo đúng5addition+2knowncataloguekeys ở
biên đọc riêng;unknown/outside/mutation vẫn được giữ/kiểm,không đổi loader
giao diện hoặc pageMetaSources toàn cục.

Chromefixture dùng renderer thật và CSS thật,không server/DB/auth/network.
VI/EN/ZH375sáng/1440tối,title/h1/description,selectownedfakePDF,nosubmit,
khôngoverflow/injection/pageerror/externalrequest. Đã xemVI375/EN1440/
ZH375rawscreens. TitleđúngkhôngđủnhậnwholeshellUI;mobilecardh2màunhạt
cần đo fullshellnative để phân biệt fixturecontext với lỗi thật.

## Cổng còn mở

Nativefullshell6READY trênDB/assettạm,CIexactHEAD,merge/deploy/runtime/
assetsreceipt vẫn riêng. Chưa cóPRmới cho đơn vịnày trước khi cácgateđạt.
KhôngnhậncompressedPDFcuối,signedproductionUI,device/Safari/toàngoal.
Web–Botparallelchỉsourcecontract/15offlinecharacterizationPASS,khôngsửa
engine/Bot/ENV/tiềnhoặcchứngminhâmthanhcuối. MotionM-FINAL01..06cuối.

PROVIDER_CALLS=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_MUTATIONS=0;ENV_CHANGES=0.

## Native đã chốt trước push

Một lượt mới actual localhost đạt6/6VI/EN/ZH×375sáng/1440tối:
firstHTML/bootstrap/title/description/header/herođúngliteralcanonical,
typedPDFGET1/items2mỗica,selectPDFsởhữu/Tabtớiôtìmnguồn,nosubmit.
Khôngoverflow/pageerror/console/dialog/toast/externalrequest/write.
Fresh3register3login12metadata/noblobs;exact3registeraudit+3login/
schema/coreproductdata/source151/binding/fixture/scopegiữ;22ownedstopped0.

Đãxem3rawscreensVI375đầutrang,EN1440tốiđầutrang,ZH375fullform.
Ởfullshellthậtcả12h2đềuopacity1/visible:lightforegroundrgb(7,58,69),
darkrgb(243,251,252),khôngtextshadow/filter. Ảnhfullshellkhôngcótìnhtrạng
h2trắngtrênnềntrắngtrongfixturethiếushell;khôngsửaCSSké.
Đâylàphépxem/màuthựctế,khôngđưa ra tỉ lệ contrast chưa tính.
Khôngchạylạinativeđãđạt;CI/pháthành/LIVEsignedoutputvẫnriêng.

## Đã giao18/11/2026

PR762 đã gộp2026-11-18T04:59:06Z sau CI44239130889 cả hai job SUCCESS
trên HEAD87f2071b1df9907daca2742b14bd463aa3775e64. Merge/runtime
6c8e2b227ba635d81dc713f6c25c77d260002e61; toàn bộ cây bằng cây đã kiểm,
treec1e157bcdf083a3f6c6ab8dcd6e82495b2b917eb, full diff exit0.
Deploy44241082812 SUCCESS1m6s. Ba verifier chỉ-đọc exit0: runtime/nguồn
đúng, ba dịch vụ active/running, health đạt, năm asset byte-exact.
Issue689 receipt6969229851 đã cập nhật bằng đúng ID/readback exact;
PR receipt6969611901. Các dòng “còn mở” phía trên là lịch sử đã được phần
này thay thế riêng về delivery, không đóng signedUI/PDF/device/Safari/motion.
