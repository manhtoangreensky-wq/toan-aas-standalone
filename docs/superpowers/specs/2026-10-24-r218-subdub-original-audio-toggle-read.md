# SD-D4 — đối chiếu bật/tắt âm thanh gốc trước khi sửa UI

Trạng thái: READ_COMPLETE, đang chờ chốt thiết kế; chưa sửa mã ứng dụng.
BASE_SHA: `ba4b2dfa1be096e35198e8bf60f3fa5596ed5af8`.
Branch `webapp-r218-billing-ui-20261022`, PR661, tracker664.
Dependency E3 đã đóng scoped delivery ở receipt6384081882, CI40092099397:
396 contract +26 runtime +456 authenticated records đều đạt. Không merge/deploy.

## Vấn đề thực sự

Spec gốc SD-15 yêu cầu bật/tắt và range/number0–100. Web hiện chỉ có range,
number và trạng thái mute khi0; chưa có công tắc riêng. Đây là thiếu UI,
không chuyển thành T0 engine và không gọi0% là đã hoàn tất mọi control.
Hai panel `DUBBING_ONLY` và `SUBTITLE_PLUS_DUBBING` dùng cùng renderer âm lượng.

## Bot tham chiếu đã đọc, không phải runtime production

Git snapshot `0d2f37669732eb2e23a78e75b728172ff41aebbd`, chỉ `git show`,
không import/chạy/sửa Bot. Không đọc ENV và không mở lại lane Multi đã khóa.
Line references thuộc đúng snapshot này; không tái dùng số dòng của snapshot khác.

| Bằng chứng source Bot | Hành vi xác minh được |
|---|---|
| `bot.py:238784` | `keep_original_audio` là trạng thái bật/tắt riêng |
| `bot.py:238796` | Âm gốc bị đưa về0 khi tắt; âm lồng tiếng có mức riêng0–200 |
| `bot.py:238926` | Có nút On/Off và nhập âm lượng riêng cho lớp âm gốc |
| `bot.py:258668` | Nhập âm gốc0–100 hợp lệ; lớn hơn0 bật,0 tắt |
| `bot.py:259410` | Toggle off→0; on→mức mặc định đã cấu hình, không khôi phục mức vừa dùng |
| `bot.py:2338` | Fallback source của mức mặc định là30; ENV runtime có thể thay, CHƯA ĐO |

Không lấy fallback30 làm giá trị máy chủ thật. Web hiện mặc định100 và chưa có
DTO mức mặc định Bot; không tự đọc ENV hoặc thay mặc định Web trong đợt này.

## Boundary Web đã đọc

`static/portal/portal.js`:

- `localVolumeControlsHtml` trong `renderSubDubHub` dựng hai cặp range/number;
  original0–100, dubbing0–200, mặc định hiện tại100, review giữ phần trăm.
- `updateSubDubLocalVolume` đồng bộ cặp input, output, lỗi và mute; chỉ riêng
  dubbing lớn hơn0 mới xóa xác nhận mute của giọng lồng tiếng.
- `captureSubDubDraft`/`subDubDraftSnapshot` chỉ giữ trường allowlist của bản nháp
  trong tab; signed-session fence xóa khi thay token/đăng xuất. Giữ nguyên fence.
- `applySubDubDraftDom` gọi volume updater khi khôi phục theo mode; control mới
  cần phản ánh đúng0/nonzero trong bước này, không chỉ đúng sau click.
- Hai delegated input/change listener chạy capture rồi cập nhật review; không POST.
- E3 native readiness tự thêm disabled cho mọi formcontrol trước signed-ready;
  không tự tạo quyền hoặc bỏ ba guard tệp/source-language/CTA đã khóa.

Soi symbol bằng `git grep -n` đã đọc: volume updater được gọi trong cùng file,
các chỗ xuất hiện ngoài file là test harness. Không đổi tên/chữ ký/export,
không sửa test cũ, không refactor module chung. Khi chốt contract sẽ đính kèm
nguyên bảng consumers và các exception nhỏ cần thiết; ngoài đó vẫn protected.

## Thiết kế đề xuất đã trình Owner — chưa triển khai

Đây là bounded UI change trong flow hiện có, không phải subsystem mới.
Một checkbox native mang vai trò công tắc, nhãn đủ VI/EN/ZH, đặt trong nhóm âm
gốc đang có; không thêm card, alert, ô trống, badge hoặc text thử nghiệm.
Giữ range/number có thể chỉnh cả khi mức0, như flow nhập số của Bot.

Hai phương án đang chờ Owner chọn:

1. Đề xuất: tắt→0; nhập/kéo lớn hơn0→bật; bật lại khôi phục mức dương vừa dùng
   trong bản nháp cùng tab/phiên, nếu chưa có dùng mặc định Web hiện tại100.
   Khôi phục mức vừa dùng là tối ưu Web có chủ đích, không tuyên bố Bot làm vậy.
2. Bật lại luôn về100, không thêm bộ nhớ mức dương trước mute; vẫn giữ các
   đồng bộ range/number/review và phiên như phương án1.

Không sửa âm lượng lồng tiếng, cảnh báo/ack giọng0, catalog/mode/Voice/engine,
provider, auth business, wallet/payment, CSS/motion hoặc backend. Nếu cần thay
phạm vi phải ghi amendment trước, không sửa ké.

## Cổng tiếp theo

- Chốt thiết kế và quyền gửi gói UI/test/spec/phiếu + đầy đủ MAP tới Flash3.8.
- Viết spec/checklist chính xác theo lựa chọn, kèm RED, allowlist và comparator.
- Antigravity R1 trước, R2 tối đa cùng SPEC_ID; hai lần không đạt mới Sol xhigh.
- Root test-only RED trước production, browser signed/keyboard/mobile/Voice/mode/
  session-fence, review/Testercases và một lần push sau khi cả batch đạt.
- Không có worker đang chạy cho SD-D4, chưa gửi source Bot hay dữ liệu runtime.

PROVIDER_CALLS_APP=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_MUTATIONS=0;
DEPLOY=NO; LIVE_PASS=NOT_TESTED; GOAL=ACTIVE; MOTION=LAST.
