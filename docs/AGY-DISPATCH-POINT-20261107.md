# Điểm tiếp tục giao việc Antigravity

## Địa chỉ làm việc

Dùng CLI Antigravity đã có trên máy điều phối. Bản đã xác minh cho đợt này:
agy1.5.3, model `gemini-3.8-flash-high`. Không tự đăng nhập lại, sửa credential
hoặc đổi settings chỉ vì thấy một cảnh báo giao diện.

```powershell
$agy = (Get-Command agy -ErrorAction SilentlyContinue).Source
if (-not $agy) { $agy = Join-Path $env:USERPROFILE '.gemini\bin\agy.exe' }
& $agy --help
& $agy models
```

Luôn truyền model đã được Owner yêu cầu trong từng lệnh giao việc; không dựa vào
model mặc định có thể đổi ngầm. Không tự hạ phiên bản để lấy kết quả.

## Bộ nhớ điều phối local

Mã conversation và trạng thái tiến trình nằm trong sổ local của máy điều phối:

- `_giao-viec/ANTIGRAVITY-DISPATCH-POINT.md`: điểm tiếp tục và hàng đợi.
- `.agents/state/LOCALE-CAMPAIGN-20261108.yaml`: stage, handle, bằng chứng và việc kế tiếp.
- `_giao-viec/AGY-DISPATCH-PRIVATE-20261108.md`: lịch sử phục hồi giữ local.

Đây là vị trí dữ liệu local, không phải liên kết công khai hoặc dữ liệu đi kèm
checkout GitHub. Không công bố conversation ID, đường dẫn credential, log CLI,
bootstrap, API response, ENV hay dữ liệu khách.

## Quy trình tiếp tục

1. Đối chiếu repo/branch/BASE_SHA và source thật; đọc MAP.md.
2. Xác minh handle hiện còn chạy trước khi chờ hoặc khởi động lại. Conversation
   ID hay ảnh Generating cũ không phải bằng chứng tiến trình hiện tại.
3. Viết phiếu đủ OLD/NEW, phạm vi, bảo vệ và lệnh kiểm; đính kèm nguyên MAP.
4. Worker chỉ trả patch văn bản. Điều phối viên kiểm exact anchors, syntax,
   diff và chạy lại tests/browser; áp các phần dùng chung file theo thứ tự.
5. SPEC_MISSING hoặc transport timeout không phải code failure. Cùng lỗi code
   sai hai vòng mới chuyển sửa trực tiếp đúng lỗi đó; không mở rộng phạm vi.
6. Không giao Git/VPS, quyền, ENV, dữ liệu thật, provider hay tiền cho worker.

## Bằng chứng đợt locale hiện tại

F/G/H/I đã trả được patch qua CLI hiện có; không cần OAuth hay đổi tài khoản.
Kết quả hiện tại và trạng thái phát hành nằm ở
[receipt locale](reports/locale-release-20261108.md) và
[phiên Tester](../KIEM-THU/PHIEN-LOCALE-20261108.md).

Chữ giao diện sạch không phải tuyên bố đã chạy provider, đã deploy hoặc LIVE.
