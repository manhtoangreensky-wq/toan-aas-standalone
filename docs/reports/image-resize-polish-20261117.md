# Đổi kích thước ảnh — tiêu đề, độ rõ chữ và bỏ khối giải thích dư

SPEC_ID=IMAGE-RESIZE-POLISH-20261117; tracker Issue689.
BASE_SHA=93b41f523f2811b8934a61e4b4db8681572ad14c, PR757 đã giao.
Branch=codex/image-resize-polish-20261117.

Ba proposal Antigravity Gemini3.8FlashHigh R1 đã trả đúng trước đợt này:
metadata năm thay thế, hai màu chữ sáng trong một thay thế, xóa nguyên
section notice/notes cuối trang trong một thay thế. Replay tuần tự đúng
bảy thay thế ở bốn tệp ứng dụng; không tự viết bản sửa ứng dụng khác.

## Kết quả quan sát được

- VI/EN/ZH có tiêu đề/mô tả riêng cho `/image/resize` ngay từ HTML đầu,
  bootstrap, tiêu đề trình duyệt, header và hero.
- Bỏ toàn bộ khối giải thích Bot/provider/ví/PayOS/webhook cuối trang,
  không để section rỗng; lịch sử vẫn là phần cuối.
- Nhãn và hướng dẫn sáng dùng hai màu semantic có sẵn.30mẫu thực tế trước
  sửa1.2653297845–2.0211528715:1, sau sửa5.7970987340–12.3515547321:1.
-30mẫu tối giữ nguyên5.5224777212–11.5279743059:1;30cặp điều khiển và
  60cặp nhãn/hướng dẫn giữ chữ, font và hình học tương đối trong field.
- Mỗi native phase có sáu ca VI/EN/ZH×375sáng/1440tối; mỗi trang nhận đúng
  một GET ảnh theo loại với hai item thật của tài khoản QA mới, chọn ảnh,
  nhập1080×1920 và Tab đến chiều cao. Không submit sản phẩm.

## Kiểm tra đã chạy — không lặp nhóm đã đạt

- Client RED chuẩn bị: chín ca lỗi đúng mục tiêu,1287.7261ms, giữ nguyên
  bằng chứng vì ứng dụng BASE cùng byte; không chạy lại.
- Server RED thật: sáu ca lỗi đúng title/description,1.53s.
- Một lượt Node35tệp:679đạt/0lỗi/0bỏqua,115005.6486ms.
- Server GREEN:12ca Resize+Split đạt3.34s; chín ca Chat bảo vệ chạy riêng
  đạt2.32s. Không gọi đây là một lượt21ca.
- Native BASE và GREEN đều sáu ca, riêng môi trường mới mỗi phase:
  ba đăng ký/ba đăng nhập/twelve typed metadata/no blobs. Audit giữ đúng
  hash ba đăng ký cũ, chỉ thêm ba đăng nhập hợp lệ; toàn bộ dữ liệu/lược đồ
  sản phẩm khác giữ nguyên. Mỗi phase dọn22tiến trình sở hữu về0.
- Không lỗi trang/console/dialog, tràn ngang, yêu cầu ngoài hoặc ghi sản phẩm.
  Hai ảnh GREEN vùng field VI375sáng và first viewport EN1440tối đã được xem;
  không suy crop thành kiểm toàn bộ trang bằng mắt.
- So sánh dữ liệu native đầu tiên báo khác chuỗi border do currentColor.
  Cả hai là border `0px none` không vẽ; chỉ chuẩn hóa màu dẫn xuất khi nó
  bằng chính màu chữ, giữ độ rộng/style và mọi border nhìn thấy.
  Chạy lại duy nhất bộ so sánh dữ liệu đã lưu rồi đạt; không chạy lại native
  hoặc679ca. Đây là lỗi bộ so sánh, không phải lỗi worker/app.

## Review và giữ luồng cũ

Fixture khóa bảy literal pairs và SHA của ba proposal. New behavior thực thi
nguồn vật lý, không qua projection lịch sử. Bộ đọc kiểm tra cũ chỉ đảo hữu hạn
bảy thay đổi; giữ nguyên assertion/hash/key/order và guard integration thật.
Không bỏ test, nới timeout hoặc đổi kỳ vọng để bỏ qua lỗi hành vi.

Không đổi năm field, option native, form/action/route/CSRF/quyền, bộ tải,
lịch sử, tên tệp/nội dung khách, font/khoảng cách/chế độ tối/motion.
Không sửa backend ngoài hai entry dictionary shell.
CI chỉ thêm hai lệnh kiểm tra. Source scope proof được ghi riêng sau đối chiếu
toàn bộ Python cấp gốc, portal assets và templates với BASE.

REVIEW_CRITICAL=0; REVIEW_IMPORTANT=0; REVIEW_MINOR=0 cho diff ứng dụng.
WORKER_CODE_FAILURES=0; COORDINATOR_APPLICATION_REPAIRS=0.

## Phát hành và giới hạn

Tài liệu vận hành, đối chiếu chức năng và phiên Tester cập nhật trước push.
Exact HEAD/provenance/CI/merge/deploy/runtime/assets có receipt riêng;
ở mốc báo cáo này chưa nhận đã đưa ứng viên lên web.

Các chữ canvas/preset và câu kỹ thuật khác còn trong hàng đợi riêng;
proposal12dòng câu chữ Resize mới và metadata Nén PDF chưa áp dụng.
Không nhận wholelocale/AX/auth/device/Safari/signedUI/finalPNG/motion hoặc
kết nối Bot đã hoàn tất từ đơn vị này. Motion vẫn ở cuối goal.

PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_MUTATIONS=0.
ENV/auth/provider/engine/Bot/ví/PayOS giữ nguyên.
