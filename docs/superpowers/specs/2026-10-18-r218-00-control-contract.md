# R218-00/01 — Hợp đồng từng control và checkpoint

## Checkpoint WIP

- #653 auth responsive/contrast: đọc trạng thái PR/HEAD/CI hiện tại trước delivery.
- #654 branch webapp-r217-subdub-ui-r218: ứng viên source/docs SubDub, review còn mở.
- Base hiện đã fetch: 559d982e8391fb7c3eb1dc6f5a41ef6bb3401209.
- 526 Node tests/12 SubDub tests từng chạy trước rebase; không thay browser/live.
- PR #654 cần review hidden field/duplicate selector, default checked khi chưa chọn,
  lý do guarded cho giọng mặc định, link Voice Vault, volume 0–200 và locale.
- Chỉ chốt phần đang dở khi evidence trên candidate hiện tại và ledger khớp.

## Mỗi nút/field có một dòng

| Cột | Bắt buộc |
|---|---|
| ID | Duy nhất, ví dụ SD-VOICE-FEMALE |
| Bot source | File:line/symbol/callback/handler; đánh dấu CODE/DESIGN |
| Web source | Renderer/route/helper thật hoặc NEW_UI/T0 |
| Labels | VI/EN/ZH tự nhiên; không jargon nội bộ |
| Position | Section/nhóm/thứ tự, CTA chính/phụ |
| Visibility | Mode/role/capability/step/data condition |
| Input | Kiểu/options/default/required/limits từ authority |
| Action | Local config/read/save/quote/submit/download; side effect phân biệt |
| Next/Back | Điểm đến; giữ nguồn/options/scroll/focus |
| States | Selected/loading/disabled/empty/error/stale/completed |
| Feedback | Thông báo field, progress, retry hợp lệ và lý do guard |
| Evidence | Test hành vi + screenshot/AX theo mode/role/theme/locale/viewport |

Không thay UI key mới thành DTO máy chủ khi chưa có mapping được xác minh.
Local editing khác quyền thực thi; không khóa cấu hình chỉ vì provider chưa mở.

## Shared layout

Mobile một cột, desktop source/preview và config chia vùng nhưng DOM order tuần tự.
H1 32–40px, mobile 28–32; H2 24px; body 16px/1.5; label 14–16px.
Spacing 8/12/16/24/32; card padding 24/16px; target 44px; AA ≥4.5:1 chữ thường.
Màu xanh/navy/teal hiện tại, icon hệ thống hiện có; không thay brand.

## State evidence

Chọn/Back/hydration/reload giữ dữ liệu đúng phiên. Logout/account change xóa dữ liệu cũ.
Một job còn chạy chỉ có status/refresh; duplicate confirm không tạo tác vụ mới.
Preview khác full output; completed khác download_ready; failed_delivery khác failed_generation.
Không bịa ID, giá, file, progress hoặc trạng thái quyền.

## Verify

`node --check static/portal/portal.js` → exit 0.
`node --test tests/subdub-hub-presentation.test.mjs` → fail 0; chỉ scope SubDub.
`git diff --check <base>...HEAD` → exit 0, dùng SHA đã đo.
Browser mỗi control/state tại 375/390/768/1440 × VI/EN/ZH × light/dark.
Shell/form thêm 320/414/1024. Screenshot/AX/contrast/type/touch/overflow phải đo.
Không dùng hidden fields/regex hoặc xóa assertion locale để đạt test.
