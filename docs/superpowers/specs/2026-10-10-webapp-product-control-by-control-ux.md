# SPEC — Đặc tả UI/UX tới từng điều khiển sản phẩm Web App

**SPEC_ID:** `WEBAPP-PRODUCT-CONTROL-BY-CONTROL-UX-20261010`

**SPEC_TYPE:** Spec con của `WEBAPP-BOT-FUNCTION-PARITY-REBASELINE-20261009` — không phải plan tổng thứ ba.

**BASELINE ĐÃ ĐỌC:** `origin/main=86d4ee6e11ddfbc0d4e1dbf63b41d9b3ed7d859b` (2026-10-10).

**STATUS:** `SPEC_READY_CONTROL_INVENTORY_AND_CANONICAL_BOT_SOURCE_STILL_OPEN`
**IMPLEMENTATION:** Chưa bắt đầu trong task này. Hoàn tất plan rồi dừng; sau đó khép công việc UI/motion dang dở, rồi mới mở các spec theo thứ tự.

## 1. Mục tiêu và ranh giới

Trước khi giao bất kỳ sửa UI sản phẩm nào, phải biết chính xác mỗi nút, link,
ô chọn, nút gạt, thanh chỉnh, vùng tải tệp, bộ lọc và menu đang làm gì. Builder
không được tự suy ra hành vi từ tên nút hoặc tự bịa route, input, giá, quyền,
trạng thái, đầu ra hay thông báo.

Spec này chỉ quy định cách kiểm kê và mô tả UI/UX. Không tự sửa route, API,
engine, provider, giá/quote, ví, job lifecycle, phân quyền server, dữ liệu hoặc
Bot. Nếu thiếu contract thật, ghi `UNKNOWN`/`BACKEND_GAP` và dừng đúng action đó;
không dùng UI để giả lập hành vi.

## 2. Nguồn chuẩn và thứ tự đối chiếu

Trước mỗi đợt, cập nhật `CURRENT_MAIN_SHA`; SHA `86d4ee6…` chỉ là mốc đã đọc,
không phải mốc vĩnh viễn. Sau phần UI/motion đang dở, phải fetch/recheck source
main mới và tạo inventory lại nếu source liên quan đã đổi.

| Dữ liệu cần biết | Nguồn phải mở trên đúng SHA | Quy tắc |
|---|---|---|
| Route, cấu hình trang, thứ tự trường, render control, nhãn hiện tại | `static/portal/portal.js`, `copyfast_pages.py`, `templates/portal_shell.html` | Ghi chính xác path + line/selector; route tồn tại không chứng minh action chạy. |
| Handler, method/endpoint, payload, lỗi trả về, trạng thái sau submit | `static/portal/integration.js`, `copyfast_api.py`, bridge tương ứng, test contract | Chỉ ghi điều đã xác nhận từ source/test; không suy diễn endpoint từ nhãn. |
| Bản dịch và aria label | `static/portal/portal-i18n.js` và DOM đã render ở VI/EN/ZH | Ghi đủ chuỗi từng locale; không lấy fallback VI làm bản EN/ZH. |
| Màu, theme, focus, kích thước, responsive, motion | `static/portal/portal.css`, `static/portal/portal-theme.css`, `static/portal/portal-motion.js` | Dùng token xanh–teal hiện có; dark theme là xanh đậm + chữ sáng, không đổi sang đen. |
| Ý nghĩa nghiệp vụ và những lựa chọn Bot thật sự hỗ trợ | Bot Git SHA đã được khóa riêng trong `SPEC-00`; action ledger có path/line | Nếu Bot HEAD và dirty overlay xung đột, tách hai record; không chọn tùy ý. |
| Thẩm quyền và điều kiện hành động | API/bridge/server authorization + contract tests | Trạng thái ẩn/hiện nút không thay thế kiểm tra quyền phía server. |

Tài liệu cũ, PR cũ, ảnh chụp và báo cáo agent là đầu mối tìm kiếm; không thay
được source/test của SHA đang nghiệm thu. Bot source chưa khóa thì chỉ được lập
inventory giao diện Web, chưa được chốt parity hoặc thiết kế thêm lựa chọn.

## 3. Sổ điều khiển bắt buộc

