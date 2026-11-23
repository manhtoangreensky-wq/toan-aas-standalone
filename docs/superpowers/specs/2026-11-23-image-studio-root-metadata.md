# ROOT-META-A/B — chữ đầu trang gốc thiết kế ảnh

BASE/runtime đã kiểm: `3d21e950fb8e676ffd0b8c945a5ff6d9c8425736`,
PR #798, CI45050895504, deploy45053284830, receipt689/7083404719.
Nhánh `codex/image-studio-root-metadata-20261123`.

Hiện trạng đo được: sáu quan sát renderer ở Việt/Anh/Trung cho thấy
`/image-studio` còn tên Anh và mô tả pha Việt/Anh; `/image-hub` có mô tả
Anh/Trung chứa giải thích kỹ thuật. Hai worker trả đúng7 record; preview
sáu trường hợp metadata và18 đối chiếu trang khác đạt, chưa áp dụng.

Phạm vi ứng dụng chỉ `static/portal/portal.js` và `portal-i18n.js`:

1. ROOT-META-A: hai nhánh title/description chỉ cho `/image-studio`; thêm
   hai khóa `imageStudioUi.page.title/description` trước khóa từ điển.
2. ROOT-META-B: đổi bốn hàng library hiện có: page.title/description và
   pagination.projectReference/assetReference. Giữ nguyên key.

Không đổi hero/section, breadcrumb logic, route, options, hành động, nội
dung khách, auth, backend, integration, Bot/engine/provider/ví/PayOS, ENV,
dữ liệu production hoặc motion. Không dùng thay chữ tổng quát.

Soi ảnh hưởng trước code: `git grep -n -E
'localizedPageTitle|localizedPageDescription|imageStudioText' --
static/portal` đo34 dòng trong một tệp ứng dụng `portal.js`. Hai hàm
metadata là dùng chung; không đổi chữ ký, nhánh mới khóa đúng một path.
Giữ các consumer và dùng đối chiếu metadata trang khác làm comparator.
Danh sách dòng:10100,10240,10246,10489,11074,11157,11225,11226,12242,
12456,12457,12459,12460,18921,18949,18951,18959,18967,19078,19079,
19080,19081,19082,19083,19084,19085,19086,19087,19136,19238,19239,
19240,19255,19258. Grep không thay cho kiểm hành vi.

Tiêu chí và thứ tự:

- [x] RED tái hiện chữ cũ bằng renderer nguồn vật lý:5 lỗi/3 đạt.
- [x] Nguồn metadata bằng BASE+đúng7 record, chỉ2app files.
- [x] Title/description hai trang đúng ba locale ở loading/failed/ready;
  controls/options/customer strings giữ; metadata18 trang đối chiếu giữ.
- [x] Hai key mới cân bằng, được đăng ký và khóa; bốn hàng cũ đúng.
- [x] Historical projection hữu hạn giữ assertion cũ và để thay đổi lạ
  tiếp tục bị phát hiện; không sửa snapshot để chấp nhận dữ liệu tùy ý.
- [x] Chrome12 màn375/1440 dùng nguồn thật, không lỗi/mạng/tràn; có thao
  tác nhập và tên khách giữ nguyên. Không suy thành toàn-app AX/contrast.
- [x] Kiểm gộp Image/metadata/historical, Python245/245 và review metadata
  C0/I0/M0; phụ lục màu có review riêng C0/I0/M0, không lặp metadata.
- [x] Vận hành/đối chiếu/Tester/provenance → một PR → exactCI → merge
  → deploy → runtime/assets → receipt. Giao diện signed production riêng.

Phản hồi/validation, bản nháp qua lỗi đọc/đổi revision/rời route và motion
không nằm trong đợt này; vẫn mở trên checklist mẹ.

Phụ lục đối chiếu lịch sử: nhóm14 tệp/89 ca ban đầu có15 lỗi so chữ/nguồn
cũ. Một lỗi catalogue chi tiết115≠93 đã có trên BASE, xác minh bằng chính
hai module test không sửa với hai nguồn UI lấy từ commit BASE:4 ca,
3 đạt/1 lỗi. Hai test purity thô cần đi qua projection hữu hạn đã có;
giữ nguyên số93/38, regex ngôn ngữ, uniqueness và mọi action assertion.
Test root mới vẫn dùng nguồn vật lý không chiếu để kiểm2key mới/4hàng
đổi và toàn bộ giá trị từ điển khác. Đây là sửa QA, không thêm thay đổi app.

