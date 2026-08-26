import json
import re
import subprocess
from pathlib import Path

import copyfast_pages
from copyfast_pages import render_portal


ROOT = Path(__file__).resolve().parents[1]
FEATURE_ENTRY = ROOT / "static" / "portal" / "portal-features.js"
FULL_WORKSPACE = {
    "/static/portal/portal-i18n.js",
    "/static/portal/portal-motion.js",
    "/static/portal/admin-customer-directory.js",
    "/static/portal/portal.js",
    "/static/portal/integration.js",
}


def _scripts(path: str) -> set[str]:
    html = render_portal(path).body.decode("utf-8")
    return set(re.findall(r'<script[^>]+src="([^"?]+)', html))


def test_features_uses_only_its_route_entry_and_shared_presentation_scripts() -> None:
    html = render_portal("/features").body.decode("utf-8")
    assert 'class="portal-body portal-body--features"' in html
    assert _scripts("/features") == {
        "/static/portal/portal-theme.js",
        "/static/portal/portal-features.js",
    }


def test_features_split_also_applies_to_fallback_template(monkeypatch) -> None:
    monkeypatch.setattr(copyfast_pages, "TEMPLATE", ROOT / "templates" / "missing.html")
    scripts = _scripts("/features")
    assert "/static/portal/portal-features.js" in scripts
    assert not ({
        "/static/portal/integration.js",
        "/static/portal/admin-customer-directory.js",
        "/static/portal/portal-auth.js",
    } & scripts)


def test_dashboard_and_admin_keep_full_workspace_while_auth_stays_split() -> None:
    for route in ("/dashboard", "/admin"):
        assert FULL_WORKSPACE <= _scripts(route)
        assert "/static/portal/portal-features.js" not in _scripts(route)
    for route in ("/login", "/register"):
        assert _scripts(route) == {
            "/static/portal/portal-theme.js", "/static/portal/portal-auth.js",
        }


ENTRY_HARNESS = r"""
(async () => {
  const fs = require("node:fs"), vm = require("node:vm");
  const source = fs.readFileSync(process.argv[2], "utf8");
  const scenario = process.argv[3];
  const calls = [], mounts = [];
  const window = { __TOAN_AAS_PORTAL__: { path: "/features", interfaceLocale: "vi" }, TOANAASPortal: {
    mount(next, options) { mounts.push({ next, options }); }
  } };
  const document = { readyState: "complete", getElementById() { return null; } };
  const response = (payload, ok = true) => ({ ok, json: async () => payload });
  const fetch = async (url) => {
    calls.push(String(url));
    if (scenario === "malformed") return response({ ok: true, data: { features: "bad", account: "bad" } });
    if (String(url).endsWith("/catalog")) return response({ ok: true, data: { features: [
      { key: "safe_tool", title: "<Công cụ>", description: "Mô tả thật", group: "content", route: "/safe-tool", kind: "customer",
        engine: { mode: "web_native", execution_state: "ready" }, readiness: { status: "available" } },
      { key: "empty_copy", title: "Công cụ chưa có mô tả", description: "", group: "other", route: "/empty-copy", kind: "customer",
        engine: { mode: "guarded", execution_state: "guarded" }, readiness: { status: "guarded" } },
      { key: "legal", title: "Legal", route: "/legal", kind: "customer" },
      { key: "privacy", title: "Privacy", route: "/privacy", kind: "customer" },
      { key: "self", title: "Self", route: "/features", kind: "customer" },
      { key: "family", title: "Family", route: "/features/video", kind: "customer" },
      { key: "external", title: "Bad", route: "//evil.example/x", kind: "customer" },
      { key: "query_secret", title: "Bad", route: "/safe?token=secret", kind: "customer" },
      { key: "admin_tool", title: "Admin", route: "/admin", kind: "admin" },
    ], menu_capabilities: [], capability_hub: {}, route_engine: { state: "deferred" } } });
    return response({ ok: true, data: { account: { email: "qa@example.invalid", display_name: "QA", role: "admin",
      profile: { locale: "vi" } }, csrf_token: "not-retained" } });
  };
  const context = { window, document, fetch, console, Promise, Object, Array, Set, String, RegExp };
  vm.createContext(context); vm.runInContext(source, context);
  await window.__TOAN_AAS_FEATURES_READY__;
  const state = window.__TOAN_AAS_PORTAL__;
  console.log(JSON.stringify({ calls, mounts: mounts.length, options: mounts[0] && mounts[0].options,
    catalog: state.catalog, session: state.session, profile: state.profile, pageStates: state.pageStates,
    retainedCsrf: JSON.stringify(state).includes("not-retained") }));
})().catch((error) => { console.error(error); process.exit(1); });
"""


