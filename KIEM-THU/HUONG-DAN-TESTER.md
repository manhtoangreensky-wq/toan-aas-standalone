# Hướng dẫn Tester TOAN AAS Web App

## 1. Nguồn case

1. Nguồn duy nhất là `KIEM-THU/DANH-SACH-CASE.md`.
2. Chọn đúng một ID trong `WA-01..WA-43` cho mỗi lượt test.
3. Nếu cần đổi case, sửa case thì sửa ở file đó trước, rồi mới đồng bộ issue.
4. Tracker batch là GitHub issue `#412` của repo `manhtoangreensky-wq/toan-aas-standalone`.
5. Không dùng chat/Zalo làm nơi lưu kết quả duy nhất.

## 2. Ghi đúng phiên bản

6. Trước khi test, ghi `BASE` SHA và `HEAD` SHA của source.
7. Sau deploy, ghi `runtime SHA` đọc từ runtime/evidence; không chép theo trí nhớ.
8. Ghi rõ môi trường: `local-temp-only`, `local-render`, `CI`, `deployed`, `ship-gated` hoặc `live`.
9. Local PASS không thay CI PASS.
10. CI PASS không thay bằng chứng deployed.
11. Deployed không thay live output.
12. `HTTP 200` không chứng minh kết quả tiền, media hoặc provider hợp lệ.

## 3. Thứ tự manual top-up

13. Chạy customer create trước, kiểm một pending request/invoice và zero initial credit.
14. Kiểm owner history/detail/status và foreign-owner isolation.
15. Đăng nhập đúng Admin, kiểm list/detail đã redaction.
16. Chạy draft và xác nhận draft không mutate Xu/audit decision.
17. Kiểm receipt chỉ dùng trong đúng session, hết hạn/tamper bị từ chối.
18. Chạy approve expected hoặc custom theo case; không tự đổi reason/số Xu ngoài fixture.
19. Chạy reject trong một request riêng và kiểm zero credit/usage/revenue.
20. Chạy idempotency/replay/concurrent case bằng fixture; không lặp trên production.
21. Kiểm owner đọc terminal status sau quyết định.

### P0-05E corrective

- WA-32 kiểm số hỗ trợ và mã nạp đều do signed server metadata cấp; số tài khoản ngân hàng là comparator riêng, không được nhầm với Hotline/Zalo.
- WA-33 phải thao tác thật `manual → amount/method/reference → hydration/remount`, không dùng source grep thay cho DOM/rendered evidence.
- WA-34 bơm sentinel `admin_note` vào single/history và giữ Admin projection làm control; customer JSON và customer JS state đều phải không có field này.
- Mobile 390/360 phải đo overlap theo diện tích giữa nút gửi với PWA FAB, Copilot và bottom nav; cả ba bằng `0`.
- WA-37 phải dùng account Web chưa liên kết Telegram: initial chỉ amount/method/confirm, không có QR/code/destination/reference/final submit. Xác nhận từng VND method enabled riêng lẻ và mỗi lượt chỉ có 1 signed QR/instruction; back hoặc chuyển PayOS→Manual phải purge và buộc xác nhận lại. USDT/Binance configured vẫn disabled vì chưa hỗ trợ đối soát VND. Không submit, quét hoặc thanh toán QR trong test UI.
- WA-38 phải dùng temp DB/private fixture: method unavailable và partial ACB không tạo row; malformed/decompression-bomb QR trả 404 có đủ security headers; concurrent same-key chỉ một request; Admin list/detail đọc đúng account/amount/code.
- WA-39 kiểm `/admin/login` tại `1920/1440/1024/841/840/821/805/804/769/768/390/360`: từ 841 trở lên hai cột, từ 840 trở xuống một cột; light/dark/system, focus, input/touch target, overflow/outside/console; `/login` và `/register` là protected comparator. Local PASS chưa phải live PASS.
- WA-40 kiểm đúng ba pha `choose → instructions → reconciliation`: initial không có QR/destination/code/history-transfer/reference/final submit hoặc QR request; click input/select không confirm; từng method VND chỉ được enable khi có canonical same-origin QR và explicit confirm chỉ hiện đúng một matching QR, không POST; back/lane-switch purge confirmation, logout/account-switch purge toàn draft; USDT/Binance hiện disabled với đúng lý do không hỗ trợ đối soát VND. Final submit chỉ chạy trên DB tạm để chứng minh một pending và zero decision/Xu/ledger/provider. Sau deploy chỉ live-test read-only tới bước confirm, không tạo pending production nếu chưa có Owner data-mutation gate mới.

### MOTION-WEBAPP-SURFACES-001

- WA-35 kiểm normal motion trên đủ bốn customer route; phải đo route/section entrance, scroll reveal, overflow, CLS, page/request error và foreign request thay vì chỉ đọc CSS.
- WA-36 kiểm `prefers-reduced-motion: reduce`; content phải visible, animation/transform presentation phải tắt và không còn section pending ngoài viewport.

