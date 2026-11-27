# Chức năng gốc và hiện tại — TOAN AAS Web App

## 27/11/2026 — thông báo quản trị giữ chức năng, bỏ chữ kỹ thuật

GSC đã giao PR819/runtime5f316f29; trạng thái GSC pending bên dưới là lịch sử.
Nguồn đối chiếu AGC: `actionBlockReason`, `renderSupportAdminBase`,
`renderOperationsAdmin`, hai copy arrays tại GitBASE5f316f29 và
masterR217/R218. Không suy chức năng provider từ các câu giới thiệu cũ.

| Trước AGC | Ứng viên đã đo local | Giữ nguyên |
|---|---|---|
| Lý do khóa thao tác chứa tên cấu hình/cơ chế |12key×3locale, lời hướng dẫn ngắn qua uiText |Mọi điều kiện,thứ tự,canAct,capability |
| Support giới thiệu/guard/loading có chữ triển khai |7row×3locale theo đúng ngôn ngữ |Bộ lọc,danh sách,form,ARIA,dữ liệu khách |
| Khung cuối trang chỉ giải thích ranh giới kỹ thuật |Bỏ đúng một section,không ô thay thế |Summary,phân trang vàquyền |
| Operations trộn trạng thái với cơ chế |12row×3locale,giữ nghĩa chưa bật/chờ/lỗi/partial/manager |Role,count,IDs,handlers |
| Payment branch từng được QA giả định reachable |Dùng constant Web thực;BASE/current cùng disabled vàlocal-action precedence |Không sửa logic tiền hoặcđổi thứ tự |
| Historical comparators khóa copy cũ |Finite22record/5owner source và31key snapshot inverse |Old pins/assertions nguyên vẹn;native primary đọc raw |

129native,consumer222/Gallery130 đã khép;browser108componentviews/36guard
đạt với0error/overflow/egress. Không thay thế bằng chứng mounted/auth,
contrast toàn bộ,device/Safari hoặc signed-production. AGC chưa phát hành.

## 27/11/2026 — danh mục tĩnh có nội dung theo ngôn ngữ, ứng viên local

GPC/GPR bên dưới đã giao quaPR818/runtime29e0c154; không còn là ứng viên.
Đợt GSC hiện chưa phát hành. Nguồn gốc:
`docs/migration/FREE_PROMPT_GALLERY_CONTRACT.md` và canonical snapshot
2026-07-15.1;không suy khả năng chạy provider từ tên câu lệnh.

| Chức năng gốc | Ứng viên GSC đã đo local | Ranh giới giữ |
|---|---|---|
| Danh mục140mẫu pha Việt/Anh |117row/351value,420bản mở rộng native đã kiểm |7nhóm/20ngành/IDs/order/snapshot |
| Nhãn mục tiêu/nền tảng hiện enum |16key/48value và unknown text giữ nguyên |Option values/payload không dịch |
| Tìm trên canonical text |Native fields và native taxonomy labels trước paginate |Tìm enum IDs cũ,filter guards |
| Copy đọc item.prompt,save tự resolve ID |List/detail/native note dùng cùng nguồn;clipboard nguyên bytes |Body chỉ idempotency_key,không nhận prompt từ browser |
| Ghi chú đã lưu chứa nội dung cũ |Không rewrite;legacyVI retry cùng note |SQL/schema/ownership/CSRF/receipt |
| Cache chỉ kiểm shape/snapshot |Locale-owner RAM ngoài DTO,đổi locale phải nạp lại |DTO/route/generic API giữ |
| Phản hồi muộn bật control lựa chọn mới/cached selection cũ chiếm lựa chọn mới |55ca currentness cuối đạt |Release/discard intent luôn thực hiện;savecapabilitygiữ |
| Comparator nguồn khóa mốc trước |7failure→finiteleaf70PASS/135composedPASS |Fixture/pin/kỳ vọng cũ giữ,chỉ project input |
| Comparator toàn nguồn backend/integration ở121consumerfiles |3121PASS giữ;40FAIL→40PASS sau169finitepressure |Đúng7backend/11integrationrecords;không chạy lại3121PASS |
| Python historicalconvergence choUI mới |187pressurePASS;255consumer253PASS/2BASEfail,warningtarget1GREEN |Giữoldpins/assertions,khôngkhôiphụccâukỹthuậtBASE |

14ca backend mới đạt;34ca affected có32đạt và2BASE-equivalent do thiếu
tzdata trên Windows;không đổi nhắc lịch để né môi trường.
Browser54cảnh là actual renderer/normalizer/i18n/CSS qua localhost,
không phải thao tác ghi production. Gate mounted riêng3locale390×844
đã đi từsignedshell/profilelocale đếnfilter/detail/clipboard/newMemorynote
trênDBtạm;display/copy/note exact,mỗi account0→1note,0lỗitrang/console/
unexpected. Live/customer production session vẫn mở.

## 27/11/2026 — Thư viện: giữ thao tác, bỏ phần giải thích dư

Nguồn đối chiếu: Gallery renderer, bộ chữ và CSS tại PR816
`bf95e4017717622d694cbef02fde07799a823a8a`; chức năng gốc theo
`docs/migration/FREE_PROMPT_GALLERY_CONTRACT.md`, không suy chức năng
xử lý nội dung từ các câu giải thích giao diện.

| BASE | Ứng viên GPC/GPR | Giữ nguyên |
|---|---|---|
| Chữ cố định lẫn thuật ngữ triển khai | 17 khóa/51 giá trị đã rà, 50 đổi/1 giữ | Key, route, quyền, dữ liệu khách |
| Câu cố định từ Web ghi đè chữ dịch | Chỉ ánh xạ hai chuỗi nguyên văn đã xác định | Chuỗi lạ hoặc gần giống không bị dịch |
| Thẻ lặp hướng dẫn, khung chưa chọn, ô tắt cuối trang | Bỏ đúng các node dư, không tạo ô thay thế | Mọi nút, form, ID, href và điều kiện hoạt động |
| Mức ưu tiên lưu hiện enum | Dùng nhãn Kho ghi nhớ có sẵn | Enum, chuẩn hóa và guard receipt |
| Chữ sáng/tối thiếu tương phản, ô nhập điện thoại 15px | 11 rule riêng Gallery, ô lọc 16px | CSS cũ nguyên byte, route khác và motion |
| Chưa có danh mục vẫn hiện hai ô số 0 | Chỉ hiện số nhóm/ngành khi danh mục hợp lệ và có quyền đọc | Kết quả tìm rỗng vẫn giữ số thật |
| Thiếu số liệu để trống một cột giới thiệu | Không có bảng số liệu thì chỉ dùng một cột | Không thêm node hoặc đổi dữ liệu |
| Danh mục tĩnh còn pha ngôn ngữ | Chuyển sang GPC-CATALOG theo ID/version riêng | Không dịch tùy ý prompt khách |

PR816 đã phát hành, không còn là ứng viên. GPC/GPR hiện chưa phát hành;
source/renderer/browser là các bằng chứng riêng, không chứng minh auth,
provider, đầu ra thật hoặc toàn WebApp hoàn tất.

## 27/11/2026 — trang nhóm công cụ và bốn cặp màu chữ

Nguồn đối chiếu: `renderFeatureFamily`, bảy khóa FEATURE_CATALOG_MESSAGES,
hai stylesheet tại BASE PR815 `363d6ca55081eea4089ebf489cd183b09ba1aa96`.
Danh sách chức năng gốc tiếp tục từ masterR217/registry; không bịa khả năng
xử lý nội dung từ thay đổi câu chữ hoặc kết quả giao diện.

| BASE | Ứng viên FCH/FCR | Giữ nguyên |
|---|---|---|
| Hero và section dưới lặp tên/mô tả | Bỏ đúng kicker và paragraph ở section | Hero,h2,CTA,nav,thẻ,guards |
| Bảy khóa có mô tả kỹ thuật/thuật ngữ lẫn ngôn ngữ |21giá trị rà,20đổi/1giữ |810giá trị entry đã giao |
| Nhóm rỗng giải thích máy chủ/cơ chế | Hai câu hướng dẫn ngắn theo locale | Điều kiện rỗng/not-found/fallback |
| Nhãn nhóm được dùng ở nhiều consumer | Chữ mới áp hero/nav/explorer/full-catalog có chủ đích | Key/route/order/state/quyền/customertext |
| Link sáng focus và eyebrow quá nhạt;marker tối và hướng dẫn rỗng thiếu tương phản | Bốn foregroundrule scoped family/default-route | CSS trước đó nguyên byte;nền/outline/font/layout/motion |
| Root `/features` có presentation riêng | Không match bốn selector mới trong4cảnh đối chứng | Root light/dark renderer và chức năng |
| Comparator lịch sử khóa mốc trước | Finite FCH21record +FCR4rule trên đầu vào lịch sử | Pin/fixture/assertion cũ;acceptance mới đọc rawphysical |

FBC135 đã giao quaPR815,không còn là ứng viên chờ phát hành. FCH/FCR
chưa qua CI/phát hành; số đo component không xác minh engine/provider/
auth/draft/production hoặc toàn bộ mục tiêu. Motion vẫn bước cuối.

## 27/11/2026 — đồng bộ tên và mô tả sang bộ chữ đầy đủ

Nguồn gốc đối chiếu: full i18n và consumer tại BASE PR814
`fdfe2f753e641c5a5ecc7d6a19305fa3c42b7b30`; canonical root đã giao,
không suy chức năng đang hoạt động từ bản dịch.

| BASE | Ứng viên FBC135 | Ranh giới giữ |
|---|---|---|
| Full bundle chỉ có 96 mục, thiếu 39 mục | Đủ 135 mục/810 giá trị VI/EN/ZH | 135 key/route/order/group giữ |
| 286 mô tả đang khác bản root đã duyệt | Đồng bộ đúng canonical đã khóa | 288 title cũ + hai mô tả giữ |
| Thẻ dùng entry-copy hoặc page fallback hiện có | Khóa mới nhận entry-copy đã duyệt | Renderer/escape/route guard không sửa |
| `/documents` dùng entry-key làm mô tả trang | Mô tả Tài liệu cũng đổi theo ba locale | Ngoại lệ chữ cố định có chủ đích, không đổi chức năng |
| `workspace_menu` có nhánh page-copy riêng | Giữ nguyên nhánh và chữ trang này | Không ép mọi thẻ vào cùng nhánh |
| NLR/dynamic-card tests kiểm mốc lịch sử | Dùng finite inverse đã khóa | Không sửa fixture, 151 pin hoặc kỳ vọng cũ; FBC đọc raw current |

Đúng 289 record dữ liệu = ba block thêm + 286 dòng mô tả thay thế.
Tổng 520 giá trị thay đổi và 290 giữ nguyên. 810 giá trị được ba worker
trả đúng canonical trong một lượt R1; không dịch lại hoặc sửa logic ứng dụng.
Tài liệu từng nói giữ tuyệt đối destination-pagecopy thiếu ngoại lệ Tài liệu;
đã sửa phạm vi và thêm kiểm actual consumer, không chấm thành lỗi worker.

CI đầu phát hiện raw historical Composer pin chưa đi qua finiteFBCinverse.
Expected hash trước đồng bộ giữ nguyên; chỉ chiếu đầu vào phép so về mốc
lịch sử, acceptance FBC vẫn rawcurrent. RED1→19relatedPASS; không đổi
bản dịch, khả năng công cụ hoặc pin/fixture để làm xanh.

Python historical chain cũng dùng finite FBCleaf từ cùng fixture289records;
không thêm vào runtime. Các expected sources/fixtures cũ giữ nguyên và
unknown bytes ngoài record không bị xóa.164ca liên quan đạt bằng receipt
hợp nhất sau một lỗi vị trí sentinel của root,không thay app để né kiểm.

## 26/11/2026 — giản lược mô tả, không đổi khả năng của công cụ

Nguồn đối chiếu là bộ chữ nhẹ135mục/renderer/registry trênBASE
`de870867a27edb02a0d944b3539c0623f1cde3eb`,đã phát hành quaPR813.
Các câu diễn giải kỹ thuật không phải bằng chứng chức năng đang chạy.

| Trước CD108 | Ứng viên hiện tại | Bảo vệ |
|---|---|---|
| 108mục cũ có nhiều diễn giải cách triển khai | 324mô tả đã rà;322đổi/2giữ | 405title/135key/route/thứtự giữ |
| 27mụcVideo vừa bổ sung quaPR813 | Giữ nguyên81entry theo3locale | Không làm lại hoặc thay nghĩa |
| Công cụ lập kế hoạch/chỉ xem/có điều kiện giao kết quả | Câu ngắn theo việc khách làm được | Không tự hứa tạo/tải/khả dụng |
| Root dùng bộ chữ nhẹ,nhóm vàworkspace dùng bundlekhác | Chỉ root `/features` được sửa ở đây | Full-bundle/family vẫn là gap riêng |
| CVN từng là newest raw acceptance | Giữ fixture/kỳ vọng CVN qua finite CD108 inverse | CD108 mới kiểm nguồn vật lý thô |

Bản ghi322old/new vàfixture đóng trước appedit,afterhash6ca65ab5…c74b1a6.
Chỉ thêmPNG là tên định dạng vàoallowlistZH;không nới purity/regex
hoặc sửa151pins/fixtures cũ. Tài liệu gốc không được dùng để suy ra
khả năng provider,giá,vốn dư hoặc số lượng dữ liệu khách chưa đo.

## 26/11/2026 — root danh mục video, không thêm khả năng xử lý

BASE `ccf824a1482ef3ae7fd2d4187932902e36ddbc14` là PR812 đã giao.
Nguồn gốc đối chiếu:135customerentries trong`copyfast_registry.py`,
nhánh `/features` của`copyfast_pages.py`,renderer nhẹ`portal-features.js`
vàbộ chữ108mục có sẵn. Không suy diễn khả năng từ tên công cụ.

| Chức năng/chữ gốc | Ứng viên CVN | Ranh giới giữ |
|---|---|---|
| 135thẻ=108nonVideo+27Video | Vẫn đúng135thẻ | Key/route/order/group/state/quyền |
| 27Video thiếu bản dịch,giữ tênAnh/mô tảViệt nguồn | Đủ27×3locale×2trường=162giá trị | 108mục cũ nguyên vẹn |
| Renderer giữ chữ nguồn nếu thiếu bản dịch | Không đổi renderer/fallback | Khóa mới chưa biết vẫn giữ nội dung nguồn |
| Tìm bằng tên/mô tả gốc/key/route | Thêm chữ hiển thịnative,từ gốc vẫn tìm được | Không đổi bộ lọc hoặc API |
| Công cụ kế hoạch/tham khảo/xem tệp | Chỉ đổi cách diễn đạt ngắn,đúng nghĩa | Không hứa tạo video/phân tích nội dung/tải kết quả |

Nineworkerrecords có before/afterhash vàfixture đóng trước sửa.
Chỉ thêm dữ liệu vào một tệp ứng dụng; không đổi backend,auth,engine,
tiền hoặc dữ liệu. Kiểm kê test từexact108sangexact135 giữ kiểm tra
108/27,purity/duplicate;chỉ thêmhai định dạng MP4/WEBM cho nhãnZH.
Đây không là chứng nhận toànbộVideoUI/đầu ra provider đã hoạt động.

## 22/11/2026 — đối chiếu chi tiết thiết kế ảnh

BASE `f6aee803a72a80bf70cd0a4ce786858f94f9d7cc` đã có bảng thiết kế,
phương án, trạng thái và liên kết công cụ ảnh. Ứng viên chỉ thay 21 câu
cố định theo VI/EN/ZH và một quy tắc màu sáng cho trợ giúp của hai form.
Không thêm chức năng hay thay điều kiện, giá trị, quyền, dữ liệu khách.

## 22/11/2026 — đối chiếu trình bày bảng thiết kế ảnh

Nguồn gốc đối chiếu là bộ chữ, hai renderer tạo/chi tiết và CSS tại
BASE `07a89b79c442981ecb7433b607c981740c95c774`.

| Chữ/hành vi gốc | Ứng viên | Ranh giới giữ |
|---|---|---|
| 19 câu có giải thích nội bộ | Câu hướng dẫn trực tiếp VI/EN/ZH | Key, thứ tự và nội dung khách |
| Khung giải thích ở tạo và chi tiết | Bỏ đúng hai lời gọi, không ô trống | Helper, form, nút, quyền |
| Biểu mẫu tạo chia hai cột với khung giải thích | Một cột dùng đủ chiều ngang | Màn chi tiết và lịch sử giữ bố cục |
| Số đếm màn chi tiết sáng tương phản 1,0182:1 | Màu chữ chính, đo 11,2544:1 | Dữ liệu, hình học, màn tối và Trung tâm ảnh |

Không thay chức năng lưu mô tả, tham khảo, lịch sử hay quy trình rà soát;
không thêm xử lý/tạo ảnh, gọi nhà cung cấp hoặc thay backend.
Đối chiếu toàn nguồn yêu cầu BASE cộng đúng 23 record từ bốn worker;
các kiểm tra lịch sử chỉ đảo đúng các record đó tại đầu vào của test.

## 22/11/2026 — đối chiếu lựa chọn ảnh

BASE `f4c5b6a9821cf957ce107778fd9abd884075fd50` có sẵn tám tỷ lệ và
ba định dạng. Tỷ lệ trước sửa lẫn chữ Việt/Anh ở mọi locale; định dạng
kèm hậu tố kỹ thuật. Ứng viên chỉ đổi nhãn theo ngôn ngữ và làm gọn
chữ định dạng. Không thêm giá trị hoặc thay kiểm tra dữ liệu.

## 22/11/2026 — đối chiếu biểu mẫu thiết kế ảnh

Nguồn gốc tại BASE `05b7ba761bd35cf4da498443db9046ed59429d90` đã có
mười trường và các thao tác tạo/chỉnh sửa. Nhãn trước sửa dùng chữ cứng
Việt/Anh lẫn lộn; ứng viên chỉ dịch nhãn và gợi ý qua bộ chữ hiện có.
Không thêm khả năng tạo ảnh hoặc đổi giá trị, giới hạn, quyền và dữ liệu.

## 22/11/2026 — đối chiếu cảnh báo trường bắt buộc

Nguồn đối chiếu là bộ xử lý biểu mẫu chung và bộ chữ giao diện ở
BASE `a09c7cc94a82537f77ab4e016d3dfa9ae7f23fcc`. Chức năng cũ đã có
kiểm tra và chọn trường chưa hợp lệ nhưng dùng một câu tiếng Việt.
Ứng viên chỉ bản địa hóa câu của ứng dụng; không thay chức năng, dữ
liệu, điều kiện kiểm tra hay ngoại lệ. Thông báo do trình duyệt tự
tạo và tính đúng ngôn ngữ toàn trang chưa được chứng nhận.

## 22/11/2026 — lỗi rà soát âm thanh theo trạng thái hiện tại

Ứng viên giữ hợp đồng bộ sưu tập âm thanh: yêu cầu hiện tại vẫn nhận
thông báo lỗi, dữ liệu và quyền không đổi. Chỉ ngăn cảnh báo của yêu
cầu đã cũ và dịch đúng ba câu cố định tại giao diện; không thay đổi
backend hoặc coi phản hồi lỗi là thành công. Nguồn chức năng gốc:
`docs/migration/MUSIC_MEDIA_WORKSPACE_CONTRACT.md`. CI và phát hành
vẫn cần xác nhận riêng.

## 22/11/2026 — trình bày kết quả rà soát âm thanh

Ứng viên chỉ tách dòng nhãn và mô tả trong kết quả rà soát; giữ bốn
mục, cảnh báo, dữ liệu, nút và quyền của hợp đồng âm thanh hiện có.
Sáu bố cục cục bộ đã được kiểm; CI và triển khai cần chứng cứ riêng.

## 21/11/2026 — tên đường dẫn và số lượng trong rà soát âm thanh

Ứng viên dựa trên PR787 chỉ đổi chữ breadcrumb của chi tiết âm thanh
và số ít/nhiều tiếng Anh của số tệp tham khảo. Tên dữ liệu khách,
receipt, revision, API và thao tác rà soát giữ như hợp đồng âm thanh
được ghi trong `docs/migration/MUSIC_MEDIA_WORKSPACE_CONTRACT.md`.
Node và Python historical được kiểm lại; bản ứng viên chưa được coi
là đã triển khai cho đến khi có CI và runtime riêng.

## 21/11/2026 — rà soát âm thanh: chữ dễ hiểu, hợp đồng chức năng giữ

Nguồn gốc: `docs/migration/MUSIC_MEDIA_WORKSPACE_CONTRACT.md`;
đối chiếu mới theo spec ARF AC01–07 và Root contract bất biến.

| Chức năng gốc/hành vi | Hiện tại trong ứng viên ARF |
|---|---|
| Music/SFX organisation | Giữ tổ chức/tệp/form/control; chỉ thay chữ bước rà soát |
| Music/SFX prompt direction | Giữ gợi ý bằng thông tin; không tự tạo audio/approval/delivery |
| Upload/select personal audio; Play/download state | Không thêm thao tác hoặc gọi blob/provider để kiểm chữ |
| Metadata revisions are immutable and bounded to 100 per collection. | Giữ backend, expected revision, API/DTO và guard |
| `ok:false` là lỗi | Giữ `api()`/outer catch; chỉ dịch đúng stock của action review |
| Raw customer/unknown server text | Không dịch tùy ý hoặc viết lại receipt |

Literal kỹ thuật trong tài liệu/kiểm tra cũ không phải chữ bắt buộc
hiện cho khách. MFF giữ server message vẫn đúng trong phạm vi MFF;
ARF chỉ bổ sung ngoại lệ hữu hạn năm stock/generic message, không
thành bộ dịch server toàn cục. Ba tệp/11 record/31 dòng/93 giá trị;
151 nguồn, 148 tệp bảo vệ, 21 hàm chung. Worker lỗi 0/takeover false.
Node 5.002 unique PASS/158 tệp, Python historical 95 PASS; không
nhận full pytest, signed production UI hoặc audio output đã đạt.
Native R3 có six-view/6reviewPOST/12newPNG/full-decode/owned0,
không ghi dữ liệu sản phẩm. Tester/CI/deploy còn receipt riêng.
Visualqueue breadcrumb VI/ZH, label/note và EN singular mở ngay
sau ARF; rồi ba shared-backend message, generic validity và motion cuối.

## 21/11/2026 — lời nhắc âm thanh: chỉ đổi cách trình bày

Nguồn gốc vẫn là `docs/migration/MUSIC_MEDIA_WORKSPACE_CONTRACT.md`,
mục Parity map và Lifecycle/API, cùng dispatcher ở BASE
`6f04b8449d7354ca44397c199ccdda77107f577e` đã giao qua PR785.

| Chức năng gốc nguyên văn | Hiện trạng ứng viên | Bằng chứng và phần giữ nguyên |
|---|---|---|
| Music/SFX organisation | 35 lời nhắc nhập sai theo VI/EN/ZH ở đúng hành động âm thanh | Mười hàm validation/classifier/read giữ nguyên byte; giới hạn, chuẩn hóa và dữ liệu không đổi |
| Upload/select personal audio | Tám lời nhắc lưu/chuyển bước dùng đúng ngôn ngữ | Yêu cầu API, DTO, thứ tự tải lại và điều hướng được kiểm qua dispatcher thật |
| Music/SFX prompt direction | Vẫn chỉ tạo gợi ý văn bản | Lời nhắc không tuyên bố có âm thanh hoặc đầu ra provider |
| Play/download state | Giữ liên kết tải và công cụ đã có | Không thêm trình phát, tải lên, công việc hoặc gọi dịch vụ |
| Metadata revisions are immutable and bounded to 100 per collection. | Quy tắc không đổi | Producer/backend/149 nguồn ngoài hai tệp giao diện giữ BASE |

Những câu kỹ thuật trong tài liệu gốc hoặc câu VI cũ trong comparator
không còn là lời bắt buộc phải hiện trên giao diện. Comparator lịch
sử chỉ dùng reader hữu hạn cho đúng vùng đã đổi chữ; fixture, golden
và các kiểm tra âm giữ nguyên. Nguồn hiện tại được kiểm dựng tiến từ
BASE với đúng 11 thay đổi, không lấy reader lịch sử làm bằng chứng.

Lỗi có thuộc tính phản hồi máy chủ hoặc trạng thái, kể cả thuộc tính
kế thừa/rỗng, không bị mapper dịch. Các hành động khác không đọc thêm
getter của lỗi. Không xóa chức năng, nới quyền hoặc đổi dữ liệu để
làm chữ gọn hơn. Phần locale và motion toàn app vẫn mở.

## 21/11/2026 — chi tiết âm thanh: trình bày lại, không đổi chức năng

Nguồn gốc giữ nguyên:
`docs/migration/MUSIC_MEDIA_WORKSPACE_CONTRACT.md`, mục Parity map
và Lifecycle/API. Mốc đã giao PR784/runtime051b9366. Ứng viên hiện
tại được đối chiếu với đúng nguồn BASE này, không suy từ tên nhánh.

| Chức năng gốc nguyên văn | Hiện trạng của đơn vị giao diện | Bằng chứng/ranh giới |
|---|---|---|
| Music/SFX prompt direction | Vẫn tạo ba gợi ý văn bản; tên và hướng dẫn dễ hiểu hơn | Ba receipt flags và ba kết quả được kiểm trong renderer thật; không hứa tạo âm thanh |
| Upload/select personal audio | Vẫn chọn tệp đã có và thêm vào bộ sưu tập | Namespace chỉ đổi ID/for/help, không đổi field name/UUID/options/payload |
| Play/download state | Giữ liên kết tải riêng đã có | Không thêm player, tải lên hoặc tạo đầu ra; không gọi link tải trong QA |
| Music/SFX organisation | Giữ vai trò, thẻ, yêu cầu, dự án, quyền và lịch sử | So hợp đồng controls trước/sau, dữ liệu khách được giữ và escape |
| Metadata revisions are immutable and bounded to 100 per collection. | Quy tắc không đổi; lời giải thích viết ngắn | Backend/integration và 148 nguồn bảo vệ giữ nguyên |
| Audio references do not roll back with metadata versions. | Giữ ý nghĩa trong câu khôi phục ngắn gọn | Chỉ thay copy, không thay revision hoặc hành vi khôi phục |

Điểm tài liệu cũ không còn dùng làm kỳ vọng giao diện: các tên
“metadata”, “Asset Vault”, “local brief directions” hoặc các hộp mô
tả cơ chế nội bộ không còn là chữ bắt buộc phải hiện cho khách.
Chúng vẫn có thể là tên kỹ thuật trong tài liệu hợp đồng. Không xóa
cơ chế hoặc mở quyền vì đã bỏ câu giải thích khỏi giao diện.

53record/ba tệp ứng dụng,47 hàng locale gồm45 override và hai khóa
mới,151 source pins/148 bảo vệ; các fixture và golden cũ giữ nguyên.
Reader hữu hạn chỉ phục vụ kiểm tra lịch sử; kiểm tra nguồn mới dựng
tiến từ BASE, không dùng reader lịch sử để che sai khác.
Thao tác ghi/validation còn trong hàng đợi riêng; không suy toàn bộ
locale, accessibility, motion hoặc signed production UI đã đạt.

## 21/11/2026 — phản hồi đọc tệp âm thanh, không đổi chức năng gốc

Nguồn gốc:docs/migration/MUSIC_MEDIA_WORKSPACE_CONTRACT.md và audio
reader/hai consumer ở BASEc8b14ade. PR783 đã giao runtimeBASE,
CI44800229661/deploy44804290178 và hai receipt đọc lại đúng.

| BASE đã đo | Ứng viên | Bằng chứng/ranh giới |
|---|---|---|
| Audio reader trả cùngshape cho readyempty/currentfailed | Catch thêm failed:true | Success/stale/merge/filters/API và mọi phần khác giữ |
| Hai action luôn success sauawait | Chỉ success đúng lượt đã tải được; lỗi cảnh báo, cũ im lặng | Physical147ca7PASS140RED→147GREEN |
| Collectionreadstate không thuộc audioresult | Dùng kết quả từ reader và counter hiện có | Không thêm globalstate hoặc mượn ready/failed của collection |
| Sáu câu cố định lẫn thuật ngữ nội bộ/VI | Sáu key18literalVI/EN/ZH | Dữ liệu khách và rawservermessage không bị dịch tự động |
| Filter/page dùng strictcapabilities | Giữ đúng biểu thức | Giá trị truthy khác true không mở quyền |

Forward151pins/149protected và historical106uniquePASS;Python15PASS/
3sameBASEFAIL,review0blocker. Hồi quy4283NodePASS;native6view/48PNG
hashCRCdecode/source/core/schema/auth/egress/owned0 đạt;release còn kiểm, không
thêm engine/player/download hoặc suy whole-app locale/AX/motion đạt.

## 21/11/2026 — phản hồi sau đọc bộ sưu tập âm thanh

Nguồn gốc vẫn là `docs/migration/MUSIC_MEDIA_WORKSPACE_CONTRACT.md`,
mục Lifecycle/API, và dispatcher/readers thực tại BASEfb1bbcf1. Chức
năng quản lý yêu cầu/liên kết tệp giữ nguyên; không thêm engine/player.
PR782 đã giao qua CI44783966598/deploy44787944401/runtimeBASE.

| BASE đã đo | Ứng viên hiện tại | Bằng chứng/ranh giới |
|---|---|---|
| Action luôn báo success sau await dù reader thất bại hoặc cũ | Chỉ lượt hiện tại ready được báo success; lỗi cảnh báo, cũ im lặng | 187ca BASE2PASS185RED; thêm5counterRED; GREEN192PASS |
| List/detail cùng ghi read-state | Giữ counter chính và snapshot counter còn lại | Không sửa reader, counter lifecycle, return hoặc API |
| Câu VI lẫn tên triển khai nội bộ | Tám key mới,24giá trị VI/EN/ZH | Không dịch dữ liệu khách hoặc raw server message ngoài scope |
| Page có capability strict true | Giữ biểu thức nguyên vẹn, chỉ dịch cảnh báo | Các giá trị false/null/số/chuỗi/object không mở quyền |
| Detail action không có control hiển thị | Giữ nguyên, không thêm nút | Native detail-toast NOT_REACHABLE; physical dispatcher có test |

Hồi quy3662NodePASS,Python15PASS3sameBASEFAIL;native6view48PNG đầy đủ,
source/core/schema/auth/egress/owned0 giữ. Release chưa chốt, không nhận
whole-app locale/AX/motion hoặc âm thanh đầu ra đã hoàn tất.

## 20/11/2026 — bộ sưu tập âm thanh: giữ chức năng, sửa chữ khách nhìn

Nguồn gốc: `docs/migration/MUSIC_MEDIA_WORKSPACE_CONTRACT.md` và năm
renderer/helper hiện có tại BASE4080b879. Đây vẫn là nơi quản lý yêu cầu
và liên kết tệp âm thanh đã lưu; không thêm engine, trình phát hay đầu ra.

| Hiện trạng nguồn BASE | Ứng viên | Ranh giới giữ |
|---|---|---|
| Default `general` và ghi chú quyền VI cố định | Hai fallback VI/EN/ZH tại bốn biểu thức | Mọi truthy customer value và String/escaping giữ |
| Bộ phân trang media dùng câu VI | Nhánh chữ chỉ đúng tuple bộ sưu tập | Signature/offset/route/action và media-audio-page giữ |
| Policy-aside/wrapper và execution-summary lộ chi tiết nội bộ | Bỏ đúng lời gọi/wrapper/span | Policy function/guard/event/version/date không đổi |
| Hai link cần dùng nằm ở aside | Chuyển vào footer tạo mới | Kho tệp/Dự án và quyền không mất |
| Câu hướng dẫn/nhãn hoạt động mang thuật ngữ triển khai | 31 key hiện có viết lại, bảy key mới | Dữ liệu khách/server không bị dịch tự động |
| Comparator cũ kiểm nguồn của đợt trước | Inverse hữu hạn sáu vùng đã khóa | Assertion/golden/raw hash/negative giữ; current151 độc lập |

96 ca vật lý và96 portable đạt; 94 ca chuỗi nguồn đạt, Python121PASS/bốn
lỗi cùng BASE. Node1800executablePASS;native12trục/36PNG/214inputs giữ,
source/core/schema/auth/egress/owned0. Native dùng ba cohortQA cùng
151appsource,R6overallfalsevẫn giữ;release cònchốt riêng. PR781 đã giao runtimeBASE,
CI44741117456/deploy44744844095/receipts đọc lại đúng. Không diễn giải
các snapshot ứng viên cũ thành hiện trạng hoặc suy toàn bộ locale đã xong.

## 20/11/2026 — nguồn lựa chọn dự án tại Kho tệp

Nguồn gốc: `docs/migration/ASSET_VAULT_CONTRACT.md` và reader Web riêng tài
khoản `hydrateProjects`. Hợp đồng gắn tệp với dự án vẫn dùng; lỗi là
dispatch không tải nguồn dự án khi mở trực tiếp Kho tệp, không phải thiếu
chức năng backend hoặc cần lấy dữ liệu Bot.

| Hiện trạng BASE4cf85908 | Ứng viên | Bằng chứng/giới hạn |
|---|---|---|
| Signed bootstrap reset projects[] nhưng không gọi reader tại Kho tệp | Một nhánh exact route + flag bật trong account guard | RED37đạt/1lỗi → 38đạt; native đại diện GET thật/chọn được |
| Reader dùng query mới ngoài Project Board | Giữ `/projects?limit=50&offset=0` | Không mang filter/offset cũ của Project Board |
| UUID/schema/counter/session/path và lỗi đọc | Giữ nguyên | Ca invalid/empty/stale/logout và 151 source pins |
| Upload, project_id, ownership và revision | Giữ nguyên | Không submit/upload/blob trong QA; không nhận output |
| Route cũ và dữ liệu tên khách | Giữ nguyên | 18 exact routes, literal đặc biệt và nhóm hồi quy liên quan |

Nhánh nhãn/tiêu đề trước đó đã giao qua PR780/CI44709731113/
deploy44735563146/runtimeBASE. Ứng viên project-options chưa triển khai.
Lịch sử ứng viên bên dưới được kết quả phát hành từng đợt thay thế.

## 20/11/2026 — nhãn bộ chọn: không thay chức năng gốc

Tìm trong docs/migration bằng ba neo renderFields,Giọngchưađặttên và
sharedSelect:không có hợp đồng gốc riêng cho nhãn dùng chung. Do đó đối
chiếu trực tiếp sourceBASE46423a6d,không tự bịa danh sách chức năng mới.

| Hành vi nguồn BASE | Ứng viên nhãn | Bằng chứng và giới hạn |
|---|---|---|
| Project/note thiếu tên dùng chuỗi cố định | Nhãn chưa đặt tên theo VI/EN/ZH | Fullphysical62PASS; không đổi tên thật |
| Giọng thiếu tên vàsuffixdefault viếtVI | Bốn nhãn dịch;default chỉstricttrue | SameVMlocalechange/hostiletext;khônggọiBridge |
| UUID/state/tts_ready/selection/required/disabled/ARIA | Giữ nguyên | Inputfrozen/BASEHTML ngoàioptiontext/nameddata |
| PDF/image bịnormalizer loại nếu thiếu tên | Giữ nguyên,không sửa deadfallback | Genuinepublicprojectionnegative soBASE |
| Tiêu đề ZH `/reminders` nhận tên ứng dụng chung từ BASE | Một nhánh riêng dùng khóa dịch Nhắc việc đã có | 3 PASS / 4 RED → 7 PASS; native ba cấu hình bổ sung đạt |
| /asset-vault cóselect dự án nhưng thiếuGETproject ởbootstrap | FindingBASEgiữmở,taskchức năngkếtiếp | Source14711/15572;khôngnhậnđãsửa từlocale |

Kết quả local cuối: 62 ca nhãn / bảy ca tiêu đề / 32 ca nguồn đạt;
5305 ca Node thực thi đạt và một bootstrap Bot trùng BASE; Python hợp
126 đạt / 17 lỗi trùng BASE. Native chín cấu hình trước + ba cấu hình
sau sửa tiêu đề, 24 PNG tổng hai đợt; không phải một lượt cùng binding.
Chưa suy ra đã phát hành, giọng canonical, đầu ra hoặc toàn goal hoàn tất.

PR779 phản hồi Kho tệp đã giao:CI44695158108/deploy44697995955/runtime
46423a6d/receiptsIssue7019553829PR7033751040. Mọi trạng thái V07 ứng viên
phía dưới làsnapshotlịchsử. Đợtnhãn hiện tại chưa triểnkhai.

## 20/11/2026 — Kho tệp: hợp đồng gốc và phản hồi hiện tại

Nguồn gốc tiếp tục là `docs/migration/ASSET_VAULT_CONTRACT.md`: danh sách/
thông tin riêng tài khoản, upload và archive/restore có revision/idempotency.
Ví dụ Railway trong tài liệu gốc vẫn chỉ là lịch sử, không đổi ENV từ đó.

| Hợp đồng/hiện trạng trước V07 | Ứng viên V07 | Bằng chứng và giới hạn |
|---|---|---|
| Đọc list có thể trả rỗng hợp lệ, lỗi/stale cũng trả mảng rỗng | Dùng counter/session/path/readState hiện có; không đổi DTO |253read cases trong429GREEN;không suy signedLIVE |
| Refresh có thông tin tệp đang mở | Chỉ báo chung khi hai lượt đọc và lựa chọn còn hiện tại |Empty/failed/race/selection fixtures thực thi dispatcher thật |
| Chữ thao tác lẫn thuật ngữ hoặc VI ở locale khác |35key/105giá trị, helper scoped |52readcopy+124write cases trong429GREEN |
| Success envelope chứa câu cố định hoặc message khác |Chỉ ba finite literals/falsy được dịch; giá trị khác giữ |Fake transport trong bộ nhớ; không ghi production |
| Auth/API/quyền/key/revision/busy/finally |Giữ nguyên điều kiện và transport |149protected/151pins;native/regression/release riêng |