Đầu ra giai đoạn inventory là bảng đọc được và JSON/CSV ổn định tại:

- `reports/audit/WEBAPP-PRODUCT-UI-ACTION-LEDGER.md`
- `reports/audit/WEBAPP-PRODUCT-UI-ACTION-LEDGER.json`

Mỗi **điều khiển đang thấy hoặc có thể xuất hiện theo trạng thái** là một dòng.
Nếu một selector dùng lại trên nhiều route, mỗi tổ hợp route + action là một
dòng riêng. Không gộp các nút “Tạo”, “Lưu”, “Duyệt”, “Tải xuống” chỉ vì cùng
component.

### Trường bắt buộc cho từng dòng

```text
CONTROL_ID=
PRODUCT_AND_CAPABILITY=
CURRENT_MAIN_SHA=
SOURCE_PATH_AND_LINES=
ROUTE_AND_AUTH_STATE=
DOM_ROLE_AND_STABLE_SELECTOR=
VISIBLE_LABEL_VI_EN_ZH=
ARIA_NAME_AND_HELP_TEXT_VI_EN_ZH=
CONTROL_CLASS=nav|submit|confirm|local-choice|upload|save|delete|approve|download|filter|editor|other
USER_INTENT=
VISIBLE_WHEN=
ENABLED_WHEN=
DISABLED_REASON=
REQUIRED_PERMISSION_AND_RECORD_OWNER=
INPUT_SCHEMA_AND_VALIDATION=
CANONICAL_REQUEST_METHOD_ENDPOINT_PAYLOAD=
QUOTE_OR_COST_AUTHORITY=NOT_APPLICABLE|EXACT_SOURCE
REQUEST_ID_IDEMPOTENCY_AND_DUPLICATE_BEHAVIOR=
EXPECTED_STATE_TRANSITION=
SUCCESS_FEEDBACK_AND_NEXT_ACTION=
ERRORS_AND_RECOVERY=
INPUT_PRESERVATION_ON_FAILURE=
DESTINATION_OR_RESULT_SURFACE=
ADMIN_CUSTOMER_REPORT_LINKAGE=
DESTRUCTIVE_CONFIRM_OR_UNDO=NOT_APPLICABLE|EXACT_RULE
RESPONSIVE_KEYBOARD_TOUCH_AND_FOCUS=
LIGHT_DARK_LOCALE_AND_CONTRAST=
MOTION_AND_REDUCED_MOTION=
TEST_COMMAND_AND_EXPECTED_OUTPUT=
EVIDENCE_PATH_AND_SHA=
DISPOSITION=SUPPORTED|GUARDED|NOT_IMPLEMENTED|BACKEND_GAP|BOT_ONLY|ADMIN_ONLY|OWNER_NEW_REQUIREMENT|UNKNOWN
```

**`UNKNOWN=0` là cổng bắt đầu code cho đúng capability**, không phải yêu cầu
che giấu phần thiếu. Nếu nguồn chưa xác định endpoint, payload, quyền, lỗi,
cost hoặc đầu ra thì ghi `UNKNOWN`/`BACKEND_GAP`, đính kèm câu hỏi chính xác và
không viết spec code cho action đó cho đến khi có bằng chứng/chủ sở hữu trả lời.

## 4. Quy tắc bố cục và hành vi chung

1. **Trang hub:** nhóm công cụ theo việc người dùng muốn làm; mỗi mục theo một
   hàng/card dọc dễ quét, nhãn là động từ + kết quả. Một CTA chính; link phụ,
   lịch sử và hướng dẫn không cạnh tranh thị giác.
2. **Form sản phẩm:** một cột theo thứ tự `mục tiêu → đầu vào → lựa chọn bắt
   buộc → tùy chọn nâng cao → estimate/quote nếu contract có → xác nhận`. Không
   ép mọi sản phẩm vào chuỗi này nếu Bot/API không có bước đó; cũng không bỏ
   bước bảo vệ đã có.
3. **Kết quả:** trạng thái, mã yêu cầu/tác vụ phù hợp, báo cáo từng bước, lỗi có
   cách khôi phục và hành động hợp lệ kế tiếp nằm gần nhau. Lịch sử/asset là
   bề mặt riêng có đường quay lại rõ.
