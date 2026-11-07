# Hướng dẫn Tester TOAN AAS Web App

## Phiên thông báo thao tác Lịch nội dung — 07/11/2026

ID `CALENDAR-ACTION-FEEDBACK-20261107`, BASE
`f70d653da80642c9a844a05179a46d3277a464ca`; case CAL-ACTION-01..03. Kiểm cả
bấm Lọc, Tháng trước/sau và Làm mới, không chỉ đọc tiêu đề hoặc nội dung tĩnh.
VI/EN/ZH phải có thông báo thành công/lỗi/guard đúng ngôn ngữ; unknown message
không bị thay bằng câu chung. Dữ liệu lịch, tên khách và giá trị bộ lọc giữ nguyên.

Giữ GET pending rồi đổi trang, phiên/tài khoản, đăng xuất, selection hoặc gửi
lượt mới; response cũ không được hiện toast hoặc mở lại nút mới. Lượt hiện hành
vẫn phải hiển thị lỗi nếu tải thất bại và mở controls khi chính lượt đó kết thúc.
Không bỏ qua lỗi hiện hành chỉ để làm test stale xanh.

Đã đo 108/108 Node, 1.670/1.670 full Node và9/9 Python/native/contracts. Ba GET
nguyên gốc từ DB tạm qua full integration kiểm đủ chín action/locale. Browser
36/36 bấm nút/submit thông thường đạt, mỗi case đúng một GET và toast nhìn thấy,
0page/console/external/write/unknown. Khởi tạo đăng nhập browser bị chặn ở seam
QA và bootstrap tổng hợp; không gọi đây là bằng chứng signed production auth.
Không gọi provider/ví/PayOS hoặc tạo lịch đăng/tác vụ. Ghi CI exact-head, runtime
VPS và signed production UI riêng; metadata POSIX Linux phải đạt, không hạ test.

## Phiên Lịch nội dung — 06–07/11/2026

ID `CALENDAR-LOCALE-PRESENTATION-20261106`, BASE
`9137c0c037995b59e178edc1055eec825ace6f73`, case CAL-LOCALE-01..CAL-SAFETY-05.
Kiểm đủ VI/EN/ZH và năm trạng thái: đang tải, tải lỗi, chưa có quyền, đọc xong rỗng,
đọc xong có mốc. Không chấp nhận thông báo “chưa có mốc” thay cho lỗi/chưa có quyền,
hoặc số 0 khi chưa đọc được. Tên khách và Facebook/TikTok phải giữ nguyên.

Hai khối giải thích tĩnh không còn; biểu mẫu tháng/trạng thái/nền tảng và hai liên
kết cuối trang phải còn. Count đúng ở đầu bộ lọc chỉ khi đã đọc xong và phải nhìn
thấy trên ảnh/thực tế, không chỉ tồn tại trong DOM. Không dùng class huy hiệu đã
bị chính sách giao diện khách ẩn để chứa count. Thử ba thẻ
trong grid và bốn mục trong agenda để bảo vệ overflow. Input/select ở ≤620px cần
16px, không tắt zoom. Thử đổi tháng/status/platform rồi trả lại, không submit trong
ma trận presentation. Kiểm theme, menu/Escape, palette/Escape, Tab/focus và tràn.

Hiện có 39/39 Node, 8/8 Python/native, 1.562/1.562 full Node và review C0/I0/M0.
Browser 90/90 cấu hình đã đạt, không lỗi trang/console hoặc request API/ngoại mạng/
ghi; có báo cáo riêng và ảnh cho mỗi cấu hình, không lấy pilot2/2 thay cho toàn
ma trận. Không dùng kết quả localhost để gọi signed production LIVE.
Mọi case provider/ví/PayOS, lịch đăng, thông báo bên ngoài và ý định nhắc việc
vẫn ngoài phạm vi. Không thay yêu cầu quyền tệp POSIX của metadata Tester chỉ vì
Windows không có cùng chế độ; Linux CI phải đạt trước phát hành.

