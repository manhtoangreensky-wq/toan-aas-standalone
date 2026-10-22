# Nghiệp vụ vận hành hiện tại — TOAN AAS Web App

## Free Tools và nội dung khách — 22/10/2026

Free Tools không gắn nguồn ảnh rỗng lúc khởi tạo; ảnh YouTube chỉ hiện sau khi
tải, lỗi có một dòng ngắn theo ngôn ngữ giao diện và có thể trích xuất lại.
Không còn fallback sang ảnh placeholder ngoài. CSP giữ nguyên: matched baseline
5messages, candidate0. Subtitle cleaner hoạt động cục bộ và TXT tải về khớp
văn bản đã làm sạch ở12cấu hình.96initialstates ở8route khách,3ngôn ngữ,
2theme,2viewport đạt không chữ thử nghiệm/demo/beta/sandbox, không hero badge,
Voiceinputtrống, không overflow/page/console/UIwrite/external. Dữ liệu quote
tổng hợp của fileQA cũ không dùng làm bản bàn giao hoặc chứng minh tạo giọng.
Đây chưa phải nghiệm thu generation/provider/output của tất cả sản phẩm.

## Music Library guard clarity — 22/10/2026

Khi thư viện nhạc hoặc SFX chưa được máy chủ cấp quyền, customer UI chỉ còn một
thông báo nguyên nhân, nút kiểm tra lại quyền và đường dẫn sang Không gian âm
thanh. Ba chip kỹ thuật lặp lại (thông tin riêng tư, nghe thử, tải tệp) đã được
bỏ khỏi thẻ chặn; capability, API, dữ liệu và boundary delivery không đổi.
Test riêng đạt `1/1`; focused Music/library đạt `57/57`; toàn bộ Node WebApp
đạt `908/908`; syntax và `git diff --check` đều đạt. Đây là sửa trình bày tại
source, chưa phải bằng chứng nghe/tải/giao tệp hoặc LIVE.

## Content Studio guard clarity — 22/10/2026

Ba trạng thái chưa xác minh của Content Studio (chưa có quyền, đang tải, tải
thất bại) chỉ hiển thị nguyên nhân và thao tác cần làm; các chip kỹ thuật lặp
về phiên, bộ nhớ đệm, cầu nối hoặc đầu ra giả đã được bỏ khỏi customer UI. Khi
máy chủ cho phép, nút thử lại vẫn giữ nguyên. Test riêng đạt `1/1`; toàn bộ
Node WebApp sau thay đổi đạt `909/909`. Đây chỉ là lớp trình bày, không mở thêm
quyền tạo, engine, AI, thanh toán hoặc giao tệp.

## Project Center guard clarity — 22/10/2026

Các trạng thái chưa có quyền/đang tải/tải lỗi của Project Center đã bỏ chip
phiên, bộ nhớ đệm và cầu nối lặp lại. Màn hình vẫn giữ nguyên nhân, trạng thái
đang chờ và nút thử lại khi capability được máy chủ cấp; không thay đổi
authoring, ownership hoặc dữ liệu dự án. Test riêng đạt `1/1`; toàn bộ Node
WebApp sau thay đổi đạt `910/910`. Chưa có thay đổi engine, provider, ví hay
giao tệp.

## Campaign Planner guard clarity — 22/10/2026

Các trạng thái chưa đăng nhập/đang tải/tải lỗi của Campaign Planner đã bỏ chip
phiên, bộ nhớ và kết nối thay thế lặp lại. Lý do truy cập, trạng thái chờ và
nút thử lại vẫn giữ nguyên; không thay đổi lịch, publish, quyền, dữ liệu hay
boundary AutoPost. Test riêng đạt `1/1`; toàn bộ Node WebApp sau thay đổi đạt
`911/911`. Không gọi kênh ngoài, provider, ví hoặc PayOS.

## Bot companion intro clarity — 22/10/2026

Các trang handoff Bot và Analytics không còn ba chip kỹ thuật lặp về authority,
report/charge và identity. Intro chỉ giữ thông điệp tiếp tục trong Bot; command,
URL, connection guard và ranh giới dữ liệu giữ nguyên. Test riêng đạt `1/1`;
toàn bộ Node WebApp sau thay đổi đạt `912/912`. Không gửi lệnh, gọi Bot,
provider hoặc thay đổi tài chính.

## Video Factory và Guide quyền sử dụng — 22/10/2026

Guard của Video Factory Workflow và Guide quyền sử dụng đã bỏ các chip kỹ
thuật lặp về phiên, execution/publish và license. Nguyên nhân cần phiên Web vẫn
hiển thị trong nội dung chính; route, quyền và boundary không đổi. Test riêng
đạt `1/1`; toàn bộ Node WebApp sau thay đổi đạt `913/913`. Không mở video
execution, provider hoặc xác minh license thay cho máy chủ.

## Image utility guard clarity — 22/10/2026

Sáu nhóm Image utility (xóa nền, lịch sử, gắn thương hiệu, storyboard, đổi
canvas và nâng chất lượng) ẩn chip kỹ thuật phiên/cache/fallback trong các guard
card bằng selector chỉ áp dụng cho đúng route. Nguyên nhân và thao tác cần làm
vẫn giữ; không đổi engine, file, capability, API hay output. Test riêng `1/1`;
toàn bộ Node WebApp sau thay đổi đạt `914/914`.

## Document/PDF utility guard clarity — 22/10/2026

Các guard card của Document/PDF utility (hub, split, merge, optimize, convert
và OCR) ẩn chip kỹ thuật phiên/storage/runtime/fallback theo từng route. Lý do
và action thật vẫn giữ nguyên; không đổi bytes, storage, capability, API hay
delivery. Test riêng đạt `1/1`; toàn bộ Node WebApp sau thay đổi đạt `915/915`.

## Support Admin guard clarity — 22/10/2026

Guard của Trung tâm hỗ trợ khách hàng trong Admin chỉ còn thông điệp yêu cầu
quyền do máy chủ cấp. Ba chip kỹ thuật về vai trò, cầu nối và dữ liệu dự phòng
đã bỏ; loading, RBAC, danh sách yêu cầu và boundary tài chính không đổi. Test
riêng đạt `1/1`; toàn bộ Node WebApp sau thay đổi đạt `916/916`.

## Remaining customer guard surfaces — 22/10/2026

Project Package, Asset Vault, Inbox, Automation, Operations và Video
finalization đã ẩn các chip implementation lặp trong guard card theo đúng
route. Metric thật ở các surface khác không bị ẩn; capability, storage, job,
API và delivery không đổi. Test riêng đạt `1/1`; toàn bộ Node WebApp sau thay
đổi đạt `917/917`.

## Campaign boundary clarity — 22/10/2026

Campaign detail và hàng tự rà soát chỉ giữ giải thích nghiệp vụ; chip mã,
CSRF, publish và audit lặp đã bỏ. Mốc lịch thật trong Calendar không thay đổi.
Test riêng đạt `1/1`; toàn bộ Node WebApp sau thay đổi đạt `918/918`.

## Voice Studio lane clarity — 22/10/2026

Voice Studio lane rail giữ tiêu đề, mô tả và nút mở khu vực; nhãn trạng thái
“đang được bảo vệ” lặp trên cả ba lane đã bỏ. Route, capability, Voice Vault và
handoff không đổi. Test riêng đạt `1/1`; toàn bộ Node WebApp sau thay đổi đạt
`919/919`. Đây chỉ là presentation, không phải preview, rename, delete, reuse
hay engine voice runtime.

## SubDub Smart Multi empty-map clarity — 22/10/2026

Smart Multi giữ mô tả nhận diện một/nhiều giọng và callback guarded, nhưng không
hiển thị khung bản đồ người nói rỗng khi server chưa trả speaker payload. UI
không đoán giọng hoặc dựng kết quả giả; upload, engine, quote và delivery vẫn
chưa mở. Test riêng đạt `1/1`; toàn bộ Node WebApp sau thay đổi đạt `920/920`.

## Guide/Video zero-metric clarity — 22/10/2026

Guide Center chỉ giữ số chủ đề; Video Factory chỉ giữ số bước có chủ đích.
Các ô `0` kỹ thuật về execution, provider call và customer publish đã bỏ vì
không phải lựa chọn nghiệp vụ của khách. Catalog, route và workflow boundary
không đổi. Test riêng đạt `1/1`; toàn bộ Node WebApp sau thay đổi đạt `921/921`.

## Free Prompt Gallery zero-metric clarity — 22/10/2026

Free Prompt Gallery chỉ giữ số nhóm mẫu và ngành; ô `0 — Thực thi / thanh
toán` đã bỏ vì không phải lựa chọn nghiệp vụ của khách. Catalog, filter, xem
chi tiết, sao chép và lưu không đổi. Test riêng đạt `1/1`; toàn bộ Node WebApp
sau thay đổi đạt `922/922`.

## Billing presentation repair — 22/10/2026

Batch `R218-BILLING-20261022` hoạt động ở lớp Web UI và read-only projection.
`/api/v1/packages` production đã quan sát `available=true`, 4 gói tháng và 20
combo; `/packages` render 24 card sau hydrate ở viewport 327×668, overflow 0.
Giá bán chỉ được phép xuất hiện khi `public_sale_catalog` có SKU, version và
`approval_status=owner_approved`; Web giữ giá trống khi upstream chưa cấp.

Nạp thủ công giữ hai nguồn đọc riêng: `/payments/options` cho method/QR và
`/payments/manual` cho history. Lỗi options không được hiển thị như lỗi history;
retry method gọi lại đúng GET options. Không có fallback sáu gói nạp client.
Hai method ACB trùng QR chỉ còn một lựa chọn hiển thị theo readiness; canonical
IDs/history giữ nguyên. Ảnh QR portrait giữ tỷ lệ tự nhiên và hiển thị rộng hơn
trên desktop/mobile, không crop/scale mã.

Evidence local: Node 902/902; wallet truth 21/21 trên DB cô lập + bridge giả lập;
billing/QR Python 24/24 (CSS baseline exclusions đã tái hiện trên BASE);
browser QA 120/120 cấu hình VI/EN/ZH × light/dark × 375/390/768/1440,
console errors 0, UI writes 0, external requests 0, overflow 0. Không gọi
provider, không tạo giao dịch, không thay wallet/PayOS. Batch chưa push/deploy;
production vẫn chạy commit `e5b1f586` cho tới khi Owner mở delivery.

## R218 Q0 — nhãn giao diện thừa và Image continuity, 21/10/2026

Shared customer/Admin không còn trình bày các ô bo tròn kiểu “đang ở trang
này”, “khả dụng”, “guarded” hoặc “read-only” cho chrome điều hướng; trạng thái
bản ghi thật vẫn là văn bản để không che giấu dữ liệu. CSS fixture đạt `8/8`,
ma trận signed đạt `120` trạng thái và hồi quy Image nhãn đạt `24/24`; không có
request ghi/ngoài hoặc overflow. CSP của `/tools/free` vẫn còn đúng `5` cảnh
báo baseline mỗi lượt và được ghi ở backlog `UT-CSP-EMPTY-THUMB`, chưa nới CSP
và chưa gọi là đã sửa.

Image hiện giữ một tài liệu với bốn mode `/image/create`, `/image-studio`,
`/image/transform`, `/image/edit`. Draft chỉ giữ scalar của form theo mode;
file, token, quote, receipt, provider và job không được ghi. Signed delayed-auth
candidate đạt `12/12` (không form/record cũ trong loading), normal Image đạt
`24/24`, focused continuity đạt `59/59` và full Node đạt `894/894`. Đây là
bằng chứng UI/UX/accessibility và vòng đời draft cục bộ; upload/reference,
engine AI/manual, before-after/history, quote/job/output/delivery và LIVE vẫn
chưa đóng.

## SD-C2 — đi tới công cụ giọng và quay lại bản nháp, 21/10/2026

Từ SubDub, link Kho giọng/Thêm giọng mở đúng Voice trong cùng tài liệu khi
phiên đang hợp lệ. Bốn tab Voice giữ đường quay lại đã kiểm; “Quay lại SubDub”
khôi phục đúng mode, lane và cấu hình hiện có, kể cả0/200 và Back/Forward.
URL chỉ chứa đường/mode hữu hạn, không chứa bản nháp/tệp/token/profile ID.
Đây là giữ ngữ cảnh giao diện, KHÔNG phải đã lưu/áp dụng giọng hay có output.
Modified click/tab mới/reload đầy đủ giữ hành vi trình duyệt; không hứa giữ
tab-memory qua tài liệu mới. Browser48 vòng trên locale/theme thực đạt;
case SDRETURN và evidence SD-C2 ghi phạm vi rõ. Không sửa API/engine/ví.

## SubDub SD-B2 — đính chính capture và trạng thái dùng chung, 21/10/2026

Test21 trước đó chưa chứng minh âm lượng0/200 được chụp từ control thật.
Review và browser mới tái hiện14 sai lệch; SD-B2 đã mở lại trước khi sửa.
Correction dùng draft đã chuẩn hóa, render trực tiếp và dùng cùng giá trị mới
nhất giữa mode tương thích; không sửa HTML bằng regex. Session identity đổi
hoặc đăng xuất xóa slot SubDub; file/provider ID không vào draft. Handoff
Voice, bước review đầy đủ, number/mute và semantics vẫn là các spec tiếp theo.
Không có upload/ASR/dịch/lồng tiếng/quote/job/output thực trong bằng chứng này.

## SubDub SD-D2 — xem lại thiết lập và cân âm lượng, 21/10/2026

Bước 3 của SubDub hiện hiển thị thiết lập dạng hàng dọc theo mode đang chọn:
nguồn phụ đề do người dùng khai báo, target/ngôn ngữ ISO, lane giọng, âm lượng
gốc/lồng tiếng, vị trí và định dạng phụ đề. Tệp nguồn, ngôn ngữ đã nhận diện,
speaker-count, giá và chi phí không có dữ liệu server thì giữ `Chưa xác minh` hoặc
`—`; không tự tính và không mở nút xử lý.

Âm lượng có thanh kéo và ô số: gốc `0–100%`, lồng tiếng `0–200%`, nhập số nguyên;
giá trị rỗng, âm, phân số, ký tự sai hoặc ngoài giới hạn giữ mức hợp lệ gần nhất
và báo lỗi cạnh ô. Khi lồng tiếng `0%`, cảnh báo và ô xác nhận chỉ là thiết lập
cục bộ; rời `0%` xóa xác nhận, quay lại phải xác nhận lại. 24/24 cấu hình QA đạt,
page/console/UIwrite/external/overflow đều `0`. Đây chưa phải upload, ASR, dịch,
lồng tiếng, Smart Multi, quote, job, output, ví hoặc LIVE.

## Image R218-05 — lát presentation hiện tại, 21/10/2026

Trang `/image/create` giữ một workspace dọc với bốn lane: Tạo ảnh, Câu lệnh từ
ảnh, Chỉnh AI và Chỉnh thủ công. Ba lane ngoài tạo ảnh hiển thị guarded; không
tự nhận đã upload, tạo ảnh, chỉnh ảnh, có preview, quote hoặc tệp kết quả. QA
18/18 cấu hình VI/EN/ZH × sáng/tối ×390/768/1440 đạt focus, không overflow,
không lỗi trang/console, request ghi/ngoài/không biết đều `0`. Đây là bằng chứng
presentation control-level; reference/upload, AI/manual engine, trước-sau,
history, quote/job/output/delivery và LIVE vẫn mở.

## SubDub SD-E2 — ngữ nghĩa và trợ năng, 21/10/2026

