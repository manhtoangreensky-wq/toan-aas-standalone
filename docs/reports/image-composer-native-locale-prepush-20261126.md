# IMAGE-COMPOSER-NATIVE-LOCALE-20261126 — báo cáo trước push

Đang đọc và áp dụng skill owner-governed-codex cho task này.

BASE `6ec003dbf8f80739f5fb93ff7bd1d7cc703c6792`; nhánh
`codex/image-composer-locale-20261126`; Issue #689. Dependency PR809
đã phát hành với receipt689/7169893110 và PR809/7169894142 đọc lại.
Một batch, một PR; không tạo issue/project/thẻ trống trùng.

## Scope và review

Đúng năm application files: `copyfast_image_studio.py`,
`static/portal/portal.js`, `portal-i18n.js`, `portal-theme.css`,
`integration.js`. Fixture giữ39record gốc,14amendments;53records total.
85 UI keys và15 feedback keys cân bằng VI/EN/ZH;24 nhãn note VI/EN.
Năm before/after full-source pins, source acceptance luôn raw.

Thay đổi locale, phản hồi, định dạng ghi chú mới, disclosure và màu/
font riêng Composer. Không đổi validation/payload/auth/CSRF/ownership/
idempotency/schema hoặc persisted category/tags/index. Không viết lại
note cũ. Mười state có sẵn giữ nguyên, không đọc/chạm state bị cấm.
Bot/route-engine/provider/wallet/PayOS/ENV/production data/deploy
workflow được bảo vệ; quality workflow chỉ bổ sung test/gate.

Review gộpC0/I2/M0; sau sửa một màu focus và đăng ký đủ test,
focused correctionC0/I0/M0. Root không sửa ứng dụng thay worker:
thay đổi cuối là exact proposal Gemini4ExtraHigh. Frame OLD anchor
đã fail hai lần từ trước, root sửa đúng OLD, NEW không đổi.

## Bằng chứng và giới hạn

[Phiên Tester](../../KIEM-THU/PHIEN-IMAGE-COMPOSER-NATIVE-LOCALE-20261126.md)
và [báo cáo](../../reports/tester/IMAGE-COMPOSER-NATIVE-LOCALE-20261126.md)
ghi riêng từng nhóm, không cộng lặp. Functional488, receipt150,
pipeline13, renderer258, feedback45, note110, final-source19,
other-route18 và Python lịch sử18 có output đạt. Builder26 tổ hợp
trong một pytest item đã kiểm lại source fixture; compile/syntax/diff
exit0. Nguồn557 observations có hai lỗi QA, phục hồi224/224; không
gọi đó là một fresh full suite.

Chrome componentHTTP48view:2112 enabled samples,min5,4733;
placeholder min5,5225;24focus min5,8601,2px;0finding/error/external/
overflow. Đã mở ảnh375sáng/tối. Không dùng overlay làm final evidence.
Không nhận full bootstrap/auth/API/persistence hoặc production.

HTTP local300s/0completed không PASS. Exact-head CI phải chạy dedicated
Ubuntu API gate tám phút và authenticated QA, cùng toàn nhóm nguồn.
Không merge khi cổng này chưa đạt.

## Ba cổng tài liệu trước push

1. [Vận hành hiện tại](../../TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md) phân
   biệt PR809 đang chạy với ứng viên Composer, không suy dữ liệu thật.
2. [Đối chiếu chức năng](../../TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md)
   dùng BASE PR809 và source ban đầu làm comparator; không bịa tài liệu
   mua sẵn hay số khách/tiền. Feature list gốc vẫn giữ trong tài liệu.
3. Phiên Tester độc lập cóID/BASE/scope/AC/regression/evidence;10case
   `ICNL-*` nằm cùng nguồn case. Dùng nhãn/mẫu có sẵn và Issue689;
   không nâng quyền Projects hoặc đăng nhập mới.

Readiness metadata cần khớp các tệp tài liệu cuối và test metadata
phải đạt trước push. Root kiểm explicit staging; không `git add .`.
Source commit → refresh Web-only evidence → evidence commit →
verify → một PR → CI exact HEAD → merge/tree → exclusive Web-only
deploy → runtime/health/assets/receipt. Các cổng sau còn pending;
không dùng trước khi có bằng chứng.

`PROVIDER_CALLS=0`; `WALLET_MUTATIONS=0`; `PRODUCTION_DATA_WRITES=0`;
`WHOLE_GOAL_COMPLETE=NO`. Signed UI/device/Safari/full locale/AX/
auth lifecycle/drafts và motion cuối vẫn giữ mở trong checklist mẹ.

Bộ nhãn Tester đã được hỏi GitHub hiện tại:22nhãn, đủ12nhãn bắt buộc;
hai mẫu issue local có sẵn. Main kiểm lại vẫn6ec003db và chưa có PR
cùng nhánh. Metadata/PASS và scope scan là điều kiện còn lại trước
source commit; không tạo thêm bảng Projects hoặc refresh đăng nhập.

`PUSH_GATE=READY_FOR_SINGLE_PR_EXACT_HEAD_CI`. Metadata1/1, compile,
syntax và diffcheck đạt. Scope manifest khóa46tệp, chỉ5tệp ứng dụng;
10statecũ bị loại khỏi staging và không đọc nội dung. Scan không có
credential thật; một private-key header chỉ là regex phát hiện bảo mật
nguyên byte từ BASE, không phải key. Các miền bảo vệ không thay đổi.
`TESTER_SESSION=READY_FOR_EXACT_HEAD_CI`; HTTP/deploy/LIVE vẫn pending.
