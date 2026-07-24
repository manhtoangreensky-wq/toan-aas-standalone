"""Focused contracts for the app-first signed access and first-run journey."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "SECURE_ACCESS_FIRST_RUN_UI_CONTRACT.md").read_text(encoding="utf-8")


def _section(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset : source.index(end, offset + len(start))]


def test_auth_keeps_email_primary_and_reveals_optional_methods_progressively() -> None:
    auth = _section(PORTAL, "function renderAuth(page, context)", "const RESULT_LABELS")
    for token in (
        'const isLogin = page.path === "/login";',
        'const isRegister = page.path === "/register";',
        'class="portal-auth-page portal-auth-page--access"',
        'class="portal-auth-primary"',
        'class="portal-auth-alternatives"',
        'Dùng Telegram hoặc OAuth',
        "renderTelegramLoginMethod(context)",
        "renderOAuthRegistrationMethods(context)",
        "alternativeMethodsOpen",
        "Không nhập ID Telegram thô",
    ):
        assert token in auth
    assert auth.index("const primaryForm") < auth.index("const alternativeMethods")
    assert 'name="telegram_id"' not in auth
    telegram_method = _section(PORTAL, "function renderTelegramLoginMethod(context)", "function renderOAuthRegistrationMethods(context)")
    for action in ("start-telegram-login", "refresh-telegram-login"):
        assert action in telegram_method
    assert "auth-mfa-login" in auth


def test_register_defaults_and_account_entry_are_concise_without_relaxing_security() -> None:
    auth = _section(PORTAL, "function renderAuth(page, context)", "const RESULT_LABELS")
    account = _section(PORTAL, "function renderAccount(page, context)", "function renderInterfaceLocaleNavigator")
    assert "Hồ sơ mặc định sau khi tạo" in auth
    assert "Không nhập ID Telegram thô" in auth
    for token in (
        "const accountNextAction = linked",
        'class="portal-account-command"',
        "Signed session hợp lệ",
        'href: "/account/security"',
        'href: "/onboarding"',
    ):
        assert token in account
    for forbidden in ("localStorage.setItem", "sessionStorage.setItem", "telegram_id"):
        assert forbidden not in account


def test_optional_telegram_onboarding_preserves_the_bounded_continuation_route() -> None:
    onboarding = _section(PORTAL, "function renderOnboarding(page, context)", "function authProviderMark(provider)")
    for token in (
        "const skipRoute = workspaceRoute;",
        'const skipLabel = continuation ? "Mở lại workflow" : "Vào Workspace";',
        'class="portal-onboarding-route"',
        "Workflow sẽ được giữ lại",
        "Web hoạt động độc lập",
        "Chỉ khi bạn muốn đọc dữ liệu canonical từ Bot",
    ):
        assert token in onboarding
    choice = onboarding[onboarding.index("const independentWorkspaceChoice"):onboarding.index("const linkChallengePaused")]
    assert 'href="${safeText(skipRoute)}"' in choice
    assert ">${safeText(skipLabel)}</a>" in choice
    for action in ("start-telegram-link", "refresh-link-status", "copy-telegram-link-command"):
        assert action in onboarding


def test_access_and_account_routes_remain_private_to_the_pwa() -> None:
    private_prefixes = WORKER.split("const PRIVATE_PATH_PREFIXES = Object.freeze([", 1)[1].split("]);", 1)[0]
    shell = WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    for route in ('"/onboarding"', '"/account"'):
        assert route in private_prefixes
        assert route not in shell


def test_new_access_scope_uses_flat_app_tokens_and_mobile_accessibility_rules() -> None:
    scope = CSS[CSS.index("/* Secure Access & First-Run Journey"):]
    for token in (
        ".portal-auth-page--access",
        ".portal-auth-journey",
        ".portal-auth-alternatives summary:focus-visible",
        ".portal-onboarding-route",
        ".portal-account-command",
        "min-height: 44px",
        "@media (prefers-reduced-motion: reduce)",
    ):
        assert token in scope
    assert "linear-gradient" not in scope


def test_contract_records_existing_authority_and_non_goals() -> None:
    for token in (
        "Email + mật khẩu",
        "raw Telegram ID",
        "Google/GitHub/Apple",
        "workspaceRoute",
        "PRIVATE_PATH_PREFIXES",
        "PayOS",
        "bot.py",
        "44px",
    ):
        assert token in CONTRACT
