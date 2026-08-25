import json
import shutil
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]

def _node_mount_auth(providers: dict) -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required")

    script = '''
const fs = require("fs");
const portalSource = fs.readFileSync(__PORTAL_PATH__, "utf8");
const i18nSource = fs.readFileSync(__I18N_PATH__, "utf8");
const providers = __PROVIDERS__;
function createClassList() { const values = new Set(); return { add: (...n) => n.forEach(x => values.add(String(x))), remove: (...n) => n.forEach(x => values.delete(String(x))), contains: (n) => values.has(String(n)), toggle: (n, f) => { const e = f === undefined ? !values.has(String(n)) : Boolean(f); if (e) values.add(String(n)); else values.delete(String(n)); return e; } }; }
function createElement() { const a = {}; return { hidden: false, innerHTML: "", textContent: "", dataset: {}, classList: createClassList(), setAttribute: (n, v) => { a[n] = String(v); }, getAttribute: (n) => a[n] || "", removeAttribute: (n) => delete a[n], hasAttribute: (n) => Object.prototype.hasOwnProperty.call(a, n), querySelector: () => null, querySelectorAll: () => [], addEventListener: () => {}, removeEventListener: () => {}, matches: () => false, closest: () => null, focus: () => {} }; }
const window = {
  addEventListener: () => {},
  matchMedia: () => ({ matches: false, addEventListener: () => {} }),
  location: { search: '' },
  __TOAN_AAS_PORTAL__: {}
};
let domReady = null;
const root = createElement();
const sidebar = createElement();
const shell = createElement();
const header = createElement();
const document = {
  body: createElement(),
  createElement: () => createElement(),
  readyState: 'loading',
  addEventListener: (type, handler) => { if (type === "DOMContentLoaded") domReady = handler; },
  documentElement: { lang: 'en', setAttribute: () => {} },
  querySelector: (sel) => {
    if (sel.includes('sidebar')) return sidebar;
    if (sel.includes('header')) return header;
    if (sel.includes('main')) return root;
    if (sel.includes('shell')) return shell;
    return null;
  },
  querySelectorAll: () => [],
  getElementById: (id) => {
    if (id === 'portal-root') return root;
    return null;
  }
};
const context = { console, process, setTimeout, clearTimeout, window, document, URL, URLSearchParams, Intl };
context.globalThis = context;
const vm = require("vm");
vm.createContext(context);
try {
    vm.runInContext(i18nSource + "\\n" + portalSource, context);
    if (typeof domReady === "function") domReady();
    vm.runInContext("window.TOANAASPortal.mount({ path: '/login', interfaceLocale: 'en', oauthProviders: " + JSON.stringify(providers) + " });", context);
    console.log(root.innerHTML);
} catch (e) {
    console.error(e);
    process.exit(1);
}
'''
    script = script.replace('__PORTAL_PATH__', repr(str(ROOT / "static" / "portal" / "portal.js")))
    script = script.replace('__I18N_PATH__', repr(str(ROOT / "static" / "portal" / "portal-i18n.js")))
    script = script.replace('__PROVIDERS__', json.dumps(providers))
    result = subprocess.run([node, "-e", script], capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Node failed:\\nSTDOUT: {result.stdout}\\nSTDERR: {result.stderr}")
    return result.stdout

def test_missing_or_disabled_providers_do_not_render_anchors():
    html = _node_mount_auth({})
    assert "portal-btn-direct-social telegram" in html
    assert "portal-btn-direct-social google" not in html
    assert "portal-btn-direct-social apple" not in html
    assert "portal-social-pair" not in html

    html_disabled = _node_mount_auth({
        "google": {"enabled": False},
        "apple": {"enabled": False}
    })
    assert "portal-btn-direct-social google" not in html_disabled
    assert "portal-btn-direct-social apple" not in html_disabled
    assert "portal-social-pair" not in html_disabled

def test_enabled_providers_render_correctly():
    html_google = _node_mount_auth({
        "google": {"enabled": True},
        "apple": {"enabled": False}
    })
    assert "portal-btn-direct-social google" in html_google
    assert "portal-btn-direct-social apple" not in html_google
    assert "portal-social-pair" in html_google
    assert 'href="/api/v1/auth/oauth/google/start?next=/dashboard"' in html_google

    html_apple = _node_mount_auth({
        "google": {"enabled": False},
        "apple": {"enabled": True}
    })
    assert "portal-btn-direct-social apple" in html_apple
    assert "portal-btn-direct-social google" not in html_apple
    assert "portal-social-pair" in html_apple
    assert 'href="/api/v1/auth/oauth/apple/start?next=/dashboard"' in html_apple

    html_both = _node_mount_auth({
        "google": {"enabled": True},
        "apple": {"enabled": True}
    })
    assert "portal-btn-direct-social google" in html_both
    assert "portal-btn-direct-social apple" in html_both
    assert "portal-social-pair" in html_both

def test_malformed_or_non_literal_true_do_not_render():
    for p in [{"google": {"enabled": "true"}}, {"google": {"enabled": 1}}, {"google": {"enabled": None}}, {"google": {}}, {"google": "true"}, {"apple": {"enabled": "true"}}, {"apple": {"enabled": 1}}, {"apple": {"enabled": None}}, {"apple": {}}, {"apple": "true"}]:
        html = _node_mount_auth(p)
        assert "portal-btn-direct-social google" not in html
        assert "portal-btn-direct-social apple" not in html
        assert "portal-social-pair" not in html
