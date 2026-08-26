import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "static/portal/integration.js"
PORTAL = ROOT / "static/portal/portal.js"
MOTION = ROOT / "static/portal/portal-motion.js"


CATALOG_HARNESS = r"""
(async () => {
  const fs = require("node:fs"), vm = require("node:vm");
  const source = fs.readFileSync(process.argv[2], "utf8");
  const take = (start, end) => source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start)));
  const selected = [
    take("  function safeFeatureExecutionFeatures", "  function featureExecutionAllowed"),
    take("  function featurePageStates", "  function safeOAuthStartPath"),
    take("  async function hydrateCanonicalData", "  async function payloadFor"),
  ].join("\n");
  const main = { identity: "main", search: { value: "sentinel" } };
  const card = { identity: "card", href: "/video/product", title: "Video sản phẩm",
    description: "Sentinel description", engine: "web_native", productReadiness: "available" };
  const document = { activeElement: main.search };
  const initial = { path: "/features", catalog: [
    { key: "video_product", route: "/video/product" },
    { key: "image_generate", route: "/image/create" },
  ], readiness: {}, pageStates: { "/features": "read_only" },
    bridge: { featureExecutionAvailable: true, featureExecutionFeatures: ["video_product", "image_generate"] },
    session: { authenticated: true, csrfReady: true }, capabilities: { "workspace-draft-save": true } };
  const window = { __TOAN_AAS_PORTAL__: initial, location: { pathname: "/features" }, TOANAASPortal: {
    mount() { mounts += 1; currentMain = { identity: "replaced-main" }; currentCard = { identity: "replaced-card" }; }
  } };
  let mounts = 0, currentMain = main, currentCard = card, resolveStatus;
  const calls = [], FEATURE_BY_PATH = { "/video/product": "video_product", "/image/create": "image_generate" };
  const base = () => window.__TOAN_AAS_PORTAL__;
  const api = (path) => { calls.push(path); return new Promise((resolve) => { resolveStatus = resolve; }); };
  const merge = (next) => { window.__TOAN_AAS_PORTAL__ = { ...base(), ...next }; window.TOANAASPortal.mount(); };
  let canonicalHydrationEpoch = 0, canonicalSessionEpoch = 1;
  const canonicalRequestIsCurrent = () => true;
  const falseNames = [
    "isNativeInterfaceLocaleNavigatorPath", "isNativeWorkspaceMenuPath", "isNativeGuideCenterPath",
    "isNativeCommunityTrustPath", "isNativePromptStudioPath", "isNativeContentPromptPackPath",
    "isNativeContentStudioPath", "isNativeChannelStrategyPath", "isNativeVoiceStudioPath",
    "isNativeVideoStudioPath", "isNativeSubtitleStudioPath", "isNativeImageStudioPath",
    "isNativeStarterKitsPath", "isNativeMusicLibraryPath", "isNativeAdminCustomerDirectoryPath",
    "isNativeAdminSystemStewardshipPath", "isNativeAdminTaxReadinessPath",
    "isNativeAdminFinancePlanningPath", "isNativeAdminPostbackReadinessPath",
    "isNativeAdminJobRecoveryGuidePath", "isNativeAdminSecurityAccessPosturePath",
  ];
  const context = { window, document, FEATURE_BY_PATH, base, api, merge,
    canonicalRequestIsCurrent, canonicalHydrationEpoch, canonicalSessionEpoch, console };
  falseNames.forEach((name) => { context[name] = () => false; });
  vm.createContext(context);
  vm.runInContext(selected + "\nglobalThis.runCatalogHydration = hydrateCanonicalData;", context);
  const pending = context.runCatalogHydration();
  await new Promise((resolve) => setImmediate(resolve));
  resolveStatus({ data: { features: {
    video_product: { public_ready: true, adapter: "canonical" },
    image_generate: { public_ready: "yes", adapter: "malformed" },
    unknown_feature: { public_ready: true },
  } } });
  await pending;
  const state = window.__TOAN_AAS_PORTAL__;
  console.log(JSON.stringify({ calls, mounts, mainIdentity: currentMain === main, cardIdentity: currentCard === card,
    searchValue: main.search.value, focusPreserved: document.activeElement === main.search,
    card: currentCard, readiness: state.readiness, pageStates: state.pageStates }));
})().catch((error) => { console.error(error); process.exit(1); });
"""