Không thêm chức năng, không bỏ control hoặc giả đầu ra. Kho tệp PR778 đã
giao; V07 đang nghiệm thu. [Phiên Tester V07](../KIEM-THU/PHIEN-VAULT-ACTION-FEEDBACK-20261120.md).

## 19/11/2026 — Kho tệp: giữ chức năng, bỏ lời triển khai

Nguồn gốc: `docs/migration/ASSET_VAULT_CONTRACT.md`, năm hàm Vault và
renderer chính. Ví dụ volume Railway trong hợp đồng cũ không phải chân lý
triển khai hiện tại; chỉ dùng ownership/revision/private-delivery như source
contract, không đổi ENV từ tài liệu cũ. Production vẫn Ubuntu VPS.

| Chức năng gốc | Ứng viên giao diện | Ranh giới giữ |
|---|---|---|
| Lưu tệp và gắn dự án | Ô nhập, hướng dẫn đủVI/EN/ZH | Name/id/required/accept/maxLength/defaults/capability |
| Danh sách, lọc và phân trang | Nhãn/trống/counts/actions rõ | UUID/state/offset/download active-only |
| Xem trạng thái, tham chiếu và khôi phục | Thông tin tệp bằng chữ khách hàng | State/reason/counts/blockers/revision/restore eligibility |
| Intro/aside giải thích triển khai | Bỏ hai khối và wrapper hai cột | Không bỏ form/panel chức năng, /assets còn trongnav |
| Tiêu đề/mô tả shell generic | Hai entry shell và hai nhánh JS đúng route | Không sửa shared metadata hoặc locale/auth |
| Hướng dẫn chọn tệp tối chỉ3.51:1 | Một rule darkcolor đo lại8.84:1 | Không đổi light/font/layout/motion/controls |

Physical27ca và HTML đầu4ca đạt; native/hồi quy/release riêng. Không nhận
toàn bộ interactionfeedback hoặc blob/output thật từ kiểm tra renderer.
Nativeđãđốichiếu48views192PNG BASE/current,source151/code/core/schema/
audit/egressgiữ,unknown996mỗiphase. Release/review vẫn cổng riêng.
[Phiên Tester](../KIEM-THU/PHIEN-VAULT-CUSTOMER-COPY-20261119.md).

## 19/11/2026 — Chữ từ ảnh/PDF, giữ giới hạn xử lý

Nguồn: `docs/migration/IMAGE_OCR_CONTRACT.md`, `PDF_OCR_CONTRACT.md`,
`PDF_OCR_WORD_CONTRACT.md`, ba renderer/field factory và handler gốc.

| Chức năng gốc | Ứng viên giao diện | Ranh giới giữ |
|---|---|---|
| Đọc chữ từ ảnh JPEG/PNG/WebP | Tên/nguồn/ngôn ngữ/hướng dẫn VI/EN/ZH | Không đổi decode/OCR hoặc dữ liệu |
| Đọc chữ PDF tối đa20MB/5trang | Bỏ lời triển khai, giữ hướng dẫn cần dùng | Mã auto/vi/en, API/nguồn/quyền giữ |
| PDF quét sang Word | Nêu rõ chữ-only, không giữ dàn trang | Ba phụ thuộc thực tế không nới |
| Panel giới hạn kỹ thuật và chỉ số phụ | Bỏ ở đúng3trang, không khung trống | Form/history/vault/refresh/download giữ |
| Metadata chưa riêng từng locale | Sáu entry shell/sáu nhánh JS đúng route | Không đổi locale/auth |

Wholephysical28ca và HTMLđầu10ca đạt; native/affected/release chốt riêng.
Không nhận đầu ra OCR cuối từ UI. [Tester](../KIEM-THU/PHIEN-DOCUMENT-OCR-CUSTOMER-COPY-20261119.md).

## 19/11/2026 — Chuyển đổi PDF: giữ chức năng, bỏ lời triển khai

Nguồn gốc: `docs/migration/PDF_TO_IMAGES_CONTRACT.md`,
`PDF_TO_WORD_CONTRACT.md`, hai renderer và hai factory trường nguồn.

| Chức năng gốc | Ứng viên hiện tại | Ranh giới giữ |
|---|---|---|
| PDF một trang ra PNG, nhiều trang ra ZIP | Chữ thao tác đúng VI/EN/ZH | Không đổi tạo, kiểm hoặc giao tệp |
| Trích chữ bôi chọn từ PDF sang DOCX | Hướng dẫn giới hạn rõ bằng ngôn ngữ người dùng | Không OCR, không hứa giữ bố cục/hình/bảng/phông |
| Chọn PDF thuộc tài khoản, lịch sử và tải xuống | Giữ control/action/route/quyền và thẻ lịch sử | Không thay UUID, dữ liệu, API hoặc capability |
| Intro/aside/notice/notes giải thích nội bộ | Bỏ tại đúng hai trang, không ô trống | Factory ghi chú dùng chung và mọi trang khác giữ |
| Tên trang chờ catalog | Thêm đúng hai entry shell và hai nhánh metadata JS | Không đổi cách chọn ngôn ngữ hay đăng nhập |

Physical 16 ca đạt, 7 trang bảo vệ byte-identical ở ba ngôn ngữ; HTML đầu
7 ca đạt. Bằng chứng native/CI/VPS và các giới hạn được chốt riêng trong
[phiên Tester](../KIEM-THU/PHIEN-DOCUMENT-CONVERT-CUSTOMER-COPY-20261119.md).

## 19/11/2026 — Loại phần giải thích không phục vụ thao tác History

Nguồn:renderImageOperationHistory vàrenderNotes trongportal.js.

| Thành phần gốc | Ứng viên đo được | Giữ nguyên |
|---|---|---|
| Hai panel giải thích triển khai | Không gọi notes ởreadyHistory | Factory/config/khóadịchchung/cáctrangkhác |
| Ba cụm metadata ởstate | Bỏ đúng3cụm,khôngkhungtrống | h2/p/icon/quyền/retry/nhánhtrạngthái |
| Danh sách vàphản hồi | 24physicalcađạt,1632+3retestsđạt | Khách/ID/card/phantrang/download/currentness |

Khônggọiảnh/provider/ví,motionhoặcquyềnbổsung. Đây làđợttiếpsau
PR772đãtriểnkhaibb3c5657;nativeFULL6trang24samples0notes0state-meta/
27owned0đãkiểm;CI/deploymớiphảikiểmriêng,empty/guardnativechỉunit.
[Phiên Tester](../KIEM-THU/PHIEN-IMAGE-HISTORY-TECHNICAL-CLEANUP-20261119.md).

## 19/11/2026 — Lịch sử ảnh không cần giải thích triển khai

Nguồn gốc:customerPage("/image/history"),renderImageOperationHistory,
IMAGE_OPERATION_COPY_ROWS và image-history-refresh trong integration.js.

| Chức năng gốc | Ứng viên đã đo | Ranh giới giữ nguyên |
|---|---|---|
| Lịch sử riêng theo tài khoản | Tiêu đề/hướng dẫn/trống đúngVIENZH | Quyền,UUID,phân trang,dữ liệu,tải xuống giữ |
| Khung giải thích ranh giới và hai chỉ số | Giữ một số đếm,ba liên kết công cụ gọn | Không xóa hoặc thay chức năng công cụ |
| Làm mới/thử lại | Nhãn gọn,ba thông báo theo locale | API/tự thử lại/timer6500ms/dedup/role giữ |
| Tài liệu cũ dùng chữ về nguồn nội bộ | Source19edits/4files/147protected,kiểm tra vật lý | Hai khối renderNotes cuối trang vẫn là việc kế tiếp |

1904Node+3ca reader sửa đúng biên đạt;12Python shell đạt.
NativeEMPTY6trang vàFULLR6sáutrang/24states/54GET/27owned0 đã đo;
FULLhai toastdịch/tự tắt có12pixelảnhRootđãxem. CI/merge/deploy/runtime
là các cổng riêng;filenameellipsis giữ vàkhôngnhậnfulltextpaint.
Không chứng minh ảnh cuối đã được tạo hoặc toànứngdụng/motion hoàn tất.
[Phiên kiểm tra](../KIEM-THU/PHIEN-IMAGE-HISTORY-CUSTOMER-CLEANUP-20261119.md).

## 11/11/2026 — Nội dung đang nhập và lưu kế hoạch không trùng

|Chức năng đang có|Hành vi ứng viên đã kiểm tra|Ranh giới giữ nguyên|
|---|---|---|
|Lập kế hoạch từ tham chiếu|Giữ nội dung cũ khi tạo lại lỗi, chặn phản hồi không còn hiện hành|Không đổi lựa chọn hợp lệ, bộ kiểm tra dữ liệu hoặc đầu ra|
|Lưu kế hoạch|Không gửi thêm khi đang chờ; mất phản hồi chỉ thử lại đúng lần lưu|Không tự gửi lại, không coi phản hồi lỗi là chưa lưu ở máy chủ|
|Lập kế hoạch từ ảnh|Luồng sửa, chờ lưu và khôi phục được kiểm tra riêng|Giữ nguyên mã đã đạt và dữ liệu gốc|

Việc xem kết quả bằng giao diện khác với thực thi tạo media. Phiên kiểm tra này
không mở quyền mới, không tạo đầu ra có phí và không thay dữ liệu production.

## 11/11/2026 — Không hiện mã mode hoặc giải thích triển khai

Nguồn:designDashboard26/07 vàAccount03/08. Quy tắc giữ dữ liệu vẫn nguyên;
chỉ3enum mode công khai có nhãn ở3ô giao diện,không đổi điều kiện hoặc giátrị.

|Chức năng gốc|Đổi có phạm vi|Bằng chứng|
|---|---|---|
|Account metadata nguồnchuẩn|3nhãn mode theo locale,unknownescaped/rawkeep|36renderer mode cases+72parity|
|Thư viện dự án/bản nháp|Bỏ2lời lặp,loading/error/empty có hướng dẫn gọn|13keys×3locale,realreadstatechecks|
|Dashboard dữ liệu tài khoản|Chữ dễ hiểu,không ẩn lỗi hoặc tạo trạng thái|612Node/51Pythonpass;nativeR2separateevidence|

Không đụng nguồn dữ liệu,quyền,provider/ví/PayOS,flow hoặc motion.

## 11/11/2026 — Hồ sơ và Tổng quan không cần thuật ngữ triển khai

Nguồn gốc: specs2026-08-03-account-center-locale-clarity-design và
2026-07-26-dashboard-reviewed-locales-design,renderAccount/Account catalogue,
renderDashboard. Catalogue đủ khóa không đồng nghĩa câu chữ phù hợp khách dùng.

|Chức năng gốc|Candidate đã đo|Ranh giới giữ|
|---|---|---|
|Hồ sơ4trường,phương thức đăng nhập,xác nhận liên kết|33khóa×3locale viết dễ hiểu;36renderer tests|Tên/giá trị/quyền/correctaccount/noemailmerge/codesecrecy giữ|
|Bot5lệnh và hướng dẫn dữ liệu|Lệnh và handoff tự gửi,disabled/href đúng|Không gửi Bot,không xóa/sửa tài chính/dữ liệu|
|Tổng quan trạng thái riêng|Bỏ assurance nội bộ lặp,hướng dẫn hữu ích|loading/failed/ready/guarded/retry giữ|
|Locale và thao tác khách|48BASE/branchparity,24nativeviews/12DOMedits|Ngoài33keys,các control/data và18otherrouteHTML giữ|

145Node/138Python đều đạt;3motion source assertions thất bại giống BASE,để đúng
đợt motion sau. Không xóa catalogue lịch sử,chức năng hay nội dung khách để làm
test xanh. [Báo cáo](../docs/reports/account-dashboard-plain-language-20261111.md).

## 09/11/2026 — Focus continuation

R217-10 cấm stale callback; restoreFocus cũ vẫn chạy sau mọi replace promise.
RED 5/8 chứng minh ID trùng có thể lấy focus khỏi form mới; candidate guard
completion theo mount hiện hành, helper giữ nguyên. 8 Node/20 native kiểm
old/current/error/fallback và Tab/selection/values/scroll. Navigation opt-in
vẫn lỗi ở cả PR700 và candidate, không suy focus PASS thành toàn motion/LIVE.
[Bằng chứng](../docs/reports/motion-focus-20261109.md).

## 09/11/2026 — Đối chiếu hợp đồng motion và hành vi thực tế

Nguồn gốc: docs/superpowers/specs/2026-10-16-r217-10-motion-performance.md.

| Hợp đồng gốc | Sai lệch đã tái hiện | Candidate có bằng chứng |
|---|---|---|
| Không stale callback/hydration replay | Native A ghi đè/enter lên B; rule toàn bài chạy Dashboard7/7/5lần | Ownership riêng main; bỏ rule vô điều kiện, giữ entry riêng |
| Scroll hot path không layout thrash | Landing đọc vị trí sau ghi; workspace đo/ghi xen kẽ | Snapshot trước ghi, giữ ngưỡng/số lần đo và cleanup |
| CLS/LCP/INP hoặc runtime evidence | Source xanh từng bị hiểu nhầm là hết giật | Native replay được đo; startup/device/fieldINP/signedUI vẫn mở |

Không đổi chức năng sản phẩm, provider/engine/backend/auth/ví hoặc dữ liệu; không
xóa keyframes cũ hay khảo sát dependency ngoài phạm vi. [Receipt](../docs/reports/motion-20261109.md).

## 08/11/2026 — Đối chiếu locale, âm nhạc và motion

| Chức năng đang có | Hiện trạng đã đo | Ranh giới giữ nguyên |
|---|---|---|
| Tiêu đề list/new/detail UUID/bảng kế hoạch |39/39 HTMLResponse đúng locale|Không đổi UUID recognizer/quyền|
| Ba công cụ âm nhạc riêng và dữ liệu kết quả |36/36 renderer,30/30 tương tác|Giữ route/action/ID/scalar và nội dung máy chủ|
| Locale và bố cục công cụ |418/418 locale,54/54 Chrome; mobile16px/min45px|Không tạo âm thanh hay quyền mới|
| Dashboard motion |Không gọi entrance trên main ở normal/reduced|Chỉ reveal lớp quyết định; không chặn trạng thái chuẩn|

Tiền tố /media-workspace/ không đủ để phân biệt tool với collection detail; dùng
layout/route đóng. Bài kiểm phải kiểm các nhóm điều hướng đang render, không
giữ một khóa home đã bỏ bằng hằng số không sử dụng. PASS local không phải deploy/LIVE.

Bằng chứng hiện tại và manifest nguồn được giữ tại [receipt phát hành](../docs/reports/locale-release-20261108.md) và [phiên Tester](../KIEM-THU/PHIEN-LOCALE-20261108.md). Không dùng số liệu lịch sử bên dưới thay cho đợt này.

## 07/11/2026 — Đối chiếu xác nhận lưu kế hoạch

Nguồn: `docs/migration/CAMPAIGN_PLANNER_BOUNDARY.md`, projection native
`_campaign_plan_public` và ba handler hiện hữu; BASE3de678d3.

| Trước sửa | Candidate có bằng chứng | Ranh giới |
|---|---|---|
| Sửa/status có thể merge nhầm ID hoặc báo thành công khi thiếu item | Kiểm11field/type/enum/UUID/revision và ID đích trước mọi side effect | Không thay API/DTO, không coi ID client là quyền sở hữu |
| Create chỉ kiểm UUID | Giữ UUID mới bất kỳ từ server, yêu cầu bản ghi đủ và trạng thái draft | Không tự đặt trước ID create |
| Receipt không có kiểm tra outer/item/target status | Các trạng thái phải nhất quán; lỗi không clear/redirect/hydrate | Không hủy/retry/rollback write đã gửi |
| Native UUID canonical có thể khác hoa/thường của request | Hai native uppercase replay trả đúng envelope cũ;5clientcontrols | Không đổi đường dẫn/payload/idempotency |

100ACK+48currentness đạt148/148; fullNode1.818/1.818, native2/2, browser18/18;
reviewC0/I0/M0,19helper/currentnessMap byte-identical. Row cũ sai enum có thể
vẫn được server ghi rồi trả ACK; client chặn metadata sai nhưng không tuyên
bố write chưa xảy ra. Không sửa DB hoặc tạo chính sách backend mới. Không
đóng toàn locale Campaign, provider/output hay signed UI; không audit dependency.

## 07/11/2026 — Đối chiếu quyền sở hữu phản hồi ghi kế hoạch

Nguồn gốc: `docs/migration/CAMPAIGN_PLANNER_BOUNDARY.md` và ba handler ghi
hiện hữu; BASE81374e73bcedbb1541c36a1cd79706dae55c5dc2.

| Trước sửa | Candidate có bằng chứng | Ranh giới giữ nguyên |
|---|---|---|
| Receipt ghi cũ vẫn merge/toast/điều hướng sau đổi context |48ca đầy đủ gồm32RED; sau sửa48/48 | Không hủy hoặc gửi lại mutation, máy chủ vẫn quyết định dữ liệu |
| Mở nút vô điều kiện sau hoàn tất | Chỉ lượt hiện hành mở nhóm nút khi không có peer cùng nhóm chờ | Helper controls, API và scope chống gửi trùng không đổi |
| Board, trang chi tiết và tự rà soát có route thao tác khác nhau | Lưu actual UI path riêng; native và browser gồm `/approvals` | Không đổi route form hoặc DTO |
| Luồng đọc đã có chốt riêng |14helper khóa byte-identical,150Calendar/PublishReview regression đạt | Không thay read fence hoặc nguồn quyền |

Toàn bộ Node1.718/1.718; native2/2; browser12/12. Bản này không dịch lại dữ liệu
khách hoặc thông báo native, không hoàn thành toàn locale Campaign hay kết nối
mạng xã hội/provider. Không khảo sát/xóa dependency hoặc mã chết trong phạm vi này.

## 07/11/2026 — Đối chiếu lưu bằng chứng kiểm tra đăng nhập

Nguồn: `.github/workflows/webapp-quality.yml` và
`scripts/ci/run_authenticated_qa_matrix.py`, BASE `a67ebbcdd8e9369bef2a264dd0e62839e668eb4c`.

| Hiện trạng trước | Candidate CI-OBS-001 | Giới hạn |
|---|---|---|
| Runner ghi JSON/ảnh trước khi báo lỗi, bước upload chỉ chạy khi thành công | Upload có `if: always()`, giữ nguyên tên/đường dẫn và lỗi khi không có tệp | Không thay runner, 456 cấu hình hoặc điều kiện PASS |
| Run main 455/456, không còn JSON/ảnh của ca lỗi | Hợp đồng 5/5 kiểm bước upload và gate cũ; review C0/I0/M0 | Không khôi phục được bằng chứng cũ, không khẳng định đã sửa Dashboard |

Không thay chức năng khách hàng, API/auth/schema, ví/provider hoặc workflow deploy.
Không khảo sát/xóa mã chết hay phụ thuộc trong bản sửa bằng chứng này.

## 07/11/2026 — Đối chiếu phản hồi thao tác Lịch nội dung

Nguồn chức năng: `docs/migration/CAMPAIGN_CALENDAR_WINDOW_CONTRACT.md` — đọc một
tháng riêng, bộ lọc giới hạn và bỏ phản hồi cũ; không có thao tác ghi từ Calendar.

| Hợp đồng / giới hạn bản PR682 | Candidate có bằng chứng | Điều không thay đổi |
|---|---|---|
| Renderer dịch nhưng toast ba action chưa dịch | Tám fixed message map locale; unknown qua helper/catch giữ nội dung | Không dịch mù metadata hoặc API error payload |
| Read helper đã bỏ dữ liệu cũ, outer handler vẫn báo lỗi/mở nút mới | Dùng lại cùng request/session/selection predicate cho feedback/finally; 66 currentness cases | Không thay predicate, read hydrate, query, auth hoặc capability |
| Thành công đọc phải phản ánh cửa sổ thật | Ba GET native DB tạm → full integration → chín action/locale toast, projection giữ nguyên | Không suy ra lịch đăng, reminder, task hay output |
| UI action phải hiện thông báo nhìn thấy | 36/36 normal click/submit và36 GET QA; toast role=status/visible; 108 Node | Không dùng DOM text-only hoặc fake success làm LIVE proof |

Toàn bộ Node 1.670/1.670; native/hợp đồng 9/9. Các hàm API/toast/merge/busy,
selection/key/path/read predicate/hydrate và PublishReview helper giống BASE
từng byte. Chỉ thêm nhánh catch cho đúng ba action. Phần còn lại toàn ứng dụng,
physical PWA, signed production UI và chuyển động vẫn chưa đóng.

## 07/11/2026 — Đối chiếu Lịch nội dung

Nguồn ban đầu: `docs/migration/CAMPAIGN_CALENDAR_WINDOW_CONTRACT.md` — “signed,
read-only monthly view”, khoảng tháng 2000-01..2100-12, tối đa 200 mục và loại bỏ
phản hồi cũ. Các ranh giới này không thay đổi trong đợt giao diện.

| Hợp đồng / hiện trạng cũ | Candidate có bằng chứng | Giới hạn |
|---|---|---|
| Một khoảng tháng riêng của tài khoản, bộ lọc và thứ tự thời gian | API/DTO/owner predicate/giới hạn không đổi; 8/8 Python/native | Không tạo lịch đăng hoặc ý định nhắc việc từ Calendar |
| Tiêu đề HTML/JS và phần lớn câu cố định chưa nhất quán locale | VI/EN/ZH đầy đủ; fallback rỗng đặt tại renderer; 211 khóa nhóm cân bằng | Tên khách và thương hiệu không dịch mù; 8.943 EN cũ giữ nguyên |
| Summary ghép số hai lần, overflow là VI | Câu đếm một lần và overflow theo locale; ba thẻ grid/bốn mục agenda vẫn đủ | Không đổi nguồn total/returned hoặc tự tải thêm dữ liệu |
| Loading/failed/guarded dễ bị diễn đạt như lịch rỗng | Tách title/body theo trạng thái đọc có sẵn, không có số 0 giả | Chỉ đổi chữ; không cấp quyền hoặc thay luồng request |
| Hai khối giải thích tĩnh, một khối nói tới bản ghi chưa có ngày mà API không trả | Bỏ hai container, giữ nguyên hai liên kết và đưa count thật vào bộ lọc | Không mất điều khiển hoặc giấu lỗi/đang tải |
| Input/select điện thoại 15px | Một khối Calendar ≤620px nâng lên 16px; phần CSS còn lại giống BASE | Không đổi style desktop, màu hoặc motion |

39 Node tập trung, 1.562 Node toàn bộ và browser 90/90 cấu hình đạt. Browser không
có lỗi trang/console hoặc request API/ngoại mạng/ghi. Tài liệu gốc không được hiểu
là quyền kết nối mạng xã hội, đăng bài,
provider/job/output, ví/PayOS, lịch quản trị hay ý định nhắc việc ở trang chi tiết.
Không audit/xóa phụ thuộc hoặc mã chết trong đợt này. Signed UI production và
phần còn lại toàn ứng dụng/chuyển động vẫn là các mục chưa hoàn thành.

## 06/11/2026 — Đối chiếu bổ sung: không làm mất nội dung phản hồi

Nguồn: `docs/migration/PUBLISH_REVIEW_PACK_CONTRACT.md`, helper phản hồi hiện hành
và hai thông báo cố định của native Web formatter. Không đổi backend hoặc DTO.

| Hợp đồng / mô tả cũ | Đo được ở bản PR680 | Candidate và bằng chứng |
|---|---|---|
| Thông báo lạ giữ nguyên | Không đúng: fallback thay nội dung; 12 ca RED | Own-property guard trả nội dung ngoài bảng; kiểm cả constructor/toString/__proto__ |
| Chữ cố định theo VI/EN/ZH | Ba câu VI còn review/Web-native; thiếu hai thông báo native | Bảy ánh xạ, 70 khóa mỗi locale; EN cũ không đổi |
| Không báo nội dung chung thay kết quả thực | Native API→renderer cũ chưa kiểm toast | Native API→integration→toast ba locale; giữ receipt và nội dung khách |
| Không gây lỗi luồng cũ | Receipt/currentness đã khóa | 119 Node tập trung, 10 Python/native, 1.523 Node toàn bộ đạt |

Các khẳng định giữ nguyên mọi thông báo lạ trong hai mục lịch sử bên dưới được
đính chính bởi mục này. Không dùng bản sửa chữ để khẳng định đã kết nối mạng xã hội,
đăng bài, tạo tác vụ trả phí hoặc hoàn thành kiểm tra giao diện production.

## 06/11/2026 — đối chiếu Gói rà soát trước khi đăng

| Yêu cầu gốc | Candidate | Evidence / giới hạn |
|---|---|---|
| Receipt text-only giữ ranh giới | Chuẩn hóa lặp giữ execution+12 false flags; sai bị loại | 21 Node receipt + native API |
| Fixed chrome đúng VI/EN/ZH | 68 khóa cân bằng, EN cũ không đổi; feedback cố định map locale | 77 Node + 10 Python/native |
| Response cũ không ghi đè | Fence theo request/session/account/route/capability/CSRF | 41 deferred-response |
| Không tự điền nội dung khách | Hashtag form ban đầu rỗng; backend fallback giữ nguyên | Native form/render |

Đây là gói văn bản để người dùng tự rà soát, không phải lịch đăng, social/OAuth,
provider job, media output, thanh toán hoặc delivery. Signed production UI và motion
vẫn mở; không dùng HTTP200 để kết luận đã đăng bài.

## 06/11/2026 — đối chiếu Gói rà soát trước khi đăng

Nguồn chức năng: `docs/migration/PUBLISH_REVIEW_PACK_CONTRACT.md` và native API hiện có.

| Yêu cầu gốc | Candidate có bằng chứng | Giới hạn |
|---|---|---|
| Receipt text-only giữ đủ ranh giới, không tạo post/job/provider | Chuẩn hóa lặp vẫn giữ `execution` + 12 cờ false; receipt sai bị loại | 21 Node receipt + native API contract; không phải provider/output proof |
| VI/EN/ZH fixed chrome đúng ngôn ngữ | 68 khóa cân bằng; EN cũ không đổi; field/help/result/boundary/scope và feedback cố định đã map | 77 Node + 10 Python/native; dynamic server/customer text không dịch mù |
| Không để response cũ ghi đè phiên mới | Chốt epoch/session/account/route/capability/CSRF riêng cho action | 41 deferred-response cases; không đổi API chung hoặc hủy request |
| Form không tự điền nội dung khách | Hashtag ban đầu rỗng; backend fallback khi request rỗng giữ nguyên hợp đồng | Native form/render test; không đổi DTO/server mặc định |

Gói rà soát là văn bản để người dùng tự kiểm tra, không phải lịch đăng, kết nối
mạng xã hội, output media, job, thanh toán hay delivery. Signed production UI và
full accessibility/motion vẫn là cổng mở; không dùng HTTP 200 hoặc fixture local
để kết luận đã đăng bài thật.

## 06/11/2026 — đối chiếu Chiến lược kênh

Nguồn chức năng ban đầu: `docs/migration/CHANNEL_STRATEGY_CONTRACT.md`.
Các mục gốc “multiple private profiles”, “version changes”, “archive or restore”
và “deterministic direction for human review” vẫn là hợp đồng đang giữ.

| Hiện trạng trước | Candidate có bằng chứng | Giới hạn |
|---|---|---|
| Catalogue có nhưng gợi ý nhập, lựa chọn và hoạt động còn chữ khác ngôn ngữ | 152 khóa VI/EN/ZH; 29/29 Node, không đổi EN cũ, giá trị máy hoặc nội dung khách | Không dịch mù dữ liệu phản hồi và không mở quyền đăng bài |
| HTML ban đầu dùng tên chung, chi tiết không có mapping riêng | Sáu trường hợp parent/detail × ba ngôn ngữ đạt | Không thêm route hoặc đổi auth |
| Chi tiết gọi helper không tồn tại trong phạm vi bundle | Helper cục bộ giữ đúng số nguyên 1–1.000.000; chi tiết/lưu trữ hiển thị được | Backend, chữ ký helper và kiểm tra quyền giữ nguyên |
| Ô nhập điện thoại 15px | Ba form riêng dùng 16px khi ≤620px; 54/54 browser và 90/90 CSS đạt sau sửa font | Không đổi desktop, dữ liệu hoặc motion |
| Detail rơi vào nhóm Công cụ dù parent thuộc Đăng bài | Một prefix bổ sung giữ cả hai trong Đăng bài; kiểm hành vi parent/detail và nhóm khác/admin | Không đổi route, resolver hoặc quyền; native/CSS106/106 |

Tài liệu gốc không được hiểu là bằng chứng kết nối mạng xã hội hay tự đăng.
Các cổng CI và triển khai cuối vẫn phải nghiệm thu trước khi gọi candidate này
là đã triển khai. Không audit hoặc xóa mã chết/phụ thuộc/ảnh
trong đợt sửa chữ; không suy “không còn lỗi toàn app” từ bộ kiểm tra của cụm này.

## 24/10/2026 — SD15: nút Bật/tắt âm thanh gốc không đồng nhất với mức0%

Nguồn gốc: spec `2026-10-18-r218-subdub-bot-parity-uiux.md`, SD15 và
crosswalk đủ21SD. Bản E3 chỉ chứng minh range/number/0%-mute, chưa có nút
Bật/tắt riêng; Tester đã phát hiện và giữ UIgap SD-D4, không đẩy sang T0.

| Yêu cầu / nguồn | Candidate hiện tại | Bằng chứng / giới hạn |
|---|---|---|
| Bật/tắt âm thanh gốc riêng trong Lồng tiếng và Combo | Native switch có nhãn3locale; off0, manualpositiveOn | Actual48QA,96VoiceReturns/48modeLoops; không thay mixing engine |
| Bot bật lại dùng mức được cấu hình, tắt đưa0 | Web khôi phục mức dương vừa dùng1–100; thiếu thì default100 | Owner duyệt restore-last. Đây là tối ưu Web, không gán hành vi đó cho Bot |
| Giữ cấu hình khi đổi mode và quay lại từ Voice | Private metadata chỉ trong signed tabdraft | Actual48QA; supplement6account/logout/relogin giữ khônglâynhớ37/53;unitfenceđạt |
| Dubbing và âm gốc độc lập | Dubbing0–200/ackmute không bị công tắc âm gốc thay đổi | Unit6/focused80 và48QA; không là output loudness/file proof |

Bot được đọc-only tại pin0d2f376, runtime ENV UNKNOWN. Fallback30 trong
source Bot không được gọi là giá trị production. Không gửi source Bot cho
Gemini, không chạy/import/sửa Bot. Các phần upload/profile/speaker/quote/job/
file delivery T0 giữ nguyên. MainQA48đạt không đóng toàn bộ21SD hoặc goal.
Dead-code/dependency/borrowed-image audit không thực hiện trong SD-D4.

## 24/10/2026 — đối chiếu readiness, giữ đủ yêu cầu gốc SD01..21

Tài liệu gốc tìm thấy: `docs/superpowers/specs/2026-10-18-r218-subdub-bot-parity-uiux.md`,
bảng21controls; plan kế tiếp24/10 và crosswalk final giữ nguyên từng ID. Đây là
spec của dự án, không phải thông tin quảng cáo hay trạng thái production.

| Chữ trong yêu cầu gốc | Candidate hiện tại / khác biệt cần biết | Giới hạn |
|---|---|---|
| “Chỉ cấu hình local không cần khóa toàn trang.” | Cấu hình mở sau signed session+CSRF; trước đó chỉ native formcontrols SubDub khóa, public links vẫn giữ. READ36early mismatch/27changed → GREEN36earlyblocked,72readycoherent | Không mang draft ẩn danh sang tài khoản; không đổi auth hoặc session-clear fence |
| “Sửa ngay nhóm liên quan” | NútSửa tới controlactive; giữ cacheE607/focusE608; final168/1218click336keyboard1050edits | Không tạo nút sửa tệp/source-language chưa được cấp |
| “Mặc định / Đã lưu / Thêm giọng / Tự động thông minh” | Bốn nhóm semantic2/1/1/3, đủ7lane; Auto2,AutoMulti3–8,SmartMulti có3callback riêng | Lựa chọn UI không phải giọng/speaker capability/output engine |
| “Review” và “Kết quả/report” | Thiết lập local/review khớp sauready; statuschờ một lần rồi biến mất; initialreport rỗng/giá chưa có bị ẩn | Không tự tạo duration/count/cost/expiry/request/job/report/đầu ra |

Điểm tài liệu cũ không được hiểu là đã hoàn tất: “control-level đã khóa” chỉ nói
renderer/interaction được đo; không chứng minh upload, ASR/dịch, picker giọng
canonical, consent/preview/save, detection/mapping, quote/charge/job/filedelivery.
21target languages khớp catalog Bot pin đã đọc; không suy ra mọi provider/ngôn ngữ
production hỗ trợ. Crosswalk `R218-SUBDUB-FINAL-UI-CROSSWALK-20261024.md` sẽ ghi
bằng chứng hiện tại từng SD, không xóa yêu cầu còn T0.

Không có deadcode/library/imagecleanup trong đợt này: CHƯA AUDIT, không kết luận
“không còn rác” từ diff UI. Không refactor/xóa fieldsetSmart đang retained/guarded.
Historical C3AXcauseUNKNOWN và LC originalrunstateUNKNOWN vẫn là unknown,
không đóng ngược bằng một lượt chạy xanh. Evidence readiness receipt6383548657.


## 24/10/2026 — SD18: sửa ngay cấu hình liên quan

| Yêu cầu gốc | Hiện trạng có bằng chứng | Còn mở |
|---|---|---|
| Sửa ngay nhóm liên quan | NútSửa theo từngeditable row+mode;1218actualclick/336keyboard đúngfocus trong168configs | Không mở tệp/source-language còncapabilityguarded |
| Không mất bản nháp hoặc chuyển màn | 1050editsreviewupdates/168modeLoops168VoiceReturns;perEditURL/mode/draft/root/requestsame | Không giữfile/preview/providerprofile/quote/job |
| Bấm thật,không bị remount/che | E607blurtraceRED→GREEN giữpressednode;E60815actions/3widths thấycontrolgiữfocus;strictfinal168 | OriginalreadinessUNKNOWNvẫnE3-READINESS,khôngđánhđồngrootcause |
| Dùngđượcphone/keyboard/theme/locale | 44x44/text12.35/focus5.86/2x/504LFassets/0overflow-errors | KhôngnativeSafari/PWA/OStextscale/fullpageAA/motion/LIVEproof |

SD18review navigation trướcEDIT chưa có,nayđạtUIcụcbộ;source/engine/cost/
expiry/readiness theoDTOthật vẫn chưađược tựsuy. Finalparent/Tester/oneE3
push chưađóng. EvidenceR218-SUBDUB-REVIEW-EDIT-QA-20261024.json.

## 24/10/2026 — SD07..14: nhóm lựa chọn giọng, không rút gọn chức năng

| Yêu cầu gốc | Hiện trạng có bằng chứng | Giới hạn |
|---|---|---|
| Bốn nhóm Default/Saved/Add/SmartAuto | 4role-group,7radio/native order2/1/1/3;84signedconfigs/588click+588arrow | Không bốn radiogroup/card mới;không actualvoice capability |
| Đủ Nữ/Nam/saved/custom/Auto2/AutoMulti3–8/Smart | Tên ngắn hiển thị,tên đầy đủ ARIA/review;168VoiceReturns và3callback giữ | Không savedpicker/profileapply/clone/detection/engineoutput |
| Gọn trênphone/desktop,không giấu lựa chọn | 36matched ngắn hơn65.20–156.36px;48phoneAuto3hàng;82fitDefaultpairs cùnghàng | 2ENCombo320 hẹpwrap;khôngnativeiOS/fullpageAA/motionproof |
| Không lộ control sai mode | 84nonvoice checks assert zero visible inputs/labels/groups toàntrang | EDIT/READINESS/parentfinal168/Testerdelivery còn mở |

OriginalSD07/SD08..14 được giữ trong spec2026-10-18; flat7radio là trạng thái
trướcGROUP,không còn UIcục bộ hiện tại. SourceGROUP chưa push/deploy; không
ticktoànSubDub/Botparity vì group/UI đạt. EvidenceVOICE-GROUPS-QA20261024.

## 24/10/2026 — SD15/16: thao tác âm lượng trên điện thoại

| Yêu cầu | Hiện trạng đo được | Giới hạn |
|---|---|---|
| Slider gốc/lồng tiếng dễ thao tác | <=480px fullrow,min200x44 ở48phoneconfigs,thayCombo32036x44 | Không chứng minh nativeiOS/physicaltouch |
| Giữ0–100/0–200/mute/draft | Main72+followup24/48modeRoundTrips/192VoiceReturns/number-range-review-output đồngbộ | Không realaudio/provider/mixingoutput |
| Không phá desktop | 24configs so exactcomputedgrid/geometry vớiRED | Không fullpageAA/motion/LIVE |

SourcechỉCSS2rules/9dòng;SD15/16semanticstừBotvẫngiữ. GROUP/EDIT/READINESS
vàE3finalmatrix chưađóng;khônglấyRANGEcục bộđểticktoànSubDub.

## 24/10/2026 — E3 label/contrast, không đánh đồng có nút với đủ UX

| Yêu cầu | Hiện trạng mới đo | Chưa hoàn tất |
|---|---|---|
| SD06/17 chọn quy tắc/hiển thị | 2uniqueidforpairs;24association/keyboard/mode-review tests trong48configs | Không cueeditor/outputthật |
| Hướng dẫn đọc được sáng/tối | Scopedhelperink;768mẫumin8.83653/unknown0 | Không fullpageWCAG/device/motionproof |
| SD07 nhóm giọng/SD18 sửa từreview | READ168 xác nhận flat7radios và thiếueditnav | GROUP/EDIT tiếp tục,khôngchuyểnT0đểbỏsótUI |
| Slider trênmobile | Combo320range36x44 ở12mẫu | RANGE sẽ sửa theoUIcontract riêng |
| Khởi tạo/sessiondraft | Mộtline-rule reviewmismatchởenhancedprobe;causeUNKNOWN | ParentREADINESS giữmở dùstable-signed48rerunđạt |

