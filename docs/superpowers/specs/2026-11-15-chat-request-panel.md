# CHAT-REQUEST-PANEL-PLAIN + CHAT-RUN-TIMELINE-PLAIN — 15/11/2026

Đang đọc và áp dụng skill owner-governed-codex cho task này.

GOAL=Khách đọc và theo dõi yêu cầu bằng đúng VI/EN/ZH, không gặp giải thích triển khai hoặc ô trạng thái thừa.
BASE_SHA=63ddccd5e34ee44590ff0493ba6a396d1e5cec2d
BRANCH=codex/chat-request-panel-20261115
TRACKER=Issue #689; checklist mẹ reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-R218.md

## Phạm vi khóa

- Áp đúng sáu thay thế Antigravity: panel R1 (ba), timeline R1 (ba).
- Ứng dụng: `static/portal/portal.js`, `static/portal/portal-i18n.js`, `static/portal/portal.css`.
- 29 khóa mỗi ngôn ngữ, thứ tự panel 17 rồi timeline 12; 87 giá trị.
- Bỏ đúng hai ô Bot/payment và Output/delivery; giữ hai trạng thái tiếp nhận và trả lời tự động, không giấu giới hạn thật.
- Desktop từ bốn sang hai cột, mobile một cột giữ nguyên. Không để vùng trống.
- Giữ nguyên quyền, trạng thái được phép gửi, xác nhận, dữ liệu, ID, route, form, field, attributes và disabled.
- Giữ bộ lọc yêu cầu, thứ tự, giới hạn 50, timestamp lưu trữ và chuẩn hóa trạng thái.
- Không bật trả lời tự động, không thay auth/backend/engine/Bot/provider/ví/PayOS/ENV/schema hoặc motion.
- Chữ do khách nhập, tên thương hiệu và tên tệp không bị dịch hoặc lọc.
- Amendment kiểm thử trước áp dụng: một needle trong `tests/test_chat_workspace_portal_contracts.py` ghim nguyên câu xác nhận cũ; thay đúng needle đó bằng biểu thức xác nhận mới qua `safeText(uiText(...))`. Giữ nguyên toàn bộ chốt quyền, action, dữ liệu nhạy cảm và mobile. Ngoài bốn tệp test mới/hai adapter history, chỉ thêm tệp test Python này vào allowlist.

## Checklist trước áp dụng

- [x] History prerequisite: PR739, CI43643846449 cả hai nhóm đạt; deploy43644999130; revision máy chủ và bốn tệp công khai khớp merge63ddccd5.
- [x] Hai phiên worker đã trả mã; raw và kết quả đối chiếu được giữ. Panel có lỗi ranh giới LF từ điều phối, không tính lỗi mã worker.
- [x] Bốn tệp test/fixture mới và hai adapter test hiện hữu chỉ nhận phép chiếu hữu hạn, giữ nguyên hash/chốt cũ.
- [x] Permanent RED trên mã chưa sửa: 11 test chưa đạt vì thiếu bộ chữ/bố cục mới, exit1; không lỗi import/setup.
- [x] Native BASE hữu hạn VI375/draft thấy đúng bốn ô và dòng chữ cũ, dữ liệu/nguồn/tiến trình giữ nguyên, `EXPECTED_FIRST_DRAFT_REQUEST_RED`, exit0, owned Jobs0.
- [x] Áp sáu thay thế và hai rule prerequisite có neo duy nhất; đủ hash nguồn đích và 29 khóa.
- [x] Một lượt GREEN theo nhóm:461Node/9Python; prerequisite17affectedPASS, cú pháp/diffcheck đạt.
- [x] Native GREEN R2: VI/EN/ZH × hai cỡ × bốn trạng thái =24 quan sát duy nhất/13 ảnh; bảy trạng thái yêu cầu chỉ là metadata QA đã lưu, không phải đầu ra thật.
- [x] Source review độc lập C0/I0/M0; tài liệu hiện tại/gốc/Tester/cases đã cập nhật. Metadata32PASS và một lỗi quyền POSIX600 Windows cũ, không mới; Linux CI giữ nguyên.
- [ ] CI đúng HEAD, merge đúng cây nguồn, một deploy; đối chiếu revision/dịch vụ/nguồn và tệp công khai, ghi receipt cùng Issue689/PR.

## Bằng chứng bắt buộc và giới hạn

QA riêng thêm đúng 21 yêu cầu và 21 tin nhắn `role=user` giả để thỏa khóa ngoại; không có assistant/run-event, không POST yêu cầu sản phẩm hoặc gọi dịch vụ trả phí. Đối chiếu tám bảng, schema, source/evidence, sáu plan/18 scene và owned Jobs về 0. Các DTO sai/quyền bị từ chối/trạng thái đọc khác/50+ hàng chỉ kiểm bằng VM; không giả bootstrap hay phản hồi API ở native.

Lệnh mục tiêu: `node --test tests/chat-request-panel.test.mjs` → trước sửa RED đúng phần thiếu; sau sửa 11 test đạt. Nhóm hồi quy và native được ghi vào báo cáo sau kết quả thực tế; không bịa số PASS.

PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_WRITES=0.
MERGED != DEPLOYED != LIVE. Kiểm tra giao diện không chứng minh trả lời tự động hoặc âm thanh cuối.

## Prerequisite phát hiện khi kiểm thật: CHAT-REQUEST-STATUS-WRAP R1

Nhóm 20 tệp Node đạt 461/461; Python 9/9. Native ZH đạt tám quan sát.
VI/EN dừng đúng quan sát375/draft vì giới hạn cũ `em:not(:empty)`86px
cắt chữ: VI cần147/133px nhưng chỉ84px, EN cần101/112px nhưng chỉ84px.
Nguồn/dữ liệu/bằng chứng vẫn giữ và owned Jobs về0; các báo cáo fail được giữ.
Đây là thiếu phạm vi CSS của điều phối, không tính lỗi mã worker đã trả đúng sáu thay thế.

Chỉ mở thêm hai rule CSS trong `portal.css`: cho label/value xuống dòng,
không ellipsis/hide, value tối đa55% để dành chỗ cho nhãn; giữ màu/cỡ
chữ/flex/padding/gap/two-column/mobile-one-column và toàn bộ JS/wording.
Giao Antigravity R1 riêng; root không tự sửa app. Bộ test thêm đúng một
ca có RED trước CSS patch, phép chiếu chỉ chấp nhận cả hai rule đầy đủ;
mọi CSS khác vẫn phải bằng toàn nguồn baseline. Không chạy lại461 ca không đổi;
kiểm lại12 test mục tiêu/CSS và native ba locale bị CSS chung tác động.
