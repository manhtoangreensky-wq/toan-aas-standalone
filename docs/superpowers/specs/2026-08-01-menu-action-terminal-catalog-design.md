# P0 Menu Action Terminal Catalog Design

## Goal

Finish the static disposition of every observed `menu|...` callback and
`menu|...` template without treating a Bot button label as a Web route,
provider request, payment operation, job action, user identity, or output.
The result is a closed migration catalog: each observed Menu callback has one
truthful terminal result—an existing fresh Web navigation only where an
independent contract already exists, or `TELEGRAM_ONLY` otherwise.

## Context

The parity report still records 61 P0 Menu mappings as
`NEEDS_FEATURE_DISPOSITION`. The unresolved exact values cover canonical
finance/tax calculations and exports, administrator maintenance/package/
provider commands, job recovery/refund actions, and Video-only hints. The
unresolved templates cover unreviewed `menu|{*}` and locale/confirmation
suffixes. None supplies a safe browser-owned record, authority, or execution
contract.

The product direction is explicit: Web is an independent professional product,
Bot remains unchanged, and Video-menu work is handled last. Therefore this
catalog must close unsafe fallthroughs now while retaining a clear future path
for a separately reviewed Web-native workflow or canonical bridge.

## Options considered

1. Infer a destination from callback labels or prefixes.

   This would make the audit look complete but could turn a Bot confirmation,
   tax/export command, or provider test into a false Web action. Rejected.

2. Add a finite terminal catalog, using existing independently authorized Web
   guidance/navigation records only where source evidence already proves that
   boundary; mark all remaining exact and templated Bot actions
   `TELEGRAM_ONLY` with an explicit reason. Recommended.

3. Build a private Bot bridge or reimplement the underlying commands now.

   This needs a separate authority, ownership, estimate/confirm, ledger,
   provider/job, delivery, and production verification contract. It is out of
   scope for this static P0 boundary.

## Design

### Finite source classes

The catalog is private to `scripts/migration/audit_bot_to_web.py`. It never
feeds raw callback values to `copyfast_registry.py`, the Portal, URL query
parameters, browser storage, PWA cache, or a Web API.

| Source class | Terminal disposition | Why |
| --- | --- | --- |
| Existing reviewed read/guidance navigation | retain its existing exact Web mapping | The destination repeats signed account/admin authorization and receives no Bot value or state. |
| Admin maintenance, package grant/look-up, provider test, job refund/recovery confirmation | `TELEGRAM_ONLY` | These are Bot command, canonical state, or mutation boundaries. |
| Tax estimate, tax profile, tax export and finance-compliance update | `TELEGRAM_ONLY` | Web guidance exists, but no Web canonical finance calculation/profile/export/write contract exists. |
| Video/menu hints, Video status, frame/video factory and translation-video entries | `TELEGRAM_ONLY` with `VIDEO_MENU_DEFERRED` evidence | Video menu/runtime is intentionally deferred; no video plan, job, provider, wallet, payment, or delivery state crosses over. |
| Frozen-baseline dynamic `menu|{*}`, localized `menu|{*}_{locale}`, `menu|admin_confirm_ack_{*}` templates | `TELEGRAM_ONLY` with `UNREVIEWED_DYNAMIC_MENU_VALUE` evidence | These exact observed source templates get no browser meaning. Promoting a specific generated Bot action later requires a new exact source review. |
| Future raw `menu|...`, case variants, malformed values, or templates not in the frozen catalog | Existing fail-closed `NEEDS_FEATURE_DISPOSITION` source-review record | The auditor keeps Bot drift visible instead of silently classifying a new Bot behavior as parity. It still receives no route, browser action, or authority. |

### Mapper behavior

The mapper must use exact, lower-case lookup before a narrow terminal template
match. It must not add a prefix-based Web route fallback. Case variants,
suffixes not matched by the frozen template, malformed values, and future menu
values remain fail-closed under their existing source-review contracts so Bot
drift is not hidden.

Every terminal record contains only the source kind, source literal/template,
classification, status, resolution, bounded disposition codes, and static
source evidence. It contains no target route for `TELEGRAM_ONLY`, no Bot user
or record ID, no command text, payment/PayOS/wallet data, provider key,
job/output state, or delivery claim.

### Documentation and generated evidence

The migration generator will write a concise Menu Terminal Catalog contract and
link it from the generated migration README and known-gaps output. The report
will show that no P0 Menu callback is still eligible for dashboard/catch-all
fallthrough. It will not claim runtime feature parity.

## Out of scope

- Editing `bot.py`, a Bot webhook, bridge, provider, Key4U, PayOS, wallet/Xu,
  job, asset, or delivery engine.
- Web implementation of admin maintenance, package grant, refund, provider
  test, tax/profile/export, translation execution, or Video menu workflows.
- Changing public feature catalog, customer/admin roles, routes, or UI.
- Any LocalVideoStudio, motion-kit, OpenMontage, or Video execution work.

## Verification

- Focused static tests enumerate the exact P0 Menu values and templates, prove
  no `NEEDS_FEATURE_DISPOSITION` remains for `menu|` sources, and verify all
  terminal records retain a false/no-runtime authority boundary.
- Case variants and arbitrary dynamic values never inherit a Web route.
- Generated reports contain no secret literal or Bot callback payload beyond
  the existing static source label conventions.
- Run the static migration audit with the frozen local Bot baseline in
  read-only mode, then run the focused audit tests and whitespace gate.