Bước kiểm tra thiết lập có heading theo mode và một vùng đọc trạng thái live;
trình hỗ trợ có thể biết vùng nào vừa thay đổi. Giá trị âm lượng dùng `status`
live/atomic, còn ô số và thanh kéo giữ nhãn, giới hạn và liên kết lỗi. Bốn tab
vẫn trỏ đúng panel và panel ẩn không lọt vào thứ tự đọc. Đã đo 3/3 test ngữ nghĩa,
hồi quy SubDub 47/47 và 24/24 cấu hình browser; đây chỉ là control-level, không
phải bằng chứng engine, provider, output hay LIVE.

## Music/SFX — trạng thái đọc và phản hồi thao tác, 21/10/2026

Thư viện hiệu ứng âm thanh không kế thừa bộ lọc/trang của thư viện nhạc.
Tìm kiếm, xóa lọc, phân trang và làm mới chỉ báo thành công khi dữ liệu hợp lệ;
lỗi và response cũ không được báo thành công. Chữ phân trang/thông báo theo
VI/EN/ZH, tìm không khớp khác với thư viện chưa có dữ liệu; loading có busy.
Test36/36 và browser39 cấu hình QA có locale hồ sơ thật, AX/ảnh/bàn phím;
không page/console error, UIwrite hoặc request ngoài. Đây vẫn là thư viện
thông tin tổng hợp chỉ đọc, không phát/tải/tạo âm thanh hay chứng minh backend
ownership. Copy dài và toast xếp chồng còn mở. Evidence:
`reports/audit/R218-MUSIC-LIBRARY-READ-STATE-QA-20261021.json`.

Ngày21/10 đã rút lại câu chữ hướng dẫn thư viện: mô tả ngắn gọn việc tìm và
mở bộ sưu tập, nêu thẳng chưa hỗ trợ nghe/tải, bỏ thuật ngữ kiểm toán nội bộ.
Browser39 cấu hình sau copy và test39/39 đạt; nội dung khách chưa được xem là
đã có playback/delivery. Q0-TOAST-STACK vẫn mở.

## Đính chính nghiệm thu 21/10/2026 — ưu tiên đọc trước checkpoint cũ

Các matrix 48/72/120/48 và motion12 của checkpoint cũ chỉ là smoke: không đủ
đóng toàn nhóm, locale thực, tương tác, AX hoặc độ mượt. Signed locale ưu tiên
hồ sơ, không thể chứng minh bằng cách đổi query. Chi tiết:
`reports/audit/R218-EVIDENCE-RECLASSIFICATION-20261021.md`.

Music đã có lượt nghiệm thu riêng mới: 18 cấu hình với locale hồ sơ VI/EN/ZH
được kiểm thực, chọn gợi ý/copy nhãn/apply, giá0/unknown, sửa và hoàn nguyên
input, expiry3 không thay form và report-only18; console/page/external/UIwrite0.
Source hashes và trường hợp cụ thể tại
`reports/audit/R218-MUSIC-RUNTIME-REVIEW-QA-20261021.json`.
Nghiệm thu này dùng dữ liệu phản hồi tổng hợp trên app QA; không chứng minh
generation/provider/delivery/LIVE. Avatar URL hiện chưa có persistence ở API
hồ sơ; chọn ảnh chưa được báo là lưu được. Trace QA còn cần đo, không bị chặn
do thiếu quyền mới trong phạm vi kiểm thử cô lập đã cấp.

## Voice — báo giá hết hạn khi trang đang mở (20/10/2026)

Đến deadline do máy chủ cung cấp, UI ẩn xác nhận cũ và báo “Báo giá đã hết
hạn. Xem báo giá mới trước khi xác nhận.” Form được giữ nguyên tại chỗ;
lời thoại, giọng, tốc độ, âm lượng 0, tệp STT/Thêm giọng và focus không mất.
Nhập lại nội dung cũ không làm báo giá hết hạn dùng lại được. Một timer được
dọn khi render/đổi route; không tự lấy báo giá hoặc gọi xử lý.

Đã đo: test hành vi 8/8, focused 70/70, full Node 769/769; Edge headless trên
fixture localhost đạt 22/22 cấu hình, 397 GET, write/request ngoài/unknown API/
console/overflow đều 0. STT vẫn guarded theo allowlist integration hiện tại;
gán tệp QA chỉ kiểm giữ file input. Evidence:
`reports/audit/R218-VOICE-QUOTE-IDLE-QA-20261020.json`. CI cho delta idle chờ
push; generation, quản lý kho giọng, giao tệp và LIVE vẫn chưa được đóng.

## Voice — báo giá sau khi sửa biểu mẫu (20/10/2026)

Khi khách sửa lời thoại, giọng, tốc độ hoặc âm lượng sau báo giá, UI ẩn xác
nhận cũ ngay và yêu cầu xem báo giá mới. Preset tốc độ và thanh âm lượng có
cùng hành vi với ô số. Nhập lại đúng input cũ chỉ hiện lại control đã có nếu
receipt còn hiệu lực; trạng thái disabled do đang gửi vẫn giữ nguyên.
Đổi chế độ/hydration không làm confirm cũ trở lại khi draft đã khác quote.

Test riêng `11/11`, focused `77/77`, full Node `761/761`; Codex browser TTS
`18/18` cấu hình, `108` lượt đổi input: focus/draft giữ nguyên, overflow/
console/write/unknown API đều `0` trong fixture localhost chỉ đọc. Backend và
integration fingerprint check không đổi. CI quote-edit tại `8d53dab` đã xanh
ở run `39406730261`. Nghiệm thu idle UI nằm ở mục trên; quote thật,
tạo/giao âm thanh và LIVE vẫn mở.

## Voice — lựa chọn giọng mặc định, sửa kết luận capability (20/10/2026)

TTS hiện yêu cầu khách chọn rõ Nữ hoặc Nam; hai giá trị gửi máy chủ vẫn là
`female` và `male`. Lần đầu ô chọn rỗng, không tự chọn giới tính. Chuyển qua
Kho giọng rồi trở lại giữ lựa chọn, lời thoại Unicode, tốc độ và âm lượng 0.
Nhãn hiển thị theo VI/EN/ZH. Renderer `15/15`, nhóm Voice/STT `75/75`, full
Node `750/750`; Codex browser localhost `18/18` cấu hình, overflow `0`, console
không lỗi; fixture chỉ GET ghi nhận write `0`, unknown API `0`.

Helper tự chọn theo `readiness.features.voice_tts.default_voice_genders` trước
đây không có dữ liệu thật: `_project_readiness` không cho qua trường này.
Helper đã bị bỏ và mục fallback được mở lại trong R218-02A/T0. Các bằng chứng
trên là UI fixture, chưa chứng minh default capability, audio delivery hay LIVE.
Chi tiết: `reports/audit/R218-VOICE-DEFAULT-SELECTION-QA-20261020.json`.

## AD-03 — checkpoint chiếu liên kết hồ sơ Admin (20/10/2026)

Lớp cầu nối Admin hiện chỉ đưa `admin_record_references` tới trình duyệt khi
request đã đi qua cờ đọc Admin (`admin_read=true`) và chốt quyền Admin phía máy
chủ. Projection chỉ nhận đúng **5** loại hồ sơ (`request`, `job`, `asset`,
`report`, `audit`), tối đa **6** liên kết trong một tập; liên kết ở record đơn
và trong `items[]` dùng cùng allowlist. ID, nhãn và đường dẫn đều bị giới hạn
độ dài; đường dẫn chỉ thuộc **5** họ nội bộ `/admin`, `/jobs`, `/assets`,
`/reports`, `/audit`. URL ngoài, `//`, `\\` và dot-segment bị loại hoặc làm
rỗng. Dữ liệu sai kiểu/kind/ID bị fail-closed; tài khoản không phải Admin
không nhận trường này. Projection không tự tạo record, không nối request → job,
không cấp quyền và không gọi provider/bridge bổ sung.

Bằng chứng local trên candidate hiện tại: contract Python AD-03 `1 passed,
56 deselected`; `py_compile` cho `copyfast_api.py` và test không lỗi; toàn bộ
Node `735/735`; `node --check` hai file Portal và `git diff --check` đều không
có output lỗi. Đây mới là bằng chứng source/local; CI trên commit mới, record
thật, RBAC thật, bridge request → job → asset → report → audit và LIVE chưa
được đóng. Không dùng checkpoint này để kết luận Admin đã duyệt tiền, giao tệp
hay production đã chạy.

## Admin theme — ứng viên UI 19/10/2026

Admin vẫn mặc định Sáng như policy visual-reset trước. Nay chọn Tối/Theo hệ
thống thực sự có tác dụng; không còn JS ép lại Sáng/xóa lựa chọn Admin.
Lựa chọn lưu riêng, không sửa theme khách. Khi storage bị chặn vẫn đổi được
trong trang; không ghi API/auth/ví. Đổi theme không reload/remount form.

Dark dùng navy `#0b132b` và thẻ `#1c2541` sẵn có, chữ sáng. Light giữ nền/thẻ/
bố cục, dùng teal đậm hơn trong cùng palette cho CTA/selected nav. Nút ≥44px;
hai meta theme-color cùng selected scheme. Node 17/17, full Node 704/704.
Browser localhost: 24 cases VI/EN/ZH ×375/390/768/1440 ×home/login, cả hai
theme; measured contrast min 7,61 dark/5,24 light, errors/write/external/
unknown/overflow 0. Đây là read-only fixture, chưa production/LIVE hay login thật.
Các bảng có dữ liệu, biểu đồ và module Admin còn cần QA riêng.

## Admin overview — quyền hiển thị và số liệu hàng đợi (19/10/2026)

Banner nạp tiền, sự cố và lối tắt `/admin` chỉ hiển thị các phân hệ trong
manifest điều hướng máy chủ đã cấp. Giao diện không cấp quyền mới; backend
vẫn kiểm tra từng request. Tổng nạp chờ duyệt chỉ lấy số nguyên không âm từ
`adminData.counts.pending_topups`: thiếu/null/sai kiểu hiện `— / Chưa xác định`,
khác số `0` thật. Không đếm trang danh sách hữu hạn thành tổng hàng đợi.

Nhãn unknown và chẩn đoán theo VI/EN/ZH. 18 test hành vi đạt; browser localhost
18 cấu hình × 6 trạng thái = 108 trạng thái đạt, page/console/request ngoài/
HTTP write/unknown API/overflow 0; tương phản nhãn unknown 5,80:1.
Fixture kiểm projection UI, không chứng minh backend RBAC, duyệt tiền hay LIVE.
Ở checkpoint overview trước, Admin vẫn bị ép sáng; xem cập nhật AD-02-THEME
ở trên để phân biệt default Light với lựa chọn Dark/System đã được sửa.

## Checkpoint Voice inventory — ứng viên 19/10/2026

Kho giọng `/voice/saved` phân biệt đang tải, lỗi kết nối, chưa kết nối và
danh sách đã tải. Lỗi không còn hiển thị như tài khoản chưa có giọng; dữ liệu
cũ được xóa trước lần đọc và khi đổi phiên. Nút Thử lại chỉ đọc dữ liệu.
Web hiển thị tối đa 50 record nhận được; API Core hiện không có pager/search
thật nên không công bố tổng kho hoặc nút trang giả. Đổi tên/đặt mặc định/xóa/
nghe thử/handoff vẫn là yêu cầu mở tại R218-02A/T0.

Đã đo trên localhost: 18 cấu hình VI/EN/ZH × sáng/tối × 390/768/1440,
7 trạng thái và 18 lượt thử lại bằng bàn phím; console/overflow/request ngoài/
mutation đều 0. Bộ inventory 34/34 và toàn bộ Node 638/638 (gồm 6 test SubDub
mới trên remote). Đây là shell,
renderer và integration.js production dùng API fixture, chưa phải dữ liệu
Core thật hoặc LIVE. Bằng chứng tại `../qa/r218-voice-inventory/result.json`.
Các mục vận hành/dữ liệu production bên dưới giữ nguyên phạm vi đo ban đầu.

### Lát UI Voice STT — 19/10/2026

Trang `/voice/stt` và alias `/voice/asr` hiện trình bày riêng luồng chép lời:
tiêu đề, mô tả, định dạng kết quả, trạng thái rỗng và CTA không còn dùng copy
“tạo giọng” hoặc bộ đếm âm lượng của TTS. Upload/estimate chỉ mở khi bootstrap
có capability riêng `voice_stt`; quyền Bridge chung không đủ để mở tệp.

Đã đo bằng Edge/Playwright localhost: 18 cấu hình VI/EN/ZH × sáng/tối ×
390/768/1440; page/console/request ngoài/write/unknown API/overflow đều `0`.
Kiểm thử hành vi STT `18/18`, toàn bộ Node của workspace `660/660`. Fixture là
projection đọc-only; chưa xác minh upload bytes, MIME/size/ownership, transcript,
progress, delivery, backend thật hoặc LIVE.

### Lát UI Music — 19/10/2026

`/music/create` (nhạc nền) và `/music/song` (bài hát) hiện dùng workspace dọc
chung nhưng tách đúng field: lời bài hát, kiểu giọng và dạng bài chỉ xuất hiện
ở bài hát; nhạc nền không hiển thị các lựa chọn đó. Copy tiêu đề, trạng thái,
handoff và cảnh báo được lấy theo catalogue VI/EN/ZH, không còn rò chuỗi của
locale khác sau hydration.

Đã đo bằng Edge/Playwright localhost: `36` cấu hình (VI/EN/ZH × sáng/tối ×
390/768/1440 × 2 route); page/console/request ngoài/write/unknown API/overflow
đều `0`. Không có audio, player, giá, download hoặc provider giả. Đây là fixture
đọc-only; generation, quote, player, tệp, delivery và LIVE vẫn chưa xác minh.

### Bản nháp Voice VO-01 — 19/10/2026

Bổ sung Voice VO-01 ngày 19/10: đổi chế độ giữ lời thoại và âm lượng trong
cùng phiên/tab; Back/Forward và locale giữ đúng. Đổi phiên xóa nháp Voice;
không lưu File/password hoặc ghi browser storage. 7/7 test hành vi, 18 cấu
hình trình duyệt; full Node mới nhất 645/645. Reload/tệp và runtime chưa đóng.

## Checkpoint UT-01 — workspace Dịch (ứng viên cục bộ 18/10/2026)

Web đã bổ sung một workspace dọc cho `/subtitle-studio/new?intent=translation&pair=...`:
nguồn tự nhận diện, 21 lựa chọn ngôn ngữ đích, tìm kiếm cục bộ, giữ bản gốc,
dịch hai chiều, trạng thái bắt đầu/dừng, kết quả và lịch sử. Đây là lớp trình
bày/control-level; nút xử lý mặc định bị khóa vì máy chủ chưa công bố
`translation-runtime-start`. Panel không gửi API action mới, không gọi provider,
không tạo quote/job/tệp, không sửa ví và chưa được kiểm thử live.

Đã đo: test riêng `4/4`, full Node `548/548`, `node --check` portal `PASS`,
`git diff --check` `PASS`. Python/pytest chưa chạy được vì workspace không có
lệnh `python` hoặc `py`.

## Checkpoint UT-04 — tiện ích miễn phí (ứng viên cục bộ 18/10/2026)

`/free-tools` hiện có 10 tab/panel: phụ đề, YouTube, VietQR, ảnh đại diện AI,
tỷ giá & quy đổi Xu, thời tiết, tải video & media, JSON, văn bản và mã hóa.
Bốn lane mới chỉ là control-level: có input, quyền sử dụng/nguồn, vùng kết quả
rỗng và trạng thái guarded; không gọi API tỷ giá/thời tiết, không tạo avatar,
không tải media và không mở provider. QR giữ flow cục bộ cũ.

Đã đo: test riêng `5/5`, full Node `549/549`, `node --check` portal và i18n
`PASS`, `git diff --check` `PASS`. Browser/AX, nguồn dữ liệu thật, stale/error
runtime, downloader delivery và live chưa chạy.

## Checkpoint giao diện Image — ứng viên cục bộ 08/10/2026

