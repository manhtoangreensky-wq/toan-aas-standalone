# Video UI checkpoint release — 2026-10-07

Owner instruction: finish the active Video UI slice, merge and preserve its
checkpoint, then prioritize Voice → Music → SubDub → remaining features;
return to the unfinished Video screens afterwards.

Base: `9f2ba35a85608495cb34d918dfc0af62f4dc2414` (fresh standalone main).

## Scope

- `/tools/video`: compact localized tool directory; ten unique existing
  destinations; vertical cards; actual navigation count, no speculative KPI.
- `/video/create` and `/video/multiscene`: existing form inputs grouped as
  content → scene count → aspect ratio, followed by optional settings. Native
  disclosures preserve keyboard access to guidance and all remaining fields.
- Remove the fabricated RTX4090/sample-video workbench from these two routes;
  retain genuine form submission, server quote/confirm gates and real output.
- Correct active-input/text/CTA contrast using semantic blue/teal tokens.
- Restore the customer mobile drawer's fixed placement and translateX state;
  restrict the compositor hint to the ordinary desktop sidebar.
- Preserve current main's API/engine code, all field names/values/limits and
  submit/estimate/confirmation event attributes. No provider or wallet action.

## Acceptance checklist

- [x] VI/EN/ZH × light/dark × desktop/mobile, three routes = 36 cases.
- [x] Ten unique hub links; first tool visible without extra scrolling.
- [x] Task textarea visible initially; guide and optional settings accessible
  by Enter, fields remain present, menus open and close with Escape.
- [x] No horizontal overflow or closed drawer covering content.
- [x] Measured small text >=4.5:1 and active input borders >=3:1.
- [ ] JS/Python syntax, source tests and the official bounded Web CI gate.
- [ ] Commit/push, one PR, CI then squash merge. Record deployment separately.

## Test compatibility

Existing CSS contracts capture sections through EOF. The new route-specific
styles are inserted before the protected final auth block, preserving its
position and assertions. No tests are disabled or weakened; the unchanged
foundation/auth modules pass 90 tests.

The full repository pytest collection requires the separate Bot module for one
cross-repository integration file; that module is absent from this standalone
checkout. Use the official standalone CI selection. Do not alter the Bot or
delete/skip its integration test to disguise that environment constraint.

## Deferred work

Self-shot, trend, storyboard, long-form, creative motion-guide, other Video
editing pages, complete product workflows and final motion remain open. This
checkpoint is not a claim that the entire Video family or whole app is complete.
