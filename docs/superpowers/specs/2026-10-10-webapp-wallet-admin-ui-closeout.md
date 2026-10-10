# Đặc tả — Luồng nạp tiền khách hàng và duyệt trong Admin

**SPEC_ID:** `WEBAPP_WALLET_ADMIN_UI_CLOSEOUT_20261010`
**STATUS:** `PLAN_ONLY_READY_AFTER_WA35_AND_SOURCE_REBASELINE`
**CURRENT_UI_STATUS:** `NEEDS_REVALIDATION`
**CURRENT_MAIN_SHA_READ:** `86d4ee6e11ddfbc0d4e1dbf63b41d9b3ed7d859b` — phải cập nhật trước khi bắt đầu code.

## 1. Mục tiêu

Làm rõ và nghiệm thu riêng hai mặt của cùng một yêu cầu tài chính:

1. Khách chọn cách nạp, nhập đúng số tiền, xác nhận rồi mới thấy hướng dẫn/mã/QR thanh toán; gửi yêu cầu để Admin xem xét.
2. Admin tìm thấy đúng yêu cầu, đối soát đủ dữ kiện và chỉ duyệt/từ chối theo thẩm quyền cùng contract hiện hành.

Mục tiêu của spec là lập contract trình bày và kiểm thử. Spec này **không** tự cấp quyền sửa logic ví, thanh toán, số dư Xu, API, cơ sở dữ liệu hoặc provider.

## 2. Bằng chứng và giới hạn hiện biết

- Owner đã báo cáo trước đây rằng form thiếu/chưa nhận số tiền, mã/QR hiển thị sai thời điểm hoặc bị mất, và Admin chưa thấy/không xử lý được yêu cầu. Đây là **reported defects**, chưa được tái xác minh trên current main trong lượt lập plan.
- Route khách từng được ghi nhận là `/wallet/topup`; route/DOM hiện hành của Admin billing phải đọc từ current-main source, không đoán từ ảnh hoặc route cũ.
- Bot source canonical chưa khóa. Vì vậy danh sách phương thức, số tiền tối thiểu/tối đa, phí, nội dung chuyển khoản, mã tham chiếu, thời hạn QR và hành vi duyệt đều phải để `UNKNOWN` cho đến khi xác minh từ Bot/API có thẩm quyền.
- Nếu Bot hỗ trợ “mã nạp là ID tài khoản”, đối chiếu và trình bày chính xác theo contract đã khóa; không tự chế mã hoặc giả lập số tiền.

## 3. Phạm vi hai giao diện

### A. Khách hàng — `UI-WALLET-01`

Thứ tự dọc bắt buộc, mỗi bước chỉ hiện thông tin cần thiết của bước đó:

1. **Chọn phương thức:** chỉ liệt kê phương thức đang được API/contract cho phép. Phương thức chưa sẵn sàng phải bị khóa kèm lý do; không quảng bá phương thức chưa hỗ trợ.
2. **Nhập số tiền:** có nhãn cố định, định dạng tiền thống nhất, giới hạn/phí lấy từ nguồn có thẩm quyền, báo lỗi cạnh ô và giữ giá trị người dùng khi lỗi.
3. **Xem lại và xác nhận:** tóm tắt phương thức + số tiền + điều kiện; bấm xác nhận một lần tạo đúng một yêu cầu pending theo idempotency contract.
4. **Hướng dẫn thanh toán:** chỉ sau xác nhận mới hiển thị đúng người nhận, mã chuyển khoản/nội dung, số tiền và QR tương ứng với yêu cầu vừa tạo. Trạng thái đầu và các phương thức chưa chọn không được lộ QR/mã/hướng dẫn thuộc yêu cầu khác.
5. **Gửi chứng từ/đối chiếu:** nếu contract hỗ trợ, nhận file/tham chiếu hợp lệ; hiển thị đang chờ kiểm tra, mã yêu cầu, số tiền, thời gian và bước tiếp theo. Không dùng chữ “đã nạp” trước khi giao dịch được duyệt.
6. **Kết quả:** `PENDING`, `APPROVED`, `REJECTED`, `EXPIRED` hoặc trạng thái thực sự có trong API; trạng thái không biết phải hiện lỗi/trạng thái chưa xác định, không đoán.

