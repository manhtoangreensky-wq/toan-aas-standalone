# R218-MUSIC-REVIEW-001 — sửa lỗ hổng nghiệm thu luồng có dữ liệu

BASE_SHA=4e7943e17fecf63638457f6aaf1ef3854a92043e; PR #654.

## Scope và thứ tự

CI fingerprint đã refresh/verify trên clean checkout nhưng chưa push riêng;
phải khóa các lỗi runtime presentation phát hiện trước, rồi sinh provenance
lần cuối trên source commit sạch. Không thay workflow hay bỏ qua gate.

Allowed: `static/portal/portal.js` chỉ các renderer Music mới, dispatch Music
trong `renderWorkspace` và khôi phục generic renderer như BASE trước wave;
`portal-i18n.js` chỉ catalogue Music; test hành vi tích hợp, ledger/evidence.
`applyCanonicalDraftToForm` và nhánh copy của `dispatchAction` chỉ được đổi
chuỗi thông báo trong điều kiện route Music, không đổi chữ ký hoặc hành vi.
Protected: Voice helpers/timer, Image/Video/generic output, backend/auth,
provider/wallet/PayOS/schema và action/payload chính thức.

## Finding cần tái hiện bằng RED

- MU-B test thay `canonicalDraftActions` bằng hàm giả nên không bắt được nút
  tiếng Việt trong EN/ZH.
- MU-D test gọi riêng report renderer; flow confirm thực tế có thể chỉ có
  `report/tracking`, không có `draft/estimate`, bị generic renderer trả rỗng.
- `renderWorkspace` bọc flow Music bằng trạng thái/thông báo kỹ thuật tiếng Việt;
  3-locale helper test không bao phủ đoạn này.
- Thay generic source note bằng `safeText` toàn chuỗi gây escape hai lần đối với
  nguồn chứa `&`, cần comparator output non-Music trước/sau.

## AC và checklist

- [x] AC01 workspace Music dùng fixed chrome VI/EN/ZH thật, action copy/apply
  gắn đúng prompt/route/field; không dịch dữ liệu người dùng.
- [x] AC02 confirm report-only + matching tracking hiển thị báo cáo; không cần
  nhét draft giả vào fixture; unknown/0/progress/empty giữ khác nhau.
- [x] AC03 giá bán được trình bày rõ trước confirm; thiếu hoặc mâu thuẫn thì
  không tạo giá; không dùng copy planning cho kết quả đã xử lý.
- [x] AC04 output generic non-Music bằng baseline (kể cả escaping).
- [x] AC05 bộ Node mới dùng renderer/actions/catalogue/report helper thật,
  browser smoke có dữ liệu ở VI/EN/ZH được kiểm locale thực tế; không gửi job.
- [x] AC06 ledger MU-B/C/D mở lại trước BUILD; chỉ đóng từng AC có evidence.

Evidence: integrated13/13; full Node826/826; browser18 cấu hình với locale hồ
sơ được assert, apply/quote0/unknown/input/revert/report-only18; idle expiry3
giữ cùng node form; page/console/UIwrites/external0. Ảnh/AX và source hashes
ở `reports/audit/R218-MUSIC-RUNTIME-REVIEW-QA-20261021.json`. Independent
review chạy lại18/18 (13 integrated +5 suggestion) và chấp thuận hẹp Music.
CI/provenance và mọi nhóm khác vẫn không được suy diễn từ evidence này.

Verify: `node --test tests/music-workspace-runtime-integration.test.mjs` →
không failure; sau đó Music/Voice/Image regression, syntax và browser QA cô lập.
PROVIDER_CALLS=0, WALLET_MUTATIONS=0, DEPLOY=NO, LIVE_PASS=NOT_TESTED.
