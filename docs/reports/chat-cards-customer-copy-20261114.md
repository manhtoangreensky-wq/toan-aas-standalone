# Hội thoại: thẻ dễ đọc, bỏ khối giải thích dư và khoảng trống

BASE `398cea1c4f6f6f256c646fa382a78563e66b8939` sau PR731 đã triển khai.
Một tracker Issue689,contract `6876292037`.
Hai phiên Antigravity độc lập trả thẻ/khối dư; cùng phiên A trả bổ sung CSS
sau review. Tổng4 thay đổi worker trong3 tệp ứng dụng, không tự viết lại.

## Người dùng thấy gì

- Bỏ khối giải thích triển khai không có thao tác ở root/chi tiết Hội thoại,
  không để khung thay thế. Phần gửi yêu cầu thật và chốt quyền vẫn giữ.
- Thẻ dùng chữ VI/EN/ZH cho cách soạn, trạng thái, ghim, ghi chú/lượt trao đổi,
  lần cập nhật, nút mở và hướng dẫn khi rỗng:20 khóa/60 giá trị mới.
- Tên/mục tiêu/thẻ khách viết không bị dịch hoặc lọc, kể cả chứa các từ kỹ thuật.
  Các giá trị vẫn escaped. ID,link,quyền,số đếm,lần sửa,thời điểm,mã trạng thái/
  cách soạn và mọi điều kiện cũ giữ nguyên.
- Khi chỉ còn biểu mẫu tạo mới trong bố cục, biểu mẫu chiếm trọn chiều rộng
  thay vì để một cột trống. Không đổi trang chi tiết/mobile hoặc cấu hình cột.

Không hứa tạo câu trả lời AI từ tính năng lưu nội dung thủ công, không đổi
engine/Bot/provider/ENV/auth/API/DB/ví/PayOS/motion hoặc bật quyền thực thi.

## Kiểm tra và sửa thiếu sót có bằng chứng

Candidate actual VM35case:BASE4PASS/31RED→35PASS. Checker đảo patch lượt đầu
tìm return rỗng quá rộng,được sửa bằng exactoffset;không sửa candidate,không
tính workerfault. B timeout được nối cùng phiên; không tự đăng nhập hoặc
đổi quyền. Nhãn guarded ban đầu trong phiếu của điều phối chưa đúng yêu cầu
Owner; amendment chỉ đổi thành “Chưa thể mở” / “Cannot open yet” /
“暂时无法打开”, giữ20key và cấu trúc. Đây SPEC_CORRECTION,workerfault0.

Permanent38case trước áp dụng3PASS/35RED; sau áp dụng38PASS, cùng consumer
boundary thành39PASS. Bắt lỗi locale/empty/five states/four modes/pinned/
permission/invalidID/customer escaping/numericfallback/language switch,
root/detail execution controls và exact old dictionary order.
Snapshot chỉ loại20 khóa và hai fullspan đúng hash,khóa lạ/giá trị bị đổi/
thiếu/đảo thứ tự/source ngoài phạm vi không được che bằng prefixfilter.

309Node affected đạt,9ChatPython đạt,syntaxhai bundle vàpy_compileapp exit0.
MetadataTester32PASS/1deselected:POSIXchmod600case đã biết không khớp Windows,
giữ nguyên case trênLinuxCI,không sửa skip trong mãtest. Case source đo
1212 dòng/135708byteLF,
SHA256 `e506d9c9aae2135e3c663d5e53d8cc2284ae4a0b812f68d9119495f5c15815fd`.
Không chạy lặp toàn bộ suite khi chỉ CSS bổ sung thay đổi. Bộ kiểm CSS trước
sửa1RED+1controlPASS; sau sửa2PASS,cùng comparator màu chữ PR731 thành3PASS.
Exactreplay4workerchanges/3appfiles,16protectedpaths giữ nguyên. Review lần đầu
C0/I1/M0,đóng I1 bằng CSS được giao worker+geometry; review bổ sung C0/I0/M0.

### Màn hình thật của dữ liệu QA tạm

BASE finite1viewVI375light dùngGET thật có5thẻ,aside còn1 và chữ cũ:
RED đúng yêu cầu;0overflow/lỗi trang/console. Không bootstrap giả.
Sau áp dụng:12root+12detail VI/EN/ZH×375/1440×sáng/tối,nhấp link thật,
GET chi tiết cùng owner,nhãn/dữ liệu/quyền/controls/locale/theme/ảnh đạt.
0tràn/lỗi trang/console/egress/productwrite,19ownedprocess dọn về0.