## Phiên bổ sung giữ nguyên phản hồi — 06/11/2026

ID `PUBLISH-REVIEW-FEEDBACK-PRESERVATION-20261106`, BASE
`5aa0683c72b79445e525d8c33c4dd0eecf8934eb`; case PR-FEEDBACK-06..08.
Thông báo riêng ngoài bảng phải giữ nguyên ở VI/EN/ZH, không bị thay bằng câu chung.
Kiểm success, guarded, guarded-error và transport; thử cả constructor/toString/
__proto__. Bảy câu hệ thống được ánh xạ đúng ngôn ngữ; không dịch nội dung khách.

Chạy `node --test tests/publish-review-feedback-preservation.test.mjs`: 42/42 đạt
sau baseline 21 đạt/21 lỗi. Bộ tập trung hiện tại 119/119, full indexed Node
1.523/1.523; Python/native 10/10 gồm native API→integration→toast ở ba locale.
Metadata Tester trên Windows có một lỗi quyền tệp POSIX đã tồn tại (0666 thay
0600), 32 ca khác đạt; không bỏ qua hoặc hạ yêu cầu, phải kiểm lại trên Linux CI.
Đọc riêng kết quả CI, merge, deploy, runtime SHA và giao diện production. Không
lấy DB tạm, thông báo thành công hoặc HTTP200 làm bằng chứng đã đăng bài thật.

## Phiên Gói rà soát trước khi đăng — 06/11/2026

ID `PUBLISH-REVIEW-LOCALE-20261106`, nguồn PR-RECEIPT-01..PR-FEEDBACK-05.
Kiểm API native trong DB tạm, rồi đưa response vào renderer thật ở VI/EN/ZH.
Không thay title/caption/hashtags/CTA/source prompt/checklist/copy_instruction của
khách; chỉ kiểm nhãn/hướng dẫn/phản hồi cố định. Đọc receipt lần hai; thử từng cờ
true/thiếu, execution sai, field thừa và transport lỗi.

Với currentness, giữ request pending rồi đổi route, epoch, account, authenticated,
capability và CSRF; gửi thêm lượt compose để kiểm response cũ không merge/toast/mở
control. Lặp guarded/error/success và xác nhận bridge không cần bật. Evidence local:
Node77 copy/receipt/currentness, Python/native10, full indexed Node1481; CI exact-head,
deploy và signed UI quan sát thực tế vẫn phải ghi riêng.

## Phiên Gói rà soát trước khi đăng — 06/11/2026

ID `PUBLISH-REVIEW-LOCALE-20261106`, nguồn PR-RECEIPT-01..PR-FEEDBACK-05.
Kiểm API native trong DB tạm, rồi đưa đúng response vào renderer thật ở VI/EN/ZH.
Không thay title/caption/hashtags/CTA/source prompt/checklist/copy_instruction của
khách; chỉ kiểm nhãn/hướng dẫn/phản hồi cố định. Đọc lại receipt lần hai để bắt
lỗi mất proof; thử từng cờ true/thiếu, execution sai, field thừa và lỗi transport.

Với currentness, giữ request pending rồi đổi route, session epoch, account,
authenticated, capability và CSRF; gửi thêm lượt compose để kiểm response cũ
không merge/toast/mở control. Lặp guarded/error/success và xác nhận bridge không
cần bật. Các cổng đạt hiện tại: Node77 copy/receipt/currentness, Python/native10,
full indexed Node1.481; CI exact-head/deploy/live vẫn phải ghi riêng. Không dùng
HTTP 200 để kết luận đăng bài, provider hay output media thành công.

## Phiên Chiến lược kênh — 06/11/2026

