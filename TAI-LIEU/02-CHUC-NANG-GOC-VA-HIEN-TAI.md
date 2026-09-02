# Chức năng gốc và hiện tại — TOAN AAS Web App

> Mục đích: đối chiếu yêu cầu nguồn với hành vi có bằng chứng ở source hiện tại.
> Trạng thái production: manual top-up PR #417 đã deploy tại `9785541`; Auth hotfix PR #419 đã deploy tại `0dd8ffa`; signed money flow vẫn `LIVE_PASS=NOT_TESTED`.

## 1. Kết luận về tài liệu giai đoạn đầu

`INITIAL_FEATURE_DOC=NOT_FOUND`

Kết luận này chỉ áp dụng cho phạm vi tìm kiếm bounded dưới đây: không tìm thấy một tài liệu duy nhất là danh sách gốc đầy đủ cho toàn sản phẩm.
Nó không có nghĩa dự án thiếu tài liệu nguồn.
Các source contract, plan và matrix vẫn được dùng để đối chiếu từng yêu cầu.
Inventory kiểm soát phép đo: `reports/migration/p0-05-prepush-inventory.json`.
Inventory SHA-256: `b2f6549380826d2688fc648b46237acfe56d20d6512578dead00e3cd131cd7e3`.
Inventory đã được nghiệm thu tại P0-05B.

## 2. Phạm vi nguồn đã tìm

- `README.md` — runtime, configuration và authority boundary hiện tại.
- `docs/UX_APP_FIRST_REDESIGN.md` — product intent, guarded UI, navigation và PWA presentation boundary.
- `docs/migration/BOT_TO_WEB_INVENTORY.md` — snapshot command/callback/route/table ở thời điểm audit.
- `docs/migration/FEATURE_PARITY_MATRIX.md` — disposition tĩnh, không phải runtime equivalence.
- `docs/migration/README.md` — catalog contract migration.
- `docs/superpowers/plans/` — `123` tracked Markdown plan theo inventory P0-05B.
- `docs/superpowers/specs/` — `139` tracked Markdown spec theo inventory P0-05B.

## 3. Cách đọc trạng thái

- `✅`: hành vi/source contract hiện vẫn đúng trong source được chỉ ra.
- `⚠️`: hành vi đã có hoặc đã đổi nhưng còn local, guarded, chưa deploy/live hoặc khác tài liệu cũ.
- `❌`: source requirement không được dùng theo cách cũ; có boundary thay thế rõ ràng.
- Không dấu nào tự chứng minh production live.
- `COPIED_GUARDED` trong parity matrix không đồng nghĩa engine tương đương runtime.
- Matrix ghi runtime workflow-equivalence `0.0% NOT_STATICALLY_VERIFIABLE`; xem `docs/migration/FEATURE_PARITY_MATRIX.md:1-3`.

## 4. Bảng đối chiếu nguồn → hiện tại

