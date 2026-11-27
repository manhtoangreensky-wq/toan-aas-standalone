# GSC-DATA — dữ liệu ngôn ngữ của danh mục tĩnh

Đang đọc và áp dụng skill owner-governed-codex cho task này.

BASE=`29e0c154dfd247ac4b0a68cd6336ec83fb3af8ef`;
branch=`codex/gallery-static-catalogue-20261127`; standalone; Issue #689.
PR818 đã giao: CI45975827455 hai SUCCESS, Web deploy45980538327 SUCCESS,
runtime29e0c154/tree030b4507 khớp tested tree, 7+7asset/cache đúng.
ReceiptIssue6897215714422/PR8187215714594 đọc lại khớp.

## Kết quả READ

Nguồn công khai `copyfast_free_prompt_gallery.py`, snapshot `2026-07-15.1`,
LF SHA256 `b9d32e2163f473649f7f9e14e7ed3f363fbb13c3e654fa29686671afc0fb94ae`.
AST literal-only, không import module hoặc mở DB:7 nhóm ×20 ngành=140mẫu.
Có7goal và9platform. Chuỗi còn pha ngôn ngữ nằm trong tên nhóm/ngành,
tiêu đề, câu lệnh và biến thay thế do Web định nghĩa, không phải nội dung khách.

READ lưu/sao chép: browser sao chép nguyên `selected.item.prompt`;
Memory save lấy lại nội dung từ danh mục trên server, không nhận prompt từ
browser. Vì vậy chỉ dịch phần hiển thị sẽ tạo khác biệt nội dung đọc/copy/save.
Không nhận giải pháp đó là hoàn thành Gallery locale.

## Phạm vi pha dữ liệu

Bốn worker độc lập, proposal-only, không ghi ứng dụng:

| SPEC_ID | Hàng dữ liệu | Kết quả bắt buộc |
|---|---|---|
| GSC-CATEGORIES |7nhóm×title/title_template/prompt_template=21 |63giá trị VI/EN/ZH |
| GSC-INDUSTRIES-A |10ngành đầu×title/product/audience/benefit=40 |120giá trị VI/EN/ZH |
| GSC-INDUSTRIES-B |10ngành sau×bốn trường=40 |120giá trị VI/EN/ZH |
| GSC-TAXONOMY |7goal+9platform=16 |48nhãn VI/EN/ZH,ID giữ |

Tổng117hàng/351giá trị phải được kiểm; chưa đo số thay đổi/giữ thì không
ghi suy đoán. Mỗi hàng gồm kind/id/field/before/after{vi,en,zh}.
Giữ đúng ID, snapshot, thứ tự, biến `{industry}/{product}/{audience}/{benefit}`,
số, thời lượng, tỷ lệ, ý nghĩa/ràng buộc nguồn. Tên thương hiệu giữ;
không để thuật ngữ Anh thông thường trong VI/ZH.
Không thêm cam kết, quảng cáo quá mức, quyền sử dụng hoặc khả năng thực thi.

ALLOWED_PROPOSAL_INPUT=trích đoạn dữ liệu tĩnh của nguồn đã công khai,
đặc tả này và toàn bộ MAP.md. Không gửi test, fixture API, credential/ENV,
dữ liệu khách, tài chính hoặc nguồn Bot.
PROTECTED=mọi appfile hiện tại, DTO/guard/auth/backend/API/engine/Bot/
provider/wallet/PayOS/schema/data/motion và51giá trị GPC đã giao.
APP_WRITES=0;GIT/VPS/LOGIN/SETTINGS=NO;PROVIDER_CALLS=0product.

## Cổng nghiệm thu dữ liệu

- [x] PR818 giao dứt điểm; BASE/branch/tracked clean đã đối chiếu.
- [x] Nguồn tĩnh được trích bằng AST, đủ7/20/7/9 và140mẫu.
- [x] Contract Issue689/7216006483 đọc lại khớp;4phiếu tự chứa full MAP.
- [x] Bốn proposal trả đúng schema/117hàng/351giá trị, CLI terminal0,
 một lượt trả proposal mỗi phiên; không tool/appwrite.
- [x] Root đọc351giá trị một lượt; giữ nghĩa, nhãn và tên riêng thống nhất.
- [x] Máy kiểm keyset/ID/before/token/number/locale/schema:
 `validate-gallery-static-proposals-nov27.cjs` exit0,0lỗi/0từ Anh thường
 trong VI/ZH. Receipt khóa nguồn tại `gallery-static-data-frozen-nov27.json`
 trong bộ bằng chứng local; đây không phải nghiệm thu runtime.

Trạng thái pha dữ liệu không phải trạng thái ứng dụng đã tích hợp.

## Cổng ứng dụng bắt buộc sau pha dữ liệu

1. Chốt riêng contract transport/presentation theo đúng nguồn ID/version:
   một ngôn ngữ nội dung nhất quán cho danh mục, tìm kiếm, chi tiết, sao chép
   và lưu mới; không dịch dữ liệu tùy ý và không sửa ghi chú đã lưu.
2. RED trước app edit; Antigravity sửa đúng allowlist đã đo. Không đổi
   ownership/CSRF/idempotency safety hoặc generic API/auth để làm tiện.
3. Kiểm hành vi current/stale/locale-switch và parity read/copy/save bằng
   dữ liệu giả/DB tạm; provider0/wallet0/production-data-write0.
4. Giữ nguyên PR818 source/fixtures/pins lịch sử bằng projection hữu hạn,
   primary mới đọc raw; nghiệm thu gộp failed/affected, không kiểm trùng.
5. Browser/role/responsive/AX, review, docs/Tester/provenance, exact CI,
   một PR/merge/Web deploy/runtime/assets/cache/receipt theo cùng Issue.

Không chọn cách chỉ dịch nhãn để né nội dung mẫu hoặc lưu. Toàn goal,
signed-production/auth/draft/device/Safari và motion cuối vẫn mở.
