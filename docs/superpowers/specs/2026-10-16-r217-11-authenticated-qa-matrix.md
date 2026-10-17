# R217-11 — Authenticated QA matrix và bot-parity evidence

**Status:** `CLOSED_WITH_EVIDENCE` (CI authenticated matrix và artifact đã được đọc/đối soát)
**Wave:** W7

## Chặn CI hiện tại — 2026-10-17

Run `39023945997` trên HEAD `3e5cd367a48e8d673a16d5184b2a45946b3275b6` chưa vào được
ma trận authenticated QA: bước `Verify committed migration evidence` dừng vì
`reports/migration/preflight.json`/`web_inventory.json` ghi fingerprint `bf9084e4509b`
nhưng 284 tệp Web đủ điều kiện trên HEAD cho fingerprint `c9bbeab9d557`.
Đã refresh Web-only provenance tại chỗ; lệnh `--verify-web-evidence` trả `ok=true`, audit
SHA khớp HEAD và fingerprint đầy đủ là
`c9bbeab9d5578d42e371a96945f805fe4cc2b2b053897becfc7693591dd59491`. Vì run này fail trước
job authenticated QA, R217-11 vẫn mở và chưa có artifact `456/456`.

## Lỗi runner và bản sửa tiếp theo — 2026-10-17

Run `39024899449` đã qua `Verify Web App` nhưng R217-11 fail ở bước tạo fixture với
`sqlite3.OperationalError: no such column: locale`. Schema Web hiện tại tách locale trong
`web_account_profiles`; `web_accounts` chỉ giữ role và canonical identity. Runner đã được sửa
để cập nhật hai bảng đúng trách nhiệm: role/canonical theo `web_accounts.id`, locale bằng
upsert vào `web_account_profiles`. Contract nguồn khóa cả câu lệnh update đúng và cấm update
locale trực tiếp trên `web_accounts`. Artifact `456/456` vẫn chưa có; cần một CI run mới.

## Điều kiện mở

- URL/lệnh runtime QA cô lập, DB fixture tách production.
- Tài khoản `customer_qa` và `canonical_admin_qa` không có ví/provider mutation.
- Browser session có thể ghi DOM/screenshot/console/network/trace.

## Contract kiểm thử

Ma trận bắt buộc: customer + Admin × VI/EN/ZH × light/dark × 375/390/768/1440.
Mỗi route ghi title/heading/CTA/field, AX name, focus order, screenshot, console, network,
persistence sau reload và state transitions input/preflight/confirm/progress/result/recovery.

Routes tối thiểu: `/welcome`, `/dashboard`, `/features`, `/image/create`, `/voice/tts`,
`/music`, `/subdub`, `/tools/video`, `/video/create`, `/workboard`, `/campaigns`,
`/free-prompt-gallery`, `/wallet/topup`, `/admin`, `/admin/operations`, `/admin/payments`,
`/admin/customers`, `/admin/audit`, `/admin/support`.

`/voice/tts` là route Voice canonical hiện tại; `/voice/create` là alias legacy được giữ để
probe route tương thích và phải ghi cả requested route lẫn resolved route trong evidence.
`/admin/payments` là route quản trị thanh toán canonical hiện tại. `/admin/billing` là tên
legacy trong một số tài liệu cũ và chỉ được ghi nhận như một alias/probe riêng nếu runtime có
route chuyển hướng; không dùng nó để thay thế route canonical trong acceptance matrix.

## Cấm

Không đăng nhập production, không gửi form trả phí, không tạo job/provider call, không
approve top-up, không sửa DB production.

## Acceptance

- Có file result với URL/viewport/locale/theme/timestamp và pass/fail từng route.
- Các lane chưa có engine phải chứng minh guarded boundary, không ghi output PASS.
- Console không có error/warning mới; network không có provider/payment mutation.

## Verify

```powershell
python -m pytest tests/test_browser_runtime_gate.py -q
```

Nếu runtime không chạy ở máy dev, giữ trạng thái runtime mở và dùng job CI cô lập; không tạo
fixture ở production.

