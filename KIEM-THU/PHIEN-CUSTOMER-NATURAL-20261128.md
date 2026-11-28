# Phiên rà lời tài khoản, bắt đầu sử dụng và dự án

ID=CUSTOMER-NATURAL-20261128; product=standalone WebApp;
repo=manhtoangreensky-wq/toan-aas-standalone; Issue689;
branch=codex/customer-natural-followup-20261128;
BASE=469f70063217814522b674272185227d93c8a08c.

## Phạm vi khóa

Hai tệp ứng dụng:413giá trị khóa sẵn có trong portal-i18n.js,không thêm
khóa;đúng một nhãn viết tắt trong portal.js dùng khóa xác thực hai bước
đã có. Tổng1239giá trị đề xuất;thực sự đổi406VI,331EN,340ZH. Những
khóa không đổi vẫn giữ trong bảng đối chiếu để bảo vệ phạm vi.

Antigravity4ExtraHigh chỉ trả đề xuất trong thư mục riêng;Root kiểm và
ghép đúng record,không tự viết logic ứng dụng. Giữ tên/giá trị trường,
nút,đường dẫn,quyền,trạng thái,tham số,lệnh thật và nội dung khách.
Không đổi xác thực,ví,thanh toán,Bot,engine,ENV,dữ liệu thật hoặc motion.

## Bằng chứng tại máy

| Case | Kết quả và giới hạn |
|---|---|
| CN-WORDING |134đề mục raw primary có kết quả đạt trong ledger cuối của lượt gộp và recovery đúng phần ảnh hưởng;không cộng số trùng,không gọi đó là một lần fullsuite mới |
| CN-CONTROLS |Cùng renderer thật:normalized data,tên/giá trị/giới hạn/quyền/nút/lệnh giữ;chữ khách cóQA/Studiođược giữ nguyên và escape |
| CN-CODE-GUIDANCE |Mã liên kết thực sự hiển thị và lệnh sao chép giữ nguyên;8mã khôi phục mẫu vẫn hiển thị;không còn cam kết sai về việc gửi Telegram/ẩn mọi mã |
| CN-HISTORY |595ca lịch sử đạt ở lượt gộp;7ca inverse mới đạt lại sau ghép cuối,chỉ bóc đúng2record/413giá trị;fixture/pin/assertion cũ giữ |
| CN-PYTHON |Nhóm44ban đầu35đạt/9lỗi đọc chữ cũ;4readerđược bóc đúng đầu vào,18ca liên quan đạt ở nguồn cuối;không cộng35+18thành tổng riêng |
| CN-BROWSER |36lượt native đúng khung/sáng-tối/VI-EN-ZH/390-1440 đạt,0lỗi/tràn/kết nối ngoài;2ảnh đầu trang đã sửa cuộn và xem lại |
| CN-DELIVERY |Chưa phát hành;chỉ tick sau đúng bản kiểm,gộp,cập nhật máy chủ,đối chiếu tài nguyên và biên nhận |

Reviewer độc lập đọc361bộ câu và chỉ ra đúng12câu cần chỉnh;Root giao
lại đúng12câu và kiểm phần ảnh hưởng. Những41khóaBot/IDvà10câu bổ
sung được tìm bằng đường hiển thị thật/quét cuối;requestSummary giữ
lịch sử lượt1và sửa lượt2,không reset. Thiếu phạm vi hoặc lỗi công cụ
kiểm tra củaRoot không tính thành lỗi worker.

Rà failed-only cuối đọc12câu đã sửa,51câu bổ sung và2câu hướng dẫn
khôi phục;hai helper lịch sử và các neo đầu vào cũng được đọc. Kết quả
APPROVE,không cófinding mới;không chạy lại tests ở reviewer. Haiảnh
đầu trang đạt theo recovery1VI390+1EN1440,đã xem và giữ đủ tiêu đề;
không dùng ảnh bịcuộn dưới header làm bằng chứng đầu trang.

Metadata67tệp đã đo lại;32ca đạt và1ca quyền tệpPOSIXkhácWindows
giữ đúng lỗi nền đã đo trước. Filetest/scriptđồng bộ không đổi;không
bỏ assertion hoặc sửa quyền máy. LinuxCIvẫn phải qua ca này trước gộp.
Runtimei18nbundlecũ failed-only1/1đạt sau neo sourcequa inverse/stdin.

Lượt kho46134749159/HEAD85792714dừng49/50đạt ở đối chiếu từ điển
tài liệu cũ. Chỉ phép so giá trị của test đó nhận snapshotđã bóc đúng
413khóa;renderer/transportvẫn đọc raw hiện tại. Failed-only1/1đạt.
Không đổi hai tệpứngdụng,fixture/pin/assertioncũ hoặc rawprimarymới.

## Giới hạn và mục còn mở

Ảnh chỉ renderer/kiểu dáng vật lý quaHTTP cục bộ và điều khiển native;
không phải phiên khách trên production hoặc bằng chứng gửi/lưu thật.
Lượt đầu trình duyệt bị môi trường chặn;lượt sau chọn nhầm vùng ẩn;
lượt36ảnh còn thiếu lớpportal-shell,nên không dùng làm bằng chứng
tương phản. Chỉ sửa công cụ kiểm tra,không sửa CSS ứng dụng.

Màn hình ngôn ngữ riêng,ghi chú mặc định,tên giá trị máy nhưgradient
nếu có đường hiển thị thật,bản nháp/lifecycle/race,AX,thiết bị/Safari,
offline và phiên production còn mở. Motion giữ bước cuối. Không suy
toàn giao diện sạch hoặc toàn goal hoàn thành từ riêng đợt chữ này.

Một số câu/nhãn cũ còn chữWebtrong đầu trang tài khoản vàthiết lập
chưa thuộc danh sách413khóa;đã ghi cho đợt tiếp theo,không gọi đợt
này là rà sạch mọi từ trên toànứng dụng. Không xóa tên riêng hoặc
giá trị do khách/máy chủ trả về bằng thay chuỗi chung trên toànHTML.

PROVIDER_CALLS=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_WRITES=0.
