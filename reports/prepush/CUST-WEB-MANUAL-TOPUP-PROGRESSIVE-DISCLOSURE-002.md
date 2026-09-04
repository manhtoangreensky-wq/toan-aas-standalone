# Báo cáo trước push — CUST-WEB-MANUAL-TOPUP-PROGRESSIVE-DISCLOSURE-002

Đang đọc và áp dụng skill owner-governed-codex cho task này.

```text
SPEC_ID=CUST-WEB-MANUAL-TOPUP-PROGRESSIVE-DISCLOSURE-002
STATUS=FINAL_LOCAL_VERIFIED_SHIP_READY
BASE_SHA=b657cea98ecc0c2f6f962bf82f1044333dfe427e
BRANCH=fix/cust-web-manual-topup-progressive-disclosure-002
PROVIDER_CALLS=0
PAYOS_LIVE_CALLS=0
TELEGRAM_LIVE_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
PUSH_GATE=OPEN
```

## 1. Review code và hành vi hiện tại

Runtime diff nằm trong `static/portal/portal.js`, `static/portal/portal.css`, `static/portal/portal-i18n.js` và đúng một session-cleanup call trong `static/portal/integration.js`; các file test nằm trong allowlist. `portal-theme.css`, `copyfast_api.py`, `copyfast_db.py`, `billing.py`, `copyfast_auth.py` là protected comparator `5/5`; Integration final `manual-topup-create` handler phải giữ byte-exact theo hunk comparator ở final gate.

Luồng candidate đo được:

1. Initial chỉ dựng amount, method và CTA xác nhận; instruction, destination, QR, payment code, hotline, reference và final submit đều vắng khỏi DOM.
   Danh sách lịch sử ở choose-state chỉ giữ request/status/amount/method; `reference` và `transfer_content` của record cũ cũng bị ẩn cho tới explicit confirm.
2. Input/select/label click không bị delegated form action chặn. Explicit confirm local kiểm amount/method; chỉ method VND có `request_enabled=true` và canonical same-origin QR của chính method mới qua admission. Confirm mount đúng một instruction/QR; `ACTION_EVENT=0`, manual POST `0`.
3. `USDT TRC20 / Binance` là option disabled/readable với đúng lý do “chưa hỗ trợ đối soát VND”; không confirm, không QR và không final submit.
4. Back/change xóa QR, instruction, reference và final submit cũ; muốn xem lại phải xác nhận lại.
   Chuyển manual→PayOS→manual xóa confirmation/reference nhưng giữ amount/method chưa xác nhận. Logout/bootstrap/account switch xóa toàn bộ draft `/wallet/topup`, gồm amount/method, nên không có dữ liệu form chảy sang signed account khác.
5. Final reconciliation giữ handler Integration hiện có. Executable Node/vm seam chạy nguyên `integration.js`, chỉ stub transport: đúng một POST `/payments/manual`, có CSRF + idempotency, payload amount/method/reference chính xác, projection `pending_admin_review`; không PayOS/provider/window-open/wallet/ledger call.

## 2. Bằng chứng đo được

| Gate | Candidate | BASE | Kết luận |
|---|---:|---:|---|
| Focused manual + Tester | `69 passed / 1 deselected / 0 failed` | — | Deselect duy nhất là POSIX file-mode assertion không áp dụng trên Windows |
| Node syntax + JSON | `3/3` + `2/2` | — | Portal/i18n/Integration parse; rendered/readiness JSON parse |
| Protected hashes | `5/5` | exact BASE | `portal-theme.css`, API, DB, billing, auth byte-identical |
| Integration comparator | `1+ / 0-`; handler byte-exact `true` | exact BASE | Chỉ thêm `/wallet/topup` session cleanup; create handler không đổi |
| Diff + credential pattern | exit `0`; match `0` | — | Không whitespace error; không credential-like token trong non-doc diff |
| Client → Integration seam | `1 passed` | — | Một POST, CSRF/idempotency/payload/pending projection đúng; transport duy nhất được stub |
| Enabled VND methods | `5/5` | — | Mỗi method đúng `1` card + `1` matching QR; other card `0`; QR load `5/5` |
| Locale × theme | `9/9` | — | VI/EN/ZH × light/dark/system; ZH document lang `zh-CN`; restore VI |
| Responsive | `5/5` | — | `1440/1024/768/390/360`; initial/confirmed overflow `0` |
| Initial/reset/relogin | `4/4` | — | Initial, back, lane return, logout/login đều QR/info/reference/final-submit `0` |
| Contrast light | `5.282 / 12.352 / 5.797` | — | small label / input text / input border đều vượt `4.5 / 4.5 / 3.0` |
| Contrast dark | `9.701 / 15.172 / 9.053` | — | small label / input text / input border đều vượt `4.5 / 4.5 / 3.0` |
| Disabled option | light `5.280`; dark `9.700`; opacity `1` | — | Computed native option color/background, không suy từ token |
| Focus + clip | mobile clearance `15.737px`; desktop `65.512px` | — | active element đúng `#manual-payment-methods-title`, heading nằm dưới sticky header và trong viewport |
| Confirm request ledger | `1` selected QR GET 200 | — | other QR `0`, manual POST `0`, failed request/HTTP 5xx `0` |
| Browser health | `0` | — | Framework overlay `0`; relevant console error/warning `0` |
| Rendered money boundary | `0` | — | Manual POST/final submit/provider/wallet/production mutation đều `0` |
| Local cleanup | `3/3` listener `0` | — | `18768=0`, `18769=0`, `18770=0`; viewport reset; agent-created tabs closed |
| History selective disclosure | RED `1F/1P` → GREEN `2P` | — | Hai sentinel `reference/transfer_content` không còn trong initial DOM; xuất hiện sau confirm |
| Session/lane cleanup | RED `2F` + lane RED `1F` → GREEN | — | Bootstrap/logout và manual→PayOS→manual không mang confirmation/reference cũ sang phiên/lane mới |
| Contrast corrective | RED `2F` → GREEN `2P` | — | currency label dùng muted ≥4.5:1; input/select border dùng muted ≥3:1; token resolve từ theme |