4. **Editor:** giữ bố cục ngang chỉ khi tác vụ thực sự cần canvas/timeline; các
   thanh công cụ, trường và danh sách hành động vẫn nhóm dọc. Không làm timeline
   giả chỉ để giống ứng dụng khác.
5. Giữ nguyên màu brand xanh–teal/blue và kiến trúc token hiện tại. Chữ thân
   tối thiểu 16px, label không dưới 14px, tiếng Việt có line-height đủ dấu;
   chữ thường tương phản tối thiểu 4.5:1, chữ lớn/ranh giới UI 3:1; vùng chạm
   tối thiểu 44×44px. Không tự đặt hex mới nếu chưa đo token hiện tại.
6. VI là tiếng Việt tự nhiên, EN là tiếng Anh đầy đủ, ZH là tiếng Trung đầy
   đủ; chỉ giữ tên riêng/thuật ngữ sản phẩm được xác nhận. Không để label, help,
   tooltip, validation, toast hoặc aria-label trộn locale.
7. **Landing/trang chào mừng:** một H1 nói rõ giá trị cho khách, CTA chính
   nhìn thấy ngay, các luận điểm quan trọng có thể dùng chữ đậm và đúng token
   màu nhấn hiện hữu; không tô màu mọi câu, không dùng số liệu/chứng thực giả.
   Kiểm riêng khách chưa đăng nhập/đã đăng nhập, VI/EN/ZH và màn 360px.
8. **Phân cấp chữ:** dùng type scale hiện có, tối đa 6 cỡ trên một màn; H1
   32–48px linh hoạt theo viewport, H2 24–36px, H3 20–24px, body 16px, label
   14px; line-height body tối thiểu 1.625 và heading không dưới 1.25 để dấu
   tiếng Việt không va/cụt. Nếu token current-main khác, đo và ghi sai khác
   trước khi sửa; không tự thêm font/hex.
9. **Tham khảo giao diện (`UI-REF-00`):** trước khi chốt bố cục/micro-interaction
   cho một nhóm sản phẩm, lưu tối đa 2 nguồn tham khảo chính thức/đáng tin cậy,
   URL và ngày truy cập; ghi rõ pattern cụ thể muốn học (phân cấp, bước thao tác,
   phản hồi, mobile) và lý do phù hợp. Bot cùng API hiện hành vẫn là nguồn sự
   thật cho nghiệp vụ; nguồn ngoài chỉ định hướng trình bày. Không sao chép logo,
   ảnh, văn bản, code, nhận diện hoặc capability không có trong contract; phải
   giữ màu xanh–teal/blue và các ràng buộc Owner.

## 5. Hợp đồng trạng thái của từng điều khiển

Không buộc mọi control có mọi state; từng dòng phải ghi state áp dụng và lý do
`NOT_APPLICABLE` cho state không hợp lý. Những state có thể xảy ra phải được
định nghĩa trước khi sửa:

| State | Hành vi bắt buộc |
|---|---|
| Mặc định | Nhãn nói rõ kết quả; phân cấp primary/secondary đúng vai trò. |
| Hover | Chỉ phản hồi thị giác; không thực thi action hoặc làm chữ mất tương phản. |
| Focus-visible | Tab/keyboard thấy rõ focus; thứ tự focus đúng luồng; không focus trap. |
| Active/pressed/selected | Phản hồi trong khoảng 100ms trên mobile; trạng thái chọn có ngữ nghĩa/aria, không chỉ đổi màu. |
| Disabled/guarded | Không thể kích hoạt; lý do và điều kiện mở khóa nhìn thấy; không giả vờ sẵn sàng. |
| Loading/submitting | Có tiến trình và chống bấm lặp; không khóa các thao tác độc lập không liên quan. |
| Success | Chỉ báo thành công sau phản hồi đúng contract; nêu kết quả kế tiếp. `HTTP 200`, draft hoặc job ID không tự là thành công cuối. |
| Validation/error/permission/offline | Báo cạnh trường/hành động, giữ input; nói cách sửa/thử lại; không lộ nội bộ/secret. |
| Retry/cancel | Retry chỉ khi idempotent hoặc có key chống trùng; cancel chỉ hiện nếu server hỗ trợ thật. |
| Reduced motion | Không phụ thuộc animation để hiểu trạng thái hoặc tiếp tục thao tác. |

