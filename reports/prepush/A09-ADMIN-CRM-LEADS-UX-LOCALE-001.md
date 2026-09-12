# A09 — Admin CRM Leads UX/locale

Spec: `A09-ADMIN-CRM-LEADS-UX-LOCALE`
Route: `/admin/crm/leads`
Branch: `fix/a09-admin-crm-leads-ux-locale`
Base: `66a052ca76abd58af9020125c65e17fc3ba6e0df`

## Kết quả nhìn thấy

Trang quản trị CRM nay tập trung vào việc cần theo dõi: hero ngắn → danh sách
ẩn danh + bộ lọc giai đoạn → kết quả → phần dữ liệu và giới hạn đóng ban đầu.
Loading và guarded có thông báo riêng, không hiển thị hàng cũ; nút làm mới bị khóa
và có `aria-busy` trong lúc loading. Ở màn hình rộng
bảng rõ ràng; ở `≤900px`, từng hàng thành thẻ dọc có nhãn cột và không còn dòng
hướng dẫn cuộn ngang gây hiểu nhầm.

Fixed copy dùng catalogue `adminCrmManager.*` đối xứng VI/EN/ZH, bao phủ tiêu
đề, bộ lọc, giai đoạn, nhóm, trạng thái đồng ý, phân trang, empty, recovery và
toast đọc. Giá trị server canonical không đổi; chỉ nhãn và ngày giờ hiển thị
được localize. Directory không có link chi tiết, action ghi, mã, chủ sở hữu,
tên, email, nhu cầu, tag hoặc note.

## Bằng chứng đo được

- Browser local: `20` trạng thái = VI/EN × sáng/tối ×
  `1440/1024/768/390/360`.
- Assertion đạt: page identity, locale, anonymous projection, theme, task-first,
  disclosure đóng, mobile vertical rows, page/table overflow, clipping, touch
  target, framework overlay, console và write request.
- Minimum sampled contrast: `5.28:1`; page/table overflow, clipping, private leak,
  relevant console, framework overlay và request ghi đều `0`.
- Tương tác thật: chọn giai đoạn `review` rồi `Áp dụng` trả đúng `1` dòng ẩn
  danh; disclosure mở/đóng được bằng bàn phím.
- Browser plugin không khả dụng; theo fallback đã cho phép, QA dùng Playwright
  với Chrome cài sẵn, không cài dependency mới.
- Receipt ngoài public repo:
  `evidence/a09-admin-crm-leads-20260912/browser/a09-crm-leads-browser-qa.json`;
  SHA-256 `E7DCD19E0846948A22326BB8C0F5F9B5B0BCA88E3F23AA293A2E51935285B73B`.

## Kiểm thử và comparator

- RED ban đầu tái hiện `ReferenceError: PARTNER_CRM_STAGES is not defined` khi
  render row; fix dùng `PARTNER_CRM_STAGE_LABELS` allow-list.
- Renderer/CSS contract: `4 passed`.
- CRM portal/backend/stale/auth/i18n focused: `42 passed`, `1` cảnh báo Pydantic,
  `0 failed`.
- Protected exact-base/candidate comparator: cả hai `25 passed / 2 failed`,
  cùng hai baseline CSS-tail IDs; `NEW_FAILURES=0`.
- Node syntax `3/3`, `git diff --check`: exit `0`.

## Authority và giới hạn

Không sửa `copyfast_partner_crm.py`, API, schema, session, role, manager DTO,
stage filter, pagination hay customer CRM routes. Không có Core Bridge/Bot,
provider, payment, ví Xu, ENV hoặc production-data mutation. Đây là local
rendered acceptance, chưa merge/deploy/live.

PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
ENV_MUTATIONS=0
CRM_MANAGER_WRITES=0
LIVE_PASS=NOT_TESTED
