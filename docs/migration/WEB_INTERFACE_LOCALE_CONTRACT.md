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

The signed Web profile accepts only these exact values. Browser display aliases
such as `zh-CN` normalize to `zh` inside the presentation bundle; they are not
additional persisted profile values. Any unreviewed display-locale request
falls back to English in the bundle. This is intentional: the Bot may accept
other language codes for its own flows, but this does not claim a fully
reviewed Web interface translation for those languages.

## Data and security boundary

- The preference is read from the signed Web account profile and is updated by
  the existing CSRF-protected profile route.
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
```

The runtime contract loads the bundle in an isolated Node context and verifies
the exact `vi`/`en`/`zh` catalog, equal key coverage, Chinese display aliases,
English fallback, document metadata, script ordering, PWA shell scope and the
workflow-language separation.
