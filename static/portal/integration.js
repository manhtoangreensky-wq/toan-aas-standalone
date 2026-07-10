/*
 * Server-backed integration for the presentation shell.
 * It calls only the standalone Web App API.  Providers, PayOS and bot secrets
 * remain server-side behind the private bridge.
 */
(function portalIntegration() {
  "use strict";

  const API = "/api/v1";
  const JOB_POLL_INTERVAL_MS = 15000;
  const JOB_POLL_MAX_BACKOFF_MS = 60000;
  let jobPollTimer = 0;
  let jobPollFailures = 0;
  const submissions = new Map();
  const FEATURE_BY_PATH = {
    "/chat": "chat", "/prompt-studio": "prompt_studio", "/content/caption": "caption",
    "/content/hashtag": "hashtag", "/content/hook": "hook", "/content/script": "script",
    "/content/storyboard": "storyboard", "/content/pack": "content_pack",
    "/image": "image_create", "/image/create": "image_create", "/image/edit": "image_edit", "/image/upscale": "image_upscale", "/image/transform": "image_transform", "/image/remove-background": "image_remove_background", "/image/history": "image_history",
    "/video": "video_single", "/video/create": "video_single", "/video/long": "video_long", "/video/image-to-video": "video_image_to_video",
    "/video/product": "video_product", "/video/trend": "video_trend", "/video/multiscene": "video_multiscene", "/video/text-to-video": "video_text_to_video", "/video/quick": "video_quick", "/video/progress": "video_progress", "/video/preview": "video_preview", "/video/export": "video_export", "/video/add-ons": "video_addons", "/video/mux": "video_mux",
    "/voice": "voice_vault", "/voice/create": "voice_tts", "/voice/tts": "voice_tts", "/voice/vault": "voice_saved_tts", "/voice/saved": "voice_saved_tts", "/voice/clone": "voice_clone", "/voice/preview": "voice_preview", "/voice/outputs": "voice_outputs",
    "/music": "music_background", "/music/library": "music_library", "/music/ai": "music_background", "/music/create": "music_background", "/music/song": "music_song", "/music/sfx": "music_sfx", "/music/upload": "music_upload",
    "/subtitle": "subtitle_asr", "/subtitle/create": "subtitle_create", "/translate": "subtitle_translate", "/dubbing": "video_dub", "/asr": "asr", "/subtitle/formats": "subtitle_formats", "/documents": "documents", "/documents/pdf": "documents_pdf", "/documents/ocr": "documents_ocr", "/documents/merge": "documents_merge", "/documents/split": "documents_split", "/documents/compress": "documents_compress", "/documents/translate": "documents_translate"
  };

  function base() {
    return window.__TOAN_AAS_PORTAL__ && typeof window.__TOAN_AAS_PORTAL__ === "object" ? window.__TOAN_AAS_PORTAL__ : {};
  }

  function toast(message, type) {
    const region = document.querySelector("[data-portal-toast]");
    if (!region) return;
    const node = document.createElement("div");
    node.className = `portal-toast${type === "error" ? " portal-toast--warning" : ""}`;
    node.textContent = message;
    region.appendChild(node);
    window.setTimeout(() => node.remove(), 6500);
  }

  function randomKey(prefix) {
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    return `${prefix}-${Array.from(bytes, (item) => item.toString(16).padStart(2, "0")).join("")}`;
  }

  function safeReturnPath(value) {
    if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//") || value.includes("\\")) return "";
    return value;
  }

  function acquireSubmission(scope, fingerprint) {
    let entry = submissions.get(scope);
    if (!entry || entry.fingerprint !== fingerprint) {
      entry = { fingerprint, key: randomKey(scope), inFlight: false };
      submissions.set(scope, entry);
    }
    if (entry.inFlight) return null;
    entry.inFlight = true;
    return entry;
  }

  function releaseSubmission(entry) {
    if (entry) entry.inFlight = false;
  }

  async function api(path, options) {
    const context = base();
    const headers = new Headers((options && options.headers) || {});
    headers.set("Accept", "application/json");
    headers.set("X-Request-ID", randomKey("web"));
    if (context.session && context.session.csrfToken && options && options.method && options.method !== "GET") {
      headers.set("X-CSRF-Token", context.session.csrfToken);
    }
    const response = await fetch(`${API}${path}`, { credentials: "same-origin", ...options, headers });
    let payload = {};
    try { payload = await response.json(); } catch (_) { /* safe generic error below */ }
    if (!response.ok || !payload.ok) {
      const error = new Error(payload.message || "Yêu cầu chưa được máy chủ xác nhận.");
      error.payload = payload;
      error.status = response.status;
      throw error;
    }
    return payload;
  }

  function merge(next) {
    window.__TOAN_AAS_PORTAL__ = { ...base(), ...next };
    if (window.TOANAASPortal) window.TOANAASPortal.mount(window.__TOAN_AAS_PORTAL__);
  }

  function activeJob(record) {
    return record && ["queued", "processing", "pending", "running"].includes(String(record.status || "").toLowerCase());
  }

  function isJobPollingRoute(path) {
    return path === "/jobs" || path.startsWith("/jobs/") || path === "/video/progress";
  }

  function scheduleJobPolling(path, records, delayMs) {
    if (jobPollTimer || !isJobPollingRoute(path) || !base().bridge || base().bridge.available !== true) return;
    const active = Array.isArray(records) ? records.some(activeJob) : activeJob(records);
    if (!active) return;
    const delay = Number.isFinite(Number(delayMs)) ? Math.max(0, Number(delayMs)) : JOB_POLL_INTERVAL_MS;
    jobPollTimer = window.setTimeout(async () => {
      jobPollTimer = 0;
      try {
        if (path.startsWith("/jobs/") && path !== "/jobs/") {
          const jobId = path.slice("/jobs/".length);
          const result = await api(`/jobs/${encodeURIComponent(jobId)}`);
          const record = result.data || {};
          merge({ jobDetail: record, pageStates: { ...(base().pageStates || {}), [path]: result.status || "read_only" } });
          jobPollFailures = 0;
          scheduleJobPolling(path, record);
        } else {
          const result = await api("/jobs");
          const items = result.data && result.data.items ? result.data.items : [];
          merge({ jobs: items });
          jobPollFailures = 0;
          scheduleJobPolling(path, items);
        }
      } catch (_) {
        // Background refresh remains quiet: a guarded/temporary bridge state
        // must never turn into client-side failure data or a fake completion.
        jobPollFailures += 1;
        const currentPath = (base().path || window.location.pathname).split("?")[0];
        const retryDelay = Math.min(JOB_POLL_MAX_BACKOFF_MS, JOB_POLL_INTERVAL_MS * (2 ** Math.min(jobPollFailures, 2)));
        if (currentPath === path) scheduleJobPolling(path, records, retryDelay);
      }
    }, delay);
  }

  function featurePageStates(catalog, readiness) {
    const states = {};
    const features = (readiness && readiness.features) || {};
    Object.entries(FEATURE_BY_PATH).forEach(([route, key]) => {
      const state = features[key];
      if (!state) return;
      states[route] = state.public_ready ? "ready" : "guarded";
    });
    (catalog || []).forEach((item) => {
      const state = features[item.key];
      if (!state) return;
      states[item.route && item.route.split("?")[0]] = state.public_ready ? "ready" : "guarded";
    });
    return states;
  }

  async function hydrate() {
    const context = base();
    const [catalogResponse, statusResponse, meResponse] = await Promise.all([
      fetch(`${API}/catalog`, { credentials: "same-origin" }).then((r) => r.json()).catch(() => ({})),
      fetch(`${API}/core/status`, { credentials: "same-origin" }).then((r) => r.json()).catch(() => ({})),
      fetch(`${API}/auth/me`, { credentials: "same-origin" }).then(async (r) => r.ok ? r.json() : ({})).catch(() => ({}))
    ]);
    const catalog = catalogResponse && catalogResponse.data && Array.isArray(catalogResponse.data.features) ? catalogResponse.data.features : [];
    const status = statusResponse && statusResponse.data ? statusResponse.data : {};
    const me = meResponse && meResponse.data ? meResponse.data : {};
    const account = me.account || null;
    const copyfastEnabled = Boolean(status.flags && status.flags.copyfast_enabled);
    const bridgeAvailable = Boolean(copyfastEnabled && status.bridge_configured && account && account.canonical_user_id);
    const capabilities = {
      "auth-login": true,
      "auth-register": true,
      "auth-logout": Boolean(account && me.csrf_token),
      "start-telegram-link": Boolean(account),
      "refresh-link-status": Boolean(account),
      "refresh-jobs": Boolean(bridgeAvailable),
      "refresh-assets": Boolean(bridgeAvailable),
      "refresh-payment": Boolean(bridgeAvailable),
      "refresh-admin": Boolean(status.flags && status.flags.admin_erp_enabled && account && account.role === "admin" && bridgeAvailable),
      "payment-create": Boolean(status.flags && status.flags.payment_enabled && bridgeAvailable),
      "feature-draft": Boolean(bridgeAvailable),
      "feature-estimate": Boolean(bridgeAvailable),
      // Confirm remains clickable when the bridge is present so its canonical
      // guarded/maintenance result can be shown instead of being faked client-side.
      "feature-confirm": Boolean(bridgeAvailable),
      "create-ticket": Boolean(bridgeAvailable)
    };
    merge({
      ...context,
      catalog,
      isAdmin: Boolean(account && account.role === "admin"),
      profile: account ? { displayName: account.display_name || account.email, email: account.email } : {},
      linkStatus: { linked: Boolean(account && account.canonical_user_id) },
      session: {
        authenticated: Boolean(account), csrfReady: Boolean(me.csrf_token), csrfToken: me.csrf_token || "",
        displayName: account ? (account.display_name || account.email) : "", email: account ? account.email : ""
      },
      bridge: { available: bridgeAvailable, csrfReady: Boolean(me.csrf_token), configured: Boolean(status.bridge_configured), copyfastEnabled },
      pwaEnabled: Boolean(status.flags && status.flags.pwa_enabled),
      capabilities,
      pageStates: featurePageStates(catalog, {})
    });
    if (status.flags && status.flags.pwa_enabled && "serviceWorker" in navigator) {
      navigator.serviceWorker.register("/static/portal/service-worker.js").catch(() => {});
    }
    if (account && (context.path || window.location.pathname).split("?")[0] === "/onboarding") await hydrateLinkStatus();
    if (bridgeAvailable) await hydrateCanonicalData();
  }

  async function hydrateLinkStatus() {
    try {
      const link = await api("/auth/telegram/link/status");
      merge({ linkStatus: link.data || {} });
    } catch (_) {
      // The onboarding shell stays usable and does not infer a link from a
      // failed status check.  A future refresh remains available.
    }
  }

  async function hydrateCanonicalData() {
    const context = base();
    const path = (context.path || window.location.pathname).split("?")[0];
    try {
      if (path === "/dashboard") {
        const [wallet, jobs, assets, readiness] = await Promise.all([api("/wallet"), api("/jobs"), api("/assets"), api("/features/status")]);
        merge({
          wallet: wallet.data || null,
          jobs: jobs.data && jobs.data.items ? jobs.data.items : [],
          assets: assets.data && assets.data.items ? assets.data.items : [],
          readiness: readiness.data || {},
          pageStates: { ...(base().pageStates || {}), ...featurePageStates(base().catalog || [], readiness.data || {}), [path]: "read_only" }
        });
      } else if (path === "/pricing") {
        const pricing = await api("/pricing");
        merge({ pricingCatalog: pricing.data || {}, pageStates: { ...(base().pageStates || {}), [path]: "read_only" } });
      } else if (path === "/packages") {
        const packages = await api("/packages");
        merge({ packageCatalog: packages.data || {}, pageStates: { ...(base().pageStates || {}), [path]: "read_only" } });
      } else if (path === "/wallet" || path === "/wallet/topup") {
        const [wallet, history, packages] = await Promise.all([api("/wallet"), api("/wallet/history"), api("/packages")]);
        merge({ wallet: wallet.data, walletHistory: history.data && history.data.items ? history.data.items : [], packageCatalog: packages.data || {}, pageStates: path === "/wallet" ? { ...(base().pageStates || {}), [path]: "read_only" } : (base().pageStates || {}) });
      } else if (path === "/jobs") {
        const jobs = await api("/jobs");
        const items = jobs.data && jobs.data.items ? jobs.data.items : [];
        merge({ jobs: items, pageStates: { ...(base().pageStates || {}), [path]: "read_only" } });
        scheduleJobPolling(path, items);
      } else if (path.startsWith("/jobs/")) {
        const jobId = path.slice("/jobs/".length);
        if (!jobId) return;
        const job = await api(`/jobs/${encodeURIComponent(jobId)}`);
        const record = job.data || {};
        merge({ jobDetail: record, pageStates: { ...(base().pageStates || {}), [path]: job.status || "read_only" } });
        scheduleJobPolling(path, record);
      } else if (path === "/assets" || ["/image/history", "/image/assets", "/video/preview", "/video/export", "/voice/outputs", "/music/library", "/music-library", "/subtitle/formats"].includes(path)) {
        const assets = await api("/assets");
        merge({ assets: assets.data && assets.data.items ? assets.data.items : [], pageStates: { ...(base().pageStates || {}), [path]: "read_only" } });
      } else if (path === "/video/progress") {
        const jobs = await api("/jobs");
        const items = jobs.data && jobs.data.items ? jobs.data.items : [];
        merge({ jobs: items, pageStates: { ...(base().pageStates || {}), [path]: "read_only" } });
        scheduleJobPolling(path, items);
      } else if ((path === "/image" || (path.startsWith("/image/") && path !== "/image/history")) || (path === "/video" || (path.startsWith("/video/") && !["/video/progress", "/video/preview", "/video/export"].includes(path)))) {
        const [pricing, readiness] = await Promise.all([api("/pricing"), api("/features/status")]);
        merge({
          pricingCatalog: pricing.data || {},
          readiness: readiness.data || {},
          pageStates: featurePageStates(base().catalog || [], readiness.data || {})
        });
      } else if (path === "/tts" || path.startsWith("/voice")) {
        const [profiles, readiness] = await Promise.all([api("/voice/profiles"), api("/features/status")]);
        merge({
          voiceProfiles: profiles.data && profiles.data.items ? profiles.data.items : [],
          readiness: readiness.data || {},
          pageStates: featurePageStates(base().catalog || [], readiness.data || {})
        });
      } else if (path === "/tickets") {
        const tickets = await api("/support/tickets");
        merge({ tickets: tickets.data && tickets.data.items ? tickets.data.items : [], pageStates: { ...(base().pageStates || {}), [path]: "read_only" } });
      } else if (path.startsWith("/admin")) {
        const endpoints = {
          "/admin": "/admin/summary",
          "/admin/users": "/admin/users",
          "/admin/jobs": "/admin/jobs",
          "/admin/jobs/failed": "/admin/jobs",
          "/admin/payments": "/admin/payments",
          "/admin/providers": "/admin/providers",
          "/admin/tickets": "/admin/tickets"
        };
        let endpoint = endpoints[path];
        if (!endpoint) {
          const pieces = path.split("/").filter(Boolean);
          const module = pieces[1] || "overview";
          const recordId = pieces.length > 2 ? pieces.slice(2).join("/") : "";
          endpoint = `/admin/modules/${encodeURIComponent(module)}${recordId ? `?record_id=${encodeURIComponent(recordId)}` : ""}`;
        }
        const admin = await api(endpoint);
        merge({
          adminData: admin.data || {},
          pageStates: { ...(base().pageStates || {}), [path]: admin.status === "completed" ? "read_only" : (admin.status || "read_only") }
        });
      } else {
        const readiness = await api("/features/status");
        merge({ readiness: readiness.data || {}, pageStates: featurePageStates(base().catalog || [], readiness.data || {}) });
      }
    } catch (error) {
      // A guarded bridge is an expected state; do not manufacture data.
      if (error && error.payload && error.payload.message) toast(error.payload.message, "error");
    }
  }

  async function payloadFor(fields, route) {
    const priorFlow = route && base().featureFlows && base().featureFlows[route];
    const priorInput = priorFlow && priorFlow.input && typeof priorFlow.input === "object" ? priorFlow.input : {};
    const values = { ...priorInput, ...fields };
    delete values.password;
    delete values.confirm_password;
    const uploadIds = Array.isArray(priorInput.upload_ids) ? priorInput.upload_ids.filter((item) => typeof item === "string" && item) : [];
    const priorUploads = priorFlow && priorFlow.data && Array.isArray(priorFlow.data.uploads) ? priorFlow.data.uploads : [];
    for (const [field, value] of Object.entries(values)) {
      const files = typeof File !== "undefined" && value instanceof File
        ? [value]
        : (Array.isArray(value) && typeof File !== "undefined" && value.every((item) => item instanceof File) ? value : []);
      if (!files.length) continue;
      for (const file of files) {
        const existing = priorUploads.find((item) => item && item.id && item.file_name === file.name && Number(item.content_size || 0) === Number(file.size || 0));
        if (existing) {
          uploadIds.push(existing.id);
          continue;
        }
        const form = new FormData();
        form.append("file", file, file.name);
        // The Web App validates the bytes, then passes them only to bot-owned
        // staging. The browser never receives a local path or provider handle.
        const uploaded = await api("/uploads", {
          method: "POST",
          headers: { "Idempotency-Key": randomKey("upload") },
          body: form
        });
        const uploadId = uploaded && uploaded.data && uploaded.data.id;
        if (!uploadId) throw new Error("Core Bridge chưa xác nhận tệp đính kèm.");
        if (!uploadIds.includes(uploadId)) uploadIds.push(uploadId);
      }
      delete values[field];
    }
    if (uploadIds.length) values.upload_ids = uploadIds;
    return values;
  }

  async function handleAction(event) {
    const detail = event.detail || {};
    const action = detail.action;
    const route = (detail.route || window.location.pathname).split("?")[0];
    const fields = detail.fields || {};
    let featureInput = null;
    try {
      if (action === "auth-register") {
        if (fields.password !== fields.confirm_password) throw new Error("Xác nhận mật khẩu chưa khớp.");
        const result = await api("/auth/register", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: fields.email || "", password: fields.password || "", display_name: fields.name || "" }) });
        toast(result.message);
        await hydrate();
        window.location.assign("/onboarding");
        return;
      }
      if (action === "auth-login") {
        const result = await api("/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: fields.email || "", password: fields.password || "" }) });
        toast(result.message);
        await hydrate();
        const account = result.data && result.data.account ? result.data.account : {};
        const requested = safeReturnPath(new URLSearchParams(window.location.search).get("next") || "");
        window.location.assign(account.canonical_user_id ? (requested || "/dashboard") : "/onboarding");
        return;
      }
      if (action === "auth-logout") {
        const result = await api("/auth/logout", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
        toast(result.message || "Đã đăng xuất.");
        window.location.assign("/login");
        return;
      }
      if (action === "start-telegram-link") {
        const result = await api("/auth/telegram/link/start", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
        merge({ linkFlow: { status: result.status || "awaiting_confirm", message: result.message, data: result.data || {} }, linkStatus: { linked: false } });
        toast(result.message);
        return;
      }
      if (action === "refresh-link-status") {
        const result = await api("/auth/telegram/link/status");
        merge({ linkStatus: result.data || {} });
        if (result.data && result.data.linked) {
          await hydrate();
          toast("Telegram đã được liên kết. Bạn có thể mở Dashboard.");
        } else {
          toast(result.message);
        }
        return;
      }
      if (action === "filter-jobs") {
        const filter = ["all", "queued", "processing", "completed", "failed", "cancelled", "refunded"].includes(detail.jobFilter) ? detail.jobFilter : "all";
        merge({ jobFilter: filter });
        return;
      }
      if (action === "refresh-jobs") {
        const result = await api("/jobs");
        const items = result.data && result.data.items ? result.data.items : [];
        merge({ jobs: items });
        scheduleJobPolling("/jobs", items);
        toast(result.message || "Đã làm mới danh sách job canonical.");
        return;
      }
      if (action === "refresh-assets") {
        const result = await api("/assets");
        merge({ assets: result.data && result.data.items ? result.data.items : [] });
        toast(result.message || "Đã làm mới metadata tài sản.");
        return;
      }
      if (action === "refresh-admin") {
        const path = route.startsWith("/admin") ? route : "/admin";
        const endpoints = {
          "/admin": "/admin/summary", "/admin/users": "/admin/users", "/admin/jobs": "/admin/jobs",
          "/admin/jobs/failed": "/admin/jobs", "/admin/payments": "/admin/payments", "/admin/providers": "/admin/providers", "/admin/tickets": "/admin/tickets"
        };
        const pieces = path.split("/").filter(Boolean);
        const module = pieces[1] || "overview";
        const recordId = pieces.length > 2 ? pieces.slice(2).join("/") : "";
        const endpoint = endpoints[path] || `/admin/modules/${encodeURIComponent(module)}${recordId ? `?record_id=${encodeURIComponent(recordId)}` : ""}`;
        const result = await api(endpoint);
        merge({ adminData: result.data || {} });
        toast(result.message || "Đã làm mới dữ liệu vận hành đã được role-check.");
        return;
      }
      if (action === "payment-create") {
        const packageId = String(fields.package || "");
        const submission = acquireSubmission("payment", packageId);
        if (!submission) {
          toast("Yêu cầu thanh toán đang được gửi. Vui lòng chờ phản hồi canonical.", "error");
          return;
        }
        try {
          const result = await api("/payments/create", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ package_id: packageId, payment_type: "topup_xu", idempotency_key: submission.key }) });
          merge({ paymentFlow: { status: (result.data && result.data.status) || result.status || "awaiting_confirm", message: result.message, data: result.data || {} } });
          toast(result.message);
        } finally {
          releaseSubmission(submission);
        }
        return;
      }
      if (action === "refresh-payment") {
        const paymentId = String(detail.paymentId || "").trim();
        if (!paymentId) throw new Error("Mã giao dịch không hợp lệ.");
        const result = await api(`/payments/${encodeURIComponent(paymentId)}`);
        merge({ paymentFlow: { status: (result.data && result.data.status) || result.status || "guarded", message: result.message, data: result.data || {} } });
        toast(result.message);
        return;
      }
      if (action === "create-ticket") {
        const subject = String(fields.subject || "");
        const detailText = String(fields.detail || "");
        const submission = acquireSubmission("ticket", `${subject}\n${detailText}`);
        if (!submission) {
          toast("Ticket đang được gửi. Vui lòng chờ phản hồi canonical.", "error");
          return;
        }
        try {
          const result = await api("/support/tickets", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ subject, detail: detailText, idempotency_key: submission.key }) });
          toast(result.message);
          window.location.assign("/tickets");
        } finally {
          releaseSubmission(submission);
        }
        return;
      }
      if (action === "feature-draft" || action === "feature-estimate" || action === "feature-confirm") {
        const feature = FEATURE_BY_PATH[route];
        if (!feature) throw new Error("Tính năng này chưa có mapping bridge an toàn.");
        if (action === "feature-confirm" && !window.confirm("Xác nhận gửi yêu cầu cho Core Bridge? Xu, job và trạng thái chỉ do bot canonical quyết định.")) return;
        const phase = action.replace("feature-", "");
        featureInput = await payloadFor(fields, route);
        const result = await api(`/features/${encodeURIComponent(feature)}/${phase}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ input: featureInput, idempotency_key: randomKey(phase) }) });
        toast(result.message);
        merge({
          pageStates: { ...(base().pageStates || {}), [route]: result.status },
          featureFlows: { ...(base().featureFlows || {}), [route]: { feature, status: result.status, message: result.message, data: result.data || {}, input: featureInput } }
        });
        return;
      }
      toast("Thao tác này đang chờ adapter canonical được xác minh.", "error");
    } catch (error) {
      if (action === "payment-create" && error && error.payload) {
        const payload = error.payload;
        merge({ paymentFlow: { status: (payload.data && payload.data.status) || payload.status || "guarded", message: payload.message || "Yêu cầu thanh toán đang được bảo vệ.", data: payload.data || {} } });
      }
      if ((action === "feature-draft" || action === "feature-estimate" || action === "feature-confirm") && error && error.payload) {
        const feature = FEATURE_BY_PATH[route];
        const payload = error.payload;
        merge({
          pageStates: { ...(base().pageStates || {}), [route]: payload.status || "guarded" },
          featureFlows: { ...(base().featureFlows || {}), [route]: { feature, status: payload.status || "guarded", message: payload.message || "Yêu cầu đang được bảo vệ.", data: payload.data || {}, input: featureInput || (base().featureFlows && base().featureFlows[route] && base().featureFlows[route].input) || {} } }
        });
      }
      toast((error && error.payload && error.payload.message) || (error && error.message) || "Yêu cầu chưa được xác nhận.", "error");
    }
  }

  window.addEventListener("toanaas:portal-action", handleAction);
  let initialHydration = null;
  function startInitialHydration() {
    if (!initialHydration) initialHydration = hydrate().catch(() => {});
    return initialHydration;
  }
  // A normal navigation emits both DOMContentLoaded and pageshow.  Hydrate
  // once for that load, then deliberately refresh only when a page is restored
  // from the back-forward cache.
  window.addEventListener("pageshow", (event) => { if (event.persisted) hydrate().catch(() => {}); });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", startInitialHydration, { once: true });
  else startInitialHydration();
}());