Pre-fix screenshots ngoài repo không còn là bằng chứng cuối vì có thể hiện history transfer code trước corrective. Final redacted receipt là `reports/prepush/CUST-WEB-MANUAL-TOPUP-PROGRESSIVE-DISCLOSURE-002-RENDERED.json`; receipt không chứa payment identifier, QR bytes, account credential hay customer record.

Lưu ý phép đo: Browser in-app dành `15px` cho thanh cuộn dọc ở trang dài; `scrollWidth-clientWidth` tạo false positive. Matrix cuối dùng `document/body scrollWidth-innerWidth` và kiểm nội dung thật, kết quả horizontal overflow `0` ở cả 5 viewport.

Codex Security scan `7e480a16-bb52-481c-b31b-73422e29fb65` đã lưu report/canonical artifact, nhưng authoritative workbench status là `failed` vì `manifest.scan.completedAt` không khớp completion timestamp sau một lần finalize bị ngắt bởi quyền SQLite. Không dùng artifact này để ghi security PASS.

## 3. Đối chiếu tài liệu gốc

`INITIAL_FEATURE_DOC=NOT_FOUND` sau phạm vi tìm đã ghi tại `TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md`. Nguồn cũ mô tả callback/manual payment Telegram và eager-render method cards; candidate không replay callback mà giữ API signed Web-local, đồng thời tách local confirm khỏi final reconciliation submit.

Các điểm tài liệu cũ không còn đúng đã được cập nhật:

- `/admin/login` responsive và motion customer đã accepted live tại runtime `b657cea…`.
- M03B progressive disclosure có final local rendered receipt; merge/deploy/live vẫn là gate riêng.
- USDT/Binance có mặt để discover nhưng disabled, không phải VND request authority.

## 4. Tester workspace

- Nguồn case đã thêm `WA-40`; hướng dẫn Tester đã đổi phạm vi thành `WA-01..WA-40`.
- Repo có đúng hai issue template: `01-case-test.yml`, `02-bao-loi.yml`.
- Tracker đã biết: issue #412; Project đã biết: `TOAN AAS Web App · Tester P0`.
- Read-only revalidation 04/09: `gh` account active; issue #412 OPEN; required labels `12/12`; local templates `2/2`. Tester Project đã verified ngày 03/09; lần đọc 04/09 bị chặn vì token thiếu `read:project`, không tự mở rộng OAuth scope và không tạo project cạnh tranh.

## 5. Cổng còn thiếu trước push

- [x] Security gate: authoritative plugin scan vẫn được ghi trung thực là terminal failed; independent fallback review trên exact final diff trả `0 Critical / 0 Important / 0 Minor`, `SECURITY_REVIEW_READY_FOR_SHIP=YES`.
- [x] Revalidate issue #412, labels `12/12`, templates `2/2`; metadata tách `local_metadata_updated_at=2026-09-04` khỏi `remote_verified_at=2026-09-03`. Project readback mới được ghi rõ blocked bởi missing `read:project`, không giả verified.
- [x] Independent final review trên exact diff trả `0 Critical / 0 Important / 0 Minor`, `SHIP_READY=YES`.
- [x] Fresh pre-commit: focused `69 passed / 1 deselected`, Node `3/3`, JSON `2/2`, protected `5/5`, Integration hunk `1+/0-` + handler byte-exact, diff/credential-pattern `0`; Tester metadata đã recompute.

Cho tới khi bốn mục trên có bằng chứng, `COMMIT=NO`, `PUSH=NO`, `PR=NO`, `MERGE=NO`, `DEPLOY=NO`.
