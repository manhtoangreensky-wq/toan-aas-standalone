# PDF-USABILITY — 16/11/2026

Đang đọc và áp dụng skill owner-governed-codex cho task này.

GOAL=Chữ Nén PDF dễ đọc trên nền sáng; thông báo khi chưa mở được ba công cụ
PDF ngắn, đúng VI/EN/ZH, không có giải thích vận hành nội bộ.
BASE_SHA=38a92641678516b589dea84efc62ec99233a9766
BRANCH=codex/pdf-usability-20261116
TRACKER=Issue #689, checklist mẹ hiện có.
DEPENDENCY=PR748 đã giao: exact-head CI43857216020 hai nhóm SUCCESS;
tested/merged treea917eb36475ff68540a58f0492b21705535875a0;
merge/runtime38a92641678516b589dea84efc62ec99233a9766;
deploy43859221752 SUCCESS; services/health/năm HTTPS assets exact;
receipts Issue6915066642 / PR6915376473.

## Hai spec độc lập trong một đợt PDF

| Spec giữ nguyên | Kết quả chính | Trạng thái đầu đợt |
|---|---|---|
| PDF-COMPRESS-LABEL-HELP-20261116 | Hai rule màu light cho label/help Nén PDF, không đổi bố cục | Antigravity R1 đã trả đúng, chưa áp/QA |
| PDF-GUARDED-CUSTOMER-COPY-20261116 | Ba guarded returns dùng hai khóa dịch, bỏ ba cụm metadata dư | Antigravity R1 đã trả đúng, chưa áp/QA |

Giữ nguyên cả hai SPEC_ID và worker history. Không gọi lại worker đã hoàn
thành, không reset lỗi; cả hai zero worker faults. Một nhóm nghiệm thu cuối
cho hai phần không đè nhau; không mở spec phụ thuộc khi acceptance còn lỗi.
Antigravity dùng Gemini3.8FlashHigh theo danh sách model đo trên CLI hiện có.

## Phạm vi khóa

ALLOWLISTapp=static/portal/portal-theme.css, static/portal/portal.js,
static/portal/portal-i18n.js.
Chỉ năm literal changes đã có: CSS1 → guarded JS3 → catalog1.
CSS thêm hai rule `html:not([data-portal-theme="dark"])` trong đúng
`.portal-page.portal-pdf-optimize`; chỉ color=portal-text/portal-muted.
Guard copy chỉ thay h2/p và bỏ state-meta ở nhánh chưa được cấp công cụ;
không thay conditions/earlyreturns/icon/article/section/ready forms/rights.
Catalog chỉ thêm hai ordered keys × ba locale = sáu giá trị.

Tests mới: tests/pdf-usability.test.mjs,
tests/helpers/pdf-usability-runtime.mjs,
tests/helpers/pdf-usability-snapshot.mjs,
tests/fixtures/pdf-usability-reviewed.json.
Adapters hữu hạn, giữ old hashes/assertions:
tests/helpers/document-card-metrics-runtime.mjs và snapshot.mjs đảo đúng
guard copy trước Metrics/Display/PDF/Card/Date/Meta/Request/History;
tests/pdf-split-readability.test.mjs và helpers/pdf-split-readability-snapshot.mjs
đảo đúng Compress EOF addition trước Split/Chat CSS comparator.
CI chỉ thêm một command. Docs/Tester/cases/checklist/metadata/provenance cập nhật.

PROTECTED=All app Python/backend/auth/CSRF/ENV/schema/DB/production data/
integration/portal.css/motion/theme JS/service worker/Bot/engine/provider/
wallet/PayOS. Không đổi font/layout/geometry/controls/opacity/display/
validation/options/upload/download, chức năng sẵn có, tên/nội dung khách,
13 metric keys hay tên/lựa chọn/ngày vừa giao.
Không tạo retry action giả, thông báo thành công giả hoặc output giả.

## Acceptance và bằng chứng bắt buộc

- [x] PR748 đã giao trước BASE; tracked clean, giữ Owner state untracked.
- [x] Hai proposal R1 có SHA binding, đã trả đúng; chưa áp/QA.
- [x] Fixture gắn đúng năm literal changes/ba app hashes/BASE.
- [x] BASE3PASS12RED đúng chữ guarded/CSS, không import/syntax/harness lỗi.
- [x] Exact five-edit forward/inverse, whole outside bằng BASE.
- [x] Actual full renderer ba công cụ × ba locale: quyền strict true/false/
  string/undefined; dữ liệu rỗng/đã chọn và customer notes/tên giữ literal.
  Ready pages toàn HTML bằng BASE; guarded chỉ đổi đúng hai text slots và
  bỏ đúng metadata, toàn phần còn lại bằng BASE.
- [x] Guarded title/body đúng locale; hostile translation escape một lần,
  same-VM/fallback/frozen two-key order; missing/unknown/value changes bị chặn.
- [x] CSS source đúng EOF addition hai rule, không màu/phạm vi/motion khác.
- [x] Một nhóm26tệp536NodePASS/0FAIL/0SKIP40521.3514ms, không chạy lặp.
- [x] Native GREEN ba quan sát: Split375light và Split1440dark là sentinel,
  Compress375light là target; một Compress field crop đã xem.
- [x] Contrast target label/help12.351555/5.797099:1 sau paint-chain/opacity/alpha checks;
  geometry/font/control và sentinel nguyên vẹn.
  BASE dùng lại chính ba mẫu native GREEN của đợt Split đã kiểm trước đó
  (Compress lúc đó là sentinel chưa sửa). SHA summary
  e5a0470ba674380fd4af7876d97106f2120ccd602925400194c55dbe763218b7;
  theme BASE6679321f8799acbb98dd65099372a7e6e31c2dfdcf4ffc530d665b254bc93440
  vẫn byte-exact hiện tại. Không chạy lại baseline native đã có.
- [x] Guarded copy VM-only vì backend QA đang cho công cụ ready; không fake
  API/quyền để chụp trạng thái. Không nhận native blocked/output từ mẫu VM.
- [x] Product tables/schema/plans/scenes/source/evidence giữ; product writes0/
  reseed0/egress0/provider0/money0; ownedJob active0.
- [x] Source review C0/I0/M0,22protectedLF/allappPython/nativebytebinding/
  CIonecommand; docs hiện tại/đối chiếu gốc/Tester READY.
  Case1431lines154298LFbytes, metadata1PASS32deselected0.45s.
- [ ] Web provenance cuối.
- [ ] Exact-head CI hai nhóm → tested merge tree → exclusive deploy →
  runtime/services/health/năm assets → receipt cùng Issue/PR.

TESTS=`node --test tests/pdf-usability.test.mjs` và nhóm chain affected một
lượt cuối. Native chỉ chạy trên localhost QA sở hữu, cấm production browser.
STOP=OLD/hash không khớp, ngoài allowlist, verification lỗi hoặc cần protected
mutation. Chỉ root điều phối/nghiệm thu; app patch là proposal Antigravity.
Full locale/responsive/AX/keyboard/auth/device/Safari/signed production UI/
real final output và M-FINAL01..06 vẫn mở, motion cuối.