Không đánh dấu thanh nạp hoàn tất chỉ vì đã tạo mã yêu cầu, đã tải QR hoặc HTTP 200.

### B. Admin — `UI-ADMIN-BILLING-01`

Route Admin billing và selector chính xác phải được lấy từ current-main source/DOM. Bề mặt cần có:

- Danh sách yêu cầu chờ duyệt, bộ lọc/trạng thái và tải/trang kế tiếp nếu nguồn có.
- Chi tiết đủ để đối chiếu: mã yêu cầu, ID/tài khoản khách, số tiền yêu cầu, phương thức, nội dung/mã giao dịch, chứng từ hợp lệ, thời điểm và trạng thái hiện tại.
- Hành động duyệt/từ chối chỉ xuất hiện khi quyền và server contract cho phép; từ chối phải có lý do nếu API yêu cầu.
- Sau thao tác, hiển thị phản hồi từ server, Admin thực hiện, thời gian, lý do/kết quả và ảnh hưởng lên bản ghi; khóa bấm lặp và thể hiện giao dịch trùng theo cơ chế server.
- Nếu thiếu endpoint, role gate, audit hoặc contract chống trùng, ghi `BACKEND_GAP` và không tạo nút giả/không ghi “đã duyệt”.

Admin billing là một lane riêng; không suy rằng mọi chức năng ERP có một nút tương đương trong Bot. Chỉ ghi Bot counterpart khi inventory nguồn xác nhận.

## 4. Quy cách trình bày và sử dụng

- Form một cột, thứ tự đọc từ trên xuống; lựa chọn thanh toán dùng nhóm có nhãn, không làm một hàng dài khó quét.
- Giữ hệ màu xanh–teal/blue hiện hữu. Chế độ tối dùng nền xanh đậm và chữ sáng; tuyệt đối không đổi nền sang đen thuần. Màu chữ/nền phải tương phản WCAG AA.
- Nút chính có một hành động rõ; QR/mã/hướng dẫn nằm trong phần thanh toán sau xác nhận, không chiếm màn hình ở bước đầu.
- VI dùng tiếng Việt tự nhiên; EN dùng tiếng Anh đầy đủ; ZH dùng tiếng Trung đầy đủ. Tên riêng/thuật ngữ thanh toán được giữ khi cần, không trộn câu.
- Desktop/tablet dùng bảng/list có nhãn và căn cột rõ; mobile chuyển sang thẻ dọc/chi tiết xếp dọc, không cuộn ngang để tìm nút duyệt.
- Kiểm trạng thái hover/focus-visible/pressed/disabled/loading/error/empty; focus không bị mất sau lỗi và không dùng màu đơn lẻ để biểu thị trạng thái.

## 5. Cổng dữ liệu, quyền và an toàn

Trước khi tạo spec code cho từng action phải có đủ:

- Current-main SHA, source path/line, route, selector và auth state.
- Canonical Bot SHA hoặc disposition rõ `SOURCE_UNAVAILABLE`; API/method/payload và owner của trường tiền/mã/QR.
- Quyền của khách và Admin, bản ghi sở hữu, xác thực dữ liệu, chống CSRF nếu áp dụng, audit, idempotency/duplicate behavior.
- Quy tắc pending/approve/reject/expire và bằng chứng trạng thái server; UI không được tự cộng Xu, sửa số dư hoặc tự đánh dấu thanh toán.
- Hạn mức, phương thức và mã chưa được source xác nhận phải `UNKNOWN`; không điền ví dụ giả vào UI như dữ liệu thật.

**Mặc định không cho phép trong wave UI/UX:** provider call, nạp tiền production, duyệt giao dịch thật, wallet mutation, sửa secrets/ENV, migration phá hủy hoặc deploy. Kiểm thử hành vi chỉ dùng fixture/DB QA cô lập và xác minh ghi nhận không đi ra production.

## 6. Checklist nghiệm thu

### Khách hàng

