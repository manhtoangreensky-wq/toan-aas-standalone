"""Static contracts for the Web-native SRT/VTT Format Lab.

The Lab is deliberately a bounded text transform: it must not be wired to a
legacy Bot handoff, an upload, a provider, a job, payment, or a file delivery
claim merely because it is presented next to subtitle workflows.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def test_subtitle_format_lab_is_a_native_route_not_a_bot_handoff() -> None:
    assert 'customerPage("/subtitle/formats", "SRT / VTT Format Lab"' in PORTAL
    assert 'layout: "subtitle-format-lab", type: "subtitle-format-lab"' in PORTAL
    assert "function renderSubtitleFormatLab(page, context)" in PORTAL
    assert 'case "subtitle-format-lab": return renderSubtitleFormatLab(page, context);' in PORTAL
    assert 'data-portal-no-transient data-portal-action="subtitle-format-convert"' in PORTAL
    assert "subtitle_formats: Object.freeze" not in PORTAL
    assert '"/subtitle/formats", "SRT/VTT Lab"' in PORTAL


def test_subtitle_format_lab_result_is_bounded_and_does_not_claim_external_execution() -> None:
    assert "function normalizeSubtitleFormatResult(raw)" in PORTAL
    assert 'source.execution !== "web_native_text_transform"' in PORTAL
    assert "source.provider_called !== false" in PORTAL
    assert "source.job_created !== false" in PORTAL
    assert "source.payment_charged !== false" in PORTAL
    assert 'class="portal-subtitle-format-output" readonly' in PORTAL
    assert "safeText(result.text)" in PORTAL
    for field in (
        "subtitleStudioEnabled: source.subtitleStudioEnabled === true",
        "subtitleStudioSummary:",
        "subtitleProjects:",
        "subtitleProjectDetail:",
        "subtitleStudioReadState:",
        "subtitleFormatToolsEnabled: source.subtitleFormatToolsEnabled === true",
        "subtitleFormatResult: normalizeSubtitleFormatResult(source.subtitleFormatResult)",
    ):
        assert field in PORTAL


def test_subtitle_format_lab_uses_csrf_native_api_and_no_legacy_bridge() -> None:
    for helper in ("subtitleFormatToolPayload", "subtitleFormatLabResultIsSafe"):
        assert f"function {helper}" in INTEGRATION
    assert '"subtitle-format-convert": Boolean(account && me.csrf_token && subtitleFormatToolsEnabled)' in INTEGRATION
    assert '"/subtitle/formats": account && subtitleFormatToolsEnabled ? "ready" : "guarded"' in INTEGRATION
    assert 'api("/subtitle-studio/format-tools/convert", {' in INTEGRATION
    assert "subtitleFormatResult: data" in INTEGRATION
    assert "subtitleFormatResult: {}," in INTEGRATION
    start = INTEGRATION.index('if (action === "subtitle-format-convert")')
    end = INTEGRATION.index('if (action === "subtitle-project-create")', start)
    action = INTEGRATION[start:end].lower()
    for forbidden in ("core bridge", "bridgeavailable", "/payments", "/jobs", "provider", "payos", "idempotency_key"):
        assert forbidden not in action


def test_subtitle_format_lab_has_private_responsive_presentation_only() -> None:
    for selector in (
        ".portal-subtitle-format-lab",
        ".portal-subtitle-format-lab-intro",
        ".portal-subtitle-format-lab-layout",
        ".portal-subtitle-format-boundary",
        ".portal-subtitle-format-result",
        ".portal-subtitle-format-output",
    ):
        assert selector in CSS
    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert "/api/v1/subtitle-studio" not in shell
    assert '"/subtitle/formats"' not in shell
