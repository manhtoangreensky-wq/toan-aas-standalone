# Secure Access & First-Run Journey

## Mục tiêu

Module này làm gọn đường đi signed Web account:

```text
/login → /register → /onboarding → /dashboard → /account → /account/security
```

Đây là thay đổi UI/state projection cho Web App, không phải một cơ chế đăng
nhập mới. Email + mật khẩu là lối vào chính; Telegram và OAuth được mở theo
progressive disclosure để màn đầu tiên không biến thành landing page hay một
danh sách provider dài.

## Authority và ranh giới

| Thành phần | Authority | Quy tắc UI |
| --- | --- | --- |
| Email/password, signed session, CSRF, rate limit, MFA | Web server hiện có | Giữ nguyên action/API và feedback server-side. |
| Telegram Login | OIDC/Web server hiện có | Không có ô nhập raw Telegram ID. Challenge vẫn one-time, hết hạn và chống replay. |
| Telegram/Bot link | Bot + signed callback hiện có | Tùy chọn, chỉ mở dữ liệu canonical sau xác minh cùng identity. |
| Google/GitHub/Apple | OAuth provider đã cấu hình ở server | Chỉ enable khi server công bố provider có cấu hình thật. |
| Profile/Account/Security | Signed Web account | Deep MFA/OAuth/session controls vẫn ở `/account/security`; UI không tự cấp quyền. |

### Bootstrap public Auth hiện hành

- `/login` và `/register` là public entry. Server đã redirect một cookie signed
  hợp lệ về `/dashboard`, nên browser public không gọi protected
  `GET /api/v1/auth/me`. Signed workspace vẫn dùng endpoint này làm authority
  cho account/session/CSRF như trước.
- Google và Apple chỉ render khi `GET /api/v1/auth/providers` trả đúng literal
  `enabled: true` cho provider tương ứng. Missing, malformed, `false`, chuỗi
  `"true"` hoặc số `1` đều bị ẩn fail-closed. Telegram giữ readiness và flow
  one-time riêng, không được suy ra từ trạng thái Google/Apple.
- Theme controller gắn marker `auth` đồng bộ trong `<head>`; CSS first-paint
  nhỏ pre-apply đúng minimal-shell geometry trước bundle chính. Auth bỏ generic
  whole-main enter trên hydration, nên nội dung rõ ngay thay vì opacity/translate
  lặp; không thay đổi form action, auth authority hoặc reduced-motion contract.

Không có thay đổi `bot.py`, Core Bridge, PayOS, wallet ledger, webhook,
provider call, database migration, secret hay Railway configuration.

## First-run và continuation

- Onboarding có ba bước rõ: chọn cách bắt đầu, xác nhận Telegram nếu chọn,
  rồi vào Workspace.
- Web độc lập là hành trình hợp lệ. Khi người dùng bỏ qua Telegram, route tiếp
  tục được giữ bằng `workspaceRoute`, không ép quay về `/dashboard` và không
  làm mất workflow đã chọn.
- Account có một Account health strip ngắn: signed session, hồ sơ Web,
  canonical link và một next action. Các chi tiết session/MFA/OAuth không bị
  nhồi vào entry strip.

## PWA và UX

- `/onboarding` và `/account` (bao gồm child routes) nằm trong
  `PRIVATE_PATH_PREFIXES`; không là shell/public offline fallback.
- Dùng dark slate/teal token của ứng dụng, không thêm gradient/hero marketing.
- Desktop control tối thiểu 40px, mobile 44px; detail summary có focus visible
  và tất cả motion mới tôn trọng `prefers-reduced-motion`.
- Các form giữ visible label, async feedback và action contract cũ. Không có
  localStorage/token/password/Telegram ID mới.
- First-paint CSS là public shell asset có build version, fallback-template và
  service-worker allowlist riêng; API/private route vẫn tuyệt đối không cache.

## Kiểm tra trọng điểm

- static contract: email primary, provider progressive disclosure, action và
  signed-state boundary không đổi;
- onboarding continuation: skip và completed link dùng cùng continuation;
- PWA: onboarding/account private, không nằm trong shell;
- responsive/accessibility: focus, 44px mobile, reduced motion và không có
  `linear-gradient` trong scope mới.
- public runtime: `/login|/register` không request `/auth/me`; signed route vẫn
  hydrate; mobile CLS tối đa `0.001`; main không có generic enter animation.
