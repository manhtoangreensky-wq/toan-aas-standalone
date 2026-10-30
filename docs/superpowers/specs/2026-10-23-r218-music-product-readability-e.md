# MU-PRODUCT-READABILITY-E — Nhạc nền/Bài hát đọc và nhập rõ ràng

Bắt đầu 23/10/2026; nghiệm thu R2 ngày24/10/2026.
Trạng thái: R2_LOCAL_UI_ACCEPTED_DELIVERY_PENDING.
Repo: standalone WebApp; root `C:/Users/toann/Documents/Codex/_webapp-r218-voice`.
Branch: `webapp-r218-billing-ui-20261022`; PR661 / Issue664.
BASE: `e8738b5ac6078c86e8793632cab3d0f3488e3f09`.
D1–D2 đã nhận tại receipt6369576116, CI39985131009 thành công cả hai job.
Hợp đồng E được công bố trước BUILD tại Issue664#issuecomment-6369813736.

## 1. Phạm vi và lỗi đã đo

E chỉ áp dụng cho `/music/create` và `/music/song`, khác hai công cụ văn bản
native Music Directions/SFX đã khóa trong D1–D2.

App QA đã đăng nhập, DB tạm, bridge/PayOS/provider tắt. Baseline 24 cấu hình:
2 route × VI/EN/ZH × sáng/tối × 390/1440. Sau auth/locale setup, UI chỉ GET.

- 66 mẫu chữ hướng dẫn nền sáng: màu 170/184/199 trên trắng, tương phản 2,021.
- 66 mẫu nền tối: tương phản 5,522.
- 132 mẫu input/select/textarea: cỡ 15px.
- Không lỗi JS, request ngoài phạm vi, request ghi từ UI hoặc tràn ngang.
- Actual gate trước sửa: 66 lỗi tương phản + 132 lỗi cỡ chữ; exit 1.
- SHA baseline: `2e6c4f6f14284a7051949bced0e940e9dbc7fd5af37cacc625c5d3289e374730`.

Kết quả duy nhất cần đạt: chữ hướng dẫn >=4,5:1 và ô nhập 16px,
không thay control, dữ liệu, bản nháp hoặc luồng xử lý.

## 2. Allowlist và thay đổi chính xác

Builder chỉ được sửa `static/portal/portal-theme.css`. R1 đã chèn đúng hai
rule đầu. R2 bổ sung hai rule nhãn/placeholder, không sửa hai rule R1.
Cả block nằm ngay trước `/* Final light AI Chat Workspace surface */`.

```css
[data-music-product-form] .portal-field-help {
  color: var(--portal-muted);
}
[data-music-product-form] :is(input, select, textarea) {
  font-size: 16px;
}
[data-music-product-form] .portal-field > label {
  color: var(--portal-ink);
}
[data-music-product-form] :is(input, textarea)::placeholder {
  color: var(--portal-input-placeholder, var(--portal-muted));
}
```

Hook chỉ được render ở hai form Music. Không sửa/xóa/reorder CSS cũ;
không đổi palette/token, min/max/step/height, button, focus, JS, i18n,
options, API, draft, báo giá, xác nhận, auth, backend, Bot, provider, ví,
ENV, motion hay test cũ. D1–D2 và toàn bộ Chat marker→EOF phải giữ nguyên.
Comparator sử dụng CRLF→LF normalization, không tuyên bố raw-byte equality.

## 3. Các bước và nghiệm thu

1. Chạy actual browser baseline gate trước source; phải thất bại do tương
   phản/cỡ chữ, không phải lỗi harness.
2. Giao Flash3.8 chạy nền, source-only, chỉ trả một edit record qua stdout.
   Không cấp tools/terminal/Git/filewrite/browser/IDE/auth/settings.
   Không gửi runtime QA, log, DB, ảnh hoặc secret.
3. Codex áp nguyên văn sau RED; bỏ block mới phải trả CSS về BASE, toàn bộ
   source/test ngoài allowlist không đổi.
4. Actual green 48 cấu hình: 24 cấu hình chính cộng dark 360/375/768/844
   landscape, hai route và ba locale. Đo helper AA, input16, submit44;
   đổi đủ 3 tier/4 vocal, giữ lyrics Unicode và bản nháp qua mode/Back;
   mở hướng dẫn bằng bàn phím, kiểm AX và CSS text 200%, không tràn ngang.
5. Chạy Node đầy đủ, Music focused27, native Python21 + foundation90,
   review độc lập, tài liệu vận hành/đối chiếu gốc, Tester, prepush,
   provenance, push/readback, CI cả hai job và receipt trước khi đóng E.

