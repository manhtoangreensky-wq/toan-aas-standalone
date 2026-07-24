# IMGTOOL Web-native disposition

## Decision

`imgtool|*` is a frozen Telegram transport namespace, not a browser protocol.
The standalone Web App must never deserialize, forward, infer intent from, or
execute an `imgtool` callback.  The Image Hub is instead a finite set of
**fresh Web navigations**.  It is a visual/app-first alias of the existing
Image Creative Studio authority, not an Image Tools callback adapter and not a
second image runtime:

```text
/image-hub[/new|/{uuid}]
  -> signed Web session and a newly entered Web-owned direction
  -> existing /api/v1/image-studio/* authority

imgtool|* from Telegram
  -> source-review record only; never a route, API input, draft, job or output
```

The alias may improve the customer-facing navigation, but it must preserve the
Image Creative Studio model and its owner checks.  It does not create an
`/api/v1/image-hub` API, a new database authority, a feature flag, a provider
adapter, a payment path or a Bot bridge.

## Source evidence

| Evidence | What it proves |
| --- | --- |
| [`CALLBACK_HANDLER_DISPATCH_MAP.md`](CALLBACK_HANDLER_DISPATCH_MAP.md) | `handle_image_tools_callback` is registered for `^imgtool\\|` at frozen `bot.py:129161` as `telegram_transport` / `NOT_BROWSER_ACTION`. |
| [`IMAGE_TOOLS_CALLBACK_CONTRACT.md`](IMAGE_TOOLS_CALLBACK_CONTRACT.md) | Every known `imgtool|*` literal and every spelling outside an exact future review is `IMGTOOL_SOURCE_REVIEW_REQUIRED`; the handler uses Telegram caller, pending/result/file/prompt/memory state and can reach local output, ShopAI, canonical Xu/provider and Telegram delivery. |
| [`FALLBACK_FEATURE_DISPOSITION.md`](FALLBACK_FEATURE_DISPOSITION.md) | The audit inventory contains 210 `imgtool` entries and leaves the family at `SOURCE_STATE_MACHINE_REQUIRED`, not a generic dashboard/image fallback. |
| [`NON_VIDEO_MENU_NAVIGATION_CATALOG.md`](NON_VIDEO_MENU_NAVIGATION_CATALOG.md) | A small, separate `menu|*` grammar has already been reviewed for fresh, signed Web navigation.  It is the only image-domain source evidence that can support a new blank Web entry. |
| [`QUICK_IMAGE_PLANNER_CALLBACK_CONTRACT.md`](QUICK_IMAGE_PLANNER_CALLBACK_CONTRACT.md) | The finite Quick Image planning grammar is a different `create_media` contract.  It creates a text plan only and does not widen `imgtool|*`. |
| `reports/migration/bot_inventory.json` | Static evidence records the frozen lowercase `imgtool|*` inventory; it is audit input only and must not be shipped to the browser. |

## Finite positive Web navigation dispositions

The rows below are deliberately small.  They are private static-auditor
decisions, not callback values in a URL, query string, fragment, form field,
browser storage key or API payload.  Each destination begins blank under the
signed Web account and independently enforces its own authorization.

| Reviewed source grammar | Fresh Web destination | Scope of the positive disposition | State that is **not** transferred |
| --- | --- | --- | --- |
| `menu|hint_image_tools`, `menu|guide_image_ai` | `/image-studio` (current frozen navigation catalog) | Opens an empty Image Creative Studio workspace. Image Hub is a separate customer-selected visual route, not a changed callback mapping. Direct Hub routes are only `/image-hub`, `/image-hub/new`, and `/image-hub/{uuid}` where `{uuid}` is a validated Web-owned record ID. | Raw callback, Telegram identity, file ID, pending/result/image/prompt/note/memory state, ShopAI tier/token, quote, provider/job state, Xu/payment/PayOS state and Telegram delivery state. |
| `menu|image_prompt_start` | `/image/prompt-composer` | Fresh, bounded text-direction composer; this is not an Image Hub execution request. | Any pending Telegram image, source callback, provider request, output or delivery. |
| `menu|image_edit_start` | `/image/edit` | Independent deterministic Image Operations entry; its source must be selected again from an owner-scoped Web Asset Vault reference. | Telegram media, image-editor state, operation result, provider/job/payment state. |
| `menu|image_upscale_start` | `/image/upscale` | Navigation to the separately guarded Web runtime only; navigation itself cannot call a provider. | Telegram source image, selected tier, quote, confirmation, Xu/payment/job/output state. |
| Exact `create_media|quick_image` / `qi_*` literals enumerated in `QUICK_IMAGE_PLANNER_CALLBACK_CONTRACT.md` | `/image/quick-planner` | Separate fresh prompt/ratio/brand-direction plan.  It is included here only to prevent the similarly named Bot image grammar from being mistaken for `imgtool`. | Bot callback bytes, Telegram image/logo, tier/confirmation, provider/job/payment/output/delivery state. |

