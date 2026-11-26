# Phiên kiểm tra — Soạn mô tả ảnh

ID `IMAGE-COMPOSER-NATIVE-LOCALE-20261126`; BASE
`6ec003dbf8f80739f5fb93ff7bd1d7cc703c6792`; nhánh
`codex/image-composer-locale-20261126`; Issue #689, contract
`7170035286`, phụ lục `7170804673`, `7171342911`, `7174154546`.
Trạng thái `LOCAL_COMPONENTS_VERIFIED_HTTP_CI_RELEASE_PENDING`.

## Phạm vi và tiêu chí

Nguồn ca duy nhất: nhóm `ICNL-*` trong [DANH-SACH-CASE.md](DANH-SACH-CASE.md).
Đúng năm tệp ứng dụng, 39 record gốc và 14 amendments, do các phiên
Gemini 4.0 Extra High đề xuất; root đối chiếu trước khi tích hợp.
Giữ bảy trường, 20 option values/order, limits, actions, ARIA, guards,
customer text và ngôn ngữ đầu ra do khách chọn. Không đổi Bot/engine/
provider/ví/PayOS/ENV/schema/production data hoặc motion.

## Kết quả đã quan sát

| Nhóm | Bằng chứng |
|---|---|
| Raw source và inverse cuối | 19 đạt, 0 lỗi/bỏ qua; đúng BASE+53 records, năm full-source pin |
| Route lân cận | 18 đạt: sáu route × ba locale, title/attributes/control markup bằng BASE |
| Receipt portal | 150 đạt; 138 valid/rejection và 12 bootstrap/render |
| Receipt pipeline | RED12fail/1pass; sau một return-object amendment,13case đạt gồm85 invalid-boundary observations |
| Builder và Pydantic thật | 26 tổ hợp trong một pytest item; EN bằng BASE/customer giữ; kiểm fixture/source cuối1/1 đạt |
| Result renderer | 258 đạt:246 view states và12 guard/escaping |
| Phản hồi thực | 45 đạt:15 nhánh × ba locale, thực thi handler/shape/guard/receipt thật, chỉ mock API boundary và request sanitization |
| Ghi chú mới | 110 đạt:26 kết quả × bốn lựa chọn và sáu invalid-index; không DB/network |
| Functional Composer | Lượt gộp488/488 đạt tại50record, trước ba CSS-only amendments cuối |
| Nguồn lân cận | 29file/557 observations:555pass/2QAfail; chỉ hai file được sửa reader/classifier, phục hồi224/224 |
| Python lịch sử/static | 18/18 đạt; compile app/helper/tests và syntax ba bundle exit0 |

Không cộng các lượt trên thành số ca duy nhất. Hai lỗi QA được giữ
trong log; không sửa assertion/pin cũ hoặc tính là lỗi worker.
Frame OLD anchor có hai lỗi worker cùng dấu gạch chéo, root chỉ sửa
OLD literal; NEW worker giữ. Các phần còn lại worker code failures0.

## Trình duyệt nguồn vật lý

Browser plugin không có; dùng Playwright/Chrome hiện có, không cài
gói. HTTP component localhost dùng renderer/CSS và helper thật, DTO
từ builder thật; mọi request ngoài bị chặn. Ma trận48 view:
VI/EN/ZH × light/dark ×360/375/768/1440 ×empty/result.

2.136 mẫu quan sát gồm2.112 mẫu đang bật đo được,0mẫu bật chưa chắc;
24mẫu vô hiệu báo riêng. Chữ thấp nhất5,4732500812:1, placeholder
5,5224777212:1. 24quan sát Tab/focus-visible thật có viền2px,
thấp nhất5,8600809480:1. 0finding/0error/0external/0overflow.
Đã mở ảnh empty375 sáng/tối để rà nhãn/ô nhập thực tế.

24view empty đã đổi Mục tiêu riêng qua lại, kiểm FormData và giữ chữ
trong DOM khi mở lại. Helper phong cách cũ vẫn xóa trường riêng khi
đổi sang gợi ý như trước. Không suy thành giữ draft qua redraw/session.

Audit ban đầu thiếu nhãn/pseudo/focus, cùng rule `!important` chung:
các lần RED và thiếu sót spec/QA được giữ riêng. Bản cuối
`image-composer-browser-physical-r8-final-nov26/summary.json` không
dùng overlay. Lượt overlay chỉ là chẩn đoán. Lượt overlay đầu0view lỗi
TEMP của sandbox, không phải lỗi ứng dụng hoặc worker.

## Review và cổng còn lại

Review gộp ban đầu C0/I2/M0: màu focus bị ghi đè và thiếu CI registration.
Đúng hai delta đã sửa; focused review C0/I0/M0, ready for exact-head CI.
Reviewer không chạy lặp suite/browser. Bốn test feedback/note/other-route
đã đăng ký trong quality workflow.

HTTP TestClient local hết300giây ở testcase đầu,0ca hoàn tất; owned QA
đã kết thúc. Không gọi PASS hoặc baseline-equivalent. Ubuntu API file
có10 test functions, phải đạt cổng tám phút của CI trước merge.
Đăng nhập CI, merge/tree, deploy/runtime/health/5+5assets/receipt và
signed production UI là các bằng chứng riêng còn chờ.

Full-app locale/AX/auth lifecycle/drafts, device/Safari và motion vẫn
mở. `PROVIDER_CALLS=0`; `WALLET_MUTATIONS=0`; `PRODUCTION_DATA_WRITES=0`;
`WHOLE_GOAL_COMPLETE=NO`.
