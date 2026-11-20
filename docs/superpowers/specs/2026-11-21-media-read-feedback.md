# Phản hồi đọc bộ sưu tập âm thanh — đúng kết quả và ngôn ngữ

TASK=MEDIA-READ-FEEDBACK-20261121.
PRODUCT=standalone WebApp.
REPO=manhtoangreensky-wq/toan-aas-standalone.
ROOT=C:/Users/toann/.codex/worktrees/locale-release-proof/_webapp-r218-voice.
BASE=fb1bbcf1fa7d36ba0745082229d9d1237d488364.
BRANCH=codex/media-read-feedback-20261121.
TRACKER=Issue689; comment tạo trước BUILD, không tạo Issue/PR giữ chỗ.
STATUS=PHYSICAL_GREEN_NATIVE_REGRESSION_PENDING; chưa phát hành.

Dependency PR782 đã giao: CI44783966598 cảhaiSUCCESS,
deploy44787944401SUCCESS70s/runtimeBASE/treeexact/VPS3active-running/
health/5+5assets/buildlocal-154a890da96f0a5fb8c8; receiptIssue7041067092/
PR7046821131đọclạiđúng. Khóa toàn bộ kết quả trước, không chạy lại.

## Lời Owner và thứ tự

“trong plan và checcklist thì cứ tự động cho phép không cần hỏi lại tôi”.
Làm đúng thứ tự, không sửa rộng, giao nhiều phiếu độc lập cho CLI hiện có;
worker chỉ trả đề xuất, Root ghép tuần tự. Hai lỗi code thật cùng fragment
mới tiếp quản trực tiếp; lỗi spec/transport/QA không tính worker sai.
Không đăng nhập hoặc đổi CLI/settings. Motion M-FINAL01..06 cuối.

Note: chia plan chi tiết thành spec có kết quả mở khóa; phần độc lập có
thể chuẩn bị/đề xuất song song, phần phức tạp có một gate nghiệm thu chung.

## Vấn đề nguồn đã quan sát, runtime RED chưa chạy

Ba branch trong integration.js28910–28942 cho filter/clear, page, refresh
đều await reader rồi báo success bằng câu VI lẫn thuật ngữ nội bộ.
hydrateMediaWorkspace có ba kết quả: current ready (kể cả empty hợp lệ),
current failed (state failed nhưng trả empty arrays), stale (stale:true).
hydrateMediaCollection trả null khi failed/stale; ready ở detail còn có
secondary await riêng AudioHub. Không được lấy global ready của lượt
khác hoặc dữ liệu truthy để tự kết luận lượt thao tác này thành công.

Đây là source witness, không phải runtime defect PASS/RED đã đo. Phải
thực thi RED trước phiếu ứng dụng.

## Phạm vi khóa

Ứng dụng chỉ hai tệp:

1. static/portal/integration.js: ba branch action trên và một helper chữ
   riêng; chỉ phản hồi sau đọc, không sửa loader/projection/currentness
   helper/API/busy/draft/schema hoặc các branch action khác.
2. static/portal/portal-i18n.js: các key mediaReadFeedback mới VI/EN/ZH,
   trước equal-keysets/freeze. Không đổi key hiện hữu.

Không sửa portal.js/CSS/motion, backend/auth/CSRF/quyền/DTO/URL/query/
offset/transport/retry/counter lifecycle, upload/write/Bot/route-engine/
provider/ví/PayOS/ENV/dữ liệu thật. Không đổi signature/return của reader.
media-audio-filter/clear/page và các validation/write/detail-copy khác
giữ ngoài scope, ghi hàng đợi riêng. Không dịch dữ liệu khách/server tùy ý.

## Các spec có dependency và kết quả chính

