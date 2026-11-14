# Phiên NAV-LEGACY-WORKBENCH-20261113

BASE: `c4da5f4a90a4ca37c46b66220c81928b806a4f2a`. Tracker: Issue #689.

|Mã|Điều kiện bắt buộc|Bằng chứng local|
|---|---|---|
|NAL-LABEL|Nhãn nhóm cố định theo VI/EN/ZH, không dịch tên khách/unknown|27 ca,3baselineđạt/24lỗi→27đạt|
|LWR-HELPER|Mọi đầu vào helper không tạo panel/claim/alert/thành công giả|18 đầu vào thật, không mock helper|
|LWR-RENDER|Bỏ đúng panel video/tài liệu/nội dung, giữ mọi dữ liệu/form/control/markup bên ngoài|120 renderer ở20route×3locale×2state|
|LWR-MUSIC-IMAGE|Hai nhóm đã rỗng vẫn rỗng, real form/quote/confirm không đổi|Hồi quy Image/Music, hai chốt caller giữ|
|LWR-NATIVE|Nhóm ảnh/tài liệu/nội dung390/1440,3locale và click sang video|18view/18click,0CSP/console/pageerror/overflow/panelgiả|
|LWR-SOURCE|Ngoài một alias và một helper, nguồn giữ nguyên|Inverse compare toàn bundle,3consumer/18protectedfiles exact|
|LWR-ISOLATION|Không gọi ngoài hoặc ghi sản phẩm/ví/production|6plan18scene/versions/evidence giữ;21ownedprocesses→0|
|LWR-DELIVERY|CIexactHEAD,merge/deploy/runtime/assets có receipt riêng|Theo cùng Issue #689 và PR đợt này|

Nhóm421Nodeđạt đã gồm27alias+138helper/renderer, không cộng chồng lấn.
30Pythonđạt/1CSS-tail BASE-equivalent, compile đạt; không sửa motion/theme
để xanh. Kiểm tra metadata case chạy riêng sau cập nhật nguồn case chuẩn.

Phạm vi native không gồm entry `/features` nhẹ riêng, mọi theme/trạng thái,
thiết bị/Safari hoặc phiên production. Phiếu status-grid Hội viên đã rút do
spec thiếu dữ kiện CSS; không áp dụng mã hoặc tạo issue cạnh tranh.
Trạng thái: READY cho gate CI/release sau local; chưa coi là production LIVE.
