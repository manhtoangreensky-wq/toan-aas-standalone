# WebApp checklist checkpoint — 09/11/2026

Đây là checkpoint của goal, không phải tuyên bố hoàn tất toàn bộ WebApp.

## Đã có bằng chứng và đã phát hành

| Nhóm | Bằng chứng hiện tại | Trạng thái |
|---|---|---|
| Locale F/G/H/I | PR690, CI `42490416291`, deploy `42491562237`, runtime `0d72bc24` | Đã triển khai/runtime verified; signed UI còn mở |
| Motion publishing | PR691, deploy `42496887494`, runtime `b7a639cb` | Đã triển khai |
| Motion lifecycle/startup | PR692, CI `42517213551`, merge `745fabbd`, deploy `42518106973` | Đã triển khai/runtime verified |
| Motion QA | Full Node `1880/1880`; Chrome menu `8/8`; landing reduced/normal; assistant closed `0` scroll read/write; layout `87.65ms → 75.07ms` cùng harness | Đã có bằng chứng cục bộ/CI; không suy ra FPS thiết bị |
| Bảo vệ phạm vi | Provider `0`, wallet `0`, ENV `0`, production data `0`; Bot/route-engine/auth authority không đổi | Đạt trong các gate của đợt |
| Voice mobile readability/Clone touch | PR chưa mở ở checkpoint; native120 records, font0 violations, Clone summary RED→green, FullNode1880/1880 | Sẵn sàng CI; signed UI/device gate riêng |

## Cổng còn mở theo đúng phạm vi goal

1. Signed production UI: chưa có phiên trình duyệt người dùng được phép để thao tác và chụp bằng chứng trực tiếp.
2. Device-level motion: chưa có đo FPS/long-task trên thiết bị thật; số đo Chrome cô lập chỉ là chẩn đoán.
3. Các PR parity cũ `#670–#673` còn mở nhưng thuộc runtime/provider/backend parity, không tự gộp vào lane UI/motion này vì nằm ngoài phạm vi goal hiện tại.
4. Issue #689 vẫn mở để giữ các cổng trên; không gắn nhãn hoàn tất toàn goal.

## Quy tắc tiếp tục

### Phạm vi bổ sung theo completion ledger R218

Danh sách cổng trên không thay thế các yêu cầu R218 còn mở ở hàng45–58 và1153–1171:
responsive shell/forms thêm320/414/1024 với type/target/contrast thực;
keyboard/focus/error/recovery thực; whole-app route×state locale/AX;
unauth direct-route/safe-next/first-paint/hydration; lab CLS/LCP/INP.
Các mục này có thể tiếp tục đo an toàn trong QA cô lập, không cần chờ signed production.
Không được suy ra cả nhóm đã đóng từ một bộ source contracts hoặc snapshot sau readyState complete.

VOICE-MOBILE-INPUT-16-001 là một lát sửa cụ thể của cổng responsive:60field RED→120cấu hình
được đối chiếu nguồn tại [receipt Voice](voice-mobile-readability-20261109.md).
Nó không đóng toàn bộ typography, AX hoặc goal.

- Không làm lại F/G/H/I hoặc P/L/N đã có runtime evidence.
- Lane mới phải có RED, scope allowlist, worker receipt, independent verification, CI, merge, deploy và runtime SHA riêng.
- Không dùng HTTP 200, CI xanh hoặc QA cô lập để thay cho signed LIVE.
- Không chạm Bot, route-engine, provider, wallet/PayOS, ENV/secrets hoặc production data.

Voice unit `VOICE-MOBILE-INPUT-16-001` và `VOICE-CLONE-TOUCH-001` chỉ đụng scoped CSS
và test/receipt; không mở upload, quote, provider, job hoặc ví. Clone summary vẫn là
acceptance touch riêng, không dùng field typography để tuyên bố toàn bộ AX.

## Provenance

- Main runtime sau motion: `745fabbdcf1306ff0c1ca92385da364f3f2ed0e8`.
- Checklist motion: `_giao-viec/MOTION-20261108-CHECKLIST.md`.
- Receipt motion: `docs/reports/motion-20261108.md`.
- Tester session: `KIEM-THU/PHIEN-MOTION-20261108.md`.
- Theo dõi duy nhất: [Issue #689](https://github.com/manhtoangreensky-wq/toan-aas-standalone/issues/689).
