"""Static Portal contracts for signed, Web-native Channel Strategy.

The frozen Bot ``videoref`` conversation is only a product reference.  Web
profiles remain private, revisioned account records; their deterministic
direction must never turn into a Bot/social/provider/job/payment shortcut.
"""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
BACKEND = (ROOT / "copyfast_channel_strategy.py").read_text(encoding="utf-8")
REGISTRY = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")


def _section(text: str, start: str, end: str) -> str:
    offset = text.index(start)
    return text[offset:text.index(end, offset + len(start))]


def _action_block(action: str) -> str:
    marker = f'if (action === "{action}")'
    offset = INTEGRATION.index(marker)
    next_offset = INTEGRATION.find('if (action === "', offset + len(marker))
    return INTEGRATION[offset:] if next_offset < 0 else INTEGRATION[offset:next_offset]


def _bootstrap_normalizer() -> str:
    """Return only the presentation boundary that runs after every render."""
    return _section(PORTAL, "function normalizeBootstrap(raw)", "function getBootstrap()")


def test_channel_strategy_has_private_native_routes_and_portal_navigation() -> None:
    desktop_nav = _section(PORTAL, "function navGroups(context, currentPage)", "function matchesRouteFamily")
    mobile_nav = _section(PORTAL, "function isMobileNavCurrent(key, page)", "function renderMobileNav(page)")

    assert 'WebFeature("channel_strategy"' in REGISTRY
    assert 'customerPage("/content/channel-strategy", "Channel Strategy"' in PORTAL
    assert 'layout: "channel-strategy", type: "channel-strategy"' in PORTAL
    assert 'path: "/content/channel-strategy/:id"' in PORTAL
    assert "function renderChannelStrategy(page, context)" in PORTAL
    assert "function renderChannelStrategyDetail(page, context)" in PORTAL
    assert 'case "channel-strategy": return renderChannelStrategy(page, context);' in PORTAL
    assert 'case "channel-strategy-detail": return renderChannelStrategyDetail(page, context);' in PORTAL
    assert '"/content/channel-strategy", "Channel Strategy"' in desktop_nav
    assert '"/content/channel-strategy"' in mobile_nav
    assert 'if (linkPath === "/content/channel-strategy")' in PORTAL


def test_channel_strategy_uses_only_its_bounded_web_api_and_no_execution_fallback() -> None:
    routes = (
        'api("/channel-strategy/summary")',
        "function channelStrategyProfilesPath(options)",
        'api("/channel-strategy/profiles/" + encodeURIComponent(String(profileId)))',
        'path: "/channel-strategy/profiles"',
        'path: `/channel-strategy/profiles/${encodeURIComponent(profileId)}`',
        'api(`/channel-strategy/profiles/${encodeURIComponent(profileId)}/strategy-preview`, {',
    )
    for route in routes:
        assert route in INTEGRATION

    action_blocks = [
        _action_block("channel-strategy-create"),
        _action_block("channel-strategy-update"),
        _section(
            INTEGRATION,
            'if (action === "channel-strategy-archive" || action === "channel-strategy-restore")',
            'if (action === "channel-strategy-preview")',
        ),
        _action_block("channel-strategy-preview"),
    ]
    for block in action_blocks:
        block = block.lower()
        for forbidden in (
            'api("/jobs',
            'api("/payments',
            'api("/wallet',
            'api("/internal',
            "window.telegram",
            "payos",
            "fetch(",
            "social_platform",
        ):
            assert forbidden not in block

    assert "isNativeChannelStrategyPath(currentPath)" in INTEGRATION
    assert "!isNativeChannelStrategyPath(currentPath)" in INTEGRATION
    assert '"channel-strategy-create": Boolean(account && me.csrf_token && channelStrategyEnabled)' in INTEGRATION
    assert '"channel-strategy-preview": Boolean(account && me.csrf_token && channelStrategyEnabled)' in INTEGRATION


