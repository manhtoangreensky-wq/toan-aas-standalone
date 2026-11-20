# Bộ sưu tập âm thanh — bằng chứng UI theo ngôn ngữ

TASK=MEDIA-COLLECTION-LOCALE-20261120.
BASE_SHA=4080b879ad8d6ded081aa47313bf9cac67121f0b.
BRANCH=codex/media-collection-locale-20261120.
TRACKER=Issue689/comment7041067092.
STATUS=LOCAL_ACCEPTED_RELEASE_PENDING.

## Phạm vi và nguồn đề xuất

Hai tệp ứng dụng: `static/portal/portal.js`,
`static/portal/portal-i18n.js`. Bốn phiên CLI hiện có dùng
gemini-3.8-flash-high, chạy độc lập chỉ trả đề xuất; Root kiểm rồi ghép
tuần tự đúng tám record. Không đăng nhập/settings mới, worker code
failures0, không tự tiếp quản sửa ứng dụng.

| Phiếu | Record | Proposal RAW SHA256 |
|---|---:|---|
| Defaults | 4 | 0a7c9944814a85497ce9dfd45bf1be3b20c9270cb579fada7a9b7b22c63e79d1 |
| Pagination | 1 | b5b1b1b07166cc04bc64bf50b78d965e33d52f85d52f495cccb27d5ccaa0a426 |
| Cleanup | 2 | bd1af315e0e6b270863af3a2027cad11854dc952b623a40b037b89dfb716ab03 |
| Catalogue | 1 | 2e2fff85a5f747ee144260f9e86b5c32adff08ea82267844e008ce0bc2b68a42 |

Mỗi packet có nguyên MAP và các OLD/NEW hữu hạn, nguồn công khai tại
BASE đã đối chiếu bytes. Không gửi test/fixture/API hoặc login response/
ENV/token/dữ liệu khách/tài chính cho worker.

## Kết quả ứng dụng

- Bốn biểu thức fallback dùng helper dịch hiện có. Chỉ dữ liệu falsy
  nhận mặc định; mọi truthy customer value giữ nguyên String semantics,
  gồm `general`, khoảng trắng, câu quyền VI đã lưu và HTML-like text.
- Bộ phân trang chỉ thêm nhánh chữ cho exact tuple
  portal-media-pagination/media-workspace-page. Không đổi chữ ký,
  offset/previous/next/route/action/attribute/escaping hoặc nhánh khác.
- Renderer chính bỏ policy-aside/wrapper hai cột và execution-summary
  dư. Hai link Kho tệp/Dự án chuyển vào create-footer inline actions.
  Giữ policy function, biểu mẫu/trường/bộ lọc/danh sách/thẻ/sự kiện/
  phiên bản/ngày và quyền. Phần chung Audio Hub dùng cùng renderer;
  overview/next-steps riêng Hub giữ nguyên.
- 38 dòng/114 giá trị: bảy key mới và31 key hiện có. Bốn nhãn hoạt động
  bổ sung trước RED sửa thiếu sót allowlist của Root; không tính lỗi worker.
  Catalogue đăng ký trước equal-keysets/freeze, ngoài allowlist giữ.

Không integration/backend/API/auth/DTO/schema/permission/CSS/motion/
Bot/route-engine/provider/ví/PayOS/ENV hoặc production-data mutation.
Không hứa tạo/phát âm thanh hoặc tự xác nhận bản quyền.

## Kiểm tra đã đo

1. Syntax hai tệp ứng dụng exit0.
2. Full physical portal/i18n:96 ca, BASE51PASS45RED(exit1) →96PASS(exit0).
   Bộ portable cùng kỳ vọng96PASS(exit0). Một test-local exposure,
   không thay hàm production. Fetch/storage/navigation/history/dispatch/
   timers bị chặn; input đóng băng. Đây là VM/DOM tổng hợp, không native.
3. Current-source/historical chain:93PASS giữ + một title-era reader
   failed-only retestPASS; tổng94 ca có bằng chứng. Candidate bằng toàn
   GitBASE cộng tám record,151 physical pins/149 protected được kiểm
   trước inverse. Raw fixture
   `f0da75ecb63d7f0abc432053441502cd8db99fcc487aa4b192a6514c84ea0515`.
4. Snapshot catalogue lịch sử cần inverse entry-level:31 giá trị BASE
   và bảy key thêm mới khóa riêng bằng nguồn BASE thực. Aux RAW
   `03e14f63b5a9018f9ff948c2a4e39153ec25fc3dc8388bbff186e351175423a9`.
   26 ca mới đạt: complete catalogue/order/customer bytes/unknown entries,
   partial/changed/duplicate/reordered/detached/type/locale negatives.
   Không đổi golden/assertions/raw hashes cũ hoặc che key ngoài scope.
5. Node liên quan77 tệp: lần đầu1380PASS/258 failure records, trong đó
   tám module chưa thực thi được suite do snapshot catalogue cũ. Giữ
   1380PASS, chỉ chạy phần lỗi/chưa thực thi:417PASS/3navFAIL. Thêm đúng
   newest finite i18n projection ở reader nav lịch sử, giữ mọi assertion;
   retest riêng ba navPASS. Tổng1800executablePASS/0unresolved, không
   chạy lại toàn bộ nhóm hoặc nhận toàn kho xanh.
