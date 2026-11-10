# Planner operation feedback — native screenshot prerequisite

BASE_SHA=e63f073f460e551438fbb8e3627ec232353f3efe; Issue #689, same batch.
The first owned native actual compose showed a mixed-language success toast
outside the page, despite clean fixed form copy. Limit correction to exact
known public messages in toast presentation; never suppress unknown errors.
Eight operation feedback keys per locale; existing13legacy mappings unchanged.

- [x] Known compose/save/stale/wait/validation messages use selectedVI/EN/ZH.
- [x] Unknown text, error role/type, dedupe/timer/ARIA remain unchanged.
- [x] Actual native compose/save feedback checked after completed worker group.

Only integration.js:toast and new remainingPlannerUi.operationFeedback keys.
No call-site, API, backend, auth, guard, provider, wallet or data changes.
Antigravity R1 output-only, full public MAP; no runtime/auth/customer data sent.

Coordinator source-extraction amendment before application: R1 included six
unrelated Motion messages and omitted actual server-success strings. R1 was
never applied. R1A has46exact messages, including one existing Video Idea
success string using the same plan-created category; this single adjacent
presentation message is explicitly included, with no action/flow change.
Two stale messages are categorized as stale, not waiting. This is a spec
correction, not a worker failure. Existing13legacy mappings remain protected.