def _entry_behavior(tmp_path: Path, scenario: str) -> dict:
    assert FEATURE_ENTRY.exists(), "portal-features.js is missing"
    runner = tmp_path / "features-entry.js"
    runner.write_text(ENTRY_HARNESS, encoding="utf-8")
    completed = subprocess.run(
        ["node", str(runner), str(FEATURE_ENTRY), scenario], cwd=ROOT,
        capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return json.loads(completed.stdout.splitlines()[-1])


def test_feature_entry_hydrates_once_from_only_catalog_and_account(tmp_path: Path) -> None:
    result = _entry_behavior(tmp_path, "valid")
    assert result["calls"] == ["/api/v1/catalog", "/api/v1/auth/me"]
    assert result["mounts"] == 0 and result.get("options") is None
    assert [item["key"] for item in result["catalog"]] == ["safe_tool", "empty_copy"]
    assert result["catalog"][0]["title"] == "<Công cụ>"
    assert result["catalog"][0]["description"] == "Mô tả thật"
    assert result["session"] == {"authenticated": True, "csrfReady": False, "displayName": "QA", "email": "qa@example.invalid"}
    assert result["profile"] == {"locale": "vi"}
    assert result["retainedCsrf"] is False


def test_feature_entry_fails_closed_for_malformed_catalog_and_account(tmp_path: Path) -> None:
    result = _entry_behavior(tmp_path, "malformed")
    assert result["mounts"] == 0 and result["catalog"] == []
    assert result["session"]["authenticated"] is False
    assert result["pageStates"] == {"/features": "guarded"}


def test_feature_entry_is_small_and_has_no_external_execution_surface() -> None:
    assert FEATURE_ENTRY.exists(), "portal-features.js is missing"
    source = FEATURE_ENTRY.read_text(encoding="utf-8")
    assert len(source.splitlines()) <= 500
    assert "/catalog" in source and "/auth/me" in source
    for forbidden in (
        "/core/status", "/auth/providers", "telegram", "/wallet", "payos", "provider",
        "localStorage", "sessionStorage", "innerHTML", "startViewTransition",
    ):
        assert forbidden not in source.lower()
    for required in (
        "data-feature-key", "data-feature-route", "data-catalog-description-fallback",
        "replaceChildren", "data-portal-catalog-search", "data-portal-theme-toggle",
    ):
        assert required in source


def test_features_reserves_its_final_header_geometry_without_global_layout_changes() -> None:
    css = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
    assert ".portal-body--features .portal-header" in css
    assert "min-height: 67px" in css
    source = FEATURE_ENTRY.read_text(encoding="utf-8")
    assert '"portal-session-avatar"' in source
    assert '"portal-session-copy"' in source


def test_feature_entry_participates_in_build_id_and_fixed_shell_cache() -> None:
    pages = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
    worker = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
    assert '"portal-features.js",' in pages
    assert '"/static/portal/portal-features.js",' in worker
    for existing in (
        "/static/portal/portal-i18n.js", "/static/portal/portal.js",
        "/static/portal/portal-motion.js", "/static/portal/integration.js",
    ):
        assert f'"{existing}",' in worker
    assert "const SHELL_PATHS = new Set(SHELL);" in worker
