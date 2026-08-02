# Aura Token Foundation Design

## Context

The Web App already has a teal/cyan Aura light/dark layer in
`static/portal/portal-theme.css`. The PDF reference and the signed design
master establish a calm, productivity-first system: light cyan canvas and
white work surfaces in light mode; slate-blue surfaces with teal/cyan accents
in dark mode. The next UI work must make spacing and component geometry
reusable before adding ERP data surfaces.

## Chosen approach

Use a token-only foundation owned by `portal-theme.css`:

- Add a complete 4/8px spacing scale (`--portal-space-*`).
- Add medium radius (`--portal-radius-md`) and preserve the existing small,
  default and large values.
- Add semantic elevation levels, icon sizes and scrim/blur tokens.
- Map every visual token to a dark-mode counterpart under the existing
  `--portal-dark-*` primitives; components continue to consume semantic
  `--portal-*` aliases.
- Replace the command/focus scrim and theme-control icon dimensions with the
  new aliases in the final theme layer. No route markup, API, provider, job,
  wallet, or Bot code changes are in scope.

This is preferred over migrating every legacy pixel value in one pass: the
canonical owner becomes stable without creating a broad visual regression
surface. Future ERP tables, KPI cards, Kanban lanes and mobile sheets can then
adopt the same tokens in isolated PRs.

## Alternatives considered

1. **Token-only foundation (chosen):** smallest diff, preserves route behavior,
   and makes future surfaces consistent.
2. **Rewrite all `portal.css` geometry now:** gives immediate global uniformity
   but mixes legacy routes and makes regressions hard to attribute.
3. **Add a second utility stylesheet:** avoids touching the owner but creates
   cascade ambiguity and violates the single-token-owner decision in `MASTER.md`.

## Contract and acceptance criteria

- `--portal-radius-md` is declared and every current reference resolves.
- Light and dark roots expose semantic spacing, elevation, icon and scrim
  aliases without raw colors in rendered rules.
- Command palette and mobile/sidebar backdrops use the scrim aliases.
- Theme-control and auth-context icons use the icon-size aliases.
- Existing theme switcher, focus-ring, reduced-motion and route contracts stay
  unchanged.
- No Bot, CSKH document, provider, payment, database, or production deploy
  changes are introduced.

## Verification

The focused contract test parses the canonical root and dark alias blocks,
checks the token set and key consumer selectors, and confirms no unscoped
custom properties are introduced. Existing Aura and teal/cyan contract tests,
Python compilation, JavaScript syntax checking and the repository whitespace
gate remain the final checks.