ID `CHANNEL-STRATEGY-LOCALE-20261106`, nguồn case CS-LOCALE-01..CS-NAV-04
trong `KIEM-THU/DANH-SACH-CASE.md`; BASE `8c85f84966ab3e0f53bf97a2999e221b23901bcf`.
Phạm vi là hai route `/content/channel-strategy` và trang chi tiết bên dưới.
Giữ nguyên dữ liệu khách; chỉ chữ cố định theo VI/EN/ZH được dịch. “Trang web” là
nhãn tiếng Việt hợp lệ cho giá trị `website`; tên Facebook/TikTok giữ nguyên.

Chạy 29 kiểm tra Node và 6 first-paint, rồi kiểm library/detail/archive ở ba
ngôn ngữ, sáng/tối, 360/768/1440. Sau sửa font đã có 54/54 cấu hình trình bày đạt;
chỉ báo Đăng bài ở trang chi tiết cũng đạt54/54 sau RED nhầm sang Công cụ.
Helper revision cục bộ phải giữ giới hạn 1–1.000.000; kiểm sai/thiếu revision
không được mở quyền. Không bỏ qua lỗi hoặc dùng cờ ép thành công.

Bản trình duyệt dùng dữ liệu tổng hợp và chặn request ngoài/API/ghi; không phải
bằng chứng phiên đăng nhập production, tạo/lưu hồ sơ thật hoặc kết nối mạng xã hội.
Trước bàn giao, ghi source revision/hash, output hồi quy, review, CI và runtime
riêng; không lấy báo cáo người sửa thay cho kết quả Tester độc lập.

## Phiên SD-D4 — 24/10/2026

Session `R218-SDD4-TESTER-20261024`, manifest
`reports/tester/R218-SUBDUB-D4-20261024.md`, case SDD4-01..08 trong nguồn duy nhất.
BASEba4b2dfa; source là worktree chưa push, xác minh bằng bốn LF hash, không chỉ HEAD.
Chỉ DB/tài khoản QA cô lập; không điều khiển IDE, không đụng đăng nhập hiện có.
Khi dùng tài khoản giả, email phải lowercase như register/login hiện có.

Nút “Giữ âm thanh gốc”: thử37→tắt0→bật37, nhập0/1/100 và giá trị sai;
kiểm cả number/range/output/review và âm lồng tiếng0/200/ack riêng. Thiếu mức nhớ
hợp lệ thì bật về100. Hai mode/Voice saved+custom phải giữ draft; kiểm URL mode
roundtrip đầy đủ, Voice return canonicalmode+locale và actualtheme giữ nguyên.

AccountA/B phải khác email và browser projection khớp; sau B53off→logout,
root vẫn có2switch disabled, không chấp nhận assertion rỗng. Real login lại B
phải100/on/offon100. Dispatch persisted-pageshow là diagnostic handler thật,
không phải native BFCache. Respect register4/login8 mỗi60s:giãn31s/case.
Không disableauth/rate hoặc giả payload/session để chạy nhanh. Đếm UIwrites0
khác tổngHTTPwrites: setup register/login/profile trong QA là mutation có thật.

Main48 đã terminalPASS; supplement42 phải terminalPASS trước verdict cuối.
Đối chiếu rawSHA/unique/4assetLF/sourceHEAD/scriptSHA và các ảnh thực. Source
review độc lập C0/I0/M0; Tester vẫn phải tự chạy unit/portable contracts và đọc
artifact. Không suy engine/output/production/LIVE hoặc hoàn tất toàn21SD.

## Phiên SubDub E3 — 24/10/2026

ID`R218-SDE3-TESTER-20261024`, manifest
`reports/tester/R218-SUBDUB-E3-20261024.md`;8caseSDE3-01..08 trong nguồn
`KIEM-THU/DANH-SACH-CASE.md`. Không mở lạiissue412đãđóng. Trackerbatch664/PR661.
Sourcecandidate26a966e2;đọc riêng finaldeliveryHEAD từGit saupush,không đoán SHA.

