# TOAN AAS Product Harmony — Teal–Sky UI/UX Design

## Purpose

Create one recognisable TOAN AAS product system across the public landing and
the signed Workspace without turning the Workspace into a marketing page.

- `toanaas.vn` explains the product, shows the honest workflow and guides a
  visitor into the right entry point.
- `app.toanaas.vn` is the application: customers plan, create, review and
  manage work; administrators operate the ERP.
- Both surfaces use the same visual language and the same Vietnamese-first
  terminology. They differ by job, information density and access level.

The public landing source is a separate repository concern. This Web App PR
only changes the standalone Web App. A follow-up Landing-only PR will apply
the same approved system to `toanaas.vn` without changing Bot logic.

## Shared visual system

The semantic tokens in `static/portal/portal-theme.css` remain the canonical
source of colour. New component rules consume tokens rather than introducing
page-local hex values.

| Role | Token/value | Use |
| --- | --- | --- |
| Product ink and desktop rail | `--portal-ink` / `--portal-rail` (`#083344`) | headings, navigation rail, high-trust anchors |
| Primary action | `--portal-action` (`#0f766e`) | exactly one main action per screen; white label |
| Brand support | `--portal-brand` (`#14b8a6`) | mark, non-critical emphasis, selected supporting detail |
| Context and focus | `--portal-context` (`#0284c7`) | keyboard focus, current location, informational state |
| App canvas | `--portal-app-canvas` (`#f4fbfc`) | signed app page background |
| Working surface | `--portal-surface-light` (`#ffffff`) | forms, cards, tables and dialogs |
| Borders and secondary copy | `--portal-border`, `--portal-muted` | structure and readable supporting information |

No purple/pink, decorative gradients, dark customer canvases, fake charts,
fake outcomes, stock photos or unverified provider/payment claims appear in
the delivered interface. The only dark large surface is the desktop
navigation rail. Motion stays within 150–220ms and respects
`prefers-reduced-motion`.

## Layout and component rules

### Public companion (`/welcome`)

- Keep a 1240px maximum public rail and one balanced two-column hero on
  desktop. Header, hero, workflow and footer share the same left/right edges.
- Use one direct product statement, a factual explanation of Workspace and
  Telegram roles, two real entry actions, then the common four-step workflow:
  `Bản nháp → Ước tính → Xác nhận → Bàn giao`.
- The public introduction is explanatory only; it never renders the signed
  sidebar, account data, wallet, jobs, provider readiness or admin controls.

### Customer Workspace

- Keep the persistent deep-teal desktop rail, but make the page canvas light,
  quiet and task-first. The selected route is a sky contextual state, not a
  second brand colour.
- The command bar uses breadcrumb, search, current account and one primary
  page action. Headings, card headers, table columns and action rows align to
  a shared 4/8px rhythm.
- Dashboard cards may show only source-backed facts or explicit empty,
  guarded or unavailable states. A table/list is preferred to decorative
  card duplication when the user must scan work.
- At phone width, use 16px gutters, 44px controls and a labelled five-item
  dock for the top-level customer destinations. Scroll content receives
  enough bottom inset to clear the dock.

### Admin ERP

- Preserve canonical signed-admin and route-authority protections.
- Use the same rail, header, action and focus system, with a denser table-led
  information hierarchy: operational filters, factual summaries, priority
  table and guarded system context.
- Status always has a textual label. Unknown/guarded integrations use honest
  language instead of fabricated figures, revenue or uptime.

## Vietnamese-first language and locales

Fixed UI copy is Vietnamese-first: concise, direct and clear for a new user.
Examples are `Tạo luồng công việc`, `Mở Project Center`, `Việc cần làm tiếp
theo`, `Đang bảo vệ`, and `Chưa có dữ liệu`. Avoid literal Bot command names,
technical jargon and ambiguous calls to action.

English and Simplified Chinese retain the same hierarchy, action intent and
safety meaning. They translate fixed chrome only; account records, asset
names, user prompts, canonical status values and other server data remain
unchanged.

## Safety and compatibility boundaries

This is a presentation and information-architecture improvement only. It
does not modify Bot ownership, Core Bridge contracts, signed session/CSRF
rules, role checks, PayOS/Xu writer authority, provider execution, webhooks,
private-download validation or PWA private-cache exclusions.

## Acceptance evidence

- At 1440, 1024, 768 and 375px, key content has no horizontal overflow,
  clipped action or broken alignment.
- Primary/surface/body text and focus states meet the existing contrast
  contract; every icon action is labelled and every touch action is at least
  44px on mobile.
- `/welcome`, signed customer routes and `/admin/*` retain their existing
  access, ownership and guarded-state behaviour.
- Vietnamese, English and Simplified Chinese fixed chrome render equivalent
  intent.
- The landing implementation is submitted in a separate Bot-repo PR; the
  Web App branch never includes `bot.py`, wallet/PayOS/provider changes or
  production environment changes.
