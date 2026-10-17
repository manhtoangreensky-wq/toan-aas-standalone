from pathlib import Path
import re
from copyfast_pages import _fallback_template, render_portal


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / "templates" / "portal_shell.html").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def test_dashboard_shell_skip_link_has_real_focus_target():
    assert '<a class="skip-link" href="#portal-main">' in TEMPLATE
    assert re.search(r'<main class="portal-main" id="portal-main" tabindex="-1"', TEMPLATE)


def test_fallback_shell_skip_link_has_real_focus_target():
    fallback = _fallback_template()
    assert '<a class="skip-link" href="#portal-main">' in fallback
    assert re.search(r'<main id="portal-main" tabindex="-1"', fallback)


def test_dashboard_unauthenticated_route_redirects_before_shell_render():
    assert 'session = current_session(request)' in APP
    assert 'requested_locale = request.query_params.get("lang")' in APP
    assert 'f"{normalized}?lang={requested_locale}"' in APP
    assert 'f"&lang={requested_locale}"' in APP
    assert 'f"/login?next={quote(return_target, safe=\'/\')}{login_locale}"' in APP
    assert APP.index('return RedirectResponse(') < APP.index('return render_portal(page_path, interface_locale=portal_interface_locale)')


def test_shell_boot_uses_layout_skeleton_with_accessible_status_copy():
    dashboard = render_portal("/dashboard").body.decode("utf-8")
    assert re.search(r'<aside[^>]+data-portal-sidebar><div[^>]+portal-boot-skeleton-sidebar', dashboard)
    assert re.search(r'<header[^>]+data-portal-header><div[^>]+portal-boot-skeleton-header', dashboard)
    assert '__PORTAL_INITIAL_' not in dashboard
    assert 'portal-boot-skeleton-grid' in dashboard
    assert 'class="portal-sr-only">__PORTAL_BOOT_MESSAGE__</p>' in TEMPLATE
    assert '.portal-boot-skeleton' in CSS
    assert '.portal-boot-skeleton-grid' in CSS
