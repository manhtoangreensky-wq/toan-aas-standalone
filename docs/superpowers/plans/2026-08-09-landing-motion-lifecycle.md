# Landing motion lifecycle hardening — implementation plan

## Objective

Make the public landing motion sequence safe across real Portal remounts. A
previous route's queued animation frame, timer, focus callback, or observer
delivery must never mutate the new page or resurrect `intro/settled` state after
the landing has unmounted.

## Scope

- `static/portal/portal-motion.js` and its focused lifecycle contract only.
- No route/API/storage/account/provider/Telegram/Bot/PayOS changes.
- Keep the existing cinematic timings, light/dark theme, mobile layout and
  `prefers-reduced-motion` behavior.

## Implementation order

1. Add a RED Node harness that deliberately delivers stale RAF/timer/observer
   callbacks after cleanup and checks listener/decoration cleanup.
2. Add a mount-generation guard and make every asynchronous landing callback
   validate its generation before mutating the DOM.
3. Make cleanup remove only motion-owned attributes/classes/listeners and keep
   the underlying content and layout untouched.
4. Run focused motion tests, JS syntax and diff checks; inspect the local
   `/welcome` behavior once; commit, push and merge as a separate PR.

## Acceptance boundaries

- A real remount gets a new `intro → settled` sequence.
- A stale callback cannot set `is-ready`, reveal a section, compact the header,
  or restore a phase attribute after unmount.
- Observer and event listeners are disconnected/removed.
- Reduced-motion mounts immediately settled with no scheduled animation work.
- No infinite animation, fake output, provider call, or live Bot flow is added.
