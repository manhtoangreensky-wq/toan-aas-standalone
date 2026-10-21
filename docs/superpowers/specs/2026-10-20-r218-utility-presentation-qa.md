# UT/AP/AC-R218 — utility and account presentation QA

## CONTRACT

Close only the UI/UX/locale/responsive presentation layer for translation,
free tools, documents, media workspace, AutoPost, Support, Account, Workboard,
Projects and Memory Center. Runtime APIs, uploads, OAuth, wallet/approval,
publish, provider and live data remain guarded/open.

During QA, six Account avatar presets were found to load from a remote
DiceBear origin on every shell render. They are now inline SVG data URIs with
the same `select-avatar-preset` action contract; no schema/auth/upload change.

## Acceptance

- 10 real Web routes render vertical, readable, localized VI/EN/ZH shells at
  390/1440 and light/dark without overflow or page/console/external/write
  errors.
- Free tools, documents, AutoPost, support, notes, workboard and account
  states remain guarded/read-only where capability is absent.
- Avatar presets have no external origin and preserve the existing selection
  action.

Verify: focused 62 utility/account tests plus avatar-local test, and Edge QA
120 cases. Provider calls/wallet mutations zero; LIVE not claimed.