MOTION_HARNESS = r"""
(async () => {
  const fs = require("node:fs"), vm = require("node:vm");
  const portal = fs.readFileSync(process.argv[2], "utf8");
  const motion = fs.readFileSync(process.argv[3], "utf8");
  const mount = portal.slice(portal.indexOf("  function mountPortal"), portal.indexOf("\n  let copilotState"));
  async function run(route) {
    let transitions = 0, renders = 0;
    const attrs = {}, main = { dataset: { portalPresentationPhase: "entry" },
      setAttribute(name, value) { attrs[name] = String(value); },
      removeAttribute(name) { delete attrs[name]; }, addEventListener() {} };
    const document = { startViewTransition(apply) { transitions += 1; apply(); return {
      ready: Promise.resolve(), finished: Promise.resolve(), updateCallbackDone: Promise.resolve() }; } };
    const window = { matchMedia: () => ({ matches: false }), setTimeout: () => 1 };
    const context = { window, document, console, Promise, Object, Math, Number, String, Array };
    vm.createContext(context); vm.runInContext(motion, context);
    const featureBranch = mount.includes('const featureCatalogRoute = page.path === "/features" && page.layout === "feature-catalog";')
      && mount.includes("const replaceResult = featureCatalogRoute\n      ? motion.replace(shell, main, renderShell, { animate: false })\n      : motion.replace(shell, main, renderShell);");
    main.dataset.portalMotionSkipEnter = featureBranch && route === "/features" ? "true" : "false";
    await context.window.TOANAASPortalMotion.replace({}, main, () => { renders += 1; },
      featureBranch && route === "/features" ? { animate: false } : undefined);
    return { transitions, renders, entered: attrs["data-portal-motion"] === "enter" };
  }
  console.log(JSON.stringify({ features: await run("/features"), other: await run("/chat"), mount }));
})().catch((error) => { console.error(error); process.exit(1); });
"""


def _catalog_behavior(tmp_path: Path) -> dict:
    runner = tmp_path / "catalog-hydration.js"
    runner.write_text(CATALOG_HARNESS, encoding="utf-8")
    completed = subprocess.run(
        ["node", str(runner), str(INTEGRATION)], cwd=ROOT,
        capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return json.loads(completed.stdout.splitlines()[-1])


def test_features_status_hydrates_context_without_replacing_catalog_dom(tmp_path: Path) -> None:
    result = _catalog_behavior(tmp_path)
    assert result["calls"] == ["/features/status"]
    assert result["mounts"] == 0
    assert result["mainIdentity"] and result["cardIdentity"]
    assert result["searchValue"] == "sentinel" and result["focusPreserved"]
    assert result["card"] == {
        "identity": "card", "href": "/video/product", "title": "Video sản phẩm",
        "description": "Sentinel description", "engine": "web_native", "productReadiness": "available",
    }


def test_features_status_context_is_sanitized_and_fail_closed(tmp_path: Path) -> None:
    result = _catalog_behavior(tmp_path)
    assert set(result["readiness"]["features"]) == {"video_product", "image_generate"}
    assert result["readiness"]["features"]["video_product"]["public_ready"] is True
    assert result["readiness"]["features"]["image_generate"]["public_ready"] is False
    assert result["pageStates"]["/features"] == "read_only"
    assert result["pageStates"]["/video/product"] == "ready"
    assert result["pageStates"]["/image/create"] == "guarded"


def test_cold_feature_catalog_skips_generic_transition_and_enter(tmp_path: Path) -> None:
    runner = tmp_path / "catalog-motion.js"
    runner.write_text(MOTION_HARNESS, encoding="utf-8")
    completed = subprocess.run(
        ["node", str(runner), str(PORTAL), str(MOTION)], cwd=ROOT,
        capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    result = json.loads(completed.stdout.splitlines()[-1])
    assert result["features"] == {"transitions": 0, "renders": 1, "entered": False}
    assert result["other"] == {"transitions": 1, "renders": 1, "entered": True}


def test_catalog_jank_contract_file_stays_bounded() -> None:
    assert len(Path(__file__).read_text(encoding="utf-8").splitlines()) <= 180