Action xóa/ghi đè/đăng/xác nhận giao dịch phải nêu ảnh hưởng, xác nhận hoặc
hoàn tác theo contract. Action tạo job phải chỉ rõ confirmation, duplicate
click, pending/processing/result và cách đi tới báo cáo. Action tải lên phải
nêu định dạng/kích thước/ownership/tiến trình/lỗi. Action tải xuống phải nêu
điều kiện file sẵn sàng và quyền truy cập. Link điều hướng phải nêu đích,
back/scroll restoration và trạng thái auth.

## 6. Phân spec nhỏ theo sản phẩm — thực hiện sau khi sổ điều khiển khóa

Mỗi dòng dưới đây chỉ là nhóm spec. Trong nhóm, ledger sinh **một phiếu cho
mỗi action/control độc lập**; số phiếu cuối cùng không đoán trước.

| Thứ tự | Nhóm spec | Controls phải tách thành action riêng | Gate trước khi code |
|---:|---|---|---|
| 0 | `UI-ACT-00` — nguồn và inventory | Route, page, mọi button/link/form/select/toggle/slider/upload/filter/pagination/result action | `CURRENT_MAIN_SHA` mới; Bot canonical/dirty provenance riêng; catalog DOM ↔ ledger reconcile; `UNKNOWN=0` trong phạm vi được giao. |
| 0A | `UI-REF-00` — đối chiếu mẫu trình bày | Tối đa 2 nguồn tham khảo đáng tin cậy cho từng nhóm; URL/ngày; pattern áp dụng, pattern loại bỏ, bằng chứng | Chỉ thực hiện sau khi source/ledger khóa; Bot/API quyết định nghiệp vụ, nguồn ngoài chỉ hỗ trợ bố cục và tương tác; giữ brand, không chép tài sản. |
| 1 | `UI-LANDING-01` — landing/trang chào mừng | H1/luận điểm nhấn/CTA chính, khối giới thiệu có thật, đăng nhập/chuyển vào app, locale và responsive | Một giá trị chính và một CTA nổi bật; copy/claim có nguồn; VI/EN/ZH và 360px không lỗi; dùng đúng token brand. |
| 2 | `UI-SHELL-01` — shared shell | Điều hướng, mở/đóng menu, locale/theme, tài khoản/xác thực, trợ lý/cài ứng dụng, back, responsive drawer | Theo `docs/superpowers/specs/2026-10-10-webapp-shared-shell-ui-closeout.md`; test khách chưa đăng nhập/đã đăng nhập, VI/EN/ZH, sáng/tối. |
| 3 | `UI-VOICE-01..N` | TTS mặc định; chọn/đổi giọng; estimate/confirm; nghe/xem kết quả; dùng voice đã lưu; thêm/clone + consent; quản lý profile | Tách mặc định/saved/clone/profile. Chỉ có nút nếu source hiện hành chứng minh; mỗi control có readiness, quyền, lỗi và đường tới audio thật. |
| 4 | `UI-MUSIC-01..N` | Tạo nhạc nền; bài hát có lời; tier/giọng/độ dài/lời; thư viện; SFX; upload nhạc; estimate/confirm/result/download | Reconcile riêng `music_background` và `music_song`; hiển thị quote theo nguồn canonical, không dùng chuỗi giá tĩnh làm authority. |
| 5 | `UI-SUBDUB-01..04` | Bốn lựa chọn: phụ đề nguồn, chỉ lồng tiếng, phụ đề theo Bot, combo; nguồn/ngôn ngữ/giọng/volume/confirm/result | Một màn hình; mỗi mode có bộ trường, yêu cầu, payload, disabled reason và report riêng; volume chỉ được ghi là có tác dụng khi payload và file cuối chứng minh. |
| 6 | `UI-IMAGE-01..N` | Tạo mới bằng AI; sửa AI; thao tác deterministic/thủ công; input/preview/quote/confirm/download | Tách rõ AI và deterministic; nguồn ảnh đúng owner; mỗi nút có output/error contract; không gọi remove-background là AI edit nếu nguồn không nói vậy. |
| 7 | `UI-WALLET-01` — khách hàng nạp tiền | Chọn phương thức được hỗ trợ → nhập số tiền → xác nhận → chỉ sau đó hiện mã/QR/hướng dẫn; gửi chứng từ/nội dung → theo dõi pending/kết quả | Mỗi phương thức và số tiền phải khớp contract hiện hành; QR/mã không hiện ở trạng thái đầu; yêu cầu tạo ra không tự cộng Xu; test chỉ trên QA cô lập. Chi tiết ở `2026-10-10-webapp-wallet-admin-ui-closeout.md`. |
| 8 | `UI-FREE-01..N` | Mỗi tiện ích Free Tool; riêng input, action, output, quota/giới hạn và lưu trữ | Chỉ liệt kê tiện ích được source xác nhận; không gọi hub/card là công cụ đã chạy. |
| 9 | `UI-MEMORY-01..N` | Notes/Memory: create/list/search/update/delete/reminder/priority nếu Bot có; mỗi action riêng | Không thêm pin/archive nếu Bot source không xác nhận; quyền sở hữu, reminder state và lỗi phải rõ. |
| 10 | `UI-DOCUMENT-01..N` | Documents/PDF/OCR/dịch: upload/inspect/process/preview/export/download/retry | Tách bản xem trước khỏi artifact đã xuất; định dạng, owner, tiến trình và lỗi rõ. |
| 11 | `UI-CONTENT-01..N` | Content/prompt tools: compose/save/copy/apply/export | Bản nháp, nội dung được tạo và nội dung đã xuất/đăng là các trạng thái khác nhau. |
| 12 | `UI-PUBLISH-01..N` | Kênh: kết nối/ủy quyền, soạn, duyệt, lên lịch, đăng, receipt, retry | Không báo đã đăng khi chưa có receipt; không tự thay đổi OAuth/channel authority. |
| 13 | `UI-PROJECT-01..N` | Projects/Workboard: tạo, mở, chỉnh sửa, phân công, hoàn tất, lọc nếu source có | Không trộn project/task với product job; quyền và owner theo record. |
| 14 | `UI-ASSET-01..N` | Assets/Downloads: preview, tải, xóa/chia sẻ nếu được hỗ trợ | Metadata không chứng minh tệp sẵn sàng; kiểm quyền, owner và artifact thực. |
| 15 | `UI-JOBS-01..N` | Jobs/History: lọc, xem trạng thái/báo cáo, mở kết quả, retry/cancel nếu API hỗ trợ | Không suy cancel/retry từ nút UI; ID/job không được gọi là artifact đầu ra. |
| 16 | `UI-SUPPORT-01..N` | Support/Tickets: gửi yêu cầu, đính kèm, trao đổi, trạng thái và đóng ticket | Giữ input khi lỗi; trạng thái và hành động tiếp theo theo server contract. |
| 17 | `UI-MEMBER-01..N` | Members: xem/tìm, cấp/đổi quyền hoặc mời thành viên nếu source hỗ trợ | Tách vai trò, record owner, quyền đọc/ghi và audit; không sửa RBAC server trong UI lane. |
| 18 | `UI-REWARD-01..N` | Rewards: điều kiện, xem điểm/quyền lợi, lịch sử và đổi thưởng nếu source hỗ trợ | Không gộp với Members; nguồn tính, số dư và điều kiện phải có authority rõ. |
| 19 | `UI-COMMUNITY-01..N` | Community/Referral: từng hành động được Bot/current source xác nhận | Chỉ vẽ chức năng có nguồn, trạng thái và quyền; không suy từ menu/route. |
| 20 | `UI-ADMIN-BILLING-01` — Admin duyệt nạp | Danh sách pending, mở chi tiết, đối chiếu số tiền/phương thức/mã/chứng từ, duyệt hoặc từ chối có lý do | Quyền/record owner/audit/idempotency theo server; không cho Admin UI giả lập duyệt nếu API không hỗ trợ. Spec riêng; test QA không ghi ví thật. |
| 21 | `UI-ADMIN-ERP-01..N` | Admin ERP: từng màn quản trị, tìm kiếm, xem, cấp quyền và các action được source xác nhận | Lane riêng theo role/record/audit/confirm/undo; Admin ERP không mặc định là Bot parity; không dùng test khách để đóng Admin. |
| 22 | `UI-VIDEO-01..N` — cuối các sản phẩm | Mỗi capability Video Bot xác nhận: self-shot, trend, storyboard, long/multi-scene, planner, render/review, AI editor, manual/timeline editor, export/history | Video đi sau toàn bộ nhóm không phải Video. Mỗi sản phẩm và từng nút có spec riêng; AI editor ≠ manual timeline. |
| 23 | `UI-MOTION-FINAL` | Enter/exit, route transition, reveal, loading/progress, tap/focus feedback, reduced motion | Chỉ sau khi khép phần motion đang dở và UI controls ổn định; WA-35/36 trên current-main SHA, không dùng claim lỗi cũ thay evidence. |