OriginalSD01..21 vẫn giữ;label/contrast chỉ hai childlocal,khôngfullE3/Botparity.

## 24/10/2026 — SD18..20: review có dữ liệu, không bày report rỗng

| Yêu cầu gốc | Hiện trạng có bằng chứng | Giới hạn còn mở |
|---|---|---|
| Review cấu hình trước xử lý | Exactkeyset/copy/mode/balance giữ trong96 cấu hình;2dòng unavailable tĩnh ẩn riêng | Không có canonical quote;không biến placeholder thành giá |
| Kết quả/báo cáo | Khung khởi đầu rỗng ẩn cảwrapper;3nonemptyboundary diagnostics khôi phục | Không có reportDTOconsumer/job/outputthật;khôngtickSD20runtime |
| Không mất chức năng | 336lanechoices/96VoiceReturns/B4/mix/draft/gates giữ,2attrs+2rulesonly | E3fullUI vàT0authority vẫn mở |

Nguồn gốc `2026-10-18-r218-subdub-bot-parity-uiux.md` SD18..20; đối chiếu
với `2026-10-24-r218-subdub-empty-review.md`. Snapshot tài liệu cũ về report
đang trống không còn là UI hiện tại; chức năng engine chưa được hoàn thành
chỉ vì không còn khung rỗng. C3receipt6379877100 là deliverynhánh,khôngLIVE.

## 24/10/2026 — SD07..14: clarity không thay cho chức năng giọng thật

| Yêu cầu | Hiện trạng có bằng chứng | Giới hạn còn mở |
|---|---|---|
| Không ô giải thích lặp/vô nghĩa | C3 chỉ ẩn guardedSmartdescription/hint, giữnote1; final48visual/AX | Không gọi đây là redesign/grouping toàn bộ voice UI |
| Không mất lane nhưBot | 7radio/3Autocallback riêng;336 lượt chọn/review,96Voice returngiữdraft | Saved profile application/clone/detection/Smart engine còn authorityT0 |
| Giữ cấu hình, tìm ngôn ngữ | B4filter/target/customISO/mix0_200/review/sourceCTAkhôngđổi | Không actualprovider/output/LIVEproof |
| Không che trạng thái có dữ liệu | Selector chỉ Smart statusguarded; non-guarded CSSdiagnostic còn hiện | Diagnostic không chứng minh server đã cấp capability |

Nguồn gốc SD01..21/SD07..14 được giữ; C3source chỉ một rule/5 dòng CSS,
JS/API/auth/backend/oldtests/Chat không đổi. FirstAXmismatchcauseUNKNOWN,
final48 sau localizedreadiness đạt không đồng nghĩa đã chẩn đoán transient.
D3emptyreport/E3fullUI/motion và runtime vẫn theo checklist mở.

## 24/10/2026 — SD-05: danh mục dễ tìm, không mở quyền dịch giả

| Yêu cầu gốc | Hiện trạng có bằng chứng | Giới hạn còn mở |
|---|---|---|
| Catalog searchable đầy đủ | B4 tìm21 mã/tên VI/EN/ZH trong3 mode; actual72targetstates/24source-only | Không phải mọi ngôn ngữ provider; catalog chỉ khớp snapshot Bot đã pin |
| Giữ cấu hình khi tìm | Pin selected/count không tínhpin/no-match giữ lựa chọn/clear21; unit5+actual96 | Query không được coi là lựa chọn đã xác nhận hoặc đầu vào dịch |
| Mode/Voice return không mất target | Reset options trước apply, latest target/customISO/giọng/mix0-200 giữ trong browser | Không chứng minh saved-profile application/upload/speaker detection |
| UI dễ đọc và dùng bàn phím | 288 mẫu chữ mới >=5,2238:1, input16px/46px/focusAX/text2x, không overflow | Không OS textscale/nativekeyboard/PWA/scroll-motion/fullpageAA proof |

Nguồn gốc SD01..21: `2026-10-18-r218-subdub-bot-parity-uiux.md`.
Spec thực hiện: `2026-10-24-r218-subdub-language-findability.md`.
B4 chỉ khép tìm ngôn ngữ và giữ draft trong UI; không thay engine, auth,
giọng đã lưu, quote/job/output. C3/D3/E3 và runtime/LIVE vẫn mở.

## 24/10/2026 — SubDub SD01..21, không đếm nút thành chạy thật

| Yêu cầu | Hiện trạng đo được | Còn thiếu, giữ checklist |
|---|---|---|
| Ô nhập dễ đọc | SD-B3: 96 cấu hình/552 mẫu computed16px, giữ cấu hình và gate; source một rule CSS | iOS/OS text-scale/contrast toàn trang chưa đo trong B3 |
| Ngôn ngữ đầy đủ và dễ tìm | 21 target code khớp catalog Bot pin, Việt/Anh/Trung đầu danh sách; actual selection/review đúng | 36 trạng thái chưa có search; SD-B4 kế tiếp, engine language support không suy từ catalog |
| Bảy lane giọng riêng | Nữ/Nam/saved/custom/Auto2/AutoMulti3–8/Smart có lựa chọn local | 24 khối Smart lặp hai câu; SD-C3; saved-profile application/speaker detection còn contract |
| Không ô vô nghĩa | Source hiện có 48 report rỗng trong READ48 | SD-D3 phải dọn không che kết quả/lỗi thật; upload/quote/job/output vẫn T0 |

Nguồn gốc `2026-10-18-r218-subdub-bot-parity-uiux.md` SD01..21; plan tiếp
`2026-10-24-r218-subdub-ui-closeout.md` giữ từng mục và các lock B2/C2/D2/E2.
Không bỏ chức năng để giao diện gọn, không bật control giả khi chưa có authority.

## 24/10/2026 — Music MU07: tách quay lại bộ cũ và tạo bộ mới

| Yêu cầu gốc | Hiện trạng có bằng chứng | Chưa được coi là hoàn thành |
|---|---|---|
| Chọn/sửa/quay lại ba gợi ý | MU07-A giữ tối đa ba prompt thực nhận, hai route/phiên; sau estimate mở native disclosure, Copy/Apply handler cũ; 19 unit/48 browser | Không sinh bộ mới, selected ID hoặc prompt giả |
| Chọn lại không dùng báo giá sai | Actual Apply1→quote→history→Apply2/edit→new quote; field/focus và quote-stale giữ đúng cả 48 cấu hình | Không khôi phục receipt/giá hoặc mở quyền confirm từ cache |
| Dễ đọc ở hai theme | 2.304 mẫu current/retained >=5,217:1; hover48 >=5,161; focus48 >=5,2; disclosure44px/AX/text2x | Không phải OS Dynamic Type/PWA/FPS/production evidence |
| Bot có đổi bộ/sửa mô tả tạo lại | Git snapshot Bot 0d2f376… có offset và pending input; Web chưa có contract rotation/version/no-effect được xác minh | Next-set và edit-regenerate giữ T0 sau UI/motion; không giả bằng shuffle hoặc gọi draft tùy tiện |

Nguồn gốc MU01..12: `2026-10-18-r218-02-03-voice-music-controls.md`.
Chi tiết từng callback và contract: `reports/audit/R218-MU07-BOT-WEB-CONTRACT-20261024.md`.
Bot snapshot không phải production truth. Source nhánh/QA không đồng nghĩa
đã deploy, tạo âm thanh hoặc toàn bộ Music ngang Bot. MU07 tổng vẫn mở.

## 24/10/2026 — Music MU08 và trạng thái rỗng F/H

| Yêu cầu gốc | Hiện trạng có bằng chứng | Giới hạn còn mở |
|---|---|---|
| Xem lại trước xác nhận | Snapshot flow.input được trình bày trước CTA, VI/EN/ZH; F172tests/browser48 | Controlled quote state không chứng minh native báo giá hoặc âm thanh |
| Không ô vô nghĩa | Hai form Music chưa có flow không render card kết quả; H12tests/54VMomissions/browser48 | Không giấu error/guarded/draft/report có dữ liệu; nonMusic giữ nguyên |
| Không mất draft/gate | Edit giữ snapshot, khóa confirm; revert/expiry/newestimate đúng; 48browsercases | Không sửa hợp đồng engine/thu Xu hoặc biến sửa form thành quote mới |
| Nội dung đầy đủ, dễ đọc | Full escapedUnicode/lyrics;720contrast>=5,522;2xt textstress,disclosure44px | Không suy thành Dynamic Type máy thật hoặc canonical output PASS |

Tài liệu gốc không còn đúng nếu diễn giải “có control” thành “đã có đầu ra”.
MU08 UI gap đã xử lý; MU02 style/style_prompt, MU06 half/full, MU07 đổi bộ
gợi ý và MU09..12 audio/editor/recovery giữ nguyên checklist mở, không bỏ sót.
Đây là source nhánh/QA; không khẳng định production đã đổi.

## 23/10/2026 — đối soát Music và bản vá đọc/nhập E

| Yêu cầu gốc | Hiện trạng có bằng chứng | Không được suy diễn |
|---|---|---|
| Form Music dễ đọc, dễ nhập | Final48 actual QA: helper/label/placeholder >=4,5:1 và input16px | Không chứng minh tạo nhạc/giao tệp hoặc iOS Dynamic Type |
| Không mất lựa chọn khi đổi gói/giọng/mode | 144 tier checks, 288 vocal checks, 48 mode/Back draft checks | Không chứng minh giọng trong audio output |
| Đủ yêu cầu MU01..12 | Có bảng đối soát từng yêu cầu, source anchor và giới hạn test | Không coi 27 test VM là toàn bộ Bot parity |
| Idea và phong cách riêng | Chưa có style input tách biệt; draft `style` và bridge `style_prompt` không đồng nhất | Không thêm field/mapping phỏng đoán |
| Review trước xác nhận | F/H đã có summary snapshot và initial-state gọn | Không sửa tiền/receipt/confirm; native output/LIVE còn mở |
| Độ dài half/full, hai bản, player/editor | Control hoặc metadata không đủ proof xử lý | Giữ backlog contract/runtime, không dựng output hoặc editor giả |

Nguồn chi tiết: `reports/audit/R218-MUSIC-REMAINING-UI-CROSSWALK-20261023.md`.
Sai lệch của tài liệu cũ là đã gộp control có sẵn với khả năng thực thi/đầu ra;
hai trạng thái này nay được theo dõi riêng, không xóa yêu cầu chưa đạt.

## 23/10/2026 — Music/SFX D2, cùng chức năng nhưng bỏ màn hình kỹ thuật

| Yêu cầu gốc/P2 | Source hiện tại | Bằng chứng/giới hạn |
|---|---|---|
| Web gọn, không ô vô nghĩa | Intro/stat/boundary/empty/scopeẩn;formvàresultcódata mớihiện | D2actualbrowsergate,khôngsuytừCSSsource |
| Native5preset/3textitems | IDs,fields,validators,explicitPOSTvà3items/cautions/reviewgiữ | FullNode1073/Python395portable;DTO/nativebrowsertáchkhỏipresentationdoubles |
| Chữ đúng ngôn ngữ | 2localH1/8copyrows/cảnhbáostale dùngcatalogue | New52tests;khôngdịchserverdata |
| Không mất nội dung khi sửa | LocalizedstaleDOMparagraphthayVIpseudocopy;SFXcomparison/remountlogicgiữ | Actualremountcheckbắtbuộc;khôngdùngrendererunitthaylifecycleproof |
| Giao nhạc/hiệu ứng thật | Lát này vẫnchỉhướng/bảngvănbản | Audio/player/download/save/reuse/BotparityvẫnOPEN |

Tài liệu cũ trình bày nhiều panel giới hạn như sản phẩm hoàn chỉnh không còn
phù hợp: giao diện gọn không đồng nghĩa engine đã tạo âm thanh. Không xoá
cảnh báo nội dung thực hoặc nới các cổng engine để tạo cảm giác đã xong.

## 23/10/2026 — đối chiếu Music presentationD1

| Mục gốcP2/copycatalogue | Hiện trạng được đo | Giới hạn |
|---|---|---|
| Hai form đúngngônngữ |4descriptionplaceholder/help dùnghelperlocale,schemagiữnguyên |Khôngđổifieldname/options/validation |
| SFXresultchrome |Direction/Mixnote/Tránh→3localizeddt,2fallbackVI→localized |Generatedserverdatatheobrieflanguage,khôngtheoUIlocale |
| Themeđọcđược |Helperlight2.021→5.797contrast,dark5.522;input16px |Scoped2rules,khôngtái thiết kếdesignsystem |
| Webgọn/appthật |48configs/96states,3nativeitems,0overflow/error |D2boundary/empty/scope/intro vẫnchưadọn;khôngwholeproductPASS |

Full1021Node/Python21/independent86.Newtestsrealrenderer+catalogue,nhưng
normalizeridentitydouble nênkhôngDTOproof;actualsignednativeQA táchriêng.
Lỗigốc làbỏqua catalogueởvàichỗvàlegacyhelpercolor,khôngphảithiếuprovider.
CIpháthiệnappendCSSởEOFviphạmranhgiớifinalChatlayer,khônglỗiChatdeclaration.
R2chỉdời2rulestrướclớpChat;testChatgiữnguyên,90foundation/395portableCIđạt;
actual48configs96statesđolạivẫngiữcontrast/input16px. KhôngsuyraLIVE/audioPASS.

## 23/10/2026 — đối chiếu lỗi/khôi phục thao tác Music/SFX

| Yêu cầu từ P2/nativeflow | Hiện trạng có bằng chứng | Giới hạn |
|---|---|---|
| Lỗi cùng ngôn ngữ giao diện |28localmessages→10nhóm/tool,20cataloguerows; realcatch consumer/realpayload lengthshape | Không sửa servererror, quyền hoặc bộvalidator |
| Không lộ thông báo kỹ thuật từ máy chủ | Unknown/serverpayload→localizedretry, numericHTTP401/403→auth; prototypekeystrictownproperty | Không giải thích lý do lỗi không được xác minh |
| Luồng khác không bị ảnh hưởng | Exact2actionguard ởoutercatch; MusicLibrary18/18,15helpers/10files equalBASE | Không toàntrang/Product/BotparityPASS |
| Gửi lỗi vẫn thao tác tiếp được bằng phím | D0capture/flag/restore10lines, test10/10 inclotherfocus/stale/wrongroute/disconnected/success/guard | Actualfocusmatrix vàdelivery xem evidenceJSON, không suy từ syntheticDOM |

FullNode1016/1016; Python21/21. BworkerR1/R2harnessfails→primarytesttakeover
và2sourcecorrections; D0productionR1/R2identicalverbatim, testF02 bổsung2cases
sau hai lượt thiếucoverage. Không vòng3 hoặc resetSPEC để néfail. Văn bản gốc
chỉ kiểm rendering/copy cân bằng đã thiếu lateerror/focus; đây là bổ sungđúng
luồngthật, không thêm nhạc/audio/player/providerjob giả.

## 23/10/2026 — đối chiếu Music/SFX submit và guard

Nguồn gốc: R218-03/P2, hai native action và backend guard contract hiện có.
Catalogue/presentation tests ban đầu không bao phủ pending/toast sau gửi;
ngay cả HTTP200 có thể là guarded, không phải kết quả thành công.

| Yêu cầu / giả định trước | Hiện trạng có bằng chứng | Chưa đóng |
|---|---|---|
| Thông báo đúng ngôn ngữ sau gửi |9feedbacksites/helper/8cataloguerows; testA10/10, signedQA36 cấu hình | Validation/error/outercatch và fieldhint/technicalcopy |
| Bị chặn không mất nội dung hoặc báo nhầm kết nối | Guard Music17keys/16strictfalse không composer; parser/caller thật3/3 và actualMusic18 | Không mở quyền/provider/job/output hoặc chứng minh bản quyền |
| Kết quả thành công phải đúng input và đủ cấu trúc | Success validators/matcher byteequalBASE80f12d2; Python21/21; nativebrowser3items | Không dùng boundaryshell composer:{} hay testdouble làm fullDTOproof |
| Music/SFX như Bot | Hai công cụ này chỉ lập hướng/cue bằng văn bản | Audio generation/editor/player/download/save/reuse/Botparity |

Tổng hồi quy1000Node; độc lập47/47, Critical0/Important0. Evidence
`reports/audit/R218-MUSIC-SFX-SUBMIT-GUARD-QA-20261023.json`; đây là localQA,
chưa merge/deploy/LIVE. Không xóa hoặc gắn PASS các finding lịch sử ngoài scope.

## 23/10/2026 — Music/SFX interaction, không thay scope sản phẩm

Nguồn gốc: R218-03/P2, hai locale-presentation test và hai catalogue Music
Directions/SFX. Catalogue cân bằng và renderer ban đầu xanh không chứng minh
thông báo sau thao tác đã dịch: bốn hàm late-event từng ghi literalVI; stale
chỉ ghi lầnđầu nên edit2 thay bằngselectedmessage. Probe6lane/locale và RED
22assertions tái hiện lỗi này. Không dùng testsource banđầu để đóng interaction.

| Yêu cầu gốc | Hiện trạng kiểm được | Ranh giới chưa đóng |
|---|---|---|
| Chọn5preset, biểu mẫu giữ ngôn ngữ | Realfunction30/30 sau sửa, VI/EN/ZH; unknown/disabled fail-closed | Chưa tự suy ra âm thanh/provider |
| Biết kết quả không khớp nội dung mới | Edit1/2/3 giữ cảnh báo địa phương hóa, kết quả/input/event không đổi | Không tự gửi yêu cầu hoặc tạo lại kết quả |
| Nhạc nền/bài hát/KhoSFX/player/reuse nhưBot | Hai endpoint này chỉ trả3hướng hoặc3cue bằngvăn bản | Generation/editor/player/audio/download/save/reuse/finaloutput vẫn ởP2 mở |

Evidence `reports/audit/R218-MUSIC-SFX-INTERACTION-QA-20261023.json` phân biệt
Node/Python/browser/delivery. Không thay danh sách gốc hay xóa các finding cũ.

## Voice notice — đối chiếu 23/10/2026

| Yêu cầu gốc / điều phải giữ | Hiện trạng local được đo | Không được suy diễn |
|---|---|---|
| Hạn chế thao tác cần rõ, không nút giả | Nguyên văn manageGuarded chỉ một lần trước ready/nonemptylist thay10lần cho10giọng;0ởempty/nonready | Không phải các thao tác rename/default/delete/preview đã được triển khai |
| Thông tin từng giọng đầy đủ | Stripping đúng paragraph cho thấy toàn bộ bundle còn lại bằngBASEefbe362; metadata/escaping/flags/limit/routes giữ nguyên;957Node/10PythonSource | Không chứng minh dữ liệu canonical production hoặc audio thật |
| UI gọn nhưng đọc được, sáng/tối/mobile |30configs VI/EN/ZH,375/landscape,300profile states/120readviews; noticecontrast>=5.522:1, error/overflow/write/external0 | QA dùng READfixtures rõ nguồn, chưa phảiLIVE hoặc mọi thiết bị thật |

Đợt này chỉ bỏ sự lặp nội dung, không xóa ý nghĩa giới hạn và không thu gọn mất
field sản phẩm. Các mục canonical Voice Vault trong R218-02A vẫn mở/T0.

## Voice canonical flags — đối chiếu 23/10/2026

Nguồn gốc: R218-02A yêu cầu tts_ready/preview_ready/default do canonical authority
xác nhận; catalogue `voiceUi.library.*` chỉ là nhãn, không phải quyền thực thi.

| Yêu cầu | Bằng chứng hiện tại | Không được suy diễn |
|---|---|---|
| Nhãn mặc định và sẵn sàng phản ánh dữ liệu xác nhận | Bảy predicate tại renderer/2select builders dùng===true; Node24/24 với true/false và13badflag vectors ở3locale | Không suy rằng mọi DTO production đều sai kiểu hoặc cần đổi backend |
| Giọng ready được giữ, tên/consent/status không đổi | Focused48/48, fullNode951/951; thẻ/option giữ giọng true, default sai kiểu chỉ mất marker; input không mutate | Không chứng minh đặt mặc định/rename/delete/preview audio hoạt động |
| UI và integration render trạng thái đúng |18configs/180profile states trong signed app với read-only fixtures, lỗi/tràn ngang/UIwrite/external0 | Không gọi fixture bootstrap/profile là API canonical hoặc LIVE đã đạt |

Các mục kho giọng thật, tìm kiếm/phân trang/management/preview/apply/reuse vẫn mở
theo contractR218-02A; không dùng lần sửa flag này để đóng Bot-parity toàn Voice.

## Dashboard — đối chiếu ngày 23/10/2026

Nguồn đối chiếu: `tests/test_p0_webapp_v2_01_customer_dashboard_transformation.py`,
`tests/test_webapp_u01_e01_dashboard_launcher_consolidation.py` và catalogue
`DASHBOARD_ENTRY_COPY_ROWS` trong `static/portal/portal-i18n.js`.

| Yêu cầu/luồng gốc | Hiện trạng được đo ở local | Giới hạn |
|---|---|---|
| Sáu lối vào sản phẩm, không nhân đôi điều hướng | Sáu route giữ nguyên trên18 cấu hình; main layout gọn được giữ | Có link không chứng minh engine sản phẩm hoạt động |
| Tiêu đề và ngôn ngữ đúng | Một H1, sáu H3, vùng tài khoản có H2 riêng; Node22/22 và Python6/6 | Không suy ra toàn bộ trang sau đăng nhập đã đạt |
| Tóm tắt tài khoản dùng dữ liệu canonical | Server plan được escape; boolean VIP dùng nhãn thành viên VIP, không tự đặt tên gói; unknown giữ— | QA không liên kết ví thật, không xác minh số dư production |
| Menu mobile còn dùng được sau resize | 12 vòng mở/resize/Escape và3 lần mở Voice bằng bàn phím đạt | Chưa phải kiểm thử mọi trình duyệt/thiết bị thật |

Đính chính source main406127e: H2 sản phẩm thay H1, nhãn số dư làm tên vùng
tài khoản và fallback “Business VIP” không phải chuẩn để bỏ regression test.
Giữ bố cục mới nhưng phục hồi ngữ nghĩa/catalogue; không diễn giải booleanVIP
thành quyền lợi, giá hoặc tên gói dịch vụ chưa được máy chủ xác nhận.

## Voice — phân biệt hồ sơ hướng đọc với kho giọng thật, 23/10/2026

Nguồn yêu cầu Bot giữ tại `2026-10-18-r218-02a-voice-vault-canonical-contract.md`:
list/rename/default/soft-delete/preview/use-video là chức năng giọng âm thanh.
Các số endpoint của Web không được thay thế yêu cầu này.

| Chức năng gốc | Hiện trạng đo được | Không được suy diễn |
|---|---|---|
| Quản lý giọng dùng TTS/SubDub/Video | `/voice/saved` chỉ có GET tối đa50 mục đã xác minh; management/preview/apply còn mở |22endpoint metadata không chứng minh đủ Bot-parity |
| Hồ sơ hướng thể hiện và lời thoại (Web bổ sung) | `/voice-studio` có22endpoint metadata; Python runtime31/31, source10/10; lifecycle/readback6cấu hình qua24ghi QA | Không sinh audio/provider voice profile |
| Thông báo theo ngôn ngữ giao diện |4cấu hình EN/ZH thực còn toast lọc tiếng Việt | Không đóng locale từ catalogue render đúng |
| Bố cục gọn, không ô kỹ thuật lặp |Disclosure soạn hướng đọc đã bỏ3ô; worker1line, renderer6/6, browser18configs/36states và fullNode933/933 | Chỉ đóng cụm này ở local UI; không đóng toàn sản phẩm hoặc LIVE |

Đính chính mọi cách đọc tài liệu cũ: “Voice Vault” trong tên endpoint
`copyfast_voice_studio.py` là bản ghi hướng đọc Web, không đồng nghĩa giọng đã
huấn luyện/lưu trong Bot. Không xóa mục thiếu khỏi checklist để gọi là hoàn thiện.

Thông báo hồ sơ hướng đọc đã được sửa và kiểm tra ở18 cấu hình VI/EN/ZH ×
light/dark ×390/768/1440. Các action read giữ payload/offset/route, không thông
báo thành công khi failed/stale/null/undefined/non-ready hoặc đổi trang. Failure
503 sau retry xóa dữ liệu cũ, khôi phục sau khi đọc lại; rate gate thật không bị
nới (72 phản hồi503 điều khiển, 0 phản hồi429).

## Free Tools — đối chiếu ngày22/10/2026

| Chức năng | Đã chứng minh | Còn mở |
|---|---|---|
| Làm sạchSRT/VTT và tảiTXT | Làm sạch nội dung rồi tải bytesTXT khớpUI ở12cấu hình appQA thật | Chưa suy ra mọi định dạng phụ đề đều được hỗ trợ |
| Trích liên kết/mã nhúngYouTube | Parser/link/ID giữ đúng; browserload/error/retry đúng, khôngsrc rỗng/CSPinline | Ảnh kiểm soát không chứng minh YouTube luôn có mọi độ phân giải; không cam kết chất lượng từ nhãn |
| Voice và sản phẩmBot | InitialUI không tự điền nội dungQA/hero pill ở96states | Không đóng quote/provider/engine/job/output/delivery từ việc kiểm giao diện |

## Billing / QR — đối chiếu ngày22/10/2026

| Chức năng | Hiện tại có bằng chứng | Còn mở |
|---|---|---|
| Nạp Xu PayOS | Guard capability và catalog server; catalog rỗng không tạo radio giả; contract Node6/6 | Không gọi checkout/provider; production delivery chờ push |
| Nạp thủ công | Method/amount progressive disclosure; options/history state tách; retry options GET; wallet21/21 cô lập | Không submit production, không chứng minh Admin approval/credit |
| Gói dịch vụ | 4 monthly +20 combos từ API; UI 24 card sau hydrate; không suy giá local | Public sale SKU/giá Core Bridge chưa phát hành; desktop production chưa có viewport override đáng tin |
| ACB/VietQR | Selector readiness chỉ một ACB; IDs/history giữ; QR natural portrait không crop; browser120 cases | Chưa deploy/live recheck |
| YouTube thumbnail labels | Bỏ hứa 1080p/720p/360p khi chưa đo; Free Tools7/7 | Không chứng minh mọi URL YouTube có ảnh hoặc media download |

## SD-C2 — nối giao diện, chưa phải áp dụng giọng canonical

Web đã giữ ngữ cảnh SubDub→kho/thêm giọng→quay lại trong cùng tài liệu;
48 vòng browser có profile locale/theme thực, không chỉ kiểm href. Quyền
lưu/preview/áp dụng profile vào SubDub và báo giá/engine/delivery vẫn chưa
được chứng minh từ bước điều hướng này. Không chuyển các mục T0 thành PASS.

## SubDub — không đồng nhất control có mặt với parity Bot

Draft UI cần đi theo cấu hình mới nhất, giữ0/200 và format riêng. Bản test21
đầu chưa chạy capture thật nên kết luận đã giữ draft là quá rộng; đã mở lại
và sửa cùng SD-B2 bằng kiểm thử control/browser. Khả năng Bot gồm nhận tệp,
nhận diện người nói, dịch/lồng tiếng, kho giọng, báo giá và giao tệp vẫn chưa
được chứng minh từ lớp presentation. SD-C2/SD-D2/SD-E2 và các gap T0 giữ mở.

## Đối chiếu Music/SFX Library — 21/10/2026

Yêu cầu Bot gồm nghe/tải/lưu/dùng cho video. Web Library hiện chỉ hiển thị
thông tin bộ sưu tập; không được gọi là đã đủ các khả năng đó. MU-E-01 sửa
đúng lỗi role SFX, phản hồi failed/stale, locale phân trang/toast và empty/loading.
Browser39 cấu hình và test36/36 chứng minh thao tác trình bày, không phải
khả năng nghe/tải, quyền backend hoặc LIVE. MU-E-02 copy và Q0-TOAST-STACK
vẫn mở tại completion ledger.

MU-E-02 đã rút câu chữ hiển thị nhưng không mở thêm khả năng nghe, tải, lưu,
dùng cho video hay quyền backend. Bằng chứng copy/browser nằm ở
`reports/audit/R218-MUSIC-LIBRARY-COPY-QA-20261021.json`; Q0-TOAST-STACK vẫn mở.

## Cập nhật Music/SFX guard — 22/10/2026

Thẻ chặn của `/music/library` và `/music/sfx-library` không còn ba chip kỹ
thuật lặp lại. Người dùng chỉ thấy lý do cần đăng nhập/cấp quyền, thao tác kiểm
tra lại và liên kết sang workspace; không có thay đổi về danh sách, capability,
nghe thử, tải tệp hoặc bàn giao. Test riêng `1/1`, focused Music/library
`57/57`, toàn bộ Node `908/908`.

## Cập nhật Content Studio guard — 22/10/2026

Các trạng thái chưa có quyền/đang tải/tải lỗi của Content Studio đã bỏ chip kỹ
thuật lặp; vẫn giữ thông điệp nguyên nhân và nút thử lại khi capability server
đã cấp. Không thay đổi authoring, ownership, API hay dữ liệu. Test riêng `1/1`
và toàn bộ Node `909/909`.

## Cập nhật Project Center guard — 22/10/2026

Project Center giữ lại thông điệp và nút thử lại cần cho người dùng, bỏ các
chip kỹ thuật lặp trong ba trạng thái chưa xác minh. Không đổi API, quyền sở
hữu, danh sách dự án hay authoring. Test riêng `1/1`, toàn bộ Node `910/910`.

## Cập nhật Campaign Planner guard — 22/10/2026

Campaign Planner giữ nguyên thông điệp và nút thử lại cần thiết, bỏ chip kỹ
thuật lặp trong ba trạng thái chưa xác minh. Không đổi lịch, publish,
capability, API, dữ liệu hoặc boundary AutoPost. Test riêng `1/1`, toàn bộ Node
`911/911`.

## Cập nhật Bot companion intro — 22/10/2026

Intro handoff Bot/Analytics đã bỏ chip authority, report/charge và identity lặp;
vẫn giữ command, URL, connection guard và ranh giới dữ liệu. Không đổi Bot
authority hoặc callback. Test riêng `1/1`, toàn bộ Node `912/912`.

## Cập nhật Video Factory và Guide quyền sử dụng — 22/10/2026

Hai guard customer này chỉ còn nguyên nhân cần phiên Web; chip phiên,
execution/publish/license lặp đã bỏ. Không đổi route, quyền, workflow video,
hay hợp đồng quyền sử dụng. Test riêng `1/1`, toàn bộ Node `913/913`.

## Cập nhật Image utility guard — 22/10/2026

Các thẻ guard của sáu Image utility chỉ còn thông điệp nguyên nhân và hành động
cần làm; chip phiên/cache/fallback được ẩn theo selector route-scoped. Không đổi
engine, file, capability, API hay output. Test riêng `1/1`, toàn bộ Node `914/914`.

## Cập nhật Document/PDF utility guard — 22/10/2026

Các guard Document/PDF utility chỉ còn nguyên nhân và thao tác cần làm; chip
phiên/storage/runtime/fallback được ẩn theo selector route-scoped. Không đổi
bytes, storage, capability, API hay delivery. Test riêng `1/1`, toàn bộ Node
`915/915`.

## Cập nhật Support Admin guard — 22/10/2026

Thẻ guard `/admin/support` chỉ còn nguyên nhân cần quyền; chip vai trò/cầu nối/
dữ liệu dự phòng được bỏ. Không đổi RBAC, yêu cầu, reply, escalation hoặc
finance boundary. Test riêng `1/1`, toàn bộ Node `916/916`.

## Cập nhật remaining customer guard surfaces — 22/10/2026

Project Package, Asset Vault, Inbox, Automation, Operations và Video
finalization đã bỏ chip implementation lặp theo selector route-scoped, giữ
nguyên metric thật và action. Không đổi capability, storage, job, API hay
delivery. Test riêng `1/1`, toàn bộ Node `917/917`.

## Cập nhật Campaign boundary — 22/10/2026

Campaign detail và hàng tự rà soát đã bỏ chip mã/CSRF/publish/audit lặp, giữ
nguyên giải thích nghiệp vụ và mốc lịch thật. Không đổi state, lịch, publish
hay API. Test riêng `1/1`, toàn bộ Node `918/918`.

## Cập nhật Voice Studio lane — 22/10/2026

Lane rail Voice Studio đã bỏ nhãn bảo vệ lặp, giữ nguyên title/description/
action và toàn bộ route/capability handoff. Không mở thêm Voice Vault runtime,
preview, rename, delete hoặc reuse. Test riêng `1/1`, toàn bộ Node `919/919`.

## Cập nhật SubDub Smart Multi empty-map — 22/10/2026

Smart Multi chỉ hiển thị mô tả và hook khi chưa có speaker payload; khung bản đồ
người nói rỗng được ẩn, không đoán giọng hoặc kết quả. Không đổi upload, engine,
quote hay delivery. Test riêng `1/1`, toàn bộ Node `920/920`.

## Cập nhật Guide/Video zero-metric — 22/10/2026

Guide Center và Video Factory đã bỏ các ô `0` kỹ thuật về execution/provider/
publish, giữ số chủ đề và số bước có ý nghĩa. Không đổi catalog, route hay
workflow boundary. Test riêng `1/1`, toàn bộ Node `921/921`.

## Cập nhật Free Prompt Gallery zero-metric — 22/10/2026

Gallery giữ số nhóm mẫu/ngành và bỏ ô `0` về thực thi/thanh toán. Không đổi
catalog, filter, xem chi tiết, sao chép, lưu hoặc boundary. Test riêng `1/1`,
toàn bộ Node `922/922`.

## Cập nhật Voice Studio policy — 22/10/2026

Policy Voice Studio chỉ còn một lời giải thích capability theo trạng thái máy
chủ thay cho bốn ô lặp; consent notice và guard thật giữ nguyên. Đã cân bằng
catalog VI/EN/ZH cho key mới. Test riêng `1/1`, toàn bộ Node `923/923`.

## Cập nhật Chat Workspace boundary — 22/10/2026

Chat Workspace chỉ còn một thông điệp capability theo server thay cho năm ô
receipt/model/provider/payment/output lặp. Không đổi composer, thread, auth,
Chat Run hoặc boundary dữ liệu. Test riêng `1/1`, toàn bộ Node `924/924`.

## Cập nhật Image Studio boundary — 22/10/2026

Image Studio chỉ còn một lời giải thích capability thay cho bốn ô provider/
preview/job/payment lặp; key mới đã cân bằng VI/EN/ZH. Không đổi route, image
engine, Asset Vault, API hay output. Test riêng `1/1`, toàn bộ Node `925/925`.

## Cập nhật Workspace boundary — 22/10/2026

Document Workspace, Analytics Workspace và Subtitle Studio chỉ còn một lời giải
thích capability theo server thay cho cụm ô OCR/provider/payment/media lặp.
Không đổi API, engine, provider, payment hay delivery. Test riêng `1/1`, toàn
bộ Node `926/926`.

## Cập nhật Music/SFX boundary — 23/10/2026

Ba workspace authoring Music/SFX chỉ còn một lời giải thích capability thay cho
các ô provider/player/output/payment lặp; preset, brief, cue và form giữ nguyên.
Không mở generation/player. Test riêng `1/1`, toàn bộ Node `927/927`.

## Cập nhật Guard selector accuracy — 22/10/2026

Đã sửa selector route-scoped cho hai card DOM lồng và thay regex kiểm tra hời
hợt bằng kiểm tra block selector đầy đủ. Focused clarity `3/3`, full Node
`926/926`; không đổi workflow hay backend.

## Cập nhật Voice Vault endpoint audit — 23/10/2026

Web Voice Studio hiện có `22` endpoint owner-scoped cho danh sách/phân trang,
CRUD hồ sơ, archive/restore, duplicate, version restore, compose/script,
cue-sheet, events và direction composer. Preview audio/provider và apply/reuse
profile trực tiếp vào SubDub/Video vẫn mở vì chưa có contract canonical.

## Cập nhật Migration evidence — 22/10/2026

Web inventory/preflight đã cập nhật theo source hiện tại: `330` files; fingerprint
được đọc từ hai file generated trong `reports/migration`, verifier trả `ok: true`
cho exact HEAD tại lần refresh gần nhất. Không suy diễn từ đây sang deploy hoặc
LIVE.

## Đính chính 21/10/2026 — không đồng nhất thẻ/route với chức năng

Các kết luận checkpoint “presentation accepted” rộng được hạ lại mức smoke;
không đủ để đóng chức năng Bot→Web. Xem
`reports/audit/R218-EVIDENCE-RECLASSIFICATION-20261021.md`.
Music correction mới chỉ đóng giá hiển thị/receipt UI, actions và report của
luồng có dữ liệu, bằng test thực13/13 và browser18 cấu hình dùng locale hồ sơ
đúng. SubDub/Image/Video/utilities/Admin/AX/motion runtime còn phải nghiệm thu
từng thao tác, không chỉ tồn tại control. Không mở engine/wallet/auth/schema.

## Đối chiếu Voice idle expiry — 20/10/2026

