# R218 — Đính chính phạm vi bằng chứng và mở lại nghiệm thu

## Trạng thái ưu tiên

Tài liệu này và completion ledger hiện hành thay thế các kết luận rộng trong
`R218-CHECKPOINT-20261021.md`, báo cáo pre-push và các đoạn checkpoint cũ của
`TAI-LIEU/`. Không xóa số đo lịch sử, nhưng không tiếp tục dùng chữ ACCEPTED
để kết luận đã hoàn thiện toàn bộ UI/UX hoặc motion.

BASE được review: `4e7943e17fecf63638457f6aaf1ef3854a92043e`.
Hai review độc lập chỉ-đọc đã đối chiếu source thực và runner QA.

## Các kết luận cũ chưa đủ bằng chứng

| Nhóm | Bằng chứng thật có | Phần còn mở |
|---|---|---|
| MU-B | Helper render đủ thẻ, escape | Test cũ mock action helper nên bỏ sót nút VI trong EN/ZH; phải kiểm workspace/actions thật |
| MU-C | Pure helper và fixture unknown/0 | Giá bán bị ẩn; chưa test input/change và idle expiry qua DOM thực |
| MU-D | Renderer con và synthetic report | Parent cần draft/estimate nên report-only confirm bị bỏ; fixture cũ thêm draft rỗng |
| MU-E | Ready row và failed-stale ở hai route | Guarded/loading/empty, role/id filtering, filter/page/isolation chưa đủ browser evidence |
| SubDub | 48 lượt URL/DOM-shape, một ảnh | Không click/keyboard/AX; chưa xác minh profile locale thực |
| Image | 72 lượt main/overflow/no-media | Không kiểm đủ form/action/AX/screenshots; locale thực chưa xác minh |
| Utilities | 120 lượt main/text-length/overflow | Không kiểm tác vụ; avatar save chưa được backend hỗ trợ; locale thực chưa xác minh |
| Video | 48 lượt body/overflow/no-media | Không đủ editor/profile/ordered-flow; locale thực chưa xác minh |
| Motion | Source/static + auth VM lifecycle | Browser chỉ đợi160ms và kiểm loader/overflow; không chứng minh mượt/hydration/cleanup/CLS/LCP/INP |

Các signed product runner cũ chỉ thay `?lang` nhưng tài khoản mới có hồ sơ VI.
`portal.js::interfaceLocaleFor` và server first paint ưu tiên locale hồ sơ đã
đăng nhập. Do đó số lượt URL không chứng minh ma trận VI/EN/ZH thực.
Chưa có lỗi console không đồng nghĩa chỉ `pageerror=0`: runner cũ không gắn
console listener. `writes=0` chỉ là page requests sau setup; vẫn có tạo/đăng
nhập tài khoản QA trước đó. Không có thao tác production/provider trong đợt.

## Sửa đúng trọng tâm

Music được sửa bằng renderer riêng, không sửa engine: nút locale đầy đủ, báo
giá công khai trước confirm, report độc lập draft/estimate và tracking đúng
reference. Generic renderer non-Music được khôi phục như baseline.
Test mới dùng catalogue/actions/report helper thật và direct confirm envelope.

Ảnh ban đầu của probe mới chụp giữa animation nên không chứng minh readable
final state; đã yêu cầu chờ animation hữu hạn kết thúc và cuộn tới report để
thu ảnh ổn định, không dùng việc chờ đó để kết luận motion mượt.

Trace chỉ-đọc trên QA cô lập là bước có thể thực hiện tiếp trong quyền QA đã
cấp. `NOT_RUN` là thiếu bằng chứng, không phải chặn do thiếu quyền.

## Việc giữ nguyên mở

Avatar API `ProfileUpdateRequest` hiện chỉ nhận display_name/locale/timezone;
UI avatar_url không có persistence, kể cả trước wave này. Không sửa auth/schema
trong phiếu Music; phải ghi riêng ở AC-01 và không báo chọn ảnh đã lưu được.

Không merge/deploy/LIVE. Runtime/provider/wallet/approval vẫn ngoài phạm vi sửa.
