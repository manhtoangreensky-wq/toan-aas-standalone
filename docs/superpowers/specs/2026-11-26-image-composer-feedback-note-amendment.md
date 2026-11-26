# COMP-FEEDBACK / COMP-NOTE — chữ thao tác và ghi chú mới

BASE6ec003db, nhánh `codex/image-composer-locale-20261126`, Issue689.
39record gốc và1receipt-amendment giữ khóa. Hai spec độc lập được giao
song song output-only; root chỉ tích hợp sau khi cả phiếu khớp contract.

## COMP-FEEDBACK

Phạm vi: `static/portal/integration.js` chỉ một helper chữ riêng và15
vị trí thông báo trong ba action chọn/soạn/lưu; `portal-i18n.js` thêm
15key cân bằng VI/EN/ZH namespace `imageComposerFeedbackUi`.
Nguồn chữ: `tests/fixtures/image-composer-feedback-copy.json`, đã được
Antigravity4ExtraHigh dịch và điều phối rà một lượt. Không dịch lại.

Thông báo thành công chỉ chạy sau các kiểm dữ liệu hiện có; không hiển
thị `result.message` cố định kỹ thuật từ server ở hai nhánh thành công.
Chặn/đã cũ/đang lưu/chưa xác nhận phải khác nghĩa, không đổi lỗi thành
công. Không đổi predicates/payload/index/acknowledgment/submission/
idempotency/route/currentness/ownership hoặc error propagation.

RED3/3fail đúng câu kỹ thuật hiện tại, không lỗi setup:
`image-composer-feedback-red-nov26.xml`. Cần mở rộng kiểm hành vi
đủ15nhánh và fallback/placeholder/locale sau code; chỉ3case chưa đủ AC.

## COMP-NOTE

Phạm vi duy nhất: `_image_prompt_composer_memory_note` trong
`copyfast_image_studio.py`. Nguồn chữ24nhãnVI/EN tại
`tests/fixtures/image-composer-native-note-copy.json`.
Ghi chú MỚI dùng ngôn ngữ mô tả `result.language`, không theo localeUI.
Title/headings và tên lựa chọn là chữ tự nhiên; không raw preset code,
language code hoặc dòng `selected_variant_index` trong nội dung.
Giữ số index ở payload/tags/logic và ý nghĩa lựa chọn hiện có.

Không thay model-validation/predicate/UUID/index/range/MAX limits/
exception/transaction/idempotency/category/priority/tags. Không đổi
nguyên văn mô tả hoặc nội dung khách. Không viết lại ghi chú đã tồn tại.
Chỉ thay cách dựng title/content mới; bỏ đoạn cuối liệt kê kỹ thuật
không liên quan. `category` vẫn `Image Prompt Composer`.

RED8/8caseVI/EN×4selection fail đúng title cũ;102case chưa chạy ở lượt
RED hẹp. Full suite mới110case gồm104serialization và6invalid-index;
cần đạt sau code. Không mở server/ghiDB/network để kiểm formatter.
Unit110 phải kiểm title/headings,26result×4selection, selected prompt,
mọi mô tả/customer text, tags và422invalid selection.

## Tích hợp và bảo vệ

Hai phiếu CODE R1: feedback3record (helper1+block15call+catalogue1), note1
recordfunction. Preflight ban đầu thấy câu chung xuất hiện7nơi, trước
khi worker nào khởi chạy; root khóa anchor cả block riêng Composer.
Không tính lỗi worker hoặc gọi là vòng retry. Các OLD/NEW ở `expected.json`;
không apply source bởi worker, không Git/VPS/ENV/login.
Cần giữ39record gốc bất biến, thêm4record riêng vào amendments sau
receipt1. Tổng dự kiến44record/năm source. Snapshot lịch sử bỏ đúng15
key mới trước85key cũ, giữ unknown/duplicate/mutated-value failures.

Source checksum của fixture26DTO phải cập nhật đúng source pin mới;
26DTO builder phải giữ nguyên byte về dữ liệu. Kỳ vọng note title/
header trong APItests chỉ đổi chữ đúng contract; mọi assertion role,
CSRF,body-shape,ownership,idempotency,counts vàcategory giữ.

- [x] Hai bảng chữ đã được rà; source function/nơi dùng đã đọc.
- [x] REDfeedback3fail; REDnote8fail đúng copy chưa thay.
- [x] Hai CODEworkerR1 khớp bản ghi, compile/diff/protected comparators.
- [x] Apply exact4amendments; feedback45nhánh, formatter110case đạt;
  source/history cuối19case đạt sau toàn bộ53record.
- [x] Full feedback15nhánh×3locale/currentness guards không đổi.
  Browser màu/disclosure đã kiểm theo phụ lục riêng, không suy draft.
- [ ] Review/hồi quy gộp, Tester/docs/provenance/UbuntuAPI/CI/ship cùngbatch.

Mọi lệnh save/runtime sản phẩm thật, Bot/engine/provider/ví/PayOS,
ENV/secrets/schema/production data và motion đều ngoài phạm vi.

Kết quả ghi chú ở đây là formatter/unit và API CI còn bắt buộc; không
được đổi thành tuyên bố đã lưu/đọc dữ liệu production thành công.
