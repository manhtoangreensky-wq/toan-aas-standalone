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
  const PAYMENT_POLL_INTERVAL_MS = 10000;
  const PAYMENT_POLL_MAX_BACKOFF_MS = 60000;
  // Mirrors Bot P0's `TRANSLATE_LANGUAGE_OPTIONS`. Keep this explicit rather
  // than accepting arbitrary target values from the browser.
  const CANONICAL_TARGET_LANGUAGE_CODES = new Set([
    "vi", "en", "zh", "zh_cn", "zh_tw", "ja", "ko", "th", "fr", "de", "es",
    "id", "ms", "pt", "ru", "ar", "hi", "lo", "km", "my", "fil", "auto"
  ]);
  // Bot P0 owns staging and rejects more than eight opaque upload IDs per
  // feature request. Preflight before `payloadFor` so the browser does not
  // upload extra files only to receive a late canonical failure.
  const MAX_FEATURE_UPLOADS = 8;
  const SUPPORT_SECRET_PATTERN = /\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|client[ _-]?secret|secret(?:[ _-]?key)?|password|passphrase|authorization)\b\s*(?:[:=]|\bis\b)\s*(?:bearer\s+)?[A-Za-z0-9_./+=:-]{8,}|\bbearer\s+[A-Za-z0-9._~+/=-]{12,}|\b(?:sk|pk|rk)_[A-Za-z0-9_-]{16,}|\b(?:otp|mã\s*xác\s*thực|ma\s*xac\s*thuc|cvv|cvc)\s*[:=]?\s*\d{3,8}\b/i;
  const SUPPORT_CARD_CANDIDATE_PATTERN = /\b(?:\d[ -]?){13,19}\b/g;
  let jobPollTimer = 0;
  let jobPollFailures = 0;
  let paymentPollTimer = 0;
  let paymentPollFailures = 0;
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
  const ADMIN_DIRECT_ENDPOINTS = Object.freeze({
    "/admin": "/admin/summary", "/admin/users": "/admin/users", "/admin/jobs": "/admin/jobs",
    "/admin/jobs/failed": "/admin/modules/failed-jobs", "/admin/payments": "/admin/payments",
    "/admin/providers": "/admin/modules/providers", "/admin/tickets": "/admin/tickets"
  });
  // The frozen bot exposes these two read-only adapters under plural/report
  // module names.  This preserves the friendly Web routes without inventing
  // an exporter, backup action or extra Bot endpoint.
  const ADMIN_MODULE_ALIASES = Object.freeze({ backup: "backups", export: "reports" });

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

  function looksLikePaymentCard(candidate) {
    const digits = String(candidate || "").replace(/\D/g, "");
    if (digits.length < 13 || digits.length > 19 || new Set(digits).size === 1) return false;
    let total = 0;
    for (let index = 0; index < digits.length; index += 1) {
      let value = Number(digits[digits.length - 1 - index]);
      if (index % 2 === 1) value = value > 4 ? (value * 2) - 9 : value * 2;
      total += value;
    }
    return total % 10 === 0;
  }

  function validateSupportIntake(subject, detail) {
    const text = `${String(subject || "")}\n${String(detail || "")}`;
    const candidates = text.match(SUPPORT_CARD_CANDIDATE_PATTERN) || [];
    if (SUPPORT_SECRET_PATTERN.test(text) || candidates.some((item) => looksLikePaymentCard(item))) {
      return "Ticket không nhận API key, token, mật khẩu, OTP/CVV hoặc số thẻ. Hãy xóa dữ liệu nhạy cảm trước khi gửi.";
    }
    return "";
  }

  function adminEndpointForPath(path) {
    const normalized = String(path || "/admin").split("?")[0];
    if (ADMIN_DIRECT_ENDPOINTS[normalized]) return ADMIN_DIRECT_ENDPOINTS[normalized];
    const pieces = normalized.split("/").filter(Boolean);
    const requestedModule = pieces[1] || "overview";
    const module = ADMIN_MODULE_ALIASES[requestedModule] || requestedModule;
    const recordId = pieces.length > 2 ? pieces.slice(2).join("/") : "";
    return `/admin/modules/${encodeURIComponent(module)}${recordId ? `?record_id=${encodeURIComponent(recordId)}` : ""}`;
  }

  async function copyPaymentBotCommand(value) {
    const command = String(value || "");
    if (!["/naptien", "/thucong"].includes(command)) throw new Error("Lệnh thanh toán canonical không hợp lệ.");
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(command);
      return;
    }
    const field = document.createElement("textarea");
    field.value = command;
    field.setAttribute("readonly", "");
    field.style.position = "fixed";
    field.style.opacity = "0";
    document.body.appendChild(field);
    field.select();
    const copied = document.execCommand("copy");
    field.remove();
    if (!copied) throw new Error("Trình duyệt chưa cho phép sao chép. Hãy copy lệnh hiển thị bên cạnh.");
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

  function setActionBusy(action, route, busy) {
    document.querySelectorAll("[data-portal-action]").forEach((control) => {
      const matches = control.getAttribute("data-portal-action") === action && (control.getAttribute("data-portal-route") || window.location.pathname) === route;
      if (!matches) return;
      control.disabled = Boolean(busy);
      control.setAttribute("aria-busy", String(Boolean(busy)));
    });
    document.querySelectorAll("[data-portal-form]").forEach((form) => {
      const matches = form.getAttribute("data-portal-action") === action && (form.getAttribute("data-portal-route") || window.location.pathname) === route;
      if (!matches) return;
      const submit = form.querySelector('button[type="submit"]');
      if (submit) {
        submit.disabled = Boolean(busy);
        submit.setAttribute("aria-busy", String(Boolean(busy)));
      }
    });
  }

  function stableValue(value) {
    if (typeof File !== "undefined" && value instanceof File) {
      return { file_name: value.name, content_size: Number(value.size || 0), content_type: value.type || "", modified_at: Number(value.lastModified || 0) };
    }
    if (Array.isArray(value)) return value.map(stableValue);
    if (value && typeof value === "object") {
      return Object.keys(value).sort().reduce((result, key) => {
        result[key] = stableValue(value[key]);
        return result;
      }, {});
    }
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean" || value === null) return value;
    return null;
  }

  function featureFingerprint(value) {
    return JSON.stringify(stableValue(value && typeof value === "object" ? value : {}));
  }

  function priorFeatureFlow(route) {
    const flows = base().featureFlows;
    return flows && typeof flows === "object" && flows[route] && typeof flows[route] === "object" ? flows[route] : {};
  }

  function selectedFiles(fields) {
    const files = [];
    Object.values(fields || {}).forEach((value) => {
      if (typeof File !== "undefined" && value instanceof File) files.push(value);
      else if (Array.isArray(value) && typeof File !== "undefined") value.forEach((item) => { if (item instanceof File) files.push(item); });
    });
    return files;
  }

  function extensionOf(item) {
    const name = String((item && (item.name || item.file_name)) || "").toLowerCase();
    const index = name.lastIndexOf(".");
    return index >= 0 ? name.slice(index) : "";
  }

  function uploadItemsFor(route, fields) {
    const flow = priorFeatureFlow(route);
    const staged = flow.data && Array.isArray(flow.data.uploads) ? flow.data.uploads : [];
    return [...selectedFiles(fields), ...staged.filter((item) => item && typeof item === "object")];
  }

  function uploadCountFor(route, fields) {
    const flow = priorFeatureFlow(route);
    const stagedIds = flow.input && Array.isArray(flow.input.upload_ids) ? flow.input.upload_ids.filter((item) => typeof item === "string" && item) : [];
    return Math.max(selectedFiles(fields).length + stagedIds.length, uploadItemsFor(route, fields).length);
  }

  function allExtensionsMatch(items, allowed) {
    return items.length > 0 && items.every((item) => allowed.has(extensionOf(item)));
  }

  function anyExtensionMatches(items, allowed) {
    return items.some((item) => allowed.has(extensionOf(item)));
  }

  function scalarField(fields, route, name) {
    if (Object.prototype.hasOwnProperty.call(fields || {}, name)) return fields[name];
    const flow = priorFeatureFlow(route);
    return flow.input && typeof flow.input === "object" ? flow.input[name] : "";
  }

  function validateFeatureIntake(feature, route, fields) {
    const files = uploadItemsFor(route, fields);
    const fileCount = uploadCountFor(route, fields);
    const audio = new Set([".mp3", ".wav", ".m4a", ".ogg"]);
    const media = new Set([".mp3", ".wav", ".m4a", ".ogg", ".mp4", ".mov", ".webm"]);
    const subtitleText = new Set([".srt", ".vtt", ".txt"]);
    const images = new Set([".jpg", ".jpeg", ".png", ".webp"]);
    const pdf = new Set([".pdf"]);
    const language = String(scalarField(fields, route, "target_language") || "").trim();
    if (fileCount > MAX_FEATURE_UPLOADS) return `Mỗi workflow chỉ nhận tối đa ${MAX_FEATURE_UPLOADS} tệp đã vào staging canonical.`;
    if (feature === "voice_clone") {
      if (!fileCount) return "Voice Clone cần một mẫu audio đã vào staging canonical.";
      if (files.length && !anyExtensionMatches(files, audio)) return "Voice Clone chỉ nhận mẫu audio MP3, WAV, M4A hoặc OGG.";
      if (scalarField(fields, route, "consent") !== true) return "Hãy xác nhận quyền sử dụng mẫu giọng trước khi tiếp tục.";
    }
    if (feature === "music_song") {
      const lengthMode = String(scalarField(fields, route, "song_length_mode") || "").trim();
      if (!["seconds", "half", "full"].includes(lengthMode)) return "Hãy chọn dạng bài hát canonical trước khi tiếp tục.";
      if (lengthMode === "seconds") {
        const duration = Number(scalarField(fields, route, "duration_seconds"));
        if (!Number.isInteger(duration) || duration < 1 || duration > 600) return "Khi chọn Theo số giây, hãy nhập thời lượng nguyên từ 1 đến 600 giây.";
      }
    }
    if (feature === "music_upload") {
      if (!fileCount) return "Hãy chọn tệp âm thanh trước khi tạo draft.";
      if (files.length && !allExtensionsMatch(files, audio)) return "Nhạc của tôi chỉ nhận MP3, WAV, M4A hoặc OGG.";
    }
    if (["subtitle_asr", "subtitle_create", "asr", "subtitle_translate", "video_dub"].includes(feature)) {
      if (!fileCount) return "Workflow phụ đề/lồng tiếng cần media đã vào staging canonical.";
      const allowed = feature === "subtitle_translate" ? new Set([...media, ...subtitleText]) : media;
      if (files.length && !anyExtensionMatches(files, allowed)) return "Tệp nguồn chưa đúng loại media/subtitle mà Core Bridge chấp nhận.";
      if (["subtitle_translate", "video_dub"].includes(feature) && !CANONICAL_TARGET_LANGUAGE_CODES.has(language)) return "Hãy chọn ngôn ngữ đích canonical từ danh sách Bot P0 hỗ trợ.";
    }
    if (["documents", "documents_pdf", "documents_ocr", "documents_merge", "documents_split", "documents_compress", "documents_translate"].includes(feature)) {
      if (!fileCount) return "Workflow tài liệu cần tệp đã vào staging canonical.";
      const operationByFeature = {
        documents_ocr: String(scalarField(fields, route, "operation") || "ocr_image"),
        documents_merge: "merge_pdf", documents_split: "split_pdf", documents_compress: "compress_pdf", documents_translate: "translate_document"
      };
      const operation = operationByFeature[feature] || String(scalarField(fields, route, "operation") || "pdf_to_word");
      if (operation === "image_to_pdf" && files.length && !allExtensionsMatch(files, images)) return "Image-to-PDF chỉ nhận JPG, PNG hoặc WebP.";
      if (["pdf_to_word", "pdf_to_images", "merge_pdf", "split_pdf", "compress_pdf", "ocr_pdf"].includes(operation) && files.length && !allExtensionsMatch(files, pdf)) return "Thao tác này chỉ nhận tệp PDF.";
      if (operation === "ocr_image" && files.length && !anyExtensionMatches(files, images)) return "OCR ảnh chỉ nhận JPG, PNG hoặc WebP.";
      if (operation === "merge_pdf" && fileCount < 2) return "Gộp PDF cần ít nhất hai tệp đã vào staging canonical.";
      if (operation === "split_pdf" && !/^\d+(?:-\d+)?$/.test(String(scalarField(fields, route, "page_range") || "").trim())) return "Khoảng trang phải là một trang hoặc dải liên tiếp, ví dụ 2 hoặc 2-5.";
      if (operation === "translate_document" && !CANONICAL_TARGET_LANGUAGE_CODES.has(language)) return "Hãy chọn ngôn ngữ đích canonical cho tài liệu từ danh sách Bot P0 hỗ trợ.";
    }
    if (["image_edit", "image_upscale", "image_transform", "image_remove_background"].includes(feature)) {
      if (!fileCount) return "Workflow ảnh này cần ảnh nguồn đã vào staging canonical.";
      if (files.length && !anyExtensionMatches(files, images)) return "Workflow ảnh này chỉ nhận JPG, PNG hoặc WebP.";
    }
    if (feature === "video_image_to_video") {
      if (!fileCount) return "Image-to-Video cần ảnh nguồn đã vào staging canonical.";
      if (files.length && !anyExtensionMatches(files, images)) return "Image-to-Video chỉ nhận JPG, PNG hoặc WebP.";
    }
    if (feature === "voice_saved_tts" && !String(scalarField(fields, route, "voice_profile_id") || "").trim()) return "Hãy chọn một giọng Voice Vault đã sẵn sàng.";
    return "";
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

  function paymentIdFromData(data) {
    const source = data && typeof data === "object" ? data : {};
    return String(source.payment_id || source.order_code || source.id || "").trim();
  }

  function validPaymentId(value) {
    return /^[A-Za-z0-9._:-]{1,120}$/.test(String(value || "").trim());
  }

  function paymentNeedsPolling(flow) {
    const data = flow && flow.data && typeof flow.data === "object" ? flow.data : {};
    const status = String(data.status || (flow && flow.status) || "").toLowerCase();
    return ["pending", "queued", "awaiting_confirm", "processing", "waiting", "unpaid"].includes(status);
  }

  function schedulePaymentPolling(paymentId, flow, delayMs, replaceExisting) {
    const route = (base().path || window.location.pathname).split("?")[0];
    if (!paymentId || route !== "/wallet/topup" || !base().bridge || base().bridge.available !== true || !paymentNeedsPolling(flow)) return;
    if (replaceExisting && paymentPollTimer) {
      window.clearTimeout(paymentPollTimer);
      paymentPollTimer = 0;
    }
    if (paymentPollTimer) return;
    const delay = Number.isFinite(Number(delayMs)) ? Math.max(0, Number(delayMs)) : PAYMENT_POLL_INTERVAL_MS;
    paymentPollTimer = window.setTimeout(async () => {
      paymentPollTimer = 0;
      try {
        const result = await api(`/payments/${encodeURIComponent(paymentId)}`);
        const nextFlow = {
          status: (result.data && result.data.status) || result.status || "guarded",
          message: result.message,
          data: result.data || {}
        };
        merge({ paymentFlow: nextFlow });
        paymentPollFailures = 0;
        schedulePaymentPolling(paymentIdFromData(nextFlow.data), nextFlow);
      } catch (_) {
        // Payment polling is strictly a signed GET read.  A temporary bridge
        // error never changes a payment state or makes a ledger decision.
        paymentPollFailures += 1;
        const currentRoute = (base().path || window.location.pathname).split("?")[0];
        const retryDelay = Math.min(PAYMENT_POLL_MAX_BACKOFF_MS, PAYMENT_POLL_INTERVAL_MS * (2 ** Math.min(paymentPollFailures, 2)));
        if (currentRoute === "/wallet/topup") schedulePaymentPolling(paymentId, flow, retryDelay);
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
    const telegramLinked = Boolean(account && account.telegram_linked);
    const bridgeAvailable = Boolean(copyfastEnabled && status.bridge_configured && telegramLinked);
    const capabilities = {
      "auth-login": true,
      "auth-register": true,
      "auth-logout": Boolean(account && me.csrf_token),
      "start-telegram-link": Boolean(account),
      "refresh-link-status": Boolean(account),
      "refresh-jobs": Boolean(bridgeAvailable),
      "refresh-assets": Boolean(bridgeAvailable),
      "refresh-payment": Boolean(bridgeAvailable),
      "payment-lookup": Boolean(bridgeAvailable),
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
      linkStatus: { linked: telegramLinked },
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
    const currentPath = (context.path || window.location.pathname).split("?")[0];
    if (account && currentPath === "/onboarding") await hydrateLinkStatus();
    // Manual top-up remains in the linked Telegram bot and does not require a
    // provider call from the Web App, so expose its safe entry point even when
    // a private bridge data read is temporarily unavailable.
    if (account && telegramLinked && currentPath === "/wallet/topup") await hydratePaymentOptions();
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

  async function hydratePaymentOptions() {
    try {
      const options = await api("/payments/options");
      merge({ paymentOptions: options.data || {} });
    } catch (_) {
      // This local/read-only metadata is optional presentation.  Do not infer
      // a payment method or expose legacy billing data after a failed request.
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
      } else if (path === "/voice/outputs") {
        const readiness = await api("/features/status");
        merge({
          readiness: readiness.data || {},
          pageStates: { ...(base().pageStates || {}), ...featurePageStates(base().catalog || [], readiness.data || {}) }
        });
      } else if (path === "/assets" || ["/image/history", "/image/assets", "/video/preview", "/video/export", "/music/library", "/music-library", "/subtitle/formats"].includes(path)) {
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
        const admin = await api(adminEndpointForPath(path));
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
    let featurePhase = "";
    let featureSubmission = null;
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
        window.location.assign(account.telegram_linked ? (requested || "/dashboard") : "/onboarding");
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
      if (action === "copy-payment-command") {
        const command = String(detail.copyText || "");
        await copyPaymentBotCommand(command);
        toast(`Đã sao chép ${command}. Hãy dán lệnh vào bot TOAN AAS đã liên kết.`);
        return;
      }
      if (action === "filter-jobs") {
        const filter = ["all", "queued", "processing", "completed", "failed", "cancelled", "refunded"].includes(detail.jobFilter) ? detail.jobFilter : "all";
        merge({ jobFilter: filter });
        return;
      }
      if (action === "filter-assets") {
        const filter = ["all", "validated", "waiting", "completed", "failed"].includes(detail.assetFilter) ? detail.assetFilter : "all";
        merge({ assetFilter: filter });
        return;
      }
      if (action === "filter-tickets") {
        const filter = ["all", "new", "reviewing", "waiting_user", "waiting_provider", "refund_pending", "resolved", "closed"].includes(detail.ticketFilter) ? detail.ticketFilter : "all";
        merge({ ticketFilter: filter });
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
        const result = await api(adminEndpointForPath(path));
        merge({ adminData: result.data || {} });
        toast(result.message || "Đã làm mới dữ liệu vận hành đã được role-check.");
        return;
      }
      if (action === "payment-create") {
        const packageId = String(fields.package || "").trim();
        if (!packageId) throw new Error("Hãy chọn gói từ catalog canonical trước khi tạo yêu cầu thanh toán.");
        const submission = acquireSubmission("payment", packageId);
        if (!submission) {
          toast("Yêu cầu thanh toán đang được gửi. Vui lòng chờ phản hồi canonical.", "error");
          return;
        }
        try {
          const result = await api("/payments/create", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ package_id: packageId, payment_type: "topup_xu", idempotency_key: submission.key }) });
          const nextFlow = { status: (result.data && result.data.status) || result.status || "awaiting_confirm", message: result.message, data: result.data || {} };
          merge({ paymentFlow: nextFlow });
          schedulePaymentPolling(paymentIdFromData(nextFlow.data), nextFlow, undefined, true);
          toast(result.message);
        } finally {
          releaseSubmission(submission);
        }
        return;
      }
      if (action === "payment-lookup") {
        const paymentId = String(fields.payment_id || "").trim();
        if (!validPaymentId(paymentId)) throw new Error("Mã đơn chỉ gồm chữ, số, dấu chấm, gạch nối, gạch dưới hoặc dấu hai chấm.");
        setActionBusy(action, route, true);
        try {
          const result = await api(`/payments/${encodeURIComponent(paymentId)}`);
          const nextFlow = { status: (result.data && result.data.status) || result.status || "guarded", message: result.message, data: result.data || {} };
          merge({ paymentFlow: nextFlow });
          schedulePaymentPolling(paymentIdFromData(nextFlow.data), nextFlow, undefined, true);
          toast(result.message);
        } finally {
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "refresh-payment") {
        const paymentId = String(detail.paymentId || "").trim();
        if (!validPaymentId(paymentId)) throw new Error("Mã giao dịch không hợp lệ.");
        const result = await api(`/payments/${encodeURIComponent(paymentId)}`);
        const nextFlow = { status: (result.data && result.data.status) || result.status || "guarded", message: result.message, data: result.data || {} };
        merge({ paymentFlow: nextFlow });
        schedulePaymentPolling(paymentIdFromData(nextFlow.data), nextFlow, undefined, true);
        toast(result.message);
        return;
      }
      if (action === "create-ticket") {
        const subject = String(fields.subject || "");
        const detailText = String(fields.detail || "");
        const safetyError = validateSupportIntake(subject, detailText);
        if (safetyError) throw new Error(safetyError);
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
        featurePhase = action.replace("feature-", "");
        const intakeError = validateFeatureIntake(feature, route, fields);
        if (intakeError) throw new Error(intakeError);
        if (featurePhase === "confirm" && selectedFiles(fields).length) {
          throw new Error("Tệp nguồn đã thay đổi. Hãy estimate lại trước khi xác nhận để Core Bridge kiểm tra đúng input.");
        }
        const draftScope = `feature:${route}:${featurePhase}`;
        const initialFingerprint = featureFingerprint({ ...priorFeatureFlow(route).input, ...fields, phase: featurePhase });
        featureSubmission = acquireSubmission(draftScope, initialFingerprint);
        if (!featureSubmission) {
          toast("Yêu cầu feature đang được gửi. Vui lòng chờ phản hồi canonical.", "error");
          return;
        }
        setActionBusy(action, route, true);
        featureInput = await payloadFor(fields, route);
        const inputFingerprint = featureFingerprint(featureInput);
        if (featurePhase === "confirm") {
          const prior = priorFeatureFlow(route);
          const estimate = prior.data && typeof prior.data === "object" ? prior.data.estimate : null;
          if (!prior || prior.phase !== "estimate" || prior.status !== "awaiting_confirm" || !estimate || estimate.available !== true || prior.estimateFingerprint !== inputFingerprint) {
            throw new Error("Thông tin đã thay đổi hoặc chưa có estimate canonical hợp lệ. Hãy ước tính lại trước khi xác nhận.");
          }
        }
        const result = await api(`/features/${encodeURIComponent(feature)}/${featurePhase}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ input: featureInput, idempotency_key: featureSubmission.key })
        });
        const estimateAvailable = featurePhase === "estimate" && result.data && result.data.estimate && result.data.estimate.available === true;
        toast(result.message);
        merge({
          pageStates: { ...(base().pageStates || {}), [route]: result.status },
          featureFlows: {
            ...(base().featureFlows || {}),
            [route]: {
              feature,
              phase: featurePhase,
              status: result.status,
              message: result.message,
              data: result.data || {},
              input: featureInput,
              inputFingerprint,
              estimateFingerprint: estimateAvailable ? inputFingerprint : ""
            }
          }
        });
        return;
      }
      toast("Thao tác này đang chờ adapter canonical được xác minh.", "error");
    } catch (error) {
      if ((action === "payment-create" || action === "payment-lookup") && error && error.payload) {
        const payload = error.payload;
        merge({ paymentFlow: { status: (payload.data && payload.data.status) || payload.status || "guarded", message: payload.message || "Yêu cầu thanh toán đang được bảo vệ.", data: payload.data || {} } });
      }
      if ((action === "feature-draft" || action === "feature-estimate" || action === "feature-confirm") && error && error.payload) {
        const feature = FEATURE_BY_PATH[route];
        const payload = error.payload;
        const previous = priorFeatureFlow(route);
        merge({
          pageStates: { ...(base().pageStates || {}), [route]: payload.status || "guarded" },
          featureFlows: {
            ...(base().featureFlows || {}),
            [route]: {
              feature,
              phase: featurePhase || previous.phase || "draft",
              status: payload.status || "guarded",
              message: payload.message || "Yêu cầu đang được bảo vệ.",
              data: payload.data || {},
              input: featureInput || previous.input || {},
              inputFingerprint: featureInput ? featureFingerprint(featureInput) : (previous.inputFingerprint || ""),
              estimateFingerprint: previous.estimateFingerprint || ""
            }
          }
        });
      }
      toast((error && error.payload && error.payload.message) || (error && error.message) || "Yêu cầu chưa được xác nhận.", "error");
    } finally {
      if (featureSubmission) {
        releaseSubmission(featureSubmission);
        setActionBusy(action, route, false);
      }
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