def test_channel_strategy_validates_non_execution_boundary_and_never_caches_private_profiles() -> None:
    validator = _section(
        INTEGRATION,
        "function channelStrategyBoundaryIsSafe(data, execution, profilePersisted)",
        "function channelStrategyPreviewIsSafe(data, profileId, expectedRevision)",
    )
    preview = _section(
        INTEGRATION,
        "function channelStrategyPreviewIsSafe(data, profileId, expectedRevision)",
        "function contentStudioSafetyError(...values)",
    )
    boundary = _section(BACKEND, "def _boundary(*, profile_persisted: bool)", "def _preview_boundary()")

    assert '"execution": "web_native_channel_strategy_profile_only"' in boundary
    assert '"execution": "web_native_deterministic_channel_strategy_preview_only"' in BACKEND
    for field in (
        "telegram_state_changed",
        "bot_called",
        "bridge_called",
        "channel_url_fetched",
        "social_platform_called",
        "provider_called",
        "job_created",
        "wallet_mutated",
        "payment_started",
        "asset_saved",
        "publish_action_created",
        "delivery_created",
        "analytics_claim_verified",
    ):
        assert f'"{field}"' in boundary
        assert field in validator
    assert "data.strategy_persisted !== false" in preview
    assert '"/" + "api/v1/channel-strategy"' in SERVICE_WORKER
    assert '"/content/channel-strategy"' in SERVICE_WORKER
    assert 'const CACHE_PREFIX = "toan-aas-portal-shell-";' in SERVICE_WORKER
    assert "const BUILD_ID = workerBuildId();" in SERVICE_WORKER
    assert "const CACHE_NAME = `${CACHE_PREFIX}${BUILD_ID}`;" in SERVICE_WORKER
    assert ".filter((key) => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME)" in SERVICE_WORKER


def test_channel_strategy_bootstrap_keeps_the_current_signed_projection() -> None:
    """Rendering must not silently discard an already-verified private read.

    Channel Strategy carries positioning and review metadata.  The integration
    layer deliberately clears it before a new signed read, but a later portal
    render must retain the *current* server projection rather than replacing
    it with empty/default values.
    """
    normalizer = _bootstrap_normalizer()
    for field in (
        "channelStrategyEnabled",
        "channelStrategySummary",
        "channelStrategyProfiles",
        "channelStrategyProfileDetail",
        "channelStrategyPreview",
        "channelStrategyReadState",
    ):
        assert f"{field}:" in normalizer
        assert f"source.{field}" in normalizer

    assert re.search(r"channelStrategyEnabled:\s*source\.channelStrategyEnabled\s*===\s*true", normalizer)
    assert re.search(r"channelStrategyProfiles:\s*Array\.isArray\(source\.channelStrategyProfiles\)", normalizer)
    assert "source.channelStrategyProfiles.slice(0, 100)" in normalizer
    assert re.search(
        r"channelStrategyReadState:\s*\[\"loading\", \"ready\", \"failed\", \"guarded\"\]\.includes",
        normalizer,
    )


def test_channel_strategy_hydration_fences_session_list_detail_and_current_signed_path() -> None:
    """Late profile reads may never cross account, route, or request epochs."""
    for name in (
        "channelStrategySessionEpoch",
        "channelStrategyListHydrationEpoch",
        "channelStrategyDetailHydrationEpoch",
    ):
        assert re.search(r"(?:\+\+|\+=\s*1)" + re.escape(name), INTEGRATION), name

    assert "function channelStrategyRequestIsCurrent(" in INTEGRATION
    # definition + list invocation + detail invocation
    assert INTEGRATION.count("channelStrategyRequestIsCurrent(") >= 3
    assert "const sessionEpoch = channelStrategySessionEpoch;" in INTEGRATION
    assert "const requestEpoch = ++channelStrategyListHydrationEpoch;" in INTEGRATION
    assert "const requestEpoch = ++channelStrategyDetailHydrationEpoch;" in INTEGRATION
    assert "if (!channelStrategyRequestIsCurrent(" in INTEGRATION

    guard_start = INTEGRATION.index("function channelStrategyRequestIsCurrent(")
    guard_end = INTEGRATION.index("async function hydrateChannelStrategy(overrides)", guard_start)
    guard = INTEGRATION[guard_start:guard_end]
    assert "currentPortalPath()" in guard
    assert "base().channelStrategyEnabled === true" in guard
    assert "base().session" in guard and "authenticated === true" in guard
