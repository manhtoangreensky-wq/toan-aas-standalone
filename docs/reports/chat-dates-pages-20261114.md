# Hội thoại: ngày giờ dễ đọc và chuyển trang đúng ngôn ngữ

BASE `7e30dd95d2d5652281f9462a73f7ba08b7801f59`, sau PR732 đã triển khai.
Một tracker Issue689. Hai phiên Antigravity độc lập trả3 thay thế trong2 tệp;
không đổi engine/Bot/provider/ENV/tiền/auth/API/loader/CSS/chuyển động.

## Kết quả

Ngày giờ trên thẻ dùng bộ định dạng ngôn ngữ có sẵn,ngày medium/giờ short,
múi giờ trình duyệt đang dùng. Không còn chuỗi ISO lẫnT/độ lệch giờ trên thẻ.
Ngày thiếu/rỗng/sai hoặc formatter lỗi/rỗng chỉ hiện dấu—,không lộ exception.
Không đổi timestamp lưu hoặc biểu thức ngày khác bên ngoài hàm thẻ.

Aria,dòng số vàhai nút chuyển trang theoVI/EN/ZH,bốn khóa/12 giá trị mới.
Mọi phép tính from/to/total,offset/null/coercion,disabled,nút/action/route/
thứ tự và emptyreturn giữ nguyên. Không tạo trang hoặc số liệu giả.
Bốn chỗ hiển thị dùngsafeText(uiText(...));uiText vốn khôngescape nên assumption
ban đầu của điều phối đã được sửa trước giao. Không đổi helper chung.

## Bằng chứng

CandidateactualVM39case BASE4PASS/35RED→39PASS,không ghi app.
Permanent31case BASE3PASS/28RED→31PASS. Lượt capture đầu pipeline cắt output
khi lấy40dòng đầu nên không được dùng exitstatus;capturelại giữcode1 và toànlog
trước khi áp dụng. Không suy PASS từ log hoặc trạng thái wrapper.

Nhóm70gồm31new+39prior:66PASS/4FAIL do historicalwrapper tạo object mới
làm mất trạng thái frozen và adapter mới bắt mutation trước adapter cũ.
Sửa đúngtesthelper:đoObject.isFrozen trên catalogVM thật trướcprojection,
vàchỉ nhận lỗi strict từ hai lớp cards/dates-pages. Khôngfreeze clone để giả
PASS,không nới điều kiện hash. Rerun4affectedPASS,không sửa app/worker.
286affectedNodePASS,9ChatPythonPASS,syntaxhai bundle/py_compileapp exit0.
MetadataTester32PASS/1knownWindowsPOSIXcase deselected locally,giữ nguyên
testsource vàLinuxCI. Nguồncase1225dòng/136822byteLF,
SHA256 `e5fd8740b4042856d1d0e98f0d1ecd64379c1d3d869b3a8054dd125b01f1eacd`.
Các nhóm có chồng lấn,không cộng làm số phủ toàn hệ thống.

So nguồn3workerchanges/2appfilesexact;DATEOLDglobal2/function1 và chỗ còn lại
giữ;17protectedpaths giữ BASE. Fullspanhash cho cards/pagination và4exactkeys
giữoldvalue/order/freeze;unknown/partial/mutation/reorder không bị lọc rộng.
ReviewnguồnđộclậpC0/I0/M0,không chạy lại suite/browservìreview.

### Kiểm tra màn hình thật

BASEfiniteVI375light dùngGETthật,cả ngàyISO vàchữphântrang cũ được bắtRED,
integrity vẫn đúng vàQAcleanup về0 trước áp dụng.

Sau sửa6view VI/EN/ZH×375sáng/1440tối,tổng18trạngthái:
GET thật offset0→50→0 bằng hai nút thật,50→5→50thẻ mỗi lượt.
Tổng55/canonicalIDs/order/owner/rawdata giữ,không bootstrap hay response giả.
Ngày từng thẻ đối chiếuIntl native độc lập từtimestamp trả về,không lấy expected
từ UIhelper. Aria/summary/buttons lấy từbảngcopyphiếu,không tựđọc implementation
đểlàmexpected. 0tràn/overlay/console/pageerror/egress/ghi sản phẩm.

QA chỉcopyfakeDB đã sở hữu,165metadata rows=3owner×55 hợp lệ,khôngschema mới;
165threadfingerprints/6plan18scene/version/idempotency vàevidencegốc giữ.
3fakeauthPOST,mọi request sản phẩmGET/HEAD;22ownedprocessdọnvề0.
Không provider/wallet/productionwrites hoặc thaytimezone/ENVmáy.
Không dùng responsiveChrome thaycho thiếtbị/Safari hoặcsignedproduction.

Bằngchứngcục bộ:`chat-dates-pages-permanent-red-exit-nov14.log`,
`chat-dates-pages-affected-nov14.log`,`chat-dates-pages-scope-nov14.json`,
candidate39report vànative `baseline-date-pages-r1`/`green-date-pages-r1`.
Chỉ công bố số đo tổng hợp,không DB/login/API/customerpayload.

## Trước push / phần còn mở

Tài liệu hiện tại/gốc,phiênTester,cases/metadata vàchecklist mẹ được cập nhật.
Không mởtracker hoặc testcaseproject cạnhtranh. Provenance,exactHEADCI/
merge/deploy/runtime/assets phải córeceipt riêng cùngIssue/PR.

PR732 đã giao HEAD211e45fe,CI43589450424bothPASS,merge/runtime7e30dd95,
deploy43590585769PASS,tree96606afc exact,services/health/4assets/protectedhashes
đúng. ReceiptIssue6896876684304/PR7326876684561.

Chatdetail/context/turn/run/lifecycle/toast vàDocumentrouteschưa thuộcphiếu
vẫn mở;hai phiếu field/lifecycle đanggiao cácphiên output-only riêng.
Không ghi “toàn bộ hết thuật ngữ” hoặc đóngM-FINAL-01..06.

Web–TTSgenericforwarding cóchủđích,khácdedicatedlifecycle không chứng minhbug.
VPSvoice_tts khôngtrongallowlistexecution;khôngbậtENV/quyền/callcóphí.
ActualaudioNOT_OBSERVED. `PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`,
`PRODUCTION_DATA_WRITES=0`;goal vẫn đang mở.
