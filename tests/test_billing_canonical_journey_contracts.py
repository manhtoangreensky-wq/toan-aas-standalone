from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
PORTAL_CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "BILLING_CANONICAL_JOURNEY_CONTRACT.md").read_text(encoding="utf-8")


def wallet_hydration() -> str:
    start = INTEGRATION.index('} else if (path === "/wallet" || path === "/wallet/topup")')
    end = INTEGRATION.index('} else if (path === "/jobs")', start)
    return INTEGRATION[start:end]


def test_wallet_snapshot_rejects_partial_or_non_integer_ledger_rows() -> None:
    validators = INTEGRATION[
        INTEGRATION.index("function walletCanonicalText"):
        INTEGRATION.index("function dashboardCanonicalSnapshot")
    ]
    for token in (
        "function walletCanonicalHistoryRows",
        "function walletCanonicalSnapshot",
        "data.items.length > 100",
        "walletCanonicalText(item.created_at)",
        "walletCanonicalText(item.event_type)",
        "Number.isSafeInteger(item.delta_xu)",
        "Number.isSafeInteger(item.balance_after_xu)",
        "Number.isSafeInteger(wallet.balance_xu)",
        "Number.isSafeInteger(wallet.total_spent_xu)",
        "typeof wallet.is_vip === \"boolean\"",
        'throw new Error("Wallet canonical snapshot không đúng schema.")',
    ):
        assert token in validators


def test_wallet_route_blanks_projection_then_sets_ready_only_after_snapshot_validation() -> None:
    hydration = wallet_hydration()
    for token in (
        "wallet: null",
        "walletHistory: []",
        'walletReadState: "loading"',
        'api("/wallet")',
        'api("/wallet/history")',
        "const snapshot = walletCanonicalSnapshot(wallet, history);",
        "wallet: snapshot.wallet",
        "walletHistory: snapshot.history",
        'walletReadState: "ready"',
    ):
        assert token in hydration
    assert hydration.index('walletReadState: "loading"') < hydration.index('api("/wallet")')
    assert hydration.index("const snapshot = walletCanonicalSnapshot") < hydration.index('walletReadState: "ready"')
    assert 'api("/packages")' not in hydration


def test_wallet_failure_is_explicit_not_a_zero_or_empty_ledger() -> None:
    failure = INTEGRATION[INTEGRATION.index('if (path === "/wallet" || path === "/wallet/topup")', INTEGRATION.index("} catch (error) {")):]
    for token in (
        "wallet: null",
        "walletHistory: []",
        'walletReadState: "failed"',
        "Không thể xác minh số dư Xu canonical",
    ):
        assert token in failure


def test_wallet_refresh_is_signed_get_only_and_keeps_prior_verified_projection_on_error() -> None:
    helper = INTEGRATION[
        INTEGRATION.index("async function refreshWalletCanonicalProjection"):
        INTEGRATION.index("function dashboardCanonicalSnapshot")
    ]
    assert 'api("/wallet")' in helper
    assert 'api("/wallet/history")' in helper
    assert "walletCanonicalSnapshot(wallet, history)" in helper
    assert "currentPortalPath() === route" in helper
    assert "sessionEpoch === canonicalSessionEpoch" in helper
    assert 'method: "POST"' not in helper

    refresh = INTEGRATION[
        INTEGRATION.index('if (action === "wallet-refresh")'):
        INTEGRATION.index('if (action === "refresh-wallet-after-bot")')
    ]
    assert "['/wallet', '/wallet/topup'].includes(route)" in refresh
    assert 'capabilities["wallet-refresh"] === true' in refresh
    assert "setActionBusy(action, route, true)" in refresh
    assert "Số dư/lịch sử đã xác minh trước đó vẫn được giữ nguyên." in refresh

    bot_refresh = INTEGRATION[
        INTEGRATION.index('if (action === "refresh-wallet-after-bot")'):
        INTEGRATION.index('if (action === "create-ticket")')
    ]
    assert 'route !== "/wallet/topup"' in bot_refresh
    assert "refreshWalletCanonicalProjection(route, \"bot\")" in bot_refresh
    assert 'method: "POST"' not in bot_refresh


def test_wallet_renderer_never_coerces_missing_ledger_values_to_zero() -> None:
    assert "function canonicalWalletProjection(value)" in PORTAL
    assert "function canonicalWalletHistoryProjection(value)" in PORTAL
    assert "function walletReadState(context)" in PORTAL
    assert "walletReadState: [\"loading\", \"ready\", \"failed\", \"guarded\"]" in PORTAL
    for unsafe_default in (
        "wallet.balance_xu || 0",
        "wallet.total_spent_xu || 0",
        "item.delta_xu || 0",
        "item.balance_after_xu || 0",
    ):
        assert unsafe_default not in PORTAL
    wallet = PORTAL[PORTAL.index("function renderWallet(page, context)"):PORTAL.index("function renderCatalog(page, context)")]
    for token in (
        "data-wallet-read-status",
        'data-portal-action="wallet-refresh"',
        "Không hiển thị dữ liệu cũ trong lúc chờ.",
        "Web không thay thế ledger bằng activity, payment receipt hay giá trị 0.",
        "renderBillingJourney()",
    ):
        assert token in wallet


def test_billing_entrypoints_and_catalog_remain_canonical_and_honest() -> None:
    entrypoints = PORTAL[
        PORTAL.index("function renderPaymentEntryPoints(context)"):
        PORTAL.index("function renderManualTopupGuide(context)")
    ]
    for token in (
        'data-billing-entrypoint="payos"',
        'data-billing-entrypoint="manual"',
        "Nạp thủ công có đối soát",
        "Không gửi bill, số tài khoản, QR, OTP hay TXID vào Web App.",
        "Bot tạo QR động và xác nhận PayOS canonical.",
    ):
        assert token in entrypoints
    assert "<input" not in entrypoints
    assert "<textarea" not in entrypoints

    catalog = PORTAL[PORTAL.index("function renderCatalog(page, context)"):PORTAL.index("const JOB_FILTERS")]
    for token in (
        "canonicalPricingCatalog(context.pricingCatalog)",
        "canonicalPackageCatalog(context.packageCatalog)",
        "Giá chưa được Core Bridge cấp",
        "không có dòng nào đủ dữ liệu để hiển thị",
        "portal-billing-catalog-card",
    ):
        assert token in catalog
    assert "context.catalog" not in catalog
    assert 'status: "completed"' not in catalog


def test_billing_ui_uses_app_first_tokens_and_mobile_targets_without_new_gradients() -> None:
    billing_css = PORTAL_CSS[PORTAL_CSS.index("/* Billing is an app workflow"):]
    for token in (
        ".portal-billing-journey",
        ".portal-wallet-read-status",
        ".portal-billing-entrypoints .portal-payment-entry",
        ".portal-billing-catalog-intro",
        ".portal-wallet-page .portal-button { min-height: 40px; }",
        ".portal-wallet-page .portal-button { min-height: 44px; }",
        "@media (prefers-reduced-motion: reduce)",
    ):
        assert token in billing_css
    assert "linear-gradient" not in billing_css


def test_billing_contract_records_the_authority_and_recovery_boundaries() -> None:
    for token in (
        "Bot ledger qua Core Bridge",
        "Bot canonical",
        "không phải bản sao của ledger Bot",
        "Response HTTP 2xx nhưng thiếu hoặc sai một trường không được đọc thành `0 Xu`",
        "Nạp thủ công luôn handoff `/thucong`",
        "không có endpoint tạo payment-link hay webhook browser",
    ):
        assert token in CONTRACT
