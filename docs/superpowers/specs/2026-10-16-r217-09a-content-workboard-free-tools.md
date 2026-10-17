# R217-09A — Content, Workboard, Free Tools và Notes

**Status:** `SOURCE_PRESENTATION_GREEN_RUNTIME_OPEN`
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
node --test tests/content-studio-locale-presentation.test.mjs tests/content-studio-detail-locale-presentation.test.mjs tests/workboard-locale-presentation.test.mjs tests/memory-center-locale-presentation.test.mjs tests/free-tools-hub-presentation.test.mjs tests/free-prompt-gallery-locale-presentation.test.mjs tests/project-studio-locale-presentation.test.mjs tests/publish-review-pack-locale-presentation.test.mjs tests/campaign-planner-locale-presentation.test.mjs
```

## Source evidence 2026-10-17

- Content Studio board/detail, Workboard board/list/detail, Memory, Free Tools, Free Prompt
  Gallery, Projects/Studio Documents, Publish Review và Campaign đều có renderer/helper và
  locale regression hiện hành; focused source set đạt `26/26`, full Node suite đạt `522/522`.
- Các route/action/field/revision và boundary bản nháp/không tạo output vẫn được kiểm tra bởi
  các test từng surface. Đây là source/presentation evidence; browser AX, responsive runtime
  và dữ liệu ghi thật vẫn mở theo W7/W8/W9. Không có code cần sửa thêm trong R217-09A khi
  source contract đã xanh; chuyển wave kế tiếp sang R217-09 Admin/customer visibility.