Chỉ QA DB/tàikhoản tạm; không tài khoản/filegiọngkhách. Browserplugin không có,
dùngheadlessEdgeđãcài; không mởIDE/cửa sổ/login/logout/settings. Test normal
click/Tab khiSubDubpending,không forceclick haygáncontrol để giảauthoring.
Khi giữnguồnresponse dùng realroute.fetch rồifulfill cùngresponse;không logtoken.

Đọc đầy đủartifact và số tổ hợp: readiness72, pending12, regression168 là ba
ma trận khác nhau,không cộngthành sốngườidùng. Pending12 không cóhashassetriêng.
Parentfinal168 riêng phải qua strictcounters0/actualfourassethashes/sourceSHA.
Disabledupload/CTA không phải lỗiUIđượcphép bật;capability/engine/outputT0.
U1C3AXcauseUNKNOWN/U2originalrunstateUNKNOWN cònnguyên dùcurrentgateđãsửa.

Mỗi kết quả ghi command/exit/count/source/rawhash và phạmvi đãkiểm. Giữ riêng
32portabletestercontracts/1WindowsPOSIXdeselected,khôngche thành33pass.
ProjectGitHub thiếu read:project thì ghiunavailable;khôngtựauthrefresh/xóađăngnhập.


Đính chính 21/10/2026: các matrix chỉ đổi URL lang không chứng minh locale đã
đăng nhập; phải set hồ sơ QA bằng endpoint CSRF và assert `html.lang` cùng
profile locale. Không dùng main/text-length/overflow/no-media để đóng
interaction/AX/screenshots hoặc motion. Các số smoke lịch sử giữ nguyên,
nhưng không còn là nghiệm thu toàn nhóm. Nguồn đính chính:
`reports/audit/R218-EVIDENCE-RECLASSIFICATION-20261021.md`.

## 1. Nguồn case

1. Nguồn duy nhất là `KIEM-THU/DANH-SACH-CASE.md`.
2. Với luồng chung, chọn đúng một ID trong `WA-01..WA-48`; với bộ kiểm thử sản phẩm chuyên biệt, dùng mã đúng nhóm trong `DANH-SACH-CASE.md` (ví dụ `IUI-01..05` cho Image, `MUI-*` cho Music, `VUI-*` cho Voice). WA-44 kiểm Operations readiness, WA-45 Reliability, WA-46 hàng chờ bàn giao nội dung, WA-47 hàng việc điều hành, WA-48 danh sách khách hàng tiềm năng ẩn danh.
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

### WA-49 — Customer 360 locale/fixed chrome

45. Dùng candidate SHA đã ghi trong PR; tạo hoặc dùng `canonical_admin_qa` chỉ trong DB QA cô
    lập, không dùng tài khoản production và không gửi thao tác ví/provider.
46. Mở Customer 360 ở VI, EN, ZH và hai theme tại `1440/1024/768/390`; kiểm tra tiêu đề,
    thẻ trạng thái, ví/tài chính, tác vụ/tệp, hỗ trợ, nhật ký và modal khóa/mở khóa.
47. Ở VI, fixed chrome không được còn `Charged`, `Tier`, `Assets`, `Support Desk`, `Audit Trail`;
    dữ liệu server như mã khách, role/status, mã case, thời điểm và action/outcome không dịch.
48. Không bấm xác nhận khóa/mở khóa, approve top-up, cộng Xu hoặc bất kỳ CTA ghi nào; chỉ kiểm
    keyboard/focus, DOM/AX, overflow/clip, console và network request.
49. Ghi rõ `3/3` locale, viewport/theme, expected/actual, ảnh/DOM/AX, console/network và
    `runtime SHA` nếu có. Nếu thiếu `py`/`pytest` hoặc fixture thì ghi `BLOCKED`, không đổi
    dependency và không suy diễn thành PASS.

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

## 13. A09 mở lại: Theo dõi độ ổn định

