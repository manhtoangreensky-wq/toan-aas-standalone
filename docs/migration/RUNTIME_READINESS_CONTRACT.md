# Runtime Readiness Contract

## Core Bridge configuration

The Web application can run without the Telegram canonical Core Bridge. In
that default mode, a missing or invalid bridge configuration does not block
startup. Any Web route that needs the bridge receives the existing guarded
public envelope instead of fabricating a result.

`CORE_BRIDGE_BASE_URL` is valid only when it is a root `https` origin with a
host. It must not contain whitespace, user credentials, a non-root path, query
string, or fragment. `CORE_BRIDGE_TOKEN` and `CORE_BRIDGE_HMAC_SECRET` must
both be non-empty. Invalid or missing values never appear in browser responses
or in the release-gate startup error.

Bridge request setup and `httpx` URL/client failures return the guarded public
envelope (`CORE_BRIDGE_INVALID_CONFIGURATION` for an unsafe configured URL, or
`CORE_BRIDGE_UNAVAILABLE` for a client/request failure). The implementation
does not log the failing URL, request, exception text, token, or HMAC secret.

## Optional release gate

Set `WEBAPP_REQUIRE_CORE_BRIDGE` to one of `1`, `true`, `yes`, or `on` only for
a release that requires the canonical bridge before it can be considered ready.
When this explicit opt-in is set and the bridge configuration is missing or
invalid, the ASGI lifespan stops before database/runtime readiness work and the
process does not serve `/health`. The startup error is a fixed configuration
message and contains no URL or secret.

Any other value, including an unset variable, leaves the gate disabled. The
gate validates local configuration only; it does not make a network call and
does not attest that the remote Bot is currently reachable.

## API fallback boundary

The final portal GET fallback remains available for public and portal paths.
It explicitly returns the application's JSON 404 error contract for unknown
paths starting with `/api/` or `/internal/`, so those callers cannot receive a
login redirect or an HTML portal shell.
