# AUTH-DRAFT-MUSIC-01 — kế hoạch kiểm thực

BASEcf94b23e; cùng nhánh auth-draft-isolation-20261128 và tracker Issue689.
Spec: `docs/superpowers/specs/2026-11-28-auth-draft-music-mounted.md`.

1. Khóa app source; giữ Voice proof không chạy lại. Công bố ba AC trước QA.
2. Tái dùng reviewed auth host/driver; chỉ thêm hai GET HTML Music ở hai
   allowlist. Helper riêng, không thay helper Voice đã đạt.
3. Đăng nhập A thật, kiểm authoring/control constraints và defaults; bridge
   guarded. Thiếu quyền phải ghi đúng, không giả response hoặc sửa ENV/app.
4. Chạy AC1→AC2→AC3 trong cùng context, không submit nội dung; thu network,
   DOM/identity/source hashes; luôn cleanup browser/server sở hữu.
5. Đánh giá nguyên nhân nếu FAIL; không tính lỗi harness vào worker. Nếu
   không lỗi app, chỉ bổ sung bằng chứng, không tạo bản vá app giả.
6. Gộp báo cáo QA theo campaign; refresh pin Tester trước source commit/
   provenance khi cập nhật tài liệu đã pin. Không mở issue/PR cạnh tranh.

Các sản phẩm khác, canonical race/error, signed EN/ZH, AX/device/Safari,
signed production/cache và motion vẫn riêng; motion làm cuối.
