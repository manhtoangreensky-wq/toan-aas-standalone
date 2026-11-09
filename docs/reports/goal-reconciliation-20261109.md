# Đối soát yêu cầu và thứ tự tiếp tục — 09/11/2026

Đây là view của completion ledger R218, không tạo checklist cạnh tranh hoặc
đổi mục tiêu. Mỗi hàng chỉ đóng khi có bằng chứng đúng phạm vi; code, CI,
deployed và LIVE là bốn mức khác nhau. Sổ GitHub duy nhất là Issue689.

## Thứ tự thực thi

| Thứ tự | Nhóm | Evidence đang có | Cổng tiếp theo bắt buộc |
|---|---|---|---|
| 1 | WIP biểu mẫu kế hoạch video + early opt-in | Renderer23/23; native18/18; markup8/8; actual-source nav8/8; fullNode1938/Python26; source review không đổi guard/data | Đã merge/deploy PR702 (CI42650106952, runtime e88f25ba, deploy42652904052); fallback native và broader route/locale responsive còn mở |
| 2 | Đối chiếu delivery đã cũ | PR700/701 đã merge/deploy; kiểm lại GitHub và VPS trả2c186071, ba services active, portal.js f0150811… | Giữ riêng delivery đã đóng và motion/native còn mở; không làm lại mã đã khóa |
| 3 | Whole-app locale VI/EN/ZH | Các unit đã phát hành và WIP là những lát hẹp | Visible DOM/AX theo route×state, gồm loading/error/empty/read-only/guarded; giữ brand và dữ liệu khách |
| 4 | Nội dung có mục đích | Các unit bỏ thẻ dư đã có evidence riêng | Inventory control→mục đích/action/output; không filler, khung trống, fake ready hoặc che guard |
| 5 | Responsive/type/target/contrast | Voice/Clone/Features/Account có evidence hẹp | Mở rộng375/390/768/1440 và320/414/1024; computed type,44px targets,AAcontrast sau animation settlement |
| 6 | Keyboard/focus/error/recovery | PR701 có20ca focus và các menu/Escape controls | Tab order/tên truy cập, invalid field/error focus, modal/drawer, disabled/loading/failure và recovery thực |
| 7 | Auth lifecycle/first paint/safe return | Source gates và authenticated matrix | Cold unauth direct routes, protected flash từ early document, safe next/no open redirect, skeleton→shell→data ổn định |
| 8 | Motion/performance cuối | PR700/701 đóng vài root cause; WIP early opt-in có diagnostic | M-FINAL-01..06: ít nhất3lượt tương đương, normal/reduced, nhiều viewport/landscape, frame/longtask/CLS/LCP/INP và review ảnh/video |
| 9 | Reconcile/live tổng | Runtime/source/asset/service từng release | Signed production/device và requirement-by-requirement audit; không tự mở T0/Bot/engine/provider/ví |

## Phần phải giữ mở, không bỏ sót

- Renderer kết quả `/video-studio/motion-guide` còn fixed headings tiếng Anh
  trong VI/ZH; `/video-studio/long-form-planner` có khoảng hở tương tự. Audit
  trước đã tái hiện6render, chưa có patch trong batch hiện tại.
- R218 Q0-CUSTOMER-CONTENT và whole-route locale/AX không đóng bằng hash catalog.
- Các bộ contract/source xanh không thay kiểm tra keyboard hoặc auth first paint.
- Body mobile≥16px, target≥44×44px và contrastAA cần đo đúng control. Quan sát
  Account43.92px chưa có nguyên nhân, không gọi là rounding đã chứng minh.
- Trace startup còn tác vụ dài; việc dời reset cuộn chưa có A/B hợp lệ và chưa
  được triển khai. Không suy sửa opt-in làm hết giật toàn app.

## Nguồn yêu cầu chuẩn

- [Completion ledger R218](../../reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-R218.md)
- [Crosswalk lịch sử](../../reports/audit/WEBAPP-HISTORICAL-CHECKLIST-CROSSWALK-R218.md)
- [Checklist R217](../../reports/audit/WEBAPP-UIUX-PARITY-MASTER-CHECKLIST-20261016.md)
- [Auth/accessibility](../superpowers/specs/2026-10-16-r217-03-auth-accessibility.md)
- [Motion/performance](../superpowers/specs/2026-10-16-r217-10-motion-performance.md)

Không công nhận toàn goal hoàn tất từ việc push tài liệu, một batch renderer,
HTTP200, CI456records hoặc source fingerprint. Các nhánh backend/provider parity
ngoài phạm vi UI không được tự gộp để sửa ví/engine/production data.