## 7. Checklist tổng cho từng action/control

Mỗi spec con chỉ được giao khi mọi mục áp dụng dưới đây đã có giá trị cụ thể:

- [ ] Có source SHA, file/line, route, selector ổn định và ảnh/DOM của đúng state.
- [ ] Có nhãn VI/EN/ZH, mục đích người dùng, phân cấp primary/secondary và vị trí trong flow dọc.
- [ ] Có điều kiện hiển thị/kích hoạt, quyền, ownership, validation và lý do khóa.
- [ ] Có method/endpoint/payload/source quote và idempotency đã kiểm; không suy từ label.
- [ ] Có state table, success/error/permission/offline, giữ input và đường hồi phục.
- [ ] Có vị trí báo cáo Admin/khách, kết quả/tệp thật, lịch sử và điều hướng sau action.
- [ ] Có token/theme/contrast/keyboard/touch/responsive/reduced-motion cho control đó.
- [ ] Nếu route hỗ trợ PWA: kiểm manifest/install/icon/start URL/scope, standalone back, safe-area/bàn phím/zoom 200%, offline/write feedback và service-worker update; nếu không áp dụng, ghi `NOT_APPLICABLE` kèm bằng chứng.
- [ ] Có một lệnh test copy-paste chạy được và output mong đợi cụ thể; có test hành vi, không chỉ snapshot chuỗi.
- [ ] Spec nêu file được sửa và file cấm sửa; không đụng engine/route/giá/ví ngoài scope được Owner duyệt.
- [ ] Tester độc lập đọc lại toàn bộ field; mọi mục `UNKNOWN` ngoài scope được liệt kê, trong scope bằng 0.

