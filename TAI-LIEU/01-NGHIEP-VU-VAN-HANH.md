# Nghiệp vụ vận hành TOAN AAS Web App — batch khôi phục và motion

Đo tại branch `fix/webapp-live-recovery-001`, base `896d3761aa1126cf4bd6a6f08e2f9a9d7c51e972`, ngày 26/08/2026.

## Hệ thống trong batch

1. `copyfast_pages.py` phát vỏ trang, asset version và reserve HTML đầu tiên.
2. `static/portal/portal-auth.js` điều khiển màn đăng nhập/đăng ký và readiness của Telegram/Google/Apple.
3. `static/portal/portal.js`, `portal-features.js`, `portal-motion.js` dựng Workspace/Admin, catalog và lifecycle presentation.
4. `static/portal/integration.js` hydrate catalog/auth/billing và checkout.
5. `copyfast_api.py` có `50` route decorator hiện tại; diff batch thêm `0` decorator mới.

## Số đo phạm vi

- `11` file production đang đổi: `2` Python, `8` asset Portal có sẵn và `1` bundle catalog mới.
- `14` file test thuộc batch; `5` state file ghi cổng auth, PayOS và motion.
- `0` migration/schema file thay đổi; không đọc hoặc ghi dữ liệu production trong local verify.
- Catalog render đủ `135/135` mục trong hai lượt evidence.
- Motion dùng token `140/220/420ms`, opacity/transform; CTA PWA và Copilot có hit target `44×44px`.

## Luồng vận hành hiện tại

- Auth: server trả readiness; Google thiếu `6/6` cấu hình và Apple thiếu `8/8`, vì vậy UI không tạo nút giả. Telegram giữ hành vi đã khóa.
- Workspace/Admin: reserve HTML giữ bố cục trước hydrate; cùng route không replay full-shell entrance hoặc View Transition.
- Catalog: `/features` tải bundle riêng, không parse toàn integration bundle để dựng danh sách ban đầu.
- PayOS: click tin cậy mở placeholder, backend chỉ trả checkout URL đã kiểm; cùng idempotency key tạo tối đa một order. Local test dùng provider stub, không gọi PayOS thật.
- Settlement: API chỉ công khai `PENDING`, `PAID`, `FAILED`, `CANCELLED`; không cộng Xu trong task/test.

## Ai được làm gì

- Quyền route/role vẫn do server cấp; browser không tự thăng quyền.
- Admin và khách dùng shell riêng nhưng cùng token UI/motion.
- Auth provider chỉ xuất hiện khi readiness `enabled=true` từ server.
- Batch không đổi user, role, schema, secret hoặc ENV.

## Bẫy vận hành

- `MERGED != DEPLOYED != LIVE`; HTTP 200 không chứng minh hydrate, checkout hoặc motion đạt.
- Không full-remount sau provider/catalog hydrate: có thể xóa dữ liệu người dùng đang gõ và replay motion.
- Không dùng `transition: all`; không để content phụ thuộc observer mới nhìn thấy.
- Google/Apple không thể E2E khi ENV còn thiếu; giữ ẩn an toàn thay vì tạo nút chết.
- PayOS live chỉ được tạo đúng một checkout sau deploy; cấm quét QR, thanh toán hoặc cộng Xu.

## Bằng chứng local hiện tại

- Motion Web App: protected `19P + 51P`; hai lượt × bốn viewport có CLS/overlap/overflow/clip/app error/non-read request `0`.
- PayOS settlement: `9P`; checkout `15P`; bridge `30P`; promo `5P`; provider call thật `0`.
- Google/Apple readiness UI: `8/8` viewport mỗi provider an toàn; E2E bị chặn bởi cấu hình ngoài code.
- Tester project: issue `manhtoangreensky-wq/toan-aas-standalone#412`; evidence local ở `D:/TOANAAS/TOAN_AAS_WEB_APP/evidence/`.

## Việc còn treo

- Fresh pre-push suite trên diff cuối; PR/checks/merge/deploy/runtime SHA.
- Live Web App desktop/mobile trên đúng revision.
- PayOS một click mở checkout thật theo gate; không thanh toán.
- Google/Apple chỉ mở lại khi Owner cấp đủ cấu hình; task này không sửa ENV.
