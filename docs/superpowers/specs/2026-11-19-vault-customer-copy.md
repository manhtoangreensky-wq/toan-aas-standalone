# Kho tệp — chữ hiển thị và nội dung có mục đích

TASK=ASSET-VAULT-CUSTOMER-COPY-20261119.
BASE_SHA=5b11e63f178b4ff81c4546462a8cb3ddcdc99fb5.
TRACKER=Issue689/comment7011217772;DEPENDENCY=PR777_DELIVERED.

note rõ là chia plan chi tiết ra thành từng spec kèm theo kết quả cần đạt để qua spec khác, với spec đơn giản thì chạy nhiều spec một lúc, nếu spec phức tạp thì làm từng spec

## Phạm vi đã khóa

Chỉ `/asset-vault`: hai factory trường, phân trang, panel thông tin tệp,
các đoạn không giao nhau trong renderer chính và metadata đúng route.
Ba tệp ứng dụng: `portal.js`, `portal-i18n.js`, `copyfast_pages.py`.
Đúng 12 thay đổi, 90 khóa/270 giá trị VI/EN/ZH, 148/151 nguồn bảo vệ.
AmendmentVAULT-04C từnativefinding: thêm riêng1ruleCSSdarkhint, tổng4app/
13phép thay/147protected;copyauthoritybanđầugiữnguyên,CSSauthorityriêng.
Không đổi chữ ký shared helpers, API, auth, schema, ENV, tiền, provider,
engine, Bot, motion hoặc dữ liệu khách.

Giữ file input/name/id/required/accept, tên trường, giới hạn, mặc định,
draft, bộ lọc, UUID, offset, trạng thái, quyền strictboolean và mọi nút
upload/lưu trữ/khôi phục/tải/xem thông tin/làm mới/phân trang.
Không thực hiện những thao tác sản phẩm đó trong kiểm tra chỉ đọc.
Không dịch tên tệp, tên dự án, nội dung hoặc ngày giờ gốc của khách.

## Thiết kế có mục đích

Tên trang “Kho tệp”/“File library”/“文件库”. Giữ hướng dẫn lưu/tìm/quản lý
tệp bằng ngôn ngữ khách hàng. Bỏ intro/aside giải thích triển khai và
wrapper chia hai cột khi không còn aside; không khung trống.
Liên kết `/assets` vẫn ở điều hướng có sẵn; chỉ bỏ bản lặp trong aside.
Panel thông tin tệp là chức năng thật, không bỏ: trạng thái, lý do,
ngày, lần cập nhật, nơi sử dụng, số lượng cần giữ, nút đóng/khôi phục.

## Checklist và thứ tự

| Spec | Kết quả phải có | Bằng chứng | Phụ thuộc |
|---|---|---|---|
| VAULT-00/01 | OCR đã giao, đọc nguồn thật | Receipt PR777 + inventory | Không |
| VAULT-02F | Ô nhập/bộ lọc đủ ba ngôn ngữ | Hai factory, 12 khóa | 01 |
| VAULT-02C | Thẻ tệp/phân trang đúng nghĩa | Hai đoạn, 23 khóa | 01 |
| VAULT-02L | Thông tin/khôi phục đúng quyền | Một hàm, 38 khóa | 01 |
| VAULT-02M | Trang chính/metadata gọn | Sáu đoạn, 17 khóa | 01 |
| VAULT-03 | Bốn kết quả ghép chính xác | Schema/literal/151 nguồn, BASE RED | 02F/C/L/M |
| VAULT-04 | Không hồi quy, trình duyệt thực | Physical/source/shell/native | 03 |
| VAULT-05 | Tài liệu/Tester/review đủ | Manifest, báo cáo trước push | 04 |
| VAULT-06 | Một PR và triển khai ngay | Exact CI/tree/VPS/assets/receipt | 05 |
| VAULT-07 | Thông báo sau thao tác | Phạm vi riêng, không nhận từ renderer | Sau 06 |

Bốn worker chỉ trả JSON riêng; Root kiểm chung một lượt, áp dụng tuần tự.
Không sửa thay trước hai lỗi thật cùng đoạn; thiếu đặc tả/QA không tính
lỗi worker. R1 cả bốn đã đúng; các nguồn và bản đồ được đối chiếu công khai
trước gửi, không có test/fixture/API/đăng nhập/bí mật/dữ liệu khách.

## Giới hạn không được nhận nhầm

Main hiện không đọc `assetVaultReadState`; không bịa thêm màn tải/lỗi để
giống trang khác. Không có `renderNotes` trong renderer này. Tiêu đề đã có
một đường dịch shared, nhưng metadata đúng route vẫn cần để tránh fallback
generic. Không đổi factory shared để chữa một trang.

Physical BASE đã có trước áp dụng. NativeBASEsauđóđượctách từexactGitcommit
vàđốichiếuđủ2514trackedblobs/66745084bytestrướcsau,48nativeviewsBASE/current;
khôngsuyA/BtừVMhoặchoànnguyênmộtphầnruntime. Lỗi/unknowns/receiptđầugiữriêng.
Không suy từ cờ/form/metadata/HTTP200 ra tệp tải được hoặc engine sẵn sàng.
Thông báo thao tác trong integration, thiếu tên dự án trong shared factory,
khả năng tiếp cận toàn app, auth, thiết bị/Safari/signed production và đầu
ra thật giữ mở. Motion M-FINAL-01..06 cuối, toàn goal ACTIVE/incomplete.
