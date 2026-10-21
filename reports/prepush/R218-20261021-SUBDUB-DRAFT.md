# SD-B2 — báo cáo trước push

Đang đọc và áp dụng skill owner-governed-codex cho task này.
BASE_SHA=83b6623f45e1c9e99a341690f54fbef3884081c2; source HEAD trước provenance
`22ff350fe07170ed3ba429d9dad77c09ab70ef37`; PR654; không merge/deploy.

## Correction ưu tiên ngày21/10 — thay kết luận capture cũ

Test21 trước đó chưa chạy capture: direct probe và browser thực phát hiện14
sai lệch nên SD-B2 đã mở lại. Correction bỏ regex HTML, normalize whitelist,
chụp range không name/position suffix, latest shared field và format riêng,
render input/output/checked/classes/link từ cùng draft; presentation identity
thay đổi/đăng xuất xóa slot riêng, không đổi auth server. Comment Music chỉ
để chiều literal CI đã bỏ; test cũ chuyển sang kiểm boundary không player/
download/confirm thay câu chữ đã đổi. Full UI foundation90/90.

Targeted25/25; full Node861/861; Python119/119; browser final24 cấu hình có
profile locale thật, đổi mode/remount/input/output0/200/checked1/latest target/
format riêng/identity projection cleanup/AX/ảnh, no failures/page/console/
UIwrite/external/overflow. Review độc lập25/25, không Important/Critical còn lại
trong scope. Case SDDRAFT-01..04 đã có, metadata LF remeasure; TAI-LIEU đã đính
chính. Evidence `R218-SUBDUB-DRAFT-RUNTIME-CORRECTION-QA-20261021.json`.
Source/CI mới cần commit/provenance sạch; không dùng CI cũ hay Node21 làm
parity toàn SubDub. SD-C2/SD-D2/SD-E2 và T0 vẫn mở.

## Finding và sửa

SubDub đổi Lồng tiếng → Combo chỉ đổi tab, còn target/giọng/âm lượng/vị trí/
kiểu hiển thị quay về default. Render lại cũng không đọc draft. Đã thêm draft
tab-memory `/subdub`, chụp input/change và trước mode switch; chỉ các trường
tương thích được chia sẻ. Không URL/localStorage/cookie/provider ID; field
không phù hợp không được thêm vào payload/CTA.

## Verify

`node --test tests/subdub-hub-presentation.test.mjs` → 21/21; full Node →
857/857; `node --check static/portal/portal.js` và diff-check exit0. RED mới
đã fail trước code vì target/volume/voice default; GREEN sau sửa. Existing
guarded upload/CTA/report, callback Auto2/AutoMulti3-8/SmartMulti và route
query tests vẫn đạt.

Focused test không phải browser: AX, remount trên app thật, mobile/theme và
Voice handoff chưa đóng; giữ SD-C2/SD-D2/SD-E2 mở. Không sửa CSS, i18n,
integration/backend/Bot/engine/provider/wallet/auth/schema.

Clean provenance refresh/verify từ checkout sạch: fingerprint
`ade97dc18ff2cf1aeaa71a7e1324fb59b3db95d61afc4c2e18e0de7977eb4e68`.
Tester PR hiện hữu, không tạo issue/project mới.

PROVIDER_CALLS=0; WALLET_MUTATIONS=0; DEPLOY=NO; LIVE_PASS=NOT_TESTED.
