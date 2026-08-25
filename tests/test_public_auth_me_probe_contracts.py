"""Runtime contracts for the public Auth bootstrap request boundary."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "static" / "portal" / "integration.js"


def _bootstrap_matrix() -> dict[str, dict]:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for the Portal runtime contract")

    script = r'''
const fs = require("fs");
const vm = require("vm");
let source = fs.readFileSync(process.argv[1], "utf8");
const closing = "}());";
const position = source.lastIndexOf(closing);
if (position < 0) throw new Error("Portal integration closure was not found");
source = source.slice(0, position)
  + "\nglobalThis.__authMeHarness = { hydrate, state: () => base() };\n"
  + source.slice(position);

const noop = () => {};
const document = {
  readyState: "loading", visibilityState: "visible",
  addEventListener: noop, removeEventListener: noop,
  querySelector: () => null, querySelectorAll: () => [], getElementById: () => null,
  createElement: () => ({ style: {}, dataset: {}, setAttribute: noop, removeAttribute: noop, appendChild: noop, remove: noop }),
  body: { appendChild: noop }, documentElement: { dataset: {} }
};
const window = {
  addEventListener: noop, removeEventListener: noop, dispatchEvent: noop,
  clearTimeout: noop, clearInterval: noop, setTimeout: () => 0, setInterval: () => 0,
  location: { origin: "https://app.toanaas.vn", pathname: "/", search: "" },
  history: { pushState: noop, replaceState: noop },
  crypto: { getRandomValues: (bytes) => bytes.fill(1) },
  document, navigator: {}, caches: null, isSecureContext: true,
  TOANAASPortal: { mount: noop }
};
class Element {}
class Headers { constructor(initial) { this.values = new Map(Object.entries(initial || {})); } set(key, value) { this.values.set(String(key), String(value)); } }
const context = {
  window, document, console, URL, URLSearchParams, Headers,
  crypto: window.crypto, HTMLElement: Element, HTMLInputElement: Element,
  HTMLSelectElement: Element, HTMLButtonElement: Element, HTMLFormElement: Element,
  Event: class Event {}, CustomEvent: class CustomEvent {}, FormData: class FormData {},
  setTimeout: window.setTimeout, clearTimeout: window.clearTimeout,
  setInterval: window.setInterval, clearInterval: window.clearInterval,
  TextEncoder, TextDecoder
};
vm.createContext(context);

let calls = [];
function response(payload) { return { ok: true, status: 200, json: async () => payload }; }
context.fetch = async (url) => {
  const path = String(url).replace(/^.*\/api\/v1/, "");
  calls.push(path);
  if (path === "/catalog") return response({ ok: true, data: { features: [], menu_capabilities: [] } });
  if (path === "/core/status") return response({ ok: true, data: { flags: {} } });
  if (path === "/auth/providers") return response({ ok: true, data: { providers: {} } });
  if (path === "/auth/telegram/connection/status") return response({ ok: true, data: {} });
  if (path === "/auth/me") return response({ ok: true, data: {
    account: { id: "account-1", email: "demo@example.com", display_name: "Demo", role: "standard", login_methods: {} },
    csrf_token: "csrf"
  } });
  return response({ ok: true, status: "read_only", data: {} });
};
vm.runInContext(source, context, { filename: process.argv[1] });

async function run(route) {
  calls = [];
  window.location.pathname = route;
  window.__TOAN_AAS_PORTAL__ = { path: route, pageStates: {} };
  await context.__authMeHarness.hydrate();
  const state = context.__authMeHarness.state();
  return { calls, authenticated: Boolean(state.session && state.session.authenticated), email: state.profile && state.profile.email || "" };
}
(async () => {
  const result = {};
  for (const route of ["/login", "/register", "/dashboard"]) result[route] = await run(route);
  process.stdout.write(JSON.stringify(result));
})().catch((error) => { console.error(error); process.exit(1); });
'''
    result = subprocess.run(
        [node, "-e", script, str(INTEGRATION)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=45,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_public_auth_routes_skip_only_the_protected_me_probe() -> None:
    result = _bootstrap_matrix()
    expected_public = {"/catalog", "/core/status", "/auth/providers", "/auth/telegram/connection/status"}
    for route in ("/login", "/register"):
        assert "/auth/me" not in result[route]["calls"]
        assert expected_public.issubset(result[route]["calls"])
        assert result[route]["authenticated"] is False


def test_signed_bootstrap_still_hydrates_the_current_account() -> None:
    result = _bootstrap_matrix()["/dashboard"]
    assert "/auth/me" in result["calls"]
    assert result["authenticated"] is True
    assert result["email"] == "demo@example.com"
