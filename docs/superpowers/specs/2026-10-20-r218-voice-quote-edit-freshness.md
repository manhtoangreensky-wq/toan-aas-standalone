# R218 VO-04/06 — báo giá Voice sau khi sửa biểu mẫu

Root: `C:/Users/toann/Documents/Codex/_webapp-r218-voice`.
Baseline đã push: `51c489b968b21ca6cd5b9c8c0af4b55546cf7c27`, PR #654.
Stack: JavaScript thuần, server-rendered shell, integration.js nhận action.

## Lỗi và evidence

Actual `renderFormCard` nhận receipt estimate tổng hợp hợp lệ, `flow.input.script`
là lời thoại cũ và transient draft là lời thoại mới. Probe cục bộ trả:
`edited_script_rendered=true`, `old_quote_confirm_rendered=true`.
`integration.js` đã so sánh fingerprint trước POST confirm; lỗi cần sửa là CTA
và thông báo UI trước khi khách nhấn.

## Phạm vi

Allowed: `static/portal/portal.js`, `static/portal/portal-i18n.js`,
`tests/voice-quote-edit-freshness.test.mjs` và ledger/evidence R218.
Chỉ bốn route `/voice/tts`, `/voice/saved`, `/voice/stt`, `/voice/clone`.
Protected: Bot, `copyfast_api.py`, `static/portal/integration.js`, route-engine,
provider, ví/PayOS, workflow CI, ENV và dữ liệu production.

## Các bước thực thi

1. **So sánh input, 2–5 phút.** Thêm helper riêng Voice trong `portal.js`:
   chỉ đọc field schema của page và giá trị của quote input/current form;
   so sánh scalar theo chuỗi, checkbox theo giá trị; tệp mới luôn cần quote mới.
   Key ngoài schema không làm thay đổi trạng thái. Không sửa flow/receipt.
   Verify: `node --test tests/voice-quote-edit-freshness.test.mjs` — cases đổi
   script/giọng/speed/volume, giữ 0, revert và file/checkbox phải đạt.
2. **Render và input/change, 2–5 phút.** Receipt cũ không render confirm khi
   transient draft đã đổi. Khi nhập tại chỗ, ẩn confirm cũ và hiện
   `voiceUi.form.quoteChanged`: “Lựa chọn đã thay đổi. Xem báo giá mới trước khi
   xác nhận.” Dùng `.portal-form-note`, `role=status`, không đổi CSS/palette.
   Giữ nguyên field/focus/draft và trạng thái disabled do busy; không tự estimate.
   VI/EN/ZH cùng khóa. Chỉ phục hồi control đã có khi input quay đúng quote cũ
   và receipt vẫn fresh; không tạo control hoặc quyền mới.
3. **Nghiệm thu, 2–5 phút.** Renderer + tương tác fixture chỉ đọc, kiểm lời thoại,
   giọng, speed, volume number/range/preset, focus và không phát request.
   `node --test tests/voice-quote-edit-freshness.test.mjs tests/voice-flow-state-presentation.test.mjs`
   phải pass; `node --check static/portal/portal.js`, full Node, diff-check và CI
   trên HEAD mới phải xanh trước khi khóa UI. Giữ API/provider/delivery/LIVE mở.

## Điều kiện đóng

- [x] Mỗi thay đổi input ảnh hưởng quote đều làm confirm cũ biến mất ngay.
- [x] Re-render/hydration với transient khác input quote không phục hồi confirm.
- [x] Bản nháp/focus/âm lượng 0 còn nguyên; không đổi disabled do busy.
- [x] Thông báo VI/EN/ZH rõ; re-estimate là thao tác có chủ đích của khách.
- [x] Quote-edit UI: test riêng 11/11, focused 77/77, full Node 761/761;
  browser TTS 18 cấu hình/108 lượt đổi input đạt. CI tại `8d53dab` đã đạt:
  run `39406730261`, cả Verify Web App và Authenticated WebApp QA thành công.
  Đây là nghiệm thu UI, không thay cho xử lý âm thanh hay LIVE.

## Lát tiếp nối VOICE-QUOTE-IDLE-001 — 20/10/2026

Baseline: `8d53dabf48f422fd25dd893ce730b2cce49353f1`.
Giữ cùng phạm vi bốn route Voice và các tệp được phép ở trên; bổ sung
`tests/voice-quote-expiry.test.mjs` cùng các harness renderer Voice đang dùng
`renderFormCard`. Không thay đổi chữ ký hàm dùng chung hay schema máy chủ.

Lỗi: UI chỉ kiểm deadline khi render/input; khách để trang mở có thể nhìn
thấy xác nhận báo giá cũ sau deadline. Bản timer đang dở dựng lại cả shell,
có nguy cơ mất file input và đổi vị trí cuộn. Cách sửa được chốt: một timer
đọc timestamp canonical, đến hạn chỉ đồng bộ confirm/note trên form đang có.
Không dựng lại DOM, không fetch, không tạo estimate hoặc đổi quyền.

1. Deadline tương lai: giữ confirm hiện có; timestamp thiếu/sai giữ policy
   hiện tại, không suy ra hạn mới.
2. Đến hạn: ẩn confirm, hiện thông báo hết hạn thuần VI/EN/ZH; giữ nội dung,
   lựa chọn, âm lượng 0, tệp mẫu, form node, focus và vị trí cuộn.
3. Input/change và nhập lại giá trị cũ sau hết hạn không phục hồi confirm
   hoặc ẩn thông báo. Busy/disabled hiện có được giữ.
4. Timer cũ bị hủy khi render mới/chuyển route; callback kiểm route hiện tại
   và deadline mới. Chỉ áp dụng `/voice/tts`, `/voice/saved`, `/voice/stt`,
   `/voice/clone`.

### Nghiệm thu lát idle

- [x] Test hành vi timer/freshness: 8/8; nhóm tập trung 70/70, full Node 769/769.
- [x] Browser Edge headless localhost: TTS 18 cấu hình VI/EN/ZH × sáng/tối ×
  390/768/1440; Kho giọng/STT/Thêm giọng mỗi route 1 cấu hình; giảm chuyển động
  1 cấu hình. Tổng 22/22, form/focus/input/tệp còn nguyên, overflow/console/
  write/unknown API/request ngoài đều 0.
- [x] STT vẫn guarded bởi allowlist `integration.js`; case STT không coi
  việc gán tệp vào form tổng hợp là upload/quote/confirm thực thi.
- [x] Syntax hai file Portal và protected comparator đạt; backend,
  integration, CSS/palette, route-engine và workflow không đổi.
- [ ] CI trên checkpoint idle sau push; ghi kết quả trực tiếp trên PR #654.

Evidence: `reports/audit/R218-VOICE-QUOTE-IDLE-QA-20261020.json`.
Runtime/provider/delivery/LIVE tiếp tục mở theo checklist R218.
