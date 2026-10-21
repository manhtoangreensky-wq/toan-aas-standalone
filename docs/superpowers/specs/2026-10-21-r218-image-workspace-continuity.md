# IM-A2 — Điều hướng và bản nháp bốn chế độ ảnh

BASE `13eb5a13531ecd49bb8d96524928b077bd7a1271`; PR #654.
Lát Image presentation cũ chỉ là smoke, không phải nghiệm thu luồng.

## Lỗi đã đo và kết quả cần đạt

Browser QA signed VI/dark/390 RED3: click Create→AI edit làm mất tài liệu,
AI edit thiếu nav chung, Back về Create mất prompt. Bốn mode phải có cùng
điều hướng dọc, đổi qua lại giữ riêng bản nháp scalar trong cùng phiên.

## CONTRACT

Allowed: `static/portal/portal.js` chỉ Image nav/capture/session và chèn nav
vào renderer Create/Studio/AI-edit/Manual cả nhánh guarded; test Image, docs/
evidence/tester/state. Copy dùng catalogue `imageCreate.workflow` VI/EN/ZH
hiện có. Không đổi CSS/theme/motion, backend/API/DTO/auth/engine/provider/ví,
không sửa integration hoặc các helper Voice/Music/SubDub đã khóa.

## Thứ tự

1. Đóng dấu smoke cũ: không dùng 18 case fixture làm bằng chứng signed flow.
2. RED Node/browser: bốn nav, native modified clicks, route allowlist/session,
   same-mode không thêm history, riêng form chính và bản nháp scalar.
3. Nav dùng bốn route cố định: `/image/create`, `/image-studio`,
   `/image/transform`, `/image/edit`; aliases chỉ normalize nguồn, không nhận
   target ngoài/record/query/hash. Normal-click signed dùng pushState rồi
   popstate hiện hữu để integration tái hydrate đúng route, không mount trước
   làm handler return sớm. Giữ hành vi native khi không có integration.
4. Capture chỉ field của form chính theo mode; không file/password/token,
   quote/receipt/provider/job, filter hay record chi tiết. Asset/project chỉ
   giữ khi còn là option owner-scoped hợp lệ. Không tự gộp asset ID giữa modes.
5. Identity replacement/logout xóa draft Image; cùng identity giữ riêng.
6. Browser signed VI/EN/ZH × light/dark ×375/390/768/1440: A→B→C→D→A,
   Back/Forward, locale/theme, alias, keyboard, focus, no stale quote/record,
   no UIwrite/provider/external/overflow. Engine/multi-product output còn T0.

## Gate

- [ ] Native finite navigation và 4 nav có active-state đúng.
- [ ] Prompt/field scalar không mất qua chuyển mode/Back/Forward/remount.
- [ ] Session cleanup không lộ draft giữa tài khoản.
- [ ] Capability/quote/receipt/ownership vẫn fail-closed, không fake output.
- [ ] Browser thật, protected comparator, regression, tester/docs/provenance/CI.

Không hứa giữ file bytes hoặc draft qua reload/tab mới. Motion vẫn làm cuối.