QA chỉ copy DB giả đã sở hữu,seed15 metadata rows hợp lệ (3owner×5),không
thêm bảng hay sửa schema. Row/schema fingerprints giữ trước/sau browser,
6plan18scene/version/idempotency và evidence gốc giữ. Lượt fixture cũ seed
guarded/UNKNOWN bị loader từ chối đúng,đã ghi SPEC_SAI của điều phối.
Native sửa fixture thành4 trạng thái chuẩn với một draft thêm cóID/tên riêng;
guarded/UNKNOWN làVM/permanent-boundary coverage,không gọi là positive ingress.
Lượt startup giới hạn60s không mở server được được giữ riêng,không tínhUI PASS.

Review phát hiện desktop sau bỏ aside vẫn giữ2track:
1440light,layout1088px/form604.546875px,onlychild1:RED geometry riêng.
375light/dark343/343px đã đúng. PhiếuCSS bổ sung chỉ một selector root/direct/
only-child với `grid-column:1/-1`,giữ nguyên prefixCSS849308byte/hash.
SauCSS:4VIroot375/1440sáng/tối đạt343/343 và1088/1088px,1detail1440sentinel
click thực giữ nguyên controls/status,0overflow/errors.13ownedprocess về0.
Không chạy lại24viewcopy đã đạt. Tổng evidence có phần chồng,không cộng làm
con số phủ toàn app.

Bằng chứng cục bộ giữ:
`chat-cards-permanent-red-nov14.log`, `chat-cards-affected-nov14.log`,
`chat-cards-scope-nov14.json`, `chat-cards-candidate-qa-nov14/aggregate.json`,
native `baseline-398-r3-valid`, `green-applied-r1`, `geometry-red-r1`,
`geometry-green-r1`. Chỉ công bố số đo,không đưa DB/login/API khách lên GitHub.

## Đối chiếu công việc và giao hàng

PR731 đã giao HEAD799b08e2,CI43584766006bothPASS,merge/runtime398cea1c,
deploy43585904925PASS. ReceiptIssue6896876023868/PR7316876024174.
Đợt này cập nhật receipt vào tài liệu trước nhưng không gộp mã cũ làm sửa mới.

Tester dùng nguồn case duy nhất và phiên riêng,giữ48P0/historicalremote/safety.
Docs hiện tại/gốc,metadata/provenance/exactHEADCI/merge/deploy/runtime/assets
của đợt thẻ sẽ có receipt riêng cùngIssue/PR;chưa có thì không gọi đãLIVE.

Vẫn mở: raw ISO thời điểm trên thẻ,Chatpagination,chi tiết/context/run/toast
và các route khác chưa theo locale;helpertextcontrast,toànAX/auth/device/
Safari/signedproduction/motioncuối. Hai phiếu ngày giờ/phân trang được giao
tiếp ở phiên output-only riêng,không nhập vào bản giao hàng này.

Web–TTS song song chỉ đọc:VPS không liệt kêvoice_tts trong allowlist thực thi;
không bật thêm hoặc gọi trả phí. Trang ready có thể chỉ là bản nháp được mở;
không suy từsource/merge/health raâmthanhthật. Actual audio NOT_OBSERVED.

`PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`, `PRODUCTION_DATA_WRITES=0`.
Goal không hoàn tất;M-FINAL-01..06 vẫn ở cuối checklist.

## Phụ lục exact CI đầu

Run43588773451 trênHEAD3f6883e6 dừng ở sharedcontracts:13PASS/1FAIL,
test SP-02 còn đòi chuỗi `portal-chat-workspace-guard-list` của aside đã bỏ.
Đây thiếu sót inventory test của điều phối,không phải lỗi worker/app.
Sửa đúng assertion cũ thành actualrenderer:boundary không tạo khung,execution
status vẫn hiện và không quyền gửi vẫn disabled. Ba chốt Support và hàm
boundary giữ,không skip/xóa test. Không đổi app hay chạy lại native đã đạt.
Sau test-only amendment cần source/provenance/exactHEADCI mới trước merge.

FinaldeliveryPR732HEAD211e45fe,CI43589450424bothPASS,merge/runtime7e30dd95,
deploy43590585769PASS;tree96606afc exact,trackedclean/servicesactive-running/
health/4publicassets/TTS+2protectedvideohashesexact. ReceiptIssue6896876684304
vàPR7326876684561. Khôngsigned-productionUIhoặcactualengineaudio claim.
