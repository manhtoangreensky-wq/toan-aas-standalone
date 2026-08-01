# Ticket Terminal Callback Catalog Design

## Intent

Close only frozen Bot `ticket|*` literals that are proven to redraw a
Telegram-only category/menu/list/search state.  The independent Web Support
Desk and Admin Support workspace remain Web-owned products; they never receive
the Bot callback, Telegram identity, category, ticket ID, pending state,
attachment, reply preview or delivery state.

The finite raw lower-case source literals are:

- customer category selectors: `ticket|cat|payment_topup`,
  `ticket|cat|image_error`, `ticket|cat|video_error`,
  `ticket|cat|document_pdf`, `ticket|cat|package_combo`,
  `ticket|cat|refund`, `ticket|cat|feature_request`, `ticket|cat|other`, and
  `ticket|cat|lead_consulting`;
- Bot-admin menu/list/search controls: `ticket|admin`,
  `ticket|al|new|0`, `ticket|al|high|0`, `ticket|al|refund|0`,
  `ticket|asearch|all`, `ticket|asearch|user`, `ticket|stats`, and
  `ticket|templates`.

## Decision

Use a finite raw, case-sensitive terminal catalog in the static audit.  Each
listed source maps only to `TELEGRAM_ONLY`, with its real customer/admin
classification and explicit Telegram pending/record or Bot-admin boundaries.

This is not a Web ticket feature or a Bot bridge.  It creates no Web route,
Web case, form prefill, API request, browser state, Bot ticket read/write,
Telegram message, attachment delivery, refund/payment/wallet/ledger action,
provider/job operation or runtime outcome.

## Exactness and drift handling

Only byte-for-byte lower-case catalog sources become terminal.  Case,
leading/trailing whitespace, suffixes, missing tokens, unknown categories,
dynamic list offsets, ticket IDs, attachment IDs, reply/preview/send,
status/assignment/lead/file operations and all future `ticket|*` values remain
`SUPPORT_TICKET_SOURCE_REVIEW_REQUIRED`.  The mapper may trim only to
recognize the family for source-review; it never trims before a terminal
lookup.

Existing reviewed fresh Web navigation entries (`ticket|start` and
`ticket|mine`) stay navigation-only.  This work does not change them.

## Evidence and verification

The audit regenerates only from frozen Bot baseline
`b29d0d474974075f4cba963d2c510f49d2d1b3e4`; it never imports or starts Bot
code.  Tests cover the catalog, terminal envelope, customer/admin separation,
case/whitespace/suffix/dynamic failure boundary and regenerated current
evidence.  Existing Web Support Desk tests are regression-only because runtime
code is not changed.

## Non-goals

Do not edit `bot.py`, change Web Support Desk or Admin Support API/UI/storage,
make a Bot bridge, enable flags, call Telegram/PayOS/provider/job systems, or
touch Video/LocalVideoStudio/motion-kit/OpenMontage files.