## 4. Auth và dữ liệu nhạy cảm

22. Kiểm signed session, role, ownership và CSRF theo đúng case.
23. Browser query/body/header không được cấp canonical owner hoặc Admin authority.
24. Ghi safe `redaction` result: token, raw bridge field, private Admin data và customer record không được xuất hiện.
25. Ảnh/log phải che email, số điện thoại, ID riêng và dữ liệu khách.
26. Không gửi token.
27. Không gửi mật khẩu.
28. Không dán backup code.
29. Không gửi Admin ID hoặc raw customer record vào issue.

## 5. Chốt tiền và provider

30. Local/manual integration giữ `PROVIDER_CALLS=0`.
31. Local/manual integration giữ `WALLET_MUTATIONS=0` ngoài temp fixture đã kiểm soát.
32. Không tự bật ENV hoặc restart production để test.
33. Không gọi provider trả phí.
34. Cấm quét QR, thanh toán hoặc cộng Xu trong case PayOS chỉ kiểm checkout.
35. `LIVE_MONEY_FLOW=NOT_TESTED` cho tới khi Owner cấp quyền cụ thể.
36. Không có Owner gate thì WA-31 phải là BLOCKED, không phải FAIL hoặc PASS. WA-32..34 vẫn chạy local/temp/render không tiền thật.

## 6. Evidence bắt buộc

37. Mỗi kết quả ghi route, role và viewport.
38. Ghi các bước đã thao tác theo thứ tự.
39. Ghi PASS criteria, expected và actual.
40. Đính kèm screenshot/JSON/terminal output phù hợp.
41. Với UI, ghi console/page/request error, overflow, clip và overlay count.
42. Với security/tiền, ghi provider/wallet/data/ENV/GitHub mutation counters.
43. Với ship, tách PR merge, CI run, deploy run, runtime SHA, service health và live output.
44. Builder self-report không thay independent Tester verdict.

## 7. Báo lỗi và retest

45. Chọn đúng severity: `🔴 chặn-bán-hàng`, `🟠 nặng`, `🟡 vừa` hoặc `🟢 nhẹ`.
46. FAIL phải mở lại cùng `SPEC_ID`; không tạo ID mới để né lịch sử.
47. Dùng nhãn dòng chảy: `chờ-test` → `đang-test` → `có-lỗi` → `chờ-test-lại` → `đạt`.
48. Báo lỗi dùng nhãn `lỗi`, `có-lỗi`, `chờ-sửa` và severity tương ứng.
49. Case có `Canh lỗi cũ` mà fail phải báo gấp vì đó là regression.
50. Retest phải ghi SHA mới và so lại protected comparator.

## 8. Dry-run đồng bộ issue

51. Xem trước ba thẻ, không ghi GitHub:

```text
python scripts/tester_case_sync.py --so=3 --json
```

52. Lệnh trên là dry-run mặc định và không gọi `gh`.
53. Dùng `--bo=N` để bỏ qua N case đầu, `--so=N` để giới hạn N case.
54. Dùng `--sua=<issue-number> --bo=N --so=1` để chuẩn bị preview sửa đúng một issue số thật.
55. Đọc kỹ title, body, labels và command preview trước khi xin quyền ghi.
56. Chỉ thêm `--that` sau khi đã xác minh repo, đăng nhập, Owner gate và một preview thật.
57. `--that` là external mutation; không dùng trong pytest/local dry-run.
58. Nếu `gh` trả lỗi, script phải trả nonzero; không báo thành công.

Xem riêng ba case P0-05E mới mà không ghi GitHub:

```text
python scripts/tester_case_sync.py --bo=31 --so=3 --json
```

## 9. GitHub readiness

59. Repo/issue/labels đã được kiểm; P0-05E đã có comment/readback trên tracker #412.
60. GitHub Project đích là `TOAN AAS Web App · Tester P0`; PR #417 đã được gắn và đọc lại thành công.
61. PR #417 đã merge/deploy tại runtime `9785541`; PR #419 Auth đã merge/deploy tại runtime `0dd8ffa`.
62. Motion đã qua local acceptance và tiếp tục trong PR riêng #418; sau rebase, base đúng là `main` tại `0dd8ffa`, không còn stacked trên branch PR #417.
63. Merge/deploy/live vẫn là cổng riêng; không suy từ local PASS, push, PR hoặc CI.

## 10. Thứ tự test A09 Auth/Admin shell

