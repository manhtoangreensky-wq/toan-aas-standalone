# Kho tệp — tải nguồn lựa chọn dự án

TASK=VAULT-PROJECT-OPTIONS-20261120.
BASE=4cf8590826846a3f3336a4d7359d53df965c226f.
BRANCH=codex/vault-project-options-20261120.
TRACKER=Issue689/comment7039622716.
STATUS=LOCAL_ACCEPTED_RELEASE_PENDING.

## Thay đổi đúng trọng tâm

Signed bootstrap xóa danh sách dự án trước khi hydrate. Route Kho tệp
không nằm trong điều kiện gọi reader dự án, dù form có ô gắn dự án.
Antigravity CLI hiện có, Gemini3.8FlashHigh, đã trả đúng một OLD/NEW và
Root áp dụng. Chỉ thêm exact `/asset-vault` với flag bật vào account
guard hiện có; không đổi reader/signature hoặc thứ tự các hydration.
0 lỗi worker code / 0 application takeover.

Fixture bất biến `tests/fixtures/vault-project-options-reviewed.json`,
RAW SHA `9faedb1fe8c1aff3d456a658f82dd107a4d4fab7690c51eb071b1d93dc53edee`.
Integration LF SHA `ae2814495b109821d0b770be78e253e4a5d0a7ddefc2eeeed6b05f1ac5c0c0a5`.
GitBASE/current151 nguồn đã đối chiếu: một nguồn đổi,150 giữ; toàn file
integration khớp đúng phép replay một fragment. Giữ account/flag/route,
UUID/schema, filter/offset, session/counter/path fences và fail-closed.

## Bằng chứng local

- Điều kiện dispatch thật cùng reader/helpers thật: BASE37PASS1RED →
  GREEN38PASS. API, session/page/mount là QA và các native-route detector
  được stub false; không nhận real detector hoặc fullbootstrap từ unit.
  18 exact routes cũ, disabled/guest/unrelated, empty/invalid/name/bounds/
  stale/logout được kiểm.
- Current-source acceptance đọc toàn nguồn vật lý trước mọi inverse;
  historical leaf hữu hạn chỉ phục vụ đầu vào kỳ vọng cũ. 42 ca chuỗi
  nguồn đạt. Review độc lập không finding chặn; assertion/golden/negative
  cũ giữ nguyên, không normalize toàn file để làm xanh.
- Node113tệp trực tiếp đọc integration và reverse-import consumers:
  3421 ca đạt,exit0,không skipped/cancelled/todo. Chạy một nhóm một lần,
  không chạy lại nhóm38/42đã đạt.
- Python20ca:16đạt/bốnlỗi. Chỉ bốn lỗi được chạy lại với exactBASEintegration
  trong child, portal/CSS/worker/pages/test bằng BASE, vẫn bốn lỗi giống
  nhau. Không sửa ứng dụng hoặc expectation để ép xanh, không nhận toàn kho.
- Native đủ sáu cấu hình hiện tại: một đại diện VI320 tối rồi đúng năm
  remaining-only. GET thật, UUID/tên có ký tự đặc biệt và chọn bàn phím
  đúng; không chạy lại đại diện. 12 ảnh đã kiểm hash/kích thước/chunk/
  CRC/IEND và giải mã đầy đủ;16 đầu vào receipt/ảnh không đổi.
  Source/core/schema/auth/egress/code giữ,owned0,0 lỗi console/network.

## Trình duyệt và giới hạn

Luồng: signed `/asset-vault` → `/api/v1/projects` → cả project/vault
readState ready → option từ server → native keyboard selection. Dữ liệu
được seed trước snapshot trong DB QA riêng; không khách hàng thật. Không
stub DOM/bootstrap/response, không upload/gửi form/blob/lifecycle/provider.
Chỉ asset-vault bật trong child, không đổi môi trường cha hoặc VPS.

Native BASE chưa chạy, không nhận một matrix before/after. 38 unit RED
không thay thế native BASE. Cấu hình current là VI/EN/ZH ×320×780 tối /
1440×900 sáng; một đại diện trước và năm remaining-only sau. Ảnh/console/
geometry/isolated guards phải được nhận trước khi phát hành.

Binding RAW SHA `bd482804c584c25f48624d2e42361a01310d746dd8b843b771d82f3c9a0bd200`.
Root đã đọc đủ bảy tệp chuẩn bị, giữ27codepins và chạy đúng1+5cấu hình.
Một lệnh CI mới chạy hai suite mới; không đổi trigger/quyền/phụ thuộc/
timeout/deploy. Bản thân nhãn native của ô chọn tệp có thể theo ngôn ngữ
trình duyệt/hệ điều hành; ảnh EN trên máy QA còn chữ VI ở control native,
không coi đây là bằng chứng toàn locale của mọi control đã hoàn tất.
Không thay control/upload trong task nguồn danh sách dự án.

Chưa có PR/CI/merge/deploy của task này. PR780 đã giao là dependency,
không phải bằng chứng project-options đã lên web. Signed production UI,
upload/blob/output, global accessibility/device/Safari vẫn chưa chứng minh.
Không Bot/route-engine/provider/wallet/PayOS/ENV/data/CSS/motion mutation.
Toàn goal ACTIVE; các câu chữ lẫn ngôn ngữ sau task này, motion cuối.
