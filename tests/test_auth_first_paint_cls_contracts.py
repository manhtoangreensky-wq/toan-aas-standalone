from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
THEME_JS = ROOT / "static" / "portal" / "portal-theme.js"
CSS = ROOT / "static" / "portal" / "portal-first-paint.css"
HTML = ROOT / "templates" / "portal_shell.html"

def test_theme_head_script_maps_auth_surface():
    content = THEME_JS.read_text(encoding="utf-8")
    assert 'data-portal-initial-surface' in content

    assert '/welcome' in content
    assert '/login' in content
    assert '/register' in content
    assert '/password-recovery' in content
    assert '/admin/login' in content

    # Isolate INITIAL_SURFACES block cho negative dashboard
    start = content.find('INITIAL_SURFACES')
    end = content.find('});', start)
    block = content[start:end]
    assert '"/dashboard"' not in block and "'/dashboard'" not in block

    assert 'auth' in content
    assert 'landing' in content

def test_template_loads_first_paint_css_in_correct_order():
    content = HTML.read_text(encoding="utf-8")

    theme_js = 'src="/static/portal/portal-theme.js'
    first_paint = 'href="/static/portal/portal-first-paint.css'
    portal_css = 'href="/static/portal/portal.css'

    assert first_paint in content, "Must include portal-first-paint.css"

    idx_theme = content.find(theme_js)
    idx_first_paint = content.find(first_paint)
    idx_portal_css = content.find(portal_css)

    assert idx_first_paint > idx_theme, "portal-first-paint.css must be after portal-theme.js"
    assert idx_portal_css > idx_first_paint, "portal-first-paint.css must be before portal.css"

def test_css_prehides_minimal_shell_and_is_safe():
    assert CSS.exists(), "portal-first-paint.css is missing"
    content = CSS.read_text(encoding="utf-8")

    lines = content.splitlines()
    assert len(lines) <= 120, "Must be <= 120 lines"

    assert 'data-portal-initial-surface' in content
    assert 'display: none' in content

    assert 'animation' not in content
    assert 'opacity' not in content
    assert 'filter' not in content

    # Assert thật desktop 26/mobile 22/bottom 42 và Landing 0
    assert 'padding-top: 26px !important;' in content
    assert 'padding-top: 22px !important;' in content
    assert 'padding-bottom: 42px !important;' in content
    assert 'padding-top: 0 !important;' in content
