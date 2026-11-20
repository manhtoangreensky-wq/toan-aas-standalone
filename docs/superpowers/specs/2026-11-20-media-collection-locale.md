# Bộ sưu tập âm thanh — default, phân trang và hướng dẫn khách hàng

TASK=MEDIA-COLLECTION-LOCALE-20261120.
BASE=4080b879ad8d6ded081aa47313bf9cac67121f0b.
BRANCH=codex/media-collection-locale-20261120.
TRACKER=Issue689/comment7041067092.
Dependency PR781 đã giao và biên nhận đọc lại đúng.

## Vấn đề đã đối chiếu nguồn

1. `mediaCollectionValues` tự điền `general` và câu quyền sử dụng tiếng
   Việt. Thẻ và tiêu đề detail còn fallback `general` khi thiếu dữ liệu.
2. `renderMediaWorkspacePagination` gọi shared renderer bằng
   `portal-media-pagination`, rơi vào nhánh câu/nút VI viết cứng.
3. `renderMediaWorkspace` hiển thị policy-aside với lời giải thích nội
   bộ/mã khả năng và dòng trạng thái thực thi dư. Hai liên kết cần dùng
   nằm trong aside nên phải di chuyển trước khi bỏ khối.
4. 31 mục chữ cố định hiện có cần viết lại bằng ngôn ngữ khách hàng.
   Bảy key mới cho hai default và năm câu phân trang. Đủ 114 giá trị.

## Thiết kế và phạm vi khóa

Chỉ `static/portal/portal.js` và `static/portal/portal-i18n.js`.
Không đổi integration/backend/API/schema/auth/quyền/motion/CSS.

MC-DEFAULTS: bốn biểu thức dùng `audioWorkspaceText` hiện có. Chỉ fallback
cho dữ liệu falsy; mọi dữ liệu truthy, gồm `general`, câu VI cũ, khoảng
trắng, tên thương hiệu, ký tự HTML và giá trị được String hóa giữ nguyên.
Không dịch dữ liệu đã lưu hoặc thay cách lưu/ngữ nghĩa quyền sử dụng.

| Key mới | VI | EN | ZH |
|---|---|---|---|
| defaults.context | Sử dụng chung | General use | 通用用途 |
| defaults.rights | Tôi xác nhận có quyền sử dụng các tệp và yêu cầu trong bộ sưu tập này. | I confirm that I have the right to use the files and brief in this collection. | 我确认有权使用此合集中的文件和创作需求。 |
| pagination.range | Đang hiển thị {from}–{to} {label} | Showing {from}–{to} {label} | 正在显示第 {from}–{to} 个{label} |
| pagination.empty | Không có {label} ở trang này | No {label} on this page | 此页没有{label} |
| pagination.previous | ← Trang trước | ← Previous | ← 上一页 |
| pagination.next | Trang sau → | Next → | 下一页 → |
| pagination.aria | Phân trang {label} | {label} pagination | {label}分页 |

MC-PAGINATION: thêm một nhánh chọn chữ chỉ khi class là
`portal-media-pagination` và action là `media-workspace-page`. Không đổi
signature, range/offset/previous/next/route/escaping, không sửa nhánh
Memory/Music Library/media-audio hoặc lớp khác.

MC-CLEANUP: chỉ bỏ lời gọi policy-aside/wrapper hai cột trong
`renderMediaWorkspace`; giữ hàm policy cũ, không refactor. Đưa hai link
`/asset-vault` và `/projects` sang inline-actions trong footer tạo mới.
Bỏ span execution-summary ở activity, giữ nhãn sự kiện/revision/thời điểm.
Không bỏ form, trường, bộ lọc, thẻ, phân trang, liên kết công cụ hoặc
chốt canView/canCreate. Không khung trống sau khi bỏ aside.

MC-CATALOGUE: cập nhật đúng 31 key hiện có, thêm bảy key trên trước
equal-keysets/freeze. Các key hiện có gồm page.description/newDescription,
workspace.guardTitle/guardBody, intro.title/body, quick.kicker/title/body/
note/open, create.body/note, create.field.briefHelp/descriptionHelp/
projectHelp/rightsHelp, list.body, filter.note, activity.kicker/body/
emptyBody, event.item_attached/item_updated/collection_version_restored/
item_detached, collection.emptyBody/policyGuarded/note,
policy.openAssets/openProjects. Không dịch nội dung server tùy ý.

## Acceptance và bằng chứng

- Full portal/i18n vật lý chạy cùng VM, một test-local exposure, không
  thay renderer/helper production bằng stub. Falsy/truthy data frozen,
  đổi locale cùng VM, thiếu translator fallbackVI, không fetch/storage.
- Tên/UUID/option filter/selection/escaping/required/disabled/ARIA/action/
  route/min/max/input constraints giữ; mọi class/action paginator khác
  byte-equal BASE. Catalogue equal/frozen, chỉ đúng 38 key được thay/thêm.
- Main hai route `/media-workspace` và `/media-workspace/new` cùng renderer;
  scope cleanup cũng áp dụng phần chung của Audio Hub; phần Hub-only
  overview/next-steps giữ nguyên, không hứa khả năng tạo/phát âm thanh.
- Native VI/EN/ZH ×320×780tối/1440×900sáng, actual signed GET/các control,
  focus, geometry, console và source/schema/core/auth/egress/owned0 đủ.
  Không submit/create/update/upload/blob/provider hoặc dữ liệu thật.
- Review, hồi quy một lần, Tester/prepush/manifest/secret trước một PR;
  exactHEADCI/merge-tree/exclusive deploy/VPS/assets/build/receipt riêng.

Các phiếu output-only chạy độc lập; Root ghép tuần tự. Hai lỗi code thật
cùng fragment mới Root takeover; không tính lỗi transport/spec/QA.
Không login/settings mới. Whole goal ACTIVE; motionM-FINAL-01..06 cuối.
