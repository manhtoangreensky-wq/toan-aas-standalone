# Remaining video-planner headers — combined batch, 10/11/2026

BASE_SHA=564467fbc04cf7445e09bb9d74ed1ea10de0487f.
Branch: codex/video-planner-header-locale-20261110. Tracker: Issue #689.
PR706 is merged/deployed and protected; it is the baseline for this header-only unit.

## Ordered work queue

| Spec | Exact routes | Outcome | Status |
|---|---|---|---|
| VIDEO-PLANNER-HEADERS-A |prompt-planner,idea-planner,self-shot-planner |6fixed title/description keys VI/EN/ZH |Local accepted after one affected sentence correction |
| VIDEO-PLANNER-HEADERS-B |script-to-screen-planner,cinematic-concept,image-motion-planner |6fixed title/description keys VI/EN/ZH |Local accepted |
| VIDEO-PLANNER-HEADERS-C |reference-format-planner,storyboard-composer |4fixed title/description keys VI/EN/ZH |Local accepted |

All paths have the `/video-studio/` prefix. Workers are isolated output-only;
coordinator applies sequentially and accepts the completed group once. Shared
prefix anchors are not concurrent repository writes. No whole-form/result locale
closure is claimed by correcting only these16header keys.

## Scope and protections

- `static/portal/portal.js`: exact route-only branches at the existing title and
  description helper prefixes. No signature, fallback, route factory, URL,
  UUID-detail match, unrelated route, form/result/control/data/guard change.
- `static/portal/portal-i18n.js`:16new keys in three distinct header namespaces;
  preserve every existing key/value, especially PR704/705/706 accepted copy.
- One new portable test, existing catalog-snapshot exclusion only for approved
  namespaces, focused CI invocation and scoped docs/provenance may be updated.
- No CSS/integration/auth/backend/Bot/engine/provider/wallet/PayOS/ENV/schema/data
  or deployment-workflow changes. No private actor/session work in this batch.

## Baseline and acceptance

The one inventory rendered8routes xVI/EN/ZH=24actual header states. All8English
descriptions remain Vietnamese;3Vietnamese titles are unlocalized English and
one contains generic “prompt”. This is fixed presentation text, not customer data.
Real normalized baseline tests:48cases,24route/input-protection pass and24locale
checks RED. No API/provider/wallet action was invoked.

- [x] Actual source, public packet contents and normalized RED are recorded.
- [x] Three complete worker outputs match16exact reviewed keys and narrow scope.
- [x] One combined renderer/data/control/old-catalog/unrelated-route acceptance:
  47retained passes plus one corrected Chinese sentence; only that case rerun.
- [x] One owned native header/ARIA check for these8routes at mobile/desktop across
  VI/EN/ZH. GET-only after temporary account setup; no product actions or repeated
  tests of already protected PR706 internals. 48/48 at320dark/1440light.
- [x] Focused regression139/139; source/protected comparison and scoped
  operations/original-feature/tester documents complete. Unchanged code evidence reused.
- [ ] Committed provenance, CI, merge and ship.
- [ ] Runtime/service/asset reconciliation after deploy, separately from signed
  production output/device/first-paint proof.

Full public MAP and selected public helper prefixes are in every packet. No
tests, fixture/API/auth response, customer/credential/ENV or Bot source is sent.
Owner's one-pass/batched acceptance rule applies: reuse receipts on unchanged
code, rerun only failed parts after new patches. No blanket full-suite repeats.

PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_MUTATIONS=0.
Whole-app locale, inner planner form/result copy, meaningful-content density,
keyboard/auth lifecycle and final motion remain in the existing master ledger.

Local evidence and limitations: `docs/reports/video-planner-headers-20261110.md`.
Tester session: `KIEM-THU/PHIEN-VIDEO-HEADERS-20261110.md`.
