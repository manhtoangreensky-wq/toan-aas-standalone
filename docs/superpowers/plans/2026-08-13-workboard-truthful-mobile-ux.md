# Plan: Workboard truthful states and mobile Kanban

1. Add a focused static contract for the Workboard read-state gate, viewer
   create affordance, guarded create route, and mobile one-column rules.
2. Run that contract on the base revision and record the expected RED result.
3. Update `static/portal/portal.js` so non-ready states short-circuit before
   metrics/board rendering, tabs receive capability context, and `/new` uses a
   recovery card instead of a disabled form when unavailable.
4. Add scoped `@media (max-width: 700px)` rules to
   `static/portal/portal-theme.css` for a one-column Kanban without page
   overflow.
5. Run focused and regression contracts, JavaScript syntax and diff checks.
   Render the Workboard in a local browser at desktop and 375px, exercising
   the recovery navigation. Review the diff and commit/push the isolated
   branch; do not merge or deploy in this slice.
