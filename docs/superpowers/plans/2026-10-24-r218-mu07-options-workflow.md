# Music MU07 — Options Workflow Implementation Plan

> **For agentic workers:** triển khai từng task bằng executing-plans, Antigravity
> 3.8Flash Builder;Codex giữreview/verify/delivery. KhôngtựđổimodelhoặcmởIDE.

**Goal:** hoàn thiện UI chọn/sửa/quay lại bộ gợi ý thật,giữ đủ nhánh regenerate
trong checklist contract;khônggiảbộmới hoặc đánh dấu toànMU07 từUI-only.

**Architecture:** cache tốiđa3prompt/2routes trongmemorytab,session-fenced,
native details sauestimate;existingCopy/Apply/quote-stale không đổi. Next-set/
edit-regenerate cần canonicalcontract riêng ởT0,khôngđưa prompt giả vàoWeb.

**Tech Stack:** FastAPI/vanillaJavaScript/CSS,existingNodeVM/pytest/EdgeQA.

**Spec:** docs/superpowers/specs/2026-10-24-r218-music-retained-options.md

## Global constraints

BASE520174941470fab34c60c26e62607ba2d4b3568f/PR661/Issue664;F/Hlockedreceipt6372116359.
UI/UX trước,motion cuối,kỹthuậtengine/paidprovider/ví không nằm batch này.
NoBot/route-engine/backend/auth/ENV/productionmutation;source/test/spec/MAP
allowlist only toGemini,noQAdata. NoR3/resetSPEC_ID. Mộtworker/mộtsharedsource.

> note rõ là chia plan chi tiết ra thành từng spec kèm theo kết quả cần đạt
> để qua spec khác, với spec đơn giản thì chạy nhiều spec một lúc, nếu spec
> phức tạp thì làm từng spec.

## Hàng đợi không bỏ sót

| Order | SPEC_ID | Outcome | Dependency | Run | Status |
|---|---|---|---|---|---|
| 1 | MU07-A-RETAINED-OPTIONS | Back sauestimate mở đúngbộđãnhận,chọnlạikhóaquote | FHaccepted | COMPLEX/SINGLE | A01_A05_PASS_A06_PENDING |
| 2 | MU07-UI-CHOOSE-EDIT | Actual choose/edit/modeBack giữtấtcảinputvàfocus | Aimplementation | QAinA,noextraengine | PASS48_records |
| 3 | MU07-A-DELIVERY | Docs/Tester/onepush/CI/receipt | Alocalaccepted | Codexonly | IN_PROGRESS |
| T0 | MU07-NEXT-SET-CONTRACT | Regenerate/rotation/version/idempotency/noeffect truth | Backendauthority | technicalafterUI/motion | OPENnotreplacedbyA |
| T0 | MU07-EDIT-REGENERATE-CONTRACT | Newdescription→new3/validation/Backcancel | Nextsetcontract | technicalafterUI/motion | OPEN |

### Task1 — test trước production,2–5phút/step

Files:newtests/music-retained-options.test.mjs<=260lines;exactspecabove.
Consumeactualsync+Musicrenderer/catalogue/quotehelpers;nohistoryrenderer stub.
ProduceREDhistorymissing,khôngharnesserror.

- [x] FlashR1/R2failedgate,artifactsretained;Solxhigh takeover,noR3;testonlybeforeproduction.
- [x] Run:`node --test tests/music-retained-options.test.mjs`.
  ExpectedassertionRED:afteractualdraft→estimate khôngdata-music-suggestion-history.
- [x] Negativegates cóvalidpositivecontrol;RED18assertions/0harnesserrors.

### Task2 — boundedmemory và fallback,2–5phút/step

Files:portal.js/portal-i18n.js/portal-theme.css onlyat exactspecanchors.
Interfaces:new synchronizeMusicSuggestionSnapshots(context)->void;
moduleMapsourceprivate/readonlyrender;publicAPI/signatureskhôngđổi.

- [x] ApplyexactSolrecordsafterRED;newsynccalledoncepremount/render.
- [x] Run:`node --test tests/music-retained-options.test.mjs`→19pass/0fail.
- [x] Run:`node --check static/portal/portal.js`→exit0.
- [x] Reviewprivacy/bounds/clone/explicit-empty/nooldsuccess/zeroI/O.

### Task3 — actualinteraction và regression,2–5phút/check

Files:ignoredQA scripts/reportsaudit,khôngproductionengine.

- [x] SignedQAcontrolledflowbaseline→green48:Apply1→estimate→openhistory→Apply2→
  editstale/newquote/sessionrotation/clear;2routesVIENZH/lightdark/3901440+
  360375768844landscape,actualassetchecks/AX/AA/nooverflow/UIwrites0.
- [x] Run:`node --test tests/*.test.mjs`→1276pass/0fail/0skip14296.0041ms.
- [x] RunboundedPythonMusic/SFX/foundation119/2existingwarnings74.32s;F/Hprotected.
- [x] IndependentreviewC0I0M0;9records/13functions/12files/oldtests/Chattailprotected.

### Task4 — single delivery batch

- [ ] Updateoperations/comparison/Tester/master/state vàfhfinalreceiptstatus.
- [ ] Prepushreport3gates,compileall/syntax/diffcached0.
- [ ] Source/docscommit→WebonlyprovenancecleanHEADrefresh/verify→2generated
  filescommit→onepushremoteGITHUB→readback+CIboth→receipt/tickAonly.
- [ ] KeepMU07totalandT0branchesOPEN;goalACTIVE;motionruntimewaveLAST.

Ownerđãyêucầuthựcthitheoplan;khônghỏiđổicáchgiaoviệchaymởthêmthread.
PhạmvimớivềAPI/auth/paidprovider/financial/data/deploycầnOwnergate riêng.
