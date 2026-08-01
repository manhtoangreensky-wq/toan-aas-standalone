# Image Tools Picker-Intent Catalog Design

## Intent

Finish one narrow, truthful parity slice for thirteen finite Image Tools pickers found
in frozen Bot baseline `b29d0d474974075f4cba963d2c510f49d2d1b3e4`.
The static auditor may classify the listed callback literals as a way to start
a brand-new signed Web route.  It must discard the Bot picker value entirely:
there is no callback handoff, identity link, form prefill, asset selection,
prompt reuse, resize execution, provider invocation, wallet action, job,
output or delivery.

## Approaches considered

1. Keep all residual `imgtool|*` values source-review-required.
   - Safest, but leaves finite prompt-planning and deterministic-resize entry
     evidence incomplete even though equivalent Web-native routes exist.
2. Map namespace prefixes or pass the picker value into a route/query string.
   - Rejected.  The Bot handler is a Telegram state machine; dynamic style,
     ratio, dimension, file and confirmation values can alter Bot-local
     pending state or delivery.  Query/form transfer would make a Bot state
     look like a signed Web request.
3. Recommended: exact raw-literal catalog that starts a fresh Web route and
   explicitly records the picker value as discarded.
   - It improves inventory coverage while retaining a fail-closed boundary.

## Reviewed exact literals

| Frozen Bot literal | Fresh Web route | Web-native tool | Why it is bounded |
| --- | --- | --- | --- |
| `imgtool|prompt_goal|product`, `imgtool|prompt_goal|ad`, `imgtool|prompt_goal|cinematic` | `/image/prompt-composer` | `web_image_prompt_composer` | Bot only stores a pending prompt goal before its next picker; Web starts an empty signed composer and the user selects again. |
| `imgtool|prompt_ratio|1x1`, `imgtool|prompt_ratio|9x16`, `imgtool|prompt_ratio|16x9`, `imgtool|prompt_ratio|4x5`, `imgtool|prompt_ratio|3x4`, `imgtool|prompt_ratio|4x3` | `/image/prompt-composer` | `web_image_prompt_composer` | Bot can build a text result from pending state; the Web route begins independently with no prompt or ratio prefill. |
| `imgtool|resize_pixels|1024x1024`, `imgtool|resize_pixels|1920x1080`, `imgtool|resize_pixels|1080x1920`, `imgtool|resize_pixels|1080x1350` | `/image/resize` | `web_image_resize` | Bot resize can download a Telegram file and deliver output.  Web begins a separate owner-scoped Asset Vault flow and requires a new explicit confirmation. |

The existing seventeen direct Image Tools entry mappings remain unchanged.
These thirteen picker-intent literals are a separate registry so future review
can distinguish a generic tool entry from a discarded Bot picker choice.

## Explicit non-goals

- Do not modify `bot.py`, Bot bridge, provider, PayOS, wallet/Xu, jobs,
  webhook, storage runtime, image engine, UI, Video, Motion, capabilities,
  skills, or LocalVideoStudio-owned files.
- Do not map `edit_type|*` in this slice.  Those values depend on a Bot image
  selection and the current Web Image Enhance route is deterministic local
  processing, not a claimed Bot AI-edit replacement.
- Do not map `prompt_style|*`: the current Web composer intentionally has a
  free-text style field, not a Web-native equivalent of Bot suggestions 1/2/3.
  Do not map custom, back, continuation, result, save, request, confirmation,
  tier, `edit_ai*`, `prompt_use`, `prompt_from_last`, `resize_continue`, or
  any dynamic/template/case/suffix/whitespace variant.
- Do not create a URL, browser storage entry, API payload or database row from
  any Bot callback token or selection.

## Contract

The audit uses raw case-sensitive dictionary lookup only.  A reviewed picker
mapping has `NAVIGATION_ONLY`, `SIGNED_WEB_NATIVE_CUSTOMER`,
`WEB_NAVIGATION`, and a source mode of `BOT_PICKER_INTENT_DISCARDED`.  Its
evidence states that the Web user must choose every field, source asset and
confirmation independently.

Every unlisted `imgtool|*` value remains
`IMGTOOL_SOURCE_REVIEW_REQUIRED`.  It cannot inherit an Image route or start
any browser/provider/wallet/job/output/delivery operation.

## Verification

- Test all thirteen exact keys, target, source mode, no-transfer dispositions
  and absence of a query/fragment in targets.
- Test upper-case, whitespace, suffix, custom, AI, confirmation and template
  values remain fail-closed.
- Regenerate static docs/reports using only the frozen Bot SHA.
- Run focused migration and Image Operation tests, compile the audit module,
  `git diff --check`, two independent reviews, and only then create/merge the
  PR.  Railway deployment, public health checks and protected-route smoke
  checks are separate release operations, not evidence for this static-only
  audit contract.