| Yêu cầu/đoạn nguồn | Hành vi source hiện tại | Trạng thái | Bằng chứng |
|---|---|---|---|
| “signed workspace and operations application” | Web dùng signed session; integration fixture đăng ký/link/login các owner/Admin session thật. | ✅ Source đã deploy tại `9785541`; signed money flow chưa test. | `docs/UX_APP_FIRST_REDESIGN.md:5-12`; `tests/test_p0_manual_topup_cross_repo_integration.py:245-275` |
| Browser raw Telegram ID không phải auth | Telegram identity phải qua OIDC hoặc one-time Bot proof; Email/OAuth account không bắt buộc link ngay cho mọi Web-only surface. | ✅ Boundary hiện hành. | `docs/migration/TELEGRAM_WEB_CONNECTION.md:3-18`; `docs/migration/TELEGRAM_WEB_CONNECTION.md:31-39` |
| One-time link gắn cùng browser session | Link/account challenge dùng callback ký và CSRF; raw ID không được render thành quyền. | ✅ Source contract. | `docs/migration/TELEGRAM_WEB_CONNECTION.md:65-75`; `tests/test_p0_manual_topup_cross_repo_integration.py:245-275` |
| Bot là authority cho Xu/PayOS/provider/job | Web manual G1/G2 hiện độc lập cho metadata/QR/pending/history/Admin reject, nhưng Web vẫn không tự credit Xu hoặc tạo ledger thứ hai. Approve/ledger thuộc G0/G3 khóa riêng. | ⚠️ Candidate local; production signed/live chưa test. | `copyfast_api.py`; `copyfast_db.py`; `tests/test_cust_web_manual_topup_visible_qr_001.py` |
| Bot manual callbacks là `TELEGRAM_ONLY` | Web không replay callback/UID/bill state; P0 thêm API signed-session riêng thay vì chuyển callback sang browser. | ⚠️ Cách triển khai Web-native mới, không phải callback parity. | `docs/migration/MANUAL_PAYMENT_CALLBACK_CONTRACT.md:3-11`; `copyfast_api.py:4689-4763` |
| Customer manual create/history/detail/status | Web có bốn route owner-scoped Web-local; không phụ thuộc Telegram/Core Bridge. | ⚠️ Candidate local, protected matrix PASS; signed production chưa test. | `copyfast_api.py`; `copyfast_db.py`; `tests/test_web_manual_topup_unlinked_g1.py` |
| Admin manual list/detail | Web-local Admin đọc pending request theo safe field allowlist; không cần canonical Bot bridge. | ⚠️ Candidate local; signed production chưa kiểm. | `copyfast_api.py`; `tests/test_web_manual_topup_unlinked_g2.py` |
| Admin manual draft/confirm | G2 chỉ two-step reject; draft không mutate request/tiền, confirm reject atomic. Approve/custom Xu vẫn khóa G0/G3. | ⚠️ Candidate local; live money flow chưa chạy. | `copyfast_db.py`; `tests/test_web_manual_topup_unlinked_g2.py` |
| “No browser-supplied ... admin_id ... is trusted” | Forged query/body/header không thay canonical Admin ID từ session; denial không mutate ledger. | ⚠️ Đã kiểm temp-only, chưa live. | `README.md:238-244`; `tests/test_p0_manual_topup_cross_repo_integration.py:510-589` |
| Owner/Admin bearer phải tách | Owner bearer bị deny ở 4 Admin route; equal/missing Admin secret fail closed. | ⚠️ Đã kiểm temp-only; ENV production chưa rotate/configure. | `tests/test_p0_manual_topup_cross_repo_integration.py:597-637` |
| Confirm phải idempotent | Hai client confirm đồng thời chỉ tạo một canonical mutation; replay không double-credit. | ⚠️ Concurrency proof là 2 client trong fixture, không phải load benchmark. | `tests/test_p0_manual_topup_cross_repo_integration.py:481-505` |
| Safe owner/Admin projection | Owner output không lộ Admin/token/raw fields; Admin output theo allow-list; foreign owner nhận safe response. | ⚠️ Source/test local accepted. | `tests/test_p0_manual_topup_cross_repo_integration.py:380-420`; `tests/test_p0_manual_topup_cross_repo_integration.py:510-589` |
| Manual amount + payment code trên Web | Khách nhập amount; payment code là 8 chữ số bền vững của Web account, do signed server metadata cấp; browser/Telegram không override. | ⚠️ Candidate local; signed submission live chưa test. | `copyfast_api.py`; `copyfast_db.py`; `tests/test_cust_web_manual_topup_visible_qr_001.py` |
| QR ACB/MoMo/ZaloPay/USDT trên Web | 5 QR canonical nằm ngoài repo public trong private Web root; signed endpoint full-decode/bomb/size/identity/cache guard. Missing method hiện unavailable, không biến mất và không submit được. | ⚠️ Local Browser 5 viewport/5 image PASS; private asset production provision/deploy/live còn mở. | `copyfast_api.py`; `static/portal/portal.js`; `tests/test_cust_web_manual_topup_visible_qr_001.py` |
| Hotline tách biệt số tài khoản | Support fallback `0898360858`; bank account fallback `0387532320`; Portal/integration không hardcode phone/account. | ✅ Source deployed; live source marker verified. | `billing.py`; `copyfast_api.py`; `tests/test_billing_canonical_journey_contracts.py` |
| Role-specific note confidentiality | Customer response và customer JS state bỏ `admin_note`; authorized Admin projection vẫn giữ note. | ⚠️ Security reviewer local kết luận fixed; live chưa kiểm. | `copyfast_api.py`; `static/portal/integration.js`; `tests/test_p0_manual_topup_customer_flow.py` |
| Manual interaction sống qua hydration | Selected lane và amount/method/reference còn nguyên sau same-route data remount; invalid lane bị bỏ qua. | ⚠️ Source deployed; Node/rendered matrix `10/10` đạt, signed production interaction chưa test. | `static/portal/portal.js`; `tests/test_p0_manual_topup_customer_flow.py`; `evidence/p0-05e-primary-manager-verified-20260830.md` |
| Admin navigation là server-authorized directory | Browser role/query không tạo module; unavailable endpoint phải fail closed. | ✅ Contract hiện hành, độc lập với P0 manual write. | `docs/migration/ADMIN_ERP_NAVIGATION_CONTRACT.md:3-30`; `docs/migration/ADMIN_ERP_NAVIGATION_CONTRACT.md:57-63` |
| Guarded capability không được trông như ready | Portal phải hiển thị guarded/unavailable; static navigation không phải runtime engine claim. | ✅ Product/UI boundary hiện hành. | `docs/UX_APP_FIRST_REDESIGN.md:5-12`; `docs/migration/FEATURE_PARITY_MATRIX.md:1-3` |
| PWA chỉ cache public shell | Wallet/payment/Admin/API/download/private workspace vẫn network-only và ownership-checked. | ✅ Cache boundary hiện hành. | `docs/migration/PWA_ROLLOUT_VERSIONING_CONTRACT.md:3-8`; `docs/migration/PWA_ROLLOUT_VERSIONING_CONTRACT.md:51-61` |
| Production runtime là VPS | Runtime truth là GitHub main → Actions → Ubuntu VPS; Railway không phải runtime production. | ✅ Runtime `0dd8ffa`, Web/nginx active, health valid. | `README.md:5-12` |
| Auth logo và low-height card | Logo không co/crop; card/form giữ trong initial viewport và control tối thiểu 44px. | ✅ Đã deploy/live tại `0dd8ffa`; local rendered `6/6` là receipt trước ship. | `evidence/auth-login-brand-viewport-001-20260831.md` |

