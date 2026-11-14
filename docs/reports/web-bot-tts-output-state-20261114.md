# Tạo giọng: không báo hoàn tất trước khi có âm thanh

BASE52f3b4a50cffa65a526bc85cddbab25624db92af, sau PR728 đã triển khai.
TrackerIssue689; contract6872085245, R2correction6872260891. Đây là đợt Web
adapter riêng, không trộn mã ứng dụng vào đợt dịch chữ.

## Lỗi và thay đổi

Đường tạo giọng Web đã có create/prepare/confirm/read/artifact tới Bot. Một
nhánh `ok:true` ở Web trước đây ghi hoàn tất dù chưa có tệp, rồi các lần đọc
khác bỏ qua bản ghi này. Kiểm tra với transport có kiểm soát và SQLite riêng
tái hiện1PASS/3RED; chưa chứng minh điều kiện này từng xảy ra ở khách thật.

Ba thay đổi chính xác từ AntigravityR2, chỉ hai hàm trong
`copyfast_voice_tts_job_bridge.py`:

1. Chỉ ghi hoàn tất khi Bot trả trạng tháicompleted và cờ có âm thanh là
   booleanTrue thật. Thiếu tệp hoặc cờ sai kiểu không ghi hoàn tất/thời gian/
   đường tải, không cập nhật các giá trị tiền.
2. Đọc lại bản ghi cũ đã mang completed nhưng thiếu đầu ra, để nhận tệp về sau.
   Bản có đầu ra hợp lệ vẫn không hỏi lại hoặc xác nhận tạo lần nữa.
3. Phản hồi chưa có âm thanh không trở thành hoàn tất; cho phép sửa trạng
   thái processing/failed của bản cũ thiếu tệp. Phản hồi trễ không hạ bản đã
   hoàn tất cùng đầu ra thật.

Không đổi đầu mối/ID, auth/ownership/prepare, báo giá/biểu thức và giá trị tiền,
nhánh lỗi/thanh toán, HMAC/nonce, schema hoặc Bot. Các giá trị thu phí vẫn do
nguồn chuẩn cũ quyết định; Web không thêm thao tác ví/thu tiền.

## Bằng chứng

- R1proposal5PASS/3FAIL trong8case:truthiness nhận nhầm cờ không phải boolean.
  R2 cùng phiên/samefragment khắc phục,8/8PASS. Không tiếp quản tự sửa ứng dụng.
-23test mới:BASE4PASS/19RED; khi áp dụng exactR2, chạy gộp cùng28testTTS cũ:
  **51/51PASS**. Có pending/missing/malformedflag,oldinvalidcompleted,
  delayedread/concurrentcomplete,duplicateconfirm,savedquote/ownership tests.
 3warning thư viện cũ được giữ,không làm yếu bài kiểm tra.
- Kiểm nguồn/AST xác nhận đúng3workerchanges/2functions; mọi bridgecall,
  tiềnexpression,confirmgates,paymentbranches không đổi;16applicationpaths
  bảo vệ khác khớp BASE. Review độc lậpC0/I0/M0,không chạy lặp suites.
- Compilecopyfastadapter/test vàdiffwhitespaceđạt. CI chỉ bổ sung2testpath
  vào lệnh critical bounded hiện có; không đổi quyền/timeout/secret/deploy.

DB riêng,networkguard chặn mọi kết nối ứng dụng;0realprovider/wallet/
productionwrites. Harness Windows ban đầu bị chặn self-pipe,đã xác định
stack/giới hạn25s và dừng đúng2PID sở hữu; lượt cô lập được phép chạy cho
raREDthật. Không coi lỗi môi trường là lỗi worker hoặc lý do đổiauth.

## Đối chiếu Bot chỉ đọc và giới hạn

Bot đang chạy804e23dad74dce0dfcaf3f472f1d2231a86931ba. Mã
`services/web_voice_tts_runtime_service.py` lưu `web_job_id` làm `job_id`;
get/confirm/artifact chuyên biệt trongbot.py dùng khóa này. Như vậy nghi vấn
WebID/runtimeID từsourceaudit không chứng minh đứt kết nối,không sửa ID.
GETBot trả has_artifact từartifact_bytes>0;confirmthànhcôngtrảTrue. Chỉ đọc
nguồn VPS,không đọcjobkhách,khônggửibằngchứngvận hànhsangworker.

Chưa gọi tạo giọng thật hoặc kiểm tệp âm thanh giải mã được. Những cổng này
cònNOT_OBSERVED; HTTP200/serviceactive/sourcepresence không thay bằng chứng.
Merge/deploy/runtimehash vàactualfinaloutput là các mức riêng. Các phầnUI/
locale/AX/auth/device/Safari/motioncuối của goal vẫn mở.

## CI preparation correction, same implementation

ExactHEAD838c61eb run43562729318 failed at the new fixture after310priorPASS.
Earlier auth tests replace `sys.modules["copyfast_bridge"]`; the new test held
a collection-time module reference, while production dynamically imports the
current module. Its mock patched the old object, so the real fail-closed
configuration gate correctly returned503. No production configuration problem
or worker implementation failure is inferred.

Owned reproduction replacing the module after collection:23/23newcasesRED.
Test-only repair resolves the current module inside the fixture, matching the
production import. No application/auth/config gate or assertion is changed;
all expected state/route/financial checks remain. Local affected rerun and new
exactHEADCI are required. The first failed run is retained, not relabeledPASS.
Affected reload reproduction now23/23PASS; previous28unchangedtests retain
their51combined evidence. No repeated broad suite to conceal the order failure.
