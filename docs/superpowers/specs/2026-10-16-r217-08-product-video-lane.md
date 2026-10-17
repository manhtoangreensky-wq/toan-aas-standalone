# R217-08 — Product Video UI/UX parity

**Status:** `SOURCE_PRESENTATION_GREEN_RUNTIME_OPEN`
**Wave:** W4
**Surface:** `/tools/video`, `/video/create`, `/video/multiscene`, `/video-studio`,
`/video/text-to-video`, `/video/long`, `/video/product`, `/video/frame-sequence`,
`/video/mux`, `/video/preview`, `/video/poster`, `/video/finishing`.

## File có thể sửa khi mở

- video hub/form/studio renderer trong `static/portal/`;
- video presentation/catalogue tests.

## Cấm sửa

Không tự nối provider/worker, không fake MP4, không đổi quote/charge/idempotency/route.

## Contract giao diện

- Hub hiển thị bốn lane dọc theo mục tiêu: lập kế hoạch, tạo video, biên tập/ghép và
  kiểm tra/bàn giao; mỗi lane có đầu vào, đầu ra và trạng thái rõ ràng.
- Có ba lối bắt đầu nhanh, nhưng danh mục chính chỉ đếm `10` route video duy nhất để tránh
  người dùng phải đoán hoặc thấy công cụ trùng lặp.
- Form chính chỉ hỏi input cần thiết; advanced settings trong disclosure.
- Flow giữ bảy bước `input → plan → quote → confirm → progress → result → recovery`;
  status và report tách khỏi khả năng download.
- AI edit và manual edit có boundary rõ; các phần timeline/scene/version/history và handoff
  sang Audio/Image/SubDub vẫn do các màn hình chuyên trách giữ nguyên.

## Acceptance

- Nhóm tác vụ dọc, CTA không lẫn jargon kỹ thuật, mobile không tràn ngang.
- Mỗi lane giữ trạng thái `ready` hoặc `guarded` đúng với khả năng source hiện tại; không
  tự hiển thị completed/download khi chưa có output thật.
- Locale, keyboard/focus, report và evidence không đổi core contract.

## Verify

```powershell
node --test tests/video-uiux-locale-presentation.test.mjs
node --test tests/*.test.mjs
```

Nếu test tên cũ không tồn tại, dùng đúng focused test được ghi trong R214 và lưu lệnh đã
chạy; không bỏ qua vì khác tên.

## Source closeout 2026-10-17

Video Hub now presents a seven-step journey, four lanes, lane input/output contracts and an
explicit AI/manual editing boundary. The existing `10` video routes remain unchanged; no
provider output, MP4, job, quote, charge or wallet mutation was added. The focused source
regression reports `11` test cases with `11` passed and `0` failed, the full Node suite reports
`522` passed and `0` failed, `node --check` passes for
Portal and i18n, and `git diff --check` passes. Evidence commit:
`8e8ca08cd31617b21fc78b2956302873fe84d337`.
Runtime upload, render, delivery, download and real artifact evidence remain open and must
not be reported as parity with Bot until a guarded QA/runtime bridge is available.

## Browser-gate correction 2026-10-17

The browser gate requires the operational finishing route `/video/finishing` to be the single
primary quick action. The source previously inferred primary status from array position, so the
new planning-first order accidentally exposed `/video-studio` as primary and caused the gate to
report one broken hub. The primary marker is now explicit on the editing quick action; planning
and creation remain visible secondary entry points. This is presentation-only: routes, guarded
states, seven-step flow and backend boundaries are unchanged.

## CI verification 2026-10-17

Candidate `59afdf7a8367a0126c6078f40c75dbce019966ae` passed GitHub Actions run `39018249838`.
The browser verification gate checked all `6/6` product hubs, captured `18` screenshots, then
the browser runtime assertions and evidence upload completed successfully. This proves the
source/browser gate contract only; authenticated QA, performance tracing and real upload/render/
delivery artifacts remain open.
