# Aura ERP Data Surfaces Design

## Context and approval

This focused PR continues the already-approved Aura application system: a
teal/cyan, application-first Web App with light and dark themes, dense but
readable ERP tables, and truthful operational states. The user explicitly
asked the work to continue sequentially without waiting between the already
approved UI/core slices. The deferred CSKH documents and every Bot file remain
out of scope.

## Safety review and chosen design

The generic Users, Payments and Jobs adapters do not publish a server-side
search/filter contract. A browser search would be misleading for paged
responses and could inspect redacted fields such as an order or user
identifier. Therefore this PR does **not** add a generic local search or a
new request/filter parameter.

Instead, each generic non-Audit Admin table receives one compact
`portal-admin-data-surface` above its existing semantic table:

- It reports either the exact number of rows supplied in this response, or an
  explicit unavailable state when `items` is absent/malformed. It never treats
  missing data as zero.
- It shows a textual, existing status badge that distinguishes redacted
  read-only data, a compatibility guard, and unavailable read data.
- It preserves `renderDataTableWrap`, the keyboard-focusable horizontal scroll
  region, current refresh capability, empty state, notices and all server
  authority boundaries.
- Audit Explorer keeps its separately allowlisted server-side category filter,
  pagination and read model. The generic toolbar never duplicates or replaces
  it.
- Numeric table cells distinguish a real `0` from `null`, empty and malformed
  values (`—`). Ticket status cells retain their canonical textual label beside
  any visual badge; `failed_no_charge` receives shared failure styling across
  Admin tables.

## Visual rules

- Consume only `--portal-*` semantic Aura tokens. Light surfaces stay white
  on the cyan canvas; dark mode uses the pre-existing slate surfaces with
  teal/cyan focus/context.
- Use the existing 4/8px spacing, tokenized medium radius/elevation, tabular
  figures for counts and a dense table-led hierarchy. No cardification of
  data rows or page-level horizontal overflow.
- Status meaning is always text plus the existing badge styling; unavailable
  or guarded sources must never be represented by decorative KPI values.
- The toolbar has no new interactive control, request, storage key or URL
  state. Existing refresh/write controls retain their own capability and CSRF
  behavior.

## Boundaries

This is frontend presentation only. It changes neither `bot.py`, bridge
contracts, signed sessions, CSRF, roles, Core Bridge endpoints, PayOS/Xu
ledger authority, provider calls, file downloads, Railway, nor the deferred
CSKH workflow documents.

## Acceptance criteria

- Generic Admin module tables show a source-backed row count only when the
  current read model actually provides an `items` array; absent data is marked
  unavailable/guarded rather than shown as `0`.
- No generic local or server filter/search is added. Audit retains its
  allowlisted server-side filter path unchanged.
- Empty and compatibility-guarded adapters preserve the current notice,
  empty-state wording and disabled refresh state; no fake metric, revenue,
  job, provider or completion claim is introduced.
- Numeric `0` remains visible while `null`, blank and malformed numeric values
  render as `—`; ticket `closed` remains textually `Đã đóng`.
- Every new fixed toolbar string has reviewed Vietnamese, English and
  Simplified Chinese catalog entries; server data remains untranslated.
- At desktop and 375px width, toolbar, table wrapper, badges and actions
  remain aligned, reachable and readable in both themes.
- No new raw colours, Bot edits, backend calls or production changes enter
  the branch.
