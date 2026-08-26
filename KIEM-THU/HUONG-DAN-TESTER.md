# Hướng dẫn Tester TOAN AAS Web App

1. Chọn đúng case `WA-01..WA-12`; không đổi route, role hoặc viewport giữa case.
2. Ghi BASE/HEAD SHA và URL evidence trước khi test.
3. Chạy case local trước; Builder self-report không thay Tester result.
4. Auth/PayOS dùng readiness/stub ở local; cấm tự thêm ENV, gọi provider thật hoặc mutate ví/dữ liệu.
5. Sau deploy, đối chiếu PR merge, workflow, runtime SHA và live output như bốn bằng chứng riêng.
6. PayOS live chỉ bấm `Nạp ngay` một lần để thấy checkout/QR; cấm quét QR, thanh toán hoặc cộng Xu.
7. Google/Apple thiếu cấu hình thì trạng thái đúng là BLOCKED + UI_SAFE, không phải PASS E2E và không phải lỗi UI.
8. FAIL case nào thì mở lại đúng SPEC_ID trong issue `#412`; không sửa spec đã khóa.

Mỗi báo lỗi ghi: route, role, viewport, bước tái hiện, expected/actual, screenshot/JSON, console/network liên quan và SHA runtime.
