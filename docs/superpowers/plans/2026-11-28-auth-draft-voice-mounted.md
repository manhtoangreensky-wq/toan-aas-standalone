# Kế hoạch AUTH-DRAFT-VOICE-01

BASE `cf94b23e6a26010e88ebcd33b36623204c784c9a`;
branch `codex/auth-draft-isolation-20261128`; tracker Issue #689.
Spec: `docs/superpowers/specs/2026-11-28-auth-draft-voice-mounted.md`.

note rõ là chia plan chi tiết ra thành từng spec kèm theo kết quả cần đạt để
qua spec khác, với spec đơn giản thì chạy nhiều spec một lúc, nếu spec phức
tạp thì làm từng spec.

1. READ/CONTRACT: giữ receipt PR821 và source BASE; đối chiếu form scalar,
   điều kiện authoring, draft Map/session, tab/history và UI logout.
   Khóa toàn bộ app code; viết checklist ba AC trước QA.
2. QA preparation: tái dùng host/auth harness đã đọc; thêm đúng hai GET
   HTML ở cả cổng mạng. Ghi source/helper hashes, child-only fake settings,
   SQLite/assets tạm; không sửa môi trường máy hoặc đọc `.env`.
3. Preflight actual DOM: đăng nhập A thật; kiểm khả năng chỉnh form và
   type/options/range. Thiếu capability thì ghi thật, không force enabled.
4. VERIFY AC1→AC2→AC3 theo thứ tự trong cùng context; không submit nội dung.
   Thu network/DOM/identity/ảnh; luôn dừng sạch tiến trình sở hữu.
5. REVIEW: source diff/runtime hashes giữ; classifier tách lỗi harness,
   thiếu spec và lỗi ứng dụng. Nếu lỗi app, mới mở phiếu Antigravity đúng
   acceptance; không tự sửa ứng dụng trước hai lần worker sai.
6. REPORT: ánh xạ từng AC với evidence, không cộng proof UI đơn lẻ thành
   full auth/draft/AX/device/Safari/motion. Nếu không có app bug, không tạo
   bản sửa app giả để có PR. Gộp báo cáo QA theo quy trình hiện có.

Khi cập nhật case/tài liệu đã pin: đo lại Tester metadata trước commit
nguồn, rồi mới Web-only provenance/CI. Không lặp thiếu sót metadata CI-1.
Không tự mở provider/engine/Bot/ví/PayOS/ENV/schema/production data.
