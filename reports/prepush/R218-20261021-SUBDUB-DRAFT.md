# SD-B2 — báo cáo trước push

Đang đọc và áp dụng skill owner-governed-codex cho task này.
BASE_SHA=83b6623f45e1c9e99a341690f54fbef3884081c2; source HEAD trước provenance
`22ff350fe07170ed3ba429d9dad77c09ab70ef37`; PR654; không merge/deploy.

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
