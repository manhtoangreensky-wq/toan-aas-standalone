# TOAN AAS Unified Teal–Sky UI Design

## Decision

Adopt one calm technology design system across the app-owned public entry,
access screens and signed Workspace.  The public surface is cool-light and
welcoming; the signed Workspace is deep teal and operational.  They share
the same sea-teal primary action, sky-blue contextual/focus color, typography
scale, border geometry, motion and Vietnamese-first wording.

This is an application redesign, not a change to Bot, Core Bridge, payment,
wallet, provider, job, delivery or session authority.

## Reference concepts

- Dashboard desktop: `C:\Users\toann\.codex\generated_images\019f4b14-cdaa-7d90-8869-cf654fcab17a\exec-64d4173a-1041-48a8-94bc-c1dd6353fde9.png`
- Public landing desktop: `C:\Users\toann\.codex\generated_images\019f4b14-cdaa-7d90-8869-cf654fcab17a\exec-02b327d1-8bf6-4b86-b831-687927c4097f.png`
- Access screen desktop: `C:\Users\toann\.codex\generated_images\019f4b14-cdaa-7d90-8869-cf654fcab17a\exec-fab0adea-e882-43b0-8b72-f0f33a732614.png`
- Workspace mobile: `C:\Users\toann\.codex\generated_images\019f4b14-cdaa-7d90-8869-cf654fcab17a\exec-de34fbea-06ea-4b9b-9193-53b1b5b02f29.png`

The generated dashboard’s placeholder counts, names and success claims are
not product content.  Production continues to render only existing
owner-scoped read models and explicit guarded/empty states.

## Palette and tokens

| Role | Value | Purpose |
| --- | --- | --- |
| App canvas | `#062A36` | Signed Workspace background |
| App surface | `#0B3440` | Cards, sidebar and table surfaces |
| Elevated surface | `#104352` | Explicit grouped/selected surfaces |
| App border | `#246070` | Quiet structural separation |
| Primary teal | `#14B8A6` | One primary action and selected emphasis |
| Teal hover | `#2DD4BF` | Hover/pressed primary feedback |
| Sky context | `#38BDF8` | Focus, links and informational context |
| Light canvas | `#F4FBFC` | Public/access background |
| Light surface | `#FFFFFF` | Public/access cards |
| Light border | `#D7ECEF` | Light surface structure |
| Dark ink | `#092B36` | Public/access heading and body ink |

All new CSS uses semantic `--portal-*` tokens.  No component may introduce
a raw hex literal after the final token declaration.  Semantic status colors
remain text-labelled and are never the only state signal.

## Layout system

- Desktop content has a consistent maximum width and shared left/right edges.
  Landing sections use one public container; signed pages use one app content
  container.  Nested cards do not invent a second grid.
- Public landing has a concise header, text-plus-workflow preview hero,
  capability, workflow and trust sections with deliberately varied rhythm.
  The preview is explanatory UI, not a claim of live job/output activity.
- Login and registration use a centred, bounded access flow.  The short intro
  and form have equal visual weight; no giant heading wraps individual words
  or pushes the form below the first viewport.
- Signed app retains data-first sidebar/header/table anatomy.  Shared cards,
  tables, buttons, forms and statuses align to the same 4/8px rhythm.
- Mobile starts at 16px gutters, preserves 44px touch controls, wraps action
  groups predictably and keeps the existing five-or-fewer-item bottom
  navigation.  Tables retain their established safe mobile treatment rather
  than becoming fake metric cards.

## Typography, copy and localization

- Use the existing performant system/Inter stack with Vietnamese and Chinese
  fallbacks; use a consistent 12/14/16/20/28/40 responsive scale rather than
  one-off sizes.
- Public/customer copy is Vietnamese-first, concise and task-oriented:
  “Tạo nội dung”, “Dự án”, “Công việc”, “Tài sản”, “Dữ liệu đã xác minh”.
  Technical `canonical`, provider and ledger language remains available in
  contextual detail/admin surfaces, never as unexplained hero copy.
- All changed fixed customer-visible text has reviewed `vi`, `en`, `zh`
  entries.  Customer names, job IDs, project/asset titles, dates, amounts and
  provider/server data remain unmodified by the display locale.

## Interaction and safety invariants

- Preserve signed sessions, CSRF, ownership checks, feature readiness,
  guarded states, no-fake-output rules, PWA private-cache boundaries and all
  existing routes/actions.
- Minimum control height is 44px on touch layouts; focus rings meet contrast
  requirements on light and dark surfaces.  Motion is 150–220ms opacity or
  transform only and honours `prefers-reduced-motion`.
- `/welcome` is the app-owned public companion in this repository.  The
  separately hosted `toanaas.vn` source is not present in this repository.
  Its verified source is the Bot repository's root `index.html`; it must be
  changed in its own clean worktree and PR rather than copied into the app
  repository or implemented by editing `bot.py`.

## Verification ledger

### Contract and safety checks

- The focused UI contracts cover the teal–sky token root, shared chrome,
  public landing, access flow, Workspace command center, i18n keysets and
  public/private cache boundary.  The final targeted run passed with no
  formatting error.
- PWA manifest, offline fallback and document `theme-color` now share the
  canonical Workspace canvas (`#062a36`).  The shell build ID includes all
  three artifacts, so a deployment uses a fresh public-shell cache generation.
- The PWA allow-list and service-worker policy remain public-shell only;
  wallet, payment, account, admin, API and private-file routes are not added
  to offline caching.

### Visual checks

- Reviewed the four approved reference concepts listed above and checked the
  local app with provider and payment calls disabled.
- At mobile width, `/welcome?lang=vi` keeps a single aligned container,
  readable Vietnamese action labels, 44px actions and an explanatory workflow
  preview without customer data, output, metrics or completion claims.
- `/login` and `/register` retain real labelled email/password forms, the
  compact language selector, optional provider disclosure and the signed-session
  boundary.  Their visible `vi`, `en` and `zh` fixed copy uses the reviewed
  catalogue rather than changing identity or canonical values.
- The signed shell keeps its sidebar/header/table anatomy and a five-item
  mobile navigation.  Cards, table dividers, primary actions and guarded
  states use the shared deep-teal/surface/sky token family; no dashboard
  metric, provider state or completion result was invented for presentation.

### Intentional scope boundaries

- This PR owns `app.toanaas.vn` and app-owned `/welcome` only.  The root
  `toanaas.vn` landing will be handled next through a separate Bot-repository
  PR limited to its existing `index.html`, after a read-only Railway domain
  ownership check.  `bot.py`, PayOS, webhook and Telegram behavior remain
  untouched.
