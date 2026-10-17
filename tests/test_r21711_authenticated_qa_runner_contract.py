"""Source contract for the isolated R217-11 authenticated browser runner."""

from __future__ import annotations

from pathlib import Path

from scripts.ci import run_authenticated_qa_matrix as matrix


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "ci" / "run_authenticated_qa_matrix.py"


def test_r21711_matrix_is_exactly_the_reviewed_route_contract() -> None:
    assert len(matrix.CUSTOMER_ROUTES) == 13
    assert len(matrix.ADMIN_ROUTES) == 6
    assert matrix.LOCALES == ("vi", "en", "zh")
    assert matrix.THEMES == ("light", "dark")
    assert tuple(item[1:3] for item in matrix.VIEWPORTS) == (
        (375, 812),
        (390, 844),
        (768, 1024),
        (1440, 900),
    )
    assert matrix.EXPECTED_RECORDS == 456


def test_r21711_runner_uses_isolated_fail_closed_safety_contract() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    for marker in (
        '"DB_FILE"',
        '"WEBAPP_SESSION_DB_PATH"',
        '"CORE_BRIDGE_BASE_URL"',
        '"PAYOS_CLIENT_ID"',
        '"provider_calls"',
        '"forbidden_mutations"',
        '"external_requests"',
        '"production_data_mutations": 0',
    ):
        assert marker in source, marker
    assert "127.0.0.1" in source
    assert "https://app.toanaas.vn" not in source


def test_r21711_runner_records_ax_focus_reload_and_artifact_hashes() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    for marker in (
        '"ax_nodes"',
        '"focus_order"',
        '"reload_persistence"',
        '"screenshot_sha256"',
        '"network_requests"',
        '"console_warnings"',
    ):
        assert marker in source, marker


def test_r21711_fixture_locale_uses_web_profile_schema() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "UPDATE web_accounts SET role_cache=?, canonical_user_id=? WHERE id=?" in source
    assert "INSERT INTO web_account_profiles" in source
    assert "SET locale=excluded.locale" in source
    assert "UPDATE web_accounts SET locale" not in source
