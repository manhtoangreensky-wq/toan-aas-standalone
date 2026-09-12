# A09 — Admin CRM Leads UX/locale

Spec: `A09-ADMIN-CRM-LEADS-UX-LOCALE`
Route: `/admin/crm/leads`
Branch: `fix/a09-admin-crm-leads-ux-locale`
Base: `66a052ca76abd58af9020125c65e17fc3ba6e0df`

## Kết quả nhìn thấy

Trang quản trị CRM nay tập trung vào việc cần theo dõi: hero ngắn → danh sách
ẩn danh + bộ lọc giai đoạn → kết quả → phần dữ liệu và giới hạn đóng ban đầu.
Loading và guarded có thông báo riêng, không hiển thị hàng cũ; nút làm mới bị khóa
và có `aria-busy` trong lúc loading. Mỗi lần làm mới, lọc hoặc chuyển trang đều
xóa projection cũ, chuyển sang `processing` trước khi bắt đầu network read, rồi
chỉ render receipt mới nếu route/session/epoch vẫn còn hợp lệ. Ở màn hình rộng
bảng rõ ràng; ở `≤900px`, từng hàng thành thẻ dọc có nhãn cột và không còn dòng
hướng dẫn cuộn ngang gây hiểu nhầm. `<thead>/<th scope="col">` vẫn ở trong
accessibility tree bằng kỹ thuật visually-hidden, không dùng `display:none`.
Scoped mobile CSS cũng vô hiệu hóa riêng sticky/max-width/shadow của cột đầu
từ bảng dùng chung, nên mọi ô dùng đủ chiều rộng hàng và không bẻ chữ theo
từng ký tự.

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
  mobile cell-width shortfall, relevant console, framework overlay và request
  ghi đều `0`.
- Tương tác thật: chọn giai đoạn `review` rồi `Áp dụng` trả đúng `1` dòng ẩn
  danh; disclosure mở/đóng được bằng bàn phím.
- Browser plugin không khả dụng; theo fallback đã cho phép, QA dùng Playwright
  với Chrome cài sẵn, không cài dependency mới.
- Receipt ngoài public repo:
  `evidence/a09-admin-crm-leads-20260912/browser/a09-crm-leads-browser-qa.json`;
  SHA-256 `82385CCCE07393C6E7FBA8E724E652A268F9285D76498816344B902978588986`.

## Kiểm thử và comparator

- RED ban đầu tái hiện `ReferenceError: PARTNER_CRM_STAGES is not defined` khi
  render row; fix dùng `PARTNER_CRM_STAGE_LABELS` allow-list.
- Review RED tái hiện `2 failed`: request gọi API trước loading nên hàng cũ còn
  hiện; mobile dùng `display:none` nên header cột biến mất khỏi accessibility
  tree. Sau sửa, hai test riêng đều `1 passed`.
- Renderer/CSS contract: `5 passed`.
- CRM portal/backend/consultation: `25 passed`; auth/stale/navigation bổ sung:
  `3 passed`, `1` cảnh báo Pydantic; tổng `28 passed`, `0 failed`.
- Tester workspace portable: `32 passed, 1 deselected`; bài kiểm mode `0600`
  POSIX-only được loại rõ ràng trên Windows, không đổi mã ngoài scope.
- Protected exact-base/candidate comparator: cả hai `25 passed / 2 failed`,
  cùng hai baseline CSS-tail IDs; `NEW_FAILURES=0`.
- Node syntax `3/3`, `git diff --check`: exit `0`.
- Independent review cuối: `0 Critical / 0 Important / 1 Minor`,
  `Ready to merge: Yes`. Minor duy nhất là timestamp provenance cũ; artifact
  migration sẽ được tái sinh từ source commit mới và commit riêng trước PR.
- PR #430 CI lần đầu run `34690972958` dừng tại `1 failed / 208 passed` vì
  contract Aura cấm toàn theme dùng `clip-path: inset(50%)`. Corrective bỏ đúng
  token không bắt buộc, giữ `clip: rect(...)` cho header accessible. Bounded
  suite sau đó lộ contract Auth chỉ được đọc phần từ marker Auth đến cuối file;
  nguyên khối CRM được chuyển lên trước marker với SHA-256 nội dung trước/sau
  cùng `5C2CB6AC…F7051B`, không đổi semantics.
- Fresh post-corrective: hai contract CI + CRM `3 passed`; toàn bounded workflow
  portable `286 passed, 1 deselected, 1 warning`; Browser lại đạt `20/20`
  trạng thái và `18/18` assertion. CI rerun trên Linux chờ push corrective.
- Independent corrective review: `0 Critical / 0 Important / 0 Minor`, Ready
  `Yes`; working tree giữ đúng năm file trong scope và reviewer không mutation.

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