| Spec | Dependency | Kết quả phải có |
|---|---|---|
| MRF-READ/RED | PR782 receipts | Tái hiện success sai/VI/stale ở dispatcher thật; đóng băng scope nguồn |
| MRF-COPY | RED | Helper fallback/plain text + tám key, ba locale bằng literal |
| MRF-FILTER-PAGE | RED + copy contract | Current readyempty/nonempty mới success; failed cảnh báo; stale im lặng |
| MRF-REFRESH | RED + copy contract | Cùng nguyên tắc cho list/detail và secondary await hiện có |
| MRF-VERIFY | Ba proposal đã review/replay | Physical GREEN +151pins/historical/regression/baseline classification |
| MRF-NATIVE | VERIFY | Signed GET thật, fault/recovery/race đúng câu/role/focus, không ghi sản phẩm |
| MRF-RELEASE | MRF-NATIVE + Tester/prepush | Một PR/exactCI/merge-tree/exclusive deploy/VPS/assets/receipt readback |

Output-only packets cho copy/helper, filter/page, refresh, catalogue
độc lập không ghi repo; Root serial replay. Không mở spec phụ thuộc nếu
gate trước chưa có output thực nghiệm.

## Acceptance đo được

- AC1: filter/clear/page/listrefresh/detailrefresh chỉ báo success khi
  request counter/session/path của chính lượt còn current sau await và
  kết quả/state ready của chính nguồn đọc hợp lệ. Empty list vẫn success.
- AC1A: list và detail cùng ghi mediaWorkspaceReadState, nên mỗi action
  giữ cả counter chính dự kiến và snapshot counter còn lại trước await.
  Nếu counter còn lại đổi, phản hồi im lặng; không mượn ready/failed của
  luồng đọc khác. Không thêm counter hoặc đổi lifecycle của counter.
- AC2: current failed báo cảnh báo dịch đúng locale, không success. Stale
  vì newer request/route/session/logout im lặng; không dùng ready của lượt
  mới hơn để hợp thức hóa phản hồi cũ. Detail secondary await được kiểm.
- AC3: không thay loader/API/projection/epoch/reset/return shapes; source
  pins/protected comparators và URL/query/offset/action/permissions giữ.
- AC4: tám khóa mới là filtered/all/page/refreshed/readFailed/
  detailRefreshed/detailFailed/pageUnavailable. Literal VI/EN/ZH chốt
  trước RED; thiếu/empty translator fallbackVI, hostile text là plain.
- AC5: page capability guard biểu thức giữ nguyên, chỉ đổi câu lỗi sang
  helper; không thêm chính sách quyền hoặc nới điều kiện bất kỳ.
- AC6: dữ liệu khách, bản gõ và raw messages ngoài những branch cố định
  giữ nguyên. Không phát/tạo âm thanh, không giả xác nhận output.
- AC7: physical source execution không qua historical inverse; tests có
  deferred GET/race/currentness, frozen inputs, không actual provider/ví/
  storage/navigation/product write. Historical pins/assertions giữ.
- AC8: native QA cô lập ba locale mobile/PC, đọc/fault/recovery thật,
  account/DB giả/secret child-only, giữ read limit120/60s. Đúng ảnh/
  hash/CRC/decode/source/core/schema/auth/egress/owned0. Chi tiết ma trận
  chốt trước chạy; không nhận signed production/engine output từ local.

## Bằng chứng hiện tại

Tracker contract7047062064 đã đăng đúng Issue689 và đọc lại byte-exact.
RED vật lý187ca:2PASS185FAIL, toàn bộ lỗi assertion phản hồi, không
syntax/setup/side-effect lỗi. Bổ sung AC1A năm ca counter luồng còn lại:
0PASS5RED trên BASE, không chạy lại nhóm187. Bốn phiên CLI thật trả
đúng năm record từ helper/filterpage/refresh/catalogue, code failure0;
Root chỉ ghép tuần tự proposal, không takeover.

GREEN vật lý192PASS/0FAIL/0skip,12,626s; không historical inverse trong
current runtime. Fixture reviewed RAWsha
`5b924e5e0882a8ca649b64203a1d2af7360c63cd53c311a2b56f520c09feeac6`;
151pin/149tệp bảo vệ và phần còn lại hai appfile bằng BASE sau hoàn
nguyên đúng năm record. Không sửa loader/currentness/counter lifecycle/
API/auth/CSS/motion. Chạy comparator lịch sử trên nguồn mới60ca:
51PASS9FAIL do catalogue/pins của PR782 chưa chiếu leaf mới; chỉ sửa
hạ tầng kiểm thử hữu hạn, không đổi golden/assertion/fixture cũ.

