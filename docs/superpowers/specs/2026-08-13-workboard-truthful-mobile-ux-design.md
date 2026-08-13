# Workboard truthful states and mobile Kanban

## Goal

Make the Web-native Workboard honest and usable when its signed projection is
loading, unavailable, guarded, or read-only. The surface must never imply that
zero records are known when the server has not supplied a trustworthy result.

## Decisions

- `workboardReadState` is the source of truth for the overview and create
  route. Only `ready` may render KPI values, an empty board, or a create form.
- `loading`, `failed`, and `guarded` render a bounded recovery card with a
  state-specific message and a safe navigation action. They do not render
  metrics, a board, or a create CTA.
- A viewer can still open Workboard and list/read records, but the create tab
  becomes a non-link “Chỉ xem” affordance. It must not be an `href` with
  `aria-disabled`, because that remains keyboard-activatable and misleading.
- `/workboard/new` renders a guarded recovery card when creation is not
  authorized or the signed projection is not ready. It never renders a
  disabled form as if submission were available.
- At widths up to 700px, Kanban columns become one vertical column, the board
  has no minimum desktop width, and its card container does not create page
  horizontal overflow. Desktop keeps the existing five-column layout.

## Boundaries

No changes to integration/API contracts, bot code, provider/payment/wallet
logic, service-worker private caching, or route registration are included.
The change is presentation-only and keeps existing server ownership checks.

## Verification

Static contract tests prove the state gates and CSS rules. Existing Workboard
and teal/cyan presentation contracts remain regression checks. `node --check`
proves the edited client remains syntactically valid; browser QA checks the
overview and create recovery states at desktop and 375px.
