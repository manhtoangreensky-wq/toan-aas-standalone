# Bot companion handoff

The standalone Web App now gives the following Telegram-first Bot workflows
their own signed customer routes:

| Web route | Bot commands offered | Ownership boundary |
| --- | --- | --- |
| `/notes` | Bot reference: `/notes`, `/note`, `/memory` | Web-owned notes, tag/search/priority/archive and version history; never reads or writes Bot `memory_*` state. |
| `/reminders` | Bot reference: `/reminders`, `/remind` | Web-owned one-time/recurring reminder state; no Telegram/email/push delivery claim and no Bot reminder mutation. |
| `/referrals` | `/referral`, `/ref` | Referral identity, links and rewards remain canonical in Bot. |
| `/rewards` | `/gift`, `/promos`, `/birthday` | Gift/promo/birthday eligibility and Xu effects remain Bot state. |
| `/community` | `/community`, `/official_channels` | Bot publishes community/channel information. |
| `/guides` | `/menu`, `/guide`, `/help` | Bot remains the current command/help authority. |
| `/account` | `/language`, `/mode`, `/profile`, `/mydata`, `/data_delete` | Web-owned profile metadata stays separate; data-deletion policy and confirmation remain in Bot. |
| `/tickets` | `/tickets`, `/ticket_status` | Ticket threads, Telegram attachments and detailed status remain Bot state. |
| `/growth/ai` | `/growth_ai days=<1..90> [platform] [campaign_id] [goal]` | Web allows only a fixed, reviewed filter set; Bot reads performance, checks Xu and returns the canonical analysis. |
| `/campaign/report` | `/campaign_report days=<1..90> [platform] [campaign_id] format=<txt\|csv>` | Bot creates the report/file and remains the only charge/refund authority. |
| guarded Content routes | `/film` | Zero-argument command opens Bot's content/script usage chooser; the Portal never appends a brief. |
| guarded Image routes | `/image_tools` | Zero-argument command opens the Bot image menu; it does not send a prompt, image or provider request. |
| guarded Video routes | `/create_media` | Zero-argument command opens the Bot media menu; the customer chooses the next step inside Telegram. |
| guarded Music routes | `/music` | Zero-argument command opens the Bot music/SFX menu; searches and input remain in Telegram. |
| guarded Subtitle/ASR/Dubbing routes | `/translate` | Zero-argument command opens the Bot translation picker; no text, media or target-language value travels from Web. |
| guarded Document routes | `/doc_tools` | Zero-argument command opens the Bot document-tool chooser; files remain inside the Telegram workflow. |

All remaining Bot-companion routes require the normal signed Web session and
linked Telegram identity before they render. They receive only public
`BOT_USERNAME` metadata from the safe Telegram connection-status endpoint,
then offer a user-initiated `https://t.me/<BOT_USERNAME>` handoff and an
allowlisted command copy action. `/notes` and `/reminders` are the explicit
exception: they require a signed Web session but not a Telegram link, and they
call only the owner-scoped Web Memory API documented in
[`MEMORY_CENTER_CONTRACT.md`](MEMORY_CENTER_CONTRACT.md).

The two analytics handoffs use a separate closed schema rather than accepting
arbitrary Bot text: days `1..90`, the Bot's supported manual-publish
platforms, a positive numeric campaign ID, fixed Growth-AI goals, and `txt`
or `csv` for campaign reports. The Portal does not read performance data,
produce a preview, calculate revenue, estimate charge, attach a file, or send
any report input through its own API.

For the remaining companion routes, the Portal does **not** send a Telegram
ID, referral/reward identity, ticket ID/thread, browser session, password, Bot
token, bridge secret, wallet/Xu state, provider input, or payment data to
Telegram. `/notes` and `/reminders` send their own note/reminder data only to
the same-origin, signed Web API; they never send it to Telegram or copy Bot
tables. The `/data_delete` button copies only the allowlisted Bot command; it
does not delete a Web/Bot account. If the public Bot username is missing,
companion links and copy controls remain disabled rather than pointing to an
ambiguous destination.

This is an intentional product boundary: the Web dashboard makes all
discoverable workflows visible, while the Telegram Bot remains the fast,
conversation-first interface for the remaining Bot-owned operations.
Memory Center is a feature-specific Web-native contract rather than a Bot
handoff; its AI classification, billing quota and actual notification sender
remain guarded until separately designed adapters exist.

## Feature-family handoff review (frozen Bot baseline)

The six family commands above are exact strings registered in the frozen Bot
checkout (`bot.py`): `/film` at line 128928, `/image_tools` at 128945,
`/create_media` at 128937, `/music` at 128693, `/translate` at 128719, and
`/doc_tools` at 128678. Handler review confirms that their zero-argument path
opens a usage/help/menu/picker rather than sending Portal data or immediately
calling an engine. The Web copy allowlist contains only these fixed strings.

Voice has no corresponding customer-ready entry command in this baseline:
`/voiceover` responds with an admin/experimental guard for non-admin users.
The Portal therefore keeps Voice on generic `/menu` handoff until a
customer-safe Bot command and bridge contract are both available. Commands
that need a topic, file, transaction, job ID, provider state, or admin role
are intentionally not offered as Web copy controls.
