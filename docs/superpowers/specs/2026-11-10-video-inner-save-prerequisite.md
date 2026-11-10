# VIDEO-INNER-SAVE-PREREQUISITE — contract before application changes

BASE_SHA=bf1e7ee3468573ef0be61ca89d9f5ae3800f98f9. Issue #689.
This is a baseline prerequisite discovered while preparing actual result/save
acceptance for the first-three-route locale batch, not a locale-worker failure.
Status: RED measured; no application patch applied yet.

## Exact defects and required contract

1. `VideoPromptPlannerResult` does not carry language. The server composer omits
   it and the Portal projection drops it, while the existing save fence requires
   exact source/result language equality. Add a required validated vi/en language
   field to this response DTO; echo `payload.language`; validate/preserve that
   field at the existing integration/Portal boundaries. Do not delete or loosen
   the source language comparison, infer language from profile, or default a
   missing response value.
2. Three integration save-receipt validators currently return a compact object
   without the execution boundary flags. The next Portal normalizer correctly
   rejects this as an incomplete transport. Keep every existing exact-key,
   UUID/revision/state/count/false-flag check and return the full validated,
   bounded receipt through merge. Portal alone projects it to content-free
   display metadata. No customer content or arbitrary response extras are added.
3. The Idea and Self-shot receipt renderers must consume the already validated
   Portal projection, not run the transport normalizer a second time. The
   Self-shot result renderer and source matcher must likewise consume their
   existing checked compact result. Raw unsafe responses still pass through the
   unchanged full boundary normalizer before any of these private consumers.

## Allowlist and protected paths

- `copyfast_video_studio.py`: only `VideoPromptPlannerResult` additive language
  field/validator and `_compose_video_prompt_plan` result language assignment.
  No request/save/DB/plan conversion/template or actual video-engine changes.
- `static/portal/integration.js`: only prompt result language validation and
  return projection of `videoPromptPlannerPlanSaveReceipt`,
  `videoIdeaPlanSaveReceipt`, `selfShotScenePlanSaveReceipt` after their existing
  strict checks. All API/action/session/CSRF/submission/idempotency logic locked.
- `static/portal/portal.js`: prompt result language read/validation/projection;
  `renderVideoIdeaPlannerSaveReceipt`, `renderSelfShotScenePlannerSaveReceipt`,
  `renderSelfShotScenePlannerResult`, `selfShotScenePlanSourceMatchesVisibleResult`
  consume their existing checked projections. No signature change, permissive
  raw-or-projection normalizer, new success fallback, new capability or bypass.
- New targeted tests/fixture already declared below; bounded legacy expectations
  may be amended only if they encode the old broken response shape. No assertion
  may be dropped to hide an unsafe boundary or permit unknown fields.

Auth authority, Bot/route-engine/provider, wallet/PayOS, ENV/credential/schema,
production data, motion/CSS/layout and deploy workflow remain protected. This
response metadata addition is not a database/schema migration or provider call.
Do not apply overlapping renderer replacements concurrently: locale output is
retained, then this prerequisite is merged sequentially at exact non-copy anchors.

## Impact evidence before BUILD

Production references measured with `git grep -n`:

| Symbol | Definition and consumers |
|---|---|
|VideoPromptPlannerResult|copyfast_video_studio.py:1627,2126,2177; result validation/composer/private plan conversion |
|normalizeVideoPromptPlannerResult|portal.js:3741,8819; private bootstrap boundary |
|selfShotScenePlanSourceMatchesVisibleResult|portal.js:4484,17312; private self-shot result renderer |
|save receipt projections|integration.js:8125,8326,8683 and their own save handlers; Portal bootstrap/renderers in the same route family |

No production module imports a JS private function. The Python DTO is used only
within its module; tests reference its source. Three application files change;
the existing i18n copy patch remains independent. Preserve the full measured
consumer list and compare all other function bodies at review.

## Acceptance / ordered handoff

- [x] Actual pure-composer fixtures produced with outbound network blocked and
  no DB/provider/wallet/production writes.
- [x] `video-inner-save-projection.test.mjs`:21tests,14pass/7fail on baseline.
- [x] `test_video_prompt_planner_language_receipt.py`:vi/en2cases fail because
  the real composer response omits language.
- [ ] `video-inner-receipt-transport.test.mjs`:3receipt parsers through real
  integration->Portal, malformed fields/IDs and true execution flags.
- [ ] One Antigravity output-only patch, independent review and affected tests.
  Same-defect worker failures start0. No direct application edit by coordinator.
- [ ] Signed localhost UI actual compose->confirm->save->readback->open for all
  three routes; test body/receipt fixtures alone are not final flow proof.
- [ ] Retain locale/protected prior evidence, run only affected regressions,
  then one combined delivery after all current batch gates pass.

Commands: `node --test tests/video-inner-save-projection.test.mjs
tests/video-inner-receipt-transport.test.mjs`; `python -m pytest --noconftest -q
tests/test_video_prompt_planner_language_receipt.py`. Fresh fixture language must
come from the actual amended server composer in native QA. Synthetic saved IDs
in unit tests must never be described as actual database/API success.

Also keep server-generated prose/output-locale cleanup open: fixed UI text is
not permission to rewrite customer content or claim server prose is clean.
PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_MUTATIONS=0.

## Safety amendment R2 — preserve every renderer validation call

During application, the guard-removal variant was rejected by the safety gate:
removing the renderer's transport normalizer could accept an inadequately checked
plan object. That variant is withdrawn, not retried indirectly. The initial
application stopped and the one task-owned source-matcher bypass was restored.

Revised contract keeps **all existing renderer/source-matcher normalization
calls**. Portal receipt normalizers retain the full content-free, strictly
validated transport metadata, not only plan ID/count. Prompt/Idea already have
exact field/false-flag checks; Self-shot receipt must gain equivalent closed-key,
plan-key and all false-flag checks before retaining anything. Return only the
validated known fields, never unknown source properties.

Self-shot result normalizer must retain only the recognized execution metadata
that it already checks, alongside its sanitized planner projection. No raw
source spread or unchecked extra field; its repeated normalizer then receives
the complete validated shape and remains fail-closed. The existing unsafe-flag,
ID/revision/state/source-match/capability checks and all normalization calls stay.

The additive required prompt language DTO/composer and language validation remain
as previously specified. Integration receipt validation remains strict and keeps
its full validated envelope through merge. Worker R1 language/integration output
is retained; only the safe metadata-retention amendment requires new code.
Safety rejection is not a worker code failure and does not authorize bypassing
guards. No production/auth/ENV/provider/payment or Bot changes are introduced.