## 5. Chỗ tài liệu cũ không còn đúng

### 5.1 Manual payment cũ chỉ nói callback Telegram

`MANUAL_PAYMENT_CALLBACK_CONTRACT.md` đúng khi cấm replay callback vào browser.
P0-01..P0-04 không phá cấm đó; chúng tạo API private/signed riêng.
Vì vậy không dùng callback value, Telegram UID hoặc Bot deposit state làm browser action.
Tài liệu vận hành phải trỏ tới Web API/Bot internal route mới, không bảo khách nhập Telegram ID.

### 5.2 README chưa phản ánh P0 local source

README hiện nói Web không có manual-topup inbox và manual reconciliation vẫn qua `/thucong` tại `README.md:258-263`.
Source P0 local đã thêm owner/Admin route và cross-repo test.
Nhưng vì P0 chưa merge/deploy, README production statement chưa được sửa thành live claim.
Pre-push docs ghi song song: production hiện hành và local candidate khác nhau.

### 5.3 Số đo audit cũ không dùng cho source hiện tại

`BOT_TO_WEB_INVENTORY.md` ghi FastAPI route Web `694` tại `docs/migration/BOT_TO_WEB_INVENTORY.md:3-10`.
P0-05B đo lại source accepted bằng AST là `702`.
Hai số có thời điểm/phương pháp khác nhau; tài liệu hiện tại dùng số P0-05B và giữ định nghĩa đo.
Không diễn giải chênh lệch số route thành phần trăm hoàn thành sản phẩm.

### 5.4 Railway compatibility không phải production truth

Một số tên ENV/file compatibility vẫn chứa chữ Railway.
Production runtime hiện tại là VPS theo `README.md:5-12`.
Không xóa compatibility metadata trong spec tài liệu này.
Không dùng sự tồn tại của `railway.json` để tuyên bố runtime đã quay lại Railway.

## 6. Rác và giới hạn

- Root repo còn các prototype/legacy entry như `db.py`, `customer_api.py`, `erp_core.py` và HTML cũ; không tự mount hoặc xóa trong P0 docs.
- Shared Portal bundle lớn là debt đã biết; tài liệu không biến debt đó thành refactor ngoài scope.
- Feature parity matrix là static disposition, không phải bằng chứng runtime output.
- Một Web route tồn tại không chứng minh provider/job/output giao thành công.
- Guarded route là trạng thái đúng khi adapter hoặc ENV chưa sẵn sàng.
- Production database record count chưa đo trong static gate.
- Credential-like tracked paths của Bot còn chặn ship và được tách thành P0-05A.
- P0-05B ban đầu chưa query GitHub Project; P0-05E sau đó đã gắn PR #417 vào `TOAN AAS Web App · Tester P0` và readback thành công.

