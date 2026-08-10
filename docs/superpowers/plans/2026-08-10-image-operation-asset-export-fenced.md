# Fenced Image Operation Asset Export Implementation Plan

> **For agentic workers:** use `superpowers:subagent-driven-development` and TDD; complete and review one task before the next.

**Goal:** Retain a signed owner's completed locally verified Image Operation
PNG as one independent, private Asset Vault asset under replay/reclaim/quota
pressure without expanding Bot/provider/payment authority.

### Task 1: Strengthen RED contracts

**Files:** `tests/test_image_operation_asset_export.py`,
`tests/test_image_operation_asset_export_portal_contracts.py`, new
`tests/test_image_operation_asset_export_leases.py`.

- [x] Correct the service-worker fixture and prove RED is two expected failures:
  missing endpoint (`405`) and absent effective capability.
- [ ] Add real `TestClient` tests for same/different key replay, same key on a
  second operation, foreign/CSRF/disabled/noncompleted/unknown/tampered cases,
  current lifecycle after archive/restore/unavailable, source archive and
  project fallback.
- [ ] Add a barrier test: freeze A after promotion, reclaim/complete B, resume
  A and assert one relation/asset with B only.
- [ ] Add direct source/destination tests for final symlink, outputs swap,
  strict RGB/RGBA/alpha, exclusive key, quota reservation vs upload and no
  private response/audit leak.

### Task 2: Add schema and fenced Asset Vault helpers

**Files:** `copyfast_db.py`, `copyfast_assets.py`, lease/Asset Vault tests.

- [ ] TDD the closed flag, relation check/foreign/unique/index invariants and
  idempotency-request mapping.
- [ ] Implement server-only reserve/reclaim/finalize/release/receipt helpers.
  Every mutable write must use lease generation/token/expiry CAS. Finalize
  inserts metadata and completes relation in one SQLite transaction.
- [ ] Include pending reservation bytes in all Vault quota checks; preserve
  current pending keys in reconciler; expose redacted lifecycle reference.
- [ ] Run lease, Asset Vault and lifecycle suites green.

### Task 3: Pin Image Operation export source

**Files:** `copyfast_image_operations.py`, export tests.

- [ ] TDD final symlink/directory swap/mode/alpha and destination-failure
  semantics.
- [ ] Add an exact `PngContract` plus descriptor-pinned export opener using
  DB-derived metadata only. Do not resolve/reopen a final pathname.
- [ ] Make only source integrity errors invoke existing unavailable marking;
  destination failure releases lease and preserves completed source.
- [ ] Run export and existing image-operation suites green.

### Task 4: Add API flag, endpoint and rate family

**Files:** `copyfast_image_operations.py`, `copyfast_api.py`, `app.py`, tests.

- [ ] TDD effective three-flag capability and fixed UUID POST rate scope.
- [ ] Add CSRF/owner route using pinned source plus fenced helper and one
  redacted audit event only on first finalization.
- [ ] Expose only safe effective capability; add anchored `image-operation-export`
  pre-session rate bucket.
- [ ] Run focused HTTP/static contracts green.

### Task 5: Connect narrow Portal interaction

**Files:** `static/portal/portal.js`, `static/portal/integration.js`, optional
shared i18n/CSS only if existing classes are insufficient, Portal tests.

- [ ] TDD eligible-card-only secondary action and guard states.
- [ ] Reuse confirmation/in-memory submission lifecycle; make one same-origin
  `api()` request; validate safe receipt; refresh private projections.
- [ ] Run Portal contracts and `node --check` green.

### Task 6: Contract evidence and clean handoff

**Files:** migration docs/README/generated static audit evidence.

- [ ] Document authority, four-kind allowlist, flags, fenced recovery, quota,
  descriptor integrity, lifecycle truthfulness, PWA/no-store and exclusions.
- [ ] Commit source/tests before static migration audit with fixed Bot baseline.
- [ ] Run targeted suites, compile, JS checks, `git diff --check`, then independent
  spec and security/code-quality review. Push one Web-only PR only after all
  pass; never deploy/change ENV/call providers/mutate wallet or payment.
