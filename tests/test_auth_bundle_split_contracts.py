import re
import json
from pathlib import Path

import copyfast_pages
from copyfast_pages import render_portal


ROOT = Path(__file__).resolve().parents[1]
AUTH_ENTRY = ROOT / "static" / "portal" / "portal-auth.js"
FULL_SCRIPTS = {
    "/static/portal/portal-i18n.js",
    "/static/portal/portal-motion.js",
    "/static/portal/admin-customer-directory.js",
    "/static/portal/portal.js",
    "/static/portal/integration.js",
}


def _scripts(path: str) -> set[str]:
    html = render_portal(path).body.decode("utf-8")
    return set(re.findall(r'<script[^>]+src="([^"?]+)', html))


def test_public_auth_uses_only_small_route_specific_javascript():
    expected = {"/static/portal/portal-theme.js", "/static/portal/portal-auth.js"}
    for route in ("/login", "/register"):
        assert _scripts(route) == expected


def test_dashboard_keeps_the_full_workspace_bundle():
    scripts = _scripts("/dashboard")
    assert "/static/portal/portal-theme.js" in scripts
    assert FULL_SCRIPTS <= scripts
    assert "/static/portal/portal-auth.js" not in scripts


def test_public_auth_split_also_applies_to_the_fallback_template(monkeypatch):
    monkeypatch.setattr(copyfast_pages, "TEMPLATE", ROOT / "templates" / "missing.html")
    expected = {"/static/portal/portal-theme.js", "/static/portal/portal-auth.js"}
    assert _scripts("/login") == expected


def test_auth_entrypoint_is_small_and_has_a_closed_public_auth_surface():
    source = AUTH_ENTRY.read_text(encoding="utf-8")
    assert len(source.splitlines()) <= 500
    for forbidden in (
        "/catalog", "/core/status", "/auth/me", "localStorage",
        "sessionStorage", "telegram_id", "telegramId",
    ):
        assert forbidden not in source
    for required in (
        "/auth/providers", "/auth/telegram/connection/status",
        "/auth/login", "/auth/register", "/auth/telegram/login/start",
        "/auth/telegram/login/status", "/auth/telegram/login/complete",
    ):
        assert required in source


def test_auth_entrypoint_owns_its_visible_pwa_install_trigger():
    source = AUTH_ENTRY.read_text(encoding="utf-8")
    assert 'window.addEventListener("beforeinstallprompt"' in source
    assert "await prompt.prompt()" in source
    assert "control.hidden = false" in source


def test_auth_submit_clears_password_values_from_the_dom():
    source = AUTH_ENTRY.read_text(encoding="utf-8")
    assert "form.querySelectorAll('input[type=\"password\"], input[data-auth-secret]')" in source
    assert 'input.value = ""' in source


def test_auth_entrypoint_preserves_effective_i18n_copy():
    source = AUTH_ENTRY.read_text(encoding="utf-8")
    expected = {
        "vi": [
            "Tạo tài khoản trước. Chỉ liên kết Telegram khi bạn muốn đồng bộ dữ liệu từ Bot.",
            "Mỗi thao tác quan trọng đều có trạng thái dễ hiểu.", "Bạn luôn có đường quay lại hỗ trợ khi cần.",
            "Tên bạn muốn dùng", "Lợi ích của không gian làm việc", "Chọn phương thức truy cập", "Bắt buộc",
        ],
        "en": [
            "Sign in to continue to your Workspace. Telegram and OAuth are separate options that open only when you need them.",
            "Create an independent Web account first. Link Telegram only when you need canonical data from the Bot.",
            "Every important action has a clear status.", "Help is always available when you need it.",
            "The name you want to use", "Workspace benefits", "Choose an access method", "Required",
            "If the email you just submitted did not yet have an account, a profile has been created. Sign in to start a signed session and use the Web Workspace; you can link Telegram later if Bot synchronization is needed.",
        ],
        "zh": [
            "登录后继续使用工作空间。Telegram 和 OAuth 是独立选项，仅在您需要时启用。",
            "请先创建独立的 Web 账户。只有在需要 Bot 的规范数据时才链接 Telegram。",
            "每项重要操作都有清晰的状态。", "需要时，您始终可以获得帮助。", "您想使用的名称",
            "工作空间优势", "选择访问方式", "必填",
            "如果您刚提交的邮箱尚未拥有账户，系统已创建资料。请登录以创建已签名会话并使用 Web 工作空间；如需同步 Bot，您可以稍后链接 Telegram。",
        ],
    }
    for values in expected.values():
        for value in values:
            assert json.dumps(value, ensure_ascii=False) in source


def test_auth_oauth_query_messages_are_localized():
    source = AUTH_ENTRY.read_text(encoding="utf-8")
    assert "oauthCancelled" in source and "oauthFailed" in source and "oauthLinkRequired" in source
    assert 'const messages = { cancelled: text.oauthCancelled' in source


def test_direct_telegram_login_copy_is_localized():
    source = AUTH_ENTRY.read_text(encoding="utf-8")
    expected = {
        "vi": ("Tạo mã bảo mật và mở Bot Telegram @toanaasbot", "Đăng nhập với Telegram Bot"),
        "en": ("Create a secure code and open the Telegram Bot @toanaasbot", "Sign in with Telegram Bot"),
        "zh": ("创建安全代码并打开 Telegram Bot @toanaasbot", "使用 Telegram Bot 登录"),
    }
    for values in expected.values():
        for value in values:
            assert json.dumps(value, ensure_ascii=False) in source
    assert 'title="${safe(text.telegramButtonTitle)}"' in source
    assert "<span>${safe(text.telegramButtonLabel)}</span>" in source


def test_pwa_trigger_stays_visible_and_has_a_localized_fallback():
    source = AUTH_ENTRY.read_text(encoding="utf-8")
    button = re.search(r'<button type=\\?"button\\?"[^>]+data-portal-action=\\?"pwa-install-prompt\\?"[^>]*>', source)
    assert button
    assert " hidden" not in button.group(0)
    assert " disabled" not in button.group(0)
    assert "aria-hidden" not in button.group(0)
    assert "pwaFallback" in source
    assert "toast(text.pwaFallback)" in source
