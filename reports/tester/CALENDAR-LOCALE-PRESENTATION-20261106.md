# Tester session CALENDAR-LOCALE-PRESENTATION-20261106

STATUS=LOCAL_ACCEPTED_PENDING_EXACT_HEAD_CI_DEPLOY_AND_SIGNED_LIVE
PRODUCT=TOAN AAS standalone WebApp
REPO=manhtoangreensky-wq/toan-aas-standalone
BASE_SHA=9137c0c037995b59e178edc1055eec825ace6f73
CASE_SOURCE=KIEM-THU/DANH-SACH-CASE.md
CASE_IDS=CAL-LOCALE-01,CAL-STATE-02,CAL-COMPACT-03,CAL-FONT-04,CAL-SAFETY-05

## Measured source and native evidence

- Baseline locale: 24 cases, 6 passed and 18 failed; first paint: 1 passed,
  2 failed. Presentation initially 0/15, with nine later assertions exposing
  preexisting loading/failed/guarded copy omissions before the final patch.
- Final focused Node: 39/39, zero skipped/cancelled/failed.
- Final shell/window/native Python: 8/8, warnings only; actual temporary-DB
  native month/filter/redaction and owner isolation remain valid.
- Full indexed Node: 1,562/1,562 across 194 files, zero skipped/failed/cancelled.
- Independent final staged source review C0/I0/M0; 211 campaignUi keys per locale,
  seven additions and all 8,943 existing English values unchanged.
- Exact-index comparators: filter form and two footer anchors match BASE; removing
  the one five-line mobile-font block restores byte-identical BASE CSS.
- Syntax checks and Python compilation passed for the affected source/tests.
- Tester metadata: 32/33 passed on Windows; the unchanged POSIX private-file
  mode assertion reports 0666 instead of0600. No chmod/skip/xfail or weakened
  security check; Linux critical CI must pass before this release is merged.

## Browser evidence gate

Ready pilot at 360/1440 VI/dark passed 2/2 after mobile font16. Full 90-config
matrix (five states, three locales, two themes, three widths) passed 90/90, with
zero page/console errors, page overflow, API/external/write/unknown requests.
Controls, matching counts, footer links, localized state copy, theme/menu/palette,
keyboard focus and month/status/platform identifier edits passed. Every isolated
browser/server was closed after its state matrix.
The first matrix had 18 QA-selector false failures: a failed-status badge was
mistaken for a numeric matching count. No application change or skipped state
was used to resolve that measurement error; the entire 90-config matrix was
remeasured successfully into separate evidence directories.

Manual PNG review then reopened a separate missing visibility assertion: the
numeric count used a badge class hidden by the customer-UI policy. The candidate
was not pushed or deployed. The final count is an ordinary subtitle paragraph,
not a badge or new box. A strict pilot first failed 2/2; after the worker patch,
the full 90/90 matrix was remeasured with client rects and ancestor CSS visibility,
display and opacity checks. All 36 ready/empty read configurations show the count;
the other 54 show no numeric result. Ninety PNG files and unchanged served assets
across states were validated. Previous DOM-text-only results are not used as this
visibility evidence. Final 39 focused,1,562 full Node and8 native checks passed
again; independent narrow review C0/I0/M0 preserves form/footer/agenda/CSS/catalog.

## Scope, authority and release limits

Calendar title/description, overflow and missing-title fallback are localized;
nonempty customer titles, including ordinary English and brand names, retain the
existing sanitization and escaping. Two tutorial containers are removed; controls,
record links, footer links and real read-only count remain. Loading/failed/guarded
copy is distinct from a completed empty read. Mobile input/select font is16px
only on Calendar at max620px. No generic rendering/action helper or shared
signature changed; Calendar's missing-title fallback is delayed until rendering.

API/DTO/backend/auth/CSRF/capabilities/currentness/date/month/filter/count arithmetic,
200-item cap, enum identifiers, order, Bot/provider/finance and motion are unchanged.
Provider calls, wallet and production-data mutations are zero. Local presentation
uses actual renderer/styles with synthetic bootstrap; native tests use a temporary
database. Neither is signed production UI or provider/publishing/output proof.
Exact-head CI, deployment, VPS/source/public-asset reconciliation and signed UI
remain separate gates. The rest of the whole-app checklist and motion remain open.
