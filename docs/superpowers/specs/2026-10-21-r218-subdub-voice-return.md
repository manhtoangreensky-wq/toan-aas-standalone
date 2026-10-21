# SD-C2 — Mở kho/thêm giọng và quay lại đúng cấu hình SubDub

Dependency: SD-B2 correction phải qua real capture/browser/session gates;
chưa BUILD khi gate đó chưa chốt. Không triển khai kho giọng hoặc ghép profile
vào engine nếu canonical capability chưa có.

## Contract

Allowed: `static/portal/portal.js` chỉ link companion SubDub, helper điều hướng
cục bộ riêng, link quay lại và nhánh nav Voice chỉ khi có continuation SubDub
hợp lệ; `static/portal/portal-i18n.js` thêm đúng key `voiceUi.workspace.returnSubDub`
cho VI/EN/ZH. Test riêng
`tests/subdub-voice-continuation.test.mjs`; harness SubDub hiện hữu chỉ nạp
helper thật mới và đổi assertion link cũ thành link có return_to đúng mode,
không bớt kiểm tra. Ledger/evidence/case. Không đổi
chữ ký hoặc logic `navigateVoiceWorkspace`, form Voice, backend/integration,
profile DTO, auth, upload, provider, ví, CSS/theme/motion.

## Luồng và cách hiển thị

1. Ở SubDub chọn Đã lưu hoặc Thêm giọng. Link vẫn là `/voice/saved` hoặc
   `/voice/clone`; kèm `return_to` chỉ chứa `/subdub?mode=` và một trong bốn
   enum mode hiện có. Không đưa nội dung, file, token, profile ID vào URL.
2. Click bình thường dùng điều hướng cùng tài liệu trong phiên đã đăng nhập:
   chụp draft SD-B2, giữ tab-memory, cập nhật history và dùng mount/hydration
   hiện có. Ctrl/Cmd/Shift/middle-click giữ hành vi trình duyệt chuẩn, không
   hứa giữ draft sang tab mới hoặc sau reload hoàn toàn.
3. Voice chỉ hiện link `Quay lại SubDub` / `Back to SubDub` / `返回 SubDub`
   khi return_to qua allowlist đúng đường/mode; không nhận external/`//`/
   encoded bypass/đường Admin hoặc URL tùy ý.
   Trong context hợp lệ, chuyển giữa bốn tab Voice tiếp tục giữ return_to bằng
   handler riêng; nhánh Voice thông thường không đổi.
4. Quay về mode gốc giữ target, lane, mix0/200, position/display và format
   riêng. UI nói mở kho/thêm giọng, không nói giọng đã được áp dụng nếu chưa
   có canonical receipt/profile handoff. Không đổi fake profile hoặc speaker map.

## Checklist / kết quả đo được

- [x] C1 RED: click thật SubDub→saved/clone→return hiện mất draft; test mới
  bắt đường đi, không chỉ assert href tồn tại.
- [x] C2 Navigation thường giữ draft/mode; native modified clicks không bị
  chặn. Back/Forward cùng tài liệu và identity thay đổi có hành vi xác định.
- [x] C3 Chỉ return path allowlist được render; không thêm quyền hay profile
  selection suy đoán, không phát sinh POST/provider/wallet/storage.
- [x] C4 Browser actual-profile VI/EN/ZH × themes ×375/390/768/1440, keyboard,
  AX/ảnh, locale/form/draft giữ nguyên và no page/console/overflow/external/UIwrite.
- [~] C5 Review/diff và comparator Voice đã khóa; full Node, source/runtime
  evidence + tester, clean provenance/PR đúng HEAD. Không dùng CI cũ để đóng.

Verify: `node --test tests/subdub-voice-continuation.test.mjs tests/voice-workspace-draft-navigation.test.mjs`
→0failure. Sau đó server QA
cô lập/Playwright Edge headless; không cần cấp lại quyền QA đã có.

Evidence: `R218-SUBDUB-VOICE-CONTINUATION-QA-20261021.json`: browserRED3
thiếu ngữ cảnh; GREEN48 vòng, focused39/39, full Node872/872. Review độc lập
39/39, không Important/Critical trong scope. Python broadened134pass/1fail
cùng literal legacy voice_style trên baseline/candidate, ghi T0. CI/PR trên
source mới chờ delivery. Không dùng Node mocks để thay browser48.

SD-D2 review/number-mute và SD-E2 semantics vẫn theo thứ tự sau SD-C2;
upload/Voice Vault mutation/engine/receipt/delivery giữ T0, không giả có.