## 8. Rà soát và dừng

`plan-chuan` review trước khi giao: người mới không có lịch sử chat vẫn biết
chính xác file nào, selector nào, hành vi/state nào, điều gì cấm, và lệnh nào
để xác minh. Spec thiếu bất kỳ phần nào trên thì chưa gửi builder.

Mỗi phiếu gửi builder phải tiếp tục được chẻ đến mức một đơn vị 2–5 phút; nếu
việc dài hơn thì tách control/state thành phiếu kế tiếp. Phiếu phải ghi path/line,
selector, yêu cầu số cụ thể, file được/cấm sửa, đúng skill cần đọc và một lệnh
verify copy-paste kèm output mong đợi. Bảng nhóm ở trên không thay thế phiếu
builder cấp nhỏ.

Sau khi tài liệu plan/checklist/spec hiện tại được cập nhật và kiểm tra diff,
dừng task theo yêu cầu Owner. Không tự chuyển sang implementation, không đụng
30 thay đổi UI/motion có sẵn trong worktree, không tạo issue/project/PR, không
merge/deploy/live-test trong spec này.

Checklist điều phối theo từng giai đoạn: `reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-20261010.md`.
Đặc tả shared shell: `docs/superpowers/specs/2026-10-10-webapp-shared-shell-ui-closeout.md`.
Đặc tả xử lý motion đang dở và nghiệm thu cuối: `docs/superpowers/specs/2026-10-10-motion-webapp-surfaces-final.md`.
Đặc tả riêng cho nạp tiền khách hàng và duyệt Admin: `docs/superpowers/specs/2026-10-10-webapp-wallet-admin-ui-closeout.md`.
