# Chi tiết âm thanh — bản sửa chữ và nhãn

TASK=MEDIA-DETAIL-CUSTOMER-COPY-20261121.
BASE=051b936695638a5f083396194730861dc7831da1.
BRANCH=codex/media-detail-customer-copy-20261121.
TRACKER=Issue689/comment7058931880.
STATUS=LOCAL_GATES_ACCEPTED_RELEASE_PENDING.

Đang đọc và áp dụng skill owner-governed-codex cho task này.

## Thay đổi khách nhìn thấy

Phân trang tệp âm thanh dùng đúng VI/EN/ZH. Chữ trang chi tiết được
viết gọn; bỏ ba lời giải thích lặp và một khung chỉ mô tả cơ chế.
Giữ nguyên các biểu mẫu, nút, liên kết tải, quyền sử dụng, lịch sử,
dự án, tệp, gợi ý văn bản và bước mở công cụ. Không hứa tạo âm thanh
từ chức năng chỉ soạn gợi ý. Tên/nội dung khách đã lưu giữ nguyên.

Form thêm tệp có namespace riêng cho bảy nhãn/ID/help; không đổi tên
trường, giá trị, UUID, action hoặc payload. Năm rule màu chỉ áp dụng
đúng vùng đã đo. Không thay token, bố cục, chuyển động hay shared
factory. integration.js/backend/auth/storage/Bot/engine/provider/
wallet/PayOS không thay đổi.

Năm proposal từ CLI Antigravity hiện có, model gemini-3.8-flash-high,
output-only/full MAP: 3/43/4/2/1 records. Root review/replay tuần tự.
53 records trong ba app files; 148 nguồn bảo vệ RAW/LF BASE-exact.
Worker codefailures=0; application takeover=false.
R1 schema bị từ chối trước generation là lỗi schema giao việc,
không phải worker codefail; các receipt false giữ nguyên.

## Kiểm tra và giới hạn

Phân trang 19 PASS. Copy+namespace ban đầu 33 PASS; sau finding review
về fixture gợi ý thiếu flags, chỉ sáu ca bị ảnh hưởng và một ca âm
được chạy lại: 7 PASS. Source/provenance final53 gate: 13 PASS.
Hồi quy nhóm 141 tệp: 4.361 PASS giữ nguyên; các lỗi golden/input cũ
được chuyển qua projector hữu hạn, không sửa fixture/golden cũ.
17 failed/changed/previously-unexecuted slices: 43 PASS, không cộng
thành tổng unique vì có retest và source gate đã chạy riêng.
Tester đã chốt bảng theo file+tên ca:4.565 unique PASS/0FAIL/0SKIP,
không phải một lượt chạy mới. Công thức4361−72duplicate+23recovered+
7actualunexecuted+246preserved=4565. Đúng149/149locale workflow files;
4.303 ca thuộc149owner và262ca từ bảy module import thêm. Báo cáo
độc lập nằm ở reports/tester/MEDIA-DETAIL-CUSTOMER-COPY-20261121.md.

Python historical hiện hành 48 PASS. Ba suite Portal liên quan:
11 PASS và bốn lỗi tái hiện đúng ID/assertion trên exact BASE bằng
public-source mirror; không nhận toàn bộ pytest xanh.

Native gồm VI/EN/ZH ×320 dark/1440 light, hai detail roots, bốn form
có dữ liệu thật trong DB tạm. Candidate R1: 384 controls/12 PNG mới,
0 nhãn lỗi/0 duplicate ID, 22 contrast FAIL và 18 QA-reader faults.
R2 chỉ đo 30 control pieces cần thiết, giữ 354; ba PNG mới giữ chín,
21/22 known contrast recoveries PASS. R3 chỉ một root/checkbox:
ratio 12.351554732138213, actual cover absolute clip rect zero-area.
22 recoveries=21 retained+1 fresh, không suy từ ảnh hoặc source.

12 required-label checks được đối chiếu offline bằng actual R2
text = fixed prefix + một khoảng trắng + hậu tố chính xác VI
“Bắt buộc”/EN “Required”/ZH “必填”, cùng required=true và label.control.
Không xóa nhãn hỗ trợ tiếp cận để làm phép so chuỗi đạt.
R3 exit0/11.668s; 383 retained+1 fresh=384 distinct; 11 retained+
1 new fully decoded PNG=12 ảnh coverage, không phải12ảnh mới.

Nguồn151/current53, code, schema, product core, audit3login/không
row lạ, egress0 và owned processes0 được giữ. Không product POST,
blob, download, playback hoặc provider. 163 unknown paint trước
đó và bốn unknown khác ở R2 vẫn NOT_CLAIMED; không nhận global AX,
contrast, keyboard, Safari/device hoặc signed production UI đạt.

## Giao hàng và phần tiếp theo

Spec/checklist/ops/crosswalk/tám case Tester/audit/manifest phải khớp.
Chỉ một PR; exact HEAD CI và artifacts được kiểm riêng, sau đó
merge-tree/exclusive deploy/VPS revision/services/public+versioned
assets/build và receipt đọc lại. Trạng thái phát hành chưa được
suy từ local PASS. Không đọc hoặc công bố tám state files.

Đơn vị kế tiếp ngay sau visible release là MDCC-FIXED-COPY:
validation/write/handoff feedback. Shared producer/classifier cần
contract/comparator riêng, nên không được nhận đã xong trong đơn vị
hiện tại. Whole goal vẫn ACTIVE; motion M-FINAL01..06 làm cuối.

PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_MUTATIONS=0.
DEPLOY=NO_AT_THIS_REPORT_SNAPSHOT.
LIVE_PASS=NOT_TESTED_SIGNED_PRODUCTION_UI_OR_AUDIO_OUTPUT.
