# Độ dễ dùng của PDF — 16/11/2026

TASK=PDF-USABILITY-20261116, local gates and independent source review passed; release pending.
BASE_SHA=38a92641678516b589dea84efc62ec99233a9766
BRANCH=codex/pdf-usability-20261116
TRACKER=Issue #689, contract comment6915436558.

## Thay đổi

Giữ hai SPEC_ID đã giao Antigravity Gemini3.8FlashHigh:
PDF-COMPRESS-LABEL-HELP-20261116 và PDF-GUARDED-CUSTOMER-COPY-20261116.
Hai proposal R1 đã có, không gọi lại; zero worker code faults.
Năm literal changes trong ba app files, hai ordered keys/sáu giá trị:

- Nén PDF: thêm đúng hai rule màu light cho label/help dùng portal-text/
  portal-muted. Không đổi font, bố cục, ô nhập, dark, opacity hoặc motion.
- Tách/Gộp/Nén PDF: ở nhánh chưa được xem công cụ, h2/p thành thông báo ngắn
  theo VI/EN/ZH, bỏ đúng cụm ba metadata nội bộ. Giữ guard strict, early return,
  icon/article/section và mọi ready forms/controls/quyền.

Portal LF `c1a4defe7b883d1b182198d60eab4353c3ace61f70d20d36aa4a6d64f30a6358`.
I18n LF `e52505655b14c640a7a9d68a6da912b78e24f6783fb61486799ff788429c7c8d`.
Theme LF `6a5028c129fc78bb701d7fd585fe3eb9776b8902a4948560e6debccbfb412f90`.
Nguồn ngoài đúng năm thay thế bằng BASE; không root-authored app repair.

## Bằng chứng

- BASE15tests:3PASS/12expectedRED,2213.4128ms; lỗi đúng guard copy/catalog/
  source/CSS chưa áp, không import/syntax/harness error.
- Một nhóm26tệp: **536 Node PASS /0FAIL /0SKIP**,40521.3514ms.
  Không chạy lại phần đã đạt.
- Actual full renderer ba công cụ/ba locale/quyền stricttrue,false,string,
  undefined/nguồn rỗng hoặc hai PDF; independent view/run/refresh quyền.
  Ready pages toàn HTML bằng BASE; guarded chỉ hai text slots+metadata removal.
  Dữ liệu/context/customer notes/filename bất biến, literal/escape một lần.
  Hostile translation, same-VM/fallback, ordered frozen two-key catalogue và
  unknown/missing/duplicate/value mutation guards.
- Exact five-edit forward/inverse/outside. Finite usability inverse trước
  Metrics→Display→PDF→Card→Date→Meta→Request→History; Compress EOF inverse
  trước Split/Chat CSS comparators. Old hashes/assertions không đổi.
- Native GREEN ba quan sát thực tế: Split375light, Split1440dark, Compress375light.
  Dùng lại ba mẫu native post-Split đã được xác minh làm BASE: theme BASE
  6679321f... hiện tại vẫn exact, summary SHA
  e5a0470ba674380fd4af7876d97106f2120ccd602925400194c55dbe763218b7.
  Không chạy lại baseline native đã có.
-10text samples; hai target Compress: label1.265330→12.351555:1,
  help2.021153→5.797099:1. Paint-chain/alpha/filter/blending/image checks đạt;
  control/font/geometry/other styles và hai Split light/dark sentinels exact.
  Một Compress field crop đã xem.
- Guarded copy chỉ actual-renderer VM proof vì QA thực tế đang cho xem công cụ;
  không fake quyền/API để tạo ảnh. Không nhận native blocked/final-output PASS.
- Chín product tables/schema, sáu plans/mười tám scenes/versions/idempotency,
 20source before/after/15original evidence hashes giữ; productwrites0/reseed0/
  egress0/provider0, ownedJob active0.
- Scope gate exit0:22protectedLF/allappPython/CIonecommand/nativebytebinding,
  exact current native source and reused BASE-theme provenance.

## Phần còn lại, không che giấu

Ready-page intro/aside/form/confirmation/history copy của ba công cụ vẫn có
chữ triển khai nội bộ; không được nhận đã sạch toàn trang từ guarded copy.
Crop Compress còn cho thấy phần tìm PDF có nhãn/trạng thái sát nhau và dòng
“Không có tham chiếu ở trang này” lặp ở footer rỗng. Hai phần này cần phiếu
riêng trước khi nhận whole-PDF/customer-ready. Chưa sửa trong đợt này.
Catalogue light owner/descriptions/fallback hub và các forms/headings khác
còn theo hàng đợi; full locale/responsive/AX/keyboard/auth/device/Safari/
signed production UI/real final output/M-FINAL01..06 mở, motion cuối.

PR748 trước đó đã giao: CI43857216020 hai nhóm SUCCESS;
merge/runtime38a92641678516b589dea84efc62ec99233a9766;
deploy43859221752 SUCCESS, services/health/five assets exact;
receipts Issue6915066642 / PR6915376473.
Source review độc lập C0/I0/M0, đúng ba frozen app hashes; không chạy lặp
Node/test/VM/native/scope gate. Tài liệu vận hành/đối chiếu gốc cập nhật;
Tester PDF-USABILITY-20261116 READY. Canonical case1431lines154298LFbytes,
SHA256f0d533ce13db9f7decfe435358a1b033c88196d136b39ac40be15c1e0104aab9;
changed metadata1PASS32deselected0.45s; historical remote/P0/labels/Projects
observations giữ, không nhận vừa revalidate remote. PUSH_GATE=READY.
Đợt PDF này chưa merge/deploy từ bằng chứng local.

FILES_CHANGED=3appfiles/tests/finite adapters/CIonecommand/docs.
BASELINE_FAILURES=12 expected; BRANCH_FAILURES=0; NEW_FAILURES=0.
PROTECTED_COMPARATORS=22LF/allappPython/outside/native data/theme/source.
PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_WRITES=0.
DEPLOY=NO for this unit; LIVE_PASS=NOT_TESTED for signed production UI/output.
BLOCKERS=Provenance/CI/release gates pending.
