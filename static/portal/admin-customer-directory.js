/*
 * Pure Web Admin Customer Directory UI Module
 * Frozen validator & semantic renderer for Web-native customer accounts.
 */
(function () {
  "use strict";

  const LIST_ROUTE = "/admin/customers";
  const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  const ALLOWED_STATUSES = Object.freeze(["all", "active", "locked"]);
  const ALLOWED_ACCOUNT_TYPES = Object.freeze(["standard", "telegram", "oauth_only"]);
  const ALLOWED_ROLES = Object.freeze(["admin", "support_manager", "support_operator", "user", "other"]);

  function isUuid(val) {
    return typeof val === "string" && UUID_RE.test(val.trim());
  }

  function isRoute(path) {
    const raw = String(path || "").split("?")[0].replace(/\/+$/, "") || "/";
    if (raw === LIST_ROUTE) return true;
    if (raw.startsWith(LIST_ROUTE + "/")) {
      const seg = raw.slice(LIST_ROUTE.length + 1);
      return isUuid(seg);
    }
    return false;
  }

  function accountIdFromPath(path) {
    const raw = String(path || "").split("?")[0].replace(/\/+$/, "");
    if (raw.startsWith(LIST_ROUTE + "/")) {
      const seg = raw.slice(LIST_ROUTE.length + 1);
      if (isUuid(seg)) return seg.toLowerCase();
    }
    return "";
  }

  function emptyState() {
    return {
      items: [],
      customer: null,
      filters: { q: "", status: "all" },
      pagination: { limit: 25, offset: 0, returned: 0, has_more: false, next_offset: null },
      readState: "loading",
      error: ""
    };
  }

  function listPath(filters, offset) {
    const q = String((filters && filters.q) || "").slice(0, 120).trim();
    const st = (filters && filters.status && ALLOWED_STATUSES.includes(filters.status)) ? filters.status : "all";
    const off = Math.max(0, Math.min(10000, Number(offset) || 0));
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    params.set("status", st);
    params.set("limit", "25");
    params.set("offset", String(off));
    return `${LIST_ROUTE}?${params.toString()}`;
  }

  function detailPath(id) {
    if (!isUuid(id)) throw new Error("Mã khách hàng không hợp lệ");
    return `${LIST_ROUTE}/${id.trim().toLowerCase()}`;
  }

  function checkExactKeys(obj, allowedKeys, label) {
    if (!obj || typeof obj !== "object" || Array.isArray(obj)) throw new Error(label + " must be a plain object");
    const keys = Object.keys(obj);
    if (keys.length !== allowedKeys.length) throw new Error("Invalid keys length in " + label);
    for (let k of keys) {
      if (!allowedKeys.includes(k)) throw new Error("Extra key " + k + " in " + label);
    }
  }

  function normalizeCustomer(raw) {
    checkExactKeys(raw, ["id", "display_name", "email", "account_type", "role", "role_label", "status", "password_login_enabled", "telegram_linked", "profile", "created_at", "updated_at"], "customer");
    if (!isUuid(raw.id)) throw new Error("Invalid customer id");
    if (typeof raw.display_name !== "string") throw new Error("Invalid display_name");
    if (typeof raw.email !== "string") throw new Error("Invalid email");
    if (typeof raw.account_type !== "string" || !ALLOWED_ACCOUNT_TYPES.includes(raw.account_type)) throw new Error("Invalid account_type");
    if (typeof raw.role !== "string" || !ALLOWED_ROLES.includes(raw.role)) throw new Error("Invalid role");
    if (typeof raw.role_label !== "string") throw new Error("Invalid role_label");
    if (raw.status !== "active" && raw.status !== "locked") throw new Error("Invalid status");
    if (typeof raw.password_login_enabled !== "boolean") throw new Error("Invalid password_login_enabled");
    if (typeof raw.telegram_linked !== "boolean") throw new Error("Invalid telegram_linked");

    checkExactKeys(raw.profile, ["locale", "timezone", "avatar_style"], "profile");
    if (typeof raw.profile.locale !== "string") throw new Error("Invalid profile locale");
    if (typeof raw.profile.timezone !== "string") throw new Error("Invalid profile timezone");
    if (typeof raw.profile.avatar_style !== "string") throw new Error("Invalid profile avatar_style");

    if (typeof raw.created_at !== "string") throw new Error("Invalid created_at");
    if (typeof raw.updated_at !== "string") throw new Error("Invalid updated_at");

    return {
      id: String(raw.id).toLowerCase(),
      display_name: raw.display_name,
      email: raw.email,
      account_type: raw.account_type,
      role: raw.role,
      role_label: raw.role_label,
      status: raw.status,
      password_login_enabled: raw.password_login_enabled,
      telegram_linked: raw.telegram_linked,
      profile: {
        locale: raw.profile.locale,
        timezone: raw.profile.timezone,
        avatar_style: raw.profile.avatar_style
      },
      created_at: raw.created_at,
      updated_at: raw.updated_at
    };
  }

  function normalizeList(data) {
    checkExactKeys(data, ["source", "customers", "returned", "limit", "offset", "has_more", "next_offset", "filters"], "list envelope");
    if (data.source !== "web_accounts_redacted") throw new Error("Invalid list source");
    if (!Array.isArray(data.customers)) throw new Error("customers must be an array");

    if (!Number.isInteger(data.returned) || data.returned < 0) throw new Error("returned must be a non-negative integer");
    if (data.returned !== data.customers.length) throw new Error("returned must match customers length");
    if (!Number.isInteger(data.limit) || data.limit < 1 || data.limit > 100) throw new Error("limit must be an integer between 1 and 100");
    if (!Number.isInteger(data.offset) || data.offset < 0 || data.offset > 10000) throw new Error("offset must be an integer between 0 and 10000");
    if (typeof data.has_more !== "boolean") throw new Error("has_more must be a boolean");
    if (data.next_offset !== null && (!Number.isInteger(data.next_offset) || data.next_offset < 0 || data.next_offset > 10000)) throw new Error("next_offset must be null or an integer between 0 and 10000");

    checkExactKeys(data.filters, ["q", "status"], "filters");
    if (typeof data.filters.q !== "string" || data.filters.q.length > 120) throw new Error("filters q must be a string <= 120 chars");
    if (typeof data.filters.status !== "string" || !ALLOWED_STATUSES.includes(data.filters.status)) throw new Error("filters status invalid");

    return {
      source: data.source,
      customers: data.customers.map(normalizeCustomer),
      returned: data.returned,
      limit: data.limit,
      offset: data.offset,
      has_more: data.has_more,
      next_offset: data.next_offset,
      filters: { q: data.filters.q, status: data.filters.status }
    };
  }

  function normalizeDetail(data) {
    checkExactKeys(data, ["source", "customer"], "detail envelope");
    if (data.source !== "web_accounts_redacted") throw new Error("Invalid detail source");
    return {
      source: data.source,
      customer: normalizeCustomer(data.customer)
    };
  }

  function renderFilter(filters, helpers, isBusy) {
    const q = helpers.safeText((filters && filters.q) || "");
    const st = (filters && filters.status) || "all";
    const dis = isBusy ? ' disabled aria-disabled="true"' : "";
    return `<section class="portal-card portal-card-pad" aria-label="Tìm kiếm khách hàng">`
      + `<form class="portal-project-filter" data-portal-action="admin-customer-filter">`
      + `<div class="portal-form-group"><label for="cust-filter-q">Tìm kiếm</label>`
      + `<input class="portal-input" id="cust-filter-q" name="q" type="search" maxlength="120" placeholder="Tên hoặc email…" value="${q}"${dis}></div>`
      + `<div class="portal-form-group"><label for="cust-filter-st">Trạng thái</label>`
      + `<select class="portal-select" id="cust-filter-st" name="status"${dis}>`
      + `<option value="all"${st === "all" ? " selected" : ""}>Tất cả</option>`
      + `<option value="active"${st === "active" ? " selected" : ""}>Đang hoạt động</option>`
      + `<option value="locked"${st === "locked" ? " selected" : ""}>Bị khóa</option>`
      + `</select></div>`
      + `<div class="portal-form-actions">`
      + `<button class="portal-button portal-button--primary" type="submit"${dis}>Áp dụng</button>`
      + `<button class="portal-button portal-button--quiet" type="button" data-portal-action="admin-customer-clear"${dis}>Đặt lại</button>`
      + `</div></form></section>`;
  }

  function renderListTable(items, helpers) {
    const rows = items.map((c) => {
      const emailText = c.email ? helpers.safeText(c.email) : `<span class="portal-text-muted">[Không công khai]</span>`;
      const tgBadge = c.telegram_linked ? `<span class="portal-badge portal-badge--info">Đã nối Telegram</span>` : `<span class="portal-badge portal-badge--neutral">Chưa nối</span>`;
      const statusBadge = c.status === "active" ? helpers.badge("active") : `<span class="portal-badge portal-badge--warning">Bị khóa</span>`;
      return `<tr>`
        + `<td><a class="portal-link-strong" href="${LIST_ROUTE}/${helpers.safeText(c.id)}">${helpers.safeText(c.display_name || "Chưa đặt tên")}</a></td>`
        + `<td>${emailText}</td>`
        + `<td>${helpers.safeText(c.account_type)}</td>`
        + `<td>${helpers.safeText(c.role_label)}</td>`
        + `<td>${statusBadge}</td>`
        + `<td>${tgBadge}</td>`
        + `<td><time datetime="${helpers.safeText(c.created_at)}">${helpers.safeText(c.created_at.slice(0, 10))}</time></td>`
        + `<td><a class="portal-button portal-button--quiet" href="${LIST_ROUTE}/${helpers.safeText(c.id)}">Chi tiết</a></td>`
        + `</tr>`;
    }).join("");

    return `<div class="portal-data-table-wrap" tabindex="0" role="region" aria-label="Bảng danh sách khách hàng" data-portal-table-scroll>`
      + `<table class="portal-data-table"><thead><tr>`
      + `<th scope="col">Tên hiển thị</th><th scope="col">Email</th><th scope="col">Loại TK</th><th scope="col">Vai trò</th>`
      + `<th scope="col">Trạng thái</th><th scope="col">Telegram</th><th scope="col">Ngày tạo</th><th scope="col">Thao tác</th>`
      + `</tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function renderPagination(pagination, isBusy) {
    const off = Number(pagination.offset) || 0;
    const lim = Number(pagination.limit) || 25;
    const hasMore = Boolean(pagination.has_more);
    const hasPrev = off > 0;
    const prevOff = Math.max(0, off - lim);
    const nextOff = off + lim;
    const dis = isBusy ? ' disabled aria-disabled="true"' : "";

    return `<div class="portal-form-footer"><div class="portal-pagination-group">`
      + `<button class="portal-button portal-button--quiet" type="button" data-portal-action="admin-customer-page" data-portal-offset="${prevOff}"${!hasPrev || isBusy ? " disabled" : ""}>← Trang trước</button>`
      + `<span class="portal-pagination-info">Vị trí: ${off + 1}–${off + (Number(pagination.returned) || 0)}</span>`
      + `<button class="portal-button portal-button--quiet" type="button" data-portal-action="admin-customer-page" data-portal-offset="${nextOff}"${!hasMore || isBusy ? " disabled" : ""}>Trang sau →</button>`
      + `</div><button class="portal-button portal-button--quiet" type="button" data-portal-action="admin-customer-refresh"${dis}>Làm mới</button></div>`;
  }

  function renderList(page, state, helpers) {
    const isBusy = state.readState === "loading";
    const filterHtml = renderFilter(state.filters, helpers, isBusy);

    if (state.readState === "loading" && !state.items.length) {
      return `<article class="portal-page" aria-busy="true">${helpers.renderHero(page)}`
        + `${filterHtml}<section class="portal-card portal-card-pad"><div class="portal-state" data-state="processing">`
        + `<div><h2>Đang nạp danh sách khách hàng…</h2><p>Đang tải dữ liệu tài khoản Web đã redaction từ máy chủ.</p></div>`
        + `</div></section></article>`;
    }
    if (state.readState === "error") {
      return `<article class="portal-page">${helpers.renderHero(page)}`
        + `${filterHtml}<section class="portal-card portal-card-pad"><div class="portal-state" data-state="guarded">`
        + `<div><h2>Không thể nạp danh sách khách hàng</h2><p>${helpers.safeText(state.error || "Đã xảy ra lỗi khi kết nối tới máy chủ.")}</p></div>`
        + `</div><div class="portal-form-footer"><button class="portal-button portal-button--primary" type="button" data-portal-action="admin-customer-refresh">Thử lại</button></div></section></article>`;
    }
    if (!state.items.length) {
      return `<article class="portal-page">${helpers.renderHero(page)}`
        + `${filterHtml}`
        + `${helpers.renderEmpty("Không tìm thấy khách hàng", "Không có tài khoản nào khớp với điều kiện tìm kiếm hiện tại.")}`
        + `</article>`;
    }

    return `<article class="portal-page">${helpers.renderHero(page)}`
      + `${filterHtml}<section class="portal-card portal-card-pad">`
      + `${renderListTable(state.items, helpers)}${renderPagination(state.pagination, isBusy)}`
      + `</section></article>`;
  }

  function renderDetail(page, state, helpers) {
    if (state.readState === "loading" && !state.customer) {
      return `<article class="portal-page" aria-busy="true">${helpers.renderHero(page)}`
        + `<section class="portal-card portal-card-pad"><div class="portal-state" data-state="processing">`
        + `<div><h2>Đang nạp chi tiết khách hàng…</h2><p>Đang tải hồ sơ tài khoản Web đã redaction từ máy chủ.</p></div>`
        + `</div></section></article>`;
    }
    if (state.readState === "error" || !state.customer) {
      return `<article class="portal-page">${helpers.renderHero(page)}`
        + `<section class="portal-card portal-card-pad"><div class="portal-state" data-state="guarded">`
        + `<div><h2>Không tìm thấy khách hàng</h2><p>${helpers.safeText(state.error || "Tài khoản không tồn tại hoặc đã bị gỡ bỏ.")}</p></div>`
        + `</div><div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="${LIST_ROUTE}">← Quay lại danh sách</a>`
        + `<button class="portal-button portal-button--primary" type="button" data-portal-action="admin-customer-refresh">Thử lại</button></div></section></article>`;
    }

    const c = state.customer;
    const prof = c.profile || {};
    const emailVal = c.email ? helpers.safeText(c.email) : `<span class="portal-text-muted">[Không công khai / Alias nội bộ]</span>`;
    const tgVal = c.telegram_linked ? `<span class="portal-badge portal-badge--info">Đã liên kết</span>` : `<span class="portal-badge portal-badge--neutral">Chưa liên kết</span>`;
    const stVal = c.status === "active" ? helpers.badge("active") : `<span class="portal-badge portal-badge--warning">Bị khóa</span>`;

    return `<article class="portal-page">${helpers.renderHero(page)}`
      + `<div class="portal-admin-grid">`
      + `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Tài khoản</h2><p class="portal-card-subtitle">Thông tin định danh Web đã bảo mật.</p></div>${stVal}</div>`
      + `<dl class="portal-summary-list">`
      + `<div class="portal-summary-item"><dt class="portal-summary-key">Mã tài khoản (UUID)</dt><dd class="portal-summary-value"><code>${helpers.safeText(c.id)}</code></dd></div><div class="portal-summary-item"><dt class="portal-summary-key">Tên hiển thị</dt><dd class="portal-summary-value">${helpers.safeText(c.display_name || "Chưa đặt tên")}</dd></div><div class="portal-summary-item"><dt class="portal-summary-key">Email công khai</dt><dd class="portal-summary-value">${emailVal}</dd></div><div class="portal-summary-item"><dt class="portal-summary-key">Loại tài khoản</dt><dd class="portal-summary-value">${helpers.safeText(c.account_type)}</dd></div><div class="portal-summary-item"><dt class="portal-summary-key">Vai trò</dt><dd class="portal-summary-value">${helpers.safeText(c.role_label)} (<code>${helpers.safeText(c.role)}</code>)</dd></div><div class="portal-summary-item"><dt class="portal-summary-key">Đăng nhập mật khẩu</dt><dd class="portal-summary-value">${c.password_login_enabled ? "Bật" : "Tắt"}</dd></div><div class="portal-summary-item"><dt class="portal-summary-key">Liên kết Telegram</dt><dd class="portal-summary-value">${tgVal}</dd></div>`
      + `</dl></section>`
      + `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Hồ sơ cá nhân</h2><p class="portal-card-subtitle">Tùy chọn hiển thị và thời gian.</p></div></div>`
      + `<dl class="portal-summary-list">`
      + `<div class="portal-summary-item"><dt class="portal-summary-key">Ngôn ngữ giao diện</dt><dd class="portal-summary-value">${helpers.safeText(prof.locale)}</dd></div><div class="portal-summary-item"><dt class="portal-summary-key">Múi giờ</dt><dd class="portal-summary-value">${helpers.safeText(prof.timezone)}</dd></div><div class="portal-summary-item"><dt class="portal-summary-key">Kiểu Avatar</dt><dd class="portal-summary-value">${helpers.safeText(prof.avatar_style)}</dd></div><div class="portal-summary-item"><dt class="portal-summary-key">Ngày tạo tài khoản</dt><dd class="portal-summary-value"><time datetime="${helpers.safeText(c.created_at)}">${helpers.safeText(c.created_at)}</time></dd></div><div class="portal-summary-item"><dt class="portal-summary-key">Cập nhật lần cuối</dt><dd class="portal-summary-value"><time datetime="${helpers.safeText(c.updated_at)}">${helpers.safeText(c.updated_at)}</time></dd></div>`
      + `</dl></section></div>`
      + `<div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="${LIST_ROUTE}">← Quay lại danh sách</a>`
      + `<button class="portal-button portal-button--quiet" type="button" data-portal-action="admin-customer-refresh">Làm mới</button></div></article>`;
  }

  function render(page, context, helpers) {
    const rawState = context && context.adminCustomerDirectory;
    const state = (rawState && typeof rawState === "object") ? rawState : emptyState();
    const safeHelpers = {
      safeText: (helpers && typeof helpers.safeText === "function") ? helpers.safeText : (v) => String(v || ""),
      badge: (helpers && typeof helpers.badge === "function") ? helpers.badge : (s) => `<span>${s}</span>`,
      renderHero: (helpers && typeof helpers.renderHero === "function") ? helpers.renderHero : (p) => `<header><h1>${p.title}</h1></header>`,
      renderEmpty: (helpers && typeof helpers.renderEmpty === "function") ? helpers.renderEmpty : (t, m) => `<div><h2>${t}</h2><p>${m}</p></div>`
    };

    if (page && page.layout === "admin-customer-directory-detail") {
      return renderDetail(page, state, safeHelpers);
    }
    return renderList(page, state, safeHelpers);
  }

  window.TOANAASAdminCustomerDirectory = Object.freeze({ LIST_ROUTE, isRoute, accountIdFromPath, emptyState, listPath, detailPath, normalizeList, normalizeDetail, render });
})();
