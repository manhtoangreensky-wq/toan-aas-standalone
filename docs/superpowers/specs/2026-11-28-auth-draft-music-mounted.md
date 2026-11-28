# AUTH-DRAFT-MUSIC-01 — bản nháp Âm nhạc trong phiên thật

Đang đọc và áp dụng skill owner-governed-codex cho task này.

BASE=`cf94b23e6a26010e88ebcd33b36623204c784c9a`;
branch `codex/auth-draft-isolation-20261128`; Issue #689.
AUTH-RETURN PR821 đã giao; ba acceptance Voice đã đạt local tại comment7227137073.
Không chạy lại nhóm Voice hoặc mở sửa ứng dụng khi chưa có lỗi thực nghiệm.

## Phạm vi và cổng

Actual FastAPI/shell/renderer/integration trên SQLite/asset tạm, fake secret
child-only; VI390×844, query `lang=vi&theme=dark`. Không sửa ENV thật,
backend/auth/session/CSRF, schema, ví/PayOS, Bot/engine/provider hoặc motion.
Không application edit trong phiếu QA này. Không bấm Save/Estimate/Confirm.

Chỉ thêm hai GET HTML `/music/create`, `/music/song` vào cả server/browser
allowlist của host auth QA đã kiểm. POST vẫn chỉ register/login/logout.
Bridge phải thật sự guarded; khả năng soạn draft phải do máy chủ/catalog cấp.
Không bơm bootstrap/capability, không force enabled, không tạo nhạc/quote/job.

## Checklist nghiệm thu

- [x] READ: hai route và tab background/song; field/options và session Map thật.
- [x] AC1: A nhập mô tả/thiết lập nhạc nền và bài hát riêng; lời bài hát có
  xuống dòng. Đổi tab, Back/Forward phục hồi đúng từng bộ; URL/form/current
  tab đồng bộ, không document reload khi đổi tab; giữ lang/theme đã chọn.
- [x] AC2: reload thật cùng cookie/context; A vẫn đăng nhập; hai draft chưa
  lưu rỗng và mọi trường về mặc định thực đã ghi trước khi nhập.
- [x] AC3: nhập lại A, UI logout/confirm/POST→auth/me401→login B cùng context.
  Không identity/draft A; B nhập draft mới và phục hồi riêng khi đổi tab.
- [x] Sentinel không có trong localStorage/sessionStorage; không POST ngoài
  auth, không provider/engine/upload/job/payment; dừng sạch process sở hữu.
- [x] Có network/DOM/identity/source evidence; không lấy unit tests hoặc ảnh
  chuyển khung thay cho native acceptance.

Fixture chỉ chọn giá trị có trong control thật:
background brief/tier/mode/duration; song thêm lyrics/vocal_mode/
song_length_mode. Duration phải hợp min1/max600/step1; không ép nhập trường
đang disabled. Ghi defaults thực; không suy từ placeholder hoặc source string.
Một context A→B, tối đa ba login attempts; không nới throttle.

## Điều kiện kết thúc

Root kiểm artifact và protected hashes. Lỗi QA/spec sửa ở harness, không sửa
app để chiều fixture. Chỉ khi có application RED mới giao Antigravity4ExtraHigh
đúng hàm, tối đa hai lượt cùng acceptance trước root takeover.

Đây là RAM draft chưa lưu; không phải draft server, tạo nhạc, canonical
race/error, signed production, full locale/AX/device/Safari/offline/motion proof.
WHOLE_GOAL_COMPLETE=NO;motion cuối;PROVIDER_CALLS=0;WALLET_MUTATIONS=0;
PRODUCTION_DATA_WRITES=0.

## Kết quả actual mounted 28/11/2026

Lượt `auth-mounted-tIzOyd/summary.json` PASS ngay lần đầu: ba AC, một
luồng VI390×844/querydark, bốn PNG; 0console/pageerror/unknownrequest,
server exit0. Runtime hashes/HEAD giữ nguyên, không application edit.

Giá trị DOM thật: nhạc nền premium/background/30 giây; bài hát standard/
lyrics/duet/seconds/45 giây, lời gốc có newline và Unicode. Hai bộ phục
hồi riêng qua tab/lịch sử; lang=vi/theme=dark giữ. Reload về defaults
thật (brief/tier/duration rỗng); B chỉ phục hồi brief B, không còn dữ liệu A.
Không xóa cookie/storage thủ công. POST chỉ register2/login3/logout1;
bridge=false, authoring capability thực=true; không canonical/provider call.

Ảnh đã đợi các animation hữu hạn kết thúc và cuộn tới form; có ảnh trường
mô tả A và B thực. Không dùng ảnh này để đóng contrast/AX/motion toàn trang.
Nhóm Voice không chạy lại. Signed EN/ZH, sản phẩm khác, server-saved draft,
canonical race/error và production vẫn chưa được chứng minh bằng ca này.
