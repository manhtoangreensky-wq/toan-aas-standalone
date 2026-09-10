"""Focused browser-contract checks for applying a saved interface locale."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")


def source_between(start: str, end: str) -> str:
    beginning = INTEGRATION.index(start)
    finish = INTEGRATION.index(end, beginning)
    return INTEGRATION[beginning:finish]


def test_profile_locale_payload_is_closed_to_reviewed_interface_catalogs() -> None:
    helpers = source_between("function profileUpdateInterfaceLocale", "const WORKSPACE_SETUP_BOUNDARY_FALSE_FIELDS")

    assert 'const INTERFACE_LOCALES = new Set(["vi", "en", "zh"]);' in INTEGRATION
    assert "if (!INTERFACE_LOCALES.has(locale)) throw new Error" in helpers
    assert "display_name:" in helpers
    assert "locale: profileUpdateInterfaceLocale(source.locale)" in helpers
    assert "timezone:" in helpers
    for forbidden in (
        "source_language",
        "target_language",
        "workflow_language",
        "telegram_id",
        "canonical_user_id",
        "role:",
        "localStorage.",
        "sessionStorage.",
    ):
        assert forbidden not in helpers


def test_profile_locale_applies_only_after_signed_receipt_then_remounts() -> None:
    action = source_between('if (action === "update-profile") {', 'if (action === "upgrade-telegram-account") {')
    receipt = source_between("function confirmedProfileInterfaceLocale", "function applyConfirmedProfileInterfaceLocale")
    apply = source_between("function applyConfirmedProfileInterfaceLocale", "const WORKSPACE_SETUP_BOUNDARY_FALSE_FIELDS")

    assert "const payload = profileUpdatePayload(fields);" in action
    assert "body: JSON.stringify(payload)" in action
    assert "applyConfirmedProfileInterfaceLocale(confirmedProfileInterfaceLocale(result));" in action
    assert action.index("applyConfirmedProfileInterfaceLocale") < action.index("await hydrate();") < action.index("toast(result.message);")
    assert "merge(" not in action
    assert "INTERFACE_LOCALES.has(locale)" in receipt
    for forbidden in ("canonical_user_id", "telegram_id", "role", "source_language", "target_language", "workflow_language"):
        assert forbidden not in receipt
    assert "i18n.setLocale(locale, { emit: false })" in apply
    # The signed receipt may retain its one exact presentation value in
    # in-memory bootstrap so a render before `/auth/me` cannot flash back to
    # the old locale. It must not merge the broader profile/account receipt.
    assert "const current = base();" in apply
    assert "const currentProfile = current.profile && typeof current.profile === \"object\"" in apply
    assert "profile: { ...currentProfile, locale }" in apply
    assert "merge(" not in apply


def test_confirmed_locale_receipt_survives_a_remount_without_replacing_profile_data() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for the locale receipt regression contract")
    apply = source_between("function applyConfirmedProfileInterfaceLocale", "const WORKSPACE_SETUP_BOUNDARY_FALSE_FIELDS")
    script = f'''\nlet state = {{\n  interfaceLocale: "vi",\n  profile: {{ locale: "vi", displayName: "TOAN AAS", timezone: "Asia/Ho_Chi_Minh" }},\n  session: {{ authenticated: true }}\n}};\nconst applied = [];\nconst window = {{\n  __TOAN_AAS_PORTAL__: state,\n  TOANAASI18n: {{ setLocale(locale, options) {{ applied.push([locale, options]); }} }}\n}};\nfunction base() {{ return window.__TOAN_AAS_PORTAL__; }}\n{apply}\napplyConfirmedProfileInterfaceLocale("en");\nprocess.stdout.write(JSON.stringify({{ state: window.__TOAN_AAS_PORTAL__, applied }}));\n'''
    result = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    rendered = json.loads(result.stdout)
    assert rendered == {
        "state": {
            "interfaceLocale": "en",
            "profile": {
                "locale": "en",
                "displayName": "TOAN AAS",
                "timezone": "Asia/Ho_Chi_Minh",
            },
            "session": {"authenticated": True},
        },
        "applied": [["en", {"emit": False}]],
    }
