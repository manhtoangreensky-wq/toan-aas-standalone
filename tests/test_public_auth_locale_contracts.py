"""Static contracts for locale-safe public account presentation."""

from pathlib import Path

from copyfast_pages import render_portal


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    return source[begin : source.index(end, begin + len(start))]


def _page_definition(path: str) -> str:
    begin = PORTAL.index(f'path: "{path}"')
    return PORTAL[begin : PORTAL.index("  });", begin)]


def test_public_auth_locale_copy_is_complete_without_new_browser_authority() -> None:
    auth = _between(PORTAL, "function renderAuth", "const RESULT_LABELS")
    fields = _between(PORTAL, "const FIELD_SETS = Object.freeze({", "// Public account and portal routes.")

    for key in (
        "access.heading.recovery",
        "access.intro.recovery",
        "access.primary.recovery",
        "access.primary.recoveryDescription",
        "access.action.recovery",
        "access.context.recoveryTitle",
        "access.field.recoveryEmail",
        "access.help.recoveryEmail",
        "access.notice.registrationHandoffTitle",
        "access.notice.registrationHandoffBody",
        "access.oauth.title",
        "access.oauth.unavailable",
        "access.oauth.cancelled",
        "access.oauth.failed",
        "access.oauth.state",
        "access.oauth.session",
        "access.oauth.linkRequired",
        "access.oauth.linked",
        "access.oauth.alreadyLinked",
        "access.notice.defaultProfileTitle",
        "access.notice.defaultProfileBody",
    ):
        assert I18N.count(f'"{key}"') == 3

    assert 'labelKey: "access.field.recoveryEmail"' in fields
    assert 'placeholderKey: "access.placeholder.email"' in fields
    assert 'helpKey: "access.help.recoveryEmail"' in fields
    assert 'actionLabelKey: "access.action.recovery"' in PORTAL
    for required in (
        'accessText("heading.recovery", "Khôi phục mật khẩu")',
        'accessText("intro.recovery", "Yêu cầu liên kết đặt lại mật khẩu một cách riêng tư.")',
        'accessText("primary.recovery", "Khôi phục mật khẩu")',
        'accessText("primary.recoveryDescription", "Nhập email để nhận hướng dẫn an toàn.")',
        'accessText("context.recoveryTitle", "Khôi phục quyền truy cập vào không gian làm việc của bạn.")',
        'accessText("notice.registrationHandoffTitle", "Tiếp tục bằng đăng nhập")',
        'accessText("notice.registrationHandoffBody", "Nếu email chưa có tài khoản, hồ sơ đã được tạo. Hãy đăng nhập để tiếp tục; bạn có thể liên kết Telegram sau.")',
        'accessText("oauth.title", "OAuth")',
        'accessText("notice.defaultProfileTitle", "Hồ sơ mặc định sau khi tạo")',
        'accessText("notice.defaultProfileBody", "Locale Tiếng Việt · múi giờ Asia/Ho_Chi_Minh · avatar gradient. Email + mật khẩu (có thể dùng Gmail) đang hoạt động. Không nhập ID Telegram thô. Telegram Login, Google OAuth, GitHub OAuth và Sign in with Apple chỉ mở khi server có cấu hình thật; Bot chỉ mở dữ liệu canonical sau khi xác minh cùng identity.")',
    ):
        assert required in auth

    for outcome in (
        'accessText("oauth.unavailable", "OAuth chưa được cấu hình trên server.")',
        'accessText("oauth.cancelled", "Bạn đã hủy xác minh tại nhà cung cấp.")',
        'accessText("oauth.failed", "Không thể xác minh OAuth. Hãy thử lại mà không chia sẻ mã hay token với bất kỳ ai.")',
        'accessText("oauth.state", "Phiên OAuth không hợp lệ hoặc đã hết hạn. Hãy bắt đầu lại từ Web App.")',
        'accessText("oauth.session", "Signed session đã thay đổi trong khi liên kết OAuth. Hãy đăng nhập lại rồi thử lại.")',
        'accessText("oauth.linkRequired", "Email này đã có tài khoản Web. Hãy đăng nhập bằng phương thức hiện có, sau đó liên kết OAuth trong trang Tài khoản.")',
        'accessText("oauth.linked", "Đã liên kết OAuth với signed session hiện tại.")',
        'accessText("oauth.alreadyLinked", "OAuth này đã liên kết với tài khoản hiện tại.")',
    ):
        assert outcome in auth

    lowered_auth = auth.lower()
    for forbidden in (
        "fetch(",
        "api(",
        "localstorage.getitem",
        "localstorage.setitem",
        "localstorage.removeitem",
        "localstorage.clear",
        "sessionstorage.getitem",
        "sessionstorage.setitem",
        "sessionstorage.removeitem",
        "sessionstorage.clear",
        "telegram_id",
        "wallet",
        "payos",
    ):
        assert forbidden not in lowered_auth


def test_recovery_route_and_server_title_stay_allowlisted() -> None:
    assert 'action: "auth-login"' in _page_definition("/login")
    assert 'action: "auth-register"' in _page_definition("/register")
    recovery = _page_definition("/password-recovery")
    assert 'action: "auth-password-recovery-start"' in recovery
    assert 'actionLabelKey: "access.action.recovery"' in recovery
    assert '"/password-recovery": {"vi": "Khôi phục mật khẩu · TOAN AAS", "en": "Password recovery · TOAN AAS", "zh": "找回密码 · TOAN AAS"}' in PAGES


def test_password_recovery_shell_is_publicly_renderable_in_english() -> None:
    response = render_portal("/password-recovery", interface_locale="en")

    assert response.status_code == 200
    assert b"<title>Password recovery \xc2\xb7 TOAN AAS</title>" in response.body


def test_public_auth_continuations_carry_only_the_reviewed_interface_locale() -> None:
    registration = _between(INTEGRATION, 'if (action === "auth-register")', 'if (action === "auth-password-recovery-start")')
    registration_locale = _between(INTEGRATION, "function publicAuthInterfaceLocale", "function telegramChallengePending")

    assert "function publicAuthInterfaceLocale()" in INTEGRATION
    assert 'const locale = String(base().interfaceLocale || "").trim().toLowerCase();' in registration_locale
    assert "window.location.search" not in registration_locale
    assert 'return INTERFACE_LOCALES.has(locale) ? locale : "vi";' in registration_locale
    assert "window.location.assign(`/login?registered=1&lang=${publicAuthInterfaceLocale()}`);" in registration
    assert "function publicOAuthStartPath" in PORTAL
    oauth = _between(PORTAL, "function publicOAuthStartPath", "function renderPublicOAuthCard")
    assert 'reviewedInterfaceLocale(context && context.interfaceLocale) || "vi"' in oauth
    assert 'new URLSearchParams({ next: `${returnPath}${separator}lang=${locale}` })' in oauth
