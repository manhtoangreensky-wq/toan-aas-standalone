# A09 — Admin Work Queue UX/locale

Spec: `A09-ADMIN-WORK-QUEUE-UX-LOCALE`
Route: `/admin/work-queue`
Branch: `fix/a09-admin-work-queue-ux-locale`
Base: `20437db1344aba0e5fe8d09378fc902855a3d328`

## Kết quả nhìn thấy

Màn hình nay đặt công việc trước thông tin kỹ thuật: hero ngắn, `Việc cần xử
lý`, bộ lọc, kết quả, nguồn dữ liệu, rồi một disclosure `Dữ liệu và giới hạn`
đóng ban đầu. Recovery/loading chỉ còn một surface ngắn với lối thử lại và về
trung tâm quản trị; không hiển thị danh sách cũ.

Fixed copy dùng catalogue `adminWorkQueue.*` đối xứng VI/EN/ZH cho tiêu đề,
nguồn, trạng thái, mức độ, bộ lọc, bảng, phân trang, empty và recovery. Bản Việt
không còn phơi `Operations Desk`, `metadata`, `server-side`, `staff`,
`redaction`, `control plane`, `retry`, `provider`, `delivery` hoặc `deploy`.
Giá trị server (kind/state/priority/time/count/route) không bị đổi.

Các toast sau Refresh, Áp dụng, Xóa bộ lọc và chuyển trang — gồm nhánh thành công,
thất bại và thiếu quyền — cũng đi qua catalogue; không còn toast hard-code trộn
ngôn ngữ. Phần tóm tắt nguồn dùng câu trung tính nên không mâu thuẫn khi một
nguồn ở trạng thái chưa xác minh.

Desktop vẫn có bảng gọn. Ở `≤900px`, từng hàng chuyển thành thẻ dọc có nhãn cột
và hủy tỷ lệ cột desktop; đây là sửa nguyên nhân làm tên nguồn bị ép/cắt ở
`390/360px`, không phải che overflow. Dòng hướng dẫn “cuộn ngang” dùng chung
được ẩn ở breakpoint này để không mâu thuẫn với layout dọc.

## Bằng chứng đo được

- Browser local: `20` trạng thái = VI/EN × sáng/tối ×
  `1440/1024/768/390/360`.
- Tất cả assertion đạt: page identity, locale, theme, task-first, disclosure
  đóng, mobile vertical rows, page/table overflow, clipping, touch target,
  framework overlay, console và write request.
- Minimum sampled contrast: `7.62:1`; touch target nhỏ hơn `44px`: `0`.
- Page overflow, table overflow, clipping, relevant console event, framework
  overlay và request ghi: đều `0`.
- Tương tác thật: chọn `Cần xử lý` rồi `Áp dụng` trả `3` hàng; disclosure mở và
  đóng lại được. Không gọi endpoint ghi.
- Executable integration feedback: `12` tổ hợp action/locale (4 action × 3
  locale) cho success/failure/permission đều trả đúng catalogue; test `5 passed`.
- Browser plugin skill không có trong session; theo fallback đã cho phép, QA dùng
  Playwright với Chrome đã cài, không cài thêm dependency.
- Receipt ngoài public repo:
  `evidence/a09-admin-work-queue-20260911/browser/a09-work-queue-browser-qa.json`;
  SHA-256 `A68D9B88C5CD2226953DF88D7FF4BE176BE0EA9DCE6333555414C20F43AA8AF7`.

## Kiểm thử và comparator

- RED đầu: `1 passed / 1 failed`; RED mở rộng sau khi khóa mobile layout:
  `1 passed / 2 failed`, đúng do catalogue và CSS chưa có.
- Focused work-queue/read-model/backend: `21 passed` sau review fix (gồm partial
  truth và action-feedback branches).
- Final focused route/i18n/Tester/UI/safety: `81 passed`, `162 deselected`,
  `1` cảnh báo Pydantic cũ, `0 failed`.
- Tester metadata: `32 passed`, `1` POSIX file-mode test deselected trên Windows;
  WA-47 nâng nguồn case thành `47` case tuần tự.
- Protected exact-base/candidate comparator chạy cùng hai file: cả hai
  `25 passed / 2 failed`; cùng đúng hai baseline IDs
  `test_admin_css_override_is_scoped_dense_visible_and_responsive` và
  `test_admin_home_final_hierarchy_is_scoped_balanced_and_motion_stable`;
  `NEW_FAILURES=0`.
- Node syntax `4/4`, Python compile và `git diff --check`: exit `0`.

## Tester và giới hạn quyền

GitHub readback ngày 12/09/2026 xác minh issue #412 đang `OPEN`, đủ `12/12`
nhãn bắt buộc và hai issue template vẫn có trong repo. Token hiện chỉ có
`gist/read:org/repo/workflow`, không có scope project; Tester Project vì vậy
được ghi `not_revalidated`, không giả là đã kiểm lại.

Không sửa `copyfast_operations_desk.py`, API, schema, session, role, filter
enum, năm nguồn hay target route. Không tạo record production; không gọi Bot,
provider, PayOS, ví Xu hoặc bất kỳ action ghi nào. Local acceptance không phải
merge, deploy hay signed production LIVE.

PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
ENV_MUTATIONS=0
OPERATIONS_DESK_WRITES=0
LIVE_PASS=NOT_TESTED