## Verification attempt 2026-10-17 (local, historical)

Bundled Python `3.12.14` was available, but the isolated runtime had no `fastapi`, `uvicorn`,
`pytest` or `websockets`. A temporary install outside the repository was attempted with
`pip install -r requirements-dev.txt`; the environment could not resolve `pypi.org`, ending
with `NameResolutionError`. The local QA server therefore did not start; this remains a local
runtime limitation only. CI is the authoritative isolated runtime for this matrix, and
production is not a substitute.

## Source fixture contract 2026-10-17

`tests/test_p0_webapp_spec01_auth_rbac_truth.py` now seeds an isolated Admin account with
`role_cache='admin'` and `canonical_user_id='canonical-admin'`, then checks the HTML shell for
the five canonical Admin child routes. The existing local bridge shortcut resolves that known
fixture identity without a Bot/provider request. The test is included in the bounded CI contract;
CI run `39021192324` passed. This proves route authority and shell availability only. The browser
route × locale × theme × viewport matrix remains open until the QA runtime dependencies are
available.

## CI runner contract 2026-10-17

`scripts/ci/run_authenticated_qa_matrix.py` là runner riêng cho R217-11. Nó khởi động
`app:app` trên `127.0.0.1` với SQLite và thư mục tài sản tạm, xoá các biến bridge/PayOS,
tắt các engine có thể tạo job, rồi tạo sáu tài khoản QA (customer/Admin × VI/EN/ZH). Mỗi
tài khoản chỉ được lưu trong DB tạm; runner không đăng nhập production và không gửi form
provider, thanh toán, ví, job hoặc delivery.

Job `authenticated-qa` trong `.github/workflows/webapp-quality.yml` chạy runner sau quality
gate, upload `r21711-authenticated-qa-matrix.json`, `screenshot-manifest.json` và 456 ảnh.
Contract nguồn `tests/test_r21711_authenticated_qa_runner_contract.py` khóa đúng 13 route
customer, 6 route Admin, 3 locale, 2 theme và 4 viewport trước khi chạy browser.
Artifact chỉ được coi là đạt khi có đủ `456/456` bản ghi, mọi bản ghi có route/locale/theme/
viewport/timestamp, DOM + AX + focus + screenshot + console + network + reload evidence,
không có lỗi console/warning, request ngoài origin, mutation bị cấm hoặc tràn ngang. Source
runner đã được kiểm tra cú pháp.

## Closeout evidence — 2026-10-17

CI run `39027760496` trên PR #647 hoàn tất `Success` trong `8m 13s`; job
`117382539076` (`Authenticated WebApp QA (R217-11)`) hoàn tất trong `5m 17s`.
Artifact `webapp-authenticated-qa-a311caf1913e7ab40361727a771a09d6eaf5ff5b` có digest
`sha256:334858235c9bb9ed67f4a5e3e093e1796bb8ce17ce32ca3bbc80f5cfc4911f38`; browser evidence
artifact `webapp-browser-evidence-a311caf1913e7ab40361727a771a09d6eaf5ff5b` có digest
`sha256:6e57d73522e244001908c88214484b8518380741ba70821e81c7871dba624d21`.

Đã đọc trực tiếp `r21711-authenticated-qa-matrix.json` và đối soát:

- `records_expected=456`, `records_completed=456`, `records_passed=456`, `records_failed=0`.
- `provider_calls=0`, `wallet_mutations=0`, `production_data_mutations=0`.
- HTTP non-200, route/locale/theme mismatch, console errors/warnings, page errors,
  failed requests, external requests, forbidden mutations và reload mismatch đều `0`.
- Predicate PASS của runner kiểm tra `horizontal_overflow=false`; 456/456 record PASS nên
  không có overflow failure.

Kết luận: R217-11 được `CLOSED_WITH_EVIDENCE`. Đây là bằng chứng DOM/AX/responsive và an
toàn QA cô lập, không phải bằng chứng real provider output, wallet approval, production
deployment hoặc LIVE; các phần đó vẫn ở spec riêng theo checklist.
