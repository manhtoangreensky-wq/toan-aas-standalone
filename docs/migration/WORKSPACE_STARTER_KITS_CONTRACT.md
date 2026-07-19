# Web-native Workspace Starter Kits

`Workspace Starter Kits` gives a signed Web account a deliberate, bounded way
to start a Project.  A confirmed kit writes one Web-owned Project, its reviewed
Studio Documents, and one Workboard card with a checklist in one SQLite
transaction.  It is a planning and coordination surface, not an engine or a
shortcut around the Bot.

## Scope and catalogue

The catalogue is source-reviewed and closed.  The browser may only select a
known key and matching version; it cannot submit a title, document content,
checklist, project reference, or arbitrary workflow instruction.

| Key | Web-owned records | Purpose |
| --- | --- | --- |
| `project-foundation` | Project, 2 documents, 1 card | A first reviewable Project brief. |
| `content-foundation` | Project, 3 documents, 1 card | Content planning and editorial review. |
| `image-direction` | Project, 3 documents, 1 card | Art-direction planning without image generation. |
| `voice-script` | Project, 3 documents, 1 card | Script and consent-review preparation without audio creation. |
| `audio-brief` | Project, 3 documents, 1 card | Audio direction and rights-review preparation. |
| `subtitle-plan` | Project, 3 documents, 1 card | Subtitle/localization planning without ASR, translation, or dubbing. |
| `document-qa` | Project, 3 documents, 1 card | Document intake and quality-review preparation. |
| `operations-board` | Project, 2 documents, 1 card | Operational review and coordination planning. |

Video workflows are deliberately **not** part of this catalogue.  They retain
their separately changing product scope and must not be inferred from a
Starter Kit.

## API and state

| Route | Access | Meaning |
| --- | --- | --- |
| `GET /api/v1/workspace/starter-kits` | signed session | Returns the owner-scoped catalogue, setup profile, installation projection and explicit effect boundary. |
| `POST /api/v1/workspace/starter-kits/{kit_key}/apply` | signed session + CSRF | Installs one closed kit after explicit confirmation. |

The POST accepts only `kit_version`, `expected_setup_revision`, `confirmed`
(strict `true`) and an idempotency key.  It requires a completed Workspace
Setup profile.  A stale revision, reused key with different input, duplicate
kit, disabled Workboard, capacity limit, or disabled Starter Kits feature is a
truthful guarded/conflict response; it never leaves a partial Project.

Successful responses use `status: "draft"`.  This describes draft Web records,
not a generated output, finished job, or delivery.

## Persistence and atomicity

The installation ledger is `web_workspace_starter_kit_installs`.  It records a
catalogue digest, setup profile revision, project ID and counts.  The same
transaction writes:

- `web_projects`;
- `web_studio_documents` and immutable `web_studio_document_versions`;
- `web_workboard_items`, its project reference, checklist entries, immutable
  item/checklist versions, and the `starter_kit_seeded` Workboard event;
- a scoped, 24-hour idempotency receipt and `web.starter_kit.apply` audit
  event.

Each account may install each closed key once.  A failed write rolls back the
entire bundle.  The module has a 1024 receipt cap per account and a 8 KiB raw
write-body cap before JSON parsing.

## Trust boundary

Every response contains a boundary object.  This module never calls or mutates
the Telegram Bot, Core Bridge, provider, job queue, wallet/Xu ledger, PayOS,
publication, notifications, media asset, or delivery system.  It does not
claim that a file, media, engine output, payment, or external action exists.

`WEBAPP_STARTER_KITS_ENABLED` controls the catalogue (default enabled for
local/test).  Applying a kit additionally requires
`WEBAPP_WORKBOARD_ENABLED`; if Workboard is unavailable, no Project is
created.  These flags are product-readiness controls, not authorization.

## Portal and offline scope

The signed Portal exposes `/starter-kits` and only eight closed detail routes.
It has a confirmation checkbox before the single create action and shows the
record counts and Web-only boundary before the user decides.  Starter Kit pages
and APIs are private PWA paths: they are never added to the public shell or
cached as user data.

## Verification focus

Focused tests cover session/CSRF/body cap, setup and flag guards, atomic
records, ownership, audit evidence, replay/collision behavior, rate limits,
closed route rendering, safe PWA scope, and absence of a fake engine/video
path.  Provider, payment, Bot and live deployment flows are intentionally out
of scope for this contract.
