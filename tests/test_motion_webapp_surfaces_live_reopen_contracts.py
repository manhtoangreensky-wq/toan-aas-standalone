"""Customer motion live-reopen contracts for shared and split Portal routes."""

from pathlib import Path
import json
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
THEME = (ROOT / "static/portal/portal-theme.css").read_text(encoding="utf-8")
MOTION = (ROOT / "static/portal/portal-motion.js").read_text(encoding="utf-8")
PORTAL = (ROOT / "static/portal/portal.js").read_text(encoding="utf-8")
FEATURES = (ROOT / "static/portal/portal-features.js").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github/workflows/webapp-quality.yml").read_text(encoding="utf-8")
MARKER = "/* MOTION-WEBAPP-SURFACES-001 live-reopen"
END_MARKER = "/* MOTION-WEBAPP-SURFACES-001 live-reopen end */"
ALLOWED = {
    ".github/workflows/webapp-quality.yml",
    "KIEM-THU/DANH-SACH-CASE.md", "KIEM-THU/HUONG-DAN-TESTER.md",
    "TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md", "TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md",
    "evidence/motion-webapp-surfaces-live-reopen-v2-20260831.md",
    "evidence/motion-webapp-surfaces-live-reopen-v2-matrix.json",
    "reports/migration/p0-05d-tester-workspace.json",
    "static/portal/portal-theme.css", "static/portal/portal-motion.js",
    "static/portal/portal.js", "static/portal/portal-features.js",
    "tests/test_motion_webapp_surfaces_live_reopen_contracts.py",
    "tests/test_p0_05d_tester_workspace.py",
}


def live_css() -> str:
    assert THEME.count(MARKER) == 2
    start = THEME.index(MARKER)
    return THEME[start : THEME.index(END_MARKER, start) + len(END_MARKER)]


def test_customer_tokens_delta_stagger_containment_and_reduced_motion() -> None:
    block = live_css()
    for token in (
        "--portal-customer-motion-control: 180ms;",
        "--portal-customer-motion-state: 360ms;",
        "--portal-customer-motion-entrance: 680ms;",
        "--portal-customer-motion-stagger: 80ms;",
        "--portal-customer-motion-distance: 20px;",
        "opacity: .12;", "scale(.985)",
        ".portal-body--features .portal-feature-group",
        "content-visibility: auto;", "contain-intrinsic-block-size: auto 620px;",
        '[data-portal-main][data-portal-motion="enter"]',
        '[data-portal-features-motion="enter"]',
        "opacity: 1 !important;", "animation: none !important;",
        "transition: none !important;", "transform: none !important;",
    ):
        assert token in block
    for forbidden in ('data-portal-app-kind="admin"', ".portal-auth", ".portal-landing", "blur(", "infinite"):
        assert forbidden not in block
    assert re.search(r"(?:transition|animation)[^;]*(?:width|height|top|left)", block) is None
    for shared in ("--portal-motion-fast: 140ms;", "--portal-motion-base: 220ms;", "--portal-motion-distance: 10px;"):
        assert shared in THEME[: THEME.index(MARKER)]


def test_shared_lifecycle_survives_hydration_and_rearms_only_offscreen() -> None:
    for token in (
        "const CUSTOMER_ENTER_CLEAR_DELAY_MS = 760;",
        "event.target !== element",
        "const markerBeforeRender =", 'markerBeforeRender === "enter"',
        "const settleVisible = opts.settleVisible !== false;",
        "function targetIsInReadableViewport(target)",
        "const revealReadablePendingTargets", ".slice(0, 6)",
        'window.addEventListener("scroll", scheduleViewportFallback, { passive: true });',
        "function refreshWorkspace(root)", "return mountWorkspace(root, { settleVisible: true });",
        "refreshWorkspace,",
    ):
        assert token in MOTION
    mount = PORTAL[PORTAL.index("  function mountPortal(") : PORTAL.index("\n\n  window.TOANAASPortal")]
    for token in (
        'options.reason === "data-hydration" && lastNormalizedRoute === actualPath',
        'const phase = isHydration ? "settled" : "entry";',
        'typeof motion.refreshWorkspace === "function"', "motion.refreshWorkspace(main);",
        "window.requestAnimationFrame(() => window.requestAnimationFrame(activateCustomerEntry));",
    ):
        assert token in mount


