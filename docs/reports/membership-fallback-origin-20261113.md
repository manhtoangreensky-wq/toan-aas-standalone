# Hội viên: nhãn gói và nguồn ghi chú

BASE: `78dc73c847a8bcf28a76bc34f00b1ae32003ac9a`, sau PR #724.
Tracker duy nhất: Issue #689, kho WebApp standalone.

## Hành vi và phạm vi

Nhãn loại gói mặc định dùng khóa dịch sẵn có ở Việt/Anh/Trung. Khi dòng gói
gốc không có ghi chú hợp lệ, thẻ không tạo đoạn mô tả thay thế hoặc đoạn
rỗng. Khi nguồn có ghi chú, nội dung đã chuẩn hóa và escape vẫn giữ nguyên,
kể cả câu trùng nguyên văn giá trị thay thế cũ hoặc có từ kỹ thuật.

Formatter riêng Hội viên xác định nguồn từ dòng hợp lệ đầu tiên theo code
và nhãn đã chuẩn hóa, đúng thứ tự monthly rồi combos và giới hạn 100 dòng
mỗi nguồn. Dòng sai hoặc trùng không được cho dòng trước mượn ghi chú.
Không đổi bộ chuẩn hóa dùng chung, không khôi phục trường đã bị projection
bỏ. Giá, quyền, trạng thái, số dư 0, liên kết, API/auth/tiền/provider/Bot và
motion đều ngoài phạm vi. Chỉ hai đoạn trong `portal.js` thay đổi.

## Kết quả local ngày 13/11/2026

- 60 ca chạy renderer thật: baseline 12 đạt/48 lỗi đúng triệu chứng, sau sửa
  60 đạt. Có thiếu/rỗng/không hợp lệ, ghi chú thật/escape/legacy, trùng dòng,
  nhãn về code, giới hạn nguồn và biên 240 ký tự.
- Nhóm hồi quy 240/240 ca Node đạt, đã gồm 60 ca trên; không cộng trùng.
  Hai bài so HTML lịch sử chỉ nhận ba nhãn loại gói được duyệt trong đúng
  phần tử; không bỏ tùy ý chữ hoặc cập nhật toàn bộ golden hash.
- Cú pháp JavaScript và biên dịch `app.py`/`copyfast_pages.py` đạt.
  Nhóm Python 51 đạt/1 lỗi quyền tệp POSIX trên Windows; cùng ca của BASE
  lỗi y hệt (0666 thay vì 0600). Không sửa hoặc bỏ ca này; CI Linux kiểm riêng.
- So nguồn: đảo đúng hai thay đổi về BASE khớp mọi byte còn lại của bundle;
  18 tệp bảo vệ khác không đổi. Không sửa i18n/CSS/integration/backend.

Component QA dùng renderer và CSS thật với nguồn tổng hợp ở 12 tổ hợp
Việt/Anh/Trung ×390/1440×sáng/tối. Có gói thiếu ghi chú, ghi chú trùng câu cũ,
ghi chú kỹ thuật thật và chuỗi giống script; không có paragraph rỗng, script
thực thi, tràn ngang hoặc lỗi trình duyệt. Ảnh component cuối dùng khung shell
gốc; lượt chụp thiếu khung trước đó không dùng để kết luận màu của trang.
Đây không phải phản hồi API hay chứng minh danh mục production.

Kiểm tra riêng app thật có đăng nhập trong localhost: 12 lượt xem, 3 lượt rời
trang, 240 mẫu callout/nút/liên kết có tỷ lệ thấp nhất 5,216649621048673:1.
Không lỗi trang/console/tràn ngang, không ghi kế hoạch hoặc gọi ngoài. Sáu
kế hoạch, 18 cảnh và lịch sử bản sao QA giữ nguyên; bằng chứng gốc không bị
ghi. Đăng nhập chỉ dùng tài khoản QA giả, không khẳng định toàn bộ byte của
DB sao chép không đổi sau tạo phiên. 19 tiến trình sở hữu được dọn về 0.

## Giao hàng và giới hạn

Phiên Tester và nguồn case đã cập nhật trước push. CI đúng HEAD, merge, deploy
đúng SHA, dịch vụ/runtime/assets và receipt được ghi riêng trong Issue #689
và PR của đợt này; local PASS không thay các cổng giao hàng đó.
Không đóng locale/clutter toàn app, thiết bị/Safari, signed production,
provider output hoặc M-FINAL-01..06. Motion vẫn làm cuối theo checklist mẹ.
