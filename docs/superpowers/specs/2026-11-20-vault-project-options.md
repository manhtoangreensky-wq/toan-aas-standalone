# Kho tệp — nguồn danh sách dự án

TASK=VAULT-PROJECT-OPTIONS-20261120.
BASE=4cf8590826846a3f3336a4d7359d53df965c226f.
Dependency: PR780 đã giao và đọc lại biên nhận; nhãn mặc định là protected.

## Lỗi và nguyên nhân đã đối chiếu

Signed bootstrap đặt `projects: []`; route dispatch hiện tại không chứa
`/asset-vault` trong điều kiện gọi `hydrateProjects()`. Trang Kho tệp vẫn
render select `optionsFrom: "projects"` để gắn dự án. Trang
`/media-workspace/new` có GET đúng và đã được quan sát native trong đợt
trước, không dùng trang đó để nhận Kho tệp đã sửa.

## Thay đổi tối thiểu

Trong một điều kiện dispatch hiện có, thêm nhánh
`(assetVaultEnabled && currentPath === "/asset-vault")`. Giữ account guard
bên ngoài, mọi route cũ, thứ tự các hydration và thân `hydrateProjects`.
Không thêm helper, state, request type, fallback, retry hoặc thay endpoint.
Đây là dữ liệu Web riêng tài khoản, không phải nguồn Bot/Bridge.

## Acceptance

1. Mở trực tiếp Kho tệp với signed account và flag bật: gọi reader dự án
   hiện có đúng một lần, query không mang filter/offset của Project Board.
2. Không account hoặc flag tắt ở Kho tệp: không project GET mới. Các route
   dự án/âm thanh cũ có cùng hành vi trước sửa; route không liên quan giữ.
3. Reader thật giữ UUID/schema validation, bounded listing và
   epoch/session/route fences. Lỗi không giữ danh sách từ tài khoản cũ.
4. Native dùng GET thật trên DB QA riêng có dự án active; hiển thị nhãn,
   chọn bàn phím và giá trị UUID đúng. Không stub response/DOM/bootstrap,
   không upload, không đọc/tải blob hoặc gọi engine.
5. VI/EN/ZH, mobile320 tối/desktop1440 sáng; ảnh/console/geometry/source/
   schema/core/auth/egress/owned-process gates đủ. Không nhận toàn AX/WCAG.
6. Proposal, diff, regression, Tester và release bằng chứng riêng; không
   dùng HTTP200/merge/deploy để suy thành công đầu ra.

## File và bảo vệ

Ứng dụng: đúng `static/portal/integration.js`, một nhánh điều kiện.
Kiểm tra mới chỉ cho dispatch/reader/source authority; helper hiện có chỉ
nối inverse hữu hạn nếu cần, không sửa assertion/golden/negative cũ.
Tài liệu ops/crosswalk/checklist/Tester/audit cập nhật kết quả đo.

Không auth/API/backend/Bot/route-engine/provider/wallet/PayOS/ENV/dữ liệu
thật/CSS/layout/motion. Không đọc state campaign của Owner.
Hai lỗi code thật cùng fragment mới Root takeover; transport/spec/QA fault
không tính lỗi worker. Model Gemini3.8FlashHigh bằng CLI hiện có.

Thứ tự: RED → proposal/review/apply → GREEN/native → regression/review →
prepush → một PR/exact CI/merge/deploy/runtime/assets/receipt. Các mục locale
khác sau task này; motion cuối.
