# TOAN AAS Web App — chức năng gốc và hiện tại

## Tài liệu giai đoạn xây dựng đã tìm

- `docs/superpowers/specs/2026-07-28-ui-motion-foundation-design.md`
- `docs/superpowers/plans/2026-07-28-teal-sky-ui-motion-foundation.md`
- `docs/UX_APP_FIRST_REDESIGN.md`
- Các spec Admin/Auth/Billing trong `docs/superpowers/specs/`.

Không có một file duy nhất liệt kê toàn bộ chức năng của Web App lúc mới xây: `INITIAL_FEATURE_DOC=NOT_FOUND`. Phạm vi đã tìm: `README.md`, `docs/`, `docs/superpowers/specs/`, `docs/superpowers/plans/`.

## Đối chiếu

| Chức năng tài liệu gốc | Hiện tại trong batch | Trạng thái |
|---|---|---|
| Shared motion `140/220/420ms`, reduced-motion | Giữ token cho tương tác; Auth semantic đứng yên; chặn replay hydrate, observer pending và layout jank | ✅ Còn dùng |
| Customer và ERP là hai shell khác nhau | Admin/khách giữ route/role server-authoritative, dùng chung token UI | ✅ Còn dùng |
| Catalog nằm trong renderer lớn | Tách `portal-features.js`, render `135/135` mục | ⚠️ Đã tối ưu |
| Auth render provider actions | Chỉ render Google/Apple khi server trả `enabled=true`; Telegram giữ nguyên | ⚠️ Fail-closed rõ hơn |
| Billing/PayOS qua canonical bridge | Có direct checkout local fallback vẫn khóa owner/idempotency/URL | ⚠️ Mở rộng, live pending |
| Floating PWA/Copilot | Chuyển về normal-flow dock, hit target `44×44px`, không che nội dung | ⚠️ Sửa lỗi bố cục |

## Chỗ tài liệu gốc không còn đúng

- Plan 28/07 coi mount lifecycle đủ để tránh replay; runtime hiện cần route identity + hydrate marker cụ thể, được khóa bằng `test_motion_webapp_lifecycle_001_contracts.py`.
- Catalog không còn thuộc full integration bundle; authority hiện nằm trong `portal-features.js` và canonical hydrate.
- Google/Apple không phải action luôn hiện; readiness production hiện thiếu lần lượt `6/6` và `8/8` cấu hình, nên UI ẩn an toàn.
- PWA/Copilot không còn floating fixed trên content; current contract là normal-flow dock trên mọi viewport.
- Auth reference fade-up `opacity: 0` không còn dùng cho intro/form: live desktop cho thấy nội dung bị che và lệch `20px` lúc đầu; current contract là semantic content hiện ngay, vị trí ổn định.

## Không đổi trong batch

- Không migration/schema, không role grant mới, không secret/ENV, không Telegram mutation.
- Không provider call thật hoặc wallet/data mutation trong test.
- Nội dung/CTA chính và server-issued access vẫn là authority.

## Rác không đưa vào PR

- `patch.py`, `patch.diff` và nội dung trong `delete/` là artifact local ngoài source allowlist; không stage.
- Các baseline failure đã ghi trong state/checklist không được sửa ké chỉ để làm xanh số liệu.
