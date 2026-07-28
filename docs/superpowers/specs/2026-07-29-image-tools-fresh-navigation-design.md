# Image Tools Fresh Web Navigation Design

## Intent

Give customers a clean, Web-native starting point for the existing deterministic Image tools without pretending that a Telegram callback is a Web request, asset reference, image edit, provider job, payment, or delivery receipt.

The Web App already owns signed routes for prompt composition, Image Enhance, Resize & Aspect, and Brand Overlay. The Bot's `imgtool|*` family remains a Telegram state machine; this design allows only selected tool-picker literals to begin a new Web session on one of those existing routes.

## Approaches considered

1. Keep every `imgtool|*` callback source-review-required.
   - Safest but leaves straightforward local-tool entry points disconnected from equivalent Web-native tools.
2. Map the entire `imgtool|*` prefix to `/image`.
   - Rejected: this would make stateful AI, tier, confirmation, prior-image, provider, Xu, and delivery actions look like safe browser navigation.
3. Recommended: a finite, case-sensitive allowlist of tool-picker callbacks that opens a new signed Web route without transferring any source state.
   - Gives clear entry points to mature Web-native tools and remains fail-closed for every unlisted Bot action.

## Recommended contract

The static migration auditor will use an exact dictionary lookup, before the generic Image Tools boundary, for these lower-case literals:

| Bot literal | Fresh signed Web route | Web-native intent |
| --- | --- | --- |
| `imgtool|prompt_manual` | `/image/prompt-composer` | Start a new structured prompt draft. |
| `imgtool|edit_need_image` | `/image/edit` | Start Image Enhance with a separately selected private Asset Vault image. |
| `imgtool|resize_need_image`, `imgtool|resize_task|ratio`, `imgtool|resize_task|pixels`, `imgtool|resize_method|blur`, `imgtool|resize_method|pad`, `imgtool|resize_method|crop`, `imgtool|editor_resize` | `/image/resize` | Start a new deterministic resize/canvas request. |
| `imgtool|editor_presets`, `imgtool|editor_preset|photo_clear_detail`, `imgtool|editor_preset|product_clean`, `imgtool|editor_preset|cinematic_warm`, `imgtool|editor_preset|fresh_blue`, `imgtool|editor_preset|food_vivid` | `/image/edit` | Start a new Image Enhance request; no Bot preset is preselected. |
| `imgtool|editor_overlays`, `imgtool|editor_text`, `imgtool|editor_logo` | `/image/brand-overlay` | Start a new private text/logo overlay request. |

Every mapping is `NAVIGATION_ONLY`, customer-classified, and recorded only in static audit evidence. The Web server independently enforces its signed-session, ownership, feature-flag, CSRF, idempotency, private Asset Vault, output validation, and download rules.

## Non-transfer and guardrails

No mapping may put the source literal, Telegram identity, file ID, asset/result ID, prompt, goal, ratio, method, preset, note, draft, tier, confirmation token, price, Xu balance, provider choice, job ID, output, or delivery URL into a browser query, form, storage entry, API payload, or database row.

The following stay on the existing generic `IMGTOOL_SOURCE_REVIEW_REQUIRED` boundary: any uppercase, suffix, template, or future value; all `prompt_*` values other than `prompt_manual`; `edit_ai*`, `ai_upscale*`, `edit_from_last`, `resize_continue`, `editor_save`, tier/confirmation, generated-variant, request, result, and back-navigation values. No provider, Bot, wallet/Xu, PayOS, job, output, or Telegram delivery operation is introduced.

## Verification

- Test exact allowlist entries, targets, intents, status, and boundary dispositions.
- Test case variants, suffixes, dynamic templates, AI/upscale, tier/confirmation, and prior-result callbacks stay fail-closed.
- Regenerate only static migration evidence from frozen Bot SHA `b29d0d474974075f4cba963d2c510f49d2d1b3e4`.
- Run focused audit and existing Web-native Image Operation contracts, static compile, JavaScript syntax, diff/secret checks, then independent spec and code-quality review.

## Scope decision

This is one bounded navigation-contract task. It does not change the Bot, route implementation, provider integration, billing, Web asset-processing engine, UI layout, Video module, or LocalVideoStudio26-owned files.
