# R217-09A — Content, Workboard, Free Tools và Notes

**Status:** `TODO`
**Wave:** W4
**Surface:** Content Studio, Workboard, Campaign/Calendar/Approvals, Notes/Memory,
Projects/Documents, Free Tools/Prompt Gallery, Publishing.

## File có thể sửa khi mở

- surface renderer/helper tương ứng trong `static/portal/`;
- catalogue locale và focused tests đúng surface.

## Cấm sửa

Không đổi server action, revision, CSRF, idempotency, publishing/automation backend hoặc
đổi dữ liệu prompt/title do server trả.

## Contract giao diện

- Mỗi surface có route title/description, primary CTA, list/detail/create, save/edit,
  archive/restore/version/history và empty/loading/error/guarded.
- Workboard: board/list/card xếp dọc trên mobile; filters/status/priority/dependency/pagination
  có nhãn; không để bảng ngang tràn.
- Campaign/Calendar/Approvals: mốc, agenda, review, reminder, status guard và handoff rõ.
- Free Prompt Gallery: search/group/industry/goal/platform, copy/save/receipt; fixed UI
  tách khỏi prompt data.

## Acceptance

- Người mới nhìn thấy “việc cần làm tiếp theo” trên từng surface, không phải đoán route.
- VI/EN/ZH thuần, keyboard/focus/contrast/responsive pass; draft không bị gọi là output.

## Verify

```powershell
node --test tests/content-studio-locale-presentation.test.mjs tests/memory-center-locale-presentation.test.mjs tests/free-prompt-gallery-locale-presentation.test.mjs tests/campaign-planner-locale-presentation.test.mjs
```