Không thêm unit chỉ grep CSS rồi coi đó là proof computed style.
Actual browser RED/GREEN là bài kiểm hành vi chính; test cũ vẫn hồi quy.
Browser plugin không có: dùng Edge headless/Playwright sẵn có, không cài gói.
Không suy từ CSS text stress ra OS Dynamic Type/installed PWA/audio/LIVE.

## 4. Checklist và bằng chứng

- [x] Baseline và allowlist được chốt trước BUILD.
- [x] E01 Flash R1 trả đúng một record, áp nguyên văn; 7 dòng/2 rule,
  không cần R2 hoặc Codex sửa production.
- [x] E02: R1 actual48 có helper sáng5,797/tối5,522, 264 ô nhập16px;
  144 tier checks, 288 vocal checks, 48 mode/Back, keyboard/AX/text-stress;
  R2 đã đo lại48:264 nhãn sáng12,352/tối13,903,120 placeholder đều>=5,522;
  association label/control đúng, giữ nguyên opacity1. Tất cả gate tương tác
  và stress chạy lại, lỗi JS/request ngoài/UI write/tràn ngang đều0.
- [x] Hồi quy Node1073/1073; Python111/111; review độc lập C0/I0/M0.
- [ ] E03 tài liệu/Tester/prepush/provenance/push/CI/receipt giao nhánh.

Raw green: `20cbee08147a12ef1678d8305a4f304df6c08d272b7414e0c76f24135f19745e`.
Evidence: `reports/audit/R218-MUSIC-PRODUCT-READABILITY-E-QA-20261023.json`.
Server QA35978 đã dừng, DB/assets tạm được dọn, listener0.

### Amendment R2 — thiếu gate nhãn/placeholder trong hợp đồng ban đầu

Ảnh QA cho thấy tên trường còn quá nhạt. Fresh signed QA37013 chạy24 cấu hình
với R1 source:132 nhãn có66 mẫu sáng chỉ1,265:1, tối11,528; association label
for/control đều đúng. Actual label gate exit1. Raw
`85f0feddc73ae17b60446e3c9376b24527a6479004091a67eb44208975d62e7d`.
Probe riêng4 cấu hình/10 placeholder:5 mẫu sáng3,233:1,5 mẫu tối5,522:1;
opacity đều1. Đây là SPEC_GAP: R1 làm đúng2rule đã giao, không phải lỗi thợ.

R2 chỉ thêm hai rule còn lại trong block trên: nhãn dùng existing ink,
placeholder dùng existing input-placeholder/muted. Không đổi opacity, text,
label/control association, JS, dữ liệu hoặc motion. Dark placeholder rule
`!important` hiện có vẫn giữ nguyên. Không thêm `!important` mới.
Actual green R2 phải có48 cấu hình, helper/label/placeholder đều>=4,5,
input16, đầy đủ các gate tương tác ban đầu. Không R3, không reset SPEC_ID;
giữ baseline và R1 green ở đường dẫn riêng, không ghi đè lịch sử.

R2 Flash3.8Low SUCCESS35.0134596s/1turn/source-only12117chars, một record
áp nguyên văn; không Codex sửa production/không R3. Final48 rawSHA
`1e706412c245756e72ec2593b24a64e76ca7725a83f8ad11d7b74c0d8ba759f2`,
themeSHA794b14e5d50d461462923273c4a882cbe51e7b11594160fb466c80cff506376c.
Node1073/1073,35143.7118ms; Python111/111,32.67s/2existingwarnings;
independent R1+R2 composition/reverse/12protected/oldtests/Chat/D1D2 PASS,
C0/I0/M0. Ba server QA đều dừng/DB-assets tạm dọn/listeners0.

## 5. Thứ tự sau E — không sửa ké

F: summary read-only từ snapshot `flow.input` cho MU08; không đổi server
quote/confirm/fingerprint và không giả selected-suggestion ID.
MU07: workflow Đổi/Sửa/Back cần spec riêng; không tạo bộ gợi ý thay thế giả.
MU02 style/style_prompt mapping, MU06 half/full, audio/2tracks/player/editor
là contract/runtime backlog, vẫn giữ trong checklist.

R1/R2 tối đa cùng ID, không R3. PROVIDER_CALLS_APP=0; WALLET_MUTATIONS=0;
DEPLOY=NO; LIVE_PASS=NOT_TESTED; GOAL=ACTIVE; MOTION=LAST.
