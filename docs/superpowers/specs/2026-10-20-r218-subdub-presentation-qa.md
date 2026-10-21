# SD-R218 — SubDub presentation/runtime QA closeout

## CONTRACT

This gate verifies the existing single-screen `/subdub` UI only. It does not
claim ASR, translation, dubbing, Smart Multi execution, upload, quote, job,
artifact or delivery. All execution controls remain guarded until server
capabilities exist.

## Acceptance

- Four modes stay in one route with one selected accessible tab/panel.
- Source subtitle state, broad language list, default/saved/custom voice,
  Auto two-voice, Auto Multi 3–8 and Smart Multi lanes are visible and
  guarded; voice library links remain discoverable.
- Dubbing/combo expose original and dubbing volume controls; subtitle modes
  expose seven positions; report is honest empty state.
- VI/EN/ZH × four modes × light/dark × 390/1440 render without overflow,
  page/console/external requests or mutations. Blue/navy/teal tokens stay.

## Verify

`node --test tests/subdub-hub-presentation.test.mjs` plus authenticated Edge
QA on localhost with the matrix above. Provider calls, wallet mutations and
feature submissions must be zero; LIVE is not claimed.
