# Yêu cầu và lịch sử yêu cầu dễ đọc — 15/11/2026

BASE `63ddccd5e34ee44590ff0493ba6a396d1e5cec2d`, nhánh
`codex/chat-request-panel-20261115`, Issue689.

## Hành vi thật trong phạm vi

Panel R1 và timeline R1 thêm29khóa/87giá trị VI/EN/ZH. Bỏ đúng hai ô
Bot/payment và Output/delivery; giữ hai trạng thái tiếp nhận yêu cầu và
trả lời tự động. Không làm tính năng chưa được bật trông như đã hoạt động.
Giữ form, xác nhận, ID/route/revision/state, quyền nghiêm ngặt, disabled,
bộ lọc hợp lệ/không có assistant/50hàng/thứ tự và timestamp gốc.
Nội dung khách và các thương hiệu không bị dịch/lọc.

Ba phiên Antigravity trả tám thay thế nguyên văn ở ba tệp ứng dụng:
panel3 + timeline3 + prerequisite CSS2. Không root tự viết lại app.
Panel có M1 ranh giới LF của điều phối, raw và phân xử giữ riêng;
không tính lỗi mã worker. Hai rule CSS sửa giới hạn86px và cho nhãn/giá trị
xuống dòng; giữ màu/cỡ chữ/pill/grid2cột desktop/mobile1cột và CSS ngoài phạm vi.

## Bằng chứng đã đo

- Permanent BASE11:0PASS/11RED, đúng phần chữ/bố cục thiếu.
- Một nhóm20tệp Node:461/461PASS; Python hợp đồng Chat9/9PASS;
  hai JS syntax, `py_compile app.py`, diffcheck exit0.
- Native R1: VI/EN375 phát hiện giá trị cần147/133 và101/112px nhưng chỉ84px,
  không bỏ qua báo cáo fail. ZH đạt tám trạng thái trên mã trước prerequisite.
- Thêm đúng một test wrapping:11PASS/1RED trước CSS; sau patch nhóm bị ảnh hưởng
  17/17PASS. Không chạy lại461ca không bị CSS tác động.
- Native R2: ba máy chủ QA riêng; VI/EN/ZH ×375sáng/1440tối ×bốn trạng thái
  =24quan sát duy nhất/13ảnh. Hai ô hiện đầy đủ, hai cột desktop/một cột mobile,
  không clipping/overflow/lỗi trang/lỗi console/hộp thoại/thao tác ghi sản phẩm.
- QA giữ15threads/24contexts/18turns/24versions/45workspaceevents, thêm
  đúng21run lifecycle giả và21tin nhắn `role=user` giả cần cho khóa ngoại;
  assistant/run-events0. Bảy trạng thái đọc qua GET/DOM thật nhưng chỉ là
  metadata QA, không chứng minh request đã thực thi hoặc có đầu ra.
- Tám bảng/allrows/schema/FK/source/evidence/sáu plan18scene giữ; owned Jobs0.
  Không click submit/refresh/restore/select/checkbox trong native.
- Empty/unknown/prototype/denied/malformed/read-state/executor-on/50+ chỉ
  kiểm bằng VM, không giả bootstrap/API ở native.
- Exact replay tám thay thế;18tệp bảo vệ giữ theo LF. Toàn bộ Python
  ngoài một needle test được phép giữ nguyên; chính tệp test đó phải bằng
  baseline sau đúng một phép thay xác nhận, không bỏ qua toàn tệp.
- Review nguồn độc lập C0/I0/M0 bằng inverse8NEW→OLD/full-source hashes;
  không reviewer chạy lại suite/native. Catalog/guard/attrs/CSS/test scope đạt.
- Nguồn case đo1312dòng/144400byteLF, SHA256
  `3d2b043c8670c3599cc9eddad756948f92ddc4d9949492878465a0ffa5fa1fc3`.
  Metadata32PASS; một test quyền POSIX600 cũ vẫn FAIL trên Windows.
  Lệnh chọn loại trừ của điều phối gõ sai tên nên test cũ đã chạy; không
  gọi đó là deselected, không sửa test/mã quyền để làm xanh, không lặp32ca.
  Test và helper quyền nguyên byte baseline; Linux CI vẫn chạy đủ.
- Scope verifier ban đầu nhầm mọi Python phải bất biến dù contract đã cho
  một needle test; sửa phép đối chiếu thành exact single-needle, giữ lỗi
  này là lỗi công cụ điều phối, không sửa app hoặc chạy lại các suite.

Artifacts: `chat-request-panel-permanent-red-nov15.log`,
`chat-request-panel-green-group-nov15.log`, `chat-request-status-wrap-red-nov15.log`,
`chat-request-status-wrap-green-nov15.log`, `chat-request-native-aggregate-nov15.json`,
`chat-request-panel-scope-nov15.json`. Ảnh VI375/EN1440 status strip đã xem.

## Giao hàng và giới hạn

Prerequisite lịch sử đã giao: PR739, CI43643846449 cả hai nhóm đạt,
merge/runtime63ddccd5, deploy43644999130, cây9d1c1eb8 giống bản kiểm tra;
dịch vụ/health/nguồn bảo vệ/bốn tệp HTTPS khớp. Receipts6884777207/6884777617.

Đơn vị hiện tại còn chờ CI đúng HEAD, merge/deploy và receipt
riêng; chưa nhận signed production UI hoặc đầu ra engine PASS.
Tiêu đề shell “AI Chat Workspace”, định dạng ngày giờ và các phần chữ ngoài
phiếu vẫn là hàng đợi, không tuyên bố toàn màn đã sạch. Kiểm toàn AX/auth/
thiết bị/Safari và M-FINAL01..06 vẫn mở, motion cuối.
Bot/route-engine/provider/wallet/PayOS/productiondata ngoài active goal.

PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_WRITES=0.

## Cổng trước push

CODE_REVIEW=C0/I0/M0; exact8replay và18protectedLF/Pythonneedle được đối chiếu.
OPERATIONS_DOCS_UPDATED=TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md.
INITIAL_FEATURE_COMPARISON=TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md;
nguồn hợp đồng Chat hiện hữu được chỉ ra, không bịa danh sách chức năng gốc.
TESTER_PROJECT_ID=CHAT-REQUEST-PANEL-20261115; TESTER_PROJECT_STATUS=READY,
workspace KIEM-THU/PHIEN-CHAT-REQUEST-PANEL-20261115.md; cùng Issue689.
CASE_METADATA=1312lines/144400bytesLF/exactSHA; nhãn/mẫu/Projects cũ giữ,
không dựng tracker cạnh tranh hoặc tự đăng nhập để lấy quyền Projects.
PUSH_GATE=READY với một baseline Windows POSIX case đã nêu; merge chỉ sau
CI đúng HEAD đạt đủ các nhóm. SOURCE/FINAL_SHA sẽ được ghi trên PR/receipt
sau commit, không đoán commit tương lai trong tài liệu nguồn.

## Receipt cập nhật15/11

PR740gộp sauCI43683345433hai nhómPASS trên576db2f5.
Merge/runtime0e97fd8a39950b67e7a6b68a2bf17aa8d3cece01,
tree0682f1ef1fda33453b781b80d7ba0e16d1292f7d exacttestedtree;
deploy43684233179PASS,services/health/protectedWebsources/fiveHTTPSassets
inclportal.css exact. Artifacts14149880596browser/14148754058auth;
receiptsIssue6896890245651/PR7406890245902. SignedUI/finaloutput chưa suy ra.
