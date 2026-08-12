# Customer Dashboard Decision Motion — Design

## Approved direction

Extend the existing Aura teal/cyan customer workspace with restrained motion at
the point a signed customer decides what to do next. The dashboard remains a
tool, not a landing page: account, wallet, job, asset, provider and readiness
data must never be hidden, delayed, inferred or restyled as an available
action.

## Presentation boundary

The existing browser-only `mountWorkspace()` helper will enhance only completed
decision landmarks that the dashboard has already rendered:

- first-session guide;
- Web-owned work lane;
- account lane;
- studio launchpad; and
- the low-priority assurance disclosure.

The dashboard summary and canonical read lane remain outside the observer
target set so their state is readable immediately. The helper will not inspect
or branch on dashboard state, identity, role, capability, wallet, jobs, assets,
tickets, providers, or any request result.

The server shell marks only the exact `/dashboard` route with presentation
metadata so its document transition can remain stationary. Portal also skips
the generic `<main>` entrance on this route. This marker is a fixed route
projection, not a browser authority input, and does not alter authorization,
session, data, action or feature-readiness decisions.

## Motion grammar

On capable browsers, a decision section fades and rises by the shared 10px
distance as it enters the readable viewport. Up to six already-rendered links
or cards inside that section stagger at 34ms. Keyboard focus reveals a section
at once; browsers without `IntersectionObserver` leave all content visible.
Fine pointers get a 1px lift on navigational cards; coarse pointers get a
`.985` press response. Only `opacity` and `transform` animate with the shared
140/220ms token family.

`prefers-reduced-motion` remains a hard presentation boundary: there is no
observer enhancement at initial mount, and an OS preference change removes
observer/listener/classes/inline stagger index immediately. The content is
never dependent on JavaScript to be visible or usable.

## Out of scope

No route, form, data fetch, signed session, bridge, Core Bot, provider, wallet,
PayOS, pricing, CSRF, PWA worker/cache, database, ENV, credential or deployment
change. This is not a claim of engine or workflow parity.

## Acceptance

1. Only the five dashboard decision landmarks above receive observer reveal.
2. Summary and canonical status are excluded from the pending target list.
3. Focus, observer fallback, remount cleanup and mid-session reduced-motion
   change are verified against the real motion asset using Node.
4. CSS uses the shared token family, opacity/transform, pointer feedback and a
   full reduced-motion reset in both Aura themes.
