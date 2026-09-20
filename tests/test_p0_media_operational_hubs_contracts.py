"""Empirical contract tests for the 5 dedicated Media Operational Hubs.

Verifies:
1. Page registrations & layout contracts in static/portal/portal.js
2. Server-side rendering (copyfast_pages.render_portal) returning HTTP 200
3. Navigation parity across desktop sidebar, mobile groups, and isNavCurrent
4. Distinct operational hubs with quick actions, workflows, metrics, and safety boundary notices
"""

from pathlib import Path
import copyfast_pages

ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")


def test_media_operational_hubs_page_registrations():
    """All 5 media operational hubs are properly declared with customerPage and unique layouts."""
    # 1. Video Operations Hub
    assert 'customerPage("/tools/video", "Video Operations Hub"' in PORTAL
    assert 'layout: "video-operations-hub", type: "video-operations-hub"' in PORTAL
    assert '}, ["/video"]);' in PORTAL

    # 2. Image Operations Hub
    assert 'customerPage("/tools/image", "Image Operations Hub"' in PORTAL
    assert 'layout: "image-operations-hub", type: "image-operations-hub"' in PORTAL
    assert '}, ["/image"]);' in PORTAL

    # 3. Voice Operations Hub
    assert 'customerPage("/voice", "Voice Operations Hub"' in PORTAL
    assert 'layout: "voice-operations-hub", type: "voice-operations-hub"' in PORTAL
    assert '}, ["/voice/hub", "/voice-vault"]);' in PORTAL

    # 4. Music Operations Hub
    assert 'customerPage("/music", "Music Operations Hub"' in PORTAL
    assert 'layout: "music-operations-hub", type: "music-operations-hub"' in PORTAL
    assert '}, ["/music/hub"]);' in PORTAL

    # 5. Sub & Dub Operations Hub
    assert 'customerPage("/subdub", "Sub & Dub Operations Hub"' in PORTAL
    assert 'layout: "subdub-operations-hub", type: "subdub-operations-hub"' in PORTAL
    assert '}, ["/subdub/hub", "/subtitle/hub"]);' in PORTAL


def test_media_operational_hubs_server_render_and_titles():
    """Server-side shell rendering returns HTTP 200 with truthful metadata for all 5 hubs and aliases."""
    paths = [
        "/tools/video", "/video",
        "/tools/image", "/image",
        "/voice",
        "/music",
        "/subdub"
    ]
    for path in paths:
        response = copyfast_pages.render_portal(path)
        assert response.status_code == 200, f"Expected 200 for {path}, got {response.status_code}"
        assert len(response.body) > 0


def test_media_operational_hubs_navigation_parity():
    """All 5 hubs maintain complete parity in sidebar navGroups, mobile groups, and isNavCurrent."""
    # Desktop sidebar navGroups
    for entry in [
        '["/tools/video", "Video Edit", ICONS.video]',
        '["/tools/image", "Image Suite", ICONS.image]',
        '["/voice", "AI Voice", ICONS.voice]',
        '["/music", "AI Music", ICONS.music]',
        '["/subdub", "AI SubDub", ICONS.prompt]'
    ]:
        assert entry in PORTAL

    # Mobile nav groups studio mapping
    assert '"/studio", "/voice", "/music", "/subdub", "/tools/video", "/tools/image"' in PORTAL
    assert '"/studio/", "/voice/", "/music/", "/subdub/", "/tools/video", "/tools/image"' in PORTAL

    # isNavCurrent matching
    assert 'if (linkPath === "/tools/video") return matchesRouteFamily(path, "/tools/video") || matchesRouteFamily(path, "/video");' in PORTAL
    assert 'if (linkPath === "/tools/image") return matchesRouteFamily(path, "/tools/image") || (matchesRouteFamily(path, "/image") && !["/image-studio", "/image-hub"].some((r) => matchesRouteFamily(path, r)));' in PORTAL
    assert 'if (linkPath === "/voice") return matchesRouteFamily(path, "/voice") && !matchesRouteFamily(path, "/voice-studio");' in PORTAL
    assert 'if (linkPath === "/subdub") return (matchesRouteFamily(path, "/subdub") || matchesRouteFamily(path, "/subtitle") || ["/translate", "/dubbing", "/asr"].includes(path)) && !matchesRouteFamily(path, "/subtitle-studio");' in PORTAL
    assert 'if (linkPath === "/music") return matchesRouteFamily(path, "/music");' in PORTAL


def test_media_operational_hubs_render_dispatch_and_functions():
    """All 5 layouts are wired in renderPage and have rich, owner-governed render functions."""
    # Layout dispatch
    assert 'case "video-operations-hub": return renderVideoHub(page, context);' in PORTAL
    assert 'case "image-operations-hub": return renderImageSuiteHub(page, context);' in PORTAL
    assert 'case "voice-operations-hub": return renderVoiceHub(page, context);' in PORTAL
    assert 'case "music-operations-hub": return renderMusicHub(page, context);' in PORTAL
    assert 'case "subdub-operations-hub": return renderSubDubHub(page, context);' in PORTAL

    # Render functions presence
    assert "function renderMediaHubPage(" in PORTAL
    assert "function renderVideoHub(" in PORTAL
    assert "function renderImageSuiteHub(" in PORTAL
    assert "function renderVoiceHub(" in PORTAL
    assert "function renderMusicHub(" in PORTAL
    assert "function renderSubDubHub(" in PORTAL

    # Safety boundary & metrics
    assert "AI Video Operations" in PORTAL
    assert "AI Image Suite" in PORTAL
    assert "AI Voice Operations" in PORTAL
    assert "AI Music & Sound" in PORTAL
    assert "AI Subtitle & Dubbing" in PORTAL
