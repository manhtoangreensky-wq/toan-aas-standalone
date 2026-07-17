"""Focused UX contracts for honest empty Job and Asset centers."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")


def _section(start: str, end: str) -> str:
    offset = PORTAL.index(start)
    return PORTAL[offset:PORTAL.index(end, offset + len(start))]


def test_job_center_empty_state_routes_to_work_not_a_fake_job() -> None:
    jobs = _section("function renderJobs(page, context)", "function renderJobDetail(page, context)")

    assert 'const firstJobActions = !allJobs.length && selected === "all"' in jobs
    assert 'href="/features">Chọn workflow</a>' in jobs
    assert 'href="/workspace">Mở bản nháp Web</a>' in jobs
    assert "không do browser tự tạo" in jobs


def test_asset_center_empty_state_routes_to_asset_vault_not_a_fake_delivery() -> None:
    assets = _section("function renderAssets(page, context)", "function validVaultAssetId(value)")

    assert 'const firstAssetActions = !allAssets.length && selected === "all"' in assets
    assert 'href="/asset-vault">Mở Asset Vault</a>' in assets
    assert 'href="/features">Chọn workflow</a>' in assets
    assert "không dựng placeholder thành file hoàn tất" in assets


def test_empty_route_actions_remain_compact_and_distinct_from_a_result() -> None:
    assert ".portal-empty-route-actions {" in CSS
    assert "border: 1px solid rgba(117, 225, 209, .16)" in CSS