BASE `dee0ac4ccaaf2cb3ebe147ab217e85ec419bec4c` là merge SubDub PR #619;
checkpoint SubDub đã đóng/khóa mã, CI đạt, chưa triển khai. Phần Image đang
trên nhánh `fix/image-ui-truth-locale-20261008`, chưa push hoặc triển khai.

`/image` và `/tools/image` có 8 đích duy nhất, tạo ảnh đứng đầu. `/image/create`
và alias `/image/new` dùng biểu mẫu thật `prompt/tier/format`, nội dung cố định
VI/EN/ZH. Báo giá đứng trước nút xác nhận; sau xác nhận, báo cáo đứng trước
biểu mẫu cũ có thể mở lại. Chỉ hiện giá bán công khai đã có và ID tracking
khớp; không giả ảnh, download, thành công, giá -5 Xu hoặc chất lượng 4K.

Đã đo cục bộ: renderer 163/163; tạo ảnh 48 trạng thái/48 ảnh; hub 12 cấu hình,
24 trạng thái/24 ảnh. Chữ thường ≥5.944:1, chữ lớn ≥8.837:1, viền input
≥5.522:1; target nhỏ nhất 45px, summary 48px; tràn ngang 0. Comparator chứng
minh 10 file bảo vệ và phần CSS/catalogue/Portal ngoài Image giữ nguyên.
Python giữ đúng 18 đạt/1 lỗi nền do test lấy nhầm media-query 700px cuối file.

Bẫy CSS đã xác minh: `:is(.portal-button, summary)` có specificity class,
thắng rule summary 48px cũ và giữ 44px; entry scale có thể làm vùng chạm
nhỏ hơn chuẩn. Đã tăng specificity riêng Image, không thay theme toàn cục.
QA đo sau khi article cũ rời DOM và animation main ổn định, giữ ngưỡng 44px.

Motion điều hướng toàn site vẫn ghi 12 lỗi ViewTransition và còn mở. Gate
browser chính thức đạt trên code SHA `e91cfc42d9c574ce6a8d01bbc1e6bfdabb0478fe`:
18 trang/ảnh, 6/6 hub, 4/4 tiện ích, không lỗi JS/request, không nháy theme,
bàn phím 6/6. Web-only provenance refresh/verify cũng đạt; push/PR/CI/release
còn mở. Bằng chứng: `../../evidence/IMAGE-I03-VERIFY-20261008.md`.
Đây là checkpoint trình bày cục bộ; các số liệu production phía dưới có ngày
riêng, không chứng minh runtime đang dùng candidate Image.

## Candidate Image UI trên PR #647 — 2026-10-17

Source của PR #647 thêm danh sách dọc tại `/image/create` để khách chọn tạo ảnh hoặc mở
công cụ tăng chất lượng ảnh hiện có. Bản Việt/Anh/Trung, trạng thái trang hiện tại và ghi chú
rõ “chỉnh ảnh bằng AI chưa khả dụng” đã được kiểm bằng test nguồn (`40/40` Image, `319/319`
locale, `521/521` Node trên candidate hiện tại). Đây chỉ là thay đổi trình bày: không thêm
upload, preview, biến thể, đầu ra AI, giá hay thao tác thanh toán. Chưa merge/deploy/live;
không được coi chức năng chỉnh sửa ảnh bằng AI là đã hoàn thành. Tester case IUI-05 là nguồn
kiểm thử giao diện; cần browser DOM/AX và viewport QA riêng trước khi đóng runtime.

## Checkpoint giao diện SubDub — ứng viên 08/10/2026

Mã giao diện đã kiểm thử: `e4070e3bf6710be1e5388c12e20800aae0ee5ea3`, trên
nhánh `fix/subdub-ui-closeout-20261008`, dựa trên `origin/main`
`e70175a5f8b4d30bdf99de939b80d2de2e54ee18`. `/subdub` có một màn hình với
bốn chế độ: phụ đề gốc, phụ đề dịch, lồng tiếng, và phụ đề kèm lồng tiếng.
Mức âm lượng gốc/giọng đọc chỉ là thiết lập hiển thị cục bộ; tải tệp, báo giá,
tạo tác vụ và đầu ra vẫn đóng cho tới khi có thẩm quyền xử lý thật. Không đổi
đường dẫn, bộ máy xử lý, giá, ví hay dữ liệu.

Đã đo trên bản nguồn này: 12/12 tổ hợp tiếng Việt/Anh/Trung × sáng/tối × 1440/360; 48/48
lần đổi chế độ; lỗi runtime, request ngoài ý muốn, sự kiện thao tác và tràn
ngang đều 0. Độ tương phản chữ tối thiểu 5.23:1, viền điều khiển 3.61:1,
vùng chạm nhỏ nhất 44px. Đây là kiểm thử cục bộ. PR #619 đang mở; lượt CI đầu
dừng ở cổng kiểm tra dấu vân tay hồ sơ cũ, cần chạy lại sau khi cập nhật bằng
chứng Web. Chưa hợp nhất, triển khai hoặc xác minh trên hệ thống thật. Bằng
chứng: `../../qa/qa/subdub-exact-e4070e3/`.
PR #617 (Voice), #618 (Music), #616 (Video) vẫn CLOSED/LOCKED; không sửa lại
các phần mã sản phẩm đã khóa. Hiệu ứng toàn trang còn là mục riêng chưa đóng.

## Checkpoint giao diện Music — ứng viên 08/10/2026

BASE là main Voice `e405cbee28f0687f528eab7d66a71ef1623125f4`.
Hub `/music` giữ đúng 6 điểm đến hiện có: 3 lối sáng tác AI đang khóa đặt
trước, sau đó là công cụ tệp âm thanh và 2 thư viện. Mỗi điểm đến chỉ có một
thẻ, dùng chữ VI/EN/ZH; bỏ số liệu “Stereo 320k” và tuyên bố bản quyền/chất
lượng không có nguồn. Thẻ đầu dẫn tới `/music/create` để xem điều kiện, không
tạo nhạc hay mở quyền xử lý. Các action/API/engine/giá/ví giữ nguyên.
Voice PR #617 và checkpoint Video PR #616 đã đóng/khóa mã sản phẩm; Music
không sửa các block đó. Music chỉ được ghi release/live sau cổng riêng.

## Checkpoint giao diện Voice — 2026-10-08

