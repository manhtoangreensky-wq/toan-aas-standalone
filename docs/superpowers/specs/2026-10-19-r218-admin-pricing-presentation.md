# R218 — Admin Pricing: kế hoạch theo lỗi đã đo

## Hàng đợi và kết quả mở khóa

| SPEC_ID | Kết quả chính | Dependency | Run | Status |
|---|---|---|---|---|
| AD-02-PRICING-DATA-TRUTH | Giá/danh mục/phiên bản chỉ từ server; thiếu khác rỗng; giữ 0 thật | Header locale accepted | COMPLEX/SINGLE | ACCEPTED_LOCAL_UI |
| AD-01-PRICING-NAV-LOCALE | Sửa root locale trong shared renderAdminModuleTabs, bảo toàn quyền/routes | DATA-TRUTH accepted | COMPLEX/SINGLE | READY_PHASE_A |
| AD-02-PRICING-LOCALE | Fixed chrome VI/EN/ZH sạch trong renderer Pricing hiện hành và cards | NAV-LOCALE accepted | COMPLEX/SINGLE | ACCEPTED_LOCAL_UI |
| AD-02-PRICING-MOBILE | Published/history dùng bố cục dọc, đọc đủ trường trên điện thoại | LOCALE accepted | COMPLEX/SINGLE | ACCEPTED_LOCAL_UI |
| AD-04-PRICING-AFFORDANCE | Nút mô tả đúng khả năng, publish handler đang guarded không hứa thực thi | MOBILE accepted; đọc contract hiện hành | COMPLEX/SINGLE | ACCEPTED_LOCAL_UI |

Một worker giữ worktree; không batch vì cùng portal.js. Bảng này nối với checklist mẹ
R218, không thay thế hoặc xóa các mục Admin/role/charts còn mở. Motion cuối.

## Audit đã đo

Production shell/renderer/integration/CSS trên localhost, fixture tổng hợp GET-only:
12 cấu hình VI/EN/ZH × light/dark ×390/1440, 3 trạng thái missing/empty/populated =36.
Artifact `../qa/r218-voice-inventory/admin-pricing-audit.json`, SHA256
`ac29f4e8d2480868ed8a5a26afba00fb96027849f683455046c0bd4b5866b658`.

- Missing server catalogue vẫn hiện 7 mã/giá tự điền và nhãn đã phát hành.
- VI có generic English; EN/ZH còn fixed chrome VI. User/server label không được dịch.
- Mobile populated vẫn dùng bảng cuộn ngang, cards đang ẩn.
- Các nút write hiện khi fixture không cấp capability; đây là finding cần đối chiếu
  readiness/contract, không phải bằng chứng backend vượt quyền. Không click nút.
- errors/write/external/unknown0. Exit1 vì findings, không phải harness failure.
- Route /admin/pricing và /admin/packages dùng renderAdminPricing; generic pricing branch
  ở renderAdminDataTable là một consumer khác, không sửa nhầm chỉ vì tìm thấy chuỗi đầu tiên.
- integration.js:38241 publish-modal-open hiện chỉ toast guarded. Tiền/price rules và
  server publish execution giữ T0; UI affordance xử lý riêng, không kích hoạt write.

## Phiếu hiện hành — AD-02-PRICING-DATA-TRUTH

