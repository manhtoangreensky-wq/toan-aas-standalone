"""Focused static contracts for the private Web-native Music/SFX libraries.

These checks intentionally pin the narrow boundary that is easy to regress:
the library must list only signed owner metadata and must not silently become a
generic bridge asset page, Bot handoff, audio player, provider/catalog lookup,
or PWA-cached private view.
"""

from pathlib import Path
import re


ROOT = Path(__file__).parents[1]
ROUTER = (ROOT / "copyfast_music_media.py").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "MUSIC_SFX_LIBRARY_CONTRACT.md").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    return source[source.index(start) : source.index(end, source.index(start))]


def _generic_asset_hydration(source: str) -> str:
    match = re.search(
        r'else if \(path === "/assets".*?const assets = await api\("/assets"\)',
        source,
        flags=re.DOTALL,
    )
    assert match is not None, "expected the existing generic /assets hydration branch"
    return match.group(0)


def test_library_endpoint_is_a_narrow_signed_owner_read() -> None:
    assert '@router.get("/library-items")' in ROUTER
    endpoint = _between(ROUTER, "async def list_library_items", "@router.")
    for required in (
        "require_account",
        "read_transaction",
        "account_id",
        "role",
        "music",
        "sfx",
        "web_media_items",
        "web_media_collections",
        "web_asset_files",
        "active",
        "has_more",
    ):
        assert required in endpoint
    for forbidden in (
        "with transaction() as conn:",
        "_idempotent(",
        "_event(",
        "_audit(",
        "_require_preview_enabled(",
        "open_verified_private_asset_stream(",
        "private_asset_inline_response(",
        "a.display_name",
    ):
        assert forbidden not in endpoint.lower()


def test_library_projection_does_not_surface_asset_or_delivery_secrets() -> None:
    projector = _between(ROUTER, "def _library_item_public", "def _library_read_boundaries")
    for required in (
        '"collection_id"',
        '"collection_title"',
        '"role"',
        '"reference_title"',
        '"tags"',
        '"favorite"',
        '"user_declared_duration_seconds"',
        '"updated_at"',
        '"collection_updated_at"',
    ):
        assert required in projector
    for forbidden in (
        '"storage_key"',
        '"sha256"',
        '"original_filename"',
        '"content_type"',
        '"byte_size"',
        '"download_url"',
        '"source_url"',
        '"asset_id"',
        '"item_id"',
        '"attribution"',
        '"license_note"',
        '"creative_brief"',
        "row[9]",
    ):
        assert forbidden not in projector
    boundary = _between(ROUTER, "def _library_read_boundaries", "def _audio_asset_not_found")
    for required in (
        '"execution": "web_native_media_library_read_only"',
        '"library_persisted": False',
        '"collection_mutated": False',
        '"provider_called": False',
        '"catalog_searched": False',
        '"player_opened": False',
        '"preview_created": False',
        '"job_created": False',
        '"wallet_mutated": False',
        '"payment_started": False',
        '"delivery_created": False',
        '"bot_called": False',
        '"telegram_called": False',
        '"rights_verified": False',
        '"release_approved": False',
    ):
        assert required in boundary


def test_music_and_sfx_pages_are_native_library_layouts_not_bridge_asset_pages() -> None:
    music_page = _between(PORTAL, 'customerPage("/music/library"', 'customerPage("/music/sfx-library"')
    sfx_page = _between(PORTAL, 'customerPage("/music/sfx-library"', 'featurePage("/music/create"')
    for page in (music_page, sfx_page):
        assert 'layout: "music-library"' in page
        assert "readOnlyPage" not in page
        assert "botCompanionPage" not in page
    assert '"/music-library"' in music_page
    assert "function isNativeMusicLibraryPath" in INTEGRATION
    assert "async function hydrateMusicLibrary" in INTEGRATION
    assert "/media-workspace/library-items" in INTEGRATION


def test_library_routes_do_not_fall_back_to_generic_assets_or_audio_execution() -> None:
    generic_assets = _generic_asset_hydration(INTEGRATION)
    for route in ('"/music/library"', '"/music-library"', '"/music/sfx-library"'):
        assert route not in generic_assets

    # The Web-native fetch stays on the narrow owner-scoped namespace rather
    # than using the old bridge asset response.  Rendering/future actions get
    # separate tests in their own scope; this one avoids locking helper order.
    assert "/media-workspace/library-items" in INTEGRATION


def test_private_music_library_paths_are_explicitly_outside_pwa_shell_cache() -> None:
    private = _between(SERVICE_WORKER, "const PRIVATE_PATH_PREFIXES", "]);\n\nself.addEventListener")
    for path in ('"/music/library"', '"/music-library"', '"/music/sfx-library"'):
        assert path in private

    shell = _between(SERVICE_WORKER, "const SHELL = Object.freeze([", "]);\nconst SHELL_PATHS")
    for path in ("/music/library", "/music-library", "/music/sfx-library"):
        assert path not in shell
    assert "/api/v1/media-workspace" in SERVICE_WORKER


def test_contract_records_the_truthful_no_execution_boundary() -> None:
    for required in (
        "Music & SFX Library",
        "metadata-only",
        "signed Web session",
        "read transaction only",
        "not an audio catalogue",
        "delivery centre or generation",
        "does not call a provider",
        "P0 source-review count therefore remains unchanged",
        "public shell",
    ):
        assert required in CONTRACT
