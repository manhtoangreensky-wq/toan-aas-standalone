/*
 * Server-backed integration for the presentation shell.
 * It calls only the standalone Web App API.  Providers, PayOS and bot secrets
 * remain server-side behind the private bridge.
 */
(function portalIntegration() {
  "use strict";

  const API = "/api/v1";
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

  function featurePageStates(catalog, readiness) {
    const states = {};
    const features = (readiness && readiness.features) || {};
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
    const bridgeAvailable = Boolean(status.bridge_configured && account && account.canonical_user_id);
    const capabilities = {
      "auth-login": true,
      "auth-register": true,
      "complete-onboarding": Boolean(account),
      "payment-create": Boolean(status.flags && status.flags.payment_enabled && bridgeAvailable),
      "feature-draft": Boolean(bridgeAvailable),
      "feature-estimate": Boolean(bridgeAvailable),
      // Confirm remains clickable when the bridge is present so its canonical
      // guarded/maintenance result can be shown instead of being faked client-side.
      "feature-confirm": Boolean(bridgeAvailable),
      "create-ticket": Boolean(bridgeAvailable),
      "admin-review": Boolean(account && account.role === "admin" && bridgeAvailable),
      "admin-retry": Boolean(account && account.role === "admin" && bridgeAvailable),
      "admin-refund": Boolean(account && account.role === "admin" && bridgeAvailable),
      "admin-freeze": Boolean(account && account.role === "admin" && bridgeAvailable)
    };
    merge({
      ...context,
      catalog,
      isAdmin: Boolean(account && account.role === "admin"),
      profile: account ? { displayName: account.display_name || account.email, email: account.email } : {},
      session: {
        authenticated: Boolean(account), csrfReady: Boolean(me.csrf_token), csrfToken: me.csrf_token || "",
        displayName: account ? (account.display_name || account.email) : "", email: account ? account.email : ""
      },
      bridge: { available: bridgeAvailable, csrfReady: Boolean(me.csrf_token), configured: Boolean(status.bridge_configured) },
      pwaEnabled: Boolean(status.flags && status.flags.pwa_enabled),
      capabilities,
      pageStates: featurePageStates(catalog, {})
    });
    if (status.flags && status.flags.pwa_enabled && "serviceWorker" in navigator) {
      navigator.serviceWorker.register("/static/portal/service-worker.js").catch(() => {});
    }
    if (bridgeAvailable) await hydrateCanonicalData();
  }

  async function hydrateCanonicalData() {
    const context = base();
    const path = (context.path || window.location.pathname).split("?")[0];
    try {
      if (path === "/wallet" || path === "/wallet/topup") {
        const [wallet, history] = await Promise.all([api("/wallet"), api("/wallet/history")]);
        merge({ wallet: wallet.data, walletHistory: history.data && history.data.items ? history.data.items : [] });
      } else if (path === "/jobs" || path.startsWith("/jobs/")) {
        const jobs = await api("/jobs");
        merge({ jobs: jobs.data && jobs.data.items ? jobs.data.items : [] });
      } else if (path === "/assets") {
        const assets = await api("/assets");
        merge({ assets: assets.data && assets.data.items ? assets.data.items : [] });
      } else if (path === "/tickets") {
        const tickets = await api("/support/tickets");
        merge({ tickets: tickets.data && tickets.data.items ? tickets.data.items : [] });
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
        const endpoint = endpoints[path];
        if (!endpoint) {
          merge({ adminData: { items: [], guarded: true, message: "Module này đang chờ adapter read-only canonical của bot." } });
          return;
        }
        const admin = await api(endpoint);
        merge({ adminData: admin.data || {} });
      } else {
        const readiness = await api("/features/status");
        merge({ readiness: readiness.data || {} });
      }
    } catch (error) {
      // A guarded bridge is an expected state; do not manufacture data.
      if (error && error.payload && error.payload.message) toast(error.payload.message, "error");
    }
  }

  function payloadFor(fields) {
    const values = { ...fields };
    delete values.password;
    delete values.confirm_password;
    return values;
  }

  async function handleAction(event) {
    const detail = event.detail || {};
    const action = detail.action;
    const route = (detail.route || window.location.pathname).split("?")[0];
    const fields = detail.fields || {};
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
        window.location.assign("/dashboard");
        return;
      }
      if (action === "complete-onboarding") {
        const result = await api("/auth/telegram/link/start", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
        const code = result.data && result.data.code;
        toast(code ? `Mã liên kết: ${code}. Hãy gửi mã này cho bot TOAN AAS.` : result.message);
        return;
      }
      if (action === "payment-create") {
        const result = await api("/payments/create", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ package_id: fields.package || "", payment_type: "topup_xu", idempotency_key: randomKey("payment") }) });
        toast(result.message);
        return;
      }
      if (action === "create-ticket") {
        const result = await api("/support/tickets", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ subject: fields.subject || "", detail: fields.detail || "", idempotency_key: randomKey("ticket") }) });
        toast(result.message);
        return;
      }
      if (action === "asset-download") {
        const assetId = String(detail.assetId || "");
        if (!assetId) throw new Error("Tài sản không hợp lệ.");
        const result = await api(`/assets/${encodeURIComponent(assetId)}/download`);
        toast(result.message);
        return;
      }
      if (action === "feature-draft" || action === "feature-estimate" || action === "feature-confirm") {
        const feature = FEATURE_BY_PATH[route];
        if (!feature) throw new Error("Tính năng này chưa có mapping bridge an toàn.");
        if (action === "feature-confirm" && !window.confirm("Xác nhận gửi yêu cầu cho Core Bridge? Xu, job và trạng thái chỉ do bot canonical quyết định.")) return;
        const phase = action.replace("feature-", "");
        const result = await api(`/features/${encodeURIComponent(feature)}/${phase}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ input: payloadFor(fields), idempotency_key: randomKey(phase) }) });
        toast(result.message);
        merge({
          pageStates: { ...(base().pageStates || {}), [route]: result.status },
          featureFlows: { ...(base().featureFlows || {}), [route]: { feature, status: result.status, message: result.message, data: result.data || {} } }
        });
        return;
      }
      toast("Thao tác này đang chờ adapter canonical được xác minh.", "error");
    } catch (error) {
      if ((action === "feature-draft" || action === "feature-estimate" || action === "feature-confirm") && error && error.payload) {
        const feature = FEATURE_BY_PATH[route];
        const payload = error.payload;
        merge({
          pageStates: { ...(base().pageStates || {}), [route]: payload.status || "guarded" },
          featureFlows: { ...(base().featureFlows || {}), [route]: { feature, status: payload.status || "guarded", message: payload.message || "Yêu cầu đang được bảo vệ.", data: payload.data || {} } }
        });
      }
      toast((error && error.payload && error.payload.message) || (error && error.message) || "Yêu cầu chưa được xác nhận.", "error");
    }
  }

  window.addEventListener("toanaas:portal-action", handleAction);
  window.addEventListener("pageshow", () => { hydrate().catch(() => {}); }, { once: true });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => { hydrate().catch(() => {}); }, { once: true });
  else hydrate().catch(() => {});
}());
