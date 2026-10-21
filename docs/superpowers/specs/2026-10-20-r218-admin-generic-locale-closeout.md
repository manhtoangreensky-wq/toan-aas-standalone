# R218 — Admin Generic locale closeout (UI-only)

## Mục tiêu

Khóa phần chữ giao diện cố định còn lẫn tiếng Anh trong các bề mặt Admin Generic:
tra cứu kiểm soát, hàng chờ sự cố, bảo trì tính năng và trạng thái bảo mật/quyền
truy cập. Chỉ sửa bản dịch hiển thị tiếng Việt và fallback tiếng Việt; không đổi
route, enum, payload, authority, dữ liệu, thao tác ví hoặc quyền ghi.

## Phạm vi

- `static/portal/portal-i18n.js`: các khóa `adminGeneric.audit.*`,
  `adminGeneric.maintenance.*` và `adminGeneric.securityAccess.state.*` của VI.
- `static/portal/portal.js`: fallback nhãn thử lại trong thao tác job, để fallback
  vẫn thuần tiếng Việt khi catalogue không nạp được.
- `tests/admin-generic-fixed-chrome-locale.test.mjs`: khóa các cụm dễ rò như
  `redaction`, `signed canonical admin session`, `Audit Explorer` và `Security &
  Access Posture` trong vùng VI.

## Hợp đồng không đổi

- Tên riêng/kỹ thuật cần giữ nguyên: Bot, Core Bridge, PayOS, Xu, CSRF và mã
  `WEBAPP_ADMIN_WRITES_ENABLED`.
- Không dịch dữ liệu do máy chủ trả về, mã route, ID, trạng thái máy, payload hay
  tên người dùng.
- Không mở thêm capability, không gọi provider, không gửi form, không thay đổi
  ví/PayOS và không suy diễn RBAC thật từ fixture.
- EN/ZH giữ nguyên catalogue của từng ngôn ngữ; thay đổi này chỉ chạm fixed chrome
  VI và fallback VI.

## Tiêu chí nghiệm thu

1. Test locale Admin Generic không còn các cụm tiếng Anh đã khóa.
2. Test module tabs VI/EN/ZH tiếp tục xanh và giữ đúng route/alias/quyền.
3. `node --check` cho hai tệp JavaScript và `git diff --check` đều thành công.
4. Full Node test không có lỗi mới; browser/live/backend/CI vẫn ghi rõ là chưa
   được chứng minh trong batch này.

## Bằng chứng batch

- `node --test tests/admin-generic-fixed-chrome-locale.test.mjs tests/admin-generic-zh-copy.test.mjs tests/admin-module-tabs-locale-purity.test.mjs`
  → 11/11 đạt.
- `node --check static/portal/portal-i18n.js` → đạt.
- `node --check static/portal/portal.js` → đạt.
- `git diff --check` → đạt.
- Full `node --test` cần chạy lại sau khi đóng batch; không suy diễn CI/LIVE từ
  kết quả local.
