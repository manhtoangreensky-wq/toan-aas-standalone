# IMAGE-COMPOSER-NATIVE-LOCALE-20261126

Đang đọc và áp dụng skill owner-governed-codex cho task này.

BASE/runtime `6ec003dbf8f80739f5fb93ff7bd1d7cc703c6792`;
nhánh `codex/image-composer-locale-20261126`, Issue689.
Dependency màu đã phát hành: PR809, CI45662670051 hai job đạt,
deploy45667062174; runtime/nguồn sạch/3dịch vụ/health/5+5assets,
receipt689/7169893110 và PR809/7169894142 đều đọc lại đúng.

## Kết quả cần đạt và phạm vi khóa

Trang Soạn mô tả ảnh dùng đúng VI/EN/ZH cho chữ cố định, không ô giải
thích/ô chỉ số trống hoặc cột bị bỏ trống. Giữ bảy trường và20giá trị
option, quyền/disabled/limits/ARIA/actions/routes, draft/no-transient/
session/escaping và nội dung tùy ý của khách. Ngôn ngữ mô tả đầu ra
do khách chọn không bị ngôn ngữ giao diện ghi đè.

Fixture `tests/fixtures/image-composer-native-locale-contract.json`
chứa nguyên39OLD/NEWrecord đã nhận từ11session
`gemini-4-hydrogen-xhigh`:20UI gồm catalogue1/fields6/result2/frame2/
metadata2/nav6/receipt-normalization1;19câu cố định Web gồm17literal
và2prefixdanhmụcVI. Có85key mới và6title-row sẵn có. Các source hash
trước/sau gắn BASE cố định; không được sửa record để làm test đạt.

39record ban đầu chỉ bốn tệp; điểm nối receipt được mở riêng bởi phụ
lục bên dưới, không tự mở các luồng khác:

- `static/portal/portal.js`: chữ/khung riêng Composer và return-shape
  của normalizer receipt; không đổi điều kiện chấp nhận hoặc hàm chung.
- `static/portal/portal-i18n.js`:85key VI/EN/ZH cân bằng, sáu nhãn có sẵn.
- `static/portal/portal-theme.css`: một rule grid riêng customer Composer.
- `copyfast_image_studio.py`: chỉ literal VI/tuple/dict VI đã liệt kê;
  cấu trúc AST ngoài string, EN, model/validator/endpoint/luồng ghi giữ.

QA allowlist: fixture/test mới, helper finite historical mới trong JS/
Python, điểm nối tối thiểu ở reader lịch sử, kỳ vọng chữ VI hiện có
trong `tests/test_copyfast_image_prompt_composer.py`, tài liệu/Tester/
readiness/cases và đăng ký test trong quality workflow. Mọi amendment
khác phải ghi trước khi sửa; không đổi assertion bảo mật hay pin cũ.

Điểm nối QA cụ thể: `tests/helpers/image-studio-validation-historical.mjs`
(source/snapshot), `tests/helpers/image_studio_locale_copy_historical.py`,
`tests/free-tools-readable-colors.test.mjs`,
`tests/image-studio-root-heading.test.mjs`,
`tests/image-studio-validation.test.mjs`,
`tests/test_image_prompt_composer_portal_contracts.py`. Chỉ thêm input
inverse trước assertion lịch sử; acceptance mới luôn đọc raw. Không
đổi kỳ vọng/hash/predicate cũ để bỏ lỗi. Helper mới đã kiểm7/7case
trước BUILD, giữ prefix/suffix/internal unknown, dictionary và lỗi lạ.

Cấm Bot/route-engine/provider/ví/PayOS/ENV/secrets/schema/dữ liệu thật,
shared renderer/factory signatures hoặc motion. Không tạo công việc
thật, ảnh, QR hoặc request trả phí. Không viết lại ghi chú khách hiện có.
Mười state cũ giữ nguyên; không đọc/chạm `LOCALE-CAMPAIGN-20261108.yaml`.

## Bằng chứng proposal, chưa phải nghiệm thu vật lý

Sáu session đầu:19UIrecord,6locale/permission states,18metadata route
khác giữ; receipt prerequisite thêm1record,138function checks gồm
12idempotence/126rejection parity và12bootstrap-render. Preview gộp
45case dùng dữ liệu custom không đủ nhận built-in goal hoàn chỉnh.
FrameOLDanchor sai cùng một dấu gạch chéo qua2vòng; root chỉ sửa OLD
từ source thật, NEW worker không đổi. Các session khác0codefail.

