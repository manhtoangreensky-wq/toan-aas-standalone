# Kho tệp — phản hồi thao tác và ngôn ngữ

TASK=VAULT-ACTION-FEEDBACK-20261120.
BASE_SHA=e49427e5e35378c0fc8b41d68b772af88501f556.
TRACKER=Issue689/comment7019553829.
Ứng viên đang nghiệm thu; chưa tạo PR hoặc triển khai đợt này.

## Hợp đồng

Chỉ sửa thông báo ở hai tệp JS. Không đổi loader DTO, counter, session,
route, lựa chọn, quyền, API, backend, engine/Bot, ví/PayOS, ENV, dữ liệu,
CSS/bố cục hoặc motion. Bốn phiên Antigravity3.8FlashHigh R1 trả đề xuất
đúng toàn bộ34record/36vị trí. Root ghép tuần tự; không tự sửa ứng dụng.
Fixture bất biến `tests/fixtures/vault-action-feedback-reviewed.json`,
SHA488924a1ee5bcd7b49b53a4a366ba6a4e31f4df2eca0e518af8af9163e9c4801.
Có35key/105giá trị VI/EN/ZH;149nguồn ứng dụng ngoài hai tệp giữ nguyên.

## Acceptance và thứ tự

1. V07-R: refresh/filter/clear/page chỉ báo thành công khi lượt đọc còn
   hiện tại và `ready`; danh sách rỗng hợp lệ vẫn thành công. Lượt lỗi
   hiện tại báo lỗi; đổi trang/phiên/lượt mới hơn im lặng. Refresh có lựa
   chọn đòi cả danh sách lẫn thông tin tệp cùng lượt và cùng lựa chọn.
2. V07-RC: kiểm tra đầu vào/quyền/trang và thông báo xem thông tin tệp
   đúng locale, không câu giải thích triển khai. Giữ cùng điều kiện chặn.
3. V07-WC: đầu vào/chờ/thành công của upload/archive/restore đúng locale.
   Chỉ dịch ba câu thành công cố định đọc từ `copyfast_assets.py`, hoặc
   fallback falsy như trước. Giá trị truthy khác đi nguyên vào toast;
   renderer vẫn trim ngoài như trước. Phản hồi HTTP/envelope lỗi không
   được đi vào success. Giữ key/revision/ack/discard/finally/busy.
4. V07-L: helper scoped và catalogue35key đủ ba locale, không key trùng;
   missing/empty translator dùng fallback VI; hiển thị qua textContent.
5. Regression: leaf hữu hạn chỉ trên comparator lịch sử. Mọi golden/hash/
   assertion/negative cũ giữ; test acceptance mới đọc nguồn vật lý đầy đủ.
6. Native: thao tác GET thật trên FastAPI/SQLite tạm, Chrome localhost,
   ba locale ×320dark/1440light. Đại diện trước, phần còn lại sau. Không
   product write/blob/provider/wallet hoặc production-data claim.
7. Phát hành: review/tài liệu/Tester sẵn sàng → một PR → CI đúng HEAD →
   merge đúng bản → deploy → VPS/asset/receipt. Không giữ PR rỗng.

## Bằng chứng hiện có

Nhóm đọc253:BASE3PASS250RED; chữ đọc52:BASE16PASS36RED; thao tác ghi124:
BASE31PASS93RED. Bộ portable giữ nguyên byte assertion/fixture/exposure
sau đúng import/root normalization,7/7đối chiếu. GREEN chung429/429,0FAIL
trên nguồn ứng dụng thật trong VM;0mạng thật/provider/ví/dữ liệu thật.
Không cộng bộ đại diện hoặc các nhóm hành vi thành nghiệm thu toàn UI.

Ba gate source lịch sử đã RED sau ứng viên mới (hai bootstrap catalogue,
một pin integration); đây là input comparator cũ, không rollback app.
Native, affected regression và review nay có bằng chứng riêng, không lấy
từ VM:5000Node executablePASS/1externalBotbootstrapBASE-equivalent,
Python90PASS17sameBASEFAIL/31locale-shellPASS,6view30PNGCRCdecoded,
24intentionalabort/0unexpectedconsole,40owned→0. Release còn gate riêng.

## Giới hạn giữ mở

Không chứng minh signed production UI, upload/archive/restore/download
thật, blob hợp lệ, đầu ra engine, thiết bị/Safari hay toàn bộ accessibility.
Fallback tên dự án dùng chung thuộc scope sau; M-FINAL01..06 vẫn cuối.
