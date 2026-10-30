# MU-PRODUCT-EMPTY-H — bỏ khối kết quả ban đầu không có nội dung

24/10/2026 READY sau khi MU08-F-REQUEST-REVIEW local accepted.
ROOT C:/Users/toann/Documents/Codex/_webapp-r218-voice; branch
webapp-r218-billing-ui-20261022; BASE1e01f2417e3000a09c45186e11ee144e52a22fa5;
PR661 / Issue664. F và H giao tuần tự, một worker Flash3.8 nền/source-only.

## Kết quả cần đạt và phạm vi

Hai route `/music/create`, `/music/song` khi chưa có flow không còn card
“Kết quả và trạng thái” cùng empty message. Form, lựa chọn mode, hướng dẫn
đóng mặc định và lưu nháp giữ nguyên. Khi có flow record không rỗng, giữ
nguyên output hiện có kể cả draft, error, guarded, estimate hoặc report.
Không coi missing quote/feature/phase là lý do giấu lỗi có thật.

Allowed: chỉ một prefix trong `static/portal/portal.js:renderWorkspace`,
và mới `tests/music-empty-result-presentation.test.mjs` <=180 dòng.
F renderer/copy/CSS, integration/API/auth/backend/draft/quote/confirm,
mọi old test, toàn bộ non-Music và motion đều protected. Không thêm hook,
helper, action, copy, card hoặc chức năng giả.

Unique old prefix (đã đếm1):

```js
    const outputSection = `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">${outputTitle}</h2>
```

Exact new prefix; template còn lại không đổi:

```js
    const outputSection = musicTask && !(flow && typeof flow === "object" && !Array.isArray(flow) && Object.keys(flow).length > 0) ? "" : `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">${outputTitle}</h2>
```

Missing/undefined/null/primitive/array/empty own-object => omit only Music.
Mọi nonempty object giữ nguyên, không đòi feature/phase/status/data/receipt.
Không sửa flowOutput/flowFirst/renderMusicFlowState hay vị trí chèn output.
`renderFeatureFlowState` không có thật trong source; không tạo hàm đó.

## Tiêu chí và evidence

- H01: real renderWorkspace, hai route×VI/EN/ZH, noflow/null/primitives/arrays/
  emptyobject không output card; form/nav vẫn còn. Assert form hiện trước khi
  assert output vắng, tránh test pass vì toàn bộ page rỗng.
- H02: actual renderMusicFlowState giữ ba gợi ý/Copy/Apply, số0 và unknown
  quote, error/guarded, queued/processing/completed/report/tracking. Không
  mock chính output expression hoặc các flow renderer đang được bảo vệ.
- H03: Non-Music exact BASE comparator chạy riêng ở QA harness; không thêm
  historical Git dependency vào new unit. Reverse đúng1prefix trả
  renderWorkspace về accepted F anchor; F/protected files giữ nguyên.
- H04: actual signed app initial GET-only, hai route×3locale×2theme×390/1440
  cộng360/375/768/844landscape; không API fixtures. Empty output heading/card
  trước1→sau0; form controls/draft/modeBack/AX/focus/overflow giữ nguyên.
  Controlled flow checks được ghi riêng, không suy thành native quote/output.
- H05: focused/fullNode/Python/review, rồi mới F/H delivery chung. Không push
  từng spec để lưu tạm. Không merge/deploy khi master/wholePR chưa đóng.

## Các bước 2–5 phút sau khi mở khóa

1. Chụp hash accepted F/đọc source; Flash R1 trả TEST_FILE rồi1EDIT exactprefix.
2. Codex áp new test trước, `node --test tests/music-empty-result-presentation.test.mjs`
   => assertionRED do initialoutput vẫn còn, không harnesserror.
3. Áp1record nguyên văn; cùng command GREEN; old focused suite không sửa:
   `node --test tests/music-product-controls.test.mjs tests/music-workspace-runtime-integration.test.mjs tests/music-flow-state-and-surface-contract.test.mjs tests/voice-flow-state-presentation.test.mjs`.
4. Browser matrix/independent comparator/review. R2 nếu chưa đạt, không R3.
5. Gộp evidence/checklist/docs/Tester/prepush/provenance vào delivery F/H.

PROVIDER_CALLS_APP=0;WALLET_MUTATIONS=0;DEPLOY=NO;LIVE_PASS=NOT_TESTED.
Không runtime/QA data gửi Gemini; không IDE/login/settings. Goal ACTIVE.

## Checklist

- [x] F local accepted mở khóa H:unit172/fullNode1245/Python119/browser48,
  source exact4records+4keycorrection/12protected/40nonMusic;0newfailures.
- [x] H01 assertionRED6/12→GREEN12/actual renderer. R1test wrapperretention;
  oldtests+independentactualMusicflowcomparator chứng minh content riêng.
- [x] H02 48validflowoutputsbằngacceptedF,quote0/unknown/3suggestions/report50/tracking.
- [x] H03 exact1prefix/reverseFhash/12protected/oldtests/40nonMusicworkspaceoutputs.
- [x] H04 actualinitial48emptyheadings0/form1/nav4/draftaction1,controlledflow
  F regression48;0errors/external/UIwrites/overflow,720AA>=5.522.
- [x] H05 Node1257/Python119/independentC0I0M0/localaccepted. F/H delivery
  CI/receipt còn gate riêng trong parent plan; không wholeMusic/LIVEclaim.
