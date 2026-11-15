# DOCUMENT-PDF-UI —15/11/2026

Đang đọc và áp dụng skill owner-governed-codex cho task này.

GOAL=Phân trang tài liệu và chữ cố định trong ô chọn PDF/trang cần tách dùng đúng VI/EN/ZH; bỏ ba khối giải thích nội bộ không có thao tác, giữ nguyên ghi chú và chức năng.
BASE_SHA=c2fc6c657e41972d806c9a3504ea2c0e0438d975
BRANCH=codex/document-pdf-ui-20261115
TRACKER=Issue689/checklist mẹ
DEPENDENCY=PR743đãgiao:CI43709678826bothPASS,deploy43710852871PASS,
runtime/tree/services/health/fiveassets exact;receipts6893914967/6893915073.

## Phạm vi khóa

Đúng ba proposal Antigravity có sẵn, áp nguyên văn:
historypages2patch6keys/sourcefields3patch7keys/threenotices3patch0keys.
Tổng8literalchanges/2appfiles/13keys×3locale=39values.
Chỉ paginationlabels/aria, Split/Optimize source/range labels/help/
placeholder và ba noticewrapper có title “Không thay thế workflow Bot”.
Mỗi removal giữ nguyên `${renderNotes(page)}`, không wrapper rỗng.

Allowlistapp:static/portal/portal.js,static/portal/portal-i18n.js.
Testmới:tests/document-pdf-ui.test.mjs,helpers/document-pdf-ui-runtime.mjs,
helpers/document-pdf-ui-snapshot.mjs,fixtures/document-pdf-ui-reviewed.json.
Existingtestadapters:document-card-copy snapshot/test currentinput,
DATE/METAcurrentrawsource nếu cần finitePDFprojection trướcchốtcũ.
CI thêm đúng một targetedcommand vào bước locale hiện hữu;
không đổi triggers/permissions/timeout/dependencies/deployworkflow.
Docs/Tester/current-original/cases/checklist/provenance theo gates.

Protected:mọiappPython/backend/auth/CSRF/DB/ENV/schema/integration/CSS/
motion/Bot/engine/provider/financial/productdata; cùng mọifieldvalidation,
required/pattern/maxLength/optionsFrom/referencePicker,limits20MB30pages,
formaction/route/rights/controls/options/source/aside/notes.
Sharedpaginationhelper enabledtruthiness giữ nguyên; actualcaller strictcanView.
Không thay heading/form/copy/metrics còn lại;khôngclaimwholePDFscreenpure.

GREENhashes dự kiến từ8replay:
portal a4130687f3bacee27082f89dd7afee96f4fdc9aa6db05d70594fc7194723e656;
i18n47c9d375a83880e49a686eb00a413098628e0c28a5c24f80487c9f066ca772a7.
MỗiOLDunique1theotừngbước. Chỉ rootreplayđúngproposal,khôngtựviếtlạiapp.

## Checklist / acceptance

- [x] PR743delivery xác minh trước khi bindBASE;khôngđoánmerge.
- [x] Rootđọcall3proposals/actualfunctions/sharedpagination/renderFields,
  5permanentPREP/nativewrappers/bindings/contracts/finalassemblies.
- [x] PermanentBASE1PASS9RED actualfullbundle trước appchange:pagination/fields/
  3pagewholeHTML/notes/rights/customer/oldcatalog/freeze/sourceguards.
- [x] NativeBASEVI375actual/split thấy nhãn nguồn và notice cũ;
  actualsignedemptyGET,wholeoperationstable0/noreseed/Jobs0.
- [x] Exact8replay/2appfiles/13keys39values/fulloutside/20protected source.
- [x] Onegroup645PASS PDF+impactedhistoricalchain;finitePDFsource/catalog/
  i18ninverseFIRST trướcCARD→DATE→META→REQUEST→HISTORY,
  khôngoldhash/globalmask/dropassertion.
- [x] NativeGREEN9unique3signedlocale×Split375light/Compress1440dark/
  Merge375light,3Splitfieldcrops;actualGETempty/nooutputfake/noactions.
- [x] Source-reviewC0/I0/M0/docs/Tester/cases1364lines148634LFbytes,
  changedmetadata1PASS32deselected/PUSH_GATE=READY.
- [ ] Provenance/exactHEADCI.
- [ ] Merge/tree/exclusivedeploy/runtime/fiveassets/receipts riêng.

Native không chế bản ghi phân trang hoặc completed/output. Pagination,
customnotes/hostile/invalid/renderedcontrol cases thuộc actualVM.
DBcopyclosedCARDgreenR1,all9tables/schema/6plans18scenes/versions/
idempotency/source/evidence giữ;wholeoperations0before/after,
khôngseed/delete/filter/productPOST. Only3fakeauth vàGET/HEAD;
child-onlyQAflags/secret/root giữ,khônghost/.env/productionbrowser.
Browserpluginabsent→existingownedlocalhostPlaywright,khôngbypassproduction.
PROVIDER_CALLS=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_WRITES=0.
RemainingDoccopy/readmeta/catalogue/locale/AX/auth/device/Safari/signedUI/
finaloutput/M-FINAL01..06 cònmở;motioncuối.
