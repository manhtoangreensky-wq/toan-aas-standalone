# Phiên DOCUMENT-REFRESH / CHAT-LABELS — 14/11/2026

BASE `3477d0d83cb88d96941f5790f642cceb285463d9`, Issue #689.
Phiên kiểm thử này không thay48 case P0 lịch sử hoặc sổ theo dõi chính.

|Mã|Điều kiện nghiệm thu|Bằng chứng|
|---|---|---|
|DCL-READ|Lỗi đọc không báo thành công; rỗng hợp lệ được báo cập nhật|42 ca real handler/loader, VI/EN/ZH|
|DCL-CURRENT|Đổi trang/phiên/yêu cầu/đăng xuất không nhận thông báo cũ|24 ca phản hồi cũ trong42 ca|
|DCL-GUARD|Sai trang/thiếu quyền không gửi yêu cầu|6 ca guard trong42 ca|
|DCL-COPY|Chỉ4 khóa/12 giá trị, giữ tất cả chữ cũ/khóa lạ|Adapter exact hash,3 ca mutation mới|
|DCL-LABEL|Chữ nhãn Hội thoại sáng rõ hơn; tối không đổi|6 view/66 nhãn,8.64385:1 sáng/11.52797:1 tối|
|DCL-DOC-NATIVE|Lỗi rồi GET thực phục hồi mới báo cập nhật|12 state,6 failed/6 success,24 deliberate abort|
|DCL-SCOPE|Chỉ3 đoạn worker/3 tệp ứng dụng,16 tệp khóa giữ|Exact replay3/3,review C0/I0/M0|
|DCL-SAFETY|Không ghi sản phẩm/tiền/provider/production|QA6plan18scene giữ,owned13+20→0|
|DCL-DELIVERY|Provenance/exactCI/merge/deploy/runtime/assets tách riêng|Receipt trên cùng Issue #689/PR|

43 RED →43 PASS;224 affected và41 historical PASS, nhóm có thể chồng lấn.
Python45 PASS/1 CSS-tail BASE failure,3 locale/auth PASS riêng.
Lượt auth trong phiên giới hạn chưa kết thúc không bị ghi PASS; chỉ nhóm
chưa kết thúc chạy lại trong QA được phép. Không đổi auth hay bỏ test lỗi.

Chưa có signed-native Chat detail riêng; route selector/renderer được kiểm,
toàn device/Safari/AX/motion/production final-output không nằm trong PASS này.