88. Chạy WA-45 local enabled với tài khoản Admin QA: kiểm `20` trạng thái VI/EN × sáng/tối × `1440/1024/768/390/360`; không dùng production để tạo dữ liệu giả.
89. Hàng “Việc cần kiểm tra” phải đứng trước số liệu; metric mobile dùng lưới 2×2; empty state không dùng mảng xám nặng; phần thông tin kỹ thuật đóng ban đầu.
90. Dùng bàn phím Enter mở rồi đóng “Thông tin vận hành và quyền truy cập”; focus phải nhìn thấy, nội dung không lồng nhiều card và không mất cảnh báo an toàn.
91. Chọn bộ lọc trạng thái/mức độ trên local; request chỉ đọc. Không bấm tiếp nhận/xử lý/mở lại trên production.
92. Chạy local disabled riêng ở `1440/390`, sáng/tối, VI/EN. Trạng thái phải nói module chưa bật, không nói tài khoản thiếu quyền, không có action ghi và có lối về trung tâm quản trị.
93. Đối chiếu screenshot production cũ với candidate: tiêu đề/eyebrow/copy thuần ngôn ngữ, một status surface, không overflow/clipping và target ≥44px.
94. Sau deploy, production đang disabled chỉ được kiểm read-only. Ghi PR/CI/deploy/runtime SHA và ảnh signed; không đổi ENV để tạo màn enabled.

## 14. A09: Hàng chờ bàn giao nội dung

95. Chạy WA-46 bằng một bản ghi QA local ở `review/revision=2`; không tạo hoặc thay đổi record production.
96. Kiểm VI/EN × sáng/tối × 1440/1024/768/390/360; title/purpose do người dùng nhập giữ nguyên, fixed copy phải theo locale.
97. Dùng Enter mở/đóng “Quy trình và giới hạn”; bộ lọc phải đứng trước card, nhãn form đủ contrast và target ≥44px.
98. Xác minh manager thấy đúng hai decision `approved_for_handoff/blocked`, operator không được mở rộng quyền; record ID, revision và cursor không đổi.
99. Browser QA bắt buộc overflow/clipping/framework overlay/relevant console/staff write request `0`; đo contrast cả heading, description, nhãn filter và decision.
100. Sau deploy chỉ kiểm signed read-only; không bấm “Ghi nhận quyết định” trên production.

## 15. A09: Hàng việc điều hành

101. Chạy WA-47 trên projection local năm nguồn; không tạo dữ liệu production, không bấm hành động ghi và không dùng Bot/provider.
102. Kiểm VI/EN × sáng/tối × `1440/1024/768/390/360`; ZH kiểm renderer. Fixed copy phải thuần locale; giá trị kind/state/priority và route đích vẫn là canonical không đổi, còn nhãn hiển thị và định dạng ngày giờ được phép localize.
103. Xác nhận thứ tự `Việc cần xử lý → bộ lọc → kết quả → Nguồn dữ liệu`; phần `Dữ liệu và giới hạn` đóng ban đầu và mở/đóng được bằng Enter.
104. Ở `390/360`, mỗi hàng hiển thị dọc với nhãn cột; không chấp nhận ép chữ, cắt nội dung, cuộn ngang cấp trang hoặc thay `—` bằng `0`.
105. Ghi minimum contrast, target, overflow/clipping, framework overlay, console và write request. Tất cả phải lần lượt đạt `≥4.5:1`, `≥44px`, `0`, `0`, `0`, `0`.
106. Recovery/loading không render bảng dữ liệu cũ; nút phải là `Thử lại` và `Về trung tâm quản trị` theo locale. Pagination vẫn giữ offset và liên kết allow-list.

## 16. A09: Theo dõi khách hàng tiềm năng ẩn danh

