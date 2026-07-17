# Nguồn tư liệu & Dubbing hợp lệ — Web-native contract

## Bot source

The guide ports the public static safety text from:

- `/source_help` / `cmd_source_help()` at `bot.py:104321–104336`;
- `/dubbing_help` / `cmd_dubbing_help()` at `bot.py:104338–104352`.

Those commands contain no provider call, provider status, database mutation,
job, Xu/wallet, PayOS, asset, output or publication action. They only state
allowed source categories and prohibited copyright/impersonation behavior.

## Web route

`/guides/source-rights` is a signed-session, read-only route. It contains the
Bot's five allowed-source ideas, the prohibited crawler/reup/watermark/DRM/
Content-ID/real-person-clone behavior, and four dubbing/voice-over principles.
It links to separate Web workspaces but transfers no source or permission data
and grants no capability.

The route is a general guidance layer, not legal advice, a fact check, a
license/consent verification result or evidence that an asset is safe to use.

## Explicit exclusions

It does not receive or persist user input; crawl/reup/fetch any source; call a
provider or Bot/Core Bridge; create job/asset/output; mutate Xu/wallet; start
PayOS; clone voice; render; connect social accounts; publish; deliver a file;
or send a webhook. The PWA treats it as private and never caches it.