NATIVE=NOT_RUN. PR/PUSH/MERGE/DEPLOY=NOT_RUN.
PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_MUTATIONS=0.
Whole goal ACTIVE/incomplete. Không suy code/CI/HTTP200 thành LIVE.

## Chốt ma trận native trước chạy

Browser plugin không có; dùng Playwright/Chrome local đã có, QA DB/asset
tạm và secret giả chỉ trong tiến trình con. Sáu view VI/EN/ZH ×320dark/
1440light; chỉ signed GET/control thật, abort/delay ở biên transport,
không fabricate response/DOM/control/state hoặc bỏ giới hạn120read/60s.
List lọc/xóa lọc/phân trang/làm mới được kiểm lỗi→phục hồi và phản hồi
cũ khi đổi trang. Detail signed GET và secondary-request bị đổi route
được kiểm riêng nếu điều kiện thật sẵn có. Mọi ảnh là mới, không dùng
ảnh PR782 để nhận kết quả đợt này.

Giới hạn có bằng chứng nguồn: detail page action="none", renderHero không
vẽ nút; chỉ list renderer có media-workspace-refresh. Vì vậy detail
refresh toast native là NOT_REACHABLE, chỉ có physical dispatcher tests;
không thêm nút hoặc phát event giả để nhận một luồng UI không tồn tại.
Gate native của đơn vị chỉ nhận các control thực có; không tuyên bố
full detail-action native, signed production UI hoặc đầu ra âm thanh.

Ma trận cố định:6view×8stage=48PNG mới (list-error/list-recovered/
empty-filter/page50/list-route-invalidated/detail-read-error/
detail-read-ready/secondary-route-invalidated). Hai lỗi transport/view
đi qua đúng ba retry GET hiện có:8abort/view,48abort/requestfail toàn
nhóm;12GET giữ chờ cho hai stale-route trục. Không sửa retry để giảm
số lỗi. View bắt đầu cách nhau ít nhất65s, observer ceiling90read/60s;
giới hạn app120/60s không đổi. Runner group420s,không tự retry toàn nhóm.

Focus: quan sát đúng trạng thái sau re-render, không ép restore bằng
script kiểm thử. Source BASE chỉ giữ focus cho input/textarea/select
và một số control riêng, không mọi nút. Nếu BODY nhận focus, ghi finding
riêng sau khi đo và kiểm control còn tới được bằng Tab thật. Không nhận
đã sửa generic focus/motion trong đơn vị phản hồi; các hàm focus/mount
giữ nguyên làm comparator chống hồi quy.

## Chữ cố định đã chốt trước RED

| Key | VI | EN | ZH |
|---|---|---|---|
| filtered | Đã lọc bộ sưu tập âm thanh. | Audio collections filtered. | 音频合集已筛选。 |
| all | Đã hiển thị tất cả bộ sưu tập âm thanh. | All audio collections shown. | 已显示全部音频合集。 |
| page | Đã tải danh sách bộ sưu tập âm thanh. | Audio collection list loaded. | 音频合集列表已加载。 |
| refreshed | Đã làm mới danh sách bộ sưu tập âm thanh. | Audio collection list refreshed. | 音频合集列表已刷新。 |
| readFailed | Chưa tải được danh sách bộ sưu tập âm thanh. Hãy thử lại. | Could not load the audio collection list. Try again. | 未能加载音频合集列表，请重试。 |
| detailRefreshed | Đã làm mới thông tin bộ sưu tập âm thanh. | Audio collection details refreshed. | 音频合集详情已刷新。 |
| detailFailed | Chưa tải được thông tin bộ sưu tập âm thanh. Hãy thử lại. | Could not load the audio collection details. Try again. | 未能加载音频合集详情，请重试。 |
| pageUnavailable | Chưa thể chuyển trang bộ sưu tập âm thanh lúc này. | Audio collection pages are not available right now. | 暂时无法切换音频合集页面。 |