107. Chạy WA-48 trên database tạm hoặc fixture manager ẩn danh; không tạo dữ liệu production và không dùng tài khoản khách để tự nâng quyền.
108. Kiểm VI/EN × sáng/tối × `1440/1024/768/390/360`; ZH kiểm renderer. Fixed copy và toast refresh/filter/page theo locale; giá trị kind/stage/consent giữ canonical trong state nhưng nhãn và ngày giờ được localize.
109. Xác nhận thứ tự `Danh sách cần theo dõi → bộ lọc → kết quả`; `Dữ liệu và giới hạn` đóng ban đầu. Loading nói đang tải, failure nói chưa tải được và cả hai không render row cũ.
110. DTO/DOM không được có ID, owner, tên, email, nội dung nhu cầu, tag hoặc note; route không có link detail hay action ghi cross-account.
111. Ở `768/390/360`, mỗi hàng hiển thị dọc với nhãn cột; không cuộn ngang cấp trang hoặc ép chữ. Contrast tối thiểu `4.5:1`, target tối thiểu `44px`.
112. Browser receipt bắt buộc overflow/table overflow/clipping/private leak/framework overlay/relevant console/write request `0`; filter `review` trả đúng tập con ẩn danh.

## 17. AutoPost Hub — APUI-01..04

113. Mở `/publishing` bằng đúng candidate SHA và ghi môi trường trước khi kiểm tra.
114. Kiểm theo thứ tự dọc: 7 nguồn → kế hoạch/thương hiệu → kênh → lịch/hàng đợi → báo cáo/lịch sử.
115. Kiểm từng locale VI/EN/ZH riêng; không đánh dấu đạt nếu bản VI còn từ giao diện tiếng Anh
     ngoài tên riêng đã được duyệt (`AutoPost`, `Affiliate`, `OAuth`, `Asset Vault`, `Campaign`,
     `Project`, `TOAN AAS`).
116. Ở mobile, xác nhận không tràn ngang, không xếp hàng ngang khó thao tác và nút đạt tối thiểu
     `44×44` nếu có tương tác.
117. Handoff chỉ được kiểm tra điều hướng; không bấm để tạo OAuth, bài đăng, lịch, queue, số liệu,
     job, provider call hoặc dữ liệu production. Nếu giao diện hiển thị kết quả/receipt khi chưa có
     server capability, ghi lỗi APUI-04.
118. Ghi rõ control-level/source PASS riêng với browser/AX/live; không gộp các mức bằng chứng.

## 18. Trung tâm hỗ trợ khách hàng — SPUI-01..05

119. Mở `/support`, `/tickets`, `/tickets/:id`, `/admin/support` và
     `/admin/support/:id` bằng candidate SHA đúng; dùng fixture tài khoản/role QA cô lập.
120. Kiểm theo thứ tự dọc: tiếp nhận → lọc/danh sách → chi tiết/dòng thời gian → phản hồi/
     trạng thái → bằng chứng. Không coi việc thấy route hoặc thẻ disabled là đã hoạt động.
121. Chọn VI/EN/ZH riêng; bản Việt phải dùng “Trung tâm hỗ trợ khách hàng”, không để
     `Support Desk`, `Web Support Desk`, `Manager`, `Operator` hoặc thuật ngữ giao diện chưa
     được duyệt lọt vào fixed chrome. Dữ liệu động như mã case, revision, thời điểm và trạng
     thái canonical không tự dịch.
122. Ở desktop/tablet/mobile `1440/1024/768/390`, kiểm focus/keyboard, target tối thiểu
     `44×44`, contrast, overflow/clipping và lưới case chuyển một cột ở `<=620px`.
123. Bằng chứng chỉ được chọn từ Asset Vault riêng; không upload bytes thô tại Support.
     Kiểm loại/kích thước, xác nhận đã che dữ liệu, owner/revision và signed download; không
     dùng bằng chứng thanh toán, QR, OCR, Telegram hoặc provider.
124. Ở Admin, xác minh phản hồi công khai và ghi chú nội bộ là hai phạm vi riêng; cập nhật
     trạng thái/mức ưu tiên phải có ghi chú, role, CSRF và revision do server cấp. Không approve
     top-up, cộng Xu, gọi provider, gửi thông báo ngoài Web hoặc tạo ticket Bot.
