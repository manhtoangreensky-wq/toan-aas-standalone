# Dashboard fallback feature-disposition backlog

Every row below was previously able to fall through to dashboard/catch-all navigation. It is now a required migration decision. `Candidate boundary` names the first contract to design; it does **not** claim that the route, runtime, provider, payment, job or output is already implemented.

| Priority | Bot family | Entries | Candidate boundary | Authority | Required next contract |
| --- | --- | --- | --- | --- | --- |
| P0 | menu | 184 | /features | Web capability catalog | Create an explicit menu-action catalog; never infer a destination from a button label or generic keyword. |
| P0 | vfinal | 130 | /video/finishing | Web-native private finishing or canonical Bot job bridge | Split safe editing choices from render/export/payment actions; require a verified source, idempotency, validated output and owner-scoped delivery before any runtime action. |
| P0 | unstructured | 95 | source_review_required | Source review required | Classify catch-all handlers and unstructured patterns with handler-level evidence before assigning any Web route or authority. |
| P0 | pkgbuy | 9 | /wallet/topup | Canonical Bot wallet/PayOS bridge | Expose only verified package/read/confirm contracts. The Web must not price, credit Xu, finalize PayOS or create a second webhook. |
| P0 | payosalert | 4 | TELEGRAM_ONLY | Canonical Bot PayOS/admin alert flow | Classify each alert action by source evidence; do not convert Telegram dismissal, test or renewal buttons into Web payment actions. |
| P0 | storage | 4 | /wallet/topup | Canonical Bot wallet/PayOS bridge | Keep storage purchase/credit changes canonical to the Bot until an owner-scoped bridge contract exists. |
| P0 | job | 1 | /jobs | Canonical Bot job bridge | Add only owner-scoped read/status projections first; retry/refund/charge/delivery require separate canonical action contracts. |
| P1 | adconcept | 107 | /video-studio/cinematic-concept | Web-native planning; runtime separately guarded | Map text concept choices to the cinematic planner; finalization/lock/runtime actions require an explicit capability contract. |
| P1 | vproduct | 67 | /video-studio/script-to-screen-planner | Web-native planning; runtime separately guarded | Map finite Script-to-Screen planning choices to a recomputed Web Video Plan; render/export stays a distinct runtime boundary. |
| P1 | storypack | 40 | /video-studio/storyboard-composer | Web-native planning | Map finite brief/concept/template choices to the signed storyboard composer and keep copy/export effects locally reviewable. |
| P1 | archive | 30 | /admin | Canonical Bot admin or separate Web admin archive | Separate Bot archive state from the isolated Web admin document archive; every write needs canonical role, CSRF, confirmation and audit evidence. |
| P1 | create_media | 25 | /media-factory | Web-native planning | Map Quick Idea choices to an explicit Media Factory blueprint; media generation and provider calls remain unavailable until a separate runtime exists. |
| P1 | marketing | 20 | /campaign-app | Web campaign planning and controlled operations | Map brief/KPI/schedule choices to account-owned campaign plans; publishing and canonical analytics remain separately authorized. |
| P1 | docflow | 19 | /documents | Web-native private document operations | Map document selection/confirmation only to validated Asset Vault-backed operations; preserve output validation and private delivery constraints. |
| P1 | opmenu | 11 | /admin | Server-authorized Admin ERP | Map every operations category to a role-checked ERP module; browser navigation must never grant Bot/admin authority. |
| P1 | motion | 8 | /video-studio/image-motion-planner | Web-native planning | Map finite motion suggestions to the owner-scoped Image Motion planner; source inspection/rendering remains a separate capability. |
| P1 | tvflow | 5 | /video-studio | Source review required | Recover the exact Bot handler state machine before mapping cancel/rewrite/confirm actions; do not infer a render or content mutation contract. |
| P1 | tr_pick | 1 | /dubbing | Web-native subtitle/dubbing boundary | Require an explicit owner-scoped source selection contract before mapping Telegram file-pick actions. |
| P2 | lang | 7 | /account | Signed Web profile locale | Map supported UI locales through the signed account preference. Bot-only languages need a reviewed locale bundle before being advertised. |
| P2 | aspect_ratio_orphan | 6 | parent_workflow_required | Parent Web workflow | Resolve orphan ratio tokens from their source keyboard/handler before mapping; a ratio alone must not become a global browser action. |

Before a row leaves this backlog, preserve the source evidence and add focused tests for signed authorization, CSRF where a Web write exists, canonical ownership, idempotency where relevant, safe guarded state, and validated private delivery for any output.