| Yêu cầu | Hiện tại và bằng chứng |
|---|---|
| Quote hết hạn khi khách chưa thao tác | Timer dùng timestamp canonical; ẩn xác nhận cũ và hiện thông báo ngay trên form. Không remount shell hoặc tự lấy quote mới |
| Giữ công việc khách đang nhập | Browser fixture xác minh form node/focus/các field/âm lượng 0 và tệp STT/Thêm giọng còn nguyên; 22/22 cấu hình, console/overflow/write/request ngoài/unknown API đều 0 |
| Chuyển trang hoặc thay deadline | Test hành vi timer 8/8; focused 70/70, full Node 769/769. Timer bị hủy hoặc cập nhật theo dữ liệu mới |
| Parity vận hành với Bot | Chưa đóng: STT vẫn guarded ở integration; file fixture không chứng minh upload/engine; quote thật, generation, kho giọng và delivery còn theo T0/P1 |

Tài liệu trước chỉ ghi “quote expiry UI đã khóa” dựa trên thời điểm render.
Điều đó chưa chứng minh hết hạn lúc trang đứng yên. Lát này bổ sung đúng
evidence idle; CI sau push và LIVE vẫn được báo riêng trên PR #654.

## Đối chiếu Voice quote freshness — 20/10/2026

- Trước: renderer hiện input đã đổi cùng confirm của quote cũ; khi nhấn,
  integration mới phát hiện fingerprint khác. Sau: UI ẩn confirm và hiện
  thông báo lấy báo giá mới ngay khi đổi field, giữ focus/bản nháp.
- Source regression `11/11`, focused `77/77`, full Node `761/761`; browser
  TTS `18` cấu hình × `6` kiểu đổi input = `108` lượt đạt. File/consent chỉ
  được kiểm ở helper source. API fingerprint/receipt/quote/wallet không đổi.
- CI quote-edit tại `8d53dab` đạt run `39406730261`; idle UI được nghiệm thu
  ở mục trên. STT/clone runtime và audio/provider/delivery/LIVE có gate riêng.

## Đối chiếu Voice default — 20/10/2026

| Yêu cầu | Trạng thái đã xác minh |
|---|---|
| Giọng mặc định Nữ/Nam | UI bắt buộc chọn rõ `female`/`male`; nhãn VI/EN/ZH, giữ lựa chọn và lời thoại khi chuyển Kho giọng → TTS. Renderer 15/15, browser fixture 18/18 |
| Fallback một giọng hoặc trung tính theo capability | Vẫn mở. Projection readiness hiện không cung cấp danh sách giới tính; helper trước chỉ được kiểm bằng dữ liệu tổng hợp và đã bị bỏ |
| Tạo, nghe, tải và chuyển giọng qua sản phẩm | Các gate runtime/delivery và R218-02A còn mở; kết quả UI không thay cho bằng chứng vận hành thật |

Kết luận `[x] DEFAULT-GENDER-CAPABILITY` trước đây đã được sửa thành `[~]`
trong ledger R218. Nguồn backend chỉ được đọc để xác minh contract.

## Đối chiếu AD-03 — liên kết request → job → asset → report → audit (20/10/2026)

| Yêu cầu | Hiện tại trên WebApp | Trạng thái và bằng chứng |
|---|---|---|
| Admin xem đúng liên kết hồ sơ do máy chủ cấp | `admin_record_references` được chiếu có điều kiện ở record đơn và `items[]`; chỉ nhận 5 kind, tối đa 6 link/tập và 5 họ đường dẫn nội bộ | ⚠️ Source/local đã khóa projection; `tests/test_copyfast_bridge.py -k admin_record_references` `1 passed/56 deselected`; CI, record thật và LIVE còn mở |
| Không lộ liên kết cho customer/non-Admin | Trường bị bỏ hoàn toàn khi không có `allow_admin_user_refs`; payload sai kind/ID fail-closed, path ngoài allowlist thành rỗng | ✅ Contract local đạt; chưa có browser fixture role thật hoặc production RBAC |
| Chuỗi nghiệp vụ thật request → job → asset → report → audit | Chưa tự suy diễn hoặc tự tạo chuỗi; projection chỉ trình bày reference explicit từ server, không tạo job, charge, delivery hay audit decision | ❌ Chưa có bridge/record/runtime evidence; giữ mở trong AD-03 tổng |

Các con số trên được đo từ source/test hiện tại, không suy diễn từ HTTP 200 hay
HTML. `735/735` Node, `py_compile`, `node --check` và `git diff --check` là
evidence local; chưa phải CI, deployed, LIVE hoặc bằng chứng duyệt tiền.

## Đối chiếu Admin theme — 19/10/2026

- Cũ: controller luôn ép Light và xóa preference Admin; CSS áp light tokens
  cho cả selector dark; nút theme bị ẩn. Mới: giữ default Light, nhưng cho chọn
  Dark/System, lưu riêng và khôi phục sau reload; customer preference không đổi.
- Dark không đổi sang đen: dùng các `--portal-dark-*` navy/teal đã có; chỉ nhánh
  Admin. Light vẫn cùng canvas/thẻ, chỉ sửa AA pairs bằng sắc teal đậm sẵn có.
- Bằng chứng core: Node 17/17, browser home/login 24 cases, min text contrast
  7,61 dark/5,24 light; không mất email khi đổi theme, không HTTP write.
  Không dùng bằng chứng này để đóng mọi module/role/data/backend/LIVE.

## Đối chiếu Admin overview — 19/10/2026

- Yêu cầu phân quyền từng bộ phận: renderer nay lọc banner/lối tắt bằng
  `serverAuthorizesAdminRoute`, không coi người mở `/admin` được dùng mọi module.
- Tổng hàng đợi: không được suy ra từ số dòng của một trang; giá trị thiếu
  khác `0` thật. UI chỉ nhận aggregate số nguyên không âm do máy chủ trả.
- Báo cáo trước ghi Admin browser 72/72 chỉ là smoke nội dung/overflow/focus;
  probe cũ không đủ để kết luận role, locale, rail dọc hoặc dark mode hoàn chỉnh.
  Probe mới `--shortcuts` kiểm 108 trạng thái cho riêng banner/lối tắt/count;
  backend, approval, dữ liệu thật vẫn mở; core theme được kiểm riêng theo mục trên.

## Đối chiếu UT-01 — workspace Dịch (ứng viên cục bộ 18/10/2026)

| Yêu cầu trong inventory Bot | Hiện tại trên ứng viên Web | Trạng thái |
|---|---|---|
| Dịch text/voice/file, nguồn tự động, chọn đích và hai chiều | Workspace một cột có nguồn tự nhận diện, 21 ngôn ngữ đích, ô tìm kiếm, giữ bản gốc và dịch hai chiều ở lớp control-level | ⚠️ |
| Bắt đầu/dừng, kết quả và lịch sử | Có vùng trình bày trạng thái, kết quả rỗng và lịch sử rỗng; nút bắt đầu/dừng vẫn bị khóa nếu chưa có capability máy chủ | ⚠️ |
| Chạy dịch thật và giao tệp | Chưa có DTO/capability/provider/quote/job/output/delivery; không được suy diễn từ giao diện | ⚠️ |

Bằng chứng: `docs/superpowers/specs/2026-10-18-r218-06a-translation-workspace-controls.md`,
`tests/translation-workspace-controls.test.mjs` `4/4`, full Node `548/548`.
Luồng `/translate` và redirect companion cũ được giữ nguyên.

## Đối chiếu UT-04 — tiện ích miễn phí (ứng viên cục bộ 18/10/2026)

| Yêu cầu trong inventory Bot | Hiện tại trên ứng viên Web | Trạng thái |
|---|---|---|
| QR | VietQR giữ bank/account/name/amount/memo/template, preview, tải ảnh và sao chép liên kết cục bộ | ⚠️ |
| Avatar | Có phong cách, brief, xác nhận quyền sử dụng, preview rỗng và capability gate; chưa tạo ảnh | ⚠️ |
| Tỷ giá | Có USD/VNĐ/Xu, nguồn, thời gian, độ mới và nút làm mới guarded; chưa lấy nguồn thật | ⚠️ |
| Thời tiết | Có địa điểm, đơn vị C/F, result/empty copy và boundary loading/error/stale; chưa gọi API | ⚠️ |
| Downloader | Có nguồn, URL, xác nhận quyền, vùng kiểm tra và gate delivery; chưa kiểm tra/tải tệp | ⚠️ |

Bằng chứng: `docs/superpowers/specs/2026-10-18-r218-06b-utilities-qr-avatar-rate-weather-download.md`,
`tests/free-tools-hub-presentation.test.mjs` `5/5`, full Node `549/549`.
Không suy diễn control-level thành runtime parity hoặc LIVE.

## Đối chiếu Image — ứng viên cục bộ 08/10/2026

| Nguồn trước sửa | Candidate hiện tại | Bằng chứng |
|---|---|---|
| Workbench dùng alert thành công, giá -5 Xu và banner giả output 4K | Bỏ khối demo trước biểu mẫu thật; field/action/quyền server giữ nguyên | `tests/image-workbench-truth.test.mjs` |
| Trang tạo ảnh lẫn thuật ngữ và ngôn ngữ | Catalogue VI/EN/ZH cho form, báo giá, báo cáo, gợi ý và tracking | `tests/image-create-locale-presentation.test.mjs`; 48 trạng thái browser |
| Hub có 12 link/8 đích, ghi count 7 và hứa Lossless | 8 đích duy nhất, tạo ảnh trước, không claim chất lượng/ready từ route tồn tại | `tests/image-hub-locale-presentation.test.mjs`; 12 cấu hình hub |
| Report sau form, mobile nhiều cột, text/target thiếu chuẩn | Report trước khi có quote/confirm; form cũ thu gọn; fields dọc, màu semantic xanh–teal | I03 JSON/ảnh; chữ ≥5.944:1, target ≥45px, summary 48px |

BASE `dee0ac4ccaaf2cb3ebe147ab217e85ec419bec4c`; chưa push/deploy. Tài liệu
hoặc ảnh cũ nói Image đã sinh/download 4K, Lossless hay -5 Xu không còn đúng.
Đầu ra thật và quyền thực thi vẫn do server quyết định; checkpoint này chỉ
sửa hai màn hình trình bày. 12 lỗi ViewTransition còn mở trong scope motion.
PR #619 SubDub đã merge/đóng mã, CI đạt, chưa deploy; các đoạn checkpoint
SubDub cũ phía dưới là lịch sử trước khi merge.

## Đối chiếu SubDub một màn hình — ứng viên 08/10/2026

| Trước | Hiện tại trên ứng viên cục bộ | Bằng chứng / ranh giới |
|---|---|---|
| Mỗi chế độ mở lại `/subdub`; phụ đề, lồng tiếng và kết hợp gây cảm giác là các sản phẩm rời. | Bốn chế độ chọn ngay trên cùng màn hình; phần thiết lập đổi theo lựa chọn và giữ nguyên ngôn ngữ đã chọn. | `tests/subdub-hub-presentation.test.mjs`; 48 lần tương tác trên 12 cấu hình trình duyệt. |
| Chỉ có lựa chọn âm thanh gốc tổng quát; mức âm thanh giọng đọc không tách riêng. | Khi có lồng tiếng, có hai thanh mức âm lượng độc lập, chỉ cập nhật con số trên màn hình. | Không có dữ liệu gửi đi, lưu trữ, yêu cầu mạng hay thay đổi hợp đồng bộ máy xử lý. |
| Trạng thái “Preparing” và biểu tượng thành công có thể bị hiểu là đã có tác vụ. | Trạng thái chưa có báo cáo được nói rõ; tải tệp, báo giá, bắt đầu xử lý và đầu ra vẫn khóa. | Python contract 9/9; không kiểm thử phiên đăng nhập hoặc media thật. |
| Tiếng Trung rơi về tiếng Việt; một số nhãn/độ tương phản chưa đạt. | Nội dung tĩnh tiếng Việt/Anh/Trung, màu xanh–lam hiện có, bố cục dọc và vùng chạm được giữ. | 12/12 tổ hợp ba ngôn ngữ × sáng/tối × 1440/360; chữ ≥5.23:1, viền ≥3.61:1, mục tiêu chạm ≥44px. |

Mã giao diện đã kiểm thử `e4070e3bf6710be1e5388c12e20800aae0ee5ea3`, bằng chứng
trình duyệt `../../qa/qa/subdub-exact-e4070e3/browser-review.json`. Đây là
thay đổi trình bày; PR #619 đang mở nhưng lượt kiểm tra đầu dừng ở cổng dấu vân
tay hồ sơ di trú cũ. Chưa hợp nhất vào nhánh chính, triển khai hay kiểm tra trên
hệ thống thật. Các luồng
thực tế của SubDub vẫn thuộc phần xử lý nền. Không mở lại mã Voice,
Music hoặc Video đã được đánh dấu CLOSED/LOCKED.

## Đối chiếu Music — ứng viên 08/10/2026

- Cũ: ba lối tắt lặp lại danh mục, số liệu/chất lượng/bản quyền chưa có nguồn.
  Mới: 6 đường dẫn duy nhất, nhóm sáng tác trước/thư viện sau; bỏ các lời hứa đó.
- Cũ: Anh–Việt trộn trong phần chữ cố định. Mới: catalogue Music VI/EN/ZH
  theo locale; trạng thái chưa khả dụng rõ và không có trình phát/nhạc mẫu.
- Bằng chứng nguồn: `tests/music-hub-presentation.test.mjs` và spec
  `2026-10-08-music-hub-ui-closeout.md`. Đây là UI hub, không khẳng định ba
  tính năng sinh nhạc đã hoạt động. Shared-shell locale/motion vẫn mở riêng.

## Đối chiếu checkpoint Voice — 2026-10-08

| Hiện trạng nguồn trước sửa | Mã ứng viên hiện tại | Bằng chứng |
|---|---|---|
| Workbench TTS mô phỏng trong trang hồ sơ giọng | Bỏ workbench mô phỏng; giữ các thao tác hồ sơ/lời thoại hiện có | `tests/voice-planning-truth.test.mjs` |
| Nhãn danh mục, hồ sơ, phiên bản và cue sheet lẫn ngôn ngữ | VI/EN/ZH cho phần chữ cố định; dữ liệu người dùng/máy chủ giữ nguyên | 5 bộ renderer catalogue/studio/detail/composer/inventory |
| Mô tả preview có thể bị hiểu là đã có file nghe | Metadata readiness tách khỏi link phát/tải được xác minh | `tests/test_portal_safety_contracts.py::test_voice_output_preview_and_history_views_do_not_overclaim_unmapped_delivery` |
| Kết quả generic dùng thuật ngữ nội bộ và nằm sau biểu mẫu cũ | Kết quả Voice được bản địa hóa, đặt trước khi có báo giá/tracking | `tests/voice-flow-state-presentation.test.mjs` |
| Nút lưu bản mới có thể trống khi mở lại bản nháp | Khóa `voiceUi.draft.saveNew` và test bản nháp đã mở lại ở 3 ngôn ngữ | Cùng bộ flow-state; 110/110 renderer Voice đạt |
| Fallback `cost_xu` có thể làm mất/bị dùng thay báo giá công khai | Chỉ `estimated_xu`/`quote_xu`; chi phí nội bộ không thay giá bán | Test giá công khai + cost, cost-only, 0/unknown |

Đây là thay đổi trình bày. Chưa khẳng định TTS/clone/provider/audio thật đã chạy;
route/engine và thẩm quyền dữ liệu không nằm trong checkpoint này. Chỉ đánh dấu
release/live sau khi có CI, merge/deploy và browser readback tương ứng.

## Đối chiếu checkpoint Video — 2026-10-07

- Khung mẫu từng ghi “RTX 4090 VIDEO RENDER ENGINE SẴN SÀNG”, kịch bản mẫu và
  nút tuyên bố `-10 Xu`. Đây không phải bằng chứng xử lý thực; hai màn hình
  `/video/create` và `/video/multiscene` hiện dùng form và kết quả thật của máy chủ.
- Hub từng ghi 8 công cụ dù 10 điểm đến khác nhau và lặp 3 link; hiện đếm từ
  chính danh mục, mỗi điểm đến một lần.
- Các bước hướng dẫn giải thích thứ tự; việc nhìn thấy hướng dẫn không có nghĩa
  dịch vụ đã chạy hoặc kết quả đã được tạo. API/engine giữ nguyên main.
- Toàn bộ nhóm Video và motion chưa hoàn tất; bản sửa này chỉ khép ba route trên.

> Mục đích: đối chiếu yêu cầu nguồn với hành vi có bằng chứng ở source hiện tại.
> Trạng thái production/main: `cc3b4689f85d7c18ebb31b500b1eda1aca20cb6f`; manual top-up PR #420, `/admin/login` PR #421 và progressive disclosure PR #422 đã accepted live; A09 shell PR #423 và Support PR #424 đã deploy nhưng A09 toàn Admin còn mở. Production `MANUAL-1` vẫn pending và không được sửa/duyệt/cộng Xu.

## 1. Kết luận về tài liệu giai đoạn đầu

`INITIAL_FEATURE_DOC=NOT_FOUND`

Kết luận này chỉ áp dụng cho phạm vi tìm kiếm bounded dưới đây: không tìm thấy một tài liệu duy nhất là danh sách gốc đầy đủ cho toàn sản phẩm.
Nó không có nghĩa dự án thiếu tài liệu nguồn.
Các source contract, plan và matrix vẫn được dùng để đối chiếu từng yêu cầu.
Inventory kiểm soát phép đo: `reports/migration/p0-05-prepush-inventory.json`.
Inventory SHA-256: `b2f6549380826d2688fc648b46237acfe56d20d6512578dead00e3cd131cd7e3`.
Inventory đã được nghiệm thu tại P0-05B.

## 2. Phạm vi nguồn đã tìm

- `README.md` — runtime, configuration và authority boundary hiện tại.
- `docs/UX_APP_FIRST_REDESIGN.md` — product intent, guarded UI, navigation và PWA presentation boundary.
- `docs/migration/BOT_TO_WEB_INVENTORY.md` — snapshot command/callback/route/table ở thời điểm audit.
- `docs/migration/FEATURE_PARITY_MATRIX.md` — disposition tĩnh, không phải runtime equivalence.
- `docs/migration/README.md` — catalog contract migration.
- `docs/superpowers/plans/` — `123` tracked Markdown plan theo inventory P0-05B.
- `docs/superpowers/specs/` — `139` tracked Markdown spec theo inventory P0-05B.

## 3. Cách đọc trạng thái

- `✅`: hành vi/source contract hiện vẫn đúng trong source được chỉ ra.
- `⚠️`: hành vi đã có hoặc đã đổi nhưng còn local, guarded, chưa deploy/live hoặc khác tài liệu cũ.
- `❌`: source requirement không được dùng theo cách cũ; có boundary thay thế rõ ràng.
- Không dấu nào tự chứng minh production live.
- `COPIED_GUARDED` trong parity matrix không đồng nghĩa engine tương đương runtime.
- Matrix ghi runtime workflow-equivalence `0.0% NOT_STATICALLY_VERIFIABLE`; xem `docs/migration/FEATURE_PARITY_MATRIX.md:1-3`.

## 4. Bảng đối chiếu nguồn → hiện tại

| Yêu cầu/đoạn nguồn | Hành vi source hiện tại | Trạng thái | Bằng chứng |
|---|---|---|---|
| “signed workspace and operations application” | Web dùng signed session; integration fixture đăng ký/link/login các owner/Admin session thật. | ✅ Source đã deploy tại `9785541`; signed money flow chưa test. | `docs/UX_APP_FIRST_REDESIGN.md:5-12`; `tests/test_p0_manual_topup_cross_repo_integration.py:245-275` |
| Browser raw Telegram ID không phải auth | Telegram identity phải qua OIDC hoặc one-time Bot proof; Email/OAuth account không bắt buộc link ngay cho mọi Web-only surface. | ✅ Boundary hiện hành. | `docs/migration/TELEGRAM_WEB_CONNECTION.md:3-18`; `docs/migration/TELEGRAM_WEB_CONNECTION.md:31-39` |
| One-time link gắn cùng browser session | Link/account challenge dùng callback ký và CSRF; raw ID không được render thành quyền. | ✅ Source contract. | `docs/migration/TELEGRAM_WEB_CONNECTION.md:65-75`; `tests/test_p0_manual_topup_cross_repo_integration.py:245-275` |
| Bot là authority cho Xu/PayOS/provider/job | Web manual đã live độc lập cho metadata/QR/pending/history/Admin queue, nhưng Web vẫn không tự credit Xu hoặc tạo ledger thứ hai. Approve/ledger thuộc G0/G3 khóa riêng. | ✅ Manual source/QR/pending lane live tại PR #420; live money approve vẫn chưa test. | `copyfast_api.py`; `copyfast_db.py`; `tests/test_cust_web_manual_topup_visible_qr_001.py` |
| Bot manual callbacks là `TELEGRAM_ONLY` | Web không replay callback/UID/bill state; P0 thêm API signed-session riêng thay vì chuyển callback sang browser. | ⚠️ Cách triển khai Web-native mới, không phải callback parity. | `docs/migration/MANUAL_PAYMENT_CALLBACK_CONTRACT.md:3-11`; `copyfast_api.py:4689-4763` |
| Customer manual create/history/detail/status | Web có bốn route owner-scoped Web-local; không phụ thuộc Telegram/Core Bridge. | ✅ PR #420 deployed; một production QA pending được owner/Admin đọc khớp, không cộng Xu. | `copyfast_api.py`; `copyfast_db.py`; `tests/test_web_manual_topup_unlinked_g1.py` |
| Admin manual list/detail | Web-local Admin đọc pending request theo safe field allowlist; không cần canonical Bot bridge. | ✅ Production QA `MANUAL-1` đã đọc khớp customer/Admin; Admin decision chưa chạy. | `copyfast_api.py`; `tests/test_web_manual_topup_unlinked_g2.py` |
| Admin manual draft/confirm | G2 chỉ two-step reject; draft không mutate request/tiền, confirm reject atomic. Approve/custom Xu vẫn khóa G0/G3. | ⚠️ Candidate local; live money flow chưa chạy. | `copyfast_db.py`; `tests/test_web_manual_topup_unlinked_g2.py` |
| “No browser-supplied ... admin_id ... is trusted” | Forged query/body/header không thay canonical Admin ID từ session; denial không mutate ledger. | ⚠️ Đã kiểm temp-only, chưa live. | `README.md:238-244`; `tests/test_p0_manual_topup_cross_repo_integration.py:510-589` |
| Owner/Admin bearer phải tách | Owner bearer bị deny ở 4 Admin route; equal/missing Admin secret fail closed. | ⚠️ Đã kiểm temp-only; ENV production chưa rotate/configure. | `tests/test_p0_manual_topup_cross_repo_integration.py:597-637` |
| Confirm phải idempotent | Hai client confirm đồng thời chỉ tạo một canonical mutation; replay không double-credit. | ⚠️ Concurrency proof là 2 client trong fixture, không phải load benchmark. | `tests/test_p0_manual_topup_cross_repo_integration.py:481-505` |
| Safe owner/Admin projection | Owner output không lộ Admin/token/raw fields; Admin output theo allow-list; foreign owner nhận safe response. | ⚠️ Source/test local accepted. | `tests/test_p0_manual_topup_cross_repo_integration.py:380-420`; `tests/test_p0_manual_topup_cross_repo_integration.py:510-589` |
| Manual amount + payment code trên Web | Khách nhập amount; payment code là 8 chữ số bền vững của Web account, do signed server metadata cấp; browser/Telegram không override. | ✅ PR #420 live; production QA tạo đúng một pending `10000 VND`, không cộng Xu. | `copyfast_api.py`; `copyfast_db.py`; `tests/test_cust_web_manual_topup_visible_qr_001.py` |
| QR ACB/MoMo/ZaloPay/USDT trên Web | 5 QR canonical nằm ngoài repo public trong private Web root; signed endpoint full-decode/bomb/size/identity/cache guard. M03B chỉ render một QR sau explicit confirm; USDT/Binance configured visible-disabled vì chưa hỗ trợ đối soát VND. | ⚠️ Private asset/signed QR đã live qua PR #420; progressive disclosure M03B đang chờ ship. | `copyfast_api.py`; `static/portal/portal.js`; `tests/test_cust_web_manual_topup_visible_qr_001.py` |
| Hotline tách biệt số tài khoản | Support fallback `0898360858`; bank account fallback `0387532320`; Portal/integration không hardcode phone/account. | ✅ Source deployed; live source marker verified. | `billing.py`; `copyfast_api.py`; `tests/test_billing_canonical_journey_contracts.py` |
| Role-specific note confidentiality | Customer response và customer JS state bỏ `admin_note`; authorized Admin projection vẫn giữ note. | ⚠️ Security reviewer local kết luận fixed; live chưa kiểm. | `copyfast_api.py`; `static/portal/integration.js`; `tests/test_p0_manual_topup_customer_flow.py` |
| Manual interaction sống qua hydration | Selected lane và amount/method/reference còn nguyên sau same-route data remount; invalid lane bị bỏ qua. | ⚠️ Source deployed; Node/rendered matrix `10/10` đạt, signed production interaction chưa test. | `static/portal/portal.js`; `tests/test_p0_manual_topup_customer_flow.py`; `evidence/p0-05e-primary-manager-verified-20260830.md` |
| Manual progressive disclosure | Initial chỉ amount + method + confirm; explicit confirm mới hiện đúng một destination/QR/code, reference và CTA đối soát. Confirm local không POST và fail closed nếu thiếu canonical same-origin QR. Back/lane-switch purge instruction; account switch/logout purge toàn draft. | ✅ PR #422 accepted live tại main/runtime `d096bac…`; `5/5` enabled method, `9/9` locale-theme và `5/5` responsive. | `static/portal/portal.js`; `static/portal/portal.css`; `static/portal/integration.js`; `tests/test_cust_web_manual_topup_progressive_disclosure_002.py`; `reports/prepush/CUST-WEB-MANUAL-TOPUP-PROGRESSIVE-DISCLOSURE-002-RENDERED.json` |
| USDT/Binance trong selector VND | `usdt_trc20` hiện dưới tên `USDT TRC20 / Binance` nhưng disabled/readable với lý do “chưa hỗ trợ đối soát VND”; không confirm, không QR, không final submit và không tạo authority VND. | ✅ Negative-control và signed production read-only projection đạt trên runtime `d096bac…`. | `static/portal/portal.js`; `tests/test_cust_web_manual_topup_progressive_disclosure_002.py` |
| Admin navigation là server-authorized directory | Browser role/query không tạo module; unavailable endpoint phải fail closed. | ✅ Contract hiện hành, độc lập với P0 manual write. | `docs/migration/ADMIN_ERP_NAVIGATION_CONTRACT.md:3-30`; `docs/migration/ADMIN_ERP_NAVIGATION_CONTRACT.md:57-63` |
| Guarded capability không được trông như ready | Portal phải hiển thị guarded/unavailable; static navigation không phải runtime engine claim. | ✅ Product/UI boundary hiện hành. | `docs/UX_APP_FIRST_REDESIGN.md:5-12`; `docs/migration/FEATURE_PARITY_MATRIX.md:1-3` |
| PWA chỉ cache public shell | Wallet/payment/Admin/API/download/private workspace vẫn network-only và ownership-checked. | ✅ Cache boundary hiện hành. | `docs/migration/PWA_ROLLOUT_VERSIONING_CONTRACT.md:3-8`; `docs/migration/PWA_ROLLOUT_VERSIONING_CONTRACT.md:51-61` |
| Production runtime là VPS | Runtime truth là GitHub main → Actions → Ubuntu VPS; Railway không phải runtime production. | ✅ Runtime `b657cea…`, Web/nginx active, health valid. | `README.md:5-12` |
| Auth logo và low-height card | Logo không co/crop; card/form giữ trong initial viewport và control tối thiểu 44px. | ✅ Đã deploy/live tại `0dd8ffa`; local rendered `6/6` là receipt trước ship. | `evidence/auth-login-brand-viewport-001-20260831.md` |
| Admin login desktop/mobile responsive | Admin app-kind marker nới đúng ancestor main; `≥841px` hai cột, `≤840px` một cột; public login/register không nhận rule. | ✅ PR #421 merged/deployed và accepted live tại `b657cea…`; protected public Auth giữ nguyên. | `tests/test_admin_login_responsive_001_contracts.py`; `reports/prepush/ADMIN-LOGIN-RESPONSIVE-001.md` |

## 4.1 Chỗ tài liệu cũ vừa được sửa — Admin login

- Tài liệu trước đây chỉ có Auth hotfix tại SHA `0dd8ffa` và không mô tả lỗi `/admin/login` bị giữ trong main `560px`.
- Hiện tại production/main là `b657cea…`; `/admin/login` đã tách bằng marker server-derived mà không sửa Auth authority hay public `/login`/`/register`.
- PR/CI/merge/deploy/runtime/live đã được ghi riêng trước khi chuyển trạng thái sang accepted live; quy tắc này tiếp tục áp dụng cho M03B.

## 5. Chỗ tài liệu cũ không còn đúng

### 5.1 Manual payment cũ chỉ nói callback Telegram

`MANUAL_PAYMENT_CALLBACK_CONTRACT.md` đúng khi cấm replay callback vào browser.
P0-01..P0-04 không phá cấm đó; chúng tạo API private/signed riêng.
Vì vậy không dùng callback value, Telegram UID hoặc Bot deposit state làm browser action.
Tài liệu vận hành phải trỏ tới Web API/Bot internal route mới, không bảo khách nhập Telegram ID.

### 5.2 README chưa phản ánh P0 local source

README cũ từng nói Web không có manual-topup inbox và manual reconciliation vẫn qua `/thucong` tại `README.md:258-263`.
PR #420 đã đưa owner/Admin Web-local route, private QR và một pending QA lên production; tài liệu vận hành hiện phải dùng runtime `b657cea…` làm mốc.
M03B chỉ thay progressive disclosure/contrast/session cleanup ở client; trạng thái live hiện được chứng minh riêng qua PR #422, runtime `d096bac…` và signed read-only receipt, không suy từ local receipt.

### 5.3 Số đo audit cũ không dùng cho source hiện tại

`BOT_TO_WEB_INVENTORY.md` ghi FastAPI route Web `694` tại `docs/migration/BOT_TO_WEB_INVENTORY.md:3-10`.
P0-05B đo lại source accepted bằng AST là `702`.
Hai số có thời điểm/phương pháp khác nhau; tài liệu hiện tại dùng số P0-05B và giữ định nghĩa đo.
Không diễn giải chênh lệch số route thành phần trăm hoàn thành sản phẩm.

### 5.4 Railway compatibility không phải production truth

Một số tên ENV/file compatibility vẫn chứa chữ Railway.
Production runtime hiện tại là VPS theo `README.md:5-12`.
Không xóa compatibility metadata trong spec tài liệu này.
Không dùng sự tồn tại của `railway.json` để tuyên bố runtime đã quay lại Railway.

## 6. Rác và giới hạn

- Root repo còn các prototype/legacy entry như `db.py`, `customer_api.py`, `erp_core.py` và HTML cũ; không tự mount hoặc xóa trong P0 docs.
- Shared Portal bundle lớn là debt đã biết; tài liệu không biến debt đó thành refactor ngoài scope.
- Feature parity matrix là static disposition, không phải bằng chứng runtime output.
- Một Web route tồn tại không chứng minh provider/job/output giao thành công.
- Guarded route là trạng thái đúng khi adapter hoặc ENV chưa sẵn sàng.
- Production database record count chưa đo trong static gate.
- Credential-like tracked paths của Bot còn chặn ship và được tách thành P0-05A.
- P0-05B ban đầu chưa query GitHub Project; P0-05E sau đó đã gắn PR #417 vào `TOAN AAS Web App · Tester P0` và readback thành công.

## 7. Không có trong tài liệu gốc

- Không có một master feature list duy nhất; feature source nằm rải trong README, migration contracts, plans và specs.
- P0 manual owner bridge/API riêng được bổ sung sau callback-only inventory.
- P0 Admin two-step receipt/confirm và scoped bearer separation được bổ sung để Web không giữ Bot token ở browser.
- Cross-repo temp-only test kết nối actual Web app với actual Bot ASGI app là bằng chứng mới của P0-05.
- P0-05B static inventory chuẩn hóa source identities, route placeholders, hashes, docs và Tester workspace.
- Auth brand/low-height viewport hotfix là bổ sung sau tài liệu gốc; không thay authentication behavior.
- Customer motion live-reopen bổ sung vocabulary quan sát được `180/360/680ms`, scroll reveal/stagger bounded, hydration không replay và reduced-motion fail-visible. `/features` vẫn giữ bundle split riêng, không quay lại full Portal bundle.
- M03B bổ sung progressive disclosure cho lane manual: QR/code/destination không còn dựng trong initial DOM; confirm selection là local-only; reconciliation submit vẫn dùng integration/API/DB hiện có.
- P0 manual/Auth source đã qua Git/deploy. PR #420 đã có signed customer create/read + Admin read của đúng một pending production; approve/reject/cộng Xu vẫn chưa chạy. Customer motion đã `ACCEPTED_LIVE` trên runtime `b657cea…`.

## 8. Chưa triển khai hoặc chưa live

- P0-05A rotate/revoke và loại credential-like tracked paths: chưa làm.
- Tester source có WA-01..WA-47; WA-41..47 thuộc chuỗi A09 Auth/Admin shell và
  các route quản trị mở rộng.
- PR #420 manual và PR #421 Admin login đã merge/deploy; signed customer create/read và Admin list/detail của `MANUAL-1 pending_admin_review` đã smoke bằng account thật, không có decision/Xu/ledger mutation.
- Customer motion live-reopen v2 đã accepted live trên runtime `b657cea…`.
- M03B progressive disclosure đã `ACCEPTED_LIVE` trên runtime `d096bac…`; A09 shell và Admin Support đã ship tới `cc3b468…`, còn các route Admin khác đang làm tuần tự.
- ENV/secret rotation: chưa làm.
- Signed production manual route nền và M03B progressive presentation đã smoke; live approve/reject/money decision chưa test.
- Provider/PayOS/Telegram live call: không chạy trong local acceptance.
- Live money flow: `LIVE_PASS=NOT_TESTED` và `LIVE_MONEY_FLOW=NOT_TESTED`.
- Production record counts: `NOT_MEASURED`.

## 9. Hướng dẫn đọc nhanh

- Muốn biết source identity, routes, hashes và số đo: đọc `reports/migration/p0-05-prepush-inventory.json`.
- Muốn biết customer behavior: đọc `tests/test_p0_manual_topup_customer_flow.py` và `copyfast_api.py:4689-4763`.
- Muốn biết Admin behavior: đọc `tests/test_p0_manual_topup_admin_queue.py` và `copyfast_api.py:4550-4675`.
- Muốn biết Web↔Bot outcome/idempotency/security: đọc `tests/test_p0_manual_topup_cross_repo_integration.py:380-698`.
- Muốn biết callback Telegram nào vẫn Bot-only: đọc `docs/migration/MANUAL_PAYMENT_CALLBACK_CONTRACT.md`.
- Muốn biết PayOS/wallet authority: đọc `README.md:236-263` và `docs/migration/PAYOS_WALLET_JOB_MAP.md:1-20`.
- Muốn biết Admin navigation authority: đọc `docs/migration/ADMIN_ERP_NAVIGATION_CONTRACT.md`.
- Muốn biết PWA private-data boundary: đọc `docs/migration/PWA_ROLLOUT_VERSIONING_CONTRACT.md:51-61`.
- Muốn biết customer motion v2: đọc `evidence/motion-webapp-surfaces-live-reopen-v2-20260831.md` và matrix JSON cùng tên.
- Muốn biết trạng thái ship: đọc checklist P0-05; không suy từ một file route hay HTTP 200.

## 10. Chân lý báo cáo

- Code tồn tại không đồng nghĩa test pass.
- Test local pass không đồng nghĩa merged.
- Merged không đồng nghĩa deployed.
- Deployed không đồng nghĩa live outcome.
- HTTP 200 không đồng nghĩa quyết định tiền hợp lệ.
- Mọi claim provider/output/payment phải có bằng chứng output cuối tương ứng.
- P0 manual, Auth layout, Admin-login responsive, customer motion và M03B đã có runtime evidence tới `d096bac…`; không suy signed/money LIVE từ deploy. A09 chỉ được gọi live sau runtime SHA và signed production matrix.

## 11. Đối chiếu bổ sung A09 Auth/Admin shell

### Reliability candidate — 11/09/2026

### Admin Content Handoff candidate — 11/09/2026

Renderer staff cũ trộn Việt/Anh (`Customer Care`, `Role`, `Manager`, `write`,
`decision`, `publish`, `delivery`, `provider`, `payment`) và dùng màu label gần
như trắng trên light mode. Candidate chỉ thay presentation của
`/admin/content-handoffs`: catalogue VI/EN/ZH, task-first queue, một disclosure
quy trình, semantic contrast và responsive controls. Customer Handoff renderer,
API/schema, transition IDs và server authorization không đổi.

Local browser đo 20 trạng thái, contrast nhỏ nhất `7.26:1`; overflow/clipping/
touch/event/write request bằng `0`. Đây chưa phải deployed/live evidence.

### Admin Work Queue candidate — 12/09/2026

Renderer cũ của `/admin/work-queue` đặt phần giới thiệu nguồn trước bộ lọc và
việc, đồng thời trộn nhiều từ vận hành tiếng Anh vào bản Việt. Candidate giữ
nguyên read-model và server authority, chỉ thay presentation: catalogue
`adminWorkQueue.*` đối xứng VI/EN/ZH, task-first hierarchy, recovery gọn và
disclosure giới hạn đóng ban đầu.

Ở desktop, kết quả vẫn là bảng có route allow-list; ở `≤900px`, mỗi hàng là một
thẻ dọc có nhãn cột để không ép chữ. Source guarded/unavailable vẫn hiện `—`;
không thêm số liệu, tìm kiếm ID hay action ghi. Toast success/failure/permission
của bốn thao tác đọc được localize đầy đủ; partial source summary dùng câu trung
tính. Browser local đo `20` trạng thái, minimum contrast `7.62:1`,
overflow/clipping/framework overlay/console/write request `0`; tương tác attention
trả `3` dòng và disclosure mở/đóng đạt. Đây là local acceptance, chưa phải
deployed/live evidence.