64. Chạy WA-41 trước: đăng nhập Admin, kiểm đủ nhóm server cấp ở sidebar dọc và rail ngang bằng `0` trên 1440/1024/768/390/360.
65. Ở 1024, đo cạnh phải sidebar và cạnh trái workspace; overlap và gap đều phải bằng `0`.
66. Chạy WA-42 với missing, partial, explicit-zero và real fixtures; không dùng card/chart giả để làm giao diện trông đầy.
67. Xác nhận “Truy cập nhanh” chỉ có route server cấp; không gọi route shortlist là task inbox.
68. Chạy WA-43 cho VI/EN ở light/dark; ZH key symmetry kiểm bằng contract. Fixed chrome không trộn ngôn ngữ ngoài tên riêng/ID/technical data.
69. Ở 390/360, mở drawer bằng menu: role dialog, aria-modal, focus nằm trong drawer; Escape đóng và trả focus về menu.
70. Đo logo cả VI và EN; tỷ lệ width/height phải `1.00`, ảnh không translate/crop.
71. Ghi riêng bounded table scroller được phép; mọi app rail hoặc page-level horizontal scroller đều FAIL.
72. Security artifact A09 có thể được tham khảo nhưng workbench `FAILED_INFRA` không được ghi thành plugin PASS.

## 11. A09 mở lại: không trộn ngôn ngữ ở trang hỗ trợ

73. Tiếp tục WA-43 trên `/admin/support` và một yêu cầu thử nghiệm có sẵn; không tạo yêu cầu production để lấy ảnh.
74. Chọn Tiếng Việt, áp dụng và tải lại. Kiểm tra tiêu đề tab, đường dẫn điều hướng, bộ lọc, ô chọn, mô tả, phân trang, nhãn trạng thái, ngày giờ và trang chi tiết. Không chấp nhận Manager, Operator, case, revision hoặc triage xen vào câu Việt.
75. Chọn English, áp dụng và tải lại. Toàn bộ nội dung cố định phải là tiếng Anh; nội dung yêu cầu và tên do người dùng nhập giữ nguyên, không được tự dịch.
76. Với mỗi ngôn ngữ, kiểm tra sáng/tối tại 1440/1024/768/390/360; danh sách và chi tiết tạo thành 40 trạng thái. Chụp cả phần dưới trang chứa phân công, chuyển cấp, biểu mẫu và nhật ký; ảnh đầu trang không chứng minh phần dưới đã đúng.
77. Không gửi phản hồi, đổi phân công, chuyển cấp hay trạng thái trên production. Nhánh ghi và thông báo xác nhận phải được kiểm tra bằng dữ liệu QA riêng.
78. Lưu log thô. Phân biệt 401 trước đăng nhập, thông báo mức info và lỗi sau khi đăng nhập; không loại toàn bộ 401/404 khỏi kết quả. `/favicon.ico` 404 hiện là lỗi nền được ghi riêng, không phải bằng chứng console hoàn toàn sạch.
79. Ghi rõ SHA mã thử, SHA triển khai và môi trường. 40 trạng thái local không thay thế bằng chứng production.
80. Ở bản Việt, danh từ tiếng Anh và mã kỹ thuật được giữ theo allowlist hữu hạn: TOAN AAS, Web, Telegram, PayOS, Odoo, Bot, Email, App, ERP, CSRF, SLA, API, ID, PDF, QR, OTP/CVV, TXID, URL, PNG, JPEG, WebP, TXT, MB, Xu. Mọi từ tiếng Anh khác trong câu cố định là lỗi cho đến khi Owner duyệt thêm ngoại lệ.

## 12. A09 mở lại: Điều hành tự động

81. Tiếp tục WA-43 trên `/admin/operations`; dùng tài khoản QA có quyền sẵn, không tự nâng role và không tạo bản ghi production để làm đầy giao diện.
82. Kiểm guarded/loading/Manager/Operator/partial/empty/populated bằng contract executable. ID, mã tác vụ và mã máy giữ nguyên; mọi tiêu đề, mô tả, phân trang, xác nhận và nhãn trạng thái phải theo locale.
83. Chạy VI/EN × sáng/tối × `1440/1024/768/390/360`. Desktop có bốn metric và hai grid hai cột; `<=980px` grid chính một cột; `<=700px` metric, thẻ và nút một cột. Page overflow, clipping và high-level horizontal scroller đều bằng `0`.
84. Đo contrast chữ chính/phụ tối thiểu `4.5:1`, hành động cao tối thiểu `44px`, focus visible. Empty state dùng surface teal-soft, không mảng xám tối hoặc số/biểu đồ giả.
85. Đổi VI→EN→VI qua header và chờ hydrate hoàn tất; DOM không được quay về locale cũ. ZH kiểm bằng renderer contract cho đến khi header Admin chính thức mở lựa chọn ZH.
86. Không bấm duyệt/từ chối trong production. Browser receipt phải ghi request ghi Operations `0`; action forms và expected revision được chứng minh trong local contract.
87. Bằng chứng local hiện hành nằm tại `evidence/a09-admin-operations-locale-20260910/browser/`: `20` trạng thái, `14/14` assertions, relevant event `0` và submit `0`. Sau deploy vẫn cần signed production read-only riêng.
