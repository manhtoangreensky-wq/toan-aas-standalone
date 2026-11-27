# Phiên kiểm tra Thư viện câu lệnh miễn phí

Đang đọc và áp dụng skill owner-governed-codex cho task này.

ID=GALLERY-CUSTOMER-COPY-20261127; Issue #689.
BASE=`bf95e4017717622d694cbef02fde07799a823a8a`;
branch=`codex/gallery-customer-copy-20261127`.
Contract7212461046; prerequisite7212923847; amendment7213070038 đọc lại đúng.
PR816 đã giao; không kiểm lại các phần không đổi của đợt đó.

## Phạm vi và điều kiện đạt

- GPC-COPY: 16 khóa Gallery +1 khóa tên trang, 51 giá trị VI/EN/ZH;
  50 đổi/1 giữ, không lẫn thuật ngữ triển khai trong chữ cố định.
- GPC-STRUCTURE: bỏ phần giải thích lặp, chi tiết chưa chọn và ô cuối;
  giữ mọi nút, form, ID, route, quyền, dữ liệu và điều kiện xác nhận lưu.
- GPC-RENDER: chỉ ánh xạ hai chuỗi Web nguyên văn; chuỗi lạ/nội dung
  khách giữ và escape; mức ưu tiên dùng nhãn có sẵn, không sửa enum.
- GPR: 11 rule riêng Gallery +1 điều kiện số liệu. Ô lọc ≥16px;
  chữ ≥4,5:1, focus ≥3:1, vùng bấm ≥44px. Không hiện số 0 chưa biết.
  Danh mục hợp lệ/tìm rỗng vẫn giữ số thật; không để cột trống.
- Source phải bằng BASE+56 record GPC+12 record GPR, không có byte khác.
  Fixture/pin/kỳ vọng lịch sử giữ; inverse hữu hạn không xóa unknown bytes.

## Bằng chứng đã có

GPC raw RED104=82fail22pass → GREEN104. Affected113PASS;
Python leaf14PASS; protected routes12PASS; review GPC C0/I0/M0.
GPR RED26=14fail12pass → GREEN26; GPC forward-source2PASS.
Bốn phiếu GPR do Antigravity `gemini-4-hydrogen-xhigh` trả đúng R1.
Root chỉ ghép cơ học, worker failures0; thêm điều kiện số liệu là thiếu
spec của root, không lỗi worker đã giữ số liệu đúng phiếu trước.

Browser đầu phát hiện 612 lỗi tương phản/120 ô nhập 15px và42 gradient
gaps. BASE3view tái hiện kiểu lỗi; gradient bounds chứng minh trắng trên
nền cũ không đủ4,5. Một lượt chạy không mở được Chrome do TEMP sandbox
được ghi riêng, không phải lỗi UI. Lượt paint recovery60view/2304mẫu
đạt màu nhưng phát hiện QA thiếu aside ở desktop khi xem ảnh; chưa nhận
kết quả đó là desktop-layout PASS.

Lượt cuối dùng đúng topology aside/backdrop/workspace từ template thật:
60view/2304mẫu đo hết; mintext5,216649621048673:1,
minfocus5,860080947953878:1, input16px, target44px;
desktopmain1136px. 0finding/error/overflow/egress/unmeasured.
Ảnh đầu trang375/1440 và sau tương tác đã xem, không cột hẹp giả.
Chrome/server đóng finally, exit0.

Affected Node94PASS và Python51PASS,0fail/error/skip. GPRdelta review
C0/I0/M0 một lượt. Không lặp104/113 hoặc đọc lại51giá trị ngữ nghĩa.

## Cách kiểm và giới hạn

Chỉ dữ liệu giả, localhost, actual full renderer/normalizer/i18n/CSS.
VI/EN/ZH × guarded/empty/list/detail/saved ×375/1440 ×sáng/tối.
Nhập ô tìm kiếm, dùng Tab, đo chữ/focus/vùng bấm/tràn/bề rộng nội dung;
xem ảnh đầu trang và ảnh sau tương tác. Không gửi form tạo/lưu thật.

Không chứng minh client hydration, clipboard/save API, auth/draft/full
header/sidebar, thiết bị/Safari, signed-production hoặc motion.
GPC-CATALOG còn riêng theo ID/version; không dịch tùy ý dữ liệu khách.
TESTER_SESSION=READY_FOR_EXACT_HEAD_CI_AFTER_MACHINE_PROVENANCE.
Metadata33ca32PASS/1WindowsBASEFAIL:POSIXmode600assertion quan sát0666,
cùng lỗi đã xác minh PR816. Test/script sync nguyênBASE,không sửa
permission/kỳvọng; CI Linux exactHEAD còn làcổng bắtbuộc.
CI/merge/deploy/runtime/assets/cache/receipt là gate riêng còn mở.
PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_WRITES=0.
WHOLE_GOAL_COMPLETE=NO; MOTION=LAST.

## CI recovery

PR818/CI45966746125:3historicalcataloguesnapshotFAIL/83PASS ởshared-select.
PhụlụcIssue6897213848011readbackexact;localRED3. Bổsung đúng17key
snapshotinverse trướcFCH,chặnthiếu/sai/lặp/đảo/foreignlocale/mixed/shape.
Khôngđổiapp/copy/CSS,khôngreviewlại51values hoặcchạybrowserlại.
ExactHEADCI của bản QA recovery vẫn phải đạt hai job trướcmerge/deploy.
Recovery146PASS/0fail/skip;QA-deltareviewC0I0M0. App3pins giữ nguyên.
