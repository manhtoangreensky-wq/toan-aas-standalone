# Báo cáo trước push — chi tiết âm thanh

TASK=MEDIA-DETAIL-CUSTOMER-COPY-20261121.
BASE=051b936695638a5f083396194730861dc7831da1.
BRANCH=codex/media-detail-customer-copy-20261121.
TRACKER=Issue689/comment7058931880.
PUSH_GATE=READY.

## 1. Review và tài liệu vận hành

Chỉ portal.js/portal-i18n.js/portal-theme.css ứng dụng,53 records
được giao đúng năm proposal CLI Antigravity model3.8FlashHigh/fullMAP.
148 nguồn khác giữ BASE RAW/LF, không đổi integration.js hoặc
shared factory. Review nhóm đã đóng finding QA fixture gợi ý bằng
7 changed/new case PASS; một rule item-contrast được Root đối chiếu
đúng measured failure, không mở rộng sang Hub/dark/token/layout.

Tài liệu vận hành phân biệt production PR784/runtimeBASE đã giao
với ứng viên hiện tại. Không dùng dữ liệu production để đo hoặc
đưa vào báo cáo. Quyền, API, DTO, UUID, revision, lịch sử, điều hướng,
tải xuống và nội dung khách được giữ; chỉ nhãn/chữ/màu vùng đã chốt.

## 2. Đối chiếu chức năng gốc

Nguồn thực docs/migration/MUSIC_MEDIA_WORKSPACE_CONTRACT.md,
mục Parity map/Lifecycle/API. Crosswalk nguyên văn đã thêm vào
TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md: gợi ý vẫn là văn bản,
chọn/liên kết/tải/quản lý âm thanh giữ. Thuật ngữ cơ chế trong tài
liệu không còn là chữ bắt buộc hiện cho khách. Không xóa chức năng
để xóa mô tả. Validation/write-copy còn ở đơn vị kế tiếp rõ ràng.

## 3. Tester và bằng chứng

Tám case MDCC trong DANH-SACH-CASE.md là nguồn duy nhất; phiên
KIEM-THU/PHIEN-MEDIA-DETAIL-CUSTOMER-COPY-20261121.md và hướng dẫn
đã có. Giữ Issue689, hai mẫu issue và12 nhãn hiện có; không tạo
project/issue/PR giữ chỗ hoặc thay quyền đăng nhập.

Source53gate13PASS, phân trang19PASS, copy/namespace33PASS ban đầu
và7changed/newPASS. Hồi quy giữ4361PASS,17slice failed/changed/
unexecuted43PASS, không cộng trùng; bảng union per-file/case được
Tester kiểm từ XML một lần:4565uniquePASS/0FAIL/0skip,149/149file
trong đúngblocklocale hiện tại.4303selected-owner+262imported-owner;
không gọi bảy module import là thêm bảyworkflowfiles. Python48historicalPASS và11PASS/
4same-exactBASEFAIL, không sửa lan sang Portal cũ.

NativeR1/R2/R3 finite scope accepted:384distinctcontrols/
12ảnhcoverage gộp;22knowncontrastrecoveries,12offline required-
annotation checks và6Hubtitles có bằng chứng thật. Source/core/
schema/auth/egress/owned0 giữ; app không đổi sau native. R3 chỉ
1newcontrol/1newPNG, không lặp phần đã đạt. False receipts giữ.
163+4unknown vẫn NOT_CLAIMED, không nhận globalAX/contrast.

## 4. Phạm vi công bố

Explicit allowlist source/test/docs/report/QA workflow và hai Web
provenance chuẩn. Tám state paths chỉ liệt kê tên để loại; không mở
campaignstate/không stage bất kỳ statefile. Không gửi credential/
raw auth/customer data/local QA DB hoặc blob.

Root chốt Tester supplement/metadata, secret scan, git diff check,
source151/forward53 và manifest trước sourcecommit. Refresh Web-only
provenance không đọc Bot, verify đúng HEAD. Một push/PR, exact CI,
merge/exclusive deploy/VPS/assets/build/receipts; không dùng HTTP200
để nhận signed UI/engine output. Whole goal ACTIVE; motion cuối.

Gate thực nghiệm: Tester supplement0Critical/Important, unique4565/
149locale files; metadata consumer1PASS/32deselected. Manifest dry
validation35scopedfiles/2provenance dự kiến, tám state excluded,
source151/protected148/secret0/diffcheck đạt. Bản manifest cuối ghim
đúng bytes sau cập nhật tài liệu này trước sourcecommit.
