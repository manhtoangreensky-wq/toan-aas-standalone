# Web Interface Locale Contract

## Purpose

The Portal has one **interface-language preference** for reviewed, fixed Web
UI. It is not a translation workflow and does not change customer content.

## Reviewed interface locales

| Stored profile value | Display language | HTML language |
| --- | --- | --- |
| `vi` | Tiếng Việt | `vi` |
| `en` | English | `en` |
| `zh` | 中文（简体界面） | `zh-CN` |

The signed Web profile accepts only these exact values. The presentation bundle
recognizes `zh-CN`, `zh-Hans` and `zh-SG` as **Simplified Chinese display
aliases** for `zh`; they are not persisted profile values. Traditional Chinese
aliases such as `zh-TW` and `zh-Hant` deliberately fall back to English rather
than masquerading as a reviewed Simplified Chinese interface. Any other
unreviewed display-locale request falls back to English in the bundle. This is
intentional: the Bot may accept other language codes for its own flows, but
this does not claim a fully reviewed Web interface translation for those
languages.

## Data and security boundary

- The preference is read from the signed Web account profile and is updated
  only through `POST /api/v1/auth/profile/interface-locale`. The endpoint
  accepts exactly `{ "locale": "vi" | "en" | "zh" }`, requires the signed
  session and CSRF token, rejects extra fields, applies a small raw-body cap
  and rate limit, and records an `auth.interface_locale_update` audit event.
- This narrow endpoint returns only `{ "profile": { "locale": "…" } }`.
  It must not replay a stale browser tab's display name, time zone, role,
  identity or workflow data into the generic profile endpoint. Existing
  profile fields are preserved server-side.
- The first Portal response for a signed session derives its `<html lang>`,
  localized shell title/copy and bootstrap `interfaceLocale` from that signed
  profile value. Public pages start in Vietnamese; query parameters,
  `Accept-Language`, local storage and Bot state never persist or override
  this preference.
- Where a reviewed Portal renderer opts into its catalog keys, it changes fixed
  chrome, account/setup/Starter Kit labels and document language metadata only.
- It never translates, rewrites or sends project briefs, prompts, documents,
  assets, generated results, provider responses or support messages.
- It is distinct from workflow fields such as `language`, `source_language`
  and `target_language`. Those keep their existing canonical option lists and
  validation; changing the interface preference must not change a job or
  provider input.
- The i18n bundle has no storage, network, bridge, Bot, payment or workflow
  action. It cannot create identity, Xu, job, provider or notification state.

## Bot-to-Web navigation boundary

The migration audit treats the Bot's language menu as a separate state machine,
not a browser preference API. Its only reviewed Web counterpart is the fresh,
signed [`/account/interface-language`](/account/interface-language) navigator;
it does **not** carry a Telegram identity, current Bot locale/menu, translation
mode, workflow language, pending state or callback value into the browser.

| Frozen Bot source | Web disposition | Why |
| --- | --- | --- |
| `/lang`, `/language` | `NAVIGATION_ONLY` to `/account/interface-language` | Opens the dedicated Web preference navigator only. The customer must explicitly select and CSRF-save `vi`, `en` or `zh`. |
| `lang|vi`, `lang|en`, `lang|zh` | `NAVIGATION_ONLY` to `/account/interface-language` | The Bot literal is reviewed solely as a fresh Web navigation entry; it never auto-applies a browser locale. |
| `lang|ja`, `lang|ko`, `lang|th`, `lang|ar` | `NAVIGATION_ONLY` to `/account/interface-language` with `UNSUPPORTED_WEB_INTERFACE_LOCALE_DISPLAY_ONLY` | The frozen Bot recognizes these values, but its source currently uses an English UI fallback. The Web shows their support boundary only: no option, persistence, silent fallback or Bot-state transfer. |
| `lang_more`, `back_lang` | `NAVIGATION_ONLY` to `/account/interface-language` | These redraw Bot menu levels only. The Web navigator never recreates the menu, consumes the callback or selects a locale. |
| `lang|{*}` or any later `lang|…` value | `INTERFACE_LOCALE_SOURCE_REVIEW_REQUIRED` | Opaque or new Bot language values fail closed and cannot inherit the navigator, a translation setting or a workflow field. |

The navigator may change presentation only after the dedicated signed Web
locale endpoint accepts an allowed value with CSRF protection and returns the
minimal allowed profile projection. A Bot callback and a raw browser-supplied
language code never bypass that confirmation. Translation-pair commands such
as `/en_vi` and `/vi_en` are intentionally outside this interface-locale
mapping; they remain workflow/translation concerns, not presentation
preferences.

## Load and PWA contract

`portal-i18n.js` loads before `portal.js` and `integration.js` in both the
normal and fallback Portal shell. It is part of the versioned build source and
the explicit public PWA shell cache because it contains only static interface
text. Account pages, workspace setup, Starter Kits and every API route remain
outside that public cache/offline fallback policy.

The bundle checks that every reviewed locale has the same key set at runtime.
It exposes a frozen `window.TOANAASI18n` / `window.TOAN_AAS_I18N` API for
translation, locale metadata and document-language updates. It does not save a
preference itself; the signed account profile remains canonical.

## Verification

Run the focused contracts after changing this surface:

```powershell
node --check static/portal/portal-i18n.js
python -m pytest -q tests/test_portal_i18n_locale_contracts.py tests/test_portal_i18n_bundle_contracts.py
python -m pytest -q tests/test_interface_locale_narrow_update_and_first_paint.py tests/test_interface_locale_navigator_portal_contracts.py
python -m pytest -q tests/test_migration_audit.py -k interface_locale
```

The runtime contract loads the bundle in an isolated Node context and verifies
the exact `vi`/`en`/`zh` catalog, equal key coverage, reviewed Simplified
Chinese aliases, English fallback, document metadata, script ordering, PWA
shell scope and the workflow-language separation. The request contracts verify
the narrow payload, signed first paint, account isolation, CSRF, body cap and
that the generic profile fields cannot be overwritten by a locale-only form.
