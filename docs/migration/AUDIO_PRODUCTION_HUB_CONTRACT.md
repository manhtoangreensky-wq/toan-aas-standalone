# Audio Production Hub — Web-native projection contract

## Purpose

`/audio-hub` is the app-first Audio Production Board for a signed Web account.
It presents the existing Media Workspace collection, revision, policy and
Asset Vault reference model in a compact production-oriented layout. It is a
visual projection only: there is no `audio_hub` database table, API namespace,
browser storage namespace, provider adapter or Bot state replica.

The compatible `/media-workspace` routes remain available as the full Audio
Library editor. A customer may choose either route family; both map to the
same owner-scoped collection UUID and server authority.

| Surface | Authority | Never introduced by this projection |
| --- | --- | --- |
| `/audio-hub`, `/audio-hub/new`, `/audio-hub/{collection_id}` | Portal route/render/hydration layer | New database, API, ledger, job, provider, player, waveform, raw URL or generated output |
| `/api/v1/media-workspace/*` | Existing standalone Web Media Workspace | Bot callback replay, Telegram state, provider request, wallet/Xu or PayOS mutation |
| `/media-workspace/*` | Existing compatible editor and API-backed model | Automatic redirect away from the customer-selected visual route |

## Route and read model

```text
/audio-hub                         -> existing summary/policy/list/events reads
/audio-hub/new                     -> same existing collection-create form
/audio-hub/{collection_id}         -> existing signed detail/policy/audio-asset reads
                                         (owner-scoped Media Workspace API)
```

All browser reads and writes remain under `/api/v1/media-workspace/*`. The
alias does not call `/api/v1/audio-hub/*` because that authority does not
exist. After a create or duplicate, the portal keeps the source route family:
an Audio Hub create opens `/audio-hub/{collection_id}`, while a Library create
opens `/media-workspace/{collection_id}`.

The board renders three auditable lanes:

1. **Brief & policy** — active collections, revision/policy guard and the
   authored creative brief boundary.
2. **Asset Vault assembly** — redacted owner-scoped music, SFX and reference
   attachments only; no bytes, player, waveform, streaming or preview.
3. **Direction review** — explicit links to Music Directions, SFX Cue Sheet
   and Audio Operations. These links do not prefill or carry collection,
   asset or account data through URL/query, browser storage or an implicit
   operation.

## Security and lifecycle guarantees

- Existing signed session, server-side ownership, CSRF, rate limit,
  idempotency and optimistic revision checks remain the only write boundary.
- A collection UUID never authorizes a read or write by itself. Detail and
  attachment data are hydrated again through the existing owner-scoped API.
- The Audio Operations handoff accepts either visual detail route and still
  performs one fresh `cache: "no-store"` Media Workspace detail read before it
  carries only an opaque Asset Vault UUID in immediate in-memory control flow.
- `/audio-hub` is explicitly private in the service-worker policy. It is not a
  public offline fallback or a shell-cache entry, so a prior account's brief,
  reference or revision cannot reappear after sign-out/account switching.
- The board never claims that music/SFX was generated, previewed, delivered,
  rendered, charged or completed. Provider, Bot, Key4U, Suno, PayOS, wallet/Xu
  and job state stay outside this module.

## Focused acceptance checks

- Deep links for list, create and UUID detail render through the normal portal
  shell and preserve the selected visual route through create/duplicate/refresh.
- Every hydration/mutation request remains an existing Media Workspace API
  call; no Audio Hub API, persistence or feature flag is introduced.
- Collection detail stays fail-closed on signed read failure and the original
  Media Workspace route remains functional.
- No player, media preview, provider/catalog request, raw source URL, query
  handoff, browser persistence or fake output exists in the Hub renderer.
- PWA and audio-operation handoff contracts cover the alias in addition to the
  original Audio Library route.
