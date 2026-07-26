# TOAN AAS Teal–Cyan UI System Design

## Purpose

Create one professional, easy-to-use visual language for the TOAN AAS public
introduction and signed workspace without making the workspace look like a
marketing landing page.  The application remains FastAPI plus the existing
server-rendered Portal shell; this work is presentation-only.

## Accepted visual direction

The reference concepts are stored outside the repository:

- Landing: `C:\Users\toann\.codex\generated_images\019f4b14-cdaa-7d90-8869-cf654fcab17a\exec-b7eb9379-ddf6-4614-90c8-34ad2e14248b.png`
- Desktop workspace: `C:\Users\toann\.codex\generated_images\019f4b14-cdaa-7d90-8869-cf654fcab17a\exec-167f60fc-c499-4a3f-a730-f88c7c120dae.png`
- Login and mobile access: `C:\Users\toann\.codex\generated_images\019f4b14-cdaa-7d90-8869-cf654fcab17a\exec-4bfdc67a-4614-45a0-afc9-53d493765a13.png`
- Mobile workspace: `C:\Users\toann\.codex\generated_images\019f4b14-cdaa-7d90-8869-cf654fcab17a\exec-4fa1732a-f7bb-4ea8-9404-24cff140cdf2.png`

The public companion is light, open and conversion-oriented.  The signed app
uses a deep ink-blue operational canvas with teal as the primary action color
and sky cyan for navigation and informative state.  Both surfaces share the
same typography, icon weight, spacing rhythm and clear Vietnamese language.

| Semantic role | Value | Use |
| --- | --- | --- |
| Ink background | `#07141d` | Workspace canvas and app shell |
| Ink surface | `#0d2330` | Operational panels and controls |
| Ink elevated | `#112b39` | Active or elevated surface |
| Light canvas | `#f6fcfc` | Public introduction and access canvas |
| Teal action | `#0e9f9a` | Primary customer action |
| Cyan context | `#0284c7` | Current navigation and information |
| Primary text | `#edf8fa` / `#06212b` | Dark / light surface text |
| Muted text | `#9bb9c3` / `#52727c` | Supporting copy |
| Border | `#234555` / `#c7e3e6` | Surface separation |

## Information architecture

1. `app.toanaas.vn` keeps the signed workspace as the product root.  Desktop
   uses the existing server-granted sidebar and header; mobile keeps the
   existing labelled five-item dock.
2. `/login` and `/register` keep email/password as the primary flow.  OAuth
   and Telegram stay configuration- or server-state-gated secondary paths;
   a raw Telegram ID is never accepted.
3. `/welcome` is the public companion in this repository.  It does not gain
   provider calls, a payment surface, browser identity storage or fabricated
   job results.  The production `toanaas.vn` site is outside this repository
   and needs its own source/hosting handoff.
4. All customer-visible additions use the existing reviewed `vi`, `en` and
   `zh` locale catalogue.  This first foundation slice changes no visible
   runtime string, so it cannot create an untranslated key.

## Non-negotiable invariants

- Keep signed sessions, CSRF, ownership, Core Bridge, wallet/PayOS and
  provider authorities unchanged.
- Keep inert server bootstrap, skip link, mobile-nav, command palette and
  script order (`portal-i18n.js`, `portal.js`, `integration.js`) unchanged.
- Preserve all `data-portal-*` attributes and existing event delegation.
- Preserve 44px mobile action targets, visible keyboard focus and reduced
  motion behaviour.
- Use semantic CSS tokens instead of page-level hex colour patches.

## Delivery slices

1. **Foundation (this branch):** load one final, scoped theme stylesheet;
   standardize colours, shell, header, primary controls, access canvas,
   public companion, focus, reduced motion and responsive rhythm.
2. **Customer workspace:** align dashboard, work queues, asset lists and
   feature workspaces with the new information hierarchy while preserving
   their real loading/guarded states.
3. **Access/account:** refine the rendered auth, onboarding and account
   information architecture and add tri-lingual copy where the renderer
   changes.
4. **Admin ERP:** apply the dense operational table/list treatment to the
   signed admin system separately so it cannot leak into customer routes.
