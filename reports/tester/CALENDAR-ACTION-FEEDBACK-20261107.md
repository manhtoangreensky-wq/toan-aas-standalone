# Tester session CALENDAR-ACTION-FEEDBACK-20261107

STATUS=LOCAL_ACCEPTED_PENDING_EXACT_HEAD_CI_DEPLOY_AND_SIGNED_LIVE
PRODUCT=TOAN AAS standalone WebApp
REPO=manhtoangreensky-wq/toan-aas-standalone
BASE_SHA=f70d653da80642c9a844a05179a46d3277a464ca
CASE_SOURCE=KIEM-THU/DANH-SACH-CASE.md
CASE_IDS=CAL-ACTION-01,CAL-ACTION-02,CAL-ACTION-03

## Measured evidence

- Baseline full-integration runtime: 108 cases,25 passed/83failed; currentness
  12/66 passed and fixed-feedback13/42 passed. Three current positive controls,
  nine newer-first controls and unknown error retention were already valid.
- After worker:108/108 focused Node;1,670/1,670 indexed Node across196files;
  zero failures,skips or cancellations. JavaScript syntax/Python compile passed.
- Native/shell/window contracts9/9. Original three temporary-DB GET envelopes
  passed through actual integration for9/9 locale/action projection controls
  and9/9 localized feedback; auth/CSRF tokens were not passed to the helper.
- Browser36/36 (three actions,three locales,two themes,360/1440) normal click/
  submit -> exactly one expected local GET -> current window/filter/count ->
  visible localized role=status toast.36PNG files validated;0page/console/
  external/write/unknown requests; all browser/server processes closed.
- Independent indexed review C0/I0/M0,108Node rerun;219balanced campaignUi keys,
  eight additions and all8,950existing English values unchanged.
- Tester metadata32passed on Windows with one unchanged POSIX private-file mode
  failure (0666 versus0600). No skip/xfail/chmod or weaker security check; the
  Linux critical CI gate is required before merge.

## Protected comparators and limits

api/toast/merge/setActionBusy,selection/key/windowPath/readfence/hydrate and
PublishReview feedback helper remain byte-identical to BASE. The outer catch
localization is restricted to the exact three Calendar actions; all others retain
their behavior. Unknown messages reaching the helper/catch keep their content.
The existing GET error/projection policy is unchanged, not a new promise to expose
every server error detail. No request abort, retry, storage, API/auth/CSRF/rights,
DTO/schema, Bot/provider/finance or motion change. Calls/mutations for application
providers,wallet and production data remain zero.

Browser uses actual renderer/styles/action listeners with original temporary-DB
GET envelopes, a synthetic signed bootstrap and a QA-served-byte seam suppressing
initial auth hydration. This verifies action feedback,not production session,
login lifecycle or external output. Native tests use a temporary database with
dummy accounts/plans and no Telegram linking. Exact-head CI, deployment/runtime/
public assets and signed production UI are separate delivery gates. Remaining
Campaign/whole-app/PWA/motion work remains open.