### Admin CRM Leads candidate — 12/09/2026

Route cũ `/admin/crm/leads` phơi chuỗi `CRM Manager Directory`, `Server-redacted`,
`stage`, `lead`, `metadata`, `pipeline`, `owner`, `opportunity`, `notes` và
`cross-account`, đồng thời gọi biến chưa tồn tại `PARTNER_CRM_STAGES` khi có dữ
liệu. Candidate thay đúng presentation bằng catalogue `adminCrmManager.*`, sửa
allow-list stage sang `PARTNER_CRM_STAGE_LABELS`, tách loading/guarded, đưa bộ
lọc trước directory và chuyển hàng thành thẻ dọc trên màn hẹp. Manager DTO,
quyền Admin, API, schema, pagination và không-lộ-dữ-liệu vẫn giữ nguyên.

Browser local đo `20` trạng thái, minimum contrast `5.28:1`; overflow, clipping,
private leak, framework overlay, console và write request `0`; filter `review`
trả `1` hàng ẩn danh, disclosure mở/đóng đạt. Focused CRM/portal/backend suite
đạt `42 passed`, `1` cảnh báo Pydantic; chưa phải deployed/live evidence.

Renderer cũ ghép trực tiếp Việt/Anh, mô tả khởi động lại Railway, đặt giải thích
kỹ thuật trước hàng chờ và dùng khối trạng thái lồng nhiều lớp. Candidate hiện:

- dùng catalogue VI/EN/ZH cho toàn bộ fixed copy;
- đặt việc cần xử lý trước số liệu và tín hiệu;
- thu thông tin vận hành/quyền vào disclosure đóng ban đầu;
- dùng một status surface gọn cho disabled/unknown, không báo thiếu quyền khi
  core status chỉ cho biết module đang tắt;
- giữ nguyên action ID, capability, revision, cursor và API authorization.

Browser local đã đo `20` trạng thái enabled và `8` trạng thái disabled; các cổng
locale, responsive, clipping, touch, console và write request đều đạt. Đây là
local acceptance, chưa phải production/live. Bằng chứng:
`tests/test_a09_reliability_locale.py`, `tests/test_operations_reliability.py`,
`evidence/a09-admin-reliability-ux-20260911/browser*/`.

### Hiệu chỉnh Operations readiness — 10/09/2026

Thông báo cũ `Quyền điều hành chưa được cấp` được dùng cho mọi trạng thái không
ready, kể cả module tắt. Điều này không chứng minh tài khoản thiếu quyền.
Candidate hiện phân biệt chưa bật (cấu hình false được máy chủ trả thành công)
và chưa xác minh (lỗi/thiếu dữ liệu). Quyền và backend không đổi; không được
coi việc sửa thông báo là hoàn tất chức năng quản trị hoặc duyệt nạp.
Bằng chứng: `tests/test_operations_readiness_truth.py` và renderer VI/EN/ZH trong
`tests/test_a09_admin_operations_locale_purity_contracts.py`. Chưa live cho candidate.

| Chức năng/tuyên bố cũ | Hiện tại trong candidate A09 | Trạng thái | Bằng chứng |
|---|---|---|---|
| Admin app switcher nằm ngang để mở các nhóm | Toàn bộ nhóm server cấp nằm trong sidebar dọc; rail/header switcher bị bỏ. | ⚠️ Candidate local, chưa live | `static/portal/portal.js`; `tests/test_a09_auth_admin_shell_vertical_responsive_locale_contracts.py` |
| Sidebar chỉ chiếu nhóm hiện hành | Sidebar chiếu mọi nhóm server-permitted; chỉ nhóm hiện hành mở mặc định. Không cấp route mới từ browser. | ⚠️ Candidate local, chưa live | `adminDesktopNavGroups`; protected navigation comparator |
| Dashboard luôn có 5 KPI và 2 analytics panel | Chỉ nguồn count/readiness hợp lệ mới render; all-missing thành một empty state, explicit `0` vẫn là dữ liệu thật. | ⚠️ Candidate local, chưa live | focused data-truth tests; Browser 22/22 |
| Route shortlist là “Tác vụ cần xử lý” | Đổi thành “Truy cập nhanh”; task inbox thật vẫn source-missing và không được giả. | ⚠️ Candidate local, chưa live | `renderAdminWorkQueues`; server route intersection tests |
| Auth/Admin fixed chrome có thể trộn endonym/VI | Public Auth, Admin-login và theme fallback dùng catalogue VI/EN/ZH; Admin header dùng `Ngôn ngữ/Language`. | ⚠️ Candidate local, chưa live | locale keyset tests; 24 Auth Browser states |
| Logo Admin dùng kích thước/translate kế thừa | Admin override giữ ảnh chính thức contain, transform none, flex fixed; ratio đo `1.00`. | ⚠️ Candidate local, chưa live | CSS A09; 20 Admin Browser states |
| Admin Operations trộn câu Việt/Anh và dùng nền console cũ | Candidate `/admin/operations` dùng catalogue VI/EN/ZH, hierarchy teal/cyan sáng/tối, responsive một cột và empty state có chiều sâu; không thay authority/action backend. | ⚠️ Local verified, chưa commit/deploy/live | `tests/test_a09_admin_operations_locale_purity_contracts.py`; Browser `20` states, `14/14` assertions |
| Biên nhận đổi locale chỉ cập nhật một field bootstrap | Candidate đồng bộ `interfaceLocale` và đúng scalar `profile.locale`, giữ nguyên mọi field hồ sơ/phiên khác; remount không kéo về locale cũ. | ⚠️ Local verified, chưa deploy/live | `tests/test_portal_profile_locale_apply_contracts.py`; focused `151P` |

Chỗ tài liệu cũ không còn đúng: tài liệu/ảnh nào còn mô tả rail ngang, five-dash KPI, empty chart frames hoặc route shortlist như task inbox phải được xem là historical. Khung A09 và Admin Support đã deploy; từng route A09 tiếp theo vẫn phải có merge SHA, deploy run và signed production evidence riêng trước khi gọi live.

### Đính chính sau PR #423 và vòng locale mở lại

Khung A09 đã merge trong PR #423 tại `6298057…`; Admin Support đã merge trong PR #424 tại `cc3b468…`. Trạng thái “candidate chưa merge” phía trên là lịch sử trước các PR, không phải trạng thái hiện hành. Tuy nhiên, việc dịch thanh điều hướng hoặc một route không chứng minh toàn bộ phân hệ Admin đã thuần ngôn ngữ.

Admin Support đã ship với danh mục riêng cho danh sách/chi tiết, phân công, chuyển cấp và thông báo cố định; final focused `84` bài đạt và local Browser QA `40` trạng thái. Signed production DOM của Support vẫn chưa có, và các route Admin khác tiếp tục được xử lý tuần tự; không khẳng định toàn Admin đã hoàn thiện.

### Đối chiếu UI shell ngày 16/10/2026

Chức năng hướng dẫn cài ứng dụng vẫn giữ nguyên hành vi và điều kiện hiển thị; chỉ màu nền
modal được chuẩn hóa theo design system xanh navy/xanh ngọc. Source candidate có một
regression test riêng đạt `1/1`; không có thay đổi route, action, API hoặc output sản phẩm.
PR #647 vẫn cần delivery trước khi đối chiếu live.

### Đối chiếu locale Admin ngày 16/10/2026

Các thẻ cố định của khu vực Quản trị hệ thống đã có bản tiếng Việt riêng trong catalogue VI;
key và route giữ nguyên, catalogue EN/ZH không đổi. Kiểm thử source đạt `1/1`. Bằng chứng
runtime sau delivery vẫn thuộc ma trận QA và chưa được suy ra từ source.

### Bổ sung đối chiếu source ngày 16/10/2026 — không đổi chức năng

Đợt `SOURCE-LOCALE-12` chỉ chuẩn hóa fixed chrome của Trung tâm kiểm soát dữ liệu và
fallback renderer trên WebApp. Không thêm hoặc xóa chức năng gốc, không đổi route/API,
payload, quyền, trạng thái hay hành vi dữ liệu. Bằng chứng đo được: regression riêng
`2/2`, toàn bộ Node `480/480`, syntax hai tệp Portal đạt và `git diff --check` đạt.
Runtime/live chưa được suy ra từ source; mọi mô tả chức năng trong tài liệu gốc vẫn giữ
nguyên cho tới khi có bundle delivery và browser evidence mới.

### Bổ sung đối chiếu source ngày 16/10/2026 — Trung tâm hỗ trợ

Đợt `SOURCE-LOCALE-13` chỉ chuẩn hóa fixed chrome `supportTicket.*` và fallback renderer của
Trung tâm hỗ trợ. Catalogue VI có `295` mục; regression riêng đạt `2/2`, full Node đạt `482/482`
và giữ các contract
tạo yêu cầu, phản hồi, liên kết bằng chứng, mã yêu cầu và phiên bản. Không thêm/xóa chức năng
gốc, không đổi route/API, payload, quyền, trạng thái hay hành vi dữ liệu; runtime/live vẫn
chưa được suy ra từ source.

### Bổ sung đối chiếu source ngày 16/10/2026 — Hồ sơ tài khoản

Đợt `SOURCE-LOCALE-14` chỉ chuẩn hóa fixed chrome `accountCenter.profile.*` và fallback
renderer của `/account`, gồm hồ sơ, ảnh đại diện, phương thức đăng nhập, liên kết Telegram,
tùy chọn Bot, nâng cấp Email và Trung tâm bảo mật. Catalogue VI có `101` mục; regression
riêng đạt `2/2`, full Node đạt `484/484`, syntax Portal đạt và `git diff --check` đạt.
Không thêm/xóa chức năng gốc, không đổi route/API, payload, quyền, trạng thái hoặc hành vi
dữ liệu; các tên riêng/mã kỹ thuật được giữ theo allowlist. Runtime/live chưa được suy ra từ
source và product-lane scan vẫn là bước kế tiếp.

### Bổ sung đối chiếu source ngày 16/10/2026 — Image Studio/Image Hub

Đợt `SOURCE-LOCALE-15` chỉ chuẩn hóa fixed chrome Image Studio và Image Hub qua catalogue
`imageStudioUi.*` cân bằng VI/EN/ZH: guard, giới thiệu, số liệu, biểu mẫu bảng thiết kế,
ranh giới biên tập, ý định, định dạng, trạng thái và bộ lọc. Bản VI không còn generic English
UI; renderer giữ nguyên route, action, field, capability, CSRF, idempotency, revision,
dữ liệu động và trạng thái không tạo ảnh/không gọi nhà cung cấp/không trừ Xu. Regression
riêng đạt `2/2`, focused Image đạt `45/45`, full Node đạt `486/486`, syntax hai tệp Portal
và `git diff --check` đều đạt. Python contract `NOT_RUN` vì môi trường thiếu `python`/`py`;
runtime/live, AX tree và các cụm Image reference/detail/Resize/Enhance/Brand Overlay/
Storyboard vẫn mở.

### Bổ sung đối chiếu source ngày 16/10/2026 — Image library/Image Hub

Đợt `SOURCE-LOCALE-16` chỉ chuẩn hóa fixed chrome của thư viện tham chiếu, thư viện bảng
thiết kế, thẻ bảng thiết kế, tổng quan Image Hub, bước tiếp theo và bảng rà soát định hướng.
Catalogue `imageStudioLibraryUi.*` có `67` mục cân bằng VI/EN/ZH; helper locale phủ nhãn lọc,
placeholder, phân trang, trạng thái, lối tắt và empty state. Không đổi route, action, offset
phân trang, capability, dữ liệu động hoặc ranh giới chỉ đọc. Regression riêng đạt `2/2`,
focused Image đạt `49/49`, full Node đạt `488/488`, syntax hai tệp Portal và
`git diff --check` đều đạt. Python contract `NOT_RUN` vì thiếu `python`/`py`; runtime/live,
AX tree, chi tiết direction/estimate/history và các route Image còn lại vẫn mở.

### Bổ sung đối chiếu source ngày 16/10/2026 — Image detail

Đợt `SOURCE-LOCALE-17` chỉ chuẩn hóa fixed chrome chi tiết Image Studio/Hub: estimate,
direction card, trạng thái bảng thiết kế, lịch sử phiên bản, activity feed, tiện ích cục bộ
và các nút xác nhận/khôi phục/lưu trữ. Catalogue `imageStudioDetailUi.*` có `91` mục cân bằng
VI/EN/ZH; helper phủ các renderer `imageStudioEstimateMarkup`, `renderImageDirectionCard`,
`renderImageStudioDetail` và nhãn event. Không đổi route, action, field, capability, CSRF,
idempotency, revision, dữ liệu động hay ranh giới không tạo ảnh.

Regression riêng đạt `2/2`, focused Image đạt `51/51`, full Node đạt `490/490`, syntax hai
tệp Portal và `git diff --check` đều đạt. Python contract `NOT_RUN` vì môi trường thiếu
`python`/`py`; runtime/live, AX tree và các route Resize/Enhance/Brand Overlay/Storyboard
vẫn mở.

### Bổ sung đối chiếu source ngày 16/10/2026 — Image operations

Đợt `SOURCE-LOCALE-18` chuẩn hóa fixed chrome các route Image Resize, Image Enhance, Brand
Overlay và Storyboard Grid qua catalogue `imageOperationUi.*` cân bằng VI/EN/ZH. Picker
Asset Vault, phân trang, trạng thái guard/loading/failed, form/option, boundary, kết quả,
lịch sử và xác nhận export/bàn giao đều dùng helper locale; Brand Overlay không còn nhãn
`Owner-scoped` cố định và Storyboard không còn chuỗi `signed/private/source reference` trong
bản tiếng Việt. Không đổi route, action, field, capability, CSRF, idempotency, revision,
download path, ownership/integrity guard hoặc dữ liệu động.

Regression `tests/image-operation-locale-purity.test.mjs` đạt `3/3`; focused Image/media
đạt `54/54`; full Node đạt `493/493` (baseline `490/490`, `NEW_FAILURES=0`), syntax hai
tệp Portal và `git diff --check` đạt. Python contract `NOT_RUN` vì thiếu `python`/`py`;
browser/AX/live chưa chạy và không có provider call, wallet mutation, production data,
merge hay deploy trong batch.

### Đối chiếu source locale — Channel Strategy và Workboard — 16/10/2026

Channel Strategy hiện có catalogue giao diện cân bằng VI/EN/ZH và renderer dùng helper cho
list, filter, create, detail, preview, history, activity, field labels và aria text. Workboard
đã dùng locale key cho nhãn bảng Kanban và trạng thái guarded. Các hợp đồng route/action/field,
quyền, revision, CSRF và idempotency không đổi; nội dung do tài khoản nhập và dữ liệu máy chủ
không bị dịch trong trình duyệt.

Evidence source: Channel Strategy `2/2`, Workboard `4/4`, focused nhóm Content/Workboard/
Free/Memory/Project/Publish/Campaign `28/28`, full Node `496/496`, `NEW_FAILURES=0`. Browser,
AX, runtime/live và Python contract chưa chạy.

### Đối chiếu source locale — Music Prompt Composer — 16/10/2026

Music Prompt Composer hiện dùng catalogue `musicPromptComposerUi.*` cân bằng VI/EN/ZH cho
fixed chrome của trang lập kế hoạch, biểu mẫu, ranh giới, kết quả, ghi chú, biên nhận và phạm
vi. Dữ liệu mô tả và biên nhận từ máy chủ giữ nguyên; các field/action/route và ranh giới
không tạo âm thanh không đổi.

Evidence source: regression `2/2`, focused Channel/Workboard/Music `8/8`, full Node `498/498`,
`NEW_FAILURES=0`. Browser, AX, runtime/live và Python contract chưa chạy.

### Đối chiếu source locale — Music Direction Presets — 16/10/2026

Music Direction Presets dùng catalogue `musicDirectionUi.*` cân bằng VI/EN/ZH cho preset card,
biểu mẫu, biên nhận, boundary, checklist và scope. ID preset và dữ liệu brief/receipt vẫn là
giá trị canonical; route/action/field/capability/CSRF/idempotency không đổi.

Evidence source: regression `2/2`, focused Composer/Direction/Voice/Media `31/31`; Browser,
AX, runtime/live và Python contract chưa chạy.

### Đối chiếu source locale — SFX Cue Sheet — 16/10/2026

SFX Cue Sheet dùng catalogue `sfxCueSheetUi.*` cân bằng VI/EN/ZH cho fixed chrome của preset,
form, placement, receipt, cue list, cảnh báo, boundary và scope. ID preset/cue/placement,
route/action/field/capability/CSRF/idempotency và dữ liệu receipt canonical không đổi.

Evidence source: regression `2/2`, focused Composer/Direction/SFX/Voice/Media `33/33`, full
Node `502/502`, `NEW_FAILURES=0`; Browser, AX, runtime/live và Python contract chưa chạy.
## Đối chiếu bổ sung — SOURCE-ADMIN-05 Customer 360 — 17/10/2026

| Chức năng hiện tại | Trạng thái | Bằng chứng đo được |
|---|---|---|
| Customer 360 fixed chrome VI/EN/ZH | ✅ | Catalogue `adminCustomer360.*` có cùng bộ khóa ở `3/3` locale; regression `3/3` |
| Safety modal khóa/mở khóa | ✅ | Nút và cảnh báo dùng helper locale; `admin-customer-*` action giữ nguyên; comparator action `771→771` |
| Dữ liệu động, ví/Xu, ledger và quyền | ⚠️ | Không thay đổi trong batch; Python Customer 360 contract chưa chạy vì thiếu `py`/`pytest`; runtime fixture vẫn mở |
| Duyệt nạp thủ công/cộng Xu thật | ⚠️ | Không thuộc batch; vẫn `DEFERRED`, không có wallet mutation |

Tài liệu gốc không có mục riêng cho catalogue Customer 360; vì vậy đây là phần bổ sung của
WebApp standalone, không được suy diễn thành chức năng Bot/Core Bridge hoặc quyền tài chính.

Kết thúc đối chiếu `SOURCE-ADMIN-05`.

## Đối chiếu bổ sung — SOURCE-IMAGE-01 — 17/10/2026

| Chức năng/trạng thái | Hiện tại trong candidate WebApp | Bằng chứng / giới hạn |
|---|---|---|
| Lối vào tạo và chỉnh ảnh trên `/image/create` | Có hai lựa chọn dọc; tạo ảnh là trang hiện tại, mục chỉnh mở `/image/edit` và mô tả đúng công cụ tăng chất lượng đang có. | `static/portal/portal.js`; `tests/image-create-locale-presentation.test.mjs` |
| Fixed chrome VI/EN/ZH | Có catalogue đủ ba ngôn ngữ cho tiêu đề, liên kết, mô tả và nhãn truy cập. | Regression Image source `40/40`; mỗi tệp locale Node chạy một lần `319/319`; full Node `521/521`. |
| Chỉnh sửa ảnh bằng AI | Source có lane `/image/transform` và alias `/image/image-to-image`, cùng bridge và API riêng; source runtime matrix ghi `BLOCKED_PROVIDER_ENTITLEMENT`, chưa xác nhận entitlement live. | `copyfast_image_transform_job_bridge.py`; `copyfast_image_transform_runtime_bridge.py`; `tests/test_r10_runtime_matrix_contracts.py`; provider dispatch vẫn khóa. Không bật quyền/nhà cung cấp trong batch UI. |
| Nâng độ phân giải bằng AI | Source có lane `/image/upscale` và bridge/API riêng; source runtime matrix cũng ghi `BLOCKED_PROVIDER_ENTITLEMENT`. | `copyfast_image_upscale_job_bridge.py`; `tests/test_r10_runtime_matrix_contracts.py`; đây không phải bằng chứng đầu ra live. |
| Trường ảnh tham chiếu trong luồng tạo | `/image/create` có API/job flow nhưng form contract hiện không nhận `reference`; Image Transform nhận asset đã có trong Asset Vault theo quyền sở hữu. | `tests/test_portal_safety_contracts.py::test_translation_upload_and_image_create_forms_match_the_frozen_bot_contract`; `copyfast_image_transform_job_bridge.py`. Không tự thêm field/upload nếu thiếu contract. |
| Trạng thái giao nhận | Source candidate thuộc PR #647; việc có PR không đồng nghĩa đã merge/deploy/live. | Browser DOM/AX/runtime chưa đo; source pass không đóng R217-04. Đối chiếu head/CI theo trang PR hiện hành. |

Nguồn yêu cầu giai đoạn xây dựng chưa có một danh mục gốc duy nhất theo bounded inventory
đã nêu ở các mục trên; vì vậy đối chiếu này ghi bổ sung hành vi của WebApp standalone,
không tuyên bố tương đương runtime với Bot. Việc hợp nhất workspace, upload/reference,
variants, preview/history và giao nhận ảnh thật vẫn mở trong R217-04. Hai lane AI có
server-side bridge nhưng đang bị chặn theo source matrix; trạng thái entitlement production
chưa được kiểm tra trong lượt này.

## Đối chiếu bổ sung — SOURCE-VOICE-01/02 — 17/10/2026

| Chức năng/trạng thái | Hiện tại trong candidate WebApp | Bằng chứng / giới hạn |
|---|---|---|
| Chọn cách làm Voice | Voice Studio có đúng `3` lane dọc: mặc định, đã lưu và thêm giọng; lần lượt mở `/voice/tts`, `/voice/saved`, `/voice/clone`. | `static/portal/portal.js`; `tests/voice-studio-locale-presentation.test.mjs`; Voice batch `126/126` |
| Locale Voice Studio | Fixed chrome của lane mới dùng cùng catalogue `customerVoiceStudio` ở `3/3` locale VI/EN/ZH; tên hồ sơ và dữ liệu máy chủ không bị dịch. | `static/portal/portal-i18n.js`; regression locale Voice |
| Màu và responsive | Voice Studio/Voice Vault dùng xanh dương–xanh ngọc/nền xanh navy; rail xếp `1` cột ở `max-width: 820px`; focus ring và hover được giữ. | `static/portal/portal.css`; `node --check` `2/2`; không có browser/live evidence trong batch |
| TTS/Voice Library/clone/preview/output thật | Chưa đóng; lane chỉ mở đúng route và giữ nhãn được bảo vệ, không dựng tệp hay trạng thái hoàn tất. | Runtime/bridge/provider/Voice Library handoff chưa được xác minh; tiếp tục mở R217-05 runtime |

Batch này chỉ đóng phần trình bày UI/UX của Voice. Không được gọi đây là parity runtime với Bot,
không đổi ví/Xu, quyền, route/action/field/capability hoặc dữ liệu production.

## Đối chiếu bổ sung — SOURCE-MUSIC-01/02 — 17/10/2026

| Chức năng/trạng thái | Hiện tại trong candidate WebApp | Bằng chứng / giới hạn |
|---|---|---|
| Chọn hướng làm nhạc | `/music` có journey ba bước và đặt hai hướng chính (nhạc nền, bài hát có lời) trước nhánh SFX; mỗi card vẫn mở route hiện hữu. | `static/portal/portal.js`; `tests/music-hub-presentation.test.mjs`; Music hub route set `6` |
| Locale Music hub | Fixed chrome dùng catalogue `musicHub.*` ở `3/3` locale VI/EN/ZH; nhãn hướng, trạng thái và journey không trộn ngôn ngữ trong bản VI. | `static/portal/portal-i18n.js`; focused Music hub/library `16/16` |
| Bố cục và khả năng đọc | Card chính có role/mode metadata và `aria-describedby`; desktop tối đa `2` cột, mobile `1` cột từ `820px`; màu dùng token xanh/navy chung. | `static/portal/portal-theme.css`; `node --check` `2/2`; chưa có browser screenshot/AX runtime |
| Tạo/preview/export nhạc thật | Chưa đóng; hub chỉ trình bày route và boundary đúng, không dựng tệp hoặc receipt hoàn tất. | Provider/adapter và browser/runtime output chưa được xác minh; tiếp tục mở R217-06 runtime |

Batch này chỉ đóng source presentation của Music hub. Không được gọi đây là parity runtime với Bot,
không đổi ví/Xu, route/action/field/capability hoặc dữ liệu production.

## Đối chiếu bổ sung — SOURCE-SUBDUB-01/02 — 17/10/2026

| Chức năng/trạng thái | Hiện tại trong candidate WebApp | Bằng chứng / giới hạn |
|---|---|---|
| Bốn hướng trong một màn hình | `/subdub` giữ phụ đề gốc, dịch phụ đề, lồng tiếng và phụ đề + lồng tiếng trong cùng tab; đổi mode không mở route mới. | `static/portal/portal.js`; `tests/subdub-hub-presentation.test.mjs` `11/11` |
| Smart Multi và âm lượng | Có lựa chọn tự động/một/hai/nhiều giọng, mapping guarded, volume âm thanh gốc/giọng riêng và ISO language input. | Source presentation; không chứng minh auto-detect, mapping hay output thật |
| Voice Library handoff | Hai panel lồng tiếng có link `Mở Thư viện giọng` tới `/voice-studio`; selector vẫn disabled/guarded. | `data-subdub-voice-library-link` `2` lần; chưa có Voice profile projection runtime |
| Báo cáo và giao tệp | Khu báo cáo rỗng nói rõ chưa có tác vụ; CTA tạo bị guarded. | Không upload, job, provider, wallet hoặc artifact; runtime/QA còn mở |

Batch này chỉ đóng source presentation của SubDub. Không được gọi đây là parity runtime với Bot,
không đổi engine, route/action/field/capability, ví/Xu hoặc dữ liệu production.

## Đối chiếu bổ sung — SOURCE-VIDEO-01/04 — 17/10/2026

| Chức năng/trạng thái | Hiện tại trong candidate WebApp | Bằng chứng / giới hạn |
|---|---|---|
| Phân loại Product Video | `/tools/video` chia `10` route duy nhất thành `4` lane: lập kế hoạch, tạo video, biên tập/ghép và kiểm tra/bàn giao; mỗi lane nêu đầu vào/đầu ra. CTA chính được đánh dấu tường minh trên `/video/finishing`; hai lối lập kế hoạch/tạo video vẫn là CTA phụ. | `static/portal/portal.js`; `tests/video-uiux-locale-presentation.test.mjs` `11/11`; full Node `523/523`; CI `39018249838` kiểm `6/6` hub và `18` screenshot |
| Quy trình bảy bước | Hub hiển thị nhập → lập kế hoạch → xem báo giá → xác nhận → theo dõi xử lý → nhận kết quả → khôi phục; form tạo và đa cảnh giữ cùng contract. | `data-video-step` cho đủ `7` bước; không đổi route/action/field |
| Ranh giới AI/thủ công | Có panel riêng cho nhánh AI và nhánh thủ công, đều ghi rõ trạng thái được bảo vệ để không nhầm kế hoạch với video đã tạo. | `data-video-editor-mode="ai"` và `"manual"`; chưa có runtime render/timeline thật |
| Locale và bố cục | Fixed chrome có đủ VI/EN/ZH; lane dùng thẻ dọc, đầu vào/đầu ra và badge trạng thái; mobile chuyển về một cột. | `static/portal/portal-i18n.js`, `static/portal/portal.css`; chưa có browser screenshot/AX runtime |
| Upload, render, MP4, preview và download thật | Chưa đóng; các lane chưa sẵn sàng vẫn guarded và không tự tạo job, provider output hoặc tệp giả. | Provider/worker/runtime/real artifact evidence chưa có; tiếp tục mở R217-08 runtime |

Batch này chỉ đóng source presentation của Product Video. Không được gọi đây là parity runtime
với Bot, không đổi engine, route/action/field/capability, ví/Xu hoặc dữ liệu production.

## Đối chiếu Bot → WebApp — R218 SubDub voice lanes — 18/10/2026

| Chức năng Bot tham chiếu | WebApp hiện tại | Bằng chứng / giới hạn |
|---|---|---|
| Bốn lane: phụ đề gốc, phụ đề dịch, lồng tiếng, combo | Một workspace `/subdub` giữ bốn tab và đổi panel tại chỗ | `tests/subdub-hub-presentation.test.mjs` `14/14` |
| Giọng mặc định nam/nữ | Đã hiển thị thành hai lane riêng, trạng thái guarded | `static/portal/portal.js`; chưa có bridge giọng thật |
| Giọng đã lưu và giọng tự thêm | Đã có lane, Voice Library link và lý do guarded | Chưa có projection `voice_profile_id` từ server |
| Auto 2 và Auto Multi 3–8 | Đã tách thành hai lane canonical `auto_two` và `auto_multi_3_8`; speaker-map panel chờ runtime data | Chưa chạy callback thật, không ép số người nói |
| Smart Multi | Đã có lane `smart_multi` riêng và callback `auto_smart_multivoice` guarded | Chưa có speaker detection, mapping override hoặc artifact |
| Nguồn phụ đề và ngôn ngữ | Đã có lựa chọn “đã có/chưa có phụ đề”, tự nhận diện nguồn, catalog target đầy đủ với Việt đứng trước; nhãn được cân bằng VI/EN/ZH | Upload/preview/search/runtime language capability chưa có bằng chứng |
| Vị trí phụ đề | Đã hiển thị đủ 7 vị trí trong các mode có phụ đề | Chưa áp dụng vào artifact thật khi execution chưa mở |
| Báo giá, xác nhận, tiến trình, artifact, receipt | Stage 3/4 vẫn guarded/empty | Không tạo job hoặc output giả; R217-07D/E còn mở |

Tài liệu gốc của Bot mô tả nhiều hơn UI Web hiện tại ở phần speaker mapping, artifact QC,
delivery receipt và charge sau delivery. R218 giữ các phần đó trong wave runtime riêng, không
đánh dấu PASS từ source presentation.

## Đối chiếu bổ sung — SOURCE-CONTENT-01/03 — 17/10/2026

| Chức năng/trạng thái | Hiện tại trong candidate WebApp | Bằng chứng / giới hạn |
|---|---|---|
| Content/Workboard/Projects | Các board/list/detail có lối vào, create/edit/save/archive/restore/version/history theo contract hiện hữu; Workboard có bố cục dọc cho mobile. | Focused source set `26/26`; không đổi action, revision hoặc server data |
| Campaign/Calendar/Approval/Publish | Fixed chrome có mốc, agenda, review, reminder, trạng thái guard và handoff; bản nháp không bị gọi là output. | `static/portal/portal.js`, catalogue VI/EN/ZH; browser/runtime chưa đo |
| Free Tools/Prompt Gallery/Memory | Có tab/filter/group/copy/save và tách fixed chrome khỏi prompt/owner data. | Source regression `26/26`; ghi thật, persistence và bridge vẫn mở |

Batch này chỉ đóng source presentation của R217-09A. Không được gọi đây là parity runtime với
Bot, không đổi engine, route/action/field/capability, ví/Xu hoặc dữ liệu production.

## Đối chiếu bổ sung — SOURCE-ADMIN-11 — 17/10/2026

| Chức năng/trạng thái | Hiện tại trong candidate WebApp | Bằng chứng / giới hạn |
|---|---|---|
| Admin fixed chrome và điều hướng | Các khu vực Customer 360, Provider, nạp thủ công, finance/domain center, stewardship và mobile data dùng catalogue/khung dọc đã rà soát. | `tests/admin-*.test.mjs` `21/21`; không đổi route/action/permission server |
| Locale và mobile | Nhãn cố định cân bằng VI/EN/ZH; module tabs có target chạm và bảng mobile có harmony source. | Full Node `522/522`; browser AX/overflow runtime chưa có |
| Quyền và tác vụ khách | UI giữ boundary theo manifest/capability và trạng thái guarded; chưa chứng minh role enforcement hoặc liên kết request/job/asset/report/audit thật. | Canonical-admin fixture, Python contract và browser runtime đang `OPEN/BLOCKED` |
| Duyệt nạp thủ công | Có amount/method/reference/status/approve/reject/reason ở lớp trình bày; ledger/Xu mutation vẫn `DEFERRED`. | Không gọi PayOS/provider, không ghi ví hoặc dữ liệu production |

Batch này chỉ đóng source recheck Admin. Không được gọi đây là parity runtime với Bot hoặc
duyệt tiền thật.

## Đối chiếu bổ sung — R217-12 auth locale return — 17/10/2026

| Chức năng gốc / hiện tại | Đối chiếu candidate WebApp | Bằng chứng / giới hạn |
|---|---|---|
| Route được bảo vệ giữ ngôn ngữ đã chọn khi yêu cầu đăng nhập | `/features?lang=vi|en|zh` nay tạo return target có đúng `lang` và mở `/login` cùng locale; client chỉ nhận một tham số `lang` đã allowlist. | `app.py`, `static/portal/portal-auth.js`, `static/portal/integration.js`; focused `17/17`, full Node `525/525` |
| An toàn return path | Query ngoài `lang`, fragment, backslash, đường dẫn ngoài và auth-loop bị fail-closed; không đổi route/action/field hoặc quyền. | `node --check`, `py_compile`, `git diff --check`; chưa có live/CI sau candidate |
| Trạng thái giao nhận | Candidate commit `0ad78e5` đã khóa source nhưng chưa phải merge/deploy/live. | Cần CI và read-only production recheck trước khi đánh dấu ✅ runtime |

## R218 — Sửa lại cách đối chiếu Bot → Web — 18/10/2026

| Nguồn | Kết luận phải dùng khi lập kế hoạch |
|---|---|
| Voice menu/handlers | Có TTS/STT/default/Vault/clone/preview/speed/volume và reuse; Web cần đủ controls, không chỉ 3 launcher |
| Music menu 3-tier | Nền/song/SFX/library có luồng; editor vẫn guard, 2 output chưa có delivery proof; duration legacy cần xác minh reachable |
| SubDub keyboard | Default/saved/custom + Auto2/Multi3–8/Smart Multi riêng; volume dub 0–200, vị trí subtitle và original/translated source |
| Video profile catalog | 32 profile planning thay danh mục legacy 12, không tương đương 32 engine |
| Video AI Edit catalog | 39 options/5 nhóm, production readiness riêng; toolbar không là CapCut parity |
| Docs shared-master V2 | DESIGN; không coi là runtime authority khi chưa kiểm code/path thật |
| Các menu còn lại | Free/Dịch/Content/Memory/Docs/AutoPost/Support/Account/Admin đều có inventory và spec R218; không bỏ qua |

Chi tiết nguồn: reports/audit/WEBAPP-BOT-PRODUCT-INVENTORY-R218.md.
Lịch sử source PASS phía trên chỉ có giá trị đúng scope/HEAD/ngày đã ghi;
không tự nâng thành hoàn tất toàn bộ sản phẩm hay deployment hiện tại.

## R218 — Đối chiếu hiện tại sau CI run 39101124230 — 18/10/2026

| Phạm vi | Hiện trạng có bằng chứng | Chưa được suy diễn |
|---|---|---|
| SubDub voice lanes | HEAD `148be4f6ec18e3c7fe3abfee8ca8a34ee1a5d099`; 13/13 test mục tiêu; CI Verify Web App và Authenticated QA xanh; 456/456 route/render case | Không chứng minh Voice Vault projection, speaker detection, upload, quote, job, output hay delivery |
| Các nhóm Voice/Music/Image/Video/Utilities/AutoPost/Admin | Inventory B01–B34, plan/checklist/spec R218 đã ghi đủ control cần đối chiếu theo bảng Bot | Chưa có control-level/browser evidence cho từng nhóm; mục chưa có evidence vẫn mở `[ ]`/`[~]` trong checklist |
| Runtime và production | Không gọi provider, không đổi ví/Xu, không sửa dữ liệu production | `MERGED != DEPLOYED != LIVE`; live pass vẫn `NOT_TESTED` |

Nguồn completion ledger duy nhất của đợt này là
`reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-R218.md`; không đánh dấu hoàn tất
chỉ vì route trả HTML hoặc CI render xanh.
## R218 — Voice control contract sau candidate 814b70c — 18/10/2026

| Control | Hiện trạng đã khóa | Bằng chứng | Còn mở |
|---|---|---|---|
| Tốc độ đọc | `speed` số `0,1–2,0`, mặc định `1,0`, preset Chậm/Chuẩn/Nhanh; `/voice/tts` và `/voice/saved` dùng cùng field | `tests/voice-controls-contract.test.mjs` `3/3`; Voice regression `97/97` | quote stale, runtime/CI/live |
| Âm lượng | `volume_percent` số `0–200` + slider đồng bộ, chỉ một field gửi FormData | cùng test `3/3`; full Node `530/530` | cảnh báo mức `0`, output/runtime |
| Bản địa hóa | label/help/preset dùng catalogue VI/EN/ZH; dữ liệu gửi giữ giá trị số | `portal.js`, catalogue `field.*`/`option.speed.*` | browser screenshot/AX sau deploy |

Candidate này chỉ đóng control-level UI/UX, không tuyên bố TTS/STT/Voice Vault/provider/output đã hoạt động thật.

## Đối chiếu Music product workspace — R218 — 18/10/2026

| Chức năng cần đối chiếu | Trạng thái candidate WebApp | Bằng chứng / giới hạn |
|---|---|---|
| Nhạc nền và bài hát có lời trên hai route rõ ràng | Đã có `/music/create` và `/music/song`, cùng workspace dọc 4 bước; route nền không lộ field bài hát | `static/portal/portal.js`; `tests/music-product-controls.test.mjs` |
| Gói chất lượng và ba phương án | Có 3 tier và 3 ô phương án ở trạng thái guarded, không tự gán giá hoặc audio | Music control `7/7`; không có quote/provider/output thật |
| Lời, kiểu giọng, thời lượng | Route bài hát giữ `lyrics`, `vocal_mode` (tự động/nam/nữ/song ca), `song_length_mode` (giây/nửa/đầy đủ) và `duration_seconds`; đổi sang giai điệu khóa field lời/giọng | `musicProductFields()` + synchronizer; server capability chưa chứng minh |
| Locale và giao diện | Catalogue fixed chrome cân bằng `vi/en/zh`; card dọc, light/dark dùng token xanh/ngọc, không thêm motion | `static/portal/portal-i18n.js`, `static/portal/portal-theme.css`; chưa có screenshot/AX/live |
| Player/tải/lưu/dùng lại/chỉnh nhạc/giao tệp | Chưa mở; không còn UI giả để thay thế capability thật | Checklist MU-04..MU-12 còn `[ ]/[!]`; provider, asset delivery và runtime chưa chạy |

