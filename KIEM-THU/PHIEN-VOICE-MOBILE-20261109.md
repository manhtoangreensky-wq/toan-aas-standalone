# Kiểm thử cỡ chữ Voice — 09/11/2026

SESSION_ID=VOICE-MOBILE-INPUT-16-001
STATUS=READY_FOR_EXACT_HEAD_CI
SOURCE_SHA=a6cdc5fb69203174e0ff3793748bdbc04968435a

[Receipt](../docs/reports/voice-mobile-readability-20261109.md) ·
[120records](../reports/ui-qa/voice-mobile-20261109/readability.json) ·
[Issue689](https://github.com/manhtoangreensky-wq/toan-aas-standalone/issues/689)

- [x] RED:12mobile TTS cases/60field observations at15px.
- [x] Exact worker CSS patch, five added lines/one property.
- [x] Native TTS/STT/Clone72cases + Saved/Outputs48cases; font/geometry acceptance.
- [x] Desktop TTS per-field comparison, no overflow/errors or product action.
- [x] Runtime leaf hashes bind the capture to source commit; FullNode1880/1880.
- [x] Independent scope review:0Critical/0Important.
- [ ] Exact-head CI, merge, deploy/runtime.
- [ ] Signed production verification.

## Chạy lại

Dùng tài khoản và app QA cô lập theo hướng dẫn Tester hiện có; không dùng dữ liệu
production. Mở năm route trên ở VI/EN/ZH, light/dark và320/414/1024/1440px.
Đợi đúng tài liệu sau reload và lifecycle finite kết thúc, rồi kiểm computed
font-size của input/select/textarea trong .portal-feature-workspace--voice-task:
mobile16px; desktop giữ giá trị baseline riêng từng field.
Kiểm không tràn ngang và không phát sinh job/upload/quote/payment.

Bộ hồi quy repository:
```powershell
node --test tests/voice-workspace-draft-navigation.test.mjs tests/voice-stt-form-presentation.test.mjs
node --test tests/*.test.mjs
```
FullNode cần catalogue Bot83a994a theo workflow hiện có, chỉ đọc hai catalogue;
không bỏ test khi thiếu dependency. Kiểm manual không tạo provider output.
