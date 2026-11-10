# Phiên kiểm thử — ba công cụ lập kế hoạch còn lại

SESSION_ID=REMAINING-PLANNER-20261110; Issue #689.
BASE_SHA=e63f073f460e551438fbb8e3627ec232353f3efe.
HEAD_SHA=commit chứa phiên này; receipt CI ghi revision cuối.
TESTER_PROJECT_STATUS=READY; dùng tracker/nhãn/mẫu hiện có, không tạo bảng trùng.

| Ca | Điều kiện | Bằng chứng |
|---|---|---|
|RP-COPY|Script/Cinematic/Storyboard đúngVI/EN/ZH, không ô trang trí|150caseledger,109giữ+41affected;6catalogcuốiđạt |
|RP-FIELD|16/10/10trường, scalar/option/constraint/default không đổi|18fieldrenderđạt,178key;phầnsửa8affected |
|RP-TRANSPORT|Giữmetadatađãxácminh, không bỏnormalizer|36casepass+3actualcomposervalidator;unsafe/mismatchrejected |
|RP-SESSION|Phiênsignedkhôngcóaccount.idvẫnnhậnđúngphảnhồi|30casepass,phản hồicũ/sai route/tắtkhôngđượchiện |
|RP-FORM|NativeCinematicstrchoicehợplệkhôngkhóalưu|RED29/30,GREEN30/30;invalid/changedvẫnchặn |
|RP-FEEDBACK|Note/titlekhiđổiinputtheolocale,giữnguard|RED0/15,GREEN15/15;R2khôiphụcđúngdataset |
|RP-TOAST|Thôngbáotạolưuthậtngắngọn,đúnglocale|138affected+15giữ=153;46câubằng8key/locale;nativecompose/saveđạt |
|RP-NATIVE|18view/9flowtạo-xácnhận-lưu-đọc-mở,font/contrast/focus|18/18;9/9flow;9plan/42scene;162contrastmin5,7971:1;54ảnh,0error/egress |
|RP-DELIVERY|CI/exactHEADmerge/exactSHAdeploy/runtime/assets|Chờreceipt,khôngsuyLIVE |

Một lần kiểm tra nhóm đã xong; sau sửa chỉ kiểm phần ảnh hưởng. Không chạy lại
luồng trước đã đạt khi source không đổi. Owned localhost/SQLite tạm; không
provider/ví/production. Nội dung máy chủ và trang kế hoạch đã lưu là backlog
locale riêng; không biến dữ liệu khách hay thông báo lỗi thành thành công giả.

LOCAL_ACCEPTANCE=PASS. Source hashes trước/sau native giữ;SQLitequick_checkok.
Tổng398khóa mới/locale,9951giá trị cũ giữ.14tệp protected không đổi, ngoài23hàm
Portal không đổi byte;integration khớp hunk review;CSSđúng3rule. PUSH_GATE=READY
sau commit/provenance. CI/merge/deploy/runtime/assets vẫn là cổng riêng.
