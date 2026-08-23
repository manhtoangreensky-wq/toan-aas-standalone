# Web-local Admin Home Access Design

**Ngày:** 24/08/2026  
**Trạng thái:** Owner đã chọn phương án A; chờ xác nhận bản spec viết ra trước khi lập implementation plan.  
**Phạm vi:** Chỉ cổng HTML `GET /admin` và test chống hồi quy quyền truy cập.

## 1. Vấn đề đã đo được

Production hiện có chuỗi sự kiện:

1. Admin Web đăng nhập thành công; `GET /api/v1/auth/me` trả `200`.
2. `GET /api/v1/admin/navigation` trả `200` và cấp nhóm `web_local_admin`.
3. `GET /admin` trả `403`.

Database production có đúng một tài khoản role Admin đang hoạt động, đăng nhập mật khẩu bật, nhưng chưa có `canonical_user_id`.

Mâu thuẫn nằm trong `app.py`:

- `/admin/login` chuyển mọi tài khoản có role cache `admin` sang `/admin`.
- `/admin` lại gọi `require_canonical_admin`, bắt buộc tài khoản phải liên kết Bot identity và được Bot xác nhận role Admin đang còn hiệu lực.

Kết quả là một Admin Web hợp lệ bị chuyển thẳng vào route mà chính tài khoản đó không được phép mở. Phản hồi `403` thay cho Portal shell tạo cảm giác màn Admin đen/trống.

## 2. Quyết định thiết kế

`GET /admin` là trang tổng quan/directory HTML, không phải API dữ liệu canonical và không phải write executor. Route này sẽ yêu cầu `require_admin(request)` thay vì `require_canonical_admin(request)`.

Sau khi Portal shell mở:

- `GET /api/v1/admin/navigation` tiếp tục là nguồn duy nhất quyết định nhóm nào được hiển thị.
- Admin Web chưa liên kết canonical chỉ nhận các nhóm `web_local_admin` đã có: Khách hàng Web, CRM nội bộ, kế hoạch vận hành, quản trị tài liệu, automation monitor, system/data stewardship, security/access posture.
- Các nhóm canonical chỉ xuất hiện khi `require_canonical_admin` xác minh thành công với Bot.
- Mọi API canonical, write action, role mutation, ví, Xu, PayOS, provider, job và dữ liệu khách vẫn giữ guard hiện tại.

Không redirect Admin Web sang `/admin/customers`, vì cách đó chỉ né triệu chứng và để `/admin` tiếp tục trả `403`.

Không ghi `canonical_user_id` thủ công, không đoán Telegram ID và không thay đổi database production.

## 3. Ranh giới file

Được phép sửa:

- `app.py` — tách exact route `/admin` khỏi nhóm canonical child routes.
- `tests/test_web_local_admin_home_access.py` — test runtime cho cổng HTML.
- Bằng chứng migration bắt buộc của CI nếu fingerprint thay đổi.

Cấm sửa:

- `copyfast_auth.py` và mọi hàm `require_canonical_admin*`.
- `copyfast_admin_erp_navigation.py` và danh sách quyền đã phát hành.
- API Admin canonical, database/schema, ENV/secret, session store.
- Ví, Xu, PayOS, provider, job, refund, role grant/revoke.
- CSS/JS giao diện và mọi trang khách.

## 4. Luồng sau sửa

### Admin Web chưa liên kết canonical

`/admin/login` → signed session role `admin` → `/admin` trả HTML `200` → `/api/v1/admin/navigation` trả `web_local_admin=true`, `canonical_admin=false` → Portal render các module Web-local và thông báo canonical vẫn được bảo vệ.

### Admin canonical

Luồng không đổi: `/admin` trả HTML `200`; navigation chỉ thêm nhóm canonical sau live Bot authority check.

### Người dùng thường

`/admin` tiếp tục trả `403`; không được phát hành Admin shell hoặc directory.

### Route canonical con

Các route như `/admin/users`, `/admin/wallet`, `/admin/payments`, `/admin/jobs` tiếp tục gọi `require_canonical_admin`; Admin Web chưa liên kết canonical vẫn nhận `403`.

## 5. Error handling

- Phiên hết hạn tiếp tục dùng cơ chế `current_session` hiện có và trả/redirect theo contract hiện tại.
- Role khác `admin` tiếp tục nhận thông báo “Chỉ quản trị viên được phép truy cập”.
- Bot không xác minh được canonical role không được nâng quyền; navigation chỉ giữ nhóm Web-local.
- Không thêm fallback quyền ở browser, localStorage, email allowlist hoặc query parameter.

## 6. Acceptance criteria

1. Local Web Admin có signed session, `role=admin`, `canonical_user_id=None`: `GET /admin` trả HTML `200` và không gọi canonical bridge.
2. Người dùng signed role `user`: `GET /admin` vẫn trả `403`.
3. Local Web Admin chưa canonical: `GET /admin/users` vẫn trả `403` qua canonical guard.
4. `require_canonical_admin`, `require_canonical_admin_csrf` và toàn bộ API/write guard không đổi.
5. Targeted tests, Python compile, Admin regression và CI quality gate đều đạt.
6. Sau deploy, production HEAD khớp merge SHA; Web/nginx active; `/health` hợp lệ.
7. Live Chrome với signed Admin session: `/admin` có sidebar/header/nội dung ERP, không phải nền đen hoặc JSON `403`; console không có lỗi app không giải thích được.

## 7. Không thuộc spec này

- Responsive màn đăng nhập/đăng ký.
- Bỏ dòng “Hoặc tiếp tục với email”.
- Ô vuông và logo trong “Luồng công việc mới”.
- Việt hóa `Workspace` và các literal tiếng Anh.
- PayOS QR/payment-link.

Các việc trên chỉ mở sau khi spec khôi phục Admin được `ACCEPTED` và live test đạt.
