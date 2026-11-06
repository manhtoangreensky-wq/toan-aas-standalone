# Tester session CHANNEL-STRATEGY-LOCALE-20261106

STATUS=LOCAL_ACCEPTED_PENDING_EXACT_HEAD_CI_DEPLOY_AND_SIGNED_LIVE
PRODUCT=TOAN AAS standalone WebApp
REPO=manhtoangreensky-wq/toan-aas-standalone
BASE_SHA=8c85f84966ab3e0f53bf97a2999e221b23901bcf
SOURCE_STATE=Reviewed candidate; exact committed SHA is recorded by the release PR and provenance receipt.
CASE_SOURCE=KIEM-THU/DANH-SACH-CASE.md
CASE_IDS=CS-LOCALE-01,CS-FIRSTPAINT-02,CS-FONT-03,CS-NAV-04

## Scope and evidence

Only Channel Strategy fixed UI copy, first-paint title, mobile form font and one
mobile-group prefix. Customer content, saved option values/order, handlers and
server authority are unchanged. The local revision helper keeps the intended
integer1..1000000 range without calling an unavailable cross-bundle function.

Coordinator fresh results: targeted Node29/29, full indexed Node1406/1406,
native/channel/firstpaint/CSS106/106, actual template/browser54/54 configurations.
The browser matrix is library/detail/archive ×VI/EN/ZH ×light/dark ×360/768/1440.
It verifies copy, attributes,16px small-phone inputs, active Publishing destination,
literal field edits, option identifiers, focus, menu/Escape, palette and theme.
Page/console/overflow/external/API/write/unknown counts are all0.
The local browser is synthetic presentation QA, not an existing signed session.

Independent reviewer reran29Node,11Pythonfirstpaint/contracts and26CSS tests,
all0fail; two scoped reviews found Critical0/Important0/Minor0. Removing the
exact6line new CSS block leaves the pre-existing stylesheet identical toBASE.
The old inline-navigation literal test was stale before app edits; it now checks
the actual map+delegation and is backed by new parent/detail/other-group/admin
behavioral tests. No skip, xfail or weakened authority guard.

## Reviewed source LF checksums

| File | SHA256 |
|---|---|
| `copyfast_pages.py` | `00eb553ad2ee358080598711b8877452983fd58a9e2b2e6a5d260e740e11085c` |
| `static/portal/portal.js` | `5207469bcab4c30791568aa86e88d660014f44ebfc79e53a9051c2422f002d0b` |
| `static/portal/portal-i18n.js` | `4fd991be6899a2c3f60318c63b1d31774f9c0ced31fcabfe99012ac5db47629c` |
| `static/portal/portal-theme.css` | `27967935247c5ee4c5b11215a28c2279872640883dd5044ee59a7fc971fbcb4a` |

## Local browser evidence checksums

Raw QA evidence remains local; it contains only synthetic data and is not a
claim about production accounts or external integrations.

| Matrix | Result | SHA256 |
|---|---|---|
| channel-library-release | 18/18 | `57acef718d39a3f7df960fdaefb49372bab7cb825c88076ef82868094f2a56ab` |
| channel-detail-release | 18/18 | `56234c6cd1239d5679919f2170d54dd71baaa6e05a80c44dc8ea858641a21243` |
| channel-archived-release | 18/18 | `dfb5b650f97f5ab318e282f803894d53c48b0dab8ff531462bbbf758b7cdc36c` |

## Open delivery and product boundaries

Exact-head CI, PR merge, deployment revision, service health, served assets/build
stamp and signed production UI are distinct gates. Do not infer LIVE fromHTTP200
or these local tests. No social OAuth/connection, external posting, provider job,
media output, wallet/payment or production data operation was tested or added.
The next Publish Review and calendar code is not in this accepted release.
Their newly reproduced defects remain open; motion remains last.

Existing Tester labels/templates were reused. Read-only06/11check found22labels
and all12required labels; the legacy48core cases remain48. Issue664 is closed
and is an older Music/SFX scope, not this release tracker; it was not reopened
or amended. GitHub Projects access remains unavailable without new authorization;
no auth/permission refresh or bulk issue creation was performed. This local
session and the scoped release PR are the work area/evidence links for these4cases.

PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
ENV_OR_PERMISSION_CHANGES=0
DEPLOY=NO_AT_LOCAL_ACCEPTANCE
SIGNED_UI_LIVE=NOT_TESTED