SPEC_ID=AD-02-PRICING-DATA-TRUTH; HANDOFF_ROUND=1; SAME_DEFECT_FAILED_HANDOFFS=0;
ESCALATION=NONE; BATCH_ID=R218-A0; MAX_SOURCE_FILES_CHANGED=2; PR_STRATEGY=ONE_FINAL_PR (#654).
Lời Owner: “nhớ xử lý triệt để, tối ưu, đúng trọng tâm về giao diện và trải nghiệm,
motion làm cuối cùng.” Không thay goal, không triển khai backend hoặc nghiệp vụ tiền.

Worktree `C:/Users/toann/Documents/Codex/_webapp-r218-voice`.
HEAD detached `1730ea41ffda53e6bcd068f45a49c8c9f6949929`, ref
`github/webapp-r217-subdub-ui-r218`; không đổi branch. Local ledger và PR hiện có là
nơi theo dõi; worker không tạo Issue/PR hoặc mutation GitHub.

Đã accepted: mobile cards3/3+browser8/8; shared-state locale7/7+browser12/12;
Admin header zh đúng option, Node713/713+browser12/12. Giữ toàn bộ diff này.
Không có repo-root AGENTS/MAP/PROGRESS/business-rules; parent AGENTS nằm ở
`C:/Users/toann/Documents/Codex/AGENTS.md`. Contract dưới đây là đầy đủ cho lượt này.

### Phạm vi

1. `static/portal/portal.js`: chỉ renderAdminPricing khoảng35158–35305 và phần hiển thị
   giá trong renderAdminPricingCard khoảng33708–33723. Không sửa chữ ký/helper khác.
2. `static/portal/portal-i18n.js`: chỉ thêm 5 key adminPricingReadState.* đủ ba locale.

Portal.js trước task SHA256 `0ebe8dc421eeb28b15b36dd58d339b90a035a49e3ddf8fa5e6eb49f5d36e31e4`;
i18n `83b93bc594cf55fbdde96d0cfe1f08abc46e84dd1fbb2dafcc387444c981c0f9`.
Protected: integration.js/Python/API/auth/RBAC/CSRF/price rules/wallet/provider/DB/CSS,
mọi tests, shared states/header và toàn bộ file/diff khác.

### RED hiện có

Codex đã chạy `node ../qa/r218-voice-inventory/admin-pricing-audit.cjs --truth --baseline --smoke`:
exit1, 1 cấu hình/6 trạng thái, 13 failed checks. Populated25/0 vẫn đúng; các lỗi là
unverified rows, unavailable-vs-empty, authority/status fallback, draft base readiness
và unknown price bị biến thành0. Artifact `admin-pricing-truth-red.json` cùng QA folder.
Không có lỗi trang/request ghi/ngoài/lạ.

### Việc làm — một gate chung, các bước 2–5 phút

1. Thay toàn bộ fallback catalogue 7 item trong đầu renderAdminPricing bằng projection:

```js
    const candidateCatalog = pricingState.published_catalog;
    const hasServerCatalog = Boolean(candidateCatalog && typeof candidateCatalog === "object"
      && !Array.isArray(candidateCatalog) && Array.isArray(candidateCatalog.items));
    const publishedCatalog = hasServerCatalog ? candidateCatalog : {};
    const draftBaseReady = hasServerCatalog && typeof publishedCatalog.catalog_version === "string"
      && publishedCatalog.catalog_version.trim().length > 0;
    const draftDisabled = draftBaseReady ? "" : " disabled";
```

2. Giữ activeDraft/versionHistory/diff/pubItems/draftItems và mọi trường server nguyên
   trạng. pubTable khi !hasServerCatalog phải renderEmpty bằng unavailable title/body
   bên dưới; catalogue hợp lệ items[] dùng empty title/body. Mobile markup dùng cùng
   empty/unavailable text, không biến unknown thành empty.
3. Metadata hiển thị catalog_version/approval_status/authority: chỉ giá trị server hoặc
   dấu “—”. Bỏ fallback owner-approved/owner_approved/Core Bridge GET ở UI.
   Badge “Đã phát hành” chỉ khi hasServerCatalog; còn lại dùng badge("unavailable").
4. Hai nút admin-pricing-draft-save/create và input reason nhận draftDisabled. Thêm note
   draftDisabledReason khi !draftBaseReady. Giữ data-action/route, field names/value,
   active draft/history, form structure và publish handler/button hiện có.
   Form base_catalog_version thiếu thì value rỗng, không đưa “—” vào payload.
5. renderAdminPricingCard: đổi `adminNumber(item.sale_price_xu || 0, " Xu")` thành
   `adminNumber(item.sale_price_xu, " Xu")`. Không đổi adminNumber hoặc tính giá.
6. Thêm đúng catalogue sau (key suffix dưới prefix adminPricingReadState.):

| Suffix | VI | EN | ZH |
|---|---|---|---|
| unavailable.title | Chưa có bảng giá được xác minh | Verified pricing is unavailable | 暂无已核实的价格表 |
| unavailable.body | Máy chủ chưa cấp danh mục giá có thể xác minh cho phiên này. Hãy làm mới để kiểm tra lại. | The server has not supplied a verified price list for this session. Refresh to check again. | 服务器尚未为此会话提供可核实的价格表。请刷新后重试。 |
| empty.title | Bảng giá chưa có sản phẩm | No products in this price list | 价格表中暂无产品 |
| empty.body | Danh mục đã được máy chủ cấp nhưng chưa có sản phẩm. | The server supplied this price list with no products. | 服务器已提供此价格表，但其中尚无产品。 |
| draftDisabledReason | Cần danh mục và phiên bản giá đã được xác minh trước khi tạo hoặc lưu bản nháp. | A verified price list and base version are required before creating or saving a draft. | 创建或保存草稿前，需要已核实的价格表及基础版本。 |

Chỉ thêm 15 giá trị; có thể đặt cạnh block states.* hiện có trong mỗi MESSAGES locale
(gần dòng1308/1755/2202 trước chỉnh). Dùng uiText với fallback VI đúng bảng.
Không dọn toàn bộ locale hoặc CSS trong phiếu này; các finding đó giữ spec kế tiếp.

### Acceptance

- AC01: missing/malformed catalogue →0 rows, unavailable message, không owner/version/
  authority/approved claim do client tự điền; khác danh mục rỗng đã xác minh.
- AC02: empty server catalogue →0 rows và empty message riêng; populated giữ đúng IDs,
  user labels và giá25/0. Không dịch label do người dùng/server cấp.
- AC03: giá không có phải là “— Xu” ở table/card, không tự thành0;0 thật vẫn0.
- AC04: thiếu catalogue hoặc base version →draft create/save/reason disabled có giải thích;
  catalogue/version hợp lệ giữ luồng bản nháp hiện hành. Form/payload/API không đổi.
- AC05: source ngoài hai function, mọi old i18n values, CSS/tests/backend/integration
  giữ nguyên. Full Node713/713; JS syntax/diff-check đạt.
- AC06: browser12 cấu hình ×6 trạng thái=72; truth failures0, errors/write/external/
  unknown0. Locale/mobile/publish-affordance findings còn mở phải báo rõ, không gọi toàn
  Pricing hoàn thiện từ gate này.

### Verify và báo cáo

Worker không chạy shell/terminal hoặc lệnh qua UI; dùng công cụ tệp. Codex sẽ chạy:

```powershell
node ../qa/r218-voice-inventory/admin-pricing-audit.cjs --truth --smoke
node ../qa/r218-voice-inventory/admin-pricing-audit.cjs --truth
node --test tests/*.test.mjs
node --check static/portal/portal.js
node --check static/portal/portal-i18n.js
git diff --check
```

Expected: truthFailures0 trên72 trạng thái, full Node713/713, syntax/diff0. Residual
presentation findings không bị bỏ khỏi audit và được giữ ở ledger/spec kế tiếp.

Ghi `_giao-viec/BAO-CAO-04-AD-02-PRICING-DATA-TRUTH.md` theo từng AC: BUILT/FAILED/BLOCKED,
HEAD, đúng file/diff, verify NOT_RUN, giả định và các mục chưa kiểm; rồi dừng. Không tự
ACCEPTED. Không Git/network/browser/package/ENV/DB/provider/wallet/production/deploy/IDE trust.
Nếu SHA/worktree lệch, cần sửa integration/price math hoặc vượt allowlist thì dừng.

## Ghi chú bắt buộc cho spec locale kế tiếp

- Bản cũ dùng value draft_id="Chưa có dự thảo mở" và integration kiểm sentinel VI này
  tại38221. Không dịch value đó thành tiếng Anh/Trung rồi gửi như một draft ID thật.
  Cần giữ payload semantics; UI copy có thể chuyển sang placeholder với value rỗng,
  có test form-data tương ứng trước sửa.
- Giữ code/SKU, user labels, reason, version và IDs nguyên bản. Không sửa DTO hoặc
  suy permission từ tên nút. Finding nút write không đồng nghĩa backend bypass.

## Nghiệm thu DATA-TRUTH 19/10/2026

Codex ACCEPTED_LOCAL_UI_CI_PENDING. Source ngoài2functions và mọi old i18n values giữ
nguyên; chỉ15 dictionary entries mới. Replayed immutable baseline có target functions
tương đương sau CRLF/LF: RED18 checks; GREEN72/72 states, Node713/713, syntax/diff0,
errors/write/external/unknown0. Artifact `admin-pricing-truth.json` SHA256
`3c5b0063939fe299eb976d5786b3ad0518940b89c1dee02dc4a302b4208c93ab` trong QA folder.
Hàm hỗ trợ cho phiếu sau: uiText:216; badge:9655; adminNumber:33002;
renderEmpty:21392; renderRowsTable:21416. Đính kèm vị trí/code helper để tránh dò toàn file.
Không reset SPEC_ID hoặc tính discovery/QA-selector correction là code failure của worker.
Locale/nav tabs, mobile/clipped empty view và disabled/publish affordance vẫn mở.

## Root cause NAV-LOCALE — dữ kiện cho spec kế tiếp

Giữ SPEC_ID AD-01-PRICING-NAV-LOCALE; root shared ảnh hưởng9 nhóm,54 tab occurrences/
48 unique paths. renderAdminModuleTabs khoảng11830 đọc context.locale và typeof
currentLocale, không khớp nguồn profile/interface locale đang dùng trong trang.
Chưa sửa source ở bước chẩn đoán.

- ADMIN_TAB_GROUPS từ11714 đến trước renderAdminModuleTabs;9 group:
  overview/customers/operations/reliability/finance/pricing/campaigns/system/governance.
- ADMIN_ERP_ROUTE_I18N:90–140 và adminErpRouteText:148 đã có native VI/EN/ZH cho46/48
  paths. Hai path chưa map là /admin/commercial và /legal.
- Không thêm public /legal vào registry Admin để sửa copy. Giữ authorizedRoutes/alias,
  ngoại lệ legal hiện có và href; dùng fallback locale riêng cho hai nhãn nếu cần.
- tests/admin-module-tabs-locale-purity.test.mjs hiện chỉ2 test catalogue source;
  bổ sung render thật9groups×3locale, role subset/denied/alias trước sửa.
- VM dùng catalogue thật và uiText adapter thật. Helpers: normalizePath2291;
  portalI18n gần200; reviewedInterfaceLocale/interfaceLocaleFor472–497;
  adminErpRouteText148. Đính kèm code/địa chỉ helper, không dò toàn portal.js.
- Scope dự kiến một tab renderer, tối đa3 copy keys aria/commercial/legal và test
  behavior; giữ ADMIN_TAB_GROUPS, registry/permissions/CSS/Pricing/backend.
  Chốt spec/checklist đầy đủ trước BUILD.
