# Q0-UI-LABELS — bỏ ô nhãn thừa toàn WebApp

Owner yêu cầu ngày21/10: ẩn toàn bộ ô tương tự “Đang ở trang này” và “Chưa
thể tạo ảnh”, trên toàn WebApp chứ không riêng Image.

## CONTRACT

Thay đổi trình bày dùng chung trong `static/portal/portal-theme.css`; tests/
browser/evidence/docs. Không đổi dữ liệu, trạng thái, điều kiện CTA, capability,
quyền, API/auth, provider, ví, theme token hoặc motion.

## Kết quả

1. Các nhãn trang hiện tại/khả dụng/giới hạn và nhãn phụ ở nav, capability,
   read-state/install bị ẩn; không để lại pill bo tròn/chấm màu.
2. Trạng thái nghiệp vụ thật trong bảng, danh sách tác vụ và báo cáo vẫn có thể
   đọc như chữ thường, không nền/viền/bo tròn/padding kiểu ô nhãn.
3. Không ẩn nút chọn tài khoản, chip hành động, bộ lọc, tên/tag nội dung khách
   hoặc thông báo lỗi/cảnh báo và disabled reason cạnh nút.
4. Giữ `aria-current` và viền selected cho điều hướng; không bịa “sẵn sàng”.

## Checklist

- [x] RED: ảnh QA trước sửa có ô trạng thái trên Image và nav, signed RED5;
  CSS Admin gate còn radius9999px trước patch Antigravity.
- [x] GREEN: CSS dùng chung loại bỏ ô trên cả khách/Admin, locale/theme;
  Antigravity3.8Flash xuất patch lượt1; Codex áp dụng và kiểm CSS8/8.
- [x] Browser: label thừa hidden, trạng thái record còn plain text, action và
  cảnh báo vẫn hiện; không overflow hoặc lỗi; Image flow giữ nguyên.
- [ ] Regression/code review/metadata/docs/provenance/CI đúng HEAD.

Local evidence: fullNode891/891; signed customer120 states có0visual failures,
0UIwrite/external/overflow; Image24/24,0page/console/UIwrite/external. CSP60 ở
Tools Free là baseline: probe cùng môi trường baseline5/candidate5,0new; giữ
UT-CSP-EMPTY-THUMB ở Utilities, không nới CSP. Delivery theo coherent wave sau
khi Image WIP qua gate. Không khai toàn app sạch console hoặc production LIVE.

Đây là yêu cầu mới thêm vào wave Image đang dở, không mở engine hoặc motion.
