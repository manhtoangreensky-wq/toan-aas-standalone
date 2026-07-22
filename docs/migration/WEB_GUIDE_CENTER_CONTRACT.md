# Web Guide Center contract

## Purpose

Guide Center is a signed, read-only Web-native navigation catalog at
/guides. It helps a customer choose a safe next workspace step without
remembering Bot commands.

The frozen Telegram Bot is research evidence only. The Web page does not
replay the Bot main-guide menu, child callback, Telegram identity, message,
conversation, pending input, provider status, job, Xu, wallet, PayOS,
asset, publishing or delivery state.

## Signed route and response

The customer portal loads GET /api/v1/guides/catalog only after the normal
signed Web session is established. The endpoint derives locale exclusively
from the signed account profile and accepts only vi, en or zh.

The response is a closed snapshot with five groups and ten reviewed topics.
Its response headers are Cache-Control: private, no-store, Pragma: no-cache
and Vary: Cookie. A query string or Accept-Language header cannot override
the account locale.

The browser validates every response before rendering it:

- exactly the reviewed group and topic identifiers are accepted;
- each card route must be in the closed customer route allowlist;
- card output is an ordinary navigation anchor, never an action button;
- malformed, stale or cross-session responses fail closed with no fallback to
  a Bot, generic help page, bridge, provider or cached catalog.

## Reviewed navigation topics

The catalog links only to Web customer destinations:

- onboarding and feature discovery;
- Content Studio and Prompt Library;
- Image Studio and Media Workspace;
- Memory Center notes and reminders;
- account security and Support Desk.

Every destination independently checks its own session, role, ownership and
feature readiness. The Guide Center does not imply that a tool is enabled or
that an operation will run.

## Explicit non-execution boundary

The endpoint declares all of the following as false: Bot call, bridge call,
provider call, job creation, wallet mutation, payment start, asset save,
content publish and media delivery. The Guide Center stores no request,
search term or customer guide state.

The two frozen Bot guide video branches remain deferred until the dedicated
Video menu phase. They are not redirected to a generic video route.

## Private-cache boundary

The service worker treats both /guides and /api/v1/guides as private paths.
They bypass Cache Storage and never become an offline shell fallback after
sign-out or an account switch.

## Verification

Focused tests prove signed-session protection, profile-locale selection,
closed catalog shape, no-store headers, app mounting, route validation,
private PWA routing, localized UI keys and audit dispositions for
menu|main_guide and menu|guide.
