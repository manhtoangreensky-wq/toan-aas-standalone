# Admin Operator menu navigation catalog

The Bot `/operator_menu` flow is a one-admin Telegram command directory. Its
callback handler first checks `ADMIN_ID` and then returns a snippet such as a
command or internal endpoint example. It does not execute that snippet from
the category callback itself.

This catalog converts only reviewed, top-level **non-production** category
buttons into fresh Web Admin ERP navigation. The static migration auditor keeps
the Telegram identifiers private; no `opmenu|...` value is emitted to a
browser, accepted by an API or used as an execution parameter.

Every mapped destination still requires a signed server session and the
current Admin ERP authorization manifest. Navigation is not evidence of an
Operator API token, provider call, worker command, PayOS lookup, wallet
mutation, publication action, background execution or successful delivery.
The Web never reproduces Telegram's in-message back/edit behavior: every
reviewed entry starts a fresh, independently authorized Admin ERP route.

| Bot category | Fresh Admin ERP destination | Scope retained |
| --- | --- | --- |
| `opmenu|root` | `/admin` | fresh Admin ERP root; no Telegram message edit/back, callback, pending state or command replay |
| `opmenu|cat_control` | `/admin` | role-checked ERP overview; no mission/run command replay |
| `opmenu|cat_trend` | `/admin/trends` | guarded trend/reference directory; no live trend search |
| `opmenu|cat_affiliate` | `/admin/growth` | guarded growth/affiliate directory; no import, postback or scale run |
| `opmenu|cat_schedule` | `/admin/calendar` | guarded calendar directory; no channel token or scheduling execution |
| `opmenu|cat_publish` | `/admin/publishing` | guarded publishing directory; no channel API or publish action |
| `opmenu|cat_money` | `/admin/finance` | finance directory; no PayOS, wallet or payout write |
| `opmenu|cat_api` | `/admin/runtime` | redacted runtime read model; no token, n8n import or external executor |
| `opmenu|cat_internal` | `/admin/audit` | redacted audit exploration; no raw identity, secret or tool event write |
| `opmenu|dashboard` | `/admin` | role-checked Admin ERP overview |

## Explicitly deferred

- `opmenu|cat_production` stays `NEEDS_FEATURE_DISPOSITION` as
  `VIDEO_ADMIN_MENU_DEFERRED`. It contains Bot video creation, film, worker,
  output, review and render-related snippets. The user asked that the Video
  menu be completed last, so it cannot inherit `/admin/jobs` or another
  convenient-looking route.
- Every individual `opmenu|...` command remains source-reviewed/guarded. The
  category mapping never turns a text snippet into a browser control.
- Web does not alter Bot, provider configuration, PayOS, wallet/Xu ledger,
  webhook, Railway environment or deployment settings in this scope.