Kết luận: batch này khóa **control-level UI/UX và ranh giới guarded**, không được gọi là
Music parity runtime với Bot hoặc là tệp đã tạo. Các mục quote, confirm, generation, editor,
player/download/save/reuse, hai bản giao tệp và browser/CI/live tiếp tục theo thứ tự R218.

## Đối chiếu AutoPost Hub — R218 — 18/10/2026

| Chức năng cần đối chiếu | Hiện tại trên WebApp | Bằng chứng / giới hạn |
|---|---|---|
| Bảy nguồn nội dung | Có các nguồn chủ đề/ý tưởng, liên kết tham khảo, Affiliate, tệp đa phương tiện, video, ảnh và kế hoạch/bản nháp | `static/portal/portal.js`; `tests/autopost-hub-product-controls.test.mjs` |
| Trình tự thao tác | Một workspace dọc có 5 bước: nguồn, kế hoạch/thương hiệu, kênh, lịch/hàng đợi, báo cáo/lịch sử | Test AutoPost `4/4`; chưa có execution runtime |
| Kênh, lịch, hàng đợi, Affiliate | Có lane trình bày và trạng thái guarded; không tự tạo lịch, bài đăng, số liệu hoặc biên nhận | Không có OAuth, publish receipt, queue receipt hay metrics thật |
| Locale và responsive | Bộ khóa VI/EN/ZH cân bằng; bố cục giữ palette xanh/ngọc và xếp một cột trên màn hình hẹp | Full Node `562/562`, syntax và `git diff --check` đạt; browser/AX/live chưa đo |

Kết luận: AutoPost mới đóng control-level UI/UX và boundary trung thực. AP-01..05 vẫn giữ
`[~]` trong completion ledger cho tới khi có capability máy chủ, browser/AX, queue/history
receipt và delivery evidence riêng.

## Đối chiếu Trung tâm hỗ trợ khách hàng — R218-07B — 18/10/2026

| Chức năng cần đối chiếu | Hiện tại trên WebApp | Bằng chứng / giới hạn |
|---|---|---|
| Tiếp nhận và danh sách yêu cầu | Có form tiếp nhận, lọc nhóm/trạng thái, phân trang, số liệu theo trạng thái và các trạng thái rỗng/đang tải/lỗi/bảo vệ | `static/portal/portal.js`; `tests/support-hub-product-controls.test.mjs` |
| Chi tiết và phản hồi | Có mã yêu cầu, revision, dòng thời gian, phản hồi khách hàng, đóng/mở lại và recovery theo trạng thái | Control-level `4/4`; chưa có signed browser evidence |
| Bằng chứng riêng tư | Chỉ chọn tệp đã có trong Asset Vault, xác nhận đã che thông tin, giới hạn loại/kích thước và liên kết theo revision; không upload bytes tại Trung tâm hỗ trợ | Helper `renderSupportEvidence`; capability/delivery server vẫn mở |
| Quản trị | Có phản hồi công khai/nội bộ tách riêng, cập nhật trạng thái/mức ưu tiên và ghi chú; role/revision do máy chủ kiểm tra | `support-admin-case-reply`, `support-admin-case-update`; browser/AX/live chưa đo |
| Locale/responsive | Fixed chrome VI/EN/ZH tách catalogue; bản Việt dùng “Trung tâm hỗ trợ khách hàng”; lưới case xếp một cột ở màn hình hẹp | Full Node `566/566`, syntax và `git diff --check` đạt |

Kết luận: Support mới đóng lát control-level UI/UX và ranh giới an toàn; SP-01 vẫn `[~]` trong
completion ledger cho tới khi có capability máy chủ, dữ liệu thật, browser/AX, CI và LIVE.
SP-02 (Guide/Chat Pro/feedback/community) vẫn là mục riêng chưa thực thi.

## Đối chiếu Voice Vault dùng lại — R218 — 18/10/2026

| Chức năng gốc cần có | Trạng thái hiện tại trên WebApp | Bằng chứng / giới hạn |
|---|---|---|
| Dùng giọng đã lưu ở SubDub và Video | Chưa đạt: có `2` link mở công cụ, không chuyển profile/draft. Nhãn đã sửa thành “Mở…” để phản ánh đúng. | `tests/voice-inventory-presentation.test.mjs`; browser QA xác minh navigation, không tuyên bố reuse. |
| Trạng thái, quyền, mặc định và nghe thử | Mỗi hồ sơ hiển thị trạng thái, quyền sử dụng, cờ mặc định, metadata nghe thử và thời điểm cập nhật. | Voice inventory test ở `3/3` locale; preview vẫn chỉ là metadata, chưa có signed link. |
| Đổi tên, đặt mặc định, xóa, nghe thử | Chưa đạt: bỏ `4` nút luôn disabled gây rối; ghi thông báo ngắn và giữ yêu cầu mở trong checklist. | API hiện có `/voice/profiles` dạng list; không có management/search/pager contract để wire UI. |
| Đếm nội dung và cảnh báo âm lượng 0 | Đã có đếm từ/ký tự Unicode, giữ 0 và cảnh báo không tiếng, đồng bộ range/number và hydration. | `tests/voice-input-feedback.test.mjs` 4/4; browser 18/18 cấu hình. |
| Locale và bố cục | VI/EN/ZH, gồm aria-label preset tốc độ; palette xanh/ngọc, tương phản cảnh báo 11,25:1 sáng và 8,84:1 tối. | Voice input/inventory/flow `64/64`; full Node `591/591`; browser/AX với fixture, LIVE chưa đo. |

Kết luận: đếm nội dung và cảnh báo 0% đã có bằng chứng renderer/interaction. Điều hướng
không được coi là profile handoff; hướng dẫn clone không phải wizard chạy thật. Voice Vault
và runtime parity vẫn mở theo ledger.

## Đối chiếu Voice STT workspace — R218 — 18/10/2026

Checkpoint inventory 19/10: đã kiểm read-state/retry/clear-stale bằng 34/34
test inventory và 18 cấu hình trình duyệt, shell + integration.js thật trên
API fixture. Đây là nghiệm thu lớp đọc/hiển thị. GET Core hiện trả tối đa 50
mục, `total` bằng số mục trả về; không chứng minh đã tải toàn bộ kho. Các proxy
management ở `c6bc455` được gỡ vì không có HTTP endpoint tương ứng phía Core.
Management/preview/handoff giữ mở; không tính là tính năng đã chạy như Bot.

| Chức năng cần đối chiếu | Hiện tại trên WebApp | Bằng chứng / giới hạn |
|---|---|---|
| STT trong workspace Voice | Có lane Giọng nói thành văn bản cùng TTS, Kho giọng và Thêm giọng; deep link `/voice/stt` và alias `/voice/asr` giữ đúng route | `renderVoiceWorkspaceNav()`; `tests/voice-workspace-stt-contract.test.mjs` `4/4` |
| Nguồn và ngôn ngữ | Có tệp audio/video nguồn, Tự nhận diện hoặc catalog ngôn ngữ nguồn, không trộn nhãn giữa VI/EN/ZH | `FIELD_SETS.voiceStt`; catalogue `portal-i18n.js`; quick-switch `152` destination mỗi locale |
| Định dạng đầu ra | Có Văn bản, SRT và VTT; khu vực kết quả vẫn rỗng/guarded khi máy chủ chưa cấp capability | Không tạo transcript, tệp hoặc download giả; upload/progress/copy/export runtime còn mở |
| Responsive và palette | Bốn lane xếp `4` cột desktop, `2` cột tablet và `1` cột màn hình nhỏ; giữ token xanh dương/xanh ngọc | `portal-theme.css`; contract source-level, chưa có browser AX upload/live evidence riêng cho STT |

Kết luận: STT đã đạt control-level UI/UX và locale parity, chưa đạt runtime parity với Bot.
Không được dùng `4/4`, `132/132` hoặc full Node `598/598` để suy ra upload, nhận dạng,
transcript, giao tệp hay LIVE đã hoạt động.

## Bổ sung đối chiếu — Admin data table trên màn hình nhỏ — 19/10/2026

| Chức năng gốc / hiện tại | Đối chiếu candidate WebApp | Bằng chứng / giới hạn |
|---|---|---|
| Bảng quản trị có thể đọc trên điện thoại | Giữ bảng semantic trên desktop/tablet; ở `<=560px` chuyển từng dòng thành thẻ dọc, mỗi ô hiển thị nhãn lấy từ tiêu đề cột. | `static/portal/portal.js`, `static/portal/portal-theme.css`, test `2/2`, full Node `705/705` |
| Lọc, chọn dòng và xem chi tiết | Không thay đổi event/filter/inspector; `data-label` chỉ là metadata trình bày, row vẫn có `tabindex`, `aria-selected` và focus ring. | Source inspection + `git diff --check`; chưa có browser fixture populated hoặc backend/RBAC |

Phần tài liệu gốc không có mô tả breakpoint hay thẻ điện thoại; đây là phần hoàn thiện UI/UX
WebApp, không phải mở authority dữ liệu hoặc thao tác tài chính.

## Đối chiếu R218 checkpoint 2026-10-21

| Nhóm chức năng gốc | Hiện trạng có bằng chứng | Chưa được suy diễn |
|---|---|---|
| Voice | Workspace TTS/STT/Voice Library/Clone, report tiến độ và locale đã có source/browser QA | Voice Vault management, preview signed, upload, TTS/STT runtime và delivery |
| Music/SFX | Nhạc nền/bài hát, 3 tier, gợi ý, quote freshness, report bounded, Library/SFX read-only | Generation, editor, player, download, save/reuse và hai bản giao thật |
| SubDub | 4 mode một màn hình, source có/chưa có phụ đề, catalog ngôn ngữ, 7 voice lane, 7 vị trí phụ đề, âm lượng | Upload/ASR/dịch/dubbing/Smart Multi/quote/job/result |
| Image | Create/prompt/AI edit/manual/upscale/cleanup/transform contracts và guarded UI | Reference upload, AI/manual execution, before-after, artifact/delivery |
| Video | Hub/Studio/Finishing/Frame Sequence vertical flow và localized guarded shell | 32 profile, render, timeline editor, AI/manual output, delivery |
| Utility/AutoPost/Support/Account | 10 route QA matrix, locale/responsive, avatar inline SVG, guarded states | OAuth/publish/ticket/approval/notes/role runtime |
| Admin | Locale/theme/data-card/shortcut/projection focused tests 80/80; core browser artifacts retained | Dynamic RBAC, records, approval/credit, Admin/app shared authority |
| Motion | Hydration entry, compositor transforms, reduced-motion, route cleanup | CLS/LCP/INP trace và production frame-time |

Nguồn đo: `reports/audit/R218-CHECKPOINT-20261021.md` và các artifact `R218-*-QA-20261020.json`.
Tất cả số liệu là checkout/QA cô lập; chưa phải trạng thái đã merge/deploy/live.

## Bổ sung đối chiếu — locale `/studio` và tên hiển thị SubDub — 2026-11-05

| Chức năng/thiết kế trước đây | Candidate hiện tại | Bằng chứng và giới hạn |
|---|---|---|
| `/studio` là trang điều hướng sáu bước, tên danh mục “Media Studio” | Route và sáu liên kết giữ nguyên; trong VI tên hiển thị là “Xưởng sáng tạo”, nội dung cố định được dịch; EN vẫn “Media Studio”, ZH vẫn “媒体工作室” | `tests/media-studio-vietnamese-purity.test.mjs` `7/7`; chưa browser/live |
| Spec `docs/superpowers/specs/2026-10-08-subdub-single-screen-ui.md` giữ tên SubDub trong bản dịch VI khi xem như danh từ sản phẩm | Theo yêu cầu Owner mới, các nhãn giao diện VI dùng “Phụ đề & Lồng tiếng”; EN/ZH và route `/subdub` giữ nguyên, định danh/API không đổi | Nhóm locale/sidebar/assistant/dashboard/voice `89/89`; không suy ra runtime parity |

Sai khác là phạm vi tên hiển thị theo locale, không phải chức năng hay route. Tên SubDub trong mã
định danh và ngôn ngữ EN/ZH giữ nguyên; riêng phần chữ VI được dịch theo yêu cầu mới.

Ngày 06/11, browser candidate đã kiểm đủ `18/18` cấu hình `/studio` ở ba ngôn ngữ,
hai giao diện và ba chiều rộng. Cột “chưa browser/live” phía trên là mốc 05/11:
browser trình bày đã đo, còn signed-session/backend/LIVE vẫn phải xác minh riêng.

## Đối chiếu Bản nháp — candidate 06/11/2026

| Thiết kế/chức năng trước | Candidate | Bằng chứng/giới hạn |
|---|---|---|
| Bản nháp riêng tư có bộ lọc, tiếp tục, lưu trữ và thêm vào dự án | Chức năng và khóa lưu giữ nguyên; 29 nhãn cố định VI và tiêu đề được dịch | Renderer10/10; không suy ra thao tác lưu backend đã được chạy |
| Thẻ hiển thị tên quy trình từ API và mã nội bộ | Tên quy trình lấy từ danh mục VI/EN/ZH; mã vẫn tồn tại trong dữ liệu, không hiện làm nhãn | Ba ca tên danh mục và ca fallback/giữ dữ liệu; không dịch tên khách nhập |
| Ô nhập điện thoại15px | Scoped16px khi ≤620px; 768/1440px vẫn15px | Browser18/18; không đổi bố cục, motion hoặc desktop |

Đây là sửa bản trình bày, không thêm dịch vụ tạo nội dung, quyền, biểu phí hoặc tác vụ.

## Đối chiếu trang Đăng bài — candidate 06/11/2026

| Hiện trạng trước | Candidate | Giới hạn |
|---|---|---|
| VI vẫn dùng AutoPost Hub, Affiliate, Asset Vault, Campaign/Project/Web | VI dùng Đăng bài tự động, tiếp thị liên kết, kho tệp, chiến dịch/dự án/ứng dụng; ZHdịch tên, ENgiữ nguyên | Chỉ catalog và nhãn điều hướng; không đổi route/data/brand |
| Ba khối hướng dẫn tĩnh chiếm diện tích trước vùng công cụ | Ẩn ba khối, giữ bảy nguồn/sáu khu vực/ba liên kết và ba hành động ngoài bị khóa | Không biến placeholder hoặc trạng thái chờ thành kết quả thật |
| Kiểm thử điều khiển mới xác nhận cân bằng key/topology, chưa bắt chữ Anh lẫn VI | Thêm renderer4ca và browser18cấu hình theo nội dung nhìn thấy | Có RED/GREEN; production phiên đăng nhập vẫn phải xác minh riêng |

Nguồn thiết kế trước: `tests/autopost-hub-product-controls.test.mjs` và renderer
`renderAutoPostHub`. Không tuyên bố hoàn tất tích hợp mạng xã hội từ thay đổi giao diện.

## Đối chiếu chuyển động — 08/11/2026

| Hành vi trước | Thay đổi hẹp | Bằng chứng và giới hạn |
|---|---|---|
| Trang Đăng bài có hiệu ứng co/dịch trên toàn main | Chỉ đúng route/layout bỏ entrance của main, không tắt lớp chuyển động khác | PR691 đã deploy; Chrome8cấu hình; chưa signed LIVE/FPS |
| Mỗi hydration dựng lại sidebar và đóng menu | Giữ menu/DOM/focus khi khách cùng trang/phiên và markup không đổi; sáu trường hợp thay đổi vẫn đóng | Nguồn27175790, Chrome8/8; auth/backend không đổi |
| Cleanup landing bật lại nút phát lại dù đang giảm chuyển động | Cleanup tôn trọng tùy chọn giảm; nút thường vẫn chạy | Nút thường lần2; dynamic hidden/disabled; initial static |

Nguồn thiết kế gốc: các contracts lifecycle/header/palette trong tests và portal-motion.js.
Không còn đúng nếu hiểu “cleanup luôn cho phép replay” hoặc “hydration luôn được đóng menu khách”.
Mốc lịch sử trên đã được phát hành qua PR692/runtime745fabbd; signed LIVE vẫn mở.
Xem receipt motion, không dùng số QA thay trạng thái production.

## Đối chiếu cỡ chữ Voice — 09/11/2026

Input Voice mobile15px ở baselinebd6f947f được nâng16px trong namespace task tại<=620px.
Các role desktop giữ nguyên (không giả định tất cả cùng15px), màu/route/action/scalar và
processing boundary không đổi.60field RED và120native cases đối chiếu source 06e4ab9;
CI/ship/LIVE riêng theo receipt Voice. Không suy ra engine/provider đã được thực thi.

## Đối chiếu kết quả lập kế hoạch video — 10/11/2026

Nguồn chức năng ban đầu: `docs/migration/CREATIVE_MOTION_GUIDE_CALLBACK_CONTRACT.md`,
`tests/test_creative_motion_guide_portal_contracts.py` và
`tests/test_long_form_video_planner_portal_contracts.py`.

| Trước | Candidate | Giới hạn |
|---|---|---|
| Kết quả hướng dẫn chuyển động có tên mục Anh và đoạn giải thích Việt trong mọi ngôn ngữ | 24 khóa chữ cố định VI/EN/ZH; nội dung khách/máy chủ giữ nguyên | Chỉ khối kết quả, chưa phải biểu mẫu hoặc cả đường dẫn |
| Kết quả kế hoạch video dài lẫn tên mục, đơn vị, ghi chú và xác nhận lưu | 45 khóa chữ cố định; số liệu, điều kiện lưu và nút vô hiệu không đổi | Không đổi chức năng tạo/lưu hoặc xác nhận tệp video |
| Kỳ vọng kiểm thử cũ tìm literal `matchesRouteFamily` trong hàm menu di động | Cả BASE và candidate đã dùng bộ ánh xạ menu chung, cùng một lỗi kiểm tra nguồn | Không đổi menu hoặc làm yếu kiểm thử trong đơn vị bản dịch |

Bộ 45 ca mới đi qua bộ chuẩn hóa thật; không dựng kết quả thay cho phản hồi hợp lệ.
Lỗi tràn mô tả trên điện thoại đã sửa bằng một quy tắc CSS hẹp và đạt kiểm tra
trình duyệt; bằng chứng cùng giới hạn CI/phát hành nằm trong receipt.

## Đối chiếu xác nhận lưu và lựa chọn — 10/11/2026

Nguồn gốc chức năng vẫn là các contract long-form/motion đã dẫn ở trên và
`tests/test_copyfast_long_form_video_planner.py`; không đổi thành dịch vụ tạo video.

| Trước | Candidate | Bằng chứng/giới hạn |
|---|---|---|
| Phản hồi lưu bị rút gọn rồi kiểm tra lại như định dạng gốc, mất xác nhận | Dữ liệu đã xác minh được chuyển đầy đủ tới bootstrap, renderer nhận bản chiếu đúng |84handler+60renderer;12luồng UI thật tạo/lưu/mở |
| Bộ lọc nhận nhầm câu cấm chuẩn trong kết quả là yêu cầu mô phỏng | Chỉ đúng câu cố định trong character_bible của kết quả được loại khỏi phép quét |108ca; không đổi bộ lọc đầu vào hoặc schema |
| Nhãn lựa chọn cố định còn sai ngôn ngữ, ô native nở hoặc cắt tên |19nhãn theo locale; scalar9/3/7giữ, ô có giới hạn và tên đầy đủ khi cần |24native+20helper; không tự thu gọn nội dung hoặc thêm ô rỗng |

Hai quan sát nhập liệu/che nút còn được giữ trong receipt; không dùng kết quả
đạt hiện tại để gọi chúng đã sửa. Signed production/device và motion vẫn riêng.

## Đối chiếu biểu mẫu video — 10/11/2026

| Trước | Candidate | Bằng chứng/giới hạn |
|---|---|---|
| Biểu mẫu/card/metadata lẫn chữ Việt/Anh/Trung |132khóa chữ cố định theo locale; chữ khách/máy chủ và protocol code giữ nguyên |24renderer, source đảo ngược đúng scope,9361keycũ giữ |
| UI bật gợi ý nhưng requestfence đọc account.id không có trong phản hồi trình duyệt |Dùng dấu phiên riêng từ dữ liệu phiên hiện hành đã có, giữ toàn bộ chốt epoch/tuyến/phiên |9handler faithful-no-id+clicknative3thẻ; không đổi authAPI |
| Roadmap mobile15px, nhãn/ghi chú sáng mờ; motion cảnh báo bị!importantghi đè |Ba rule roadmap và hai rule motion sáng giới hạn đúng form |24nativeaccepted:18giữ+6sửa; không đổi dark/layout/option/payload |

Các định nghĩa gốc trong renderer và contractprivate-route vẫn còn dùng; sai ở
cách gắn chữ cố định/ownershipstatephíaUI, không phải đổi chức năng lập kế hoạch
thành tạo video. Density, toàn ứng dụng, authlifecycle vàmotion cuối vẫn mở.

## Đối chiếu tiêu đề tám trang video — 10/11/2026

Nguồn khởi tạo của đơn vị này là tám định nghĩa route/tiêu đề/mô tả trong
`static/portal/portal.js` tại BASE564467fb, không phải một chức năng tạo video mới.

| Trước | Hiện trạng local | Giới hạn |
|---|---|---|
|8mô tả tiếng Anh thực tế là tiếng Việt;3tên VI tiếng Anh và1tên dùng prompt |16keycố định VI/EN/ZH;139focused+48native đạt |Chỉ header động, không server-first-paint |
|Có thể hiểu sửa tên là đã sạch toàn trang |Ảnh mobile vẫn cho thấy badge và chữ trong form còn trộn |Giữ mục inner-form/result mở, không tuyên bố đã hoàn tất |
|Các trang là công cụ lập kế hoạch |Giữ nguyên8route, kiểm tra quyền và dữ liệu/controls |Không tạo tệp video hoặc gọi provider |

PR704/705/706 đã được phát hành theo receipt tương ứng; các đoạn candidate phía
trên là mốc QA lịch sử, không thay thế SHA runtime trong receipt phát hành.

## Đối chiếu ba biểu mẫu và đường lưu — 10/11/2026

Nguồn gốc: các contract/Python test hiện có của VideoPrompt/VideoIdea/SelfShot
và renderer tạiBASEbf1e7ee3; không đổi chức năng lập kế hoạch thành tạo video.

| Trước | Hiện trạng local | Bằng chứng/giới hạn |
|---|---|---|
|Nhãn/option/result cố định lẫn chữ|420keyVI/EN/ZH; dữliệunguồn giữ|99casegộp; không dịch server/customerprose |
|Promptsave so language nhưng DTOkhông cólanguage|Thêmfield bắtbuộcvi/en,check vàgiữquaUI|Python10affectedpass; không bỏso sánh |
|Receipt/result bị rút gọn rồi kiểm tra transport lần nữa|Giữđủmetadatađãxácminh; giữmọi normalizercall|60affectedpass; SelfShotclosedkeys/falseflags được tăng |
|Ônhậpmobile15px|Đúng3form16px<=620px|Native18/18; desktopkhôngđổi |
|Nút lưu có thể mất dù phản hồi hợp lệ|9luồngthậtđã lưu/readback/mở trongDBtạm|9plan/30scene, không suy production/providerLIVE |

Các kỳ vọng kiểm thử cũ cấm language trong response không còn đúng với contract
khớp nguồn hiện tại. Bốn phép dò nguồn menu đã sai từBASE vẫn ghi nhận, không
sửa menu hoặc bỏ assertions để gọi xanh. Nhómserver-outputlocale/detail/motion
vẫn mở, không dùng kết quả đơn vị này thay cho toàngoal.

## Đối chiếu màn Đăng bài theo ảnh báo lỗi — 10/11/2026

Nguồngốc:renderAutoPostHub vàautopostHub-product-controls/publishing-puritytại
BASE2174a2b2; sourcecũbắtbuộc7nguồn/5bước/3nútchờnaykhôngcònđúngyêucầukhách.

| Trước | Hiệntrạnglocal | Bằngchứng/giới hạn |
|---|---|---|
|7nguồnluônChờcấpquyền,3ôkhóakhôngthao tác|Bỏkhỏirenderer,khôngthaykhungrỗng|3linkthật;6native/18navigation |
|TênĐăngbàitựđộngnhưngchưacóthao tácđăngngoài|TênĐăngbài/Publishing/内容发布|3metadata+3serverfirstpaint |
|ToastlộCoreBridge/canonical/ledger|13thôngbáohiệnngônngữkhách,lỗivẫnalert|63caseledger,unknown/prototype/ARIA/timergiữ |

Khôngxóaendpoint/backendhaytựmởquyềnđểlàmgiaodiệntrônghoạtđộng. Dọnkhốidư
ởcáctrangkhácvàchứngminhđầuraenginevẫnđượctheodõiriêngtronggoal.

## Đối chiếu mật độ ba trang video — 10/11/2026

Nguồnđịnhnghĩagốc:3outerrendererVideoPrompt/VideoIdea/SelfShotởBASE5ad97cf9.
Các đoạnintro/metrics0/guard-list/finalscopekhôngphảichứcnăngthựcthi;
Ownerđãyêucầubỏchúng,khôngphảichỉdịchchữnộibộ.

| Trước | Hiệntrạnglocal | Giữ |
|---|---|---|
|Formbịđẩyxuốngbởigiảithích/sốđếmvàasidekhôngthao tác|Bỏ3khốitrangtrímỗitrang,đổiwrapperthànhverticalstack|Form/kếtquả/lưuthậtbyte-identical |
|Headerformnóiphiên/CSRF/template/storage|Bỏđúng3paragraphngoàiform|Khôngxóakiểmtraquyền/CSRF/consent/inputhelp |
|Layout2cộtđểtrốngnếuasidebỏ|Dùngportal-stackhiệncó,khôngthêmCSS|6nativewidth/focus/overflowđạt |

Khôngbậtenginehayhứavideođãtạo;bảnkếhoạchvẫnlàchứcnăngđượcthựcthivàlưuthật.

## Ba công cụ kế hoạch còn lại — đối chiếu 10/11/2026

Nguồn gốc: ba renderer/field/result và parser trong portal.js/integration.js
tại BASEe63f073f. Không lấy nhãn catalog làm bằng chứng engine đã chạy.

| Trước | Thay đổi đang nghiệm thu | Giữ nguyên |
|---|---|---|
|Khối số đếm/giới hạn kỹ thuật đẩy biểu mẫu xuống|Bỏ khối thừa, giữ stack chứa biểu mẫu và kết quả|16/10/10field,consent,nguồn và quyền|
|Kết quả/biên nhận hợp lệ bị mất metadata qua parser|Giữ đúng metadata đã qua kiểm tra|Mọi normalization/source-match/cờ an toàn|
|Dựa vào account.id không có ở trình duyệt|Dấu phiên riêng trong RAM, đúng route/epoch|API/auth/CSRF máy chủ không đổi|
|Ô chọn số HTML khiến Cinematic không lưu được|Chuyển đúng ba chuỗi chuẩn trong matcher biểu mẫu|Sai/mismatch vẫn chặn,transport vẫn strict|
|Thông báo khi chỉnh sửa/tạo/lưu lẫn ngôn ngữ|VI/EN/ZH ngắn gọn, lỗi vẫn hiển thị|Không giả thành công/đầu ra/provider|

Đây là chức năng lập và lưu kế hoạch văn bản, không phải video đã được kết
xuất. Native cuối, CI/phát hành và nội dung máy chủ/trang chi tiết còn mở;
không đổi tài liệu thành tuyên bố hệ thống đã hoàn tất khi thiếu bằng chứng.

## Hai biểu mẫu tham chiếu — đối chiếu11/11/2026

Nguồn gốc:renderImageMotionPlanner/renderReferenceFormatPlanner tạiBASE7f8753d5,
không thay source/result/normalizer/backend bằng giao diện trông thuyết phục hơn.

|Trước|Hiện trạng local|Bằng chứng/giới hạn|
|---|---|---|
|Intro/số đếm/aside giớihạn thực thi đẩy form xuống|Bỏ khối thừa,giữstack/form5/9field|24statecontrolscalars/guards/resultcallsgiữ|
|Nhãn/option trộn ngôn ngữ|75keydùngthậtVI/EN/ZH,36aliasthừađãbỏ|10349giátrịcũbyte-identical|
|Mobile15px,lightlabel/help1,2653:1|14controlmobile16px,20mẫu sáng đạt|12native/120mẫugiữguardsempty/blocked|
|Không có tham chiếu trong tài khoản|Vẫn khóa thao tác,hiện hướng dẫn nguồn|Không dựngAPIreferencehoặcfalse-ready|

Đây là dọn đúng biểu mẫu,không phải nghiệm thu tạo/lưu kết quả hoặc đầu ra
video. Phần đó tiếp theo;không đổi nhãn thành công để che chức năng chưa đạt.

## Thông báo chung không có hướng xử lý —11/11/2026

Trước:legacyguarded được đổi thành "Không thể thực hiện thao tác này lúc này."
nhưng vẫn là dòng chung Owner yêu cầu bỏ. Nay exactguardtoastkhông tạo node
haytimer cho đúnglegacy/VI/EN/ZHcâu đó. Lỗi cụthể/unknown vẫn hiển thị,
status/backend/quyềnkhôngđổi. Không coi việc xóa thông báo là tạo thành công.

## Kết quả/lưu hai công cụ tham chiếu —11/11/2026

Nguồngốc:2result/2saveproducer,4receiptparser vàImageMotionrequestfence tạiBASEd72eed76.

|Trước|Hiệntrạnglocal|Bằngchứng/giớihạn|
|---|---|---|
|Imagebấm0POSTvìaccount.idkhôngđượccấp|PrivateRAMstamp,capture/currentepoch/path/Authgiữ|20focusedpass,6actualmobileflowskhônginternalID|
|Referenceđãlưunhưngreceiptbiếnmất/nútlưuvẫnbật|Giữđúngmetadatađãxácminh,parseridempotent|6plan18scene/readback/open,terminalbuttonabsent|
|Emptycard/confirmationpaneldưsaukhilưu|Emptyreturn"",receiptchỉhiệnkếtquảlưuthật|42renderer×2checks;sourcecallsgiữ|
|Fixedlabels/cảnhbáo/toasttrộnVI/EN/ZH|76keymới,unknownerrors/lock/retrygiữ|27lockcases/111toastpass|
|Vùngkếtquảphụthuộclayoutcũ|2semanticdataattrsvalidresult/receiptonly|DOMstale-noteRED->GREEN,21markerasserts|

Nộidungmẫumáychủvàtrangplanđãlưuvẫnmởchờdịchthuần;6happyflowskhôngđóng
Referencecurrent-input/stale-session/actualretry/device/Safari/motion/engineoutput.

## Nội dung hệ thống hai kế hoạch — 11/11/2026

Nguồn gốc: hai pure composers và catalog hiển thị tại BASE1b76f75d.

| Trước | Hiện trạng local | Giữ nguyên |
|---|---|---|
| Image trộn VI/EN bất kể language | Chữ hệ thống theo vi/en/zh hiện có của reference | Raw reference, ID, duration, ba scene và helper/schema |
| Reference en vẫn ghép catalog VI, vi lẫn từ chung tiếng Anh | Catalog và template cùng theo payload vi/en | Accepted languages vẫn vi/en; không thêm zh |
| System text và customer text khó phân biệt | Chỉ fixed phrase lookup, named format truyền giá trị một lần | Customer source_title/topic/audience kể cả literal braces |
| Compose và recompute cùng gọi composer nhưng nội dung còn trộn ngôn ngữ | Cả hai tiếp tục gọi cùng pure composer đã dịch | Idempotency, quyền, validation và persist flags không đổi |

Không rewrite/migrate kế hoạch cũ. Detail labels/English shot-note headers,
các planner khác, stale-session/current-input, auth/AX/device và motion cuối
chưa được suy là hoàn tất từ đợt dịch hai hàm này.

## Kế hoạch đã lưu — thay đổi 11/11/2026

Nguồn đối chiếu: hai converter tại BASE7ef871e3, không phải tính năng engine.

| Trước | Ứng viên hiện tại | Bằng chứng / giới hạn |
|---|---|---|
| Preview đã dịch nhưng brief/scene headers lưu bằng EN | Fixed saved prose chọn cùng content language | RED7/5pass ->18passed(15giữ+3affected);6actualflows đạt |
| Reference EN objective ghép direction VI | Lookup direction từ bảng chữ đã duyệt theo language | Customer goal ID/audience không đổi |
| Image audience tự điền Private Web editor | Optional empty audience, không bịa khách mục tiêu | Existing optional schema giữ nguyên |
|4dòng giới thiệu/giới hạn và5dòng ghi chú lặp | Brief3dòng có nguồn/lựa chọn/ranh giới thật; scene4dòng giá trị | Không bỏ camera/audio/editorial/timing hoặc quyền sử dụng |
|Nhãn dễ vô tình đụng guard URL | R1 file: bị từ chối; giữ guard, sửa đúng EN label |40BASEcases0newrejection;6darkreadonly đạt;CI/delivery receipt trên Issue689 |

Không rewrite records cũ, không diễn giải việc lưu kế hoạch là đã tạo tệp.
Detail UI labels/tags,11giới hạn title cũ, các planner khác và full-goal gates
vẫn mở. Nguồn case chuẩn và phiên Tester SPC được thêm trước push.

## UI kế hoạch đã lưu — đối chiếu 11/11/2026

NguồnBASE652af67d:5renderer vàUUIDpage.section,scopedthemeCSS; khôngengine/APIchange.

|Trước|Hành vi mới trong code|Bằng chứng/giới hạn|
|---|---|---|
|Intro/counter/boundary vàtechnicalparagraphs cheeditor|Bỏ đúng markup tĩnh,khôngbỏform/control/history/guard|48views/1392interactiveattrsparity|
|3summaryfacts là3ô106px|Facts inline/wrap,gọn nhưng đủ trạng thái/revision/scenecount|320actualmax54px|
|Rawsystemtagchips trộn thẻ khách|Finite known-origin metadata decoration filtered,custom/unknown/rawinputs preserved|Tagcases3locale,0contextmutation|
|Nhãn sáng trênwhite/mobile15px/runtimegraytiles|Scopelabel/support/surface roles dùngtokens,mobile16px|2718samplesmin5.3313,54aggregateviews|
|UUIDsectionrawEnglish ởbreadcrumb|Existingpage.titlelookup cho displayleaf|3localeRED->GREEN,6actualheaders|
|DuplicatefieldIDs làm label sai control|Khôngsửa lén trongclutterpatch; namespace next|9BASEduplicateIDgroups;khôngclaimwholeAX|

API/names/actions/confirmations/readonly/archived/clientdata giữ nguyên; không
migrate/cậpnhật productionrecords. Rawtagediting/oldrecords/title/stale-retry/
auth/device/signedLIVE/motion-last vẫn thuộcfullgoal,khôngđóng bởiđợtUI này.

## Video label association — đối chiếu 11/11/2026

|Trước tạiBASEb1a48e09|Code mới|Bằng chứng/giới hạn|
|---|---|---|
|9duplicateIDgroups,scene-title label trỏ khácform|4existingrenderFields consumers truyền namespace role/UUID|24RED->GREEN,27passed|
|Generichelper đã có optionalnamespace nhưngVideo chưa dùng|Reusehelper5tharg,khôngsửahelper/signature/normalizer|Only4callsubstrings,19protectedpaths unchanged|
|Data/action/disabled có nguycơ đổi khi xửlýIDs|WholeHTML trừid/for/aria-describedby exactBASE|24views/digest/rawrecords exact;12native/336clickfocus/0valuechanges|

Không data migration hay productionrecords writes; actual clickfocus kiểm riêng,
không coi renderPASS là toànappAX/providerLIVE/device. Otherfullgoalgates giữmở.

## Membership/product emphasis — đối chiếu 11/11/2026

|Trước|Code mới|Bằng chứng/giới hạn|
|---|---|---|
|Tierdínhlabel/2unavailable/internalverified/duplicatebenefit|Tierblock/missingbalancekhôngemptybox/protocolremoved|30membercases/3paragraphcases,valid0/VIP/customdata giữ|
|6landingtoneclassesđềuépteal|6familycolors+edgeSVG/headingaccentshared|60uniqueactualviews,sáng/tối/390/1440;khôngfullfunctional/adminclaim|
|DeadlaunchpadselectorskhôngđủchoStudio|Actualdashboardh1/6studioarticlescovered|NativeDOMthật,nofakecards/API|
|Protocolcopyrảiráctoànapp|Exactmembership/2accountparagraphsremoved,actualcandidateinventoryopen|Khôngnói694catalogcandidateslà694visiblebugs;consent/errors/securitygates giữ|

Noauth/CSRF/schema/DB/provider/wallet/payment/Bot/route-engine/motion/sourceAPI
change. SameAntigravitysession/fragmenthistory;no directappimplementationtakeover.

## Thông báo và khối giải thích tĩnh — đối chiếu 11/11/2026

|Trước ở bản đối chiếu 8371c43d|Hành vi mới|Bằng chứng và giới hạn|
|---|---|---|
|Thông báo nổi che chữ trên nút lưu|Hàng thông báo riêng, nội dung cuộn trong phần còn lại|24 trạng thái có thông báo thật; không dùng hit-through thay bằng chứng thị giác|
|Hội viên luôn thêm ô danh mục không khả dụng|Bỏ đúng khối tĩnh, không thêm ô thay thế|12 ca ba ngôn ngữ/bốn trạng thái giữ nguyên phần còn lại, kể cả giá trị 0|
|Câu giới thiệu landing giải thích cơ chế bên trong|Một câu hướng dẫn khách hàng tương đương Việt/Anh/Trung|3 ca giữ nguyên mọi khóa khác và toàn bộ HTML ngoài câu này|
|Nguy cơ thay luồng đang chạy khi dọn UI|Không đổi API/auth/handlers/tiền/provider/motion|94 ca Node, 12 ca Python; 12 lượt xem chỉ đọc và 3 lượt rời trang|

