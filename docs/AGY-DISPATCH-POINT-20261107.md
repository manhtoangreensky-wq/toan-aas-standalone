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

## Đối chiếu CLI ngày 10/11/2026

Đợt kết quả kế hoạch video đã nhận được mã qua CLI hiện có với model
`gemini-3.8-flash-high`, không đăng nhập lại hoặc sửa settings; phát hành qua
PR #704, CI42668319118 và deploy42670123474. Đợt tiếp theo vẫn dùng cùng điểm
giao việc này; không tìm OAuth chỉ vì lệnh in hết thời gian chờ.

Phiếu phải có source thật và OLD/NEW đầy đủ, không chỉ một danh sách nhãn.
Lệnh giao chỉ cho phép thư mục gói mã công khai, không phải toàn repository.
Ghi rõ **đường dẫn tuyệt đối tới đúng phiếu** trong prompt: khi nối conversation,
thư mục cũ có thể khiến tên tương đối `packet.md` trỏ sang phiếu trước.
Đối chiếu SPEC_ID, schema hiện tại, OLD anchor và thay đổi thực tế trước áp dụng.
Nếu trả lại nguyên đề xuất cũ, đó chưa phải bằng chứng đã sửa phiếu mới.

Giữ kết quả đầy đủ của tiến trình (mã thoát, handle, response, structured output),
không chỉ in trường output rồi bỏ handle. Timeout chưa có patch không được tính
là lỗi nghiệm thu code. Xác minh phiên hiện có trước khi mở lượt mới; không gửi
vòng đăng nhập mới để chữa lỗi định dạng/đường dẫn phiếu.

Các tệp test, dữ liệu tổng hợp/API response và log chẩn đoán ở máy điều phối
không tự đi kèm gói gửi worker. Chỉ đưa source công khai đúng allowlist, đặc tả
và toàn bộ MAP đã kiểm tra. Worker trả mã; điều phối viên chạy cả luồng thật,
không công nhận source-render xanh là chứng minh thao tác lưu trên ứng dụng.

## Quy tắc nghiệm thu tiết kiệm usage Codex — Owner 10/11/2026

Owner yêu cầu: sau khi một task Antigravity xong, kiểm tra đúng phần đó một lần;
hoặc gom các task đã xong để kiểm tra chung một lần, tránh dùng Codex lặp việc.

- Chốt phạm vi và các cổng cần thiết trước khi giao. Gom các bản vá hoàn tất,
  không xung đột vào một lượt nghiệm thu có bằng chứng.
- Mỗi phiên bản mã ổn định chỉ chạy một lượt các kiểm tra đã chốt. Không đọc
  lại toàn bộ nguồn, gọi thêm reviewer hoặc chạy lại bộ lớn khi mã không đổi.
- Nếu phát hiện lỗi, ghi đúng finding và trả worker; sau bản sửa mới chỉ chạy
  lại các kiểm tra cần thiết cho finding và rủi ro hồi quy của thay đổi đó.
- Mất ngữ cảnh thì đối chiếu SHA/hash và receipt hiện có; bằng chứng đúng mã
  được dùng lại, không tự làm lại từ đầu.
- CI và đối chiếu sau deploy là cổng ở môi trường mới, không phải lý do lặp lại
  toàn bộ kiểm tra local. Dùng các cổng tối thiểu đã định, không suy LIVE từ CI.
- Tiến trình đang chạy được theo dõi bằng handle/log thật; không mở thêm model
  chỉ để hỏi lại trạng thái hoặc kiểm tra cùng một phần chưa đổi.

Đây là quy tắc điều phối trong dự án theo lệnh Owner, không tự sửa skill hay
thăng cấp thành luật toàn cục. Các chốt ENV/secret, dữ liệu, provider, ví và
production vẫn giữ nguyên.
