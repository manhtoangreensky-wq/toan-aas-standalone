# Hướng dẫn Tester TOAN AAS Web App

1. Chọn đúng case `WA-01..WA-16`; không đổi route, role hoặc viewport giữa case.
2. Ghi BASE/HEAD SHA và URL evidence trước khi test.
3. Chạy case local trước; Builder self-report không thay Tester result.
4. Auth/PayOS dùng readiness/stub ở local; cấm tự thêm ENV, gọi provider thật hoặc mutate ví/dữ liệu.
5. Sau deploy, đối chiếu PR merge, workflow, runtime SHA và live output như bốn bằng chứng riêng.
6. PayOS live chỉ bấm `Nạp ngay` một lần để thấy checkout/QR; cấm quét QR, thanh toán hoặc cộng Xu.
7. Google/Apple thiếu cấu hình thì trạng thái đúng là BLOCKED + UI_SAFE, không phải PASS E2E và không phải lỗi UI.
8. FAIL case nào thì mở lại đúng SPEC_ID trong issue `#412`; không sửa spec đã khóa.
9. WA-13..WA-16 dùng evidence Admin: `admin-vi-en-shell-001/r2`, `admin-detail-dashboard-002/r2`, `admin-data-views-003/r1`.
10. Với locale, chỉ miễn trừ dữ liệu server như ID/tên người dùng/enum nguồn; hero, guard, header, aside, note, filter và inspector header phải thuần VI hoặc EN.
11. Với bảng Admin, kiểm click/Enter/Space chọn row; click action trong Job không được chọn row hoặc phát request ngoài ý muốn.
12. Với chuỗi XSS fixture, PASS chỉ khi literal vẫn là text, unsafe node bằng `0` và counter thực thi bằng `0`.

Mỗi báo lỗi ghi: route, role, viewport, bước tái hiện, expected/actual, screenshot/JSON, console/network liên quan và SHA runtime.
