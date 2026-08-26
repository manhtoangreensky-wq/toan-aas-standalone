"""Static lifecycle contract for clear, stationary public Auth entry."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")


def _mount_portal() -> str:
    start = PORTAL.index("function mountPortal(override) {")
    end = PORTAL.index("\n\n  window.TOANAASPortal", start)
    return PORTAL[start:end]


def test_auth_surface_skips_generic_main_enter_before_replace() -> None:
    mount = _mount_portal()
    existing_assignment = (
        'main.dataset.portalMotionSkipEnter = landingMotionRoute || dashboardMotionRoute '
        '|| featureCatalogRoute || isCustomerDirectoryRoute || isAdminPortalSurface(page) ? "true" : "false";'
    )
    auth_override = 'if (isAuth) main.dataset.portalMotionSkipEnter = "true";'

    assert existing_assignment in mount
    assert auth_override in mount
    assert mount.index(existing_assignment) < mount.index(auth_override) < mount.index(
        "const replaceResult = featureCatalogRoute"
    )
