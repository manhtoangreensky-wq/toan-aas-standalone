# WA-35 hydrated motion measurement — R11 — 2026-10-10

## Result

`PARTIAL_MEASUREMENT_NOT_PASS`. The local hydrated matrix produced 16/16
measurements with `CLS=0` and `pageErrors=0`, but the acceptance runner exited
`1`. Four rows contain a long task over 200 ms (maximum 311 ms); ten rows
contain a frame gap over 200 ms (maximum 450 ms). The matrix records one
computed `portal-customer-observable-enter` animation in each of the 8 normal
rows and none in the 8 reduced-motion rows, but it records no matching
`animationend` event for any normal row. Therefore this run does not verify the
680 ms duration and does not pass WA-35.

## Run boundary

- Web source HEAD: `17b9494392cc063e8f9d0f39974da2569009b23d` plus the local dirty
  overlay recorded by the QA manifest; this is not `main`, deployed, or live.
- Routes: `/features`, `/dashboard`, `/studio`, `/wallet/topup`.
- Viewports: `1440px` and `390px`; motion: normal and reduced.
- Run window: `2026-10-10 11:04:48–11:06:59` Asia/Saigon.
- Runner: local Python/Playwright harness; 16 screenshot/row JSON files were
  generated under `outputs/wa35-measured-20261010-r11/browser/` in the task
  workspace. Raw browser profile is intentionally not part of this evidence.
- Safety counters: `PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`,
  `PRODUCTION_DATA_MUTATIONS=0`.

## Per-row measurements

| Route | Viewport | Motion | CLS | Max long task (ms) | Max frame gap (ms) | Page errors |
|---|---:|---|---:|---:|---:|---:|
| `/features` | 1440 | Normal | 0 | 100 | 100 | 0 |
| `/dashboard` | 1440 | Normal | 0 | 99 | 233.5 | 0 |
| `/studio` | 1440 | Normal | 0 | 99 | 216.6 | 0 |
| `/wallet/topup` | 1440 | Normal | 0 | 311 | 450 | 0 |
| `/features` | 1440 | Reduced | 0 | 111 | 116.6 | 0 |
| `/dashboard` | 1440 | Reduced | 0 | 117 | 233.4 | 0 |
| `/studio` | 1440 | Reduced | 0 | 87 | 183.4 | 0 |
| `/wallet/topup` | 1440 | Reduced | 0 | 257 | 283.3 | 0 |
| `/features` | 390 | Normal | 0 | 142 | 133.3 | 0 |
| `/dashboard` | 390 | Normal | 0 | 97 | 233.3 | 0 |
| `/studio` | 390 | Normal | 0 | 92 | 200.1 | 0 |
| `/wallet/topup` | 390 | Normal | 0 | 264 | 350.1 | 0 |
| `/features` | 390 | Reduced | 0 | 131 | 133.4 | 0 |
| `/dashboard` | 390 | Reduced | 0 | 95 | 216.7 | 0 |
| `/studio` | 390 | Reduced | 0 | 97 | 183.4 | 0 |
| `/wallet/topup` | 390 | Reduced | 0 | 230 | 250 | 0 |

## Failure and next acceptance gates

The failing assertion is `qa-wa35-astra-browser.py:107`: a normal-motion row
must contain exactly one observed `animationend` event with duration 0.68 s.
The matrix contains `animationEnds=[]` for all 8 normal rows, even though the
computed animation is present. This could be event-capture timing or a real
animation completion issue; this run does not distinguish the two. Do not infer
either cause without a corrected repeat.

- [ ] Fix/validate animation event capture and prove the expected duration.
- [ ] Attribute the long tasks and frame gaps to app work versus browser/runtime
  scheduling using a repeatable trace; keep the current >200 ms rows open.
- [ ] Rerun cold and warm loads, reduced-motion and protected Admin/Auth/Landing
  comparators on the same candidate scope.
- [ ] Keep WA-35/WA-36 open until all acceptance gates pass.

Raw `matrix.json`, per-row JSON, screenshots, and `browser.log` remain in the
local QA output directory; this checked-in summary is not a substitute for the
raw trace or live/deployed evidence.
