# REMAINING-PLANNER-SESSION-OWNERSHIP — faithful browser metadata

BASE_SHA=e63f073f460e551438fbb8e3627ec232353f3efe. Issue #689.
Before actual compose/save verification, source inspection found the same private
client-fence assumption fixed earlier for motion: these three request-current
helpers require account.id, but the browser auth projection intentionally omits
internal account ID. Do not publish an ID, invent one or weaken server auth.

Allow only integration.js client-response ownership fence for cinematic,
script-to-screen and storyboard. Add one private RAM-only signed-hydration stamp
per route, copied from existing trusted auth/me csrf_token after hydrate checks;
clear all three before any hydration await. Set only for signed account, enabled
route and its exact initial path, like the already accepted motion stamp.

The three private RequestIsCurrent helpers keep signature/epoch/session/route/
enabled/authenticated guards and compare captured stamp with private current
stamp instead of nonexistent account.id. Their six compose/save captures take
the corresponding private stamp; no token is put into fields/DOM/storage/logs/
URLs/newheaders or sent to worker. This is UI stale-response ownership, not
server auth, CSRF policy, role, permission or canonical authority changes.

The historical local variable/parameter name expectedAccountId may remain to
avoid unrelated churn; it holds only the private signed-session stamp in this
scope and is never used as an authority input. All action payloads/requests/
idempotency/form/confirmation/normalizer/safetyflags remain exact. No Bot/engine/
provider/wallet/PayOS/ENV/schema/productiondata/authAPI or global account changes.

- [x] Faithful no-ID owned-state regression30cases:currentcompose/save accepted;
 missing/changed/cleared stamp,olderrequest/session,wrongroute,disabled/unsigned
 remain rejected. No fake account-ID fixture.
- [x] One Antigravity exact patch; private stamp clear/set/capture paths reviewed.
- [x] Actual signed localhost hydrate->compose->save confirms stamps are populated
 by real auth response; fixture seed alone is not final hydration proof.
- [ ] Retain copy/metadata evidence on unchanged bytes, affected reruns only;
 then current group's CI/merge/deploy/runtime assets gates. No signedproduction
 or provider-output success inferred from these client checks.

Worker only gets public source/MAP and aggregate observations, not auth response,
token value/testfixture/runtime/customer data. No login/settings/permissions.
PROVIDER_CALLS=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_MUTATIONS=0.
