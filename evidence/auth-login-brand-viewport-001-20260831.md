# AUTH-LOGIN-BRAND-VIEWPORT-001 — local rendered evidence

## Outcome

The approved bounded hotfix keeps the official TOAN AAS mark fully visible and keeps the login card inside the initial viewport without changing authentication, form fields, copy, routing or server behavior. This report proves the local candidate only; it does not claim commit, push, merge, deploy or production LIVE behavior.

## Source and measured root cause

- Repository: `manhtoangreensky-wq/toan-aas-standalone`.
- Exact production base: `978554130a1b329dd367ee5cf7c5918606770ccc`.
- Before fix at `1056×763`: Auth header `480px`; expected brand mark `36px`; actual mark `10.6375px`; image `56px`; mark overflow `hidden`.
- The global image rule also applied `translate(-8px, -4px)`, so a fixed container alone still clipped the image by its border.
- At the low-height `844×610` reproduction, the old vertical rhythm could push the card beyond the initial viewport at high zoom/DPI.

## Bounded implementation

- Changed presentation only in `static/portal/portal-theme.css`.
- Auth main capacity is capped at `660px`; the desktop/tablet header uses `min(calc(100vw - 32px), 620px)`.
- Brand and mark cannot shrink; the mark stays `36×36px`.
- The image uses the mark content box at `100%×100%`, `object-fit: contain` and `transform: none`.
- Auth switch links and all card buttons retain a minimum `44px` target.
- A `max-height:680px / min-width:601px` rule reduces whitespace and card padding while retaining `44px` controls.
- The existing two-row mobile header remains active at `600px` and below.

## TDD and regression gates

- Initial RED: marker count `0`; expected failure because the hotfix block did not exist.
- First GREEN: `1 passed`.
- Rendered feedback strengthened the contract for viewport-relative header width, image transform reset and `44px` controls; each strengthened contract was observed RED before its minimal CSS change.
- Raw Auth comparator after CI coverage: `23 passed / 3 failed`.
- Clean-base comparator before the hotfix: `21 passed / 3 failed`.
- Exact three failure IDs are unchanged and all belong to stale `test_login_app_ux_contracts.py` copy/Admin-breakpoint assertions:
  1. `test_access_screen_uses_one_compact_app_entry_without_repeating_the_brand`
  2. `test_access_screen_uses_a_balanced_desktop_rail_and_single_column_mobile_fallback`
  3. `test_public_access_uses_reviewed_locale_links_and_translated_field_copy`
- Applicable focused gate: `23 passed / 3 deselected`; `NEW_FAILURES=0`.
- The PR quality workflow executes `tests/test_auth_login_brand_viewport_001_contracts.py`; the workflow-coverage assertion was RED before that target was added and GREEN afterward.

## Rendered matrix

- Six cases: `1056×763`, `844×610`, `390×667` × light/dark.
- Desktop/tablet header width: `620px`; mobile header width: `358.4px`.
- Brand mark: `36×36px` in all six cases; the image is fully inside the mark in `6/6`.
- Card bottom/gap: `626.7/136.3px`, `567.9/42.1px`, `569/98px`.
- Minimum input/button/switch target: `44px`.
- Horizontal overflow: `0/6`; relevant console error/warning: `0/6`.
- The `844×610` page retains `30px` vertical scroll reserve, but the full card itself ends `42.1px` above the viewport bottom.

The canonical machine-readable matrix is `evidence/auth-login-brand-viewport-001-matrix.json`. PNGs remain outside Git under `review/auth-login-brand-viewport-001/`; their sizes and SHA-256 values are recorded in the matrix.

## Safety ledger

`PROVIDER_CALLS=0` · `WALLET_MUTATIONS=0` · `PRODUCTION_DATA_MUTATIONS=0` · `ENV_MUTATIONS=0` · `EXTERNAL_FORM_SUBMISSIONS=0` · `DEPLOY=NO` · `LIVE_PASS=NOT_TESTED`.
