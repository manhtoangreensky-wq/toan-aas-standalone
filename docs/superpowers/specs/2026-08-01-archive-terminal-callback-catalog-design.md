# Archive Terminal Callback Catalog Design

## Intent

Close only four frozen-Bot Archive callbacks that are proven to depend on
Telegram-local pending state, while retaining the existing Web-native Admin
Internal Document Archive as a separate, signed-admin product.

The affected exact lower-case source literals are:

- `archive|back_department`
- `archive|change_dept`
- `archive|discard_to_dept`
- `archive|edit`

The frozen handler reads or updates `get_internal_archive_pending(uid)`, moves
the Telegram conversation through preview/department/metadata states, or
requires the pending record. Those transitions have no safe Web equivalent:
the Web archive owns different records, versions, identities, CSRF and
idempotency controls.

## Decision

Use a finite raw, case-sensitive terminal catalog. Each literal maps only to a
static audit envelope with `target` and `status` equal to `TELEGRAM_ONLY`, an
admin classification, explicit Bot-pending-state dispositions, static source
evidence, and `NO_RUNTIME_CLAIM`.

This is a non-Web safety disposition, not Archive runtime feature parity. It
does not create a route, browser capability, request, Web record, job, output,
provider call, payment, wallet change or external effect.

## Exactness and drift handling

The Archive mapper must use raw source values for every finite registry lookup.
It may use a normalized value only to recognize the Archive namespace and send
an upper-case/case-mixed value to the source-review boundary. Therefore all of
the following remain `NEEDS_FEATURE_DISPOSITION` with no route or launch
metadata:

- case variants such as `ARCHIVE|BACK_DEPARTMENT`;
- whitespace/suffix variants such as `archive|edit ` and
  `archive|back_department|future`;
- dynamic templates such as `archive|dept|{*}`; and
- every future unlisted Archive value.

Existing exact fresh navigation literals (`archive|root`, `archive|help`, and
the reviewed finite directory entries) keep their fresh signed Admin Archive
disposition. Existing `archive|preview` and `archive|save` remain
Telegram-only under their existing pending-record/delivery contract.

## Evidence and verification

The static audit report should move the nine frozen callback occurrences for
the four exact literals from `NEEDS_FEATURE_DISPOSITION` to `TELEGRAM_ONLY`.
The two dynamic `archive|dept|{*}` occurrences remain in the Archive backlog,
so future Bot drift stays visible.

Focused verification will prove the raw allowlist, terminal envelope, no-route
shape, case/suffix/template failure boundary and regenerated frozen evidence.
The existing Archive runtime test remains a regression check only; no runtime
Archive implementation changes are in scope.

## Non-goals

Do not edit `bot.py`, change the Web Archive API/UI/storage model, enable an
Archive flag, call Telegram, provider, PayOS, wallet, job or Railway runtime,
or touch Video/LocalVideoStudio/motion-kit/OpenMontage areas.