def test_split_features_owns_small_motion_without_loading_full_bundle() -> None:
    for token in (
        "function mountFeatureMotion(main)", 'set(shell, "data-portal-app-kind", "customer")',
        'set(entrance, "data-portal-features-motion", "enter")',
        'target.classList.add("portal-workspace-motion-target")',
        'else entry.target.classList.add("is-pending");',
        'item.classList.add("portal-workspace-motion-item")', ".slice(0, 6)",
        "const scheduleReveal = (target) => {", "new WeakSet()",
        "window.requestAnimationFrame(() => window.requestAnimationFrame(() => reveal(target)))",
        "window.requestAnimationFrame(() => window.requestAnimationFrame(activate))",
        "targets.forEach((target) => observer.observe(target));",
        "if (featureMotionReduced()) return;", "mountFeatureMotion(main);",
    ):
        assert token in FEATURES
    for forbidden_asset in ("portal-motion.js", "portal.js", "integration.js"):
        assert forbidden_asset not in FEATURES


def test_shared_runtime_marker_and_refresh_behavior() -> None:
    harness = r'''
const fs=require("fs"),vm=require("vm"),source=fs.readFileSync(process.argv[1],"utf8");
const el=(top=0,bottom=0)=>{const c=new Set(),a={},l={};return {dataset:{},style:{setProperty(n,v){this[n]=String(v)},removeProperty(n){delete this[n]}},classList:{add(...x){x.forEach(v=>c.add(v))},remove(...x){x.forEach(v=>c.delete(v))},contains(v){return c.has(v)}},setAttribute(n,v){a[n]=String(v)},removeAttribute(n){delete a[n]},getAttribute(n){return a[n]??null},addEventListener(n,f){l[n]=f},removeEventListener(){},emit(n,t=this){if(l[n])l[n]({currentTarget:this,target:t})},querySelectorAll(){return this.items||[]},closest(){return null},getBoundingClientRect(){return {top,bottom}}}};
const main=el(),visible=el(100,300),off=el(1000,1200);main.parentElement={dataset:{portalAppKind:"customer"}};visible.items=Array.from({length:7},()=>el());off.items=Array.from({length:7},()=>el());let observed=[],delays=[];class IO{constructor(cb){this.cb=cb}observe(x){observed.push(x)}unobserve(x){observed=observed.filter(v=>v!==x)}disconnect(){observed=[]}}
const window={innerHeight:900,matchMedia(){return {matches:false,addEventListener(){},removeEventListener(){}}},setTimeout(_f,d){delays.push(d);return 1},clearTimeout(){},requestAnimationFrame(f){f();return 1},cancelAnimationFrame(){},addEventListener(){},removeEventListener(){},IntersectionObserver:IO};const document={documentElement:{clientHeight:900}};vm.runInNewContext(source,{window,document,console});const m=window.TOANAASPortalMotion;
m.enter(main,"enter");main.dataset.portalPresentationPhase="settled";m.replace(null,main,()=>{});const afterHydrate=main.getAttribute("data-portal-motion");main.emit("animationend",visible);const afterChild=main.getAttribute("data-portal-motion");main.emit("animationend");const root={querySelectorAll(s){return s.includes("portal-feature-directory-controls")?[visible,off]:[]}};m.refreshWorkspace(root);process.stdout.write(JSON.stringify({delay:delays[0],afterHydrate,afterChild,afterEnd:main.getAttribute("data-portal-motion"),visiblePending:visible.classList.contains("is-pending"),offPending:off.classList.contains("is-pending"),observed:observed.includes(off),visibleItems:visible.items.filter(x=>x.classList.contains("portal-workspace-motion-item")).length,offItems:off.items.filter(x=>x.classList.contains("portal-workspace-motion-item")).length}));
'''
    result = subprocess.run(["node", "-e", harness, str(ROOT / "static/portal/portal-motion.js")], cwd=ROOT, check=True, text=True, capture_output=True)
    assert json.loads(result.stdout) == {"delay": 760, "afterHydrate": "enter", "afterChild": "enter", "afterEnd": None, "visiblePending": False, "offPending": True, "observed": True, "visibleItems": 0, "offItems": 6}


def test_pr_quality_gate_executes_changed_motion_runtime_and_contracts() -> None:
    for token in (
        "node --check static/portal/portal-features.js",
        "node --check static/portal/portal-motion.js",
        "tests/test_motion_webapp_surfaces_live_reopen_contracts.py",
        "tests/test_p0_05d_tester_workspace.py",
    ):
        assert token in WORKFLOW


def test_scope_and_size_are_exact() -> None:
    status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, check=True, text=True, capture_output=True).stdout.splitlines()
    assert {line[3:] for line in status if len(line) > 3} <= ALLOWED
    assert len(Path(__file__).read_text(encoding="utf-8").splitlines()) <= 300
