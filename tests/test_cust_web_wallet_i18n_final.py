"""TDD test suite for CUST-WEB-FINAL-001: complete i18n coverage for wallet & topup."""

import json
import shutil
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_WALLET_KEYS = [
    "customerWallet.kicker",
    "customerWallet.title",
    "customerWallet.subtitle",
    "customerWallet.metric.balance",
    "customerWallet.metric.rate",
    "customerWallet.metric.spent",
    "customerWallet.metric.spentNote",
    "customerWallet.metric.plan",
    "customerWallet.facts.balance",
    "customerWallet.facts.plan",
    "customerWallet.status.ready",
    "customerWallet.status.unverifiedTitle",
    "customerWallet.status.kicker",
    "customerWallet.footerNote",
    "customerWallet.action.refresh",
    "customerWallet.action.topupNow",
    "customerWallet.action.viewPackages",
    "customerWallet.action.pricing",
    "customerWallet.history.title",
    "customerWallet.history.subtitle",
    "customerWallet.history.colTime",
    "customerWallet.history.colType",
    "customerWallet.history.colDelta",
    "customerWallet.history.colBalance",
    "customerWallet.history.emptyTitle",
    "customerWallet.history.emptyBody",
    "customerWallet.history.emptyTip",
    "customerWallet.assurance.title",
]

def test_wallet_i18n_keys_defined_across_all_locales():
    """Verify that all customerWallet keys are translated in VI, EN, and ZH."""
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required")

    i18n_file = (ROOT / "static" / "portal" / "portal-i18n.js").as_posix()
    verifier = f"""
    const fs = require('fs');
    const content = fs.readFileSync({json.dumps(i18n_file)}, 'utf-8');
    const sandbox = {{}};
    const fn = new Function('window', 'globalThis', content);
    fn(sandbox, sandbox);
    const i18n = sandbox.TOANAASI18n;

    const keys = {json.dumps(REQUIRED_WALLET_KEYS)};
    const locales = ['vi', 'en', 'zh'];
    const missing = {{}};

    for (const loc of locales) {{
        i18n.setLocale(loc);
        missing[loc] = [];
        for (const k of keys) {{
            if (!i18n.has(k)) {{
                missing[loc].push(k);
            }}
        }}
    }}
    console.log(JSON.stringify(missing));
    """

    res = subprocess.run([node, "-e", verifier], capture_output=True, text=True)
    assert res.returncode == 0, f"Node script error: {res.stderr}"
    results = json.loads(res.stdout)

    for loc in ("vi", "en", "zh"):
        assert results[loc] == [], f"Missing keys in locale {loc}: {results[loc]}"

def test_portal_wallet_uses_i18n_keys():
    """Verify that portal.js uses the customerWallet i18n keys instead of hardcoded strings."""
    portal_text = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
    assert 'uiText("customerWallet.kicker"' in portal_text
    assert 'uiText("customerWallet.title"' in portal_text
    assert 'uiText("customerWallet.metric.balance"' in portal_text
    assert 'uiText("customerWallet.history.title"' in portal_text