Bốn session câu Web cố định trả19record; ASTngoàistring giữ,compile
đạt,15pure-helperchecks giữ EN/customer;10giá trị danh mụcVI đổi,
keys/order/shape/EN/TikTok giữ. Không có app write ở các preview.
Nguồn và MAP đã được xác minh công khai bằng GitHub blob trước khi gửi.

## Thứ tự và checklist

Chia chi tiết thành từng spec kèm kết quả để qua spec sau; proposal đơn
giản độc lập được giao song song, tích hợp phức tạp chạy tuần tự.

1. COMP-RECEIPT: receipt hợp lệ sống qua normalizeBootstrap/render,
   mọi predicate cũ và126rejection giữ. Không suy backend persistence.
2. COMP-TEXT:19record literal VI cho mục tiêu/phong cách/nội dung mẫu;
   EN/customer interpolation giữ, keys/models/validators/AST giữ.
3. COMP-UI:20recordUI hoàn chỉnh; locale/controls/guards/customerdata/
   page metadata và layout riêng không ảnh hưởng QuickPlanner/route khác.
4. COMP-VERIFY: built-in3goal×2output languages×3UIlocales, custom,
   empty/guarded/ready/result/receipt/invalid, drafts/session, browser.
5. COMP-SHIP: tài liệu/Tester/provenance/CI/merge/deploy/runtime/assets/
   receipt; không mở PR rời khi local chưa đủ cổng.

- [x] Dependency PR809 đã phát hành và biên nhận đọc lại.
- [x] Proposal/code/model/nguồn công khai và preflight19+20record đủ.
- [x] FixtureBASE+39record và hash bốn tệp; chưa sửa ứng dụng.
- [x] RED nguồn vật lý/renderer:7ca/7fail đúng hash/title chưa sửa,
  không skip hoặc lỗi khởi tạo; `image-composer-physical-red-nov26.xml`.
- [x] Helper inverse hữu hạn7/7case; giữ byte lạ/duplicate/missing/oldassertions;
  nguồn nghiệm thu hiện tại phải đọc raw không chiếu.
- [x] Áp đúng39record/bốn tệp. GREEN nguồn/renderer7/7,0fail0skip;
  `image-composer-physical-green-nov26.xml`. Pycompile,JSsyntax,diffcheckexit0.
- [x] COMP-RECEIPT/TEXT/UI đạt source/unit/renderer và protected
  comparators trong phạm vi; không thay full app/auth/API bằng chứng.
- [x] COMP-VERIFY component48view và review gộp; hai delta quan trọng
  được sửa, focused reviewC0/I0/M0; full-app draft/auth vẫn kiểm riêng.
- [ ] COMP-SHIP đủ từng bằng chứng; signedUI/thiết bị thật/Safari và
  toàn-app locale/AX/auth vẫn giữ riêng nếu chưa có evidence.

### Bằng chứng bổ sung và điểm nối receipt

- Receipt portal-only:150/150case gồm138valid/rejection và12bootstrap/
  render; kết quả không chứng minh đoạn integration nhận API.
- Real Webbuilder+Pydantic:26goal/preset/language tổ hợp; tiếng Anh bằng
  GitBASE, VI không còn từ Anh cố định sau khi tách đúng chuỗi khách.
  Fixture26DTO được buộc hash source và kiểm lại bằng builder thật.
- Renderer:258/258case gồm246viewresult/capability/selection/locale và
  12caseguard/escaping. Giữ đúng ngôn ngữ đầu ra và customer text.
- Python source/model group11/11. Không cộng lặp26tổ hợp vào số test.
- HTTP cục bộ chạm300giây ở testcase đầu,0case hoàn tất; đúng PID QA
  đã kết thúc. Không nhận PASS hoặc cùng-baseline; không rerun để làm xanh.
  Quality workflow có thêm cổng Ubuntu API10case có hạn8phút và nhóm
  source/model10+1case; tất cả phải đạt trước merge.

Phụ lục `2026-11-26-image-composer-receipt-integration-amendment.md`,
Issue689/7170804673 mở thêm đúng một return-object trongintegration.js.
39record gốc giữ nguyên; record mới ở `amendments` riêng, source pin
bổ sung thành năm tệp. AntigravityR1 trả đúng, toàn predicate giữ;
nhóm pipeline/raw-source/inverse29/29 đạt sau apply.13case pipeline đã
đi qua acceptor→bootstrap→renderer, có85invalid flag observations.
Đây là bổ sung phần thiếu trong spec, không codefail worker cũ.

