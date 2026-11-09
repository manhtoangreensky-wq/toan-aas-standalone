# Cỡ chữ biểu mẫu Voice — 09/11/2026

SPEC_ID=VOICE-MOBILE-INPUT-16-001
BASE_SHA=bd6f947f033943ea670d1b1774cd8e459f2bfb37
SOURCE_SHA=a6cdc5fb69203174e0ff3793748bdbc04968435a

## Kết quả đúng phạm vi

Năm dòng CSS đặt cỡ chữ ô nhập Voice thành16px khi viewport không quá620px.
Selector chỉ áp dụng lớp biểu mẫu Voice hiện có; không đổi máy tính, màu, bố cục,
motion, chữ, giá trị form, quyền, API, Bot, provider, ví hoặc dữ liệu production.

Native QA trước sửa đã xác minh tài liệu mới sau reload và lifecycle kết thúc:
TTS có60 quan sát field15px ở12cấu hình điện thoại320/414. Đây là RED thực,
khác những kích thước43,9px tạm thời do entrance animation đang chạy.

Sau patch worker:120cấu hình của TTS/STT/Clone/Saved/Outputs, ba ngôn ngữ,
hai theme,320/414/1024/1440px; không tràn ngang, không lỗi trang/kết nối ngoài
hoặc action sản phẩm. Ô nhập mobile đạt16px. Cỡ chữ desktop của từng field TTS
khớp baseline (không giả định mọi role đều15px). Full Node1880/1880; review độc lập
0Critical/0Important. Chỉ một property CSS thay đổi.

[Bằng chứng120cấu hình](../../reports/ui-qa/voice-mobile-20261109/readability.json)
ghi rõ capture từ BASE+CSS patch; tám hash UTF-8/LF runtime đã được đối chiếu
độc lập với Git blob của SOURCE_SHA, không gán nhầm capture cũ thành commit mới.
Các file raw, DB, credential/phiên/login/API response và đường dẫn máy không công bố.

## Chốt còn mở

Dòng native summary hướng dẫn Clone vẫn cao24px ở12cấu hình mobile.
Đây là lỗi vùng bấm riêng VOICE-CLONE-TOUCH-001; bản font không thay đổi summary,
không tự gộp hoặc tuyên bố đóng bằng chứng touch toàn app.

Whole-app locale/AX, keyboard tương tác, contrast/body typography, auth first-paint
và CLS/LCP/INP vẫn theo R218; không thu hẹp goal còn hai cổng production/device.
PWA cũ đã chạy7/7 khi dùng quyền chạy cục bộ phù hợp; stack treo trước đó không
đủ để kết luận lỗi Python/AnyIO.

CI, merge/deploy/runtime và signed production của đơn vị này được cập nhật ở
[Issue689](https://github.com/manhtoangreensky-wq/toan-aas-standalone/issues/689).
Hiện tại đây là bằng chứng QA nguồn, không phải signed production LIVE.