6. Python bảy tệp source contracts:121PASS/bốn FAIL. Failed-only child
   đọc đúng hai nguồn BASE vẫn bốn FAIL giống tên/lý do. Một lỗi sys.path
   của runner trước đó không chạy được test và giữ riêng. Không sửa app
   hoặc kỳ vọng các test ngoài scope này.
7. Review nhóm ứng dụng/QA ban đầu và supplemental đúng adapter mới:
   cả hai Critical0/Important0/Minor0 actionable. Supplemental không
   mở lại ứng dụng hoặc nhận native/CI/deploy từ việc đọc code.
8. Tester metadata đo sáu tệp LF-portable; hai ca kiểm48case gốc và
   metadata đạt, không đổi case gốc/remote/P0/safety snapshots.

## Native và giới hạn

Native chỉ localhost, SQLite và tài khoản/metadata giả, secret child-only.
Không gửi form sản phẩm/create/update/upload/blob/provider/ví. Actual
signed page và API GET, không giả bootstrap/route/capabilities.

R1/R2 đại diện dừng vì bước chờ chỉ thấy collection response/ready cũ
trước khi hydrate đủ bốn GET. R3 chờ network-idle và render settlement;
đại diện VI320dark đạt native/isolation/auth/schema/core/source/owned0,
ba PNG đã hash/CRC/full decode. Giữ nguyên receipt đại diện này.

Nhóm remaining R3 dừng tại view thứ hai vì control cũ bị thay khi render.
Một row đủ UI nhưng isolation/auth chưa đạt do chỉ đăng nhập1/3 tài khoản;
không nhận nhóm đó thành PASS. R4 chỉ đổi cách bấm GET-button qua locator,
giữ keyboard project/Tab và mọi assertion. Nó giữ đại diện R3 bằng source/
target/MAP/151rawLF equality qua hai binding QA, không nhận12view cùngbinding.
R4 phát hiện kỳ vọng tự điền lại ô người dùng chủ động xóa nằm ngoài
contract fallback nguồn. R5 bỏ đúng sample đó, giữ fresh/default/truthy/
sourcefalsy assertions; không đổi ứng dụng để ép đạt. R5 gặp429 do chạy
quá nhanh năm view×24read lấp bucket120/60s. R6 giữ rate guard, chỉ giãn
viewstart17s và đăng nhập đủ ba account giả trước khi quan sát.

R6 bảy row đầu đạt UI trên VI/EN, source/core/schema/auth/egress/owned0
đủ; receipt nhóm vẫnfalse vì viewZH320main dừng ở kiểm cuộn control.
Bốn cấu hìnhZH failed/unexecuted là follow-up tiếp theo. Không chạy lại
đại diện R3 đã nghiệm thu; prefix7 cần khóa đủ PNG trước khi được giữ.
R6 prefix7 đã được validator độc lập kiểm21PNG/hash/CRC/full decode,
giữ receipt nhómfalse. R7 thêm focus/settlement nhưng tìm được box cụ
thể của description:bottom781.21875 trên viewport780, vượt ngưỡng
height+1 đúng0.21875px. R8 dùng cuộn chuột thực đưa control vào giữa,
không nới bbox assertion hoặc sửa DOM/CSS/app. BốnZHfollow-up đạt cùng
source/core/schema/auth/egress/owned0. Không chạy lại tám view đã giữ.

Kết quả cuối: R3representative1 + R6qualifiedprefix7 + R8ZH4 =12trục
riêng,36PNG đúng manifest/hash/kích thước/chunk/CRC/IEND/full decode,
214đầu vào không đổi. Cùng151 raw/LF application sources nhưng ba binding
QA riêng; không nhận một lượt12view cùngbinding hoặc viết lại receiptfalse.
Không console/page/network lỗi bất ngờ, product/provider/wallet mutations0,
tiến trình còn0. Native BASE chưa chạy. Báo cáo audit giữ34hash bằng chứng.

Nhánh thiếu quyền và detail-summary fallback có unit/source, không giả
capability để nhận native. Native BASE chưa chạy. Toast VI cũ trong
integration là backlog kế tiếp, không nhận toàn trang đã thuần ngôn ngữ.
Hai route không có file-input; nhãn chooser hệ điều hành không là dữ liệu
catalogue. Không nhận signed production UI, actual audio output, toàn
device/Safari/AX/auth lifecycle hoặc toàn goal. Motion M-FINAL01..06 cuối.

## Phát hành

Prepush/Tester/manifest/secret, một PR, CI đúng HEAD, merge-tree,
exclusive deploy, VPS/assets/build và receipt đọc lại đều là cổng riêng.
Tại thời điểm bản này: local đã nghiệm thu, chưa push/PR/merge/deploy đơn
vị âm thanh. Biên nhận cùng tracker thay thế trạng thái release khi đã giao.

PROVIDER_CALLS=0.
WALLET_MUTATIONS=0.
PRODUCTION_DATA_MUTATIONS=0.
LIVE_PASS=NOT_TESTED.
WHOLE_GOAL_COMPLETE=false.
