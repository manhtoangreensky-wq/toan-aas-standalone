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
- [~] Source/UI đã kiểm: test riêng 11/11, focused 77/77, full Node 761/761;
  browser TTS 18 cấu hình/108 lượt đổi input đạt. CI trên commit mới còn chờ;
  kết quả delivery sẽ được ghi trên PR #654. STT/clone chỉ có kiểm so sánh
  source/file/consent, chưa có browser runtime riêng cho hai luồng đó.
