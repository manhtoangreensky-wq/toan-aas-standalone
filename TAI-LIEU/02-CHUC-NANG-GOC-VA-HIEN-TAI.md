# Chức năng gốc và hiện tại — TOAN AAS Web App

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
