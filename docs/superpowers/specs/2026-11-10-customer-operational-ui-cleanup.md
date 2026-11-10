# Customer operational UI cleanup — screenshot amendment, 10/11/2026

Owner screenshots show internal CoreBridge toast and Chờ cấp quyền badge, and
explicitly request removal of useless nonoperational UI. This is the next
separate release after in-flight PR708; do not mutate the checked PR head.
Tracker remains Issue #689. No engine/auth/payment permission is inferred.

Measured source root causes:

- `copyfast_api.py:667` supplies the technical guarded message; integration
  `api()` throws the exact envelope message and the action catch displays it.
  Keep failure visible but translate only known internal wording for customers;
  do not suppress errors or change status/CSRF/security/financial semantics.
- `renderAutoPostHub` unconditionally gives7static source rows the same waiting
  permission badge and renders3disabled destination cards without implementation.
  These are not measurements of current account permission. Remove these7rows,
  3disabled cards, metrics7/5/0,5step narrative and execution-boundary explanation.
  Keep exactly3actual route links for strategy/calendar/review, no blank wrapper.

| Task | Scope | Observable outcome |
|---|---|---|
|CUSTOMER-PUBLISHING-USEFUL-ONLY|one renderer+9newkeys|Only3real workflow launchers; no static permission/source/disabled/filler cards |
|CUSTOMER-BRIDGE-TOAST-COPY|one toast presentation function+13keys|13exact known legacy messages localized; unknown/error/status/timeout behavior preserved |

Both isolated output-only Antigravity tasks run in parallel. No current-PR source
write by workers. One combined acceptance after outputs: VI/EN/ZH, exact3links,
13toast mappings/unknown preservation/error ARIA,320/1440 native view. After
acceptance, separate Git/CI/merge/deploy/live reconciliation. No fake social
publishing, OAuth, provider/engine/job/payment or newly granted capability.

Broader redundant blocks in other routes remain to inventory and remove by
bounded renderer tasks. Customer/server content, data-changing forms, consent,
error recovery and real task/result state must never be removed as decoration.
M-FINAL stays last; this amendment moves actual new screenshot defects into the
current ordered queue, not a competing checklist or whole-goal closure.

Visual amendment: after6candidate configurations/18real navigations passed, the
old shared page/shell title still claimed automated posting. Update exactly
autopostHub.page.title/page.description and shellNav.autoPostHub inVI/EN/ZH to
honest Publishing/Đăng bài/内容发布 preparation metadata. Keep3toolactions and
all18navigationreceipts; only metadata renderer cases need an affected check.