## 7. Không có trong tài liệu gốc

- Không có một master feature list duy nhất; feature source nằm rải trong README, migration contracts, plans và specs.
- P0 manual owner bridge/API riêng được bổ sung sau callback-only inventory.
- P0 Admin two-step receipt/confirm và scoped bearer separation được bổ sung để Web không giữ Bot token ở browser.
- Cross-repo temp-only test kết nối actual Web app với actual Bot ASGI app là bằng chứng mới của P0-05.
- P0-05B static inventory chuẩn hóa source identities, route placeholders, hashes, docs và Tester workspace.
- Auth brand/low-height viewport hotfix là bổ sung sau tài liệu gốc; không thay authentication behavior.
- Customer motion live-reopen bổ sung vocabulary quan sát được `180/360/680ms`, scroll reveal/stagger bounded, hydration không replay và reduced-motion fail-visible. `/features` vẫn giữ bundle split riêng, không quay lại full Portal bundle.
- P0 manual/Auth source đã qua Git/deploy; từng signed/money outcome vẫn cần cổng bằng chứng riêng. Motion còn local tại thời điểm capture.

## 8. Chưa triển khai hoặc chưa live

- P0-05A rotate/revoke và loại credential-like tracked paths: chưa làm.
- Tester source candidate có WA-01..36; WA-35/36 thuộc motion.
- PR #417 manual và PR #419 Auth đã merge/deploy; signed customer/Admin manual route vẫn chưa smoke bằng account thật.
- Customer motion live-reopen v2 đã local-render/Tester PASS; chưa merge/deploy trên main hiện tại và chưa có signed production acceptance.
- ENV/secret rotation: chưa làm.
- Signed production customer/Admin manual routes: chưa test.
- Provider/PayOS/Telegram live call: không chạy trong local acceptance.
- Live money flow: `LIVE_PASS=NOT_TESTED` và `LIVE_MONEY_FLOW=NOT_TESTED`.
- Production record counts: `NOT_MEASURED`.

## 9. Hướng dẫn đọc nhanh

- Muốn biết source identity, routes, hashes và số đo: đọc `reports/migration/p0-05-prepush-inventory.json`.
- Muốn biết customer behavior: đọc `tests/test_p0_manual_topup_customer_flow.py` và `copyfast_api.py:4689-4763`.
- Muốn biết Admin behavior: đọc `tests/test_p0_manual_topup_admin_queue.py` và `copyfast_api.py:4550-4675`.
- Muốn biết Web↔Bot outcome/idempotency/security: đọc `tests/test_p0_manual_topup_cross_repo_integration.py:380-698`.
- Muốn biết callback Telegram nào vẫn Bot-only: đọc `docs/migration/MANUAL_PAYMENT_CALLBACK_CONTRACT.md`.
- Muốn biết PayOS/wallet authority: đọc `README.md:236-263` và `docs/migration/PAYOS_WALLET_JOB_MAP.md:1-20`.
- Muốn biết Admin navigation authority: đọc `docs/migration/ADMIN_ERP_NAVIGATION_CONTRACT.md`.
- Muốn biết PWA private-data boundary: đọc `docs/migration/PWA_ROLLOUT_VERSIONING_CONTRACT.md:51-61`.
- Muốn biết customer motion v2: đọc `evidence/motion-webapp-surfaces-live-reopen-v2-20260831.md` và matrix JSON cùng tên.
- Muốn biết trạng thái ship: đọc checklist P0-05; không suy từ một file route hay HTTP 200.

## 10. Chân lý báo cáo

- Code tồn tại không đồng nghĩa test pass.
- Test local pass không đồng nghĩa merged.
- Merged không đồng nghĩa deployed.
- Deployed không đồng nghĩa live outcome.
- HTTP 200 không đồng nghĩa quyết định tiền hợp lệ.
- Mọi claim provider/output/payment phải có bằng chứng output cuối tương ứng.
- P0 manual source đã deploy tại `9785541`, Auth layout tại `0dd8ffa`; không suy signed/money LIVE từ deploy. Customer motion v2 mới local-verified, chưa ship.
