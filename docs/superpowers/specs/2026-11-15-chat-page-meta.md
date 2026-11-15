# CHAT-PAGE-META — 15/11/2026

Đang đọc và áp dụng skill owner-governed-codex cho task này.

GOAL=Tiêu đề, mô tả, dấu dẫn đường và tiêu đề tab của trang trò chuyện dùng đúng VI/EN/ZH, không đổi tên/nội dung do khách nhập.
BASE_SHA=0e97fd8a39950b67e7a6b68a2bf17aa8d3cece01
BRANCH=codex/chat-page-meta-20261115
TRACKER=Issue689/checklist mẹ WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-R218.md
DEPENDENCY=PR740 đã giao; CI43683345433/deploy43684233179, runtime/cây/năm tệp công khai khớp.

## Phạm vi và tác động

Áp đúng hai proposal Antigravity công khai576db2 có cùng app bytes với merge0e97:
client5thay thế trong `portal.js`/`portal-i18n.js`; shell2 trong `copyfast_pages.py`.
Hai khóa/locale, sáu giá trị. Tiêu đề: Trò chuyện / Chat / 对话; mô tả nói rõ
viết và lưu mục tiêu, tham khảo, ghi chú để xem lại, không hứa trả lời tự động.

Giữ raw registry/resolver, tên cuộc trò chuyện/h2/form/tag khách, shared menu keys
và `/chat/new`/invalid/nonChat sentinels. Dịch tại consumer sau chọn locale,
không dịch sớm ở resolvePage vì resolve chạy trước applyInterfaceLocale.
SSR chỉ thêm entry `/chat` và nhánh UUID fullmatch dùng cùng entry; regex,
locale trust, auth, HTML escaping, descriptions/cache/build stamp và legacy
`_title_for` không đổi. Không CSS/motion/API/engine/ví/PayOS/ENV/data changes.

Impact scan thực tế: `localizedPageTitle`10lexical occurrences trong portal.js
(định nghĩa/typeof/tám call); `localizedPageDescription`3(def/hai call);
`supportTicketHeroSection`2(def/call), `_shell_title_for`2 trong copyfast_pages.py
(def/call). Hai tệp consumer sản phẩm, thêm catalog là ba appfiles.
Đây là shared presentation có guard hẹp; không rename hoặc đổi chữ ký helper.
Tests không được bỏ assertion tên khách hoặc đổi snapshot toàn cục cho xanh.

## Checklist trước áp dụng

- [x] Quan sát native trước có fixed “AI Chat Workspace”; đọc actual title/locale/SSR call path, phân biệt legacy resolver không phải đường first paint.
- [x] Hai phiên Antigravity riêng đã trả bảy thay thế đúng nguyên văn; public byte/hash/full actual MAP được xác thực, không M1/lỗi mã/rerun.
- [x] Permanent VM14RED/SSR6RED3PASS trên BASE, actual bundle/HTMLResponse.
- [x] NativeBASEVI375detail fixedchrome cũ, data/source giữ, Jobs0.
- [x] Bảy exactthay thế/ba apphashes đích/hai orderedkeys.
- [x] Node476nghiệmthu473+3affected, locale/fallback/escape/customer giữ.
- [x] Python69PASS gồm root/detail/invalid/nonChat/locale-trust, không wholeauthclaim.
- [x] Native12unique/6ảnh/onefreshserver, response/hydratedtitle đúng, noreseed/Jobs0.
- [x] SourcereviewC0/I0/M0/18protectedLF/current-originaldocs/Tester;
  case1325lines145383bytesLF/exactSHA, changedmetadata1testPASS.
- [ ] Provenance/exactCI/merge/deploy/runtime/fiveassets và receipt riêng.

Chỉ local QA riêng dùng dữ liệu giả và secret child-only hiện hữu; không sửa
ENV hoặc phiên khách/production. Các file QA/bằng chứng không gửi worker.
Không đụng Bot/route-engine/provider/wallet/PayOS/productiondata.
M-FINAL01..06 vẫn cuối; goal không đóng từ một title unit.

## Amendment bằng chứng sau grouped GREEN

Native12quan sát đã đạt, kiểm Node473PASS/3FAIL. Ba lỗi nằm trong sentinel
đòi toàn trang `/features/content` bất biến; source có consumer thẻ `/chat`
dùng chính `localizedPageTitle/Description`. Phép đối chiếu riêng đo đúng
hai text node h3/p của thẻ đổi theo bộ chữ mới; toàn bộ attributes/actions/
badges/markup thẻ và toàn HTML bên ngoài giữ nguyên từng byte ở ba locale.
Giữ tên/mô tả mới đồng nhất trên thẻ là đúng mục tiêu khách dùng; không
sửa app để quay lại chữ cũ. Amendment test chỉ chiếu đúng hai node của một
anchor `/chat` duy nhất sang expected cũ rồi so toàn trang, không regex lọc
từ hoặc bỏ assertion. Ba route sentinel khác và mọi tên khách giữ nguyên.
Đây là spec/harness quá rộng của điều phối, worker code failures0.
Chỉ chạy lại ba test đã fail;473ca đã đạt không chạy lại.