The current first-row mapping remains `/image-studio` and retains the existing
`/api/v1/image-studio/*` API/model. A direct `/image-hub` visit is a
customer-selected visual alias; it does not alter a reviewed `menu|*` mapping
and it never converts an existing raw `imgtool|*` callback into a browser
route.

## Fail-closed disposition for the complete IMGTOOL family

| Source form | Required disposition | Browser behavior |
| --- | --- | --- |
| Every known lowercase `imgtool|*` literal or template | `IMGTOOL_SOURCE_REVIEW_REQUIRED` | No navigation, reset, API request, draft creation, asset lookup, image edit/generation, output display or success claim. |
| Case changes, missing segments, extra segments, suffixes, unrecognized values and future `imgtool|*` values | `IMGTOOL_SOURCE_REVIEW_REQUIRED` | Same fail-closed result.  It must not inherit `/image-hub`, `/image-studio`, `/image/*`, wallet, checkout, support or a generic dashboard route. |
| Any deep `/image-hub/*` value other than the exact root, `/new`, or a validated Web-owned UUID route | Invalid Web route | Render the normal not-found/safe route result; do not coerce it into an Image Studio record, a generic image menu or a Bot-state recovery flow. |
| Any request carrying a callback, Telegram UID/chat/message/file ID, Bot pending/result ID, provider/tier, payment/reference, job ID or delivery/output claim | Invalid Web handoff | Reject/ignore it before Web draft or operation hydration.  No query, fragment, local/session storage or API compatibility path may become a side channel. |

This catch-all is intentional.  A familiar button label, callback prefix or
image-looking identifier is not a substitute for a reviewed Web contract.

## Boundary invariants

1. A direct `/image-hub` visit is fresh navigation, never a replay of
   `handle_image_tools_callback`.
2. The Image Hub uses the signed Web session and server-side ownership checks.
   Web writes retain CSRF protection and the existing Image Creative Studio
   lifecycle; a browser-provided account, role or asset identifier grants no
   authority.
3. The Hub may render Web-owned draft/history metadata only.  It cannot read
   Bot `USER_PENDING`, Telegram message/media IDs, Bot prompt/note/memory
   records or Bot result caches.
4. The Hub does not call a provider, create/retry/refund a job, quote or debit
   Xu, create/finalize/replay PayOS, or claim an image was produced/delivered.
   Those behaviours require separate explicit Web-native contracts.
5. Image Creative Studio, deterministic Image Operations and Quick Image
   Planner remain separate authorities.  No Image Hub alias may silently
   cross-load their drafts, Asset Vault references, lifecycle records or
   execution endpoints.
6. Private Image Hub pages and private Image Studio APIs remain outside PWA
   shell caching.  A service worker must not make a previous account's draft,
   asset or operation appear offline to another session.

## Acceptance checks

- Static checks must prove that Image Hub has only its finite direct routes,
  that the frozen menu catalog remains unchanged, and that the API remains
  `/api/v1/image-studio/*`.
- A direct Image Hub navigation must create/read only Web-owned state and must
  contain no raw callback value in the rendered DOM, URL or request payload.
- Unknown `imgtool|*` data and malformed Image Hub deep links must fail closed
  without browser navigation or an execution side effect.
- Tests must cover signed session/CSRF/ownership boundaries, route validation,
  no-store/private PWA scope, and the absence of provider, job, Xu, PayOS and
  Telegram delivery calls from the Image Hub path.
