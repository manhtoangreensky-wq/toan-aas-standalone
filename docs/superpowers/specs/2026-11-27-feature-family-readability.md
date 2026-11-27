# FAMILY-READABILITY-20261127 — prerequisite của FCH

Đang đọc và áp dụng skill owner-governed-codex cho task này.

BASE `363d6ca55081eea4089ebf489cd183b09ba1aa96`;
branch `codex/feature-family-native-chrome-20261127`; cùng tracker Issue689.
Không tạo batch/PR cạnh tranh. FCH21records đã review được giữ khóa.

## READ và root cause

96 cảnh actual family renderer qua HTTP, CSS/SVG thật, dữ liệu giả:
5100 mẫu đo, 102 finding màu, không lỗi console/page/overflow/egress.
48 focus-link sáng đạt1,0304:1;48 current-marker tối đạt2,4761:1;
6 đoạn hướng dẫn rỗng sáng đạt3,0115:1. Đối chứng BASE ba cảnh tái hiện
đúng ba loại lỗi; CSS hiện tại bằng BASE, không phải hồi quy FCH.
Đo bổ sung ba cảnh xác nhận eyebrow sáng đạt1,40996:1.

Nguồn: `portal.css` giữ màu hover/focus sáng cũ; current-marker dùng
action-token tối trên surface-soft; paragraph dùng muted trên nền pha tối;
eyebrow còn màu mint sáng từ rule chung. Không đổi token toàn cục.

Evidence local: `family-chrome-browser-physical-nov27-r2/summary.json`,
`family-chrome-browser-physical-nov27-baseline/summary.json`,
`family-chrome-browser-physical-nov27-color-probe/summary.json`.
Giới hạn: không auth hydration/full sidebar/header/client lifecycle,
thiết bị/Safari/motion hoặc UI production đã đăng nhập.

## CONTRACT

- GOAL: chữ của bốn vai trò đọc được ở cả nền sáng/tối và trạng thái tương tác.
- SCOPE: trang nhóm `/features/{family}`, không `/features` gốc.
- ALLOWED_APP: `static/portal/portal-theme.css`, chỉ bốn rule màu chữ.
- ALLOWED_QA: test readability mới, đăng ký CI, fixture/evidence CSS nếu cần.
  Finite CSS historical leaf JS/Python mới và hai hook trong
  feature-catalog-full-bundle135-historical.mjs / Python tương ứng; chỉ
  đảo bốn rule đã duyệt để các comparator lịch sử giữ nguyên pin/assertion.
- PROTECTED: FCH JS/i18n21records; CSS cũ nguyên byte; mọi route/guard/data/
  form/action/ARIA/outline/background/border/font/size/layout/motion; root
  Features, auth, Bot/engine/provider/wallet/PayOS/ENV/schema/productiondata.
- ACCEPTANCE: text≥4,5:1; focus≥3:1; targets≥44px;0new errors/overflow/
  egress; chỉ bốn declaration `color`, token theme có sẵn.
- STOP: proposal ngoài selector/declaration; protected diff; lỗi chưa đo.
- PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_WRITES=0.

## Hàng đợi độc lập

| SPEC_ID | Kết quả duy nhất | Dependency | Risk/run | Gate |
|---|---|---|---|---|
| FCR-LINK | Link sáng hover/focus dùng text-token | RED đã đo | SIMPLE/proposal-only | text≥4,5 |
| FCR-CURRENT | Marker nhóm hiện tại tối dùng text-token | RED đã đo | SIMPLE/proposal-only | text≥4,5 |
| FCR-EMPTY | Paragraph rỗng sáng dùng text-token | RED đã đo | SIMPLE/proposal-only | text≥4,5 |
| FCR-EYEBROW | Eyebrow sáng dùng text-token | RED đã đo | SIMPLE/proposal-only | text≥4,5 |

Owner đã yêu cầu nhiều session4.0ExtraHigh độc lập. Bốn session chỉ trả
đề xuất ở thư mục riêng, không chung mutable state; root là bên duy nhất
tích hợp CSS. Không dùng model cũ, không đăng nhập mới hoặc đổi settings.

Selector bắt buộc có `[data-portal-main][data-portal-presentation-route="default"]`
và `> .portal-page:has(> .portal-feature-jumps)`; chỉ family renderer có
navigation trực tiếp này. Root catalog có navigation trong controls và
presentation-route=features, không match. Không thêm class hoặc sửa JS.
Mỗi rule chỉ `color: var(--portal-text);`. Giữ màu nền và outline hiện tại.

## Checklist trước BUILD

- [x] Ba lỗi cũ tái hiện bằng BASE browser; eyebrow đo bổ sung; CSS BASE bằng current.
- [x] Tracker7202275592 đăng đúng repo/branch/BASE và đọc lại.
- [x] Bốn proposal R1 riêng có toàn MAP; không application writes.
- [x] QA RED5source vàbrowserroles trước CSS integration.
- [x] Root review gộp, tích hợp nguyên proposal hợp phạm vi.
- [x] Chạy failed/affected browser: hover/focus/current/empty/eyebrow,
  VI/EN/ZH,375/1440,light/dark; không lặp semantic541case.
- [x] Source5/Nodeleaf12/Pythonleaf9/CSSconsumer19PASS;reviewC0I0M0;
  closurecũ2533PASS vàfiniteinverseCSStrảđúnginputBASE.
- [ ] Docs/Tester/manifest/CI/merge/Web-only deploy/runtime/assets/cache/receipt.

## Verify của root

`node --test tests/feature-family-readability.test.mjs`
→0fail/skip sau khi tạo QA trước CSS integration.
Browser riêng dùng Chrome có sẵn/Playwright qua localhost, không cài thêm;
chạy cùng phép đo RED rồi GREEN và giữ minh bạch giới hạn.
Đổi rule màu chỉ mở kiểm tra CSS/ảnh hưởng, không review lại21copy/810entry.

Mọi mục chưa có evidence tiếp tục mở; chưa commit/push/deploy batch này.

GREEN:96views/5196samples,mintext4,987079411628882/focus5,409547285826742/
target44;0finding/error/egress/unmeasured/overflow.4rootviews0match.
EMPTYtransporterror0turn gửi lại nguyênphiếu thànhcông;khôngworkerfailure.
Browser/serverđãđóngfinally,exit0;ảnh375sáng/tốiđãxem.