PR #799 đã phát hành: CI45129027195 hai job success trên HEAD
b05d786ba3c902650f56751000461537dd1730ea. Merge/runtime
5a95e48c9df922cc19a4bd83dfef46f2d85c04d2, cây nguồn
4fbe691ab459831f3539fdb1c6fd5d8128a42848 trùng bản kiểm.
Deploy45132203233 success; VPS đúng SHA, nguồn sạch, ba dịch vụ active,
health hợp lệ và5+5assets đúng byte. Receipt689/7094535782 đã đọc lại.
Signed production UI vẫn NOT_TESTED; không đóng toàn goal.

## Prerequisite ROOT-HEADING — sửa màu tiêu đề thẻ gốc

Ảnh Chrome cho thấy tiêu đề thẻ gốc trắng trên nền sáng. Đo riêng8 màn
(hai route, hai viewport375/1440, sáng/tối):18/36 mẫu dưới4,5:1, thấp nhất
1,046:1; không lỗi/mạng. Đây là lỗi BASE còn lại, không do bảy record chữ.

Trước phát hành cùng đợt này, mở thêm đúng một record trong
`static/portal/portal-theme.css`: mở rộng rule màu sáng hiện có của hai
layout chi tiết sang thêm hai layout gốc. Giữ nguyên `color:
var(--portal-ink)`, độ đặc hiệu, kích thước/bố cục, nền và toàn giao diện
tối. Comment đổi từ “detail” sang “workspace” cho đúng phạm vi.

ROOT-META-A/B bảy record vẫn khóa nguyên vẹn trong fixture riêng.
ROOT-HEADING một record/fixture riêng, Antigravity chỉ trả đề xuất, Codex
đo preview trước áp dụng. Tổng ứng dụng đợt phát hành là8 record/3tệp.
Gate bổ sung:36/36 mẫu≥4,5:1, text/geometry/background giữ, dark foreground
giữ; source CSS=BASE+đúng1record, inverse hữu hạn và comparator cũ giữ.
Không mở rộng sang theme toàn app; motion vẫn cuối.

Prerequisite màu đã nhận đúng một record worker, preview và nguồn vật lý
đều36/36 mẫu đạt, thấp nhất12,352:1; text/geometry/background/dark
foreground giữ. CSS source test RED1 trước sửa, GREEN2 sau sửa; nhóm CSS
và các comparator ảnh hưởng33/33 đạt. Python màu90/90 chạy lại sau màu
là tập con của245 ca trước đó, không cộng thành335. Tổng Node cục bộ
99 ca duy nhất/16 tệp theo kết quả ghép và lượt kiểm phần thay đổi; không
khai là một lượt toàn suite mới. CI đúng HEAD vẫn là gate phát hành riêng.

CI đầu45124090509/head d9712dc1 thất bại6 ca của
`legacy-decorative-workbench.test.mjs`, cả ba locale/two wallet-fixture
states tại `/features/image`. Root cause: thẻ liên kết dùng cùng metadata
Hub đã đổi, nhưng factory đối chiếu lịch sử chỉ chiếu portal source, chưa
chiếu i18n source. Không phải lỗi chức năng hoặc dữ liệu; controls/context
đã qua các assertion trước điểm so HTML. Không rollback tám app records.

Sửa QA đúng một đầu đọc i18n bằng inverse bảy metadata record đã được kiểm
độc lập, không thay assertions/expected markup. Thêm raw-renderer case
cho cả hai thẻ ở ba locale để bảo vệ đúng chữ mới. Nhóm147/147 đạt, gồm
138 legacy và9 root metadata. Tổng kết ghép hiện238 ca Node/17tệp;
99 trước CI là lịch sử, không cộng lặp147 vào99. Chờ CI đúng HEAD mới.
