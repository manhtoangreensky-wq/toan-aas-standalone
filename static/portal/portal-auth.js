/* Lightweight public Auth entrypoint. Server endpoints remain the only session authority. */
(() => {
  "use strict";

  const API = "/api/v1";
  const AUTH_ROUTES = new Set(["/login", "/register"]);
  const LOCALES = new Set(["vi", "en", "zh"]);
  const POLL_MS = 2500;
  const MAX_POLL_MS = 10000;
  const MAX_CHALLENGE_MINUTES = 30;
  let bootstrap = {};
  try {
    const node = document.getElementById("portal-bootstrap");
    const parsed = node && JSON.parse(node.textContent || "{}");
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) bootstrap = parsed;
  } catch (_) { bootstrap = {}; }

  const path = AUTH_ROUTES.has(bootstrap.path) ? bootstrap.path : "";
  if (!path) return;
  const locale = LOCALES.has(bootstrap.interfaceLocale) ? bootstrap.interfaceLocale : "vi";
  const text = {
    vi: {
      brand: "Không gian AI", back: "Giới thiệu", language: "Ngôn ngữ giao diện",
      login: "Đăng nhập", register: "Tạo tài khoản", loginHeading: "Chào mừng trở lại",
      registerHeading: "Tạo không gian làm việc của bạn",
      loginIntro: "Đăng nhập để tiếp tục vào không gian làm việc.",
      registerIntro: "Tạo tài khoản trước. Chỉ liên kết Telegram khi bạn muốn đồng bộ dữ liệu từ Bot.",
      contextLabel: "Lợi ích của không gian làm việc", context: "Không gian làm việc", loginContext: "Mọi việc bắt đầu từ một không gian rõ ràng.",
      registerContext: "Tạo không gian làm việc cho quy trình của bạn.",
      pointOne: "Dự án, tài sản và tiến độ được tổ chức cùng nhau.",
      pointTwo: "Mỗi thao tác quan trọng đều có trạng thái dễ hiểu.",
      pointThree: "Bạn luôn có đường quay lại hỗ trợ khi cần.",
      name: "Tên hiển thị", namePlaceholder: "Tên bạn muốn dùng", email: "Email (có thể dùng Gmail)",
      password: "Mật khẩu", passwordPlaceholder: "Nhập mật khẩu", passwordMin: "Tối thiểu 12 ký tự",
      confirm: "Xác nhận mật khẩu", confirmPlaceholder: "Nhập lại mật khẩu", show: "Hiện", hide: "Ẩn",
      forgot: "Quên mật khẩu?", theme: "Giao diện", switchLabel: "Chọn phương thức truy cập", required: "Bắt buộc",
      install: "Tải & Cài đặt App TOAN AAS", pwaFallback: "Hãy dùng menu trình duyệt để cài ứng dụng.",
      registeredTitle: "Tiếp tục bằng đăng nhập",
      registeredBody: "Nếu email chưa có tài khoản, hồ sơ đã được tạo. Hãy đăng nhập để tiếp tục; bạn có thể liên kết Telegram sau.",
      oauthCancelled: "Bạn đã hủy xác minh tại nhà cung cấp.",
      oauthFailed: "Không thể xác minh OAuth. Hãy thử lại mà không chia sẻ mã hay token với bất kỳ ai.",
      oauthState: "Phiên OAuth không hợp lệ hoặc đã hết hạn. Hãy bắt đầu lại từ Web App.",
      oauthSession: "Signed session đã thay đổi trong khi liên kết OAuth. Hãy đăng nhập lại rồi thử lại.",
      oauthLinkRequired: "Email này đã có tài khoản Web. Hãy đăng nhập bằng phương thức hiện có, sau đó liên kết OAuth trong trang Tài khoản.",
      mismatch: "Xác nhận mật khẩu chưa khớp.", genericError: "Yêu cầu chưa được máy chủ xác nhận.",
      telegramButtonTitle: "Tạo mã bảo mật và mở Bot Telegram @toanaasbot", telegramButtonLabel: "Đăng nhập với Telegram Bot",
      telegramUnavailable: "Đăng nhập Telegram hiện chưa sẵn sàng.",
      telegramPending: "Mã đăng nhập Telegram đang được tạo. Vui lòng chờ phản hồi.",
      telegramWaiting: "Đang chờ Telegram xác minh mã trong Bot.", mfaTitle: "Mật khẩu đã được xác minh",
      mfaBody: "Nhập mã 6 số từ ứng dụng xác thực, hoặc một mã khôi phục.",
      mfaCode: "Mã xác thực hoặc mã khôi phục", mfaSubmit: "Xác thực & đăng nhập", mfaCancel: "Hủy và đăng nhập lại"
    },
    en: {
      brand: "AI workspace", back: "Overview", language: "Interface language", login: "Sign in",
      register: "Create account", loginHeading: "Welcome back", registerHeading: "Create your Workspace",
      loginIntro: "Sign in to continue to your Workspace. Telegram and OAuth are separate options that open only when you need them.",
      registerIntro: "Create an independent Web account first. Link Telegram only when you need canonical data from the Bot.",
      contextLabel: "Workspace benefits", context: "TOAN AAS Workspace", loginContext: "Every task starts in a clear workspace.", registerContext: "Create a workspace for your workflow.",
      pointOne: "Projects, assets and progress stay organized together.", pointTwo: "Every important action has a clear status.",
      pointThree: "Help is always available when you need it.", name: "Display name", namePlaceholder: "The name you want to use",
      email: "Email (Gmail is supported)", password: "Password", passwordPlaceholder: "Enter password", passwordMin: "At least 12 characters",
      confirm: "Confirm password", confirmPlaceholder: "Re-enter password", show: "Show", hide: "Hide", forgot: "Forgot password?",
      theme: "Theme", switchLabel: "Choose an access method", required: "Required", install: "Install TOAN AAS App",
      pwaFallback: "Use your browser menu to install the app.", registeredTitle: "Continue by signing in",
      registeredBody: "If the email you just submitted did not yet have an account, a profile has been created. Sign in to start a signed session and use the Web Workspace; you can link Telegram later if Bot synchronization is needed.",
      oauthCancelled: "You cancelled verification with the provider.",
      oauthFailed: "OAuth could not be verified. Try again without sharing a code or token with anyone.",
      oauthState: "The OAuth session is invalid or has expired. Start again from the Web App.",
      oauthSession: "The signed session changed while OAuth was being linked. Sign in again and try again.",
      oauthLinkRequired: "This email already has a Web account. Sign in with the existing method, then link OAuth from Account.",
      mismatch: "Password confirmation does not match.", genericError: "The server has not confirmed this request.",
      telegramButtonTitle: "Create a secure code and open the Telegram Bot @toanaasbot", telegramButtonLabel: "Sign in with Telegram Bot",
      telegramUnavailable: "Telegram sign-in is not ready.", telegramPending: "A Telegram sign-in code is being created.",
      telegramWaiting: "Waiting for Telegram verification in the Bot.", mfaTitle: "Password verified",
      mfaBody: "Enter the six-digit authenticator code or a recovery code.", mfaCode: "Authenticator or recovery code",
      mfaSubmit: "Verify and sign in", mfaCancel: "Cancel and sign in again"
    },
    zh: {
      brand: "AI 工作空间", back: "产品介绍", language: "界面语言", login: "登录", register: "创建账户",
      loginHeading: "欢迎回来", registerHeading: "创建您的工作空间", loginIntro: "登录后继续使用工作空间。Telegram 和 OAuth 是独立选项，仅在您需要时启用。",
      registerIntro: "请先创建独立的 Web 账户。只有在需要 Bot 的规范数据时才链接 Telegram。",
      contextLabel: "工作空间优势", context: "TOAN AAS 工作空间",
      loginContext: "每项工作都从清晰的工作空间开始。", registerContext: "为您的工作流程创建工作空间。",
      pointOne: "项目、资产和进度会集中有序地管理。", pointTwo: "每项重要操作都有清晰的状态。", pointThree: "需要时，您始终可以获得帮助。",
      name: "显示名称", namePlaceholder: "您想使用的名称", email: "邮箱（支持 Gmail）", password: "密码", passwordPlaceholder: "输入密码",
      passwordMin: "至少 12 个字符", confirm: "确认密码", confirmPlaceholder: "再次输入密码", show: "显示", hide: "隐藏",
      forgot: "忘记密码？", theme: "主题", switchLabel: "选择访问方式", required: "必填", install: "安装 TOAN AAS App",
      pwaFallback: "请使用浏览器菜单安装应用。", registeredTitle: "请继续登录",
      registeredBody: "如果您刚提交的邮箱尚未拥有账户，系统已创建资料。请登录以创建已签名会话并使用 Web 工作空间；如需同步 Bot，您可以稍后链接 Telegram。",
      oauthCancelled: "您已取消在提供方处的验证。",
      oauthFailed: "无法验证 OAuth。请重试，并且不要向任何人分享代码或令牌。",
      oauthState: "OAuth 会话无效或已过期。请从 Web App 重新开始。",
      oauthSession: "链接 OAuth 时已签名会话发生变化。请重新登录后再试。",
      oauthLinkRequired: "此邮箱已有 Web 账户。请使用现有方式登录，然后在“账户”页面链接 OAuth。", mismatch: "两次输入的密码不一致。",
      genericError: "服务器尚未确认此请求。",
      telegramButtonTitle: "创建安全代码并打开 Telegram Bot @toanaasbot", telegramButtonLabel: "使用 Telegram Bot 登录",
      telegramUnavailable: "Telegram 登录尚未就绪。",
      telegramPending: "正在创建 Telegram 登录码。", telegramWaiting: "正在等待 Bot 中的 Telegram 验证。",
      mfaTitle: "密码已验证", mfaBody: "请输入六位身份验证器代码或恢复代码。", mfaCode: "身份验证器或恢复代码",
      mfaSubmit: "验证并登录", mfaCancel: "取消并重新登录"
    }
  }[locale];
  const state = { providers: {}, connection: {}, telegram: {}, mfa: null, pollTimer: 0, pollFailures: 0, pollDeadline: 0 };
  let pwaInstallPrompt = null;

  function safe(value) {
    return typeof value === "string" ? value.replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char])) : "";
  }

  function randomKey() {
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    return `web-${Array.from(bytes, (item) => item.toString(16).padStart(2, "0")).join("")}`;
  }

  function safeReturnPath(value) {
    if (typeof value !== "string") return "";
    const route = value.trim();
    if (!route.startsWith("/") || route.startsWith("//") || route.includes("\\") || route.includes("?") || route.includes("#")) return "";
    const normalized = route.replace(/\/+$/, "") || "/";
    return ["/login", "/register", "/password-recovery", "/onboarding"].includes(normalized) ? "" : normalized;
  }

  function nextRoute() { return safeReturnPath(new URLSearchParams(window.location.search).get("next") || ""); }

  function safeTelegramLink(value) {
    if (typeof value !== "string" || !value) return "";
    try {
      const url = new URL(value);
      return url.protocol === "https:" && url.hostname === "t.me" && !url.port && !url.username && !url.password ? url.href : "";
    } catch (_) { return ""; }
  }

  function toast(message, type) {
    const region = document.querySelector("[data-portal-toast]");
    if (!region || !message) return;
    const node = document.createElement("div");
    node.className = `portal-toast${type === "error" ? " portal-toast--warning" : ""}`;
    node.textContent = message;
    region.appendChild(node);
    window.setTimeout(() => node.remove(), 6500);
  }

  async function api(endpoint, options) {
    const headers = new Headers((options && options.headers) || {});
    headers.set("Accept", "application/json");
    headers.set("X-Request-ID", randomKey());
    const response = await fetch(`${API}${endpoint}`, { credentials: "same-origin", cache: "no-store", ...options, headers });
    let payload = {};
    try { payload = await response.json(); } catch (_) { payload = {}; }
    if (!response.ok || payload.ok !== true) {
      const error = new Error(payload.message || text.genericError);
      error.payload = payload;
      throw error;
    }
    return payload;
  }

  async function publicData(endpoint) {
    try {
      const response = await fetch(`${API}${endpoint}`, { credentials: "same-origin", cache: "no-store", headers: { Accept: "application/json" } });
      const payload = await response.json();
      return response.ok && payload && payload.data && typeof payload.data === "object" ? payload.data : {};
    } catch (_) { return {}; }
  }

  function localeHref(code) {
    const params = new URLSearchParams(window.location.search || "");
    params.set("lang", code);
    return `${path}?${params.toString()}`;
  }

  function icon(paths) { return `<svg class="portal-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${paths}</svg>`; }
  function brandMark() { return '<img class="portal-brand-mark-image" src="/static/logo_ch%C3%ADnh_th%E1%BB%A9c.png" alt="" width="56" height="56" decoding="async">'; }
  function themeToggle() { return `<button class="portal-theme-toggle" type="button" data-portal-theme-toggle aria-label="${safe(text.theme)}" title="${safe(text.theme)}"><span class="portal-theme-toggle-icon" data-portal-theme-icon aria-hidden="true"></span><span class="portal-theme-toggle-label" data-portal-theme-label>${safe(text.theme)}</span></button>`; }

  function field(name, label, type, placeholder, autocomplete, required, minLength, maxLength) {
    const id = `portal-field-${name}`;
    const requiredMarkup = required ? `<span class="portal-required-mark" data-portal-required-mark aria-hidden="true">*</span><span class="portal-sr-only" data-portal-required-message> ${safe(text.required)}</span>` : "";
    const input = `<input class="portal-input" id="${id}" name="${name}" type="${type}" placeholder="${safe(placeholder)}" autocomplete="${autocomplete}"${type === "password" ? " data-auth-secret" : ""}${required ? " required aria-required=\"true\"" : ""}${minLength ? ` minlength="${minLength}"` : ""} maxlength="${maxLength}">`;
    const control = type === "password" ? `<span class="portal-password-control">${input}<button class="portal-password-toggle" type="button" aria-controls="${id}" aria-label="${safe(text.show)}" aria-pressed="false" data-portal-toggle-password><span data-portal-password-toggle-label>${safe(text.show)}</span></button></span>` : input;
    return `<div class="portal-field"><label for="${id}">${safe(label)}${requiredMarkup}</label>${control}</div>`;
  }

  function primaryForm() {
    if (state.mfa) {
      return `<div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">✓</span><div><strong>${safe(text.mfaTitle)}</strong><p>${safe(text.mfaBody)}</p></div></div><form class="portal-form" data-portal-form data-portal-action="auth-mfa-login" data-portal-route="/login" novalidate><div class="portal-fields">${field("code", text.mfaCode, "text", "123456 / ABCD-EFGH", "one-time-code", true, 0, 16)}</div><div class="portal-form-footer"><button class="portal-button portal-button--primary" type="submit">${safe(text.mfaSubmit)}</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="auth-mfa-login-cancel">${safe(text.mfaCancel)}</button></div></form>`;
    }
    const fields = path === "/login"
      ? field("email", text.email, "email", "you@example.com", "email", true, 0, 254) + field("password", text.password, "password", text.passwordPlaceholder, "current-password", true, 0, 256)
      : field("name", text.name, "text", text.namePlaceholder, "name", false, 0, 120) + field("email", text.email, "email", "you@example.com", "email", true, 0, 254) + field("password", text.password, "password", text.passwordMin, "new-password", true, 12, 256) + field("confirm_password", text.confirm, "password", text.confirmPlaceholder, "new-password", true, 12, 256);
    const forgot = path === "/login" ? `<a class="portal-auth-forgot-link" href="/password-recovery?lang=${locale}">${safe(text.forgot)}</a>` : "";
    return `<form class="portal-form portal-auth-compact-form" data-portal-form data-portal-action="${path === "/login" ? "auth-login" : "auth-register"}" data-portal-route="${path}" novalidate><div class="portal-fields">${fields}</div><div class="portal-auth-form-actions">${forgot}<button class="portal-button portal-button--primary portal-auth-submit-btn" type="submit">${safe(path === "/login" ? text.login : text.register)}</button></div></form>`;
  }

  function socialLogin() {
    const googleEnabled = state.providers.google && state.providers.google.enabled === true;
    const appleEnabled = state.providers.apple && state.providers.apple.enabled === true;
    const google = googleEnabled ? `
          <a class="portal-btn-direct-social google" href="/api/v1/auth/oauth/google/start?next=/dashboard" title="Đăng nhập bằng Google">
            <svg viewBox="0 0 24 24" width="18" height="18"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/></svg>
            <span>Google</span>
          </a>` : "";
    const apple = appleEnabled ? `
          <a class="portal-btn-direct-social apple" href="/api/v1/auth/oauth/apple/start?next=/dashboard" title="Đăng nhập bằng Apple ID">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M15.97 6.38c.62-.75 1.04-1.8 0.92-2.88-.9.04-1.99.6-2.63 1.35-.57.65-1.07 1.72-.94 2.76 1 .08 2.03-.49 2.65-1.23"/></svg>
            <span>Apple</span>
          </a>` : "";
    const pair = google || apple ? `
        <div class="portal-social-pair">${google}${apple}
        </div>` : "";
    return `
      <div class="portal-direct-social-auth">
        <button type="button" class="portal-btn-direct-social telegram" data-portal-action="start-telegram-login" data-portal-route="/login" title="${safe(text.telegramButtonTitle)}">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="m20.665 3.717-17.73 6.837c-1.21.486-1.203 1.161-.222 1.462l4.552 1.42 10.532-6.645c.498-.303.953-.14.579.192l-8.533 7.701h-.002l-.313 4.674c.458 0 .66-.21.916-.458l2.199-2.138 4.573 3.378c.843.464 1.448.225 1.658-.783l3-14.137c.308-1.234-.471-1.794-1.289-1.423z"/></svg>
          <span>${safe(text.telegramButtonLabel)}</span>
        </button>${pair}
      </div>
    `;
  }

  function queryNotice() {
    const params = new URLSearchParams(window.location.search || "");
    if (path === "/login" && params.get("registered") === "1") return `<div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>${safe(text.registeredTitle)}</strong><p>${safe(text.registeredBody)}</p></div></div>`;
    const reason = params.get("oauth") || "";
    const messages = { cancelled: text.oauthCancelled, failed: text.oauthFailed, state: text.oauthState, session: text.oauthSession, "link-required": text.oauthLinkRequired };
    return reason && messages[reason] ? `<div class="portal-notice"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>OAuth</strong><p>${safe(messages[reason])}</p></div></div>` : "";
  }

  function render(options = {}) {
    const main = document.getElementById("portal-main") || document.getElementById("portal-root");
    if (!main) return;
    if (main.hasAttribute("data-auth-motion-phase")) {
      main.setAttribute("data-auth-motion-phase", "settled");
      const card = main.querySelector(".portal-auth-card");
      if (card) {
        const primary = card.querySelector(".portal-auth-primary");
        if (primary && options.primary === true) primary.innerHTML = primaryForm();
        const oldSocial = card.querySelector(".portal-direct-social-auth");
        if (state.mfa) {
          if (oldSocial) oldSocial.remove();
        } else {
          const temp = document.createElement("div");
          temp.innerHTML = socialLogin();
          const newSocial = temp.firstElementChild;
          if (oldSocial) {
            if (newSocial) card.replaceChild(newSocial, oldSocial);
            else oldSocial.remove();
          } else if (newSocial) {
            card.appendChild(newSocial);
          }
        }
      }
      return;
    }
    main.setAttribute("data-auth-motion-mounted", "true");
    main.setAttribute("data-auth-motion-phase", "entry");
    const shell = document.querySelector("[data-portal-shell]");
    const sidebar = document.querySelector("[data-portal-sidebar]");
    const header = document.querySelector("[data-portal-header]");
    const mobile = document.querySelector("[data-portal-mobile-nav]");
    if (shell) shell.classList.add("portal-shell--auth");
    document.body.classList.add("portal-body--auth");
    if (sidebar) sidebar.hidden = true;
    if (header) header.hidden = true;
    if (mobile) mobile.hidden = true;
    main.dataset.portalMotionSkipEnter = "true";
    const isLogin = path === "/login";
    const localeMarkup = [["vi", "Tiếng Việt"], ["en", "English"], ["zh", "中文"]].map(([code, label]) => `<a class="portal-auth-locale-link" href="${safe(localeHref(code))}"${locale === code ? ' aria-current="true"' : ""}>${label}</a>`).join("");
    const contextMarkup = `<aside class="portal-auth-context" aria-label="${safe(text.contextLabel)}"><div class="portal-auth-context-head"><span class="portal-auth-context-icon" aria-hidden="true">${icon('<path d="M12 3.5 19 6v5.8c0 4.4-2.9 7.6-7 8.7-4.1-1.1-7-4.3-7-8.7V6z"/><path d="m9 12 2 2 4-4"/>')}</span><strong class="portal-auth-context-kicker">${safe(text.context)}</strong></div><p class="portal-auth-context-title">${safe(isLogin ? text.loginContext : text.registerContext)}</p><ul class="portal-auth-context-list"><li><span class="portal-auth-feat-check">✓</span><span>${safe(text.pointOne)}</span></li><li><span class="portal-auth-feat-check">✓</span><span>${safe(text.pointTwo)}</span></li><li><span class="portal-auth-feat-check">✓</span><span>${safe(text.pointThree)}</span></li></ul><div style="margin-top: 20px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.08);"><button type="button" class="portal-button portal-button--primary" data-portal-action="pwa-install-prompt" style="width:100%; display:inline-flex; align-items:center; justify-content:center; gap:8px; font-weight:700; border-radius:10px;"><span>📲</span><span>${safe(text.install)}</span></button></div></aside>`;
    const authSwitch = `<nav class="portal-auth-switch" aria-label="${safe(text.switchLabel)}"><a href="/login?lang=${locale}"${isLogin ? ' aria-current="page"' : ""}>${safe(text.login)}</a><a href="/register?lang=${locale}"${!isLogin ? ' aria-current="page"' : ""}>${safe(text.register)}</a></nav>`;
    main.innerHTML = `<article class="portal-auth-page portal-auth-page--access"><header class="portal-auth-header"><div class="portal-auth-brand"><span class="portal-brand-mark" aria-hidden="true">${brandMark()}</span><span><strong>TOAN AAS</strong><small>${safe(text.brand)}</small></span></div><nav class="portal-auth-locale-nav" aria-label="${safe(text.language)}">${localeMarkup}</nav><div class="portal-auth-header-actions">${themeToggle()}<a class="portal-auth-back" href="/welcome?lang=${locale}" aria-label="${safe(text.back)}"><span class="portal-auth-back-label">${safe(text.back)}</span><span aria-hidden="true">${icon('<path d="M5 12h14M13 6l6 6-6 6"/>')}</span></a></div></header><div class="portal-auth-shell"><section class="portal-auth-intro"><h1 class="portal-title">${safe(isLogin ? text.loginHeading : text.registerHeading)}</h1><p class="portal-description">${safe(isLogin ? text.loginIntro : text.registerIntro)}</p>${contextMarkup}</section><section class="portal-card portal-card-pad portal-auth-card"><div class="portal-auth-card-top">${authSwitch}</div>${queryNotice()}<div class="portal-auth-primary">${primaryForm()}</div>${state.mfa ? "" : socialLogin()}</section></div><footer class="portal-auth-footer" hidden><div class="portal-auth-footer-grid"></div></footer></article>`;
    const theme = window.TOANAASPortalTheme;
    if (theme && typeof theme.syncControls === "function") theme.syncControls();
    syncPwaInstallControl();
  }

  function setBusy(control, busy) {
    if (!control) return;
    control.disabled = busy;
    control.setAttribute("aria-busy", busy ? "true" : "false");
  }

  function syncPwaInstallControl() {
    const control = document.querySelector('[data-portal-action="pwa-install-prompt"]');
    if (!control) return;
    control.hidden = false;
    control.disabled = false;
    control.removeAttribute("aria-hidden");
  }

  async function requestPwaInstall(control) {
    const prompt = pwaInstallPrompt;
    if (!prompt || typeof prompt.prompt !== "function") {
      toast(text.pwaFallback);
      return;
    }
    setBusy(control, true);
    try {
      await prompt.prompt();
      if (prompt.userChoice && typeof prompt.userChoice.then === "function") await prompt.userChoice;
    } finally {
      pwaInstallPrompt = null;
      setBusy(control, false);
      syncPwaInstallControl();
    }
  }

  function validMfa(data) {
    const challengeId = String((data && data.challenge_id) || "").trim().toLowerCase();
    const token = String((data && data.challenge_token) || "").trim();
    const minutes = Number(data && data.expires_in_minutes);
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(challengeId) && /^[A-Za-z0-9_-]{32,160}$/.test(token) && Number.isInteger(minutes) && minutes >= 1 && minutes <= 10 ? { challenge_id: challengeId, challenge_token: token } : null;
  }

  async function submitAuth(form) {
    if (!form.reportValidity()) return;
    const values = Object.fromEntries(new FormData(form).entries());
    const button = form.querySelector('button[type="submit"]');
    setBusy(button, true);
    try {
      if (form.dataset.portalAction === "auth-register") {
        if (values.password !== values.confirm_password) throw new Error(text.mismatch);
        const result = await api("/auth/register", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: values.email || "", password: values.password || "", display_name: values.name || "" }) });
        toast(result.message);
        window.location.assign(`/login?registered=1&lang=${locale}`);
      } else if (form.dataset.portalAction === "auth-mfa-login") {
        const code = String(values.code || "").trim().toUpperCase();
        if (!state.mfa || !/^(?:[0-9]{6}|[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4})$/.test(code)) throw new Error(text.genericError);
        const result = await api("/auth/login/mfa", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...state.mfa, code }) });
        state.mfa = null;
        toast(result.message);
        window.location.assign(nextRoute() || "/dashboard");
      } else {
        const result = await api("/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: values.email || "", password: values.password || "", admin_portal: false }) });
        if (result.data && result.data.mfa_required === true) {
          state.mfa = validMfa(result.data);
          if (!state.mfa) throw new Error(text.genericError);
          toast(result.message);
          render({ primary: true });
        } else {
          toast(result.message);
          window.location.assign(nextRoute() || "/dashboard");
        }
      }
    } catch (error) { toast(error instanceof Error ? error.message : text.genericError, "error"); }
    finally {
      values.password = "";
      values.confirm_password = "";
      form.querySelectorAll('input[type="password"], input[data-auth-secret]').forEach((input) => { input.value = ""; });
      setBusy(button, false);
    }
  }

  function stopPolling() {
    if (state.pollTimer) window.clearTimeout(state.pollTimer);
    state.pollTimer = 0;
    state.pollFailures = 0;
    state.pollDeadline = 0;
  }

  function challengePending() {
    const flow = state.telegram || {};
    const data = flow.data && typeof flow.data === "object" ? flow.data : {};
    return flow.status === "awaiting_confirm" && ((typeof data.code === "string" && /^[A-Za-z0-9_-]{12,160}$/.test(data.code)) || data.recovered === true);
  }

  function schedulePolling(delay) {
    if (!challengePending() || document.visibilityState === "hidden" || state.pollTimer) return;
    const minutes = Math.max(1, Math.min(MAX_CHALLENGE_MINUTES, Math.floor(Number(state.telegram.data && state.telegram.data.expires_in_minutes) || 10)));
    if (!state.pollDeadline) state.pollDeadline = Date.now() + minutes * 60000;
    if (Date.now() >= state.pollDeadline) return;
    state.pollTimer = window.setTimeout(async () => {
      state.pollTimer = 0;
      try { const complete = await refreshTelegram(true); state.pollFailures = 0; if (!complete) schedulePolling(); }
      catch (_) { state.pollFailures += 1; schedulePolling(Math.min(MAX_POLL_MS, POLL_MS * (2 ** Math.min(state.pollFailures, 2)))); }
    }, Number.isFinite(Number(delay)) ? Math.max(0, Number(delay)) : POLL_MS);
  }

  async function completeTelegram() {
    stopPolling();
    const result = await api("/auth/telegram/login/complete", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    toast(result.message);
    window.location.assign(nextRoute() || "/dashboard");
    return true;
  }

  async function refreshTelegram(silent) {
    const result = await api("/auth/telegram/login/status");
    const previous = state.telegram && state.telegram.data && typeof state.telegram.data === "object" ? state.telegram.data : {};
    state.telegram = { status: result.status || "awaiting_confirm", message: result.message, errorCode: result.error_code || "", data: { ...previous, ...(result.data || {}) } };
    if (result.data && result.data.ready === true) return completeTelegram();
    if (!silent) toast(result.message || text.telegramWaiting);
    return false;
  }

  async function resumeTelegram() {
    try {
      const result = await api("/auth/telegram/login/status");
      state.telegram = { status: result.status || "awaiting_confirm", message: result.message, errorCode: result.error_code || "", data: { ...(result.data || {}), recovered: true } };
      if (result.data && result.data.ready === true) return completeTelegram();
      schedulePolling();
    } catch (error) {
      const code = String(error && error.payload && error.payload.error_code || "");
      if (!["TELEGRAM_LOGIN_CHALLENGE_REQUIRED", "TELEGRAM_LOGIN_EXPIRED"].includes(code)) throw error;
      if (code === "TELEGRAM_LOGIN_EXPIRED") toast(error.message, "error");
    }
    return false;
  }

  async function startTelegram(control) {
    if (!(state.connection && state.connection.ready === true)) return toast(text.telegramUnavailable, "error");
    setBusy(control, true);
    try {
      stopPolling();
      const result = await api("/auth/telegram/login/start", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      state.telegram = { status: result.status || "awaiting_confirm", message: result.message, errorCode: result.error_code || "", data: result.data || {} };
      const deepLink = safeTelegramLink(result.data && result.data.deep_link);
      if (deepLink) window.open(deepLink, "_blank");
      toast(result.message || text.telegramWaiting);
      schedulePolling();
    } catch (error) { toast(error instanceof Error ? error.message : text.genericError, "error"); }
    finally { setBusy(control, false); }
  }

  document.addEventListener("click", (event) => {
    const toggle = event.target.closest && event.target.closest("[data-portal-toggle-password]");
    if (toggle) {
      const input = document.getElementById(toggle.getAttribute("aria-controls"));
      if (!input) return;
      const reveal = input.type === "password";
      input.type = reveal ? "text" : "password";
      toggle.setAttribute("aria-pressed", reveal ? "true" : "false");
      toggle.setAttribute("aria-label", reveal ? text.hide : text.show);
      const label = toggle.querySelector("[data-portal-password-toggle-label]");
      if (label) label.textContent = reveal ? text.hide : text.show;
      return;
    }
    const action = event.target.closest && event.target.closest("[data-portal-action]");
    if (!action) return;
    if (action.dataset.portalAction === "pwa-install-prompt") { requestPwaInstall(action); return; }
    if (action.dataset.portalAction === "start-telegram-login") startTelegram(action);
    if (action.dataset.portalAction === "auth-mfa-login-cancel") { state.mfa = null; render({ primary: true }); }
  });
  document.addEventListener("submit", (event) => {
    const form = event.target.closest && event.target.closest("[data-portal-form]");
    if (!form) return;
    event.preventDefault();
    submitAuth(form);
  });
  document.addEventListener("visibilitychange", () => { if (document.visibilityState !== "hidden") schedulePolling(0); });
  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    pwaInstallPrompt = event;
    syncPwaInstallControl();
  });
  window.addEventListener("appinstalled", () => {
    pwaInstallPrompt = null;
    syncPwaInstallControl();
  });

  render();
  Promise.all([publicData("/auth/providers"), publicData("/auth/telegram/connection/status")]).then(async ([providers, connection]) => {
    state.providers = providers.providers && typeof providers.providers === "object" ? providers.providers : {};
    state.connection = connection;
    render();
    try { await resumeTelegram(); } catch (_) { /* Public Auth stays fail-closed. */ }
  });
})();
