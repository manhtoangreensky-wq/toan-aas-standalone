# P0-05E — PRIMARY MANAGER VERIFIED LOCAL

Đang đọc và áp dụng skill owner-governed-codex cho task này.

**SPEC_ID:** `P0-05E-WEB-MANUAL-TOPUP-PARITY-HOTLINE-SECURITY`
**Manager stage:** `VERIFIED_LOCAL / PRE-PUSH READY AFTER FINAL GATES`
**PR previous HEAD:** `15c00151b97c1dd3324b3d8bdb990721e0ad1c0e`
**Not claimed:** commit, corrective push, merge, deploy, runtime or live-money outcome.

## Builder/takeover history

- Antigravity R1: `FAILED_ACCEPTANCE` — missing rendered code/hotline, guarded lane persistence, Admin parity and exact test output.
- Antigravity R2: terminal `BUILT`; sealed patch SHA-256 `a3fb6137a4ef4c8bd69050e4cd2791b9d839c49db72c52905b588f729b263dae`, 317 lines, 7 allowlist paths. Manager canonical run was `3F/17P`; verdict `FAILED_ACCEPTANCE`.
- Codex Sol `gpt-5.6-sol/xhigh`: exact dispatch/session `01a05189-587a-7873-a5fa-1f980a229dba`, but access and refresh tokens were revoked before source work; mutations `0`.
- Primary takeover: retained exact SPEC_ID and scope; fixed only confirmed production/test/viewport boundaries.

## Corrective behavior

- Hotline fallback is `0898360858`; bank-account fallback remains independently `0387532320`.
- Signed payment options derive a display-only payment code from exact ASCII numeric linked identity; whitespace, Unicode digits, zero, nonnumeric and >20 digits fail closed.
- Browser create schema/body remains closed; no payment code, owner or Admin authority can be supplied by the browser.
- Manual lane and `amount_vnd/method/reference` survive same-route data hydration; invalid lane values cannot mutate route state.
- Customer single/history/detail/status projections and customer JS state omit `admin_note`; authorized Admin projection retains request ID, Telegram ID, display name, amount, method and note.
- Mobile manual submit clears the PWA FAB, Copilot and bottom dock without moving global controls.

## RED → GREEN

Sealed external probes:

| Probe | SHA-256 | Baseline | Candidate |
|---|---|---:|---:|
| Portal mount/click/input/hydration | `c5f4ef413d293fc28dfc4d8c3b12d60465a7f7b5c2be83a74464240ab700faf7` | `1F` | `1P` |
| Owner/Admin-note security | `9db3254de5fd6ea9ef30f884b4c59cb12b1b83866c21e879d2a111a998d55455` | `2F` | `2P` |
| Hotline/payment metadata | `b183c544607d61fea5ae6957cd2c44db3e22947a0d0b5460b33ff6d4b1c23370` | `9F/1P` | `10P` |

Canonical targeted after Primary: `21 passed, 87 deselected, 1 warning in 8.93s`.
Scoped CSS/static follow-up: `13 passed, 87 deselected`, diff-check exit `0`.

## Protected comparator

Same five-file suite on exact PR head and candidate:

```text
BASELINE=7 failed, 175 passed
CANDIDATE=7 failed, 179 passed
FAILURE_IDS=same exact seven existing portal-safety debts
NEW_FAILURES=0
```

Python compile exit `0`; Portal/integration/i18n Node syntax `3/3` exit `0`; `git diff --check` exit `0` before final docs amendment.

## Security verification

Independent read-only reviewer result:

```json
{"results":[{"id":"Customer manual-topup API exposes private Admin notes","status":"fixed","evidence":"All four customer routes converge on the owner projector without admin_note; customer JS allow-list also omits it; Admin-specific projector/authorization retains canonical reconciliation fields."}]}
```

`REVIEW_FINDINGS=NONE`.

## Rendered evidence

Root: `C:/Users/toann/Documents/Codex/2026-07-10/1-ngu-n-ch-nh-v/review/p0-05e-rendered-evidence/`