125. Ghi riêng source/control-level, browser/AX, CI và LIVE. Nếu capability hoặc runtime chưa
     có, phải giữ `guarded` và `LIVE_PASS=NOT_TESTED`; không dùng `4/4` source để thay thế.

## 19. AD-03 — kiểm tra liên kết hồ sơ Admin

126. Ghi `BASE` và `HEAD` SHA; dùng đúng Admin fixture đã được cấp quyền và một
     fixture customer/foreign owner riêng. Không dùng dữ liệu production để bơm
     reference.
127. Mở các màn hình Admin có record đơn và danh sách `items[]`. Khi server cấp
     reference hợp lệ, kiểm đúng 5 kind: `request`, `job`, `asset`, `report`,
     `audit`; kiểm tối đa 6 link trong một tập và label/id/path không bị cắt sai.
128. Mở từng path và xác nhận chỉ có 5 họ nội bộ `/admin`, `/jobs`, `/assets`,
     `/reports`, `/audit`. URL ngoài, `//`, `\\`, dot-segment thường hoặc mã hóa
     không được điều hướng; record sai kind/ID phải fail-closed.
129. Lặp cùng payload bằng customer/foreign fixture. Trường
     `admin_record_references` phải không xuất hiện ở record đơn lẫn `items[]`;
     không được lộ token, raw bridge field, user khác, provider hoặc URL tải tệp.
130. Ghi DOM/ảnh/AX, console, network và mutation. Không bấm approve, refund,
     charge, retry, delivery hoặc provider; case này chỉ đọc và xác minh
     projection. Contract local `1 passed/56 deselected` không thay cho CI,
     deployed, record thật, RBAC thật hay LIVE.

## R218 checkpoint tester handoff — 21/10/2026

1. Nguồn duy nhất của trạng thái đợt này là `reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-R218.md`;
   các artifact `reports/audit/R218-*-QA-20261020.json` trỏ đúng mức bằng chứng.
2. Đã có browser evidence cho Music `18` cấu hình/36 route states, SubDub `48`, Image `72`,
   tiện ích `120`, Video `48`, Motion `12`; đây là QA cô lập, không chứng minh provider, wallet,
   production hay live.
3. Trước khi báo PASS runtime, tester phải ghi riêng runtime SHA, service health, route/role,
   output cuối, artifact/download readiness và `PROVIDER_CALLS/WALLET_MUTATIONS`.
4. Lỗi ngoài phạm vi presentation phải thêm vào đúng nhóm ledger; không đổi tên case để né lịch sử.
5. Trace CLS/LCP/INP hiện `NOT_RUN`; không được thay bằng screenshot hoặc HTTP 200.

## Phiên Đăng bài — PUBLISHING-LOCALE-20261106

Kiểm ba case AP-LOCALE-01/AP-DENSITY-02/AP-FIRSTPAINT-03 trong file nguồn. Đổi VI/EN/ZH,
sáng/tối và360/768/1440; đọc tiêu đề ban đầu và sau tải, breadcrumb, các thẻ. VI không
giữ AutoPost/Hub/Affiliate/AssetVault/Campaign/Project/Web/hashtag làm chữ cố định.
Giữ tên khách/thương hiệu và các đường dẫn; không thử OAuth, đăng bài hoặc nhập dữ liệu
khách thật. Ba khối hướng dẫn được ẩn, nhưng7nguồn/6khu vực/3link/3nút đang khóa giữ
đúng. Không ghi thành công tích hợp từ việc giao diện đã dịch. Local hiện18cấu hình
trình bày và4renderer; first-paint hiện3/3đạt, bộPythoni18n/boundary33/33; chỉbàn giao
sauCI/merge/deploy vàđốichiếuđúngrevision.

Đã thêm375×812 và844×390 ở3locale×2theme:12/12cấu hình bổ sung đạt. Tổng trình bày
Publishing30/30, giữ7nguồn/6khu vực/3link/3khóa và không lỗi trang/console/tràn/ngắt
luồng menu/theme. BộNode1.379/1.379 và Pythoni18n+boundary30/30 cũng đã đo local.