Không coi việc bỏ một khối là đã hoàn tất locale/clutter toàn app. Không có
thay đổi dữ liệu khách hoặc xác nhận đầu ra dịch vụ trả phí trong phạm vi này.

## Chữ Hội viên — đối chiếu 11/11/2026

|Bản trước e2afca85|Thay đổi giới hạn|Bằng chứng|
|---|---|---|
|Hộp dẫn Bảng giá luôn tiếng Việt, lộ route|Bốn đoạn chữ theo locale, liên kết thật giữ nguyên|12 ca renderer so controls/HTML hữu hạn; không sửa API|
|14 khóa dùng ngôn ngữ triển khai|Chữ dành cho khách; thiếu dữ liệu không bịa gói/quyền lợi|40 giá trị đổi/2 giữ; 15 giá trị mới, snapshot strict19keys|
|Ghi chú tĩnh trộn ngôn ngữ dưới nguyên tắc|Chỉ bỏ render danh sách đó, giữ nguyên tắc/trạng thái thật|12 ca có missing/0/VIP/catalog và giữ dữ liệu khách|
|Chữ trắng/cyan sáng, màu tối chưa đủ rõ|CSS riêng callout và CTA dùng vai trò màu đúng theme|12 view/240 mẫu, min5,216649621048673:1, 0 indeterminate|

556 ca nguồn/hồi quy đạt, 67 ca ảnh hưởng chạy lại sau màu cuối; không cộng
trùng số ca. Nhóm này không thay tiền, quyền hoặc nguồn dữ liệu danh mục.

## Ghi chú và loại gói Hội viên — đối chiếu 13/11/2026

|Trước ở BASE78dc73c8|Hành vi mới|Bằng chứng và giới hạn|
|---|---|---|
|Loại gói mặc định luôn tiếng Việt|Dùng khóa dịch gói hiện có ở VI/EN/ZH|60 ca renderer thật, không thêm khóa|
|Nguồn thiếu ghi chú nhưng bộ chuẩn hóa tự thêm câu triển khai|Formatter riêng kiểm nguồn rồi bỏ paragraph khi thiếu|Không đổi canonicalPackageCatalog hoặc xóa chuỗi khách|
|Ghi chú thật có thể trùng câu thay thế cũ|Giữ nguyên ghi chú đã chuẩn hóa/escape|Có case trùng nguyên văn, chữ kỹ thuật và script-looking|
|Duplicate/nguồn sai có thể cho mượn ghi chú|Lấy dòng hợp lệ đầu tiên theo code+label và giới hạn nguồn|240 ca hồi quy, 18 tệp bảo vệ giữ nguyên|

12 component có nguồn tổng hợp không thay bằng chứng API. 12 lượt xem thật
có đăng nhập QA/3 rời trang chỉ đọc không chứng minh signed production hoặc
provider output. Các cổng toàn goal và motion cuối vẫn mở.

## Nhãn và panel điền sẵn — đối chiếu 13/11/2026

|Trước ở BASEc4da5f4a|Hành vi mới|Bằng chứng/giới hạn|
|---|---|---|
|Alias AI Studio thiếu dù khóa dịch đã có|Thêm một alias cố định, không thay manifest/khách|27ca3đạt/24lỗi→27đạt|
|Ba panel hứa phần cứng, giá, độ chính xác và kết quả nhưng chỉ gọi alert|Helper trả chuỗi rỗng; giữ chữ ký/callers/real forms|138ca62đạt/76lỗi→138đạt|
|Native click sang video tạo36CSP inline-handler errors|Bỏ nguồn nút giả, không nới CSP/logs|18view/18click cuối0lỗi/overflow|
|Nguy cơ dọn nhầm phần đang chạy|So mọi HTML/controls/context ngoài panel và nguồn bảo vệ|421Node,3consumer/18files exact,0ghi sản phẩm|
|Status-grid tưởng còn hiện dựa vào renderer source|Rút phiếu sau đối chiếu CSS đã ẩn|Không áp dụng mã hoặc chấm lỗi worker|

30caPythonđạt/1CSS-tail lỗi y hệt BASE; không sửa theme/motion trong đợt này.
Danh mục root nhẹ riêng, thiết bị/Safari/signed production và provider output
không được suy ra từ các ca renderer/native nhóm.

## Chat/Documents root-access — đối chiếu 14/11/2026

|Trước ở BASE7ef5e3c6|Hành vi mới|Bằng chứng/giới hạn|
|---|---|---|
|Tiêu đề root luôn tên Anh, mô tả lẫn kỹ thuật|Bốn roottext dùng4khóa dịch cũ|Rootonly; tên khách trùng tên sản phẩm giữ nguyên|
|GuardChat có signed-session/thread/server/guarded|3khóaVI/EN/ZH,giữ2tìnhhuống truy cập|72finalcases,không đổi canView/canCreate|
|Documentguard lặp3tag triển khai|2khóa mới+khôngtagrowrỗng|Dữ liệu/loading/failed/ready/controls exact|
|Modulecard cần giữ ưu tiênentrylabel|Fallback dùng root khi thiếuentrykey,APIentry cósẵn ưu tiên|12view/12click thật,href/data unchanged|
|Phiếu chènkhóa trướcapi saufreeze làm VMlỗi|Worker catalogR2 chèn trướcverify/freeze|SPEC SAI của người giao,khôngworkerfault hoặc trực tiếp sửalogic|

358affected/72target có chồng lấn;32Pythonđạt/1CSS-tailBASEfailure;24rootview
sáng/tối. Không claimwholelocale/AX/auth/device/provider/signedproduction/motion.

## Chat authoring/Document read — đối chiếu 14/11/2026

|Trước ở BASEd14c6f0e|Hiện tại trong phiếu|Bằng chứng/giới hạn|
|---|---|---|
|19chữ rootChat lẫn thuật ngữ vàAnh|Câu do người dùng hiểu theoVI/EN/ZH|Không biến lưu thủ công thành AIoutput|
|8nhãnfilter hardcodedVI,review/handoff/archive|Nhãnđộng theo locale,nămvalue/ordercũ|Form/GET/quyền/khách giữ|
|5thôngbáotài liệu lẫn private/metadata/projection|Tải/lỗi/thửlại dễ hiểu|Readytools/hiddentags giữ;retrythật|
|Keyset snapshots chặn tất cả key mới|Chỉ32key/96value đã duyệt được chuẩn hóa|Hash/thứtựcũ giữ,mutation/unknown thấtbại|
|Run nhiều request gặp429 ởlocale3|Giữ32viewhợp lệ,serverriêng16ZH|Không tắt rate guard hoặc gọi lại VI/EN|

55target/72prior/186affected/288historical cóchồnglấn;45Python/1BASEfailure.
ĐườngengineTTS mới ởsourceaudit+RED,khôngđượcghi đã nhậnâmthanhthật.

## TTS completion — đối chiếu 14/11/2026

|TrướcBASE52f3b4a5|Hiện tại|Bằng chứng/giới hạn|
|---|---|---|
|ok:true bịghi completed dùchưaâmthanh|Đòicompleted+booleanTrue|23newcaseBASE19RED→GREEN|
|Localcompletedthiếutệp làmGETbỏqua|Chođọclạichỉbảnthiếuđầura|Oldrecordrepair/51finaltests|
|Phản hồitrễcóthểghi đècanonicalcompletedthiếutệp|SQLguard bảo vệbảncóâmthanhđãxong|4concurrentlatecases|
|SourceauditnghiIDruntimekhácWebID|Bot804e23da lưuWebjobIDlàmprimarykey|Chỉđọcnguồn,khôngsửaID/auth|
|Source/readinessđượcnhầmlàđầurathật|GiữactualfinaloutputNOT_OBSERVED|0realprovidercalls,khôngfakeaudio|

## Usable Chat/Document copy — 14/11/2026

|TrướcBASE2cae14ab|HiệntrạngđợtUI|Bằngchứng/giớihạn|
|---|---|---|
|ChatfieldnameshiệnlẫnAnh/kỹthuật|19text3locale,8contractgiữ|12consumercreate/detail,24nativegõ/chọn|
|Chatintro3thẻ0chiếmhếtmobile|Chỉdlallnonpositivebỏ,positivegiữ|24cases,ảnh390thấyform|
|9Doccards3grouplẫnprivate/runtime/output|24textcustomer-language|36readycases giữhref/readiness|
|Boardinstructions/historylẫnjargon|24textvàcountparamsđúnglocale|48nativeview,12retry/12toolnav|
|Footerchỉdisclaimerkỹthuật|Bỏexact1line,noreplacement|Sharednotes/otherconsumerskhôngđổi|
|Testcũđòichữthuậtngữ|Actualconsumer +strictfinitehistoricaladapter|Unknownkey/mutationgiữFAIL,khôngđổigoldenhash|

Khôngđóngtoànroute/auth/AX/device/Safari/provider/signedproduction/motion;
chữngoàiphiếu/toast vànhãnsángnhạtphảilàmriêng.

## Làm mới tài liệu/chữ Hội thoại — đối chiếu 14/11/2026

|Trước BASE3477d0d8|Trong phiếu hiện tại|Bằng chứng/giới hạn|
|---|---|---|
|Đọc lỗi trả[] vẫn báo đã làm mới|Chỉ mảng+ready hiện tại được báo cập nhật|42 ca thực thi handler/loader; không đổi loader|
|Phản hồi làm mới cũ có thể báo thành công|Chặn đổi trang/phiên/yêu cầu/đăng xuất|Không thêm yêu cầu hoặc đổi auth|
|Thông báo làm mới lẫn tên triển khai|4 khóa/12 giá trị VI/EN/ZH|Chữ cũ giữ, adapter chỉ4 khóa theo hash|
|Nhãn Chat sáng1.26533:1|Dùng màu chữ chính,8.64385:1|6 native view/66 labels; tối không đổi|
|Chỉ source/HTTP được hiểu là chạy engine|Tách bản nháp, confirm và file âm thanh thực|Phiên Web–TTS chỉ đọc; chưa xác nhận audio thật|

Không thay công cụ/đường xử lý/tiền/ENV/Bot/motion. Giao hàng có receipt riêng;
native detail/device/Safari/toàn app và đầu ra provider không được suy từ phiếu này.

## Thẻ Hội thoại — đối chiếu 14/11/2026

|TrướcBASE398cea1c|Trong phiếu hiện tại|Bằng chứng/giới hạn|
|---|---|---|
|Thẻ cònFocus/context/review/archive/Mởthread|20key60valueVI/EN/ZH|Không đổi customerdata/rawcodes/links|
|Aside chỉ giải thích triển khai ởroot/detail|Bỏexactreturn,khôngkhungthaythế|Execution controls giữ,39targetPASS|
|Bỏaside đểdesktop trống mộttrack|Onlychildform spans existinggrid|RED604.546875/1088→1088/1088px|
|Mobile đã1cột|Giữ343/343px,sáng/tối|Không đổigridtemplate/motion/detail|
|FixtureQA5states cóguarded khônghợp đồng|4validstates+draftlặpIDriêng|Loaderkhôngbypass,unknownVM riêng|
|Ngày giờ vẫnISO/phântrangchưa dịch|Giữmởphiếukế,khôngbáođãdịchhết|KhônggộpcodechưaQA vàođợtthẻ|

## Ngày giờ/chuyển trang — đối chiếu 14/11/2026

|TrướcBASE7e30dd95|Trong phiếu hiện tại|Bằngchứng/giớihạn|
|---|---|---|
|Thẻ hiệnISO cóT/độ lệchgiờ|Intlmedium/short theoactive locale/browserzone|Khôngđổitimestampatrest/biểuthứckhác|
|Ngày malformed hiệnrawtext|Ngày thiếu/lỗi/formatterthrowempty về—|31newcases,khôngrawexception|
|PhântranghọithoạiluônViệt|4keys12valuesVI/EN/ZH|SafeText/uiText,dynamicfallbackgiữmath|
|Trangđầu/sau/chuyểnngược|Cùngoffset0→50→0 và50→5→50thẻ|18nativeactualGETstates,khôngfakeAPI|
|Adaptercũđoobjectclonefrozen|ĐoVMcatalogthậttrướcprojection|4harnesscases sửa,khôngclonefreezefakePASS|

## Biểu mẫu/nút chi tiết — đối chiếu 14/11/2026

|TrướcBASEd71c68c9|Trong phiếu hiện tại|Bằng chứng/giới hạn|
|---|---|---|
|Loạicontext/Tags/PromptlẫnAnh|19nhãn/gợiý/lựachọn3locale|Raw4context3turncodes/constraints giữ|
|Self-review/Archive/Drafttrênnút|10nhãn/xácnhận3locale|State/rights/actions/targets/disabledgiữ|
|Assertcứngcâu“không tạo câu trả lời giả”|ActualrunfieldcontractkhônghứaAI|1affectedPythonPASS,cácguardkhácgiữ|
|QAđòiidnộibộtrongpublicme|Kiểmknownfakeidentity+exactownerIDs+GETscope|KhônglộID/thayprojection/auth|
|Mộtservernhiềuviewgặp429|Giữ13states,xửlý11statesthiếuserverriêng|24unique,khôngtắtguard/khônglặpVI|

## Thông tin/chỉnh sửa chi tiết — đối chiếu 14/11/2026

|Trước BASE20c3e6fd|Trong phiếu hiện tại|Bằng chứng/giới hạn|
|---|---|---|
|Guard/thông tin cố định lẫn ngôn ngữ|Sáu khóa mới và dùng lại nhãn đã dịch|Giữ điều kiện quyền/ID/backlink và nội dung khách|
|Revision hiện tiền tố `v`|Nhãn lần cập nhật và cùng giá trị số|Không đổi phép tính hoặc dữ liệu lưu|
|Phần chỉnh sửa còn chữ cố định|Năm khóa mới và huy hiệu theo locale|Tám trường/lifecycle/attrs/disabled giữ|
|Đòi nguyên byte toàn bộ đề xuất|Ghi rõ ba dòng trống bổ sung của điều phối|M1 không hành vi, không worker fault; giữ native binding|
|Một bộ đo không đủ chứng minh toàn trang|24 unique scoped native states/13 ảnh|Checkbox EN và context/history/run ngoài phiếu vẫn mở|

## Ghi chú/nội dung/ô ghim — đối chiếu 14/11/2026

|Trước BASEd124b867|Hiện tại trong phiếu|Bằng chứng/giới hạn|
|---|---|---|
|Hai form còn Private context/Human-authored/Prompt|10keys3locale, hướng dẫn/nút dễ hiểu|Form attrs/disabled/rights giữ|
|Context library/Conversation record ở sáu vị trí|Sáu slots dùng locale|Không đổi thứ tự/nội dung khách|
|Checkbox EN/ZH rơi về “Tôi xác nhận”|Field riêng “Ghim hội thoại” theo locale|Root/detail value/checked/ID giữ|
|Mutation19field dùng replacement đã không khớp|Chiếu accepted scope,assert target1 trước mutate|285+1affectedPASS, không no-op giả|
|Adapter mới chặn nhầm nguồn lịch sử trước gate cũ|Nguồn không khóa mới chuyển nguyên vẹn|Old hash gate vẫn bắt writablemutation|

## Danh sách ghi chú/nội dung — đối chiếu 14/11/2026

|Trước BASE6a519756|Trong phiếu hiện tại|Bằng chứng/giới hạn|
|---|---|---|
|Context/Active/Archived/Archive còn lẫn ngôn ngữ|Thẻ và bốn option dùng locale|Giữ raw kind/state/caps/selected/disabled|
|Turnlist có v/lượt và loại cố định|Nhãn lượt/cập nhật/nút/xác nhận theo locale|Ordinal/revision/rawdate expressions giữ|
|Chỉ QA metadata/arrays rỗng|QA có24contexts18turns ở15threads|ActualGET/DOM,8tables exact trước/sau|
|Hàm options dùng global label cũ|Local labels theo mỗi lần render|Không đổi sharedmap/helper signature|
|Nguy cơ kiểm lặp candidate/permanent|MộtactualVM RED→GREEN147/147|Không thêm candidate GREEN trùng|

## Nhãn loại ghi chú sáng — đối chiếu15/11/2026

|Trước BASE87afb6b6|Trong phiếu hiện tại|Bằng chứng/giới hạn|
|---|---|---|
|Rulecũ chỉ áp `.portal-field > label`|OneEOFselector cho saved-context `>span` sáng|Chỉcolor,không global/broad/darkchange|
|Màu nhạt1.26533:1|Màu semanticink12.35155:1|ComputedRGBA,khôngguesshex|
|RawDOMkhác do empty-style attrs|Giữraw,semanticclone bỏexactemptycontrolstyle|Mọi name/value/disabled/nonempty CSS giữ|
|JSundefined keys khácJSONlưu|Presenceguards+samewirecomparison|Không bỏ meaningfuldata/màu/nền/layout|

## Lịch sử hội thoại — đối chiếu15/11/2026

|TrướcBASE344e0310|Trong phiếu hiện tại|Bằng chứng/giới hạn|
|---|---|---|
|Versionhistory/thread/revision/feed/metadata trongfixedcopy|6version+16activitykeys3locale|4exactworkerchanges,rawdata/attrs giữ|
|Hoạt động hiển thị enum nộibộ|15finiteactionlabels/unknownchung|Không bỏ hàng/Number/String/time expressions|
|ActivityR1thiếuVIfallback|SamefragmentR2đúngmọi fallback|ActualVMfallbacktest,onecoderfailuregiữ|
|QAtrước chưa có versions/events|Ownedcopy24versions45events|ActualGET/DOM/order,8tablesexact|
|RawISOtime cònhiển thị|Giữngoàiphiếu ngàygiờ kếtiếp|Không nhận toànmàn sạch mọi định dạng|

## Yêu cầu hội thoại — đối chiếu15/11/2026

Nguồn gốc đối chiếu: hợp đồng Chat guarded receipt trong
`tests/test_chat_workspace_portal_contracts.py` và ba hàm renderer ở BASE63ddccd5;
không suy thêm chức năng trả lời tự động từ bảng tính năng chung.

|Trước BASE63ddccd5|Trong phiếu hiện tại|Bằng chứng/giới hạn|
|---|---|---|
|Bốn ô implementation/status còn thuật ngữ|Hai trạng thái tiếp nhận/trả lời tự động|Không đổi readiness/capabilities hoặc bật executor|
|Timeline/kicker/confirm/note lẫn ngôn ngữ|29khóa×3locale, đầy đủ VI fallback|Bộ lọc/50/order/rawtimes/customerdata giữ|
|86pxcap cắt giá trị sau dịch|Hai rule cho label/value xuống dòng|NativeVI/ENfail giữ; R2ba locale24uniquePASS|
|Chỉ có metadata QA rỗng về run|21lifecycle run+21FKuser message giả|GET/DOM thật không chứng minh thực thi/assistant/output|
|Needle test ghim nguyên câu kỹ thuật|Một biểu thức `safeText(uiText(...))` mới|Mọi chốt action/quyền/private-data còn nguyên|
|Lịch sử unit trước chưa có receipt tại tài liệu|PR739 đãgiao63ddccd5/deploy43644999130|Signedproduction UI và wholegoal vẫn mở|

## Metadata Chat —đối chiếu15/11/2026

Nguồngốc:registryChat/localizedPageTitle/Description/_shell_title_for/
_PORTAL_SHELL_TITLES tạiBASE0e97fd8a,khôngbịa featuregốc.

|Trước BASE0e97fd8a|Trongphiếu|Bằngchứng/giớihạn|
|---|---|---|
|DetailAIChatWorkspace/rootnhãnmenu rộng|TitleTròchuyện/Chat/对话riêng|Registry/customerfields giữ|
|Descriptionthread/context/Webaccount|Môtảviết/lưudễhiểu|2keys/locale/fallback/per-render|
|SSRgenericworkspace|HTMLresponsechatlocale ngay|UUIDfullmatch/trust/auth giữ|
|Catalogchatconsumerdùnghelper|2textnodes đồngnhấtmetadata|Restcard/pageexact3locale|
|Sentineltoàncatalogquárộng|Finite2nodeprojection/oldassertionsgiữ|473+3affectedNodePASS|
|Khôngcówholeappclaim|12native/69Python/476Node scoped|SignedUI/AX/auth/device/motionmở|
|18comparatorlịchsửvẫngiữmetadata trướcđổi|Haitestrendererschiếuđúng4sourcefragmentsđãduyệt|18RED→18PASS;app/customer/control/oldhashgiữ|

## Ngày giờ Chat —đối chiếu15/11/2026

Nguồn:bốn timestampconsumer trong actualrenderChatWorkspaceDetail/
renderChatRunTimeline và dateIIFE thẻroot tạiBASEc048dd7e.

|Hành vi trước|Ứng viên trong phiếu|Bằng chứng/giới hạn|
|---|---|---|
|RawISO ở yêu cầu/nội dung/lần lưu/hoạt động|Format mediumshort theo currentlocale|BASE10RED/native4areas→625PASS/native6|
|DateIIFEroot đãformat|Giữ nguyên từngbyte|RootwholeHTMLsentinel|
|Timestamp/customerISO bị dùng cùng giao diện|Chỉsystemdateconsumer đổi|RawDTO/store/body/title/tag giữ|
|FullPageQA không chụp inner-scroll|Viewportshot có actualdatebox|R1 giữ;R2sixaffectedPASS|
|Oldtestguard ghim source trướcdate|Strict5fragmentinverse trướcmetadata|Khôngoldhash/globalmask|
|Titleunit chưa có receipt trong tài liệu|PR741c048 đãgiao|CI43689932109/deploy43690886966|

## Thẻ tài liệu —đối chiếu15/11/2026

NguồnactualrenderDocumentOperationCards/state/downloadhelpers tạiBASE5bc8;
không bịa featurelist hoặc actualoutput.

|Trước|Ứng viên|Bằng chứng/giới hạn|
|---|---|---|
|7pendingbranches có thuật ngữ nội bộ|Chữ dễ hiểuVIENZH/escapeonce|ActualVM/conditionsgiữ|
|Nhãn vàconfirmationcứngVI|14keysperlocale|DownloadURL/caps/attrs/metrics exact|
|Defaultempty mô tảparser/output|2keysper-call|Actual/splitGETempty,customargsgiữ|
|Wholei18noldguards chưa có23keys|Finite3literaladditioninverse|2FAIL+1expandedgate→3PASS|
|Có thể nhầm fakecompleted vớioutput|Nativechỉactualempty9tables0writes|Nocards/nodownloads/submitblocked|
|DATEcổnglocalđangmởtrongtài liệu trước|PR7425bc8đãgiao|CI43706589548/deploy43707642952|

## Giao diện PDF —đối chiếu15/11/2026

Nguồnactualdocumentpagination/SplitOptimizefields/3PDFrenderers tạiBASEc2fc.

|Trước|Ứng viên|Bằng chứng/giới hạn|
|---|---|---|
|PaginationcứngVI|6labels/ariaVIENZH|Offsets/controlstate/helpersgiữ|
|Sourcefields nêu thuật ngữ nội bộ|7fieldcopykeys dễhiểu|Validation/limits20MB30pages/options/refpickergiữ|
|3noticewrapperkhôngcóaction|Chỉwrapperbỏ/notesrendergiữ|Whole3pages/asideformsrights exact|
|Đã có thẻ tài liệu dịch|Không thay thẻ lần nữa|Oldhash/catalogfreeze/customerkept|
|LIGHTtextnhạttrênwhite|GhiUIreadabilityseparate|Chưađocomputedcontrast,khôngcontrastPASS|
|CARDchưacóreceipttrongtài liệu trước|PR743c2fcđãgiao|CI43709678826/deploy43710852871|

## Thông tin nội bộ —đối chiếu15/11/2026

NguồnthựcBASE206eccc2:renderDocumentHub,renderRouteEngineBoundary,
renderCapabilityHubFamilySummary;catalogue-chínhportal-features.js.

|Trước|Ứng viên|Bằng chứng/giới hạn|
|---|---|---|
|Loading/failedcó6tagtriểnkhai|Bỏ2metarows|Paragraph/retry/rightsstrict exact|
|Familyvẽnoticeđịnhtuyếnkhôngaction|Helpertrảrỗng|Khôngsửaengine/capabilities/normalizer|
|Familyauditdetailsnằmtronghiddenstatusgrid|BỏDOMdetails|KhônggọiđâylàthayđổiUIđangvisible|
|Cataloguebundlecũkháccatalogue-chính|Kiểmownerthậttừserver|Lightentry135cardskhôngđổitrongunit|
|PDFchưaghiđãtriểnkhai|PR744206eccc2đãgiao|CI43713208147/deploy43732595353|
|Readabilitychưacósốđo|4LIGHTfail/4DARKpass|Chỉ2Splitobservations,phiếuCSSriêng|

## Chữ Tách PDF —đối chiếu16/11/2026

NguồnactualCSSBASE44134931vànativecomputedBASE/GREEN6observations.

|Trước|Ứng viên|Bằng chứng/giới hạn|
|---|---|---|
|LIGHTlabel1.265330/help2.021153:1|2rulecolorsemantic|12.351555/5.797099:1thựctế|
|Darkđãđủtươngphản|Khôngđổi|Styles/font/geometryexactBASE|
|MànCompresscùnglỗinhạt|Giữsentinelvàghiđơnvịkế|KhôngclaimđãfixngoàiSplit|
|ChatCSSchainkhóakhứ|Exact2ruleinverseFIRST|Oldhash/wholeCSS/assertionsgiữ|
|DISPLAYchưaghiđãtriểnkhai|PR74544134931đãgiao|CI43737144840/deploy43814377064|

## Thẻ tài liệu —đối chiếu16/11/2026

NguồnactualrenderDocumentOperationCards/datehelper tạiBASEc40f94ce.

|Trước|Ứng viên|Bằng chứng/giới hạn|
|---|---|---|
|FallbacknamesnêuOCR/private|6tênmặcđịnh/2nhãnbiểutượng|Têntệpkháchliteral/formatnamesgiữ|
|Selectedmô tảcứngVI/thuậtngữ|11keysVIENZH|Count/range/languagebranches/coercionsgiữ|
|UpdatedrawISO/malformedstrings|Dùngdatehelperđãcó|Invalid→emDash/prioritygiữ/nopersistedchange|
|Carddateproposalwholefunction|ReplayDATEfirstthennames/selected|Khôngghiđècácunit/compoundinverseexact|
|Cóthểlấynativeemptylàfilledcardproof|FilledfieldactualVM-only|Native0cards/nofakedata/output|
|SplitCSSchưaghiđãtriểnkhai|PR746c40f94ceđãgiao|CI43816413685/deploy43817989559|

## Số liệu thẻ tài liệu — đối chiếu16/11/2026

Nguồn thực tế: renderDocumentOperationCards tại BASE b3c1749f, giữ nguyên
danh sách chức năng gốc đã đối chiếu; đây là thay đổi chữ, không thêm công cụ.

| Trước | Ứng viên | Bằng chứng/giới hạn |
|---|---|---|
| Count/pages có chữ VI cứng ở EN/ZH |13 key theo locale | Actual renderer9kind/521NodePASS |
| Image source ghi private |1 ảnh đã chọn theo locale | Tên tệp khách chứa private vẫn literal |
| Output ghi đã xác minh từ nhãn | Chỉ nêu định dạng khi downloadPath hợp lệ | Không đổi state/capability/download guard |
| EN đếm một tệp có thể sai số nhiều | Năm nhãn label-first trong R1A | Phụ lục người điều phối, không lỗi worker |
| Có thể nhận native empty là output thật | Filled metrics VM-only | Native ba histories thực sự0cards |
| PR747 chưa ghi đã triển khai | PR747b3c1749f đã giao | CI43821671694/deploy43853462350/receipt6910067903 |

## PDF dễ dùng — đối chiếu16/11/2026

Nguồn thực: ba renderPdf functions và theme tại BASE38a92641; danh sách
chức năng gốc giữ nguyên, không thêm engine hay khả năng xử lý mới.

| Trước | Ứng viên | Bằng chứng/giới hạn |
|---|---|---|
| Compress light label/help1.265330/2.021153:1 | Hai semantic colors light-only |12.351555/5.797099:1; font/geometry giữ |
| Guarded giải thích signed/storage/Bot/provider | Hai thông báo locale, bỏ metadata | Whole HTML ngoài hai slots/removal exact |
| Ready forms có copy kỹ thuật | Không đổi trong đợt này | Ghi backlog, không nhận sạch whole PDF |
| Reference-picker header/footer còn chật/dư | Không đổi trong đợt này | Crop Compress thực tế, cần phiếu riêng |
| Có thể giả trạng thái blocked cho ảnh | Không fake API/quyền | Guarded VM-only, native actual ready |
| Metrics chưa ghi đã triển khai | PR74838a92641 đã giao | CI43857216020/deploy43859221752/receipt6915066642 |

## PDF tập trung thao tác — đối chiếu16/11/2026

Nguồn thực:ba renderPdf functions/referencepicker/theme tạiBASE2b126b40.
Danh sáchchức nănggốc giữ,khôngthêm enginehay khả năngxửlýmới.

| Trước | Ứng viên | Bằng chứng/giới hạn |
|---|---|---|
| Intro/asidegiải thíchpipeline,nhiềucộttrống | Formmộtcột,linkkhotệpvàofooter | Wholeoutside/guardedHTML/controls exact |
| Bỏasidecóthểmấtusefullimits | GiữlimitsởdescriptionVI/EN/ZH | CoordinatorAMEND2,khôngworkerfault |
| Referenceheaderdính,emptyfooterlặp | Gap6px/status14px,giữnavigation |556NodePASS/native6actualemptyforms |
| Customerfilenamecótừtechnical | Giữliteral,mộtlầnescape | Immutable/hostiletranslationtests |
| Assumebaselineinputđã16px | Đãđo15px,queuedfont16riêng | NativeR1zeroobs,R2scopeamendment |
| Legacy/losslessassertionfail | Giữ1samefailBASE/branch | Python29PASSboth;khônghiddenfailure |
| PUchưaghiđãtriểnkhai | PR7492b126b40đãgiao | CI43863230530/deploy43865201248/receipt6916141029 |
| CóthểnhậnwholePDFsạchlocale | Mergefields/defaultnotes/toolskháccòn |KhôngwholeAX/signedUI/outputclaim |

## Cỡ chữ nhập PDF — đối chiếu16/11/2026

Nguồn thực: theme CSS tại BASEefe06a29. Không thêm công cụ hay engine.

| Trước | Ứng viên | Bằng chứng/giới hạn |
|---|---|---|
| Control PDF15px ở màn hình nhỏ | Chỉ ba form tăng16px≤767px |42actualmobile samples |
| Control desktop15px | Giữ15px≥768px |28actualdesktop samples |
| Có thể sửa ké theme hoặc logic | Một exact CSS replacement |24protectedLF/allappPython/outside giữ |
| QA observer thiếu metadata tham chiếu | Đọc fixture cũ qua boundSHA | R1zeroobs/R2native15cases,khôngworkerfault |
| Cleanup còn ghi chưa triển khai | PR750efe06a29 đã giao | CI43874550883/deploy43876776533/receipt6917466951 |
| Có thể nhận font là toàn bộ AX đạt | Chỉ actual owned QA font proof | Safari/iOS/locale/signedUI/output riêng |

## Nhãn Gộp PDF — đối chiếu16/11/2026

Nguồn thực:pdfMergeFormFields tạiBASEb9f714e6,khôngthêm engine/chức năng.

| Trước | Ứng viên | Bằng chứng/giới hạn |
|---|---|---|
|8fieldscóVIcứngvàgiải thíchslot/output/signed |7keys21valuesVI/EN/ZH,plainhelp |576NodePASS/native48fields144copyslots |
| Cóthểmấtpositionkhi fallback | DynamicVItemplateđãresolve | Actualfactoryparams1..8 |
| Cóthểxóadấubắtbuộckhiso tênfield | Mark+screenreadertextgiữriêng | Native3locale/first2required |
| Fontunitcònghichưadeploy | PR751b9f714e6đãgiao | CI43880993436/deploy43903263914/receipt6918381914 |
| CopyđúngcóthểbịhiểulàtoànUIđạt | Contrast/toasttechnicalcònriêng | HaiAGYcontracts6922273292/6922273259 |

## Độ rõ chữ Gộp PDF — đối chiếu17/11/2026

Nguồn thực:Merge lightCSS tạiBASE2c7eba2c. Khôngthêmchức nănghayengine.

| Trước | Ứng viên | Bằng chứng/giới hạn |
|---|---|---|
| Merge lightlabel/helpnhạt |2semanticforegroundcolors |32targets1.265330/2.021153→12.351555/5.797099:1 |
| CóthểlấymàutừảnhhoặcSplitbase | TrueMergeactualBASE/GREEN |48textsamplesmỗiphase,opaquepaintproof |
| Cóthểđổifont/layout/darkké | Chỉforegroundlightđổi |24controlsexact/16darksentinels/wholeoutside |
| Copyunitcònghichưadeploy | PR7522c7eba2cđãgiao | CI43908810643/deploy43911268504/receipt6922389994 |
| CropcóthểđượccoinhưfullvisualPASS | Chỉhelp-regionwitness | Label/selectoccluded,wholeUX/AXvẫnmở |

## Thông báo danh sách tệp — đối chiếu17/11/2026

Nguồn thực: hai nhánh thao tác tham chiếu trong integration.js tại BASEeb3ab9a7.

| Trước | Ứng viên có phạm vi | Bằng chứng/giới hạn |
|---|---|---|
| Find/Clear/Page dùng VI cứng và reference/API owner-scoped | Bốn khóa VI/EN/ZH, thông báo gọn theo locale hiện tại | Real handler/hydrator/API/toast trong VM |
| Có thể coi tải lỗi là thành công | Giữ nguyên tiêu chí cũ, vẫn chỉ alert khi lỗi |36typedGET success/failure scenarios |
| Có thể dịch cả tên tệp khách | Chỉ fixedcopy, tên/UUID/metadata giữ literal | Selected/pinned/hostiletext tests |
| Frozen i18n export không thể thay bằng phép gán trong QA | Chỉ đổi ownedwindow test boundary, không sửa app | QA lỗi được ghi rõ, không tính workerfault |
| Stale data guard bị hiểu là stale feedback đã yên lặng | Baseline alert cũ tái hiện, phiếu riêng2edits |28tests8PASS20RED; copyunit không sửa ké |
| Contrast còn ghi chưa triển khai | PR753eb3ab9a7 đã giao | CI43916771242/deploy43919393644/receipt6923402077 |

## Phản hồi đã cũ — đối chiếu17/11/2026

| Trước | Ứng viên | Bằng chứng/giới hạn |
|---|---|---|
| Chốt dữ liệu đã bỏ phản hồi cũ nhưng action vẫn báo lỗi | Dùng lại chính chốt hiện hành trước thông báo |28realVMcases8PASS20RED→newraw30tests |
| Lượt mới hoàn tất trước lượt cũ vẫn có thể thêm alert | Lượt cũ im lặng, không đổi dữ liệu/lượt mới |43NodePASS/8staticPythonPASS |
| Có thể nới quyền hoặc đổi hàm tải khi sửa toast | Chỉ2localcapture+postawaitfences,khôngepochmutation | Exactworker/inverse/outside |
| Unitcopy còn ghi chưa triển khai | PR754cb358cea đã giao | CI43924561893/deploy43926903239/receipt6924690075 |
| UnitVM có thể bị coi là signedLIVE | NativeSPA/read-onlyruntime có gate riêng | Fullauth/device/output/M-FINAL cònmở |

## Hướng dẫn đổi kích thước ảnh — đối chiếu17/11/2026

Nguồn thực là ba dòng có sẵn tại BASE1eefbf29, không phải chức năng ảnh mới.

| Trước | Ứng viên có phạm vi | Bằng chứng/giới hạn |
|---|---|---|
| Mô tả gửi mã tài sản và cấu hình trình duyệt | Hướng dẫn chọn ảnh, kích thước, cách đặt ảnh | Ba locale qua renderer thật |
| Ghi chú giải mã/sao chép/kiểm tra nội bộ | Tệp gốc giữ nguyên, tải PNG khi hoàn tất | Không hứa tác vụ đã hoàn tất |
| Giải thích kỹ thuật về canvas/AI | Cắt giữa, thêm nền trắng hoặc làm mờ nền | Giữ nguyên ba chức năng/nút |
| Có thể dịch cả tên tệp khách hoặc nới quyền | Chỉ chín giá trị chữ cố định | Whole-HTML/control/data/rights comparators |
| Sửa chữ làm hỏng hash lịch sử | Khôi phục hữu hạn đúng ba dòng tại chỗ đọc kiểm tra cũ | Assertions và stale guard giữ |
| Có thể suy kiểm tra chữ thành cả trang đạt | Sáu native ca có giới hạn | Header VI/light contrast còn lỗi cũ; không wholeUI/LIVE |
| PR755 còn ghi chờ triển khai | Đã giao runtime1eefbf29 | CI44025420679/deploy44026819906/receipt6939697009 |

Không coi81Node/sáu native ca là bằng chứng tạo PNG, kết nối Bot hoặc
signedLIVE. Các câu giải thích khác, thiết bị/Safari, vòng đời đăng nhập
và motion vẫn theo checklist riêng.

## Tiêu đề Tách PDF — đối chiếu17/11/2026

Nguồn thực:metadata của `/documents/split` tại BASE4ddd63ce.

