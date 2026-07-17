# PWA rollout and shell versioning contract

## Purpose

The installable TOAN AAS shell must not combine a new server-rendered page
with a stale public JavaScript/CSS cache from a prior deployment. This is a
public-shell availability contract only; it does not make account data,
wallet/payment data, admin pages, APIs, downloads or workspace records
available offline.

## Build ID source and validation

`copyfast_pages.py` renders one public `buildId` in the inert portal bootstrap
and uses the same value in public shell asset URLs. It selects the first valid,
opaque identifier in this order:

1. `APP_BUILD_ID`;
2. `RAILWAY_GIT_COMMIT_SHA`;
3. `RAILWAY_DEPLOYMENT_ID`;
4. a deterministic SHA-256-derived local shell-source fallback.

An identifier is accepted only when it is 1–96 characters of
`A-Za-z0-9._-`, starts with an alphanumeric character, and contains no URL,
HTML, whitespace or credential material. Invalid environment values are
ignored. The browser validates the value again before it reaches a worker URL,
and the worker validates the query parameter itself before deriving a cache
name.

## Controlled worker lifecycle

When PWA is enabled, the browser registers:

```text
/service-worker.js?build=<encoded-public-build-id>
```

The worker owns exactly `toan-aas-portal-shell-<validated-build-id>` and
cleans only obsolete cache names with that prefix. It seeds its cache with a
fixed public allow-list using build-scoped reload requests, and offline
lookups are always scoped to that exact cache generation.

The worker intentionally does **not** call `skipWaiting()`, `clients.claim()`,
or reload an existing tab. A customer editing a form keeps the current
controller. While online, a normal browser reload uses the network-first shell
URLs from the newly rendered page, so it receives the deployed public assets
without a forced reload. The new worker becomes the offline controller after
the browser naturally retires the old controlled clients (for example, after
existing app tabs are closed/reopened); that transition is never forced by
application JavaScript.

## Cache boundary

Only the fixed public CSS/JS/manifest/icon/offline document allow-list may be
stored. There is no runtime `cache.put`, no API cache, and no cache fallback
for dashboard, account, wallet, payments, admin, jobs, assets, support, inbox,
automation or private delivery URLs. A route remains signed-session and
ownership checked after any PWA update.
