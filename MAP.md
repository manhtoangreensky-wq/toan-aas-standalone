# MAP — TOAN AAS standalone WebApp
> Rà lại 20/11/2026 trên BASE `e49427e5` và thay đổi UI V07 đang nghiệm thu. FastAPI/Python + vanilla JS/CSS. Gốc: `_webapp-r218-voice`.
> Bản đồ được đính kèm nguyên văn vào phiếu Builder; không thay việc đọc source.

## 1. Module và vai trò
- `app.py`: ứng dụng FastAPI đang chạy; mount routes/API/static.
- `copyfast_pages.py`, `templates/portal_shell.html`: shell và asset build stamp.
- `copyfast_api.py`, `copyfast_bridge.py`: projection allowlist/bridge tới nguồn chuẩn.
- `copyfast_auth.py`: signed session, CSRF và quyền; không đổi trong UI batch.
- `static/portal/portal.js`: renderer, lựa chọn và draft giao diện.
- `static/portal/integration.js`: hydrate GET/API action và stale-response fences.
- `static/portal/portal-i18n.js`: chữ cố định VI/EN/ZH.
- `static/portal/portal.css`, `portal-theme.css`: bố cục và theme xanh/navy/ngọc.
- `copyfast_*.py`: các workspace Web độc lập theo sản phẩm.
- `tests/`, `scripts/ci/`: contracts và QA DB tạm; không chứng minh provider LIVE.

## 2. Entry points
- `app.py:app`: runtime VPS `toanaas-web.service`.
- `portal.js` + `integration.js`: mount/hydrate sau server shell.
- `scripts/ci/run_authenticated_qa_matrix.py`: server QA cô lập, không production.
- `.github/workflows/webapp-quality.yml`: CI source/browser/đăng nhập.
- `.github/workflows/deploy-vps.yml`: dispatch exact SHA tới `/opt/toanaas/webapp`.

## 3. Dùng chung từ ba nơi
- `copyfast_auth.require_account`: import/consumer ở nhiều module `copyfast_*.py`.
- `copyfast_auth.require_csrf`: cổng action ghi của các workspace; giữ nguyên.
- Đo 20/11: `require_account` có trong 46 tệp Python ngoài tests; `require_csrf` trong 44 tệp.
- `portal.js:safeText`, `uiText`: nhiều renderer cùng bundle; không đổi chữ ký.
- `integration.js:api`, `merge`: nhiều hydration/action; chỉ sửa nhánh allowlist.
- `integration.js:vaultFeedbackText`: 39 chỗ gọi trong Kho tệp; dịch câu cố định, không đổi nội dung tùy ý.

## 4. Luồng dữ liệu
- Signed page → shell → auth/bootstrap → GET projection → normalize → renderer.
- Catalog giá/gói: bridge → allowlist → approved SKU/version → read-only cards.
- Manual top-up: GET options → chọn method/amount → xác nhận local → QR → POST riêng.
- API options và history là hai nguồn khác nhau; không dùng history state làm options state.
- Bản nháp: mã `feature_key` giữ nguyên; nhãn qua `featureCatalogText` theo locale, không đổi DTO.
- Kho tệp: epoch/route/selection hiện có → kết quả đọc hiện tại → phản hồi đúng locale; phản hồi cũ im lặng.

## 5. Điểm nhạy cảm
- Auth/CSRF: `copyfast_auth.py`; session epoch guards trong `integration.js`.
- Tiền: `billing.py`, `copyfast_api.py`; UI không tính giá hoặc cộng Xu.
- DB/ENV/secret/QR gốc: ngoài scope; không đọc/gửi worker dữ liệu thật.
- Provider/engine/Bot/route-engine: giữ T0; UI PASS không đồng nghĩa đầu ra thật.
- Deploy: backup/source SHA/health/live phải có bằng chứng riêng; không đổi workflow.

<!-- MÁY SINH:BẮT ĐẦU -->
## 6. Máy sinh — đừng sửa tay (cập nhật 20/11/2026 13:33)

### 🔥 ĐIỂM NÓNG — top 10 theo (số dòng × số lần sửa)

| File | Số dòng | Số lần sửa | fanIn |
|---|--:|--:|--:|
| `static/portal/portal.js` ⚠️ **>500 dòng — vi phạm điều CẤM số 1** | 43292 | 410 | 0 |
| `static/portal/integration.js` ⚠️ **>500 dòng — vi phạm điều CẤM số 1** | 39488 | 197 | 0 |
| `static/portal/portal-i18n.js` ⚠️ **>500 dòng — vi phạm điều CẤM số 1** | 22848 | 158 | 0 |
| `static/portal/portal-motion.js` ⚠️ **>500 dòng — vi phạm điều CẤM số 1** | 935 | 30 | 0 |
| `static/portal/service-worker.js` | 308 | 57 | 0 |
| `static/portal/portal-auth.js` ⚠️ **>500 dòng — vi phạm điều CẤM số 1** | 673 | 6 | 0 |
| `static/portal/portal-theme.js` | 284 | 11 | 0 |
| `static/portal/portal-features.js` ⚠️ **>500 dòng — vi phạm điều CẤM số 1** | 574 | 5 | 0 |
| `studio/script.js` ⚠️ **>500 dòng — vi phạm điều CẤM số 1** | 1496 | 1 | 0 |
| `static/portal/portal-feature-catalog-copy.js` ⚠️ **>500 dòng — vi phạm điều CẤM số 1** | 1308 | 1 | 0 |

### 🔷 HÌNH DẠNG — ⚠️ không áp dụng

KHÔNG có quan hệ import nào giữa 21 file (0 cạnh) — nhiều khả năng dự án nạp mã bằng thẻ <script> trong HTML chứ không phải ES module. Bộ lọc hình dạng KHÔNG dùng được ở đây: "node lẻ = tất cả" là hệ quả của cách nạp, không phải lỗi.
<!-- MÁY SINH:KẾT THÚC -->
