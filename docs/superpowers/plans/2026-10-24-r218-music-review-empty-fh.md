# Music UI F → H — xem lại yêu cầu, bỏ card rỗng

ROOT `C:/Users/toann/Documents/Codex/_webapp-r218-voice`; branch
`webapp-r218-billing-ui-20261022`; BASE `1e01f2417e3000a09c45186e11ee144e52a22fa5`.
PR661 / Issue664. E đã accepted: CI39992812318 cả hai job thành công,
receipt6370628830. D1/D2/E khóa, không làm lại.

Theo Owner: làm phần dở dang trước, UI/UX trước, không ô vô nghĩa/output giả,
đủ chức năng theo Bot nhưng tối ưu Web; motion và kỹ thuật engine làm cuối.

> note rõ là chia plan chi tiết ra thành từng spec kèm theo kết quả cần đạt
> để qua spec khác, với spec đơn giản thì chạy nhiều spec một lúc, nếu spec
> phức tạp thì làm từng spec.

| Thứ tự | SPEC_ID | Kết quả đo được | Dependency | Kiểu chạy | Trạng thái |
|---|---|---|---|---|---|
| 1 | MU08-F-REQUEST-REVIEW | Snapshot input đã gửi hiển thị trước CTA, không thay quote/confirm hoặc mất draft | E accepted | COMPLEX/SINGLE | ACCEPTED_LOCAL;delivery chung còn mở |
| 2 | MU-PRODUCT-EMPTY-H | Music chưa có flow không còn card kết quả rỗng; flow thật/error/report giữ nguyên | F local acceptance | BOUNDED/SINGLE | ACCEPTED_LOCAL |
| 3 | FH-DELIVERY | Cả hai spec đủ review/QA/docs/Tester/provenance, push một lần, CI và receipt đúng HEAD | F/H local acceptance | Codex only | RUNNING;không merge/deploy |

Cùng chạm portal.js nên chạy tuần tự, không nhiều worker ghi cùng source.
Mỗi spec giữ R1/R2 riêng; không R3/reset ID, không dùng H sửa lén lỗi của F.
Antigravity3.8Flash chạy nền, source-only stdout; Codex test trước/sau, review,
QA và Git. Không IDE/login/settings; không runtimeQA/DB/secret gửi worker.

F dùng actual renderer unit tests và app signed QA với controlled flow fixtures
được ghi rõ, không gọi quote/provider thật. H initial-state dùng actual app
GET-only, không API fixtures. Không suy fixture thành engine/output/LIVE.

Không đổi Bot/route-engine/backend/auth/ENV/provider/ví/PayOS/production data.
Không merge/deploy khi whole PR/master còn mở. MU02 style mapping, MU06 length,
audio2tracks/player/editor/runtime recovery và MU07 workflow vẫn trong backlog.