15key phản hồi VI/EN/ZH và24nhãn ghi chú mới VI/EN đã áp dụng qua
phụ lục riêng,45nhánh hành động và110formattercases đạt. Không dùng
40record trước phụ lục làm bằng chứng cho phần mới; tổng hiện53record.

### Bổ sung QA cho composition sau51record

Nhóm29sourcefiles đã kết thúc với557observations,555pass/2fail.
Hai lỗi QA: reader `image-studio-validation.test.mjs` còn đọc rawintegration
trong assertion lịch sử; testmutationCSS của inverse mới chưa chấp nhận
việc sửa nestedrecord bị từ chối bằng assertion thay vì trả source.
Sửa đúng readerinput/testclassifier, giữ oldassertions và pins; không app edit.
ReaderPython `tests/test_free_tools_readable_colors_historical.py` cũng
cần chiếu Composer trước rawphysical comparison lịch sử của đợt màu.
RawacceptanceComposer không chiếu; unknown outside records vẫn giữ.

## Lệnh và chứng cứ bắt buộc

`node --test tests/image-composer-native-locale.test.mjs`: trước BUILD,
nguồn bốn tệp và renderer ba locale phải RED; sau BUILD tất cả đạt.
Giữ file này làm acceptance raw-source độc lập, không gắn inverse.

`python -m py_compile copyfast_image_studio.py` →exit0.
`python -m pytest -q tests/test_copyfast_image_prompt_composer.py`
trên SQLite tạm do test tự tạo, không production; kỳ vọng chữ VI cập
nhật đúng contract, EN/guard/persistence/idempotency/ownership giữ.
`python -m pytest --noconftest -q tests/test_image_prompt_composer_portal_contracts.py`
giữ assertion cũ qua input inverse hữu hạn nơi source copy thay.

Renderer/normalizer nhận dữ liệu đầy đủ từ schema Web:3goal built-in
product/ad/cinematic ×2outputlanguagevi/en,85key locale cố định, quyền
compose/save bật/tắt,4selectionindices,receipt hợp lệ và tất cả flag
không hợp lệ. Nội dung khách chứaFacebook/TikTok/media/studio và HTML
phải thoát đúng, không bị thay chữ hay chạy mã.

Trình duyệt360/375/768/1440×sáng/tối×VI/EN/ZH: chữ đo được≥4,5:1;
focus≥3:1, input≥16px, mục tiêu chạm≥44px khi áp dụng; không tràn.
Đo disabled/gradient không chắc riêng, không tự nhận toàn-app conformance.
Kiểm field focus/dynamic fields/keyboard/draft/error redraw/session.
Không bấm tạo job/provider hoặc save dữ liệu thật.

## Lịch sử trước phụ lục ghi chú

Thân ghi chú do Web tự dựng còn heading/metadata cố định kỹ thuật ở
`_image_prompt_composer_memory_note`; không được coi39record đã sửa
phần đó. Cần kiểm hiển thị và contract riêng nếu sửa, giữ category/tags/
IDs/index/idempotency/luồng ghi và ghi chú cũ. Không thay mù nội dung
khách đã lưu. Motion vẫn là bước cuối của goal mẹ.

## Trạng thái cuối cục bộ trước phát hành

39record gốc bất biến+14amendments/năm source.100key UI/feedback cân
bằng VI/EN/ZH;24nhãn note theo outputVI/EN. Finalraw/history19,
other-route18 và freshfixturebuilder1 đạt; functional488 tại50record,
ba record sau chỉCSS. Nguồn557observations có2QAfail, phục hồi224/224;
Pythonhistorical18/18. Không cộng lặp hoặc gọi là freshfullsuite.

Physical-r8-final48view có2112enabledtextsamples,min5,4733;
placeholdermin5,5225;24focusmin5,8601và2px;0finding/error/external/
overflow. Browser chỉcomponentHTTP, không auth/API/persistence.
ReviewC0/I2/M0 ban đầu, correctionC0/I0/M0. Tester/operations/feature
comparison/10case đã cập nhật. CI đúng HEAD, HTTPUbuntu10functions,
merge/deploy/runtime/assets/receipt vẫn là các cổng cần hoàn thành.
