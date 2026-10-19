# R218 — AD-02-STATE-LOCALE

## Kết quả cần đạt và thứ tự

Sửa nhãn trạng thái dùng chung bị rơi về tiếng Việt khi giao diện chọn Anh/Trung.
Thực hiện sau khi nghiệm thu AD-02-MOBILE-DATA và trước ma trận role/module của Admin.
Spec này thuộc A0 và đóng một phần F0/Q0 locale; không đóng toàn bộ Admin hoặc LIVE.

Lỗi đã xác minh ngày 19/10/2026: fixture dùng shell/renderer/integration/CSS production,
VI/EN × sáng/tối × 390/1440. `failed_no_charge` hiển thị tiếng Việt ở cả bốn cấu hình EN.
Artifact: `../qa/r218-voice-inventory/admin-data-reviewed.json`, SHA256
`8995d3f057bffe687850967652fbc1de7799dc3d1d0068bc3590c87ce2e0c636`.
`STATE_I18N_KEYS` thiếu 14 trạng thái được `ALLOWED_STATES` cho phép; `stateLabel()` vì
thế dùng `STATE_LABELS` tiếng Việt. Catalogue VI còn dùng danh từ chung `Backlog`.

## Contract

- BASE/HEAD: `1730ea41ffda53e6bcd068f45a49c8c9f6949929`.
- Worktree: `C:/Users/toann/Documents/Codex/_webapp-r218-voice` (detached; không đổi ref).
- COMPLEX do ảnh hưởng shared renderer; một worker Antigravity, hai bước có gate.
- Allowed: `static/portal/portal.js` chỉ `STATE_LABELS`/`STATE_I18N_KEYS`;
  `static/portal/portal-i18n.js` chỉ catalogue `states.*` VI/EN/ZH;
  `tests/shared-state-label-locale.test.mjs`.
- Protected: enum/state transitions, API/auth/RBAC/route-engine/DB/provider/wallet/payment,
  CSS/theme, mọi renderer khác và mọi diff/tài liệu có sẵn.
- Không đổi tên/chữ ký `stateLabel`, không đổi giá trị `data-status`, không thêm state.
- Provider/wallet/production writes/Git/merge/deploy của worker = 0/NO.

## Bảng nhãn bắt buộc

| State | Khóa mới/hiện có | VI | EN | ZH |
|---|---|---|---|---|
| failed_no_charge | states.failedNoCharge | Không hoàn tất · chưa trừ Xu | Failed · no Xu charged | 未完成 · 未扣除 Xu |
| refunded | states.refunded | Đã hoàn Xu | Xu refunded | 已退还 Xu |
| in_review | states.inReview | Đang chờ duyệt | Pending review | 待审核 |
| approved | states.approved | Đã sẵn sàng | Approved | 已批准 |
| error | states.error | Lỗi kết nối | Connection error | 连接错误 |
| new | states.new | Yêu cầu mới | New request | 新请求 |
| waiting_user | states.waitingUser | Chờ bạn phản hồi | Awaiting your reply | 等待你的回复 |
| waiting_provider | states.waitingProvider | Chờ đối tác xác minh | Awaiting partner verification | 等待合作方核实 |
| refund_pending | states.refundPending | Đang xem xét hoàn tiền | Refund under review | 退款审核中 |
| resolved | states.resolved | Đã xử lý | Resolved | 已解决 |
| closed | states.closed | Đã đóng | Closed | 已关闭 |
| unread | states.unread | Chưa đọc | Unread | 未读 |
| read | states.read | Đã đọc | Read | 已读 |
| dismissed | states.dismissed | Đã bỏ qua | Dismissed | 已忽略 |
| backlog | states.backlog | Việc chờ xử lý | Backlog | 待办列表 |

Giữ các nhãn đã dịch còn lại. Đồng bộ fallback VI `STATE_LABELS.backlog` với bảng trên.
`read_only` tiếp tục alias `ready`; trạng thái không hợp lệ tiếp tục về `guarded`.
Xu là tên đơn vị nên giữ nguyên trong ba locale.

## Acceptance / evidence

1. 35 state hợp lệ đều có khóa mà catalogue của từng locale chứa; không dùng fallback
   tiếng Việt trong EN/ZH. Ba locale có cùng tập khóa `states.*`.
2. 15 dòng bảng trên trả đúng nhãn bằng hàm `stateLabel()` thật và catalogue thật.
3. Unknown state/chuỗi HTML không được hiện nguyên văn; `read_only` vẫn trả nhãn `ready`.
4. Danh sách enum, route, capability, status payload và CSS không đổi.
5. Browser Admin giữ 8/8 layout/interaction cũ; mở rộng ZH để có 12 cấu hình. Mọi nhãn
   `failed_no_charge` phải khớp locale, không chỉ text trong catalogue.
6. Test mục tiêu, full Node, syntax, diff check và protected diff đều đạt. Đây là
   fixture presentation, không chứng minh backend/RBAC hoặc production LIVE.

## RED → GREEN

- Bước A (worker, 2–5 phút): chỉ tạo test, rồi dừng. Test dùng `vm` nạp catalogue thật,
  trích toàn bộ constants ALLOWED_STATES/STATE_LABELS/STATE_I18N_KEYS và stateLabel thật
  từ `portal.js`; không dùng nhãn giả hoặc ép fallback. Mỗi locale có hai test (coverage
  mọi state và exact labels); thêm một test unknown/read_only dùng cả ba locale: 7 test.
- Codex chạy `node --test tests/shared-state-label-locale.test.mjs`: cần RED do các
  mapping/nhãn đang thiếu. Lưu output trước khi mở B.
- Bước B (worker, 2–5 phút): chỉ thêm mapping/catalogue được chỉ định, cập nhật fallback
  backlog. Không giảm assertion hoặc sửa các test khác.
- Codex chạy cùng test: 7/7, rồi `node --test tests/*.test.mjs`, syntax hai JS,
  `git diff --check` và browser fixture 12 cấu hình.
- Worker dùng công cụ tệp; không chạy shell/terminal qua UI. Tất cả test do Codex chạy.

## Giao nhận và dừng

Giữ SPEC_ID, HANDOFF_ROUND và SAME_DEFECT_FAILED_HANDOFFS qua từng giao nhận. Lỗi hook
hạ tầng không là một lần code sai. Nếu cùng AC code sai hai lượt thì áp dụng escalation
đã quy định; không tự mở rộng allowlist. Báo cáo thiếu evidence phải ghi NOT_RUN.
Không gọi spec ACCEPTED từ báo cáo worker. Codex cập nhật checklist mẹ sau review/verify.

## Kết quả thực thi 19/10/2026

`ACCEPTED_LOCAL_UI_CI_PENDING`: Codex đo RED 1 pass/6 fail, rồi GREEN 7/7 với test
giữ nguyên; full Node 713/713; syntax/diff check và comparator enum/function/backend
đạt. Browser 12/12, locale state chính xác, mobile318/318px, filter/empty/focus/keyboard
đạt; errors/writes/external/unknown0. Artifact mới `admin-state-locale.json` SHA256
`85ebdac2270a7dc393137f4fe5e35717ec7a56518b14d2bb1d459eeac6f73561` trong QA folder.
Logs `state-locale-red.txt` / `state-locale-green.txt`. Chưa commit/push/CI/deploy/LIVE.
Không suy ra toàn trang hoặc toàn bộ Admin đã sạch locale từ acceptance của state labels.