| Trước | Ứng viên có phạm vi | Bằng chứng/giới hạn |
|---|---|---|
| HTML đầu dùng tên ứng dụng/mô tả chung | Tên/mô tả riêng ở VI/EN/ZH |6actualserverRED→targetedPASS |
| Giao diện Anh/Trung còn nhãn Việt và thuật ngữ nội bộ | Hai khóa theo ngôn ngữ giao diện |6rawrendererRED→PASS |
| Có thể đổi nhầm công cụ khác hoặc tên tệp khách | Chỉ hai nhánh route chính xác | Other-route wholeHTML/header/customer comparators |
| So sánh cũ không hiểu hai khóa mới | Projection hữu hạn đúng phần metadata | Oldassertions/hashes/order giữ |
| Lỗi bộ đo bị tính thành lỗi worker | Ba lỗi harness được ghi riêng |90PASS/5FAIL→chỉ5affectedPASS |
| Nhóm hướng dẫn ảnh còn ghi ứng viên | PR756 đã giao | CI44031412556/deploy44033266452/receipt6940613584 |

Không thêm tính năng, không chạy xử lý PDF hoặc mở quyền/backend/engine.
Native/exactCI/phát hành/signedLIVE và toàn bộ goal có bằng chứng riêng.

## Đổi kích thước ảnh — đối chiếu17/11/2026

Nguồn thực:renderImageResize và metadata của `/image/resize` tại BASE93b41f52.

| Trước | Ứng viên có phạm vi | Bằng chứng/giới hạn |
|---|---|---|
| Header/HTML đầu dùng tên tiếng Anh hoặc mô tả chung | Hai khóa/sáu giá trị metadata VI/EN/ZH |9clientRED và6serverRED;rawsource/nativeHTML |
| Nhãn/hướng dẫn sáng quá nhạt | Hai rule màu semantic đúng route, không đổi tối/font/layout |30lighttargets1.265330–2.021153→5.797099–12.351555 |
| Khối cuối kể Bot/provider/ví/PayOS/webhook | Xóa toàn bộ notice/notes section, lịch sử vẫn là phần cuối |DOM/wholeoutside/control comparators |
| Có thể đổi tên/nội dung khách hoặc quyền khi dọn chữ | Ngoài bảy substitutions giữ nguyên |679Node,30nativecontrolpairs/exactsource |
| Màu chữ đổi kéo theo currentColor border không nhìn thấy | Bộ so sánh phân biệt border0pxnone với border thật |Chỉ sửa QA comparator,không sửa app/rerun native |
| PR757 còn ghi ứng viên | Đã giao runtime93b41f52 |CI44071806148/deploy44074756251/receipt6941948619 |

Không gọi toàn bộ trang đã sạch thuật ngữ:canvas/preset và phần chữ còn lại
thuộc phiếu tiếp theo. Không thêm tính năng hoặc đổi engine/quyền/giá/ví.
SignedUI/finalPNG/device/Safari/auth/motion và wholegoal vẫn mở.

## Câu chữ Resize — đối chiếu17/11/2026

Nguồn thực:IMAGE_OPERATION_COPY_ROWS và các consumer Resize tạiBASEb6c717bc.

| Trước | Ứng viên có phạm vi | Bằng chứng/giới hạn |
|---|---|---|
| Câu tải/lỗi kể cơ chế nội bộ | Thông báo ngắn,hướng dẫn thử lại,giữ trạng thái thật |Rawguard/loading/failed/permissioncases |
| Canvas/preset/AI disclaimer trong hướng dẫn | Kích thước ảnh,tùy chỉnh,cắt/thêm nền |33rows/raw99slots/native144consumerchecks |
| Đề xuất câu “tự điền ô” không đúng nguồn | Kích thước có sẵn không cần nhập ô tùy chỉnh |Actual9:16clears+disables/customrestoreschecks |
| Cùng nhãn Resize xuất hiện trong Lịch sử ảnh | Ba intendedlabels cập nhật đồng bộ,không đổi hành vi |3wholeHTMLinverses/controls/title comparators |
| Test cắt form ở section tìm ảnh lồng | Chỉ sửa reader,nút thật vẫn kiểm đủ |3BASE RED→3GREEN,noapprepair |
| Text chưa cuộn tới bị tính là cắt | Scroll thật từng node rồi đo |120nativevisibilitychecks,no threshold widening |
| PR758 còn ghi ứng viên | Đã giao runtimeb6c717bc |CI44081274590/deploy44083777023/receipt6947295414 |

Không thêm tính năng,không tạo PNG,không đổi engine/auth/giá/ví.
Sharedsource/commoncopy và metadatachips còn được ghi riêng,không giấu thiếu sót.

## Nhãn công cụ ảnh dùng chung — đối chiếu18/11/2026

Nguồn thực: IMAGE_OPERATION_COPY_ROWS và renderImageResize tại BASEce40bf40.
Đây là thay chữ/bớt phần giải thích dư, không thêm năng lực xử lý ảnh.

| Trước | Ứng viên đúng phạm vi | Bằng chứng và giới hạn |
|---|---|---|
| Canvas, Asset Vault, PNG riêng tư trong thao tác thường | Kích thước ảnh, kho tệp, ảnh PNG; VI/EN/ZH riêng | 21 hàng/63 giá trị, khóa và thứ tự giữ |
| Tải dữ liệu kể cơ chế riêng tư và bảo vệ nội bộ | Đang tải/chưa tải được/thử lại, giữ lỗi thật | Dựng full bundle ở trạng thái thật của renderer |
| Hai cụm ba nhãn xác thực/cache/fallback lặp ở Resize | Bỏ nguyên div, không thêm khung trống | Chín ca VI/EN/ZH giữ h2/p/state/quyền/retry |
| Một khóa openVault có bản giống ở mảng khác | Chỉ đổi bản thuộc IMAGE_OPERATION_COPY_ROWS | Neo mảng/OLD khớp một lần, đối chiếu byte ngoài |
| Test đếm mọi div rỗng và xem hero-actions là khung mới | So danh sách div rỗng với BASE, không nới điều kiện xóa chip | Chín ca chạy lại, không đổi ứng dụng |
| PR759 còn mô tả ứng viên | Đã giao runtimece40bf40 | CI44089896015/deploy44092746398/receipt6949503144 |

Các utility khác vẫn có mô tả kỹ thuật ngoài 21 khóa này; phụ đề kết quả còn
giá trị custom chưa được xử lý trong nhóm. Không nhận toàn locale/UX đã xong.
Không đổi Bot, đường engine, auth, ENV, dữ liệu, giá/ví/PayOS hoặc provider.

## Ô nhập Resize — đối chiếu18/11/2026

Nguồn gốc: grid .portal-fields/.portal-field trong portal.css và form Resize.

| Hành vi cũ đã đo | Ứng viên | Giữ nguyên |
|---|---|---|
| Preset desktop131,828125px theo vùng tìm ảnh | align-content:start;native select44px/input44,5px | Chiều rộng,5field,option/giới hạn/quyền |
| Mobile44px | Giữ44–44,5px qua3locale | Nội dung,flow,không submit |
| Comparator lịch sử khóa theme cũ | Đảo hữu hạn đúng addition mới tại biên đọc QA | Assertion/hash/mutation cũ,byte ngoài |

Không thêm công cụ hoặc năng lực tạo ảnh.12geometry và6native chỉ chứng minh
bố cục/điều khiển được kiểm;CI/deploy/LIVE/PNG cuối là các cổng khác.

## Nén PDF — đối chiếu18/11/2026

Nguồnhiệnhữu:/documents/compress,renderPdfOptimize,shellmetadata dictionaries.

| Trước | Ứng viên | Phần giữ nguyên |
|---|---|---|
| Shell còn tiêu đề workspace chung |3locale cóNénPDF/title/descriptiontừtảiđầu |Route/bootstrapallowlist/auth |
| Helper chưa mapping riêng Compress |2exactroutebranches/twokey6values |Signature/order/cácroutekhác |
| Formnénđãvận hành |Metadatađúngkhôngthayform |Controls/options/limits/source/customertext |
| Goldennguồnđãkhóa3tệp |Đảohữuhạn5additionởbiênđọctest |Oldassertions/hash/unknownoutside/mutations |

Không thêmkhảnăngnén,khôngtạokếtquảPDFtrongQAhoặcgọiprovider.
Browserfixturemetadatađạt khôngthaynativefullshell/CI/deploy/finaloutput.

## Ảnh thành PDF — đối chiếu18/11/2026

Nguồn hiện hữu: renderImageToPdf; không thêm công cụ hoặc sửa xử lý tài liệu.

| Trước | Ứng viên đã kiểm | Giữ nguyên |
|---|---|---|
| Guard cố định tiếng Việt, lẫn thuật ngữ triển khai | Hai khóa VI/EN/ZH sẵn có, một tiêu đề/một câu hướng dẫn | Điều kiện canView === true |
| Ba nhãn kỹ thuật trong guard | Bỏ đúng ba nhãn, không ô rỗng thay thế | Không thêm form hoặc nút xử lý khi bị từ chối |
| Form được phép có tám ảnh nguồn | Whole HTML/control/context giữ byte-exact | Quyền chạy/làm mới, tên tệp/nội dung khách |
| Comparator cũ đọc bundle trước thay đổi | Đảo hữu hạn đúng một return tại biên đọc QA | Hash/assertion/mutation và byte ngoài |
| Nén PDF còn ghi chờ phát hành | PR762 đã giao runtime6c8e2b22 | Receipt6969229851, deploy44241082812 |

Sáu lượt native guarded là trạng thái server QA tạm thật; không chứng minh
READY native hoặc PDF đầu ra. READY được khóa bằng renderer parity ba ngôn ngữ.
Tiêu đề/mô tả ngoài guard còn thiếu bản địa hóa, ghi backlog metadata riêng.

## Hướng dẫn chỉnh ảnh — đối chiếu18/11/2026

Nguồn hiện hữu: IMAGE_OPERATION_COPY_ROWS, renderImageEnhance và các
consumer sẵn có. Không bổ sung công cụ/năng lực xử lý.

| Trước | Ứng viên đã đo | Giữ nguyên |
|---|---|---|
| Sáu đoạn nói ID/thuật toán/băm/phiên/cache | Sáu hướng dẫn thao tácVI/EN/ZH | Sáu khóa/vị trí,18giá trị có nội dung |
| Lẫn giải thích triển khai vào giới hạn | Vẫn2x/4096/16triệu điểm ảnh, không thêm chi tiết | Tệp gốc và thứ tự xử lý |
| Form/nguồn/giá trị tùy chọn sẵn có | FullHTML/context3locale×8state giữ ngoài sáu đoạn | Controls/giới hạn/quyền/tên riêng/customer |
| Catalogue cũ bị khóa | Đảo hữu hạn đúng sáu dòng/giá trị tại biên đọc QA | Hash/assertion/order/byte ngoài/mutation cũ |
| Guard Image-to-PDF còn chờ cập nhật | PR763 đã giao runtime39a3fb9e | Receipt6969883472/deploy44245453666 |

12ca mục tiêu và385ca liên quan đạt. Native/CI/runtime của ứng viên vẫn
riêng; không suy UI thành xử lý ảnh hoặc PNG cuối.

## Ảnh thành PDF — tiêu đề/mô tả18/11/2026

Nguồn hiện hữu: /documents/image-to-pdf,renderImageToPdf,
localizedPageTitle/Description và shellmetadata dictionaries.

| Trước | Ứng viên đã đo | Giữ nguyên |
|---|---|---|
| FirstHTML là workspace chung | VI/EN/ZH có title/description riêng | Bootstrapallowlist/auth/lang |
| Hero còn tiếng Việt/thuật ngữ trên EN/ZH | Hai exactroutebranches/two keys sixvalues | Helper signature/order/route khác |
| Guard đã bản địa hóa PR763 | Whole HTML ngoài hero giữ,0mởformkhi bị từ chối | Hai khóa guard và ba chip đã bỏ |
| Formtámnguồn/rights/actions sẵn có | Controls/context/customer giữ | Không mở xử lý PDF hoặc provider |
| ReaderCompress dựa toànOLD+addition | Chỉ đảo năm addition của chính Compress trong RAM | Source vật lý/newmetadata/authority/hash/assertions |

Không thêm khả năng tạo PDF.18Python và399+22Nodeca chỉ chứng minh
phạm vi đã kiểm; native/live/thiết bị/Safari/PDF cuối là gate riêng.

## Chỉnh ảnh — tiêu đề/mô tả18/11/2026

Nguồn hiện hữu:/image/edit,renderImageEnhance,localizedPageTitle/Description,
shell dictionaries. Không thêm năng lực hoặc thay engine.

| Trước | Ứng viên đã đo | Giữ nguyên |
|---|---|---|
| FirstHTML là workspace chung | VI/EN/ZH có title/description riêng | Bootstrapallowlist/lang/auth |
| HeroVI còn Image Enhance Studio/EN/ZH lẫn ngôn ngữ | Hai exactroutebranches/two keys sixvalues | Chữ ký helper/thứ tự route |
| Sáu hướng dẫn PR764 đã giao | WholeHTML ngoài hai hero nodes không đổi | Form/controls/quyền/ảnh nguồn/customer |
| Golden metadata cũ đã khóa | Đảo đúng fiveaddition/two keys ở biên lịch sử | Hash/assertion/unknownoutside/mutations |
| Ảnh thành PDF còn ghi chờ phát hành | PR765 đã giao runtimeb9815725 | Receipt6971500533/deploy44256934807 |

423Node và30Python đạt;native/CI/runtime riêng,không chứng minh PNG cuối.

## Chỉnh ảnh — màu chữ ba bước18/11/2026

Nguồn hiện hữu:.portal-project-steps,strong/span vàsemantic --portal-ink.

| Trước đã đo | Thay đổi được giao | Giữ nguyên |
|---|---|---|
| Ba lightviews có18mismatches,headingrgb236251255/bodyrgb143169181 | Một rule scopedEnhance/light dùng token#073a45 đo tại node | Text/font/geometry/layout |
| Dark3views có màu riêng | Selector không áp dụng dark | Sáu màu tối/textfill |
| Form và nguồn ảnh sẵn có | Không đổi HTML hoặc hàm xử lý | Capabilities/readstates/controls/customer |
| Comparator theme cũ khóa hash trước addition | Đảo hữu hạn đúng addition tại biên lịch sử | Goldenhash/assertions/outsidebytes/mutations |
| Metadata còn ghi chờ phát hành | PR766 đã giao runtimec1fdd4bf | Receipt6972711440/deploy44283897180 |

Không thêm công cụ hoặc xử lý ảnh. Không suy semanticcolor equality thành
toàn AX hoặc tỷ lệ tương phản trên nền gradient đã được chứng minh.

## Đổi kích thước — nhãn lựa chọn18/11/2026

Nguồn hiện hữu:renderImageOperationCards,renderImageHistoryOperationCards,
field.resize.preset.custom. Không đổi preset/fit_mode được lưu.

| Trước đã đo | Thay đổi được giao | Giữ nguyên |
|---|---|---|
| Stringcustom hiển thịraw cả3ngônngữ | Tokenknowncustom/fallback qua existingkeyVI/EN/ZH | Chín tỷ lệ/unknown/customerliteral |
| Hai consumer current/history khác vị trí | Hai inlineconditional cùng logic | NonResizehistoryconstpreset |
| Fullrenderer8case4RED4protectedPASS | Bổ sungGREEN/source/negativecases | UUID/state/dates/geometry/downloads/form/context |
| Golden nguồn trước thay đổi | Finiteleaf đúng hai substitutions | Hash/assertions/byte ngoài |
| Màu Chỉnh ảnh còn ghi chờ phát hành | PR767 đã giao runtime979b80d2 | Receipt6976220745/deploy44290989110 |

Không gọi xử lý ảnh hoặc nhậnđầu PNG/signedUI/wholelocale/AX/motion.

Phụlục cùng lỗi:actualnativeVI375đãdịchnhãnnhưngCSSBASE1241
nowrap/hidden/ellipsis cắtphầncuối. Parentchưapháthành.
Thêm1CSSrule AntigravityR1 scopedResize/historycard-subtitle để
normal/anywhere/visible/clip;khôngđổitext/font/width/dữliệu.
NonResizehistorysubtitle cũngđượcphéptăngchiềucaotựnhiên đểđọcđủ,
khôngđổiHTML/content/state/download. Combined2appfiles149protected,
3canonicaledits;56CSSaffectedPASS.
Nghiệm thuR5đủ12màn/48phụđề đọcđủ/48ảnh,giữmetadata/form/rights/
ownership/audit/schema/core/source151;28tiếntrìnhsởhữudừng0.
R4lỗiđiềukiệnchờKho tài sản ởHistory đượcRoot sửađúng2điềukiệnQA;
khôngđổiapp hoặc nớivisibility. CI/runtime/signedUI/finalPNG vẫnriêng.

## Chỉnh ảnh — tiêu đề hướng dẫn18/11/2026

Nguồn hiện hữu: sáu heading trongrenderImageEnhance và
IMAGE_OPERATION_COPY_ROWS;không đổi chức năng chỉnh ảnh.

| Tài liệu/chữ cũ | Hành vi ứng viên | Ranh giới giữ |
|---|---|---|
| Tiêu đề mô tả Web/verifiability/private delivery | Sáu headingVI/EN/ZH viết cho người dùng | Sixbodyparagraphs/meta/form/rights |
| Metadata Chỉnh ảnh đã dịch | Giữ nguyên tên trang/mô tả/header | Customerliteral/keys/order/route |
| Heading trùng tên ảnh do khách đặt | Chỉ đổi sáu node cố định | Không thay chuỗi toàn cục trong tên ảnh |
| Snapshot nguồn cũ | Finite6rowleaf tại biên lịch sử | Goldenhash/assertions/unknownoutside |
| Resize còn ghi chờ phát hành | PR768đã giao runtimebe8015ad | CI44301447174/deploy44304009103/receipts |

BASE21cases7RED14PASS;source1changed150protected6edits.
Nhóm ứng viên/native/CI/delivery vẫn phải có output riêng.

Ứng viên đã đo1525PASS/1BASE-equivalentoldreaderFAIL;
reader-onlyfix giữassertions,4PASS,no passinggrouprerun.
NativeR2đủ6views/54metadatahelp+36headingpaint/18shots,22ownedstopped0,
rights/body/source/audit/schema/coreheld. R1edgehit→realcenter-scrollQA,
khôngđổiapp. Khôngsuycandidategeometry thànhBASEequality hoặcwholepage.

## Đổi kích thước — nhãn kết quả, 18/11/2026

Nguồn đối chiếu là hai dòng `result.resize.subtitle` và
`result.history.operation.resize` đang tồn tại; không thêm chức năng.

| Chữ/hành vi cũ | Ứng viên | Ranh giới giữ |
|---|---|---|
| Đổi canvas / Canvas resize / 调整画布 | Đổi kích thước / Image resize / 调整尺寸 |Đúng hai nhãn cố định |
| Phụ đề thẻ và ô loại thao tác |Cùng nhãn theo locale hiện tại |Placeholder/fit/preset/customer giữ |
| Test RSC cũ chờ prefix cũ |Đổi đúng ba expected literals |Renderer vật lý/mọi assertion/vector giữ |
| Golden nguồn lịch sử |Inverse hữu hạn đúng hai dòng ở biên lịch sử |Hash cũ và byte ngoài phạm vi giữ |

BASE7RED/7PASS; ứng viên1566PASS/0FAIL; native12màn/48caption/48ảnh.
Không nhận processing-output/signedproduction hoặc toàn trang đã sạch.
CI/merge/deploy/runtime/assets phải có bằng chứng riêng.

## Chỉnh ảnh — đối chiếu đúng chức năng,19/11/2026

Nguồn gốc:renderImageEnhance,IMAGE_OPERATION_COPY_ROWS và menu4route tại
GitBASEf8932643;không thêm tính năng xử lý ảnh hoặc sửa engine.

| Chữ/hành vi cũ | Ứng viên | Ranh giới giữ |
|---|---|---|
| Preset/Cinematic/LANCZOS/UnsharpMask trong fixedcopy |Câu dễ hiểuVI/EN/ZH |20keys/mã/options/bounds/customer |
| Intro/aside/notice/notes dài |Hero/nav/form/history,khôngôtrống |Guard/action/pagination |
| Kho tệp trong khung bên |Giữ trong chân form |Href/quyền |
| Bốncardmobile≥96px+nhiềuchữ |Bốndòng≥44px/tênđủ/viềnchọn |Nativehref/tabIndex/aria-current |
| Badge đã ẩn ởBASEtheme |Tiếp tục ẩn |Không bật nhãn kỹ thuật lại |
| BộcũHelp/Headings bảo vệ6khối đã bỏ |Phânloại rõ historicalcomparator |Golden/assertion/negative giữ |

CurrentUI dùng physical/native riêng,không projection. PDF PR774 đã giao;
không phát hành đồng thời hai đơn vị hoặc nhận signedproduction/output.

## PDF — đối chiếu đúng chức năng,19/11/2026

Nguồn gốc dùng cho đơn vị này là các hàm đang có tại GitBASE513557a9:
imageToPdfFormFields, renderPdfOptimize và renderImageToPdf. Không tuyên bố
có thêm tính năng chuyển đổi hoặc xác minh output trong đợt câu chữ.

| Chữ/hành vi gốc | Ứng viên | Ranh giới giữ |
|---|---|---|
| renderNotes cuối Nén PDF | Bỏ đúng một lời gọi | Factory/config/trang khác |
| Tám nhãn/help hardcodedVI | Sáu khóaVI/EN/ZH | Names/IDs/first-required/options |
| Intro/aside/notice/notes kỹ thuật | Chỉ hero/form/history, không ô trống | Guard/action/data/pagination |
| Liên kết Asset Vault ở khung bên | Mở kho tệp trong chân biểu mẫu | Route và quyền |
| Catalogue sau freeze không thể ghi | Đăng ký15khóa trước keyset/freeze | Kiểm keyset và bất biến |
| Golden kiểm nguồn lịch sử | Finite4editinverse tại comparator | Hash/assertions/unknownbytes |

Physical14/source11PASS; native48view/96PNG/192nhãn/87owned0. Không nhận
deployed/signedproduction/output/wholelocale hoặc motion từ các kiểm tra này.

## Lịch sử ảnh — thông báo trạng thái, 19/11/2026

Đối chiếu sáu dòng history.guard/loading/failed.title/body hiện hữu,
không thêm chức năng hoặc đổi thứ tự nhánh.

| Chữ/hành vi cũ | Ứng viên | Ranh giới giữ |
|---|---|---|
| Giải thích nội bộ khi chưa đọc được lịch sử |Thông báo ngắn, hướng dẫn chờ/thử lại |Quyền/nhãn phụ/retry/dữ liệu |
| GET tự thử lại tối đa3lượt |Giữ nguyên, không phải chức năng mới |Một lỗi tạm thời có thể tự hồi phục |
| Golden nguồn lịch sử |Inverse hữu hạn đúng6dòng |Hash cũ/assertions/unknownoutside giữ |
| Danh sách sẵn sàng và trang bên cạnh |Toàn HTML không đổi |Customer/UUID/state/downloads/form |

BASE13RED/8PASS;candidate1590PASS/0FAIL. NativeR1lỗi kỳ vọng bài kiểm tra,
không tính Antigravity sai;R2đi hết4failedGETrồiretry thật.
Các chữ ready/empty và khung thừa là đơn vị tiếp theo,không nhận đã xong.

## Thiết kế ảnh — đối chiếu phản hồi đọc dữ liệu, 22/11/2026

| Hành vi ở BASE `ef3643d84c269aa2a07e411debe400a44f72d8e6` | Ứng viên | Giới hạn |
|---|---|---|
| Làm mới, lọc, xóa lọc, chuyển trang có thể báo thành công sau lỗi đọc | Chỉ báo thành công khi lượt đọc hiện tại sẵn sàng; lỗi hiển thị thất bại | Giữ hàm tải, quyền, API và dữ liệu |
| Phản hồi cũ vẫn có thể tạo thông báo | Bỏ thông báo khi đường dẫn, phiên hoặc lượt đọc tương ứng đã đổi | Không hủy yêu cầu mạng |
| Lỗi kiểm tra bộ lọc đã lưu có thể xuất hiện trước khi đánh số lượt đọc | Giữ lỗi cụ thể và ngăn lượt đọc trước ghi đè | Không khẳng định đã sửa các tranh chấp khác |
| Thông báo cố định chưa đủ ngôn ngữ | Năm thông báo có Việt, Anh và Trung | Không dịch nội dung do khách nhập |

PR #795 đã triển khai; ứng viên phản hồi đọc đang chờ các cổng phát hành.
Màn chờ chi tiết và kiểm tra giao diện production sau đăng nhập vẫn mở.

## Chi tiết ảnh — đối chiếu chờ và bản đang sửa, 22/11/2026

Nguồn đối chiếu là bản đang triển khai `e177ce5f5791fd22e517d95706331051223e0ccb`.

| Hành vi gốc | Ứng viên | Bằng chứng và giới hạn |
|---|---|---|
| Mở chi tiết có thể hiện thông báo chưa mở được khi đang tải | Hiện thông báo chờ riêng trước khi tải xong | 12 tình huống điều hướng trước sửa; 36 màn sau sửa |
| Chữ tiêu đề chờ nhạt trên nền sáng | Dùng màu chữ hiện có trong phạm vi màn chờ chi tiết | 1,046→12,352:1; tối giữ 13,903:1 |
| Vẽ lại cùng trang lấy các trường đã lưu, mất nội dung đang gõ | Giữ độc lập các trường được phép khi phiên, biểu mẫu và phiên bản khớp | Trước sửa 8/8 mất nội dung; sau sửa 20 tình huống trình duyệt đạt |
| Biểu mẫu có mã trùng có thể bị gán nhầm bản đang sửa | Bỏ khôi phục mọi biểu mẫu có nhận dạng mơ hồ | Hai tình huống mã trùng trên hai nhóm đường dẫn |
| Giá trị chọn không còn khả dụng | Chỉ khôi phục lựa chọn còn có và còn bật | Sáu tình huống xóa/vô hiệu lựa chọn |
| Lỗi đọc, rời trang hoặc dữ liệu đổi phiên bản | Còn mở, cần xử lý riêng | Không dùng kết quả cùng phiên bản để đóng các trường hợp này |

## Thiết kế ảnh — đối chiếu ngôn ngữ nhãn, 23/11/2026

BASE là runtime `d165bad407a51a8cf6339b019a073f8a1a1eb37a`.

| Hiện trạng BASE | Ứng viên | Ranh giới giữ |
|---|---|---|
| Chi tiết Studio/Hub dùng tiêu đề và mô tả lẫn ngôn ngữ | Ba khóa chung cho title/description/section, áp vào hero/breadcrumb | Chỉ hai layout chi tiết |
| 24 câu thư viện chứa giải thích kỹ thuật | Câu ngắn hướng dẫn tìm/chọn/mở công cụ | Giữ key, trạng thái không thể chọn và dữ liệu khách |
| Chín trường phương án hardcode chữ Việt/Anh | 19 khóa VI/EN/ZH cho label/hint/help/empty choice | Names/order/required/limits/options/values giữ |
| Lựa chọn không dùng ảnh gốc có ghi chỉ phù hợp Create | Dịch rõ chỉ khi Tạo mới | Không làm mất yêu cầu ảnh gốc của các loại khác |
| 16/32 mẫu tiêu đề thẻ sáng quá nhạt | Một rule màu giới hạn ở chi tiết ảnh sáng | Geometry và màu tối giữ nguyên |

Đối chiếu hiện vật mới có 32 record, 22 khóa thêm và 24 hàng thay câu.
Không suy ra khả năng tạo ảnh hay trạng thái provider từ thay đổi này.

## Thiết kế ảnh — đối chiếu tiêu đề gốc và màu thẻ, 23/11/2026

BASE đã triển khai qua PR #798 tại `3d21e950fb8e676ffd0b8c945a5ff6d9c8425736`.

| Hiện trạng BASE | Ứng viên đã kiểm cục bộ | Ranh giới giữ |
|---|---|---|
| Trang gốc dùng tên Anh và mô tả Việt pha Anh ở cả ba locale | Hai nhánh metadata riêng và hai key VI/EN/ZH | Chỉ `/image-studio`; route khác giữ |
| Hub có mô tả EN/ZH kỹ thuật và nhãn tham chiếu cũ | Bốn hàng library đổi câu cố định | Không thay key, phân trang, điều kiện chọn hoặc tên khách |
| 18/36 mẫu tiêu đề thẻ gốc sáng không đọc rõ | Mở rộng một rule màu sáng sẵn có,36/36 đạt | Geometry/background/dark foreground giữ |
| Purity test thô có115keys nhưng kỳ vọng lịch sử93, đã lỗi trên BASE | Projection hữu hạn trước assertion lịch sử | Giữ93/38, regex và action assertions; test mới kiểm raw source và mọi key |

Không đổi khả năng xử lý ảnh, quyền, provider, giá hoặc dữ liệu. Chưa dùng
kết quả cục bộ để kết luận toàn-app locale/AX/auth/device hoặc đã triển khai.

PR #799 đã triển khai; biên nhận Issue689/7094535782 ghi đủ CI/deploy/
runtime/5+5assets. Trạng thái chưa triển khai ở trên là lịch sử trước phát hành.

## Thiết kế ảnh — đối chiếu thông báo nhập liệu, 23/11/2026

BASE/runtime5a95e48c9df922cc19a4bd83dfef46f2d85c04d2.

| Hành vi trên BASE | Ứng viên | Ranh giới giữ |
|---|---|---|
| Thông báo kiểm tra đầu vào lẫn Việt/Anh và từ kỹ thuật |51key VI/EN/ZH, câu ngắn chỉ thao tác có thật |Điều kiện từ chối, regex và giới hạn giữ |
| Tên trường cũ được nối thẳng vào lỗi |Allowlist25 nhãn tĩnh chỉ dịch ở nhánh lỗi |Nhãn lạ/nội dung khách giữ, không thay dữ liệu |
| Số lớn hiển thị theo Việt ở mọi locale |Dùng formatNumber đang có cho lỗi |Giá trị và kiểu dữ liệu trong payload giữ |
| Cảnh báo dùng chung có thể bảo Composer chọn ảnh dù chỉ nhận chữ |Yêu cầu bỏ đường dẫn rồi thử lại ở cả ba locale |Không đổi detector/route/chức năng |
| Test nguồn cũ dùng câu chữ lịch sử |Inverse đúng30record, intent trùng được khóa theo từng hàm |Giữ assertions và phát hiện thay đổi ngoài hợp đồng |

Không thêm tạo ảnh, lưu ảnh, provider hoặc khả năng thanh toán. Các nhãn
Composer còn pha Anh và thông báo hành động là việc tiếp theo, chưa được
đóng bởi bản sửa riêng thông báo nhập liệu.

PR #800 đã triển khai tại `a8cf07490448548a2a1be6800fb7e146abeac726`;
CI45551291541, deploy45553790822 và receipt689/7153868208 tách riêng,
không dùng bản trước sync main làm bằng chứng phát hành.

## Công cụ miễn phí — đối chiếu màu chữ/nền, 25/11/2026

| Hiện trạng BASE PR800 | Ứng viên đã kiểm | Ranh giới giữ |
|---|---|---|
| Tab dùng nền cố định nhưng chữ đổi theo theme; tab chọn có cặp màu khó đọc | Cặp nền/chữ riêng sáng/tối, 640/640 mẫu ở 32 trạng thái đạt 4,5:1 | Tên tab, thứ tự, chọn bằng bàn phím, hình học và font giữ |
| Một số nhãn, ô nhập, nút và số liệu khó đọc | 278 mẫu chữ đang bật đo được đều đạt; tám phần tử vô hiệu giữ nguyên | Không đổi phép tính, giá trị, thuộc tính hoặc hành động |
| Khung QR kế thừa nền/chữ không đồng bộ | Chỉ đổi cặp màu khung ngoài và tiêu đề | Nền QR bên trong vẫn trắng; thuật toán và thông tin không đổi |
| Probe focus sớm thiếu ngữ cảnh gợi ý cần thêm `!important` | ArrowRight thật ở tám view đạt, thấp nhất 11,7725:1 | Không áp dụng amendment không cần thiết |

Chỉ chín record/ hai tệp ứng dụng, không phải thiết kế lại trang. Không
thay chức năng, provider, quyền, ví hoặc dữ liệu. Chỉ kiểm thân panel
ban đầu; output/lỗi sau hành động, toàn ứng dụng, Safari/thiết bị thật và
giao diện production sau đăng nhập chưa được chứng minh bởi đợt màu.

Nhánh màu đã giữ thêm UI danh mục/tiện ích của PR810 tại0a9022ce.
Đây là phần kế thừa, không phải record màu mới. So nguồn vật lý vẫn
đòi main cố định+đúng9record; QA ba record catalog chỉ phục vụ so lịch sử,
không bỏ byte lạ hoặc đổi assertion. Bằng chứng sau ghép538Node/98Python;
không mở rộng kết luận tới Bot/API/provider hoặc production interaction.

PR #809 đã phát hành tại `6ec003dbf8f80739f5fb93ff7bd1d7cc703c6792`;
CI45662670051, deploy45667062174 và hai receipt689/7169893110,
PR809/7169894142 là bằng chứng cuối của đợt màu, thay trạng thái chờ
lịch sử phía trên; chưa thay bằng chứng signed production UI.

## Soạn mô tả ảnh — đối chiếu với BASE PR809, 26/11/2026

| Hành vi trên BASE | Ứng viên đã kiểm | Ranh giới giữ |
|---|---|---|
| Nhãn, trợ giúp và khung dùng Việt pha Anh hoặc chữ Việt ở locale khác | 85 khóa giao diện và 15 khóa phản hồi VI/EN/ZH; sáu nhãn điều hướng cập nhật | Bảy trường, 20 option values, route, quyền và giới hạn giữ |
| Câu mẫu tiếng Việt do Web dựng có từ Anh cố định | 19 record câu cố định được dịch; builder thật kiểm 26 tổ hợp | Tiếng Anh bằng BASE và nội dung khách nguyên vẹn |
| Biên nhận bị mất facts đã xác minh giữa integration và renderer | Một return-object giữ lại đúng các facts đã được kiểm | Predicate, whitelist, CSRF, quyền và luồng ghi không đổi |
| Ghi chú mới có tiêu đề/heading và đuôi kỹ thuật | 24 nhãn VI/EN, chọn theo ngôn ngữ mô tả; 110 ca formatter đạt | Category/tags/index/idempotency/ownership giữ, không sửa note cũ |
| Ô Mục tiêu riêng vẫn hiện khi không sử dụng | Chỉ hiện và bắt buộc ở lựa chọn riêng, ẩn thì không vào FormData | Giữ giá trị DOM khi mở lại; không thêm lưu trữ hoặc bản nháp |
| Nhãn tối, ví dụ ô nhập và viền sáng thiếu tương phản | 48 view nguồn vật lý đạt; chữ min5,4733, placeholder min5,5225, focus min5,8601 | Chỉ scope Composer; viền 2px, không đổi CSS chung hoặc motion |
| Ô chỉ số/giải thích dư làm trang có cột trống | Khung một cột, không còn các ô dư đã liệt kê | Tính năng, trạng thái thật và output mô tả không bị ẩn |

Nguồn nghiệm thu so raw BASE cộng đúng 53 record, không dùng inverse
để che lỗi hiện tại. Inverse hữu hạn chỉ phục vụ assertions lịch sử,
giữ byte/key lạ và từ chối bản ghi thiếu/lặp/đã sửa. So 18 trường hợp
ở sáu route khác, ba ngôn ngữ, giữ title/attributes/control markup.
Không thêm khả năng tạo ảnh, gọi engine/provider hay ghi dữ liệu thật.
HTTP/CI/merge/deploy/runtime và signed production vẫn là bằng chứng
riêng; không dùng unit/component PASS thay cho các cổng này.

Composer đã khép phát hành ở PR811/CI45762823823/deploy45765839822,
runtime1a57e621; hai receipt689/7184206269 vàPR811/7184206373 đọc lại.
Các trạng thái chờ ở mục trên là lịch sử trước phát hành.

## Nhãn native và banner tiện ích — đối chiếu BASE PR811

| Hành vi BASE | Ứng viên | Ranh giới giữ |
|---|---|---|
| Tên trống hiện một câu trạng thái phiên tiếng Việt ở nhiều locale | Header dùng Tài khoản; lời chào bạn/there/您 | Tên thật/precedence/trim80/escape/auth giữ |
| Slider Voice dùng key thiếu namespace nên nhãn truy cập còn Việt | Hai key thêm voiceUi namespace đã có | Numeric/range/disabled/payload và renderer chung giữ |
| Banner tiện ích hardcode Việt pha Anh ở cả ba locale | 13 key,39 giá trị VI/EN/ZH | Chế độ/thiết lập/SubDub draft/authoring guards giữ |
| Link Store thiếu mã tiện ích,301vềhomepage | Bỏ riêng CTA sai; giữ gói ZIP tải thật200/CRC9file | Không đổi ZIP/API/extensioncode; không tự thêm URL mới |
| Hai CTA cao24px,108mẫu màu dưới4,5:1 trong12view | Nút/hướng dẫn≥44px;168mẫu cuối≥4,5,min5,4733 | Chỉ CSS/banner,giữ brand/global styles/motion |
| Lời chàoR1 và paragraphdetails bị sai do spec | Hai amendment riêng,không sửa record gốc | Tests/ngưỡng giữ;không tính worker codefail |

Source acceptance đọc rawBASE+8+2records,năm mươi ba record Composer
trước giữ nguyên pin. Các helper test lịch sử chỉ đảo đúng phần đã duyệt,
không vào ứng dụng. Không suy bản dịch banner thành xác nhận xử lý
video, mức phí, provider, số dư hay việc cài/chạy tiện ích.
