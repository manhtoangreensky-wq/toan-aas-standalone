/* Lightweight owner for the signed feature catalogue route. */
(function featureCatalogueEntry() {
  "use strict";

  const API = "/api/v1";
  const FEATURE_COPY = window.TOANAASFeatureCatalogCopy && typeof window.TOANAASFeatureCatalogCopy === "object"
    ? window.TOANAASFeatureCatalogCopy : Object.freeze({});
  const LOCALES = new Set(["vi", "en", "zh"]);
  const ENGINE_MODES = new Set(["web_native", "bot_companion", "guarded"]);
  const ENGINE_STATES = new Set(["ready", "guarded"]);
  const READINESS_STATES = new Set([
    "available", "planning_only", "local_execution", "canonical_read", "guarded", "disabled"
  ]);
  const EXCLUDED_ROUTES = new Set([
    "/", "/welcome", "/login", "/register", "/password-recovery", "/status",
    "/legal", "/privacy", "/features"
  ]);
  const FAMILY_ROUTES = new Set([
    "/features/content", "/features/image", "/features/video", "/features/voice",
    "/features/music", "/features/subtitle", "/features/documents", "/features/support"
  ]);
  const GROUPS = [
    "free_tools", "account", "wallet", "jobs", "content", "image", "video",
    "voice", "music", "subtitle", "documents", "support", "other"
  ];
  // Keep the standalone catalogue in the same closed SVG icon language as
  // the shared customer shell. These paths are local constants only; no
  // server or catalog value can supply markup.
  const FEATURE_ICON_PATHS = Object.freeze({
    dashboard: '<path d="M3.5 10.5 12 3.7l8.5 6.8v9.2a1.3 1.3 0 0 1-1.3 1.3H4.8a1.3 1.3 0 0 1-1.3-1.3z"/><path d="M9 21v-6h6v6"/>',
    catalogue: '<path d="m12 2 1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8z"/><path d="m19 16 .7 2.3L22 19l-2.3.7L19 22l-.7-2.3L16 19l2.3-.7z"/>',
    work: '<path d="M7 3.5h10M7 20.5h10M8 3.5c0 4 2.1 5.5 4 7 1.9 1.5 4 3 4 7M16 3.5c0 4-2.1 5.5-4 7-1.9 1.5-4 3-4 7"/>',
    library: '<path d="M3.5 6.5h6l1.7 2h9.3v10.8a1.7 1.7 0 0 1-1.7 1.7H5.2a1.7 1.7 0 0 1-1.7-1.7z"/><path d="M3.5 8.5h17"/>',
    account: '<circle cx="12" cy="8" r="3.5"/><path d="M4.5 20.5c.8-3.8 3.3-5.7 7.5-5.7s6.7 1.9 7.5 5.7"/>',
    legal: '<path d="M12 3v18M6 6h12M5 20h14M7 6l-3 7h6zm10 0-3 7h6z"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
    close: '<path d="m6 6 12 12M18 6 6 18"/>'
  });

  function featureIconMarkup(icon) {
    const paths = FEATURE_ICON_PATHS[icon] || FEATURE_ICON_PATHS.dashboard;
    return `<svg class="portal-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${paths}</svg>`;
  }

  const COPY = Object.freeze({
    vi: {
      caption: "Không gian làm việc", nav: "Điều hướng chính", dashboard: "Tổng quan",
      features: "Danh mục", mobileHome: "Trang chủ", mobileCreate: "Tạo",
      workspace: "Không gian", work: "Công việc", library: "Thư viện", account: "Tài khoản",
      openNav: "Mở điều hướng", closeNav: "Đóng điều hướng", location: "Vị trí hiện tại", legalPrivacy: "Pháp lý & quyền riêng tư", pageKicker: "Danh mục công cụ",
      title: "Chọn công cụ phù hợp", body: "Tìm theo mục tiêu và mở đúng không gian làm việc của bạn.",
      search: "Tìm công cụ", placeholder: "Ví dụ: OCR, video, tài liệu…", clear: "Xóa",
      result: "quy trình đang hiển thị", open: "Mở quy trình", guardedTitle: "Chưa thể tải danh mục",
      guardedBody: "Phiên hoặc dữ liệu danh mục chưa được xác minh. Vui lòng tải lại trang.",
      fallback: "Chưa có mô tả chi tiết cho công cụ này.", theme: "Giao diện", signed: "Phiên đã xác minh",
      groups: ["Tiện ích miễn phí", "Tài khoản", "Thanh toán", "Công việc", "Nội dung", "Hình ảnh", "Video", "Giọng nói", "Âm nhạc", "Phụ đề & dịch", "Tài liệu", "Hỗ trợ", "Quy trình khác"],
      engine: ["Ứng dụng Web", "Kết nối Bot", "Có giới hạn"],
      boundary: ["Liên kết tác vụ chuẩn", "Lập kế hoạch trên Web", "Tạo nội dung bằng AI", "Quản lý tài khoản"],
      readiness: ["Sẵn sàng", "Lập kế hoạch", "Xử lý tại Web", "Chỉ đọc dữ liệu chuẩn", "Có giới hạn", "Tạm dừng"]
    },
    en: {
      caption: "Workspace", nav: "Main navigation", dashboard: "Overview", features: "Catalogue",
      workspace: "Workspaces", mobileHome: "Home", mobileCreate: "Create", work: "Work", library: "Library",
      account: "Account", openNav: "Open navigation", location: "Current location", legalPrivacy: "Legal & privacy",
      closeNav: "Close navigation", pageKicker: "Workflow catalogue", title: "Choose the right tool",
      body: "Search by goal and open the workspace that fits your task.", search: "Search tools",
      placeholder: "For example: OCR, video, documents…", clear: "Clear", result: "workflows visible",
      open: "Open workflow", guardedTitle: "Catalogue unavailable", guardedBody: "The session or catalogue data could not be verified. Reload this page.",
      fallback: "A detailed description is not available for this workflow.", theme: "Theme", signed: "Verified session",
      groups: ["Free tools", "Account", "Billing", "Work", "Content", "Image", "Video", "Voice", "Music", "Subtitles & translation", "Documents", "Support", "Other workflows"],
      engine: ["Web-native", "Bot companion", "Guarded"],
      boundary: ["Canonical workflow", "Web planning", "AI content generation", "Account settings"],
      readiness: ["Available", "Planning", "Local execution", "Canonical read", "Guarded", "Disabled"]
    },
    zh: {
      caption: "工作空间", nav: "主导航", dashboard: "总览", features: "功能目录",
      workspace: "工作空间", mobileHome: "首页", mobileCreate: "创建", work: "工作", library: "资源库",
      account: "账户", openNav: "打开导航", closeNav: "关闭导航", location: "当前位置", legalPrivacy: "法律与隐私",
      pageKicker: "工作流目录", title: "选择合适的工具", body: "按目标搜索并打开适合当前任务的工作空间。",
      search: "搜索工具", placeholder: "例如：OCR、视频、文档…", clear: "清除", result: "个工作流可见",
      open: "打开工作流", guardedTitle: "无法加载目录", guardedBody: "无法验证会话或目录数据，请重新加载页面。",
      fallback: "此工作流暂时没有详细说明。", theme: "界面", signed: "会话已验证",
      groups: ["免费工具", "账户", "计费", "工作", "内容", "图像", "视频", "语音", "音乐", "字幕与翻译", "文档", "支持", "其他工作流"],
      engine: ["Web 原生", "Bot 协作", "受保护"],
      boundary: ["标准工作流", "网页规划", "AI 内容生成", "账户设置"],
      readiness: ["可用", "规划中", "Web 本地处理", "读取标准数据", "受保护", "已停用"]
    }
  });

  function safeRoute(value) {
    if (typeof value !== "string") return "";
    const route = value.trim();
    return /^\/(?!\/)[^\\?#\u0000-\u001f\u007f]*$/.test(route) ? route : "";
  }

  function safeFeature(raw) {
    if (!raw || typeof raw !== "object" || raw.kind !== "customer") return null;
    const key = typeof raw.key === "string" ? raw.key.trim().toLowerCase() : "";
    const title = typeof raw.title === "string" ? raw.title.trim() : "";
    const description = typeof raw.description === "string" ? raw.description.trim() : "";
    const route = safeRoute(raw.route);
    if (!/^[a-z][a-z0-9_]{1,119}$/.test(key) || !title || !route) return null;
    if (route.startsWith("/admin") || EXCLUDED_ROUTES.has(route) || FAMILY_ROUTES.has(route)) return null;
    const group = typeof raw.group === "string" && GROUPS.includes(raw.group.trim().toLowerCase())
      ? raw.group.trim().toLowerCase() : "other";
    const engineSource = raw.engine && typeof raw.engine === "object" ? raw.engine : {};
    const readinessSource = raw.readiness && typeof raw.readiness === "object" ? raw.readiness : {};
    return {
      key, title, description, group, route, kind: "customer",
      engine: {
        mode: ENGINE_MODES.has(engineSource.mode) ? engineSource.mode : "guarded",
        execution_state: ENGINE_STATES.has(engineSource.execution_state) ? engineSource.execution_state : "guarded"
      },
      readiness: { status: READINESS_STATES.has(readinessSource.status) ? readinessSource.status : "guarded" }
    };
  }

  function projectCatalogue(data) {
    if (!data || !Array.isArray(data.features)) return null;
    const seenKeys = new Set(), seenRoutes = new Set(), features = [];
    for (const raw of data.features) {
      const item = safeFeature(raw);
      if (!item || seenKeys.has(item.key) || seenRoutes.has(item.route)) continue;
      seenKeys.add(item.key); seenRoutes.add(item.route); features.push(item);
      if (features.length === 500) break;
    }
    return features;
  }

  function readBootstrap() {
    if (window.__TOAN_AAS_PORTAL__ && typeof window.__TOAN_AAS_PORTAL__ === "object") return window.__TOAN_AAS_PORTAL__;
    try {
      const item = document.getElementById("portal-bootstrap");
      const parsed = item && JSON.parse(item.textContent || "{}");
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch (_error) { return {}; }
  }

  function featuresHydrationIsCurrent(main, expectedPath) {
    if (!main || typeof document.getElementById !== "function") return false;
    if (document.getElementById("portal-main") !== main
      && document.getElementById("portal-root") !== main) return false;
    const location = typeof window === "object" && window ? window.location : null;
    if (!location || typeof location.pathname !== "string") return true;
    const pathname = location.pathname.replace(/\/+$/, "") || "/";
    return pathname === expectedPath;
  }

  async function readJson(path) {
    try {
      const response = await fetch(`${API}${path}`, {
        credentials: "same-origin", cache: "no-store", headers: { Accept: "application/json" }
      });
      const payload = response.ok ? await response.json() : null;
      return payload && payload.ok === true && payload.data && typeof payload.data === "object" ? payload.data : null;
    } catch (_error) { return null; }
  }

  function projectAccount(data, fallbackLocale) {
    const raw = data && data.account;
    if (!raw || typeof raw !== "object") return null;
    const email = typeof raw.email === "string" ? raw.email.trim() : "";
    const displayName = typeof raw.display_name === "string" ? raw.display_name.trim() : "";
    if (!displayName && !email) return null;
    const profile = raw.profile && typeof raw.profile === "object" ? raw.profile : {};
    return { email, displayName: displayName || email, locale: LOCALES.has(profile.locale) ? profile.locale : fallbackLocale };
  }

  function make(tag, className, text) {
    const item = document.createElement(tag);
    if (className) item.className = className;
    if (text !== undefined) item.textContent = text;
    return item;
  }
  function set(item, name, value) { item.setAttribute(name, String(value)); return item; }
  function add(parent, ...children) { children.filter(Boolean).forEach((child) => parent.appendChild(child)); return parent; }

  function officialBrandMark() {
    const mark = set(make("span", "portal-brand-mark"), "aria-hidden", "true");
    const image = make("img", "portal-brand-mark-image");
    for (const [name, value] of Object.entries({ src: "/static/logo_ch%C3%ADnh_th%E1%BB%A9c.png", alt: "", width: "56", height: "56", decoding: "async" })) set(image, name, value);
    return add(mark, image);
  }

  function link(route, label, icon, current, mobile) {
    const item = set(make("a", mobile ? "portal-mobile-nav-link" : "portal-nav-link"), "href", route);
    if (current) set(item, "aria-current", "page");
    const iconNode = set(make("span", mobile ? "portal-mobile-nav-icon" : "portal-nav-icon"), "aria-hidden", "true");
    iconNode.innerHTML = featureIconMarkup(icon);
    return add(item, iconNode,
      make("span", mobile ? "portal-mobile-nav-label" : "", label));
  }

  function renderSidebar(sidebar, copy) {
    if (!sidebar) return;
    const brand = make("div", "portal-brand"), brandHome = set(make("a", "portal-brand-home"), "href", "/dashboard");
    const brandCopy = make("span", "portal-brand-copy");
    add(brandCopy, make("strong", "portal-brand-name", "TOAN AAS"), make("small", "portal-brand-caption", copy.caption));
    const close = set(make("button", "portal-sidebar-close"), "type", "button");
    set(close, "aria-label", copy.closeNav); set(close, "data-portal-close-menu", ""); close.innerHTML = featureIconMarkup("close");
    add(brandHome, officialBrandMark(), brandCopy); add(brand, brandHome, close);
    const nav = set(make("nav", "portal-nav"), "aria-label", copy.nav), links = make("div", "portal-nav-links");
    add(links, link("/dashboard", copy.dashboard, "dashboard", false, false), link("/features", copy.features, "catalogue", true, false),
      link("/workspace-menu", copy.workspace, "dashboard", false, false), link("/account", copy.account, "account", false, false));
    add(nav, make("span", "portal-nav-label", copy.nav), links);
    const footer = make("div", "portal-sidebar-foot");
    add(footer, link("/legal", copy.legalPrivacy, "legal", false, false));
    sidebar.replaceChildren(brand, nav, footer);
  }

  function themeButton(copy) {
    const button = set(make("button", "portal-theme-toggle"), "type", "button");
    set(button, "data-portal-theme-toggle", "");
    const icon = set(make("span", "portal-theme-toggle-icon"), "data-portal-theme-icon", ""); set(icon, "aria-hidden", "true");
    return add(button, icon, set(make("span", "portal-theme-toggle-label", copy.theme), "data-portal-theme-label", ""));
  }

  function renderHeader(header, account, copy) {
    if (!header) return;
    const crumbs = set(make("nav", "portal-crumbs"), "aria-label", copy.location), actions = make("div", "portal-header-actions");
    const currentCrumb = set(make("span", "", copy.features), "aria-current", "page");
    add(crumbs, make("span", "", "TOAN AAS"), currentCrumb);
    const menu = set(make("button", "portal-menu-button"), "type", "button");
    const menuIcon = set(make("span", "portal-control-icon"), "aria-hidden", "true");
    menuIcon.innerHTML = featureIconMarkup("menu");
    add(menu, menuIcon);
    set(menu, "aria-label", copy.openNav); set(menu, "aria-controls", "portal-sidebar");
    set(menu, "aria-expanded", "false"); set(menu, "data-portal-menu", "");
    const session = make("span", "portal-session-chip"); set(session, "title", account.email || account.displayName);
    add(session, make("span", "portal-session-avatar", (account.displayName || "T").slice(0, 1).toUpperCase()),
      make("span", "portal-session-copy", account.displayName));
    add(actions, themeButton(copy), session); header.replaceChildren(menu, crumbs, actions);
  }

  function renderMobile(mobileNav, copy) {
    if (!mobileNav) return;
    mobileNav.replaceChildren(
      link("/dashboard", copy.mobileHome, "dashboard", false, true),
      link("/features", copy.mobileCreate, "catalogue", true, true),
      link("/jobs", copy.work, "work", false, true),
      link("/assets", copy.library, "library", false, true),
      link("/account", copy.account, "account", false, true)
    );
    mobileNav.hidden = false;
  }

  let featureNavigationCleanup = () => {};
  const FEATURE_TABINDEX_SNAPSHOT = "data-features-tabindex";
  function bindFeatureNavigation(copy) {
    featureNavigationCleanup();
    const sidebar = document.querySelector("[data-portal-sidebar]");
    const backdrop = document.querySelector("[data-portal-backdrop]");
    const menu = document.querySelector("[data-portal-menu]");
    const close = sidebar && sidebar.querySelector("[data-portal-close-menu]");
    if (!sidebar || !backdrop || !menu || !close || typeof window.matchMedia !== "function") return;
    const media = window.matchMedia("(max-width: 980px)");
    let returnFocus = null;
    const controls = () => Array.from(sidebar.querySelectorAll(
      "a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary"
    ));
    const setTabStops = (disabled) => controls().forEach((control) => {
      if (disabled) {
        if (!control.hasAttribute(FEATURE_TABINDEX_SNAPSHOT)) {
          set(control, FEATURE_TABINDEX_SNAPSHOT, control.hasAttribute("tabindex") ? (control.getAttribute("tabindex") || "") : "__absent__");
        }
        set(control, "tabindex", "-1");
        return;
      }
      const previous = control.getAttribute(FEATURE_TABINDEX_SNAPSHOT);
      if (previous === null) return;
      if (previous === "__absent__") control.removeAttribute("tabindex"); else set(control, "tabindex", previous);
      control.removeAttribute(FEATURE_TABINDEX_SNAPSHOT);
    });
    const setClosed = (restoreFocus) => {
      const wasOpen = sidebar.classList.contains("is-open");
      sidebar.classList.remove("is-open"); backdrop.hidden = true;
      sidebar.removeAttribute("role"); sidebar.removeAttribute("aria-modal");
      set(menu, "aria-expanded", "false"); set(menu, "aria-label", copy.openNav);
      if (media.matches) {
        set(sidebar, "aria-hidden", "true"); if ("inert" in sidebar) sidebar.inert = true; setTabStops(true);
      } else {
        sidebar.removeAttribute("aria-hidden"); if ("inert" in sidebar) sidebar.inert = false; setTabStops(false);
      }
      if (restoreFocus && wasOpen && returnFocus && typeof returnFocus.focus === "function") returnFocus.focus();
      returnFocus = null;
    };
    const open = () => {
      if (!media.matches) return;
      returnFocus = menu;
      sidebar.classList.add("is-open"); set(sidebar, "role", "dialog"); set(sidebar, "aria-modal", "true");
      sidebar.removeAttribute("aria-hidden"); if ("inert" in sidebar) sidebar.inert = false; setTabStops(false);
      backdrop.hidden = false; set(menu, "aria-expanded", "true"); set(menu, "aria-label", copy.closeNav);
      window.requestAnimationFrame(() => close.focus());
    };
    const keydown = (event) => {
      if (!sidebar.classList.contains("is-open")) return;
      if (event.key === "Escape") { event.preventDefault(); setClosed(true); return; }
      if (event.key !== "Tab") return;
      const items = controls(), first = items[0], last = items[items.length - 1], activeInside = sidebar.contains(document.activeElement);
      if (!items.length) return;
      if (event.shiftKey && (document.activeElement === first || !activeInside)) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && (document.activeElement === last || !activeInside)) { event.preventDefault(); first.focus(); }
    };
    const toggle = () => sidebar.classList.contains("is-open") ? setClosed(true) : open();
    const dismiss = () => setClosed(true);
    const sync = () => {
      const active = document.activeElement;
      setClosed(false);
      if (media.matches && sidebar.contains(active)) {
        menu.focus();
      } else if (!media.matches && (active === menu || active === close)) {
        const destination = controls().find((control) => control.tagName === "A");
        if (destination && typeof destination.focus === "function") destination.focus();
      }
    };
    menu.addEventListener("click", toggle); close.addEventListener("click", dismiss);
    backdrop.addEventListener("click", dismiss); document.addEventListener("keydown", keydown);
    if (media.addEventListener) media.addEventListener("change", sync); else media.addListener(sync);
    sync();
    featureNavigationCleanup = () => {
      menu.removeEventListener("click", toggle); close.removeEventListener("click", dismiss);
      backdrop.removeEventListener("click", dismiss); document.removeEventListener("keydown", keydown);
      if (media.removeEventListener) media.removeEventListener("change", sync); else media.removeListener(sync);
    };
  }

  function signal(className, attribute, value, label) { return set(make("span", className, label), attribute, value); }

  function localizedFeatureCopy(feature, locale) {
    const localized = FEATURE_COPY[locale] && FEATURE_COPY[locale][feature.key];
    return localized && localized.title && localized.description
      ? { ...feature, title: localized.title, description: localized.description }
      : { ...feature };
  }

  function classifyCatalogBoundary(feature) {
    if (!feature) return "other";
    const k = feature.key || "";
    const r = feature.route || "";
    const accountRouteByKey = {
      interface_locale_navigator: "/account/interface-language",
      account_security: "/account/security",
      workspace_care: "/account/workspace-care"
    };
    if (accountRouteByKey[k] === r) {
      return "account_management";
    }
    if (k === "video_ai_prompt" || k === "video_single" || r === "/video/create" || r === "/video/new") {
      return "canonical_bridge";
    }
    if (feature.engine && feature.engine.mode === "web_native") return "web_planning";
    if (feature.readiness && feature.readiness.status === "planning_only") return "web_planning";
    if (r.startsWith("/video-studio/") || r.startsWith("/content/") || ["dashboard", "projects", "workspace_drafts", "notes", "reminders", "inbox", "workboard", "campaign_planner", "prompt_studio", "prompt_library", "free_prompt_gallery", "content_studio", "chat", "cskh_help"].includes(k)) {
      return "web_planning";
    }
    return "runtime_generator";
  }

  function featureCard(feature, copy, locale) {
    const displayFeature = localizedFeatureCopy(feature, locale);
    const boundary = classifyCatalogBoundary(feature);
    const wrapper = make("div", "portal-catalog-item");
    set(wrapper, "data-catalog-item", ""); set(wrapper, "data-feature-key", feature.key); set(wrapper, "data-feature-route", feature.route);
    set(wrapper, "data-boundary", boundary);
    const boundaryKeywords = boundary === "account_management"
      ? "tài khoản ngôn ngữ bảo mật dữ liệu account settings"
      : (boundary === "canonical_bridge"
      ? "job bridge canonical thực thi trực tiếp"
      : (boundary === "web_planning"
        ? "kế hoạch workspace bản nháp draft web planning"
        : "bộ tạo ai bot generator runtime"));
    set(wrapper, "data-catalog-text", [displayFeature.title, displayFeature.description, feature.title, feature.description, feature.key, feature.route, feature.group, boundary, boundaryKeywords].join(" ").toLocaleLowerCase());
    const card = set(make("a", "portal-module-card"), "href", feature.route);
    set(card, "data-feature-key", feature.key); set(card, "data-feature-route", feature.route);
    set(card, "data-boundary", boundary);
    const top = make("div", "portal-module-card-top"), signals = make("span", "portal-module-card-signals");
    const engineIndex = ["web_native", "bot_companion", "guarded"].indexOf(feature.engine.mode);
    const readinessIndex = ["available", "planning_only", "local_execution", "canonical_read", "guarded", "disabled"].indexOf(feature.readiness.status);
    const boundaryIndex = { canonical_bridge: 0, web_planning: 1, runtime_generator: 2, account_management: 3 }[boundary] ?? 2;
    add(signals, signal("portal-engine-label", "data-engine-mode", feature.engine.mode, copy.engine[Math.max(0, engineIndex)]),
      signal("portal-readiness-label", "data-readiness", feature.readiness.status, copy.readiness[Math.max(0, readinessIndex)]),
      signal("portal-boundary-label", "data-boundary", boundary, copy.boundary[boundaryIndex]));
    add(top, make("span", "portal-module-icon", "◇"), signals);
    const details = make("div"), description = make("p", "", displayFeature.description || copy.fallback);
    if (!displayFeature.description) set(description, "data-catalog-description-fallback", "true");
    add(details, make("h3", "", displayFeature.title), description);
    const footer = make("span", "portal-module-card-footer"); add(footer, make("span", "", copy.open), make("span", "portal-module-arrow", "→"));
    add(card, top, details, footer); return add(wrapper, card);
  }

  function renderGuarded(main, copy) {
    const page = set(make("article", "portal-page"), "data-features-guarded", "true"), card = make("section", "portal-card portal-card-pad");
    add(card, make("h1", "portal-title", copy.guardedTitle), make("p", "portal-description", copy.guardedBody));
    add(page, card); main.replaceChildren(page); set(main, "data-portal-features-state", "guarded");
  }

  function renderCatalogue(main, features, copy, locale) {
    const page = set(make("article", "portal-page"), "data-features-ready", "true"), hero = make("header", "portal-hero");
    add(hero, make("span", "portal-eyebrow", copy.pageKicker), make("h1", "portal-title", copy.title), make("p", "portal-description", copy.body));
    const catalog = make("section", "portal-feature-catalog"), search = make("div", "portal-catalog-search");
    const label = set(make("label", "", copy.search), "for", "portal-catalog-search"), control = make("div", "portal-catalog-search-control");
    const input = set(make("input", "portal-input"), "id", "portal-catalog-search");
    set(input, "type", "search"); set(input, "placeholder", copy.placeholder); set(input, "data-portal-catalog-search", "");
    const clear = set(make("button", "portal-catalog-clear", copy.clear), "type", "button"); set(clear, "data-portal-catalog-clear", ""); clear.hidden = true;
    add(control, make("span", "", "⌕"), input, clear);
    const result = set(make("p", "portal-catalog-search-result"), "data-portal-catalog-result", "");
    set(result, "role", "status");
    add(search, label, control, result); add(catalog, search);
    const cards = [];
    GROUPS.forEach((group, index) => {
      const entries = features.filter((item) => item.group === group); if (!entries.length) return;
      const section = set(make("section", "portal-feature-group"), "data-catalog-group", group), heading = make("div", "portal-feature-group-head");
      add(heading, make("h2", "", copy.groups[index]), make("span", "portal-feature-count", String(entries.length)));
      const grid = make("div", "portal-module-grid");
      entries.forEach((feature) => { const card = featureCard(feature, copy, locale); cards.push(card); add(grid, card); });
      add(section, heading, grid); add(catalog, section);
    });
    const filter = () => {
      const needle = input.value.trim().toLocaleLowerCase(); let visible = 0;
      cards.forEach((card) => { card.hidden = Boolean(needle) && !card.getAttribute("data-catalog-text").includes(needle); if (!card.hidden) visible += 1; });
      catalog.querySelectorAll("[data-catalog-group]").forEach((section) => {
        const matching = Array.from(section.querySelectorAll("[data-catalog-item]")).filter((card) => !card.hidden).length;
        section.hidden = matching === 0;
        section.querySelector(".portal-feature-count").textContent = String(matching);
      });
      clear.hidden = !needle; result.textContent = `${visible} ${copy.result}.`;
    };
    input.addEventListener("input", filter);
    input.addEventListener("keydown", (event) => { if (event.key === "Escape" && input.value) { input.value = ""; filter(); input.focus(); } });
    clear.addEventListener("click", () => { input.value = ""; filter(); input.focus(); });
    filter(); add(page, hero, catalog); main.replaceChildren(page); set(main, "data-portal-features-state", "ready");
  }

  let featureMotionCleanup = () => {};
  function featureMotionReduced() {
    return typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }
  function mountFeatureMotion(main) {
    featureMotionCleanup(); featureMotionCleanup = () => {};
    const shell = document.getElementById("portal-shell"), body = document.body;
    if (shell) { set(shell, "data-portal-app-kind", "customer"); set(shell, "data-portal-surface", "customer"); set(shell, "data-portal-presentation-phase", "entry"); }
    if (body) { set(body, "data-portal-app-kind", "customer"); set(body, "data-portal-surface", "customer"); }
    set(main, "data-portal-presentation-phase", featureMotionReduced() ? "settled" : "entry");
    if (featureMotionReduced()) return;

    const entrance = main.querySelector(".portal-hero") || main;
    const targets = Array.from(main.querySelectorAll(".portal-feature-group"));
    const armItems = (target) => {
      Array.from(target.querySelectorAll(".portal-catalog-item")).slice(0, 6).forEach((item, index) => {
        item.classList.add("portal-workspace-motion-item");
        item.style.setProperty("--portal-workspace-motion-index", String(index));
      });
    };
    let observer = null, clearTimer = null, featureMotionActive = true;
    const revealFrames = new Set();
    const focusHandlers = [];
    const reveal = (target) => {
      if (!featureMotionActive || !target || !target.classList.contains("is-pending")) return;
      target.classList.remove("is-pending"); target.classList.add("is-visible");
      if (observer) observer.unobserve(target);
    };
    targets.forEach((target) => {
      target.classList.add("portal-workspace-motion-target");
      const onFocus = () => { armItems(target); reveal(target); };
      target.addEventListener("focusin", onFocus, { once: true });
      focusHandlers.push({ target, onFocus });
    });

    const revealQueued = new WeakSet();
    const scheduleReveal = (target) => {
      if (!featureMotionActive || revealQueued.has(target)) return;
      revealQueued.add(target);
      armItems(target);
      if (typeof window.requestAnimationFrame !== "function") return reveal(target);
      let firstFrame = 0;
      firstFrame = window.requestAnimationFrame(() => {
        revealFrames.delete(firstFrame);
        if (!featureMotionActive) return;
        let secondFrame = 0;
        secondFrame = window.requestAnimationFrame(() => {
          revealFrames.delete(secondFrame);
          if (featureMotionActive) reveal(target);
        });
        revealFrames.add(secondFrame);
      });
      revealFrames.add(firstFrame);
    };
    if (typeof window.IntersectionObserver === "function") {
      observer = new window.IntersectionObserver((entries) => {
        if (!featureMotionActive) return;
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            if (entry.target.classList.contains("is-pending")) scheduleReveal(entry.target);
            else observer.unobserve(entry.target);
          } else entry.target.classList.add("is-pending");
        });
      }, { rootMargin: "0px 0px -8%", threshold: 0 });
      targets.forEach((target) => observer.observe(target));
    }

    const clearEntrance = (event) => {
      if (event && event.target !== entrance) return;
      entrance.removeAttribute("data-portal-features-motion");
      set(main, "data-portal-presentation-phase", "settled");
      if (shell) set(shell, "data-portal-presentation-phase", "settled");
      if (clearTimer !== null) { window.clearTimeout(clearTimer); clearTimer = null; }
      entrance.removeEventListener("animationend", clearEntrance);
    };
    const activate = () => {
      if (!featureMotionActive || !entrance.isConnected) return;
      set(entrance, "data-portal-features-motion", "enter");
      clearTimer = window.setTimeout(clearEntrance, 760);
    };
    entrance.addEventListener("animationend", clearEntrance);
    let entranceFrameOne = 0, entranceFrameTwo = 0;
    if (typeof window.requestAnimationFrame === "function") {
      entranceFrameOne = window.requestAnimationFrame(() => {
        entranceFrameOne = 0;
        if (!featureMotionActive) return;
        entranceFrameTwo = window.requestAnimationFrame(() => {
          entranceFrameTwo = 0;
          activate();
        });
      });
    } else activate();
    featureMotionCleanup = () => {
      featureMotionActive = false;
      if (observer) observer.disconnect();
      if (clearTimer !== null) { window.clearTimeout(clearTimer); clearTimer = null; }
      if (typeof window.cancelAnimationFrame === "function") {
        if (entranceFrameOne) window.cancelAnimationFrame(entranceFrameOne);
        if (entranceFrameTwo) window.cancelAnimationFrame(entranceFrameTwo);
        revealFrames.forEach((frame) => window.cancelAnimationFrame(frame));
      }
      entranceFrameOne = 0;
      entranceFrameTwo = 0;
      revealFrames.clear();
      focusHandlers.forEach(({ target, onFocus }) => target.removeEventListener("focusin", onFocus));
      entrance.removeEventListener("animationend", clearEntrance);
    };
  }

  function renderShell(features, account, locale, ready) {
    if (!document || typeof document.getElementById !== "function") return;
    const main = document.getElementById("portal-main") || document.getElementById("portal-root");
    if (!main || typeof document.createElement !== "function") return;
    const copy = COPY[locale]; renderSidebar(document.getElementById("portal-sidebar"), copy);
    renderHeader(document.querySelector ? document.querySelector("[data-portal-header]") : null, account || { displayName: "", email: "" }, copy);
    const mobile = document.querySelector ? document.querySelector("[data-portal-mobile-nav]") : null;
    if (ready) { renderMobile(mobile, copy); renderCatalogue(main, features, copy, locale); } else renderGuarded(main, copy);
    mountFeatureMotion(main);
    bindFeatureNavigation(copy);
    if (window.TOANAASPortalTheme && typeof window.TOANAASPortalTheme.syncControls === "function") window.TOANAASPortalTheme.syncControls();
  }

  async function hydrateFeatures() {
    const initial = readBootstrap(), fallbackLocale = LOCALES.has(initial.interfaceLocale) ? initial.interfaceLocale : "vi";
    const initialMain = document.getElementById("portal-main") || document.getElementById("portal-root");
    const [catalogueData, accountData] = await Promise.all([readJson("/catalog"), readJson("/auth/me")]);
    const catalog = projectCatalogue(catalogueData), account = projectAccount(accountData, fallbackLocale);
    const locale = account ? account.locale : fallbackLocale, ready = Boolean(catalog && account);
    const next = {
      ...initial, path: "/features", interfaceLocale: locale, catalog: catalog || [], isAdmin: false, capabilities: {},
      profile: account ? { locale } : {}, session: { authenticated: Boolean(account), csrfReady: false,
        displayName: account ? account.displayName : "", email: account ? account.email : "" },
      pageStates: { ...(initial.pageStates || {}), "/features": ready ? "read_only" : "guarded" }
    };
    if (!featuresHydrationIsCurrent(initialMain, "/features")) return initial;
    window.__TOAN_AAS_PORTAL__ = next; renderShell(next.catalog, account, locale, ready); return next;
  }

  window.__TOAN_AAS_FEATURES_READY__ = hydrateFeatures();
}());
