"""Static contracts for canonical and ERP stale-response isolation."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")


def test_bootstrap_invalidates_private_sessions_before_its_first_await() -> None:
    start = INTEGRATION.index("async function hydrate()")
    first_fetch = INTEGRATION.index("const [catalogResponse", start)
    first_response_guard = INTEGRATION.index("if (bootstrapEpoch !== portalHydrationEpoch) return;", first_fetch)
    source = INTEGRATION[start:first_fetch]

    assert "const bootstrapEpoch = ++portalHydrationEpoch;" in source
    for epoch in (
        "canonicalSessionEpoch",
        "canonicalAdminDataHydrationEpoch",
        "campaignSessionEpoch",
        "projectCenterSessionEpoch",
        "promptLibrarySessionEpoch",
        "freePromptGallerySessionEpoch",
        "assetVaultSessionEpoch",
        "supportSessionEpoch",
        "contentStudioSessionEpoch",
        "operationsSessionEpoch",
    ):
        assert f"++{epoch};" in source

    assert first_response_guard > first_fetch
    assert first_response_guard < INTEGRATION.index("const catalogData", first_fetch)


def test_canonical_bridge_reads_require_latest_session_route_and_request() -> None:
    helper = INTEGRATION[
        INTEGRATION.index("function canonicalRequestIsCurrent"):
        INTEGRATION.index("function canonicalAdminDataRequestIsCurrent")
    ]
    for requirement in (
        "requestEpoch === canonicalHydrationEpoch",
        "sessionEpoch === canonicalSessionEpoch",
        "currentPortalPath() === expectedPath",
        "base().bridge && base().bridge.available === true",
        "base().session && base().session.authenticated === true",
    ):
        assert requirement in helper

    source = INTEGRATION[
        INTEGRATION.index("async function hydrateCanonicalData()"):
        INTEGRATION.index("async function payloadFor", INTEGRATION.index("async function hydrateCanonicalData()"))
    ]
    assert "const requestEpoch = ++canonicalHydrationEpoch;" in source
    assert "const isCurrent = () => canonicalRequestIsCurrent(requestEpoch, sessionEpoch, path);" in source
    # Every canonical branch awaits remote data, then fences it before merge
    # or polling. The count deliberately catches regressions in new branches.
    assert source.count("if (!isCurrent()) return null;") >= 15
    assert "scheduleJobPolling(path, items);" in source
    assert "scheduleJobPolling(path, record);" in source
    assert "await hydrateCanonicalAdminData(path);" in source
    assert "if (!isCurrent()) return null;\n      if (error" in source


def test_admin_read_wrapper_is_route_scoped_and_used_by_refresh_and_write_readback() -> None:
    wrapper = INTEGRATION[
        INTEGRATION.index("function canonicalAdminDataRequestIsCurrent"):
        INTEGRATION.index("async function hydrateCanonicalData()")
    ]
    for requirement in (
        "requestEpoch === canonicalAdminDataHydrationEpoch",
        "sessionEpoch === canonicalSessionEpoch",
        "currentPortalPath() === expectedPath",
        "expectedPath.startsWith(\"/admin\")",
        "expectedPath !== \"/admin/audit\"",
        "async function hydrateCanonicalAdminData(path)",
        "adminData: {},",
    ):
        assert requirement in wrapper

    # The low-level adapter remains behind exactly one guarded wrapper call;
    # action refreshes and post-write readbacks cannot bypass it.
    assert INTEGRATION.count("await readAdminPath(") == 1
    assert INTEGRATION.count("await hydrateCanonicalAdminData(") >= 4
    assert "adminData: {}," in INTEGRATION