- [ ] Trạng thái mới vào chưa chọn phương thức/số tiền không hiển thị QR, tài khoản nhận hoặc mã chuyển khoản.
- [ ] Chỉ có phương thức được source xác nhận; chọn phương thức khác sẽ không giữ nhầm QR/mã của lựa chọn trước.
- [ ] Không thể xác nhận khi số tiền rỗng/ngoài giới hạn; lỗi có hướng sửa và giữ nguyên dữ liệu đã nhập.
- [ ] Một lần xác nhận sinh đúng một yêu cầu; bấm lặp/refresh không nhân đôi yêu cầu.
- [ ] QR/mã/nội dung chuyển khoản/amount sau xác nhận khớp request/quote server trả về.
- [ ] Sau gửi yêu cầu, trạng thái hiển thị đang chờ Admin; số dư không được mô tả là đã tăng.
- [ ] Lỗi mạng, hết hạn, gửi chứng từ sai hoặc giao dịch trùng có thông báo và đường phục hồi đúng contract.

### Admin

- [ ] Người không có quyền không thấy hoặc không kích hoạt được hành động duyệt; server vẫn từ chối nếu gọi trực tiếp.
- [ ] Pending hiển thị đúng khách, ID tài khoản, số tiền, phương thức, mã/tham chiếu, chứng từ và thời gian.
- [ ] Duyệt chỉ hoàn tất sau phản hồi server; thao tác lặp không ghi nhận hai lần.
- [ ] Từ chối có lý do và khách nhận đúng trạng thái/kết quả nếu hệ thống hỗ trợ.
- [ ] Audit nối được actor Admin → request → quyết định/thời điểm → trạng thái sau cùng.
- [ ] Bảng desktop và thẻ mobile không cắt số tiền, mã, tên hoặc nút chính.

### Chất lượng hiển thị

- [ ] VI/EN/ZH đầy đủ; không trộn locale ở label, placeholder, lỗi, nút, toast hoặc aria-label.
- [ ] Sáng/tối giữ brand; chữ thường tương phản ≥4.5:1, chữ lớn/UI ≥3:1.
- [ ] Kiểm 360/375/768/1440px, bàn phím, Tab/focus, touch ≥44×44px, zoom 200%, không tràn ngang.
- [ ] Success/error/loading/empty/pending/rejected đều có trạng thái ngữ nghĩa, không chỉ dựa màu.

## 7. Thứ tự và bằng chứng

1. Đóng việc WA-35 đang dở theo master checklist; không mở spec này để triển khai trước cổng đó.
2. Rebaseline current main và khóa Bot/API nguồn; lập control ledger cho Wallet/Top-up và Admin billing.
3. Chốt `UNKNOWN=0` cho phương thức, amount/quote, mã/QR, quyền, trạng thái và báo cáo; nếu chưa đạt thì chỉ cập nhật blocker.
4. Sinh phiếu code nhỏ theo từng control (mỗi phiếu 2–5 phút, file allowlist/blocklist, skill, lệnh verify và output mong đợi); chỉ giao sau khi contract đầy đủ.
5. Chạy contract/UI test trên DB QA cô lập hoặc response mock, zero provider/wallet/production mutations; phần nút duyệt kiểm bằng fixture/mock không ghi số dư. Muốn kiểm thử commit tài chính thực trong QA cần Owner duyệt riêng trước; Tester độc lập xem evidence trước khi đóng.

Lệnh test cụ thể sẽ được ghi ở phiếu từng control sau khi xác định chính xác test file/selector ở current main; không bịa lệnh hoặc kết quả từ snapshot cũ.

## 8. Trạng thái

```ini
SPEC_ID=WEBAPP_WALLET_ADMIN_UI_CLOSEOUT_20261010
STATUS=PLAN_ONLY_READY_AFTER_WA35_AND_SOURCE_REBASELINE
CUSTOMER_CURRENT_UI=NEEDS_REVALIDATION
ADMIN_CURRENT_UI=NEEDS_REVALIDATION
BOT_CANONICAL_SHA=NOT_LOCKED
API_AND_METHODS=UNKNOWN_UNTIL_SOURCE_RECONCILIATION
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
CODE_CHANGED=NO
PUSH=NO
DEPLOY=NO
LIVE_PASS=NO
NEXT=WA35_RCA_THEN_CURRENT_MAIN_AND_BOT_SOURCE_REBASELINE
```