## Phiên Bản nháp — WORKSPACE-LOCALE-20261106

Phạm vi chỉ là nhãn/cỡ chữ của trang Bản nháp và kỳ vọng chữ của kiểm thử bàn giao.
Chạy các case WS-LOCALE-01/WS-FONT-02/WS-HANDOFF-03 trong file nguồn case.
Kiểm VI/EN/ZH × sáng/tối ×360/768/1440. Bốn control tìm kiếm, trạng thái, quy trình,
chọn dự án phải có nhãn; chữ16px trên điện thoại, desktop15px. Gõ văn bản rồi kiểm
focus/Tab và menu/Escape; không gửi biểu mẫu hoặc dùng dữ liệu khách thật.

Phiên local READY: renderer10/10, bộNode1.375/1.375, nativePython41/41, trình bày18/18
và54lượt kiểmloading/failed/guarded. Kiểm hai ô giải thích đã ẩn nhưng form/trạng thái
lỗi không bị ẩn; nút thư viện đủ chiều rộng, ≥44px ở điện thoại. Chỉ đóng nghiệm thu
production khi có đúng SHA đã triển khai và bằng chứng tương ứng; CI xanh không thay
thế kiểm tra phiên đăng nhập production. Không sửa auth, ví, provider hoặc motion.

Kiểm bổ sung375×812 và844×390 đã đạt12/12cấu hình (3ngônngữ×2theme×2kích thước),
thêm36lượt readstate; ô đang focus không bị thanh điều hướng dưới che. Tổng browser
trình bày của đợt là30cấu hình và90lượt readstate, không phải bằng chứng native backend/LIVE.

## Phiên locale `/studio` và nhãn SubDub — LOCALE-183

Phiên hiện hành `LOCALE183-RELEASE-QA-20261106` ở trạng thái READY: 89 test Node,
16 test Python và 18 cấu hình browser candidate đạt. Phần số liệu 05/11 phía dưới
là lịch sử; đối chiếu hồ sơ `reports/audit/R218-LOCALE-183-RELEASE-20261106.md`
và PR bàn giao để lấy CI, SHA triển khai và kết quả production mới nhất.

Các case `LOCALE-183-STUDIO-01` và `LOCALE-183-SUBDUB-02` trong `KIEM-THU/DANH-SACH-CASE.md`
kiểm tra đúng hai yêu cầu hiển thị, không thay chức năng.

1. Sau khi có build SHA mới, mở ứng dụng bằng tài khoản QA được cấp; ghi lại SHA, locale, theme
   và viewport. Thử ở màn rộng `1440px` và điện thoại `390px`.
2. Chọn Tiếng Việt rồi mở `/studio`. Kiểm breadcrumb, nhãn đầu trang, tiêu đề, đoạn giới thiệu,
   sáu thẻ và các liên kết. Không được còn `Media Studio`, `media`, `brief`, `workspace`, `job`
   hay `browser` trong fixed copy; tên riêng và mã kỹ thuật được giữ nguyên.
3. Kiểm menu trái, trợ lý, dashboard và liên kết Voice ↔ SubDub. VI phải ghi “Phụ đề & Lồng tiếng”; EN/ZH vẫn ghi `SubDub`.
4. Chụp ảnh sau khi tải lại ở từng locale; ghi riêng lỗi console, tràn khung và route đích.
   Không gửi biểu mẫu, không tạo job, không nhập dữ liệu khách thật.
5. Candidate local hiện có `7/7` renderer, `89/89` nhóm locale liên quan, `373/373` test locale rộng trên `67` file và `19/19` Python locale/title.
   Chưa có browser/live evidence cho candidate này; không đánh dấu case production đạt trước khi xem build SHA.
6. Repo hiện đã có `22` nhãn và `2` issue template kiểm thử. Danh sách GitHub Projects không đọc được do thiếu scope `read:project`; không refresh auth và không sửa board.
