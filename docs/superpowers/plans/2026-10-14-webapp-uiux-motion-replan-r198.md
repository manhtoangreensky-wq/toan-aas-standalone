# Kế hoạch Web App UI/UX, locale và motion — cập nhật R198/R210

## Nguyên tắc điều hành

Phạm vi là Web App standalone. Không sửa Bot/Core, Telegram, provider, ví/Xu,
PayOS, dữ liệu production, VPS, deploy hoặc backend ngoài hợp đồng presentation.
Giữ màu xanh dương/xanh ngọc và nền tối xanh lam; bố cục dọc, responsive, không
tràn ngang. Mỗi surface phải có VI/EN/ZH thuần theo locale, chỉ giữ danh từ
riêng và tên sản phẩm đã được phép. Không đổi route, field, action,
capability, CSRF, idempotency, revision hay dữ liệu động.

FSM bắt buộc cho từng checkpoint:

`READ -> CONTRACT -> BUILD -> REVIEW -> VERIFY -> REPORT -> LEARN`

Không gọi provider trả phí, không mutation ví và không tuyên bố live pass khi
chưa có bằng chứng runtime thật.

## Thứ tự checkpoint

1. **R207 — Content Studio board/new:** hoàn tất source locale và contract.
2. **R208 — Content Studio detail:** hoàn tất archive/restore, composer,
   history, activity và action labels.
3. **R209 — Publish Review:** hoàn tất chrome và boundary copy.
4. **R210 — Workboard:** đã đạt source gate; browser acceptance còn mở.
5. **R211 — Notes/Memory Center:** tiếp theo, rà soát board, detail, create,
   search/filter, version/history, empty/loading/guarded và locale.
6. **R212 — Campaign/Calendar/Approvals:** rà soát các tab, form, trạng thái,
   lịch, phê duyệt và nhãn hành động; giữ nguyên write contract.
7. **R213 — Non-video surfaces còn fixed copy:** quét theo route inventory,
   sửa từng surface nhỏ, không gom refactor lớn. R213-01 Free Prompt Gallery đã
   xanh source. Checkpoint tiếp theo là **R213-02 Audio Workspace shell**:
   localize shell/home, Audio Hub overview, bộ lọc và option cố định; giữ nguyên
   collection/detail data, route/action và engine boundary.
8. **R214 — Video UI/UX:** chỉ xử lý sau khi các surface non-video đóng; kiểm
   tra product lanes, trạng thái, report và responsive.
9. **R215 — Full UI/UX acceptance:** ma trận VI/EN/ZH, light/dark, 375/390/768/
   1440, keyboard/focus, overflow, contrast, console/network và state guards.
10. **R216 — Motion:** chỉ bắt đầu khi R215 đóng. Sửa lifecycle/render trước,
    sau đó compositor/scroll, popup gesture, PWA readiness, reduced-motion và
    đo CLS/LCP/INP.

## Mỗi checkpoint phải có

- một spec hẹp nêu allowed files và protected contracts;
- test source/locale riêng và comparator cho route/action/field/revision;
- bằng chứng lệnh mới chạy, số pass/fail và baseline nếu so sánh được;
- checklist cập nhật ngay sau verify;
- báo cáo `PROVIDER_CALLS`, `WALLET_MUTATIONS`, `DEPLOY`, `LIVE_PASS` trung
  thực;
- nếu browser runtime chưa có, để `QA_RUNTIME_UNAVAILABLE`, không suy diễn.

## Motion backlog sau UI/UX

- `portal-auth.js` đang có nguy cơ render lần hai sau Promise auth, cắt animation
  entry và gây layout shift; cần một lifecycle gate có test.
- Bỏ transition theo `left`, chuyển sang thuộc tính compositor phù hợp.
- Scroll reveal phải bám tiến độ cuộn, không dùng transition trễ một nhịp.
- Mở Telegram phải giữ user gesture trước `await`, có fallback deep-link an toàn.
- Chỉ hiện nút cài PWA sau `beforeinstallprompt` hoặc trạng thái hướng dẫn thật.
- Kiểm tra `prefers-reduced-motion`, CLS/LCP/INP và trace desktop/mobile.

## Trạng thái hiện tại

R213-01: `SOURCE_GREEN;BROWSER_ACCEPTANCE_OPEN`.

R213-01 source evidence (2026-10-15): the Free Prompt Gallery filter chrome now
uses the VI/EN/ZH catalogue for search labels, placeholder/help, group,
industry, goal and platform labels/options. Fixed copy remains separate from
server-owned prompt data. Focused test is 5/5; the complete Node suite is
430/430; both Portal bundles pass `node --check`; `git diff --check` passes.
The browser acceptance gate remains open because the isolated QA runtime is not
available, so this checkpoint is not a live pass.

R213-02 is now in `CONTRACT`: the next bounded surface is the Media Workspace /
Audio Production Hub shell and filters. Detail/editor text remains protected
until a separate focused spec is opened; no provider, engine, wallet or
production mutation is part of this checkpoint.

Kiểm thử nền trước R213-01: focused locale/presentation 339/339, syntax pass,
`git diff --check` pass. Worktree chưa commit/push/merge/deploy; browser runtime
QA cô lập chưa khả dụng. R213-01 phải xanh trước khi chuyển surface non-video
tiếp theo; không quay lại motion trước khi R215 đóng trừ khi có lỗi chặn nghiêm
trọng được chứng minh.
