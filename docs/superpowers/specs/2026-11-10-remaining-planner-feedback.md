# Remaining planner feedback — prerequisite before native acceptance

BASE_SHA=e63f073f460e551438fbb8e3627ec232353f3efe; Issue #689; same UI batch.
Owned Script compose/edit RED showed an English page with Vietnamese stale
feedback. Limit the amendment to text/title expressions in five functions:
portal.js synchronizeCinematicConceptDraftFreshness,
synchronizeScriptToScreenDraftFreshness,synchronizeStoryboardComposerDraftFreshness;
integration.js reconcileScriptToScreenPlannerSaveControls and
reconcileStoryboardComposerSaveControls. Four new feedback keys per locale.

- [x] Stale, saving and already-saved feedback follows VI/EN/ZH selection.
- [x] Exact same fresh/saved/pending/disabled guards, datasets, events and forms.
- [x] Native compose/edit/save/readback evidence; unknown server data preserved.

Antigravity R1 output-only with full public MAP, no auth/test/fixture/runtime
response or customer data. Two independent output-only sessions are allowed;
coordinator applies sequentially. No auth/API/backend/provider/payment/ENV/data
change. i18n.t is (key,params,locale), never a string fallback API.
PROVIDER_CALLS=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_MUTATIONS=0.