Remote main đã đọc lại ở `8a040d0c2af0cdcb2ebd89a27f5f2caa9beff952`
(checkpoint Video PR #616). Checkpoint Voice trên nhánh
`fix/voice-ui-closeout-20261007` đang chuẩn bị release; các mục dưới đây mô tả
mã ứng viên và QA cục bộ, chưa xác nhận production đã đổi.

- Hub giữ 7 điểm đến hiện có. Các màn TTS, giọng đã lưu, nhân bản, nghe thử,
  kết quả, hồ sơ/lời thoại và soạn cách thể hiện dùng nội dung VI/EN/ZH.
- Biểu mẫu/card dọc; thiết lập phụ và thông tin quyền có thể mở bằng bàn phím.
  Trạng thái báo giá/công việc được đặt trước biểu mẫu cũ; sau xác nhận xử lý,
  biểu mẫu trước được thu gọn nhưng vẫn có thể mở lại.
- Chỉ giá công khai `estimated_xu`/`quote_xu` được ghi là giá bán. 0 Xu là một
  giá đã biết; giá thiếu/mâu thuẫn là “—”. `cost_xu`, giá provider và nguồn giá
  nội bộ không được dùng thay giá bán hoặc đưa lên phần chi tiết.
- Nút xác nhận giữ kiểm tra quyền phiên, khả năng xử lý, fingerprint và receipt
  hiện có; không xuất hiện khi thiếu giá công khai. ID công việc chỉ dùng khi
  khớp feature/trạng thái; trạng thái hoàn tất không tự cấp audio/download.
- “Lưu thành bản mới” khi mở lại bản nháp có nhãn đầy đủ ở cả 3 ngôn ngữ.
  Các action, tên trường, payload và xử lý backend giữ nguyên.
- Sáu bộ renderer Voice: **110/110 đạt** trên source hiện tại. Bằng chứng browser
  theo từng lát được dẫn trong `docs/superpowers/specs/2026-10-07-voice-ui-closeout.md`
  và `2026-10-08-voice-flow-state-presentation.md`; CI và live có cổng riêng.
- Music/SubDub chưa thuộc release Voice này. Shared-shell locale, nút nổi và
  motion toàn site vẫn mở; không suy ra đã sửa chúng từ checkpoint Voice.

Các số liệu runtime/nghiệp vụ cũ phía dưới là snapshot lịch sử có ngày/SHA.

## Checkpoint giao diện Video — 2026-10-07

Ứng viên phát hành từ main `9f2ba35a85608495cb34d918dfc0af62f4dc2414`.
Ba màn hình đang khép: `/tools/video`, `/video/create`, `/video/multiscene`.
Hub giữ 10 điểm đến duy nhất và xếp thẻ dọc. Hai form giữ nguyên input/action
của main; nội dung, số cảnh và tỷ lệ hiện trước phần thiết lập tùy chọn. Hướng
dẫn có thể mở bằng bàn phím; khung Video mẫu không còn xuất hiện ở hai route.
Thẩm quyền xử lý/giá/Xu vẫn do máy chủ xác nhận. Đây là bản sửa UI; trạng thái
merge/deploy/live phải đối chiếu riêng trong PR, không suy từ kiểm thử localhost.
Voice → Music → SubDub được ưu tiên sau khi checkpoint này merge; các màn hình
Video còn lại tiếp tục sau các tính năng khác.

Các phần có ngày/SHA cũ dưới đây là lịch sử, không xác nhận runtime hiện tại.

> Phạm vi đo: `origin/main` và production Web đến SHA `cc3b4689f85d7c18ebb31b500b1eda1aca20cb6f` ngày 10/09/2026; A09 Admin Operations được đo local trên đúng BASE này. Tham chiếu Bot chỉ mô tả ranh giới bridge đã nghiệm thu trước đó.
> Tài liệu này mô tả hành vi có bằng chứng trong source; không thay thế hướng dẫn deploy hay quyền phê duyệt của Owner.

## 1. Trạng thái và định danh nguồn

- Web production/main: `cc3b4689f85d7c18ebb31b500b1eda1aca20cb6f` (PR #424); Web/nginx active+enabled, tracked diff `0` tại readback.
- Bot comparator BASE/HEAD: `6476f20bdd9f8728a5db0b1d62a245b0d612aea8`.
- Inventory P0-05B: `reports/migration/p0-05-prepush-inventory.json`.
- Inventory SHA-256: `b2f6549380826d2688fc648b46237acfe56d20d6512578dead00e3cd131cd7e3`.
- PR #417 đã merge; quality run `33354445985` và deploy run `33354446011` đều `SUCCESS`.
- VPS readback sau PR #419: exact HEAD `0dd8ffa`; `toanaas-web.service=active`; `nginx.service=active`; `/health` trả `ok=true`, app `TOAN AAS Web App`, entrypoint `app.py`.
- Manual top-up `ACCEPTED_LIVE`: signed QR `6/6`, năm ảnh canonical unique `5/5`, năm viewport `5/5`, hotline `0898360858`; đúng một `MANUAL-1` đang `pending_admin_review`.
- PR #419 Auth hotfix đã merge; quality run `33373616782` và deploy run `33373616654` đều `SUCCESS`; live logo/card đã đo tại `844×610` và `390×667`.
- PR #421 Admin-login responsive đã merge/deploy; runtime `b657cea…` được live-test tại desktop/tablet/mobile và public `/login`/`/register` giữ nguyên comparator.
- Motion customer trên runtime `b657cea…` đã nghiệm thu lại: route entrance `8/8`, scroll reveal `6/6`, hydration no-replay `2/2`, reduced-motion `8/8`; overflow/framework/relevant-console/page error `0`.
- Production QA chỉ tạo một pending `10000 VND`; approve/reject/draft/confirm, `approved_xu`, ledger, provider, PayOS và Telegram call đều `0`. Đây không phải giao dịch đã thanh toán hay cộng Xu.
- `MERGED != DEPLOYED != LIVE`.
- `HTTP 200` chỉ chứng minh request HTTP được xử lý; nó không chứng minh quyết định tài chính cuối hợp lệ.

### 1.1 `/admin/login` responsive — đã accepted live

- BASE trước ship: `94dbd2825889f4ff71d201465870c182075a0282`; PR #421; runtime sau ship `b657cea98ecc0c2f6f962bf82f1044333dfe427e`.
- Source runtime thay đổi đúng một CSS file; regression test mới là file thứ hai. Các tài liệu/case trong commit là ship evidence, không phải runtime.
- Root cause cũ: `.portal-main` bị giới hạn `560px`, trong khi Admin article không có route-scoped desktop override; selector R1 từng đảo ancestor/descendant và không thể match.
- Candidate dùng exact ancestor `.portal-shell--auth[data-portal-app-kind="admin"] .portal-main`; mọi selector trong block đều có Admin marker.
- Fresh protected gate: `11 passed`, `1` warning deprecation; Node/diff exit `0`; artifact/secret match `0`.
- Browser local sau corrective: `1920/1440/1024` hai cột; `768/390/360` một cột; boundary `769/804/806/822/840` một cột và Browser-rounded `842` hai cột. Tất cả overflow/outside `0`; candidate khóa `≤840` stacked và `≥841` two-column.
- Light/dark giữ nguyên geometry; theme cuối được khôi phục `system`. `/login` và `/register` tại `390px` có Admin marker `false`, overflow/outside `0`.
- GitHub merge, deploy, runtime SHA và live Browser đã có bằng chứng riêng; phần này được khóa làm protected comparator cho M03B.

## 2. Kiến trúc quyền sở hữu

- Web App là sản phẩm độc lập có signed session, CSRF, tài khoản và nhiều module Web-native.
- Lane manual top-up hiện là Web-local và không yêu cầu liên kết Telegram/Core Bridge: Web sở hữu mã nạp 8 số, cấu hình/QR private, pending request/history và Admin reconciliation queue.
- Web vẫn không phải nguồn ghi số dư Xu hay sổ tài chính canonical.
- Browser gửi yêu cầu qua signed Web session và CSRF.
- Web API kiểm tra owner hoặc Admin bằng authority server-side.
- Customer create/history/detail/status và Admin list/detail/reject hiện đọc/ghi Web DB theo signed account/role; không gọi Bot bridge.
- Admin Web-local hiện chỉ có two-step reject. Approve/cộng Xu/ledger thuộc gate G0/G3 riêng và chưa được mở trong batch này.
- Browser không được tự gửi Telegram ID để nhận quyền sở hữu.
- Browser không được tự gửi `admin_id` để nhận quyền Admin.
- Web không cộng Xu trực tiếp.
- Web không tạo PayOS webhook thứ hai.
- Web không duy trì một ledger thanh toán thứ hai.
- Ranh giới tổng quát được mô tả tại `README.md:236-263`.
- Ranh giới Admin server-authoritative được mô tả tại `docs/migration/ADMIN_ERP_NAVIGATION_CONTRACT.md:3-30`.

## 3. Luồng dữ liệu manual top-up

1. Khách đăng nhập Web bằng signed session; liên kết Telegram là tùy chọn và không mở/khóa lane manual.
2. Signed `GET /api/v1/payments/options` trả mã nạp 8 số, hotline và projection phương thức từ cấu hình/asset private của Web; response luôn `no-store, private`.
3. QR chỉ đi qua signed same-origin endpoint; path private không xuất hiện trong JSON/HTML và repo public không chứa QR binary/config.
4. Selector hiển thị các method VND server cấp; method chưa sẵn sàng vẫn visible-disabled. USDT/Binance configured được hiển thị disabled với lý do chưa hỗ trợ đối soát VND, không phải “chưa cấu hình”. Initial không render method card/QR/code.
5. Khách nhập `amount_vnd`, chọn method và xác nhận local để mở đúng một instruction/QR. Sau khi chuyển tiền, khách có thể nhập reference rồi submit bằng CSRF + idempotency key.
6. Trong một `BEGIN IMMEDIATE`, Web xử lý đúng thứ tự: replay/conflict đã có → admission method → quota pending → insert một `pending_admin_review`.
7. Request/history/detail/status chỉ dùng account ID từ signed session và projection owner-safe.
8. Admin Web-local xem list/detail có account, email, amount, method, payment code và request ID.
9. G2 hiện chỉ cho draft/confirm reject với receipt ràng buộc Admin/session/request; reject không cộng Xu.
10. Approve/cộng Xu/ledger vẫn khóa; source hiện tại không tạo positive-credit/usage/revenue event.
11. Bằng chứng local: `tests/test_cust_web_manual_topup_visible_qr_001.py`, G1/G2 tests và protected matrix `70 passed, 79 deselected` ngày 02/09/2026.

### 3.1 Corrective P0-05E — số tiền, mã nạp và quyền riêng tư

- Khách nhập `amount_vnd`, chọn phương thức server cấp và có thể nhập tham chiếu/TXID; browser create body không được nhận owner ID, Admin ID hoặc `payment_code`.
- Signed `/api/v1/payments/options` lấy `manual.payment_code` từ mã 8 chữ số ASCII bền vững của Web account (`[1-9][0-9]{7}`); browser và Telegram ID không được dùng để override.
- `manual.support_hotline` dùng ENV hợp lệ 8–15 chữ số hoặc fallback `0898360858`. Fallback số tài khoản ngân hàng là comparator độc lập `0387532320`; Portal không hardcode hai số này.
- Lựa chọn manual, amount, method và reference được giữ trong transient route state qua same-route data hydration/remount. Hidden `topup_lane` chỉ giữ UI state; integration create body vẫn là `amount_vnd`, `method`, `reference`, `idempotency_key`.
- Customer single/history/detail/status không chứa `admin_note`; customer JS normalizer cũng không giữ field này. Admin projection riêng vẫn giữ request ID, Telegram ID, display name, amount, method và Admin note theo quyền.
- Browser behavior contract chạy Portal thật qua Node `vm`: chọn manual → `125000/bank_acb/TX-125` → invalid-lane attempt → hydration remount vẫn giữ đúng lane và dữ liệu.
- Local security reviewer độc lập kết luận finding “Customer manual-topup API exposes private Admin notes” là `fixed`; production/runtime/live money vẫn chưa được tuyên bố.

### 3.2 Payment destination và QR private — candidate 02/09/2026

- Backend công bố `manual.methods[]` bốn field tương thích và `manual.payment_destinations` keyed bằng method ID canonical.
- ACB VietQR chỉ `request_enabled=true` khi vừa có destination đủ bank code/name/account/owner, vừa có QR giải mã hợp lệ. MoMo/ZaloPay cần QR canonical; USDT TRC20 xuất hiện discoverable nhưng disabled, không vào VND admission.
- Nguồn runtime mặc định là `/opt/toanaas/webapp-private/manual-payment`: 5 ảnh private và `config.json` root-owned tối đa 16 KiB. ENV, nếu có, chỉ override. Không asset/config nào được commit vào repo public.
- QR được giới hạn 5 MiB, 4096 px mỗi cạnh, 16 MP; Pillow full verify/decode, decompression bomb và malformed file fail closed. Response có `Cache-Control`, `Cross-Origin-Resource-Policy: same-origin`, `nosniff`.
- Cache decode tối đa 12 entry theo resolved path + device/inode/size/mtime/ctime; file thay đổi phải revalidate, signed request lặp không decode lại ảnh ổn định.
- Independent Tester final `0 Critical / 0 Important / 0 Minor`; final immutable security discovery phủ 6/6 production file và candidate count `0`. `LIVE_PASS` vẫn `NOT_TESTED` trước deploy.

### 3.3 Progressive disclosure manual top-up — candidate M03B ngày 04/09/2026

- SPEC `CUST-WEB-MANUAL-TOPUP-PROGRESSIVE-DISCLOSURE-002`, BASE `b657cea98ecc0c2f6f962bf82f1044333dfe427e`, branch `fix/cust-web-manual-topup-progressive-disclosure-002`.
- Initial state chỉ có số tiền, selector phương thức và CTA xác nhận; destination, mã nạp, hotline, QR, reference và CTA đối soát đều vắng khỏi DOM. History/current record ở choose-state cũng không render `reference` hoặc `transfer_content`; explicit confirm mới mở chi tiết. Input/select click không tự xác nhận và không chặn native picker.
- Explicit local confirm kiểm số nguyên dương và fail closed trừ khi method thuộc projection VND, `request_enabled=true` **và** có đúng canonical same-origin QR route của chính method đó. Confirm không phát `ACTION_EVENT`, không POST API và chỉ hiển thị đúng một instruction/QR.
- `USDT TRC20 / Binance` được hiển thị discoverable nhưng disabled với copy “chưa hỗ trợ đối soát VND”; destination metadata không tạo authority VND. Back/change hoặc manual→PayOS→manual xóa confirmation, instruction, QR và reference cũ, nhưng giữ amount/method chưa xác nhận để khách không nhập lại. Logout, bootstrap signed account mới hoặc account switch xóa toàn bộ draft `/wallet/topup`, gồm cả amount/method.
- Light dùng chữ tối trên nền sáng; dark dùng chữ sáng trên nền tối. Placeholder/disabled control dùng semantic token có opacity `1`; mobile input tối thiểu `16px`, target tối thiểu `44px`.
- Final local rendered receipt: enabled VND method `5/5`, mỗi method đúng `1` instruction card + `1` matching signed QR, other-method card `0`, QR decode/load `5/5`; VI/EN/ZH × light/dark/system `9/9`; viewport `1440/1024/768/390/360` `5/5`; initial/back/lane-reset/relogin đều `QR=0`, final submit `0`, horizontal overflow `0`, relevant console error/warning `0`. Locale cuối được khôi phục VI.
- Contrast đo trên computed style: light small-label `5.282:1`, input text `12.352:1`, border `5.797:1`; dark tương ứng `9.701:1`, `15.172:1`, `9.053:1`. Receipt đã redaction, không chứa payment identifier/QR bytes: `reports/prepush/CUST-WEB-MANUAL-TOPUP-PROGRESSIVE-DISCLOSURE-002-RENDERED.json`.
- Một final-submit duy nhất trên DB tạm tạo đúng `1` request `125000 VND`, method `bank_acb_vietqr`, status `pending_admin_review`; decision receipt, wallet/ledger table và provider call `0`. Không final-submit production và không chạm production `MANUAL-1`.
- Final focused suite phải được chạy lại ngay trước commit; browser receipt nêu trên không thay test/CI. Integration chỉ đổi đúng one-line `/wallet/topup` session cleanup; final `manual-topup-create` handler phải tiếp tục byte-identical với BASE theo hunk comparator.
- Codex Security artifact đã review 6 dirty file và giữ report, nhưng workbench kết thúc `failed` do lỗi timestamp completion của plugin. Không gọi scan đó là PASS; ship chỉ mở khi independent fallback review trên exact frozen diff trả `0 Critical / 0 Important`.

## 4. Các route Web dành cho khách

- `POST /api/v1/payments/manual` — tạo yêu cầu manual top-up.
- `GET /api/v1/payments/options` — metadata signed, Web-local, `no-store`.
- `GET /api/v1/payments/options/manual-methods/{method_id}/qr` — QR private signed, fail closed.
- `GET /api/v1/payments/manual` — lịch sử owner-scoped.
- `GET /api/v1/payments/manual/{request_id}` — chi tiết owner-scoped.
- `GET /api/v1/payments/manual/{request_id}/status` — trạng thái rút gọn.
- Decorator và handler nằm tại `copyfast_api.py:4689-4763`.
- Placeholder công khai của Web là `{request_id}`.
- Owner khác đọc request không thuộc mình nhận response đã che thông tin.
- Invalid request ID không được dùng để truy vấn tùy ý vào Bot.

## 5. Các route Web dành cho Admin

- `GET /api/v1/admin/payments/manual` — hàng đợi có filter và limit đã kiểm tra.
- `GET /api/v1/admin/payments/manual/{request_id}` — chi tiết an toàn.
- `POST /api/v1/admin/payments/manual/{request_id}/draft` — tạo quyết định nháp.
- `POST /api/v1/admin/payments/manual/{request_id}/confirm` — xác nhận quyết định.
- Decorator và handler nằm tại `copyfast_api.py:4550-4675`.
- Cả hai write route cần signed Admin, CSRF và canonical Admin authority.
- Browser-supplied Admin ID bị bỏ qua hoặc bị từ chối trước bridge.
- Receipt từ Admin session A không dùng được ở session B.

## 6. Các route Bot dành cho owner

- `POST /internal/v1/payments/manual` — canonical create.
- `GET /internal/v1/payments/manual` — canonical owner history.
- `GET /internal/v1/payments/manual/{deposit_id}` — canonical owner detail.
- `GET /internal/v1/payments/manual/{deposit_id}/status` — canonical owner status.
- Decorator nằm tại `bot.py:274555-274732`.
- Placeholder nội bộ của Bot là `{deposit_id}`.
- Không đổi `{deposit_id}` thành `{request_id}` trong tài liệu route map; tên placeholder là một phần source truth.

## 7. Các route Bot dành cho Admin

- `GET /internal/v1/admin/payments/manual` — canonical Admin list.
- `GET /internal/v1/admin/payments/manual/{deposit_id}` — canonical Admin detail.
- `POST /internal/v1/admin/payments/manual/{deposit_id}/draft` — tạo token xác nhận nội bộ.
- `POST /internal/v1/admin/payments/manual/{deposit_id}/confirm` — quyết định canonical.
- Decorator nằm tại `bot.py:274983-275109`.
- Owner bearer gọi Admin route bị từ chối.
- Admin bearer gọi owner route bị từ chối.
- Admin token thiếu hoặc trùng owner token phải fail closed.
- Các denial này được khóa tại `tests/test_p0_manual_topup_cross_repo_integration.py:597-637`.

## 8. State machine và ý nghĩa tiền

- `pending_admin_review`: Bot đã ghi request/invoice chờ Admin; chưa cộng Xu.
- `awaiting_confirm`: Admin đã draft; đây là trạng thái envelope xác nhận, chưa cộng Xu.
- `approved`: Bot đã hoàn tất quyết định approve canonical.
- `rejected`: Bot đã hoàn tất quyết định reject canonical.
- Approve expected dùng số Xu do canonical Bot decision trả về.
- Approve custom yêu cầu số Xu và reason hợp lệ.
- Reject không tạo positive-credit, usage-credit hoặc revenue event.
- Status public không được lộ token, Admin ID riêng hoặc raw bridge response.
- Canonical status được kiểm tại `tests/test_p0_manual_topup_cross_repo_integration.py:380-476`.

## 9. Idempotency và concurrency

- Create dùng idempotency key để tránh tạo lại request do click/retry.
- Confirm dùng idempotency key và confirmation receipt.
- Hai confirm đồng thời chỉ được tạo một mutation canonical.
- Replay cùng key trả terminal result mà không cộng thêm.
- Dùng key khác với receipt đã dùng bị từ chối.
- Reject replay không tăng audit decision lần hai.
- Bằng chứng concurrency/replay nằm tại `tests/test_p0_manual_topup_cross_repo_integration.py:481-505`.
- HTTP retry không được coi là lý do hợp lệ để bỏ qua idempotency.

## 10. Auth, CSRF và ownership

- Signed Web session là nguồn account identity.
- CSRF bắt buộc trên customer create và Admin write.
- Canonical Admin ID được kiểm server-side bằng Bot authority.
- Anonymous customer/Admin read bị từ chối.
- Customer role không được gọi Admin list/draft/confirm.
- Foreign owner không đọc được detail/status của người khác.
- Forged Admin query/body/header không thay đổi canonical Admin identity.
- Cross-session, tampered và expired receipt đều bị từ chối.
- Các denial không được tạo wallet, usage, revenue hoặc audit mutation.
- Bằng chứng đầy đủ nằm tại `tests/test_p0_manual_topup_cross_repo_integration.py:510-589`.
- Raw Telegram ID trong browser không phải authentication; xem `docs/migration/TELEGRAM_WEB_CONNECTION.md:3-18`.

### Auth brand và viewport — candidate hotfix

- Candidate local: Auth header desktop/tablet có rail độc lập `620px`; card giữ `480px`.
- Brand mark không được flex-shrink và giữ `36×36px`; ảnh logo nằm trọn content box, không dùng translate/scale.
- Ba viewport `1056×763`, `844×610`, `390×667` được đo ở light/dark: `6/6` không horizontal overflow, control nhỏ nhất `44px`, card còn lề đáy tối thiểu `42.1px`.
- Đây là presentation-only behavior; không thay Auth API/session/form/routing.

## 11. Safe projection

- Safe projection là projection response theo owner/role, không phải màn hình xem trước giá.
- Owner projection không chứa Admin note riêng, decision token hoặc raw response.
- Admin projection chỉ chứa các trường đã allow-list cho nghiệp vụ duyệt.
- Not-found và foreign-owner response không được tiết lộ record tồn tại.
- Projection không trao quyền write; write vẫn cần role, CSRF và confirmation.
- Bằng chứng owner/Admin projection nằm tại `tests/test_p0_manual_topup_cross_repo_integration.py:380-420`.

## 12. Dữ liệu và artifact kiểm thử

- Integration test dùng Bot DB, Web session DB và legacy Web DB trong pytest temp root.
- Test không đọc database production.
- Test không gọi production endpoint.
- Test dùng actual Web app và actual Bot ASGI handlers; transport chỉ thay network.
- Test chặn PayOS, provider và Telegram delivery bằng sentinel.
- Test xác nhận external HTTP call count bằng `0`.
- Bằng chứng isolation nằm tại `tests/test_p0_manual_topup_cross_repo_integration.py:665-698`.
- `PRODUCTION_RECORD_COUNTS=NOT_MEASURED`.
- Không suy số bản ghi production từ fixture.

## 13. Các số đo source hiện hành

- `tracked_files=1033`: số path trả về bởi `git ls-files` trong Web worktree.
- `production_python_files=100`: tracked `*.py` sau khi loại test/docs/scripts/reports và cache/generated components.
- `fastapi_route_decorators=702`: AST count các decorator HTTP/WebSocket trong tập Python production trên.
- `test_files=352`: tracked `tests/**/test_*.py` theo basename.
- `migration_markdown_files=208`: tracked Markdown dưới `docs/migration/`.
- Định nghĩa và số đo được lưu trong inventory P0-05B; không dùng số cũ trong tài liệu Admin 27/08.

## 14. Configuration surface

- `CORE_BRIDGE_BASE_URL` — địa chỉ bridge server-side; không đưa vào browser.
- `INTERNAL_BILLING_TOKEN` — owner bridge bearer; giá trị không ghi trong Git/tài liệu.
- `INTERNAL_MANUAL_ADMIN_TOKEN` — Admin bridge bearer riêng; không được trùng owner bearer.
- `WEBAPP_COPYFAST_ENABLED` — feature gate chung.
- `WEBAPP_ADMIN_ERP_ENABLED` — Admin ERP gate.
- `WEBAPP_ADMIN_WRITES_ENABLED` — Admin write gate.
- Tài liệu chỉ nêu tên biến, không nêu giá trị, hash hoặc phương pháp suy ra secret.
- Thay đổi ENV/restart là một Owner gate riêng, không thuộc local acceptance.

## 15. Hướng dẫn vận hành an toàn

- Khi khách báo lỗi, ghi `request_id`, thời gian và trạng thái public; không yêu cầu gửi secret.
- Khi Admin xử lý, đọc detail rồi draft trước khi confirm.
- Kiểm tra action, số Xu dự kiến/custom và reason ngay trên confirmation UI.
- Không reuse receipt giữa hai browser session.
- Sau confirm, đọc lại owner status và canonical decision counts.
- Nếu response timeout, retry bằng cùng idempotency key; không tạo key mới tùy tiện.
- Nếu state guarded/unavailable, giữ trạng thái thật và mở incident; không dựng output giả.
- Không sửa SQLite trực tiếp.
- Điều chỉnh tài chính phải là audited compensating business action qua nghiệp vụ được Owner duyệt.
- Không xóa pending deposit hoặc finance invoice để “sửa nhanh”.
- Không chạy provider/PayOS/Telegram smoke chỉ để làm test xanh.

## 16. Cổng an toàn và rollback

- `PROVIDER_CALLS=0` trong toàn bộ local acceptance P0.
- `PAYOS_LIVE_CALLS=0` trong toàn bộ local acceptance P0.
- `TELEGRAM_LIVE_CALLS=0` trong toàn bộ local acceptance P0.
- `EXTERNAL_HTTP_CALLS=0` ngoài in-process ASGI transport.
- `PRODUCTION_WALLET_MUTATIONS=0`.
- `PRODUCTION_DATA_MUTATIONS=0`.
- `ENV_MUTATIONS=0`.
- `LIVE_MONEY_FLOW=NOT_TESTED`.
- Rollback source dùng Git revision/PR được kiểm soát; rollback dữ liệu tài chính không đồng nghĩa sửa DB tay.

## 17. PWA, private data và UI truth

- PWA chỉ cache shell/public allow-list.
- Wallet, payment, Admin, API, download và workspace record không được cache offline.
- PWA boundary được khóa tại `docs/migration/PWA_ROLLOUT_VERSIONING_CONTRACT.md:51-61`.
- UI phải hiển thị guarded/unavailable khi capability chưa sẵn sàng.
- UI direction cấm làm Bot-owned record hoặc provider unavailable trông như ready; xem `docs/UX_APP_FIRST_REDESIGN.md:5-12`.
- `availability` trong Admin navigation là metadata, không phải engine/payment live claim; xem `docs/migration/ADMIN_ERP_NAVIGATION_CONTRACT.md:43-55`.

### Motion khách hàng sau live-reopen

- Customer Web dùng nhịp presentation riêng: control `180ms`, state/navigation `360ms`, route/section entrance `680ms`, stagger `80ms` cho tối đa 6 item; token chung của Admin/Auth/Landing không bị tăng.
- Route entrance chạy trên container ổn định và sống qua cùng-route hydration; hydration không khởi chạy route entrance lần hai. Section đã ở trong viewport được settle ngay; section ngoài viewport chỉ reveal khi cuộn/focus tới.
- `/features` giữ bundle split `portal-features.js`, không tải lại full `portal.js`, `integration.js` hoặc `portal-motion.js`; motion split chỉ dùng DOM class, `IntersectionObserver`, RAF và cleanup.
- `prefers-reduced-motion: reduce` giữ toàn bộ content visible với opacity `1`, animation/transition/transform presentation bị tắt.
- Catalogue dài dùng `content-visibility:auto` và intrinsic block size để giữ 135 workflow trong DOM/search nhưng không layout toàn bộ nhóm ngoài viewport ở first paint.
- Local signed route matrix đã đo `/dashboard`, `/features`, `/studio`, `/wallet/topup` tại `1440×900` và `390×667`, normal/reduced: `16/16` content visible, overflow/CLS/page error/request failure/foreign request đều `0`. Dashboard long-task xuất hiện cả normal và reduced nên là baseline render debt, không phải motion regression; chuyển vào Customer Final thay vì sửa ké.

## 18. Việc còn mở

- `P0-05A`: rotate/revoke và loại ba credential-like tracked paths khỏi Bot HEAD theo security spec riêng.
- Tester workspace source có `43` case tuần tự; WA-41..43 thuộc đúng `A09-AUTH-ADMIN-SHELL-VERTICAL-RESPONSIVE-LOCALE`.
- Auth login brand/viewport hotfix đã deploy/live tại `0dd8ffa`.
- `MOTION-WEBAPP-SURFACES-001` đã accepted live trên runtime `b657cea…`; normal route/scroll/hydration và reduced-motion đều có matrix riêng.
- M03B progressive disclosure đã `ACCEPTED_LIVE` qua PR #422 tại main/runtime `d096bac…`; A09 shell PR #423 và Admin Support PR #424 đã deploy, nhưng A09 toàn Admin vẫn mở.
- GitHub CLI đã revalidate issue #412 OPEN, required labels `12/12` và local templates `2/2` ngày 04/09. Tester Project đã được xác minh tồn tại ngày 03/09; token hiện thiếu `read:project` nên chưa đọc lại Project ngày 04/09 và không tự mở rộng OAuth scope.
- Tester readiness `p0-05d.v2` lưu line/byte/SHA theo `utf-8-lf-portable`; cùng source CRLF trên Windows và LF trên Linux phải cho metadata giống nhau.
- Security source fix và local tests không thay signed production verification.
- ENV/secret rotation chưa được thực hiện.
- Underlying PR #420 signed customer create/read + Admin list/detail đã live-smoke trên đúng `MANUAL-1 pending_admin_review`; riêng M03B progressive UI chưa live trước deploy, và không chạy approve/reject/cộng Xu.
- Live money flow không được chạy khi chưa có Owner money gate.

## 19. Bản đồ bằng chứng

- P0-01 request bridge: `evidence/p0-01-codex-sol-manager-accepted-20260828.md`.
- P0-02 Admin decision bridge: `evidence/p0-02-primary-manager-accepted-20260828.md`.
- P0-03 customer Web flow: `evidence/p0-03-primary-manager-accepted-20260829.md`.
- P0-04 Admin Web queue: `evidence/p0-04-primary-manager-accepted-20260829.md`.
- P0-05 local cross-repo integration: `evidence/p0-05-local-integration-accepted-20260829.md`.
- P0-05B static inventory: `evidence/p0-05b-static-inventory-accepted-20260829.md`.
- P0-05E corrective: `evidence/p0-05e-primary-manager-verified-20260830.md` sau khi Manager closeout; trước khi file này tồn tại, trạng thái vẫn chưa ACCEPTED.
- Auth login brand/viewport: `evidence/auth-login-brand-viewport-001-20260831.md` và matrix JSON cùng tên.
- Customer motion live-reopen: `evidence/motion-webapp-surfaces-live-reopen-v2-20260831.md` + `evidence/motion-webapp-surfaces-live-reopen-v2-matrix.json`; video/frames nặng được giữ ngoài repo với SHA-256 ghi trong report.
- Current-main motion live retest: `evidence/motion-live-retest-b657/`.
- M03B pre-fix rendered/temp DB ngoài repo chỉ là historical diagnostic. Final redacted browser receipt: `reports/prepush/CUST-WEB-MANUAL-TOPUP-PROGRESSIVE-DISCLOSURE-002-RENDERED.json`; pre-push review: `reports/prepush/CUST-WEB-MANUAL-TOPUP-PROGRESSIVE-DISCLOSURE-002.md`.
- Các bằng chứng trên chứng minh local source/test; chúng không chứng minh production deployment hoặc live money result.

## Cập nhật vận hành WebApp — R217-07A và R218 plan — 18/10/2026

SubDub WebApp hiện có một workspace duy nhất với bốn hướng xử lý và bảy lựa chọn gán
giọng riêng: mặc định nữ, mặc định nam, giọng đã lưu, giọng tự thêm, Auto 2,
Auto Multi 3–8 và Smart Multi. Workspace còn nêu rõ nguồn đã có/chưa có phụ đề,
source auto-detect, catalog target đầy đủ theo VI/EN/ZH, bảy vị trí phụ đề, volume
âm thanh gốc/giọng lồng tiếng, speaker-map guarded và đường sang Voice Library.

- Regression SubDub: `14/14` đạt, `0` lỗi.
- Full Node suite hiện tại: `538/538` đạt, `0` lỗi.
- `node --check` Portal JS: `2/2` đạt; `git diff --check`: đạt.
- Provider calls: `0`; wallet mutations: `0`; production data mutations: `0`.
- Upload/preview, Voice Library data, preflight, confirm, provider bridge, speaker
  detection, output artifact và live report vẫn guarded; chưa gọi đây là parity runtime với Bot.
- Plan/checklist/spec mới: R218 trong `docs/superpowers/` và `reports/audit/`.

## 20. A09 Auth + Admin shell — trạng thái vận hành candidate 05/09/2026

- A09 là thay đổi presentation-only: không thay API, session, MFA, CSRF, role, schema, payment, wallet, provider hoặc Internal App.
- Admin sidebar dựng toàn bộ nhóm/module do `adminErpNavigation` server cấp theo dạng dọc. Browser không thêm route; nhóm hiện hành mở mặc định, các nhóm khác đóng nhưng vẫn discoverable.
- Horizontal app rail cũ đã bị loại khỏi renderer và CSS. Bảng dữ liệu vẫn có wrapper cuộn ngang cục bộ khi cần; toàn trang không cuộn ngang.
- Dashboard chỉ nhận bốn count key `users`, `engine_jobs`, `worker_jobs`, `payments`. Key phải là own-property, số hữu hạn và không âm; số `0` là dữ liệu thật. Missing/unrelated key không tạo card dấu gạch.
- Workload chỉ hiện khi có ít nhất một trong ba nguồn job/payment thật; readiness chỉ hiện khi có entry readiness thật. Khi mọi nguồn vắng, giao diện hiện đúng một empty state và không tạo KPI/chart giả.
- Danh sách route giao nhau với server grant được gọi đúng là `Truy cập nhanh / Quick access`; đây không phải task inbox.
- Public Auth và Admin-login có catalogue VI/EN/ZH đối xứng cho tên ngôn ngữ, theme fallback và fixed chrome; Admin header VI không còn nhãn cứng `VI / EN`.
- Desktop `>=981px` dùng sidebar `256px` và workspace `minmax(0,1fr)`; drawer sở hữu `<=980px`. Dưới `768px`, KPI/work list/content là một cột và giữ safe-area variables.
- Logo Admin dùng ảnh chính thức với `width/height/max-width=100%`, `object-fit:contain`, `transform:none`; tỷ lệ render đo được `1.00` ở 20 trạng thái Admin.
- Local evidence: focused `50P`; protected BASE/candidate `68P/2F`; expanded BASE/candidate `130P/3F`; exact failure IDs bằng nhau và `NEW_FAILURES=0`. Browser Admin `20` trạng thái + Auth comparator `24` trạng thái, aggregate `22/22`, relevant console event `0`.
- Codex Security inventory đã review `5/5` production paths và artifact sealed có findings `0`, nhưng workbench terminal `FAILED_INFRA` do sandbox parent-path. Đây là limitation, không phải security PASS.
- Candidate chưa merge/deploy/live. Chỉ sau PR, CI, runtime SHA, service health và signed production matrix mới đổi A09 sang `ACCEPTED_LIVE`.

### A09 mở lại — ngôn ngữ quản trị hỗ trợ, 08/09/2026

PR #423 đã đưa phần khung quản trị lên main tại `6298057…`. PR #424 đã sửa nhóm `/admin/support`, merge/deploy tại `cc3b468…`; source/runtime đạt nhưng signed production DOM chưa có nên chưa gọi `ACCEPTED_LIVE`.

- Nội dung cố định của danh sách/chi tiết hỗ trợ dùng danh mục dịch VI/EN/ZH; tên riêng, ID, nội dung khách hàng và mã nghiệp vụ không bị dịch.
- Ngày giờ dùng ngôn ngữ đang chọn; bản Việt không được rơi về tên tháng tiếng Anh.
- Kiểm thử Support cuối: `84 passed, 2 warnings`; trình duyệt QA có 40 trạng thái list/detail × VI/EN × sáng/tối × 5 kích thước. Kiểm tra ngôn ngữ và tràn/cắt nội dung đạt trong phạm vi đó.
- Báo cáo trình duyệt gốc vẫn giữ `consoleHealth=false`: 13 sự kiện thông tin cài ứng dụng và 1 phản hồi 401 trước đăng nhập cần phân loại theo giai đoạn. Không dùng báo cáo này để khẳng định production hoàn tất.
- Nguyên nhân cần tránh: dịch thanh điều hướng không đồng nghĩa dịch toàn bộ trang; mọi nhãn, mô tả, xác nhận, trạng thái rỗng và nhánh chi tiết đều phải được kiểm tra.
- Theo chỉ thị Owner, bản Việt giữ danh từ tiếng Anh và mã kỹ thuật quen thuộc trong allowlist hữu hạn (TOAN AAS, Web, Telegram, PayOS, Odoo, Bot, Email, App, ERP, CSRF, SLA, API, ID, PDF, QR, OTP/CVV, TXID, URL, định dạng ảnh/tệp và Xu). Các động từ, tính từ và câu hướng dẫn còn lại phải là tiếng Việt; bản Anh vẫn phải toàn bộ bằng tiếng Anh.

### A09 mở lại — Điều hành tự động, 10/09/2026

### Candidate kế tiếp — Theo dõi độ ổn định, 11/09/2026

- `/admin/reliability` chuyển nội dung cố định sang catalogue VI/EN/ZH: tiêu đề,
  mô tả, bộ lọc, phân trang, trạng thái, nút/xác nhận, tín hiệu và giới hạn hoạt động.
- Chưa có dữ liệu hợp lệ không được quy kết tài khoản thiếu quyền. Module chưa
  được bật hay kết nối chưa sẵn sàng không được coi là nghiệp vụ đã hoàn thành.
- Mã tác vụ, con trỏ trang, phiên bản, quyền và backend không đổi. Không bật ENV,
  gọi nhà cung cấp, sửa Bot hoặc thực hiện giao dịch tiền trong batch này.
- Candidate phân biệt ba trạng thái cấu hình: `enabled`, `disabled`, `unknown`.
  Chỉ phản hồi core status thành công với hai Boolean chính xác mới được dùng để
  kết luận bật/tắt; lỗi hoặc dữ liệu sai kiểu không bị quy thành thiếu quyền.
- Luồng hiển thị đã chuyển sang task-first: `Việc cần kiểm tra` đứng trước số
  liệu, tín hiệu và phần giải thích. Thông tin kỹ thuật/quyền được gom vào một
  disclosure đóng ban đầu; mã kỹ thuật nội bộ không xuất hiện trên mặt chính.
- Browser local enabled đo `20` trạng thái = VI/EN × sáng/tối × 5 viewport;
  disabled đo `8` trạng thái = VI/EN × sáng/tối × 1440/390. Cả hai report đều
  có overflow/clipping/event/write request bằng `0`; contrast nhỏ nhất của
  enabled là `5.8:1`; target tương tác tối thiểu `44px`.
- Full renderer kiểm VI/EN/ZH và 24 tổ hợp trạng thái/capability. Backend
  Reliability chạy trên DB tạm: `10 passed`, 1 cảnh báo Pydantic trong 35.08s.
- CUA/IAB chặn localhost nên Browser QA dùng Playwright/Chrome local; đây là
  local acceptance, chưa phải production. Production screenshot trước sửa vẫn
  trộn Việt-Anh và báo sai thiếu quyền; chưa gọi `ACCEPTED_LIVE` cho candidate.

### Bằng chứng lịch sử Operations

### Candidate — Hàng chờ bàn giao nội dung, 11/09/2026

- `/admin/content-handoffs` là hàng chờ Web-native riêng cho nhân viên; không đọc
  Bot bridge và không tự xuất bản hoặc gửi tệp.
- Candidate dùng catalogue VI/EN/ZH cho title, filter, status, decision, empty,
  guarded và pagination; title/purpose do người dùng nhập giữ nguyên ngôn ngữ gốc.
- UX task-first: filter → record → decision; thông tin quy trình/quyền thu trong
  một disclosure đóng ban đầu. Label form dùng semantic ink, không còn chữ trắng
  mờ trên light mode.
- Browser local `20` trạng thái = VI/EN × sáng/tối × `1440/1024/768/390/360`:
  mọi assertion đạt; minimum contrast `7.26:1`; overflow, clipping, framework
  overlay, relevant event, touch violation và staff write request `0`.
- Local fixture duy nhất là `review/revision=2`; không submit review. Focused
  backend/customer/staff suite đạt `63 passed`, một cảnh báo Pydantic.
- Đây là local acceptance; chưa merge/deploy/live. Customer create/detail, API,
  schema và transition values không đổi.

### Candidate — Theo dõi khách hàng tiềm năng ẩn danh, 12/09/2026

- `/admin/crm/leads` dùng manager directory Web-native chỉ đọc; server vẫn là
  nơi kiểm tra vai trò Admin, stage filter, phân trang và boundary. Không mở
  Core Bridge/Bot, không có chi tiết cross-account hay thao tác ghi.
- Renderer task-first đặt `Danh sách cần theo dõi` và bộ lọc trước kết quả; dữ
  liệu và giới hạn nằm trong disclosure đóng ban đầu. Loading và guarded không
  hiển thị hàng cũ.
- Catalogue `adminCrmManager.*` đối xứng VI/EN/ZH bao phủ tiêu đề, nhóm, giai
  đoạn, trạng thái đồng ý, bộ lọc, phân trang, empty, recovery và toast đọc.
  Giá trị canonical không đổi; nhãn và ngày giờ hiển thị theo locale.
- DTO giữ ẩn danh: không có mã lead, chủ sở hữu, tên, email, nhu cầu, nhãn,
  ghi chú hoặc liên kết chi tiết. Ở `≤900px`, hàng chuyển thành thẻ dọc có nhãn
  cột; màu và tương phản dùng token teal/cyan.
- Browser local đo `20` trạng thái = VI/EN × sáng/tối ×
  `1440/1024/768/390/360`; minimum contrast `5.28:1`; overflow, clipping,
  private leak, framework overlay, relevant console và write request đều `0`;
  filter `review` trả `1` hàng ẩn danh. Đây là local acceptance, chưa deploy/live.

### Candidate — Hàng việc điều hành, 12/09/2026

- `/admin/work-queue` là màn hình điều phối Web-native chỉ đọc; backend, năm
  nguồn, bộ lọc enum, quyền nhân viên và route đích không đổi.
- Renderer chuyển sang task-first: hero ngắn → `Việc cần xử lý` + bộ lọc →
  kết quả → `Nguồn dữ liệu` → phần `Dữ liệu và giới hạn` đóng ban đầu. Không còn
  phơi chuỗi kỹ thuật (`metadata`, `server-side`, `redaction`, `control plane`,
  `retry`, `provider`, `delivery`, `deploy`) trên mặt chính bản Việt.
- Catalogue `adminWorkQueue.*` đối xứng VI/EN/ZH bao phủ title, mô tả, nguồn,
  trạng thái, mức độ, bộ lọc, bảng, phân trang, empty/loading/guarded và recovery.
  Dữ liệu động (trạng thái canonical, thời gian, số lượng, route) không bị dịch
  hoặc tự suy diễn.
- Toast của bốn thao tác đọc (làm mới, áp dụng/xóa bộ lọc, chuyển trang) và lỗi
  thiếu quyền đều dùng cùng catalogue ở cả ba locale. Câu tóm tắt nguồn trung
  tính; khi partial vẫn hiện rõ nguồn chưa xác minh, không nói tất cả đã kiểm tra.
- Ở màn hình `≤900px`, bảng chuyển từng dòng thành thẻ dọc có nhãn cột; override
  mobile hủy tỷ lệ cột desktop nên không ép/cắt tên nguồn. Nút và điều khiển giữ
  chiều cao tối thiểu `44px`; light/dark dùng token teal/cyan và tương phản đo
  được.
- Browser local đo `20` trạng thái = VI/EN × sáng/tối ×
  `1440/1024/768/390/360`; toàn bộ assertion đạt, minimum contrast `7.62:1`,
  overflow, clipping, framework overlay, relevant console và write request đều
  `0`. Tương tác lọc `all → attention` trả đúng `3` dòng; disclosure mở/đóng
  được và đóng mặc định.
- Focused source/read-model/backend suite đạt `19 passed`; i18n locale bundle
  đạt `19 passed` với `1` cảnh báo Pydantic. Đây là local acceptance; chưa merge,
  deploy hoặc signed production LIVE.

#### Cập nhật readiness sau PR #425

PR #425 đã merge/deploy tại `24dda30a06838480f00b60668a5f7a78d8a3b43a`.
Quan sát signed production ngày 10/09 cho thấy thông báo thiếu quyền không phản ánh
đúng `autopilot_enabled=false`. Đăng nhập không còn là blocker.
Bản sửa kế tiếp `fix/a09-operations-readiness-truth` chưa triển khai:
phản hồi thành công với Boolean false mới chứng minh chưa bật; phản hồi thiếu,
lỗi hoặc sai kiểu là chưa xác minh; Boolean true không tự cấp quyền.
Loading và quyền manager/operator hiện hành giữ nguyên. Không bật module,
không thực thi quyết định, không thay ví hoặc cấu hình. Bộ kiểm thử mở rộng
ngày 10/09 đạt `61 passed in 8.20s`, exit 0; đây không phải live PASS.

Các số liệu local bên dưới mô tả batch PR #425 trước khi ship.

- Nhánh local `fix/a09-admin-operations-locale-purity` bắt đầu từ exact main `cc3b468…`; chưa commit/push/deploy.
- `/admin/operations` có catalogue riêng `adminOperations.*` với key VI/EN/ZH đối xứng. Guard/loading, Manager/Operator, partial, populated, empty, phân trang, xác nhận, sự cố và nhịp chạy đều qua catalogue; ID, mã tác vụ và mã máy vẫn giữ nguyên.
- Bố cục route dùng semantic teal/cyan của master design system: intro rõ quyền, bốn số liệu thật, hai cột quyết định/ranh giới và hai cột lần quét/sự cố; `<=980px` hạ một cột, `<=700px` toàn bộ thẻ và hành động xếp dọc. Không thêm số liệu hoặc biểu đồ giả.
- Root cause đổi ngôn ngữ không bền qua remount: biên nhận chỉ cập nhật `interfaceLocale`, trong khi renderer ưu tiên `profile.locale` cũ. Helper nay chỉ đồng bộ thêm scalar `profile.locale`; display name, timezone, session, role, identity và workflow giữ nguyên.
- Fresh focused gate: `151 passed`, `2` dependency warnings, `0` failed. Protected exact-main/candidate đều `68 passed / 2` CSS-tail baseline failures; `NEW_FAILURES=0`. Node syntax `3/3`, diff-check `0`.
- Signed local Browser: `20` trạng thái = VI/EN × sáng/tối × `1440/1024/768/390/360`; `14/14` assertions đạt, console/network sau readiness `0`, request ghi Operations `0`, page overflow/clipping/high-level horizontal scroller `0`, contrast và touch target đạt.
- Codex Security scan `8bc4f21a-ed08-46ed-a7ba-ec0a0ae6e8ed` lưu partial draft với `0` finding trên `7` changed-file surfaces; Workbench inventory lỗi `destination escaped its bound context`, nên đây không phải plugin PASS.

### Cập nhật WebApp UI shell ngày 16/10/2026

Bản WebApp candidate hiện giữ modal hướng dẫn cài ứng dụng trên nền xanh navy/xanh ngọc:
lớp phủ dùng `rgba(3, 20, 43, .86)`, thanh chọn tab dùng `rgba(5, 31, 57, .92)` và
không còn nền đen trong vùng modal. Đây là thay đổi giao diện tĩnh, không tạo request,
không đổi phiên đăng nhập, dữ liệu, ví Xu hay cấu hình vận hành. Regression riêng
`tests/install-modal-navy-palette.test.mjs` đạt `1 passed`, exit `0`; live production
chưa được gọi là đã cập nhật vì PR #647 chưa có deployment.

### Cập nhật locale Admin ngày 16/10/2026

Tám tiêu đề cố định của khu vực Quản trị hệ thống trong catalogue tiếng Việt đã được chuẩn
hóa: theo dõi tự động hóa, tình trạng bảo mật, quyền truy cập, tài liệu quản trị, kho tài liệu
nội bộ, hệ thống, môi trường chạy và bản sao lưu. Regression riêng đạt `1/1`; đây chỉ là thay
đổi copy Web, không cấp quyền, không tạo dữ liệu và chưa phải bằng chứng live.

### Ghi nhận source locale customer — Data Controls — 16/10/2026

Nhóm `accountCenter.dataControls.*` và mô tả `/account/data-controls` đã được chuẩn hóa
tiếng Việt ở lớp giao diện cố định. Phạm vi thay đổi chỉ gồm `static/portal/portal-i18n.js`,
`static/portal/portal.js` và regression `tests/data-controls-locale-purity.test.mjs`;
không đổi route, action, capability, CSRF, idempotency, revision, dữ liệu máy chủ,
ví/Xu hoặc nhà cung cấp. Regression riêng đạt `2/2`; toàn bộ Node đạt `480/480`;
hai tệp Portal qua `node --check` và `git diff --check` đều đạt. Đây là bằng chứng source
trên nhánh PR #647, chưa phải bundle đã giao, deployed hoặc live.

Bẫy cần giữ: fallback trong renderer cũng là giao diện người dùng. Nếu chỉ sửa catalogue mà
bỏ qua fallback, khi thiếu key bản Việt có thể quay lại các từ `review`, `export`, `signed`,
`authoring` hoặc `Web`; regression hiện khóa cả catalogue và fallback để ngăn lỗi này.

### Ghi nhận source locale customer — Trung tâm hỗ trợ — 16/10/2026

Nhóm `supportTicket.*` và fallback của các màn hình tư vấn, bằng chứng, yêu cầu, chi tiết,
đánh giá và phân loại vận hành đã được chuẩn hóa tiếng Việt. Regression
`tests/support-ticket-locale-purity.test.mjs` đạt `2/2`; catalogue cố định có `295` mục và
renderer giữ ít nhất `210` fallback an toàn. Route, action, field, capability, CSRF,
idempotency, revision, dữ liệu máy chủ, ví/Xu và nhà cung cấp không thay đổi; full Node đạt
`482/482`. Đây là bằng chứng source trên nhánh PR #647, chưa phải bundle đã giao, deployed hoặc live.

### Ghi nhận source locale customer — Hồ sơ tài khoản — 16/10/2026

Nhóm `accountCenter.profile.*` và fallback của trang `/account` đã được chuẩn hóa tiếng Việt;
101 mục catalogue được kiểm tra, bao gồm phiên đã xác thực, phương thức đăng nhập, hồ sơ,
liên kết Telegram, ảnh đại diện, tùy chọn Bot, nâng cấp Email và Trung tâm bảo mật. Các tên
riêng/mã kỹ thuật như Telegram, Google, GitHub, Apple, OAuth, CSRF, MFA, PayOS, Bot, Web,
URL, BOT_USERNAME và Core Bridge được giữ nguyên. Regression riêng đạt `2/2`, toàn bộ Node
đạt `484/484`, syntax hai tệp Portal đạt và `git diff --check` đạt. Route, action, field,
capability, dữ liệu hồ sơ, ví/Xu và nhà cung cấp không thay đổi; đây là bằng chứng source trên
nhánh PR #647, chưa phải bundle đã giao, deployed hoặc live.

### Ghi nhận source locale customer — Image Studio và Image Hub — 16/10/2026

Fixed chrome của Image Studio/Image Hub đã được chuẩn hóa qua catalogue `imageStudioUi.*`
đối xứng VI/EN/ZH, gồm guard, giới thiệu, số liệu, biểu mẫu bảng thiết kế, ranh giới biên
tập, ý định, định dạng, trạng thái và bộ lọc. Bản tiếng Việt không còn generic English UI;
các mã kỹ thuật, định dạng và tên riêng được giữ nguyên. Renderer dùng helper locale cho
option/status/fallback và bổ sung trạng thái `active` để bộ lọc phản ánh đúng dữ liệu.

Regression `tests/image-studio-locale-purity.test.mjs` đạt `2/2`; focused Image đạt `45/45`;
full Node đạt `486/486`; `node --check static/portal/portal.js`, `node --check
static/portal/portal-i18n.js` và `git diff --check` đều đạt. Route, action, field,
capability, CSRF, idempotency, revision, dữ liệu động, provider và ví/Xu không thay đổi;
Python contract chưa chạy vì môi trường không có `python`/`py`. Đây là source evidence trên
PR #647, chưa phải bundle đã giao, deployed hoặc live. Các cụm Image reference/detail,
Resize/Enhance/Brand Overlay/Storyboard vẫn là bước tiếp theo.

### Ghi nhận source locale customer — Image library và Image Hub — 16/10/2026

Fixed chrome của thư viện tham chiếu, thư viện bảng thiết kế, thẻ bảng thiết kế, tổng quan
Image Hub, các bước tiếp theo và bảng rà soát định hướng đã được đưa qua catalogue
`imageStudioLibraryUi.*` có `67` mục cân bằng VI/EN/ZH. Bản tiếng Việt không còn các cụm giao diện
`reference library`, `creative review`, `signed account`, `owner-check`, `Image operations
board`, `Independent next steps` hoặc `Direction review board`; nhãn bộ lọc, placeholder,
phân trang, trạng thái, lối tắt và empty state đều đi qua helper locale.

Regression `tests/image-studio-library-locale-purity.test.mjs` đạt `2/2`; focused Image
đạt `49/49`; full Node đạt `488/488`; syntax hai tệp Portal và `git diff --check` đều đạt.
Route, action, offset phân trang, capability, dữ liệu động, provider và ví/Xu không đổi;
Python contract chưa chạy vì môi trường không có `python`/`py`. Đây là source evidence trên
PR #647, chưa phải bundle đã giao, deployed hoặc live. Chi tiết direction card, estimate,
history và các route Resize/Enhance/Brand Overlay/Storyboard vẫn là bước kế tiếp.

### Ghi nhận source locale customer — Image Studio/Hub detail — 16/10/2026

Fixed chrome của trang chi tiết Image Studio/Hub đã được chuẩn hóa qua catalogue
`imageStudioDetailUi.*` gồm `91` mục cân bằng VI/EN/ZH: bản tổng hợp rà soát, thẻ biến thể,
trạng thái, lịch sử phiên bản, activity feed, tiện ích cục bộ và các nút xác nhận/khôi phục.
Helper `imageStudioDetailText` phủ estimate, direction card, detail renderer và nhãn event;
bản VI không còn các cụm raw `review estimate`, `Asset Vault refs`, `Archive artboard`,
`Direction library`, `Version history` hoặc `Audit-safe feed`.

Regression `tests/image-studio-detail-locale-purity.test.mjs` đạt `2/2`; focused Image
đạt `51/51`; full Node đạt `490/490`; syntax hai tệp Portal và `git diff --check` đều đạt.
Route, action, field, capability, CSRF, idempotency, revision, dữ liệu động, provider và
ví/Xu không đổi; Python contract chưa chạy vì môi trường không có `python`/`py`. Đây là
source evidence trên PR #647, chưa phải bundle đã giao, deployed hoặc live. Runtime/live,
browser AX tree và Image Resize/Enhance/Brand Overlay/Storyboard vẫn mở.

### Ghi nhận source locale customer — Image operations — 16/10/2026

Đợt `SOURCE-LOCALE-18` chuẩn hóa fixed chrome của Image Resize, Image Enhance, Brand Overlay
và Storyboard Grid qua catalogue `imageOperationUi.*` cân bằng VI/EN/ZH. Phạm vi gồm picker
Asset Vault, phân trang, guard/loading/failed, nhãn biểu mẫu và option, boundary, empty/result,
lịch sử Image, vị trí logo/chữ và xác nhận lưu tiếp tục/bàn giao. Brand Overlay đã bỏ nhãn
`Owner-scoped` cố định và thêm bản dịch xem trước công khai; Storyboard Grid đã chuyển toàn bộ
chuỗi mixed-language sang helper locale.

Regression mới `tests/image-operation-locale-purity.test.mjs` đạt `3/3`; focused Image/media
đạt `54/54`; full Node đạt `493/493` với baseline `490/490`, `NEW_FAILURES=0`. Hai tệp Portal
qua `node --check`, `git diff --check` đều đạt. Route, action, field, capability, CSRF,
idempotency, revision, download path, ownership/integrity guard và điều kiện
`completed + download_ready` không đổi; không gọi provider, không thay đổi ví/Xu/PayOS,
không tạo output giả. Python contract `NOT_RUN` vì môi trường thiếu `python`/`py`; đây là
source evidence trên PR #647, chưa phải bundle đã giao, deployed hoặc live. Browser/AX/live
recheck và các lane tiếp theo vẫn mở.

### Ghi nhận source locale — Channel Strategy và Workboard — 16/10/2026

`SOURCE-LOCALE-19` nối fixed chrome Channel Strategy vào catalogue `channelStrategyUi.*`
cân bằng VI/EN/ZH, gồm guard, thư viện, bộ lọc, phân trang, biểu mẫu, chi tiết, vòng đời,
định hướng, lịch sử, hoạt động, field label/help và aria text. Workboard dùng key locale cho
aria-label bảng Kanban và guarded recovery, không còn fallback tiếng Việt khi chọn EN/ZH.
Route/action/field/capability/revision/CSRF/idempotency và dữ liệu động không đổi.

Regression Channel Strategy `2/2`, Workboard `4/4`; focused Content/Workboard/Free/Memory/
Project/Publish/Campaign `28/28`; focused Image/media `54/54`; full Node `496/496`, baseline
`493/493`, `NEW_FAILURES=0`. Đây là source evidence; browser/AX/live và Python contract vẫn
chưa chạy, không gọi provider, không chạm ví/Xu/PayOS, không deploy hoặc merge.

### Ghi nhận source locale — Music Prompt Composer — 16/10/2026

`SOURCE-LOCALE-20A` chuẩn hóa fixed chrome Music Prompt Composer qua catalogue
`musicPromptComposerUi.*` cân bằng VI/EN/ZH: trang lập kế hoạch, biểu mẫu, boundary, ba hướng,
ghi chú sử dụng, biên nhận lưu Memory và phạm vi. Route/action/field/capability/CSRF/
idempotency giữ nguyên; không tạo âm thanh, tác vụ, thanh toán hoặc đầu ra giả.

Regression riêng `2/2`, focused Channel/Workboard/Music `8/8`, Image/media `54/54`, full Node
`498/498`, baseline `496/496`, `NEW_FAILURES=0`; browser/AX/live và Python contract chưa chạy.

### Ghi nhận source locale — Music Direction Presets — 16/10/2026

`SOURCE-LOCALE-20B` chuẩn hóa fixed chrome của Music Direction Presets qua catalogue
`musicDirectionUi.*` cân bằng VI/EN/ZH: preset card, form, receipt, boundary, checklist và
phạm vi. ID preset, route/action/field/capability/CSRF/idempotency và ranh giới không tạo âm
thanh giữ nguyên.

Regression riêng `2/2`; focused Composer/Direction/Voice/Media `31/31`; browser/AX/live và
Python contract chưa chạy. SFX Cue Sheet là nhóm kế tiếp.

### Ghi nhận source locale — SFX Cue Sheet — 16/10/2026

`SOURCE-LOCALE-20C` chuẩn hóa fixed chrome SFX Cue Sheet qua catalogue `sfxCueSheetUi.*`
cân bằng VI/EN/ZH: preset card, form, placement, receipt, danh sách cue, cảnh báo, boundary
và scope. Preset ID, cue family, placement ID, route/action/field/capability/CSRF/idempotency
giữ nguyên; không kiểm tra media, không tạo SFX/audio/provider/job/payment.

Regression riêng `2/2`, focused Composer/Direction/SFX/Voice/Media `33/33`, full Node
`502/502`, baseline `500/500`, `NEW_FAILURES=0`; browser/AX/live và Python contract chưa chạy.
## Checkpoint nguồn WebApp — SOURCE-ADMIN-05 Customer 360 — 17/10/2026

Candidate đã push là `a0069fa866a866dc319bcea91e5c2da867433c94` trên nhánh
`webapp-checklist-r116`/PR #647. Đợt này chỉ đổi fixed chrome Customer 360 và safety modal
trong `static/portal/portal.js` + `static/portal/portal-i18n.js`; không đổi route, action,
field, capability, CSRF, idempotency, revision, dữ liệu customer, RBAC/ABAC, ví/Xu, ledger,
Core Bridge write, provider hoặc deploy.

- Catalogue mới `adminCustomer360.*` có cùng bộ khóa trong đủ `3` locale: VI/EN/ZH.
- Regression mới đạt `3/3`; full Node suite đạt `512/512`; `node --check` cho `2/2` tệp
  Portal đạt; `git diff --check` đạt.
- Comparator source trước/sau giữ nguyên `771` occurrence `data-portal-action`, `630`
  occurrence `data-portal-route` và `439` occurrence `name`; `removed=0`, `added=0`.
- Contract Python `tests/test_p0_webapp_v2_05_admin_customer_360.py` chưa chạy được vì máy
  không có lệnh `py`/`pytest`; đây là blocker công cụ, không phải PASS.
- Browser/runtime/live và canonical-admin fixture chưa được chứng minh trong batch; `MERGED`,
  `DEPLOYED`, `LIVE` vẫn là các cổng riêng. `PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`,
  `PRODUCTION_DATA_MUTATIONS=0`.

### Bẫy cần giữ

Fixed chrome phải đi qua catalogue; không dịch `customer_id`, role/status server, mã case,
thời điểm, action/outcome audit hoặc số tiền. Không thay giá trị thiếu bằng số `0`, không biến
Customer 360 thành quyền ghi ví/ledger và không tuyên bố runtime chỉ từ source test.

Kết thúc checkpoint nguồn `SOURCE-ADMIN-05`.

## Checkpoint nguồn WebApp — R217-05 Voice workspace — 17/10/2026

Batch Voice tiếp theo của PR #647 chỉ thay trình bày WebApp trong `static/portal/portal.js`,
`static/portal/portal-i18n.js`, `static/portal/portal.css` và hợp đồng kiểm thử locale. Voice
Studio hiện mở đầu bằng ba lối vào dọc: giọng mặc định (`/voice/tts`), giọng đã lưu
(`/voice/saved`) và thêm giọng (`/voice/clone`). Mỗi thẻ có mô tả mục đích, CTA và nhãn được
bảo vệ; không thêm audio, upload, provider, job, wallet/Xu hoặc output giả.

- Catalogue `customerVoiceStudio` giữ đủ khóa VI/EN/ZH; lane rail có `3` thẻ và giữ nguyên
  route/action/field/capability hiện có.
- Voice Studio/Voice Vault dùng hệ xanh dương–xanh ngọc và nền xanh navy của portal; hover chỉ
  nâng `1px`, focus ring vẫn nhìn thấy, mobile chuyển về `1` cột ở `max-width: 820px`.
- Regression Voice/audio/SubDub đạt `126/126`; `node --check` `2/2` tệp Portal và
  `git diff --check` đạt. Đây là source evidence trên PR #647, chưa phải merge/deploy/live.
- TTS, clone, preview, output/download và dữ liệu Voice Library nối sang SubDub vẫn là
  `guarded` vì chưa có runtime/bridge evidence; không suy diễn source pass thành sản phẩm đã chạy.

## Checkpoint nguồn WebApp — R217-06 Music hub — 17/10/2026

Music hub được làm gọn theo một quy trình dễ đọc: chọn hướng → chuẩn bị mô tả → chờ hệ thống
xác nhận kết quả thật. Hai hướng chính là nhạc nền và bài hát có lời; hiệu ứng âm thanh giữ ở
nhánh bổ trợ. Các thẻ vẫn mở đúng `6` route hiện hữu (`/music/create`, `/music/song`,
`/music/sfx`, `/audio/assets`, `/music/library`, `/music/sfx-library`) và không thêm provider,
job, output, ví Xu hay thanh toán giả.

- Catalogue `musicHub.*` giữ đủ `3/3` locale VI/EN/ZH; nhãn hướng và mô tả trình đọc màn hình
  nằm trên từng card, không trộn English trong bản VI.
- Giao diện dùng token xanh/navy chung; desktop tối đa `2` cột, mobile chuyển `1` cột tại
  `max-width: 820px`; card chính có phân biệt thị giác nhưng không đổi route/action.
- Regression Music hub/library đạt `16/16`; `node --check` `2/2` tệp Portal và
  `git diff --check` đạt. Đây là bằng chứng source, chưa phải browser/runtime/live.
- Tạo nhạc, nghe thử, lịch sử, xuất tệp và output thật vẫn `guarded` vì chưa có bridge/provider
  evidence; không được báo parity runtime với Bot.

## Checkpoint nguồn WebApp — R217-07 SubDub single-screen — 17/10/2026

SubDub giữ một màn hình `/subdub` cho đủ `4` hướng: phụ đề gốc, dịch phụ đề, lồng tiếng và
phụ đề + lồng tiếng. Tab có thể điều khiển bằng bàn phím, đổi mode không điều hướng sang form
khác; hai panel có lồng tiếng dùng volume âm thanh gốc và giọng lồng tiếng riêng. Smart Multi,
Voice Library và mã ngôn ngữ ISO mở rộng hiển thị đúng biên guarded để người dùng hiểu bước
tiếp theo mà không nhầm là đã có engine.

- Regression `tests/subdub-hub-presentation.test.mjs` đạt `11/11`; có đủ VI/EN/ZH, trạng thái
  báo cáo rỗng và không có CTA tạo job/provider/wallet giả.
- Link `Mở Thư viện giọng` xuất hiện `2` lần cho hai panel liên quan và giữ route `/voice-studio`;
  dữ liệu Voice thật, upload, Smart Multi backend và output dubbing vẫn chưa có evidence runtime.
- Không gọi provider, không tạo video/audio/subtitle, không đổi Xu/PayOS hoặc dữ liệu production;
  source pass không phải parity runtime với Bot.

## Checkpoint nguồn WebApp — R217-08 Product Video hub — 17/10/2026

Hub Product Video được sắp xếp lại theo `4` lane dọc: lập kế hoạch, tạo video, biên tập/ghép
và kiểm tra/bàn giao. Danh mục giữ `10` route hiện hữu, không thêm route hoặc thay đổi action:
`/video-studio`, `/video/long`, `/video/product`, `/video/text-to-video`, `/video/multiscene`,
`/video/frame-sequence`, `/video/finishing`, `/video/mux`, `/video/preview`, `/video/poster`.
Mỗi lane nêu đầu vào, đầu ra và trạng thái; hub có quy trình `7` bước nhập → lập kế hoạch →
xem báo giá → xác nhận → theo dõi → nhận kết quả → khôi phục. Một panel riêng phân biệt nhánh
AI và nhánh thủ công để không nhầm bản kế hoạch với video đã tạo.

CTA chính của nhóm Bắt đầu nhanh được đánh dấu tường minh trên `/video/finishing` (biên tập và
hoàn thiện). `/video-studio` (lập kế hoạch) và `/video/text-to-video` (tạo video) vẫn là hai
lối phụ; không suy ra CTA chính theo vị trí mảng để tránh browser gate và trợ năng đọc nhầm
luồng lập kế hoạch thành luồng vận hành.

- `tests/video-uiux-locale-presentation.test.mjs`: `11` test, `11` passed, `0` failed;
  full Node suite `523` passed, `0` failed; catalogue VI/EN/ZH cân bằng, route và flow
  bảy bước được giữ nguyên.
- `node --check static/portal/portal.js`, `node --check static/portal/portal-i18n.js`
  và `git diff --check` đạt.
- GitHub Actions run `39018249838` trên candidate `59afdf7a8367a0126c6078f40c75dbce019966ae`
  đã đạt: browser gate kiểm đủ `6/6` hub, tạo `18` screenshot, browser runtime assertions,
  upload evidence và diff gate đều thành công.
- Đây chỉ là source presentation evidence. Upload, render, delivery, download và artifact
  video thật vẫn `guarded`; không gọi provider, không tạo job/MP4 và không đổi Xu/PayOS hay
  dữ liệu production.

## Checkpoint nguồn WebApp — R217-09A Content/Workboard/Free Tools — 17/10/2026

Các surface Content Studio, Workboard, Free Tools, Free Prompt Gallery, Memory, Projects,
Publish Review và Campaign đã được kiểm lại theo cùng checklist. Lệnh focused hiện hành chạy
`26` test, `26` passed, `0` failed; full Node suite trên candidate chạy `522` passed, `0` failed.
Các route/action/field/revision, bản nháp và trạng thái guarded giữ nguyên. Browser/AX,
responsive runtime và dữ liệu ghi thật chưa có môi trường QA nên vẫn mở; không gọi provider,
không tạo output và không ghi dữ liệu production. Wave source này đóng, chuyển sang rà Admin.

## Recheck nguồn WebApp — R217-09 Admin/customer visibility — 17/10/2026

Bộ `tests/admin-*.test.mjs` hiện chạy `21` test, `21` passed, `0` failed; full Node suite
`522` passed, `0` failed. Fixed chrome, điều hướng dọc, locale VI/EN/ZH, Customer 360,
Provider, nạp thủ công, finance/domain center và mobile harmony đều có evidence source.
Quyền Owner/role, liên kết request/job/asset/report/audit, canonical-admin fixture, duyệt
ledger/Xu và browser/AX runtime vẫn chưa có bằng chứng phù hợp; giữ `OPEN/DEFERRED`, không
ghi PASS thay cho backend permission hoặc mutation thật.

## Checkpoint vận hành — R217-12 auth locale return — 17/10/2026

Candidate `0ad78e5` sửa một seam trình bày trước phiên đăng nhập: khi khách mở route được bảo vệ
với `?lang=vi|en|zh`, máy chủ đưa locale đã allowlist lên cả URL `/login` và return target đã mã
hóa. Bộ lọc phía trình duyệt chỉ chấp nhận đúng một tham số `lang` trong ba giá trị này; query
khác, fragment, đường dẫn ngoài, dấu `\\` và vòng lặp auth bị loại bỏ. Route, quyền, phiên, API,
ví/Xu, Bot bridge và dữ liệu production không đổi.

- Bằng chứng source: focused `17/17`, full Node `525/525`, `node --check` hai tệp JavaScript,
  `py_compile` `4/4`, `git diff --check` đạt.
- Trạng thái giao nhận: commit đã tạo trên `webapp-live-r117`, chưa CI/deploy/live; không được
  gọi đây là locale đã sửa trên production cho đến khi recheck trực tiếp chứng minh.
- Blocker kiểm thử: `pytest` chưa chạy vì Python bundled không có module `pytest`; CI phải chạy
  lại bộ Python trước delivery.

## R218 — Cập nhật evidence sau WIP SubDub control — 18/10/2026

- Source candidate đã push của PR #654: `db8faa41fd059467d8f084a7661a01e53f4a5e85`.
- CI run `39101124230`: `Verify Web App=SUCCESS`, `Authenticated WebApp QA=SUCCESS`;
  ma trận route/render ghi nhận `456/456` case trên customer/admin, VI/EN/ZH,
  light/dark và phone/tablet/desktop.
- Local gate của SubDub presentation: `14/14` test mục tiêu, `node --check
  static/portal/portal.js`, `git diff --check`, full Node `538/538`.
- Kết luận vận hành: chỉ khóa được lane presentation, locale, selector và route/render
  evidence; đợt này bổ sung source state, language catalog, 7 subtitle positions và
  ba lane Auto canonical. Chưa có bằng chứng server capability, upload, quote, job, provider output,
  artifact delivery hoặc live production; `PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`,
  `PRODUCTION_DATA_MUTATIONS=0`, `LIVE_PASS=NOT_TESTED`.
- Ba lane Auto 2, Auto Multi 3–8 và Smart Multi vẫn là ba callback riêng; không được
  gộp thành một engine hay suy diễn từ route matrix.

## R218 — Toàn sản phẩm, nguồn Bot và checkpoint trước SubDub control patch — 18/10/2026

R218 hiện bao phủ Voice, Music/SFX, SubDub, Image, Product Video/AI và manual edit,
Dịch/Content/Free/Memory/Documents/Assets/Projects, AutoPost/Support/Account và
Admin/app nội bộ. Inventory B01–B34 có nguồn menu/handler và spec theo control.

Phần SubDub trong đoạn checkpoint này là snapshot trước control patch: thẻ disabled,
selector lặp/hidden field, link kho giọng và volume 0–200 còn cần review theo spec mới.
Bot source không là runtime proof: Music editor còn guard, hai track delivery chưa
chứng minh, Video AI edit có catalog nhưng disabled, long/series có execution lock.

CI run 39098833727 trên candidate 235d83661e78fd670bf09d58a436f114ea5ce14b đã
SUCCESS (Verify Web App 2m31s, Authenticated QA 4m09s). Bản mở rộng tài liệu R218
cần CI riêng sau push. Không suy test xanh thành product parity hoặc LIVE.
Voice/Music và các sản phẩm khác chỉ mở sau plan + WIP checkpoint, Video sau cùng
sản phẩm, motion cuối. Backend/provider/wallet/PayOS/publish giữ T0 và đợi lệnh.
## R218 — Khóa control Voice tốc độ và âm lượng — 18/10/2026

- Candidate source cho batch UI/UX hiện tại: `814b70cee2b6f4d2d1d2db23c903bfc0ca3d50bd` trên nhánh `webapp-r217-subdub-ui-r218`.
- `/voice/tts` và `/voice/saved` dùng cùng hợp đồng control: `speed` là một ô số từ `0,1` đến `2,0`, mặc định `1,0`, có 3 mức gợi ý; `volume_percent` là một ô số từ `0` đến `200` kèm thanh kéo đồng bộ, không tạo field gửi trùng.
- Nhãn, trợ giúp và preset lấy từ catalogue VI/EN/ZH; không còn giá trị biểu tượng `normal/slow/fast` trong payload.
- Bằng chứng local: `3/3` test control, `97/97` Voice regression, `530/530` full Node, `node --check static/portal/portal.js`, `git diff --check`.
- Đây chỉ là khóa trình bày và payload UI. Volume `0` warning, quote stale, Voice Vault/runtime execution, file output và live/CI vẫn chưa được coi là hoàn tất.

## R218 — Image four-mode control checkpoint — 18/10/2026

`/image/create` đã được sắp lại thành một cụm mode dọc, rõ theo đúng thứ tự người dùng:
Tạo ảnh, Câu lệnh từ ảnh, Chỉnh sửa AI và Chỉnh sửa thủ công. Mode tạo ảnh giữ form
`prompt/tier/format` và flow báo giá hiện có; mode tham chiếu mở `/image-studio`; mode
AI mở `/image/transform`; mode thủ công mở `/image/edit`. Ba mode ngoài tạo ảnh hiển thị
trạng thái chờ quyền xử lý để không nhầm rằng engine đã mở.

Đây chỉ là hoàn thiện control-level UI/UX và locale VI/EN/ZH. Không có upload, preview,
ảnh giả, provider, job, quote, delivery hoặc thay đổi Xu. IM-02 và IM-07..10 vẫn mở,
chờ capability/source/runtime/browser evidence.

## R218 — Music control-level guarded — 18/10/2026

Batch Music chỉ thay đổi lớp trình bày và bản nháp an toàn trên WebApp:

- `/music/create` và `/music/song` có một workspace dọc gồm `4` bước: nhập mô tả, chọn thông số,
  so sánh `3` phương án và nhận tệp/báo cáo.
- Hai route hiển thị `3` tier bằng trạng thái chờ máy chủ; route bài hát giữ các field
  `brief`, `tier`, `mode`, `vocal_mode`, `lyrics`, `song_length_mode`, `duration_seconds`.
  Route nhạc nền không lộ các field chỉ dành cho bài hát.
- Không còn provider badge, giá hard-code, player, tên MP3, download hoặc thông báo tạo tệp
  giả trong workbench Music. Khi capability chưa bật, cờ `data-music-product-enabled` giữ
  toàn bộ field ở trạng thái khóa.
- Catalogue `musicProduct.*` có cùng bộ khóa ở `3/3` locale `vi/en/zh`; theme giữ palette
  xanh/ngọc hiện tại, card dọc và breakpoint `980px/640px`.

Bằng chứng source-only: Music control `7/7`, focused Music+Voice `19/19`, nhóm Music
hub/prompt/library `25/25`, full Node `537/537`, `node --check` và `git diff --check`.
`PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`, `PRODUCTION_DATA_MUTATIONS=0`, `DEPLOY=NO`,
`LIVE_PASS=NOT_TESTED`.

Đây chưa phải Music runtime: tạo nhạc, báo giá/xác nhận, chỉnh nhạc, trình phát, tải, lưu,
dùng lại, lịch sử, giao tệp hai bản và bằng chứng trình duyệt/CI/live vẫn mở trong checklist
R218.

## R218 — Utilities/Content/Projects locale checkpoint — 18/10/2026

Đã rà soát và khóa phần giao diện cố định của Content Studio, Content Prompt Pack, Prompt
Gallery, Công cụ miễn phí, Memory Center/Reminder, Project Center và Workboard. Content Prompt
Pack hiện dùng một catalogue VI/EN/ZH cân bằng cho biểu mẫu, gợi ý, trạng thái rỗng, kết quả,
biên nhận và ranh giới xử lý; bản VI không còn các nhãn giao diện tiếng Anh như `Draft composer`,
`Execution boundary`, `Provider call` hoặc `Local deterministic draft`. Chủ đề, nội dung, tên
server, nhãn kiểm tra và biên nhận owner-scoped vẫn giữ nguyên, không tự dịch dữ liệu người dùng.

Bằng chứng local: `25/25` test focused Utilities/Content/Projects, `node --check` cho
`portal.js` và `portal-i18n.js`, `git diff --check` đều đạt. Đây là bằng chứng control-level
và locale; upload, dữ liệu thật, phiên bản, provider, publish, ví Xu, browser/AX và LIVE vẫn
chưa được coi là hoàn tất.

## R218 — AutoPost Hub control-level — 18/10/2026

`/publishing` hiện có một không gian làm việc dọc duy nhất cho AutoPost, gồm `7` nguồn đầu vào
và `5` bước theo thứ tự: chọn nguồn → lập kế hoạch/thương hiệu → chọn kênh → lịch/hàng đợi →
báo cáo/lịch sử. Các lane thương hiệu, lịch nội bộ, rà soát trước khi đăng, kênh, hàng đợi và
Affiliate được nối bằng handoff Web-native hoặc hiển thị trạng thái chờ quyền máy chủ.

Đã đo: `tests/autopost-hub-product-controls.test.mjs` `4/4`, full Node `562/562`,
`node --check static/portal/portal.js` đạt, `node --check static/portal/portal-i18n.js` đạt,
`git diff --check` đạt. Locale VI/EN/ZH dùng cùng bộ khóa; giao diện giữ màu xanh/ngọc và
chuyển thành một cột ở màn hình hẹp.

Đây chỉ là control-level/presentation. Chưa có OAuth/kết nối kênh, lịch đăng thật, biên nhận
publish, Affiliate metrics, queue receipt, provider call, job, giao tệp hoặc live evidence.
Không tạo dữ liệu production, không gọi provider, không đổi ví/Xu hoặc PayOS.

## R218 — Trung tâm hỗ trợ khách hàng control-level — 18/10/2026

Lát WebApp hiện có một luồng hỗ trợ dọc cho `/support`, `/tickets`, `/tickets/:id`,
`/admin/support` và `/admin/support/:id`: tiếp nhận, lọc/phân trang, chi tiết/dòng thời gian,
phản hồi công khai hoặc nội bộ, trạng thái/khôi phục, phản hồi kết quả và liên kết bằng chứng
từ Asset Vault. Bản Việt dùng tên “Trung tâm hỗ trợ khách hàng”; bố cục case chuyển một cột ở
`<=620px`, giữ palette xanh dương/xanh ngọc.

Đã đo: `tests/support-hub-product-controls.test.mjs` `4/4`, full Node `566/566`, hai lệnh
`node --check` và `git diff --check` đạt. Đây là control-level/presentation evidence; capability
server, dữ liệu thật, browser/AX, CI, delivery và LIVE chưa đóng. Trung tâm hỗ trợ không upload
bytes thô, không tạo ticket Bot, không gọi provider, không thay đổi ví/Xu, PayOS hoặc dữ liệu
production.

## R218 — Voice: phản hồi biểu mẫu và điều hướng kho giọng — 18/10/2026

`/voice/tts` và `/voice/saved` đã có số đếm từ/ký tự và cảnh báo khi âm lượng bằng 0.
Nhập số hoặc kéo thanh cập nhật tại chỗ; hydration giữ nguyên lời thoại và giá trị 0.
Cảnh báo dùng chữ tương phản trên nền xanh/ngọc ở cả hai theme. Nhãn accessibility của
preset tốc độ đã được dịch đầy đủ; không còn “Reading speed gợi ý” ở bản tiếng Anh.

Kho giọng có `2` liên kết mở SubDub và công cụ video. Các link không chuyển giọng đã chọn,
nên đã sửa nhãn từ “Dùng trong…” sang “Mở…”. Dãy `4` nút quản lý luôn khóa đã được bỏ,
thay bằng một thông báo ngắn. Rename/default/delete/preview và profile handoff vẫn chưa có
contract máy chủ; chúng tiếp tục là yêu cầu chưa hoàn tất trong ledger.

Bằng chứng local: Voice input/inventory/flow/expiry `67/67`, full Node `594/594`,
`node --check` đạt cho `portal.js` và `portal-i18n.js`, `git diff --check` đạt; catalogue có
đủ `3/3` locale `vi/en/zh`. `PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`,
`PRODUCTION_DATA_MUTATIONS=0`, `DEPLOY=NO`, `LIVE_PASS=NOT_TESTED`.

## R218 checkpoint 2026-10-21 — trạng thái vận hành WebApp hiện tại

Đây là số đo của checkout QA hiện tại, không phải số đo production và không phải bằng chứng đã triển khai live.

| Hạng mục | Số đo / trạng thái | Bằng chứng |
|---|---:|---|
| JavaScript toàn repo | 813 đạt / 0 lỗi | `node --test tests/*.test.mjs` |
| Hợp đồng bản nháp an toàn | 17 đạt / 78 bỏ qua theo bộ lọc | `pytest ... -k workspace_draft` |
| Syntax Portal | 2/2 tệp đạt | `node --check static/portal/portal.js`, `portal-i18n.js` |
| Music intake | 18 cấu hình, 36 route states, 3 lần ghi QA | `R218-NATIVE-DRAFT-SAFE-FIELDS-QA-20261020.json` |
| SubDub presentation | 48 trường hợp, 4 mode, 7 voice lane | `R218-SUBDUB-PRESENTATION-QA-20261020.json` |
| Image presentation | 72 trường hợp, 4 lane | `R218-IMAGE-PRESENTATION-QA-20261020.json` |
| Utility/Account/AutoPost/Support/Workboard/Memory | 120 trường hợp, 10 route | `R218-UTILITY-PRESENTATION-QA-20261020.json` |
| Video presentation | 48 trường hợp, 4 lane cốt lõi | `R218-VIDEO-PRESENTATION-QA-20261020.json` |
| Motion lifecycle | 29 static/lifecycle assertion; 12 browser case | `R218-MOTION-QA-20261020.json` |
| Provider / wallet / production mutation | 0 / 0 / 0 | các artifact checkpoint R218 |
| QA server tạm | Đã dừng, port `7628` không còn listener | terminal probe 2026-10-21 |

Runtime engine thật, upload byte, ASR/dịch/lồng tiếng, Smart Multi execution, quote/charge/job/artifact/delivery,
OAuth/publish, Admin RBAC dữ liệu động và approval/credit vẫn là cổng chưa nghiệm thu. Trace CLS/LCP/INP là
`NOT_RUN`; không dùng browser smoke thay trace. Máy chủ QA dùng DB/tệp tạm và Core Bridge/PayOS/provider bị vô hiệu hóa.

## R218 — Admin data mobile cards — 19/10/2026

Các bảng dữ liệu Admin đã được cấp vẫn giữ nguyên bảng HTML có tiêu đề cột và bộ lọc/inspector.
Ở màn hình rộng `<=560px`, mỗi bản ghi được trình bày thành một thẻ dọc; nhãn cột được gắn
từ chính `thead` sau khi renderer đồng bộ, nên không lặp danh sách nhãn thủ công và không đổi
record, permission hay trạng thái server. Màn hình desktop/tablet giữ bảng và vùng cuộn hiện tại.

Đã đo: `tests/admin-mobile-data-harmony-source.test.mjs` `2/2`, full Node `705/705`,
`node --check static/portal/portal.js`, và `git diff --check` đều đạt. Đây là thay đổi
presentation-only; chưa phải bằng chứng dữ liệu Admin thật, RBAC server, approval tiền,
browser đăng nhập hoặc LIVE.

Browser renderer QA localhost: `18/18` cấu hình VI/EN/ZH × sáng/tối × 390/768/1440,
hai route/cấu hình; lỗi trang/console, overflow, request ngoài localhost và mutation đều `0`.
Tương phản cảnh báo: `11,25:1` ở theme sáng và `8,84:1` ở theme tối. Dữ liệu phiên là fixture,
`integration.js` không được nạp: không phải kiểm thử API, DB, provider hoặc LIVE.

Evidence local ở `../qa/r218-voice-input/result.json`, AX và PNG cùng thư mục. Quote expiry UI
đã khóa; phần còn treo: search/page server, profile-aware handoff, rename/default/delete/
preview thật, confirm/progress/output và browser QA đăng nhập thật/live. Các mục này tiếp tục ở P1.

## R218 — Voice STT workspace control-level — 18/10/2026

Voice đã bổ sung lane **Giọng nói thành văn bản** vào cùng workspace dọc với bốn lane
Văn bản thành giọng nói, Giọng nói thành văn bản, Kho giọng và Thêm giọng. Route `/voice/stt`
và alias `/voice/asr` giữ cùng ranh giới guarded; biểu mẫu chỉ trình bày tệp audio/video,
ngôn ngữ nguồn (có Tự nhận diện) và định dạng Văn bản/SRT/VTT. Không tự tạo transcript,
không upload bytes, không gọi provider và không tạo job/quote/đầu ra.

Đã đo: contract STT/workspace `4/4`, quick-switch locale kiểm đúng `152` destination ở
`vi/en/zh`, toàn bộ nhóm Voice `132/132`, full Node `598/598`, `node --check` cho
`portal.js` và `portal-i18n.js`, `git diff --check` đều đạt. Đây là bằng chứng source/control-level;
MIME/size/ownership server, tiến trình, transcript/copy/export, browser/AX upload, delivery
và LIVE vẫn chưa đóng. `PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`,
`PRODUCTION_DATA_MUTATIONS=0`, `DEPLOY=NO`, `LIVE_PASS=NOT_TESTED`.