- `matrix.json`: `91fd864153724ac22fae130c8ddb2201fa63e51ca4ac80a569b8d46e0dba409d`.
- VI + EN × `1440/1024/768/390/360` = `10/10` cases.
- Every case: manual active, PayOS hidden, `125000/bank_acb/TX-125`, payment code `123456789`, hotline `0898360858`, overflow `0`, console warn/error `0`, submit overlap with PWA FAB/Copilot/bottom nav `0`, target ≥48px.
- VI guarded `768×900`: manual visible, code/hotline visible, create form/submit count `0`.
- ZH `1024×768`: manual-card keyset/content renders Chinese; server method names/IDs/units remain data exemptions.
- Full-page screenshot stitch visually duplicated one block, but live DOM exact card/form/info/code/hotline/title counts are all `1`; no source fix was made for the tool artifact.
- Whole-page EN/ZH still contains Vietnamese hero/billing/lane/floating copy outside this manual-card corrective. This debt is recorded under `CUST-WEB-FINAL-001`, not hidden or expanded into this spec.

## Tester/pre-push amendment

- Tester source now has `34` sequential cases: `18` red, `13` orange, `3` yellow; WA-32..34 cover metadata, rendered hydration and role-specific note privacy.
- `tester_case_sync.py --bo=31 --so=3 --json` emits exactly three dry-run payloads and performs no GitHub write.
- P0-05D Windows baseline `2F/24P`; candidate `1F/26P`. The remaining common failure is POSIX mode `0600` under Windows (`0o666` observed); Linux CI is the permission gate. Readiness metadata debt was removed.

## Final local verification after docs/CSS closeout

```text
TARGETED=21 passed, 87 deselected, 1 warning in 11.39s
TESTER_LOCAL=26 passed, 1 deselected in 0.56s
DESELECTED_TEST=Windows-only POSIX 0600 assertion; baseline debt, Linux CI gate
PY_COMPILE_AST=PASS
NODE_CHECKS=portal/integration/i18n 0/0/0
TESTER_DRY_RUN=WA-32..34 only, exit 0, GitHub mutation 0
GIT_DIFF_CHECK=0
SECRET_SHAPE_MATCHES=0 across 15 changed files before evidence file
GENERATED_FILES=0
CACHE_DIRS=0
```

Final local diff scope before commit is 16 paths: 9 runtime/test paths, 6 pre-push docs/Tester/readiness paths, and this evidence report. No Bot, bridge, auth, schema, PayOS writer, wallet/ledger, provider or deploy file changed.

Local preview limitation: the external fixture served Portal assets from the worktree but did not map the production `/static/logo_chính_thức.png` or favicon path, so server logs contained fixture-only 404s. Functional DOM/console matrix stayed clean; those asset requests are not counted as production request health and require normal app/live validation later.

## Independent Tester final verdict

The first independent pass found one P2 documentation contradiction only; runtime/security/render ACs passed. Three stale status sentences were corrected. Final read-only reverify:

```text
VERDICT=PASS
AC_01..AC_09=PASS
FINDINGS=P0:0 P1:0 P2:0 P3:0
FILES_CHANGED_BY_TESTER=0
```

Final pre-commit document identities: operating doc `243` lines / SHA-256 `f92d7ee1e83c3f5af39e1b49248dfac1b05d2fbde214377d76cea1b9c56bedb8`; original/current comparison `144` lines / SHA-256 `cfa6a3c927537f8ab000a935e75975ef1656c7de6c6cd4a15828c9a0cab6cd0e`.

## Safety ledger

```text
BOT_SOURCE_MUTATIONS=0
PROVIDER_CALLS=0
PAYOS_LIVE_CALLS=0
TELEGRAM_LIVE_CALLS=0
PRODUCTION_WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
ENV_MUTATIONS=0
COMMIT=NO
PUSH=NO
MERGE=NO
DEPLOY=NO
LIVE_MONEY_FLOW=NOT_TESTED
```
