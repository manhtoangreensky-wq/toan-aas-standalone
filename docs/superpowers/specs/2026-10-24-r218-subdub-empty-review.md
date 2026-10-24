# SD-D3-EMPTY-REVIEW — no meaningless initial SubDub cells

## Contract
BASE_SHA=00a34c2b9aea1c43ba387bd70004ea6a90b5b55f
ROOT=C:/Users/toann/Documents/Codex/_webapp-r218-voice
BRANCH=webapp-r218-billing-ui-20261022; PR661; Issue664.
Dependency SD-C3 accepted receipt6379877100; CI40061704379 bothSUCCESS,
456authenticated records. SD-B3/B4/C2/D2/E2/C3 remain locked.
Owner: "tiếp tục xử lý triệt để theo thứ tự"; hide meaningless boxes without
losing features; no fake media/output/price or experimental labels; motion LAST.
Risk BOUNDED/SINGLE. One presentation outcome, two production files.

## READ
portal.js renderSubDubHub stage3 always shows four summary rows: mode,
static unavailable price, static unavailable-cost explanation, actual projected
balance. VI values are "Giá chưa khả dụng" and "Chi phí sẽ được xác nhận khi tính
năng sẵn sàng." These are not quotes. Existing guarded reason remains visible.
Stage4 always has one header and one direct empty report child; no real report
DTO consumer exists here. Do not claim report/output capability.
No function signature, pricing formula, route, DTO or business logic changes.

## Production allowlist
1. static/portal/portal.js: only add data-subdub-summary-placeholder="unavailable"
to the TWO portal-summary-item parent divs containing summaryPriceKey/PriceValue
and summaryCostKey/CostValue. Do not mark mode/balance/settings rows. Keep all
original spans/copy/value expressions, including zero balance.
2. static/portal/portal-theme.css: insert exactly these TWO rules before unique
/* Final light AI Chat Workspace surface */:

```css
.portal-subdub-hub [data-subdub-summary-placeholder="unavailable"] {
  display: none;
}
.portal-subdub-hub [data-subdub-stage="4"][data-status="guarded"]:has(> .portal-subdub-report-empty[data-state="empty"]):not(:has(> :not(.portal-card-header, .portal-subdub-report-empty[data-state="empty"]))) {
  display: none;
}
```

No nth-child/text matching/global hides/important/opacity/palette/motion.
The report rule intentionally fails open if wrapper status is not guarded,
empty child state changes, or any other direct child (besides header/empty
message) is present. This amendment narrows the draft selector to avoid hiding
future error/status/output alongside a stale empty child. CSS diagnostics only;
not proof of real reports. Future canonical price rows must not carry placeholder
marker; server authority remains required.

Protected: all other JS bytes/oldtests/integration/i18n/portal.css/backend/auth/
wallet/PayOS/Bot/provider/ENV/Chat tail. No removal of shared note, seven lanes,
Auto2/Multi3-8/Smart callbacks, B4search/target21/customISO, volume0-200,
draft/Voice continuation/source guard/disabledCTA/settings/mode/balance.
Docs/tester/evidence/state allowed only to Codex.

## AC and evidence
- D301 actual baseline48:four modes*VIENZH*lightdark*3901440. Report wrapper
and TWO unavailable rows visible; desired-hidden assertion fails for that reason.
- D302 final96:four modes*VIENZH*eight views(light3901440;dark3901440/
360375768844landscape). Initial report wrapper/header and placeholder text absent
visually/AX;2placeholder parents hidden;mode/balance rows visible and equal
baseline;all setting rows/guard/CTA retained;no blank vacated grid row.
- D303 diagnostics on actual DOM:empty child state error,wrapper status error,
and added direct output child EACH restores wrapper. Clear diagnostic to original
and wrapper hides again. Marked price diagnostic removal restores rows. No actual
job/error/quote assertion from diagnostics. Zero balance uses controlled
presentation only if actual QA projection is unavailable, no wallet mutation.
- D304 target21/search/customISO/formats/positions/sourcechoice/7voices/
callbacks/mix0and200/review/draft/Voice return/keyboard/gates preserved.
0overflow/page-console errors/external/UIwrites;sourceLF assets match.
- D305 exact2attributes+2rules reverse equals BASE;backend/oldtests/Chat
unchanged;Nodefocused/full1281/PythonCSS21/reviewC0I0/Tester/docs/prepush.
No unit which only greps source; actual browser assertions catch missing markers,
wrong balance tag, overbroad hides and extra-output hiding.
- D306 source/provenance one push/exactHEAD bothCI/readback/receipt before tick
D3 and unlock E3. No receipt-onlycommit loop. WholePR/master remainOPEN.

## Steps 2-5min per worker step
1. Return exact two markup replacements around price/cost parent divs.
2. Return exact CSS insertion at unique marker.
3. Return report VERIFY=NOT_RUN; Codex runs browser and regression.
Command (Codex): node <QA>/browser-SDD3.cjs <isolatedorigin> red|green
Expected RED exit1 visible empties48; GREEN exit0 configurations96,errors0.
Regression: node --test tests/subdub*.test.mjs; node --test tests/*.test.mjs;
python -m pytest -q tests/test_portal_aura_theme_contracts.py.
Flash3.8 R1/R2 max sameSPEC_ID/noR3;isolated emptyCWD/noadddir/sandbox/
source-only stdout/no tools. Root reviews/applies exact records after RED.
No settings/auth/global policy changes;PROVIDER_CALLS_APP=0;
WALLET_MUTATIONS=0;DEPLOY=NO;LIVE_PASS=NOT_TESTED;GOAL=ACTIVE.
E3-AX-READINESS causeUNKNOWN retained, not solved by D3.
