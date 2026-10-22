# Q0-VOICE-DIRECTION-CLARITY

BASE_SHA=30903110482f0c15b20fc959b30796dc0c7a1490.
Branch=webapp-r218-billing-ui-20261022; PR661.

## Phạm vi và nguyên nhân

Trang `/voice-studio/direction-composer` đã có lời giải thích về kết quả văn bản
trong disclosure, nhưng renderer vẫn tạo thêm ba ô âm thanh/nhà cung cấp/tác vụ
đều báo tắt. Đây là nội dung kỹ thuật lặp, không phải thiết lập sản phẩm.
Owner yêu cầu bỏ các ô tương tự trên toàn WebApp; lát này tiếp tục P1/Q0 sau
Music/SFX boundary, không mở engine/provider hay thay đổi contract.

## Acceptance

- AC1: disclosure giữ một summary và lời giải thích phạm vi bằng VI/EN/ZH;
  không còn ba ô trạng thái kỹ thuật.
- AC2: giữ nguyên năm field, giá trị mặc định, action, capability và kết quả;
  không thêm/xóa lựa chọn giọng, đồng ý quyền sử dụng hoặc chức năng Bot-parity.
- AC3: renderer thực đạt kiểm thử cho cả capability on/off; trình duyệt ở
  390/768/1440 × light/dark × VI/EN/ZH kiểm disclosure, form và overflow.
- AC4: full Node, JS syntax và protected-file diff đạt; engine/output/LIVE mở.

## Allowlist

Worker chỉ trả patch cho `static/portal/portal.js` và
`tests/voice-direction-clarity.test.mjs`; không được chỉnh file trực tiếp.
Codex áp test trước, đo RED, rồi áp implementation nguyên văn sau review.
Mọi backend, integration, CSS, locale catalog, auth, wallet, provider, Bot,
ENV, DB và workflow đều là protected comparator.

## Checklist và cổng

- [x] Đọc renderer và xác định cụm ba ô lặp trong disclosure.
- [ ] RED thực thi renderer cho VI/EN/ZH × capability on/off.
- [ ] Antigravity Flash lượt 1 trả patch; Codex kiểm đúng allowlist.
- [ ] GREEN mục tiêu và full Node/syntax/protected comparators.
- [ ] Browser disclosure mở/đóng, form không đổi, locale/theme/viewport.
- [ ] Cập nhật ledger bằng evidence; chỉ đóng đúng lát UI này.

Worker một phiên nền, model `gemini-3.8-flash-high`; không đổi settings/login,
không mở IDE. Hai lượt cùng AC vẫn sai mới Codex tiếp quản.

## Verify

`node --test tests/voice-direction-clarity.test.mjs` → fail0 sau RED hợp lệ.
`node --test tests/*.test.mjs` → fail0; baseline hiện tại927/927.
`node --check static/portal/portal.js` và `git diff --check` → exit0.
Browser dùng renderer/CSS thực, localhost và dữ liệu giả đọc-only; không dùng
fixture làm evidence provider/engine hay production.

PROVIDER_CALLS_APP=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_MUTATIONS=0;
DEPLOY=NO; LIVE_PASS=NOT_TESTED.
